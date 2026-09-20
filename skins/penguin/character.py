"""Penguin desktop companion: waddling, belly sliding, and snowball tosses."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from behavior.personality import CharacterPersonality
from behavior.memory import CharacterMemory
from behavior.state_machine import CharacterBehavior, BehaviorState


class PenguinCharacter(BaseCharacter):
    """Playful tuxedo penguin companion with waddling and belly sliding."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="penguin")
        self.can_fly = False
        self.personality = CharacterPersonality(energy=0.65, curiosity=0.70, playfulness=0.85, sleepiness=0.50)
        self.memory = CharacterMemory(skin_id="penguin")
        self.behavior = CharacterBehavior("Penguin", personality=self.personality, memory=self.memory, can_fly=False)

        self.waddle = 0.0
        self.is_sliding = False

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("belly_slide", "slide"):
            self.is_sliding = True
            dx = target_x - self.x
            self.vx = (1.0 if dx >= 0 else -1.0) * 15.0
            particle_mgr.burst_dust(self.x, self.y + 20, count=4)
            audio_mgr.play("swoosh")
            self.memory.record_interaction("belly_slide")
            return True

        elif ability_name == "snowball_toss":
            particle_mgr.burst_stars(self.x + (16 if self.facing_right else -16), self.y, count=5, color=(0.9, 0.95, 1.0))
            audio_mgr.play("swoosh")
            self.memory.record_interaction("snowball_toss")
            return True

        elif ability_name in ("playful_waddle", "waddle"):
            self.waddle += 10.0
            particle_mgr.burst_hearts(self.x, self.y - 12, count=2)
            self.memory.record_interaction("playful_waddle")
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
        min_x, min_y, screen_w, screen_h = screen_bounds
        ground_y = min_y + screen_h - 70.0
        activity = config_data.get("activity_level", 1.0)

        if abs(cursor_x - self.x) > 6.0:
            self.facing_right = (cursor_x >= self.x)

        # Autonomous behavior
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

        if self.is_sliding:
            self.vx *= 0.96
            if abs(self.vx) < 1.0:
                self.is_sliding = False
        elif self.state in (BehaviorState.RUN, BehaviorState.WALK):
            tx = self.behavior.target_x
            dx = tx - self.x
            if abs(dx) > 16.0:
                spd = 6.0 if self.state == BehaviorState.RUN else 3.5
                self.vx += ((1.0 if dx > 0 else -1.0) * spd - self.vx) * 0.18
                self.waddle += dt * 12.0
            else:
                self.vx *= 0.8
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.8
            self.waddle = 0.0

        self.x += self.vx
        self.y = ground_y

        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # Waddle rocking tilt
        tilt_waddle = math.sin(self.waddle) * 0.16 if not self.is_sliding else 0.0
        ctx.rotate(tilt_waddle)

        if self.is_sliding:
            # Horizontal sliding pose
            ctx.save()
            ctx.rotate(math.pi * 0.35)
            # Black body
            ctx.set_source_rgb(0.12, 0.12, 0.15)
            ctx.arc(0, 0, 14, 0, math.pi * 2)
            ctx.fill()
            # White belly
            ctx.set_source_rgb(0.96, 0.96, 0.98)
            ctx.arc(4, 0, 9, 0, math.pi * 2)
            ctx.fill()
            # Orange beak
            ctx.set_source_rgb(1.0, 0.65, 0.1)
            ctx.move_to(12, -2)
            ctx.line_to(18, 0)
            ctx.line_to(12, 2)
            ctx.close_path()
            ctx.fill()
            ctx.restore()
            ctx.restore()
            return

        # Upright cute penguin pose
        # 1. Orange webbed feet
        ctx.save()
        ctx.set_source_rgb(1.0, 0.65, 0.1)
        foot_rock = math.sin(self.waddle) * 3.0
        ctx.arc(-6, 22 - foot_rock, 5, 0, math.pi * 2)
        ctx.fill()
        ctx.arc(6, 22 + foot_rock, 5, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # 2. Black Body & Head
        ctx.save()
        ctx.set_source_rgb(0.12, 0.12, 0.16)
        # Plump oval body
        ctx.save()
        ctx.translate(0, 4)
        ctx.scale(1.0, 1.25)
        ctx.arc(0, 0, 15, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # Head
        ctx.arc(0, -12, 11, 0, math.pi * 2)
        ctx.fill()

        # Flippers
        flipper_wave = math.sin(self.waddle * 1.5) * 4.0
        ctx.new_path()
        ctx.move_to(-12, 0)
        ctx.curve_to(-18, 8, -16 + flipper_wave, 18, -12, 14)
        ctx.fill()
        ctx.new_path()
        ctx.move_to(12, 0)
        ctx.curve_to(18, 8, 16 - flipper_wave, 18, 12, 14)
        ctx.fill()
        ctx.restore()

        # 3. Bright White Chest & Belly
        ctx.save()
        ctx.set_source_rgb(0.96, 0.97, 1.0)
        ctx.save()
        ctx.translate(2, 6)
        ctx.scale(1.0, 1.15)
        ctx.arc(0, 0, 10, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()
        ctx.restore()

        # 4. Face, Eyes & Beak
        ctx.save()
        # White eye mask patches
        ctx.set_source_rgb(0.96, 0.97, 1.0)
        ctx.arc(3, -13, 4, 0, math.pi * 2)
        ctx.fill()

        # Big cute eye
        ctx.set_source_rgb(0.1, 0.1, 0.15)
        ctx.arc(4, -13, 2.0, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(4.5, -14, 0.8, 0, math.pi * 2)
        ctx.fill()

        # Orange triangular beak
        ctx.set_source_rgb(1.0, 0.6, 0.1)
        ctx.new_path()
        ctx.move_to(7, -13)
        ctx.line_to(14, -11)
        ctx.line_to(7, -9)
        ctx.close_path()
        ctx.fill()

        # Blushing pink cheeks
        ctx.set_source_rgba(1.0, 0.5, 0.6, 0.45)
        ctx.arc(2, -8, 2.2, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        ctx.restore()
