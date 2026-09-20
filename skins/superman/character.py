"""Superman character: Man of Steel with supersonic horizontal flight pose, flowing cape, muscular anatomy, and burning heat vision."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager, CYAN_GLOW


class SupermanCharacter(BaseCharacter):
    """Man of Steel with supersonic flight poses, multi-layered flowing cape, House of El crest, and laser heat vision."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="superman")
        self.can_fly = True
        self.is_firing_heat_vision = False
        self.heat_vision_end = 0.0
        self.heat_target = (0.0, 0.0)
        self.action_timer = time.time() + random.uniform(3.0, 6.0)
        self.hover_offset = 0.0

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        if ability_name in ("heat_vision", "attack"):
            self.is_firing_heat_vision = True
            self.heat_vision_end = time.time() + 0.75
            self.heat_target = (target_x, target_y)
            particle_mgr.burst_sparks(target_x, target_y, count=18, color=(1.0, 0.25, 0.05), size=3.0)
            particle_mgr.shockwave(target_x, target_y, max_radius=50.0, color=(1.0, 0.35, 0.1))
            audio_mgr.play("laser")
            return True
        elif ability_name in ("supersonic_flight", "flight", "glide"):
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            self.vx = (dx / dist) * 28.0
            self.vy = (dy / dist) * 28.0
            self.state = CharacterState.FLY
            particle_mgr.shockwave(self.x, self.y, max_radius=70.0, color=(0.9, 0.95, 1.0))
            audio_mgr.play("jet")
            return True
        elif ability_name == "hero_pose":
            self.state = CharacterState.VICTORY
            particle_mgr.burst_sparks(self.x, self.y - 18, count=12, color=(1.0, 0.85, 0.2))
            return True
        return False

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
        self.anim_time += 0.06
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)

        # Facing direction
        self.facing_right = (cursor_x >= self.x)

        if self.is_firing_heat_vision and now >= self.heat_vision_end:
            self.is_firing_heat_vision = False

        # Periodic heroic actions
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(4.0, 8.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.55:
                self.trigger_ability("heat_vision", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.85:
                self.trigger_ability("supersonic_flight", cursor_x, cursor_y, particle_mgr, audio_mgr)
            else:
                self.trigger_ability("hero_pose", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Supersonic flight movement
        speed_mult = config_data.get("speed", 1.0)
        max_spd = 22.0 * speed_mult
        accel = 1.10 * speed_mult

        # True vector to cursor without artificial offset
        dx = cursor_x - self.x
        dy = cursor_y - self.y
        dist = math.hypot(dx, dy)

        if dist > 50.0:
            self.vx += (dx / dist) * min(dist * 0.08, accel)
            self.vy += (dy / dist) * min(dist * 0.08, accel)
            self.state = CharacterState.FLY
        else:
            # Peaceful touch/petting deadzone
            self.state = CharacterState.HOVER
            self.vx *= 0.70
            self.vy *= 0.70

        self.vx *= 0.91
        self.vy *= 0.91

        spd = math.hypot(self.vx, self.vy)
        if spd > max_spd:
            self.vx = (self.vx / spd) * max_spd
            self.vy = (self.vy / spd) * max_spd

        self.x += self.vx
        self.y += self.vy

        # Gentle floating hover wave
        self.hover_offset = math.sin(self.anim_time * 2.5) * 3.5

        # Speed streak particles during supersonic flight
        if spd > 10.0 and random.random() < 0.4:
            particle_mgr.burst_sparks(self.x, self.y, count=2, color=(0.85, 0.95, 1.0), size=1.6)

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 50.0, self.y))

        # Dynamic body tilt: In flight, Superman tilts heavily into the motion angle!
        if self.state == CharacterState.FLY:
            target_tilt = (self.vx / max_spd) * 0.45
        else:
            target_tilt = 0.0
        self.tilt += (target_tilt - self.tilt) * 0.18

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()

        # 1. Twin laser heat vision beams emerging precisely from eyes
        if self.is_firing_heat_vision:
            ctx.save()
            dir_mult = 1.0 if self.facing_right else -1.0
            cos_t = math.cos(self.tilt)
            sin_t = math.sin(self.tilt)

            # In local space, eyes are located at front (4.5, -15.0) and rear (-2.5, -15.0)
            local_eyes = [(4.5, -15.0), (-2.5, -15.0)]
            tgt_x, tgt_y = self.heat_target

            for lx, ly in local_eyes:
                sx = lx * dir_mult * self.scale
                sy = ly * self.scale
                eye_x = self.x + (sx * cos_t - sy * sin_t)
                eye_y = self.y + self.hover_offset + (sx * sin_t + sy * cos_t)

                dx = tgt_x - eye_x
                dy = tgt_y - eye_y
                dist = math.hypot(dx, dy) + 1e-4
                beam_len = min(95.0, max(40.0, dist))
                tx = eye_x + (dx / dist) * beam_len
                ty = eye_y + (dy / dist) * beam_len

                # Wide radiant crimson energy aura
                ctx.new_path()
                ctx.set_line_cap(cairo.LINE_CAP_ROUND)
                ctx.set_line_width(6.0 * self.scale)
                ctx.set_source_rgba(1.0, 0.15, 0.05, 0.45)
                ctx.move_to(eye_x, eye_y)
                ctx.line_to(tx, ty)
                ctx.stroke()

                # Concentrated orange/amber plasma core
                ctx.new_path()
                ctx.set_line_width(3.2 * self.scale)
                ctx.set_source_rgba(1.0, 0.55, 0.12, 0.85)
                ctx.move_to(eye_x, eye_y)
                ctx.line_to(tx, ty)
                ctx.stroke()

                # White-hot laser central core
                ctx.new_path()
                ctx.set_line_width(1.4 * self.scale)
                ctx.set_source_rgba(1.0, 0.98, 0.88, 0.98)
                ctx.move_to(eye_x, eye_y)
                ctx.line_to(tx, ty)
                ctx.stroke()

                # Eye lens corona flare at emergence
                ctx.new_path()
                ctx.set_source_rgba(1.0, 0.35, 0.1, 0.8)
                ctx.arc(eye_x, eye_y, 3.5 * self.scale, 0, 2 * math.pi)
                ctx.fill()
                ctx.new_path()
                ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95)
                ctx.arc(eye_x, eye_y, 1.2 * self.scale, 0, 2 * math.pi)
                ctx.fill()

                # Impact flare
                ctx.new_path()
                ctx.set_source_rgba(1.0, 0.85, 0.2, 0.85)
                ctx.arc(tx, ty, 4.0 * self.scale, 0, 2 * math.pi)
                ctx.fill()

            ctx.restore()

        # 2. Translate & Orient Superman
        ctx.translate(self.x, self.y + self.hover_offset)
        ctx.rotate(self.tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        spd = math.hypot(self.vx, self.vy)
        is_flying = (self.state == CharacterState.FLY or spd > 6.0)

        # 3. Flowing Red Cape with Dynamic Multi-Wave Cloth Physics
        ctx.save()
        cape_pat = cairo.LinearGradient(-8, -10, -32, 28)
        cape_pat.add_color_stop_rgb(0.0, 0.88, 0.12, 0.16)
        cape_pat.add_color_stop_rgb(0.6, 0.72, 0.08, 0.12)
        cape_pat.add_color_stop_rgb(1.0, 0.45, 0.04, 0.06)
        ctx.set_source(cape_pat)

        if is_flying:
            # Cape streams straight back horizontally in supersonic flight
            wave_f = math.sin(self.anim_time * 8.0) * 4.0
            ctx.new_path()
            ctx.move_to(-6, -6)
            ctx.curve_to(-20, -10 + wave_f, -38, -6 - wave_f, -48, -2 + wave_f)
            ctx.line_to(-46, 8 + wave_f)
            ctx.curve_to(-36, 4 - wave_f, -20, 2 + wave_f, -6, 2)
            ctx.close_path()
            ctx.fill()
        else:
            # Standing / Hover: Cape hangs gracefully down with breeze ripples
            wave1 = math.sin(self.anim_time * 3.5) * 3.5
            wave2 = math.cos(self.anim_time * 3.0) * 2.5
            ctx.new_path()
            ctx.move_to(-6, -8)
            ctx.curve_to(-18 + wave1, 4 + wave2, -28 + wave2, 16 + wave1, -24 + wave1, 32)
            ctx.line_to(6, 28)
            ctx.line_to(6, -8)
            ctx.close_path()
            ctx.fill()
        ctx.restore()

        # 4. Muscular Kryptonian Suit & Anatomy
        # Legs & Crimson Boots
        if is_flying:
            # Horizontal streamlined legs trailing back
            ctx.save()
            # Muscular thighs
            suit_leg_pat = cairo.LinearGradient(-8, 2, -26, 10)
            suit_leg_pat.add_color_stop_rgb(0.0, 0.12, 0.38, 0.85)
            suit_leg_pat.add_color_stop_rgb(1.0, 0.06, 0.20, 0.55)
            ctx.set_source(suit_leg_pat)
            ctx.new_path()
            ctx.move_to(-6, 2)
            ctx.line_to(-24, 4)
            ctx.line_to(-24, 10)
            ctx.line_to(-6, 8)
            ctx.close_path()
            ctx.fill()

            # Boots
            boot_pat = cairo.LinearGradient(-24, 4, -34, 9)
            boot_pat.add_color_stop_rgb(0.0, 0.88, 0.12, 0.16)
            boot_pat.add_color_stop_rgb(1.0, 0.55, 0.06, 0.08)
            ctx.set_source(boot_pat)
            ctx.new_path()
            ctx.move_to(-24, 4)
            ctx.line_to(-34, 5)
            ctx.line_to(-34, 9)
            ctx.line_to(-24, 10)
            ctx.close_path()
            ctx.fill()
            ctx.restore()
        else:
            # Standing muscular legs
            for lx in [-8, 2]:
                ctx.save()
                leg_pat = cairo.LinearGradient(lx, 12, lx + 6, 26)
                leg_pat.add_color_stop_rgb(0.0, 0.12, 0.38, 0.85)
                leg_pat.add_color_stop_rgb(1.0, 0.06, 0.20, 0.55)
                ctx.set_source(leg_pat)
                ctx.rectangle(lx, 12, 6, 14)
                ctx.fill()

                # Calf-high crimson boots with peaked front
                boot_pat = cairo.LinearGradient(lx, 22, lx + 6, 28)
                boot_pat.add_color_stop_rgb(0.0, 0.88, 0.12, 0.16)
                boot_pat.add_color_stop_rgb(1.0, 0.55, 0.06, 0.08)
                ctx.set_source(boot_pat)
                ctx.new_path()
                ctx.move_to(lx, 24)
                ctx.line_to(lx + 3, 21.5)  # peaked boot top
                ctx.line_to(lx + 6, 24)
                ctx.line_to(lx + 6, 28)
                ctx.line_to(lx, 28)
                ctx.close_path()
                ctx.fill()
                ctx.restore()

        # Torso: Sculpted V-Taper Kryptonian Suit
        torso_pat = cairo.LinearGradient(-11, -12, 11, 12)
        torso_pat.add_color_stop_rgb(0.0, 0.15, 0.42, 0.90)
        torso_pat.add_color_stop_rgb(0.5, 0.10, 0.32, 0.75)
        torso_pat.add_color_stop_rgb(1.0, 0.05, 0.18, 0.50)
        ctx.set_source(torso_pat)
        ctx.save()
        ctx.new_path()
        ctx.move_to(-11, -10)
        ctx.line_to(11, -10)
        ctx.line_to(8, 10)
        ctx.line_to(-8, 10)
        ctx.close_path()
        ctx.fill()

        # Pectoral & Abdominal muscle contour lines
        ctx.set_source_rgba(0.02, 0.10, 0.30, 0.4)
        ctx.set_line_width(1.0)
        ctx.move_to(-7, -2)
        ctx.curve_to(-3, 0, 3, 0, 7, -2)
        ctx.stroke()
        ctx.move_to(0, -2)
        ctx.line_to(0, 8)
        ctx.stroke()
        ctx.restore()

        # Red Trunks & Gold Belt with Pentagonal Buckle
        if not is_flying:
            # Red trunks
            ctx.set_source_rgb(0.85, 0.10, 0.15)
            ctx.rectangle(-8, 9, 16, 4.5)
            ctx.fill()
            # Golden belt
            belt_pat = cairo.LinearGradient(-8, 7.5, 8, 9.5)
            belt_pat.add_color_stop_rgb(0.0, 1.0, 0.88, 0.25)
            belt_pat.add_color_stop_rgb(1.0, 0.82, 0.65, 0.12)
            ctx.set_source(belt_pat)
            ctx.rectangle(-8, 7.5, 16, 2.5)
            ctx.fill()
            # Oval gold buckle
            ctx.arc(0, 8.7, 2.2, 0, 2 * math.pi)
            ctx.fill()

        # 5. Iconic House of El Diamond Shield Crest on Chest
        ctx.save()
        ctx.translate(0.5, -2.5)
        # Gold diamond crest backing
        gold_pat = cairo.LinearGradient(0, -7, 0, 8)
        gold_pat.add_color_stop_rgb(0.0, 1.0, 0.90, 0.32)
        gold_pat.add_color_stop_rgb(1.0, 0.85, 0.68, 0.15)
        ctx.set_source(gold_pat)
        ctx.new_path()
        ctx.move_to(0, -7)
        ctx.line_to(7.5, -3.5)
        ctx.line_to(5.5, 5.5)
        ctx.line_to(0, 8.5)
        ctx.line_to(-5.5, 5.5)
        ctx.line_to(-7.5, -3.5)
        ctx.close_path()
        ctx.fill()

        # Scarlet Red 'S' Glyph
        ctx.set_source_rgb(0.85, 0.10, 0.15)
        ctx.set_line_width(2.0)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.new_path()
        ctx.move_to(3.5, -3.5)
        ctx.curve_to(-3.5, -4.5, -3.5, -0.5, 0, 0.5)
        ctx.curve_to(3.5, 1.5, 3.5, 6.0, -3.0, 5.0)
        ctx.stroke()
        # Top right serif block
        ctx.rectangle(2.5, -5.5, 2.5, 2.5)
        ctx.fill()
        ctx.restore()

        # 6. Heroic Arms & Poses
        if is_flying:
            # Supersonic Flight Pose: Right arm thrust straight forward leading flight!
            ctx.save()
            r_arm_pat = cairo.LinearGradient(4, -8, 24, -4)
            r_arm_pat.add_color_stop_rgb(0.0, 0.12, 0.38, 0.85)
            r_arm_pat.add_color_stop_rgb(1.0, 0.08, 0.25, 0.65)
            ctx.set_source(r_arm_pat)
            ctx.rectangle(6, -8, 16, 5.5)
            ctx.fill()

            # Leading Clenched Fist
            ctx.set_source_rgb(0.95, 0.78, 0.65)
            ctx.arc(23, -5.2, 3.5, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()
        else:
            # Hover / Stand: Heroic Arms
            for side in [-1, 1]:
                ctx.save()
                arm_pat = cairo.LinearGradient(side * 10, -8, side * 15, 8)
                arm_pat.add_color_stop_rgb(0.0, 0.12, 0.38, 0.85)
                arm_pat.add_color_stop_rgb(1.0, 0.08, 0.25, 0.65)
                ctx.set_source(arm_pat)
                ctx.rectangle(side * 10 if side > 0 else -15, -8, 5, 14)
                ctx.fill()
                # Hands
                ctx.set_source_rgb(0.95, 0.78, 0.65)
                ctx.arc(side * 12.5, 8, 3.0, 0, 2 * math.pi)
                ctx.fill()
                ctx.restore()

        # 7. Head, Chiselled Jaw & Iconic Spit-Curl Hair
        ctx.save()
        # Chiselled jaw & head
        face_pat = cairo.RadialGradient(0, -15, 2, 0, -15, 10)
        face_pat.add_color_stop_rgb(0.0, 1.0, 0.85, 0.72)
        face_pat.add_color_stop_rgb(1.0, 0.90, 0.72, 0.58)
        ctx.set_source(face_pat)
        ctx.arc(0, -15, 9.5, 0, 2 * math.pi)
        ctx.fill()

        # Jet Black Hair
        ctx.set_source_rgb(0.06, 0.06, 0.10)
        ctx.arc(0, -18.5, 9.5, math.pi, 2 * math.pi)
        ctx.fill()
        ctx.new_path()
        ctx.move_to(-9.5, -18.5)
        ctx.line_to(-7, -13)
        ctx.line_to(-5, -18.5)
        ctx.close_path()
        ctx.fill()

        # Iconic S-Curled Spit Curl on Forehead
        ctx.set_source_rgb(0.06, 0.06, 0.10)
        ctx.set_line_width(1.8)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.new_path()
        ctx.move_to(1, -21)
        ctx.curve_to(3.5, -17, -0.5, -16, 2, -13.5)
        ctx.stroke()

        # Heroic Eyes (Blazing Crimson when firing Heat Vision, Royal Blue otherwise)
        if self.is_firing_heat_vision:
            ctx.new_path()
            ctx.set_source_rgb(1.0, 0.15, 0.05)
            ctx.arc(-2.5, -15.0, 2.5, 0, 2 * math.pi)
            ctx.arc(4.5, -15.0, 2.5, 0, 2 * math.pi)
            ctx.fill()
            ctx.new_path()
            ctx.set_source_rgb(1.0, 0.9, 0.8)
            ctx.arc(-2.5, -15.0, 1.0, 0, 2 * math.pi)
            ctx.arc(4.5, -15.0, 1.0, 0, 2 * math.pi)
            ctx.fill()
        else:
            ctx.new_path()
            ctx.set_source_rgb(0.12, 0.45, 0.88)
            ctx.arc(-2.5, -15.0, 1.6, 0, 2 * math.pi)
            ctx.arc(4.5, -15.0, 1.6, 0, 2 * math.pi)
            ctx.fill()
            ctx.new_path()
            ctx.set_source_rgb(0.05, 0.05, 0.08)
            ctx.arc(-2.3, -15.0, 0.8, 0, 2 * math.pi)
            ctx.arc(4.7, -15.0, 0.8, 0, 2 * math.pi)
            ctx.fill()

        ctx.restore()
        ctx.restore()
