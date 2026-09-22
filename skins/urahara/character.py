"""Kisuke Urahara desktop companion: Benihime, Kannonbiraki Bankai, Striped Bucket Hat, and Paper Fan."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, Optional

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager


class UraharaCharacter(BaseCharacter):
    """Kisuke Urahara — Former 12th Division Captain and Shop Owner."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="urahara")
        self.can_fly = False
        self.is_bankai = False

        # States: "RELAXED", "OPEN_FAN", "ADJUST_HAT", "GADGET", "BENIHIME", "BANKAI"
        self.substate = "RELAXED"
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
        if ability_name in ("benihime", "special"):
            self.substate = "BENIHIME"
            self.ability_end_time = now + 2.5
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.95, 0.15, 0.3), count=18)
            particle_mgr.shockwave(self.x, self.y, max_radius=85.0, color=(0.9, 0.15, 0.3))
            if audio_mgr:
                audio_mgr.play("laser")
            return True

        elif ability_name == "kannonbiraki_bankai":
            self.is_bankai = not self.is_bankai
            self.substate = "BANKAI" if self.is_bankai else "RELAXED"
            self.ability_end_time = now + 5.0 if self.is_bankai else 0.0
            particle_mgr.shockwave(self.x, self.y, max_radius=125.0, color=(0.95, 0.1, 0.25), line_width=4.0)
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.9, 0.1, 0.25), count=24)
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name == "open_fan":
            self.substate = "OPEN_FAN"
            self.substate_timer = now + 3.5
            return True

        elif ability_name == "adjust_hat":
            self.substate = "ADJUST_HAT"
            self.substate_timer = now + 3.0
            return True

        elif ability_name == "gadget_tinker":
            self.substate = "GADGET"
            self.substate_timer = now + 4.0
            particle_mgr.burst_sparks(self.x + 14, self.y - 4, count=6, color=(0.2, 0.8, 1.0))
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

        if self.ability_end_time > 0 and now > self.ability_end_time:
            self.substate = "RELAXED"
            self.ability_end_time = 0.0

        is_moving = math.hypot(self.vx, self.vy) > 0.5
        if is_moving:
            self.substate = "RELAXED"
        else:
            if self.ability_end_time <= 0 and now >= self.substate_timer:
                self.substate_timer = now + random.uniform(6.0, 13.0)
                options = ["RELAXED", "OPEN_FAN", "ADJUST_HAT", "GADGET"]
                self.substate = random.choice(options)

        # Ambient crimson Reiatsu threads in Bankai
        if self.is_bankai and random.random() < 0.20:
            particle_mgr.burst_reiatsu(self.x, self.y + 10, color=(0.9, 0.1, 0.25), count=1)

        # Facing direction
        if abs(cursor_x - self.x) > 10.0:
            self.facing_right = (cursor_x >= self.x)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1, 1)

        # Relaxed lazy sway bob
        bob_y = math.sin(self.anim_time * 1.8) * 1.0
        ctx.translate(0, bob_y)

        # 1. Kannonbiraki Bankai Giant Entity Silhouette & Red Restructuring Threads
        if self.is_bankai or self.substate == "BANKAI":
            self._draw_kannonbiraki_entity(ctx)

        # 2. Cane Sword (Shikomizue)
        self._draw_cane(ctx)

        # 3. Wooden Geta & Hakama
        self._draw_legs(ctx)

        # 4. Dark Green Haori & Kimono
        self._draw_robes(ctx)

        # 5. Head, Blonde Messy Hair, Striped Bucket Hat & Smirk
        self._draw_head(ctx)

        # 6. Arms & Props (Paper Fan, Cane Grip, or Gadget)
        self._draw_arms(ctx)

        ctx.restore()

    def _draw_kannonbiraki_entity(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Towering mannequin goddess behind him
        ctx.set_source_rgba(0.25, 0.08, 0.15, 0.45)
        ctx.new_path()
        ctx.move_to(-24, -45)
        ctx.curve_to(-35, -20, -32, 10, -18, 20)
        ctx.line_to(18, 20)
        ctx.curve_to(32, 10, 35, -20, 24, -45)
        ctx.close_path()
        ctx.fill()

        # Restructuring crimson threads spreading outwards
        ctx.set_source_rgba(0.95, 0.15, 0.3, 0.8)
        ctx.set_line_width(1.1)
        for tx, ty in [(-28, -15), (-20, 10), (20, 10), (28, -15), (0, -42)]:
            ctx.move_to(0, -10)
            ctx.line_to(tx, ty)
        ctx.stroke()
        ctx.restore()

    def _draw_cane(self, ctx: cairo.Context) -> None:
        ctx.save()
        if self.substate != "BENIHIME":
            # Shikomizue walking cane held or rested at side
            ctx.set_source_rgb(0.55, 0.38, 0.22)
            ctx.rectangle(8, -2, 2.8, 30)
            ctx.fill()
            # Golden ferrule
            ctx.set_source_rgb(0.85, 0.70, 0.2)
            ctx.rectangle(8, 26, 2.8, 2.5)
            ctx.fill()
        ctx.restore()

    def _draw_legs(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Dark grey/black hakama trousers
        ctx.set_source_rgb(0.12, 0.12, 0.14)
        ctx.rectangle(-8, 12, 6, 14)
        ctx.rectangle(2, 12, 6, 14)
        ctx.fill()

        # Wooden Geta sandals (elevated wooden teeth)
        ctx.set_source_rgb(0.60, 0.42, 0.25)
        # Left geta
        ctx.rectangle(-8, 26, 6, 2.5)
        ctx.rectangle(-8, 28.5, 2, 2.5)
        ctx.rectangle(-4, 28.5, 2, 2.5)
        # Right geta
        ctx.rectangle(2, 26, 6, 2.5)
        ctx.rectangle(2, 28.5, 2, 2.5)
        ctx.rectangle(6, 28.5, 2, 2.5)
        ctx.fill()
        # Red thong straps
        ctx.set_source_rgb(0.85, 0.15, 0.15)
        ctx.set_line_width(1.0)
        ctx.move_to(-6, 26)
        ctx.line_to(-5, 24)
        ctx.move_to(4, 26)
        ctx.line_to(5, 24)
        ctx.stroke()
        ctx.restore()

    def _draw_robes(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Black under-kimono
        ctx.set_source_rgb(0.12, 0.12, 0.14)
        ctx.rectangle(-10, -8, 20, 22)
        ctx.fill()

        # Dark forest green Haori jacket
        ctx.set_source_rgb(0.15, 0.35, 0.22)
        ctx.new_path()
        ctx.move_to(-12, -8)
        ctx.line_to(12, -8)
        ctx.line_to(14, 18)
        ctx.line_to(-14, 18)
        ctx.close_path()
        ctx.fill()

        # White diamond pattern along haori lower hem
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        for dx in range(-11, 12, 4):
            ctx.new_path()
            ctx.move_to(dx, 16)
            ctx.line_to(dx + 2, 14)
            ctx.line_to(dx + 4, 16)
            ctx.line_to(dx + 2, 18)
            ctx.close_path()
            ctx.fill()
        ctx.restore()

    def _draw_head(self, ctx: cairo.Context) -> None:
        ctx.save()
        head_y = -16

        # Messy blonde / sand-colored hair
        ctx.set_source_rgb(0.94, 0.88, 0.65)
        ctx.new_path()
        ctx.move_to(-8, head_y - 2)
        ctx.line_to(-10, head_y + 4)
        ctx.line_to(10, head_y + 4)
        ctx.line_to(8, head_y - 2)
        ctx.close_path()
        ctx.fill()

        # Face
        ctx.set_source_rgb(0.96, 0.82, 0.70)
        ctx.new_path()
        ctx.move_to(-6, head_y - 4)
        ctx.line_to(6, head_y - 4)
        ctx.line_to(5, head_y + 3)
        ctx.line_to(0, head_y + 7)  # Slender jaw
        ctx.line_to(-5, head_y + 3)
        ctx.close_path()
        ctx.fill()

        # Scruffy chin stubble
        ctx.set_source_rgb(0.4, 0.35, 0.3)
        ctx.set_line_width(0.8)
        ctx.move_to(-2, head_y + 5.5)
        ctx.line_to(2, head_y + 5.5)
        ctx.stroke()

        # Eyes shaded under hat brim (keen grey eyes peeking out)
        ctx.set_source_rgb(0.95, 0.95, 0.95)
        ctx.rectangle(-4.5, head_y - 1.5, 3.5, 2.5)
        ctx.rectangle(1.0, head_y - 1.5, 3.5, 2.5)
        ctx.fill()
        ctx.set_source_rgb(0.35, 0.45, 0.45)
        ctx.arc(-2.8, head_y - 0.5, 1.2, 0, math.pi * 2)
        ctx.arc(2.8, head_y - 0.5, 1.2, 0, math.pi * 2)
        ctx.fill()

        # Knowing mysterious smirk
        ctx.set_source_rgb(0.5, 0.25, 0.2)
        ctx.set_line_width(1.1)
        ctx.move_to(-1, head_y + 4)
        ctx.line_to(3, head_y + 3.2)
        ctx.stroke()

        # Iconic Green & White Striped Bucket Hat!
        hat_y = head_y - 6
        # Flat crown
        ctx.set_source_rgb(0.20, 0.45, 0.28)  # Green base
        ctx.rectangle(-8, hat_y - 9, 16, 9)
        ctx.fill()
        # White vertical stripes on crown
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        for sx in (-5, -1, 3):
            ctx.rectangle(sx, hat_y - 9, 2.5, 9)
            ctx.fill()

        # Hat Brim sloping down
        ctx.set_source_rgb(0.20, 0.45, 0.28)
        ctx.new_path()
        ctx.move_to(-12, hat_y + 1)
        ctx.line_to(12, hat_y + 1)
        ctx.line_to(9, hat_y - 1)
        ctx.line_to(-9, hat_y - 1)
        ctx.close_path()
        ctx.fill()

        # White stripes on brim
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        for sx in (-7, -2, 3):
            ctx.rectangle(sx, hat_y - 1, 2.5, 2)
            ctx.fill()

        ctx.restore()

    def _draw_arms(self, ctx: cairo.Context) -> None:
        ctx.save()
        sleeve_color = (0.15, 0.35, 0.22)

        if self.substate == "BENIHIME":
            # Drawing Benihime cane-sword with crimson energy aura!
            ctx.set_source_rgb(*sleeve_color)
            ctx.rectangle(6, -6, 12, 5)
            ctx.fill()
            ctx.set_source_rgb(0.96, 0.82, 0.70)
            ctx.arc(18, -3.5, 2.8, 0, math.pi * 2)
            ctx.fill()

            # Benihime blade (crimson edge & ornate black guard)
            ctx.translate(18, -3.5)
            ctx.rotate(-0.35)
            # Steel blade
            ctx.set_source_rgb(0.85, 0.85, 0.9)
            ctx.rectangle(0, -1.5, 34, 3)
            ctx.fill()
            # Crimson reiatsu glow along edge
            ctx.set_source_rgba(0.95, 0.15, 0.3, 0.85)
            ctx.set_line_width(1.5)
            ctx.move_to(0, 1.5)
            ctx.line_to(34, 1.5)
            ctx.stroke()

        elif self.substate == "OPEN_FAN":
            # Holding paper fan covering mouth/chin
            ctx.set_source_rgb(*sleeve_color)
            ctx.rectangle(2, -4, 8, 4)
            ctx.fill()
            ctx.set_source_rgb(0.96, 0.82, 0.70)
            ctx.arc(6, -2, 2.5, 0, math.pi * 2)
            ctx.fill()

            # Open paper fan
            ctx.save()
            ctx.translate(2, -12)
            ctx.set_source_rgb(0.92, 0.85, 0.70)
            ctx.new_path()
            ctx.move_to(0, 4)
            ctx.arc(0, 4, 10.0, -math.pi * 0.85, -math.pi * 0.15)
            ctx.close_path()
            ctx.fill()
            # Wooden fan ribs
            ctx.set_source_rgb(0.55, 0.38, 0.22)
            ctx.set_line_width(0.8)
            for fa in (-0.75, -0.5, -0.25):
                ctx.move_to(0, 4)
                ctx.line_to(math.cos(fa * math.pi) * 10, math.sin(fa * math.pi) * 10 + 4)
            ctx.stroke()
            ctx.restore()

        elif self.substate == "ADJUST_HAT":
            # Hand tipping hat brim
            ctx.set_source_rgb(*sleeve_color)
            ctx.rectangle(4, -8, 6, 8)
            ctx.fill()
            ctx.set_source_rgb(0.96, 0.82, 0.70)
            ctx.arc(8, -18, 2.5, 0, math.pi * 2)
            ctx.fill()

        else:
            # Relaxed stance with hand resting on cane
            ctx.set_source_rgb(*sleeve_color)
            ctx.rectangle(6, -6, 4, 12)
            ctx.fill()
            ctx.set_source_rgb(0.96, 0.82, 0.70)
            ctx.arc(8, 4, 2.5, 0, math.pi * 2)
            ctx.fill()

        ctx.restore()
