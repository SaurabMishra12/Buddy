"""Harry Potter character: wand spellcasting, flying broomstick, and teleportation."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from skins.manager import skin_manager
from core.particles import ParticleManager, MAGIC_PURPLE, MAGIC_GOLD


class HarryPotterCharacter(BaseCharacter):
    """Wizard desktop pet with wand spells, broom flight, and magical teleportation."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="harry_potter")
        self.can_fly = True
        self.riding_broom = True
        self.action_timer = time.time() + random.uniform(3.0, 6.0)

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        wand_x = self.x + (20.0 if self.facing_right else -20.0)
        wand_y = self.y - 2.0

        if ability_name == "cast_spell":
            particle_mgr.arc_connect(wand_x, wand_y, target_x, target_y, branches=1, color=MAGIC_GOLD)
            particle_mgr.burst_sparks(target_x, target_y, count=12, color=MAGIC_PURPLE)
            particle_mgr.shockwave(target_x, target_y, max_radius=40.0, color=MAGIC_GOLD)
            audio_mgr.play("magic")
            return True
        elif ability_name == "teleport":
            particle_mgr.smoke_puff(self.x, self.y, count=6, color=(0.7, 0.4, 0.8))
            particle_mgr.burst_sparks(self.x, self.y, count=10, color=MAGIC_GOLD)
            self.x = target_x + random.uniform(-40, 40)
            self.y = target_y + random.uniform(-40, 40)
            particle_mgr.smoke_puff(self.x, self.y, count=6, color=(0.7, 0.4, 0.8))
            audio_mgr.play("teleport")
            return True
        elif ability_name == "broom_flight":
            self.riding_broom = not self.riding_broom
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

        # Random spell cast / teleport
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(4.0, 8.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.60:
                self.trigger_ability("cast_spell", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.85:
                self.trigger_ability("teleport", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Flight movement
        speed_mult = config_data.get("speed", 1.0)
        max_spd = 13.0 * speed_mult
        accel = 0.55 * speed_mult

        target_y = cursor_y - 40.0
        dx = cursor_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)

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

        # Sparkles trailing broom
        if self.riding_broom and random.random() < 0.35:
            tail_x = self.x - (22.0 if self.facing_right else -22.0)
            particle_mgr.burst_sparks(tail_x, self.y + 12, count=1, color=MAGIC_GOLD, size=1.8)

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 50.0, self.y))

        # Dynamic body tilt
        target_tilt = (self.vx / max_spd) * 0.22
        self.tilt += (target_tilt - self.tilt) * 0.15

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.rotate(self.tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Flying Broomstick (Nimbus / Firebolt)
        if self.riding_broom:
            ctx.save()
            ctx.set_source_rgb(0.40, 0.22, 0.10)  # Wood handle
            ctx.set_line_width(3.5)
            ctx.move_to(-28, 14)
            ctx.line_to(22, 6)
            ctx.stroke()
            # Golden twig twigs at tail
            ctx.set_source_rgb(0.75, 0.55, 0.18)
            ctx.new_path()
            ctx.move_to(-22, 13)
            ctx.line_to(-38, 10)
            ctx.line_to(-36, 19)
            ctx.close_path()
            ctx.fill()
            ctx.restore()

        # 2. Gryffindor Black Robes & Scarlet Scarf
        ctx.set_source_rgb(0.12, 0.12, 0.15)  # Black robe
        ctx.rectangle(-8, -8, 16, 22)
        ctx.fill()

        # Scarlet & Gold Gryffindor Scarf
        for i, col in enumerate([(0.75, 0.1, 0.15), (0.95, 0.78, 0.15), (0.75, 0.1, 0.15)]):
            ctx.set_source_rgb(col[0], col[1], col[2])
            ctx.rectangle(-7, -8 + i * 3, 14, 3)
            ctx.fill()

        # 3. Arms & Wand
        # Robe sleeve
        ctx.set_source_rgb(0.12, 0.12, 0.15)
        ctx.rectangle(4, -6, 12, 4.5)
        ctx.fill()
        # Hand
        ctx.set_source_rgb(0.95, 0.78, 0.65)
        ctx.arc(16, -4, 2.5, 0, 2 * math.pi)
        ctx.fill()
        # Magic wand
        ctx.set_source_rgb(0.35, 0.18, 0.08)
        ctx.set_line_width(1.8)
        ctx.move_to(16, -4)
        ctx.line_to(25, -2)
        ctx.stroke()

        # 4. Head & Messy Black Hair
        ctx.set_source_rgb(0.95, 0.78, 0.65)
        ctx.arc(0, -15, 9, 0, 2 * math.pi)
        ctx.fill()

        # Messy black hair
        ctx.set_source_rgb(0.1, 0.1, 0.1)
        ctx.arc(0, -18, 9, math.pi, 2 * math.pi)
        ctx.fill()
        ctx.rectangle(-8, -20, 16, 4)
        ctx.fill()

        # Iconic Round Glasses
        ctx.set_source_rgb(0.2, 0.2, 0.2)
        ctx.set_line_width(1.2)
        ctx.arc(-2.5, -15, 3.2, 0, 2 * math.pi)
        ctx.stroke()
        ctx.arc(4.5, -15, 3.2, 0, 2 * math.pi)
        ctx.stroke()
        ctx.move_to(0.5, -15)
        ctx.line_to(1.5, -15)
        ctx.stroke()

        # Eyes behind glasses
        ctx.set_source_rgb(0.1, 0.45, 0.2)  # Lily's green eyes
        ctx.arc(-2.5, -15, 1.2, 0, 2 * math.pi)
        ctx.arc(4.5, -15, 1.2, 0, 2 * math.pi)
        ctx.fill()

        # Lightning Bolt Scar on Forehead!
        ctx.set_source_rgb(0.85, 0.2, 0.2)
        ctx.set_line_width(1.0)
        ctx.new_path()
        ctx.move_to(1, -21)
        ctx.line_to(3, -19)
        ctx.line_to(1, -19)
        ctx.line_to(3, -17)
        ctx.stroke()

        ctx.restore()


skin_manager.register("harry_potter", HarryPotterCharacter)
