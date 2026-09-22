"""Native macOS UI dialogs and popup context menus using AppKit."""

import sys
from pathlib import Path
from typing import Any, Optional

import AppKit
from Foundation import NSRect, NSPoint, NSSize, NSObject
from skins.manager import skin_manager
from pomodoro.manager import PomodoroState
from pomodoro.statistics import PomodoroStats
from platforms.macos.menu_bar import MenuActionTarget


def show_macos_context_menu(engine, event):
    """Display native macOS popup context menu at mouse location."""
    menu = AppKit.NSMenu.alloc().init()
    menu.setAutoenablesItems_(False)
    targets = []

    def add_item(title, cb=None, parent_menu=menu):
        item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, None, "")
        if cb:
            target = MenuActionTarget.alloc().initWithCallback_(cb)
            targets.append(target)
            item.setTarget_(target)
            item.setAction_("onAction:")
        parent_menu.addItem_(item)
        return item

    # 1. Signature Move
    add_item("⚡ Perform Signature Move", lambda _: engine.trigger_signature_ability())
    add_item("➡️ Next Character (Scroll / Middle-Click)", lambda _: engine.next_skin())
    menu.addItem_(AppKit.NSMenuItem.separatorItem())

    # 2. Switch Skin Submenu
    skin_sub = add_item(f"🎭 Switch Skin ({engine.character.skin_id.upper()})")
    skin_menu = AppKit.NSMenu.alloc().init()
    for s in skin_manager.get_available_skins():
        sid = s["id"]
        prefix = "✓ " if sid == engine.character.skin_id else "   "
        add_item(f"{prefix}{s.get('name', sid)}", lambda _, id=sid: engine.switch_skin(id), skin_menu)
    skin_sub.setSubmenu_(skin_menu)

    # 3. Abilities Submenu
    skin_meta = skin_manager.get_metadata(engine.character.skin_id)
    if skin_meta and skin_meta.get("abilities"):
        ab_sub = add_item("✨ Abilities")
        ab_menu = AppKit.NSMenu.alloc().init()
        for ab in skin_meta["abilities"]:
            add_item(
                ab.replace("_", " ").title(),
                lambda _, a=ab: engine.character.trigger_ability(
                    a, engine.cursor_x, engine.cursor_y, engine.particles, engine.audio
                ),
                ab_menu
            )
        ab_sub.setSubmenu_(ab_menu)

    menu.addItem_(AppKit.NSMenuItem.separatorItem())

    # 4. Pomodoro Submenu
    pomo = getattr(engine, "pomodoro", None)
    if pomo:
        pomo_sub = add_item(f"🍅 Pomodoro [{pomo.status_label}]")
        pomo_menu = AppKit.NSMenu.alloc().init()
        if pomo.state in (PomodoroState.WORK, PomodoroState.SHORT_BREAK, PomodoroState.LONG_BREAK):
            add_item("⏸ Pause Focus Session", lambda _: pomo.pause(), pomo_menu)
        elif pomo.state == PomodoroState.PAUSED:
            add_item("▶ Resume Focus Session", lambda _: pomo.resume(), pomo_menu)
        else:
            add_item("▶ Start Focus Session (25 min)", lambda _: pomo.start_work(), pomo_menu)
        add_item("⏭ Skip to Next", lambda _: pomo.skip(), pomo_menu)
        add_item("⏹ Reset Timer", lambda _: pomo.reset(), pomo_menu)
        pomo_sub.setSubmenu_(pomo_menu)

    menu.addItem_(AppKit.NSMenuItem.separatorItem())

    # 5. Modes & Preferences
    add_item(
        f"{'✓ ' if engine.click_through else '   '}Click-through Mode",
        lambda _: engine.toggle_click_through()
    )
    add_item(
        f"{'✓ ' if not engine.audio.enabled else '   '}Quiet Mode (Mute)",
        lambda _: _toggle_sound(engine, not engine.audio.enabled)
    )

    menu.addItem_(AppKit.NSMenuItem.separatorItem())
    add_item("Preferences...", lambda _: show_macos_settings_dialog(engine))
    add_item("Character Gallery...", lambda _: show_macos_skin_selector(engine))
    add_item("Statistics...", lambda _: show_macos_stats_dialog(engine))
    menu.addItem_(AppKit.NSMenuItem.separatorItem())
    add_item("Quit Buddy", lambda _: AppKit.NSApplication.sharedApplication().terminate_(None))

    ns_event = getattr(event, "ns_event", None)
    if ns_event and hasattr(engine.window, "view"):
        AppKit.NSMenu.popUpContextMenu_withEvent_forView_(menu, ns_event, engine.window.view)


