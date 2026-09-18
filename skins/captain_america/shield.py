"""Vibranium Shield entity with ricochet physics, rotation, and return mechanics."""

import math
import random
import cairo
from typing import Tuple, Optional
from skins.base import BaseProjectile
from core.particles import ParticleManager


class VibraniumShield(BaseProjectile):
    """Captain America's iconic circular shield that ricochets and returns."""

    def __init__(self, x: float = 0.0, y: float = 0.0):
        super().__init__(x, y)
        self.state = "HELD"  # "HELD", "THROWN", "RETURNING"
        self.radius = 16.0
        self.spin = 0.0
        self.bounces = 0
        self.max_bounces = 3

    def throw(self, start_x: float, start_y: float, target_x: float, target_y: float) -> None:
        self.x = start_x
        self.y = start_y
        self.state = "THROWN"
        self.bounces = 0
        dx = target_x - start_x
        dy = target_y - start_y
        dist = math.hypot(dx, dy) + 1e-4
        speed = 22.0
        self.vx = (dx / dist) * speed
        self.vy = (dy / dist) * speed

    def recall(self) -> None:
        self.state = "RETURNING"

    def catch(self, hand_x: float, hand_y: float) -> None:
        self.state = "HELD"
        self.x = hand_x
        self.y = hand_y
        self.vx = 0.0
        self.vy = 0.0

    def update(
        self,
        hand_x: float,
        hand_y: float,
        screen_bounds: Tuple[int, int, int, int],
        particle_mgr: ParticleManager
    ) -> Optional[str]:
        if self.state == "HELD":
            self.x = hand_x
            self.y = hand_y
            return None

        self.spin += 0.40
        self.x += self.vx
        self.y += self.vy

        min_x, min_y, screen_w, screen_h = screen_bounds
        pad = 35.0

        if self.state == "THROWN":
            collided = False
            if self.x < min_x + pad or self.x > min_x + screen_w - pad:
                self.vx = -self.vx
                collided = True
            if self.y < min_y + pad or self.y > min_y + screen_h - pad:
                self.vy = -self.vy
                collided = True

            if collided:
                self.bounces += 1
                particle_mgr.burst_sparks(self.x, self.y, count=8, color=(0.9, 0.9, 1.0))
                if self.bounces >= self.max_bounces:
                    self.state = "RETURNING"

        elif self.state == "RETURNING":
            dx = hand_x - self.x
            dy = hand_y - self.y
            dist = math.hypot(dx, dy) + 1e-4
            pull = 24.0
            self.vx = (dx / dist) * pull
            self.vy = (dy / dist) * pull

            if dist < 28.0:
                self.catch(hand_x, hand_y)
                particle_mgr.burst_sparks(hand_x, hand_y, count=10, color=(0.9, 0.9, 1.0))
                return "CAUGHT"

        return None

    def draw(self, ctx: cairo.Context) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.rotate(self.spin)

        # Concentric Red and Silver Vibranium Rings
        # 1. Outer Red Ring
        ctx.set_source_rgb(0.85, 0.12, 0.15)
        ctx.arc(0, 0, self.radius, 0, 2 * math.pi)
        ctx.fill()

        # 2. Silver Ring
        ctx.set_source_rgb(0.92, 0.94, 0.96)
        ctx.arc(0, 0, self.radius * 0.78, 0, 2 * math.pi)
        ctx.fill()

        # 3. Inner Red Ring
        ctx.set_source_rgb(0.85, 0.12, 0.15)
        ctx.arc(0, 0, self.radius * 0.58, 0, 2 * math.pi)
        ctx.fill()

        # 4. Center Blue Circle
        ctx.set_source_rgb(0.08, 0.32, 0.78)
        ctx.arc(0, 0, self.radius * 0.38, 0, 2 * math.pi)
        ctx.fill()

        # 5. Silver Star in Center
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.new_path()
        r_out = self.radius * 0.34
        r_in = r_out * 0.42
        for i in range(5):
            ang = -math.pi / 2 + i * (2 * math.pi / 5)
            x1 = math.cos(ang) * r_out
            y1 = math.sin(ang) * r_out
            if i == 0:
                ctx.move_to(x1, y1)
            else:
                ctx.line_to(x1, y1)
            ang_in = ang + (math.pi / 5)
            x2 = math.cos(ang_in) * r_in
            y2 = math.sin(ang_in) * r_in
            ctx.line_to(x2, y2)
        ctx.close_path()
        ctx.fill()

        ctx.restore()
