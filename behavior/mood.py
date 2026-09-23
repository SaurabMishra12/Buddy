"""
Buddy Companion Mood Presentation Layer.

Mood acts as a behavioral modifier rather than a rigid state machine.
Affects idle animation selection, movement speed/frequency, reaction frequency,
VFX intensity, and sound probability.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple


class MoodType(str, Enum):
    CALM = "calm"
    HAPPY = "happy"
    CURIOUS = "curious"
    EXCITED = "excited"
    SLEEPY = "sleepy"
    ANNOYED = "annoyed"
    FOCUSED = "focused"
    ENERGIZED = "energized"


@dataclass
class MoodModifier:
    """Multipliers and presentation offsets applied by mood."""
    movement_frequency: float = 1.0  # multiplier for how often Buddy wanders
    movement_speed: float = 1.0      # multiplier for walk/dash velocity
    reaction_frequency: float = 1.0  # how sensitive to mouse/keyboard interactions
    vfx_intensity: float = 1.0       # multiplier for particle density and aura glow
    sound_frequency: float = 1.0     # multiplier for sound triggers
    idle_stretch_delay: float = 8.0  # average seconds between idle flourishes


MOOD_PROFILES: Dict[MoodType, MoodModifier] = {
    MoodType.CALM: MoodModifier(
        movement_frequency=0.5,
        movement_speed=0.8,
        reaction_frequency=0.7,
        vfx_intensity=0.8,
        sound_frequency=0.5,
        idle_stretch_delay=12.0,
    ),
    MoodType.HAPPY: MoodModifier(
        movement_frequency=1.2,
        movement_speed=1.1,
        reaction_frequency=1.3,
        vfx_intensity=1.1,
        sound_frequency=1.2,
        idle_stretch_delay=6.0,
    ),
    MoodType.CURIOUS: MoodModifier(
        movement_frequency=1.4,
        movement_speed=1.0,
        reaction_frequency=1.8,  # very responsive to cursor
        vfx_intensity=1.0,
        sound_frequency=1.0,
        idle_stretch_delay=5.0,
    ),
    MoodType.EXCITED: MoodModifier(
        movement_frequency=1.8,
        movement_speed=1.4,
        reaction_frequency=1.9,
        vfx_intensity=1.4,
        sound_frequency=1.5,
        idle_stretch_delay=3.5,
    ),
    MoodType.SLEEPY: MoodModifier(
        movement_frequency=0.15,
        movement_speed=0.5,
        reaction_frequency=0.2,
        vfx_intensity=0.4,
        sound_frequency=0.2,
        idle_stretch_delay=20.0,
    ),
    MoodType.ANNOYED: MoodModifier(
        movement_frequency=0.7,
        movement_speed=1.2,
        reaction_frequency=0.6,
        vfx_intensity=1.2,
        sound_frequency=0.8,
        idle_stretch_delay=10.0,
    ),
    MoodType.FOCUSED: MoodModifier(
        movement_frequency=0.3,
        movement_speed=0.9,
        reaction_frequency=0.3,
        vfx_intensity=0.6,
        sound_frequency=0.2,  # stays quiet during focus
        idle_stretch_delay=15.0,
    ),
    MoodType.ENERGIZED: MoodModifier(
        movement_frequency=1.6,
        movement_speed=1.3,
        reaction_frequency=1.5,
        vfx_intensity=1.3,
        sound_frequency=1.3,
        idle_stretch_delay=4.0,
    ),
}


class MoodManager:
    """Tracks and transitions companion mood dynamically."""

    def __init__(self, initial_mood: MoodType = MoodType.CALM):
        self.current_mood = initial_mood
        self._mood_duration: float = 0.0

    @property
    def modifier(self) -> MoodModifier:
        return MOOD_PROFILES.get(self.current_mood, MOOD_PROFILES[MoodType.CALM])

    def set_mood(self, mood: MoodType) -> None:
        self.current_mood = mood
        self._mood_duration = 0.0

    def update(self, dt: float) -> None:
        self._mood_duration += dt

    def evaluate_mood(
        self,
        idle_seconds: float,
        is_focus_active: bool,
        is_break_active: bool,
        mouse_active: bool,
        battery_low: bool,
    ) -> None:
        """Adapts mood contextually based on user state."""
        if battery_low:
            if self.current_mood != MoodType.SLEEPY:
                self.set_mood(MoodType.SLEEPY)
            return

        if is_focus_active:
            if self.current_mood != MoodType.FOCUSED:
                self.set_mood(MoodType.FOCUSED)
            return

        if is_break_active:
            if self.current_mood != MoodType.HAPPY:
                self.set_mood(MoodType.HAPPY)
            return

        if idle_seconds > 180.0:
            if self.current_mood != MoodType.SLEEPY:
                self.set_mood(MoodType.SLEEPY)
        elif mouse_active and self.current_mood == MoodType.SLEEPY:
            self.set_mood(MoodType.CALM)
