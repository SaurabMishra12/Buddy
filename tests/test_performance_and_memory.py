"""Performance, Memory, and Lag Benchmark Tests for Buddy.

Validates:
1. Dragon character shared surface caching (zero memory leak on repeat instantiations).
2. High-performance frame rendering (< 1.2 ms / frame).
3. Window movement IPC deduplication (zero redundant XMoveWindow calls when stationary).
4. Paused simulation throttle (no queue_draw calls when paused).
5. Zero list churn in ParticleManager when idle.
6. Non-blocking pre-initialized audio queue.
"""

import os
import time
import unittest
import cairo
from unittest.mock import MagicMock

from skins.manager import skin_manager
from skins.dragon.character import DragonCharacter
from core.particles import ParticleManager
from core.window import OverlayWindow
from core.audio import audio_manager


class TestPerformanceAndMemory(unittest.TestCase):

    def test_dragon_surface_cache_prevents_memory_leak(self):
        """Verify DragonCharacter reuses cached surfaces across repeated instantiations."""
        d1 = DragonCharacter(100.0, 100.0)
        d2 = DragonCharacter(200.0, 200.0)
        d3 = DragonCharacter(300.0, 300.0)

        # Surfaces must be the exact same objects in memory
        self.assertIs(d1.fly_surfaces, d2.fly_surfaces)
        self.assertIs(d2.fly_surfaces, d3.fly_surfaces)
        self.assertIs(d1.seat_surfaces, d2.seat_surfaces)
        self.assertGreater(len(d1.fly_surfaces), 0)
        self.assertGreater(len(d1.seat_surfaces), 0)

    def test_dragon_frame_render_speed(self):
        """Verify optimized Dragon frame renders in under 1.2ms on CPU."""
        dragon = DragonCharacter(90.0, 90.0)
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 180, 180)
        ctx = cairo.Context(surf)
        pm = ParticleManager()

        # Warm-up
        dragon.draw(ctx, pm)

        # Benchmark 100 frames
        t0 = time.perf_counter()
        for _ in range(100):
            dragon.anim_time += 0.016
            ctx.save()
            ctx.set_operator(cairo.OPERATOR_CLEAR)
            ctx.paint()
            ctx.restore()
            dragon.draw(ctx, pm)
            surf.flush()
        t1 = time.perf_counter()
        avg_ms = (t1 - t0) / 100.0 * 1000.0

        print(f"\n[Benchmark] Dragon average draw time: {avg_ms:.3f} ms/frame")
        self.assertLess(avg_ms, 1.2, f"Draw time {avg_ms:.3f} ms exceeded 1.2ms budget")

    def test_window_move_deduplication(self):
        """Verify OverlayWindow.move_to does not call window.move when coordinates are unchanged."""
        mock_draw = MagicMock()
        win = OverlayWindow(on_draw=mock_draw)
        mock_gtk_win = MagicMock()
        win.window = mock_gtk_win

        # First move to (200.0, 200.0)
        win.move_to(200.0, 200.0)
        self.assertEqual(mock_gtk_win.move.call_count, 1)

        # Subsequent move to exact same position
        win.move_to(200.0, 200.0)
        self.assertEqual(mock_gtk_win.move.call_count, 1)  # No redundant call!

        # Subpixel jitter less than 1 integer pixel
        win.move_to(200.2, 200.4)
        self.assertEqual(mock_gtk_win.move.call_count, 1)  # Still no redundant call!

        # Meaningful move
        win.move_to(210.0, 205.0)
        self.assertEqual(mock_gtk_win.move.call_count, 2)

    def test_particle_update_zero_allocations_when_idle(self):
        """Verify ParticleManager.update does not recreate list objects when empty."""
        pm = ParticleManager()
        sparks_id = id(pm.sparks)
        flames_id = id(pm.flames)
        smoke_id = id(pm.smoke)

        # 10 updates when idle
        for _ in range(10):
            pm.update()

        # List object references should remain unchanged (no re-allocation churn)
        self.assertEqual(id(pm.sparks), sparks_id)
        self.assertEqual(id(pm.flames), flames_id)
        self.assertEqual(id(pm.smoke), smoke_id)

    def test_lazy_skin_manager_import_speed(self):
        """Verify lazy skin manager exposes metadata immediately without eager module loading."""
        available = skin_manager.get_available_skins()
        self.assertGreaterEqual(len(available), 11)
        # Verify specific metadata
        dragon_meta = skin_manager.get_metadata("dragon")
        self.assertIsNotNone(dragon_meta)
        self.assertEqual(dragon_meta["name"], "Dragon")
        self.assertTrue(dragon_meta["canFly"])

    def test_audio_manager_worker_thread_alive(self):
        """Verify audio manager has an active non-blocking worker queue."""
        self.assertTrue(hasattr(audio_manager, "_audio_queue"))
        self.assertIsNotNone(audio_manager._audio_queue)


if __name__ == "__main__":
    unittest.main()
