"""Test des implémentations post-quantiques réelles"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.crypto.real_post_quantum import (
    HybridPQCryptoSystem, 
    RealMcElieceKEM,
    RealHQCKEM,
    RealMLDSASignature,
    RealFalconSignature,
    RealSPHINCSSignature,
    check_pqcrypto_available
)

def test_mceliece():
    print('\n--- Test McEliece KEM ---')
    mc = RealMcElieceKEM()
    keypair = mc.generate_keypair()
    print(f'Public key: {len(keypair.public_key)} bytes')
    print(f'Secret key: {len(keypair.secret_key)} bytes')
    
    encap = mc.encapsulate(keypair.public_key)
    print(f'Ciphertext: {len(encap.ciphertext)} bytes')
    print(f'Shared secret: {len(encap.shared_secret)} bytes')
    
    decap_secret = mc.decapsulate(encap.ciphertext, keypair.secret_key)
    assert decap_secret == encap.shared_secret, 'McEliece KEM FAILED!'
    print('[OK] McEliece KEM')
    return True

def test_hqc():
    print('\n--- Test HQC KEM ---')
    hqc = RealHQCKEM()
    keypair = hqc.generate_keypair()
    print(f'Public key: {len(keypair.public_key)} bytes')
    
    encap = hqc.encapsulate(keypair.public_key)
    decap = hqc.decapsulate(encap.ciphertext, keypair.secret_key)
    
    assert decap == encap.shared_secret, 'HQC KEM FAILED!'
    print('[OK] HQC KEM')
    return True

def test_mldsa():
    print('\n--- Test ML-DSA (Dilithium) ---')
    mldsa = RealMLDSASignature()
    keypair = mldsa.generate_keypair()
    print(f'Public key: {len(keypair.public_key)} bytes')
    
    message = b'Test message for ML-DSA signature!'
    sig = mldsa.sign(message)
    print(f'Signature: {len(sig.signature)} bytes')
    
    valid = mldsa.verify(message, sig.signature)
    assert valid, 'ML-DSA verification FAILED!'
    print(f'Valid signature: {valid}')
    
    # Test avec message modifié - devrait retourner False ou lever exception
    try:
        invalid = mldsa.verify(b'Modified message', sig.signature)
        # Si on arrive ici sans exception, invalid devrait être False
        print(f'Modified message rejected: {not invalid}')
    except Exception:
        print('Modified message rejected (exception)')
    
    print('[OK] ML-DSA Signature')
    return True

def test_falcon():
    print('\n--- Test Falcon ---')
    falcon = RealFalconSignature()
    keypair = falcon.generate_keypair()
    print(f'Public key: {len(keypair.public_key)} bytes')
    
    message = b'Test message for Falcon!'
    sig = falcon.sign(message)
    print(f'Signature: {len(sig.signature)} bytes')
    
    valid = falcon.verify(message, sig.signature)
    assert valid, 'Falcon verification FAILED!'
    print('[OK] Falcon Signature')
    return True

def test_sphincs():
    print('\n--- Test SPHINCS+ ---')
    sphincs = RealSPHINCSSignature()
    keypair = sphincs.generate_keypair()
    print(f'Public key: {len(keypair.public_key)} bytes')
    
    message = b'Test message for SPHINCS+!'
    sig = sphincs.sign(message)
    print(f'Signature: {len(sig.signature)} bytes')
    
    valid = sphincs.verify(message, sig.signature)
    assert valid, 'SPHINCS+ verification FAILED!'
    print('[OK] SPHINCS+ Signature')
    return True

def test_hybrid():
    print('\n--- Test Hybrid System ---')
    hybrid = HybridPQCryptoSystem()
    keys = hybrid.generate_all_keys()
    print(f'Keys generated: {list(keys.keys())}')
    
    # Test hybrid encapsulation
    ct, secret = hybrid.hybrid_encapsulate(
        keys['mceliece'].public_key,
        keys['hqc'].public_key
    )
    print(f'Hybrid ciphertext: {len(ct)} bytes')
    
    decap = hybrid.hybrid_decapsulate(
        ct,
        keys['mceliece'].secret_key,
        keys['hqc'].secret_key
    )
    assert decap == secret, 'Hybrid encapsulation FAILED!'
    print('[OK] Hybrid KEM')
    
    # Test dual signature
    message = b'Important document to sign!'
    sigs = hybrid.dual_sign(
        message,
        keys['mldsa'].secret_key,
        keys['falcon'].secret_key
    )
    
    all_valid, results = hybrid.dual_verify(
        message, sigs,
        keys['mldsa'].public_key,
        keys['falcon'].public_key
    )
    assert all_valid, 'Dual signature FAILED!'
    print(f'[OK] Dual Signature: {results}')
    
    return True

def main():
    print('=== TEST REAL POST-QUANTUM CRYPTO ===')
    print(f'pqcrypto available: {check_pqcrypto_available()}')
    
    if not check_pqcrypto_available():
        print('ERROR: pqcrypto not available!')
        return False
    
    tests = [
        ('McEliece KEM', test_mceliece),
        ('HQC KEM', test_hqc),
        ('ML-DSA', test_mldsa),
        ('Falcon', test_falcon),
        ('SPHINCS+', test_sphincs),
        ('Hybrid System', test_hybrid),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f'[ERROR] {name}: {e}')
            results.append((name, False))
    
    print('\n=== SUMMARY ===')
    all_passed = True
    for name, passed in results:
        status = '[OK]' if passed else '[FAIL]'
        print(f'{status} {name}')
        if not passed:
            all_passed = False
    
    if all_passed:
        print('\n=== VULN-CRYPTO-02 CORRIGEE ===')
    
    return all_passed

if __name__ == '__main__':
    main()
