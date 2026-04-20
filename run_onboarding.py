#!/usr/bin/env python3
"""
AI-OS Onboarding Launcher
Starts the unified Eel-based onboarding wizard with binary avatar support.
This is the single entry point — run_aios_with_avatar.py redirects here.
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AIOS")


def _dispatch_subprocess_mode() -> bool:
    # PyInstaller makes sys.executable point to this launcher, so the kernel
    # passes `--subprocess <mode>` when it wants a helper process. Route to
    # the real script here instead of re-running the onboarding GUI (which
    # previously caused an infinite boot loop).
    if len(sys.argv) < 3 or sys.argv[1] != "--subprocess":
        return False

    mode = sys.argv[2]
    sys.argv = [sys.argv[0], *sys.argv[3:]]
    root = Path(__file__).resolve().parent

    if mode == "avatar-bridge":
        import importlib.util
        import asyncio
        spec = importlib.util.spec_from_file_location(
            "avatar_bridge", root / "web" / "avatar-bridge.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        asyncio.run(module.main())
        return True

    if mode == "kernel":
        import runpy
        runpy.run_path(str(root / "aios_kernel.py"), run_name="__main__")
        return True

    logger.error(f"Unknown --subprocess mode: {mode}")
    sys.exit(2)


def check_dependencies():
    missing = []
    for pkg in ("eel", "bottle", "websockets", "numpy", "psutil"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    return missing


def main():
    logger.info("=" * 60)
    logger.info("AIOS Onboarding — Binary Avatar Integration")
    logger.info("=" * 60)

    missing = check_dependencies()
    if missing:
        logger.error(f"Missing dependencies: {', '.join(missing)}")
        logger.info(f"Install with: pip install {' '.join(missing)}")
        sys.exit(1)

    web_folder = Path(__file__).parent / "web"
    if not web_folder.is_dir():
        logger.error(f"Web folder not found at: {web_folder}")
        sys.exit(1)

    logger.info("Starting unified onboarding wizard with avatar...")
    from kernel.onboarding_gui import start_eel_app
    start_eel_app()


if __name__ == "__main__":
    if not _dispatch_subprocess_mode():
        main()
