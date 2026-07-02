# PyInstaller spec — shared across macOS / Windows / Linux.
# Build from the project root:
#     pyinstaller installer/PortAIOS.spec --noconfirm
#
# Platform-specific build scripts in installer/{macos,windows,linux}/
# invoke this file after ensuring deps are installed.

# ruff: noqa
import sys
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).resolve().parent
INSTALLER_DIR = PROJECT_ROOT / "installer"

block_cipher = None

datas = [
    (str(PROJECT_ROOT / "web"),    "web"),
    (str(PROJECT_ROOT / "assets"), "assets"),
    (str(PROJECT_ROOT / "models"), "models"),
    (str(PROJECT_ROOT / "kernel" / "security_policy.json"), "kernel"),
]

hiddenimports = [
    # Web / async
    "eel",
    "bottle",
    "bottle_websocket",
    "gevent",
    "gevent.monkey",
    "websockets",
    "websockets.legacy",
    "websockets.legacy.server",
    "websockets.legacy.client",
    "websockets.http11",
    "websockets.datastructures",
    # Numerics / data / media
    "numpy",
    "scipy",
    "pandas",
    "sklearn",
    "sklearn.utils",
    "trimesh",
    "trimesh.visual",
    "trimesh.creation",
    "psutil",
    "GPUtil",
    "soundfile",
    "PIL",
    # Computer vision / gesture
    "cv2",
    "mediapipe",
    # Browser automation
    "browserbase",
    "playwright",
    "playwright.sync_api",
    "playwright.async_api",
    # Kernel — core
    "kernel",
    "kernel.boot",
    "kernel.onboarding",
    "kernel.onboarding_gui",
    "kernel.onboarding_gui_fallback",
    "kernel.hardware_detection",
    "kernel.system_monitor",
    "kernel.compatibility_checker",
    "kernel.system_updater",
    "kernel.security",
    "kernel.security_cli",
    # Kernel — voice / avatar
    "kernel.voice_commands",
    "kernel.voice_assistant",
    "kernel.viseme_integration",
    "kernel.piper_viseme_server",
    "kernel.ui_voice_commands",
    "kernel.voice_keyboard_commands",
    "kernel.avatar_generator",
    "kernel.avatar_creation_server",
    "kernel.avatar_storage",
    # Kernel — AI / compute
    "kernel.agent_commands",
    "kernel.agent_executor",
    "kernel.ai_file_operations",
    "kernel.ai_learning_engine",
    "kernel.ai_learning_enhanced",
    "kernel.model_manager",
    "kernel.distributed_training",
    "kernel.container_runtime",
    "kernel.scheduler",
    "kernel.resource_manager",
    # Kernel — multimodal / gesture
    "kernel.multimodal_controller",
    "kernel.multimodal_integration",
    "kernel.gesture_controller",
    "kernel.gesture_commands",
    # Kernel — browser automation
    "kernel.browserbase_automation",
    # Kernel — system / UI
    "kernel.filesystem",
    "kernel.network",
    "kernel.desktop_integration",
    "kernel.advanced_desktop_features",
    "kernel.os_integration_manager",
    "kernel.terminal_manager",
    "kernel.ui_data_provider",
    # Installer
    "installer.first_run",
]

# Heavy optional deps — excluded unless PORTAIOS_INCLUDE_TTS=1 is set at build time
import os
if os.environ.get("PORTAIOS_INCLUDE_TTS") != "1":
    excludes = ["TTS", "torch", "torchaudio", "transformers", "pyaudio", "PyQt6", "cv2"]
else:
    excludes = []
    hiddenimports.extend(["TTS", "torch", "pyaudio"])

a = Analysis(
    [str(INSTALLER_DIR / "launcher.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Platform-specific icon
if sys.platform == "darwin":
    icon_file = str(INSTALLER_DIR / "icons" / "PortAIOS.icns")
elif sys.platform == "win32":
    icon_file = str(INSTALLER_DIR / "icons" / "PortAIOS.ico")
else:
    icon_file = str(INSTALLER_DIR / "icons" / "PortAIOS.png")

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PortAIOS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # windowed app, no terminal
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=(
        str(INSTALLER_DIR / "macos" / "entitlements.plist")
        if sys.platform == "darwin"
        else None
    ),
    icon=icon_file if Path(icon_file).exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="PortAIOS",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="PortAIOS.app",
        icon=icon_file if Path(icon_file).exists() else None,
        bundle_identifier="com.portaios.app",
        version="1.0.0",
        info_plist={
            "CFBundleName": "PortAIOS",
            "CFBundleDisplayName": "PortAIOS",
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "LSMinimumSystemVersion": "10.15.0",
            "NSHighResolutionCapable": True,
            "NSMicrophoneUsageDescription": "PortAIOS uses the microphone for voice input.",
            "NSCameraUsageDescription": "PortAIOS may use the camera for avatar features.",
        },
    )
