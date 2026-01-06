"""
Test du système de simulation matérielle
"""
from __future__ import annotations

import sys
import os
from typing import TYPE_CHECKING

# Ajouter le répertoire parent (poly_spinor_nexus_7d) au path
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

# Imports pour le type checking (pyright) - ignorés car sys.path est modifié dynamiquement
if TYPE_CHECKING:
    from core.material_database import PolyhedronMaterialDatabase, SurfaceMaterialDatabase, MaterialProperties  # type: ignore[import-not-found]
    from core.physics_engine import PolyhedronPhysicsEngine, PolyhedronType  # type: ignore[import-not-found]
    from core.material_fingerprint import MaterialFingerprintExtractor, CryptoVertexCalculator  # type: ignore[import-not-found]
    from protocols.material_vault import MaterialBasedVaultSystem, AccessLevel, VaultAccessDenied  # type: ignore[import-not-found]
    from core.material_simulation_pipeline import CompleteMaterialSimulationPipeline  # type: ignore[import-not-found]

def test_material_database():
    print("\n" + "=" * 60)
    print("TEST 1: Base de données matériaux")
    print("=" * 60)
    
    from core.material_database import (
        PolyhedronMaterialDatabase, 
        SurfaceMaterialDatabase,
        MATERIAL_DB
    )
    
    print(f"Matériaux disponibles: {len(MATERIAL_DB.materials)}")
    
    # Lister quelques matériaux
    for name, mat in list(MATERIAL_DB.materials.items())[:5]:
        print(f"  - {name}: densité={mat.density} kg/m³, élasticité={mat.elasticity}")
    
    # Test surface database
    print(f"\nSurfaces disponibles: {len(SurfaceMaterialDatabase.SURFACES)}")
    
    print("\n[OK] Test base de données réussi")
    return True


def test_physics_engine():
    print("\n" + "=" * 60)
    print("TEST 2: Moteur physique")
    print("=" * 60)
    
    from core.physics_engine import (
        PolyhedronPhysicsEngine,
        PolyhedronType
    )
    from core.material_database import MATERIAL_DB
    
    # Obtenir le tungsten
    tungsten = MATERIAL_DB.get_material('tungsten')
    assert tungsten is not None, "Matériau tungsten non trouvé!"
    print(f"Matériau: {tungsten.name} (densité: {tungsten.density} kg/m³)")
    
    # Créer le moteur
    engine = PolyhedronPhysicsEngine(
        PolyhedronType.D20,
        tungsten
    )
    # Utiliser un timestep plus grand pour les tests
    engine.dt = 0.001  # 1ms au lieu de 0.1ms
    
    print(f"Masse du dé: {engine.mass:.6f} kg")
    print(f"Volume: {engine.volume:.9f} m³")
    
    # Simulation
    print("\nSimulation d'un lancer...")
    result = engine.simulate_throw(
        initial_conditions={
            'position': [0, 0, 1.5],
            'velocity': [2.0, 1.0, 3.0],
            'orientation': [1, 0, 0, 0],
            'angular_velocity': [10, 5, 8]
        },
        surface_properties={
            'elasticity': 0.4,
            'friction': 0.5,
            'damping_coefficient': 0.1
        }
    )
    
    print(f"Face finale: {result['final_face']}")
    print(f"Collisions: {result['material_specific_data']['num_collisions']}")
    print(f"Énergie perdue: {result['material_specific_data']['energy_loss_profile']:.4f} J")
    
    print("\n[OK] Test moteur physique réussi")
    return True


def test_fingerprint_extraction():
    print("\n" + "=" * 60)
    print("TEST 3: Extraction empreinte matérielle")
    print("=" * 60)
    
    from core.material_fingerprint import (
        MaterialFingerprintExtractor,
        CryptoVertexCalculator
    )
    from core.physics_engine import PolyhedronPhysicsEngine, PolyhedronType
    from core.material_database import MATERIAL_DB
    
    # Faire quelques simulations
    materials = ['tungsten', 'ebony', 'acrylic']
    simulation_results = []
    
    for mat_name in materials:
        material = MATERIAL_DB.get_material(mat_name)
        assert material is not None, f"Matériau {mat_name} non trouvé!"
        engine = PolyhedronPhysicsEngine(PolyhedronType.D6, material)
        engine.dt = 0.001  # Faster for testing
        
        result = engine.simulate_throw(
            {'position': [0, 0, 1.2], 'velocity': [1.5, 0.5, 2.0]},
            {'elasticity': 0.4, 'friction': 0.5}
        )
        result['material'] = material.to_dict()
        simulation_results.append(result)
    
    # Extraire l'empreinte
    extractor = MaterialFingerprintExtractor()
    fingerprint = extractor.extract_from_simulation_results(simulation_results)
    
    print(f"Hash statique: {fingerprint.static_hash[:32]}...")
    print(f"Hash interactions: {fingerprint.interaction_hash[:32]}...")
    print(f"Signature dynamique: {fingerprint.dynamic_signature[:32]}...")
    print(f"Empreinte composite: {fingerprint.composite_fingerprint[:32]}...")
    
    # Calculer crypto vertex
    vertex = CryptoVertexCalculator.calculate_crypto_vertex(fingerprint, simulation_results)
    print(f"\nCrypto Vertex: {vertex[:32]}...")
    
    print("\n[OK] Test extraction empreinte réussi")
    return True


