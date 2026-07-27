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
            mimetype="application/javascript",  # type: ignore[arg-type]
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
            mimetype="model/gltf-binary",  # type: ignore[arg-type]
        )
    if lower.endswith(".gltf"):
        return bottle.static_file(
            filename,
            root=str(_AIOS_ROOT / "models"),
            mimetype="model/gltf+json",  # type: ignore[arg-type]
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
# MiniKernel integration — eel bridge to the AI-first microkernel
# ---------------------------------------------------------------------------

_minikernel_system = None
_minikernel_boot_thread: Optional[threading.Thread] = None
_minikernel_lock = threading.Lock()


def _run_minikernel_boot():
    """Background thread: import, instantiate, and boot MiniKernelSystem."""
    global _minikernel_system
    try:
        root = Path(__file__).resolve().parent.parent
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))

        from minikernel.boot import MiniKernelSystem
        from minikernel.security.confirmation_loop import ConfirmationMode

        system = MiniKernelSystem(config={"confirmation_mode": ConfirmationMode.AUTO_APPROVE})
        if system.boot():
            with _minikernel_lock:
                _minikernel_system = system
            logger.info("MiniKernel booted and ready")
        else:
            logger.error("MiniKernel boot failed")
    except Exception as e:
        logger.error("MiniKernel boot error: %s", e, exc_info=True)


@eel.expose
def minikernel_boot():
    """Boot the minikernel in a background thread. Safe to call multiple times."""
    global _minikernel_boot_thread

    with _minikernel_lock:
        if _minikernel_system is not None:
            return {"success": True, "status": "running"}

    if _minikernel_boot_thread and _minikernel_boot_thread.is_alive():
        return {"success": True, "status": "booting"}

    _minikernel_boot_thread = threading.Thread(
        target=_run_minikernel_boot, daemon=True, name="MiniKernelBoot"
    )
    _minikernel_boot_thread.start()
    return {"success": True, "status": "booting"}


@eel.expose
def minikernel_status():
    """Return the current minikernel state and service summary."""
    is_booting = _minikernel_boot_thread is not None and _minikernel_boot_thread.is_alive()

    with _minikernel_lock:
        system = _minikernel_system

    if system is None:
        return {
            "state": "booting" if is_booting else "offline",
            "services": 0,
            "memory_mb": 0,
            "capabilities": [],
        }

    try:
        stats = system.kernel.get_stats()
        caps  = system.capabilities.get_agent_capabilities("minikernel_ai")
        return {
            "state":        stats.get("state", "unknown"),
            "services":     stats.get("services", 0),
            "memory_mb":    round(stats.get("memory_mb", 0), 1),
            "capabilities": [c.capability.value for c in caps],
        }
    except Exception as e:
        return {"state": "error", "error": str(e), "capabilities": []}


@eel.expose
def minikernel_command(text: str):
    """
    Send a natural-language command through the minikernel intent pipeline.

    Returns a dict with: success, output, error, intent { type, action, confidence }, risk
    """
    with _minikernel_lock:
        system = _minikernel_system

    if system is None:
        return {"success": False, "error": "MiniKernel is not running. Boot it first."}

    text = (text or "").strip()
    if not text:
        return {"success": False, "error": "Empty command."}

    try:
        intent      = system.intent_parser.parse(text)
        intent_info = {
            "type":       intent.intent_type.value,
            "action":     intent.action,
            "confidence": round(intent.confidence, 2),
        }

        if intent.confidence < 0.3:
            return {
                "success": False,
                "error":   f"Command not understood (confidence {intent.confidence:.0%})",
                "intent":  intent_info,
            }

        validation = system.validator.validate(intent)
        if not validation.is_valid:
            return {
                "success": False,
                "error":   "Blocked: " + "; ".join(validation.errors),
                "intent":  intent_info,
                "risk":    validation.risk_level.value,
            }

        # Submitting via the UI counts as explicit user confirmation.
        result = system.executor.execute(intent, validation, confirmed=True)

        output_msg = (result.output or {}).get("message", "Done")
        files = (result.output or {}).get("files", [])
        if files:
            output_msg += f"\n{len(files)} result(s):"
            for f in files[:8]:
                output_msg += "\n  " + f.get("path", f.get("name", "?"))
            if len(files) > 8:
                output_msg += f"\n  … {len(files) - 8} more"

        return {
            "success": result.success,
            "output":  output_msg,
            "error":   result.error,
            "intent":  intent_info,
            "risk":    validation.risk_level.value,
        }

    except Exception as e:
        logger.error("minikernel_command error: %s", e, exc_info=True)
        return {"success": False, "error": str(e)}


