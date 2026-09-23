"""
Comprehensive test suite validating the macOS production upgrade systems:
1. Single-instance lock and lifecycle states
2. Universal power tiers and schema validation for all 36 characters
3. Composable ability primitives and execution runner
4. Ability combo engine and compatibility chains
5. Experimental Fusion Lab
6. Companion Brain 4-layer behavior hierarchy
7. Autonomous Ability System and smart suppression
8. Window perching manager and scoring
9. User profiles, schema versioning, and migration
10. Prioritized audio channels
"""

import os
import json
import pytest
import time
from pathlib import Path

from core.lifecycle import SingleInstanceLock, AppLifecycleState
from skins.schema import (
    PowerTier,
    POWER_TIER_REGISTRY,
    get_power_tier_labels,
    validate_character_metadata,
)
from skins.manager import skin_manager
from skins.base import BLEACH_CHARACTERS
from core.abilities.primitives import (
    AbilityExecutionContext,
    MovementPrimitive,
    ChargePrimitive,
    ProjectilePrimitive,
    BeamPrimitive,
    MeleePrimitive,
    AreaEffectPrimitive,
    TeleportPrimitive,
    TransformationPrimitive,
    RecoveryPrimitive,
)
from core.abilities.ability import (
    AbilityDefinition,
    AbilityRegistry,
    AbilityRunner,
    RarityTier,
    ability_registry,
)
from core.abilities.combo import ComboEngine, ComboSequence, combo_engine
from core.abilities.fusion import FusionLab, fusion_lab
from behavior.mood import MoodManager, MoodType
from behavior.brain import CompanionBrain, Intent
from behavior.autonomous import AutonomousAbilityManager, AutonomousMode, AutonomousSettings
from behavior.perching import PerchTarget, PerchTargetScorer, PerchManager, PerchMode
from core.profile import BuddyProfile, ProfileManager, BUILTIN_PROFILES
from platforms.macos.audio import AudioPriority, MacOSSoundManager


# ---------------------------------------------------------------------------
# 1. Single-Instance Lock & Lifecycle Tests
# ---------------------------------------------------------------------------
def test_single_instance_lock(tmp_path):
    lock_file = tmp_path / "test_buddy.lock"
    lock1 = SingleInstanceLock(lock_file)
    assert lock1.acquire() is True
    assert lock1.is_locked is True

    # Second instance attempting to acquire the same lock must fail gracefully
    lock2 = SingleInstanceLock(lock_file)
    assert lock2.acquire() is False
    assert lock2.is_locked is False

    # Once lock1 releases, lock2 can acquire
    lock1.release()
    assert lock1.is_locked is False
    assert lock2.acquire() is True
    lock2.release()


def test_app_lifecycle_state():
    lifecycle = AppLifecycleState()
    assert lifecycle.can_transition_to(AppLifecycleState.STARTING) is True
    lifecycle.set_state(AppLifecycleState.STARTING)
    assert lifecycle.state == AppLifecycleState.STARTING

    lifecycle.set_state(AppLifecycleState.ACTIVE)
    assert lifecycle.state == AppLifecycleState.ACTIVE

    lifecycle.set_state(AppLifecycleState.TERMINATING)
    assert lifecycle.state == AppLifecycleState.TERMINATING


# ---------------------------------------------------------------------------
# 2. Universal Power Tiers & Character Schema Tests
# ---------------------------------------------------------------------------
def test_universal_power_tier_registry_completeness():
    """Verify all 36 characters have valid universal power tier mappings."""
    all_skins = skin_manager.list_skins()
    assert len(all_skins) >= 36

    for skin_id in all_skins:
        labels = get_power_tier_labels(skin_id)
        assert "signature" in labels, f"{skin_id} missing signature label"
        assert "power_up" in labels, f"{skin_id} missing power_up label"
        assert "ultimate" in labels, f"{skin_id} missing ultimate label"

        # Strictly verify non-Bleach characters NEVER receive Shikai or Bankai
        if skin_id not in BLEACH_CHARACTERS:
            assert "bankai" not in labels["ultimate"].lower(), (
                f"Non-Bleach character {skin_id} has Bankai in label: {labels['ultimate']}"
            )
            assert "shikai" not in labels["power_up"].lower(), (
                f"Non-Bleach character {skin_id} has Shikai in label: {labels['power_up']}"
            )


