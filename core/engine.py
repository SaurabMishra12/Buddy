"""Core desktop pet engine: GLib animation tick loop, layer rendering, and character coordinator."""

import time
import math
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


class BuddyEngine:
    """Coordinates lifecycle, animation pacing, input routing, and rendering for Buddy."""

    def __init__(self, requested_skin: Optional[str] = None, debug_mode: bool = False):
        self.config = config
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
        else:
            self.particles.burst_sparks(old_x, old_y, count=20)
            self.audio.play("magic")

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
            self.particles.shockwave(cx, cy, max_radius=75.0, color=(1.0, 0.4, 0.0))
            self.particles.flame_breath(cx, cy, cx + (50 if self.character.facing_right else -50), cy)
            self.audio.play("roar")
        elif skin_id == "cat":
            for _ in range(15):
                self.particles.burst_sparks(cx, cy, count=3, color=(1.0, 0.4, 0.7))
            self.audio.play("purr")
        elif skin_id == "dog":
            self.particles.burst_sparks(cx, cy, count=15, color=(1.0, 0.8, 0.2))
            self.audio.play("bark")
        elif skin_id == "hulk":
            self.particles.shockwave(cx, cy, max_radius=85.0, color=(0.2, 0.9, 0.2))
            self.audio.play("roar")
        elif skin_id == "ironman":
            self.particles.shockwave(cx, cy, max_radius=70.0, color=(0.2, 0.8, 1.0))
            self.particles.burst_sparks(cx, cy, count=25, color=(0.2, 0.9, 1.0))
            self.audio.play("laser")
        elif skin_id == "harry_potter":
            for _ in range(20):
                self.particles.burst_sparks(cx, cy, count=3, color=(0.8, 0.8, 1.0))
            self.audio.play("magic")
        elif skin_id == "captain_america":
            self.character.trigger_ability("shield_throw", cx, cy, self.particles, self.audio)
            self.audio.play("laser")
        elif skin_id == "thanos":
            self.particles.shockwave(cx, cy, max_radius=90.0, color=(0.7, 0.1, 0.9))
            self.audio.play("magic")
        elif skin_id == "batman":
            self.character.trigger_ability("smoke_bomb", cx, cy, self.particles, self.audio)
            self.audio.play("swoosh")
        else:
            self.particles.burst_sparks(cx, cy, count=15)
            self.audio.play("magic")

    def on_tick(self) -> bool:
        """Master simulation tick."""
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
            if self.is_dragging:
                # Dragging: follow mouse directly with traversal animation
                prev_x = self.character.x
                prev_y = self.character.y
                self.character.x = max(0.0, min(self.window.screen_w, self.cursor_x - self.drag_offset_x))
                self.character.y = max(0.0, min(self.window.screen_h, self.cursor_y - self.drag_offset_y))
                self.character.vx = self.character.x - prev_x
                self.character.vy = self.character.y - prev_y
                if abs(self.character.vx) > 1.0:
                    self.character.facing_right = (self.character.vx >= 0.0)

                # Character-specific traversal state while dragged
                skin = self.character.skin_id
                if skin in ("superman", "thor", "ironman", "dragon", "harry_potter"):
                    self.character.state = CharacterState.FLY
                elif skin == "hulk":
                    self.character.state = CharacterState.JUMP
                else:
                    self.character.state = CharacterState.RUN

                # Trailing particles while traversing/dragged
                if skin == "thor":
                    self.particles.burst_sparks(self.character.x, self.character.y + 15, count=2, color=CYAN_GLOW)
                elif skin == "dragon":
                    if random.random() < 0.4:
                        self.particles.flame_puff(self.character.x, self.character.y + 10, count=1, size=4.0)
                elif skin == "ironman":
                    self.particles.burst_sparks(self.character.x, self.character.y + 16, count=2, color=(1.0, 0.5, 0.1))
                elif skin == "superman":
                    self.particles.burst_sparks(self.character.x, self.character.y + 16, count=1, color=(1.0, 0.2, 0.2))
                elif skin == "hulk":
                    if random.random() < 0.3:
                        self.particles.smoke_puff(self.character.x, self.character.y + 20, count=1)
            else:
                # Smart hysteresis deadzone like Mjolnir:
                # Closer than 55px -> character does NOT run away; stays calm so user can click or drag it!
                # Farther than 110px -> character wakes up and chases cursor across screen
                dist_to_cursor = math.hypot(self.cursor_x - self.character.x, self.cursor_y - self.character.y)
                if dist_to_cursor > 110.0:
                    self.is_chasing = True
                elif dist_to_cursor < 55.0:
                    self.is_chasing = False

                # Handle spin animation
                if self.is_spinning:
                    if now < self.spin_end_time:
                        self.character.tilt += 0.35
                    else:
                        self.is_spinning = False
                        self.character.tilt = 0.0

                # Target coordinates passed to character:
                # If within deadzone and idle, target is character's current position so it stays put!
                target_x = self.cursor_x if self.is_chasing else self.character.x
                target_y = self.cursor_y if self.is_chasing else self.character.y

                self.character.update(
                    dt,
                    target_x,
                    target_y,
                    self.window.bounds,
                    self.particles,
                    self.audio,
                    self.config.data
                )

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

        return False

    def _draw_debug_hud(self, ctx: cairo.Context) -> None:
        """Render compact developer telemetry badge."""
        ctx.save()
        ctx.set_source_rgba(0.05, 0.05, 0.1, 0.8)
        ctx.rectangle(4, 4, 110, 34)
        ctx.fill()

        ctx.set_source_rgb(0.0, 0.9, 1.0)
        ctx.set_line_width(1.0)
        ctx.stroke()

        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.select_font_face("Monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(9)
        ctx.move_to(8, 16)
        ctx.show_text(f"{self.character.skin_id.upper()} {self.current_fps:.0f}FPS")
        ctx.move_to(8, 28)
        ctx.show_text(f"{self.character.state}")
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

        # 4. Left-click: Start drag
        if event.button == 1:
            self.is_dragging = True
            self.is_chasing = False
            self.drag_offset_x = event.x - self.window.half_size
            self.drag_offset_y = event.y - self.window.half_size
            skin = self.character.skin_id
            if skin in ("superman", "thor", "ironman", "dragon", "harry_potter"):
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
            if was_dragging:
                if skin == "hulk":
                    # Release drop: Hulk plunges down to smash the ground!
                    self.character.state = CharacterState.JUMP
                    self.character.vy = 10.0
                    self.character.is_airborne = True
                elif skin in ("superman", "thor", "ironman", "dragon", "harry_potter"):
                    self.character.state = CharacterState.HOVER
                else:
                    self.character.state = CharacterState.IDLE
            else:
                self.character.state = CharacterState.IDLE
            return True
        return False

    def on_motion(self, widget: Gtk.Widget, event: Gdk.EventMotion) -> bool:
        if self.is_dragging:
            try:
                px, py = self.window.query_pointer()
                self.character.x = max(0.0, min(self.window.screen_w, px - self.drag_offset_x))
                self.character.y = max(0.0, min(self.window.screen_h, py - self.drag_offset_y))
                self.character.vx = 0.0
                self.character.vy = 0.0
                self.window.move_to(self.character.x, self.character.y)
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
