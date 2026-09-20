"""Alien desktop companion: UFO saucer flight, tractor beam, and cosmic pulses."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from behavior.personality import CharacterPersonality
from behavior.memory import CharacterMemory
from behavior.state_machine import CharacterBehavior, BehaviorState


class AlienCharacter(BaseCharacter):
    """Extraterrestrial companion riding a glowing flying saucer UFO."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="alien")
        self.can_fly = True
        self.is_airborne = True
        self.personality = CharacterPersonality(energy=0.75, curiosity=0.95, playfulness=0.60, sleepiness=0.20)
        self.memory = CharacterMemory(skin_id="alien")
        self.behavior = CharacterBehavior("Alien", personality=self.personality, memory=self.memory, can_fly=True)

        self.beam_active = False
        self.beam_timer = 0.0
        self.saucer_wobble = 0.0
        self.light_phase = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("ufo_beam", "tractor_beam"):
            self.beam_active = True
            self.beam_timer = time.time() + 1.5
            particle_mgr.shockwave(self.x, self.y + 20, max_radius=65.0, color=(0.2, 1.0, 0.4))
            audio_mgr.play("laser")
            self.memory.record_interaction("ufo_beam")
            return True

        elif ability_name == "cosmic_teleport":
            particle_mgr.cosmic_burst(self.x, self.y, count=12)
            self.x = target_x
            self.y = target_y
            particle_mgr.shockwave(self.x, self.y, max_radius=60.0, color=(0.4, 0.9, 0.5))
            audio_mgr.play("teleport")
            self.memory.record_interaction("cosmic_teleport")
            return True

        elif ability_name == "antigravity_pulse":
            particle_mgr.shockwave(self.x, self.y, max_radius=80.0, color=(0.2, 1.0, 0.7))
            particle_mgr.energy_orbs(self.x, self.y, count=4, color=(0.1, 0.9, 0.5))
            audio_mgr.play("magic")
            self.memory.record_interaction("antigravity_pulse")
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
        self.anim_time += dt * 3.5
        self.light_phase += dt * 6.0
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)

        if now > self.beam_timer:
            self.beam_active = False

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

        self.saucer_wobble = math.sin(self.anim_time * 1.5) * 5.0
        self.tilt = (self.vx / 10.0) * 0.15

        if self.state in (BehaviorState.FLY, BehaviorState.WALK):
            tx, ty = self.behavior.target_x, self.behavior.target_y
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            if dist > 15.0:
                self.vx += ((dx / dist) * 5.2 - self.vx) * 0.12
                self.vy += ((dy / dist) * 5.2 - self.vy) * 0.12
            else:
                self.vx *= 0.82
                self.vy *= 0.82
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.82
            self.vy *= 0.82

        self.x += self.vx
        self.y += self.vy

        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 70.0, self.y))

        # Cosmic stardust trail
        if random.random() < 0.22:
            particle_mgr.burst_stars(self.x, self.y + 12, count=1, size=4.0, color=(0.3, 1.0, 0.6))

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        ctx.save()
        ctx.translate(self.x, self.y + self.saucer_wobble)
        ctx.rotate(self.tilt)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Tractor Abduction Beam
        if self.beam_active:
            ctx.save()
            ctx.set_source_rgba(0.2, 1.0, 0.4, 0.3)
            ctx.new_path()
            ctx.move_to(-12, 12)
            ctx.line_to(12, 12)
            ctx.line_to(45, 80)
            ctx.line_to(-45, 80)
            ctx.close_path()
            ctx.fill()
            ctx.restore()

        # 2. Glass Dome & Cute Alien Pilot
        ctx.save()
        # Alien Head inside dome
        ctx.set_source_rgb(0.35, 0.88, 0.38)  # Lime alien skin
        ctx.arc(0, -6, 9, 0, math.pi * 2)
        ctx.fill()

        # Antenna
        ctx.set_source_rgb(0.3, 0.8, 0.32)
        ctx.set_line_width(1.5)
        ctx.move_to(0, -15)
        ctx.line_to(0, -22)
        ctx.stroke()
        ctx.arc(0, -23, 2.5, 0, math.pi * 2)
        ctx.fill()

        # Large Oval Alien Eyes (Glossy Black)
        ctx.set_source_rgb(0.06, 0.08, 0.1)
        ctx.save()
        ctx.translate(3, -6)
        ctx.scale(1.0, 1.4)
        ctx.arc(0, 0, 3.0, 0, math.pi * 2)
        ctx.fill()
        # White reflection dot
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(1, -1, 1.0, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # Glass Cockpit Dome
        ctx.set_source_rgba(0.5, 0.85, 1.0, 0.45)
        ctx.arc(0, -4, 15, math.pi, 0)
        ctx.close_path()
        ctx.fill()
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.7)
        ctx.set_line_width(1.2)
        ctx.stroke()
        ctx.restore()

        # 3. Metallic Saucer Hull
        ctx.save()
        # Saucer upper disc
        ctx.set_source_rgb(0.75, 0.8, 0.85)
        ctx.save()
        ctx.translate(0, 2)
        ctx.scale(1.0, 0.35)
        ctx.arc(0, 0, 32, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # Saucer lower rim
        ctx.set_source_rgb(0.5, 0.55, 0.62)
        ctx.save()
        ctx.translate(0, 5)
        ctx.scale(1.0, 0.3)
        ctx.arc(0, 0, 26, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # Saucer bottom emitter
        ctx.set_source_rgb(0.2, 1.0, 0.5)
        ctx.arc(0, 9, 5, 0, math.pi * 2)
        ctx.fill()

        # 4. Animated perimeter lights
        for i in range(5):
            angle = self.light_phase + (i * (math.pi / 2.5))
            light_x = math.cos(angle) * 26.0
            light_y = math.sin(angle) * 8.0 + 2.0
            ctx.set_source_rgba(0.2, 1.0, 0.4, 0.85)
            ctx.arc(light_x, light_y, 2.0, 0, math.pi * 2)
            ctx.fill()
        ctx.restore()

        ctx.restore()
