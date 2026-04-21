"""
AIOS Onboarding Engine — Pure Python, No Web Dependencies

Drives the onboarding wizard through any DisplayBackend (TUI, SDL2,
WebView). The existing Eel-based onboarding_gui.py is preserved as
the browser-mode path; this module is the native-mode equivalent.

All step definitions, config persistence, and flow control live here.
"""

import json
import logging
import time
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

from kernel.display.base import (
    DisplayBackend,
    InputEvent,
    EventType,
    AvatarState,
    OnboardingStepView,
)

logger = logging.getLogger("AIOS.onboarding")

_AIOS_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Onboarding config (same format as onboarding_gui.py — shared JSON)
# ---------------------------------------------------------------------------

class OnboardingConfig:
    CONFIG_FILE = Path.home() / ".aios" / "onboarding_config.json"

    def __init__(self):
        self.config = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "onboarding_complete": False,
            "current_step": 0,
            "user_name": "",
            "system_name": "",
            "install_path": str(Path.cwd()),
            "gpu_enabled": False,
            "auto_start": False,
            "telemetry_enabled": True,
            "completed_steps": [],
        }

    def save(self):
        self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)

    def mark_step_complete(self, step: int):
        if step not in self.config["completed_steps"]:
            self.config["completed_steps"].append(step)
        self.save()

    @property
    def current_step(self) -> int:
        return self.config.get("current_step", 0)

    @current_step.setter
    def current_step(self, val: int):
        self.config["current_step"] = val

    @property
    def is_complete(self) -> bool:
        return self.config.get("onboarding_complete", False)


# ---------------------------------------------------------------------------
# Onboarding steps — single source of truth (mirrors onboarding_gui.py)
# ---------------------------------------------------------------------------

ONBOARDING_STEPS = [
    {
        "key": "welcome",
        "type": "welcome",
        "title": "Welcome to AI-OS",
        "description": "Your AI-Powered Operating System. I am your personal AI agent. Let me guide you through the setup process.",
        "speech": "Welcome to AIOS. I am your personal AI agent. Let me guide you through the setup process.",
        "emotion": "happy",
    },
    {
        "key": "hardware_setup",
        "type": "configure",
        "title": "Hardware Detection",
        "description": "Scanning your system for CPUs, GPUs, memory, and storage devices.",
        "speech": "First, I will detect your hardware: CPUs, GPUs, memory, and storage devices.",
        "emotion": "neutral",
        "action": "detect_hardware",
    },
    {
        "key": "gpu_config",
        "type": "configure",
        "title": "GPU Configuration",
        "description": "Setting up GPU acceleration for AI workloads. CUDA, ROCm, or Metal will be enabled if a compatible GPU is detected.",
        "speech": "If a GPU is present, I can enable CUDA, ROCm, or Metal acceleration for AI workloads.",
        "emotion": "neutral",
        "action": "configure_gpu",
    },
    {
        "key": "system",
        "type": "configure",
        "title": "System Configuration",
        "description": "Configure your system name and preferences.",
        "speech": "Let's configure your system name and preferences.",
        "emotion": "neutral",
        "action": "configure_system",
    },
    {
        "key": "complete",
        "type": "complete",
        "title": "Setup Complete!",
        "description": "Your system is configured and ready. Press Enter or say 'launch' to start AIOS.",
        "speech": "Setup complete! Your system is configured and ready. Say launch or press Enter to start AIOS.",
        "emotion": "excited",
    },
]


# ---------------------------------------------------------------------------
# Step actions — run OS-level operations that browsers can't do
# ---------------------------------------------------------------------------

