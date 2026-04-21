"""
WebView Display Backend

Uses pywebview to embed a lightweight system webview (WebKit/Edge/GTK)
instead of requiring a full browser installation. Reuses all existing
Three.js assets from the web/ directory.

This is the best of both worlds: the full Johnny Mnemonic Three.js
avatar with GPU-accelerated WebGL, but no Chrome/Firefox dependency.

Install: pip install pywebview
"""

import os
import json
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List

from kernel.display.base import (
    DisplayBackend,
    InputEvent,
    EventType,
    AvatarState,
    OnboardingStepView,
)

_AIOS_ROOT = Path(__file__).resolve().parent.parent.parent
WEB_FOLDER = _AIOS_ROOT / "web"


class WebViewAPI:
    """
    JavaScript-callable API exposed to the webview window.
    Mirrors the Eel-exposed functions from onboarding_gui.py but
    communicates via pywebview's native JS bridge instead.
    """

    def __init__(self, backend: "WebViewBackend"):
        self._backend = backend

    def get_current_step_data(self):
        step = self._backend._current_step
        if not step:
            return None
        return {
            "index": step.index,
            "total_steps": step.total_steps,
            "title": step.title,
            "description": step.description,
            "type": step.step_type,
        }

    def get_system_stats(self):
        return self._backend._system_stats

    def send_event(self, event_type: str, value: str = ""):
        """Called from JS when the user clicks Next/Back/etc."""
        try:
            evt_type = EventType(event_type)
        except ValueError:
            evt_type = EventType.KEY_PRESS
        self._backend._event_queue.append(InputEvent(evt_type, value))

    def process_voice_command(self, command: str):
        """Proxy voice commands to the kernel voice handler."""
        self._backend._event_queue.append(
            InputEvent(EventType.VOICE_COMMAND, command)
        )
        return {"action": "received", "success": True}


class WebViewBackend(DisplayBackend):
    def __init__(self):
        self._window = None
        self._running = False
        self._current_step: Optional[OnboardingStepView] = None
        self._avatar_state = AvatarState()
        self._messages: List[Dict[str, str]] = []
        self._system_stats: Dict[str, Any] = {}
        self._progress = (0, 0, "")
        self._event_queue: List[InputEvent] = []
        self._api = WebViewAPI(self)
        self._webview_thread: Optional[threading.Thread] = None

    def init(self, width: int = 1280, height: int = 800) -> None:
        import webview

        # Determine which HTML to load — prefer the lip-sync version,
        # fall back to the voice-enabled one, then the integration page.
        html_candidates = [
            "index-lipsync.html",
            "index-voice-enabled.html",
            "avatar-integration.html",
            "index-binary-avatar.html",
        ]
        html_file = None
        for candidate in html_candidates:
            path = WEB_FOLDER / candidate
            if path.exists():
                html_file = str(path)
                break

        if not html_file:
            raise FileNotFoundError(
                f"No HTML entry point found in {WEB_FOLDER}. "
                f"Tried: {html_candidates}"
            )

        self._window = webview.create_window(
            "AIOS — Johnny Mnemonic Neural Interface",
            url=html_file,
            js_api=self._api,
            width=width,
            height=height,
            resizable=True,
            frameless=False,
            easy_drag=False,
            text_select=False,
        )

        # pywebview.start() blocks, so run it in a thread
        self._running = True
        self._webview_thread = threading.Thread(
            target=self._run_webview, daemon=True
        )
        self._webview_thread.start()

        # Give the window a moment to open
        import time
        time.sleep(1.5)

    def _run_webview(self):
        import webview
        webview.start(debug=False)
        self._running = False

    def destroy(self) -> None:
        self._running = False
        if self._window:
            try:
                self._window.destroy()
            except Exception:
                pass
            self._window = None

    # --- rendering (push updates to JS) -----------------------------------

    def _eval_js(self, js: str) -> None:
        """Evaluate JavaScript in the webview window."""
        if self._window:
            try:
                self._window.evaluate_js(js)
            except Exception:
                pass

    def show_step(self, step: OnboardingStepView) -> None:
        self._current_step = step
        data = json.dumps({
            "index": step.index,
            "total_steps": step.total_steps,
            "title": step.title,
            "description": step.description,
            "type": step.step_type,
        })
        self._eval_js(f"window.AIOS_onStepUpdate && window.AIOS_onStepUpdate({data})")

    def show_message(self, text: str, level: str = "info") -> None:
        self._messages.append({"text": text, "level": level})
        safe_text = json.dumps(text)
        self._eval_js(
            f"window.AIOS_onMessage && window.AIOS_onMessage({safe_text}, '{level}')"
        )

    def show_progress(self, current: int, total: int, label: str = "") -> None:
        self._progress = (current, total, label)
        self._eval_js(
            f"window.AIOS_onProgress && window.AIOS_onProgress({current}, {total}, {json.dumps(label)})"
        )

    def show_avatar(self, state: AvatarState) -> None:
        self._avatar_state = state
        data = json.dumps({
            "emotion": state.emotion,
            "activity": state.activity,
            "volume": state.volume,
            "color_palette": state.color_palette,
        })
        self._eval_js(f"window.AIOS_onAvatarUpdate && window.AIOS_onAvatarUpdate({data})")

    def show_system_stats(self, stats: Dict[str, Any]) -> None:
        self._system_stats = stats
        self._eval_js(
            f"window.AIOS_onStats && window.AIOS_onStats({json.dumps(stats)})"
        )

    # --- input ------------------------------------------------------------

    def get_input(self, timeout_ms: int = 0) -> Optional[InputEvent]:
        if self._event_queue:
            return self._event_queue.pop(0)

        if timeout_ms > 0:
            import time
            deadline = time.time() + timeout_ms / 1000.0
            while time.time() < deadline:
                if self._event_queue:
                    return self._event_queue.pop(0)
                time.sleep(0.02)

        if timeout_ms < 0:
            import time
            while not self._event_queue and self._running:
                time.sleep(0.02)
            if self._event_queue:
                return self._event_queue.pop(0)

        return None

    def is_running(self) -> bool:
        return self._running

    def set_title(self, title: str) -> None:
        if self._window:
            try:
                self._window.set_title(title)
            except Exception:
                pass

    def supports_avatar(self) -> bool:
        return True  # Full Three.js avatar via webview

    def supports_audio(self) -> bool:
        return True  # Web Speech API available in webview
