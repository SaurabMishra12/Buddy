"""Desktop window and panel ledge detection on macOS using Quartz CoreGraphics APIs."""

import math
from typing import List, Tuple
from core.platforms import DesktopLedge
import Quartz


def scan_macos_desktop_windows(screen_bounds: Tuple[int, int, int, int]) -> List[DesktopLedge]:
    """Scans macOS desktop for application windows, top menu bar, and window traffic-light buttons."""
    min_x, min_y, screen_w, screen_h = screen_bounds
    discovered: List[DesktopLedge] = []

    # 1. macOS Top Menu Bar (24pt height)
    menu_bar_h = 24.0
    discovered.append(DesktopLedge(
        x=float(min_x),
        y=float(min_y + menu_bar_h),
        width=float(screen_w),
        height=4.0,
        ledge_type="panel",
        title="macOS Menu Bar"
    ))

    # 2. Open application windows queried via Quartz
    try:
        wins = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID
        )
        if wins:
            for w in wins:
                # Filter for standard document/app windows (layer 0)
                layer = w.get("kCGWindowLayer", 0)
                if layer != 0:
                    continue

                owner = str(w.get("kCGWindowOwnerName", ""))
                if "buddy" in owner.lower() or "dock" in owner.lower() or "window server" in owner.lower():
                    continue

                bounds = w.get("kCGWindowBounds", {})
                wx = float(bounds.get("X", 0))
                wy = float(bounds.get("Y", 0))
                ww = float(bounds.get("Width", 0))
                wh = float(bounds.get("Height", 0))

                if ww > 150 and wh > 100:
                    # Top titlebar ledge
                    discovered.append(DesktopLedge(
                        x=wx,
                        y=wy + 2.0,
                        width=ww,
                        height=26.0,
                        ledge_type="window",
                        title=f"{owner} Titlebar"
                    ))

                    # macOS Window traffic light buttons (top-left corner)
                    discovered.append(DesktopLedge(
                        x=wx + 10.0,
                        y=wy + 4.0,
                        width=56.0,
                        height=16.0,
                        ledge_type="button",
                        title=f"{owner} Controls"
                    ))
    except Exception as e:
        pass

    if not discovered:
        # Fallback ledge in center of workspace
        w1_x = min_x + screen_w * 0.15
        w1_y = min_y + screen_h * 0.20
        w1_w = screen_w * 0.70
        discovered.append(DesktopLedge(
            x=w1_x,
            y=w1_y,
            width=w1_w,
            height=28.0,
            ledge_type="window",
            title="Desktop Window"
        ))

    return discovered
