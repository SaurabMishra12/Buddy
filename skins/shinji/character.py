"""Shinji Hirako desktop companion: Sakanade inverted perception, Hollow mask, and eccentric swagger."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, Optional

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager


class ShinjiCharacter(BaseCharacter):
    """Shinji Hirako — 5th Division Captain with Sakanade inverted optical perception and Visored mask."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="shinji")
        self.can_fly = False
        self.is_inverted = False
        self.has_mask = False

        # States: "SWAGGER", "CHEEKY_GRIN", "SAKANADE_SPIN", "HOLLOW_MASK"
        self.substate = "SWAGGER"
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
        if ability_name in ("sakanade", "inverted_world", "shikai", "special"):
            self.is_inverted = not self.is_inverted
            self.substate = "SAKANADE_SPIN" if self.is_inverted else "SWAGGER"
            self.state_machine.transition_to(
                CharacterState.SHIKAI_ACTIVE if self.is_inverted else CharacterState.IDLE,
                duration=4.0 if self.is_inverted else None
            )
            self.ability_end_time = now + 4.0 if self.is_inverted else 0.0
            particle_mgr.shockwave(self.x, self.y, max_radius=95.0, color=(1.0, 0.4, 0.8))
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.95, 0.3, 0.7), count=22)
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name in ("hollow_mask", "bankai", "ultimate"):
            self.has_mask = not self.has_mask
            self.substate = "HOLLOW_MASK" if self.has_mask else "SWAGGER"
            self.state_machine.transition_to(
                CharacterState.BANKAI_ACTIVE if self.has_mask else CharacterState.IDLE,
                duration=4.5 if self.has_mask else None
            )
            self.ability_end_time = now + 4.5 if self.has_mask else 0.0
            particle_mgr.shockwave(self.x, self.y, max_radius=110.0, color=(0.85, 0.1, 0.2), line_width=3.5)
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.8, 0.05, 0.1), count=26)
            if audio_mgr:
                audio_mgr.play("fire")
            return True

        elif ability_name == "cheeky_grin":
            self.substate = "CHEEKY_GRIN"
            self.substate_timer = now + 3.0
            return True

        elif ability_name == "shunpo":
            self.x = target_x + random.uniform(-25, 25)
            self.y = target_y + random.uniform(-15, 15)
            particle_mgr.burst_sparks(self.x, self.y, count=10, color=(0.9, 0.8, 0.2))
            if audio_mgr:
                audio_mgr.play("swoosh")
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
        super().update(dt, cursor_x, cursor_y, screen_bounds, particle_mgr, audio_mgr, config_data)
        self.anim_time += dt * 3.8
        now = time.time()

        if self.ability_end_time > 0 and now > self.ability_end_time:
            self.substate = "SWAGGER"
            self.ability_end_time = 0.0
            self.is_inverted = False
            self.has_mask = False
            self.state_machine.transition_to(CharacterState.IDLE)

        is_moving = math.hypot(self.vx, self.vy) > 0.5
        if is_moving:
            self.substate = "SWAGGER"
        elif now > self.substate_timer and not self.is_inverted and not self.has_mask:
            self.substate = random.choice(["SWAGGER", "CHEEKY_GRIN"])
            self.substate_timer = now + random.uniform(5.0, 11.0)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)

        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # Inverted World: Render-layer inversion / tilt
        if self.is_inverted:
            invert_angle = math.sin(self.anim_time * 2.5) * 0.35 + math.pi
            ctx.rotate(invert_angle)

        t = self.anim_time
        breathe = math.sin(t) * 1.3
        is_moving = math.hypot(self.vx, self.vy) > 0.5
        leg_cycle = math.sin(t * 3.4) * 8.5 if is_moving else 0.0

        # Hakama / Pants
        ctx.set_source_rgba(0.12, 0.12, 0.14, 1.0)
        ctx.rectangle(-10 + leg_cycle * 0.35, 10, 8, 22)
        ctx.rectangle(2 - leg_cycle * 0.35, 10, 8, 22)
        ctx.fill()

        # White Captain Haori & Shihakushō
        ctx.set_source_rgba(0.96, 0.96, 0.98, 1.0)
        ctx.new_path()
        ctx.move_to(-14, -15 + breathe)
        ctx.line_to(14, -15 + breathe)
        ctx.line_to(16, 14)
        ctx.line_to(-16, 14)
        ctx.close_path()
        ctx.fill()

        # Modern necktie hanging down
        ctx.set_source_rgba(0.7, 0.2, 0.25, 1.0)
        ctx.new_path()
        ctx.move_to(-2, -14 + breathe)
        ctx.line_to(2, -14 + breathe)
        ctx.line_to(3, 4 + breathe)
        ctx.line_to(0, 7 + breathe)
        ctx.line_to(-3, 4 + breathe)
        ctx.close_path()
        ctx.fill()

        # Sakanade Sword with Ring Guard at hip
        ctx.save()
        ctx.translate(-14, 2 + breathe)
        ctx.rotate(-0.4)
        ctx.set_source_rgba(0.2, 0.2, 0.22, 1.0)
        ctx.rectangle(-2, 0, 4, 26)
        ctx.fill()
        # Large spinning ring pommel
        ctx.set_source_rgba(0.95, 0.82, 0.1, 1.0)
        ctx.set_line_width(2.0)
        ctx.arc(0, -6, 5.0, 0, math.pi * 2)
        ctx.stroke()
        ctx.restore()

        # Head & Face
        ctx.set_source_rgba(0.96, 0.88, 0.82, 1.0)
        ctx.arc(0, -26 + breathe, 10.5, 0, math.pi * 2)
        ctx.fill()

        # Visored Hollow Mask
        if self.has_mask:
            ctx.set_source_rgba(0.95, 0.95, 0.98, 1.0)
            ctx.new_path()
            ctx.move_to(-8, -32 + breathe)
            ctx.line_to(8, -32 + breathe)
            ctx.line_to(10, -20 + breathe)
            ctx.line_to(0, -14 + breathe)
            ctx.line_to(-10, -20 + breathe)
            ctx.close_path()
            ctx.fill()
            # Red pharaoh slits
            ctx.set_source_rgba(0.85, 0.1, 0.15, 1.0)
            ctx.set_line_width(2.0)
            ctx.move_to(-6, -24 + breathe)
            ctx.line_to(6, -24 + breathe)
            ctx.stroke()
        else:
            # Brown sharp eyes
            ctx.set_source_rgba(0.3, 0.2, 0.15, 1.0)
            ctx.rectangle(-5, -26 + breathe, 3, 2)
            ctx.rectangle(2, -26 + breathe, 3, 2)
            ctx.fill()

            # Iconic wide toothy cheeky grin
            ctx.set_source_rgba(0.95, 0.95, 0.95, 1.0)
            ctx.rectangle(-5, -21 + breathe, 10, 4)
            ctx.fill()
            ctx.set_source_rgba(0.2, 0.2, 0.2, 1.0)
            ctx.set_line_width(1.0)
            ctx.rectangle(-5, -21 + breathe, 10, 4)
            ctx.stroke()
            for tx in (-2, 1):
                ctx.move_to(tx, -21 + breathe)
                ctx.line_to(tx, -17 + breathe)
                ctx.stroke()

        # Blonde Bob Cut Hair
        ctx.set_source_rgba(0.96, 0.88, 0.32, 1.0)
        ctx.new_path()
        ctx.arc(0, -29 + breathe, 11.5, math.pi * 0.75, math.pi * 2.25)
        ctx.fill()
        # Straight-cut blunt bob bangs
        ctx.rectangle(-11, -34 + breathe, 22, 9)
        ctx.fill()

        ctx.restore()
