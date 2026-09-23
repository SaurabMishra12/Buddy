"""Ulquiorra Cifer desktop companion: Murciélago bat wings, Cero Oscuras, and Segunda Etapa."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, Optional

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager


class UlquiorraCharacter(BaseCharacter):
    """Ulquiorra Cifer — 4th Espada with Murciélago bat wings, Cero Oscuras, and Segunda Etapa."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="ulquiorra")
        self.can_fly = True
        self.is_resurreccion = False
        self.is_segunda_etapa = False

        # States: "STOIC", "GLARE", "CERO_OSCURAS", "MURCIELAGO_WINGS", "LANZA"
        self.substate = "STOIC"
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
        if ability_name in ("cero_oscuras", "special"):
            self.substate = "CERO_OSCURAS"
            self.state_machine.transition_to(CharacterState.ATTACK, duration=1.8)
            self.ability_end_time = now + 1.8
            # Black and green Cero
            particle_mgr.shockwave(self.x, self.y, max_radius=100.0, color=(0.1, 0.9, 0.3), line_width=4.0)
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.02, 0.02, 0.02), count=25)
            if audio_mgr:
                audio_mgr.play("fire")
            return True

        elif ability_name in ("resurreccion_murcielago", "shikai"):
            self.is_resurreccion = not self.is_resurreccion
            self.substate = "MURCIELAGO_WINGS" if self.is_resurreccion else "STOIC"
            self.state_machine.transition_to(
                CharacterState.SHIKAI_ACTIVE if self.is_resurreccion else CharacterState.IDLE,
                duration=4.5 if self.is_resurreccion else None
            )
            self.ability_end_time = now + 4.5 if self.is_resurreccion else 0.0
            particle_mgr.shockwave(self.x, self.y, max_radius=120.0, color=(0.1, 0.85, 0.3), line_width=3.5)
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.08, 0.75, 0.25), count=30)
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name in ("lanza_del_relampago", "bankai", "ultimate"):
            self.is_segunda_etapa = not self.is_segunda_etapa
            self.substate = "LANZA" if self.is_segunda_etapa else "STOIC"
            self.state_machine.transition_to(
                CharacterState.BANKAI_ACTIVE if self.is_segunda_etapa else CharacterState.IDLE,
                duration=4.5 if self.is_segunda_etapa else None
            )
            self.ability_end_time = now + 4.5 if self.is_segunda_etapa else 0.0
            particle_mgr.shockwave(self.x, self.y, max_radius=145.0, color=(0.0, 1.0, 0.4), line_width=4.5)
            particle_mgr.burst_sparks(self.x, self.y, count=35, color=(0.2, 1.0, 0.5))
            if audio_mgr:
                audio_mgr.play("lightning")
            return True

        elif ability_name in ("sonido", "shunpo"):
            self.x = target_x + random.uniform(-20, 20)
            self.y = target_y + random.uniform(-15, 15)
            particle_mgr.burst_sparks(self.x, self.y, count=12, color=(0.1, 0.8, 0.3))
            if audio_mgr:
                audio_mgr.play("swoosh")
            return True

        elif ability_name == "stoic_glare":
            self.substate = "GLARE"
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
        self.anim_time += dt * 3.8
        now = time.time()

        if self.ability_end_time > 0 and now > self.ability_end_time:
            self.substate = "STOIC"
            self.ability_end_time = 0.0
            self.is_resurreccion = False
            self.is_segunda_etapa = False
            self.state_machine.transition_to(CharacterState.IDLE)

        # Green spiritual rain if Resurrección
        if (self.is_resurreccion or self.is_segunda_etapa) and random.random() < 0.4:
            particle_mgr.burst_reiatsu(
                self.x + random.uniform(-20, 20),
                self.y + random.uniform(-20, 20),
                color=(0.1, 0.85, 0.3),
                count=2
            )

        is_moving = math.hypot(self.vx, self.vy) > 0.5
        if is_moving:
            self.substate = "STOIC"
        elif now > self.substate_timer and not self.is_resurreccion and not self.is_segunda_etapa:
            self.substate = random.choice(["STOIC", "GLARE"])
            self.substate_timer = now + random.uniform(6.0, 12.0)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)

        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        t = self.anim_time
        breathe = math.sin(t) * 1.2
        is_moving = math.hypot(self.vx, self.vy) > 0.5
        leg_cycle = math.sin(t * 3.4) * 8.0 if is_moving else 0.0

        # Giant black leathery bat wings if Resurrección or Segunda Etapa
        if self.is_resurreccion or self.is_segunda_etapa:
            ctx.save()
            wing_flap = math.sin(t * 4.0) * 0.15
            ctx.set_source_rgba(0.08, 0.08, 0.1, 0.95)
            # Left wing
            ctx.new_path()
            ctx.move_to(-12, -15 + breathe)
            ctx.curve_to(-28, -48 + wing_flap * 30, -55, -35, -52, -10 + wing_flap * 20)
            ctx.curve_to(-38, -5, -28, 5, -12, 5 + breathe)
            ctx.close_path()
            ctx.fill()
            # Right wing
            ctx.new_path()
            ctx.move_to(12, -15 + breathe)
            ctx.curve_to(28, -48 - wing_flap * 30, 55, -35, 52, -10 - wing_flap * 20)
            ctx.curve_to(38, -5, 28, 5, 12, 5 + breathe)
            ctx.close_path()
            ctx.fill()
            ctx.restore()

        # White Arrancar Pants
        ctx.set_source_rgba(0.95, 0.95, 0.97, 1.0)
        ctx.rectangle(-10 + leg_cycle * 0.35, 10, 8, 22)
        ctx.rectangle(2 - leg_cycle * 0.35, 10, 8, 22)
        ctx.fill()

        # White Arrancar Coat with black edge seams
        ctx.set_source_rgba(0.96, 0.96, 0.98, 1.0)
        ctx.new_path()
        ctx.move_to(-14, -15 + breathe)
        ctx.line_to(14, -15 + breathe)
        ctx.line_to(16, 16)
        ctx.line_to(-16, 16)
        ctx.close_path()
        ctx.fill()

        # Black edge seams
        ctx.set_source_rgba(0.12, 0.12, 0.14, 1.0)
        ctx.set_line_width(1.5)
        ctx.move_to(0, -15 + breathe)
        ctx.line_to(0, 16)
        ctx.stroke()

        # Head & Face (Pale alabaster skin)
        ctx.set_source_rgba(0.94, 0.95, 0.96, 1.0)
        ctx.arc(0, -26 + breathe, 10.5, 0, math.pi * 2)
        ctx.fill()

        # Emerald green eyes
        ctx.set_source_rgba(0.1, 0.85, 0.3, 1.0)
        ctx.arc(-4, -26 + breathe, 2.0, 0, math.pi * 2)
        ctx.arc(4, -26 + breathe, 2.0, 0, math.pi * 2)
        ctx.fill()

        # Iconic teal/dark green tear tracks flowing down cheeks
        ctx.set_source_rgba(0.12, 0.55, 0.35, 1.0)
        ctx.set_line_width(1.5)
        ctx.move_to(-4, -24 + breathe)
        ctx.line_to(-4, -17 + breathe)
        ctx.move_to(4, -24 + breathe)
        ctx.line_to(4, -17 + breathe)
        ctx.stroke()

        # Black messy hair
        ctx.set_source_rgba(0.12, 0.12, 0.15, 1.0)
        ctx.new_path()
        ctx.arc(0, -29 + breathe, 11.5, math.pi * 0.75, math.pi * 2.25)
        ctx.fill()

        # Horned Hollow mask fragment on left side of head
        ctx.set_source_rgba(0.96, 0.96, 0.98, 1.0)
        ctx.new_path()
        ctx.move_to(-8, -32 + breathe)
        ctx.curve_to(-14, -42 + breathe, -18, -48 + breathe, -16, -50 + breathe)
        ctx.curve_to(-13, -44 + breathe, -10, -38 + breathe, -6, -34 + breathe)
        ctx.close_path()
        ctx.fill()

        # Lanza del Relámpago (Green lightning javelin) if Segunda Etapa
        if self.is_segunda_etapa:
            ctx.save()
            ctx.translate(14, -15 + breathe)
            ctx.set_source_rgba(0.2, 1.0, 0.5, 0.95)
            ctx.set_line_width(2.5)
            ctx.move_to(0, -30)
            ctx.line_to(0, 30)
            ctx.stroke()
            ctx.restore()

        ctx.restore()
