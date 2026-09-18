"""Hulk character: colossal strength with tectonic Ground Smash, concussive Thunderclap, pulsating Gamma Rage, and high parabolic leaps."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, List
from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager


class HulkCharacter(BaseCharacter):
    """The Incredible Hulk with ground smashes, concussive thunderclaps, gamma rage aura, and parabolic leaps."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="hulk")
        self.can_fly = False
        self.hitbox_radius = 48.0
        self.is_smashing = False
        self.smash_end = 0.0
        self.is_thunderclapping = False
        self.clap_end = 0.0
        self.rage_aura = 0.0
        self.rage_boost_timer = 0.0
        self.ground_cracks: List[Tuple[float, float, float]] = []  # (offset_x, offset_y, alpha)
        self.action_timer = time.time() + random.uniform(3.0, 6.0)

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("hulk_smash", "ground_smash", "attack"):
            # 1. Ground Smash: Leaps up and hammers both fists down, cracking the ground
            self.is_smashing = True
            self.smash_end = time.time() + 0.75
            self.vy = -8.0  # slight hop before violent slam down

            # Tectonic ground cracks
            self.ground_cracks.clear()
            for _ in range(8):
                ang = random.uniform(-0.8, 0.8)
                length = random.uniform(15.0, 45.0)
                self.ground_cracks.append((math.sin(ang) * length, math.cos(ang) * (length * 0.4), 1.0))

            particle_mgr.shockwave(self.x, self.y + 24, max_radius=85.0, color=(0.25, 0.88, 0.25), line_width=4.5)
            particle_mgr.shockwave(self.x, self.y + 24, max_radius=50.0, color=(0.9, 0.95, 0.3), line_width=2.5)
            particle_mgr.burst_sparks(self.x, self.y + 24, count=24, color=(0.4, 0.95, 0.2), size=3.5)
            particle_mgr.smoke_puff(self.x, self.y + 24, count=8, color=(0.45, 0.40, 0.35))
            audio_mgr.play("smash")
            return True

        elif ability_name in ("thunderclap", "clap"):
            # 2. Thunderclap: Colossal palm slam emitting concentric forward shockwave cones
            self.is_thunderclapping = True
            self.clap_end = time.time() + 0.6
            dir_mult = 1.0 if self.facing_right else -1.0
            clap_x = self.x + dir_mult * 25.0
            clap_y = self.y - 4.0

            # Concussive sonic rings
            particle_mgr.shockwave(clap_x, clap_y, max_radius=70.0, color=(0.95, 1.0, 0.85), line_width=3.5)
            particle_mgr.shockwave(clap_x + dir_mult * 20.0, clap_y, max_radius=55.0, color=(0.3, 0.9, 0.3), line_width=2.5)
            particle_mgr.burst_sparks(clap_x, clap_y, count=16, color=(0.85, 1.0, 0.5), size=2.8)
            audio_mgr.play("smash")
            return True

        elif ability_name in ("gamma_rage", "roar"):
            # 3. Gamma Rage: Roar with surging radioactive aura and temporary size boost
            self.rage_aura = 1.5
            self.rage_boost_timer = time.time() + 3.5
            particle_mgr.shockwave(self.x, self.y - 10, max_radius=75.0, color=(0.2, 0.95, 0.2), line_width=4.0)
            particle_mgr.burst_sparks(self.x, self.y - 10, count=20, color=(0.3, 1.0, 0.2), size=3.0)
            audio_mgr.play("roar")
            return True

        elif ability_name in ("super_jump", "jump"):
            # 4. Parabolic Super Leap: Massive launch across distance
            dx = target_x - self.x
            self.vx = max(-18.0, min(18.0, dx * 0.10))
            self.vy = -20.0  # Massive upward thrust
            self.state = CharacterState.JUMP
            particle_mgr.smoke_puff(self.x, self.y + 24, count=6, color=(0.45, 0.40, 0.35))
            particle_mgr.shockwave(self.x, self.y + 24, max_radius=40.0, color=(0.3, 0.85, 0.2))
            audio_mgr.play("smash")
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
        ground_y = min_y + screen_h - 70.0

        # Facing direction
        self.facing_right = (cursor_x >= self.x)

        if self.is_smashing and now >= self.smash_end:
            self.is_smashing = False

        if self.is_thunderclapping and now >= self.clap_end:
            self.is_thunderclapping = False

        if self.rage_aura > 0.05:
            self.rage_aura *= 0.95

        # Fade ground cracks
        for i in range(len(self.ground_cracks)):
            cx, cy, a = self.ground_cracks[i]
            self.ground_cracks[i] = (cx, cy, max(0.0, a - 0.015))
        self.ground_cracks = [c for c in self.ground_cracks if c[2] > 0.01]

        # Random ability triggers
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(4.0, 8.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.35:
                self.trigger_ability("ground_smash", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.65:
                self.trigger_ability("thunderclap", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.85:
                self.trigger_ability("super_jump", cursor_x, cursor_y, particle_mgr, audio_mgr)
            else:
                self.trigger_ability("gamma_rage", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Ground-based movement physics with Parabolic Super Leaps
        speed_mult = config_data.get("speed", 1.0)
        max_spd = 12.0 * speed_mult

        # Apply gravity
        if self.y < ground_y:
            self.vy += 0.95  # Heavy Titan gravity
            self.is_airborne = True
            self.state = CharacterState.JUMP
        else:
            self.y = ground_y
            if self.vy > 6.0:  # Hard landing impact!
                particle_mgr.shockwave(self.x, self.y + 24, max_radius=50.0, color=(0.35, 0.85, 0.2))
                particle_mgr.smoke_puff(self.x, self.y + 24, count=5)
                particle_mgr.burst_sparks(self.x, self.y + 24, count=10, color=(0.4, 0.9, 0.2))
                audio_mgr.play("smash")
            self.vy = 0.0
            self.is_airborne = False

        # Traversal: If target is far (>120px) and on ground, Hulk initiates a Parabolic Super Leap!
        dx = cursor_x - self.x
        dist_x = abs(dx)

        if not self.is_smashing and not self.is_thunderclapping:
            if not self.is_airborne:
                if dist_x > 140.0 and random.random() < 0.08:
                    # Launch parabolic super leap towards target!
                    self.trigger_ability("super_jump", cursor_x, cursor_y, particle_mgr, audio_mgr)
                elif dist_x > 70.0:
                    dir_x = 1.0 if dx > 0 else -1.0
                    self.vx += dir_x * (0.65 * speed_mult)
                    self.state = CharacterState.RUN if dist_x > 220.0 else CharacterState.WALK
                else:
                    self.vx *= 0.80
                    self.state = CharacterState.IDLE
            else:
                # Airborne drift
                dir_x = 1.0 if dx > 0 else -1.0
                self.vx += dir_x * 0.15

        self.vx *= 0.92
        if abs(self.vx) > max_spd:
            self.vx = (self.vx / abs(self.vx)) * max_spd

        self.x += self.vx
        self.y += self.vy

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = min(ground_y, max(min_y + 60.0, self.y))

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()

        # 1. Ground cracks under Hulk's feet
        if self.ground_cracks:
            ctx.save()
            for cx, cy, alpha in self.ground_cracks:
                ctx.set_source_rgba(0.15, 0.12, 0.10, alpha * 0.7)
                ctx.set_line_width(2.0 * alpha)
                ctx.move_to(self.x, self.y + 24)
                ctx.line_to(self.x + cx, self.y + 24 + cy)
                ctx.stroke()
            ctx.restore()

        # 2. Enraged scale boost during Gamma Rage
        current_scale = self.scale * (1.18 if time.time() < self.rage_boost_timer else 1.0)
        ctx.translate(self.x, self.y)
        ctx.scale(current_scale, current_scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # Radioactive Gamma Aura Glow
        if self.rage_aura > 0.05 or time.time() < self.rage_boost_timer:
            ctx.save()
            glow_rad = 42.0 + math.sin(self.anim_time * 8.0) * 4.0
            pat_aura = cairo.RadialGradient(0, 0, 8, 0, 0, glow_rad)
            pat_aura.add_color_stop_rgba(0.0, 0.3, 1.0, 0.3, 0.4)
            pat_aura.add_color_stop_rgba(0.7, 0.1, 0.8, 0.2, 0.2)
            pat_aura.add_color_stop_rgba(1.0, 0.0, 0.5, 0.1, 0.0)
            ctx.set_source(pat_aura)
            ctx.arc(0, 0, glow_rad, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

        # 3. Massive Muscular Legs & Torn Purple Trousers
        # Legs
        for lx in [-12, 4]:
            ctx.save()
            leg_pat = cairo.LinearGradient(lx, 12, lx + 9, 28)
            leg_pat.add_color_stop_rgb(0.0, 0.22, 0.65, 0.24)
            leg_pat.add_color_stop_rgb(1.0, 0.12, 0.42, 0.15)
            ctx.set_source(leg_pat)
            ctx.rectangle(lx, 12, 9, 16)
            ctx.fill()

            # Heavy calf muscles
            ctx.set_source_rgb(0.14, 0.46, 0.18)
            ctx.set_line_width(1.2)
            ctx.arc(lx + 4.5, 20, 4.0, 0, math.pi)
            ctx.stroke()
            ctx.restore()

        # Torn Purple Shorts with ragged hem
        shorts_pat = cairo.LinearGradient(-15, 6, 15, 18)
        shorts_pat.add_color_stop_rgb(0.0, 0.48, 0.20, 0.62)
        shorts_pat.add_color_stop_rgb(1.0, 0.30, 0.12, 0.40)
        ctx.set_source(shorts_pat)
        ctx.rectangle(-15, 6, 30, 13)
        ctx.fill()

        # Ragged torn cloth fringes
        ctx.set_source_rgb(0.25, 0.08, 0.35)
        ctx.new_path()
        for x_step in range(-15, 16, 3):
            ctx.line_to(x_step, 19 + (abs(x_step) % 4))
        ctx.stroke()

        # 4. Colossal Muscular Torso & Sculpted Pectorals
        torso_pat = cairo.LinearGradient(-18, -14, 18, 12)
        torso_pat.add_color_stop_rgb(0.0, 0.26, 0.72, 0.28)
        torso_pat.add_color_stop_rgb(0.5, 0.18, 0.58, 0.22)
        torso_pat.add_color_stop_rgb(1.0, 0.10, 0.38, 0.14)
        ctx.set_source(torso_pat)
        ctx.new_path()
        ctx.move_to(-18, -12)
        ctx.line_to(18, -12)
        ctx.line_to(14, 10)
        ctx.line_to(-14, 10)
        ctx.close_path()
        ctx.fill()

        # Sculpted Pectoral Plates
        ctx.set_source_rgba(0.08, 0.28, 0.10, 0.55)
        ctx.set_line_width(2.0)
        ctx.arc(-8, -4, 7, 0, math.pi)
        ctx.stroke()
        ctx.arc(8, -4, 7, 0, math.pi)
        ctx.stroke()
        # Abdominal division lines
        ctx.move_to(0, -4)
        ctx.line_to(0, 8)
        ctx.move_to(-6, 2)
        ctx.line_to(6, 2)
        ctx.stroke()

        # 5. Massive Arms, Shoulders & Action Poses
        if self.is_smashing:
            # Slam Pose: Both giant fists raised high overhead ready to slam!
            for ax in [-18, 8]:
                ctx.save()
                arm_pat = cairo.LinearGradient(ax, -28, ax + 10, -10)
                arm_pat.add_color_stop_rgb(0.0, 0.26, 0.72, 0.28)
                arm_pat.add_color_stop_rgb(1.0, 0.12, 0.42, 0.15)
                ctx.set_source(arm_pat)
                ctx.rectangle(ax, -28, 10, 20)
                ctx.fill()
                # Giant clenched fists
                ctx.arc(ax + 5, -28, 8.0, 0, 2 * math.pi)
                ctx.fill()
                ctx.restore()

        elif self.is_thunderclapping:
            # Thunderclap Pose: Both arms slammed forward together
            ctx.save()
            arm_pat = cairo.LinearGradient(8, -8, 26, -2)
            arm_pat.add_color_stop_rgb(0.0, 0.26, 0.72, 0.28)
            arm_pat.add_color_stop_rgb(1.0, 0.12, 0.42, 0.15)
            ctx.set_source(arm_pat)
            ctx.rectangle(10, -9, 16, 8)
            ctx.fill()
            # Interlocked giant hands
            ctx.arc(26, -5, 8.5, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

        elif self.state == CharacterState.JUMP:
            # Leap Pose: Muscular arms flexed upward with fists clenched
            for ax, sign in [(-22, -1), (12, 1)]:
                ctx.save()
                arm_pat = cairo.LinearGradient(ax, -16, ax + 10, 8)
                arm_pat.add_color_stop_rgb(0.0, 0.26, 0.72, 0.28)
                arm_pat.add_color_stop_rgb(1.0, 0.12, 0.42, 0.15)
                ctx.set_source(arm_pat)
                ctx.rectangle(ax, -16, 10, 22)
                ctx.fill()
                ctx.arc(ax + 5, 6, 7.5, 0, 2 * math.pi)
                ctx.fill()
                ctx.restore()
        else:
            # Standing / Running: Giant arms hanging with clenched fists
            for ax in [-24, 14]:
                ctx.save()
                arm_pat = cairo.LinearGradient(ax, -10, ax + 10, 16)
                arm_pat.add_color_stop_rgb(0.0, 0.26, 0.72, 0.28)
                arm_pat.add_color_stop_rgb(1.0, 0.12, 0.42, 0.15)
                ctx.set_source(arm_pat)
                ctx.rectangle(ax, -10, 10, 24)
                ctx.fill()
                # Giant Fists
                ctx.arc(ax + 5, 15, 7.5, 0, 2 * math.pi)
                ctx.fill()
                ctx.restore()

        # 6. Head, Furrowed Brow & Radioactive Glowing Eyes
        ctx.save()
        head_pat = cairo.RadialGradient(0, -18, 2, 0, -18, 12)
        head_pat.add_color_stop_rgb(0.0, 0.28, 0.74, 0.30)
        head_pat.add_color_stop_rgb(1.0, 0.14, 0.46, 0.18)
        ctx.set_source(head_pat)
        ctx.arc(0, -18, 12.5, 0, 2 * math.pi)
        ctx.fill()

        # Shaggy Jet-Black / Dark Green Hair
        ctx.set_source_rgb(0.06, 0.10, 0.08)
        ctx.arc(0, -22, 12.5, math.pi, 2 * math.pi)
        ctx.fill()
        # Spiky hair tufts
        for hx in [-9, -4, 0, 4, 8]:
            ctx.new_path()
            ctx.move_to(hx - 2, -22)
            ctx.line_to(hx, -26)
            ctx.line_to(hx + 2, -22)
            ctx.close_path()
            ctx.fill()

        # Enraged Glowing Eyes
        ctx.set_source_rgb(0.3, 1.0, 0.2)  # Glowing radioactive lime
        ctx.arc(-4, -18, 2.4, 0, 2 * math.pi)
        ctx.arc(4, -18, 2.4, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgb(1.0, 1.0, 0.7)
        ctx.arc(-4, -18, 1.0, 0, 2 * math.pi)
        ctx.arc(4, -18, 1.0, 0, 2 * math.pi)
        ctx.fill()

        # Heavy Furrowed Brow
        ctx.set_source_rgb(0.08, 0.28, 0.10)
        ctx.set_line_width(2.2)
        ctx.move_to(-9, -21)
        ctx.line_to(-1, -19)
        ctx.line_to(1, -19)
        ctx.line_to(9, -21)
        ctx.stroke()

        # Enraged Jaws / Teeth
        ctx.set_source_rgb(0.08, 0.28, 0.10)
        ctx.rectangle(-5, -13, 10, 3)
        ctx.fill()
        ctx.set_source_rgb(0.95, 0.95, 0.90)
        for tx in [-3, -1, 1, 3]:
            ctx.rectangle(tx - 0.5, -13, 1.2, 2.0)
            ctx.fill()

        ctx.restore()
        ctx.restore()
