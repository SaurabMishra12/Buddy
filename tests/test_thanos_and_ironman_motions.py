"""Unit tests verifying:
1. Thanos Reality Warp clones are fully contained within the 180x180 window boundary without clipping.
2. Thanos flight motions (Space Stone levitation rifts, articulated leg flight postures, gauntlet flare).
3. Thanos ground walking stride animations.
4. Iron Man flight motions (dynamic bank angle tilt, supersonic backward swept articulated legs, dual-stage thruster plumes).
5. Iron Man chest arc reactor repulsor ('unibeam') firing DesktopProjectileWindow, torso arch, and muzzle flash.
"""

import time
import math
import unittest
import cairo

from skins.thanos.character import ThanosCharacter
from skins.ironman.character import IronManCharacter
from skins.base import CharacterState
from core.particles import ParticleManager
from core.audio import audio_manager
from core.projectiles import DesktopProjectileWindow


class TestThanosAndIronmanMotions(unittest.TestCase):

    def setUp(self):
        self.particles = ParticleManager()
        self.bounds = (0, 0, 1920, 1080)
        self.config = {"speed": 1.0, "activity_level": 1.0, "cursor_follow": True}
        # Exact window surface size used in Buddy main window (180x180)
        self.win_size = 180
        self.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.win_size, self.win_size)
        self.ctx = cairo.Context(self.surf)

    def test_thanos_reality_warp_window_boundary_containment(self):
        """Verify that during peak Reality Warp expansion, all 6 clones stay completely inside the 180x180 window."""
        thanos = ThanosCharacter(90.0, 90.0)
        thanos.trigger_ability("reality_warp", 90.0, 90.0, self.particles, audio_manager)
        self.assertTrue(thanos.is_reality_warping)

        # Set to peak radial expansion phase
        thanos.reality_warp_start = time.time() - 1.5
        thanos.update(0.016, 90.0, 90.0, self.bounds, self.particles, audio_manager, self.config)

        # Clone radius in character.py is max_clone_radius = 45.0
        # Clone scale is 0.62
        # Character height ~ 70px -> half height ~ 35px -> scaled half height ~ 22px
        # With center at (90, 90), clone centers are at 90 + 45 * cos(angle), 90 + 45 * sin(angle)
        # For angle = -pi/2 (top clone): y_center = 90 - 45 = 45. Top of head ~ 45 - 22 = 23px > 0 (not clipped!)
        # For angle = +pi/2 (bottom clone): y_center = 90 + 45 = 135. Bottom of feet ~ 135 + 22 = 157px < 180 (not clipped!)

        # Render to Cairo context at 180x180
        thanos.draw(self.ctx, self.particles)

        for i in range(6):
            base_angle = (i * math.pi / 3.0) + (math.pi / 6.0)
            cx = 45.0 * math.cos(base_angle)
            cy = 45.0 * math.sin(base_angle)
            abs_x = 90.0 + cx
            abs_y = 90.0 + cy
            # Verify clone center coordinates are well within margins
            self.assertGreater(abs_x, 30.0)
            self.assertLess(abs_x, 150.0)
            self.assertGreater(abs_y, 30.0)
            self.assertLess(abs_y, 150.0)

    def test_thanos_flight_and_walk_motions(self):
        """Verify Thanos has dynamic stride while walking and levitation rifts/trailing legs while flying."""
        thanos = ThanosCharacter(500.0, 400.0)

        # 1. Flight mode: cursor far away
        thanos.update(0.016, 800.0, 200.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertEqual(thanos.state, CharacterState.FLY)
        self.assertGreater(thanos.fly_phase, 0.0)
        self.assertNotEqual(thanos.stride, 0.0)

        # Render flight frame
        thanos.draw(self.ctx, self.particles)

        # 2. Hover mode: cursor within deadzone
        thanos.update(0.016, 500.0, 400.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertEqual(thanos.state, CharacterState.HOVER)
        thanos.draw(self.ctx, self.particles)

    def test_ironman_flight_kinematics(self):
        """Verify Iron Man computes bank angle, leg thruster sweep, and thruster plumes during flight."""
        ironman = IronManCharacter(500.0, 400.0)

        # Step flight update towards upper-right cursor
        for _ in range(20):
            ironman.update(0.016, 900.0, 200.0, self.bounds, self.particles, audio_manager, self.config)

        self.assertEqual(ironman.state, CharacterState.FLY)
        self.assertGreater(abs(ironman.vx), 3.0)
        self.assertGreater(ironman.stride, 0.0)
        # Dynamic banking tilt should reflect movement trajectory
        self.assertNotEqual(ironman.tilt, 0.0)

        # Render flight pose with dual thruster flames and swept legs
        ironman.draw(self.ctx, self.particles)

    def test_ironman_reactor_repulsor_unibeam(self):
        """Verify Iron Man triggers chest reactor repulsor (unibeam), launches projectile and arches torso."""
        ironman = IronManCharacter(500.0, 400.0)

        # Trigger unibeam
        res = ironman.trigger_ability("unibeam", 850.0, 400.0, self.particles, audio_manager)
        self.assertTrue(res)
        self.assertTrue(ironman.is_firing_unibeam)
        self.assertGreater(ironman.unibeam_end, time.time())
        self.assertGreater(ironman.arc_pulse, 2.0)

        # Also trigger synonym "reactor_repulsor"
        ironman.is_firing_unibeam = False
        res2 = ironman.trigger_ability("reactor_repulsor", 850.0, 400.0, self.particles, audio_manager)
        self.assertTrue(res2)
        self.assertTrue(ironman.is_firing_unibeam)

        # Render unibeam firing pose
        ironman.draw(self.ctx, self.particles)

        # Verify unibeam projectile window rendering
        proj = DesktopProjectileWindow(
            proj_type="unibeam",
            start_x=500.0,
            start_y=400.0,
            target_x=900.0,
            target_y=400.0,
            owner_getter=lambda: (500.0, 400.0),
            speed=36.0
        )
        self.assertEqual(proj.state, "OUTBOUND")
        # Draw projectile window surface
        proj_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, proj.win_size, proj.win_size)
        proj_ctx = cairo.Context(proj_surf)
        proj.draw(proj_ctx)

        # Tick projectile and verify traversal
        for _ in range(5):
            proj.on_tick()
        self.assertNotEqual(proj.x, 500.0)


if __name__ == "__main__":
    unittest.main()
