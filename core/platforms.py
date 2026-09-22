"""Platform and desktop window ledge detection for interactive companion perching and navigation."""

import time
import math
from typing import List, Tuple, Optional, Dict, Any


class DesktopLedge:
    """Represents a walkable, perchable, and seatable platform on the desktop."""

    def __init__(
        self,
        x: float,
        y: float,
        width: float,
        height: float = 4.0,
        ledge_type: str = "window",  # "window", "panel", "button", "ground"
        title: str = "",
        is_real: bool = True
    ):
        self.x = float(x)
        self.y = float(y)
        self.width = float(max(10.0, width))
        self.height = float(max(2.0, height))
        self.ledge_type = ledge_type
        self.title = title
        self.is_real = is_real

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.height

    def contains_x(self, x: float, margin: float = 8.0) -> bool:
        return (self.left - margin) <= x <= (self.right + margin)

    def distance_to(self, px: float, py: float) -> float:
        # Distance to line segment representing top of ledge
        clamped_x = max(self.left, min(self.right, px))
        return math.hypot(px - clamped_x, py - self.top)


class PlatformManager:
    """Discovers and caches desktop window frames, titlebars, buttons, and system panels."""

    def __init__(self):
        self.ledges: List[DesktopLedge] = []
        self.dynamic_ledges: List[DesktopLedge] = []
        self.last_scan_time = 0.0
        self.scan_interval = 4.0  # seconds between full desktop window queries
        self._atspi_available = True

    def is_real_surface(self, ledge: Optional[DesktopLedge]) -> bool:
        """Check if a ledge represents a verified visible physical surface (panel, real window, etc.)."""
        if not ledge:
            return False
        if not getattr(ledge, "is_real", True):
            return False
        if getattr(ledge, "title", "") in ("Workspace Window", "Window Controls"):
            return False
        return True

    def scan_desktop_windows(self, screen_bounds: Tuple[int, int, int, int]) -> None:
        """Scan desktop for open application windows, top panels, and buttons."""
        min_x, min_y, screen_w, screen_h = screen_bounds
        discovered: List[DesktopLedge] = []

        # 1. System top panel (GNOME Shell / KDE status bar) - always genuine physical surface
        top_bar_h = 32.0
        discovered.append(DesktopLedge(
            x=min_x,
            y=min_y + top_bar_h,
            width=screen_w,
            height=4.0,
            ledge_type="panel",
            title="System Panel",
            is_real=True
        ))

        # 2. AT-SPI real accessibility windows and buttons query if enabled
        atspi_discovered: List[DesktopLedge] = []
        if self._atspi_available:
            try:
                import gi
                gi.require_version('Atspi', '2.0')
                from gi.repository import Atspi
                Atspi.init()
                desktop = Atspi.get_desktop(0)
                if desktop:
                    n_apps = min(12, desktop.get_child_count())
                    for i in range(n_apps):
                        app = desktop.get_child_at_index(i)
                        if not app:
                            continue
                        app_name = app.get_name() or ""
                        # Skip desktop pet overlays, daemons, and helper processes
                        if any(pet in app_name.lower() for pet in ("buddy", "oneko", "mjolnir", "desktop-pet", "evolution", "ibus")):
                            continue

                        n_wins = min(6, app.get_child_count())
                        for j in range(n_wins):
                            child = app.get_child_at_index(j)
                            if not child:
                                continue
                            try:
                                comp = child.get_component_iface()
                                if comp:
                                    rect = comp.get_extents(Atspi.CoordType.SCREEN)
                                    # Filter out unpositioned (0,0), off-screen, or tiny pet/icon overlays
                                    if rect.width >= 280 and rect.height >= 180 and rect.y >= 20 and rect.y < screen_h - 100:
                                        # Window top titlebar ledge
                                        atspi_discovered.append(DesktopLedge(
                                            x=rect.x,
                                            y=rect.y + 2.0,
                                            width=rect.width,
                                            height=26.0,
                                            ledge_type="window",
                                            title=child.get_name() or app_name,
                                            is_real=True
                                        ))
                                        # Window buttons (top right corner)
                                        atspi_discovered.append(DesktopLedge(
                                            x=rect.x + rect.width - 85.0,
                                            y=rect.y + 4.0,
                                            width=80.0,
                                            height=20.0,
                                            ledge_type="button",
                                            title=f"{app_name} Buttons",
                                            is_real=True
                                        ))
                            except Exception:
                                pass
            except Exception:
                self._atspi_available = False

        if atspi_discovered:
            discovered.extend(atspi_discovered)
        else:
            # Fallback typical workspace window frames when no AT-SPI windows are detected (e.g. headless tests)
            # Marked as is_real=False so characters know it is a phantom ledge and will not sit in mid-air on it
            w1_x = min_x + max(60.0, screen_w * 0.12)
            w1_y = min_y + max(100.0, screen_h * 0.18)
            w1_w = min(1200.0, screen_w * 0.76)
            discovered.append(DesktopLedge(
                x=w1_x,
                y=w1_y,
                width=w1_w,
                height=30.0,
                ledge_type="window",
                title="Workspace Window",
                is_real=False
            ))
            discovered.append(DesktopLedge(
                x=w1_x + w1_w - 95.0,
                y=w1_y + 4.0,
                width=90.0,
                height=22.0,
                ledge_type="button",
                title="Window Controls",
                is_real=False
            ))

        self.ledges = discovered

    def update(self, screen_bounds: Tuple[int, int, int, int], cursor_x: float, cursor_y: float) -> None:
        """Periodic refresh of ledges and dynamic cursor platforms."""
        now = time.time()
        if now - self.last_scan_time >= self.scan_interval or not self.ledges:
            self.last_scan_time = now
            self.scan_desktop_windows(screen_bounds)

    def get_nearest_ledge(
        self,
        px: float,
        py: float,
        max_dist: float = 120.0,
        require_real: bool = False
    ) -> Optional[DesktopLedge]:
        """Find the closest platform or window ledge to coordinates."""
        best_ledge: Optional[DesktopLedge] = None
        best_dist = float("inf")

        for ledge in self.ledges + self.dynamic_ledges:
            if require_real and not self.is_real_surface(ledge):
                continue
            # Check if x is within ledge span with margin
            if ledge.contains_x(px, margin=24.0):
                d = abs(py - ledge.top)
                if d < best_dist and d <= max_dist:
                    best_dist = d
                    best_ledge = ledge

        return best_ledge

    def is_on_ledge(
        self,
        px: float,
        py: float,
        tolerance: float = 12.0,
        require_real: bool = False
    ) -> Optional[DesktopLedge]:
        """Determine if character feet or body is resting on a window ledge or button."""
        for ledge in self.ledges + self.dynamic_ledges:
            if require_real and not self.is_real_surface(ledge):
                continue
            if ledge.contains_x(px, margin=16.0):
                if abs(py - ledge.top) <= tolerance:
                    return ledge
        return None

    def register_user_click_ledge(self, x: float, y: float) -> None:
        """Register a user interaction point as a perchable window ledge."""
        self.dynamic_ledges = [l for l in self.dynamic_ledges if time.time() - getattr(l, "created_at", 0) < 30.0]
        ledge = DesktopLedge(
            x=x - 140.0,
            y=y,
            width=280.0,
            height=24.0,
            ledge_type="window",
            title="User Window Point",
            is_real=True
        )
        setattr(ledge, "created_at", time.time())
        self.dynamic_ledges.append(ledge)


platform_manager = PlatformManager()
