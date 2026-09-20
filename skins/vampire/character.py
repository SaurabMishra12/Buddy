"""Vampire desktop companion: aristocratic levitation, billowing two-tone Dracula cape,
wing-cape flight stance, glowing ruby eyes, animated bat swarms, and shadow glides.
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


class VampireCharacter(BaseCharacter):
    """Aristocratic gothic vampire companion with authentic levitation kinematics,
    billowing crimson-lined cape, wing-cape flight mode, and animated bat swarm summons.
    """

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="vampire")
        self.can_fly = True
        self.is_airborne = True
        self.personality = CharacterPersonality(energy=0.75, curiosity=0.68, playfulness=0.55, sleepiness=0.40)
        self.memory = CharacterMemory(skin_id="vampire")
        self.behavior = CharacterBehavior("Vampire", personality=self.personality, memory=self.memory, can_fly=True)

        self.cape_wave = 0.0
        self.hover_y = 0.0
        self.eye_pulse = 0.0
        self.bat_swarm: List[Dict[str, Any]] = []

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("bat_swarm", "bats", "summon_bats"):
            # Summon 7 real animated flying vampire bats with flapping wings!
            self.bat_swarm = []
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4

            for i in range(7):
                angle = (i / 7.0) * math.pi * 2.0
                spd = random.uniform(8.0, 14.0)
                bvx = math.cos(angle) * spd + (dx / dist) * 6.0
                bvy = math.sin(angle) * spd + (dy / dist) * 6.0
                self.bat_swarm.append({
                    "x": self.x + math.cos(angle) * 12.0,
                    "y": self.y + math.sin(angle) * 12.0,
                    "vx": bvx,
                    "vy": bvy,
                    "wing_phase": random.uniform(0, math.pi * 2),
                    "life": 1.6,
                    "scale": random.uniform(0.75, 1.15)
                })

            particle_mgr.shockwave(self.x, self.y, max_radius=65.0, color=(0.85, 0.08, 0.18))
            for _ in range(8):
                particle_mgr.burst_stars(
                    self.x + random.uniform(-15, 15),
                    self.y + random.uniform(-10, 10),
                    count=2,
                    color=(0.25, 0.05, 0.12)
                )
            audio_mgr.play("swoosh")
            self.memory.record_interaction("bat_swarm")
            return True

        elif ability_name in ("shadow_glide", "flight", "levitate", "glide"):
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.vx = (dx / dist) * 16.0
            self.vy = (dy / dist) * 16.0
            self.state = CharacterState.FLY
            particle_mgr.smoke_puff(self.x, self.y, count=4, color=(0.18, 0.06, 0.12))
            particle_mgr.burst_stars(self.x, self.y, count=6, color=(0.85, 0.10, 0.20))
            audio_mgr.play("swoosh")
            self.memory.record_interaction("shadow_glide")
            return True

        elif ability_name in ("mist_fade", "shadow_mist", "mist"):
            for _ in range(8):
                particle_mgr.smoke_puff(
                    self.x + random.uniform(-10, 10),
                    self.y + random.uniform(-10, 10),
                    count=2,
                    color=(0.22, 0.08, 0.18)
                )
            self.x = target_x
            self.y = target_y
            particle_mgr.shockwave(self.x, self.y, max_radius=60.0, color=(0.75, 0.08, 0.2))
            audio_mgr.play("swoosh")
            self.memory.record_interaction("mist_fade")
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
        self.cape_wave += dt * 6.5
        self.eye_pulse += dt * 7.0
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)
        speed_mult = config_data.get("speed", 1.0)

        # Facing direction
        if abs(cursor_x - self.x) > 6.0:
            self.facing_right = (cursor_x >= self.x)

        # Update animated flying bat swarm
        for bat in self.bat_swarm:
            bat["x"] += bat["vx"]
            bat["y"] += bat["vy"]
            bat["wing_phase"] += dt * 26.0  # Rapid bat wing flap
            bat["life"] -= dt
            # Bat flutter turbulence
            bat["vx"] += random.uniform(-1.2, 1.2)
            bat["vy"] += random.uniform(-0.8, 0.8)
            if random.random() < 0.25:
                particle_mgr.burst_stars(bat["x"], bat["y"], count=1, size=2.0, color=(0.85, 0.1, 0.2))
        self.bat_swarm = [b for b in self.bat_swarm if b["life"] > 0]

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

        # Aristocratic levitation hover
        self.hover_y = (
            math.sin(self.anim_time * 1.8) * 5.5 +
            math.cos(self.anim_time * 3.4) * 1.4
        )

        # Locomotion & cursor chase
        dx = cursor_x - self.x
        dy = cursor_y - self.y
        dist = math.hypot(dx, dy)

        if dist > 55.0 and config_data.get("cursor_follow", True):
            glide_spd = min(10.0 * speed_mult, max(3.5, dist * 0.065))
            self.vx += ((dx / dist) * glide_spd - self.vx) * 0.18
            self.vy += ((dy / dist) * glide_spd - self.vy) * 0.18
            self.state = CharacterState.FLY
        elif self.state in (BehaviorState.FLY, BehaviorState.WALK):
            tx, ty = self.behavior.target_x, self.behavior.target_y
            tdx = tx - self.x
            tdy = ty - self.y
            tdist = math.hypot(tdx, tdy)
            if tdist > 16.0:
                spd = 5.8 * speed_mult
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

        # Screen clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 70.0, self.y))

        # Dynamic levitation tilt
        target_tilt = (self.vx / 11.0) * 0.20
        self.tilt += (target_tilt - self.tilt) * 0.20

        # Ambient dark embers / crimson motes
        if random.random() < 0.2:
            particle_mgr.burst_stars(
                self.x + random.uniform(-12, 12),
                self.y + 14,
                count=1,
                size=2.8,
                color=(0.85, 0.12, 0.24)
            )

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        # Draw active flying bats first
        for bat in self.bat_swarm:
            ctx.save()
            ctx.translate(bat["x"], bat["y"])
            ctx.scale(bat["scale"], bat["scale"])
            # Face flight direction
            if bat["vx"] < 0:
                ctx.scale(-1.0, 1.0)

            # Flapping wing factor (-1.0 to 1.0)
            wing_y = math.sin(bat["wing_phase"]) * 6.0

            # Bat tiny body
            ctx.set_source_rgb(0.12, 0.08, 0.14)
            ctx.arc(0, 0, 2.8, 0, math.pi * 2)
            ctx.fill()

            # Glowing red bat eyes
            ctx.set_source_rgb(0.95, 0.15, 0.25)
            ctx.arc(1.5, -0.8, 0.7, 0, math.pi * 2)
            ctx.fill()

            # Pointed bat ears
            ctx.set_source_rgb(0.14, 0.09, 0.16)
            ctx.move_to(-1.0, -2.0)
            ctx.line_to(-0.5, -4.8)
            ctx.line_to(1.0, -2.0)
            ctx.close_path()
            ctx.fill()

            # Flapping bat wings with scalloped webbing
            ctx.set_source_rgb(0.15, 0.10, 0.18)
            # Right wing
            ctx.new_path()
            ctx.move_to(1.5, 0)
            ctx.line_to(11.0, -2.0 + wing_y)
            ctx.line_to(7.0, 3.0 + wing_y * 0.4)
            ctx.line_to(4.0, 1.5)
            ctx.close_path()
            ctx.fill()
            # Left wing
            ctx.new_path()
            ctx.move_to(-1.5, 0)
            ctx.line_to(-11.0, -2.0 + wing_y)
            ctx.line_to(-7.0, 3.0 + wing_y * 0.4)
            ctx.line_to(-4.0, 1.5)
            ctx.close_path()
            ctx.fill()

            ctx.restore()

        ctx.save()
        ctx.translate(self.x, self.y + self.hover_y)
        ctx.rotate(self.tilt)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        speed = math.hypot(self.vx, self.vy)
        is_gliding = speed > 2.5
        wave = math.sin(self.cape_wave) * 4.5
        cape_drag = -self.vx * 1.2

        # -------------------------------------------------------------
        # 1. Flowing Dracula Cape (Two-Tone Obsidian & Velvet Crimson)
        # -------------------------------------------------------------
        ctx.save()

        if is_gliding:
            # WING-CAPE FLIGHT MODE: Cape spreads out into majestic bat wings!
            # Outer midnight obsidian bat wing
            ctx.set_source_rgb(0.10, 0.08, 0.13)
            ctx.new_path()
            ctx.move_to(-8, -6)
            ctx.curve_to(-24, -14, -36, -8, -38 + cape_drag * 0.5, 12 + wave)
            ctx.line_to(-26 + cape_drag * 0.5, 20 + wave)
            ctx.line_to(-12, 14)
            ctx.line_to(12, 14)
            ctx.line_to(26 - cape_drag * 0.5, 20 + wave)
            ctx.line_to(38 - cape_drag * 0.5, 12 + wave)
            ctx.curve_to(36, -8, 24, -14, 8, -6)
            ctx.close_path()
            ctx.fill()

            # Inner velvet crimson lining highlight
            ctx.set_source_rgb(0.80, 0.08, 0.16)
            ctx.new_path()
            ctx.move_to(-6, -4)
            ctx.curve_to(-20, -10, -30, -4, -32 + cape_drag * 0.4, 10 + wave)
            ctx.line_to(-22 + cape_drag * 0.4, 16 + wave)
            ctx.line_to(-10, 12)
            ctx.line_to(10, 12)
            ctx.line_to(22 - cape_drag * 0.4, 16 + wave)
            ctx.line_to(32 - cape_drag * 0.4, 10 + wave)
            ctx.curve_to(30, -4, 20, -10, 6, -4)
            ctx.close_path()
            ctx.fill()

        else:
            # BILLOWING LEVITATION CAPE: Flowing behind aristocratic stance
            # Outer obsidian cape
            ctx.set_source_rgb(0.10, 0.08, 0.13)
            ctx.new_path()
            ctx.move_to(-10, -6)
            ctx.curve_to(-20, 8, -26 + cape_drag + wave, 24, -20 + cape_drag + wave, 32)
            ctx.line_to(18, 30)
            ctx.curve_to(14, 14, 8, -4, 4, -6)
            ctx.close_path()
            ctx.fill()

            # Inner velvet crimson silk lining
            ctx.set_source_rgb(0.80, 0.08, 0.16)
            ctx.new_path()
            ctx.move_to(-8, -4)
            ctx.curve_to(-16, 8, -20 + cape_drag + wave, 22, -14 + cape_drag + wave, 28)
            ctx.line_to(14, 26)
            ctx.curve_to(10, 12, 4, -2, 2, -4)
            ctx.close_path()
            ctx.fill()

        # Tall Pointed Dracula Collar (Standing upright around neck)
        collar_grad = cairo.LinearGradient(-18, -28, 18, -6)
        collar_grad.add_color_stop_rgb(0.0, 0.88, 0.09, 0.18)
        collar_grad.add_color_stop_rgb(1.0, 0.55, 0.05, 0.10)
        ctx.set_source(collar_grad)

        ctx.new_path()
        ctx.move_to(-14, -6)
        ctx.line_to(-19, -26)   # Tall pointed left peak
        ctx.line_to(-8, -15)
        ctx.line_to(0, -11)
        ctx.line_to(8, -15)
        ctx.line_to(19, -26)    # Tall pointed right peak
        ctx.line_to(14, -6)
        ctx.close_path()
        ctx.fill()

        # Collar gold trim border
        ctx.set_source_rgb(0.85, 0.75, 0.3)
        ctx.set_line_width(1.1)
        ctx.move_to(-14, -6)
        ctx.line_to(-19, -26)
        ctx.line_to(-8, -15)
        ctx.move_to(8, -15)
        ctx.line_to(19, -26)
        ctx.line_to(14, -6)
        ctx.stroke()

        ctx.restore()

        # -------------------------------------------------------------
        # 2. Aristocratic Levitation Lower Body (Trousers & Polished Boots)
        # -------------------------------------------------------------
        ctx.save()
        # Midnight black trousers
        ctx.set_source_rgb(0.14, 0.14, 0.18)
        # Left leg hovering
        ctx.rectangle(-7, 14, 5.5, 14)
        ctx.fill()
        # Right leg hovering slightly forward
        ctx.rectangle(1.5, 15, 5.5, 14)
        ctx.fill()

        # Polished pointed leather boots (angling gracefully downwards in levitation)
        ctx.set_source_rgb(0.06, 0.06, 0.08)
        # Left boot
        ctx.new_path()
        ctx.move_to(-7, 28)
        ctx.line_to(-9, 34)
        ctx.line_to(-2, 34)
        ctx.line_to(-1.5, 28)
        ctx.close_path()
        ctx.fill()
        # Right boot
        ctx.new_path()
        ctx.move_to(1.5, 29)
        ctx.line_to(0.5, 35)
        ctx.line_to(6.5, 35)
        ctx.line_to(7.0, 29)
        ctx.close_path()
        ctx.fill()

        # Boot polish shine
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.4)
        ctx.set_line_width(0.9)
        ctx.move_to(-8, 33)
        ctx.line_to(-4, 33)
        ctx.move_to(1.5, 34)
        ctx.line_to(5.5, 34)
        ctx.stroke()

        ctx.restore()

        # -------------------------------------------------------------
        # 3. Aristocratic Tailored Vest, Cravat & Ruby Brooch
        # -------------------------------------------------------------
        ctx.save()
        # Charcoal velvet tailored double-breasted vest
        vest_grad = cairo.LinearGradient(-8, -4, 8, 16)
        vest_grad.add_color_stop_rgb(0.0, 0.22, 0.22, 0.28)
        vest_grad.add_color_stop_rgb(1.0, 0.15, 0.15, 0.20)
        ctx.set_source(vest_grad)
        ctx.rectangle(-8, -4, 16, 20)
        ctx.fill()

        # Gold vest buttons
        ctx.set_source_rgb(0.9, 0.8, 0.3)
        for by in (0.0, 5.0, 10.0):
            ctx.arc(-3, by, 1.1, 0, math.pi * 2)
            ctx.fill()
            ctx.arc(3, by, 1.1, 0, math.pi * 2)
            ctx.fill()

        # Silk white pleated cravat
        ctx.set_source_rgb(0.95, 0.95, 0.98)
        ctx.new_path()
        ctx.move_to(-5, -6)
        ctx.line_to(5, -6)
        ctx.line_to(2.5, 3)
        ctx.line_to(0, 5)
        ctx.line_to(-2.5, 3)
        ctx.close_path()
        ctx.fill()

        # Glowing royal ruby brooch with gold setting
        ctx.set_source_rgb(0.85, 0.75, 0.25)
        ctx.arc(0, -1.5, 2.8, 0, math.pi * 2)
        ctx.fill()
        # Ruby gemstone
        ctx.set_source_rgb(0.92, 0.08, 0.18)
        ctx.arc(0, -1.5, 2.0, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(-0.6, -2.1, 0.7, 0, math.pi * 2)
        ctx.fill()

        ctx.restore()

        # -------------------------------------------------------------
        # 4. Floating Aristocratic Hands with Poet Shirt Cuffs
        # -------------------------------------------------------------
        ctx.save()
        # Right gesturing hand towards cursor
        hand_y = 6.0 + math.sin(self.anim_time * 2.0) * 1.5
        ctx.set_source_rgb(0.95, 0.95, 0.98)  # White ruffled cuff
        ctx.arc(10, hand_y - 1.5, 3.2, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgb(0.92, 0.94, 0.97)  # Pale alabaster hand
        ctx.arc(11.5, hand_y, 2.4, 0, math.pi * 2)
        ctx.fill()

        # Left hand poised at cape fold
        ctx.set_source_rgb(0.95, 0.95, 0.98)
        ctx.arc(-9, hand_y + 1.0, 3.0, 0, math.pi * 2)
        ctx.fill()
        ctx.set_source_rgb(0.92, 0.94, 0.97)
        ctx.arc(-10.2, hand_y + 2.0, 2.2, 0, math.pi * 2)
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 5. Pale Alabaster Face, Widow's Peak Hair & Glowing Ruby Eyes
        # -------------------------------------------------------------
        ctx.save()

        # Pale aristocratic alabaster skin
        face_grad = cairo.RadialGradient(0, -14, 2, 0, -14, 11)
        face_grad.add_color_stop_rgb(0.0, 0.96, 0.97, 0.99)
        face_grad.add_color_stop_rgb(1.0, 0.88, 0.90, 0.94)
        ctx.set_source(face_grad)
        ctx.arc(0, -14, 10.5, 0, math.pi * 2)
        ctx.fill()

        # Sleek raven hair with sharp widow's peak
        ctx.set_source_rgb(0.06, 0.05, 0.08)
        ctx.new_path()
        ctx.arc(0, -16.5, 11.2, math.pi * 0.85, math.pi * 2.15)
        # Deep widow's peak point
        ctx.line_to(5, -16)
        ctx.line_to(0, -13.5)
        ctx.line_to(-5, -16)
        ctx.close_path()
        ctx.fill()

        # Arched noble eyebrows
        ctx.set_source_rgb(0.12, 0.10, 0.15)
        ctx.set_line_width(1.1)
        ctx.move_to(-6, -17.5)
        ctx.curve_to(-4, -19.5, -2, -18.5, -1, -17.0)
        ctx.stroke()
        ctx.move_to(1, -17.0)
        ctx.curve_to(2, -18.5, 4, -19.5, 6, -17.5)
        ctx.stroke()

        # Glowing Ruby Vampire Eyes with Inner Glint
        eye_glow = 0.85 + 0.15 * math.sin(self.eye_pulse)
        for ex in (-3.5, 3.5):
            # Eye socket
            ctx.set_source_rgb(0.10, 0.06, 0.10)
            ctx.arc(ex, -14.2, 2.5, 0, math.pi * 2)
            ctx.fill()

            # Glowing ruby iris
            ctx.set_source_rgba(0.95, 0.10, 0.22, eye_glow)
            ctx.arc(ex, -14.2, 1.9, 0, math.pi * 2)
            ctx.fill()

            # Pupil
            ctx.set_source_rgb(0.35, 0.02, 0.08)
            ctx.arc(ex, -14.2, 1.0, 0, math.pi * 2)
            ctx.fill()

            # Bright white glint
            ctx.set_source_rgb(1.0, 1.0, 1.0)
            ctx.arc(ex - 0.6, -14.8, 0.6, 0, math.pi * 2)
            ctx.fill()

        # Charming aristocratic smirk with sharp white canine fangs
        ctx.set_source_rgb(0.32, 0.12, 0.18)
        ctx.set_line_width(1.3)
        ctx.new_path()
        ctx.move_to(-3.5, -9.0)
        ctx.curve_to(0, -7.8, 3.0, -8.0, 5.5, -10.0)
        ctx.stroke()

        # Sharp vampire canine fangs
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        # Left fang
        ctx.new_path()
        ctx.move_to(-2.2, -8.2)
        ctx.line_to(-1.4, -5.5)
        ctx.line_to(-0.6, -8.2)
        ctx.close_path()
        ctx.fill()
        # Right fang
        ctx.new_path()
        ctx.move_to(2.0, -8.4)
        ctx.line_to(2.8, -5.7)
        ctx.line_to(3.6, -8.4)
        ctx.close_path()
        ctx.fill()

        ctx.restore()
        ctx.restore()
