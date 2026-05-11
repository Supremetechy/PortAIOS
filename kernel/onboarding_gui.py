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
import mimetypes
import time
from pathlib import Path
from typing import Dict, Any, Optional

import bottle
import threading

# Browsers reject <script type="module"> with a non-JS MIME type (Chrome/Safari
# strict MIME checking). Python's stdlib mimetypes doesn't know .jsx by default,
# so Bottle's static_file falls back to text/html and ESM imports fail with
# "'text/html' is not a valid JavaScript MIME type". Register the mapping once
# at import time before any request is served.
mimetypes.add_type("application/javascript", ".jsx")
mimetypes.add_type("application/javascript", ".mjs")
# IANA-registered types for glTF assets — used by the React 3D avatar GLB load.
mimetypes.add_type("model/gltf-binary", ".glb")
mimetypes.add_type("model/gltf+json", ".gltf")

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


_JS_MODULE_EXTS = (".jsx", ".mjs", ".js")


@bottle.route("/assets/<filename:path>")
def serve_static_assets(filename):
    # Pass mimetype explicitly for ESM-bound files. Some Python builds don't
    # honor mimetypes.add_type for bottle.static_file (or the registry hasn't
    # been re-imported), and Chrome rejects <script type="module"> with a
    # text/html response. This belt-and-suspenders the global registration
    # done at the top of the module.
    if filename.lower().endswith(_JS_MODULE_EXTS):
        return bottle.static_file(
            filename,
            root=str(_AIOS_ROOT / "assets"),
            mimetype="application/javascript",
        )
    return bottle.static_file(filename, root=str(_AIOS_ROOT / "assets"))


@bottle.route("/models/<filename:path>")
def serve_models(filename):
    """Expose models/ so the web UI can fetch generated avatar.glb files."""
    lower = filename.lower()
    if lower.endswith(".glb"):
        return bottle.static_file(
            filename,
            root=str(_AIOS_ROOT / "models"),
            mimetype="model/gltf-binary",
        )
    if lower.endswith(".gltf"):
        return bottle.static_file(
            filename,
            root=str(_AIOS_ROOT / "models"),
            mimetype="model/gltf+json",
        )
    return bottle.static_file(filename, root=str(_AIOS_ROOT / "models"))


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
            "hardware_summary": None,
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


def _serialize_system_specs(specs) -> Dict[str, Any]:
    gpu_processors = [
        processor for processor in specs.processors
        if getattr(processor.processor_type, "value", "") == "gpu"
    ]
    accelerator_processors = [
        processor for processor in specs.processors
        if getattr(processor.processor_type, "value", "") in {"gpu", "npu", "tpu", "vpu"}
    ]

    return {
        "hostname": specs.hostname,
        "os_type": specs.os_type,
        "os_version": specs.os_version,
        "kernel_version": specs.kernel_version,
        "architecture": specs.architecture,
        "memory": {
            "total_gb": round(specs.memory.total_gb, 2),
            "available_gb": round(specs.memory.available_gb, 2),
            "used_gb": round(specs.memory.used_gb, 2),
        },
        "storage_devices": [
            {
                "device_name": device.device_name,
                "mount_point": device.mount_point,
                "total_gb": round(device.total_gb, 2),
                "used_gb": round(device.used_gb, 2),
                "filesystem_type": device.filesystem_type,
                "is_ssd": device.is_ssd,
                "model": device.model,
            }
            for device in specs.storage_devices
        ],
        "network_interfaces": specs.network_interfaces,
        "processors": [
            {
                "processor_type": processor.processor_type.value,
                "vendor": processor.vendor.value,
                "model": processor.model,
                "cores": processor.cores,
                "threads": processor.threads,
                "frequency_mhz": processor.frequency_mhz,
                "memory_gb": processor.memory_gb,
                "compute_capability": processor.compute_capability,
                "driver_version": processor.driver_version,
                "capabilities": processor.capabilities[:12],
            }
            for processor in specs.processors
        ],
        "gpu_count": len(gpu_processors),
        "has_gpu": bool(gpu_processors),
        "accelerator_count": len(accelerator_processors),
    }


def _onboarding_state() -> Dict[str, Any]:
    return {
        "step": get_current_step_data(),
        "config": dict(onboarding_config.config),
        "redirect_url": "avatar-integration.html",
    }


def _startup_page() -> str:
    if onboarding_config.config.get("onboarding_complete"):
        return "avatar-integration.html"
    return "index.html"


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
            "key": step["key"],
            "title": step["title"],
            "description": step["description"],
            "speech": step.get("speech", step["description"]),
            "emotion": step.get("emotion", "neutral"),
            "type": step.get("type", "configure"),
            "video_url": AIAssistantVideos.get_video_path(step["key"]),
        }
    return None


