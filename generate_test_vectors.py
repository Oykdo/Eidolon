#!/usr/bin/env python3
"""Generate test vectors for Eidolon cryptographic operations."""

import eidolon_crypto
import json
import hashlib

vectors = []

# 1. AES-GCM roundtrip
key = bytes(32)
nonce = bytes(12)
plaintext = b"Eidolon test vector"
aad = b""
ct = eidolon_crypto.aes_gcm_encrypt(key, nonce, plaintext, aad)
back = eidolon_crypto.aes_gcm_decrypt(key, ct, aad)
vectors.append({
    "operation": "aes_gcm_roundtrip",
    "key_sha256": hashlib.sha256(key).hexdigest(),
    "nonce_sha256": hashlib.sha256(nonce).hexdigest(),
    "plaintext_hex": plaintext.hex(),
    "ciphertext_len": len(ct),
    "roundtrip_ok": back == plaintext,
})

# 2. Shamir secret sharing
secret = bytes(range(1, 33))
shares = eidolon_crypto.shamir_split_v1(secret, threshold=3, total_shares=5)
reconstructed = eidolon_crypto.shamir_reconstruct_v1(
    [shares[0]["data"], shares[2]["data"], shares[4]["data"]],
    share_indices=[shares[0]["index"], shares[2]["index"], shares[4]["index"]],
    threshold=3,
)
vectors.append({
    "operation": "shamir_split_reconstruct",
    "secret_sha256": hashlib.sha256(secret).hexdigest(),
    "threshold": 3,
    "total_shares": 5,
    "shares_used_indices": [shares[0]["index"], shares[2]["index"], shares[4]["index"]],
    "reconstructed_sha256": hashlib.sha256(reconstructed).hexdigest(),
    "roundtrip_ok": reconstructed == secret,
})

# 3. ZKP scalar derivation
vault_secret = b"test_vector_vault_key_32bytes_pad!"
scalar = eidolon_crypto.zkp_scalar_from_secret(vault_secret)
pubkey = eidolon_crypto.zkp_public_key_from_scalar(scalar)
vectors.append({
    "operation": "zkp_scalar_from_secret",
    "input_sha256": hashlib.sha256(vault_secret).hexdigest(),
    "scalar_hex_prefix": str(scalar)[:34],
    "public_key_hex_prefix": str(pubkey)[:34],
})

# 4. Full pipeline
result = eidolon_crypto.pipeline_generate("TestVector", True, "granite")
vault_key = bytes(result["vault_key"])
vectors.append({
    "operation": "pipeline_generate",
    "seed_material": "TestVector",
    "pq_enabled": True,
    "material": "granite",
    "key_id": result["key_id"],
    "merkle_root": result["merkle_root"][:64],
    "min_entropy_bits": int(result["min_entropy_bits"]),
    "computational_complexity_bits": int(result["computational_complexity_bits"]),
    "psnx_bytes_len": len(result["psnx_bytes"]),
    "vault_key_sha256": hashlib.sha256(vault_key).hexdigest(),
    "pq_kem_pubkey_sha256": hashlib.sha256(bytes(result["pq_kem_public_key"])).hexdigest(),
    "pq_sig_pubkey_sha256": hashlib.sha256(bytes(result["pq_sig_public_key"])).hexdigest(),
})

with open("docs/TEST_VECTORS.json", "w") as f:
    json.dump(vectors, f, indent=2)

print(f"Written {len(vectors)} test vectors to docs/TEST_VECTORS.json")
