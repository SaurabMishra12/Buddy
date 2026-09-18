import unittest
from skins.manager import skin_manager
import skins  # Trigger registrations
from core.particles import ParticleManager
from core.audio import audio_manager
from core.config import DEFAULT_CONFIG


class TestSkins(unittest.TestCase):
    EXPECTED_SKINS = [
        "thor", "dragon", "cat", "dog", "hulk",
        "ironman", "harry_potter", "captain_america",
        "thanos", "batman", "superman"
    ]

    def setUp(self):
        self.particles = ParticleManager()
        self.bounds = (0, 0, 1920, 1080)

    def test_all_11_skins_registered(self):
        available = [s["id"] for s in skin_manager.get_available_skins()]
        for expected in self.EXPECTED_SKINS:
            self.assertIn(expected, available, f"Skin '{expected}' missing from manager registry.")

    def test_character_instantiation_and_update(self):
        for skin_id in self.EXPECTED_SKINS:
            char = skin_manager.create_character(skin_id, x=500.0, y=400.0)
            self.assertIsNotNone(char, f"Failed to instantiate character '{skin_id}'")
            self.assertEqual(char.skin_id, skin_id)

            # Step 10 simulation frames
            for _ in range(10):
                char.update(
                    dt=1.0 / 60.0,
                    cursor_x=600.0,
                    cursor_y=500.0,
                    screen_bounds=self.bounds,
                    particle_mgr=self.particles,
                    audio_mgr=audio_manager,
                    config_data=DEFAULT_CONFIG
                )
            self.assertGreater(char.x, 0)
            self.assertGreater(char.y, 0)


if __name__ == "__main__":
    unittest.main()
