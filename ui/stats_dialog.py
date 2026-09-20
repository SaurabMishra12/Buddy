"""Lightweight productivity and Pomodoro statistics dialog for Buddy 2.0."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from pomodoro.statistics import PomodoroStats


class StatsDialog(Gtk.Dialog):
    """Visual dashboard displaying focus sessions, daily/weekly metrics, and streaks."""

    def __init__(self, engine, parent=None):
        super().__init__(
            title="Buddy — Productivity Statistics",
            transient_for=parent,
            flags=0
        )
        self.engine = engine
        self.stats = getattr(engine, "pomodoro", None).stats if hasattr(engine, "pomodoro") else PomodoroStats()
        self.set_default_size(440, 360)
        self.set_position(Gtk.WindowPosition.CENTER)

        header = Gtk.HeaderBar(title="Productivity Dashboard", show_close_button=True)
        header.set_subtitle("Focus sessions and daily companion milestones")
        self.set_titlebar(header)

        content = self.get_content_area()
        content.set_spacing(12)
        content.set_margin_top(14)
        content.set_margin_bottom(14)
        content.set_margin_left(16)
        content.set_margin_right(16)

        # Overview Grid
        grid = Gtk.Grid()
        grid.set_column_spacing(14)
        grid.set_row_spacing(14)
        grid.set_column_homogeneous(True)
        content.pack_start(grid, True, True, 0)

        # 1. Today's Focus Time
        today_mins = self.stats.sessions_today * 25.0
        hours = int(today_mins // 60)
        mins = int(today_mins % 60)
        time_str = f"{hours}h {mins}m" if hours > 0 else f"{mins}m"
        card_today = self._create_stat_card("⏱️ Today's Focus", time_str, "#3498db")
        grid.attach(card_today, 0, 0, 1, 1)

        # 2. Sessions Completed Today
        sessions_today = self.stats.sessions_today
        card_sessions = self._create_stat_card("🎯 Sessions Today", str(sessions_today), "#2ecc71")
        grid.attach(card_sessions, 1, 0, 1, 1)

        # 3. Current Streak
        streak = self.stats.streak_days
        card_streak = self._create_stat_card("🔥 Daily Streak", f"{streak} days", "#e67e22")
        grid.attach(card_streak, 0, 1, 1, 1)

        # 4. Total Lifetime Sessions
        total_focus = f"{round(self.stats.total_focus_minutes / 60.0, 1)} hrs"
        card_total = self._create_stat_card("🏆 Total Focus", total_focus, "#9b59b6")
        grid.attach(card_total, 1, 1, 1, 1)

        # Companion milestone message
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        skin_name = engine.character.skin_id.replace("_", " ").title()
        info_lbl = Gtk.Label()
        info_lbl.set_markup(f"<i>Your companion <b>{skin_name}</b> is cheering you on for every focused sprint!</i>")
        info_lbl.set_line_wrap(True)
        info_box.pack_start(info_lbl, True, True, 0)
        content.pack_start(info_box, False, False, 6)

        # Action Buttons
        self.add_button("Reset Stats", Gtk.ResponseType.REJECT)
        close_btn = self.add_button("Close", Gtk.ResponseType.CLOSE)
        close_btn.get_style_context().add_class("suggested-action")

        self.show_all()

    def _create_stat_card(self, title: str, value: str, accent_hex: str) -> Gtk.Frame:
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.set_margin_top(12)
        vbox.set_margin_bottom(12)
        vbox.set_margin_left(12)
        vbox.set_margin_right(12)
        frame.add(vbox)

        title_lbl = Gtk.Label(label=title)
        title_lbl.get_style_context().add_class("dim-label")
        title_lbl.set_xalign(0.5)
        vbox.pack_start(title_lbl, False, False, 0)

        val_lbl = Gtk.Label()
        val_lbl.set_markup(f"<b><span size='xx-large' color='{accent_hex}'>{value}</span></b>")
        val_lbl.set_xalign(0.5)
        vbox.pack_start(val_lbl, True, True, 0)

        return frame


def show_stats_dialog(engine, parent=None):
    """Open the Pomodoro Statistics Dashboard."""
    dialog = StatsDialog(engine, parent=parent)
    response = dialog.run()
    if response == Gtk.ResponseType.REJECT:
        # User requested to reset statistics
        if hasattr(engine, "pomodoro"):
            engine.pomodoro.stats.reset_all()
    dialog.destroy()
