#!/usr/bin/env python3
"""
Integration tests: Rosetta Stone x1.2 yield multiplier flows through
both the runtime sphere daily yield and the economy reward computation.
"""

import sys
import types
import shutil
import tempfile
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

if "Eidolon" not in sys.modules:
    sys.modules["Eidolon"] = types.ModuleType("Eidolon")

import pytest

from core.rosetta_stone_system import (
    RosettaStoneRegistry,
    YIELD_MULTIPLIER,
)
from core.eidolon_economy import compute_eidolon_reward, _rosetta_multiplier


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def rosetta_dir():
    d = tempfile.mkdtemp(prefix="rosetta_yield_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def distributed_registry(rosetta_dir):
    """A registry with all 255 stones initialized and distributed."""
    reg = RosettaStoneRegistry(storage_dir=rosetta_dir)
    reg.initialize_stones()
    reg.distribute()
    return reg


# ============================================================================
# ECONOMY: compute_eidolon_reward
# ============================================================================

class TestEconomyRewardIntegration:
    def test_reward_without_vault_number_has_no_rosetta_bonus(self):
        """When vault_number is omitted, rosetta multiplier is 1.0."""
        result = compute_eidolon_reward(
            finalized_reward_ratio=10.0,
            resonance_score=50.0,
            operational_entropy=0.0,
        )
        assert result["rosetta_stone_multiplier"] == 1.0

    def test_reward_with_holder_vault_gets_1_2(self, distributed_registry, monkeypatch):
        """Vault #1 (Supreme) should get x1.2 on rewards."""
        monkeypatch.setattr(
            "core.rosetta_stone_system.RosettaStoneRegistry",
            lambda **kw: distributed_registry,
        )
        result = compute_eidolon_reward(
            finalized_reward_ratio=10.0,
            resonance_score=50.0,
            operational_entropy=0.0,
            vault_number=1,
        )
        assert result["rosetta_stone_multiplier"] == YIELD_MULTIPLIER
        result_no_rosetta = compute_eidolon_reward(
            finalized_reward_ratio=10.0,
            resonance_score=50.0,
            operational_entropy=0.0,
        )
        assert result["eidolon_reward_units"] > result_no_rosetta["eidolon_reward_units"]

    def test_reward_with_non_holder_vault_gets_1_0(self, distributed_registry, monkeypatch):
        """Vault #5000 has no stone, multiplier stays 1.0."""
        monkeypatch.setattr(
            "core.rosetta_stone_system.RosettaStoneRegistry",
            lambda **kw: distributed_registry,
        )
        result = compute_eidolon_reward(
            finalized_reward_ratio=10.0,
            resonance_score=50.0,
            operational_entropy=0.0,
            vault_number=5000,
        )
        assert result["rosetta_stone_multiplier"] == 1.0

    def test_reward_ratio_exactly_1_2x(self, distributed_registry, monkeypatch):
        """The x1.2 bonus is multiplicative on the final amount."""
        monkeypatch.setattr(
            "core.rosetta_stone_system.RosettaStoneRegistry",
            lambda **kw: distributed_registry,
        )
        base = compute_eidolon_reward(
            finalized_reward_ratio=10.0,
            resonance_score=50.0,
            operational_entropy=0.0,
        )
        with_rosetta = compute_eidolon_reward(
            finalized_reward_ratio=10.0,
            resonance_score=50.0,
            operational_entropy=0.0,
            vault_number=1,
        )
        ratio = with_rosetta["eidolon_reward_units"] / base["eidolon_reward_units"]
        assert abs(ratio - 1.2) < 0.01


# ============================================================================
# RUNTIME SPHERES: _compute_daily_yield
# ============================================================================

class TestRuntimeSphereYieldIntegration:
    def test_daily_yield_with_rosetta_holder(self, distributed_registry, monkeypatch, tmp_path):
        """A sphere in an awakened state for a Rosetta holder yields x1.2 more."""
        from core.runtime_spheres import RuntimeSphereManager, BASE_YIELD

        # Patch the registry
        monkeypatch.setattr(
            "core.rosetta_stone_system.RosettaStoneRegistry",
            lambda **kw: distributed_registry,
        )

        # Create manager for vault #1 (Supreme, has Rosetta Stone)
        mgr = RuntimeSphereManager(vault_id="testvault_001", vault_number=1)
        mgr._storage_dir = tmp_path
        mgr._spheres_file = tmp_path / "runtime_spheres.json"

        # Assign a common sphere in awakened state
        sphere = mgr.assign_sphere("sphere_test_001", "common")
        sphere["state"] = "awakened"
        sphere["state_multiplier"] = 1.0
        sphere["yield_multiplier"] = 1.0
        mgr._save()

        yield_val = mgr._compute_daily_yield(sphere)
        expected = BASE_YIELD["common"] * 1.0 * 1.0 * YIELD_MULTIPLIER
        assert abs(yield_val - expected) < 0.001

    def test_daily_yield_without_rosetta(self, distributed_registry, monkeypatch, tmp_path):
        """A sphere for a non-holder vault yields at base rate."""
        from core.runtime_spheres import RuntimeSphereManager, BASE_YIELD

        monkeypatch.setattr(
            "core.rosetta_stone_system.RosettaStoneRegistry",
            lambda **kw: distributed_registry,
        )

        # Vault #5000 has no Rosetta Stone
        mgr = RuntimeSphereManager(vault_id="testvault_5000", vault_number=5000)
        mgr._storage_dir = tmp_path
        mgr._spheres_file = tmp_path / "runtime_spheres.json"

        sphere = mgr.assign_sphere("sphere_test_002", "common")
        sphere["state"] = "awakened"
        sphere["state_multiplier"] = 1.0
        sphere["yield_multiplier"] = 1.0
        mgr._save()

        yield_val = mgr._compute_daily_yield(sphere)
        expected = BASE_YIELD["common"] * 1.0 * 1.0 * 1.0
        assert abs(yield_val - expected) < 0.001

    def test_yield_projection_includes_rosetta_bonus(self, distributed_registry, monkeypatch, tmp_path):
        """get_yield_projection() exposes the rosetta_stone_bonus field."""
        from core.runtime_spheres import RuntimeSphereManager

        monkeypatch.setattr(
            "core.rosetta_stone_system.RosettaStoneRegistry",
            lambda **kw: distributed_registry,
        )

        mgr = RuntimeSphereManager(vault_id="testvault_001", vault_number=1)
        mgr._storage_dir = tmp_path
        mgr._spheres_file = tmp_path / "runtime_spheres.json"

        projection = mgr.get_yield_projection()
        assert "rosetta_stone_bonus" in projection
        assert projection["rosetta_stone_bonus"] == YIELD_MULTIPLIER
