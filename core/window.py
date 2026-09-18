"""Oneko-style floating interactive window management matching Mjolnir desktop pet architecture.

Eliminates full-screen dimming/fading by using a lightweight floating window that tracks
the pet's position across the desktop, with seamless input transparency for background windows.
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
        self.max_frames = 24

        self.connect("draw", self.on_draw)
        GLib.timeout_add(16, self.on_tick)
        self.show_all()

    def on_tick(self):
        self.frames += 1
        self.bolt1.update()
        self.bolt2.update()
        if self.frames >= self.max_frames:
            self.destroy()
            return False
        self.queue_draw()
        return True

    def on_draw(self, widget, ctx):
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()
        ctx.restore()

        ctx.set_operator(cairo.OPERATOR_OVER)
        if self.frames in (0, 1, 2, 5, 6, 9):
            flicker = 1.0
        elif self.frames in (3, 4, 7, 8):
            flicker = 0.65
        else:
            flicker = max(0.0, 1.0 - ((self.frames - 9) / 15.0))

        self.bolt1.intensity = flicker
        self.bolt2.intensity = flicker * 0.7
        self.bolt1.draw(ctx)
        self.bolt2.draw(ctx)
        return False


class OverlayWindow:
    """Oneko-style floating interactive companion window matching Mjolnir architecture."""

    def __init__(
        self,
        on_draw: Callable,
        on_button_press: Optional[Callable] = None,
        on_button_release: Optional[Callable] = None,
        on_motion: Optional[Callable] = None
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

        # Determine full screen bounds
        primary = self.display.get_primary_monitor() or self.display.get_monitor(0)
        geom = primary.get_geometry()
        self.screen_w = float(geom.width)
        self.screen_h = float(geom.height)
        self.bounds = (geom.x, geom.y, geom.width, geom.height)

        # Window creation: 180x180 floating pet window
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_title("Buddy")
        self.window.set_decorated(False)
        self.window.set_app_paintable(True)
        self.window.set_keep_above(True)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_default_size(self.win_size, self.win_size)
        self.window.set_resizable(False)

        # Zero focus theft prevents Mutter/GNOME from dimming or fading the desktop!
        self.window.set_accept_focus(False)
        self.window.set_focus_on_map(False)

        # Enable RGBA visual for transparency
        visual = self.screen.get_rgba_visual()
        if visual is not None and self.screen.is_composited():
            self.window.set_visual(visual)

        # CSS transparency override
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"window { background-color: transparent; }")
        Gtk.StyleContext.add_provider_for_screen(
            self.screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Realize window to access low-level GDK/X11 window
        self.window.realize()
        self.gdk_window = self.window.get_window()

        # override_redirect allows free travel anywhere on screen without WM borders
        self.gdk_window.set_override_redirect(True)

        # Set active input shape around character:
        # Clicks within this 80x80 box interact with the pet (drag, double-click, right-click options)
        # Everywhere else on desktop passes through 100% cleanly!
        self.set_hitbox_mask(radius=42.0)

        # Event masks
        self.window.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.BUTTON1_MOTION_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )

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

        self.click_through = False

    def set_hitbox_mask(self, radius: float = 42.0) -> None:
        """Sets active clickable input region around center, letting rest of screen pass clicks through."""
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
        """Toggle whether clicks pass 100% through to background windows."""
        self.click_through = enabled
        if not self.gdk_window:
            return
        if enabled:
            empty_region = cairo.Region()
            self.gdk_window.input_shape_combine_region(empty_region, 0, 0)
        else:
            self.set_hitbox_mask(radius=42.0)

    def move_to(self, center_x: float, center_y: float) -> None:
        """Positions window so (HALF_SIZE, HALF_SIZE) aligns exactly with (center_x, center_y)."""
        wx = int(center_x - self.half_size)
        wy = int(center_y - self.half_size)
        self.window.move(wx, wy)

    def query_pointer(self) -> Tuple[float, float]:
        """Global pointer coordinates."""
        if not self.pointer:
            return 500.0, 400.0
        try:
            _, px, py = self.pointer.get_position()
            return float(px), float(py)
        except Exception:
            return 500.0, 400.0

    def trigger_sky_strike(self, target_x: float, target_y: float) -> None:
        """Summons colossal lightning bolt from top of screen to target coordinates."""
        SkyStrikeWindow(target_x, target_y)

    def queue_draw(self) -> None:
        self.window.queue_draw()

    def show(self) -> None:
        self.window.show_all()
