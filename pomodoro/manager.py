"""Pomodoro state machine and timer controller for Buddy."""

import time
from typing import Callable, List, Optional, Dict, Any

from pomodoro.statistics import PomodoroStats
from pomodoro.notifications import NotificationManager


class PomodoroState:
    IDLE = "IDLE"
    WORK = "WORK"
    SHORT_BREAK = "SHORT_BREAK"
    LONG_BREAK = "LONG_BREAK"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"


class PomodoroManager:
    """Manages focus sessions, breaks, notifications, and productivity statistics."""

    def __init__(
        self,
        config: Optional[Any] = None,
        stats: Optional[PomodoroStats] = None,
        notifications: Optional[NotificationManager] = None,
    ):
        self.config = config
        self.stats = stats or PomodoroStats()
        self.notifications = notifications or NotificationManager()

        # Configurable durations (in seconds)
        self.work_duration: float = 25.0 * 60.0
        self.short_break_duration: float = 5.0 * 60.0
        self.long_break_duration: float = 15.0 * 60.0
        self.sessions_before_long_break: int = 4
        self.auto_start_breaks: bool = True
        self.auto_start_work: bool = False

        if self.config:
            self._load_from_config()

        # State tracking
        self.state: str = PomodoroState.IDLE
        self.previous_state: str = PomodoroState.IDLE
        self.total_duration: float = self.work_duration
        self.remaining_seconds: float = self.work_duration
        self.completed_cycles: int = 0
        self.last_tick_time: float = time.time()

        # Listeners: callback(event_name: str, state: str, remaining: float)
        self._listeners: List[Callable[[str, str, float], None]] = []

    def _load_from_config(self) -> None:
        """Load settings from application configuration."""
        if not self.config:
            return
        p_cfg = self.config.get("pomodoro", {})
        if isinstance(p_cfg, dict):
            self.work_duration = float(p_cfg.get("work_duration", 25)) * 60.0
            self.short_break_duration = float(p_cfg.get("short_break_duration", 5)) * 60.0
            self.long_break_duration = float(p_cfg.get("long_break_duration", 15)) * 60.0
            self.sessions_before_long_break = int(p_cfg.get("sessions_before_long_break", 4))
            self.auto_start_breaks = bool(p_cfg.get("auto_start_breaks", True))
            self.auto_start_work = bool(p_cfg.get("auto_start_work", False))
            self.notifications.enabled = bool(p_cfg.get("notifications_enabled", True))

    def add_listener(self, callback: Callable[[str, str, float], None]) -> None:
        """Register callback(event, state, remaining_seconds)."""
        self._listeners.append(callback)

    def _emit(self, event_name: str) -> None:
        for cb in self._listeners:
            try:
                cb(event_name, self.state, self.remaining_seconds)
            except Exception:
                pass

    @property
    def progress(self) -> float:
        """Completion progress from 0.0 to 1.0."""
        if self.total_duration <= 0:
            return 0.0
        elapsed = self.total_duration - self.remaining_seconds
        return max(0.0, min(1.0, elapsed / self.total_duration))

    @property
    def remaining_formatted(self) -> str:
        """Return 'MM:SS' display string."""
        total_sec = max(0, int(self.remaining_seconds))
        minutes = total_sec // 60
        seconds = total_sec % 60
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def status_label(self) -> str:
        """Human-readable status label."""
        labels = {
            PomodoroState.IDLE: "Idle",
            PomodoroState.WORK: f"Focusing ({self.remaining_formatted})",
            PomodoroState.SHORT_BREAK: f"Short Break ({self.remaining_formatted})",
            PomodoroState.LONG_BREAK: f"Long Break ({self.remaining_formatted})",
            PomodoroState.PAUSED: f"Paused ({self.remaining_formatted})",
            PomodoroState.COMPLETED: "Session Completed!",
        }
        return labels.get(self.state, "Pomodoro")

    def start_work(self) -> None:
        """Start a new focus session."""
        self.state = PomodoroState.WORK
        self.total_duration = self.work_duration
        self.remaining_seconds = self.work_duration
        self.last_tick_time = time.time()
        self.notifications.notify("Pomodoro Focus Started", "Time to focus! Your Buddy is right beside you.")
        self._emit("work_start")

    def start_break(self, is_long: bool = False) -> None:
        """Start a break session."""
        self.state = PomodoroState.LONG_BREAK if is_long else PomodoroState.SHORT_BREAK
        dur = self.long_break_duration if is_long else self.short_break_duration
        self.total_duration = dur
        self.remaining_seconds = dur
        self.last_tick_time = time.time()
        title = "Long Break Started" if is_long else "Short Break Started"
        self.notifications.notify(title, "Step away, stretch, drink some water, and relax!")
        self._emit("break_start")

    def pause(self) -> None:
        """Pause active timer."""
        if self.state in (PomodoroState.WORK, PomodoroState.SHORT_BREAK, PomodoroState.LONG_BREAK):
            self.previous_state = self.state
            self.state = PomodoroState.PAUSED
            self._emit("pause")

    def resume(self) -> None:
        """Resume paused timer."""
        if self.state == PomodoroState.PAUSED:
            self.state = self.previous_state or PomodoroState.WORK
            self.last_tick_time = time.time()
            self._emit("resume")

    def toggle_pause(self) -> None:
        """Toggle between active and paused states."""
        if self.state == PomodoroState.PAUSED:
            self.resume()
        elif self.state in (PomodoroState.WORK, PomodoroState.SHORT_BREAK, PomodoroState.LONG_BREAK):
            self.pause()
        elif self.state == PomodoroState.IDLE:
            self.start_work()

    def reset(self) -> None:
        """Reset timer back to idle state."""
        self.state = PomodoroState.IDLE
        self.total_duration = self.work_duration
        self.remaining_seconds = self.work_duration
        self._emit("reset")

    def skip(self) -> None:
        """Skip current session to next state."""
        if self.state == PomodoroState.WORK:
            self._on_work_completed()
        elif self.state in (PomodoroState.SHORT_BREAK, PomodoroState.LONG_BREAK):
            self.reset()
            if self.auto_start_work:
                self.start_work()

    def tick(self, dt: Optional[float] = None) -> None:
        """Update countdown timer. Call on each GLib tick."""
        if self.state not in (PomodoroState.WORK, PomodoroState.SHORT_BREAK, PomodoroState.LONG_BREAK):
            return

        now = time.time()
        step = dt if dt is not None else max(0.0, now - self.last_tick_time)
        self.last_tick_time = now

        self.remaining_seconds = max(0.0, self.remaining_seconds - step)

        if self.remaining_seconds <= 0.0:
            if self.state == PomodoroState.WORK:
                self._on_work_completed()
            elif self.state in (PomodoroState.SHORT_BREAK, PomodoroState.LONG_BREAK):
                self._on_break_completed()

    def _on_work_completed(self) -> None:
        """Handle completion of a focus work session."""
        self.completed_cycles += 1
        duration_minutes = self.work_duration / 60.0
        self.stats.record_completed_session(duration_minutes)

        is_long = (self.completed_cycles % self.sessions_before_long_break == 0)
        self.notifications.notify(
            "🎉 Focus Session Complete!",
            f"Great work! Completed session #{self.completed_cycles} today.",
            urgency="critical"
        )
        self.state = PomodoroState.COMPLETED
        self._emit("work_completed")

        if self.auto_start_breaks:
            self.start_break(is_long=is_long)
        else:
            self.state = PomodoroState.IDLE
            self.remaining_seconds = self.work_duration

    def _on_break_completed(self) -> None:
        """Handle completion of a break."""
        self.notifications.notify(
            "Break Over!",
            "Break ended. Ready for the next focus sprint?",
            urgency="normal"
        )
        self._emit("break_completed")
        if self.auto_start_work:
            self.start_work()
        else:
            self.reset()
