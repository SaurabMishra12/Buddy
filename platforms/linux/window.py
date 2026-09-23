"""Linux GTK3/GDK floating companion window and transient visual effects.

Matches Mjolnir desktop pet architecture with X11/XWayland input shape transparency.
"""

import sys
import math
import random
import cairo
from typing import Tuple, Optional, Callable

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib


WIN_SIZE = 180              # 180x180 visual space for character, particles, and effects
HALF_SIZE = WIN_SIZE / 2.0  # 90.0 (Pet center coordinate inside window)

CYAN_GLOW = (0.0, 0.9, 1.0)
BLUE_GLOW = (0.1, 0.45, 1.0)
WHITE_CORE = (1.0, 1.0, 1.0)


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

            # Outer glow
            trace()
            ctx.set_line_width(8.0)
            ctx.set_source_rgba(BLUE_GLOW[0], BLUE_GLOW[1], BLUE_GLOW[2], 0.35 * fade)
            ctx.stroke()

            # Mid glow
            trace()
            ctx.set_line_width(4.0)
            ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], 0.75 * fade)
            ctx.stroke()

            # Core
            trace()
            ctx.set_line_width(1.8)
            ctx.set_source_rgba(WHITE_CORE[0], WHITE_CORE[1], WHITE_CORE[2], 0.95 * fade)
            ctx.stroke()

        ctx.restore()


