"""Native macOS Menu Bar Status Item controller using AppKit NSStatusBar & NSMenu."""

import sys
from pathlib import Path
from typing import Any, Optional

import AppKit
import objc
from Foundation import NSObject, NSSize
from skins.manager import skin_manager
from pomodoro.manager import PomodoroState


class MenuController(NSObject):
    """Primary Objective-C action dispatcher for all menu bar items."""

    @objc.IBAction
    def onControlCenter_(self, sender):
        if hasattr(self, "_engine") and self._engine:
            self._engine.open_control_center()

    @objc.IBAction
    def onSwitchSkin_(self, sender):
        if not hasattr(self, "_engine") or not self._engine:
            return
        skin_id = str(sender.representedObject())
        dev_mode = self._engine.is_developer_mode() if hasattr(self._engine, "is_developer_mode") else self._engine.config.get("developer_mode", False)
        if skin_manager.is_archived(skin_id) and not dev_mode:
            print(f"[Menu Bar] Rejected switch to archived character '{skin_id}' because Developer Mode is OFF.")
            return
        self._engine.switch_skin(skin_id)
        if hasattr(self._engine.window, "queue_draw"):
            self._engine.window.queue_draw()
        if hasattr(self, "_bar") and self._bar:
            self._bar.update_skin_checkmarks(skin_id)

    @objc.IBAction
    def onAbility_(self, sender):
        if hasattr(self, "_engine") and self._engine:
            ab = str(sender.representedObject())
            self._engine.character.trigger_ability(
                ab, self._engine.cursor_x, self._engine.cursor_y,
                self._engine.particles, self._engine.audio
            )

    @objc.IBAction
    def onSignatureMove_(self, sender):
        if hasattr(self, "_engine") and self._engine:
            self._engine.trigger_signature_ability()

    @objc.IBAction
    def onNextSkin_(self, sender):
        if hasattr(self, "_engine") and self._engine:
            new_id = self._engine.next_skin()
            if hasattr(self, "_bar") and self._bar:
                self._bar.update_skin_checkmarks(new_id)

    @objc.IBAction
    def onSetCompanionMode_(self, sender):
        if hasattr(self, "_engine") and self._engine:
            mode = str(sender.representedObject())
            self._engine.set_mode(mode)
            if hasattr(self, "_bar") and self._bar:
                self._bar.update_mode_checkmarks(mode)

    @objc.IBAction
    def onPreferences_(self, sender):
        if hasattr(self, "_engine") and self._engine:
            AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            from platforms.macos.ui import show_macos_settings_dialog
            show_macos_settings_dialog(self._engine)

    @objc.IBAction
    def onSkinGallery_(self, sender):
        if hasattr(self, "_engine") and self._engine:
            AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            from platforms.macos.ui import show_macos_skin_selector
            show_macos_skin_selector(self._engine)

    @objc.IBAction
    def onStats_(self, sender):
        if hasattr(self, "_engine") and self._engine:
            AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            from platforms.macos.ui import show_macos_stats_dialog
            show_macos_stats_dialog(self._engine)

    @objc.IBAction
    def onToggleClickThrough_(self, sender):
        if hasattr(self, "_engine") and self._engine:
            val = self._engine.toggle_click_through()
            sender.setState_(AppKit.NSControlStateValueOn if val else AppKit.NSControlStateValueOff)

    @objc.IBAction
    def onToggleMute_(self, sender):
        if hasattr(self, "_engine") and self._engine:
            new_enabled = not self._engine.audio.enabled
            self._engine.audio.enabled = new_enabled
            self._engine.config.set("sound_enabled", new_enabled)
            sender.setState_(AppKit.NSControlStateValueOff if new_enabled else AppKit.NSControlStateValueOn)

    @objc.IBAction
    def onSetScale_(self, sender):
        if hasattr(self, "_engine") and self._engine:
            try:
                scale_val = float(sender.representedObject())
                self._engine.set_scale(scale_val)
                menu = sender.menu()
                if menu:
                    for it in menu.itemArray():
                        it.setState_(AppKit.NSControlStateValueOn if it == sender else AppKit.NSControlStateValueOff)
            except Exception as e:
                print(f"[Buddy Menu] Error setting scale: {e}", file=sys.stderr)

    @objc.IBAction
    def onPomodoroAction_(self, sender):
        if hasattr(self, "_engine") and self._engine:
            pomo = getattr(self._engine, "pomodoro", None)
            if not pomo:
                return
            act = str(sender.representedObject())
            if act == "start":
                pomo.start_work()
            elif act == "pause":
                pomo.pause()
            elif act == "resume":
                pomo.resume()
            elif act == "skip":
                pomo.skip()
            elif act == "reset":
                pomo.reset()
            if hasattr(self, "_bar") and self._bar:
                self._bar.update_pomodoro_label()

    @objc.IBAction
    def onHelp_(self, sender):
        if hasattr(self, "_bar") and self._bar:
            self._bar._show_help()

    @objc.IBAction
    def onQuit_(self, sender):
        AppKit.NSApplication.sharedApplication().terminate_(None)


