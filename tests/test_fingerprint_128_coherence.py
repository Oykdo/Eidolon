#!/usr/bin/env python3
"""
Test de coherence historique pour la migration des fingerprints.

Le format canonique est maintenant 256-bit (64 hex), tout en conservant
la compatibilite avec les empreintes legacy 128-bit (32 hex) et 64-bit
(16 hex).
"""

import os
import sys
import hashlib
import secrets
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


from src.crypto.fingerprint_utils import namespaced_key_fingerprint, fingerprints_match
from src.crypto.psnx_signing import PSNXSecurityManager, BlendDataSignature


def fingerprint_64bit(key_id: str) -> str:
    return namespaced_key_fingerprint(key_id, 16)


def fingerprint_128bit(key_id: str) -> str:
    return namespaced_key_fingerprint(key_id, 32)


def fingerprint_256bit(key_id: str) -> str:
    return namespaced_key_fingerprint(key_id, 64)


def signing_fingerprint_64bit(public_key_bytes: bytes) -> str:
    return hashlib.sha256(public_key_bytes).hexdigest()[:16]


def signing_fingerprint_128bit(public_key_bytes: bytes) -> str:
    return hashlib.sha256(public_key_bytes).hexdigest()[:32]


def signing_fingerprint_256bit(public_key_bytes: bytes) -> str:
    return hashlib.sha256(public_key_bytes).hexdigest()[:64]


def test_fingerprint_determinism():
    print("\n=== TEST 1: Determinisme et compatibilite de prefixe ===")

    all_ok = True
    for key_id in ["a" * 16, "b" * 16, "1234567890abcdef", secrets.token_hex(8)]:
        fp_64 = fingerprint_64bit(key_id)
        fp_128 = fingerprint_128bit(key_id)
        fp_256 = fingerprint_256bit(key_id)

        checks = {
            "64_len": len(fp_64) == 16,
            "128_len": len(fp_128) == 32,
            "256_len": len(fp_256) == 64,
            "64_prefix_128": fp_128.startswith(fp_64),
            "128_prefix_256": fp_256.startswith(fp_128),
            "match_64_256": fingerprints_match(fp_64, fp_256),
            "match_128_256": fingerprints_match(fp_128, fp_256),
            "deterministic": fp_256 == fingerprint_256bit(key_id),
        }

        if not all(checks.values()):
            print(f"  [FAIL] key_id={key_id[:8]}... -> {checks}")
            all_ok = False
        else:
            print(f"  [OK]   key_id={key_id[:8]}... -> 64={fp_64} | 128={fp_128} | 256={fp_256[:32]}...")

    print(f"\n  Resultat: {'PASS' if all_ok else 'FAIL'}")
    return all_ok


def test_signing_fingerprint_coherence():
    print("\n=== TEST 2: Coherence du fingerprint de signature Ed25519 ===")

    all_ok = True
    for i in range(5):
        master_seed = secrets.token_bytes(64)
        manager = PSNXSecurityManager(master_seed, f"signing_{i}")
        public_key_bytes = manager.signing_keys.public_key_bytes

        fp_64 = signing_fingerprint_64bit(public_key_bytes)
        fp_128 = signing_fingerprint_128bit(public_key_bytes)
        fp_256 = signing_fingerprint_256bit(public_key_bytes)

        checks = {
            "key_len_ok": len(public_key_bytes) == 32,
            "64_prefix_128": fp_128.startswith(fp_64),
            "128_prefix_256": fp_256.startswith(fp_128),
            "manager_uses_256": manager.signing_keys.public_key_fingerprint == fp_256,
        }

        if not all(checks.values()):
            print(f"  [FAIL] key #{i}: {checks}")
            all_ok = False

    if all_ok:
        print("  [OK]   5/5 paires de cles testees")

    print(f"\n  Resultat: {'PASS' if all_ok else 'FAIL'}")
    return all_ok


