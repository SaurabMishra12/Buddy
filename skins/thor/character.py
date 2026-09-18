"""Thor character: vector rendering, flowing cape physics, and realistic Mjolnir combat mechanics."""

import math
import random
import time
import cairo
from typing import Tuple, Dict, Any, Optional

from skins.base import BaseCharacter, CharacterState
from skins.manager import skin_manager
from skins.thor.cape import Cape
from skins.thor.hammer import Mjolnir
from core.particles import ParticleManager, CYAN_GLOW
from core.projectiles import DesktopProjectileWindow


class ThorCharacter(BaseCharacter):
    """Thor, God of Thunder — Desktop companion with authentic Mjolnir and fractal lightning."""

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="thor")
        self.can_fly = True
        self.cape = Cape(x, y)
        self.mjolnir = Mjolnir(x + 12.5, y + 12.0)
        self.eyes_glow = 0.3
        self.play_timer = time.time() + random.uniform(4.0, 8.0)
        self.thrown_time = 0.0
        self.is_summoning = False
        self.target_offset_x = -50.0
        self.target_offset_y = -50.0

    def get_hand_pos(self) -> Tuple[float, float]:
        """Returns world coordinates of Thor's active right hand."""
        dir_mult = 1.0 if self.facing_right else -1.0
        spd = math.hypot(self.vx, self.vy)
        if self.state == "SUMMONING":
            hx = self.x + dir_mult * 26.0
            hy = self.y - 3.5
        elif spd > 4.0:
            hx = self.x + dir_mult * 22.0
            hy = self.y - 2.5
        else:
            hx = self.x + dir_mult * 12.5
            hy = self.y + 12.0
        return (hx, hy)

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        hand_x, hand_y = self.get_hand_pos()
        if ability_name in ("hammer_throw", "attack"):
            if self.mjolnir.state == "HELD":
                self.mjolnir.state = "DESKTOP_THROWN"
                self.state = "SUMMONING"
                self.is_summoning = True

                def _on_catch():
                    self.mjolnir.state = "HELD"
                    self.is_summoning = False
                    self.state = CharacterState.IDLE
                    particle_mgr.burst_sparks(self.x, self.y, count=20, color=CYAN_GLOW)
                    particle_mgr.shockwave(self.x, self.y, max_radius=65.0)

                DesktopProjectileWindow(
                    proj_type="mjolnir",
                    start_x=hand_x,
                    start_y=hand_y,
                    target_x=target_x,
                    target_y=target_y,
                    owner_getter=self.get_hand_pos,
                    on_catch=_on_catch,
                    speed=28.0
                )
                self.thrown_time = time.time()
                particle_mgr.burst_sparks(hand_x, hand_y, count=16, color=CYAN_GLOW)
                audio_mgr.play("lightning")
                return True
        elif ability_name == "lightning_summon":
            particle_mgr.sky_strike(target_x, target_y)
            audio_mgr.play("lightning")
            return True
        elif ability_name == "hammer_spin":
            if self.mjolnir.state == "HELD":
                self.mjolnir.throw(hand_x, hand_y, target_x, target_y, mode="orbit")
                self.thrown_time = time.time()
                particle_mgr.shockwave(self.x, self.y, max_radius=65.0)
                audio_mgr.play("lightning")
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
        min_x, min_y, screen_w, screen_h = screen_bounds
        now = time.time()
        hand_x, hand_y = self.get_hand_pos()

        # Facing direction
        if self.state == "SUMMONING":
            self.facing_right = (self.mjolnir.x >= self.x)
        else:
            self.facing_right = (cursor_x >= self.x)

        # AI Behavior: Playful Mjolnir spin & Bounded Boomerang
        if self.mjolnir.state == "HELD":
            self.is_summoning = False
            if self.state == "SUMMONING":
                self.state = CharacterState.IDLE

            activity = config_data.get("activity_level", 1.0)
            if now >= self.play_timer and activity > 0.1:
                # Thor periodically executes an epic thunder orbit or a quick boomerang strike
                mode = random.choice(["orbit", "orbit", "boomerang"])
                if mode == "orbit":
                    target_x = self.x
                    target_y = self.y
                else:
                    # Bounded throw towards cursor (within 45px of Thor)
                    dx = cursor_x - self.x
                    dy = cursor_y - self.y
                    dist = math.hypot(dx, dy) + 1e-4
                    target_x = self.x + (dx / dist) * min(45.0, dist)
                    target_y = self.y + (dy / dist) * min(35.0, dist)

                self.mjolnir.throw(hand_x, hand_y, target_x, target_y, mode=mode)
                self.thrown_time = now
                self.play_timer = now + random.uniform(5.0, 9.0) / max(0.2, activity)
                particle_mgr.burst_sparks(hand_x, hand_y, count=12, color=CYAN_GLOW)
                audio_mgr.play("lightning")
                if random.random() < 0.35:
                    particle_mgr.sky_strike(self.x, self.y)

        elif self.mjolnir.state in ("THROWN", "ORBITING"):
            if now - self.thrown_time >= 1.4 and not self.is_summoning:
                self.is_summoning = True
                self.state = "SUMMONING"
                self.mjolnir.summon()
                particle_mgr.burst_sparks(hand_x, hand_y, count=14, color=CYAN_GLOW)
                audio_mgr.play("lightning")

        # Thor movement physics (chases cursor with smooth spring damping)
        speed_mult = config_data.get("speed", 1.0)
        max_speed = 18.0 * speed_mult
        accel = 0.8 * speed_mult
        friction = 0.88

        tx = cursor_x + self.target_offset_x
        ty = cursor_y + self.target_offset_y

        dx = tx - self.x
        dy = ty - self.y
        dist = math.hypot(dx, dy)

        if dist > 8.0:
            self.vx += (dx / dist) * min(dist * 0.08, accel)
            self.vy += (dy / dist) * min(dist * 0.08, accel)
            if self.state not in ("SUMMONING", CharacterState.ATTACK):
                self.state = CharacterState.FLY
        else:
            if self.state not in ("SUMMONING", CharacterState.ATTACK):
                self.state = CharacterState.IDLE

        self.vx *= friction
        self.vy *= friction

        spd = math.hypot(self.vx, self.vy)
        if spd > max_speed:
            self.vx = (self.vx / spd) * max_speed
            self.vy = (self.vy / spd) * max_speed

        self.x += self.vx
        self.y += self.vy

        # Idle hover bob
        if self.state == CharacterState.IDLE:
            self.y += math.sin(self.anim_time * 3.0) * 0.35

        # Screen boundary clamp
        self.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.x))
        self.y = max(min_y + 50.0, min(min_y + screen_h - 50.0, self.y))

        # Dynamic body tilt
        target_tilt = (self.vx / max_speed) * 0.25
        self.tilt += (target_tilt - self.tilt) * 0.15

        # Cape physics
        cape_anchor_x = self.x - (10.0 if self.facing_right else -10.0)
        cape_anchor_y = self.y - 12.0
        self.cape.update(cape_anchor_x, cape_anchor_y, self.vx, self.vy)

        # Eye glow
        target_glow = 1.0 if self.state == "SUMMONING" else (0.3 + (spd / max_speed) * 0.6)
        self.eyes_glow += (target_glow - self.eyes_glow) * 0.15

        if self.state == "SUMMONING" and random.random() < 0.4:
            particle_mgr.burst_sparks(hand_x, hand_y, count=2, color=CYAN_GLOW)
        elif spd > 10.0 and random.random() < 0.2:
            particle_mgr.burst_sparks(self.x, self.y, count=1, color=CYAN_GLOW)

        # Update Mjolnir (passing Thor coordinates for bounded orbit)
        if self.mjolnir.state != "DESKTOP_THROWN":
            catch_event = self.mjolnir.update(
                hand_x,
                hand_y,
                cursor_x,
                cursor_y,
                screen_w,
                screen_h,
                particle_mgr,
                thor_x=self.x,
                thor_y=self.y
            )
            if catch_event == "CAUGHT":
                self.is_summoning = False
                self.state = CharacterState.IDLE
                self.play_timer = now + random.uniform(5.0, 9.0) / max(0.2, config_data.get("activity_level", 1.0))

    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        ctx.save()

        # 1. Flowing Asgardian Cape behind Thor's body
        dir_mult = 1.0 if self.facing_right else -1.0
        self.cape.draw(ctx, self.x - 8 * dir_mult, self.x + 4 * dir_mult, self.y - 14)

        # 2. Thor body
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.rotate(self.tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # Legs & Norse Boots
        ctx.set_source_rgb(0.12, 0.14, 0.20)
        ctx.rectangle(-8, 14, 6, 16)
        ctx.rectangle(2, 14, 6, 16)
        ctx.fill()

        ctx.set_source_rgb(0.65, 0.45, 0.25)
        ctx.rectangle(-9, 26, 8, 8)
        ctx.rectangle(1, 26, 8, 8)
        ctx.fill()

        ctx.set_source_rgb(0.85, 0.88, 0.92)
        ctx.rectangle(-7, 28, 4, 2)
        ctx.rectangle(3, 28, 4, 2)
        ctx.fill()

        # Torso Armor & Silver Discs
        ctx.set_source_rgb(0.20, 0.24, 0.30)
        ctx.rectangle(-11, -8, 22, 24)
        ctx.fill()

        # Megingjörð Golden Belt
        ctx.set_source_rgb(0.95, 0.78, 0.15)
        ctx.rectangle(-12, 11, 24, 4.5)
        ctx.fill()
        ctx.set_source_rgb(0.80, 0.60, 0.10)
        ctx.rectangle(-3, 10, 6, 6.5)
        ctx.fill()

        # 6 Iconic Silver Armor Discs
        ctx.set_source_rgb(0.82, 0.86, 0.92)
        disc_positions = [(-6, -3), (6, -3), (-6, 4), (6, 4), (-5, 9), (5, 9)]
        for dx, dy in disc_positions:
            ctx.arc(dx, dy, 3.2, 0, 2 * math.pi)
            ctx.fill()
            ctx.set_source_rgb(0.4, 0.45, 0.52)
            ctx.set_line_width(0.8)
            ctx.stroke()
            ctx.set_source_rgb(0.82, 0.86, 0.92)

        # Shoulder medallions
        ctx.set_source_rgb(0.95, 0.80, 0.20)
        ctx.arc(-9, -8, 2.8, 0, 2 * math.pi)
        ctx.arc(9, -8, 2.8, 0, 2 * math.pi)
        ctx.fill()

        # Left Arm
        ctx.set_source_rgb(0.12, 0.14, 0.20)
        ctx.rectangle(-15, -6, 5, 16)
        ctx.fill()
        ctx.set_source_rgb(0.82, 0.86, 0.92)
        ctx.rectangle(-15, 4, 5, 6)
        ctx.fill()

        # Right Arm & Mjolnir Grip
        spd = math.hypot(self.vx, self.vy)
        is_held = (self.mjolnir.state == "HELD")

        if self.state == "SUMMONING" or (not is_held and self.mjolnir.state == "RETURNING"):
            # Arm raised forward summoning thunder
            ctx.save()
            ctx.set_source_rgb(0.12, 0.14, 0.20)
            ctx.rectangle(8, -6, 16, 5)
            ctx.fill()
            ctx.set_source_rgb(0.82, 0.86, 0.92)
            ctx.rectangle(15, -6, 7, 5)
            ctx.fill()

            if is_held:
                ctx.save()
                ctx.translate(26, -3.5)
                ctx.rotate(-0.25)
                self.mjolnir.draw_held(ctx, ci=max(0.5, self.mjolnir.charged_intensity), anim_time=self.anim_time)
                ctx.restore()

            # Hand flesh
            ctx.set_source_rgb(0.94, 0.76, 0.62)
            ctx.arc(26, -3.5, 3.5, 0, 2 * math.pi)
            ctx.fill()

            # Crackling energy around palm
            ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], 0.85)
            ctx.arc(26, -3.5, 6.5, 0, 2 * math.pi)
            ctx.set_line_width(1.5)
            ctx.stroke()
            ctx.restore()

        elif not is_held:
            # Arm outstretched directing flying Mjolnir
            ctx.save()
            ctx.set_source_rgb(0.12, 0.14, 0.20)
            ctx.rectangle(8, -5, 14, 5)
            ctx.fill()
            ctx.set_source_rgb(0.82, 0.86, 0.92)
            ctx.rectangle(14, -5, 6, 5)
            ctx.fill()

            # Open palm controlling hammer
            ctx.set_source_rgb(0.94, 0.76, 0.62)
            ctx.arc(22, -2.5, 3.2, 0, 2 * math.pi)
            ctx.fill()

            # Glowing palm aura
            ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], 0.75)
            ctx.arc(22, -2.5, 5.0, 0, 2 * math.pi)
            ctx.set_line_width(1.2)
            ctx.stroke()
            ctx.restore()

        elif spd > 4.0:
            # Flying through the air: Mjolnir extended forward, pulling Thor!
            ctx.save()
            ctx.set_source_rgb(0.12, 0.14, 0.20)
            ctx.rectangle(8, -5, 14, 5)
            ctx.fill()
            ctx.set_source_rgb(0.82, 0.86, 0.92)
            ctx.rectangle(14, -5, 6, 5)
            ctx.fill()

            # Mjolnir held forward in flight
            ctx.save()
            ctx.translate(22, -2.5)
            ctx.rotate(1.25)
            self.mjolnir.draw_held(ctx, ci=max(0.35, self.mjolnir.charged_intensity), anim_time=self.anim_time)
            ctx.restore()

            # Fist flesh wrapped around handle
            ctx.set_source_rgb(0.94, 0.76, 0.62)
            ctx.arc(22, -2.5, 3.4, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

        else:
            # Idle / Walking: Arm hanging naturally with Mjolnir held firmly by his side
            ctx.save()
            ctx.set_source_rgb(0.12, 0.14, 0.20)
            ctx.rectangle(10, -6, 5, 16)
            ctx.fill()
            ctx.set_source_rgb(0.82, 0.86, 0.92)
            ctx.rectangle(10, 4, 5, 6)
            ctx.fill()

            # Mjolnir held at side, head resting angled upright
            ctx.save()
            ctx.translate(12.5, 12)
            ctx.rotate(-0.35)
            self.mjolnir.draw_held(ctx, ci=self.mjolnir.charged_intensity, anim_time=self.anim_time)
            ctx.restore()

            # Fist flesh wrapped over handle grip
            ctx.set_source_rgb(0.94, 0.76, 0.62)
            ctx.arc(12.5, 12, 3.2, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

        # Head & Golden Blond Hair
        ctx.set_source_rgb(0.92, 0.78, 0.25)
        ctx.arc(0, -14, 11, 0, 2 * math.pi)
        ctx.fill()

        # Face & Norse Beard
        ctx.set_source_rgb(0.94, 0.76, 0.62)
        ctx.rectangle(-7, -18, 14, 11)
        ctx.fill()

        ctx.set_source_rgb(0.92, 0.78, 0.25)
        ctx.new_path()
        ctx.move_to(-7, -11)
        ctx.line_to(7, -11)
        ctx.line_to(4, -6)
        ctx.line_to(0, -4)
        ctx.line_to(-4, -6)
        ctx.close_path()
        ctx.fill()

        # Glowing Thunder Eyes
        glow_a = min(1.0, max(0.2, self.eyes_glow))
        ctx.set_source_rgba(CYAN_GLOW[0], CYAN_GLOW[1], CYAN_GLOW[2], glow_a)
        ctx.arc(-2.5, -14.5, 2.2, 0, 2 * math.pi)
        ctx.arc(3.5, -14.5, 2.2, 0, 2 * math.pi)
        ctx.fill()

        ctx.set_source_rgba(1.0, 1.0, 1.0, glow_a)
        ctx.arc(-2.5, -14.5, 1.0, 0, 2 * math.pi)
        ctx.arc(3.5, -14.5, 1.0, 0, 2 * math.pi)
        ctx.fill()

        # Winged Silver Helmet
        pat_helm = cairo.LinearGradient(0, -26, 0, -14)
        pat_helm.add_color_stop_rgb(0.0, 0.92, 0.94, 0.98)
        pat_helm.add_color_stop_rgb(1.0, 0.58, 0.64, 0.72)
        ctx.set_source(pat_helm)
        ctx.arc(0, -18, 9, math.pi, 2 * math.pi)
        ctx.fill()

        ctx.set_source_rgb(0.95, 0.80, 0.18)
        ctx.rectangle(-9, -19, 18, 2.5)
        ctx.fill()

        # Wings on Helmet
        for side in [-1, 1]:
            ctx.save()
            ctx.translate(side * 8, -21)
            ctx.rotate(side * 0.35)
            ctx.set_source_rgb(0.90, 0.93, 0.97)
            ctx.new_path()
            ctx.move_to(0, 0)
            ctx.line_to(side * 12, -9)
            ctx.line_to(side * 14, -6)
            ctx.line_to(side * 9, -1)
            ctx.line_to(side * 11, 2)
            ctx.line_to(0, 3)
            ctx.close_path()
            ctx.fill()
            ctx.set_source_rgb(0.4, 0.45, 0.52)
            ctx.set_line_width(0.8)
            ctx.stroke()
            ctx.restore()

        ctx.restore()

        # 3. Airborne Mjolnir (Orbiting / Thrown / Returning)
        if self.mjolnir.state != "DESKTOP_THROWN":
            self.mjolnir.draw(ctx)

        ctx.restore()


# Register Thor skin with the manager
skin_manager.register("thor", ThorCharacter)
