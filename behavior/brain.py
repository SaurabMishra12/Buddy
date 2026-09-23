"""
Buddy Companion Brain.

Lightweight local behavior planner implementing the 4-layer behavior hierarchy:
  Layer 1 - Intent (e.g. idle, explore, follow, rest, react, play, celebrate, attack, sleep)
  Layer 2 - Character Behavior (personality-specific actions)
  Layer 3 - Animation (underlying animation state)
  Layer 4 - Ability/VFX (particle / sound / visual flourish)

Driven by mood, desktop context, user idle time, and Pomodoro focus states.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import random
import time
from typing import Any, Dict, List, Optional

from behavior.mood import MoodManager, MoodType


class Intent(str, Enum):
    IDLE = "idle"
    EXPLORE = "explore"
    FOLLOW = "follow"
    REST = "rest"
    REACT = "react"
    PLAY = "play"
    CELEBRATE = "celebrate"
    ATTACK = "attack"
    DEFEND = "defend"
    TRANSFORM = "transform"
    RECOVER = "recover"
    SLEEP = "sleep"


@dataclass
class BehaviorPlan:
    """The 4-layer output produced by the Companion Brain."""
    layer1_intent: Intent
    layer2_character_behavior: str
    layer3_animation: str
    layer4_vfx: Optional[str] = None
    duration: float = 3.0
    sound_cue: Optional[str] = None
    target_x: Optional[float] = None
    target_y: Optional[float] = None


@dataclass
class CharacterPersonality:
    """Personality weights that govern intent distribution."""
    name: str
    idle_variants: List[str] = field(default_factory=lambda: ["idle_default"])
    reactions: List[str] = field(default_factory=lambda: ["look_at_cursor"])
    celebrations: List[str] = field(default_factory=lambda: ["celebrate_jump"])
    curiosity_weight: float = 1.0
    calmness_weight: float = 1.0
    energy_weight: float = 1.0
    aggression_weight: float = 0.5
    playfulness_weight: float = 1.0
    preferred_perch_style: str = "window_top"


# Canonical personality registry
PERSONALITY_PROFILES: Dict[str, CharacterPersonality] = {
    "ichigo": CharacterPersonality(
        name="Ichigo",
        idle_variants=["confident_stance", "sword_adjust", "impatient_glance", "wind_cloak"],
        reactions=["shunpo_dodge", "sword_alert", "direct_gaze"],
        celebrations=["getsuga_salute", "zanpakuto_sheath"],
        curiosity_weight=0.8,
        calmness_weight=1.0,
        energy_weight=1.6,
        aggression_weight=1.2,
        playfulness_weight=0.6,
    ),
    "byakuya": CharacterPersonality(
        name="Byakuya",
        idle_variants=["still_posture", "petal_flutter", "scarf_drift", "calm_observation"],
        reactions=["petal_shield", "dignified_turn", "silent_gaze"],
        celebrations=["petal_orbit_zen", "senkei_sheath"],
        curiosity_weight=0.4,
        calmness_weight=2.0,
        energy_weight=0.6,
        aggression_weight=0.7,
        playfulness_weight=0.2,
    ),
    "aizen": CharacterPersonality(
        name="Aizen",
        idle_variants=["serene_contemplation", "glasses_adjust", "deliberate_gesture"],
        reactions=["illusion_flicker", "subtle_smile"],
        celebrations=["shattered_mirror_ascend"],
        curiosity_weight=0.6,
        calmness_weight=2.5,
        energy_weight=0.5,
        aggression_weight=0.8,
        playfulness_weight=0.1,
    ),
    "yoruichi": CharacterPersonality(
        name="Yoruichi",
        idle_variants=["feline_stretch", "lightning_sparkle", "agile_crouch"],
        reactions=["lightning_dash", "playful_feint"],
        celebrations=["thunder_backflip", "cat_grin"],
        curiosity_weight=1.8,
        calmness_weight=0.8,
        energy_weight=2.0,
        aggression_weight=1.1,
        playfulness_weight=1.9,
    ),
    "cat": CharacterPersonality(
        name="Cat",
        idle_variants=["tail_swish", "ear_twitch", "paws_groom", "yawn_curl"],
        reactions=["curious_tilt", "pounce_stalk", "startled_jump"],
        celebrations=["playful_purr_roll", "high_tail_trot"],
        curiosity_weight=2.5,
        calmness_weight=1.2,
        energy_weight=1.0,
        aggression_weight=0.3,
        playfulness_weight=2.5,
    ),
    "dog": CharacterPersonality(
        name="Dog",
        idle_variants=["tail_wag_pant", "sniff_ground", "happy_tilt", "sit_alert"],
        reactions=["excited_hop", "fetch_ready", "play_bow"],
        celebrations=["spin_bark_joy", "happy_trot"],
        curiosity_weight=2.0,
        calmness_weight=0.7,
        energy_weight=2.2,
        aggression_weight=0.2,
        playfulness_weight=2.8,
    ),
    "thor": CharacterPersonality(
        name="Thor",
        idle_variants=["mjolnir_twirl", "sky_glance", "thunder_aura", "proud_stance"],
        reactions=["hammer_guard", "spark_flash"],
        celebrations=["lightning_strike_cheer"],
        curiosity_weight=0.9,
        calmness_weight=1.1,
        energy_weight=1.8,
        aggression_weight=1.3,
        playfulness_weight=1.2,
    ),
    "spiderman": CharacterPersonality(
        name="Spider-Man",
        idle_variants=["perch_squat", "web_fiddle", "upside_down_hang", "head_scratch"],
        reactions=["spidey_sense_flip", "web_shield", "quick_dodge"],
        celebrations=["finger_guns_swing", "acrobatic_landing"],
        curiosity_weight=2.2,
        calmness_weight=0.9,
        energy_weight=1.8,
        aggression_weight=0.6,
        playfulness_weight=2.2,
    ),
    "batman": CharacterPersonality(
        name="Batman",
        idle_variants=["cape_drape", "vigilant_survey", "grapnel_check"],
        reactions=["smoke_fade", "cape_deflect"],
        celebrations=["shadow_disappear"],
        curiosity_weight=0.8,
        calmness_weight=2.2,
        energy_weight=0.8,
        aggression_weight=1.4,
        playfulness_weight=0.1,
    ),
}

DEFAULT_PERSONALITY = CharacterPersonality(
    name="Companion",
    idle_variants=["idle_breathing", "look_around", "subtle_sway"],
    reactions=["look_at_cursor", "gentle_hop"],
    celebrations=["happy_spin"],
)


class CompanionBrain:
    """Local, lightweight behavior planner driving natural character autonomy."""

    def __init__(self, character_id: str = "ichigo"):
        self.character_id = character_id
        self.mood_manager = MoodManager(MoodType.CALM)
        self.current_plan: Optional[BehaviorPlan] = None
        self.plan_elapsed: float = 0.0
        self.last_interaction_time: float = time.time()
        self.user_idle_seconds: float = 0.0
        self.is_focus_active: bool = False
        self.is_break_active: bool = False

    @property
    def personality(self) -> CharacterPersonality:
        return PERSONALITY_PROFILES.get(self.character_id, DEFAULT_PERSONALITY)

    def set_character(self, character_id: str) -> None:
        self.character_id = character_id
        self.current_plan = None

    def update(
        self,
        dt: float,
        companion_x: float,
        companion_y: float,
        cursor_x: float,
        cursor_y: float,
        behavior_mode: str,
    ) -> BehaviorPlan:
        """Evaluates conditions and generates the current BehaviorPlan."""
        self.mood_manager.update(dt)
        self.plan_elapsed += dt

        # Distance to cursor
        dx = cursor_x - companion_x
        dy = cursor_y - companion_y
        dist = (dx * dx + dy * dy) ** 0.5
        cursor_near = dist < 160.0

        # Plan expiration check
        if self.current_plan is None or self.plan_elapsed >= self.current_plan.duration:
            self.current_plan = self._decide_next_plan(
                companion_x, companion_y, cursor_x, cursor_y, cursor_near, behavior_mode
            )
            self.plan_elapsed = 0.0

        return self.current_plan

    def _decide_next_plan(
        self,
        cx: float,
        cy: float,
        cur_x: float,
        cur_y: float,
        cursor_near: bool,
        behavior_mode: str,
    ) -> BehaviorPlan:
        modifier = self.mood_manager.modifier
        p = self.personality

        # Check for cursor reaction
        if cursor_near and random.random() < (0.45 * modifier.reaction_frequency * p.curiosity_weight):
            reaction_name = random.choice(p.reactions) if p.reactions else "look_at_cursor"
            return BehaviorPlan(
                layer1_intent=Intent.REACT,
                layer2_character_behavior=reaction_name,
                layer3_animation="react",
                layer4_vfx="cursor_spark",
                duration=random.uniform(1.2, 2.2),
                target_x=cur_x,
                target_y=cur_y,
            )

        # Focus / Break special states
        if self.is_break_active and random.random() < 0.6:
            celebration = random.choice(p.celebrations) if p.celebrations else "celebrate_jump"
            return BehaviorPlan(
                layer1_intent=Intent.CELEBRATE,
                layer2_character_behavior=celebration,
                layer3_animation="celebrate",
                layer4_vfx="confetti_burst",
                duration=2.5,
            )

        # Decide between IDLE, EXPLORE, and REST
        weights = {
            Intent.IDLE: 55.0 * p.calmness_weight,
            Intent.EXPLORE: 25.0 * modifier.movement_frequency * p.energy_weight,
            Intent.PLAY: 15.0 * modifier.reaction_frequency * p.playfulness_weight,
            Intent.REST: 10.0 if self.mood_manager.current_mood == MoodType.SLEEPY else 3.0,
        }

        # In static modes, heavily suppress explore
        if behavior_mode in ["static_roam", "draggable", "perch"]:
            weights[Intent.EXPLORE] *= 0.1

        choices = list(weights.keys())
        prob = [weights[k] for k in choices]
        chosen_intent = random.choices(choices, weights=prob, k=1)[0]

        if chosen_intent == Intent.EXPLORE:
            target_dx = random.uniform(-140.0, 140.0)
            return BehaviorPlan(
                layer1_intent=Intent.EXPLORE,
                layer2_character_behavior=f"{p.name.lower()}_wander",
                layer3_animation="walk",
                duration=random.uniform(2.0, 4.0),
                target_x=cx + target_dx,
                target_y=cy,
            )
        elif chosen_intent == Intent.PLAY:
            return BehaviorPlan(
                layer1_intent=Intent.PLAY,
                layer2_character_behavior=random.choice(p.reactions) if p.reactions else "play_hop",
                layer3_animation="react",
                layer4_vfx="heart_bubble",
                duration=random.uniform(1.5, 2.5),
            )
        elif chosen_intent == Intent.REST:
            return BehaviorPlan(
                layer1_intent=Intent.REST,
                layer2_character_behavior="curled_rest",
                layer3_animation="sleep",
                duration=random.uniform(6.0, 15.0),
            )
        else:
            # Idle variant
            idle_name = random.choice(p.idle_variants) if p.idle_variants else "idle_default"
            return BehaviorPlan(
                layer1_intent=Intent.IDLE,
                layer2_character_behavior=idle_name,
                layer3_animation="idle",
                duration=random.uniform(3.0, 6.0),
            )