def _toggle_sound(engine, enabled: bool) -> None:
    engine.audio.enabled = enabled
    engine.config.set("sound_enabled", enabled)


# Active window references to prevent ARC collection while open
_active_dialogs = []


def show_macos_settings_dialog(engine, parent=None):
    """Show native macOS preferences window."""
    cfg = engine.config
    win_w, win_h = 480, 360

    style = (
        AppKit.NSWindowStyleMaskTitled |
        AppKit.NSWindowStyleMaskClosable
    )
    frame = NSRect(NSPoint(300, 300), NSSize(win_w, win_h))
    win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, style, AppKit.NSBackingStoreBuffered, False
    )
    win.setTitle_("Buddy Preferences")
    win.center()
    _active_dialogs.append(win)

    content = win.contentView()

    # Tab view
    tabs = AppKit.NSTabView.alloc().initWithFrame_(NSRect(NSPoint(16, 60), NSSize(win_w - 32, win_h - 80)))

    # Tab 1: General
    tab1 = AppKit.NSTabViewItem.alloc().initWithIdentifier_("general")
    tab1.setLabel_("General")
    v1 = AppKit.NSView.alloc().initWithFrame_(tabs.contentRect())

    lbl_skin = AppKit.NSTextField.labelWithString_("Default Character:")
    lbl_skin.setFrame_(NSRect(NSPoint(20, 180), NSSize(140, 24)))
    v1.addSubview_(lbl_skin)

    skin_popup = AppKit.NSPopUpButton.alloc().initWithFrame_pullsDown_(NSRect(NSPoint(160, 178), NSSize(200, 26)), False)
    skins = skin_manager.get_available_skins()
    for s in skins:
        skin_popup.addItemWithTitle_(s.get("name", s["id"]))
    cur_id = cfg.get("skin", "thor")
    for i, s in enumerate(skins):
        if s["id"] == cur_id:
            skin_popup.selectItemAtIndex_(i)
            break
    v1.addSubview_(skin_popup)

    # Scale slider
    lbl_scale = AppKit.NSTextField.labelWithString_("Scale (Size):")
    lbl_scale.setFrame_(NSRect(NSPoint(20, 140), NSSize(140, 24)))
    v1.addSubview_(lbl_scale)

    scale_slider = AppKit.NSSlider.alloc().initWithFrame_(NSRect(NSPoint(160, 140), NSSize(180, 24)))
    scale_slider.setMinValue_(0.5)
    scale_slider.setMaxValue_(2.0)
    scale_slider.setDoubleValue_(float(cfg.get("scale", 1.0)))
    v1.addSubview_(scale_slider)

    # Volume slider
    lbl_vol = AppKit.NSTextField.labelWithString_("Master Volume:")
    lbl_vol.setFrame_(NSRect(NSPoint(20, 100), NSSize(140, 24)))
    v1.addSubview_(lbl_vol)

    vol_slider = AppKit.NSSlider.alloc().initWithFrame_(NSRect(NSPoint(160, 100), NSSize(180, 24)))
    vol_slider.setMinValue_(0.0)
    vol_slider.setMaxValue_(1.0)
    vol_slider.setDoubleValue_(float(cfg.get("sound_volume", 0.7)))
    v1.addSubview_(vol_slider)

    # Autostart checkbox
    from platforms.macos.autostart import MacOSAutostart
    autostart_mgr = MacOSAutostart()
    chk_autostart = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(20, 60), NSSize(280, 24)))
    chk_autostart.setButtonType_(AppKit.NSButtonTypeSwitch)
    chk_autostart.setTitle_("Start Buddy automatically on login")
    chk_autostart.setState_(1 if autostart_mgr.is_enabled() else 0)
    v1.addSubview_(chk_autostart)

    tab1.setView_(v1)
    tabs.addTabViewItem_(tab1)

    # Tab 2: Appearance & Effects
    tab2 = AppKit.NSTabViewItem.alloc().initWithIdentifier_("effects")
    tab2.setLabel_("Effects")
    v2 = AppKit.NSView.alloc().initWithFrame_(tabs.contentRect())

    chk_particles = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(20, 170), NSSize(240, 24)))
    chk_particles.setButtonType_(AppKit.NSButtonTypeSwitch)
    chk_particles.setTitle_("Enable Particles & Magic Sparks")
    chk_particles.setState_(1 if cfg.get("particles_enabled", True) else 0)
    v2.addSubview_(chk_particles)

    chk_shake = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(20, 130), NSSize(240, 24)))
    chk_shake.setButtonType_(AppKit.NSButtonTypeSwitch)
    chk_shake.setTitle_("Enable Screen Shake on Impact")
    chk_shake.setState_(1 if cfg.get("screen_shake_enabled", True) else 0)
    v2.addSubview_(chk_shake)

    chk_power = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(20, 90), NSSize(240, 24)))
    chk_power.setButtonType_(AppKit.NSButtonTypeSwitch)
    chk_power.setTitle_("Low Power Mode (30 FPS)")
    chk_power.setState_(1 if cfg.get("low_power_mode", False) else 0)
    v2.addSubview_(chk_power)

    tab2.setView_(v2)
    tabs.addTabViewItem_(tab2)

    content.addSubview_(tabs)

    # Action Buttons: Cancel and Save
    btn_cancel = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(win_w - 200, 16), NSSize(84, 30)))
    btn_cancel.setTitle_("Cancel")
    btn_cancel.setBezelStyle_(AppKit.NSBezelStyleRounded)

    class DialogTarget(NSObject):
        def onCancel_(self_t, sender):
            win.close()
            if win in _active_dialogs:
                _active_dialogs.remove(win)

        def onSave_(self_t, sender):
            idx = skin_popup.indexOfSelectedItem()
            if 0 <= idx < len(skins):
                new_skin = skins[idx]["id"]
                cfg.set("skin", new_skin)
                engine.switch_skin(new_skin)

            new_scale = float(scale_slider.doubleValue())
            cfg.set("scale", new_scale)
            engine.set_scale(new_scale)

            new_vol = float(vol_slider.doubleValue())
            cfg.set("sound_volume", new_vol)
            engine.audio.volume = new_vol

            cfg.set("particles_enabled", chk_particles.state() == 1)
            cfg.set("screen_shake_enabled", chk_shake.state() == 1)
            cfg.set("low_power_mode", chk_power.state() == 1)

            if chk_autostart.state() == 1:
                autostart_mgr.enable()
            else:
                autostart_mgr.disable()

            cfg.save()
            win.close()
            if win in _active_dialogs:
                _active_dialogs.remove(win)

    dt = DialogTarget.alloc().init()
    _active_dialogs.append(dt)
    btn_cancel.setTarget_(dt)
    btn_cancel.setAction_("onCancel:")
    content.addSubview_(btn_cancel)

    btn_save = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(win_w - 104, 16), NSSize(90, 30)))
    btn_save.setTitle_("Save & Apply")
    btn_save.setBezelStyle_(AppKit.NSBezelStyleRounded)
    btn_save.setKeyEquivalent_("\r")
    btn_save.setTarget_(dt)
    btn_save.setAction_("onSave:")
    content.addSubview_(btn_save)

    win.makeKeyAndOrderFront_(None)


