#!/usr/bin/env python3
"""
Tests de compatibilite pour la migration des fingerprints vers 256 bits.
"""

import hashlib
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def test_prefix_compatibility():
    from src.crypto.fingerprint_utils import namespaced_key_fingerprint, fingerprints_match

    key_id = "test1234abcd5678"
    fp_64 = namespaced_key_fingerprint(key_id, 16)
    fp_128 = namespaced_key_fingerprint(key_id, 32)
    fp_256 = namespaced_key_fingerprint(key_id, 64)

    assert fp_128.startswith(fp_64)
    assert fp_256.startswith(fp_128)
    assert fingerprints_match(fp_64, fp_256)
    assert fingerprints_match(fp_128, fp_256)


def test_psnx_signing_accepts_legacy_fingerprint_lengths():
    from src.crypto.psnx_signing import PSNXSecurityManager, BlendDataSignature

    master_seed = hashlib.sha256(b"fingerprint-compat").digest() * 2
    manager = PSNXSecurityManager(master_seed, "compat_vault")

    blend_data = {
        "format": "PSNX_BLEND_DATA",
        "version": 2,
        "key_id": "compat_vault",
        "scene": {"name": "CompatVault"},
        "clusters": [],
        "key_polyhedra": [],
        "materials": {},
        "crypto_properties": {}
    }

    signed = manager.sign_blend_data(blend_data, schema_version=2)
    signature = signed["crypto_properties"]["signature"]

    psnx_signing_data = manager.get_psnx_signing_data()
    assert len(psnx_signing_data["signing_pubkey_fingerprint"]) == 64
    assert len(psnx_signing_data["signing_pubkey_fingerprint_128"]) == 32
    assert len(psnx_signing_data["signing_pubkey_fingerprint_64"]) == 16

    verifier_64 = manager.create_verifier_from_psnx({
        **psnx_signing_data,
        "signing_pubkey_fingerprint": psnx_signing_data["signing_pubkey_fingerprint_64"]
    })
    result_64 = verifier_64.verify(signed, BlendDataSignature.from_dict(signature))
    assert result_64.valid

    verifier_128 = manager.create_verifier_from_psnx({
        **psnx_signing_data,
        "signing_pubkey_fingerprint": psnx_signing_data["signing_pubkey_fingerprint_128"]
    })
    result_128 = verifier_128.verify(signed, BlendDataSignature.from_dict(signature))
    assert result_128.valid
