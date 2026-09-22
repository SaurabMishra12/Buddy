"""Floating companion overlay window platform dispatcher for Buddy."""

from platforms import is_macos

if is_macos():
    from platforms.macos.window import (
        OverlayWindow, WebRopeWindow, SkyStrikeWindow, TransientLightning,
        WIN_SIZE, HALF_SIZE, CYAN_GLOW, BLUE_GLOW, WHITE_CORE
    )
else:
    from platforms.linux.window import (
        OverlayWindow, WebRopeWindow, SkyStrikeWindow, TransientLightning,
        WIN_SIZE, HALF_SIZE, CYAN_GLOW, BLUE_GLOW, WHITE_CORE
    )

__all__ = [
    "OverlayWindow",
    "WebRopeWindow",
    "SkyStrikeWindow",
    "TransientLightning",
    "WIN_SIZE",
    "HALF_SIZE",
    "CYAN_GLOW",
    "BLUE_GLOW",
    "WHITE_CORE",
]
