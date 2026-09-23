"""
Buddy Fusion Lab (Experimental).

Allows synthesizing hybrid cross-character abilities from composable primitives:
- Ichigo Shunpo + Thor Lightning -> Lightning Shunpo
- Spider-Man Web + Iron Man Repulsor -> Repulsor Web Dash
- Byakuya Petals + Rukia Ice -> Frozen Senbonzakura

Disabled by default in settings.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional

from core.abilities.ability import AbilityDefinition, AbilityRegistry, RarityTier
from core.abilities.primitives import (
    AbilityPrimitive,
    ChargePrimitive,
    MovementPrimitive,
    MeleePrimitive,
    ProjectilePrimitive,
    AreaEffectPrimitive,
    TeleportPrimitive,
    ParticlePrimitive,
    SoundPrimitive,
    RecoveryPrimitive,
)


@dataclass
class FusionRecipe:
    id: str
    name: str
    description: str
    primary_character_id: str
    secondary_character_id: str
    ability: AbilityDefinition


class FusionLab:
    """Experimental laboratory for cross-character abilities."""

    _instance: Optional[FusionLab] = None

    def __init__(self):
        self.enabled: bool = False
        self._recipes: Dict[str, FusionRecipe] = {}
        self._init_default_fusions()

    @classmethod
    def get_instance(cls) -> FusionLab:
        if cls._instance is None:
            cls._instance = FusionLab()
        return cls._instance

    def _init_default_fusions(self) -> None:
        # 1. Ichigo + Thor = Lightning Shunpo
        lightning_shunpo_ab = AbilityDefinition(
            id="fusion_lightning_shunpo",
            name="Lightning Shunpo",
            description="Hyper-accelerated flash step wrapped in Asgardian crackling thunder.",
            character_id="ichigo",
            primitives=[
                SoundPrimitive(sound_id="thunder_strike"),
                TeleportPrimitive(distance=220.0, particle_type="speed_lines"),
                ParticlePrimitive(duration=0.5, particle_family="lightning_sparks", color=(0.4, 0.9, 1.0, 0.95), count=18),
                AreaEffectPrimitive(duration=0.6, radius=120.0, color=(0.3, 0.8, 1.0, 0.8), sound="thunder_clap"),
                RecoveryPrimitive(duration=0.2),
            ],
            cooldown=6.0,
            rarity=RarityTier.EPIC,
            tags=["teleport", "movement", "element", "area"],
        )
        self._recipes["lightning_shunpo"] = FusionRecipe(
            id="lightning_shunpo",
            name="Lightning Shunpo",
            description="Ichigo Shunpo + Thor Lightning",
            primary_character_id="ichigo",
            secondary_character_id="thor",
            ability=lightning_shunpo_ab,
        )

        # 2. Spiderman + Iron Man = Repulsor Web Dash
        repulsor_web_ab = AbilityDefinition(
            id="fusion_repulsor_web",
            name="Repulsor Web Dash",
            description="Propels web grapple forward with high-output repulsor thrusters.",
            character_id="spiderman",
            primitives=[
                SoundPrimitive(sound_id="thwip"),
                ProjectilePrimitive(duration=0.3, projectile_type="web_line", speed=600.0, color=(0.95, 0.95, 0.95, 0.9)),
                ChargePrimitive(duration=0.2, color=(0.3, 0.8, 1.0, 0.9), sound="repulsor_charge"),
                MovementPrimitive(duration=0.5, dx=220.0, dy=-40.0, easing="ease_out"),
                ParticlePrimitive(duration=0.4, particle_family="blue_flame_trail", color=(0.4, 0.8, 1.0, 0.9), count=12),
                RecoveryPrimitive(duration=0.25),
            ],
            cooldown=5.5,
            rarity=RarityTier.EPIC,
            tags=["movement", "projectile", "acrobatic"],
        )
        self._recipes["repulsor_web"] = FusionRecipe(
            id="repulsor_web",
            name="Repulsor Web Dash",
            description="Spider-Man Web Swing + Iron Man Repulsor",
            primary_character_id="spiderman",
            secondary_character_id="ironman",
            ability=repulsor_web_ab,
        )

        # 3. Byakuya + Rukia = Frozen Senbonzakura
        frozen_senbonzakura_ab = AbilityDefinition(
            id="fusion_frozen_senbonzakura",
            name="Frozen Senbonzakura",
            description="Cherry blossom petals freeze into crystalline diamond dust.",
            character_id="byakuya",
            primitives=[
                SoundPrimitive(sound_id="chire"),
                ChargePrimitive(duration=0.4, color=(0.7, 0.9, 1.0, 0.95), sound="ice_freeze"),
                AreaEffectPrimitive(duration=1.4, effect_type="frost_petals", radius=180.0, color=(0.6, 0.85, 1.0, 0.9)),
                ParticlePrimitive(duration=0.8, particle_family="snow_crystals", color=(0.8, 0.95, 1.0, 0.9), count=25),
                RecoveryPrimitive(duration=0.3),
            ],
            cooldown=7.5,
            rarity=RarityTier.EPIC,
            tags=["area", "element", "finisher"],
        )
        self._recipes["frozen_senbonzakura"] = FusionRecipe(
            id="frozen_senbonzakura",
            name="Frozen Senbonzakura",
            description="Byakuya Senbonzakura + Rukia Snow & Frost",
            primary_character_id="byakuya",
            secondary_character_id="rukia",
            ability=frozen_senbonzakura_ab,
        )

    def list_recipes(self) -> List[FusionRecipe]:
        return list(self._recipes.values())

    def get_fusion_ability(self, char_a: str, char_b: str) -> Optional[AbilityDefinition]:
        """Finds any registered fusion ability matching the two characters."""
        if not self.enabled:
            return None
        for recipe in self._recipes.values():
            if (recipe.primary_character_id == char_a and recipe.secondary_character_id == char_b) or \
               (recipe.primary_character_id == char_b and recipe.secondary_character_id == char_a):
                return recipe.ability
        return None


fusion_lab = FusionLab.get_instance()
