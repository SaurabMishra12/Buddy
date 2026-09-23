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
    # Bleach Soul Reapers & Espada
    "ichigo": ("skins.ichigo.character", "IchigoCharacter"),
    "byakuya": ("skins.byakuya.character", "ByakuyaCharacter"),
    "yamamoto": ("skins.yamamoto.character", "YamamotoCharacter"),
    "kenpachi": ("skins.kenpachi.character", "KenpachiCharacter"),
    "hitsugaya": ("skins.hitsugaya.character", "HitsugayaCharacter"),
    "rukia": ("skins.rukia.character", "RukiaCharacter"),
    "urahara": ("skins.urahara.character", "UraharaCharacter"),
    "aizen": ("skins.aizen.character", "AizenCharacter"),
    "yoruichi": ("skins.yoruichi.character", "YoruichiCharacter"),
    "shunsui": ("skins.shunsui.character", "ShunsuiCharacter"),
    "soi_fon": ("skins.soi_fon.character", "SoiFonCharacter"),
    "shinji": ("skins.shinji.character", "ShinjiCharacter"),
    "mayuri": ("skins.mayuri.character", "MayuriCharacter"),
    "ulquiorra": ("skins.ulquiorra.character", "UlquiorraCharacter"),
}


ACTIVE_ROSTER = [
    "ichigo",
    "byakuya",
    "yamamoto",
    "hitsugaya",
    "rukia",
    "aizen",
    "ulquiorra",
]

# Backwards compatibility alias
ACTIVE_BLEACH_ROSTER = ACTIVE_ROSTER

ARCHIVED_ROSTER = [k for k in BUILTIN_SKINS.keys() if k not in ACTIVE_ROSTER]


def _get_active_classes() -> Dict[str, Type[BaseCharacter]]:
    """Only pre-import the 7 active Bleach characters at startup for instant boot and minimum RAM."""
    from skins.ichigo.character import IchigoCharacter
    from skins.byakuya.character import ByakuyaCharacter
    from skins.yamamoto.character import YamamotoCharacter
    from skins.hitsugaya.character import HitsugayaCharacter
    from skins.rukia.character import RukiaCharacter
    from skins.aizen.character import AizenCharacter
    from skins.ulquiorra.character import UlquiorraCharacter

    return {
        "ichigo": IchigoCharacter,
        "byakuya": ByakuyaCharacter,
        "yamamoto": YamamotoCharacter,
        "hitsugaya": HitsugayaCharacter,
        "rukia": RukiaCharacter,
        "aizen": AizenCharacter,
        "ulquiorra": UlquiorraCharacter,
    }


