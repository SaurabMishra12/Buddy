"""Skin manager: loads, registers, validates, and instantiates character skins."""

import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Type, Tuple
from skins.base import BaseCharacter

SKINS_DIR = Path(__file__).parent
USER_SKINS_DIR = Path.home() / ".config" / "buddy" / "skins"


BUILTIN_SKINS: Dict[str, Tuple[str, str]] = {
    "thor": ("skins.thor.character", "ThorCharacter"),
    "dragon": ("skins.dragon.character", "DragonCharacter"),
    "cat": ("skins.cat.character", "CatCharacter"),
    "dog": ("skins.dog.character", "DogCharacter"),
    "hulk": ("skins.hulk.character", "HulkCharacter"),
    "ironman": ("skins.ironman.character", "IronManCharacter"),
    "harry_potter": ("skins.harry_potter.character", "HarryPotterCharacter"),
    "captain_america": ("skins.captain_america.character", "CaptainAmericaCharacter"),
    "thanos": ("skins.thanos.character", "ThanosCharacter"),
    "batman": ("skins.batman.character", "BatmanCharacter"),
    "superman": ("skins.superman.character", "SupermanCharacter"),
    "spiderman": ("skins.spiderman.character", "SpiderManCharacter"),
    "pixel_wizard": ("skins.pixel_wizard.character", "PixelWizardCharacter"),
    "space_robot": ("skins.space_robot.character", "SpaceRobotCharacter"),
    "ninja": ("skins.ninja.character", "NinjaCharacter"),
    "vampire": ("skins.vampire.character", "VampireCharacter"),
    "fairy": ("skins.fairy.character", "FairyCharacter"),
    "alien": ("skins.alien.character", "AlienCharacter"),
    "ghost": ("skins.ghost.character", "GhostCharacter"),
    "penguin": ("skins.penguin.character", "PenguinCharacter"),
    "fox": ("skins.fox.character", "FoxCharacter"),
    "slime": ("skins.slime.character", "SlimeCharacter"),
    # Bleach Soul Reapers
    "ichigo": ("skins.ichigo.character", "IchigoCharacter"),
    "byakuya": ("skins.byakuya.character", "ByakuyaCharacter"),
    "yamamoto": ("skins.yamamoto.character", "YamamotoCharacter"),
    "kenpachi": ("skins.kenpachi.character", "KenpachiCharacter"),
    "hitsugaya": ("skins.hitsugaya.character", "HitsugayaCharacter"),
    "rukia": ("skins.rukia.character", "RukiaCharacter"),
    "urahara": ("skins.urahara.character", "UraharaCharacter"),
}


def _get_builtin_classes() -> Dict[str, Type[BaseCharacter]]:
    """Statically import and map all 29 character classes for reliable execution and PyInstaller bundling."""
    from skins.thor.character import ThorCharacter
    from skins.dragon.character import DragonCharacter
    from skins.cat.character import CatCharacter
    from skins.dog.character import DogCharacter
    from skins.hulk.character import HulkCharacter
    from skins.ironman.character import IronManCharacter
    from skins.harry_potter.character import HarryPotterCharacter
    from skins.captain_america.character import CaptainAmericaCharacter
    from skins.thanos.character import ThanosCharacter
    from skins.batman.character import BatmanCharacter
    from skins.superman.character import SupermanCharacter
    from skins.spiderman.character import SpiderManCharacter
    from skins.pixel_wizard.character import PixelWizardCharacter
    from skins.space_robot.character import SpaceRobotCharacter
    from skins.ninja.character import NinjaCharacter
    from skins.vampire.character import VampireCharacter
    from skins.fairy.character import FairyCharacter
    from skins.alien.character import AlienCharacter
    from skins.ghost.character import GhostCharacter
    from skins.penguin.character import PenguinCharacter
    from skins.fox.character import FoxCharacter
    from skins.slime.character import SlimeCharacter
    # Bleach Soul Reapers
    from skins.ichigo.character import IchigoCharacter
    from skins.byakuya.character import ByakuyaCharacter
    from skins.yamamoto.character import YamamotoCharacter
    from skins.kenpachi.character import KenpachiCharacter
    from skins.hitsugaya.character import HitsugayaCharacter
    from skins.rukia.character import RukiaCharacter
    from skins.urahara.character import UraharaCharacter

    return {
        "thor": ThorCharacter,
        "dragon": DragonCharacter,
        "cat": CatCharacter,
        "dog": DogCharacter,
        "hulk": HulkCharacter,
        "ironman": IronManCharacter,
        "harry_potter": HarryPotterCharacter,
        "captain_america": CaptainAmericaCharacter,
        "thanos": ThanosCharacter,
        "batman": BatmanCharacter,
        "superman": SupermanCharacter,
        "spiderman": SpiderManCharacter,
        "pixel_wizard": PixelWizardCharacter,
        "space_robot": SpaceRobotCharacter,
        "ninja": NinjaCharacter,
        "vampire": VampireCharacter,
        "fairy": FairyCharacter,
        "alien": AlienCharacter,
        "ghost": GhostCharacter,
        "penguin": PenguinCharacter,
        "fox": FoxCharacter,
        "slime": SlimeCharacter,
        # Bleach Soul Reapers
        "ichigo": IchigoCharacter,
        "byakuya": ByakuyaCharacter,
        "yamamoto": YamamotoCharacter,
        "kenpachi": KenpachiCharacter,
        "hitsugaya": HitsugayaCharacter,
        "rukia": RukiaCharacter,
        "urahara": UraharaCharacter,
    }


