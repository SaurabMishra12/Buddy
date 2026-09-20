"""Space Robot desktop companion: thruster flight, hologram scans, and LED eye expressions."""

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
    """Futuristic companion robot with hover thrusters, scanning beam, and emotes."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="space_robot")
        self.can_fly = True
        self.is_airborne = True
        self.personality = CharacterPersonality(energy=0.85, curiosity=0.90, playfulness=0.45, sleepiness=0.15)
        self.memory = CharacterMemory(skin_id="space_robot")
        self.behavior = CharacterBehavior("Space Robot", personality=self.personality, memory=self.memory, can_fly=True)

        self.hover_y = 0.0
        self.scanning_beam_timer = 0.0
        self.hologram_alpha = 0.0
        self.eye_blink = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name == "jet_boost":
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.vx = (dx / dist) * 16.0
            self.vy = (dy / dist) * 16.0
            self.state = CharacterState.FLY
            particle_mgr.shockwave(self.x, self.y, max_radius=65.0, color=(0.2, 0.85, 1.0))
            for _ in range(8):
                particle_mgr.burst_sparks(self.x, self.y + 16, count=2, color=(0.1, 0.9, 1.0))
            audio_mgr.play("jet")
            self.memory.record_interaction("jet_boost")
            return True

        elif ability_name in ("scanning_beam", "scan_beam"):
            self.scanning_beam_timer = time.time() + 1.4
            particle_mgr.energy_orbs(self.x, self.y, count=2, color=(0.1, 0.9, 1.0))
            audio_mgr.play("laser")
            self.memory.record_interaction("scanning_beam")
            return True

        elif ability_name == "hologram":
            self.hologram_alpha = 1.0
            particle_mgr.burst_stars(self.x, self.y - 30, count=10, color=(0.3, 0.9, 1.0))
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
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)

        # Decay visual FX
        if self.hologram_alpha > 0.0:
            self.hologram_alpha = max(0.0, self.hologram_alpha - dt * 0.7)

        # Facing
        if abs(cursor_x - self.x) > 6.0:
            self.facing_right = (cursor_x >= self.x)

        # Eye blink cycle
        self.eye_blink += dt
        if self.eye_blink > 4.0:
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

        if self.state in (BehaviorState.FLY, BehaviorState.WALK):
            tx, ty = self.behavior.target_x, self.behavior.target_y
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            if dist > 16.0:
                self.vx += ((dx / dist) * 5.5 - self.vx) * 0.12
                self.vy += ((dy / dist) * 5.5 - self.vy) * 0.12
            else:
                self.vx *= 0.85
                self.vy *= 0.85
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.82
            self.vy *= 0.82

        self.x += self.vx
        self.y += self.vy

        # Bounds clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 70.0, self.y))

        # Boot thruster exhaust particles
        if random.random() < 0.35:
            particle_mgr.burst_sparks(self.x, self.y + 20, count=1, color=(0.1, 0.85, 1.0), size=1.8)

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        ctx.save()
        ctx.translate(self.x, self.y + self.hover_y)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Scanning Beam Effect
        if time.time() < self.scanning_beam_timer:
            ctx.save()
            ctx.set_source_rgba(0.1, 0.9, 1.0, 0.35)
            ctx.new_path()
            ctx.move_to(8, -8)
            ctx.line_to(65, -35)
            ctx.line_to(65, 20)
            ctx.close_path()
            ctx.fill()
            ctx.restore()

        # 2. Hologram Projection
        if self.hologram_alpha > 0.05:
            ctx.save()
            ctx.translate(0, -42)
            ctx.set_source_rgba(0.2, 0.95, 1.0, self.hologram_alpha * 0.8)
            ctx.set_line_width(1.5)
            ctx.arc(0, 0, 14, 0, math.pi * 2)
            ctx.stroke()
            # Mini rotating wireframe globe
            ctx.arc(0, 0, 7, 0, math.pi * 2)
            ctx.stroke()
            ctx.restore()

        # 3. Thruster Flame
        ctx.save()
        thruster_flame_h = 10.0 + random.uniform(0, 4)
        ctx.set_source_rgba(0.1, 0.85, 1.0, 0.8)
        ctx.new_path()
        ctx.move_to(-6, 16)
        ctx.line_to(0, 16 + thruster_flame_h)
        ctx.line_to(6, 16)
        ctx.close_path()
        ctx.fill()
        # Flame white core
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.9)
        ctx.new_path()
        ctx.move_to(-3, 16)
        ctx.line_to(0, 16 + thruster_flame_h * 0.5)
        ctx.line_to(3, 16)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # 4. Robot Chassis / Body (Futuristic Curved Capsule)
        ctx.save()
        # White ceramic armor
        ctx.set_source_rgb(0.92, 0.94, 0.98)
        ctx.new_path()
        ctx.arc(0, -6, 15, math.pi, 0)
        ctx.line_to(15, 12)
        ctx.arc(0, 12, 15, 0, math.pi)
        ctx.line_to(-15, -6)
        ctx.close_path()
        ctx.fill()

        # Cyan tech accents
        ctx.set_source_rgb(0.1, 0.8, 0.95)
        ctx.set_line_width(2.0)
        ctx.stroke()
        ctx.restore()

        # 5. Visor Display (Dark Glass with Cyan LED Eyes)
        ctx.save()
        ctx.set_source_rgb(0.08, 0.1, 0.15)  # Dark glass visor
        ctx.new_path()
        ctx.arc(0, -7, 10, math.pi, 0)
        ctx.arc(0, -1, 10, 0, math.pi)
        ctx.close_path()
        ctx.fill()

        # Cyan LED Eyes (Blinking animation)
        if self.eye_blink < 3.8:
            ctx.set_source_rgb(0.0, 0.95, 1.0)
            # Left eye
            ctx.arc(-4, -4, 2.4, 0, math.pi * 2)
            ctx.fill()
            # Right eye
            ctx.arc(4, -4, 2.4, 0, math.pi * 2)
            ctx.fill()
        else:
            # Eye blink line
            ctx.set_source_rgb(0.0, 0.95, 1.0)
            ctx.set_line_width(1.5)
            ctx.move_to(-6, -4)
            ctx.line_to(-2, -4)
            ctx.move_to(2, -4)
            ctx.line_to(6, -4)
            ctx.stroke()
        ctx.restore()

        # 6. Antenna with Blinking Beacon
        ctx.save()
        ctx.set_source_rgb(0.7, 0.75, 0.8)
        ctx.set_line_width(2.0)
        ctx.move_to(0, -21)
        ctx.line_to(0, -29)
        ctx.stroke()

        # Blinking beacon orb
        beacon_alpha = 0.5 + 0.5 * math.sin(self.anim_time * 4.0)
        ctx.set_source_rgba(0.1, 0.9, 1.0, beacon_alpha)
        ctx.arc(0, -31, 3.5, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        ctx.restore()
