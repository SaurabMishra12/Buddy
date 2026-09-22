"""System tray indicator for Linux desktop environments (GNOME, KDE, XFCE)."""

import sys
import os
from typing import Any, Optional

import gi
try:
    gi.require_version("AppIndicator3", "0.1")
    from gi.repository import AppIndicator3 as appindicator
except (ValueError, ImportError):
    try:
        gi.require_version("AyatanaAppIndicator3", "0.1")
        from gi.repository import AyatanaAppIndicator3 as appindicator
    except (ValueError, ImportError):
        appindicator = None

from gi.repository import Gtk, GLib
from skins.manager import skin_manager
from pomodoro.manager import PomodoroState


class BuddyTray:
    """Rich Linux system tray indicator for Buddy 2.0."""

    def __init__(self, engine: Any):
        self.engine = engine
        self.indicator = None
        if appindicator is None:
            print("[Buddy Tray] Note: AppIndicator not available on this system, tray icon omitted.")
            return

        icon_path = "applications-games"
        self.indicator = appindicator.Indicator.new(
            "buddy-desktop-pet",
            icon_path,
            appindicator.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.update_menu()

    def update_menu(self) -> None:
        if not self.indicator:
            return

        menu = Gtk.Menu()

        # 1. Title / Header
        title_item = Gtk.MenuItem(label=f"Buddy 2.0 — {self.engine.character.skin_id.replace('_', ' ').title()}")
        title_item.set_sensitive(False)
        menu.append(title_item)
        menu.append(Gtk.SeparatorMenuItem())

        # 2. Current Skin Submenu
        skin_sub = Gtk.MenuItem(label="Current Skin")
        skin_menu = Gtk.Menu()
        skin_sub.set_submenu(skin_menu)
        for s in skin_manager.get_available_skins():
            sid = s["id"]
            prefix = "✓ " if sid == self.engine.character.skin_id else "   "
            item = Gtk.MenuItem(label=f"{prefix}{s.get('name', sid)}")
            item.connect("activate", lambda _, id=sid: (self.engine.switch_skin(id), self.update_menu()))
            skin_menu.append(item)
        menu.append(skin_sub)

        # 3. Pomodoro Submenu
        pomo = getattr(self.engine, "pomodoro", None)
        if pomo:
            pomo_sub = Gtk.MenuItem(label=f"Pomodoro ({pomo.status_label})")
            pomo_menu = Gtk.Menu()
            pomo_sub.set_submenu(pomo_menu)

            if pomo.state in (PomodoroState.WORK, PomodoroState.SHORT_BREAK, PomodoroState.LONG_BREAK):
                t_item = Gtk.MenuItem(label="Pause")
                t_item.connect("activate", lambda _: (pomo.pause(), self.update_menu()))
                pomo_menu.append(t_item)
            elif pomo.state == PomodoroState.PAUSED:
                t_item = Gtk.MenuItem(label="Resume")
                t_item.connect("activate", lambda _: (pomo.resume(), self.update_menu()))
                pomo_menu.append(t_item)
            else:
                t_item = Gtk.MenuItem(label="Start Focus")
                t_item.connect("activate", lambda _: (pomo.start_work(), self.update_menu()))
                pomo_menu.append(t_item)

            sk_item = Gtk.MenuItem(label="Skip to Next")
            sk_item.connect("activate", lambda _: (pomo.skip(), self.update_menu()))
            pomo_menu.append(sk_item)

            r_item = Gtk.MenuItem(label="Reset")
            r_item.connect("activate", lambda _: (pomo.reset(), self.update_menu()))
            pomo_menu.append(r_item)

            menu.append(pomo_sub)

        # 4. Buddy Mode Submenu
        mode_sub = Gtk.MenuItem(label="Buddy Mode")
        mode_menu = Gtk.Menu()
        mode_sub.set_submenu(mode_menu)

        ct_item = Gtk.CheckMenuItem(label="Click-through")
        ct_item.set_active(self.engine.click_through)
        ct_item.connect("toggled", lambda w: self.engine.toggle_click_through())
        mode_menu.append(ct_item)

        focus_item = Gtk.CheckMenuItem(label="Focus Mode")
        focus_item.set_active(self.engine.config.get("focus_mode", False))
        focus_item.connect("toggled", lambda w: self.engine.config.set("focus_mode", w.get_active()))
        mode_menu.append(focus_item)

        quiet_item = Gtk.CheckMenuItem(label="Quiet Mode")
        quiet_item.set_active(not self.engine.audio.enabled)
        quiet_item.connect("toggled", lambda w: self._toggle_sound(not w.get_active()))
        mode_menu.append(quiet_item)

        menu.append(mode_sub)

        # 5. Size Submenu
        size_sub = Gtk.MenuItem(label="Size")
        size_menu = Gtk.Menu()
        size_sub.set_submenu(size_menu)
        for label, sc in [("Small", 0.75), ("Medium", 1.0), ("Large", 1.35)]:
            cur_sc = getattr(self.engine.character, "scale", 1.0)
            chk = "✓ " if abs(cur_sc - sc) < 0.1 else "   "
            s_item = Gtk.MenuItem(label=f"{chk}{label}")
            s_item.connect("activate", lambda _, val=sc: self.engine.set_scale(val))
            size_menu.append(s_item)
        menu.append(size_sub)

        menu.append(Gtk.SeparatorMenuItem())

        # 6. Settings, Skin Gallery, Statistics, Help, Quit
        settings_item = Gtk.MenuItem(label="Settings...")
        settings_item.connect("activate", self._on_open_settings)
        menu.append(settings_item)

        gallery_item = Gtk.MenuItem(label="Skin Gallery...")
        gallery_item.connect("activate", self._on_change_skin)
        menu.append(gallery_item)

        stats_item = Gtk.MenuItem(label="Statistics...")
        stats_item.connect("activate", self._on_open_stats)
        menu.append(stats_item)

        help_item = Gtk.MenuItem(label="Help & Shortcuts...")
        help_item.connect("activate", self._on_help)
        menu.append(help_item)

        menu.append(Gtk.SeparatorMenuItem())

        quit_item = Gtk.MenuItem(label="Quit Buddy")
        quit_item.connect("activate", lambda _: Gtk.main_quit())
        menu.append(quit_item)

        menu.show_all()
        self.indicator.set_menu(menu)

    def _on_change_skin(self, widget: Gtk.Widget) -> None:
        from ui.skin_selector import show_skin_selector
        show_skin_selector(self.engine)
        self.update_menu()

    def _on_open_settings(self, widget: Gtk.Widget) -> None:
        from ui.settings_dialog import show_settings_dialog
        show_settings_dialog(self.engine)
        self.update_menu()

    def _on_open_stats(self, widget: Gtk.Widget) -> None:
        from ui.stats_dialog import show_stats_dialog
        show_stats_dialog(self.engine)

    def _toggle_sound(self, enabled: bool) -> None:
        self.engine.audio.enabled = enabled
        self.engine.config.set("sound_enabled", enabled)

    def _on_help(self, widget: Gtk.Widget) -> None:
        dialog = Gtk.MessageDialog(
            transient_for=None,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Buddy 2.0 — Linux Desktop Companion"
        )
        dialog.format_secondary_markup(
            "<b>Controls:</b>\n"
            "• <b>Left Click & Drag:</b> Move / play with your companion\n"
            "• <b>Double Click:</b> Execute signature ability / acrobatic stunt\n"
            "• <b>Middle Click / Scroll:</b> Cycle characters\n"
            "• <b>Right Click:</b> Context menu with Pomodoro and modes\n\n"
            "<b>CLI Commands:</b>\n"
            "<code>buddy --skin [name]</code>\n"
            "<code>buddy --pomodoro [start|pause|resume|reset|status]</code>\n"
            "<code>buddy --stats</code>\n"
            "<code>buddy --skin-gallery</code>"
        )
        dialog.run()
        dialog.destroy()
