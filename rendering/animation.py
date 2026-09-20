"""Mathematical animation easing functions and spring dynamics for Buddy."""

import math
from typing import Tuple


def linear(t: float) -> float:
    return max(0.0, min(1.0, float(t)))


def ease_in_quad(t: float) -> float:
    t = linear(t)
    return t * t


def ease_out_quad(t: float) -> float:
    t = linear(t)
    return t * (2.0 - t)


def ease_in_out_quad(t: float) -> float:
    t = linear(t)
    return 2.0 * t * t if t < 0.5 else -1.0 + (4.0 - 2.0 * t) * t


def ease_in_cubic(t: float) -> float:
    t = linear(t)
    return t * t * t


def ease_out_cubic(t: float) -> float:
    t = linear(t) - 1.0
    return t * t * t + 1.0


def ease_in_out_cubic(t: float) -> float:
    t = linear(t)
    return 4.0 * t * t * t if t < 0.5 else (t - 1.0) * (2.0 * t - 2.0) * (2.0 * t - 2.0) + 1.0


def ease_out_bounce(t: float) -> float:
    t = linear(t)
    if t < (1.0 / 2.75):
        return 7.5625 * t * t
    elif t < (2.0 / 2.75):
        t -= (1.5 / 2.75)
        return 7.5625 * t * t + 0.75
    elif t < (2.5 / 2.75):
        t -= (2.25 / 2.75)
        return 7.5625 * t * t + 0.9375
    else:
        t -= (2.625 / 2.75)
        return 7.5625 * t * t + 0.984375


def ease_out_elastic(t: float) -> float:
    t = linear(t)
    if t == 0.0 or t == 1.0:
        return t
    p = 0.3
    s = p / 4.0
    return math.pow(2.0, -10.0 * t) * math.sin((t - s) * (2.0 * math.pi) / p) + 1.0


def spring_step(
    current: float,
    target: float,
    velocity: float,
    stiffness: float = 180.0,
    damping: float = 18.0,
    dt: float = 0.016,
) -> Tuple[float, float]:
    """Single Euler integration step for critically damped or bouncy spring."""
    dt = max(1e-4, min(0.1, dt))
    force = -stiffness * (current - target) - damping * velocity
    new_velocity = velocity + force * dt
    new_current = current + new_velocity * dt
    return new_current, new_velocity


def interpolate(start: float, end: float, t: float, easing: str = "ease_out_quad") -> float:
    """Interpolate between start and end using specified easing curve."""
    easings = {
        "linear": linear,
        "ease_in": ease_in_quad,
        "ease_out": ease_out_quad,
        "ease_in_out": ease_in_out_quad,
        "ease_in_cubic": ease_in_cubic,
        "ease_out_cubic": ease_out_cubic,
        "ease_in_out_cubic": ease_in_out_cubic,
        "bounce": ease_out_bounce,
        "elastic": ease_out_elastic,
    }
    func = easings.get(easing.lower(), ease_out_quad)
    return start + (end - start) * func(t)
