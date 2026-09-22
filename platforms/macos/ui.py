"""Native macOS UI dialogs and popup context menus using AppKit."""

import sys
from pathlib import Path
from typing import Any, Optional, List, Dict

import AppKit
from Foundation import NSRect, NSPoint, NSSize, NSObject
from skins.manager import skin_manager
from pomodoro.manager import PomodoroState
from pomodoro.statistics import PomodoroStats
from platforms.macos.menu_bar import MenuActionTarget
from platforms.macos.autostart import MacOSAutostart

# Global references to prevent garbage collection while windows/menus are open
_active_dialogs: List[Any] = []
_active_menu_targets: List[Any] = []


def _toggle_sound(engine: Any, enabled: bool) -> None:
    engine.audio.enabled = enabled
    engine.config.set("sound_enabled", enabled)


# ============================================================================
# Context Menu
# ============================================================================

def show_macos_context_menu(engine: Any, event: Any) -> None:
    """Display native macOS popup context menu at mouse location."""
    global _active_menu_targets
    _active_menu_targets.clear()

    menu = AppKit.NSMenu.alloc().init()
    menu.setAutoenablesItems_(False)

    def add_item(title: str, cb=None, parent_menu=menu):
        item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, None, "")
        if cb:
            target = MenuActionTarget.alloc().init()
            target.callback = cb
            _active_menu_targets.append(target)
            item.setTarget_(target)
            item.setAction_("onAction:")
        parent_menu.addItem_(item)
        return item

    # 1. Signature Move
    add_item("⚡ Perform Signature Move", lambda _: engine.trigger_signature_ability())
    add_item("➡️ Next Character (Scroll / Middle-Click)", lambda _: engine.next_skin())
    menu.addItem_(AppKit.NSMenuItem.separatorItem())

    # 2. Switch Skin Submenu
    cur_id = engine.character.skin_id
    skin_sub = add_item(f"🎭 Switch Skin ({cur_id.replace('_', ' ').title()})")
    skin_menu = AppKit.NSMenu.alloc().init()
    for s in skin_manager.get_available_skins():
        sid = s["id"]
        prefix = "✓ " if sid == cur_id else "   "
        s_name = s.get("name", sid)
        add_item(
            f"{prefix}{s_name}",
            lambda _, target_id=sid: (engine.switch_skin(target_id), engine.window.queue_draw()),
            skin_menu
        )
    skin_sub.setSubmenu_(skin_menu)

    # 3. Abilities Submenu
    skin_meta = skin_manager.get_metadata(cur_id)
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
        add_item("⏭ Skip to Next Interval", lambda _: pomo.skip(), pomo_menu)
        add_item("⏹ Reset Timer", lambda _: pomo.reset(), pomo_menu)
        pomo_sub.setSubmenu_(pomo_menu)

    menu.addItem_(AppKit.NSMenuItem.separatorItem())

    # 5. Modes & Preferences
    add_item(
        f"{'✓ ' if engine.click_through else '   '}👻 Click-Through Mode",
        lambda _: engine.toggle_click_through()
    )
    add_item(
        f"{'✓ ' if not engine.audio.enabled else '   '}🔇 Quiet Mode (Mute)",
        lambda _: _toggle_sound(engine, not engine.audio.enabled)
    )

    # Scale submenu
    scale_sub = add_item("🔍 Pet Scale")
    scale_menu = AppKit.NSMenu.alloc().init()
    cur_sc = getattr(engine.character, "scale", 1.0)
    for label, sc in [("Small (0.75x)", 0.75), ("Normal (1.0x)", 1.0), ("Large (1.35x)", 1.35), ("Giant (1.75x)", 1.75)]:
        chk = "✓ " if abs(cur_sc - sc) < 0.1 else "   "
        add_item(f"{chk}{label}", lambda _, val=sc: engine.set_scale(val), scale_menu)
    scale_sub.setSubmenu_(scale_menu)

    menu.addItem_(AppKit.NSMenuItem.separatorItem())
    add_item("⚙️ Preferences...", lambda _: show_macos_settings_dialog(engine))
    add_item("🎨 Character Gallery...", lambda _: show_macos_skin_selector(engine))
    add_item("📈 Productivity Dashboard...", lambda _: show_macos_stats_dialog(engine))
    menu.addItem_(AppKit.NSMenuItem.separatorItem())
    add_item("❌ Quit Buddy", lambda _: AppKit.NSApplication.sharedApplication().terminate_(None))

    ns_event = getattr(event, "ns_event", None)
    if ns_event and hasattr(engine.window, "view"):
        AppKit.NSMenu.popUpContextMenu_withEvent_forView_(menu, ns_event, engine.window.view)


