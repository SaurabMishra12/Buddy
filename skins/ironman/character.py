"""Iron Man character: Mark armor with metallic gradients, arc reactor, repulsor blasts, and rocket boot thrusters."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager, CYAN_GLOW, FIRE_YELLOW, FIRE_ORANGE
from core.projectiles import DesktopProjectileWindow


class IronManCharacter(BaseCharacter):
    """Tony Stark in high-tech Mark armor with jet flight, unibeam, and screen-wide repulsor bolts."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="ironman")
        self.can_fly = True
        self.arc_pulse = 0.0
        self.is_firing_repulsor = False
        self.repulsor_end = 0.0
        self.action_timer = time.time() + random.uniform(3.0, 6.0)

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        dir_mult = 1.0 if self.facing_right else -1.0
        palm_x = self.x + dir_mult * 24.0
        palm_y = self.y - 6.0

        if ability_name in ("repulsor_blast", "attack"):
            self.is_firing_repulsor = True
            self.repulsor_end = time.time() + 0.45

            DesktopProjectileWindow(
                proj_type="repulsor",
                start_x=palm_x,
                start_y=palm_y,
                target_x=target_x,
                target_y=target_y,
                owner_getter=lambda: (self.x + dir_mult * 20.0, self.y - 6.0),
                speed=30.0
            )
            particle_mgr.burst_sparks(palm_x, palm_y, count=14, color=CYAN_GLOW)
            particle_mgr.shockwave(palm_x, palm_y, max_radius=40.0, color=CYAN_GLOW)
            audio_mgr.play("laser")
            return True
        elif ability_name == "air_dash":
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.vx = (dx / dist) * 28.0
            self.vy = (dy / dist) * 28.0
            self.state = CharacterState.FLY
            particle_mgr.flame_puff(self.x, self.y + 16, count=8, size=9.0)
            particle_mgr.shockwave(self.x, self.y + 16, max_radius=50.0, color=CYAN_GLOW)
            audio_mgr.play("jet")
            return True
        elif ability_name == "unibeam":
            self.arc_pulse = 2.0
            particle_mgr.shockwave(self.x, self.y, max_radius=75.0, color=CYAN_GLOW)
            particle_mgr.burst_sparks(self.x, self.y, count=25, color=CYAN_GLOW)
            audio_mgr.play("laser")
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

        # Facing direction
        self.facing_right = (cursor_x >= self.x)

        if self.is_firing_repulsor and now >= self.repulsor_end:
            self.is_firing_repulsor = False

        if self.arc_pulse > 0.0:
            self.arc_pulse = max(0.0, self.arc_pulse - 0.05)

        # Random personality events
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(4.0, 8.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.50:
                self.trigger_ability("repulsor_blast", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.80:
                self.trigger_ability("air_dash", cursor_x, cursor_y, particle_mgr, audio_mgr)
            else:
                self.trigger_ability("unibeam", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Flight movement
        speed_mult = config_data.get("speed", 1.0)
        max_spd = 17.0 * speed_mult
        accel = 0.75 * speed_mult

        # True vector to cursor without artificial offset
        dx = cursor_x - self.x
        dy = cursor_y - self.y
        dist = math.hypot(dx, dy)

        if dist > 50.0:
            self.vx += (dx / dist) * min(dist * 0.08, accel)
            self.vy += (dy / dist) * min(dist * 0.08, accel)
            self.state = CharacterState.FLY
        else:
            # Peaceful touch/petting deadzone
            self.state = CharacterState.HOVER
            self.vx *= 0.70
            self.vy *= 0.70

        self.vx *= 0.90
        self.vy *= 0.90

        spd = math.hypot(self.vx, self.vy)
        if spd > max_spd:
            self.vx = (self.vx / spd) * max_spd
            self.vy = (self.vy / spd) * max_spd

        self.x += self.vx
        self.y += self.vy

        # Dual-stage jet boot flames
        boot_y = self.y + 26.0
        boot_left_x = self.x - 5.5
        boot_right_x = self.x + 5.5
        particle_mgr.flame_puff(boot_left_x, boot_y, vy=random.uniform(2.5, 6.0), count=1, size=4.5)
        particle_mgr.flame_puff(boot_right_x, boot_y, vy=random.uniform(2.5, 6.0), count=1, size=4.5)
        if spd > 8.0:
            particle_mgr.burst_sparks(self.x, boot_y, count=2, color=CYAN_GLOW, size=1.5)

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 50.0, self.y))

        # Dynamic body tilt
        target_tilt = (self.vx / max_spd) * 0.35 if self.state == CharacterState.FLY else 0.0
        self.tilt += (target_tilt - self.tilt) * 0.15

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.rotate(self.tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Armored Legs with Gold Thigh Insets & Boots
        # Left Leg
        for lx in [-8, 2]:
            ctx.save()
            # Thigh armor with metallic crimson gradient
            thigh_pat = cairo.LinearGradient(lx, 10, lx + 6, 24)
            thigh_pat.add_color_stop_rgb(0.0, 0.88, 0.12, 0.16)
            thigh_pat.add_color_stop_rgb(0.5, 0.65, 0.08, 0.10)
            thigh_pat.add_color_stop_rgb(1.0, 0.40, 0.04, 0.06)
            ctx.set_source(thigh_pat)
            ctx.rectangle(lx, 10, 6, 14)
            ctx.fill()

            # Gold Knee Cop Plate
            knee_pat = cairo.LinearGradient(lx, 14, lx + 6, 19)
            knee_pat.add_color_stop_rgb(0.0, 1.0, 0.88, 0.35)
            knee_pat.add_color_stop_rgb(1.0, 0.78, 0.58, 0.12)
            ctx.set_source(knee_pat)
            ctx.rectangle(lx, 14, 6, 4.5)
            ctx.fill()

            # Jet Boot
            boot_pat = cairo.LinearGradient(lx - 1, 22, lx + 7, 28)
            boot_pat.add_color_stop_rgb(0.0, 0.85, 0.14, 0.16)
            boot_pat.add_color_stop_rgb(1.0, 0.45, 0.06, 0.08)
            ctx.set_source(boot_pat)
            ctx.rectangle(lx - 1, 22, 7, 6.5)
            ctx.fill()

            # Boot sole thruster nozzle
            ctx.set_source_rgb(0.25, 0.25, 0.28)
            ctx.rectangle(lx, 27.5, 5, 1.5)
            ctx.fill()
            ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], 0.9)
            ctx.rectangle(lx + 1, 28, 3, 1.0)
            ctx.fill()
            ctx.restore()

        # 2. Torso Armor with Sculpted Pectorals and Gold Flank Inlays
        torso_pat = cairo.LinearGradient(-11, -12, 11, 12)
        torso_pat.add_color_stop_rgb(0.0, 0.92, 0.15, 0.18)
        torso_pat.add_color_stop_rgb(0.4, 0.72, 0.10, 0.12)
        torso_pat.add_color_stop_rgb(1.0, 0.42, 0.05, 0.07)
        ctx.set_source(torso_pat)
        ctx.rectangle(-11, -11, 22, 23)
        ctx.fill()

        # Metallic edge specular shine
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.25)
        ctx.set_line_width(1.0)
        ctx.move_to(-11, -11)
        ctx.line_to(11, -11)
        ctx.stroke()

        # Gold Rib / Flank Armor Inlays
        gold_flank = cairo.LinearGradient(-11, -6, 11, 10)
        gold_flank.add_color_stop_rgb(0.0, 1.0, 0.88, 0.35)
        gold_flank.add_color_stop_rgb(1.0, 0.75, 0.55, 0.10)
        ctx.set_source(gold_flank)
        ctx.rectangle(-11, -6, 3.5, 14)
        ctx.rectangle(7.5, -6, 3.5, 14)
        ctx.fill()

        # Abdominal armor division grooves
        ctx.set_source_rgb(0.20, 0.05, 0.05)
        ctx.set_line_width(1.0)
        ctx.move_to(-6, 3)
        ctx.line_to(6, 3)
        ctx.move_to(-6, 7)
        ctx.line_to(6, 7)
        ctx.stroke()

        # 3. RT Arc Reactor (Unibeam Core)
        arc_x, arc_y = 0.0, -2.0
        # Outer glow
        glow_rad = 6.5 + math.sin(self.anim_time * 6.0) * 1.0 + self.arc_pulse * 4.0
        pat_arc_glow = cairo.RadialGradient(arc_x, arc_y, 2, arc_x, arc_y, glow_rad)
        pat_arc_glow.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 0.95)
        pat_arc_glow.add_color_stop_rgba(0.4, CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], 0.8)
        pat_arc_glow.add_color_stop_rgba(1.0, 0.1, 0.4, 0.9, 0.0)
        ctx.set_source(pat_arc_glow)
        ctx.arc(arc_x, arc_y, glow_rad, 0, 2 * math.pi)
        ctx.fill()

        # High-tech silver casing rim
        ctx.set_source_rgb(0.85, 0.88, 0.92)
        ctx.arc(arc_x, arc_y, 4.2, 0, 2 * math.pi)
        ctx.stroke()
        # White hot energy core
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(arc_x, arc_y, 2.5, 0, 2 * math.pi)
        ctx.fill()

        # 4. Arms & Repulsor Palms
        # Left Arm (hanging naturally or cocked)
        ctx.save()
        arm_pat = cairo.LinearGradient(-16, -8, -10, 10)
        arm_pat.add_color_stop_rgb(0.0, 0.85, 0.12, 0.15)
        arm_pat.add_color_stop_rgb(1.0, 0.45, 0.06, 0.08)
        ctx.set_source(arm_pat)
        ctx.rectangle(-15, -8, 4.5, 16)
        ctx.fill()
        # Gold bicep band
        ctx.set_source_rgb(0.95, 0.80, 0.20)
        ctx.rectangle(-15, -4, 4.5, 3.5)
        ctx.fill()
        ctx.restore()

        # Right Arm (Raised forward aiming repulsor)
        ctx.save()
        r_arm_pat = cairo.LinearGradient(10, -9, 24, -3)
        r_arm_pat.add_color_stop_rgb(0.0, 0.88, 0.14, 0.16)
        r_arm_pat.add_color_stop_rgb(1.0, 0.55, 0.08, 0.10)
        ctx.set_source(r_arm_pat)
        ctx.rectangle(10, -9, 14, 5.0)
        ctx.fill()
        # Gold gauntlet trim
        ctx.set_source_rgb(0.95, 0.80, 0.20)
        ctx.rectangle(14, -9, 4.0, 5.0)
        ctx.fill()

        # Palm Repulsor Emitter (Blazing Cyan)
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(24, -6.5, 2.8, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], 0.85)
        ctx.arc(24, -6.5, 5.2, 0, 2 * math.pi)
        ctx.set_line_width(1.5)
        ctx.stroke()
        ctx.restore()

        # 5. Helmet & Iconic Sculpted Gold Faceplate
        ctx.save()
        helm_pat = cairo.LinearGradient(0, -28, 0, -10)
        helm_pat.add_color_stop_rgb(0.0, 0.92, 0.15, 0.18)
        helm_pat.add_color_stop_rgb(1.0, 0.52, 0.08, 0.10)
        ctx.set_source(helm_pat)
        ctx.arc(0, -18, 9.5, 0, 2 * math.pi)
        ctx.fill()

        # Sculpted 24K Gold Faceplate
        fp_pat = cairo.LinearGradient(0, -25, 0, -11)
        fp_pat.add_color_stop_rgb(0.0, 1.0, 0.90, 0.38)
        fp_pat.add_color_stop_rgb(0.6, 0.88, 0.70, 0.20)
        fp_pat.add_color_stop_rgb(1.0, 0.65, 0.45, 0.10)
        ctx.set_source(fp_pat)
        ctx.new_path()
        ctx.move_to(-5.5, -24)
        ctx.line_to(5.5, -24)
        ctx.line_to(6.5, -16)
        ctx.line_to(3.5, -11)
        ctx.line_to(-3.5, -11)
        ctx.line_to(-6.5, -16)
        ctx.close_path()
        ctx.fill()

        # Faceplate seam bevel line
        ctx.set_source_rgb(0.35, 0.20, 0.05)
        ctx.set_line_width(0.8)
        ctx.stroke()

        # Glowing Cyan Optic Eye Slits
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.rectangle(-4.5, -18, 3.2, 1.4)
        ctx.rectangle(1.5, -18, 3.2, 1.4)
        ctx.fill()

        # Optic lens neon bloom
        ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], 0.9)
        ctx.set_line_width(1.0)
        ctx.rectangle(-4.5, -18, 3.2, 1.4)
        ctx.rectangle(1.5, -18, 3.2, 1.4)
        ctx.stroke()

        ctx.restore()
        ctx.restore()
