"""
Buddy Ability Definition and Registry.

Composes primitives into complete abilities, manages cooldowns, rarity,
and registers canonical abilities for characters.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import time

from core.abilities.primitives import (
    AbilityExecutionContext,
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


class RarityTier(str, Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    ULTIMATE = "ultimate"


@dataclass
class AbilityDefinition:
    """A complete composable ability built from primitives."""
    id: str
    name: str
    description: str
    character_id: str
    primitives: List[AbilityPrimitive]
    cooldown: float = 3.0  # seconds
    rarity: RarityTier = RarityTier.COMMON
    tags: List[str] = field(default_factory=list)  # movement, projectile, melee, area, defensive, finisher, etc.
    sound_cue: Optional[str] = None
    autonomous_weight: float = 1.0  # baseline weight for autonomous brain selection
    last_used: float = 0.0

    @property
    def total_duration(self) -> float:
        return sum(p.duration for p in self.primitives)

    def is_ready(self, now: Optional[float] = None) -> bool:
        t = now if now is not None else time.time()
        return (t - self.last_used) >= self.cooldown

    def trigger(self, now: Optional[float] = None) -> None:
        t = now if now is not None else time.time()
        self.last_used = t


class AbilityRunner:
    """Manages active ability execution across frames."""

    def __init__(self, definition: AbilityDefinition, ctx: AbilityExecutionContext):
        self.definition = definition
        self.ctx = ctx
        self.ctx.duration = definition.total_duration
        self.elapsed = 0.0
        self.completed = False
        for prim in self.definition.primitives:
            if hasattr(prim, "reset"):
                prim.reset()

    def update(self, dt: float) -> None:
        if self.completed:
            return

        self.elapsed += dt
        self.ctx.elapsed_time = self.elapsed

        accumulated_time = 0.0
        for prim in self.definition.primitives:
            start_t = accumulated_time
            end_t = accumulated_time + prim.duration
            accumulated_time = end_t

            if getattr(prim, "completed", False):
                continue

            if self.elapsed >= start_t and self.elapsed < end_t:
                prim_progress = (self.elapsed - start_t) / prim.duration
                prim.execute(self.ctx, min(1.0, max(0.0, prim_progress)))
            elif self.elapsed >= end_t:
                # Finished this primitive exactly once
                prim.execute(self.ctx, 1.0)
                prim.completed = True

        if self.elapsed >= self.definition.total_duration:
            self.completed = True
            self.ctx.completed = True


class AbilityRegistry:
    """Global registry of character abilities."""

    _instance: Optional[AbilityRegistry] = None
    _abilities: Dict[str, AbilityDefinition] = {}

    def __new__(cls) -> AbilityRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._abilities = {}
            cls._instance._init_canonical_abilities()
        return cls._instance

    @classmethod
    def get_instance(cls) -> AbilityRegistry:
        if cls._instance is None:
            cls._instance = AbilityRegistry()
        return cls._instance

    def register(self, ability: AbilityDefinition) -> None:
        self._abilities[ability.id] = ability

    def get(self, ability_id: str) -> Optional[AbilityDefinition]:
        return self._abilities.get(ability_id)

    def get_by_character(self, character_id: str) -> List[AbilityDefinition]:
        return [ab for ab in self._abilities.values() if ab.character_id == character_id]

    def _init_canonical_abilities(self) -> None:
        """Register canonical, composable abilities for characters."""

        # -------------------------------------------------------------
        # BLEACH: ICHIGO KUROSAKI
        # -------------------------------------------------------------
        self.register(AbilityDefinition(
            id="ichigo_shunpo",
            name="Shunpo",
            description="High-speed flash step repositioning.",
            character_id="ichigo",
            primitives=[
                SoundPrimitive(sound_id="shunpo"),
                TeleportPrimitive(distance=180.0, particle_type="speed_lines"),
                RecoveryPrimitive(duration=0.15),
            ],
            cooldown=2.5,
            rarity=RarityTier.COMMON,
            tags=["movement", "teleport"],
            autonomous_weight=2.5,
        ))

        self.register(AbilityDefinition(
            id="ichigo_getsuga",
            name="Getsuga Tenshō",
            description="Condenses spiritual pressure and releases an azure crescent slash.",
            character_id="ichigo",
            primitives=[
                ChargePrimitive(duration=0.4, particle_type="energy_gather", color=(0.2, 0.6, 1.0, 0.9), sound="charge"),
                MeleePrimitive(duration=0.25, slash_type="arc_slash", color=(0.3, 0.7, 1.0, 0.9), sound="slash"),
                ProjectilePrimitive(duration=0.9, projectile_type="getsuga_crescent", speed=450.0, color=(0.2, 0.7, 1.0, 0.9), sound="getsuga_release"),
                RecoveryPrimitive(duration=0.3),
            ],
            cooldown=5.0,
            rarity=RarityTier.UNCOMMON,
            tags=["melee", "projectile", "finisher"],
            autonomous_weight=2.0,
        ))

        self.register(AbilityDefinition(
            id="ichigo_bankai",
            name="Bankai: Tensa Zangetsu",
            description="Condenses vast Reiatsu into a sleek daitō and black shihakushō.",
            character_id="ichigo",
            primitives=[
                SoundPrimitive(sound_id="bankai_shout"),
                ChargePrimitive(duration=0.8, particle_type="black_red_whirl", color=(0.1, 0.1, 0.1, 0.95), intensity=1.8),
                TransformationPrimitive(duration=1.2, target_form="ultimate", aura_color=(0.9, 0.1, 0.1, 0.9), sound="bankai_burst"),
                AreaEffectPrimitive(duration=0.6, radius=160.0, color=(0.8, 0.1, 0.1, 0.8)),
                RecoveryPrimitive(duration=0.4),
            ],
            cooldown=25.0,
            rarity=RarityTier.ULTIMATE,
            tags=["transformation", "ultimate", "area"],
            autonomous_weight=0.2,
        ))

        # -------------------------------------------------------------
        # BLEACH: BYAKUYA KUCHIKI
        # -------------------------------------------------------------
        self.register(AbilityDefinition(
            id="byakuya_senbonzakura",
            name="Senbonzakura",
            description="Scatters sword blade into countless lethal cherry blossom petals.",
            character_id="byakuya",
            primitives=[
                SoundPrimitive(sound_id="chire"),
                ChargePrimitive(duration=0.4, color=(1.0, 0.6, 0.8, 0.9)),
                AreaEffectPrimitive(duration=1.2, effect_type="petal_storm", radius=170.0, color=(1.0, 0.5, 0.75, 0.85), sound="petal_flourish"),
                RecoveryPrimitive(duration=0.3),
            ],
            cooldown=6.0,
            rarity=RarityTier.UNCOMMON,
            tags=["area", "projectile"],
            autonomous_weight=2.0,
        ))

        self.register(AbilityDefinition(
            id="byakuya_senkei",
            name="Senkei Senbonzakura Kageyoshi",
            description="True killing form enclosing space in four rows of glowing blades.",
            character_id="byakuya",
            primitives=[
                SoundPrimitive(sound_id="senkei_release"),
                TransformationPrimitive(duration=1.5, target_form="ultimate", aura_color=(1.0, 0.4, 0.7, 0.95), sound="senkei_burst"),
                AreaEffectPrimitive(duration=1.0, radius=200.0, color=(1.0, 0.4, 0.7, 0.9)),
                RecoveryPrimitive(duration=0.4),
            ],
            cooldown=30.0,
            rarity=RarityTier.ULTIMATE,
            tags=["transformation", "ultimate", "area"],
            autonomous_weight=0.2,
        ))

        # -------------------------------------------------------------
        # BLEACH: SOSUKE AIZEN
        # -------------------------------------------------------------
        self.register(AbilityDefinition(
            id="aizen_kyoka_suigetsu",
            name="Kyōka Suigetsu",
            description="Complete Hypnosis bending the perception of space and time.",
            character_id="aizen",
            primitives=[
                SoundPrimitive(sound_id="aizen_whisper"),
                TeleportPrimitive(duration=0.5, distance=120.0, particle_type="mirror_shatter", sound="glass_shatter"),
                ParticlePrimitive(duration=0.8, particle_family="shattered_illusion", color=(0.6, 0.8, 1.0, 0.8), count=16),
                RecoveryPrimitive(duration=0.3),
            ],
            cooldown=7.0,
            rarity=RarityTier.UNCOMMON,
            tags=["teleport", "defensive"],
            autonomous_weight=1.8,
        ))

        self.register(AbilityDefinition(
            id="aizen_kurohitsugi",
            name="Hadō #90: Kurohitsugi",
            description="Black Coffin encasing the target in a torrent of gravitational darkness.",
            character_id="aizen",
            primitives=[
                SoundPrimitive(sound_id="kurohitsugi_chant"),
                ChargePrimitive(duration=1.2, particle_type="black_gravity", color=(0.05, 0.05, 0.08, 0.95), intensity=2.0),
                AreaEffectPrimitive(duration=1.4, effect_type="black_box", radius=180.0, color=(0.05, 0.05, 0.08, 0.95), sound="kurohitsugi_collapse"),
                RecoveryPrimitive(duration=0.5),
            ],
            cooldown=35.0,
            rarity=RarityTier.ULTIMATE,
            tags=["area", "ultimate", "finisher"],
            autonomous_weight=0.15,
        ))

        # -------------------------------------------------------------
        # BLEACH: YORUICHI SHIHŌIN
        # -------------------------------------------------------------
        self.register(AbilityDefinition(
            id="yoruichi_shunko",
            name="Shunkō",
            description="Pressurizes lightning Kidō around shoulders and back.",
            character_id="yoruichi",
            primitives=[
                ChargePrimitive(duration=0.3, particle_type="lightning_spark", color=(0.9, 0.9, 0.2, 0.9), sound="lightning_spark"),
                MovementPrimitive(duration=0.3, dx=160.0, easing="ease_out"),
                MeleePrimitive(duration=0.25, slash_type="lightning_strike", color=(1.0, 1.0, 0.4, 0.9), sound="thunder_strike"),
                RecoveryPrimitive(duration=0.2),
            ],
            cooldown=4.5,
            rarity=RarityTier.UNCOMMON,
            tags=["movement", "melee", "element"],
            autonomous_weight=2.2,
        ))

        # -------------------------------------------------------------
        # BLEACH: ULQUIORRA CIFER
        # -------------------------------------------------------------
        self.register(AbilityDefinition(
            id="ulquiorra_cero_oscuras",
            name="Cero Oscuras",
            description="Pitch-black Grand Hollow flash with immense destructive force.",
            character_id="ulquiorra",
            primitives=[
                ChargePrimitive(duration=0.5, particle_type="black_green_charge", color=(0.1, 0.9, 0.4, 0.9), sound="cero_charge"),
                BeamPrimitive(duration=1.0, beam_type="cero_beam", length=550.0, width=28.0, color=(0.08, 0.08, 0.08, 0.95), sound="cero_blast"),
                RecoveryPrimitive(duration=0.4),
            ],
            cooldown=8.0,
            rarity=RarityTier.RARE,
            tags=["projectile", "element", "finisher"],
            autonomous_weight=1.5,
        ))

        self.register(AbilityDefinition(
            id="ulquiorra_segunda_etapa",
            name="Segunda Etapa",
            description="Second release unique to Ulquiorra, cloaking him in nihilistic power.",
            character_id="ulquiorra",
            primitives=[
                TransformationPrimitive(duration=1.5, target_form="ultimate", aura_color=(0.1, 0.8, 0.4, 0.95), sound="resurreccion"),
                AreaEffectPrimitive(duration=0.8, radius=190.0, color=(0.1, 0.8, 0.4, 0.8)),
                RecoveryPrimitive(duration=0.4),
            ],
            cooldown=30.0,
            rarity=RarityTier.ULTIMATE,
            tags=["transformation", "ultimate"],
            autonomous_weight=0.2,
        ))

        # -------------------------------------------------------------
        # MARVEL: THOR
        # -------------------------------------------------------------
        self.register(AbilityDefinition(
            id="thor_hammer_throw",
            name="Mjolnir Hammer Throw",
            description="Hurls enchanted uru hammer forward, returning with crackling lightning.",
            character_id="thor",
            primitives=[
                SoundPrimitive(sound_id="mjolnir_whirl"),
                ProjectilePrimitive(duration=0.7, projectile_type="hammer_spin", speed=400.0, color=(0.7, 0.9, 1.0, 0.95), sound="hammer_flight"),
                ParticlePrimitive(duration=0.3, particle_family="lightning_sparks", color=(0.5, 0.85, 1.0, 0.9), count=10),
                RecoveryPrimitive(duration=0.3),
            ],
            cooldown=5.0,
            rarity=RarityTier.UNCOMMON,
            tags=["projectile", "element"],
            autonomous_weight=2.0,
        ))

        self.register(AbilityDefinition(
            id="thor_god_blast",
            name="God Blast",
            description="Summons the celestial fury of Asgard into a sky-shattering thunder strike.",
            character_id="thor",
            primitives=[
                SoundPrimitive(sound_id="thunder_clap"),
                TransformationPrimitive(duration=1.2, target_form="ultimate", aura_color=(0.4, 0.8, 1.0, 0.95), sound="lightning_surge"),
                AreaEffectPrimitive(duration=1.0, effect_type="lightning_burst", radius=220.0, color=(0.5, 0.9, 1.0, 0.9)),
                RecoveryPrimitive(duration=0.5),
            ],
            cooldown=28.0,
            rarity=RarityTier.ULTIMATE,
            tags=["transformation", "ultimate", "area", "element"],
            autonomous_weight=0.2,
        ))

        # -------------------------------------------------------------
        # MARVEL: SPIDER-MAN
        # -------------------------------------------------------------
        self.register(AbilityDefinition(
            id="spiderman_web_swing",
            name="Web Swing & Aerial Flip",
            description="Fires a web line to swing gracefully across the desktop with an acrobatic flip.",
            character_id="spiderman",
            primitives=[
                SoundPrimitive(sound_id="thwip"),
                ProjectilePrimitive(duration=0.3, projectile_type="web_line", speed=600.0, color=(0.95, 0.95, 0.95, 0.9)),
                MovementPrimitive(duration=0.6, dx=180.0, dy=-60.0, easing="ease_in_out"),
                RecoveryPrimitive(duration=0.25),
            ],
            cooldown=4.0,
            rarity=RarityTier.COMMON,
            tags=["movement", "acrobatic"],
            autonomous_weight=2.5,
        ))

        # -------------------------------------------------------------
        # MARVEL: IRON MAN
        # -------------------------------------------------------------
        self.register(AbilityDefinition(
            id="ironman_repulsor",
            name="Repulsor Blast",
            description="Fires concentrated particle beam from palm repulsor node.",
            character_id="ironman",
            primitives=[
                ChargePrimitive(duration=0.3, color=(0.4, 0.8, 1.0, 0.9), sound="repulsor_charge"),
                BeamPrimitive(duration=0.8, beam_type="repulsor_stream", length=480.0, width=18.0, color=(0.4, 0.85, 1.0, 0.95), sound="repulsor_fire"),
                RecoveryPrimitive(duration=0.3),
            ],
            cooldown=4.5,
            rarity=RarityTier.UNCOMMON,
            tags=["projectile", "element"],
            autonomous_weight=2.2,
        ))

        # -------------------------------------------------------------
        # DC: BATMAN
        # -------------------------------------------------------------
        self.register(AbilityDefinition(
            id="batman_grapple",
            name="Grapple & Smoke Escape",
            description="Fires Grapnel gun and vanishes behind a cloud of smoke pellets.",
            character_id="batman",
            primitives=[
                SoundPrimitive(sound_id="smoke_pellet"),
                ParticlePrimitive(duration=0.6, particle_family="smoke_cloud", color=(0.3, 0.3, 0.35, 0.85), count=20),
                MovementPrimitive(duration=0.4, dx=140.0, dy=-50.0, easing="ease_out"),
                RecoveryPrimitive(duration=0.3),
            ],
            cooldown=5.0,
            rarity=RarityTier.UNCOMMON,
            tags=["movement", "defensive", "teleport"],
            autonomous_weight=2.2,
        ))

        # -------------------------------------------------------------
        # PET: CAT
        # -------------------------------------------------------------
        self.register(AbilityDefinition(
            id="cat_pounce",
            name="Curious Pounce",
            description="Wiggles tail, coils hind legs, and pounces toward the cursor with playful energy.",
            character_id="cat",
            primitives=[
                SoundPrimitive(sound_id="cat_purr"),
                MovementPrimitive(duration=0.4, dx=90.0, dy=-30.0, easing="ease_out", target_cursor=True),
                ParticlePrimitive(duration=0.3, particle_family="paw_prints", color=(1.0, 0.8, 0.9, 0.7), count=4),
                RecoveryPrimitive(duration=0.3),
            ],
            cooldown=3.5,
            rarity=RarityTier.COMMON,
            tags=["movement", "interaction"],
            autonomous_weight=3.0,
        ))

        # -------------------------------------------------------------
        # PET: DOG
        # -------------------------------------------------------------
        self.register(AbilityDefinition(
            id="dog_fetch",
            name="Fetch Rush",
            description="Excitedly gallops across the screen chasing virtual treats and fetches happily.",
            character_id="dog",
            primitives=[
                SoundPrimitive(sound_id="dog_bark"),
                MovementPrimitive(duration=0.5, dx=140.0, easing="ease_in_out"),
                ParticlePrimitive(duration=0.4, particle_family="happy_stars", color=(1.0, 0.9, 0.2, 0.9), count=8),
                RecoveryPrimitive(duration=0.25),
            ],
            cooldown=3.5,
            rarity=RarityTier.COMMON,
            tags=["movement", "interaction"],
            autonomous_weight=3.0,
        ))


ability_registry = AbilityRegistry.get_instance()
