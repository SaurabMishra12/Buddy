"""Ghost desktop companion: ethereal floating, organic undulating spectral tail,
internal glowing soul flame, floating gesturing hands, cute spooks, and spirit wisps.
"""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, List
from skins.base import BaseCharacter, CharacterState
from behavior.personality import CharacterPersonality
from behavior.memory import CharacterMemory
from behavior.state_machine import CharacterBehavior, BehaviorState


class GhostCharacter(BaseCharacter):
    """Adorable spectral phantom companion with multi-segment undulating tail physics,
    internal glowing soul flame, floating expressive hands, and playful cute spooks.
    """

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="ghost")
        self.can_fly = True
        self.is_airborne = True
        self.personality = CharacterPersonality(energy=0.74, curiosity=0.88, playfulness=0.96, sleepiness=0.28)
        self.memory = CharacterMemory(skin_id="ghost")
        self.behavior = CharacterBehavior("Ghost", personality=self.personality, memory=self.memory, can_fly=True)

        self.spectral_opacity = 0.88
        self.wave_time = 0.0
        self.hover_y = 0.0
        self.soul_pulse = 0.0
        self.is_spooking = False
        self.spook_end_time = 0.0
        self.spook_scale = 1.0
        self.spirit_wisps: List[Dict[str, Any]] = []

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("spook_burst", "spook", "boo_spook"):
            # Dramatic cute "BOO!" expansion with raised paws
            self.is_spooking = True
            self.spook_end_time = time.time() + 1.4
            self.vy = -7.5
            particle_mgr.shockwave(self.x, self.y, max_radius=80.0, color=(0.75, 0.90, 1.0))
            particle_mgr.burst_stars(self.x, self.y, count=14, color=(0.8, 0.92, 1.0))
            particle_mgr.burst_hearts(self.x, self.y - 18, count=3)
            audio_mgr.play("magic")
            self.memory.record_interaction("spook_burst")
            return True

        elif ability_name in ("spectral_fade", "phase_shift", "fade"):
            # Phase into ethereal plane
            self.spectral_opacity = 0.18
            particle_mgr.shockwave(self.x, self.y, max_radius=65.0, color=(0.6, 0.85, 1.0))
            for _ in range(8):
                particle_mgr.burst_stars(
                    self.x + random.uniform(-15, 15),
                    self.y + random.uniform(-15, 15),
                    count=2,
                    color=(0.7, 0.9, 1.0)
                )
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.vx = (dx / dist) * 14.0
            self.vy = (dy / dist) * 14.0
            audio_mgr.play("swoosh")
            self.memory.record_interaction("spectral_fade")
            return True

        elif ability_name in ("ethereal_float", "spirit_wisps", "wisps"):
            # Summon 2 mini companion will-o'-the-wisps
            self.spirit_wisps = []
            for angle in (0.0, math.pi):
                self.spirit_wisps.append({
                    "angle": angle,
                    "radius": 24.0,
                    "life": 2.2,
                    "color": (0.6, 0.9, 1.0) if angle == 0 else (0.8, 0.6, 1.0)
                })
            particle_mgr.burst_stars(self.x, self.y, count=8, color=(0.7, 0.88, 1.0))
            audio_mgr.play("magic")
            self.memory.record_interaction("ethereal_float")
            return True

        return False

    def update(
        self,
        dt: float,
        cursor_x: float,
        cursor_y: float,
        screen_bounds: Tuple[int, int, int, int],
        particle_mgr: Any,
        audio_mgr: Any,
        config_data: Dict[str, Any]
    ) -> None:
        self.anim_time += dt * 3.8
        self.wave_time += dt * 6.8
        self.soul_pulse += dt * 5.0
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)
        speed_mult = config_data.get("speed", 1.0)

        # Spook mode duration & scale animation
        if self.is_spooking:
            if now < self.spook_end_time:
                self.spook_scale += (1.28 - self.spook_scale) * 0.25
            else:
                self.is_spooking = False
        else:
            self.spook_scale += (1.0 - self.spook_scale) * 0.18

        # Restore spectral opacity smoothly
        if self.spectral_opacity < 0.88:
            self.spectral_opacity = min(0.88, self.spectral_opacity + dt * 0.6)

        # Facing direction
        if abs(cursor_x - self.x) > 6.0:
            self.facing_right = (cursor_x >= self.x)

        # Update orbiting spirit wisps
        for wisp in self.spirit_wisps:
            wisp["angle"] += dt * 3.8
            wisp["life"] -= dt
            wx = self.x + math.cos(wisp["angle"]) * wisp["radius"]
            wy = self.y + math.sin(wisp["angle"]) * (wisp["radius"] * 0.5)
            if random.random() < 0.35:
                particle_mgr.burst_stars(wx, wy, count=1, size=2.5, color=wisp["color"])
        self.spirit_wisps = [w for w in self.spirit_wisps if w["life"] > 0]

        # Autonomous AI decisions
        cursor_speed = math.hypot(cursor_x - self.x, cursor_y - self.y) / max(1e-4, dt)
        self.behavior.evaluate_next_action(
            dt=dt,
            char_x=self.x,
            char_y=self.y,
            cursor_x=cursor_x,
            cursor_y=cursor_y,
            cursor_speed=cursor_speed,
            screen_bounds=screen_bounds,
            pomodoro_state=config_data.get("pomodoro_state", "IDLE"),
            activity_level=activity
        )
        self.state = self.behavior.current_state

        # Organic floating hover
        self.hover_y = (
            math.sin(self.anim_time * 1.8) * 6.5 +
            math.cos(self.anim_time * 3.0) * 1.8
        )

        # Locomotion & cursor chase
        dx = cursor_x - self.x
        dy = cursor_y - self.y
        dist = math.hypot(dx, dy)

        if dist > 55.0 and config_data.get("cursor_follow", True):
            fly_spd = min(9.5 * speed_mult, max(3.0, dist * 0.060))
            self.vx += ((dx / dist) * fly_spd - self.vx) * 0.16
            self.vy += ((dy / dist) * fly_spd - self.vy) * 0.16
            self.state = CharacterState.FLY
        elif self.state in (BehaviorState.FLY, BehaviorState.WALK):
            tx, ty = self.behavior.target_x, self.behavior.target_y
            tdx = tx - self.x
            tdy = ty - self.y
            tdist = math.hypot(tdx, tdy)
            if tdist > 15.0:
                spd = 5.2 * speed_mult
                self.vx += ((tdx / tdist) * spd - self.vx) * 0.14
                self.vy += ((tdy / tdist) * spd - self.vy) * 0.14
            else:
                self.vx *= 0.84
                self.vy *= 0.84
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.84
            self.vy *= 0.84

        self.x += self.vx
        self.y += self.vy

        # Screen clamp
        self.x = max(min_x + 45.0, min(min_x + screen_w - 45.0, self.x))
        self.y = max(min_y + 45.0, min(min_y + screen_h - 65.0, self.y))

        # Dynamic ethereal tilt
        target_tilt = (self.vx / 10.0) * 0.18
        self.tilt += (target_tilt - self.tilt) * 0.18

        # Ambient floating sparkles
        if random.random() < 0.22:
            particle_mgr.burst_stars(
                self.x + random.uniform(-12, 12),
                self.y + 12,
                count=1,
                size=3.0,
                color=(0.82, 0.92, 1.0)
            )

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        # Draw orbiting spirit wisps first
        for wisp in self.spirit_wisps:
            wx = self.x + math.cos(wisp["angle"]) * wisp["radius"]
            wy = self.y + math.sin(wisp["angle"]) * (wisp["radius"] * 0.5)
            ctx.save()
            ctx.translate(wx, wy)
            col = wisp["color"]
            ctx.set_source_rgba(col[0], col[1], col[2], 0.4)
            ctx.arc(0, 0, 6.0, 0, math.pi * 2)
            ctx.fill()
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.85)
            ctx.arc(0, 0, 2.5, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

        ctx.save()
        ctx.translate(self.x, self.y + self.hover_y)
        ctx.rotate(self.tilt)
        ctx.scale(self.spook_scale, self.spook_scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        op = self.spectral_opacity

        # -------------------------------------------------------------
        # 1. Soft Ethereal Aura Glow
        # -------------------------------------------------------------
        ctx.save()
        aura_rad = 28.0 + 4.0 * math.sin(self.soul_pulse)
        aura_grad = cairo.RadialGradient(0, 0, 6, 0, 0, aura_rad)
        aura_grad.add_color_stop_rgba(0.0, 0.65, 0.90, 1.0, op * 0.35)
        aura_grad.add_color_stop_rgba(0.6, 0.50, 0.80, 0.95, op * 0.15)
        aura_grad.add_color_stop_rgba(1.0, 0.40, 0.70, 0.90, 0.0)
        ctx.set_source(aura_grad)
        ctx.arc(0, 0, aura_rad, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 2. Flowing Translucent Ghost Sheet Body with Undulating Tail
        # -------------------------------------------------------------
        ctx.save()

        # Trailing tail inertia based on horizontal movement
        tail_drag = -self.vx * 0.65

        # 4 continuous wave harmonics for organic billowing folds
        w1 = math.sin(self.wave_time) * 3.5
        w2 = math.sin(self.wave_time + 1.3) * 3.5
        w3 = math.sin(self.wave_time + 2.6) * 3.5
        w4 = math.sin(self.wave_time + 3.9) * 3.5

        # Translucent ghostly sheet gradient
        sheet_grad = cairo.LinearGradient(0, -18, 0, 26)
        sheet_grad.add_color_stop_rgba(0.0, 0.98, 1.0, 1.0, op)
        sheet_grad.add_color_stop_rgba(0.6, 0.92, 0.96, 1.0, op * 0.92)
        sheet_grad.add_color_stop_rgba(1.0, 0.75, 0.88, 1.0, op * 0.70)
        ctx.set_source(sheet_grad)

        ctx.new_path()
        # Rounded dome head
        ctx.arc(0, -7, 16.5, math.pi, 0)
        # Right draped body contour
        ctx.curve_to(18, 5, 17 + tail_drag * 0.5, 16, 19 + tail_drag, 24 + w1)

        # Undulating bottom hem folds
        ctx.curve_to(14 + tail_drag, 20 + w2, 9 + tail_drag, 27 + w2, 5 + tail_drag, 22 + w2)
        ctx.curve_to(1 + tail_drag, 19 + w3, -4 + tail_drag, 26 + w3, -8 + tail_drag, 22 + w3)
        ctx.curve_to(-12 + tail_drag, 19 + w4, -16 + tail_drag, 27 + w4, -19 + tail_drag, 23 + w4)

        # Left draped body contour
        ctx.curve_to(-17 + tail_drag * 0.5, 15, -18, 4, -16.5, -7)
        ctx.close_path()
        ctx.fill()

        # Sheet subtle rim highlight
        ctx.set_source_rgba(1.0, 1.0, 1.0, op * 0.6)
        ctx.set_line_width(1.2)
        ctx.stroke()

        ctx.restore()

        # -------------------------------------------------------------
        # 3. Internal Glowing Soul Flame (Will-o'-the-Wisp Core)
        # -------------------------------------------------------------
        ctx.save()
        soul_y = 2.0 + math.sin(self.soul_pulse) * 2.0
        soul_pulse_r = 5.5 + math.sin(self.soul_pulse * 1.5) * 1.2
        soul_grad = cairo.RadialGradient(0, soul_y, 1, 0, soul_y, soul_pulse_r * 2.2)
        soul_grad.add_color_stop_rgba(0.0, 0.9, 1.0, 1.0, op * 0.8)
        soul_grad.add_color_stop_rgba(0.4, 0.35, 0.85, 1.0, op * 0.55)
        soul_grad.add_color_stop_rgba(1.0, 0.20, 0.60, 0.9, 0.0)
        ctx.set_source(soul_grad)
        ctx.arc(0, soul_y, soul_pulse_r * 2.0, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 4. Floating Articulated Spectral Hands
        # -------------------------------------------------------------
        # Hands position reacts to spook mode or normal floating
        if self.is_spooking:
            # Raised spooky "BOO!" paws beside head
            hand_targets = [
                (-18.0, -10.0 + math.sin(self.wave_time * 2.0) * 3.0),
                (18.0, -10.0 + math.cos(self.wave_time * 2.0) * 3.0)
            ]
        else:
            # Gentle relaxed floating drift
            hand_targets = [
                (-17.0, 4.0 + math.sin(self.anim_time * 2.0) * 2.5),
                (17.0, 4.0 + math.cos(self.anim_time * 2.0) * 2.5)
            ]

        for hx, hy in hand_targets:
            ctx.save()
            ctx.translate(hx, hy)
            # Soft glowing ghost paw
            ctx.set_source_rgba(0.95, 0.98, 1.0, op * 0.9)
            ctx.scale(1.0, 0.85)
            ctx.arc(0, 0, 4.2, 0, math.pi * 2)
            ctx.fill()
            ctx.set_source_rgba(1.0, 1.0, 1.0, op * 0.7)
            ctx.set_line_width(0.9)
            ctx.stroke()
            ctx.restore()

        # -------------------------------------------------------------
        # 5. Adorable Expressive Face
        # -------------------------------------------------------------
        ctx.save()

        if self.is_spooking:
            # Spooky cute "BOO!" face
            # Wide glowing round eyes
            ctx.set_source_rgba(0.10, 0.12, 0.18, op)
            ctx.arc(-5, -6, 3.8, 0, math.pi * 2)
            ctx.fill()
            ctx.arc(5, -6, 3.8, 0, math.pi * 2)
            ctx.fill()

            # White glowing pupils
            ctx.set_source_rgba(0.8, 0.95, 1.0, op)
            ctx.arc(-5, -6, 1.8, 0, math.pi * 2)
            ctx.fill()
            ctx.arc(5, -6, 1.8, 0, math.pi * 2)
            ctx.fill()

            # Wide comical open "O" mouth
            ctx.set_source_rgba(0.12, 0.14, 0.20, op)
            ctx.save()
            ctx.translate(0, 1)
            ctx.scale(0.8, 1.25)
            ctx.arc(0, 0, 4.0, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

        else:
            # Cute cheerful normal face
            # Glossy obsidian eyes
            ctx.set_source_rgba(0.12, 0.15, 0.22, op)
            ctx.arc(-4.5, -5.5, 2.9, 0, math.pi * 2)
            ctx.fill()
            ctx.arc(4.5, -5.5, 2.9, 0, math.pi * 2)
            ctx.fill()

            # Double specular eye highlights
            ctx.set_source_rgba(1.0, 1.0, 1.0, op)
            ctx.arc(-5.5, -6.5, 1.1, 0, math.pi * 2)
            ctx.fill()
            ctx.arc(3.5, -6.5, 1.1, 0, math.pi * 2)
            ctx.fill()
            ctx.arc(-3.8, -4.8, 0.5, 0, math.pi * 2)
            ctx.fill()
            ctx.arc(5.2, -4.8, 0.5, 0, math.pi * 2)
            ctx.fill()

            # Sweet smiling mouth
            ctx.set_source_rgba(0.15, 0.18, 0.25, op)
            ctx.set_line_width(1.3)
            ctx.arc(0, -2, 2.2, 0.15, math.pi - 0.15)
            ctx.stroke()

        # Rosy blushing cheeks
        ctx.set_source_rgba(1.0, 0.50, 0.68, op * 0.55)
        ctx.arc(-8.5, -2.0, 2.8, 0, math.pi * 2)
        ctx.fill()
        ctx.arc(8.5, -2.0, 2.8, 0, math.pi * 2)
        ctx.fill()

        ctx.restore()
        ctx.restore()
