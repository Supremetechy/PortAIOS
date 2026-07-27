"""
DeepGram Voice Agent Backend for PortAIOS

Integrates DeepGram's Agent API for streaming voice interactions with
STT (Speech-to-Text), LLM thinking, and TTS (Text-to-Speech) in a single pipeline.
"""

import os
import json
import logging
import asyncio
import threading
import tempfile
from typing import Optional, Dict, Any, Callable
from pathlib import Path

# Load environment variables from .env file
from kernel.env_loader import ensure_env_loaded
ensure_env_loaded()

logger = logging.getLogger("AIOS.audio.deepgram")

try:
    from deepgram import DeepgramClient
    from deepgram.agent.v1.types import (
        AgentV1Settings, AgentV1SettingsAgent,
        AgentV1SettingsAgentListen, AgentV1SettingsAgentListenProvider_V1,
        AgentV1SettingsAudio, AgentV1SettingsAudioInput, AgentV1SettingsAudioOutput,
    )
    from deepgram.types.think_settings_v1 import ThinkSettingsV1
    from deepgram.types.think_settings_v1provider import (
        ThinkSettingsV1Provider_OpenAi,
        ThinkSettingsV1Provider_Anthropic,
        ThinkSettingsV1Provider_Google,
    )
    from deepgram.types.speak_settings_v1 import SpeakSettingsV1
    from deepgram.types.speak_settings_v1provider import SpeakSettingsV1Provider_Deepgram
    DEEPGRAM_AVAILABLE = True
except ImportError:
    DEEPGRAM_AVAILABLE = False
    logger.warning("DeepGram SDK not available. Install with: pip install deepgram-sdk")


