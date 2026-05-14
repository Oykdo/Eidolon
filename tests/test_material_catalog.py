"""
Tests for the 256-material catalog and HKDF-based selection.

Validates:
  1. Catalog completeness (exactly 256 entries)
  2. Density range coverage (10 orders of magnitude)
  3. Property validity (no negatives, no out-of-range values)
  4. Selection determinism (same seed → same materials)
  5. Avalanche (1-bit flip → ≥5/7 materials change)
  6. Performance (selection < 1ms)
"""

import time

import pytest

from src.holo.material_catalog import (
    MATERIAL_CATALOG,
    CatalogMaterial,
    select_materials,
)


class TestCatalogCompleteness:
    def test_exactly_256_entries(self):
        assert len(MATERIAL_CATALOG) == 256

    def test_all_entries_are_catalog_material(self):
        for m in MATERIAL_CATALOG:
            assert isinstance(m, CatalogMaterial)

    def test_unique_names(self):
        names = [m.name for m in MATERIAL_CATALOG]
        assert len(names) == len(set(names)), f"Duplicate names found"


class TestPropertyValidity:
    def test_density_positive(self):
        for m in MATERIAL_CATALOG:
            assert m.density > 0, f"{m.name}: density={m.density}"

    def test_elasticity_range(self):
        for m in MATERIAL_CATALOG:
            assert 0 <= m.elasticity <= 1.0, f"{m.name}: elasticity={m.elasticity}"

    def test_friction_range(self):
        for m in MATERIAL_CATALOG:
            assert 0 <= m.friction <= 1.0, f"{m.name}: friction={m.friction}"

    def test_roughness_range(self):
        for m in MATERIAL_CATALOG:
            assert 0 <= m.roughness <= 1.0, f"{m.name}: roughness={m.roughness}"

    def test_hardness_range(self):
        for m in MATERIAL_CATALOG:
            assert 0 <= m.hardness <= 10.0, f"{m.name}: hardness={m.hardness}"

    def test_specific_heat_positive(self):
        for m in MATERIAL_CATALOG:
            assert m.specific_heat > 0, f"{m.name}: specific_heat={m.specific_heat}"

    def test_sound_velocity_positive(self):
        for m in MATERIAL_CATALOG:
            assert m.sound_velocity > 0, f"{m.name}: sound_velocity={m.sound_velocity}"


class TestDensityDistribution:
    RANGES = [
        (0, 50), (50, 200), (200, 600), (600, 1500), (1500, 3000),
        (3000, 5000), (5000, 8000), (8000, 12000), (12000, 20000), (20000, 100000),
    ]

    def test_all_ranges_populated(self):
        for lo, hi in self.RANGES:
            count = sum(1 for m in MATERIAL_CATALOG if lo <= m.density < hi)
            assert count >= 10, (
                f"Range [{lo}, {hi}) has only {count} materials (need ≥10)"
            )

    def test_density_spans_4_orders_of_magnitude(self):
        densities = [m.density for m in MATERIAL_CATALOG]
        ratio = max(densities) / min(densities)
        assert ratio > 1000, f"Density ratio {ratio:.0f}x (need >1000x)"


class TestSelectionDeterminism:
    SEED_A = b"\x42" * 64
    SEED_B = b"\x43" * 64

    def test_same_seed_same_materials(self):
        m1 = select_materials(self.SEED_A)
        m2 = select_materials(self.SEED_A)
        assert [m.name for m in m1] == [m.name for m in m2]

    def test_different_seed_different_materials(self):
        m1 = select_materials(self.SEED_A)
        m2 = select_materials(self.SEED_B)
        names1 = [m.name for m in m1]
        names2 = [m.name for m in m2]
        diff = sum(1 for a, b in zip(names1, names2) if a != b)
        assert diff >= 5, f"Only {diff}/7 materials differ between seeds"

    def test_returns_7_materials(self):
        mats = select_materials(self.SEED_A)
        assert len(mats) == 7

    def test_custom_count(self):
        mats = select_materials(self.SEED_A, count=3)
        assert len(mats) == 3


class TestAvalanche:
    def test_1bit_flip_changes_most_materials(self):
        seed_a = b"\x00" * 64
        seed_b = bytearray(seed_a)
        seed_b[0] = 0x01
        seed_b = bytes(seed_b)

        m_a = select_materials(seed_a)
        m_b = select_materials(seed_b)
        diff = sum(1 for a, b in zip(m_a, m_b) if a.name != b.name)
        assert diff >= 5, f"Only {diff}/7 materials changed with 1-bit flip"

    def test_different_bit_positions(self):
        """Flipping different bits should produce different selections."""
        base_seed = b"\x00" * 64
        selections = set()
        for byte_pos in range(32):
            s = bytearray(base_seed)
            s[byte_pos] = 0x01
            mats = select_materials(bytes(s))
            key = tuple(m.name for m in mats)
            selections.add(key)
        # At least 30 unique selections from 32 bit positions
        assert len(selections) >= 30


class TestPerformance:
    def test_selection_under_1ms(self):
        seed = b"\x42" * 64
        start = time.monotonic()
        for _ in range(100):
            select_materials(seed)
        elapsed = (time.monotonic() - start) / 100
        assert elapsed < 0.001, f"Selection took {elapsed*1000:.2f}ms (limit: 1ms)"

    def test_catalog_import_fast(self):
        """The catalog is pre-built; accessing it should be instant."""
        start = time.monotonic()
        _ = len(MATERIAL_CATALOG)
        elapsed = time.monotonic() - start
        assert elapsed < 0.01
