"""Dragon character: high-performance, 100% procedural vector Cairo dreadwyrm companion.
Crafted with realistic pitch-black obsidian anatomy: perfectly coordinated bat wings anchored
at the shoulders, sinuous barbed tail, chiseled skull with swept horns, razor ivory fangs,
piercing molten-gold eye, and incandescent fire breath.
Supports automatic perching/seating when stopping, sleeping/napping with soft embers,
roaring, and billowing flame breath.
Strictly 0 external bitmaps/PNGs — sub-millisecond draw time, zero asset memory overhead.
"""

import math
import random
import time
from typing import Tuple, Dict, Any, List
import cairo

from skins.base import BaseCharacter, CharacterState
from core.particles import ParticleManager, FIRE_ORANGE, FIRE_YELLOW
from core.projectiles import DesktopProjectileWindow

# Module-level surface cache kept for API & test compatibility (zero bitmap memory)
_DRAGON_SURFACE_CACHE: Dict[str, Any] = {
    "fly_surfaces": ["vector_dreadwyrm_flight_rig"],
    "seat_surfaces": ["vector_dreadwyrm_seated_rig"],
    "fly_w": 260,
    "fly_h": 260,
    "seat_w": 260,
    "seat_h": 260,
    "loaded": True
}


class DragonCharacter(BaseCharacter):
    """Mythical pitch-black dreadwyrm companion rendered purely with high-fidelity
    procedural Cairo vector mathematics: realistic obsidian scales, coordinated bat wings,
    sinuous barbed tail, chiseled horns, gripping talons, automatic seated resting,
    sleeping postures, and incandescent flame stream.
    """

    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="dragon")
        self.can_fly = True
        self.hitbox_radius = 52.0

        # Articulated wing flapping & anatomy kinematics
        self.wing_angle = 0.0
        self.back_wing_angle = 0.0
        self.wing_speed = 0.22
        self.tail_wave = 0.0
        self.paw_step = 0.0
        self.jaw_open = 0.0

        # Abilities & personality timers
        self.is_breathing_fire = False
        self.fire_end_time = 0.0
        self.action_timer = time.time() + random.uniform(4.0, 8.0)

        # Dynamic behavioral postures: Seated resting vs Sleeping vs Soaring flight
        self.is_seated = False
        self.is_sleeping = False
        self.stationary_time = 0.0
        self.sleep_timer = 0.0
        self.head_lower = 0.0
        self.hand_motion = 0.0
        self.tail_motion = 0.0
        self.hand_step = 0.0
        self.blink_state = 0.0
        self.blink_timer = time.time() + random.uniform(2.5, 5.0)

        # Surface cache references for backward-compatibility
        self.fly_surfaces = _DRAGON_SURFACE_CACHE["fly_surfaces"]
        self.seat_surfaces = _DRAGON_SURFACE_CACHE["seat_surfaces"]
        self.fly_w = _DRAGON_SURFACE_CACHE["fly_w"]
        self.fly_h = _DRAGON_SURFACE_CACHE["fly_h"]
        self.seat_w = _DRAGON_SURFACE_CACHE["seat_w"]
        self.seat_h = _DRAGON_SURFACE_CACHE["seat_h"]

    @classmethod
    def _ensure_surfaces_loaded(cls) -> None:
        """Procedural engine requires zero disk I/O; cache flag is immediately ready."""
        global _DRAGON_SURFACE_CACHE
        _DRAGON_SURFACE_CACHE["loaded"] = True

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: ParticleManager,
        audio_mgr: Any
    ) -> bool:
        if not audio_mgr:
            from core.audio import audio_manager
            audio_mgr = audio_manager

        dir_mult = 1.0 if self.facing_right else -1.0
        mouth_x = self.x + dir_mult * (48.0 if not self.is_seated else 42.0)
        mouth_y = self.y + (14.0 if not self.is_seated else -18.0)

        if ability_name in ("fire_breath", "breath"):
            self.is_sleeping = False
            self.is_breathing_fire = True
            self.fire_end_time = time.time() + 1.8
            self.jaw_open = 1.0
            self.blink_state = 0.0
            audio_mgr.play("fire")
            particle_mgr.flame_puff(mouth_x, mouth_y, vx=dir_mult * 22.0, vy=0.0, count=8, size=10.5)
            particle_mgr.burst_sparks(mouth_x, mouth_y, count=10, color=(1.0, 0.75, 0.2), size=3.2)
            return True

        elif ability_name == "fireball":
            self.is_sleeping = False
            self.jaw_open = 1.0
            self.blink_state = 0.0
            def _on_catch():
                particle_mgr.flame_puff(self.x + dir_mult * 32.0, self.y, count=9, size=8.5)

            DesktopProjectileWindow(
                proj_type="fireball",
                start_x=mouth_x,
                start_y=mouth_y,
                target_x=target_x,
                target_y=target_y,
                owner_getter=lambda: (self.x + (32.0 if self.facing_right else -32.0), self.y),
                on_catch=_on_catch,
                speed=26.0
            )
            audio_mgr.play("fire")
            particle_mgr.flame_puff(mouth_x, mouth_y, count=7, size=8.5)
            return True

        elif ability_name in ("flight", "glide"):
            self.is_seated = False
            self.is_sleeping = False
            self.blink_state = 0.0
            self.vy -= 9.5
            self.state = CharacterState.FLY
            particle_mgr.smoke_puff(self.x, self.y + 16, count=6)
            audio_mgr.play("swoosh")
            return True

        elif ability_name in ("seat", "sit"):
            self.is_seated = True
            self.state = CharacterState.IDLE
            self.vy = 0.0
            self.wing_angle = 0.28
            self.back_wing_angle = 0.24
            particle_mgr.smoke_puff(self.x, self.y + 20, count=4)
            return True

        elif ability_name == "sleep":
            self.is_seated = True
            self.is_sleeping = True
            self.state = CharacterState.IDLE
            self.blink_state = 1.0
            self.vy = 0.0
            self.wing_angle = 0.28
            self.back_wing_angle = 0.24
            particle_mgr.smoke_puff(self.x, self.y + 10, count=2)
            return True

        elif ability_name == "wake":
            self.is_sleeping = False
            self.blink_state = 0.0
            self.head_lower = 0.0
            return True

        elif ability_name == "roar":
            self.is_sleeping = False
            self.jaw_open = 1.0
            self.blink_state = 0.0
            audio_mgr.play("roar")
            particle_mgr.shockwave(mouth_x, mouth_y, max_radius=80.0, color=(1.0, 0.45, 0.1))
            particle_mgr.flame_puff(mouth_x, mouth_y, count=8, size=9.5)
            particle_mgr.burst_sparks(mouth_x, mouth_y, count=12, color=(1.0, 0.8, 0.2), size=3.0)
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
        speed_mult = config_data.get("speed", 1.0)
        ground_y = min_y + screen_h - 75.0

        # Living draconic biological motions
        self.tail_motion = math.sin(self.anim_time * 2.8) * 4.5
        self.tail_wave = math.sin(self.anim_time * 3.5) * 5.5
        self.hand_motion = math.sin(self.anim_time * 4.2) * 5.0
        self.hand_step = math.sin(self.anim_time * 6.5) * 6.0

        # Eye blink cycle when awake
        if not self.is_sleeping:
            if now >= self.blink_timer:
                self.blink_state = 1.0
                if now >= self.blink_timer + 0.12:
                    self.blink_state = 0.0
                    self.blink_timer = now + random.uniform(3.0, 6.5)
            else:
                self.blink_state = 0.0
        else:
            self.blink_state = 1.0  # Closed eyes when sleeping

        dx = cursor_x - self.x
        dy = cursor_y - self.y
        dist = math.hypot(dx, dy)
        dist_x = abs(dx)

        # Facing direction
        if dist_x > 6.0 and not self.is_sleeping:
            self.facing_right = (cursor_x >= self.x)
        dir_mult = 1.0 if self.facing_right else -1.0

        mouth_x = self.x + dir_mult * (48.0 if not self.is_seated else 42.0)
        mouth_y = self.y + (14.0 if not self.is_seated else -18.0)

        # Continuous fire breath stream
        if self.is_breathing_fire:
            self.jaw_open = min(1.0, self.jaw_open + 0.3)
            particle_mgr.flame_puff(
                mouth_x,
                mouth_y,
                vx=dir_mult * random.uniform(15.0, 25.0),
                vy=random.uniform(-3.5, 3.5),
                count=3,
                size=random.uniform(8.0, 13.0)
            )
            if random.random() < 0.45:
                particle_mgr.burst_sparks(
                    mouth_x,
                    mouth_y,
                    count=2,
                    color=(1.0, 0.75, 0.15),
                    size=2.8
                )
            if now >= self.fire_end_time:
                self.is_breathing_fire = False
        else:
            self.jaw_open = max(0.0, self.jaw_open - 0.15)

        # Autonomous abilities when active
        if activity > 0.1 and now >= self.action_timer:
            self.action_timer = now + random.uniform(5.0, 11.0) / max(0.2, activity)
            if self.is_sleeping:
                # Wake up with a small nostril puff or stretch
                if random.random() < 0.35:
                    self.is_sleeping = False
            else:
                r = random.random()
                if r < 0.45:
                    self.trigger_ability("fire_breath", cursor_x, cursor_y, particle_mgr, audio_mgr)
                elif r < 0.75:
                    self.trigger_ability("roar", cursor_x, cursor_y, particle_mgr, audio_mgr)
                elif not self.is_seated and r < 0.90:
                    self.trigger_ability("fireball", cursor_x, cursor_y, particle_mgr, audio_mgr)

        # FLIGHT, HOVER, WALK, SEATED, AND SLEEPING DYNAMICS
        is_on_ground = (self.y >= ground_y - 3.0)
        cursor_on_ground = (cursor_y >= ground_y - 20.0)

        if dist > 60.0:
            # Cursor is away -> Active pursuit!
            self.is_seated = False
            self.is_sleeping = False
            self.stationary_time = 0.0
            self.head_lower = 0.0

            if is_on_ground and cursor_on_ground:
                # Walking stride along the ground
                self.state = CharacterState.WALK
                self.paw_step += 0.14 * speed_mult
                self.wing_angle = 0.22 + math.sin(self.anim_time * 2.0) * 0.05
                self.back_wing_angle = 0.20
                target_vx = (1.0 if dx > 0 else -1.0) * min(7.0, max(2.0, dist_x * 0.06)) * speed_mult
                self.vx += (target_vx - self.vx) * 0.18
                self.vy = 0.0
                self.y = ground_y
            else:
                # Soaring flight!
                self.state = CharacterState.FLY
                target_vx = (dx / dist) * min(9.0, max(2.5, dist * 0.055)) * speed_mult
                target_vy = (dy / dist) * min(7.0, max(2.0, dist * 0.045)) * speed_mult
                self.vx += (target_vx - self.vx) * 0.14
                self.vy += (target_vy - self.vy) * 0.14

                spd = math.hypot(self.vx, self.vy)
                flap_speed = min(0.32, max(0.16, spd * 0.032)) * speed_mult
                self.wing_angle = math.sin(self.anim_time * flap_speed * 20.0) * 0.48
                self.back_wing_angle = math.sin(self.anim_time * flap_speed * 20.0 - 0.40) * 0.42

        else:
            # Cursor is near (peaceful touch / petting deadzone)
            self.vx *= 0.82
            self.vy *= 0.82
            self.stationary_time += dt

            # If resting undisturbed near cursor for > 2.0s, smoothly perch/seat
            if self.stationary_time > 2.0:
                self.is_seated = True
                self.state = CharacterState.IDLE
                self.wing_angle = 0.28
                self.back_wing_angle = 0.24

                # If left undisturbed seated for > 5.0s, fall asleep peacefully
                if self.stationary_time > 5.0:
                    self.is_sleeping = True
                    self.blink_state = 1.0
                    self.head_lower += (3.5 - self.head_lower) * 0.12
                    # Gentle sleeping smoke ember from nostril
                    if random.random() < 0.035:
                        particle_mgr.smoke_puff(mouth_x, mouth_y - 2, count=1)
                else:
                    self.head_lower += (0.0 - self.head_lower) * 0.15
            else:
                # Gentle hovering / idle near cursor
                self.is_seated = False
                self.is_sleeping = False
                self.head_lower = 0.0
                if is_on_ground:
                    self.state = CharacterState.IDLE
                else:
                    self.state = CharacterState.HOVER
                    self.wing_angle = math.sin(self.anim_time * 3.0) * 0.22
                    self.back_wing_angle = math.sin(self.anim_time * 3.0 - 0.35) * 0.18

        self.x += self.vx
        self.y += self.vy

        # Screen boundary clamp (fly freely across screen, down to ground)
        self.x = max(min_x + 60.0, min(min_x + screen_w - 60.0, self.x))
        self.y = max(min_y + 60.0, min(ground_y, self.y))

        # Dynamic body tilt (banking in flight)
        target_tilt = (self.vx / 8.0) * 0.26 if not self.is_seated else 0.0
        self.tilt += (target_tilt - self.tilt) * 0.16


    def draw(self, ctx: cairo.Context, particle_mgr: ParticleManager) -> None:
        """Renders the realistic pitch-black dreadwyrm purely in Cairo vector mathematics.
        Both wings are anatomically unified at the shoulders, sweeping in coordinated harmony in flight
        and folding symmetrically when seated/sleeping.
        """
        ctx.save()

        # Position and scale
        hover_y = math.sin(self.anim_time * 3.5) * 3.5 if (self.state in (CharacterState.FLY, CharacterState.HOVER) and not self.is_seated) else 0.0
        ctx.translate(self.x, self.y + hover_y)
        ctx.rotate(self.tilt)
        ctx.scale(self.scale, self.scale)
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # Dramatic size multiplier to fill window nicely
        s = 1.15
        ctx.scale(s, s)

        is_seated_pose = self.is_seated and (self.state not in (CharacterState.FLY, CharacterState.HOVER))
        state_name = "IDLE" if is_seated_pose else ("WALK" if self.state == CharacterState.WALK else "FLY")

        # -------------------------------------------------------------
        # 1. FAR (BACK) WING — Anchored at Shoulder (-2, -9)
        # -------------------------------------------------------------
        ctx.save()
        ctx.translate(-2, -9 + self.head_lower * 0.3)
        scale_b = 0.88
        ctx.scale(scale_b, scale_b)

        if is_seated_pose or state_name == "WALK":
            # Folded back wing silhouette (peeking neatly behind upper flank)
            ctx.set_source_rgba(0.06, 0.06, 0.08, 0.95)
            ctx.new_path()
            ctx.move_to(0, 0)
            ctx.curve_to(-8, -14, -20, -17, -26, -15)
            ctx.curve_to(-22, -4, -14, 8, -4, 13)
            ctx.curve_to(0, 8, 2, 2, 0, 0)
            ctx.close_path()
            ctx.fill_preserve()
            ctx.set_source_rgba(0.18, 0.18, 0.22, 0.8)
            ctx.set_line_width(1.0)
            ctx.stroke()
        else:
            # Airborne Back Wing (Unified orientation with Fore Wing!)
            b_flap = self.back_wing_angle
            ctx.rotate(b_flap)

            elbow = (-14, -30)
            wrist = (10, -52)
            f1 = (36, -50)
            f2 = (22, -32)
            f3 = (4, -16)

            ctx.new_path()
            ctx.move_to(0, 0)
            ctx.line_to(elbow[0], elbow[1])
            ctx.line_to(wrist[0], wrist[1])
            ctx.line_to(f1[0], f1[1])
            ctx.curve_to(30, -38, 28, -34, f2[0], f2[1])
            ctx.curve_to(16, -24, 10, -18, f3[0], f3[1])
            ctx.curve_to(-4, -6, -6, 2, 0, 0)
            ctx.close_path()

            pat_bwing = cairo.LinearGradient(wrist[0], wrist[1], f3[0], f3[1])
            pat_bwing.add_color_stop_rgba(0.0, 0.09, 0.09, 0.12, 0.95)
            pat_bwing.add_color_stop_rgba(0.5, 0.04, 0.02, 0.02, 0.92)
            pat_bwing.add_color_stop_rgba(1.0, 0.02, 0.02, 0.03, 0.96)
            ctx.set_source(pat_bwing)
            ctx.fill_preserve()
            ctx.set_source_rgba(0.01, 0.01, 0.02, 0.95)
            ctx.set_line_width(1.1)
            ctx.stroke()

            # Back wing skeletal bone struts
            ctx.set_source_rgba(0.14, 0.14, 0.18, 0.95)
            ctx.set_line_width(2.4)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(0, 0)
            ctx.line_to(elbow[0], elbow[1])
            ctx.line_to(wrist[0], wrist[1])
            ctx.stroke()
            ctx.set_line_width(1.2)
            for fg in [f1, f2, f3]:
                ctx.move_to(wrist[0], wrist[1])
                ctx.line_to(fg[0], fg[1])
                ctx.stroke()
        ctx.restore()

        # -------------------------------------------------------------
        # 2. SINUOUS BARBED OBSIDIAN TAIL
        # -------------------------------------------------------------
        ctx.save()
        tail_pts = [
            (-14, 5),
            (-26, 7 + self.tail_wave * 0.35),
            (-40, 8 + self.tail_wave * 0.75),
            (-55, 6 + self.tail_wave * 1.25),
            (-68, 2 + self.tail_wave * 1.70)
        ]
        if is_seated_pose:
            # Curled restfully along the ground
            tail_pts = [
                (-14, 10),
                (-24, 16),
                (-30, 22),
                (-18, 26),
                (-4, 25)
            ]

        # Draw tapered segmented tail with overlapping scales
        for i in range(len(tail_pts) - 1):
            p1 = tail_pts[i]
            p2 = tail_pts[i+1]
            thick = max(2.0, 7.0 - i * 1.25)

            ctx.save()
            pat_tail = cairo.LinearGradient(p1[0], p1[1], p2[0], p2[1])
            pat_tail.add_color_stop_rgb(0.0, 0.11, 0.11, 0.14)
            pat_tail.add_color_stop_rgb(1.0, 0.03, 0.03, 0.05)
            ctx.set_source(pat_tail)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_width(thick)
            ctx.move_to(p1[0], p1[1])
            ctx.line_to(p2[0], p2[1])
            ctx.stroke()

            # Razor dorsal spine scales along tail
            if i < len(tail_pts) - 2 and not is_seated_pose:
                ctx.set_source_rgb(0.18, 0.18, 0.22)
                ctx.new_path()
                ctx.move_to(p1[0], p1[1] - thick * 0.4)
                ctx.line_to(p1[0] - 2, p1[1] - thick * 0.8 - 3.0)
                ctx.line_to(p1[0] + 2, p1[1] - thick * 0.4)
                ctx.close_path()
                ctx.fill()
            ctx.restore()

        # Obsidian Barbed Spade Blade at Tail Tip
        tip = tail_pts[-1]
        ctx.save()
        ctx.translate(tip[0], tip[1])
        blade_ang = math.atan2(tail_pts[-1][1] - tail_pts[-2][1], tail_pts[-1][0] - tail_pts[-2][0])
        ctx.rotate(blade_ang)

        # Sharp double-barbed arrowhead blade
        ctx.set_source_rgb(0.12, 0.12, 0.15)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.line_to(-12, -5.5)
        ctx.line_to(-8, 0)
        ctx.line_to(-12, 5.5)
        ctx.close_path()
        ctx.fill_preserve()
        ctx.set_source_rgba(0.4, 0.45, 0.55, 0.85)
        ctx.set_line_width(0.9)
        ctx.stroke()
        ctx.restore()
        ctx.restore()

        # -------------------------------------------------------------
        # 3. HIND LEGS & CURVED OBSIDIAN TALONS
        # -------------------------------------------------------------
        ctx.save()
        if is_seated_pose:
            ctx.translate(-10, 12)
            pat_thigh = cairo.RadialGradient(0, 0, 2, 0, 0, 10)
            pat_thigh.add_color_stop_rgb(0.0, 0.18, 0.18, 0.22)
            pat_thigh.add_color_stop_rgb(1.0, 0.04, 0.04, 0.06)
            ctx.set_source(pat_thigh)
            ctx.arc(0, 0, 9, 0, 2 * math.pi)
            ctx.fill()

            # Gripping claws on ground
            ctx.set_source_rgb(0.06, 0.06, 0.08)
            ctx.rectangle(-4, 6, 8, 4)
            ctx.fill()
            for cx in [-3, 0, 3]:
                ctx.set_source_rgb(0.01, 0.01, 0.02)
                ctx.new_path()
                ctx.move_to(cx, 10)
                ctx.line_to(cx + 2.5, 14.5)
                ctx.line_to(cx - 1, 10)
                ctx.close_path()
                ctx.fill()
        else:
            walk_offset = math.sin(self.paw_step * 3.0) * 5.0 if state_name == "WALK" else 0.0
            leg_rot = -0.38 if state_name == "FLY" else (walk_offset * 0.08)
            ctx.translate(-11, 7)
            ctx.rotate(leg_rot)

            # Muscular thigh with specular ridge
            pat_thigh = cairo.RadialGradient(0, 0, 2, 0, 0, 9)
            pat_thigh.add_color_stop_rgb(0.0, 0.20, 0.20, 0.25)
            pat_thigh.add_color_stop_rgb(1.0, 0.04, 0.04, 0.06)
            ctx.set_source(pat_thigh)
            ctx.save()
            ctx.scale(1.15, 0.92)
            ctx.arc(0, 0, 8.0, 0, 2 * math.pi)
            ctx.fill()
            ctx.restore()

            # Hock and lower leg
            ctx.set_source_rgb(0.09, 0.09, 0.12)
            ctx.set_line_width(4.0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(0, 4)
            ctx.line_to(2 if state_name != "WALK" else walk_offset, 15)
            ctx.stroke()

            # Curved razor talons
            foot_x = 2 if state_name != "WALK" else walk_offset
            for tx in [-2.5, 0, 2.5]:
                ctx.set_source_rgb(0.01, 0.01, 0.02)
                ctx.new_path()
                ctx.move_to(foot_x + tx, 15)
                ctx.line_to(foot_x + tx + 3.0, 19.5)
                ctx.line_to(foot_x + tx - 1.0, 15)
                ctx.close_path()
                ctx.fill_preserve()
                ctx.set_source_rgba(0.45, 0.50, 0.60, 0.8)
                ctx.set_line_width(0.6)
                ctx.stroke()
        ctx.restore()

        # -------------------------------------------------------------
        # 4. MAIN TORSO & UNDERBELLY SCUTES
        # -------------------------------------------------------------
        ctx.save()
        pat_body = cairo.LinearGradient(-18, -14, 18, 14)
        pat_body.add_color_stop_rgb(0.0, 0.22, 0.22, 0.27)   # Top specular spine ridge
        pat_body.add_color_stop_rgb(0.35, 0.11, 0.11, 0.14)  # Mid flank scales
        pat_body.add_color_stop_rgb(1.0, 0.02, 0.02, 0.04)   # Deep shadow underbelly
        ctx.set_source(pat_body)

        # Anatomical predatory drake body
        ctx.new_path()
        ctx.move_to(-16, 5)
        ctx.curve_to(-18, -5, -8, -14, 6, -12)  # Arched muscular spine
        ctx.curve_to(18, -9, 20, 2, 14, 9)      # Muscular pectoral chest
        ctx.curve_to(6, 15, -6, 14, -16, 5)     # Abdominal belly
        ctx.close_path()
        ctx.fill_preserve()

        ctx.set_source_rgba(0.32, 0.35, 0.42, 0.5)
        ctx.set_line_width(1.0)
        ctx.stroke()

        # Overlapping Armor Scutes with breathing motion (slower deep breath when sleeping)
        breath_rate = 1.6 if self.is_sleeping else 2.6
        breath = math.sin(self.anim_time * breath_rate) * (1.1 if self.is_sleeping else 0.85)
        for si, (sc_x, sc_y, sc_w) in enumerate([(-10, 8, 8), (-4, 10 + breath * 0.4, 9), (3, 10 + breath * 0.7, 10), (9, 8 + breath * 0.4, 9)]):
            ctx.save()
            ctx.translate(sc_x, sc_y)
            ctx.set_source_rgba(0.14, 0.14, 0.18, 0.95)
            ctx.rectangle(-sc_w * 0.5, 0, sc_w, 3.2)
            ctx.fill()
            ctx.set_source_rgba(0.02, 0.02, 0.03, 0.95)
            ctx.set_line_width(0.8)
            ctx.stroke()
            ctx.restore()

        # Dorsal Spine Ridge Plates along back
        for di, (dx, dy) in enumerate([(-12, -9), (-6, -13), (1, -13), (8, -11)]):
            ctx.save()
            ctx.translate(dx, dy)
            ctx.set_source_rgb(0.24, 0.24, 0.30)
            ctx.new_path()
            ctx.move_to(-2.5, 2)
            ctx.line_to(0, -5.0 - di * 0.35)
            ctx.line_to(2.5, 2)
            ctx.close_path()
            ctx.fill()
            ctx.restore()
        ctx.restore()

        # -------------------------------------------------------------
        # 5. FORELEG & FRONT TALONS
        # -------------------------------------------------------------
        ctx.save()
        if is_seated_pose:
            ctx.translate(11, 11)
            ctx.set_source_rgb(0.11, 0.11, 0.14)
            ctx.rectangle(-3, 0, 6, 13)
            ctx.fill()
            for cx in [-2, 0, 2]:
                ctx.set_source_rgb(0.01, 0.01, 0.02)
                ctx.new_path()
                ctx.move_to(cx, 13)
                ctx.line_to(cx + 2.5, 17)
                ctx.line_to(cx - 1.0, 13)
                ctx.close_path()
                ctx.fill()
        else:
            front_offset = -math.sin(self.paw_step * 3.0) * 5.0 if state_name == "WALK" else 0.0
            fore_rot = 0.38 if state_name == "FLY" else (front_offset * 0.08)
            ctx.translate(11, 7)
            ctx.rotate(fore_rot)

            # Shoulder Armor Plate
            ctx.set_source_rgb(0.16, 0.16, 0.20)
            ctx.arc(0, 0, 6.0, 0, 2 * math.pi)
            ctx.fill()

            # Forearm
            ctx.set_source_rgb(0.10, 0.10, 0.13)
            ctx.set_line_width(3.6)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(0, 2)
            ctx.line_to(2 if state_name != "WALK" else front_offset, 13)
            ctx.stroke()

            # Reaching predatory talons
            cl_x = 2 if state_name != "WALK" else front_offset
            for cx in [-2, 0, 2]:
                ctx.set_source_rgb(0.01, 0.01, 0.02)
                ctx.new_path()
                ctx.move_to(cl_x + cx, 13)
                ctx.line_to(cl_x + cx + 3.2, 17.5)
                ctx.line_to(cl_x + cx - 0.9, 13)
                ctx.close_path()
                ctx.fill_preserve()
                ctx.set_source_rgba(0.45, 0.50, 0.60, 0.8)
                ctx.set_line_width(0.6)
                ctx.stroke()
        ctx.restore()

        # -------------------------------------------------------------
        # 6. FORE WING — Anchored at Shoulder (3, -9)
        # -------------------------------------------------------------
        ctx.save()
        ctx.translate(3, -9 + self.head_lower * 0.3)

        if is_seated_pose or state_name == "WALK":
            # Folded fore wing neatly tucked along the flank
            ctx.set_source_rgb(0.14, 0.14, 0.18)
            ctx.new_path()
            ctx.move_to(0, 0)
            ctx.curve_to(-8, -14, -20, -18, -28, -16)
            ctx.curve_to(-24, -4, -15, 10, -4, 15)
            ctx.curve_to(0, 9, 2, 2, 0, 0)
            ctx.close_path()
            ctx.fill_preserve()
            ctx.set_source_rgba(0.32, 0.36, 0.44, 0.6)
            ctx.set_line_width(1.1)
            ctx.stroke()

            # Folded skeletal bone ridges
            ctx.set_source_rgb(0.20, 0.20, 0.25)
            ctx.set_line_width(2.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(0, 0)
            ctx.line_to(-28, -16)
            ctx.line_to(-4, 15)
            ctx.stroke()
        else:
            # Grand sweeping airborne flight beat
            flap = self.wing_angle
            ctx.rotate(flap)

            elbow = (-14, -30)
            wrist = (10, -52)
            f1 = (36, -50)
            f2 = (22, -32)
            f3 = (4, -16)

            # Wing Membrane Silhouette
            ctx.new_path()
            ctx.move_to(0, 0)
            ctx.line_to(elbow[0], elbow[1])
            ctx.line_to(wrist[0], wrist[1])
            ctx.line_to(f1[0], f1[1])
            ctx.curve_to(30, -38, 28, -34, f2[0], f2[1])
            ctx.curve_to(16, -24, 10, -18, f3[0], f3[1])
            ctx.curve_to(-4, -6, -6, 2, 0, 0)
            ctx.close_path()

            pat_wing = cairo.LinearGradient(wrist[0], wrist[1], f3[0], f3[1])
            pat_wing.add_color_stop_rgba(0.0, 0.18, 0.18, 0.22, 0.95)
            pat_wing.add_color_stop_rgba(0.45, 0.08, 0.03, 0.03, 0.92)  # subtle dark crimson vein
            pat_wing.add_color_stop_rgba(1.0, 0.02, 0.02, 0.04, 0.96)
            ctx.set_source(pat_wing)
            ctx.fill_preserve()

            ctx.set_source_rgba(0.01, 0.01, 0.02, 0.95)
            ctx.set_line_width(1.2)
            ctx.stroke()

            # Skeletal Humerus and Radius Bones
            ctx.set_source_rgb(0.24, 0.24, 0.29)
            ctx.set_line_width(3.2)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.move_to(0, 0)
            ctx.line_to(elbow[0], elbow[1])
            ctx.line_to(wrist[0], wrist[1])
            ctx.stroke()

            # Elongated finger struts
            ctx.set_line_width(1.6)
            for fg in [f1, f2, f3]:
                ctx.move_to(wrist[0], wrist[1])
                ctx.line_to(fg[0], fg[1])
                ctx.stroke()

            # Alula Thumb Claw
            ctx.set_source_rgb(0.02, 0.02, 0.03)
            ctx.new_path()
            ctx.move_to(wrist[0], wrist[1])
            ctx.line_to(wrist[0] + 4, wrist[1] - 5)
            ctx.line_to(wrist[0] + 1, wrist[1] + 1)
            ctx.close_path()
            ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 7. SERPENTINE NECK & CHISELED SKULL (Resting low if sleeping)
        # -------------------------------------------------------------
        ctx.save()
        ctx.translate(14, -6 + self.head_lower)

        # Sinuous muscular neck
        pat_neck = cairo.LinearGradient(0, 4, 16, -10)
        pat_neck.add_color_stop_rgb(0.0, 0.18, 0.18, 0.22)
        pat_neck.add_color_stop_rgb(1.0, 0.05, 0.05, 0.07)
        ctx.set_source(pat_neck)
        ctx.set_line_width(10.0)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(0, 4)
        ctx.curve_to(6, 2, 11, -5, 16, -10)
        ctx.stroke()

        # Neck armor spines
        ctx.set_source_rgb(0.24, 0.24, 0.30)
        for nx, ny in [(5, -1), (11, -7)]:
            ctx.new_path()
            ctx.move_to(nx - 1, ny + 1)
            ctx.line_to(nx - 2, ny - 4.5)
            ctx.line_to(nx + 1, ny)
            ctx.close_path()
            ctx.fill()

        # Chiseled Skull Pivot at (16, -10)
        ctx.translate(16, -10)
        if self.is_sleeping:
            ctx.rotate(0.18)  # Gentle downward sleeping head tilt

        # Sweeping Horns curving backwards over neck
        ctx.save()
        # Back Horn
        ctx.set_source_rgb(0.08, 0.08, 0.10)
        ctx.new_path()
        ctx.move_to(-2, -4)
        ctx.curve_to(-12, -14, -22, -18, -32, -20)
        ctx.curve_to(-22, -15, -10, -7, 0, -2)
        ctx.close_path()
        ctx.fill()

        # Fore Horn (long ribbed obsidian blade horn)
        ctx.set_source_rgb(0.16, 0.16, 0.20)
        ctx.new_path()
        ctx.move_to(1, -3)
        ctx.curve_to(-10, -14, -20, -20, -30, -24)
        ctx.curve_to(-18, -16, -6, -7, 3, -1)
        ctx.close_path()
        ctx.fill_preserve()
        ctx.set_source_rgba(0.40, 0.44, 0.52, 0.75)
        ctx.set_line_width(0.8)
        ctx.stroke()
        ctx.restore()

        # Predatory Cranium & Snout
        pat_head = cairo.LinearGradient(0, -7, 18, 3)
        pat_head.add_color_stop_rgb(0.0, 0.22, 0.22, 0.27)  # Brow specular highlight
        pat_head.add_color_stop_rgb(0.55, 0.12, 0.12, 0.15) # Muzzle
        pat_head.add_color_stop_rgb(1.0, 0.03, 0.03, 0.05)  # Nostril/throat
        ctx.set_source(pat_head)

        ctx.new_path()
        ctx.move_to(-1, -6)                   # Crown
        ctx.curve_to(6, -7, 13, -5, 20, -1)   # Slender predatory bridge
        ctx.line_to(22, 2)                    # Snout tip
        ctx.line_to(9, 2.5)                   # Upper jawline
        ctx.line_to(0, 4)                     # Throat junction
        ctx.close_path()
        ctx.fill_preserve()
        ctx.set_source_rgba(0.35, 0.38, 0.45, 0.6)
        ctx.set_line_width(0.9)
        ctx.stroke()

        # Nostril
        ctx.set_source_rgb(0.01, 0.01, 0.02)
        ctx.arc(18, 0, 1.3, 0, 2 * math.pi)
        ctx.fill()

        # Razor ivory upper fangs
        ctx.set_source_rgb(0.94, 0.92, 0.86)
        for fx in [13, 17]:
            ctx.new_path()
            ctx.move_to(fx, 2.5)
            ctx.line_to(fx + 1.0, 5.8)
            ctx.line_to(fx - 0.8, 2.5)
            ctx.close_path()
            ctx.fill()

        # Articulated Lower Jaw
        jaw_ang = self.jaw_open * 0.48 if (self.jaw_open > 0.1 or self.is_breathing_fire) else 0.0
        ctx.save()
        ctx.translate(4, 2.5)
        ctx.rotate(jaw_ang)

        ctx.set_source_rgb(0.09, 0.09, 0.12)
        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.line_to(15, 1)
        ctx.line_to(13, 4.5)
        ctx.line_to(0, 3.5)
        ctx.close_path()
        ctx.fill()

        # Lower ivory fangs
        ctx.set_source_rgb(0.94, 0.92, 0.86)
        ctx.new_path()
        ctx.move_to(12, 1)
        ctx.line_to(12.8, -2.5)
        ctx.line_to(13.6, 1)
        ctx.close_path()
        ctx.fill()
        ctx.restore()

        # -------------------------------------------------------------
        # 8. INCANDESCENT MAGMA THROAT CORE & BILLOWING FLAME JET
        # -------------------------------------------------------------
        if self.is_breathing_fire or self.jaw_open > 0.4:
            # Magma throat core
            ctx.save()
            pat_throat = cairo.RadialGradient(10, 2.5, 0.5, 10, 2.5, 12.0)
            pat_throat.add_color_stop_rgba(0.0, 1.0, 1.0, 0.85, 1.0)    # Blinding white-hot center
            pat_throat.add_color_stop_rgba(0.35, 1.0, 0.60, 0.10, 0.95) # Molten orange
            pat_throat.add_color_stop_rgba(0.75, 0.95, 0.20, 0.02, 0.6)  # Crimson halo
            pat_throat.add_color_stop_rgba(1.0, 0.2, 0.02, 0.0, 0.0)
            ctx.set_source(pat_throat)
            ctx.arc(10, 2.5, 12.0, 0, 2 * math.pi)
            ctx.fill()

            # Flame stream billowing out of the open mouth
            ctx.translate(22, 2.0)
            pat_flame = cairo.LinearGradient(0, 0, 48, 0)
            pat_flame.add_color_stop_rgba(0.0, 1.0, 0.95, 0.4, 0.95)
            pat_flame.add_color_stop_rgba(0.4, 1.0, 0.45, 0.05, 0.85)
            pat_flame.add_color_stop_rgba(1.0, 0.85, 0.1, 0.0, 0.0)
            ctx.set_source(pat_flame)

            ctx.new_path()
            ctx.move_to(0, -2)
            ctx.curve_to(16, -9, 32, -13, 48, -2)
            ctx.curve_to(36, 9, 22, 11, 0, 3)
            ctx.close_path()
            ctx.fill()
            ctx.restore()

        # -------------------------------------------------------------
        # 9. PIERCING MOLTEN-GOLD DRAKE EYE (Or sleeping slit lid)
        # -------------------------------------------------------------
        eye_x, eye_y = 8.0, -3.0
        if self.blink_state < 0.85 and not self.is_sleeping:
            # Outer fiery lens flare
            pat_eye = cairo.RadialGradient(eye_x, eye_y, 0.3, eye_x, eye_y, 4.2)
            pat_eye.add_color_stop_rgba(0.0, 1.0, 0.95, 0.4, 1.0)
            pat_eye.add_color_stop_rgba(0.5, 1.0, 0.65, 0.05, 0.95)
            pat_eye.add_color_stop_rgba(1.0, 0.2, 0.05, 0.0, 0.0)
            ctx.set_source(pat_eye)
            ctx.arc(eye_x, eye_y, 4.2, 0, 2 * math.pi)
            ctx.fill()

            # Glowing golden draconic eye
            ctx.set_source_rgb(1.0, 0.85, 0.15)
            ctx.new_path()
            ctx.move_to(eye_x - 3.2, eye_y)
            ctx.curve_to(eye_x - 1, eye_y - 2.2, eye_x + 1, eye_y - 2.2, eye_x + 3.2, eye_y)
            ctx.curve_to(eye_x + 1, eye_y + 2.0, eye_x - 1, eye_y + 2.0, eye_x - 3.2, eye_y)
            ctx.close_path()
            ctx.fill()

            # Black Cat-like Slit Pupil
            ctx.set_source_rgb(0.01, 0.01, 0.02)
            ctx.new_path()
            ctx.move_to(eye_x, eye_y - 2.0)
            ctx.curve_to(eye_x + 0.7, eye_y, eye_x + 0.7, eye_y, eye_x, eye_y + 2.0)
            ctx.curve_to(eye_x - 0.7, eye_y, eye_x - 0.7, eye_y, eye_x, eye_y - 2.0)
            ctx.close_path()
            ctx.fill()

            # Specular Glint
            ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95)
            ctx.arc(eye_x - 0.8, eye_y - 0.8, 0.7, 0, 2 * math.pi)
            ctx.fill()
        else:
            # Sleeping peacefully or closed eyelid line
            ctx.set_source_rgb(0.09, 0.09, 0.12)
            ctx.set_line_width(1.4)
            ctx.new_path()
            ctx.move_to(eye_x - 3.2, eye_y - 0.3)
            ctx.curve_to(eye_x - 1, eye_y + 1.2, eye_x + 1, eye_y + 1.2, eye_x + 3.2, eye_y - 0.3)
            ctx.stroke()

        ctx.restore()
        ctx.restore()
