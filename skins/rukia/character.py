"""Rukia Kuchiki desktop companion: Sode no Shirayuki, Tsukishiro, Hakka no Togame, and Chappy."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, Optional

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager


class RukiaCharacter(BaseCharacter):
    """Rukia Kuchiki — Soul Reaper with the pure white Zanpakutō Sode no Shirayuki."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="rukia")
        self.can_fly = False
        self.is_bankai = False

        # States: "CALM", "DRAW_CHAPPY", "RIBBON_TWIRL", "TSUKISHIRO", "HAKKA_NO_TOGAME"
        self.substate = "CALM"
        self.substate_timer = time.time() + random.uniform(5.0, 10.0)
        self.ability_end_time = 0.0

        # Flowing white silk ribbon physics
        self.ribbon_phase = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        now = time.time()
        if ability_name in ("sode_no_shirayuki", "special"):
            self.substate = "TSUKISHIRO"
            self.ability_end_time = now + 2.5
            particle_mgr.burst_ice_crystals(self.x, self.y, count=26)
            particle_mgr.shockwave(self.x, self.y, max_radius=85.0, color=(0.85, 0.95, 1.0))
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name == "tsukishiro":
            self.substate = "TSUKISHIRO"
            self.ability_end_time = now + 3.0
            particle_mgr.shockwave(target_x, target_y, max_radius=70.0, color=(1.0, 1.0, 1.0), line_width=3.5)
            particle_mgr.burst_ice_crystals(target_x, target_y, count=28, size=8.0)
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name == "hakka_no_togame":
            self.is_bankai = not self.is_bankai
            self.substate = "HAKKA_NO_TOGAME" if self.is_bankai else "CALM"
            self.ability_end_time = now + 5.0 if self.is_bankai else 0.0
            particle_mgr.shockwave(self.x, self.y, max_radius=125.0, color=(0.95, 0.98, 1.0), line_width=4.5)
            particle_mgr.burst_ice_crystals(self.x, self.y, count=36, size=9.0)
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name == "draw_chappy":
            self.substate = "DRAW_CHAPPY"
            self.substate_timer = now + 3.5
            particle_mgr.burst_stars(self.x + 16, self.y - 10, count=6, color=(1.0, 0.7, 0.9))
            return True

        elif ability_name == "ribbon_twirl":
            self.substate = "RIBBON_TWIRL"
            self.substate_timer = now + 3.0
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
        self.ribbon_phase += dt * 3.0
        now = time.time()

        if self.ability_end_time > 0 and now > self.ability_end_time:
            self.substate = "HAKKA_NO_TOGAME" if self.is_bankai else "CALM"
            self.ability_end_time = 0.0

        is_moving = math.hypot(self.vx, self.vy) > 0.5
        if is_moving:
            self.substate = "HAKKA_NO_TOGAME" if self.is_bankai else "CALM"
        else:
            if self.ability_end_time <= 0 and now >= self.substate_timer:
                self.substate_timer = now + random.uniform(6.0, 13.0)
                options = ["CALM", "CALM", "DRAW_CHAPPY", "RIBBON_TWIRL"]
                self.substate = random.choice(options)

        # Gentle falling snowflakes during idle
        if self.is_bankai or random.random() < 0.08:
            particle_mgr.burst_ice_crystals(self.x + random.uniform(-14, 14), self.y - 14, count=1, size=4.0)

        # Facing direction
        if abs(cursor_x - self.x) > 10.0:
            self.facing_right = (cursor_x >= self.x)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1, 1)

        # Gentle breathing bob
        bob_y = math.sin(self.anim_time * 2.0) * 1.2
        ctx.translate(0, bob_y)

        # 1. Bankai Absolute Zero Frost Aura
        if self.is_bankai or self.substate == "HAKKA_NO_TOGAME":
            ctx.save()
            pulse = math.sin(self.anim_time * 3.5) * 0.06
            ctx.set_source_rgba(0.9, 0.96, 1.0, 0.22 + pulse)
            ctx.arc(0, 0, 38.0, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

        # 2. Sheathed or Drawn Sode no Shirayuki
        self._draw_sode_no_shirayuki(ctx)

        # 3. Hakama / Legs
        self._draw_legs(ctx)

        # 4. Shihakushō / Bankai White Kimono
        self._draw_kimono(ctx)

        # 5. Head, Short Black Hair with Center Strand, Violet Eyes
        self._draw_head(ctx)

        # 6. Arms & Actions (Doodling Chappy or Twirling Ribbon)
        self._draw_arms(ctx)

        ctx.restore()

    def _draw_sode_no_shirayuki(self, ctx: cairo.Context) -> None:
        ctx.save()
        ctx.translate(-8, 6)
        ctx.rotate(0.60)

        # Pure snow-white scabbard (saya) & hilt
        ctx.set_source_rgb(0.98, 0.98, 1.0)
        ctx.rectangle(-1.5, -20, 3, 28)
        ctx.fill()
        # White circular tsuba
        ctx.set_source_rgb(0.92, 0.94, 0.98)
        ctx.arc(0, -6, 3.2, 0, math.pi * 2)
        ctx.fill()

        # Long flowing silk ribbon from pommel
        ribbon_wave = math.sin(self.ribbon_phase) * 3.0
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.9)
        ctx.set_line_width(1.8)
        ctx.new_path()
        ctx.move_to(0, -20)
        ctx.curve_to(-6 + ribbon_wave, -28, 4 - ribbon_wave, -34, 0, -42)
        ctx.stroke()
        ctx.restore()

    def _draw_legs(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Hakama color: white in Bankai, black in standard
        if self.is_bankai:
            ctx.set_source_rgb(0.96, 0.96, 0.98)
        else:
            ctx.set_source_rgb(0.1, 0.1, 0.12)
        ctx.rectangle(-7, 10, 5.5, 14)
        ctx.rectangle(1.5, 10, 5.5, 14)
        ctx.fill()
        # White tabi socks & clean sandals
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        ctx.rectangle(-7, 24, 5.5, 3.5)
        ctx.rectangle(1.5, 24, 5.5, 3.5)
        ctx.fill()
        ctx.restore()

    def _draw_kimono(self, ctx: cairo.Context) -> None:
        ctx.save()
        if self.is_bankai:
            # Hakka no Togame: Pure white flowing celestial kimono with crystalline edges
            ctx.set_source_rgb(0.98, 0.98, 1.0)
            ctx.new_path()
            ctx.move_to(-10, -8)
            ctx.line_to(10, -8)
            ctx.line_to(14, 18)
            ctx.line_to(-14, 18)
            ctx.close_path()
            ctx.fill()
            # Crystalline ice blue lapel trim
            ctx.set_source_rgb(0.75, 0.90, 1.0)
            ctx.set_line_width(1.2)
            ctx.move_to(-4, -8)
            ctx.line_to(0, 0)
            ctx.line_to(4, -8)
            ctx.stroke()
        else:
            # Classic black Shihakushō
            ctx.set_source_rgb(0.12, 0.12, 0.14)
            ctx.new_path()
            ctx.move_to(-9, -8)
            ctx.line_to(9, -8)
            ctx.line_to(11, 16)
            ctx.line_to(-11, 16)
            ctx.close_path()
            ctx.fill()
            # White inner collar (juban)
            ctx.set_source_rgb(0.96, 0.96, 0.98)
            ctx.new_path()
            ctx.move_to(-4, -8)
            ctx.line_to(0, 0)
            ctx.line_to(4, -8)
            ctx.close_path()
            ctx.fill()
            # White obi sash
            ctx.rectangle(-9, 4, 18, 4)
            ctx.fill()
        ctx.restore()

    def _draw_head(self, ctx: cairo.Context) -> None:
        ctx.save()
        head_y = -16

        # Pale delicate face
        ctx.set_source_rgb(0.98, 0.88, 0.82)
        ctx.new_path()
        ctx.move_to(-6, head_y - 6)
        ctx.line_to(6, head_y - 6)
        ctx.line_to(5, head_y + 3)
        ctx.line_to(0, head_y + 7)  # Petite chin
        ctx.line_to(-5, head_y + 3)
        ctx.close_path()
        ctx.fill()

        # Large expressive violet eyes
        ctx.set_source_rgb(0.98, 0.98, 0.98)
        ctx.rectangle(-4.5, head_y - 2, 3.5, 3)
        ctx.rectangle(1.0, head_y - 2, 3.5, 3)
        ctx.fill()

        # Deep violet iris
        ctx.set_source_rgb(0.48, 0.25, 0.70)
        ctx.arc(-2.8, head_y - 0.5, 1.3, 0, math.pi * 2)
        ctx.arc(2.8, head_y - 0.5, 1.3, 0, math.pi * 2)
        ctx.fill()
        # White sparkle glint
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(-2.4, head_y - 1.0, 0.5, 0, math.pi * 2)
        ctx.arc(3.2, head_y - 1.0, 0.5, 0, math.pi * 2)
        ctx.fill()

        # Delicate eyebrows
        ctx.set_source_rgb(0.15, 0.15, 0.18)
        ctx.set_line_width(1.0)
        ctx.move_to(-5, head_y - 3.5)
        ctx.line_to(-1.5, head_y - 2.5)
        ctx.move_to(5, head_y - 3.5)
        ctx.line_to(1.5, head_y - 2.5)
        ctx.stroke()

        # Small gentle mouth
        ctx.set_source_rgb(0.65, 0.38, 0.40)
        ctx.set_line_width(1.0)
        ctx.move_to(-1.2, head_y + 4.5)
        ctx.line_to(1.2, head_y + 4.5)
        ctx.stroke()

        # Short Black Hair with signature strand hanging down the center!
        hair_color = (0.95, 0.98, 1.0) if self.is_bankai else (0.08, 0.08, 0.1)
        ctx.set_source_rgb(*hair_color)

        # Hair base bob
        ctx.new_path()
        ctx.move_to(-7, head_y - 6)
        ctx.line_to(-8, head_y + 3)
        ctx.line_to(-6, head_y + 6)
        ctx.line_to(6, head_y + 6)
        ctx.line_to(8, head_y + 3)
        ctx.line_to(7, head_y - 6)
        ctx.close_path()
        ctx.fill()

        # Side bangs
        ctx.new_path()
        ctx.move_to(-7, head_y - 6)
        ctx.line_to(-3, head_y - 1)
        ctx.line_to(0, head_y - 5)
        ctx.line_to(3, head_y - 1)
        ctx.line_to(7, head_y - 6)
        ctx.close_path()
        ctx.fill()

        # Signature single strand falling between eyes!
        ctx.new_path()
        ctx.move_to(-0.5, head_y - 5)
        ctx.line_to(0.5, head_y + 2)
        ctx.line_to(-0.5, head_y + 3.5)
        ctx.line_to(-1.2, head_y - 1)
        ctx.close_path()
        ctx.fill()

        # Hakka no Togame Crystalline Ice Ribbon Hairpiece (in Bankai)
        if self.is_bankai:
            ctx.set_source_rgba(0.7, 0.9, 1.0, 0.9)
            ctx.rectangle(-4, head_y - 9, 8, 2.5)
            ctx.fill()

        ctx.restore()

    def _draw_arms(self, ctx: cairo.Context) -> None:
        ctx.save()
        sleeve_color = (0.98, 0.98, 1.0) if self.is_bankai else (0.12, 0.12, 0.14)

        if self.substate == "DRAW_CHAPPY":
            # Right arm extended drawing Chappy doodle!
            ctx.set_source_rgb(*sleeve_color)
            ctx.rectangle(4, -6, 10, 4)
            ctx.fill()
            ctx.set_source_rgb(0.98, 0.88, 0.82)
            ctx.arc(14, -4, 2.2, 0, math.pi * 2)
            ctx.fill()

            # Glowing pink Chappy bunny doodle in the air!
            ctx.save()
            ctx.translate(22, -8)
            ctx.set_source_rgba(1.0, 0.5, 0.8, 0.85)
            ctx.set_line_width(1.2)
            # Bunny head
            ctx.arc(0, 0, 4.0, 0, math.pi * 2)
            ctx.stroke()
            # Bunny long ears
            ctx.arc(-2, -6, 1.5, 0, math.pi * 2)
            ctx.arc(2, -6, 1.5, 0, math.pi * 2)
            ctx.stroke()
            ctx.restore()

        elif self.substate == "TSUKISHIRO":
            # Pointing Sode no Shirayuki to the ground!
            ctx.set_source_rgb(*sleeve_color)
            ctx.rectangle(4, -6, 8, 4)
            ctx.fill()
            ctx.set_source_rgb(0.98, 0.88, 0.82)
            ctx.arc(12, -4, 2.2, 0, math.pi * 2)
            ctx.fill()

            # Drawn white sword pointing down
            ctx.translate(12, -4)
            ctx.rotate(1.2)
            ctx.set_source_rgb(1.0, 1.0, 1.0)
            ctx.rectangle(0, -1, 26, 2)
            ctx.fill()

        else:
            # Elegant gentle standing arms
            ctx.set_source_rgb(*sleeve_color)
            ctx.rectangle(-10, -6, 4, 13)
            ctx.rectangle(6, -6, 4, 13)
            ctx.fill()
            ctx.set_source_rgb(0.98, 0.88, 0.82)
            ctx.arc(-8, 7, 2.0, 0, math.pi * 2)
            ctx.arc(8, 7, 2.0, 0, math.pi * 2)
            ctx.fill()

        ctx.restore()
