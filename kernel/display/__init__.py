"""
Display Backend Auto-Detection

Probes the runtime environment and returns the best available
DisplayBackend — from full GPU rendering down to a terminal TUI.

Priority order:
  1. WebView  — desktop with webkit; reuses existing Three.js assets
  2. SDL2     — native GPU window, no browser needed
  3. TUI      — terminal / SSH / serial console (always available)
  4. DRM/KMS  — bare-metal framebuffer (future)
"""

import os
import logging
from typing import Optional

from kernel.display.base import DisplayBackend

logger = logging.getLogger("AIOS.display")


def _has_display_server() -> bool:
    """Check if a graphical display server is available."""
    return bool(
        os.environ.get("DISPLAY")
        or os.environ.get("WAYLAND_DISPLAY")
        or os.environ.get("TERM_PROGRAM")  # macOS Terminal.app / iTerm
    )


def _try_webview() -> Optional[DisplayBackend]:
    try:
        import webview  # noqa: F401
        from kernel.display.webview_backend import WebViewBackend
        return WebViewBackend()
    except ImportError:
        return None


def _try_sdl() -> Optional[DisplayBackend]:
    try:
        import sdl2  # noqa: F401
        from kernel.display.sdl_backend import SDLBackend
        return SDLBackend()
    except ImportError:
        return None


def _try_tui() -> Optional[DisplayBackend]:
    try:
        import curses  # noqa: F401
        from kernel.display.tui_backend import TUIBackend
        return TUIBackend()
    except ImportError:
        return None


def get_display_backend(prefer: Optional[str] = None) -> DisplayBackend:
    """
    Return the best available display backend.

    Parameters
    ----------
    prefer : str, optional
        Force a specific backend: "webview", "sdl", "tui", "eel".
        When set, only that backend is tried (raises if unavailable).
    """

    if prefer:
        prefer = prefer.lower()
        if prefer == "webview":
            backend = _try_webview()
        elif prefer == "sdl":
            backend = _try_sdl()
        elif prefer == "tui":
            backend = _try_tui()
        elif prefer == "eel":
            # Eel is handled separately by the existing run_onboarding.py path
            raise ValueError(
                "Eel backend is launched via run_onboarding.py, not through "
                "the native display layer. Use --mode eel or the default launcher."
            )
        else:
            raise ValueError(f"Unknown display backend: {prefer}")

        if backend is None:
            raise RuntimeError(f"Requested backend '{prefer}' is not available")
        logger.info("Display backend (forced): %s", backend.name)
        return backend

    # --- auto-detect ------------------------------------------------------

    has_gui = _has_display_server()

    if has_gui:
        # Prefer webview (reuses all existing web/ assets)
        backend = _try_webview()
        if backend:
            logger.info("Display backend (auto): WebView")
            return backend

        # Fallback to SDL2 native rendering
        backend = _try_sdl()
        if backend:
            logger.info("Display backend (auto): SDL2")
            return backend

    # Terminal / headless fallback (always works)
    backend = _try_tui()
    if backend:
        logger.info("Display backend (auto): TUI")
        return backend

    # Should never happen — curses is in stdlib
    raise RuntimeError("No display backend available (not even curses)")
