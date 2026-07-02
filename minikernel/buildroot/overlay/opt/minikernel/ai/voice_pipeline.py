"""
Voice Pipeline - Integrates STT and TTS from PortAIOS

Leverages existing whisper.cpp (STT) and Piper (TTS) implementations
"""

import logging
import sys
import os
from typing import Optional, Callable, Any
from pathlib import Path

# Add parent directory to path to import from kernel
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from kernel.audio.stt import STTEngine, WhisperSTTBackend, StdinSTTBackend
from kernel.audio.tts import TTSEngine, PiperTTSBackend, SilentTTSBackend

logger = logging.getLogger("MiniKernel.Voice")


class VoicePipeline:
    """
    Voice Pipeline for MiniKernel
    
    Integrates:
    - Speech-to-Text (Whisper.cpp)
    - Text-to-Speech (Piper TTS)
    - Streaming audio processing
    
    Reuses PortAIOS audio infrastructure
    """
    
    def __init__(
        self,
        stt_backend: Optional[str] = None,
        tts_backend: Optional[str] = None,
        model_path: Optional[str] = None
    ):
        self.stt_backend_name = stt_backend
        self.tts_backend_name = tts_backend
        self.model_path = model_path
        
        # Initialize engines
        self.stt_engine = self._init_stt()
        self.tts_engine = self._init_tts()
        
        # Callbacks
        self.on_speech_detected: Optional[Callable[[str], None]] = None
        self.on_synthesis_complete: Optional[Callable[[], None]] = None
        
        logger.info(f"Voice Pipeline initialized (STT={self.stt_engine.name}, TTS={self.tts_engine.name})")
    
    def _init_stt(self) -> STTEngine:
        """Initialize Speech-to-Text engine"""
        if self.stt_backend_name == "stdin":
            backend = StdinSTTBackend()
        elif self.stt_backend_name == "whisper":
            backend = WhisperSTTBackend(model_name="base")
        else:
            # Auto-detect
            if WhisperSTTBackend().is_available():
                backend = WhisperSTTBackend(model_name="base")
                logger.info("Using Whisper STT backend")
            else:
                logger.warning("Whisper not available, using stdin fallback")
                backend = StdinSTTBackend()
        
        return STTEngine(backend=backend)
    
    def _init_tts(self) -> TTSEngine:
        """Initialize Text-to-Speech engine"""
        if self.tts_backend_name == "silent":
            backend = SilentTTSBackend()
        elif self.tts_backend_name == "piper":
            backend = PiperTTSBackend(model_path=self.model_path)
        else:
            # Auto-detect
            if PiperTTSBackend().is_available():
                backend = PiperTTSBackend(model_path=self.model_path)
                logger.info("Using Piper TTS backend")
            else:
                logger.warning("Piper not available, using silent fallback")
                backend = SilentTTSBackend()
        
        return TTSEngine(backend=backend)
    
    def listen(self, timeout_seconds: int = 10) -> Optional[str]:
        """
        Listen for voice input
        
        Returns:
            Transcribed text or None if timeout/error
        """
        try:
            logger.debug("Listening for voice input...")
            text = self.stt_engine.listen(timeout_seconds=timeout_seconds)
            
            if text:
                logger.info(f"Voice input: '{text}'")
                
                # Trigger callback
                if self.on_speech_detected:
                    self.on_speech_detected(text)
                
                return text
            else:
                logger.debug("No speech detected")
                return None
                
        except Exception as e:
            logger.error(f"STT error: {e}")
            return None
    
    def speak(self, text: str) -> bool:
        """
        Speak text via TTS
        
        Args:
            text: Text to synthesize
            
        Returns:
            True if successful
        """
        try:
            logger.debug(f"Speaking: '{text}'")
            self.tts_engine.speak(text)
            
            # Trigger callback
            if self.on_synthesis_complete:
                self.on_synthesis_complete()
            
            return True
            
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return False
    
    def listen_continuous(
        self,
        callback: Callable[[str], None],
        timeout_seconds: int = 10
    ) -> None:
        """
        Continuous listening mode (blocking)
        
        Args:
            callback: Function to call with each transcription
            timeout_seconds: Timeout between utterances
        """
        logger.info("Starting continuous listening mode")
        
        try:
            while True:
                text = self.listen(timeout_seconds=timeout_seconds)
                if text:
                    callback(text)
        except KeyboardInterrupt:
            logger.info("Continuous listening stopped")
    
    def get_info(self) -> dict:
        """Get pipeline information"""
        return {
            "stt_backend": self.stt_engine.name,
            "tts_backend": self.tts_engine.name,
            "model_path": self.model_path,
            "stt_available": True,
            "tts_available": True
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # Create voice pipeline
    pipeline = VoicePipeline()
    
    # Test TTS
    pipeline.speak("Voice pipeline initialized")
    
    # Test STT
    print("Say something...")
    text = pipeline.listen(timeout_seconds=5)
    if text:
        print(f"You said: {text}")
        pipeline.speak(f"You said: {text}")
