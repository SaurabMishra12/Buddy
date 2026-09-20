"""Right-click context menu for instant character interactions, Pomodoro controls, and modes."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
from skins.manager import skin_manager
from pomodoro.manager import PomodoroState


def show_context_menu(engine, event: Gdk.EventButton):
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
    gallery_item.connect("activate", lambda _: _open_skin_selector(engine))
    skin_menu.append(gallery_item)
    menu.append(skin_sub)

    # Direct Character Gallery entry
    browse_gallery = Gtk.MenuItem(label="🎨 Character Gallery & Personalities...")
    browse_gallery.connect("activate", lambda _: _open_skin_selector(engine))
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
        pomo_stats.connect("activate", lambda _: _open_stats(engine))
        pomo_menu.append(pomo_stats)

        menu.append(pomo_sub)

    # 6. Buddy Mode Submenu
    mode_sub = Gtk.MenuItem(label="🛡️ Companion Mode")
    mode_menu = Gtk.Menu()
    mode_sub.set_submenu(mode_menu)

    click_thru_item = Gtk.CheckMenuItem(label="Click-Through Overlay")
    click_thru_item.set_active(engine.click_through)
    click_thru_item.connect("toggled", lambda w: engine.toggle_click_through())
    mode_menu.append(click_thru_item)

    is_focus = engine.config.get("focus_mode", False)
    focus_mode_item = Gtk.CheckMenuItem(label="Focus Mode (Calm & Unobtrusive)")
    focus_mode_item.set_active(is_focus)
    focus_mode_item.connect("toggled", lambda w: _toggle_focus_mode(engine, w.get_active()))
    mode_menu.append(focus_mode_item)

    is_quiet = engine.config.get("accessibility", {}).get("mute_all", False) or not engine.audio.enabled
    quiet_mode_item = Gtk.CheckMenuItem(label="Quiet Mode (Mute Audio)")
    quiet_mode_item.set_active(is_quiet)
    quiet_mode_item.connect("toggled", lambda w: _toggle_sound(engine, not w.get_active()))
    mode_menu.append(quiet_mode_item)

    menu.append(mode_sub)

    # 7. Scale Submenu
    scale_sub = Gtk.MenuItem(label="📏 Pet Size")
    scale_menu = Gtk.Menu()
    scale_sub.set_submenu(scale_menu)
    for label, sc in [("Small (75%)", 0.75), ("Normal (100%)", 1.0), ("Large (125%)", 1.25), ("Giant (150%)", 1.5)]:
        cur_sc = getattr(engine.character, "scale", 1.0)
        chk = "✓ " if abs(cur_sc - sc) < 0.1 else "   "
        s_item = Gtk.MenuItem(label=f"{chk}{label}")
        s_item.connect("activate", lambda _, val=sc: engine.set_scale(val))
        scale_menu.append(s_item)
    menu.append(scale_sub)

    menu.append(Gtk.SeparatorMenuItem())

    # 8. Pause / Resume
    pause_text = "▶  Resume Buddy" if engine.paused else "⏸  Pause Buddy"
    pause_item = Gtk.MenuItem(label=pause_text)
    pause_item.connect("activate", lambda _: engine.toggle_pause())
    menu.append(pause_item)

    # 9. Reset Position to center
    reset_item = Gtk.MenuItem(label="🎯 Reset Position to Screen Center")
    reset_item.connect("activate", lambda _: _reset_pos(engine))
    menu.append(reset_item)

    # 10. Settings Dialog
    settings_item = Gtk.MenuItem(label="⚙️ Preferences...")
    settings_item.connect("activate", lambda _: _open_settings(engine))
    menu.append(settings_item)

    menu.append(Gtk.SeparatorMenuItem())

    # 11. Quit
    quit_item = Gtk.MenuItem(label="❌ Quit Buddy")
    quit_item.connect("activate", lambda _: Gtk.main_quit())
    menu.append(quit_item)

    menu.show_all()
    try:
        menu.popup_at_pointer(event)
    except Exception:
        menu.popup(None, None, None, None, event.button, event.time)


def _toggle_sound(engine, enabled: bool):
    engine.audio.enabled = enabled
    engine.config.set("sound_enabled", enabled)


def _toggle_focus_mode(engine, enabled: bool):
    engine.config.set("focus_mode", enabled)


def _open_skin_selector(engine):
    from ui.skin_selector import show_skin_selector
    show_skin_selector(engine)


def _open_settings(engine):
    from ui.settings_dialog import show_settings_dialog
    show_settings_dialog(engine)


def _open_stats(engine):
    from ui.stats_dialog import show_stats_dialog
    show_stats_dialog(engine)


def _reset_pos(engine):
    engine.character.x = engine.window.screen_w * 0.5
    engine.character.y = engine.window.screen_h * 0.4
    engine.character.vx = 0.0
    engine.character.vy = 0.0
    engine.window.move_to(engine.character.x, engine.character.y)
    engine.particles.burst_sparks(engine.character.x, engine.character.y, count=30)
