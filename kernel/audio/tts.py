"""
Standalone TTS Engine — No Browser Required

Cascade order:
  1. Piper TTS  — fast, local neural TTS binary
  2. Coqui TTS  — high-fidelity Python TTS library
  3. espeak-ng   — lightweight, available on most Linux distros
  4. macOS 'say' — built into macOS
  5. Silent       — log-only fallback (always works)

Each backend is tried at init time; the first one that works is used.
"""

import logging
import os
import platform
import subprocess
import tempfile
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger("AIOS.audio.tts")


class TTSBackend(ABC):
    """Abstract TTS backend."""
    name: str = "unknown"

    @abstractmethod
    def speak(self, text: str) -> None:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...


# ---------------------------------------------------------------------------
# Backend implementations
# ---------------------------------------------------------------------------

class PiperTTSBackend(TTSBackend):
    name = "piper"

    def __init__(self, model_path: Optional[str] = None):
        self._model_path = model_path

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["piper", "--version"],
                capture_output=True, timeout=3,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError, OSError):
            return False

    def speak(self, text: str) -> None:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name

        try:
            cmd = ["piper", "--output_file", wav_path]
            if self._model_path:
                cmd.extend(["--model", self._model_path])

            proc = subprocess.run(
                cmd, input=text.encode("utf-8"),
                capture_output=True, timeout=30,
            )
            if proc.returncode != 0:
                logger.warning(f"Piper TTS failed: {proc.stderr.decode()}")
                return

            self._play_wav(wav_path)
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass

    def _play_wav(self, path: str) -> None:
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.run(["afplay", path], timeout=30)
            elif system == "Linux":
                # Try aplay first, then paplay (PulseAudio)
                for player in ["aplay", "paplay", "pw-play"]:
                    try:
                        subprocess.run([player, path], timeout=30)
                        return
                    except FileNotFoundError:
                        continue
                logger.warning("No audio player found (tried aplay, paplay, pw-play)")
            elif system == "Windows":
                subprocess.run(
                    ["powershell", "-c",
                     f"(New-Object Media.SoundPlayer '{path}').PlaySync();"],
                    timeout=30,
                )
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.warning(f"Audio playback failed: {e}")


class CoquiTTSBackend(TTSBackend):
    name = "coqui"

    def __init__(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC"):
        self._model_name = model_name
        self._tts = None

    def is_available(self) -> bool:
        try:
            from TTS.api import TTS  # noqa: F401
            return True
        except Exception:
            return False

    def _ensure_loaded(self):
        if self._tts is None:
            from TTS.api import TTS
            self._tts = TTS(self._model_name)

    def speak(self, text: str) -> None:
        self._ensure_loaded()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name

        try:
            self._tts.tts_to_file(text=text, file_path=wav_path)
            PiperTTSBackend._play_wav(None, wav_path)  # reuse wav player
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass


class EspeakTTSBackend(TTSBackend):
    name = "espeak"

    def is_available(self) -> bool:
        for cmd in ["espeak-ng", "espeak"]:
            try:
                result = subprocess.run(
                    [cmd, "--version"], capture_output=True, timeout=3,
                )
                if result.returncode == 0:
                    self._cmd = cmd
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired, PermissionError, OSError):
                continue
        return False

    def speak(self, text: str) -> None:
        try:
            subprocess.run(
                [self._cmd, text],
                capture_output=True, timeout=30,
            )
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.warning(f"espeak failed: {e}")


class MacOSSayBackend(TTSBackend):
    name = "macos-say"

    def is_available(self) -> bool:
        return platform.system() == "Darwin"

    def speak(self, text: str) -> None:
        try:
            subprocess.run(["say", text], timeout=60)
        except (subprocess.TimeoutExpired, OSError) as e:
            logger.warning(f"macOS say failed: {e}")


class SilentTTSBackend(TTSBackend):
    name = "silent"

    def is_available(self) -> bool:
        return True

    def speak(self, text: str) -> None:
        logger.info(f"[TTS-silent] {text}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class TTSEngine:
    """
    Cascading TTS engine. Tries backends in priority order and uses
    the first one that works.
    """

    def __init__(self, backend: Optional[TTSBackend] = None):
        self.backend = backend or self._auto_detect()
        logger.info(f"TTS engine: {self.backend.name}")

    def _auto_detect(self) -> TTSBackend:
        candidates = [
            PiperTTSBackend(),
            CoquiTTSBackend(),
            EspeakTTSBackend(),
            MacOSSayBackend(),
            SilentTTSBackend(),
        ]
        for backend in candidates:
            try:
                if backend.is_available():
                    return backend
            except Exception:
                continue
        return SilentTTSBackend()

    def speak(self, text: str) -> None:
        try:
            self.backend.speak(text)
        except Exception as e:
            logger.error(f"TTS ({self.backend.name}) failed: {e}")
            # Fall through to silent
            if self.backend.name != "silent":
                SilentTTSBackend().speak(text)

    @property
    def name(self) -> str:
        return self.backend.name


def get_tts_engine(prefer: Optional[str] = None) -> TTSEngine:
    """
    Get a TTS engine, optionally forcing a specific backend.

    Parameters
    ----------
    prefer : str, optional
        Force: "piper", "coqui", "espeak", "macos", "silent"
    """
    if prefer:
        backends = {
            "piper": PiperTTSBackend,
            "coqui": CoquiTTSBackend,
            "espeak": EspeakTTSBackend,
            "macos": MacOSSayBackend,
            "silent": SilentTTSBackend,
        }
        cls = backends.get(prefer.lower())
        if cls:
            backend = cls()
            if backend.is_available():
                return TTSEngine(backend)
            raise RuntimeError(f"TTS backend '{prefer}' is not available")
        raise ValueError(f"Unknown TTS backend: {prefer}")
    return TTSEngine()
