"""Mayuri Kurotsuchi desktop companion: Ashisogi Jizō, Konjiki Ashisogi Jizō poison caterpillar, and eccentric science."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, Optional

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager


class MayuriCharacter(BaseCharacter):
    """Mayuri Kurotsuchi — 12th Division Captain & Research Institute President with Konjiki Ashisogi Jizō."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="mayuri")
        self.can_fly = False
        self.is_bankai = False

        # States: "ECCENTRIC", "EXAMINE_SYRINGE", "MAD_CACKLE", "ASHISOGI_MIST", "KONJIKI_BANKAI"
        self.substate = "ECCENTRIC"
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
        if ability_name in ("ashisogi_jizo", "poison_mist", "shikai", "special"):
            self.substate = "ASHISOGI_MIST"
            self.state_machine.transition_to(CharacterState.SHIKAI_ACTIVATION, duration=2.2)
            self.ability_end_time = now + 2.5
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.8, 0.2, 0.9), count=20)
            particle_mgr.shockwave(self.x, self.y, max_radius=85.0, color=(0.7, 0.15, 0.85))
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name in ("konjiki_bankai", "bankai", "ultimate"):
            self.is_bankai = not self.is_bankai
            self.substate = "KONJIKI_BANKAI" if self.is_bankai else "ECCENTRIC"
            self.state_machine.transition_to(
                CharacterState.BANKAI_ACTIVE if self.is_bankai else CharacterState.IDLE,
                duration=4.5 if self.is_bankai else None
            )
            self.ability_end_time = now + 4.5 if self.is_bankai else 0.0
            particle_mgr.shockwave(self.x, self.y, max_radius=130.0, color=(0.95, 0.75, 0.1), line_width=4.0)
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.6, 0.1, 0.8), count=30)
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name == "mad_cackle":
            self.substate = "MAD_CACKLE"
            self.substate_timer = now + 3.0
            return True

        elif ability_name == "examine_syringe":
            self.substate = "EXAMINE_SYRINGE"
            self.substate_timer = now + 3.5
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
            self.substate = "ECCENTRIC"
            self.ability_end_time = 0.0
            self.is_bankai = False
            self.state_machine.transition_to(CharacterState.IDLE)

        # Poison particles if Bankai active
        if self.is_bankai and random.random() < 0.35:
            particle_mgr.burst_reiatsu(
                self.x + random.uniform(-25, 25),
                self.y + random.uniform(-15, 15),
                color=(0.6, 0.1, 0.8),
                count=2
            )

        is_moving = math.hypot(self.vx, self.vy) > 0.5
        if is_moving:
            self.substate = "ECCENTRIC"
        elif now > self.substate_timer and not self.is_bankai:
            self.substate = random.choice(["ECCENTRIC", "EXAMINE_SYRINGE", "MAD_CACKLE"])
            self.substate_timer = now + random.uniform(5.0, 11.0)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)

        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        t = self.anim_time
        breathe = math.sin(t) * 1.2
        is_moving = math.hypot(self.vx, self.vy) > 0.5
        leg_cycle = math.sin(t * 3.2) * 8.0 if is_moving else 0.0

        # Giant Konjiki Ashisogi Jizō background silhouette if Bankai
        if self.is_bankai:
            ctx.save()
            ctx.set_source_rgba(0.95, 0.8, 0.15, 0.45)
            # Giant caterpillar body
            ctx.arc(0, -48, 28, 0, math.pi * 2)
            ctx.fill()
            # Silver halo ring
            ctx.set_source_rgba(0.95, 0.95, 1.0, 0.7)
            ctx.set_line_width(2.5)
            ctx.arc(0, -78, 14, 0, math.pi * 2)
            ctx.stroke()
            ctx.restore()

        # Hakama / Pants
        ctx.set_source_rgba(0.12, 0.12, 0.14, 1.0)
        ctx.rectangle(-10 + leg_cycle * 0.35, 10, 8, 22)
        ctx.rectangle(2 - leg_cycle * 0.35, 10, 8, 22)
        ctx.fill()

        # White Captain Haori with purple inner collar
        ctx.set_source_rgba(0.96, 0.96, 0.98, 1.0)
        ctx.new_path()
        ctx.move_to(-15, -15 + breathe)
        ctx.line_to(15, -15 + breathe)
        ctx.line_to(17, 14)
        ctx.line_to(-17, 14)
        ctx.close_path()
        ctx.fill()

        # Purple silk collar trim
        ctx.set_source_rgba(0.55, 0.12, 0.75, 1.0)
        ctx.rectangle(-8, -14 + breathe, 16, 10)
        ctx.fill()

        # Head & Face Makeup (Iconic Black & White split mask)
        ctx.set_source_rgba(0.98, 0.98, 0.98, 1.0)
        ctx.arc(0, -26 + breathe, 10.5, 0, math.pi * 2)
        ctx.fill()

        # Black facepaint wrapping around eyes and ears
        ctx.set_source_rgba(0.08, 0.08, 0.1, 1.0)
        ctx.rectangle(-10.5, -29 + breathe, 21, 6)
        ctx.fill()

        # Yellow cat eyes within black paint
        ctx.set_source_rgba(0.95, 0.85, 0.1, 1.0)
        ctx.arc(-4, -26 + breathe, 2.0, 0, math.pi * 2)
        ctx.arc(4, -26 + breathe, 2.0, 0, math.pi * 2)
        ctx.fill()

        # Golden Headdress & Crown Spikes
        ctx.set_source_rgba(0.95, 0.8, 0.15, 1.0)
        # Giant crescent crest over head
        ctx.new_path()
        ctx.move_to(-16, -32 + breathe)
        ctx.curve_to(0, -46 + breathe, 0, -46 + breathe, 16, -32 + breathe)
        ctx.line_to(12, -28 + breathe)
        ctx.curve_to(0, -38 + breathe, 0, -38 + breathe, -12, -28 + breathe)
        ctx.close_path()
        ctx.fill()

        # Ear trumpet / horn protrusions
        ctx.rectangle(-14, -28 + breathe, 4, 10)
        ctx.rectangle(10, -28 + breathe, 4, 10)
        ctx.fill()

        # Syringe prop if examining
        if self.substate == "EXAMINE_SYRINGE":
            ctx.save()
            ctx.set_source_rgba(0.2, 0.9, 0.4, 0.9)
            ctx.rectangle(8, -24 + breathe, 4, 12)
            ctx.fill()
            ctx.set_source_rgba(0.8, 0.8, 0.85, 1.0)
            ctx.set_line_width(1.5)
            ctx.move_to(10, -24 + breathe)
            ctx.line_to(10, -30 + breathe)
            ctx.stroke()
            ctx.restore()

        ctx.restore()