def _detect_hardware() -> Dict[str, Any]:
    """Run real hardware detection via kernel subsystem."""
    results = {"status": "ok", "details": []}
    try:
        from kernel.hardware_detection import HardwareDetector
        detector = HardwareDetector()
        specs = detector.detect_all()

        for proc in specs.processors:
            results["details"].append(
                f"{proc.processor_type.value.upper()}: {proc.vendor.value} {proc.model}"
            )
        results["details"].append(f"Memory: {specs.memory.total_gb:.1f} GB")
        results["details"].append(f"Storage devices: {len(specs.storage_devices)}")
        results["details"].append(f"Network interfaces: {len(specs.network_interfaces)}")
        results["specs"] = specs
    except Exception as e:
        results["status"] = "error"
        results["details"].append(f"Detection failed: {e}")
    return results


def _configure_gpu() -> Dict[str, Any]:
    """Probe GPU acceleration availability."""
    results = {"status": "ok", "details": [], "gpu_available": False}
    try:
        from kernel.hardware_detection import HardwareDetector
        detector = HardwareDetector()
        specs = detector.detect_all()
        gpus = [p for p in specs.processors if p.processor_type.value == "gpu"]
        if gpus:
            results["gpu_available"] = True
            for gpu in gpus:
                info = f"{gpu.vendor.value.upper()} {gpu.model}"
                if gpu.memory_gb:
                    info += f" ({gpu.memory_gb:.1f} GB VRAM)"
                results["details"].append(info)
        else:
            results["details"].append("No GPU detected — CPU-only mode")
    except Exception as e:
        results["status"] = "error"
        results["details"].append(f"GPU probe failed: {e}")
    return results


def _configure_system() -> Dict[str, Any]:
    """Gather basic system configuration."""
    import platform
    return {
        "status": "ok",
        "details": [
            f"Platform: {platform.system()} {platform.release()}",
            f"Architecture: {platform.machine()}",
            f"Python: {platform.python_version()}",
            f"Hostname: {platform.node()}",
        ],
    }


STEP_ACTIONS = {
    "detect_hardware": _detect_hardware,
    "configure_gpu": _configure_gpu,
    "configure_system": _configure_system,
}


# ---------------------------------------------------------------------------
# System stats helper (no psutil hard requirement)
# ---------------------------------------------------------------------------

def get_system_stats() -> Dict[str, Any]:
    try:
        import psutil
        return {
            "cpu_usage": psutil.cpu_percent(interval=0.1),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent,
        }
    except ImportError:
        return {"cpu_usage": 0, "memory_usage": 0, "disk_usage": 0}


# ---------------------------------------------------------------------------
# Onboarding Engine
# ---------------------------------------------------------------------------

