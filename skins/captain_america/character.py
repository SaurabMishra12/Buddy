"""Captain America character: tactical armor, screen-wide ricocheting Vibranium shield, and combat stances."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from skins.captain_america.shield import VibraniumShield
from core.projectiles import DesktopProjectileWindow
from core.particles import ParticleManager, CYAN_GLOW


class CaptainAmericaCharacter(BaseCharacter):
    """Steve Rogers with star-spangled uniform, defensive stances, and screen-wide ricocheting shield."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="captain_america")
        self.can_fly = False
        self.shield = VibraniumShield(x - 12.0, y + 2.0)
        self.is_blocking = False
        self.block_end = 0.0
        self.action_timer = time.time() + random.uniform(4.0, 8.0)
        self.hitbox_radius = 46.0

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
        if ability_name in ("shield_throw", "signature"):
            if self.shield.state == "HELD":
                self.shield.state = "THROWN"

                def _on_catch():
                    self.shield.state = "HELD"
                    particle_mgr.burst_sparks(self.x, self.y, count=12)

                DesktopProjectileWindow(
                    proj_type="shield",
                    start_x=hand_x,
                    start_y=hand_y,
                    target_x=target_x,
                    target_y=target_y,
                    owner_getter=self.get_shield_hand_pos,
                    on_catch=_on_catch,
                    speed=26.0
                )
                audio_mgr.play("smash")
                particle_mgr.burst_sparks(hand_x, hand_y, count=8)
                return True
        elif ability_name == "shield_block":
            self.is_blocking = True
            self.block_end = time.time() + 1.2
            particle_mgr.shockwave(hand_x, hand_y, max_radius=45.0, color=(0.4, 0.6, 1.0))
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
            self.action_timer = now + random.uniform(5.0, 9.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.50:
                self.trigger_ability("shield_throw", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.75:
                self.trigger_ability("shield_block", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.90:
                self.trigger_ability("hero_pose", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Ground sprint & run physics
        speed_mult = config_data.get("speed", 1.0)
        max_spd = 14.0 * speed_mult
        accel = 0.75 * speed_mult

        # True vector to cursor without artificial offset
        dx = cursor_x - self.x
        dist_x = abs(dx)

        if dist_x > 45.0:
            self.vx += (1.0 if dx > 0 else -1.0) * min(dist_x * 0.08, accel)
            self.state = CharacterState.RUN
            # Dust puffs when sprinting
            if random.random() < 0.2:
                particle_mgr.smoke_puff(self.x, self.y + 24, count=1)
        else:
            # Peaceful touch/petting deadzone
            self.state = CharacterState.IDLE
            self.vx *= 0.70

        self.vx *= 0.88
        self.vy = 0.0

        spd = abs(self.vx)
        if spd > max_spd:
            self.vx = (self.vx / spd) * max_spd

        self.x += self.vx
        self.y = ground_y

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # Running leg stride animation
        spd = abs(self.vx)
        leg_stride = math.sin(self.anim_time * 12.0) * 8.0 if spd > 2.0 else 0.0

        # 1. Legs & Crimson Combat Boots
        pat_pants = cairo.LinearGradient(0, 10, 0, 26)
        pat_pants.add_color_stop_rgb(0.0, 0.14, 0.25, 0.52)
        pat_pants.add_color_stop_rgb(1.0, 0.08, 0.15, 0.35)

        # Left Leg
        ctx.set_source(pat_pants)
        ctx.rectangle(-7 - leg_stride * 0.5, 12, 5.5, 14)
        ctx.fill()
        # Right Leg
        ctx.rectangle(2 + leg_stride * 0.5, 12, 5.5, 14)
        ctx.fill()

        # Crimson Combat Boots with Tread
        ctx.set_source_rgb(0.80, 0.12, 0.16)
        ctx.rectangle(-8 - leg_stride * 0.5, 22, 6.5, 7)
        ctx.rectangle(1 + leg_stride * 0.5, 22, 6.5, 7)
        ctx.fill()
        ctx.set_source_rgb(0.20, 0.05, 0.05)
        ctx.rectangle(-8 - leg_stride * 0.5, 27, 6.5, 2)
        ctx.rectangle(1 + leg_stride * 0.5, 27, 6.5, 2)
        ctx.fill()

        # 2. Torso with Red/White Abdominal Armor Stripes
        pat_chest = cairo.LinearGradient(0, -12, 0, 12)
        pat_chest.add_color_stop_rgb(0.0, 0.16, 0.32, 0.65)
        pat_chest.add_color_stop_rgb(1.0, 0.08, 0.18, 0.42)
        ctx.set_source(pat_chest)
        ctx.rectangle(-11, -11, 22, 23)
        ctx.fill()

        # Red & White Tactical Stripes on Abdomen
        stripe_cols = [(0.85, 0.12, 0.15), (0.95, 0.95, 0.95), (0.85, 0.12, 0.15), (0.95, 0.95, 0.95), (0.85, 0.12, 0.15)]
        for i, col in enumerate(stripe_cols):
            ctx.set_source_rgb(col[0], col[1], col[2])
            ctx.rectangle(-8.5 + i * 3.4, 2, 3.4, 10)
            ctx.fill()

        # Brown Leather Utility Belt & Tactical Buckles
        ctx.set_source_rgb(0.32, 0.18, 0.10)
        ctx.rectangle(-11, 11, 22, 3.5)
        ctx.fill()
        ctx.set_source_rgb(0.85, 0.75, 0.20)
        ctx.rectangle(-2.5, 10.5, 5, 4.5)
        ctx.fill()

        # White Star Insignia on Chest
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.new_path()
        r_out = 5.0
        r_in = 2.2
        for i in range(5):
            ang = -math.pi / 2 + i * (2 * math.pi / 5)
            x1 = math.cos(ang) * r_out
            y1 = -4.5 + math.sin(ang) * r_out
            if i == 0:
                ctx.move_to(x1, y1)
            else:
                ctx.line_to(x1, y1)
            ang_in = ang + (math.pi / 5)
            x2 = math.cos(ang_in) * r_in
            y2 = -4.5 + math.sin(ang_in) * r_in
            ctx.line_to(x2, y2)
        ctx.close_path()
        ctx.fill()

        # 3. Arms & Tactical Red Gauntlets
        ctx.set_source(pat_chest)
        ctx.rectangle(-15, -8, 4.5, 15)
        ctx.rectangle(10, -8, 4.5, 15)
        ctx.fill()
        # Red Combat Gauntlets
        ctx.set_source_rgb(0.80, 0.12, 0.16)
        ctx.rectangle(-15, 3, 4.5, 7)
        ctx.rectangle(10, 3, 4.5, 7)
        ctx.fill()

        # 4. Cowl Helmet with Embossed 'A' and Wings
        ctx.set_source(pat_chest)
        ctx.arc(0, -18, 9.5, 0, 2 * math.pi)
        ctx.fill()

        # Jawline / Flesh Face
        ctx.set_source_rgb(0.95, 0.78, 0.65)
        ctx.rectangle(-5.5, -16, 11, 7.5)
        ctx.fill()

        # Crisp White 'A' on Brow
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.set_line_width(1.6)
        ctx.move_to(-2.8, -15.5)
        ctx.line_to(0, -22.5)
        ctx.line_to(2.8, -15.5)
        ctx.move_to(-1.8, -18.5)
        ctx.line_to(1.8, -18.5)
        ctx.stroke()

        # Silver Helmet Wing Accents
        ctx.set_source_rgb(0.92, 0.94, 0.98)
        for side in [-1, 1]:
            ctx.new_path()
            ctx.move_to(side * 6.5, -19)
            ctx.line_to(side * 11.5, -23.5)
            ctx.line_to(side * 7.5, -16.5)
            ctx.close_path()
            ctx.fill()

        # 5. Held Vibranium Shield
        if self.shield.state == "HELD":
            ctx.save()
            if self.is_blocking:
                ctx.translate(14, -2)
                ctx.scale(0.85, 1.0)
            else:
                ctx.translate(-11, 4)
                ctx.scale(0.55, 1.0)

            # Draw Vibranium Shield with concentric rings
            ctx.set_source_rgb(0.85, 0.12, 0.15)
            ctx.arc(0, 0, 16, 0, 2 * math.pi)
            ctx.fill()
            ctx.set_source_rgb(0.92, 0.94, 0.98)
            ctx.arc(0, 0, 12, 0, 2 * math.pi)
            ctx.fill()
            ctx.set_source_rgb(0.85, 0.12, 0.15)
            ctx.arc(0, 0, 8.5, 0, 2 * math.pi)
            ctx.fill()
            ctx.set_source_rgb(0.12, 0.28, 0.72)
            ctx.arc(0, 0, 5.5, 0, 2 * math.pi)
            ctx.fill()
            # Star
            ctx.set_source_rgb(1.0, 1.0, 1.0)
            ctx.arc(0, 0, 2.5, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

        ctx.restore()
