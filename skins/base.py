"""Abstract character interface and base projectile classes for all Buddy skins."""

import math
import random
import cairo
from typing import Tuple, Dict, Any, List, Optional
from core.physics import PhysicsBody


class CharacterState:
    IDLE = "IDLE"
    WALK = "WALK"
    RUN = "RUN"
    CHASE = "CHASE"
    JUMP = "JUMP"
    FALL = "FALL"
    LAND = "LAND"
    ATTACK = "ATTACK"
    SPECIAL = "SPECIAL"
    FLY = "FLY"
    HOVER = "HOVER"
    TAKEOFF = "TAKEOFF"
    LANDING = "LANDING"
    SLEEP = "SLEEP"
    SIT = "SIT"
    INTERACT = "INTERACT"
    VICTORY = "VICTORY"
    # Buddy 2.0 states
    CURIOUS = "CURIOUS"
    PLAY = "PLAY"
    FOLLOW_CURSOR = "FOLLOW_CURSOR"
    CELEBRATE = "CELEBRATE"
    FOCUS = "FOCUS"
    BREAK = "BREAK"
    TIRED = "TIRED"
    CONFUSED = "CONFUSED"
    EXCITED = "EXCITED"


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
        self.state = CharacterState.IDLE
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
        raise NotImplementedError("Subclasses must implement update()")

    def draw(self, ctx: cairo.Context, particle_mgr: Any) -> None:
        """Render character on cairo context."""
        raise NotImplementedError("Subclasses must implement draw()")

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