class OnboardingEngine:
    """
    Main onboarding loop — works with any DisplayBackend.
    Does NOT import eel, bottle, or any web framework.
    """

    def __init__(self, display: DisplayBackend, tts=None):
        self.display = display
        self.tts = tts  # Optional kernel.audio.tts.TTSEngine
        self.config = OnboardingConfig()
        self.steps = ONBOARDING_STEPS
        self._step_results: Dict[str, Any] = {}

    def run(self) -> bool:
        """
        Run the full onboarding wizard. Returns True if completed,
        False if the user quit early.
        """
        if self.config.is_complete:
            logger.info("Onboarding already completed, skipping")
            return True

        self.display.set_title("AIOS — Onboarding")

        while self.display.is_running():
            step_def = self.steps[self.config.current_step]
            step_view = self._build_step_view(step_def)

            # Show the step
            self.display.show_step(step_view)
            self.display.show_avatar(AvatarState(
                emotion=step_def.get("emotion", "neutral"),
                activity="idle",
            ))

            # Speak the step narration
            self._speak(step_def.get("speech", step_def["description"]))

            # Run the step's OS-level action (hardware detection, etc.)
            action_key = step_def.get("action")
            if action_key and action_key in STEP_ACTIONS:
                self.display.show_avatar(AvatarState(
                    emotion="thinking", activity="thinking",
                ))
                self.display.show_message(f"Running {step_def['title']}...", "info")

                result = STEP_ACTIONS[action_key]()
                self._step_results[action_key] = result

                for detail in result.get("details", []):
                    self.display.show_message(detail, "success" if result["status"] == "ok" else "error")
                    time.sleep(0.3)

                self.display.show_avatar(AvatarState(
                    emotion=step_def.get("emotion", "neutral"),
                    activity="idle",
                ))

            # Update progress
            self.display.show_progress(
                self.config.current_step + 1,
                len(self.steps),
                "Onboarding",
            )

            # Update system stats
            self.display.show_system_stats(get_system_stats())

            # Wait for user input
            event = self._wait_for_navigation()
            if event is None or event.type == EventType.QUIT:
                logger.info("Onboarding cancelled by user")
                return False

            if event.type == EventType.NEXT:
                if self.config.current_step < len(self.steps) - 1:
                    self.config.mark_step_complete(self.config.current_step)
                    self.config.current_step += 1
                    self.config.save()
                else:
                    # Final step — mark complete
                    self.config.config["onboarding_complete"] = True
                    self.config.save()
                    self.display.show_message("Onboarding complete!", "success")
                    self._speak("Setup complete. Launching AIOS kernel.")
                    return True

            elif event.type == EventType.PREV:
                if self.config.current_step > 0:
                    self.config.current_step -= 1
                    self.config.save()

            elif event.type == EventType.VOICE_COMMAND:
                self._handle_voice_command(event.value)

        return False

    def _build_step_view(self, step_def: Dict) -> OnboardingStepView:
        idx = self.config.current_step
        fields = []

        # Add action results as fields if available
        action_key = step_def.get("action")
        if action_key and action_key in self._step_results:
            result = self._step_results[action_key]
            for detail in result.get("details", []):
                fields.append({"label": "", "value": detail})

        return OnboardingStepView(
            index=idx,
            total_steps=len(self.steps),
            title=step_def["title"],
            description=step_def["description"],
            step_type=step_def.get("type", "configure"),
            fields=fields,
        )

    def _speak(self, text: str) -> None:
        """Speak via the TTS engine if available."""
        if self.tts:
            try:
                self.display.show_avatar(AvatarState(
                    emotion=self.steps[self.config.current_step].get("emotion", "neutral"),
                    activity="speaking",
                ))
                self.tts.speak(text)
                self.display.show_avatar(AvatarState(
                    emotion=self.steps[self.config.current_step].get("emotion", "neutral"),
                    activity="idle",
                ))
            except Exception as e:
                logger.warning(f"TTS failed: {e}")
        else:
            logger.info(f"[TTS] {text}")

    def _wait_for_navigation(self) -> Optional[InputEvent]:
        """Block until the user presses Next, Back, or Quit."""
        while self.display.is_running():
            self.display.update()
            event = self.display.get_input(timeout_ms=50)
            if event and event.type in (
                EventType.NEXT, EventType.PREV, EventType.QUIT,
                EventType.VOICE_COMMAND, EventType.CONFIRM,
            ):
                return event
            # Periodic stats refresh
            self.display.show_system_stats(get_system_stats())
        return None

    def _handle_voice_command(self, command: str) -> None:
        cmd = command.lower().strip()
        if cmd in ("next", "continue", "proceed"):
            self.config.mark_step_complete(self.config.current_step)
            if self.config.current_step < len(self.steps) - 1:
                self.config.current_step += 1
                self.config.save()
        elif cmd in ("back", "previous"):
            if self.config.current_step > 0:
                self.config.current_step -= 1
                self.config.save()
        elif cmd in ("launch", "start", "go"):
            self.config.config["onboarding_complete"] = True
            self.config.save()


# ---------------------------------------------------------------------------
# Kernel launch helper
# ---------------------------------------------------------------------------

def launch_kernel() -> None:
    """Launch the AIOS kernel after onboarding completes."""
    kernel_script = _AIOS_ROOT / "aios_kernel.py"
    if kernel_script.exists():
        logger.info("Launching AIOS kernel...")
        subprocess.Popen([sys.executable, str(kernel_script)])
    else:
        logger.error(f"Kernel script not found: {kernel_script}")
