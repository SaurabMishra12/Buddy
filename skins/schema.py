"""Character metadata schema, validation, and universal power-tier descriptors."""

from typing import Dict, Any, List, Optional


class PowerTier:
    """Universal power progression hierarchy across all universes."""
    BASE = "BASE"
    SIGNATURE = "SIGNATURE"
    POWER_UP = "POWER_UP"
    ULTIMATE = "ULTIMATE"


# Universal character-specific power tier terminology
POWER_TIER_REGISTRY: Dict[str, Dict[str, str]] = {
    "ichigo": {"signature": "Getsuga Tenshō", "power_up": "Shikai (Zangetsu)", "ultimate": "Bankai (Tensa Zangetsu)"},
    "byakuya": {"signature": "Senbonzakura", "power_up": "Senkei Kageyoshi", "ultimate": "Shūkei: Hakuteiken"},
    "yamamoto": {"signature": "Ryūjin Jakka", "power_up": "Ennetsu Jigoku", "ultimate": "Zanka no Tachi"},
    "kenpachi": {"signature": "Nozarashi", "power_up": "Eyepatch Release", "ultimate": "Demonic Bankai Rage"},
    "hitsugaya": {"signature": "Hyōrinmaru", "power_up": "Sōten Kisshun", "ultimate": "Daiguren Hyōrinmaru"},
    "rukia": {"signature": "Sode no Shirayuki", "power_up": "Some no Mai: Tsukishiro", "ultimate": "Hakka no Togame"},
    "urahara": {"signature": "Benihime", "power_up": "Chikasumi no Tate", "ultimate": "Kannonbiraki Bankai"},
    "aizen": {"signature": "Kyōka Suigetsu", "power_up": "Kanzen Saimin", "ultimate": "Hadō #90: Kurohitsugi"},
    "yoruichi": {"signature": "Shunkō", "power_up": "Lightning Dash", "ultimate": "Thunder God Form"},
    "shunsui": {"signature": "Katen Kyōkotsu", "power_up": "Kageoni", "ultimate": "Karamatsu Shinjū"},
    "soi_fon": {"signature": "Suzumebachi", "power_up": "Stealth Step", "ultimate": "Jakuhō Raikōben"},
    "shinji": {"signature": "Sakanade", "power_up": "Inverted World", "ultimate": "Visored Hollow Mask"},
    "mayuri": {"signature": "Ashisogi Jizō", "power_up": "Poison Mist", "ultimate": "Konjiki Ashisogi Jizō"},
    "ulquiorra": {"signature": "Cero Oscuras", "power_up": "Resurrección (Murciélago)", "ultimate": "Segunda Etapa"},
    "thor": {"signature": "Mjolnir Throw", "power_up": "Lightning Summon", "ultimate": "God Blast"},
    "spiderman": {"signature": "Web Shot", "power_up": "Spider-Sense", "ultimate": "Acrobatic Web Swing"},
    "ironman": {"signature": "Repulsor Blast", "power_up": "Flight Overdrive", "ultimate": "Maximum Repulsor"},
    "hulk": {"signature": "Hulk Smash", "power_up": "Gamma Roar", "ultimate": "World Breaker Stomp"},
    "batman": {"signature": "Batarang", "power_up": "Smoke Stealth", "ultimate": "Batwing Strike"},
    "superman": {"signature": "Heat Vision", "power_up": "Supersonic Flight", "ultimate": "Solar Flare"},
    "thanos": {"signature": "Power Blast", "power_up": "Reality Warp", "ultimate": "Infinity Snap"},
    "captain_america": {"signature": "Shield Throw", "power_up": "Vibranium Block", "ultimate": "Avengers Assemble"},
    "cat": {"signature": "Pounce", "power_up": "Zoomies", "ultimate": "Cozy Catnap"},
    "dog": {"signature": "Fetch", "power_up": "Tail Wag Burst", "ultimate": "Joyful Bark"},
    "dragon": {"signature": "Fireball", "power_up": "Flame Glide", "ultimate": "Inferno Breath"},
    "pixel_wizard": {"signature": "Arcane Orb", "power_up": "Spell Circle", "ultimate": "Spatial Teleport"},
    "space_robot": {"signature": "Laser Scan", "power_up": "Hologram Display", "ultimate": "Jet Thruster Overdrive"},
    "ninja": {"signature": "Shuriken Throw", "power_up": "Smoke Vanish", "ultimate": "Shadow Step Leap"},
    "vampire": {"signature": "Bat Swarm", "power_up": "Shadow Mist", "ultimate": "Crimson Levitation"},
    "fairy": {"signature": "Sparkle Trail", "power_up": "Healing Glow", "ultimate": "Prismatic Flutter"},
    "alien": {"signature": "Tractor Beam", "power_up": "Cosmic Bubble", "ultimate": "UFO Abduction"},
    "ghost": {"signature": "Phase Shift", "power_up": "Spectral Glow", "ultimate": "Spooky Surprise"},
    "penguin": {"signature": "Belly Slide", "power_up": "Snow Hop", "ultimate": "Waddle Parade"},
    "fox": {"signature": "Pounce Jump", "power_up": "Dash Sprint", "ultimate": "Bushy Tail Flourish"},
    "slime": {"signature": "Super Bounce", "power_up": "Jelly Split", "ultimate": "Mega Wobble"},
    "harry_potter": {"signature": "Cast Spell", "power_up": "Broom Flight", "ultimate": "Patronus Summon"},
}


def get_power_tier_labels(skin_id: str) -> Dict[str, str]:
    """Retrieve universe-authentic terminology for character power levels."""
    sid = str(skin_id).lower()
    return POWER_TIER_REGISTRY.get(sid, {
        "signature": "Signature Ability",
        "power_up": "Power-Up",
        "ultimate": "Ultimate Move"
    })


def validate_character_metadata(meta: Dict[str, Any]) -> List[str]:
    """Validate character metadata against required fields. Returns list of errors (empty if valid)."""
    errors = []
    if not isinstance(meta, dict):
        return ["Metadata must be a dictionary"]

    for req in ("id", "name", "description"):
        if req not in meta or not str(meta[req]).strip():
            errors.append(f"Missing required metadata field: '{req}'")

    abilities = meta.get("abilities", [])
    if not isinstance(abilities, list):
        errors.append("Field 'abilities' must be a list")

    return errors
