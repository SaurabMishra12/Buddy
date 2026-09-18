"""Superman character: supersonic flight trails, laser heat vision beams, and heroic hover."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from skins.manager import skin_manager
from core.particles import ParticleManager, CYAN_GLOW


class SupermanCharacter(BaseCharacter):
    """Man of Steel with supersonic flight speed, flowing cape, and cursor-tracking heat vision lasers."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="superman")
        self.can_fly = True
        self.is_firing_heat_vision = False
        self.heat_vision_end = 0.0
        self.heat_target = (0.0, 0.0)
        self.action_timer = time.time() + random.uniform(3.0, 6.0)
        self.hover_offset = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        if ability_name == "heat_vision":
            self.is_firing_heat_vision = True
            self.heat_vision_end = time.time() + 0.65
            self.heat_target = (target_x, target_y)
            dir_mult = 1.0 if self.facing_right else -1.0
            beam_x = self.x + dir_mult * 50.0
            beam_y = self.y - 14.0
            particle_mgr.burst_sparks(beam_x, beam_y, count=16, color=(1.0, 0.25, 0.05), size=2.8)
            particle_mgr.shockwave(beam_x, beam_y, max_radius=45.0, color=(1.0, 0.35, 0.1))
            audio_mgr.play("laser")
            return True
        elif ability_name == "supersonic_flight":
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.vx = (dx / dist) * 28.0
            self.vy = (dy / dist) * 28.0
            self.state = CharacterState.FLY
            particle_mgr.shockwave(self.x, self.y, max_radius=65.0, color=(0.9, 0.95, 1.0))
            audio_mgr.play("jet")
            return True
        return False

    def update(
        self,
        dt: float,
        cursor_x: float,
        cursor_y: float,
        screen_bounds: Tuple[int, int, int, int],
        particle_mgr: ParticleManager,
        audio_mgr: Any,
        config_data: Dict[str, Any]
    ) -> None:
        self.anim_time += 0.06
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)

        # Facing direction
        self.facing_right = (cursor_x >= self.x)

        if self.is_firing_heat_vision and now >= self.heat_vision_end:
            self.is_firing_heat_vision = False

        # Periodic heroic action
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(4.0, 8.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.60:
                self.trigger_ability("heat_vision", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.85:
                self.trigger_ability("supersonic_flight", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Supersonic flight movement
        speed_mult = config_data.get("speed", 1.0)
        max_spd = 22.0 * speed_mult
        accel = 1.10 * speed_mult

        tx = cursor_x - (40.0 if self.facing_right else -40.0)
        ty = cursor_y - 45.0
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)

        if dist > 40.0:
            self.vx += (dx / dist) * min(dist * 0.08, accel)
            self.vy += (dy / dist) * min(dist * 0.08, accel)
            self.state = CharacterState.FLY
        else:
            self.state = CharacterState.HOVER
            self.vx *= 0.86
            self.vy *= 0.86

        self.vx *= 0.91
        self.vy *= 0.91

        spd = math.hypot(self.vx, self.vy)
        if spd > max_spd:
            self.vx = (self.vx / spd) * max_spd
            self.vy = (self.vy / spd) * max_spd

        self.x += self.vx
        self.y += self.vy

        # Gentle floating hover wave
        self.hover_offset = math.sin(self.anim_time * 2.5) * 3.5

        # Speed streak particles during supersonic flight
        if spd > 10.0 and random.random() < 0.4:
            particle_mgr.burst_sparks(self.x, self.y, count=2, color=(0.85, 0.95, 1.0), size=1.6)

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 50.0, self.y))

        # Dynamic body tilt
        target_tilt = (self.vx / max_spd) * 0.35 if self.state == CharacterState.FLY else 0.0
        self.tilt += (target_tilt - self.tilt) * 0.15

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()

        # 1. Twin crimson heat vision beams from eyes
        if self.is_firing_heat_vision:
            ctx.save()
            dir_mult = 1.0 if self.facing_right else -1.0
            eye_x = self.x + dir_mult * 6.0
            eye_y = self.y - 15.0 + self.hover_offset

            dx = self.heat_target[0] - self.x
            dy = self.heat_target[1] - self.y
            dist = math.hypot(dx, dy) + 1e-4
            beam_len = min(68.0, max(35.0, dist))
            tx = eye_x + (dx / dist) * beam_len
            ty = eye_y + (dy / dist) * beam_len

            # Outer radiant crimson energy glow
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_width(8.0)
            ctx.set_source_rgba(1.0, 0.1, 0.05, 0.55)
            ctx.move_to(eye_x, eye_y)
            ctx.line_to(tx, ty)
            ctx.stroke()

            # Mid laser core
            ctx.set_line_width(4.0)
            ctx.set_source_rgba(1.0, 0.45, 0.1, 0.85)
            ctx.move_to(eye_x, eye_y)
            ctx.line_to(tx, ty)
            ctx.stroke()

            # White-hot laser beam center
            ctx.set_line_width(1.8)
            ctx.set_source_rgba(1.0, 0.98, 0.85, 0.95)
            ctx.move_to(eye_x, eye_y)
            ctx.line_to(tx, ty)
            ctx.stroke()

            # Target impact blast flare
            ctx.set_source_rgba(1.0, 0.8, 0.2, 0.8)
            ctx.arc(tx, ty, 5.0, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

        # 2. Translate & Orient Superman
        ctx.translate(self.x, self.y + self.hover_offset)
        ctx.rotate(self.tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 3. Flowing Red Cape with dynamic wind ripples
        wave1 = math.sin(self.anim_time * 3.5) * 3.0
        wave2 = math.cos(self.anim_time * 3.0) * 2.5
        ctx.save()
        ctx.set_source_rgb(0.85, 0.10, 0.15)  # Scarlet red
        ctx.new_path()
        ctx.move_to(-4, -8)
        ctx.curve_to(-16 + wave1, 2 + wave2, -26 + wave2, 14 + wave1, -22 + wave1, 30)
        ctx.line_to(4, 25)
        ctx.line_to(4, -8)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # 4. Outstretched Heroic Arm when Flying
        if self.state == CharacterState.FLY:
            ctx.save()
            # Outstretched right arm forward
            ctx.set_source_rgb(0.08, 0.32, 0.78)
            ctx.rectangle(2, -8, 14, 5.5)
            ctx.fill()
            # Clenched fist
            ctx.set_source_rgb(0.95, 0.78, 0.65)
            ctx.arc(17, -5.2, 3.2, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

        # 5. Blue Kryptonian Suit & Red Trunks
        ctx.set_source_rgb(0.08, 0.32, 0.78)  # Royal Krypton blue
        ctx.rectangle(-9, -8, 18, 22)
        ctx.fill()

        # Muscular legs
        ctx.rectangle(-8, 14, 6, 14)
        ctx.rectangle(2, 14, 6, 14)
        ctx.fill()

        # Red Boots
        ctx.set_source_rgb(0.85, 0.10, 0.15)
        ctx.rectangle(-8, 24, 6, 6)
        ctx.rectangle(2, 24, 6, 6)
        ctx.fill()

        # Red trunks & golden belt
        ctx.rectangle(-9, 10, 18, 5)
        ctx.fill()
        ctx.set_source_rgb(0.95, 0.80, 0.15)
        ctx.rectangle(-9, 8, 18, 2.5)
        ctx.fill()

        # 6. House of El 'S' Shield on Chest
        ctx.save()
        ctx.translate(0, -2)
        # Yellow diamond crest
        ctx.set_source_rgb(0.95, 0.80, 0.15)
        ctx.new_path()
        ctx.move_to(0, -6)
        ctx.line_to(7, -3)
        ctx.line_to(5, 5)
        ctx.line_to(0, 8)
        ctx.line_to(-5, 5)
        ctx.line_to(-7, -3)
        ctx.close_path()
        ctx.fill()
        # Red 'S' symbol
        ctx.set_source_rgb(0.85, 0.10, 0.15)
        ctx.set_line_width(1.6)
        ctx.move_to(3, -3)
        ctx.curve_to(-3, -4, -3, 0, 0, 1)
        ctx.curve_to(3, 2, 3, 6, -3, 5)
        ctx.stroke()
        ctx.restore()

        # 7. Head & Classic Spit Curl Hair
        ctx.set_source_rgb(0.95, 0.78, 0.65)
        ctx.arc(0, -15, 9, 0, 2 * math.pi)
        ctx.fill()

        # Jet black hair
        ctx.set_source_rgb(0.08, 0.08, 0.12)
        ctx.arc(0, -18, 9, math.pi, 2 * math.pi)
        ctx.fill()

        # Forehead spit curl
        ctx.set_line_width(1.5)
        ctx.move_to(1, -21)
        ctx.curve_to(3, -17, 0, -16, 2, -14)
        ctx.stroke()

        # Blue eyes (blazing red when firing heat vision)
        if self.is_firing_heat_vision:
            ctx.set_source_rgb(1.0, 0.2, 0.1)
            ctx.arc(-2.5, -15, 2.2, 0, 2 * math.pi)
            ctx.fill()
            ctx.arc(4.5, -15, 2.2, 0, 2 * math.pi)
            ctx.fill()
        else:
            ctx.set_source_rgb(0.1, 0.45, 0.85)
            ctx.arc(-2.5, -15, 1.4, 0, 2 * math.pi)
            ctx.fill()
            ctx.arc(4.5, -15, 1.4, 0, 2 * math.pi)
            ctx.fill()

        ctx.restore()


skin_manager.register("superman", SupermanCharacter)
