"""
PortAIOS desktop launcher — PyInstaller entry point.

When frozen (bundled via PyInstaller) resources live in sys._MEIPASS.
When run from source they live relative to this file. Both paths are
resolved here so the rest of the app can import normally.
"""

from __future__ import annotations

import logging
import os
import runpy
import sys
from pathlib import Path


def _resource_root() -> Path:
    """Root containing bundled resources (kernel/, web/, assets/, models/)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def _run_subprocess_mode(mode: str, extra_args: list[str]) -> int:
    """Dispatch a --subprocess <mode> invocation to the correct backend script.

    Under PyInstaller, sys.executable is the launcher binary itself. Any
    Popen([sys.executable, ...]) re-enters this process. Without this handler
    the child would fall through to main() and start another GUI — creating
    an infinite browser-tab + subprocess spawn loop.
    """
    resource_root = _resource_root()
    sys.path.insert(0, str(resource_root))

    if mode == "avatar-bridge":
        script = resource_root / "web" / "avatar-bridge.py"
        if not script.exists():
            print(f"avatar-bridge script missing at {script}", file=sys.stderr)
            return 2
        sys.argv = [str(script), *extra_args]
        runpy.run_path(str(script), run_name="__main__")
        return 0

    if mode == "kernel":
        script = resource_root / "aios_kernel.py"
        if not script.exists():
            print(f"kernel script missing at {script}", file=sys.stderr)
            return 2
        sys.argv = [str(script), *extra_args]
        runpy.run_path(str(script), run_name="__main__")
        return 0

    print(f"Unknown --subprocess mode: {mode!r}", file=sys.stderr)
    return 2


def _user_data_dir() -> Path:
    """Per-user writable dir for config, logs, downloaded models."""
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "PortAIOS"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home())) / "PortAIOS"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "PortAIOS"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _configure_logging(user_dir: Path) -> logging.Logger:
    log_file = user_dir / "portaios.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )
    return logging.getLogger("PortAIOS.launcher")


def _show_error(message: str) -> None:
    """Best-effort error dialog for non-technical users."""
    try:
        if sys.platform == "darwin":
            import subprocess
            subprocess.run(
                ["osascript", "-e", f'display dialog "{message}" with icon stop buttons {{"OK"}}'],
                check=False,
            )
        elif sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, message, "PortAIOS", 0x10)
        else:
            import subprocess
            subprocess.run(["zenity", "--error", "--text", message], check=False)
    except Exception:
        print(f"PortAIOS error: {message}", file=sys.stderr)


def main() -> int:
    # Intercept subprocess dispatch BEFORE any GUI/first-run work. This must
    # stay at the top of main() — under PyInstaller every Popen(sys.executable)
    # re-enters here, so anything above this line runs once per spawned child.
    if len(sys.argv) >= 3 and sys.argv[1] == "--subprocess":
        return _run_subprocess_mode(sys.argv[2], sys.argv[3:])

    # Belt-and-braces guard: if the GUI is already running in an ancestor,
    # refuse to start a second one. Prevents runaway tab loops even if a
    # future subprocess call forgets the --subprocess flag.
    if os.environ.get("PORTAIOS_GUI_RUNNING") == "1":
        print("PortAIOS GUI already running in ancestor process; exiting child.", file=sys.stderr)
        return 0

    user_dir = _user_data_dir()
    log = _configure_logging(user_dir)

    resource_root = _resource_root()
    log.info("PortAIOS starting")
    log.info("Resource root: %s", resource_root)
    log.info("User data dir: %s", user_dir)

    sys.path.insert(0, str(resource_root))
    os.chdir(resource_root)

    try:
        from installer.first_run import ensure_ready
        ensure_ready(resource_root, user_dir, log)
    except Exception as exc:
        log.exception("First-run setup failed")
        _show_error(f"PortAIOS setup failed:\n{exc}")
        return 1

    try:
        from kernel.onboarding_gui import start_eel_app
        start_eel_app()
    except Exception as exc:
        log.exception("Application crashed")
        _show_error(f"PortAIOS crashed — see log at:\n{user_dir / 'portaios.log'}\n\n{exc}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
