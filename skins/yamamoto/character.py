"""Yamamoto desktop companion: Ryūjin Jakka, Zanka no Tachi, Flame Wave, and ancient authority."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, Optional

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager


class YamamotoCharacter(BaseCharacter):
    """Genryūsai Shigekuni Yamamoto — Captain-Commander of the Gotei 13."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="yamamoto")
        self.can_fly = False
        self.is_bankai = False

        # States: "AUTHORITY", "STROKE_BEARD", "LEAN_CANE", "MEDITATE", "SHIKAI", "BANKAI"
        self.substate = "AUTHORITY"
        self.substate_timer = time.time() + random.uniform(6.0, 12.0)
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
        if ability_name in ("ryujin_jakka", "flame_wave", "special"):
            self.substate = "SHIKAI"
            self.ability_end_time = now + 2.5
            particle_mgr.burst_reiatsu(self.x, self.y, color=(1.0, 0.35, 0.05), count=22)
            particle_mgr.flame_puff(self.x, self.y - 10, vx=4.0 if self.facing_right else -4.0, count=12, size=9.0)
            particle_mgr.shockwave(self.x, self.y, max_radius=110.0, color=(1.0, 0.3, 0.0))
            if audio_mgr:
                audio_mgr.play("fire")
            return True

        elif ability_name == "zanka_no_tachi":
            self.is_bankai = not self.is_bankai
            self.substate = "BANKAI" if self.is_bankai else "AUTHORITY"
            self.ability_end_time = now + 4.0 if self.is_bankai else 0.0
            particle_mgr.shockwave(self.x, self.y, max_radius=140.0, color=(0.2, 0.05, 0.05), line_width=4.0)
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.85, 0.1, 0.05), count=26)
            if audio_mgr:
                audio_mgr.play("fire")
            return True

        elif ability_name == "stroke_beard":
            self.substate = "STROKE_BEARD"
            self.substate_timer = now + 3.0
            return True

        elif ability_name == "meditate":
            self.substate = "MEDITATE"
            self.substate_timer = now + 5.0
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
        self.anim_time += dt * 3.5
        now = time.time()

        if self.ability_end_time > 0 and now > self.ability_end_time:
            self.substate = "AUTHORITY"
            self.ability_end_time = 0.0

        is_moving = math.hypot(self.vx, self.vy) > 0.5
        if is_moving:
            self.substate = "AUTHORITY"
        else:
            if self.ability_end_time <= 0 and now >= self.substate_timer:
                self.substate_timer = now + random.uniform(7.0, 15.0)
                choices = ["AUTHORITY", "STROKE_BEARD", "LEAN_CANE", "MEDITATE"]
                self.substate = random.choice(choices)

        # Ambient ember sparks flickering around cane/sword
        if random.random() < 0.12:
            particle_mgr.flame_puff(self.x + (14 if self.facing_right else -14), self.y + 10, count=1, size=3.0)

        # Facing direction
        if abs(cursor_x - self.x) > 12.0:
            self.facing_right = (cursor_x >= self.x)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1, 1)

        # Imposing subtle authority breathing
        bob_y = math.sin(self.anim_time * 1.2) * 0.7
        ctx.translate(0, bob_y)

        # Bankai heat aura shimmer
        if self.is_bankai or self.substate == "BANKAI":
            ctx.save()
            pulse = math.sin(self.anim_time * 4.0) * 0.06
            ctx.set_source_rgba(0.9, 0.15, 0.05, 0.15 + pulse)
            ctx.arc(0, 0, 42.0, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

        # 1. Legs and Feet
        self._draw_legs(ctx)

        # 2. Captain-Commander Haori and Black Shihakushō
        self._draw_robes(ctx)

        # 3. Head, Facial Scars, Eyebrows, and Huge White Beard
        self._draw_head(ctx)

        # 4. Cane / Ryūjin Jakka / Zanka no Tachi & Arms
        self._draw_arms_and_weapon(ctx)

        ctx.restore()

    def _draw_legs(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Black hakama
        ctx.set_source_rgb(0.1, 0.1, 0.12)
        ctx.rectangle(-8, 14, 7, 14)
        ctx.rectangle(2, 14, 7, 14)
        ctx.fill()
        # White socks & sandals
        ctx.set_source_rgb(0.92, 0.92, 0.92)
        ctx.rectangle(-8, 28, 7, 4)
        ctx.rectangle(2, 28, 7, 4)
        ctx.fill()
        ctx.restore()

    def _draw_robes(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Black Shihakushō kimono
        ctx.set_source_rgb(0.12, 0.12, 0.14)
        ctx.rectangle(-11, -10, 22, 26)
        ctx.fill()

        # Captain-Commander Haori (White with purple inner lining)
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        ctx.new_path()
        ctx.move_to(-14, -10)
        ctx.line_to(14, -10)
        ctx.line_to(17, 22)
        ctx.line_to(-17, 22)
        ctx.close_path()
        ctx.fill()

        # Haori black geometric diamond border at hem
        ctx.set_source_rgb(0.12, 0.12, 0.14)
        for hx in range(-14, 16, 4):
            ctx.new_path()
            ctx.move_to(hx, 20)
            ctx.line_to(hx + 2, 22)
            ctx.line_to(hx + 4, 20)
            ctx.close_path()
            ctx.fill()

        # Purple inner collar trim
        ctx.set_source_rgb(0.45, 0.20, 0.55)
        ctx.set_line_width(1.8)
        ctx.move_to(-5, -10)
        ctx.line_to(0, 2)
        ctx.line_to(5, -10)
        ctx.stroke()
        ctx.restore()

    def _draw_head(self, ctx: cairo.Context) -> None:
        ctx.save()
        head_y = -18

        # Bald commanding head with weathered skin
        ctx.set_source_rgb(0.92, 0.78, 0.68)
        ctx.arc(0, head_y - 2, 7.5, 0, math.pi * 2)
        ctx.fill()

        # Forehead crossed battle scars (X-shaped scars)
        ctx.set_source_rgb(0.75, 0.55, 0.48)
        ctx.set_line_width(1.0)
        ctx.move_to(-3, head_y - 8)
        ctx.line_to(3, head_y - 4)
        ctx.move_to(3, head_y - 8)
        ctx.line_to(-3, head_y - 4)
        ctx.stroke()

        # Fierce bushy white eyebrows
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        ctx.set_line_width(1.8)
        ctx.move_to(-6, head_y - 4)
        ctx.line_to(-1, head_y - 2)
        ctx.move_to(6, head_y - 4)
        ctx.line_to(1, head_y - 2)
        ctx.stroke()

        # Eyes: slit closed in authority or burning open
        if self.substate in ("SHIKAI", "BANKAI"):
            # Glowing golden/fiery eyes!
            ctx.set_source_rgb(1.0, 0.85, 0.2)
            ctx.arc(-3, head_y - 2, 1.4, 0, math.pi * 2)
            ctx.arc(3, head_y - 2, 1.4, 0, math.pi * 2)
            ctx.fill()
        else:
            # Stern narrow slit eyes
            ctx.set_source_rgb(0.2, 0.15, 0.15)
            ctx.set_line_width(1.2)
            ctx.move_to(-5, head_y - 2)
            ctx.line_to(-1.5, head_y - 1.5)
            ctx.move_to(5, head_y - 2)
            ctx.line_to(1.5, head_y - 1.5)
            ctx.stroke()

        # Enormous Cascading White Beard
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        ctx.new_path()
        ctx.move_to(-5, head_y + 1)
        ctx.line_to(5, head_y + 1)
        ctx.curve_to(7, head_y + 15, 4, head_y + 32, 0, head_y + 36)
        ctx.curve_to(-4, head_y + 32, -7, head_y + 15, -5, head_y + 1)
        ctx.close_path()
        ctx.fill()

        # Purple ribbon tied around mid-beard
        ctx.set_source_rgb(0.50, 0.18, 0.60)
        ctx.rectangle(-3, head_y + 18, 6, 2.8)
        ctx.fill()
        ctx.restore()

    def _draw_arms_and_weapon(self, ctx: cairo.Context) -> None:
        ctx.save()
        if self.substate == "SHIKAI":
            # Drawing ignited Ryūjin Jakka!
            ctx.set_source_rgb(0.96, 0.96, 0.98)
            ctx.rectangle(8, -8, 14, 6)
            ctx.fill()
            ctx.set_source_rgb(0.92, 0.78, 0.68)
            ctx.arc(22, -5, 3.0, 0, math.pi * 2)
            ctx.fill()

            # Fiery blade
            ctx.translate(22, -5)
            ctx.rotate(-0.30)
            # Steel core
            ctx.set_source_rgb(0.85, 0.85, 0.9)
            ctx.rectangle(0, -2, 34, 3)
            ctx.fill()
            # Surging flames along blade
            ctx.set_source_rgba(1.0, 0.35, 0.05, 0.85)
            ctx.new_path()
            ctx.move_to(0, -6)
            ctx.line_to(36, -3)
            ctx.line_to(38, 5)
            ctx.line_to(0, 5)
            ctx.close_path()
            ctx.fill()
            # Yellow fire core
            ctx.set_source_rgba(1.0, 0.9, 0.2, 0.9)
            ctx.rectangle(4, -1, 28, 2)
            ctx.fill()

        elif self.substate == "BANKAI":
            # Zanka no Tachi: Pitch black charred blade, subtle heat smoke
            ctx.set_source_rgb(0.96, 0.96, 0.98)
            ctx.rectangle(8, -8, 14, 6)
            ctx.fill()
            ctx.set_source_rgb(0.92, 0.78, 0.68)
            ctx.arc(22, -5, 3.0, 0, math.pi * 2)
            ctx.fill()

            ctx.translate(22, -5)
            ctx.rotate(-0.25)
            # Charred black blade
            ctx.set_source_rgb(0.06, 0.06, 0.08)
            ctx.rectangle(0, -2, 36, 3.5)
            ctx.fill()
            # Glowing scorched edge
            ctx.set_source_rgba(0.95, 0.15, 0.05, 0.8)
            ctx.set_line_width(1.0)
            ctx.move_to(0, 1.5)
            ctx.line_to(36, 1.5)
            ctx.stroke()

        elif self.substate == "STROKE_BEARD":
            # Hand gently touching beard
            ctx.set_source_rgb(0.96, 0.96, 0.98)
            ctx.rectangle(4, -6, 8, 6)
            ctx.fill()
            ctx.set_source_rgb(0.92, 0.78, 0.68)
            ctx.arc(3, -2, 2.8, 0, math.pi * 2)
            ctx.fill()

            # Wooden cane held in other hand
            ctx.set_source_rgb(0.45, 0.28, 0.15)
            ctx.rectangle(-12, -4, 3, 34)
            ctx.fill()

        else:
            # Leaning on walking cane / standing tall
            ctx.set_source_rgb(0.96, 0.96, 0.98)
            ctx.rectangle(8, -8, 6, 16)
            ctx.fill()
            ctx.set_source_rgb(0.92, 0.78, 0.68)
            ctx.arc(11, 8, 2.8, 0, math.pi * 2)
            ctx.fill()

            # Wooden cane
            ctx.set_source_rgb(0.45, 0.28, 0.15)
            ctx.rectangle(10, 6, 3, 24)
            ctx.fill()
            # Curved wooden cane handle
            ctx.arc(11.5, 6, 3.5, math.pi, math.pi * 2)
            ctx.fill()

        ctx.restore()
