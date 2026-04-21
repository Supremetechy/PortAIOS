"""
AIOS Audio Subsystem

Standalone TTS and STT engines that work without a browser or
Web Speech API. Each engine cascades through available backends
from highest to lowest quality.
"""

from kernel.audio.tts import TTSEngine, get_tts_engine
from kernel.audio.stt import STTEngine, get_stt_engine

__all__ = ["TTSEngine", "get_tts_engine", "STTEngine", "get_stt_engine"]
