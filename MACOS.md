# 🍏 Buddy on macOS — Native Desktop Companion Guide

Buddy 2.0 features **first-class native macOS support** built directly upon Apple's **AppKit**, **PyObjC**, and **Quartz CoreGraphics** frameworks alongside **Cairo 2D vector rendering**. 

Buddy runs as a lightweight, floating desktop companion with zero dependencies on X11, XQuartz, or Linux GTK libraries.

---

## 🌟 macOS Native Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       Buddy Engine                          │
│     (Physics, State Machine, Pomodoro, 22 Characters)       │
└──────────────────────────────┬──────────────────────────────┘
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
    ┌──────────────────────┐        ┌──────────────────────┐
    │     Linux Backend    │        │    macOS Backend     │
    │  (GTK3, GDK, Cairo)  │        │  (AppKit, PyObjC)    │
    └──────────────────────┘        └──────────┬───────────┘
                                               │
             ┌─────────────────────────────────┼────────────────────────────────┐
             ▼                                 ▼                                ▼
   ┌──────────────────┐              ┌──────────────────┐             ┌──────────────────┐
   │ MacOSOverlayWin  │              │ MacOSStatusItem  │             │ MacOSSoundManager│
   │ Borderless NSWin │              │ Native NSMenu    │             │ AppKit NSSound   │
   │ Circular hitTest │              │ Skin/Pomo/Scale  │             │ Non-blocking     │
   └─────────┬────────┘              └──────────────────┘             └──────────────────┘
             │
             ▼
   ┌──────────────────┐
   │ High-DPI Retina  │
   │ Cairo ARGB32 ->  │
   │ CGImage (0.06ms) │
   └──────────────────┘
```

### 1. Zero-Flicker High-DPI Retina Rendering
* Automatically detects `NSScreen.backingScaleFactor()` (typically `2.0` on Retina MacBook/iMac displays, `1.0` on standard external monitors).
* Cairo surface allocated at native pixel dimensions (`180 * scale = 360px`), with context matrix scaled `ctx.scale(scale, scale)` for crisp vector graphics.
* In-memory buffer transfer from Cairo `ImageSurface.get_data()` directly to `CGDataProviderCreateWithData` and `CGImageCreate` executes in **~0.060 ms/frame** (~16x faster than the 1.2ms budget).

### 2. Native Circular Hitbox Masking & Click-Through
* Overrides `hitTest:` in `BuddyOverlayView` to enforce an exact circular collision boundary ($r = 54\text{ px}$). Clicks outside this radius pass directly through to underlying macOS desktop windows without delay.
* Supports **100% Click-Through Mode** (`set_click_through(True)` / `window.setIgnoresMouseEvents_(True)`).

### 3. Coordinate System Canonicalization
* Canonical conversion functions (`platforms/macos/coordinate.py`) translate transparently between Buddy's top-left $Y$-down world and AppKit's bottom-left $Y$-up screen coordinate space, accounting for multi-display primary heights.

### 4. Native Menu Bar Controls
* Uses `NSStatusBar.systemStatusBar().statusItemWithLength_()` to place a native accessory icon in the top macOS menu bar.
* Offers instant access to all 22 characters, Pomodoro controls, companion scale slider, Settings dialog, and Quit.

### 5. Native Sound Engine (`NSSound`)
* Uses AppKit's native `NSSound` pipeline for asynchronous playback with zero subprocess spawning and zero terminal audio player dependencies.
* Built-in dynamic synthesizer caches procedural sound effects in `~/Library/Caches/Buddy/sounds/`.

### 6. User LaunchAgent Autostart
* Cleanly integrates with macOS `launchd` via user LaunchAgent plist (`~/Library/LaunchAgents/com.saurabmishra.buddy.plist`) with `RunAtLoad = true`.

### 7. Quartz Window Perching
* Utilizes `Quartz.CGWindowListCopyWindowInfo` to detect open application window titlebars, traffic-light buttons, and the top menu bar as physical perching surfaces for your companion.

---

## 🚀 Installation & Setup

### Prerequisites

* macOS 12 Monterey, 13 Ventura, 14 Sonoma, or 15 Sequoia (Apple Silicon M1/M2/M3/M4 or Intel x86_64).
* Python 3.9+ (Python 3.11+ recommended via Homebrew).

```bash
# If needed, install Python via Homebrew
brew install python3
```

### Option A: Quick Automated Installer (Recommended)

From the project root directory:

```bash
git clone https://github.com/SaurabMishra12/Buddy.git
cd Buddy
./scripts/install_macos.sh
```

This installer automatically installs required Python frameworks (`pycairo`, `pyobjc-framework-Cocoa`, `pyobjc-framework-Quartz`), links `buddy` to your CLI path, and verifies system compatibility.

### Option B: Build Standalone `Buddy.app` Bundle

To package Buddy as a standalone macOS application:

```bash
./scripts/build_macos_app.sh
```

Once built, move `Buddy.app` to your Applications folder:

```bash
cp -R dist/Buddy.app /Applications/
open /Applications/Buddy.app
```

The application runs in **Accessory Mode** (`LSUIElement = 1`), meaning it sits elegantly in your menu bar and floats across spaces without cluttering your Dock.

---

## ⌨️ Desktop Controls on macOS

| Action | Gesture / Key | Description |
|---|---|---|
| **Left-Click & Drag** | Click + Drag | Pick up and move companion anywhere across monitors. |
| **Double-Click** | Double Click | Trigger companion's signature ability (e.g. Thor Mjolnir throw, Dragon fire breath, Spider-Man web). |
| **Right-Click** | Secondary Click / 2-Finger Tap | Open native macOS context menu (Switch Skin, Pomodoro, Settings, Quit). |
| **Scroll Wheel** | Trackpad 2-Finger Scroll | Dynamically zoom companion scale ($0.5\times$ to $2.5\times$). |
| **Click-Through** | Menu Bar -> Appearance | Toggle click-through mode so Buddy hovers without intercepting mouse clicks. |

---

## 🛠️ CLI Commands

When launched via terminal:

```bash
# Launch default companion
buddy

