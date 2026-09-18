"""Dragon character: high-resolution realistic fantasy wyrm/drake asset with soaring flight,
dynamic wing flex, glowing ember eye, flame breath cone, and screen-wide returning fireball.
"""

import math
import random
import time
from pathlib import Path
import cairo
from typing import Tuple, Dict, Any, List
from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager, FIRE_ORANGE, FIRE_YELLOW
from core.projectiles import DesktopProjectileWindow


class DragonCharacter(BaseCharacter):
    """Fantasy dragon companion with realistic textured scales, bat-wings, soaring flight, and fire breath."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="dragon")
        self.can_fly = True
        self.hitbox_radius = 48.0
        self.wing_angle = 0.0
        self.wing_speed = 0.18
        self.is_breathing_fire = False
        self.fire_end_time = 0.0
        self.action_timer = time.time() + random.uniform(3.0, 6.0)

        # Load high-resolution realistic dragon asset (PNG / SVG backed)
        self.dragon_surface = None
        asset_png = Path(__file__).parent / "dragon_realistic.png"
        if asset_png.exists():
            try:
                self.dragon_surface = cairo.ImageSurface.create_from_png(str(asset_png))
                self.surf_w = self.dragon_surface.get_width()
                self.surf_h = self.dragon_surface.get_height()
            except Exception as e:
                print(f"[Dragon] Failed to load realistic asset {asset_png}: {e}")
                self.dragon_surface = None
        else:
            self.dragon_surface = None

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        dir_mult = 1.0 if self.facing_right else -1.0
        mouth_x = self.x + dir_mult * 48.0
        mouth_y = self.y + 16.0

        if ability_name == "fire_breath":
            self.is_breathing_fire = True
            self.fire_end_time = time.time() + 1.4
            audio_mgr.play("fire")
            particle_mgr.flame_puff(mouth_x, mouth_y, vx=dir_mult * 14.0, vy=0.0, count=5, size=8.0)
            return True
        elif ability_name == "fireball":
            def _on_catch():
                particle_mgr.flame_puff(self.x + dir_mult * 30.0, self.y + 10.0, count=6, size=6.0)

            DesktopProjectileWindow(
                proj_type="fireball",
                start_x=mouth_x,
                start_y=mouth_y,
                target_x=target_x,
                target_y=target_y,
                owner_getter=lambda: (self.x + (30.0 if self.facing_right else -30.0), self.y + 10.0),
                on_catch=_on_catch,
                speed=26.0
            )
            audio_mgr.play("fire")
            particle_mgr.flame_puff(mouth_x, mouth_y, count=6, size=7.0)
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

        # Dynamic mouth position for fire particles
        dir_mult = 1.0 if self.facing_right else -1.0
        mouth_x = self.x + dir_mult * 48.0
        mouth_y = self.y + 16.0

        # Fire breath continuous stream
        if self.is_breathing_fire:
            particle_mgr.flame_puff(
                mouth_x,
                mouth_y,
                vx=dir_mult * random.uniform(9.0, 18.0),
                vy=random.uniform(-3.5, 3.5),
                count=3,
                size=random.uniform(5.5, 10.0)
            )
            if random.random() < 0.4:
                particle_mgr.burst_sparks(
                    mouth_x,
                    mouth_y,
                    count=2,
                    color=(1.0, 0.75, 0.15),
                    size=2.4
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

        if self.dragon_surface is not None:
            # =========================================================
            # HIGH-RESOLUTION REALISTIC DRAGON RENDERING
            # =========================================================
            dw = self.surf_w
            dh = self.surf_h
            target_w = 126.0
            s = target_w / dw

            # Dynamic flight wing-stroke and breathing scale
            wing_flex = 1.0 + math.sin(self.anim_time * 6.5 * (self.wing_speed / 0.18)) * 0.045
            breath = 1.0 + math.sin(self.anim_time * 2.5) * 0.02

            # Render realistic textured dragon graphic
            ctx.save()
            ctx.scale(s * breath, s * wing_flex)
            ctx.set_source_surface(self.dragon_surface, -dw * 0.52, -dh * 0.48)
            ctx.paint()
            ctx.restore()

            # Fiery glowing amber eye with pulsing lens flare
            eye_x = (775 - dw * 0.52) * s
            eye_y = (488 - dh * 0.48) * s
            pulse = 0.8 + 0.2 * math.sin(self.anim_time * 5.0)

            pat_eye = cairo.RadialGradient(eye_x, eye_y, 0.4, eye_x, eye_y, 4.2)
            pat_eye.add_color_stop_rgba(0.0, 1.0, 1.0, 0.6, 1.0)
            pat_eye.add_color_stop_rgba(0.4, 1.0, 0.6, 0.1, 0.85 * pulse)
            pat_eye.add_color_stop_rgba(1.0, 1.0, 0.2, 0.0, 0.0)
            ctx.set_source(pat_eye)
            ctx.arc(eye_x, eye_y, 4.2, 0, 2 * math.pi)
            ctx.fill()

            # Specular eye gleam
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            ctx.arc(eye_x - 0.4, eye_y - 0.4, 0.7, 0, 2 * math.pi)
            ctx.fill()

            # Radiant glow inside open mouth when breathing fire
            if self.is_breathing_fire:
                mouth_x = (822 - dw * 0.52) * s
                mouth_y = (525 - dh * 0.48) * s

                pat_mouth = cairo.RadialGradient(mouth_x, mouth_y, 1.0, mouth_x, mouth_y, 10.0)
                pat_mouth.add_color_stop_rgba(0.0, 1.0, 0.95, 0.4, 1.0)
                pat_mouth.add_color_stop_rgba(0.5, 1.0, 0.45, 0.05, 0.8)
                pat_mouth.add_color_stop_rgba(1.0, 1.0, 0.1, 0.0, 0.0)
                ctx.set_source(pat_mouth)
                ctx.arc(mouth_x, mouth_y, 10.0, 0, 2 * math.pi)
                ctx.fill()

            ctx.restore()
            return

        # =============================================================
        # PROCEDURAL FALLBACK RENDERING (If PNG Asset Missing)
        # =============================================================
        # 1. Back Wing
        ctx.save()
        ctx.translate(-4, -6)
        ctx.rotate(-0.35 + self.wing_angle * 0.5)
        pat_wing = cairo.LinearGradient(0, -32, 0, 8)
        pat_wing.add_color_stop_rgb(0.0, 0.72, 0.15, 0.18)
        pat_wing.add_color_stop_rgb(1.0, 0.32, 0.06, 0.08)
        ctx.set_source(pat_wing)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.curve_to(-12, -28, -6, -42, 14, -36)
        ctx.curve_to(8, -22, 16, -14, 0, 0)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # 2. Body & Neck
        pat_body = cairo.LinearGradient(-15, -12, 15, 12)
        pat_body.add_color_stop_rgb(0.0, 0.85, 0.18, 0.18)
        pat_body.add_color_stop_rgb(0.6, 0.65, 0.10, 0.12)
        pat_body.add_color_stop_rgb(1.0, 0.38, 0.05, 0.08)
        ctx.set_source(pat_body)
        ctx.save()
        ctx.translate(0, 4)
        ctx.scale(1.3, 0.9)
        ctx.arc(0, 0, 15, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        # 3. Head & Snout
        ctx.save()
        ctx.translate(18, -4)
        ctx.set_source(pat_body)
        ctx.new_path()
        ctx.move_to(-4, 2)
        ctx.line_to(12, -2)
        ctx.line_to(14, 4)
        ctx.line_to(0, 8)
        ctx.close_path()
        ctx.fill()
        # Eye
        ctx.set_source_rgb(1.0, 0.85, 0.1)
        ctx.arc(6, 0, 2.2, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()

        ctx.restore()
