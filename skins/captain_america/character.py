"""Captain America character: star-spangled armor, Vibranium Shield throws, and defensive block."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from skins.manager import skin_manager
from skins.captain_america.shield import VibraniumShield
from core.particles import ParticleManager


class CaptainAmericaCharacter(BaseCharacter):
    """Steve Rogers with star-spangled uniform, defensive stances, and ricocheting shield."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="captain_america")
        self.can_fly = False
        self.shield = VibraniumShield(x - 12.0, y + 2.0)
        self.is_blocking = False
        self.block_end = 0.0
        self.action_timer = time.time() + random.uniform(3.5, 7.0)

    def get_shield_hand_pos(self) -> Tuple[float, float]:
        dir_mult = 1.0 if self.facing_right else -1.0
        if self.is_blocking:
            return self.x + dir_mult * 14.0, self.y - 2.0
        else:
            return self.x - dir_mult * 10.0, self.y + 4.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        hand_x, hand_y = self.get_shield_hand_pos()
        if ability_name == "shield_throw":
            if self.shield.state == "HELD":
                self.shield.throw(hand_x, hand_y, target_x, target_y)
                particle_mgr.burst_sparks(hand_x, hand_y, count=6, color=(0.9, 0.9, 1.0))
                audio_mgr.play("smash")
                return True
        elif ability_name == "shield_block":
            self.is_blocking = True
            self.block_end = time.time() + 1.2
            particle_mgr.shockwave(hand_x, hand_y, max_radius=40.0, color=(0.4, 0.6, 1.0))
            audio_mgr.play("smash")
            return True
        elif ability_name == "hero_pose":
            self.state = CharacterState.VICTORY
            self.state_timer = time.time() + 1.5
            particle_mgr.burst_sparks(self.x, self.y - 15, count=10, color=(1.0, 0.85, 0.2))
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
        self.anim_time += 0.05
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)
        ground_y = min_y + screen_h - 65.0

        # Facing direction
        self.facing_right = (cursor_x >= self.x)

        if self.is_blocking and now >= self.block_end:
            self.is_blocking = False

        if self.state == CharacterState.VICTORY and now >= self.state_timer:
            self.state = CharacterState.IDLE

        # Random personality events
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(4.0, 8.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.45:
                self.trigger_ability("shield_throw", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.70:
                self.trigger_ability("shield_block", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.85:
                self.trigger_ability("hero_pose", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Ground movement physics
        speed_mult = config_data.get("speed", 1.0)
        max_spd = 12.0 * speed_mult
        accel = 0.60 * speed_mult

        # Apply gravity
        if self.y < ground_y:
            self.vy += 0.75
            self.is_airborne = True
        else:
            self.y = ground_y
            self.vy = 0.0
            self.is_airborne = False

        # Horizontal cursor follow
        dx = cursor_x - self.x
        dist_x = abs(dx)

        if dist_x > 70.0 and config_data.get("cursor_follow", True) and not self.is_blocking:
            dir_x = 1.0 if dx > 0 else -1.0
            self.vx += dir_x * accel
            if not self.is_airborne:
                self.state = CharacterState.RUN if dist_x > 200.0 else CharacterState.WALK
        else:
            self.vx *= 0.84
            if not self.is_airborne and self.state != CharacterState.VICTORY:
                self.state = CharacterState.IDLE

        self.vx *= 0.88
        if abs(self.vx) > max_spd:
            self.vx = (self.vx / abs(self.vx)) * max_spd

        self.x += self.vx
        self.y += self.vy

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = min(ground_y, max(min_y + 50.0, self.y))

        # Update shield
        hand_x, hand_y = self.get_shield_hand_pos()
        self.shield.update(hand_x, hand_y, screen_bounds, particle_mgr)

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()

        # Render shield if thrown
        if self.shield.state != "HELD":
            self.shield.draw(ctx)

        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Legs & Red Boots
        ctx.set_source_rgb(0.12, 0.28, 0.65)  # Navy uniform pants
        ctx.rectangle(-7, 12, 5, 14)
        ctx.rectangle(2, 12, 5, 14)
        ctx.fill()
        # Red Combat Boots
        ctx.set_source_rgb(0.85, 0.12, 0.15)
        ctx.rectangle(-8, 22, 6, 6)
        ctx.rectangle(1, 22, 6, 6)
        ctx.fill()

        # 2. Torso with Red/White Abdominal Stripes
        ctx.set_source_rgb(0.12, 0.28, 0.65)
        ctx.rectangle(-10, -10, 20, 22)
        ctx.fill()

        # Red & White stripes on stomach
        for i, col in enumerate([(0.85, 0.12, 0.15), (1.0, 1.0, 1.0), (0.85, 0.12, 0.15), (1.0, 1.0, 1.0), (0.85, 0.12, 0.15)]):
            ctx.set_source_rgb(col[0], col[1], col[2])
            ctx.rectangle(-8 + i * 3.2, 3, 3.2, 9)
            ctx.fill()

        # Brown Leather Utility Belt & Harness
        ctx.set_source_rgb(0.35, 0.20, 0.10)
        ctx.rectangle(-10, 11, 20, 3)
        ctx.fill()

        # White Star on Chest
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.new_path()
        r_out = 4.5
        r_in = 2.0
        for i in range(5):
            ang = -math.pi / 2 + i * (2 * math.pi / 5)
            x1 = math.cos(ang) * r_out
            y1 = -4 + math.sin(ang) * r_out
            if i == 0:
                ctx.move_to(x1, y1)
            else:
                ctx.line_to(x1, y1)
            ang_in = ang + (math.pi / 5)
            x2 = math.cos(ang_in) * r_in
            y2 = -4 + math.sin(ang_in) * r_in
            ctx.line_to(x2, y2)
        ctx.close_path()
        ctx.fill()

        # 3. Arms & Hands
        ctx.set_source_rgb(0.12, 0.28, 0.65)
        ctx.rectangle(-14, -8, 4, 15)
        ctx.rectangle(10, -8, 4, 15)
        ctx.fill()
        # Red gauntlet gloves
        ctx.set_source_rgb(0.85, 0.12, 0.15)
        ctx.rectangle(-14, 3, 4, 6)
        ctx.rectangle(10, 3, 4, 6)
        ctx.fill()

        # 4. Helmet with 'A' and Wings
        ctx.set_source_rgb(0.12, 0.28, 0.65)
        ctx.arc(0, -18, 9, 0, 2 * math.pi)
        ctx.fill()

        # White 'A' on forehead
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.set_line_width(1.5)
        ctx.move_to(-2.5, -15)
        ctx.line_to(0, -22)
        ctx.line_to(2.5, -15)
        ctx.move_to(-1.8, -18)
        ctx.line_to(1.8, -18)
        ctx.stroke()

        # Silver helmet wings
        ctx.set_source_rgb(0.9, 0.92, 0.96)
        ctx.new_path()
        ctx.move_to(-7, -19)
        ctx.line_to(-12, -23)
        ctx.line_to(-8, -17)
        ctx.close_path()
        ctx.fill()

        ctx.new_path()
        ctx.move_to(7, -19)
        ctx.line_to(12, -23)
        ctx.line_to(8, -17)
        ctx.close_path()
        ctx.fill()

        # 5. Held Shield
        if self.shield.state == "HELD":
            ctx.save()
            if self.is_blocking:
                ctx.translate(12, -2)
                ctx.scale(0.8, 1.0)
            else:
                ctx.translate(-10, 4)
                ctx.scale(0.5, 1.0)
            self.shield.draw(ctx)
            ctx.restore()

        ctx.restore()
        ctx.restore()


skin_manager.register("captain_america", CaptainAmericaCharacter)
