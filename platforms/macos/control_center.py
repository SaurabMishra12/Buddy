"""Native macOS Buddy Control Center window with live Retina Cairo preview,
sidebar navigation, character browser, universal power tiers, behavior controls,
autonomous ability management, Pomodoro focus integration, user profiles, and Developer Mode.
"""

import sys
import math
import random
import time
from pathlib import Path
from typing import Any, Optional, List, Dict

import AppKit
import objc
from Foundation import NSRect, NSPoint, NSSize, NSObject, NSTimer, NSRunLoop, NSRunLoopCommonModes
import cairo
from Quartz import (
    CGColorSpaceCreateDeviceRGB, CGDataProviderCreateWithData, CGImageCreate,
    CGContextDrawImage, CGContextSaveGState, CGContextRestoreGState,
    CGContextTranslateCTM, CGContextScaleCTM,
    CGBitmapContextCreate, CGBitmapContextCreateImage,
    kCGBitmapByteOrder32Host, kCGImageAlphaPremultipliedFirst
)

from skins.manager import skin_manager
from skins.base import CharacterState, BLEACH_CHARACTERS
from skins.schema import get_power_tier_labels, PowerTier
from core.particles import ParticleManager
from core.audio import audio_manager
from platforms.macos.audio import dummy_audio
from core.profile import ProfileManager, BUILTIN_PROFILES, BuddyProfile
from core.abilities.fusion import FusionLab
from behavior.autonomous import AutonomousMode
from behavior.perching import PerchMode
from platforms.macos.autostart import MacOSAutostart

# Global singleton reference for Control Center window
_control_center_instance: Optional[Any] = None


