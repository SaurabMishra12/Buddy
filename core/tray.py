"""System tray / Menu Bar status item platform dispatcher for Buddy."""

from platforms import is_macos

if is_macos():
    from platforms.macos.menu_bar import MacOSMenuBar as BuddyTray
else:
    from platforms.linux.tray import BuddyTray

__all__ = ["BuddyTray"]
