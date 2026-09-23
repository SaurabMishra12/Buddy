"""Native macOS AppKit floating companion window, transient visual effects, and Cairo-to-Quartz rendering pipeline."""

import sys
import math
import random
import cairo
from typing import Tuple, Optional, Callable, Dict, Any

import objc
import AppKit
from Foundation import NSPoint, NSRect, NSSize, NSObject, NSTimer, NSRunLoop, NSRunLoopCommonModes
from Quartz import (
    CGColorSpaceCreateDeviceRGB, CGDataProviderCreateWithData, CGImageCreate,
    CGContextDrawImage, CGContextSaveGState, CGContextRestoreGState,
    CGContextTranslateCTM, CGContextScaleCTM,
    CGBitmapContextCreate, CGBitmapContextCreateImage,
    kCGBitmapByteOrder32Host, kCGImageAlphaPremultipliedFirst
)

from platforms.base import PlatformWindow
from platforms.macos.coordinate import (
    buddy_window_to_appkit_origin, appkit_to_buddy_point,
    get_primary_screen_height, get_virtual_desktop_bounds
)

WIN_SIZE = 180              # 180x180 visual space for character, particles, and effects
HALF_SIZE = WIN_SIZE / 2.0  # 90.0 (Pet center coordinate inside window)

CYAN_GLOW = (0.0, 0.9, 1.0)
BLUE_GLOW = (0.1, 0.45, 1.0)
WHITE_CORE = (1.0, 1.0, 1.0)


# Synthetic Event structures for platform parity with Linux GDK callbacks
class EventProxy:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class ScrollDirection:
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3


# Module-level Objective-C classes (must be registered once at module scope)
class SkyStrikeView(AppKit.NSView):
    def isFlipped(self):
        return True

    def drawRect_(self, rect):
        if not hasattr(self, "_owner") or not self._owner:
            return
        owner = self._owner
        ctx = owner.cairo_ctx
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()
        ctx.restore()

        ctx.set_operator(cairo.OPERATOR_OVER)
        owner.bolt1.draw(ctx)
        owner.bolt2.draw(ctx)
        owner.surface.flush()

        cg_img = CGBitmapContextCreateImage(owner.cg_bitmap_ctx)
        if cg_img:
            if self.layer():
                self.layer().setContents_(cg_img)
            ns_ctx = AppKit.NSGraphicsContext.currentContext().CGContext()
            CGContextSaveGState(ns_ctx)
            CGContextTranslateCTM(ns_ctx, 0, rect.size.height)
            CGContextScaleCTM(ns_ctx, 1.0, -1.0)
            CGContextDrawImage(ns_ctx, rect, cg_img)
            CGContextRestoreGState(ns_ctx)


class SkyStrikeTimerTarget(NSObject):
    def onTick_(self, timer):
        if hasattr(self, "_owner") and self._owner:
            self._owner.on_tick()



class WebRopeView(AppKit.NSView):
    def isFlipped(self):
        return True

    def drawRect_(self, rect):
        if hasattr(self, "_owner") and self._owner:
            self._owner.render_cairo_to_view(rect)


class WorldEffectView(AppKit.NSView):
    """Retina-ready high-performance view for world-space VFX (Getsuga, Cero, Fire, Ice Dragon)."""
    def isFlipped(self):
        return True

    def drawRect_(self, rect):
        if not hasattr(self, "_owner") or not self._owner:
            return
        owner = self._owner
        owner.render_to_view(rect)


class WorldEffectTimerTarget(NSObject):
    def onTick_(self, timer):
        if hasattr(self, "_owner") and self._owner:
            self._owner.on_tick()


class BuddyNSPanel(AppKit.NSPanel):
    """Non-activating floating panel: never steals focus from active apps and never drops behind."""
    def canBecomeKeyWindow(self):
        return False

    def canBecomeMainWindow(self):
        return False

    def destroy(self):
        self.close()


BuddyNSWindow = BuddyNSPanel


class BuddyOverlayView(AppKit.NSView):
    def isFlipped(self):
        return True

    def hitTest_(self, aPoint):
        if not hasattr(self, "overlay_ref") or not self.overlay_ref:
            return None
        overlay = self.overlay_ref
        if overlay.click_through:
            return None

        # Allow instant click pass-through when Option or Command key is pressed
        flags = AppKit.NSEvent.modifierFlags()
        if (flags & AppKit.NSEventModifierFlagOption) or (flags & AppKit.NSEventModifierFlagCommand):
            return None

        local = self.convertPoint_fromView_(aPoint, None)
        dx = local.x - overlay.half_size
        dy = local.y - overlay.half_size
        r = getattr(overlay, "hitbox_radius", 36.0)
        if (dx * dx + dy * dy) <= (r * r):
            return self
        return None

    def drawRect_(self, rect):
        if not hasattr(self, "overlay_ref") or not self.overlay_ref:
            return
        overlay = self.overlay_ref
        ctx = overlay.cairo_ctx
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()
        ctx.restore()

        ctx.set_operator(cairo.OPERATOR_OVER)
        if overlay.on_draw_cb:
            try:
                overlay.on_draw_cb(self, ctx)
            except Exception:
                pass
        overlay.surface.flush()

        cg_img = None
        if hasattr(overlay, "cg_bitmap_ctx") and overlay.cg_bitmap_ctx:
            cg_img = CGBitmapContextCreateImage(overlay.cg_bitmap_ctx)
        elif hasattr(overlay, "surface"):
            data = bytes(overlay.surface.get_data())
            provider = CGDataProviderCreateWithData(None, data, len(data), None)
            cg_img = CGImageCreate(
                overlay.pixel_w, overlay.pixel_h, 8, 32,
                overlay.stride, overlay.color_space,
                kCGBitmapByteOrder32Host | kCGImageAlphaPremultipliedFirst,
                provider, None, False, 0
            )

        if cg_img:
            ns_ctx = AppKit.NSGraphicsContext.currentContext().CGContext()
            CGContextSaveGState(ns_ctx)
            CGContextTranslateCTM(ns_ctx, 0, rect.size.height)
            CGContextScaleCTM(ns_ctx, 1.0, -1.0)
            CGContextDrawImage(ns_ctx, rect, cg_img)
            CGContextRestoreGState(ns_ctx)

    def mouseDown_(self, event):
        if not hasattr(self, "overlay_ref") or not self.overlay_ref:
            return
        try:
            loc = self.convertPoint_fromView_(event.locationInWindow(), None)
            ev = EventProxy(
                button=1,
                x=loc.x,
                y=loc.y,
                type=5 if event.clickCount() >= 2 else 4
            )
            if self.overlay_ref.on_button_press_cb:
                self.overlay_ref.on_button_press_cb(self, ev)
        except Exception as e:
            print(f"[Buddy Overlay] Error in mouseDown_: {e}", file=sys.stderr)

    def mouseDragged_(self, event):
        if not hasattr(self, "overlay_ref") or not self.overlay_ref:
            return
        try:
            loc = self.convertPoint_fromView_(event.locationInWindow(), None)
            ev = EventProxy(x=loc.x, y=loc.y)
            if self.overlay_ref.on_motion_cb:
                self.overlay_ref.on_motion_cb(self, ev)
        except Exception as e:
            print(f"[Buddy Overlay] Error in mouseDragged_: {e}", file=sys.stderr)

    def mouseUp_(self, event):
        if not hasattr(self, "overlay_ref") or not self.overlay_ref:
            return
        try:
            loc = self.convertPoint_fromView_(event.locationInWindow(), None)
            ev = EventProxy(button=1, x=loc.x, y=loc.y)
            if self.overlay_ref.on_button_release_cb:
                self.overlay_ref.on_button_release_cb(self, ev)
        except Exception as e:
            print(f"[Buddy Overlay] Error in mouseUp_: {e}", file=sys.stderr)

    def rightMouseDown_(self, event):
        if not hasattr(self, "overlay_ref") or not self.overlay_ref:
            return
        try:
            loc = self.convertPoint_fromView_(event.locationInWindow(), None)
            ev = EventProxy(button=3, x=loc.x, y=loc.y, ns_event=event)
            if self.overlay_ref.on_button_press_cb:
                self.overlay_ref.on_button_press_cb(self, ev)
        except Exception as e:
            print(f"[Buddy Overlay] Error in rightMouseDown_: {e}", file=sys.stderr)

    def otherMouseDown_(self, event):
        if not hasattr(self, "overlay_ref") or not self.overlay_ref:
            return
        try:
            if event.buttonNumber() == 2:
                loc = self.convertPoint_fromView_(event.locationInWindow(), None)
                ev = EventProxy(button=2, x=loc.x, y=loc.y)
                if self.overlay_ref.on_button_press_cb:
                    self.overlay_ref.on_button_press_cb(self, ev)
        except Exception as e:
            print(f"[Buddy Overlay] Error in otherMouseDown_: {e}", file=sys.stderr)

    def scrollWheel_(self, event):
        if not hasattr(self, "overlay_ref") or not self.overlay_ref:
            return
        try:
            dy = event.deltaY()
            direction = ScrollDirection.UP if dy > 0 else ScrollDirection.DOWN
            ev = EventProxy(direction=direction, delta_y=dy)
            if self.overlay_ref.on_scroll_cb:
                self.overlay_ref.on_scroll_cb(self, ev)
        except Exception as e:
            print(f"[Buddy Overlay] Error in scrollWheel_: {e}", file=sys.stderr)



