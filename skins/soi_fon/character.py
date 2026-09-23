"""Soi Fon desktop companion: Suzumebachi stinger, Nigeki Kessatsu, and Jakuhō Raikōben Bankai."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, Optional

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager


class SoiFonCharacter(BaseCharacter):
    """Soi Fon — 2nd Division Captain & Onmitsukidō Commander with Suzumebachi and Jakuhō Raikōben."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="soi_fon")
        self.can_fly = False
        self.speed_multiplier = 1.3
        self.is_bankai = False

        # States: "POOSED", "SCOUT_STANCE", "STINGER_STRIKE", "BANKAI_LAUNCH"
        self.substate = "POISED"
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
        if ability_name in ("suzumebachi", "nigeki_kessatsu", "shikai", "special"):
            self.substate = "STINGER_STRIKE"
            self.state_machine.transition_to(CharacterState.SHIKAI_ACTIVATION, duration=1.8)
            self.ability_end_time = now + 1.8
            particle_mgr.burst_sparks(self.x, self.y, count=18, color=(1.0, 0.85, 0.1))
            particle_mgr.shockwave(self.x, self.y, max_radius=85.0, color=(1.0, 0.8, 0.0))
            if audio_mgr:
                audio_mgr.play("swoosh")
            return True

        elif ability_name in ("jakuho_raikoben", "bankai", "ultimate"):
            self.is_bankai = not self.is_bankai
            self.substate = "BANKAI_LAUNCH" if self.is_bankai else "POISED"
            self.state_machine.transition_to(
                CharacterState.BANKAI_ACTIVE if self.is_bankai else CharacterState.IDLE,
                duration=4.0 if self.is_bankai else None
            )
            self.ability_end_time = now + 4.0 if self.is_bankai else 0.0
            particle_mgr.shockwave(self.x, self.y, max_radius=140.0, color=(1.0, 0.6, 0.0), line_width=4.5)
            particle_mgr.burst_sparks(self.x, self.y, count=35, color=(1.0, 0.9, 0.2))
            if audio_mgr:
                audio_mgr.play("fire")
            return True

        elif ability_name == "stealth_step":
            self.x = target_x + random.uniform(-20, 20)
            self.y = target_y + random.uniform(-15, 15)
            particle_mgr.burst_sparks(self.x, self.y, count=10, color=(0.9, 0.9, 0.3))
            if audio_mgr:
                audio_mgr.play("swoosh")
            return True

        elif ability_name == "scout_stance":
            self.substate = "SCOUT_STANCE"
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
        super().update(dt, cursor_x, cursor_y, screen_bounds, particle_mgr, audio_mgr, config_data)
        self.anim_time += dt * 4.5
        now = time.time()

        if self.ability_end_time > 0 and now > self.ability_end_time:
            self.substate = "POISED"
            self.ability_end_time = 0.0
            self.is_bankai = False
            self.state_machine.transition_to(CharacterState.IDLE)

        is_moving = math.hypot(self.vx, self.vy) > 0.5
        if is_moving:
            self.substate = "POISED"
        elif now > self.substate_timer and not self.is_bankai:
            self.substate = random.choice(["POISED", "SCOUT_STANCE"])
            self.substate_timer = now + random.uniform(5.0, 10.0)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)

        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        t = self.anim_time
        breathe = math.sin(t) * 1.3
        is_moving = math.hypot(self.vx, self.vy) > 0.5
        leg_cycle = math.sin(t * 3.8) * 9.0 if is_moving else 0.0

        # Hakama
        ctx.set_source_rgba(0.12, 0.12, 0.14, 1.0)
        ctx.rectangle(-9 + leg_cycle * 0.4, 8, 7, 22)
        ctx.rectangle(2 - leg_cycle * 0.4, 7, 7, 22)
        ctx.fill()

        # White Captain Haori (sleeveless)
        ctx.set_source_rgba(0.96, 0.96, 0.98, 1.0)
        ctx.new_path()
        ctx.move_to(-13, -15 + breathe)
        ctx.line_to(13, -15 + breathe)
        ctx.line_to(15, 12)
        ctx.line_to(-15, 12)
        ctx.close_path()
        ctx.fill()

        # Black inner uniform & yellow sash
        ctx.set_source_rgba(0.95, 0.8, 0.15, 1.0)
        ctx.rectangle(-12, 2 + breathe, 24, 4)
        ctx.fill()

        # Bare arms & skin
        ctx.set_source_rgba(0.96, 0.88, 0.82, 1.0)
        ctx.rectangle(-14, -13 + breathe, 3.5, 14)
        ctx.rectangle(10.5, -13 + breathe, 3.5, 14)
        ctx.fill()

        # Head & Face
        ctx.arc(0, -25 + breathe, 9.5, 0, math.pi * 2)
        ctx.fill()

        # Sharp gray/black eyes
        ctx.set_source_rgba(0.2, 0.2, 0.25, 1.0)
        ctx.rectangle(-4, -26 + breathe, 2.5, 2.0)
        ctx.rectangle(2, -26 + breathe, 2.5, 2.0)
        ctx.fill()

        # Short black hair
        ctx.set_source_rgba(0.15, 0.15, 0.18, 1.0)
        ctx.new_path()
        ctx.arc(0, -27 + breathe, 10.5, math.pi * 0.8, math.pi * 2.2)
        ctx.fill()

        # Twin braided side loops wrapped in white rings
        for sx in (-9, 9):
            ctx.set_source_rgba(0.15, 0.15, 0.18, 1.0)
            ctx.arc(sx, -20 + breathe, 4.0, 0, math.pi * 2)
            ctx.fill()
            ctx.set_source_rgba(0.95, 0.95, 0.98, 1.0)
            ctx.arc(sx, -20 + breathe, 2.2, 0, math.pi * 2)
            ctx.stroke()

        # Bankai: Massive Golden Missile (Jakuhō Raikōben)
        if self.is_bankai:
            ctx.save()
            ctx.translate(14, -8 + breathe)
            ctx.rotate(0.25)
            # Gold launcher body
            ctx.set_source_rgba(0.98, 0.78, 0.1, 1.0)
            ctx.new_path()
            ctx.move_to(-8, -12)
            ctx.line_to(36, -6)
            ctx.line_to(44, 0)
            ctx.line_to(36, 6)
            ctx.line_to(-8, 12)
            ctx.close_path()
            ctx.fill()
            # Steel lining
            ctx.set_source_rgba(0.3, 0.3, 0.35, 1.0)
            ctx.rectangle(0, -8, 28, 16)
            ctx.stroke()
            ctx.restore()
        else:
            # Suzumebachi golden wasp stinger on right hand
            ctx.save()
            ctx.translate(12, 1 + breathe)
            ctx.set_source_rgba(0.98, 0.82, 0.1, 1.0)
            ctx.new_path()
            ctx.move_to(0, -2)
            ctx.line_to(10, 0)
            ctx.line_to(0, 2)
            ctx.close_path()
            ctx.fill()
            ctx.restore()

        ctx.restore()
