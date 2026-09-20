import unittest
from core.particles import ParticleManager, Spark, FlameParticle, Shockwave, LightningBolt


class TestParticles(unittest.TestCase):
    def setUp(self):
        self.mgr = ParticleManager(max_particles=50)

    def test_burst_sparks_and_limit(self):
        self.mgr.burst_sparks(100.0, 100.0, count=30)
        self.assertEqual(len(self.mgr.sparks), 30)

        # Enforce max limit
        self.mgr.burst_sparks(100.0, 100.0, count=40)
        self.assertLessEqual(len(self.mgr.sparks), 50)

    def test_particle_decay_and_cleanup(self):
        spark = Spark(50.0, 50.0, decay=0.6)
        self.assertTrue(spark.update())
        # Second step exceeds 1.0 life decay
        self.assertFalse(spark.update())

    def test_shockwave_expansion(self):
        sw = Shockwave(100.0, 100.0, max_radius=30.0)
        init_r = sw.radius
        sw.update()
        self.assertGreater(sw.radius, init_r)

    def test_sky_strike(self):
        self.mgr.sky_strike(200.0, 300.0)
        self.assertEqual(len(self.mgr.bolts), 1)
        self.assertGreater(len(self.mgr.shockwaves), 0)
        self.assertGreater(len(self.mgr.sparks), 0)

    def test_new_particle_types(self):
        self.mgr.burst_hearts(100.0, 100.0, count=5)
        self.mgr.burst_stars(100.0, 100.0, count=5)
        self.mgr.burst_confetti(100.0, 100.0, count=5)
        self.mgr.burst_dust(100.0, 100.0, count=5)
        self.mgr.energy_orbs(100.0, 100.0, count=2)

        self.assertEqual(len(self.mgr.hearts), 5)
        self.assertEqual(len(self.mgr.stars), 5)
        self.assertEqual(len(self.mgr.confetti), 5)
        self.assertEqual(len(self.mgr.dust), 5)
        self.assertEqual(len(self.mgr.orbs), 2)

        # Update should advance all particles
        self.mgr.update()
        self.mgr.clear()
        self.assertEqual(len(self.mgr.particles), 0)

    def test_animation_easing_primitives(self):
        from rendering.animation import (
            ease_in_quad,
            ease_out_quad,
            ease_in_out_cubic,
            ease_out_bounce,
            spring_step,
            interpolate,
        )
        self.assertAlmostEqual(ease_in_quad(0.0), 0.0)
        self.assertAlmostEqual(ease_in_quad(1.0), 1.0)
        self.assertAlmostEqual(ease_out_quad(1.0), 1.0)
        self.assertAlmostEqual(ease_in_out_cubic(0.5), 0.5)

        # Test bounce boundary
        self.assertAlmostEqual(ease_out_bounce(0.0), 0.0)
        self.assertAlmostEqual(ease_out_bounce(1.0), 1.0)

        # Test spring
        pos, vel = spring_step(current=0.0, target=100.0, velocity=0.0, dt=0.016)
        self.assertGreater(pos, 0.0)
        self.assertGreater(vel, 0.0)

        # Test interpolate
        val = interpolate(10.0, 20.0, 0.5, "ease_out")
        self.assertGreater(val, 15.0)


if __name__ == "__main__":
    unittest.main()
