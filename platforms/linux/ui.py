"""Linux GTK3 UI dialogs and menus for Buddy 2.0."""

from pathlib import Path
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango
from skins.manager import skin_manager
from pomodoro.manager import PomodoroState
from pomodoro.statistics import PomodoroStats

AUTOSTART_DIR = Path.home() / ".config" / "autostart"
AUTOSTART_FILE = AUTOSTART_DIR / "buddy.desktop"


def show_linux_context_menu(engine, event: Gdk.EventButton):
    """Display modern popup context menu with companion options, Pomodoro controls, and modes."""
    menu = Gtk.Menu()

    # 1. Signature Move
    sig_item = Gtk.MenuItem(label="⚡ Perform Signature Move (Double-Click)")
    sig_item.connect("activate", lambda _: engine.trigger_signature_ability())
    menu.append(sig_item)

    # 2. Quick skin cycling
    next_item = Gtk.MenuItem(label="➡️ Next Character (Scroll / Middle-Click)")
    next_item.connect("activate", lambda _: engine.next_skin())
    menu.append(next_item)

    menu.append(Gtk.SeparatorMenuItem())

    # 3. Change Skin Submenu
    skin_sub = Gtk.MenuItem(label=f"🎭 Switch Skin ({engine.character.skin_id.upper()})")
    skin_menu = Gtk.Menu()
    skin_sub.set_submenu(skin_menu)

    for skin in skin_manager.get_available_skins():
        s_id = skin["id"]
        s_name = skin["name"]
        prefix = "✓ " if s_id == engine.character.skin_id else "   "
        item = Gtk.MenuItem(label=f"{prefix}{s_name}")
        item.connect("activate", lambda _, sid=s_id: engine.switch_skin(sid))
        skin_menu.append(item)

    skin_menu.append(Gtk.SeparatorMenuItem())
    gallery_item = Gtk.MenuItem(label="Browse Skin Gallery...")
    gallery_item.connect("activate", lambda _: show_linux_skin_selector(engine))
    skin_menu.append(gallery_item)
    menu.append(skin_sub)

    # Direct Character Gallery entry
    browse_gallery = Gtk.MenuItem(label="🎨 Character Gallery & Personalities...")
    browse_gallery.connect("activate", lambda _: show_linux_skin_selector(engine))
    menu.append(browse_gallery)

    # 4. Trigger Ability Submenu
    skin_meta = skin_manager.get_metadata(engine.character.skin_id)
    if skin_meta and skin_meta.get("abilities"):
        ab_sub = Gtk.MenuItem(label="✨ Abilities")
        ab_menu = Gtk.Menu()
        ab_sub.set_submenu(ab_menu)
        for ab in skin_meta["abilities"]:
            ab_item = Gtk.MenuItem(label=ab.replace("_", " ").title())
            ab_item.connect("activate", lambda _, a=ab: engine.character.trigger_ability(
                a, engine.cursor_x, engine.cursor_y, engine.particles, engine.audio
            ))
            ab_menu.append(ab_item)
        menu.append(ab_sub)

    menu.append(Gtk.SeparatorMenuItem())

    # 5. Pomodoro Productivity Submenu
    pomo_state = getattr(engine, "pomodoro", None)
    if pomo_state:
        status_str = pomo_state.status_label
        pomo_sub = Gtk.MenuItem(label=f"🍅 Pomodoro [{status_str}]")
        pomo_menu = Gtk.Menu()
        pomo_sub.set_submenu(pomo_menu)

        if pomo_state.state in (PomodoroState.WORK, PomodoroState.SHORT_BREAK, PomodoroState.LONG_BREAK):
            pomo_toggle = Gtk.MenuItem(label="⏸ Pause Focus Session")
            pomo_toggle.connect("activate", lambda _: pomo_state.pause())
            pomo_menu.append(pomo_toggle)
        elif pomo_state.state == PomodoroState.PAUSED:
            pomo_toggle = Gtk.MenuItem(label="▶ Resume Focus Session")
            pomo_toggle.connect("activate", lambda _: pomo_state.resume())
            pomo_menu.append(pomo_toggle)
        else:
            pomo_toggle = Gtk.MenuItem(label="▶ Start Focus Session (25 min)")
            pomo_toggle.connect("activate", lambda _: pomo_state.start_work())
            pomo_menu.append(pomo_toggle)

        pomo_skip = Gtk.MenuItem(label="⏭ Skip to Next Interval")
        pomo_skip.connect("activate", lambda _: pomo_state.skip())
        pomo_menu.append(pomo_skip)

        pomo_reset = Gtk.MenuItem(label="⏹ Reset Timer")
        pomo_reset.connect("activate", lambda _: pomo_state.reset())
        pomo_menu.append(pomo_reset)

        pomo_menu.append(Gtk.SeparatorMenuItem())
        pomo_stats = Gtk.MenuItem(label="📊 Productivity Statistics...")
        pomo_stats.connect("activate", lambda _: show_linux_stats_dialog(engine))
        pomo_menu.append(pomo_stats)

        menu.append(pomo_sub)

    menu.append(Gtk.SeparatorMenuItem())

    # 6. Mode & Behavior Controls
    ct_item = Gtk.CheckMenuItem(label="👻 Click-Through Mode")
    ct_item.set_active(engine.click_through)
    ct_item.connect("toggled", lambda w: engine.toggle_click_through())
    menu.append(ct_item)

    sound_item = Gtk.CheckMenuItem(label="🔊 Sound Effects")
    sound_item.set_active(engine.audio.enabled)
    sound_item.connect("toggled", lambda w: _toggle_sound(engine, w.get_active()))
    menu.append(sound_item)

    scale_sub = Gtk.MenuItem(label="🔍 Size / Scale")
    scale_menu = Gtk.Menu()
    scale_sub.set_submenu(scale_menu)
    for label, sc in [("Small (0.75x)", 0.75), ("Normal (1.0x)", 1.0), ("Large (1.35x)", 1.35), ("Giant (1.75x)", 1.75)]:
        cur_sc = getattr(engine.character, "scale", 1.0)
        chk = "✓ " if abs(cur_sc - sc) < 0.1 else "   "
        s_item = Gtk.MenuItem(label=f"{chk}{label}")
        s_item.connect("activate", lambda _, val=sc: engine.set_scale(val))
        scale_menu.append(s_item)
    menu.append(scale_sub)

    menu.append(Gtk.SeparatorMenuItem())

    # 7. Preferences & Quit
    settings_item = Gtk.MenuItem(label="⚙️ Settings & Preferences...")
    settings_item.connect("activate", lambda _: show_linux_settings_dialog(engine))
    menu.append(settings_item)

    stats_direct = Gtk.MenuItem(label="📈 Productivity Dashboard...")
    stats_direct.connect("activate", lambda _: show_linux_stats_dialog(engine))
    menu.append(stats_direct)

    quit_item = Gtk.MenuItem(label="❌ Quit Buddy")
    quit_item.connect("activate", lambda _: _quit_app())
    menu.append(quit_item)

    menu.show_all()
    menu.popup_at_pointer(event)


