"""Screen-wide desktop projectile overlay for macOS: handles long-range thrown shields, hammers, and fireballs."""

import math
import random
import time
import cairo
from typing import Tuple, List, Optional, Callable, Dict, Any

import AppKit
from Foundation import NSPoint, NSRect, NSSize, NSObject, NSTimer, NSRunLoop, NSRunLoopCommonModes
from Quartz import (
    CGColorSpaceCreateDeviceRGB, CGDataProviderCreateWithData, CGImageCreate,
    CGContextDrawImage, CGContextSaveGState, CGContextRestoreGState,
    CGContextTranslateCTM, CGContextScaleCTM,
    kCGBitmapByteOrder32Host, kCGImageAlphaPremultipliedFirst
)

from core.particles import CYAN_GLOW, BLUE_GLOW, FIRE_ORANGE, FIRE_YELLOW
from core.audio import audio_manager
from platforms.macos.coordinate import (
    buddy_window_to_appkit_origin, get_primary_screen_frame, get_primary_screen_height
)
from platforms.macos.window import MacOSWebRopeWindow, WebRopeWindow


class ProjectileView(AppKit.NSView):
    def isFlipped(self):
        return True

    def drawRect_(self, rect):
        if not hasattr(self, "proj_ref") or not self.proj_ref:
            return
        proj = self.proj_ref
        ctx = proj.cairo_ctx
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()
        ctx.restore()

        ctx.set_operator(cairo.OPERATOR_OVER)
        proj.on_draw(self, ctx)
        proj.surface.flush()

        data = bytes(proj.surface.get_data())
        provider = CGDataProviderCreateWithData(None, data, len(data), None)
        cg_img = CGImageCreate(
            proj.pixel_w, proj.pixel_h, 8, 32,
            proj.stride, proj.color_space,
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


class ProjTimerTarget(NSObject):
    def onTick_(self, timer):
        if hasattr(self, "_owner") and self._owner:
            self._owner.on_tick()



class MacOSDesktopProjectileWindow:
    """Floating transparent window for long-range projectiles traveling across macOS desktop."""


    def __init__(
        self,
        proj_type: str,
        start_x: float,
        start_y: float,
        target_x: float,
        target_y: float,
        owner_getter: Callable[[], Tuple[float, float]],
        on_catch: Optional[Callable[[], None]] = None,
        speed: float = 24.0
    ):
        self.proj_type = proj_type
        self.owner_getter = owner_getter
        self.on_catch = on_catch
        self.win_size = 110
        self.half_size = 55.0

        _, _, self.screen_w, self.screen_h = get_primary_screen_frame()
        self.primary_h = self.screen_h

        # Movement & state
        self.x = float(start_x)
        self.y = float(start_y)
        dx = target_x - start_x
        dy = target_y - start_y
        dist = math.hypot(dx, dy) + 1e-4

        self.vx = (dx / dist) * speed
        self.vy = (dy / dist) * speed
        self.target_x = target_x
        self.target_y = target_y
        self.angle = 0.0
        self.angular_velocity = 0.45
        self.state = "OUTBOUND"  # "OUTBOUND", "RETURNING", "EXPLODING"
        self.trail: List[Tuple[float, float, float]] = []
        self.sparks: List[Dict[str, Any]] = []
        self.shockwave_rad = 0.0
        self.shockwave_alpha = 0.0
        self._last_wx = None
        self._last_wy = None
        self.explosion_frame = 0

        # Create AppKit window
        init_ax, init_ay = buddy_window_to_appkit_origin(
            self.x - self.half_size, self.y - self.half_size,
            self.win_size, self.win_size, self.primary_h
        )
        frame = NSRect(NSPoint(init_ax, init_ay), NSSize(self.win_size, self.win_size))
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

        # High-DPI backing scale
        primary_screens = AppKit.NSScreen.screens()
        primary = primary_screens[0] if primary_screens else None
        self.backing_scale = float(primary.backingScaleFactor()) if primary else 2.0
        self.pixel_w = int(self.win_size * self.backing_scale)
        self.pixel_h = int(self.win_size * self.backing_scale)

        self.stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, self.pixel_w)
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.pixel_w, self.pixel_h)
        self.cairo_ctx = cairo.Context(self.surface)
        self.cairo_ctx.scale(self.backing_scale, self.backing_scale)
        self.color_space = CGColorSpaceCreateDeviceRGB()

        # Dedicated full-length web rope overlay connecting hero wrist to projectile
        self.rope_window: Optional[MacOSWebRopeWindow] = None
        if self.proj_type == "web":
            try:
                self.rope_window = MacOSWebRopeWindow(
                    start_getter=self._get_owner_wrist,
                    end_getter=lambda: (self.x, self.y),
                    rope_style="throw",
                    alpha_getter=self._get_web_alpha
                )
            except Exception:
                self.rope_window = None

        self.view = ProjectileView.alloc().initWithFrame_(NSRect(NSPoint(0, 0), NSSize(self.win_size, self.win_size)))
        self.view.proj_ref = self
        self.window.setContentView_(self.view)
        self.window.orderFrontRegardless()

        self._timer_target = ProjTimerTarget.alloc().init()
        self._timer_target._owner = self

        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.016, self._timer_target, "onTick:", None, True
        )
        NSRunLoop.currentRunLoop().addTimer_forMode_(self.timer, NSRunLoopCommonModes)


    def _get_owner_wrist(self) -> Tuple[float, float]:
        try:
            hx, hy = self.owner_getter()
            dir_mult = 1.0 if self.target_x >= hx else -1.0
            return (hx + dir_mult * 26.0, hy - 6.0)
        except Exception:
            return (self.x, self.y)

    def _get_web_alpha(self) -> float:
        if self.state == "EXPLODING":
            return max(0.0, 1.0 - self.explosion_frame / 16.0)
        return 1.0

    def _cleanup_rope(self) -> None:
        if hasattr(self, "rope_window") and self.rope_window:
            self.rope_window.destroy_rope()
            self.rope_window = None

    def destroy(self):
        if self.timer:
            self.timer.invalidate()
            self.timer = None
        self._cleanup_rope()
        try:
            self.window.close()
        except Exception:
            pass

    def destroy_projectile(self) -> None:
        self.destroy()

    def on_tick(self) -> bool:
        if self.state == "EXPLODING":
            self.explosion_frame += 1
            # Update sparks
            for s in self.sparks:
                s["x"] += s["vx"]
                s["y"] += s["vy"]
                s["vy"] += 0.3
                s["life"] -= 0.06
            self.sparks = [s for s in self.sparks if s["life"] > 0]
            self.shockwave_rad += 3.5
            self.shockwave_alpha = max(0.0, 1.0 - (self.explosion_frame / 15.0))

            if hasattr(self, "rope_window") and self.rope_window:
                self.rope_window.update()

            if self.explosion_frame > 16:
                self.destroy()
                return False
            self.view.setNeedsDisplay_(True)
            return True

        # Trail recording
        self.trail.append((self.x, self.y, self.angle))
        if len(self.trail) > 10:
            self.trail.pop(0)

        # Update position
        self.x += self.vx
        self.y += self.vy
        self.angle += self.angular_velocity

        if hasattr(self, "rope_window") and self.rope_window:
            self.rope_window.update()

        if self.state == "OUTBOUND":
            dist_to_target = math.hypot(self.target_x - self.x, self.target_y - self.y)
            out_of_bounds = (
                self.x < -80 or self.x > self.screen_w + 80 or
                self.y < -80 or self.y > self.screen_h + 80
            )
            if dist_to_target < 30.0 or out_of_bounds:
                self._trigger_collision()

        elif self.state == "RETURNING":
            # Homing in on hero
            try:
                hx, hy = self.owner_getter()
            except Exception:
                hx, hy = self.target_x, self.target_y

            dx = hx - self.x
            dy = hy - self.y
            dist_to_owner = math.hypot(dx, dy) + 1e-4

            return_speed = min(36.0, max(22.0, dist_to_owner * 0.08))
            self.vx = (dx / dist_to_owner) * return_speed
            self.vy = (dy / dist_to_owner) * return_speed

            if dist_to_owner < 38.0:
                # Caught!
                if self.on_catch:
                    try:
                        self.on_catch()
                    except Exception:
                        pass
                audio_manager.play("smash")
                self.destroy()
                return False

        # Move native window
        wx = int(self.x - self.half_size)
        wy = int(self.y - self.half_size)
        if wx != self._last_wx or wy != self._last_wy:
            ax, ay = buddy_window_to_appkit_origin(wx, wy, self.win_size, self.win_size, self.primary_h)
            self.window.setFrameOrigin_(NSPoint(ax, ay))
            self._last_wx = wx
            self._last_wy = wy

        self.view.setNeedsDisplay_(True)
        return True

    def _trigger_collision(self) -> None:
        """Called when projectile collides with target or boundary."""
        self._trigger_impact()
        if self.proj_type in ("mjolnir", "shield"):
            self.state = "RETURNING"
        else:
            self.state = "EXPLODING"
            self.explosion_frame = 0

    def _trigger_impact(self) -> None:
        """Spawn burst particles and audio when projectile strikes target."""
        if self.proj_type == "mjolnir":
            audio_manager.play("lightning")
            for _ in range(16):
                ang = random.uniform(0, math.pi * 2)
                spd = random.uniform(3.0, 10.0)
                self.sparks.append({
                    "x": self.half_size,
                    "y": self.half_size,
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd,
                    "color": CYAN_GLOW,
                    "life": 1.0,
                    "size": random.uniform(2.5, 4.5)
                })
        elif self.proj_type == "shield":
            audio_manager.play("smash")
            for _ in range(14):
                ang = random.uniform(0, math.pi * 2)
                spd = random.uniform(4.0, 9.0)
                self.sparks.append({
                    "x": self.half_size,
                    "y": self.half_size,
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd,
                    "color": (1.0, 0.9, 0.4),
                    "life": 1.0,
                    "size": random.uniform(2.0, 4.0)
                })
        elif self.proj_type == "fireball":
            audio_manager.play("fire")
            for _ in range(20):
                ang = random.uniform(0, math.pi * 2)
                spd = random.uniform(3.0, 12.0)
                self.sparks.append({
                    "x": self.half_size,
                    "y": self.half_size,
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd,
                    "color": FIRE_ORANGE if random.random() > 0.4 else FIRE_YELLOW,
                    "life": 1.0,
                    "size": random.uniform(3.0, 6.0)
                })
        elif self.proj_type == "unibeam":
            audio_manager.play("jet")
            for _ in range(18):
                ang = random.uniform(0, math.pi * 2)
                spd = random.uniform(4.0, 11.0)
                self.sparks.append({
                    "x": self.half_size,
                    "y": self.half_size,
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd,
                    "color": (0.2, 0.85, 1.0) if random.random() > 0.3 else (1.0, 1.0, 1.0),
                    "life": 1.0,
                    "size": random.uniform(2.5, 5.0)
                })
        elif self.proj_type == "power_blast":
            audio_manager.play("roar")
            for _ in range(22):
                ang = random.uniform(0, math.pi * 2)
                spd = random.uniform(3.5, 12.0)
                self.sparks.append({
                    "x": self.half_size,
                    "y": self.half_size,
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd,
                    "color": (0.85, 0.2, 1.0) if random.random() > 0.4 else (0.4, 0.1, 0.9),
                    "life": 1.0,
                    "size": random.uniform(3.0, 6.5)
                })
        elif self.proj_type == "web":
            audio_manager.play("thwip")
            for _ in range(16):
                ang = random.uniform(0, math.pi * 2)
                spd = random.uniform(2.5, 7.0)
                self.sparks.append({
                    "x": self.half_size,
                    "y": self.half_size,
                    "vx": math.cos(ang) * spd,
                    "vy": math.sin(ang) * spd,
                    "color": (0.95, 0.98, 1.0),
                    "life": 1.0,
                    "size": random.uniform(1.8, 3.5)
                })

    def draw(self, ctx: cairo.Context) -> bool:
        """Compatibility wrapper for direct test rendering calls (e.g. proj.draw(ctx))."""
        return self.on_draw(getattr(self, "view", None), ctx)

    def on_draw(self, widget, ctx: cairo.Context) -> bool:
        cx = self.half_size
        cy = self.half_size

        if self.state == "EXPLODING":
            if self.shockwave_rad > 0 and self.shockwave_alpha > 0:
                ctx.save()
                ctx.set_source_rgba(1.0, 0.9, 0.3, 0.5 * self.shockwave_alpha)
                ctx.set_line_width(4.0)
                ctx.arc(cx, cy, self.shockwave_rad, 0, 2 * math.pi)
                ctx.stroke()
                ctx.restore()

            for s in self.sparks:
                ctx.save()
                r, g, b = s["color"]
                ctx.set_source_rgba(r, g, b, s["life"])
                ctx.arc(s["x"], s["y"], s["size"] * s["life"], 0, 2 * math.pi)
                ctx.fill()
                ctx.restore()
            return False

        # Motion trail
        for i, (tx, ty, tang) in enumerate(self.trail):
            alpha = (i / len(self.trail)) * 0.4
            ctx.save()
            ctx.translate(cx, cy)
            ctx.rotate(tang)
            if self.proj_type == "mjolnir":
                ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], alpha * 0.5)
                ctx.rectangle(-14, -8, 28, 16)
                ctx.fill()
            elif self.proj_type == "fireball":
                ctx.set_source_rgba(FIRE_ORANGE[0], FIRE_ORANGE[1], FIRE_ORANGE[2], alpha)
                ctx.arc(0, 0, 14.0 * (i / len(self.trail)), 0, 2 * math.pi)
                ctx.fill()
            elif self.proj_type == "shield":
                ctx.set_source_rgba(0.2, 0.4, 0.9, alpha * 0.4)
                ctx.arc(0, 0, 16.0, 0, 2 * math.pi)
                ctx.fill()
            elif self.proj_type == "unibeam":
                ctx.set_source_rgba(0.2, 0.85, 1.0, alpha * 0.6)
                ctx.rectangle(-18, -9, 36, 18)
                ctx.fill()
            elif self.proj_type == "power_blast":
                ctx.set_source_rgba(0.85, 0.2, 1.0, alpha * 0.5)
                ctx.arc(0, 0, 15.0 * (i / len(self.trail)), 0, 2 * math.pi)
                ctx.fill()
            elif self.proj_type == "web":
                ctx.set_source_rgba(0.9, 0.95, 1.0, alpha * 0.4)
                ctx.arc(0, 0, 12.0, 0, 2 * math.pi)
                ctx.fill()
            ctx.restore()

        # Render Active Projectile
        ctx.save()
        ctx.translate(cx, cy)
        ctx.rotate(self.angle)

        if self.proj_type == "mjolnir":
            # Thor Mjolnir
            ctx.set_source_rgba(0.45, 0.26, 0.12, 1.0)
            ctx.rectangle(-3, 0, 6, 26)
            ctx.fill()

            pat = cairo.LinearGradient(-18, -14, 18, 8)
            pat.add_color_stop_rgb(0.0, 0.85, 0.88, 0.92)
            pat.add_color_stop_rgb(0.5, 0.60, 0.63, 0.68)
            pat.add_color_stop_rgb(1.0, 0.35, 0.38, 0.42)
            ctx.set_source(pat)
            ctx.rectangle(-18, -14, 36, 20)
            ctx.fill()
            ctx.set_source_rgb(0.2, 0.22, 0.25)
            ctx.set_line_width(1.5)
            ctx.rectangle(-18, -14, 36, 20)
            ctx.stroke()

            # Glowing runic engraving
            ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], 0.85)
            ctx.set_line_width(1.2)
            ctx.arc(0, -4, 4.0, 0, 2 * math.pi)
            ctx.stroke()

        elif self.proj_type == "shield":
            # Captain America Vibranium Shield
            rad = 18.0
            for r, col in [
                (rad, (0.85, 0.1, 0.1)),
                (rad * 0.78, (0.9, 0.9, 0.9)),
                (rad * 0.56, (0.85, 0.1, 0.1)),
                (rad * 0.36, (0.1, 0.25, 0.75))
            ]:
                ctx.set_source_rgb(*col)
                ctx.arc(0, 0, r, 0, 2 * math.pi)
                ctx.fill()
            # Star
            ctx.set_source_rgb(1.0, 1.0, 1.0)
            ctx.new_path()
            for p in range(5):
                outer_a = p * (2 * math.pi / 5) - math.pi / 2
                inner_a = outer_a + (math.pi / 5)
                px = math.cos(outer_a) * (rad * 0.32)
                py = math.sin(outer_a) * (rad * 0.32)
                ix = math.cos(inner_a) * (rad * 0.14)
                iy = math.sin(inner_a) * (rad * 0.14)
                if p == 0:
                    ctx.move_to(px, py)
                else:
                    ctx.line_to(px, py)
                ctx.line_to(ix, iy)
            ctx.close_path()
            ctx.fill()

        elif self.proj_type == "fireball":
            # Dragon Fireball
            rad = 18.0
            pat = cairo.RadialGradient(0, 0, 2, 0, 0, rad)
            pat.add_color_stop_rgba(0.0, 1.0, 1.0, 0.8, 1.0)
            pat.add_color_stop_rgba(0.4, 1.0, 0.6, 0.0, 0.95)
            pat.add_color_stop_rgba(0.8, 0.9, 0.1, 0.0, 0.8)
            pat.add_color_stop_rgba(1.0, 0.4, 0.0, 0.0, 0.0)
            ctx.set_source(pat)
            ctx.arc(0, 0, rad, 0, 2 * math.pi)
            ctx.fill()

        elif self.proj_type == "unibeam":
            # Iron Man Chest Arc Reactor Unibeam Repulsor Bolt
            w_box, h_box = 24.0, 12.0
            pat = cairo.RadialGradient(0, 0, 2, 0, 0, 16.0)
            pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 1.0)
            pat.add_color_stop_rgba(0.3, 0.3, 0.85, 1.0, 0.95)
            pat.add_color_stop_rgba(0.7, 0.05, 0.45, 0.95, 0.7)
            pat.add_color_stop_rgba(1.0, 0.0, 0.2, 0.8, 0.0)
            ctx.set_source(pat)
            ctx.arc(0, 0, 18.0, 0, 2 * math.pi)
            ctx.fill()

        elif self.proj_type == "power_blast":
            # Thanos Power Stone Cosmic Energy Orb
            rad = 19.0
            pat = cairo.RadialGradient(0, 0, 2, 0, 0, rad)
            pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 1.0)
            pat.add_color_stop_rgba(0.35, 0.95, 0.20, 1.0, 0.95)
            pat.add_color_stop_rgba(0.75, 0.60, 0.05, 0.85, 0.85)
            pat.add_color_stop_rgba(1.0, 0.25, 0.0, 0.40, 0.0)
            ctx.set_source(pat)
            ctx.arc(0, 0, rad, 0, 2 * math.pi)
            ctx.fill()

        elif self.proj_type == "web":
            # Spider-Man Spun Web Core
            ctx.set_source_rgba(0.85, 0.92, 1.0, 0.35)
            ctx.arc(0, 0, 15.0, 0, 2 * math.pi)
            ctx.fill()

            pat_core = cairo.RadialGradient(0, 0, 2, 0, 0, 9.0)
            pat_core.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 1.0)
            pat_core.add_color_stop_rgba(0.65, 0.90, 0.95, 1.0, 0.95)
            pat_core.add_color_stop_rgba(1.0, 0.70, 0.85, 1.0, 0.40)
            ctx.set_source(pat_core)
            ctx.arc(0, 0, 9.0, 0, 2 * math.pi)
            ctx.fill()

            ctx.set_source_rgba(0.95, 0.98, 1.0, 0.95)
            ctx.set_line_width(1.6)
            for rad_ang in [0.0, 0.785, 1.57, 2.356, 3.14, 3.927, 4.712, 5.498]:
                ctx.move_to(0, 0)
                ctx.line_to(math.cos(rad_ang) * 14.0, math.sin(rad_ang) * 14.0)
                ctx.stroke()

        ctx.restore()
        return False


DesktopProjectileWindow = MacOSDesktopProjectileWindow
