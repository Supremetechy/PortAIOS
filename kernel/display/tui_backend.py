"""
TUI (Terminal User Interface) Display Backend

Uses Python's built-in curses module to render the onboarding UI
directly in the terminal. Works over SSH, serial console, or any
terminal emulator — zero external dependencies.

Provides a Johnny Mnemonic-themed ASCII interface with:
  - Box-drawing borders and progress bars
  - Animated ASCII avatar with emotion states
  - Color-coded status messages (green/cyan/amber/red)
  - Keyboard navigation (arrow keys, Enter, q to quit)
"""

import curses
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


# ASCII avatar frames by emotion
AVATAR_FRAMES = {
    "neutral": [
        "   ╔═══════╗   ",
        "   ║ 01001 ║   ",
        "   ║ █▀▀▀█ ║   ",
        "   ║ █ ● ● ║   ",
        "   ║ █  ▄  ║   ",
        "   ║ █▄▄▄█ ║   ",
        "   ║ 10110 ║   ",
        "   ╚═══════╝   ",
        "    ║█████║    ",
        "   ╔╩═════╩╗   ",
        "   ║ NEURAL ║   ",
        "   ╚═══════╝   ",
    ],
    "happy": [
        "   ╔═══════╗   ",
        "   ║ 01001 ║   ",
        "   ║ █▀▀▀█ ║   ",
        "   ║ █ ◉ ◉ ║   ",
        "   ║ █ ╰╯  ║   ",
        "   ║ █▄▄▄█ ║   ",
        "   ║ 10110 ║   ",
        "   ╚═══════╝   ",
        "    ║█████║    ",
        "   ╔╩═════╩╗   ",
        "   ║ ONLINE ║   ",
        "   ╚═══════╝   ",
    ],
    "thinking": [
        "   ╔═══════╗   ",
        "   ║ 01001 ║   ",
        "   ║ █▀▀▀█ ║   ",
        "   ║ █ ◦ ◦ ║   ",
        "   ║ █  ═  ║   ",
        "   ║ █▄▄▄█ ║   ",
        "   ║ ..... ║   ",
        "   ╚═══════╝   ",
        "    ║█████║    ",
        "   ╔╩═════╩╗   ",
        "   ║PROCESS ║   ",
        "   ╚═══════╝   ",
    ],
    "excited": [
        "   ╔═══════╗   ",
        "   ║ 01001 ║   ",
        "   ║ █▀▀▀█ ║   ",
        "   ║ █ ★ ★ ║   ",
        "   ║ █ ╰╯  ║   ",
        "   ║ █▄▄▄█ ║   ",
        "   ║ !!!!! ║   ",
        "   ╚═══════╝   ",
        "    ║█████║    ",
        "   ╔╩═════╩╗   ",
        "   ║ READY! ║   ",
        "   ╚═══════╝   ",
    ],
    "error": [
        "   ╔═══════╗   ",
        "   ║ ERROR ║   ",
        "   ║ █▀▀▀█ ║   ",
        "   ║ █ X X ║   ",
        "   ║ █  ▲  ║   ",
        "   ║ █▄▄▄█ ║   ",
        "   ║ !!ERR ║   ",
        "   ╚═══════╝   ",
        "    ║█████║    ",
        "   ╔╩═════╩╗   ",
        "   ║ FAULT! ║   ",
        "   ╚═══════╝   ",
    ],
    "speaking": [
        "   ╔═══════╗   ",
        "   ║ 01001 ║   ",
        "   ║ █▀▀▀█ ║   ",
        "   ║ █ ● ● ║   ",
        "   ║ █ ╰─╯ ║   ",
        "   ║ █▄▄▄█ ║   ",
        "   ║ >>>>> ║   ",
        "   ╚═══════╝   ",
        "    ║█████║    ",
        "   ╔╩═════╩╗   ",
        "   ║SPEAKNG ║   ",
        "   ╚═══════╝   ",
    ],
}

# Speaking mouth animation frames
MOUTH_FRAMES = [" █  ▄  ", " █ ╰╯  ", " █ ╰─╯ ", " █ ╰══╯"]


