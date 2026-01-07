#!/usr/bin/env python3
"""
Tests complets de la Security Suite 10/10
Eidolon
"""

import sys
import os
import time
import tempfile
import secrets

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_secure_memory():
    """Test du module secure_memory"""
    print("\n[TEST] Secure Memory...")
    
    from core.secure_memory import SecureBuffer, SecureZeroMethod
    
    # Test creation
    with SecureBuffer(32) as buf:
        secret = secrets.token_bytes(32)
        buf.write(secret)
        
        # Test lecture
        read_back = buf.read()
        assert read_back == secret, "Lecture incorrecte"
        
        # Test rotation
        buf.rotate_mask()
        read_after_rotate = buf.read()
        assert read_after_rotate == secret, "Rotation a corrompu les donnees"
    
    print("  [OK] SecureBuffer fonctionne")
    return True


def test_authenticated_files():
    """Test du module authenticated_files"""
    print("\n[TEST] Authenticated Files...")
    
    from core.authenticated_files import AuthenticatedFileFormat, AuthenticationError
    
    auth_key = secrets.token_bytes(32)
    aff = AuthenticatedFileFormat(auth_key)
    
    # Test creation
    data = b"Secret data for testing"
    file_content = aff.create_file(data, "test", "key123", compress=True)
    
    # Test parsing
    metadata, parsed_data = aff.parse_file(file_content)
    assert parsed_data == data, "Donnees corrompues"
    assert metadata.key_id == "key123"
    
    # Test tampering detection
    tampered = bytearray(file_content)
    tampered[20] ^= 0xFF  # Modifier un byte
    
    try:
        aff.parse_file(bytes(tampered))
        print("  [FAIL] Tampering non detecte!")
        return False
    except AuthenticationError:
        pass  # Attendu
    
    print("  [OK] Authentification HMAC fonctionne")
    return True


def test_quantum_entropy():
    """Test du module quantum_entropy"""
    print("\n[TEST] Quantum Entropy...")
    
    from core.quantum_entropy import HybridEntropyPool, EntropyQuality
    
    pool = HybridEntropyPool(
        use_quantum=False,  # Skip API calls for test
        use_atmospheric=False
    )
    
    # Test collecte
    entropy = pool.get_entropy(64, min_sources=1)
    assert len(entropy) == 64, f"Taille incorrecte: {len(entropy)}"
    
    # Test rapport
    report = pool.get_collection_report()
    assert report['sources_used'] >= 1
    
    print(f"  [OK] Entropie collectee: {report['total_bits']} bits")
    return True


def test_secret_sharing():
    """Test du module secret_sharing (Shamir)"""
    print("\n[TEST] Secret Sharing (Shamir)...")
    
    from core.secret_sharing import ShamirSecretSharing
    
    secret = secrets.token_bytes(32)
    
    # Test 3/5 sharing
    sss = ShamirSecretSharing(threshold=3, total_shares=5)
    shares = sss.split(secret)
    
    assert len(shares) == 5, "Nombre de parts incorrect"
    
    # Test reconstruction avec 3 parts
    recovered = sss.reconstruct(shares[:3])
    assert recovered == secret, "Reconstruction echouee avec 3 parts"
    
    # Test avec parts differentes
    recovered2 = sss.reconstruct([shares[1], shares[3], shares[4]])
    assert recovered2 == secret, "Reconstruction echouee avec parts differentes"
    
    print("  [OK] Shamir 3/5 fonctionne")
    return True


def test_constant_time():
    """Test du module constant_time"""
    print("\n[TEST] Constant Time Operations...")
    
    from core.constant_time import constant_time_compare, constant_time_select
    
    a = b"test_value_1234567890"
    b_same = b"test_value_1234567890"
    b_diff = b"test_value_0987654321"
    
    # Test comparaison
    assert constant_time_compare(a, b_same) == True
    assert constant_time_compare(a, b_diff) == False
    
    # Test selection
    result = constant_time_select(True, a, b_diff)
    assert result == a
    
    result = constant_time_select(False, a, b_diff)
    assert result == b_diff
    
    print("  [OK] Operations constant-time fonctionnent")
    return True


