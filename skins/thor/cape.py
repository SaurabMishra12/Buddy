"""Verlet-like chain for dynamic cloth simulation of Thor's flowing scarlet cape."""

import math
import cairo

CAPE_SEGMENTS = 7
CAPE_LENGTH = 32.0
CAPE_GRAVITY = 0.5
CAPE_WIND_TURBULENCE = 1.2


class Cape:
    """Simulates realistic cloth inertia and wind turbulence for Thor's cape."""

    def __init__(self, x: float, y: float):
        self.segments = []
        seg_dist = CAPE_LENGTH / CAPE_SEGMENTS
        for i in range(CAPE_SEGMENTS):
            self.segments.append([x - (i * seg_dist), y + (i * seg_dist * 0.4)])
        self.wave_time = 0.0

    def update(self, anchor_x: float, anchor_y: float, vx: float, vy: float) -> None:
        self.wave_time += 0.15
        self.segments[0] = [anchor_x, anchor_y]
        seg_dist = CAPE_LENGTH / CAPE_SEGMENTS

        # Wind effect opposite to Thor's velocity
        wind_x = -vx * 1.8 + math.sin(self.wave_time * 2.0) * CAPE_WIND_TURBULENCE
        wind_y = -vy * 1.2 + math.cos(self.wave_time * 1.5) * CAPE_WIND_TURBULENCE + CAPE_GRAVITY

        for i in range(1, len(self.segments)):
            prev = self.segments[i - 1]
            curr = self.segments[i]

            # Apply wind & gravity
            curr[0] += wind_x * (i / CAPE_SEGMENTS) * 0.3
            curr[1] += wind_y * 0.4

            # Constrain distance to previous segment
            dx = curr[0] - prev[0]
            dy = curr[1] - prev[1]
            dist = math.hypot(dx, dy) + 1e-4
            curr[0] = prev[0] + (dx / dist) * seg_dist
            curr[1] = prev[1] + (dy / dist) * seg_dist

    def draw(self, ctx: cairo.Context, anchor_left_x: float, anchor_right_x: float, anchor_y: float) -> None:
        ctx.save()
        # Rich Norse scarlet red
        pat = cairo.LinearGradient(anchor_left_x, anchor_y, self.segments[-1][0], self.segments[-1][1])
        pat.add_color_stop_rgb(0.0, 0.85, 0.08, 0.12)  # Bright crimson top
        pat.add_color_stop_rgb(1.0, 0.55, 0.04, 0.07)  # Dark shadow bottom
        ctx.set_source(pat)

        ctx.new_path()
        ctx.move_to(anchor_left_x, anchor_y)
        # Left side down
        for i in range(len(self.segments)):
            width = 12.0 + (i * 2.8)
            ctx.line_to(self.segments[i][0] - width / 2, self.segments[i][1])
        # Bottom curve
        ctx.line_to(self.segments[-1][0] + (width / 2), self.segments[-1][1])
        # Right side up
        for i in range(len(self.segments) - 1, -1, -1):
            width = 12.0 + (i * 2.8)
            ctx.line_to(self.segments[i][0] + width / 2, self.segments[i][1])
        ctx.close_path()
        ctx.fill()

        # Cape fold shadow lines
        ctx.set_source_rgba(0.35, 0.02, 0.04, 0.4)
        ctx.set_line_width(1.5)
        ctx.move_to(anchor_left_x + 4, anchor_y)
        for pt in self.segments:
            ctx.line_to(pt[0], pt[1])
        ctx.stroke()

        ctx.restore()