class SkinManager:
    """Discovers, validates, and registers modular character skins."""

    def __init__(self):
        # Startup optimization: pre-load only the 7 active Bleach characters
        self._registry: Dict[str, Type[BaseCharacter]] = _get_active_classes()
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
            # Bleach Soul Reapers & Espada
            ("ichigo", "Ichigo Kurosaki", "Substitute Soul Reaper wielding Zangetsu with Getsuga Tenshō and Tensa Zangetsu Bankai.", ["getsuga_tensho", "bankai", "shunpo"]),
            ("byakuya", "Byakuya Kuchiki", "Captain of the 6th Division wielding Senbonzakura, Senkei, and Shūkei Hakuteiken.", ["senbonzakura", "senkei", "hakuteiken"]),
            ("yamamoto", "Genryūsai Yamamoto", "Captain-Commander of the Gotei 13 wielding Ryūjin Jakka and Zanka no Tachi.", ["ryujin_jakka", "zanka_no_tachi", "flame_wave"]),
            ("kenpachi", "Kenpachi Zaraki", "Captain of the 11th Division wielding colossal Nozarashi and demonic red Bankai.", ["nozarashi", "bankai_rage"]),
            ("hitsugaya", "Tōshirō Hitsugaya", "Captain of the 10th Division wielding the ice dragon Hyōrinmaru and Daiguren Bankai wings.", ["hyorinmaru", "daiguren_bankai", "soten_hyoso", "ice_wings", "flight"]),
            ("rukia", "Rukia Kuchiki", "Soul Reaper wielding the pure white snow blade Sode no Shirayuki and Hakka no Togame.", ["sode_no_shirayuki", "tsukishiro", "hakka_no_togame"]),
            ("urahara", "Kisuke Urahara", "Former 12th Division Captain wielding Benihime, paper fan, and Kannonbiraki Bankai.", ["benihime", "kannonbiraki_bankai"]),
            ("aizen", "Sōsuke Aizen", "Former 5th Division Captain commanding Kyōka Suigetsu complete hypnosis and Kurohitsugi.", ["kyoka_suigetsu", "kurohitsugi", "shunpo"]),
            ("yoruichi", "Yoruichi Shihōin", "Flash Goddess and former Onmitsukidō Commander wielding lightning Shunkō and feline agility.", ["shunko", "lightning_dash", "shunpo"]),
            ("shunsui", "Shunsui Kyōraku", "Captain of the 8th Division wielding dual blades Katen Kyōkotsu, shadow games, and Karamatsu Shinjū.", ["kageoni", "karamatsu_shinju", "irooni"]),
            ("soi_fon", "Soi Fon", "Commander of the Onmitsukidō wielding Suzumebachi stinger and Jakuhō Raikōben Bankai artillery.", ["suzumebachi", "jakuho_raikoben", "nigeki_kessatsu"]),
            ("shinji", "Shinji Hirako", "5th Division Captain and Visored leader wielding Sakanade inverted perception and Sakashima Yokoshima Bankai.", ["sakanade", "hollow_mask", "inverted_world"]),
            ("mayuri", "Mayuri Kurotsuchi", "President of the Shinigami Research Institute wielding Ashisogi Jizō and Konjiki Ashisogi Jizō Bankai.", ["ashisogi_jizo", "konjiki_bankai", "poison_mist"]),
            ("ulquiorra", "Ulquiorra Cifer", "4th Espada wielding Murciélago bat wings, Cero Oscuras, and Segunda Etapa.", ["cero_oscuras", "resurreccion_murcielago", "lanza_del_relampago", "flight"]),
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
                "category": "bleach" if skin_id in ["ichigo", "byakuya", "yamamoto", "kenpachi", "hitsugaya", "rukia", "urahara", "aizen", "yoruichi", "shunsui", "soi_fon", "shinji", "mayuri", "ulquiorra"] else ("superhero" if skin_id in ["thor", "hulk", "ironman", "captain_america", "batman", "superman", "thanos", "spiderman"] else ("animals" if skin_id in ["cat", "dog", "penguin", "fox"] else ("fantasy" if skin_id in ["dragon", "pixel_wizard", "fairy", "vampire", "ghost"] else ("sci-fi" if skin_id in ["space_robot", "alien"] else "cute"))))
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
            return "ichigo"
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

    def is_archived(self, skin_id: str) -> bool:
        """Return True if character is archived (not in active 7 Bleach roster)."""
        norm_id = self.normalize_skin_id(skin_id)
        return norm_id in ARCHIVED_ROSTER

    def list_skins(self, include_archived: bool = True) -> List[str]:
        """Return list of skin IDs. Includes all 36 for schema/tests if include_archived is True."""
        if include_archived:
            return list(BUILTIN_SKINS.keys())
        return list(ACTIVE_ROSTER)

    def get_active_skins(self) -> List[Dict[str, Any]]:
        """Return metadata strictly for the 7 active Bleach characters."""
        return [self._metadata_cache[sid] for sid in ACTIVE_ROSTER if sid in self._metadata_cache]

    def get_available_skins(self, include_archived: bool = True) -> List[Dict[str, Any]]:
        """Return list of skins metadata. Returns all 36 if include_archived=True (default), or active 7 if False."""
        if include_archived:
            return list(self._metadata_cache.values())
        return self.get_active_skins()

    def get_metadata(self, skin_id: str) -> Optional[Dict[str, Any]]:
        """Return metadata for specific skin ID with case-insensitive normalization."""
        norm_id = self.normalize_skin_id(skin_id)
        return self._metadata_cache.get(norm_id)

    def create_character(self, skin_id: str, x: float = 500.0, y: float = 400.0) -> BaseCharacter:
        """Instantiate character for specified skin ID with lazy loading for archived characters and fallback to Ichigo."""
        import importlib
        norm_id = self.normalize_skin_id(skin_id)

        # 1. Fast path: already loaded active character or previously requested archived character
        cls = self._registry.get(norm_id)

        # 2. Lazy loading: if skin is archived but registered in BUILTIN_SKINS, import on demand
        if not cls and norm_id in BUILTIN_SKINS:
            mod_path, cls_name = BUILTIN_SKINS[norm_id]
            try:
                mod = importlib.import_module(mod_path)
                cls = getattr(mod, cls_name, None)
                if cls:
                    self._registry[norm_id] = cls
            except Exception as e:
                print(f"[SkinManager] Warning: failed lazy-loading archived skin '{norm_id}': {e}")

        # 3. Fallback to active Bleach protagonist Ichigo
        if not cls:
            cls = self._registry.get("ichigo")
            if not cls:
                from skins.ichigo.character import IchigoCharacter
                cls = IchigoCharacter
                self._registry["ichigo"] = cls

        return cls(x, y)


# Global skin manager singleton with lazy on-demand module discovery
skin_manager = SkinManager()
