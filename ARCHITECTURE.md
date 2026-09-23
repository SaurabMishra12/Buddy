# Buddy 2.0 — Architecture & Developer Guide

Buddy is an animated cross-platform desktop companion and productivity assistant designed to run natively on **Linux** (GNOME, KDE, X11, Wayland) and **macOS** (Apple Silicon and Intel Cocoa/AppKit) with zero shared compromises.

---

## High-Level System Architecture

```
                                  ┌───────────────────────────┐
                                  │      CLI & Entrypoint     │
                                  │          (buddy)          │
                                  └─────────────┬─────────────┘
                                                │
                                  ┌─────────────▼─────────────┐
                                  │       BuddyEngine         │
                                  │     (core/engine.py)      │
                                  └─────────────┬─────────────┘
                                                │
                 ┌──────────────────────────────┼──────────────────────────────┐
                 │                              │                              │
      ┌──────────▼──────────┐        ┌──────────▼──────────┐        ┌──────────▼──────────┐
      │  Physics/Kinematics │        │   Pomodoro Engine   │        │   Particle Engine   │
      │   & State Machine   │        │ (pomodoro/manager)  │        │  (core/particles)   │
      └─────────────────────┘        └─────────────────────┘        └─────────────────────┘
                 │                              │                              │
                 └──────────────────────────────┼──────────────────────────────┘
                                                │
                                  ┌─────────────▼─────────────┐
                                  │   Platform Dispatcher     │
                                  │     (platforms/base)      │
                                  └─────────────┬─────────────┘
                                                │
                     ┌──────────────────────────┴──────────────────────────┐
                     │                                                     │
          ┌──────────▼──────────┐                               ┌──────────▼──────────┐
          │    macOS Backend    │                               │    Linux Backend    │
          │ (platforms/macos/)  │                               │  (platforms/linux/) │
          ├─────────────────────┤                               ├─────────────────────┤
          │ • NSWindow (AppKit) │                               │ • Gtk.Window (GTK3) │
          │ • Quartz CTM / CG   │                               │ • Gdk.Window (Cairo)│
          │ • NSStatusBar / Paw │                               │ • AppIndicator3     │
          │ • NSSound Engine    │                               │ • PulseAudio / ALSA │
          │ • LaunchAgent Plist │                               │ • XDG Autostart     │
          └─────────────────────┘                               └─────────────────────┘
```

---

## Core Architecture Principles

1. **Procedural Vector Drawing (Cairo-First)**:
   All character animations, poses, physics bodies, and visual effects are drawn via **PyCairo** vector geometry (`cairo.Context`). This guarantees pixel-perfect vector scalability at any display scaling factor without bitmap pixelation.
2. **Strict Platform Separation**:
   Platform-specific system calls (AppKit/PyObjC on macOS, GTK3/GDK/AppIndicator on Linux) are isolated in `platforms/macos/` and `platforms/linux/`. Core modules (`core/`, `skins/`, `pomodoro/`) never import platform-specific GUI libraries directly.
3. **High-DPI Retina Coordinate Space**:
   On macOS, `NSScreen.backingScaleFactor()` ($2.0\times$) allocates a native $360 \times 360\text{ px}$ pixel buffer. The Quartz CTM coordinate system is adjusted using `CGContextTranslateCTM` and `CGContextScaleCTM(1.0, -1.0)` to ensure all graphics, badges, and lightning strikes render upright and crisp.
4. **Polite Desktop Etiquette**:
   Companions maintain an interactive hit-test mask ($24\text{ px}$ radius) and employ **courtesy distancing** ($38\text{ px}$) when approaching the cursor, ensuring underlying desktop applications, links, and text fields are never obstructed.

---

## Companion Skin Architecture (`skins/`)

Every character in Buddy is a modular package residing in `skins/<skin_id>/`:

```
skins/
├── base.py                   # BaseCharacter contract & state machines
├── manager.py                # Skin discovery, normalization & lifecycle
├── thor/                     # Example Superhero Companion
│   ├── __init__.py
│   ├── character.py          # Pose kinematic rendering & abilities
│   └── metadata.py           # Lore, category, ability declarations
├── dragon/                   # Example Fantasy Flying Companion
├── cat/                      # Example Ground Pet Companion
└── ... (22 companions)
```

