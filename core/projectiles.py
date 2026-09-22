"""Desktop projectile overlay platform dispatcher for Buddy."""

from platforms import is_macos

if is_macos():
    from platforms.macos.projectiles import DesktopProjectileWindow
else:
    from platforms.linux.projectiles import DesktopProjectileWindow

__all__ = ["DesktopProjectileWindow"]