@eel.expose
def get_onboarding_state():
    return _onboarding_state()


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
def update_onboarding_config(updates: Optional[Dict[str, Any]] = None):
    if not isinstance(updates, dict):
        return {"success": False, "error": "Invalid onboarding update payload"}

    allowed_fields = {
        "user_name": str,
        "system_name": str,
        "install_path": str,
        "gpu_enabled": bool,
        "auto_start": bool,
        "telemetry_enabled": bool,
    }

    for field, expected_type in allowed_fields.items():
        if field not in updates:
            continue
        value = updates[field]
        if expected_type is bool:
            onboarding_config.config[field] = bool(value)
        elif value is None:
            onboarding_config.config[field] = ""
        else:
            onboarding_config.config[field] = str(value).strip()

    onboarding_config.save()
    return {"success": True, **_onboarding_state()}


@eel.expose
def detect_hardware():
    try:
        from kernel.hardware_detection import HardwareDetector

        detector = HardwareDetector()
        specs = detector.detect_all()
        summary = _serialize_system_specs(specs)
        onboarding_config.config["hardware_summary"] = summary
        onboarding_config.config["gpu_enabled"] = bool(summary.get("has_gpu"))
        onboarding_config.save()
        return {"success": True, "hardware": summary, **_onboarding_state()}
    except Exception as e:
        logger.exception("Hardware detection failed")
        return {"success": False, "error": str(e), **_onboarding_state()}


@eel.expose
def complete_onboarding():
    user_name = str(onboarding_config.config.get("user_name", "")).strip()
    system_name = str(onboarding_config.config.get("system_name", "")).strip()
    install_path = str(onboarding_config.config.get("install_path", "")).strip()

    if not user_name or not system_name:
        return {
            "success": False,
            "error": "Please enter both your name and a system name before continuing.",
            **_onboarding_state(),
        }

    if not install_path:
        return {
            "success": False,
            "error": "Please choose an installation path before continuing.",
            **_onboarding_state(),
        }

    onboarding_config.config["onboarding_complete"] = True
    onboarding_config.config["current_step"] = len(ONBOARDING_STEPS) - 1
    onboarding_config.config["completed_steps"] = list(range(len(ONBOARDING_STEPS)))
    onboarding_config.save()
    return {"success": True, "redirect_url": "avatar-integration.html", **_onboarding_state()}


