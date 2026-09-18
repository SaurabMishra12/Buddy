# 🔧 Buddy Troubleshooting Guide

Common questions, desktop integration solutions, and tips for Linux systems.

---

## 🖥️ Wayland vs X11 Compatibility

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
```

---

## 🖱️ Mouse Clicks and Window Interaction

### "Clicks pass through Buddy and I can't click the pet"
* **Normal Behavior**: By default, Buddy operates in **100% Click-Through Mode** so that it never disrupts your terminal, code editor, or browser workflow.
* **To interact directly with Buddy**:
  - Right-click the **System Tray icon** and uncheck **"100% Click-Through Overlay"**.
  - Or run: `buddy --settings` $\to$ **Display** $\to$ uncheck **"100% Click-Through Overlay"**.
  - In interactive mode, clicks on Buddy allow dragging, petting, and right-clicking the context menu, while clicks outside Buddy continue passing through to underlying applications.

---

## 🔊 Audio & Sound Effects

### "I don't hear any sounds"
1. Verify that sound is enabled:
   ```bash
   buddy --settings  # Check Audio tab
   ```
2. Verify audio playback utilities on your system:
   Buddy automatically detects and uses any of `pw-play` (PipeWire), `paplay` (PulseAudio), or `aplay` (ALSA). Test with:
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

## 🔄 Resetting Configuration

If you ever wish to restore factory defaults:
```bash
rm -f ~/.config/buddy/config.json
```
The next time Buddy launches, it will re-generate clean default settings.
