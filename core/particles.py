"""Reusable particle engine: lightning arcs, fire, smoke, cosmic energy, and shockwaves."""

import math
import random
import cairo
from typing import List, Tuple, Optional

# Color presets (R, G, B)
CYAN_GLOW = (0.0, 0.9, 1.0)
BLUE_GLOW = (0.1, 0.35, 0.95)
WHITE_CORE = (1.0, 1.0, 1.0)
FIRE_ORANGE = (1.0, 0.45, 0.05)
FIRE_YELLOW = (1.0, 0.9, 0.1)
SMOKE_GREY = (0.35, 0.35, 0.38)
MAGIC_PURPLE = (0.85, 0.2, 0.95)
MAGIC_GOLD = (1.0, 0.85, 0.2)
COSMIC_VIOLET = (0.6, 0.1, 0.9)


class Spark:
    """An individual electric or energetic spark particle."""

    def __init__(
        self,
        x: float,
        y: float,
        vx: Optional[float] = None,
        vy: Optional[float] = None,
        color: Tuple[float, float, float] = CYAN_GLOW,
        size: float = 2.4,
        decay: Optional[float] = None
    ):
        self.x = float(x)
        self.y = float(y)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2.0, 8.0)
        self.vx = vx if vx is not None else math.cos(angle) * speed
        self.vy = vy if vy is not None else math.sin(angle) * speed
        self.life = 1.0
        self.decay = decay if decay is not None else random.uniform(0.04, 0.09)
        self.size = size
        self.color = color

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2  # subtle gravity
        self.vx *= 0.95
        self.vy *= 0.95
        self.life -= self.decay
        return self.life > 0

    def draw(self, ctx: cairo.Context) -> None:
        alpha = max(0.0, min(1.0, self.life))
        ctx.save()
        # Outer glow
        r, g, b = self.color
        ctx.set_source_rgba(r, g, b, alpha * 0.7)
        ctx.arc(self.x, self.y, self.size * 1.6, 0, 2 * math.pi)
        ctx.fill()
        # Core
        ctx.set_source_rgba(1.0, 1.0, 1.0, alpha)
        ctx.arc(self.x, self.y, self.size * 0.7, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()


class FlameParticle:
    """Rising flame or thruster particle with turbulent motion."""

    def __init__(self, x: float, y: float, vx: float = 0.0, vy: float = -3.0, size: float = 6.0):
        self.x = float(x) + random.uniform(-3, 3)
        self.y = float(y) + random.uniform(-2, 2)
        self.vx = vx + random.uniform(-1.0, 1.0)
        self.vy = vy + random.uniform(-1.5, 0.5)
        self.life = 1.0
        self.decay = random.uniform(0.05, 0.12)
        self.size = size
        self.initial_size = size

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.vx += random.uniform(-0.3, 0.3)
        self.size = max(0.5, self.initial_size * self.life)
        self.life -= self.decay
        return self.life > 0

    def draw(self, ctx: cairo.Context) -> None:
        alpha = max(0.0, min(1.0, self.life))
        ctx.save()
        if self.life > 0.6:
            r, g, b = FIRE_YELLOW
        elif self.life > 0.3:
            r, g, b = FIRE_ORANGE
        else:
            r, g, b = (0.9, 0.1, 0.05)
        ctx.set_source_rgba(r, g, b, alpha * 0.85)
        ctx.arc(self.x, self.y, self.size, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()


class SmokeParticle:
    """Soft expanding smoke puff that drifts and dissipates."""

    def __init__(self, x: float, y: float, vx: float = 0.0, vy: float = -1.0, color: Tuple[float, float, float] = SMOKE_GREY):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx + random.uniform(-0.8, 0.8)
        self.vy = vy + random.uniform(-0.5, 0.5)
        self.life = 1.0
        self.decay = random.uniform(0.03, 0.06)
        self.size = random.uniform(4.0, 8.0)
        self.growth = random.uniform(0.3, 0.6)
        self.color = color

    def update(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.size += self.growth
        self.vx *= 0.96
        self.vy *= 0.96
        self.life -= self.decay
        return self.life > 0

    def draw(self, ctx: cairo.Context) -> None:
        alpha = max(0.0, min(1.0, self.life * 0.45))
        ctx.save()
        r, g, b = self.color
        ctx.set_source_rgba(r, g, b, alpha)
        ctx.arc(self.x, self.y, self.size, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()


class Shockwave:
    """Expanding circular energy wave for impacts, catches, and smashes."""

    def __init__(
        self,
        x: float,
        y: float,
        max_radius: float = 65.0,
        color: Tuple[float, float, float] = CYAN_GLOW,
        line_width: float = 2.8
    ):
        self.x = float(x)
        self.y = float(y)
        self.radius = 3.0
        self.max_radius = max_radius
        self.life = 1.0
        self.decay = 0.055
        self.color = color
        self.line_width = line_width

    def update(self) -> bool:
        self.radius += (self.max_radius - self.radius) * 0.22 + 1.8
        self.life -= self.decay
        return self.life > 0 and self.radius < self.max_radius

    def draw(self, ctx: cairo.Context) -> None:
        alpha = max(0.0, min(1.0, self.life))
        ctx.save()
        r, g, b = self.color
        ctx.set_line_width(self.line_width * alpha)
        ctx.set_source_rgba(r, g, b, alpha * 0.85)
        ctx.arc(self.x, self.y, self.radius, 0, 2 * math.pi)
        ctx.stroke()
        ctx.restore()


class LightningBolt:
    """Fractal jagged lightning bolt with branching forks and multi-pass bloom."""

    def __init__(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        branches: int = 2,
        lifetime: int = 5,
        color: Tuple[float, float, float] = CYAN_GLOW
    ):
        self.points = self._generate_bolt(x1, y1, x2, y2, roughness=0.32)
        self.branch_bolts: List[List[Tuple[float, float]]] = []
        self.lifetime = lifetime
        self.age = 0
        self.color = color

        if branches > 0 and len(self.points) > 4:
            for _ in range(branches):
                idx = random.randint(1, len(self.points) - 2)
                bx, by = self.points[idx]
                angle = random.uniform(-0.9, 0.9)
                dx = (x2 - x1)
                dy = (y2 - y1)
                base_angle = math.atan2(dy, dx)
                branch_angle = base_angle + angle
                branch_len = math.hypot(dx, dy) * random.uniform(0.2, 0.45)
                end_x = bx + math.cos(branch_angle) * branch_len
                end_y = by + math.sin(branch_angle) * branch_len
                self.branch_bolts.append(self._generate_bolt(bx, by, end_x, end_y, roughness=0.25))

    def _generate_bolt(self, x1: float, y1: float, x2: float, y2: float, roughness: float = 0.3) -> List[Tuple[float, float]]:
        segments = [(x1, y1), (x2, y2)]
        iterations = 4
        for _ in range(iterations):
            new_segments = []
            for i in range(len(segments) - 1):
                p1 = segments[i]
                p2 = segments[i + 1]
                mid_x = (p1[0] + p2[0]) / 2.0
                mid_y = (p1[1] + p2[1]) / 2.0
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1]
                length = math.hypot(dx, dy)
                # Perpendicular displacement
                norm_x = -dy / (length + 1e-6)
                norm_y = dx / (length + 1e-6)
                offset = (random.random() - 0.5) * length * roughness
                mid_x += norm_x * offset
                mid_y += norm_y * offset
                new_segments.append(p1)
                new_segments.append((mid_x, mid_y))
            new_segments.append(segments[-1])
            segments = new_segments
        return segments

    def update(self) -> bool:
        self.age += 1
        return self.age < self.lifetime

    def draw(self, ctx: cairo.Context) -> None:
        alpha = 1.0 - (self.age / self.lifetime)
        r, g, b = self.color
        all_lines = [self.points] + self.branch_bolts

        ctx.save()
        # Pass 1: Electric Blue Ambient Bloom
        ctx.set_source_rgba(BLUE_GLOW[0], BLUE_GLOW[1], BLUE_GLOW[2], alpha * 0.35)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.set_line_width(7.0)
        for line in all_lines:
            if len(line) < 2:
                continue
            ctx.new_path()
            ctx.move_to(line[0][0], line[0][1])
            for pt in line[1:]:
                ctx.line_to(pt[0], pt[1])
            ctx.stroke()

        # Pass 2: Main colored bolt
        ctx.set_source_rgba(r, g, b, alpha * 0.9)
        ctx.set_line_width(3.2)
        for line in all_lines:
            if len(line) < 2:
                continue
            ctx.new_path()
            ctx.move_to(line[0][0], line[0][1])
            for pt in line[1:]:
                ctx.line_to(pt[0], pt[1])
            ctx.stroke()

        # Pass 3: White Hot Core
        ctx.set_source_rgba(1.0, 1.0, 1.0, alpha)
        ctx.set_line_width(1.2)
        for line in all_lines:
            if len(line) < 2:
                continue
            ctx.new_path()
            ctx.move_to(line[0][0], line[0][1])
            for pt in line[1:]:
                ctx.line_to(pt[0], pt[1])
            ctx.stroke()

        ctx.restore()


class ParticleManager:
    """Coordinates simulation and drawing of all active particles and effects."""

    def __init__(self, max_particles: int = 300):
        self.max_particles = max_particles
        self.sparks: List[Spark] = []
        self.flames: List[FlameParticle] = []
        self.smoke: List[SmokeParticle] = []
        self.shockwaves: List[Shockwave] = []
        self.bolts: List[LightningBolt] = []
        self.enabled: bool = True

    @property
    def particles(self) -> List[Any]:
        """Aggregate list of all active particulate entities."""
        return list(self.sparks) + list(self.flames) + list(self.smoke)

    def clear(self) -> None:
        """Clear all active particles."""
        self.sparks.clear()
        self.flames.clear()
        self.smoke.clear()
        self.shockwaves.clear()
        self.bolts.clear()

    def burst_sparks(
        self,
        x: float,
        y: float,
        count: int = 6,
        color: Tuple[float, float, float] = CYAN_GLOW,
        size: float = 2.4
    ) -> None:
        """Spawn a radial burst of sparks."""
        if not self.enabled:
            return
        for _ in range(count):
            if len(self.sparks) >= self.max_particles:
                break
            self.sparks.append(Spark(x, y, color=color, size=size))

    def sky_strike(self, target_x: float, target_y: float, color: Tuple[float, float, float] = CYAN_GLOW) -> None:
        """Create a monumental lightning bolt striking from the top of the monitor."""
        if not self.enabled:
            return
        start_x = target_x + random.uniform(-100, 100)
        start_y = 0.0
        self.bolts.append(LightningBolt(start_x, start_y, target_x, target_y, branches=3, lifetime=6, color=color))
        self.burst_sparks(target_x, target_y, count=16, color=color)
        self.shockwave(target_x, target_y, max_radius=60.0, color=color)

    def arc_connect(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        branches: int = 1,
        color: Tuple[float, float, float] = CYAN_GLOW
    ) -> None:
        """Create a short-lived electric arc between two points."""
        if not self.enabled:
            return
        self.bolts.append(LightningBolt(x1, y1, x2, y2, branches=branches, lifetime=3, color=color))

    def shockwave(
        self,
        x: float,
        y: float,
        max_radius: float = 65.0,
        color: Tuple[float, float, float] = CYAN_GLOW,
        line_width: float = 2.8
    ) -> None:
        """Emit an expanding shockwave ring."""
        if not self.enabled:
            return
        self.shockwaves.append(Shockwave(x, y, max_radius=max_radius, color=color, line_width=line_width))

    def flame_puff(self, x: float, y: float, vx: float = 0.0, vy: float = -3.0, count: int = 3, size: float = 5.0) -> None:
        """Spawn flame particles for dragons, rockets, and explosions."""
        if not self.enabled:
            return
        for _ in range(count):
            if len(self.flames) >= self.max_particles:
                break
            self.flames.append(FlameParticle(x, y, vx=vx, vy=vy, size=size))

    def smoke_puff(self, x: float, y: float, count: int = 2, color: Tuple[float, float, float] = SMOKE_GREY) -> None:
        """Spawn smoke particles."""
        if not self.enabled:
            return
        for _ in range(count):
            if len(self.smoke) >= self.max_particles:
                break
            self.smoke.append(SmokeParticle(x, y, color=color))

    def cosmic_burst(self, x: float, y: float, count: int = 8, color: Tuple[float, float, float] = COSMIC_VIOLET) -> None:
        """Burst of cosmic stardust particles (Thanos / Magic)."""
        self.burst_sparks(x, y, count=count, color=color, size=3.0)
        self.shockwave(x, y, max_radius=50.0, color=color)

    def update(self) -> None:
        """Update simulation for all particles, removing dead ones."""
        self.sparks = [s for s in self.sparks if s.update()]
        self.flames = [f for f in self.flames if f.update()]
        self.smoke = [sm for sm in self.smoke if sm.update()]
        self.shockwaves = [sw for sw in self.shockwaves if sw.update()]
        self.bolts = [b for b in self.bolts if b.update()]

    def draw(self, ctx: cairo.Context) -> None:
        """Render all active particles in layered order."""
        if not self.enabled:
            return

        # 1. Background shockwaves
        for sw in self.shockwaves:
            sw.draw(ctx)

        # 2. Lightning bolts
        for b in self.bolts:
            b.draw(ctx)

        # 3. Smoke puffs
        for sm in self.smoke:
            sm.draw(ctx)

        # 4. Flames
        for f in self.flames:
            f.draw(ctx)

        # 5. Foreground sparks
        for s in self.sparks:
            s.draw(ctx)
