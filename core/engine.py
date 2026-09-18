"""Core desktop pet engine: GLib animation tick loop, layer rendering, and character coordinator."""

import time
import cairo
from typing import Optional, Dict, Any

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from core.config import config
from core.window import OverlayWindow
from core.particles import ParticleManager
from core.audio import audio_manager
from core.physics import ScreenShake
from skins.manager import skin_manager
from skins.base import BaseCharacter


class BuddyEngine:
    """Coordinates lifecycle, animation pacing, input routing, and rendering for Buddy."""

    def __init__(self, requested_skin: Optional[str] = None, debug_mode: bool = False):
        self.config = config
        self.debug_mode = debug_mode or self.config.get("debug_mode", False)
        self.paused = False

        # Display and window initialization
        self.window = OverlayWindow(
            on_draw=self.on_draw,
            on_button_press=self.on_button_press,
            on_button_release=self.on_button_release,
            on_motion=self.on_motion
        )

        # Particle, Audio, and Screen shake managers
        limit = self.config.get("particle_limit", 300)
        self.particles = ParticleManager(max_particles=limit)
        self.audio = audio_manager
        self.audio.enabled = self.config.get("sound_enabled", True)
        self.audio.volume = self.config.get("sound_volume", 0.7)
        self.shake = ScreenShake()

        # Instantiate character
        active_skin_id = requested_skin or self.config.get("skin", "thor")
        self.character: BaseCharacter = skin_manager.create_character(
            active_skin_id,
            x=self.window.bounds[0] + self.window.bounds[2] * 0.5,
            y=self.window.bounds[1] + self.window.bounds[3] * 0.4
        )
        self.character.scale = self.config.get("scale", 1.0)

        # Sync click-through setting
        self.click_through = self.config.get("click_through", True)
        self.window.set_click_through(self.click_through)

        # Mouse tracking
        self.cursor_x, self.cursor_y = self.window.query_pointer()
        self.prev_cursor_x = self.cursor_x
        self.prev_cursor_y = self.cursor_y

        # Dragging state (interactive mode)
        self.is_dragging = False
        self.drag_offset_x = 0.0
        self.drag_offset_y = 0.0

        # FPS Pacing and performance monitoring
        self.target_fps = 30 if self.config.get("low_power_mode", False) else self.config.get("fps", 60)
        self.frame_interval_ms = int(1000 / self.target_fps)
        self.last_frame_time = time.time()
        self.fps_counter = 0
        self.current_fps = float(self.target_fps)
        self.fps_timer = time.time()

        # Arrival effect!
        self.particles.sky_strike(self.character.x, self.character.y)

        # Start main animation tick
        GLib.timeout_add(self.frame_interval_ms, self.on_tick)

    def switch_skin(self, skin_id: str) -> bool:
        """Dynamically switch to a different character."""
        meta = skin_manager.get_metadata(skin_id)
        if not meta:
            print(f"[Buddy Engine] Warning: Skin '{skin_id}' not found, ignoring switch.")
            return False

        old_x, old_y = self.character.x, self.character.y
        self.particles.clear()
        self.character = skin_manager.create_character(skin_id, x=old_x, y=old_y)
        self.character.scale = self.config.get("scale", 1.0)
        self.config.set("skin", skin_id)

        # Arrival celebration effect for new skin
        self.particles.sky_strike(old_x, old_y)
        self.audio.play("magic")
        print(f"[Buddy Engine] Switched to skin: {skin_id}")
        return True

    def toggle_pause(self) -> bool:
        """Pause or resume Buddy."""
        self.paused = not self.paused
        print(f"[Buddy Engine] Pet {'paused' if self.paused else 'resumed'}")
        return self.paused

    def toggle_click_through(self) -> bool:
        """Toggle between pure click-through and interactive hitboxes."""
        self.click_through = not self.click_through
        self.config.set("click_through", self.click_through)
        self.window.set_click_through(self.click_through)
        return self.click_through

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

        # Query pointer position
        px, py = self.window.query_pointer()
        self.prev_cursor_x = self.cursor_x
        self.prev_cursor_y = self.cursor_y
        self.cursor_x = px
        self.cursor_y = py

        if not self.paused:
            # Update active character
            self.character.update(
                dt,
                self.cursor_x,
                self.cursor_y,
                self.window.bounds,
                self.particles,
                self.audio,
                self.config.data
            )

            # Update particles
            self.particles.update()

            # Update screen shake
            self.shake.update()

            # If interactive hitbox mode is active, update shape around character
            if not self.click_through:
                hx, hy, r = self.character.get_hitbox()
                self.window.update_interactive_hitbox(hx, hy, radius=r + 15.0)

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

        # Apply screen shake offset if active
        ctx.save()
        if self.shake.intensity > 0.1 and self.config.get("screen_shake_enabled", True):
            ctx.translate(self.shake.offset_x, self.shake.offset_y)

        # 2. Render background particles & effects
        ctx.set_operator(cairo.OPERATOR_OVER)
        self.particles.draw(ctx)

        # 3. Render active character
        self.character.draw(ctx, self.particles)

        ctx.restore()

        # 4. Developer / Debug HUD
        if self.debug_mode:
            self._draw_debug_hud(ctx)

        return False

    def _draw_debug_hud(self, ctx: cairo.Context) -> None:
        """Render developer telemetry overlay in corner."""
        ctx.save()
        ctx.set_source_rgba(0.05, 0.05, 0.1, 0.75)
        ctx.rectangle(20, 20, 260, 140)
        ctx.fill()

        ctx.set_source_rgba(0.0, 0.9, 1.0, 0.9)
        ctx.set_line_width(1.5)
        ctx.stroke()

        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.select_font_face("Monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(12)

        lines = [
            f"BUDDY DEVELOPER MODE",
            f"Skin: {self.character.skin_id.upper()}",
            f"State: {self.character.state}",
            f"Pos: ({int(self.character.x)}, {int(self.character.y)})",
            f"Vel: ({self.character.vx:.1f}, {self.character.vy:.1f})",
            f"Target: ({int(self.cursor_x)}, {int(self.cursor_y)})",
            f"FPS: {self.current_fps:.1f} / {self.target_fps}",
            f"Particles: {len(self.particles.sparks) + len(self.particles.flames)}"
        ]
        for i, text in enumerate(lines):
            ctx.move_to(30, 40 + (i * 14))
            ctx.show_text(text)

        ctx.restore()

    def on_button_press(self, widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        """Handle mouse click in interactive mode."""
        if event.button == 1:  # Left click: Pet or drag
            hx, hy, r = self.character.get_hitbox()
            if math.hypot(event.x_root - hx, event.y_root - hy) < r:
                self.is_dragging = True
                self.drag_offset_x = self.character.x - event.x_root
                self.drag_offset_y = self.character.y - event.y_root
                self.audio.play("purr" if self.character.skin_id == "cat" else "bark")
                return True
        elif event.button == 3:  # Right click: Context menu
            from ui.context_menu import show_context_menu
            show_context_menu(self, event)
            return True
        return False

    def on_button_release(self, widget: Gtk.Widget, event: Gdk.EventButton) -> bool:
        if event.button == 1:
            self.is_dragging = False
        return False

    def on_motion(self, widget: Gtk.Widget, event: Gdk.EventMotion) -> bool:
        if self.is_dragging:
            self.character.x = event.x_root + self.drag_offset_x
            self.character.y = event.y_root + self.drag_offset_y
            self.character.vx = 0.0
            self.character.vy = 0.0
            return True
        return False

    def run(self) -> None:
        """Start the GTK main loop."""
        self.window.show()
        Gtk.main()
