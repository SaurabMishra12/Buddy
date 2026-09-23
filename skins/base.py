"""Abstract character interface and base projectile classes for all Buddy skins."""

import math
import random
import cairo
from typing import Tuple, Dict, Any, List, Optional
from core.physics import PhysicsBody


class CharacterState:
    # 30 Standardized Character Animation States
    IDLE = "IDLE"
    IDLE_VARIATION = "IDLE_VARIATION"
    WALK = "WALK"
    RUN = "RUN"
    JUMP_START = "JUMP_START"
    JUMP = "JUMP"
    FALL = "FALL"
    LAND = "LAND"
    SIT = "SIT"
    SLEEP = "SLEEP"
    WAKE = "WAKE"
    LOOK_AROUND = "LOOK_AROUND"
    HAPPY = "HAPPY"
    CONFUSED = "CONFUSED"
    ANNOYED = "ANNOYED"
    SURPRISED = "SURPRISED"
    EXCITED = "EXCITED"
    INTERACT = "INTERACT"
    ATTACK_READY = "ATTACK_READY"
    ATTACK = "ATTACK"
    SPECIAL_READY = "SPECIAL_READY"
    SHIKAI_ACTIVATION = "SHIKAI_ACTIVATION"
    SHIKAI_ACTIVE = "SHIKAI_ACTIVE"
    BANKAI_ACTIVATION = "BANKAI_ACTIVATION"
    BANKAI_ACTIVE = "BANKAI_ACTIVE"
    ULTIMATE = "ULTIMATE"
    DAMAGE = "DAMAGE"
    RECOVERY = "RECOVERY"
    DEACTIVATE = "DEACTIVATE"
    RETURN_TO_IDLE = "RETURN_TO_IDLE"

    # Supported Movement & Productivity Aliases for backwards compatibility
    CHASE = "CHASE"
    SPECIAL = "SPECIAL"
    FLY = "FLY"
    HOVER = "HOVER"
    TAKEOFF = "TAKEOFF"
    LANDING = "LANDING"
    VICTORY = "VICTORY"
    CURIOUS = "CURIOUS"
    PLAY = "PLAY"
    FOLLOW_CURSOR = "FOLLOW_CURSOR"
    CELEBRATE = "CELEBRATE"
    FOCUS = "FOCUS"
    BREAK = "BREAK"
    TIRED = "TIRED"


# Roster of characters canonical to Bleach Universe where Shikai & Bankai apply
BLEACH_CHARACTERS = {
    "ichigo", "byakuya", "yamamoto", "kenpachi", "hitsugaya", "rukia", "urahara",
    "aizen", "yoruichi", "shunsui", "soi_fon", "shinji", "mayuri", "ulquiorra"
}


class CharacterStateMachine:
    """Unified Character Animation State Machine.
    Controls state transitions, durations, and safe returns to IDLE.
    Enforces that Shikai and Bankai transformations are strictly reserved for Bleach characters.
    """

    DEFAULT_DURATIONS = {
        CharacterState.JUMP_START: 0.18,
        CharacterState.JUMP: 0.45,
        CharacterState.FALL: 0.35,
        CharacterState.LAND: 0.22,
        CharacterState.INTERACT: 1.2,
        CharacterState.LOOK_AROUND: 1.8,
        CharacterState.HAPPY: 1.5,
        CharacterState.CONFUSED: 1.6,
        CharacterState.ANNOYED: 1.4,
        CharacterState.SURPRISED: 1.2,
        CharacterState.EXCITED: 1.6,
        CharacterState.ATTACK_READY: 0.4,
        CharacterState.ATTACK: 0.65,
        CharacterState.SPECIAL_READY: 0.5,
        CharacterState.SPECIAL: 1.2,
        CharacterState.SHIKAI_ACTIVATION: 1.5,
        CharacterState.BANKAI_ACTIVATION: 2.2,
        CharacterState.ULTIMATE: 2.5,
        CharacterState.DAMAGE: 0.45,
        CharacterState.RECOVERY: 0.5,
        CharacterState.DEACTIVATE: 0.8,
        CharacterState.RETURN_TO_IDLE: 0.25,
        CharacterState.IDLE_VARIATION: 2.0,
    }

    def __init__(self, character: Any):
        self.character = character
        self.current_state: str = CharacterState.IDLE
        self.previous_state: str = CharacterState.IDLE
        self.next_state: Optional[str] = None
        self.state_time: float = 0.0
        self.state_duration: Optional[float] = None
        self.is_bleach: bool = str(getattr(character, "skin_id", "")).lower() in BLEACH_CHARACTERS

    def transition_to(
        self,
        new_state: str,
        duration: Optional[float] = None,
        next_state: Optional[str] = None
    ) -> bool:
        """Safely transition to a new animation state with transition validation."""
        # Rule: Shikai and Bankai are strictly for Bleach characters
        if not self.is_bleach and new_state in (
            CharacterState.SHIKAI_ACTIVATION, CharacterState.SHIKAI_ACTIVE,
            CharacterState.BANKAI_ACTIVATION, CharacterState.BANKAI_ACTIVE
        ):
            # Gracefully map to appropriate superhero/companion ability state
            if "BANKAI" in new_state:
                new_state = CharacterState.ULTIMATE
            else:
                new_state = CharacterState.SPECIAL_READY

        self.previous_state = self.current_state
        self.current_state = new_state
        self.state_time = 0.0
        self.state_duration = duration if duration is not None else self.DEFAULT_DURATIONS.get(new_state)
        self.next_state = next_state if next_state is not None else self._get_default_next(new_state)

        # Reflect on character attribute
        if hasattr(self.character, "_state"):
            self.character._state = new_state

        return True

    def _get_default_next(self, state: str) -> Optional[str]:
        """Determine what state to transition to after a temporary state expires."""
        if state == CharacterState.JUMP_START:
            return CharacterState.JUMP
        elif state == CharacterState.JUMP:
            return CharacterState.FALL
        elif state == CharacterState.FALL:
            return CharacterState.LAND
        elif state == CharacterState.LAND:
            return CharacterState.IDLE
        elif state == CharacterState.SHIKAI_ACTIVATION:
            return CharacterState.SHIKAI_ACTIVE
        elif state == CharacterState.BANKAI_ACTIVATION:
            return CharacterState.BANKAI_ACTIVE
        elif state in (CharacterState.SHIKAI_ACTIVE, CharacterState.BANKAI_ACTIVE):
            return None  # Persistent mode until deactivated or interrupted
        elif state in (CharacterState.IDLE, CharacterState.HOVER, CharacterState.WALK, CharacterState.RUN, CharacterState.FLY):
            return None  # Sustained states
        elif state == CharacterState.DEACTIVATE:
            return CharacterState.IDLE
        elif state == CharacterState.RETURN_TO_IDLE:
            return CharacterState.IDLE
        else:
            return CharacterState.IDLE

    def update(self, dt: float) -> str:
        """Tick state timer and automatically transition when duration expires."""
        self.state_time += dt
        if self.state_duration is not None and self.state_time >= self.state_duration:
            target = self.next_state if self.next_state else CharacterState.IDLE
            self.transition_to(target)
        return self.current_state

    def is_in_transformation(self) -> bool:
        """Check if character is currently in Shikai or Bankai."""
        return self.current_state in (
            CharacterState.SHIKAI_ACTIVATION, CharacterState.SHIKAI_ACTIVE,
            CharacterState.BANKAI_ACTIVATION, CharacterState.BANKAI_ACTIVE
        )


