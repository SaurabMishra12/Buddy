"""Thanos character: Infinity Gauntlet with 6 Stone abilities and cosmic snap effects."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, List
from skins.base import BaseCharacter, CharacterState
from skins.manager import skin_manager
from core.particles import ParticleManager, COSMIC_VIOLET, CYAN_GLOW


class ThanosCharacter(BaseCharacter):
    """The Mad Titan wielding the Infinity Gauntlet and cosmic stone effects."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="thanos")
        self.can_fly = True
        self.hitbox_radius = 42.0
        self.stone_glow = 0.0
        self.active_stone = "power"  # "power", "space", "time", "reality", "mind", "soul"
        self.action_timer = time.time() + random.uniform(3.0, 7.0)

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        if ability_name == "power_blast":
            self.active_stone = "power"
            particle_mgr.arc_connect(self.x, self.y, target_x, target_y, branches=2, color=COSMIC_VIOLET)
            particle_mgr.shockwave(target_x, target_y, max_radius=65.0, color=COSMIC_VIOLET, line_width=3.5)
            particle_mgr.burst_sparks(target_x, target_y, count=16, color=COSMIC_VIOLET)
            audio_mgr.play("teleport")
            return True
        elif ability_name == "space_teleport":
            self.active_stone = "space"
            # Blue cosmic portal
            particle_mgr.shockwave(self.x, self.y, max_radius=50.0, color=CYAN_GLOW)
            particle_mgr.burst_sparks(self.x, self.y, count=12, color=CYAN_GLOW)
            self.x = target_x + random.uniform(-50, 50)
            self.y = target_y + random.uniform(-50, 50)
            particle_mgr.shockwave(self.x, self.y, max_radius=50.0, color=CYAN_GLOW)
            audio_mgr.play("teleport")
            return True
        elif ability_name == "time_stone":
            self.active_stone = "time"
            # Green temporal ripple
            particle_mgr.shockwave(self.x, self.y, max_radius=75.0, color=(0.1, 0.9, 0.3), line_width=4.0)
            audio_mgr.play("teleport")
            return True
        elif ability_name == "reality_warp":
            self.active_stone = "reality"
            # Crimson reality distortion
            particle_mgr.shockwave(self.x, self.y, max_radius=60.0, color=(0.95, 0.15, 0.25))
            audio_mgr.play("teleport")
            return True
        elif ability_name == "the_snap":
            # The legendary Infinity Gauntlet Snap
            particle_mgr.shockwave(self.x, self.y, max_radius=110.0, color=(1.0, 0.9, 0.4), line_width=5.0)
            particle_mgr.burst_sparks(self.x, self.y, count=30, color=(0.8, 0.4, 0.9), size=3.5)
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

        # Facing direction
        self.facing_right = (cursor_x >= self.x)

        # Random ability triggers
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(4.0, 9.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.30:
                self.trigger_ability("power_blast", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.55:
                self.trigger_ability("space_teleport", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.75:
                self.trigger_ability("time_stone", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.90:
                self.trigger_ability("the_snap", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Imposing floating movement
        speed_mult = config_data.get("speed", 1.0)
        max_spd = 11.0 * speed_mult
        accel = 0.50 * speed_mult

        tx = cursor_x - (50.0 if self.facing_right else -50.0)
        ty = cursor_y - 40.0
        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)

        if dist > 40.0:
            self.vx += (dx / dist) * min(dist * 0.06, accel)
            self.vy += (dy / dist) * min(dist * 0.06, accel)
            self.state = CharacterState.FLY
        else:
            self.state = CharacterState.HOVER
            self.vx *= 0.88
            self.vy *= 0.88

        self.vx *= 0.90
        self.vy *= 0.90

        spd = math.hypot(self.vx, self.vy)
        if spd > max_spd:
            self.vx = (self.vx / spd) * max_spd
            self.vy = (self.vy / spd) * max_spd

        self.x += self.vx
        self.y += self.vy

        # Screen boundary clamp
        self.x = max(min_x + 60.0, min(min_x + screen_w - 60.0, self.x))
        self.y = max(min_y + 60.0, min(min_y + screen_h - 60.0, self.y))

        # Dynamic body tilt
        target_tilt = (self.vx / max_spd) * 0.18
        self.tilt += (target_tilt - self.tilt) * 0.15

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.rotate(self.tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Armored Legs & Boots
        ctx.set_source_rgb(0.18, 0.20, 0.28)  # Dark battle armor
        ctx.rectangle(-10, 14, 8, 16)
        ctx.rectangle(2, 14, 8, 16)
        ctx.fill()
        # Gold greaves
        ctx.set_source_rgb(0.85, 0.70, 0.18)
        ctx.rectangle(-10, 18, 8, 8)
        ctx.rectangle(2, 18, 8, 8)
        ctx.fill()

        # 2. Imposing Golden Torso Armor
        ctx.set_source_rgb(0.85, 0.70, 0.18)
        ctx.rectangle(-14, -12, 28, 26)
        ctx.fill()

        # Armor segment lines
        ctx.set_source_rgb(0.60, 0.48, 0.10)
        ctx.set_line_width(1.5)
        ctx.move_to(-14, 0)
        ctx.line_to(14, 0)
        ctx.move_to(-14, 8)
        ctx.line_to(14, 8)
        ctx.stroke()

        # Golden Shoulder Pauldrons
        ctx.set_source_rgb(0.92, 0.76, 0.20)
        ctx.arc(-14, -10, 8, 0, 2 * math.pi)
        ctx.arc(14, -10, 8, 0, 2 * math.pi)
        ctx.fill()

        # 3. Head & Striated Chin (Purple Skin)
        ctx.set_source_rgb(0.55, 0.35, 0.65)  # Titan purple
        ctx.arc(0, -18, 11, 0, 2 * math.pi)
        ctx.fill()

        # Striated chin grooves
        ctx.set_source_rgb(0.42, 0.25, 0.50)
        ctx.set_line_width(1.2)
        for cx in [-4, 0, 4]:
            ctx.move_to(cx, -12)
            ctx.line_to(cx, -8)
            ctx.stroke()

        # Golden Battle Helmet
        ctx.set_source_rgb(0.85, 0.70, 0.18)
        ctx.new_path()
        ctx.move_to(-11, -18)
        ctx.line_to(-6, -28)
        ctx.line_to(0, -26)
        ctx.line_to(6, -28)
        ctx.line_to(11, -18)
        ctx.close_path()
        ctx.fill()

        # Piercing Eyes
        ctx.set_source_rgb(0.1, 0.1, 0.2)
        ctx.arc(-4, -18, 1.8, 0, 2 * math.pi)
        ctx.arc(4, -18, 1.8, 0, 2 * math.pi)
        ctx.fill()

        # 4. The Infinity Gauntlet (Left Arm Raised Forward)
        ctx.save()
        ctx.translate(14, -4)
        # Golden Gauntlet body
        ctx.set_source_rgb(0.95, 0.80, 0.18)
        ctx.rectangle(0, -5, 14, 10)
        ctx.fill()
        ctx.arc(14, 0, 5.5, 0, 2 * math.pi)
        ctx.fill()

        # 6 Infinity Stones
        # Space (Blue), Reality (Red), Power (Purple), Time (Green), Soul (Orange), Mind (Center Yellow)
        gem_specs = [
            (14, -3, (0.1, 0.5, 1.0)),    # Space
            (17, -1, (0.95, 0.1, 0.1)),   # Reality
            (17, 2, (0.8, 0.1, 0.9)),     # Power
            (14, 4, (0.1, 0.9, 0.2)),     # Time
            (11, -1, (1.0, 0.5, 0.0)),    # Soul
            (14, 0, (1.0, 0.95, 0.2)),    # Mind (Big center stone)
        ]
        for gx, gy, col in gem_specs:
            ctx.set_source_rgb(col[0], col[1], col[2])
            radius = 2.0 if col[0] == 1.0 and col[1] == 0.95 else 1.4
            ctx.arc(gx, gy, radius, 0, 2 * math.pi)
            ctx.fill()

        ctx.restore()
        ctx.restore()


skin_manager.register("thanos", ThanosCharacter)