def test_full_signing_chain():
    print("\n=== TEST 3: Chaine complete signature/verification 256-bit ===")

    all_ok = True

    for trial in range(3):
        master_seed = secrets.token_bytes(64)
        key_id = hashlib.sha256(master_seed).hexdigest()[:16]
        manager = PSNXSecurityManager(master_seed, key_id)

        blend_data = {
            "format": "PSNX_BLEND_DATA",
            "version": 3,
            "key_id": key_id,
            "user_name": f"TestUser_{trial}",
            "created_at": datetime.utcnow().isoformat(),
            "scene": {"name": "PolySpinorVault"},
            "clusters": [],
            "key_polyhedra": [],
            "materials": {},
            "crypto_properties": {
                "psnx_version": 3,
                "psnx_key_id": key_id,
                "psnx_key_fingerprint": fingerprint_256bit(key_id),
                "psnx_key_fingerprint_128": fingerprint_128bit(key_id),
                "psnx_key_fingerprint_64": fingerprint_64bit(key_id),
            }
        }

        signed = manager.sign_blend_data(blend_data, schema_version=3)
        signature = BlendDataSignature.from_dict(signed["crypto_properties"]["signature"])
        psnx_signing = manager.get_psnx_signing_data()

        verifier = PSNXSecurityManager.create_verifier_from_psnx(psnx_signing)
        result_full = verifier.verify(signed, signature)

        verifier_128 = PSNXSecurityManager.create_verifier_from_psnx({
            **psnx_signing,
            "signing_pubkey_fingerprint": psnx_signing["signing_pubkey_fingerprint_128"]
        })
        result_128 = verifier_128.verify(signed, signature)

        verifier_64 = PSNXSecurityManager.create_verifier_from_psnx({
            **psnx_signing,
            "signing_pubkey_fingerprint": psnx_signing["signing_pubkey_fingerprint_64"]
        })
        result_64 = verifier_64.verify(signed, signature)

        checks = {
            "fp_256_len": len(signed["crypto_properties"]["psnx_key_fingerprint"]) == 64,
            "fp_128_alias_len": len(signed["crypto_properties"]["psnx_key_fingerprint_128"]) == 32,
            "fp_64_alias_len": len(signed["crypto_properties"]["psnx_key_fingerprint_64"]) == 16,
            "verify_256": result_full.valid,
            "verify_128": result_128.valid,
            "verify_64": result_64.valid,
        }

        if not all(checks.values()):
            print(f"  [FAIL] trial={trial}: {checks}")
            all_ok = False
        else:
            print(f"  [OK]   trial={trial}: verification 256/128/64 OK")

    print(f"\n  Resultat: {'PASS' if all_ok else 'FAIL'}")
    return all_ok


def test_collision_resistance():
    print("\n=== TEST 4: Resistance aux collisions ===")

    sample_size = 2000
    fps_64 = set()
    fps_128 = set()
    fps_256 = set()

    for _ in range(sample_size):
        key_id = secrets.token_hex(8)
        fps_64.add(fingerprint_64bit(key_id))
        fps_128.add(fingerprint_128bit(key_id))
        fps_256.add(fingerprint_256bit(key_id))

    collisions_64 = sample_size - len(fps_64)
    collisions_128 = sample_size - len(fps_128)
    collisions_256 = sample_size - len(fps_256)

    ok = collisions_256 <= collisions_128 <= collisions_64
    print(f"  Collisions 64-bit:   {collisions_64}")
    print(f"  Collisions 128-bit:  {collisions_128}")
    print(f"  Collisions 256-bit:  {collisions_256}")
    print(f"\n  Resultat: {'PASS' if ok else 'FAIL'}")
    return ok


def test_backward_compatibility():
    print("\n=== TEST 5: Retrocompatibilite 64/128/256-bit ===")

    key_id = secrets.token_hex(8)
    fp_64 = fingerprint_64bit(key_id)
    fp_128 = fingerprint_128bit(key_id)
    fp_256 = fingerprint_256bit(key_id)

    checks = {
        "64_is_prefix_of_128": fp_128.startswith(fp_64),
        "128_is_prefix_of_256": fp_256.startswith(fp_128),
        "truncate_256_to_128": fp_256[:32] == fp_128,
        "truncate_256_to_64": fp_256[:16] == fp_64,
        "compat_match_64_256": fingerprints_match(fp_64, fp_256),
        "compat_match_128_256": fingerprints_match(fp_128, fp_256),
    }

    passed = sum(1 for value in checks.values() if value)
    total = len(checks)
    print(f"  key_id:  {key_id}")
    print(f"  fp_64:   {fp_64}")
    print(f"  fp_128:  {fp_128}")
    print(f"  fp_256:  {fp_256[:32]}...")
    print(f"  Checks:  {passed}/{total}")

    ok = all(checks.values())
    print(f"\n  Resultat: {'PASS' if ok else 'FAIL'}")
    return ok


def main():
    print("=" * 70)
    print("  EIDOLON -- TEST DE COHERENCE FINGERPRINT 256-BIT")
    print("  Verification du format canonique et des compatibilites legacy")
    print("=" * 70)

    tests = [
        ("Determinisme & prefixe", test_fingerprint_determinism),
        ("Signing Ed25519 coherence", test_signing_fingerprint_coherence),
        ("Chaine signature complete 256-bit", test_full_signing_chain),
        ("Resistance collisions", test_collision_resistance),
        ("Retrocompatibilite 64/128/256-bit", test_backward_compatibility),
    ]

    results = []
    for name, test_fn in tests:
        try:
            results.append((name, test_fn()))
        except Exception as exc:
            print(f"\n  [ERROR] {name}: {exc}")
            results.append((name, False))

    print("\n" + "=" * 70)
    print("  RESUME")
    print("=" * 70)

    all_passed = True
    for name, passed in results:
        print(f"  {'[PASS]' if passed else '[FAIL]'}  {name}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("  [OK] VERDICT: TOUS LES TESTS PASSENT")
        print("     Le format 256-bit est stable et la retrocompatibilite est preservee.")
    else:
        print("  [FAIL] VERDICT: CERTAINS TESTS ECHOUENT")

    print("=" * 70)
    return all_passed


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