# ============================================================================
# Target Handlers (Must be defined at module level in PyObjC)
# ============================================================================

class SettingsDialogTarget(NSObject):
    def onCancel_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.close()
            if self._win in _active_dialogs:
                _active_dialogs.remove(self._win)

    def onScaleChange_(self, sender):
        if hasattr(self, "_lbl_scale") and self._lbl_scale:
            val = round(float(sender.doubleValue()), 2)
            self._lbl_scale.setStringValue_(f"Scale: {int(val * 100)}%")

    def onVolChange_(self, sender):
        if hasattr(self, "_lbl_vol") and self._lbl_vol:
            val = round(float(sender.doubleValue()), 2)
            self._lbl_vol.setStringValue_(f"Volume: {int(val * 100)}%")

    def onSave_(self, sender):
        if not hasattr(self, "_ctx") or not self._ctx:
            return
        ctx = self._ctx
        engine = ctx["engine"]
        cfg = engine.config

        # Skin
        skin_popup = ctx["skin_popup"]
        skins = ctx["skins"]
        idx = skin_popup.indexOfSelectedItem()
        if 0 <= idx < len(skins):
            new_skin = skins[idx]["id"]
            cfg.set("skin", new_skin)
            engine.switch_skin(new_skin)

        # Scale
        new_scale = round(float(ctx["scale_slider"].doubleValue()), 2)
        cfg.set("scale", new_scale)
        engine.set_scale(new_scale)

        # Volume
        new_vol = round(float(ctx["vol_slider"].doubleValue()), 2)
        cfg.set("sound_volume", new_vol)
        engine.audio.set_volume(new_vol)

        # Switches
        cfg.set("particles_enabled", ctx["chk_particles"].state() == 1)
        cfg.set("screen_shake_enabled", ctx["chk_shake"].state() == 1)
        cfg.set("low_power_mode", ctx["chk_power"].state() == 1)

        # Autostart
        if ctx["chk_autostart"].state() == 1:
            ctx["autostart_mgr"].enable()
        else:
            ctx["autostart_mgr"].disable()

        cfg.save()
        if hasattr(self, "_win") and self._win:
            self._win.close()
            if self._win in _active_dialogs:
                _active_dialogs.remove(self._win)


class GalleryTableSource(NSObject):
    def numberOfRowsInTableView_(self, tv):
        return len(getattr(self, "items", []))

    def tableView_objectValueForTableColumn_row_(self, tv, col, row):
        items = getattr(self, "items", [])
        if 0 <= row < len(items):
            s = items[row]
            flight = " ✈️" if s.get("canFly") else ""
            return f"  {s.get('name', s['id'])}{flight}"
        return ""


class GalleryDialogTarget(NSObject):
    def onCategoryChange_(self, sender):
        if hasattr(self, "_filter_cb") and self._filter_cb:
            self._filter_cb()

    def onSearchChange_(self, sender):
        if hasattr(self, "_filter_cb") and self._filter_cb:
            self._filter_cb()

    def onTableSelect_(self, sender):
        if hasattr(self, "_update_card_cb") and self._update_card_cb:
            self._update_card_cb()

    def onTableDoubleClick_(self, sender):
        if hasattr(self, "_apply_cb") and self._apply_cb:
            self._apply_cb()

    def onApply_(self, sender):
        if hasattr(self, "_apply_cb") and self._apply_cb:
            self._apply_cb()

    def onClose_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.close()
            if self._win in _active_dialogs:
                _active_dialogs.remove(self._win)


