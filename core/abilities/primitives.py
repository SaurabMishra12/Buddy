"""
Buddy Composable Ability Primitives.

Reusable, modular execution primitives for character abilities:
- MovementPrimitive
- ChargePrimitive
- ProjectilePrimitive
- BeamPrimitive
- MeleePrimitive
- AreaEffectPrimitive
- ShieldPrimitive
- TeleportPrimitive
- TransformationPrimitive
- ParticlePrimitive
- SoundPrimitive
- RecoveryPrimitive
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class AbilityExecutionContext:
    """Context passed across primitive execution steps."""
    character_id: str
    companion_x: float
    companion_y: float
    companion_scale: float
    facing_right: bool
    target_x: Optional[float] = None
    target_y: Optional[float] = None
    elapsed_time: float = 0.0
    duration: float = 1.0
    phase_data: Dict[str, Any] = field(default_factory=dict)
    particles_to_spawn: List[Dict[str, Any]] = field(default_factory=list)
    sounds_to_play: List[Dict[str, Any]] = field(default_factory=list)
    screen_shake: float = 0.0
    completed: bool = False


class AbilityPrimitive:
    """Base class for all ability primitives."""

    def __init__(self, name: str, duration: float = 0.5):
        self.name = name
        self.duration = max(0.01, duration)
        self.completed = False

    def reset(self) -> None:
        """Reset execution state for clean reuse across ability invocations."""
        self.completed = False

    def execute(self, ctx: AbilityExecutionContext, progress: float) -> None:
        """
        Progress goes from 0.0 to 1.0 over this primitive's duration.
        Subclasses override to apply effects, spawn particles, move, etc.
        """
        pass


class MovementPrimitive(AbilityPrimitive):
    """Controls character movement, dashes, lunges, and leaps."""

    def __init__(
        self,
        name: str = "movement",
        duration: float = 0.4,
        dx: float = 0.0,
        dy: float = 0.0,
        easing: str = "ease_out",  # linear, ease_in, ease_out, ease_in_out
        target_cursor: bool = False,
    ):
        super().__init__(name, duration)
        self.dx = dx
        self.dy = dy
        self.easing = easing
        self.target_cursor = target_cursor

    def _ease(self, t: float) -> float:
        if self.easing == "ease_in":
            return t * t
        elif self.easing == "ease_out":
            return 1.0 - (1.0 - t) * (1.0 - t)
        elif self.easing == "ease_in_out":
            return 0.5 * (1.0 - math.cos(math.pi * t))
        return t

    def execute(self, ctx: AbilityExecutionContext, progress: float) -> None:
        factor = self._ease(progress)
        direction = 1.0 if ctx.facing_right else -1.0
        
        target_dx = self.dx * direction
        target_dy = self.dy
        
        if self.target_cursor and ctx.target_x is not None and ctx.target_y is not None:
            target_dx = (ctx.target_x - ctx.companion_x) * 0.5
            target_dy = (ctx.target_y - ctx.companion_y) * 0.5

        ctx.phase_data["offset_x"] = target_dx * factor
        ctx.phase_data["offset_y"] = target_dy * factor


class ChargePrimitive(AbilityPrimitive):
    """Energy charging phase with gathering particles and aura glow."""

    def __init__(
        self,
        name: str = "charge",
        duration: float = 0.8,
        particle_type: str = "energy_gather",
        color: tuple = (0.3, 0.7, 1.0, 0.8),
        intensity: float = 1.0,
        sound: Optional[str] = "charge",
    ):
        super().__init__(name, duration)
        self.particle_type = particle_type
        self.color = color
        self.intensity = intensity
        self.sound = sound
        self._sound_played = False
        self._last_spawn_time = 0.0

    def reset(self) -> None:
        super().reset()
        self._sound_played = False
        self._last_spawn_time = 0.0

    def execute(self, ctx: AbilityExecutionContext, progress: float) -> None:
        if not self._sound_played and self.sound:
            ctx.sounds_to_play.append({"sound": self.sound, "volume": 0.8 * self.intensity})
            self._sound_played = True

        ctx.phase_data["aura_intensity"] = progress * self.intensity
        ctx.phase_data["aura_color"] = self.color
        
        # Throttle inward collapsing particles to at most once every 0.1s
        if ctx.elapsed_time - self._last_spawn_time >= 0.1:
            self._last_spawn_time = ctx.elapsed_time
            ctx.particles_to_spawn.append({
                "type": self.particle_type,
                "x": ctx.companion_x,
                "y": ctx.companion_y,
                "color": self.color,
                "rate": max(1, int(4 * progress * self.intensity)),
                "inward": True,
            })


class ProjectilePrimitive(AbilityPrimitive):
    """Creates a flying projectile (Getsuga, Batarang, Repulsor, Fireball, Web Shot)."""

    def __init__(
        self,
        name: str = "projectile",
        duration: float = 1.0,
        projectile_type: str = "energy_slash",
        speed: float = 400.0,
        angle_deg: float = 0.0,
        color: tuple = (0.2, 0.8, 1.0, 0.9),
        scale: float = 1.0,
        piercing: bool = False,
        sound: Optional[str] = "projectile_fire",
    ):
        super().__init__(name, duration)
        self.projectile_type = projectile_type
        self.speed = speed
        self.angle_deg = angle_deg
        self.color = color
        self.scale = scale
        self.piercing = piercing
        self.sound = sound
        self._fired = False
        self._last_trail_time = 0.0

    def reset(self) -> None:
        super().reset()
        self._fired = False
        self._last_trail_time = 0.0

    def execute(self, ctx: AbilityExecutionContext, progress: float) -> None:
        direction = 1.0 if ctx.facing_right else -1.0
        if not self._fired:
            if self.sound:
                ctx.sounds_to_play.append({"sound": self.sound, "volume": 0.9})
            self._fired = True

        dist = progress * self.speed * self.duration
        proj_x = ctx.companion_x + direction * dist * math.cos(math.radians(self.angle_deg))
        proj_y = ctx.companion_y - dist * math.sin(math.radians(self.angle_deg))

        ctx.phase_data["projectile"] = {
            "type": self.projectile_type,
            "x": proj_x,
            "y": proj_y,
            "facing_right": ctx.facing_right,
            "color": self.color,
            "scale": self.scale,
            "progress": progress,
        }

        # Projectile trail particles throttled to once every 0.08s
        if ctx.elapsed_time - self._last_trail_time >= 0.08:
            self._last_trail_time = ctx.elapsed_time
            ctx.particles_to_spawn.append({
                "type": "trail",
                "x": proj_x,
                "y": proj_y,
                "color": self.color,
                "rate": 2,
            })


class BeamPrimitive(AbilityPrimitive):
    """Continuous laser / energy beam / Cero / Repulsor stream."""

    def __init__(
        self,
        name: str = "beam",
        duration: float = 1.2,
        beam_type: str = "energy_beam",
        length: float = 500.0,
        width: float = 24.0,
        color: tuple = (1.0, 0.2, 0.2, 0.9),
        sound: Optional[str] = "beam_fire",
    ):
        super().__init__(name, duration)
        self.beam_type = beam_type
        self.length = length
        self.width = width
        self.color = color
        self.sound = sound
        self._sound_played = False

    def reset(self) -> None:
        super().reset()
        self._sound_played = False

    def execute(self, ctx: AbilityExecutionContext, progress: float) -> None:
        if not self._sound_played and self.sound:
            ctx.sounds_to_play.append({"sound": self.sound, "volume": 1.0})
            self._sound_played = True

        # Width ramps up then tapers down
        current_width = math.sin(progress * math.pi) * self.width
        direction = 1.0 if ctx.facing_right else -1.0

        ctx.phase_data["beam"] = {
            "type": self.beam_type,
            "start_x": ctx.companion_x,
            "start_y": ctx.companion_y,
            "end_x": ctx.companion_x + direction * self.length,
            "end_y": ctx.companion_y,
            "width": current_width,
            "color": self.color,
        }
        ctx.screen_shake = max(ctx.screen_shake, current_width * 0.15)


class MeleePrimitive(AbilityPrimitive):
    """Sword slash, claw swipe, hammer hit, shield bash."""

    def __init__(
        self,
        name: str = "melee",
        duration: float = 0.35,
        slash_type: str = "arc_slash",
        radius: float = 80.0,
        color: tuple = (1.0, 1.0, 1.0, 0.9),
        sound: Optional[str] = "slash",
    ):
        super().__init__(name, duration)
        self.slash_type = slash_type
        self.radius = radius
        self.color = color
        self.sound = sound
        self._sound_played = False

    def reset(self) -> None:
        super().reset()
        self._sound_played = False

    def execute(self, ctx: AbilityExecutionContext, progress: float) -> None:
        if not self._sound_played and self.sound:
            ctx.sounds_to_play.append({"sound": self.sound, "volume": 0.85})
            self._sound_played = True

        ctx.phase_data["slash"] = {
            "type": self.slash_type,
            "radius": self.radius,
            "progress": progress,
            "color": self.color,
            "facing_right": ctx.facing_right,
        }
        if progress > 0.4 and progress < 0.6:
            ctx.screen_shake = max(ctx.screen_shake, 3.0)


class AreaEffectPrimitive(AbilityPrimitive):
    """Ground slam, Senbonzakura petal storm, ice field, lightning burst."""

    def __init__(
        self,
        name: str = "aoe",
        duration: float = 1.0,
        effect_type: str = "circle_expand",
        radius: float = 150.0,
        color: tuple = (0.9, 0.4, 0.8, 0.8),
        sound: Optional[str] = "impact",
    ):
        super().__init__(name, duration)
        self.effect_type = effect_type
        self.radius = radius
        self.color = color
        self.sound = sound
        self._sound_played = False
        self._shockwave_spawned = False

    def reset(self) -> None:
        super().reset()
        self._sound_played = False
        self._shockwave_spawned = False

    def execute(self, ctx: AbilityExecutionContext, progress: float) -> None:
        if not self._sound_played and self.sound:
            ctx.sounds_to_play.append({"sound": self.sound, "volume": 0.9})
            self._sound_played = True

        current_radius = self.radius * math.sqrt(progress)
        alpha = (1.0 - progress) * self.color[3]
        ctx.phase_data["aoe"] = {
            "type": self.effect_type,
            "center_x": ctx.companion_x,
            "center_y": ctx.companion_y,
            "radius": current_radius,
            "color": (self.color[0], self.color[1], self.color[2], alpha),
        }
        if not self._shockwave_spawned:
            ctx.particles_to_spawn.append({
                "type": "ring_burst",
                "x": ctx.companion_x,
                "y": ctx.companion_y,
                "radius": self.radius,
                "color": self.color,
                "rate": 8,
            })
            self._shockwave_spawned = True


class ShieldPrimitive(AbilityPrimitive):
    """Protective barrier, ice shield, energy barrier."""

    def __init__(
        self,
        name: str = "shield",
        duration: float = 2.0,
        shield_type: str = "hex_barrier",
        radius: float = 70.0,
        color: tuple = (0.2, 0.6, 1.0, 0.7),
        sound: Optional[str] = "shield_up",
    ):
        super().__init__(name, duration)
        self.shield_type = shield_type
        self.radius = radius
        self.color = color
        self.sound = sound
        self._sound_played = False

    def reset(self) -> None:
        super().reset()
        self._sound_played = False

    def execute(self, ctx: AbilityExecutionContext, progress: float) -> None:
        if not self._sound_played and self.sound:
            ctx.sounds_to_play.append({"sound": self.sound, "volume": 0.7})
            self._sound_played = True

        pulse = 1.0 + 0.05 * math.sin(progress * 15.0)
        ctx.phase_data["shield"] = {
            "type": self.shield_type,
            "radius": self.radius * pulse,
            "color": self.color,
            "remaining": 1.0 - progress,
        }


class TeleportPrimitive(AbilityPrimitive):
    """Instant reposition (Shunpo, Batman grapple disappearance, ninja flash step)."""

    def __init__(
        self,
        name: str = "teleport",
        duration: float = 0.3,
        distance: float = 180.0,
        particle_type: str = "speed_lines",
        sound: Optional[str] = "teleport",
    ):
        super().__init__(name, duration)
        self.distance = distance
        self.particle_type = particle_type
        self.sound = sound
        self._repositioned = False
        self._spawned_start = False
        self._spawned_end = False

    def reset(self) -> None:
        super().reset()
        self._repositioned = False
        self._spawned_start = False
        self._spawned_end = False

    def execute(self, ctx: AbilityExecutionContext, progress: float) -> None:
        direction = 1.0 if ctx.facing_right else -1.0
        if progress < 0.5:
            # Fade out
            ctx.phase_data["opacity"] = 1.0 - (progress * 2.0)
            if not self._spawned_start:
                ctx.particles_to_spawn.append({
                    "type": self.particle_type,
                    "x": ctx.companion_x,
                    "y": ctx.companion_y,
                    "rate": 6,
                })
                self._spawned_start = True
        else:
            if not self._repositioned:
                ctx.companion_x += direction * self.distance
                self._repositioned = True
                if self.sound:
                    ctx.sounds_to_play.append({"sound": self.sound, "volume": 0.8})
            # Fade back in
            ctx.phase_data["opacity"] = (progress - 0.5) * 2.0
            if not self._spawned_end:
                ctx.particles_to_spawn.append({
                    "type": self.particle_type,
                    "x": ctx.companion_x,
                    "y": ctx.companion_y,
                    "rate": 6,
                })
                self._spawned_end = True


class TransformationPrimitive(AbilityPrimitive):
    """Form transformation (Power-Up, Ultimate, Shikai, Bankai, Resurreccion, God Blast)."""

    def __init__(
        self,
        name: str = "transformation",
        duration: float = 1.5,
        target_form: str = "power_up",
        aura_color: tuple = (1.0, 0.84, 0.0, 0.9),
        burst_particles: str = "power_pillar",
        sound: Optional[str] = "transform",
    ):
        super().__init__(name, duration)
        self.target_form = target_form
        self.aura_color = aura_color
        self.burst_particles = burst_particles
        self.sound = sound
        self._sound_played = False
        self._burst_spawned = False

    def reset(self) -> None:
        super().reset()
        self._sound_played = False
        self._burst_spawned = False

    def execute(self, ctx: AbilityExecutionContext, progress: float) -> None:
        if not self._sound_played and self.sound:
            ctx.sounds_to_play.append({"sound": self.sound, "volume": 1.0})
            self._sound_played = True

        ctx.phase_data["transformation_active"] = True
        ctx.phase_data["target_form"] = self.target_form
        ctx.phase_data["aura_intensity"] = 1.5 * math.sin(progress * math.pi)
        ctx.phase_data["aura_color"] = self.aura_color
        ctx.screen_shake = 5.0 * math.sin(progress * math.pi)

        if not self._burst_spawned and progress >= 0.15:
            ctx.particles_to_spawn.append({
                "type": self.burst_particles,
                "x": ctx.companion_x,
                "y": ctx.companion_y,
                "color": self.aura_color,
                "rate": 12,
            })
            self._burst_spawned = True


class ParticlePrimitive(AbilityPrimitive):
    """Spawns arbitrary particle families."""

    def __init__(
        self,
        name: str = "particles",
        duration: float = 0.6,
        particle_family: str = "sparks",
        color: tuple = (1.0, 0.9, 0.3, 0.8),
        count: int = 12,
    ):
        super().__init__(name, duration)
        self.particle_family = particle_family
        self.color = color
        self.count = count
        self._spawned = False

    def reset(self) -> None:
        super().reset()
        self._spawned = False

    def execute(self, ctx: AbilityExecutionContext, progress: float) -> None:
        if not self._spawned:
            ctx.particles_to_spawn.append({
                "type": self.particle_family,
                "x": ctx.companion_x,
                "y": ctx.companion_y,
                "color": self.color,
                "rate": self.count,
            })
            self._spawned = True


class SoundPrimitive(AbilityPrimitive):
    """Plays audio cue at exact timeline."""

    def __init__(self, name: str = "sound", sound_id: str = "ability_whoosh", volume: float = 0.8):
        super().__init__(name, 0.1)
        self.sound_id = sound_id
        self.volume = volume
        self._played = False

    def reset(self) -> None:
        super().reset()
        self._played = False

    def execute(self, ctx: AbilityExecutionContext, progress: float) -> None:
        if not self._played:
            ctx.sounds_to_play.append({"sound": self.sound_id, "volume": self.volume})
            self._played = True


class RecoveryPrimitive(AbilityPrimitive):
    """Return to resting posture, settle momentum, dissipate remaining VFX."""

    def __init__(self, name: str = "recovery", duration: float = 0.35):
        super().__init__(name, duration)

    def execute(self, ctx: AbilityExecutionContext, progress: float) -> None:
        # Smoothly reset transient offsets
        if "offset_x" in ctx.phase_data:
            ctx.phase_data["offset_x"] *= (1.0 - progress)
        if "offset_y" in ctx.phase_data:
            ctx.phase_data["offset_y"] *= (1.0 - progress)
        if "aura_intensity" in ctx.phase_data:
            ctx.phase_data["aura_intensity"] *= (1.0 - progress)
        ctx.screen_shake *= (1.0 - progress)
