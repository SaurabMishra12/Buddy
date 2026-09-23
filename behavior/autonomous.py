"""
Buddy Autonomous Ability System.

Governed by the Companion Brain to enable lifelike autonomous ability usage:
- Modes: MANUAL, OCCASIONAL (default), ACTIVE, CHAOS
- Contextual selection considering personality, mood, cooldowns, and rarity
- Anti-annoyance cooldowns and smart suppression during typing, focus, and low-power modes
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import random
import time
from typing import Dict, List, Optional

from behavior.brain import CompanionBrain, Intent
from behavior.mood import MoodType
from core.abilities.ability import AbilityDefinition, AbilityRegistry, RarityTier
from core.abilities.combo import ComboEngine, ComboSequence


class AutonomousMode(str, Enum):
    OFF = "off"                  # abilities completely disabled
    MANUAL = "manual"            # abilities only fire via manual user action
    OCCASIONAL = "occasional"    # default: gentle, occasional signature flourishes
    ACTIVE = "active"            # regular abilities during exploration and idle
    CHAOS = "chaos"              # playground mode: high frequency combos and powers


@dataclass
class AutonomousSettings:
    mode: AutonomousMode = AutonomousMode.OCCASIONAL
    global_cooldown: float = 12.0       # minimum seconds between any autonomous abilities
    ultimate_cooldown: float = 60.0     # minimum seconds between autonomous ultimates
    vfx_intensity: float = 1.0
    sound_enabled: bool = True
    combos_enabled: bool = True


class AutonomousAbilityManager:
    """Orchestrates intelligent, non-disruptive autonomous ability execution."""

    def __init__(
        self,
        brain: CompanionBrain,
        combo_engine: Optional[ComboEngine] = None,
        registry: Optional[AbilityRegistry] = None,
    ):
        self.brain = brain
        self.combo_engine = combo_engine or ComboEngine()
        self.registry = registry or AbilityRegistry.get_instance()
        self.settings = AutonomousSettings()

        self.last_ability_time: float = 0.0
        self.last_ultimate_time: float = 0.0
        self.recent_abilities: List[str] = []

        # Smart suppression state
        self.user_typing_active: bool = False
        self.battery_low: bool = False
        self.focus_mode_active: bool = False

    def update(
        self,
        dt: float,
        character_id: str,
        now: Optional[float] = None,
    ) -> Optional[AbilityDefinition]:
        """
        Periodically evaluates if an autonomous ability should trigger.
        Returns the chosen AbilityDefinition, or None.
        """
        current_time = now if now is not None else time.time()

        if self.settings.mode in (AutonomousMode.MANUAL, AutonomousMode.OFF):
            return None

        # Smart suppression checks
        if self.user_typing_active or self.battery_low or self.focus_mode_active:
            return None

        # Check global delay based on mode
        delay_threshold = self._get_mode_delay()
        if (current_time - self.last_ability_time) < delay_threshold:
            return None

        # Fetch eligible abilities for character
        abilities = self.registry.get_by_character(character_id)
        ready_abilities = [ab for ab in abilities if ab.is_ready(current_time)]
        if not ready_abilities:
            return None

        # Weighted selection based on rarity, mood, and personality
        chosen = self._select_weighted_ability(ready_abilities, current_time)
        if chosen:
            chosen.trigger(current_time)
            self.last_ability_time = current_time
            if chosen.rarity == RarityTier.ULTIMATE:
                self.last_ultimate_time = current_time

            self.recent_abilities.append(chosen.id)
            if len(self.recent_abilities) > 5:
                self.recent_abilities.pop(0)

            return chosen

        return None

    def _get_mode_delay(self) -> float:
        if self.settings.mode == AutonomousMode.CHAOS:
            return 4.0
        elif self.settings.mode == AutonomousMode.ACTIVE:
            return 8.0
        else:  # OCCASIONAL
            return max(self.settings.global_cooldown, 14.0)

    def _select_weighted_ability(
        self,
        abilities: List[AbilityDefinition],
        current_time: float,
    ) -> Optional[AbilityDefinition]:
        weights: List[float] = []
        candidates: List[AbilityDefinition] = []

        mood_mod = self.brain.mood_manager.modifier
        personality = self.brain.personality

        for ab in abilities:
            # Respect ultimate cooldown
            if ab.rarity == RarityTier.ULTIMATE:
                if (current_time - self.last_ultimate_time) < self.settings.ultimate_cooldown:
                    continue
                if self.settings.mode == AutonomousMode.OCCASIONAL and random.random() > 0.15:
                    continue

            # Anti-repetition penalty
            repeat_penalty = 0.3 if ab.id in self.recent_abilities else 1.0

            # Base weight by rarity
            rarity_multiplier = 1.0
            if ab.rarity == RarityTier.COMMON:
                rarity_multiplier = 3.0
            elif ab.rarity == RarityTier.UNCOMMON:
                rarity_multiplier = 2.0
            elif ab.rarity == RarityTier.RARE:
                rarity_multiplier = 1.0
            elif ab.rarity == RarityTier.EPIC:
                rarity_multiplier = 0.5
            elif ab.rarity == RarityTier.ULTIMATE:
                rarity_multiplier = 0.15

            w = ab.autonomous_weight * rarity_multiplier * repeat_penalty * mood_mod.vfx_intensity
            candidates.append(ab)
            weights.append(w)

        if not candidates or sum(weights) <= 0.0:
            return None

        return random.choices(candidates, weights=weights, k=1)[0]
