"""Batman character: grappling hook physics, batarang projectiles, and scalloped cape gliding."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, List, Optional
from skins.base import BaseCharacter, CharacterState, BaseProjectile
from core.particles import ParticleManager, SMOKE_GREY
from core.window import WebRopeWindow


class Batarang(BaseProjectile):
    """Spinning Bat gadget projectile."""

    def __init__(self, x: float, y: float, vx: float, vy: float):
        super().__init__(x, y)
        self.vx = vx
        self.vy = vy
        self.active = True
        self.life = 1.0

    def update(self, dt: float, screen_bounds: Tuple[int, int, int, int], particle_mgr: ParticleManager, audio_mgr: Any) -> None:
        self.x += self.vx
        self.y += self.vy
        self.angle += 0.45
        self.life -= 0.02
        min_x, min_y, w, h = screen_bounds
        if self.x < min_x or self.x > min_x + w or self.y < min_y + h or self.life <= 0:
            self.active = False
            particle_mgr.burst_sparks(self.x, self.y, count=4, color=(0.8, 0.8, 0.8), size=1.5)

    def draw(self, ctx: cairo.Context) -> None:
        if not self.active:
            return
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.rotate(self.angle)
        ctx.set_source_rgb(0.1, 0.1, 0.12)
        ctx.new_path()
        ctx.move_to(-10, 0)
        ctx.curve_to(-5, -6, 5, -6, 10, 0)
        ctx.curve_to(5, 3, -5, 3, -10, 0)
        ctx.fill()
        ctx.restore()


class BatmanCharacter(BaseCharacter):
    """The Dark Knight with grapple hook climb, scalloped cape gliding, and Batarangs."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="batman")
        self.can_fly = True
        self.is_grappling = False
        self.anchor_x = x
        self.anchor_y = y - 160.0
        self.grapple_target = (self.anchor_x, self.anchor_y)
        self.rope_window: Optional[WebRopeWindow] = None
        self.batarangs: List[Batarang] = []
        self.is_gliding = False
        self.nav_target: Optional[Tuple[float, float]] = None
        self.nav_stage = "IDLE"  # "RUN", "GRAPPLE", "GLIDE", "LAND", "IDLE"
        self.nav_timer = 0.0
        self.stride = 0.0
        self.action_timer = time.time() + random.uniform(3.0, 6.0)

    def get_grapple_hand_pos(self) -> Tuple[float, float]:
        dir_mult = 1.0 if self.facing_right else -1.0
        return self.x + dir_mult * 8.0, self.y - 8.0

    def get_anchor_pos(self) -> Tuple[float, float]:
        return self.anchor_x, self.anchor_y

    def get_cable_alpha(self) -> float:
        return 1.0 if (self.is_grappling or self.nav_stage == "GRAPPLE") else 0.0

    def _ensure_grapple_rope(self) -> None:
        if self.rope_window is None:
            self.rope_window = WebRopeWindow(
                start_getter=self.get_grapple_hand_pos,
                end_getter=self.get_anchor_pos,
                alpha_getter=self.get_cable_alpha,
                rope_style="grapple"
            )

    def _destroy_grapple_rope(self) -> None:
        if self.rope_window is not None:
            try:
                self.rope_window.destroy_rope()
            except Exception:
                pass
            self.rope_window = None

    def destroy(self) -> None:
        self._destroy_grapple_rope()

    def nav_to(self, target_x: float, target_y: float) -> None:
        """Initiate multi-stage superhero movement (run -> grapple climb -> cape glide -> land)."""
        self.nav_target = (target_x, target_y)
        self.nav_stage = "RUN"
        self.nav_timer = time.time()
        self.is_gliding = False
        self.is_grappling = False

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        if ability_name == "grapple":
            self.is_grappling = True
            self.anchor_x = target_x
            self.anchor_y = min(target_y, self.y - 120.0)
            self.grapple_target = (self.anchor_x, self.anchor_y)
            self._ensure_grapple_rope()
            audio_mgr.play("grapple")
            particle_mgr.burst_sparks(self.anchor_x, self.anchor_y, count=10, color=(0.85, 0.85, 0.95), size=2.5)
            return True
        elif ability_name == "batarang":
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.batarangs.append(Batarang(self.x, self.y, (dx / dist) * 18.0, (dy / dist) * 18.0))
            audio_mgr.play("grapple")
            return True
        elif ability_name == "cape_glide":
            self.is_gliding = True
            self.vy = 1.0  # gentle descent
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
        speed_mult = config_data.get("speed", 1.0)
        ground_y = min_y + screen_h - 70.0

        # Facing direction
        if self.nav_target is None:
            self.facing_right = (cursor_x >= self.x)

        # 1. MULTI-STAGE AUTONOMOUS NAVIGATION (Run -> Grapple Climb -> Cape Glide -> Land)
        if self.nav_target is not None:
            tx, ty = self.nav_target
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            self.facing_right = (dx >= 0.0)

            if dist < 26.0:
                self.nav_target = None
                self.nav_stage = "IDLE"
                self.is_grappling = False
                self.is_gliding = False
                self.state = CharacterState.IDLE
                self.vx = 0.0
                self.vy = 0.0
                self.tilt = 0.0
                particle_mgr.smoke_puff(self.x, self.y + 16, count=3)
            else:
                elapsed = time.time() - self.nav_timer
                if dist > 120.0:
                    if self.nav_stage == "RUN":
                        # Stage 1: Tactical sprint
                        self.state = CharacterState.RUN
                        self.stride += 0.28 * speed_mult
                        dir_sign = 1.0 if dx > 0 else -1.0
                        self.vx = dir_sign * 13.0 * speed_mult
                        self.x += self.vx
                        if elapsed > 0.25:
                            # Stage 2: Fire high Bat-Claw grapple hook!
                            self.nav_stage = "GRAPPLE"
                            self.nav_timer = time.time()
                            self.anchor_x = (self.x + tx) / 2.0
                            self.anchor_y = max(30.0, min(self.y - 180.0, ty - 160.0))
                            self.grapple_target = (self.anchor_x, self.anchor_y)
                            self.is_grappling = True
                            self.state = "GRAPPLE"
                            self._ensure_grapple_rope()
                            audio_mgr.play("grapple")
                            particle_mgr.burst_sparks(self.anchor_x, self.anchor_y, count=12, color=(0.85, 0.85, 0.95), size=2.5)
                    elif self.nav_stage == "GRAPPLE":
                        # Stage 2: Rapid zip/climb along cable to overhead vantage point
                        self._ensure_grapple_rope()
                        if self.rope_window:
                            self.rope_window.update()
                        self.state = "GRAPPLE"
                        adx = self.anchor_x - self.x
                        ady = self.anchor_y - self.y
                        adist = math.hypot(adx, ady)
                        climb_spd = 22.0 * speed_mult
                        if adist > 28.0 and elapsed < 1.1:
                            self.vx = (adx / adist) * climb_spd
                            self.vy = (ady / adist) * climb_spd
                            self.x += self.vx
                            self.y += self.vy
                            self.tilt = (math.atan2(adx, -ady)) * 0.4
                            if random.random() < 0.35:
                                particle_mgr.burst_sparks(self.x, self.y - 8, count=2, color=(0.8, 0.8, 0.9), size=1.8)
                        else:
                            # Reached cable peak: release cable and deploy scalloped cape wings into aerodynamic GLIDE!
                            self.is_grappling = False
                            self.nav_stage = "GLIDE"
                            self.nav_timer = time.time()
                            self.is_gliding = True
                            self.state = CharacterState.FLY
                            audio_mgr.play("swoosh")
                            particle_mgr.smoke_puff(self.x, self.y + 12, count=3)
                    elif self.nav_stage == "GLIDE":
                        # Stage 3: Scalloped cape glide descent straight to target
                        self.state = CharacterState.FLY
                        self.is_gliding = True
                        follow_spd = min(16.0, max(5.0, dist * 0.12)) * speed_mult
                        target_vx = (dx / dist) * follow_spd
                        target_vy = (dy / dist) * follow_spd
                        self.vx += (target_vx - self.vx) * 0.22
                        self.vy += (target_vy - self.vy) * 0.22
                        self.x += self.vx
                        self.y += self.vy
                        target_tilt = (self.vx / 14.0) * 0.35
                        self.tilt += (target_tilt - self.tilt) * 0.20
                        if dist < 30.0 or elapsed > 2.0:
                            self.nav_target = None
                            self.nav_stage = "IDLE"
                            self.is_gliding = False
                            self.state = CharacterState.IDLE
                            self.vx = 0.0
                            self.vy = 0.0
                            self.tilt = 0.0
                            particle_mgr.smoke_puff(self.x, self.y + 16, count=3)
                else:
                    # Short range: tactical sprint straight to target
                    self.state = CharacterState.RUN
                    self.stride += 0.26 * speed_mult
                    follow_spd = min(14.0, max(4.0, dist * 0.14)) * speed_mult
                    self.vx = (dx / dist) * follow_spd
                    self.vy = (dy / dist) * follow_spd
                    self.x += self.vx
                    self.y += self.vy

        # 2. STANDARD WANDER (When not navigating)
        elif self.is_grappling:
            self._ensure_grapple_rope()
            if self.rope_window:
                self.rope_window.update()
            gx, gy = self.anchor_x, self.anchor_y
            dx = gx - self.x
            dy = gy - self.y
            dist = math.hypot(dx, dy)
            if dist > 25.0:
                self.vx += (dx / dist) * 2.2
                self.vy += (dy / dist) * 2.2
                self.state = "GRAPPLE"
            else:
                self.is_grappling = False
                self.state = CharacterState.FLY
                self.is_gliding = True
                particle_mgr.smoke_puff(self.x, self.y + 10, count=2)
        else:
            # Random personality events
            if now >= self.action_timer and activity > 0.1:
                self.action_timer = now + random.uniform(4.0, 8.0) / max(0.2, activity)
                roll = random.random()
                if roll < 0.45:
                    self.trigger_ability("grapple", cursor_x, cursor_y - 150.0, particle_mgr, audio_mgr)
                elif roll < 0.75:
                    self.trigger_ability("batarang", cursor_x, cursor_y, particle_mgr, audio_mgr)

            max_spd = 14.0 * speed_mult
            accel = 0.60 * speed_mult
            dx = cursor_x - self.x
            dy = cursor_y - self.y
            dist = math.hypot(dx, dy)

            if dist > 50.0:
                self.vx += (dx / dist) * min(dist * 0.06, accel)
                self.vy += (dy / dist) * min(dist * 0.06, accel)
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

            target_tilt = (self.vx / max_spd) * 0.25
            self.tilt += (target_tilt - self.tilt) * 0.15

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 50.0, self.y))

        # Always update rope window if initialized
        if self.rope_window:
            self.rope_window.update()

        # Update Batarangs
        for b in self.batarangs:
            b.update(dt, screen_bounds, particle_mgr, audio_mgr)
        self.batarangs = [b for b in self.batarangs if b.active]

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()

        # Draw batarangs
        for b in self.batarangs:
            b.draw(ctx)

        # Local cable attachment at hand if grappling
        if self.is_grappling:
            ctx.save()
            ctx.set_source_rgba(0.2, 0.2, 0.25, 0.9)
            ctx.set_line_width(1.6)
            ctx.move_to(self.x, self.y - 6)
            ctx.line_to(self.anchor_x, self.anchor_y)
            ctx.stroke()
            ctx.restore()

        ctx.translate(self.x, self.y)
        ctx.rotate(self.tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Scalloped Gliding Bat Cape
        ctx.save()
        ctx.set_source_rgb(0.08, 0.08, 0.10)  # Dark cowl black
        ctx.new_path()
        if self.is_gliding:
            # Wide aerodynamic gliding bat-wings!
            ctx.move_to(-6, -10)
            ctx.curve_to(-32, -8, -54, 8, -52, 22)
            ctx.curve_to(-40, 18, -28, 24, -18, 16)
            ctx.curve_to(-10, 24, 0, 18, 6, 22)
            ctx.curve_to(18, 24, 32, 18, 48, 22)
            ctx.curve_to(52, 8, 32, -8, 6, -10)
            ctx.close_path()
            ctx.fill()
            # Gliding cape wing spines
            ctx.set_source_rgb(0.14, 0.14, 0.18)
            ctx.set_line_width(1.4)
            for wx in [-44, -28, -12, 14, 30, 42]:
                ctx.move_to(0, -8)
                ctx.line_to(wx, 18)
            ctx.stroke()
        else:
            ctx.move_to(-4, -8)
            # Scalloped edges
            ctx.curve_to(-18, 0, -28, 8, -26, 26)
            ctx.curve_to(-20, 20, -14, 26, -10, 22)
            ctx.curve_to(-6, 26, 0, 20, 4, 24)
            ctx.line_to(4, -8)
            ctx.close_path()
            ctx.fill()
        ctx.restore()

        # 2. Body & Grey Batsuit
        ctx.set_source_rgb(0.28, 0.30, 0.34)  # Tactical grey suit
        ctx.rectangle(-9, -8, 18, 22)
        ctx.fill()

        # Golden Utility Belt
        ctx.set_source_rgb(0.85, 0.70, 0.15)
        ctx.rectangle(-10, 10, 20, 4.5)
        ctx.fill()
        for bx in [-6, -2, 2, 6]:
            ctx.set_source_rgb(0.70, 0.55, 0.10)
            ctx.rectangle(bx, 9, 3, 6)
            ctx.fill()

        # Bat Emblem on Chest
        ctx.set_source_rgb(0.08, 0.08, 0.10)
        ctx.new_path()
        ctx.move_to(-7, -4)
        ctx.line_to(0, -6)
        ctx.line_to(7, -4)
        ctx.line_to(4, 2)
        ctx.line_to(0, 5)
        ctx.line_to(-4, 2)
        ctx.close_path()
        ctx.fill()

        # 3. Cowl & Pointed Bat Ears
        ctx.set_source_rgb(0.08, 0.08, 0.10)
        ctx.arc(0, -15, 9, 0, 2 * math.pi)
        ctx.fill()

        # Pointed Bat Ears
        for ear_x, ear_rot in [(-5, -0.15), (5, 0.15)]:
            ctx.save()
            ctx.translate(ear_x, -21)
            ctx.rotate(ear_rot)
            ctx.new_path()
            ctx.move_to(-3, 4)
            ctx.line_to(0, -9)
            ctx.line_to(3, 4)
            ctx.close_path()
            ctx.fill()
            ctx.restore()

        # White glowing cowl eye lenses
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.new_path()
        ctx.move_to(-5, -16)
        ctx.line_to(-1, -14)
        ctx.line_to(-5, -13)
        ctx.close_path()
        ctx.fill()

        ctx.new_path()
        ctx.move_to(5, -16)
        ctx.line_to(1, -14)
        ctx.line_to(5, -13)
        ctx.close_path()
        ctx.fill()

        # Gauntlet blades
        ctx.set_source_rgb(0.12, 0.12, 0.15)
        ctx.rectangle(8, -4, 4, 12)
        ctx.fill()
        for blade_y in [0, 4, 8]:
            ctx.move_to(12, blade_y)
            ctx.line_to(16, blade_y + 2)
            ctx.line_to(12, blade_y + 3)
            ctx.fill()

        ctx.restore()
