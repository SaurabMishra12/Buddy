"""Unit tests for Thanos abilities, cursor touch deadzone, and hero-specific drag locomotion."""

import unittest
import math
from skins.manager import skin_manager
from skins.base import CharacterState
from skins.thanos.character import ThanosCharacter
from skins.hulk.character import HulkCharacter
from skins.ironman.character import IronManCharacter
from skins.superman.character import SupermanCharacter
from skins.captain_america.character import CaptainAmericaCharacter
from skins.dragon.character import DragonCharacter
from core.particles import ParticleManager
from core.audio import SoundManager
from core.engine import BuddyEngine
from core.config import ConfigManager


class MockWindow:
    def __init__(self, w=1920, h=1080):
        self.screen_w = float(w)
        self.screen_h = float(h)
        self.bounds = (0, 0, int(w), int(h))
        self.half_size = 55.0
        self.x = 500.0
        self.y = 400.0

    def query_pointer(self):
        return (self.x, self.y)

    def move_to(self, x, y):
        self.x = x
        self.y = y

    def queue_draw(self):
        pass

    def show(self):
        pass

    def trigger_sky_strike(self, x, y):
        pass


class TestThanosAbilities(unittest.TestCase):
    def setUp(self):
        self.character = ThanosCharacter(x=500.0, y=400.0)
        self.particles = ParticleManager()
        self.audio = SoundManager(enabled=False)

    def test_snap_ability(self):
        success = self.character.trigger_ability("the_snap", 600.0, 400.0, self.particles, self.audio)
        self.assertTrue(success)
        self.assertTrue(self.character.is_snapping)
        self.assertGreater(len(self.particles.shockwaves), 0)
        self.assertGreater(len(self.particles.particles), 0)

    def test_time_stone_ability(self):
        success = self.character.trigger_ability("time_stone", 600.0, 400.0, self.particles, self.audio)
        self.assertTrue(success)
        self.assertEqual(self.character.active_stone, "time")
        self.assertGreater(len(self.particles.shockwaves), 0)

    def test_space_teleport_ability(self):
        old_x = self.character.x
        success = self.character.trigger_ability("space_teleport", 800.0, 300.0, self.particles, self.audio)
        self.assertTrue(success)
        self.assertEqual(self.character.active_stone, "space")
        self.assertAlmostEqual(self.character.y, 300.0, delta=20.0)
        self.assertNotEqual(self.character.x, old_x)


class TestCursorNoFleeing(unittest.TestCase):
    """Ensure characters do not run away when cursor is near them."""

    def test_all_characters_calm_when_cursor_near(self):
        particles = ParticleManager()
        audio = SoundManager(enabled=False)
        bounds = (0, 0, 1920, 1080)
        config = {"speed": 1.0, "activity_level": 0.0, "cursor_follow": True}

        all_skins = [s["id"] for s in skin_manager.get_available_skins()]
        self.assertGreaterEqual(len(all_skins), 11)

        for skin_id in all_skins:
            init_y = 500.0 if skin_id in ("thor", "dragon", "ironman", "harry_potter", "superman") else 1010.0
            char = skin_manager.create_character(skin_id, x=500.0, y=init_y)
            near_cursor_x = 510.0
            near_cursor_y = init_y + 5.0

            for _ in range(5):
                char.update(0.016, near_cursor_x, near_cursor_y, bounds, particles, audio, config)

            spd = math.hypot(char.vx, char.vy)
            self.assertLess(spd, 4.5, f"Character {skin_id} has high speed {spd} while cursor is near! Might be fleeing.")
            self.assertIn(char.state, (CharacterState.IDLE, CharacterState.HOVER, CharacterState.WALK),
                          f"Character {skin_id} state is {char.state} when cursor is near!")


class TestSkinSwitchingDragonToHulk(unittest.TestCase):
    """Verify switching between flying dragon and ground hulk does not get stuck."""

    def test_dragon_to_hulk_switch(self):
        dragon = skin_manager.create_character("dragon", x=400.0, y=150.0)
        self.assertIsInstance(dragon, DragonCharacter)
        self.assertTrue(dragon.can_fly)

        hulk = skin_manager.create_character("hulk", x=400.0, y=150.0)
        self.assertIsInstance(hulk, HulkCharacter)
        self.assertFalse(hulk.can_fly)

        config = ConfigManager(profile="test_drag")
        config.set("skin", "dragon")
        engine = BuddyEngine(config=config)
        engine.window = MockWindow()
        engine.character = dragon

        switched = engine.switch_skin("hulk")
        self.assertTrue(switched)
        self.assertIsInstance(engine.character, HulkCharacter)
        ground_y = 1080 - 70.0
        self.assertAlmostEqual(engine.character.y, ground_y, delta=5.0)
        self.assertFalse(engine.is_dragging)


class TestHeroDragLocomotion(unittest.TestCase):
    """Verify each character follows slightly slower in their unique way during dragging."""

    def test_ironman_drag_flies(self):
        config = ConfigManager(profile="test_drag_im")
        engine = BuddyEngine(config=config)
        engine.window = MockWindow()
        engine.switch_skin("ironman")

        engine.character.x = 500.0
        engine.character.y = 400.0
        engine.cursor_x = 800.0
        engine.cursor_y = 300.0
        engine.is_dragging = True

        engine.on_tick()

        self.assertEqual(engine.character.state, CharacterState.FLY)
        self.assertGreater(engine.character.x, 500.0)
        self.assertLess(engine.character.x, 800.0)

    def test_superman_drag_flies(self):
        config = ConfigManager(profile="test_drag_sm")
        engine = BuddyEngine(config=config)
        engine.window = MockWindow()
        engine.switch_skin("superman")

        engine.character.x = 400.0
        engine.character.y = 400.0
        engine.cursor_x = 800.0
        engine.cursor_y = 350.0
        engine.is_dragging = True

        engine.on_tick()

        self.assertEqual(engine.character.state, CharacterState.FLY)
        self.assertGreater(engine.character.x, 400.0)
        self.assertLess(engine.character.x, 800.0)

    def test_captain_america_drag_runs(self):
        config = ConfigManager(profile="test_drag_cap")
        engine = BuddyEngine(config=config)
        engine.window = MockWindow()
        engine.switch_skin("captain_america")

        ground_y = 1080 - 70.0
        engine.character.x = 300.0
        engine.character.y = ground_y
        engine.cursor_x = 700.0
        engine.cursor_y = ground_y
        engine.is_dragging = True

        engine.on_tick()

        self.assertEqual(engine.character.state, CharacterState.RUN)
        self.assertGreater(engine.character.x, 300.0)
        self.assertLess(engine.character.x, 700.0)
        self.assertAlmostEqual(engine.character.y, ground_y, delta=2.0)

    def test_hulk_drag_jumps(self):
        config = ConfigManager(profile="test_drag_hulk")
        engine = BuddyEngine(config=config)
        engine.window = MockWindow()
        engine.switch_skin("hulk")

        ground_y = 1080 - 70.0
        engine.character.x = 300.0
        engine.character.y = ground_y
        engine.cursor_x = 750.0
        engine.cursor_y = ground_y
        engine.is_dragging = True

        engine.on_tick()

        self.assertEqual(engine.character.state, CharacterState.JUMP)
        self.assertLess(engine.character.vy, -10.0)
        self.assertGreater(engine.character.vx, 5.0)


if __name__ == "__main__":
    unittest.main()
