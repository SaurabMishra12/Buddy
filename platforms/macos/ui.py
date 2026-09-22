"""Classic native Apple macOS UI dialogs and popup context menus using AppKit."""

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
    local_targets: List[Any] = []

    def add_item(title: str, cb=None, parent_menu=menu):
        item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, None, "")
        if cb:
            target = MenuActionTarget.alloc().init()
            target.callback = cb
            local_targets.append(target)
            _active_menu_targets.append(target)
            item.setTarget_(target)
            item.setAction_("onAction:")
        parent_menu.addItem_(item)
        return item

    # 1. Signature Move
    add_item("⚡ Perform Signature Move", lambda _: engine.trigger_signature_ability())
    add_item("➡️ Next Character (Scroll Wheel / Middle-Click)", lambda _: engine.next_skin())
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
        ab_sub = add_item("✨ Abilities & Stunts")
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
        f"{'✓ ' if engine.click_through else '   '}Click-Through Mode (Ghost)",
        lambda _: engine.toggle_click_through()
    )
    add_item(
        f"{'✓ ' if not engine.audio.enabled else '   '}Quiet Mode (Mute)",
        lambda _: _toggle_sound(engine, not engine.audio.enabled)
    )

    # Scale submenu
    scale_sub = add_item("🔍 Companion Scale")
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

    menu._retained_targets = local_targets

    ns_event = getattr(event, "ns_event", None)
    if ns_event and hasattr(engine.window, "view"):
        AppKit.NSMenu.popUpContextMenu_withEvent_forView_(menu, ns_event, engine.window.view)


# ============================================================================
# Target Handlers
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
# Classic Apple Character Gallery Dialog
# ============================================================================

