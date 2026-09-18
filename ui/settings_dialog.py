"""Settings dialog: full customization of Buddy behaviors, performance, audio, and display."""

import os
from pathlib import Path
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / "buddy.desktop"


class SettingsDialog(Gtk.Dialog):
    """Full settings and preferences manager."""

    def __init__(self, engine, parent=None):
        super().__init__(
            title="Buddy Settings",
            transient_for=parent,
            flags=0
        )
        self.engine = engine
        self.config = engine.config
        self.set_default_size(520, 480)
        self.set_position(Gtk.WindowPosition.CENTER)

        content = self.get_content_area()
        content.set_spacing(10)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_left(14)
        content.set_margin_right(14)

        notebook = Gtk.Notebook()
        content.pack_start(notebook, True, True, 0)

        # Tab 1: General
        tab_general = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        tab_general.set_margin_top(12)
        tab_general.set_margin_left(12)
        tab_general.set_margin_right(12)

        # Scale slider
        scale_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        scale_box.pack_start(Gtk.Label(label="Pet Scale:"), False, False, 0)
        self.scale_adj = Gtk.Adjustment(value=self.config.get("scale", 1.0), lower=0.5, upper=2.5, step_increment=0.1, page_increment=0.2)
        self.scale_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.scale_adj)
        self.scale_scale.set_digits(1)
        scale_box.pack_start(self.scale_scale, True, True, 0)
        tab_general.pack_start(scale_box, False, False, 0)

        # Speed slider
        speed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        speed_box.pack_start(Gtk.Label(label="Movement Speed:"), False, False, 0)
        self.speed_adj = Gtk.Adjustment(value=self.config.get("speed", 1.0), lower=0.5, upper=2.5, step_increment=0.1, page_increment=0.2)
        self.speed_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.speed_adj)
        self.speed_scale.set_digits(1)
        speed_box.pack_start(self.speed_scale, True, True, 0)
        tab_general.pack_start(speed_box, False, False, 0)

        # Activity level slider
        act_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        act_box.pack_start(Gtk.Label(label="Activity Level:"), False, False, 0)
        self.act_adj = Gtk.Adjustment(value=self.config.get("activity_level", 1.0), lower=0.1, upper=2.5, step_increment=0.1, page_increment=0.2)
        self.act_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.act_adj)
        self.act_scale.set_digits(1)
        act_box.pack_start(self.act_scale, True, True, 0)
        tab_general.pack_start(act_box, False, False, 0)

        # Cursor follow toggle
        self.follow_chk = Gtk.CheckButton(label="Follow mouse cursor automatically")
        self.follow_chk.set_active(self.config.get("cursor_follow", True))
        tab_general.pack_start(self.follow_chk, False, False, 0)

        notebook.append_page(tab_general, Gtk.Label(label="General"))

        # Tab 2: Performance
        tab_perf = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        tab_perf.set_margin_top(12)
        tab_perf.set_margin_left(12)
        tab_perf.set_margin_right(12)

        self.low_power_chk = Gtk.CheckButton(label="Enable Low Power Mode (30 FPS, reduced effects)")
        self.low_power_chk.set_active(self.config.get("low_power_mode", False))
        tab_perf.pack_start(self.low_power_chk, False, False, 0)

        self.shake_chk = Gtk.CheckButton(label="Enable Screen Shake on heavy impacts (Hulk Smash / Catches)")
        self.shake_chk.set_active(self.config.get("screen_shake_enabled", True))
        tab_perf.pack_start(self.shake_chk, False, False, 0)

        # Particle limit
        part_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        part_box.pack_start(Gtk.Label(label="Maximum Particles:"), False, False, 0)
        self.part_adj = Gtk.Adjustment(value=self.config.get("particle_limit", 300), lower=50, upper=600, step_increment=25, page_increment=50)
        self.part_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.part_adj)
        self.part_scale.set_digits(0)
        part_box.pack_start(self.part_scale, True, True, 0)
        tab_perf.pack_start(part_box, False, False, 0)

        notebook.append_page(tab_perf, Gtk.Label(label="Performance"))

        # Tab 3: Display
        tab_disp = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        tab_disp.set_margin_top(12)
        tab_disp.set_margin_left(12)
        tab_disp.set_margin_right(12)

        self.click_chk = Gtk.CheckButton(label="100% Click-Through Overlay (Clicks pass through to desktop)")
        self.click_chk.set_active(self.config.get("click_through", False))
        tab_disp.pack_start(self.click_chk, False, False, 0)

        # Monitor Area
        mon_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        mon_box.pack_start(Gtk.Label(label="Movement Area:"), False, False, 0)
        self.mon_combo = Gtk.ComboBoxText()
        self.mon_combo.append("current_monitor", "Current Primary Monitor")
        self.mon_combo.append("all_monitors", "All Connected Monitors")
        self.mon_combo.set_active_id(self.config.get("movement_area", "current_monitor"))
        mon_box.pack_start(self.mon_combo, False, False, 0)
        tab_disp.pack_start(mon_box, False, False, 0)

        notebook.append_page(tab_disp, Gtk.Label(label="Display"))

        # Tab 4: Audio
        tab_audio = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        tab_audio.set_margin_top(12)
        tab_audio.set_margin_left(12)
        tab_audio.set_margin_right(12)

        self.audio_chk = Gtk.CheckButton(label="Enable Sound Effects")
        self.audio_chk.set_active(self.config.get("sound_enabled", True))
        tab_audio.pack_start(self.audio_chk, False, False, 0)

        vol_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        vol_box.pack_start(Gtk.Label(label="Sound Volume:"), False, False, 0)
        self.vol_adj = Gtk.Adjustment(value=self.config.get("sound_volume", 0.7) * 100, lower=0, upper=100, step_increment=5, page_increment=10)
        self.vol_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.vol_adj)
        self.vol_scale.set_digits(0)
        vol_box.pack_start(self.vol_scale, True, True, 0)
        tab_audio.pack_start(vol_box, False, False, 0)

        notebook.append_page(tab_audio, Gtk.Label(label="Audio"))

        # Tab 5: Startup
        tab_sys = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        tab_sys.set_margin_top(12)
        tab_sys.set_margin_left(12)
        tab_sys.set_margin_right(12)

        self.autostart_chk = Gtk.CheckButton(label="Start Buddy automatically on login (Autostart)")
        self.autostart_chk.set_active(AUTOSTART_FILE.exists())
        tab_sys.pack_start(self.autostart_chk, False, False, 0)

        notebook.append_page(tab_sys, Gtk.Label(label="Startup"))

        # Action Buttons
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        apply_btn = self.add_button("Save & Apply", Gtk.ResponseType.APPLY)
        apply_btn.get_style_context().add_class("suggested-action")

        self.show_all()

    def apply_settings(self):
        # Update config object
        self.config.set("scale", self.scale_adj.get_value(), auto_save=False)
        self.config.set("speed", self.speed_adj.get_value(), auto_save=False)
        self.config.set("activity_level", self.act_adj.get_value(), auto_save=False)
        self.config.set("cursor_follow", self.follow_chk.get_active(), auto_save=False)
        self.config.set("low_power_mode", self.low_power_chk.get_active(), auto_save=False)
        self.config.set("screen_shake_enabled", self.shake_chk.get_active(), auto_save=False)
        self.config.set("particle_limit", int(self.part_adj.get_value()), auto_save=False)
        self.config.set("click_through", self.click_chk.get_active(), auto_save=False)
        self.config.set("movement_area", self.mon_combo.get_active_id() or "current_monitor", auto_save=False)
        self.config.set("sound_enabled", self.audio_chk.get_active(), auto_save=False)
        self.config.set("sound_volume", self.vol_adj.get_value() / 100.0, auto_save=False)
        self.config.save()

        # Apply to live engine
        self.engine.character.scale = self.config.get("scale", 1.0)
        self.engine.click_through = self.config.get("click_through", False)
        self.engine.window.set_click_through(self.engine.click_through)
        self.engine.audio.enabled = self.config.get("sound_enabled", True)
        self.engine.audio.volume = self.config.get("sound_volume", 0.7)
        self.engine.particles.max_particles = self.config.get("particle_limit", 300)

        # Autostart configuration
        if self.autostart_chk.get_active():
            self._install_autostart()
        else:
            self._remove_autostart()

    def _install_autostart(self):
        try:
            AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
            content = """[Desktop Entry]
Type=Application
Name=Buddy Desktop Pet
Comment=Animated superhero and fantasy desktop companion for Linux
Exec=buddy
Icon=buddy
Terminal=false
Categories=Utility;Amusement;
X-GNOME-Autostart-enabled=true
"""
            with open(AUTOSTART_FILE, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"[Buddy Settings] Warning: Failed to write autostart entry: {e}")

    def _remove_autostart(self):
        if AUTOSTART_FILE.exists():
            try:
                AUTOSTART_FILE.unlink()
            except Exception:
                pass


def show_settings_dialog(engine):
    dialog = SettingsDialog(engine)
    response = dialog.run()
    if response == Gtk.ResponseType.APPLY:
        dialog.apply_settings()
    dialog.destroy()
