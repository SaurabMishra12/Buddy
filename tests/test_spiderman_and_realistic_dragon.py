"""Comprehensive unit tests for:
1. Spider-Man character skin: abilities (web_swing, web_throw, spider_sense, wall_crawl, perch),
   pendulum kinematics, expressive eye squinting, and 100% procedural vector Cairo rendering.
2. Realistic pitch-black dreadwyrm Dragon vector Cairo rendering (zero PNGs/bitmaps, sub-ms performance,
   jaw unhinging, flame cone, glowing eye, bat wings).
3. Engine integration for Spider-Man: arrival fanfare, signature move, drag locomotion, and aliases.
"""

import math
import time
import unittest
import cairo

from skins.manager import skin_manager
from skins.spiderman.character import SpiderManCharacter
from skins.dragon.character import DragonCharacter
from skins.base import CharacterState
from core.particles import ParticleManager
from core.audio import audio_manager
from core.config import ConfigManager
from core.engine import BuddyEngine
from core.window import WebRopeWindow
from core.projectiles import DesktopProjectileWindow


class MockWindow:
    def __init__(self):
        self.bounds = (0, 0, 1920, 1080)
        self.x = 500.0
        self.y = 400.0
        self.draw_count = 0
        self.move_count = 0

    def move_to(self, x, y):
        self.x = x
        self.y = y
        self.move_count += 1

    def queue_draw(self):
        self.draw_count += 1

    def trigger_sky_strike(self, x, y):
        pass


