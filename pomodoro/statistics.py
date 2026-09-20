"""Pomodoro statistics and productivity analytics tracker."""

import json
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

STATS_FILE = Path.home() / ".config" / "buddy" / "pomodoro_stats.json"


class PomodoroStats:
    """Records daily focus sessions, weekly aggregations, and streak milestones."""

    def __init__(self, stats_file: Optional[Path] = None):
        self.stats_file = Path(stats_file) if stats_file else STATS_FILE
        self.sessions_today: int = 0
        self.sessions_this_week: int = 0
        self.total_focus_minutes: float = 0.0
        self.streak_days: int = 0
        self.last_active_date: str = ""
        self.daily_history: Dict[str, int] = {}  # date string -> session count

        self._ensure_dir()
        self.load()

    def _ensure_dir(self) -> None:
        try:
            self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    def load(self) -> None:
        """Load stats and compute current day/week rollover."""
        today_str = date.today().isoformat()
        if self.stats_file.exists():
            try:
                raw = self.stats_file.read_text(encoding="utf-8")
                data = json.loads(raw)
                if isinstance(data, dict):
                    self.total_focus_minutes = float(data.get("total_focus_minutes", 0.0))
                    self.daily_history = data.get("daily_history", {})
                    self.streak_days = int(data.get("streak_days", 0))
                    self.last_active_date = data.get("last_active_date", "")
            except Exception as e:
                print(f"[Pomodoro Stats] Warning loading stats: {e}")

        # Recalculate today and this week
        self.sessions_today = self.daily_history.get(today_str, 0)
        self.sessions_this_week = self._calculate_week_sessions()
        self._update_streak(today_str)

    def save(self) -> bool:
        """Persist stats to local file."""
        self._ensure_dir()
        try:
            today_str = date.today().isoformat()
            self.daily_history[today_str] = self.sessions_today
            data = {
                "total_focus_minutes": round(self.total_focus_minutes, 1),
                "streak_days": self.streak_days,
                "last_active_date": self.last_active_date,
                "daily_history": self.daily_history,
                "updated_at": time.time(),
            }
            tmp = self.stats_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp.replace(self.stats_file)
            return True
        except Exception as e:
            print(f"[Pomodoro Stats] Error saving stats: {e}")
            return False

    def record_completed_session(self, duration_minutes: float) -> None:
        """Add completed focus session."""
        today_str = date.today().isoformat()
        self.sessions_today += 1
        self.daily_history[today_str] = self.sessions_today
        self.total_focus_minutes += duration_minutes
        self.sessions_this_week = self._calculate_week_sessions()
        self._update_streak(today_str)
        self.last_active_date = today_str
        self.save()

    def _calculate_week_sessions(self) -> int:
        """Sum sessions over last 7 days."""
        today = date.today()
        count = 0
        for i in range(7):
            d_str = (today - timedelta(days=i)).isoformat()
            count += self.daily_history.get(d_str, 0)
        return count

    def _update_streak(self, today_str: str) -> None:
        """Compute consecutive day streak."""
        if not self.daily_history:
            self.streak_days = 0
            return

        today = date.today()
        streak = 0
        # If user did at least 1 session today, start counting from today
        start_offset = 0 if self.daily_history.get(today_str, 0) > 0 else 1

        for i in range(start_offset, 365):
            d_str = (today - timedelta(days=i)).isoformat()
            if self.daily_history.get(d_str, 0) > 0:
                streak += 1
            else:
                break
        self.streak_days = streak

    def get_summary(self) -> Dict[str, Any]:
        """Return formatted summary dictionary."""
        hours_today = (self.sessions_today * 25.0) / 60.0
        hours_week = self.sessions_this_week * 25.0 / 60.0
        return {
            "sessions_today": self.sessions_today,
            "sessions_this_week": self.sessions_this_week,
            "total_focus_minutes": round(self.total_focus_minutes, 1),
            "total_focus_hours": round(self.total_focus_minutes / 60.0, 1),
            "streak_days": self.streak_days,
            "history_days_count": len(self.daily_history),
        }

    def reset_all(self) -> None:
        """Reset all tracked statistics back to zero."""
        self.sessions_today = 0
        self.sessions_this_week = 0
        self.total_focus_minutes = 0.0
        self.streak_days = 0
        self.daily_history = {}
        self.last_active_date = ""
        self.save()