class TUIBackend(DisplayBackend):
    def __init__(self):
        self.screen = None
        self._running = False
        self._current_step: Optional[OnboardingStepView] = None
        self._avatar_state = AvatarState()
        self._messages: List[Dict[str, str]] = []
        self._system_stats: Dict[str, Any] = {}
        self._progress = (0, 0, "")
        self._input_queue: List[InputEvent] = []
        self._lock = threading.Lock()
        self._mouth_frame = 0
        self._anim_tick = 0

    def init(self, width: int = 1280, height: int = 800) -> None:
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.curs_set(0)
        self.screen.keypad(True)
        self.screen.nodelay(True)  # non-blocking getch

        if curses.has_colors():
            curses.start_color()
            curses.use_default_colors()
            # Color pairs: (foreground, background)
            curses.init_pair(1, curses.COLOR_GREEN, -1)    # matrix green
            curses.init_pair(2, curses.COLOR_CYAN, -1)     # cyan highlights
            curses.init_pair(3, curses.COLOR_YELLOW, -1)   # amber / warning
            curses.init_pair(4, curses.COLOR_RED, -1)      # error
            curses.init_pair(5, curses.COLOR_WHITE, -1)    # normal text
            curses.init_pair(6, curses.COLOR_GREEN, curses.COLOR_BLACK)  # header
            curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_GREEN)  # inverted

        self._running = True
        self._draw_full()

    def destroy(self) -> None:
        self._running = False
        if self.screen:
            curses.nocbreak()
            self.screen.keypad(False)
            curses.echo()
            curses.endwin()
            self.screen = None

    # --- rendering --------------------------------------------------------

    def show_step(self, step: OnboardingStepView) -> None:
        with self._lock:
            self._current_step = step
        self._draw_full()

    def show_message(self, text: str, level: str = "info") -> None:
        with self._lock:
            self._messages.append({"text": text, "level": level})
            if len(self._messages) > 8:
                self._messages = self._messages[-8:]
        self._draw_messages()

    def show_progress(self, current: int, total: int, label: str = "") -> None:
        with self._lock:
            self._progress = (current, total, label)
        self._draw_progress()

    def show_avatar(self, state: AvatarState) -> None:
        with self._lock:
            self._avatar_state = state
        self._draw_avatar()

    def show_system_stats(self, stats: Dict[str, Any]) -> None:
        with self._lock:
            self._system_stats = stats
        self._draw_stats()

    # --- input ------------------------------------------------------------

    def get_input(self, timeout_ms: int = 0) -> Optional[InputEvent]:
        if not self.screen:
            return None

        if timeout_ms < 0:
            self.screen.nodelay(False)
        elif timeout_ms > 0:
            self.screen.timeout(timeout_ms)
        else:
            self.screen.nodelay(True)

        try:
            key = self.screen.getch()
        except curses.error:
            return None
        finally:
            self.screen.nodelay(True)

        if key == -1:
            return None

        # Map keys to events
        if key == curses.KEY_RIGHT or key == ord('n') or key == ord('\n'):
            return InputEvent(EventType.NEXT)
        elif key == curses.KEY_LEFT or key == ord('b'):
            return InputEvent(EventType.PREV)
        elif key == ord('q') or key == 27:  # q or ESC
            return InputEvent(EventType.QUIT)
        elif key == ord('y'):
            return InputEvent(EventType.CONFIRM, "yes")
        elif key == ord(' '):
            return InputEvent(EventType.SELECT)
        elif key == curses.KEY_RESIZE:
            self._draw_full()
            return InputEvent(EventType.RESIZE)
        else:
            return InputEvent(EventType.KEY_PRESS, chr(key) if 32 <= key < 127 else "")

    def is_running(self) -> bool:
        return self._running

    def update(self) -> None:
        self._anim_tick += 1
        if self._avatar_state.activity == "speaking" and self._anim_tick % 3 == 0:
            self._mouth_frame = (self._mouth_frame + 1) % len(MOUTH_FRAMES)
            self._draw_avatar()

    def set_title(self, title: str) -> None:
        # xterm-compatible title escape
        import sys
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()

    def supports_avatar(self) -> bool:
        return True  # ASCII avatar

    # --- internal drawing -------------------------------------------------

    def _safe_addstr(self, y: int, x: int, text: str, attr=0) -> None:
        """Write text, silently ignoring out-of-bounds."""
        if not self.screen:
            return
        try:
            max_y, max_x = self.screen.getmaxyx()
            if y < 0 or y >= max_y or x < 0:
                return
            # Truncate to fit
            available = max_x - x
            if available <= 0:
                return
            self.screen.addnstr(y, x, text, available, attr)
        except curses.error:
            pass

    def _draw_full(self) -> None:
        if not self.screen:
            return
        try:
            self.screen.clear()
            self._draw_header()
            self._draw_avatar()
            self._draw_step_content()
            self._draw_progress()
            self._draw_stats()
            self._draw_messages()
            self._draw_footer()
            self.screen.refresh()
        except curses.error:
            pass

    def _draw_header(self) -> None:
        max_y, max_x = self.screen.getmaxyx()
        green = curses.color_pair(1) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
        cyan = curses.color_pair(2) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD

        border = "═" * (max_x - 2)
        self._safe_addstr(0, 0, "╔" + border + "╗", green)
        title = "AIOS — JOHNNY MNEMONIC NEURAL INTERFACE"
        pad = (max_x - 2 - len(title)) // 2
        self._safe_addstr(1, 0, "║", green)
        self._safe_addstr(1, 1 + pad, title, cyan)
        self._safe_addstr(1, max_x - 1, "║", green)
        self._safe_addstr(2, 0, "╠" + border + "╣", green)

    def _draw_avatar(self) -> None:
        if not self.screen:
            return
        max_y, max_x = self.screen.getmaxyx()
        green = curses.color_pair(1) if curses.has_colors() else 0
        cyan = curses.color_pair(2) if curses.has_colors() else 0

        emotion = self._avatar_state.emotion
        activity = self._avatar_state.activity

        # Pick frames
        if activity == "speaking":
            frames = AVATAR_FRAMES.get("speaking", AVATAR_FRAMES["neutral"])
        else:
            frames = AVATAR_FRAMES.get(emotion, AVATAR_FRAMES["neutral"])

        # Draw in left column
        start_y = 4
        start_x = 2
        for i, line in enumerate(frames):
            color = cyan if i in (0, 7) else green
            self._safe_addstr(start_y + i, start_x, line, color)

        # Animate mouth when speaking
        if activity == "speaking":
            mouth = MOUTH_FRAMES[self._mouth_frame]
            self._safe_addstr(start_y + 4, start_x + 4, mouth, green)

    def _draw_step_content(self) -> None:
        if not self.screen or not self._current_step:
            return

        max_y, max_x = self.screen.getmaxyx()
        green = curses.color_pair(1) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD
        cyan = curses.color_pair(2) if curses.has_colors() else 0
        white = curses.color_pair(5) if curses.has_colors() else 0

        step = self._current_step
        content_x = 22  # Right of avatar
        content_w = max_x - content_x - 2

        # Step counter
        counter = f"[ Step {step.index + 1} / {step.total_steps} ]"
        self._safe_addstr(4, content_x, counter, cyan)

        # Title
        self._safe_addstr(6, content_x, step.title, green)

        # Separator
        self._safe_addstr(7, content_x, "─" * min(content_w, 40), green)

        # Description (word-wrap)
        desc = step.description
        y = 9
        while desc and y < max_y - 8:
            if len(desc) <= content_w:
                self._safe_addstr(y, content_x, desc, white)
                break
            # Find wrap point
            wrap = desc[:content_w].rfind(' ')
            if wrap <= 0:
                wrap = content_w
            self._safe_addstr(y, content_x, desc[:wrap], white)
            desc = desc[wrap:].lstrip()
            y += 1

        # Fields / options
        y += 2
        for fld in step.fields:
            label = fld.get("label", "")
            value = fld.get("value", "")
            self._safe_addstr(y, content_x, f"  {label}: ", cyan)
            self._safe_addstr(y, content_x + len(label) + 4, value, white)
            y += 1

        for opt in step.options:
            marker = "●" if opt.get("selected") else "○"
            self._safe_addstr(y, content_x, f"  {marker} {opt.get('label', '')}", white)
            y += 1

    def _draw_progress(self) -> None:
        if not self.screen:
            return
        max_y, max_x = self.screen.getmaxyx()
        green = curses.color_pair(1) if curses.has_colors() else 0
        inv = curses.color_pair(7) if curses.has_colors() else curses.A_REVERSE

        current, total, label = self._progress
        if total <= 0:
            return

        bar_y = max_y - 5
        bar_x = 2
        bar_w = max_x - 4

        pct = current / total if total else 0
        filled = int(bar_w * pct)

        self._safe_addstr(bar_y, bar_x, "█" * filled, inv)
        self._safe_addstr(bar_y, bar_x + filled, "░" * (bar_w - filled), green)

        info = f" {label} {current}/{total} ({pct:.0%}) "
        self._safe_addstr(bar_y - 1, bar_x, info, green)

    def _draw_stats(self) -> None:
        if not self.screen or not self._system_stats:
            return
        max_y, max_x = self.screen.getmaxyx()
        cyan = curses.color_pair(2) if curses.has_colors() else 0

        stats_y = max_y - 3
        cpu = self._system_stats.get("cpu_usage", 0)
        mem = self._system_stats.get("memory_usage", 0)
        disk = self._system_stats.get("disk_usage", 0)

        stat_line = f"CPU: {cpu:.0f}%  │  MEM: {mem:.0f}%  │  DISK: {disk:.0f}%"
        self._safe_addstr(stats_y, 2, stat_line, cyan)

    def _draw_messages(self) -> None:
        if not self.screen:
            return
        max_y, max_x = self.screen.getmaxyx()

        color_map = {
            "info": curses.color_pair(1) if curses.has_colors() else 0,
            "warn": curses.color_pair(3) if curses.has_colors() else 0,
            "error": curses.color_pair(4) if curses.has_colors() else 0,
            "success": curses.color_pair(2) if curses.has_colors() else 0,
        }

        msg_y = 18
        for msg in self._messages[-6:]:
            color = color_map.get(msg["level"], 0)
            prefix = {"info": "▸", "warn": "⚠", "error": "✗", "success": "✓"}.get(
                msg["level"], "·"
            )
            self._safe_addstr(msg_y, 2, f" {prefix} {msg['text']}", color)
            msg_y += 1

    def _draw_footer(self) -> None:
        if not self.screen:
            return
        max_y, max_x = self.screen.getmaxyx()
        green = curses.color_pair(1) if curses.has_colors() else 0
        cyan = curses.color_pair(2) if curses.has_colors() else 0

        border = "═" * (max_x - 2)
        self._safe_addstr(max_y - 2, 0, "╚" + border + "╝", green)

        nav = " [→/Enter] Next  [←/B] Back  [Q] Quit "
        self._safe_addstr(max_y - 1, 2, nav, cyan)
