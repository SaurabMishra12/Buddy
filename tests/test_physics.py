import unittest
import math
from core.physics import PhysicsBody, ScreenShake


class TestPhysics(unittest.TestCase):
    def test_physics_body_movement_and_friction(self):
        body = PhysicsBody(x=100.0, y=100.0, friction=0.9, is_flying=True)
        body.impulse(10.0, 0.0)
        body.update()
        self.assertAlmostEqual(body.x, 109.0, places=1)
        self.assertAlmostEqual(body.vx, 9.0, places=1)

    def test_accelerate_toward(self):
        body = PhysicsBody(x=0.0, y=0.0, max_speed=20.0, is_flying=True)
        dist = body.accelerate_toward(100.0, 0.0, accel=2.0)
        self.assertAlmostEqual(dist, 100.0, places=1)
        self.assertGreater(body.vx, 0.0)

    def test_boundary_clamp_and_bounce(self):
        body = PhysicsBody(x=10.0, y=10.0, bounciness=0.5, is_flying=True)
        body.vx = -10.0
        collided = body.clamp_bounds(min_x=0, min_y=0, max_x=800, max_y=600, padding=20.0, bounce=True)
        self.assertTrue(collided)
        self.assertEqual(body.x, 20.0)
        self.assertEqual(body.vx, 5.0)  # Rebounded with bounciness 0.5

    def test_screen_shake(self):
        shake = ScreenShake()
        shake.trigger(10.0)
        ox, oy = shake.update()
        self.assertNotEqual(ox, 0.0)
        self.assertLessEqual(math.hypot(ox, oy), 10.01)


if __name__ == "__main__":
    unittest.main()
