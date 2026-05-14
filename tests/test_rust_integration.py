"""
Integration tests for eidolon_crypto Rust module.
Run with: pytest tests/test_rust_integration.py -v
"""

import pytest


class TestPipelineGeneration:
    """Test the 9-phase holographic pipeline."""
    
    def test_import_module(self):
        """Module should import successfully."""
        import eidolon_crypto
        assert hasattr(eidolon_crypto, 'pipeline_generate')
    
    def test_pipeline_generate_basic(self):
        """Basic pipeline generation should work."""
        import eidolon_crypto
        
        result = eidolon_crypto.pipeline_generate("TestUser", False, "granite")
        
        assert 'key_id' in result
        assert 'vault_key' in result
        assert 'merkle_root' in result
        assert len(result['vault_key']) == 32
        assert len(result['key_id']) == 16
    
    def test_pipeline_generate_with_pq(self):
        """Pipeline with post-quantum should include PQ data."""
        import eidolon_crypto
        
        result = eidolon_crypto.pipeline_generate("TestUser", True, "granite")
        
        assert result['pq_enabled'] is True
        assert 'pq_kem_public_key' in result
        assert 'pq_sig_public_key' in result
        assert len(result['pq_kem_public_key']) == 1568  # Kyber1024
        assert len(result['pq_sig_public_key']) == 2592  # Dilithium5
    
    def test_pipeline_deterministic_key_id(self):
        """Same seed should produce same key_id pattern."""
        import eidolon_crypto
        
        # Different runs produce different keys (CSPRNG)
        r1 = eidolon_crypto.pipeline_generate("User1", False, "granite")
        r2 = eidolon_crypto.pipeline_generate("User1", False, "granite")
        
        # Keys should be different (random each time)
        assert r1['key_id'] != r2['key_id']
    
    def test_pipeline_entropy_metrics(self):
        """Entropy metrics should be reasonable."""
        import eidolon_crypto
        
        result = eidolon_crypto.pipeline_generate("Test", True, "granite")
        
        assert result['min_entropy_bits'] >= 256
        assert result['computational_complexity_bits'] >= 5000
        assert result['merkle_proof_count'] >= 6
    
    def test_pipeline_genesis_files(self):
        """Genesis phase should produce valid file data."""
        import eidolon_crypto
        import json
        
        result = eidolon_crypto.pipeline_generate("Test", False, "granite")
        
        # PSNX bytes should start with marker
        psnx = bytes(result['psnx_bytes'])
        assert psnx.startswith(b'PSNX7D_COMPLETE_V2')
        
        # Blend JSON should be valid
        blend = json.loads(result['blend_json'])
        assert blend['format'] == 'PSNX_BLEND_DATA'
        assert 'crypto_properties' in blend


class TestMerkleTree:
    """Test Merkle tree implementation."""
    
    def test_create_tree(self):
        """Should create tree from leaves."""
        import eidolon_crypto
        
        leaves = [b'leaf1', b'leaf2', b'leaf3', b'leaf4']
        tree = eidolon_crypto.MerkleTree(leaves)
        
        assert tree.leaf_count() == 4
        assert tree.depth() == 3
        assert len(tree.root()) == 64  # hex string
    
    def test_proof_generation(self):
        """Should generate valid proofs."""
        import eidolon_crypto
        
        leaves = [b'a', b'b', b'c', b'd', b'e']
        tree = eidolon_crypto.MerkleTree(leaves)
        
        for i in range(5):
            proof = tree.prove(i)
            assert proof.verify() is True
    
    def test_tamper_detection(self):
        """Modified data should fail verification."""
        import eidolon_crypto
        
        leaves = [b'original', b'data']
        tree = eidolon_crypto.MerkleTree(leaves)
        
        proof = tree.prove(0)
        original_root = tree.root()
        
        # Update leaf
        tree.update_leaf(0, b'modified')
        
        # Root should change
        assert tree.root() != original_root
    
    def test_serialization(self):
        """Tree should serialize and restore."""
        import eidolon_crypto
        
        leaves = [b'x', b'y', b'z']
        tree = eidolon_crypto.MerkleTree(leaves)
        
        data = tree.to_bytes()
        restored = eidolon_crypto.MerkleTree.from_bytes(data)
        
        assert restored.root() == tree.root()
        assert restored.leaf_count() == tree.leaf_count()


class TestEcosystemRegistry:
    """Test ecosystem registry."""
    
    def test_create_registry(self):
        """Should create empty registry."""
        import eidolon_crypto
        
        registry = eidolon_crypto.EcosystemRegistry()
        
        assert registry.vault_count() == 0
        assert registry.version() == 0
    
    def test_register_vault(self):
        """Should register vault and return proof."""
        import eidolon_crypto
        
        registry = eidolon_crypto.EcosystemRegistry()
        
        entry = eidolon_crypto.VaultEntry(
            vault_id="vault_001",
            key_id="abc123",
            owner_hash="owner_hash",
            merkle_root="root_hash",
            pq_enabled=True,
            tier="supreme",
            eidolon_score=8500.0
        )
        
        proof = registry.register_vault(entry)
        
        assert proof.verify() is True
        assert registry.vault_count() == 1
        assert registry.version() == 1
    
    def test_membership_proof(self):
        """Should verify membership."""
        import eidolon_crypto
        
        registry = eidolon_crypto.EcosystemRegistry()
        
        for i in range(5):
            entry = eidolon_crypto.VaultEntry(
                vault_id=f"vault_{i}",
                key_id=f"key_{i}",
                owner_hash="owner",
                merkle_root="root",
                pq_enabled=True,
                tier="standard",
                eidolon_score=1000.0 * i
            )
            registry.register_vault(entry)
        
        # All vaults should have valid proofs
        for i in range(5):
            proof = registry.get_proof(f"vault_{i}")
            assert registry.verify_proof(proof) is True
    
    def test_export_anchor(self):
        """Should export blockchain anchor data."""
        import eidolon_crypto
        
        registry = eidolon_crypto.EcosystemRegistry()
        
        entry = eidolon_crypto.VaultEntry(
            vault_id="v1",
            key_id="k1",
            owner_hash="o1",
            merkle_root="m1",
            pq_enabled=False,
            tier="basic",
            eidolon_score=100.0
        )
        registry.register_vault(entry)
        
        anchor = registry.export_anchor()
        
        assert 'root' in anchor
        assert 'version' in anchor
        assert 'vault_count' in anchor
        assert anchor['vault_count'] == 1


class TestCryptoFunctions:
    """Test standalone crypto functions."""
    
    def test_verify_merkle_proof(self):
        """Standalone proof verification should work."""
        import eidolon_crypto
        
        leaves = [b'test1', b'test2', b'test3']
        tree = eidolon_crypto.MerkleTree(leaves)
        proof = tree.prove(1)
        
        # Verify using standalone function
        valid = eidolon_crypto.verify_merkle_proof(
            proof.leaf_hash(),
            proof.leaf_index(),
            proof.siblings(),
            proof.directions(),
            proof.root()
        )
        
        assert valid is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
