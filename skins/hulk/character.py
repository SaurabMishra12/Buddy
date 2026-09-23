"""Hulk character: colossal strength with tectonic Ground Smash, concussive Thunderclap, pulsating Gamma Rage, and high parabolic leaps."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, List, Optional
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
        self.nav_target: Optional[Tuple[float, float]] = None
        self.nav_timer = 0.0
        self.action_timer = time.time() + random.uniform(3.0, 6.0)

    def launch_super_leap(
        self,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> None:
        """Launch a massive parabolic super leap towards the destination."""
        dx = target_x - self.x
        dist_x = abs(dx)
        dir_x = 1.0 if dx >= 0 else -1.0
        self.facing_right = (dir_x > 0)
        # Parabolic ballistic physics: height scales with distance
        self.vy = min(-16.0, max(-28.0, -18.0 - dist_x * 0.035))
        time_air = (2.0 * abs(self.vy)) / 0.95
        self.vx = dx / max(8.0, time_air)
        self.vx = max(-22.0, min(22.0, self.vx))
        self.state = CharacterState.JUMP
        self.is_airborne = True
        particle_mgr.shockwave(self.x, self.y + 24, max_radius=60.0, color=(0.3, 0.9, 0.2), line_width=4.0)
        particle_mgr.smoke_puff(self.x, self.y + 24, count=8, color=(0.45, 0.40, 0.35))
        audio_mgr.play("roar")

    def nav_to(self, target_x: float, target_y: float) -> None:
        """Command Hulk to traverse to point via massive parabolic super leaps."""
        self.nav_target = (target_x, target_y)
        self.is_smashing = False
        self.is_thunderclapping = False
        self.nav_timer = time.time()
        self.facing_right = (target_x >= self.x)
        # Trajectory launched on next update frame

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
            self.launch_super_leap(target_x, target_y, particle_mgr, audio_mgr)
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
                self.ground_cracks.clear()
                for _ in range(6):
                    ang = random.uniform(-0.8, 0.8)
                    length = random.uniform(12.0, 35.0)
                    self.ground_cracks.append((math.sin(ang) * length, math.cos(ang) * (length * 0.4), 1.0))
                particle_mgr.shockwave(self.x, self.y + 24, max_radius=55.0, color=(0.35, 0.85, 0.2), line_width=3.5)
                particle_mgr.smoke_puff(self.x, self.y + 24, count=6)
                if audio_mgr:
                    audio_mgr.play("smash")
            self.vy = 0.0
            self.is_airborne = False

        # 1. AUTONOMOUS BALLISTIC PARABOLIC SUPER LEAP NAVIGATION
        if self.nav_target is not None:
            tx, ty = self.nav_target
            dx = tx - self.x
            dist_x = abs(dx)
            self.facing_right = (dx >= 0.0)

            if not self.is_airborne and self.y >= ground_y - 4.0:
                if dist_x < 35.0:
                    # Reached target destination!
                    self.nav_target = None
                    self.state = CharacterState.IDLE
                    self.vx = 0.0
                    self.vy = 0.0
                    particle_mgr.shockwave(self.x, self.y + 24, max_radius=60.0, color=(0.25, 0.88, 0.25), line_width=4.5)
                    particle_mgr.smoke_puff(self.x, self.y + 24, count=6)
                    audio_mgr.play("smash")
                else:
                    # Launch massive parabolic super leap directly to target!
                    self.launch_super_leap(tx, ty, particle_mgr, audio_mgr)
            else:
                # Mid-air ballistic drift towards target
                target_drift = (1.0 if dx > 0 else -1.0) * min(20.0, max(4.0, dist_x * 0.12))
                self.vx += (target_drift - self.vx) * 0.08

        # 2. STANDARD GROUND WANDER (When not navigating)
        elif not self.is_smashing and not self.is_thunderclapping:
            dx = cursor_x - self.x
            dist_x = abs(dx)
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

        # Dynamic 3/4 Colossal Titan Locomotion
        spd = abs(self.vx)
        is_moving = (self.state in (CharacterState.RUN, CharacterState.WALK) or spd > 1.2) and not (self.is_smashing or self.is_thunderclapping)
        walk_cycle = self.anim_time * (10.5 if self.state == CharacterState.RUN else 7.0)

        if is_moving:
            bob = -abs(math.sin(walk_cycle)) * 3.2
            sway = math.sin(walk_cycle) * 0.04
            ctx.translate(0, bob)
            ctx.rotate(0.24 + sway)  # Heavy hunched ~14° forward charge

        # Hulk Color Palette
        HULK_GREEN = (0.24, 0.68, 0.26)
        HULK_GREEN_DARK = (0.12, 0.38, 0.14)
        HULK_GREEN_DEEP = (0.07, 0.24, 0.09)
        SHORTS_PURPLE = (0.46, 0.18, 0.60)
        SHORTS_DARK = (0.26, 0.10, 0.36)

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

        # -------------------------------------------------------------
        # 3. TREE-TRUNK LEGS & SHREDDED PURPLE TROUSERS (3/4 Titan Locomotion)
        # -------------------------------------------------------------
        ctx.save()
        if is_moving:
            sin_walk = math.sin(walk_cycle)

            # FAR TREE-TRUNK LEG (Driving in counter-cadence)
            ctx.set_source_rgb(*HULK_GREEN_DARK)
            ctx.set_line_width(9.5)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            far_hip_x, far_hip_y = -6.0, 11.0
            far_knee_x = far_hip_x - sin_walk * 11.0 - 2.0
            far_knee_y = far_hip_y + 9.5 + max(0.0, sin_walk * 4.0)
            far_foot_x = far_knee_x - sin_walk * 8.0 - 2.5
            far_foot_y = far_knee_y + 11.0 - max(0.0, -sin_walk * 4.0)

            ctx.move_to(far_hip_x, far_hip_y)
            ctx.line_to(far_knee_x, far_knee_y)
            ctx.line_to(far_foot_x, far_foot_y)
            ctx.stroke()
            # Far heavy foot & toes
            ctx.arc(far_foot_x, far_foot_y, 5.0, 0, 2 * math.pi)
            ctx.fill()

            # NEAR TREE-TRUNK LEG (Powerful forward knee drive)
            ctx.set_source_rgb(*HULK_GREEN)
            ctx.set_line_width(10.5)
            near_hip_x, near_hip_y = 5.0, 11.0
            near_knee_x = near_hip_x + sin_walk * 13.0 + 2.0
            near_knee_y = near_hip_y + 9.0 - max(0.0, sin_walk * 5.5)
            near_foot_x = near_knee_x + sin_walk * 9.0 + (3.5 if sin_walk > 0 else -2.5)
            near_foot_y = near_knee_y + 11.0 + max(0.0, -sin_walk * 3.5)

            ctx.move_to(near_hip_x, near_hip_y)
            ctx.line_to(near_knee_x, near_knee_y)
            ctx.line_to(near_foot_x, near_foot_y)
            ctx.stroke()
            # Near heavy foot & splayed toes
            ctx.arc(near_foot_x, near_foot_y, 5.5, 0, 2 * math.pi)
            ctx.fill()
            ctx.set_source_rgb(*HULK_GREEN_DARK)
            ctx.set_line_width(1.5)
            for tox in range(-3, 4, 3):
                ctx.move_to(near_foot_x + tox, near_foot_y + 2)
                ctx.line_to(near_foot_x + tox + 1, near_foot_y + 5)
                ctx.stroke()

        elif self.state == CharacterState.JUMP:
            # Airborne flexed legs
            ctx.set_source_rgb(*HULK_GREEN)
            ctx.set_line_width(10.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-8, 11)
            ctx.line_to(-14, 18)
            ctx.line_to(-10, 25)
            ctx.stroke()
            ctx.move_to(8, 11)
            ctx.line_to(14, 18)
            ctx.line_to(10, 25)
            ctx.stroke()

        else:
            # Standing 3/4 Titan Stance (Wide, immovable stance)
            ctx.set_source_rgb(*HULK_GREEN_DARK)
            ctx.set_line_width(9.5)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-7, 11)
            ctx.line_to(-9, 20)
            ctx.line_to(-11, 28)
            ctx.stroke()
            ctx.arc(-11, 28, 5.0, 0, 2 * math.pi)
            ctx.fill()

            ctx.set_source_rgb(*HULK_GREEN)
            ctx.set_line_width(10.5)
            ctx.move_to(5, 11)
            ctx.line_to(7, 20)
            ctx.line_to(9, 28)
            ctx.stroke()
            ctx.arc(9, 28, 5.5, 0, 2 * math.pi)
            ctx.fill()
        ctx.restore()

        # Torn Purple Shorts with shredded hems in 3/4
        ctx.save()
        shorts_pat = cairo.LinearGradient(0, 6, 0, 18)
        shorts_pat.add_color_stop_rgb(0.0, *SHORTS_PURPLE)
        shorts_pat.add_color_stop_rgb(1.0, *SHORTS_DARK)
        ctx.set_source(shorts_pat)
        ctx.new_path()
        ctx.move_to(-15, 6)
        ctx.line_to(15, 6)
        ctx.line_to(14, 16)
        ctx.line_to(-14, 16)
        ctx.close_path()
        ctx.fill()

        # Ragged torn fringes fluttering
        ctx.set_source_rgb(0.20, 0.06, 0.28)
        ctx.set_line_width(1.6)
        ctx.new_path()
        for x_step in range(-15, 16, 3):
            ctx.move_to(x_step, 16)
            ctx.line_to(x_step + 1.2, 19 + (abs(x_step) % 4))
            ctx.line_to(x_step + 3.0, 16)
        ctx.stroke()
        ctx.restore()

        # -------------------------------------------------------------
        # 4. COLOSSAL 3/4 HUNCHED TITAN TORSO & MASSIVE TRAPS
        # -------------------------------------------------------------
        ctx.save()
        # Massive Trapezius Hump rising behind neck
        ctx.set_source_rgb(*HULK_GREEN_DARK)
        ctx.new_path()
        ctx.move_to(-16, -14)
        ctx.curve_to(-14, -25, 2, -24, 7, -15)
        ctx.close_path()
        ctx.fill()

        # Colossal Muscular Torso angled in 3/4 view
        torso_pat = cairo.LinearGradient(-18, -14, 18, 12)
        torso_pat.add_color_stop_rgb(0.0, 0.26, 0.72, 0.28)
        torso_pat.add_color_stop_rgb(0.5, 0.18, 0.58, 0.22)
        torso_pat.add_color_stop_rgb(1.0, 0.10, 0.38, 0.14)
        ctx.set_source(torso_pat)
        ctx.new_path()
        ctx.move_to(-17, -12)
        ctx.line_to(16, -12)
        ctx.line_to(13, 9)
        ctx.line_to(-13, 9)
        ctx.close_path()
        ctx.fill()

        # Sculpted 3/4 Pectoral Slabs
        ctx.set_source_rgba(*HULK_GREEN_DEEP, 0.60)
        ctx.set_line_width(2.0)
        # Near prominent pec
        ctx.arc(4, -4, 7.5, 0, math.pi)
        ctx.stroke()
        # Far foreshortened pec
        ctx.arc(-8, -4, 6.0, 0, math.pi)
        ctx.stroke()
        # Abdominal division lines
        ctx.move_to(0, -4)
        ctx.line_to(0, 8)
        ctx.move_to(-5, 2)
        ctx.line_to(5, 2)
        ctx.stroke()
        ctx.restore()

        # -------------------------------------------------------------
        # 5. MASSIVE SWINGING BOULDER ARMS & FISTS
        # -------------------------------------------------------------
        ctx.save()
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

        elif is_moving:
            # HEAVY SWINGING BOULDER FISTS
            arm_sin = math.sin(walk_cycle)

            # TRAILING ARM (Swinging heavy backward arc)
            ctx.set_source_rgb(*HULK_GREEN_DARK)
            ctx.set_line_width(9.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            far_elbow_x = -10.0 - arm_sin * 10.0
            far_elbow_y = -3.0 + abs(arm_sin) * 4.0
            far_fist_x = far_elbow_x - arm_sin * 8.0
            far_fist_y = far_elbow_y + 10.0 - arm_sin * 4.0
            ctx.move_to(-10, -8)
            ctx.line_to(far_elbow_x, far_elbow_y)
            ctx.line_to(far_fist_x, far_fist_y)
            ctx.stroke()
            # Trailing boulder fist
            ctx.arc(far_fist_x, far_fist_y, 7.5, 0, 2 * math.pi)
            ctx.fill()

            # LEADING ARM (Swinging heavy forward destructive arc)
            ctx.set_source_rgb(*HULK_GREEN)
            ctx.set_line_width(10.5)
            near_elbow_x = 10.0 + arm_sin * 10.0
            near_elbow_y = -3.0 + abs(arm_sin) * 4.0
            near_fist_x = near_elbow_x + arm_sin * 9.0 + 4.0
            near_fist_y = near_elbow_y + 8.0 - arm_sin * 5.0
            ctx.move_to(9, -8)
            ctx.line_to(near_elbow_x, near_elbow_y)
            ctx.line_to(near_fist_x, near_fist_y)
            ctx.stroke()
            # Leading massive boulder fist
            ctx.arc(near_fist_x, near_fist_y, 8.5, 0, 2 * math.pi)
            ctx.fill()
            # Knuckle muscle definition
            ctx.set_source_rgb(*HULK_GREEN_DEEP)
            ctx.set_line_width(1.6)
            ctx.arc(near_fist_x, near_fist_y, 5.0, -0.8, 1.2)
            ctx.stroke()

        else:
            # Standing / Idle relaxed massive arms
            breath = math.sin(self.anim_time * 3.0) * 1.5
            ctx.set_source_rgb(*HULK_GREEN_DARK)
            ctx.set_line_width(9.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-12, -8)
            ctx.line_to(-18, 4)
            ctx.line_to(-15, 16 + breath)
            ctx.stroke()
            ctx.arc(-15, 16 + breath, 7.2, 0, 2 * math.pi)
            ctx.fill()

            ctx.set_source_rgb(*HULK_GREEN)
            ctx.set_line_width(10.0)
            ctx.move_to(11, -8)
            ctx.line_to(17, 4)
            ctx.line_to(14, 16 + breath)
            ctx.stroke()
            ctx.arc(14, 16 + breath, 8.0, 0, 2 * math.pi)
            ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 6. SNARLING 3/4 TITAN HEAD, UNDERBITE FANGS & RADIOACTIVE EYES
        # -------------------------------------------------------------
        ctx.save()
        ctx.translate(3.5, -18)  # Head thrust forward from trapezius

        # Head Base in 3/4 perspective
        head_pat = cairo.RadialGradient(2, -1, 2, 0, 0, 13)
        head_pat.add_color_stop_rgb(0.0, 0.28, 0.74, 0.30)
        head_pat.add_color_stop_rgb(1.0, 0.14, 0.46, 0.18)
        ctx.set_source(head_pat)
        ctx.arc(0, 0, 12.0, 0, 2 * math.pi)
        ctx.fill()

        # Shaggy Jet-Black / Dark Green Hair swept back
        ctx.set_source_rgb(0.06, 0.10, 0.08)
        ctx.arc(-1, -4, 12.0, math.pi * 0.9, math.pi * 2.05)
        ctx.fill()
        # Spiky hair tufts
        for hx in [-9, -4, 1, 6]:
            ctx.new_path()
            ctx.move_to(hx - 2, -4)
            ctx.line_to(hx, -9)
            ctx.line_to(hx + 2, -4)
            ctx.close_path()
            ctx.fill()

        # Heavy Furrowed Brow Ridge jutting forward
        ctx.set_source_rgb(*HULK_GREEN_DEEP)
        ctx.set_line_width(2.5)
        ctx.move_to(-7, -3)
        ctx.line_to(1, -1)
        ctx.line_to(7, -3)
        ctx.stroke()

        # Enraged Radioactive Lime Eyes (3/4 angle)
        # Near eye (prominent)
        ctx.set_source_rgb(0.3, 1.0, 0.2)
        ctx.arc(4, 0, 2.4, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgb(1.0, 1.0, 0.7)
        ctx.arc(4, 0, 1.0, 0, 2 * math.pi)
        ctx.fill()
        # Far eye (foreshortened)
        ctx.set_source_rgb(0.3, 1.0, 0.2)
        ctx.arc(-3, 0, 1.8, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgb(1.0, 1.0, 0.7)
        ctx.arc(-3, 0, 0.8, 0, 2 * math.pi)
        ctx.fill()

        # Snarling Jutting Lower Jaw & Teeth in 3/4 profile
        ctx.set_source_rgb(*HULK_GREEN_DEEP)
        ctx.new_path()
        ctx.move_to(-4, 5)
        ctx.line_to(6, 5)
        ctx.line_to(7, 9)
        ctx.line_to(1, 10.5)
        ctx.line_to(-4, 9)
        ctx.close_path()
        ctx.fill()

        # White Underbite Fangs
        ctx.set_source_rgb(0.95, 0.95, 0.90)
        # Big canine fangs pointing UP from lower jaw
        ctx.new_path()
        ctx.move_to(4.5, 8.5)
        ctx.line_to(5.5, 4.5)
        ctx.line_to(6.5, 8.5)
        ctx.close_path()
        ctx.fill()
        ctx.new_path()
        ctx.move_to(-1.5, 8.5)
        ctx.line_to(-0.5, 5.0)
        ctx.line_to(0.5, 8.5)
        ctx.close_path()
        ctx.fill()
        # Smaller incisors
        for tx in [1.5, 3.0]:
            ctx.rectangle(tx, 6.0, 1.0, 2.0)
            ctx.fill()

        ctx.restore()
        ctx.restore()
