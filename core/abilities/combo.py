"""
Buddy Ability Combo Engine.

Allows chaining compatible abilities based on semantic tags:
movement -> melee -> finisher
teleport -> projectile -> recovery
projectile -> area -> ultimate
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import time

from core.abilities.ability import AbilityDefinition, AbilityRegistry, AbilityRunner
from core.abilities.primitives import AbilityExecutionContext


# Tag transition compatibility graph
VALID_COMBO_TRANSITIONS: Dict[str, List[str]] = {
    "movement": ["melee", "projectile", "teleport", "acrobatic"],
    "teleport": ["melee", "projectile", "area", "transformation"],
    "melee": ["projectile", "area", "movement", "finisher"],
    "projectile": ["movement", "area", "teleport", "finisher"],
    "area": ["finisher", "ultimate", "teleport"],
    "acrobatic": ["melee", "projectile", "movement"],
    "transformation": ["area", "melee", "ultimate", "finisher"],
    "element": ["melee", "projectile", "area"],
}


@dataclass
class ComboSequence:
    """A series of chained abilities forming an active combo."""
    abilities: List[AbilityDefinition]
    character_id: str
    current_index: int = 0
    current_runner: Optional[AbilityRunner] = None
    started_at: float = field(default_factory=time.time)
    completed: bool = False

    @property
    def total_steps(self) -> int:
        return len(self.abilities)

    @property
    def current_ability(self) -> Optional[AbilityDefinition]:
        if 0 <= self.current_index < len(self.abilities):
            return self.abilities[self.current_index]
        return None


class ComboEngine:
    """Evaluates ability compatibility and manages autonomous or manual combo chains."""

    def __init__(self, registry: Optional[AbilityRegistry] = None):
        self.registry = registry or AbilityRegistry.get_instance()
        self.active_combo: Optional[ComboSequence] = None

    def can_chain(self, first: AbilityDefinition, next_ability: AbilityDefinition) -> bool:
        """Determines if next_ability can naturally chain after first."""
        # Cannot chain same ability immediately
        if first.id == next_ability.id:
            return False

        # Check tag matches
        for tag in first.tags:
            allowed_next = VALID_COMBO_TRANSITIONS.get(tag, [])
            for next_tag in next_ability.tags:
                if next_tag in allowed_next:
                    return True
        return False

    def build_combo(self, character_id: str, max_chain: int = 3) -> Optional[ComboSequence]:
        """Finds a valid chain of abilities for a character."""
        char_abilities = self.registry.get_by_character(character_id)
        if not char_abilities:
            return None

        # Prefer starting with movement, teleport, or melee
        starters = [
            ab for ab in char_abilities
            if any(t in ["movement", "teleport", "melee", "acrobatic"] for t in ab.tags)
            and ab.is_ready()
        ]
        if not starters:
            starters = [ab for ab in char_abilities if ab.is_ready()]
        if not starters:
            return None

        chain: List[AbilityDefinition] = [starters[0]]
        current = starters[0]

        while len(chain) < max_chain:
            candidates = [
                ab for ab in char_abilities
                if ab not in chain and self.can_chain(current, ab) and ab.is_ready()
            ]
            if not candidates:
                break
            # Pick candidate with highest weight or least cooldown
            chosen = sorted(candidates, key=lambda a: a.autonomous_weight, reverse=True)[0]
            chain.append(chosen)
            current = chosen

        if len(chain) >= 2:
            return ComboSequence(abilities=chain, character_id=character_id)
        return None

    def start_combo(self, combo: ComboSequence, initial_ctx: AbilityExecutionContext) -> None:
        self.active_combo = combo
        if combo.abilities:
            combo.current_index = 0
            first_ab = combo.abilities[0]
            first_ab.trigger()
            combo.current_runner = AbilityRunner(first_ab, initial_ctx)

    def update(self, dt: float, ctx_provider_cb) -> Optional[AbilityExecutionContext]:
        """Updates active combo step. Returns current execution context or None."""
        if not self.active_combo or self.active_combo.completed:
            return None

        combo = self.active_combo
        runner = combo.current_runner
        if runner:
            runner.update(dt)
            if runner.completed:
                # Advance to next ability in combo
                combo.current_index += 1
                if combo.current_index < len(combo.abilities):
                    next_ab = combo.abilities[combo.current_index]
                    next_ab.trigger()
                    new_ctx = ctx_provider_cb()
                    combo.current_runner = AbilityRunner(next_ab, new_ctx)
                else:
                    combo.completed = True
                    self.active_combo = None
            return runner.ctx
        return None

    def cancel(self) -> None:
        self.active_combo = None


combo_engine = ComboEngine()
