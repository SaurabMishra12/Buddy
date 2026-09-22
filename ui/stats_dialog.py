"""Productivity statistics dialog platform dispatcher for Buddy."""

from platforms import is_macos

if is_macos():
    from platforms.macos.ui import show_macos_stats_dialog as show_stats_dialog
    StatsDialog = None
else:
    from platforms.linux.ui import StatsDialog, show_stats_dialog

__all__ = ["StatsDialog", "show_stats_dialog"]
