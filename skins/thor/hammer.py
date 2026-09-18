"""Mjolnir (Thor's Hammer) entity with flight physics, rotation, and summoning mechanics."""

import math
import random
import cairo
from typing import Tuple, List, Optional
from skins.base import BaseProjectile
from core.particles import ParticleManager, CYAN_GLOW, BLUE_GLOW

HAMMER_SPIN_SPEED = 0.35
HAMMER_MAX_SPEED = 32.0
HAMMER_SUMMON_PULL = 1.6
HAMMER_TRAIL_LENGTH = 12


class Mjolnir(BaseProjectile):
    """Thor's legendary hammer with autonomous flight, boomerang arcs, and magnetic recall."""

    def __init__(self, x: float = 0.0, y: float = 0.0):
        super().__init__(x, y)
        self.state = "HELD"  # "HELD", "THROWN", "ORBITING", "RETURNING"
        self.angular_velocity = 0.0
        self.trail: List[Tuple[float, float, float]] = []  # [(x, y, angle), ...]
        self.target = (0.0, 0.0)
        self.orbit_angle = 0.0
        self.orbit_radius = 60.0
        self.orbit_speed = 0.06
        self.glow_intensity = 0.0

    def throw(self, start_x: float, start_y: float, target_x: float, target_y: float, mode: str = "boomerang") -> None:
        self.x = start_x
        self.y = start_y
        self.state = "THROWN" if mode != "orbit" else "ORBITING"
        dx = target_x - start_x
        dy = target_y - start_y
        dist = math.hypot(dx, dy) + 1e-4

        base_speed = random.uniform(18.0, 24.0)
        self.vx = (dx / dist) * base_speed
        self.vy = (dy / dist) * base_speed
        if mode == "boomerang":
            self.vy -= 6.0
            self.vx += random.uniform(-4.0, 4.0)

        self.angular_velocity = HAMMER_SPIN_SPEED * (1.2 if random.random() > 0.5 else -1.2)
        self.trail.clear()
        self.glow_intensity = 1.0

    def summon(self) -> None:
        """Magnetically summon Mjolnir back to Thor's hand."""
        self.state = "RETURNING"
        self.glow_intensity = 1.0

    def catch(self, hand_x: float, hand_y: float) -> None:
        self.state = "HELD"
        self.x = hand_x
        self.y = hand_y
        self.vx = 0.0
        self.vy = 0.0
        self.angular_velocity = 0.0
        self.angle = -0.3
        self.trail.clear()
        self.glow_intensity = 0.4

    def update(
        self,
        hand_x: float,
        hand_y: float,
        cursor_x: float,
        cursor_y: float,
        screen_w: float,
        screen_h: float,
        particle_mgr: ParticleManager
    ) -> Optional[str]:
        # Update motion trail
        if self.state != "HELD":
            self.trail.insert(0, (self.x, self.y, self.angle))
            if len(self.trail) > HAMMER_TRAIL_LENGTH:
                self.trail.pop()
        else:
            self.trail.clear()

        # Decay glow
        if self.glow_intensity > 0.1 and self.state == "HELD":
            self.glow_intensity *= 0.95

        # State behaviors
        if self.state == "HELD":
            self.x = hand_x
            self.y = hand_y
            self.angle = -0.35

        elif self.state == "THROWN":
            self.x += self.vx
            self.y += self.vy
            self.angle += self.angular_velocity

            # Air drag & curve
            self.vx *= 0.985
            self.vy *= 0.985
            self.vy += 0.15

            # Screen bounds bounce
            padding = 40.0
            if self.x < padding or self.x > screen_w - padding:
                self.vx = -self.vx * 0.9
                particle_mgr.burst_sparks(self.x, self.y, count=8)
            if self.y < padding or self.y > screen_h - padding:
                self.vy = -self.vy * 0.9
                particle_mgr.burst_sparks(self.x, self.y, count=8)

            if random.random() < 0.3:
                particle_mgr.burst_sparks(self.x, self.y, count=2)

        elif self.state == "ORBITING":
            self.orbit_angle += self.orbit_speed
            target_cx = cursor_x + math.cos(self.orbit_angle) * self.orbit_radius
            target_cy = cursor_y + math.sin(self.orbit_angle) * (self.orbit_radius * 0.6)
            self.x += (target_cx - self.x) * 0.15
            self.y += (target_cy - self.y) * 0.15
            self.angle += self.angular_velocity
            if random.random() < 0.25:
                particle_mgr.burst_sparks(self.x, self.y, count=2)

        elif self.state == "RETURNING":
            dx = hand_x - self.x
            dy = hand_y - self.y
            dist = math.hypot(dx, dy) + 1e-4

            # Electric arc connecting Thor's palm and Mjolnir during recall
            if random.random() < 0.6:
                particle_mgr.arc_connect(hand_x, hand_y, self.x, self.y)

            pull = min(HAMMER_MAX_SPEED, (dist * 0.08) + HAMMER_SUMMON_PULL * 3.0)
            self.vx += (dx / dist) * pull
            self.vy += (dy / dist) * pull

            current_speed = math.hypot(self.vx, self.vy)
            if current_speed > HAMMER_MAX_SPEED:
                self.vx = (self.vx / current_speed) * HAMMER_MAX_SPEED
                self.vy = (self.vy / current_speed) * HAMMER_MAX_SPEED

            self.x += self.vx
            self.y += self.vy
            self.angle += self.angular_velocity * 1.5

            particle_mgr.burst_sparks(self.x, self.y, count=3)

            # Impact catch
            if dist < 32.0:
                self.catch(hand_x, hand_y)
                particle_mgr.sky_strike(hand_x, hand_y)
                particle_mgr.shockwave(hand_x, hand_y, max_radius=80.0)
                particle_mgr.burst_sparks(hand_x, hand_y, count=24)
                return "CAUGHT"

        return None

    def draw(self, ctx: cairo.Context) -> None:
        ctx.save()

        # Motion trail
        if self.state in ("THROWN", "RETURNING", "ORBITING") and len(self.trail) > 1:
            for i, (tx, ty, ta) in enumerate(self.trail):
                alpha = (1.0 - (i / len(self.trail))) * 0.28
                ctx.save()
                ctx.translate(tx, ty)
                ctx.rotate(ta)
                ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], alpha)
                self._draw_hammer_geometry(ctx, glow=True)
                ctx.restore()

        # Main hammer body
        ctx.translate(self.x, self.y)
        ctx.rotate(self.angle)

        if self.glow_intensity > 0.05:
            ctx.save()
            ctx.set_source_rgba(BLUE_GLOW[0], BLUE_GLOW[1], BLUE_GLOW[2], self.glow_intensity * 0.5)
            ctx.arc(0, 0, 22, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

        self._draw_hammer_geometry(ctx, glow=False)
        ctx.restore()

    def _draw_hammer_geometry(self, ctx: cairo.Context, glow: bool = False) -> None:
        if glow:
            ctx.rectangle(-14, -8, 28, 16)
            ctx.set_line_width(4)
            ctx.stroke()
            return

        # 1. Wooden handle wrapped with leather and silver bands
        handle_len = 22.0
        handle_w = 4.5
        ctx.save()
        ctx.set_source_rgb(0.28, 0.16, 0.10)
        ctx.rectangle(-handle_w / 2, 0, handle_w, handle_len)
        ctx.fill()

        ctx.set_source_rgb(0.78, 0.82, 0.88)
        for y_pos in [4, 9, 14, 19]:
            ctx.rectangle(-handle_w / 2, y_pos, handle_w, 1.2)
            ctx.fill()

        ctx.arc(0, handle_len + 1.0, 3.2, 0, 2 * math.pi)
        ctx.fill()

        # Leather strap loop
        ctx.set_source_rgb(0.35, 0.20, 0.12)
        ctx.set_line_width(1.8)
        ctx.arc(0, handle_len + 5.0, 4.0, -math.pi / 2, math.pi / 2)
        ctx.stroke()
        ctx.restore()

        # 2. Asgardian Uru Metal Hammer Head
        hw = 13.0
        hh = 7.5
        chamfer = 3.0

        ctx.save()
        ctx.new_path()
        ctx.move_to(-hw + chamfer, -hh)
        ctx.line_to(hw - chamfer, -hh)
        ctx.line_to(hw, -hh + chamfer)
        ctx.line_to(hw, hh - chamfer)
        ctx.line_to(hw - chamfer, hh)
        ctx.line_to(-hw + chamfer, hh)
        ctx.line_to(-hw, hh - chamfer)
        ctx.line_to(-hw, -hh + chamfer)
        ctx.close_path()

        pat = cairo.LinearGradient(-hw, -hh, hw, hh)
        pat.add_color_stop_rgb(0.0, 0.88, 0.90, 0.94)  # Polished Uru highlight
        pat.add_color_stop_rgb(0.4, 0.65, 0.70, 0.76)  # Mid metallic grey
        pat.add_color_stop_rgb(1.0, 0.38, 0.42, 0.48)  # Shadow
        ctx.set_source(pat)
        ctx.fill_preserve()

        ctx.set_source_rgb(0.25, 0.28, 0.32)
        ctx.set_line_width(1.2)
        ctx.stroke()

        # Center runic engraving
        ctx.set_source_rgba(0.0, 0.85, 1.0, 0.7)
        ctx.set_line_width(1.0)
        ctx.move_to(-6, 0)
        ctx.line_to(6, 0)
        ctx.move_to(0, -4)
        ctx.line_to(0, 4)
        ctx.stroke()

        # Runic side bevels
        ctx.set_source_rgba(0.2, 0.22, 0.26, 0.8)
        ctx.rectangle(-hw + 2, -hh + 2, 3, hh * 2 - 4)
        ctx.fill()
        ctx.rectangle(hw - 5, -hh + 2, 3, hh * 2 - 4)
        ctx.fill()
        ctx.restore()
