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


if __name__ == "__main__":
    unittest.main()
