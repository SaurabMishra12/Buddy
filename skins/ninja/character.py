"""Ninja desktop companion: agile shinobi dashes, multi-joint running kinematics,
spinning steel shurikens, shadow afterimages, and smoke bomb vanishings.
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


class NinjaCharacter(BaseCharacter):
    """Silent shadow shinobi companion with fluid anime running kinematics,
    articulated knees, flowing wind-reactive headband ribbons, and spinning shurikens.
    """

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="ninja")
        self.can_fly = False
        self.personality = CharacterPersonality(energy=0.88, curiosity=0.75, playfulness=0.50, sleepiness=0.15)
        self.memory = CharacterMemory(skin_id="ninja")
        self.behavior = CharacterBehavior("Ninja", personality=self.personality, memory=self.memory, can_fly=False)

        self.stride = 0.0
        self.headband_wave = 0.0
        self.arm_swing = 0.0
        self.shadow_clones: List[Dict[str, Any]] = []
        self.shurikens: List[Dict[str, Any]] = []
        self.is_vanishing = False
        self.vanish_timer = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("smoke_teleport", "smoke_bomb"):
            # Dense smoke screen and instant shadow replacement
            for _ in range(12):
                particle_mgr.smoke_puff(
                    self.x + random.uniform(-10, 10),
                    self.y + random.uniform(-10, 10),
                    count=2,
                    color=(0.18, 0.18, 0.22)
                )
            self.shadow_clones.append({"x": self.x, "y": self.y, "facing": self.facing_right, "alpha": 0.8})
            self.x = target_x
            self.y = target_y
            self.vx = 0.0
            self.vy = 0.0
            particle_mgr.burst_dust(self.x, self.y + 15, count=6)
            audio_mgr.play("swoosh")
            self.memory.record_interaction("smoke_teleport")
            return True

        elif ability_name in ("shuriken_strike", "shuriken"):
            # Launch 3 real spinning shurikens with metallic shine!
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            base_vx = (dx / dist) * 18.0
            base_vy = (dy / dist) * 18.0
            dir_mult = 1.0 if self.facing_right else -1.0

            for spread in (-0.25, 0.0, 0.25):
                cos_s = math.cos(spread)
                sin_s = math.sin(spread)
                svx = base_vx * cos_s - base_vy * sin_s
                svy = base_vx * sin_s + base_vy * cos_s
                self.shurikens.append({
                    "x": self.x + dir_mult * 14.0,
                    "y": self.y - 6.0,
                    "vx": svx,
                    "vy": svy,
                    "rot": random.uniform(0, math.pi),
                    "life": 1.2
                })
            particle_mgr.burst_stars(self.x + dir_mult * 14.0, self.y - 6.0, count=4, color=(0.85, 0.9, 1.0))
            audio_mgr.play("swoosh")
            self.memory.record_interaction("shuriken_strike")
            return True

        elif ability_name in ("shadow_dash", "dash"):
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.vx = (dx / dist) * 22.0
            self.vy = (dy / dist) * 12.0
            self.facing_right = (dx >= 0)
            self.shadow_clones.append({"x": self.x, "y": self.y, "facing": self.facing_right, "alpha": 0.7})
            particle_mgr.burst_dust(self.x, self.y + 18, count=5)
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
        self.anim_time += dt * 5.0
        self.headband_wave += dt * 9.0
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)
        speed_mult = config_data.get("speed", 1.0)

        # Facing direction
        if abs(cursor_x - self.x) > 8.0:
            self.facing_right = (cursor_x >= self.x)

        # Update active shurikens
        for sh in self.shurikens:
            sh["x"] += sh["vx"]
            sh["y"] += sh["vy"]
            sh["rot"] += dt * 35.0
            sh["life"] -= dt
            if random.random() < 0.3:
                particle_mgr.burst_sparks(sh["x"], sh["y"], count=1, color=(0.9, 0.95, 1.0), size=1.5)
        self.shurikens = [sh for sh in self.shurikens if sh["life"] > 0]

        # Fade shadow afterimages
        for cl in self.shadow_clones:
            cl["alpha"] -= dt * 2.5
        self.shadow_clones = [cl for cl in self.shadow_clones if cl["alpha"] > 0.05]

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

        # Locomotion & cursor chase
        dx = cursor_x - self.x
        dy = cursor_y - self.y
        dist = math.hypot(dx, dy)

        if dist > 55.0 and config_data.get("cursor_follow", True):
            # Agile shinobi run toward cursor
            run_spd = min(11.0 * speed_mult, max(3.5, dist * 0.065))
            self.vx += ((dx / dist) * run_spd - self.vx) * 0.22
            self.vy += ((dy / dist) * run_spd - self.vy) * 0.22
            self.state = CharacterState.RUN if dist > 180.0 else CharacterState.WALK
            self.stride += dt * (18.0 if self.state == CharacterState.RUN else 10.0)
            self.arm_swing += dt * 14.0
        elif self.state in (BehaviorState.RUN, BehaviorState.WALK):
            tx, ty = self.behavior.target_x, self.behavior.target_y
            tdx = tx - self.x
            tdy = ty - self.y
            tdist = math.hypot(tdx, tdy)
            if tdist > 18.0:
                spd = 8.5 * speed_mult if self.state == BehaviorState.RUN else 4.5 * speed_mult
                self.vx += ((tdx / tdist) * spd - self.vx) * 0.20
                self.vy += ((tdy / tdist) * spd - self.vy) * 0.20
                self.stride += dt * (16.0 if self.state == BehaviorState.RUN else 9.0)
                self.arm_swing += dt * 12.0
            else:
                self.vx *= 0.8
                self.vy *= 0.8
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.82
            self.vy *= 0.82
            self.stride *= 0.85
            self.arm_swing *= 0.85

        self.x += self.vx
        self.y += self.vy

        # Screen clamp
        self.x = max(min_x + 45.0, min(min_x + screen_w - 45.0, self.x))
        self.y = max(min_y + 45.0, min(min_y + screen_h - 55.0, self.y))

        # Dynamic forward running tilt
        target_tilt = (self.vx / 12.0) * 0.22
        self.tilt += (target_tilt - self.tilt) * 0.20

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        # Draw active flying shurikens first
        for sh in self.shurikens:
            ctx.save()
            ctx.translate(sh["x"], sh["y"])
            ctx.rotate(sh["rot"])
            # 4-point steel shuriken
            ctx.set_source_rgb(0.85, 0.88, 0.94)
            for angle in (0.0, math.pi * 0.5, math.pi, math.pi * 1.5):
                ctx.save()
                ctx.rotate(angle)
                ctx.new_path()
                ctx.move_to(0, -3)
                ctx.line_to(9, 0)
                ctx.line_to(0, 3)
                ctx.close_path()
                ctx.fill()
                ctx.restore()
            # Central brass ring
            ctx.set_source_rgb(0.3, 0.3, 0.35)
            ctx.arc(0, 0, 2.5, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

        # Render shadow clones
        for cl in self.shadow_clones:
            ctx.save()
            ctx.translate(cl["x"], cl["y"])
            if not cl["facing"]:
                ctx.scale(-1.0, 1.0)
            ctx.set_source_rgba(0.1, 0.1, 0.15, cl["alpha"])
            ctx.arc(0, -8, 16, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

        # Main Ninja body
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.rotate(self.tilt)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Articulated Legs (Shinobi Hakama Trousers with Tabi)
        # Running leg phases with joint bending
        speed = abs(self.vx) + abs(self.vy)
        is_moving = speed > 0.8

        left_phase = self.stride
        right_phase = self.stride + math.pi

        for is_left, phase in ((True, left_phase), (False, right_phase)):
            hip_x = -5.0 if is_left else 3.0
            hip_y = 10.0

            if is_moving:
                thigh_angle = math.sin(phase) * 0.65
                knee_angle = thigh_angle + max(0.0, math.cos(phase) * 0.7)
            else:
                thigh_angle = -0.1 if is_left else 0.1
                knee_angle = 0.0

            # Upper leg (Thigh)
            knee_x = hip_x + math.sin(thigh_angle) * 9.0
            knee_y = hip_y + math.cos(thigh_angle) * 9.0

            # Lower leg (Calf + Foot)
            foot_x = knee_x + math.sin(knee_angle) * 9.0
            foot_y = knee_y + math.cos(knee_angle) * 9.0

            ctx.save()
            ctx.set_source_rgb(0.12, 0.12, 0.14)
            ctx.set_line_width(5.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(hip_x, hip_y)
            ctx.line_to(knee_x, knee_y)
            ctx.line_to(foot_x, foot_y)
            ctx.stroke()

            # White Tabi foot wrap
            ctx.set_source_rgb(0.92, 0.92, 0.95)
            ctx.set_line_width(4.5)
            ctx.move_to(knee_x + (foot_x - knee_x) * 0.6, knee_y + (foot_y - knee_y) * 0.6)
            ctx.line_to(foot_x + 3.0, foot_y)
            ctx.stroke()
            ctx.restore()

        # 2. Torso (Midnight Black Gi)
        ctx.save()
        ctx.set_source_rgb(0.14, 0.14, 0.16)
        ctx.new_path()
        ctx.move_to(-12, -9)
        ctx.line_to(12, -9)
        ctx.line_to(9, 12)
        ctx.line_to(-9, 12)
        ctx.close_path()
        ctx.fill()

        # Crimson Red Sash Belt with Knotted Tassels
        ctx.set_source_rgb(0.85, 0.15, 0.15)
        ctx.rectangle(-10, 7, 20, 4)
        ctx.fill()
        # Hanging knot sash
        ctx.set_line_width(2.2)
        ctx.move_to(-2, 11)
        ctx.line_to(-4, 19 + math.sin(self.headband_wave * 0.5) * 2.0)
        ctx.stroke()

        # Katana Scabbard on Back (Diagonal over shoulder)
        ctx.set_source_rgb(0.22, 0.22, 0.25)
        ctx.set_line_width(3.0)
        ctx.move_to(-18, 12)
        ctx.line_to(14, -20)
        ctx.stroke()
        # Katana Tsuka (Hilt with Gold Tsuba)
        ctx.set_source_rgb(0.95, 0.8, 0.2)
        ctx.arc(14, -20, 2.5, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgb(0.85, 0.15, 0.15)  # Red cord wrap
        ctx.set_line_width(2.5)
        ctx.move_to(14, -20)
        ctx.line_to(19, -25)
        ctx.stroke()
        ctx.restore()

        # 3. Articulated Arms
        ctx.save()
        ctx.set_source_rgb(0.13, 0.13, 0.15)
        ctx.set_line_width(4.5)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        if is_moving:
            # Anime ninja running pose: arms swept aerodynamic back or pumping
            arm_swing_l = math.sin(self.arm_swing) * 0.6
            ctx.move_to(-7, -4)
            ctx.line_to(-16, 4 - arm_swing_l * 6.0)
            ctx.stroke()
            ctx.move_to(7, -4)
            ctx.line_to(14, 2 + arm_swing_l * 6.0)
            ctx.stroke()
        else:
            # Ninja ready stance: hands poised forward
            ctx.move_to(-7, -4)
            ctx.line_to(-4, 4)
            ctx.stroke()
            ctx.move_to(7, -4)
            ctx.line_to(4, 4)
            ctx.stroke()
        ctx.restore()

        # 4. Masked Shinobi Head
        ctx.save()
        # Black hood
        ctx.set_source_rgb(0.12, 0.12, 0.15)
        ctx.arc(0, -18, 12, 0, math.pi * 2)
        ctx.fill()

        # Eye-slit cutout (pale skin)
        ctx.set_source_rgb(0.95, 0.82, 0.72)
        ctx.rectangle(-7, -22, 14, 6)
        ctx.fill()

        # Intense focused ninja eye
        ctx.set_source_rgb(0.08, 0.08, 0.1)
        ctx.arc(3.5, -19, 1.8, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(4.0, -19.5, 0.6, 0, math.pi * 2)
        ctx.fill()

        # Crimson Red Forehead Band
        ctx.set_source_rgb(0.88, 0.12, 0.12)
        ctx.rectangle(-12, -26, 24, 3.5)
        ctx.fill()
        # Steel Shinobi Emblem Plate
        ctx.set_source_rgb(0.82, 0.85, 0.9)
        ctx.rectangle(-4, -26, 8, 3.5)
        ctx.fill()

        # Flowing ribbons trailing in the wind with wave mechanics
        wind_offset = abs(self.vx) * 0.8
        wave1 = math.sin(self.headband_wave) * (4.0 + wind_offset * 0.3)
        wave2 = math.cos(self.headband_wave) * (3.5 + wind_offset * 0.3)

        ctx.set_source_rgb(0.88, 0.12, 0.12)
        ctx.set_line_width(2.6)
        ctx.new_path()
        ctx.move_to(-11, -25)
        ctx.curve_to(-18 - wind_offset * 0.5, -25 + wave1, -24 - wind_offset, -21 + wave2, -32 - wind_offset * 1.2, -23 + wave1)
        ctx.stroke()
        ctx.new_path()
        ctx.move_to(-11, -24)
        ctx.curve_to(-17 - wind_offset * 0.5, -23 + wave2, -23 - wind_offset, -19 + wave1, -29 - wind_offset * 1.1, -20 + wave2)
        ctx.stroke()
        ctx.restore()

        ctx.restore()
