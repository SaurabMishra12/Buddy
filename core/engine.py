"""Core desktop pet engine: GLib animation tick loop, layer rendering, and character coordinator."""

import sys
import time
import math
import random
import cairo
from typing import Optional, Dict, Any

from platforms import is_macos

if not is_macos():
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
from behavior.brain import CompanionBrain, Intent
from behavior.autonomous import AutonomousAbilityManager, AutonomousMode
from behavior.perching import PerchManager, PerchMode
from core.abilities.ability import AbilityRegistry, AbilityRunner, AbilityDefinition
from core.abilities.combo import ComboEngine
from core.abilities.primitives import AbilityExecutionContext
from skins.schema import get_power_tier_labels, PowerTier


if is_macos():
    from Foundation import NSObject, NSTimer, NSRunLoop, NSRunLoopCommonModes

    class EngineTimerTarget(NSObject):
        def onTick_(self, timer):
            try:
                if hasattr(self, "_engine") and self._engine:
                    self._engine.on_tick()
            except Exception as e:
                import traceback
                print(f"[Buddy Engine] Error caught in AppKit timer loop: {e}", file=sys.stderr)
                traceback.print_exc()



class BuddyEngine:
    """Coordinates lifecycle, animation pacing, input routing, and rendering for Buddy."""


    def __init__(self, requested_skin: Optional[str] = None, debug_mode: bool = False, config: Optional[Any] = None):
        self.config = config if config is not None else globals()["config"]
        self.debug_mode = debug_mode or self.config.get("debug_mode", False)
        self.developer_mode = bool(self.config.get("developer_mode", False) or self.debug_mode)
        self.paused = False

        # Oneko-style floating companion window (180x180)
        self.window = OverlayWindow(
            on_draw=self.on_draw,
            on_button_press=self.on_button_press,
            on_button_release=self.on_button_release,
            on_motion=self.on_motion,
            on_scroll=self.on_scroll
        )
        if hasattr(self.window, "set_engine"):
            self.window.set_engine(self)

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
        default_skin = "ichigo" if is_macos() else "thor"
        raw_skin = requested_skin or self.config.get("skin", default_skin)
        if is_macos() and not requested_skin and raw_skin == "thor":
            raw_skin = "ichigo"
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

        # Companion Behavior Mode: "static" (Desk Pet / Stay Where Dropped), "roam" (Free Roam), "follow" (Cursor Companion)
        self.mode = self.config.get("companion_mode", "static")
        self.anchor_x = float(self.character.x)
        self.anchor_y = float(self.character.y)
        self.roam_target_x = float(self.character.x)
        self.roam_target_y = float(self.character.y)
        self.roam_next_decision = time.time() + 3.0

        # Smart hysteresis deadzone (False = calm/idle near cursor; True = chasing far cursor)
        self.is_chasing = False

        # Companion Brain, Autonomous Ability Manager, Perching, and Composable Abilities
        self.brain = CompanionBrain(character_id=active_skin_id)
        self.combo_engine = ComboEngine()
        self.autonomous_manager = AutonomousAbilityManager(brain=self.brain, combo_engine=self.combo_engine)
        self.perch_manager = PerchManager(mode=PerchMode.SAFE)
        self.active_ability_runner: Optional[AbilityRunner] = None

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
        if is_macos():
            import AppKit
            self._timer_target = EngineTimerTarget.alloc().init()
            self._timer_target._engine = self

            # Determine display refresh rate (e.g. 120Hz on ProMotion, 60Hz standard)
            screen = AppKit.NSScreen.mainScreen()
            max_fps = int(screen.maximumFramesPerSecond()) if (screen and hasattr(screen, "maximumFramesPerSecond")) else 60
            if not self.config.get("low_power_mode", False):
                self.target_fps = max_fps
                self.frame_interval_ms = int(1000 / self.target_fps)

            # Modern CADisplayLink migration (Apple recommended API for macOS)
            self._display_link = None
            self._timer = None
            try:
                if screen and hasattr(screen, "displayLinkWithTarget_selector_"):
                    self._display_link = screen.displayLinkWithTarget_selector_(self._timer_target, "onTick:")
                    if self._display_link:
                        self._display_link.addToRunLoop_forMode_(NSRunLoop.currentRunLoop(), NSRunLoopCommonModes)
            except Exception as e:
                print(f"[Buddy Engine] CADisplayLink initialization failed: {e}")
                self._display_link = None

            # Fallback to NSTimer if CADisplayLink is unavailable
            if not self._display_link:
                interval = max(0.001, self.frame_interval_ms / 1000.0)
                self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                    interval, self._timer_target, "onTick:", None, True
                )
                NSRunLoop.currentRunLoop().addTimer_forMode_(self._timer, NSRunLoopCommonModes)
        else:
            GLib.timeout_add(self.frame_interval_ms, self.on_tick)



    def switch_skin(self, skin_id: str) -> bool:
        """Dynamically switch to a different character with robust error boundaries."""
        try:
            norm_id = skin_manager.normalize_skin_id(skin_id)
            meta = skin_manager.get_metadata(norm_id)
            if not meta:
                print(f"[Buddy Engine] Warning: Skin '{skin_id}' (normalized: '{norm_id}') not found, ignoring switch.")
                return False

            old_x, old_y = self.character.x, self.character.y
            if hasattr(self.character, "_destroy_swing_rope"):
                try:
                    self.character._destroy_swing_rope()
                except Exception:
                    pass
            self.particles.clear()

            # Atomic creation with fallback to Thor if anything fails
            try:
                new_character = skin_manager.create_character(norm_id, x=old_x, y=old_y)
            except Exception as e:
                import traceback
                print(f"[Buddy Engine] Error instantiating skin '{norm_id}': {e}. Falling back safely.", file=sys.stderr)
                traceback.print_exc()
                new_character = skin_manager.create_character("ichigo", x=old_x, y=old_y)
                norm_id = "ichigo"
                meta = skin_manager.get_metadata("ichigo") or {}

            self.character = new_character
            self.character.scale = self.config.get("scale", 1.0)
            self.config.set("skin", norm_id)

            # Character arrival celebration safely guarded
            try:
                self._play_arrival_fanfare(norm_id, old_x, old_y)
            except Exception as e:
                print(f"[Buddy Engine] Non-fatal arrival fanfare error: {e}", file=sys.stderr)

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
            if hasattr(self, "brain") and self.brain:
                self.brain.set_character(norm_id)
            self.window.move_to(self.character.x, self.character.y)
            self.window.queue_draw()

            if hasattr(self, "tray") and self.tray and hasattr(self.tray, "update_skin_checkmarks"):
                try:
                    self.tray.update_skin_checkmarks(norm_id)
                except Exception:
                    pass

            print(f"[Buddy Engine] Switched to skin: {norm_id.upper()}")
            return True
        except Exception as e:
            import traceback
            print(f"[Buddy Engine] Recovered from fatal exception during switch_skin: {e}", file=sys.stderr)
            traceback.print_exc()
            return False

    def _play_arrival_fanfare(self, norm_id: str, old_x: float, old_y: float) -> None:
        """Character-specific arrival celebrations safely executed."""
        if norm_id == "thor":
            if hasattr(self.window, "trigger_sky_strike"):
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
            self.particles.burst_sparks(old_x, old_y, count=30, color=(0.8, 0.8, 1.0))
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
        elif norm_id in ("ichigo", "byakuya", "yamamoto", "kenpachi", "hitsugaya", "rukia", "urahara", "aizen", "yoruichi", "shunsui", "soi_fon", "shinji", "mayuri", "ulquiorra"):
            if hasattr(self.particles, "burst_reiatsu"):
                self.particles.burst_reiatsu(old_x, old_y, count=16)
            self.particles.shockwave(old_x, old_y, max_radius=85.0, color=(0.2, 0.7, 1.0))
            self.audio.play("swoosh")
        else:
            self.particles.burst_sparks(old_x, old_y, count=16)


    def is_developer_mode(self) -> bool:
        """Check whether Developer Mode is currently active."""
        return bool(getattr(self, "developer_mode", False) or getattr(self, "debug_mode", False) or self.config.get("developer_mode", False))

    def set_developer_mode(self, enabled: bool) -> None:
        """Update Developer Mode status and persist to config."""
        self.developer_mode = enabled
        self.config.set("developer_mode", enabled)

    def next_skin(self) -> str:
        """Cycle to the next available character skin.
        Respects ACTIVE_ROSTER allowlist unless Developer Mode is ON.
        """
        if self.is_developer_mode():
            skins = [s["id"] for s in skin_manager.get_available_skins(include_archived=True)]
        else:
            from skins.manager import ACTIVE_ROSTER
            skins = list(ACTIVE_ROSTER)

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
        """Cycle to the previous available character skin.
        Respects ACTIVE_ROSTER allowlist unless Developer Mode is ON.
        """
        if self.is_developer_mode():
            skins = [s["id"] for s in skin_manager.get_available_skins(include_archived=True)]
        else:
            from skins.manager import ACTIVE_ROSTER
            skins = list(ACTIVE_ROSTER)

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

    def set_mode(self, mode: str) -> str:
        """Switch companion behavior mode ('static', 'roam', 'follow')."""
        mode = mode.lower().strip()
        if mode in ("static", "roam", "follow"):
            self.mode = mode
            self.config.set("companion_mode", mode)
            self.anchor_x = float(self.character.x)
            self.anchor_y = float(self.character.y)
            self.roam_target_x = float(self.character.x)
            self.roam_target_y = float(self.character.y)
            self.is_chasing = False
            self.character.vx = 0.0
            self.character.vy = 0.0
            meta = skin_manager.get_metadata(self.character.skin_id) or {}
            if mode == "static":
                if meta.get("canFly", False):
                    self.character.state = CharacterState.HOVER
                else:
                    self.character.state = CharacterState.IDLE
            print(f"[Buddy Engine] Switched companion mode: {mode.upper()}")
            if hasattr(self, "tray") and self.tray and hasattr(self.tray, "update_mode_checkmarks"):
                try:
                    self.tray.update_mode_checkmarks(mode)
                except Exception:
                    pass
        return self.mode

    def set_scale(self, scale: float) -> None:
        """Adjust character scale."""
        self.character.scale = max(0.5, min(2.5, scale))
        self.config.set("scale", self.character.scale)
        if hasattr(self.window, "set_scale"):
            self.window.set_scale(self.character.scale)
        self.window.queue_draw()

    def open_control_center(self) -> None:
        """Open or bring forward the native macOS Buddy Control Center."""
        try:
            if is_macos():
                from platforms.macos.control_center import show_macos_control_center
                show_macos_control_center(self)
            else:
                from ui.settings_dialog import show_settings_dialog
                show_settings_dialog(self)
        except Exception as e:
            print(f"[Buddy Engine] Error opening Control Center: {e}", file=sys.stderr)

    def trigger_animation(self, anim_name: str) -> bool:
        """Trigger one of the 30 standardized character animation states."""
        try:
            if hasattr(self.character, "state_machine"):
                res = self.character.state_machine.transition_to(anim_name)
            else:
                self.character.state = anim_name
                res = True
            self.window.queue_draw()
            return res
        except Exception as e:
            print(f"[Buddy Engine] Error triggering animation '{anim_name}': {e}", file=sys.stderr)
            self.character.state = CharacterState.IDLE
            return False

    def trigger_shikai(self) -> bool:
        """Trigger Shikai for Bleach characters (exclusive to Bleach universe)."""
        try:
            from skins.base import BLEACH_CHARACTERS
            skin_id = getattr(self.character, "skin_id", "").lower()
            if skin_id not in BLEACH_CHARACTERS:
                print(f"[Buddy Engine] Notice: Shikai is exclusively for Bleach characters.")
                return False
            cx, cy = self.character.x, self.character.y
            if hasattr(self.window, "trigger_world_vfx"):
                if skin_id == "ichigo":
                    self.window.trigger_world_vfx("getsuga_tensho", cx, cy, self.cursor_x, self.cursor_y, is_bankai=False, duration_frames=45)
                elif skin_id == "byakuya":
                    self.window.trigger_world_vfx("senkei", cx, cy, self.cursor_x, self.cursor_y, duration_frames=50)
                elif skin_id == "yamamoto":
                    self.window.trigger_world_vfx("ryujin_jakka", cx, cy, self.cursor_x, self.cursor_y, is_bankai=False, duration_frames=50)
                elif skin_id == "hitsugaya":
                    self.window.trigger_world_vfx("hyorinmaru", cx, cy, self.cursor_x, self.cursor_y, duration_frames=50)
                elif skin_id == "rukia":
                    self.window.trigger_world_vfx("tsukishiro", cx, cy, self.cursor_x, self.cursor_y, duration_frames=50)
                elif skin_id == "aizen":
                    self.window.trigger_world_vfx("kyoka_suigetsu", cx, cy, self.cursor_x, self.cursor_y, duration_frames=50)
                elif skin_id == "ulquiorra":
                    self.window.trigger_world_vfx("cero_oscuras", cx, cy, self.cursor_x, self.cursor_y, duration_frames=50)

            # Call character ability or transition state machine
            res = self.character.trigger_ability("shikai", self.cursor_x, self.cursor_y, self.particles, self.audio)
            if not res:
                res = self.trigger_animation(CharacterState.SHIKAI_ACTIVATION)
            self.window.queue_draw()
            return res
        except Exception as e:
            print(f"[Buddy Engine] Error triggering Shikai: {e}", file=sys.stderr)
            return False

    def trigger_bankai(self) -> bool:
        """Trigger Bankai for Bleach characters (exclusive to Bleach universe)."""
        try:
            from skins.base import BLEACH_CHARACTERS
            skin_id = getattr(self.character, "skin_id", "").lower()
            if skin_id not in BLEACH_CHARACTERS:
                print(f"[Buddy Engine] Notice: Bankai is exclusively for Bleach characters.")
                return False
            cx, cy = self.character.x, self.character.y
            if hasattr(self.window, "trigger_world_vfx"):
                if skin_id == "ichigo":
                    self.window.trigger_world_vfx("getsuga_tensho", cx, cy, self.cursor_x, self.cursor_y, is_bankai=True, duration_frames=50)
                elif skin_id == "byakuya":
                    self.window.trigger_world_vfx("gokei", cx, cy, self.cursor_x, self.cursor_y, duration_frames=55)
                elif skin_id == "yamamoto":
                    self.window.trigger_world_vfx("kyokujitsujin", cx, cy, self.cursor_x, self.cursor_y, is_bankai=True, duration_frames=55)
                elif skin_id == "hitsugaya":
                    self.window.trigger_world_vfx("hyorinmaru", cx, cy, self.cursor_x, self.cursor_y, duration_frames=55)
                elif skin_id == "rukia":
                    self.window.trigger_world_vfx("hakka_no_togame", cx, cy, self.cursor_x, self.cursor_y, is_bankai=True, duration_frames=55)
                elif skin_id == "aizen":
                    self.window.trigger_world_vfx("kurohitsugi", cx, cy, self.cursor_x, self.cursor_y, duration_frames=55)
                elif skin_id == "ulquiorra":
                    self.window.trigger_world_vfx("lanza", cx, cy, self.cursor_x, self.cursor_y, duration_frames=55)

            res = self.character.trigger_ability("bankai", self.cursor_x, self.cursor_y, self.particles, self.audio)
            if not res:
                res = self.trigger_animation(CharacterState.BANKAI_ACTIVATION)
            self.window.queue_draw()
            return res
        except Exception as e:
            print(f"[Buddy Engine] Error triggering Bankai: {e}", file=sys.stderr)
            return False

    def trigger_play(self) -> bool:
        """Trigger an engaging interactive playful reaction or flourish with companion."""
        try:
            cx, cy = self.character.x, self.character.y
            skin_id = getattr(self.character, "skin_id", "").lower()
            self.particles.burst_hearts(cx, cy - 20, count=5)
            self.particles.burst_stars(cx, cy - 10, count=6)
            self.character.vx = random.choice([-2.0, 2.0])
            self.character.vy = -3.5  # Playful hop

            # Distinct Bleach personality animations
            if skin_id == "ichigo":
                self.character.trigger_ability("check_phone", cx, cy, self.particles, self.audio)
                self.audio.play("swoosh")
            elif skin_id == "byakuya":
                self.character.trigger_ability("adjust_scarf", cx, cy, self.particles, self.audio)
                self.particles.burst_cherry_petals(cx, cy, count=12)
                self.audio.play("magic")
            elif skin_id == "yamamoto":
                self.character.trigger_ability("stroke_beard", cx, cy, self.particles, self.audio)
                self.audio.play("fire")
            elif skin_id == "hitsugaya":
                self.character.trigger_ability("crossed_arms", cx, cy, self.particles, self.audio)
                self.particles.burst_ice_crystals(cx, cy, count=10)
                self.audio.play("magic")
            elif skin_id == "rukia":
                self.character.trigger_ability("draw_chappy", cx, cy, self.particles, self.audio)
                self.audio.play("sparkle")
            elif skin_id == "aizen":
                self.character.trigger_ability("adjust_glasses", cx, cy, self.particles, self.audio)
                self.audio.play("magic")
            elif skin_id == "ulquiorra":
                self.character.trigger_ability("stoic_glare", cx, cy, self.particles, self.audio)
                self.audio.play("swoosh")
            else:
                self.audio.play("sparkle")

            self.window.queue_draw()
            return True
        except Exception as e:
            print(f"[Buddy Engine] Error in trigger_play: {e}", file=sys.stderr)
            return False

    def trigger_ability(self, ability_name: str, target_x: Optional[float] = None, target_y: Optional[float] = None) -> bool:
        """Execute a character ability safely with error boundaries and world VFX."""
        try:
            tx = target_x if target_x is not None else self.cursor_x
            ty = target_y if target_y is not None else self.cursor_y
            cx, cy = self.character.x, self.character.y

            # World-space VFX for Bleach moves
            ab_lower = ability_name.lower()
            if any(k in ab_lower for k in ("getsuga", "senbonzakura", "ryujin", "flame_wave", "hyorinmaru", "tsukishiro", "kyoka", "kurohitsugi", "cero", "lanza")):
                is_bk = getattr(self.character, "is_bankai", False) or getattr(self.character, "is_segunda_etapa", False)
                self.window.trigger_world_vfx(ab_lower, cx, cy, tx, ty, is_bankai=is_bk)

            res = self.character.trigger_ability(ability_name, tx, ty, self.particles, self.audio)
            self.window.queue_draw()
            return res
        except Exception as e:
            print(f"[Buddy Engine] Error executing ability '{ability_name}': {e}", file=sys.stderr)
            return False

    def trigger_composable_ability(self, ab: AbilityDefinition) -> None:
        """Executes a composable ability definition."""
        try:
            ctx = AbilityExecutionContext(
                character_id=self.character.skin_id,
                companion_x=self.character.x,
                companion_y=self.character.y,
                companion_scale=self.character.scale,
                facing_right=self.character.facing_right,
                target_x=self.cursor_x,
                target_y=self.cursor_y,
            )
            self.active_ability_runner = AbilityRunner(ab, ctx)
        except Exception as e:
            print(f"[Buddy Engine] Error starting composable ability {ab.id}: {e}", file=sys.stderr)

    def trigger_power_tier(self, tier: str) -> bool:
        """Universal power tier activation: 'signature', 'power_up', 'ultimate'."""
        tier = tier.lower()
        skin_id = getattr(self.character, "skin_id", "").lower()
        if tier == "signature":
            self.trigger_signature_ability()
            return True
        elif tier in ["power_up", "shikai"]:
            from skins.base import BLEACH_CHARACTERS
            if skin_id in BLEACH_CHARACTERS:
                return self.trigger_shikai()
            else:
                res = self.character.trigger_ability("power_up", self.cursor_x, self.cursor_y, self.particles, self.audio)
                if not res:
                    res = self.character.trigger_ability("rage", self.cursor_x, self.cursor_y, self.particles, self.audio)
                if not res:
                    self.particles.burst_sparks(self.character.x, self.character.y, count=25, color=(1.0, 0.84, 0.0))
                    self.audio.play("charge")
                    res = True
                self.window.queue_draw()
                return res
        elif tier in ["ultimate", "bankai"]:
            from skins.base import BLEACH_CHARACTERS
            if skin_id in BLEACH_CHARACTERS:
                return self.trigger_bankai()
            else:
                res = self.character.trigger_ability("ultimate", self.cursor_x, self.cursor_y, self.particles, self.audio)
                if not res:
                    res = self.character.trigger_ability("thunderclap", self.cursor_x, self.cursor_y, self.particles, self.audio)
                if not res:
                    self.particles.shockwave(self.character.x, self.character.y, max_radius=90.0)
                    self.particles.burst_sparks(self.character.x, self.character.y, count=30, color=(0.9, 0.1, 0.1))
                    self.audio.play("bankai")
                    res = True
                self.window.queue_draw()
                return res
        return False

    def trigger_signature_ability(self) -> None:
        """Triggers character-specific signature move safely with crash protection."""
        try:
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
            elif skin_id == "ichigo":
                is_bankai = getattr(self.character, "is_bankai", False)
                self.character.trigger_ability("getsuga_tensho", self.cursor_x, self.cursor_y, self.particles, self.audio)
                self.window.trigger_world_vfx("getsuga_tensho", cx, cy, self.cursor_x, self.cursor_y, is_bankai=is_bankai)
                self.particles.launch_getsuga(cx, cy, self.cursor_x, self.cursor_y, is_bankai=is_bankai)
                self.particles.burst_reiatsu(cx, cy, color=(0.1, 0.6, 1.0) if not is_bankai else (0.9, 0.1, 0.1), count=12)
                self.shake.trigger(10.0 if is_bankai else 7.0)
                self.audio.play("swoosh")
            elif skin_id == "byakuya":
                self.character.trigger_ability("senbonzakura", self.cursor_x, self.cursor_y, self.particles, self.audio)
                self.window.trigger_world_vfx("senbonzakura", cx, cy, self.cursor_x, self.cursor_y)
                self.particles.burst_cherry_petals(cx, cy, count=28)
                self.particles.shockwave(cx, cy, max_radius=85.0, color=(1.0, 0.5, 0.75))
                self.shake.trigger(6.0)
                self.audio.play("magic")
            elif skin_id == "yamamoto":
                self.character.trigger_ability("ryujin_jakka", self.cursor_x, self.cursor_y, self.particles, self.audio)
                self.window.trigger_world_vfx("ryujin_jakka", cx, cy, self.cursor_x, self.cursor_y)
                self.particles.burst_reiatsu(cx, cy, color=(1.0, 0.3, 0.0), count=18)
                self.particles.shockwave(cx, cy, max_radius=110.0, color=(1.0, 0.2, 0.0))
                self.shake.trigger(15.0)
                self.audio.play("fire")
            elif skin_id == "kenpachi":
                self.character.trigger_ability("nozarashi", self.cursor_x, self.cursor_y, self.particles, self.audio)
                self.particles.burst_reiatsu(cx, cy, color=(0.85, 0.05, 0.1), count=20)
                self.particles.shockwave(cx, cy, max_radius=120.0, color=(0.9, 0.1, 0.1))
                self.shake.trigger(16.0)
                self.audio.play("roar")
            elif skin_id == "hitsugaya":
                self.character.trigger_ability("hyorinmaru", self.cursor_x, self.cursor_y, self.particles, self.audio)
                self.window.trigger_world_vfx("hyorinmaru", cx, cy, self.cursor_x, self.cursor_y)
                self.particles.burst_ice_crystals(cx, cy, count=24)
                self.particles.shockwave(cx, cy, max_radius=90.0, color=(0.6, 0.9, 1.0))
                self.shake.trigger(7.0)
                self.audio.play("magic")
            elif skin_id == "rukia":
                self.character.trigger_ability("tsukishiro", self.cursor_x, self.cursor_y, self.particles, self.audio)
                self.window.trigger_world_vfx("tsukishiro", cx, cy, self.cursor_x, self.cursor_y)
                self.particles.burst_ice_crystals(cx, cy, count=24)
                self.particles.shockwave(cx, cy, max_radius=95.0, color=(0.95, 0.98, 1.0))
                self.shake.trigger(6.0)
                self.audio.play("magic")
            elif skin_id == "urahara":
                self.character.trigger_ability("benihime", self.cursor_x, self.cursor_y, self.particles, self.audio)
                self.particles.burst_reiatsu(cx, cy, color=(0.9, 0.15, 0.3), count=14)
                self.particles.shockwave(cx, cy, max_radius=85.0, color=(0.9, 0.15, 0.3))
                self.shake.trigger(8.0)
                self.audio.play("laser")
            elif skin_id == "aizen":
                self.character.trigger_ability("kyoka_suigetsu", self.cursor_x, self.cursor_y, self.particles, self.audio)
                self.window.trigger_world_vfx("kyoka_suigetsu", cx, cy, self.cursor_x, self.cursor_y)
                self.particles.shockwave(cx, cy, max_radius=100.0, color=(0.3, 0.8, 0.9))
                self.audio.play("magic")
            elif skin_id == "yoruichi":
                self.character.trigger_ability("shunko", self.cursor_x, self.cursor_y, self.particles, self.audio)
                self.particles.burst_sparks(cx, cy, count=22, color=(0.9, 0.95, 0.3))
                self.audio.play("lightning")
            elif skin_id == "shunsui":
                self.character.trigger_ability("katen_kyokotsu", self.cursor_x, self.cursor_y, self.particles, self.audio)
                self.particles.burst_cherry_petals(cx, cy, count=18)
                self.audio.play("swoosh")
            elif skin_id == "soi_fon":
                self.character.trigger_ability("suzumebachi", self.cursor_x, self.cursor_y, self.particles, self.audio)
                self.particles.burst_sparks(cx, cy, count=15, color=(1.0, 0.9, 0.1))
                self.audio.play("laser")
            elif skin_id == "shinji":
                self.character.trigger_ability("sakanade", self.cursor_x, self.cursor_y, self.particles, self.audio)
                self.audio.play("magic")
            elif skin_id == "mayuri":
                self.character.trigger_ability("ashisogi_jizo", self.cursor_x, self.cursor_y, self.particles, self.audio)
                self.particles.smoke_puff(cx, cy, count=16, color=(0.6, 0.1, 0.8))
                self.audio.play("magic")
            elif skin_id == "ulquiorra":
                self.character.trigger_ability("cero_oscuras", self.cursor_x, self.cursor_y, self.particles, self.audio)
                self.window.trigger_world_vfx("cero_oscuras", cx, cy, self.cursor_x, self.cursor_y)
                self.particles.burst_reiatsu(cx, cy, color=(0.1, 0.8, 0.2), count=18)
                self.audio.play("laser")
            else:
                if not self.character.trigger_ability("special", cx, cy, self.particles, self.audio):
                    self.particles.burst_sparks(cx, cy, count=15)
                    self.audio.play("magic")
        except Exception as e:
            print(f"[Buddy Engine] Error in trigger_signature_ability: {e}", file=sys.stderr)


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
        """Master simulation tick with comprehensive crash recovery boundary."""
        if self.paused:
            return True
        try:
            return self._tick_simulation()
        except Exception as e:
            import traceback
            print(f"[Buddy Engine] Recovered from exception during on_tick: {e}", file=sys.stderr)
            traceback.print_exc()
            if hasattr(self, "character") and self.character:
                try:
                    self.character.vx = 0.0
                    self.character.vy = 0.0
                    self.character.state = CharacterState.IDLE
                except Exception:
                    pass
            return True

    def _tick_simulation(self) -> bool:
        """Internal simulation logic execution."""
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

            # Composable Ability & Autonomous Brain simulation
            if hasattr(self, "active_ability_runner") and self.active_ability_runner:
                self.active_ability_runner.update(dt)
                ctx = self.active_ability_runner.ctx
                while ctx.particles_to_spawn:
                    p = dict(ctx.particles_to_spawn.pop(0))
                    ptype = p.pop("type", "sparks")
                    px = p.pop("x", self.character.x)
                    py = p.pop("y", self.character.y)
                    self.particles.spawn_generic(ptype, px, py, **p)
                while ctx.sounds_to_play:
                    s = ctx.sounds_to_play.pop(0)
                    self.audio.play(s.get("sound", "swoosh"))
                if ctx.screen_shake > 0:
                    self.shake.trigger(ctx.screen_shake)
                if self.active_ability_runner.completed:
                    self.active_ability_runner = None
            elif hasattr(self, "autonomous_manager") and self.autonomous_manager:
                auto_ab = self.autonomous_manager.update(dt, self.character.skin_id, now=now)
                if auto_ab:
                    self.trigger_composable_ability(auto_ab)

            if hasattr(self, "brain") and self.brain:
                self.brain.update(
                    dt=dt,
                    companion_x=self.character.x,
                    companion_y=self.character.y,
                    cursor_x=self.cursor_x,
                    cursor_y=self.cursor_y,
                    behavior_mode=self.mode,
                )

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
                self.anchor_x = float(self.character.x)
                self.anchor_y = float(self.character.y)

            elif self.mode == "static":
                # Desk Pet Mode: Buddy stays calm right where you dropped him!
                self.character.x = self.anchor_x
                self.character.y = self.anchor_y
                self.character.vx = 0.0
                self.character.vy = 0.0
                self.is_chasing = False
                meta = skin_manager.get_metadata(self.character.skin_id) or {}
                if meta.get("canFly", False):
                    if self.character.state not in (CharacterState.HOVER, CharacterState.SLEEP, CharacterState.SIT):
                        self.character.state = CharacterState.HOVER
                else:
                    if self.character.state not in (CharacterState.IDLE, CharacterState.SLEEP, CharacterState.SIT):
                        self.character.state = CharacterState.IDLE

                # Softly turn to face user's cursor without moving
                if abs(self.cursor_x - self.character.x) > 20.0:
                    self.character.facing_right = (self.cursor_x >= self.character.x)

            else:
                # Autonomous Roam or Cursor Follow modes
                if self.mode == "roam":
                    # Autonomous wandering to random waypoints
                    if now >= self.roam_next_decision:
                        self.roam_next_decision = now + random.uniform(6.0, 14.0)
                        self.roam_target_x = random.uniform(min_x + 100.0, min_x + screen_w - 100.0)
                        self.roam_target_y = random.uniform(min_y + 100.0, min_y + screen_h - 100.0)
                    target_x = self.roam_target_x
                    target_y = self.roam_target_y
                    dist_to_target = math.hypot(target_x - self.character.x, target_y - self.character.y)
                    should_move = dist_to_target > 40.0
                    self.is_chasing = False
                else:
                    # "follow": active cursor following
                    target_x = self.cursor_x
                    target_y = self.cursor_y
                    dist_to_cursor = math.hypot(self.cursor_x - self.character.x, self.cursor_y - self.character.y)
                    self.is_chasing = (dist_to_cursor > 50.0)
                    should_move = self.is_chasing

                if should_move:
                    skin = self.character.skin_id
                    meta = skin_manager.get_metadata(skin) or {}

                    if hasattr(self.character, "nav_to"):
                        curr_target = getattr(self.character, "nav_target", None)
                        if curr_target is None or math.hypot(target_x - curr_target[0], target_y - curr_target[1]) > 40.0:
                            self.character.nav_to(target_x, target_y)
                    else:
                        dx = target_x - self.character.x
                        dy = target_y - self.character.y
                        dist = math.hypot(dx, dy)
                        is_flyer = meta.get("canFly", False) or getattr(self.character, "can_fly", False) or skin in ("superman", "thor", "ironman", "dragon", "harry_potter", "thanos")

                        if is_flyer:
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

                                self.character.vx += (target_vx - self.character.vx) * 0.22
                                self.character.vy += (target_vy - self.character.vy) * 0.22
                                self.character.x += self.character.vx
                                self.character.y += self.character.vy

                                target_tilt = (self.character.vx / 15.0) * 0.22
                                self.character.tilt += (target_tilt - self.character.tilt) * 0.16
                            else:
                                self.character.state = CharacterState.HOVER
                                self.character.vx *= 0.82
                                self.character.vy *= 0.82
                                self.character.tilt *= 0.82
                        else:
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
                            else:
                                self.character.state = CharacterState.IDLE
                                self.character.vx *= 0.8
                                self.character.vy *= 0.8

                        # Screen boundary clamp
                        self.character.x = max(min_x + 50.0, min(min_x + screen_w - 50.0, self.character.x))
                        self.character.y = max(min_y + 50.0, min(min_y + screen_h - 50.0, self.character.y))
                else:
                    self.character.vx *= 0.8
                    self.character.vy *= 0.8

            # Handle signature move active window & acrobatics
            if self.is_spinning:
                if now < self.spin_end_time:
                    if self.character.skin_id == "cat":
                        t_rel = max(0.0, min(1.0, (self.spin_end_time - now) / 0.8))
                        self.character.tilt = (1.0 - t_rel) * 2.0 * math.pi
                else:
                    self.is_spinning = False
                    if self.character.skin_id == "cat":
                        self.character.tilt = 0.0

            # Inject Companion Mode, Pomodoro, and Focus context for intelligent behavior selection
            cfg_context = dict(self.config.data)
            cfg_context["companion_mode"] = self.mode
            cfg_context["cursor_follow"] = (self.mode == "follow")
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

    def on_draw(self, widget: Any, ctx: cairo.Context) -> bool:
        """Render composite frame with complete exception boundary."""
        try:
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
        except Exception as e:
            print(f"[Buddy Engine] Recovered from rendering exception in on_draw: {e}", file=sys.stderr)

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
        ctx.set_font_size(9)
        ctx.move_to(8, 16)
        p_cnt = getattr(self.particles, "particle_count", len(self.particles.particles))
        ctx.show_text(f"{self.character.skin_id.upper()} {self.current_fps:.0f}FPS P:{p_cnt}")
        ctx.move_to(8, 28)
        ctx.show_text(f"ST:{self.character.state}")
        ctx.move_to(8, 40)
        ctx.set_source_rgb(1.0, 0.75, 0.2)
        ctx.show_text(f"POMO:{self.pomodoro.state[:5]} {self.pomodoro.remaining_formatted}")
        ctx.restore()

    def on_button_press(self, widget: Any, event: Any) -> bool:
        """Handle mouse click on pet."""
        click_dist = math.hypot(event.x - self.window.half_size, event.y - self.window.half_size)
        if click_dist > 54.0:
            return False

        # 1. Double-click: Open Buddy Control Center interface!
        double_click_type = 5 if is_macos() else getattr(Gdk.EventType, "_2BUTTON_PRESS", 5)
        if event.type == double_click_type:
            self.open_control_center()
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
            elif self.character.skin_id == "byakuya":
                self.audio.play("magic")
                self.particles.burst_cherry_petals(self.character.x, self.character.y, count=8)
            elif self.character.skin_id in ("hitsugaya", "rukia"):
                self.audio.play("magic")
                self.particles.burst_ice_crystals(self.character.x, self.character.y, count=8)
            elif self.character.skin_id == "yamamoto":
                self.audio.play("fire")
                self.particles.burst_reiatsu(self.character.x, self.character.y, color=(1.0, 0.3, 0.0), count=6)
            elif self.character.skin_id == "kenpachi":
                self.audio.play("roar")
                self.particles.burst_reiatsu(self.character.x, self.character.y, color=(0.85, 0.05, 0.1), count=6)
            elif self.character.skin_id == "ichigo":
                self.audio.play("swoosh")
                self.particles.burst_reiatsu(self.character.x, self.character.y, color=(0.1, 0.6, 1.0), count=6)
            elif self.character.skin_id == "urahara":
                self.audio.play("laser")
            else:
                self.audio.play("magic")

            self.particles.burst_sparks(self.character.x, self.character.y, count=8)
            return True

        return False

    def on_button_release(self, widget: Any, event: Any) -> bool:
        if event.button == 1:
            was_dragging = self.is_dragging
            self.is_dragging = False
            self.is_chasing = False
            self.anchor_x = float(self.character.x)
            self.anchor_y = float(self.character.y)
            self.character.vx = 0.0
            self.character.vy = 0.0
            skin = self.character.skin_id
            meta = skin_manager.get_metadata(skin) or {}

            if self.mode == "static":
                if meta.get("canFly", False):
                    self.character.state = CharacterState.HOVER
                else:
                    self.character.state = CharacterState.IDLE
            else:
                target_x = self.cursor_x
                target_y = self.cursor_y

                from core.platforms import platform_manager
                platform_manager.register_user_click_ledge(target_x, target_y)

                if hasattr(self.character, "nav_to"):
                    self.character.nav_to(target_x, target_y)
                elif meta.get("canFly", False) or skin in ("superman", "thor", "ironman", "dragon", "harry_potter", "thanos"):
                    self.character.state = CharacterState.HOVER
                else:
                    self.character.state = CharacterState.IDLE
            return True
        return False

    def on_motion(self, widget: Any, event: Any) -> bool:
        """Update global cursor coordinates during mouse motion."""
        try:
            px, py = self.window.query_pointer()
            self.cursor_x = px
            self.cursor_y = py
            return True
        except Exception:
            pass
        return False

    def on_scroll(self, widget: Any, event: Any) -> bool:
        """Cycle character skins using mouse scroll wheel directly over pet."""
        dir_val = getattr(event, "direction", None)
        is_up = dir_val == 0 or (not is_macos() and hasattr(Gdk, "ScrollDirection") and dir_val == Gdk.ScrollDirection.UP)
        is_down = dir_val == 1 or (not is_macos() and hasattr(Gdk, "ScrollDirection") and dir_val == Gdk.ScrollDirection.DOWN)
        if is_up:
            self.prev_skin()
            return True
        elif is_down:
            self.next_skin()
            return True
        return False

    def run(self) -> None:
        """Start the native desktop event loop."""
        self.window.show()
        if is_macos():
            import AppKit
            AppKit.NSApplication.sharedApplication().run()
        else:
            Gtk.main()

    def quit(self) -> None:
        """Gracefully terminate active event loop and invalidate render links."""
        if is_macos():
            if hasattr(self, "_display_link") and self._display_link:
                try:
                    self._display_link.invalidate()
                except Exception:
                    pass
                self._display_link = None
            if hasattr(self, "_timer") and self._timer:
                try:
                    self._timer.invalidate()
                except Exception:
                    pass
                self._timer = None
            try:
                from platforms.macos.control_center import close_macos_control_center
                close_macos_control_center()
            except Exception:
                pass
            if hasattr(self, "window") and self.window:
                try:
                    self.window.close()
                except Exception:
                    pass
            import AppKit
            AppKit.NSApplication.sharedApplication().terminate_(None)
        else:
            if Gtk.main_level() > 0:
                Gtk.main_quit()

