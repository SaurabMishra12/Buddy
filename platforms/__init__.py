"""Platform abstraction package for Buddy.

Provides platform detection and dispatch to native backends:
- Linux: GTK3 / GDK / AppIndicator / X11 / Wayland
- macOS: AppKit / Quartz / PyObjC / NSSound
"""

import sys
from typing import Literal

PlatformType = Literal["linux", "macos", "unknown"]


def get_platform_name() -> PlatformType:
    """Return canonical platform identifier."""
    if sys.platform == "darwin":
        return "macos"
    elif sys.platform.startswith("linux"):
        return "linux"
    return "unknown"


def is_macos() -> bool:
    """Return True if running natively on macOS (Darwin)."""
    return sys.platform == "darwin"


def is_linux() -> bool:
    """Return True if running on Linux."""
    return sys.platform.startswith("linux")
