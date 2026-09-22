"""Settings preferences dialog platform dispatcher for Buddy."""

from platforms import is_macos

if is_macos():
    from platforms.macos.ui import show_macos_settings_dialog as show_settings_dialog
    SettingsDialog = None
else:
    from platforms.linux.ui import SettingsDialog, show_settings_dialog

__all__ = ["SettingsDialog", "show_settings_dialog"]
