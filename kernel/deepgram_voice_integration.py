"""
DeepGram Voice Integration Module

Provides high-level integration of DeepGram voice agent into PortAIOS.
This module wraps the DeepGram agent and integrates it with the existing
voice assistant infrastructure.
"""

import os
import logging
from typing import Optional, Callable, Dict, Any, TYPE_CHECKING
from pathlib import Path

# Load environment variables from .env file
from kernel.env_loader import ensure_env_loaded
ensure_env_loaded()

logger = logging.getLogger("AIOS.DeepGramIntegration")

try:
    from kernel.audio.deepgram_backend import DeepGramVoiceAgent, get_deepgram_agent
    DEEPGRAM_AVAILABLE = True
except ImportError:
    if TYPE_CHECKING:
        from typing import Any as DeepGramVoiceAgent  # pragma: no cover
        from typing import Any as get_deepgram_agent  # pragma: no cover
    else:
        DeepGramVoiceAgent = None  # type: ignore[assignment]
        get_deepgram_agent = None  # type: ignore[assignment]
    DEEPGRAM_AVAILABLE = False
    logger.warning("DeepGram backend not available")


class DeepGramVoiceIntegration:
    """
    High-level integration of DeepGram voice agent with PortAIOS.
    
    This class manages the DeepGram voice agent lifecycle and provides
    integration points with the existing voice assistant system.
    """
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        on_user_speech: Optional[Callable[[str], None]] = None,
        on_agent_response: Optional[Callable[[str], None]] = None,
        on_audio_output: Optional[Callable[[bytes], None]] = None,
    ):
        """
        Initialize DeepGram voice integration.
        
        Args:
            config_path: Path to config.json
            on_user_speech: Callback when user speech is transcribed
            on_agent_response: Callback when agent responds with text
            on_audio_output: Callback when agent produces audio
        """
        self.config_path = config_path
        self.on_user_speech = on_user_speech
        self.on_agent_response = on_agent_response
        self.on_audio_output = on_audio_output
        
        self._agent: Optional[DeepGramVoiceAgent] = None
        self._enabled = False
        self._fallback_mode = False
        
    def is_available(self) -> bool:
        """Check if DeepGram is available and configured."""
        if not DEEPGRAM_AVAILABLE:
            return False
        
        api_key = os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            logger.warning("DEEPGRAM_API_KEY not set. DeepGram voice agent unavailable.")
            return False
        
        return True
    
    def enable(self) -> bool:
        """
        Enable DeepGram voice agent.
        
        Returns:
            True if successfully enabled, False otherwise
        """
        if self._enabled:
            logger.info("DeepGram voice agent already enabled")
            return True
        
        if not self.is_available():
            logger.warning("DeepGram not available. Using fallback voice system.")
            self._fallback_mode = True
            return False
        
        try:
            # Create agent instance
            self._agent = get_deepgram_agent(
                config_path=self.config_path,
                on_response=self._handle_agent_response,
                on_audio=self._handle_audio_output,
            )
            
            if not self._agent:
                logger.error("Failed to create DeepGram agent")
                self._fallback_mode = True
                return False
            
            # Start the agent
            self._agent.start()  # type: ignore[union-attr]
            self._enabled = True
            logger.info("✅ DeepGram voice agent enabled")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable DeepGram agent: {e}", exc_info=True)
            self._fallback_mode = True
            return False
    
    def disable(self):
        """Disable DeepGram voice agent."""
        if not self._enabled:
            return
        
        if self._agent:
            try:
                self._agent.stop()
            except Exception as e:
                logger.error(f"Error stopping DeepGram agent: {e}")
            finally:
                self._agent = None
        
        self._enabled = False
        logger.info("DeepGram voice agent disabled")
    
    def _handle_agent_response(self, text: str):
        """Internal handler for agent text responses."""
        logger.info(f"Agent: {text}")
        
        if self.on_agent_response:
            try:
                self.on_agent_response(text)
            except Exception as e:
                logger.error(f"Error in agent response callback: {e}")
    
    def _handle_audio_output(self, audio_data: bytes):
        """Internal handler for agent audio output."""
        logger.debug(f"Received {len(audio_data)} bytes of audio")
        
        if self.on_audio_output:
            try:
                self.on_audio_output(audio_data)
            except Exception as e:
                logger.error(f"Error in audio output callback: {e}")
    
    def send_text(self, text: str):
        """
        Send text to the agent (for testing or text-based interaction).
        
        Args:
            text: Text to send to the agent
        """
        if not self._enabled or not self._agent:
            logger.warning("DeepGram agent not enabled")
            return
        if get_deepgram_agent is None:
            logger.warning("DeepGram backend not available")
            return
        
        try:
            self._agent.send_text(text)
        except Exception as e:
            logger.error(f"Error sending text to agent: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the DeepGram integration.
        
        Returns:
            Dictionary with status information
        """
        return {
            "available": self.is_available(),
            "enabled": self._enabled,
            "fallback_mode": self._fallback_mode,
            "agent_running": self._agent is not None and self._enabled,
        }
    
    def __enter__(self):
        """Context manager entry."""
        self.enable()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disable()


# Global singleton instance
_deepgram_integration: Optional[DeepGramVoiceIntegration] = None


def get_deepgram_integration(
    config_path: Optional[str] = None,
    **kwargs
) -> DeepGramVoiceIntegration:
    """
    Get or create the global DeepGram integration instance.
    
    Args:
        config_path: Path to config.json
        **kwargs: Additional arguments for DeepGramVoiceIntegration
    
    Returns:
        DeepGramVoiceIntegration instance
    """
    global _deepgram_integration
    
    if _deepgram_integration is None:
        _deepgram_integration = DeepGramVoiceIntegration(
            config_path=config_path,
            **kwargs
        )
    
    return _deepgram_integration


def setup_deepgram_for_eel(eel_module):
    """
    Setup DeepGram integration with Eel for web frontend.
    
    Args:
        eel_module: The Eel module to expose functions to
    """
    integration = get_deepgram_integration()
    
    @eel_module.expose
    def enable_deepgram_voice() -> Dict[str, Any]:
        """Enable DeepGram voice agent."""
        success = integration.enable()
        return integration.get_status()
    
    @eel_module.expose
    def disable_deepgram_voice():
        """Disable DeepGram voice agent."""
        integration.disable()
        return integration.get_status()
    
    @eel_module.expose
    def get_deepgram_status() -> Dict[str, Any]:
        """Get DeepGram agent status."""
        return integration.get_status()
    
    @eel_module.expose
    def send_text_to_deepgram(text: str):
        """Send text to DeepGram agent."""
        integration.send_text(text)
    
    logger.info("DeepGram Eel API registered")
