"""Coordinate conversion layer between Buddy world space and macOS AppKit screen coordinates.

Buddy canonical coordinate system:
- Origin (0, 0) is at the TOP-LEFT of the primary display.
- X increases to the right.
- Y increases downward.
- Window coordinates (center_x - half_size, center_y - half_size) specify top-left.

macOS AppKit coordinate system:
- Origin (0, 0) is at the BOTTOM-LEFT of the primary display.
- X increases to the right.
- Y increases upward.
- Window coordinates specify bottom-left corner of the window.
- Multi-monitor: NSScreen frames are positioned relative to the primary display's bottom-left origin.
"""

from typing import Tuple, List, Optional
import AppKit


def get_primary_screen_frame() -> Tuple[float, float, float, float]:
    """Returns (origin_x, origin_y, width, height) of the primary display in AppKit space."""
    screens = AppKit.NSScreen.screens()
    if screens and len(screens) > 0:
        f = screens[0].frame()
        return float(f.origin.x), float(f.origin.y), float(f.size.width), float(f.size.height)
    return 0.0, 0.0, 1920.0, 1080.0


def get_primary_screen_height() -> float:
    """Returns primary screen height in points."""
    _, _, _, h = get_primary_screen_frame()
    return h


def get_virtual_desktop_bounds() -> Tuple[float, float, float, float]:
    """Calculates virtual desktop bounding box across all connected monitors in Buddy world coordinates.

    Returns:
        (min_x, min_y, total_width, total_height)
    """
    screens = AppKit.NSScreen.screens()
    if not screens:
        return 0.0, 0.0, 1920.0, 1080.0

    primary_h = screens[0].frame().size.height

    min_bx = float("inf")
    min_by = float("inf")
    max_bx = float("-inf")
    max_by = float("-inf")

    for s in screens:
        f = s.frame()
        sx = float(f.origin.x)
        sy = float(f.origin.y)
        sw = float(f.size.width)
        sh = float(f.size.height)

        # In AppKit: Top of screen is sy + sh, bottom is sy
        # In Buddy: Top of screen is primary_h - (sy + sh), bottom is primary_h - sy
        bx1 = sx
        by1 = primary_h - (sy + sh)
        bx2 = sx + sw
        by2 = primary_h - sy

        min_bx = min(min_bx, bx1)
        min_by = min(min_by, by1)
        max_bx = max(max_bx, bx2)
        max_by = max(max_by, by2)

    return min_bx, min_by, max_bx - min_bx, max_by - min_by


def buddy_to_appkit_point(bx: float, by: float, primary_h: Optional[float] = None) -> Tuple[float, float]:
    """Converts a point from Buddy world space (top-left origin, Y down) to AppKit space (bottom-left origin, Y up)."""
    if primary_h is None:
        primary_h = get_primary_screen_height()
    return float(bx), float(primary_h - by)


def appkit_to_buddy_point(ax: float, ay: float, primary_h: Optional[float] = None) -> Tuple[float, float]:
    """Converts a point from AppKit space (bottom-left origin, Y up) to Buddy world space (top-left origin, Y down)."""
    if primary_h is None:
        primary_h = get_primary_screen_height()
    return float(ax), float(primary_h - ay)


def buddy_window_to_appkit_origin(
    top_left_x: float,
    top_left_y: float,
    win_w: float,
    win_h: float,
    primary_h: Optional[float] = None
) -> Tuple[float, float]:
    """Converts Buddy window top-left coordinates to AppKit window bottom-left origin.

    In Buddy coordinates:
      top edge = top_left_y
      bottom edge = top_left_y + win_h
    In AppKit coordinates:
      bottom edge = primary_h - (top_left_y + win_h)
    """
    if primary_h is None:
        primary_h = get_primary_screen_height()
    ax = float(top_left_x)
    ay = float(primary_h - (top_left_y + win_h))
    return ax, ay


def appkit_origin_to_buddy_window(
    ax: float,
    ay: float,
    win_w: float,
    win_h: float,
    primary_h: Optional[float] = None
) -> Tuple[float, float]:
    """Converts AppKit window bottom-left origin to Buddy window top-left coordinates."""
    if primary_h is None:
        primary_h = get_primary_screen_height()
    bx = float(ax)
    by = float(primary_h - (ay + win_h))
    return bx, by