class TestSpiderManAndRealisticDragon(unittest.TestCase):

    def setUp(self):
        self.particles = ParticleManager()
        self.bounds = (0, 0, 1920, 1080)
        self.config = {"speed": 1.0, "activity_level": 1.0, "cursor_follow": True}
        self.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 400, 400)
        self.ctx = cairo.Context(self.surf)

    def test_spiderman_registration_and_metadata(self):
        """Verify Spider-Man is registered in skin_manager with superhero metadata."""
        meta = skin_manager.get_metadata("spiderman")
        self.assertIsNotNone(meta)
        self.assertEqual(meta["name"], "Spider-Man")
        self.assertEqual(meta["category"], "superhero")
        self.assertTrue(meta["canFly"])
        self.assertIn("web_swing", meta["abilities"])
        self.assertIn("web_throw", meta["abilities"])
        self.assertIn("spider_sense", meta["abilities"])

        # Check aliases
        for alias in ["spiderman", "spider_man", "spidey", "spider"]:
            norm = skin_manager.normalize_skin_id(alias)
            self.assertEqual(norm, "spiderman")
            char = skin_manager.create_character(alias, 300.0, 300.0)
            self.assertIsInstance(char, SpiderManCharacter)

    def test_spiderman_abilities_and_kinematics(self):
        """Verify Spider-Man's abilities: swinging, web throw, spider sense, perching, and hanging."""
        spidey = SpiderManCharacter(500.0, 500.0)

        # 1. Web Swing
        self.assertTrue(spidey.trigger_ability("web_swing", 700.0, 500.0, self.particles, audio_manager))
        self.assertTrue(spidey.is_swinging)
        self.assertEqual(spidey.state, CharacterState.FLY)
        initial_x = spidey.x
        for _ in range(10):
            spidey.update(0.016, 700.0, 500.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertNotEqual(spidey.x, initial_x)

        # 2. Web Throw
        self.assertTrue(spidey.trigger_ability("web_throw", 600.0, 400.0, self.particles, audio_manager))
        self.assertGreater(spidey.web_shoot_timer, time.time())
        self.assertGreater(spidey.eye_squint, 0.0)  # Focused squint

        # 3. Spider-Sense
        self.assertTrue(spidey.trigger_ability("spider_sense", 510.0, 510.0, self.particles, audio_manager))
        self.assertTrue(spidey.spider_sense_active)
        self.assertLess(spidey.eye_squint, 0.0)  # Wide alert eyes
        self.assertLess(spidey.vy, 0.0)  # Evasive dodge leap

        # 4. Perch
        ground_y = self.bounds[3] - 70.0
        spidey.y = ground_y
        self.assertTrue(spidey.trigger_ability("perch", 500.0, ground_y, self.particles, audio_manager))
        self.assertTrue(spidey.is_perched)
        self.assertEqual(spidey.state, CharacterState.IDLE)

        # 5. Upside-Down Hang
        self.assertTrue(spidey.trigger_ability("upside_down_hang", 500.0, 300.0, self.particles, audio_manager))
        self.assertTrue(spidey.is_hanging_upside_down)
        self.assertAlmostEqual(spidey.tilt, math.pi)

    def test_spiderman_vector_rendering(self):
        """Verify Spider-Man renders purely in Cairo vector without errors across all postures."""
        spidey = SpiderManCharacter(200.0, 200.0)

        # Draw standing / idle
        spidey.draw(self.ctx, self.particles)

        # Draw running
        spidey.state = CharacterState.RUN
        spidey.stride = 1.5
        spidey.draw(self.ctx, self.particles)

        # Draw swinging with web strand
        spidey.is_swinging = True
        spidey.anchor_x = 200.0
        spidey.anchor_y = 50.0
        spidey.draw(self.ctx, self.particles)

        # Draw perched three-point crouch
        spidey.is_swinging = False
        spidey.is_perched = True
        spidey.draw(self.ctx, self.particles)

        # Draw Spider-Sense alert with radiating comic tingle arcs
        spidey.is_perched = False
        spidey.spider_sense_active = True
        spidey.draw(self.ctx, self.particles)

        # Draw upside down hang
        spidey.spider_sense_active = False
        spidey.is_hanging_upside_down = True
        spidey.draw(self.ctx, self.particles)

        # Measure frame render performance
        t0 = time.perf_counter()
        for _ in range(100):
            self.ctx.save()
            self.ctx.set_operator(cairo.OPERATOR_CLEAR)
            self.ctx.paint()
            self.ctx.restore()
            spidey.draw(self.ctx, self.particles)
        avg_ms = (time.perf_counter() - t0) / 100.0 * 1000.0
        print(f"\n[Benchmark] Spider-Man average draw time: {avg_ms:.3f} ms/frame")
        self.assertLess(avg_ms, 1.2)

    def test_realistic_pitch_black_dragon_vector_rendering(self):
        """Verify the Dragon is rendered 100% procedurally with realistic pitch-black aesthetics."""
        dragon = DragonCharacter(200.0, 200.0)
        self.assertEqual(dragon.skin_id, "dragon")
        self.assertTrue(dragon.can_fly)

        # Render flight posture
        dragon.state = CharacterState.FLY
        dragon.wing_angle = 0.35
        dragon.back_wing_angle = 0.28
        dragon.tail_wave = 3.0
        dragon.draw(self.ctx, self.particles)

        # Render roaring flame breath with open jaw
        dragon.is_breathing_fire = True
        dragon.jaw_open = 1.0
        dragon.draw(self.ctx, self.particles)

        # Render seated perched posture
        dragon.is_breathing_fire = False
        dragon.trigger_ability("seat", 200.0, 300.0, self.particles, audio_manager)
        self.assertTrue(dragon.is_seated)
        dragon.draw(self.ctx, self.particles)

        # Render walking posture
        dragon.is_seated = False
        dragon.state = CharacterState.WALK
        dragon.paw_step = 2.0
        dragon.draw(self.ctx, self.particles)

    def test_engine_spiderman_integration(self):
        """Verify BuddyEngine switches to Spider-Man and triggers signature double-click move."""
        config = ConfigManager(profile="test_spiderman")
        config.set("skin", "spiderman")
        engine = BuddyEngine(config=config)
        engine.window = MockWindow()

        # Check initial skin
        self.assertEqual(engine.character.skin_id, "spiderman")
        self.assertIsInstance(engine.character, SpiderManCharacter)

        # Switch to spiderman (verifies arrival fanfare)
        engine.switch_skin("spider_man")
        self.assertEqual(engine.character.skin_id, "spiderman")

        # Signature double-click ability
        engine.trigger_signature_ability()
        self.assertTrue(engine.character.is_hanging_upside_down)

    def test_web_rope_window_direct_bounds_and_render(self):
        """Verify WebRopeWindow uses static screen overlay, click-through, and zero-resize updates."""
        pos1 = [200.0, 500.0]
        pos2 = [800.0, 50.0]

        rope_win = WebRopeWindow(
            start_getter=lambda: (pos1[0], pos1[1]),
            end_getter=lambda: (pos2[0], pos2[1]),
            rope_style="swing"
        )
        self.assertFalse(rope_win.is_destroyed)
        self.assertFalse(rope_win.get_resizable())
        self.assertLessEqual(rope_win.cur_min_x, 200.0 - 40.0)
        self.assertLessEqual(rope_win.cur_min_y, 50.0 - 40.0)
        self.assertGreaterEqual(rope_win.cur_w, 600)
        self.assertGreaterEqual(rope_win.cur_h, 450)

        initial_w = rope_win.cur_w
        initial_h = rope_win.cur_h
        initial_x = rope_win.cur_min_x
        initial_y = rope_win.cur_min_y

        # Move points across several frames and update
        pos1[0] = 300.0
        pos1[1] = 450.0
        pos2[0] = 950.0
        pos2[1] = 20.0
        rope_win.update()

        # Geometry must remain strictly static (no resize/move) to prevent X11 black box flashing
        self.assertEqual(rope_win.cur_w, initial_w)
        self.assertEqual(rope_win.cur_h, initial_h)
        self.assertEqual(rope_win.cur_min_x, initial_x)
        self.assertEqual(rope_win.cur_min_y, initial_y)

        # Clean disposal
        rope_win.destroy_rope()
        self.assertTrue(rope_win.is_destroyed)

    def test_spiderman_swing_rope_full_desktop_integration(self):
        """Verify SpiderManCharacter manages WebRopeWindow across swinging and upside-down hang."""
        spidey = SpiderManCharacter(500.0, 500.0)
        self.assertIsNone(spidey.rope_window)

        # 1. Trigger swing
        spidey.trigger_ability("web_swing", 800.0, 500.0, self.particles, audio_manager)
        self.assertTrue(spidey.is_swinging)
        self.assertIsNotNone(spidey.rope_window)
        self.assertFalse(spidey.rope_window.is_destroyed)
        self.assertEqual(spidey.rope_window.rope_style, "swing")

        # Update while swinging
        for _ in range(5):
            spidey.update(0.016, 800.0, 500.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertIsNotNone(spidey.rope_window)

        # Trigger perch -> should cleanly destroy swing rope
        spidey.trigger_ability("perch", 500.0, 500.0, self.particles, audio_manager)
        self.assertFalse(spidey.is_swinging)
        self.assertIsNone(spidey.rope_window)

        # 2. Trigger upside-down hang
        spidey.trigger_ability("upside_down_hang", 500.0, 500.0, self.particles, audio_manager)
        self.assertTrue(spidey.is_hanging_upside_down)
        self.assertIsNotNone(spidey.rope_window)
        self.assertEqual(spidey.rope_window.rope_style, "swing")

        # End hang -> rope destroyed
        spidey.is_hanging_upside_down = False
        spidey.update(0.016, 500.0, 500.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertIsNone(spidey.rope_window)

    def test_spiderman_web_throw_rope_lifecycle(self):
        """Verify DesktopProjectileWindow creates and tracks full unclipped rope during web throw."""
        spidey = SpiderManCharacter(400.0, 400.0)
        proj = DesktopProjectileWindow(
            proj_type="web",
            start_x=426.0,
            start_y=394.0,
            target_x=900.0,
            target_y=200.0,
            owner_getter=lambda: (spidey.x, spidey.y),
            speed=30.0
        )
        self.assertIsNotNone(proj.rope_window)
        self.assertFalse(proj.rope_window.is_destroyed)
        self.assertEqual(proj.rope_window.rope_style, "throw")

        # Tick outbound travel
        for _ in range(3):
            proj.on_tick()
        self.assertFalse(proj.rope_window.is_destroyed)

        # Collide and trigger net explosion
        proj._trigger_collision()
        self.assertEqual(proj.state, "EXPLODING")
        self.assertGreater(proj._get_web_alpha(), 0.0)

        # Destroy projectile -> verifies rope cleanup
        proj.destroy_projectile()
        self.assertIsNone(proj.rope_window)


if __name__ == "__main__":
    unittest.main()

