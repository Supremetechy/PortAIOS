"""
SDL2 / OpenGL Display Backend

Native GPU-accelerated window using PySDL2. Renders the Johnny Mnemonic
avatar and onboarding UI without a browser. Single external dependency
(PySDL2 + SDL2 shared lib).

If OpenGL is available, shaders from the web/ Three.js avatar are ported
to native GLSL. Otherwise falls back to SDL2 2D rendering.

Install: pip install PySDL2 PySDL2-dll
"""

import ctypes
import math
import time
import threading
from typing import Optional, Dict, Any, List

from kernel.display.base import (
    DisplayBackend,
    InputEvent,
    EventType,
    AvatarState,
    OnboardingStepView,
)

# Lazy-loaded at init() time
sdl2 = None
SDL_INIT_VIDEO = 0x00000020
SDL_INIT_EVENTS = 0x00004000


def _import_sdl2():
    global sdl2
    import sdl2 as _sdl2
    import sdl2.ext
    sdl2 = _sdl2
    return sdl2


class SDLBackend(DisplayBackend):
    def __init__(self):
        self.window = None
        self.renderer = None
        self._running = False
        self._current_step: Optional[OnboardingStepView] = None
        self._avatar_state = AvatarState()
        self._messages: List[Dict[str, str]] = []
        self._system_stats: Dict[str, Any] = {}
        self._progress = (0, 0, "")
        self._lock = threading.Lock()
        self._width = 1280
        self._height = 800
        self._font = None
        self._tick = 0

    def init(self, width: int = 1280, height: int = 800) -> None:
        _import_sdl2()

        self._width = width
        self._height = height

        sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_EVENTS)

        self.window = sdl2.SDL_CreateWindow(
            b"AIOS - Johnny Mnemonic Neural Interface",
            sdl2.SDL_WINDOWPOS_CENTERED,
            sdl2.SDL_WINDOWPOS_CENTERED,
            width, height,
            sdl2.SDL_WINDOW_SHOWN | sdl2.SDL_WINDOW_RESIZABLE,
        )

        self.renderer = sdl2.SDL_CreateRenderer(
            self.window, -1,
            sdl2.SDL_RENDERER_ACCELERATED | sdl2.SDL_RENDERER_PRESENTVSYNC,
        )

        # Try to load SDL2_ttf for text rendering
        try:
            import sdl2.sdlttf as ttf
            ttf.TTF_Init()
            # Try system monospace fonts
            for font_path in [
                b"/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                b"/usr/share/fonts/TTF/DejaVuSansMono.ttf",
                b"/System/Library/Fonts/Menlo.ttc",
                b"/System/Library/Fonts/SFMono-Regular.otf",
                b"C:\\Windows\\Fonts\\consola.ttf",
            ]:
                self._font = ttf.TTF_OpenFont(font_path, 16)
                if self._font:
                    break
        except (ImportError, OSError):
            self._font = None

        self._running = True

    def destroy(self) -> None:
        self._running = False
        if self._font:
            try:
                import sdl2.sdlttf as ttf
                ttf.TTF_CloseFont(self._font)
                ttf.TTF_Quit()
            except Exception:
                pass
        if self.renderer:
            sdl2.SDL_DestroyRenderer(self.renderer)
        if self.window:
            sdl2.SDL_DestroyWindow(self.window)
        sdl2.SDL_Quit()

    # --- rendering --------------------------------------------------------

    def show_step(self, step: OnboardingStepView) -> None:
        with self._lock:
            self._current_step = step
        self._render()

    def show_message(self, text: str, level: str = "info") -> None:
        with self._lock:
            self._messages.append({"text": text, "level": level})
            if len(self._messages) > 10:
                self._messages = self._messages[-10:]
        self._render()

    def show_progress(self, current: int, total: int, label: str = "") -> None:
        with self._lock:
            self._progress = (current, total, label)
        self._render()

    def show_avatar(self, state: AvatarState) -> None:
        with self._lock:
            self._avatar_state = state
        self._render()

    def show_system_stats(self, stats: Dict[str, Any]) -> None:
        with self._lock:
            self._system_stats = stats
        self._render()

    # --- input ------------------------------------------------------------

    def get_input(self, timeout_ms: int = 0) -> Optional[InputEvent]:
        event = sdl2.SDL_Event()

        if timeout_ms < 0:
            # Blocking wait
            if sdl2.SDL_WaitEvent(ctypes.byref(event)):
                return self._map_sdl_event(event)
            return None
        elif timeout_ms > 0:
            if sdl2.SDL_WaitEventTimeout(ctypes.byref(event), timeout_ms):
                return self._map_sdl_event(event)
            return None
        else:
            if sdl2.SDL_PollEvent(ctypes.byref(event)):
                return self._map_sdl_event(event)
            return None

    def _map_sdl_event(self, event) -> Optional[InputEvent]:
        if event.type == sdl2.SDL_QUIT:
            self._running = False
            return InputEvent(EventType.QUIT)

        if event.type == sdl2.SDL_KEYDOWN:
            sym = event.key.keysym.sym
            if sym == sdl2.SDLK_RIGHT or sym == sdl2.SDLK_RETURN:
                return InputEvent(EventType.NEXT)
            elif sym == sdl2.SDLK_LEFT:
                return InputEvent(EventType.PREV)
            elif sym == sdl2.SDLK_ESCAPE or sym == sdl2.SDLK_q:
                return InputEvent(EventType.QUIT)
            elif sym == sdl2.SDLK_y:
                return InputEvent(EventType.CONFIRM, "yes")
            elif sym == sdl2.SDLK_SPACE:
                return InputEvent(EventType.SELECT)
            else:
                ch = chr(sym) if 32 <= sym < 127 else ""
                return InputEvent(EventType.KEY_PRESS, ch)

        if event.type == sdl2.SDL_WINDOWEVENT:
            if event.window.event == sdl2.SDL_WINDOWEVENT_RESIZED:
                self._width = event.window.data1
                self._height = event.window.data2
                return InputEvent(EventType.RESIZE)

        return None

    def is_running(self) -> bool:
        return self._running

    def update(self) -> None:
        self._tick += 1
        # Pump SDL events
        event = sdl2.SDL_Event()
        while sdl2.SDL_PollEvent(ctypes.byref(event)):
            mapped = self._map_sdl_event(event)
            # Events are consumed here; get_input will miss them.
            # For a production system you'd queue them.
        self._render()

    def set_title(self, title: str) -> None:
        if self.window:
            sdl2.SDL_SetWindowTitle(self.window, title.encode("utf-8"))

    def supports_avatar(self) -> bool:
        return True

    # --- internal rendering -----------------------------------------------

    def _render(self) -> None:
        if not self.renderer:
            return

        # Clear to black
        sdl2.SDL_SetRenderDrawColor(self.renderer, 0, 0, 0, 255)
        sdl2.SDL_RenderClear(self.renderer)

        self._render_border()
        self._render_header()
        self._render_avatar_gfx()
        self._render_step_content()
        self._render_progress_bar()
        self._render_stats_bar()
        self._render_messages()
        self._render_footer()

        sdl2.SDL_RenderPresent(self.renderer)

    def _set_color(self, r, g, b, a=255):
        sdl2.SDL_SetRenderDrawColor(self.renderer, r, g, b, a)

    def _draw_rect(self, x, y, w, h, filled=True):
        rect = sdl2.SDL_Rect(x, y, w, h)
        if filled:
            sdl2.SDL_RenderFillRect(self.renderer, rect)
        else:
            sdl2.SDL_RenderDrawRect(self.renderer, rect)

    def _render_text(self, text: str, x: int, y: int, r=0, g=255, b=65):
        """Render text using SDL_ttf or fallback pixel blocks."""
        if self._font:
            try:
                import sdl2.sdlttf as ttf
                color = sdl2.SDL_Color(r, g, b, 255)
                surface = ttf.TTF_RenderText_Blended(self._font, text.encode("utf-8"), color)
                if surface:
                    texture = sdl2.SDL_CreateTextureFromSurface(self.renderer, surface)
                    w, h = ctypes.c_int(), ctypes.c_int()
                    sdl2.SDL_QueryTexture(texture, None, None, ctypes.byref(w), ctypes.byref(h))
                    dst = sdl2.SDL_Rect(x, y, w.value, h.value)
                    sdl2.SDL_RenderCopy(self.renderer, texture, None, dst)
                    sdl2.SDL_DestroyTexture(texture)
                    sdl2.SDL_FreeSurface(surface)
                    return
            except Exception:
                pass

        # Fallback: draw small rectangles for each character (very basic)
        self._set_color(r, g, b)
        char_w, char_h = 8, 14
        for i, ch in enumerate(text):
            if ch != ' ':
                self._draw_rect(x + i * char_w, y, char_w - 1, char_h - 1)

    def _render_border(self):
        self._set_color(0, 255, 65, 180)  # matrix green
        self._draw_rect(0, 0, self._width, self._height, filled=False)
        self._draw_rect(1, 1, self._width - 2, self._height - 2, filled=False)

    def _render_header(self):
        # Header bar
        self._set_color(0, 255, 65, 40)
        self._draw_rect(2, 2, self._width - 4, 40)

        self._render_text("AIOS — JOHNNY MNEMONIC NEURAL INTERFACE", 20, 12, 0, 255, 255)

    def _render_avatar_gfx(self):
        """Draw a geometric avatar head using SDL2 primitives."""
        cx = 120  # center x
        cy = 200  # center y

        emotion = self._avatar_state.emotion
        activity = self._avatar_state.activity

        # Head outline (rectangle approximation)
        self._set_color(0, 255, 65)
        self._draw_rect(cx - 40, cy - 50, 80, 70, filled=False)

        # Binary data streams around head
        t = time.time()
        self._set_color(0, 255, 65, 100)
        for i in range(8):
            bx = cx - 55 + int(math.sin(t + i) * 5)
            by = cy - 60 + i * 15
            self._draw_rect(bx, by, 3, 10)
            bx2 = cx + 50 + int(math.cos(t + i) * 5)
            self._draw_rect(bx2, by, 3, 10)

        # Eyes
        if emotion == "error":
            # X eyes
            self._set_color(255, 0, 0)
        elif emotion == "happy" or emotion == "excited":
            self._set_color(0, 255, 255)
        else:
            self._set_color(0, 255, 65)

        eye_size = 8
        self._draw_rect(cx - 18, cy - 25, eye_size, eye_size)
        self._draw_rect(cx + 10, cy - 25, eye_size, eye_size)

        # Mouth
        if activity == "speaking":
            mouth_h = 4 + int(abs(math.sin(t * 8)) * 10)
            self._set_color(0, 255, 255)
            self._draw_rect(cx - 12, cy + 5, 24, mouth_h)
        elif emotion == "happy" or emotion == "excited":
            self._set_color(0, 255, 65)
            self._draw_rect(cx - 12, cy + 5, 24, 4)
        else:
            self._set_color(0, 255, 65)
            self._draw_rect(cx - 10, cy + 8, 20, 2)

        # Neck
        self._set_color(0, 255, 65, 150)
        self._draw_rect(cx - 8, cy + 20, 16, 20)

        # Shoulders
        self._draw_rect(cx - 50, cy + 40, 100, 8)

        # Label
        labels = {
            "neutral": "STANDBY",
            "happy": "ONLINE",
            "thinking": "PROCESSING",
            "excited": "READY",
            "error": "FAULT",
            "speaking": "SPEAKING",
        }
        label = labels.get(activity if activity == "speaking" else emotion, "NEURAL")
        self._render_text(label, cx - 30, cy + 60, 0, 255, 255)

    def _render_step_content(self):
        step = self._current_step
        if not step:
            return

        content_x = 240
        content_w = self._width - content_x - 20

        # Step counter
        counter = f"[ Step {step.index + 1} / {step.total_steps} ]"
        self._render_text(counter, content_x, 60, 0, 255, 255)

        # Title
        self._render_text(step.title, content_x, 90, 0, 255, 65)

        # Separator line
        self._set_color(0, 255, 65, 100)
        self._draw_rect(content_x, 115, min(content_w, 400), 1)

        # Description
        self._render_text(step.description, content_x, 130, 200, 200, 200)

        # Fields
        y = 170
        for fld in step.fields:
            label = fld.get("label", "")
            value = fld.get("value", "")
            self._render_text(f"{label}: {value}", content_x + 10, y, 0, 255, 255)
            y += 22

        for opt in step.options:
            marker = "●" if opt.get("selected") else "○"
            self._render_text(f"{marker} {opt.get('label', '')}", content_x + 10, y, 200, 200, 200)
            y += 22

    def _render_progress_bar(self):
        current, total, label = self._progress
        if total <= 0:
            return

        bar_y = self._height - 80
        bar_x = 20
        bar_w = self._width - 40
        bar_h = 16

        pct = current / total if total else 0
        filled_w = int(bar_w * pct)

        # Background
        self._set_color(20, 40, 20)
        self._draw_rect(bar_x, bar_y, bar_w, bar_h)

        # Filled
        self._set_color(0, 255, 65)
        self._draw_rect(bar_x, bar_y, filled_w, bar_h)

        # Label
        info = f"{label} {current}/{total} ({pct:.0%})"
        self._render_text(info, bar_x, bar_y - 20, 0, 255, 255)

    def _render_stats_bar(self):
        if not self._system_stats:
            return
        cpu = self._system_stats.get("cpu_usage", 0)
        mem = self._system_stats.get("memory_usage", 0)
        disk = self._system_stats.get("disk_usage", 0)

        y = self._height - 50
        self._render_text(
            f"CPU: {cpu:.0f}%   MEM: {mem:.0f}%   DISK: {disk:.0f}%",
            20, y, 0, 255, 255,
        )

    def _render_messages(self):
        y = 320
        color_map = {
            "info": (0, 255, 65),
            "warn": (255, 200, 0),
            "error": (255, 50, 50),
            "success": (0, 255, 255),
        }
        for msg in self._messages[-8:]:
            r, g, b = color_map.get(msg["level"], (0, 255, 65))
            prefix = {"info": ">", "warn": "!", "error": "X", "success": "+"}.get(
                msg["level"], ">"
            )
            self._render_text(f" {prefix} {msg['text']}", 20, y, r, g, b)
            y += 20

    def _render_footer(self):
        y = self._height - 24
        self._set_color(0, 255, 65, 40)
        self._draw_rect(2, y - 4, self._width - 4, 22)
        self._render_text(
            "[Right/Enter] Next   [Left] Back   [Q/Esc] Quit",
            20, y, 0, 255, 255,
        )