class StatsDialogTarget(NSObject):
    def onClose_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.close()
            if self._win in _active_dialogs:
                _active_dialogs.remove(self._win)


# ============================================================================
# Modern Character Gallery Dialog
# ============================================================================

def show_macos_skin_selector(engine: Any, parent=None) -> None:
    """Show rich, visual native macOS Character Skin Gallery."""
    win_w, win_h = 720, 520
    style = (
        AppKit.NSWindowStyleMaskTitled |
        AppKit.NSWindowStyleMaskClosable |
        AppKit.NSWindowStyleMaskMiniaturizable
    )
    frame = NSRect(NSPoint(200, 200), NSSize(win_w, win_h))
    win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, style, AppKit.NSBackingStoreBuffered, False
    )
    win.setTitle_("Buddy 2.0 — Character Skin Gallery")
    win.center()
    _active_dialogs.append(win)

    content = win.contentView()

    all_skins = skin_manager.get_available_skins()
    filtered_skins: List[Dict[str, Any]] = list(all_skins)

    target = GalleryDialogTarget.alloc().init()
    target._win = win
    _active_dialogs.append(target)

    # 1. Top Controls Bar: Search + Category Segments
    search_field = AppKit.NSSearchField.alloc().initWithFrame_(NSRect(NSPoint(20, win_h - 48), NSSize(230, 28)))
    search_field.setPlaceholderString_("Search companion or ability...")
    search_field.setTarget_(target)
    search_field.setAction_("onSearchChange:")
    content.addSubview_(search_field)

    categories = ["All", "Heroes", "Animals", "Fantasy", "Sci-Fi", "Cute"]
    seg = AppKit.NSSegmentedControl.alloc().initWithFrame_(NSRect(NSPoint(260, win_h - 48), NSSize(win_w - 280, 28)))
    seg.setSegmentCount_(len(categories))
    for i, cat in enumerate(categories):
        seg.setLabel_forSegment_(cat, i)
        seg.setWidth_forSegment_(0, i)  # Auto-fit
    seg.setSelectedSegment_(0)
    seg.setTarget_(target)
    seg.setAction_("onCategoryChange:")
    content.addSubview_(seg)

    # 2. Left Side: Scrollable Table View
    table_w = 260
    scroll = AppKit.NSScrollView.alloc().initWithFrame_(NSRect(NSPoint(20, 68), NSSize(table_w, win_h - 130)))
    scroll.setHasVerticalScroller_(True)
    scroll.setBorderType_(AppKit.NSBezelBorder)

    table_view = AppKit.NSTableView.alloc().initWithFrame_(scroll.contentRect())
    col = AppKit.NSTableColumn.alloc().initWithIdentifier_("companion")
    col.setWidth_(table_w - 24)
    col.setTitle_("Characters (22)")
    table_view.addTableColumn_(col)
    table_view.setHeaderView_(None)  # Minimalist modern list
    table_view.setRowHeight_(28.0)

    src = GalleryTableSource.alloc().init()
    src.items = filtered_skins
    _active_dialogs.append(src)
    table_view.setDataSource_(src)
    table_view.setTarget_(target)
    table_view.setAction_("onTableSelect:")
    table_view.setDoubleAction_("onTableDoubleClick:")
    scroll.setDocumentView_(table_view)
    content.addSubview_(scroll)

    # 3. Right Side: Character Detail Card
    card_x = table_w + 36
    card_w = win_w - card_x - 20
    card_h = win_h - 130

    card_view = AppKit.NSBox.alloc().initWithFrame_(NSRect(NSPoint(card_x, 68), NSSize(card_w, card_h)))
    card_view.setTitlePosition_(AppKit.NSNoTitle)
    card_view.setBoxType_(AppKit.NSBoxTypeCustom)
    card_view.setFillColor_(AppKit.NSColor.windowBackgroundColor())
    card_view.setBorderColor_(AppKit.NSColor.separatorColor())
    card_view.setBorderWidth_(1.0)
    card_view.setCornerRadius_(8.0)
    content.addSubview_(card_view)

    # Card subviews
    lbl_title = AppKit.NSTextField.labelWithString_("")
    lbl_title.setFrame_(NSRect(NSPoint(18, card_h - 44), NSSize(card_w - 36, 30)))
    lbl_title.setFont_(AppKit.NSFont.boldSystemFontOfSize_(18))
    card_view.addSubview_(lbl_title)

    lbl_badges = AppKit.NSTextField.labelWithString_("")
    lbl_badges.setFrame_(NSRect(NSPoint(18, card_h - 70), NSSize(card_w - 36, 22)))
    lbl_badges.setFont_(AppKit.NSFont.systemFontOfSize_(12))
    card_view.addSubview_(lbl_badges)

    # Lore / Description scroll
    desc_scroll = AppKit.NSScrollView.alloc().initWithFrame_(NSRect(NSPoint(18, card_h - 220), NSSize(card_w - 36, 140)))
    desc_scroll.setHasVerticalScroller_(True)
    desc_scroll.setBorderType_(AppKit.NSNoBorder)
    desc_scroll.setDrawsBackground_(False)

    desc_text = AppKit.NSTextView.alloc().initWithFrame_(desc_scroll.contentRect())
    desc_text.setEditable_(False)
    desc_text.setSelectable_(True)
    desc_text.setDrawsBackground_(False)
    desc_text.setFont_(AppKit.NSFont.systemFontOfSize_(12.5))
    desc_scroll.setDocumentView_(desc_text)
    card_view.addSubview_(desc_scroll)

    # Abilities title & list
    lbl_ab_hdr = AppKit.NSTextField.labelWithString_("✨ Special Abilities & Stunts:")
    lbl_ab_hdr.setFrame_(NSRect(NSPoint(18, card_h - 250), NSSize(card_w - 36, 20)))
    lbl_ab_hdr.setFont_(AppKit.NSFont.boldSystemFontOfSize_(12.5))
    card_view.addSubview_(lbl_ab_hdr)

    lbl_abilities = AppKit.NSTextField.labelWithString_("")
    lbl_abilities.setFrame_(NSRect(NSPoint(18, 16), NSSize(card_w - 36, card_h - 275)))
    lbl_abilities.setFont_(AppKit.NSFont.systemFontOfSize_(12))
    card_view.addSubview_(lbl_abilities)

    # 4. Helper closures for filtering and card updates
    def update_card():
        row = table_view.selectedRow()
        if 0 <= row < len(src.items):
            s = src.items[row]
            is_active = (s["id"] == engine.character.skin_id)
            active_badge = " • [Active Companion]" if is_active else ""
            flight_badge = "✈️ Can Fly" if s.get("canFly") else "🐾 Ground Pet"
            cat_badge = s.get("category", "General").capitalize()

            lbl_title.setStringValue_(s.get("name", s["id"]))
            lbl_badges.setStringValue_(f"Category: {cat_badge}  |  {flight_badge}{active_badge}")
            desc_text.setString_(s.get("description", "No description available."))

            abs_list = s.get("abilities", [])
            if abs_list:
                formatted_abs = "\n".join(f"  • {a.replace('_', ' ').title()}" for a in abs_list)
            else:
                formatted_abs = "  • Autonomous Wandering & Pouncing"
            lbl_abilities.setStringValue_(formatted_abs)

    def filter_list():
        query = str(search_field.stringValue()).strip().lower()
        sel_seg = seg.selectedSegment()
        cat_filter = categories[sel_seg] if 0 <= sel_seg < len(categories) else "All"

        filtered: List[Dict[str, Any]] = []
        for s in all_skins:
            s_name = s.get("name", s["id"]).lower()
            s_cat = s.get("category", "general").capitalize()
            s_desc = s.get("description", "").lower()
            s_abs = " ".join(s.get("abilities", [])).lower()

            if cat_filter != "All" and s_cat != cat_filter:
                continue
            if query and (query not in s_name and query not in s_desc and query not in s_abs):
                continue
            filtered.append(s)

        src.items = filtered
        table_view.reloadData()
        if filtered:
            table_view.selectRowIndexes_byExtendingSelection_(AppKit.NSIndexSet.indexSetWithIndex_(0), False)
            update_card()

    def apply_selection():
        row = table_view.selectedRow()
        if 0 <= row < len(src.items):
            target_id = src.items[row]["id"]
            engine.switch_skin(target_id)
            engine.window.queue_draw()
        win.close()
        if win in _active_dialogs:
            _active_dialogs.remove(win)

    target._filter_cb = filter_list
    target._update_card_cb = update_card
    target._apply_cb = apply_selection

    # 5. Bottom Buttons
    btn_close = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(win_w - 260, 18), NSSize(90, 32)))
    btn_close.setTitle_("Close")
    btn_close.setBezelStyle_(AppKit.NSBezelStyleRounded)
    btn_close.setTarget_(target)
    btn_close.setAction_("onClose:")
    content.addSubview_(btn_close)

    btn_apply = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(win_w - 156, 18), NSSize(136, 32)))
    btn_apply.setTitle_("Select Companion")
    btn_apply.setBezelStyle_(AppKit.NSBezelStyleRounded)
    btn_apply.setKeyEquivalent_("\r")
    btn_apply.setTarget_(target)
    btn_apply.setAction_("onApply:")
    content.addSubview_(btn_apply)

    # Initial selection: highlight current character
    initial_idx = 0
    cur_id = engine.character.skin_id
    for i, s in enumerate(filtered_skins):
        if s["id"] == cur_id:
            initial_idx = i
            break
    table_view.selectRowIndexes_byExtendingSelection_(AppKit.NSIndexSet.indexSetWithIndex_(initial_idx), False)
    update_card()

    win.makeKeyAndOrderFront_(None)


