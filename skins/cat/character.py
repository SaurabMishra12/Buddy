"""Cat desktop companion: prowling, cursor chasing, grooming, and sleeping."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from skins.manager import skin_manager
from core.particles import ParticleManager


class CatCharacter(BaseCharacter):
    """Classic adorable desktop cat with personality states and cursor stalking."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="cat")
        self.can_fly = False
        self.tail_angle = 0.0
        self.tail_wave = 0.0
        self.ear_twitch = 0.0
        self.pounce_prep = 0.0
        self.action_timer = time.time() + random.uniform(3.0, 8.0)
        self.paw_step = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        if ability_name == "pounce":
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.vx = (dx / dist) * 16.0
            self.vy = (dy / dist) * 16.0 - 5.0
            self.state = CharacterState.JUMP
            particle_mgr.smoke_puff(self.x, self.y + 15, count=2)
            audio_mgr.play("purr")
            return True
        elif ability_name == "groom":
            self.state = "GROOM"
            self.state_timer = time.time() + 3.0
            audio_mgr.play("purr")
            return True
        elif ability_name == "nap":
            self.state = CharacterState.SLEEP
            self.state_timer = time.time() + 6.0
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
        ground_y = min_y + screen_h - 60.0

        # Facing direction
        if abs(cursor_x - self.x) > 5.0 and self.state != CharacterState.SLEEP:
            self.facing_right = (cursor_x >= self.x)

        # Handle timed states (grooming / sleeping)
        if self.state in ("GROOM", CharacterState.SLEEP):
            self.vx *= 0.8
            self.vy *= 0.8
            if now >= self.state_timer:
                self.state = CharacterState.IDLE
                self.action_timer = now + random.uniform(4.0, 9.0) / max(0.2, activity)
            return

        # Random personality transitions
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(5.0, 11.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.25:
                self.trigger_ability("groom", cursor_x, cursor_y, particle_mgr, audio_mgr)
                return
            elif roll < 0.40:
                self.trigger_ability("nap", cursor_x, cursor_y, particle_mgr, audio_mgr)
                return
            elif roll < 0.65:
                # Sudden zoomies sprint towards cursor
                self.trigger_ability("pounce", cursor_x, cursor_y, particle_mgr, audio_mgr)
                return

        # Movement physics
        dx = cursor_x - self.x
        dy = (cursor_y - 20.0) - self.y
        dist = math.hypot(dx, dy)

        speed_mult = config_data.get("speed", 1.0)
        max_spd = 9.0 * speed_mult
        accel = 0.45 * speed_mult

        if dist > 70.0 and config_data.get("cursor_follow", True):
            # Walking or running
            self.vx += (dx / dist) * min(dist * 0.05, accel)
            self.vy += (dy / dist) * min(dist * 0.05, accel)
            self.state = CharacterState.RUN if dist > 200.0 else CharacterState.WALK
            self.paw_step += 0.25
        else:
            self.state = CharacterState.IDLE
            self.vx *= 0.85
            self.vy *= 0.85

        self.vx *= 0.90
        self.vy *= 0.90

        spd = math.hypot(self.vx, self.vy)
        if spd > max_spd:
            self.vx = (self.vx / spd) * max_spd
            self.vy = (self.vy / spd) * max_spd

        self.x += self.vx
        self.y += self.vy

        # Screen boundary clamp
        self.x = max(min_x + 40.0, min(min_x + screen_w - 40.0, self.x))
        self.y = max(min_y + 40.0, min(min_y + screen_h - 50.0, self.y))

        # Tail waving animation
        self.tail_wave += 0.12 if self.state != CharacterState.IDLE else 0.05
        self.tail_angle = math.sin(self.tail_wave) * (0.4 if self.state == CharacterState.IDLE else 0.8)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # Sleeping state
        if self.state == CharacterState.SLEEP:
            # Curled sleeping cat ball
            ctx.set_source_rgb(0.95, 0.55, 0.20)  # Orange tabby
            ctx.arc(0, 8, 18, 0, 2 * math.pi)
            ctx.fill()
            # Tail wrapping body
            ctx.set_line_width(4.5)
            ctx.arc(0, 8, 20, 0.4, 2.8)
            ctx.stroke()
            # Sleeping eyes
            ctx.set_source_rgb(0.3, 0.15, 0.05)
            ctx.set_line_width(1.5)
            ctx.arc(8, 4, 3, 0.2, math.pi - 0.2)
            ctx.stroke()
            # 'Z' particles
            if math.sin(self.anim_time * 2.0) > 0.7:
                particle_mgr.smoke_puff(self.x + 10, self.y - 12, count=1, color=(0.8, 0.8, 0.9))
            ctx.restore()
            return

        # 1. Animated Tail
        ctx.save()
        ctx.translate(-16, 2)
        ctx.rotate(self.tail_angle)
        ctx.set_source_rgb(0.92, 0.52, 0.18)  # Ginger coat
        ctx.set_line_width(5.0)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-10, -8, -14, -18, -8, -26)
        ctx.stroke()
        # White tail tip
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(-8, -26, 3.2, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # 2. Paws
        paw_offset = math.sin(self.paw_step) * 4.0 if self.state in (CharacterState.WALK, CharacterState.RUN) else 0.0
        ctx.set_source_rgb(1.0, 1.0, 1.0)  # White socks
        ctx.arc(-8, 16 - paw_offset, 4.0, 0, 2 * math.pi)
        ctx.arc(6, 16 + paw_offset, 4.0, 0, 2 * math.pi)
        ctx.fill()

        # 3. Cat Body
        ctx.set_source_rgb(0.95, 0.55, 0.20)
        ctx.save()
        ctx.translate(0, 6)
        ctx.scale(1.3, 1.0)
        ctx.arc(0, 0, 14, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # Tabby stripes
        ctx.set_source_rgb(0.80, 0.38, 0.10)
        ctx.set_line_width(2.0)
        ctx.move_to(-4, 0)
        ctx.line_to(-4, 8)
        ctx.move_to(2, -1)
        ctx.line_to(2, 7)
        ctx.stroke()

        # 4. Cat Head
        ctx.set_source_rgb(0.95, 0.55, 0.20)
        ctx.arc(10, -4, 11, 0, 2 * math.pi)
        ctx.fill()

        # Pointed Ears
        for ear_x, angle in [(4, -0.2), (14, 0.2)]:
            ctx.save()
            ctx.translate(ear_x, -12)
            ctx.rotate(angle)
            ctx.new_path()
            ctx.move_to(-4, 4)
            ctx.line_to(0, -9)
            ctx.line_to(4, 4)
            ctx.close_path()
            ctx.set_source_rgb(0.95, 0.55, 0.20)
            ctx.fill_preserve()
            # Pink inner ear
            ctx.set_source_rgb(1.0, 0.75, 0.80)
            ctx.set_line_width(1.0)
            ctx.stroke()
            ctx.restore()

        # Big Feline Eyes (Emerald Green)
        ctx.set_source_rgb(0.2, 0.85, 0.4)
        ctx.arc(8, -5, 3.2, 0, 2 * math.pi)
        ctx.arc(14, -5, 3.2, 0, 2 * math.pi)
        ctx.fill()

        # Pupils
        ctx.set_source_rgb(0.05, 0.05, 0.05)
        ctx.arc(8.5, -5, 1.5, 0, 2 * math.pi)
        ctx.arc(14.5, -5, 1.5, 0, 2 * math.pi)
        ctx.fill()

        # White eye glint
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(7.5, -6, 0.9, 0, 2 * math.pi)
        ctx.arc(13.5, -6, 0.9, 0, 2 * math.pi)
        ctx.fill()

        # Cute pink nose
        ctx.set_source_rgb(1.0, 0.65, 0.70)
        ctx.arc(12, -1, 1.5, 0, 2 * math.pi)
        ctx.fill()

        # Whiskers
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.8)
        ctx.set_line_width(1.0)
        ctx.move_to(14, -1)
        ctx.line_to(23, -3)
        ctx.move_to(14, 0)
        ctx.line_to(22, 2)
        ctx.stroke()

        ctx.restore()


skin_manager.register("cat", CatCharacter)
