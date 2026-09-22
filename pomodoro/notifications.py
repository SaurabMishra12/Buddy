"""Desktop notification manager for Buddy companion events and Pomodoro alerts."""

import shutil
import subprocess
from typing import Optional


class NotificationManager:
    """Delivers native desktop notifications via notify-send or DBus with graceful degradation."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._notify_send_path: Optional[str] = shutil.which("notify-send")

    def notify(self, title: str, message: str, icon: str = "dialog-information", urgency: str = "normal") -> bool:
        """Send desktop notification. Returns True if successfully sent."""
        if not self.enabled:
            return False

        from platforms import is_macos
        if is_macos():
            try:
                # Sanitize single quotes to prevent AppleScript injection
                clean_title = title.replace('"', '\\"')
                clean_msg = message.replace('"', '\\"')
                script = f'display notification "{clean_msg}" with title "{clean_title}"'
                subprocess.run(["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.0)
                return True
            except Exception:
                return False

        # Prefer native GI Notify first (native DBus, zero process fork overhead)

        try:
            import gi
            gi.require_version("Notify", "0.7")
            from gi.repository import Notify
            if not Notify.is_initted():
                Notify.init("Buddy")
            n = Notify.Notification.new(title, message, icon)
            n.show()
            return True
        except Exception:
            pass

        # Fallback to notify-send command line utility
        if self._notify_send_path:
            try:
                subprocess.run(
                    [
                        self._notify_send_path,
                        "-a", "Buddy",
                        "-i", icon,
                        "-u", urgency,
                        title,
                        message
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=0.5
                )
                return True
            except Exception:
                pass

        return False