class TransientLightning:
    """Branching lightning bolt for transient sky strikes."""
    def __init__(self, start_x, start_y, end_x, end_y, duration=22, intensity=1.0):
        self.points = self._gen(start_x, start_y, end_x, end_y)
        self.branches = []
        self.life = duration
        self.age = 0
        self.intensity = intensity

        if len(self.points) > 4:
            for _ in range(random.randint(2, 4)):
                b_idx = random.randint(2, len(self.points) - 2)
                bx, by = self.points[b_idx]
                ang = math.atan2(end_y - start_y, end_x - start_x) + random.uniform(-0.85, 0.85)
                blen = math.hypot(end_x - start_x, end_y - start_y) * random.uniform(0.3, 0.5)
                b_end_x = bx + math.cos(ang) * blen
                b_end_y = by + math.sin(ang) * blen
                self.branches.append(self._gen(bx, by, b_end_x, b_end_y, iterations=2))

    def _gen(self, x1, y1, x2, y2, iterations=3):
        pts = [(x1, y1), (x2, y2)]
        for _ in range(iterations):
            new_pts = []
            for i in range(len(pts) - 1):
                p1, p2 = pts[i], pts[i + 1]
                mx = (p1[0] + p2[0]) / 2.0
                my = (p1[1] + p2[1]) / 2.0
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                d = math.hypot(dx, dy)
                disp = (random.random() - 0.5) * d * 0.45
                nx = -dy / (d + 1e-4)
                ny = dx / (d + 1e-4)
                mx += nx * disp
                my += ny * disp
                new_pts.append(p1)
                new_pts.append((mx, my))
            new_pts.append(pts[-1])
            pts = new_pts
        return pts

    def update(self):
        self.age += 1
        return self.age < self.life

    def draw(self, ctx):
        fade = (1.0 - (self.age / self.life)) * self.intensity
        if fade <= 0:
            return

        all_paths = [self.points] + self.branches
        ctx.save()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)

        for path in all_paths:
            if len(path) < 2:
                continue

            def trace():
                ctx.new_path()
                ctx.move_to(path[0][0], path[0][1])
                for pt in path[1:]:
                    ctx.line_to(pt[0], pt[1])

            trace()
            ctx.set_line_width(8.0)
            ctx.set_source_rgba(BLUE_GLOW[0], BLUE_GLOW[1], BLUE_GLOW[2], 0.35 * fade)
            ctx.stroke()

            trace()
            ctx.set_line_width(4.0)
            ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], 0.75 * fade)
            ctx.stroke()

            trace()
            ctx.set_line_width(1.8)
            ctx.set_source_rgba(WHITE_CORE[0], WHITE_CORE[1], WHITE_CORE[2], 0.95 * fade)
            ctx.stroke()

        ctx.restore()


class MacOSSkyStrikeWindow:
    """Transient, self-destroying narrow window for colossal lightning strikes from screen top."""

    def __init__(self, target_cx: float, target_cy: float):
        self.width = 240
        self.height = max(120, int(target_cy) + 30)
        primary_h = get_primary_screen_height()

        ax = float(target_cx - self.width / 2.0)
        ay = float(primary_h - self.height)

        frame = NSRect(NSPoint(ax, ay), NSSize(self.width, self.height))
        self.window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            AppKit.NSWindowStyleMaskBorderless,
            AppKit.NSBackingStoreBuffered,
            False
        )
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(AppKit.NSColor.clearColor())
        self.window.setHasShadow_(False)
        self.window.setLevel_(AppKit.NSFloatingWindowLevel)
        self.window.setIgnoresMouseEvents_(True)
        self.window.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces |
            AppKit.NSWindowCollectionBehaviorStationary |
            AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        mid_x = self.width / 2.0
        self.bolt1 = TransientLightning(mid_x, 0.0, mid_x, float(target_cy), duration=22, intensity=1.0)
        self.bolt2 = TransientLightning(
            mid_x + random.uniform(-25, 25),
            0.0,
            mid_x + random.uniform(-10, 10),
            float(target_cy) * 0.7,
            duration=16,
            intensity=0.7
        )
        self.frames = 0

        self.stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, self.width)
        self.pixel_buf = bytearray(self.stride * self.height)
        self.surface = cairo.ImageSurface.create_for_data(
            self.pixel_buf, cairo.FORMAT_ARGB32, self.width, self.height, self.stride
        )
        self.cairo_ctx = cairo.Context(self.surface)
        self.color_space = CGColorSpaceCreateDeviceRGB()
        self.cg_bitmap_ctx = CGBitmapContextCreate(
            self.pixel_buf, self.width, self.height, 8, self.stride, self.color_space,
            kCGBitmapByteOrder32Host | kCGImageAlphaPremultipliedFirst
        )

        self.view = SkyStrikeView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(self.width, self.height)))
        self.view._owner = self
        self.view.setWantsLayer_(True)
        self.window.setContentView_(self.view)
        self.window.orderFrontRegardless()

        self._timer_target = SkyStrikeTimerTarget.alloc().init()
        self._timer_target._owner = self

        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.016, self._timer_target, "onTick:", None, True
        )
        NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer, NSRunLoopCommonModes)

    def on_tick(self):
        self.frames += 1
        a1 = self.bolt1.update()
        a2 = self.bolt2.update()
        if (not a1 and not a2) or self.frames > 35:
            if self.timer:
                self.timer.invalidate()
                self.timer = None
            self.window.close()
            return
        self.view.setNeedsDisplay_(True)


