# ⚡ Buddy 2.0 — Your Linux Desktop Companion & Productivity Platform

[![Platform](https://img.shields.io/badge/Platform-Fedora%20%7C%20Ubuntu%20%7C%20Arch%20%7C%20Linux-blue)](https://getfedora.org/)
[![Desktop](https://img.shields.io/badge/Desktop-GNOME%20%7C%20KDE%20%7C%20Wayland%20%7C%20X11-green)](https://www.gnu.org/)
[![Python](https://img.shields.io/badge/Python-3.9%2B-yellow)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

**Buddy 2.0** transforms the traditional Linux desktop pet into an intelligent, autonomous **desktop companion platform**. Built natively for **Fedora Linux**, GNOME, KDE Plasma, Wayland, and X11 using Python 3, PyGObject, and Cairo 2D vector graphics, Buddy combines:

```text
Desktop Pet + Character Simulator + Pomodoro Productivity Companion + Extensible Skin Platform
```

Buddy feels alive even when idle. Each companion boasts a distinct personality, autonomous behavioral engine, state machine, local memory, signature abilities, and deep Pomodoro focus/break reactions.

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
./install.sh
```

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
