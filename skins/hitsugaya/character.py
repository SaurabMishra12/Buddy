"""Tōshirō Hitsugaya desktop companion: Hyōrinmaru, Daiguren Bankai Ice Wings, and Crystalline Frost."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, Optional

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager


class HitsugayaCharacter(BaseCharacter):
    """Tōshirō Hitsugaya — Captain of the 10th Division with Hyōrinmaru and Daiguren Bankai."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="hitsugaya")
        self.can_fly = True
        self.is_bankai = False

        # States: "SERIOUS", "CROSSED_ARMS", "ANNOYED", "HYORINMARU", "DAIGUREN"
        self.substate = "SERIOUS"
        self.substate_timer = time.time() + random.uniform(5.0, 10.0)
        self.ability_end_time = 0.0

        # Annoyed twitch animation
        self.twitch_timer = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        now = time.time()
        if ability_name in ("hyorinmaru", "special"):
            self.substate = "HYORINMARU"
            self.ability_end_time = now + 2.5
            particle_mgr.burst_ice_crystals(self.x, self.y, count=28)
            particle_mgr.shockwave(self.x, self.y, max_radius=85.0, color=(0.4, 0.85, 1.0))
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name in ("daiguren_bankai", "ice_wings"):
            self.is_bankai = not self.is_bankai
            self.substate = "DAIGUREN" if self.is_bankai else "SERIOUS"
            self.ability_end_time = now + 5.0 if self.is_bankai else 0.0
            particle_mgr.burst_ice_crystals(self.x, self.y, count=36, size=8.0)
            particle_mgr.shockwave(self.x, self.y, max_radius=120.0, color=(0.7, 0.95, 1.0), line_width=4.0)
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name == "soten_hyoso":
            self.substate = "HYORINMARU"
            self.ability_end_time = now + 3.0
            particle_mgr.burst_ice_crystals(target_x, target_y, count=30, size=9.0)
            particle_mgr.shockwave(target_x, target_y, max_radius=90.0, color=(0.5, 0.9, 1.0))
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name == "crossed_arms":
            self.substate = "CROSSED_ARMS"
            self.substate_timer = now + 4.0
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
            self.substate = "DAIGUREN" if self.is_bankai else "SERIOUS"
            self.ability_end_time = 0.0

        is_moving = math.hypot(self.vx, self.vy) > 0.5
        if is_moving:
            self.substate = "DAIGUREN" if self.is_bankai else "SERIOUS"
        else:
            if self.ability_end_time <= 0 and now >= self.substate_timer:
                self.substate_timer = now + random.uniform(6.0, 12.0)
                options = ["SERIOUS", "CROSSED_ARMS", "SERIOUS"]
                self.substate = random.choice(options)

        # Gentle floating snowflakes and ice crystals
        if (self.is_bankai or random.random() < 0.10):
            particle_mgr.burst_ice_crystals(self.x + random.uniform(-15, 15), self.y - 15, count=1, size=4.5)

        # Facing direction
        if abs(cursor_x - self.x) > 10.0:
            self.facing_right = (cursor_x >= self.x)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1, 1)

        # Youthful floating / calm hover bob
        bob_y = math.sin(self.anim_time * 2.2) * 1.5
        ctx.translate(0, bob_y)

        # 1. Daiguren Bankai Ice Wings (if in Bankai)
        if self.is_bankai or self.substate == "DAIGUREN":
            self._draw_ice_wings(ctx)

        # 2. Hyōrinmaru Katana on back
        self._draw_sheathed_hyorinmaru(ctx)

        # 3. Hakama & Footwear
        self._draw_legs(ctx)

        # 4. Captain's Haori & Green Sash
        self._draw_robes(ctx)

        # 5. Youthful Head, Spiked White Hair, Turquoise Eyes
        self._draw_head(ctx)

        # 6. Arms & Crossed Stance / Ice Surge
        self._draw_arms(ctx)

        ctx.restore()

    def _draw_ice_wings(self, ctx: cairo.Context) -> None:
        ctx.save()
        wing_flutter = math.sin(self.anim_time * 3.5) * 0.12

        # 3 Purple-Cyan Ice Flower Stars floating overhead
        flower_pulse = math.sin(self.anim_time * 3.0) * 1.0
        for fx, fy in [(-12, -32), (0, -36), (12, -32)]:
            ctx.save()
            ctx.translate(fx, fy + flower_pulse)
            ctx.set_source_rgba(0.7, 0.4, 0.95, 0.85)
            ctx.new_path()
            ctx.move_to(0, -3)
            ctx.line_to(3, 0)
            ctx.line_to(0, 3)
            ctx.line_to(-3, 0)
            ctx.close_path()
            ctx.fill()
            ctx.restore()

        # Left Crystalline Wing
        ctx.save()
        ctx.translate(-8, -10)
        ctx.rotate(-0.35 + wing_flutter)
        # Ice wing gradient / polygon facets
        ctx.set_source_rgba(0.45, 0.85, 1.0, 0.75)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.line_to(-28, -22)
        ctx.line_to(-38, -8)
        ctx.line_to(-32, 8)
        ctx.line_to(-16, 12)
        ctx.close_path()
        ctx.fill()
        # White crystal facet highlight
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.85)
        ctx.set_line_width(1.3)
        ctx.move_to(0, 0)
        ctx.line_to(-38, -8)
        ctx.stroke()
        ctx.restore()

        # Right Crystalline Wing
        ctx.save()
        ctx.translate(8, -10)
        ctx.rotate(0.35 - wing_flutter)
        ctx.set_source_rgba(0.45, 0.85, 1.0, 0.75)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.line_to(28, -22)
        ctx.line_to(38, -8)
        ctx.line_to(32, 8)
        ctx.line_to(16, 12)
        ctx.close_path()
        ctx.fill()
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.85)
        ctx.set_line_width(1.3)
        ctx.move_to(0, 0)
        ctx.line_to(38, -8)
        ctx.stroke()
        ctx.restore()

        ctx.restore()

    def _draw_sheathed_hyorinmaru(self, ctx: cairo.Context) -> None:
        ctx.save()
        ctx.translate(-8, -6)
        ctx.rotate(0.55)
        # Deep blue scabbard
        ctx.set_source_rgb(0.12, 0.18, 0.35)
        ctx.rectangle(-1.5, -24, 3, 30)
        ctx.fill()
        # Bronze 4-pointed star tsuba (Hyōrinmaru emblem)
        ctx.set_source_rgb(0.85, 0.75, 0.25)
        ctx.new_path()
        ctx.move_to(0, -28)
        ctx.line_to(3, -25)
        ctx.line_to(0, -22)
        ctx.line_to(-3, -25)
        ctx.close_path()
        ctx.fill()
        # Light blue tsukamaki hilt
        ctx.set_source_rgb(0.45, 0.75, 0.95)
        ctx.rectangle(-1.5, -36, 3, 10)
        ctx.fill()
        ctx.restore()

    def _draw_legs(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Black hakama trousers (short prodigy proportion)
        ctx.set_source_rgb(0.1, 0.1, 0.12)
        ctx.rectangle(-7, 10, 5.5, 13)
        ctx.rectangle(1.5, 10, 5.5, 13)
        ctx.fill()
        # White tabi & sandals
        ctx.set_source_rgb(0.95, 0.95, 0.95)
        ctx.rectangle(-7, 23, 5.5, 3.5)
        ctx.rectangle(1.5, 23, 5.5, 3.5)
        ctx.fill()
        ctx.restore()

    def _draw_robes(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Black Shihakushō
        ctx.set_source_rgb(0.12, 0.12, 0.14)
        ctx.rectangle(-8, -8, 16, 20)
        ctx.fill()

        # Captain's White Haori
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        ctx.new_path()
        ctx.move_to(-10, -8)
        ctx.line_to(10, -8)
        ctx.line_to(12, 17)
        ctx.line_to(-12, 17)
        ctx.close_path()
        ctx.fill()

        # Haori black diamond hem border
        ctx.set_source_rgb(0.12, 0.12, 0.14)
        for hx in range(-10, 11, 4):
            ctx.new_path()
            ctx.move_to(hx, 15)
            ctx.line_to(hx + 2, 17)
            ctx.line_to(hx + 4, 15)
            ctx.close_path()
            ctx.fill()

        # Green sword sash across chest
        ctx.set_source_rgb(0.20, 0.65, 0.40)
        ctx.set_line_width(2.2)
        ctx.move_to(-7, -6)
        ctx.line_to(7, 8)
        ctx.stroke()
        ctx.restore()

    def _draw_head(self, ctx: cairo.Context) -> None:
        ctx.save()
        head_y = -16

        # Youthful face
        ctx.set_source_rgb(0.98, 0.85, 0.75)
        ctx.new_path()
        ctx.move_to(-6, head_y - 6)
        ctx.line_to(6, head_y - 6)
        ctx.line_to(5, head_y + 3)
        ctx.line_to(0, head_y + 7)  # Youthful chin
        ctx.line_to(-5, head_y + 3)
        ctx.close_path()
        ctx.fill()

        # Turquoise / Teal gemstone eyes
        ctx.set_source_rgb(0.98, 0.98, 0.98)
        ctx.rectangle(-4.5, head_y - 2, 3.5, 2.5)
        ctx.rectangle(1.0, head_y - 2, 3.5, 2.5)
        ctx.fill()

        ctx.set_source_rgb(0.15, 0.80, 0.85)  # Vivid turquoise
        ctx.arc(-2.8, head_y - 0.8, 1.2, 0, math.pi * 2)
        ctx.arc(2.8, head_y - 0.8, 1.2, 0, math.pi * 2)
        ctx.fill()

        # Serious disciplined furrowed eyebrows
        ctx.set_source_rgb(0.4, 0.45, 0.5)
        ctx.set_line_width(1.1)
        ctx.move_to(-5, head_y - 3.5)
        ctx.line_to(-1.5, head_y - 2)
        ctx.move_to(5, head_y - 3.5)
        ctx.line_to(1.5, head_y - 2)
        ctx.stroke()

        # Annoyed small mouth
        ctx.set_source_rgb(0.6, 0.35, 0.35)
        ctx.set_line_width(1.0)
        ctx.move_to(-1.5, head_y + 4)
        ctx.line_to(1.5, head_y + 4)
        ctx.stroke()

        # Spiky Pure White / Silver Hair
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        spikes = [
            (-8, head_y - 4), (-10, head_y - 9), (-6, head_y - 12),
            (-5, head_y - 15), (-1, head_y - 18), (0, head_y - 14),
            (3, head_y - 18), (6, head_y - 14), (8, head_y - 10),
            (8, head_y - 4), (4, head_y - 6), (0, head_y - 7), (-4, head_y - 6)
        ]
        ctx.new_path()
        ctx.move_to(spikes[0][0], spikes[0][1])
        for sx, sy in spikes[1:]:
            ctx.line_to(sx, sy)
        ctx.close_path()
        ctx.fill()

        # Subtle frosty blue hair shadow
        ctx.set_source_rgb(0.82, 0.90, 0.98)
        ctx.set_line_width(1.0)
        ctx.move_to(-1, head_y - 16)
        ctx.line_to(0, head_y - 11)
        ctx.move_to(3, head_y - 16)
        ctx.line_to(2, head_y - 10)
        ctx.stroke()

        ctx.restore()

    def _draw_arms(self, ctx: cairo.Context) -> None:
        ctx.save()
        if self.substate == "HYORINMARU":
            # Directing ice dragon forward!
            ctx.set_source_rgb(0.96, 0.96, 0.98)
            ctx.rectangle(6, -6, 12, 5)
            ctx.fill()
            ctx.set_source_rgb(0.98, 0.85, 0.75)
            ctx.arc(18, -3.5, 2.5, 0, math.pi * 2)
            ctx.fill()
            # Ice dragon head contour
            ctx.set_source_rgba(0.4, 0.85, 1.0, 0.8)
            ctx.arc(24, -3.5, 5.0, 0, math.pi * 2)
            ctx.fill()
        elif self.substate == "CROSSED_ARMS":
            # Disciplined crossed arms across chest
            ctx.set_source_rgb(0.96, 0.96, 0.98)
            ctx.rectangle(-7, -4, 14, 5)
            ctx.fill()
            ctx.set_source_rgb(0.12, 0.12, 0.14)
            ctx.rectangle(-5, -2, 10, 3)
            ctx.fill()
        else:
            # Natural stance
            ctx.set_source_rgb(0.96, 0.96, 0.98)
            ctx.rectangle(-10, -6, 4, 14)
            ctx.rectangle(6, -6, 4, 14)
            ctx.fill()
            ctx.set_source_rgb(0.98, 0.85, 0.75)
            ctx.arc(-8, 8, 2.2, 0, math.pi * 2)
            ctx.arc(8, 8, 2.2, 0, math.pi * 2)
            ctx.fill()
        ctx.restore()
