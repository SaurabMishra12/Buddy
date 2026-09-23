"""Byakuya Kuchiki desktop companion: Senbonzakura, Senbonzakura Kageyoshi, Senkei, and Hakuteiken."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, Optional

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager


class ByakuyaCharacter(BaseCharacter):
    """Byakuya Kuchiki — Captain of the 6th Division with Senbonzakura and Hakuteiken."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="byakuya")
        self.can_fly = False

        # States: "COMPOSED", "ADJUST_SCARF", "MEDITATE", "SHIKAI", "BANKAI_SENKEI", "HAKUTEIKEN"
        self.substate = "COMPOSED"
        self.substate_timer = time.time() + random.uniform(6.0, 12.0)
        self.ability_end_time = 0.0

        # Special visual effects
        self.has_hakuteiken_wings = False
        self.senkei_blades_active = False

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        now = time.time()
        if ability_name in ("senbonzakura", "special"):
            self.substate = "SHIKAI"
            self.ability_end_time = now + 2.5
            particle_mgr.burst_cherry_petals(self.x, self.y, count=32)
            particle_mgr.shockwave(self.x, self.y, max_radius=85.0, color=(1.0, 0.6, 0.8))
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name in ("senkei", "shikai", "power_up"):
            self.substate = "BANKAI_SENKEI"
            self.senkei_blades_active = True
            self.ability_end_time = now + 4.0
            particle_mgr.burst_cherry_petals(self.x, self.y, count=40)
            particle_mgr.shockwave(self.x, self.y, max_radius=110.0, color=(1.0, 0.4, 0.7))
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name in ("gokei", "bankai", "ultimate", "hakuteiken"):
            self.substate = "HAKUTEIKEN"
            self.has_hakuteiken_wings = True
            self.ability_end_time = now + 3.5
            particle_mgr.shockwave(target_x, target_y, max_radius=130.0, color=(1.0, 0.5, 0.8), line_width=4.0)
            particle_mgr.burst_cherry_petals(self.x, self.y, count=45)
            if audio_mgr:
                audio_mgr.play("swoosh")
            return True

        elif ability_name == "adjust_scarf":
            self.substate = "ADJUST_SCARF"
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
        self.anim_time += dt * 4.0
        now = time.time()

        # Ability duration
        if self.ability_end_time > 0 and now > self.ability_end_time:
            self.substate = "COMPOSED"
            self.ability_end_time = 0.0
            self.has_hakuteiken_wings = False
            self.senkei_blades_active = False

        # Peaceful state transitions
        is_moving = math.hypot(self.vx, self.vy) > 0.5
        if is_moving:
            self.substate = "COMPOSED"
        else:
            if self.ability_end_time <= 0 and now >= self.substate_timer:
                self.substate_timer = now + random.uniform(7.0, 15.0)
                options = ["COMPOSED", "COMPOSED", "ADJUST_SCARF", "MEDITATE"]
                self.substate = random.choice(options)

        # Gentle ambient falling sakura petals during idle
        if self.substate in ("COMPOSED", "MEDITATE") and random.random() < 0.06:
            particle_mgr.burst_cherry_petals(self.x + random.uniform(-20, 20), self.y - 20, count=1)

        # Facing direction
        if abs(cursor_x - self.x) > 10.0:
            self.facing_right = (cursor_x >= self.x)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1, 1)

        # Aristocratic minimal bobbing
        bob_y = math.sin(self.anim_time * 1.5) * 0.8
        ctx.translate(0, bob_y)

        # 1. Hakuteiken Pure White Wings (if active)
        if self.has_hakuteiken_wings:
            self._draw_hakuteiken_wings(ctx)

        # 2. Senkei Blades Floating in Ring (if active)
        if self.senkei_blades_active:
            self._draw_senkei_blades(ctx)

        # 3. Sheathed Senbonzakura at hip
        if self.substate != "SHIKAI":
            self._draw_sheathed_katana(ctx)

        # 4. Black Hakama trousers & footwear
        self._draw_legs(ctx)

        # 5. Captain Haori & Shihakushō Robes
        self._draw_haori(ctx)

        # 6. Ginpaku Kazahana Turquoise Scarf
        self._draw_scarf(ctx)

        # 7. Head, Noble Face, Kenseikan, & Long Black Hair
        self._draw_head(ctx)

        # 8. Arms & Hand Gestures
        self._draw_arms(ctx)

        ctx.restore()

    def _draw_hakuteiken_wings(self, ctx: cairo.Context) -> None:
        ctx.save()
        wing_anim = math.sin(self.anim_time * 2.5) * 0.1
        # Left Wing
        ctx.save()
        ctx.translate(-8, -12)
        ctx.rotate(-0.35 + wing_anim)
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.85)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-35, -25, -45, -5, -20, 15)
        ctx.close_path()
        ctx.fill()
        # Wing glow border
        ctx.set_source_rgba(0.9, 0.95, 1.0, 0.9)
        ctx.set_line_width(1.5)
        ctx.stroke()
        ctx.restore()

        # Right Wing
        ctx.save()
        ctx.translate(8, -12)
        ctx.rotate(0.35 - wing_anim)
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.85)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(35, -25, 45, -5, 20, 15)
        ctx.close_path()
        ctx.fill()
        ctx.set_source_rgba(0.9, 0.95, 1.0, 0.9)
        ctx.set_line_width(1.5)
        ctx.stroke()
        ctx.restore()
        ctx.restore()

    def _draw_senkei_blades(self, ctx: cairo.Context) -> None:
        """Render Byakuya's Senkei: four rotating rows of solid glowing blades forming a cage."""
        ctx.save()
        rot_base = self.anim_time * 1.5
        radius_x = 34.0
        radius_y = 16.0
        for tier in range(4):
            tier_y = -36.0 + tier * 14.0
            tier_rot = rot_base + (tier * 0.45)
            for b in range(6):
                ang = tier_rot + b * (math.pi / 3.0)
                bx = radius_x * math.cos(ang)
                by = tier_y + radius_y * math.sin(ang)
                depth = (math.sin(ang) + 1.0) * 0.5
                b_alpha = 0.45 + 0.55 * depth

                ctx.save()
                ctx.translate(bx, by)
                ctx.set_source_rgba(1.0, 0.5, 0.8, 0.85 * b_alpha)
                ctx.rectangle(-1.2, -7, 2.4, 14)
                ctx.fill()
                ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95 * b_alpha)
                ctx.rectangle(-0.5, -6, 1.0, 12)
                ctx.fill()
                ctx.restore()
        ctx.restore()

    def _draw_sheathed_katana(self, ctx: cairo.Context) -> None:
        ctx.save()
        ctx.translate(-8, 8)
        ctx.rotate(0.65)
        # Black lacquered scabbard (saya)
        ctx.set_source_rgb(0.08, 0.08, 0.1)
        ctx.rectangle(-1.5, -6, 3, 30)
        ctx.fill()
        # Bronze tsuba & lavender tsukamaki hilt cord
        ctx.set_source_rgb(0.75, 0.60, 0.85)
        ctx.rectangle(-1.5, -18, 3, 12)
        ctx.fill()
        ctx.set_source_rgb(0.85, 0.70, 0.25)
        ctx.rectangle(-3.5, -6, 7, 2)
        ctx.fill()
        ctx.restore()

    def _draw_legs(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Black hakama trousers
        ctx.set_source_rgb(0.1, 0.1, 0.12)
        ctx.rectangle(-8, 14, 6, 14)
        ctx.rectangle(2, 14, 6, 14)
        ctx.fill()
        # White tabi socks & clean sandals
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        ctx.rectangle(-8, 28, 6, 3)
        ctx.rectangle(2, 28, 6, 3)
        ctx.fill()
        ctx.restore()

    def _draw_haori(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Black inner Shihakushō
        ctx.set_source_rgb(0.12, 0.12, 0.14)
        ctx.rectangle(-9, -10, 18, 24)
        ctx.fill()

        # Pure white captain's haori with flowing hem
        ctx.set_source_rgb(0.98, 0.98, 1.0)
        ctx.new_path()
        ctx.move_to(-12, -10)
        ctx.line_to(12, -10)
        ctx.line_to(15, 20)
        ctx.line_to(-15, 20)
        ctx.close_path()
        ctx.fill()

        # Haori black geometric diamond border at hem
        ctx.set_source_rgb(0.12, 0.12, 0.14)
        for hx in range(-12, 14, 4):
            ctx.new_path()
            ctx.move_to(hx, 18)
            ctx.line_to(hx + 2, 20)
            ctx.line_to(hx + 4, 18)
            ctx.close_path()
            ctx.fill()

        # Haori black lapel lines
        ctx.set_line_width(1.2)
        ctx.move_to(-4, -10)
        ctx.line_to(-6, 20)
        ctx.move_to(4, -10)
        ctx.line_to(6, 20)
        ctx.stroke()
        ctx.restore()

    def _draw_scarf(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Ginpaku Kazahana — precious teal / seafoam green scarf
        ctx.set_source_rgb(0.40, 0.82, 0.78)
        ctx.rectangle(-7, -8, 14, 5)
        ctx.fill()
        # Flowing scarf tail trailing slightly back
        flutter = math.sin(self.anim_time * 2.0) * 2.0
        ctx.new_path()
        ctx.move_to(5, -6)
        ctx.curve_to(12, -4, 16 + flutter, 2, 14 + flutter, 12)
        ctx.curve_to(10, 8, 8, -2, 5, -6)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

    def _draw_head(self, ctx: cairo.Context) -> None:
        ctx.save()
        head_y = -18

        # Long silky black hair behind head
        ctx.set_source_rgb(0.08, 0.08, 0.1)
        ctx.new_path()
        ctx.move_to(-8, head_y - 6)
        ctx.line_to(-10, head_y + 24)
        ctx.line_to(10, head_y + 24)
        ctx.line_to(8, head_y - 6)
        ctx.close_path()
        ctx.fill()

        # Pale noble face
        ctx.set_source_rgb(0.98, 0.88, 0.82)
        ctx.new_path()
        ctx.move_to(-6, head_y - 7)
        ctx.line_to(6, head_y - 7)
        ctx.line_to(5, head_y + 4)
        ctx.line_to(0, head_y + 8)  # Aristocratic slender chin
        ctx.line_to(-5, head_y + 4)
        ctx.close_path()
        ctx.fill()

        # Eyes
        if self.substate == "MEDITATE":
            # Calm closed eyes
            ctx.set_source_rgb(0.3, 0.25, 0.25)
            ctx.set_line_width(1.1)
            ctx.move_to(-4.5, head_y - 1)
            ctx.line_to(-1.5, head_y - 0.5)
            ctx.move_to(1.5, head_y - 0.5)
            ctx.line_to(4.5, head_y - 1)
            ctx.stroke()
        else:
            # Composed dark grey slate eyes
            ctx.set_source_rgb(0.98, 0.98, 0.98)
            ctx.rectangle(-4.5, head_y - 2, 3.5, 2.5)
            ctx.rectangle(1.0, head_y - 2, 3.5, 2.5)
            ctx.fill()
            ctx.set_source_rgb(0.28, 0.32, 0.38)
            ctx.arc(-2.8, head_y - 0.8, 1.2, 0, math.pi * 2)
            ctx.arc(2.8, head_y - 0.8, 1.2, 0, math.pi * 2)
            ctx.fill()
            # Calm level eyebrows
            ctx.set_source_rgb(0.12, 0.12, 0.15)
            ctx.set_line_width(1.0)
            ctx.move_to(-5, head_y - 3.5)
            ctx.line_to(-1.5, head_y - 3)
            ctx.move_to(5, head_y - 3.5)
            ctx.line_to(1.5, head_y - 3)
            ctx.stroke()

        # Neutral aristocratic mouth
        ctx.set_source_rgb(0.65, 0.45, 0.45)
        ctx.set_line_width(1.0)
        ctx.move_to(-1.5, head_y + 4.5)
        ctx.line_to(1.5, head_y + 4.5)
        ctx.stroke()

        # Front Hair Bangs
        ctx.set_source_rgb(0.08, 0.08, 0.1)
        ctx.new_path()
        ctx.move_to(-7, head_y - 7)
        ctx.line_to(-2, head_y - 1)
        ctx.line_to(0, head_y - 6)
        ctx.line_to(2, head_y - 1)
        ctx.line_to(7, head_y - 7)
        ctx.line_to(5, head_y - 10)
        ctx.line_to(-5, head_y - 10)
        ctx.close_path()
        ctx.fill()

        # White Kenseikan Hairpieces (Noble headpieces)
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        # Top-right hair tube ornament
        ctx.rectangle(3, head_y - 13, 2.5, 5)
        ctx.rectangle(-5.5, head_y - 13, 2.5, 5)
        ctx.fill()
        ctx.set_source_rgb(0.3, 0.3, 0.35)
        ctx.set_line_width(0.7)
        ctx.rectangle(3, head_y - 13, 2.5, 5)
        ctx.rectangle(-5.5, head_y - 13, 2.5, 5)
        ctx.stroke()

        ctx.restore()

    def _draw_arms(self, ctx: cairo.Context) -> None:
        ctx.save()
        if self.substate == "SHIKAI":
            # Releasing Senbonzakura: extended hand with blade dissolving into blossoms!
            ctx.set_source_rgb(0.98, 0.98, 1.0)
            ctx.rectangle(6, -8, 14, 6)
            ctx.fill()
            ctx.set_source_rgb(0.98, 0.88, 0.82)
            ctx.arc(20, -5, 2.8, 0, math.pi * 2)
            ctx.fill()
            # Dissolving blade hilt
            ctx.set_source_rgb(0.75, 0.60, 0.85)
            ctx.rectangle(20, -7, 6, 2)
            ctx.fill()
        elif self.substate == "ADJUST_SCARF":
            # Hand gracefully touching scarf collar
            ctx.set_source_rgb(0.98, 0.98, 1.0)
            ctx.rectangle(4, -8, 8, 5)
            ctx.fill()
            ctx.set_source_rgb(0.98, 0.88, 0.82)
            ctx.arc(3, -5, 2.5, 0, math.pi * 2)
            ctx.fill()
        else:
            # Hands hidden calmly inside haori sleeves (classic Byakuya stance)
            ctx.set_source_rgb(0.98, 0.98, 1.0)
            ctx.rectangle(-12, -8, 6, 16)
            ctx.rectangle(6, -8, 6, 16)
            ctx.fill()
            # Crossed cuffs inside haori
            ctx.set_source_rgb(0.12, 0.12, 0.14)
            ctx.rectangle(-6, 4, 12, 4)
            ctx.fill()
        ctx.restore()
