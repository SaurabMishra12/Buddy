"""Dragon character: mythical crimson wyrm with flapping wings, fire breath cone, screen-wide returning fireball, and soaring flight."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, List
from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager, FIRE_ORANGE, FIRE_YELLOW
from core.projectiles import DesktopProjectileWindow


class DragonCharacter(BaseCharacter):
    """Fantasy dragon companion with authentic multi-stop scales, flapping bat-wings, soaring flight, and fire breath."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="dragon")
        self.can_fly = True
        self.wing_angle = 0.0
        self.wing_speed = 0.18
        self.is_breathing_fire = False
        self.fire_end_time = 0.0
        self.action_timer = time.time() + random.uniform(3.0, 6.0)

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        if ability_name == "fire_breath":
            self.is_breathing_fire = True
            self.fire_end_time = time.time() + 1.2
            audio_mgr.play("fire")
            return True
        elif ability_name == "fireball":
            dir_mult = 1.0 if self.facing_right else -1.0
            start_x = self.x + dir_mult * 26.0
            start_y = self.y - 4.0

            def _on_catch():
                particle_mgr.flame_puff(self.x + dir_mult * 20.0, self.y, count=6, size=5.5)

            DesktopProjectileWindow(
                proj_type="fireball",
                start_x=start_x,
                start_y=start_y,
                target_x=target_x,
                target_y=target_y,
                owner_getter=lambda: (self.x + (20.0 if self.facing_right else -20.0), self.y),
                on_catch=_on_catch,
                speed=25.0
            )
            audio_mgr.play("fire")
            particle_mgr.flame_puff(start_x, start_y, count=5, size=6.0)
            return True
        elif ability_name in ("flight", "glide"):
            self.vy -= 8.0
            self.state = CharacterState.FLY
            particle_mgr.smoke_puff(self.x, self.y + 16, count=3)
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
        self.anim_time += 0.05
        now = time.time()
        min_x, min_y, screen_w, screen_h = screen_bounds
        activity = config_data.get("activity_level", 1.0)

        # Facing direction
        self.facing_right = (cursor_x >= self.x)

        # Fire breath duration
        if self.is_breathing_fire:
            dir_mult = 1.0 if self.facing_right else -1.0
            mouth_x = self.x + dir_mult * 26.0
            mouth_y = self.y - 4.0
            particle_mgr.flame_puff(
                mouth_x,
                mouth_y,
                vx=dir_mult * random.uniform(8.0, 16.0),
                vy=random.uniform(-3.5, 3.5),
                count=3,
                size=random.uniform(5.0, 9.0)
            )
            if now >= self.fire_end_time:
                self.is_breathing_fire = False

        # Random personality actions
        if now >= self.action_timer and activity > 0.1:
            self.action_timer = now + random.uniform(4.0, 8.0) / max(0.2, activity)
            roll = random.random()
            if roll < 0.40:
                self.trigger_ability("fire_breath", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.70:
                self.trigger_ability("fireball", cursor_x, cursor_y, particle_mgr, audio_mgr)
            elif roll < 0.90:
                self.trigger_ability("flight", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # Flight physics (soars and hovers near cursor)
        speed_mult = config_data.get("speed", 1.0)
        max_spd = 14.0 * speed_mult
        accel = 0.55 * speed_mult

        # True vector to cursor without artificial offset
        dx = cursor_x - self.x
        dy = cursor_y - self.y
        dist = math.hypot(dx, dy)

        if dist > 50.0:
            self.vx += (dx / dist) * min(dist * 0.05, accel)
            self.vy += (dy / dist) * min(dist * 0.05, accel)
            self.state = CharacterState.FLY
        else:
            # Peaceful touch/petting deadzone
            self.state = CharacterState.HOVER
            self.vx *= 0.70
            self.vy *= 0.70

        self.vx *= 0.92
        self.vy *= 0.92

        spd = math.hypot(self.vx, self.vy)
        if spd > max_spd:
            self.vx = (self.vx / spd) * max_spd
            self.vy = (self.vy / spd) * max_spd

        self.x += self.vx
        self.y += self.vy

        # Wing flapping speed depends on velocity
        self.wing_speed = 0.25 if spd > 2.0 else 0.12
        self.wing_angle = math.sin(self.anim_time * 8.0 * (self.wing_speed / 0.18)) * 0.65

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 50.0, self.y))

        # Dynamic body tilt
        target_tilt = (self.vx / max_spd) * 0.25
        self.tilt += (target_tilt - self.tilt) * 0.15

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()
        # Floating hover bobbing in flight
        hover_y = math.sin(self.anim_time * 3.0) * 3.5 if self.state in (CharacterState.FLY, CharacterState.HOVER) else 0.0
        ctx.translate(self.x, self.y + hover_y)
        ctx.rotate(self.tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # -------------------------------------------------------------
        # 1. Back Wing (Behind Body, with translucent membrane & skeletal struts)
        # -------------------------------------------------------------
        ctx.save()
        ctx.translate(-6, -8)
        ctx.rotate(-self.wing_angle * 0.85 - 0.15)

        # Translucent Back Wing Webbing (Subsurface amber-to-crimson scattering)
        pat_bw = cairo.LinearGradient(0, 0, 12, -38)
        pat_bw.add_color_stop_rgba(0.0, 0.48, 0.08, 0.10, 0.85)
        pat_bw.add_color_stop_rgba(0.4, 0.65, 0.18, 0.12, 0.88)
        pat_bw.add_color_stop_rgba(0.8, 0.85, 0.35, 0.15, 0.90)
        pat_bw.add_color_stop_rgba(1.0, 0.30, 0.05, 0.06, 0.85)
        ctx.set_source(pat_bw)

        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-18, -28, -6, -42, 16, -34)
        ctx.curve_to(26, -26, 22, -16, 14, -6)
        ctx.close_path()
        ctx.fill()

        # Back Wing Veins & Skeletal Struts
        ctx.set_source_rgba(0.28, 0.04, 0.06, 0.9)
        ctx.set_line_width(2.2)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-6, -22, -4, -36, 16, -34)
        ctx.stroke()
        # Secondary struts
        ctx.set_line_width(1.2)
        ctx.move_to(0, -16)
        ctx.line_to(18, -24)
        ctx.move_to(0, -10)
        ctx.line_to(14, -12)
        ctx.stroke()
        ctx.restore()

        # -------------------------------------------------------------
        # 2. Serpentine Muscular Tail with Dorsal Spines & Barbed Spade
        # -------------------------------------------------------------
        ctx.save()
        tail_wave = math.sin(self.anim_time * 4.0) * 4.0
        tail_pat = cairo.LinearGradient(0, 8, -42, -4 + tail_wave)
        tail_pat.add_color_stop_rgb(0.0, 0.72, 0.13, 0.15)
        tail_pat.add_color_stop_rgb(0.5, 0.52, 0.09, 0.11)
        tail_pat.add_color_stop_rgb(1.0, 0.32, 0.05, 0.07)
        ctx.set_source(tail_pat)
        ctx.set_line_width(8.0)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.new_path()
        ctx.move_to(-12, 6)
        ctx.curve_to(-24, 12, -34, 4 + tail_wave * 0.5, -42, -4 + tail_wave)
        ctx.stroke()

        # Tail Dorsal Spine Crests
        ctx.set_source_rgb(0.22, 0.18, 0.22)
        for t_x, t_y in [(-18, 9), (-26, 8), (-34, 2 + tail_wave * 0.4), (-40, -2 + tail_wave * 0.8)]:
            ctx.new_path()
            ctx.move_to(t_x, t_y)
            ctx.line_to(t_x - 3, t_y - 7)
            ctx.line_to(t_x + 3, t_y - 2)
            ctx.close_path()
            ctx.fill()

        # Sharp Barbed Obsidian Tail Spade
        ctx.save()
        ctx.translate(-42, -4 + tail_wave)
        ctx.rotate(-0.35 + tail_wave * 0.04)
        spade_pat = cairo.LinearGradient(-12, 0, 4, 0)
        spade_pat.add_color_stop_rgb(0.0, 0.12, 0.12, 0.15)
        spade_pat.add_color_stop_rgb(0.5, 0.35, 0.15, 0.18)
        spade_pat.add_color_stop_rgb(1.0, 0.15, 0.14, 0.16)
        ctx.set_source(spade_pat)
        ctx.new_path()
        ctx.move_to(2, -9)
        ctx.curve_to(-6, -7, -14, -2, -18, 0)
        ctx.curve_to(-14, 2, -6, 7, 2, 9)
        ctx.line_to(-4, 0)
        ctx.close_path()
        ctx.fill()
        # Central spine on spade
        ctx.set_source_rgb(0.75, 0.25, 0.25)
        ctx.set_line_width(1.2)
        ctx.move_to(-16, 0)
        ctx.line_to(0, 0)
        ctx.stroke()
        ctx.restore()
        ctx.restore()

        # -------------------------------------------------------------
        # 3. Muscular Drake Hind Limbs & Razor-Sharp Talons
        # -------------------------------------------------------------
        for lx, ly, leg_scale in [(-8, 10, 0.95), (6, 12, 1.05)]:
            ctx.save()
            ctx.translate(lx, ly)
            ctx.scale(leg_scale, leg_scale)

            # Muscular Thigh with scale texture
            thigh_pat = cairo.RadialGradient(0, 0, 1, 0, 0, 9)
            thigh_pat.add_color_stop_rgb(0.0, 0.78, 0.16, 0.18)
            thigh_pat.add_color_stop_rgb(0.7, 0.55, 0.10, 0.12)
            thigh_pat.add_color_stop_rgb(1.0, 0.32, 0.06, 0.08)
            ctx.set_source(thigh_pat)
            ctx.new_path()
            ctx.arc(0, 0, 7.5, 0, 2 * math.pi)
            ctx.fill()

            # Lower leg / Hock
            ctx.set_source_rgb(0.48, 0.09, 0.11)
            ctx.new_path()
            ctx.move_to(-2.5, 3)
            ctx.line_to(2.5, 3)
            ctx.line_to(3.5, 11)
            ctx.line_to(-3.5, 11)
            ctx.close_path()
            ctx.fill()

            # 3 Curved Black Obsidian Talons
            ctx.set_source_rgb(0.12, 0.11, 0.14)
            for tox in [-3.0, 0.0, 3.0]:
                ctx.new_path()
                ctx.move_to(tox - 1.2, 11)
                ctx.curve_to(tox, 13, tox + 2.5, 15, tox + 4.0, 16)
                ctx.curve_to(tox + 1.8, 14.5, tox, 13, tox + 0.8, 11)
                ctx.close_path()
                ctx.fill()
                # Specular talon highlight
                ctx.set_source_rgba(1.0, 1.0, 1.0, 0.4)
                ctx.set_line_width(0.7)
                ctx.move_to(tox, 11.5)
                ctx.line_to(tox + 2.5, 14.5)
                ctx.stroke()
                ctx.set_source_rgb(0.12, 0.11, 0.14)
            ctx.restore()

        # -------------------------------------------------------------
        # 4. Muscular Sculpted Dragon Torso & Neck
        # -------------------------------------------------------------
        # Muscular Body Mass
        body_pat = cairo.RadialGradient(-3, 2, 2, 0, 4, 22)
        body_pat.add_color_stop_rgb(0.0, 0.90, 0.22, 0.22)
        body_pat.add_color_stop_rgb(0.5, 0.68, 0.13, 0.15)
        body_pat.add_color_stop_rgb(1.0, 0.35, 0.06, 0.08)
        ctx.set_source(body_pat)
        ctx.save()
        ctx.translate(-1, 5)
        ctx.scale(1.45, 1.05)
        ctx.arc(0, 0, 16.5, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # Arching Muscular Neck
        neck_pat = cairo.LinearGradient(-2, 4, 14, -8)
        neck_pat.add_color_stop_rgb(0.0, 0.65, 0.12, 0.14)
        neck_pat.add_color_stop_rgb(0.6, 0.82, 0.18, 0.20)
        neck_pat.add_color_stop_rgb(1.0, 0.50, 0.08, 0.10)
        ctx.set_source(neck_pat)
        ctx.new_path()
        ctx.move_to(-2, 0)
        ctx.curve_to(2, -8, 8, -14, 16, -10)
        ctx.curve_to(14, -4, 10, 6, 4, 10)
        ctx.close_path()
        ctx.fill()

        # Overlapping Diamond Scales Texture (Neck & Upper Flank)
        ctx.set_source_rgba(1.0, 0.5, 0.3, 0.45)
        ctx.set_line_width(0.9)
        scale_coords = [(-6, 2), (-2, 0), (2, -2), (6, -4), (10, -6),
                        (-4, 6), (0, 4), (4, 2), (8, 0),
                        (-2, 9), (2, 7), (6, 5)]
        for scx, scy in scale_coords:
            ctx.new_path()
            ctx.move_to(scx, scy - 2)
            ctx.line_to(scx + 2.5, scy)
            ctx.line_to(scx, scy + 2)
            ctx.line_to(scx - 2.5, scy)
            ctx.close_path()
            ctx.stroke()

        # Dorsal Spines along the Neck and Spine
        ctx.set_source_rgb(0.18, 0.16, 0.20)
        for sx, sy, sh in [(-10, -2, 5), (-4, -6, 7), (2, -9, 8), (8, -13, 9), (13, -15, 7)]:
            ctx.new_path()
            ctx.move_to(sx - 2.5, sy)
            ctx.line_to(sx, sy - sh)
            ctx.line_to(sx + 3.0, sy + 1)
            ctx.close_path()
            ctx.fill()
            # Ridge highlight
            ctx.set_source_rgba(0.5, 0.45, 0.5, 0.6)
            ctx.set_line_width(0.8)
            ctx.move_to(sx - 1.5, sy)
            ctx.line_to(sx, sy - sh)
            ctx.stroke()
            ctx.set_source_rgb(0.18, 0.16, 0.20)

        # Segmented Ventral Golden-Amber Belly Armor (Scutes)
        belly_pat = cairo.LinearGradient(0, 3, 0, 16)
        belly_pat.add_color_stop_rgb(0.0, 1.0, 0.88, 0.35)
        belly_pat.add_color_stop_rgb(0.6, 0.90, 0.68, 0.18)
        belly_pat.add_color_stop_rgb(1.0, 0.68, 0.42, 0.10)
        ctx.set_source(belly_pat)
        ctx.save()
        ctx.translate(4, 8)
        ctx.scale(1.15, 0.72)
        ctx.arc(0, 0, 10.5, 0, 2 * math.pi)
        ctx.fill()
        # Fine segment lines & plate seams
        ctx.set_source_rgba(0.42, 0.22, 0.04, 0.75)
        ctx.set_line_width(1.1)
        for sy in [-6, -2, 2, 6]:
            ctx.move_to(-8, sy)
            ctx.curve_to(-3, sy + 1.2, 3, sy + 1.2, 8, sy)
            ctx.stroke()
        ctx.restore()

        # -------------------------------------------------------------
        # 5. Grand Front Wing (Large Articulated Bat Wing with Translucent Membrane)
        # -------------------------------------------------------------
        ctx.save()
        ctx.translate(1, -6)
        ctx.rotate(self.wing_angle)

        # Translucent Wing Webbing with rich subsurface scattering
        pat_fw = cairo.LinearGradient(0, 0, 24, -46)
        pat_fw.add_color_stop_rgba(0.0, 0.96, 0.45, 0.20, 0.92)
        pat_fw.add_color_stop_rgba(0.4, 0.82, 0.22, 0.15, 0.94)
        pat_fw.add_color_stop_rgba(0.75, 0.60, 0.12, 0.12, 0.96)
        pat_fw.add_color_stop_rgba(1.0, 0.32, 0.05, 0.07, 0.96)
        ctx.set_source(pat_fw)

        # Scalloped aerodynamic wing contour
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-14, -32, 6, -48, 32, -32)
        ctx.curve_to(30, -22, 26, -14, 20, -6)
        ctx.curve_to(16, -2, 10, 0, 0, 0)
        ctx.close_path()
        ctx.fill()

        # Translucent Branching Capillary Veins in the Wing Webbing
        ctx.set_source_rgba(1.0, 0.8, 0.4, 0.35)
        ctx.set_line_width(0.8)
        ctx.new_path()
        ctx.move_to(8, -26)
        ctx.line_to(16, -34)
        ctx.move_to(12, -20)
        ctx.line_to(22, -26)
        ctx.move_to(14, -14)
        ctx.line_to(24, -18)
        ctx.stroke()

        # Skeletal Wing Arm Bones (Humerus, Radius/Ulna & Elongated Fingers)
        ctx.set_source_rgb(0.38, 0.06, 0.08)
        ctx.set_line_width(3.0)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(2, -24, 4, -44, 8, -46)
        ctx.stroke()

        # Elongated Finger Struts
        ctx.set_line_width(1.8)
        ctx.new_path()
        ctx.move_to(8, -46)
        ctx.line_to(32, -32)
        ctx.move_to(6, -38)
        ctx.line_to(26, -20)
        ctx.move_to(4, -28)
        ctx.line_to(20, -10)
        ctx.stroke()

        # Hooked Thumb Claw (Alula) at Wing Apex
        ctx.set_source_rgb(0.12, 0.10, 0.14)
        ctx.new_path()
        ctx.move_to(8, -46)
        ctx.curve_to(11, -50, 9, -52, 6, -49)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 6. Predatory Drake Head, Curved Horns & Piercing Eyes
        # -------------------------------------------------------------
        ctx.save()
        # Head Base & Jaw Muscles
        head_pat = cairo.RadialGradient(16, -7, 2, 16, -7, 16)
        head_pat.add_color_stop_rgb(0.0, 0.92, 0.25, 0.22)
        head_pat.add_color_stop_rgb(0.65, 0.70, 0.14, 0.16)
        head_pat.add_color_stop_rgb(1.0, 0.38, 0.07, 0.09)
        ctx.set_source(head_pat)
        ctx.new_path()
        ctx.arc(16, -7, 12.5, 0, 2 * math.pi)
        ctx.fill()

        # Chiseled Predatory Snout / Jaws
        ctx.new_path()
        ctx.move_to(16, -12)
        ctx.curve_to(24, -13, 30, -11, 33, -9)  # Upper snout bridge
        ctx.line_to(33, -3)                      # Snout tip
        ctx.curve_to(28, -2, 22, -1, 15, 2)      # Lower jaw contour
        ctx.close_path()
        ctx.fill()

        # Nostril Ridge with Glowing Smoke & Fire Embers
        ctx.set_source_rgb(0.18, 0.04, 0.04)
        ctx.arc(29, -8, 1.6, 0, 2 * math.pi)
        ctx.fill()
        # Glowing ember spark inside nostril
        ctx.set_source_rgb(1.0, 0.6, 0.1)
        ctx.arc(28.5, -8, 0.7, 0, 2 * math.pi)
        ctx.fill()
        if random.random() < 0.30:
            particle_mgr.smoke_puff(self.x + (30 if self.facing_right else -30), self.y - 7 + hover_y, count=1)

        # Internal Glowing Maw (if breathing fire or ready)
        if self.is_breathing_fire or random.random() < 0.20:
            ctx.set_source_rgba(1.0, 0.55, 0.1, 0.75)
            ctx.new_path()
            ctx.move_to(22, -4)
            ctx.line_to(31, -5)
            ctx.line_to(24, 0)
            ctx.close_path()
            ctx.fill()

        # Razor-Sharp Ivory Fangs
        ctx.set_source_rgb(0.98, 0.97, 0.92)
        for fx, fy, fh in [(21, -3, 3.5), (25, -4, 4.0), (29, -5, 3.0), (32, -5, 2.5)]:
            ctx.new_path()
            ctx.move_to(fx - 1.0, fy)
            ctx.line_to(fx + 0.5, fy + fh)
            ctx.line_to(fx + 2.0, fy)
            ctx.close_path()
            ctx.fill()

        # Dual Swept-back Horns with Growth Ridges & Obsidian Sheen
        # Primary Curved Dragon Horn
        ctx.set_source_rgb(0.16, 0.14, 0.18)
        ctx.new_path()
        ctx.move_to(11, -15)
        ctx.curve_to(8, -28, -2, -37, -14, -33)
        ctx.curve_to(-7, -27, 2, -21, 14, -13)
        ctx.close_path()
        ctx.fill()

        # Secondary Lower Cheek Horn
        ctx.new_path()
        ctx.move_to(13, -3)
        ctx.curve_to(6, -7, -2, -8, -6, -6)
        ctx.curve_to(1, -4, 7, -1, 14, 0)
        ctx.close_path()
        ctx.fill()

        # Horn Growth Rings & Specular Highlights
        ctx.set_source_rgba(0.55, 0.50, 0.58, 0.6)
        ctx.set_line_width(1.1)
        for h_step in [(6, -20), (2, -25), (-3, -29), (-8, -32)]:
            ctx.move_to(h_step[0] - 2.5, h_step[1])
            ctx.line_to(h_step[0] + 2.5, h_step[1] + 2.5)
            ctx.stroke()

        # Piercing Golden-Amber Reptilian Slit Eye with Glassy Cornea
        # Eye Socket Shadow
        ctx.set_source_rgb(0.25, 0.05, 0.06)
        ctx.arc(17, -10, 4.8, 0, 2 * math.pi)
        ctx.fill()

        # Glowing Amber/Gold Iris
        eye_iris = cairo.RadialGradient(17, -10, 0.5, 17, -10, 4.0)
        eye_iris.add_color_stop_rgb(0.0, 1.0, 0.92, 0.25)
        eye_iris.add_color_stop_rgb(0.7, 0.98, 0.72, 0.05)
        eye_iris.add_color_stop_rgb(1.0, 0.75, 0.35, 0.02)
        ctx.set_source(eye_iris)
        ctx.arc(17, -10, 4.0, 0, 2 * math.pi)
        ctx.fill()

        # Black Predatory Vertical Slit Pupil
        ctx.set_source_rgb(0.04, 0.02, 0.02)
        ctx.new_path()
        ctx.move_to(17, -13.5)
        ctx.curve_to(17.8, -10, 17.8, -10, 17, -6.5)
        ctx.curve_to(16.2, -10, 16.2, -10, 17, -13.5)
        ctx.close_path()
        ctx.fill()

        # Specular Cornea Catchlight
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(15.8, -11.2, 1.0, 0, 2 * math.pi)
        ctx.fill()

        ctx.restore()
        ctx.restore()
