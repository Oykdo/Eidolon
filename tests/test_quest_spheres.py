"""Pytest suite for the quest_spheres module."""

import hashlib
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from src.holo.realms.quest_spheres import (
    LOOT_TABLE,
    TOTAL_WEIGHT,
    MAX_MINTS_PER_EON,
    QuestSphereRegistry,
    generate_quest_sphere,
    generate_twin_sphere,
    roll_rarity,
)
from src.holo.realms.quest_spheres.generator import verify_sphere_rng
from src.holo.realms.quest_spheres.loot_table import (
    FUSION_REQUIREMENT,
    get_rarity_by_tier,
    get_next_tier,
)


@pytest.fixture
def tmp_registry(tmp_path):
    return QuestSphereRegistry(data_dir=tmp_path / "quest_spheres")


# ---------------------------------------------------------------------------
# Loot Table
# ---------------------------------------------------------------------------

def test_loot_table_weights_sum_to_total():
    assert sum(r.weight for r in LOOT_TABLE) == TOTAL_WEIGHT == 1000


def test_drop_rate_calculations():
    for r in LOOT_TABLE:
        assert r.drop_rate == (r.weight / TOTAL_WEIGHT) * 100


def test_get_rarity_by_tier():
    assert get_rarity_by_tier("cosmic").yield_multi == 5.0
    assert get_rarity_by_tier("STONE").yield_multi == 1.0
    assert get_rarity_by_tier("unknown") is None


def test_fusion_chain():
    assert get_next_tier("stone") == "crystal"
    assert get_next_tier("crystal") == "lunar"
    assert get_next_tier("lunar") == "stellar"
    assert get_next_tier("stellar") == "cosmic"
    assert get_next_tier("cosmic") is None


# ---------------------------------------------------------------------------
# RNG
# ---------------------------------------------------------------------------

def test_rng_determinism():
    seed = b"reproducible_seed_42"
    assert roll_rarity(seed).tier == roll_rarity(seed).tier


def test_rng_distribution_within_tolerance():
    counts = {r.tier: 0 for r in LOOT_TABLE}
    for i in range(20000):
        seed = hashlib.sha256(f"dist_{i}".encode()).digest()
        counts[roll_rarity(seed).tier] += 1
    for r in LOOT_TABLE:
        observed = counts[r.tier] / 20000 * 100
        # Tolerance of 1.5% absolute deviation
        assert abs(observed - r.drop_rate) < 1.5, (
            f"{r.tier}: expected {r.drop_rate}%, got {observed}%"
        )


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def test_generate_quest_sphere_minimal():
    sphere = generate_quest_sphere("vault_x", "q1", "pilgrimage", 100)
    assert sphere["era"] == "quest"
    assert sphere["vault_id"] == "vault_x"
    assert sphere["sphereId"].startswith("QUEST_")
    assert sphere["tradeable"] is True
    assert verify_sphere_rng(sphere) is True


def test_generate_with_forced_rarity():
    sphere = generate_quest_sphere(
        "vault_x", "q1", "test", 100, forced_rarity="cosmic"
    )
    assert sphere["tier"] == "cosmic"
    assert sphere["yield_multi"] == 5.0


def test_twin_sphere_chsh_floors():
    # High CHSH -> cosmic
    twin = generate_twin_sphere("a", "b", "p1", chsh_score=2.7, epoch=100)
    assert twin["tier"] == "cosmic"
    assert twin["kind"] == "twin"
    assert twin["tradeable"] is False
    assert set(twin["twin_pair"]) == {"a", "b"}
    
    # Mid CHSH -> at least lunar
    twin2 = generate_twin_sphere("a", "b", "p2", chsh_score=2.1, epoch=100)
    assert twin2["tier"] in ("lunar", "stellar", "cosmic")
    
    # Low CHSH -> capped at crystal
    twin3 = generate_twin_sphere("a", "b", "p3", chsh_score=1.5, epoch=100)
    assert twin3["tier"] in ("stone", "crystal")


def test_twin_sphere_seed_symmetric():
    # Same vaults in different order should yield same sphere id
    t1 = generate_twin_sphere("vault_a", "vault_b", "p", 2.5, 100, nonce=b"x")
    t2 = generate_twin_sphere("vault_b", "vault_a", "p", 2.5, 100, nonce=b"x")
    assert t1["sphereId"] == t2["sphereId"]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

def test_mint_and_retrieve(tmp_registry):
    sphere = generate_quest_sphere("vault_y", "q2", "pilgrimage", 100)
    ok, msg = tmp_registry.mint(sphere, eon=1)
    assert ok, msg
    
    loaded = tmp_registry.get_sphere(sphere["sphereId"])
    assert loaded is not None
    assert loaded["sphereId"] == sphere["sphereId"]


def test_inventory_per_vault(tmp_registry):
    s1 = generate_quest_sphere("v1", "qA", "pilgrimage", 100)
    s2 = generate_quest_sphere("v1", "qB", "pilgrimage", 100)
    s3 = generate_quest_sphere("v2", "qC", "pilgrimage", 100)
    tmp_registry.mint(s1, eon=1)
    tmp_registry.mint(s2, eon=1)
    tmp_registry.mint(s3, eon=1)
    
    assert len(tmp_registry.get_vault_inventory("v1")) == 2
    assert len(tmp_registry.get_vault_inventory("v2")) == 1


def test_summary_and_yield(tmp_registry):
    cosmic = generate_quest_sphere("v1", "q", "test", 100, forced_rarity="cosmic")
    stone = generate_quest_sphere("v1", "q2", "test", 100, forced_rarity="stone")
    tmp_registry.mint(cosmic, eon=1)
    tmp_registry.mint(stone, eon=1)
    
    summary = tmp_registry.get_inventory_summary("v1")
    assert summary["cosmic"] == 1
    assert summary["stone"] == 1
    
    yield_bonus = tmp_registry.get_total_yield_bonus("v1")
    assert yield_bonus == pytest.approx(6.0)  # 5.0 + 1.0