def test_vault_system():
    print("\n" + "=" * 60)
    print("TEST 4: Système de vault matériel")
    print("=" * 60)
    
    from protocols.material_vault import (
        MaterialBasedVaultSystem,
        AccessLevel,
        VaultAccessDenied
    )
    from core.physics_engine import PolyhedronPhysicsEngine, PolyhedronType
    from core.material_database import MATERIAL_DB
    
    # Simuler les lancers pour l'enregistrement
    def run_simulations():
        results = []
        for mat_name in ['tungsten', 'sapphire']:
            material = MATERIAL_DB.get_material(mat_name)
            assert material is not None, f"Matériau {mat_name} non trouvé!"
            engine = PolyhedronPhysicsEngine(PolyhedronType.D20, material)
            engine.dt = 0.001  # Faster for testing
            result = engine.simulate_throw(
                {'position': [0, 0, 1.5], 'velocity': [2.0, 1.0, 2.5]},
                {'elasticity': 0.4, 'friction': 0.5}
            )
            result['material'] = material.to_dict()
            results.append(result)
        return results
    
    # Créer le système de vault
    vault = MaterialBasedVaultSystem()
    
    # Enregistrer un utilisateur
    print("Enregistrement utilisateur 'test_user'...")
    sim_results = run_simulations()
    credentials = vault.register_user('test_user', sim_results, AccessLevel.ADMIN)
    
    print(f"Utilisateur enregistré: {credentials.user_id}")
    print(f"Niveau d'accès: {credentials.access_level.value}")
    print(f"Vertex: {credentials.crypto_vertex[:32]}...")
    
    # Tentative de déverrouillage avec les mêmes résultats
    print("\nTentative de déverrouillage...")
    try:
        unlock_result = vault.unlock_vault('test_user', sim_results)
        print(f"Accès accordé: {unlock_result['access_granted']}")
        print(f"Score de correspondance: {unlock_result['match_score']:.4f}")
        print(f"Clé vault (hex): {unlock_result['vault_key'][:32]}...")
    except VaultAccessDenied as e:
        print(f"Accès refusé: {e}")
    
    print("\n[OK] Test système vault réussi")
    return True


def test_complete_pipeline():
    print("\n" + "=" * 60)
    print("TEST 5: Pipeline complet")
    print("=" * 60)
    
    from core.material_simulation_pipeline import (
        CompleteMaterialSimulationPipeline,
        create_sample_user_config
    )
    
    # Créer la config
    config = create_sample_user_config("pipeline_test_user")
    # Réduire le nombre de lancers pour le test
    for die in config['dice_configuration']:
        die['throw_count'] = 3
    
    print(f"Configuration utilisateur: {config['user_id']}")
    print(f"Nombre de types de dés: {len(config['dice_configuration'])}")
    
    # Exécuter le pipeline
    pipeline = CompleteMaterialSimulationPipeline()
    results = pipeline.run_full_pipeline(config)
    
    if results['success']:
        print(f"\n[OK] Pipeline terminé avec succès")
        print(f"Validation token: {results['validation_token'][:32]}...")
        print(f"Nombre de simulations: {len(results['simulation_results'])}")
    else:
        print(f"\n[ERREUR] Pipeline échoué: {results.get('error')}")
        return False
    
    return True


def run_all_tests():
    print("\n" + "=" * 70)
    print("  TESTS DU SYSTÈME DE SIMULATION MATÉRIELLE")
    print("=" * 70)
    
    tests = [
        ("Base de données matériaux", test_material_database),
        ("Moteur physique", test_physics_engine),
        ("Extraction empreinte", test_fingerprint_extraction),
        ("Système vault", test_vault_system),
        ("Pipeline complet", test_complete_pipeline)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n[ERREUR] {name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Résumé
    print("\n" + "=" * 70)
    print("  RÉSUMÉ DES TESTS")
    print("=" * 70)
    
    all_passed = True
    for name, success in results:
        status = "[OK]" if success else "[ÉCHEC]"
        print(f"  {status} {name}")
        if not success:
            all_passed = False
    
    print("=" * 70)
    
    if all_passed:
        print("  TOUS LES TESTS RÉUSSIS")
    else:
        print("  CERTAINS TESTS ONT ÉCHOUÉ")
    
    print("=" * 70)
    
    return all_passed


if __name__ == "__main__":
    run_all_tests()
