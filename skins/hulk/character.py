"""Hulk character: heavy stomping, ground smash with crater particles, shockwaves, and roar."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from skins.manager import skin_manager
from core.particles import ParticleManager


class HulkCharacter(BaseCharacter):
    """The Incredible Hulk with ground smashes, high leaps, and roar rage."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="hulk")
        self.can_fly = False
        self.hitbox_radius = 45.0
        self.is_smashing = False
        self.smash_end = 0.0
        self.rage_aura = 0.0
        self.action_timer = time.time() + random.uniform(3.0, 7.0)

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        if ability_name == "hulk_smash":
            self.is_smashing = True
            self.smash_end = time.time() + 0.6
            self.vy = 8.0  # slam downward
            particle_mgr.shockwave(self.x, self.y + 24, max_radius=80.0, color=(0.2, 0.8, 0.2), line_width=4.0)
            particle_mgr.burst_sparks(self.x, self.y + 24, count=18, color=(0.4, 0.9, 0.2))
            particle_mgr.smoke_puff(self.x, self.y + 24, count=6, color=(0.45, 0.40, 0.35))
            audio_mgr.play("smash")
            return True
        elif ability_name == "super_jump":
            dx = target_x - self.x
            self.vx = max(-14.0, min(14.0, dx * 0.08))
            self.vy = -18.0  # massive upward leap
            self.state = CharacterState.JUMP
            particle_mgr.smoke_puff(self.x, self.y + 24, count=4, color=(0.45, 0.40, 0.35))
            audio_mgr.play("smash")
            return True
        elif ability_name == "roar":
            self.rage_aura = 1.0
            particle_mgr.shockwave(self.x, self.y - 10, max_radius=55.0, color=(0.3, 0.9, 0.3))
            audio_mgr.play("smash")
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
        ground_y = min_y + screen_h - 70.0

        # Facing direction
        self.facing_right = (cursor_x >= self.x)

        if self.is_smashing and now >= self.smash_end:
            self.is_smashing = False

        if self.rage_aura > 0.05:
            self.rage_aura *= 0.94

        # Random ability triggers
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(4.0, 8.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.40:
                self.trigger_ability("hulk_smash", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.70:
                self.trigger_ability("super_jump", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.90:
                self.trigger_ability("roar", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Ground-based movement physics with gravity
        speed_mult = config_data.get("speed", 1.0)
        max_spd = 10.0 * speed_mult
        accel = 0.50 * speed_mult

        # Apply gravity
        if self.y < ground_y:
            self.vy += 0.85  # strong gravity
            self.is_airborne = True
        else:
            self.y = ground_y
            if self.vy > 6.0:  # Hard landing impact!
                particle_mgr.shockwave(self.x, self.y + 24, max_radius=45.0, color=(0.4, 0.8, 0.2))
                particle_mgr.smoke_puff(self.x, self.y + 24, count=3)
            self.vy = 0.0
            self.is_airborne = False

        # Cursor follow horizontally
        dx = cursor_x - self.x
        dist_x = abs(dx)

        if dist_x > 80.0 and config_data.get("cursor_follow", True) and not self.is_smashing:
            dir_x = 1.0 if dx > 0 else -1.0
            self.vx += dir_x * accel
            if not self.is_airborne:
                self.state = CharacterState.RUN if dist_x > 250.0 else CharacterState.WALK
        else:
            self.vx *= 0.82
            if not self.is_airborne:
                self.state = CharacterState.IDLE

        self.vx *= 0.90

        if abs(self.vx) > max_spd:
            self.vx = (self.vx / abs(self.vx)) * max_spd

        self.x += self.vx
        self.y += self.vy

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = min(ground_y, max(min_y + 60.0, self.y))

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # Rage aura glow
        if self.rage_aura > 0.05:
            ctx.save()
            ctx.set_source_rgba(0.2, 0.9, 0.2, self.rage_aura * 0.4)
            ctx.arc(0, 0, 36, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

        # 1. Massive Muscular Legs & Purple Torn Shorts
        ctx.set_source_rgb(0.18, 0.58, 0.22)  # Jade Hulk green
        ctx.rectangle(-12, 14, 9, 16)
        ctx.rectangle(3, 14, 9, 16)
        ctx.fill()

        # Torn Purple Shorts
        ctx.set_source_rgb(0.42, 0.18, 0.55)
        ctx.rectangle(-14, 8, 28, 12)
        ctx.fill()
        # Jagged torn cloth hem
        ctx.new_path()
        for x_step in range(-14, 15, 4):
            ctx.line_to(x_step, 20 + (x_step % 3))
        ctx.stroke()

        # 2. Giant Muscular Torso & Chest Pecks
        ctx.set_source_rgb(0.20, 0.64, 0.25)
        ctx.rectangle(-16, -12, 32, 24)
        ctx.fill()

        # Pectorals definition
        ctx.set_source_rgb(0.15, 0.48, 0.18)
        ctx.set_line_width(1.8)
        ctx.arc(-7, -4, 6, 0, math.pi)
        ctx.stroke()
        ctx.arc(7, -4, 6, 0, math.pi)
        ctx.stroke()

        # 3. Massive Arms & Fists
        if self.is_smashing:
            # Both giant fists raised high overhead
            ctx.set_source_rgb(0.20, 0.64, 0.25)
            ctx.rectangle(-18, -26, 10, 18)
            ctx.rectangle(8, -26, 10, 18)
            ctx.fill()
            ctx.arc(-13, -28, 7.5, 0, 2 * math.pi)
            ctx.arc(13, -28, 7.5, 0, 2 * math.pi)
            ctx.fill()
        else:
            # Arms at side with clenched fists
            ctx.set_source_rgb(0.20, 0.64, 0.25)
            ctx.rectangle(-22, -8, 9, 22)
            ctx.rectangle(13, -8, 9, 22)
            ctx.fill()
            # Fists
            ctx.arc(-17.5, 16, 7.0, 0, 2 * math.pi)
            ctx.arc(17.5, 16, 7.0, 0, 2 * math.pi)
            ctx.fill()

        # 4. Head & Shaggy Hair
        ctx.set_source_rgb(0.20, 0.64, 0.25)
        ctx.arc(0, -18, 12, 0, 2 * math.pi)
        ctx.fill()

        # Shaggy dark hair
        ctx.set_source_rgb(0.1, 0.15, 0.1)
        ctx.arc(0, -22, 12, math.pi, 2 * math.pi)
        ctx.fill()

        # Brow & Angered Eyes
        ctx.set_source_rgb(0.9, 0.9, 0.2)  # Glowing enraged eyes
        ctx.arc(-4, -18, 1.8, 0, 2 * math.pi)
        ctx.arc(4, -18, 1.8, 0, 2 * math.pi)
        ctx.fill()

        # Heavy furrowed brow
        ctx.set_source_rgb(0.12, 0.40, 0.15)
        ctx.set_line_width(2.0)
        ctx.move_to(-8, -21)
        ctx.line_to(-1, -19)
        ctx.line_to(1, -19)
        ctx.line_to(8, -21)
        ctx.stroke()

        ctx.restore()


skin_manager.register("hulk", HulkCharacter)
