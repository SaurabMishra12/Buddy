"""Abstract base contracts and interfaces for Buddy platform backends."""

from abc import ABC, abstractmethod
from typing import Tuple, Optional, Callable, Dict, Any, List


class PlatformWindow(ABC):
    """Contract for floating desktop pet companion overlay window."""

    @abstractmethod
    def move_to(self, center_x: float, center_y: float) -> None:
        """Positions window so its visual center aligns with (center_x, center_y)."""
        pass

    @abstractmethod
    def set_click_through(self, enabled: bool) -> None:
        """Toggle click-through mode."""
        pass

    @abstractmethod
    def set_hitbox_mask(self, radius: float = 54.0) -> None:
        """Sets active clickable input region around center."""
        pass

    @abstractmethod
    def query_pointer(self) -> Tuple[float, float]:
        """Returns global pointer/cursor coordinates in canonical Buddy world space (0,0 top-left)."""
        pass

    @abstractmethod
    def queue_draw(self) -> None:
        """Requests asynchronous redraw of the window surface."""
        pass

    @abstractmethod
    def show(self) -> None:
        """Displays the window on screen."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Destroys and closes the window."""
        pass


class PlatformTray(ABC):
    """Contract for system tray / menu bar item."""

    @abstractmethod
    def update_menu(self) -> None:
        """Rebuilds or refreshes status item menu items."""
        pass


class PlatformAudio(ABC):
    """Contract for audio sound playback."""

    @abstractmethod
    def play(self, sound_name: str, custom_path: Optional[str] = None) -> None:
        """Plays sound effect non-blockingly."""
        pass


class PlatformAutostart(ABC):
    """Contract for login startup persistence."""

    @abstractmethod
    def is_enabled(self) -> bool:
        """Checks if Buddy is set to start at login."""
        pass

    @abstractmethod
    def enable(self) -> bool:
        """Configures Buddy to launch at login."""
        pass

    @abstractmethod
    def disable(self) -> bool:
        """Removes Buddy from login items."""
        pass
