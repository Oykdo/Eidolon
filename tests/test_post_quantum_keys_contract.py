import hashlib
import unittest

import numpy as np

from src.crypto.post_quantum_keys import (
    McElieceKey,
    NTRUKey,
    SPHINCSKey,
    SPHINCSKeyGenerator,
    TripleEnvelope,
    derive_post_quantum_merkle_leaf,
    derive_post_quantum_merkle_node,
    derive_post_quantum_merkle_root_fallback,
    derive_post_quantum_public_hash,
)


class PostQuantumKeysContractTests(unittest.TestCase):
    def test_public_hash_matches_existing_sha256_contract(self):
        payload = b"post-quantum-public-material"
        expected = hashlib.sha256(payload).hexdigest()

        self.assertEqual(derive_post_quantum_public_hash(payload), expected)

    def test_triple_envelope_to_dict_preserves_existing_hash_contracts(self):
        ntru = NTRUKey(
            n=3,
            q=17,
            f=np.array([1, 0, -1]),
            g=np.array([0, 1, 1]),
            h=np.array([1, 2, 3]),
        )
        mceliece = McElieceKey(
            n=10,
            k=5,
            t=2,
            generator_matrix=np.array([[1, 0], [0, 1]], dtype=np.uint8),
            parity_check=np.array([[1, 1], [0, 1]], dtype=np.uint8),
        )
        sphincs = SPHINCSKey(
            seed=b"seed",
            public_seed=b"public-seed",
            secret_seed=b"secret-seed",
            tree_height=64,
        )

        envelope = TripleEnvelope(ntru_key=ntru, mceliece_key=mceliece, sphincs_key=sphincs)
        data = envelope.to_dict()

        self.assertEqual(data["ntru"]["h_hash"], hashlib.sha256(ntru.to_bytes()).hexdigest())
        self.assertEqual(data["sphincs"]["public_seed_hash"], hashlib.sha256(sphincs.public_seed).hexdigest())

    def test_sphincs_merkle_helpers_match_existing_sha256_contracts(self):
        leaf_payload = b"leaf-payload"
        left = bytes.fromhex("11" * 32)
        right = bytes.fromhex("22" * 32)
        secret = b"secret"
        public = b"public"

        self.assertEqual(derive_post_quantum_merkle_leaf(leaf_payload), hashlib.sha256(leaf_payload).digest())
        self.assertEqual(derive_post_quantum_merkle_node(left, right), hashlib.sha256(left + right).digest())
        self.assertEqual(
            derive_post_quantum_merkle_root_fallback(secret, public),
            hashlib.sha256(secret + public).digest(),
        )

    def test_sphincs_compute_merkle_root_preserves_existing_contract(self):
        generator = SPHINCSKeyGenerator(security_level=256, tree_height=64)
        secret = b"secret-seed"
        public = b"public-seed"

        leaves = [
            hashlib.sha256(secret + public + i.to_bytes(4, "big")).digest()
            for i in range(2 ** min(4, generator.tree_height // 16))
        ]
        while len(leaves) > 1:
            new_leaves = []
            for i in range(0, len(leaves), 2):
                if i + 1 < len(leaves):
                    new_leaves.append(hashlib.sha256(leaves[i] + leaves[i + 1]).digest())
                else:
                    new_leaves.append(leaves[i])
            leaves = new_leaves
        expected = leaves[0] if leaves else hashlib.sha256(secret + public).digest()

        self.assertEqual(generator._compute_merkle_root(secret, public), expected)


if __name__ == "__main__":
    unittest.main()
