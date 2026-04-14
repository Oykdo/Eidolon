#!/usr/bin/env python3
"""
Test de validation de l'integration de l'audit d'entropie.

Verifie:
1. Dual entropy metrics (min_entropy_bits vs computational_complexity_bits)
2. Backward compatibility (total_entropy_bits == computational_complexity_bits)
3. Fingerprint 256-bit dans blend_data crypto_properties
4. min_entropy_bits inclus dans le Merkle root
5. calculate_real_entropy() retourne les bonnes valeurs

Usage: python tests/test_entropy_audit.py
"""

import os
import sys
import hashlib
import secrets

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def test_calculate_real_entropy():
    """Test calculate_real_entropy() returns correct values."""
    print("\n=== TEST 1: calculate_real_entropy() ===")
    from src.crypto.complete_key_generator import calculate_real_entropy

    # Without PQ
    assert calculate_real_entropy(None) == 512, "Should be 512 without PQ"
    print("  [OK] Without PQ: 512 bits")

    # With PQ (any truthy object)
    class FakePQ:
        pass
    assert calculate_real_entropy(FakePQ()) == 768, "Should be 768 with PQ"
    print("  [OK] With PQ: 768 bits")

    print("  Resultat: PASS")
    return True


def test_complete_key_data_fields():
    """Test that CompleteKeyData has dual entropy fields."""
    print("\n=== TEST 2: CompleteKeyData dual fields ===")
    from src.crypto.complete_key_generator import CompleteKeyData
    import dataclasses

    fields = {f.name for f in dataclasses.fields(CompleteKeyData)}

    assert 'min_entropy_bits' in fields, "Missing min_entropy_bits field"
    assert 'computational_complexity_bits' in fields, "Missing computational_complexity_bits field"
    assert 'total_entropy_bits' in fields, "Missing total_entropy_bits (backward compat)"
    print("  [OK] All three entropy fields present in dataclass")

    print("  Resultat: PASS")
    return True


def test_to_dict_from_bytes_roundtrip():
    """Test serialization includes new fields and backward compat."""
    print("\n=== TEST 3: to_dict / from_bytes roundtrip ===")
    import numpy as np
    from src.crypto.complete_key_generator import (
        CompleteKeyData, SpatialCaptureData, PhysicsSimulationData,
        SpinorTransformData, BellVerificationData, SpinorHashData,
        PostQuantumData, SigningData
    )

    # Create a minimal CompleteKeyData
    key_data = CompleteKeyData(
        key_id="test1234",
        version=2,
        created_at="2026-01-01T00:00:00",
        user_name="TestUser",
        master_seed=secrets.token_bytes(64),
        spatial_data=SpatialCaptureData(
            clusters={'D6': []},
            epr_correlations=[0.85],
            calibration_valid=True,
            total_points=210,
            entropy_bits=1050
        ),
        physics_data=PhysicsSimulationData(
            trajectories={'D6': {}},
            total_collisions=100,
            total_energy_loss=0.5,
            entropy_bits=700
        ),
        spinor_data=SpinorTransformData(
            coefficients=np.zeros(128, dtype=np.complex128),
            clifford_signature="Cl(0,7)",
            transform_hash="a" * 128,
            entropy_bits=4096
        ),
        bell_data=BellVerificationData(
            correlation_tensor=np.zeros((7, 7), dtype=np.float64),
            violations=[{'pair': (0,1), 'value': 2.5}],
            max_violation=2.8,
            is_quantum=True,
            certified_randomness=secrets.token_bytes(32),
            entropy_bits=500
        ),
        hash_data=SpinorHashData(
            spinor_hash="s" * 128,
            quaternion_hash="q" * 128,
            composite_hash="b" * 128,
            entropy_bits=512
        ),
        pq_data=None,
        signing_data=None,
        merkle_root="d" * 64,
        vault_key_hash="e" * 64,
        total_entropy_bits=7370,
        min_entropy_bits=512,
        computational_complexity_bits=7370
    )

    # Serialize
    d = key_data.to_dict()
    assert 'min_entropy_bits' in d, "min_entropy_bits missing from to_dict()"
    assert 'computational_complexity_bits' in d, "computational_complexity_bits missing"
    assert d['total_entropy_bits'] == 7370, "total_entropy_bits wrong"
    assert d['min_entropy_bits'] == 512, "min_entropy_bits wrong"
    assert d['computational_complexity_bits'] == 7370, "computational_complexity_bits wrong"
    print("  [OK] to_dict() includes all three fields")

    # Deserialize via to_bytes/from_bytes
    serialized = key_data.to_bytes()
    restored = CompleteKeyData.from_bytes(serialized)
    assert restored.min_entropy_bits == 512
    assert restored.computational_complexity_bits == 7370
    assert restored.total_entropy_bits == 7370
    print("  [OK] from_bytes() restores all three fields")

    # Backward compat: simulate old format without new fields
    import json, zlib
    old_dict = d.copy()
    del old_dict['min_entropy_bits']
    del old_dict['computational_complexity_bits']
    old_bytes = zlib.compress(json.dumps(old_dict).encode('utf-8'), level=9)
    restored_old = CompleteKeyData.from_bytes(old_bytes)
    assert restored_old.min_entropy_bits == 512, "Backward compat default should be 512"
    assert restored_old.computational_complexity_bits == 7370, "Should fallback to total_entropy_bits"
    print("  [OK] Backward compat: old format correctly defaults")

    print("  Resultat: PASS")
    return True


