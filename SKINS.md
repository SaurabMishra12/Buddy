# 🎨 Creating Custom Skins for Buddy

Buddy features a modular, data-driven skin architecture. You can add new characters without modifying the core engine code.

---

## 📁 Skin Directory Structure

User-defined skins live in `~/.config/buddy/skins/<skin_id>/`:

```text
~/.config/buddy/skins/
    my_character/
        skin.json
        character.py        (optional custom vector / logic)
        sprites/            (optional PNG frames)
            idle_01.png
            walk_01.png
        sounds/             (optional custom sound effects)
            action.wav
```

---

## 📄 `skin.json` Specification

Example `skin.json`:

```json
{
  "id": "my_hero",
  "name": "My Hero",
  "title": "Cosmic Defender",
  "description": "A custom hero companion with laser vision and hover flight.",
  "speed": 1.2,
  "canFly": true,
  "abilities": [
    "laser_blast",
    "speed_dash",
    "flight"
  ],
  "sound_theme": "laser"
}
```

### Supported Metadata Fields:
* `id` *(string, required)*: Unique slug (lowercase, no spaces).
* `name` *(string, required)*: Human-readable display name.
* `title` *(string)*: Character subtitle/epithet.
* `description` *(string)*: Short description shown in the Skin Selector.
* `speed` *(float)*: Speed multiplier (1.0 is standard).
* `canFly` *(boolean)*: Whether the character flies or stays on the ground.
* `abilities` *(list of strings)*: Names of special abilities.
* `sound_theme` *(string)*: Audio profile name.

---

## 💻 Writing a Character Class in Python

To provide custom physics or rendering, create `character.py` inside your skin directory:

```python
from skins.base import BaseCharacter, CharacterState
from skins.manager import skin_manager
import cairo

class MyHero(BaseCharacter):
    def __init__(self, x=500.0, y=400.0):
        super().__init__(x, y, skin_id="my_hero")
        self.can_fly = True

    def trigger_ability(self, ability_name, target_x, target_y, particle_mgr, audio_mgr):
        if ability_name == "laser_blast":
            particle_mgr.arc_connect(self.x, self.y, target_x, target_y)
            audio_mgr.play("laser")
            return True
        return False

    def update(self, dt, cursor_x, cursor_y, screen_bounds, particle_mgr, audio_mgr, config_data):
        # Update motion towards cursor
        self.x += (cursor_x - self.x) * 0.04
        self.y += (cursor_y - self.y) * 0.04

    def draw(self, ctx: cairo.Context, particle_mgr):
        ctx.save()
        ctx.translate(self.x, self.y)
        # Draw custom shape using Cairo
        ctx.set_source_rgb(0.2, 0.6, 1.0)
        ctx.arc(0, 0, 16, 0, 6.28)
        ctx.fill()
        ctx.restore()

# Register automatically
skin_manager.register("my_hero", MyHero)
```
