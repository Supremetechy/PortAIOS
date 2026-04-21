#!/usr/bin/env python3
"""
Avatar Bridge - WebSocket Server for Binary Avatar Backend Communication
Handles TTS streaming, FFT analysis, and system state updates
"""

import asyncio
import websockets
import json
import base64
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import tempfile

# Audio processing
try:
    import numpy as np
    import soundfile as sf
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("Warning: numpy/soundfile not available, audio processing limited")

# TTS engines
try:
    from TTS.api import TTS as CoquiTTS
    COQUI_AVAILABLE = True
except ImportError:
    COQUI_AVAILABLE = False

# System monitoring
import psutil
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AvatarBridge")

# Ensure project root is on sys.path so kernel.* imports work
_BRIDGE_ROOT = Path(__file__).resolve().parent.parent
if str(_BRIDGE_ROOT) not in sys.path:
    sys.path.insert(0, str(_BRIDGE_ROOT))

# Agent executor (lazy-loaded on first agent_command)
_agent_executor = None

def _get_agent_executor():
    global _agent_executor
    if _agent_executor is None:
        try:
            from kernel.agent_executor import AgentExecutor
            _agent_executor = AgentExecutor()
            logger.info("AgentExecutor initialized for WebSocket bridge")
        except Exception as e:
            logger.error(f"Failed to initialize AgentExecutor: {e}")
    return _agent_executor


class TTSEngine:
    """Abstract TTS engine interface"""
    
    def synthesize(self, text: str, emotion: str = "neutral") -> bytes:
        """Synthesize text to audio bytes"""
        raise NotImplementedError


