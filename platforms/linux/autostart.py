"""Linux autostart management using ~/.config/autostart/buddy.desktop."""

import os
from pathlib import Path
from platforms.base import PlatformAutostart

AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / "buddy.desktop"


class LinuxAutostart(PlatformAutostart):
    """Manages Linux XDG autostart desktop entry."""

    def is_enabled(self) -> bool:
        return AUTOSTART_FILE.exists()

    def enable(self) -> bool:
        try:
            AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
            desktop_content = (
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=Buddy\n"
                "GenericName=Desktop Companion\n"
                "Comment=Buddy Animated Desktop Pet\n"
                "Exec=buddy\n"
                "Icon=buddy\n"
                "Terminal=false\n"
                "Categories=Utility;Amusement;\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
            with open(AUTOSTART_FILE, "w", encoding="utf-8") as f:
                f.write(desktop_content)
            return True
        except Exception as e:
            print(f"[Buddy Linux] Warning: Could not enable autostart: {e}")
            return False

    def disable(self) -> bool:
        try:
            if AUTOSTART_FILE.exists():
                AUTOSTART_FILE.unlink()
            return True
        except Exception as e:
            print(f"[Buddy Linux] Warning: Could not disable autostart: {e}")
            return False
