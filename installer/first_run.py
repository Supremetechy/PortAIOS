"""
First-run setup for PortAIOS.

Creates the user data tree, copies default config, and downloads any
optional models the user opts into. Idempotent — safe to call every launch.
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

MARKER_FILENAME = "first_run_complete.json"


def _copy_default_config(resource_root: Path, user_dir: Path, log: logging.Logger) -> None:
    src = resource_root / "kernel" / "security_policy.json"
    dst = user_dir / "security_policy.json"
    if src.exists() and not dst.exists():
        shutil.copy2(src, dst)
        log.info("Installed default security policy -> %s", dst)


def _ensure_dirs(user_dir: Path) -> None:
    for sub in ("logs", "models", "cache"):
        (user_dir / sub).mkdir(parents=True, exist_ok=True)


def _write_marker(user_dir: Path) -> None:
    marker = user_dir / MARKER_FILENAME
    marker.write_text(json.dumps({"version": 1, "complete": True}, indent=2))


def _is_first_run(user_dir: Path) -> bool:
    return not (user_dir / MARKER_FILENAME).exists()


def ensure_ready(resource_root: Path, user_dir: Path, log: logging.Logger) -> None:
    """Run every launch. Does expensive work only on first run."""
    _ensure_dirs(user_dir)

    if not _is_first_run(user_dir):
        log.info("First-run setup already complete")
        return

    log.info("Running first-run setup...")
    _copy_default_config(resource_root, user_dir, log)
    _write_marker(user_dir)
    log.info("First-run setup complete")
