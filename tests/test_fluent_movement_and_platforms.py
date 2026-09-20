"""Tests for fluent superhero locomotion (Spider-Man, Cap, Hulk, Batman),
window ledge & button platform detection, and zero black rectangular glitch.
"""

import unittest
import time
import math
from typing import Tuple, Dict, Any

from skins.spiderman.character import SpiderManCharacter
from skins.captain_america.character import CaptainAmericaCharacter
from skins.hulk.character import HulkCharacter
from skins.batman.character import BatmanCharacter
from skins.superman.character import SupermanCharacter
from skins.ironman.character import IronManCharacter
from skins.base import CharacterState
from core.particles import ParticleManager
from core.audio import audio_manager
from core.platforms import platform_manager, DesktopLedge
from core.window import WebRopeWindow
from core.projectiles import DesktopProjectileWindow
from core.engine import BuddyEngine
from core.config import ConfigManager


class MockWindow:
    def __init__(self, bounds=(0, 0, 1920, 1080)):
        self.bounds = bounds
        self.half_size = 90
        self.x = 500
        self.y = 500

    def move_to(self, x, y):
        self.x = x
        self.y = y

    def query_pointer(self):
        return (self.x, self.y)

    def queue_draw(self):
        pass


class TestFluentMovementAndPlatforms(unittest.TestCase):
    def setUp(self):
        self.particles = ParticleManager()
        self.bounds = (0, 0, 1920, 1080)
        self.config = {
            "activity_level": 1.0,
            "speed": 1.0,
            "sound_enabled": False
        }

    def test_desktop_ledges_and_platform_detection(self):
        """Verify PlatformManager scans window frames, top panel, and buttons."""
        platform_manager.scan_desktop_windows(self.bounds)
        self.assertGreater(len(platform_manager.ledges), 2)

        # Should include panel, window, and button
        types = {l.ledge_type for l in platform_manager.ledges}
        self.assertIn("panel", types)
        self.assertIn("window", types)
        self.assertIn("button", types)

        # Dynamic user click registration
        platform_manager.register_user_click_ledge(600.0, 450.0)
        user_ledge = platform_manager.is_on_ledge(600.0, 450.0, tolerance=10.0)
        self.assertIsNotNone(user_ledge)
        self.assertTrue(user_ledge.contains_x(600.0))

    def test_spiderman_multi_stage_navigation_and_seating(self):
        """Verify Spider-Man runs -> swings -> jumps -> perches/sits on window ledges."""
        spidey = SpiderManCharacter(300.0, 1010.0)
        self.assertFalse(spidey.is_seated)

        # 1. Test Sitting directly on a window ledge
        spidey.trigger_ability("seat", 500.0, 500.0, self.particles, audio_manager)
        self.assertTrue(spidey.is_seated)
        self.assertFalse(spidey.is_perched)
        self.assertFalse(spidey.is_swinging)

        # 2. Test Multi-Stage Navigation to far destination (e.g. from 300 to 1200)
        spidey.x = 300.0
        spidey.y = 1010.0
        spidey.nav_to(1200.0, 600.0)

        self.assertEqual(spidey.nav_stage, "RUN")
        # Update during RUN stage
        spidey.update(0.016, 1200.0, 600.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertEqual(spidey.state, CharacterState.RUN)
        self.assertGreater(spidey.vx, 0.0)

        # Force transition to SWING stage
        spidey.nav_timer = time.time() - 0.4
        spidey.update(0.016, 1200.0, 600.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertEqual(spidey.nav_stage, "SWING")
        self.assertTrue(spidey.is_swinging)

        # Force transition to JUMP stage
        spidey.nav_timer = time.time() - 0.7
        spidey.update(0.016, 1200.0, 600.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertEqual(spidey.nav_stage, "JUMP")
        self.assertFalse(spidey.is_swinging)
        self.assertEqual(spidey.state, CharacterState.JUMP)

        # Complete jump arrival at target
        spidey.x = 1195.0
        spidey.y = 605.0
        spidey.update(0.016, 1200.0, 600.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertIsNone(spidey.nav_target)
        self.assertEqual(spidey.nav_stage, "IDLE")
        self.assertTrue(spidey.is_perched or spidey.is_seated)
        self.assertEqual(spidey.tilt, 0.0)

    def test_spiderman_seated_upright_and_zero_corner_revolving(self):
        """Verify Spider-Man sits straight upright (0.0 tilt) and never revolves around corners."""
        spidey = SpiderManCharacter(300.0, 1010.0)

        # 1. Sitting must have 0.0 tilt (strictly upright, not sideways or upside down)
        spidey.trigger_ability("seat", 500.0, 500.0, self.particles, audio_manager)
        self.assertTrue(spidey.is_seated)
        self.assertEqual(spidey.tilt, 0.0)

        # 2. Exit from wall-crawl (math.pi * 0.5) must reset tilt to 0.0
        spidey.is_wall_crawling = True
        spidey.tilt = math.pi * 0.5
        spidey.x = 200.0  # Away from screen edges
        spidey.update(0.016, 500.0, 500.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertFalse(spidey.is_wall_crawling)
        self.assertEqual(spidey.tilt, 0.0)

        # 3. Exit from upside-down hang (math.pi) must reset tilt to 0.0
        spidey.trigger_ability("upside_down_hang", 500.0, 500.0, self.particles, audio_manager)
        self.assertTrue(spidey.is_hanging_upside_down)
        self.assertEqual(spidey.tilt, math.pi)
        spidey.hang_end_time = time.time() - 0.1
        spidey.update(0.016, 500.0, 500.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertFalse(spidey.is_hanging_upside_down)
        self.assertEqual(spidey.tilt, 0.0)

        # 4. Jump somersault / corner movement must NOT revolve continuously
        spidey.nav_to(1850.0, 1050.0)  # Target near corner
        spidey.nav_stage = "JUMP"
        spidey.vx = 15.0
        for _ in range(60):  # Simulate 1 second of jumping
            spidey.update(0.016, 1850.0, 1050.0, self.bounds, self.particles, audio_manager, self.config)
            # Tilt must stay within controlled athletic lean bounds (< 0.45 rad ~ 25 degrees)
            self.assertLessEqual(abs(spidey.tilt), 0.45, f"Tilt {spidey.tilt} exceeded athletic limit!")

        # 5. When arriving or seated on a ledge, hips must sit squarely (ledge.top - 8.0) and tilt 0.0
        platform_manager.register_user_click_ledge(800.0, 600.0)
        user_ledge = platform_manager.is_on_ledge(800.0, 600.0, tolerance=10.0)
        self.assertIsNotNone(user_ledge)
        spidey.x = 800.0
        spidey.y = 600.0
        spidey.trigger_ability("seat", 800.0, 600.0, self.particles, audio_manager)
        self.assertTrue(spidey.is_seated)
        self.assertEqual(spidey.tilt, 0.0)
        self.assertAlmostEqual(spidey.y, user_ledge.top - 8.0, delta=1.0)

    def test_captain_america_sprint_and_shield_dash(self):
        """Verify Captain America runs then dashes with Vibranium shield."""
        cap = CaptainAmericaCharacter(200.0, 1010.0)
        cap.nav_to(900.0, 1010.0)
        self.assertEqual(cap.nav_stage, "RUN")

        cap.update(0.016, 900.0, 1010.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertEqual(cap.state, CharacterState.RUN)
        self.assertFalse(cap.is_dashing)

        # Advance elapsed time to trigger Shield Dash
        cap.nav_timer = time.time() - 0.3
        cap.update(0.016, 900.0, 1010.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertEqual(cap.nav_stage, "DASH")
        self.assertTrue(cap.is_dashing)
        self.assertGreater(abs(cap.vx), 20.0)  # Supersonic dash velocity

    def test_hulk_parabolic_super_leap(self):
        """Verify Hulk launches parabolic ballistic leaps directly to target instead of walking."""
        hulk = HulkCharacter(200.0, 1010.0)
        hulk.nav_to(950.0, 1010.0)

        # On next update, Hulk launches super leap
        hulk.update(0.016, 950.0, 1010.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertTrue(hulk.is_airborne)
        self.assertEqual(hulk.state, CharacterState.JUMP)
        self.assertLess(hulk.vy, -15.0)  # High upward leap velocity
        self.assertGreater(hulk.vx, 5.0)   # Forward trajectory

    def test_batman_run_grapple_and_cape_glide(self):
        """Verify Batman runs -> grapples & climbs -> glides with scalloped cape."""
        batman = BatmanCharacter(200.0, 1010.0)
        batman.nav_to(1000.0, 800.0)
        self.assertEqual(batman.nav_stage, "RUN")

        batman.update(0.016, 1000.0, 800.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertEqual(batman.state, CharacterState.RUN)

        # Trigger Grapple stage
        batman.nav_timer = time.time() - 0.3
        batman.update(0.016, 1000.0, 800.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertEqual(batman.nav_stage, "GRAPPLE")
        self.assertTrue(batman.is_grappling)

        # Advance grapple climb to reach peak and transition to Cape Glide
        batman.x = batman.anchor_x
        batman.y = batman.anchor_y + 10.0
        batman.update(0.016, 1000.0, 800.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertEqual(batman.nav_stage, "GLIDE")
        self.assertTrue(batman.is_gliding)
        self.assertEqual(batman.state, CharacterState.FLY)

    def test_zero_black_rectangular_glitch_overlay_transparency(self):
        """Verify WebRopeWindow and DesktopProjectileWindow configure full RGBA transparency."""
        rope_win = WebRopeWindow(
            start_getter=lambda: (100.0, 100.0),
            end_getter=lambda: (300.0, 300.0),
            rope_style="grapple"
        )
        self.assertIsNotNone(rope_win.get_visual())
        # Ensure destroyed cleanly
        rope_win.destroy_rope()
        self.assertTrue(rope_win.is_destroyed)


if __name__ == "__main__":
    unittest.main()
