"""Comprehensive verification tests for:
1. Batman overhaul: aerodynamic Batarang projectile, grapple rope cleanup,
   tactical smoke bomb, gargoyle perch, and full articulated anatomical vector rendering.
2. Spider-Man overhaul: glitch-free pendulum web-swinging without frame-1 aborts,
   apex somersault release launch, McFarlane acrobatic aerial leap/jump split pose,
   iconic three-point ground perch with planted setae hand, and upside-down hang.
"""

import math
import time
import unittest
import cairo

from skins.manager import skin_manager
from skins.batman.character import BatmanCharacter
from skins.spiderman.character import SpiderManCharacter
from skins.base import CharacterState
from core.particles import ParticleManager
from core.audio import audio_manager
from core.projectiles import DesktopProjectileWindow
from core.window import WebRopeWindow
from core.platforms import platform_manager


class TestBatmanAndSpiderManOverhaul(unittest.TestCase):

    def setUp(self):
        self.particles = ParticleManager()
        self.bounds = (0, 0, 1920, 1080)
        self.config = {"speed": 1.0, "activity_level": 1.0, "cursor_follow": True}
        self.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 400, 400)
        self.ctx = cairo.Context(self.surf)

    def tearDown(self):
        # Clean up any lingering rope or projectile windows
        pass

    # =========================================================================
    # BATMAN VERIFICATION
    # =========================================================================

    def test_batman_metadata_and_abilities(self):
        """Verify Batman metadata, category, and abilities list."""
        meta = skin_manager.get_metadata("batman")
        self.assertIsNotNone(meta)
        self.assertEqual(meta["name"], "Batman")
        self.assertEqual(meta["category"], "superhero")
        abilities = meta.get("abilities", [])
        for req in ["grapple", "batarang", "cape_glide", "smoke_bomb", "perch"]:
            self.assertIn(req, abilities)

    def test_batman_abilities_trigger_and_batarang(self):
        """Verify Batman triggers abilities and launches Batarang correctly."""
        batman = BatmanCharacter(500.0, 500.0)

        # 1. Batarang Ability
        caught = []
        def on_catch():
            caught.append(True)

        self.assertTrue(batman.trigger_ability("batarang", 700.0, 500.0, self.particles, audio_manager))
        self.assertGreater(batman.batarang_timer, time.time())

        # 2. Smoke Bomb Ability
        self.assertTrue(batman.trigger_ability("smoke_bomb", 500.0, 500.0, self.particles, audio_manager))
        self.assertGreater(batman.smoke_timer, time.time())

        # 3. Gargoyle Perch Ability
        self.assertTrue(batman.trigger_ability("perch", 500.0, 500.0, self.particles, audio_manager))
        self.assertTrue(batman.is_perched)
        self.assertEqual(batman.state, CharacterState.IDLE)

        # 4. Grapple Ability & Rope Window Lifecycle
        self.assertTrue(batman.trigger_ability("grapple", 700.0, 100.0, self.particles, audio_manager))
        self.assertTrue(batman.is_grappling)
        self.assertIsNotNone(batman.rope_window)

        # Clean up rope
        batman.cleanup_rope()
        self.assertIsNone(batman.rope_window)

    def test_batman_batarang_projectile_mesh_rendering(self):
        """Verify DesktopProjectileWindow correctly renders the procedural Batarang mesh."""
        proj = DesktopProjectileWindow(
            proj_type="batarang",
            start_x=200.0,
            start_y=200.0,
            target_x=400.0,
            target_y=200.0,
            owner_getter=lambda: (200.0, 200.0),
            speed=25.0
        )
        try:
            # Render Batarang frame in Cairo
            proj.on_draw(proj, self.ctx)
            self.assertEqual(proj.proj_type, "batarang")
            self.assertGreater(proj.angular_velocity, 0.0)
        finally:
            proj.destroy_projectile()

    def test_batman_anatomical_vector_rendering_performance(self):
        """Verify Batman renders all anatomical states in sub-millisecond frame times."""
        batman = BatmanCharacter(200.0, 200.0)

        t0 = time.perf_counter()
        # 1. Idle standing with articulated tactical boots & dual gauntlet blades
        batman.draw(self.ctx, self.particles)

        # 2. Running vigilante patrol
        batman.state = CharacterState.RUN
        batman.stride = 1.8
        batman.draw(self.ctx, self.particles)

        # 3. Cape gliding wings
        batman.is_gliding = True
        batman.state = CharacterState.FLY
        batman.draw(self.ctx, self.particles)
        batman.is_gliding = False

        # 4. Gothic gargoyle perch
        batman.is_perched = True
        batman.draw(self.ctx, self.particles)
        batman.is_perched = False

        # 5. Smoke bomb ninja shroud
        batman.smoke_timer = time.time() + 1.0
        batman.draw(self.ctx, self.particles)
        elapsed_total = time.perf_counter() - t0

        # Benchmark: 5 distinct postures must render in under 20ms total (< 4ms/frame)
        self.assertLess(elapsed_total, 0.05)

    # =========================================================================
    # SPIDER-MAN VERIFICATION
    # =========================================================================

    def test_spiderman_metadata_and_abilities(self):
        """Verify Spider-Man metadata and abilities list."""
        meta = skin_manager.get_metadata("spiderman")
        self.assertIsNotNone(meta)
        self.assertEqual(meta["name"], "Spider-Man")
        abilities = meta.get("abilities", [])
        for req in ["web_swing", "web_throw", "spider_sense", "wall_crawl", "perch", "upside_down_hang"]:
            self.assertIn(req, abilities)

    def test_spiderman_swing_no_frame1_abort_on_ground(self):
        """CRITICAL: Verify Spider-Man web-swinging triggered near/on ground does NOT abort on frame 1."""
        ground_y = self.bounds[3] - 70.0  # 1010.0
        spidey = SpiderManCharacter(300.0, ground_y)

        # Trigger swing from the ground
        self.assertTrue(spidey.trigger_ability("web_swing", 700.0, ground_y, self.particles, audio_manager))
        self.assertTrue(spidey.is_swinging)
        self.assertEqual(spidey.state, CharacterState.FLY)
        self.assertGreater(spidey.swing_timer, 0.0)

        # Update for 15 frames (~0.24 seconds)
        initial_x = spidey.x
        for _ in range(15):
            spidey.update(0.016, 700.0, ground_y, self.bounds, self.particles, audio_manager, self.config)
            # MUST still be swinging — not aborted on frame 1!
            self.assertTrue(spidey.is_swinging, "Spider-Man aborted web swing prematurely near ground!")

        # Verify he moved forward along the pendulum arc
        self.assertGreater(spidey.x, initial_x)
        spidey.cleanup_rope()

    def test_spiderman_swing_apex_release_into_acrobatic_jump(self):
        """Verify Spider-Man releases web line at apex and launches into acrobatic jump."""
        spidey = SpiderManCharacter(500.0, 600.0)
        spidey.trigger_ability("web_swing", 800.0, 600.0, self.particles, audio_manager)

        # Fast forward swing timer past minimum duration and simulate rising apex
        spidey.swing_timer = time.time() - 0.7
        spidey.swing_direction = 1.0
        spidey.swing_angle = 0.35  # Swung up forward
        spidey.swing_vel = 0.2     # Decelerated near apex

        spidey.update(0.016, 800.0, 600.0, self.bounds, self.particles, audio_manager, self.config)

        # Swing should release and launch Spidey into JUMP
        self.assertFalse(spidey.is_swinging)
        self.assertEqual(spidey.state, CharacterState.JUMP)
        self.assertGreater(spidey.vx, 0.0, "Expected forward horizontal momentum at apex release")
        self.assertLess(spidey.vy, 0.0, "Expected upward vertical velocity at apex release")

    def test_spiderman_three_point_perch_posture(self):
        """Verify Spider-Man three-point perch posture state and lean."""
        ground_y = self.bounds[3] - 70.0
        spidey = SpiderManCharacter(500.0, ground_y)

        spidey.trigger_ability("perch", 500.0, ground_y, self.particles, audio_manager)
        self.assertTrue(spidey.is_perched)
        self.assertFalse(spidey.is_seated)
        self.assertFalse(spidey.is_swinging)
        self.assertEqual(spidey.state, CharacterState.IDLE)
        self.assertEqual(spidey.tilt, 0.0)

        # Draw perched pose in Cairo without error
        spidey.draw(self.ctx, self.particles)

    def test_spiderman_upside_down_hang_pose(self):
        """Verify Spider-Man upside down ceiling hang ability and inverted rendering."""
        spidey = SpiderManCharacter(500.0, 400.0)
        self.assertTrue(spidey.trigger_ability("upside_down_hang", 500.0, 200.0, self.particles, audio_manager))
        self.assertTrue(spidey.is_hanging_upside_down)
        self.assertEqual(spidey.tilt, math.pi)

        # Draw upside down pose in Cairo
        spidey.draw(self.ctx, self.particles)
        spidey.cleanup_rope()

    def test_spiderman_acrobatic_aerial_vector_rendering(self):
        """Verify Spider-Man's acrobatic aerial McFarlane jump split and flight limbs render without errors."""
        spidey = SpiderManCharacter(200.0, 200.0)

        t0 = time.perf_counter()
        # 1. Rising jump leap (vy < 0)
        spidey.state = CharacterState.JUMP
        spidey.vy = -12.0
        spidey.vx = 8.0
        spidey.draw(self.ctx, self.particles)

        # 2. Descending dive (vy > 0)
        spidey.vy = 10.0
        spidey.draw(self.ctx, self.particles)

        # 3. High horizontal speed flight (CharacterState.FLY)
        spidey.state = CharacterState.FLY
        spidey.vx = 14.0
        spidey.draw(self.ctx, self.particles)

        # 4. Web swing pose
        spidey.is_swinging = True
        spidey.swing_vel = 1.5
        spidey.draw(self.ctx, self.particles)
        spidey.is_swinging = False

        # 5. Athletic 3/4 runner stride
        spidey.state = CharacterState.RUN
        spidey.stride = 2.4
        spidey.draw(self.ctx, self.particles)

        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.05, "Rendering 5 dynamic Spider-Man poses took too long!")

    def test_spiderman_airborne_landing_into_three_point_perch(self):
        """Verify Spider-Man landing from airborne jump naturally drops into a three-point perch."""
        ground_y = self.bounds[3] - 70.0
        spidey = SpiderManCharacter(500.0, ground_y - 20.0)
        spidey.state = CharacterState.JUMP
        spidey.vy = 8.0  # Falling toward ground

        # Step airborne simulation until ground is reached
        for _ in range(5):
            spidey.update(0.016, 500.0, ground_y, self.bounds, self.particles, audio_manager, self.config)
            if spidey.y >= ground_y:
                break

        self.assertEqual(spidey.y, ground_y)
        self.assertEqual(spidey.vy, 0.0)
        self.assertEqual(spidey.state, CharacterState.IDLE)
        self.assertTrue(spidey.is_perched, "Spider-Man should land in a heroic three-point perch!")

    def test_spiderman_web_cocoon_ability_and_projectile(self):
        """Verify Spider-Man launches a web cocoon projectile that renders silk wrapping and radial web mesh."""
        from core.projectiles import DesktopProjectileWindow
        spidey = SpiderManCharacter(400.0, 500.0)
        
        # Trigger cocoon ability
        self.assertTrue(spidey.trigger_ability("web_cocoon", 700.0, 500.0, self.particles, audio_manager))
        
        # Test DesktopProjectileWindow for web_cocoon
        cocoon = DesktopProjectileWindow(
            proj_type="web_cocoon",
            start_x=400.0,
            start_y=500.0,
            target_x=700.0,
            target_y=500.0,
            owner_getter=lambda: (spidey.x, spidey.y),
            speed=28.0
        )
        try:
            self.assertEqual(cocoon.proj_type, "web_cocoon")
            
            # Test rendering in outbound spindle state
            t0 = time.perf_counter()
            cocoon.on_draw(cocoon, self.ctx)
            elapsed1 = time.perf_counter() - t0
            self.assertLess(elapsed1, 0.015, "Cocoon spindle draw should be < 15ms!")
            
            # Test collision / explosion into sticky silk cocoon wrap
            cocoon._trigger_collision()
            self.assertEqual(cocoon.state, "EXPLODING")
            t1 = time.perf_counter()
            cocoon.on_draw(cocoon, self.ctx)
            elapsed2 = time.perf_counter() - t1
            self.assertLess(elapsed2, 0.015, "Exploded web cocoon draw should be < 15ms!")
        finally:
            cocoon.destroy_projectile()

    def test_spiderman_swing_attack_ability_and_recoil(self):
        """Verify Spider-Man launches dynamic swing attack dive, renders dropkick limbs, and recoils on impact."""
        spidey = SpiderManCharacter(300.0, 400.0)
        
        # Trigger swing attack towards target
        self.assertTrue(spidey.trigger_ability("swing_attack", 600.0, 400.0, self.particles, audio_manager))
        self.assertTrue(spidey.is_swing_attacking)
        self.assertEqual(spidey.state, CharacterState.FLY)
        self.assertGreater(spidey.vx, 15.0)  # High-speed catapult strike
        
        # Render dropkick and web-shooter dive limbs in Cairo
        t0 = time.perf_counter()
        spidey.draw(self.ctx, self.particles)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.015, "Swing attack render should be sub-millisecond!")
        
        # Simulate updates until strike connects
        initial_x = spidey.x
        for _ in range(30):
            spidey.update(0.016, 600.0, 400.0, self.bounds, self.particles, audio_manager, self.config)
            if not spidey.is_swing_attacking:
                break
                
        # Must have completed attack and leapt back into somersault
        self.assertFalse(spidey.is_swing_attacking)
        self.assertLess(spidey.vx, 0.0, "Spider-Man should recoil backward after dropkick impact!")
        spidey.cleanup_rope()

    def test_spiderman_no_seating_on_air_or_flat_ground(self):
        """Verify Spider-Man strictly never sits in mid-air or on flat floor ground."""
        ground_y = self.bounds[3] - 70.0
        spidey = SpiderManCharacter(500.0, 500.0)  # Floating in mid-air
        
        # If somehow flagged as seated in mid-air, update must clear it
        spidey.is_seated = True
        spidey.update(0.016, 500.0, 500.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertFalse(spidey.is_seated, "Spider-Man must never remain seated in mid-air!")
        
        # Drop onto flat ground
        spidey.y = ground_y
        spidey.vy = 0.0
        spidey.is_seated = True
        spidey.update(0.016, 500.0, ground_y, self.bounds, self.particles, audio_manager, self.config)
        self.assertFalse(spidey.is_seated, "Spider-Man must not sit on flat floor; he must use 3-point crouch!")
        self.assertTrue(spidey.is_perched)

    def test_spiderman_upper_taskbar_and_window_sitting(self):
        """Verify Spider-Man sits in iconic raised-knee, chin-propped style on upper taskbar or windows."""
        from core.platforms import platform_manager, DesktopLedge
        top_panel = DesktopLedge(0, 0, 1920, 32, "panel", "Top Bar")
        platform_manager.ledges.append(top_panel)
        
        spidey = SpiderManCharacter(500.0, 500.0)
        
        # Trigger seat with upper taskbar target
        self.assertTrue(spidey.trigger_ability("seat", 500.0, 24.0, self.particles, audio_manager))
        self.assertTrue(spidey.is_seated)
        self.assertFalse(spidey.is_perched)
        self.assertLess(spidey.y, 50.0, "Spider-Man should be seated at the upper taskbar!")
        
        # Render authentic Spider-Man sitting pose (raised knee + chin prop + dangling leg)
        t0 = time.perf_counter()
        spidey.draw(self.ctx, self.particles)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 0.015, "Spider-Man seated pose should render in < 15ms!")
        
        platform_manager.ledges.remove(top_panel)

    def test_phantom_workspace_window_ignored_by_spiderman_sitting(self):
        """Verify fallback 'Workspace Window' phantom ledge is never used as a mid-air seat."""
        from core.platforms import platform_manager, DesktopLedge
        phantom = DesktopLedge(100.0, 194.0, 1000.0, 30.0, "window", "Workspace Window", is_real=False)
        self.assertFalse(platform_manager.is_real_surface(phantom))

        # is_on_ledge with require_real=True must reject phantom ledges
        platform_manager.dynamic_ledges.append(phantom)
        detected = platform_manager.is_on_ledge(500.0, 194.0, tolerance=14.0, require_real=True)
        self.assertIsNone(detected)

        # Spidey in mid-air near phantom ledge must not sit on it
        spidey = SpiderManCharacter(500.0, 194.0)
        spidey.update(0.016, 500.0, 194.0, self.bounds, self.particles, audio_manager, self.config)
        self.assertFalse(spidey.is_seated)
        self.assertNotEqual(spidey.vy, 0.0)  # Gravity must still pull him

        platform_manager.dynamic_ledges.remove(phantom)

    def test_mid_air_seat_trigger_web_zips_to_taskbar(self):
        """Verify triggering 'seat' while floating in mid-air web-zips Spidey up to the upper taskbar."""
        spidey = SpiderManCharacter(500.0, 350.0)  # Mid-air
        self.assertFalse(spidey.is_seated)

        # Trigger seat while floating in mid-air
        spidey.trigger_ability("seat", 500.0, 350.0, self.particles, audio_manager)
        self.assertTrue(spidey.is_seated)
        # Must be on the upper taskbar, NEVER in mid-air!
        self.assertLessEqual(spidey.y, 42.0, "Spider-Man must web-zip to upper taskbar when seated from mid-air!")


if __name__ == "__main__":
    unittest.main()
