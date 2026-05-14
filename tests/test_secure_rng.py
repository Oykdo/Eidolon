"""Test du générateur aléatoire sécurisé - VULN-CRYPTO-03 FIX"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.holo.material_simulation_pipeline import (
    SecureRandomGenerator,
    MaterialBasedInitialConditions
)
from src.holo.material_database import MATERIAL_DB
from src.holo.physics_engine import PolyhedronType


def test_secure_rng_determinism():
    """Test que le RNG est déterministe avec la même seed"""
    print("\n--- Test Déterminisme ---")
    
    seed = b"test_seed_32_bytes_exactly_here!"
    
    rng1 = SecureRandomGenerator(seed)
    rng2 = SecureRandomGenerator(seed)
    
    # Même contexte = même résultat
    val1 = rng1.normal(0, 1, context="test_context")
    val2 = rng2.normal(0, 1, context="test_context")
    
    print(f"RNG1 value: {val1}")
    print(f"RNG2 value: {val2}")
    assert val1 == val2, "Déterminisme échoué!"
    print("[OK] Déterminisme vérifié")


def test_secure_rng_uniqueness():
    """Test que différentes seeds produisent différentes valeurs"""
    print("\n--- Test Unicité ---")
    
    rng1 = SecureRandomGenerator(b"seed_one_32_bytes_exactly_here!")
    rng2 = SecureRandomGenerator(b"seed_two_32_bytes_exactly_here!")
    
    val1 = rng1.normal(0, 1, context="same_context")
    val2 = rng2.normal(0, 1, context="same_context")
    
    print(f"Seed1 value: {val1}")
    print(f"Seed2 value: {val2}")
    assert val1 != val2, "Seeds différentes devraient produire valeurs différentes!"
    print("[OK] Unicité vérifiée")


def test_secure_rng_context_isolation():
    """Test que différents contextes produisent différentes valeurs"""
    print("\n--- Test Isolation de Contexte ---")
    
    seed = b"test_seed_32_bytes_exactly_here!"
    rng = SecureRandomGenerator(seed)
    
    val1 = rng.normal(0, 1, context="context_a")
    val2 = rng.normal(0, 1, context="context_b")
    
    print(f"Context A: {val1}")
    print(f"Context B: {val2}")
    assert val1 != val2, "Contextes différents devraient produire valeurs différentes!"
    print("[OK] Isolation de contexte vérifiée")


def test_material_initial_conditions_reproducibility():
    """Test que MaterialBasedInitialConditions est reproductible"""
    print("\n--- Test Reproductibilité MaterialBasedInitialConditions ---")
    
    seed = b"material_test_seed_32_bytes_ok!!"
    
    gen1 = MaterialBasedInitialConditions(master_seed=seed)
    gen2 = MaterialBasedInitialConditions(master_seed=seed)
    
    material = MATERIAL_DB.get_material('tungsten')
    poly_type = PolyhedronType.D20
    
    params1 = gen1.generate_throw_parameters(material, poly_type, 0)
    params2 = gen2.generate_throw_parameters(material, poly_type, 0)
    
    print(f"Params1 height: {params1.position[2]:.6f}")
    print(f"Params2 height: {params2.position[2]:.6f}")
    
    # Vérifier que les paramètres sont identiques
    assert params1.position[2] == params2.position[2], "Hauteur non reproductible!"
    assert all(params1.velocity == params2.velocity), "Vitesse non reproductible!"
    assert all(params1.orientation == params2.orientation), "Orientation non reproductible!"
    
    print("[OK] MaterialBasedInitialConditions reproductible")


def test_from_user_secret():
    """Test la création depuis un secret utilisateur"""
    print("\n--- Test from_user_secret ---")
    
    user_secret = b"mon_mot_de_passe_secret"
    salt = b"mon_sel_unique"
    
    rng1 = SecureRandomGenerator.from_user_secret(user_secret, salt)
    rng2 = SecureRandomGenerator.from_user_secret(user_secret, salt)
    
    val1 = rng1.uniform(0, 100, context="test")
    val2 = rng2.uniform(0, 100, context="test")
    
    print(f"User secret RNG1: {val1}")
    print(f"User secret RNG2: {val2}")
    assert val1 == val2, "from_user_secret non déterministe!"
    
    # Test avec sel différent
    rng3 = SecureRandomGenerator.from_user_secret(user_secret, b"autre_sel")
    val3 = rng3.uniform(0, 100, context="test")
    assert val1 != val3, "Sels différents devraient produire valeurs différentes!"
    
    print("[OK] from_user_secret fonctionne")


def test_crypto_quality():
    """Test basique de qualité cryptographique"""
    print("\n--- Test Qualité Crypto ---")
    
    rng = SecureRandomGenerator()
    
    # Générer beaucoup de valeurs
    values = [rng.uniform(0, 1) for _ in range(1000)]
    
    # Vérifier la distribution (devrait être ~0.5 en moyenne)
    mean = sum(values) / len(values)
    print(f"Moyenne de 1000 valeurs uniformes: {mean:.4f} (attendu: ~0.5)")
    
    assert 0.4 < mean < 0.6, "Distribution uniforme suspecte!"
    
    # Vérifier que la master seed est bien 32 bytes hex (64 chars)
    seed_hex = rng.get_master_seed_hex()
    print(f"Master seed (hex): {seed_hex[:16]}...")
    assert len(seed_hex) == 64, "Master seed devrait être 32 bytes (64 hex chars)"
    
    print("[OK] Qualité crypto basique vérifiée")


def main():
    print("=== TEST SECURE RANDOM GENERATOR ===")
    print("=== VULN-CRYPTO-03 FIX VALIDATION ===")
    
    tests = [
        ("Déterminisme", test_secure_rng_determinism),
        ("Unicité", test_secure_rng_uniqueness),
        ("Isolation Contexte", test_secure_rng_context_isolation),
        ("Reproductibilité Material", test_material_initial_conditions_reproducibility),
        ("from_user_secret", test_from_user_secret),
        ("Qualité Crypto", test_crypto_quality),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n=== SUMMARY ===")
    all_passed = True
    for name, passed in results:
        status = "[OK]" if passed else "[FAIL]"
        print(f"{status} {name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n=== VULN-CRYPTO-03 CORRIGEE ===")
    
    return all_passed


if __name__ == "__main__":
    main()
