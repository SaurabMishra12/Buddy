"""Spider-Man character: high-performance, 100% procedural vector Cairo superhero companion.
Equipped with realistic pendulum web-swinging physics, THWIP! web throw projectiles,
vibrating Spider-Sense danger detection, wall-crawling, and agile three-point perching.
Strictly 0 external images — sub-millisecond Cairo draw time and crisp at any DPI.
"""

import math
import random
import time
from typing import Tuple, Dict, Any, List, Optional
import cairo

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager
from core.projectiles import DesktopProjectileWindow
from core.window import WebRopeWindow
from core.platforms import platform_manager


class SpiderManCharacter(BaseCharacter):
    """Your friendly neighborhood Spider-Man desktop companion.
    Pure procedural Cairo vector art with iconic red & blue webbed suit, expressive white eye lenses,
    dynamic pendulum web-swinging, THWIP! web shooting, and spider-sense alerts.
    """

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="spiderman")
        self.can_fly = True  # Can traverse airborne via web-swinging
        self.hitbox_radius = 44.0

        # Web-swinging kinematics & pendulum physics
        self.is_swinging = False
        self.anchor_x = x
        self.anchor_y = 50.0
        self.web_length = 320.0
        self.swing_angle = 0.0
        self.swing_vel = 0.0
        self.swing_timer = 0.0
        self.swing_direction = 1.0

        # Abilities & expressive states
        self.spider_sense_timer = 0.0
        self.spider_sense_active = False
        self.eye_squint = 0.0  # -0.6 (wide surprise) to 0.8 (focused squint)
        self.web_shoot_timer = 0.0
        self.is_hanging_upside_down = False
        self.hang_end_time = 0.0
        self.is_perched = False
        self.is_seated = False
        self.is_wall_crawling = False
        self.action_timer = time.time() + random.uniform(3.0, 7.0)

        # Autonomous multi-stage navigation (run -> swing -> jump -> land/seat/perch)
        self.nav_target: Optional[Tuple[float, float]] = None
        self.nav_stage = "IDLE"  # "RUN", "SWING", "JUMP", "LAND"
        self.nav_timer = 0.0
        self.current_ledge = None

        # Cursor velocity tracking for reflex-based spider sense
        self.prev_cursor_x = x
        self.prev_cursor_y = y
        self.prev_cursor_time = time.time()

        # Leg & arm stride oscillation
        self.stride = 0.0
        self.web_target_x = x + 120.0
        self.web_target_y = y

        # Swing attack and web strike tracking
        self.is_swing_attacking = False
        self.attack_target_x = 0.0
        self.attack_target_y = 0.0
        self.attack_timer = 0.0

        # Dedicated screen-spanning web rope overlay for full unclipped swinging/hanging
        self.rope_window: Optional[WebRopeWindow] = None

    def _ensure_swing_rope(self) -> None:
        if self.rope_window is None:
            try:
                def get_hand_pos():
                    if not (self.is_swinging or self.is_hanging_upside_down or self.is_swing_attacking):
                        return (self.x, self.y)
                    if self.is_hanging_upside_down:
                        return (self.x, self.y + 15.0)
                    elif self.is_swing_attacking:
                        dir_mult = 1.0 if self.facing_right else -1.0
                        return (self.x + dir_mult * 24.0, self.y - 6.0)
                    else:
                        dir_mult = 1.0 if self.facing_right else -1.0
                        return (self.x + dir_mult * 8.0, self.y - 16.0)

                def get_anchor_pos():
                    if self.is_swing_attacking:
                        return (self.attack_target_x, self.attack_target_y)
                    return (self.anchor_x, self.anchor_y)

                def get_rope_alpha():
                    if self.is_swinging or self.is_hanging_upside_down or self.is_swing_attacking:
                        return 1.0
                    return 0.0

                self.rope_window = WebRopeWindow(
                    start_getter=get_hand_pos,
                    end_getter=get_anchor_pos,
                    rope_style="swing",
                    alpha_getter=get_rope_alpha
                )
            except Exception:
                self.rope_window = None

    def _destroy_swing_rope(self) -> None:
        self.cleanup_rope()

    def cleanup_rope(self) -> None:
        if self.rope_window is not None:
            try:
                self.rope_window.destroy_rope()
            except Exception:
                pass
            self.rope_window = None

    def __del__(self) -> None:
        self.cleanup_rope()

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        dir_mult = 1.0 if self.facing_right else -1.0
        wrist_x = self.x + dir_mult * 26.0
        wrist_y = self.y - 6.0

        if ability_name in ("web_swing", "swing"):
            now = time.time()
            self.is_hanging_upside_down = False
            self.is_perched = False
            self.is_wall_crawling = False
            self.is_seated = False
            self.is_swinging = True
            self.state = CharacterState.FLY
            self.swing_timer = now

            swing_dir = 1.0 if target_x >= self.x else -1.0
            self.facing_right = (swing_dir > 0)
            self.swing_direction = swing_dir

            # Anchor web to ceiling ahead of Spider-Man
            anchor_dist_x = min(320.0, max(120.0, abs(target_x - self.x) * 0.65))
            self.anchor_x = self.x + swing_dir * anchor_dist_x
            self.anchor_y = max(25.0, min(self.y - 180.0, 90.0))

            # Calibrate web length so the pendulum swing clears the ground comfortably
            max_safe_len = max(140.0, (self.y + 120.0) - self.anchor_y)
            curr_dist = math.hypot(self.x - self.anchor_x, self.y - self.anchor_y)
            self.web_length = max(140.0, min(curr_dist, max_safe_len))

            # Initial pendulum angle and impulse
            dx = max(-self.web_length * 0.95, min(self.web_length * 0.95, self.x - self.anchor_x))
            self.swing_angle = math.asin(dx / self.web_length)
            self.swing_vel = swing_dir * random.uniform(1.4, 2.2)

            self._ensure_swing_rope()

            audio_mgr.play("thwip")
            particle_mgr.burst_sparks(wrist_x, wrist_y, count=6, color=(0.95, 0.98, 1.0), size=2.5)
            self.web_shoot_timer = now + 0.35
            return True

        elif ability_name in ("web_throw", "web_shoot", "web"):
            self.facing_right = (target_x >= self.x)
            dir_mult = 1.0 if self.facing_right else -1.0
            wrist_x = self.x + dir_mult * 26.0
            wrist_y = self.y - 6.0
            self.web_target_x = target_x
            self.web_target_y = target_y
            self.web_shoot_timer = time.time() + 0.55
            self.eye_squint = 0.65  # Focused aiming squint
            audio_mgr.play("thwip")

            def _on_impact():
                particle_mgr.burst_sparks(target_x, target_y, count=18, color=(0.94, 0.97, 1.0), size=3.0)
                particle_mgr.shockwave(target_x, target_y, max_radius=65.0, color=(0.92, 0.96, 1.0))

            DesktopProjectileWindow(
                proj_type="web",
                start_x=wrist_x,
                start_y=wrist_y,
                target_x=target_x,
                target_y=target_y,
                owner_getter=lambda: (self.x, self.y),
                on_catch=_on_impact,
                speed=30.0
            )
            particle_mgr.burst_sparks(wrist_x, wrist_y, count=12, color=(0.95, 0.98, 1.0), size=3.0)
            return True

        elif ability_name in ("spider_sense", "sense"):
            self._destroy_swing_rope()
            self.spider_sense_active = True
            self.spider_sense_timer = time.time() + 1.5
            self.eye_squint = -0.5  # Eyes widen in sudden alert
            audio_mgr.play("thwip")
            particle_mgr.burst_sparks(self.x, self.y - 25, count=12, color=(1.0, 0.85, 0.1), size=3.0)
            particle_mgr.shockwave(self.x, self.y - 25, max_radius=50.0, color=(0.2, 0.8, 1.0))
            
            # Evasive agile backflip dodge leap
            self.vy = -11.0
            self.vx = -dir_mult * 7.0
            self.state = CharacterState.JUMP
            return True

        elif ability_name in ("swing_attack", "web_strike", "strike"):
            self._destroy_swing_rope()
            self.facing_right = (target_x >= self.x)
            dir_mult = 1.0 if self.facing_right else -1.0
            wrist_x = self.x + dir_mult * 26.0
            wrist_y = self.y - 6.0
            self.attack_target_x = target_x
            self.attack_target_y = target_y
            self.is_swing_attacking = True
            self.attack_timer = time.time()
            self.is_perched = False
            self.is_seated = False
            self.is_hanging_upside_down = False
            self.is_wall_crawling = False
            self.is_swinging = False
            self.state = CharacterState.FLY
            self.eye_squint = 0.5

            dx = target_x - self.x
            dy = target_y - self.y
            dist = max(10.0, math.hypot(dx, dy))

            # Catapult forward at high velocity towards target with dropkick angle
            strike_speed = 28.0
            self.vx = (dx / dist) * strike_speed
            self.vy = (dy / dist) * strike_speed
            self.tilt = math.atan2(dy, dx) + (-0.15 if self.facing_right else 0.15)

            self._ensure_swing_rope()
            audio_mgr.play("thwip")
            particle_mgr.burst_sparks(wrist_x, wrist_y, count=8, color=(0.95, 0.98, 1.0), size=2.5)
            return True

        elif ability_name in ("web_cocoon", "cocoon"):
            self._destroy_swing_rope()
            self.facing_right = (target_x >= self.x)
            dir_mult = 1.0 if self.facing_right else -1.0
            wrist_x = self.x + dir_mult * 26.0
            wrist_y = self.y - 6.0
            self.web_target_x = target_x
            self.web_target_y = target_y
            self.web_shoot_timer = time.time() + 0.65
            self.eye_squint = 0.7  # Intense web-spinning squint
            audio_mgr.play("thwip")

            def _on_cocoon_impact():
                audio_mgr.play("thwip")
                particle_mgr.burst_sparks(target_x, target_y, count=24, color=(0.95, 0.98, 1.0), size=3.2)
                particle_mgr.shockwave(target_x, target_y, max_radius=85.0, color=(0.92, 0.96, 1.0))

            DesktopProjectileWindow(
                proj_type="web_cocoon",
                start_x=wrist_x,
                start_y=wrist_y,
                target_x=target_x,
                target_y=target_y,
                owner_getter=lambda: (self.x, self.y),
                on_catch=_on_cocoon_impact,
                speed=28.0
            )
            particle_mgr.burst_sparks(wrist_x, wrist_y, count=16, color=(0.95, 0.98, 1.0), size=3.0)
            return True

        elif ability_name in ("perch", "crouch"):
            self._destroy_swing_rope()
            self.is_swinging = False
            self.is_hanging_upside_down = False
            self.is_wall_crawling = False
            self.is_swing_attacking = False
            self.is_seated = False
            self.is_perched = True
            self.state = CharacterState.IDLE
            self.vx = 0.0
            self.vy = 0.0
            self.tilt = 0.0
            self.eye_squint = 0.3
            from core.platforms import platform_manager
            ledge = platform_manager.is_on_ledge(self.x, self.y, tolerance=30.0) or platform_manager.get_nearest_ledge(self.x, self.y, max_dist=50.0)
            if ledge:
                self.current_ledge = ledge
                self.y = ledge.top
            particle_mgr.smoke_puff(self.x, self.y + 20, count=3)
            return True

        elif ability_name in ("seat", "sit"):
            self._destroy_swing_rope()
            self.is_swinging = False
            self.is_hanging_upside_down = False
            self.is_wall_crawling = False
            self.is_swing_attacking = False
            self.state = CharacterState.IDLE
            self.vx = 0.0
            self.vy = 0.0
            self.tilt = 0.0
            self.eye_squint = 0.0

            from core.platforms import platform_manager
            all_ledges = platform_manager.ledges + platform_manager.dynamic_ledges
            real_ledges = [l for l in all_ledges if platform_manager.is_real_surface(l)]
            panel_ledges = [l for l in all_ledges if l.ledge_type == "panel"]
            window_ledges = [l for l in real_ledges if l.ledge_type == "window"]

            # 1. Check if Spidey is already directly on a valid ledge (e.g. test or real window)
            on_ledge = platform_manager.is_on_ledge(self.x, self.y, tolerance=32.0, require_real=False)
            if on_ledge and (on_ledge.ledge_type in ("window", "panel") or platform_manager.is_real_surface(on_ledge)):
                self.current_ledge = on_ledge
                self.is_seated = True
                self.is_perched = False
                self.y = on_ledge.top - 8.0
                particle_mgr.smoke_puff(self.x, self.y + 16, count=2)
                return True

            # 2. Check upper taskbar panel (system panel ledge or top of screen y <= 45.0)
            if abs(self.y - 32.0) < 55.0 or (panel_ledges and abs(self.y - panel_ledges[0].top) < 55.0):
                top_panel = panel_ledges[0] if panel_ledges else None
                top_y = top_panel.top if top_panel else 32.0
                self.current_ledge = top_panel
                self.is_seated = True
                self.is_perched = False
                self.y = top_y - 8.0
                audio_mgr.play("thwip")
                particle_mgr.smoke_puff(self.x, self.y + 16, count=2)
                return True

            # 3. Check if near ground floor level
            if self.y >= 980.0:  # near standard ground
                self.current_ledge = None
                self.is_seated = True
                self.is_perched = False
                self.y = 1010.0 - 8.0
                particle_mgr.smoke_puff(self.x, self.y + 16, count=2)
                return True

            # 4. If there is a real, verified window ledge on screen, web-zip to it
            if window_ledges:
                best_ledge = min(window_ledges, key=lambda l: l.distance_to(self.x, self.y))
                self.current_ledge = best_ledge
                self.x = max(best_ledge.left + 25.0, min(best_ledge.right - 25.0, self.x))
                self.y = best_ledge.top - 8.0
                self.is_seated = True
                self.is_perched = False
                audio_mgr.play("thwip")
                particle_mgr.burst_sparks(self.x, self.y, count=5, color=(0.95, 0.98, 1.0))
                return True

            # 5. Default fallback: Web-zip up to Upper Taskbar Panel (y=24.0)
            # Firmly seated on the upper taskbar overlooking the desktop, never in mid-air
            top_panel = panel_ledges[0] if panel_ledges else None
            top_y = top_panel.top if top_panel else 32.0
            self.current_ledge = top_panel
            self.y = top_y - 8.0
            self.is_seated = True
            self.is_perched = False
            audio_mgr.play("thwip")
            particle_mgr.burst_sparks(self.x, self.y, count=5, color=(0.95, 0.98, 1.0))
            return True

        elif ability_name in ("wall_crawl", "crawl"):
            self._destroy_swing_rope()
            self.is_swinging = False
            self.is_hanging_upside_down = False
            self.is_perched = False
            self.is_seated = False
            self.is_wall_crawling = True
            self.state = CharacterState.IDLE
            particle_mgr.burst_sparks(self.x, self.y, count=4, color=(0.9, 0.95, 1.0), size=2.0)
            return True

        elif ability_name in ("upside_down_hang", "hang"):
            self.is_swinging = False
            self.is_perched = False
            self.is_seated = False
            self.is_wall_crawling = False
            self.is_hanging_upside_down = True
            self.tilt = math.pi
            self.hang_end_time = time.time() + 2.2
            self.anchor_x = self.x
            self.anchor_y = max(20.0, self.y - 160.0)
            self._ensure_swing_rope()
            audio_mgr.play("thwip")
            particle_mgr.burst_sparks(self.x, self.y + 20, count=18, color=(0.95, 0.98, 1.0), size=3.2)
            particle_mgr.shockwave(self.x, self.y + 20, max_radius=70.0, color=(0.95, 0.98, 1.0))
            return True

        return False

    def nav_to(self, target_x: float, target_y: float) -> None:
        """Initiate multi-stage superhero movement (run -> swing -> jump -> land/seat/perch)."""
        self.nav_target = (target_x, target_y)
        self.nav_stage = "RUN"
        self.nav_timer = time.time()
        self.is_perched = False
        self.is_seated = False
        self.is_hanging_upside_down = False
        self.is_wall_crawling = False
        self.tilt = 0.0

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

        # Eye squint recovery towards neutral
        if now > self.spider_sense_timer:
            self.spider_sense_active = False
            self.eye_squint += (0.0 - self.eye_squint) * 0.15

        # Reflex-based Spider-Sense detection on rapid cursor motion
        cursor_moved = math.hypot(cursor_x - self.prev_cursor_x, cursor_y - self.prev_cursor_y)
        cursor_spd = cursor_moved / max(1e-3, dt)
        self.prev_cursor_x = cursor_x
        self.prev_cursor_y = cursor_y

        dist_to_cursor = math.hypot(cursor_x - self.x, cursor_y - self.y)
        if activity > 0.2 and cursor_spd > 1800.0 and 45.0 < dist_to_cursor < 180.0 and not self.spider_sense_active:
            self.trigger_ability("spider_sense", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Autonomous abilities
        if activity > 0.1 and now >= self.action_timer:
            self.action_timer = now + random.uniform(3.5, 7.5) / max(0.2, activity)
            r = random.random()
            if r < 0.25 and not self.is_swinging and not self.is_swing_attacking:
                target_swing_x = cursor_x if abs(cursor_x - self.x) > 80.0 else (self.x + random.choice([-260.0, 260.0]))
                self.trigger_ability("web_swing", target_swing_x, cursor_y, particle_mgr, audio_mgr)
            elif r < 0.40 and not self.is_swinging and not self.is_swing_attacking:
                # Web cocoon barrage!
                self.trigger_ability("web_cocoon", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif r < 0.55 and not self.is_swinging and not self.is_swing_attacking:
                # Dynamic swing attack / web-strike
                self.trigger_ability("swing_attack", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif r < 0.70:
                self.trigger_ability("web_throw", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif r < 0.85 and not self.is_swinging and not self.is_swing_attacking:
                # Web-zip to upper taskbar or window to sit or hang!
                if random.random() < 0.55:
                    self.trigger_ability("seat", cursor_x, cursor_y, particle_mgr, audio_mgr)
                else:
                    self.trigger_ability("upside_down_hang", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif self.y >= ground_y - 10.0:
                self.trigger_ability("perch", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # SWING-ATTACK / WEB-STRIKE KINEMATICS
        if self.is_swing_attacking:
            now = time.time()
            elapsed_atk = now - self.attack_timer
            self._ensure_swing_rope()
            if self.rope_window:
                self.rope_window.update()

            self.state = CharacterState.FLY
            dx = self.attack_target_x - self.x
            dy = self.attack_target_y - self.y
            dist = math.hypot(dx, dy)

            # Check impact with target point or duration timeout
            if dist < 36.0 or elapsed_atk > 0.48:
                # Impact target with comic web strike!
                self.is_swing_attacking = False
                self._destroy_swing_rope()
                self.state = CharacterState.JUMP
                audio_mgr.play("punch")
                particle_mgr.burst_sparks(self.x, self.y, count=16, color=(0.95, 0.98, 1.0), size=3.2)
                particle_mgr.shockwave(self.x, self.y, max_radius=65.0, color=(1.0, 0.9, 0.2))

                # Dynamic backflip recoil leap
                dir_sign = -1.0 if self.facing_right else 1.0
                self.vx = dir_sign * 11.0
                self.vy = -13.0
                self.tilt = dir_sign * 0.45
            else:
                # Catapulting towards target
                self.x += self.vx
                self.y += self.vy
                self.tilt = math.atan2(dy, dx) + (-0.15 if self.facing_right else 0.15)
                if random.random() < 0.4:
                    particle_mgr.burst_sparks(self.x, self.y, count=2, color=(0.95, 0.98, 1.0), size=1.8)
            return

        # UPSIDE-DOWN HANG STATE
        if self.is_hanging_upside_down:
            self._ensure_swing_rope()
            if self.rope_window:
                self.rope_window.update()
            self.state = CharacterState.IDLE
            self.vx = 0.0
            self.vy = 0.0
            self.tilt = math.pi  # Full upside down orientation
            if now >= self.hang_end_time:
                self.is_hanging_upside_down = False
                self._destroy_swing_rope()
                self.vy = 4.0
                self.tilt = 0.0
                self.state = CharacterState.FLY
                audio_mgr.play("swoosh")
                particle_mgr.smoke_puff(self.x, self.y - 10, count=3)
            return

        # PENDULUM WEB-SWINGING DYNAMICS
        if self.is_swinging:
            self._ensure_swing_rope()
            if self.rope_window:
                self.rope_window.update()
            self.state = CharacterState.FLY
            elapsed_swing = now - self.swing_timer

            # Calibrated dynamic pendulum physics with kinetic pump
            gravity = 18.0
            accel = -gravity * math.sin(self.swing_angle)
            self.swing_vel += accel * dt * speed_mult
            self.swing_vel *= 0.995  # Aerodynamic drag damping
            self.swing_angle += self.swing_vel * dt * 2.8

            # Update coordinates along pendulum arc
            self.x = self.anchor_x + self.web_length * math.sin(self.swing_angle)
            raw_y = self.anchor_y + self.web_length * math.cos(self.swing_angle)
            self.y = min(ground_y - 8.0, raw_y)

            # Body orientation tilts dynamically with the swing arc
            target_tilt = self.swing_angle + (0.35 if self.swing_vel > 0 else -0.35)
            self.tilt += (target_tilt - self.tilt) * 0.25
            self.facing_right = (self.swing_vel >= 0.0)

            # Navigation swing transition into acrobatic jump & somersault
            if self.nav_target is not None and self.nav_stage == "SWING":
                tx, ty = self.nav_target
                dx = tx - self.x
                dy = ty - self.y
                dist = math.hypot(dx, dy)
                elapsed = now - self.nav_timer
                if elapsed > 0.65 or dist < 140.0:
                    self.is_swinging = False
                    self._destroy_swing_rope()
                    self.nav_stage = "JUMP"
                    self.nav_timer = now
                    self.state = CharacterState.JUMP
                    self.vx = (dx / max(1.0, dist)) * 16.5 * speed_mult
                    self.vy = min(-9.0, max(-20.0, dy * 0.14))
                    self.tilt = (self.vx / 14.0) * 0.25
                    audio_mgr.play("swoosh")
                    particle_mgr.burst_sparks(self.x, self.y, count=5, color=(0.95, 0.98, 1.0))
                    return

            # Release web at apex or after solid swing duration
            # Spider-Man MUST swing for at least 0.40 seconds before releasing!
            is_apex = (
                elapsed_swing > 0.40 and (
                    (self.swing_direction > 0 and self.swing_angle > 0.22 and self.swing_vel < 0.6) or
                    (self.swing_direction < 0 and self.swing_angle < -0.22 and self.swing_vel > -0.6) or
                    elapsed_swing > 1.35
                )
            )
            is_ground_hit = (
                elapsed_swing > 0.45 and
                self.y >= ground_y - 10.0 and
                self.swing_vel * math.sin(self.swing_angle) > 0.1
            )

            if is_apex or is_ground_hit:
                # Release web line and transition to graceful aerial leap
                self.is_swinging = False
                self._destroy_swing_rope()
                dir_sign = 1.0 if self.facing_right else -1.0
                self.vx = dir_sign * max(14.0, abs(self.swing_vel) * 28.0) * speed_mult
                self.vy = min(-10.0, -abs(self.swing_vel) * 16.0)
                if self.nav_stage == "SWING":
                    self.nav_stage = "JUMP"
                    self.nav_timer = now
                    self.state = CharacterState.JUMP
                else:
                    self.state = CharacterState.JUMP
                self.tilt = (self.vx / 14.0) * 0.25
                audio_mgr.play("swoosh")
                particle_mgr.burst_sparks(self.x, self.y, count=5, color=(0.92, 0.96, 1.0), size=2.4)

            return

        if not (self.is_swinging or self.is_hanging_upside_down or self.is_swing_attacking):
            if self.rope_window is not None:
                self._destroy_swing_rope()

        # WALL-CRAWL STATE
        near_left = (self.x <= min_x + 65.0)
        near_right = (self.x >= min_x + screen_w - 65.0)
        if self.is_wall_crawling and (near_left or near_right):
            self.state = CharacterState.WALK
            self.facing_right = near_left
            self.tilt = math.pi * 0.5 if near_left else -math.pi * 0.5
            self.stride += 0.12 * speed_mult
            target_y = max(min_y + 100.0, min(ground_y, cursor_y))
            self.vy += ((target_y - self.y) * 0.05 - self.vy) * 0.18
            self.y += self.vy
            return
        else:
            if self.is_wall_crawling:
                self.tilt = 0.0
                self.is_wall_crawling = False
                return
            self.is_wall_crawling = False

        # 1. MULTI-STAGE AUTONOMOUS NAVIGATION (Run -> Swing -> Jump -> Land/Seat/Perch)
        if self.nav_target is not None:
            raw_tx, raw_ty = self.nav_target
            # Clamp destination within reachable screen space to prevent corner entrapment
            tx = max(min_x + 50.0, min(min_x + screen_w - 50.0, raw_tx))
            ty = max(min_y + 50.0, min(ground_y, raw_ty))
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            self.facing_right = (dx >= 0.0)

            elapsed = time.time() - self.nav_timer
            # Arrived if close or reached timeout (prevent infinite corner revolving)
            if dist < 28.0 or (abs(dx) < 22.0 and abs(dy) < 22.0) or elapsed > 3.2:
                # Arrived at destination!
                self.nav_target = None
                self.nav_stage = "IDLE"
                self.vx = 0.0
                self.vy = 0.0
                self.tilt = 0.0
                # Check if arrived on a window ledge or button (require genuine real surface)
                from core.platforms import platform_manager
                ledge = platform_manager.is_on_ledge(self.x, self.y, tolerance=24.0, require_real=True) or platform_manager.get_nearest_ledge(self.x, self.y, max_dist=45.0, require_real=True)
                if ledge:
                    self.current_ledge = ledge
                    if ledge.ledge_type == "button":
                        self.is_perched = True
                        self.is_seated = False
                        self.y = ledge.top
                    elif ledge.ledge_type == "panel":
                        self.is_seated = True
                        self.is_perched = False
                        self.y = ledge.top - 8.0
                    else:
                        if random.random() < 0.6:
                            self.is_seated = True
                            self.is_perched = False
                            self.y = ledge.top - 8.0
                        else:
                            self.is_perched = True
                            self.is_seated = False
                            self.y = ledge.top
                    self.state = CharacterState.IDLE
                elif self.y <= 40.0:
                    self.current_ledge = None
                    self.is_seated = True
                    self.is_perched = False
                    self.y = 24.0
                    self.state = CharacterState.IDLE
                else:
                    # Arrived at coordinates without a ledge: Land gracefully on the ground in superhero perch!
                    self.current_ledge = None
                    self.is_perched = True
                    self.is_seated = False
                    self.y = ground_y
                    self.state = CharacterState.IDLE
                particle_mgr.smoke_puff(self.x, self.y + 16, count=2)
                return
            else:
                if dist > 180.0:
                    if self.nav_stage == "RUN":
                        # Stage 1: Sprint towards launch point
                        self.state = CharacterState.RUN
                        self.stride += 0.28 * speed_mult
                        dir_sign = 1.0 if dx > 0 else -1.0
                        self.vx = dir_sign * 13.5 * speed_mult
                        self.x += self.vx
                        self.tilt += (0.0 - self.tilt) * 0.2
                        if elapsed > 0.32:
                            # Stage 2: Fire web and launch high pendulum swing!
                            self.nav_stage = "SWING"
                            self.nav_timer = time.time()
                            self.swing_timer = self.nav_timer
                            self.anchor_x = (self.x + tx) / 2.0
                            self.anchor_y = max(30.0, min(self.y - 150.0, ty - 180.0))
                            curr_dist = math.hypot(self.x - self.anchor_x, self.y - self.anchor_y)
                            max_safe_len = max(140.0, (self.y + 120.0) - self.anchor_y)
                            self.web_length = max(140.0, min(curr_dist, max_safe_len))
                            dx_anc = max(-self.web_length * 0.95, min(self.web_length * 0.95, self.x - self.anchor_x))
                            self.swing_angle = math.asin(dx_anc / self.web_length)
                            self.swing_vel = 1.8 if dx > 0 else -1.8
                            self.is_swinging = True
                            self.state = CharacterState.FLY
                            self._ensure_swing_rope()
                            audio_mgr.play("thwip")
                            particle_mgr.burst_sparks(self.x, self.y - 12, count=6, color=(0.95, 0.98, 1.0))
                    elif self.nav_stage == "SWING":
                        # Transition to Stage 3 (Acrobatic Jump) at apex or when near target
                        if elapsed > 0.65 or dist < 130.0:
                            self.is_swinging = False
                            self._destroy_swing_rope()
                            self.nav_stage = "JUMP"
                            self.nav_timer = time.time()
                            self.state = CharacterState.JUMP
                            self.vx = (dx / dist) * 16.5 * speed_mult
                            self.vy = min(-9.0, max(-20.0, dy * 0.14))
                            self.tilt = (self.vx / 14.0) * 0.22
                            audio_mgr.play("swoosh")
                            particle_mgr.burst_sparks(self.x, self.y, count=5, color=(0.95, 0.98, 1.0))
                    elif self.nav_stage == "JUMP":
                        # Stage 3: Aerodynamic athletic jump (controlled lean, NO endless spinning)
                        self.state = CharacterState.JUMP
                        target_tilt = (self.vx / 14.0) * 0.22
                        self.tilt += (target_tilt - self.tilt) * 0.20
                        self.x += self.vx
                        self.y += self.vy
                        self.vy += 0.72  # Air gravity

                        from core.platforms import platform_manager
                        if self.y >= ground_y - 2.0:
                            self.y = ground_y
                            self.tilt = 0.0
                            self.nav_target = None
                            self.nav_stage = "IDLE"
                            self.state = CharacterState.IDLE
                            return
                        hit_ledge = platform_manager.is_on_ledge(self.x, self.y, tolerance=18.0)
                        if hit_ledge:
                            self.current_ledge = hit_ledge
                            self.tilt = 0.0
                            self.nav_target = None
                            self.nav_stage = "IDLE"
                            self.state = CharacterState.IDLE
                            self.is_perched = True
                            self.y = hit_ledge.top
                            return
                else:
                    # Short-range: sprint and rapid web-zip leap directly to target
                    self.state = CharacterState.RUN
                    self.stride += 0.26 * speed_mult
                    follow_spd = min(15.0, max(4.5, dist * 0.14))
                    self.vx = (dx / dist) * follow_spd
                    self.vy = (dy / dist) * follow_spd
                    self.tilt += (0.0 - self.tilt) * 0.25
                    self.x += self.vx
                    self.y += self.vy

        # 2. WINDOW LEDGE & BUTTON INTERACTION
        from core.platforms import platform_manager
        current_ledge = platform_manager.is_on_ledge(self.x, self.y, tolerance=14.0, require_real=True)
        if current_ledge and self.nav_target is None and not self.is_swinging and not self.is_hanging_upside_down and not self.is_swing_attacking:
            self.current_ledge = current_ledge
            self.vy = 0.0

            if abs(self.vx) < 1.0:
                # Sitting or perching on window frame / buttons / top panel
                if not self.is_perched and not self.is_seated:
                    if current_ledge.ledge_type == "button":
                        self.is_perched = True
                        self.is_seated = False
                    elif current_ledge.ledge_type == "panel":
                        self.is_seated = True
                        self.is_perched = False
                    else:
                        if random.random() < 0.6:
                            self.is_seated = True
                            self.is_perched = False
                        else:
                            self.is_perched = True
                            self.is_seated = False
                if self.is_seated:
                    self.y = current_ledge.top - 8.0
                    self.tilt = 0.0
                elif self.is_perched:
                    self.y = current_ledge.top
                    self.tilt = 0.0
            else:
                # Running horizontally along the window ledge or button surface
                self.is_perched = False
                self.is_seated = False
                self.y = current_ledge.top
        else:
            if not platform_manager.is_real_surface(self.current_ledge):
                self.current_ledge = None

        # Strict Anti-Mid-Air Seating Invariant:
        # Spider-Man CANNOT be seated in mid-air (between upper taskbar and ground without a verified real surface)
        if self.is_seated and not self.is_swinging and not self.is_hanging_upside_down and not self.is_wall_crawling:
            on_top_panel = (self.y <= 42.0 or (self.current_ledge and self.current_ledge.ledge_type == "panel"))
            on_ground = (self.y >= ground_y - 14.0)
            on_real_window = (self.current_ledge is not None and platform_manager.is_real_surface(self.current_ledge))
            if not (on_top_panel or on_ground or on_real_window):
                self.is_seated = False
                self.current_ledge = None
                self.state = CharacterState.JUMP
                self.vy = 1.5

        # 3. GROUND & AIR NAVIGATION (Standard Autonomous Wander)
        if self.nav_target is None and not self.is_swinging and not self.is_hanging_upside_down and not self.is_swing_attacking:
            dx = cursor_x - self.x
            dy = cursor_y - self.y
            dist = math.hypot(dx, dy)
            dist_x = abs(dx)

            if dist_x > 6.0:
                self.facing_right = (cursor_x >= self.x)

            if self.current_ledge:
                # On window ledge or button platform
                self.vy = 0.0
                if self.is_seated:
                    self.y = self.current_ledge.top - 8.0
                    self.tilt = 0.0
                    self.state = CharacterState.IDLE
                    self.vx *= 0.75
                elif self.is_perched:
                    self.y = self.current_ledge.top
                    self.tilt = 0.0
                    self.state = CharacterState.IDLE
                    self.vx *= 0.75
                elif dist_x > 25.0:
                    # Run along window frame
                    self.y = self.current_ledge.top
                    self.state = CharacterState.RUN
                    self.stride += 0.22 * speed_mult
                    target_vx = (1.0 if dx > 0 else -1.0) * min(10.0, dist_x * 0.08) * speed_mult
                    self.vx += (target_vx - self.vx) * 0.22
                    self.x += self.vx
                    # Don't walk off ledge without intention
                    self.x = max(self.current_ledge.left + 15.0, min(self.current_ledge.right - 15.0, self.x))
                else:
                    self.y = self.current_ledge.top
                    self.state = CharacterState.IDLE
                    self.tilt = 0.0
                    self.vx *= 0.80
            elif self.y >= ground_y - 3.0 and abs(self.vy) < 2.0:
                # On ground: Spider-Man crouches in his iconic three-point perch (NEVER sits dangling legs on floor)
                self.vy = 0.0
                self.is_seated = False
                if self.is_perched or abs(self.vx) < 0.5:
                    self.is_perched = True
                    self.y = ground_y
                    self.tilt = 0.0
                    self.state = CharacterState.IDLE
                    self.vx *= 0.75
                elif dist_x > 25.0:
                    # Acrobatic low-profile running sprint
                    self.y = ground_y
                    self.state = CharacterState.RUN
                    self.stride += 0.22 * speed_mult
                    target_vx = (1.0 if dx > 0 else -1.0) * min(11.0, dist_x * 0.09) * speed_mult
                    self.vx += (target_vx - self.vx) * 0.22
                    self.x += self.vx
                    self.tilt += (0.0 - self.tilt) * 0.2
                    if random.random() < 0.2:
                        particle_mgr.smoke_puff(self.x, ground_y + 18, count=1)
                else:
                    self.y = ground_y
                    self.tilt = 0.0
                    self.state = CharacterState.IDLE
                    self.vx *= 0.80
                    self.x += self.vx
            else:
                # Airborne acrobatic jump / leap kinematics
                # MUST CLEAR is_seated and is_perched while airborne!
                self.is_seated = False
                self.is_perched = False
                self.state = CharacterState.JUMP if abs(self.vy) > 1.5 else (CharacterState.FLY if abs(self.vx) > 3.0 else CharacterState.HOVER)
                self.vy += 0.72  # Air gravity
                self.vx *= 0.97
                self.x += self.vx
                self.y += self.vy
                target_tilt = (self.vx / 14.0) * 0.28 + (-0.10 if self.vy < 0 else 0.16)
                self.tilt += (target_tilt - self.tilt) * 0.20

                # Ledge collision check while airborne (require genuine physical surface)
                hit_ledge = platform_manager.is_on_ledge(self.x, self.y, tolerance=18.0, require_real=True)
                if hit_ledge and self.vy > 0 and self.y < ground_y - 30.0:
                    self.current_ledge = hit_ledge
                    self.vy = 0.0
                    self.vx = 0.0
                    self.tilt = 0.0
                    self.state = CharacterState.IDLE
                    if hit_ledge.ledge_type == "panel":
                        self.is_seated = True
                        self.is_perched = False
                        self.y = hit_ledge.top - 8.0
                    elif hit_ledge.ledge_type == "window" and random.random() < 0.65:
                        self.is_seated = True
                        self.is_perched = False
                        self.y = hit_ledge.top - 8.0
                    else:
                        self.is_perched = True
                        self.is_seated = False
                        self.y = hit_ledge.top
                    particle_mgr.smoke_puff(self.x, self.y + 16, count=2)
                    return

                if self.y >= ground_y:
                    self.y = ground_y
                    self.vy = 0.0
                    self.vx *= 0.6
                    self.tilt = 0.0
                    self.state = CharacterState.IDLE
                    self.is_perched = True
                    self.is_seated = False
                    particle_mgr.smoke_puff(self.x, ground_y + 18, count=3)

        # Screen boundaries clamping
        self.x = max(min_x + 45.0, min(min_x + screen_w - 45.0, self.x))
        self.y = max(min_y + 45.0, min(ground_y, self.y))

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        """Procedurally renders Spider-Man in classic red/blue webbed suit, expressive 3/4 lenses,
        genuine Ditko two-finger web-shooter trigger, dynamic web lines, and athletic runner sprint.
        """
        ctx.save()
        now = time.time()
        is_firing_web = (now < self.web_shoot_timer)

        # -------------------------------------------------------------
        # LOCAL WEB ATTACHMENT CUES (Full screen rope handled by WebRopeWindow)
        # -------------------------------------------------------------
        if self.is_swinging:
            # Local silk grip knot at Spidey's hand
            dir_mult = 1.0 if self.facing_right else -1.0
            hx = self.x + dir_mult * 6.0
            hy = self.y - 16.0
            ctx.save()
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            ctx.arc(hx, hy, 3.2, 0, 2 * math.pi)
            ctx.fill()
            ctx.set_source_rgba(0.9, 0.96, 1.0, 0.75)
            ctx.arc(hx, hy, 5.0, 0, 2 * math.pi)
            ctx.stroke()
            ctx.restore()

        elif self.is_hanging_upside_down:
            # Web line grip at Spidey's boots
            hy = self.y + 15.0
            ctx.save()
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            ctx.arc(self.x, hy, 3.2, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

        elif is_firing_web and hasattr(self, 'web_target_x'):
            # Wrist web-shooter muzzle flash and local silk ejection spark
            dir_mult = 1.0 if self.facing_right else -1.0
            wx = self.x + dir_mult * 28.0
            wy = self.y - 8.0
            ctx.save()
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.98)
            ctx.arc(wx, wy, 3.0, 0, 2 * math.pi)
            ctx.fill()
            ctx.set_source_rgba(0.90, 0.96, 1.0, 0.65)
            ctx.arc(wx, wy, 5.5, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

        # -------------------------------------------------------------
        # CHARACTER LOCAL TRANSFORMATION
        # -------------------------------------------------------------
        ctx.translate(self.x, self.y)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        is_running = (self.state == CharacterState.RUN)
        if self.is_hanging_upside_down:
            ctx.rotate(math.pi)
        elif self.is_perched:
            ctx.rotate(0.30)  # Athletic forward 3-point crouch lean
            ctx.translate(0, 8)  # Lower center of mass toward ledge/ground
        elif getattr(self, "is_swing_attacking", False):
            ctx.rotate(0.32)  # Aerodynamic forward dropkick dive angle
        elif self.is_seated or self.state == CharacterState.IDLE:
            pass
        elif is_running:
            run_cycle = self.stride * 4.5
            bob = -abs(math.sin(run_cycle)) * 2.8
            ctx.translate(0, bob)
            ctx.rotate(0.24)  # ~14° forward athletic lean into the sprint
        else:
            # Airborne (JUMP / FLY) tilt
            dir_mult = 1.0 if self.facing_right else -1.0
            ctx.rotate(self.tilt * dir_mult)

        ctx.scale(self.scale, self.scale)

        # Spider-Man Classic Palette
        SPIDER_RED = (0.86, 0.12, 0.12)
        SPIDER_RED_DARK = (0.62, 0.08, 0.08)
        SPIDER_BLUE = (0.08, 0.18, 0.46)
        SPIDER_BLUE_DARK = (0.04, 0.10, 0.28)
        SPIDER_BLACK = (0.08, 0.08, 0.10)
        EYE_WHITE = (0.98, 0.99, 1.0)

        # -------------------------------------------------------------
        # 1. SPIDER-SENSE TINGLE ARCS (Concentric comic alert arcs)
        # -------------------------------------------------------------
        if self.spider_sense_active or time.time() < self.spider_sense_timer:
            pulse = math.sin(self.anim_time * 25.0) * 2.0
            ctx.save()
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_source_rgba(1.0, 0.88, 0.12, 0.9)
            ctx.set_line_width(2.2)
            for r_dist in [26.0 + pulse, 34.0 + pulse]:
                for ang_start, ang_end in [(-2.3, -1.8), (-1.6, -1.1), (-0.9, -0.4)]:
                    ctx.new_path()
                    ctx.arc(0, -22, r_dist, ang_start, ang_end)
                    ctx.stroke()
            ctx.set_source_rgba(0.2, 0.85, 1.0, 0.85)
            ctx.set_line_width(1.6)
            for ang_start, ang_end in [(-2.4, -1.7), (-1.5, -0.9), (-0.8, -0.3)]:
                ctx.new_path()
                ctx.arc(0, -22, 42.0 + pulse, ang_start, ang_end)
                ctx.stroke()
            ctx.restore()

        # -------------------------------------------------------------
        # 2. LEGS & RED BOOTS (3/4 Dynamic Athletic Runner Cycle)
        # -------------------------------------------------------------
        ctx.save()
        if self.is_hanging_upside_down:
            # Hanging upside down from ceiling web strand
            # Far leg extended straight up to hook web line
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(7.5)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-3, 4)
            ctx.line_to(-4, 16)
            ctx.line_to(-3, 27)
            ctx.stroke()
            # Far boot wrapped around web strand
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.set_line_width(6.8)
            ctx.move_to(-4, 20)
            ctx.line_to(-3, 27)
            ctx.line_to(1, 28)
            ctx.stroke()

            # Near leg casually crossed over knee
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(8.0)
            ctx.move_to(3, 4)
            ctx.line_to(14, 12)
            ctx.line_to(1, 16)
            ctx.stroke()
            # Near boot
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.set_line_width(7.0)
            ctx.move_to(8, 14)
            ctx.line_to(0, 16)
            ctx.line_to(-3, 15)
            ctx.stroke()

        elif self.is_seated:
            # Authentic Spider-Man Window Sill / Taskbar Seating Posture:
            # One knee raised high with boot planted on the ledge, other leg dangling and swinging over edge
            swing = math.sin(self.anim_time * 2.2) * 3.5

            # Far Leg: High raised knee pulled near chest, boot planted on ledge
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(7.5)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-3, 6)
            ctx.line_to(-2, -6)
            ctx.line_to(4, 7)
            ctx.stroke()
            # Far Boot planted on ledge
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.set_line_width(6.5)
            ctx.move_to(2, 2)
            ctx.line_to(4, 7)
            ctx.line_to(9, 7)
            ctx.stroke()

            # Near Leg: Thigh forward over sill edge, calf dangling and swinging freely
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(8.0)
            ctx.move_to(3, 6)
            ctx.line_to(11, 7)
            ctx.line_to(12 + swing, 23)
            ctx.stroke()
            # Near Boot dangling in breeze
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.set_line_width(7.0)
            ctx.move_to(11.5 + swing * 0.7, 16)
            ctx.line_to(12.5 + swing, 24)
            ctx.line_to(16.5 + swing, 24)
            ctx.stroke()

        elif getattr(self, "is_swing_attacking", False):
            # Iconic Spider-Man flying dual-footed dropkick / web strike impact kick
            # Far leg thrust forward
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(7.8)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-3, 2)
            ctx.line_to(12, -1)
            ctx.line_to(28, -3)
            ctx.stroke()
            # Far boot with striking sole
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.set_line_width(6.8)
            ctx.move_to(20, -2)
            ctx.line_to(28, -3)
            ctx.line_to(31, -1)
            ctx.stroke()

            # Near leg thrust forward alongside far leg
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(8.2)
            ctx.move_to(4, 3)
            ctx.line_to(16, 2)
            ctx.line_to(30, 4)
            ctx.stroke()
            # Near boot with striking sole
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.set_line_width(7.2)
            ctx.move_to(22, 3)
            ctx.line_to(30, 4)
            ctx.line_to(33, 6)
            ctx.stroke()

        elif self.is_perched:
            # Iconic superhero three-point crouch legs
            # Deeply flexed thighs, wide stable base, boots firmly planted
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(8.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-4, 4)
            ctx.line_to(-18, 10)
            ctx.line_to(-14, 26)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.set_line_width(7.0)
            ctx.move_to(-16, 18)
            ctx.line_to(-14, 26)
            ctx.line_to(-8, 26)
            ctx.stroke()

            # Near leg crouched under chest with forward knee
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(8.5)
            ctx.move_to(4, 4)
            ctx.line_to(16, 12)
            ctx.line_to(10, 26)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.set_line_width(7.5)
            ctx.move_to(14, 18)
            ctx.line_to(10, 26)
            ctx.line_to(16, 26)
            ctx.stroke()

        elif self.is_swinging:
            # Dynamic airborne tucked legs trailing in wind, reacting to swing speed
            vel_push = max(-8.0, min(8.0, self.swing_vel * 2.4))
            
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(7.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-5, 4)
            ctx.line_to(-16 + vel_push * 0.5, 12)
            ctx.line_to(-10 + vel_push, 24)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.set_line_width(6.2)
            ctx.move_to(-13 + vel_push * 0.7, 18)
            ctx.line_to(-8 + vel_push, 26)
            ctx.stroke()

            # Near leg kicking forward with g-force
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(7.8)
            ctx.move_to(3, 4)
            ctx.line_to(14 + vel_push * 0.8, 14)
            ctx.line_to(10 + vel_push * 1.2, 26)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.set_line_width(7.0)
            ctx.move_to(12 + vel_push, 20)
            ctx.line_to(10 + vel_push * 1.2, 28)
            ctx.stroke()

        elif self.state in (CharacterState.JUMP, CharacterState.FLY):
            # ICONIC MCFARLANE ACROBATIC AERIAL LEAP / FLIP SPLIT
            is_ascending = (self.vy < 0.0)
            
            # Far leg (trailing aerodynamically behind in depth)
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(7.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            far_hip = (-4.0, 3.0)
            if is_ascending:
                # Trailing straight back with sleek pointed toe
                far_knee = (-16.0, 10.0)
                far_foot = (-26.0, 14.0)
            else:
                # Tucked up ready to absorb landing shock
                far_knee = (-14.0, 6.0)
                far_foot = (-10.0, 20.0)
            ctx.move_to(far_hip[0], far_hip[1])
            ctx.line_to(far_knee[0], far_knee[1])
            ctx.line_to(far_foot[0], far_foot[1])
            ctx.stroke()
            # Far red boot
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.set_line_width(6.2)
            ctx.move_to(far_knee[0] + (far_foot[0] - far_knee[0]) * 0.4, far_knee[1] + (far_foot[1] - far_knee[1]) * 0.4)
            ctx.line_to(far_foot[0], far_foot[1])
            ctx.line_to(far_foot[0] - 3.0, far_foot[1] + 1.0)
            ctx.stroke()

            # Near leg (high athletic forward knee drive)
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(7.8)
            near_hip = (4.0, 3.0)
            if is_ascending:
                # Explosive high knee tucked toward chest
                near_knee = (15.0, 6.0)
                near_foot = (12.0, 20.0)
            else:
                # Reaching forward to touch down on ledge/ground
                near_knee = (14.0, 14.0)
                near_foot = (8.0, 26.0)
            ctx.move_to(near_hip[0], near_hip[1])
            ctx.line_to(near_knee[0], near_knee[1])
            ctx.line_to(near_foot[0], near_foot[1])
            ctx.stroke()
            # Near red boot with flexed sole
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.set_line_width(7.0)
            ctx.move_to(near_knee[0] + (near_foot[0] - near_knee[0]) * 0.4, near_knee[1] + (near_foot[1] - near_knee[1]) * 0.4)
            ctx.line_to(near_foot[0], near_foot[1])
            ctx.line_to(near_foot[0] + 3.5, near_foot[1] + 2.0)
            ctx.stroke()

        elif is_firing_web:
            # DYNAMIC BRACED SHOOTING STANCE (Low superhero recoil brace)
            # Far back leg braced for recoil
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(7.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-4, 4)
            ctx.line_to(-12, 16)
            ctx.line_to(-16, 28)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.set_line_width(6.5)
            ctx.move_to(-12, 18)
            ctx.line_to(-16, 28)
            ctx.line_to(-19, 28)
            ctx.stroke()

            # Near front leg bent forward, planted firmly
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(7.8)
            ctx.move_to(4, 4)
            ctx.line_to(9, 14)
            ctx.line_to(7, 28)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.set_line_width(7.0)
            ctx.move_to(8, 20)
            ctx.line_to(7, 28)
            ctx.line_to(11, 28)
            ctx.stroke()

        elif is_running:
            # NATURAL ATHLETIC 3/4 RUNNER STRIDE
            run_cycle = self.stride * 4.5
            sin_f = math.sin(run_cycle)
            cos_f = math.cos(run_cycle)

            # FAR LEG (Darker for depth, trailing in counter-cadence)
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(7.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            far_hip_x, far_hip_y = -4.0, 4.0
            far_knee_x = far_hip_x - sin_f * 10.0 - 2.0
            far_knee_y = far_hip_y + 10.0 + max(0.0, sin_f * 4.0)
            far_foot_x = far_knee_x - sin_f * 8.0 - 2.0
            far_foot_y = far_knee_y + 11.0 - max(0.0, -sin_f * 5.0)

            ctx.move_to(far_hip_x, far_hip_y)
            ctx.line_to(far_knee_x, far_knee_y)
            ctx.line_to(far_foot_x, far_foot_y)
            ctx.stroke()
            # Far red boot
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.set_line_width(6.2)
            ctx.move_to(far_knee_x + (far_foot_x - far_knee_x) * 0.4, far_knee_y + (far_foot_y - far_knee_y) * 0.4)
            ctx.line_to(far_foot_x, far_foot_y)
            ctx.line_to(far_foot_x + (2.5 if sin_f > 0 else -1.0), far_foot_y + 2.0)
            ctx.stroke()

            # NEAR LEG (Leading high knee drive or trailing push)
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(7.5)
            near_hip_x, near_hip_y = 4.0, 4.0
            near_knee_x = near_hip_x + sin_f * 12.0 + 2.0
            near_knee_y = near_hip_y + 9.0 - max(0.0, sin_f * 6.0)
            near_foot_x = near_knee_x + sin_f * 9.0 + (3.0 if sin_f > 0 else -2.0)
            near_foot_y = near_knee_y + 11.0 + max(0.0, -sin_f * 4.0)

            ctx.move_to(near_hip_x, near_hip_y)
            ctx.line_to(near_knee_x, near_knee_y)
            ctx.line_to(near_foot_x, near_foot_y)
            ctx.stroke()
            # Near red boot with flexed sole
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.set_line_width(6.8)
            ctx.move_to(near_knee_x + (near_foot_x - near_knee_x) * 0.4, near_knee_y + (near_foot_y - near_knee_y) * 0.4)
            ctx.line_to(near_foot_x, near_foot_y)
            ctx.line_to(near_foot_x + 3.5, near_foot_y + 1.5)
            ctx.stroke()

        else:
            # 3/4 Standing / Idle Stance (weight shifted, agile posture)
            breath = math.sin(self.anim_time * 3.0) * 0.6
            # Back Leg
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(7.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-5, 4)
            ctx.line_to(-8, 16)
            ctx.line_to(-10, 28)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.move_to(-9, 21)
            ctx.line_to(-11, 28)
            ctx.stroke()

            # Front Leg
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(7.5)
            ctx.move_to(3, 4)
            ctx.line_to(5, 16 + breath)
            ctx.line_to(6, 28)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.move_to(5.5, 21 + breath * 0.5)
            ctx.line_to(7, 28)
            ctx.stroke()
        ctx.restore()

        # -------------------------------------------------------------
        # 3. MUSCULAR 3/4 TORSO (Red chest vest, blue flank, black webbing)
        # -------------------------------------------------------------
        ctx.save()
        # Navy blue muscular flank base in 3/4 perspective
        ctx.set_source_rgb(*SPIDER_BLUE)
        ctx.new_path()
        ctx.move_to(-11, -12)
        ctx.curve_to(-13, -2, -11, 6, -7, 10)
        ctx.line_to(9, 10)
        ctx.curve_to(13, 5, 14, -2, 11, -12)
        ctx.close_path()
        ctx.fill()

        # Center Crimson Vest & Abdomen (angled in 3/4 leading toward +X)
        pat_chest = cairo.LinearGradient(2, -12, 2, 10)
        pat_chest.add_color_stop_rgb(0.0, *SPIDER_RED)
        pat_chest.add_color_stop_rgb(1.0, *SPIDER_RED_DARK)
        ctx.set_source(pat_chest)
        ctx.new_path()
        ctx.move_to(-6, -12)
        ctx.curve_to(-7, -4, -5, 4, -3, 10)
        ctx.line_to(6, 10)
        ctx.curve_to(9, 4, 11, -4, 9, -12)
        ctx.close_path()
        ctx.fill()

        # Black Webbing on Chest (Arced in 3/4 perspective)
        ctx.set_source_rgba(*SPIDER_BLACK, 0.75)
        ctx.set_line_width(0.85)
        # Vertical web lines converging down
        for wx in [-4, -1, 3, 7]:
            ctx.move_to(wx, -12)
            ctx.line_to(wx * 0.7 + 1.0, 10)
            ctx.stroke()
        # Arched cross-web lines
        for wy in [-8, -4, 0, 4, 8]:
            ctx.new_path()
            ctx.move_to(-5, wy)
            ctx.curve_to(0, wy + 1.5, 4, wy + 1.5, 8, wy)
            ctx.stroke()

        # Black Chest Spider Emblem in 3/4 view
        ctx.set_source_rgb(*SPIDER_BLACK)
        ctx.new_path()
        ctx.arc(1.5, -3, 2.0, 0, 2 * math.pi)
        ctx.arc(1.5, -6, 1.4, 0, 2 * math.pi)
        ctx.fill()
        # Spider legs (curved in 3/4 perspective)
        ctx.set_line_width(0.95)
        for side, mult in [(-1, 0.8), (1, 1.2)]:
            ctx.move_to(1.5 + side * 1.2, -5)
            ctx.line_to(1.5 + side * 4.5 * mult, -9)
            ctx.line_to(1.5 + side * 4.0 * mult, -12)
            ctx.stroke()
            ctx.move_to(1.5 + side * 1.2, -4)
            ctx.line_to(1.5 + side * 6.0 * mult, -6)
            ctx.line_to(1.5 + side * 7.0 * mult, -8)
            ctx.stroke()
            ctx.move_to(1.5 + side * 1.2, -3)
            ctx.line_to(1.5 + side * 5.0 * mult, 0)
            ctx.line_to(1.5 + side * 6.0 * mult, 3)
            ctx.stroke()
            ctx.move_to(1.5 + side * 1.2, -2)
            ctx.line_to(1.5 + side * 4.0 * mult, 2)
            ctx.line_to(1.5 + side * 3.5 * mult, 6)
            ctx.stroke()

        # Red Belt with center chevron angled in 3/4
        ctx.set_source_rgb(*SPIDER_RED)
        ctx.new_path()
        ctx.move_to(-7, 9)
        ctx.line_to(1.5, 12)
        ctx.line_to(9, 9)
        ctx.line_to(9, 11)
        ctx.line_to(1.5, 14)
        ctx.line_to(-7, 11)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 4. ARMS & GENUINE DITKO WEB-SHOOTER TRIGGER GESTURE
        # -------------------------------------------------------------
        ctx.save()
        if self.is_hanging_upside_down:
            # Casual nonchalant Spidey hanging upside down: arms folded across chest
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            # Far arm folded
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(6.2)
            ctx.move_to(-6, -7)
            ctx.line_to(-12, -1)
            ctx.line_to(4, -1)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.arc(4, -1, 3.2, 0, 2 * math.pi)
            ctx.fill()

            # Near arm folded over
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(6.8)
            ctx.move_to(6, -7)
            ctx.line_to(12, 1)
            ctx.line_to(-4, 1)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.arc(-4, 1, 3.4, 0, 2 * math.pi)
            ctx.fill()

        elif self.is_swinging:
            # Lead arm holds web line upwards toward anchor
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(6.8)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(8, -8)
            ctx.line_to(14, -18)
            ctx.line_to(18, -27)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.set_line_width(6.2)
            ctx.move_to(14, -18)
            ctx.line_to(18, -27)
            ctx.stroke()
            # Glove clutching web line tightly
            ctx.arc(18, -27, 3.6, 0, 2 * math.pi)
            ctx.fill()

            # Trailing arm outstretched for aerodynamic counter-balance
            vel_push = max(-6.0, min(6.0, self.swing_vel * 2.0))
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(6.2)
            ctx.move_to(-8, -8)
            ctx.line_to(-18 - vel_push * 0.5, -2)
            ctx.line_to(-25 - vel_push, 6)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.arc(-25 - vel_push, 6, 3.2, 0, 2 * math.pi)
            ctx.fill()

        elif self.is_seated:
            # Authentic Spider-Man Ledge Arm Posture:
            # Far arm planted back on sill behind hip for support
            # Near arm resting elbow on raised knee, glove propping masked chin
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            # Far arm supporting behind hip
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(6.5)
            ctx.move_to(-7, -4)
            ctx.line_to(-14, 2)
            ctx.line_to(-12, 8)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.move_to(-13, 4)
            ctx.line_to(-12, 8)
            ctx.stroke()
            ctx.arc(-12, 8, 3.2, 0, 2 * math.pi)
            ctx.fill()

            # Near arm: resting elbow on raised knee (-2, -6), glove supporting chin
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(7.0)
            ctx.move_to(6, -4)
            ctx.line_to(0, -6)
            ctx.line_to(2, -15)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.set_line_width(6.2)
            ctx.move_to(0, -6)
            ctx.line_to(2, -15)
            ctx.stroke()
            # Glove propped under chin
            ctx.arc(2, -15, 3.4, 0, 2 * math.pi)
            ctx.fill()

        elif getattr(self, "is_swing_attacking", False):
            # High-speed web strike dive arms:
            # Near arm extended forward in Ditko web-shooter trigger gesture
            # Far arm swept back for supersonic balance
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            # Far arm swept back
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(6.2)
            ctx.move_to(-6, -6)
            ctx.line_to(-15, -2)
            ctx.line_to(-24, 4)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.arc(-24, 4, 3.2, 0, 2 * math.pi)
            ctx.fill()

            # Near arm extended forward in Ditko web-shooter trigger gesture
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(7.2)
            ctx.move_to(7, -5)
            ctx.line_to(18, -4)
            ctx.line_to(28, -3)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.set_line_width(6.5)
            ctx.move_to(20, -4)
            ctx.line_to(28, -3)
            ctx.stroke()
            # Gloved wrist & Ditko trigger fingers
            ctx.arc(28, -3, 3.4, 0, 2 * math.pi)
            ctx.fill()
            # Dual middle/ring fingers pressed to palm, index/pinky outstretched
            ctx.set_source_rgb(*SPIDER_BLACK)
            ctx.set_line_width(1.4)
            ctx.move_to(28, -3)
            ctx.line_to(32, -4)
            ctx.stroke()
            ctx.move_to(28, -3)
            ctx.line_to(32, -2)
            ctx.stroke()

            # Dual silk speed trails streaming from shooter into target
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.9)
            ctx.set_line_width(1.5)
            ctx.move_to(31, -4)
            ctx.line_to(45, -5)
            ctx.stroke()
            ctx.move_to(31, -2)
            ctx.line_to(45, -1)
            ctx.stroke()

        elif self.is_perched:
            # Planted hands on desktop surface (THE ICONIC THIRD POINT OF CONTACT)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            # Far arm poised bent over high rear knee
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(6.2)
            ctx.move_to(-8, -5)
            ctx.line_to(-16, 2)
            ctx.line_to(-11, 14)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.move_to(-14, 8)
            ctx.line_to(-11, 14)
            ctx.stroke()
            ctx.arc(-11, 14, 3.0, 0, 2 * math.pi)
            ctx.fill()

            # Near arm: Planted firmly on the ground surface, fingers spread
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(7.0)
            ctx.move_to(8, -5)
            ctx.line_to(15, 8)
            ctx.line_to(10, 26)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.set_line_width(6.2)
            ctx.move_to(14, 16)
            ctx.line_to(10, 26)
            ctx.stroke()
            # Glove palm planted
            ctx.arc(10, 26, 3.4, 0, 2 * math.pi)
            ctx.fill()
            # Splayed finger setae gripping surface
            ctx.set_line_width(1.6)
            ctx.move_to(10, 26)
            ctx.line_to(14, 27)
            ctx.stroke()
            ctx.move_to(10, 26)
            ctx.line_to(11, 28)
            ctx.stroke()
            ctx.move_to(10, 26)
            ctx.line_to(7, 27)
            ctx.stroke()

        elif self.state in (CharacterState.JUMP, CharacterState.FLY):
            # Acrobatic aerial balance arms
            is_ascending = (self.vy < 0.0)
            
            # Far arm (trailing back high in the wind)
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(6.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            far_sh = (-7.0, -7.0)
            far_el = (-16.0, -12.0 if is_ascending else -4.0)
            far_hd = (-24.0, -16.0 if is_ascending else 4.0)
            ctx.move_to(far_sh[0], far_sh[1])
            ctx.line_to(far_el[0], far_el[1])
            ctx.line_to(far_hd[0], far_hd[1])
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.arc(far_hd[0], far_hd[1], 3.2, 0, 2 * math.pi)
            ctx.fill()

            # Near arm (reaching forward / downward in heroic trajectory)
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(6.8)
            near_sh = (7.0, -7.0)
            near_el = (16.0, -4.0 if is_ascending else 4.0)
            near_hd = (24.0, -2.0 if is_ascending else 12.0)
            ctx.move_to(near_sh[0], near_sh[1])
            ctx.line_to(near_el[0], near_el[1])
            ctx.line_to(near_hd[0], near_hd[1])
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.arc(near_hd[0], near_hd[1], 3.5, 0, 2 * math.pi)
            ctx.fill()

        elif is_firing_web:
            # =========================================================
            # AUTHENTIC DITKO / ROMITA WEB SHOOTER POSE
            # =========================================================
            # Trailing arm poised back for athletic balance
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(6.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-8, -8)
            ctx.line_to(-18, 0)
            ctx.line_to(-22, 6)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.move_to(-18, 0)
            ctx.line_to(-22, 6)
            ctx.stroke()

            # Leading arm outstretched straight toward aim line
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(6.5)
            ctx.move_to(8, -8)
            ctx.line_to(20, -8)
            ctx.stroke()
            # Red Glove Forearm
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.move_to(18, -8)
            ctx.line_to(27, -8)
            ctx.stroke()

            # Metallic Silver Web-Shooter Wrist Cuff
            ctx.set_source_rgb(0.90, 0.92, 0.96)
            ctx.set_line_width(3.2)
            ctx.move_to(25, -10.5)
            ctx.line_to(25, -5.5)
            ctx.stroke()
            # Micro steel nozzle stud on palm side
            ctx.set_source_rgb(0.70, 0.72, 0.78)
            ctx.arc(26.5, -8.0, 1.3, 0, 2 * math.pi)
            ctx.fill()

            # THE ICONIC TWO-FINGER TRIGGER HAND:
            # Palm turned forward, middle and ring fingers curled down onto palm trigger stud!
            # Index and Pinky extended straight forward, Thumb cocked outward!
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            # Palm base
            ctx.arc(28.0, -8.0, 3.2, 0, 2 * math.pi)
            ctx.fill()

            # Index finger (extended straight along fire vector)
            ctx.set_line_width(1.8)
            ctx.move_to(29.5, -9.5)
            ctx.line_to(36.0, -9.8)
            ctx.stroke()

            # Pinky finger (extended straight)
            ctx.move_to(29.5, -6.5)
            ctx.line_to(35.5, -6.0)
            ctx.stroke()

            # Middle & Ring fingers (folded down tightly pressing palm trigger)
            ctx.set_line_width(2.2)
            ctx.move_to(29.0, -8.0)
            ctx.curve_to(31.5, -7.0, 31.0, -9.0, 28.5, -8.0)
            ctx.stroke()

            # Thumb cocked upward
            ctx.set_line_width(1.8)
            ctx.move_to(27.5, -10.0)
            ctx.line_to(29.0, -13.0)
            ctx.stroke()

            # THWIP! Muzzle Flash & Web Ejection Spark
            flash_rad = 3.5 + math.sin(self.anim_time * 30.0) * 1.2
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            ctx.arc(28.0, -8.0, flash_rad, 0, 2 * math.pi)
            ctx.fill()
            # Directional ejection starburst
            ctx.set_line_width(1.2)
            ctx.move_to(28.0, -8.0 - flash_rad * 1.5)
            ctx.line_to(28.0, -8.0 + flash_rad * 1.5)
            ctx.move_to(28.0 - flash_rad * 1.5, -8.0)
            ctx.line_to(28.0 + flash_rad * 2.2, -8.0)
            ctx.stroke()

        elif is_running:
            # ATHLETIC RUNNER ARM PUMP
            run_cycle = self.stride * 4.5
            arm_sin = math.sin(run_cycle)

            # FAR ARM (Pumping backward in counter-stride)
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(6.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            far_elbow_x = -6.0 - arm_sin * 8.0
            far_elbow_y = -3.0 + abs(arm_sin) * 4.0
            far_hand_x = far_elbow_x - arm_sin * 6.0
            far_hand_y = far_elbow_y + 6.0 - arm_sin * 3.0
            ctx.move_to(-6, -8)
            ctx.line_to(far_elbow_x, far_elbow_y)
            ctx.line_to(far_hand_x, far_hand_y)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.arc(far_hand_x, far_hand_y, 3.2, 0, 2 * math.pi)
            ctx.fill()

            # NEAR ARM (Pumping forward in bent runner elbow)
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(6.5)
            near_elbow_x = 8.0 + arm_sin * 8.0
            near_elbow_y = -3.0 + abs(arm_sin) * 3.0
            near_hand_x = near_elbow_x + arm_sin * 7.0 + 3.0
            near_hand_y = near_elbow_y - 4.0 - arm_sin * 4.0
            ctx.move_to(8, -8)
            ctx.line_to(near_elbow_x, near_elbow_y)
            ctx.line_to(near_hand_x, near_hand_y)
            ctx.stroke()
            # Near runner fist
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.arc(near_hand_x, near_hand_y, 3.5, 0, 2 * math.pi)
            ctx.fill()

        else:
            # Standing / Idle relaxed arms
            breath = math.sin(self.anim_time * 3.0) * 1.5
            ctx.set_source_rgb(*SPIDER_BLUE_DARK)
            ctx.set_line_width(6.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(-6, -8)
            ctx.line_to(-12, 0)
            ctx.line_to(-10, 8 + breath)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED_DARK)
            ctx.arc(-10, 8 + breath, 3.0, 0, 2 * math.pi)
            ctx.fill()

            # Near arm
            ctx.set_source_rgb(*SPIDER_BLUE)
            ctx.set_line_width(6.5)
            ctx.move_to(8, -8)
            ctx.line_to(12, 2)
            ctx.line_to(10, 10 + breath)
            ctx.stroke()
            ctx.set_source_rgb(*SPIDER_RED)
            ctx.arc(10, 10 + breath, 3.2, 0, 2 * math.pi)
            ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 5. MASK / HEAD (Turned 3/4 Forward into the Run, McFarlane Lenses)
        # -------------------------------------------------------------
        ctx.save()
        ctx.translate(2.5, -22)  # Shifted forward in 3/4 perspective

        # Mask Silhouette in 3/4 perspective (leading nose bridge and chin towards +X)
        pat_mask = cairo.RadialGradient(3, -3, 2, 0, 0, 14)
        pat_mask.add_color_stop_rgb(0.0, *SPIDER_RED)
        pat_mask.add_color_stop_rgb(1.0, *SPIDER_RED_DARK)
        ctx.set_source(pat_mask)
        ctx.new_path()
        ctx.move_to(1, -14)
        ctx.curve_to(10, -14, 13, -5, 10, 6)
        ctx.curve_to(7, 12, 2, 13.5, 2, 13.5)
        ctx.curve_to(2, 13.5, -5, 12, -8, 6)
        ctx.curve_to(-11, -4, -8, -14, 1, -14)
        ctx.close_path()
        ctx.fill_preserve()
        ctx.set_source_rgba(*SPIDER_BLACK, 0.4)
        ctx.set_line_width(0.8)
        ctx.stroke()

        # Mask Web Lattice (Radiating from 3/4 nose bridge at x=4.0, y=0.0)
        ctx.set_source_rgba(*SPIDER_BLACK, 0.75)
        ctx.set_line_width(0.75)
        nose_x, nose_y = 3.5, 0.0
        # Radial spokes in perspective
        for ang in [-2.6, -2.1, -1.6, -1.1, -0.6, 0.0, 0.6, 1.2, 1.7, 2.2]:
            ctx.move_to(nose_x, nose_y)
            ctx.line_to(nose_x + math.cos(ang) * 11.5, nose_y + math.sin(ang) * 11.5)
            ctx.stroke()
        # Concentric web arches
        for wr in [4.0, 7.5, 11.0]:
            ctx.new_path()
            ctx.arc(nose_x, nose_y, wr, -math.pi * 0.85, math.pi * 0.85)
            ctx.stroke()

        # Expressive White Eye Lenses in 3/4 perspective
        squint_mod = self.eye_squint * 2.2

        # FAR EYE (Foreshortened at rear of mask, looking forward)
        ctx.save()
        ctx.set_source_rgb(*SPIDER_BLACK)
        ctx.new_path()
        ctx.move_to(-1.0, 1.0 + squint_mod * 0.3)
        ctx.curve_to(-4.0, 1.5, -6.5, -1.0, -7.5, -5.5 + squint_mod)
        ctx.curve_to(-4.5, -4.8, -2.5, -3.0, -1.0, 1.0 + squint_mod * 0.3)
        ctx.close_path()
        ctx.fill()

        ctx.set_source_rgb(*EYE_WHITE)
        ctx.new_path()
        ctx.move_to(-1.4, 0.5 + squint_mod * 0.3)
        ctx.curve_to(-3.8, 0.9, -5.8, -1.2, -6.8, -5.0 + squint_mod)
        ctx.curve_to(-4.2, -4.2, -2.6, -2.6, -1.4, 0.5 + squint_mod * 0.3)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # NEAR EYE (Large, dramatic comic lens facing forward)
        ctx.save()
        # Bold Black Outer Border
        ctx.set_source_rgb(*SPIDER_BLACK)
        ctx.new_path()
        ctx.move_to(4.5, 1.8 + squint_mod * 0.3)
        ctx.curve_to(8.5, 2.2, 12.0, -1.0, 13.0, -7.0 + squint_mod)
        ctx.curve_to(9.0, -5.8, 6.0, -3.5, 4.5, 1.8 + squint_mod * 0.3)
        ctx.close_path()
        ctx.fill()

        # Reflective White Inner Lens
        ctx.set_source_rgb(*EYE_WHITE)
        ctx.new_path()
        ctx.move_to(5.0, 1.0 + squint_mod * 0.3)
        ctx.curve_to(8.3, 1.4, 11.0, -1.4, 11.9, -6.2 + squint_mod)
        ctx.curve_to(8.5, -5.0, 6.3, -3.0, 5.0, 1.0 + squint_mod * 0.3)
        ctx.close_path()
        ctx.fill()

        # Subtle cyan specular rim
        ctx.set_source_rgba(0.75, 0.92, 1.0, 0.65)
        ctx.set_line_width(0.7)
        ctx.move_to(5.0, 1.0 + squint_mod * 0.3)
        ctx.curve_to(8.3, 1.4, 11.0, -1.4, 11.9, -6.2 + squint_mod)
        ctx.stroke()
        ctx.restore()

        ctx.restore()
        ctx.restore()
