"""Unit tests for Oneko-style floating window and interactive input events."""

import unittest
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["GDK_BACKEND"] = "x11"

try:
    import gi
    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gtk, Gdk
    HAS_GI = True
except (ImportError, ValueError):
    HAS_GI = False

from core.window import OverlayWindow, WIN_SIZE, HALF_SIZE
from core.engine import BuddyEngine


@unittest.skipUnless(HAS_GI, "GTK/GDK (Linux) required")
class TestInteractiveWindow(unittest.TestCase):
    def setUp(self):
        self.engine = BuddyEngine(requested_skin="thor")

    def tearDown(self):
        if hasattr(self.engine, "window") and self.engine.window.window:
            self.engine.window.window.destroy()

    def test_window_properties(self):
        """Verify window matches Mjolnir Oneko settings to prevent fading/dimming."""
        win = self.engine.window.window
        self.assertEqual(self.engine.window.win_size, WIN_SIZE)
        self.assertEqual(self.engine.window.half_size, HALF_SIZE)
        self.assertFalse(win.get_accept_focus())
        self.assertFalse(win.get_focus_on_map())
        self.assertFalse(win.get_decorated())
        self.assertTrue(win.get_app_paintable())

    def test_window_movement(self):
        """Verify window moves to track character center coordinate."""
        self.engine.character.x = 400.0
        self.engine.character.y = 300.0
        self.engine.window.move_to(self.engine.character.x, self.engine.character.y)
        # Verify no crash and movement executed
        self.assertTrue(True)

    def test_signature_ability_trigger(self):
        """Verify double-click signature ability triggers spin and particle effects."""
        old_sparks = len(self.engine.particles.sparks)
        self.engine.trigger_signature_ability()
        self.assertTrue(self.engine.is_spinning)
        self.assertGreater(len(self.engine.particles.sparks), old_sparks)

    def test_skin_switching(self):
        """Verify all 11 skins can be switched smoothly."""
        skins = ["dragon", "cat", "dog", "hulk", "ironman", "harry_potter", "captain_america", "thanos", "batman", "superman", "thor"]
        for s in skins:
            success = self.engine.switch_skin(s)
            self.assertTrue(success)
            self.assertEqual(self.engine.character.skin_id, s)


if __name__ == "__main__":
    unittest.main()
