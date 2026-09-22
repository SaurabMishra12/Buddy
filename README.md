# ⚡ Buddy 2.0 — Cross-Platform Desktop Companion & Productivity Assistant

[![Platform: Linux](https://img.shields.io/badge/Linux-Fedora%20%7C%20Ubuntu%20%7C%20Arch-blue)](https://getfedora.org/)
[![Platform: macOS](https://img.shields.io/badge/macOS-Apple%20Silicon%20%7C%20Intel-black?logo=apple)](MACOS.md)
[![Python](https://img.shields.io/badge/Python-3.9%2B-yellow)](https://www.python.org/)
[![CI](https://github.com/SaurabMishra12/Buddy/actions/workflows/ci.yml/badge.svg)](.github/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

**Buddy 2.0** transforms the traditional desktop pet into an intelligent, autonomous **desktop companion platform**. Built natively for both **macOS (AppKit / PyObjC / Retina)** and **Linux (Fedora, GNOME, KDE, Wayland, X11)** using Python 3 and Cairo 2D vector graphics, Buddy combines:

```text
Desktop Pet + Character Simulator + Pomodoro Productivity Companion + Extensible Skin Platform
```

Buddy feels alive even when idle. Each companion boasts a distinct personality, autonomous behavioral engine, state machine, local memory, signature abilities, and deep Pomodoro focus/break reactions. All platforms use 100% native windowing (no XQuartz or web wrappers on macOS; native GTK3/GDK on Linux).

---

## 🌟 What's New in Buddy 2.0

### 🍅 Pomodoro Productivity Engine & Companion Reactions
* **Autonomous Work / Break State Machine**: Configurable focus durations (default: 25m), short breaks (5m), and long breaks (15m after 4 cycles).
* **Companion Focus Reactions**: Buddies calm down during focus sessions (meditating, reading, napping, sitting quietly) and celebrate break time with confetti, star bursts, and dances!
* **Productivity Statistics Dashboard**: Tracks daily focused minutes, sessions completed today, consecutive day streaks, and weekly summaries saved locally in `~/.config/buddy/pomodoro_stats.json`.
* **Desktop Notifications & Sound Alerts**: Native DBus / `notify-send` alerts for session intervals.
* **Unobtrusive Floating Badge**: Compact pill timer displaying live focus/break countdowns near your companion.

### 🧠 Autonomous Character Behavior & Personality Engine
* **Disposition Matrix**: Characters have individual personality profiles (`energy`, `curiosity`, `playfulness`, `sleepiness`).
* **State Machine**: Evaluates cursor speed, distance, recent interactions, and Pomodoro mode to seamlessly transition between `IDLE`, `WALK`, `RUN`, `CURIOUS`, `PLAY`, `FOCUS`, `BREAK`, `CELEBRATE`, and `SLEEP`.
* **Local Memory**: Tracks interaction counts, favorite spots, and completed sessions locally in `~/.config/buddy/memory/` without telemetry.

### 🎭 22 Unique Characters Out-of-the-Box
Buddy 2.0 features **22 distinct characters** across Heroes, Animals, Fantasy, Sci-Fi, and Cute categories:

| Category | Companions |
|---|---|
| **Heroes** | **Thor**, **Iron Man**, **Spider-Man**, **Superman**, **Batman**, **Hulk**, **Captain America**, **Thanos** |
| **Animals** | **Cat**, **Dog**, **Fox**, **Penguin** |
| **Fantasy** | **Dragon** (Pitch-Black Dreadwyrm), **Pixel Wizard**, **Fairy**, **Vampire**, **Harry Potter** |
| **Sci-Fi** | **Space Robot**, **Alien** |
| **Cute** | **Bouncy Slime**, **Ghost** |

### 🎨 Visual Skin Gallery & Modern 6-Tab Settings
* **Character Gallery (`buddy --skins`)**: Browse all 22 characters with category filter tabs (*All*, *Heroes*, *Animals*, *Fantasy*, *Sci-Fi*, *Cute*), instant search, live personality meters, and ability summaries.
* **Multi-Section Settings (`buddy --settings`)**:
  - **General**: Default companion, scale, master volume, and autostart on login.
  - **Behavior**: Activity/energy level, movement speed, curiosity, wandering, and nap behavior.
  - **Appearance**: 100% click-through toggle, screen shake, floating Pomodoro badge, and monitor selector.
  - **Pomodoro**: Custom session durations, auto-start breaks, and notifications.
  - **Performance**: Quality presets (*Low*, *Balanced*, *High*, *Ultra*), target FPS (30/60/120), and particle caps.
  - **Accessibility**: Reduced motion, disable flashing effects, and quiet mode (mute audio).

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/SaurabMishra12/Buddy.git
cd Buddy

# On Linux (Fedora / Ubuntu / Arch):
./install.sh

# On macOS (Apple Silicon & Intel):
./scripts/install_macos.sh
# (Or build standalone Buddy.app: ./scripts/build_macos_app.sh)
```

See [INSTALL.md](INSTALL.md) for distro-specific packages and [MACOS.md](MACOS.md) for the complete macOS guide.

### Launching Buddy 2.0

```bash
# Launch default companion
buddy

# Launch with a specific companion
buddy --skin slime
buddy --skin fox
buddy --skin pixel_wizard
buddy --skin dragon
buddy --skin spiderman

# Open Visual Skin Gallery
buddy --skins

# Open Settings
buddy --settings

# View Productivity Dashboard
buddy --stats

# Control Pomodoro
buddy --pomodoro start
buddy --pomodoro pause
buddy --pomodoro resume
buddy --pomodoro reset
```

---

## ⌨️ Desktop Controls & Interaction

| Action | Control | Description |
|---|---|---|
| **Left-Click & Drag** | Mouse 1 + Drag | Pick up and move Buddy anywhere; triggers custom flight trails or running locomotion. |
| **Signature Move** | Double-Click | Executes the character's signature move (Thor sky strike, Slime bounce, Ninja smoke bomb, etc.). |
| **Cycle Companion** | Middle-Click / Scroll | Instant transformation to the next character. |
| **Context Menu** | Right-Click | Complete popup menu with Pomodoro controls, companion modes, abilities, scale, and settings. |
| **System Tray** | Tray Icon | Rich indicator menu supporting live Pomodoro status, companion switching, and modes. |

---

## 🔒 Privacy & Architecture

* **100% Local-First**: No telemetry, no remote servers, no cloud dependencies.
* **Linux-Native**: Built with Python 3, PyGObject (GTK 3/Gdk/GLib), and Cairo 2D vector graphics. Zero Electron bloat.
* **Wayland & X11**: Seamlessly runs on modern GNOME and KDE Wayland sessions via XWayland input shape pass-through.
* **Safe Configuration**: Corrupted settings gracefully fall back to defaults without crashing.

---

## 📜 Documentation

* [Installation Guide](INSTALL.md)
* [Custom Skins & Schema](SKINS.md)
* [Development & Testing](DEVELOPMENT.md)
* [Troubleshooting & Wayland](TROUBLESHOOTING.md)

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
