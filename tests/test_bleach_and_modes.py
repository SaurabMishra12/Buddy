"""Unit tests for Bleach Soul Reaper characters and Companion Behavior Modes."""

import pytest
import cairo
import math
from skins.manager import skin_manager
from core.particles import ParticleManager
from core.config import config
from core.engine import BuddyEngine
from skins.base import CharacterState


BLEACH_CHARACTERS = [
    "ichigo",
    "byakuya",
    "yamamoto",
    "kenpachi",
    "hitsugaya",
    "rukia",
    "urahara"
]


def test_bleach_characters_registered():
    """Verify all 7 Bleach characters are registered and categorized as 'bleach'."""
    all_skins = skin_manager.get_available_skins()
    skin_ids = [s["id"] for s in all_skins]

    for char_id in BLEACH_CHARACTERS:
        assert char_id in skin_ids, f"Character '{char_id}' not found in registered skins"
        meta = skin_manager.get_metadata(char_id)
        assert meta is not None, f"Metadata missing for '{char_id}'"
        assert meta.get("category") == "bleach", f"Character '{char_id}' category is not 'bleach'"
        assert len(meta.get("abilities", [])) > 0, f"Character '{char_id}' has no registered abilities"


def test_bleach_character_instantiation_and_rendering():
    """Verify each Bleach character instantiates and renders onto a Cairo context without errors."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 250, 250)
    ctx = cairo.Context(surf)
    pm = ParticleManager()

    for char_id in BLEACH_CHARACTERS:
        char = skin_manager.create_character(char_id, x=125.0, y=125.0)
        assert char is not None
        assert char.skin_id == char_id

        # Update frame
        char.update(
            dt=0.016,
            cursor_x=180.0,
            cursor_y=120.0,
            screen_bounds=(0, 0, 1920, 1080),
            particle_mgr=pm,
            audio_mgr=None,
            config_data={"companion_mode": "static"}
        )

        # Draw frame
        char.draw(ctx, pm)

        # Flip facing left
        char.facing_right = False
        char.draw(ctx, pm)


def test_bleach_abilities_and_particles():
    """Verify Bleach character abilities trigger particles correctly."""
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 250, 250)
    ctx = cairo.Context(surf)
    pm = ParticleManager()

    # Byakuya Senbonzakura -> cherry petals
    byakuya = skin_manager.create_character("byakuya", x=100.0, y=100.0)
    assert byakuya.trigger_ability("senbonzakura", 150.0, 150.0, pm, None)
    assert len(pm.cherry_petals) > 0

    # Hitsugaya Hyorinmaru -> ice crystals
    hitsugaya = skin_manager.create_character("hitsugaya", x=100.0, y=100.0)
    assert hitsugaya.trigger_ability("hyorinmaru", 150.0, 150.0, pm, None)
    assert len(pm.ice_crystals) > 0

    # Rukia Tsukishiro -> ice crystals
    rukia = skin_manager.create_character("rukia", x=100.0, y=100.0)
    assert rukia.trigger_ability("sode_no_shirayuki", 150.0, 150.0, pm, None)
    assert len(pm.ice_crystals) > 0

    # Yamamoto Ryujin Jakka -> flame and reiatsu
    yamamoto = skin_manager.create_character("yamamoto", x=100.0, y=100.0)
    assert yamamoto.trigger_ability("ryujin_jakka", 150.0, 150.0, pm, None)
    assert len(pm.reiatsu_auras) > 0

    # Kenpachi Nozarashi -> reiatsu
    kenpachi = skin_manager.create_character("kenpachi", x=100.0, y=100.0)
    assert kenpachi.trigger_ability("nozarashi", 150.0, 150.0, pm, None)
    assert len(pm.reiatsu_auras) > 0

    # Ichigo Getsuga Tensho -> getsuga crescent
    ichigo = skin_manager.create_character("ichigo", x=100.0, y=100.0)
    assert ichigo.trigger_ability("getsuga_tensho", 150.0, 150.0, pm, None)
    assert len(pm.getsuga_slashes) > 0

    # Urahara Benihime -> reiatsu
    urahara = skin_manager.create_character("urahara", x=100.0, y=100.0)
    assert urahara.trigger_ability("benihime", 150.0, 150.0, pm, None)
    assert len(pm.reiatsu_auras) > 0

    # Verify particle manager updates and renders
    pm.update()
    pm.draw(ctx)


def test_companion_behavior_modes():
    """Verify setting companion behavior modes in BuddyEngine."""
    engine = BuddyEngine(requested_skin="ichigo")

    # Initial default should be static
    assert engine.mode in ("static", "roam", "follow")

    # Test switching to static
    engine.set_mode("static")
    assert engine.mode == "static"
    assert config.get("companion_mode") == "static"

    # Test switching to roam
    engine.set_mode("roam")
    assert engine.mode == "roam"
    assert config.get("companion_mode") == "roam"

    # Test switching to follow
    engine.set_mode("follow")
    assert engine.mode == "follow"
    assert config.get("companion_mode") == "follow"

    # Switch back to static
    engine.set_mode("static")
    assert engine.mode == "static"

    # Test drag & drop in static mode updates anchor
    engine.character.x = 350.0
    engine.character.y = 450.0
    class MockEvent:
        button = 1
        x = engine.window.half_size
        y = engine.window.half_size
    engine.on_button_release(None, MockEvent())
    assert engine.anchor_x == 350.0
    assert engine.anchor_y == 450.0
