"""Bouncy Slime desktop companion: squash-and-stretch jelly bounce and split particles."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from behavior.personality import CharacterPersonality
from behavior.memory import CharacterMemory
from behavior.state_machine import CharacterBehavior, BehaviorState


class SlimeCharacter(BaseCharacter):
    """Vibrant, elastic jelly slime companion with squash and stretch physics."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="slime")
        self.can_fly = False
        self.personality = CharacterPersonality(energy=0.85, curiosity=0.80, playfulness=0.95, sleepiness=0.20)
        self.memory = CharacterMemory(skin_id="slime")
        self.behavior = CharacterBehavior("Slime", personality=self.personality, memory=self.memory, can_fly=False)

        # Squash and stretch state
        self.squash_x = 1.0
        self.squash_y = 1.0
        self.wobble_freq = 10.0
        self.wobble_amp = 0.0
        self.blink_timer = 0.0
        self.is_blinking = False

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("super_bounce", "bounce"):
            dx = target_x - self.x
            self.vx = (1.0 if dx >= 0 else -1.0) * 9.0
            self.vy = -14.0
            self.squash_x = 0.6
            self.squash_y = 1.5
            self.state = CharacterState.JUMP
            particle_mgr.burst_stars(self.x, self.y + 15, count=6)
            audio_mgr.play("sparkle")
            self.memory.record_interaction("super_bounce")
            return True

        elif ability_name in ("jelly_split", "split"):
            self.wobble_amp = 0.5
            particle_mgr.burst_energy_orbs(self.x, self.y, count=8)
            particle_mgr.burst_confetti(self.x, self.y - 10, count=12)
            audio_mgr.play("sparkle")
            self.memory.record_interaction("jelly_split")
            return True

        elif ability_name in ("wobble", "jiggle"):
            self.wobble_amp = 0.6
            particle_mgr.burst_hearts(self.x, self.y - 20, count=4)
            audio_mgr.play("sparkle")
            self.memory.record_interaction("wobble")
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

        # Look direction
        if abs(cursor_x - self.x) > 10.0:
            self.facing_right = (cursor_x >= self.x)

        # Autonomous AI decisions
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

        # Blinking logic
        self.blink_timer -= dt
        if self.blink_timer <= 0:
            self.is_blinking = not self.is_blinking
            self.blink_timer = 0.15 if self.is_blinking else random.uniform(2.5, 6.0)

        # Movement and physics
        if self.state in (BehaviorState.WALK, BehaviorState.RUN):
            tx = self.behavior.target_x
            dx = tx - self.x
            if abs(dx) > 12.0:
                # Bouncing hop motion
                hop_spd = 5.0 if self.state == BehaviorState.WALK else 9.0
                dir_x = 1.0 if dx > 0 else -1.0
                self.vx += (dir_x * hop_spd - self.vx) * 0.15

                # Slime hopping rhythm
                hop_cycle = math.sin(self.anim_time * 2.5)
                if hop_cycle > 0.3 and self.y >= ground_y - 2:
                    self.vy = -5.0
                    self.squash_x = 0.75
                    self.squash_y = 1.3
            else:
                self.vx *= 0.8
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.85

        # Gravity & ground contact
        if self.y < ground_y or self.vy != 0.0:
            self.vy += 0.75
            self.y += self.vy
            # Airborne stretch
            if self.vy < -1.0:
                self.squash_x = max(0.7, self.squash_x - dt * 2.0)
                self.squash_y = min(1.4, self.squash_y + dt * 2.0)
            elif self.vy > 1.0:
                self.squash_x = min(1.1, self.squash_x + dt * 1.5)
                self.squash_y = max(0.9, self.squash_y - dt * 1.5)

            if self.y >= ground_y:
                self.y = ground_y
                # Land impact squash
                self.squash_x = 1.45
                self.squash_y = 0.65
                self.vy = 0.0
                if random.random() < 0.3:
                    particle_mgr.burst_dust(self.x, ground_y + 15, count=2)
                if self.state == CharacterState.JUMP:
                    self.state = CharacterState.IDLE
        else:
            self.y = ground_y

        # Recover squash back toward 1.0
        self.squash_x += (1.0 - self.squash_x) * 0.18
        self.squash_y += (1.0 - self.squash_y) * 0.18

        # Dampen wobble amplitude
        if self.wobble_amp > 0.01:
            self.wobble_amp *= 0.94
        else:
            self.wobble_amp = 0.0

        # Boundary clamping
        self.x += self.vx
        self.x = max(min_x + 40.0, min(min_x + screen_w - 40.0, self.x))

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)

        # Facing direction
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # Apply squash & stretch + wobble
        wobble = math.sin(self.anim_time * self.wobble_freq) * self.wobble_amp
        sx = self.squash_x + wobble
        sy = self.squash_y - wobble
        ctx.scale(sx, sy)

        # Ground soft shadow
        ctx.save()
        ctx.set_source_rgba(0.05, 0.15, 0.1, 0.22)
        ctx.scale(1.0, 0.3)
        ctx.arc(0, 48 / sy, 34 * sx, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # Slime body: organic jelly droplet dome
        # Base gradient (fresh lime/emerald jelly)
        pat = cairo.RadialGradient(-8, -12, 4, 0, 0, 36)
        pat.add_color_stop_rgba(0.0, 0.45, 0.95, 0.4, 0.92)   # Translucent bright core
        pat.add_color_stop_rgba(0.65, 0.15, 0.75, 0.3, 0.88)  # Mid emerald
        pat.add_color_stop_rgba(1.0, 0.08, 0.55, 0.22, 0.95)  # Darker jelly edge
        ctx.set_source(pat)

        ctx.new_path()
        # Draw curved teardrop dome
        ctx.move_to(-28, 14)
        ctx.curve_to(-32, -6, -20, -28, 0, -32)     # Left side to tip
        ctx.curve_to(20, -28, 32, -6, 28, 14)       # Tip to right side
        ctx.curve_to(20, 20, -20, 20, -28, 14)      # Bottom curve
        ctx.close_path()
        ctx.fill_preserve()

        # Jelly contour edge shine
        ctx.set_source_rgba(0.55, 1.0, 0.55, 0.5)
        ctx.set_line_width(2.0)
        ctx.stroke()

        # Inner floating bubble nucleus
        ctx.save()
        ctx.set_source_rgba(0.8, 1.0, 0.7, 0.45)
        n_wobble = math.sin(self.anim_time * 3.0) * 2.0
        ctx.arc(6 + n_wobble, 2, 7, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # Cute face
        eye_y = -6
        eye_x_left = -10
        eye_x_right = 10

        if self.is_blinking:
            # Happy closed curved eyes (^_^)
            ctx.set_source_rgba(0.05, 0.3, 0.1, 0.85)
            ctx.set_line_width(2.2)
            ctx.new_path()
            ctx.arc(eye_x_left, eye_y, 4, math.pi * 1.1, math.pi * 1.9)
            ctx.stroke()
            ctx.new_path()
            ctx.arc(eye_x_right, eye_y, 4, math.pi * 1.1, math.pi * 1.9)
            ctx.stroke()
        else:
            # Glossy anime oval eyes
            for ex in (eye_x_left, eye_x_right):
                ctx.set_source_rgba(0.04, 0.25, 0.1, 0.9)
                ctx.save()
                ctx.translate(ex, eye_y)
                ctx.scale(1.0, 1.3)
                ctx.arc(0, 0, 4.0, 0, 2 * math.pi)
                ctx.fill()

                # Big eye catchlight
                ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95)
                ctx.arc(1.2, -1.2, 1.6, 0, 2 * math.pi)
                ctx.fill()
                # Tiny secondary catchlight
                ctx.arc(-1.0, 1.2, 0.8, 0, 2 * math.pi)
                ctx.fill()
                ctx.restore()

        # Rosy blushing cheeks
        ctx.set_source_rgba(1.0, 0.4, 0.6, 0.4)
        ctx.save()
        ctx.scale(1.3, 0.8)
        ctx.arc(-16 / 1.3, 2 / 0.8, 3.5, 0, 2 * math.pi)
        ctx.fill()
        ctx.arc(16 / 1.3, 2 / 0.8, 3.5, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # Cheerful mouth
        ctx.set_source_rgba(0.04, 0.25, 0.1, 0.85)
        ctx.set_line_width(1.8)
        ctx.new_path()
        ctx.arc(0, 0, 3.5, 0.2 * math.pi, 0.8 * math.pi)
        ctx.stroke()

        # Top specular highlight (glassy gloss)
        ctx.save()
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.6)
        ctx.rotate(-0.35)
        ctx.scale(1.8, 0.7)
        ctx.arc(-6, -30, 7, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        ctx.restore()