def test_validate_all_characters_metadata():
    """Verify all 36 characters pass strict metadata schema validation."""
    all_skins = skin_manager.list_skins()
    for skin_id in all_skins:
        meta = skin_manager.get_metadata(skin_id)
        assert meta is not None, f"Metadata missing for {skin_id}"
        errors = validate_character_metadata(meta)
        assert errors == [], f"Validation errors for {skin_id}: {errors}"


# ---------------------------------------------------------------------------
# 3. Composable Ability Primitives & Execution Tests
# ---------------------------------------------------------------------------
def test_composable_ability_execution():
    ctx = AbilityExecutionContext(
        character_id="ichigo",
        companion_x=200.0,
        companion_y=300.0,
        companion_scale=1.0,
        facing_right=True,
        target_x=400.0,
        target_y=300.0,
    )

    test_ab = AbilityDefinition(
        id="test_blast",
        name="Test Blast",
        description="A composable test ability.",
        character_id="ichigo",
        primitives=[
            ChargePrimitive(duration=0.2, color=(0.2, 0.6, 1.0, 0.9), sound="charge"),
            ProjectilePrimitive(duration=0.3, speed=500.0, color=(0.2, 0.7, 1.0, 0.9)),
            RecoveryPrimitive(duration=0.1),
        ],
        cooldown=2.0,
        rarity=RarityTier.COMMON,
        tags=["projectile"],
    )

    runner = AbilityRunner(test_ab, ctx)
    assert runner.completed is False
    assert test_ab.total_duration == pytest.approx(0.6, abs=1e-3)

    # Step halfway
    runner.update(0.3)
    assert runner.completed is False
    assert "aura_intensity" in ctx.phase_data or "projectile" in ctx.phase_data

    # Complete execution
    runner.update(0.35)
    assert runner.completed is True
    assert ctx.completed is True


# ---------------------------------------------------------------------------
# 4. Ability Combo Engine Tests
# ---------------------------------------------------------------------------
def test_ability_combo_chaining():
    engine = ComboEngine()
    move_ab = AbilityDefinition(
        id="test_dash",
        name="Dash",
        description="Dash",
        character_id="ichigo",
        primitives=[MovementPrimitive(duration=0.2, dx=100.0)],
        tags=["movement"],
    )
    melee_ab = AbilityDefinition(
        id="test_slash",
        name="Slash",
        description="Slash",
        character_id="ichigo",
        primitives=[MeleePrimitive(duration=0.2)],
        tags=["melee"],
    )

    # movement -> melee is a valid transition
    assert engine.can_chain(move_ab, melee_ab) is True
    # Cannot chain same ability to itself
    assert engine.can_chain(move_ab, move_ab) is False


# ---------------------------------------------------------------------------
# 5. Fusion Lab (Experimental) Tests
# ---------------------------------------------------------------------------
def test_fusion_lab():
    lab = FusionLab()
    assert lab.enabled is False  # Must be OFF by default

    # Disabled by default
    assert lab.get_fusion_ability("ichigo", "thor") is None

    # When enabled, returns the synthesized recipe
    lab.enabled = True
    fused = lab.get_fusion_ability("ichigo", "thor")
    assert fused is not None
    assert fused.id == "fusion_lightning_shunpo"
    assert "teleport" in fused.tags


