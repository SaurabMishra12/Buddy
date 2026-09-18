"""Right-click context menu for instant character interactions."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk
from skins.manager import skin_manager


def show_context_menu(engine, event: Gdk.EventButton):
    """Display popup context menu with all character options."""
    menu = Gtk.Menu()

    # 1. Signature Move
    sig_item = Gtk.MenuItem(label="⚡ Perform Signature Move (Double-Click)")
    sig_item.connect("activate", lambda _: engine.trigger_signature_ability())
    menu.append(sig_item)

    # Quick skin cycling
    next_item = Gtk.MenuItem(label="➡️ Next Character (Scroll / Middle-Click)")
    next_item.connect("activate", lambda _: engine.next_skin())
    menu.append(next_item)

    menu.append(Gtk.SeparatorMenuItem())

    # 2. Change Skin Submenu
    skin_sub = Gtk.MenuItem(label=f"🎭 Switch Skin (Current: {engine.character.skin_id.upper()})")
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

    # 3. Trigger Ability Submenu
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

    # 4. Scale Submenu
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

    # 5. Pause / Resume
    pause_text = "▶  Resume Buddy" if engine.paused else "⏸  Pause Buddy"
    pause_item = Gtk.MenuItem(label=pause_text)
    pause_item.connect("activate", lambda _: engine.toggle_pause())
    menu.append(pause_item)

    # 6. Sound Toggle
    sound_active = engine.audio.enabled
    sound_item = Gtk.CheckMenuItem(label="🔊 Sound Effects")
    sound_item.set_active(sound_active)
    sound_item.connect("toggled", lambda w: _toggle_sound(engine, w.get_active()))
    menu.append(sound_item)

    # 7. Reset Position to center
    reset_item = Gtk.MenuItem(label="🎯 Reset Position to Screen Center")
    reset_item.connect("activate", lambda _: _reset_pos(engine))
    menu.append(reset_item)

    # 8. Settings
    settings_item = Gtk.MenuItem(label="⚙️ Settings Dialog...")
    settings_item.connect("activate", lambda _: _open_settings(engine))
    menu.append(settings_item)

    menu.append(Gtk.SeparatorMenuItem())

    # 9. Quit
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


def _open_skin_selector(engine):
    from ui.skin_selector import show_skin_selector
    show_skin_selector(engine)


def _open_settings(engine):
    from ui.settings_dialog import show_settings_dialog
    show_settings_dialog(engine)


def _reset_pos(engine):
    engine.character.x = engine.window.screen_w * 0.5
    engine.character.y = engine.window.screen_h * 0.4
    engine.character.vx = 0.0
    engine.character.vy = 0.0
    engine.window.move_to(engine.character.x, engine.character.y)
    engine.particles.burst_sparks(engine.character.x, engine.character.y, count=30)
