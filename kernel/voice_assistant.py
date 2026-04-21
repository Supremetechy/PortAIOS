"""
AI-OS Voice Onboarding Assistant

Guides users through first-boot setup and day-to-day operation with
synthesized speech and voice-command input. Designed to degrade gracefully:
when no TTS/STT backend is available, prompts fall back to stdout/stdin so
the same guide flow still runs on minimal bare-metal images.

Typical usage:

    from kernel.voice_assistant import VoiceOnboardingAssistant
    assistant = VoiceOnboardingAssistant()
    assistant.run_interactive_guide()
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional


# --- Backend capability probes ---------------------------------------------

def _probe_pyttsx3():
    try:
        import pyttsx3  # type: ignore
        return pyttsx3
    except Exception:
        return None


def _probe_coqui_tts():
    try:
        from TTS.api import TTS  # type: ignore
        return TTS
    except Exception:
        return None


def _probe_speech_recognition():
    try:
        import speech_recognition as sr  # type: ignore
        return sr
    except Exception:
        return None


def _probe_whisper():
    try:
        import whisper  # type: ignore
        return whisper
    except Exception:
        return None


def _probe_sounddevice():
    try:
        import sounddevice as sd  # type: ignore
        return sd
    except Exception:
        return None


# --- TTS backends -----------------------------------------------------------

class TTSBackend:
    name: str = "base"
    available: bool = False

    def speak(self, text: str) -> None:
        raise NotImplementedError


class Pyttsx3Backend(TTSBackend):
    name = "pyttsx3"

    def __init__(self) -> None:
        self._engine = None
        self._pyttsx3 = _probe_pyttsx3()
        self.available = self._pyttsx3 is not None
        if self.available:
            try:
                self._engine = self._pyttsx3.init()
                self._engine.setProperty("rate", 175)
            except Exception:
                self.available = False
                self._engine = None

    def speak(self, text: str) -> None:
        if not self._engine:
            raise RuntimeError("pyttsx3 engine unavailable")
        self._engine.say(text)
        self._engine.runAndWait()


class CoquiBackend(TTSBackend):
    name = "coqui"

    def __init__(self, model_name: str = "tts_models/en/ljspeech/tacotron2-DDC") -> None:
        tts_cls = _probe_coqui_tts()
        self.available = tts_cls is not None
        self._tts = None
        if self.available:
            try:
                self._tts = tts_cls(model_name)
            except Exception:
                self.available = False

    def speak(self, text: str) -> None:
        if not self._tts:
            raise RuntimeError("Coqui TTS unavailable")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        try:
            self._tts.tts_to_file(text=text, file_path=wav_path)
            _play_wav(wav_path)
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass


class SystemSayBackend(TTSBackend):
    """macOS `say` / Linux `espeak` / Windows SAPI fallback."""
    name = "system"

    def __init__(self) -> None:
        self._cmd: Optional[List[str]] = None
        if platform.system() == "Darwin" and shutil.which("say"):
            self._cmd = ["say"]
        elif shutil.which("espeak-ng"):
            self._cmd = ["espeak-ng"]
        elif shutil.which("espeak"):
            self._cmd = ["espeak"]
        elif platform.system() == "Windows":
            self._cmd = ["powershell", "-Command"]
        self.available = self._cmd is not None

    def speak(self, text: str) -> None:
        if not self._cmd:
            raise RuntimeError("no system TTS")
        if self._cmd[0] == "powershell":
            escaped = text.replace("'", "''")
            script = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{escaped}')"
            subprocess.run(["powershell", "-Command", script], check=False)
        else:
            subprocess.run(self._cmd + [text], check=False)


class PiperWebSocketBackend(TTSBackend):
    """Sends text to kernel/piper_viseme_server.py over WebSocket.

    Returns synthesized audio + phoneme timeline. Plays the WAV locally
    and (when the GUI is running) pushes the viseme timeline for avatar
    lip-sync via an optional callback.
    """
    name = "piper"

    def __init__(
        self,
        url: str = "ws://127.0.0.1:8765",
        on_visemes: Optional[Callable] = None,
    ) -> None:
        self._url = url
        self._on_visemes = on_visemes
        self.available = False
        try:
            import websockets  # noqa: F401
            self.available = True
        except ImportError:
            pass

    def speak(self, text: str) -> None:
        import asyncio
        import json as _json
        import base64 as _b64

        async def _send():
            try:
                import websockets
            except ImportError:
                raise RuntimeError("websockets not installed")
            async with websockets.connect(self._url) as ws:
                uid = f"u_{id(text)}"
                await ws.send(_json.dumps({
                    "utterance_id": uid, "text": text,
                }))
                resp = _json.loads(await ws.recv())
                if "error" in resp:
                    raise RuntimeError(resp["error"])
                wav_bytes = _b64.b64decode(resp["audio"])
                if self._on_visemes and "phonemes" in resp:
                    self._on_visemes(resp["phonemes"], wav_bytes)
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(wav_bytes)
                    wav_path = f.name
                try:
                    _play_wav(wav_path)
                finally:
                    try:
                        os.unlink(wav_path)
                    except OSError:
                        pass

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                pool.submit(asyncio.run, _send()).result()
        else:
            asyncio.run(_send())


class StdoutBackend(TTSBackend):
    """Last-resort fallback: print the spoken line."""
    name = "stdout"
    available = True

    def speak(self, text: str) -> None:
        print(f"[VOICE] {text}")


def _play_wav(path: str) -> None:
    system = platform.system()
    if system == "Darwin" and shutil.which("afplay"):
        subprocess.run(["afplay", path], check=False)
    elif system == "Linux":
        for player in ("aplay", "paplay", "play"):
            if shutil.which(player):
                subprocess.run([player, path], check=False)
                return
    elif system == "Windows":
        subprocess.run(
            ["powershell", "-Command",
             f"(New-Object Media.SoundPlayer '{path}').PlaySync();"],
            check=False,
        )


# --- STT backends -----------------------------------------------------------

class STTBackend:
    name: str = "base"
    available: bool = False

    def listen_once(self, timeout: float = 6.0) -> Optional[str]:
        raise NotImplementedError


class SpeechRecognitionBackend(STTBackend):
    name = "speech_recognition"

    def __init__(self) -> None:
        sr = _probe_speech_recognition()
        self._sr = sr
        self.available = sr is not None
        self._recognizer = None
        self._mic = None
        if self.available:
            try:
                self._recognizer = sr.Recognizer()
                self._mic = sr.Microphone()
                with self._mic as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
            except Exception:
                self.available = False
                self._recognizer = None
                self._mic = None

    def listen_once(self, timeout: float = 6.0) -> Optional[str]:
        if not (self._recognizer and self._mic):
            return None
        try:
            with self._mic as source:
                audio = self._recognizer.listen(source, timeout=timeout, phrase_time_limit=timeout)
            try:
                return self._recognizer.recognize_google(audio)  # type: ignore[attr-defined]
            except Exception:
                try:
                    return self._recognizer.recognize_sphinx(audio)  # type: ignore[attr-defined]
                except Exception:
                    return None
        except Exception:
            return None


class WhisperMicBackend(STTBackend):
    """Captures a short clip with sounddevice and transcribes via whisper."""
    name = "whisper"

    def __init__(self, model_name: str = "base", sample_rate: int = 16000) -> None:
        whisper_mod = _probe_whisper()
        sd = _probe_sounddevice()
        self.available = bool(whisper_mod and sd)
        self._whisper = whisper_mod
        self._sd = sd
        self._model = None
        self._rate = sample_rate
        if self.available:
            try:
                self._model = whisper_mod.load_model(model_name)
            except Exception:
                self.available = False

    def listen_once(self, timeout: float = 6.0) -> Optional[str]:
        if not (self._model and self._sd):
            return None
        try:
            import numpy as np  # type: ignore
            duration = max(1.0, min(timeout, 15.0))
            audio = self._sd.rec(int(duration * self._rate),
                                 samplerate=self._rate, channels=1, dtype="float32")
            self._sd.wait()
            flat = np.asarray(audio, dtype="float32").flatten()
            result = self._model.transcribe(flat, language="en")
            text = (result.get("text") or "").strip()
            return text or None
        except Exception:
            return None


class StdinBackend(STTBackend):
    """Last-resort fallback: read a line from stdin (headless CI, SSH)."""
    name = "stdin"
    available = True

    def listen_once(self, timeout: float = 6.0) -> Optional[str]:
        try:
            line = input("(voice) say something > ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        return line or None


# --- Onboarding script ------------------------------------------------------

@dataclass
class VoiceStep:
    key: str
    title: str
    prompt: str
    hints: List[str] = field(default_factory=list)


DEFAULT_SCRIPT: List[VoiceStep] = [
    VoiceStep(
        key="welcome",
        title="Welcome",
        prompt=(
            "Welcome to AI-OS. I am your onboarding assistant. "
            "I will walk you through setup using voice. "
            "Say 'next' to continue, 'repeat' to hear a step again, "
            "'skip' to move past a step, or 'help' at any time."
        ),
        hints=["next", "repeat", "skip", "help"],
    ),
    VoiceStep(
        key="hardware",
        title="Hardware Detection",
        prompt=(
            "First I will detect your hardware: CPUs, GPUs, memory, and storage. "
            "Say 'detect' to scan now, or 'next' to accept the existing profile."
        ),
        hints=["detect", "next", "skip"],
    ),
    VoiceStep(
        key="gpu",
        title="GPU Configuration",
        prompt=(
            "If a GPU is present, I can enable CUDA, ROCm, or Metal acceleration "
            "for AI workloads. Say 'enable GPU' to turn acceleration on, "
            "or 'disable GPU' to keep CPU only."
        ),
        hints=["enable GPU", "disable GPU", "next", "skip"],
    ),
    VoiceStep(
        key="network",
        title="Network Setup",
        prompt=(
            "Next, network configuration. AI-OS can join a local network for "
            "distributed training and remote model access. "
            "Say 'configure network' to set this up, or 'skip' to defer."
        ),
        hints=["configure network", "skip", "next"],
    ),
    VoiceStep(
        key="security",
        title="Security & Identity",
        prompt=(
            "Now I will set up your identity and security policy. "
            "You can enable multi-factor authentication and choose which agents "
            "may act on your behalf. Say 'enable 2FA' or 'defaults' to continue."
        ),
        hints=["enable 2FA", "defaults", "skip", "next"],
    ),
    VoiceStep(
        key="agents",
        title="Autonomous AI Agents",
        prompt=(
            "AI-OS can run fully autonomous AI agents for you. "
            "Say 'enable agents' to activate, or 'disable agents' to require "
            "manual approval for every action."
        ),
        hints=["enable agents", "disable agents", "next"],
    ),
    VoiceStep(
        key="complete",
        title="Setup Complete",
        prompt=(
            "Setup is complete. AI-OS is ready. "
            "You can ask me questions at any time. "
            "Say 'launch' to open the system shell, or 'shutdown' to power down."
        ),
        hints=["launch", "shutdown", "help"],
    ),
]


# --- Command parsing --------------------------------------------------------

COMMAND_ALIASES: Dict[str, List[str]] = {
    "next":     ["next", "continue", "proceed", "forward", "okay next"],
    "back":     ["back", "previous", "go back"],
    "repeat":   ["repeat", "again", "say again", "what"],
    "skip":     ["skip", "pass", "later"],
    "help":     ["help", "commands", "what can i say"],
    "yes":      ["yes", "yeah", "yep", "sure", "correct", "confirm"],
    "no":       ["no", "nope", "cancel"],
    "exit":     ["exit", "quit", "stop", "end", "goodbye"],
    "detect":   ["detect", "scan", "scan hardware", "detect hardware"],
    "enable_gpu":  ["enable gpu", "turn on gpu", "use gpu"],
    "disable_gpu": ["disable gpu", "turn off gpu", "cpu only"],
    "enable_2fa":  ["enable 2fa", "turn on 2fa", "multi factor"],
    "enable_agents":  ["enable agents", "turn on agents", "autonomous on"],
    "disable_agents": ["disable agents", "turn off agents", "autonomous off"],
    "configure_network": ["configure network", "setup network", "connect network"],
    "launch":   ["launch", "start", "open shell"],
    "shutdown": ["shutdown", "power off", "turn off"],
    "defaults": ["defaults", "use defaults", "skip this"],
}


def parse_command(utterance: str) -> Optional[str]:
    """Map a free-form utterance to a canonical command.

    Uses word-boundary matching so 'no' does not match 'now' and 'skip'
    does not match 'skipper'. Longer multi-word aliases take priority.
    """
    if not utterance:
        return None
    text = utterance.strip().lower()
    best: Optional[tuple] = None  # (alias_length, command)
    for cmd, aliases in COMMAND_ALIASES.items():
        for alias in aliases:
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, text):
                score = len(alias)
                if best is None or score > best[0]:
                    best = (score, cmd)
    return best[1] if best else None


# --- Main assistant ---------------------------------------------------------

class VoiceOnboardingAssistant:
    """Voice-first onboarding & operability guide for AI-OS.

    The assistant owns a TTS backend (for speaking prompts) and an STT backend
    (for capturing user commands). It walks users through the setup script,
    but is also usable as a general voice command entry point after boot.
    """

    def __init__(
        self,
        script: Optional[List[VoiceStep]] = None,
        tts_backend: Optional[TTSBackend] = None,
        stt_backend: Optional[STTBackend] = None,
        prefer_offline: bool = True,
        on_command: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self.script = script or DEFAULT_SCRIPT
        self.tts = tts_backend or self._select_tts(prefer_offline)
        self.stt = stt_backend or self._select_stt()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._on_command = on_command
        self._step_index = 0

    # Backend selection ------------------------------------------------------

    @staticmethod
    def _select_tts(prefer_offline: bool) -> TTSBackend:
        candidates: List[TTSBackend] = []
        if prefer_offline:
            candidates.append(Pyttsx3Backend())
            candidates.append(SystemSayBackend())
            candidates.append(CoquiBackend())
            candidates.append(PiperWebSocketBackend())
        else:
            candidates.append(PiperWebSocketBackend())
            candidates.append(CoquiBackend())
            candidates.append(Pyttsx3Backend())
            candidates.append(SystemSayBackend())
        for backend in candidates:
            if backend.available:
                return backend
        return StdoutBackend()

    @staticmethod
    def _select_stt() -> STTBackend:
        for backend in (SpeechRecognitionBackend(), WhisperMicBackend()):
            if backend.available:
                return backend
        return StdinBackend()

    # Public API -------------------------------------------------------------

    @property
    def tts_name(self) -> str:
        return self.tts.name

    @property
    def stt_name(self) -> str:
        return self.stt.name

    def speak(self, text: str) -> None:
        with self._lock:
            try:
                self.tts.speak(text)
            except Exception as err:
                print(f"[VOICE] TTS failed ({err}); falling back to stdout")
                print(f"[VOICE] {text}")

    def listen(self, timeout: float = 6.0) -> Optional[str]:
        try:
            return self.stt.listen_once(timeout=timeout)
        except Exception as err:
            print(f"[VOICE] STT error: {err}")
            return None

    def await_command(self, timeout: float = 6.0, retries: int = 2) -> Optional[str]:
        """Listen repeatedly until a recognized command is heard."""
        for attempt in range(retries + 1):
            heard = self.listen(timeout=timeout)
            if heard is None:
                continue
            cmd = parse_command(heard)
            if cmd:
                return cmd
            if attempt < retries:
                self.speak("Sorry, I did not understand. Please try again.")
        return None

    def guide_step(self, key: str) -> Optional[str]:
        step = next((s for s in self.script if s.key == key), None)
        if step is None:
            return None
        self.speak(f"{step.title}. {step.prompt}")
        cmd = self.await_command()
        if cmd and self._on_command:
            try:
                self._on_command(key, cmd)
            except Exception as err:
                print(f"[VOICE] on_command handler error: {err}")
        return cmd

    def run_interactive_guide(self) -> None:
        """Run the full onboarding script from start to finish."""
        self.speak(
            f"Voice assistant ready. Speech output via {self.tts_name}, "
            f"input via {self.stt_name}."
        )
        self._step_index = 0
        while 0 <= self._step_index < len(self.script) and not self._stop.is_set():
            step = self.script[self._step_index]
            self.speak(f"{step.title}. {step.prompt}")
            cmd = self.await_command()
            if cmd == "exit":
                self.speak("Exiting voice guide. You can resume any time.")
                return
            if cmd == "back":
                self._step_index = max(0, self._step_index - 1)
                continue
            if cmd == "repeat":
                continue
            if cmd == "help":
                self._announce_hints(step)
                continue
            if cmd and self._on_command:
                try:
                    self._on_command(step.key, cmd)
                except Exception as err:
                    print(f"[VOICE] on_command handler error: {err}")
            self._step_index += 1
        if not self._stop.is_set():
            self.speak("Onboarding finished. AI-OS is at your service.")

    def start_always_on(self, poll_interval: float = 0.2) -> threading.Thread:
        """Launch a background thread that listens for voice commands forever."""
        def _loop() -> None:
            self.speak("Voice command channel online. Say 'help' for commands.")
            while not self._stop.is_set():
                heard = self.listen(timeout=5.0)
                if heard is None:
                    time.sleep(poll_interval)
                    continue
                cmd = parse_command(heard)
                if cmd == "exit":
                    self._stop.set()
                    self.speak("Voice channel closed.")
                    return
                if cmd == "help":
                    self.speak(
                        "You can say: next, back, repeat, skip, help, "
                        "launch, shutdown, enable GPU, disable GPU, "
                        "enable agents, or exit."
                    )
                    continue
                if cmd and self._on_command:
                    try:
                        self._on_command("always_on", cmd)
                    except Exception as err:
                        print(f"[VOICE] on_command handler error: {err}")
                else:
                    self.speak(f"I heard: {heard}")
        thread = threading.Thread(target=_loop, daemon=True, name="aios-voice")
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop.set()

    # Internals --------------------------------------------------------------

    def _announce_hints(self, step: VoiceStep) -> None:
        if not step.hints:
            self.speak("No specific commands for this step. Say 'next' to continue.")
            return
        self.speak("You can say: " + ", ".join(step.hints) + ".")


# --- Convenience entry points ----------------------------------------------

def run_voice_onboarding(flag_file: Optional[Path] = None) -> None:
    """Run the voice-guided onboarding once, skipping if already completed.

    A flag file (default `~/.aios/voice_onboarding_done`) records completion
    so the guide does not replay on every boot.
    """
    if flag_file is None:
        flag_file = Path.home() / ".aios" / "voice_onboarding_done"
    if flag_file.exists():
        return
    assistant = VoiceOnboardingAssistant()
    try:
        assistant.run_interactive_guide()
    finally:
        try:
            flag_file.parent.mkdir(parents=True, exist_ok=True)
            flag_file.write_text("1\n", encoding="utf-8")
        except OSError:
            pass


def voice_command_repl() -> None:
    """Launch a background voice command channel that stays on for the session."""
    assistant = VoiceOnboardingAssistant()
    assistant.start_always_on()


if __name__ == "__main__":
    if "--once" in sys.argv:
        run_voice_onboarding()
    else:
        a = VoiceOnboardingAssistant()
        print(f"[VOICE] TTS={a.tts_name} STT={a.stt_name}")
        a.run_interactive_guide()
