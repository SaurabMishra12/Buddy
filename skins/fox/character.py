"""Fox desktop companion: quadruped trotting kinematics, bushy tail physics,
acrobatic pounce leaps, and alert twitching ears.
"""

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
    """Swift clever woodland red fox companion with quadruped running kinematics,
    athletic arched pounces, and a lush expressive bushy tail.
    """

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="fox")
        self.can_fly = False
        self.personality = CharacterPersonality(energy=0.90, curiosity=0.88, playfulness=0.85, sleepiness=0.20)
        self.memory = CharacterMemory(skin_id="fox")
        self.behavior = CharacterBehavior("Fox", personality=self.personality, memory=self.memory, can_fly=False)

        self.tail_wave = 0.0
        self.ear_twitch = 0.0
        self.trot_stride = 0.0
        self.is_pouncing = False
        self.pounce_end_time = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("pounce_jump", "pounce"):
            self.is_pouncing = True
            self.pounce_end_time = time.time() + 1.2
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            dir_mult = 1.0 if dx >= 0 else -1.0
            self.vx = dir_mult * min(15.0, max(6.0, abs(dx) * 0.12))
            self.vy = min(-8.0, -13.0 + dy * 0.04)
            self.state = CharacterState.JUMP
            self.facing_right = (dx >= 0)
            particle_mgr.burst_dust(self.x, self.y + 16, count=6)
            particle_mgr.burst_hearts(self.x, self.y - 14, count=3)
            audio_mgr.play("bark")
            self.memory.record_interaction("pounce_jump")
            return True

        elif ability_name in ("dash_sprint", "dash"):
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.vx = (dx / dist) * 18.0
            self.vy = (dy / dist) * 10.0
            self.facing_right = (dx >= 0)
            particle_mgr.burst_dust(self.x, self.y + 16, count=5)
            audio_mgr.play("bark")
            self.memory.record_interaction("dash_sprint")
            return True

        elif ability_name in ("tail_flick", "wag", "celebrate"):
            self.tail_wave += 18.0
            particle_mgr.burst_hearts(self.x, self.y - 14, count=4)
            audio_mgr.play("purr")
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
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)
        speed_mult = config_data.get("speed", 1.0)

        # Look direction
        if abs(cursor_x - self.x) > 6.0:
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

        dx = cursor_x - self.x
        dy = cursor_y - self.y
        dist = math.hypot(dx, dy)

        if self.is_pouncing:
            self.vy += 0.65  # Pounce ballistic gravity
            if now >= self.pounce_end_time or (self.vy > 0 and self.y >= min_y + screen_h - 60.0):
                self.is_pouncing = False
                particle_mgr.burst_dust(self.x, self.y + 16, count=4)
        elif dist > 55.0 and config_data.get("cursor_follow", True):
            # Smooth quadruped trot toward cursor
            trot_spd = min(9.5 * speed_mult, max(3.0, dist * 0.065))
            self.vx += ((dx / dist) * trot_spd - self.vx) * 0.20
            self.vy += ((dy / dist) * trot_spd - self.vy) * 0.20
            self.state = CharacterState.RUN if dist > 190.0 else CharacterState.WALK
            self.trot_stride += dt * (18.0 if self.state == CharacterState.RUN else 11.0)
            if random.random() < 0.2:
                particle_mgr.burst_dust(self.x - (8 if self.facing_right else -8), self.y + 16, count=1)
        elif self.state in (BehaviorState.RUN, BehaviorState.WALK):
            tx, ty = self.behavior.target_x, self.behavior.target_y
            tdx = tx - self.x
            tdy = ty - self.y
            tdist = math.hypot(tdx, tdy)
            if tdist > 16.0:
                spd = 8.5 * speed_mult if self.state == BehaviorState.RUN else 4.5 * speed_mult
                self.vx += ((tdx / tdist) * spd - self.vx) * 0.18
                self.vy += ((tdy / tdist) * spd - self.vy) * 0.18
                self.trot_stride += dt * (16.0 if self.state == BehaviorState.RUN else 10.0)
            else:
                self.vx *= 0.8
                self.vy *= 0.8
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.82
            self.vy *= 0.82
            self.trot_stride *= 0.85

        self.x += self.vx
        self.y += self.vy

        # Screen boundary clamp
        self.x = max(min_x + 45.0, min(min_x + screen_w - 45.0, self.x))
        self.y = max(min_y + 45.0, min(min_y + screen_h - 55.0, self.y))

        # Dynamic body tilt (forward running lean or pounce tilt)
        if self.is_pouncing:
            target_tilt = -0.35 if self.vy < 0 else 0.25
        else:
            target_tilt = (self.vx / 14.0) * 0.18
        self.tilt += (target_tilt - self.tilt) * 0.22

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.rotate(self.tilt)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        speed = math.hypot(self.vx, self.vy)
        is_moving = speed > 0.6 or self.is_pouncing
        stride = self.trot_stride

        # -------------------------------------------------------------
        # 1. 4 Articulated Quadruped Legs (Trotting Phase Pairs)
        # -------------------------------------------------------------
        # Diagonal trotting pairs: (Front-Left & Rear-Right), (Front-Right & Rear-Left)
        phase_FL = stride
        phase_RR = stride
        phase_FR = stride + math.pi
        phase_RL = stride + math.pi

        legs = [
            # is_front, is_left, x_offset, phase
            (False, True, -10.0, phase_RL),   # Rear Left (far)
            (True, True, 6.0, phase_FL),      # Front Left (far)
            (False, False, -7.0, phase_RR),   # Rear Right (near)
            (True, False, 9.0, phase_FR),     # Front Right (near)
        ]

        for is_front, is_far, leg_x, phase in legs:
            ctx.save()
            # Far legs are slightly darker for depth
            if is_far:
                ctx.set_source_rgb(0.78, 0.32, 0.10)
            else:
                ctx.set_source_rgb(0.94, 0.40, 0.12)

            if self.is_pouncing:
                # Paws extended forward during pounce
                leg_angle = -0.6 if is_front else 0.5
            elif is_moving:
                leg_angle = math.sin(phase) * 0.55
            else:
                leg_angle = 0.05 if is_front else -0.05

            knee_x = leg_x + math.sin(leg_angle) * 7.0
            knee_y = 10.0 + math.cos(leg_angle) * 7.0
            foot_x = knee_x + math.sin(leg_angle * 0.6) * 7.0
            foot_y = knee_y + math.cos(leg_angle * 0.6) * 7.0

            ctx.set_line_width(4.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(leg_x, 4.0)
            ctx.line_to(knee_x, knee_y)
            ctx.stroke()

            # Dark black-brown fox sock paw
            ctx.set_source_rgb(0.18, 0.15, 0.15)
            ctx.set_line_width(4.5)
            ctx.move_to(knee_x, knee_y)
            ctx.line_to(foot_x, foot_y)
            ctx.stroke()
            ctx.restore()

        # -------------------------------------------------------------
        # 2. Lush Bushy Tail with White Tip
        # -------------------------------------------------------------
        tail_s = math.sin(self.tail_wave) * (5.0 + speed * 0.6)
        tail_wind = -self.vx * 0.6

        ctx.save()
        # Vibrant red-orange tail base
        ctx.set_source_rgb(0.92, 0.38, 0.12)
        ctx.new_path()
        ctx.move_to(-12, 4)
        ctx.curve_to(-24 + tail_wind * 0.5, 0, -32 + tail_wind, -10 + tail_s, -26 + tail_wind, -22 + tail_s)
        ctx.curve_to(-16 + tail_wind * 0.5, -12, -12, 0, -8, 2)
        ctx.close_path()
        ctx.fill()

        # White fluffy tail tip
        ctx.set_source_rgb(0.98, 0.98, 1.0)
        ctx.new_path()
        ctx.move_to(-27 + tail_wind, -16 + tail_s)
        ctx.curve_to(-33 + tail_wind, -10 + tail_s, -26 + tail_wind, -22 + tail_s, -22 + tail_wind, -18 + tail_s)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 3. Slender Aerodynamic Torso
        # -------------------------------------------------------------
        ctx.save()
        ctx.set_source_rgb(0.94, 0.40, 0.12)
        ctx.save()
        ctx.translate(0, 4)
        ctx.scale(1.25, 0.9)
        ctx.arc(0, 0, 13.5, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # White chest ruff / bib
        ctx.set_source_rgb(0.98, 0.98, 1.0)
        ctx.new_path()
        ctx.move_to(4, -3)
        ctx.curve_to(12, 0, 11, 10, 4, 13)
        ctx.curve_to(-1, 10, -2, 1, 4, -3)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 4. Sharp Clever Fox Head, Muzzle & Ears
        # -------------------------------------------------------------
        ctx.save()
        # Head base
        ctx.set_source_rgb(0.94, 0.40, 0.12)
        ctx.arc(6, -8, 10.5, 0, math.pi * 2)
        ctx.fill()

        # Tapered muzzle & black nose
        ctx.new_path()
        ctx.move_to(10, -10)
        ctx.line_to(21, -6)
        ctx.line_to(10, -2)
        ctx.close_path()
        ctx.fill()

        # White cheek fluff ruffs
        ctx.set_source_rgb(0.98, 0.98, 1.0)
        ctx.new_path()
        ctx.move_to(6, -4)
        ctx.curve_to(13, -2, 17, -5, 17, -6)
        ctx.line_to(11, 0)
        ctx.close_path()
        ctx.fill()

        # Jet black button nose
        ctx.set_source_rgb(0.1, 0.1, 0.1)
        ctx.arc(21, -6, 1.8, 0, math.pi * 2)
        ctx.fill()

        # Amber almond-shaped fox eye
        ctx.set_source_rgb(0.2, 0.12, 0.05)
        ctx.arc(10.5, -9.5, 2.0, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgb(1.0, 0.8, 0.2)  # Amber iris
        ctx.arc(10.8, -9.5, 1.2, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgb(1.0, 1.0, 1.0)  # Reflection
        ctx.arc(11.2, -10.0, 0.6, 0, math.pi * 2)
        ctx.fill()

        # Triangular pointed ears (twitching with wind/sound)
        ear_twitch = math.sin(self.anim_time * 6.0) * 0.1 if is_moving else 0.0
        ctx.save()
        ctx.translate(2, -15)
        ctx.rotate(ear_twitch)

        # Black outer ear tips
        ctx.set_source_rgb(0.18, 0.15, 0.15)
        ctx.new_path()
        ctx.move_to(-3, 0)
        ctx.line_to(1, -12)
        ctx.line_to(7, 0)
        ctx.close_path()
        ctx.fill()

        # White inner ear fur
        ctx.set_source_rgb(0.98, 0.98, 1.0)
        ctx.new_path()
        ctx.move_to(-1, 0)
        ctx.line_to(1, -8)
        ctx.line_to(5, 0)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        ctx.restore()
        ctx.restore()