class MacOSMenuBar:
    """Native macOS Status Item in Menu Bar with persistent target dispatch."""

    def __init__(self, engine: Any):
        self.engine = engine
        self.status_bar = AppKit.NSStatusBar.systemStatusBar()
        self.status_item = self.status_bar.statusItemWithLength_(AppKit.NSVariableStatusItemLength)

        # Persistent controller that lives as long as the status bar item
        self.controller = MenuController.alloc().init()
        self.controller._engine = self.engine
        self.controller._bar = self

        # Configure menu bar button with crisp native SF Symbol
        button = self.status_item.button()
        if button:
            button.setToolTip_("Buddy Desktop Companion")
            icon = None
            for sym_name in ("pawprint.fill", "sparkles", "bolt.fill"):
                try:
                    icon = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_(sym_name, "Buddy")
                    if icon:
                        break
                except Exception:
                    pass

            if icon:
                button.setImage_(icon)
            else:
                button.setTitle_("🐾")

        self.title_item = None
        self.skin_sub_item = None
        self.skin_menu = None
        self.mode_sub_item = None
        self.behavior_menu = None
        self.mode_items = {}
        self.pomo_sub_item = None
        self.scale_menu = None

        self._build_menu()

    def update_mode_checkmarks(self, mode: str) -> None:
        """Update Companion Behavior Mode checkmarks in Menu Bar."""
        if hasattr(self, "mode_items"):
            for m, it in self.mode_items.items():
                it.setState_(AppKit.NSControlStateValueOn if m == mode else AppKit.NSControlStateValueOff)
        if hasattr(self, "mode_sub_item") and self.mode_sub_item:
            self.mode_sub_item.setTitle_(f"🧭 Behavior Mode ({mode.capitalize()})")

    def _build_menu(self) -> None:
        menu = AppKit.NSMenu.alloc().init()
        menu.setAutoenablesItems_(False)

        # 1. Title Header
        cur_id = self.engine.character.skin_id
        char_name = cur_id.replace("_", " ").title()
        self.title_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"Buddy 2.0 — {char_name}", None, ""
        )
        self.title_item.setEnabled_(False)
        menu.addItem_(self.title_item)

        # 1b. Buddy Control Center
        cc_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "🎛️ Buddy Control Center...", "onControlCenter:", ","
        )
        cc_item.setTarget_(self.controller)
        menu.addItem_(cc_item)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # 2. Companion Behavior Mode
        cur_mode = getattr(self.engine, "mode", "static")
        self.mode_sub_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"🧭 Behavior Mode ({cur_mode.capitalize()})", None, ""
        )
        self.behavior_menu = AppKit.NSMenu.alloc().init()
        self.behavior_menu.setAutoenablesItems_(False)
        self.mode_items = {}

        mode_options = [
            ("📌 Desk Pet (Static — Stays Put Where Dropped)", "static"),
            ("🐾 Free Roam (Wanders Desktop Autonomously)", "roam"),
            ("⚡ Cursor Companion (Follows Cursor)", "follow"),
        ]
        for label, m in mode_options:
            it = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(label, "onSetCompanionMode:", "")
            it.setTarget_(self.controller)
            it.setRepresentedObject_(m)
            if cur_mode == m:
                it.setState_(AppKit.NSControlStateValueOn)
            self.behavior_menu.addItem_(it)
            self.mode_items[m] = it

        self.mode_sub_item.setSubmenu_(self.behavior_menu)
        menu.addItem_(self.mode_sub_item)

        # Signature Move
        sig_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "⚡ Perform Signature Move", "onSignatureMove:", ""
        )
        sig_item.setTarget_(self.controller)
        menu.addItem_(sig_item)

        # Next Skin
        next_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "➡️ Next Companion (Scroll Wheel)", "onNextSkin:", ""
        )
        next_item.setTarget_(self.controller)
        menu.addItem_(next_item)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # 3. Companion Selection Submenu (Categorized by Universe)
        self.skin_sub_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            f"🎭 Switch Companion ({char_name})", None, ""
        )
        self.skin_menu = AppKit.NSMenu.alloc().init()
        self.skin_menu.setAutoenablesItems_(False)

        dev_mode = self.engine.is_developer_mode() if hasattr(self.engine, "is_developer_mode") else self.engine.config.get("developer_mode", False)
        if not dev_mode:
            from skins.manager import ACTIVE_ROSTER
            for sid in ACTIVE_ROSTER:
                meta = skin_manager.get_metadata(sid) or {}
                s_name = meta.get("name", sid.replace("_", " ").title())
                flight = " ✈️" if meta.get("canFly") else ""
                it = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(f"{s_name}{flight}", "onSwitchSkin:", "")
                it.setTarget_(self.controller)
                it.setRepresentedObject_(sid)
                if sid == cur_id:
                    it.setState_(AppKit.NSControlStateValueOn)
                self.skin_menu.addItem_(it)
        else:
            categories_map = {
                "bleach": ("⚔️ Bleach Soul Reapers", []),
                "superhero": ("🦸 Superheroes", []),
                "animals": ("🐾 Pets & Animals", []),
                "fantasy": ("🔮 Fantasy & Magic", []),
                "sci-fi": ("🚀 Sci-Fi & Others", []),
                "cute": ("✨ Cute Companions", []),
            }
            for s in skin_manager.get_available_skins(include_archived=True):
                cat = s.get("category", "superhero").lower()
                if cat in categories_map:
                    categories_map[cat][1].append(s)
                else:
                    categories_map["sci-fi"][1].append(s)

            for cat_key, (cat_label, cat_skins) in categories_map.items():
                if not cat_skins:
                    continue
                cat_sub_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(cat_label, None, "")
                cat_menu = AppKit.NSMenu.alloc().init()
                cat_menu.setAutoenablesItems_(False)
                for s in cat_skins:
                    sid = s["id"]
                    s_name = s.get("name", sid)
                    flight = " ✈️" if s.get("canFly") else ""
                    it = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(f"{s_name}{flight}", "onSwitchSkin:", "")
                    it.setTarget_(self.controller)
                    it.setRepresentedObject_(sid)
                    if sid == cur_id:
                        it.setState_(AppKit.NSControlStateValueOn)
                    cat_menu.addItem_(it)
                cat_sub_item.setSubmenu_(cat_menu)
                self.skin_menu.addItem_(cat_sub_item)

        self.skin_sub_item.setSubmenu_(self.skin_menu)
        menu.addItem_(self.skin_sub_item)

        # 4. Pomodoro Submenu
        pomo = getattr(self.engine, "pomodoro", None)
        if pomo:
            self.pomo_sub_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                f"🍅 Pomodoro [{pomo.status_label}]", None, ""
            )
            pomo_menu = AppKit.NSMenu.alloc().init()
            pomo_menu.setAutoenablesItems_(False)

            for title, act in [
                ("▶ Start Focus Session (25 min)", "start"),
                ("⏸ Pause Focus Session", "pause"),
                ("▶ Resume Focus Session", "resume"),
                ("⏭ Skip to Next Interval", "skip"),
                ("⏹ Reset Timer", "reset"),
            ]:
                p_it = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, "onPomodoroAction:", "")
                p_it.setTarget_(self.controller)
                p_it.setRepresentedObject_(act)
                pomo_menu.addItem_(p_it)

            self.pomo_sub_item.setSubmenu_(pomo_menu)
            menu.addItem_(self.pomo_sub_item)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # 5. Companion Mode Submenu
        mode_sub_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("⚙️ Companion Mode", None, "")
        mode_menu = AppKit.NSMenu.alloc().init()
        mode_menu.setAutoenablesItems_(False)

        ct_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Click-Through Mode (Ghost)", "onToggleClickThrough:", ""
        )
        ct_item.setTarget_(self.controller)
        ct_item.setState_(AppKit.NSControlStateValueOn if self.engine.click_through else AppKit.NSControlStateValueOff)
        mode_menu.addItem_(ct_item)

        quiet_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quiet Mode (Mute)", "onToggleMute:", ""
        )
        quiet_item.setTarget_(self.controller)
        quiet_item.setState_(AppKit.NSControlStateValueOff if self.engine.audio.enabled else AppKit.NSControlStateValueOn)
        mode_menu.addItem_(quiet_item)

        # Scale submenu
        size_sub_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Pet Scale", None, "")
        self.scale_menu = AppKit.NSMenu.alloc().init()
        self.scale_menu.setAutoenablesItems_(False)
        cur_sc = getattr(self.engine.character, "scale", 1.0)
        for label, sc in [("Small (75%)", 0.75), ("Normal (100%)", 1.0), ("Large (135%)", 1.35), ("Giant (175%)", 1.75)]:
            s_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(label, "onSetScale:", "")
            s_item.setTarget_(self.controller)
            s_item.setRepresentedObject_(sc)
            if abs(cur_sc - sc) < 0.1:
                s_item.setState_(AppKit.NSControlStateValueOn)
            self.scale_menu.addItem_(s_item)
        size_sub_item.setSubmenu_(self.scale_menu)
        mode_menu.addItem_(size_sub_item)

        mode_sub_item.setSubmenu_(mode_menu)
        menu.addItem_(mode_sub_item)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # 6. Dialog Actions
        pref_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Preferences...", "onPreferences:", "")
        pref_item.setTarget_(self.controller)
        menu.addItem_(pref_item)

        gal_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Character Gallery...", "onSkinGallery:", "")
        gal_item.setTarget_(self.controller)
        menu.addItem_(gal_item)

        stats_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Productivity Statistics...", "onStats:", "")
        stats_item.setTarget_(self.controller)
        menu.addItem_(stats_item)

        help_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Help & Controls...", "onHelp:", "")
        help_item.setTarget_(self.controller)
        menu.addItem_(help_item)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # 7. Quit
        quit_item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit Buddy", "onQuit:", "")
        quit_item.setTarget_(self.controller)
        menu.addItem_(quit_item)

        self.status_item.setMenu_(menu)

    def update_skin_checkmarks(self, current_skin_id: str) -> None:
        """Update native checkmarks without recreating the menu."""
        char_name = current_skin_id.replace("_", " ").title()
        if self.title_item:
            self.title_item.setTitle_(f"Buddy 2.0 — {char_name}")
        if self.skin_sub_item:
            self.skin_sub_item.setTitle_(f"🎭 Switch Companion ({char_name})")
        if self.skin_menu:
            for it in self.skin_menu.itemArray():
                sid = str(it.representedObject())
                it.setState_(AppKit.NSControlStateValueOn if sid == current_skin_id else AppKit.NSControlStateValueOff)

    def update_pomodoro_label(self) -> None:
        pomo = getattr(self.engine, "pomodoro", None)
        if pomo and self.pomo_sub_item:
            self.pomo_sub_item.setTitle_(f"🍅 Pomodoro [{pomo.status_label}]")

    def _show_help(self) -> None:
        AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        alert = AppKit.NSAlert.alloc().init()
        alert.setMessageText_("Buddy 2.0 — Desktop Companion (macOS)")
        alert.setInformativeText_(
            "Controls:\n"
            "• Left Click & Drag: Pick up and navigate with Buddy\n"
            "• Double Click: Execute signature ability / acrobatic stunt\n"
            "• Right Click: Open companion menu & Pomodoro options\n"
            "• Option/Command Click: Click straight through Buddy to background apps\n"
            "• Scroll Wheel: Cycle characters\n\n"
            "CLI Commands:\n"
            "  buddy --skin [name]\n"
            "  buddy --pause / buddy --resume\n"
            "  buddy --settings / buddy --skins\n"
            "  buddy --pomodoro [start|pause|resume|reset]\n"
            "  buddy --quit"
        )
        alert.addButtonWithTitle_("OK")
        if hasattr(alert, "window") and alert.window():
            alert.window().setLevel_(AppKit.NSFloatingWindowLevel)
        alert.runModal()
