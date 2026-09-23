"""Configuration management for Buddy Desktop Pet."""

import os
import json
from pathlib import Path
from typing import Any, Dict, Optional

import sys
from platforms import is_macos

if is_macos():
    CONFIG_DIR = Path.home() / "Library" / "Application Support" / "Buddy"
    CONFIG_FILE = CONFIG_DIR / "config.json"
    CACHE_DIR = Path.home() / "Library" / "Caches" / "Buddy"
    USER_SKINS_DIR = CONFIG_DIR / "skins"
    # Migration helper: If user previously ran Linux configuration on Mac
    _legacy_cfg = Path.home() / ".config" / "buddy" / "config.json"
    if _legacy_cfg.exists() and not CONFIG_FILE.exists():
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.copy2(str(_legacy_cfg), str(CONFIG_FILE))
        except Exception:
            pass
else:
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
    "companion_mode": "static",  # "static" (Desk Pet / Stay Where Dropped), "roam" (Free Roam), "follow" (Cursor Companion)
    "particles_enabled": True,
    "particle_limit": 300,
    "low_power_mode": False,
    "movement_area": "current_monitor",  # "current_monitor" or "all_monitors"
    "always_on_top": True,
    "debug_mode": False,
    "developer_mode": False,
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

    def __init__(self, config_file: Optional[Path] = None, profile: Optional[str] = None):
        if config_file:
            self.config_file = Path(config_file)
        elif profile:
            self.config_file = CONFIG_DIR / f"config_{profile}.json"
        else:
            self.config_file = CONFIG_FILE
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
                raw = self.config_file.read_text(encoding="utf-8")
                if not raw.strip():
                    print("[Buddy Config] Warning: Config file is empty, using defaults.")
                    return self.data
                loaded = json.loads(raw)
                if not isinstance(loaded, dict):
                    raise ValueError(f"Expected dict at top level, got {type(loaded).__name__}")
                # Merge loaded values over defaults
                for k, v in loaded.items():
                    if k in self.data and isinstance(self.data[k], dict) and isinstance(v, dict):
                        self.data[k].update(v)
                    else:
                        self.data[k] = v
            except (json.JSONDecodeError, ValueError) as e:
                print(f"[Buddy Config] Error: Corrupt config file ({e}), backing up and using defaults.")
                try:
                    backup = self.config_file.with_suffix(".json.bak")
                    self.config_file.rename(backup)
                    print(f"[Buddy Config] Corrupt config backed up to: {backup}")
                except OSError:
                    pass
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
ConfigManager = Config
