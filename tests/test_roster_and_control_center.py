"""Comprehensive validation tests for the entire character roster, 30-state animation machine,
Bleach Shikai/Bankai isolation, and macOS Buddy Control Center."""

import pytest
import cairo
from skins.manager import skin_manager
from skins.base import BaseCharacter, CharacterState, CharacterStateMachine, BLEACH_CHARACTERS
from core.particles import ParticleManager


def test_entire_roster_instantiation_and_rendering():
    """Verify that every character in BUILTIN_SKINS can be instantiated, updated, and drawn to Cairo without errors."""
    particles = ParticleManager()
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 200, 200)
    ctx = cairo.Context(surface)

    all_skins = skin_manager.get_available_skins()
    assert len(all_skins) >= 29, f"Expected at least 29 characters, found {len(all_skins)}"

    for skin_info in all_skins:
        skin_id = skin_info["id"]
        char = skin_manager.create_character(skin_id, x=100.0, y=100.0)
        assert char is not None, f"Failed to instantiate character: {skin_id}"
        assert isinstance(char, BaseCharacter)
        assert hasattr(char, "state_machine")

        # Test physics update
        char.update(
            dt=0.016,
            cursor_x=120.0,
            cursor_y=110.0,
            screen_bounds=(0, 0, 1920, 1080),
            particle_mgr=particles,
            audio_mgr=None,
            config_data={"companion_mode": "static"}
        )

        # Test vector draw
        ctx.save()
        char.draw(ctx, particles)
        ctx.restore()

        # Test capabilities
        caps = char.get_capabilities()
        assert isinstance(caps, dict)


def test_bleach_shikai_bankai_partitioning():
    """Verify that Shikai and Bankai are strictly partitioned to Bleach characters."""
    bleach_chars = ["ichigo", "byakuya", "yamamoto", "aizen", "yoruichi", "shunsui", "soi_fon", "shinji", "mayuri", "ulquiorra"]
    non_bleach_chars = ["thor", "ironman", "cat", "dog", "spiderman", "batman", "superman"]

    for b_id in bleach_chars:
        char = skin_manager.create_character(b_id, x=100.0, y=100.0)
        assert char.state_machine.is_bleach is True
        char.state_machine.transition_to(CharacterState.SHIKAI_ACTIVATION)
        assert char.state_machine.current_state == CharacterState.SHIKAI_ACTIVATION

        char.state_machine.transition_to(CharacterState.BANKAI_ACTIVATION)
        assert char.state_machine.current_state == CharacterState.BANKAI_ACTIVATION

    for nb_id in non_bleach_chars:
        char = skin_manager.create_character(nb_id, x=100.0, y=100.0)
        assert char.state_machine.is_bleach is False

        # Attempting Shikai on non-Bleach character should map to SPECIAL_READY
        char.state_machine.transition_to(CharacterState.SHIKAI_ACTIVATION)
        assert char.state_machine.current_state == CharacterState.SPECIAL_READY

        # Attempting Bankai on non-Bleach character should map to ULTIMATE
        char.state_machine.transition_to(CharacterState.BANKAI_ACTIVATION)
        assert char.state_machine.current_state == CharacterState.ULTIMATE


def test_standardized_state_machine_30_states():
    """Verify all 30 states can be transitioned to and tick without exception."""
    all_states = [
        CharacterState.IDLE, CharacterState.IDLE_VARIATION, CharacterState.WALK,
        CharacterState.RUN, CharacterState.JUMP_START, CharacterState.JUMP,
        CharacterState.FALL, CharacterState.LAND, CharacterState.SIT,
        CharacterState.SLEEP, CharacterState.WAKE, CharacterState.LOOK_AROUND,
        CharacterState.HAPPY, CharacterState.CONFUSED, CharacterState.ANNOYED,
        CharacterState.SURPRISED, CharacterState.EXCITED, CharacterState.INTERACT,
        CharacterState.ATTACK_READY, CharacterState.ATTACK, CharacterState.SPECIAL_READY,
        CharacterState.SHIKAI_ACTIVATION, CharacterState.SHIKAI_ACTIVE,
        CharacterState.BANKAI_ACTIVATION, CharacterState.BANKAI_ACTIVE,
        CharacterState.ULTIMATE, CharacterState.DAMAGE, CharacterState.RECOVERY,
        CharacterState.DEACTIVATE, CharacterState.RETURN_TO_IDLE
    ]

    char = skin_manager.create_character("ichigo", x=100.0, y=100.0)
    sm = char.state_machine

    for st in all_states:
        sm.transition_to(st, duration=0.05)
        assert sm.current_state == st
        # Simulate expiration
        sm.update(0.1)
        # Should either progress to its next expected state or safely return to IDLE
        assert sm.current_state is not None


def test_rapid_animation_and_character_switching():
    """Stress test rapid switching between abilities, states, and characters."""
    particles = ParticleManager()
    roster_sample = ["thor", "ichigo", "byakuya", "aizen", "yoruichi", "spiderman", "mayuri"]

    for _ in range(3):
        for skin_id in roster_sample:
            char = skin_manager.create_character(skin_id, x=100.0, y=100.0)
            meta = skin_manager.get_metadata(skin_id)
            abilities = meta.get("abilities", [])

            for ab in abilities:
                # Trigger ability rapidly
                char.trigger_ability(ab, 150.0, 150.0, particles, None)

            # Rapid state transitions
            char.state_machine.transition_to(CharacterState.ATTACK)
            char.state_machine.transition_to(CharacterState.SPECIAL)
            char.state_machine.transition_to(CharacterState.RETURN_TO_IDLE)
            char.state_machine.update(0.5)
            assert char.state_machine.current_state == CharacterState.IDLE


def test_control_center_instantiation():
    """Verify ControlCenterWindow and Live Preview can be instantiated in AppKit without crashes."""
    import sys
    if sys.platform != "darwin":
        pytest.skip("Control Center is native macOS AppKit")

    from platforms.macos.control_center import BuddyControlCenterWindow, show_macos_control_center
    from core.engine import BuddyEngine

    engine = BuddyEngine(requested_skin="ichigo", debug_mode=True)
    cc = show_macos_control_center(engine)
    assert cc is not None
    assert cc.preview_view is not None

    # Test tab switching across all 7 tabs
    for idx in range(7):
        cc.select_tab(idx)
        assert cc.active_tab_index == idx

    # Test preview tick
    cc.on_preview_tick()

    # Test character selection in preview
    cc.select_character("byakuya")
    assert cc.selected_skin_id == "byakuya"
    assert cc.preview_char.skin_id == "byakuya"

    # Test preview animation trigger
    cc.trigger_animation("BANKAI_ACTIVATION")
    assert cc.preview_char.state_machine.current_state == CharacterState.BANKAI_ACTIVATION

    cc.close()