# Launch with a specific companion
buddy --skin thor
buddy --skin dragon
buddy --skin ironman
buddy --skin spiderman

# Open Visual Skin Gallery
buddy --skins

# Open Multi-Section Settings
buddy --settings

# Pomodoro Focus Timer
buddy --pomodoro start
buddy --pomodoro pause
buddy --pomodoro resume
buddy --pomodoro reset

# View Productivity Statistics
buddy --stats

# Terminate running Buddy instance
buddy --quit
```

---

## 📁 File Locations on macOS

* **Configuration**: `~/Library/Application Support/Buddy/config.json`
* **Local Memory**: `~/Library/Application Support/Buddy/memory/`
* **Pomodoro Statistics**: `~/Library/Application Support/Buddy/pomodoro_stats.json`
* **Audio Cache**: `~/Library/Caches/Buddy/sounds/`
* **LaunchAgent Plist**: `~/Library/LaunchAgents/com.saurabmishra.buddy.plist`
* **Socket / PID**: `~/Library/Caches/Buddy/buddy.sock`

---

## 🔍 Troubleshooting

### 1. `buddy` command not found in Terminal
Add `~/.local/bin` to your shell profile (`~/.zshrc`):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

### 2. Window perching not detecting background windows
On macOS Mojave and later, `CGWindowListCopyWindowInfo` requires **Screen Recording** permission to read window titles across other apps. If not granted, Buddy gracefully falls back to desktop ledges and the menu bar. To enable full window perching:
* Open **System Settings -> Privacy & Security -> Screen Recording**.
* Enable Terminal / Python / Buddy.

### 3. Missing Audio
Ensure system volume is unmuted. Buddy uses macOS `NSSound` natively with volume scaled from the Settings dialog (`buddy --settings` -> Volume).
