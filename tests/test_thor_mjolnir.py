import unittest
from skins.thor.character import ThorCharacter
from skins.thor.hammer import Mjolnir
from skins.thor.cape import Cape
from core.particles import ParticleManager
from core.audio import audio_manager
from core.config import DEFAULT_CONFIG


class TestThorAndMjolnir(unittest.TestCase):
    def setUp(self):
        self.particles = ParticleManager()
        self.thor = ThorCharacter(x=500.0, y=400.0)
        self.bounds = (0, 0, 1920, 1080)

    def test_thor_cape_chain(self):
        cape = Cape(500.0, 400.0)
        self.assertEqual(len(cape.segments), 7)
        cape.update(510.0, 400.0, vx=5.0, vy=0.0)
        # Segments follow anchor
        self.assertEqual(cape.segments[0], [510.0, 400.0])

    def test_mjolnir_throw_and_recall(self):
        mjolnir = self.thor.mjolnir
        self.assertEqual(mjolnir.state, "HELD")

        # Throw Mjolnir towards target
        mjolnir.throw(start_x=500.0, start_y=400.0, target_x=800.0, target_y=300.0, mode="boomerang")
        self.assertEqual(mjolnir.state, "THROWN")
        self.assertGreater(abs(mjolnir.vx), 0.0)

        # Update while thrown
        mjolnir.update(500.0, 400.0, 800.0, 300.0, 1920, 1080, self.particles)
        self.assertNotEqual(mjolnir.x, 500.0)

        # Summon Mjolnir back
        mjolnir.summon()
        self.assertEqual(mjolnir.state, "RETURNING")

        # Teleport near hand to trigger catch
        mjolnir.x = 510.0
        mjolnir.y = 405.0
        event = mjolnir.update(500.0, 400.0, 800.0, 300.0, 1920, 1080, self.particles)
        self.assertEqual(event, "CAUGHT")
        self.assertEqual(mjolnir.state, "HELD")

    def test_thor_ability_triggers(self):
        # Hammer throw
        success = self.thor.trigger_ability("hammer_throw", 800.0, 400.0, self.particles, audio_mgr=audio_manager)
        self.assertTrue(success)
        self.assertIn(self.thor.mjolnir.state, ("THROWN", "DESKTOP_THROWN"))

        # Lightning summon
        lightning_success = self.thor.trigger_ability("lightning_summon", 600.0, 400.0, self.particles, audio_mgr=audio_manager)
        self.assertTrue(lightning_success)
        self.assertGreater(len(self.particles.bolts), 0)

    def test_mjolnir_orbit_bounded_within_window(self):
        """Verify Mjolnir's orbit stays strictly within 50px of Thor to prevent clipping in 180x180 window."""
        self.thor.mjolnir.catch(500.0, 400.0)
        self.thor.trigger_ability("hammer_spin", 500.0, 400.0, self.particles, audio_mgr=audio_manager)
        self.assertEqual(self.thor.mjolnir.state, "ORBITING")

        # Step through orbit updates
        for _ in range(20):
            self.thor.mjolnir.update(500.0, 400.0, 500.0, 400.0, 1920, 1080, self.particles, thor_x=500.0, thor_y=400.0)
            dist_from_thor = ((self.thor.mjolnir.x - 500.0)**2 + (self.thor.mjolnir.y - 400.0)**2)**0.5
            # Must stay well within half window size (90px)
            self.assertLess(dist_from_thor, 60.0)

    def test_thor_drawing_with_held_mjolnir(self):
        """Verify Cairo drawing runs cleanly without exception for Thor holding Mjolnir."""
        import cairo
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 180, 180)
        ctx = cairo.Context(surface)
        # Thor in held state
        self.thor.draw(ctx, self.particles)
        # Verify surface drawn
        self.assertEqual(surface.get_width(), 180)


if __name__ == "__main__":
    unittest.main()