@eel.expose
def minikernel_shutdown_kernel():
    """Gracefully shut down the running minikernel instance."""
    global _minikernel_system
    with _minikernel_lock:
        system          = _minikernel_system
        _minikernel_system = None

    if system:
        try:
            system.shutdown()
        except Exception:
            pass

    return {"success": True}


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
        import importlib.util
        tts_engine = "coqui" if importlib.util.find_spec("TTS") else "fallback"
        if tts_engine == "coqui":
            logger.info("Coqui TTS available — using high-fidelity voice")
        else:
            logger.info("Coqui TTS not available — avatar will use browser TTS")

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

    # Setup voice command handlers
    try:
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
    
    # Setup AI Guardian 3D bridge
    try:
        from kernel.ai_guardian_bridge import setup_guardian_eel_api
        setup_guardian_eel_api()
        logger.info("✓ AI Guardian 3D bridge enabled")
    except Exception as e:
        logger.warning(f"AI Guardian bridge not available: {e}")
        import traceback
        traceback.print_exc()

    # Setup filesystem / dynamic UI data providers used by avatar-integration.html
    try:
        from kernel.ui_data_provider import setup_ui_data_provider
        ui_provider = setup_ui_data_provider()
        
        # Setup OS Integration Manager
        try:
            from kernel.os_integration_manager import setup_os_integration
            os_integration = setup_os_integration()
            if os_integration:
                logger.info("✓ OS Integration Manager initialized")
        except Exception as e:
            logger.warning(f"OS Integration Manager not available: {e}")
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

        # Setup desktop integration
        from kernel.desktop_integration import setup_desktop_integration
        setup_desktop_integration()

        # Setup advanced desktop features
        from kernel.advanced_desktop_features import setup_advanced_desktop_features
        setup_advanced_desktop_features()
        logger.info("UI voice commands and desktop integration enabled")
    except Exception as e:
        logger.warning(f"UI voice commands not available: {e}")

    # Setup Browserbase cloud browser automation
    try:
        from kernel.browserbase_automation import setup_browserbase
        setup_browserbase()
        logger.info("Browserbase cloud browser automation enabled")
    except Exception as e:
        logger.warning(f"Browserbase automation not available: {e}")
    
    # Setup voice keyboard commands (keyboard control, annotation, dictation)
    try:
        from kernel.voice_keyboard_commands import setup_voice_keyboard_for_eel
        setup_voice_keyboard_for_eel(eel)
        
        # Setup multimodal system (gesture, AI learning, fusion)
        logger.info("Initializing multimodal AI system...")
        from kernel.multimodal_integration import setup_multimodal_eel_integration, initialize_multimodal_system
        
        # Setup Eel APIs
        multimodal_apis = setup_multimodal_eel_integration(eel)
        
        # Initialize system
        init_result = initialize_multimodal_system()
        if init_result['success']:
            logger.info("✅ Multimodal AI system initialized successfully")
        else:
            logger.warning(f"⚠️  Multimodal system initialized with warnings: {init_result.get('errors')}")
    except ImportError as e:
        logger.info(f"Multimodal system not available (optional): {e}")
    except Exception as e:
        logger.warning(f"Failed to initialize multimodal system: {e}")
        logger.info("Voice keyboard commands enabled (keyboard, annotation, dictation)")
    except Exception as e:
        logger.warning(f"Voice keyboard commands not available: {e}")
    
    # Setup DeepGram voice integration
    try:
        from kernel.deepgram_voice_integration import setup_deepgram_for_eel
        setup_deepgram_for_eel(eel)
        logger.info("✅ DeepGram voice integration registered")
    except ImportError:
        logger.info("DeepGram voice integration not available (optional)")
    except Exception as e:
        logger.warning(f"Failed to setup DeepGram integration: {e}")
    
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
        # Keep the backend alive when the browser closes so terminal sessions,
        # avatar bridge, and any long-running agent tasks continue uninterrupted.
        # The process only exits via SIGINT/SIGTERM or the in-UI quit_app() call.
        logger.info(f"Browser disconnected (page={page}); backend staying alive — {len(sockets)} socket(s) remaining")

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
        from kernel.kimi_agent import create_kimi_agent
        _agent = AgentExecutor(llm=create_kimi_agent())
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

    # ── Embedded PTY terminal — exposed to the web UI ─────────────────────
    try:
        from kernel.terminal_manager import setup_terminal_manager

        # eel.terminal_output is the JS function registered by terminal-panel.js.
        # We defer the callback wiring until after eel.start() is called below,
        # so we pass the eel module and let setup_terminal_manager wire it then.
        _terminal_mgr = setup_terminal_manager(eel)
        logger.info("Terminal manager initialized")

        @eel.expose
        def terminal_create(name: str = "shell") -> str:
            """Create a new PTY session and return its session_id."""
            return _terminal_mgr.create_session(name)

        @eel.expose
        def terminal_input(session_id: str, data: str) -> bool:
            """Write raw keystroke data to a session's PTY."""
            return _terminal_mgr.send_input(session_id, data)

        @eel.expose
        def terminal_send_command(session_id: str, command: str) -> bool:
            """Send a shell command (with newline) to a session."""
            return _terminal_mgr.send_command(session_id, command)

        @eel.expose
        def terminal_resize(session_id: str, cols: int, rows: int) -> bool:
            """Resize a terminal session (propagates SIGWINCH to the shell)."""
            return _terminal_mgr.resize(session_id, int(cols), int(rows))

        @eel.expose
        def terminal_kill(session_id: str) -> bool:
            """Kill a terminal session."""
            return _terminal_mgr.kill_session(session_id)

        @eel.expose
        def terminal_list() -> list:
            """Return metadata for all active terminal sessions."""
            return _terminal_mgr.list_sessions()

        @eel.expose
        def terminal_scrollback(session_id: str) -> str:
            """Return base64-encoded scrollback buffer for session replay."""
            return _terminal_mgr.get_scrollback_b64(session_id)

    except Exception as e:
        logger.warning(f"Terminal manager not available: {e}")
        import traceback; traceback.print_exc()

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
        startup_page = _startup_page()

        # ── Headless / Docker mode ──────────────────────────────────────────
        # When AIOS_HEADLESS=1, Eel binds on all interfaces (0.0.0.0) so the
        # host browser can reach it, and we never attempt to spawn a browser
        # inside the container.
        _headless = os.environ.get("AIOS_HEADLESS") == "1"
        _host = "0.0.0.0" if _headless else "localhost"

        if _headless:
            logger.info(
                "Headless mode — Eel serving on http://0.0.0.0:8001 "
                "(open http://localhost:8001 in your host browser)"
            )
            eel.start(
                startup_page,
                host="0.0.0.0",
                port=8001,
                size=(1280, 800),
                mode=None,
                block=True,
                close_callback=close_callback,
            )
            return  # headless path handled above

        logger.info("Starting AIOS onboarding UI on http://localhost:8001 ...")
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
                _time.sleep(1.5)
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
                            ["/usr/bin/open", "-a", app_name, url],
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

                # Fallback: open in default system browser
                try:
                    _sp.Popen(
                        ["/usr/bin/open", url],
                        stdout=_sp.DEVNULL,
                        stderr=_sp.DEVNULL,
                    )
                    logger.info("Launched default browser as fallback")
                    return True
                except Exception as e:
                    logger.warning(f"Failed to open default browser: {e}")

                logger.warning(
                    "No browser could be opened. "
                    f"Navigate manually: {url}"
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