class SkinManager:
    """Discovers, validates, and registers modular character skins."""

    def __init__(self):
        self._registry: Dict[str, Type[BaseCharacter]] = _get_builtin_classes()
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._populate_metadata()

    def register(self, skin_id: str, character_cls: Type[BaseCharacter], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Register a character class with its metadata."""
        self._registry[skin_id] = character_cls
        if metadata:
            self._metadata_cache[skin_id] = metadata

    def _populate_metadata(self) -> None:
        """Load metadata definitions for all built-in skins."""
        skin_defs = [
            ("thor", "Thor", "Norse God of Thunder wielding Mjolnir with fractal lightning.", ["hammer_throw", "lightning", "flight", "hammer_spin"]),
            ("dragon", "Dragon", "Fantasy winged dragon breathing fire and soaring the desktop.", ["fire_breath", "fireball", "flight", "glide"]),
            ("cat", "Cat", "Playful feline friend that chases cursors, grooms, and curls up.", ["chase", "pounce", "groom", "nap"]),
            ("dog", "Dog", "Enthusiastic puppy that wags its tail, barks, and fetches cursors.", ["bark", "dig", "fetch", "wag"]),
            ("hulk", "Hulk", "Green colossus with ground-shattering smashes and shockwaves.", ["hulk_smash", "super_jump", "roar"]),
            ("ironman", "Iron Man", "Armored hero with boot thrusters, repulsors, and air dash.", ["repulsor_blast", "flight", "air_dash"]),
            ("harry_potter", "Harry Potter", "Wizard casting spells, summoning spark trails, and flying a broom.", ["cast_spell", "broom_flight", "teleport"]),
            ("captain_america", "Captain America", "Super soldier throwing and bouncing his Vibranium Shield.", ["shield_throw", "shield_block", "hero_pose"]),
            ("thanos", "Thanos", "Titan wielding the 6 Infinity Stones with cosmic energy bursts.", ["time_stone", "reality_warp", "space_teleport", "power_blast", "the_snap"]),
            ("batman", "Batman", "Dark Knight grappling, cape gliding, and throwing batarangs.", ["grapple", "cape_glide", "batarang", "perch"]),
            ("superman", "Superman", "Man of Steel flying at supersonic speed with laser heat vision.", ["heat_vision", "supersonic_flight", "super_jump"]),
            ("spiderman", "Spider-Man", "Your friendly neighborhood Spider-Man with acrobatic web-swinging, web throws, and spider-sense.", ["web_swing", "web_throw", "spider_sense", "wall_crawl", "perch"]),
            ("pixel_wizard", "Pixel Wizard", "Mystic scholar channeling glowing arcane orbs, runes, and spatial teleports.", ["magic_orb", "teleport", "spell_circle"]),
            ("space_robot", "Space Robot", "Advanced cybernetic droid equipped with rocket thrusters, laser scanners, and holograms.", ["jet_boost", "hologram", "scan_beam"]),
            ("ninja", "Ninja", "Shadow shinobi mastering silent leaps, shuriken barrages, and smoke vanishing.", ["smoke_bomb", "shuriken", "wall_leap"]),
            ("vampire", "Vampire", "Noble lord of shadows levitating in a cape with swarms of bats.", ["bat_swarm", "shadow_mist", "levitate"]),
            ("fairy", "Fairy", "Enchanted sprite with iridescent wings casting sparkling dust and healing radiance.", ["sparkle_burst", "fairy_dust", "flutter"]),
            ("alien", "Alien", "Cosmic traveler hovering with anti-gravity bubbles and UFO tractor beams.", ["tractor_beam", "teleport", "alien_glow"]),
            ("ghost", "Ghost", "Spectral phantom fading through windows with eerie floating and spirit orbs.", ["phase_shift", "boo_spook", "spectral_glow"]),
            ("penguin", "Penguin", "Adorable arctic penguin belly-sliding across the screen and waddling cheerfully.", ["belly_slide", "peck_dance", "snow_hop"]),
            ("fox", "Fox", "Clever woodland red fox with a bushy tail, rapid sprints, and playful pounces.", ["dash_sprint", "pounce_jump", "tail_flick"]),
            ("slime", "Bouncy Slime", "Cheerful jelly creature that bounces with squash-and-stretch physics and splits droplets.", ["super_bounce", "jelly_split", "wobble"]),
            # Bleach Soul Reapers
            ("ichigo", "Ichigo Kurosaki", "Substitute Soul Reaper wielding Zangetsu with Getsuga Tenshō and Tensa Zangetsu Bankai.", ["getsuga_tensho", "bankai", "shunpo"]),
            ("byakuya", "Byakuya Kuchiki", "Captain of the 6th Division wielding Senbonzakura, Senkei, and Shūkei Hakuteiken.", ["senbonzakura", "senkei", "hakuteiken"]),
            ("yamamoto", "Genryūsai Yamamoto", "Captain-Commander of the Gotei 13 wielding Ryūjin Jakka and Zanka no Tachi.", ["ryujin_jakka", "zanka_no_tachi", "flame_wave"]),
            ("kenpachi", "Kenpachi Zaraki", "Captain of the 11th Division wielding colossal Nozarashi and demonic red Bankai.", ["nozarashi", "bankai_rage"]),
            ("hitsugaya", "Tōshirō Hitsugaya", "Captain of the 10th Division wielding the ice dragon Hyōrinmaru and Daiguren Bankai wings.", ["hyorinmaru", "daiguren_bankai", "soten_hyoso", "ice_wings", "flight"]),
            ("rukia", "Rukia Kuchiki", "Soul Reaper wielding the pure white snow blade Sode no Shirayuki and Hakka no Togame.", ["sode_no_shirayuki", "tsukishiro", "hakka_no_togame"]),
            ("urahara", "Kisuke Urahara", "Former 12th Division Captain wielding Benihime, paper fan, and Kannonbiraki Bankai.", ["benihime", "kannonbiraki_bankai"]),
        ]

        for skin_id, name, desc, abilities in skin_defs:
            meta_path = SKINS_DIR / skin_id / "skin.json"
            meta = {
                "id": skin_id,
                "name": name,
                "description": desc,
                "speed": 1.0,
                "canFly": "flight" in abilities or "glide" in abilities or "web_swing" in abilities or "levitate" in abilities or "flutter" in abilities or "tractor_beam" in abilities or "phase_shift" in abilities or "ice_wings" in abilities,
                "abilities": abilities,
                "category": "bleach" if skin_id in ["ichigo", "byakuya", "yamamoto", "kenpachi", "hitsugaya", "rukia", "urahara"] else ("superhero" if skin_id in ["thor", "hulk", "ironman", "captain_america", "batman", "superman", "thanos", "spiderman"] else ("animals" if skin_id in ["cat", "dog", "penguin", "fox"] else ("fantasy" if skin_id in ["dragon", "pixel_wizard", "fairy", "vampire", "ghost"] else ("sci-fi" if skin_id in ["space_robot", "alien"] else "cute"))))
            }
            if meta_path.exists():
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        meta.update(loaded)
                except Exception:
                    pass
            self._metadata_cache[skin_id] = meta

    def _discover_and_register_all(self) -> None:
        """Dynamically load and register built-in skin modules."""
        import importlib
        for skin_id, (mod_path, cls_name) in BUILTIN_SKINS.items():
            try:
                mod = importlib.import_module(mod_path)
                cls = getattr(mod, cls_name, None)
                if cls:
                    self.register(skin_id, cls)
            except Exception as e:
                print(f"[SkinManager] Warning: failed to load module {mod_path}: {e}")

    @staticmethod
    def normalize_skin_id(skin_id: str) -> str:
        """Normalize skin name to canonical lowercase ID."""
        if not skin_id:
            return "thor"
        raw = str(skin_id).lower().strip().replace("-", "_").replace(" ", "_")
        aliases = {
            "iron_man": "ironman",
            "super_man": "superman",
            "spider_man": "spiderman",
            "spidey": "spiderman",
            "spider": "spiderman",
            "captainamerica": "captain_america",
            "harrypotter": "harry_potter",
            "harry": "harry_potter",
            "potter": "harry_potter",
            "cap": "captain_america",
            "wizard": "pixel_wizard",
            "pixelwizard": "pixel_wizard",
            "robot": "space_robot",
            "spacerobot": "space_robot",
            "bouncy_slime": "slime",
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
        cls = self._registry.get(norm_id) or self._registry.get("thor")
        if not cls:
            from skins.thor.character import ThorCharacter
            return ThorCharacter(x, y)
        return cls(x, y)


# Global skin manager singleton with lazy on-demand module discovery
skin_manager = SkinManager()
