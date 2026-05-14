#!/usr/bin/env python3
"""
Contract tests for the Rosetta Stone system.

Verifies:
- Total supply is exactly 255
- 33 stones go to Supreme vaults (#1-33)
- 222 stones randomly distributed to vaults #34-1000
- Permanent yield multiplier of 1.2
- Deterministic distribution (reproducible RNG)
- NFT structure and inscription flow
- Transfer tracking
"""

import sys
import os
import shutil
import tempfile
import types
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Prevent the broken Eidolon/__init__.py from being loaded as a package
if "Eidolon" not in sys.modules:
    sys.modules["Eidolon"] = types.ModuleType("Eidolon")

import pytest

from core.rosetta_stone_system import (
    RANDOM_ALLOCATION,
    RANDOM_POOL_END,
    RANDOM_POOL_START,
    SUPREME_ALLOCATION,
    TOTAL_SUPPLY,
    YIELD_MULTIPLIER,
    RosettaStone,
    RosettaStoneRegistry,
    RosettaStoneStatus,
)


@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp(prefix="rosetta_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def registry(tmp_dir):
    reg = RosettaStoneRegistry(storage_dir=tmp_dir)
    reg.initialize_stones()
    return reg


# ============================================================================
# SUPPLY AND CONSTANTS
# ============================================================================

class TestSupply:
    def test_total_supply_is_255(self):
        assert TOTAL_SUPPLY == 255

    def test_supreme_allocation_is_33(self):
        assert SUPREME_ALLOCATION == 33

    def test_random_allocation_is_222(self):
        assert RANDOM_ALLOCATION == 222

    def test_allocations_sum_to_total(self):
        assert SUPREME_ALLOCATION + RANDOM_ALLOCATION == TOTAL_SUPPLY

    def test_yield_multiplier_is_1_2(self):
        assert YIELD_MULTIPLIER == 1.2

    def test_random_pool_bounds(self):
        assert RANDOM_POOL_START == 34
        assert RANDOM_POOL_END == 1000


# ============================================================================
# INITIALIZATION
# ============================================================================

class TestInitialization:
    def test_initialize_creates_255_stones(self, registry):
        assert len(registry.stones) == TOTAL_SUPPLY

    def test_stone_numbers_are_sequential(self, registry):
        numbers = sorted(s.stone_number for s in registry.stones.values())
        assert numbers == list(range(1, TOTAL_SUPPLY + 1))

    def test_all_stones_start_unassigned(self, registry):
        for stone in registry.stones.values():
            assert stone.status == RosettaStoneStatus.UNASSIGNED
            assert stone.vault_id is None
            assert stone.vault_number is None

    def test_stone_ids_are_unique(self, registry):
        ids = [s.stone_id for s in registry.stones.values()]
        assert len(set(ids)) == TOTAL_SUPPLY

    def test_all_stones_have_yield_multiplier(self, registry):
        for stone in registry.stones.values():
            assert stone.yield_multiplier == YIELD_MULTIPLIER

    def test_initialize_is_idempotent(self, registry):
        stones_before = set(registry.stones.keys())
        registry.initialize_stones()
        assert set(registry.stones.keys()) == stones_before

    def test_individual_stone_files_created(self, tmp_dir, registry):
        stones_dir = Path(tmp_dir) / "stones"
        files = list(stones_dir.glob("stone_*.json"))
        assert len(files) == TOTAL_SUPPLY


# ============================================================================
# DISTRIBUTION
# ============================================================================

class TestDistribution:
    def test_distribute_assigns_all_255(self, registry):
        result = registry.distribute()
        assigned = sum(1 for s in registry.stones.values() if s.is_assigned)
        assert assigned == TOTAL_SUPPLY
        assert result["total_distributed"] == TOTAL_SUPPLY

    def test_supreme_vaults_get_stones_1_to_33(self, registry):
        registry.distribute()
        for vault_num in range(1, 34):
            stone = registry.get_stone_for_vault(vault_num)
            assert stone is not None
            assert stone.stone_number == vault_num
            assert stone.distribution_type == "supreme"

    def test_random_recipients_are_in_range_34_to_1000(self, registry):
        registry.distribute()
        for stone in registry.stones.values():
            if stone.distribution_type == "random":
                assert RANDOM_POOL_START <= stone.vault_number <= RANDOM_POOL_END

    def test_random_distribution_count_is_222(self, registry):
        result = registry.distribute()
        assert result["random"]["count"] == RANDOM_ALLOCATION
        random_stones = [
            s for s in registry.stones.values() if s.distribution_type == "random"
        ]
        assert len(random_stones) == RANDOM_ALLOCATION

    def test_no_vault_gets_two_stones(self, registry):
        registry.distribute()
        vault_numbers = [
            s.vault_number for s in registry.stones.values() if s.is_assigned
        ]
        assert len(vault_numbers) == len(set(vault_numbers))

    def test_distribution_is_deterministic(self, tmp_dir):
        """Two separate registries produce identical distributions."""
        dir_a = Path(tmp_dir) / "a"
        dir_b = Path(tmp_dir) / "b"

        reg_a = RosettaStoneRegistry(storage_dir=str(dir_a))
        reg_a.initialize_stones()
        result_a = reg_a.distribute()

        reg_b = RosettaStoneRegistry(storage_dir=str(dir_b))
        reg_b.initialize_stones()
        result_b = reg_b.distribute()

        recipients_a = [r["vault_number"] for r in result_a["random"]["recipients"]]
        recipients_b = [r["vault_number"] for r in result_b["random"]["recipients"]]
        assert recipients_a == recipients_b

    def test_cannot_distribute_twice(self, registry):
        registry.distribute()
        with pytest.raises(ValueError, match="already completed"):
            registry.distribute()

    def test_cannot_distribute_without_initialization(self, tmp_dir):
        reg = RosettaStoneRegistry(storage_dir=tmp_dir)
        reg.reset()
        with pytest.raises(ValueError, match="Initialize"):
            reg.distribute()

    def test_distribute_with_vault_ids(self, registry):
        vault_ids = {1: "vault_aaa", 2: "vault_bbb", 50: "vault_ccc"}
        registry.distribute(vault_ids=vault_ids)

        stone_1 = registry.get_stone_for_vault(1)
        assert stone_1 is not None
        assert stone_1.vault_id == "vault_aaa"

        stone_2 = registry.get_stone_for_vault(2)
        assert stone_2 is not None
        assert stone_2.vault_id == "vault_bbb"


# ============================================================================
# YIELD MULTIPLIER
# ============================================================================

class TestYieldMultiplier:
    def test_holder_gets_1_2_multiplier(self, registry):
        registry.distribute()
        assert registry.get_yield_multiplier(1) == 1.2
        assert registry.get_yield_multiplier(33) == 1.2

    def test_non_holder_gets_neutral_multiplier(self, registry):
        registry.distribute()
        # Find a vault in 34-1000 that was NOT selected
        holders = set(registry.get_all_holders())
        for v in range(34, 1001):
            if v not in holders:
                assert registry.get_yield_multiplier(v) == 1.0
                break

    def test_vault_above_1000_gets_neutral(self, registry):
        registry.distribute()
        assert registry.get_yield_multiplier(1001) == 1.0
        assert registry.get_yield_multiplier(50000) == 1.0


# ============================================================================
# QUERIES
# ============================================================================

class TestQueries:
    def test_get_stone_by_number(self, registry):
        stone = registry.get_stone_by_number(1)
        assert stone is not None
        assert stone.stone_number == 1

    def test_get_stone_by_invalid_number(self, registry):
        assert registry.get_stone_by_number(0) is None
        assert registry.get_stone_by_number(256) is None

    def test_vault_has_stone(self, registry):
        registry.distribute()
        assert registry.vault_has_stone(1) is True
        assert registry.vault_has_stone(33) is True

    def test_get_all_holders_count(self, registry):
        registry.distribute()
        holders = registry.get_all_holders()
        assert len(holders) == TOTAL_SUPPLY

    def test_get_stats(self, registry):
        registry.distribute()
        stats = registry.get_stats()
        assert stats["total_supply"] == 255
        assert stats["assigned"] == 255
        assert stats["unassigned"] == 0
        assert stats["supreme_distributed"] == 33
        assert stats["random_distributed"] == 222
        assert stats["yield_multiplier"] == 1.2
        assert stats["distribution_complete"] is True


# ============================================================================
# NFT / INSCRIPTION
# ============================================================================

class TestInscription:
    def test_prepare_payload_structure(self, registry):
        registry.distribute()
        payload = registry.prepare_inscription_payload(1)
        assert payload is not None
        assert payload["p"] == "eidolon"
        assert payload["op"] == "rosetta_stone"
        assert payload["stone_number"] == 1
        assert payload["total_supply"] == 255
        assert payload["yield_multiplier"] == 1.2
        assert payload["properties"]["permanent_yield_bonus"] is True

    def test_prepare_payload_unassigned_returns_none(self, registry):
        assert registry.prepare_inscription_payload(1) is None

    def test_record_inscription(self, registry):
        registry.distribute()
        ok = registry.record_inscription(
            stone_number=1,
            inscription_id="abc123i0",
            inscription_txid="tx_abc123",
            inscription_number=99999,
            owner_address="bc1q_test",
        )
        assert ok is True
        stone = registry.get_stone_by_number(1)
        assert stone.is_inscribed
        assert stone.inscription_id == "abc123i0"
        assert stone.owner_address == "bc1q_test"
        assert len(stone.transfer_history) == 1

    def test_record_inscription_invalid_stone(self, registry):
        assert registry.record_inscription(999, "x", "y") is False


# ============================================================================
# TRANSFER
# ============================================================================

class TestTransfer:
    def test_transfer_updates_owner(self, registry):
        registry.distribute()
        registry.record_inscription(1, "abc123i0", "tx1")
        ok = registry.record_transfer(
            stone_number=1,
            new_owner_address="bc1q_new",
            txid="tx_transfer",
            new_vault_number=500,
            new_vault_id="vault_500",
        )
        assert ok is True
        stone = registry.get_stone_by_number(1)
        assert stone.vault_number == 500
        assert stone.owner_address == "bc1q_new"
        assert stone.status == RosettaStoneStatus.TRANSFERRED

    def test_transfer_updates_vault_index(self, registry):
        registry.distribute()
        registry.record_inscription(1, "abc123i0", "tx1")
        registry.record_transfer(1, "bc1q_new", "tx2", new_vault_number=500)
        assert not registry.vault_has_stone(1)
        assert registry.vault_has_stone(500)

    def test_transfer_not_inscribed_fails(self, registry):
        registry.distribute()
        assert registry.record_transfer(1, "addr", "tx") is False


# ============================================================================
# PERSISTENCE
# ============================================================================

class TestPersistence:
    def test_reload_preserves_state(self, tmp_dir):
        reg = RosettaStoneRegistry(storage_dir=tmp_dir)
        reg.initialize_stones()
        reg.distribute()

        reg2 = RosettaStoneRegistry(storage_dir=tmp_dir)
        assert len(reg2.stones) == TOTAL_SUPPLY
        assert reg2.distribution_complete is True
        assert len(reg2.vault_index) == TOTAL_SUPPLY

    def test_link_vault_id_persists(self, tmp_dir):
        reg = RosettaStoneRegistry(storage_dir=tmp_dir)
        reg.initialize_stones()
        reg.distribute()
        reg.link_vault_id(1, "vault_001")

        reg2 = RosettaStoneRegistry(storage_dir=tmp_dir)
        stone = reg2.get_stone_for_vault(1)
        assert stone.vault_id == "vault_001"


# ============================================================================
# DATACLASS
# ============================================================================

class TestRosettaStoneDataclass:
    def test_to_dict_roundtrip(self):
        stone = RosettaStone(stone_id="abc", stone_number=1)
        d = stone.to_dict()
        restored = RosettaStone.from_dict(d)
        assert restored.stone_id == "abc"
        assert restored.stone_number == 1
        assert restored.yield_multiplier == YIELD_MULTIPLIER

    def test_is_assigned_false_when_unassigned(self):
        stone = RosettaStone(stone_id="abc", stone_number=1)
        assert stone.is_assigned is False

    def test_is_inscribed_false_when_draft(self):
        stone = RosettaStone(stone_id="abc", stone_number=1)
        assert stone.is_inscribed is False
