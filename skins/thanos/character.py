"""Thanos character: sculpted Titan battle armor, Infinity Gauntlet with 6 glowing stones, and cosmic snap."""

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
            particle_mgr.shockwave(self.x, self.y, max_radius=75.0, color=(0.15, 0.95, 0.35))
            particle_mgr.burst_sparks(self.x, self.y, count=22, color=(0.15, 0.95, 0.35))
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

        # Random ability triggers (smooth, non-spastic)
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(6.0, 11.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.40:
                self.trigger_ability("power_blast", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.75:
                self.trigger_ability("time_stone", cursor_x, cursor_y, particle_mgr, audio_mgr)
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
        else:
            # Peaceful petting/touch deadzone: stays still and calm!
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

        # Hover breathing bob
        if self.state == CharacterState.HOVER:
            self.y += math.sin(self.anim_time * 2.5) * 0.35

        # Screen boundary clamp
        self.x = max(min_x + 55.0, min(min_x + screen_w - 55.0, self.x))
        self.y = max(min_y + 55.0, min(min_y + screen_h - 55.0, self.y))

        # Dynamic body tilt
        target_tilt = (self.vx / max_spd) * 0.15
        self.tilt += (target_tilt - self.tilt) * 0.12

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.rotate(self.tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Armored Legs & Golden Battle Greaves
        # Thigh armor
        ctx.set_source_rgb(0.16, 0.18, 0.24)
        ctx.rectangle(-11, 12, 9, 16)
        ctx.rectangle(2, 12, 9, 16)
        ctx.fill()

        # Sculpted Golden Shin Guards
        pat_gold = cairo.LinearGradient(0, 18, 0, 30)
        pat_gold.add_color_stop_rgb(0.0, 0.95, 0.82, 0.28)
        pat_gold.add_color_stop_rgb(0.5, 0.75, 0.58, 0.16)
        pat_gold.add_color_stop_rgb(1.0, 0.45, 0.32, 0.08)

        ctx.set_source(pat_gold)
        ctx.rectangle(-12, 20, 10, 10)
        ctx.rectangle(2, 20, 10, 10)
        ctx.fill()
        ctx.set_source_rgb(0.35, 0.25, 0.08)
        ctx.set_line_width(1.0)
        ctx.rectangle(-12, 20, 10, 10)
        ctx.rectangle(2, 20, 10, 10)
        ctx.stroke()

        # Heavy battle boots
        ctx.set_source_rgb(0.20, 0.22, 0.28)
        ctx.rectangle(-13, 29, 12, 5)
        ctx.rectangle(1, 29, 12, 5)
        ctx.fill()

        # 2. Imposing Golden Torso Cuirass with Obsidian Inlays
        ctx.set_source(pat_gold)
        ctx.rectangle(-16, -14, 32, 28)
        ctx.fill()

        # Obsidian chest armor segments
        ctx.set_source_rgb(0.12, 0.14, 0.20)
        ctx.rectangle(-12, -10, 24, 8)
        ctx.fill()
        ctx.rectangle(-10, 2, 20, 8)
        ctx.fill()

        # Gold chest chevron lines
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
            ctx.set_source_rgb(0.35, 0.25, 0.08)
            ctx.set_line_width(1.2)
            ctx.stroke()
            ctx.restore()

        # 3. Sculpted Titan Head, Chin Striations & Golden Helmet
        # Purple Titan Skin
        pat_skin = cairo.LinearGradient(0, -30, 0, -8)
        pat_skin.add_color_stop_rgb(0.0, 0.62, 0.42, 0.72)
        pat_skin.add_color_stop_rgb(1.0, 0.42, 0.25, 0.52)
        ctx.set_source(pat_skin)
        ctx.arc(0, -19, 12, 0, 2 * math.pi)
        ctx.fill()

        # Signature Vertical Chin Grooves (Striations)
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
        ctx.set_source_rgb(0.35, 0.25, 0.08)
        ctx.set_line_width(1.0)
        ctx.stroke()

        # Piercing Golden Eyes
        ctx.set_source_rgb(1.0, 0.90, 0.20)
        ctx.arc(-4, -19, 2.0, 0, 2 * math.pi)
        ctx.arc(4, -19, 2.0, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgb(0.1, 0.0, 0.2)
        ctx.arc(-4, -19, 0.9, 0, 2 * math.pi)
        ctx.arc(4, -19, 0.9, 0, 2 * math.pi)
        ctx.fill()

        # 4. Right Arm (Battle gauntlet)
        ctx.set_source_rgb(0.16, 0.18, 0.24)
        ctx.rectangle(-18, -10, 5, 18)
        ctx.fill()
        ctx.set_source(pat_gold)
        ctx.rectangle(-19, 0, 6, 7)
        ctx.fill()

        # 5. The INFINITY GAUNTLET (Raised Forward on Left Arm)
        ctx.save()
        ctx.translate(14, -5)

        # Arm
        ctx.set_source_rgb(0.16, 0.18, 0.24)
        ctx.rectangle(0, -6, 12, 6)
        ctx.fill()

        # Ornate Golden Gauntlet
        pat_gauntlet = cairo.LinearGradient(0, -8, 22, 6)
        pat_gauntlet.add_color_stop_rgb(0.0, 1.0, 0.88, 0.35)
        pat_gauntlet.add_color_stop_rgb(0.6, 0.80, 0.62, 0.18)
        pat_gauntlet.add_color_stop_rgb(1.0, 0.50, 0.35, 0.10)
        ctx.set_source(pat_gauntlet)
        ctx.rectangle(6, -6, 14, 11)
        ctx.fill()
        # Knuckle fist
        ctx.arc(17, -0.5, 6.5, 0, 2 * math.pi)
        ctx.fill()
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
            # Outer stone glow aura
            ctx.set_source_rgba(col[0], col[1], col[2], 0.45 * gp)
            ctx.arc(gx, gy, rad * 2.2, 0, 2 * math.pi)
            ctx.fill()
            # Stone facet
            ctx.set_source_rgb(col[0], col[1], col[2])
            ctx.arc(gx, gy, rad, 0, 2 * math.pi)
            ctx.fill()
            # Specular gleam
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.85)
            ctx.arc(gx - 0.5, gy - 0.5, rad * 0.4, 0, 2 * math.pi)
            ctx.fill()

        # Cosmic energy crackle around gauntlet if snapping
        if self.is_snapping:
            ctx.set_source_rgba(COSMIC_VIOLET[0], COSMIC_VIOLET[1], COSMIC_VIOLET[2], 0.9)
            ctx.arc(17, -0.5, 14.0, 0, 2 * math.pi)
            ctx.set_line_width(2.0)
            ctx.stroke()

        ctx.restore()
        ctx.restore()
