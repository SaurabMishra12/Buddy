"""Skin manager: loads, registers, validates, and instantiates character skins."""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Type
from skins.base import BaseCharacter

SKINS_DIR = Path(__file__).parent
USER_SKINS_DIR = Path.home() / ".config" / "buddy" / "skins"


class SkinManager:
    """Discovers, validates, and registers modular character skins."""

    def __init__(self):
        self._registry: Dict[str, Type[BaseCharacter]] = {}
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._discover_and_register_all()

    def register(self, skin_id: str, character_cls: Type[BaseCharacter], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Register a character class with its metadata."""
        self._registry[skin_id] = character_cls
        if metadata:
            self._metadata_cache[skin_id] = metadata

    def _discover_and_register_all(self) -> None:
        """Dynamically load built-in skin modules."""
        # Built-in skin definitions
        skin_defs = [
            ("thor", "Thor", "Norse God of Thunder wielding Mjolnir with fractal lightning.", ["hammer_throw", "lightning", "flight", "hammer_spin"]),
            ("dragon", "Dragon", "Fantasy winged dragon breathing fire and soaring the desktop.", ["fire_breath", "fireball", "flight", "glide"]),
            ("cat", "Cat", "Playful feline friend that chases cursors, grooms, and curls up.", ["chase", "pounce", "groom", "nap"]),
            ("dog", "Dog", "Enthusiastic puppy that wags its tail, barks, and fetches cursors.", ["bark", "dig", "fetch", "wag"]),
            ("hulk", "Hulk", "Green colossus with ground-shattering smashes and shockwaves.", ["hulk_smash", "super_jump", "roar"]),
            ("ironman", "Iron Man", "Armored hero with boot thrusters, repulsors, and air dash.", ["repulsor_blast", "flight", "air_dash"]),
            ("harry_potter", "Harry Potter", "Wizard casting spells, summoning spark trails, and flying a broom.", ["cast_spell", "broom_flight", "teleport"]),
            ("captain_america", "Captain America", "Super soldier throwing and bouncing his Vibranium Shield.", ["shield_throw", "shield_block", "hero_pose"]),
            ("thanos", "Thanos", "Titan wielding the 6 Infinity Stones with cosmic energy bursts.", ["time_stone", "space_teleport", "power_blast", "the_snap"]),
            ("batman", "Batman", "Dark Knight grappling, cape gliding, and throwing batarangs.", ["grapple", "cape_glide", "batarang", "perch"]),
            ("superman", "Superman", "Man of Steel flying at supersonic speed with laser heat vision.", ["heat_vision", "supersonic_flight", "super_jump"])
        ]

        for skin_id, name, desc, abilities in skin_defs:
            meta_path = SKINS_DIR / skin_id / "skin.json"
            meta = {
                "id": skin_id,
                "name": name,
                "description": desc,
                "speed": 1.0,
                "canFly": "flight" in abilities or "glide" in abilities,
                "abilities": abilities,
                "category": "superhero" if skin_id in ["thor", "hulk", "ironman", "captain_america", "batman", "superman", "thanos"] else ("pet" if skin_id in ["cat", "dog"] else "fantasy")
            }
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        meta.update(loaded)
                except Exception:
                    pass
            self._metadata_cache[skin_id] = meta

    @staticmethod
    def normalize_skin_id(skin_id: str) -> str:
        """Normalize skin name to canonical lowercase ID."""
        if not skin_id:
            return "thor"
        raw = str(skin_id).lower().strip().replace("-", "_").replace(" ", "_")
        aliases = {
            "iron_man": "ironman",
            "super_man": "superman",
            "captainamerica": "captain_america",
            "harrypotter": "harry_potter",
            "harry": "harry_potter",
            "potter": "harry_potter",
            "cap": "captain_america"
        }
        return aliases.get(raw, raw)

    def get_available_skins(self) -> List[Dict[str, Any]]:
        """Return list of all registered skins metadata."""
        return list(self._metadata_cache.values())

    def get_metadata(self, skin_id: str) -> Optional[Dict[str, Any]]:
        """Return metadata for specific skin ID with case-insensitive normalization."""
        norm_id = self.normalize_skin_id(skin_id)
        return self._metadata_cache.get(norm_id)

    def create_character(self, skin_id: str, x: float = 500.0, y: float = 400.0) -> BaseCharacter:
        """Instantiate character for specified skin ID with fallback to Thor if missing."""
        norm_id = self.normalize_skin_id(skin_id)
        target_id = norm_id if norm_id in self._registry else "thor"
        cls = self._registry.get(target_id)
        if not cls:
            # Fallback import of thor character if registry not populated yet
            from skins.thor.character import ThorCharacter
            return ThorCharacter(x, y)
        return cls(x, y)


skin_manager = SkinManager()
