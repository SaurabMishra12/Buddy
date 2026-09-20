"""Ninja desktop companion: smoke dashes, shuriken throws, and shadow teleports."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from behavior.personality import CharacterPersonality
from behavior.memory import CharacterMemory
from behavior.state_machine import CharacterBehavior, BehaviorState


class NinjaCharacter(BaseCharacter):
    """Silent shadow shinobi companion with swift dashes and smoke bombs."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="ninja")
        self.can_fly = False
        self.personality = CharacterPersonality(energy=0.88, curiosity=0.55, playfulness=0.40, sleepiness=0.20)
        self.memory = CharacterMemory(skin_id="ninja")
        self.behavior = CharacterBehavior("Ninja", personality=self.personality, memory=self.memory, can_fly=False)

        self.stride = 0.0
        self.headband_wave = 0.0
        self.shadow_trail: list = []

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("smoke_teleport", "smoke_bomb"):
            for _ in range(8):
                particle_mgr.smoke_puff(self.x, self.y, count=3, color=(0.2, 0.2, 0.25))
            self.x = target_x
            self.y = target_y
            particle_mgr.burst_dust(self.x, self.y + 20, count=6)
            audio_mgr.play("swoosh")
            self.memory.record_interaction("smoke_teleport")
            return True

        elif ability_name in ("shuriken_strike", "shuriken"):
            for _ in range(4):
                particle_mgr.burst_stars(self.x + (15 if self.facing_right else -15), self.y, count=2, color=(0.8, 0.8, 0.85))
            audio_mgr.play("swoosh")
            self.memory.record_interaction("shuriken_strike")
            return True

        elif ability_name == "shadow_dash":
            dx = target_x - self.x
            self.vx = (1.0 if dx >= 0 else -1.0) * 22.0
            particle_mgr.burst_dust(self.x, self.y + 20, count=4)
            audio_mgr.play("swoosh")
            self.memory.record_interaction("shadow_dash")
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
        self.anim_time += dt * 6.0
        self.headband_wave += dt * 7.0
        min_x, min_y, screen_w, screen_h = screen_bounds
        ground_y = min_y + screen_h - 70.0
        activity = config_data.get("activity_level", 1.0)

        # Facing
        if abs(cursor_x - self.x) > 6.0:
            self.facing_right = (cursor_x >= self.x)

        # Behavior decision
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

        # Locomotion along ground
        if self.state in (BehaviorState.RUN, BehaviorState.WALK):
            tx = self.behavior.target_x
            dx = tx - self.x
            if abs(dx) > 18.0:
                spd = 8.0 if self.state == BehaviorState.RUN else 4.2
                self.vx += ((1.0 if dx > 0 else -1.0) * spd - self.vx) * 0.22
                self.stride += dt * (16.0 if self.state == BehaviorState.RUN else 9.0)
                if random.random() < 0.2:
                    particle_mgr.burst_dust(self.x, ground_y + 20, count=1)
            else:
                self.vx *= 0.8
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.8
            self.stride = 0.0

        self.x += self.vx
        self.y = ground_y

        # Screen clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # Leg stride bounce
        leg_offset = math.sin(self.stride) * 4.0 if abs(self.vx) > 0.5 else 0.0

        # 1. Legs (Shinobi Hakama Trousers)
        ctx.save()
        ctx.set_source_rgb(0.12, 0.12, 0.14)
        # Left leg
        ctx.rectangle(-8, 12 - leg_offset, 6, 14)
        ctx.fill()
        # Right leg
        ctx.rectangle(2, 12 + leg_offset, 6, 14)
        ctx.fill()

        # Ninja Tabi Wraps (White ankle wrap cords)
        ctx.set_source_rgb(0.85, 0.85, 0.85)
        ctx.set_line_width(1.0)
        ctx.move_to(-8, 20 - leg_offset)
        ctx.line_to(-2, 20 - leg_offset)
        ctx.move_to(2, 20 + leg_offset)
        ctx.line_to(8, 20 + leg_offset)
        ctx.stroke()
        ctx.restore()

        # 2. Torso (Midnight Black Gi)
        ctx.save()
        ctx.set_source_rgb(0.14, 0.14, 0.16)
        ctx.new_path()
        ctx.move_to(-12, -8)
        ctx.line_to(12, -8)
        ctx.line_to(10, 14)
        ctx.line_to(-10, 14)
        ctx.close_path()
        ctx.fill()

        # Crimson Red Sash Belt
        ctx.set_source_rgb(0.85, 0.15, 0.15)
        ctx.rectangle(-11, 8, 22, 4)
        ctx.fill()

        # Katana Scabbard on Back
        ctx.set_source_rgb(0.2, 0.2, 0.22)
        ctx.set_line_width(2.5)
        ctx.move_to(-16, 10)
        ctx.line_to(14, -20)
        ctx.stroke()
        # Gold hilt
        ctx.set_source_rgb(0.95, 0.8, 0.2)
        ctx.move_to(14, -20)
        ctx.line_to(18, -24)
        ctx.stroke()
        ctx.restore()

        # 3. Masked Head
        ctx.save()
        # Black hood
        ctx.set_source_rgb(0.12, 0.12, 0.15)
        ctx.arc(0, -18, 12, 0, math.pi * 2)
        ctx.fill()

        # Skin eye-slit cutout
        ctx.set_source_rgb(0.95, 0.82, 0.72)
        ctx.rectangle(-7, -22, 14, 6)
        ctx.fill()

        # Focused sharp eyes
        ctx.set_source_rgb(0.1, 0.1, 0.1)
        ctx.arc(3, -19, 1.6, 0, math.pi * 2)
        ctx.fill()

        # Crimson Red Forehead Band & Flying Ribbons
        ctx.set_source_rgb(0.88, 0.12, 0.12)
        ctx.rectangle(-12, -26, 24, 3)
        ctx.fill()

        # Flowing ribbon tails behind head
        wave1 = math.sin(self.headband_wave) * 4.0
        wave2 = math.cos(self.headband_wave) * 3.0
        ctx.set_line_width(2.5)
        ctx.new_path()
        ctx.move_to(-11, -25)
        ctx.curve_to(-18, -25 + wave1, -24, -20 + wave2, -30, -22 + wave1)
        ctx.stroke()
        ctx.restore()

        ctx.restore()
