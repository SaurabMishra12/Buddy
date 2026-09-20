"""Space Robot desktop companion: dual hover thrusters with banking exhaust,
sweeping holographic scanning beam, wireframe hologram projection, and reactive emotive visor.
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


class SpaceRobotCharacter(BaseCharacter):
    """Futuristic companion robot with articulated hover thrusters,
    wide sweeping holographic scanning beam, and emotive LED visor.
    """

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="space_robot")
        self.can_fly = True
        self.is_airborne = True
        self.personality = CharacterPersonality(energy=0.86, curiosity=0.92, playfulness=0.55, sleepiness=0.12)
        self.memory = CharacterMemory(skin_id="space_robot")
        self.behavior = CharacterBehavior("Space Robot", personality=self.personality, memory=self.memory, can_fly=True)

        self.hover_y = 0.0
        self.scanning_beam_timer = 0.0
        self.hologram_alpha = 0.0
        self.hologram_rot = 0.0
        self.eye_blink = 0.0
        self.arm_motion = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("scanning_beam", "scan_beam"):
            self.scanning_beam_timer = time.time() + 1.8
            particle_mgr.energy_orbs(self.x, self.y, count=3, color=(0.1, 0.9, 1.0))
            audio_mgr.play("laser")
            self.memory.record_interaction("scanning_beam")
            return True

        elif ability_name == "jet_boost":
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.vx = (dx / dist) * 18.0
            self.vy = (dy / dist) * 18.0
            self.state = CharacterState.FLY
            particle_mgr.shockwave(self.x, self.y, max_radius=70.0, color=(0.2, 0.9, 1.0))
            for _ in range(8):
                particle_mgr.burst_sparks(self.x, self.y + 16, count=3, color=(0.1, 0.95, 1.0))
            audio_mgr.play("jet")
            self.memory.record_interaction("jet_boost")
            return True

        elif ability_name in ("hologram", "celebrate"):
            self.hologram_alpha = 1.0
            particle_mgr.burst_stars(self.x, self.y - 32, count=12, color=(0.25, 0.92, 1.0))
            audio_mgr.play("magic")
            self.memory.record_interaction("hologram")
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
        self.hologram_rot += dt * 2.5
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)
        speed_mult = config_data.get("speed", 1.0)

        # Decay hologram
        if self.hologram_alpha > 0.0:
            self.hologram_alpha = max(0.0, self.hologram_alpha - dt * 0.6)

        # Look direction
        if abs(cursor_x - self.x) > 6.0:
            self.facing_right = (cursor_x >= self.x)

        # Eye blink cycle
        self.eye_blink += dt
        if self.eye_blink > 4.5:
            self.eye_blink = 0.0

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

        # Jet hover physics
        self.hover_y = math.sin(self.anim_time * 1.8) * 5.0

        dx = cursor_x - self.x
        dy = cursor_y - self.y
        dist = math.hypot(dx, dy)

        if dist > 50.0 and config_data.get("cursor_follow", True):
            fly_spd = min(9.0 * speed_mult, max(2.5, dist * 0.065))
            self.vx += ((dx / dist) * fly_spd - self.vx) * 0.18
            self.vy += ((dy / dist) * fly_spd - self.vy) * 0.18
            self.state = CharacterState.FLY
        elif self.state in (BehaviorState.FLY, BehaviorState.WALK):
            tx, ty = self.behavior.target_x, self.behavior.target_y
            tdx = tx - self.x
            tdy = ty - self.y
            tdist = math.hypot(tdx, tdy)
            if tdist > 15.0:
                spd = 6.8 * speed_mult
                self.vx += ((tdx / tdist) * spd - self.vx) * 0.16
                self.vy += ((tdy / tdist) * spd - self.vy) * 0.16
            else:
                self.vx *= 0.8
                self.vy *= 0.8
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.82
            self.vy *= 0.82

        self.x += self.vx
        self.y += self.vy

        # Screen clamp
        self.x = max(min_x + 45.0, min(min_x + screen_w - 45.0, self.x))
        self.y = max(min_y + 45.0, min(min_y + screen_h - 55.0, self.y))

        # Dynamic banking tilt into turns
        target_tilt = (self.vx / 12.0) * 0.24
        self.tilt += (target_tilt - self.tilt) * 0.22

        # Dual thruster spark particles
        if random.random() < 0.40:
            particle_mgr.burst_sparks(
                self.x - (6 if self.facing_right else -6),
                self.y + 20,
                count=1,
                color=(0.15, 0.90, 1.0),
                size=2.0
            )

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        ctx.save()
        ctx.translate(self.x, self.y + self.hover_y)
        ctx.rotate(self.tilt)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # -------------------------------------------------------------
        # 1. Sweeping Holographic Scanning Beam
        # -------------------------------------------------------------
        if time.time() < self.scanning_beam_timer:
            ctx.save()
            scan_sweep = math.sin(self.anim_time * 6.0) * 0.35
            ctx.rotate(scan_sweep)
            pat_scan = cairo.LinearGradient(10, -5, 75, 0)
            pat_scan.add_color_stop_rgba(0.0, 0.2, 0.9, 1.0, 0.7)
            pat_scan.add_color_stop_rgba(0.5, 0.1, 0.8, 1.0, 0.25)
            pat_scan.add_color_stop_rgba(1.0, 0.05, 0.7, 1.0, 0.0)
            ctx.set_source(pat_scan)
            ctx.new_path()
            ctx.move_to(8, -6)
            ctx.line_to(75, -28)
            ctx.line_to(75, 20)
            ctx.close_path()
            ctx.fill()

            # Concentric target arcs
            ctx.set_source_rgba(0.2, 0.95, 1.0, 0.6)
            ctx.set_line_width(1.5)
            ctx.arc(8, -6, 35, -0.3, 0.3)
            ctx.stroke()
            ctx.arc(8, -6, 58, -0.35, 0.35)
            ctx.stroke()
            ctx.restore()

        # -------------------------------------------------------------
        # 2. Wireframe Hologram Projection
        # -------------------------------------------------------------
        if self.hologram_alpha > 0.05:
            ctx.save()
            ctx.translate(0, -42)
            ctx.rotate(self.hologram_rot)
            ctx.set_source_rgba(0.2, 0.95, 1.0, self.hologram_alpha * 0.85)
            ctx.set_line_width(1.4)
            # Rotating planetary ring and core
            ctx.arc(0, 0, 13, 0, math.pi * 2)
            ctx.stroke()
            ctx.save()
            ctx.scale(1.0, 0.35)
            ctx.arc(0, 0, 20, 0, math.pi * 2)
            ctx.stroke()
            ctx.restore()
            ctx.restore()

        # -------------------------------------------------------------
        # 3. Dual Rocket Boot Thrusters (Articulated Exhaust Flames)
        # -------------------------------------------------------------
        speed = math.hypot(self.vx, self.vy)
        flame_len = 9.0 + speed * 1.5 + random.uniform(0, 4)

        for bx in (-7, 7):
            ctx.save()
            ctx.translate(bx, 15)
            # Boot nozzle (Dark titanium)
            ctx.set_source_rgb(0.22, 0.25, 0.30)
            ctx.rectangle(-4, 0, 8, 4)
            ctx.fill()

            # Cyan plasma plume
            pat_flame = cairo.LinearGradient(0, 4, 0, 4 + flame_len)
            pat_flame.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.95)
            pat_flame.add_color_stop_rgba(0.3, 0.2, 0.9, 1.0, 0.9)
            pat_flame.add_color_stop_rgba(1.0, 0.05, 0.5, 1.0, 0.0)
            ctx.set_source(pat_flame)
            ctx.new_path()
            ctx.move_to(-3.5, 4)
            ctx.line_to(0, 4 + flame_len)
            ctx.line_to(3.5, 4)
            ctx.close_path()
            ctx.fill()
            ctx.restore()

        # -------------------------------------------------------------
        # 4. Futuristic Robotic Chassis (Aerodynamic Capsule)
        # -------------------------------------------------------------
        ctx.save()
        # White ceramic composite armor
        ctx.set_source_rgb(0.92, 0.94, 0.98)
        ctx.new_path()
        ctx.arc(0, -6, 15, math.pi, 0)
        ctx.line_to(15, 12)
        ctx.arc(0, 12, 15, 0, math.pi)
        ctx.line_to(-15, -6)
        ctx.close_path()
        ctx.fill()

        # Metallic edge bevel
        ctx.set_source_rgb(0.78, 0.82, 0.88)
        ctx.set_line_width(1.5)
        ctx.stroke()

        # Glowing Cyan Circuit Traces
        ctx.set_source_rgb(0.1, 0.85, 1.0)
        ctx.set_line_width(1.8)
        ctx.move_to(-11, 4)
        ctx.line_to(-6, 8)
        ctx.line_to(6, 8)
        ctx.line_to(11, 4)
        ctx.stroke()
        ctx.restore()

        # -------------------------------------------------------------
        # 5. Articulated Robotic Arms
        # -------------------------------------------------------------
        ctx.save()
        ctx.set_source_rgb(0.25, 0.28, 0.35)  # Dark titanium joints
        ctx.set_line_width(3.2)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        arm_wave = math.sin(self.anim_time * 3.0) * 4.0

        # Left (back) arm
        ctx.move_to(-13, 0)
        ctx.line_to(-19, 6 + arm_wave)
        ctx.stroke()
        # Left claw
        ctx.set_source_rgb(0.1, 0.85, 1.0)
        ctx.arc(-19, 6 + arm_wave, 2.0, 0, math.pi * 2)
        ctx.fill()

        # Right (front) arm pointing/waving
        ctx.set_source_rgb(0.25, 0.28, 0.35)
        ctx.move_to(13, 0)
        ctx.line_to(19, 4 - arm_wave)
        ctx.stroke()
        # Right claw
        ctx.set_source_rgb(0.1, 0.85, 1.0)
        ctx.arc(19, 4 - arm_wave, 2.0, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 6. Visor Display & Emotive LED Eyes
        # -------------------------------------------------------------
        ctx.save()
        # Tinted obsidian glass visor
        ctx.set_source_rgb(0.08, 0.1, 0.14)
        ctx.new_path()
        ctx.arc(0, -7, 10, math.pi, 0)
        ctx.arc(0, -1, 10, 0, math.pi)
        ctx.close_path()
        ctx.fill()

        # LED Eyes based on state & blink
        ctx.set_source_rgb(0.15, 0.95, 1.0)  # Bright cyan LED
        ctx.set_line_width(2.0)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)

        if self.eye_blink > 4.2:
            # Blink line: - -
            ctx.move_to(-6, -4)
            ctx.line_to(-2, -4)
            ctx.stroke()
            ctx.move_to(2, -4)
            ctx.line_to(6, -4)
            ctx.stroke()
        elif self.state == CharacterState.FLY:
            # Focused chevron eyes: > <
            ctx.new_path()
            ctx.move_to(-6, -6)
            ctx.line_to(-3, -4)
            ctx.line_to(-6, -2)
            ctx.stroke()
            ctx.new_path()
            ctx.move_to(6, -6)
            ctx.line_to(3, -4)
            ctx.line_to(6, -2)
            ctx.stroke()
        else:
            # Happy smiling visor eyes: ^ ^
            ctx.new_path()
            ctx.arc(-4, -4, 2.2, math.pi * 1.1, math.pi * 1.9)
            ctx.stroke()
            ctx.new_path()
            ctx.arc(4, -4, 2.2, math.pi * 1.1, math.pi * 1.9)
            ctx.stroke()

        # Little top antenna with blinking LED
        ctx.set_source_rgb(0.3, 0.35, 0.4)
        ctx.set_line_width(2.0)
        ctx.move_to(0, -21)
        ctx.line_to(0, -27)
        ctx.stroke()
        # Antenna glowing tip
        ctx.set_source_rgb(0.1, 0.95, 1.0)
        ctx.arc(0, -28, 2.5, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        ctx.restore()
