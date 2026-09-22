"""Batman character: grappling hook physics, batarang projectiles, and scalloped cape gliding."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, List, Optional
from skins.base import BaseCharacter, CharacterState, BaseProjectile
from core.particles import ParticleManager, SMOKE_GREY
from core.window import WebRopeWindow
from core.platforms import platform_manager


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
        if self.x < min_x or self.x > min_x + w or self.y < min_y or self.y > min_y + h or self.life <= 0:
            self.active = False
            particle_mgr.burst_sparks(self.x, self.y, count=6, color=(0.85, 0.88, 0.95), size=2.0)

    def draw(self, ctx: cairo.Context) -> None:
        if not self.active:
            return
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.rotate(self.angle)
        ctx.set_source_rgb(0.08, 0.08, 0.10)
        ctx.new_path()
        ctx.move_to(-12, 0)
        ctx.curve_to(-8, -8, -3, -9, 0, -3)
        ctx.curve_to(3, -9, 8, -8, 12, 0)
        ctx.curve_to(7, 4, 3, 5, 0, 2)
        ctx.curve_to(-3, 5, -7, 4, -12, 0)
        ctx.close_path()
        ctx.fill()
        ctx.set_source_rgba(0.85, 0.90, 0.98, 0.75)
        ctx.set_line_width(0.8)
        ctx.stroke()
        ctx.restore()


class BatmanCharacter(BaseCharacter):
    """The Dark Knight with grapple hook climb, scalloped cape gliding, Batarangs, and gothic perching."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="batman")
        self.can_fly = True
        self.is_grappling = False
        self.anchor_x = x
        self.anchor_y = y - 160.0
        self.grapple_target = (self.anchor_x, self.anchor_y)
        self.rope_window: Optional[WebRopeWindow] = None
        self.batarangs: List[Batarang] = []
        self.batarang_timer = 0.0
        self.smoke_timer = 0.0
        self.is_gliding = False
        self.is_perched = False
        self.current_ledge = None
        self.nav_target: Optional[Tuple[float, float]] = None
        self.nav_stage = "IDLE"  # "RUN", "GRAPPLE", "GLIDE", "LAND", "IDLE"
        self.nav_timer = 0.0
        self.stride = 0.0
        self.action_timer = time.time() + random.uniform(3.0, 6.0)

    def get_grapple_hand_pos(self) -> Tuple[float, float]:
        dir_mult = 1.0 if self.facing_right else -1.0
        return self.x + dir_mult * 8.0, self.y - 12.0

    def get_anchor_pos(self) -> Tuple[float, float]:
        return self.anchor_x, self.anchor_y

    def get_cable_alpha(self) -> float:
        return 1.0 if (self.is_grappling or self.nav_stage == "GRAPPLE") else 0.0

    def _ensure_grapple_rope(self) -> None:
        if self.rope_window is None:
            try:
                self.rope_window = WebRopeWindow(
                    start_getter=self.get_grapple_hand_pos,
                    end_getter=self.get_anchor_pos,
                    alpha_getter=self.get_cable_alpha,
                    rope_style="grapple"
                )
            except Exception:
                self.rope_window = None

    def _destroy_grapple_rope(self) -> None:
        if self.rope_window is not None:
            try:
                self.rope_window.destroy_rope()
            except Exception:
                pass
            self.rope_window = None

    def _destroy_swing_rope(self) -> None:
        self._destroy_grapple_rope()

    def cleanup_rope(self) -> None:
        self._destroy_grapple_rope()

    def destroy(self) -> None:
        self._destroy_grapple_rope()

    def __del__(self) -> None:
        self._destroy_grapple_rope()

    def nav_to(self, target_x: float, target_y: float) -> None:
        """Initiate multi-stage superhero movement (run -> grapple climb -> cape glide -> land)."""
        self.nav_target = (target_x, target_y)
        self.nav_stage = "RUN"
        self.nav_timer = time.time()
        self.is_gliding = False
        self.is_grappling = False
        self.is_perched = False

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        if ability_name == "grapple":
            self.is_perched = False
            self.is_gliding = False
            self.is_grappling = True
            self.anchor_x = target_x
            self.anchor_y = min(target_y, self.y - 120.0)
            self.grapple_target = (self.anchor_x, self.anchor_y)
            self._ensure_grapple_rope()
            audio_mgr.play("grapple")
            particle_mgr.burst_sparks(self.anchor_x, self.anchor_y, count=12, color=(0.85, 0.85, 0.95), size=2.5)
            return True

        elif ability_name == "batarang":
            self.facing_right = (target_x >= self.x)
            dir_mult = 1.0 if self.facing_right else -1.0
            hand_x = self.x + dir_mult * 14.0
            hand_y = self.y - 4.0
            self.batarang_timer = time.time() + 0.6

            def _on_catch():
                particle_mgr.burst_sparks(self.x, self.y, count=8, color=(0.85, 0.88, 0.95), size=2.2)

            try:
                from core.projectiles import DesktopProjectileWindow
                DesktopProjectileWindow(
                    proj_type="batarang",
                    start_x=hand_x,
                    start_y=hand_y,
                    target_x=target_x,
                    target_y=target_y,
                    owner_getter=lambda: (self.x, self.y),
                    on_catch=_on_catch,
                    speed=28.0
                )
            except Exception:
                dx = target_x - self.x
                dy = target_y - self.y
                dist = math.hypot(dx, dy) + 1e-4
                self.batarangs.append(Batarang(self.x, self.y, (dx / dist) * 20.0, (dy / dist) * 20.0))

            audio_mgr.play("grapple")
            particle_mgr.burst_sparks(hand_x, hand_y, count=8, color=(0.85, 0.90, 1.0), size=2.2)
            return True

        elif ability_name == "cape_glide":
            self.is_perched = False
            self.is_gliding = True
            self.vy = 1.0  # gentle descent
            self.state = CharacterState.FLY
            audio_mgr.play("swoosh")
            return True

        elif ability_name in ("smoke_bomb", "smoke"):
            self._destroy_grapple_rope()
            self.is_grappling = False
            self.is_gliding = False
            self.is_perched = False
            self.smoke_timer = time.time() + 1.2
            for _ in range(16):
                particle_mgr.smoke_puff(
                    self.x + random.uniform(-18, 18),
                    self.y + random.uniform(-14, 14),
                    count=2,
                    color=(0.14, 0.14, 0.18)
                )
            particle_mgr.burst_sparks(self.x, self.y, count=10, color=(0.9, 0.9, 0.95), size=2.5)
            self.x = target_x
            self.y = target_y
            self.vx = 0.0
            self.vy = 0.0
            audio_mgr.play("swoosh")
            particle_mgr.smoke_puff(self.x, self.y + 16, count=4)
            return True

        elif ability_name in ("perch", "crouch"):
            self._destroy_grapple_rope()
            self.is_grappling = False
            self.is_gliding = False
            self.is_perched = True
            self.state = CharacterState.IDLE
            self.vx = 0.0
            self.vy = 0.0
            self.tilt = 0.0
            ledge = platform_manager.is_on_ledge(self.x, self.y, tolerance=30.0) or platform_manager.get_nearest_ledge(self.x, self.y, max_dist=50.0)
            if ledge:
                self.current_ledge = ledge
                self.y = ledge.top
            particle_mgr.smoke_puff(self.x, self.y + 16, count=3)
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
        if self.nav_target is None and not self.is_grappling:
            if abs(cursor_x - self.x) > 6.0:
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
                self._destroy_grapple_rope()
                self.state = CharacterState.IDLE
                self.vx = 0.0
                self.vy = 0.0
                self.tilt = 0.0
                # Check for window ledge / button perch
                ledge = platform_manager.is_on_ledge(self.x, self.y, tolerance=24.0) or platform_manager.get_nearest_ledge(self.x, self.y, max_dist=40.0)
                if ledge:
                    self.current_ledge = ledge
                    self.is_perched = True
                    self.y = ledge.top
                particle_mgr.smoke_puff(self.x, self.y + 16, count=3)
            else:
                elapsed = time.time() - self.nav_timer
                if dist > 140.0:
                    if self.nav_stage == "RUN":
                        # Stage 1: Tactical sprint
                        self.state = CharacterState.RUN
                        self.stride += 0.28 * speed_mult
                        dir_sign = 1.0 if dx > 0 else -1.0
                        self.vx = dir_sign * 13.0 * speed_mult
                        self.x += self.vx
                        self.tilt += (0.0 - self.tilt) * 0.2
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
                        climb_spd = 24.0 * speed_mult
                        if adist > 30.0 and elapsed < 1.1:
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
                            self._destroy_grapple_rope()
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
                        if dist < 30.0 or elapsed > 2.2:
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

        # 2. STANDARD GROUND & LEDGE PATROL (When not navigating)
        elif self.is_grappling:
            self._ensure_grapple_rope()
            if self.rope_window:
                self.rope_window.update()
            gx, gy = self.anchor_x, self.anchor_y
            dx = gx - self.x
            dy = gy - self.y
            dist = math.hypot(dx, dy)
            if dist > 25.0:
                self.vx += (dx / dist) * 2.5
                self.vy += (dy / dist) * 2.5
                self.state = "GRAPPLE"
                self.x += self.vx
                self.y += self.vy
            else:
                self.is_grappling = False
                self._destroy_grapple_rope()
                self.state = CharacterState.FLY
                self.is_gliding = True
                particle_mgr.smoke_puff(self.x, self.y + 10, count=2)
        elif self.is_gliding:
            self.state = CharacterState.FLY
            self.vy += 0.35
            self.vx *= 0.98
            self.x += self.vx
            self.y += self.vy
            target_tilt = (self.vx / 12.0) * 0.25
            self.tilt += (target_tilt - self.tilt) * 0.18
            if self.y >= ground_y:
                self.y = ground_y
                self.vy = 0.0
                self.is_gliding = False
                self.state = CharacterState.IDLE
                particle_mgr.smoke_puff(self.x, ground_y + 16, count=3)
        else:
            # Random personality events
            if now >= self.action_timer and activity > 0.1:
                self.action_timer = now + random.uniform(4.0, 8.0) / max(0.2, activity)
                roll = random.random()
                if roll < 0.40 and abs(cursor_y - self.y) > 120.0:
                    self.trigger_ability("grapple", cursor_x, cursor_y - 120.0, particle_mgr, audio_mgr)
                elif roll < 0.70:
                    self.trigger_ability("batarang", cursor_x, cursor_y, particle_mgr, audio_mgr)
                elif roll < 0.85 and self.y >= ground_y - 5.0:
                    self.trigger_ability("perch", self.x, self.y, particle_mgr, audio_mgr)

            # Check for window ledge (require genuine physical surface)
            current_ledge = platform_manager.is_on_ledge(self.x, self.y, tolerance=16.0, require_real=True)
            if current_ledge:
                self.current_ledge = current_ledge
                self.vy = 0.0
                if self.is_perched:
                    self.y = current_ledge.top
                    self.state = CharacterState.IDLE
                    self.vx *= 0.75
                else:
                    dx = cursor_x - self.x
                    dist_x = abs(dx)
                    if dist_x > 30.0:
                        self.state = CharacterState.RUN
                        self.stride += 0.22 * speed_mult
                        target_vx = (1.0 if dx > 0 else -1.0) * min(10.0, dist_x * 0.08) * speed_mult
                        self.vx += (target_vx - self.vx) * 0.22
                        self.x += self.vx
                        self.x = max(current_ledge.left + 15.0, min(current_ledge.right - 15.0, self.x))
                    else:
                        self.state = CharacterState.IDLE
                        self.vx *= 0.80
                    self.y = current_ledge.top
            elif self.y >= ground_y - 3.0:
                self.current_ledge = None
                self.vy = 0.0
                if self.is_perched:
                    self.y = ground_y
                    self.state = CharacterState.IDLE
                    self.vx *= 0.75
                else:
                    dx = cursor_x - self.x
                    dy = cursor_y - self.y
                    dist_x = abs(dx)
                    # If cursor is far elevated, fire grapple gun!
                    if dy < -220.0 and activity > 0.3 and dist_x < 300.0:
                        self.trigger_ability("grapple", cursor_x, cursor_y - 80.0, particle_mgr, audio_mgr)
                    elif dist_x > 25.0:
                        self.y = ground_y
                        self.state = CharacterState.RUN
                        self.stride += 0.24 * speed_mult
                        target_vx = (1.0 if dx > 0 else -1.0) * min(11.0, dist_x * 0.09) * speed_mult
                        self.vx += (target_vx - self.vx) * 0.22
                        self.x += self.vx
                        self.tilt += (0.0 - self.tilt) * 0.2
                    else:
                        self.y = ground_y
                        self.state = CharacterState.IDLE
                        self.vx *= 0.80
            else:
                # Airborne falling with gravity
                self.vy += 0.85
                self.vx *= 0.95
                self.x += self.vx
                self.y += self.vy
                self.state = CharacterState.FLY
                if self.y >= ground_y:
                    self.y = ground_y
                    self.vy = 0.0
                    self.tilt = 0.0
                    self.state = CharacterState.IDLE
                    particle_mgr.smoke_puff(self.x, ground_y + 16, count=2)

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(ground_y, self.y))

        # Always update rope window if initialized
        if self.rope_window:
            self.rope_window.update()

        # Update local Batarangs if active
        for b in self.batarangs:
            b.update(dt, screen_bounds, particle_mgr, audio_mgr)
        self.batarangs = [b for b in self.batarangs if b.active]

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()

        # Draw any fallback local batarangs
        for b in self.batarangs:
            b.draw(ctx)

        effective_tilt = 0.0 if (self.is_perched or self.state == CharacterState.IDLE) else self.tilt
        ctx.translate(self.x, self.y)
        ctx.rotate(effective_tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        is_running = (self.state == CharacterState.RUN)
        run_cycle = self.stride * 4.5 if is_running else 0.0
        sin_run = math.sin(run_cycle)
        cos_run = math.cos(run_cycle)

        # -------------------------------------------------------------
        # 1. SCALLOPED BAT CAPE
        # -------------------------------------------------------------
        ctx.save()
        ctx.set_source_rgb(0.08, 0.08, 0.10)  # Dark cowl black

        if self.is_gliding:
            # Wide aerodynamic gliding bat-wings!
            ctx.new_path()
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

        elif self.is_perched:
            # Gothic gargoyle shroud: cape drapes around entire crouched body
            ctx.new_path()
            ctx.move_to(-8, -10)
            ctx.curve_to(-18, 0, -22, 16, -18, 28)
            ctx.curve_to(-12, 26, -6, 28, 0, 25)
            ctx.curve_to(6, 28, 12, 26, 18, 28)
            ctx.curve_to(20, 14, 16, -2, 8, -10)
            ctx.close_path()
            ctx.fill()
            # Shroud fold creases
            ctx.set_source_rgb(0.14, 0.14, 0.16)
            ctx.set_line_width(1.2)
            ctx.move_to(-4, -6)
            ctx.curve_to(-10, 8, -12, 18, -12, 27)
            ctx.stroke()
            ctx.move_to(4, -6)
            ctx.curve_to(10, 8, 12, 18, 12, 27)
            ctx.stroke()

        else:
            # Billowing cape behind shoulders with animated flutter
            flutter = math.sin(self.anim_time * 6.0 + (sin_run * 1.5)) * 3.2 if is_running else math.sin(self.anim_time * 2.5) * 1.5
            ctx.new_path()
            ctx.move_to(-5, -8)
            ctx.curve_to(-18 - flutter, 2, -26 - flutter * 1.4, 12, -24 - flutter, 26)
            ctx.curve_to(-18, 21, -12, 26, -8, 22)
            ctx.curve_to(-4, 26, 2, 21, 6, 25)
            ctx.line_to(5, -8)
            ctx.close_path()
            ctx.fill()
            # Inner fold highlight
            ctx.set_source_rgb(0.13, 0.13, 0.16)
            ctx.set_line_width(1.2)
            ctx.move_to(-2, -6)
            ctx.curve_to(-10, 8, -14, 16, -14 - flutter * 0.5, 24)
            ctx.stroke()

        ctx.restore()

        # -------------------------------------------------------------
        # 2. ARTICULATED LEGS & TACTICAL COMBAT BOOTS
        # -------------------------------------------------------------
        ctx.save()
        BAT_GREY_DARK = (0.20, 0.22, 0.25)
        BAT_GREY = (0.28, 0.30, 0.34)
        BAT_BLACK = (0.08, 0.08, 0.10)

        if self.is_perched:
            # Crouched gargoyle knees: thighs angled out, combat boots planted
            ctx.set_source_rgb(*BAT_GREY_DARK)
            ctx.set_line_width(6.5)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            # Far leg
            ctx.move_to(-4, 12)
            ctx.line_to(-14, 18)
            ctx.line_to(-11, 27)
            ctx.stroke()
            # Far boot
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.set_line_width(6.0)
            ctx.move_to(-12, 23)
            ctx.line_to(-11, 28)
            ctx.line_to(-7, 28)
            ctx.stroke()

            # Near leg
            ctx.set_source_rgb(*BAT_GREY)
            ctx.set_line_width(7.0)
            ctx.move_to(4, 12)
            ctx.line_to(14, 18)
            ctx.line_to(11, 27)
            ctx.stroke()
            # Near boot
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.set_line_width(6.5)
            ctx.move_to(12, 23)
            ctx.line_to(11, 28)
            ctx.line_to(15, 28)
            ctx.stroke()

        elif self.is_gliding:
            # Aerodynamic trailing legs behind cape
            ctx.set_source_rgb(*BAT_GREY_DARK)
            ctx.set_line_width(6.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-3, 12)
            ctx.line_to(-8, 20)
            ctx.line_to(-12, 26)
            ctx.stroke()
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.set_line_width(5.5)
            ctx.move_to(-9, 21)
            ctx.line_to(-12, 27)
            ctx.stroke()

            # Near leg
            ctx.set_source_rgb(*BAT_GREY)
            ctx.set_line_width(6.5)
            ctx.move_to(3, 12)
            ctx.line_to(0, 21)
            ctx.line_to(-4, 27)
            ctx.stroke()
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.set_line_width(6.0)
            ctx.move_to(-1, 22)
            ctx.line_to(-4, 28)
            ctx.stroke()

        elif is_running:
            # Tactical runner stride
            # Far leg
            far_knee_x = -4.0 - sin_run * 8.0
            far_knee_y = 12.0 + 8.0 + max(0.0, sin_run * 3.5)
            far_foot_x = far_knee_x - sin_run * 7.0
            far_foot_y = far_knee_y + 8.0 - max(0.0, -sin_run * 4.0)

            ctx.set_source_rgb(*BAT_GREY_DARK)
            ctx.set_line_width(6.5)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-4, 12)
            ctx.line_to(far_knee_x, far_knee_y)
            ctx.line_to(far_foot_x, far_foot_y)
            ctx.stroke()

            # Far combat boot
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.set_line_width(5.8)
            ctx.move_to(far_knee_x + (far_foot_x - far_knee_x) * 0.4, far_knee_y + (far_foot_y - far_knee_y) * 0.4)
            ctx.line_to(far_foot_x, far_foot_y)
            ctx.line_to(far_foot_x + 3.0, far_foot_y + 1.0)
            ctx.stroke()

            # Near leg
            near_knee_x = 4.0 + sin_run * 9.0
            near_knee_y = 12.0 + 7.5 - max(0.0, sin_run * 5.0)
            near_foot_x = near_knee_x + sin_run * 8.0
            near_foot_y = near_knee_y + 8.5 + max(0.0, -sin_run * 3.5)

            ctx.set_source_rgb(*BAT_GREY)
            ctx.set_line_width(7.0)
            ctx.move_to(4, 12)
            ctx.line_to(near_knee_x, near_knee_y)
            ctx.line_to(near_foot_x, near_foot_y)
            ctx.stroke()

            # Near combat boot
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.set_line_width(6.5)
            ctx.move_to(near_knee_x + (near_foot_x - near_knee_x) * 0.4, near_knee_y + (near_foot_y - near_knee_y) * 0.4)
            ctx.line_to(near_foot_x, near_foot_y)
            ctx.line_to(near_foot_x + 3.5, near_foot_y + 1.2)
            ctx.stroke()

        else:
            # Solid grounded tactical stance
            # Far leg
            ctx.set_source_rgb(*BAT_GREY_DARK)
            ctx.set_line_width(6.5)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-4, 12)
            ctx.line_to(-7, 20)
            ctx.line_to(-8, 27)
            ctx.stroke()
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.set_line_width(6.0)
            ctx.move_to(-7, 22)
            ctx.line_to(-8, 28)
            ctx.line_to(-5, 28)
            ctx.stroke()

            # Near leg
            ctx.set_source_rgb(*BAT_GREY)
            ctx.set_line_width(7.0)
            ctx.move_to(4, 12)
            ctx.line_to(6, 20)
            ctx.line_to(7, 27)
            ctx.stroke()
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.set_line_width(6.5)
            ctx.move_to(6, 22)
            ctx.line_to(7, 28)
            ctx.line_to(11, 28)
            ctx.stroke()

        ctx.restore()

        # -------------------------------------------------------------
        # 3. BODY & TACTICAL KEVLAR BATSUIT
        # -------------------------------------------------------------
        # Armored Torso with muscular chest bevel
        ctx.save()
        ctx.set_source_rgb(*BAT_GREY)
        ctx.new_path()
        ctx.move_to(-10, -8)
        ctx.line_to(10, -8)
        ctx.line_to(8, 12)
        ctx.line_to(-8, 12)
        ctx.close_path()
        ctx.fill()

        # Kevlar plate abdominal contour lines
        ctx.set_source_rgb(0.20, 0.22, 0.26)
        ctx.set_line_width(1.0)
        ctx.move_to(0, -8)
        ctx.line_to(0, 11)
        ctx.stroke()
        for py in [-2, 3, 8]:
            ctx.move_to(-6, py)
            ctx.line_to(6, py)
            ctx.stroke()

        # Golden Utility Belt with brass buckle and capsule pouches
        ctx.set_source_rgb(0.85, 0.70, 0.15)
        ctx.rectangle(-9, 10, 18, 4.5)
        ctx.fill()
        for bx in [-6, -2, 2, 6]:
            ctx.set_source_rgb(0.70, 0.55, 0.10)
            ctx.rectangle(bx - 1.0, 9.5, 2.5, 5.5)
            ctx.fill()
        # Buckle center
        ctx.set_source_rgb(0.95, 0.85, 0.30)
        ctx.rectangle(-2, 9.5, 4, 5.5)
        ctx.fill()

        # Bat Emblem on Chest
        ctx.set_source_rgb(*BAT_BLACK)
        ctx.new_path()
        ctx.move_to(-8, -4)
        ctx.line_to(0, -6.5)
        ctx.line_to(8, -4)
        ctx.line_to(5, 2)
        ctx.line_to(0, 5.5)
        ctx.line_to(-5, 2)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 4. ARMS & BLADED GAUNTLETS
        # -------------------------------------------------------------
        ctx.save()
        if self.is_grappling:
            # Lead arm raised aiming Bat-Claw grapple gun upward!
            ctx.set_source_rgb(*BAT_GREY)
            ctx.set_line_width(6.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(6, -6)
            ctx.line_to(12, -14)
            ctx.line_to(10, -22)
            ctx.stroke()
            # Gauntlet
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.move_to(12, -14)
            ctx.line_to(10, -22)
            ctx.stroke()
            # Grapple gun muzzle
            ctx.set_source_rgb(0.35, 0.38, 0.45)
            ctx.rectangle(8, -26, 4, 5)
            ctx.fill()

            # Trailing arm back for balance
            ctx.set_source_rgb(*BAT_GREY_DARK)
            ctx.move_to(-6, -6)
            ctx.line_to(-14, 2)
            ctx.line_to(-16, 10)
            ctx.stroke()
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.move_to(-14, 2)
            ctx.line_to(-16, 10)
            ctx.stroke()

        elif self.is_gliding:
            # Arms extended holding cape leading edge
            ctx.set_source_rgb(*BAT_GREY)
            ctx.set_line_width(6.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(6, -6)
            ctx.line_to(22, -4)
            ctx.stroke()
            ctx.move_to(-6, -6)
            ctx.line_to(-22, -4)
            ctx.stroke()
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.move_to(16, -5)
            ctx.line_to(24, -4)
            ctx.stroke()
            ctx.move_to(-16, -5)
            ctx.line_to(-24, -4)
            ctx.stroke()

        elif is_running:
            # Dynamic runner arm pump
            arm_sin = sin_run * 7.0
            ctx.set_source_rgb(*BAT_GREY_DARK)
            ctx.set_line_width(6.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-6, -6)
            ctx.line_to(-12 - arm_sin, 2)
            ctx.line_to(-10 - arm_sin, 10)
            ctx.stroke()
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.move_to(-12 - arm_sin, 2)
            ctx.line_to(-10 - arm_sin, 10)
            ctx.stroke()

            ctx.set_source_rgb(*BAT_GREY)
            ctx.set_line_width(6.5)
            ctx.move_to(6, -6)
            ctx.line_to(12 + arm_sin, 2)
            ctx.line_to(10 + arm_sin, 10)
            ctx.stroke()
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.move_to(12 + arm_sin, 2)
            ctx.line_to(10 + arm_sin, 10)
            ctx.stroke()
            # Gauntlet blades
            for blade_y in [4, 7, 10]:
                ctx.move_to(12 + arm_sin, blade_y)
                ctx.line_to(16 + arm_sin, blade_y + 2)
                ctx.line_to(12 + arm_sin, blade_y + 3)
                ctx.fill()

        elif self.is_perched:
            # Hands resting firmly on crouched knees
            ctx.set_source_rgb(*BAT_GREY)
            ctx.set_line_width(6.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-6, -6)
            ctx.line_to(-10, 6)
            ctx.line_to(-12, 16)
            ctx.stroke()
            ctx.move_to(6, -6)
            ctx.line_to(10, 6)
            ctx.line_to(12, 16)
            ctx.stroke()
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.move_to(-10, 8)
            ctx.line_to(-12, 16)
            ctx.stroke()
            ctx.move_to(10, 8)
            ctx.line_to(12, 16)
            ctx.stroke()

        else:
            # Tactical idle: clenched fists beside utility belt
            breath = math.sin(self.anim_time * 2.8) * 0.8
            ctx.set_source_rgb(*BAT_GREY_DARK)
            ctx.set_line_width(6.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-6, -6)
            ctx.line_to(-10, 2)
            ctx.line_to(-9, 10 + breath)
            ctx.stroke()
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.arc(-9, 10 + breath, 3.2, 0, 2 * math.pi)
            ctx.fill()

            ctx.set_source_rgb(*BAT_GREY)
            ctx.set_line_width(6.5)
            ctx.move_to(6, -6)
            ctx.line_to(10, 2)
            ctx.line_to(9, 10 + breath)
            ctx.stroke()
            ctx.set_source_rgb(*BAT_BLACK)
            ctx.arc(9, 10 + breath, 3.4, 0, 2 * math.pi)
            ctx.fill()

            # Gauntlet forearm blades
            for blade_y in [2, 5, 8]:
                ctx.move_to(11, blade_y + breath)
                ctx.line_to(15, blade_y + 2 + breath)
                ctx.line_to(11, blade_y + 3 + breath)
                ctx.fill()

        ctx.restore()

        # -------------------------------------------------------------
        # 5. COWL, POINTED BAT EARS & EYES
        # -------------------------------------------------------------
        ctx.save()
        ctx.set_source_rgb(*BAT_BLACK)
        ctx.arc(0, -15, 9.5, 0, 2 * math.pi)
        ctx.fill()

        # Chiseled jawline cutout
        ctx.set_source_rgb(0.92, 0.78, 0.68)
        ctx.new_path()
        ctx.move_to(-4, -9)
        ctx.line_to(0, -7)
        ctx.line_to(4, -9)
        ctx.line_to(2, -5.5)
        ctx.line_to(-2, -5.5)
        ctx.close_path()
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

        ctx.restore()
        ctx.restore()
