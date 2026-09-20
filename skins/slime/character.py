"""Bouncy Slime desktop companion: organic squash-and-stretch hopping,
glossy translucent gel optics, floating internal nucleus, and mini-slime splits.
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


class SlimeCharacter(BaseCharacter):
    """Bouncy emerald jelly slime companion with fluid squash-and-stretch physics,
    elastic wobble oscillations, internal nucleus, and splitting mini-slimes.
    """

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="slime")
        self.can_fly = False
        self.personality = CharacterPersonality(energy=0.88, curiosity=0.82, playfulness=0.95, sleepiness=0.18)
        self.memory = CharacterMemory(skin_id="slime")
        self.behavior = CharacterBehavior("Slime", personality=self.personality, memory=self.memory, can_fly=False)

        # Elastic squash and stretch
        self.squash_x = 1.0
        self.squash_y = 1.0
        self.wobble_amp = 0.0
        self.wobble_time = 0.0
        self.hop_phase = 0.0
        self.blink_timer = 0.0
        self.is_blinking = False

        # Split mini-slimes
        self.mini_slimes: List[Dict[str, Any]] = []
        self.split_end_time = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("super_bounce", "bounce"):
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.vx = (dx / dist) * 14.0
            self.vy = min(-10.0, (dy / dist) * 14.0 - 6.0)
            self.squash_x = 0.65
            self.squash_y = 1.45
            self.state = CharacterState.JUMP
            particle_mgr.burst_stars(self.x, self.y + 14, count=8, color=(0.4, 0.95, 0.5))
            particle_mgr.burst_confetti(self.x, self.y - 10, count=12)
            audio_mgr.play("sparkle")
            self.memory.record_interaction("super_bounce")
            return True

        elif ability_name in ("jelly_split", "split"):
            # Split into 3 bouncy mini-slimes!
            self.mini_slimes = []
            self.split_end_time = time.time() + 2.0
            for angle in (0.0, math.pi * 0.66, math.pi * 1.33):
                self.mini_slimes.append({
                    "angle": angle,
                    "dist": 0.0,
                    "target_dist": random.uniform(25.0, 38.0),
                    "hop": random.uniform(0, math.pi)
                })
            self.wobble_amp = 0.6
            particle_mgr.burst_energy_orbs(self.x, self.y, count=6, color=(0.2, 0.9, 0.4))
            particle_mgr.burst_confetti(self.x, self.y - 12, count=14)
            audio_mgr.play("sparkle")
            self.memory.record_interaction("jelly_split")
            return True

        elif ability_name in ("wobble", "jiggle", "celebrate"):
            self.wobble_amp = 0.8
            particle_mgr.burst_hearts(self.x, self.y - 18, count=4)
            audio_mgr.play("sparkle")
            self.memory.record_interaction("wobble")
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
        self.wobble_time += dt * 14.0
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)
        speed_mult = config_data.get("speed", 1.0)

        # Decay wobble ripples
        if self.wobble_amp > 0.01:
            self.wobble_amp *= 0.92
        else:
            self.wobble_amp = 0.0

        # Update mini-slimes
        if self.mini_slimes:
            if now < self.split_end_time:
                for ms in self.mini_slimes:
                    ms["dist"] += (ms["target_dist"] - ms["dist"]) * 0.15
                    ms["hop"] += dt * 8.0
            else:
                # Merge back
                all_merged = True
                for ms in self.mini_slimes:
                    ms["dist"] *= 0.80
                    if ms["dist"] > 2.0:
                        all_merged = False
                if all_merged:
                    self.mini_slimes = []
                    self.squash_x = 1.3
                    self.squash_y = 0.7
                    self.wobble_amp = 0.5
                    particle_mgr.burst_stars(self.x, self.y, count=6, color=(0.4, 0.95, 0.5))

        # Look direction
        if abs(cursor_x - self.x) > 8.0:
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

        # Blinking
        self.blink_timer -= dt
        if self.blink_timer <= 0:
            self.is_blinking = not self.is_blinking
            self.blink_timer = 0.12 if self.is_blinking else random.uniform(2.5, 5.5)

        dx = cursor_x - self.x
        dy = cursor_y - self.y
        dist = math.hypot(dx, dy)

        is_moving = False
        if dist > 50.0 and config_data.get("cursor_follow", True):
            is_moving = True
            hop_spd = min(8.0 * speed_mult, max(2.5, dist * 0.055))
            self.vx += ((dx / dist) * hop_spd - self.vx) * 0.16
            self.vy += ((dy / dist) * hop_spd - self.vy) * 0.16
            self.state = CharacterState.RUN if dist > 180.0 else CharacterState.WALK
            self.hop_phase += dt * (14.0 if self.state == CharacterState.RUN else 9.0)
        elif self.state in (BehaviorState.RUN, BehaviorState.WALK):
            is_moving = True
            tx, ty = self.behavior.target_x, self.behavior.target_y
            tdx = tx - self.x
            tdy = ty - self.y
            tdist = math.hypot(tdx, tdy)
            if tdist > 14.0:
                spd = 7.0 * speed_mult if self.state == BehaviorState.RUN else 4.0 * speed_mult
                self.vx += ((tdx / tdist) * spd - self.vx) * 0.15
                self.vy += ((tdy / tdist) * spd - self.vy) * 0.15
                self.hop_phase += dt * (12.0 if self.state == BehaviorState.RUN else 8.0)
            else:
                self.vx *= 0.8
                self.vy *= 0.8
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.80
            self.vy *= 0.80
            self.hop_phase *= 0.85

        self.x += self.vx
        self.y += self.vy

        # Screen boundary clamp
        self.x = max(min_x + 45.0, min(min_x + screen_w - 45.0, self.x))
        self.y = max(min_y + 45.0, min(min_y + screen_h - 55.0, self.y))

        # Squash and stretch kinematics
        if is_moving:
            hop_sin = math.sin(self.hop_phase)
            if hop_sin > 0:
                # Mid-air vertical stretch
                target_sx = 0.80
                target_sy = 1.25
            else:
                # Compression pre-hop
                target_sx = 1.25
                target_sy = 0.80
            self.squash_x += (target_sx - self.squash_x) * 0.25
            self.squash_y += (target_sy - self.squash_y) * 0.25
        else:
            # Idle rhythmic breathing squish
            idle_breath = math.sin(self.anim_time * 2.0) * 0.05
            target_sx = 1.0 + idle_breath
            target_sy = 1.0 - idle_breath
            self.squash_x += (target_sx - self.squash_x) * 0.15
            self.squash_y += (target_sy - self.squash_y) * 0.15

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        # Draw split mini-slimes
        for ms in self.mini_slimes:
            ms_x = self.x + math.cos(ms["angle"]) * ms["dist"]
            ms_y = self.y + math.sin(ms["angle"]) * ms["dist"] - math.sin(ms["hop"]) * 6.0
            ctx.save()
            ctx.translate(ms_x, ms_y)
            ctx.scale(0.48, 0.48)
            # Translucent emerald body
            ctx.set_source_rgba(0.2, 0.85, 0.4, 0.8)
            ctx.arc(0, 0, 14, 0, math.pi * 2)
            ctx.fill()
            # Mini cute eyes
            ctx.set_source_rgb(0.1, 0.15, 0.1)
            ctx.arc(-3, -2, 1.8, 0, math.pi * 2)
            ctx.arc(3, -2, 1.8, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

        # Main Slime
        ctx.save()
        ctx.translate(self.x, self.y)

        # Apply wobble ripple and squash/stretch
        wobble_x = 1.0 + math.sin(self.wobble_time) * self.wobble_amp
        wobble_y = 1.0 - math.sin(self.wobble_time) * self.wobble_amp
        ctx.scale(self.squash_x * wobble_x, self.squash_y * wobble_y)

        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Outer Translucent Emerald Jelly
        # Multi-stop linear gradient for 3D liquid gel volume
        pat = cairo.LinearGradient(0, -22, 0, 22)
        pat.add_color_stop_rgba(0.0, 0.45, 0.95, 0.55, 0.90)  # Bright emerald crest
        pat.add_color_stop_rgba(0.5, 0.15, 0.80, 0.35, 0.85)  # Vibrant green core
        pat.add_color_stop_rgba(1.0, 0.08, 0.60, 0.25, 0.95)  # Deep forest base
        ctx.set_source(pat)

        ctx.new_path()
        # Rounded teardrop droplet dome
        ctx.move_to(0, -22)
        ctx.curve_to(14, -20, 24, -4, 22, 12)
        ctx.curve_to(20, 22, -20, 22, -22, 12)
        ctx.curve_to(-24, -4, -14, -20, 0, -22)
        ctx.close_path()
        ctx.fill()

        # 2. Glowing Inner Core / Nucleus
        ctx.save()
        core_bob = math.sin(self.anim_time * 2.5) * 2.0
        ctx.translate(0, 4 + core_bob)
        ctx.set_source_rgba(0.7, 1.0, 0.6, 0.55)
        ctx.arc(0, 0, 7.5, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # 3. Glossy Glass Specular Highlights
        ctx.save()
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.65)
        # Top-left crescent reflection
        ctx.new_path()
        ctx.arc(-7, -12, 5.0, math.pi * 0.8, math.pi * 1.8)
        ctx.set_line_width(2.2)
        ctx.stroke()
        # Secondary small glint
        ctx.arc(10, -8, 1.8, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # 4. Cheerful Kawaii Face: Expressive Eyes & Smile
        ctx.save()
        if not self.is_blinking:
            # Big round dark jelly eyes
            ctx.set_source_rgb(0.08, 0.15, 0.08)
            ctx.arc(-5, -2, 2.8, 0, math.pi * 2)
            ctx.arc(5, -2, 2.8, 0, math.pi * 2)
            ctx.fill()

            # Specular twinkle reflections
            ctx.set_source_rgb(1.0, 1.0, 1.0)
            ctx.arc(-4.2, -3.2, 1.0, 0, math.pi * 2)
            ctx.arc(5.8, -3.2, 1.0, 0, math.pi * 2)
            ctx.fill()
            ctx.arc(-5.8, -1.0, 0.5, 0, math.pi * 2)
            ctx.arc(4.2, -1.0, 0.5, 0, math.pi * 2)
            ctx.fill()
        else:
            # Happy closed crescent blink eyes: ^^
            ctx.set_source_rgb(0.08, 0.15, 0.08)
            ctx.set_line_width(1.8)
            ctx.new_path()
            ctx.arc(-5, -2, 2.8, math.pi * 1.1, math.pi * 1.9)
            ctx.stroke()
            ctx.new_path()
            ctx.arc(5, -2, 2.8, math.pi * 1.1, math.pi * 1.9)
            ctx.stroke()

        # Happy open mouth smile
        ctx.set_source_rgb(0.1, 0.2, 0.1)
        ctx.new_path()
        ctx.arc(0, 3, 3.2, 0, math.pi)
        ctx.close_path()
        ctx.fill()
        # Pink tongue
        ctx.set_source_rgb(1.0, 0.55, 0.65)
        ctx.arc(0, 4.5, 1.6, 0, math.pi)
        ctx.fill()

        # Blushing cheeks
        ctx.set_source_rgba(1.0, 0.45, 0.6, 0.35)
        ctx.arc(-10, 2, 2.5, 0, math.pi * 2)
        ctx.arc(10, 2, 2.5, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        ctx.restore()