class MacOSWorldEffectWindow:
    """Transient, high-DPI desktop overlay window for expansive Bleach VFX (500-1500+ px).
    Decouples visual effect footprint from the character's local ~180px window.
    Reuses a single pooled instance across abilities to avoid redundant window creation.
    """
    _active_instance: Optional['MacOSWorldEffectWindow'] = None

    @classmethod
    def trigger(
        cls,
        effect_type: str,
        start_x: float,
        start_y: float,
        target_x: float,
        target_y: float,
        **kwargs
    ) -> 'MacOSWorldEffectWindow':
        inst = cls._active_instance
        if inst is not None and inst.window is not None:
            inst.reset_and_show(effect_type, start_x, start_y, target_x, target_y, **kwargs)
            return inst
        inst = cls(effect_type, start_x, start_y, target_x, target_y, **kwargs)
        cls._active_instance = inst
        return inst

    def __init__(
        self,
        effect_type: str,
        start_x: float,
        start_y: float,
        target_x: float,
        target_y: float,
        **kwargs
    ):
        self._init_state(effect_type, start_x, start_y, target_x, target_y, **kwargs)

        frame = NSRect(NSPoint(self.appkit_x, self.appkit_y), NSSize(self.width, self.height))
        self.window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            AppKit.NSWindowStyleMaskBorderless,
            AppKit.NSBackingStoreBuffered,
            False
        )
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(AppKit.NSColor.clearColor())
        self.window.setHasShadow_(False)
        self.window.setLevel_(AppKit.NSFloatingWindowLevel)
        self.window.setIgnoresMouseEvents_(True)
        self.window.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces |
            AppKit.NSWindowCollectionBehaviorStationary |
            AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        self._init_surface()

        self.view = WorldEffectView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(self.width, self.height)))
        self.view._owner = self
        self.view.setWantsLayer_(True)
        self.window.setContentView_(self.view)
        self.window.orderFrontRegardless()

        self._timer_target = WorldEffectTimerTarget.alloc().init()
        self._timer_target._owner = self

        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.016, self._timer_target, "onTick:", None, True
        )
        NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer, NSRunLoopCommonModes)

    def _init_state(self, effect_type: str, start_x: float, start_y: float, target_x: float, target_y: float, **kwargs):
        self.effect_type = effect_type.lower()
        self.start_bx = float(start_x)
        self.start_by = float(start_y)
        self.target_bx = float(target_x)
        self.target_by = float(target_y)
        self.kwargs = kwargs

        # Dynamic world-space bounding box with generous padding
        pad = 260.0
        min_bx = min(self.start_bx, self.target_bx) - pad
        max_bx = max(self.start_bx, self.target_bx) + pad
        min_by = min(self.start_by, self.target_by) - pad
        max_by = max(self.start_by, self.target_by) + pad

        self.width = max(550, min(1800, int(max_bx - min_bx)))
        self.height = max(420, min(1400, int(max_by - min_by)))
        self.min_bx = min_bx
        self.min_by = min_by

        primary_h = get_primary_screen_height()
        self.appkit_x = float(min_bx)
        self.appkit_y = float(primary_h - (min_by + self.height))
        self.frames = 0
        self.max_frames = int(self.kwargs.get("duration_frames", 42))

    def _init_surface(self):
        self.stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, self.width)
        self.pixel_buf = bytearray(self.stride * self.height)
        self.surface = cairo.ImageSurface.create_for_data(
            self.pixel_buf, cairo.FORMAT_ARGB32, self.width, self.height, self.stride
        )
        self.cairo_ctx = cairo.Context(self.surface)
        self.color_space = CGColorSpaceCreateDeviceRGB()
        self.cg_bitmap_ctx = CGBitmapContextCreate(
            self.pixel_buf, self.width, self.height, 8, self.stride, self.color_space,
            kCGBitmapByteOrder32Host | kCGImageAlphaPremultipliedFirst
        )

    def reset_and_show(self, effect_type: str, start_x: float, start_y: float, target_x: float, target_y: float, **kwargs):
        if self.timer:
            try:
                self.timer.invalidate()
            except Exception:
                pass
            self.timer = None

        old_w, old_h = self.width, self.height
        self._init_state(effect_type, start_x, start_y, target_x, target_y, **kwargs)

        if self.width != old_w or self.height != old_h:
            self._init_surface()
            self.view.setFrame_(NSRect(NSPoint(0, 0), NSSize(self.width, self.height)))
            self.window.setFrame_display_(NSRect(NSPoint(self.appkit_x, self.appkit_y), NSSize(self.width, self.height)), True)
        else:
            self.window.setFrameOrigin_(NSPoint(self.appkit_x, self.appkit_y))

        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.016, self._timer_target, "onTick:", None, True
        )
        NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer, NSRunLoopCommonModes)
        self.window.orderFrontRegardless()
        self.view.setNeedsDisplay_(True)

    def on_tick(self):
        self.frames += 1
        if self.frames >= self.max_frames:
            if self.timer:
                self.timer.invalidate()
                self.timer = None
            self.window.orderOut_(None)
            return
        self.view.setNeedsDisplay_(True)

    def destroy(self):
        if self.timer:
            try:
                self.timer.invalidate()
            except Exception:
                pass
            self.timer = None
        if self.window:
            try:
                self.window.close()
            except Exception:
                pass
            self.window = None
        if MacOSWorldEffectWindow._active_instance is self:
            MacOSWorldEffectWindow._active_instance = None

    def render_to_view(self, rect):
        ctx = self.cairo_ctx
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()
        ctx.restore()

        ctx.save()
        self.draw_effect(ctx)
        ctx.restore()
        self.surface.flush()

        cg_img = None
        if hasattr(self, "cg_bitmap_ctx") and self.cg_bitmap_ctx:
            cg_img = CGBitmapContextCreateImage(self.cg_bitmap_ctx)
        elif hasattr(self, "surface"):
            data = bytes(self.surface.get_data())
            provider = CGDataProviderCreateWithData(None, data, len(data), None)
            cg_img = CGImageCreate(
                self.width, self.height, 8, 32, self.stride, self.color_space,
                kCGBitmapByteOrder32Host | kCGImageAlphaPremultipliedFirst,
                provider, None, False, 0
            )

        if cg_img:
            ns_ctx = AppKit.NSGraphicsContext.currentContext().CGContext()
            CGContextSaveGState(ns_ctx)
            CGContextTranslateCTM(ns_ctx, 0, rect.size.height)
            CGContextScaleCTM(ns_ctx, 1.0, -1.0)
            CGContextDrawImage(ns_ctx, rect, cg_img)
            CGContextRestoreGState(ns_ctx)

    def draw_effect(self, ctx: cairo.Context):
        p = self.frames / float(max(1, self.max_frames))
        sx = self.start_bx - self.min_bx
        sy = self.start_by - self.min_by
        tx = self.target_bx - self.min_bx
        ty = self.target_by - self.min_by

        ef = self.effect_type
        if "getsuga" in ef:
            self._draw_getsuga(ctx, p, sx, sy, tx, ty)
        elif "senkei" in ef:
            self._draw_senkei(ctx, p, sx, sy, tx, ty)
        elif "gokei" in ef:
            self._draw_gokei(ctx, p, sx, sy, tx, ty)
        elif "senbonzakura" in ef or "kageyoshi" in ef or "petal" in ef:
            self._draw_senbonzakura(ctx, p, sx, sy, tx, ty)
        elif "kyokujitsujin" in ef or ("ryujin" in ef and self.kwargs.get("is_bankai", False)):
            self._draw_kyokujitsujin(ctx, p, sx, sy, tx, ty)
        elif "ryujin" in ef or "flame" in ef or "fire" in ef:
            self._draw_ryujin_jakka(ctx, p, sx, sy, tx, ty)
        elif "hyorinmaru" in ef or "ice_dragon" in ef:
            self._draw_hyorinmaru(ctx, p, sx, sy, tx, ty)
        elif "hakuren" in ef:
            self._draw_hakuren(ctx, p, sx, sy, tx, ty)
        elif "hakka_no_togame" in ef:
            self._draw_hakka_no_togame(ctx, p, sx, sy, tx, ty)
        elif "tsukishiro" in ef or "sode_no_shirayuki" in ef or "frost" in ef:
            if self.kwargs.get("is_bankai", False):
                self._draw_hakka_no_togame(ctx, p, sx, sy, tx, ty)
            else:
                self._draw_tsukishiro(ctx, p, sx, sy, tx, ty)
        elif "kyoka" in ef or "illusion" in ef:
            self._draw_kyoka_suigetsu(ctx, p, sx, sy, tx, ty)
        elif "kurohitsugi" in ef or "coffin" in ef:
            self._draw_kurohitsugi(ctx, p, sx, sy, tx, ty)
        elif "cero" in ef:
            self._draw_cero_oscuras(ctx, p, sx, sy, tx, ty)
        elif "lanza" in ef:
            self._draw_lanza(ctx, p, sx, sy, tx, ty)
        else:
            self._draw_getsuga(ctx, p, sx, sy, tx, ty)

    def _draw_getsuga(self, ctx: cairo.Context, p: float, sx: float, sy: float, tx: float, ty: float):
        """Ichigo's massive travelling crescent getsuga tensho:
        - Shikai: pale cyan-blue crescent wave, moderate width, clean edge.
        - Bankai: black core with a vivid crimson/red rim-light outline (not flat obsidian).
        """
        is_bankai = bool(self.kwargs.get("is_bankai", False))
        alpha = math.sin(p * math.pi)

        # Travel along trajectory from start to target
        dist_x = tx - sx
        dist_y = ty - sy
        dist = math.hypot(dist_x, dist_y)
        if dist < 1.0:
            dist_x, dist_y, dist = 1.0, 0.0, 1.0
        nx, ny = dist_x / dist, dist_y / dist
        cur_dist = dist * (0.1 + 0.9 * p)
        cx = sx + nx * cur_dist
        cy = sy + ny * cur_dist
        angle = math.atan2(ny, nx)

        ctx.save()
        ctx.translate(cx, cy)
        ctx.rotate(angle)

        arc_r = 135.0 + 20.0 * math.sin(p * math.pi)

        if is_bankai:
            # Bankai: Black core with crimson/red rim-light outline
            ctx.save()
            ctx.set_source_rgba(0.95, 0.08, 0.15, 0.88 * alpha)
            ctx.set_line_width(26.0)
            ctx.arc(0, 0, arc_r, -0.65 * math.pi, 0.65 * math.pi)
            ctx.stroke()
            ctx.restore()

            ctx.save()
            ctx.set_source_rgba(0.02, 0.02, 0.03, 0.98 * alpha)
            ctx.set_line_width(14.0)
            ctx.arc(0, 0, arc_r, -0.62 * math.pi, 0.62 * math.pi)
            ctx.stroke()
            ctx.restore()

            ctx.save()
            ctx.set_source_rgba(1.0, 0.25, 0.3, 0.95 * alpha)
            ctx.set_line_width(3.5)
            ctx.arc(0, 0, arc_r + 5.0, -0.58 * math.pi, 0.58 * math.pi)
            ctx.stroke()
            ctx.restore()

            for trail_i in range(1, 4):
                t_offset = trail_i * 24.0
                t_alpha = alpha * (0.6 / trail_i)
                ctx.save()
                ctx.set_source_rgba(0.85, 0.08, 0.12, t_alpha)
                ctx.set_line_width(7.0)
                ctx.arc(-t_offset, 0, arc_r * (1.0 - trail_i * 0.08), -0.5 * math.pi, 0.5 * math.pi)
                ctx.stroke()
                ctx.restore()
        else:
            ctx.save()
            ctx.set_source_rgba(0.2, 0.72, 1.0, 0.55 * alpha)
            ctx.set_line_width(20.0)
            ctx.arc(0, 0, arc_r, -0.62 * math.pi, 0.62 * math.pi)
            ctx.stroke()
            ctx.restore()

            ctx.save()
            ctx.set_source_rgba(0.88, 0.96, 1.0, 0.95 * alpha)
            ctx.set_line_width(9.0)
            ctx.arc(0, 0, arc_r, -0.60 * math.pi, 0.60 * math.pi)
            ctx.stroke()
            ctx.restore()

            ctx.save()
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.98 * alpha)
            ctx.set_line_width(3.0)
            ctx.arc(0, 0, arc_r, -0.55 * math.pi, 0.55 * math.pi)
            ctx.stroke()
            ctx.restore()

        ctx.restore()

    def _draw_senkei(self, ctx: cairo.Context, p: float, sx: float, sy: float, tx: float, ty: float):
        """Byakuya's Senkei: four rotating rows of solid glowing blades forming a rectangular cage/cylinder."""
        alpha = math.sin(p * math.pi)
        cx, cy = tx, ty
        rot_angle = p * 2.5

        ctx.save()
        ctx.translate(cx, cy)

        cage_rx = 180.0
        cage_ry = 110.0
        num_blades_per_row = 8
        blade_h = 70.0
        blade_w = 5.0

        for row in range(4):
            row_y_offset = (row - 1.5) * 32.0
            row_rot = rot_angle + (row * 0.35)
            for b in range(num_blades_per_row):
                b_ang = row_rot + (b / float(num_blades_per_row)) * 2 * math.pi
                bx = cage_rx * math.cos(b_ang)
                by = cage_ry * math.sin(b_ang) + row_y_offset
                b_depth = (math.sin(b_ang) + 1.0) * 0.5
                b_alpha = alpha * (0.4 + 0.6 * b_depth)

                ctx.save()
                ctx.translate(bx, by)
                ctx.set_source_rgba(1.0, 0.45, 0.75, 0.75 * b_alpha)
                ctx.rectangle(-blade_w, -blade_h * 0.5, blade_w * 2, blade_h)
                ctx.fill()
                ctx.set_source_rgba(1.0, 0.95, 1.0, 0.95 * b_alpha)
                ctx.rectangle(-blade_w * 0.4, -blade_h * 0.45, blade_w * 0.8, blade_h * 0.9)
                ctx.fill()
                ctx.restore()

        ctx.save()
        ctx.set_source_rgba(1.0, 0.55, 0.8, 0.45 * alpha)
        ctx.set_line_width(2.5)
        for ry_bound in [-60.0, 60.0]:
            ctx.save()
            ctx.translate(0, ry_bound)
            ctx.scale(1.0, cage_ry / cage_rx)
            ctx.arc(0, 0, cage_rx, 0, 2 * math.pi)
            ctx.stroke()
            ctx.restore()
        ctx.restore()

        ctx.restore()

    def _draw_gokei(self, ctx: cairo.Context, p: float, sx: float, sy: float, tx: float, ty: float):
        """Byakuya's Gōkei: petals swarm into a sphere around the target, then collapse inward to a point."""
        alpha = math.sin(p * math.pi)
        cx, cy = tx, ty

        if p < 0.4:
            phase_p = p / 0.4
            sphere_r = 320.0 * phase_p
        elif p < 0.75:
            sphere_r = 320.0
        else:
            collapse_p = (p - 0.75) / 0.25
            sphere_r = 320.0 * (1.0 - collapse_p)

        total_petals = 180
        ctx.save()
        ctx.translate(cx, cy)

        for i in range(total_petals):
            seed = i * 0.381966
            phi = math.acos(max(-1.0, min(1.0, 1.0 - 2.0 * (i / float(total_petals)))))
            theta = seed * 6.283 + (p * 5.0)

            px = sphere_r * math.sin(phi) * math.cos(theta)
            py = sphere_r * math.cos(phi) * 0.7 + (sphere_r * math.sin(phi) * math.sin(theta) * 0.3)

            pet_a = alpha * (0.5 + 0.5 * math.sin(phi))
            ctx.save()
            ctx.translate(px, py)
            ctx.rotate(theta)
            ctx.set_source_rgba(1.0, 0.48, 0.76, pet_a)
            ctx.scale(1.0, 0.5)
            ctx.arc(0, 0, 6.0, 0, 6.283)
            ctx.fill()
            ctx.restore()

        if p >= 0.75:
            flash_p = (p - 0.75) / 0.25
            flash_alpha = math.sin(flash_p * math.pi)
            ctx.save()
            ctx.set_source_rgba(1.0, 0.9, 1.0, 0.85 * flash_alpha)
            ctx.arc(0, 0, 50.0 * (1.0 - flash_p), 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

        ctx.restore()

    def _draw_senbonzakura(self, ctx: cairo.Context, p: float, sx: float, sy: float, tx: float, ty: float):
        """Byakuya's Senbonzakura Kageyoshi: twin sword pillars + 800px swirling petal vortex."""
        alpha = math.sin(p * math.pi)

        if p < 0.6:
            pillar_p = p / 0.6
            h = 240.0 * (1.0 - pillar_p * 0.5)
            w = 16.0
            for side in (-120.0, 120.0):
                px = sx + side
                py = sy + 40.0 - h * pillar_p
                ctx.save()
                ctx.set_source_rgba(0.9, 0.95, 1.0, 0.7 * (1.0 - pillar_p))
                ctx.rectangle(px - w / 2, py, w, h)
                ctx.fill()
                ctx.restore()

        total_petals = 160
        max_vortex_r = 380.0 * min(1.0, p * 1.5)
        for i in range(total_petals):
            seed = i * 0.381966
            frac = (i / float(total_petals))
            r = max_vortex_r * math.sqrt(frac)
            theta = seed * 6.283 + (p * 4.0) + (frac * 3.0)

            pet_x = sx + r * math.cos(theta)
            pet_y = sy + (r * 0.45) * math.sin(theta)

            pet_a = alpha * (0.4 + 0.6 * math.sin((frac + p) * math.pi))
            ctx.save()
            ctx.translate(pet_x, pet_y)
            ctx.rotate(theta + seed * 2.0)
            ctx.set_source_rgba(1.0, 0.52, 0.76, pet_a)
            ctx.scale(1.0, 0.55)
            ctx.arc(0, 0, 7.0, 0, 6.283)
            ctx.fill()
            ctx.restore()

    def _draw_kyokujitsujin(self, ctx: cairo.Context, p: float, sx: float, sy: float, tx: float, ty: float):
        """Yamamoto's Zanka no Tachi, East: Kyokujitsujin (Rising Sun's Edge).
        Flame concentrates purely into the blade edge, instant white-hot incineration on contact.
        """
        alpha = math.sin(p * math.pi)
        dist_x = tx - sx
        dist_y = ty - sy
        dist = math.hypot(dist_x, dist_y)
        if dist < 1.0:
            dist_x, dist_y, dist = 1.0, 0.0, 1.0
        nx, ny = dist_x / dist, dist_y / dist

        cur_reach = dist * min(1.0, p * 1.6)
        ex = sx + nx * cur_reach
        ey = sy + ny * cur_reach

        ctx.save()
        ctx.set_source_rgba(0.08, 0.02, 0.02, 0.7 * alpha)
        ctx.set_line_width(12.0)
        ctx.move_to(sx, sy)
        ctx.line_to(ex, ey)
        ctx.stroke()

        ctx.set_source_rgba(1.0, 0.35, 0.05, 0.85 * alpha)
        ctx.set_line_width(6.0)
        ctx.move_to(sx, sy)
        ctx.line_to(ex, ey)
        ctx.stroke()

        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.98 * alpha)
        ctx.set_line_width(2.5)
        ctx.move_to(sx, sy)
        ctx.line_to(ex, ey)
        ctx.stroke()

        if p > 0.4:
            contact_p = (p - 0.4) / 0.6
            burst_r = 65.0 * math.sin(contact_p * math.pi)
            ctx.save()
            ctx.translate(tx, ty)
            ctx.set_source_rgba(1.0, 0.4, 0.05, 0.45 * alpha)
            ctx.arc(0, 0, burst_r * 1.4, 0, 2 * math.pi)
            ctx.fill()
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95 * alpha)
            ctx.arc(0, 0, burst_r * 0.6, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

        ctx.restore()

    def _draw_ryujin_jakka(self, ctx: cairo.Context, p: float, sx: float, sy: float, tx: float, ty: float):
        """Yamamoto's sweeping fire wave extending across 800-1000px."""
        alpha = math.sin(p * math.pi)
        dx = tx - sx
        facing_dir = 1.0 if dx >= 0 else -1.0
        wave_front = 750.0 * p * facing_dir

        num_tongues = 14
        for i in range(num_tongues):
            t_frac = i / float(num_tongues)
            bx = sx + (wave_front * t_frac)
            by = sy + (i - num_tongues / 2.0) * 22.0
            flame_h = 140.0 * (1.0 - t_frac * 0.4) * (0.8 + 0.4 * math.sin(p * 10.0 + i))

            ctx.save()
            ctx.set_source_rgba(1.0, 0.35, 0.05, 0.8 * alpha)
            ctx.move_to(bx - 35.0, by + 20.0)
            ctx.curve_to(bx, by - flame_h * 0.5, bx + 10.0, by - flame_h, bx + 35.0, by + 20.0)
            ctx.close_path()
            ctx.fill()
            ctx.restore()

            ctx.save()
            ctx.set_source_rgba(1.0, 0.88, 0.2, 0.9 * alpha)
            ctx.move_to(bx - 18.0, by + 20.0)
            ctx.curve_to(bx, by - flame_h * 0.4, bx + 6.0, by - flame_h * 0.7, bx + 18.0, by + 20.0)
            ctx.close_path()
            ctx.fill()
            ctx.restore()

    def _draw_hyorinmaru(self, ctx: cairo.Context, p: float, sx: float, sy: float, tx: float, ty: float):
        """Hitsugaya's soaring crystalline ice dragon with diamond mist."""
        alpha = math.sin(p * math.pi)
        dx = tx - sx
        dy = ty - sy
        dist = math.hypot(dx, dy)
        if dist < 1.0:
            dist = 1.0
            dx, dy = 1.0, 0.0
        nx, ny = dx / dist, dy / dist

        segments = 22
        body_points = []
        for i in range(segments):
            frac = i / float(segments)
            seg_p = max(0.0, p - (1.0 - frac) * 0.4)
            wave = math.sin(seg_p * 8.0 + frac * 4.0) * 45.0
            px = sx + (dx * seg_p) - (ny * wave)
            py = sy + (dy * seg_p) + (nx * wave)
            body_points.append((px, py, frac))

        for px, py, frac in body_points:
            seg_r = (18.0 + 14.0 * frac) * alpha
            ctx.save()
            ctx.translate(px, py)
            ctx.set_source_rgba(0.45, 0.85, 1.0, 0.85 * alpha)
            ctx.rectangle(-seg_r, -seg_r, seg_r * 2, seg_r * 2)
            ctx.fill()

            ctx.set_source_rgba(0.95, 0.98, 1.0, 0.95 * alpha)
            ctx.rectangle(-seg_r * 0.5, -seg_r * 0.5, seg_r, seg_r)
            ctx.fill()
            ctx.restore()

    def _draw_hakuren(self, ctx: cairo.Context, p: float, sx: float, sy: float, tx: float, ty: float):
        """Rukia's Next Dance, Hakuren: directional wave-front of ice fired forward in a widening cone."""
        alpha = math.sin(p * math.pi)
        dist_x = tx - sx
        dist_y = ty - sy
        dist = math.hypot(dist_x, dist_y)
        if dist < 1.0:
            dist_x, dist_y, dist = 1.0, 0.0, 1.0
        nx, ny = dist_x / dist, dist_y / dist
        perp_x, perp_y = -ny, nx

        front_dist = dist * (0.2 + 0.8 * p)
        cx = sx + nx * front_dist
        cy = sy + ny * front_dist

        ctx.save()
        cone_width = 160.0 * (0.2 + 0.8 * p)
        num_spikes = 16
        for i in range(num_spikes):
            frac = (i / float(num_spikes - 1)) - 0.5
            spike_x = cx + perp_x * (frac * cone_width) + (random.Random(i).uniform(-10, 10))
            spike_y = cy + perp_y * (frac * cone_width) + (random.Random(i).uniform(-10, 10))
            length = (45.0 + 20.0 * (1.0 - abs(frac))) * alpha

            ctx.save()
            ctx.set_source_rgba(0.75, 0.92, 1.0, 0.85 * alpha)
            ctx.set_line_width(3.0)
            ctx.move_to(spike_x - nx * length, spike_y - ny * length)
            ctx.line_to(spike_x, spike_y)
            ctx.stroke()

            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95 * alpha)
            ctx.set_line_width(1.2)
            ctx.move_to(spike_x - nx * length * 0.4, spike_y - ny * length * 0.4)
            ctx.line_to(spike_x, spike_y)
            ctx.stroke()
            ctx.restore()

        ctx.save()
        ctx.set_source_rgba(0.85, 0.96, 1.0, 0.35 * alpha)
        ctx.new_path()
        ctx.move_to(sx, sy)
        ctx.line_to(cx + perp_x * (cone_width * 0.5), cy + perp_y * (cone_width * 0.5))
        ctx.line_to(cx - perp_x * (cone_width * 0.5), cy - perp_y * (cone_width * 0.5))
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        ctx.restore()

    def _draw_hakka_no_togame(self, ctx: cairo.Context, p: float, sx: float, sy: float, tx: float, ty: float):
        """Rukia's Ultimate Hakka no Togame: screen-space frost vignette pulse and absolute zero light pillar."""
        alpha = math.sin(p * math.pi)
        cx, cy = tx, ty

        ctx.save()
        pat = cairo.RadialGradient(cx, cy, 50.0, cx, cy, float(self.width) * 0.7)
        pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.05 * alpha)
        pat.add_color_stop_rgba(0.6, 0.85, 0.95, 1.0, 0.25 * alpha)
        pat.add_color_stop_rgba(1.0, 0.75, 0.90, 1.0, 0.55 * alpha)
        ctx.set_source(pat)
        ctx.rectangle(0, 0, self.width, self.height)
        ctx.fill()

        mandala_r = 340.0 * min(1.0, p * 1.5)
        ctx.save()
        ctx.set_source_rgba(0.95, 0.98, 1.0, 0.9 * alpha)
        ctx.set_line_width(4.5)
        ctx.arc(cx, cy, mandala_r, 0, 6.283)
        ctx.stroke()
        ctx.set_line_width(2.0)
        ctx.arc(cx, cy, mandala_r * 0.65, 0, 6.283)
        ctx.stroke()
        ctx.restore()

        pillar_h = float(self.height) * alpha
        ctx.save()
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.45 * alpha)
        ctx.rectangle(cx - mandala_r * 0.45, cy - pillar_h, mandala_r * 0.9, pillar_h)
        ctx.fill()
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.85 * alpha)
        ctx.rectangle(cx - mandala_r * 0.15, cy - pillar_h, mandala_r * 0.3, pillar_h)
        ctx.fill()
        ctx.restore()

        ctx.restore()

    def _draw_tsukishiro(self, ctx: cairo.Context, p: float, sx: float, sy: float, tx: float, ty: float):
        """Rukia's First Dance, Tsukishiro: circular frost ring expanding outward from the ground up."""
        alpha = math.sin(p * math.pi)
        cx, cy = tx, ty

        ring_p = min(1.0, p / 0.4)
        mandala_r = 280.0 * ring_p

        ctx.save()
        ctx.set_source_rgba(0.95, 0.98, 1.0, 0.85 * alpha)
        ctx.set_line_width(4.0)
        ctx.arc(cx, cy, mandala_r, 0, 6.283)
        ctx.stroke()

        ctx.set_line_width(2.0)
        ctx.arc(cx, cy, mandala_r * 0.65, 0, 6.283)
        ctx.stroke()

        if p > 0.25:
            pillar_p = min(1.0, (p - 0.25) / 0.35)
            pillar_h = 550.0 * pillar_p * alpha
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.40 * alpha)
            ctx.rectangle(cx - mandala_r * 0.45, cy - pillar_h, mandala_r * 0.9, pillar_h)
            ctx.fill()

        ctx.restore()

    def _draw_kyoka_suigetsu(self, ctx: cairo.Context, p: float, sx: float, sy: float, tx: float, ty: float):
        """Aizen's shattered mirror complete hypnosis illusion."""
        alpha = math.sin(p * math.pi)
        shatter_r = 300.0 * min(1.0, p * 1.6)

        # Prismatic glass fracture lines
        ctx.save()
        ctx.translate(sx, sy)
        ctx.set_source_rgba(0.7, 0.45, 0.95, 0.75 * alpha)
        ctx.set_line_width(2.5)
        for i in range(12):
            angle = i * (6.283 / 12.0)
            ctx.move_to(0, 0)
            ctx.line_to(shatter_r * math.cos(angle), shatter_r * math.sin(angle))
        ctx.stroke()
        ctx.restore()

    def _draw_cero_oscuras(self, ctx: cairo.Context, p: float, sx: float, sy: float, tx: float, ty: float):
        """Ulquiorra's colossal 800-1200px black and emerald Cero beam."""
        alpha = math.sin(p * math.pi)
        dx = tx - sx
        dy = ty - sy
        dist = max(1.0, math.hypot(dx, dy))
        nx, ny = dx / dist, dy / dist
        beam_len = max(900.0, dist * 1.5)
        ex = sx + nx * beam_len
        ey = sy + ny * beam_len

        # Roaring emerald outer corona
        ctx.save()
        ctx.set_source_rgba(0.08, 0.95, 0.3, 0.85 * alpha)
        ctx.set_line_width(85.0 * alpha)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(sx, sy)
        ctx.line_to(ex, ey)
        ctx.stroke()

        # Pitch-black void core
        ctx.set_source_rgba(0.02, 0.02, 0.02, 0.98 * alpha)
        ctx.set_line_width(38.0 * alpha)
        ctx.move_to(sx, sy)
        ctx.line_to(ex, ey)
        ctx.stroke()
        ctx.restore()

    def _draw_kurohitsugi(self, ctx: cairo.Context, p: float, sx: float, sy: float, tx: float, ty: float):
        """Aizen's Hado #90 Kurohitsugi (Black Coffin)."""
        alpha = math.sin(p * math.pi)
        cx, cy = tx, ty
        box_w = 160.0
        box_h = 360.0 * min(1.0, p * 1.5)

        ctx.save()
        # Deep obsidian monolithic block
        ctx.set_source_rgba(0.05, 0.02, 0.08, 0.92 * alpha)
        ctx.rectangle(cx - box_w / 2, cy - box_h, box_w, box_h)
        ctx.fill()

        # Deep violet edge runes
        ctx.set_source_rgba(0.55, 0.15, 0.85, 0.8 * alpha)
        ctx.set_line_width(3.0)
        ctx.rectangle(cx - box_w / 2, cy - box_h, box_w, box_h)
        ctx.stroke()
        ctx.restore()

    def _draw_lanza(self, ctx: cairo.Context, p: float, sx: float, sy: float, tx: float, ty: float):
        """Ulquiorra's Lanza del Relampago green lightning javelin and cross detonation."""
        alpha = math.sin(p * math.pi)
        cx = sx + (tx - sx) * min(1.0, p * 2.0)
        cy = sy + (ty - sy) * min(1.0, p * 2.0)

        ctx.save()
        if p < 0.5:
            # Flying lightning spear
            ctx.set_source_rgba(0.1, 1.0, 0.4, 0.9 * alpha)
            ctx.set_line_width(8.0)
            ctx.move_to(cx - 30.0, cy)
            ctx.line_to(cx + 30.0, cy)
            ctx.stroke()
        else:
            # Giant emerald cross detonation
            cross_size = 280.0 * alpha
            ctx.set_source_rgba(0.0, 1.0, 0.45, 0.85 * alpha)
            ctx.set_line_width(26.0 * alpha)
            ctx.move_to(tx, ty - cross_size)
            ctx.line_to(tx, ty + cross_size)
            ctx.move_to(tx - cross_size, ty)
            ctx.line_to(tx + cross_size, ty)
            ctx.stroke()
        ctx.restore()


