"""Configuration management for Buddy Desktop Pet."""

import os
import json
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path.home() / ".config" / "buddy"
CONFIG_FILE = CONFIG_DIR / "config.json"
CACHE_DIR = Path.home() / ".cache" / "buddy"
USER_SKINS_DIR = CONFIG_DIR / "skins"

DEFAULT_CONFIG: Dict[str, Any] = {
    "skin": "thor",
    "fps": 60,
    "scale": 1.0,
    "speed": 1.0,
    "activity_level": 1.0,
    "sound_enabled": True,
    "sound_volume": 0.7,
    "click_through": False,
    "cursor_follow": True,
    "particles_enabled": True,
    "particle_limit": 300,
    "low_power_mode": False,
    "movement_area": "current_monitor",  # "current_monitor" or "all_monitors"
    "always_on_top": True,
    "debug_mode": False,
    "start_with_system": False,
    "favorite_skins": ["thor", "dragon", "cat", "dog", "ironman"],
    "screen_shake_enabled": True,
    "shortcuts": {
        "pause": "<Control><Shift>p",
        "skin_menu": "<Control><Shift>s",
        "settings": "<Control><Shift>c",
        "quit": "<Control><Shift>q"
    }
}


class Config:
    """Manages application settings with JSON persistence."""

    def __init__(self, config_file: Path = CONFIG_FILE):
        self.config_file = Path(config_file)
        self.data: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self.ensure_dirs()
        self.load()

    def ensure_dirs(self) -> None:
        """Ensure config, cache, and user skins directories exist."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            USER_SKINS_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            print(f"[Buddy Config] Warning: Could not create directories: {e}")

    def load(self) -> Dict[str, Any]:
        """Load configuration from file or fallback to defaults."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        # Merge loaded values over defaults
                        for k, v in loaded.items():
                            if k in self.data and isinstance(self.data[k], dict) and isinstance(v, dict):
                                self.data[k].update(v)
                            else:
                                self.data[k] = v
            except Exception as e:
                print(f"[Buddy Config] Error reading config file, using defaults: {e}")
        return self.data

    def save(self) -> bool:
        """Persist current settings to JSON file."""
        self.ensure_dirs()
        try:
            temp_file = self.config_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, sort_keys=True)
            temp_file.replace(self.config_file)
            return True
        except Exception as e:
            print(f"[Buddy Config] Error saving configuration: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a setting value."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """Set a setting value and optionally save to disk."""
        self.data[key] = value
        if auto_save:
            self.save()

    def reset_to_defaults(self) -> None:
        """Reset all configuration to factory defaults."""
        self.data = dict(DEFAULT_CONFIG)
        self.save()


# Global config instance for convenience
config = Config()