class DeepGramVoiceAgent:
    """
    Unified voice agent using DeepGram's Agent API.
    
    Handles the complete voice interaction pipeline:
    - Listen (STT): DeepGram Nova or Flux models
    - Think (LLM): OpenAI, Anthropic, or Google models
    - Speak (TTS): DeepGram Aura voices
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        api_key: Optional[str] = None,
        on_response: Optional[Callable[[str], None]] = None,
        on_audio: Optional[Callable[[bytes], None]] = None,
    ):
        """
        Initialize DeepGram voice agent.
        
        Args:
            config_path: Path to config.json file
            api_key: DeepGram API key (or set DEEPGRAM_API_KEY env var)
            on_response: Callback for text responses from the agent
            on_audio: Callback for audio chunks from TTS
        """
        if not DEEPGRAM_AVAILABLE:
            raise ImportError("DeepGram SDK is required. Install with: pip install deepgram-sdk")
        
        self.api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            logger.warning("No DeepGram API key found. Set DEEPGRAM_API_KEY environment variable.")
        
        self.config = self._load_config(config_path)
        self.on_response = on_response
        self.on_audio = on_audio
        
        self.client = DeepgramClient(api_key=self.api_key) if self.api_key else None
        self.agent = None
        self._loop = None
        self._thread = None
        self._running = False
        
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from config.json file."""
        if config_path is None:
            # Default to config.json in project root
            config_path = Path(__file__).parent.parent.parent / "config.json"
        
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}. Using defaults.")
            return self._get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file: {e}. Using defaults.")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "audio": {
                "input": {
                    "encoding": "linear16",
                    "sample_rate": 48000
                },
                "output": {
                    "encoding": "linear16",
                    "sample_rate": 24000,
                    "container": "none"
                }
            },
            "agent": {
                "listen": {
                    "provider": {
                        "type": "deepgram",
                        "model": "nova-3"
                    }
                },
                "think": {
                    "provider": {
                        "type": "open_ai",
                        "model": "gpt-4o-mini"
                    },
                    "prompt": "You are a helpful AI assistant."
                },
                "speak": {
                    "provider": {
                        "type": "deepgram",
                        "model": "aura-2-odysseus-en"
                    }
                }
            }
        }
    
    def _build_settings(self) -> AgentV1Settings:
        """Build DeepGram agent settings from config."""
        config = self.config
        
        # Audio settings
        audio_config = config.get("audio", {})
        input_config = audio_config.get("input", {})
        output_config = audio_config.get("output", {})
        
        audio_settings = AgentV1SettingsAudio(
            input=AgentV1SettingsAudioInput(
                encoding=input_config.get("encoding", "linear16"),
                sample_rate=input_config.get("sample_rate", 48000)
            ),
            output=AgentV1SettingsAudioOutput(
                encoding=output_config.get("encoding", "linear16"),
                sample_rate=output_config.get("sample_rate", 24000),
                container=output_config.get("container", "none")
            )
        )
        
        # Agent settings
        agent_config = config.get("agent", {})
        
        # Listen (STT) settings
        listen_config = agent_config.get("listen", {}).get("provider", {})
        listen_provider = AgentV1SettingsAgentListenProvider_V1(
            type=listen_config.get("type", "deepgram"),
            model=listen_config.get("model", "nova-3")
        )
        
        # Think (LLM) settings
        think_config = agent_config.get("think", {})
        think_provider_config = think_config.get("provider", {})
        provider_type = think_provider_config.get("type", "open_ai")
        
        # Select appropriate provider based on type
        if provider_type == "anthropic":
            think_provider = ThinkSettingsV1Provider_Anthropic(
                type="anthropic",
                model=think_provider_config.get("model", "claude-3-5-sonnet-20241022")
            )
        elif provider_type == "google":
            think_provider = ThinkSettingsV1Provider_Google(
                type="google",
                model=think_provider_config.get("model", "gemini-2.0-flash-exp")
            )
        else:  # default to OpenAI
            think_provider = ThinkSettingsV1Provider_OpenAi(
                type="open_ai",
                model=think_provider_config.get("model", "gpt-4o-mini")
            )
        
        # Speak (TTS) settings
        speak_config = agent_config.get("speak", {}).get("provider", {})
        speak_provider = SpeakSettingsV1Provider_Deepgram(
            type="deepgram",
            model=speak_config.get("model", "aura-2-odysseus-en")
        )
        
        return AgentV1Settings(
            audio=audio_settings,
            agent=AgentV1SettingsAgent(
                listen=AgentV1SettingsAgentListen(provider=listen_provider),  # type: ignore[arg-type]
                think=ThinkSettingsV1(
                    provider=think_provider,
                    prompt=think_config.get("prompt", "You are a helpful AI assistant.")
                ),
                speak=SpeakSettingsV1(provider=speak_provider)
            )
        )
    
    def is_available(self) -> bool:
        """Check if DeepGram backend is available."""
        return DEEPGRAM_AVAILABLE and self.client is not None
    
    async def _run_agent_async(self):
        """Async event loop for the DeepGram agent."""
        if not self.client:
            logger.error("DeepGram client not initialized")
            return
        
        try:
            settings = self._build_settings()
            
            async with self.client.agent.v1.connect() as agent:
                self.agent = agent
                
                # Send initial settings
                await agent.send_settings(settings)
                
                # Start listening
                await agent.start_listening()
                
                logger.info("DeepGram agent connected and listening")
                
                # Event handlers
                async for event in agent:
                    if hasattr(event, 'type'):
                        if event.type == "UserStartedSpeaking":
                            logger.debug("User started speaking")
                        
                        elif event.type == "UserStoppedSpeaking":
                            logger.debug("User stopped speaking")
                        
                        elif event.type == "AgentThinking":
                            logger.debug("Agent is thinking...")
                        
                        elif event.type == "AgentStartedSpeaking":
                            logger.debug("Agent started speaking")
                        
                        elif event.type == "AgentStoppedSpeaking":
                            logger.debug("Agent stopped speaking")
                        
                        elif event.type == "Transcript":
                            # User transcript (STT result)
                            if hasattr(event, 'text'):
                                logger.info(f"User said: {event.text}")
                        
                        elif event.type == "Response":
                            # Agent text response
                            if hasattr(event, 'text'):
                                logger.info(f"Agent response: {event.text}")
                                if self.on_response:
                                    self.on_response(event.text)
                        
                        elif event.type == "Audio":
                            # Agent audio (TTS output)
                            if hasattr(event, 'data') and self.on_audio:
                                self.on_audio(event.data)
                        
                        elif event.type == "Error":
                            logger.error(f"Agent error: {event}")
                    
                    if not self._running:
                        break
                        
        except Exception as e:
            logger.error(f"DeepGram agent error: {e}", exc_info=True)
        finally:
            self.agent = None
    
    def start(self):
        """Start the DeepGram voice agent in a background thread."""
        if self._running:
            logger.warning("Agent already running")
            return
        
        if not self.is_available():
            logger.error("DeepGram agent not available")
            return
        
        self._running = True
        
        def _run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(self._run_agent_async())
            finally:
                self._loop.close()
                self._loop = None
        
        self._thread = threading.Thread(target=_run_loop, daemon=True)
        self._thread.start()
        logger.info("DeepGram voice agent started")
    
    def stop(self):
        """Stop the DeepGram voice agent."""
        if not self._running:
            return
        
        self._running = False
        
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        
        logger.info("DeepGram voice agent stopped")
    
    def send_text(self, text: str):
        """
        Send text to the agent (for testing or mixed-mode interaction).
        
        Args:
            text: Text to send to the agent
        """
        if not self.agent:
            logger.error("Agent not connected")
            return
        
        # This would require async handling
        asyncio.run_coroutine_threadsafe(
            self.agent.send_text(text),
            self._loop
        )
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


def get_deepgram_agent(**kwargs) -> Optional[DeepGramVoiceAgent]:
    """
    Factory function to create a DeepGram voice agent.
    
    Returns None if DeepGram is not available or not configured.
    """
    if not DEEPGRAM_AVAILABLE:
        logger.warning("DeepGram SDK not available")
        return None
    
    api_key = kwargs.get('api_key') or os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        logger.warning("No DeepGram API key configured")
        return None
    
    try:
        return DeepGramVoiceAgent(**kwargs)
    except Exception as e:
        logger.error(f"Failed to create DeepGram agent: {e}")
        return None