class MacOSWebRopeWindow:
    """Virtual desktop overlay window dedicated to rendering Spider-Man / Batman swing lines and grapple cables on macOS."""

    def __init__(
        self,
        start_getter: Callable[[], Tuple[float, float]],
        end_getter: Callable[[], Tuple[float, float]],
        rope_style: str = "swing",
        alpha_getter: Optional[Callable[[], float]] = None
    ):
        self.start_getter = start_getter
        self.end_getter = end_getter
        self.rope_style = rope_style
        self.alpha_getter = alpha_getter
        self.anim_time = 0.0
        self.is_destroyed = False

        vx, vy, vw, vh = get_virtual_desktop_bounds()
        self.origin_x = int(vx)
        self.origin_y = int(vy)
        self.win_w = max(64, int(vw))
        self.win_h = max(64, int(vh))

        self.cur_min_x = self.origin_x
        self.cur_min_y = self.origin_y
        self.cur_w = self.win_w
        self.cur_h = self.win_h

        primary_h = get_primary_screen_height()
        ax, ay = buddy_window_to_appkit_origin(self.origin_x, self.origin_y, self.win_w, self.win_h, primary_h)

        frame = NSRect(NSPoint(ax, ay), NSSize(self.win_w, self.win_h))
        self.window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            AppKit.NSWindowStyleMaskBorderless,
            AppKit.NSBackingStoreBuffered,
            False
        )
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(AppKit.NSColor.clearColor())
        self.window.setHasShadow_(False)
        self.window.setLevel_(AppKit.NSFloatingWindowLevel)
        self.window.setIgnoresMouseEvents_(True)
        self.window.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces |
            AppKit.NSWindowCollectionBehaviorStationary |
            AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        self.stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, self.win_w)
        self.pixel_buf = bytearray(self.stride * self.win_h)
        self.surface = cairo.ImageSurface.create_for_data(
            self.pixel_buf, cairo.FORMAT_ARGB32, self.win_w, self.win_h, self.stride
        )
        self.cairo_ctx = cairo.Context(self.surface)
        self.color_space = CGColorSpaceCreateDeviceRGB()
        self.cg_bitmap_ctx = CGBitmapContextCreate(
            self.pixel_buf, self.win_w, self.win_h, 8, self.stride, self.color_space,
            kCGBitmapByteOrder32Host | kCGImageAlphaPremultipliedFirst
        )

        self.view = WebRopeView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(self.win_w, self.win_h)))
        self.view._owner = self
        self.view.setWantsLayer_(True)
        self.window.setContentView_(self.view)
        self.window.orderFrontRegardless()

    def update(self) -> None:
        if self.is_destroyed:
            return
        self.anim_time += 0.05
        self.view.setNeedsDisplay_(True)

    def queue_draw(self) -> None:
        if not self.is_destroyed:
            self.view.setNeedsDisplay_(True)

    def destroy_rope(self) -> None:
        if not self.is_destroyed:
            self.is_destroyed = True
            try:
                self.window.close()
            except Exception:
                pass

    def destroy(self) -> None:
        self.destroy_rope()

    def get_visual(self):
        return self.color_space or True

    def get_resizable(self) -> bool:
        return False

    def render_cairo_to_view(self, rect: NSRect) -> None:
        if self.is_destroyed:
            return
        try:
            p1 = self.start_getter()
            p2 = self.end_getter()
            if not p1 or not p2:
                return
        except Exception:
            return

        ctx = self.cairo_ctx
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()
        ctx.restore()

        ctx.set_operator(cairo.OPERATOR_OVER)
        alpha = 1.0
        if self.alpha_getter:
            try:
                alpha = max(0.0, min(1.0, self.alpha_getter()))
            except Exception:
                alpha = 1.0
        if alpha <= 0.01:
            return

        lx1 = p1[0] - self.origin_x
        ly1 = p1[1] - self.origin_y
        lx2 = p2[0] - self.origin_x
        ly2 = p2[1] - self.origin_y

        dx = lx2 - lx1
        dy = ly2 - ly1
        dist = math.hypot(dx, dy)
        if dist < 3.0:
            return

        nx = -dy / dist
        ny = dx / dist

        ctx.save()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)

        if self.rope_style == "swing":
            ctx.save()
            ctx.translate(lx2, ly2)
            ctx.set_source_rgba(0.95, 0.98, 1.0, 0.90 * alpha)
            ctx.set_line_width(1.8)
            for i in range(8):
                ang = i * (math.pi / 4.0) + 0.2
                spoke_len = 16.0 if i % 2 == 0 else 11.0
                ctx.move_to(0, 0)
                ctx.line_to(math.cos(ang) * spoke_len, math.sin(ang) * spoke_len)
                ctx.stroke()

            ctx.set_source_rgba(0.88, 0.94, 1.0, 0.75 * alpha)
            ctx.set_line_width(1.3)
            ctx.new_path()
            for i in range(8):
                ang = i * (math.pi / 4.0) + 0.2
                r = 10.0 if i % 2 == 0 else 7.0
                px = math.cos(ang) * r
                py = math.sin(ang) * r
                if i == 0:
                    ctx.move_to(px, py)
                else:
                    ctx.line_to(px, py)
            ctx.close_path()
            ctx.stroke()

            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95 * alpha)
            ctx.arc(0, 0, 3.5, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

            ctx.set_source_rgba(0.85, 0.92, 1.0, 0.40 * alpha)
            ctx.set_line_width(4.2)
            ctx.move_to(lx1, ly1)
            ctx.line_to(lx2, ly2)
            ctx.stroke()

            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95 * alpha)
            ctx.set_line_width(2.2)
            ctx.move_to(lx1, ly1)
            ctx.line_to(lx2, ly2)
            ctx.stroke()

            ctx.set_source_rgba(0.92, 0.98, 1.0, 0.75 * alpha)
            ctx.set_line_width(1.1)
            seg_len = 16.0
            steps = max(4, int(dist / seg_len))
            for s in range(steps):
                t1 = s / steps
                t2 = (s + 1) / steps
                p1x = lx1 + dx * t1
                p1y = ly1 + dy * t1
                p2x = lx1 + dx * t2
                p2y = ly1 + dy * t2
                wave = math.sin(s * 1.5 + self.anim_time * 8.0) * 3.2
                ctx.curve_to(
                    p1x + nx * wave, p1y + ny * wave,
                    p2x + nx * wave, p2y + ny * wave,
                    p2x, p2y
                )
                ctx.stroke()

        elif self.rope_style == "grapple":
            ctx.save()
            ctx.translate(lx2, ly2)
            ang = math.atan2(ly2 - ly1, lx2 - lx1)
            ctx.rotate(ang)

            ctx.set_source_rgba(0.25, 0.28, 0.35, 0.95 * alpha)
            ctx.set_line_width(2.2)
            ctx.arc(0, 0, 3.2, 0, 2 * math.pi)
            ctx.fill()
            for prong_angle in [-0.85, 0.0, 0.85]:
                ctx.move_to(0, 0)
                ctx.line_to(-math.cos(prong_angle) * 9.0, math.sin(prong_angle) * 9.0)
                ctx.stroke()
            ctx.restore()

            ctx.set_source_rgba(0.12, 0.14, 0.18, 0.95 * alpha)
            ctx.set_line_width(2.6)
            ctx.move_to(lx1, ly1)
            ctx.line_to(lx2, ly2)
            ctx.stroke()

            ctx.set_source_rgba(0.75, 0.82, 0.92, 0.85 * alpha)
            ctx.set_line_width(1.0)
            ctx.move_to(lx1, ly1)
            ctx.line_to(lx2, ly2)
            ctx.stroke()

            ctx.set_source_rgba(0.9, 0.95, 1.0, 0.40 * alpha)
            ctx.set_line_width(0.8)
            seg_len = 18.0
            steps = max(3, int(dist / seg_len))
            for s in range(steps):
                t1 = s / steps
                t2 = (s + 1) / steps
                p1x = lx1 + dx * t1
                p1y = ly1 + dy * t1
                p2x = lx1 + dx * t2
                p2y = ly1 + dy * t2
                vibe = math.sin(s * 2.0 + self.anim_time * 25.0) * 1.2
                ctx.move_to(p1x + nx * vibe, p1y + ny * vibe)
                ctx.line_to(p2x - nx * vibe, p2y - ny * vibe)
                ctx.stroke()

            ctx.set_source_rgba(0.3, 0.35, 0.45, 0.95 * alpha)
            ctx.arc(lx1, ly1, 2.5, 0, 2 * math.pi)
            ctx.fill()

        else:
            ctx.set_source_rgba(0.88, 0.95, 1.0, 0.55 * alpha)
            ctx.set_line_width(4.5)
            ctx.move_to(lx1, ly1)
            ctx.line_to(lx2, ly2)
            ctx.stroke()

            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.98 * alpha)
            ctx.set_line_width(2.4)
            ctx.move_to(lx1, ly1)
            ctx.line_to(lx2, ly2)
            ctx.stroke()

            ctx.set_source_rgba(0.92, 0.98, 1.0, 0.85 * alpha)
            ctx.set_line_width(1.2)
            seg_len = 14.0
            steps = max(4, int(dist / seg_len))
            for s in range(steps):
                t1 = s / steps
                t2 = (s + 1) / steps
                p1x = lx1 + dx * t1
                p1y = ly1 + dy * t1
                p2x = lx1 + dx * t2
                p2y = ly1 + dy * t2
                wave1 = math.sin(s * 1.8 + self.anim_time * 20.0) * 3.4 * (1.0 - t1 * 0.3)
                wave2 = math.cos(s * 1.8 + self.anim_time * 20.0) * 3.4 * (1.0 - t1 * 0.3)
                ctx.move_to(p1x + nx * wave1, p1y + ny * wave1)
                ctx.line_to(p2x + nx * wave2, p2y + ny * wave2)
                ctx.stroke()

            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95 * alpha)
            ctx.arc(lx1, ly1, 2.5, 0, 2 * math.pi)
            ctx.fill()

        ctx.restore()
        self.surface.flush()

        cg_img = None
        if hasattr(self, "cg_bitmap_ctx") and self.cg_bitmap_ctx:
            cg_img = CGBitmapContextCreateImage(self.cg_bitmap_ctx)
        elif hasattr(self, "surface"):
            data = bytes(self.surface.get_data())
            provider = CGDataProviderCreateWithData(None, data, len(data), None)
            cg_img = CGImageCreate(
                self.win_w, self.win_h, 8, 32, self.stride, self.color_space,
                kCGBitmapByteOrder32Host | kCGImageAlphaPremultipliedFirst,
                provider, None, False, 0
            )

        if cg_img:
            ns_ctx = AppKit.NSGraphicsContext.currentContext().CGContext()
            CGContextSaveGState(ns_ctx)
            CGContextTranslateCTM(ns_ctx, 0, rect.size.height)
            CGContextScaleCTM(ns_ctx, 1.0, -1.0)
            CGContextDrawImage(ns_ctx, rect, cg_img)
            CGContextRestoreGState(ns_ctx)



