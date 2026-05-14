#!/usr/bin/env python3
"""
Eidolon - Basic Usage Examples
==============================

This file demonstrates the core functionality of the Eidolon
post-quantum vault system.

Requirements:
    pip install eidolon-crypto

"""

import eidolon_crypto as ec


def example_1_create_vault():
    """
    Example 1: Create a new vault with the 9-phase holographic pipeline.
    
    The pipeline generates a cryptographically secure vault key using:
    - Phase 1: 512-bit CSPRNG master seed
    - Phase 2: 7D spatial capture with EPR correlations
    - Phase 3: Physics simulation (RK4) with 256 materials
    - Phase 4: Cl(0,7) Clifford algebra transformation
    - Phase 5: Bell 7D inequality verification
    - Phase 6: Composite spinor hash (SHA3-512)
    - Phase 7: Post-quantum crypto (Kyber1024 + Dilithium5)
    - Phase 8: Key derivation (Scrypt + HKDF)
    - Phase 9: Merkle tree + genesis files
    """
    print("=" * 60)
    print("Example 1: Creating a Vault")
    print("=" * 60)
    
    # Generate vault with post-quantum enabled
    result = ec.pipeline_generate(
        user_name="Alice",
        enable_pq=True,          # Enable Kyber + Dilithium
        surface_material="granite"
    )
    
    # Access the results
    print(f"Key ID:      {result['key_id']}")
    print(f"Vault Key:   {result['vault_key'][:8].hex()}... (256-bit)")
    print(f"Merkle Root: {result['merkle_root'][:32]}...")
    print(f"Entropy:     {result['min_entropy_bits']} bits (source)")
    print(f"Complexity:  {result['computational_complexity_bits']} bits")
    print(f"PQ Enabled:  {result['pq_enabled']}")
    
    if result['pq_enabled']:
        print(f"Kyber Key:   {len(result['pq_kem_public_key'])} bytes")
        print(f"Dilithium:   {len(result['pq_sig_public_key'])} bytes")
    
    # Save vault files
    with open("my_vault.psnx", "wb") as f:
        f.write(bytes(result['psnx_bytes']))
    
    with open("my_vault.blend_data", "w") as f:
        f.write(result['blend_json'])
    
    print("\nFiles saved: my_vault.psnx, my_vault.blend_data")
    print()
    
    return result


def example_2_merkle_tree():
    """
    Example 2: Use Merkle trees for data verification.
    
    Merkle trees enable:
    - Efficient proof of inclusion (O(log n))
    - Tamper detection
    - Blockchain anchoring
    """
    print("=" * 60)
    print("Example 2: Merkle Tree Verification")
    print("=" * 60)
    
    # Create a tree from data
    documents = [
        b"Contract v1.0",
        b"Identity proof",
        b"Financial record",
        b"Medical data",
        b"Legal document"
    ]
    
    tree = ec.MerkleTree(documents)
    
    print(f"Documents:   {tree.leaf_count()}")
    print(f"Tree depth:  {tree.depth()}")
    print(f"Root hash:   {tree.root()[:32]}...")
    
    # Generate proof for document #2
    proof = tree.prove(2)
    print(f"\nProof for 'Financial record':")
    print(f"  Leaf hash: {proof.leaf_hash()[:32]}...")
    print(f"  Siblings:  {len(proof.siblings())} hashes")
    print(f"  Valid:     {proof.verify()}")
    
    # Detect tampering
    original_root = tree.root()
    tree.update_leaf(2, b"TAMPERED financial record")
    print(f"\nAfter tampering:")
    print(f"  Root changed: {tree.root() != original_root}")
    print()


def example_3_ecosystem_registry():
    """
    Example 3: Ecosystem registry for vault membership.
    
    The registry enables:
    - Proof of vault membership
    - Cross-vault verification
    - Blockchain anchoring
    """
    print("=" * 60)
    print("Example 3: Ecosystem Registry")
    print("=" * 60)
    
    # Create registry
    registry = ec.EcosystemRegistry()
    
    # Register some vaults
    vaults = []
    for i, name in enumerate(["Alice", "Bob", "Charlie"]):
        # Generate vault
        result = ec.pipeline_generate(name, True, "granite")
        
        # Create entry
        entry = ec.VaultEntry(
            vault_id=f"vault_{i:03d}",
            key_id=result['key_id'],
            owner_hash=f"owner_{name.lower()}",
            merkle_root=result['merkle_root'],
            pq_enabled=result['pq_enabled'],
            tier="supreme" if i == 0 else "standard",
            eidolon_score=8000.0 + i * 500
        )
        
        # Register and get membership proof
        proof = registry.register_vault(entry)
        vaults.append((name, proof))
        print(f"Registered {name}: proof valid = {proof.verify()}")
    
    print(f"\nRegistry stats:")
    print(f"  Total vaults: {registry.vault_count()}")
    print(f"  Version:      {registry.version()}")
    print(f"  Root:         {registry.root()[:32]}...")
    
    # Export for blockchain anchoring
    anchor = registry.export_anchor()
    print(f"\nBlockchain anchor data:")
    print(f"  Root:       {anchor['root'][:32]}...")
    print(f"  Timestamp:  {anchor['timestamp']}")
    print(f"  Vaults:     {anchor['vault_count']}")
    print()


def example_4_standalone_verification():
    """
    Example 4: Verify a proof without the original tree.
    
    Useful for:
    - Third-party verification
    - Offline validation
    - API responses
    """
    print("=" * 60)
    print("Example 4: Standalone Proof Verification")
    print("=" * 60)
    
    # Create tree and proof
    tree = ec.MerkleTree([b"data1", b"data2", b"data3"])
    proof = tree.prove(1)
    
    # Extract proof components (e.g., from JSON API response)
    leaf_hash = proof.leaf_hash()
    leaf_index = proof.leaf_index()
    siblings = proof.siblings()
    directions = proof.directions()
    root = proof.root()
    
    # Verify without the tree
    is_valid = ec.verify_merkle_proof(
        leaf_hash_hex=leaf_hash,
        leaf_index=leaf_index,
        siblings_hex=siblings,
        directions=directions,
        root_hex=root
    )
    
    print(f"Proof components:")
    print(f"  Leaf hash:  {leaf_hash[:32]}...")
    print(f"  Leaf index: {leaf_index}")
    print(f"  Siblings:   {len(siblings)}")
    print(f"  Root:       {root[:32]}...")
    print(f"\nVerification: {'VALID' if is_valid else 'INVALID'}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  EIDOLON - Post-Quantum Vault System")
    print("  Usage Examples")
    print("=" * 60 + "\n")
    
    example_1_create_vault()
    example_2_merkle_tree()
    example_3_ecosystem_registry()
    example_4_standalone_verification()
    
    print("=" * 60)
    print("  All examples completed successfully!")
    print("=" * 60)