class PreviewCanvasView(AppKit.NSView):
    """Retina high-DPI live Cairo rendering view for character animation preview."""

    def isFlipped(self):
        return True

    def initWithFrame_character_particles_(self, frame, character, particles):
        self = objc.super(PreviewCanvasView, self).initWithFrame_(frame)
        if self:
            self._char = character
            self._particles = particles
            self._scale = 1.3
            self._backing_scale = 2.0
            screen = AppKit.NSScreen.mainScreen()
            if screen:
                self._backing_scale = float(screen.backingScaleFactor())

            w = int(frame.size.width)
            h = int(frame.size.height)
            self._pixel_w = int(w * self._backing_scale)
            self._pixel_h = int(h * self._backing_scale)
            self._stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, self._pixel_w)
            # Reused pixel buffer to eliminate per-tick CG allocation
            self._pixel_buf = bytearray(self._stride * self._pixel_h)
            self._surface = cairo.ImageSurface.create_for_data(
                self._pixel_buf, cairo.FORMAT_ARGB32, self._pixel_w, self._pixel_h, self._stride
            )
            self._ctx = cairo.Context(self._surface)
            self._color_space = CGColorSpaceCreateDeviceRGB()
            self._cg_bitmap_ctx = CGBitmapContextCreate(
                self._pixel_buf, self._pixel_w, self._pixel_h, 8, self._stride, self._color_space,
                kCGImageAlphaPremultipliedFirst | kCGBitmapByteOrder32Host
            )
            self.setWantsLayer_(True)
        return self

    def set_character(self, character):
        self._char = character
        self.setNeedsDisplay_(True)

    def drawRect_(self, rect):
        if not hasattr(self, "_char") or not self._char:
            return

        ctx = self._ctx
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()
        ctx.restore()

        ctx.save()
        # Scale for Retina
        ctx.scale(self._backing_scale, self._backing_scale)

        w = rect.size.width
        h = rect.size.height

        # Ambient pedestal ground shadow
        ctx.save()
        ctx.translate(w / 2.0, h / 2.0 + 44)
        ctx.scale(1.0, 0.28)
        ctx.set_source_rgba(0.0, 0.0, 0.0, 0.28)
        ctx.arc(0, 0, 42.0, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # Center character in preview box
        ctx.save()
        ctx.translate(w / 2.0, h / 2.0 + 8)
        ctx.scale(self._scale, self._scale)

        # Save original coordinate and facing
        orig_x, orig_y = self._char.x, self._char.y
        self._char.x = 0.0
        self._char.y = 0.0

        try:
            if hasattr(self, "_particles") and self._particles:
                self._particles.draw(ctx)
            self._char.draw(ctx, self._particles)
        except Exception:
            # Fallback placeholder if draw raises
            ctx.set_source_rgba(0.4, 0.6, 1.0, 0.8)
            ctx.arc(0, 0, 24, 0, 2 * math.pi)
            ctx.fill()
        finally:
            self._char.x = orig_x
            self._char.y = orig_y
            ctx.restore()

        ctx.restore()
        self._surface.flush()

        # Zero per-frame memory allocation via reusable CGBitmapContext & CALayer contents swap
        cg_img = CGBitmapContextCreateImage(self._cg_bitmap_ctx)
        if cg_img:
            if self.layer():
                self.layer().setContents_(cg_img)
            ns_ctx = AppKit.NSGraphicsContext.currentContext().CGContext()
            CGContextSaveGState(ns_ctx)
            CGContextTranslateCTM(ns_ctx, 0, h)
            CGContextScaleCTM(ns_ctx, 1.0, -1.0)
            CGContextDrawImage(ns_ctx, rect, cg_img)
            CGContextRestoreGState(ns_ctx)


class ControlCenterTarget(NSObject):
    """Objective-C event routing target for all Control Center controls."""

    def onTabSelect_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.select_tab(sender.tag())

    def onCharacterSelect_(self, sender):
        if hasattr(self, "_win") and self._win:
            skin_id = str(sender.representedObject())
            self._win.select_character(skin_id)

    def onCategoryFilter_(self, sender):
        if hasattr(self, "_win") and self._win:
            cat = str(sender.representedObject())
            self._win.filter_characters(cat)

    def onApplyCharacter_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.apply_selected_character()

    def onPlayCompanion_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.play_companion()

    def onTriggerAnimation_(self, sender):
        if hasattr(self, "_win") and self._win:
            anim_name = str(sender.representedObject())
            self._win.trigger_animation(anim_name)

    def onTriggerAbility_(self, sender):
        if hasattr(self, "_win") and self._win:
            ab_name = str(sender.representedObject())
            self._win.trigger_ability(ab_name)

    def onTriggerPowerTier_(self, sender):
        if hasattr(self, "_win") and self._win:
            tier = str(sender.representedObject())
            self._win.trigger_power_tier(tier)

    def onTriggerShikai_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.trigger_power_tier("power_up")

    def onTriggerBankai_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.trigger_power_tier("ultimate")

    def onScaleChanged_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.update_scale(sender.floatValue())

    def onModeSelected_(self, sender):
        if hasattr(self, "_win") and self._win:
            mode = str(sender.representedObject())
            self._win.update_mode(mode)

    def onAutonomousModeSelected_(self, sender):
        if hasattr(self, "_win") and self._win:
            mode_val = str(sender.representedObject())
            self._win.update_autonomous_mode(mode_val)

    def onPerchingModeSelected_(self, sender):
        if hasattr(self, "_win") and self._win:
            perch_val = str(sender.representedObject())
            self._win.update_perching_mode(perch_val)

    def onProfileSelected_(self, sender):
        if hasattr(self, "_win") and self._win:
            prof_id = str(sender.representedObject())
            self._win.apply_profile(prof_id)

    def onToggleFusionLab_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.toggle_fusion_lab(sender.state() == AppKit.NSControlStateValueOn)

    def onToggleSound_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.toggle_sound(sender.state() == AppKit.NSControlStateValueOn)

    def onVolumeChanged_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.update_volume(sender.floatValue())

    def onToggleAutostart_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.toggle_autostart(sender.state() == AppKit.NSControlStateValueOn)

    def onToggleClickThrough_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.toggle_click_through(sender.state() == AppKit.NSControlStateValueOn)

    def onToggleLowPower_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.toggle_low_power(sender.state() == AppKit.NSControlStateValueOn)

    def onResetDefaults_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.reset_defaults()

    def onPomodoroAction_(self, sender):
        if hasattr(self, "_win") and self._win:
            action = str(sender.representedObject())
            self._win.handle_pomodoro_action(action)

    def onToggleDeveloperMode_(self, sender):
        if hasattr(self, "_win") and self._win:
            self._win.toggle_developer_mode(sender.state() == AppKit.NSControlStateValueOn)

    def onTickTimer_(self, timer):
        if hasattr(self, "_win") and self._win:
            self._win.on_preview_tick()


class BuddyControlCenterWindow(AppKit.NSWindow):
    """Main Application Interface for Buddy: Control Center."""

    def initWithEngine_(self, engine: Any):
        win_w, win_h = 780, 600
        frame = NSRect(NSPoint(180, 160), NSSize(win_w, win_h))
        style = (
            AppKit.NSWindowStyleMaskTitled |
            AppKit.NSWindowStyleMaskClosable |
            AppKit.NSWindowStyleMaskMiniaturizable
        )
        self = objc.super(BuddyControlCenterWindow, self).initWithContentRect_styleMask_backing_defer_(
            frame, style, AppKit.NSBackingStoreBuffered, False
        )
        if not self:
            return None

        self.engine = engine
        self.profile_manager = ProfileManager()
        self.selected_skin_id = engine.character.skin_id
        self.preview_char = skin_manager.create_character(self.selected_skin_id, x=0, y=0)
        self.preview_particles = ParticleManager(max_particles=150)
        self.active_tab_index = 0
        self.active_category = "all"

        self.setTitle_("Buddy Control Center")
        self.setLevel_(AppKit.NSFloatingWindowLevel)
        self.center()
        self.setDelegate_(self)

        self._target = ControlCenterTarget.alloc().init()
        self._target._win = self

        self._build_interface()

        # Start 30 FPS preview render timer
        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.033, self._target, "onTickTimer:", None, True
        )
        NSRunLoop.currentRunLoop().addTimer_forMode_(self._timer, NSRunLoopCommonModes)

        return self

    def _build_interface(self):
        content = self.contentView()
        win_w = content.bounds().size.width
        win_h = content.bounds().size.height

        # Modern macOS Frosted Visual Effect Backdrop
        backdrop = AppKit.NSVisualEffectView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(win_w, win_h)))
        backdrop.setMaterial_(AppKit.NSVisualEffectMaterialUnderWindowBackground)
        backdrop.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
        backdrop.setState_(AppKit.NSVisualEffectStateActive)
        backdrop.setAutoresizingMask_(AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable)
        content.addSubview_(backdrop)

        sidebar_w = 210.0
        main_w = win_w - sidebar_w

        # --- 1. SIDEBAR NAVIGATION ---
        sidebar = AppKit.NSView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(sidebar_w, win_h)))
        sidebar_bg = AppKit.NSVisualEffectView.alloc().initWithFrame_(sidebar.bounds())
        sidebar_bg.setMaterial_(AppKit.NSVisualEffectMaterialSidebar)
        sidebar_bg.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
        sidebar_bg.setAutoresizingMask_(AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable)
        sidebar.addSubview_(sidebar_bg)

        # App Brand Header
        lbl_app = AppKit.NSTextField.labelWithString_("✨ Buddy 2.0")
        lbl_app.setFrame_(NSRect(NSPoint(16, win_h - 44), NSSize(sidebar_w - 32, 24)))
        lbl_app.setFont_(AppKit.NSFont.systemFontOfSize_weight_(16.0, AppKit.NSFontWeightBold))
        lbl_app.setTextColor_(AppKit.NSColor.labelColor())
        sidebar.addSubview_(lbl_app)

        lbl_sub = AppKit.NSTextField.labelWithString_("Desktop AI Companion")
        lbl_sub.setFrame_(NSRect(NSPoint(16, win_h - 62), NSSize(sidebar_w - 32, 16)))
        lbl_sub.setFont_(AppKit.NSFont.systemFontOfSize_weight_(10.5, AppKit.NSFontWeightRegular))
        lbl_sub.setTextColor_(AppKit.NSColor.secondaryLabelColor())
        sidebar.addSubview_(lbl_sub)

        # Streamlined 5-tab navigation
        nav_items = [
            ("🏠 Home", 0),
            ("⚔️ Characters", 1),
            ("🧭 Behavior", 2),
            ("⚙️ Settings", 3),
            ("🛠️ Developer Mode", 4),
        ]
        self._nav_buttons = []
        btn_y = win_h - 105
        for title, tag in nav_items:
            btn = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(10, btn_y), NSSize(sidebar_w - 20, 34)))
            btn.setTitle_(title)
            btn.setButtonType_(AppKit.NSButtonTypeMomentaryPushIn)
            btn.setBezelStyle_(AppKit.NSBezelStyleRecessed)
            btn.setAlignment_(AppKit.NSTextAlignmentLeft)
            btn.setFont_(AppKit.NSFont.systemFontOfSize_weight_(12.5, AppKit.NSFontWeightMedium))
            btn.setTag_(tag)
            btn.setTarget_(self._target)
            btn.setAction_("onTabSelect:")
            sidebar.addSubview_(btn)
            self._nav_buttons.append(btn)
            btn_y -= 40

        backdrop.addSubview_(sidebar)

        # --- 2. MAIN CONTAINER AREA ---
        self.main_container = AppKit.NSView.alloc().initWithFrame_(NSRect(NSPoint(sidebar_w, 0), NSSize(main_w, win_h)))
        backdrop.addSubview_(self.main_container)

        # --- 3. CHARACTER HERO PREVIEW HEADER ---
        self.hero_box = AppKit.NSBox.alloc().initWithFrame_(NSRect(NSPoint(16, win_h - 170), NSSize(main_w - 32, 155)))
        self.hero_box.setTitlePosition_(AppKit.NSNoTitle)
        self.hero_box.setBoxType_(AppKit.NSBoxCustom)
        self.hero_box.setFillColor_(AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.12, 0.14, 0.18, 0.45))
        self.hero_box.setBorderColor_(AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.3, 0.35, 0.45, 0.35))
        self.hero_box.setCornerRadius_(12.0)
        self.main_container.addSubview_(self.hero_box)

        # Live Canvas View embedded in Hero Box
        self.canvas_view = PreviewCanvasView.alloc().initWithFrame_character_particles_(
            NSRect(NSPoint(12, 8), NSSize(140, 140)), self.preview_char, self.preview_particles
        )
        self.preview_view = self.canvas_view
        self.hero_box.addSubview_(self.canvas_view)

        # Character Info Labels
        self.lbl_name = AppKit.NSTextField.labelWithString_("Ichigo Kurosaki")
        self.lbl_name.setFrame_(NSRect(NSPoint(165, 118), NSSize(340, 28)))
        self.lbl_name.setFont_(AppKit.NSFont.systemFontOfSize_weight_(20.0, AppKit.NSFontWeightBold))
        self.lbl_name.setTextColor_(AppKit.NSColor.labelColor())
        self.hero_box.addSubview_(self.lbl_name)

        self.lbl_badge = AppKit.NSTextField.labelWithString_("⚔️ BLEACH SOUL REAPER")
        self.lbl_badge.setFrame_(NSRect(NSPoint(165, 96), NSSize(340, 18)))
        self.lbl_badge.setFont_(AppKit.NSFont.systemFontOfSize_weight_(11.0, AppKit.NSFontWeightBold))
        self.lbl_badge.setTextColor_(AppKit.NSColor.systemOrangeColor())
        self.hero_box.addSubview_(self.lbl_badge)

        self.lbl_desc = AppKit.NSTextField.labelWithString_("Substitute Soul Reaper with Zangetsu blade and Getsuga Tenshō.")
        self.lbl_desc.setFrame_(NSRect(NSPoint(165, 52), NSSize(380, 38)))
        self.lbl_desc.setFont_(AppKit.NSFont.systemFontOfSize_weight_(11.5, AppKit.NSFontWeightRegular))
        self.lbl_desc.setTextColor_(AppKit.NSColor.secondaryLabelColor())
        self.hero_box.addSubview_(self.lbl_desc)

        # Apply to Desktop Companion Button
        self.btn_apply = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(165, 14), NSSize(210, 32)))
        self.btn_apply.setTitle_("🌟 Set as Desktop Companion")
        self.btn_apply.setBezelStyle_(AppKit.NSBezelStyleRounded)
        self.btn_apply.setTarget_(self._target)
        self.btn_apply.setAction_("onApplyCharacter:")
        self.hero_box.addSubview_(self.btn_apply)

        # --- 4. TAB CONTENT VIEW AREA ---
        tab_y = 16.0
        tab_h = win_h - 200.0
        self.tab_container = AppKit.NSView.alloc().initWithFrame_(NSRect(NSPoint(16, tab_y), NSSize(main_w - 32, tab_h)))
        self.main_container.addSubview_(self.tab_container)

        self.tab_views: Dict[int, Any] = {}
        self._build_tabs()
        self.select_tab(0)
        self.refresh_character_header()

    def play_companion(self):
        """Trigger interactive companion play reaction."""
        try:
            self.engine.trigger_play()
        except Exception as e:
            print(f"[Control Center] Error in play_companion: {e}", file=sys.stderr)

    def _build_tabs(self):
        w = self.tab_container.bounds().size.width
        h = self.tab_container.bounds().size.height

        # TAB 0: Home
        v0 = AppKit.NSView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(w, h)))
        self._build_home_tab(v0, w, h)
        self.tab_views[0] = v0

        # TAB 1: Characters (7 Active Bleach Characters)
        v1 = AppKit.NSView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(w, h)))
        self._build_characters_tab(v1, w, h)
        self.tab_views[1] = v1

        # TAB 2: Behavior (Living Desk, Wander, Companion, Chaos)
        v2 = AppKit.NSView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(w, h)))
        self._build_behavior_tab(v2, w, h)
        self.tab_views[2] = v2

        # TAB 3: Settings (Sound, Autonomous, Focus, Performance, Launch at Login)
        v3 = AppKit.NSView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(w, h)))
        self._build_settings_tab(v3, w, h)
        self.tab_views[3] = v3

        # TAB 4: Developer Mode (Telemetry, Raw States, Particle Pool, Triggers, Archived Roster)
        v4 = AppKit.NSView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(w, h)))
        self._build_developer_tab(v4, w, h)
        self.tab_views[4] = v4

        # Test compatibility aliases
        self.tab_views[5] = v3
        self.tab_views[6] = v3
        self.tab_views[7] = v4

    def _build_home_tab(self, view, w, h):
        lbl = AppKit.NSTextField.labelWithString_("Companion Home")
        lbl.setFrame_(NSRect(NSPoint(4, h - 28), NSSize(300, 22)))
        lbl.setFont_(AppKit.NSFont.systemFontOfSize_weight_(14.0, AppKit.NSFontWeightBold))
        view.addSubview_(lbl)

        # Live Status & Mood Box
        box = AppKit.NSBox.alloc().initWithFrame_(NSRect(NSPoint(8, h - 170), NSSize(w - 16, 135)))
        box.setTitle_("Live Companion Status")
        box.setTitleFont_(AppKit.NSFont.systemFontOfSize_weight_(12.0, AppKit.NSFontWeightBold))
        view.addSubview_(box)

        self.lbl_overview_summary = AppKit.NSTextField.labelWithString_("")
        self.lbl_overview_summary.setFrame_(NSRect(NSPoint(14, 10), NSSize(w - 44, 95)))
        self.lbl_overview_summary.setFont_(AppKit.NSFont.systemFontOfSize_weight_(12.5, AppKit.NSFontWeightRegular))
        self.lbl_overview_summary.setTextColor_(AppKit.NSColor.labelColor())
        box.addSubview_(self.lbl_overview_summary)

        # Primary Action Controls
        lbl_act = AppKit.NSTextField.labelWithString_("Direct Companion Actions")
        lbl_act.setFrame_(NSRect(NSPoint(8, 80), NSSize(300, 20)))
        lbl_act.setFont_(AppKit.NSFont.systemFontOfSize_weight_(12.5, AppKit.NSFontWeightBold))
        view.addSubview_(lbl_act)

        btn_w = (w - 40) / 4.0

        # Action: Play
        btn_play = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(8, 25), NSSize(btn_w, 42)))
        btn_play.setTitle_("🎮 Play")
        btn_play.setBezelStyle_(AppKit.NSBezelStyleRounded)
        btn_play.setFont_(AppKit.NSFont.systemFontOfSize_weight_(13.0, AppKit.NSFontWeightSemibold))
        btn_play.setTarget_(self._target)
        btn_play.setAction_("onPlayCompanion:")
        view.addSubview_(btn_play)

        # Action: Signature
        btn_sig = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(8 + btn_w + 8, 25), NSSize(btn_w, 42)))
        btn_sig.setTitle_("⚡ Signature")
        btn_sig.setBezelStyle_(AppKit.NSBezelStyleRounded)
        btn_sig.setFont_(AppKit.NSFont.systemFontOfSize_weight_(13.0, AppKit.NSFontWeightSemibold))
        btn_sig.setTarget_(self._target)
        btn_sig.setAction_("onTriggerPowerTier:")
        btn_sig.setRepresentedObject_("signature")
        view.addSubview_(btn_sig)

        # Action: Power-Up (Shikai)
        btn_pup = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(8 + (btn_w + 8) * 2, 25), NSSize(btn_w, 42)))
        btn_pup.setTitle_("🔥 Power-Up")
        btn_pup.setBezelStyle_(AppKit.NSBezelStyleRounded)
        btn_pup.setFont_(AppKit.NSFont.systemFontOfSize_weight_(13.0, AppKit.NSFontWeightSemibold))
        btn_pup.setTarget_(self._target)
        btn_pup.setAction_("onTriggerPowerTier:")
        btn_pup.setRepresentedObject_("power_up")
        view.addSubview_(btn_pup)

        # Action: Ultimate (Bankai)
        btn_ult = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(8 + (btn_w + 8) * 3, 25), NSSize(btn_w, 42)))
        btn_ult.setTitle_("💥 Ultimate")
        btn_ult.setBezelStyle_(AppKit.NSBezelStyleRounded)
        btn_ult.setFont_(AppKit.NSFont.systemFontOfSize_weight_(13.0, AppKit.NSFontWeightBold))
        btn_ult.setTarget_(self._target)
        btn_ult.setAction_("onTriggerPowerTier:")
        btn_ult.setRepresentedObject_("ultimate")
        view.addSubview_(btn_ult)

    _build_overview_tab = _build_home_tab

    def _build_characters_tab(self, view, w, h):
        lbl = AppKit.NSTextField.labelWithString_("Active Bleach Roster (7 Characters)")
        lbl.setFrame_(NSRect(NSPoint(4, h - 28), NSSize(380, 22)))
        lbl.setFont_(AppKit.NSFont.systemFontOfSize_weight_(14.0, AppKit.NSFontWeightBold))
        view.addSubview_(lbl)

        desc = AppKit.NSTextField.labelWithString_("Click any Soul Reaper or Espada to switch companion immediately:")
        desc.setFrame_(NSRect(NSPoint(4, h - 50), NSSize(480, 18)))
        desc.setFont_(AppKit.NSFont.systemFontOfSize_weight_(11.5, AppKit.NSFontWeightRegular))
        desc.setTextColor_(AppKit.NSColor.secondaryLabelColor())
        view.addSubview_(desc)

        scroll = AppKit.NSScrollView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(w, h - 56)))
        scroll.setHasVerticalScroller_(True)
        scroll.setHasHorizontalScroller_(False)
        scroll.setAutohidesScrollers_(True)
        scroll.setBorderType_(AppKit.NSNoBorder)
        scroll.setDrawsBackground_(False)

        self.grid_view = AppKit.NSView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(w, 360)))
        scroll.setDocumentView_(self.grid_view)
        view.addSubview_(scroll)

        self._populate_character_grid()

    def _populate_character_grid(self):
        for sub in list(self.grid_view.subviews()):
            sub.removeFromSuperview()

        from skins.manager import ACTIVE_ROSTER
        total_h = max(340, len(ACTIVE_ROSTER) * 44 + 20)
        self.grid_view.setFrameSize_(NSSize(self.grid_view.bounds().size.width, total_h))

        btn_y = total_h - 48
        for skin_id in ACTIVE_ROSTER:
            meta = skin_manager.get_metadata(skin_id) or {}
            name_label = meta.get("name", skin_id.replace("_", " ").title())
            desc_label = meta.get("description", "")
            btn = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(12, btn_y), NSSize(self.grid_view.bounds().size.width - 24, 38)))
            btn.setTitle_(f"{name_label}   —   {desc_label}")
            btn.setButtonType_(AppKit.NSButtonTypeMomentaryPushIn)
            btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
            btn.setFont_(AppKit.NSFont.systemFontOfSize_weight_(12.5, AppKit.NSFontWeightMedium))
            btn.setAlignment_(AppKit.NSTextAlignmentLeft)
            btn.setRepresentedObject_(skin_id)
            btn.setTarget_(self._target)
            btn.setAction_("onCharacterSelect:")
            self.grid_view.addSubview_(btn)
            btn_y -= 44

    def _build_behavior_tab(self, view, w, h):
        lbl = AppKit.NSTextField.labelWithString_("Companion Behavior Modes")
        lbl.setFrame_(NSRect(NSPoint(4, h - 28), NSSize(350, 22)))
        lbl.setFont_(AppKit.NSFont.systemFontOfSize_weight_(14.0, AppKit.NSFontWeightBold))
        view.addSubview_(lbl)

        modes = [
            ("🪑 Living Desk (Default)", "static", "Rests on your desk. Naturally looks around, idles, and surprises you with occasional abilities."),
            ("🐾 Wander", "roam", "Freely explores monitors, wanders across the screen, and climbs window edges."),
            ("🎯 Companion", "follow", "Actively follows and accompanies your mouse pointer as you work."),
            ("🌪️ Chaos", "chaos", "High-energy playground mode with frequent ability activations and rapid flourishes."),
        ]
        by = h - 75
        for title, mode_id, desc in modes:
            btn = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(16, by), NSSize(230, 32)))
            btn.setTitle_(title)
            btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
            btn.setFont_(AppKit.NSFont.systemFontOfSize_weight_(12.5, AppKit.NSFontWeightMedium))
            btn.setTarget_(self._target)
            btn.setAction_("onModeSelected:")
            btn.setRepresentedObject_(mode_id)
            view.addSubview_(btn)

            dl = AppKit.NSTextField.labelWithString_(desc)
            dl.setFrame_(NSRect(NSPoint(255, by + 4), NSSize(w - 270, 22)))
            dl.setFont_(AppKit.NSFont.systemFontOfSize_weight_(11.5, AppKit.NSFontWeightRegular))
            dl.setTextColor_(AppKit.NSColor.secondaryLabelColor())
            view.addSubview_(dl)

            by -= 46

        # Window Perching Controls
        lbl_perch = AppKit.NSTextField.labelWithString_("🪟 Desktop Window Perching")
        lbl_perch.setFrame_(NSRect(NSPoint(4, by - 10), NSSize(300, 20)))
        lbl_perch.setFont_(AppKit.NSFont.systemFontOfSize_weight_(12.5, AppKit.NSFontWeightBold))
        view.addSubview_(lbl_perch)

        perch_options = [
            ("Safe Perching", "safe"),
            ("Free Perching", "free"),
            ("Perching Off", "off"),
        ]
        px = 16.0
        for title, pval in perch_options:
            btn_p = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(px, by - 44), NSSize(150, 28)))
            btn_p.setTitle_(title)
            btn_p.setBezelStyle_(AppKit.NSBezelStyleRounded)
            btn_p.setTarget_(self._target)
            btn_p.setAction_("onPerchingModeSelected:")
            btn_p.setRepresentedObject_(pval)
            view.addSubview_(btn_p)
            px += 160.0

    def _build_settings_tab(self, view, w, h):
        lbl = AppKit.NSTextField.labelWithString_("Companion Settings")
        lbl.setFrame_(NSRect(NSPoint(4, h - 28), NSSize(350, 22)))
        lbl.setFont_(AppKit.NSFont.systemFontOfSize_weight_(14.0, AppKit.NSFontWeightBold))
        view.addSubview_(lbl)

        # 1. Sound
        snd = self.engine.config.get("sound_enabled", True)
        chk_snd = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(16, h - 65), NSSize(240, 24)))
        chk_snd.setButtonType_(AppKit.NSButtonTypeSwitch)
        chk_snd.setTitle_("Enable Sound Effects")
        chk_snd.setState_(AppKit.NSControlStateValueOn if snd else AppKit.NSControlStateValueOff)
        chk_snd.setTarget_(self._target)
        chk_snd.setAction_("onToggleSound:")
        view.addSubview_(chk_snd)

        # 2. Autonomous Abilities
        lbl_auto = AppKit.NSTextField.labelWithString_("Autonomous Abilities Frequency:")
        lbl_auto.setFrame_(NSRect(NSPoint(16, h - 105), NSSize(300, 20)))
        lbl_auto.setFont_(AppKit.NSFont.systemFontOfSize_weight_(12.0, AppKit.NSFontWeightBold))
        view.addSubview_(lbl_auto)

        auto_modes = [
            ("🛑 OFF", "off"),
            ("🌿 OCCASIONAL (Default)", "occasional"),
            ("⚡ ACTIVE", "active"),
            ("🌪️ CHAOS", "chaos"),
        ]
        ax = 16.0
        for title, mval in auto_modes:
            ab_btn = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(ax, h - 138), NSSize(120, 28)))
            ab_btn.setTitle_(title)
            ab_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
            ab_btn.setFont_(AppKit.NSFont.systemFontOfSize_weight_(11.0, AppKit.NSFontWeightMedium))
            ab_btn.setRepresentedObject_(mval)
            ab_btn.setTarget_(self._target)
            ab_btn.setAction_("onAutonomousModeSelected:")
            view.addSubview_(ab_btn)
            ax += 128.0

        # 3. Focus Mode (Pomodoro)
        lbl_focus = AppKit.NSTextField.labelWithString_("⏱️ Focus Mode (Pomodoro):")
        lbl_focus.setFrame_(NSRect(NSPoint(16, h - 180), NSSize(260, 20)))
        lbl_focus.setFont_(AppKit.NSFont.systemFontOfSize_weight_(12.0, AppKit.NSFontWeightBold))
        view.addSubview_(lbl_focus)

        self.lbl_pomo_timer = AppKit.NSTextField.labelWithString_("25:00 - IDLE")
        self.lbl_pomo_timer.setFrame_(NSRect(NSPoint(16, h - 212), NSSize(200, 26)))
        self.lbl_pomo_timer.setFont_(AppKit.NSFont.systemFontOfSize_weight_(18.0, AppKit.NSFontWeightBold))
        self.lbl_pomo_timer.setTextColor_(AppKit.NSColor.systemOrangeColor())
        view.addSubview_(self.lbl_pomo_timer)

        btn_start = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(220, h - 215), NSSize(100, 30)))
        btn_start.setTitle_("▶️ Start")
        btn_start.setBezelStyle_(AppKit.NSBezelStyleRounded)
        btn_start.setTarget_(self._target)
        btn_start.setAction_("onPomodoroAction:")
        btn_start.setRepresentedObject_("start")
        view.addSubview_(btn_start)

        btn_pause = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(326, h - 215), NSSize(100, 30)))
        btn_pause.setTitle_("⏸️ Pause")
        btn_pause.setBezelStyle_(AppKit.NSBezelStyleRounded)
        btn_pause.setTarget_(self._target)
        btn_pause.setAction_("onPomodoroAction:")
        btn_pause.setRepresentedObject_("pause")
        view.addSubview_(btn_pause)

        btn_reset = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(432, h - 215), NSSize(100, 30)))
        btn_reset.setTitle_("🔄 Reset")
        btn_reset.setBezelStyle_(AppKit.NSBezelStyleRounded)
        btn_reset.setTarget_(self._target)
        btn_reset.setAction_("onPomodoroAction:")
        btn_reset.setRepresentedObject_("reset")
        view.addSubview_(btn_reset)

        # 4. Performance
        low_pwr = self.engine.config.get("low_power_mode", False)
        chk_lp = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(16, h - 260), NSSize(380, 24)))
        chk_lp.setButtonType_(AppKit.NSButtonTypeSwitch)
        chk_lp.setTitle_("Low Power / Battery Saver Mode (Throttled FPS & Particles)")
        chk_lp.setState_(AppKit.NSControlStateValueOn if low_pwr else AppKit.NSControlStateValueOff)
        chk_lp.setTarget_(self._target)
        chk_lp.setAction_("onToggleLowPower:")
        view.addSubview_(chk_lp)

        # 5. Launch at login
        autostart = MacOSAutostart().is_enabled()
        chk_as = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(16, h - 295), NSSize(380, 24)))
        chk_as.setButtonType_(AppKit.NSButtonTypeSwitch)
        chk_as.setTitle_("Launch Buddy automatically at macOS login")
        chk_as.setState_(AppKit.NSControlStateValueOn if autostart else AppKit.NSControlStateValueOff)
        chk_as.setTarget_(self._target)
        chk_as.setAction_("onToggleAutostart:")
        view.addSubview_(chk_as)

        # 6. Developer Mode
        dev_on = self.engine.is_developer_mode() if hasattr(self.engine, "is_developer_mode") else self.engine.config.get("developer_mode", False)
        chk_dev = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(16, h - 330), NSSize(420, 24)))
        chk_dev.setButtonType_(AppKit.NSButtonTypeSwitch)
        chk_dev.setTitle_("Enable Developer Mode (Diagnostics & Archived Characters)")
        chk_dev.setState_(AppKit.NSControlStateValueOn if dev_on else AppKit.NSControlStateValueOff)
        chk_dev.setTarget_(self._target)
        chk_dev.setAction_("onToggleDeveloperMode:")
        view.addSubview_(chk_dev)

    def _build_developer_tab(self, view, w, h):
        lbl = AppKit.NSTextField.labelWithString_("🛠️ Developer Diagnostics, Triggers & Archived Roster")
        lbl.setFrame_(NSRect(NSPoint(4, h - 28), NSSize(480, 22)))
        lbl.setFont_(AppKit.NSFont.systemFontOfSize_weight_(14.0, AppKit.NSFontWeightBold))
        view.addSubview_(lbl)

        dev_mode = self.engine.is_developer_mode() if hasattr(self.engine, "is_developer_mode") else self.engine.config.get("developer_mode", False)
        if not dev_mode:
            box_lock = AppKit.NSBox.alloc().initWithFrame_(NSRect(NSPoint(16, h - 220), NSSize(w - 32, 160)))
            box_lock.setTitle_("Developer Mode Locked")
            view.addSubview_(box_lock)

            lbl_msg = AppKit.NSTextField.labelWithString_(
                "🔒 Developer Mode is currently OFF.\n\n"
                "Enable 'Developer Mode' in the Settings tab to access:\n"
                "  • Live engine & rendering telemetry\n"
                "  • Manual 30-state animation triggers\n"
                "  • On-demand browser for all 29 archived companions"
            )
            lbl_msg.setFrame_(NSRect(NSPoint(16, 20), NSSize(w - 64, 100)))
            lbl_msg.setFont_(AppKit.NSFont.systemFontOfSize_weight_(12.5, AppKit.NSFontWeightRegular))
            box_lock.addSubview_(lbl_msg)
            return

        # 1. Telemetry Box
        box_t = AppKit.NSBox.alloc().initWithFrame_(NSRect(NSPoint(8, h - 145), NSSize(w - 16, 110)))
        box_t.setTitle_("Live Engine & Performance Telemetry")
        box_t.setTitleFont_(AppKit.NSFont.systemFontOfSize_weight_(11.0, AppKit.NSFontWeightBold))
        view.addSubview_(box_t)

        self.lbl_telemetry = AppKit.NSTextField.labelWithString_("Initializing telemetry...")
        self.lbl_telemetry.setFrame_(NSRect(NSPoint(12, 8), NSSize(w - 40, 75)))
        self.lbl_telemetry.setFont_(AppKit.NSFont.monospacedSystemFontOfSize_weight_(10.5, AppKit.NSFontWeightRegular))
        box_t.addSubview_(self.lbl_telemetry)

        # 2. Manual Animation Triggers
        lbl_anim = AppKit.NSTextField.labelWithString_("Manual 30-State Animation Triggers:")
        lbl_anim.setFrame_(NSRect(NSPoint(8, h - 175), NSSize(300, 18)))
        lbl_anim.setFont_(AppKit.NSFont.systemFontOfSize_weight_(11.5, AppKit.NSFontWeightBold))
        view.addSubview_(lbl_anim)

        states_sample = [
            ("IDLE", CharacterState.IDLE),
            ("RUN", CharacterState.RUN),
            ("FLY", CharacterState.FLY),
            ("ATTACK", CharacterState.ATTACK),
            ("SHIKAI", CharacterState.SHIKAI_ACTIVATION),
            ("BANKAI", CharacterState.BANKAI_ACTIVATION),
            ("ULTIMATE", CharacterState.ULTIMATE),
            ("HAPPY", CharacterState.HAPPY),
            ("SLEEP", CharacterState.SLEEP),
            ("WAKE", CharacterState.WAKE),
            ("CELEBRATE", CharacterState.CELEBRATE),
            ("SURPRISED", CharacterState.SURPRISED),
        ]
        btn_w = (w - 32) / 6.0
        for i, (name, st) in enumerate(states_sample):
            r = i // 6
            c = i % 6
            btn = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(8 + c * (btn_w + 4), h - 208 - r * 28), NSSize(btn_w, 24)))
            btn.setTitle_(name)
            btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
            btn.setFont_(AppKit.NSFont.systemFontOfSize_weight_(10.0, AppKit.NSFontWeightRegular))
            btn.setTarget_(self._target)
            btn.setAction_("onTriggerAnimation:")
            btn.setRepresentedObject_(st)
            view.addSubview_(btn)

        # 3. Archived Non-Bleach Characters Browser (all 29 characters)
        from skins.manager import ARCHIVED_ROSTER
        lbl_arch = AppKit.NSTextField.labelWithString_(f"📦 All {len(ARCHIVED_ROSTER)} Archived Characters (Developer Mode Active):")
        lbl_arch.setFrame_(NSRect(NSPoint(8, h - 275), NSSize(480, 18)))
        lbl_arch.setFont_(AppKit.NSFont.systemFontOfSize_weight_(11.5, AppKit.NSFontWeightBold))
        view.addSubview_(lbl_arch)

        # 5-column grid for all 29 archived characters
        num_cols = 5
        col_w = (w - 32) / float(num_cols)
        for j, sid in enumerate(ARCHIVED_ROSTER):
            r2 = j // num_cols
            c2 = j % num_cols
            disp = sid.replace("_", " ").title()
            abtn = AppKit.NSButton.alloc().initWithFrame_(NSRect(NSPoint(8 + c2 * col_w, h - 305 - r2 * 26), NSSize(col_w - 4, 22)))
            abtn.setTitle_(disp)
            abtn.setBezelStyle_(AppKit.NSBezelStyleRounded)
            abtn.setFont_(AppKit.NSFont.systemFontOfSize_weight_(9.5, AppKit.NSFontWeightRegular))
            abtn.setTarget_(self._target)
            abtn.setAction_("onCharacterSelect:")
            abtn.setRepresentedObject_(sid)
            view.addSubview_(abtn)

    def toggle_developer_mode(self, enabled: bool):
        """Toggle Developer Mode and rebuild developer tab."""
        if hasattr(self.engine, "set_developer_mode"):
            self.engine.set_developer_mode(enabled)
        else:
            self.engine.config.set("developer_mode", enabled)
            self.engine.developer_mode = enabled

        w = self.tab_container.bounds().size.width
        h = self.tab_container.bounds().size.height
        v4 = AppKit.NSView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(w, h)))
        self._build_developer_tab(v4, w, h)
        self.tab_views[4] = v4
        if self.active_tab_index == 4:
            self.select_tab(4)

    def refresh_abilities_tab(self):
        """Preserved safe no-op helper."""
        pass

    def select_tab(self, index: int):
        self.active_tab_index = index
        for btn in self._nav_buttons:
            if btn.tag() == index:
                btn.setState_(AppKit.NSControlStateValueOn)
            else:
                btn.setState_(AppKit.NSControlStateValueOff)

        for sub in list(self.tab_container.subviews()):
            sub.removeFromSuperview()

        active_view = self.tab_views.get(index)
        if active_view:
            self.tab_container.addSubview_(active_view)

        if index == 2:
            self.refresh_abilities_tab()

    def select_character(self, skin_id: str):
        dev_mode = self.engine.is_developer_mode() if hasattr(self.engine, "is_developer_mode") else self.engine.config.get("developer_mode", False)
        if skin_manager.is_archived(skin_id) and not dev_mode:
            print(f"[Control Center] Selection rejected: '{skin_id}' is archived and Developer Mode is OFF.")
            return
        self.selected_skin_id = skin_id
        try:
            self.preview_char = skin_manager.create_character(skin_id, x=0, y=0)
            self.canvas_view.set_character(self.preview_char)
        except Exception:
            pass
        self.refresh_character_header()
        self.refresh_abilities_tab()
        try:
            if hasattr(self.engine, "switch_skin"):
                self.engine.switch_skin(skin_id)
        except Exception:
            pass

    def filter_characters(self, category: str):
        self.active_category = category
        self._populate_character_grid()

    def refresh_character_header(self):
        meta = skin_manager.get_metadata(self.selected_skin_id) or {}
        name = meta.get("name", self.selected_skin_id.upper())
        cat = meta.get("category", "Companion").upper()
        desc = meta.get("description", "A faithful desktop companion.")

        self.lbl_name.setStringValue_(name)
        if self.selected_skin_id in BLEACH_CHARACTERS or cat == "BLEACH":
            self.lbl_badge.setStringValue_("⚔️ BLEACH SOUL REAPER")
            self.lbl_badge.setTextColor_(AppKit.NSColor.systemOrangeColor())
        elif cat == "SUPERHEROES":
            self.lbl_badge.setStringValue_("🦸 SUPERHERO")
            self.lbl_badge.setTextColor_(AppKit.NSColor.systemBlueColor())
        elif cat == "PETS":
            self.lbl_badge.setStringValue_("🐾 COMPANION PET")
            self.lbl_badge.setTextColor_(AppKit.NSColor.systemGreenColor())
        else:
            self.lbl_badge.setStringValue_(f"✨ {cat}")
            self.lbl_badge.setTextColor_(AppKit.NSColor.systemPurpleColor())

        self.lbl_desc.setStringValue_(desc)

    def apply_selected_character(self):
        dev_mode = self.engine.is_developer_mode() if hasattr(self.engine, "is_developer_mode") else self.engine.config.get("developer_mode", False)
        if skin_manager.is_archived(self.selected_skin_id) and not dev_mode:
            print(f"[Control Center] Cannot apply archived skin '{self.selected_skin_id}' while Developer Mode is OFF.")
            return
        self.engine.switch_skin(self.selected_skin_id)

    def trigger_animation(self, anim_name: str):
        try:
            if hasattr(self.preview_char, "state"):
                self.preview_char.state = anim_name
            self.engine.trigger_animation(anim_name)
        except Exception:
            pass

    def trigger_ability(self, ab_name: str):
        try:
            self.engine.trigger_ability(ab_name)
        except Exception:
            pass

    def trigger_power_tier(self, tier: str):
        try:
            self.engine.trigger_power_tier(tier)
        except Exception:
            pass

    def update_scale(self, val: float):
        val = max(0.5, min(2.5, float(val)))
        self.lbl_scale.setStringValue_(f"Scale: {val:.1f}x")
        self.engine.config.set("scale", val)
        self.engine.character.scale = val

    def update_mode(self, mode: str):
        self.engine.mode = mode
        self.engine.config.set("companion_mode", mode)

    def update_autonomous_mode(self, mode_val: str):
        try:
            self.engine.autonomous_manager.settings.mode = AutonomousMode(mode_val)
            self.refresh_abilities_tab()
        except Exception:
            pass

    def update_perching_mode(self, pval: str):
        try:
            self.engine.perch_manager.mode = PerchMode(pval)
        except Exception:
            pass

    def apply_profile(self, prof_id: str):
        prof = BUILTIN_PROFILES.get(prof_id)
        if not prof:
            return
        self.engine.switch_skin(prof.character)
        self.update_scale(prof.scale)
        self.update_mode(prof.behavior_mode)
        self.update_autonomous_mode(prof.autonomous_mode)
        self.update_perching_mode(prof.perching_mode)
        self.toggle_sound(prof.sound_enabled)
        self.update_volume(prof.sound_volume)
        self.toggle_click_through(prof.ghost_mode)
        self.select_character(prof.character)

    def toggle_fusion_lab(self, enabled: bool):
        FusionLab.get_instance().enabled = enabled

    def toggle_sound(self, enabled: bool):
        self.engine.config.set("sound_enabled", enabled)
        self.engine.audio.enabled = enabled

    def update_volume(self, val: float):
        self.lbl_vol.setStringValue_(f"Volume: {int(val * 100)}%")
        self.engine.config.set("sound_volume", float(val))
        self.engine.audio.set_volume(float(val))

    def toggle_autostart(self, enabled: bool):
        MacOSAutostart().set_enabled(enabled)

    def toggle_click_through(self, enabled: bool):
        self.engine.config.set("click_through", enabled)
        self.engine.window.set_click_through(enabled)

    def toggle_low_power(self, enabled: bool):
        self.engine.config.set("low_power_mode", enabled)
        self.engine.target_fps = 30 if enabled else 60
        self.engine.frame_interval_ms = int(1000 / self.engine.target_fps)

    def handle_pomodoro_action(self, action: str):
        if action == "start":
            self.engine.pomodoro.start()
        elif action == "pause":
            self.engine.pomodoro.pause()
        elif action == "reset":
            self.engine.pomodoro.reset()

    def reset_defaults(self):
        self.engine.config.reset_to_defaults()
        self.update_scale(1.0)
        self.update_mode("static")
        self.toggle_sound(True)
        self.update_volume(0.7)
        self.toggle_click_through(False)
        self.toggle_low_power(False)

    def on_preview_tick(self):
        try:
            if not self.isVisible() or self.isMiniaturized():
                return

            if hasattr(self.preview_char, "update"):
                self.preview_char.update(0.033, 0, 0, (0, 0, 200, 200), self.preview_particles, dummy_audio, {})
            self.preview_particles.update()
            self.canvas_view.setNeedsDisplay_(True)

            # Update Overview Summary
            if self.active_tab_index == 0:
                cur_skin = self.engine.character.skin_id.replace("_", " ").title()
                mode_str = self.engine.mode.replace("_", " ").title()
                mood_str = getattr(self.engine.brain.mood_manager.current_mood, "value", "calm").title()
                pomo_st = self.engine.pomodoro.state.title()
                pomo_rem = self.engine.pomodoro.remaining_formatted

                overview_text = (
                    f"🌟 Active Companion:    {cur_skin}\n"
                    f"🧭 Behavior Mode:      {mode_str}\n"
                    f"💭 Current Mood:        {mood_str}\n"
                    f"⏱️ Pomodoro Status:     {pomo_st} ({pomo_rem})"
                )
                self.lbl_overview_summary.setStringValue_(overview_text)

            # Update Pomodoro Timer Display
            if self.active_tab_index in (3, 5):
                pomo_st = self.engine.pomodoro.state.upper()
                pomo_rem = self.engine.pomodoro.remaining_formatted
                if hasattr(self, "lbl_pomo_timer"):
                    self.lbl_pomo_timer.setStringValue_(f"{pomo_rem} - {pomo_st}")

            # Update Developer Telemetry
            if self.active_tab_index in (4, 7):
                cur_skin = self.engine.character.skin_id.upper()
                cur_st = self.engine.character.state
                mode_str = self.engine.mode.upper()
                fps = self.engine.current_fps
                pos_x = int(self.engine.character.x)
                pos_y = int(self.engine.character.y)
                p_count = getattr(self.engine.particles, "particle_count", len(self.engine.particles.particles))
                auto_mode = getattr(self.engine.autonomous_manager.settings.mode, "value", "none").upper()

                info = (
                    f"Active Skin:       {cur_skin}\n"
                    f"State:             {cur_st}\n"
                    f"Behavior Mode:     {mode_str} | Autonomous: {auto_mode}\n"
                    f"Position:          X={pos_x}, Y={pos_y} (Global Display Space)\n"
                    f"Render Engine:     {fps:.0f} FPS (Retina High-DPI Cairo)\n"
                    f"Active Particles:  {p_count}\n"
                    f"Perching Mode:     {getattr(self.engine.perch_manager.mode, 'value', 'none').upper()}"
                )
                self.lbl_telemetry.setStringValue_(info)
        except Exception:
            pass

    def close(self):
        global _control_center_instance
        if hasattr(self, "_timer") and self._timer:
            try:
                self._timer.invalidate()
            except Exception:
                pass
            self._timer = None
        _control_center_instance = None
        import objc
        objc.super(BuddyControlCenterWindow, self).close()

    def windowWillClose_(self, notification):
        global _control_center_instance
        if hasattr(self, "_timer") and self._timer:
            try:
                self._timer.invalidate()
            except Exception:
                pass
            self._timer = None
        _control_center_instance = None


def close_macos_control_center() -> None:
    """Safely tear down and close any open Control Center window and its timers."""
    global _control_center_instance
    if _control_center_instance is not None:
        try:
            if hasattr(_control_center_instance, "_timer") and _control_center_instance._timer:
                try:
                    _control_center_instance._timer.invalidate()
                except Exception:
                    pass
                _control_center_instance._timer = None
            _control_center_instance.close()
        except Exception:
            pass
        _control_center_instance = None


def show_macos_control_center(engine: Any) -> BuddyControlCenterWindow:
    """Instantiate or reveal the frontmost native macOS Buddy Control Center."""
    global _control_center_instance
    AppKit.NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    if _control_center_instance is not None:
        try:
            _control_center_instance.makeKeyAndOrderFront_(None)
            _control_center_instance.orderFrontRegardless()
            return _control_center_instance
        except Exception:
            _control_center_instance = None

    win = BuddyControlCenterWindow.alloc().initWithEngine_(engine)
    win.makeKeyAndOrderFront_(None)
    win.orderFrontRegardless()
    _control_center_instance = win
    return win
