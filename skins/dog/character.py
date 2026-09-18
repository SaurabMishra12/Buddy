"""Dog desktop companion: enthusiastic barking, tail wagging, jumping, and digging."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from skins.manager import skin_manager
from core.particles import ParticleManager


class DogCharacter(BaseCharacter):
    """Enthusiastic puppy companion with bouncy movement and playful barks."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="dog")
        self.can_fly = False
        self.tail_wave = 0.0
        self.ear_flop = 0.0
        self.tongue_out = True
        self.action_timer = time.time() + random.uniform(3.0, 7.0)
        self.paw_step = 0.0
        self.is_barking = False
        self.bark_end = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        if ability_name == "bark":
            self.is_barking = True
            self.bark_end = time.time() + 0.4
            particle_mgr.shockwave(self.x + (16 if self.facing_right else -16), self.y - 8, max_radius=35.0, color=(1.0, 0.8, 0.2))
            audio_mgr.play("bark")
            return True
        elif ability_name == "dig":
            self.state = "DIG"
            self.state_timer = time.time() + 2.5
            particle_mgr.smoke_puff(self.x, self.y + 16, count=4, color=(0.55, 0.40, 0.25))
            return True
        elif ability_name == "fetch":
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.vx = (dx / dist) * 18.0
            self.vy = (dy / dist) * 18.0 - 4.0
            self.state = CharacterState.JUMP
            particle_mgr.smoke_puff(self.x, self.y + 14, count=2)
            audio_mgr.play("bark")
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
        self.anim_time += 0.08
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)

        # Facing direction
        if abs(cursor_x - self.x) > 5.0 and self.state != "DIG":
            self.facing_right = (cursor_x >= self.x)

        if self.is_barking and now >= self.bark_end:
            self.is_barking = False

        if self.state == "DIG":
            self.vx *= 0.5
            self.vy *= 0.5
            if random.random() < 0.3:
                particle_mgr.smoke_puff(self.x + random.uniform(-6, 6), self.y + 16, count=1, color=(0.55, 0.40, 0.25))
            if now >= self.state_timer:
                self.state = CharacterState.IDLE
            return

        # Random personality events
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(4.0, 8.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.35:
                self.trigger_ability("bark", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.55:
                self.trigger_ability("dig", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.75:
                self.trigger_ability("fetch", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Cursor follow / chase
        dx = cursor_x - self.x
        dy = (cursor_y - 25.0) - self.y
        dist = math.hypot(dx, dy)

        speed_mult = config_data.get("speed", 1.0)
        max_spd = 11.0 * speed_mult
        accel = 0.65 * speed_mult

        if dist > 60.0 and config_data.get("cursor_follow", True):
            self.vx += (dx / dist) * min(dist * 0.06, accel)
            self.vy += (dy / dist) * min(dist * 0.06, accel)
            self.state = CharacterState.RUN if dist > 180.0 else CharacterState.WALK
            self.paw_step += 0.32
        else:
            self.state = CharacterState.IDLE
            self.vx *= 0.85
            self.vy *= 0.85

        self.vx *= 0.88
        self.vy *= 0.88

        spd = math.hypot(self.vx, self.vy)
        if spd > max_spd:
            self.vx = (self.vx / spd) * max_spd
            self.vy = (self.vy / spd) * max_spd

        self.x += self.vx
        self.y += self.vy

        # Screen boundary clamp
        self.x = max(min_x + 40.0, min(min_x + screen_w - 40.0, self.x))
        self.y = max(min_y + 40.0, min(min_y + screen_h - 50.0, self.y))

        # Tail wagging animation
        self.tail_wave += 0.35 if spd > 1.0 else 0.18
        self.ear_flop = math.sin(self.anim_time * 4.0) * (0.3 if spd > 1.0 else 0.1)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # Bouncing motion
        bounce = math.sin(self.paw_step * 2.0) * 2.5 if self.state in (CharacterState.WALK, CharacterState.RUN) else 0.0
        ctx.translate(0, bounce)

        # 1. Wagging Tail
        tail_ang = math.sin(self.tail_wave) * 0.7
        ctx.save()
        ctx.translate(-16, 2)
        ctx.rotate(tail_ang - 0.5)
        ctx.set_source_rgb(0.78, 0.52, 0.28)  # Golden brown
        ctx.set_line_width(5.5)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-6, -10, -10, -18, -4, -24)
        ctx.stroke()
        ctx.restore()

        # 2. Paws
        paw_off = math.sin(self.paw_step) * 5.0 if self.state in (CharacterState.WALK, CharacterState.RUN) else 0.0
        ctx.set_source_rgb(0.68, 0.44, 0.22)
        ctx.arc(-8, 16 - paw_off, 4.2, 0, 2 * math.pi)
        ctx.arc(8, 16 + paw_off, 4.2, 0, 2 * math.pi)
        ctx.fill()

        # 3. Dog Body
        ctx.set_source_rgb(0.82, 0.56, 0.30)
        ctx.save()
        ctx.translate(0, 5)
        ctx.scale(1.35, 1.0)
        ctx.arc(0, 0, 15, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # White chest patch
        ctx.set_source_rgb(0.96, 0.94, 0.90)
        ctx.arc(6, 6, 7.0, 0, 2 * math.pi)
        ctx.fill()

        # Red collar with gold medal tag
        ctx.set_source_rgb(0.90, 0.15, 0.15)
        ctx.rectangle(7, -3, 6, 4)
        ctx.fill()
        ctx.set_source_rgb(1.0, 0.85, 0.2)
        ctx.arc(10, 3, 2.5, 0, 2 * math.pi)
        ctx.fill()

        # 4. Dog Head
        ctx.set_source_rgb(0.82, 0.56, 0.30)
        ctx.arc(12, -6, 12, 0, 2 * math.pi)
        ctx.fill()

        # Floppy Ears
        ctx.save()
        ctx.translate(6, -14)
        ctx.rotate(self.ear_flop - 0.2)
        ctx.set_source_rgb(0.65, 0.40, 0.20)  # Darker ear
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-5, 8, -4, 16, 2, 18)
        ctx.curve_to(6, 14, 5, 6, 0, 0)
        ctx.fill()
        ctx.restore()

        # Muzzle / Snout
        ctx.set_source_rgb(0.92, 0.70, 0.45)
        ctx.arc(18, -4, 6.5, 0, 2 * math.pi)
        ctx.fill()

        # Black nose
        ctx.set_source_rgb(0.1, 0.1, 0.1)
        ctx.arc(22, -6, 2.6, 0, 2 * math.pi)
        ctx.fill()

        # Cute eye
        ctx.set_source_rgb(0.12, 0.08, 0.05)
        ctx.arc(13, -9, 2.8, 0, 2 * math.pi)
        ctx.fill()
        # Eye twinkle
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(12, -10, 1.0, 0, 2 * math.pi)
        ctx.fill()

        # Panting Tongue
        if self.tongue_out or self.is_barking:
            ctx.set_source_rgb(1.0, 0.45, 0.55)
            ctx.new_path()
            ctx.move_to(17, -1)
            ctx.curve_to(22, 4, 20, 8, 17, 7)
            ctx.curve_to(16, 4, 16, 1, 17, -1)
            ctx.fill()

        ctx.restore()


skin_manager.register("dog", DogCharacter)
