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
        self.assertEqual(self.thor.mjolnir.state, "THROWN")

        # Lightning summon
        lightning_success = self.thor.trigger_ability("lightning_summon", 600.0, 400.0, self.particles, audio_mgr=audio_manager)
        self.assertTrue(lightning_success)
        self.assertGreater(len(self.particles.bolts), 0)


if __name__ == "__main__":
    unittest.main()
