"""Yoruichi Shihōin desktop companion: Flash Goddess, Shunkō lightning, feline agility, and thunder steps."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, Optional

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager


class YoruichiCharacter(BaseCharacter):
    """Yoruichi Shihōin — Flash Goddess with Shunkō lightning and extreme agility."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="yoruichi")
        self.can_fly = False
        self.speed_multiplier = 1.35
        self.is_shunko = False

        # States: "AGILE_STANCE", "CAT_STRETCH", "PLAYFUL_TAUNT", "SHUNKO_BURST", "LIGHTNING_DASH"
        self.substate = "AGILE_STANCE"
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
        if ability_name in ("shunko", "bankai", "ultimate", "special"):
            self.is_shunko = not self.is_shunko
            self.substate = "SHUNKO_BURST" if self.is_shunko else "AGILE_STANCE"
            self.state_machine.transition_to(
                CharacterState.BANKAI_ACTIVE if self.is_shunko else CharacterState.IDLE,
                duration=4.5 if self.is_shunko else None
            )
            self.ability_end_time = now + 4.5 if self.is_shunko else 0.0

            particle_mgr.shockwave(self.x, self.y, max_radius=110.0, color=(0.4, 0.8, 1.0), line_width=3.5)
            particle_mgr.burst_sparks(self.x, self.y, count=30, color=(0.85, 0.95, 1.0))
            if audio_mgr:
                audio_mgr.play("lightning")
            return True

        elif ability_name in ("lightning_dash", "shunpo"):
            self.substate = "LIGHTNING_DASH"
            self.ability_end_time = now + 0.35
            particle_mgr.burst_sparks(self.x, self.y, count=16, color=(0.5, 0.85, 1.0))
            self.x = target_x + random.uniform(-20, 20)
            self.y = target_y + random.uniform(-15, 15)
            particle_mgr.shockwave(self.x, self.y, max_radius=65.0, color=(0.7, 0.9, 1.0))
            if audio_mgr:
                audio_mgr.play("swoosh")
            return True

        elif ability_name == "cat_stretch":
            self.substate = "CAT_STRETCH"
            self.substate_timer = now + 3.0
            return True

        elif ability_name == "playful_taunt":
            self.substate = "PLAYFUL_TAUNT"
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
        self.anim_time += dt * 5.0
        now = time.time()

        if self.ability_end_time > 0 and now > self.ability_end_time:
            self.substate = "AGILE_STANCE"
            self.ability_end_time = 0.0
            self.is_shunko = False
            self.state_machine.transition_to(CharacterState.IDLE)

        # Shunkō electric spark emitter
        if self.is_shunko and random.random() < 0.4:
            particle_mgr.burst_sparks(
                self.x + random.uniform(-15, 15),
                self.y + random.uniform(-30, 10),
                count=3,
                color=(0.7, 0.9, 1.0)
            )

        is_moving = math.hypot(self.vx, self.vy) > 0.5
        if is_moving:
            self.substate = "AGILE_STANCE"
        elif now > self.substate_timer and not self.is_shunko:
            self.substate = random.choice(["AGILE_STANCE", "CAT_STRETCH", "PLAYFUL_TAUNT"])
            self.substate_timer = now + random.uniform(5.0, 11.0)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)

        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        t = self.anim_time
        breathe = math.sin(t) * 1.5
        is_moving = math.hypot(self.vx, self.vy) > 0.5
        leg_cycle = math.sin(t * 4.0) * 10.0 if is_moving else 0.0

        # Shunkō lightning mantle
        if self.is_shunko:
            ctx.save()
            ctx.set_source_rgba(0.6, 0.85, 1.0, 0.35 + math.sin(t * 10) * 0.15)
            ctx.arc(0, -15, 36, 0, math.pi * 2)
            ctx.fill()
            # Lightning bolts
            ctx.set_source_rgba(0.9, 0.98, 1.0, 0.8)
            ctx.set_line_width(2.0)
            for i in range(4):
                ang = t * 6 + i * (math.pi / 2)
                lx1 = math.cos(ang) * 18
                ly1 = math.sin(ang) * 18 - 15
                lx2 = math.cos(ang) * 34 + random.uniform(-4, 4)
                ly2 = math.sin(ang) * 34 - 15 + random.uniform(-4, 4)
                ctx.move_to(lx1, ly1)
                ctx.line_to((lx1 + lx2) * 0.5 + random.uniform(-5, 5), (ly1 + ly2) * 0.5 + random.uniform(-5, 5))
                ctx.line_to(lx2, ly2)
                ctx.stroke()
            ctx.restore()

        # Legs (Shinobi tights)
        ctx.set_source_rgba(0.12, 0.12, 0.14, 1.0)
        ctx.rectangle(-10 + leg_cycle * 0.4, 8, 8, 22)
        ctx.rectangle(2 - leg_cycle * 0.4, 8, 8, 22)
        ctx.fill()

        # Orange ninja vest / undershirt
        ctx.set_source_rgba(0.95, 0.48, 0.08, 1.0)
        ctx.new_path()
        ctx.move_to(-12, -15 + breathe)
        ctx.line_to(12, -15 + breathe)
        ctx.line_to(14, 12)
        ctx.line_to(-14, 12)
        ctx.close_path()
        ctx.fill()

        # Black obi / belt
        ctx.set_source_rgba(0.15, 0.15, 0.18, 1.0)
        ctx.rectangle(-13, 2 + breathe, 26, 5)
        ctx.fill()

        # Skin tone (warm golden tan)
        ctx.set_source_rgba(0.78, 0.54, 0.42, 1.0)
        # Shoulders / arms
        ctx.rectangle(-14, -14 + breathe, 4, 16)
        ctx.rectangle(10, -14 + breathe, 4, 16)
        ctx.fill()

        # Head & Face
        ctx.arc(0, -26 + breathe, 10.5, 0, math.pi * 2)
        ctx.fill()

        # Amber / golden cat-like eyes
        ctx.set_source_rgba(0.95, 0.75, 0.1, 1.0)
        ctx.arc(-4, -26 + breathe, 2.5, 0, math.pi * 2)
        ctx.arc(4, -26 + breathe, 2.5, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgba(0.1, 0.1, 0.1, 1.0)
        ctx.arc(-4, -26 + breathe, 1.2, 0, math.pi * 2)
        ctx.arc(4, -26 + breathe, 1.2, 0, math.pi * 2)
        ctx.fill()

        # Playful smirk
        ctx.set_source_rgba(0.5, 0.2, 0.2, 1.0)
        ctx.set_line_width(1.2)
        ctx.arc(1, -21 + breathe, 3.0, 0.1, math.pi - 0.4)
        ctx.stroke()

        # Deep Purple Hair (Ponytail & Bangs)
        ctx.set_source_rgba(0.32, 0.15, 0.45, 1.0)
        ctx.new_path()
        ctx.arc(0, -29 + breathe, 11.5, math.pi * 0.8, math.pi * 2.2)
        ctx.fill()

        # Ponytail flowing backward
        tail_sway = math.sin(t * 3.5) * 4.0
        ctx.new_path()
        ctx.move_to(-6, -30 + breathe)
        ctx.curve_to(-16, -26 + breathe, -24 + tail_sway, -15 + breathe, -28 + tail_sway, -6 + breathe)
        ctx.curve_to(-22 + tail_sway, -12 + breathe, -14, -22 + breathe, -4, -25 + breathe)
        ctx.close_path()
        ctx.fill()

        # Forehead bangs
        ctx.new_path()
        ctx.move_to(-8, -32 + breathe)
        ctx.line_to(-4, -25 + breathe)
        ctx.line_to(0, -32 + breathe)
        ctx.line_to(4, -24 + breathe)
        ctx.line_to(8, -32 + breathe)
        ctx.close_path()
        ctx.fill()

        ctx.restore()
