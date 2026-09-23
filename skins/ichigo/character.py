"""Ichigo Kurosaki desktop companion: Shikai Zangetsu, Bankai Tensa Zangetsu, Getsuga Tenshō, and Shunpo."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, Optional

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager, CYAN_GLOW


class IchigoCharacter(BaseCharacter):
    """Ichigo Kurosaki — Substitute Soul Reaper with Zangetsu, Getsuga Tenshō, and Bankai."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="ichigo")
        self.can_fly = False
        self.is_bankai = False
        self.bankai_timer = 0.0

        # Animation states
        self.idle_substate = "STAND"  # "STAND", "SIT_CROSS", "PHONE", "ARMS_CROSSED", "NAP"
        self.substate_timer = time.time() + random.uniform(5.0, 10.0)
        self.nap_waking = False
        self.nap_wake_time = 0.0

        # Combat action states
        self.slash_active = False
        self.slash_end_time = 0.0
        self.shunpo_active = False
        self.shunpo_end_time = 0.0

        # Cloth & hair sway
        self.cloth_flutter = 0.0
        self.afterimages = []

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        now = time.time()
        if ability_name == "getsuga_tensho":
            self.slash_active = True
            self.slash_end_time = now + 0.35
            self.facing_right = (target_x >= self.x)
            particle_mgr.launch_getsuga(self.x, self.y - 10.0, target_x, target_y, is_bankai=self.is_bankai)
            reiatsu_color = (0.9, 0.1, 0.1) if self.is_bankai else (0.15, 0.65, 1.0)
            particle_mgr.burst_reiatsu(self.x, self.y, color=reiatsu_color, count=10)
            if audio_mgr:
                audio_mgr.play("swoosh")
            return True

        elif ability_name == "bankai":
            self.is_bankai = not self.is_bankai
            self.bankai_timer = now + 25.0 if self.is_bankai else 0.0
            particle_mgr.shockwave(self.x, self.y, max_radius=90.0, color=(0.9, 0.1, 0.1) if self.is_bankai else (0.2, 0.7, 1.0))
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.1, 0.1, 0.15) if self.is_bankai else (0.2, 0.7, 1.0), count=16)
            particle_mgr.burst_sparks(self.x, self.y, count=16, color=(1.0, 0.2, 0.2) if self.is_bankai else CYAN_GLOW)
            if audio_mgr:
                audio_mgr.play("magic")
            return True

        elif ability_name == "shunpo":
            self.shunpo_active = True
            self.shunpo_end_time = now + 0.25
            old_x, old_y = self.x, self.y
            dest_x = target_x + random.uniform(-25, 25)
            dest_y = target_y + random.uniform(-15, 15)
            # Create 2-3 fading afterimage copies at 60-80ms offsets along the dash vector
            self.afterimages = []
            for i in range(1, 4):
                t_frac = i / 4.0
                delay = i * 0.070  # ~70ms offset
                img_x = old_x + (dest_x - old_x) * t_frac
                img_y = old_y + (dest_y - old_y) * t_frac
                self.afterimages.append({
                    "x": img_x,
                    "y": img_y,
                    "facing_right": self.facing_right,
                    "is_bankai": self.is_bankai,
                    "created_at": now,
                    "offset_delay": delay,
                    "duration": 0.24,
                })
            self.x = dest_x
            self.y = dest_y
            particle_mgr.burst_sparks(old_x, old_y, count=10, color=(0.1, 0.1, 0.1))
            particle_mgr.burst_reiatsu(self.x, self.y, color=(0.8, 0.1, 0.1) if self.is_bankai else (0.1, 0.6, 1.0), count=8)
            if audio_mgr:
                audio_mgr.play("swoosh")
            return True

        elif ability_name == "check_phone":
            self.idle_substate = "PHONE"
            self.substate_timer = now + 4.0
            return True

        elif ability_name == "cross_legged_rest":
            self.idle_substate = "SIT_CROSS"
            self.substate_timer = now + 7.0
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
        self.anim_time += dt * 5.0
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        companion_mode = config_data.get("companion_mode", "static")

        # Bankai duration timeout
        if self.is_bankai and self.bankai_timer > 0 and now > self.bankai_timer:
            self.is_bankai = False
            particle_mgr.burst_sparks(self.x, self.y, count=10, color=(0.4, 0.4, 0.4))

        # Reset timed actions
        if self.slash_active and now > self.slash_end_time:
            self.slash_active = False
        if self.shunpo_active and now > self.shunpo_end_time:
            self.shunpo_active = False

        # Idle substate transitions when peaceful
        is_moving = math.hypot(self.vx, self.vy) > 0.5
        if is_moving:
            self.idle_substate = "STAND"
            self.nap_waking = False
        else:
            if now >= self.substate_timer:
                self.substate_timer = now + random.uniform(6.0, 14.0)
                substates = ["STAND", "STAND", "SIT_CROSS", "PHONE", "ARMS_CROSSED", "NAP"]
                self.idle_substate = random.choice(substates)
                if self.idle_substate == "NAP":
                    self.nap_waking = False

        # If user taps or moves near while napping, wake up with a jolt
        if self.idle_substate == "NAP":
            dist = math.hypot(cursor_x - self.x, cursor_y - self.y)
            if dist < 70.0 and not self.nap_waking:
                self.nap_waking = True
                self.nap_wake_time = now + 1.2
                particle_mgr.burst_sparks(self.x, self.y - 25, count=5, color=(1.0, 0.8, 0.2))
            if self.nap_waking and now > self.nap_wake_time:
                self.idle_substate = "STAND"
                self.nap_waking = False

        # Facing direction
        if not self.slash_active and abs(cursor_x - self.x) > 10.0:
            self.facing_right = (cursor_x >= self.x)

        # Ambient spiritual aura in Bankai
        if self.is_bankai and random.random() < 0.25:
            particle_mgr.burst_reiatsu(self.x, self.y + 10, color=(0.1, 0.1, 0.15), count=1)

        # Update Shunpo fading afterimages
        self.afterimages = [
            img for img in self.afterimages
            if (now - img["created_at"]) < (img["offset_delay"] + img["duration"])
        ]

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        now = time.time()
        # Draw Shunpo fading afterimages (2-3 copies at 60-80ms offsets)
        for img in self.afterimages:
            elapsed = now - img["created_at"]
            if elapsed >= img["offset_delay"]:
                fade = max(0.0, min(1.0, 1.0 - (elapsed - img["offset_delay"]) / img["duration"]))
                if fade > 0.02:
                    ctx.save()
                    ctx.translate(img["x"], img["y"])
                    ctx.scale(self.scale, self.scale)
                    if not img["facing_right"]:
                        ctx.scale(-1, 1)
                    if img["is_bankai"]:
                        ctx.set_source_rgba(0.9, 0.1, 0.15, fade * 0.45)
                    else:
                        ctx.set_source_rgba(0.15, 0.65, 1.0, fade * 0.45)
                    ctx.arc(0, -18, 12, 0, math.pi * 2)
                    ctx.fill()
                    ctx.rectangle(-8, -6, 16, 22)
                    ctx.fill()
                    ctx.rectangle(-8, 16, 6, 14)
                    ctx.rectangle(2, 16, 6, 14)
                    ctx.fill()
                    ctx.restore()

        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1, 1)

        # Gentle breathing / idle bob
        bob_y = math.sin(self.anim_time * 2.0) * 1.5 if self.idle_substate == "STAND" else 0.0
        ctx.translate(0, bob_y)

        # 1. Back aura / Reiatsu surge if in Bankai
        if self.is_bankai:
            ctx.save()
            ctx.set_source_rgba(0.9, 0.1, 0.15, 0.18 + 0.08 * math.sin(self.anim_time * 4.0))
            ctx.arc(0, 0, 36.0, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

        # 2. Zanpakutō on back / at side (if not swinging)
        if not self.slash_active:
            self._draw_sheathed_sword(ctx)

        # 3. Lower Body / Legs / Seated pose
        if self.idle_substate == "SIT_CROSS":
            self._draw_seated_legs(ctx)
        else:
            self._draw_standing_legs(ctx)

        # 4. Torso & Shihakushō
        self._draw_torso(ctx)

        # 5. Head, Face & Spiky Orange Hair
        self._draw_head(ctx)

        # 6. Arms & Props (Phone, Active Sword Slash, or Crossed Arms)
        self._draw_arms(ctx)

        ctx.restore()

    def _draw_sheathed_sword(self, ctx: cairo.Context) -> None:
        ctx.save()
        if self.is_bankai:
            # Tensa Zangetsu: Sleek black sheath along back
            ctx.translate(-14, -8)
            ctx.rotate(0.55)
            # Black scabbard
            ctx.set_source_rgb(0.08, 0.08, 0.1)
            ctx.rectangle(-2, -32, 4, 38)
            ctx.fill()
            # Golden accents
            ctx.set_source_rgb(0.85, 0.7, 0.2)
            ctx.rectangle(-2.5, -34, 5, 2)
            ctx.fill()
        else:
            # Shikai Zangetsu: Large wrapped cleaver blade on back
            ctx.translate(-16, -12)
            ctx.rotate(0.60)
            # White wrapped cloth hilt and blade back
            ctx.set_source_rgb(0.92, 0.92, 0.94)
            ctx.new_path()
            ctx.move_to(-4, -28)
            ctx.line_to(6, -28)
            ctx.line_to(10, 18)
            ctx.line_to(-4, 18)
            ctx.close_path()
            ctx.fill()
            # Black cleaver blade edge
            ctx.set_source_rgb(0.12, 0.12, 0.14)
            ctx.new_path()
            ctx.move_to(2, -28)
            ctx.line_to(6, -28)
            ctx.line_to(10, 18)
            ctx.line_to(2, 18)
            ctx.close_path()
            ctx.fill()
            # Silver blade tip curve
            ctx.set_source_rgb(0.75, 0.78, 0.82)
            ctx.set_line_width(1.2)
            ctx.move_to(10, 18)
            ctx.line_to(6, -28)
            ctx.stroke()
        ctx.restore()

    def _draw_standing_legs(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Black hakama trousers
        ctx.set_source_rgb(0.1, 0.1, 0.12)
        # Left leg
        ctx.new_path()
        ctx.move_to(-7, 10)
        ctx.line_to(-12, 28)
        ctx.line_to(-4, 28)
        ctx.line_to(-2, 10)
        ctx.close_path()
        ctx.fill()
        # Right leg
        ctx.new_path()
        ctx.move_to(2, 10)
        ctx.line_to(4, 28)
        ctx.line_to(12, 28)
        ctx.line_to(7, 10)
        ctx.close_path()
        ctx.fill()
        # White tabi socks & straw waraji sandals
        ctx.set_source_rgb(0.95, 0.95, 0.95)
        ctx.rectangle(-11, 28, 6, 4)
        ctx.rectangle(5, 28, 6, 4)
        ctx.fill()
        # Straw straps
        ctx.set_source_rgb(0.7, 0.6, 0.4)
        ctx.set_line_width(1.0)
        ctx.move_to(-11, 30)
        ctx.line_to(-5, 30)
        ctx.move_to(5, 30)
        ctx.line_to(11, 30)
        ctx.stroke()
        ctx.restore()

    def _draw_seated_legs(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Crossed legs hakama fold
        ctx.set_source_rgb(0.1, 0.1, 0.12)
        ctx.new_path()
        ctx.move_to(-16, 12)
        ctx.line_to(16, 12)
        ctx.line_to(14, 24)
        ctx.line_to(-14, 24)
        ctx.close_path()
        ctx.fill()
        # Feet tucked
        ctx.set_source_rgb(0.95, 0.95, 0.95)
        ctx.arc(-13, 22, 3.0, 0, math.pi * 2)
        ctx.arc(13, 22, 3.0, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

    def _draw_torso(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Black Shihakushō kimono robe
        ctx.set_source_rgb(0.12, 0.12, 0.14)
        ctx.new_path()
        ctx.move_to(-10, -10)
        ctx.line_to(10, -10)
        ctx.line_to(12, 12)
        ctx.line_to(-12, 12)
        ctx.close_path()
        ctx.fill()

        # White inner collar (juban) V-neck
        ctx.set_source_rgb(0.95, 0.95, 0.98)
        ctx.new_path()
        ctx.move_to(-5, -10)
        ctx.line_to(0, 0)
        ctx.line_to(5, -10)
        ctx.close_path()
        ctx.fill()

        # White obi sash belt
        ctx.set_source_rgb(0.90, 0.90, 0.94)
        ctx.rectangle(-11, 6, 22, 5)
        ctx.fill()

        # Red Zangetsu harness strap across chest
        ctx.set_source_rgb(0.85, 0.15, 0.15)
        ctx.set_line_width(2.4)
        ctx.move_to(-9, -8)
        ctx.line_to(9, 7)
        ctx.stroke()

        # Bankai coat jagged flutter
        if self.is_bankai:
            ctx.set_source_rgb(0.08, 0.08, 0.1)
            ctx.new_path()
            ctx.move_to(-12, 10)
            ctx.line_to(-16, 26 + math.sin(self.anim_time * 3.0) * 2.0)
            ctx.line_to(-10, 22)
            ctx.line_to(0, 24)
            ctx.line_to(10, 22)
            ctx.line_to(16, 26 - math.sin(self.anim_time * 3.0) * 2.0)
            ctx.line_to(12, 10)
            ctx.close_path()
            ctx.fill()
            # Red inner lining border
            ctx.set_source_rgb(0.75, 0.1, 0.1)
            ctx.set_line_width(1.0)
            ctx.stroke()
        ctx.restore()

    def _draw_head(self, ctx: cairo.Context) -> None:
        ctx.save()
        # Head tilt / nap drooping
        head_y = -18
        if self.idle_substate == "NAP":
            if self.nap_waking:
                ctx.translate(0, -2)  # Jolt up!
            else:
                ctx.translate(0, 3)  # Drooping sleep

        # Neck
        ctx.set_source_rgb(0.96, 0.78, 0.65)
        ctx.rectangle(-3.5, head_y + 4, 7, 6)
        ctx.fill()

        # Face
        ctx.set_source_rgb(0.98, 0.82, 0.70)
        ctx.new_path()
        ctx.move_to(-7, head_y - 8)
        ctx.line_to(7, head_y - 8)
        ctx.line_to(6, head_y + 4)
        ctx.line_to(0, head_y + 8)  # Sharp chin
        ctx.line_to(-6, head_y + 4)
        ctx.close_path()
        ctx.fill()

        # Eyes & Eyebrows
        if self.idle_substate == "NAP" and not self.nap_waking:
            # Sleeping closed eyes
            ctx.set_source_rgb(0.3, 0.2, 0.15)
            ctx.set_line_width(1.2)
            ctx.move_to(-5, head_y)
            ctx.line_to(-1, head_y + 1)
            ctx.move_to(1, head_y + 1)
            ctx.line_to(5, head_y)
            ctx.stroke()
            # Small Zzz bubble
            ctx.set_source_rgba(0.2, 0.6, 1.0, 0.8)
            ctx.set_font_size(8)
            ctx.move_to(8, head_y - 6)
            ctx.show_text("z")
        else:
            # Sharp determined eyes
            ctx.set_source_rgb(0.98, 0.98, 0.98)
            ctx.rectangle(-5.5, head_y - 2, 4, 3)
            ctx.rectangle(1.5, head_y - 2, 4, 3)
            ctx.fill()

            # Brown irises & black pupils
            ctx.set_source_rgb(0.45, 0.22, 0.08)
            ctx.arc(-3.5, head_y - 0.5, 1.4, 0, math.pi * 2)
            ctx.arc(3.5, head_y - 0.5, 1.4, 0, math.pi * 2)
            ctx.fill()

            # Confident furrowed orange eyebrows
            ctx.set_source_rgb(0.85, 0.35, 0.05)
            ctx.set_line_width(1.3)
            ctx.move_to(-6, head_y - 4)
            ctx.line_to(-1.5, head_y - 2)
            ctx.move_to(6, head_y - 4)
            ctx.line_to(1.5, head_y - 2)
            ctx.stroke()

            # Determined smirk
            ctx.set_source_rgb(0.5, 0.25, 0.2)
            ctx.set_line_width(1.1)
            ctx.move_to(-2, head_y + 4)
            ctx.line_to(3, head_y + 3.5)
            ctx.stroke()

        # Spiky Bright Orange Hair!
        ctx.set_source_rgb(1.0, 0.48, 0.05)
        spikes = [
            (-9, head_y - 6), (-12, head_y - 12), (-7, head_y - 14),
            (-8, head_y - 18), (-3, head_y - 16), (-2, head_y - 21),
            (2, head_y - 20), (4, head_y - 16), (8, head_y - 18),
            (7, head_y - 13), (12, head_y - 11), (9, head_y - 5),
            (6, head_y - 7), (0, head_y - 8), (-6, head_y - 7)
        ]
        ctx.new_path()
        ctx.move_to(spikes[0][0], spikes[0][1])
        for sx, sy in spikes[1:]:
            ctx.line_to(sx, sy)
        ctx.close_path()
        ctx.fill()

        # Hair highlight streaks
        ctx.set_source_rgb(1.0, 0.68, 0.2)
        ctx.set_line_width(1.2)
        ctx.move_to(-2, head_y - 18)
        ctx.line_to(-1, head_y - 12)
        ctx.move_to(3, head_y - 17)
        ctx.line_to(3, head_y - 11)
        ctx.stroke()

        ctx.restore()

    def _draw_arms(self, ctx: cairo.Context) -> None:
        ctx.save()
        if self.slash_active:
            # Active Getsuga swing forward!
            ctx.set_source_rgb(0.12, 0.12, 0.14)
            ctx.new_path()
            ctx.move_to(8, -8)
            ctx.line_to(22, -4)
            ctx.line_to(20, 2)
            ctx.line_to(8, -2)
            ctx.close_path()
            ctx.fill()

            # Hand
            ctx.set_source_rgb(0.98, 0.82, 0.70)
            ctx.arc(22, -1, 3.0, 0, math.pi * 2)
            ctx.fill()

            # Drawing the active swinging blade!
            if self.is_bankai:
                # Tensa Zangetsu: Sleek pitch black katana with manji tsuba
                ctx.translate(22, -1)
                ctx.rotate(-0.35)
                # Black blade
                ctx.set_source_rgb(0.05, 0.05, 0.08)
                ctx.rectangle(0, -2, 38, 3.5)
                ctx.fill()
                # Silver razor edge
                ctx.set_source_rgb(0.85, 0.88, 0.95)
                ctx.set_line_width(0.8)
                ctx.move_to(0, 1.5)
                ctx.line_to(38, 1.5)
                ctx.stroke()
                # Manji guard
                ctx.set_source_rgb(0.15, 0.15, 0.18)
                ctx.rectangle(-2, -5, 4, 10)
                ctx.fill()
            else:
                # Shikai Zangetsu: Giant cleaver slash
                ctx.translate(22, -1)
                ctx.rotate(-0.25)
                ctx.set_source_rgb(0.12, 0.12, 0.14)
                ctx.new_path()
                ctx.move_to(0, -6)
                ctx.line_to(36, -3)
                ctx.line_to(40, 10)
                ctx.line_to(0, 6)
                ctx.close_path()
                ctx.fill()
                ctx.set_source_rgb(0.85, 0.88, 0.92)
                ctx.set_line_width(1.5)
                ctx.move_to(36, -3)
                ctx.line_to(40, 10)
                ctx.stroke()

        elif self.idle_substate == "PHONE":
            # Holding phone up
            ctx.set_source_rgb(0.12, 0.12, 0.14)
            ctx.rectangle(6, -6, 10, 4)
            ctx.fill()
            # Hand
            ctx.set_source_rgb(0.98, 0.82, 0.70)
            ctx.arc(16, -4, 2.8, 0, math.pi * 2)
            ctx.fill()
            # Smartphone
            ctx.set_source_rgb(0.2, 0.2, 0.25)
            ctx.rectangle(15, -12, 6, 10)
            ctx.fill()
            # Glowing screen
            ctx.set_source_rgb(0.4, 0.8, 1.0)
            ctx.rectangle(16, -11, 4, 8)
            ctx.fill()

        elif self.idle_substate == "ARMS_CROSSED":
            # Arms folded across chest
            ctx.set_source_rgb(0.12, 0.12, 0.14)
            ctx.rectangle(-8, -4, 16, 6)
            ctx.fill()
            ctx.set_source_rgb(0.98, 0.82, 0.70)
            ctx.arc(8, -1, 2.5, 0, math.pi * 2)
            ctx.arc(-8, -1, 2.5, 0, math.pi * 2)
            ctx.fill()

        else:
            # Natural resting arms
            ctx.set_source_rgb(0.12, 0.12, 0.14)
            ctx.rectangle(-12, -8, 4, 15)
            ctx.rectangle(8, -8, 4, 15)
            ctx.fill()
            ctx.set_source_rgb(0.98, 0.82, 0.70)
            ctx.arc(-10, 8, 2.5, 0, math.pi * 2)
            ctx.arc(10, 8, 2.5, 0, math.pi * 2)
            ctx.fill()

        ctx.restore()
