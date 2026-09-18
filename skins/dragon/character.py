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
        ctx.translate(self.x, self.y)
        ctx.rotate(self.tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # 1. Back Wing (Behind Body)
        ctx.save()
        ctx.translate(-4, -10)
        ctx.rotate(-self.wing_angle - 0.2)
        # Membrane gradient
        pat_bw = cairo.LinearGradient(0, 0, 10, -30)
        pat_bw.add_color_stop_rgb(0.0, 0.45, 0.08, 0.10)
        pat_bw.add_color_stop_rgb(0.7, 0.35, 0.06, 0.08)
        pat_bw.add_color_stop_rgb(1.0, 0.22, 0.04, 0.05)
        ctx.set_source(pat_bw)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-16, -26, -2, -34, 18, -26)
        ctx.line_to(12, -14)
        ctx.close_path()
        ctx.fill()
        # Back wing bone
        ctx.set_source_rgb(0.35, 0.06, 0.08)
        ctx.set_line_width(2.0)
        ctx.move_to(0, 0)
        ctx.line_to(-2, -34)
        ctx.stroke()
        ctx.restore()

        # 2. Serpentine Tail with Dorsal Spines and Barbed Spade
        ctx.save()
        # Tail curve
        tail_pat = cairo.LinearGradient(0, 6, -38, -6)
        tail_pat.add_color_stop_rgb(0.0, 0.70, 0.14, 0.16)
        tail_pat.add_color_stop_rgb(1.0, 0.45, 0.08, 0.10)
        ctx.set_source(tail_pat)
        ctx.set_line_width(6.5)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.new_path()
        ctx.move_to(-12, 6)
        ctx.curve_to(-24, 10, -32, 2, -38, -6)
        ctx.stroke()

        # Tail spines
        ctx.set_source_rgb(0.25, 0.22, 0.24)
        for t_x, t_y in [(-18, 9), (-26, 7), (-33, 0)]:
            ctx.new_path()
            ctx.move_to(t_x, t_y)
            ctx.line_to(t_x - 3, t_y - 5)
            ctx.line_to(t_x + 2, t_y - 1)
            ctx.close_path()
            ctx.fill()

        # Arrowhead Barbed Tail Spade
        ctx.translate(-38, -6)
        ctx.rotate(-0.4)
        ctx.set_source_rgb(0.20, 0.18, 0.20)
        ctx.new_path()
        ctx.move_to(0, -7)
        ctx.line_to(-10, 0)
        ctx.line_to(0, 7)
        ctx.line_to(-3, 0)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # 3. Dragon Legs & Sharp Black Talons
        for lx, ly in [(-6, 12), (6, 13)]:
            ctx.save()
            ctx.set_source_rgb(0.60, 0.12, 0.14)
            ctx.rectangle(lx - 3, ly, 6, 8)
            ctx.fill()
            # Talons
            ctx.set_source_rgb(0.15, 0.15, 0.18)
            for tox in [-2, 0, 2]:
                ctx.new_path()
                ctx.move_to(lx + tox, ly + 8)
                ctx.line_to(lx + tox + 2, ly + 11)
                ctx.line_to(lx + tox - 1, ly + 11)
                ctx.close_path()
                ctx.fill()
            ctx.restore()

        # 4. Sculpted Dragon Body
        body_pat = cairo.RadialGradient(-2, 0, 2, 0, 4, 18)
        body_pat.add_color_stop_rgb(0.0, 0.85, 0.22, 0.22)
        body_pat.add_color_stop_rgb(0.6, 0.65, 0.14, 0.16)
        body_pat.add_color_stop_rgb(1.0, 0.40, 0.08, 0.10)
        ctx.set_source(body_pat)
        ctx.save()
        ctx.translate(0, 4)
        ctx.scale(1.4, 1.0)
        ctx.arc(0, 0, 15, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # Dorsal Spines along spine
        ctx.set_source_rgb(0.25, 0.22, 0.25)
        for sx, sy in [(-8, -4), (-2, -8), (4, -8), (10, -5)]:
            ctx.new_path()
            ctx.move_to(sx - 2, sy)
            ctx.line_to(sx, sy - 5)
            ctx.line_to(sx + 3, sy)
            ctx.close_path()
            ctx.fill()

        # Golden Belly Plates / Scutes
        belly_pat = cairo.LinearGradient(0, 4, 0, 14)
        belly_pat.add_color_stop_rgb(0.0, 0.98, 0.82, 0.25)
        belly_pat.add_color_stop_rgb(1.0, 0.80, 0.55, 0.12)
        ctx.set_source(belly_pat)
        ctx.save()
        ctx.translate(3, 8)
        ctx.scale(1.1, 0.65)
        ctx.arc(0, 0, 9.5, 0, 2 * math.pi)
        ctx.fill()
        # Segment lines
        ctx.set_source_rgba(0.5, 0.3, 0.05, 0.6)
        ctx.set_line_width(1.0)
        for sy in [-5, -1, 3, 6]:
            ctx.move_to(-7, sy)
            ctx.line_to(7, sy)
            ctx.stroke()
        ctx.restore()

        # 5. Front Wing (Large leathery bat-wing with bone struts)
        ctx.save()
        ctx.translate(2, -6)
        ctx.rotate(self.wing_angle)
        # Wing membrane with dramatic red-to-amber lighting
        pat_fw = cairo.LinearGradient(0, 0, 15, -34)
        pat_fw.add_color_stop_rgb(0.0, 0.90, 0.35, 0.18)
        pat_fw.add_color_stop_rgb(0.5, 0.75, 0.18, 0.12)
        pat_fw.add_color_stop_rgb(1.0, 0.45, 0.08, 0.08)
        ctx.set_source(pat_fw)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-12, -28, 4, -38, 28, -26)
        ctx.curve_to(24, -20, 20, -14, 16, -8)
        ctx.close_path()
        ctx.fill()

        # Skeletal Wing Bones and Struts
        ctx.set_source_rgb(0.35, 0.06, 0.08)
        ctx.set_line_width(2.4)
        ctx.move_to(0, 0)
        ctx.line_to(4, -38)
        ctx.move_to(4, -38)
        ctx.line_to(28, -26)
        ctx.stroke()
        # Secondary struts
        ctx.set_line_width(1.4)
        ctx.move_to(0, 0)
        ctx.line_to(16, -30)
        ctx.move_to(0, 0)
        ctx.line_to(22, -18)
        ctx.stroke()
        # Wing joint thumb claw
        ctx.set_source_rgb(0.20, 0.18, 0.20)
        ctx.new_path()
        ctx.move_to(4, -38)
        ctx.line_to(6, -42)
        ctx.line_to(2, -40)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # 6. Dragon Head, Jaws & Horns
        ctx.save()
        head_pat = cairo.RadialGradient(14, -6, 2, 14, -6, 14)
        head_pat.add_color_stop_rgb(0.0, 0.85, 0.22, 0.22)
        head_pat.add_color_stop_rgb(0.8, 0.65, 0.14, 0.16)
        head_pat.add_color_stop_rgb(1.0, 0.40, 0.08, 0.10)
        ctx.set_source(head_pat)
        ctx.arc(14, -6, 11.5, 0, 2 * math.pi)
        ctx.fill()

        # Snout / Jaws
        ctx.new_path()
        ctx.move_to(14, -10)
        ctx.line_to(27, -9)
        ctx.line_to(27, -2)
        ctx.line_to(14, 1)
        ctx.close_path()
        ctx.fill()

        # Sharp White Fangs
        ctx.set_source_rgb(0.95, 0.95, 0.92)
        for fx in [18, 22, 25]:
            ctx.new_path()
            ctx.move_to(fx, -2)
            ctx.line_to(fx + 1.5, 2)
            ctx.line_to(fx + 3, -2)
            ctx.close_path()
            ctx.fill()

        # Swept-back Horns with Ridges
        ctx.set_source_rgb(0.22, 0.22, 0.25)
        ctx.new_path()
        ctx.move_to(8, -14)
        ctx.curve_to(6, -26, -3, -32, -10, -29)
        ctx.curve_to(-5, -24, 2, -19, 12, -12)
        ctx.close_path()
        ctx.fill()

        # Horn ridge highlights
        ctx.set_source_rgb(0.40, 0.40, 0.45)
        ctx.set_line_width(1.0)
        for h_step in [(4, -18), (1, -22), (-2, -26)]:
            ctx.move_to(h_step[0] - 2, h_step[1])
            ctx.line_to(h_step[0] + 2, h_step[1] + 2)
            ctx.stroke()

        # Glowing Amber Reptilian Eye
        ctx.set_source_rgb(1.0, 0.85, 0.10)
        ctx.arc(15, -9, 3.4, 0, 2 * math.pi)
        ctx.fill()
        # Vertical Slit Pupil
        ctx.set_source_rgb(0.08, 0.04, 0.02)
        ctx.rectangle(14.4, -11.5, 1.2, 5.0)
        ctx.fill()
        # Eye specular spark
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(14.0, -10.0, 0.8, 0, 2 * math.pi)
        ctx.fill()

        # Nostril with glowing smoke wisp
        ctx.set_source_rgb(0.2, 0.05, 0.05)
        ctx.arc(24, -6.5, 1.2, 0, 2 * math.pi)
        ctx.fill()
        if random.random() < 0.35:
            particle_mgr.smoke_puff(self.x + (26 if self.facing_right else -26), self.y - 6, count=1)

        ctx.restore()
        ctx.restore()