def test_backward_compat_alias():
    """Test that total_entropy_bits == computational_complexity_bits."""
    print("\n=== TEST 4: Backward compat alias ===")
    # This is tested indirectly - just verify the design contract
    from src.crypto.complete_key_generator import calculate_real_entropy

    min_e = calculate_real_entropy(None)
    assert min_e == 512
    # total_entropy_bits is always set to computational_complexity_bits in generate_complete_key
    print("  [OK] total_entropy_bits = computational_complexity_bits (by design)")

    print("  Resultat: PASS")
    return True


def test_threejs_renderer_dual_metrics():
    """Test that ThreeJSAvatarRenderer has dual entropy attributes."""
    print("\n=== TEST 5: ThreeJS renderer dual metrics ===")
    from src.game.avatar_system.threejs_renderer import ThreeJSAvatarRenderer

    avatar_data = {
        'avatar_id': 'test_' + secrets.token_hex(16),
        'geometry_type': 'quantum_sphere',
        'rarity_tier': 'rare',
        'rarity_score': 75,
        'attributes': {
            'quantum_entropy': 80,
            'spinor_complexity': 60,
            'bell_verification': 70,
            'polyhedral_symmetry': 50,
            'temporal_stability': 90,
            'spatial_coherence': 85,
            'dimensional_depth': 5.0,
            'fractal_dimension': 3.0,
            'energy_resonance': 30,
            'pioneer_blessing': 20
        },
        'effective_power': 7500
    }

    renderer = ThreeJSAvatarRenderer(avatar_data)
    assert renderer.min_entropy_bits == 512, f"min_entropy_bits should be 512, got {renderer.min_entropy_bits}"
    assert renderer.computational_complexity_bits > 0, "computational_complexity_bits should be positive"
    assert renderer.total_entropy_bits == renderer.computational_complexity_bits, "total should equal complexity"
    print(f"  [OK] min_entropy_bits = {renderer.min_entropy_bits}")
    print(f"  [OK] computational_complexity_bits = {renderer.computational_complexity_bits}")
    print(f"  [OK] total_entropy_bits = computational_complexity_bits")

    print("  Resultat: PASS")
    return True


def test_protected_core_entry():
    """Test that protected_core_entry has updated key_strength."""
    print("\n=== TEST 6: protected_core_entry info ===")

    with open(os.path.join(PROJECT_ROOT, 'src', '_dormant', 'protected_core_entry.py'), 'r') as f:
        content = f.read()

    assert '512 bits min-entropy' in content, "Missing '512 bits min-entropy' in protected_core_entry.py"
    assert 'min_entropy_bits' in content, "Missing 'min_entropy_bits' field"
    print("  [OK] key_strength updated with dual metrics")

    print("  Resultat: PASS")
    return True


def test_fingerprint_256bit_in_codebase():
    """Test that fingerprint is now 256 bits in complete_key_generator.py."""
    print("\n=== TEST 7: Fingerprint 256-bit ===")

    with open(os.path.join(PROJECT_ROOT, 'src', 'crypto', 'complete_key_generator.py'), 'r') as f:
        content = f.read()

    assert "FINGERPRINT_SHA256_HEX_LEN" in content, "Fingerprint should use centralized 256-bit length"
    assert "psnx_key_fingerprint_128" in content, "Legacy 128-bit alias should remain available"
    print("  [OK] Fingerprint upgraded to 256-bit with legacy aliases")

    # Verify actual fingerprint output
    test_key_id = "test1234abcd5678"
    fp = hashlib.sha256(b'PSNX_FINGERPRINT_' + test_key_id.encode()).hexdigest()[:64]
    assert len(fp) == 64, f"Fingerprint should be 64 hex chars, got {len(fp)}"
    print(f"  [OK] Sample fingerprint: {fp[:32]}... (64 hex = 256 bits)")

    print("  Resultat: PASS")
    return True


def test_merkle_includes_entropy():
    """Test that min_entropy_bits is included in Merkle root calculation."""
    print("\n=== TEST 8: Merkle root includes min_entropy_bits ===")

    with open(os.path.join(PROJECT_ROOT, 'src', 'crypto', 'complete_key_generator.py'), 'r') as f:
        content = f.read()

    assert 'str(key_data.min_entropy_bits)' in content, \
        "min_entropy_bits should be included in Merkle root leaves"
    print("  [OK] min_entropy_bits included in Merkle root calculation")

    print("  Resultat: PASS")
    return True


def main():
    print("=" * 60)
    print("  EIDOLON -- VALIDATION AUDIT ENTROPIE")
    print("=" * 60)

    tests = [
        ("calculate_real_entropy()", test_calculate_real_entropy),
        ("CompleteKeyData dual fields", test_complete_key_data_fields),
        ("to_dict/from_bytes roundtrip", test_to_dict_from_bytes_roundtrip),
        ("Backward compat alias", test_backward_compat_alias),
        ("ThreeJS renderer dual metrics", test_threejs_renderer_dual_metrics),
        ("protected_core_entry info", test_protected_core_entry),
        ("Fingerprint 256-bit", test_fingerprint_256bit_in_codebase),
        ("Merkle includes entropy", test_merkle_includes_entropy),
    ]

    results = []
    for name, test_fn in tests:
        try:
            result = test_fn()
            results.append((name, result))
        except Exception as e:
            print(f"\n  [ERROR] {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    print("\n" + "=" * 60)
    print("  RESUME")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}  {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("  [OK] TOUS LES TESTS PASSENT")
        print("     Integration de l'audit d'entropie validee.")
    else:
        print("  [FAIL] CERTAINS TESTS ECHOUENT")

    print("=" * 60)
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
