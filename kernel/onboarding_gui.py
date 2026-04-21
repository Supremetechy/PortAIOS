"""
AI-OS Unified Onboarding GUI

Single Eel backend that drives both the binary avatar interface and the
onboarding wizard. Exposes all step navigation, system stats, avatar
bridge lifecycle, and kernel launch to the browser frontend.
"""

import eel
import sys
import os
import json
import signal
import subprocess
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional

import bottle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AIOS")

# ---------------------------------------------------------------------------
# Paths — always absolute so CWD doesn't matter
# ---------------------------------------------------------------------------

_AIOS_ROOT = Path(__file__).resolve().parent.parent
# Add the project root to the Python path to resolve module import issues
sys.path.append(str(_AIOS_ROOT))


def _python_subprocess_cmd(mode: str, script_path: Path, *extra_args: str) -> list:
    # Under PyInstaller, sys.executable is the launcher binary, not a Python
    # interpreter. Passing a script path would re-run the launcher (and thus
    # the onboarding GUI) instead — an infinite spawn loop. When frozen,
    # hand the launcher a --subprocess <mode> flag it knows how to dispatch.
    if getattr(sys, "frozen", False):
        return [sys.executable, "--subprocess", mode, *extra_args]
    return [sys.executable, str(script_path), *extra_args]

WEB_FOLDER = str(_AIOS_ROOT / "web")
eel.init(WEB_FOLDER)


@bottle.route("/assets/<filename:path>")
def serve_static_assets(filename):
    return bottle.static_file(filename, root=str(_AIOS_ROOT / "assets"))


# ---------------------------------------------------------------------------
# Onboarding config (persisted to ~/.aios/onboarding_config.json)
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

    def is_step_complete(self, step: int) -> bool:
        return step in self.config.get("completed_steps", [])


# ---------------------------------------------------------------------------
# Video assets helper
# ---------------------------------------------------------------------------

class AIAssistantVideos:
    VIDEOS_DIR = _AIOS_ROOT / "assets" / "onboarding_videos"

    VIDEOS = {
        "welcome":        {"file": "welcome.mp4",          "title": "Welcome to AI-OS"},
        "hardware_setup": {"file": "hardware_setup.mp4",   "title": "Hardware Detection & Setup"},
        "gpu_config":     {"file": "gpu_configuration.mp4","title": "GPU Configuration"},
        "network_setup":  {"file": "network_setup.mp4",    "title": "Network Configuration"},
        "security":       {"file": "security_overview.mp4","title": "Security & Privacy"},
        "complete":       {"file": "setup_complete.mp4",   "title": "Setup Complete!"},
    }

    @classmethod
    def get_video_path(cls, video_key: str) -> Optional[str]:
        if video_key in cls.VIDEOS:
            path = cls.VIDEOS_DIR / cls.VIDEOS[video_key]["file"]
            if path.exists():
                return f"/assets/onboarding_videos/{cls.VIDEOS[video_key]['file']}"
        return None

    @classmethod
    def get_video_info(cls, video_key: str) -> Optional[Dict[str, str]]:
        return cls.VIDEOS.get(video_key)


# ---------------------------------------------------------------------------
# Onboarding steps — single source of truth
# ---------------------------------------------------------------------------

ONBOARDING_STEPS = [
    {
        "key": "welcome",
        "type": "welcome",
        "title": "Welcome to AI-OS",
        "description": "Your AI-Powered Operating System",
        "speech": "Welcome to AIOS. I am your personal AI agent. Let me guide you through the setup process.",
        "emotion": "happy",
    },
    {
        "key": "hardware_setup",
        "type": "configure",
        "title": "Hardware Detection",
        "description": "Scanning your system hardware",
        "speech": "First, I will detect your hardware: CPUs, GPUs, memory, and storage devices.",
        "emotion": "neutral",
    },
    {
        "key": "gpu_config",
        "type": "configure",
        "title": "GPU Configuration",
        "description": "Setting up GPU acceleration for AI workloads",
        "speech": "If a GPU is present, I can enable CUDA, ROCm, or Metal acceleration for AI workloads.",
        "emotion": "neutral",
    },
    {
        "key": "system",
        "type": "configure",
        "title": "System Configuration",
        "description": "Basic system settings",
        "speech": "Let's configure your system name and preferences.",
        "emotion": "neutral",
    },
    {
        "key": "complete",
        "type": "complete",
        "title": "Setup Complete!",
        "description": "You're ready to launch AI-OS",
        "speech": "Setup complete! Your system is configured and ready. Say launch or click the button to start AIOS.",
        "emotion": "excited",
    },
]

