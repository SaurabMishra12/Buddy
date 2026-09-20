"""Ghost desktop companion: ethereal floating, spectral fade, and cute spooks."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from behavior.personality import CharacterPersonality
from behavior.memory import CharacterMemory
from behavior.state_machine import CharacterBehavior, BehaviorState


class GhostCharacter(BaseCharacter):
    """Playful cute spectral phantom companion with rippling hem and spooky bursts."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="ghost")
        self.can_fly = True
        self.is_airborne = True
        self.personality = CharacterPersonality(energy=0.70, curiosity=0.85, playfulness=0.95, sleepiness=0.30)
        self.memory = CharacterMemory(skin_id="ghost")
        self.behavior = CharacterBehavior("Ghost", personality=self.personality, memory=self.memory, can_fly=True)

        self.spectral_opacity = 0.85
        self.wave_time = 0.0
        self.hover_y = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("spectral_fade", "phase_shift", "fade"):
            self.spectral_opacity = 0.3
            particle_mgr.shockwave(self.x, self.y, max_radius=60.0, color=(0.8, 0.9, 1.0))
            audio_mgr.play("swoosh")
            self.memory.record_interaction("spectral_fade")
            return True

        elif ability_name in ("spook_burst", "spook"):
            particle_mgr.burst_stars(self.x, self.y, count=10, color=(0.7, 0.85, 1.0))
            particle_mgr.burst_hearts(self.x, self.y - 15, count=2)
            particle_mgr.shockwave(self.x, self.y, max_radius=70.0, color=(0.9, 0.95, 1.0))
            audio_mgr.play("magic")
            self.memory.record_interaction("spook_burst")
            return True

        elif ability_name == "ethereal_float":
            self.vy = -7.0
            particle_mgr.burst_stars(self.x, self.y + 16, count=4, color=(0.6, 0.9, 1.0))
            audio_mgr.play("swoosh")
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
        self.anim_time += dt * 3.5
        self.wave_time += dt * 6.0
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)

        # Restore opacity
        if self.spectral_opacity < 0.85:
            self.spectral_opacity = min(0.85, self.spectral_opacity + dt * 0.5)

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

        self.hover_y = math.sin(self.anim_time) * 6.0

        if self.state in (BehaviorState.FLY, BehaviorState.WALK):
            tx, ty = self.behavior.target_x, self.behavior.target_y
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            if dist > 14.0:
                self.vx += ((dx / dist) * 4.2 - self.vx) * 0.1
                self.vy += ((dy / dist) * 4.2 - self.vy) * 0.1
            else:
                self.vx *= 0.85
                self.vy *= 0.85
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.82
            self.vy *= 0.82

        self.x += self.vx
        self.y += self.vy

        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 70.0, self.y))

        # Ambient floating sparkles
        if random.random() < 0.2:
            particle_mgr.burst_stars(self.x, self.y + 12, count=1, size=3.0, color=(0.8, 0.9, 1.0))

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        ctx.save()
        ctx.translate(self.x, self.y + self.hover_y)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Ethereal Cyan Aura Glow
        ctx.save()
        ctx.set_source_rgba(0.6, 0.9, 1.0, self.spectral_opacity * 0.25)
        ctx.arc(0, 0, 24, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # 2. Flowing Ghost Body with Wavy Hem
        ctx.save()
        ctx.set_source_rgba(0.96, 0.98, 1.0, self.spectral_opacity)

        w1 = math.sin(self.wave_time) * 3.0
        w2 = math.sin(self.wave_time + 1.2) * 3.0
        w3 = math.sin(self.wave_time + 2.4) * 3.0

        ctx.new_path()
        # Rounded dome head
        ctx.arc(0, -8, 16, math.pi, 0)
        # Right drape
        ctx.curve_to(18, 4, 16, 14, 18, 22)
        # Wavy bottom tail folds
        ctx.curve_to(14, 18 + w1, 8, 24 + w1, 4, 20 + w1)
        ctx.curve_to(0, 18 + w2, -4, 24 + w2, -8, 20 + w2)
        ctx.curve_to(-12, 18 + w3, -16, 24 + w3, -18, 22)
        # Left drape
        ctx.curve_to(-16, 14, -18, 4, -16, -8)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # 3. Adorable Eyes and Blush
        ctx.save()
        # Large cute eyes
        ctx.set_source_rgba(0.12, 0.15, 0.2, self.spectral_opacity)
        ctx.arc(-4, -6, 2.8, 0, math.pi * 2)
        ctx.fill()
        ctx.arc(4, -6, 2.8, 0, math.pi * 2)
        ctx.fill()

        # White eye highlights
        ctx.set_source_rgba(1.0, 1.0, 1.0, self.spectral_opacity)
        ctx.arc(-5, -7, 1.0, 0, math.pi * 2)
        ctx.fill()
        ctx.arc(3, -7, 1.0, 0, math.pi * 2)
        ctx.fill()

        # Rosy blushing cheeks
        ctx.set_source_rgba(1.0, 0.5, 0.65, self.spectral_opacity * 0.5)
        ctx.arc(-8, -2, 2.5, 0, math.pi * 2)
        ctx.fill()
        ctx.arc(8, -2, 2.5, 0, math.pi * 2)
        ctx.fill()

        # Cute mouth
        ctx.set_source_rgba(0.12, 0.15, 0.2, self.spectral_opacity)
        ctx.arc(0, -2, 1.8, 0, math.pi)
        ctx.fill()
        ctx.restore()

        ctx.restore()
