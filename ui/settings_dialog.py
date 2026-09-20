"""Settings dialog: full multi-section preferences manager for Buddy 2.0."""

import os
from pathlib import Path
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from skins.manager import skin_manager

AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / "buddy.desktop"


class SettingsDialog(Gtk.Dialog):
    """Multi-section preferences dialog covering General, Behavior, Appearance, Pomodoro, Performance, and Accessibility."""

    def __init__(self, engine, parent=None):
        super().__init__(
            title="Buddy Settings",
            transient_for=parent,
            flags=0
        )
        self.engine = engine
        self.config = engine.config
        self.set_default_size(620, 520)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Header Bar
        header = Gtk.HeaderBar(title="Buddy Preferences", show_close_button=True)
        header.set_subtitle("Customize behavior, productivity, and desktop graphics")
        self.set_titlebar(header)

        content = self.get_content_area()
        content.set_spacing(10)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_left(14)
        content.set_margin_right(14)

        # Tabbed Notebook
        self.notebook = Gtk.Notebook()
        content.pack_start(self.notebook, True, True, 0)

        # Build each Section Tab
        self._build_general_tab()
        self._build_behavior_tab()
        self._build_appearance_tab()
        self._build_pomodoro_tab()
        self._build_performance_tab()
        self._build_accessibility_tab()

        # Action Buttons
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        apply_btn = self.add_button("Save & Apply", Gtk.ResponseType.APPLY)
        apply_btn.get_style_context().add_class("suggested-action")

        self.show_all()

    def _create_tab_box(self) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_left(14)
        box.set_margin_right(14)
        return box

    # 1. GENERAL TAB
    def _build_general_tab(self) -> None:
        box = self._create_tab_box()

        # Default Skin Combo
        skin_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        skin_box.pack_start(Gtk.Label(label="Default Character:"), False, False, 0)
        self.skin_combo = Gtk.ComboBoxText()
        for meta in skin_manager.get_available_skins():
            self.skin_combo.append(meta["id"], meta.get("name", meta["id"]))
        self.skin_combo.set_active_id(self.config.get("skin", "thor"))
        skin_box.pack_start(self.skin_combo, True, True, 0)
        box.pack_start(skin_box, False, False, 0)

        # Scale slider
        scale_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        scale_box.pack_start(Gtk.Label(label="Companion Size:"), False, False, 0)
        self.scale_adj = Gtk.Adjustment(value=self.config.get("scale", 1.0), lower=0.5, upper=2.5, step_increment=0.1, page_increment=0.2)
        scale_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.scale_adj)
        scale_scale.set_digits(1)
        scale_box.pack_start(scale_scale, True, True, 0)
        box.pack_start(scale_box, False, False, 0)

        # Master Audio
        self.audio_chk = Gtk.CheckButton(label="Enable Sound Effects & Audio")
        self.audio_chk.set_active(self.config.get("sound_enabled", True))
        box.pack_start(self.audio_chk, False, False, 0)

        vol_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        vol_box.pack_start(Gtk.Label(label="Master Volume:"), False, False, 0)
        self.vol_adj = Gtk.Adjustment(value=self.config.get("sound_volume", 0.7) * 100, lower=0, upper=100, step_increment=5, page_increment=10)
        vol_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.vol_adj)
        vol_scale.set_digits(0)
        vol_box.pack_start(vol_scale, True, True, 0)
        box.pack_start(vol_box, False, False, 0)

        # Autostart
        self.autostart_chk = Gtk.CheckButton(label="Start Buddy automatically on system login")
        self.autostart_chk.set_active(AUTOSTART_FILE.exists())
        box.pack_start(self.autostart_chk, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="General"))

    # 2. BEHAVIOR TAB
    def _build_behavior_tab(self) -> None:
        box = self._create_tab_box()

        # Activity level
        act_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        act_box.pack_start(Gtk.Label(label="Activity / Energy Level:"), False, False, 0)
        self.act_adj = Gtk.Adjustment(value=self.config.get("activity_level", 1.0), lower=0.2, upper=2.5, step_increment=0.1, page_increment=0.2)
        act_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.act_adj)
        act_scale.set_digits(1)
        act_box.pack_start(act_scale, True, True, 0)
        box.pack_start(act_box, False, False, 0)

        # Movement speed
        speed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        speed_box.pack_start(Gtk.Label(label="Movement Speed:"), False, False, 0)
        self.speed_adj = Gtk.Adjustment(value=self.config.get("speed", 1.0), lower=0.5, upper=2.5, step_increment=0.1, page_increment=0.2)
        speed_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.speed_adj)
        speed_scale.set_digits(1)
        speed_box.pack_start(speed_scale, True, True, 0)
        box.pack_start(speed_box, False, False, 0)

        # Behavioral options
        beh_cfg = self.config.get("behavior", {})
        self.curiosity_chk = Gtk.CheckButton(label="Curious cursor inspection (looks toward and follows pointer)")
        self.curiosity_chk.set_active(beh_cfg.get("curiosity_enabled", True))
        box.pack_start(self.curiosity_chk, False, False, 0)

        self.wander_chk = Gtk.CheckButton(label="Autonomous wandering and desktop exploration")
        self.wander_chk.set_active(beh_cfg.get("wandering_enabled", True))
        box.pack_start(self.wander_chk, False, False, 0)

        self.sleep_chk = Gtk.CheckButton(label="Allow Buddy to take cozy naps when system is idle")
        self.sleep_chk.set_active(beh_cfg.get("sleep_enabled", True))
        box.pack_start(self.sleep_chk, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Behavior"))

    # 3. APPEARANCE TAB
    def _build_appearance_tab(self) -> None:
        box = self._create_tab_box()

        self.click_chk = Gtk.CheckButton(label="100% Click-Through Overlay (Clicks pass through directly to desktop)")
        self.click_chk.set_active(self.config.get("click_through", False))
        box.pack_start(self.click_chk, False, False, 0)

        self.shake_chk = Gtk.CheckButton(label="Screen Shake on heavy kinetic impacts (Hulk Smash, landings)")
        self.shake_chk.set_active(self.config.get("screen_shake_enabled", True))
        box.pack_start(self.shake_chk, False, False, 0)

        self.badge_chk = Gtk.CheckButton(label="Show floating Pomodoro status pill badge near Buddy")
        self.badge_chk.set_active(self.config.get("show_pomodoro_badge", True))
        box.pack_start(self.badge_chk, False, False, 0)

        # Movement Area
        mon_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        mon_box.pack_start(Gtk.Label(label="Desktop Movement Area:"), False, False, 0)
        self.mon_combo = Gtk.ComboBoxText()
        self.mon_combo.append("current_monitor", "Primary / Active Monitor")
        self.mon_combo.append("all_monitors", "All Connected Monitors")
        self.mon_combo.set_active_id(self.config.get("movement_area", "current_monitor"))
        mon_box.pack_start(self.mon_combo, False, False, 0)
        box.pack_start(mon_box, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Appearance"))

    # 4. POMODORO TAB
    def _build_pomodoro_tab(self) -> None:
        box = self._create_tab_box()
        p_cfg = self.config.get("pomodoro", {})

        # Work Duration
        w_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        w_box.pack_start(Gtk.Label(label="Focus Work Duration (minutes):"), False, False, 0)
        self.pomo_work_spin = Gtk.SpinButton.new_with_range(1, 120, 1)
        self.pomo_work_spin.set_value(float(p_cfg.get("work_duration", 25)))
        w_box.pack_start(self.pomo_work_spin, False, False, 0)
        box.pack_start(w_box, False, False, 0)

        # Short Break
        sb_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        sb_box.pack_start(Gtk.Label(label="Short Break Duration (minutes):"), False, False, 0)
        self.pomo_sb_spin = Gtk.SpinButton.new_with_range(1, 30, 1)
        self.pomo_sb_spin.set_value(float(p_cfg.get("short_break_duration", 5)))
        sb_box.pack_start(self.pomo_sb_spin, False, False, 0)
        box.pack_start(sb_box, False, False, 0)

        # Long Break
        lb_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        lb_box.pack_start(Gtk.Label(label="Long Break Duration (minutes):"), False, False, 0)
        self.pomo_lb_spin = Gtk.SpinButton.new_with_range(1, 60, 1)
        self.pomo_lb_spin.set_value(float(p_cfg.get("long_break_duration", 15)))
        lb_box.pack_start(self.pomo_lb_spin, False, False, 0)
        box.pack_start(lb_box, False, False, 0)

        # Sessions before long break
        cyc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        cyc_box.pack_start(Gtk.Label(label="Sessions Before Long Break:"), False, False, 0)
        self.pomo_cycle_spin = Gtk.SpinButton.new_with_range(1, 12, 1)
        self.pomo_cycle_spin.set_value(int(p_cfg.get("sessions_before_long_break", 4)))
        cyc_box.pack_start(self.pomo_cycle_spin, False, False, 0)
        box.pack_start(cyc_box, False, False, 0)

        # Auto start breaks and notify
        self.pomo_auto_break = Gtk.CheckButton(label="Automatically start break when focus finishes")
        self.pomo_auto_break.set_active(p_cfg.get("auto_start_breaks", True))
        box.pack_start(self.pomo_auto_break, False, False, 0)

        self.pomo_notify_chk = Gtk.CheckButton(label="Send desktop notifications for Pomodoro intervals")
        self.pomo_notify_chk.set_active(p_cfg.get("notifications_enabled", True))
        box.pack_start(self.pomo_notify_chk, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Pomodoro"))

    # 5. PERFORMANCE TAB
    def _build_performance_tab(self) -> None:
        box = self._create_tab_box()

        # Quality Preset buttons
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        preset_box.pack_start(Gtk.Label(label="Quality Preset:"), False, False, 0)
        for preset in ["Low", "Balanced", "High", "Ultra"]:
            btn = Gtk.Button(label=preset)
            btn.connect("clicked", self._on_preset_clicked, preset)
            preset_box.pack_start(btn, False, False, 0)
        box.pack_start(preset_box, False, False, 0)

        # Target FPS
        fps_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        fps_box.pack_start(Gtk.Label(label="Target FPS:"), False, False, 0)
        self.fps_combo = Gtk.ComboBoxText()
        self.fps_combo.append("30", "30 FPS (Battery Saver)")
        self.fps_combo.append("60", "60 FPS (Smooth Default)")
        self.fps_combo.append("120", "120 FPS (High Refresh Rate)")
        self.fps_combo.set_active_id(str(self.config.get("fps", 60)))
        fps_box.pack_start(self.fps_combo, False, False, 0)
        box.pack_start(fps_box, False, False, 0)

        # Low power mode
        self.low_power_chk = Gtk.CheckButton(label="Low Power Mode (caps at 30 FPS, reduces ambient particles)")
        self.low_power_chk.set_active(self.config.get("low_power_mode", False))
        box.pack_start(self.low_power_chk, False, False, 0)

        # Particle Limit
        part_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        part_box.pack_start(Gtk.Label(label="Maximum Particles:"), False, False, 0)
        self.part_adj = Gtk.Adjustment(value=self.config.get("particle_limit", 300), lower=50, upper=600, step_increment=25, page_increment=50)
        part_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.part_adj)
        part_scale.set_digits(0)
        part_box.pack_start(part_scale, True, True, 0)
        box.pack_start(part_box, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Performance"))

    # 6. ACCESSIBILITY TAB
    def _build_accessibility_tab(self) -> None:
        box = self._create_tab_box()
        a_cfg = self.config.get("accessibility", {})

        self.reduced_motion_chk = Gtk.CheckButton(label="Reduced motion (calmer movements, slower dashing)")
        self.reduced_motion_chk.set_active(a_cfg.get("reduced_motion", False))
        box.pack_start(self.reduced_motion_chk, False, False, 0)

        self.no_flash_chk = Gtk.CheckButton(label="Disable flashing effects (mutes high-frequency strobing)")
        self.no_flash_chk.set_active(a_cfg.get("disable_flashing", False))
        box.pack_start(self.no_flash_chk, False, False, 0)

        self.mute_all_chk = Gtk.CheckButton(label="Mute all audio completely (Quiet Mode)")
        self.mute_all_chk.set_active(a_cfg.get("mute_all", False))
        box.pack_start(self.mute_all_chk, False, False, 0)

        self.notebook.append_page(box, Gtk.Label(label="Accessibility"))

    def _on_preset_clicked(self, button: Gtk.Button, preset: str) -> None:
        if preset == "Low":
            self.low_power_chk.set_active(True)
            self.fps_combo.set_active_id("30")
            self.part_adj.set_value(100)
            self.shake_chk.set_active(False)
        elif preset == "Balanced":
            self.low_power_chk.set_active(False)
            self.fps_combo.set_active_id("60")
            self.part_adj.set_value(250)
            self.shake_chk.set_active(True)
        elif preset == "High":
            self.low_power_chk.set_active(False)
            self.fps_combo.set_active_id("60")
            self.part_adj.set_value(400)
            self.shake_chk.set_active(True)
        elif preset == "Ultra":
            self.low_power_chk.set_active(False)
            self.fps_combo.set_active_id("120")
            self.part_adj.set_value(600)
            self.shake_chk.set_active(True)

    def apply_settings(self) -> None:
        """Commit all GUI configurations to persistent storage and live engine."""
        # General
        chosen_skin = self.skin_combo.get_active_id()
        if chosen_skin and chosen_skin != self.engine.character.skin_id:
            self.engine.switch_skin(chosen_skin)
        self.config.set("skin", chosen_skin or "thor", auto_save=False)
        self.config.set("scale", self.scale_adj.get_value(), auto_save=False)
        self.config.set("sound_enabled", self.audio_chk.get_active(), auto_save=False)
        self.config.set("sound_volume", self.vol_adj.get_value() / 100.0, auto_save=False)

        # Behavior
        self.config.set("activity_level", self.act_adj.get_value(), auto_save=False)
        self.config.set("speed", self.speed_adj.get_value(), auto_save=False)
        self.config.set("behavior", {
            "curiosity_enabled": self.curiosity_chk.get_active(),
            "wandering_enabled": self.wander_chk.get_active(),
            "sleep_enabled": self.sleep_chk.get_active()
        }, auto_save=False)

        # Appearance
        self.config.set("click_through", self.click_chk.get_active(), auto_save=False)
        self.config.set("screen_shake_enabled", self.shake_chk.get_active(), auto_save=False)
        self.config.set("show_pomodoro_badge", self.badge_chk.get_active(), auto_save=False)
        self.config.set("movement_area", self.mon_combo.get_active_id() or "current_monitor", auto_save=False)

        # Pomodoro
        self.config.set("pomodoro", {
            "work_duration": int(self.pomo_work_spin.get_value()),
            "short_break_duration": int(self.pomo_sb_spin.get_value()),
            "long_break_duration": int(self.pomo_lb_spin.get_value()),
            "sessions_before_long_break": int(self.pomo_cycle_spin.get_value()),
            "auto_start_breaks": self.pomo_auto_break.get_active(),
            "notifications_enabled": self.pomo_notify_chk.get_active()
        }, auto_save=False)

        # Performance
        target_fps = int(self.fps_combo.get_active_id() or "60")
        self.config.set("fps", target_fps, auto_save=False)
        self.config.set("low_power_mode", self.low_power_chk.get_active(), auto_save=False)
        self.config.set("particle_limit", int(self.part_adj.get_value()), auto_save=False)

        # Accessibility
        self.config.set("accessibility", {
            "reduced_motion": self.reduced_motion_chk.get_active(),
            "disable_flashing": self.no_flash_chk.get_active(),
            "mute_all": self.mute_all_chk.get_active()
        }, auto_save=False)

        self.config.save()

        # Update live engine states
        self.engine.character.scale = self.config.get("scale", 1.0)
        self.engine.click_through = self.config.get("click_through", False)
        self.engine.window.set_click_through(self.engine.click_through)
        self.engine.particles.max_particles = self.config.get("particle_limit", 300)

        # Update audio
        if self.config.get("accessibility", {}).get("mute_all", False):
            self.engine.audio.enabled = False
        else:
            self.engine.audio.enabled = self.config.get("sound_enabled", True)
            self.engine.audio.volume = self.config.get("sound_volume", 0.7)

        # Reload Pomodoro settings in manager
        if hasattr(self.engine, "pomodoro"):
            self.engine.pomodoro._load_from_config()

        # Autostart
        if self.autostart_chk.get_active():
            self._install_autostart()
        else:
            self._remove_autostart()

    def _install_autostart(self) -> None:
        try:
            AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
            content = """[Desktop Entry]
Type=Application
Name=Buddy Desktop Pet
Comment=Animated superhero and companion for Linux desktops
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

    def _remove_autostart(self) -> None:
        if AUTOSTART_FILE.exists():
            try:
                AUTOSTART_FILE.unlink()
            except Exception:
                pass


def show_settings_dialog(engine, parent=None):
    """Open the Buddy 2.0 multi-section preferences dialog."""
    dialog = SettingsDialog(engine, parent=parent)
    response = dialog.run()
    if response in (Gtk.ResponseType.APPLY, Gtk.ResponseType.OK):
        dialog.apply_settings()
    dialog.destroy()