@eel.expose
def reset_onboarding():
    completed_steps = onboarding_config.config.get("completed_steps", [])
    onboarding_config.config["onboarding_complete"] = False
    onboarding_config.config["current_step"] = 0
    onboarding_config.config["completed_steps"] = []
    if isinstance(completed_steps, list) and len(completed_steps) >= 1:
        onboarding_config.config["completed_steps"] = []
    onboarding_config.save()
    return {"success": True, **_onboarding_state()}


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
    """Start the avatar WebSocket bridge (ws://localhost:8765).

    Tries the full TTS+lip-sync bridge first (web/avatar-bridge.py). If that
    isn't available, falls back to the lightweight viseme simulator at
    server.py — which still produces a working stream so the UI animates.
    """
    global _bridge_process

    bridge_script = _AIOS_ROOT / "web" / "avatar-bridge.py"
    fallback_script = _AIOS_ROOT / "server.py"

    if bridge_script.exists():
        tts_engine = "fallback"
        try:
            from TTS.api import TTS  # noqa: F401
            tts_engine = "coqui"
            logger.info("Coqui TTS available — using high-fidelity voice")
        except Exception as e:
            logger.info(f"Coqui TTS not available ({e}) — avatar will use browser TTS")

        logger.info("Starting avatar WebSocket bridge (full)...")
        proc = subprocess.Popen(
            _python_subprocess_cmd("avatar-bridge", bridge_script, "--tts", tts_engine),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(2)
        if proc.poll() is None:
            logger.info(f"Avatar bridge running (PID {proc.pid})")
            _bridge_process = proc
            return proc
        logger.warning("Full avatar bridge exited prematurely — trying fallback simulator")

    if fallback_script.exists():
        logger.info("Starting fallback viseme simulator (server.py) on ws://127.0.0.1:8765 ...")
        proc = subprocess.Popen(
            _python_subprocess_cmd("avatar-bridge-fallback", fallback_script),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(1)
        if proc.poll() is None:
            logger.info(f"Fallback viseme simulator running (PID {proc.pid})")
            _bridge_process = proc
            return proc
        logger.error("Fallback simulator exited prematurely")

    logger.warning("No avatar bridge available — avatar will use browser TTS only")
    return None


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
    pending_cleanup_timer = None
    
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

    # Setup filesystem / dynamic UI data providers used by avatar-integration.html
    try:
        from kernel.ui_data_provider import setup_ui_data_provider
        ui_provider = setup_ui_data_provider()
        logger.info("UI data provider enabled")
    except Exception as e:
        ui_provider = None
        logger.warning(f"UI data provider not available: {e}")

    try:
        from kernel.ai_file_operations import setup_ai_file_operations
        setup_ai_file_operations(ui_provider)
        logger.info("AI file operations enabled")
    except Exception as e:
        logger.warning(f"AI file operations not available: {e}")

    try:
        from kernel.ui_voice_commands import setup_ui_voice_commands
        setup_ui_voice_commands()
        logger.info("UI voice commands enabled")
    except Exception as e:
        logger.warning(f"UI voice commands not available: {e}")
    
    # Setup avatar creation server
    try:
        from kernel.avatar_creation_server import setup_avatar_creation_server
        setup_avatar_creation_server()
        logger.info("Avatar creation server enabled")
    except Exception as e:
        logger.warning(f"Avatar creation server not available: {e}")

    def cleanup(signum=None, frame=None):
        stop_avatar_bridge()
        os._exit(0)

    def close_callback(page, sockets):
        nonlocal pending_cleanup_timer

        if sockets:
            if pending_cleanup_timer is not None:
                pending_cleanup_timer.cancel()
                pending_cleanup_timer = None
            return

        def _delayed_cleanup():
            logger.info("No active Eel sockets after grace period; shutting down UI backend")
            cleanup()

        if pending_cleanup_timer is not None:
            pending_cleanup_timer.cancel()
        pending_cleanup_timer = threading.Timer(2.5, _delayed_cleanup)
        pending_cleanup_timer.daemon = True
        pending_cleanup_timer.start()

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

    # ── Avatar customizer — exposed to the web UI ──────────────────────
    @eel.expose
    def generate_custom_avatar(params: Optional[Dict[str, Any]] = None):
        """Generate a customized AI_Avatar.glb from UI sliders.

        Writes to models/avatar_generated.glb (NOT avatar.glb — that path is
        reserved for the Ready Player Me head used by the React 3D lip-sync
        avatar, which needs morphs this generator does not produce). The
        returned URL points at the generated file for preview only; the
        REACT_3D mode continues to load the RPM avatar.glb separately.
        """
        from kernel.avatar_generator import generate_from_dict, DEFAULT_OUTPUT
        result = generate_from_dict(params, output_path=str(DEFAULT_OUTPUT))
        if result.get("success"):
            result["model_url"] = f"/models/avatar_generated.glb?v={int(time.time())}"
        return result

    @eel.expose
    def get_avatar_default_params():
        """Expose AvatarParams defaults so the UI can render initial slider values."""
        from kernel.avatar_generator import AvatarParams
        return AvatarParams().to_dict()

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

        startup_page = _startup_page()
        url = f"http://localhost:8001/{startup_page}"

        if sys.platform == "darwin":
            # macOS TCC (microphone) permissions are assigned to the
            # "responsible" process. When Eel's default launcher spawns
            # Chrome via subprocess.Popen, Chrome inherits PortAIOS.app as
            # its responsible process — and the ad-hoc-signed bundle has no
            # mic entitlement, so Chrome's getUserMedia silently fails.
            #
            # `open -na` routes the launch through Launch Services, which
            # makes Chrome its own responsible process and its existing
            # per-origin mic permission applies normally.
            import time as _time
            import subprocess as _sp

            def _launch_detached() -> bool:
                # Wait briefly for the Eel server to bind to :8001 before
                # handing the URL to Chrome.
                _time.sleep(1.2)
                candidates = [
                    "Google Chrome",
                    "Microsoft Edge",
                    "Brave Browser",
                    "Chromium",
                ]
                for app_name in candidates:
                    if not Path(f"/Applications/{app_name}.app").exists():
                        continue
                    try:
                        _sp.Popen(
                            [
                                "/usr/bin/open",
                                "-a",
                                app_name,
                                "--args",
                                f"--app={url}",
                                "--window-size=1280,800",
                            ],
                            stdout=_sp.DEVNULL,
                            stderr=_sp.DEVNULL,
                        )
                        logger.info(
                            f"Launched {app_name} via Launch Services "
                            "(detached for TCC/microphone)"
                        )
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to launch {app_name}: {e}")
                logger.warning(
                    "No Chromium browser found in /Applications. "
                    f"Open manually: {url}"
                )
                return False

            threading.Thread(target=_launch_detached, daemon=True).start()

            # Start Eel server without launching a browser (we handle it manually above)
            eel.start(
                startup_page,
                host="localhost",
                port=8001,
                size=(1280, 800),
                mode=None,  # Explicitly no browser launch - we do it manually
                block=True,
                close_callback=close_callback,
            )
        else:
            eel.start(
                startup_page,
                host="localhost",
                port=8001,
                size=(1280, 800),
                mode="default",
                block=True,
            )
    except (SystemExit, KeyboardInterrupt):
        pass
    except Exception as e:
        logger.warning(f"UI launch issue ({e}); running headless on :8001")
        try:
            startup_page = _startup_page()
            eel.start(
                startup_page,
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
