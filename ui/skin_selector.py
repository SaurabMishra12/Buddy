"""Skin Gallery dialog platform dispatcher for Buddy."""

from platforms import is_macos

if is_macos():
    from platforms.macos.ui import show_macos_skin_selector as show_skin_selector
    SkinSelectorDialog = None
else:
    from platforms.linux.ui import SkinSelectorDialog, show_skin_selector

__all__ = ["SkinSelectorDialog", "show_skin_selector"]
