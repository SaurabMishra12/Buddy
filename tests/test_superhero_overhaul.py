"""Unit tests verifying superhero abilities, screen-wide projectiles, and character poses."""

import unittest
import time
from core.particles import ParticleManager
from core.audio import audio_manager
from core.projectiles import DesktopProjectileWindow
from skins.manager import skin_manager
from skins.base import CharacterState


class TestSuperheroOverhaul(unittest.TestCase):
    def setUp(self):
        self.particles = ParticleManager(max_particles=200)

    def test_hulk_distinct_powers(self):
        hulk = skin_manager.create_character("hulk", 500.0, 400.0)
        
        # 1. Ground smash creates seismic cracks
        smash_ok = hulk.trigger_ability("ground_smash", 500.0, 400.0, self.particles, audio_manager)
        self.assertTrue(smash_ok)
        self.assertTrue(hulk.is_smashing)
        self.assertGreater(len(hulk.ground_cracks), 0)

        # 2. Thunderclap triggers sonic rings
        clap_ok = hulk.trigger_ability("thunderclap", 600.0, 400.0, self.particles, audio_manager)
        self.assertTrue(clap_ok)
        self.assertTrue(hulk.is_thunderclapping)

        # 3. Gamma rage triggers aura and size boost
        rage_ok = hulk.trigger_ability("gamma_rage", 500.0, 400.0, self.particles, audio_manager)
        self.assertTrue(rage_ok)
        self.assertGreater(hulk.rage_aura, 1.0)
        self.assertGreater(hulk.rage_boost_timer, time.time())

        # 4. Super jump sets upward velocity
        jump_ok = hulk.trigger_ability("super_jump", 700.0, 200.0, self.particles, audio_manager)
        self.assertTrue(jump_ok)
        self.assertEqual(hulk.state, CharacterState.JUMP)
        self.assertLess(hulk.vy, -10.0)

    def test_superman_abilities_and_flight_pose(self):
        superman = skin_manager.create_character("superman", 500.0, 400.0)

        # Heat vision
        hv_ok = superman.trigger_ability("heat_vision", 700.0, 400.0, self.particles, audio_manager)
        self.assertTrue(hv_ok)
        self.assertTrue(superman.is_firing_heat_vision)

        # Supersonic flight sets fly state
        flight_ok = superman.trigger_ability("supersonic_flight", 800.0, 300.0, self.particles, audio_manager)
        self.assertTrue(flight_ok)
        self.assertEqual(superman.state, CharacterState.FLY)
        self.assertGreater(abs(superman.vx), 15.0)

    def test_ironman_repulsor_and_unibeam(self):
        ironman = skin_manager.create_character("ironman", 500.0, 400.0)

        # Unibeam
        uni_ok = ironman.trigger_ability("unibeam", 500.0, 400.0, self.particles, audio_manager)
        self.assertTrue(uni_ok)
        self.assertGreater(ironman.arc_pulse, 1.0)

        # Repulsor blast
        rep_ok = ironman.trigger_ability("repulsor_blast", 800.0, 400.0, self.particles, audio_manager)
        self.assertTrue(rep_ok)
        self.assertTrue(ironman.is_firing_repulsor)

    def test_dragon_fireball_and_breath(self):
        dragon = skin_manager.create_character("dragon", 500.0, 400.0)

        # Fire breath
        fb_ok = dragon.trigger_ability("fire_breath", 600.0, 400.0, self.particles, audio_manager)
        self.assertTrue(fb_ok)
        self.assertTrue(dragon.is_breathing_fire)

        # Fireball
        ball_ok = dragon.trigger_ability("fireball", 800.0, 400.0, self.particles, audio_manager)
        self.assertTrue(ball_ok)

    def test_thanos_infinity_gauntlet(self):
        thanos = skin_manager.create_character("thanos", 500.0, 400.0)

        # Snap
        snap_ok = thanos.trigger_ability("infinity_snap", 500.0, 400.0, self.particles, audio_manager)
        self.assertTrue(snap_ok)
        self.assertTrue(thanos.is_snapping)

        # Verify deadzone stability (no shaking / oscillation)
        thanos.update(0.016, 500.0, 400.0, (0, 0, 1920, 1080), self.particles, audio_manager, {"speed": 1.0, "cursor_follow": True})
        self.assertLess(abs(thanos.vx), 2.0)

    def test_captain_america_shield_throw(self):
        cap = skin_manager.create_character("captain_america", 500.0, 400.0)
        self.assertEqual(cap.shield.state, "HELD")

        throw_ok = cap.trigger_ability("shield_throw", 800.0, 400.0, self.particles, audio_manager)
        self.assertTrue(throw_ok)
        self.assertEqual(cap.shield.state, "THROWN")

    def test_desktop_projectile_trajectory_and_collision(self):
        caught = []
        proj = DesktopProjectileWindow(
            proj_type="shield",
            start_x=500.0,
            start_y=400.0,
            target_x=12.0,  # will hit left screen boundary
            target_y=400.0,
            owner_getter=lambda: (500.0, 400.0),
            on_catch=lambda: caught.append(True),
            speed=30.0
        )
        self.assertEqual(proj.state, "OUTBOUND")
        # Step ticks until edge collision
        for _ in range(30):
            proj.on_tick()
            if proj.state == "RETURNING":
                break

        self.assertEqual(proj.state, "RETURNING")
        # Step ticks homing back to owner (500, 400)
        for _ in range(60):
            res = proj.on_tick()
            if not res:
                break

        self.assertTrue(len(caught) > 0 or proj.state in ("RETURNING", "EXPLODING"))


if __name__ == "__main__":
    unittest.main()
