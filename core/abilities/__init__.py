"""Composable ability system, action primitives, combo chaining, and experimental Fusion Lab."""

from core.abilities.primitives import (
    AbilityPrimitive,
    MovementPrimitive,
    ChargePrimitive,
    ProjectilePrimitive,
    BeamPrimitive,
    MeleePrimitive,
    AreaEffectPrimitive,
    ShieldPrimitive,
    TeleportPrimitive,
    TransformationPrimitive,
    ParticlePrimitive,
    SoundPrimitive,
    RecoveryPrimitive,
)
from core.abilities.ability import AbilityDefinition, AbilityRegistry, RarityTier, ability_registry
from core.abilities.combo import ComboEngine, combo_engine
from core.abilities.fusion import FusionLab, fusion_lab

__all__ = [
    "AbilityPrimitive",
    "MovementPrimitive",
    "ChargePrimitive",
    "ProjectilePrimitive",
    "BeamPrimitive",
    "MeleePrimitive",
    "AreaEffectPrimitive",
    "ShieldPrimitive",
    "TeleportPrimitive",
    "TransformationPrimitive",
    "ParticlePrimitive",
    "SoundPrimitive",
    "RecoveryPrimitive",
    "AbilityDefinition",
    "AbilityRegistry",
    "RarityTier",
    "ability_registry",
    "ComboEngine",
    "combo_engine",
    "FusionLab",
    "fusion_lab",
]