class BaseProjectile:
    """Base class for character projectiles (Mjolnir, Shield, Batarang, Fireball, Spells)."""

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.angle = 0.0
        self.active = False

    def update(self, dt: float, screen_bounds: Tuple[int, int, int, int], particle_mgr: Any, audio_mgr: Any) -> None:
        pass

    def draw(self, ctx: cairo.Context) -> None:
        pass


class BaseCharacter:
    """Abstract base class for all desktop pet characters."""

    def __init__(self, x: float = 500.0, y: float = 400.0, skin_id: str = "generic"):
        self.skin_id = skin_id
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.facing_right = True
        self._state = CharacterState.IDLE
        self.state_machine = CharacterStateMachine(self)
        self.anim_time = 0.0
        self.scale = 1.0
        self.speed_multiplier = 1.0
        self.tilt = 0.0
        self.can_fly = False
        self.is_airborne = False
        self.hitbox_radius = 35.0
        self.ability_cooldown = 0.0
        self.next_action_time = 0.0
        from behavior.personality import CharacterPersonality
        from behavior.memory import CharacterMemory
        from behavior.state_machine import CharacterBehavior

        self.personality = CharacterPersonality.preset("heroic" if skin_id in ["thor", "ironman", "captain_america", "batman", "superman", "spiderman"] else ("playful" if skin_id in ["cat", "dog"] else "energetic"))
        self.memory = CharacterMemory(skin_id=skin_id)
        self.behavior = CharacterBehavior(skin_id, personality=self.personality, memory=self.memory, can_fly=self.can_fly)

    @property
    def state(self) -> str:
        return self.state_machine.current_state

    @state.setter
    def state(self, new_state: str) -> None:
        self._state = new_state
        if hasattr(self, "state_machine"):
            self.state_machine.current_state = new_state

    def get_hitbox(self) -> Tuple[float, float, float]:
        """Returns (center_x, center_y, radius) in world coordinates."""
        return self.x, self.y, self.hitbox_radius * self.scale

    def update(
        self,
        dt: float,
        cursor_x: float,
        cursor_y: float,
        screen_bounds: Tuple[int, int, int, int],
        particle_mgr: Any,
        audio_mgr: Any,
        config_data: Dict[str, Any]
    ) -> None:
        """Update physics, state transitions, animations, and AI for this character frame."""
        self.state_machine.update(dt)

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        """Render character on cairo context."""
        pass

    def trigger_ability(
        self,
        ability_name: str,
        target_x: float,
        target_y: float,
        particle_mgr: Any,
        audio_mgr: Any
    ) -> bool:
        """Execute a character ability. Returns True if successfully fired."""
        return False

    def on_click(self, button: int, click_x: float, click_y: float) -> None:
        """Handle mouse click interactions (e.g. petting, poke, double click)."""
        pass

    def get_capabilities(self) -> Dict[str, Any]:
        """Return character capabilities (flight, abilities, type)."""
        return {
            "can_fly": self.can_fly,
            "abilities": []
        }