onboarding_config = OnboardingConfig()


# ---------------------------------------------------------------------------
# Eel-exposed functions (called from JavaScript)
# ---------------------------------------------------------------------------

@eel.expose
def get_current_step_data():
    idx = onboarding_config.config["current_step"]
    if 0 <= idx < len(ONBOARDING_STEPS):
        step = ONBOARDING_STEPS[idx]
        return {
            "index": idx,
            "total_steps": len(ONBOARDING_STEPS),
            "title": step["title"],
            "description": step["description"],
            "speech": step.get("speech", step["description"]),
            "emotion": step.get("emotion", "neutral"),
            "type": step.get("type", "configure"),
            "video_url": AIAssistantVideos.get_video_path(step["key"]),
        }
    return None


@eel.expose
def next_step():
    idx = onboarding_config.config["current_step"]
    if idx < len(ONBOARDING_STEPS) - 1:
        onboarding_config.config["current_step"] += 1
        onboarding_config.mark_step_complete(idx)
        onboarding_config.save()
        return get_current_step_data()
    return None


@eel.expose
def previous_step():
    idx = onboarding_config.config["current_step"]
    if idx > 0:
        onboarding_config.config["current_step"] -= 1
        onboarding_config.save()
        return get_current_step_data()
    return None


@eel.expose
def get_system_stats():
    try:
        import psutil
        return {
            "cpu_usage": psutil.cpu_percent(interval=0.1),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage("/").percent,
            "disk_available_gb": psutil.disk_usage("/").free / (1024 ** 3)
        }
    except ImportError:
        return {"cpu_usage": 0, "memory_usage": 0, "disk_usage": 0, "disk_available_gb": 0}


@eel.expose
def launch_aios():
    onboarding_config.config["onboarding_complete"] = True
    onboarding_config.save()
    logger.info("Launching AI-OS kernel...")
    try:
        subprocess.Popen(_python_subprocess_cmd("kernel", _AIOS_ROOT / "aios_kernel.py"))
    except Exception as e:
        logger.error(f"Failed to launch kernel: {e}")
    return True


@eel.expose
def get_onboarding_step(step_index):
    if 0 <= step_index < len(ONBOARDING_STEPS):
        step = ONBOARDING_STEPS[step_index]
        return {
            "index": step_index,
            "total_steps": len(ONBOARDING_STEPS),
            "title": step["title"],
            "description": step["description"],
            "speech": step.get("speech", step["description"]),
            "emotion": step.get("emotion", "neutral"),
            "type": step.get("type", "configure"),
            "video_url": AIAssistantVideos.get_video_path(step["key"]),
        }
    return None


# ---------------------------------------------------------------------------
# Avatar bridge lifecycle
# ---------------------------------------------------------------------------

_bridge_process: Optional[subprocess.Popen] = None


def start_avatar_bridge() -> Optional[subprocess.Popen]:
    """Start the avatar WebSocket bridge (ws://localhost:8765)."""
    global _bridge_process

    bridge_script = _AIOS_ROOT / "web" / "avatar-bridge.py"
    if not bridge_script.exists():
        logger.warning("avatar-bridge.py not found — avatar will use browser TTS")
        return None

    tts_engine = "fallback"
    try:
        from TTS.api import TTS  # noqa: F401
        tts_engine = "coqui"
        logger.info("Coqui TTS available — using high-fidelity voice")
    except Exception as e:
        logger.info(f"Coqui TTS not available ({e}) — avatar will use browser TTS")

    logger.info("Starting avatar WebSocket bridge...")
    proc = subprocess.Popen(
        _python_subprocess_cmd("avatar-bridge", bridge_script, "--tts", tts_engine),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)
    if proc.poll() is not None:
        logger.error("Avatar bridge exited prematurely")
        return None
    logger.info(f"Avatar bridge running (PID {proc.pid})")
    _bridge_process = proc
    return proc