# ============================================================================
# Modern Preferences Dialog
# ============================================================================

def show_macos_settings_dialog(engine: Any, parent=None) -> None:
    """Show tabbed, modern preferences dialog."""
    cfg = engine.config
    win_w, win_h = 520, 400

    style = (
        AppKit.NSWindowStyleMaskTitled |
        AppKit.NSWindowStyleMaskClosable
    )
    frame = NSRect(NSPoint(240, 240), NSSize(win_w, win_h))
    win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, style, AppKit.NSBackingStoreBuffered, False
    )
    win.setTitle_("Buddy Preferences")
    win.center()
    _active_dialogs.append(win)

    content = win.contentView()
    tabs = AppKit.NSTabView.alloc().initWithFrame_(NSRect(NSPoint(16, 64), NSSize(win_w - 32, win_h - 84)))

    target = SettingsDialogTarget.alloc().init()
    target._win = win
    _active_dialogs.append(target)

    # --- TAB 1: General ---
    tab1 = AppKit.NSTabViewItem.alloc().initWithIdentifier_("general")
    tab1.setLabel_("General")
    v1 = AppKit.NSView.alloc().initWithFrame_(tabs.contentRect())

    # Default character popup
    lbl_skin = AppKit.NSTextField.labelWithString_("Default Character:")
    lbl_skin.setFrame_(NSRect(NSPoint(20, 220), NSSize(140, 24)))
    v1.addSubview_(lbl_skin)

    skin_popup = AppKit.NSPopUpButton.alloc().initWithFrame_pullsDown_(NSRect(NSPoint(160, 218), NSSize(220, 26)), False)
    skins = skin_manager.get_available_skins()
    for s in skins:
        skin_popup.addItemWithTitle_(s.get("name", s["id"]))
    cur_id = cfg.get("skin", "thor")
    for i, s in enumerate(skins):
        if s["id"] == cur_id:
            skin_popup.selectItemAtIndex_(i)
            break
    v1.addSubview_(skin_popup)

    # Scale slider with dynamic label
    cur_scale = float(cfg.get("scale", 1.0))
    lbl_scale = AppKit.NSTextField.labelWithString_(f"Scale: {int(cur_scale * 100)}%")
    lbl_scale.setFrame_(NSRect(NSPoint(20, 170), NSSize(130, 24)))
    v1.addSubview_(lbl_scale)

    scale_slider = AppKit.NSSlider.alloc().initWithFrame_(NSRect(NSPoint(160, 170), NSSize(220, 24)))
    scale_slider.setMinValue_(0.5)
    scale_slider.setMaxValue_(2.0)
    scale_slider.setDoubleValue_(cur_scale)
    scale_slider.setTarget_(target)
    scale_slider.setAction_("onScaleChange:")
    target._lbl_scale = lbl_scale
    v1.addSubview_(scale_slider)

    # Volume slider with dynamic label
    cur_vol = float(cfg.get("sound_volume", 0.7))
    lbl_vol = AppKit.NSTextField.labelWithString_(f"Volume: {int(cur_vol * 100)}%")
    lbl_vol.setFrame_(NSRect(NSPoint(20, 120), NSSize(130, 24)))
    v1.addSubview_(lbl_vol)

    vol_slider = AppKit.NSSlider.alloc().initWithFrame_(NSRect(NSPoint(160, 120), NSSize(220, 24)))
    vol_slider.setMinValue_(0.0)
    vol_slider.setMaxValue_(1.0)
    vol_slider.setDoubleValue_(cur_vol)
    vol_slider.setTarget_(target)
    vol_slider.setAction_("onVolChange:")
    target._lbl_vol = lbl_vol
    v1.addSubview_(vol_slider)

    # Autostart checkbox
    autostart_mgr = MacOSAutostart()
    chk_autostart = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(20, 60), NSSize(360, 24)))
    chk_autostart.setButtonType_(AppKit.NSButtonTypeSwitch)
    chk_autostart.setTitle_("Start Buddy automatically on login (LaunchAgent)")
    chk_autostart.setState_(1 if autostart_mgr.is_enabled() else 0)
    v1.addSubview_(chk_autostart)

    tab1.setView_(v1)
    tabs.addTabViewItem_(tab1)

    # --- TAB 2: Appearance & Effects ---
    tab2 = AppKit.NSTabViewItem.alloc().initWithIdentifier_("effects")
    tab2.setLabel_("Effects & Performance")
    v2 = AppKit.NSView.alloc().initWithFrame_(tabs.contentRect())

    chk_particles = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(20, 210), NSSize(360, 24)))
    chk_particles.setButtonType_(AppKit.NSButtonTypeSwitch)
    chk_particles.setTitle_("Enable Particles & Magic Sparks")
    chk_particles.setState_(1 if cfg.get("particles_enabled", True) else 0)
    v2.addSubview_(chk_particles)

    chk_shake = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(20, 160), NSSize(360, 24)))
    chk_shake.setButtonType_(AppKit.NSButtonTypeSwitch)
    chk_shake.setTitle_("Enable Screen Shake on Impact")
    chk_shake.setState_(1 if cfg.get("screen_shake_enabled", True) else 0)
    v2.addSubview_(chk_shake)

    chk_power = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(20, 110), NSSize(360, 24)))
    chk_power.setButtonType_(AppKit.NSButtonTypeSwitch)
    chk_power.setTitle_("Low Power Mode (30 FPS Energy Saving)")
    chk_power.setState_(1 if cfg.get("low_power_mode", False) else 0)
    v2.addSubview_(chk_power)

    tab2.setView_(v2)
    tabs.addTabViewItem_(tab2)

    content.addSubview_(tabs)

    # Action context
    target._ctx = {
        "engine": engine,
        "skin_popup": skin_popup,
        "skins": skins,
        "scale_slider": scale_slider,
        "vol_slider": vol_slider,
        "chk_autostart": chk_autostart,
        "autostart_mgr": autostart_mgr,
        "chk_particles": chk_particles,
        "chk_shake": chk_shake,
        "chk_power": chk_power
    }

    # Bottom Buttons
    btn_cancel = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(win_w - 220, 16), NSSize(90, 32)))
    btn_cancel.setTitle_("Cancel")
    btn_cancel.setBezelStyle_(AppKit.NSBezelStyleRounded)
    btn_cancel.setTarget_(target)
    btn_cancel.setAction_("onCancel:")
    content.addSubview_(btn_cancel)

    btn_save = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(win_w - 120, 16), NSSize(104, 32)))
    btn_save.setTitle_("Save & Apply")
    btn_save.setBezelStyle_(AppKit.NSBezelStyleRounded)
    btn_save.setKeyEquivalent_("\r")
    btn_save.setTarget_(target)
    btn_save.setAction_("onSave:")
    content.addSubview_(btn_save)

    win.makeKeyAndOrderFront_(None)