class BuddyAppDelegate(NSObject):
    """Native macOS application delegate handling Dock / Launchpad activation & reopening."""

    def applicationShouldHandleReopen_hasVisibleWindows_(self, sender, flag):
        try:
            if hasattr(self, "_engine") and self._engine:
                self._engine.open_control_center()
        except Exception as e:
            print(f"[Buddy AppDelegate] Error handling reopen: {e}", file=sys.stderr)
        return True

    def applicationWillTerminate_(self, notification):
        try:
            from platforms.macos.control_center import close_macos_control_center
            close_macos_control_center()
        except Exception:
            pass


class MacOSOverlayWindow(PlatformWindow):
    """Native macOS AppKit floating transparent pet window."""

    def __init__(
        self,
        on_draw: Callable,
        on_button_press: Optional[Callable] = None,
        on_button_release: Optional[Callable] = None,
        on_motion: Optional[Callable] = None,
        on_scroll: Optional[Callable] = None
    ):
        self.win_size = WIN_SIZE
        self.half_size = HALF_SIZE
        self.on_draw_cb = on_draw
        self.on_button_press_cb = on_button_press
        self.on_button_release_cb = on_button_release
        self.on_motion_cb = on_motion
        self.on_scroll_cb = on_scroll
        self._engine = None

        app = AppKit.NSApplication.sharedApplication()
        app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
        self.app_delegate = BuddyAppDelegate.alloc().init()
        self.app_delegate._engine = None
        app.setDelegate_(self.app_delegate)

        # Use the main (focused) screen for bounds and backing scale,
        # not screens()[0] which is only correct for coordinate-origin math.
        from platforms.macos.coordinate import get_main_screen
        primary = get_main_screen()
        p_frame = primary.frame() if primary else NSRect(NSPoint(0, 0), NSSize(1920, 1080))
        self.screen_w = float(p_frame.size.width)
        self.screen_h = float(p_frame.size.height)
        self.bounds = (float(p_frame.origin.x), float(p_frame.origin.y), self.screen_w, self.screen_h)

        self.backing_scale = float(primary.backingScaleFactor()) if primary else 2.0
        self.pixel_w = int(self.win_size * self.backing_scale)
        self.pixel_h = int(self.win_size * self.backing_scale)

        self.stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, self.pixel_w)
        self.pixel_buf = bytearray(self.stride * self.pixel_h)
        self.surface = cairo.ImageSurface.create_for_data(
            self.pixel_buf, cairo.FORMAT_ARGB32, self.pixel_w, self.pixel_h, self.stride
        )
        self.cairo_ctx = cairo.Context(self.surface)
        self.cairo_ctx.scale(self.backing_scale, self.backing_scale)
        self.color_space = CGColorSpaceCreateDeviceRGB()
        self.cg_bitmap_ctx = CGBitmapContextCreate(
            self.pixel_buf, self.pixel_w, self.pixel_h, 8, self.stride, self.color_space,
            kCGBitmapByteOrder32Host | kCGImageAlphaPremultipliedFirst
        )

        init_frame = NSRect(NSPoint(200, 200), NSSize(self.win_size, self.win_size))
        panel_style = (
            AppKit.NSWindowStyleMaskBorderless |
            AppKit.NSWindowStyleMaskNonactivatingPanel
        )
        self.window = BuddyNSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            init_frame,
            panel_style,
            AppKit.NSBackingStoreBuffered,
            False
        )
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(AppKit.NSColor.clearColor())
        self.window.setHasShadow_(False)
        self.window.setLevel_(AppKit.NSStatusWindowLevel)
        self.window.setHidesOnDeactivate_(False)
        self.window.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces |
            AppKit.NSWindowCollectionBehaviorStationary |
            AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        self.hitbox_radius = 36.0
        self.click_through = False
        self._last_wx: Optional[int] = None
        self._last_wy: Optional[int] = None

        self.view = BuddyOverlayView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(self.win_size, self.win_size)))
        self.view.overlay_ref = self
        self.view.setWantsLayer_(True)
        self.window.setContentView_(self.view)

    def set_hitbox_mask(self, radius: float = 36.0) -> None:
        self.hitbox_radius = radius

    def set_scale(self, scale: float) -> None:
        self.hitbox_radius = max(20.0, min(54.0, 36.0 * scale))

    def set_click_through(self, enabled: bool) -> None:
        self.click_through = enabled
        self.window.setIgnoresMouseEvents_(enabled)

    def move_to(self, center_x: float, center_y: float) -> None:
        wx = int(center_x - self.half_size)
        wy = int(center_y - self.half_size)
        if wx != self._last_wx or wy != self._last_wy:
            ax, ay = buddy_window_to_appkit_origin(wx, wy, self.win_size, self.win_size, self.screen_h)
            if hasattr(self.window, "setFrameOrigin_"):
                self.window.setFrameOrigin_(NSPoint(ax, ay))
            if hasattr(self.window, "move"):
                self.window.move(wx, wy)
            self._last_wx = wx
            self._last_wy = wy

    def query_pointer(self) -> Tuple[float, float]:
        loc = AppKit.NSEvent.mouseLocation()
        bx, by = appkit_to_buddy_point(loc.x, loc.y, self.screen_h)
        return bx, by

    def trigger_sky_strike(self, target_x: float, target_y: float) -> None:
        MacOSSkyStrikeWindow(target_x, target_y)

    def trigger_world_vfx(
        self,
        effect_type: str,
        start_x: float,
        start_y: float,
        target_x: float,
        target_y: float,
        **kwargs
    ) -> None:
        """Trigger unclipped, full-desktop Bleach world-space visual effect."""
        try:
            MacOSWorldEffectWindow.trigger(effect_type, start_x, start_y, target_x, target_y, **kwargs)
        except Exception as e:
            print(f"[MacOSOverlayWindow] Error triggering world VFX '{effect_type}': {e}", file=sys.stderr)

    def queue_draw(self) -> None:
        self.view.setNeedsDisplay_(True)

    def set_engine(self, engine: Any) -> None:
        self._engine = engine
        if hasattr(self, "app_delegate") and self.app_delegate:
            self.app_delegate._engine = engine

    def show(self) -> None:
        self.window.orderFrontRegardless()

    def close(self) -> None:
        try:
            if MacOSWorldEffectWindow._active_instance is not None:
                MacOSWorldEffectWindow._active_instance.destroy()
        except Exception:
            pass
        try:
            self.window.close()
        except Exception:
            pass

    def destroy(self) -> None:
        self.close()


OverlayWindow = MacOSOverlayWindow
WebRopeWindow = MacOSWebRopeWindow
SkyStrikeWindow = MacOSSkyStrikeWindow
