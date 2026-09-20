"""Behavior engine and state machine for Buddy companions."""

import math
import random
import time
from typing import Dict, Any, Optional, Tuple, Callable, List

from behavior.personality import CharacterPersonality
from behavior.memory import CharacterMemory


class BehaviorState:
    """Comprehensive companion states for Buddy 2.0."""
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
    # Buddy 2.0 Enhanced States
    CURIOUS = "CURIOUS"
    PLAY = "PLAY"
    FOLLOW_CURSOR = "FOLLOW_CURSOR"
    CELEBRATE = "CELEBRATE"
    FOCUS = "FOCUS"
    BREAK = "BREAK"
    TIRED = "TIRED"
    CONFUSED = "CONFUSED"
    EXCITED = "EXCITED"


class CharacterBehavior:
    """Coordinates personality-driven state transitions, attention, and reactions."""

    def __init__(
        self,
        character_name: str,
        personality: Optional[CharacterPersonality] = None,
        memory: Optional[CharacterMemory] = None,
        can_fly: bool = False,
    ):
        self.character_name = character_name
        self.personality = personality or CharacterPersonality()
        self.memory = memory
        self.can_fly = can_fly

        # State tracking
        self.current_state: str = BehaviorState.IDLE
        self.previous_state: str = BehaviorState.IDLE
        self.state_time: float = 0.0
        self.state_duration: float = random.uniform(2.5, 5.0)

        # Attention & Kinematics targets
        self.target_x: float = 500.0
        self.target_y: float = 400.0
        self.attention_target: Optional[Tuple[float, float]] = None
        self.is_focusing_pomodoro: bool = False
        self.is_in_break: bool = False

        # Internal state change listeners
        self._listeners: List[Callable[[str, str], None]] = []

    def add_listener(self, callback: Callable[[str, str], None]) -> None:
        """Register listener callback(old_state, new_state)."""
        self._listeners.append(callback)

    def transition_to(self, new_state: str, duration: Optional[float] = None) -> None:
        """Execute formal state transition."""
        if new_state == self.current_state and duration is None:
            return

        old_state = self.current_state
        self.previous_state = old_state
        self.current_state = new_state
        self.state_time = 0.0

        if duration is not None:
            self.state_duration = duration
        else:
            self.state_duration = self._calculate_default_duration(new_state)

        for listener in self._listeners:
            try:
                listener(old_state, new_state)
            except Exception:
                pass

    def _calculate_default_duration(self, state: str) -> float:
        """Set realistic natural durations based on state and personality."""
        if state == BehaviorState.SLEEP:
            # Sleepy companions sleep longer
            return random.uniform(8.0, 20.0) * (0.8 + 0.6 * self.personality.sleepiness)
        elif state == BehaviorState.CURIOUS:
            return random.uniform(1.2, 2.5)
        elif state == BehaviorState.CELEBRATE:
            return random.uniform(2.5, 4.0)
        elif state in (BehaviorState.WALK, BehaviorState.FLY):
            return random.uniform(2.0, 5.0) * (0.8 + 0.4 * self.personality.energy)
        elif state == BehaviorState.FOCUS:
            return 999999.0  # Kept until pomodoro changes
        elif state == BehaviorState.BREAK:
            return 999999.0  # Kept until break changes
        elif state == BehaviorState.SPECIAL:
            return 1.5
        elif state == BehaviorState.CONFUSED:
            return 1.8
        elif state == BehaviorState.EXCITED:
            return random.uniform(2.0, 3.5)
        else:
            # Idle duration inversely proportional to energy
            return random.uniform(2.0, 6.0) / max(0.2, self.personality.energy)

    def evaluate_next_action(
        self,
        dt: float,
        char_x: float,
        char_y: float,
        cursor_x: float,
        cursor_y: float,
        cursor_speed: float,
        screen_bounds: Tuple[int, int, int, int],
        pomodoro_state: str = "IDLE",
        activity_level: float = 1.0,
    ) -> None:
        """Master autonomous decision loop invoked every tick."""
        self.state_time += dt
        if self.memory:
            self.memory.record_time(dt, char_x, char_y)

        min_x, min_y, screen_w, screen_h = screen_bounds
        dist_to_cursor = math.hypot(cursor_x - char_x, cursor_y - char_y)

        # 1. Pomodoro Focus Override
        if pomodoro_state == "WORK":
            self.is_focusing_pomodoro = True
            self.is_in_break = False
            if self.current_state != BehaviorState.FOCUS:
                self.transition_to(BehaviorState.FOCUS)
                # Rest calmly near bottom or bottom-right
                self.target_x = min_x + screen_w - 180.0
                self.target_y = min_y + screen_h - 90.0
            return

        # 2. Pomodoro Break Override
        elif pomodoro_state in ("SHORT_BREAK", "LONG_BREAK"):
            self.is_focusing_pomodoro = False
            self.is_in_break = True
            if self.current_state not in (BehaviorState.BREAK, BehaviorState.CELEBRATE, BehaviorState.PLAY):
                self.transition_to(BehaviorState.BREAK)
            # Pick joyful playful targets during break
            if self.state_time >= self.state_duration:
                self.state_time = 0.0
                self.state_duration = random.uniform(1.8, 3.5)
                self.target_x = random.uniform(min_x + 80.0, min_x + screen_w - 80.0)
                self.target_y = random.uniform(min_y + 80.0, min_y + screen_h - 90.0) if self.can_fly else min_y + screen_h - 70.0
            return

        # Regular autonomous companion mode
        self.is_focusing_pomodoro = False
        self.is_in_break = False

        # 3. Cursor proximity interaction
        if dist_to_cursor < 45.0:
            # Cursor is right on pet — wake up if sleeping, or enter playful/interact state
            if self.current_state == BehaviorState.SLEEP:
                self.transition_to(BehaviorState.CONFUSED, duration=1.2)
            return

        # 4. Curiosity check when cursor moves quickly nearby
        investigate_dist = self.personality.get_cursor_investigate_distance()
        if 60.0 < dist_to_cursor < investigate_dist and cursor_speed > 300.0:
            if random.random() < self.personality.curiosity * 0.4 and self.current_state in (BehaviorState.IDLE, BehaviorState.SIT):
                self.transition_to(BehaviorState.CURIOUS, duration=1.6)
                self.attention_target = (cursor_x, cursor_y)
                return

        # 5. State expiration & next state selection
        if self.state_time >= self.state_duration:
            self._select_next_state(char_x, char_y, cursor_x, cursor_y, screen_bounds, activity_level)

    def _select_next_state(
        self,
        char_x: float,
        char_y: float,
        cursor_x: float,
        cursor_y: float,
        screen_bounds: Tuple[int, int, int, int],
        activity_level: float,
    ) -> None:
        """Select next natural state according to personality profile."""
        min_x, min_y, screen_w, screen_h = screen_bounds
        ground_y = min_y + screen_h - 70.0

        if self.current_state == BehaviorState.SLEEP:
            # Waking up
            self.transition_to(BehaviorState.IDLE, duration=random.uniform(2.0, 4.0))
            return

        if self.current_state in (BehaviorState.CURIOUS, BehaviorState.CONFUSED, BehaviorState.EXCITED):
            self.transition_to(BehaviorState.IDLE)
            return

        # Roll chance to sleep
        if random.random() < (self.personality.get_sleep_chance() * 0.35) and activity_level <= 1.2:
            self.transition_to(BehaviorState.SLEEP)
            return

        # Roll chance to wander or play
        wander_chance = self.personality.get_wander_chance(activity_level)
        if random.random() < wander_chance:
            # Pick wander destination
            if self.can_fly:
                self.target_x = random.uniform(min_x + 90.0, min_x + screen_w - 90.0)
                self.target_y = random.uniform(min_y + 90.0, ground_y - 20.0)
                self.transition_to(BehaviorState.FLY)
            else:
                self.target_x = random.uniform(min_x + 90.0, min_x + screen_w - 90.0)
                # Roam naturally in 2D around current area or desktop floor
                self.target_y = max(min_y + 80.0, min(ground_y, char_y + random.uniform(-150.0, 150.0)))
                # High energy might run, moderate energy walks
                if self.personality.energy > 0.75 and random.random() < 0.4:
                    self.transition_to(BehaviorState.RUN)
                else:
                    self.transition_to(BehaviorState.WALK)
        else:
            # Sit or Idle
            next_st = BehaviorState.SIT if (self.personality.energy < 0.5 and random.random() < 0.5) else BehaviorState.IDLE
            self.transition_to(next_st)