def stop_avatar_bridge():
    global _bridge_process
    if _bridge_process:
        logger.info("Stopping avatar bridge...")
        _bridge_process.terminate()
        try:
            _bridge_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _bridge_process.kill()
        _bridge_process = None


# ---------------------------------------------------------------------------
# Application entry point
# ---------------------------------------------------------------------------

def start_eel_app():
    """Launch the unified AIOS onboarding + avatar UI."""
    # Mark this process tree as the GUI owner so any child re-launch of the
    # frozen binary (via sys.executable) bails out instead of opening another
    # browser tab. Pairs with the guard in installer/launcher.py:main().
    if os.environ.get("PORTAIOS_GUI_RUNNING") == "1":
        logger.warning("GUI already running in ancestor process; refusing to start a second instance")
        return
    os.environ["PORTAIOS_GUI_RUNNING"] = "1"

    bridge = start_avatar_bridge()
    
    # Setup voice command handlers
    try:
        import sys
        from pathlib import Path
        # Add parent directory to path if needed
        root = Path(__file__).parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        
        from kernel.voice_commands import setup_voice_commands_for_eel
        voice_cmds = setup_voice_commands_for_eel(eel)
        logger.info("Voice commands enabled")
    except Exception as e:
        logger.warning(f"Voice commands not available: {e}")
        import traceback
        traceback.print_exc()
    
    # Setup viseme integration for lip-sync
    try:
        import sys
        from pathlib import Path
        # Add parent directory to path if needed
        root = Path(__file__).parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
            
        from kernel.viseme_integration import setup_viseme_integration
        viseme_bridge = setup_viseme_integration(eel)
        logger.info("Viseme lip-sync integration enabled")
    except Exception as e:
        logger.warning(f"Viseme integration not available: {e}")
        import traceback
        traceback.print_exc()

    def cleanup(signum=None, frame=None):
        stop_avatar_bridge()
        os._exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    @eel.expose
    def quit_app():
        """In-UI kill switch — callable from the browser to cleanly stop PortAIOS."""
        logger.info("quit_app requested from UI — shutting down")
        cleanup()
        return True

    # Setup agent executor for agentic commands
    try:
        from kernel.agent_executor import AgentExecutor
        _agent = AgentExecutor()
        logger.info("Agent executor initialized")

        @eel.expose
        def agent_execute(text: str):
            """Execute a natural-language command via the AIOS agent."""
            result = _agent.execute(text)
            return {
                "success": result.success,
                "message": result.message,
                "speak": result.speak,
                "data": result.data,
            }

        @eel.expose
        def agent_capabilities():
            """Return the list of agent capabilities."""
            return _agent.get_capabilities()

        @eel.expose
        def agent_help():
            """Return help text for the agent."""
            return _agent.get_help_text()

    except Exception as e:
        logger.warning(f"Agent executor not available: {e}")

    # Add speak_with_lipsync function for Piper TTS integration
    @eel.expose
    def speak_with_lipsync(text: str):
        """Speak using Piper TTS with phoneme data for lip-sync"""
        logger.info(f"Speaking with lip-sync: '{text}'")
        
        try:
            # Use Piper backend if available
            from kernel.viseme_integration import create_piper_backend_with_visemes
            
            backend = create_piper_backend_with_visemes()
            backend.speak(text)
            
            return {'status': 'ok', 'backend': 'piper'}
        except Exception as e:
            logger.warning(f"Piper TTS not available: {e}, using fallback")
            return {'status': 'fallback', 'error': str(e)}
    
    try:
        logger.info("Starting AIOS onboarding UI on http://localhost:8001 ...")
        eel.start(
            "avatar-integration.html",  # Use avatar interface
            host="localhost",
            port=8001,
            size=(1280, 800),
            mode="default",
            block=True,
        )
    except (SystemExit, KeyboardInterrupt):
        pass
    except Exception as e:
        logger.warning(f"Chrome/Edge app mode unavailable ({e}), opening in browser")
        try:
            eel.start(
                "index-voice-enabled.html",  # Use voice-enabled interface
                host="localhost",
                port=8001,
                size=(1280, 800),
                mode=None,
                block=True,
            )
        except (SystemExit, KeyboardInterrupt):
            pass
    finally:
        stop_avatar_bridge()


if __name__ == "__main__":
    start_eel_app()