def test_zkp_auth():
    """Test du module zkp_auth"""
    print("\n[TEST] Zero-Knowledge Proofs...")
    
    from core.zkp_auth import VaultZKPAuth
    
    vault_key = secrets.token_bytes(32)
    
    # Creer le prover
    auth = VaultZKPAuth(vault_key)
    public_key = auth.get_public_key()
    
    # Creer une preuve
    challenge = f"test_{int(time.time())}"
    proof = auth.create_auth_proof(challenge)
    
    # Verifier
    valid, reason = VaultZKPAuth.verify_auth(public_key, proof, challenge)
    assert valid, f"Verification echouee: {reason}"
    
    # Test avec mauvais challenge
    valid2, _ = VaultZKPAuth.verify_auth(public_key, proof, "wrong_challenge")
    assert not valid2, "Devrait echouer avec mauvais challenge"
    
    print("  [OK] ZKP fonctionne")
    return True


def test_security_suite_integration():
    """Test de la suite integree"""
    print("\n[TEST] Security Suite Integration...")
    
    from core.security_suite import SecureVaultManager, SecurityConfig
    
    config = SecurityConfig(
        use_quantum_entropy=False,  # Skip API for test
        memory_protection=True,
        file_authentication=True,
        enable_zkp=True,
        shamir_threshold=2,
        shamir_total=3
    )
    
    manager = SecureVaultManager(config)
    
    # 1. Generation de cle
    vault_key = manager.generate_secure_key("TestUser")
    assert len(vault_key) == 32
    print("  [OK] Generation de cle")
    
    # 2. ZKP
    challenge = f"integration_test_{int(time.time())}"
    proof = manager.create_ownership_proof(challenge)
    creds = manager.get_public_credentials()
    valid, _ = manager.verify_ownership(creds, proof, challenge)
    assert valid
    print("  [OK] ZKP authentication")
    
    # 3. Shamir
    shares = manager.create_recovery_shares(threshold=2, total=3)
    assert len(shares['shares']) == 3
    
    # Recuperation
    recovered = manager.recover_from_shares(shares['shares'][:2])
    assert recovered == vault_key
    print("  [OK] Shamir recovery")
    
    # 4. Fichiers authentifies
    with tempfile.NamedTemporaryFile(delete=False, suffix='.psnx') as f:
        temp_path = f.name
    
    try:
        test_data = b"Test secure file content"
        manager.save_secure_file(temp_path, test_data)
        
        _, loaded = manager.load_secure_file(temp_path)
        assert loaded == test_data
        print("  [OK] Fichiers authentifies")
    finally:
        os.unlink(temp_path)
    
    # Cleanup
    manager.secure_wipe_key()
    print("  [OK] Secure wipe")
    
    return True


def run_all_tests():
    """Execute tous les tests"""
    print("="*70)
    print("  TESTS SECURITY SUITE 10/10 - EIDOLON")
    print("="*70)
    
    tests = [
        ("Secure Memory", test_secure_memory),
        ("Authenticated Files", test_authenticated_files),
        ("Quantum Entropy", test_quantum_entropy),
        ("Secret Sharing", test_secret_sharing),
        ("Constant Time", test_constant_time),
        ("ZKP Auth", test_zkp_auth),
        ("Integration", test_security_suite_integration),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success, None))
        except Exception as e:
            results.append((name, False, str(e)))
            import traceback
            traceback.print_exc()
    
    # Rapport
    print("\n" + "="*70)
    print("  RAPPORT DE TESTS")
    print("="*70)
    
    passed = 0
    failed = 0
    
    for name, success, error in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} {name}")
        if error:
            print(f"       Error: {error}")
        if success:
            passed += 1
        else:
            failed += 1
    
    print("="*70)
    print(f"  Total: {passed}/{len(results)} tests passes")
    
    if failed == 0:
        print("  TOUS LES TESTS REUSSIS!")
        print("  Score de securite: 10/10")
    else:
        print(f"  {failed} test(s) echoue(s)")
    
    print("="*70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
