"""Integration tests for the full quest flow."""

import os
import shutil
import time
from pathlib import Path

import pytest

from src.holo.realms.quests import (
    QuestEngine,
    QuestRegistry,
    QuestStatus,
    QuestType,
    PILGRIMAGE_CONFIG,
    ENTANGLEMENT_CONFIG,
)
from src.holo.realms.quest_spheres import QuestSphereRegistry


@pytest.fixture
def tmp_engine(tmp_path):
    quest_dir = tmp_path / "quests"
    sphere_dir = tmp_path / "quest_spheres"
    registry = QuestRegistry(data_dir=quest_dir)
    sphere_registry = QuestSphereRegistry(data_dir=sphere_dir)
    
    epoch_holder = {"epoch": 1000}
    def get_epoch():
        return epoch_holder["epoch"]
    
    engine = QuestEngine(registry=registry, epoch_provider=get_epoch)
    # Inject our sphere registry into the modules via attribute
    return engine, sphere_registry, epoch_holder


# ---------------------------------------------------------------------------
# Pilgrimage flow
# ---------------------------------------------------------------------------

def test_pilgrimage_full_flow(tmp_engine, monkeypatch):
    engine, sphere_registry, epoch = tmp_engine
    
    # Patch the sphere registry constructor (imported inside claim_reward)
    monkeypatch.setattr(
        "src.holo.realms.quest_spheres.QuestSphereRegistry",
        lambda: sphere_registry,
    )
    
    # Start
    ok, quest, msg = engine.start_pilgrimage("vault_alice")
    assert ok, msg
    assert quest is not None
    assert quest.status == QuestStatus.ACTIVE
    targets = quest.progress["target_spheres"]
    assert len(targets) == 7
    
    # Cannot restart (cooldown)
    ok2, _, msg2 = engine.start_pilgrimage("vault_alice")
    assert not ok2
    
    # Visit all 7 with proper epoch spacing
    for i, sid in enumerate(targets):
        epoch["epoch"] = 1000 + (i + 1) * 24
        ok_v, msg_v = engine.record_pilgrimage_visit("vault_alice", sid)
        assert ok_v, msg_v
    
    # Quest should be completed now
    completed = engine.get_completed_unclaimed("vault_alice")
    assert len(completed) == 1
    
    # Claim
    epoch["epoch"] = 1200
    rewards = engine.claim_completed("vault_alice")
    assert len(rewards) == 1
    sphere = rewards[0]["sphere"]
    assert sphere["era"] == "quest"
    assert sphere["quest_type"] == "pilgrimage"
    assert sphere["vault_id"] == "vault_alice"


def test_pilgrimage_min_visit_interval(tmp_engine, monkeypatch):
    engine, sphere_registry, epoch = tmp_engine
    monkeypatch.setattr(
        "src.holo.realms.quest_spheres.QuestSphereRegistry",
        lambda: sphere_registry,
    )
    
    ok, quest, _ = engine.start_pilgrimage("vault_x")
    assert ok
    targets = quest.progress["target_spheres"]
    
    # First visit ok
    epoch["epoch"] = 1020
    ok1, _ = engine.record_pilgrimage_visit("vault_x", targets[0])
    assert ok1
    
    # Second visit immediately fails
    epoch["epoch"] = 1025  # only 5 epochs later
    ok2, msg2 = engine.record_pilgrimage_visit("vault_x", targets[1])
    assert not ok2
    assert "apart" in msg2.lower()


def test_pilgrimage_expiry(tmp_engine, monkeypatch):
    engine, sphere_registry, epoch = tmp_engine
    monkeypatch.setattr(
        "src.holo.realms.quest_spheres.QuestSphereRegistry",
        lambda: sphere_registry,
    )
    
    ok, quest, _ = engine.start_pilgrimage("vault_x")
    assert ok
    
    # Skip past expiry
    epoch["epoch"] = 1000 + PILGRIMAGE_CONFIG.duration_epochs + 10
    
    ok_v, msg = engine.record_pilgrimage_visit("vault_x", quest.progress["target_spheres"][0])
    assert not ok_v
    assert "expired" in msg.lower()


# ---------------------------------------------------------------------------
# EPR Pact flow
# ---------------------------------------------------------------------------

def test_pact_full_flow(tmp_engine, monkeypatch):
    engine, sphere_registry, epoch = tmp_engine
    
    import src.holo.realms.quests.entanglement as emod
    monkeypatch.setattr(emod, "QuestSphereRegistry", lambda: sphere_registry,
                        raising=False)
    # Also patch the import inside claim()
    monkeypatch.setattr(
        "src.holo.realms.quest_spheres.QuestSphereRegistry",
        lambda: sphere_registry,
    )
    
    # Propose
    ok, pact_id, msg = engine.propose_pact("vault_bob", "vault_carol")
    assert ok, msg
    assert pact_id
    
    # Pending list for target
    pending = engine.get_pending_pacts("vault_carol")
    assert len(pending) == 1
    
    # Accept
    ok_a, msg_a = engine.accept_pact(pact_id, "vault_carol")
    assert ok_a, msg_a
    
    # Submit 3 measurements
    base_time = time.time()
    for i in range(3):
        ts_b = base_time + i * 10
        ts_c = base_time + i * 10 + 2.0
        ok1, m1 = engine.submit_measurement(pact_id, "vault_bob", "a", timestamp=ts_b)
        assert ok1, m1
        ok2, m2 = engine.submit_measurement(pact_id, "vault_carol", "b", timestamp=ts_c)
        assert ok2, m2
    
    # Both claim
    rewards_b = engine.claim_completed("vault_bob")
    rewards_c = engine.claim_completed("vault_carol")
    assert len(rewards_b) == 1
    assert len(rewards_c) == 1
    
    # First claim returns twin, second does not (already minted)
    twin_in_first = rewards_b[0].get("twin_sphere") or rewards_c[0].get("twin_sphere")
    assert twin_in_first is not None
    assert twin_in_first["kind"] == "twin"


def test_pact_self_blocked(tmp_engine):
    engine, _, _ = tmp_engine
    ok, _, msg = engine.propose_pact("vault_x", "vault_x")
    assert not ok
    assert "self" in msg.lower()


def test_pact_sync_window_violation(tmp_engine, monkeypatch):
    engine, sphere_registry, epoch = tmp_engine
    monkeypatch.setattr(
        "src.holo.realms.quest_spheres.QuestSphereRegistry",
        lambda: sphere_registry,
    )
    
    ok, pact_id, _ = engine.propose_pact("a", "b")
    engine.accept_pact(pact_id, "b")
    
    # Bob submits, then Carol submits TOO LATE
    base_time = time.time()
    engine.submit_measurement(pact_id, "a", "a", timestamp=base_time)
    
    # 60s later - outside window
    ok, msg = engine.submit_measurement(pact_id, "b", "b",
                                        timestamp=base_time + 60)
    assert not ok
    assert "sync" in msg.lower() or "window" in msg.lower()


def test_pact_cooldown(tmp_engine):
    engine, _, _ = tmp_engine
    ok, _, _ = engine.propose_pact("a", "b")
    assert ok
    
    # Immediate re-propose should fail (still in cooldown)
    ok2, _, msg = engine.propose_pact("a", "b")
    assert not ok2
    assert "cooldown" in msg.lower()
