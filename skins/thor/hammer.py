"""Mjolnir (Thor's Hammer) entity with realistic rendering, flight physics, and Asgardian thunder mechanics."""

import math
import random
import time
import cairo
from typing import Tuple, List, Optional
from skins.base import BaseProjectile
from core.particles import ParticleManager, CYAN_GLOW, BLUE_GLOW


class RadialLightning:
    """Branching lightning bolt reaching outward into nearby desktop space."""

    def __init__(self, start_x: float, start_y: float, end_x: float, end_y: float, duration: int = 7, intensity: float = 1.0):
        self.points = self._gen(start_x, start_y, end_x, end_y)
        self.branches: List[List[Tuple[float, float]]] = []
        self.life = duration
        self.age = 0
        self.intensity = intensity

        # Secondary branch forks
        if len(self.points) > 4:
            for _ in range(random.randint(1, 3)):
                b_idx = random.randint(2, len(self.points) - 2)
                bx, by = self.points[b_idx]
                ang = math.atan2(end_y - start_y, end_x - start_x) + random.uniform(-0.85, 0.85)
                blen = math.hypot(end_x - start_x, end_y - start_y) * random.uniform(0.3, 0.6)
                b_end_x = bx + math.cos(ang) * blen
                b_end_y = by + math.sin(ang) * blen
                self.branches.append(self._gen(bx, by, b_end_x, b_end_y, iterations=2))

    def _gen(self, x1: float, y1: float, x2: float, y2: float, iterations: int = 3) -> List[Tuple[float, float]]:
        pts = [(x1, y1), (x2, y2)]
        for _ in range(iterations):
            new_pts = []
            for i in range(len(pts) - 1):
                p1 = pts[i]
                p2 = pts[i + 1]
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

    def update(self) -> bool:
        self.age += 1
        return self.age < self.life

    def draw(self, ctx: cairo.Context) -> None:
        fade = (1.0 - (self.age / self.life)) * self.intensity
        if fade <= 0:
            return

        all_paths = [self.points] + self.branches
        ctx.save()
        ctx.set_line_cap(1)
        ctx.set_line_join(1)

        for path in all_paths:
            if len(path) < 2:
                continue

            def trace():
                ctx.new_path()
                ctx.move_to(path[0][0], path[0][1])
                for pt in path[1:]:
                    ctx.line_to(pt[0], pt[1])

            # 1. Wide Outer Electric Aura
            trace()
            ctx.set_line_width(8.0)
            ctx.set_source_rgba(BLUE_GLOW[0], BLUE_GLOW[1], BLUE_GLOW[2], 0.35 * fade)
            ctx.stroke()

            # 2. Vibrant Neon Cyan Core
            trace()
            ctx.set_line_width(3.2)
            ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], 0.95 * fade)
            ctx.stroke()

            # 3. Brilliant White Core
            trace()
            ctx.set_line_width(1.4)
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.98 * fade)
            ctx.stroke()

        ctx.restore()


