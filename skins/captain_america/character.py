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
        self.is_hero_posing = False
        self.hero_pose_end = 0.0
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
        elif ability_name in ("hero_pose", "victory", "pose", "salute"):
            self.is_hero_posing = True
            self.hero_pose_end = time.time() + 2.5
            self.state = CharacterState.VICTORY
            self.vx = 0.0
            particle_mgr.shockwave(self.x, self.y, max_radius=65.0, color=(0.95, 0.85, 0.25), line_width=3.5)
            particle_mgr.burst_sparks(self.x, self.y - 14, count=25, color=(1.0, 0.90, 0.3), size=3.2)
            particle_mgr.burst_sparks(self.x, self.y - 14, count=15, color=(0.2, 0.5, 1.0), size=2.5)
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
        ground_y = min_y + screen_h - 65.0

        # Facing direction
        self.facing_right = (cursor_x >= self.x)

        if self.is_blocking and now >= self.block_end:
            self.is_blocking = False

        if self.is_hero_posing:
            if now >= self.hero_pose_end:
                self.is_hero_posing = False
                self.state = CharacterState.IDLE
            else:
                self.state = CharacterState.VICTORY
                self.vx *= 0.60
                if random.random() < 0.25:
                    particle_mgr.burst_sparks(self.x, self.y - 6, count=1, color=(1.0, 0.88, 0.3), size=2.0)

        # Random personality events
        if now >= self.action_timer and activity > 0.1 and not self.is_hero_posing:
            self.action_timer = now + random.uniform(5.0, 9.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.45:
                self.trigger_ability("shield_throw", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.70:
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

        if self.is_hero_posing:
            # Stand firmly planted during Hero Pose
            self.vx *= 0.50
            self.state = CharacterState.VICTORY
        elif dist_x > 45.0:
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

        # Dynamic running stride and forward soldier charge lean
        spd = abs(self.vx)
        is_running = (self.state == CharacterState.RUN or spd > 2.0) and not self.is_hero_posing

        run_cycle = self.anim_time * 12.0
        if is_running:
            bob = -abs(math.sin(run_cycle)) * 2.5
            ctx.translate(0, bob)
            ctx.rotate(0.22)  # ~13° super-soldier forward combat charge

        # Color Palette
        CAP_BLUE = (0.12, 0.26, 0.58)
        CAP_BLUE_DARK = (0.07, 0.15, 0.36)
        CAP_RED = (0.84, 0.12, 0.16)
        CAP_RED_DARK = (0.60, 0.08, 0.10)
        CAP_WHITE = (0.96, 0.96, 0.98)
        LEATHER_BROWN = (0.34, 0.20, 0.12)
        LEATHER_DARK = (0.22, 0.12, 0.07)
        BUCKLE_GOLD = (0.86, 0.74, 0.22)
        FLESH_TONE = (0.94, 0.78, 0.66)

        # -------------------------------------------------------------
        # 1. LEGS & CRIMSON COMBAT BOOTS (3/4 Soldier Stride)
        # -------------------------------------------------------------
        ctx.save()
        if self.is_hero_posing:
            # Heroic Wide Planted Stance
            pat_pants = cairo.LinearGradient(0, 10, 0, 26)
            pat_pants.add_color_stop_rgb(0.0, *CAP_BLUE)
            pat_pants.add_color_stop_rgb(1.0, *CAP_BLUE_DARK)
            ctx.set_source(pat_pants)
            ctx.rectangle(-10, 12, 5.5, 14)
            ctx.rectangle(4.5, 12, 5.5, 14)
            ctx.fill()
            # Crimson Combat Boots with Tread
            ctx.set_source_rgb(*CAP_RED)
            ctx.rectangle(-11, 22, 6.5, 7)
            ctx.rectangle(3.5, 22, 6.5, 7)
            ctx.fill()
            ctx.set_source_rgb(0.20, 0.05, 0.05)
            ctx.rectangle(-11, 27, 6.5, 2)
            ctx.rectangle(3.5, 27, 6.5, 2)
            ctx.fill()

        elif is_running:
            sin_stride = math.sin(run_cycle)

            # FAR LEG (Darker for depth, driving back in counter-cadence)
            ctx.set_source_rgb(*CAP_BLUE_DARK)
            ctx.set_line_width(6.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            far_hip_x, far_hip_y = -4.0, 11.0
            far_knee_x = far_hip_x - sin_stride * 9.0 - 1.5
            far_knee_y = far_hip_y + 9.0 + max(0.0, sin_stride * 3.5)
            far_foot_x = far_knee_x - sin_stride * 7.0 - 2.0
            far_foot_y = far_knee_y + 10.0 - max(0.0, -sin_stride * 4.0)

            ctx.move_to(far_hip_x, far_hip_y)
            ctx.line_to(far_knee_x, far_knee_y)
            ctx.line_to(far_foot_x, far_foot_y)
            ctx.stroke()
            # Far crimson combat boot
            ctx.set_source_rgb(*CAP_RED_DARK)
            ctx.set_line_width(5.8)
            ctx.move_to(far_knee_x + (far_foot_x - far_knee_x) * 0.4, far_knee_y + (far_foot_y - far_knee_y) * 0.4)
            ctx.line_to(far_foot_x, far_foot_y)
            ctx.line_to(far_foot_x + (2.0 if sin_stride > 0 else -1.5), far_foot_y + 1.8)
            ctx.stroke()

            # NEAR LEG (High driving soldier knee with reinforced knee pad)
            ctx.set_source_rgb(*CAP_BLUE)
            ctx.set_line_width(6.8)
            near_hip_x, near_hip_y = 4.0, 11.0
            near_knee_x = near_hip_x + sin_stride * 11.0 + 2.0
            near_knee_y = near_hip_y + 8.5 - max(0.0, sin_stride * 5.0)
            near_foot_x = near_knee_x + sin_stride * 8.0 + (3.0 if sin_stride > 0 else -2.0)
            near_foot_y = near_knee_y + 10.0 + max(0.0, -sin_stride * 3.5)

            ctx.move_to(near_hip_x, near_hip_y)
            ctx.line_to(near_knee_x, near_knee_y)
            ctx.line_to(near_foot_x, near_foot_y)
            ctx.stroke()
            # Tactical Knee Pad
            ctx.set_source_rgb(*CAP_BLUE_DARK)
            ctx.arc(near_knee_x, near_knee_y, 3.4, 0, 2 * math.pi)
            ctx.fill()
            # Near crimson combat boot
            ctx.set_source_rgb(*CAP_RED)
            ctx.set_line_width(6.4)
            ctx.move_to(near_knee_x + (near_foot_x - near_knee_x) * 0.4, near_knee_y + (near_foot_y - near_knee_y) * 0.4)
            ctx.line_to(near_foot_x, near_foot_y)
            ctx.line_to(near_foot_x + 3.0, near_foot_y + 1.5)
            ctx.stroke()
            # Tread sole
            ctx.set_source_rgb(0.20, 0.05, 0.05)
            ctx.set_line_width(1.8)
            ctx.move_to(near_foot_x - 2.0, near_foot_y + 2.0)
            ctx.line_to(near_foot_x + 4.0, near_foot_y + 2.0)
            ctx.stroke()

        else:
            # Standing 3/4 Soldier Ready Stance
            pat_pants = cairo.LinearGradient(0, 10, 0, 26)
            pat_pants.add_color_stop_rgb(0.0, *CAP_BLUE)
            pat_pants.add_color_stop_rgb(1.0, *CAP_BLUE_DARK)
            # Far Leg
            ctx.set_source_rgb(*CAP_BLUE_DARK)
            ctx.set_line_width(6.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-5, 11)
            ctx.line_to(-7, 20)
            ctx.line_to(-8, 27)
            ctx.stroke()
            ctx.set_source_rgb(*CAP_RED_DARK)
            ctx.set_line_width(5.8)
            ctx.move_to(-7.5, 22)
            ctx.line_to(-8.5, 27)
            ctx.line_to(-10, 28)
            ctx.stroke()

            # Near Leg
            ctx.set_source_rgb(*CAP_BLUE)
            ctx.set_line_width(6.8)
            ctx.move_to(3, 11)
            ctx.line_to(5, 20)
            ctx.line_to(6, 27)
            ctx.stroke()
            ctx.set_source_rgb(*CAP_RED)
            ctx.set_line_width(6.4)
            ctx.move_to(5.5, 22)
            ctx.line_to(6.5, 27)
            ctx.line_to(9, 28)
            ctx.stroke()
        ctx.restore()

        # -------------------------------------------------------------
        # 2. TACTICAL TORSO WITH 3/4 ABDOMINAL ARMOR STRIPES
        # -------------------------------------------------------------
        ctx.save()
        # Navy blue tactical chest plate angled in 3/4
        pat_chest = cairo.LinearGradient(2, -12, 2, 12)
        pat_chest.add_color_stop_rgb(0.0, 0.16, 0.34, 0.68)
        pat_chest.add_color_stop_rgb(1.0, 0.08, 0.18, 0.42)
        ctx.set_source(pat_chest)
        ctx.new_path()
        ctx.move_to(-10, -12)
        ctx.line_to(10, -12)
        ctx.line_to(12, 2)
        ctx.line_to(10, 11)
        ctx.line_to(-9, 11)
        ctx.line_to(-11, 2)
        ctx.close_path()
        ctx.fill()

        # Red & White Tactical Stripes on Abdomen (Arced in 3/4 perspective)
        stripe_cols = [CAP_RED, CAP_WHITE, CAP_RED, CAP_WHITE, CAP_RED]
        for i, col in enumerate(stripe_cols):
            ctx.set_source_rgb(*col)
            sx = -8.0 + i * 3.6
            ctx.rectangle(sx, 2, 3.2, 9)
            ctx.fill()

        # Brown Leather Utility Belt & Tactical Pouches
        ctx.set_source_rgb(*LEATHER_BROWN)
        ctx.rectangle(-10, 10.5, 21, 3.5)
        ctx.fill()
        # Brass Belt Buckle centered in 3/4
        ctx.set_source_rgb(*BUCKLE_GOLD)
        ctx.rectangle(-1.5, 10, 4.5, 4.5)
        ctx.fill()
        # Side tactical equipment pouches
        ctx.set_source_rgb(*LEATHER_DARK)
        ctx.rectangle(-8.5, 10.5, 3.2, 3.5)
        ctx.rectangle(6.5, 10.5, 3.2, 3.5)
        ctx.fill()

        # White Star Insignia on Upper Chest
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.new_path()
        star_cx, star_cy = 1.0, -5.0
        r_out = 5.0
        r_in = 2.2
        for i in range(5):
            ang = -math.pi / 2 + i * (2 * math.pi / 5)
            x1 = star_cx + math.cos(ang) * r_out
            y1 = star_cy + math.sin(ang) * r_out
            if i == 0:
                ctx.move_to(x1, y1)
            else:
                ctx.line_to(x1, y1)
            ang_in = ang + (math.pi / 5)
            x2 = star_cx + math.cos(ang_in) * r_in
            y2 = star_cy + math.sin(ang_in) * r_in
            ctx.line_to(x2, y2)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 3. ARMS & TACTICAL CRIMSON GAUNTLETS
        # -------------------------------------------------------------
        ctx.save()
        if self.is_hero_posing:
            # Right Arm in Crisp Military Salute to Helmet Brow
            ctx.set_source_rgb(*CAP_BLUE)
            ctx.set_line_width(4.5)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.new_path()
            ctx.move_to(10, -6)
            ctx.line_to(16, -14)
            ctx.line_to(7, -19)
            ctx.stroke()
            # Red Combat Gauntlet on Salute Hand
            ctx.set_source_rgb(*CAP_RED)
            ctx.arc(7, -19, 3.2, 0, 2 * math.pi)
            ctx.fill()

        elif is_running:
            # RUNNING SOLDIER ARM MOTION
            arm_sin = math.sin(run_cycle)

            # Trailing Arm (pumping backward in soldier cadence)
            ctx.set_source_rgb(*CAP_BLUE_DARK)
            ctx.set_line_width(5.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            far_arm_x = -7.0 - arm_sin * 8.0
            far_arm_y = -3.0 + abs(arm_sin) * 4.0
            far_hand_x = far_arm_x - arm_sin * 6.0
            far_hand_y = far_arm_y + 6.0 - arm_sin * 3.0
            ctx.move_to(-7, -7)
            ctx.line_to(far_arm_x, far_arm_y)
            ctx.line_to(far_hand_x, far_hand_y)
            ctx.stroke()
            # Trailing red combat gauntlet
            ctx.set_source_rgb(*CAP_RED_DARK)
            ctx.arc(far_hand_x, far_hand_y, 3.2, 0, 2 * math.pi)
            ctx.fill()

            # Leading Arm (if shield is thrown, pumps forward with clenched fist)
            if self.shield.state != "HELD":
                ctx.set_source_rgb(*CAP_BLUE)
                ctx.set_line_width(5.8)
                near_arm_x = 8.0 + arm_sin * 8.0
                near_arm_y = -3.0 + abs(arm_sin) * 3.0
                near_hand_x = near_arm_x + arm_sin * 7.0 + 3.0
                near_hand_y = near_arm_y - 3.0 - arm_sin * 4.0
                ctx.move_to(7, -7)
                ctx.line_to(near_arm_x, near_arm_y)
                ctx.line_to(near_hand_x, near_hand_y)
                ctx.stroke()
                ctx.set_source_rgb(*CAP_RED)
                ctx.arc(near_hand_x, near_hand_y, 3.5, 0, 2 * math.pi)
                ctx.fill()

        else:
            # Standing / Idle arms
            ctx.set_source_rgb(*CAP_BLUE_DARK)
            ctx.set_line_width(5.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-8, -7)
            ctx.line_to(-14, 2)
            ctx.line_to(-12, 10)
            ctx.stroke()
            ctx.set_source_rgb(*CAP_RED_DARK)
            ctx.arc(-12, 10, 3.0, 0, 2 * math.pi)
            ctx.fill()

            if self.shield.state != "HELD" and not self.is_blocking:
                ctx.set_source_rgb(*CAP_BLUE)
                ctx.set_line_width(5.5)
                ctx.move_to(8, -7)
                ctx.line_to(13, 2)
                ctx.line_to(11, 10)
                ctx.stroke()
                ctx.set_source_rgb(*CAP_RED)
                ctx.arc(11, 10, 3.2, 0, 2 * math.pi)
                ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 4. 3/4 COWL HELMET WITH EMBOSSED 'A' AND WINGS
        # -------------------------------------------------------------
        ctx.save()
        ctx.translate(2.0, -18)

        # Helmet Head Sphere in 3/4 view
        pat_helm = cairo.RadialGradient(2, -2, 2, 0, 0, 11)
        pat_helm.add_color_stop_rgb(0.0, 0.18, 0.36, 0.70)
        pat_helm.add_color_stop_rgb(1.0, 0.08, 0.18, 0.42)
        ctx.set_source(pat_helm)
        ctx.arc(0, 0, 9.5, 0, 2 * math.pi)
        ctx.fill()

        # Jawline / Flesh Face in 3/4 profile
        ctx.set_source_rgb(*FLESH_TONE)
        ctx.new_path()
        ctx.move_to(-3, 2)
        ctx.line_to(6, 2)
        ctx.line_to(7, 8)
        ctx.line_to(1, 9)
        ctx.line_to(-3, 8)
        ctx.close_path()
        ctx.fill()

        # Brown Leather Chinstrap
        ctx.set_source_rgb(*LEATHER_BROWN)
        ctx.set_line_width(1.2)
        ctx.move_to(-3, 3)
        ctx.line_to(-1, 8.5)
        ctx.line_to(3, 8.5)
        ctx.line_to(5, 3)
        ctx.stroke()

        # Crisp White 'A' on Forehead Brow (angled in 3/4)
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.set_line_width(1.6)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(-0.5, 1.0)
        ctx.line_to(2.0, -5.5)
        ctx.line_to(4.5, 1.0)
        ctx.move_to(0.5, -1.8)
        ctx.line_to(3.5, -1.8)
        ctx.stroke()

        # Silver Helmet Wings in 3/4 perspective
        ctx.set_source_rgb(0.92, 0.94, 0.98)
        # Near wing (prominent)
        ctx.new_path()
        ctx.move_to(5.5, -1.0)
        ctx.line_to(10.5, -5.5)
        ctx.line_to(6.5, 1.5)
        ctx.close_path()
        ctx.fill()
        # Far wing (foreshortened)
        ctx.new_path()
        ctx.move_to(-6.0, -1.0)
        ctx.line_to(-9.5, -5.0)
        ctx.line_to(-6.5, 1.0)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 5. HELD VIBRANIUM SHIELD (Dynamic 3/4 Running Combat Guard)
        # -------------------------------------------------------------
        if self.shield.state == "HELD":
            ctx.save()
            if self.is_hero_posing:
                # Proud Front-and-Center Raised Shield
                ctx.translate(0, 1)
                ctx.scale(1.08, 1.08)
            elif self.is_blocking:
                # Direct Forward Protective Barrier
                ctx.translate(14, -2)
                ctx.scale(0.85, 1.0)
            elif is_running:
                # DYNAMIC 3/4 RUNNING COMBAT GUARD ON FORWARD FOREARM!
                ctx.translate(11, 0)
                ctx.rotate(-0.15)
                ctx.scale(0.82, 1.0)  # Realistic 3/4 elliptical foreshortening
            else:
                # Relaxed 3/4 Ready Shield Stance
                ctx.translate(9, 3)
                ctx.scale(0.72, 1.0)

            # Outer Crimson Vibranium Ring with Specular Rim
            ring_pat = cairo.RadialGradient(0, 0, 8, 0, 0, 17)
            ring_pat.add_color_stop_rgb(0.0, 0.92, 0.18, 0.20)
            ring_pat.add_color_stop_rgb(1.0, 0.65, 0.08, 0.10)
            ctx.set_source(ring_pat)
            ctx.arc(0, 0, 16.5, 0, 2 * math.pi)
            ctx.fill()

            # Silver Alloy Ring
            ctx.set_source_rgb(0.92, 0.94, 0.98)
            ctx.arc(0, 0, 12.5, 0, 2 * math.pi)
            ctx.fill()

            # Inner Crimson Ring
            ctx.set_source(ring_pat)
            ctx.arc(0, 0, 9.0, 0, 2 * math.pi)
            ctx.fill()

            # Deep Blue Center Starfield
            blue_pat = cairo.RadialGradient(0, 0, 1, 0, 0, 6)
            blue_pat.add_color_stop_rgb(0.0, 0.22, 0.45, 0.90)
            blue_pat.add_color_stop_rgb(1.0, 0.08, 0.20, 0.60)
            ctx.set_source(blue_pat)
            ctx.arc(0, 0, 6.0, 0, 2 * math.pi)
            ctx.fill()

            # 5-Pointed Brilliant White Star
            ctx.set_source_rgb(1.0, 1.0, 1.0)
            ctx.new_path()
            star_out = 4.0
            star_in = 1.7
            for i in range(5):
                ang = -math.pi / 2 + i * (2 * math.pi / 5)
                sx = math.cos(ang) * star_out
                sy = math.sin(ang) * star_out
                if i == 0:
                    ctx.move_to(sx, sy)
                else:
                    ctx.line_to(sx, sy)
                ang_in = ang + (math.pi / 5)
                sx_in = math.cos(ang_in) * star_in
                sy_in = math.sin(ang_in) * star_in
                ctx.line_to(sx_in, sy_in)
            ctx.close_path()
            ctx.fill()

            # Star Lens Flare Gleam in Hero Pose
            if self.is_hero_posing:
                flare_time = self.anim_time * 5.0
                flare_alpha = 0.6 + 0.3 * math.sin(flare_time)
                ctx.set_source_rgba(1.0, 0.95, 0.6, flare_alpha)
                ctx.set_line_width(1.8)
                ctx.move_to(-12, 0)
                ctx.line_to(12, 0)
                ctx.move_to(0, -12)
                ctx.line_to(0, 12)
                ctx.stroke()
                ctx.set_line_width(1.0)
                ctx.move_to(-6, -6)
                ctx.line_to(6, 6)
                ctx.move_to(-6, 6)
                ctx.line_to(6, -6)
                ctx.stroke()

            ctx.restore()

        ctx.restore()
