"""Penguin desktop companion: authentic waddle gait, belly sliding with frost trails,
flying snowball projectiles, and joyful flipper flaps.
"""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, List
from skins.base import BaseCharacter, CharacterState
from behavior.personality import CharacterPersonality
from behavior.memory import CharacterMemory
from behavior.state_machine import CharacterBehavior, BehaviorState


class PenguinCharacter(BaseCharacter):
    """Adorable Antarctic penguin companion with authentic side-to-side waddling,
    dynamic belly sliding on an ice frost trail, and snowball throws.
    """

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="penguin")
        self.can_fly = False
        self.personality = CharacterPersonality(energy=0.72, curiosity=0.80, playfulness=0.90, sleepiness=0.40)
        self.memory = CharacterMemory(skin_id="penguin")
        self.behavior = CharacterBehavior("Penguin", personality=self.personality, memory=self.memory, can_fly=False)

        self.waddle = 0.0
        self.flipper_flap = 0.0
        self.is_sliding = False
        self.slide_time = 0.0
        self.snowballs: List[Dict[str, Any]] = []

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
            self.slide_time = time.time() + 2.0
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.vx = (dx / dist) * 16.0
            self.vy = (dy / dist) * 8.0
            self.facing_right = (dx >= 0)
            particle_mgr.burst_dust(self.x, self.y + 16, count=6)
            particle_mgr.burst_stars(self.x, self.y + 16, count=4, color=(0.85, 0.95, 1.0))
            audio_mgr.play("swoosh")
            self.memory.record_interaction("belly_slide")
            return True

        elif ability_name in ("snowball_toss", "snowball"):
            # Launch an authentic flying snowball!
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            dir_mult = 1.0 if self.facing_right else -1.0
            self.snowballs.append({
                "x": self.x + dir_mult * 14.0,
                "y": self.y - 8.0,
                "vx": (dx / dist) * 15.0,
                "vy": min(-4.0, (dy / dist) * 15.0 - 3.0),
                "radius": 5.5,
                "life": 1.4
            })
            particle_mgr.burst_stars(self.x + dir_mult * 14.0, self.y - 8.0, count=4, color=(0.92, 0.96, 1.0))
            audio_mgr.play("swoosh")
            self.memory.record_interaction("snowball_toss")
            return True

        elif ability_name in ("playful_waddle", "waddle", "celebrate"):
            self.waddle += 15.0
            self.flipper_flap += 20.0
            particle_mgr.burst_hearts(self.x, self.y - 16, count=3)
            audio_mgr.play("purr")
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
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)
        speed_mult = config_data.get("speed", 1.0)

        # Look direction
        if abs(cursor_x - self.x) > 6.0 and not self.is_sliding:
            self.facing_right = (cursor_x >= self.x)

        # Update flying snowballs
        for sb in self.snowballs:
            sb["x"] += sb["vx"]
            sb["y"] += sb["vy"]
            sb["vy"] += 0.35  # Gravity arc
            sb["life"] -= dt
            if random.random() < 0.4:
                particle_mgr.burst_dust(sb["x"], sb["y"], count=1, color=(0.92, 0.96, 1.0))
        self.snowballs = [sb for sb in self.snowballs if sb["life"] > 0]

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

        dx = cursor_x - self.x
        dy = cursor_y - self.y
        dist = math.hypot(dx, dy)

        if self.is_sliding:
            # High-speed ice glide
            self.vx *= 0.97
            self.vy *= 0.97
            if random.random() < 0.45:
                particle_mgr.burst_dust(self.x, self.y + 12, count=2, color=(0.88, 0.95, 1.0))
            if now > self.slide_time or (abs(self.vx) < 1.0 and abs(self.vy) < 1.0):
                self.is_sliding = False
        elif dist > 50.0 and config_data.get("cursor_follow", True):
            # Cute waddle follow toward cursor anywhere on desktop
            waddle_spd = min(7.5 * speed_mult, max(2.5, dist * 0.05))
            self.vx += ((dx / dist) * waddle_spd - self.vx) * 0.18
            self.vy += ((dy / dist) * waddle_spd - self.vy) * 0.18
            self.state = CharacterState.RUN if dist > 180.0 else CharacterState.WALK
            self.waddle += dt * 14.0
            self.flipper_flap += dt * 16.0
        elif self.state in (BehaviorState.RUN, BehaviorState.WALK):
            tx, ty = self.behavior.target_x, self.behavior.target_y
            tdx = tx - self.x
            tdy = ty - self.y
            tdist = math.hypot(tdx, tdy)
            if tdist > 15.0:
                spd = 6.5 * speed_mult if self.state == BehaviorState.RUN else 3.8 * speed_mult
                self.vx += ((tdx / tdist) * spd - self.vx) * 0.16
                self.vy += ((tdy / tdist) * spd - self.vy) * 0.16
                self.waddle += dt * 12.0
                self.flipper_flap += dt * 14.0
            else:
                self.vx *= 0.8
                self.vy *= 0.8
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.82
            self.vy *= 0.82
            self.waddle *= 0.85
            self.flipper_flap *= 0.85

        self.x += self.vx
        self.y += self.vy

        # Screen boundary clamp
        self.x = max(min_x + 45.0, min(min_x + screen_w - 45.0, self.x))
        self.y = max(min_y + 45.0, min(min_y + screen_h - 55.0, self.y))

        # Waddle tilt angle
        if not self.is_sliding:
            target_tilt = math.sin(self.waddle) * (0.22 if abs(self.vx) > 0.5 else 0.08)
            self.tilt += (target_tilt - self.tilt) * 0.25
        else:
            self.tilt = (0.75 if self.facing_right else -0.75)

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        # Draw active snowballs first
        for sb in self.snowballs:
            ctx.save()
            ctx.translate(sb["x"], sb["y"])
            # Frosty glowing core
            ctx.set_source_rgb(0.95, 0.98, 1.0)
            ctx.arc(0, 0, sb["radius"], 0, math.pi * 2)
            ctx.fill()
            ctx.set_source_rgba(0.7, 0.9, 1.0, 0.5)
            ctx.set_line_width(1.2)
            ctx.stroke()
            ctx.restore()

        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.rotate(self.tilt)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        if self.is_sliding:
            # -------------------------------------------------------------
            # BELLY SLIDING POSE (Tucked wings, feet kicked back)
            # -------------------------------------------------------------
            ctx.save()
            # Ice frost glide line underneath
            ctx.set_source_rgba(0.7, 0.92, 1.0, 0.6)
            ctx.set_line_width(3.0)
            ctx.move_to(-24, 16)
            ctx.line_to(22, 16)
            ctx.stroke()

            # Black body
            ctx.set_source_rgb(0.12, 0.12, 0.16)
            ctx.save()
            ctx.scale(1.35, 0.85)
            ctx.arc(0, 2, 15, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

            # White sliding belly
            ctx.set_source_rgb(0.96, 0.97, 1.0)
            ctx.save()
            ctx.scale(1.2, 0.7)
            ctx.arc(2, 6, 12, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

            # Feet tucked back
            ctx.set_source_rgb(1.0, 0.62, 0.1)
            ctx.arc(-18, 0, 4.5, 0, math.pi * 2)
            ctx.fill()

            # Streamlined head
            ctx.set_source_rgb(0.12, 0.12, 0.16)
            ctx.arc(14, -6, 9.5, 0, math.pi * 2)
            ctx.fill()
            # Beak pointing forward
            ctx.set_source_rgb(1.0, 0.6, 0.1)
            ctx.new_path()
            ctx.move_to(22, -8)
            ctx.line_to(30, -5)
            ctx.line_to(22, -3)
            ctx.close_path()
            ctx.fill()
            # Happy eye
            ctx.set_source_rgb(0.96, 0.97, 1.0)
            ctx.arc(16, -7, 2.5, 0, math.pi * 2)
            ctx.fill()
            ctx.set_source_rgb(0.1, 0.1, 0.15)
            ctx.arc(17, -7, 1.4, 0, math.pi * 2)
            ctx.fill()

            # Swept-back aerodynamic flippers
            ctx.set_source_rgb(0.12, 0.12, 0.16)
            ctx.new_path()
            ctx.move_to(4, -2)
            ctx.curve_to(-6, -12, -18, -10, -20, -4)
            ctx.curve_to(-14, 0, -4, 2, 4, -2)
            ctx.close_path()
            ctx.fill()

            ctx.restore()
            ctx.restore()
            return

        # -----------------------------------------------------------------
        # UPRIGHT WADDLE POSE
        # -----------------------------------------------------------------
        # 1. Alternating Stepping Feet
        ctx.save()
        ctx.set_source_rgb(1.0, 0.62, 0.1)
        foot_step_l = math.sin(self.waddle) * 4.0
        foot_step_r = -foot_step_l

        # Left foot
        ctx.save()
        ctx.translate(-7, 20 + foot_step_l)
        ctx.scale(1.25, 0.7)
        ctx.arc(0, 0, 5.0, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # Right foot
        ctx.save()
        ctx.translate(6, 20 + foot_step_r)
        ctx.scale(1.25, 0.7)
        ctx.arc(0, 0, 5.0, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()
        ctx.restore()

        # 2. Tuxedo Black Body & Head
        ctx.save()
        ctx.set_source_rgb(0.12, 0.12, 0.16)
        # Plump belly oval
        ctx.save()
        ctx.translate(0, 3)
        ctx.scale(1.05, 1.3)
        ctx.arc(0, 0, 15, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # Round head
        ctx.arc(0, -13, 11, 0, math.pi * 2)
        ctx.fill()

        # Dynamic Flippers flapping with waddle for balance
        flap_l = math.sin(self.flipper_flap) * 0.35
        flap_r = math.cos(self.flipper_flap) * 0.35

        # Left (back) flipper
        ctx.new_path()
        ctx.move_to(-12, -2)
        ctx.curve_to(-18 - flap_l * 8.0, 6, -17 - flap_l * 6.0, 16, -11, 12)
        ctx.close_path()
        ctx.fill()

        # Right (front) flipper
        ctx.new_path()
        ctx.move_to(12, -2)
        ctx.curve_to(18 + flap_r * 8.0, 6, 17 + flap_r * 6.0, 16, 11, 12)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # 3. Bright White Chest & Belly Bib
        ctx.save()
        ctx.set_source_rgb(0.96, 0.97, 1.0)
        ctx.save()
        ctx.translate(2, 5)
        ctx.scale(1.0, 1.2)
        ctx.arc(0, 0, 10.5, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # White eye mask patches
        ctx.arc(3.5, -14, 4.5, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # 4. Cute Face: Sparkly Eye, Triangular Beak, Rosy Cheeks
        ctx.save()
        # Large expressive dark eye
        ctx.set_source_rgb(0.1, 0.1, 0.15)
        ctx.arc(4.5, -14, 2.4, 0, math.pi * 2)
        ctx.fill()
        # White anime reflection highlights
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(5.2, -15, 0.9, 0, math.pi * 2)
        ctx.fill()
        ctx.arc(3.8, -13.2, 0.4, 0, math.pi * 2)
        ctx.fill()

        # Golden-Orange Triangular Beak
        ctx.set_source_rgb(1.0, 0.6, 0.1)
        ctx.new_path()
        ctx.move_to(7.5, -14.5)
        ctx.line_to(15.5, -12.5)
        ctx.line_to(7.5, -10.5)
        ctx.close_path()
        ctx.fill()

        # Soft blushing pink cheeks
        ctx.set_source_rgba(1.0, 0.45, 0.55, 0.45)
        ctx.arc(2.0, -9.0, 2.5, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        ctx.restore()
