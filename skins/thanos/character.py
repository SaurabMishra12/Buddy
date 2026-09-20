"""Thanos character: sculpted Titan battle armor, Infinity Gauntlet with 6 glowing stones,
active Time Stone chronal spell mandala, and Reality Warp clone convergence.
"""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, List
from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager, COSMIC_VIOLET, CYAN_GLOW
from core.audio import audio_manager
from core.projectiles import DesktopProjectileWindow


class ThanosCharacter(BaseCharacter):
    """The Mad Titan wielding the 6 Infinity Stones with cosmic energy and battle armor."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="thanos")
        self.can_fly = True
        self.hitbox_radius = 48.0
        self.active_stone = "mind"
        self.action_timer = time.time() + random.uniform(5.0, 9.0)
        self.gem_pulse = 0.0
        self.is_snapping = False
        self.snap_end_time = 0.0
        self.stride = 0.0
        self.fly_phase = 0.0

        # Time Stone chronal state
        self.is_time_active = False
        self.time_stone_end = 0.0

        # Reality Warp clone army & convergence state
        self.is_reality_warping = False
        self.reality_warp_start = 0.0
        self.reality_warp_duration = 3.2
        self.reality_has_imploded = False

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("the_snap", "infinity_snap", "signature"):
            self.is_snapping = True
            self.snap_end_time = time.time() + 1.8
            # Multi-layer cosmic shockwaves
            particle_mgr.shockwave(self.x, self.y, max_radius=95.0, color=(1.0, 0.88, 0.25))
            particle_mgr.shockwave(self.x, self.y, max_radius=75.0, color=COSMIC_VIOLET)
            particle_mgr.shockwave(self.x, self.y, max_radius=55.0, color=CYAN_GLOW)
            particle_mgr.burst_sparks(self.x, self.y, count=45, color=(0.85, 0.40, 0.95), size=3.2)
            audio_mgr.play("smash")
            audio_mgr.play("magic")
            return True
        elif ability_name == "power_blast":
            self.active_stone = "power"
            DesktopProjectileWindow(
                proj_type="power_blast",
                start_x=self.x,
                start_y=self.y,
                target_x=target_x,
                target_y=target_y,
                owner_getter=lambda: (self.x, self.y),
                speed=26.0
            )
            particle_mgr.shockwave(self.x, self.y, max_radius=60.0, color=COSMIC_VIOLET)
            particle_mgr.burst_sparks(self.x, self.y, count=18, color=COSMIC_VIOLET)
            audio_mgr.play("laser")
            return True
        elif ability_name == "time_stone":
            self.active_stone = "time"
            self.is_time_active = True
            self.time_stone_end = time.time() + 3.8
            particle_mgr.shockwave(self.x, self.y, max_radius=85.0, color=(0.15, 0.95, 0.35))
            particle_mgr.burst_sparks(self.x, self.y, count=32, color=(0.15, 0.95, 0.35), size=3.2)
            audio_mgr.play("magic")
            return True
        elif ability_name in ("reality_warp", "reality_stone", "reality_wrap", "reality"):
            self.active_stone = "reality"
            self.is_reality_warping = True
            self.reality_warp_start = time.time()
            self.reality_warp_duration = 3.2
            self.reality_has_imploded = False
            particle_mgr.shockwave(self.x, self.y, max_radius=90.0, color=(0.95, 0.15, 0.25))
            particle_mgr.burst_sparks(self.x, self.y, count=36, color=(0.95, 0.15, 0.25), size=3.2)
            audio_mgr.play("magic")
            return True
        elif ability_name in ("space_teleport", "space_stone", "teleport"):
            self.active_stone = "space"
            # Blue portal departure
            particle_mgr.shockwave(self.x, self.y, max_radius=70.0, color=CYAN_GLOW)
            particle_mgr.burst_sparks(self.x, self.y, count=20, color=CYAN_GLOW)
            audio_mgr.play("teleport")
            # Teleport near destination
            self.x = target_x - (40.0 if self.facing_right else -40.0)
            self.y = target_y
            # Blue portal arrival
            particle_mgr.shockwave(self.x, self.y, max_radius=70.0, color=CYAN_GLOW)
            particle_mgr.burst_sparks(self.x, self.y, count=25, color=CYAN_GLOW)
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
        self.gem_pulse = 0.7 + (math.sin(self.anim_time * 4.0) * 0.3)
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)

        # Facing direction
        self.facing_right = (cursor_x >= self.x)

        if self.is_snapping and now >= self.snap_end_time:
            self.is_snapping = False

        # Time Stone chronal active timer
        if self.is_time_active:
            if now >= self.time_stone_end:
                self.is_time_active = False
            else:
                if random.random() < 0.28:
                    particle_mgr.burst_sparks(
                        self.x + random.uniform(-25, 25),
                        self.y + random.uniform(-25, 25),
                        count=2,
                        color=(0.15, 0.95, 0.35),
                        size=2.6
                    )

        # Reality Warp clone & convergence timer
        if self.is_reality_warping:
            t_rel = (now - self.reality_warp_start) / self.reality_warp_duration
            if t_rel >= 1.0:
                self.is_reality_warping = False
            else:
                # Trigger convergence shockwave when clones snap back into center
                if t_rel >= 0.85 and not self.reality_has_imploded:
                    self.reality_has_imploded = True
                    particle_mgr.shockwave(self.x, self.y, max_radius=110.0, color=(0.95, 0.15, 0.25))
                    particle_mgr.shockwave(self.x, self.y, max_radius=70.0, color=(1.0, 0.35, 0.45))
                    particle_mgr.burst_sparks(self.x, self.y, count=45, color=(0.95, 0.15, 0.25), size=3.5)
                    audio_mgr.play("smash")
                # Crimson reality distortion particles
                if random.random() < 0.32:
                    particle_mgr.burst_sparks(
                        self.x + random.uniform(-40, 40),
                        self.y + random.uniform(-40, 40),
                        count=2,
                        color=(0.95, 0.15, 0.25),
                        size=2.8
                    )

        # Random ability triggers (smooth, non-spastic)
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(6.0, 11.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.25:
                self.trigger_ability("power_blast", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.50:
                self.trigger_ability("time_stone", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.75:
                self.trigger_ability("reality_warp", cursor_x, cursor_y, particle_mgr, audio_mgr)
            else:
                self.trigger_ability("the_snap", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Smooth, imposing Titan levitation
        speed_mult = config_data.get("speed", 1.0)
        max_spd = 12.0 * speed_mult
        accel = 0.45 * speed_mult

        # True vector to cursor without artificial offset
        dx = cursor_x - self.x
        dy = cursor_y - self.y
        dist = math.hypot(dx, dy)

        if dist > 48.0:
            self.vx += (dx / dist) * min(dist * 0.04, accel)
            self.vy += (dy / dist) * min(dist * 0.04, accel)
            self.state = CharacterState.FLY
            self.fly_phase += 0.08
            self.stride += 0.12
            if random.random() < 0.22:
                particle_mgr.burst_sparks(
                    self.x + random.uniform(-10, 10),
                    self.y + 24.0,
                    count=1,
                    color=(0.10, 0.60, 1.0),
                    size=2.2
                )
        else:
            # Peaceful petting/touch deadzone: stays still and calm!
            self.state = CharacterState.HOVER
            self.vx *= 0.70
            self.vy *= 0.70
            self.stride *= 0.85

        self.vx *= 0.90
        self.vy *= 0.90

        spd = math.hypot(self.vx, self.vy)
        if spd > max_spd:
            self.vx = (self.vx / spd) * max_spd
            self.vy = (self.vy / spd) * max_spd

        self.x += self.vx
        self.y += self.vy

        # Hover breathing bob
        if self.state == CharacterState.HOVER:
            self.y += math.sin(self.anim_time * 2.5) * 0.35

        # Screen boundary clamp
        self.x = max(min_x + 55.0, min(min_x + screen_w - 55.0, self.x))
        self.y = max(min_y + 55.0, min(min_y + screen_h - 55.0, self.y))

        # Dynamic body tilt
        target_tilt = (self.vx / max_spd) * 0.15
        self.tilt += (target_tilt - self.tilt) * 0.12

    def _draw_titan_body(
        self,
        ctx: cairo.Context,
        is_clone: bool = False,
        clone_alpha: float = 1.0
    ) -> None:
        """Renders the detailed Titan body, armor, head, and gauntlet."""
        pat_gold = cairo.LinearGradient(0, -18, 0, 30)
        if is_clone:
            pat_gold.add_color_stop_rgba(0.0, 0.95, 0.35, 0.40, clone_alpha)
            pat_gold.add_color_stop_rgba(0.5, 0.75, 0.20, 0.25, clone_alpha)
            pat_gold.add_color_stop_rgba(1.0, 0.45, 0.10, 0.15, clone_alpha)
        else:
            pat_gold.add_color_stop_rgb(0.0, 0.95, 0.82, 0.28)
            pat_gold.add_color_stop_rgb(0.5, 0.75, 0.58, 0.16)
            pat_gold.add_color_stop_rgb(1.0, 0.45, 0.32, 0.08)

        # 1. Armored Legs & Golden Battle Greaves
        # Calculate dynamic leg angles based on movement state
        if self.state == CharacterState.FLY:
            # Trailing imperial levitation posture
            rot_l = -0.16 - self.tilt * 0.4
            rot_r = 0.22 + self.tilt * 0.6 + math.sin(self.anim_time * 3.0) * 0.06
        elif self.state in (CharacterState.WALK, CharacterState.RUN):
            # Heavy titan battle stride
            rot_l = math.sin(self.stride) * 0.35
            rot_r = -math.sin(self.stride) * 0.35
        else:
            # Hover breathing bob
            rot_l = math.sin(self.anim_time * 2.0) * 0.04
            rot_r = -math.sin(self.anim_time * 2.0) * 0.04

        legs_spec = [
            (-6.5, rot_l),  # Left leg (pivot at -6.5, 12)
            (6.5, rot_r),   # Right leg (pivot at 6.5, 12)
        ]

        for hx, rot in legs_spec:
            ctx.save()
            ctx.translate(hx, 12)
            ctx.rotate(rot)

            # Thigh & shin
            if is_clone:
                ctx.set_source_rgba(0.20, 0.08, 0.12, clone_alpha)
            else:
                ctx.set_source_rgb(0.16, 0.18, 0.24)
            ctx.rectangle(-4.5, 0, 9, 16)
            ctx.fill()

            # Sculpted Golden Shin Guard
            pat_shin = cairo.LinearGradient(-4.5, 8, 4.5, 18)
            if is_clone:
                pat_shin.add_color_stop_rgba(0.0, 0.95, 0.35, 0.40, clone_alpha)
                pat_shin.add_color_stop_rgba(0.5, 0.75, 0.20, 0.25, clone_alpha)
                pat_shin.add_color_stop_rgba(1.0, 0.45, 0.10, 0.15, clone_alpha)
            else:
                pat_shin.add_color_stop_rgb(0.0, 0.95, 0.82, 0.28)
                pat_shin.add_color_stop_rgb(0.5, 0.75, 0.58, 0.16)
                pat_shin.add_color_stop_rgb(1.0, 0.45, 0.32, 0.08)

            ctx.set_source(pat_shin)
            ctx.rectangle(-5.0, 8, 10, 10)
            ctx.fill()
            if is_clone:
                ctx.set_source_rgba(0.95, 0.15, 0.25, clone_alpha * 0.8)
            else:
                ctx.set_source_rgb(0.35, 0.25, 0.08)
            ctx.set_line_width(1.0)
            ctx.rectangle(-5.0, 8, 10, 10)
            ctx.stroke()

            # Heavy battle boot
            if is_clone:
                ctx.set_source_rgba(0.25, 0.10, 0.15, clone_alpha)
            else:
                ctx.set_source_rgb(0.20, 0.22, 0.28)
            ctx.rectangle(-6.0, 17, 12, 5.5)
            ctx.fill()

            # Space Stone Levitation Rift beneath boot in flight
            if self.state == CharacterState.FLY and not is_clone:
                pat_space = cairo.RadialGradient(0, 22, 1, 0, 22, 12)
                pat_space.add_color_stop_rgba(0.0, 0.25, 0.85, 1.0, 0.80 * self.gem_pulse)
                pat_space.add_color_stop_rgba(0.45, 0.60, 0.18, 0.95, 0.45 * self.gem_pulse)
                pat_space.add_color_stop_rgba(1.0, 0.10, 0.05, 0.30, 0.0)
                ctx.set_source(pat_space)
                ctx.arc(0, 22, 12, 0, 2 * math.pi)
                ctx.fill()

            ctx.restore()

        # 2. Imposing Golden Torso Cuirass with Obsidian Inlays
        ctx.set_source(pat_gold)
        ctx.rectangle(-16, -14, 32, 28)
        ctx.fill()

        # Obsidian chest armor segments
        if is_clone:
            ctx.set_source_rgba(0.18, 0.06, 0.10, clone_alpha)
        else:
            ctx.set_source_rgb(0.12, 0.14, 0.20)
        ctx.rectangle(-12, -10, 24, 8)
        ctx.fill()
        ctx.rectangle(-10, 2, 20, 8)
        ctx.fill()

        # Gold chest chevron lines
        if is_clone:
            ctx.set_source_rgba(1.0, 0.40, 0.45, clone_alpha)
        else:
            ctx.set_source_rgb(0.98, 0.88, 0.35)
        ctx.set_line_width(1.6)
        ctx.move_to(-16, -1)
        ctx.line_to(16, -1)
        ctx.move_to(-16, 11)
        ctx.line_to(16, 11)
        ctx.stroke()

        # Massive Golden Pauldrons (Shoulder Guards)
        ctx.set_source(pat_gold)
        for sx in [-17, 17]:
            ctx.save()
            ctx.translate(sx, -12)
            ctx.arc(0, 0, 8.5, 0, 2 * math.pi)
            ctx.fill()
            if is_clone:
                ctx.set_source_rgba(0.95, 0.15, 0.25, clone_alpha * 0.8)
            else:
                ctx.set_source_rgb(0.35, 0.25, 0.08)
            ctx.set_line_width(1.2)
            ctx.stroke()
            ctx.restore()

        # 3. Sculpted Titan Head, Chin Striations & Golden Helmet
        # Purple Titan Skin
        pat_skin = cairo.LinearGradient(0, -30, 0, -8)
        if is_clone:
            pat_skin.add_color_stop_rgba(0.0, 0.82, 0.25, 0.50, clone_alpha)
            pat_skin.add_color_stop_rgba(1.0, 0.55, 0.15, 0.35, clone_alpha)
        else:
            pat_skin.add_color_stop_rgb(0.0, 0.62, 0.42, 0.72)
            pat_skin.add_color_stop_rgb(1.0, 0.42, 0.25, 0.52)
        ctx.set_source(pat_skin)
        ctx.arc(0, -19, 12, 0, 2 * math.pi)
        ctx.fill()

        # Signature Vertical Chin Grooves (Striations)
        if is_clone:
            ctx.set_source_rgba(0.45, 0.10, 0.25, clone_alpha)
        else:
            ctx.set_source_rgb(0.32, 0.18, 0.40)
        ctx.set_line_width(1.5)
        for cx in [-5, -2, 2, 5]:
            ctx.move_to(cx, -14)
            ctx.line_to(cx, -9)
            ctx.stroke()

        # Golden Battle Helmet
        ctx.set_source(pat_gold)
        ctx.new_path()
        ctx.move_to(-12, -19)
        ctx.line_to(-7, -31)
        ctx.line_to(0, -29)
        ctx.line_to(7, -31)
        ctx.line_to(12, -19)
        ctx.line_to(8, -19)
        ctx.line_to(0, -24)
        ctx.line_to(-8, -19)
        ctx.close_path()
        ctx.fill()
        if is_clone:
            ctx.set_source_rgba(0.95, 0.15, 0.25, clone_alpha * 0.8)
        else:
            ctx.set_source_rgb(0.35, 0.25, 0.08)
        ctx.set_line_width(1.0)
        ctx.stroke()

        # Piercing Golden Eyes
        if is_clone:
            ctx.set_source_rgba(1.0, 0.30, 0.35, clone_alpha)
        else:
            ctx.set_source_rgb(1.0, 0.90, 0.20)
        ctx.arc(-4, -19, 2.0, 0, 2 * math.pi)
        ctx.arc(4, -19, 2.0, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgba(0.1, 0.0, 0.2, clone_alpha)
        ctx.arc(-4, -19, 0.9, 0, 2 * math.pi)
        ctx.arc(4, -19, 0.9, 0, 2 * math.pi)
        ctx.fill()

        # 4. Right Arm (Battle gauntlet)
        ctx.save()
        arm_rot = 0.0
        if self.state in (CharacterState.WALK, CharacterState.RUN):
            arm_rot = -math.sin(self.stride) * 0.28
        elif self.state == CharacterState.FLY:
            arm_rot = -0.20 + self.tilt * 0.35
        ctx.translate(-16, -10)
        ctx.rotate(arm_rot)
        if is_clone:
            ctx.set_source_rgba(0.20, 0.08, 0.12, clone_alpha)
        else:
            ctx.set_source_rgb(0.16, 0.18, 0.24)
        ctx.rectangle(-2.5, 0, 5, 18)
        ctx.fill()
        ctx.set_source(pat_gold)
        ctx.rectangle(-3.0, 10, 6, 7)
        ctx.fill()
        ctx.restore()

        # 5. The INFINITY GAUNTLET (Raised Forward on Left Arm)
        ctx.save()
        gauntlet_lift = -2.5 if self.state == CharacterState.FLY else 0.0
        ctx.translate(14, -5 + gauntlet_lift)

        # Arm
        if is_clone:
            ctx.set_source_rgba(0.20, 0.08, 0.12, clone_alpha)
        else:
            ctx.set_source_rgb(0.16, 0.18, 0.24)
        ctx.rectangle(0, -6, 12, 6)
        ctx.fill()

        # Ornate Golden Gauntlet
        pat_gauntlet = cairo.LinearGradient(0, -8, 22, 6)
        if is_clone:
            pat_gauntlet.add_color_stop_rgba(0.0, 1.0, 0.45, 0.50, clone_alpha)
            pat_gauntlet.add_color_stop_rgba(0.6, 0.80, 0.25, 0.30, clone_alpha)
            pat_gauntlet.add_color_stop_rgba(1.0, 0.50, 0.15, 0.20, clone_alpha)
        else:
            pat_gauntlet.add_color_stop_rgb(0.0, 1.0, 0.88, 0.35)
            pat_gauntlet.add_color_stop_rgb(0.6, 0.80, 0.62, 0.18)
            pat_gauntlet.add_color_stop_rgb(1.0, 0.50, 0.35, 0.10)
        ctx.set_source(pat_gauntlet)
        ctx.rectangle(6, -6, 14, 11)
        ctx.fill()
        # Knuckle fist
        ctx.arc(17, -0.5, 6.5, 0, 2 * math.pi)
        ctx.fill()
        if is_clone:
            ctx.set_source_rgba(0.95, 0.15, 0.25, clone_alpha * 0.8)
        else:
            ctx.set_source_rgb(0.35, 0.25, 0.08)
        ctx.set_line_width(1.2)
        ctx.stroke()

        # THE 6 INFINITY STONES with glowing neon auras
        gp = self.gem_pulse
        gems = [
            # gx, gy, radius, (r, g, b)
            (17, -4.5, 2.0, (0.10, 0.60, 1.00)),   # Space (Electric Blue)
            (21, -2.0, 2.0, (0.95, 0.15, 0.20)),   # Reality (Crimson Red)
            (21, 1.5, 2.0, (0.85, 0.15, 0.95)),    # Power (Cosmic Violet)
            (17, 4.0, 2.0, (0.15, 0.95, 0.35)),    # Time (Emerald Green)
            (12, -2.0, 1.8, (1.00, 0.55, 0.10)),   # Soul (Warm Amber)
            (17, -0.5, 3.2, (1.00, 0.95, 0.25)),   # Mind (Center Solar Gold)
        ]

        for gx, gy, rad, col in gems:
            # Space stone cosmic flight flare
            if col == (0.10, 0.60, 1.00) and self.state == CharacterState.FLY and not is_clone:
                ctx.set_source_rgba(0.10, 0.70, 1.0, 0.80 * gp)
                ctx.arc(gx, gy, rad * 3.2, 0, 2 * math.pi)
                ctx.fill()

            # Outer stone glow aura
            ctx.set_source_rgba(col[0], col[1], col[2], 0.45 * gp * clone_alpha)
            ctx.arc(gx, gy, rad * 2.2, 0, 2 * math.pi)
            ctx.fill()
            # Stone facet
            ctx.set_source_rgba(col[0], col[1], col[2], clone_alpha)
            ctx.arc(gx, gy, rad, 0, 2 * math.pi)
            ctx.fill()
            # Specular gleam
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.85 * clone_alpha)
            ctx.arc(gx - 0.5, gy - 0.5, rad * 0.4, 0, 2 * math.pi)
            ctx.fill()

        # Cosmic energy crackle around gauntlet if snapping
        if self.is_snapping and not is_clone:
            ctx.set_source_rgba(COSMIC_VIOLET[0], COSMIC_VIOLET[1], COSMIC_VIOLET[2], 0.9)
            ctx.arc(17, -0.5, 14.0, 0, 2 * math.pi)
            ctx.set_line_width(2.0)
            ctx.stroke()

        # =============================================================
        # ACTIVE TIME STONE: Doctor Strange Chronal Spell Mandala!
        # =============================================================
        if self.is_time_active and not is_clone:
            ctx.save()
            # Center mandala at the green Time Stone knuckle (17, 4.0)
            ctx.translate(17, 4.0)

            t_pulse = 0.8 + 0.2 * math.sin(self.anim_time * 5.0)
            ctx.scale(t_pulse, t_pulse)

            # 1. Outer Runed Chronal Ring
            ctx.set_source_rgba(0.15, 0.95, 0.35, 0.85 * t_pulse)
            ctx.set_line_width(1.8)
            ctx.arc(0, 0, 22.0, 0, 2 * math.pi)
            ctx.stroke()

            # 2. Interlocking Concentric Square Glyphs (Doctor Strange Geometry)
            ctx.save()
            ctx.rotate(self.anim_time * 1.8)
            ctx.set_source_rgba(0.25, 1.0, 0.45, 0.70 * t_pulse)
            ctx.set_line_width(1.4)
            sq_size = 14.0
            ctx.rectangle(-sq_size, -sq_size, sq_size * 2, sq_size * 2)
            ctx.stroke()
            ctx.rotate(math.pi / 4.0)
            ctx.rectangle(-sq_size, -sq_size, sq_size * 2, sq_size * 2)
            ctx.stroke()
            ctx.restore()

            # 3. Inner Reverse-Spinning Chronal Gear
            ctx.save()
            ctx.rotate(-self.anim_time * 2.5)
            ctx.set_source_rgba(0.40, 1.0, 0.55, 0.80 * t_pulse)
            ctx.set_line_width(1.2)
            ctx.arc(0, 0, 10.0, 0, 2 * math.pi)
            ctx.stroke()
            # Cogs
            for i in range(12):
                ang = i * (math.pi / 6.0)
                ctx.move_to(9.0 * math.cos(ang), 9.0 * math.sin(ang))
                ctx.line_to(12.0 * math.cos(ang), 12.0 * math.sin(ang))
            ctx.stroke()
            ctx.restore()

            # 4. Central Chronal Luminous Core
            pat_core = cairo.RadialGradient(0, 0, 1, 0, 0, 14)
            pat_core.add_color_stop_rgba(0.0, 1.0, 1.0, 0.9, 0.95 * t_pulse)
            pat_core.add_color_stop_rgba(0.4, 0.15, 0.95, 0.35, 0.70 * t_pulse)
            pat_core.add_color_stop_rgba(1.0, 0.05, 0.65, 0.20, 0.0)
            ctx.set_source(pat_core)
            ctx.arc(0, 0, 14.0, 0, 2 * math.pi)
            ctx.fill()

            ctx.restore()

        ctx.restore()

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        now = time.time()

        # =============================================================
        # REALITY WARP: 6 Clones Fan Out Radially and Converge into One!
        # Clones fan out to radius 45px (scaled to 0.62x) so all 6 clones stay 100% inside 180x180 window!
        # =============================================================
        if self.is_reality_warping:
            t_rel = min(1.0, max(0.0, (now - self.reality_warp_start) / self.reality_warp_duration))

            # Phase Calculations:
            # 0.0 -> 0.40: Smooth expansion outward to 45px
            # 0.40 -> 0.68: Imposing multi-Thanos standoff (fanning out around target)
            # 0.68 -> 0.95: Rapid inward convergence & snap collapse into center
            # 0.95 -> 1.00: Full fusion shockwave at center
            max_clone_radius = 45.0

            if t_rel < 0.40:
                p_out = math.sin((t_rel / 0.40) * (math.pi / 2.0))
                current_radius = max_clone_radius * p_out
                clone_alpha = min(0.85, (t_rel / 0.20) * 0.85)
            elif t_rel < 0.68:
                current_radius = max_clone_radius + math.sin(self.anim_time * 3.5) * 2.0
                clone_alpha = 0.85
            elif t_rel < 0.95:
                p_in = (t_rel - 0.68) / (0.95 - 0.68)
                current_radius = max_clone_radius * max(0.0, (1.0 - (p_in ** 2.2)))
                clone_alpha = 0.85 * max(0.0, (1.0 - p_in * 0.3))
            else:
                current_radius = 0.0
                clone_alpha = 0.0

            if current_radius > 4.0 and clone_alpha > 0.05:
                # Render 6 Reality Clones arranged symmetrically in hexagon
                for i in range(6):
                    theta = (i * (math.pi / 3.0)) + (self.anim_time * 0.35)
                    cx = current_radius * math.cos(theta)
                    cy = current_radius * math.sin(theta)

                    # 1. Reality energy ribbon linking clone to true Thanos
                    ctx.save()
                    ctx.set_source_rgba(0.95, 0.15, 0.25, 0.40 * clone_alpha)
                    ctx.set_line_width(1.6)
                    ctx.move_to(self.x, self.y)
                    # Wavy bezier energy arc with constrained wave amplitude to stay well inside window
                    mid_x = (self.x + self.x + cx) * 0.5 + math.sin(self.anim_time * 4.0 + i) * 3.5
                    mid_y = (self.y + self.y + cy) * 0.5 + math.cos(self.anim_time * 4.0 + i) * 3.5
                    ctx.curve_to(mid_x, mid_y, mid_x, mid_y, self.x + cx, self.y + cy)
                    ctx.stroke()
                    ctx.restore()

                    # 2. Reality distortion cubes & runes around each clone
                    ctx.save()
                    ctx.translate(self.x + cx, self.y + cy)
                    ctx.rotate(self.anim_time * 2.0 + i)
                    ctx.set_source_rgba(0.95, 0.15, 0.25, 0.50 * clone_alpha)
                    ctx.set_line_width(1.0)
                    cube_s = 4.5
                    ctx.rectangle(-cube_s, -cube_s, cube_s * 2, cube_s * 2)
                    ctx.stroke()
                    ctx.restore()

                    # 3. Draw the Reality Clone figure (scaled to 0.62 to fit completely in window)
                    ctx.save()
                    ctx.translate(self.x + cx, self.y + cy)
                    ctx.rotate(self.tilt + math.sin(self.anim_time * 2.0 + i) * 0.08)
                    ctx.scale(self.scale * 0.62, self.scale * 0.62)
                    if not self.facing_right:
                        ctx.scale(-1.0, 1.0)
                    self._draw_titan_body(ctx, is_clone=True, clone_alpha=clone_alpha)
                    ctx.restore()

        # =============================================================
        # THE TRUE THANOS (Central Imposing Titan)
        # =============================================================
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.rotate(self.tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        self._draw_titan_body(ctx, is_clone=False, clone_alpha=1.0)

        ctx.restore()
