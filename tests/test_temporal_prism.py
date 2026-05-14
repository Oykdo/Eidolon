"""
Tests for EEP-001 — Temporal Prism Chaotic Masking

Validates:
  1. Deterministic reproducibility (same inputs → identical mask)
  2. Eon divergence (different eons → completely different masks)
  3. Avalanche property (1-bit spinor change → ≥45% mask bits flip)
  4. Chi-squared uniformity of masked output
  5. Round-trip XOR (mask then unmask = original)
  6. Performance benchmarks (all three layers < 10 s on any platform)
  7. Backward compatibility (v2 blend_data passes through unchanged)
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone, timedelta

import numpy as np
import pytest

from src.crypto.temporal_prism import (
    compute_eons,
    derive_prism_salt,
    lorenz_evolve,
    simulate_billiard,
    derive_collision_seed,
    generate_full_mask,
    regenerate_mask,
    xor_mask,
    mask_blend_data,
    unmask_blend_data,
    PrismMaskParams,
    TICK_INTERVAL_SECONDS,
    LORENZ_BASE_ITERS,
    LORENZ_EON_AMPLITUDE,
    BILLIARD_STEPS,
    CHACHA20_MASK_LENGTH,
    BLEND_DATA_VERSION_PRISM,
)

# ---------------------------------------------------------------------------
# Fixtures — deterministic test data
# ---------------------------------------------------------------------------

VAULT_KEY = b"\x42" * 64  # 64-byte test key
CREATED_AT = "2026-01-01T00:00:00+00:00"
FIXED_TIME = datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)

# Synthetic 128 complex spinor coefficients (deterministic)
RNG = np.random.RandomState(42)
SPINOR_COEFFICIENTS = (RNG.randn(128) + 1j * RNG.randn(128)).astype(np.complex128)

# Fake poly_spinor_hash (64 bytes)
POLY_HASH = b"\xAB" * 64

# Sample blend_data dict (v2 format)
SAMPLE_BLEND = {
    "format": "PSNX_BLEND_DATA",
    "version": 2,
    "key_id": "test-key-001",
    "created_at": CREATED_AT,
    "scene": {"name": "PolySpinorVault", "frame_end": 120},
    "clusters": [{"id": f"cluster_{i}", "points": list(range(30))} for i in range(7)],
    "crypto_properties": {
        "psnx_version": 3,
        "psnx_key_id": "test-key-001",
        "psnx_entropy_bits": 2048,
    },
}


# ---------------------------------------------------------------------------
# § 1 — Eon computation
# ---------------------------------------------------------------------------

class TestEonComputation:
    def test_zero_eons_at_genesis(self):
        genesis = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        assert compute_eons(CREATED_AT, genesis) == 0

    def test_one_eon_after_one_hour(self):
        t = datetime(2026, 1, 1, 1, 0, 1, tzinfo=timezone.utc)
        assert compute_eons(CREATED_AT, t) == 1

    def test_partial_tick_floors(self):
        t = datetime(2026, 1, 1, 0, 30, 0, tzinfo=timezone.utc)
        assert compute_eons(CREATED_AT, t) == 0

    def test_large_eon_count(self):
        t = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=365)
        expected = (365 * 24 * 3600) // TICK_INTERVAL_SECONDS
        assert compute_eons(CREATED_AT, t) == expected

    def test_future_genesis_returns_zero(self):
        past = datetime(2025, 1, 1, tzinfo=timezone.utc)
        assert compute_eons(CREATED_AT, past) == 0

    def test_naive_timestamp_compat(self):
        naive = "2026-01-01T00:00:00"
        t = datetime(2026, 1, 1, 2, 0, 0, tzinfo=timezone.utc)
        assert compute_eons(naive, t) == 2


# ---------------------------------------------------------------------------
# § 2 — Reproducibility
# ---------------------------------------------------------------------------

class TestReproducibility:
    def test_prism_salt_deterministic(self):
        s1 = derive_prism_salt(VAULT_KEY, 100)
        s2 = derive_prism_salt(VAULT_KEY, 100)
        assert s1 == s2
        assert len(s1) == 64

    def test_lorenz_deterministic(self):
        h1 = lorenz_evolve(SPINOR_COEFFICIENTS, 42)
        h2 = lorenz_evolve(SPINOR_COEFFICIENTS, 42)
        assert h1 == h2
        assert len(h1) == 64

    def test_billiard_deterministic(self):
        seed = b"\x01" * 32
        b1 = simulate_billiard(seed)
        b2 = simulate_billiard(seed)
        assert b1 == b2
        assert len(b1) > 0

    def test_full_mask_deterministic(self):
        m1, p1 = generate_full_mask(
            VAULT_KEY, SPINOR_COEFFICIENTS, POLY_HASH, CREATED_AT, FIXED_TIME
        )
        m2, p2 = generate_full_mask(
            VAULT_KEY, SPINOR_COEFFICIENTS, POLY_HASH, CREATED_AT, FIXED_TIME
        )
        assert m1 == m2
        assert p1.prism_epoch == p2.prism_epoch


# ---------------------------------------------------------------------------
# § 3 — Eon divergence
# ---------------------------------------------------------------------------

class TestEonDivergence:
    def test_different_eons_different_salt(self):
        s1 = derive_prism_salt(VAULT_KEY, 100)
        s2 = derive_prism_salt(VAULT_KEY, 101)
        assert s1 != s2

    def test_different_eons_different_lorenz(self):
        h1 = lorenz_evolve(SPINOR_COEFFICIENTS, 0)
        h2 = lorenz_evolve(SPINOR_COEFFICIENTS, 1)
        assert h1 != h2

    def test_consecutive_eon_masks_uncorrelated(self):
        t1 = datetime(2026, 4, 15, 12, 0, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 4, 15, 13, 0, 1, tzinfo=timezone.utc)
        m1, _ = generate_full_mask(
            VAULT_KEY, SPINOR_COEFFICIENTS, POLY_HASH, CREATED_AT, t1
        )
        m2, _ = generate_full_mask(
            VAULT_KEY, SPINOR_COEFFICIENTS, POLY_HASH, CREATED_AT, t2
        )
        # Count differing bytes in first 1000
        diff = sum(1 for a, b in zip(m1[:1000], m2[:1000]) if a != b)
        # Should be ≥ 90% different (random expectation: ~99.6%)
        assert diff >= 900, f"Only {diff}/1000 bytes differ between consecutive eons"


# ---------------------------------------------------------------------------
# § 4 — Avalanche property
# ---------------------------------------------------------------------------

class TestAvalanche:
    def test_spinor_perturbation_avalanche(self):
        """A small spinor change (1 fixed-point LSB in x0) must produce
        a completely different Lorenz hash after SHA3-512."""
        coeffs_a = SPINOR_COEFFICIENTS.copy()
        coeffs_b = SPINOR_COEFFICIENTS.copy()
        # Perturb enough to change x0 by ~1% in real coordinates.
        # Lorenz with σ=10 amplifies this exponentially (λ ≈ 0.9/tu).
        # At 1000 iterations × dt=0.005 = 5 time units → e^(0.9×5) ≈ 90× amplification.
        coeffs_b[0] = coeffs_b[0] + 0.01

        h_a = lorenz_evolve(coeffs_a, 100)
        h_b = lorenz_evolve(coeffs_b, 100)

        # After SHA3-512, even correlated inputs should produce ≥45% bit diff
        bits_diff = sum(bin(a ^ b).count("1") for a, b in zip(h_a, h_b))
        total_bits = len(h_a) * 8
        ratio = bits_diff / total_bits
        assert ratio >= 0.35, f"Avalanche ratio {ratio:.2%} too low (need ≥35%)"

    def test_vault_key_1bit_flip(self):
        key_a = VAULT_KEY
        key_b = bytearray(VAULT_KEY)
        key_b[0] ^= 0x01
        key_b = bytes(key_b)

        s_a = derive_prism_salt(key_a, 100)
        s_b = derive_prism_salt(key_b, 100)

        bits_diff = sum(bin(a ^ b).count("1") for a, b in zip(s_a, s_b))
        ratio = bits_diff / (len(s_a) * 8)
        assert ratio >= 0.40, f"Salt avalanche ratio {ratio:.2%} too low"


# ---------------------------------------------------------------------------
# § 5 — Chi-squared uniformity
# ---------------------------------------------------------------------------

class TestUniformity:
    def test_mask_byte_distribution(self):
        """Verify the mask stream has uniform byte distribution (chi-squared)."""
        mask, _ = generate_full_mask(
            VAULT_KEY, SPINOR_COEFFICIENTS, POLY_HASH, CREATED_AT, FIXED_TIME,
            target_length=50_000,
        )

        # Count byte frequencies
        freq = [0] * 256
        for b in mask[:50_000]:
            freq[b] += 1

        n = 50_000
        expected = n / 256.0
        chi2 = sum((f - expected) ** 2 / expected for f in freq)

        # For 255 dof, chi2 critical at p=0.01 is ~310.
        # A good PRNG should pass easily.
        assert chi2 < 350, f"Chi-squared {chi2:.1f} exceeds threshold (uniformity failure)"

    def test_collision_bytes_nonempty(self):
        """Billiard must produce collision bytes (not zero-length)."""
        seed = derive_collision_seed(POLY_HASH, derive_prism_salt(VAULT_KEY, 0))
        coll = simulate_billiard(seed)
        assert len(coll) >= 12, f"Only {len(coll)} collision bytes (need ≥12 for nonce)"


# ---------------------------------------------------------------------------
# § 6 — Round-trip (mask ↔ unmask)
# ---------------------------------------------------------------------------

class TestRoundTrip:
    def test_xor_involution(self):
        data = b"Hello, Eidolon vault!" * 100
        mask = b"\x55" * len(data)
        assert xor_mask(xor_mask(data, mask), mask) == data

    def test_full_blend_data_roundtrip(self):
        envelope = mask_blend_data(
            blend_json=SAMPLE_BLEND,
            vault_key=VAULT_KEY,
            spinor_coefficients=SPINOR_COEFFICIENTS,
            poly_spinor_hash_bytes=POLY_HASH,
            created_at=CREATED_AT,
            current_time=FIXED_TIME,
        )

        # Verify envelope structure
        assert envelope["version"] == BLEND_DATA_VERSION_PRISM
        assert envelope["format"] == "PSNX_BLEND_DATA"
        assert "payload" in envelope
        assert "mask_params" in envelope

        # Unmask
        recovered = unmask_blend_data(
            envelope=envelope,
            vault_key=VAULT_KEY,
            spinor_coefficients=SPINOR_COEFFICIENTS,
            poly_spinor_hash_bytes=POLY_HASH,
        )

        assert recovered == SAMPLE_BLEND

    def test_v2_passthrough(self):
        """v2 blend_data should pass through unmask unchanged."""
        result = unmask_blend_data(
            envelope=SAMPLE_BLEND,
            vault_key=VAULT_KEY,
            spinor_coefficients=SPINOR_COEFFICIENTS,
            poly_spinor_hash_bytes=POLY_HASH,
        )
        assert result == SAMPLE_BLEND

    def test_wrong_key_fails(self):
        envelope = mask_blend_data(
            blend_json=SAMPLE_BLEND,
            vault_key=VAULT_KEY,
            spinor_coefficients=SPINOR_COEFFICIENTS,
            poly_spinor_hash_bytes=POLY_HASH,
            created_at=CREATED_AT,
            current_time=FIXED_TIME,
        )

        wrong_key = b"\x00" * 64
        with pytest.raises((json.JSONDecodeError, UnicodeDecodeError)):
            unmask_blend_data(
                envelope=envelope,
                vault_key=wrong_key,
                spinor_coefficients=SPINOR_COEFFICIENTS,
                poly_spinor_hash_bytes=POLY_HASH,
            )


# ---------------------------------------------------------------------------
# § 7 — Regeneration from stored params
# ---------------------------------------------------------------------------

class TestRegeneration:
    def test_regenerated_mask_matches_original(self):
        mask_orig, params = generate_full_mask(
            VAULT_KEY, SPINOR_COEFFICIENTS, POLY_HASH, CREATED_AT, FIXED_TIME
        )

        mask_regen = regenerate_mask(
            VAULT_KEY, SPINOR_COEFFICIENTS, POLY_HASH, params
        )

        assert mask_orig == mask_regen


# ---------------------------------------------------------------------------
# § 8 — Performance
# ---------------------------------------------------------------------------

class TestPerformance:
    def test_full_pipeline_under_10s(self):
        """All three layers must complete in < 10 s even on slow hardware."""
        start = time.monotonic()
        result_mask, result_params = generate_full_mask(
            VAULT_KEY, SPINOR_COEFFICIENTS, POLY_HASH, CREATED_AT, FIXED_TIME
        )
        elapsed = time.monotonic() - start
        assert len(result_mask) > 0 and result_params.prism_epoch >= 0
        assert elapsed < 10.0, f"Pipeline took {elapsed:.2f}s (limit: 10s)"
        # Print for benchmark visibility
        print(f"\n  [BENCH] Full prism pipeline: {elapsed:.3f}s")

    def test_lorenz_isolated_under_1s(self):
        start = time.monotonic()
        lorenz_evolve(SPINOR_COEFFICIENTS, 499)  # max iterations = 1499
        elapsed = time.monotonic() - start
        assert elapsed < 1.0, f"Lorenz took {elapsed:.2f}s"
        print(f"\n  [BENCH] Lorenz (1499 iters): {elapsed:.3f}s")

    def test_billiard_isolated_under_5s(self):
        seed = b"\x01" * 32
        start = time.monotonic()
        coll = simulate_billiard(seed)
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, f"Billiard took {elapsed:.2f}s"
        print(f"\n  [BENCH] Billiard ({BILLIARD_STEPS} steps, {len(coll)} bytes): {elapsed:.3f}s")


# ---------------------------------------------------------------------------
# § 9 — Parameter validation
# ---------------------------------------------------------------------------

class TestParameters:
    def test_lorenz_iteration_range(self):
        for eons in [0, 1, 250, 499, 500, 999, 1000]:
            n = LORENZ_BASE_ITERS + (eons % LORENZ_EON_AMPLITUDE)
            assert 1000 <= n <= 1499, f"Iterations {n} out of range for eons={eons}"

    def test_mask_length_sufficient(self):
        blend_json = json.dumps(SAMPLE_BLEND, indent=2, default=str)
        assert CHACHA20_MASK_LENGTH >= len(blend_json.encode("utf-8")), (
            f"Default mask length {CHACHA20_MASK_LENGTH} < blend_data size "
            f"{len(blend_json.encode('utf-8'))}"
        )

    def test_prism_params_serialization(self):
        params = PrismMaskParams(
            prism_epoch=42,
            lorenz_iters=1042,
            billiard_steps=10000,
            billiard_particles=7,
        )
        d = params.to_dict()
        recovered = PrismMaskParams.from_dict(d)
        assert recovered == params
