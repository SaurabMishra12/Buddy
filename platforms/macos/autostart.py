"""macOS user-level autostart management via LaunchAgent plist."""

import os
import sys
import plistlib
from pathlib import Path
from platforms.base import PlatformAutostart

LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_LABEL = "com.saurabmishra.buddy"
PLIST_FILE = LAUNCH_AGENTS_DIR / f"{PLIST_LABEL}.plist"


class MacOSAutostart(PlatformAutostart):
    """Manages launch-at-login on macOS using user LaunchAgent plist."""

    def is_enabled(self) -> bool:
        return PLIST_FILE.exists()

    def enable(self) -> bool:
        try:
            LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)

            # Determine executable path
            buddy_path = shutil_which_buddy()

            plist_data = {
                "Label": PLIST_LABEL,
                "ProgramArguments": [buddy_path],
                "RunAtLoad": True,
                "KeepAlive": False,
                "ProcessType": "Interactive"
            }

            with open(PLIST_FILE, "wb") as f:
                plistlib.dump(plist_data, f)

            return True
        except Exception as e:
            print(f"[Buddy Autostart macOS] Warning: Could not create LaunchAgent: {e}")
            return False

    def disable(self) -> bool:
        try:
            if PLIST_FILE.exists():
                PLIST_FILE.unlink()
            return True
        except Exception as e:
            print(f"[Buddy Autostart macOS] Warning: Could not remove LaunchAgent: {e}")
            return False

    def is_autostart_enabled(self) -> bool:
        return self.is_enabled()

    def set_autostart(self, enabled: bool) -> bool:
        return self.enable() if enabled else self.disable()


MacOSAutostartManager = MacOSAutostart
LAUNCH_AGENT_PLIST = PLIST_FILE


def shutil_which_buddy() -> str:
    """Find installed buddy executable or fallback to current script."""
    import shutil
    found = shutil.which("buddy")
    if found:
        return found
    # Fallback to local script
    root = Path(__file__).resolve().parent.parent.parent
    local_buddy = root / "buddy"
    if local_buddy.exists():
        return str(local_buddy)
    return sys.executable