# ---------------------------------------------------------------------------
# 6. Companion Brain & Mood Tests
# ---------------------------------------------------------------------------
def test_companion_brain_intent_generation():
    brain = CompanionBrain(character_id="ichigo")
    assert brain.personality.name == "Ichigo"

    plan = brain.update(
        dt=0.1,
        companion_x=300.0,
        companion_y=400.0,
        cursor_x=310.0,
        cursor_y=400.0,
        behavior_mode="static_roam",
    )
    assert plan is not None
    assert isinstance(plan.layer1_intent, Intent)
    assert isinstance(plan.layer2_character_behavior, str)
    assert isinstance(plan.layer3_animation, str)


def test_mood_adaptation():
    mood_mgr = MoodManager(MoodType.CALM)
    assert mood_mgr.current_mood == MoodType.CALM

    # In low power, mood transitions to SLEEPY to conserve energy
    mood_mgr.evaluate_mood(
        idle_seconds=10.0,
        is_focus_active=False,
        is_break_active=False,
        mouse_active=False,
        battery_low=True,
    )
    assert mood_mgr.current_mood == MoodType.SLEEPY


# ---------------------------------------------------------------------------
# 7. Autonomous Ability System & Smart Suppression Tests
# ---------------------------------------------------------------------------
def test_autonomous_ability_system():
    brain = CompanionBrain(character_id="ichigo")
    auto_mgr = AutonomousAbilityManager(brain=brain)
    auto_mgr.settings.mode = AutonomousMode.ACTIVE

    # Smart suppression: rapid typing suppresses autonomous abilities
    auto_mgr.user_typing_active = True
    now = time.time()
    ab = auto_mgr.update(dt=0.1, character_id="ichigo", now=now)
    assert ab is None

    # Clear typing suppression; after cooldown threshold an ability can trigger
    auto_mgr.user_typing_active = False
    auto_mgr.last_ability_time = now - 20.0
    ab2 = auto_mgr.update(dt=0.1, character_id="ichigo", now=now)
    if ab2:
        assert isinstance(ab2, AbilityDefinition)
        assert ab2.character_id == "ichigo"


# ---------------------------------------------------------------------------
# 8. Window Perching Subsystem Tests
# ---------------------------------------------------------------------------
def test_perching_scorer_and_manager():
    target1 = PerchTarget(
        window_id=101,
        owner_name="Safari",
        title="Web Browser",
        x=200.0,
        y=100.0,
        width=900.0,
        height=600.0,
    )
    target2 = PerchTarget(
        window_id=102,
        owner_name="TextEdit",
        title="Notes",
        x=800.0,
        y=400.0,
        width=300.0,
        height=200.0,
    )

    scorer = PerchTargetScorer()
    score1 = scorer.score(target1, companion_x=300.0, companion_y=150.0)
    score2 = scorer.score(target2, companion_x=300.0, companion_y=150.0)

    # Large browser window close to companion must score higher
    assert score1 > score2


# ---------------------------------------------------------------------------
# 9. User Profiles & Schema Migration Tests
# ---------------------------------------------------------------------------
def test_profile_schema_migration(tmp_path):
    mgr = ProfileManager(profiles_dir=tmp_path)
    assert "default" in mgr.profiles
    assert "focus_mode" in mgr.profiles
    assert "gaming_mode" in mgr.profiles

    # Test v1 -> v2 migration
    v1_data = {
        "id": "custom_v1",
        "name": "Custom Legacy",
        "character": "thor",
        "scale": 1.2,
        "schema_version": 1,
    }
    raw = json.dumps(v1_data)
    imported = mgr.import_profile_json(raw)
    assert imported is not None
    assert imported.schema_version == 2
    assert imported.perching_mode == "safe"
    assert imported.autonomous_mode == "occasional"


# ---------------------------------------------------------------------------
# 10. Prioritized Audio Channels Tests
# ---------------------------------------------------------------------------
def test_audio_priority():
    sound_mgr = MacOSSoundManager(enabled=True, volume=0.5)
    assert sound_mgr.volume == 0.5

    # Channel priorities
    assert AudioPriority.UI > AudioPriority.ABILITY
    assert AudioPriority.ULTIMATE > AudioPriority.ABILITY
    assert AudioPriority.ABILITY > AudioPriority.AMBIENT
