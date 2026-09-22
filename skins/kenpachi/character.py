"""Kenpachi Zaraki desktop companion: Nozarashi, Demonic Bankai, Bell Hair, and Unstoppable Battle Lust."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, Optional

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager


class KenpachiCharacter(BaseCharacter):
    """Kenpachi Zaraki — Captain of the 11th Division."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="kenpachi")
        self.can_fly = False
        self.is_bankai = False

        # States: "SHOULDER_SWORD", "ADJUST_EYEPATCH", "LAUGH", "BORED", "NOZARASHI", "BANKAI"
        self.substate = "SHOULDER_SWORD"
        self.substate_timer = time.time() + random.uniform(5.0, 10.0)
        self.ability_end_time = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        now = time.time()
        if ability_name in ("nozarashi", "special"):
            self.substate = "NOZARASHI"
            self.ability_end_time = now + 2.5
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.85, 0.05, 0.1), count=22)
            particle_mgr.shockwave(self.x, self.y, max_radius=115.0, color=(0.9, 0.1, 0.1), line_width=4.0)
            if audio_mgr:
                audio_mgr.play("roar")
            return True

        elif ability_name == "bankai_rage":
            self.is_bankai = not self.is_bankai
            self.substate = "BANKAI" if self.is_bankai else "SHOULDER_SWORD"
            self.ability_end_time = now + 5.0 if self.is_bankai else 0.0
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.95, 0.0, 0.05), count=30)
            particle_mgr.shockwave(self.x, self.y, max_radius=140.0, color=(1.0, 0.0, 0.0), line_width=5.0)
            if audio_mgr:
                audio_mgr.play("roar")
            return True

        elif ability_name == "adjust_eyepatch":
            self.substate = "ADJUST_EYEPATCH"
            self.substate_timer = now + 3.0
            return True

        elif ability_name == "maniac_laugh":
            self.substate = "LAUGH"
            self.substate_timer = now + 3.5
            if audio_mgr:
                audio_mgr.play("roar")
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
        self.anim_time += dt * 4.5
        now = time.time()

        if self.ability_end_time > 0 and now > self.ability_end_time:
            self.substate = "SHOULDER_SWORD"
            self.ability_end_time = 0.0

        is_moving = math.hypot(self.vx, self.vy) > 0.5
        if is_moving:
            self.substate = "SHOULDER_SWORD"
        else:
            if self.ability_end_time <= 0 and now >= self.substate_timer:
                self.substate_timer = now + random.uniform(6.0, 13.0)
                options = ["SHOULDER_SWORD", "SHOULDER_SWORD", "ADJUST_EYEPATCH", "LAUGH", "BORED"]
                self.substate = random.choice(options)

        # Ambient yellow Reiatsu sparks or Bankai blood aura
        if self.is_bankai:
            if random.random() < 0.35:
                particle_mgr.burst_reiatsu(self.x, self.y + 10, color=(0.9, 0.05, 0.1), count=2)
        elif random.random() < 0.08:
            particle_mgr.burst_sparks(self.x, self.y + 5, count=2, color=(1.0, 0.85, 0.2))

        # Facing direction
        if abs(cursor_x - self.x) > 12.0:
            self.facing_right = (cursor_x >= self.x)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1, 1)

        # Muscular breathing bob
        bob_y = math.sin(self.anim_time * 2.0) * 1.0
        ctx.translate(0, bob_y)

        # Demonic Bankai Reiatsu aura
        if self.is_bankai or self.substate == "BANKAI":
            ctx.save()
            pulse = math.sin(self.anim_time * 5.0) * 0.08
            ctx.set_source_rgba(0.9, 0.05, 0.1, 0.25 + pulse)
            ctx.arc(0, 0, 44.0, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

        # 1. Legs and Hakama
        self._draw_legs(ctx)

        # 2. Muscular Torso & Shredded Sleeveless Haori
        self._draw_torso(ctx)

        # 3. Head, Spiked Hair with Brass Bells, Eyepatch & Grin
        self._draw_head(ctx)

        # 4. Arms & Giant Sword / Nozarashi Cleaver
        self._draw_arms_and_weapon(ctx)

        ctx.restore()

    def _draw_legs(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Black hakama
        ctx.set_source_rgb(0.1, 0.1, 0.12)
        ctx.rectangle(-9, 14, 8, 14)
        ctx.rectangle(2, 14, 8, 14)
        ctx.fill()
        # White tabi & waraji
        ctx.set_source_rgb(0.92, 0.92, 0.94)
        ctx.rectangle(-9, 28, 8, 4)
        ctx.rectangle(2, 28, 8, 4)
        ctx.fill()
        ctx.restore()

    def _draw_torso(self, ctx: cairo.Context) -> None:
        ctx.save()
        skin_color = (0.78, 0.18, 0.18) if self.is_bankai else (0.95, 0.78, 0.65)

        # Muscular exposed chest
        ctx.set_source_rgb(*skin_color)
        ctx.rectangle(-10, -10, 20, 18)
        ctx.fill()
        # Pectoral & abdominal definition
        ctx.set_source_rgb(0.2, 0.1, 0.1 if self.is_bankai else 0.5)
        ctx.set_line_width(0.9)
        ctx.move_to(0, -6)
        ctx.line_to(0, 6)
        ctx.stroke()

        # Black Shihakushō waist
        ctx.set_source_rgb(0.12, 0.12, 0.14)
        ctx.rectangle(-11, 6, 22, 9)
        ctx.fill()

        # White Captain's Haori (Sleeveless with ragged shredded hem)
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        ctx.new_path()
        ctx.move_to(-14, -10)
        ctx.line_to(-10, -10)
        ctx.line_to(-11, 20)
        ctx.line_to(-16, 22)
        ctx.close_path()
        ctx.fill()

        ctx.new_path()
        ctx.move_to(10, -10)
        ctx.line_to(14, -10)
        ctx.line_to(16, 22)
        ctx.line_to(11, 20)
        ctx.close_path()
        ctx.fill()

        # Ragged jagged hem cuts on haori
        ctx.set_source_rgb(0.12, 0.12, 0.14)
        for rx in (-15, -13, 12, 14):
            ctx.new_path()
            ctx.move_to(rx, 20)
            ctx.line_to(rx + 1, 17)
            ctx.line_to(rx + 2, 20)
            ctx.close_path()
            ctx.fill()
        ctx.restore()

    def _draw_head(self, ctx: cairo.Context) -> None:
        ctx.save()
        head_y = -20
        skin_color = (0.82, 0.20, 0.20) if self.is_bankai else (0.95, 0.80, 0.68)

        # Face & Jaw
        ctx.set_source_rgb(*skin_color)
        ctx.new_path()
        ctx.move_to(-7, head_y - 6)
        ctx.line_to(7, head_y - 6)
        ctx.line_to(6, head_y + 4)
        ctx.line_to(0, head_y + 9)  # Sharp rugged jaw
        ctx.line_to(-6, head_y + 4)
        ctx.close_path()
        ctx.fill()

        # Long facial scar running down left eye
        ctx.set_source_rgb(0.5, 0.1, 0.1)
        ctx.set_line_width(1.1)
        ctx.move_to(-3, head_y - 8)
        ctx.line_to(-3, head_y + 5)
        ctx.stroke()

        # Spirit-Eating Eyepatch over right eye
        ctx.set_source_rgb(0.08, 0.08, 0.1)
        # Eyepatch plate
        ctx.rectangle(1, head_y - 3, 5.5, 5)
        ctx.fill()
        # Eyepatch strap diagonal across forehead
        ctx.set_line_width(1.3)
        ctx.move_to(-7, head_y + 4)
        ctx.line_to(7, head_y - 6)
        ctx.stroke()

        # Left Eye (piercing crazy battle gaze)
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.rectangle(-5.5, head_y - 3, 4, 3)
        ctx.fill()
        ctx.set_source_rgb(0.85, 0.2, 0.1 if self.is_bankai else 0.85)  # Glowing iris
        ctx.arc(-3.5, head_y - 1.5, 1.3, 0, math.pi * 2)
        ctx.fill()

        # Maniac grin / bared teeth
        if self.substate in ("LAUGH", "NOZARASHI", "BANKAI"):
            # Wide ferocious grin
            ctx.set_source_rgb(0.1, 0.05, 0.05)
            ctx.new_path()
            ctx.arc(0, head_y + 4.5, 3.5, 0, math.pi)
            ctx.close_path()
            ctx.fill()
            ctx.set_source_rgb(0.95, 0.95, 0.95)
            ctx.rectangle(-2.5, head_y + 4.5, 5, 1.5)
            ctx.fill()
        else:
            # Dangerous confident smirk
            ctx.set_source_rgb(0.4, 0.15, 0.15)
            ctx.set_line_width(1.2)
            ctx.move_to(-3, head_y + 5)
            ctx.line_to(3, head_y + 4)
            ctx.stroke()

        # Wild Spiked Hair with Brass Bells at each tip!
        ctx.set_source_rgb(0.06, 0.06, 0.08)
        spike_tips = [
            (-12, head_y - 12), (-10, head_y - 18), (-6, head_y - 24),
            (-2, head_y - 27), (2, head_y - 27), (6, head_y - 24),
            (10, head_y - 18), (12, head_y - 12)
        ]
        ctx.new_path()
        ctx.move_to(-7, head_y - 5)
        for tx, ty in spike_tips:
            ctx.line_to(tx, ty)
            ctx.line_to(tx * 0.7, ty + 6)
        ctx.line_to(7, head_y - 5)
        ctx.close_path()
        ctx.fill()

        # Small brass bells dangling on hair tips!
        ctx.set_source_rgb(0.95, 0.82, 0.15)
        for tx, ty in spike_tips:
            ctx.arc(tx, ty, 1.6, 0, math.pi * 2)
            ctx.fill()

        # Horns in Bankai mode!
        if self.is_bankai:
            ctx.set_source_rgb(0.1, 0.1, 0.12)
            ctx.new_path()
            ctx.move_to(-4, head_y - 7)
            ctx.line_to(-7, head_y - 16)
            ctx.line_to(-1, head_y - 9)
            ctx.close_path()
            ctx.fill()
            ctx.new_path()
            ctx.move_to(4, head_y - 7)
            ctx.line_to(7, head_y - 16)
            ctx.line_to(1, head_y - 9)
            ctx.close_path()
            ctx.fill()

        ctx.restore()

    def _draw_arms_and_weapon(self, ctx: cairo.Context) -> None:
        ctx.save()
        skin_color = (0.78, 0.18, 0.18) if self.is_bankai else (0.95, 0.78, 0.65)

        if self.substate == "NOZARASHI":
            # Colossal executioner cleaver axe raised!
            ctx.set_source_rgb(*skin_color)
            ctx.rectangle(8, -10, 16, 6)
            ctx.fill()
            ctx.arc(24, -7, 3.2, 0, math.pi * 2)
            ctx.fill()

            # Nozarashi executioner war cleaver
            ctx.translate(24, -7)
            ctx.rotate(-0.45)
            # Long wooden pole
            ctx.set_source_rgb(0.4, 0.25, 0.15)
            ctx.rectangle(-12, -2, 28, 4)
            ctx.fill()
            # Colossal axe blade
            ctx.set_source_rgb(0.75, 0.78, 0.85)
            ctx.new_path()
            ctx.move_to(14, -14)
            ctx.line_to(42, -18)
            ctx.line_to(44, 22)
            ctx.line_to(14, 16)
            ctx.close_path()
            ctx.fill()
            # Golden decorative rim & red tassel
            ctx.set_source_rgb(0.9, 0.1, 0.1)
            ctx.rectangle(-12, 0, 8, 2.5)
            ctx.fill()

        elif self.substate == "ADJUST_EYEPATCH":
            # Hand reaching to adjust eyepatch
            ctx.set_source_rgb(*skin_color)
            ctx.rectangle(6, -10, 8, 5)
            ctx.fill()
            ctx.arc(6, -18, 3.0, 0, math.pi * 2)
            ctx.fill()

            # Massive sword resting on other side
            ctx.translate(-10, -14)
            ctx.rotate(0.4)
            ctx.set_source_rgb(0.8, 0.82, 0.86)
            ctx.rectangle(-2, -24, 4, 34)
            ctx.fill()

        else:
            # Massive Zanpakutō casually rested on shoulder (classic Kenpachi posture)
            ctx.save()
            ctx.translate(8, -10)
            ctx.rotate(-0.65)
            # Ragged chipped giant blade
            ctx.set_source_rgb(0.78, 0.80, 0.85)
            ctx.rectangle(-3, -28, 6, 42)
            ctx.fill()
            # White wrapped bandage hilt
            ctx.set_source_rgb(0.92, 0.92, 0.94)
            ctx.rectangle(-2.5, 14, 5, 12)
            ctx.fill()
            ctx.restore()

            # Muscular arm resting on hilt
            ctx.set_source_rgb(*skin_color)
            ctx.rectangle(6, -8, 6, 15)
            ctx.fill()
            ctx.arc(9, 7, 3.0, 0, math.pi * 2)
            ctx.fill()

        ctx.restore()