def _toggle_sound(engine, enabled: bool) -> None:
    engine.audio.enabled = enabled
    engine.config.set("sound_enabled", enabled)


def _quit_app():
    if Gtk.main_level() > 0:
        Gtk.main_quit()




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


"""Skin Gallery dialog: modern visual character browser with categories, search, personality metrics, and abilities."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Pango
from skins.manager import skin_manager


class SkinSelectorDialog(Gtk.Dialog):
    """Modern Buddy 2.0 visual skin gallery and character browser."""

    CATEGORIES = ["All", "Heroes", "Animals", "Fantasy", "Sci-Fi", "Cute"]

    def __init__(self, engine, parent=None):
        super().__init__(
            title="Buddy — Character Gallery",
            transient_for=parent,
            flags=0
        )
        self.engine = engine
        self.selected_skin_id = engine.character.skin_id
        self.active_category = "All"
        self.search_query = ""

        self.set_default_size(840, 580)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Header Bar
        header = Gtk.HeaderBar(title="Buddy Character Gallery", show_close_button=True)
        header.set_subtitle("Browse personalities, abilities, and desktop companions")
        self.set_titlebar(header)

        main_content = self.get_content_area()
        main_content.set_spacing(10)
        main_content.set_margin_top(12)
        main_content.set_margin_bottom(12)
        main_content.set_margin_left(14)
        main_content.set_margin_right(14)

        # Top Control Bar: Search and Categories
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        main_content.pack_start(top_bar, False, False, 0)

        # Search Entry
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search companion or ability...")
        self.search_entry.set_width_chars(24)
        self.search_entry.connect("search-changed", self._on_search_changed)
        top_bar.pack_start(self.search_entry, False, False, 0)

        # Category Buttons
        cat_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.cat_buttons = {}
        for cat in self.CATEGORIES:
            btn = Gtk.ToggleButton(label=cat)
            if cat == "All":
                btn.set_active(True)
            btn.connect("toggled", self._on_category_toggled, cat)
            cat_box.pack_start(btn, False, False, 0)
            self.cat_buttons[cat] = btn
        top_bar.pack_start(cat_box, True, True, 0)

        # Split Pane: Gallery Grid on left, Detailed Info Panel on right
        paned = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        main_content.pack_start(paned, True, True, 0)

        # Left: Scrollable Grid
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_min_content_width(480)
        paned.pack_start(scroller, True, True, 0)

        self.flow = Gtk.FlowBox()
        self.flow.set_valign(Gtk.Align.START)
        self.flow.set_max_children_per_line(2)
        self.flow.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.flow.set_homogeneous(True)
        self.flow.set_column_spacing(10)
        self.flow.set_row_spacing(10)
        self.flow.set_filter_func(self._filter_skin_card)
        scroller.add(self.flow)

        # Populate Skin Cards
        self.cards = {}
        skins = skin_manager.get_available_skins()
        for meta in skins:
            card = self._create_skin_card(meta)
            self.flow.add(card)
            self.cards[meta["id"]] = card

        self.flow.set_activate_on_single_click(True)
        self.flow.connect("selected-children-changed", self._on_selected_children_changed)
        self.flow.connect("child-activated", self._on_child_activated)

        # Right: Detail Sidebar
        self.detail_panel = self._create_detail_panel()
        paned.pack_start(self.detail_panel, False, False, 0)

        # Bottom Action Bar
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.apply_btn = self.add_button(f"Use This Buddy", Gtk.ResponseType.APPLY)
        self.apply_btn.get_style_context().add_class("suggested-action")

        self.show_all()

        # Select currently active skin
        for child in self.flow.get_children():
            box = child.get_child()
            if getattr(box, "skin_id", "") == self.selected_skin_id:
                self.flow.select_child(child)
                self._update_detail_panel(skin_manager.get_metadata(self.selected_skin_id) or {})
                break

    def _create_skin_card(self, meta: dict) -> Gtk.Widget:
        """Card widget inside the FlowBox."""
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_left(10)
        box.set_margin_right(10)
        frame.add(box)

        # Name + Active Indicator
        is_active = (meta["id"] == self.selected_skin_id)
        active_badge = " ✓ Active" if is_active else ""
        name_lbl = Gtk.Label()
        name_lbl.set_markup(f"<b>{meta.get('name', 'Unknown')}</b> <small><span color='#2ecc71'>{active_badge}</span></small>")
        name_lbl.set_xalign(0.0)
        box.pack_start(name_lbl, False, False, 0)

        # Category and Tag
        cat = meta.get("category", "original").capitalize()
        fly_str = " • 🕊️ Fly" if meta.get("canFly", False) else ""
        cat_lbl = Gtk.Label(label=f"{cat}{fly_str}")
        cat_lbl.get_style_context().add_class("dim-label")
        cat_lbl.set_xalign(0.0)
        box.pack_start(cat_lbl, False, False, 0)

        # Short summary
        desc = meta.get("description", "")
        if len(desc) > 75:
            desc = desc[:72] + "..."
        desc_lbl = Gtk.Label(label=desc)
        desc_lbl.set_line_wrap(True)
        desc_lbl.set_max_width_chars(24)
        desc_lbl.set_xalign(0.0)
        box.pack_start(desc_lbl, True, True, 0)

        # Ability tags
        abilities = meta.get("abilities", [])
        if abilities:
            ab_str = "⚡ " + ", ".join([a.replace("_", " ").title() for a in abilities[:2]])
            ab_lbl = Gtk.Label()
            ab_lbl.set_markup(f"<small><i>{ab_str}</i></small>")
            ab_lbl.set_xalign(0.0)
            box.pack_start(ab_lbl, False, False, 0)

        box.skin_id = meta["id"]
        box.meta = meta
        return frame

    def _create_detail_panel(self) -> Gtk.Widget:
        """Right sidebar displaying in-depth character personality and abilities."""
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        frame.set_min_content_width(280)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_top(14)
        vbox.set_margin_bottom(14)
        vbox.set_margin_left(14)
        vbox.set_margin_right(14)
        frame.add(vbox)

        # Title
        self.detail_title = Gtk.Label()
        self.detail_title.set_markup("<b><big>Character Details</big></b>")
        self.detail_title.set_xalign(0.0)
        vbox.pack_start(self.detail_title, False, False, 0)

        self.detail_subtitle = Gtk.Label()
        self.detail_subtitle.set_xalign(0.0)
        vbox.pack_start(self.detail_subtitle, False, False, 0)

        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

        # Full Description
        self.detail_desc = Gtk.Label()
        self.detail_desc.set_line_wrap(True)
        self.detail_desc.set_xalign(0.0)
        vbox.pack_start(self.detail_desc, False, False, 4)

        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

        # Personality Meters Section
        p_hdr = Gtk.Label()
        p_hdr.set_markup("<b>Personality Profile</b>")
        p_hdr.set_xalign(0.0)
        vbox.pack_start(p_hdr, False, False, 0)

        self.bar_energy = self._create_metric_row(vbox, "⚡ Energy:")
        self.bar_curiosity = self._create_metric_row(vbox, "🔍 Curiosity:")
        self.bar_playfulness = self._create_metric_row(vbox, "🎈 Playfulness:")

        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

        # Full Abilities List
        ab_hdr = Gtk.Label()
        ab_hdr.set_markup("<b>Special Abilities</b>")
        ab_hdr.set_xalign(0.0)
        vbox.pack_start(ab_hdr, False, False, 0)

        self.detail_abilities = Gtk.Label()
        self.detail_abilities.set_line_wrap(True)
        self.detail_abilities.set_xalign(0.0)
        vbox.pack_start(self.detail_abilities, True, True, 0)

        return frame

    def _create_metric_row(self, container: Gtk.Box, label_text: str) -> Gtk.ProgressBar:
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl = Gtk.Label(label=label_text)
        lbl.set_width_chars(12)
        lbl.set_xalign(0.0)
        bar = Gtk.ProgressBar()
        bar.set_fraction(0.5)
        bar.set_show_text(True)
        hbox.pack_start(lbl, False, False, 0)
        hbox.pack_start(bar, True, True, 0)
        container.pack_start(hbox, False, False, 2)
        return bar

    def _update_detail_panel(self, meta: dict) -> None:
        """Update detail sidebar with selected skin's attributes."""
        if not meta:
            return

        name = meta.get("name", "Unknown")
        cat = meta.get("category", "General").capitalize()
        fly_str = " • 🕊️ Can Fly" if meta.get("canFly", False) else " • 🐾 Ground"
        self.detail_title.set_markup(f"<b><big>{name}</big></b>")
        self.detail_subtitle.set_markup(f"<small>{cat}{fly_str}</small>")
        self.detail_desc.set_text(meta.get("description", "No description available."))

        # Personality metrics
        personality = meta.get("personality", {})
        energy = float(personality.get("energy", 0.7))
        curiosity = float(personality.get("curiosity", 0.6))
        playfulness = float(personality.get("playfulness", 0.6))

        self.bar_energy.set_fraction(energy)
        self.bar_energy.set_text(f"{int(energy * 100)}%")
        self.bar_curiosity.set_fraction(curiosity)
        self.bar_curiosity.set_text(f"{int(curiosity * 100)}%")
        self.bar_playfulness.set_fraction(playfulness)
        self.bar_playfulness.set_text(f"{int(playfulness * 100)}%")

        # Abilities list
        abs_list = meta.get("abilities", [])
        if abs_list:
            lines = [f"• <b>{a.replace('_', ' ').title()}</b>" for a in abs_list]
            self.detail_abilities.set_markup("\n".join(lines))
        else:
            self.detail_abilities.set_text("Default desktop movement and companion interactions.")

    def _filter_skin_card(self, child: Gtk.FlowBoxChild) -> bool:
        """Filter FlowBox items by active category and search query."""
        frame = child.get_child()
        box = frame.get_child()
        meta = getattr(box, "meta", {})
        if not meta:
            return True

        # 1. Category check
        if self.active_category != "All":
            meta_cat = str(meta.get("category", "")).lower()
            target_cat = self.active_category.lower()
            if target_cat == "heroes":
                if "hero" not in meta_cat:
                    return False
            elif target_cat not in meta_cat:
                return False

        # 2. Search query check
        if self.search_query:
            q = self.search_query.lower()
            name = str(meta.get("name", "")).lower()
            desc = str(meta.get("description", "")).lower()
            abilities = " ".join(meta.get("abilities", [])).lower()
            if q not in name and q not in desc and q not in abilities:
                return False

        return True

    def _on_category_toggled(self, button: Gtk.ToggleButton, category: str) -> None:
        if button.get_active():
            self.active_category = category
            # Deselect other category buttons
            for cat, btn in self.cat_buttons.items():
                if cat != category and btn.get_active():
                    btn.set_active(False)
            self.flow.invalidate_filter()

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self.search_query = entry.get_text().strip()
        self.flow.invalidate_filter()

    def _on_selected_children_changed(self, flowbox: Gtk.FlowBox) -> None:
        selected = flowbox.get_selected_children()
        if selected:
            frame = selected[0].get_child()
            box = frame.get_child()
            sid = getattr(box, "skin_id", None)
            meta = getattr(box, "meta", None)
            if sid and meta:
                self.selected_skin_id = sid
                self.apply_btn.set_label(f"Use {meta.get('name', sid)}")
                self._update_detail_panel(meta)

    def _on_child_activated(self, flowbox: Gtk.FlowBox, child: Gtk.FlowBoxChild) -> None:
        frame = child.get_child()
        box = frame.get_child()
        sid = getattr(box, "skin_id", None)
        if sid:
            self.selected_skin_id = sid
        self.response(Gtk.ResponseType.APPLY)


def show_skin_selector(engine, parent=None):
    """Open the modern Buddy 2.0 Skin Gallery dialog."""
    dialog = SkinSelectorDialog(engine, parent=parent)
    response = dialog.run()
    if response in (Gtk.ResponseType.APPLY, Gtk.ResponseType.OK, Gtk.ResponseType.ACCEPT):
        engine.switch_skin(dialog.selected_skin_id)
    dialog.destroy()


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
