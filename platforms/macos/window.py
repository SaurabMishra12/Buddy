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

        data = bytes(owner.surface.get_data())
        provider = CGDataProviderCreateWithData(None, data, len(data), None)
        cg_img = CGImageCreate(
            owner.width, owner.height, 8, 32, owner.stride, owner.color_space,
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


class BuddyNSWindow(AppKit.NSWindow):
    def canBecomeKeyWindow(self):
        return True

    def destroy(self):
        self.close()


class BuddyOverlayView(AppKit.NSView):
    def isFlipped(self):
        return True

    def hitTest_(self, aPoint):
        if not hasattr(self, "overlay_ref") or not self.overlay_ref:
            return None
        overlay = self.overlay_ref
        if overlay.click_through:
            return None
        local = self.convertPoint_fromView_(aPoint, None)
        dx = local.x - overlay.half_size
        dy = local.y - overlay.half_size
        if (dx * dx + dy * dy) <= (overlay.hitbox_radius * overlay.hitbox_radius):
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
        loc = self.convertPoint_fromView_(event.locationInWindow(), None)
        ev = EventProxy(
            button=1,
            x=loc.x,
            y=loc.y,
            type=5 if event.clickCount() >= 2 else 4
        )
        if self.overlay_ref.on_button_press_cb:
            self.overlay_ref.on_button_press_cb(self, ev)

    def mouseDragged_(self, event):
        if not hasattr(self, "overlay_ref") or not self.overlay_ref:
            return
        loc = self.convertPoint_fromView_(event.locationInWindow(), None)
        ev = EventProxy(x=loc.x, y=loc.y)
        if self.overlay_ref.on_motion_cb:
            self.overlay_ref.on_motion_cb(self, ev)

    def mouseUp_(self, event):
        if not hasattr(self, "overlay_ref") or not self.overlay_ref:
            return
        loc = self.convertPoint_fromView_(event.locationInWindow(), None)
        ev = EventProxy(button=1, x=loc.x, y=loc.y)
        if self.overlay_ref.on_button_release_cb:
            self.overlay_ref.on_button_release_cb(self, ev)

    def rightMouseDown_(self, event):
        if not hasattr(self, "overlay_ref") or not self.overlay_ref:
            return
        loc = self.convertPoint_fromView_(event.locationInWindow(), None)
        ev = EventProxy(button=3, x=loc.x, y=loc.y, ns_event=event)
        if self.overlay_ref.on_button_press_cb:
            self.overlay_ref.on_button_press_cb(self, ev)

    def otherMouseDown_(self, event):
        if not hasattr(self, "overlay_ref") or not self.overlay_ref:
            return
        if event.buttonNumber() == 2:
            loc = self.convertPoint_fromView_(event.locationInWindow(), None)
            ev = EventProxy(button=2, x=loc.x, y=loc.y)
            if self.overlay_ref.on_button_press_cb:
                self.overlay_ref.on_button_press_cb(self, ev)

    def scrollWheel_(self, event):
        if not hasattr(self, "overlay_ref") or not self.overlay_ref:
            return
        dy = event.deltaY()
        direction = ScrollDirection.UP if dy > 0 else ScrollDirection.DOWN
        ev = EventProxy(direction=direction, delta_y=dy)
        if self.overlay_ref.on_scroll_cb:
            self.overlay_ref.on_scroll_cb(self, ev)


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

        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        self.cairo_ctx = cairo.Context(self.surface)
        self.color_space = CGColorSpaceCreateDeviceRGB()
        self.stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, self.width)

        self.view = SkyStrikeView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(self.width, self.height)))
        self.view._owner = self
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

        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.win_w, self.win_h)
        self.cairo_ctx = cairo.Context(self.surface)
        self.color_space = CGColorSpaceCreateDeviceRGB()
        self.stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, self.win_w)

        self.view = WebRopeView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(self.win_w, self.win_h)))
        self.view._owner = self
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

        app = AppKit.NSApplication.sharedApplication()
        app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

        primary_screens = AppKit.NSScreen.screens()
        primary = primary_screens[0] if primary_screens else None
        p_frame = primary.frame() if primary else NSRect(NSPoint(0, 0), NSSize(1920, 1080))
        self.screen_w = float(p_frame.size.width)
        self.screen_h = float(p_frame.size.height)
        self.bounds = (float(p_frame.origin.x), float(p_frame.origin.y), self.screen_w, self.screen_h)

        self.backing_scale = float(primary.backingScaleFactor()) if primary else 2.0
        self.pixel_w = int(self.win_size * self.backing_scale)
        self.pixel_h = int(self.win_size * self.backing_scale)

        self.stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, self.pixel_w)
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.pixel_w, self.pixel_h)
        self.cairo_ctx = cairo.Context(self.surface)
        self.cairo_ctx.scale(self.backing_scale, self.backing_scale)
        self.color_space = CGColorSpaceCreateDeviceRGB()

        init_frame = NSRect(NSPoint(200, 200), NSSize(self.win_size, self.win_size))
        self.window = BuddyNSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            init_frame,
            AppKit.NSWindowStyleMaskBorderless,
            AppKit.NSBackingStoreBuffered,
            False
        )
        self.window.setOpaque_(False)
        self.window.setBackgroundColor_(AppKit.NSColor.clearColor())
        self.window.setHasShadow_(False)
        self.window.setLevel_(AppKit.NSFloatingWindowLevel)
        self.window.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces |
            AppKit.NSWindowCollectionBehaviorStationary |
            AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        self.hitbox_radius = 54.0
        self.click_through = False
        self._last_wx: Optional[int] = None
        self._last_wy: Optional[int] = None

        self.view = BuddyOverlayView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(self.win_size, self.win_size)))
        self.view.overlay_ref = self
        self.window.setContentView_(self.view)

    def set_hitbox_mask(self, radius: float = 54.0) -> None:
        self.hitbox_radius = radius

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

    def queue_draw(self) -> None:
        self.view.setNeedsDisplay_(True)

    def show(self) -> None:
        self.window.orderFrontRegardless()

    def close(self) -> None:
        try:
            self.window.close()
        except Exception:
            pass

    def destroy(self) -> None:
        self.close()


OverlayWindow = MacOSOverlayWindow
WebRopeWindow = MacOSWebRopeWindow
SkyStrikeWindow = MacOSSkyStrikeWindow
