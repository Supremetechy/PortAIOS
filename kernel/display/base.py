"""
Display Backend Abstract Interface

All display backends (TUI, SDL2, WebView, DRM) implement this interface.
The kernel and onboarding engine talk only to DisplayBackend — never
directly to Eel, curses, SDL, or any specific renderer.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class EventType(Enum):
    NEXT = "next"
    PREV = "prev"
    SELECT = "select"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    QUIT = "quit"
    TEXT_INPUT = "text_input"
    VOICE_COMMAND = "voice_command"
    KEY_PRESS = "key_press"
    RESIZE = "resize"


@dataclass
class InputEvent:
    type: EventType
    value: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AvatarState:
    emotion: str = "neutral"
    activity: str = "idle"
    volume: float = 0.0
    color_palette: str = "matrix"


@dataclass
class OnboardingStepView:
    index: int
    total_steps: int
    title: str
    description: str
    step_type: str = "configure"
    fields: List[Dict[str, Any]] = field(default_factory=list)
    options: List[Dict[str, Any]] = field(default_factory=list)


class DisplayBackend(ABC):
    """Abstract base for all AIOS display backends."""

    @abstractmethod
    def init(self, width: int = 1280, height: int = 800) -> None:
        """Initialize the display surface."""

    @abstractmethod
    def destroy(self) -> None:
        """Tear down the display and free resources."""

    # --- rendering --------------------------------------------------------

    @abstractmethod
    def show_step(self, step: OnboardingStepView) -> None:
        """Render an onboarding step on screen."""

    @abstractmethod
    def show_message(self, text: str, level: str = "info") -> None:
        """Display a status / log message (info, warn, error)."""

    @abstractmethod
    def show_progress(self, current: int, total: int, label: str = "") -> None:
        """Render a progress indicator."""

    @abstractmethod
    def show_avatar(self, state: AvatarState) -> None:
        """Render or update the avatar visual."""

    @abstractmethod
    def show_system_stats(self, stats: Dict[str, Any]) -> None:
        """Show CPU / RAM / disk telemetry overlay."""

    # --- input ------------------------------------------------------------

    @abstractmethod
    def get_input(self, timeout_ms: int = 0) -> Optional[InputEvent]:
        """
        Poll for user input.
        timeout_ms=0 means non-blocking; negative means block forever.
        Returns None when no event is available within the timeout.
        """

    # --- lifecycle --------------------------------------------------------

    @abstractmethod
    def is_running(self) -> bool:
        """True while the display window / session is alive."""

    def update(self) -> None:
        """
        Called once per frame / tick by the main loop.
        Override if the backend needs per-frame bookkeeping (e.g. SDL
        event pump, curses refresh). Default is a no-op.
        """

    # --- optional helpers -------------------------------------------------

    def set_title(self, title: str) -> None:
        """Set the window / terminal title if supported."""

    def supports_avatar(self) -> bool:
        """Whether this backend can render the graphical avatar."""
        return False

    def supports_audio(self) -> bool:
        """Whether this backend can play audio directly."""
        return False

    @property
    def name(self) -> str:
        return self.__class__.__name__
