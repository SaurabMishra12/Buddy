# Buddy 2.0 Troubleshooting Guide

Common questions, desktop integration solutions, and tips for Linux systems.

---

## Wayland vs X11 Compatibility

### Symptoms:
* Cursor is not tracked when outside the Buddy overlay.
* Buddy overlay has a solid black or grey background instead of being transparent.

### Explanation & Solution:
Buddy defaults to setting `GDK_BACKEND=x11`. On modern GNOME and KDE Wayland sessions, XWayland provides global mouse polling and transparent input shape pass-through without requiring privileged compositor extensions.

Ensure XWayland is available on your system:
```bash
echo $DISPLAY  # Should output :0 or similar
```
If you encounter display initialization errors, verify that `cairo-gobject` and `gtk3` are installed:
```bash
# Fedora:
sudo dnf install -y gtk3 cairo-gobject
# Ubuntu/Debian:
sudo apt install -y gir1.2-gtk-3.0 python3-cairo
# Arch:
sudo pacman -S gtk3 python-cairo python-gobject
```

---

## Pomodoro Notifications & DBus

### Symptoms:
* Focus session or break end alerts do not appear on your desktop.

### Solution:
Buddy automatically attempts DBus notification dispatch (`org.freedesktop.Notifications`) and falls back to `notify-send`.

Verify `notify-send` is installed:
```bash
# Fedora:
sudo dnf install -y libnotify
# Ubuntu/Debian:
sudo apt install -y libnotify-bin
```
Test notifications manually:
```bash
notify-send "Buddy Test" "Notifications are working!"
```

---

## Mouse Clicks and Window Interaction

### "Clicks pass through Buddy and I can't click the companion"
* **Normal Behavior**: When **"100% Click-Through Overlay"** is enabled, Buddy passes all mouse events to the background so that it never disrupts your terminal, code editor, or browser workflow.
* **To interact directly with Buddy**:
  - Right-click the **System Tray icon** $\to$ **Buddy Mode** $\to$ uncheck **"Click-through"**.
  - Or run: `buddy --settings` $\to$ **Appearance** $\to$ uncheck **"100% Click-Through Overlay"**.
  - In interactive mode, clicks on Buddy allow dragging, petting, and right-clicking the context menu, while clicks outside Buddy continue passing through cleanly.

---

## Audio & Sound Effects

### "I don't hear any sounds"
1. Verify that sound is enabled:
   ```bash
   buddy --settings  # Check General / Accessibility tabs
   ```
2. Ensure **Quiet Mode** is disabled in the right-click menu or tray.
3. Buddy automatically detects and uses any of `pw-play` (PipeWire), `paplay` (PulseAudio), or `aplay` (ALSA). Test with:
   ```bash
   pw-play /usr/share/sounds/freedesktop/stereo/complete.oga
   ```
   If no player is found, install `pipewire-utils` or `pulseaudio-utils`:
   ```bash
   # Fedora:
   sudo dnf install -y pipewire-utils
   # Ubuntu:
   sudo apt install -y pulseaudio-utils
   ```

---

## Performance Optimization

Buddy 2.0 provides adaptive quality presets in `buddy --settings` $\to$ **Performance**:
* **Low**: 30 FPS cap, 100 particle limit, screen shake disabled. Ideal for low-power laptops on battery.
* **Balanced (Default)**: 60 FPS target, 250 particle limit, screen shake enabled.
* **High**: 60 FPS target, 400 particle limit.
* **Ultra**: 120 FPS high-refresh rate, 600 particle limit.

---

## Resetting Configuration & Statistics

If you ever wish to restore factory defaults:
```bash
# Reset settings:
rm -f ~/.config/buddy/config.json

# Reset Pomodoro statistics:
rm -f ~/.config/buddy/pomodoro_stats.json

# Reset character memory:
rm -rf ~/.config/buddy/memory/
```
The next time Buddy launches, it will regenerate clean default settings.