def show_macos_skin_selector(engine, parent=None):
    """Show native macOS character gallery dialog."""
    win_w, win_h = 560, 420
    style = (
        AppKit.NSWindowStyleMaskTitled |
        AppKit.NSWindowStyleMaskClosable
    )
    frame = NSRect(NSPoint(320, 260), NSSize(win_w, win_h))
    win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, style, AppKit.NSBackingStoreBuffered, False
    )
    win.setTitle_("Buddy 2.0 — Character Skin Gallery")
    win.center()
    _active_dialogs.append(win)

    content = win.contentView()

    # List of skins in table/scroll view or pop-up
    lbl_hdr = AppKit.NSTextField.labelWithString_("Select Your Desktop Companion:")
    lbl_hdr.setFrame_(NSRect(NSPoint(20, win_h - 40), NSSize(400, 24)))
    font = AppKit.NSFont.boldSystemFontOfSize_(14)
    lbl_hdr.setFont_(font)
    content.addSubview_(lbl_hdr)

    # Pop-up selector with description preview
    skins = skin_manager.get_available_skins()
    popup = AppKit.NSPopUpButton.alloc().initWithFrame_pullsDown_(NSRect(NSPoint(20, win_h - 80), NSSize(240, 28)), False)
    for s in skins:
        flight = " ✈️" if s.get("canFly") else ""
        popup.addItemWithTitle_(f"{s.get('name', s['id'])}{flight}")

    cur_skin = engine.character.skin_id
    for i, s in enumerate(skins):
        if s["id"] == cur_skin:
            popup.selectItemAtIndex_(i)
            break
    content.addSubview_(popup)

    # Description text view
    scroll = AppKit.NSScrollView.alloc().initWithFrame_(NSRect(NSPoint(20, 70), NSSize(win_w - 40, win_h - 165)))
    text_view = AppKit.NSTextView.alloc().initWithFrame_(scroll.contentRect())
    text_view.setEditable_(False)
    scroll.setDocumentView_(text_view)
    content.addSubview_(scroll)

    def update_desc():
        idx = popup.indexOfSelectedItem()
        if 0 <= idx < len(skins):
            s = skins[idx]
            abs_str = ", ".join(a.replace("_", " ").title() for a in s.get("abilities", []))
            desc_text = (
                f"NAME: {s.get('name', s['id'])}\n"
                f"CATEGORY: {s.get('category', 'general').capitalize()}\n"
                f"CAN FLY: {'Yes' if s.get('canFly') else 'No'}\n\n"
                f"DESCRIPTION:\n{s.get('description', '')}\n\n"
                f"SPECIAL ABILITIES:\n{abs_str}\n"
            )
            text_view.setString_(desc_text)

    update_desc()

    class GalleryTarget(NSObject):
        def onSelect_(self_t, sender):
            update_desc()

        def onApply_(self_t, sender):
            idx = popup.indexOfSelectedItem()
            if 0 <= idx < len(skins):
                target_id = skins[idx]["id"]
                engine.switch_skin(target_id)
            win.close()
            if win in _active_dialogs:
                _active_dialogs.remove(win)

        def onClose_(self_t, sender):
            win.close()
            if win in _active_dialogs:
                _active_dialogs.remove(win)

    gt = GalleryTarget.alloc().init()
    _active_dialogs.append(gt)
    popup.setTarget_(gt)
    popup.setAction_("onSelect:")

    btn_close = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(win_w - 220, 20), NSSize(84, 30)))
    btn_close.setTitle_("Close")
    btn_close.setBezelStyle_(AppKit.NSBezelStyleRounded)
    btn_close.setTarget_(gt)
    btn_close.setAction_("onClose:")
    content.addSubview_(btn_close)

    btn_switch = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(win_w - 124, 20), NSSize(110, 30)))
    btn_switch.setTitle_("Select Companion")
    btn_switch.setBezelStyle_(AppKit.NSBezelStyleRounded)
    btn_switch.setKeyEquivalent_("\r")
    btn_switch.setTarget_(gt)
    btn_switch.setAction_("onApply:")
    content.addSubview_(btn_switch)

    win.makeKeyAndOrderFront_(None)


def show_macos_stats_dialog(engine, parent=None):
    """Show native macOS Pomodoro and Focus productivity statistics."""
    stats = PomodoroStats()
    summary = stats.get_summary()

    today_mins = stats.sessions_today * 25.0
    h = int(today_mins // 60)
    m = int(today_mins % 60)
    today_str = f"{h}h {m}m" if h > 0 else f"{m}m"

    alert = AppKit.NSAlert.alloc().init()
    alert.setMessageText_("📊 Buddy 2.0 Focus & Productivity Statistics")
    alert.setInformativeText_(
        f"• Today's Focus:      {today_str}\n"
        f"• Sessions Today:     {stats.sessions_today}\n"
        f"• Sessions This Week: {stats.sessions_this_week}\n"
        f"• Current Streak:     {stats.streak_days} days\n"
        f"• Lifetime Focus:     {summary.get('total_focus_hours', 0)} hours\n"
        f"• Longest Streak:     {summary.get('longest_streak_days', 0)} days"
    )
    alert.addButtonWithTitle_("OK")
    alert.runModal()
