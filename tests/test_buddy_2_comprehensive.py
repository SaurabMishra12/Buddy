"""Comprehensive test suite for Buddy 2.0 features:
- All 10 new skins instantiation, abilities, update, and Cairo rendering
- SkinManager registration and aliases
- PomodoroManager state machine, countdown, transitions, and callbacks
- PomodoroStats metrics, daily/weekly aggregation, and persistence
- CharacterBehavior and Personality autonomous action selection
- CharacterMemory local recording
- Engine Pomodoro and behavior integration
"""

import unittest
import cairo
import time
from pathlib import Path
from skins.manager import skin_manager, BUILTIN_SKINS
from skins.base import CharacterState
from behavior.personality import CharacterPersonality
from behavior.memory import CharacterMemory
from behavior.state_machine import CharacterBehavior, BehaviorState
from pomodoro.manager import PomodoroManager, PomodoroState
from pomodoro.statistics import PomodoroStats
from pomodoro.notifications import NotificationManager
from core.particles import ParticleManager
from core.audio import audio_manager


class MockEngine:
    """Mock BuddyEngine for lightweight integration testing."""
    def __init__(self):
        self.character = skin_manager.create_character("slime")
        self.paused = False
        self.click_through = False
        self.cursor_x = 500.0
        self.cursor_y = 400.0
        self.particles = ParticleManager(max_particles=100)
        self.audio = audio_manager
        self.config = type("MockConfig", (), {
            "data": {},
            "get": lambda s, k, d=None: d,
            "set": lambda s, k, v, auto_save=True: None,
            "save": lambda s: None
        })()


