"""Live display smoke test: runs 120 animation ticks (2 seconds) on display."""

import unittest
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure X11 backend
os.environ["GDK_BACKEND"] = "x11"

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gtk, GLib

from core.engine import BuddyEngine
from skins.manager import skin_manager


class TestLiveDisplaySmoke(unittest.TestCase):
    def test_engine_run_and_skin_switch(self):
        # Instantiate engine
        engine = BuddyEngine(requested_skin="thor", debug_mode=True)
        self.assertEqual(engine.character.skin_id, "thor")

        ticks_counted = 0
        max_ticks = 60

        def test_step():
            nonlocal ticks_counted
            ticks_counted += 1

            # At tick 30, test dynamic skin switch to dragon
            if ticks_counted == 30:
                success = engine.switch_skin("dragon")
                self.assertTrue(success)
                self.assertEqual(engine.character.skin_id, "dragon")

            # At tick 50, test dynamic skin switch to cat
            if ticks_counted == 50:
                success = engine.switch_skin("cat")
                self.assertTrue(success)
                self.assertEqual(engine.character.skin_id, "cat")

            # At tick 55, restore skin to thor
            if ticks_counted == 55:
                engine.switch_skin("thor")

            if ticks_counted >= max_ticks:
                Gtk.main_quit()
                return False
            return True

        GLib.timeout_add(16, test_step)
        engine.window.show()

        # Run loop until Gtk.main_quit()
        Gtk.main()

        self.assertGreaterEqual(ticks_counted, max_ticks)

    def test_superhero_live_smoke(self):
        """Smoke test verifying Thanos, Superman, Ironman, Hulk, and Cap in live GTK loop."""
        engine = BuddyEngine(requested_skin="thanos", debug_mode=False)
        skins_to_test = ["thanos", "superman", "ironman", "hulk", "captain_america"]
        tick = 0
        skin_idx = 0

        def step():
            nonlocal tick, skin_idx
            tick += 1
            if tick % 15 == 0:
                skin_idx += 1
                if skin_idx < len(skins_to_test):
                    engine.switch_skin(skins_to_test[skin_idx])
                    engine.trigger_signature_ability()
                else:
                    Gtk.main_quit()
                    return False
            return True

        GLib.timeout_add(16, step)
        engine.window.show()
        Gtk.main()
        self.assertEqual(skin_idx, len(skins_to_test))


if __name__ == "__main__":
    unittest.main()
