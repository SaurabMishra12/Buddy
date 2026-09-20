"""Fairy desktop companion: rapid fluttering gossamer wings, stardust trails,
healing aura vortex, and graceful aerial loopings.
"""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from behavior.personality import CharacterPersonality
from behavior.memory import CharacterMemory
from behavior.state_machine import CharacterBehavior, BehaviorState


class FairyCharacter(BaseCharacter):
    """Magical woodland fairy companion with rapid iridescent wing flutters,
    shimmering pixie dust trails, and aerial loopings.
    """

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="fairy")
        self.can_fly = True
        self.is_airborne = True
        self.personality = CharacterPersonality(energy=0.86, curiosity=0.88, playfulness=0.92, sleepiness=0.22)
        self.memory = CharacterMemory(skin_id="fairy")
        self.behavior = CharacterBehavior("Fairy", personality=self.personality, memory=self.memory, can_fly=True)

        self.wing_flutter = 0.0
        self.hover_y = 0.0
        self.loop_angle = 0.0
        self.is_looping = False
        self.loop_end_time = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("sparkle_trail", "sparkle_burst", "sparkle"):
            self.is_looping = True
            self.loop_end_time = time.time() + 1.2
            for _ in range(12):
                particle_mgr.burst_stars(
                    self.x + random.uniform(-15, 15),
                    self.y + random.uniform(-15, 15),
                    count=2,
                    color=(1.0, 0.9, 0.35)
                )
                particle_mgr.burst_hearts(self.x, self.y - 10, count=1)
            audio_mgr.play("magic")
            self.memory.record_interaction("sparkle_trail")
            return True

        elif ability_name in ("healing_glow", "healing_aura"):
            particle_mgr.shockwave(self.x, self.y, max_radius=85.0, color=(0.45, 1.0, 0.65))
            particle_mgr.burst_stars(self.x, self.y, count=16, color=(0.6, 1.0, 0.75))
            audio_mgr.play("magic")
            self.memory.record_interaction("healing_glow")
            return True

        elif ability_name in ("flutter_hover", "celebrate"):
            self.vy = -7.0
            particle_mgr.burst_stars(self.x, self.y + 12, count=8, color=(1.0, 0.65, 0.9))
            audio_mgr.play("magic")
            self.memory.record_interaction("flutter_hover")
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
        self.anim_time += dt * 4.0
        self.wing_flutter += dt * 26.0  # Rapid organic dragonfly/butterfly flutter
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)
        speed_mult = config_data.get("speed", 1.0)

        # Loop celebration
        if self.is_looping:
            self.loop_angle += dt * (math.pi * 2.0 / 0.8)
            if now >= self.loop_end_time or self.loop_angle >= math.pi * 2.0:
                self.is_looping = False
                self.loop_angle = 0.0

        # Look direction
        if abs(cursor_x - self.x) > 6.0 and not self.is_looping:
            self.facing_right = (cursor_x >= self.x)

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

        # Ethereal floating hover
        self.hover_y = math.sin(self.anim_time * 2.2) * 5.5

        dx = cursor_x - self.x
        dy = cursor_y - self.y
        dist = math.hypot(dx, dy)

        if dist > 50.0 and config_data.get("cursor_follow", True):
            fly_spd = min(8.5 * speed_mult, max(2.5, dist * 0.06))
            self.vx += ((dx / dist) * fly_spd - self.vx) * 0.16
            self.vy += ((dy / dist) * fly_spd - self.vy) * 0.16
            self.state = CharacterState.FLY
        elif self.state in (BehaviorState.FLY, BehaviorState.WALK):
            tx, ty = self.behavior.target_x, self.behavior.target_y
            tdx = tx - self.x
            tdy = ty - self.y
            tdist = math.hypot(tdx, tdy)
            if tdist > 15.0:
                spd = 6.5 * speed_mult
                self.vx += ((tdx / tdist) * spd - self.vx) * 0.14
                self.vy += ((tdy / tdist) * spd - self.vy) * 0.14
            else:
                self.vx *= 0.8
                self.vy *= 0.8
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.82
            self.vy *= 0.82

        self.x += self.vx
        self.y += self.vy

        # Screen clamp
        self.x = max(min_x + 45.0, min(min_x + screen_w - 45.0, self.x))
        self.y = max(min_y + 45.0, min(min_y + screen_h - 55.0, self.y))

        # Banking flight tilt
        if not self.is_looping:
            target_tilt = (self.vx / 14.0) * 0.20
            self.tilt += (target_tilt - self.tilt) * 0.22

        # Ambient stardust drop
        if random.random() < 0.26:
            particle_mgr.burst_stars(
                self.x + random.uniform(-4, 4),
                self.y + 12,
                count=1,
                size=3.2,
                color=(1.0, 0.90, 0.4)
            )

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        ctx.save()
        ctx.translate(self.x, self.y + self.hover_y)

        if self.is_looping:
            ctx.rotate(self.loop_angle)
        else:
            ctx.rotate(self.tilt)

        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # -------------------------------------------------------------
        # 1. Gossamer Shimmering Wings (Anchored Behind Back)
        # -------------------------------------------------------------
        # Proper wing spread between 0.35 and 1.0 — never inverted over face!
        wing_span = 0.35 + 0.65 * abs(math.cos(self.wing_flutter))
        wing_rot = math.sin(self.wing_flutter) * 0.22

        ctx.save()
        ctx.translate(-4, -6)
        ctx.rotate(wing_rot)
        ctx.scale(wing_span, 1.0)

        # Upper Fore-Wing (Large Translucent Teardrop with Iridescent Sheen)
        pat_wing = cairo.LinearGradient(0, 0, -35, -25)
        pat_wing.add_color_stop_rgba(0.0, 0.9, 0.98, 1.0, 0.85)  # Shimmering cyan-white
        pat_wing.add_color_stop_rgba(0.6, 0.65, 0.85, 1.0, 0.55) # Ethereal violet
        pat_wing.add_color_stop_rgba(1.0, 0.95, 0.8, 1.0, 0.70)  # Rose gold edge
        ctx.set_source(pat_wing)

        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-16, -26, -34, -20, -28, 0)
        ctx.curve_to(-20, 10, -8, 6, 0, 0)
        ctx.close_path()
        ctx.fill()

        # Wing gold veins
        ctx.set_source_rgba(1.0, 0.9, 0.4, 0.6)
        ctx.set_line_width(1.0)
        ctx.move_to(0, 0)
        ctx.curve_to(-12, -12, -22, -10, -26, 0)
        ctx.stroke()

        # Lower Hind-Wing (Smaller Teardrop)
        ctx.set_source_rgba(0.75, 0.9, 1.0, 0.6)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-14, 4, -24, 14, -16, 22)
        ctx.curve_to(-10, 20, -4, 10, 0, 0)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 2. Slender Hovering Legs & Golden Slippers
        # -------------------------------------------------------------
        ctx.save()
        leg_sway = math.sin(self.anim_time * 2.0) * 2.0
        ctx.set_source_rgb(0.96, 0.84, 0.75)  # Pale skin tone
        ctx.set_line_width(2.8)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        # Left leg
        ctx.move_to(-3, 10)
        ctx.line_to(-5 - leg_sway, 20)
        ctx.stroke()
        # Right leg
        ctx.move_to(3, 10)
        ctx.line_to(1 + leg_sway, 20)
        ctx.stroke()

        # Tiny golden pixie slippers
        ctx.set_source_rgb(1.0, 0.85, 0.25)
        ctx.arc(-5 - leg_sway, 20, 2.0, 0, math.pi * 2)
        ctx.fill()
        ctx.arc(1 + leg_sway, 20, 2.0, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 3. Emerald Flower Petal Dress
        # -------------------------------------------------------------
        ctx.save()
        ctx.set_source_rgb(0.35, 0.85, 0.45)  # Leaf green dress
        ctx.new_path()
        ctx.move_to(-7, -4)
        ctx.line_to(7, -4)
        ctx.line_to(11, 11)
        ctx.line_to(0, 14)
        ctx.line_to(-11, 11)
        ctx.close_path()
        ctx.fill()

        # Golden waist sash
        ctx.set_source_rgb(1.0, 0.85, 0.2)
        ctx.rectangle(-7, 2, 14, 2.2)
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 4. Fairy Head, Golden Locks, Wand & Halo
        # -------------------------------------------------------------
        ctx.save()
        # Head (porcelain skin)
        ctx.set_source_rgb(0.96, 0.84, 0.75)
        ctx.arc(0, -12, 8.5, 0, math.pi * 2)
        ctx.fill()

        # Large sparkly anime eyes
        ctx.set_source_rgb(0.1, 0.5, 0.3)  # Emerald eyes
        ctx.arc(2.5, -12.5, 2.2, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(3.0, -13.2, 0.8, 0, math.pi * 2)
        ctx.fill()

        # Sweet smile
        ctx.set_source_rgb(0.85, 0.3, 0.4)
        ctx.set_line_width(1.2)
        ctx.new_path()
        ctx.arc(1.5, -9, 2.0, 0, math.pi)
        ctx.stroke()

        # Blushing pink cheeks
        ctx.set_source_rgba(1.0, 0.4, 0.6, 0.4)
        ctx.arc(1.0, -9.5, 2.0, 0, math.pi * 2)
        ctx.fill()

        # Shimmering golden blonde hair
        ctx.set_source_rgb(1.0, 0.88, 0.35)
        # Hair crown
        ctx.new_path()
        ctx.arc(0, -15, 8.5, math.pi * 0.85, math.pi * 2.15)
        ctx.fill()
        # Side bangs & flowing twin tails
        hair_s = math.sin(self.anim_time * 3.0) * 2.0
        ctx.new_path()
        ctx.move_to(-7, -14)
        ctx.curve_to(-12, -8, -14 + hair_s, 2, -10 + hair_s, 6)
        ctx.curve_to(-8, 2, -5, -6, -5, -12)
        ctx.close_path()
        ctx.fill()

        # Tiny flower blossom hair pin
        ctx.set_source_rgb(1.0, 0.5, 0.7)
        ctx.arc(-5, -17, 2.5, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgb(1.0, 0.9, 0.2)
        ctx.arc(-5, -17, 1.0, 0, math.pi * 2)
        ctx.fill()

        # Magic Star Wand in Hand
        ctx.set_source_rgb(1.0, 0.85, 0.2)
        ctx.set_line_width(1.8)
        ctx.move_to(5, -4)
        ctx.line_to(14, -14)
        ctx.stroke()
        # Star tip
        ctx.arc(14, -14, 2.8, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        ctx.restore()
