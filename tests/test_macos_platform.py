"""Unit tests for native macOS backend components in Buddy.

Tests:
1. Platform detection contracts.
2. Cocoa / AppKit coordinate transformations (bottom-left Y-up vs top-left Y-down).
3. Native circular hitbox hitTest masking and click-through passthrough.
4. LaunchAgent plist management (creation, format validation, removal).
5. Native sound manager (NSSound caching, queue, tone generation).
6. Quartz window scanning resilience.
"""

import os
import plistlib
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from platforms import is_macos, is_linux, get_platform_name

if not is_macos():
    raise unittest.SkipTest("macOS native tests require macOS environment")

import AppKit
from platforms.macos.coordinate import (
    buddy_to_appkit_point,
    appkit_to_buddy_point,
    buddy_window_to_appkit_origin,
    get_primary_screen_height,
    get_virtual_desktop_bounds
)
from platforms.macos.window import MacOSOverlayWindow, BuddyOverlayView, WIN_SIZE, HALF_SIZE
from platforms.macos.autostart import MacOSAutostartManager, LAUNCH_AGENT_PLIST
from platforms.macos.audio import MacOSSoundManager
from platforms.macos.windows_detect import scan_macos_desktop_windows


class TestMacOSPlatform(unittest.TestCase):

    def test_platform_detection(self):
        """Verify macOS platform detection flags and name."""
        self.assertTrue(is_macos())
        self.assertFalse(is_linux())
        self.assertEqual(get_platform_name(), "macos")

    def test_coordinate_transforms_roundtrip(self):
        """Verify mathematical round-trip conversion between Buddy top-left and AppKit bottom-left coords."""
        screen_h = 1080.0
        test_points = [
            (0.0, 0.0),
            (500.0, 300.0),
            (1920.0, 1080.0),
            (960.0, 540.0),
            (123.45, 678.90)
        ]
        for bx, by in test_points:
            ax, ay = buddy_to_appkit_point(bx, by, screen_h)
            rx, ry = appkit_to_buddy_point(ax, ay, screen_h)
            self.assertAlmostEqual(bx, rx, places=4, msg=f"X mismatch for point ({bx}, {by})")
            self.assertAlmostEqual(by, ry, places=4, msg=f"Y mismatch for point ({bx}, {by})")

    def test_window_origin_conversion(self):
        """Verify window top-left (wx, wy) converts correctly to AppKit bottom-left origin."""
        screen_h = 1000.0
        wx, wy = 100, 200
        ww, wh = 180, 180
        ax, ay = buddy_window_to_appkit_origin(wx, wy, ww, wh, screen_h)
        self.assertEqual(ax, 100.0)
        # Top-left at wy=200 with height 180 means bottom edge is at wy=380.
        # In bottom-left coords: 1000 - 380 = 620
        self.assertEqual(ay, 620.0)

    def test_virtual_desktop_bounds(self):
        """Verify multi-monitor bounds retrieval returns valid positive geometry."""
        x, y, w, h = get_virtual_desktop_bounds()
        self.assertGreater(w, 0.0)
        self.assertGreater(h, 0.0)
        self.assertGreaterEqual(get_primary_screen_height(), 480.0)

    def test_hittest_circular_mask_and_clickthrough(self):
        """Verify native AppKit hitTest: restricts clicks to 54px circle and passes through when enabled."""
        overlay = MacOSOverlayWindow(on_draw=lambda view, ctx: None)
        view = overlay.view

        # Center of 180x180 window is (90, 90)
        # 1. Point at center (dx=0, dy=0) -> Should hit
        center_pt = AppKit.NSPoint(90, 90)
        self.assertIsNotNone(view.hitTest_(center_pt))

        # 2. Point 40px away from center -> within 54px -> Should hit
        inside_pt = AppKit.NSPoint(90 + 40, 90)
        self.assertIsNotNone(view.hitTest_(inside_pt))

        # 3. Corner of window (0, 0) -> distance sqrt(90^2 + 90^2) = 127px > 54px -> Should be click-through (None)
        corner_pt = AppKit.NSPoint(5, 5)
        self.assertIsNone(view.hitTest_(corner_pt))

        # 4. Enable click-through -> Even center point returns None
        overlay.set_click_through(True)
        self.assertIsNone(view.hitTest_(center_pt))

        # 5. Disable click-through -> Center hits again
        overlay.set_click_through(False)
        self.assertIsNotNone(view.hitTest_(center_pt))

        overlay.close()

    def test_launchagent_plist_lifecycle(self):
        """Verify creation, validation, and deletion of user LaunchAgent plist."""
        autostart = MacOSAutostartManager()
        backup_exists = LAUNCH_AGENT_PLIST.exists()
        backup_content = LAUNCH_AGENT_PLIST.read_bytes() if backup_exists else None

        try:
            # Enable autostart
            success = autostart.set_autostart(True)
            self.assertTrue(success)
            self.assertTrue(LAUNCH_AGENT_PLIST.exists())
            self.assertTrue(autostart.is_autostart_enabled())

            # Validate plist format and keys
            with open(LAUNCH_AGENT_PLIST, "rb") as fp:
                plist_data = plistlib.load(fp)
            self.assertEqual(plist_data.get("Label"), "com.saurabmishra.buddy")
            self.assertTrue(plist_data.get("RunAtLoad"))
            self.assertIn("ProgramArguments", plist_data)
            self.assertTrue(len(plist_data["ProgramArguments"]) >= 1)

            # Disable autostart
            success = autostart.set_autostart(False)
            self.assertTrue(success)
            self.assertFalse(LAUNCH_AGENT_PLIST.exists())
            self.assertFalse(autostart.is_autostart_enabled())

        finally:
            # Restore previous state
            if backup_exists and backup_content is not None:
                LAUNCH_AGENT_PLIST.write_bytes(backup_content)
            elif LAUNCH_AGENT_PLIST.exists():
                LAUNCH_AGENT_PLIST.unlink()

    def test_macos_sound_manager(self):
        """Verify MacOSSoundManager initialization, volume, and playback limits."""
        audio = MacOSSoundManager(enabled=True, volume=0.5)
        self.assertEqual(audio.volume, 0.5)
        self.assertTrue(hasattr(audio, "_audio_queue"))
        self.assertIsNotNone(audio._audio_queue)

        # Set volume bounds
        audio.set_volume(1.5)
        self.assertEqual(audio.volume, 1.0)
        audio.set_volume(-0.5)
        self.assertEqual(audio.volume, 0.0)

        # Cooldown prevents rapid repeat playback
        audio.set_volume(0.8)
        audio.play("bark")
        t_first = audio.last_played.get("bark", 0)
        audio.play("bark")  # Rapid second call should be ignored by cooldown
        self.assertEqual(audio.last_played.get("bark"), t_first)

    def test_quartz_window_scan(self):
        """Verify scan_macos_desktop_windows returns DesktopLedge items including menu bar."""
        ledges = scan_macos_desktop_windows((0, 0, 1920, 1080))
        self.assertIsInstance(ledges, list)
        self.assertGreater(len(ledges), 0)
        # At least the menu bar ledge must be present
        menu_bar = [l for l in ledges if l.title == "macOS Menu Bar"]
        self.assertEqual(len(menu_bar), 1)
        self.assertEqual(menu_bar[0].ledge_type, "panel")
        self.assertGreater(menu_bar[0].width, 1000.0)


if __name__ == "__main__":
    unittest.main()
