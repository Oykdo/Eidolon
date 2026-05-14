import hashlib
import unittest

from src.crypto.real_post_quantum import PQAlgorithm, PQKeyPair, PQSecurityLevel, derive_pq_public_key_hash


class RealPostQuantumContractTests(unittest.TestCase):
    def test_public_key_hash_matches_existing_sha256_prefix_contract(self):
        public_key = b"pq-public-key-fixture"
        expected = hashlib.sha256(public_key).hexdigest()[:16]

        self.assertEqual(derive_pq_public_key_hash(public_key), expected)

    def test_pq_keypair_public_key_hash_matches_existing_contract(self):
        keypair = PQKeyPair(
            algorithm=PQAlgorithm.ML_DSA,
            public_key=b"another-public-key",
            secret_key=b"secret",
            security_level=PQSecurityLevel.LEVEL_3,
        )
        expected = hashlib.sha256(keypair.public_key).hexdigest()[:16]

        self.assertEqual(keypair.public_key_hash(), expected)


if __name__ == "__main__":
    unittest.main()
