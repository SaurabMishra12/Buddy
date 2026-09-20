"""Core desktop pet engine: GLib animation tick loop, layer rendering, and character coordinator."""

import time
import math
import random
import cairo
from typing import Optional, Dict, Any

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from core.config import config
from core.window import OverlayWindow
from core.particles import ParticleManager, CYAN_GLOW
from core.audio import audio_manager
from core.physics import ScreenShake
from skins.manager import skin_manager
from skins.base import BaseCharacter, CharacterState
from pomodoro.manager import PomodoroManager, PomodoroState


class BuddyEngine:
    """Coordinates lifecycle, animation pacing, input routing, and rendering for Buddy."""

    def __init__(self, requested_skin: Optional[str] = None, debug_mode: bool = False, config: Optional[Any] = None):
        self.config = config if config is not None else globals()["config"]
        self.debug_mode = debug_mode or self.config.get("debug_mode", False)
        self.paused = False

        # Oneko-style floating companion window (180x180)
        self.window = OverlayWindow(
            on_draw=self.on_draw,
            on_button_press=self.on_button_press,
            on_button_release=self.on_button_release,
            on_motion=self.on_motion,
            on_scroll=self.on_scroll
        )

        # Particle, Audio, and Screen shake managers
        limit = self.config.get("particle_limit", 300)
        self.particles = ParticleManager(max_particles=limit)
        self.audio = audio_manager
        self.audio.enabled = self.config.get("sound_enabled", True)
        self.audio.volume = self.config.get("sound_volume", 0.7)
        self.shake = ScreenShake()

        # Pomodoro Productivity & Behavior synchronization
        self.pomodoro = PomodoroManager(config=self.config)
        self.pomodoro.add_listener(self._on_pomodoro_event)

        # Instantiate character at screen center
        raw_skin = requested_skin or self.config.get("skin", "thor")
        active_skin_id = skin_manager.normalize_skin_id(raw_skin)

        init_x = self.window.screen_w * 0.5
        init_y = self.window.screen_h * 0.4
        self.character: BaseCharacter = skin_manager.create_character(
            active_skin_id,
            x=init_x,
            y=init_y
        )
        self.character.scale = self.config.get("scale", 1.0)
        self.config.set("skin", active_skin_id)

        # Sync click-through: In Oneko floating window, character hitbox is clickable
        # while everything outside passes through cleanly.
        self.click_through = self.config.get("click_through", False)
        self.window.set_click_through(self.click_through)

        # Mouse tracking
        self.cursor_x, self.cursor_y = self.window.query_pointer()
        self.prev_cursor_x = self.cursor_x
        self.prev_cursor_y = self.cursor_y

        # Dragging state (interactive mode)
        self.is_dragging = False
        self.drag_offset_x = 0.0
        self.drag_offset_y = 0.0

        # Special ability spin state
        self.is_spinning = False
        self.spin_end_time = 0.0

        # Smart hysteresis deadzone (False = calm/idle near cursor; True = chasing far cursor)
        self.is_chasing = False

        # Position window over initial character coordinates
        self.window.move_to(self.character.x, self.character.y)

        # FPS Pacing and performance monitoring
        self.target_fps = 30 if self.config.get("low_power_mode", False) else self.config.get("fps", 60)
        self.frame_interval_ms = int(1000 / self.target_fps)
        self.last_frame_time = time.time()
        self.fps_counter = 0
        self.current_fps = float(self.target_fps)
        self.fps_timer = time.time()

        # Arrival effect!
        self.particles.burst_sparks(self.character.x, self.character.y, count=25)

        # Show window & start main animation tick
        self.window.show()
        GLib.timeout_add(self.frame_interval_ms, self.on_tick)

    def switch_skin(self, skin_id: str) -> bool:
        """Dynamically switch to a different character with character-specific fanfare."""
        norm_id = skin_manager.normalize_skin_id(skin_id)
        meta = skin_manager.get_metadata(norm_id)
        if not meta:
            print(f"[Buddy Engine] Warning: Skin '{skin_id}' (normalized: '{norm_id}') not found, ignoring switch.")
            return False

        old_x, old_y = self.character.x, self.character.y
        if hasattr(self.character, "_destroy_swing_rope"):
            self.character._destroy_swing_rope()
        self.particles.clear()
        self.character = skin_manager.create_character(norm_id, x=old_x, y=old_y)
        self.character.scale = self.config.get("scale", 1.0)
        self.config.set("skin", norm_id)

        # Character-specific arrival celebrations!
        if norm_id == "thor":
            self.window.trigger_sky_strike(old_x, old_y)
            self.particles.burst_sparks(old_x, old_y, count=35, color=CYAN_GLOW)
            self.particles.shockwave(old_x, old_y, max_radius=80.0)
            self.audio.play("lightning")
        elif norm_id == "superman":
            self.particles.shockwave(old_x, old_y, max_radius=80.0, color=(0.85, 0.95, 1.0))
            self.particles.burst_sparks(old_x, old_y, count=25, color=(1.0, 0.2, 0.2))
            self.audio.play("jet")
        elif norm_id == "dragon":
            self.particles.shockwave(old_x, old_y, max_radius=75.0, color=(1.0, 0.4, 0.0))
            self.audio.play("roar")
        elif norm_id == "ironman":
            self.particles.shockwave(old_x, old_y, max_radius=70.0, color=(0.2, 0.8, 1.0))
            self.particles.burst_sparks(old_x, old_y, count=20, color=(1.0, 0.5, 0.1))
            self.audio.play("laser")
        elif norm_id == "hulk":
            self.particles.shockwave(old_x, old_y, max_radius=90.0, color=(0.2, 0.9, 0.2))
            self.audio.play("roar")
        elif norm_id == "cat":
            self.particles.burst_sparks(old_x, old_y, count=15, color=(1.0, 0.4, 0.7))
            self.audio.play("purr")
        elif norm_id == "dog":
            self.particles.burst_sparks(old_x, old_y, count=15, color=(1.0, 0.8, 0.2))
            self.audio.play("bark")
        elif norm_id == "harry_potter":
            for _ in range(25):
                self.particles.burst_sparks(old_x, old_y, count=2, color=(0.8, 0.8, 1.0))
            self.audio.play("magic")
        elif norm_id == "captain_america":
            self.particles.shockwave(old_x, old_y, max_radius=60.0, color=(0.8, 0.1, 0.1))
            self.audio.play("laser")
        elif norm_id == "thanos":
            self.particles.shockwave(old_x, old_y, max_radius=95.0, color=(0.7, 0.1, 0.9))
            self.audio.play("magic")
        elif norm_id == "batman":
            self.particles.shockwave(old_x, old_y, max_radius=60.0, color=(0.3, 0.3, 0.35))
            self.audio.play("swoosh")
        elif norm_id == "spiderman":
            self.particles.shockwave(old_x, old_y, max_radius=70.0, color=(0.92, 0.96, 1.0))
            self.particles.burst_sparks(old_x, old_y, count=22, color=(0.86, 0.12, 0.12))
            self.particles.burst_sparks(old_x, old_y, count=14, color=(0.08, 0.18, 0.44))
            self.audio.play("thwip")
        # Ensure non-flying ground characters are placed safely on the ground
        if not meta.get("canFly", False):
            min_x, min_y, screen_w, screen_h = self.window.bounds
            self.character.y = min_y + screen_h - 70.0
            self.character.vy = 0.0
            self.character.is_airborne = False
            self.character.state = CharacterState.IDLE

        self.is_dragging = False
        self.is_chasing = False
        self.is_spinning = False
        self.window.move_to(self.character.x, self.character.y)

        print(f"[Buddy Engine] Switched to skin: {norm_id.upper()}")
        return True

    def next_skin(self) -> str:
        """Cycle to the next available character skin."""
        skins = [s["id"] for s in skin_manager.get_available_skins()]
        if not skins:
            return self.character.skin_id
        try:
            idx = skins.index(self.character.skin_id)
            next_id = skins[(idx + 1) % len(skins)]
        except ValueError:
            next_id = skins[0]
        self.switch_skin(next_id)
        return next_id

    def prev_skin(self) -> str:
        """Cycle to the previous available character skin."""
        skins = [s["id"] for s in skin_manager.get_available_skins()]
        if not skins:
            return self.character.skin_id
        try:
            idx = skins.index(self.character.skin_id)
            prev_id = skins[(idx - 1) % len(skins)]
        except ValueError:
            prev_id = skins[0]
        self.switch_skin(prev_id)
        return prev_id

    def toggle_pause(self) -> bool:
        """Pause or resume Buddy."""
        self.paused = not self.paused
        print(f"[Buddy Engine] Pet {'paused' if self.paused else 'resumed'}")
        self.window.queue_draw()
        return self.paused

    def toggle_click_through(self) -> bool:
        """Toggle between interactive pet hitbox and 100% click-through."""
        self.click_through = not self.click_through
        self.config.set("click_through", self.click_through)
        self.window.set_click_through(self.click_through)
        return self.click_through

    def set_scale(self, scale: float) -> None:
        """Adjust character scale."""
        self.character.scale = max(0.5, min(2.5, scale))
        self.config.set("scale", self.character.scale)

    def trigger_signature_ability(self) -> None:
        """Triggers character-specific signature move on double click!"""
        skin_id = self.character.skin_id
        cx, cy = self.character.x, self.character.y
        self.is_spinning = True
        self.spin_end_time = time.time() + 1.2
        self.shake.trigger(4.0)

        if skin_id == "thor":
            self.window.trigger_sky_strike(cx, cy)
            self.particles.burst_sparks(cx, cy, count=35, color=CYAN_GLOW)
            self.particles.shockwave(cx, cy, max_radius=80.0)
            self.audio.play("lightning")
            self.character.trigger_ability("hammer_spin", cx, cy, self.particles, self.audio)
        elif skin_id == "superman":
            self.character.trigger_ability("heat_vision", self.cursor_x, self.cursor_y, self.particles, self.audio)
            self.character.trigger_ability("supersonic_flight", self.cursor_x, self.cursor_y, self.particles, self.audio)
            self.particles.shockwave(cx, cy, max_radius=80.0, color=(1.0, 0.3, 0.1))
            self.audio.play("laser")
        elif skin_id == "dragon":
            self.character.trigger_ability("fireball", self.cursor_x, self.cursor_y, self.particles, self.audio)
            self.particles.shockwave(cx, cy, max_radius=75.0, color=(1.0, 0.4, 0.0))
            self.audio.play("roar")
        elif skin_id == "cat":
            for _ in range(15):
                self.particles.burst_sparks(cx, cy, count=3, color=(1.0, 0.4, 0.7))
            self.audio.play("purr")
        elif skin_id == "dog":
            self.particles.burst_sparks(cx, cy, count=15, color=(1.0, 0.8, 0.2))
            self.audio.play("bark")
        elif skin_id == "hulk":
            self.character.trigger_ability("ground_smash", cx, cy, self.particles, self.audio)
            self.character.trigger_ability("thunderclap", cx, cy, self.particles, self.audio)
            self.shake.trigger(14.0)
        elif skin_id == "ironman":
            self.character.trigger_ability("unibeam", self.cursor_x, self.cursor_y, self.particles, self.audio)
            self.particles.shockwave(cx, cy, max_radius=85.0, color=(0.2, 0.85, 1.0))
            self.shake.trigger(10.0)
            self.audio.play("laser")
        elif skin_id == "harry_potter":
            for _ in range(20):
                self.particles.burst_sparks(cx, cy, count=3, color=(0.8, 0.8, 1.0))
            self.audio.play("magic")
        elif skin_id == "captain_america":
            self.character.trigger_ability("shield_throw", self.cursor_x, self.cursor_y, self.particles, self.audio)
            self.audio.play("laser")
        elif skin_id == "thanos":
            self.character.trigger_ability("the_snap", self.cursor_x, self.cursor_y, self.particles, self.audio)
            self.shake.trigger(16.0)
        elif skin_id == "batman":
            self.character.trigger_ability("smoke_bomb", cx, cy, self.particles, self.audio)
            self.audio.play("swoosh")
        elif skin_id == "spiderman":
            self.character.trigger_ability("upside_down_hang", cx, cy, self.particles, self.audio)
            self.particles.shockwave(cx, cy, max_radius=85.0, color=(0.94, 0.97, 1.0))
            self.audio.play("thwip")
        elif skin_id == "pixel_wizard":
            self.character.trigger_ability("magic_orb", self.cursor_x, self.cursor_y, self.particles, self.audio)
            self.particles.burst_energy_orbs(cx, cy, count=6)
            self.audio.play("magic")
        elif skin_id == "space_robot":
            self.character.trigger_ability("scan_beam", self.cursor_x, self.cursor_y, self.particles, self.audio)
            self.particles.burst_energy_orbs(cx, cy, count=5)
            self.audio.play("laser")
        elif skin_id == "ninja":
            self.character.trigger_ability("smoke_bomb", cx, cy, self.particles, self.audio)
            self.particles.smoke_puff(cx, cy, count=12)
            self.audio.play("swoosh")
        elif skin_id == "vampire":
            self.character.trigger_ability("bat_swarm", self.cursor_x, self.cursor_y, self.particles, self.audio)
            self.particles.burst_dust(cx, cy, count=8)
            self.audio.play("magic")
        elif skin_id == "fairy":
            self.character.trigger_ability("sparkle_burst", cx, cy, self.particles, self.audio)
            self.particles.burst_stars(cx, cy - 15, count=12)
            self.audio.play("sparkle")
        elif skin_id == "alien":
            self.character.trigger_ability("tractor_beam", self.cursor_x, self.cursor_y, self.particles, self.audio)
            self.particles.burst_energy_orbs(cx, cy, count=6)
            self.audio.play("laser")
        elif skin_id == "ghost":
            self.character.trigger_ability("phase_shift", cx, cy, self.particles, self.audio)
            self.particles.burst_energy_orbs(cx, cy, count=5)
            self.audio.play("swoosh")
        elif skin_id == "penguin":
            self.character.trigger_ability("belly_slide", self.cursor_x, self.cursor_y, self.particles, self.audio)
            self.particles.burst_dust(cx, cy + 15, count=6)
            self.audio.play("bark")
        elif skin_id == "fox":
            self.character.trigger_ability("pounce_jump", self.cursor_x, self.cursor_y, self.particles, self.audio)
            self.particles.burst_hearts(cx, cy - 15, count=4)
            self.audio.play("bark")
        elif skin_id == "slime":
            self.character.trigger_ability("super_bounce", self.cursor_x, self.cursor_y, self.particles, self.audio)
            self.particles.burst_confetti(cx, cy - 10, count=12)
            self.audio.play("sparkle")
        else:
            if not self.character.trigger_ability("special", cx, cy, self.particles, self.audio):
                self.particles.burst_sparks(cx, cy, count=15)
                self.audio.play("magic")

    def _on_pomodoro_event(self, event_name: str, state: str, remaining: float) -> None:
        """Handle Pomodoro milestones and trigger character reactions, audio, and particles."""
        cx, cy = self.character.x, self.character.y
        skin_id = self.character.skin_id

        if event_name == "work_start":
            self.particles.burst_energy_orbs(cx, cy, count=4)
            self.audio.play("laser" if skin_id in ("ironman", "space_robot") else "magic")
            if hasattr(self.character, "memory") and self.character.memory:
                self.character.memory.record_interaction("pomodoro_work_start")
            if hasattr(self.character, "behavior") and self.character.behavior:
                from behavior.state_machine import BehaviorState
                self.character.behavior.transition_to(BehaviorState.FOCUS)

        elif event_name == "break_start":
            self.particles.burst_confetti(cx, cy - 20, count=16)
            self.particles.burst_stars(cx, cy - 10, count=8)
            self.audio.play("purr" if skin_id == "cat" else ("bark" if skin_id in ("dog", "fox") else "sparkle"))
            if hasattr(self.character, "memory") and self.character.memory:
                self.character.memory.record_interaction("pomodoro_break_start")
            if hasattr(self.character, "behavior") and self.character.behavior:
                from behavior.state_machine import BehaviorState
                self.character.behavior.transition_to(BehaviorState.BREAK)

        elif event_name == "work_completed":
            self.particles.burst_confetti(cx, cy - 25, count=28)
            self.particles.burst_stars(cx, cy - 15, count=14)
            self.shake.trigger(8.0)
            if skin_id == "thor":
                self.audio.play("lightning")
                self.window.trigger_sky_strike(cx, cy)
            elif skin_id == "dragon":
                self.audio.play("roar")
                self.particles.flame_puff(cx, cy, count=3)
            elif skin_id == "cat":
                self.audio.play("purr")
            elif skin_id == "hulk":
                self.audio.play("smash")
            else:
                self.audio.play("sparkle")

            if hasattr(self.character, "memory") and self.character.memory:
                self.character.memory.record_pomodoro_session()
            if hasattr(self.character, "behavior") and self.character.behavior:
                from behavior.state_machine import BehaviorState
                self.character.behavior.transition_to(BehaviorState.CELEBRATE)

        elif event_name == "break_completed":
            self.particles.burst_sparks(cx, cy, count=10)

    def on_tick(self) -> bool:
        """Master simulation tick."""
        if self.paused:
            return True

        now = time.time()
        dt = max(1e-4, now - self.last_frame_time)
        self.last_frame_time = now

        # Update FPS calculation
        self.fps_counter += 1
        if now - self.fps_timer >= 1.0:
            self.current_fps = self.fps_counter / (now - self.fps_timer)
            self.fps_counter = 0
            self.fps_timer = now

        # Query pointer position globally
        px, py = self.window.query_pointer()
        self.prev_cursor_x = self.cursor_x
        self.prev_cursor_y = self.cursor_y
        self.cursor_x = px
        self.cursor_y = py

        if not self.paused:
            min_x, min_y, screen_w, screen_h = self.window.bounds
            ground_y = min_y + screen_h - 70.0

            from core.platforms import platform_manager
            platform_manager.update(self.window.bounds, self.cursor_x, self.cursor_y)

            if self.is_dragging:
                # Drag locomotion: Navigate autonomously in their own distinct superhero way!
                target_x = self.cursor_x
                target_y = self.cursor_y
                skin = self.character.skin_id
                meta = skin_manager.get_metadata(skin) or {}

                if hasattr(self.character, "nav_to"):
                    # Continuous superhero locomotion towards target destination:
                    # - Spider-Man: run -> swing -> jump -> land/seat/perch
                    # - Captain America: run -> supersonic shield dash -> slide
                    # - Batman: run -> grapple shot & climb -> cape glide -> land
                    # - Hulk: parabolic super leaps across desktop!
                    curr_target = getattr(self.character, "nav_target", None)
                    if curr_target is None or math.hypot(target_x - curr_target[0], target_y - curr_target[1]) > 40.0:
                        self.character.nav_to(target_x, target_y)
                else:
                    dx = target_x - self.character.x
                    dy = target_y - self.character.y
                    dist = math.hypot(dx, dy)
                    is_flyer = meta.get("canFly", False) or getattr(self.character, "can_fly", False) or skin in ("superman", "thor", "ironman", "dragon", "harry_potter", "thanos")

                    if is_flyer:
                        # FLYERS: Critically damped spring-damper flight towards mouse destination
                        if dist > 12.0:
                            self.character.facing_right = (dx >= 0.0)
                            self.character.state = CharacterState.FLY
                            if hasattr(self.character, "is_seated"):
                                self.character.is_seated = False
                            if hasattr(self.character, "is_sleeping"):
                                self.character.is_sleeping = False
                            follow_spd = min(15.0, max(2.5, dist * 0.085))
                            target_vx = (dx / dist) * follow_spd
                            target_vy = (dy / dist) * follow_spd

                            # Critically damped spring-damper velocity easing (fluid & smooth)
                            self.character.vx += (target_vx - self.character.vx) * 0.22
                            self.character.vy += (target_vy - self.character.vy) * 0.22
                            self.character.x += self.character.vx
                            self.character.y += self.character.vy

                            # Hero/Companion banking tilt and flight propulsion trails
                            target_tilt = (self.character.vx / 15.0) * 0.22
                            self.character.tilt += (target_tilt - self.character.tilt) * 0.16

                            if skin == "ironman":
                                self.particles.burst_sparks(self.character.x, self.character.y + 16, count=2, color=(1.0, 0.5, 0.1))
                                self.particles.burst_sparks(self.character.x - (8 if self.character.facing_right else -8), self.character.y + 18, count=1, color=CYAN_GLOW)
                            elif skin == "space_robot":
                                self.particles.burst_sparks(self.character.x, self.character.y + 18, count=2, color=(0.1, 0.9, 1.0))
                            elif skin == "fairy":
                                self.particles.burst_stars(self.character.x, self.character.y + 8, count=2, color=(1.0, 0.9, 0.4))
                            elif skin == "alien":
                                if random.random() < 0.4:
                                    self.particles.burst_stars(self.character.x, self.character.y + 10, count=1, color=(0.2, 1.0, 0.5))
                            elif skin == "ghost":
                                if random.random() < 0.3:
                                    self.particles.burst_stars(self.character.x, self.character.y + 10, count=1, color=(0.7, 0.9, 1.0))
                            elif skin == "vampire":
                                if random.random() < 0.3:
                                    self.particles.smoke_puff(self.character.x, self.character.y + 10, count=1, color=(0.2, 0.05, 0.15))
                            elif skin == "pixel_wizard":
                                if random.random() < 0.35:
                                    self.particles.burst_stars(self.character.x, self.character.y + 8, count=1, color=(0.8, 0.4, 1.0))
                            elif skin == "superman":
                                target_tilt = (self.character.vx / 15.0) * 0.24
                                self.character.tilt += (target_tilt - self.character.tilt) * 0.18
                                self.particles.burst_sparks(self.character.x - (12 if self.character.facing_right else -12), self.character.y + 8, count=1, color=(1.0, 0.2, 0.2))
                                self.particles.burst_sparks(self.character.x, self.character.y + 12, count=1, color=(0.2, 0.4, 0.9))
                            elif skin == "thor":
                                target_tilt = (self.character.vx / 15.0) * 0.18
                                self.character.tilt += (target_tilt - self.character.tilt) * 0.15
                                self.particles.burst_sparks(self.character.x + (16 if self.character.facing_right else -16), self.character.y - 4, count=2, color=CYAN_GLOW)
                            elif skin == "dragon":
                                target_tilt = (self.character.vx / 15.0) * 0.25
                                self.character.tilt += (target_tilt - self.character.tilt) * 0.16
                                if random.random() < 0.35:
                                    self.particles.flame_puff(self.character.x, self.character.y + 10, count=1, size=4.0)
                            elif skin == "harry_potter":
                                target_tilt = (self.character.vx / 15.0) * 0.20
                                self.character.tilt += (target_tilt - self.character.tilt) * 0.15
                                self.particles.burst_sparks(self.character.x - (12 if self.character.facing_right else -12), self.character.y + 8, count=2, color=(1.0, 0.85, 0.2))
                            elif skin == "thanos":
                                target_tilt = (self.character.vx / 15.0) * 0.16
                                self.character.tilt += (target_tilt - self.character.tilt) * 0.14
                                self.particles.burst_sparks(self.character.x, self.character.y + 16, count=2, color=(0.7, 0.1, 0.9))
                        else:
                            self.character.state = CharacterState.HOVER
                            self.character.vx *= 0.82
                            self.character.vy *= 0.82
                            self.character.tilt *= 0.82
                            self.character.x += self.character.vx
                            self.character.y += self.character.vy
                    else:
                        # RUNNERS & GROUND COMPANIONS:
                        self.character.facing_right = (dx >= 0.0)

                        if dist > 12.0:
                            follow_spd = min(14.0, max(2.5, dist * 0.10))
                            target_vx = (dx / dist) * follow_spd
                            target_vy = (dy / dist) * follow_spd
                            self.character.vx += (target_vx - self.character.vx) * 0.25
                            self.character.vy += (target_vy - self.character.vy) * 0.25
                            self.character.x += self.character.vx
                            self.character.y += self.character.vy
                            self.character.state = CharacterState.RUN
                            if random.random() < 0.2:
                                self.particles.burst_dust(self.character.x, self.character.y + 15, count=1)
                        else:
                            self.character.state = CharacterState.IDLE
                            self.character.vx *= 0.8
                            self.character.vy *= 0.8
                            self.character.x += self.character.vx
                            self.character.y += self.character.vy

                    # Screen boundary clamp
                    self.character.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.character.x))
                    self.character.y = max(min_y + 50.0, min(min_y + screen_h - 50.0, self.character.y))

            else:
                # Normal peaceful behavior when not dragging:
                # Closer than 50px -> Character stays calm in IDLE/HOVER; user can touch/click/drag without fleeing!
                dist_to_cursor = math.hypot(self.cursor_x - self.character.x, self.cursor_y - self.character.y)
                self.is_chasing = (dist_to_cursor > 50.0)

                # Handle signature move active window & acrobatics
                if self.is_spinning:
                    if now < self.spin_end_time:
                        # Only acrobatic pet skins (e.g. cat) perform a smooth 360° somersault;
                        # superhero and creature characters maintain their authentic upright poses and kinematics!
                        if self.character.skin_id == "cat":
                            t_rel = max(0.0, min(1.0, (self.spin_end_time - now) / 0.8))
                            self.character.tilt = (1.0 - t_rel) * 2.0 * math.pi
                    else:
                        self.is_spinning = False
                        if self.character.skin_id == "cat":
                            self.character.tilt = 0.0

            # Inject Pomodoro and Focus context for intelligent behavior selection
            cfg_context = dict(self.config.data)
            cfg_context["pomodoro_state"] = self.pomodoro.state
            cfg_context["pomodoro_remaining"] = self.pomodoro.remaining_seconds
            cfg_context["focus_mode"] = (self.pomodoro.state == PomodoroState.WORK) or self.config.get("focus_mode", False)

            self.character.update(
                dt,
                self.cursor_x,
                self.cursor_y,
                self.window.bounds,
                self.particles,
                self.audio,
                cfg_context
            )

            # Advance Pomodoro countdown
            self.pomodoro.tick(dt)

            # Move the floating window so (half_size, half_size) matches (character.x, character.y)
            self.window.move_to(self.character.x, self.character.y)

            # Update particles & screen shake
            self.particles.update()
            self.shake.update()

            # Redraw
            self.window.queue_draw()
        return True

    def on_draw(self, widget: Gtk.Widget, ctx: cairo.Context) -> bool:
        """Render composite frame."""
        # 1. Clear background transparently
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()
        ctx.restore()

        # 2. Translate coordinates so world (character.x, character.y) renders at window center
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_OVER)
        ctx.translate(
            self.window.half_size - self.character.x,
            self.window.half_size - self.character.y
        )

        # Apply screen shake offset if active
        if self.shake.intensity > 0.1 and self.config.get("screen_shake_enabled", True):
            ctx.translate(self.shake.offset_x, self.shake.offset_y)

        # Render particles & active character
        self.particles.draw(ctx)
        self.character.draw(ctx, self.particles)

        ctx.restore()

        # 3. Compact developer HUD if debug mode
        if self.debug_mode:
            self._draw_debug_hud(ctx)

        # 4. Floating Pomodoro status badge (compact glassmorphic pill above Buddy)
        if self.pomodoro.state not in (PomodoroState.IDLE, PomodoroState.COMPLETED) and self.config.get("show_pomodoro_badge", True):
            self._draw_pomodoro_badge(ctx)

        return False

    def _draw_pomodoro_badge(self, ctx: cairo.Context) -> None:
        """Render a small, sleek floating focus/break pill badge near Buddy."""
        ctx.save()
        cx = self.window.half_size
        cy = self.window.half_size - 48

        is_work = (self.pomodoro.state == PomodoroState.WORK)
        is_paused = (self.pomodoro.state == PomodoroState.PAUSED)
        bg_r, bg_g, bg_b = (0.85, 0.25, 0.2) if is_work else ((0.85, 0.65, 0.15) if is_paused else (0.15, 0.75, 0.4))

        text = f"{'PAUSE' if is_paused else ('FOCUS' if is_work else 'BREAK')} {self.pomodoro.remaining_formatted}"

        # Pill background
        pill_w = 78
        pill_h = 18
        px = cx - pill_w / 2.0
        py = cy - pill_h / 2.0

        ctx.set_source_rgba(0.08, 0.08, 0.12, 0.85)
        # Rounded rectangle
        r = 9.0
        ctx.new_path()
        ctx.arc(px + r, py + r, r, math.pi, 1.5 * math.pi)
        ctx.arc(px + pill_w - r, py + r, r, 1.5 * math.pi, 2 * math.pi)
        ctx.arc(px + pill_w - r, py + pill_h - r, r, 0, 0.5 * math.pi)
        ctx.arc(px + r, py + pill_h - r, r, 0.5 * math.pi, math.pi)
        ctx.close_path()
        ctx.fill_preserve()

        # Accent border
        ctx.set_source_rgba(bg_r, bg_g, bg_b, 0.9)
        ctx.set_line_width(1.2)
        ctx.stroke()

        # Progress bar under-glow
        prog = self.pomodoro.progress
        if prog > 0.0:
            ctx.set_source_rgba(bg_r, bg_g, bg_b, 0.4)
            ctx.rectangle(px + 4, py + pill_h - 3, (pill_w - 8) * prog, 1.5)
            ctx.fill()

        # Text label
        ctx.set_source_rgba(1.0, 1.0, 1.0, 0.95)
        ctx.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(9)
        extents = ctx.text_extents(text)
        tx = cx - extents.width / 2.0 - extents.x_bearing
        ty = cy - extents.height / 2.0 - extents.y_bearing
        ctx.move_to(tx, ty)
        ctx.show_text(text)

        ctx.restore()

    def _draw_debug_hud(self, ctx: cairo.Context) -> None:
        """Render comprehensive developer telemetry badge."""
        ctx.save()
        ctx.set_source_rgba(0.04, 0.05, 0.08, 0.88)
        ctx.rectangle(4, 4, 138, 48)
        ctx.fill()

        ctx.set_source_rgb(0.0, 0.9, 1.0)
        ctx.set_line_width(1.0)
        ctx.stroke()

        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.select_font_face("Monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(9)
        ctx.move_to(8, 16)
        ctx.show_text(f"{self.character.skin_id.upper()} {self.current_fps:.0f}FPS P:{len(self.particles.particles)}")
        ctx.move_to(8, 28)
        ctx.show_text(f"ST:{self.character.state}")
        ctx.move_to(8, 40)
        ctx.set_source_rgb(1.0, 0.75, 0.2)
        ctx.show_text(f"POMO:{self.pomodoro.state[:5]} {self.pomodoro.remaining_formatted}")
        ctx.restore()

    def on_button_press(self, widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        """Handle mouse click on pet."""
        click_dist = math.hypot(event.x - self.window.half_size, event.y - self.window.half_size)
        if click_dist > 54.0:
            return False

        # 1. Double-click: signature ability move & spin
        double_click_type = getattr(Gdk.EventType, "_2BUTTON_PRESS", 5)
        if event.type == double_click_type:
            self.trigger_signature_ability()
            return True

        # 2. Middle-click (Button 2): Transform directly to next skin!
        if event.button == 2:
            self.next_skin()
            return True

        # 3. Right-click: Open interactive options context menu
        if event.button == 3:
            from ui.context_menu import show_context_menu
            show_context_menu(self, event)
            return True

        # 4. Left-click: Direct character or start superhero navigation
        if event.button == 1:
            self.is_dragging = True
            self.is_chasing = False
            self.drag_offset_x = event.x - self.window.half_size
            self.drag_offset_y = event.y - self.window.half_size
            skin = self.character.skin_id

            if hasattr(self.character, "nav_to"):
                self.character.nav_to(self.cursor_x, self.cursor_y)
            elif skin in ("superman", "thor", "ironman", "dragon", "harry_potter", "thanos"):
                self.character.state = CharacterState.FLY
            elif skin == "hulk":
                self.character.state = CharacterState.JUMP
            else:
                self.character.state = CharacterState.RUN

            if self.character.skin_id == "cat":
                self.audio.play("purr")
            elif self.character.skin_id == "dog":
                self.audio.play("bark")
            elif self.character.skin_id == "superman":
                self.audio.play("jet")
            elif self.character.skin_id == "thor":
                self.audio.play("lightning")
                self.particles.burst_sparks(self.character.x, self.character.y, count=14, color=CYAN_GLOW)
            elif self.character.skin_id == "hulk":
                self.audio.play("roar")
            else:
                self.audio.play("magic")

            self.particles.burst_sparks(self.character.x, self.character.y, count=8)
            return True

        return False

    def on_button_release(self, widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        if event.button == 1:
            was_dragging = self.is_dragging
            self.is_dragging = False
            self.is_chasing = False
            skin = self.character.skin_id

            target_x = self.cursor_x
            target_y = self.cursor_y

            from core.platforms import platform_manager
            platform_manager.register_user_click_ledge(target_x, target_y)

            if hasattr(self.character, "nav_to"):
                self.character.nav_to(target_x, target_y)
            elif skin in ("superman", "thor", "ironman", "dragon", "harry_potter", "thanos"):
                self.character.state = CharacterState.HOVER
            else:
                self.character.state = CharacterState.IDLE
            return True
        return False

    def on_motion(self, widget: Gtk.Widget, event: Gdk.EventMotion) -> bool:
        """Update global cursor coordinates during mouse motion."""
        try:
            px, py = self.window.query_pointer()
            self.cursor_x = px
            self.cursor_y = py
            return True
        except Exception:
            pass
        return False

    def on_scroll(self, widget: Gtk.Widget, event: Gdk.EventScroll) -> bool:
        """Cycle character skins using mouse scroll wheel directly over pet."""
        if event.direction == Gdk.ScrollDirection.UP:
            self.prev_skin()
            return True
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self.next_skin()
            return True
        return False

    def run(self) -> None:
        """Start the GTK main loop."""
        self.window.show()
        Gtk.main()