# ============================================================================
# Productivity Dashboard
# ============================================================================

def show_macos_stats_dialog(engine: Any, parent=None) -> None:
    """Show native macOS Pomodoro and Focus productivity statistics dashboard."""
    stats = PomodoroStats()
    summary = stats.get_summary()

    today_mins = stats.sessions_today * 25.0
    h = int(today_mins // 60)
    m = int(today_mins % 60)
    today_str = f"{h}h {m}m" if h > 0 else f"{m}m"

    win_w, win_h = 440, 340
    style = (
        AppKit.NSWindowStyleMaskTitled |
        AppKit.NSWindowStyleMaskClosable
    )
    frame = NSRect(NSPoint(260, 260), NSSize(win_w, win_h))
    win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, style, AppKit.NSBackingStoreBuffered, False
    )
    win.setTitle_("Buddy 2.0 — Productivity Dashboard")
    win.center()
    _active_dialogs.append(win)

    content = win.contentView()

    target = StatsDialogTarget.alloc().init()
    target._win = win
    _active_dialogs.append(target)

    # Header
    lbl_hdr = AppKit.NSTextField.labelWithString_("📊 Focus & Productivity Metrics")
    lbl_hdr.setFrame_(NSRect(NSPoint(24, win_h - 48), NSSize(win_w - 48, 26)))
    lbl_hdr.setFont_(AppKit.NSFont.boldSystemFontOfSize_(16))
    content.addSubview_(lbl_hdr)

    # Stat Cards
    stat_items = [
        ("Today's Focused Time:", today_str),
        ("Completed Sessions Today:", f"{stats.sessions_today} cycles (25m each)"),
        ("Sessions Completed This Week:", f"{stats.sessions_this_week} cycles"),
        ("Current Consecutive Streak:", f"{stats.streak_days} days 🔥"),
        ("Lifetime Focus Logged:", f"{summary.get('total_focus_hours', 0)} hours")
    ]

    y = win_h - 96
    for title, val in stat_items:
        t_lbl = AppKit.NSTextField.labelWithString_(title)
        t_lbl.setFrame_(NSRect(NSPoint(28, y), NSSize(220, 22)))
        t_lbl.setFont_(AppKit.NSFont.systemFontOfSize_(13))
        content.addSubview_(t_lbl)

        v_lbl = AppKit.NSTextField.labelWithString_(val)
        v_lbl.setFrame_(NSRect(NSPoint(250, y), NSSize(160, 22)))
        v_lbl.setFont_(AppKit.NSFont.boldSystemFontOfSize_(13))
        content.addSubview_(v_lbl)
        y -= 36

    btn_ok = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(win_w - 110, 18), NSSize(90, 32)))
    btn_ok.setTitle_("Close")
    btn_ok.setBezelStyle_(AppKit.NSBezelStyleRounded)
    btn_ok.setKeyEquivalent_("\r")
    btn_ok.setTarget_(target)
    btn_ok.setAction_("onClose:")
    content.addSubview_(btn_ok)

    win.makeKeyAndOrderFront_(None)
