# 🛠️ Buddy Developer Guide & Architecture

This document describes the internal architecture of **Buddy** and how to contribute, debug, and extend the engine.

---

## 🏛️ System Architecture

Buddy is architected into modular sub-engines:

```text
Buddy Desktop Pet Engine
│
├── core/
│   ├── engine.py       # Main simulation loop, layer rendering, FPS pacing, HUD
│   ├── window.py       # RGBA overlay window, X11/XWayland input shape transparency
│   ├── physics.py      # 2D physics equations: velocity, gravity, drag, bounce, screen bounds
│   ├── particles.py    # Spark, flame, smoke, shockwave, and lightning bolt manager
│   ├── audio.py        # Non-blocking sound triggers (pw-play / paplay / aplay / canberra)
│   ├── config.py       # Configuration schema and ~/.config/buddy/config.json persistence
│   └── tray.py         # AppIndicator3 system tray menu
│
├── skins/
│   ├── base.py         # BaseCharacter & BaseProjectile interfaces
│   ├── manager.py      # Skin registry, validation, and factory loader
│   ├── thor/           # Preserved Thor, cloth cape simulation, Mjolnir projectile
│   ├── dragon/         # Wing flapping, fire breath cone, fireball projectiles
│   ├── cat/            # Ground movement, pouncing, grooming, sleep states
│   ├── dog/            # Playful bouncing, tail wagging, barking, digging
│   ├── hulk/           # Ground smashes, shockwaves, screen shake, roar rage
│   ├── ironman/        # Jet thrusters, repulsor blast, supersonic air dash
│   ├── harry_potter/   # Wand spell sparks, broom flight, smoke teleportation
│   ├── captain_america/# Vibranium Shield throw/ricochet/return physics, block guard
│   ├── thanos/         # Infinity Gauntlet with 6 Stone abilities and The Snap
│   ├── batman/         # Grappling hook physics, cape gliding, batarangs
│   └── superman/       # Supersonic flight, twin eye laser heat vision
│
└── ui/
    ├── skin_selector.py   # Visual character picker gallery
    ├── settings_dialog.py # Full preferences and system startup dialog
    └── context_menu.py    # Right-click context menu
```

---

## 🔬 Physics & Simulation Loop

1. **Input Polling**: Queries the root pointer position from the GDK default seat at each frame interval (16.6ms for 60 FPS).
2. **Physics Integration**:
   - Acceleration towards cursor:
     $$v_{next} = (v + a \cdot \Delta t) \times \mu$$
   - Boundary constraints clamp or bounce with coefficient of restitution.
3. **Particle Updates**:
   - All sparks, flames, smoke, and shockwaves step forward; dead particles ($\text{life} \le 0$) are pruned.
   - Global particle ceiling prevents memory growth.
4. **Window Draw Event**:
   - `cairo.OPERATOR_CLEAR` wipes previous frame.
   - `cairo.OPERATOR_OVER` renders background effects $\to$ character $\to$ projectiles $\to$ foreground particles.

---

## 🔍 Developer HUD Mode

Launch Buddy with the `--debug` flag to enable the real-time diagnostics HUD:

```bash
buddy --debug
```

The HUD displays:
* Current active Skin ID
* State machine state (`IDLE`, `WALK`, `FLY`, `HOVER`, `SUMMONING`, `JUMP`, etc.)
* Position and Velocity vectors
* Target cursor coordinates
* Real-time FPS vs Target FPS
* Active particle count

---

## 🧪 Running Unit Tests

Run the full test suite anytime during development:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```