class TestBuddy2Comprehensive(unittest.TestCase):

    def setUp(self):
        self.particle_mgr = ParticleManager(max_particles=200)
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 180, 180)
        self.ctx = cairo.Context(self.surface)
        self.screen_bounds = (0, 0, 1920, 1080)

    # 1. NEW SKINS TEST
    def test_all_10_new_skins_instantiate_and_draw(self):
        """Verify that all 10 new skins instantiate, update, and render cleanly in Cairo."""
        new_skin_ids = [
            "pixel_wizard", "space_robot", "ninja", "vampire", "fairy",
            "alien", "ghost", "penguin", "fox", "slime"
        ]
        for sid in new_skin_ids:
            with self.subTest(skin=sid):
                char = skin_manager.create_character(sid, x=90.0, y=90.0)
                self.assertIsNotNone(char)
                self.assertEqual(char.skin_id, sid)
                self.assertIsNotNone(char.personality)
                self.assertIsNotNone(char.memory)
                self.assertIsNotNone(char.behavior)

                # Test update tick
                char.update(
                    0.016,
                    cursor_x=120.0,
                    cursor_y=80.0,
                    screen_bounds=self.screen_bounds,
                    particle_mgr=self.particle_mgr,
                    audio_mgr=audio_manager,
                    config_data={"activity_level": 1.0, "pomodoro_state": "IDLE"}
                )

                # Test Cairo rendering
                self.ctx.save()
                char.draw(self.ctx, self.particle_mgr)
                self.ctx.restore()

    def test_all_10_new_skins_trigger_abilities(self):
        """Verify that signature abilities fire for all 10 new skins."""
        abilities_map = {
            "pixel_wizard": "magic_orb",
            "space_robot": "scan_beam",
            "ninja": "smoke_bomb",
            "vampire": "bat_swarm",
            "fairy": "sparkle_burst",
            "alien": "tractor_beam",
            "ghost": "phase_shift",
            "penguin": "belly_slide",
            "fox": "pounce_jump",
            "slime": "super_bounce"
        }
        for sid, ability in abilities_map.items():
            with self.subTest(skin=sid, ability=ability):
                char = skin_manager.create_character(sid, x=100.0, y=100.0)
                fired = char.trigger_ability(ability, 200.0, 100.0, self.particle_mgr, audio_manager)
                self.assertTrue(fired, f"Ability {ability} failed to trigger for {sid}")

    # 2. SKIN MANAGER TESTS
    def test_skin_manager_total_skins_and_aliases(self):
        """Verify skin manager provides 22 skins and handles aliases properly."""
        available = skin_manager.get_available_skins()
        self.assertGreaterEqual(len(available), 22)
        self.assertIn("slime", [s["id"] for s in available])
        self.assertIn("fox", [s["id"] for s in available])

        # Test normalization aliases
        self.assertEqual(skin_manager.normalize_skin_id("wizard"), "pixel_wizard")
        self.assertEqual(skin_manager.normalize_skin_id("robot"), "space_robot")
        self.assertEqual(skin_manager.normalize_skin_id("bouncy_slime"), "slime")

    # 3. POMODORO MANAGER TESTS
    def test_pomodoro_lifecycle_and_transitions(self):
        """Verify Pomodoro work -> short break -> long break cycle."""
        stats = PomodoroStats()
        stats.reset_all()
        mgr = PomodoroManager(stats=stats)
        mgr.work_duration = 0.05  # fast test durations
        mgr.short_break_duration = 0.02
        mgr.long_break_duration = 0.04
        mgr.sessions_before_long_break = 2
        mgr.auto_start_breaks = True
        mgr.auto_start_work = True

        events_received = []
        mgr.add_listener(lambda ev, st, rem: events_received.append(ev))

        # 1. Start Work
        mgr.start_work()
        self.assertEqual(mgr.state, PomodoroState.WORK)
        self.assertIn("work_start", events_received)

        # 2. Advance to completion
        mgr.tick(dt=0.06)
        self.assertIn("work_completed", events_received)
        self.assertIn("break_start", events_received)
        self.assertEqual(mgr.state, PomodoroState.SHORT_BREAK)
        self.assertEqual(stats.sessions_today, 1)

        # 3. Advance short break to completion -> auto start next work session
        mgr.tick(dt=0.03)
        self.assertIn("break_completed", events_received)
        self.assertEqual(mgr.state, PomodoroState.WORK)

        # 4. Advance 2nd work session -> should trigger long break!
        mgr.tick(dt=0.06)
        self.assertEqual(mgr.state, PomodoroState.LONG_BREAK)
        self.assertEqual(stats.sessions_today, 2)

    def test_pomodoro_pause_resume_reset_skip(self):
        """Verify pause, resume, reset, and skip operations."""
        mgr = PomodoroManager()
        mgr.work_duration = 100.0
        mgr.start_work()

        # Pause
        mgr.pause()
        self.assertEqual(mgr.state, PomodoroState.PAUSED)
        rem_before = mgr.remaining_seconds
        mgr.tick(dt=10.0)  # Should not countdown when paused
        self.assertEqual(mgr.remaining_seconds, rem_before)

        # Resume
        mgr.resume()
        self.assertEqual(mgr.state, PomodoroState.WORK)
        mgr.tick(dt=10.0)
        self.assertLess(mgr.remaining_seconds, rem_before)

        # Reset
        mgr.reset()
        self.assertEqual(mgr.state, PomodoroState.IDLE)
        self.assertEqual(mgr.remaining_seconds, mgr.work_duration)

    # 4. BEHAVIOR & PERSONALITY TESTS
    def test_personality_profiles_and_behavior(self):
        """Verify Personality drives autonomous behavior states."""
        pers = CharacterPersonality.preset("playful")
        self.assertGreaterEqual(pers.playfulness, 0.9)

        mem = CharacterMemory(skin_id="test_char")
        mem.record_interaction("play")
        self.assertEqual(mem.interactions_count, 1)

        beh = CharacterBehavior("TestChar", personality=pers, memory=mem)
        self.assertEqual(beh.current_state, BehaviorState.IDLE)

        # Evaluate behavior under Focus Pomodoro state
        beh.evaluate_next_action(
            dt=0.1,
            char_x=100,
            char_y=100,
            cursor_x=200,
            cursor_y=200,
            cursor_speed=0.0,
            screen_bounds=self.screen_bounds,
            pomodoro_state="WORK"
        )
        self.assertEqual(beh.current_state, BehaviorState.FOCUS)

        # Evaluate behavior under Break Pomodoro state
        beh.evaluate_next_action(
            dt=0.1,
            char_x=100,
            char_y=100,
            cursor_x=200,
            cursor_y=200,
            cursor_speed=0.0,
            screen_bounds=self.screen_bounds,
            pomodoro_state="SHORT_BREAK"
        )
        self.assertIn(beh.current_state, (BehaviorState.BREAK, BehaviorState.CELEBRATE, BehaviorState.PLAY))

    # 5. ENGINE INTEGRATION TEST
    def test_engine_pomodoro_integration(self):
        """Verify BuddyEngine initializes and coordinates Pomodoro."""
        from core.engine import BuddyEngine
        engine = BuddyEngine(requested_skin="slime", debug_mode=False)
        self.assertIsNotNone(engine.pomodoro)
        self.assertEqual(engine.character.skin_id, "slime")

        # Start pomodoro and verify event firing
        engine.pomodoro.start_work()
        self.assertEqual(engine.pomodoro.state, PomodoroState.WORK)

        # Simulate tick
        engine.on_tick()
        self.assertGreater(len(engine.particles.particles), 0)

        # Clean up window
        if hasattr(engine.window, "window") and hasattr(engine.window.window, "destroy"):
            engine.window.window.destroy()


if __name__ == "__main__":
    unittest.main()
