"""Shunsui Kyōraku desktop companion: Katen Kyōkotsu dual blades, shadow games, and Karamatsu Shinjū."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, Optional

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager


class ShunsuiCharacter(BaseCharacter):
    """Shunsui Kyōraku — 8th Division Captain with dual blades Katen Kyōkotsu and theatrical Bankai."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="shunsui")
        self.can_fly = False
        self.is_bankai = False

        # States: "RELAXED", "TILT_HAT", "SIP_SAKE", "SHADOW_DIVE", "BANKAI_THEATER"
        self.substate = "RELAXED"
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
        if ability_name in ("kageoni", "shikai", "special"):
            self.substate = "SHADOW_DIVE"
            self.state_machine.transition_to(CharacterState.SHIKAI_ACTIVATION, duration=2.0)
            self.ability_end_time = now + 2.0
            particle_mgr.shockwave(self.x, self.y, max_radius=80.0, color=(0.1, 0.05, 0.15))
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.15, 0.1, 0.2), count=18)
            # Reappear near target
            self.x = target_x + random.uniform(-20, 20)
            self.y = target_y + random.uniform(-10, 10)
            if audio_mgr:
                audio_mgr.play("swoosh")
            return True

        elif ability_name in ("karamatsu_shinju", "bankai", "ultimate"):
            self.is_bankai = not self.is_bankai
            self.substate = "BANKAI_THEATER" if self.is_bankai else "RELAXED"
            self.state_machine.transition_to(
                CharacterState.BANKAI_ACTIVE if self.is_bankai else CharacterState.IDLE,
                duration=4.5 if self.is_bankai else None
            )
            self.ability_end_time = now + 4.5 if self.is_bankai else 0.0
            particle_mgr.shockwave(self.x, self.y, max_radius=135.0, color=(0.05, 0.05, 0.15), line_width=4.0)
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.1, 0.1, 0.3), count=25)
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name == "sip_sake":
            self.substate = "SIP_SAKE"
            self.substate_timer = now + 3.5
            return True

        elif ability_name == "tilt_hat":
            self.substate = "TILT_HAT"
            self.substate_timer = now + 2.5
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
        self.anim_time += dt * 3.5
        now = time.time()

        if self.ability_end_time > 0 and now > self.ability_end_time:
            self.substate = "RELAXED"
            self.ability_end_time = 0.0
            self.is_bankai = False
            self.state_machine.transition_to(CharacterState.IDLE)

        is_moving = math.hypot(self.vx, self.vy) > 0.5
        if is_moving:
            self.substate = "RELAXED"
        elif now > self.substate_timer and not self.is_bankai:
            self.substate = random.choice(["RELAXED", "TILT_HAT", "SIP_SAKE"])
            self.substate_timer = now + random.uniform(6.0, 13.0)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)

        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        t = self.anim_time
        breathe = math.sin(t) * 1.3
        is_moving = math.hypot(self.vx, self.vy) > 0.5
        leg_cycle = math.sin(t * 3.2) * 8.0 if is_moving else 0.0

        # Bankai stage shadow pool under feet
        if self.is_bankai:
            ctx.save()
            pat = cairo.RadialGradient(0, 20, 10, 0, 20, 50)
            pat.add_color_stop_rgba(0, 0.05, 0.05, 0.15, 0.6)
            pat.add_color_stop_rgba(1, 0.0, 0.0, 0.0, 0.0)
            ctx.set_source(pat)
            ctx.scale(1.4, 0.5)
            ctx.arc(0, 40, 45, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

        # Hakama / Black Pants
        ctx.set_source_rgba(0.12, 0.12, 0.14, 1.0)
        ctx.rectangle(-11 + leg_cycle * 0.35, 10, 9, 22)
        ctx.rectangle(2 - leg_cycle * 0.35, 10, 9, 22)
        ctx.fill()

        # Black Shihakushō inner robe
        ctx.rectangle(-12, -14 + breathe, 24, 25)
        ctx.fill()

        # Pink Floral Haori draped over shoulders
        ctx.set_source_rgba(0.96, 0.68, 0.76, 1.0)
        ctx.new_path()
        ctx.move_to(-18, -16 + breathe)
        ctx.line_to(18, -16 + breathe)
        ctx.line_to(20, 16)
        ctx.line_to(-20, 16)
        ctx.close_path()
        ctx.fill()

        # Cherry blossom flower patterns on haori
        ctx.set_source_rgba(0.9, 0.35, 0.5, 0.8)
        for fx, fy in [(-12, -4), (-6, 8), (10, -2), (12, 9)]:
            ctx.arc(fx, fy + breathe * 0.5, 2.5, 0, math.pi * 2)
            ctx.fill()

        # Dual Swords (Katen Kyōkotsu) tucked in sash
        ctx.save()
        ctx.translate(-14, 2 + breathe)
        ctx.rotate(-0.5)
        ctx.set_source_rgba(0.15, 0.15, 0.18, 1.0)
        ctx.rectangle(-2, 0, 4, 28)
        ctx.rectangle(1, 4, 3, 22)
        ctx.fill()
        # Red tassled cords
        ctx.set_source_rgba(0.85, 0.15, 0.15, 1.0)
        ctx.arc(-1, -4, 3, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # Head & Face
        ctx.set_source_rgba(0.96, 0.86, 0.78, 1.0)
        ctx.arc(0, -26 + breathe, 11, 0, math.pi * 2)
        ctx.fill()

        # Chin stubble
        ctx.set_source_rgba(0.35, 0.25, 0.2, 0.6)
        ctx.arc(0, -19 + breathe, 4, 0, math.pi)
        ctx.fill()

        # Wavy Brown Hair
        ctx.set_source_rgba(0.32, 0.2, 0.15, 1.0)
        ctx.arc(-8, -26 + breathe, 6, 0, math.pi * 2)
        ctx.arc(8, -26 + breathe, 6, 0, math.pi * 2)
        ctx.fill()

        # Straw Hat (Kasa)
        ctx.save()
        hat_tilt = -0.15 if self.substate == "TILT_HAT" else -0.05
        ctx.translate(0, -32 + breathe)
        ctx.rotate(hat_tilt)
        # Wide conical straw hat
        ctx.set_source_rgba(0.85, 0.72, 0.48, 1.0)
        ctx.new_path()
        ctx.move_to(0, -8)
        ctx.line_to(22, 4)
        ctx.line_to(-22, 4)
        ctx.close_path()
        ctx.fill()
        # Hat texture weave lines
        ctx.set_source_rgba(0.65, 0.52, 0.32, 0.7)
        ctx.set_line_width(1.0)
        ctx.move_to(0, -8)
        ctx.line_to(11, 4)
        ctx.move_to(0, -8)
        ctx.line_to(-11, 4)
        ctx.stroke()
        ctx.restore()

        # Sake cup if sipping
        if self.substate == "SIP_SAKE":
            ctx.save()
            ctx.set_source_rgba(0.9, 0.9, 0.92, 1.0)
            ctx.arc(6, -21 + breathe, 3.5, 0, math.pi * 2)
            ctx.fill()
            ctx.set_source_rgba(0.8, 0.2, 0.2, 1.0)
            ctx.arc(6, -21 + breathe, 1.8, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

        ctx.restore()
