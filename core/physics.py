"""Lightweight 2D physics engine for Buddy desktop characters and projectiles."""

import math
import random
from typing import Tuple, Optional


class PhysicsBody:
    """Represents a 2D physics body with velocity, acceleration, friction, and gravity."""

    def __init__(
        self,
        x: float = 0.0,
        y: float = 0.0,
        mass: float = 1.0,
        gravity: float = 0.0,
        friction: float = 0.90,
        max_speed: float = 15.0,
        bounciness: float = 0.5,
        is_flying: bool = False
    ):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.ax = 0.0
        self.ay = 0.0
        self.mass = max(0.1, mass)
        self.gravity = gravity
        self.friction = friction
        self.max_speed = max_speed
        self.bounciness = bounciness
        self.is_flying = is_flying
        self.is_grounded = False

    def apply_force(self, fx: float, fy: float) -> None:
        """Apply an instantaneous force vector."""
        self.ax += fx / self.mass
        self.ay += fy / self.mass

    def impulse(self, ivx: float, ivy: float) -> None:
        """Directly add to velocity."""
        self.vx += ivx
        self.vy += ivy

    def accelerate_toward(self, target_x: float, target_y: float, accel: float, max_spd: Optional[float] = None) -> float:
        """Smoothly accelerate towards a target point with spring-like response."""
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)
        if dist > 1e-3:
            effective_accel = min(dist * 0.1, accel)
            self.vx += (dx / dist) * effective_accel
            self.vy += (dy / dist) * effective_accel
        
        limit = max_spd or self.max_speed
        speed = math.hypot(self.vx, self.vy)
        if speed > limit:
            self.vx = (self.vx / speed) * limit
            self.vy = (self.vy / speed) * limit
        return dist

    def update(self, dt: float = 1.0 / 60.0) -> None:
        """Step physics simulation forward."""
        # Apply accumulated acceleration
        self.vx += self.ax
        self.vy += self.ay
        self.ax = 0.0
        self.ay = 0.0

        # Apply gravity if not flying and not on ground
        if not self.is_flying and not self.is_grounded:
            self.vy += self.gravity

        # Apply friction
        self.vx *= self.friction
        self.vy *= self.friction if self.is_flying else (self.friction if not self.is_grounded else self.friction * 0.8)

        # Speed clamp
        spd = math.hypot(self.vx, self.vy)
        if spd > self.max_speed:
            self.vx = (self.vx / spd) * self.max_speed
            self.vy = (self.vy / spd) * self.max_speed

        # Position integration
        self.x += self.vx
        self.y += self.vy

    def clamp_bounds(
        self,
        min_x: float,
        min_y: float,
        max_x: float,
        max_y: float,
        padding: float = 30.0,
        bounce: bool = False
    ) -> bool:
        """Constrain entity within screen boundaries."""
        collided = False
        left = min_x + padding
        right = max_x - padding
        top = min_y + padding
        bottom = max_y - padding

        if self.x < left:
            self.x = left
            if bounce:
                self.vx = -self.vx * self.bounciness
            else:
                self.vx = 0.0
            collided = True
        elif self.x > right:
            self.x = right
            if bounce:
                self.vx = -self.vx * self.bounciness
            else:
                self.vx = 0.0
            collided = True

        if self.y < top:
            self.y = top
            if bounce:
                self.vy = -self.vy * self.bounciness
            else:
                self.vy = 0.0
            collided = True
        elif self.y > bottom:
            self.y = bottom
            if bounce:
                self.vy = -self.vy * self.bounciness
            else:
                self.vy = 0.0
            self.is_grounded = True
            collided = True
        else:
            self.is_grounded = False

        return collided


class ScreenShake:
    """Manages brief procedural camera/screen shake offsets for impacts and smashes."""

    def __init__(self):
        self.intensity = 0.0
        self.decay = 0.90
        self.offset_x = 0.0
        self.offset_y = 0.0

    def trigger(self, intensity: float = 12.0) -> None:
        """Trigger an impact screen shake."""
        self.intensity = max(self.intensity, intensity)

    def update(self) -> Tuple[float, float]:
        """Update shake decay and return current (offset_x, offset_y)."""
        if self.intensity > 0.5:
            angle = random.uniform(0, 2 * math.pi)
            self.offset_x = math.cos(angle) * self.intensity
            self.offset_y = math.sin(angle) * self.intensity
            self.intensity *= self.decay
        else:
            self.intensity = 0.0
            self.offset_x = 0.0
            self.offset_y = 0.0
        return self.offset_x, self.offset_y