class CoquiTTSEngine(TTSEngine):
    """Coqui TTS Engine (High Fidelity)"""
    
    def __init__(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC"):
        if not COQUI_AVAILABLE:
            raise RuntimeError("Coqui TTS not available")
        
        logger.info(f"Loading Coqui TTS model: {model_name}")
        self.tts = CoquiTTS(model_name=model_name)
        logger.info("Coqui TTS model loaded")
    
    def synthesize(self, text: str, emotion: str = "neutral") -> bytes:
        """Synthesize speech and return WAV bytes"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
        
        try:
            # Generate audio
            self.tts.tts_to_file(text=text, file_path=temp_path)
            
            # Read audio file
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
            
            return audio_data
        finally:
            Path(temp_path).unlink(missing_ok=True)


class PiperTTSEngine(TTSEngine):
    """Piper TTS Engine (Robotic/Retro)"""
    
    def __init__(self, model_path: Optional[str] = None):
        logger.info("Initializing Piper TTS (robotic voice)")
        self.model_path = model_path
        # Piper is typically called via subprocess
        # Implementation depends on Piper installation
    
    def synthesize(self, text: str, emotion: str = "neutral") -> bytes:
        """Synthesize speech using Piper"""
        import subprocess
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
        
        try:
            # Call Piper CLI
            cmd = ["piper", "--model", self.model_path or "en_US-lessac-medium", 
                   "--output_file", temp_path]
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            stdout, stderr = process.communicate(input=text.encode())
            
            if process.returncode != 0:
                raise RuntimeError(f"Piper failed: {stderr.decode()}")
            
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
            
            return audio_data
        finally:
            Path(temp_path).unlink(missing_ok=True)


class FallbackTTSEngine(TTSEngine):
    """Fallback TTS using system TTS (for development)"""
    
    def synthesize(self, text: str, emotion: str = "neutral") -> bytes:
        """Return empty audio - client will use Web Speech API"""
        logger.warning("Using fallback TTS - client will handle speech")
        return b""


class AvatarBridgeServer:
    """WebSocket server for avatar communication"""
    
    def __init__(self, host: str = "localhost", port: int = 8765, 
                 tts_engine: str = "coqui"):
        self.host = host
        self.port = port
        self.clients = set()
        
        # Initialize TTS engine
        self.tts = self._init_tts_engine(tts_engine)
        
        # System monitoring
        self.monitoring = True
    
    def _init_tts_engine(self, engine_name: str) -> TTSEngine:
        """Initialize the requested TTS engine"""
        
        if engine_name == "coqui" and COQUI_AVAILABLE:
            try:
                return CoquiTTSEngine()
            except Exception as e:
                logger.error(f"Failed to initialize Coqui TTS: {e}")
        
        if engine_name == "piper":
            try:
                return PiperTTSEngine()
            except Exception as e:
                logger.error(f"Failed to initialize Piper TTS: {e}")
        
        logger.warning("Using fallback TTS engine")
        return FallbackTTSEngine()
    
    async def handle_client(self, websocket, path=None):
        """Handle WebSocket client connection"""
        logger.info(f"Client connected: {websocket.remote_address}")
        self.clients.add(websocket)
        
        try:
            async for message in websocket:
                await self.handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        finally:
            self.clients.remove(websocket)
    
    async def handle_message(self, websocket, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'tts_request':
                await self.handle_tts_request(websocket, data)
            
            elif msg_type == 'request_status':
                await self.send_system_status(websocket)
            
            elif msg_type == 'set_state':
                await self.broadcast_state_update(data.get('state', {}))

            elif msg_type == 'agent_command':
                await self.handle_agent_command(websocket, data)

            else:
                logger.warning(f"Unknown message type: {msg_type}")
        
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def handle_tts_request(self, websocket, data: Dict[str, Any]):
        """Handle TTS synthesis request"""
        text = data.get('text', '')
        emotion = data.get('emotion', 'neutral')
        
        logger.info(f"TTS request: '{text}' (emotion: {emotion})")
        
        try:
            # Synthesize speech
            audio_bytes = self.tts.synthesize(text, emotion)

            if audio_bytes:
                # Send complete WAV as a single base64 message so the
                # browser can decode a valid audio file in one shot.
                encoded = base64.b64encode(audio_bytes).decode('utf-8')
                await websocket.send(json.dumps({
                    'type': 'audio_data',
                    'data': encoded,
                    'format': 'wav',
                }))

            # Send completion message
            await websocket.send(json.dumps({
                'type': 'tts_complete'
            }))
        
        except Exception as e:
            logger.error(f"TTS error: {e}")
            await websocket.send(json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def send_system_status(self, websocket):
        """Send system status to client"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            status = {
                'cpu_usage': cpu_percent,
                'memory_usage': memory.percent,
                'memory_available_gb': memory.available / (1024 ** 3),
                'disk_usage': disk.percent,
                'disk_available_gb': disk.free / (1024 ** 3),
            }
            
            await websocket.send(json.dumps({
                'type': 'system_status',
                'status': status
            }))
        
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
    
    async def broadcast_state_update(self, state: Dict[str, Any]):
        """Broadcast state update to all clients"""
        message = json.dumps({
            'type': 'state_update',
            'state': state
        })
        
        # Send to all connected clients
        if self.clients:
            await asyncio.gather(
                *[client.send(message) for client in self.clients],
                return_exceptions=True
            )
    
    async def handle_agent_command(self, websocket, data: Dict[str, Any]):
        """Handle an agentic command routed from the frontend."""
        text = data.get('text', '').strip()
        if not text:
            await websocket.send(json.dumps({
                'type': 'agent_result',
                'success': False,
                'message': 'Empty command',
                'speak': 'I didn\'t catch that. Could you try again?',
            }))
            return

        logger.info(f"Agent command: '{text}'")

        agent = _get_agent_executor()
        if agent is None:
            await websocket.send(json.dumps({
                'type': 'agent_result',
                'success': False,
                'message': 'Agent executor unavailable',
                'speak': 'Sorry, the agent system is not available right now.',
            }))
            return

        try:
            # Run the synchronous executor in a thread to keep the event loop free
            result = await asyncio.to_thread(agent.execute, text)

            response = {
                'type': 'agent_result',
                'success': result.success,
                'message': result.message,
                'speak': result.speak,
                'data': result.data,
            }
            await websocket.send(json.dumps(response, default=str))

            # Auto-speak the result if TTS is available
            if result.speak:
                await self.handle_tts_request(websocket, {
                    'text': result.speak,
                    'emotion': 'neutral' if result.success else 'error',
                })

        except Exception as e:
            logger.error(f"Agent execution error: {e}")
            await websocket.send(json.dumps({
                'type': 'agent_result',
                'success': False,
                'message': f'Error: {e}',
                'speak': 'Sorry, something went wrong executing that command.',
            }))

    async def monitor_system(self):
        """Periodically monitor system and broadcast updates"""
        while self.monitoring:
            try:
                cpu_percent = psutil.cpu_percent(interval=1)
                
                # Determine activity based on CPU usage
                activity = 'idle'
                if cpu_percent > 80:
                    activity = 'thinking'
                elif cpu_percent > 50:
                    activity = 'processing'
                
                # Broadcast to all clients
                await self.broadcast_state_update({
                    'activity': activity,
                    'cpuLoad': cpu_percent / 100.0
                })
                
                await asyncio.sleep(5)
            
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(5)
    
    async def start(self):
        """Start the WebSocket server"""
        logger.info(f"Starting Avatar Bridge on {self.host}:{self.port}")
        
        # Start system monitoring
        asyncio.create_task(self.monitor_system())
        
        # Start WebSocket server
        async with websockets.serve(self.handle_client, self.host, self.port):
            logger.info(f"Avatar Bridge running on ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever
    
    def stop(self):
        """Stop the server"""
        self.monitoring = False


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Binary Avatar WebSocket Bridge")
    parser.add_argument("--host", default="localhost", help="WebSocket host")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port")
    parser.add_argument("--tts", choices=["coqui", "piper", "fallback"], 
                        default="coqui", help="TTS engine to use")
    
    args = parser.parse_args()
    
    server = AvatarBridgeServer(host=args.host, port=args.port, tts_engine=args.tts)
    
    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.stop()


if __name__ == "__main__":
    asyncio.run(main())
