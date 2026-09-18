"""Right-click context menu for instant character interactions."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk


def show_context_menu(engine, event: Gdk.EventButton):
    """Display popup context menu at click location."""
    menu = Gtk.Menu()

    # Skin change item
    skin_item = Gtk.MenuItem(label=f"Change Skin (Current: {engine.character.skin_id.capitalize()})...")
    skin_item.connect("activate", lambda _: _open_skin_selector(engine))
    menu.append(skin_item)

    # Pause / Resume
    pause_text = "Resume Buddy" if engine.paused else "Pause Buddy"
    pause_item = Gtk.MenuItem(label=pause_text)
    pause_item.connect("activate", lambda _: engine.toggle_pause())
    menu.append(pause_item)

    # Trigger Ability submenu
    meta = engine.character.get_capabilities()
    abilities = engine.config.get("abilities", [])
    from skins.manager import skin_manager
    skin_meta = skin_manager.get_metadata(engine.character.skin_id)
    if skin_meta and skin_meta.get("abilities"):
        ab_menu = Gtk.Menu()
        ab_sub = Gtk.MenuItem(label="Trigger Ability")
        ab_sub.set_submenu(ab_menu)
        for ab in skin_meta["abilities"]:
            ab_item = Gtk.MenuItem(label=ab.replace("_", " ").title())
            ab_item.connect("activate", lambda _, a=ab: engine.character.trigger_ability(
                a, engine.cursor_x, engine.cursor_y, engine.particles, engine.audio
            ))
            ab_menu.append(ab_item)
        menu.append(ab_sub)

    menu.append(Gtk.SeparatorMenuItem())

    # Click-through toggle
    click_item = Gtk.CheckMenuItem(label="100% Click-Through Overlay")
    click_item.set_active(engine.click_through)
    click_item.connect("toggled", lambda _: engine.toggle_click_through())
    menu.append(click_item)

    # Reset position to center
    reset_item = Gtk.MenuItem(label="Reset Position")
    reset_item.connect("activate", lambda _: _reset_pos(engine))
    menu.append(reset_item)

    # Settings
    settings_item = Gtk.MenuItem(label="Settings...")
    settings_item.connect("activate", lambda _: _open_settings(engine))
    menu.append(settings_item)

    menu.append(Gtk.SeparatorMenuItem())

    # Quit
    quit_item = Gtk.MenuItem(label="Quit Buddy")
    quit_item.connect("activate", lambda _: Gtk.main_quit())
    menu.append(quit_item)

    menu.show_all()
    menu.popup_at_pointer(event)


def _open_skin_selector(engine):
    from ui.skin_selector import show_skin_selector
    show_skin_selector(engine)


def _open_settings(engine):
    from ui.settings_dialog import show_settings_dialog
    show_settings_dialog(engine)


def _reset_pos(engine):
    engine.character.x = engine.window.bounds[0] + engine.window.bounds[2] * 0.5
    engine.character.y = engine.window.bounds[1] + engine.window.bounds[3] * 0.4
    engine.character.vx = 0.0
    engine.character.vy = 0.0
    engine.particles.sky_strike(engine.character.x, engine.character.y)
