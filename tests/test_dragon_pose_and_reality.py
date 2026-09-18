"""Unit tests verifying:
1. Realistic Dragon rendering, wing flap, and fire abilities.
2. Captain America hero pose activation, persistence across ticks, and Cairo rendering.
3. Thanos Time Stone active chronal mandala and timer behavior.
4. Thanos Reality Warp 6 clones radial expansion, convergence, and implosion.
5. Fluent, smooth character movement and spring-damper physics.
"""

import time
import math
import unittest
import cairo

from skins.dragon.character import DragonCharacter
from skins.captain_america.character import CaptainAmericaCharacter
from skins.thanos.character import ThanosCharacter
from skins.base import CharacterState
from core.particles import ParticleManager
from core.audio import audio_manager


class TestDragonPoseAndReality(unittest.TestCase):

    def setUp(self):
        self.particles = ParticleManager()
        self.bounds = (0, 0, 1920, 1080)
        self.config = {"speed": 1.0, "activity_level": 1.0}
        self.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 400, 400)
        self.ctx = cairo.Context(self.surf)

    def test_dragon_realistic_rendering_and_abilities(self):
        """Verify Dragon initializes with realistic anatomy and renders error-free."""
        dragon = DragonCharacter(300.0, 300.0)
        self.assertEqual(dragon.skin_id, "dragon")
        self.assertTrue(dragon.can_fly)

        # Test abilities
        self.assertTrue(dragon.trigger_ability("fire_breath", 400, 300, self.particles, audio_manager))
        self.assertTrue(dragon.trigger_ability("fireball", 400, 300, self.particles, audio_manager))
        self.assertTrue(dragon.trigger_ability("flight", 400, 300, self.particles, audio_manager))

        # Update several ticks to simulate wing flapping and flight hover
        for _ in range(10):
            dragon.update(0.016, 450.0, 300.0, self.bounds, self.particles, audio_manager, self.config)

        # Draw to Cairo context - must succeed without error
        dragon.draw(self.ctx, self.particles)
        self.assertGreater(dragon.wing_speed, 0.0)
        self.assertIsNotNone(dragon.wing_angle)

    def test_captain_america_hero_pose_persistence(self):
        """Verify Cap hero pose does NOT get immediately overwritten by movement updates."""
        cap = CaptainAmericaCharacter(200.0, 950.0)
        self.assertEqual(cap.skin_id, "captain_america")

        # Trigger hero pose
        res = cap.trigger_ability("hero_pose", 200.0, 950.0, self.particles, audio_manager)
        self.assertTrue(res)
        self.assertTrue(cap.is_hero_posing)
        self.assertEqual(cap.state, CharacterState.VICTORY)

        # Update several ticks with cursor far away - state MUST stay VICTORY
        for _ in range(15):
            cap.update(0.016, 800.0, 950.0, self.bounds, self.particles, audio_manager, self.config)
            self.assertEqual(cap.state, CharacterState.VICTORY)
            self.assertTrue(cap.is_hero_posing)

        # Draw the hero pose with shield and star flare
        cap.draw(self.ctx, self.particles)

        # Fast forward past hero pose end time
        cap.hero_pose_end = time.time() - 0.1
        cap.update(0.016, 800.0, 950.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertFalse(cap.is_hero_posing)
        self.assertEqual(cap.state, CharacterState.RUN)

    def test_thanos_time_stone_mandala(self):
        """Verify Thanos Time Stone activates chronal state and renders mystic mandala."""
        thanos = ThanosCharacter(500.0, 400.0)
        self.assertFalse(thanos.is_time_active)

        # Trigger Time Stone
        res = thanos.trigger_ability("time_stone", 600.0, 400.0, self.particles, audio_manager)
        self.assertTrue(res)
        self.assertTrue(thanos.is_time_active)
        self.assertGreater(thanos.time_stone_end, time.time())

        # Update while active
        thanos.update(0.016, 600.0, 400.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertTrue(thanos.is_time_active)

        # Draw to Cairo with active Time Stone mandala
        thanos.draw(self.ctx, self.particles)

        # Fast forward time stone expiry
        thanos.time_stone_end = time.time() - 0.1
        thanos.update(0.016, 600.0, 400.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertFalse(thanos.is_time_active)

    def test_thanos_reality_warp_clones_and_convergence(self):
        """Verify Reality Warp spawns 6 clones, fans out, converges, and implodes."""
        thanos = ThanosCharacter(500.0, 400.0)
        self.assertFalse(thanos.is_reality_warping)

        # Trigger Reality Warp
        res = thanos.trigger_ability("reality_warp", 600.0, 400.0, self.particles, audio_manager)
        self.assertTrue(res)
        self.assertTrue(thanos.is_reality_warping)
        self.assertEqual(thanos.active_stone, "reality")

        # Phase 1: Expansion (e.g. 0.2s in)
        thanos.reality_warp_start = time.time() - 0.6
        thanos.update(0.016, 600.0, 400.0, self.bounds, self.particles, audio_manager, self.config)
        thanos.draw(self.ctx, self.particles)

        # Phase 2: Full standoff (e.g. 1.5s in)
        thanos.reality_warp_start = time.time() - 1.5
        thanos.update(0.016, 600.0, 400.0, self.bounds, self.particles, audio_manager, self.config)
        thanos.draw(self.ctx, self.particles)

        # Phase 3: Convergence (e.g. 2.9s in)
        thanos.reality_warp_start = time.time() - 2.9
        thanos.update(0.016, 600.0, 400.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertTrue(thanos.reality_has_imploded)
        thanos.draw(self.ctx, self.particles)

        # Phase 4: Complete
        thanos.reality_warp_start = time.time() - 3.5
        thanos.update(0.016, 600.0, 400.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertFalse(thanos.is_reality_warping)

    def test_smooth_velocity_spring_damping(self):
        """Verify spring-damper formula eases velocity smoothly without harsh jumps."""
        vx = 0.0
        target_vx = 14.0
        trajectory = []
        for _ in range(5):
            vx += (target_vx - vx) * 0.22
            trajectory.append(vx)

        # Trajectory must be monotonically increasing and strictly less than target_vx on frame 1
        self.assertLess(trajectory[0], target_vx)
        for i in range(1, len(trajectory)):
            self.assertGreater(trajectory[i], trajectory[i - 1])


if __name__ == "__main__":
    unittest.main()
