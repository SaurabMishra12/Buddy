"""Lightweight local character memory system for Buddy companions."""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

MEMORY_DIR = Path.home() / ".config" / "buddy" / "memory"


class CharacterMemory:
    """Tracks historical interaction, favorite positions, and shared moments with the user."""

    def __init__(self, skin_id: str, memory_dir: Optional[Path] = None, enabled: bool = True):
        self.skin_id = skin_id
        self.memory_dir = Path(memory_dir) if memory_dir else MEMORY_DIR
        self.enabled = enabled
        self.file_path = self.memory_dir / f"{self.skin_id}.json"

        # Defaults
        self.interactions_count: int = 0
        self.total_active_seconds: float = 0.0
        self.last_interaction_time: float = 0.0
        self.favorite_pos: Tuple[float, float] = (500.0, 400.0)
        self.pomodoro_sessions_completed: int = 0
        self.last_special_ability: str = ""
        self.mood_affinity: float = 0.5  # 0.0 (unfamiliar) to 1.0 (best friend)

        self._load()

    def _ensure_dir(self) -> None:
        if self.enabled:
            try:
                self.memory_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass

    def _load(self) -> None:
        if not self.enabled or not self.file_path.exists():
            return
        try:
            raw = self.file_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                self.interactions_count = int(data.get("interactions_count", 0))
                self.total_active_seconds = float(data.get("total_active_seconds", 0.0))
                self.last_interaction_time = float(data.get("last_interaction_time", 0.0))
                pos = data.get("favorite_pos", [500.0, 400.0])
                if isinstance(pos, (list, tuple)) and len(pos) == 2:
                    self.favorite_pos = (float(pos[0]), float(pos[1]))
                self.pomodoro_sessions_completed = int(data.get("pomodoro_sessions_completed", 0))
                self.last_special_ability = str(data.get("last_special_ability", ""))
                self.mood_affinity = float(data.get("mood_affinity", 0.5))
        except Exception as e:
            print(f"[Buddy Memory] Warning reading memory for {self.skin_id}: {e}")

    def save(self) -> bool:
        if not self.enabled:
            return False
        self._ensure_dir()
        try:
            data = {
                "skin_id": self.skin_id,
                "interactions_count": self.interactions_count,
                "total_active_seconds": round(self.total_active_seconds, 1),
                "last_interaction_time": self.last_interaction_time,
                "favorite_pos": list(self.favorite_pos),
                "pomodoro_sessions_completed": self.pomodoro_sessions_completed,
                "last_special_ability": self.last_special_ability,
                "mood_affinity": round(self.mood_affinity, 2),
                "updated_at": time.time(),
            }
            tmp = self.file_path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            tmp.replace(self.file_path)
            return True
        except Exception as e:
            print(f"[Buddy Memory] Error saving memory for {self.skin_id}: {e}")
            return False

    def record_interaction(self, ability_name: str = "") -> None:
        """Call when user clicks, pets, or triggers abilities."""
        self.interactions_count += 1
        self.last_interaction_time = time.time()
        if ability_name:
            self.last_special_ability = ability_name
        self.mood_affinity = min(1.0, self.mood_affinity + 0.02)

    def record_time(self, dt: float, current_x: float, current_y: float) -> None:
        """Accrue active companion time and slowly update favorite screen position."""
        self.total_active_seconds += dt
        # Exponential moving average for favorite resting spot
        fx, fy = self.favorite_pos
        self.favorite_pos = (fx * 0.999 + current_x * 0.001, fy * 0.999 + current_y * 0.001)

    def record_pomodoro_completed(self) -> None:
        """Call when a focus work session is successfully finished."""
        self.pomodoro_sessions_completed += 1
        self.mood_affinity = min(1.0, self.mood_affinity + 0.05)

    def reset(self) -> None:
        """Clear memory for this companion."""
        self.interactions_count = 0
        self.total_active_seconds = 0.0
        self.last_interaction_time = 0.0
        self.pomodoro_sessions_completed = 0
        self.last_special_ability = ""
        self.mood_affinity = 0.5
        if self.file_path.exists():
            try:
                self.file_path.unlink()
            except OSError:
                pass