def show_macos_skin_selector(engine: Any, parent=None) -> None:
    """Show classic Apple design native Character Skin Gallery."""
    AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    win_w, win_h = 740, 520
    style = (
        AppKit.NSWindowStyleMaskTitled |
        AppKit.NSWindowStyleMaskClosable |
        AppKit.NSWindowStyleMaskMiniaturizable
    )
    frame = NSRect(NSPoint(200, 200), NSSize(win_w, win_h))
    win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, style, AppKit.NSBackingStoreBuffered, False
    )
    win.setTitle_("Buddy Companions — Character Gallery")
    win.center()
    _active_dialogs.append(win)

    content = win.contentView()

    # Classic Apple Frosted Glass / Vibrancy Backdrop
    backdrop = AppKit.NSVisualEffectView.alloc().initWithFrame_(content.bounds())
    backdrop.setMaterial_(AppKit.NSVisualEffectMaterialUnderWindowBackground)
    backdrop.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
    backdrop.setState_(AppKit.NSVisualEffectStateActive)
    backdrop.setAutoresizingMask_(AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable)
    content.addSubview_(backdrop)

    all_skins = skin_manager.get_available_skins()
    filtered_skins: List[Dict[str, Any]] = list(all_skins)

    target = GalleryDialogTarget.alloc().init()
    target._win = win
    _active_dialogs.append(target)

    # 1. Header with Classic Apple Typography
    lbl_hdr = AppKit.NSTextField.labelWithString_("Companion Gallery")
    lbl_hdr.setFrame_(NSRect(NSPoint(24, win_h - 44), NSSize(300, 26)))
    lbl_hdr.setFont_(AppKit.NSFont.systemFontOfSize_weight_(19.0, AppKit.NSFontWeightBold))
    lbl_hdr.setTextColor_(AppKit.NSColor.labelColor())
    backdrop.addSubview_(lbl_hdr)

    lbl_sub = AppKit.NSTextField.labelWithString_("Choose an animated desktop pet with unique physics and abilities.")
    lbl_sub.setFrame_(NSRect(NSPoint(24, win_h - 66), NSSize(420, 20)))
    lbl_sub.setFont_(AppKit.NSFont.systemFontOfSize_weight_(12.0, AppKit.NSFontWeightRegular))
    lbl_sub.setTextColor_(AppKit.NSColor.secondaryLabelColor())
    backdrop.addSubview_(lbl_sub)

    # 2. Controls Bar: Search Field + Category Segmented Control
    search_field = AppKit.NSSearchField.alloc().initWithFrame_(NSRect(NSPoint(24, win_h - 104), NSSize(230, 28)))
    search_field.setPlaceholderString_("Search companions...")
    search_field.setFont_(AppKit.NSFont.systemFontOfSize_(12.5))
    search_field.setTarget_(target)
    search_field.setAction_("onSearchChange:")
    backdrop.addSubview_(search_field)

    categories = ["All", "Heroes", "Animals", "Fantasy", "Sci-Fi", "Cute"]
    seg = AppKit.NSSegmentedControl.alloc().initWithFrame_(NSRect(NSPoint(268, win_h - 104), NSSize(win_w - 292, 28)))
    seg.setSegmentCount_(len(categories))
    seg.setSegmentStyle_(AppKit.NSSegmentStyleTexturedRounded)
    for i, cat in enumerate(categories):
        seg.setLabel_forSegment_(cat, i)
        seg.setWidth_forSegment_(0, i)
    seg.setSelectedSegment_(0)
    seg.setTarget_(target)
    seg.setAction_("onCategoryChange:")
    backdrop.addSubview_(seg)

    # 3. Left Side: Scrollable Table View
    table_w = 230
    scroll_h = win_h - 176
    scroll = AppKit.NSScrollView.alloc().initWithFrame_(NSRect(NSPoint(24, 60), NSSize(table_w, scroll_h)))
    scroll.setHasVerticalScroller_(True)
    scroll.setBorderType_(AppKit.NSBezelBorder)

    table_view = AppKit.NSTableView.alloc().initWithFrame_(scroll.contentView().bounds())
    col = AppKit.NSTableColumn.alloc().initWithIdentifier_("companion")
    col.setWidth_(table_w - 20)
    col.setTitle_("Companions (22)")
    table_view.addTableColumn_(col)
    table_view.setHeaderView_(None)
    table_view.setRowHeight_(30.0)
    table_view.setSelectionHighlightStyle_(AppKit.NSTableViewSelectionHighlightStyleRegular)

    src = GalleryTableSource.alloc().init()
    src.items = filtered_skins
    _active_dialogs.append(src)
    table_view.setDataSource_(src)
    table_view.setTarget_(target)
    table_view.setAction_("onTableSelect:")
    table_view.setDoubleAction_("onTableDoubleClick:")
    scroll.setDocumentView_(table_view)
    backdrop.addSubview_(scroll)

    # 4. Right Side: Character Detail Card
    card_x = table_w + 38
    card_w = win_w - card_x - 24
    card_h = scroll_h

    card_view = AppKit.NSBox.alloc().initWithFrame_(NSRect(NSPoint(card_x, 60), NSSize(card_w, card_h)))
    card_view.setTitlePosition_(AppKit.NSNoTitle)
    card_view.setBoxType_(AppKit.NSBoxCustom)
    card_view.setFillColor_(AppKit.NSColor.controlBackgroundColor())
    card_view.setBorderColor_(AppKit.NSColor.separatorColor())
    card_view.setBorderWidth_(1.0)
    card_view.setCornerRadius_(10.0)
    backdrop.addSubview_(card_view)

    lbl_title = AppKit.NSTextField.labelWithString_("")
    lbl_title.setFrame_(NSRect(NSPoint(20, card_h - 44), NSSize(card_w - 40, 28)))
    lbl_title.setFont_(AppKit.NSFont.systemFontOfSize_weight_(20.0, AppKit.NSFontWeightBold))
    lbl_title.setTextColor_(AppKit.NSColor.labelColor())
    card_view.addSubview_(lbl_title)

    lbl_badges = AppKit.NSTextField.labelWithString_("")
    lbl_badges.setFrame_(NSRect(NSPoint(20, card_h - 70), NSSize(card_w - 40, 20)))
    lbl_badges.setFont_(AppKit.NSFont.systemFontOfSize_weight_(12.0, AppKit.NSFontWeightMedium))
    lbl_badges.setTextColor_(AppKit.NSColor.secondaryLabelColor())
    card_view.addSubview_(lbl_badges)

    # Description scroll view
    desc_scroll = AppKit.NSScrollView.alloc().initWithFrame_(NSRect(NSPoint(20, card_h - 200), NSSize(card_w - 40, 120)))
    desc_scroll.setHasVerticalScroller_(True)
    desc_scroll.setBorderType_(AppKit.NSNoBorder)
    desc_scroll.setDrawsBackground_(False)

    desc_text = AppKit.NSTextView.alloc().initWithFrame_(desc_scroll.contentView().bounds())
    desc_text.setEditable_(False)
    desc_text.setSelectable_(True)
    desc_text.setDrawsBackground_(False)
    desc_text.setFont_(AppKit.NSFont.systemFontOfSize_(12.5))
    desc_text.setTextColor_(AppKit.NSColor.labelColor())
    desc_scroll.setDocumentView_(desc_text)
    card_view.addSubview_(desc_scroll)

    # Abilities Header
    lbl_ab_hdr = AppKit.NSTextField.labelWithString_("✨ Special Moves & Acrobatics:")
    lbl_ab_hdr.setFrame_(NSRect(NSPoint(20, card_h - 228), NSSize(card_w - 40, 20)))
    lbl_ab_hdr.setFont_(AppKit.NSFont.systemFontOfSize_weight_(12.5, AppKit.NSFontWeightSemibold))
    lbl_ab_hdr.setTextColor_(AppKit.NSColor.labelColor())
    card_view.addSubview_(lbl_ab_hdr)

    lbl_abilities = AppKit.NSTextField.labelWithString_("")
    lbl_abilities.setFrame_(NSRect(NSPoint(20, 16), NSSize(card_w - 40, card_h - 250)))
    lbl_abilities.setFont_(AppKit.NSFont.systemFontOfSize_(12.0))
    lbl_abilities.setTextColor_(AppKit.NSColor.secondaryLabelColor())
    card_view.addSubview_(lbl_abilities)

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
    btn_close = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(win_w - 256, 16), NSSize(90, 32)))
    btn_close.setTitle_("Close")
    btn_close.setBezelStyle_(AppKit.NSBezelStyleRounded)
    btn_close.setKeyEquivalent_("\x1b")
    btn_close.setTarget_(target)
    btn_close.setAction_("onClose:")
    backdrop.addSubview_(btn_close)

    btn_apply = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(win_w - 156, 16), NSSize(136, 32)))
    btn_apply.setTitle_("Select Companion")
    btn_apply.setBezelStyle_(AppKit.NSBezelStyleRounded)
    btn_apply.setKeyEquivalent_("\r")
    btn_apply.setTarget_(target)
    btn_apply.setAction_("onApply:")
    backdrop.addSubview_(btn_apply)

    # Initial selection
    initial_idx = 0
    cur_id = engine.character.skin_id
    for i, s in enumerate(filtered_skins):
        if s["id"] == cur_id:
            initial_idx = i
            break
    table_view.selectRowIndexes_byExtendingSelection_(AppKit.NSIndexSet.indexSetWithIndex_(initial_idx), False)
    update_card()

    win.makeKeyAndOrderFront_(None)
    win.orderFrontRegardless()


