"""Sōsuke Aizen desktop companion: Kyōka Suigetsu complete hypnosis, Kurohitsugi, and deceptive composure."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, Optional

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager


class AizenCharacter(BaseCharacter):
    """Sōsuke Aizen — Master of Kyōka Suigetsu, Complete Hypnosis, and Kurohitsugi."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="aizen")
        self.can_fly = False
        self.is_bankai = False

        # States: "COMPOSED", "ADJUST_GLASSES", "CALM_SMILE", "HYPNOSIS", "KUROHITSUGI"
        self.substate = "COMPOSED"
        self.substate_timer = time.time() + random.uniform(7.0, 14.0)
        self.ability_end_time = 0.0

        # Illusion clones
        self.illusion_active = False
        self.clones = []

        # Kurohitsugi coffin effect
        self.coffin_active = False
        self.coffin_progress = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        now = time.time()
        if ability_name in ("kyoka_suigetsu", "shikai", "special"):
            self.substate = "HYPNOSIS"
            self.state_machine.transition_to(CharacterState.SHIKAI_ACTIVATION, duration=2.5)
            self.ability_end_time = now + 3.0
            self.illusion_active = True
            self.clones = [
                (self.x - 45, self.y - 10, 0.6),
                (self.x + 45, self.y - 8, 0.6),
            ]
            particle_mgr.shockwave(self.x, self.y, max_radius=95.0, color=(0.7, 0.4, 0.95))
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.6, 0.3, 0.9), count=20)
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name in ("kurohitsugi", "bankai", "ultimate"):
            self.substate = "KUROHITSUGI"
            self.state_machine.transition_to(CharacterState.BANKAI_ACTIVATION, duration=3.2)
            self.ability_end_time = now + 3.5
            self.coffin_active = True
            self.coffin_progress = 0.0
            particle_mgr.shockwave(self.x, self.y, max_radius=130.0, color=(0.15, 0.05, 0.25), line_width=4.0)
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.2, 0.05, 0.35), count=30)
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name == "shunpo":
            self.x = target_x + random.uniform(-25, 25)
            self.y = target_y + random.uniform(-15, 15)
            particle_mgr.burst_sparks(self.x, self.y, count=10, color=(0.8, 0.6, 1.0))
            if audio_mgr:
                audio_mgr.play("swoosh")
            return True

        elif ability_name == "adjust_glasses":
            self.substate = "ADJUST_GLASSES"
            self.substate_timer = now + 2.5
            return True

        elif ability_name == "calm_smile":
            self.substate = "CALM_SMILE"
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
        self.anim_time += dt * 3.5
        now = time.time()

        if self.ability_end_time > 0 and now > self.ability_end_time:
            self.substate = "COMPOSED"
            self.ability_end_time = 0.0
            self.illusion_active = False
            self.coffin_active = False
            self.state_machine.transition_to(CharacterState.IDLE)

        if self.coffin_active:
            self.coffin_progress = min(1.0, self.coffin_progress + dt * 0.9)
            if random.random() < 0.3:
                particle_mgr.burst_reiatsu(self.x + random.uniform(-20, 20), self.y + random.uniform(-40, 20), color=(0.1, 0.0, 0.2), count=3)

        # Autonomous idle behaviors
        is_moving = math.hypot(self.vx, self.vy) > 0.5
        if is_moving:
            self.substate = "COMPOSED"
        elif now > self.substate_timer and not self.illusion_active and not self.coffin_active:
            choices = ["COMPOSED", "ADJUST_GLASSES", "CALM_SMILE"]
            self.substate = random.choice(choices)
            self.substate_timer = now + random.uniform(6.0, 12.0)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)

        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # Draw illusion clones if active
        if self.illusion_active:
            for cx, cy, alpha in self.clones:
                ctx.save()
                # World-relative offset back to local
                dx = (cx - self.x) * (1.0 if self.facing_right else -1.0)
                dy = cy - self.y
                ctx.translate(dx, dy)
                self._draw_aizen_figure(ctx, alpha=alpha * 0.7)
                ctx.restore()

        # Draw main figure
        self._draw_aizen_figure(ctx, alpha=1.0)

        # Kurohitsugi black box effect
        if self.coffin_active:
            self._draw_kurohitsugi(ctx)

        ctx.restore()

    def _draw_aizen_figure(self, ctx: cairo.Context, alpha: float = 1.0) -> None:
        t = self.anim_time
        breathe = math.sin(t) * 1.2
        is_moving = math.hypot(self.vx, self.vy) > 0.5
        leg_cycle = math.sin(t * 3.0) * 8.0 if is_moving else 0.0

        # Subtle lavender reiatsu glow
        pat = cairo.RadialGradient(0, -10, 5, 0, -10, 42)
        pat.add_color_stop_rgba(0, 0.55, 0.25, 0.85, 0.22 * alpha)
        pat.add_color_stop_rgba(1, 0.3, 0.1, 0.5, 0.0)
        ctx.set_source(pat)
        ctx.arc(0, -10, 42, 0, math.pi * 2)
        ctx.fill()

        # Hakama / Pants
        ctx.set_source_rgba(0.12, 0.12, 0.14, alpha)
        ctx.save()
        ctx.rectangle(-11 + leg_cycle * 0.3, 10, 9, 22)
        ctx.rectangle(2 - leg_cycle * 0.3, 10, 9, 22)
        ctx.fill()
        ctx.restore()

        # White Captain / Arrancar Robe (Haori)
        ctx.set_source_rgba(0.96, 0.96, 0.98, alpha)
        ctx.new_path()
        ctx.move_to(-16, -16 + breathe)
        ctx.line_to(16, -16 + breathe)
        ctx.line_to(18, 16)
        ctx.line_to(-18, 16)
        ctx.close_path()
        ctx.fill()

        # Black collar / sash
        ctx.set_source_rgba(0.1, 0.1, 0.12, alpha)
        ctx.rectangle(-8, -14 + breathe, 16, 12)
        ctx.fill()

        # Belt / Obi
        ctx.set_source_rgba(0.65, 0.15, 0.25, alpha)
        ctx.rectangle(-14, 2 + breathe, 28, 4)
        ctx.fill()

        # Zanpakutō Kyōka Suigetsu on hip
        ctx.save()
        ctx.translate(-14, 2 + breathe)
        ctx.rotate(-0.45)
        # Sheath
        ctx.set_source_rgba(0.18, 0.45, 0.35, alpha)
        ctx.rectangle(-2, 0, 4, 30)
        ctx.fill()
        # Guard (rhombus)
        ctx.set_source_rgba(0.85, 0.75, 0.25, alpha)
        ctx.rectangle(-5, -2, 10, 3)
        ctx.fill()
        # Hilt
        ctx.set_source_rgba(0.2, 0.6, 0.45, alpha)
        ctx.rectangle(-2, -12, 4, 10)
        ctx.fill()
        ctx.restore()

        # Head & Face
        ctx.set_source_rgba(0.98, 0.88, 0.82, alpha)
        ctx.arc(0, -28 + breathe, 11, 0, math.pi * 2)
        ctx.fill()

        # Calm closed-eye smile or observant glance
        ctx.set_source_rgba(0.3, 0.2, 0.2, alpha)
        ctx.set_line_width(1.5)
        if self.substate == "CALM_SMILE":
            # Serene crescent eyes
            ctx.arc(-4, -28 + breathe, 2.5, 0.2, math.pi - 0.2)
            ctx.stroke()
            ctx.arc(4, -28 + breathe, 2.5, 0.2, math.pi - 0.2)
            ctx.stroke()
            # Faint smile
            ctx.arc(0, -23 + breathe, 3.5, 0.2, math.pi - 0.2)
            ctx.stroke()
        else:
            # Observant cool eyes
            ctx.rectangle(-5, -29 + breathe, 3, 2)
            ctx.rectangle(3, -29 + breathe, 3, 2)
            ctx.fill()
            # Smirk
            ctx.move_to(-2, -23 + breathe)
            ctx.line_to(3, -22.5 + breathe)
            ctx.stroke()

        # Hair (Dark brown, sleek back with single front lock)
        ctx.set_source_rgba(0.22, 0.16, 0.12, alpha)
        ctx.new_path()
        ctx.arc(0, -31 + breathe, 12, math.pi, math.pi * 2)
        ctx.line_to(12, -26 + breathe)
        ctx.line_to(-12, -26 + breathe)
        ctx.close_path()
        ctx.fill()

        # Signature single strand of hair curving down forehead
        ctx.set_line_width(2.0)
        ctx.new_path()
        ctx.move_to(0, -38 + breathe)
        ctx.curve_to(3, -33 + breathe, 4, -27 + breathe, 2, -21 + breathe)
        ctx.stroke()

        # Arm & hand (adjusting glasses if in that substate)
        ctx.set_source_rgba(0.96, 0.96, 0.98, alpha)
        if self.substate == "ADJUST_GLASSES":
            ctx.save()
            ctx.set_line_width(3.0)
            ctx.move_to(8, -12 + breathe)
            ctx.line_to(7, -26 + breathe)
            ctx.stroke()
            ctx.set_source_rgba(0.98, 0.88, 0.82, alpha)
            ctx.arc(6, -27 + breathe, 2.5, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

    def _draw_kurohitsugi(self, ctx: cairo.Context) -> None:
        """Render Hadō #90: Kurohitsugi (Black Coffin)."""
        p = self.coffin_progress
        h = 75.0 * p
        w = 36.0

        ctx.save()
        ctx.set_source_rgba(0.08, 0.04, 0.12, 0.88)
        ctx.rectangle(-w * 0.5, -45 - (h - 75) * 0.5, w, h)
        ctx.fill()

        # Purple obsidian edges & gravity runes
        ctx.set_source_rgba(0.7, 0.25, 0.95, 0.9 * p)
        ctx.set_line_width(2.0)
        ctx.rectangle(-w * 0.5, -45 - (h - 75) * 0.5, w, h)
        ctx.stroke()

        # Piercing spears of dark light
        if p > 0.6:
            spear_alpha = (p - 0.6) / 0.4
            ctx.set_source_rgba(0.85, 0.4, 1.0, spear_alpha)
            ctx.set_line_width(2.5)
            for angle in (-0.5, 0.5, 2.6, 3.6):
                sx = math.cos(angle) * 45
                sy = math.sin(angle) * 45 - 20
                ctx.move_to(sx, sy)
                ctx.line_to(0, -20)
                ctx.stroke()
        ctx.restore()
