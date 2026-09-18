"""Iron Man character: repulsor blasts, rocket boot thrusters, and air dash."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from skins.manager import skin_manager
from core.particles import ParticleManager, CYAN_GLOW, FIRE_YELLOW, FIRE_ORANGE


class IronManCharacter(BaseCharacter):
    """Tony Stark in high-tech Mark armor with jet flight and repulsor attacks."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="ironman")
        self.can_fly = True
        self.arc_glow = 0.8
        self.is_firing_repulsor = False
        self.repulsor_end = 0.0
        self.repulsor_target = (0.0, 0.0)
        self.action_timer = time.time() + random.uniform(3.0, 6.0)

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        if ability_name == "repulsor_blast":
            self.is_firing_repulsor = True
            self.repulsor_end = time.time() + 0.35
            self.repulsor_target = (target_x, target_y)
            particle_mgr.burst_sparks(target_x, target_y, count=10, color=CYAN_GLOW)
            particle_mgr.shockwave(target_x, target_y, max_radius=45.0, color=CYAN_GLOW)
            audio_mgr.play("jet")
            return True
        elif ability_name == "air_dash":
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.vx = (dx / dist) * 26.0
            self.vy = (dy / dist) * 26.0
            self.state = CharacterState.FLY
            particle_mgr.flame_puff(self.x, self.y + 15, count=6, size=8.0)
            audio_mgr.play("jet")
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

        if self.is_firing_repulsor and now >= self.repulsor_end:
            self.is_firing_repulsor = False

        # Random personality events
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(4.0, 8.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.50:
                self.trigger_ability("repulsor_blast", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.75:
                self.trigger_ability("air_dash", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Flight movement
        speed_mult = config_data.get("speed", 1.0)
        max_spd = 16.0 * speed_mult
        accel = 0.70 * speed_mult

        tx = cursor_x - (40.0 if self.facing_right else -40.0)
        ty = cursor_y - 45.0
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)

        if dist > 30.0:
            self.vx += (dx / dist) * min(dist * 0.08, accel)
            self.vy += (dy / dist) * min(dist * 0.08, accel)
            self.state = CharacterState.FLY
        else:
            self.state = CharacterState.HOVER
            self.vx *= 0.86
            self.vy *= 0.86

        self.vx *= 0.90
        self.vy *= 0.90

        spd = math.hypot(self.vx, self.vy)
        if spd > max_spd:
            self.vx = (self.vx / spd) * max_spd
            self.vy = (self.vy / spd) * max_spd

        self.x += self.vx
        self.y += self.vy

        # Jet boot flame particles
        boot_y = self.y + 26.0
        boot_left_x = self.x - 6.0
        boot_right_x = self.x + 6.0
        particle_mgr.flame_puff(boot_left_x, boot_y, vy=random.uniform(2.0, 5.0), count=1, size=4.0)
        particle_mgr.flame_puff(boot_right_x, boot_y, vy=random.uniform(2.0, 5.0), count=1, size=4.0)

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 50.0, self.y))

        # Dynamic body tilt
        target_tilt = (self.vx / max_spd) * 0.30
        self.tilt += (target_tilt - self.tilt) * 0.15

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()

        # Draw repulsor beam if firing
        if self.is_firing_repulsor:
            ctx.save()
            ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], 0.85)
            ctx.set_line_width(6.0)
            ctx.new_path()
            ctx.move_to(self.x + (16 if self.facing_right else -16), self.y - 2)
            ctx.line_to(self.repulsor_target[0], self.repulsor_target[1])
            ctx.stroke()
            # White core
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            ctx.set_line_width(2.0)
            ctx.stroke()
            ctx.restore()

        ctx.translate(self.x, self.y)
        ctx.rotate(self.tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Armored Legs & Jet Boots
        ctx.set_source_rgb(0.78, 0.12, 0.15)  # Hot rod crimson red
        ctx.rectangle(-7, 10, 5, 14)
        ctx.rectangle(2, 10, 5, 14)
        ctx.fill()
        # Gold knee plates
        ctx.set_source_rgb(0.92, 0.75, 0.22)
        ctx.rectangle(-7, 14, 5, 4)
        ctx.rectangle(2, 14, 5, 4)
        ctx.fill()
        # Jet boots
        ctx.set_source_rgb(0.78, 0.12, 0.15)
        ctx.rectangle(-8, 22, 6, 6)
        ctx.rectangle(1, 22, 6, 6)
        ctx.fill()

        # 2. Torso Armor
        ctx.set_source_rgb(0.78, 0.12, 0.15)
        ctx.rectangle(-10, -10, 20, 22)
        ctx.fill()
        # Gold flank armor
        ctx.set_source_rgb(0.92, 0.75, 0.22)
        ctx.rectangle(-10, -6, 3, 14)
        ctx.rectangle(7, -6, 3, 14)
        ctx.fill()

        # Glowing Arc Reactor (Unibeam)
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(0, -1, 3.8, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], 0.8)
        ctx.set_line_width(1.8)
        ctx.stroke()

        # 3. Arms & Repulsor Palms
        # Left Arm
        ctx.set_source_rgb(0.78, 0.12, 0.15)
        ctx.rectangle(-14, -8, 4, 15)
        ctx.fill()
        # Right Arm (active outstretched forward)
        ctx.rectangle(10, -8, 12, 4)
        ctx.fill()
        # Palm repulsor
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(22, -6, 2.5, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], 0.7)
        ctx.arc(22, -6, 4.5, 0, 2 * math.pi)
        ctx.fill()

        # 4. Helmet & Gold Faceplate
        ctx.set_source_rgb(0.78, 0.12, 0.15)
        ctx.arc(0, -18, 9, 0, 2 * math.pi)
        ctx.fill()

        # Iconic Gold Faceplate
        ctx.set_source_rgb(0.92, 0.75, 0.22)
        ctx.new_path()
        ctx.move_to(-5, -24)
        ctx.line_to(5, -24)
        ctx.line_to(6, -15)
        ctx.line_to(3, -11)
        ctx.line_to(-3, -11)
        ctx.line_to(-6, -15)
        ctx.close_path()
        ctx.fill()

        # Glowing Eye Slits
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.rectangle(-4, -18, 3, 1.5)
        ctx.rectangle(2, -18, 3, 1.5)
        ctx.fill()
        ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], 0.9)
        ctx.set_line_width(0.8)
        ctx.stroke()

        ctx.restore()


skin_manager.register("ironman", IronManCharacter)