# ============================================================================
# Classic Apple Preferences Dialog
# ============================================================================

def show_macos_settings_dialog(engine: Any, parent=None) -> None:
    """Show classic Apple design native Preferences dialog."""
    AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    cfg = engine.config
    win_w, win_h = 520, 420

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

    backdrop = AppKit.NSVisualEffectView.alloc().initWithFrame_(content.bounds())
    backdrop.setMaterial_(AppKit.NSVisualEffectMaterialUnderWindowBackground)
    backdrop.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
    backdrop.setState_(AppKit.NSVisualEffectStateActive)
    backdrop.setAutoresizingMask_(AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable)
    content.addSubview_(backdrop)

    # Header
    lbl_hdr = AppKit.NSTextField.labelWithString_("Preferences")
    lbl_hdr.setFrame_(NSRect(NSPoint(24, win_h - 40), NSSize(200, 24)))
    lbl_hdr.setFont_(AppKit.NSFont.systemFontOfSize_weight_(18.0, AppKit.NSFontWeightBold))
    lbl_hdr.setTextColor_(AppKit.NSColor.labelColor())
    backdrop.addSubview_(lbl_hdr)

    tabs = AppKit.NSTabView.alloc().initWithFrame_(NSRect(NSPoint(16, 56), NSSize(win_w - 32, win_h - 100)))

    target = SettingsDialogTarget.alloc().init()
    target._win = win
    _active_dialogs.append(target)

    # --- TAB 1: General ---
    tab1 = AppKit.NSTabViewItem.alloc().initWithIdentifier_("general")
    tab1.setLabel_("General")
    v1 = AppKit.NSView.alloc().initWithFrame_(tabs.contentRect())

    # Default character popup
    lbl_skin = AppKit.NSTextField.labelWithString_("Default Companion:")
    lbl_skin.setFrame_(NSRect(NSPoint(20, 230), NSSize(150, 24)))
    lbl_skin.setFont_(AppKit.NSFont.systemFontOfSize_weight_(13.0, AppKit.NSFontWeightMedium))
    v1.addSubview_(lbl_skin)

    skin_popup = AppKit.NSPopUpButton.alloc().initWithFrame_pullsDown_(NSRect(NSPoint(180, 228), NSSize(230, 26)), False)
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
    cur_scale = float(cfg.get("scale", 1.0))
    lbl_scale = AppKit.NSTextField.labelWithString_(f"Scale: {int(cur_scale * 100)}%")
    lbl_scale.setFrame_(NSRect(NSPoint(20, 175), NSSize(150, 24)))
    lbl_scale.setFont_(AppKit.NSFont.systemFontOfSize_weight_(13.0, AppKit.NSFontWeightMedium))
    v1.addSubview_(lbl_scale)

    scale_slider = AppKit.NSSlider.alloc().initWithFrame_(NSRect(NSPoint(180, 175), NSSize(230, 24)))
    scale_slider.setMinValue_(0.5)
    scale_slider.setMaxValue_(2.0)
    scale_slider.setDoubleValue_(cur_scale)
    scale_slider.setTarget_(target)
    scale_slider.setAction_("onScaleChange:")
    target._lbl_scale = lbl_scale
    v1.addSubview_(scale_slider)

    # Volume slider
    cur_vol = float(cfg.get("sound_volume", 0.7))
    lbl_vol = AppKit.NSTextField.labelWithString_(f"Volume: {int(cur_vol * 100)}%")
    lbl_vol.setFrame_(NSRect(NSPoint(20, 120), NSSize(150, 24)))
    lbl_vol.setFont_(AppKit.NSFont.systemFontOfSize_weight_(13.0, AppKit.NSFontWeightMedium))
    v1.addSubview_(lbl_vol)

    vol_slider = AppKit.NSSlider.alloc().initWithFrame_(NSRect(NSPoint(180, 120), NSSize(230, 24)))
    vol_slider.setMinValue_(0.0)
    vol_slider.setMaxValue_(1.0)
    vol_slider.setDoubleValue_(cur_vol)
    vol_slider.setTarget_(target)
    vol_slider.setAction_("onVolChange:")
    target._lbl_vol = lbl_vol
    v1.addSubview_(vol_slider)

    # Autostart checkbox
    autostart_mgr = MacOSAutostart()
    chk_autostart = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(20, 50), NSSize(400, 24)))
    chk_autostart.setButtonType_(AppKit.NSButtonTypeSwitch)
    chk_autostart.setTitle_("Start Buddy automatically on login (LaunchAgent)")
    chk_autostart.setFont_(AppKit.NSFont.systemFontOfSize_(12.5))
    chk_autostart.setState_(1 if autostart_mgr.is_enabled() else 0)
    v1.addSubview_(chk_autostart)

    tab1.setView_(v1)
    tabs.addTabViewItem_(tab1)

    # --- TAB 2: Effects & Performance ---
    tab2 = AppKit.NSTabViewItem.alloc().initWithIdentifier_("effects")
    tab2.setLabel_("Effects & Performance")
    v2 = AppKit.NSView.alloc().initWithFrame_(tabs.contentRect())

    chk_particles = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(20, 220), NSSize(400, 24)))
    chk_particles.setButtonType_(AppKit.NSButtonTypeSwitch)
    chk_particles.setTitle_("Enable Particle Sparks & Magic Dust")
    chk_particles.setFont_(AppKit.NSFont.systemFontOfSize_(12.5))
    chk_particles.setState_(1 if cfg.get("particles_enabled", True) else 0)
    v2.addSubview_(chk_particles)

    chk_shake = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(20, 170), NSSize(400, 24)))
    chk_shake.setButtonType_(AppKit.NSButtonTypeSwitch)
    chk_shake.setTitle_("Enable Screen Shake on Powerful Impacts")
    chk_shake.setFont_(AppKit.NSFont.systemFontOfSize_(12.5))
    chk_shake.setState_(1 if cfg.get("screen_shake_enabled", True) else 0)
    v2.addSubview_(chk_shake)

    chk_power = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(20, 120), NSSize(400, 24)))
    chk_power.setButtonType_(AppKit.NSButtonTypeSwitch)
    chk_power.setTitle_("Low Power Mode (Cap at 30 FPS for Battery Saving)")
    chk_power.setFont_(AppKit.NSFont.systemFontOfSize_(12.5))
    chk_power.setState_(1 if cfg.get("low_power_mode", False) else 0)
    v2.addSubview_(chk_power)

    tab2.setView_(v2)
    tabs.addTabViewItem_(tab2)

    backdrop.addSubview_(tabs)

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
    btn_cancel = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(win_w - 230, 16), NSSize(96, 32)))
    btn_cancel.setTitle_("Cancel")
    btn_cancel.setBezelStyle_(AppKit.NSBezelStyleRounded)
    btn_cancel.setKeyEquivalent_("\x1b")
    btn_cancel.setTarget_(target)
    btn_cancel.setAction_("onCancel:")
    backdrop.addSubview_(btn_cancel)

    btn_save = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(win_w - 124, 16), NSSize(108, 32)))
    btn_save.setTitle_("Save & Apply")
    btn_save.setBezelStyle_(AppKit.NSBezelStyleRounded)
    btn_save.setKeyEquivalent_("\r")
    btn_save.setTarget_(target)
    btn_save.setAction_("onSave:")
    backdrop.addSubview_(btn_save)

    win.makeKeyAndOrderFront_(None)
    win.orderFrontRegardless()


