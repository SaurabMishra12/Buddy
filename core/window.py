"""Transparent, borderless overlay window management with X11/XWayland input shape masking."""

import sys
import cairo
from typing import Tuple, Optional, Callable

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk


class OverlayWindow:
    """Creates and manages an always-on-top, transparent, click-through desktop overlay."""

    def __init__(
        self,
        on_draw: Callable,
        on_button_press: Optional[Callable] = None,
        on_button_release: Optional[Callable] = None,
        on_motion: Optional[Callable] = None
    ):
        self.display = Gdk.Display.get_default()
        if not self.display:
            print("[Buddy Window] Error: Could not get default display.", file=sys.stderr)
            sys.exit(1)

        self.screen = Gdk.Screen.get_default()
        self.seat = self.display.get_default_seat()
        self.pointer = self.seat.get_pointer() if self.seat else None

        # Window creation
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.window.set_title("Buddy Desktop Pet")
        self.window.set_decorated(False)
        self.window.set_app_paintable(True)
        self.window.set_keep_above(True)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_accept_focus(False)  # Avoid stealing window focus

        # Enable RGBA visual for transparency
        visual = self.screen.get_rgba_visual()
        if visual is not None and self.screen.is_composited():
            self.window.set_visual(visual)
        else:
            print("[Buddy Window] Warning: RGBA compositing not active, transparency may be limited.", file=sys.stderr)

        # Connect events
        self.window.connect("draw", on_draw)
        self.window.connect("destroy", Gtk.main_quit)

        # Mouse input event masks
        self.window.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )
        if on_button_press:
            self.window.connect("button-press-event", on_button_press)
        if on_button_release:
            self.window.connect("button-release-event", on_button_release)
        if on_motion:
            self.window.connect("motion-notify-event", on_motion)

        # Realize window to access low-level GDK/X11 window
        self.window.realize()
        self.gdk_window = self.window.get_window()

        # Geometry setup
        self.bounds = self.get_display_geometry("current_monitor")
        self.apply_geometry()

        # Input shape mode
        self.click_through = True
        self.set_click_through(True)

    def get_display_geometry(self, mode: str = "current_monitor") -> Tuple[int, int, int, int]:
        """Calculates display bounds (x, y, width, height) across monitors."""
        n_monitors = self.display.get_n_monitors()
        if mode == "all_monitors" and n_monitors > 1:
            min_x = 0
            min_y = 0
            max_x = 0
            max_y = 0
            for i in range(n_monitors):
                mon = self.display.get_monitor(i)
                geom = mon.get_geometry()
                min_x = min(min_x, geom.x)
                min_y = min(min_y, geom.y)
                max_x = max(max_x, geom.x + geom.width)
                max_y = max(max_y, geom.y + geom.height)
            return min_x, min_y, max_x - min_x, max_y - min_y
        else:
            primary = self.display.get_primary_monitor() or self.display.get_monitor(0)
            geom = primary.get_geometry()
            return geom.x, geom.y, geom.width, geom.height

    def apply_geometry(self) -> None:
        """Position window over the screen bounds."""
        x, y, w, h = self.bounds
        self.window.move(x, y)
        self.window.resize(w, h)

    def set_click_through(self, enabled: bool) -> None:
        """Toggle whether clicks pass 100% through to background windows."""
        self.click_through = enabled
        if not self.gdk_window:
            return
        if enabled:
            # Empty region = all clicks pass through to apps below
            empty_region = cairo.Region()
            self.gdk_window.input_shape_combine_region(empty_region, 0, 0)
        else:
            # Full window receives clicks
            x, y, w, h = self.bounds
            rect = cairo.RectangleInt(0, 0, w, h)
            region = cairo.Region(rect)
            self.gdk_window.input_shape_combine_region(region, 0, 0)

    def update_interactive_hitbox(self, pet_x: float, pet_y: float, radius: float = 45.0) -> None:
        """Sets input shape exclusively around pet hitbox, leaving rest of screen click-through."""
        if self.click_through or not self.gdk_window:
            return
        x = int(pet_x - radius - self.bounds[0])
        y = int(pet_y - radius - self.bounds[1])
        size = int(radius * 2)
        rect = cairo.RectangleInt(x, y, size, size)
        region = cairo.Region(rect)
        self.gdk_window.input_shape_combine_region(region, 0, 0)

    def query_pointer(self) -> Tuple[float, float]:
        """Global pointer coordinates."""
        if not self.pointer:
            return 500.0, 400.0
        try:
            _, px, py = self.pointer.get_position()
            return float(px), float(py)
        except Exception:
            return 500.0, 400.0

    def queue_draw(self) -> None:
        self.window.queue_draw()

    def show(self) -> None:
        self.window.show_all()
