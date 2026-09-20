"""Vampire desktop companion: cape hovering, bat swarm summoning, and shadow glides."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from behavior.personality import CharacterPersonality
from behavior.memory import CharacterMemory
from behavior.state_machine import CharacterBehavior, BehaviorState


class VampireCharacter(BaseCharacter):
    """Aristocratic vampire companion with high collar cape and bat swarms."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="vampire")
        self.can_fly = True
        self.is_airborne = True
        self.personality = CharacterPersonality(energy=0.70, curiosity=0.60, playfulness=0.50, sleepiness=0.45)
        self.memory = CharacterMemory(skin_id="vampire")
        self.behavior = CharacterBehavior("Vampire", personality=self.personality, memory=self.memory, can_fly=True)

        self.cape_wave = 0.0
        self.hover_y = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("bat_swarm", "bats"):
            for _ in range(6):
                particle_mgr.burst_stars(self.x + random.uniform(-15, 15), self.y + random.uniform(-10, 10), count=2, color=(0.2, 0.1, 0.25))
            particle_mgr.shockwave(self.x, self.y, max_radius=60.0, color=(0.8, 0.1, 0.2))
            audio_mgr.play("swoosh")
            self.memory.record_interaction("bat_swarm")
            return True

        elif ability_name in ("shadow_glide", "flight"):
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.vx = (dx / dist) * 14.0
            self.vy = (dy / dist) * 14.0
            self.state = CharacterState.FLY
            particle_mgr.smoke_puff(self.x, self.y, count=3, color=(0.2, 0.1, 0.2))
            audio_mgr.play("swoosh")
            self.memory.record_interaction("shadow_glide")
            return True

        elif ability_name == "mist_fade":
            for _ in range(6):
                particle_mgr.smoke_puff(self.x, self.y, count=3, color=(0.25, 0.1, 0.25))
            self.x = target_x
            self.y = target_y
            audio_mgr.play("swoosh")
            self.memory.record_interaction("mist_fade")
            return True

        return False

    def update(
        self,
        dt: float,
        cursor_x: float,
        cursor_y: float,
        screen_bounds: Tuple[int, int, int, int],
        particle_mgr: Any,
        audio_mgr: Any,
        config_data: Dict[str, Any]
    ) -> None:
        self.anim_time += dt * 4.0
        self.cape_wave += dt * 5.0
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)

        # Facing
        if abs(cursor_x - self.x) > 6.0:
            self.facing_right = (cursor_x >= self.x)

        # Autonomous decisions
        cursor_speed = math.hypot(cursor_x - self.x, cursor_y - self.y) / max(1e-4, dt)
        self.behavior.evaluate_next_action(
            dt=dt,
            char_x=self.x,
            char_y=self.y,
            cursor_x=cursor_x,
            cursor_y=cursor_y,
            cursor_speed=cursor_speed,
            screen_bounds=screen_bounds,
            pomodoro_state=config_data.get("pomodoro_state", "IDLE"),
            activity_level=activity
        )
        self.state = self.behavior.current_state

        # Hover
        self.hover_y = math.sin(self.anim_time) * 6.0

        if self.state in (BehaviorState.FLY, BehaviorState.WALK):
            tx, ty = self.behavior.target_x, self.behavior.target_y
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            if dist > 16.0:
                self.vx += ((dx / dist) * 4.8 - self.vx) * 0.12
                self.vy += ((dy / dist) * 4.8 - self.vy) * 0.12
            else:
                self.vx *= 0.82
                self.vy *= 0.82
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.82
            self.vy *= 0.82

        self.x += self.vx
        self.y += self.vy

        # Screen clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 70.0, self.y))

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        ctx.save()
        ctx.translate(self.x, self.y + self.hover_y)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Flowing Crimson-Lined Vampire Cape
        wave = math.sin(self.cape_wave) * 4.0
        ctx.save()
        # Outer black cape
        ctx.set_source_rgb(0.1, 0.08, 0.12)
        ctx.new_path()
        ctx.move_to(-12, -8)
        ctx.curve_to(-22, 10, -25 + wave, 24, -20 + wave, 28)
        ctx.line_to(16, 26)
        ctx.curve_to(12, 10, 8, -6, 4, -8)
        ctx.close_path()
        ctx.fill()

        # Inner Crimson Silk Lining
        ctx.set_source_rgb(0.78, 0.08, 0.15)
        ctx.new_path()
        ctx.move_to(-10, -6)
        ctx.curve_to(-18, 10, -18 + wave, 22, -14 + wave, 26)
        ctx.line_to(12, 24)
        ctx.curve_to(8, 10, 4, -4, 2, -6)
        ctx.close_path()
        ctx.fill()

        # High Pointed Vampire Collar
        ctx.set_source_rgb(0.78, 0.08, 0.15)
        ctx.new_path()
        ctx.move_to(-14, -6)
        ctx.line_to(-18, -24)  # Left tall wing
        ctx.line_to(-8, -14)
        ctx.line_to(0, -10)
        ctx.line_to(8, -14)
        ctx.line_to(18, -24)  # Right tall wing
        ctx.line_to(14, -6)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # 2. Aristocratic Vest & Cravat
        ctx.save()
        ctx.set_source_rgb(0.18, 0.18, 0.22)  # Charcoal vest
        ctx.rectangle(-8, -4, 16, 22)
        ctx.fill()
        # White cravat
        ctx.set_source_rgb(0.95, 0.95, 0.98)
        ctx.move_to(-5, -6)
        ctx.line_to(5, -6)
        ctx.line_to(0, 4)
        ctx.close_path()
        ctx.fill()
        # Ruby brooch
        ctx.set_source_rgb(0.9, 0.1, 0.2)
        ctx.arc(0, -2, 2.0, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # 3. Pale Vampire Face & Sleek Hair
        ctx.save()
        # Pale alabaster skin
        ctx.set_source_rgb(0.92, 0.94, 0.96)
        ctx.arc(0, -14, 10, 0, math.pi * 2)
        ctx.fill()

        # Sleek widow's peak hair
        ctx.set_source_rgb(0.08, 0.06, 0.1)
        ctx.new_path()
        ctx.arc(0, -16, 11, math.pi * 0.9, math.pi * 2.1)
        ctx.line_to(0, -17)  # Widow's peak point
        ctx.close_path()
        ctx.fill()

        # Crimson vampire eyes
        ctx.set_source_rgb(0.85, 0.1, 0.2)
        ctx.arc(3, -14, 1.8, 0, math.pi * 2)
        ctx.fill()

        # Charming smirk with tiny white fang
        ctx.set_source_rgb(0.2, 0.1, 0.15)
        ctx.set_line_width(1.0)
        ctx.move_to(1, -9)
        ctx.curve_to(3, -8, 5, -8, 6, -10)
        ctx.stroke()
        # Tiny fang
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.move_to(2, -8)
        ctx.line_to(3, -6)
        ctx.line_to(4, -8)
        ctx.fill()
        ctx.restore()

        ctx.restore()
