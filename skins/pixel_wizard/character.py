"""Pixel Wizard desktop companion: floating royal violet robes, staff with pulsing crystal,
3D orbiting celestial orb with depth occlusion, expanding runic spell circles, and arcane portals.
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


class PixelWizardCharacter(BaseCharacter):
    """Wise arcane sorcerer companion with ethereal levitation,
    3D orbiting cosmic orb, runic circles, and celestial teleports.
    """

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="pixel_wizard")
        self.can_fly = True
        self.is_airborne = True
        self.personality = CharacterPersonality(energy=0.72, curiosity=0.95, playfulness=0.60, sleepiness=0.35)
        self.memory = CharacterMemory(skin_id="pixel_wizard")
        self.behavior = CharacterBehavior("Pixel Wizard", personality=self.personality, memory=self.memory, can_fly=True)

        self.orb_angle = 0.0
        self.spell_circle_alpha = 0.0
        self.spell_circle_rot = 0.0
        self.hover_y = 0.0
        self.mystic_missiles: List[Dict[str, Any]] = []

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("magic_orb", "spell_circle", "spell"):
            self.spell_circle_alpha = 1.0
            # Launch an arcane mystic missile toward target
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            dir_mult = 1.0 if self.facing_right else -1.0
            self.mystic_missiles.append({
                "x": self.x + dir_mult * 18.0,
                "y": self.y - 12.0,
                "vx": (dx / dist) * 16.0,
                "vy": (dy / dist) * 16.0,
                "rot": 0.0,
                "life": 1.4
            })
            particle_mgr.burst_energy_orbs(self.x, self.y, count=6, color=(0.75, 0.35, 1.0))
            audio_mgr.play("magic")
            self.memory.record_interaction("magic_orb")
            return True

        elif ability_name in ("teleport", "astral_teleport"):
            particle_mgr.shockwave(self.x, self.y, max_radius=60.0, color=(0.8, 0.3, 1.0))
            for _ in range(8):
                particle_mgr.burst_stars(self.x, self.y, count=2, color=(0.85, 0.4, 1.0))
            self.x = target_x
            self.y = target_y
            particle_mgr.shockwave(self.x, self.y, max_radius=75.0, color=(0.8, 0.3, 1.0))
            audio_mgr.play("magic")
            self.memory.record_interaction("teleport")
            return True

        elif ability_name in ("meditate", "celebrate"):
            self.spell_circle_alpha = 1.0
            particle_mgr.burst_stars(self.x, self.y - 20, count=12, color=(0.9, 0.45, 1.0))
            audio_mgr.play("sparkle")
            self.memory.record_interaction("meditate")
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
        self.orb_angle += dt * 2.8
        self.spell_circle_rot += dt * 1.5
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)
        speed_mult = config_data.get("speed", 1.0)

        # Decay spell circle
        if self.spell_circle_alpha > 0.0:
            self.spell_circle_alpha = max(0.0, self.spell_circle_alpha - dt * 0.7)

        # Look direction
        if abs(cursor_x - self.x) > 6.0:
            self.facing_right = (cursor_x >= self.x)

        # Update flying mystic missiles
        for ms in self.mystic_missiles:
            ms["x"] += ms["vx"]
            ms["y"] += ms["vy"]
            ms["rot"] += dt * 20.0
            ms["life"] -= dt
            if random.random() < 0.35:
                particle_mgr.burst_stars(ms["x"], ms["y"], count=1, size=3.0, color=(0.85, 0.4, 1.0))
        self.mystic_missiles = [ms for ms in self.mystic_missiles if ms["life"] > 0]

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

        # Ethereal floating hover (anchored, no uncompensated drift!)
        self.hover_y = math.sin(self.anim_time * 1.8) * 5.0

        dx = cursor_x - self.x
        dy = cursor_y - self.y
        dist = math.hypot(dx, dy)

        if dist > 50.0 and config_data.get("cursor_follow", True):
            fly_spd = min(8.0 * speed_mult, max(2.5, dist * 0.055))
            self.vx += ((dx / dist) * fly_spd - self.vx) * 0.16
            self.vy += ((dy / dist) * fly_spd - self.vy) * 0.16
            self.state = CharacterState.FLY
        elif self.state in (BehaviorState.FLY, BehaviorState.WALK):
            tx, ty = self.behavior.target_x, self.behavior.target_y
            tdx = tx - self.x
            tdy = ty - self.y
            tdist = math.hypot(tdx, tdy)
            if tdist > 15.0:
                spd = 6.2 * speed_mult
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

        # Banking tilt
        target_tilt = (self.vx / 14.0) * 0.18
        self.tilt += (target_tilt - self.tilt) * 0.20

        # Ambient celestial star particles
        if random.random() < 0.25:
            particle_mgr.burst_stars(
                self.x + random.uniform(-6, 6),
                self.y + 12,
                count=1,
                size=3.0,
                color=(0.85, 0.45, 1.0)
            )

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        # Draw active flying missiles
        for ms in self.mystic_missiles:
            ctx.save()
            ctx.translate(ms["x"], ms["y"])
            ctx.rotate(ms["rot"])
            # Glowing celestial orb
            pat_ms = cairo.RadialGradient(0, 0, 1, 0, 0, 7)
            pat_ms.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 1.0)
            pat_ms.add_color_stop_rgba(0.5, 0.8, 0.35, 1.0, 0.9)
            pat_ms.add_color_stop_rgba(1.0, 0.5, 0.1, 0.9, 0.0)
            ctx.set_source(pat_ms)
            ctx.arc(0, 0, 7, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

        # 3D Orbiting Orb coordinates with depth
        orb_x = math.cos(self.orb_angle) * 26.0
        orb_y = math.sin(self.orb_angle) * 8.5
        orb_in_back = math.sin(self.orb_angle) < 0.0

        ctx.save()
        ctx.translate(self.x, self.y + self.hover_y)
        ctx.rotate(self.tilt)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # -------------------------------------------------------------
        # 1. Glowing Runic Spell Circle on Ground/Air
        # -------------------------------------------------------------
        if self.spell_circle_alpha > 0.05:
            ctx.save()
            ctx.translate(0, 24)
            ctx.scale(1.0, 0.32)
            ctx.rotate(self.spell_circle_rot)
            # Outer runic circle
            ctx.set_source_rgba(0.85, 0.35, 1.0, self.spell_circle_alpha * 0.75)
            ctx.set_line_width(2.0)
            ctx.arc(0, 0, 34, 0, math.pi * 2)
            ctx.stroke()
            # Inner circle with cross-quadrants
            ctx.arc(0, 0, 22, 0, math.pi * 2)
            ctx.stroke()
            for a in (0.0, math.pi * 0.5, math.pi, math.pi * 1.5):
                ctx.move_to(math.cos(a) * 14, math.sin(a) * 14)
                ctx.line_to(math.cos(a) * 34, math.sin(a) * 34)
                ctx.stroke()
            ctx.restore()

        # -------------------------------------------------------------
        # 2. Draw Orbiting Mystic Orb (WHEN IN BACKGROUND)
        # -------------------------------------------------------------
        if orb_in_back:
            self._draw_mystic_orb(ctx, orb_x, orb_y)

        # -------------------------------------------------------------
        # 3. Flowing Royal Violet Wizard Robes
        # -------------------------------------------------------------
        robe_wave = math.sin(self.anim_time * 2.5) * 3.0
        robe_wind = -self.vx * 0.8

        ctx.save()
        # Deep royal purple base
        ctx.set_source_rgb(0.24, 0.12, 0.44)
        ctx.new_path()
        ctx.move_to(-12, -8)
        ctx.line_to(12, -8)
        ctx.curve_to(16, 6, 18 + robe_wind * 0.5, 16, 14 + robe_wind, 20 + robe_wave)
        ctx.curve_to(0, 22, -10, 22, -16 + robe_wind, 20 - robe_wave)
        ctx.curve_to(-18 + robe_wind * 0.5, 12, -14, 0, -12, -8)
        ctx.close_path()
        ctx.fill()

        # Golden Runic Hem Embroidery
        ctx.set_source_rgb(1.0, 0.85, 0.25)
        ctx.set_line_width(1.8)
        ctx.new_path()
        ctx.move_to(-16 + robe_wind, 20 - robe_wave)
        ctx.curve_to(-10, 22, 0, 22, 14 + robe_wind, 20 + robe_wave)
        ctx.stroke()

        # Golden sash belt
        ctx.rectangle(-10, 5, 20, 3.2)
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 4. Carved Wooden Wizard Staff with Pulsing Crystal
        # -------------------------------------------------------------
        ctx.save()
        # Wooden staff shaft
        ctx.set_source_rgb(0.38, 0.22, 0.12)
        ctx.set_line_width(3.2)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(12, 18)
        ctx.line_to(14, -20)
        ctx.stroke()

        # Staff headpiece prongs
        ctx.set_source_rgb(0.95, 0.8, 0.25)  # Gold mounting
        ctx.set_line_width(2.0)
        ctx.arc(14, -22, 4.0, math.pi * 0.5, math.pi * 2.5)
        ctx.stroke()

        # Pulsing Arcane Crystal on Staff Top
        crystal_glow = 0.7 + 0.3 * math.sin(self.anim_time * 4.0)
        pat_cryst = cairo.RadialGradient(14, -26, 1, 14, -26, 7)
        pat_cryst.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, crystal_glow)
        pat_cryst.add_color_stop_rgba(0.5, 0.85, 0.4, 1.0, crystal_glow * 0.85)
        pat_cryst.add_color_stop_rgba(1.0, 0.5, 0.1, 0.8, 0.0)
        ctx.set_source(pat_cryst)
        ctx.arc(14, -26, 7, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 5. Head, Flowing White Beard & Pointed Wizard Hat
        # -------------------------------------------------------------
        ctx.save()
        # Head (face)
        ctx.set_source_rgb(0.95, 0.82, 0.72)
        ctx.arc(0, -12, 9, 0, math.pi * 2)
        ctx.fill()

        # Kind wise eyes
        ctx.set_source_rgb(0.12, 0.1, 0.15)
        ctx.arc(3.5, -13, 1.6, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(4.0, -13.5, 0.6, 0, math.pi * 2)
        ctx.fill()

        # Majestic flowing white wizard beard
        beard_s = math.sin(self.anim_time * 2.0) * 2.0
        ctx.set_source_rgb(0.96, 0.96, 0.98)
        ctx.new_path()
        ctx.move_to(-7, -8)
        ctx.curve_to(-8, 2, -4, 14 + beard_s, 0, 16 + beard_s)
        ctx.curve_to(4, 14 + beard_s, 8, 2, 7, -8)
        ctx.close_path()
        ctx.fill()

        # Pointed Royal Violet Wizard Hat
        hat_tilt = math.sin(self.anim_time * 1.5) * 0.08
        ctx.save()
        ctx.translate(0, -16)
        ctx.rotate(hat_tilt)

        # Hat brim
        ctx.set_source_rgb(0.18, 0.08, 0.35)
        ctx.save()
        ctx.scale(1.4, 0.4)
        ctx.arc(0, 0, 14, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # Hat cone (crooked wizard tip)
        ctx.new_path()
        ctx.move_to(-12, 0)
        ctx.curve_to(-10, -14, -8, -26, -4, -34)
        ctx.curve_to(0, -32, 6, -18, 12, 0)
        ctx.close_path()
        ctx.fill()

        # Gold star emblem on hat band
        ctx.set_source_rgb(1.0, 0.85, 0.25)
        ctx.rectangle(-11, -3, 22, 2.8)
        ctx.fill()
        ctx.arc(0, -1.5, 2.5, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()
        ctx.restore()

        # -------------------------------------------------------------
        # 6. Draw Orbiting Mystic Orb (WHEN IN FOREGROUND)
        # -------------------------------------------------------------
        if not orb_in_back:
            self._draw_mystic_orb(ctx, orb_x, orb_y)

        ctx.restore()

    def _draw_mystic_orb(self, ctx: cairo.Context, ox: float, oy: float) -> None:
        """Draws the glowing celestial mystic orb with radial gradient optics."""
        ctx.save()
        ctx.translate(ox, oy)
        pat = cairo.RadialGradient(0, 0, 1, 0, 0, 8.5)
        pat.add_color_stop_rgba(0.0, 1.0, 1.0, 1.0, 1.0)
        pat.add_color_stop_rgba(0.4, 0.85, 0.4, 1.0, 0.95)
        pat.add_color_stop_rgba(0.8, 0.5, 0.15, 0.9, 0.6)
        pat.add_color_stop_rgba(1.0, 0.3, 0.05, 0.6, 0.0)
        ctx.set_source(pat)
        ctx.arc(0, 0, 8.5, 0, math.pi * 2)
        ctx.fill()
        # Internal star twinkle
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(0, 0, 1.8, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()
