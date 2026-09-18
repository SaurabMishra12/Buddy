# ⚡ Buddy — Your Linux Desktop Companion

[![Platform](https://img.shields.io/badge/Platform-Fedora%20%7C%20Ubuntu%20%7C%20Arch%20%7C%20Linux-blue)](https://getfedora.org/)
[![Desktop](https://img.shields.io/badge/Desktop-GNOME%20%7C%20KDE%20%7C%20Wayland%20%7C%20X11-green)](https://www.gnu.org/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-yellow)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

**Buddy** is a polished, lightweight, extensible Linux desktop pet application designed primarily for **Fedora Linux** (GNOME, KDE Plasma, X11, Wayland) and other modern Linux distributions. Buddy brings your desktop to life with an animated superhero or fantasy companion living directly on your screen: walking, running, reacting to your cursor, performing character-specific abilities, and casting procedural particle effects.

---

## 🌟 Key Features

* **11 Character Skins Out-of-the-Box**:
  1. **Thor**: Preserved Mjolnir throwing/summoning physics, cloth-simulated Verlet cape, and fractal lightning arcs.
  2. **Dragon**: Wing flapping, gliding, soaring flight, fire breath cone, and fireball projectiles.
  3. **Cat**: Prowling, grooming, tail swishing, cursor stalking, zoomies pouncing, and curling up to nap.
  4. **Dog**: Playful barks, digging, wagging tail, floppy ears, and energetic cursor fetching.
  5. **Hulk**: Muscular colossus with ground-shattering smashes, shockwaves, roaring rage auras, and super leaps.
  6. **Iron Man**: Armored suit with boot thrusters, glowing arc reactor, air dash, and palm repulsor beams.
  7. **Harry Potter**: Gryffindor robes, lightning scar, wand spellcasting, flying broomstick, and teleport smoke.
  8. **Captain America**: Star-spangled hero throwing and ricocheting his Vibranium Shield across screen edges.
  9. **Thanos**: Titan wielding the Infinity Gauntlet (Time, Space, Power, Reality, Mind, Soul, and The Snap).
  10. **Batman**: Gotham's Dark Knight with grappling hook winch physics, batarangs, and cape gliding.
  11. **Superman**: Last Son of Krypton with supersonic flight, speed trails, and eye laser heat vision.

* **Linux-Native Desktop Integration**:
  - **Fedora First**: Built with Python 3 + PyGObject (GTK 3 / Gdk / GLib) and Cairo 2D vector acceleration.
  - **Wayland & X11**: Seamlessly runs on GNOME Wayland via XWayland input shape transparency.
  - **100% Click-Through Overlay**: Never obstructs your work, clicks, or terminal commands.
  - **Dynamic Interactive Mode**: Can switch to an interactive hitbox so you can drag, pet, and interact with Buddy.
  - **System Tray**: Native AppIndicator tray menu to change skins, toggle pause, and access settings.
  - **Multi-Monitor**: Support for single primary monitor or multi-monitor spanning.

* **Extensible Skin Pipeline**:
  - Add your own characters easily by dropping a `skin.json` into `~/.config/buddy/skins/` without modifying core code.

---

## 🚀 Quick Start

### Installation

Clone the repository and run the automated installer:

```bash
git clone https://github.com/SaurabMishra12/Buddy.git
cd Buddy
./install.sh
```

The installer installs the `buddy` command into `~/.local/bin/buddy` and registers the desktop launcher and high-definition icons in your Fedora application menu.

### Launching Buddy

Launch directly from terminal or your application menu:

```bash
# Launch default companion (Thor)
buddy

# Launch with a specific superhero or pet
buddy --skin dragon
buddy --skin cat
buddy --skin ironman
buddy --skin superman

# Open the visual Skin Gallery
buddy --skins

# Open Settings Dialog
buddy --settings

# Launch with Developer Diagnostics HUD
buddy --debug
```

### CLI Controls for Running Instance

When Buddy is running in the background, you can control it from any terminal:

```bash
buddy --pause          # Pause active companion
buddy --resume         # Resume active companion
buddy --skin thanos    # Dynamically switch skin
buddy --quit           # Close Buddy
```

---

## ⌨️ Desktop Controls & Interaction

| Action | Control | Description |
|---|---|---|
| **Pet / Drag** | Left-Click & Drag | Pick up and move Buddy anywhere across the screen with custom drag animations and trail particles |
| **Signature Move** | Double-Click Pet | Executes the character's signature special move (Thor sky strike & spin, Dragon fire circle, Cat flip, etc.) |
| **Context Menu** | Right-Click Pet | Popup menu with instant skin switcher (11 skins), abilities, size scaling, pause, and settings |
| **System Tray** | Click Tray Icon | Quick access to character switcher, pause, and preferences |
| **Developer HUD** | `--debug` CLI flag | Displays real-time FPS, coordinates, velocity, and state |

---

## 📂 Configuration & Data Directories

* **Configuration**: `~/.config/buddy/config.json`
* **Custom Skins**: `~/.config/buddy/skins/`
* **Cache & Audio**: `~/.cache/buddy/`
* **Autostart**: `~/.config/autostart/buddy.desktop`

---

## 🧪 Testing

Buddy includes a full automated test suite covering physics, particles, configuration, and all 11 character skins:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

---

## 📜 Documentation

* [INSTALL.md](INSTALL.md) — Comprehensive installation guide for Fedora, Ubuntu, Arch, and openSUSE.
* [DEVELOPMENT.md](DEVELOPMENT.md) — Architecture breakdown, physics engine, and developer tools.
* [SKINS.md](SKINS.md) — How to build and publish custom skins.
* [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Tips for Wayland, X11, transparency, and audio.

---

## 🛡️ License

MIT License. Designed with ❤️ for the Linux desktop community.
