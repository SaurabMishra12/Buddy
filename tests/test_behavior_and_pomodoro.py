"""Unit tests for Buddy 2.0 Behavior engine and Pomodoro system."""

import unittest
import tempfile
from pathlib import Path

from behavior.personality import CharacterPersonality
from behavior.memory import CharacterMemory
from behavior.state_machine import CharacterBehavior, BehaviorState
from pomodoro.manager import PomodoroManager, PomodoroState
from pomodoro.statistics import PomodoroStats
from pomodoro.notifications import NotificationManager


class TestBehaviorAndPomodoro(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_personality_profiles_and_clamping(self):
        p = CharacterPersonality(energy=1.5, curiosity=-0.2, playfulness=0.8)
        self.assertEqual(p.energy, 1.0)
        self.assertEqual(p.curiosity, 0.0)
        self.assertEqual(p.playfulness, 0.8)

        data = p.to_dict()
        p2 = CharacterPersonality.from_dict(data)
        self.assertEqual(p2.energy, 1.0)
        self.assertEqual(p2.playfulness, 0.8)

        preset = CharacterPersonality.preset("energetic")
        self.assertGreater(preset.energy, 0.8)

    def test_character_memory_persistence(self):
        mem = CharacterMemory(skin_id="thor", memory_dir=self.temp_path)
        self.assertEqual(mem.interactions_count, 0)
        mem.record_interaction("hammer_spin")
        mem.record_time(10.0, 600.0, 500.0)
        mem.record_pomodoro_completed()
        self.assertTrue(mem.save())

        # Reload
        mem2 = CharacterMemory(skin_id="thor", memory_dir=self.temp_path)
        self.assertEqual(mem2.interactions_count, 1)
        self.assertEqual(mem2.last_special_ability, "hammer_spin")
        self.assertEqual(mem2.pomodoro_sessions_completed, 1)
        self.assertGreater(mem2.total_active_seconds, 9.0)

        # Reset
        mem2.reset()
        self.assertEqual(mem2.interactions_count, 0)

    def test_behavior_state_transitions(self):
        b = CharacterBehavior("Thor", can_fly=True)
        transitions = []
        b.add_listener(lambda old_s, new_s: transitions.append((old_s, new_s)))

        self.assertEqual(b.current_state, BehaviorState.IDLE)
        b.transition_to(BehaviorState.FLY, duration=3.0)
        self.assertEqual(b.current_state, BehaviorState.FLY)
        self.assertEqual(transitions[-1], (BehaviorState.IDLE, BehaviorState.FLY))

        # Pomodoro focus override
        b.evaluate_next_action(
            dt=0.1,
            char_x=500.0,
            char_y=400.0,
            cursor_x=500.0,
            cursor_y=400.0,
            cursor_speed=0.0,
            screen_bounds=(0, 0, 1920, 1080),
            pomodoro_state="WORK",
        )
        self.assertEqual(b.current_state, BehaviorState.FOCUS)
        self.assertTrue(b.is_focusing_pomodoro)

    def test_pomodoro_manager_lifecycle(self):
        stats_file = self.temp_path / "pomodoro_stats.json"
        stats = PomodoroStats(stats_file=stats_file)
        notif = NotificationManager(enabled=False)
        mgr = PomodoroManager(stats=stats, notifications=notif)

        events = []
        mgr.add_listener(lambda ev, st, rem: events.append(ev))

        self.assertEqual(mgr.state, PomodoroState.IDLE)
        mgr.work_duration = 0.2  # 0.2 seconds for fast test
        mgr.short_break_duration = 0.1
        mgr.start_work()
        self.assertEqual(mgr.state, PomodoroState.WORK)
        self.assertIn("work_start", events)

        # Pause and resume
        mgr.pause()
        self.assertEqual(mgr.state, PomodoroState.PAUSED)
        mgr.resume()
        self.assertEqual(mgr.state, PomodoroState.WORK)

        # Tick down to completion
        mgr.tick(dt=0.25)
        # Should complete work and auto-start short break
        self.assertIn("work_completed", events)
        self.assertEqual(mgr.state, PomodoroState.SHORT_BREAK)
        self.assertEqual(stats.sessions_today, 1)

        # Tick break to completion
        mgr.tick(dt=0.15)
        self.assertIn("break_completed", events)
        self.assertEqual(mgr.state, PomodoroState.IDLE)


if __name__ == "__main__":
    unittest.main()
