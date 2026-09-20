"""Pixel Wizard desktop companion: arcane orbs, teleports, and astral floating."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from behavior.personality import CharacterPersonality
from behavior.memory import CharacterMemory
from behavior.state_machine import CharacterBehavior, BehaviorState


class PixelWizardCharacter(BaseCharacter):
    """Arcane wizard companion with staff, glowing crystal orb, and teleportation."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="pixel_wizard")
        self.can_fly = True
        self.is_airborne = True
        self.personality = CharacterPersonality(energy=0.65, curiosity=0.92, playfulness=0.55, sleepiness=0.35)
        self.memory = CharacterMemory(skin_id="pixel_wizard")
        self.behavior = CharacterBehavior("Pixel Wizard", personality=self.personality, memory=self.memory, can_fly=True)

        self.hover_offset = 0.0
        self.orb_angle = 0.0
        self.orb_distance = 26.0
        self.is_teleporting = False
        self.teleport_timer = 0.0
        self.spell_circle_alpha = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("magic_orb", "cast_spell"):
            particle_mgr.energy_orbs(self.x, self.y - 20, count=3, color=(0.7, 0.2, 1.0))
            particle_mgr.burst_stars(self.x, self.y, count=8, color=(0.85, 0.4, 1.0))
            audio_mgr.play("magic")
            self.memory.record_interaction("magic_orb")
            return True

        elif ability_name == "teleport":
            self.is_teleporting = True
            self.teleport_timer = time.time() + 0.4
            particle_mgr.shockwave(self.x, self.y, max_radius=60.0, color=(0.6, 0.1, 0.9))
            particle_mgr.burst_sparks(self.x, self.y, count=18, color=(0.8, 0.3, 1.0))
            self.x = target_x
            self.y = target_y
            particle_mgr.shockwave(self.x, self.y, max_radius=60.0, color=(0.3, 0.8, 1.0))
            audio_mgr.play("teleport")
            self.memory.record_interaction("teleport")
            return True

        elif ability_name == "spell_circle":
            self.spell_circle_alpha = 1.0
            particle_mgr.burst_stars(self.x, self.y, count=12, color=(1.0, 0.85, 0.2))
            audio_mgr.play("magic")
            self.memory.record_interaction("spell_circle")
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
        self.orb_angle += dt * 2.5
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)

        # Decay spell circle
        if self.spell_circle_alpha > 0.0:
            self.spell_circle_alpha = max(0.0, self.spell_circle_alpha - dt * 0.8)

        # Facing
        if abs(cursor_x - self.x) > 6.0:
            self.facing_right = (cursor_x >= self.x)

        # Autonomous behavior evaluation
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
        self.hover_offset = math.sin(self.anim_time) * 6.0

        if self.state in (BehaviorState.FLY, BehaviorState.WALK):
            tx, ty = self.behavior.target_x, self.behavior.target_y
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            if dist > 15.0:
                self.vx += ((dx / dist) * 4.5 - self.vx) * 0.1
                self.vy += ((dy / dist) * 4.5 - self.vy) * 0.1
            else:
                self.vx *= 0.85
                self.vy *= 0.85
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.82
            self.vy *= 0.82

        self.x += self.vx
        self.y += self.vy + math.sin(self.anim_time * 1.5) * 0.4

        # Bounds clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 70.0, self.y))

        # Ambient starlight trail
        if random.random() < 0.2:
            particle_mgr.burst_stars(self.x, self.y + 10, count=1, size=4.0)

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        ctx.save()
        ctx.translate(self.x, self.y + self.hover_offset)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Glowing spell circle on ground
        if self.spell_circle_alpha > 0.05:
            ctx.save()
            ctx.translate(0, 26)
            ctx.scale(1.0, 0.35)
            ctx.set_source_rgba(0.8, 0.3, 1.0, self.spell_circle_alpha * 0.6)
            ctx.set_line_width(2.0)
            ctx.arc(0, 0, 32, 0, math.pi * 2)
            ctx.stroke()
            ctx.arc(0, 0, 20, 0, math.pi * 2)
            ctx.stroke()
            ctx.restore()

        # 2. Flowing Wizard Robe (Deep Royal Violet)
        ctx.save()
        ctx.set_source_rgb(0.24, 0.12, 0.45)  # Dark purple robe
        ctx.new_path()
        ctx.move_to(-16, -6)
        ctx.curve_to(-20, 10, -22, 22, -18, 25)
        ctx.line_to(18, 25)
        ctx.curve_to(22, 22, 20, 10, 16, -6)
        ctx.close_path()
        ctx.fill()

        # Gold robe trim
        ctx.set_source_rgb(0.95, 0.8, 0.2)
        ctx.set_line_width(1.5)
        ctx.move_to(-18, 25)
        ctx.line_to(18, 25)
        ctx.stroke()
        ctx.move_to(0, -6)
        ctx.line_to(0, 25)
        ctx.stroke()
        ctx.restore()

        # 3. Wizard Head & Face
        ctx.save()
        ctx.set_source_rgb(0.98, 0.85, 0.75)  # Skin
        ctx.arc(0, -12, 10, 0, math.pi * 2)
        ctx.fill()

        # Big bushy white wizard beard
        ctx.set_source_rgb(0.95, 0.95, 0.98)
        ctx.new_path()
        ctx.move_to(-8, -10)
        ctx.curve_to(-10, 0, -6, 12, 0, 16)
        ctx.curve_to(6, 12, 10, 0, 8, -10)
        ctx.close_path()
        ctx.fill()

        # Kind eyes
        ctx.set_source_rgb(0.1, 0.1, 0.2)
        ctx.arc(3, -13, 1.6, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # 4. Pointy Wizard Hat
        ctx.save()
        ctx.translate(0, -16)
        # Hat brim
        ctx.set_source_rgb(0.18, 0.08, 0.38)
        ctx.save()
        ctx.scale(1.0, 0.4)
        ctx.arc(0, 0, 18, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # Hat cone
        ctx.new_path()
        ctx.move_to(-12, 0)
        ctx.curve_to(-8, -14, -6, -26, -10, -32)  # Curved tip
        ctx.curve_to(0, -22, 6, -12, 12, 0)
        ctx.close_path()
        ctx.fill()

        # Gold buckle band
        ctx.set_source_rgb(0.95, 0.8, 0.2)
        ctx.rectangle(-11, -3, 22, 3)
        ctx.fill()
        ctx.restore()

        # 5. Wooden Staff & Mystic Orb
        ctx.save()
        staff_x = 16
        ctx.set_source_rgb(0.42, 0.26, 0.15)  # Wood
        ctx.set_line_width(2.5)
        ctx.move_to(staff_x, -16)
        ctx.line_to(staff_x, 26)
        ctx.stroke()

        # Floating Arcane Orb on staff
        orb_y = -22 + math.sin(self.anim_time * 2.0) * 2.0
        # Outer glow
        ctx.set_source_rgba(0.7, 0.2, 1.0, 0.4)
        ctx.arc(staff_x, orb_y, 9, 0, math.pi * 2)
        ctx.fill()
        # Orb core
        ctx.set_source_rgba(0.9, 0.5, 1.0, 0.9)
        ctx.arc(staff_x, orb_y, 5, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(staff_x - 1, orb_y - 1, 1.8, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        ctx.restore()
