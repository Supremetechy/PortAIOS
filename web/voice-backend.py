#!/usr/bin/env python3
"""
Voice Backend for AIOS Onboarding
Extends avatar-bridge.py with voice command processing
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional

# Speech recognition backend (optional advanced features)
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False
    logging.warning("speech_recognition not available (pip install SpeechRecognition)")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VoiceBackend")


class VoiceCommandProcessor:
    """Process and route voice commands"""
    
    def __init__(self):
        self.command_handlers = {}
        self.context = {}
        self.awaiting_response = False
        self.expected_response_type = None
        
    def register_handler(self, command_type: str, handler):
        """Register a command handler"""
        self.command_handlers[command_type] = handler
        logger.info(f"Registered handler for: {command_type}")
    
    async def process_command(self, command: str, user_id: str = None) -> Dict[str, Any]:
        """Process a voice command and return action"""
        
        logger.info(f"Processing command: '{command}'")
        
        # Parse command
        parsed = self.parse_command(command)
        logger.info(f"Parsed: {parsed}")
        
        # If awaiting specific response
        if self.awaiting_response:
            return await self.handle_response(parsed, command)
        
        # Route to appropriate handler
        handler = self.command_handlers.get(parsed['type'])
        
        if handler:
            return await handler(parsed, command, self.context)
        
        # Default handler
        return {
            'action': 'unknown',
            'message': 'Command not recognized',
            'command': command
        }
    
    def parse_command(self, command: str) -> Dict[str, Any]:
        """Parse command into type and parameters"""
        
        lower_cmd = command.lower().strip()
        
        # Navigation commands
        if any(word in lower_cmd for word in ['next', 'continue', 'proceed']):
            return {'type': 'next', 'params': []}
        
        if any(word in lower_cmd for word in ['back', 'previous', 'return']):
            return {'type': 'back', 'params': []}
        
        if any(word in lower_cmd for word in ['skip']):
            return {'type': 'skip', 'params': []}
        
        # Confirmation
        if any(word in lower_cmd for word in ['yes', 'yeah', 'yep', 'sure', 'okay']):
            return {'type': 'yes', 'params': []}
        
        if any(word in lower_cmd for word in ['no', 'nope', 'nah']):
            return {'type': 'no', 'params': []}
        
        # Help
        if any(word in lower_cmd for word in ['help', 'what', 'how']):
            return {'type': 'help', 'params': []}
        
        # Repeat
        if any(word in lower_cmd for word in ['repeat', 'again', 'say again']):
            return {'type': 'repeat', 'params': []}
        
        # Input (e.g., "type John Doe")
        if lower_cmd.startswith('type ') or lower_cmd.startswith('enter '):
            value = command.split(None, 1)[1] if ' ' in command else ''
            return {'type': 'input', 'params': [value]}
        
        # Custom/unknown
        return {'type': 'custom', 'params': [command]}
    
    async def handle_response(self, parsed: Dict, raw_command: str) -> Dict[str, Any]:
        """Handle response when awaiting specific input"""
        
        if self.expected_response_type == 'yes_no':
            if parsed['type'] == 'yes':
                self.awaiting_response = False
                self.expected_response_type = None
                return {'action': 'response_yes', 'value': True}
            elif parsed['type'] == 'no':
                self.awaiting_response = False
                self.expected_response_type = None
                return {'action': 'response_no', 'value': False}
            else:
                return {
                    'action': 'clarify',
                    'message': 'Please say yes or no'
                }
        
        elif self.expected_response_type == 'text':
            self.awaiting_response = False
            self.expected_response_type = None
            return {
                'action': 'response_text',
                'value': raw_command
            }
        
        return {'action': 'unknown'}
    
    def request_response(self, response_type: str):
        """Request a specific type of voice response"""
        self.awaiting_response = True
        self.expected_response_type = response_type
        logger.info(f"Requesting {response_type} response")


class AdvancedVoiceRecognition:
    """
    Advanced voice recognition using offline models
    Optional enhancement over Web Speech API
    """
    
    def __init__(self):
        if not SPEECH_RECOGNITION_AVAILABLE:
            raise RuntimeError("speech_recognition library not available")
        
        self.recognizer = sr.Recognizer()
        self.microphone = None
        
    def recognize_from_audio(self, audio_data: bytes) -> Optional[str]:
        """Recognize speech from audio bytes"""
        try:
            # Convert bytes to AudioData
            audio = sr.AudioData(audio_data, 16000, 2)
            
            # Try multiple engines
            try:
                # Google Speech Recognition (requires internet)
                text = self.recognizer.recognize_google(audio)
                return text
            except sr.UnknownValueError:
                logger.warning("Could not understand audio")
                return None
            except sr.RequestError as e:
                logger.error(f"Recognition service error: {e}")
                
                # Fallback to offline Sphinx
                try:
                    text = self.recognizer.recognize_sphinx(audio)
                    return text
                except:
                    return None
        
        except Exception as e:
            logger.error(f"Recognition error: {e}")
            return None
    
    def listen_from_microphone(self, timeout: int = 5) -> Optional[str]:
        """Listen directly from microphone (for testing)"""
        if not self.microphone:
            self.microphone = sr.Microphone()
        
        try:
            with self.microphone as source:
                logger.info("Listening from microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=timeout)
                
            logger.info("Processing audio...")
            text = self.recognizer.recognize_google(audio)
            return text
        
        except sr.WaitTimeoutError:
            logger.warning("Listening timeout")
            return None
        except sr.UnknownValueError:
            logger.warning("Could not understand audio")
            return None
        except Exception as e:
            logger.error(f"Microphone error: {e}")
            return None


# Default command handlers
async def handle_next(parsed, command, context):
    """Handle next command"""
    return {
        'action': 'navigate',
        'direction': 'next',
        'message': 'Moving to next step'
    }

async def handle_back(parsed, command, context):
    """Handle back command"""
    return {
        'action': 'navigate',
        'direction': 'back',
        'message': 'Going back'
    }

async def handle_help(parsed, command, context):
    """Handle help command"""
    return {
        'action': 'help',
        'message': 'Available commands: next, back, yes, no, repeat, type [text]'
    }

async def handle_repeat(parsed, command, context):
    """Handle repeat command"""
    return {
        'action': 'repeat',
        'message': 'Repeating current step'
    }

async def handle_input(parsed, command, context):
    """Handle input command"""
    value = parsed['params'][0] if parsed['params'] else ''
    return {
        'action': 'input',
        'value': value,
        'message': f'Input received: {value}'
    }


# Integration with WebSocket server
class VoiceWebSocketHandler:
    """Handle voice-related WebSocket messages"""
    
    def __init__(self, command_processor: VoiceCommandProcessor):
        self.processor = command_processor
    
    async def handle_message(self, message_type: str, data: Dict, websocket):
        """Handle voice-related WebSocket message"""
        
        if message_type == 'voice_command':
            # Process voice command
            command = data.get('command', '')
            result = await self.processor.process_command(command)
            
            # Send result back to client
            await websocket.send(json.dumps({
                'type': 'voice_command_result',
                'result': result
            }))
        
        elif message_type == 'request_voice_input':
            # Request specific voice input from user
            response_type = data.get('response_type', 'text')
            self.processor.request_response(response_type)
            
            await websocket.send(json.dumps({
                'type': 'voice_input_requested',
                'response_type': response_type
            }))
        
        elif message_type == 'voice_audio_data':
            # Process audio data (if using advanced recognition)
            audio_data = data.get('audio', '')
            # Handle audio processing here
            pass


def create_voice_processor():
    """Create and configure voice command processor"""
    
    processor = VoiceCommandProcessor()
    
    # Register default handlers
    processor.register_handler('next', handle_next)
    processor.register_handler('back', handle_back)
    processor.register_handler('help', handle_help)
    processor.register_handler('repeat', handle_repeat)
    processor.register_handler('input', handle_input)
    
    return processor


# Eel integration functions
def setup_eel_voice_functions(eel_module):
    """Setup Eel-exposed voice functions"""
    
    processor = create_voice_processor()
    
    @eel_module.expose
    def process_voice_command(command: str):
        """Process voice command from frontend"""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(processor.process_command(command))
        loop.close()
        return result
    
    @eel_module.expose
    def request_voice_input(response_type: str = 'text'):
        """Request voice input from user"""
        processor.request_response(response_type)
        return {'status': 'ok', 'awaiting': response_type}
    
    return processor


# CLI testing
if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("AIOS Voice Backend - Test Mode")
    print("=" * 60)
    
    processor = create_voice_processor()
    
    # Test basic commands
    test_commands = [
        "next",
        "go back",
        "yes",
        "help",
        "type John Doe",
        "repeat that"
    ]
    
    async def test():
        print("\nTesting command parsing:\n")
        
        for cmd in test_commands:
            result = await processor.process_command(cmd)
            print(f"Command: '{cmd}'")
            print(f"Result: {result}")
            print()
    
    asyncio.run(test())
    
    # Interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        print("\n" + "=" * 60)
        print("Interactive Mode - Enter commands (Ctrl+C to exit)")
        print("=" * 60)
        
        async def interactive():
            while True:
                try:
                    cmd = input("\nYou: ")
                    if cmd.lower() in ['quit', 'exit']:
                        break
                    
                    result = await processor.process_command(cmd)
                    print(f"Result: {result}")
                
                except KeyboardInterrupt:
                    break
        
        asyncio.run(interactive())
    
    # Microphone test
    if len(sys.argv) > 1 and sys.argv[1] == '--mic':
        if SPEECH_RECOGNITION_AVAILABLE:
            print("\n" + "=" * 60)
            print("Microphone Test - Speak now!")
            print("=" * 60)
            
            recognizer = AdvancedVoiceRecognition()
            
            async def mic_test():
                text = recognizer.listen_from_microphone(timeout=10)
                
                if text:
                    print(f"\nHeard: '{text}'")
                    result = await processor.process_command(text)
                    print(f"Result: {result}")
                else:
                    print("No speech detected")
            
            asyncio.run(mic_test())
        else:
            print("speech_recognition not available")
            print("Install with: pip install SpeechRecognition pyaudio")
