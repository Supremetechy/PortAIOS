"""
Standalone STT (Speech-to-Text) Engine — No Browser Required

Cascade order:
  1. Whisper (OpenAI) — high-quality local transcription
  2. ALSA/sox record + Whisper — mic capture on Linux
  3. macOS dictation — built-in speech recognition
  4. stdin text input — always-available fallback

Each backend is tried at init time; the first one that works is used.
"""

import logging
import os
import platform
import subprocess
import tempfile
import sys
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger("AIOS.audio.stt")


class STTBackend(ABC):
    """Abstract STT backend."""
    name: str = "unknown"

    @abstractmethod
    def listen(self, timeout_seconds: int = 10) -> str:
        """Listen for speech and return transcribed text."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


# ---------------------------------------------------------------------------
# Backend implementations
# ---------------------------------------------------------------------------

class WhisperSTTBackend(STTBackend):
    """Uses OpenAI Whisper for local transcription with mic capture."""
    name = "whisper"

    def __init__(self, model_name: str = "base"):
        self._model_name = model_name
        self._model = None
        self._record_cmd = None

    def is_available(self) -> bool:
        try:
            import whisper  # noqa: F401
            # Also need a way to record audio
            self._record_cmd = self._find_record_command()
            return self._record_cmd is not None
        except ImportError:
            return False

    def _find_record_command(self) -> Optional[list]:
        """Find a command-line tool to record audio from the mic."""
        system = platform.system()

        if system == "Darwin":
            # macOS: use sox (if installed) or ffmpeg
            for cmd, args in [
                (["sox", "-d", "-t", "wav", "-r", "16000", "-c", "1"], ["sox"]),
                (["ffmpeg", "-f", "avfoundation", "-i", ":0", "-t"], ["ffmpeg"]),
            ]:
                try:
                    subprocess.run(
                        [args[0], "--version" if args[0] == "ffmpeg" else "--help"],
                        capture_output=True, timeout=3,
                    )
                    return cmd
                except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                    continue

        elif system == "Linux":
            # Linux: arecord (ALSA) or sox
            for cmd, test_args in [
                (["arecord", "-f", "S16_LE", "-r", "16000", "-c", "1", "-t", "wav"], ["arecord", "--help"]),
                (["sox", "-d", "-t", "wav", "-r", "16000", "-c", "1"], ["sox", "--help"]),
            ]:
                try:
                    subprocess.run(test_args, capture_output=True, timeout=3)
                    return cmd
                except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                    continue

        return None

    def _ensure_model(self):
        if self._model is None:
            import whisper
            self._model = whisper.load_model(self._model_name)

    def listen(self, timeout_seconds: int = 10) -> str:
        self._ensure_model()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name

        try:
            # Build record command with output path and duration
            cmd = list(self._record_cmd)
            system = platform.system()

            if "arecord" in cmd[0]:
                cmd.extend(["-d", str(timeout_seconds), wav_path])
            elif "sox" in cmd[0]:
                cmd.append(wav_path)
                cmd.extend(["trim", "0", str(timeout_seconds)])
            elif "ffmpeg" in cmd[0]:
                cmd.extend([str(timeout_seconds), wav_path, "-y"])

            logger.info(f"Recording {timeout_seconds}s of audio...")
            subprocess.run(cmd, capture_output=True, timeout=timeout_seconds + 5)

            # Transcribe
            result = self._model.transcribe(wav_path, language="en")
            text = result.get("text", "").strip()
            logger.info(f"Transcribed: {text}")
            return text
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass


class StdinSTTBackend(STTBackend):
    """Fallback: read text input from stdin."""
    name = "stdin"

    def is_available(self) -> bool:
        return True

    def listen(self, timeout_seconds: int = 10) -> str:
        try:
            text = input("aios> ").strip()
            return text
        except (EOFError, KeyboardInterrupt):
            return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class STTEngine:
    """
    Cascading STT engine. Tries backends in priority order.
    """

    def __init__(self, backend: Optional[STTBackend] = None):
        self.backend = backend or self._auto_detect()
        logger.info(f"STT engine: {self.backend.name}")

    def _auto_detect(self) -> STTBackend:
        candidates = [
            WhisperSTTBackend(),
            StdinSTTBackend(),
        ]
        for backend in candidates:
            try:
                if backend.is_available():
                    return backend
            except Exception:
                continue
        return StdinSTTBackend()

    def listen(self, timeout_seconds: int = 10) -> str:
        try:
            return self.backend.listen(timeout_seconds)
        except Exception as e:
            logger.error(f"STT ({self.backend.name}) failed: {e}")
            if self.backend.name != "stdin":
                return StdinSTTBackend().listen(timeout_seconds)
            return ""

    @property
    def name(self) -> str:
        return self.backend.name


def get_stt_engine(prefer: Optional[str] = None) -> STTEngine:
    """
    Get an STT engine, optionally forcing a specific backend.

    Parameters
    ----------
    prefer : str, optional
        Force: "whisper", "stdin"
    """
    if prefer:
        backends = {
            "whisper": WhisperSTTBackend,
            "stdin": StdinSTTBackend,
        }
        cls = backends.get(prefer.lower())
        if cls:
            backend = cls()
            if backend.is_available():
                return STTEngine(backend)
            raise RuntimeError(f"STT backend '{prefer}' is not available")
        raise ValueError(f"Unknown STT backend: {prefer}")
    return STTEngine()