class MjolnirSpark:
    """Dynamic electric spark bursting from Mjolnir."""

    def __init__(self, x: float, y: float, vx: float, vy: float, color: Tuple[float, float, float] = CYAN_GLOW, life: int = 18):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.age = 0
        self.size = random.uniform(1.4, 2.6)

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.94
        self.vy *= 0.94
        self.vy += 0.12  # subtle gravity
        self.age += 1
        return self.age < self.life

    def draw(self, ctx: cairo.Context) -> None:
        alpha = max(0.0, 1.0 - (self.age / self.life))
        ctx.save()
        # Glow
        ctx.set_source_rgba(self.color[0], self.color[1], self.color[2], alpha * 0.75)
        ctx.arc(self.x, self.y, self.size * 1.8, 0, 2 * math.pi)
        ctx.fill()
        # White hot center
        ctx.set_source_rgba(1.0, 1.0, 1.0, alpha * 0.95)
        ctx.arc(self.x, self.y, self.size * 0.8, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()


class Mjolnir(BaseProjectile):
    """Thor's legendary Mjolnir hammer with realistic Uru geometry, Norse runes, and lightning."""

    def __init__(self, x: float = 0.0, y: float = 0.0):
        super().__init__(x, y)
        self.state = "HELD"  # "HELD", "THROWN", "ORBITING", "RETURNING"
        self.angular_velocity = 0.0
        self.trail: List[Tuple[float, float, float]] = []  # [(x, y, angle), ...]
        self.lightnings: List[RadialLightning] = []
        self.sparks: List[MjolnirSpark] = []

        # Orbit parameters (centered on Thor to ensure 100% visibility inside window)
        self.orbit_angle = 0.0
        self.orbit_radius_x = 46.0
        self.orbit_radius_y = 36.0
        self.orbit_speed = 0.16
        self.orbit_start_time = 0.0

        # Throw & Boomerang parameters
        self.throw_start_time = 0.0
        self.throw_origin_x = 0.0
        self.throw_origin_y = 0.0
        self.boomerang_phase = 0.0  # 0.0 to 1.0 progress

        # Energy & Visuals
        self.charged_intensity = 0.0
        self.glow_intensity = 0.3
        self.anim_time = 0.0
        self.shockwave_rad = 0.0
        self.shockwave_alpha = 0.0

    def throw(self, start_x: float, start_y: float, target_x: float, target_y: float, mode: str = "boomerang") -> None:
        """Throws Mjolnir in a bounded arc that remains fully visible inside Thor's window."""
        self.x = start_x
        self.y = start_y
        self.throw_origin_x = start_x
        self.throw_origin_y = start_y
        self.state = "THROWN" if mode != "orbit" else "ORBITING"
        self.trail.clear()
        self.charged_intensity = 1.0
        self.glow_intensity = 1.0
        self.throw_start_time = time.time()
        self.orbit_start_time = time.time()

        if mode == "orbit":
            self.orbit_angle = random.uniform(0, 2 * math.pi)
            self.angular_velocity = 0.38
        else:
            # Bounded boomerang strike: fly max 45px towards target, then snap back
            dx = target_x - start_x
            dy = target_y - start_y
            dist = math.hypot(dx, dy) + 1e-4
            speed = 12.0
            self.vx = (dx / dist) * speed
            self.vy = (dy / dist) * speed
            self.angular_velocity = 0.42 * (1.0 if self.vx >= 0 else -1.0)
            self.boomerang_phase = 0.0

        # Initial burst of sparks and radial lightning
        self._spawn_sparks(start_x, start_y, count=10)
        self._spawn_lightning(start_x, start_y, count=2)

    def summon(self) -> None:
        """Magnetically recalls Mjolnir back to Thor's hand."""
        self.state = "RETURNING"
        self.charged_intensity = 1.0
        self.glow_intensity = 1.0

    def catch(self, hand_x: float, hand_y: float) -> None:
        """Catches Mjolnir into Thor's hand."""
        self.state = "HELD"
        self.x = hand_x
        self.y = hand_y
        self.vx = 0.0
        self.vy = 0.0
        self.angular_velocity = 0.0
        self.angle = -0.35
        self.trail.clear()
        self.charged_intensity = 0.6
        self.glow_intensity = 0.5
        self.shockwave_rad = 10.0
        self.shockwave_alpha = 0.8
        self._spawn_sparks(hand_x, hand_y, count=16)

    def _spawn_sparks(self, cx: float, cy: float, count: int = 4) -> None:
        for _ in range(count):
            ang = random.uniform(0, 2 * math.pi)
            spd = random.uniform(2.5, 7.0)
            self.sparks.append(MjolnirSpark(
                cx, cy,
                math.cos(ang) * spd,
                math.sin(ang) * spd,
                color=CYAN_GLOW,
                life=random.randint(12, 22)
            ))

    def _spawn_lightning(self, cx: float, cy: float, count: int = 1) -> None:
        for _ in range(count):
            ang = random.uniform(0, 2 * math.pi)
            dist = random.uniform(22.0, 48.0)
            tx = cx + math.cos(ang) * dist
            ty = cy + math.sin(ang) * dist
            self.lightnings.append(RadialLightning(cx, cy, tx, ty, duration=random.randint(5, 9)))

    def update(
        self,
        hand_x: float,
        hand_y: float,
        cursor_x: float,
        cursor_y: float,
        screen_w: float,
        screen_h: float,
        particle_mgr: ParticleManager,
        thor_x: Optional[float] = None,
        thor_y: Optional[float] = None
    ) -> Optional[str]:
        self.anim_time += 0.06
        now = time.time()
        center_x = thor_x if thor_x is not None else hand_x
        center_y = thor_y if thor_y is not None else hand_y

        # Update and purge sub-effects
        self.lightnings = [l for l in self.lightnings if l.update()]
        self.sparks = [s for s in self.sparks if s.update()]

        # Update shockwave
        if self.shockwave_alpha > 0.0:
            self.shockwave_rad += 3.5
            self.shockwave_alpha -= 0.05
            if self.shockwave_alpha < 0.0:
                self.shockwave_alpha = 0.0

        # Update motion trail when airborne
        if self.state != "HELD":
            self.trail.insert(0, (self.x, self.y, self.angle))
            if len(self.trail) > 8:
                self.trail.pop()
        else:
            self.trail.clear()

        # Decay energy gradually
        if self.charged_intensity > 0.02:
            self.charged_intensity *= 0.96
        if self.glow_intensity > 0.3:
            self.glow_intensity *= 0.97

        # 1. State HELD: firmly gripped by Thor
        if self.state == "HELD":
            self.x = hand_x
            self.y = hand_y
            self.angle = -0.35
            # Subtle occasional crackle while holding
            if random.random() < 0.04:
                self._spawn_sparks(hand_x, hand_y, count=1)

        # 2. State ORBITING: epic 360° thunder vortex around Thor
        elif self.state == "ORBITING":
            self.orbit_angle += self.orbit_speed
            self.x = center_x + math.cos(self.orbit_angle) * self.orbit_radius_x
            self.y = center_y + math.sin(self.orbit_angle) * self.orbit_radius_y
            self.angle += self.angular_velocity
            self.charged_intensity = min(1.0, self.charged_intensity + 0.1)

            if random.random() < 0.35:
                self._spawn_sparks(self.x, self.y, count=2)
            if random.random() < 0.18:
                self._spawn_lightning(self.x, self.y, count=1)

            # Auto-return after 1.2s spin duration
            if now - self.orbit_start_time >= 1.2:
                self.summon()

        # 3. State THROWN: bounded boomerang strike
        elif self.state == "THROWN":
            elapsed = now - self.throw_start_time
            dist_from_thor = math.hypot(self.x - center_x, self.y - center_y)

            # Reverse trajectory like a true boomerang if traveling beyond 45px or after 0.4s
            if dist_from_thor > 45.0 or elapsed >= 0.4:
                self.summon()
            else:
                self.x += self.vx
                self.y += self.vy
                self.angle += self.angular_velocity
                self.vx *= 0.92
                self.vy *= 0.92
                if random.random() < 0.3:
                    self._spawn_sparks(self.x, self.y, count=2)

        # 4. State RETURNING: snapping magnetically back to Thor's hand
        elif self.state == "RETURNING":
            dx = hand_x - self.x
            dy = hand_y - self.y
            dist = math.hypot(dx, dy) + 1e-4

            # Lightning arc connecting Thor's palm to Mjolnir during recall
            if random.random() < 0.5:
                self._spawn_lightning(self.x, self.y, count=1)
                particle_mgr.arc_connect(hand_x, hand_y, self.x, self.y)

            pull_speed = min(28.0, max(12.0, dist * 0.25))
            self.vx = (dx / dist) * pull_speed
            self.vy = (dy / dist) * pull_speed
            self.x += self.vx
            self.y += self.vy
            self.angle += self.angular_velocity * 1.4

            if random.random() < 0.35:
                self._spawn_sparks(self.x, self.y, count=2)

            # Impact catch!
            if dist < 24.0:
                self.catch(hand_x, hand_y)
                particle_mgr.shockwave(hand_x, hand_y, max_radius=70.0)
                particle_mgr.burst_sparks(hand_x, hand_y, count=20, color=CYAN_GLOW)
                return "CAUGHT"

        return None

    def draw_held(self, ctx: cairo.Context, ci: float = 0.0, anim_time: float = 0.0) -> None:
        """Renders Mjolnir directly gripped in Thor's right hand."""
        self._draw_mjolnir_geometry(ctx, ci=ci, anim_time=anim_time, held=True)

    def draw(self, ctx: cairo.Context) -> None:
        """Renders airborne Mjolnir (orbiting/thrown/returning) with glow, trails, lightning, and sparks."""
        # Draw sparks & lightning in world space
        for s in self.sparks:
            s.draw(ctx)
        for l in self.lightnings:
            l.draw(ctx)

        # Draw expanding shockwave ring
        if self.shockwave_alpha > 0:
            ctx.save()
            ctx.set_line_width(2.5 * self.shockwave_alpha)
            ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], max(0.0, self.shockwave_alpha))
            ctx.arc(self.x, self.y, self.shockwave_rad, 0, 2 * math.pi)
            ctx.stroke()
            ctx.restore()

        # If held, Thor's character renderer draws it directly in his hand
        if self.state == "HELD":
            return

        ctx.save()

        # Motion trail
        if len(self.trail) > 1:
            for i, (tx, ty, ta) in enumerate(self.trail):
                alpha = (1.0 - (i / len(self.trail))) * 0.32
                ctx.save()
                ctx.translate(tx, ty)
                ctx.rotate(ta)
                ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], alpha)
                self._draw_mjolnir_geometry(ctx, ci=0.3, anim_time=self.anim_time, held=False, trail=True)
                ctx.restore()

        # Main hammer body
        ctx.translate(self.x, self.y)
        ctx.rotate(self.angle)
        self._draw_mjolnir_geometry(ctx, ci=self.charged_intensity, anim_time=self.anim_time, held=False)
        ctx.restore()

    def _draw_mjolnir_geometry(
        self,
        ctx: cairo.Context,
        ci: float = 0.0,
        anim_time: float = 0.0,
        held: bool = False,
        trail: bool = False
    ) -> None:
        """Renders the authentic Uru metal Mjolnir with Norse runes and leather wrap."""
        # 0. Aura Glow when charged or airborne
        glow_a = max(self.glow_intensity * 0.25, ci * 0.85)
        if glow_a > 0.05 and not trail:
            ctx.save()
            # Wide Cyan Bloom
            ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], glow_a * 0.45)
            ctx.arc(0, -13.0, 26 + (ci * 10), 0, 2 * math.pi)
            ctx.fill()
            # Inner Electric White Halo when charged
            if ci > 0.1:
                ctx.set_source_rgba(1.0, 1.0, 1.0, ci * 0.6)
                ctx.arc(0, -13.0, 16 + (ci * 6), 0, 2 * math.pi)
                ctx.fill()
            ctx.restore()

        if trail:
            hw = 12.0
            hh = 7.0
            ctx.rectangle(-hw, -20.0, hw * 2, hh * 2)
            ctx.fill()
            return

        # 1. Authentic Wooden Handle wrapped with leather and silver bands
        # (Pivot y=0 is precisely where Thor's fist grips the handle!)
        handle_len_down = 10.0
        handle_len_up = 6.0
        handle_w = 3.6

        ctx.save()
        # Handle leather/wood body
        ctx.set_source_rgb(0.24 + 0.3 * ci, 0.14 + 0.4 * ci, 0.08 + 0.5 * ci)
        ctx.rectangle(-handle_w / 2, -handle_len_up, handle_w, handle_len_up + handle_len_down)
        ctx.fill()

        # Silver wrapping bands
        ctx.set_source_rgb(0.82 + 0.18 * ci, 0.85 + 0.15 * ci, 0.90 + 0.10 * ci)
        for y_pos in [-3.0, 1.0, 5.0, 8.5]:
            ctx.rectangle(-handle_w / 2, y_pos, handle_w, 1.0)
            ctx.fill()

        # Silver Pommel cap
        ctx.arc(0, handle_len_down, 2.5, 0, 2 * math.pi)
        ctx.fill()

        # Curved Leather Wrist Strap Loop
        ctx.set_source_rgb(0.32 + 0.2 * ci, 0.18 + 0.3 * ci, 0.10 + 0.4 * ci)
        ctx.set_line_width(1.3)
        ctx.arc(0, handle_len_down + 2.5, 3.2, -math.pi / 2, math.pi / 2)
        ctx.stroke()
        ctx.restore()

        # 2. Asgardian Uru Metal Hammer Head
        hw = 12.0
        hh = 7.0
        chamfer = 2.5
        head_y = -13.0

        ctx.save()
        ctx.new_path()
        ctx.move_to(-hw + chamfer, head_y - hh)
        ctx.line_to(hw - chamfer, head_y - hh)
        ctx.line_to(hw, head_y - hh + chamfer)
        ctx.line_to(hw, head_y + hh - chamfer)
        ctx.line_to(hw - chamfer, head_y + hh)
        ctx.line_to(-hw + chamfer, head_y + hh)
        ctx.line_to(-hw, head_y + hh - chamfer)
        ctx.line_to(-hw, head_y - hh + chamfer)
        ctx.close_path()

        # Realistic metallic gradient shifts to glowing white-hot Uru metal when charged
        pat = cairo.LinearGradient(-hw, head_y - hh, hw, head_y + hh)
        pat.add_color_stop_rgb(0.0, 0.92 + 0.08 * ci, 0.95 + 0.05 * ci, 0.98 + 0.02 * ci)  # Polished specular
        pat.add_color_stop_rgb(0.35, 0.35 + 0.55 * ci, 0.68 + 0.32 * ci, 0.74 + 0.26 * ci)  # Cyan Uru core
        pat.add_color_stop_rgb(1.0, 0.35 + 0.45 * ci, 0.38 + 0.55 * ci, 0.45 + 0.55 * ci)  # Steel shadow
        ctx.set_source(pat)
        ctx.fill_preserve()

        # Metallic border outline
        ctx.set_source_rgb(0.20 + 0.8 * ci, 0.22 + 0.78 * ci, 0.28 + 0.72 * ci)
        ctx.set_line_width(1.0 + 0.8 * ci)
        ctx.stroke()

        # 3. Norse Thor Rune Cross
        rune_pulse = 0.7 + (math.sin(anim_time * 4.0) * 0.3)
        if ci > 0.2:
            ctx.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        else:
            ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], min(1.0, max(0.5, rune_pulse)))

        ctx.set_line_width(1.2 + 1.2 * ci)
        ctx.move_to(-5, head_y)
        ctx.line_to(5, head_y)
        ctx.move_to(0, head_y - 4)
        ctx.line_to(0, head_y + 4)
        ctx.stroke()

        ctx.restore()
