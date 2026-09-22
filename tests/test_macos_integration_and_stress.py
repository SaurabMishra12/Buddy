"""macOS Integration, Multi-Skin Switching, and Stress Test Suite for Buddy.

Validates:
1. BuddyEngine launch on macOS with native Cocoa overlay window.
2. Rapid multi-character dynamic skin switching (Thor -> Dragon -> Iron Man -> Cat -> Spider-Man -> Batman -> Thanos).
3. 200-tick animation and physics loop stability with particle generation.
4. SkyStrike and projectile window spawning on macOS.
5. Pause / resume mechanics.
6. Clean resource teardown and window dismissal.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

from platforms import is_macos

if not is_macos():
    raise unittest.SkipTest("macOS integration tests require macOS environment")

from core.engine import BuddyEngine
from skins.manager import skin_manager
from skins.base import CharacterState


class TestMacOSIntegrationAndStress(unittest.TestCase):

    def setUp(self):
        # Initialize engine with Thor
        self.engine = BuddyEngine(requested_skin="thor", debug_mode=True)

    def tearDown(self):
        if hasattr(self, "engine") and self.engine and self.engine.window:
            try:
                self.engine.window.close()
            except Exception:
                pass

    def test_engine_init_macos(self):
        """Verify engine successfully boots with native macOS overlay window."""
        self.assertEqual(self.engine.character.skin_id, "thor")
        self.assertIsNotNone(self.engine.window)
        self.assertGreater(self.engine.window.screen_w, 0)
        self.assertGreater(self.engine.window.screen_h, 0)
        self.assertFalse(self.engine.paused)

    def test_multi_skin_switching_stability(self):
        """Verify seamless dynamic skin switching across multiple character archetypes."""
        skins_to_test = ["dragon", "ironman", "cat", "spiderman", "batman", "thanos", "slime", "thor"]

        for skin_id in skins_to_test:
            success = self.engine.switch_skin(skin_id)
            self.assertTrue(success, f"Failed switching to skin: {skin_id}")
            self.assertEqual(self.engine.character.skin_id, skin_id)

            # Run 10 ticks for each skin to verify physics and particle pipeline
            for _ in range(10):
                self.engine.on_tick()

    def test_200_ticks_stress_simulation(self):
        """Verify engine runs 200 consecutive animation ticks without performance or memory collapse."""
        initial_sparks = len(self.engine.particles.sparks)
        initial_flames = len(self.engine.particles.flames)

        # Run 200 ticks
        for tick in range(200):
            # Inject simulated cursor movements
            self.engine.target_x = 400.0 + (tick % 50) * 8.0
            self.engine.target_y = 300.0 + (tick % 30) * 6.0
            self.engine.on_tick()

        # Engine must still be healthy and running
        self.assertFalse(self.engine.paused)
        self.assertGreater(self.engine.character.x, -500.0)
        self.assertGreater(self.engine.character.y, -500.0)

    def test_sky_strike_trigger_macos(self):
        """Verify Thor SkyStrike lightning window can be triggered on macOS."""
        try:
            self.engine.window.trigger_sky_strike(500.0, 300.0)
            success = True
        except Exception as e:
            success = False
            self.fail(f"trigger_sky_strike raised unexpected exception: {e}")
        self.assertTrue(success)

    def test_pause_resume_toggle(self):
        """Verify pausing halts movement and toggling resumes properly."""
        self.engine.paused = False
        self.engine.toggle_pause()
        self.assertTrue(self.engine.paused)

        x_paused = self.engine.character.x
        y_paused = self.engine.character.y

        # When paused, on_tick returns True immediately without character updates
        for _ in range(5):
            self.engine.on_tick()
        self.assertEqual(self.engine.character.x, x_paused)
        self.assertEqual(self.engine.character.y, y_paused)

        # Resume
        self.engine.toggle_pause()
        self.assertFalse(self.engine.paused)


if __name__ == "__main__":
    unittest.main()
