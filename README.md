# Buddy 2.0 — Desktop Companion & Productivity Platform (macOS Beta & Linux)

[![Platform: Linux](https://img.shields.io/badge/Linux-Fedora%20%7C%20Ubuntu%20%7C%20Arch-blue)](https://getfedora.org/)
[![Platform: macOS](https://img.shields.io/badge/macOS-Apple%20Silicon%20%7C%20Intel%20(Beta)-black?logo=apple)](MACOS.md)
[![Python](https://img.shields.io/badge/Python-3.9%2B-yellow)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

Buddy 2.0 is an autonomous desktop companion and productivity platform engineered natively for **macOS** (AppKit, PyObjC, Quartz CoreGraphics) and **Linux** (Fedora, GNOME, KDE, Wayland, X11) using Python 3 and pure Cairo 2D vector graphics.

Buddy combines:
- Autonomous Character Simulator with personality profiles, moods, and behavior state machines.
- Deep Pomodoro Productivity Engine with companion focus and break reactions.
- Universal Power Tier System (Base, Signature, Power-Up, Ultimate) with unclipped screen-space visual effects.
- Extensible Skin & Companion Platform supporting 36 unique characters across Bleach, Superheroes, Animals, Fantasy, Sci-Fi, and Cute categories.
- 100% Native Integration: Native Cocoa AppKit windows, menus, and CADisplayLink/Retina rendering on macOS; native GTK3/GDK on Linux. Zero Electron overhead, zero web wrappers, and zero telemetry.

---

## Key Features

### Native macOS Architecture (v2.0.0 Beta)
- **AppKit & PyObjC Windowing**: Seamless borderless non-activating `NSPanel` floating at status window level (`NSStatusWindowLevel`), traveling across Mission Control spaces.
- **60 FPS Retina Cairo Pipeline**: Directly blits zero-allocation 32-bit ARGB Cairo surfaces to hardware-accelerated `CGImage` buffers in under 0.1 ms per frame at native 2x Retina scale.
- **Circular HitTesting & Click-Through**: Precision circular hitmasking (36 pt) ensures mouse clicks outside the companion pass straight through to underlying applications. Full click-through ghost mode supported.
- **Quartz Window Perching**: Companions detect application titlebars and headers via `CGWindowListCopyWindowInfo` in a background thread to perch on active windows.
- **Native Audio Engine**: Non-blocking background worker queue handling high-fidelity sound cues, channel prioritization, and procedural audio synthesis fallback.
- **Buddy Control Center**: Native two-pane Cocoa management window featuring live 60 FPS companion previews, instant ability triggers, skin switcher, behavior tuning, and appearance customization.

### Pomodoro Productivity Engine
- **Autonomous State Machine**: Configurable focus durations (default: 25 min), short breaks (5 min), and long breaks (15 min after 4 cycles).
- **Companion Focus Reactions**: Companions sit calmly, read, meditate, or take naps during focus sessions, and celebrate break intervals with custom effects.
- **Productivity Statistics**: Tracks daily focus minutes, completed sessions, and streaks stored locally in `~/.config/buddy/pomodoro_stats.json`.
- **Floating Badge**: Minimal countdown timer badge displaying live session status near the companion.

### Autonomous Behavior & Personality Engine
- **Disposition Matrix**: Every companion features configurable personality weights (`energy`, `curiosity`, `playfulness`, `sleepiness`).
- **Dynamic State Machine**: Evaluates cursor distance, velocity, inactivity, and Pomodoro mode to transition seamlessly between `IDLE`, `WALK`, `RUN`, `CURIOUS`, `PLAY`, `FOCUS`, `BREAK`, `CELEBRATE`, and `SLEEP`.
- **4 Behavior Modes**: Living Desk (quiet resting on desk), Wander (exploring desktop and window edges), Companion (following cursor with hysteresis deadzone), and Chaos (high-energy playground).

### Universal Power Tiers & Abilities
- **4-Tier Schema**: Standardized ability taxonomy: Base, Signature, Power-Up, and Ultimate.
- **Authentic Lore Labels**: Universe-specific naming (e.g., Zanpakuto release, Shikai, and Bankai for Bleach; repulsor and unibeam for Iron Man).
- **World-Space VFX**: Abilities render across screen space without clipping to the character's bounding box.
- **Combo Engine**: Chained ability triggers with semantic tag validation (e.g., Ice + Blade, Flame + Impact).

### 36 Characters Out-of-the-Box
- **Bleach Universe**: Ichigo Kurosaki, Rukia Kuchiki, Byakuya Kuchiki, Toshiro Hitsugaya, Genryusai Yamamoto, Sosuke Aizen, Ulquiorra Cifer, Yoruichi Shihoin, Shunsui Kyoraku, Shinji Hirako, Soi Fon, Mayuri Kurotsuchi.
- **Heroes**: Thor, Iron Man, Spider-Man, Hulk, Thanos, Superman, Batman, Captain America.
- **Animals**: Cat, Dog, Fox, Penguin.
- **Fantasy**: Dragon (Pitch-Black Dreadwyrm), Pixel Wizard, Fairy, Vampire, Harry Potter.
- **Sci-Fi**: Space Robot, Alien.
- **Cute**: Bouncy Slime, Ghost.

---

## Quick Start

### Installation on macOS

```bash
git clone https://github.com/SaurabMishra12/Buddy.git
cd Buddy

# Run macOS automated installer:
./scripts/install_macos.sh

# Or build the standalone macOS Application Bundle:
./scripts/build_macos_app.sh
cp -R dist/Buddy.app /Applications/
open /Applications/Buddy.app
```

See [MACOS.md](MACOS.md) for the master macOS guide and [INSTALL.md](INSTALL.md) for distro-specific Linux packages.

### Installation on Linux

```bash
git clone https://github.com/SaurabMishra12/Buddy.git
cd Buddy

# Run the Linux installer (Fedora / Ubuntu / Arch / openSUSE):
./install.sh
```

### Launching Buddy

```bash
# Launch default companion
buddy

# Launch with a specific companion
buddy --skin ichigo
buddy --skin byakuya
buddy --skin thor
buddy --skin slime

# Open Buddy Control Center (macOS)
buddy --control-center

# Open Settings
buddy --settings

# Open Skin Gallery (Linux)
buddy --skins

# View Productivity Statistics
buddy --stats

# Control Pomodoro Sessions
buddy --pomodoro start
buddy --pomodoro pause
buddy --pomodoro resume
buddy --pomodoro reset
```

---

## Desktop Controls & Interaction

| Input Gesture | Action | Description |
|---|---|---|
| Left-Click & Drag | Move Companion | Pick up and reposition Buddy anywhere across displays. |
| Double-Click | Control Center / Special | Opens the Buddy Control Center on macOS, or fires special ability on Linux. |
| Right-Click | Context Menu | Access companion switching, behavior modes, Pomodoro controls, and settings. |
| Scroll Wheel / Middle-Click | Cycle Skin | Instantly transforms into the next companion in the roster. |
| Cmd+, (macOS) | Preferences | Opens the Buddy Control Center. |
| Option-Click (macOS) | Pass-Through | Passes click through directly to the underlying application window. |

---

## Privacy & Local Architecture

- **100% Local-First**: No remote servers, no cloud dependencies, and zero analytics or telemetry.
- **Vector Cairo Pipeline**: Zero raster pixelation on 4K/5K Retina monitors.
- **Graceful Error Handling**: Corrupted configurations or missing audio automatically fall back to safe built-in defaults without crashing.

---

## Documentation

- [macOS Complete Guide & Architecture](MACOS.md)
- [System Architecture & Developer Guide](ARCHITECTURE.md)
- [Installation Guide](INSTALL.md)
- [Custom Skins & Schema](SKINS.md)
- [Development & Test Suite](DEVELOPMENT.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)

---

## License

MIT License. See [LICENSE](LICENSE) for details.