### Character States
Each companion transitions through formal states defined in [`core/physics.py`](file:///Users/tshrayansh/buddy%20for%20mac%20/core/physics.py):
* `CharacterState.IDLE`: Peaceful resting / breathing.
* `CharacterState.WALK`: Forward/backward stride cycle.
* `CharacterState.RUN`: Fast sprint or dash.
* `CharacterState.JUMP`: Vertical takeoff with gravity decay.
* `CharacterState.FALL`: Downward acceleration with terminal velocity.
* `CharacterState.FLY`: Autonomous aerial navigation with aerodynamic banking tilt.
* `CharacterState.HOVER`: Steady in-place flight oscillation.
* `CharacterState.SEAT`: Perched on an application window titlebar or desktop ledge.
* `CharacterState.SLEEP`: Low-power slumber animation during Pomodoro focus breaks.
* `CharacterState.SPECIAL`: Active signature ability / acrobatic stunt.

---

## How to Build and Add a New Character Companion

Adding a new character works identically across **both Linux and macOS**. Because character drawing uses pure procedural Cairo, any companion created runs instantly on both platforms without modification.

### Step 1: Create the Companion Directory
Create a folder under `skins/` matching your companion's lowercase identifier:

```bash
mkdir -p skins/fox_spirit
touch skins/fox_spirit/__init__.py
touch skins/fox_spirit/character.py
touch skins/fox_spirit/metadata.py
```

### Step 2: Define Companion Metadata (`metadata.py`)
Declare your companion's name, flight capability, classification, lore, and abilities:

```python
# skins/fox_spirit/metadata.py
METADATA = {
    "id": "fox_spirit",
    "name": "Kitsune",
    "category": "fantasy",            # heroes | animals | fantasy | sci-fi | cute
    "canFly": True,                   # True: flies freely; False: runs on ground/ledges
    "flight_speed": 12.0,
    "description": "A mystical nine-tailed fox spirit that conjures blue spirit orbs and glides across your desktop.",
    "abilities": ["spirit_flame", "teleport", "nine_tails_dance"],
    "signature_ability": "spirit_flame",
    "sound_theme": "magic",           # laser | magic | lightning | purr | bark | roar
}
```

### Step 3: Implement the Character Class (`character.py`)
Subclass `BaseCharacter` and implement the required procedural Cairo drawing passes:

```python
# skins/fox_spirit/character.py
import math
import cairo
from typing import Any, Tuple, Dict
from skins.base import BaseCharacter
from core.physics import CharacterState
from skins.fox_spirit.metadata import METADATA

class FoxSpiritCharacter(BaseCharacter):
    def __init__(self, x: float = 200.0, y: float = 200.0):
        super().__init__(skin_id="fox_spirit", x=x, y=y)
        self.can_fly = METADATA["canFly"]
        self.metadata = METADATA
        self.anim_time = 0.0

    def update(
        self,
        dt: float,
        cursor_x: float,
        cursor_y: float,
        bounds: Tuple[float, float, float, float],
        particle_mgr: Any,
        audio_mgr: Any,
        cfg: Dict[str, Any]
    ) -> None:
        """Update pose kinematics, autonomous decisions, and state."""
        super().update(dt, cursor_x, cursor_y, bounds, particle_mgr, audio_mgr, cfg)
        self.anim_time += dt

        # Spawn magical tail embers while moving
        if self.state in (CharacterState.FLY, CharacterState.RUN):
            if math.sin(self.anim_time * 15.0) > 0.6:
                particle_mgr.burst_sparks(self.x, self.y + 10, count=1, color=(0.3, 0.7, 1.0))

    def draw(self, ctx: cairo.Context) -> None:
        """Render vector companion using Cairo."""
        ctx.save()
        ctx.translate(self.x, self.y)

        # Apply horizontal flip when facing left
        if not self.facing_right:
            ctx.scale(-1.0, 1.0)

        # Apply flight banking tilt
        if abs(self.tilt) > 0.01:
            ctx.rotate(self.tilt)

        # 1. Render animated tails
        self._draw_tails(ctx)

        # 2. Render body & head
        self._draw_body(ctx)

        # 3. Render face & glowing markings
        self._draw_face(ctx)

        ctx.restore()

    def _draw_tails(self, ctx: cairo.Context) -> None:
        ctx.save()
        tail_wave = math.sin(self.anim_time * 6.0) * 8.0
        ctx.set_source_rgba(0.2, 0.6, 1.0, 0.85)
        ctx.move_to(-12, 10)
        ctx.curve_to(-35, 5 + tail_wave, -45, -15 - tail_wave, -55, -20)
        ctx.curve_to(-40, 5, -25, 20, -10, 16)
        ctx.fill()
        ctx.restore()

    def _draw_body(self, ctx: cairo.Context) -> None:
        # Pure procedural Cairo vector geometry
        ctx.set_source_rgb(0.96, 0.96, 0.98) # Pearl white fur
        ctx.arc(0, 0, 16.0, 0, 2 * math.pi)
        ctx.fill()

    def _draw_face(self, ctx: cairo.Context) -> None:
        # Expressive eyes
        ctx.set_source_rgb(0.1, 0.5, 0.9)
        ctx.arc(6, -2, 2.8, 0, 2 * math.pi)
        ctx.fill()
        # Specular shine
        ctx.set_source_rgb(1.0, 1.0, 1.0)
        ctx.arc(5.2, -3.0, 1.0, 0, 2 * math.pi)
        ctx.fill()

    def trigger_ability(self, ability_name: str, cx: float, cy: float, particles: Any, audio: Any) -> None:
        """Trigger interactive ability."""
        if ability_name == "spirit_flame":
            particles.shockwave(self.x, self.y, max_radius=70.0, color=(0.2, 0.6, 1.0))
            particles.burst_sparks(self.x, self.y, count=25, color=(0.5, 0.9, 1.0))
            audio.play("magic")
        elif ability_name == "teleport":
            particles.burst_stars(self.x, self.y, count=20, color=(0.4, 0.8, 1.0))
            self.x = cx
            self.y = cy
            audio.play("magic")
```

### Step 4: Register Companion in `skins/manager.py`
Open [`skins/manager.py`](file:///Users/tshrayansh/buddy%20for%20mac%20/skins/manager.py) and add the import to the registry dictionary:

```python
from skins.fox_spirit.character import FoxSpiritCharacter
from skins.fox_spirit.metadata import METADATA as FOX_SPIRIT_META

# Add to character factory registry
SKIN_CLASSES["fox_spirit"] = FoxSpiritCharacter
SKIN_METADATA["fox_spirit"] = FOX_SPIRIT_META
```

### Step 5: Test Your New Companion

#### On macOS:
```bash
# Launch directly with the new skin
buddy --skin fox_spirit

# Or test via python directly:
python3 buddy --skin fox_spirit
```

#### On Linux:
```bash
python3 buddy --skin fox_spirit
```

Your companion will immediately appear in:
1. The **Character Skin Gallery** (`buddy --skins` or via menu) under its declared category.
2. The **Menu Bar Status Item** / **Linux System Tray**.
3. The **Right-Click Context Menu**.
4. The CLI auto-completion (`buddy --list-skins`).

---

## Testing & Verification Matrix

| Area | macOS Command | Linux Command |
| :--- | :--- | :--- |
| **All Tests** | `pytest tests/` | `pytest tests/` |
| **Retina & Quartz CTM** | `pytest tests/test_macos_platform.py` | *(Skipped via `skipUnless`)* |
| **Kinematics & Physics** | `pytest tests/test_physics.py` | `pytest tests/test_physics.py` |
| **Skins Registry** | `pytest tests/test_skins.py` | `pytest tests/test_skins.py` |
| **Standalone Build** | `./scripts/build_macos_app.sh` | `./scripts/package_linux.sh` |
