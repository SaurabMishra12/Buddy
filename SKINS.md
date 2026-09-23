# Creating Custom Skins for Buddy 2.0

Buddy features a modular, data-driven skin architecture. You can add new characters without modifying the core engine code.

---

## Skin Directory Structure

User-defined skins live in `~/.config/buddy/skins/<skin_id>/`:

```text
~/.config/buddy/skins/
    my_character/
        skin.json
        character.py        (optional custom vector / logic)
        sprites/            (optional PNG frames)
        sounds/             (optional custom sound effects)
```

---

## `skin.json` Specification (Buddy 2.0 Schema)

Example `skin.json`:

```json
{
  "id": "my_hero",
  "name": "My Hero",
  "category": "heroes",
  "description": "A custom hero companion with laser vision and hover flight.",
  "speed": 1.2,
  "canFly": true,
  "personality": {
    "energy": 0.85,
    "curiosity": 0.70,
    "playfulness": 0.60,
    "sleepiness": 0.20,
    "interaction_rate": 0.75
  },
  "abilities": [
    "laser_blast",
    "speed_dash",
    "flight"
  ],
  "sounds": {
    "action": "laser.wav"
  },
  "pomodoro": {
    "work": "meditate",
    "break": "victory_dance",
    "celebrate": "fireworks"
  }
}
```

### Supported Metadata Fields:
* `id` *(string, required)*: Unique slug (lowercase, no spaces).
* `name` *(string, required)*: Human-readable display name.
* `category` *(string)*: One of `"heroes"`, `"animals"`, `"fantasy"`, `"sci-fi"`, `"cute"`, or `"custom"`.
* `description` *(string)*: Short description shown in the Skin Gallery.
* `speed` *(float)*: Speed multiplier (1.0 is standard).
* `canFly` *(boolean)*: Whether the character flies or walks on the ground.
* `personality` *(object)*:
  - `energy` *(0.0 - 1.0)*: How frequently the character moves or sprints.
  - `curiosity` *(0.0 - 1.0)*: How strongly the character approaches and inspects cursor movement.
  - `playfulness` *(0.0 - 1.0)*: Likelihood of performing tricks, games, or jumps.
  - `sleepiness` *(0.0 - 1.0)*: Tendency to idle or take naps when the desktop is quiet.
* `abilities` *(list of strings)*: Names of special abilities.
* `sounds` *(object)*: Key-value mapping of action to audio files.
* `pomodoro` *(object)*:
  - `work`: Character state/behavior during focus sessions.
  - `break`: Character state/behavior during breaks.
  - `celebrate`: Action upon completing a focus milestone.

---

## Writing a Character Class in Python

To provide custom physics or rendering, create `character.py` inside your skin directory:

```python
import math
import cairo
from typing import Tuple, Dict, Any
from skins.base import BaseCharacter, CharacterState
from behavior.personality import CharacterPersonality
from behavior.memory import CharacterMemory
from behavior.state_machine import CharacterBehavior, BehaviorState

class MyHero(BaseCharacter):
    def __init__(self, x: float = 500.0, y: float = 400.0):
        super().__init__(x, y, skin_id="my_hero")
        self.can_fly = True
        self.personality = CharacterPersonality(energy=0.85, curiosity=0.7, playfulness=0.6, sleepiness=0.2)
        self.memory = CharacterMemory(skin_id="my_hero")
        self.behavior = CharacterBehavior("MyHero", personality=self.personality, memory=self.memory, can_fly=True)

    def trigger_ability(self, ability_name: str, target_x: float, target_y: float, particle_mgr: Any, audio_mgr: Any) -> bool:
        if ability_name == "laser_blast":
            particle_mgr.arc_connect(self.x, self.y, target_x, target_y)
            audio_mgr.play("laser")
            self.memory.record_interaction("laser_blast")
            return True
        return False

    def update(self, dt: float, cursor_x: float, cursor_y: float, screen_bounds: Tuple[int, int, int, int], particle_mgr: Any, audio_mgr: Any, config_data: Dict[str, Any]) -> None:
        self.behavior.evaluate_next_action(
            dt=dt,
            char_x=self.x,
            char_y=self.y,
            cursor_x=cursor_x,
            cursor_y=cursor_y,
            cursor_speed=0.0,
            screen_bounds=screen_bounds,
            pomodoro_state=config_data.get("pomodoro_state", "IDLE")
        )
        self.state = self.behavior.current_state

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        ctx.save()
        ctx.translate(self.x, self.y)
        ctx.set_source_rgb(0.2, 0.6, 1.0)
        ctx.arc(0, 0, 18, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()
```