class SkyStrikeWindow(Gtk.Window):
    """Transient, self-destroying narrow window for colossal lightning strikes from screen top."""

    def __init__(self, target_cx: float, target_cy: float):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("SkyStrike")
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_accept_focus(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)

        screen = Gdk.Screen.get_default()
        visual = screen.get_rgba_visual()
        if visual is not None:
            self.set_visual(visual)

        self.width = 240
        self.height = max(120, int(target_cy) + 30)
        self.set_default_size(self.width, self.height)

        self.realize()
        gdk_win = self.get_window()
        gdk_win.set_override_redirect(True)
        # 100% click-through so user can click through lightning
        gdk_win.input_shape_combine_region(cairo.Region(), 0, 0)

        # Move to screen top, centered above target
        self.move(int(target_cx - self.width / 2), 0)

        # CSS transparency override
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"window { background-color: transparent; }")
        Gtk.StyleContext.add_provider_for_screen(screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

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
        self.connect("draw", self.on_draw)
        GLib.timeout_add(16, self.on_tick)
        self.show_all()

    def on_tick(self) -> bool:
        self.frames += 1
        a1 = self.bolt1.update()
        a2 = self.bolt2.update()
        if not a1 and not a2 or self.frames > 35:
            self.destroy()
            return False
        self.queue_draw()
        return True

    def on_draw(self, widget, ctx: cairo.Context) -> bool:
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()
        ctx.restore()

        ctx.set_operator(cairo.OPERATOR_OVER)
        self.bolt1.draw(ctx)
        self.bolt2.draw(ctx)
        return False


class WebRopeWindow(Gtk.Window):
    """Full virtual desktop overlay window dedicated to rendering Spider-Man / Batman swing lines.

    Eliminates all window-border clipping by spanning the exact region between start and end coordinates.
    Used for:
    1. Spider-Man web-swinging and upside-down hanging (hand -> ceiling anchor).
    2. Spider-Man web throw projectile silk rope (wrist -> projectile/target).
    """

    def __init__(
        self,
        start_getter: Callable[[], Tuple[float, float]],
        end_getter: Callable[[], Tuple[float, float]],
        rope_style: str = "swing",  # "swing" or "throw"
        alpha_getter: Optional[Callable[[], float]] = None
    ):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("BuddyWebRope")
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)

        self.start_getter = start_getter
        self.end_getter = end_getter
        self.rope_style = rope_style
        self.alpha_getter = alpha_getter
        self.anim_time = 0.0
        self.is_destroyed = False

        self.display = Gdk.Display.get_default()
        self.screen = Gdk.Screen.get_default()

        # Compute virtual desktop span across all monitors
        origin_x, origin_y = 0, 0
        win_w, win_h = 1920, 1080
        if self.display:
            n_monitors = self.display.get_n_monitors()
            if n_monitors > 0:
                min_mx, min_my = float("inf"), float("inf")
                max_mx, max_my = float("-inf"), float("-inf")
                for i in range(n_monitors):
                    mon = self.display.get_monitor(i)
                    if mon:
                        g = mon.get_geometry()
                        min_mx = min(min_mx, g.x)
                        min_my = min(min_my, g.y)
                        max_mx = max(max_mx, g.x + g.width)
                        max_my = max(max_my, g.y + g.height)
                if min_mx < float("inf"):
                    origin_x = int(min_mx)
                    origin_y = int(min_my)
                    win_w = max(64, int(max_mx - min_mx))
                    win_h = max(64, int(max_my - min_my))
            else:
                primary = self.display.get_primary_monitor() or self.display.get_monitor(0)
                if primary:
                    g = primary.get_geometry()
                    origin_x, origin_y, win_w, win_h = g.x, g.y, g.width, g.height
        elif self.screen:
            win_w = max(64, self.screen.get_width())
            win_h = max(64, self.screen.get_height())

        self.origin_x = origin_x
        self.origin_y = origin_y
        self.win_w = win_w
        self.win_h = win_h

        # Retain attributes for backward compatibility
        self.cur_min_x = origin_x
        self.cur_min_y = origin_y
        self.cur_w = win_w
        self.cur_h = win_h

        self.set_default_size(self.win_w, self.win_h)
        self.set_resizable(False)

        # Transparency setup
        if self.screen is not None:
            visual = self.screen.get_rgba_visual()
            if visual is not None:
                self.set_visual(visual)

            css_provider = Gtk.CssProvider()
            css_provider.load_from_data(b"window { background-color: transparent; }")
            Gtk.StyleContext.add_provider_for_screen(
                self.screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            self.get_style_context().add_provider(
                css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        self.realize()
        gdk_win = self.get_window()
        if gdk_win:
            gdk_win.set_override_redirect(True)
            gdk_win.input_shape_combine_region(cairo.Region(), 0, 0)
            try:
                gdk_win.set_background_rgba(Gdk.RGBA(0.0, 0.0, 0.0, 0.0))
            except Exception:
                pass
            try:
                gdk_win.set_background_pattern(None)
            except Exception:
                pass

        self.move(self.origin_x, self.origin_y)
        self.connect("draw", self.on_draw)
        self.show_all()

    def update(self) -> None:
        if self.is_destroyed:
            return
        self.anim_time += 0.05
        try:
            self.queue_draw()
        except Exception:
            pass

    def destroy_rope(self) -> None:
        if not self.is_destroyed:
            self.is_destroyed = True
            try:
                self.destroy()
            except Exception:
                pass

    def on_draw(self, widget, ctx: cairo.Context) -> bool:
        if self.is_destroyed:
            return False

        try:
            p1 = self.start_getter()
            p2 = self.end_getter()
            if not p1 or not p2:
                return False
        except Exception:
            return False

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
            return False

        lx1 = p1[0] - self.origin_x
        ly1 = p1[1] - self.origin_y
        lx2 = p2[0] - self.origin_x
        ly2 = p2[1] - self.origin_y

        dx = lx2 - lx1
        dy = ly2 - ly1
        dist = math.hypot(dx, dy)
        if dist < 3.0:
            return False

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
        return False


class OverlayWindow:
    """Oneko-style floating interactive companion window matching Mjolnir architecture."""

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

        self.display = Gdk.Display.get_default()
        if not self.display:
            print("[Buddy Window] Error: Could not get default display.", file=sys.stderr)
            sys.exit(1)

        self.screen = Gdk.Screen.get_default()
        self.seat = self.display.get_default_seat()
        self.pointer = self.seat.get_pointer() if self.seat else None

        primary = self.display.get_primary_monitor() or self.display.get_monitor(0)
        geom = primary.get_geometry()
        self.screen_w = float(geom.width)
        self.screen_h = float(geom.height)
        self.bounds = (geom.x, geom.y, geom.width, geom.height)

        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_title("Buddy")
        self.window.set_decorated(False)
        self.window.set_app_paintable(True)
        self.window.set_keep_above(True)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_default_size(self.win_size, self.win_size)
        self.window.set_resizable(False)

        self.window.set_accept_focus(False)
        self.window.set_focus_on_map(False)

        visual = self.screen.get_rgba_visual()
        if visual is not None and self.screen.is_composited():
            self.window.set_visual(visual)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"window { background-color: transparent; }")
        Gtk.StyleContext.add_provider_for_screen(
            self.screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.window.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.BUTTON1_MOTION_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.SCROLL_MASK
        )

        self.window.realize()
        self.gdk_window = self.window.get_window()

        self.gdk_window.set_override_redirect(True)
        try:
            self.gdk_window.set_background_rgba(Gdk.RGBA(0.0, 0.0, 0.0, 0.0))
        except Exception:
            pass
        try:
            self.gdk_window.set_background_pattern(None)
        except Exception:
            pass
        self.gdk_window.set_events(
            self.gdk_window.get_events()
            | Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.BUTTON1_MOTION_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.SCROLL_MASK
        )

        self.set_hitbox_mask(radius=54.0)

        def _on_destroy(widget):
            if Gtk.main_level() > 0:
                Gtk.main_quit()

        self.window.connect("draw", on_draw)
        self.window.connect("destroy", _on_destroy)
        if on_button_press:
            self.window.connect("button-press-event", on_button_press)
        if on_button_release:
            self.window.connect("button-release-event", on_button_release)
        if on_motion:
            self.window.connect("motion-notify-event", on_motion)
        if on_scroll:
            self.window.connect("scroll-event", on_scroll)

        self.click_through = False
        self._last_wx: Optional[int] = None
        self._last_wy: Optional[int] = None

    def set_hitbox_mask(self, radius: float = 54.0) -> None:
        if not self.gdk_window:
            return
        size = int(radius * 2)
        box = cairo.RectangleInt(
            x=int(self.half_size - radius),
            y=int(self.half_size - radius),
            width=size,
            height=size
        )
        self.gdk_window.input_shape_combine_region(cairo.Region(box), 0, 0)

    def set_click_through(self, enabled: bool) -> None:
        self.click_through = enabled
        if not self.gdk_window:
            return
        if enabled:
            empty_region = cairo.Region()
            self.gdk_window.input_shape_combine_region(empty_region, 0, 0)
        else:
            self.set_hitbox_mask(radius=54.0)

    def move_to(self, center_x: float, center_y: float) -> None:
        wx = int(center_x - self.half_size)
        wy = int(center_y - self.half_size)
        if wx != self._last_wx or wy != self._last_wy:
            self.window.move(wx, wy)
            self._last_wx = wx
            self._last_wy = wy

    def query_pointer(self) -> Tuple[float, float]:
        if not self.pointer:
            return 500.0, 400.0
        try:
            _, px, py = self.pointer.get_position()
            return float(px), float(py)
        except Exception:
            return 500.0, 400.0

    def trigger_sky_strike(self, target_x: float, target_y: float) -> None:
        SkyStrikeWindow(target_x, target_y)

    def trigger_world_vfx(self, *args, **kwargs) -> None:
        """World VFX stub for Linux parity."""
        pass

    def queue_draw(self) -> None:
        self.window.queue_draw()

    def show(self) -> None:
        self.window.show_all()
