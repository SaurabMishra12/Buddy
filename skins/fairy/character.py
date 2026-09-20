"""Fairy desktop companion: flutter wings, sparkle trails, and healing stardust."""

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
    """Magical woodland fairy with rapid fluttering wings and stardust trails."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="fairy")
        self.can_fly = True
        self.is_airborne = True
        self.personality = CharacterPersonality(energy=0.85, curiosity=0.85, playfulness=0.90, sleepiness=0.25)
        self.memory = CharacterMemory(skin_id="fairy")
        self.behavior = CharacterBehavior("Fairy", personality=self.personality, memory=self.memory, can_fly=True)

        self.wing_flutter = 0.0
        self.hover_y = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("sparkle_trail", "sparkle_burst", "sparkle"):
            for _ in range(8):
                particle_mgr.burst_stars(self.x, self.y, count=3, color=(1.0, 0.85, 0.3))
                particle_mgr.burst_hearts(self.x, self.y, count=1)
            audio_mgr.play("magic")
            self.memory.record_interaction("sparkle_trail")
            return True

        elif ability_name == "healing_glow":
            particle_mgr.shockwave(self.x, self.y, max_radius=75.0, color=(0.4, 0.95, 0.5))
            particle_mgr.burst_stars(self.x, self.y, count=12, color=(0.5, 1.0, 0.6))
            audio_mgr.play("magic")
            self.memory.record_interaction("healing_glow")
            return True

        elif ability_name == "flutter_hover":
            self.vy = -8.0
            particle_mgr.burst_stars(self.x, self.y + 12, count=6, color=(1.0, 0.6, 0.9))
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
        self.wing_flutter += dt * 24.0  # Rapid butterfly wing flutter
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)

        # Facing
        if abs(cursor_x - self.x) > 6.0:
            self.facing_right = (cursor_x >= self.x)

        # Autonomous decisions
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

        self.hover_y = math.sin(self.anim_time * 2.0) * 6.0

        if self.state in (BehaviorState.FLY, BehaviorState.WALK):
            tx, ty = self.behavior.target_x, self.behavior.target_y
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            if dist > 14.0:
                self.vx += ((dx / dist) * 5.0 - self.vx) * 0.14
                self.vy += ((dy / dist) * 5.0 - self.vy) * 0.14
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
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 70.0, self.y))

        # Ambient stardust drop
        if random.random() < 0.28:
            particle_mgr.burst_stars(self.x, self.y + 12, count=1, size=3.5, color=(1.0, 0.85, 0.4))

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        ctx.save()
        ctx.translate(self.x, self.y + self.hover_y)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Gossamer Fairy Wings (Shimmering Translucent Iridescent)
        wing_scale_x = math.sin(self.wing_flutter)
        ctx.save()
        ctx.translate(-4, -6)
        ctx.scale(wing_scale_x, 1.0)

        # Top large wing
        ctx.set_source_rgba(0.7, 0.95, 1.0, 0.65)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-16, -26, -34, -18, -26, 0)
        ctx.curve_to(-18, 12, -8, 8, 0, 0)
        ctx.close_path()
        ctx.fill()
        # Wing veins
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.8)
        ctx.set_line_width(1.0)
        ctx.stroke()

        # Bottom smaller wing
        ctx.set_source_rgba(0.9, 0.7, 1.0, 0.55)
        ctx.new_path()
        ctx.move_to(0, 4)
        ctx.curve_to(-12, 14, -22, 22, -14, 26)
        ctx.curve_to(-6, 22, -2, 12, 0, 4)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # 2. Emerald Leaf Dress
        ctx.save()
        ctx.set_source_rgb(0.35, 0.82, 0.45)
        ctx.new_path()
        ctx.move_to(-8, -2)
        ctx.line_to(8, -2)
        ctx.curve_to(12, 10, 14, 18, 10, 22)
        ctx.line_to(-10, 22)
        ctx.curve_to(-14, 18, -12, 10, -8, -2)
        ctx.close_path()
        ctx.fill()

        # Petal hemline
        ctx.set_source_rgb(0.95, 0.55, 0.75)
        ctx.arc(0, 22, 3, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # 3. Head, Hair & Flower Crown
        ctx.save()
        # Skin
        ctx.set_source_rgb(0.98, 0.86, 0.78)
        ctx.arc(0, -11, 8.5, 0, math.pi * 2)
        ctx.fill()

        # Golden Blonde Hair
        ctx.set_source_rgb(0.98, 0.82, 0.25)
        ctx.new_path()
        ctx.arc(0, -12, 9.5, math.pi * 0.8, math.pi * 2.2)
        ctx.curve_to(-10, -8, -8, 6, -6, 12)  # Flowing braid
        ctx.close_path()
        ctx.fill()

        # Flower Crown (Blossoms)
        ctx.set_source_rgb(1.0, 0.4, 0.6)
        ctx.arc(-4, -18, 2.2, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgb(0.4, 0.9, 1.0)
        ctx.arc(1, -19, 2.2, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgb(1.0, 0.85, 0.3)
        ctx.arc(5, -17, 2.2, 0, math.pi * 2)
        ctx.fill()

        # Sparkling emerald eyes
        ctx.set_source_rgb(0.2, 0.75, 0.4)
        ctx.arc(3, -11, 1.6, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # 4. Tiny Wand with Star Tip
        ctx.save()
        ctx.set_source_rgb(0.9, 0.8, 0.5)
        ctx.set_line_width(1.5)
        ctx.move_to(8, 2)
        ctx.line_to(18, -10)
        ctx.stroke()
        # Star tip
        ctx.set_source_rgb(1.0, 0.88, 0.2)
        ctx.arc(18, -10, 3.2, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        ctx.restore()
