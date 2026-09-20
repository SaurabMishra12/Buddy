"""Alien desktop companion: UFO saucer flight, banking tilt, rotating neon strobes,
reactive green alien pilot, volumetric tractor abduction beam, and plasma torpedoes.
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


class AlienCharacter(BaseCharacter):
    """Extraterrestrial companion riding a glowing high-tech UFO flying saucer
    with realistic banking flight, rotating neon rim strobes, reactive pilot,
    pulsing warp core, and volumetric tractor abduction beam.
    """

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="alien")
        self.can_fly = True
        self.is_airborne = True
        self.personality = CharacterPersonality(energy=0.82, curiosity=0.96, playfulness=0.68, sleepiness=0.18)
        self.memory = CharacterMemory(skin_id="alien")
        self.behavior = CharacterBehavior("Alien", personality=self.personality, memory=self.memory, can_fly=True)

        self.beam_active = False
        self.beam_timer = 0.0
        self.saucer_wobble = 0.0
        self.light_phase = 0.0
        self.warp_pulse = 0.0
        self.antenna_flex = 0.0
        self.look_offset_x = 0.0
        self.look_offset_y = 0.0
        self.plasma_torpedoes: List[Dict[str, Any]] = []

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("ufo_beam", "tractor_beam", "abduction"):
            self.beam_active = True
            self.beam_timer = time.time() + 2.2
            particle_mgr.shockwave(self.x, self.y + 22, max_radius=75.0, color=(0.25, 1.0, 0.45))
            particle_mgr.energy_orbs(self.x, self.y + 15, count=4, color=(0.2, 0.95, 0.6))
            audio_mgr.play("laser")
            self.memory.record_interaction("ufo_beam")
            return True

        elif ability_name in ("plasma_blaster", "alien_glow", "antigravity_pulse", "plasma"):
            # Launch 2 glowing emerald/cyan plasma torpedoes toward target
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            dir_mult = 1.0 if self.facing_right else -1.0

            for spread in (-0.18, 0.18):
                cos_s = math.cos(spread)
                sin_s = math.sin(spread)
                vx = (dx / dist) * 16.0
                vy = (dy / dist) * 16.0
                svx = vx * cos_s - vy * sin_s
                svy = vx * sin_s + vy * cos_s
                self.plasma_torpedoes.append({
                    "x": self.x + dir_mult * 16.0,
                    "y": self.y + 6.0,
                    "vx": svx,
                    "vy": svy,
                    "life": 1.4,
                    "phase": random.uniform(0, math.pi * 2)
                })

            particle_mgr.shockwave(self.x, self.y, max_radius=60.0, color=(0.2, 0.95, 0.65))
            audio_mgr.play("laser")
            self.memory.record_interaction("plasma_blaster")
            return True

        elif ability_name in ("cosmic_teleport", "teleport", "warp"):
            particle_mgr.cosmic_burst(self.x, self.y, count=16)
            particle_mgr.shockwave(self.x, self.y, max_radius=65.0, color=(0.4, 0.9, 0.6))
            self.x = target_x
            self.y = target_y
            particle_mgr.shockwave(self.x, self.y, max_radius=75.0, color=(0.3, 1.0, 0.7))
            particle_mgr.burst_stars(self.x, self.y, count=10, color=(0.5, 1.0, 0.8))
            audio_mgr.play("teleport")
            self.memory.record_interaction("cosmic_teleport")
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
        self.light_phase += dt * 5.5
        self.warp_pulse += dt * 8.0
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)
        speed_mult = config_data.get("speed", 1.0)

        # Beam timer
        if now > self.beam_timer:
            self.beam_active = False

        # Facing direction
        if abs(cursor_x - self.x) > 6.0:
            self.facing_right = (cursor_x >= self.x)

        # Eye tracking offsets inside cockpit
        dx_eye = cursor_x - self.x
        dy_eye = cursor_y - self.y
        dist_eye = math.hypot(dx_eye, dy_eye) + 1e-4
        target_lx = (dx_eye / dist_eye) * 2.2
        target_ly = (dy_eye / dist_eye) * 1.8
        self.look_offset_x += (target_lx - self.look_offset_x) * 0.25
        self.look_offset_y += (target_ly - self.look_offset_y) * 0.25

        # Antenna inertial flex based on horizontal movement
        target_antenna = -self.vx * 0.08
        self.antenna_flex += (target_antenna - self.antenna_flex) * 0.20

        # Update active plasma torpedoes
        for torp in self.plasma_torpedoes:
            torp["x"] += torp["vx"]
            torp["y"] += torp["vy"]
            torp["phase"] += dt * 14.0
            torp["life"] -= dt
            if random.random() < 0.35:
                particle_mgr.burst_stars(torp["x"], torp["y"], count=1, size=3.0, color=(0.3, 1.0, 0.7))
        self.plasma_torpedoes = [t for t in self.plasma_torpedoes if t["life"] > 0]

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

        # Hover wobble with harmonic frequencies
        self.saucer_wobble = (
            math.sin(self.anim_time * 1.8) * 4.5 +
            math.cos(self.anim_time * 3.2) * 1.5
        )

        # Locomotion & cursor chase
        dx = cursor_x - self.x
        dy = cursor_y - self.y
        dist = math.hypot(dx, dy)

        if dist > 55.0 and config_data.get("cursor_follow", True):
            fly_spd = min(10.5 * speed_mult, max(3.5, dist * 0.065))
            self.vx += ((dx / dist) * fly_spd - self.vx) * 0.18
            self.vy += ((dy / dist) * fly_spd - self.vy) * 0.18
            self.state = CharacterState.FLY
        elif self.state in (BehaviorState.FLY, BehaviorState.WALK):
            tx, ty = self.behavior.target_x, self.behavior.target_y
            tdx = tx - self.x
            tdy = ty - self.y
            tdist = math.hypot(tdx, tdy)
            if tdist > 16.0:
                spd = 6.2 * speed_mult
                self.vx += ((tdx / tdist) * spd - self.vx) * 0.15
                self.vy += ((tdy / tdist) * spd - self.vy) * 0.15
            else:
                self.vx *= 0.82
                self.vy *= 0.82
                self.behavior.transition_to(BehaviorState.IDLE)
        else:
            self.vx *= 0.82
            self.vy *= 0.82

        self.x += self.vx
        self.y += self.vy

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 70.0, self.y))

        # Dynamic saucer banking tilt (banks into turn)
        target_tilt = (self.vx / 9.0) * 0.28
        self.tilt += (target_tilt - self.tilt) * 0.22

        # Ambient stardust / warp particles
        if random.random() < 0.25:
            particle_mgr.burst_stars(
                self.x + random.uniform(-10, 10),
                self.y + 14,
                count=1,
                size=3.5,
                color=(0.25, 1.0, 0.65)
            )

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        # Draw active plasma torpedoes first
        for torp in self.plasma_torpedoes:
            ctx.save()
            ctx.translate(torp["x"], torp["y"])
            # Outer plasma orb glow
            ctx.set_source_rgba(0.2, 1.0, 0.5, 0.45)
            ctx.arc(0, 0, 8.5, 0, math.pi * 2)
            ctx.fill()
            # Dense core
            ctx.set_source_rgba(0.85, 1.0, 0.9, 0.95)
            ctx.arc(0, 0, 4.0, 0, math.pi * 2)
            ctx.fill()
            # Spinning energy rings
            ctx.set_source_rgba(0.3, 1.0, 0.7, 0.7)
            ctx.set_line_width(1.5)
            ctx.rotate(torp["phase"])
            ctx.save()
            ctx.scale(1.0, 0.4)
            ctx.arc(0, 0, 7.0, 0, math.pi * 2)
            ctx.stroke()
            ctx.restore()
            ctx.restore()

        ctx.save()
        ctx.translate(self.x, self.y + self.saucer_wobble)
        ctx.rotate(self.tilt)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # -----------------------------------------------------------------
        # 1. Volumetric Tractor Abduction Beam
        # -----------------------------------------------------------------
        if self.beam_active:
            ctx.save()
            # Volumetric cone gradient
            beam_grad = cairo.LinearGradient(0, 10, 0, 85)
            beam_grad.add_color_stop_rgba(0.0, 0.25, 1.0, 0.55, 0.65)
            beam_grad.add_color_stop_rgba(0.6, 0.15, 0.95, 0.45, 0.35)
            beam_grad.add_color_stop_rgba(1.0, 0.10, 0.85, 0.40, 0.10)
            ctx.set_source(beam_grad)

            ctx.new_path()
            ctx.move_to(-12, 10)
            ctx.line_to(12, 10)
            ctx.line_to(48, 85)
            ctx.line_to(-48, 85)
            ctx.close_path()
            ctx.fill()

            # Pulsing descending tractor beam rings
            for r_idx in range(4):
                phase_ring = (self.anim_time * 2.5 + r_idx * 1.5) % 4.0
                ring_y = 12.0 + phase_ring * 18.0
                ring_rx = 12.0 + phase_ring * 9.0
                ring_alpha = max(0.0, 1.0 - (phase_ring / 4.0)) * 0.75

                ctx.save()
                ctx.translate(0, ring_y)
                ctx.scale(1.0, 0.28)
                ctx.set_source_rgba(0.4, 1.0, 0.7, ring_alpha)
                ctx.set_line_width(2.0)
                ctx.arc(0, 0, ring_rx, 0, math.pi * 2)
                ctx.stroke()
                ctx.restore()

            # Desktop ground impact ripple
            ctx.save()
            ctx.translate(0, 85)
            ctx.scale(1.0, 0.25)
            ctx.set_source_rgba(0.3, 1.0, 0.6, 0.55)
            ctx.arc(0, 0, 48, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

            ctx.restore()

        # -----------------------------------------------------------------
        # 2. Glowing Cockpit Dome & Animated Alien Pilot
        # -----------------------------------------------------------------
        ctx.save()

        # A. Alien Pilot Body & Head
        # Torso (deep purple space suit)
        ctx.new_path()
        ctx.set_source_rgb(0.32, 0.20, 0.48)
        ctx.arc(0, -2, 7.5, 0, math.pi)
        ctx.close_path()
        ctx.fill()

        # Alien Head (Organic lime green)
        head_y = -9.0 + math.sin(self.anim_time * 1.5) * 0.8
        ctx.new_path()
        ctx.set_source_rgb(0.38, 0.92, 0.42)
        ctx.new_path()
        # Inverted pear shape head
        ctx.save()
        ctx.translate(0, head_y)
        ctx.scale(1.0, 1.15)
        ctx.arc(0, 0, 9.0, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # B. Expressive Antennae with Inertial Flex
        for ant_x, ant_dir in ((-4.5, -1.0), (4.5, 1.0)):
            ctx.save()
            ctx.set_source_rgb(0.32, 0.84, 0.36)
            ctx.set_line_width(1.8)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.new_path()
            ctx.move_to(ant_x, head_y - 8.0)
            bend_x = ant_x + ant_dir * 3.5 + self.antenna_flex
            bend_y = head_y - 17.0
            tip_x = ant_x + ant_dir * 6.0 + self.antenna_flex * 1.4
            tip_y = head_y - 21.0
            ctx.curve_to(bend_x, bend_y + 4.0, bend_x, bend_y, tip_x, tip_y)
            ctx.stroke()

            # Glowing antenna tip sphere
            tip_pulse = 0.7 + 0.3 * math.sin(self.warp_pulse + ant_dir)
            ctx.set_source_rgba(0.4, 1.0, 0.6, tip_pulse)
            ctx.arc(tip_x, tip_y, 3.2, 0, math.pi * 2)
            ctx.fill()
            ctx.set_source_rgb(0.9, 1.0, 0.95)
            ctx.arc(tip_x, tip_y, 1.4, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

        # C. Big Glossy Obsidian Alien Eyes (Tracking Cursor)
        for eye_x in (-4.2, 4.2):
            ctx.save()
            ctx.translate(eye_x, head_y - 0.5)
            # Tilt eyes outward slightly
            eye_tilt = 0.22 if eye_x > 0 else -0.22
            ctx.rotate(eye_tilt)
            ctx.scale(0.85, 1.35)

            # Black glossy cornea
            ctx.set_source_rgb(0.05, 0.08, 0.10)
            ctx.arc(0, 0, 3.8, 0, math.pi * 2)
            ctx.fill()

            # Pupil/Iris tracking cursor
            ctx.set_source_rgba(0.2, 0.85, 0.4, 0.65)
            ctx.arc(self.look_offset_x * 0.4, self.look_offset_y * 0.4, 1.8, 0, math.pi * 2)
            ctx.fill()

            # White specular reflection highlight
            ctx.set_source_rgb(1.0, 1.0, 1.0)
            ctx.arc(1.2, -1.2, 1.2, 0, math.pi * 2)
            ctx.fill()
            ctx.arc(-1.0, 1.0, 0.6, 0, math.pi * 2)
            ctx.fill()
            ctx.restore()

        # Cute small smile
        ctx.save()
        ctx.set_source_rgb(0.18, 0.55, 0.22)
        ctx.set_line_width(1.2)
        ctx.arc(0, head_y + 4.5, 2.5, 0.2, math.pi - 0.2)
        ctx.stroke()
        ctx.restore()

        # Cute waving hand inside glass dome
        ctx.save()
        wave_angle = math.sin(self.anim_time * 3.5) * 0.35
        ctx.translate(7.5, head_y + 3.0)
        ctx.rotate(wave_angle)
        ctx.set_source_rgb(0.38, 0.92, 0.42)
        ctx.arc(0, 0, 2.2, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # D. Glass Cockpit Dome Shell (Cyan Glass with Specular Glint)
        dome_grad = cairo.RadialGradient(0, -10, 4, 0, -5, 20)
        dome_grad.add_color_stop_rgba(0.0, 0.75, 0.95, 1.0, 0.55)
        dome_grad.add_color_stop_rgba(0.7, 0.40, 0.80, 0.95, 0.35)
        dome_grad.add_color_stop_rgba(1.0, 0.20, 0.60, 0.85, 0.25)
        ctx.set_source(dome_grad)

        ctx.new_path()
        ctx.arc(0, -3.5, 17.5, math.pi, 0)
        ctx.close_path()
        ctx.fill()

        # Specular glass arc highlight
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.85)
        ctx.set_line_width(1.6)
        ctx.new_path()
        ctx.arc(0, -3.5, 16.5, math.pi * 1.15, math.pi * 1.55)
        ctx.stroke()

        ctx.restore()

        # -----------------------------------------------------------------
        # 3. High-Tech Metallic Saucer Hull
        # -----------------------------------------------------------------
        ctx.save()

        # A. Saucer Upper Disc (Brushed Titanium Gradient)
        upper_grad = cairo.LinearGradient(-36, -4, 36, 10)
        upper_grad.add_color_stop_rgb(0.0, 0.88, 0.92, 0.96)  # Bright silver
        upper_grad.add_color_stop_rgb(0.4, 0.72, 0.78, 0.84)  # Metallic alloy
        upper_grad.add_color_stop_rgb(1.0, 0.48, 0.54, 0.62)  # Shaded rim
        ctx.set_source(upper_grad)

        ctx.save()
        ctx.translate(0, 3)
        ctx.scale(1.0, 0.36)
        ctx.new_path()
        ctx.arc(0, 0, 36, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # Upper hull rim line
        ctx.save()
        ctx.translate(0, 3)
        ctx.scale(1.0, 0.36)
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.7)
        ctx.set_line_width(1.4)
        ctx.new_path()
        ctx.arc(0, 0, 35.5, math.pi, math.pi * 2)
        ctx.stroke()
        ctx.restore()

        # B. Saucer Lower Hull (Dark Titanium Alloy)
        lower_grad = cairo.LinearGradient(0, 4, 0, 14)
        lower_grad.add_color_stop_rgb(0.0, 0.40, 0.44, 0.52)
        lower_grad.add_color_stop_rgb(1.0, 0.22, 0.25, 0.30)
        ctx.set_source(lower_grad)

        ctx.save()
        ctx.translate(0, 7)
        ctx.scale(1.0, 0.32)
        ctx.arc(0, 0, 28, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # C. Bottom Anti-Gravity Emitter Core (Pulsing Plasma Core)
        warp_intensity = 0.75 + 0.25 * math.sin(self.warp_pulse)
        core_grad = cairo.RadialGradient(0, 10, 1, 0, 10, 9)
        core_grad.add_color_stop_rgba(0.0, 0.9, 1.0, 0.95, warp_intensity)
        core_grad.add_color_stop_rgba(0.5, 0.2, 1.0, 0.55, warp_intensity * 0.8)
        core_grad.add_color_stop_rgba(1.0, 0.1, 0.8, 0.45, 0.0)
        ctx.set_source(core_grad)

        ctx.arc(0, 10.5, 8.5, 0, math.pi * 2)
        ctx.fill()

        # Emitter metallic nozzle ring
        ctx.set_source_rgb(0.55, 0.60, 0.68)
        ctx.set_line_width(1.5)
        ctx.arc(0, 10.5, 5.5, 0, math.pi * 2)
        ctx.stroke()

        # D. 8 Rotating Multi-Color LED Perimeter Strobes
        # Colors: Electric Cyan, Neon Lime, Solar Amber, Cosmic Magenta
        strobe_colors = [
            (0.2, 0.95, 1.0),   # Cyan
            (0.3, 1.0, 0.4),    # Lime
            (1.0, 0.85, 0.2),   # Amber
            (0.95, 0.3, 0.85),  # Magenta
            (0.2, 0.95, 1.0),   # Cyan
            (0.3, 1.0, 0.4),    # Lime
            (1.0, 0.85, 0.2),   # Amber
            (0.95, 0.3, 0.85),  # Magenta
        ]

        for i in range(8):
            angle = self.light_phase + (i * (math.pi / 4.0))
            light_x = math.cos(angle) * 31.0
            light_y = math.sin(angle) * 9.5 + 3.5

            # Perspective depth: lights in front are larger & brighter
            z_depth = math.sin(angle)
            light_alpha = 0.55 + 0.45 * max(0.0, z_depth)
            light_radius = 2.0 + 0.8 * max(0.0, z_depth)
            col = strobe_colors[i]

            # Halo glow
            ctx.set_source_rgba(col[0], col[1], col[2], light_alpha * 0.4)
            ctx.arc(light_x, light_y, light_radius * 2.0, 0, math.pi * 2)
            ctx.fill()

            # Glowing bulb core
            ctx.set_source_rgba(col[0], col[1], col[2], light_alpha)
            ctx.arc(light_x, light_y, light_radius, 0, math.pi * 2)
            ctx.fill()

            # White hot center
            ctx.set_source_rgba(1.0, 1.0, 1.0, light_alpha * 0.9)
            ctx.arc(light_x, light_y, light_radius * 0.4, 0, math.pi * 2)
            ctx.fill()

        ctx.restore()
        ctx.restore()
