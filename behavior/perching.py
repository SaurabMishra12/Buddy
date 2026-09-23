"""
Buddy Desktop Window Perching Subsystem.

Provides:
- PerchMode: OFF, SAFE (default), FREE
- PerchTarget: On-screen window target
- PerchTargetDetector: Queries Quartz window list excluding Buddy and system UI
- PerchTargetScorer: Evaluates geometry, visibility, and size
- PerchManager: Cooldowns and perching target coordination
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import time
from typing import Any, Dict, List, Optional

try:
    import Quartz
except ImportError:
    Quartz = None


class PerchMode(str, Enum):
    OFF = "off"
    SAFE = "safe"  # Only normal user windows, non-system, comfortable top ledge
    FREE = "free"  # Any visible eligible window


@dataclass
class PerchTarget:
    window_id: int
    owner_name: str
    title: str
    x: float
    y: float
    width: float
    height: float
    score: float = 0.0

    @property
    def top_ledge_center(self) -> tuple[float, float]:
        """Center of the top window border in Buddy world coordinates."""
        return (self.x + self.width * 0.5, self.y)


class PerchTargetDetector:
    """Discovers available desktop window perches using macOS Quartz."""

    EXCLUDED_OWNERS = {
        "Buddy",
        "ControlCenter",
        "Dock",
        "Window Server",
        "Spotlight",
        "SystemUIServer",
        "NotificationCenter",
        "loginwindow",
        "TextInputMenuAgent",
    }

    def detect_windows(self) -> List[PerchTarget]:
        if Quartz is None:
            return []

        try:
            # kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements
            options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
            window_list = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
            if not window_list:
                return []

            targets: List[PerchTarget] = []
            for win in window_list:
                owner = str(win.get(Quartz.kCGWindowOwnerName, ""))
                layer = int(win.get(Quartz.kCGWindowLayer, 0))
                
                # Exclude internal / system / background / floating overlays
                if owner in self.EXCLUDED_OWNERS or layer != 0:
                    continue

                bounds_dict = win.get(Quartz.kCGWindowBounds)
                if not bounds_dict:
                    continue

                w = float(bounds_dict.get("Width", 0))
                h = float(bounds_dict.get("Height", 0))
                x = float(bounds_dict.get("X", 0))
                y = float(bounds_dict.get("Y", 0))

                # Must have reasonable minimum dimensions
                if w < 250.0 or h < 150.0:
                    continue

                title = str(win.get(Quartz.kCGWindowName, ""))
                win_id = int(win.get(Quartz.kCGWindowNumber, 0))

                targets.append(PerchTarget(
                    window_id=win_id,
                    owner_name=owner,
                    title=title,
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                ))

            return targets
        except Exception:
            return []


class PerchTargetScorer:
    """Evaluates and ranks potential window perches."""

    @staticmethod
    def score(target: PerchTarget, companion_x: float, companion_y: float) -> float:
        score = 100.0

        # Preference for wide, spacious windows (e.g. IDEs, browsers)
        if target.width > 800:
            score += 30.0
        elif target.width > 500:
            score += 15.0

        # Distance penalty: closer windows are preferred
        dist_x = abs(target.x + target.width * 0.5 - companion_x)
        dist_y = abs(target.y - companion_y)
        dist = (dist_x * dist_x + dist_y * dist_y) ** 0.5
        score -= min(50.0, dist * 0.04)

        target.score = max(0.0, score)
        return target.score


class PerchManager:
    """Coordinates window perching with safety cooldowns."""

    def __init__(self, mode: PerchMode = PerchMode.SAFE):
        self.mode = mode
        self.detector = PerchTargetDetector()
        self.scorer = PerchTargetScorer()
        self.current_perch: Optional[PerchTarget] = None
        self.last_perch_time: float = 0.0
        self.perch_cooldown: float = 20.0  # prevent rapid hopping between windows

    def find_best_perch(
        self,
        companion_x: float,
        companion_y: float,
        now: Optional[float] = None,
    ) -> Optional[PerchTarget]:
        if self.mode == PerchMode.OFF:
            return None

        t = now if now is not None else time.time()
        if (t - self.last_perch_time) < self.perch_cooldown:
            return self.current_perch

        windows = self.detector.detect_windows()
        if not windows:
            return None

        for win in windows:
            self.scorer.score(win, companion_x, companion_y)

        windows.sort(key=lambda w: w.score, reverse=True)
        best = windows[0] if windows else None

        if best and best.score > 40.0:
            self.current_perch = best
            self.last_perch_time = t
            return best

        return None

    def release_perch(self) -> None:
        self.current_perch = None
