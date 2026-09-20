"""Fox desktop companion: swift sprints, bushy tail wags, and playful pounces."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from behavior.personality import CharacterPersonality
from behavior.memory import CharacterMemory
from behavior.state_machine import CharacterBehavior, BehaviorState


class FoxCharacter(BaseCharacter):
    """Swift clever woodland red fox companion with lush bushy tail."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="fox")
        self.can_fly = False
        self.personality = CharacterPersonality(energy=0.90, curiosity=0.85, playfulness=0.85, sleepiness=0.25)
        self.memory = CharacterMemory(skin_id="fox")
        self.behavior = CharacterBehavior("Fox", personality=self.personality, memory=self.memory, can_fly=False)

        self.tail_wave = 0.0
        self.ear_twitch = 0.0
        self.paw_step = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("pounce_jump", "pounce"):
            dx = target_x - self.x
            self.vx = (1.0 if dx >= 0 else -1.0) * 12.0
            self.vy = -10.0
            self.state = CharacterState.JUMP
            particle_mgr.burst_dust(self.x, self.y + 20, count=4)
            audio_mgr.play("bark")
            self.memory.record_interaction("pounce_jump")
            return True

        elif ability_name in ("dash_sprint", "dash"):
            dx = target_x - self.x
            self.vx = (1.0 if dx >= 0 else -1.0) * 18.0
            particle_mgr.burst_dust(self.x, self.y + 20, count=5)
            audio_mgr.play("bark")
            self.memory.record_interaction("dash_sprint")
            return True

        elif ability_name in ("tail_flick", "wag"):
            self.tail_wave += 12.0
            particle_mgr.burst_hearts(self.x, self.y - 12, count=3)
            self.memory.record_interaction("tail_flick")
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
        self.tail_wave += dt * 8.0
        min_x, min_y, screen_w, screen_h = screen_bounds
        ground_y = min_y + screen_h - 70.0
        activity = config_data.get("activity_level", 1.0)

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

        if self.state in (BehaviorState.RUN, BehaviorState.WALK):
            tx = self.behavior.target_x
            dx = tx - self.x
            if abs(dx) > 16.0:
                spd = 8.5 if self.state == BehaviorState.RUN else 4.5
                self.vx += ((1.0 if dx > 0 else -1.0) * spd - self.vx) * 0.2
                self.paw_step += dt * 14.0
                if random.random() < 0.2:
                    particle_mgr.burst_dust(self.x, ground_y + 20, count=1)
            else:
                self.vx *= 0.8
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.8
            self.paw_step = 0.0

        # Jump physics
        if self.state == CharacterState.JUMP:
            self.vy += 0.8
            self.y += self.vy
            if self.y >= ground_y:
                self.y = ground_y
                self.vy = 0.0
                self.state = CharacterState.IDLE
        else:
            self.y = ground_y

        self.x += self.vx
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Bushy Curved Tail with White Tip
        tail_s = math.sin(self.tail_wave) * 6.0
        ctx.save()
        # Red-Orange tail base
        ctx.set_source_rgb(0.92, 0.38, 0.12)
        ctx.new_path()
        ctx.move_to(-12, 6)
        ctx.curve_to(-24, 0, -32, -10 + tail_s, -26, -20 + tail_s)
        ctx.curve_to(-18, -12, -14, -2, -10, 2)
        ctx.close_path()
        ctx.fill()

        # White tail tip
        ctx.set_source_rgb(0.98, 0.98, 1.0)
        ctx.new_path()
        ctx.move_to(-28, -15 + tail_s)
        ctx.curve_to(-32, -10 + tail_s, -26, -20 + tail_s, -22, -18 + tail_s)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # 2. Body (Lush Orange Coat)
        ctx.save()
        ctx.set_source_rgb(0.94, 0.4, 0.12)
        # Quadruped / seated body
        ctx.new_path()
        ctx.arc(0, 4, 14, 0, math.pi * 2)
        ctx.fill()

        # White Chest Bib
        ctx.set_source_rgb(0.98, 0.98, 1.0)
        ctx.new_path()
        ctx.move_to(4, -4)
        ctx.curve_to(12, 0, 10, 10, 4, 14)
        ctx.curve_to(0, 10, -2, 0, 4, -4)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # 3. Paws (Dark socks)
        ctx.save()
        ctx.set_source_rgb(0.18, 0.15, 0.15)
        step = math.sin(self.paw_step) * 3.0
        ctx.rectangle(-6, 14 - step, 5, 8)
        ctx.fill()
        ctx.rectangle(4, 14 + step, 5, 8)
        ctx.fill()
        ctx.restore()

        # 4. Fox Head & Face
        ctx.save()
        ctx.set_source_rgb(0.94, 0.4, 0.12)
        ctx.new_path()
        ctx.arc(6, -10, 11, 0, math.pi * 2)
        ctx.fill()

        # Muzzle & Nose
        ctx.new_path()
        ctx.move_to(10, -12)
        ctx.line_to(20, -8)
        ctx.line_to(10, -4)
        ctx.close_path()
        ctx.fill()

        # White cheek ruffs
        ctx.set_source_rgb(0.98, 0.98, 1.0)
        ctx.new_path()
        ctx.move_to(6, -6)
        ctx.curve_to(14, -4, 18, -7, 18, -8)
        ctx.line_to(12, -2)
        ctx.close_path()
        ctx.fill()

        # Black nose tip
        ctx.set_source_rgb(0.1, 0.1, 0.1)
        ctx.arc(20, -8, 1.8, 0, math.pi * 2)
        ctx.fill()

        # Clever Fox Eyes
        ctx.set_source_rgb(0.12, 0.1, 0.08)
        ctx.arc(10, -12, 1.8, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(10.5, -12.5, 0.7, 0, math.pi * 2)
        ctx.fill()

        # Pointed Ears with Black Backings
        ctx.set_source_rgb(0.18, 0.15, 0.15)  # Black ear tips
        ctx.new_path()
        ctx.move_to(0, -18)
        ctx.line_to(3, -28)
        ctx.line_to(10, -18)
        ctx.close_path()
        ctx.fill()
        # White inner ear fluff
        ctx.set_source_rgb(0.98, 0.98, 1.0)
        ctx.new_path()
        ctx.move_to(2, -18)
        ctx.line_to(4, -25)
        ctx.line_to(8, -18)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        ctx.restore()
