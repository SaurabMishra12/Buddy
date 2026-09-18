"""Batman character: grappling hook physics, batarang projectiles, and scalloped cape gliding."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, List
from skins.base import BaseCharacter, CharacterState, BaseProjectile
from skins.manager import skin_manager
from core.particles import ParticleManager, SMOKE_GREY


class Batarang(BaseProjectile):
    """Spinning Bat gadget projectile."""

    def __init__(self, x: float, y: float, vx: float, vy: float):
        super().__init__(x, y)
        self.vx = vx
        self.vy = vy
        self.active = True
        self.life = 1.0

    def update(self, dt: float, screen_bounds: Tuple[int, int, int, int], particle_mgr: ParticleManager, audio_mgr: Any) -> None:
        self.x += self.vx
        self.y += self.vy
        self.angle += 0.45
        self.life -= 0.02
        min_x, min_y, w, h = screen_bounds
        if self.x < min_x or self.x > min_x + w or self.y < min_y + h or self.life <= 0:
            self.active = False
            particle_mgr.burst_sparks(self.x, self.y, count=4, color=(0.8, 0.8, 0.8), size=1.5)

    def draw(self, ctx: cairo.Context) -> None:
        if not self.active:
            return
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.rotate(self.angle)
        ctx.set_source_rgb(0.1, 0.1, 0.12)
        ctx.new_path()
        ctx.move_to(-10, 0)
        ctx.curve_to(-5, -6, 5, -6, 10, 0)
        ctx.curve_to(5, 3, -5, 3, -10, 0)
        ctx.fill()
        ctx.restore()


class BatmanCharacter(BaseCharacter):
    """The Dark Knight with grappling hook, cape gliding, and Batarangs."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="batman")
        self.can_fly = True
        self.is_grappling = False
        self.grapple_target = (0.0, 0.0)
        self.batarangs: List[Batarang] = []
        self.is_gliding = False
        self.action_timer = time.time() + random.uniform(3.0, 6.0)

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        if ability_name == "grapple":
            self.is_grappling = True
            # Shoot anchor upward or to cursor
            self.grapple_target = (target_x, min(target_y, self.y - 120.0))
            audio_mgr.play("grapple")
            particle_mgr.burst_sparks(self.grapple_target[0], self.grapple_target[1], count=5, color=(0.8, 0.8, 0.9))
            return True
        elif ability_name == "batarang":
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.batarangs.append(Batarang(self.x, self.y, (dx / dist) * 18.0, (dy / dist) * 18.0))
            audio_mgr.play("grapple")
            return True
        elif ability_name == "cape_glide":
            self.is_gliding = True
            self.vy = 1.0  # gentle descent
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

        # Grappling hook physics
        if self.is_grappling:
            gx, gy = self.grapple_target
            dx = gx - self.x
            dy = gy - self.y
            dist = math.hypot(dx, dy)
            if dist > 20.0:
                self.vx += (dx / dist) * 2.2
                self.vy += (dy / dist) * 2.2
                self.state = "GRAPPLE"
            else:
                self.is_grappling = False
                self.state = CharacterState.FLY
                self.is_gliding = True
                particle_mgr.smoke_puff(self.x, self.y + 10, count=2)

        # Random personality events
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(4.0, 8.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.45:
                self.trigger_ability("grapple", cursor_x, cursor_y - 150.0, particle_mgr, audio_mgr)
            elif roll < 0.75:
                self.trigger_ability("batarang", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Standard movement
        speed_mult = config_data.get("speed", 1.0)
        max_spd = 14.0 * speed_mult
        accel = 0.60 * speed_mult

        tx = cursor_x - (40.0 if self.facing_right else -40.0)
        ty = cursor_y - 30.0
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)

        if not self.is_grappling:
            if dist > 60.0:
                self.vx += (dx / dist) * min(dist * 0.06, accel)
                self.vy += (dy / dist) * min(dist * 0.06, accel)
                self.state = CharacterState.FLY
            else:
                self.state = CharacterState.HOVER
                self.vx *= 0.88
                self.vy *= 0.88

        self.vx *= 0.90
        self.vy *= 0.90

        spd = math.hypot(self.vx, self.vy)
        if spd > max_spd:
            self.vx = (self.vx / spd) * max_spd
            self.vy = (self.vy / spd) * max_spd

        self.x += self.vx
        self.y += self.vy

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 50.0, self.y))

        # Dynamic body tilt
        target_tilt = (self.vx / max_spd) * 0.25
        self.tilt += (target_tilt - self.tilt) * 0.15

        # Update Batarangs
        for b in self.batarangs:
            b.update(dt, screen_bounds, particle_mgr, audio_mgr)
        self.batarangs = [b for b in self.batarangs if b.active]

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()

        # Draw batarangs
        for b in self.batarangs:
            b.draw(ctx)

        # Draw grappling line if active
        if self.is_grappling:
            ctx.save()
            ctx.set_source_rgba(0.2, 0.2, 0.25, 0.9)
            ctx.set_line_width(1.6)
            ctx.move_to(self.x, self.y - 4)
            ctx.line_to(self.grapple_target[0], self.grapple_target[1])
            ctx.stroke()
            ctx.restore()

        ctx.translate(self.x, self.y)
        ctx.rotate(self.tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Scalloped Gliding Bat Cape
        ctx.save()
        ctx.set_source_rgb(0.08, 0.08, 0.10)  # Dark cowl black
        ctx.new_path()
        ctx.move_to(-4, -8)
        # Scalloped edges
        ctx.curve_to(-18, 0, -28, 8, -26, 26)
        ctx.curve_to(-20, 20, -14, 26, -10, 22)
        ctx.curve_to(-6, 26, 0, 20, 4, 24)
        ctx.line_to(4, -8)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # 2. Body & Grey Batsuit
        ctx.set_source_rgb(0.28, 0.30, 0.34)  # Tactical grey suit
        ctx.rectangle(-9, -8, 18, 22)
        ctx.fill()

        # Golden Utility Belt
        ctx.set_source_rgb(0.85, 0.70, 0.15)
        ctx.rectangle(-10, 10, 20, 4.5)
        ctx.fill()
        for bx in [-6, -2, 2, 6]:
            ctx.set_source_rgb(0.70, 0.55, 0.10)
            ctx.rectangle(bx, 9, 3, 6)
            ctx.fill()

        # Bat Emblem on Chest
        ctx.set_source_rgb(0.08, 0.08, 0.10)
        ctx.new_path()
        ctx.move_to(-7, -4)
        ctx.line_to(0, -6)
        ctx.line_to(7, -4)
        ctx.line_to(4, 2)
        ctx.line_to(0, 5)
        ctx.line_to(-4, 2)
        ctx.close_path()
        ctx.fill()

        # 3. Cowl & Pointed Bat Ears
        ctx.set_source_rgb(0.08, 0.08, 0.10)
        ctx.arc(0, -15, 9, 0, 2 * math.pi)
        ctx.fill()

        # Pointed Bat Ears
        for ear_x, ear_rot in [(-5, -0.15), (5, 0.15)]:
            ctx.save()
            ctx.translate(ear_x, -21)
            ctx.rotate(ear_rot)
            ctx.new_path()
            ctx.move_to(-3, 4)
            ctx.line_to(0, -9)
            ctx.line_to(3, 4)
            ctx.close_path()
            ctx.fill()
            ctx.restore()

        # White glowing cowl eye lenses
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.new_path()
        ctx.move_to(-5, -16)
        ctx.line_to(-1, -14)
        ctx.line_to(-5, -13)
        ctx.close_path()
        ctx.fill()

        ctx.new_path()
        ctx.move_to(5, -16)
        ctx.line_to(1, -14)
        ctx.line_to(5, -13)
        ctx.close_path()
        ctx.fill()

        # Gauntlet blades
        ctx.set_source_rgb(0.12, 0.12, 0.15)
        ctx.rectangle(8, -4, 4, 12)
        ctx.fill()
        for blade_y in [0, 4, 8]:
            ctx.move_to(12, blade_y)
            ctx.line_to(16, blade_y + 2)
            ctx.line_to(12, blade_y + 3)
            ctx.fill()

        ctx.restore()


skin_manager.register("batman", BatmanCharacter)
