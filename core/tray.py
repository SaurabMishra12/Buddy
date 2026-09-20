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


class BuddyTray:
    """Linux system tray / app indicator for quick Buddy controls."""

    def __init__(self, engine: Any):
        self.engine = engine
        self.indicator = None
        if appindicator is None:
            print("[Buddy Tray] Note: AppIndicator not available on this system, tray icon omitted.")
            return

        # Find or use fallback icon
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

        # Title / Status
        title_item = Gtk.MenuItem(label=f"Buddy — Skin: {self.engine.character.skin_id.capitalize()}")
        title_item.set_sensitive(False)
        menu.append(title_item)
        menu.append(Gtk.SeparatorMenuItem())

        # Change Skin item
        skin_item = Gtk.MenuItem(label="Change Character Skin...")
        skin_item.connect("activate", self._on_change_skin)
        menu.append(skin_item)

        # Pause / Resume item
        pause_label = "Resume Buddy" if self.engine.paused else "Pause Buddy"
        pause_item = Gtk.MenuItem(label=pause_label)
        pause_item.connect("activate", self._on_toggle_pause)
        menu.append(pause_item)

        # Click-through toggle item
        click_item = Gtk.CheckMenuItem(label="100% Click-Through Overlay")
        click_item.set_active(self.engine.click_through)
        click_item.connect("toggled", self._on_toggle_click_through)
        menu.append(click_item)

        # Settings item
        settings_item = Gtk.MenuItem(label="Settings...")
        settings_item.connect("activate", self._on_open_settings)
        menu.append(settings_item)

        menu.append(Gtk.SeparatorMenuItem())

        # About item
        about_item = Gtk.MenuItem(label="About Buddy")
        about_item.connect("activate", self._on_about)
        menu.append(about_item)

        # Quit item
        quit_item = Gtk.MenuItem(label="Quit Buddy")
        quit_item.connect("activate", lambda _: Gtk.main_quit())
        menu.append(quit_item)

        menu.show_all()
        self.indicator.set_menu(menu)

    def _on_change_skin(self, widget: Gtk.Widget) -> None:
        from ui.skin_selector import show_skin_selector
        show_skin_selector(self.engine)

    def _on_toggle_pause(self, widget: Gtk.Widget) -> None:
        self.engine.toggle_pause()
        self.update_menu()

    def _on_toggle_click_through(self, widget: Gtk.CheckMenuItem) -> None:
        self.engine.toggle_click_through()

    def _on_open_settings(self, widget: Gtk.Widget) -> None:
        from ui.settings_dialog import show_settings_dialog
        show_settings_dialog(self.engine)

    def _on_about(self, widget: Gtk.Widget) -> None:
        about = Gtk.AboutDialog()
        about.set_program_name("Buddy")
        about.set_version("1.0.0")
        about.set_comments("A modern, extensible Linux desktop pet application designed for Fedora Linux.")
        about.set_website("https://github.com/SaurabMishra12/Buddy")
        about.set_website_label("Buddy Desktop Companion")
        about.run()
        about.destroy()
