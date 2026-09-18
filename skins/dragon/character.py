"""Dragon character: flapping wings, fire breath cone, fireball projectiles, and gliding flight."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, List
from skins.base import BaseCharacter, CharacterState, BaseProjectile
from skins.manager import skin_manager
from core.particles import ParticleManager, FIRE_ORANGE, FIRE_YELLOW


class Fireball(BaseProjectile):
    """Spit fireball projectile that arcs and explodes into sparks and smoke."""

    def __init__(self, x: float, y: float, vx: float, vy: float):
        super().__init__(x, y)
        self.vx = vx
        self.vy = vy
        self.active = True
        self.life = 1.0

    def update(self, dt: float, screen_bounds: Tuple[int, int, int, int], particle_mgr: ParticleManager, audio_mgr: Any) -> None:
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15  # subtle gravity arc
        self.life -= 0.02
        particle_mgr.flame_puff(self.x, self.y, vx=-self.vx * 0.2, vy=-self.vy * 0.2, count=2, size=4.5)

        min_x, min_y, w, h = screen_bounds
        if self.x < min_x or self.x > min_x + w or self.y > min_y + h or self.life <= 0:
            self.active = False
            particle_mgr.shockwave(self.x, self.y, max_radius=40.0, color=FIRE_ORANGE)
            particle_mgr.burst_sparks(self.x, self.y, count=12, color=FIRE_YELLOW)

    def draw(self, ctx: cairo.Context) -> None:
        if not self.active:
            return
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.set_source_rgba(1.0, 0.4, 0.05, 0.9)
        ctx.arc(0, 0, 7.0, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgba(1.0, 0.9, 0.2, 0.95)
        ctx.arc(0, 0, 3.5, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()


class DragonCharacter(BaseCharacter):
    """Fantasy dragon companion with flapping wings, soaring flight, and fire breath."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="dragon")
        self.can_fly = True
        self.wing_angle = 0.0
        self.wing_speed = 0.18
        self.fireballs: List[Fireball] = []
        self.is_breathing_fire = False
        self.fire_end_time = 0.0
        self.action_timer = time.time() + random.uniform(3.0, 6.0)

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        if ability_name == "fire_breath":
            self.is_breathing_fire = True
            self.fire_end_time = time.time() + 1.2
            audio_mgr.play("fire")
            return True
        elif ability_name == "fireball":
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            dir_mult = 1.0 if self.facing_right else -1.0
            fb = Fireball(self.x + dir_mult * 20.0, self.y - 4.0, (dx / dist) * 15.0, (dy / dist) * 15.0)
            self.fireballs.append(fb)
            audio_mgr.play("fire")
            return True
        elif ability_name in ("flight", "glide"):
            self.vy -= 8.0
            self.state = CharacterState.FLY
            particle_mgr.smoke_puff(self.x, self.y + 16, count=3)
            return True
        return False

    def update(
        self,
        dt: float,
        cursor_x: float,
        cursor_y: float,
        screen_bounds: Tuple[int, int, int, int],
        particle_mgr: ParticleManager,
        audio_mgr: Any,
        config_data: Dict[str, Any]
    ) -> None:
        self.anim_time += 0.05
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)

        # Facing direction
        self.facing_right = (cursor_x >= self.x)

        # Fire breath duration
        if self.is_breathing_fire:
            dir_mult = 1.0 if self.facing_right else -1.0
            mouth_x = self.x + dir_mult * 22.0
            mouth_y = self.y - 4.0
            particle_mgr.flame_puff(
                mouth_x,
                mouth_y,
                vx=dir_mult * random.uniform(6.0, 14.0),
                vy=random.uniform(-3.0, 3.0),
                count=3,
                size=random.uniform(4.0, 8.0)
            )
            if now >= self.fire_end_time:
                self.is_breathing_fire = False

        # Random personality actions
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(4.0, 8.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.40:
                self.trigger_ability("fire_breath", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.70:
                self.trigger_ability("fireball", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.90:
                self.trigger_ability("flight", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Flight physics (soars and hovers near cursor)
        speed_mult = config_data.get("speed", 1.0)
        max_spd = 14.0 * speed_mult
        accel = 0.55 * speed_mult

        target_y = cursor_y - 60.0
        dx = cursor_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)

        if dist > 80.0:
            self.vx += (dx / dist) * min(dist * 0.05, accel)
            self.vy += (dy / dist) * min(dist * 0.05, accel)
            self.state = CharacterState.FLY
        else:
            self.state = CharacterState.HOVER
            self.vx *= 0.88
            self.vy *= 0.88

        self.vx *= 0.92
        self.vy *= 0.92

        spd = math.hypot(self.vx, self.vy)
        if spd > max_spd:
            self.vx = (self.vx / spd) * max_spd
            self.vy = (self.vy / spd) * max_spd

        self.x += self.vx
        self.y += self.vy

        # Wing flapping speed depends on velocity
        self.wing_speed = 0.25 if spd > 2.0 else 0.12
        self.wing_angle = math.sin(self.anim_time * 8.0 * (self.wing_speed / 0.18)) * 0.65

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 50.0, self.y))

        # Dynamic body tilt
        target_tilt = (self.vx / max_spd) * 0.25
        self.tilt += (target_tilt - self.tilt) * 0.15

        # Update active fireballs
        for fb in self.fireballs:
            fb.update(dt, screen_bounds, particle_mgr, audio_mgr)
        self.fireballs = [fb for fb in self.fireballs if fb.active]

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()

        # Draw fireballs
        for fb in self.fireballs:
            fb.draw(ctx)

        ctx.translate(self.x, self.y)
        ctx.rotate(self.tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Back Wing
        ctx.save()
        ctx.translate(-4, -10)
        ctx.rotate(-self.wing_angle - 0.2)
        ctx.set_source_rgb(0.55, 0.12, 0.15)  # Crimson dragon scales
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-16, -26, -2, -34, 18, -26)
        ctx.line_to(12, -14)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # 2. Tail with arrowhead spade
        ctx.set_source_rgb(0.72, 0.18, 0.20)
        ctx.set_line_width(5.0)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.new_path()
        ctx.move_to(-12, 6)
        ctx.curve_to(-24, 10, -32, 2, -38, -6)
        ctx.stroke()

        # Tail tip spade
        ctx.save()
        ctx.translate(-38, -6)
        ctx.rotate(-0.4)
        ctx.new_path()
        ctx.move_to(0, -6)
        ctx.line_to(-8, 0)
        ctx.line_to(0, 6)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # 3. Dragon Body
        ctx.set_source_rgb(0.72, 0.18, 0.20)
        ctx.save()
        ctx.translate(0, 4)
        ctx.scale(1.4, 1.0)
        ctx.arc(0, 0, 15, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # Golden belly scales
        ctx.set_source_rgb(0.95, 0.75, 0.22)
        ctx.save()
        ctx.translate(2, 8)
        ctx.scale(1.1, 0.6)
        ctx.arc(0, 0, 9, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # 4. Front Wing (Large with membrane ridges)
        ctx.save()
        ctx.translate(2, -6)
        ctx.rotate(self.wing_angle)
        # Wing membrane
        ctx.set_source_rgb(0.85, 0.35, 0.20)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-12, -28, 4, -36, 26, -24)
        ctx.line_to(18, -10)
        ctx.close_path()
        ctx.fill()
        # Wing bone ridges
        ctx.set_source_rgb(0.55, 0.10, 0.12)
        ctx.set_line_width(2.0)
        ctx.move_to(0, 0)
        ctx.line_to(4, -36)
        ctx.move_to(0, 0)
        ctx.line_to(26, -24)
        ctx.stroke()
        ctx.restore()

        # 5. Dragon Head & Horns
        ctx.set_source_rgb(0.72, 0.18, 0.20)
        ctx.arc(14, -6, 11, 0, 2 * math.pi)
        ctx.fill()

        # Snout / Jaws
        ctx.rectangle(14, -8, 12, 8)
        ctx.fill()

        # Swept-back Horns
        ctx.set_source_rgb(0.35, 0.35, 0.38)
        ctx.new_path()
        ctx.move_to(8, -14)
        ctx.curve_to(6, -24, -2, -28, -8, -26)
        ctx.curve_to(-4, -22, 2, -18, 12, -12)
        ctx.close_path()
        ctx.fill()

        # Glowing Yellow Reptilian Eye
        ctx.set_source_rgb(1.0, 0.9, 0.1)
        ctx.arc(14, -9, 3.2, 0, 2 * math.pi)
        ctx.fill()
        # Slit pupil
        ctx.set_source_rgb(0.1, 0.05, 0.0)
        ctx.rectangle(13.5, -11, 1.2, 4.0)
        ctx.fill()

        # Smoke from nostrils
        if random.random() < 0.25:
            particle_mgr.smoke_puff(self.x + (26 if self.facing_right else -26), self.y - 6, count=1)

        ctx.restore()


skin_manager.register("dragon", DragonCharacter)