# ============================================================================
# Classic Apple Productivity Dashboard
# ============================================================================

def show_macos_stats_dialog(engine: Any, parent=None) -> None:
    """Show classic Apple HUD dashboard for Pomodoro productivity stats."""
    AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    stats = PomodoroStats()
    summary = stats.get_summary()

    win_w, win_h = 440, 360
    style = (
        AppKit.NSWindowStyleMaskTitled |
        AppKit.NSWindowStyleMaskClosable
    )
    frame = NSRect(NSPoint(260, 260), NSSize(win_w, win_h))
    win = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, style, AppKit.NSBackingStoreBuffered, False
    )
    win.setTitle_("Productivity Statistics")
    win.center()
    _active_dialogs.append(win)

    content = win.contentView()

    backdrop = AppKit.NSVisualEffectView.alloc().initWithFrame_(content.bounds())
    backdrop.setMaterial_(AppKit.NSVisualEffectMaterialUnderWindowBackground)
    backdrop.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
    backdrop.setState_(AppKit.NSVisualEffectStateActive)
    backdrop.setAutoresizingMask_(AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable)
    content.addSubview_(backdrop)

    target = StatsDialogTarget.alloc().init()
    target._win = win
    _active_dialogs.append(target)

    # Header
    lbl_hdr = AppKit.NSTextField.labelWithString_("Focus Dashboard")
    lbl_hdr.setFrame_(NSRect(NSPoint(24, win_h - 44), NSSize(300, 26)))
    lbl_hdr.setFont_(AppKit.NSFont.systemFontOfSize_weight_(19.0, AppKit.NSFontWeightBold))
    lbl_hdr.setTextColor_(AppKit.NSColor.labelColor())
    backdrop.addSubview_(lbl_hdr)

    lbl_sub = AppKit.NSTextField.labelWithString_("Pomodoro focus intervals and companion productivity metrics.")
    lbl_sub.setFrame_(NSRect(NSPoint(24, win_h - 66), NSSize(380, 20)))
    lbl_sub.setFont_(AppKit.NSFont.systemFontOfSize_weight_(12.0, AppKit.NSFontWeightRegular))
    lbl_sub.setTextColor_(AppKit.NSColor.secondaryLabelColor())
    backdrop.addSubview_(lbl_sub)

    # Metrics grid: 2x2
    today_mins = int(stats.sessions_today * 25.0)
    cards_data = [
        ("Today's Focus", f"{today_mins} min", 24, win_h - 180),
        ("Sessions Today", str(stats.sessions_today), 228, win_h - 180),
        ("Active Streak", f"{stats.streak_days} days 🔥", 24, win_h - 280),
        ("Lifetime Hours", f"{summary['total_focus_hours']} hrs", 228, win_h - 280),
    ]

    for title, val, cx, cy in cards_data:
        box = AppKit.NSBox.alloc().initWithFrame_(NSRect(NSPoint(cx, cy), NSSize(188, 88)))
        box.setTitlePosition_(AppKit.NSNoTitle)
        box.setBoxType_(AppKit.NSBoxCustom)
        box.setFillColor_(AppKit.NSColor.controlBackgroundColor())
        box.setBorderColor_(AppKit.NSColor.separatorColor())
        box.setBorderWidth_(1.0)
        box.setCornerRadius_(8.0)

        t_lbl = AppKit.NSTextField.labelWithString_(title)
        t_lbl.setFrame_(NSRect(NSPoint(14, 56), NSSize(160, 20)))
        t_lbl.setFont_(AppKit.NSFont.systemFontOfSize_weight_(11.5, AppKit.NSFontWeightMedium))
        t_lbl.setTextColor_(AppKit.NSColor.secondaryLabelColor())
        box.addSubview_(t_lbl)

        v_lbl = AppKit.NSTextField.labelWithString_(val)
        v_lbl.setFrame_(NSRect(NSPoint(14, 16), NSSize(160, 36)))
        v_lbl.setFont_(AppKit.NSFont.systemFontOfSize_weight_(24.0, AppKit.NSFontWeightBold))
        v_lbl.setTextColor_(AppKit.NSColor.labelColor())
        box.addSubview_(v_lbl)

        backdrop.addSubview_(box)

    btn_done = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(win_w - 120, 16), NSSize(96, 32)))
    btn_done.setTitle_("Done")
    btn_done.setBezelStyle_(AppKit.NSBezelStyleRounded)
    btn_done.setKeyEquivalent_("\r")
    btn_done.setTarget_(target)
    btn_done.setAction_("onClose:")
    backdrop.addSubview_(btn_done)

    win.makeKeyAndOrderFront_(None)
    win.orderFrontRegardless()
