"""
Buddy User Profile and Preference Migration Engine.

Supports preset and custom user profiles:
- Default
- Focus Mode
- Gaming Mode
- Anime Chaos
- Minimal

Handles schema versioning and profile import/export.
"""

from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import CONFIG_DIR


CURRENT_SCHEMA_VERSION = 2


@dataclass
class BuddyProfile:
    id: str
    name: str
    character: str = "ichigo"
    scale: float = 1.0
    behavior_mode: str = "static_roam"     # static_roam, free_roam, draggable, follow_mouse, perch
    autonomous_mode: str = "occasional"   # manual, occasional, active, chaos
    perching_mode: str = "safe"           # off, safe, free
    sound_enabled: bool = True
    sound_volume: float = 0.7
    ghost_mode: bool = False
    particles_enabled: bool = True
    favorite_abilities: List[str] = field(default_factory=list)
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    schema_version: int = CURRENT_SCHEMA_VERSION


BUILTIN_PROFILES: Dict[str, BuddyProfile] = {
    "default": BuddyProfile(
        id="default",
        name="Default",
        character="ichigo",
        scale=1.0,
        behavior_mode="static_roam",
        autonomous_mode="occasional",
        perching_mode="safe",
        sound_enabled=True,
        sound_volume=0.7,
        ghost_mode=False,
        particles_enabled=True,
    ),
    "focus_mode": BuddyProfile(
        id="focus_mode",
        name="Focus Mode",
        character="byakuya",
        scale=0.85,
        behavior_mode="draggable",
        autonomous_mode="manual",
        perching_mode="off",
        sound_enabled=False,
        sound_volume=0.0,
        ghost_mode=True,
        particles_enabled=False,
    ),
    "gaming_mode": BuddyProfile(
        id="gaming_mode",
        name="Gaming Mode",
        character="cat",
        scale=0.75,
        behavior_mode="draggable",
        autonomous_mode="manual",
        perching_mode="off",
        sound_enabled=False,
        sound_volume=0.0,
        ghost_mode=True,
        particles_enabled=False,
    ),
    "anime_chaos": BuddyProfile(
        id="anime_chaos",
        name="Anime Chaos",
        character="kenpachi",
        scale=1.2,
        behavior_mode="free_roam",
        autonomous_mode="chaos",
        perching_mode="free",
        sound_enabled=True,
        sound_volume=0.9,
        ghost_mode=False,
        particles_enabled=True,
    ),
    "minimal": BuddyProfile(
        id="minimal",
        name="Minimal",
        character="slime",
        scale=0.7,
        behavior_mode="static_roam",
        autonomous_mode="occasional",
        perching_mode="off",
        sound_enabled=False,
        sound_volume=0.0,
        ghost_mode=False,
        particles_enabled=False,
    ),
}


class ProfileManager:
    """Manages active and saved Buddy profiles with schema migration."""

    def __init__(self, profiles_dir: Optional[Path] = None):
        self.profiles_dir = profiles_dir or (CONFIG_DIR / "profiles")
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self.profiles: Dict[str, BuddyProfile] = dict(BUILTIN_PROFILES)
        self.active_profile_id: str = "default"
        self._load_saved_profiles()

    @property
    def active_profile(self) -> BuddyProfile:
        return self.profiles.get(self.active_profile_id, BUILTIN_PROFILES["default"])

    def set_active_profile(self, profile_id: str) -> bool:
        if profile_id in self.profiles:
            self.active_profile_id = profile_id
            return True
        return False

    def save_profile(self, profile: BuddyProfile) -> bool:
        self.profiles[profile.id] = profile
        try:
            target = self.profiles_dir / f"{profile.id}.json"
            target.write_text(json.dumps(asdict(profile), indent=2), encoding="utf-8")
            return True
        except Exception as e:
            print(f"[Buddy Profile] Error saving profile {profile.id}: {e}")
            return False

    def export_profile_json(self, profile_id: str) -> Optional[str]:
        prof = self.profiles.get(profile_id)
        if prof:
            return json.dumps(asdict(prof), indent=2)
        return None

    def import_profile_json(self, raw_json: str) -> Optional[BuddyProfile]:
        try:
            data = json.loads(raw_json)
            migrated = self._migrate_schema(data)
            prof = BuddyProfile(**migrated)
            self.save_profile(prof)
            return prof
        except Exception as e:
            print(f"[Buddy Profile] Failed importing profile: {e}")
            return None

    def _migrate_schema(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Upgrades legacy schemas to CURRENT_SCHEMA_VERSION."""
        version = data.get("schema_version", 1)
        if version < 2:
            # v1 migration: Ensure perching_mode and autonomous_mode exist
            if "perching_mode" not in data:
                data["perching_mode"] = "safe"
            if "autonomous_mode" not in data:
                data["autonomous_mode"] = "occasional"
            data["schema_version"] = 2
        return data

    def _load_saved_profiles(self) -> None:
        if not self.profiles_dir.exists():
            return
        for file in self.profiles_dir.glob("*.json"):
            try:
                raw = file.read_text(encoding="utf-8")
                data = json.loads(raw)
                migrated = self._migrate_schema(data)
                prof = BuddyProfile(**migrated)
                self.profiles[prof.id] = prof
            except Exception as e:
                print(f"[Buddy Profile] Failed to read {file}: {e}")