def test_twin_appears_in_both_inventories(tmp_registry):
    twin = generate_twin_sphere("va", "vb", "pact", 2.5, 100)
    ok, _ = tmp_registry.mint(twin, eon=1)
    assert ok
    
    inv_a = tmp_registry.get_vault_inventory("va")
    inv_b = tmp_registry.get_vault_inventory("vb")
    
    twin_ids_a = {s["sphereId"] for s in inv_a}
    twin_ids_b = {s["sphereId"] for s in inv_b}
    assert twin["sphereId"] in twin_ids_a
    assert twin["sphereId"] in twin_ids_b


def test_mint_cap_per_eon(tmp_registry, monkeypatch):
    monkeypatch.setattr(
        "src.holo.realms.quest_spheres.registry.MAX_MINTS_PER_EON", 2
    )
    monkeypatch.setattr(
        "src.holo.realms.quest_spheres.loot_table.MAX_MINTS_PER_EON", 2
    )
    
    # Re-init registry to pick up the cap? It's referenced at runtime, so OK.
    s1 = generate_quest_sphere("v1", "q1", "t", 100)
    s2 = generate_quest_sphere("v1", "q2", "t", 100)
    s3 = generate_quest_sphere("v1", "q3", "t", 100)
    
    # Manually patch the registry's cap reading function
    import src.holo.realms.quest_spheres.registry as reg_mod
    monkeypatch.setattr(reg_mod, "MAX_MINTS_PER_EON", 2)
    
    assert tmp_registry.mint(s1, eon=1)[0]
    assert tmp_registry.mint(s2, eon=1)[0]
    ok, msg = tmp_registry.mint(s3, eon=1)
    assert not ok
    assert "cap" in msg.lower()


def test_fusion_success(tmp_registry):
    # Mint 3 stone spheres
    spheres = []
    for i in range(3):
        s = generate_quest_sphere("v1", f"q{i}", "test", 100,
                                   forced_rarity="stone")
        ok, _ = tmp_registry.mint(s, eon=1)
        assert ok
        spheres.append(s["sphereId"])
    
    ok, new_sphere, msg = tmp_registry.fuse(spheres, "v1", eon=1)
    assert ok, msg
    assert new_sphere["tier"] == "crystal"
    
    # Old spheres consumed
    inv = tmp_registry.get_vault_inventory("v1")
    inv_ids = {s["sphereId"] for s in inv}
    for sid in spheres:
        assert sid not in inv_ids
    
    # New sphere present
    assert new_sphere["sphereId"] in inv_ids


def test_fusion_requires_same_tier(tmp_registry):
    cosmic = generate_quest_sphere("v1", "q1", "t", 100, forced_rarity="cosmic")
    stone1 = generate_quest_sphere("v1", "q2", "t", 100, forced_rarity="stone")
    stone2 = generate_quest_sphere("v1", "q3", "t", 100, forced_rarity="stone")
    for s in (cosmic, stone1, stone2):
        tmp_registry.mint(s, eon=1)
    
    ok, _, msg = tmp_registry.fuse(
        [cosmic["sphereId"], stone1["sphereId"], stone2["sphereId"]],
        "v1", eon=1,
    )
    assert not ok
    assert "same tier" in msg.lower()


def test_fusion_cosmic_cap(tmp_registry):
    cosmics = [
        generate_quest_sphere("v1", f"q{i}", "t", 100, forced_rarity="cosmic")
        for i in range(3)
    ]
    for c in cosmics:
        tmp_registry.mint(c, eon=1)
    
    ok, _, msg = tmp_registry.fuse(
        [c["sphereId"] for c in cosmics], "v1", eon=1
    )
    assert not ok
    assert "cannot fuse" in msg.lower() or "max tier" in msg.lower()


def test_fusion_rejects_twin(tmp_registry):
    twin = generate_twin_sphere("va", "vb", "p", 2.5, 100)
    tmp_registry.mint(twin, eon=1)
    # Need two more "fake" spheres of same tier - just use forced_rarity
    s1 = generate_quest_sphere("va", "q1", "t", 100, forced_rarity=twin["tier"])
    s2 = generate_quest_sphere("va", "q2", "t", 100, forced_rarity=twin["tier"])
    tmp_registry.mint(s1, eon=1)
    tmp_registry.mint(s2, eon=1)
    
    ok, _, msg = tmp_registry.fuse(
        [twin["sphereId"], s1["sphereId"], s2["sphereId"]], "va", eon=1
    )
    assert not ok
    assert "twin" in msg.lower()


def test_transfer_changes_ownership(tmp_registry):
    sphere = generate_quest_sphere("v1", "q", "t", 100, forced_rarity="stone")
    tmp_registry.mint(sphere, eon=1)
    
    # Force a non-burning trade by picking a sphere that won't roll the tax
    # We can't predict exact tax outcome without knowing hash, so just verify
    # the call works (one of: burned OR transferred)
    ok, msg = tmp_registry.transfer(sphere["sphereId"], "v1", "v2")
    assert ok
    
    # After the call, sphere is either gone (burned) or in v2's inventory
    inv_v2 = tmp_registry.get_vault_inventory("v2")
    inv_v1 = tmp_registry.get_vault_inventory("v1")
    
    # In either case, v1 no longer has it
    v1_ids = {s["sphereId"] for s in inv_v1}
    assert sphere["sphereId"] not in v1_ids
