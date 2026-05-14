import hashlib
import json
import unittest

from src.core.avatar_merkle_tree import (
    AvatarLeaf,
    AvatarMerkleTree,
    derive_avatar_empty_hash,
    derive_avatar_empty_root_hash,
    derive_avatar_leaf_hash,
    derive_avatar_metadata_hash,
    MerkleProof,
    derive_avatar_pair_hash,
    derive_merkle_publication_id,
)


class AvatarMerkleTreeContractTests(unittest.TestCase):
    def test_avatar_leaf_hash_matches_existing_sha256_contract(self):
        leaf = AvatarLeaf(
            avatar_id="avatar-001",
            owner_fingerprint="owner-fp",
            rarity="mythic",
            created_at="2026-04-03T12:00:00+00:00",
            metadata_hash="deadbeef",
        )
        data = json.dumps(leaf.to_dict(), sort_keys=True).encode()
        expected = hashlib.sha256(data).hexdigest()

        self.assertEqual(derive_avatar_leaf_hash(data), expected)
        self.assertEqual(leaf.compute_hash(), expected)

    def test_empty_hash_matches_existing_sha256_contract(self):
        expected = hashlib.sha256(b"EMPTY_LEAF").hexdigest()

        self.assertEqual(derive_avatar_empty_hash(), expected)
        self.assertEqual(AvatarMerkleTree("owner-fp")._empty_hash(), expected)

    def test_empty_root_hash_matches_existing_sha256_contract(self):
        expected = hashlib.sha256(b"empty").hexdigest()

        self.assertEqual(derive_avatar_empty_root_hash(), expected)
        tree = AvatarMerkleTree("owner-fp")
        tree._rebuild_tree()
        self.assertEqual(tree.root_hash, expected)

    def test_metadata_hash_matches_existing_sha256_contract(self):
        metadata = {"rarity_score": 99, "traits": ["glow", "mythic"]}
        expected = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()

        self.assertEqual(derive_avatar_metadata_hash(metadata), expected)

    def test_publication_id_matches_existing_sha256_prefix_contract(self):
        owner_fingerprint = "owner-fp"
        root_hash = "abc123root"
        timestamp = "2026-04-03T12:00:00+00:00"
        expected = hashlib.sha256(
            f"{owner_fingerprint}{root_hash}{timestamp}".encode()
        ).hexdigest()[:16]

        self.assertEqual(
            derive_merkle_publication_id(owner_fingerprint, root_hash, timestamp),
            expected,
        )

    def test_pair_hash_matches_existing_sorted_sha256_contract(self):
        left = "ff00"
        right = "00aa"
        expected = hashlib.sha256(f"{right}{left}".encode()).hexdigest()

        self.assertEqual(derive_avatar_pair_hash(left, right), expected)
        self.assertEqual(AvatarMerkleTree("owner-fp")._hash_pair(left, right), expected)

    def test_verify_proof_matches_existing_sorted_sha256_contract(self):
        leaf_hash = hashlib.sha256(b"leaf").hexdigest()
        sibling_hash = hashlib.sha256(b"sibling").hexdigest()
        combined = (
            f"{leaf_hash}{sibling_hash}"
            if leaf_hash < sibling_hash
            else f"{sibling_hash}{leaf_hash}"
        )
        root_hash = hashlib.sha256(combined.encode()).hexdigest()
        proof = MerkleProof(
            leaf_index=0,
            leaf_hash=leaf_hash,
            proof_hashes=[sibling_hash],
            proof_directions=["right"],
            root_hash=root_hash,
        )

        self.assertTrue(AvatarMerkleTree.verify_proof(proof))


if __name__ == "__main__":
    unittest.main()
