"""Screen-wide desktop projectile overlay: handles long-range thrown shields, hammers, and fireballs."""

import math
import random
import time
import cairo
from typing import Tuple, List, Optional, Callable, Dict, Any

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from core.particles import CYAN_GLOW, BLUE_GLOW, FIRE_ORANGE, FIRE_YELLOW
from core.audio import audio_manager
from core.window import WebRopeWindow


class DesktopProjectileWindow(Gtk.Window):
    """Floating transparent window for long-range projectiles traveling across the entire monitor."""

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
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.proj_type = proj_type
        self.owner_getter = owner_getter
        self.on_catch = on_catch
        self.win_size = 110
        self.half_size = 55.0

        self.set_title("BuddyProjectile")
        self.set_decorated(False)
        self.set_app_paintable(True)
        self.set_keep_above(True)
        self.set_accept_focus(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_default_size(self.win_size, self.win_size)
        self.set_resizable(False)

        screen = Gdk.Screen.get_default()
        visual = screen.get_rgba_visual()
        if visual is not None:
            self.set_visual(visual)

        self.realize()
        gdk_win = self.get_window()
        gdk_win.set_override_redirect(True)
        # 100% click-through
        gdk_win.input_shape_combine_region(cairo.Region(), 0, 0)

        # Monitor screen dimensions
        display = Gdk.Display.get_default()
        primary = display.get_primary_monitor() or display.get_monitor(0)
        geom = primary.get_geometry()
        self.screen_w = float(geom.width)
        self.screen_h = float(geom.height)

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
        initial_wx = int(self.x - self.half_size)
        initial_wy = int(self.y - self.half_size)
        self.move(initial_wx, initial_wy)
        self._last_wx = initial_wx
        self._last_wy = initial_wy
        self.explosion_frame = 0

        # Dedicated full-length web rope overlay connecting hero wrist to projectile
        self.rope_window: Optional[WebRopeWindow] = None
        if self.proj_type == "web":
            try:
                self.rope_window = WebRopeWindow(
                    start_getter=self._get_owner_wrist,
                    end_getter=lambda: (self.x, self.y),
                    rope_style="throw",
                    alpha_getter=self._get_web_alpha
                )
            except Exception:
                self.rope_window = None

        def _on_destroy(widget):
            self._cleanup_rope()

        self.connect("destroy", _on_destroy)
        self.connect("draw", self.on_draw)
        GLib.timeout_add(16, self.on_tick)
        self.show_all()

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

    def destroy_projectile(self) -> None:
        self._cleanup_rope()
        try:
            self.destroy()
        except Exception:
            pass

    def on_tick(self) -> bool:
        self.angle += self.angular_velocity

        # Update full-length web rope overlay
        if self.rope_window:
            self.rope_window.update()

        # Update trail
        self.trail.insert(0, (self.half_size, self.half_size, self.angle))
        if len(self.trail) > 7:
            self.trail.pop()

        # Update sparks
        for s in self.sparks:
            s["x"] += s["vx"]
            s["y"] += s["vy"]
            s["life"] -= 1
        self.sparks = [s for s in self.sparks if s["life"] > 0]

        # Shockwave
        if self.shockwave_alpha > 0:
            self.shockwave_rad += 3.0
            self.shockwave_alpha -= 0.06

        if self.state == "OUTBOUND":
            self.x += self.vx
            self.y += self.vy

            # Collision check: Screen boundary or target proximity
            padding = 45.0
            hit_edge = (self.x <= padding or self.x >= self.screen_w - padding or self.y <= padding or self.y >= self.screen_h - padding)
            hit_target = math.hypot(self.x - self.target_x, self.y - self.target_y) < 30.0

            if hit_edge or hit_target:
                # Screen edge or target collision!
                self._trigger_collision()
                if self.proj_type in ("fireball", "web"):
                    self.state = "EXPLODING"
                    self.explosion_frame = 0
                else:
                    self.state = "RETURNING"

        elif self.state == "RETURNING":
            # Boomerang spring-damper return to hero's actual position
            hx, hy = self.owner_getter()
            dx = hx - self.x
            dy = hy - self.y
            dist = math.hypot(dx, dy) + 1e-4

            pull = min(32.0, max(16.0, dist * 0.12))
            self.vx += (dx / dist) * pull * 0.4
            self.vy += (dy / dist) * pull * 0.4

            spd = math.hypot(self.vx, self.vy)
            if spd > 28.0:
                self.vx = (self.vx / spd) * 28.0
                self.vy = (self.vy / spd) * 28.0

            self.x += self.vx
            self.y += self.vy

            # Impact catch by hero's hand
            if dist < 38.0:
                if self.on_catch:
                    self.on_catch()
                if self.proj_type == "fireball":
                    audio_manager.play("fire")
                elif self.proj_type == "shield":
                    audio_manager.play("smash")
                else:
                    audio_manager.play("lightning")
                self._cleanup_rope()
                self.destroy()
                return False

        elif self.state == "EXPLODING":
            self.explosion_frame += 1
            if self.explosion_frame > 14:
                self._cleanup_rope()
                self.destroy()
                return False

        # Move the transparent window to current position
        wx = int(self.x - self.half_size)
        wy = int(self.y - self.half_size)
        if wx != self._last_wx or wy != self._last_wy:
            self.move(wx, wy)
            self._last_wx = wx
            self._last_wy = wy
        self.queue_draw()
        return True

    def _trigger_collision(self) -> None:
        """Called when projectile collides with monitor boundary or target."""
        self.shockwave_rad = 8.0
        self.shockwave_alpha = 1.0

        for _ in range(16):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(3.0, 8.0)
            if self.proj_type == "power_blast":
                col = (0.85, 0.20, 1.0)
            elif self.proj_type in ("shield", "mjolnir", "unibeam"):
                col = CYAN_GLOW
            else:
                col = FIRE_YELLOW
            self.sparks.append({
                "x": self.half_size,
                "y": self.half_size,
                "vx": math.cos(ang) * spd,
                "vy": math.sin(ang) * spd,
                "color": col,
                "life": random.randint(12, 24)
            })

        if self.proj_type in ("shield", "mjolnir", "fireball"):
            if self.proj_type == "shield":
                audio_manager.play("smash")
            elif self.proj_type == "mjolnir":
                audio_manager.play("lightning")
            elif self.proj_type == "fireball":
                audio_manager.play("fire")
            self.state = "RETURNING"
            # Reverse bounce direction
            self.vx = -self.vx * 0.7
            self.vy = -self.vy * 0.7
        elif self.proj_type == "power_blast":
            audio_manager.play("smash")
            self.state = "EXPLODING"
        elif self.proj_type == "web":
            audio_manager.play("thwip")
            self.state = "EXPLODING"
        else:
            # Repulsor blast detonates on impact
            audio_manager.play("laser")
            self.state = "EXPLODING"

    def on_draw(self, widget: Gtk.Widget, ctx: cairo.Context) -> bool:
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()
        ctx.restore()

        ctx.set_operator(cairo.OPERATOR_OVER)

        # Draw sparks
        for s in self.sparks:
            alpha = s["life"] / 20.0
            ctx.set_source_rgba(s["color"][0], s["color"][1], s["color"][2], alpha)
            ctx.arc(s["x"], s["y"], 2.0, 0, 2 * math.pi)
            ctx.fill()

        # Draw shockwave
        if self.shockwave_alpha > 0:
            ctx.set_line_width(3.5 * self.shockwave_alpha)
            if self.proj_type == "power_blast":
                col = (0.75, 0.10, 0.95)
            elif self.proj_type in ("shield", "mjolnir", "unibeam"):
                col = CYAN_GLOW
            elif self.proj_type == "web":
                col = (0.92, 0.96, 1.0)
            else:
                col = FIRE_ORANGE
            ctx.set_source_rgba(col[0], col[1], col[2], self.shockwave_alpha)
            ctx.arc(self.half_size, self.half_size, self.shockwave_rad, 0, 2 * math.pi)
            ctx.stroke()

        if self.state == "EXPLODING":
            if self.proj_type == "web":
                # Expanding intricate spider-web net blossom
                net_rad = 12.0 + self.explosion_frame * 4.5
                alpha = max(0.0, 1.0 - self.explosion_frame / 20.0)
                ctx.save()
                ctx.translate(self.half_size, self.half_size)

                # Outer sticky silk splash droplets
                ctx.set_source_rgba(0.95, 0.98, 1.0, alpha * 0.75)
                for di in range(12):
                    dang = di * (math.pi / 6.0) + 0.15
                    d_dist = net_rad * 1.15
                    ctx.arc(math.cos(dang) * d_dist, math.sin(dang) * d_dist, 2.2, 0, 2 * math.pi)
                    ctx.fill()

                # 12 Radiating structural web spokes
                ctx.set_source_rgba(1.0, 1.0, 1.0, alpha * 0.95)
                ctx.set_line_width(1.8)
                ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                spoke_count = 12
                for i in range(spoke_count):
                    ang = i * (2 * math.pi / spoke_count)
                    ctx.move_to(0, 0)
                    ctx.line_to(math.cos(ang) * net_rad, math.sin(ang) * net_rad)
                    ctx.stroke()

                # 4 Concentric geometric web spiral rings with catenary drooping curves
                ctx.set_source_rgba(0.88, 0.94, 1.0, alpha * 0.85)
                ctx.set_line_width(1.3)
                for ring_f in [0.25, 0.50, 0.75, 1.0]:
                    r = net_rad * ring_f
                    ctx.new_path()
                    for i in range(spoke_count):
                        ang = i * (2 * math.pi / spoke_count)
                        px = math.cos(ang) * r
                        py = math.sin(ang) * r
                        if i == 0:
                            ctx.move_to(px, py)
                        else:
                            prev_ang = (i - 1) * (2 * math.pi / spoke_count)
                            mid_ang = (prev_ang + ang) * 0.5
                            sag_r = r * 0.91
                            ctrl_x = math.cos(mid_ang) * sag_r
                            ctrl_y = math.sin(mid_ang) * sag_r
                            ctx.quad_to(ctrl_x, ctrl_y, px, py)
                    ctx.close_path()
                    ctx.stroke()

                # Center anchor impact knot
                ctx.set_source_rgba(1.0, 1.0, 1.0, alpha)
                ctx.arc(0, 0, 3.8, 0, 2 * math.pi)
                ctx.fill()
                ctx.restore()
            else:
                # Explosion blast
                rad = 12.0 + self.explosion_frame * 3.2
                alpha = max(0.0, 1.0 - self.explosion_frame / 14.0)
                pat = cairo.RadialGradient(self.half_size, self.half_size, 2, self.half_size, self.half_size, rad)
                if self.proj_type == "power_blast":
                    pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, alpha)
                    pat.add_color_stop_rgba(0.4, 0.95, 0.20, 1.0, alpha * 0.9)
                    pat.add_color_stop_rgba(1.0, 0.50, 0.05, 0.85, 0.0)
                elif self.proj_type in ("unibeam", "repulsor"):
                    pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, alpha)
                    pat.add_color_stop_rgba(0.35, CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], alpha * 0.95)
                    pat.add_color_stop_rgba(1.0, 0.05, 0.35, 0.95, 0.0)
                else:
                    pat.add_color_stop_rgba(0.0, 1.0, 1.0, 0.9, alpha)
                    pat.add_color_stop_rgba(0.4, 1.0, 0.5, 0.1, alpha * 0.8)
                    pat.add_color_stop_rgba(1.0, 0.8, 0.1, 0.0, 0.0)
                ctx.set_source(pat)
                ctx.arc(self.half_size, self.half_size, rad, 0, 2 * math.pi)
                ctx.fill()
            return False

        # Motion trail
        if len(self.trail) > 1:
            for i, (tx, ty, ta) in enumerate(self.trail):
                alpha = (1.0 - (i / len(self.trail))) * 0.25
                ctx.save()
                ctx.translate(tx, ty)
                ctx.rotate(ta)
                self._draw_projectile_mesh(ctx, alpha=alpha)
                ctx.restore()

        # Main projectile body
        ctx.save()
        ctx.translate(self.half_size, self.half_size)
        ctx.rotate(self.angle)
        self._draw_projectile_mesh(ctx, alpha=1.0)
        ctx.restore()

        return False

    def _draw_projectile_mesh(self, ctx: cairo.Context, alpha: float = 1.0) -> None:
        if self.proj_type == "shield":
            # Captain America's Vibranium Shield
            # Outer Red
            ctx.set_source_rgba(0.85, 0.12, 0.15, alpha)
            ctx.arc(0, 0, 24, 0, 2 * math.pi)
            ctx.fill()

            # Specular metallic sheen gradient
            pat = cairo.LinearGradient(-24, -24, 24, 24)
            pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.35 * alpha)
            pat.add_color_stop_rgba(0.5, 1.0, 1.0, 1.0, 0.0)
            pat.add_color_stop_rgba(1.0, 0.0, 0.0, 0.0, 0.25 * alpha)
            ctx.set_source(pat)
            ctx.arc(0, 0, 24, 0, 2 * math.pi)
            ctx.fill()

            # White / Silver Ring
            ctx.set_source_rgba(0.92, 0.94, 0.98, alpha)
            ctx.arc(0, 0, 18, 0, 2 * math.pi)
            ctx.fill()

            # Inner Red Ring
            ctx.set_source_rgba(0.85, 0.12, 0.15, alpha)
            ctx.arc(0, 0, 13, 0, 2 * math.pi)
            ctx.fill()

            # Blue Center
            ctx.set_source_rgba(0.12, 0.28, 0.72, alpha)
            ctx.arc(0, 0, 8, 0, 2 * math.pi)
            ctx.fill()

            # 5-Pointed Silver Star
            ctx.set_source_rgba(1.0, 1.0, 1.0, alpha)
            ctx.new_path()
            star_rad_out = 7.0
            star_rad_in = 2.8
            for pt in range(10):
                r = star_rad_out if pt % 2 == 0 else star_rad_in
                a = (pt * math.pi / 5.0) - (math.pi / 2.0)
                px = math.cos(a) * r
                py = math.sin(a) * r
                if pt == 0:
                    ctx.move_to(px, py)
                else:
                    ctx.line_to(px, py)
            ctx.close_path()
            ctx.fill()

        elif self.proj_type == "mjolnir":
            # Thor's Mjolnir
            # Uru metal head
            hw = 15.0
            hh = 9.0
            ctx.set_source_rgba(0.70, 0.75, 0.82, alpha)
            ctx.rectangle(-hw, -hh - 4, hw * 2, hh * 2)
            ctx.fill()

            # Rune
            ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], alpha)
            ctx.set_line_width(1.8)
            ctx.move_to(-6, -4)
            ctx.line_to(6, -4)
            ctx.move_to(0, -9)
            ctx.line_to(0, 1)
            ctx.stroke()

            # Handle
            ctx.set_source_rgba(0.28, 0.15, 0.08, alpha)
            ctx.rectangle(-2.5, 4, 5, 18)
            ctx.fill()
            ctx.set_source_rgba(0.85, 0.88, 0.92, alpha)
            for y in [8, 12, 16, 20]:
                ctx.rectangle(-2.5, y, 5, 1.2)
                ctx.fill()

        elif self.proj_type == "fireball":
            # Dragon Fireball
            rad = 18.0
            pat = cairo.RadialGradient(0, 0, 3, 0, 0, rad)
            pat.add_color_stop_rgba(0.0, 1.0, 1.0, 0.9, alpha)
            pat.add_color_stop_rgba(0.4, FIRE_YELLOW[0], FIRE_YELLOW[1], FIRE_YELLOW[2], 0.9 * alpha)
            pat.add_color_stop_rgba(0.8, FIRE_ORANGE[0], FIRE_ORANGE[1], FIRE_ORANGE[2], 0.7 * alpha)
            pat.add_color_stop_rgba(1.0, 0.8, 0.1, 0.0, 0.0)
            ctx.set_source(pat)
            ctx.arc(0, 0, rad, 0, 2 * math.pi)
            ctx.fill()

        elif self.proj_type == "repulsor":
            # Iron Man Plasma Bolt
            rad = 16.0
            pat = cairo.RadialGradient(0, 0, 2, 0, 0, rad)
            pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, alpha)
            pat.add_color_stop_rgba(0.4, CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], 0.85 * alpha)
            pat.add_color_stop_rgba(1.0, BLUE_GLOW[0], BLUE_GLOW[1], BLUE_GLOW[2], 0.0)
            ctx.set_source(pat)
            ctx.arc(0, 0, rad, 0, 2 * math.pi)
            ctx.fill()

        elif self.proj_type == "unibeam":
            # Iron Man Colossal Chest Arc Reactor Unibeam
            rad = 24.0
            pat = cairo.RadialGradient(0, 0, 3, 0, 0, rad)
            pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, alpha)
            pat.add_color_stop_rgba(0.35, 0.35, 0.95, 1.0, 0.95 * alpha)
            pat.add_color_stop_rgba(0.70, 0.05, 0.55, 1.0, 0.70 * alpha)
            pat.add_color_stop_rgba(1.0, 0.0, 0.15, 0.75, 0.0)
            ctx.set_source(pat)
            ctx.arc(0, 0, rad, 0, 2 * math.pi)
            ctx.fill()

            # Concentric expanding pulse rings
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.90 * alpha)
            ctx.set_line_width(2.2)
            ctx.arc(0, 0, 9.0, 0, 2 * math.pi)
            ctx.stroke()
            ctx.set_source_rgba(0.20, 0.90, 1.0, 0.75 * alpha)
            ctx.set_line_width(1.4)
            ctx.arc(0, 0, 17.0, 0, 2 * math.pi)
            ctx.stroke()

            # Spiraling arc filaments
            ctx.set_source_rgba(0.85, 0.98, 1.0, 0.95 * alpha)
            for ang in [0.0, 1.57, 3.14, 4.71]:
                px = math.cos(ang + self.angle * 3.5) * 14.0
                py = math.sin(ang + self.angle * 3.5) * 14.0
                ctx.arc(px, py, 2.5, 0, 2 * math.pi)
                ctx.fill()

        elif self.proj_type == "power_blast":
            # Thanos Power Stone Cosmic Energy Orb
            rad = 19.0
            pat = cairo.RadialGradient(0, 0, 2, 0, 0, rad)
            pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, alpha)
            pat.add_color_stop_rgba(0.35, 0.95, 0.20, 1.0, 0.95 * alpha)
            pat.add_color_stop_rgba(0.75, 0.60, 0.05, 0.85, 0.85 * alpha)
            pat.add_color_stop_rgba(1.0, 0.25, 0.0, 0.40, 0.0)
            ctx.set_source(pat)
            ctx.arc(0, 0, rad, 0, 2 * math.pi)
            ctx.fill()

            # Orbiting cosmic power sparks
            ctx.set_source_rgba(1.0, 0.85, 0.25, 0.9 * alpha)
            for ang in [0.0, 1.25, 2.5, 3.75, 5.0]:
                px = math.cos(ang + self.angle * 2.0) * 12.0
                py = math.sin(ang + self.angle * 2.0) * 12.0
                ctx.arc(px, py, 2.0, 0, 2 * math.pi)
                ctx.fill()

        elif self.proj_type == "web":
            # Spider-Man High-Velocity Spun Web Missile & Spiral Silk Stream
            ctx.save()

            # Trailing aerodynamic silk wisps extending behind projectile
            ctx.set_source_rgba(0.92, 0.96, 1.0, 0.70 * alpha)
            ctx.set_line_width(1.4)
            for trail_ang, trail_len in [(-2.7, 24.0), (-3.14, 30.0), (-3.6, 22.0)]:
                ctx.new_path()
                ctx.move_to(0, 0)
                tx1 = math.cos(trail_ang) * (trail_len * 0.5)
                ty1 = math.sin(trail_ang) * (trail_len * 0.5) + math.sin(self.angle * 6.0) * 3.5
                tx2 = math.cos(trail_ang) * trail_len
                ty2 = math.sin(trail_ang) * trail_len + math.sin(self.angle * 6.0 + 1.2) * 5.0
                ctx.curve_to(tx1, ty1, tx1, ty1, tx2, ty2)
                ctx.stroke()

            # Spinning Web Core
            ctx.rotate(self.angle * 4.0)

            # Outer luminous silk halo
            ctx.set_source_rgba(0.85, 0.92, 1.0, 0.35 * alpha)
            ctx.arc(0, 0, 15.0, 0, 2 * math.pi)
            ctx.fill()

            # Central coiled web core with bright silk density
            pat_core = cairo.RadialGradient(0, 0, 2, 0, 0, 9.0)
            pat_core.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 1.0 * alpha)
            pat_core.add_color_stop_rgba(0.65, 0.90, 0.95, 1.0, 0.95 * alpha)
            pat_core.add_color_stop_rgba(1.0, 0.70, 0.85, 1.0, 0.40 * alpha)
            ctx.set_source(pat_core)
            ctx.arc(0, 0, 9.0, 0, 2 * math.pi)
            ctx.fill()

            # 8 High-tensile radial web filaments
            ctx.set_source_rgba(0.95, 0.98, 1.0, 0.95 * alpha)
            ctx.set_line_width(1.6)
            for rad_ang in [0.0, 0.785, 1.57, 2.356, 3.14, 3.927, 4.712, 5.498]:
                ctx.move_to(0, 0)
                ctx.line_to(math.cos(rad_ang) * 14.0, math.sin(rad_ang) * 14.0)
                ctx.stroke()

            # Octagonal bounding silk tension ring
            ctx.new_path()
            for i in range(8):
                ang = i * (math.pi / 4.0)
                px = math.cos(ang) * 12.0
                py = math.sin(ang) * 12.0
                if i == 0:
                    ctx.move_to(px, py)
                else:
                    ctx.line_to(px, py)
            ctx.close_path()
            ctx.stroke()

            ctx.restore()
