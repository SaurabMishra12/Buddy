"""Native macOS Menu Bar Status Item controller using AppKit NSStatusBar & NSMenu."""

import sys
from pathlib import Path
from typing import Any, Optional

import AppKit
from Foundation import NSObject, NSSize
from skins.manager import skin_manager
from pomodoro.manager import PomodoroState


class MenuActionTarget(NSObject):
    """Reusable Obj-C target for dispatching NSMenuItem callbacks."""

    def onAction_(self, sender):
        if hasattr(self, "callback") and self.callback:
            try:
                self.callback(sender)
            except Exception as e:
                import traceback
                print(f"[Buddy Menu] Error executing menu callback: {e}", file=sys.stderr)
                traceback.print_exc()


class MenuUpdateDelegate(NSObject):
    """Delegate called immediately before the menu opens to ensure fresh state."""

    def menuWillOpen_(self, menu):
        if hasattr(self, "_bar") and self._bar:
            try:
                self._bar.rebuild_menu_items(menu)
            except Exception as e:
                print(f"[Buddy Menu] Error in menuWillOpen: {e}", file=sys.stderr)


class MacOSMenuBar:
    """Native macOS Status Item in Menu Bar."""

    def __init__(self, engine: Any):
        self.engine = engine
        self.status_bar = AppKit.NSStatusBar.systemStatusBar()
        self.status_item = self.status_bar.statusItemWithLength_(AppKit.NSVariableStatusItemLength)

        # Persistent target retention pool to prevent garbage collection
        self._targets = []

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

        self.menu_delegate = MenuUpdateDelegate.alloc().init()
        self.menu_delegate._bar = self

        self.menu = AppKit.NSMenu.alloc().init()
        self.menu.setDelegate_(self.menu_delegate)
        self.rebuild_menu_items(self.menu)
        self.status_item.setMenu_(self.menu)

    def _create_item(self, title: str, callback: Optional[Any] = None) -> AppKit.NSMenuItem:
        item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, None, "")
        if callback:
            target = MenuActionTarget.alloc().init()
            target.callback = callback
            self._targets.append(target)
            item.setTarget_(target)
            item.setAction_("onAction:")
        return item

    def update_menu(self) -> None:
        """Trigger a manual refresh of the menu items."""
        if hasattr(self, "menu") and self.menu:
            self.rebuild_menu_items(self.menu)

    def rebuild_menu_items(self, menu: AppKit.NSMenu) -> None:
        """Populate menu items with up-to-date states."""
        self._targets.clear()
        menu.removeAllItems()
        menu.setAutoenablesItems_(False)

        # 1. Title / Header
        char_name = self.engine.character.skin_id.replace("_", " ").title()
        title_item = self._create_item(f"Buddy 2.0 — {char_name}")
        title_item.setEnabled_(False)
        menu.addItem_(title_item)
        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # 2. Signature Move
        sig_item = self._create_item("⚡ Perform Signature Move", lambda _: self.engine.trigger_signature_ability())
        menu.addItem_(sig_item)

        # 3. Current Skin Submenu
        cur_skin = self.engine.character.skin_id
        skin_sub_item = self._create_item(f"🎭 Switch Skin ({cur_skin.replace('_', ' ').title()})")
        skin_menu = AppKit.NSMenu.alloc().init()
        for s in skin_manager.get_available_skins():
            sid = s["id"]
            prefix = "✓ " if sid == cur_skin else "   "
            s_name = s.get("name", sid)
            it = self._create_item(f"{prefix}{s_name}", lambda _, target_id=sid: self._switch_and_redraw(target_id))
            skin_menu.addItem_(it)
        skin_sub_item.setSubmenu_(skin_menu)
        menu.addItem_(skin_sub_item)

        # 4. Pomodoro Submenu
        pomo = getattr(self.engine, "pomodoro", None)
        if pomo:
            pomo_sub_item = self._create_item(f"🍅 Pomodoro [{pomo.status_label}]")
            pomo_menu = AppKit.NSMenu.alloc().init()

            if pomo.state in (PomodoroState.WORK, PomodoroState.SHORT_BREAK, PomodoroState.LONG_BREAK):
                t_item = self._create_item("⏸ Pause Focus Session", lambda _: pomo.pause())
                pomo_menu.addItem_(t_item)
            elif pomo.state == PomodoroState.PAUSED:
                t_item = self._create_item("▶ Resume Focus Session", lambda _: pomo.resume())
                pomo_menu.addItem_(t_item)
            else:
                t_item = self._create_item("▶ Start Focus Session (25 min)", lambda _: pomo.start_work())
                pomo_menu.addItem_(t_item)

            sk_item = self._create_item("⏭ Skip to Next Interval", lambda _: pomo.skip())
            pomo_menu.addItem_(sk_item)

            r_item = self._create_item("⏹ Reset Timer", lambda _: pomo.reset())
            pomo_menu.addItem_(r_item)

            pomo_sub_item.setSubmenu_(pomo_menu)
            menu.addItem_(pomo_sub_item)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # 5. Buddy Mode Submenu
        mode_sub_item = self._create_item("⚙️ Companion Mode")
        mode_menu = AppKit.NSMenu.alloc().init()

        ct_item = self._create_item(
            f"{'✓ ' if self.engine.click_through else '   '}Click-Through Mode (Ghost)",
            lambda _: self.engine.toggle_click_through()
        )
        mode_menu.addItem_(ct_item)

        quiet_item = self._create_item(
            f"{'✓ ' if not self.engine.audio.enabled else '   '}Quiet Mode (Mute)",
            lambda _: self._toggle_sound(not self.engine.audio.enabled)
        )
        mode_menu.addItem_(quiet_item)

        # Scale submenu
        size_sub_item = self._create_item("Pet Scale")
        size_menu = AppKit.NSMenu.alloc().init()
        cur_sc = getattr(self.engine.character, "scale", 1.0)
        for label, sc in [("Small (75%)", 0.75), ("Medium (100%)", 1.0), ("Large (135%)", 1.35), ("Giant (175%)", 1.75)]:
            chk = "✓ " if abs(cur_sc - sc) < 0.1 else "   "
            s_item = self._create_item(f"{chk}{label}", lambda _, val=sc: self.engine.set_scale(val))
            size_menu.addItem_(s_item)
        size_sub_item.setSubmenu_(size_menu)
        mode_menu.addItem_(size_sub_item)

        mode_sub_item.setSubmenu_(mode_menu)
        menu.addItem_(mode_sub_item)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # 6. Dialogs: Settings, Skin Gallery, Stats
        settings_item = self._create_item("Preferences...", lambda _: self._open_settings())
        menu.addItem_(settings_item)

        gallery_item = self._create_item("Character Gallery...", lambda _: self._open_skin_selector())
        menu.addItem_(gallery_item)

        stats_item = self._create_item("Productivity Statistics...", lambda _: self._open_stats())
        menu.addItem_(stats_item)

        help_item = self._create_item("Help & Controls...", lambda _: self._show_help())
        menu.addItem_(help_item)

        menu.addItem_(AppKit.NSMenuItem.separatorItem())

        # 7. Quit Buddy
        quit_item = self._create_item("Quit Buddy", lambda _: self._quit())
        menu.addItem_(quit_item)

    def _switch_and_redraw(self, skin_id: str) -> None:
        self.engine.switch_skin(skin_id)
        if hasattr(self.engine.window, "queue_draw"):
            self.engine.window.queue_draw()

    def _toggle_sound(self, enabled: bool) -> None:
        self.engine.audio.enabled = enabled
        self.engine.config.set("sound_enabled", enabled)

    def _open_settings(self) -> None:
        AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        from ui.settings_dialog import show_settings_dialog
        show_settings_dialog(self.engine)

    def _open_skin_selector(self) -> None:
        AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        from ui.skin_selector import show_skin_selector
        show_skin_selector(self.engine)

    def _open_stats(self) -> None:
        AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        from ui.stats_dialog import show_stats_dialog
        show_stats_dialog(self.engine)

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
        alert.runModal()

    def _quit(self) -> None:
        AppKit.NSApplication.sharedApplication().terminate_(None)
