"""Character personality profile system for Buddy companions."""

from typing import Dict, Any, Optional


class CharacterPersonality:
    """Defines a character's disposition, driving autonomous behavior selection."""

    def __init__(
        self,
        energy: float = 0.7,
        curiosity: float = 0.6,
        playfulness: float = 0.6,
        sleepiness: float = 0.3,
        interaction_rate: float = 0.7,
    ):
        self.energy = max(0.0, min(1.0, float(energy)))
        self.curiosity = max(0.0, min(1.0, float(curiosity)))
        self.playfulness = max(0.0, min(1.0, float(playfulness)))
        self.sleepiness = max(0.0, min(1.0, float(sleepiness)))
        self.interaction_rate = max(0.0, min(1.0, float(interaction_rate)))

    def to_dict(self) -> Dict[str, float]:
        """Serialize to dictionary."""
        return {
            "energy": round(self.energy, 2),
            "curiosity": round(self.curiosity, 2),
            "playfulness": round(self.playfulness, 2),
            "sleepiness": round(self.sleepiness, 2),
            "interaction_rate": round(self.interaction_rate, 2),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "CharacterPersonality":
        """Instantiate from dictionary with safe fallbacks."""
        if not isinstance(data, dict):
            return cls()
        return cls(
            energy=data.get("energy", 0.7),
            curiosity=data.get("curiosity", 0.6),
            playfulness=data.get("playfulness", 0.6),
            sleepiness=data.get("sleepiness", 0.3),
            interaction_rate=data.get("interaction_rate", 0.7),
        )

    @classmethod
    def preset(cls, name: str) -> "CharacterPersonality":
        """Predefined archetypes for quick assignment."""
        presets = {
            "energetic": cls(energy=0.95, curiosity=0.8, playfulness=0.9, sleepiness=0.15, interaction_rate=0.85),
            "sleepy": cls(energy=0.3, curiosity=0.3, playfulness=0.2, sleepiness=0.85, interaction_rate=0.4),
            "curious": cls(energy=0.75, curiosity=0.95, playfulness=0.7, sleepiness=0.25, interaction_rate=0.8),
            "playful": cls(energy=0.85, curiosity=0.7, playfulness=0.95, sleepiness=0.3, interaction_rate=0.9),
            "stoic": cls(energy=0.6, curiosity=0.4, playfulness=0.2, sleepiness=0.3, interaction_rate=0.5),
            "scholarly": cls(energy=0.5, curiosity=0.9, playfulness=0.4, sleepiness=0.4, interaction_rate=0.6),
            "heroic": cls(energy=0.88, curiosity=0.65, playfulness=0.5, sleepiness=0.2, interaction_rate=0.75),
        }
        return presets.get(name.lower(), cls())

    def get_wander_chance(self, activity_level: float = 1.0) -> float:
        """Probability per check of starting a wander motion."""
        return (0.3 + 0.5 * self.energy) * activity_level

    def get_sleep_chance(self) -> float:
        """Probability of transitioning to sleep when idle."""
        return 0.1 + 0.6 * self.sleepiness

    def get_cursor_investigate_distance(self) -> float:
        """Distance threshold at which curious character turns to inspect cursor."""
        return 120.0 + 160.0 * self.curiosity
