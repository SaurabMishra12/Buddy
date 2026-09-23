"""Process lifecycle, single-instance management, and error recovery watchdog for Buddy."""

import os
import sys
import fcntl
import signal
import socket
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from core.config import CACHE_DIR

LOCK_FILE = CACHE_DIR / "buddy.lock"
PID_FILE = CACHE_DIR / "buddy.pid"
SOCKET_FILE = CACHE_DIR / "buddy.sock"


class AppLifecycleState:
    INITIALIZING = "INITIALIZING"
    STARTING = "INITIALIZING"
    RUNNING = "RUNNING"
    ACTIVE = "RUNNING"
    PAUSED = "PAUSED"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    TERMINATING = "SHUTTING_DOWN"
    TERMINATED = "TERMINATED"

    def __init__(self, initial_state: str = INITIALIZING):
        self.state = initial_state

    def set_state(self, new_state: str) -> None:
        self.state = new_state

    def can_transition_to(self, new_state: str) -> bool:
        return True


class SingleInstanceLock:
    """Robust single-instance file lock using fcntl.flock to guarantee exactly one Buddy instance."""

    def __init__(self, lock_path: Optional[Path] = None):
        self.lock_path = lock_path or LOCK_FILE
        self._lock_fd: Optional[int] = None
        self.is_owner: bool = False

    @property
    def is_locked(self) -> bool:
        return self.is_owner

    def acquire(self) -> bool:
        """Attempt to acquire exclusive non-blocking lock. Returns True if acquired, False if already running."""
        try:
            self.lock_path.parent.mkdir(parents=True, exist_ok=True)
            self._lock_fd = os.open(str(self.lock_path), os.O_CREAT | os.O_RDWR, 0o644)
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.is_owner = True

            # Write current PID into lock file
            os.ftruncate(self._lock_fd, 0)
            os.lseek(self._lock_fd, 0, os.SEEK_SET)
            os.write(self._lock_fd, f"{os.getpid()}\n".encode("utf-8"))
            return True
        except (BlockingIOError, OSError):
            self.is_owner = False
            if self._lock_fd is not None:
                try:
                    os.close(self._lock_fd)
                except OSError:
                    pass
                self._lock_fd = None
            return False

    def release(self) -> None:
        """Release lock and clean up lock file."""
        if self.is_owner and self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
                os.close(self._lock_fd)
            except OSError:
                pass
            self._lock_fd = None
            self.is_owner = False
            try:
                if self.lock_path.exists():
                    self.lock_path.unlink()
            except OSError:
                pass


class LifecycleWatchdog:
    """Monitors subsystems and provides graceful degradation instead of crashing."""

    def __init__(self, engine: Any):
        self.engine = engine
        self.state: str = AppLifecycleState.INITIALIZING
        self.degraded_subsystems: Dict[str, str] = {}
        self.error_log: list = []

    def log_error(self, subsystem: str, error: Exception, critical: bool = False) -> None:
        msg = f"[{time.strftime('%X')}] Subsystem '{subsystem}' error: {error}"
        self.error_log.append(msg)
        if len(self.error_log) > 100:
            self.error_log.pop(0)
        print(f"[Buddy Watchdog] {msg}", file=sys.stderr)

        if critical:
            self.degraded_subsystems[subsystem] = str(error)

    def is_subsystem_healthy(self, subsystem: str) -> bool:
        return subsystem not in self.degraded_subsystems

    def set_state(self, new_state: str) -> None:
        self.state = new_state
