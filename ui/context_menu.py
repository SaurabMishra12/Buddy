"""Context menu platform dispatcher for Buddy."""

from platforms import is_macos

if is_macos():
    from platforms.macos.ui import show_macos_context_menu as show_context_menu
else:
    from platforms.linux.ui import show_linux_context_menu as show_context_menu

__all__ = ["show_context_menu"]
