# Buddy 2.0 Developer Guide & Architecture

This document describes the internal architecture of **Buddy 2.0** and how to contribute, debug, and extend the engine.
For detailed instructions on creating new characters and understanding the cross-platform rendering pipeline, see [**`ARCHITECTURE.md`**](ARCHITECTURE.md).

---

## System Architecture

Buddy is architected into modular sub-engines:

```text
Buddy Desktop Platform Engine
│
├── core/
│   ├── engine.py       # Main simulation loop, layer rendering, FPS pacing, HUD, Pomodoro integration
│   ├── window.py       # RGBA overlay window, X11/XWayland input shape transparency
│   ├── physics.py      # 2D physics equations: velocity, gravity, drag, bounce, screen bounds
│   ├── particles.py    # Spark, flame, smoke, shockwave, heart, star, confetti, dust, energy orbs
│   ├── audio.py        # Non-blocking sound triggers (pw-play / paplay / aplay / canberra)
│   ├── config.py       # Configuration schema and ~/.config/buddy/config.json persistence
│   └── tray.py         # AppIndicator3 system tray menu
│
├── platforms/
│   ├── __init__.py     # Platform detection (is_macos, is_linux, get_platform_name)
│   ├── base.py         # Abstract contracts (PlatformWindow, PlatformTray, PlatformAudio, PlatformAutostart)
│   ├── linux/          # Native Linux GTK3, GDK, AppIndicator3, XDG desktop implementation
│   └── macos/          # Native macOS AppKit, PyObjC, Quartz, NSSound, LaunchAgent implementation
│
├── behavior/
│   ├── personality.py  # CharacterPersonality profile (energy, curiosity, playfulness, sleepiness)
│   ├── state_machine.py# CharacterBehavior autonomous state machine (Focus, Break, Walk, Play, Idle)
│   └── memory.py       # Local character memory (~/.config/buddy/memory/{skin_id}.json)
│
├── pomodoro/
│   ├── manager.py      # PomodoroManager state machine (work, short break, long break, countdown)
│   ├── statistics.py   # PomodoroStats daily/weekly/streak metrics (~/.config/buddy/pomodoro_stats.json)
│   └── notifications.py# Desktop notification dispatcher (DBus / notify-send / AppleScript)
│
├── rendering/
│   └── animation.py    # Easing primitives: bounce, elastic, ease_in, ease_out, spring_step
│
├── skins/
│   ├── base.py         # BaseCharacter & BaseProjectile interfaces
│   ├── manager.py      # Skin registry, validation, and factory loader
│   ├── thor/           # Preserved Thor, cloth cape simulation, Mjolnir projectile
│   ├── dragon/         # Procedural Dreadwyrm, wing flapping, fire breath cone
│   ├── cat/            # Ground movement, pouncing, grooming, sleep states
│   ├── dog/            # Playful bouncing, tail wagging, barking, digging
│   ├── hulk/           # Ground smashes, shockwaves, screen shake, roar rage
│   ├── ironman/        # Jet thrusters, unibeam reactor repulsor, flight kinematics
│   ├── harry_potter/   # Wand spell sparks, broom flight, smoke teleportation
│   ├── captain_america/# Vibranium Shield throw/ricochet/return physics, block guard
│   ├── thanos/         # Infinity Gauntlet with 6 Stone abilities and The Snap
│   ├── batman/         # Grappling hook physics, cape gliding, batarangs
│   ├── superman/       # Supersonic flight, speed trails, twin eye laser heat vision
│   ├── spiderman/      # Acrobatic web-swinging rope, web throws, upside-down perch
│   ├── pixel_wizard/   # Magic arcane orbs, spatial teleportation, runic circles
│   ├── space_robot/    # Cybernetic droid, laser scanning beam, holographic display
│   ├── ninja/          # Smoke bomb vanishing, shuriken throwing, wall leaps
│   ├── vampire/        # Crimson cape levitation, bat swarm summons, shadow mist
│   ├── fairy/          # Gossamer wings, sparkle trails, stardust healing radiance
│   ├── alien/          # UFO tractor beams, anti-gravity pulses, warp teleports
│   ├── ghost/          # Ethereal floating, phase shift fade, friendly spooks
│   ├── penguin/        # Cheerful Antarctic penguin, belly slide, snowball tosses
│   ├── fox/            # Red fox swift sprints, bushy tail wags, playful pounces
│   └── slime/          # Bouncy jelly creature, squash-and-stretch bounce, bubbly splits
│
└── ui/
    ├── skin_selector.py   # Visual character gallery with categories, search, personality metrics
    ├── settings_dialog.py # 6-tab preferences dialog (General, Behavior, Appearance, Pomodoro, Performance, A11y)
    ├── stats_dialog.py    # Productivity & focus sprint statistics dashboard
    └── context_menu.py    # Right-click context menu with Pomodoro controls and companion modes
```

---

## Physics & Simulation Loop

1. **Input Polling**: Queries the root pointer position from native windowing system (AppKit on macOS, GDK default seat on Linux) at each frame interval (16.6ms for 60 FPS).
2. **Pomodoro Synchronization**:
   - Updates countdown timer on every tick (`self.pomodoro.tick(dt)`).
   - Injects Pomodoro state (`WORK`, `SHORT_BREAK`, `LONG_BREAK`, `PAUSED`) into character behavior engine.
3. **Autonomous Behavior Selection**:
   - `CharacterBehavior.evaluate_next_action` evaluates cursor distance, idle duration, and personality disposition to choose state transitions.
4. **Particle Updates**:
   - Advances sparks, flames, smoke, shockwaves, stars, hearts, confetti, dust, and energy orbs.
   - Enforces configurable particle ceilings to prevent runaway CPU or memory usage.
5. **Window Draw Event**:
   - `cairo.OPERATOR_CLEAR` wipes previous frame for transparent background.
   - `cairo.OPERATOR_OVER` renders character, projectiles, and particle effects.
   - On macOS: in-memory zero-copy buffer transfer to CGImage (`~0.060 ms/frame`).
   - Optionally renders the floating Pomodoro pill badge and developer telemetry HUD.

---

## Developer HUD Mode

Launch Buddy with the `--debug` flag to enable the real-time diagnostics HUD:

```bash
buddy --debug
```

The HUD displays:
* Active Skin ID & Target FPS
* Active particle count
* State machine state (`IDLE`, `WALK`, `RUN`, `FLY`, `HOVER`, `FOCUS`, `BREAK`, etc.)
* Live Pomodoro status and countdown timer

---

## Running Unit Tests

Run the full automated test suite anytime during development:

```bash
# Using pytest (Recommended)
pytest -v tests/

# Using unittest runner
python3 -m unittest discover -s tests -p "test_*.py" -v
```

### Running macOS Platform-Specific Tests

```bash
pytest -v tests/test_macos_platform.py tests/test_macos_integration_and_stress.py
```

### Building Standalone App Bundle

```bash
./scripts/build_macos_app.sh
```
