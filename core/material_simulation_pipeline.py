"""
Pipeline Complet de Simulation Matérielle
De la configuration utilisateur au fichier .blend avec signatures cryptographiques

VULN-CRYPTO-03 FIX: Utilisation de HKDF pour dériver des seeds déterministes
à partir d'une master seed cryptographiquement sécurisée.
"""

import hashlib
import json
import numpy as np
import secrets
import time
import os
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .material_database import (
    PolyhedronMaterialDatabase, MaterialProperties, 
    SurfaceMaterialDatabase, MATERIAL_DB
)
from .physics_engine import (
    PolyhedronPhysicsEngine, PolyhedronType, PhysicsState, Trajectory
)
from .material_fingerprint import (
    MaterialFingerprint, MaterialFingerprintExtractor, CryptoVertexCalculator
)


class SecureRandomGenerator:
    """
    Générateur de nombres aléatoires sécurisé et déterministe.
    
    Utilise HKDF pour dériver des seeds à partir d'une master seed,
    garantissant la reproductibilité tout en maintenant la sécurité cryptographique.
    """
    
    def __init__(self, master_seed: Optional[bytes] = None):
        """
        Initialise le générateur.
        
        Args:
            master_seed: Seed maître (32 bytes). Si None, génère une seed sécurisée.
        """
        if master_seed is None:
            self.master_seed = secrets.token_bytes(32)
        else:
            self.master_seed = master_seed
        
        self._counter = 0
        self._rng: Optional[np.random.Generator] = None
        self._initialize_rng()
    
    def _initialize_rng(self):
        """Initialise le générateur numpy avec une seed dérivée via HKDF"""
        derived_seed = self._derive_seed(b"numpy_rng_init")
        # Convertir les 32 bytes en un entier pour numpy
        seed_int = int.from_bytes(derived_seed[:8], 'big')
        self._rng = np.random.default_rng(seed_int)
    
    def _derive_seed(self, context: bytes) -> bytes:
        """
        Dérive une seed déterministe pour un contexte donné.
        
        Args:
            context: Information de contexte (ex: b"throw_1", b"quaternion")
        
        Returns:
            32 bytes de seed déterministe
        """
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._counter.to_bytes(8, 'big'),
            info=context
        )
        self._counter += 1
        return hkdf.derive(self.master_seed)
    
    def get_rng_for_context(self, context: str) -> np.random.Generator:
        """
        Retourne un générateur numpy seedé pour un contexte spécifique.
        
        Args:
            context: Description du contexte (ex: "throw_5_height")
        
        Returns:
            np.random.Generator déterministe pour ce contexte
        """
        derived = self._derive_seed(context.encode())
        seed_int = int.from_bytes(derived[:8], 'big')
        return np.random.default_rng(seed_int)
    
    def normal(self, mean: float = 0.0, std: float = 1.0, 
               context: Optional[str] = None) -> float:
        """Distribution normale sécurisée"""
        if context:
            rng = self.get_rng_for_context(context)
            return float(rng.normal(mean, std))
        return float(self._rng.normal(mean, std))
    
    def uniform(self, low: float = 0.0, high: float = 1.0,
                context: Optional[str] = None) -> float:
        """Distribution uniforme sécurisée"""
        if context:
            rng = self.get_rng_for_context(context)
            return float(rng.uniform(low, high))
        return float(self._rng.uniform(low, high))
    
    def random(self, size: Optional[int] = None,
               context: Optional[str] = None) -> np.ndarray:
        """Nombres aléatoires [0, 1) sécurisés"""
        if context:
            rng = self.get_rng_for_context(context)
            return rng.random(size)
        return self._rng.random(size)
    
    def randn(self, *shape, context: Optional[str] = None) -> np.ndarray:
        """Distribution normale standard sécurisée"""
        if context:
            rng = self.get_rng_for_context(context)
            return rng.standard_normal(shape)
        return self._rng.standard_normal(shape)
    
    def get_master_seed_hex(self) -> str:
        """Retourne la master seed en hexadécimal (pour debug/audit)"""
        return self.master_seed.hex()
    
    @classmethod
    def from_user_secret(cls, user_secret: bytes, salt: bytes = b"") -> 'SecureRandomGenerator':
        """
        Crée un générateur à partir d'un secret utilisateur.
        
        Args:
            user_secret: Secret fourni par l'utilisateur
            salt: Sel optionnel pour diversification
        
        Returns:
            SecureRandomGenerator avec seed dérivée du secret
        """
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            info=b"secure_random_master_seed"
        )
        master_seed = hkdf.derive(user_secret)
        return cls(master_seed)


class ValidationError(Exception):
    """Erreur de validation"""
    pass


@dataclass
class ThrowParameters:
    """Paramètres d'un lancer"""
    position: np.ndarray
    velocity: np.ndarray
    angular_velocity: np.ndarray
    orientation: np.ndarray
    material_parameters: Dict
    throw_id: str


class MaterialBasedInitialConditions:
    """
    Génère des conditions initiales basées sur les propriétés matérielles.
    
    VULN-CRYPTO-03 FIX: Utilise SecureRandomGenerator au lieu de np.random
    pour garantir des seeds cryptographiquement sécurisées et déterministes.
    """
    
    def __init__(self, material_db: Optional[PolyhedronMaterialDatabase] = None,
                 master_seed: Optional[bytes] = None):
        """
        Args:
            material_db: Base de données des matériaux
            master_seed: Seed maître pour reproductibilité (32 bytes)
        """
        self.material_db = material_db or MATERIAL_DB
        self.secure_rng = SecureRandomGenerator(master_seed)
    
    def generate_throw_parameters(self, material: MaterialProperties,
                                  poly_type: PolyhedronType,
                                  throw_number: int) -> ThrowParameters:
        """Génère des paramètres de lancer uniques basés sur le matériau"""
        
        # Contexte unique pour ce lancer (garantit reproductibilité)
        ctx_base = f"{material.name}_{poly_type.name}_{throw_number}"
        
        # 1. Hauteur de lancer (fonction de la densité)
        base_height = 1.5  # mètres
        density_factor = material.density / 10000
        height_noise = self.secure_rng.normal(0, 0.1, context=f"{ctx_base}_height")
        height = base_height * (1.0 - 0.3 * density_factor) + height_noise
        height = max(0.5, min(3.0, height))
        
        # 2. Vitesse initiale (fonction de l'élasticité)
        base_velocity = 3.0  # m/s
        velocity_mag = base_velocity * (1.2 - 0.4 * material.elasticity)
        velocity_noise = self.secure_rng.normal(0, 0.2, context=f"{ctx_base}_velocity")
        velocity_mag += velocity_noise
        velocity_mag = max(1.0, min(5.0, velocity_mag))
        
        # 3. Rotation initiale (fonction de la rugosité)
        spin_magnitude = 20.0 * (1.0 + material.roughness)  # rad/s
        
        # 4. Axe de rotation pondéré
        spin_axis = self._weighted_random_spin_axis(material, poly_type, ctx_base)
        
        # 5. Angle de lancement (fonction du frottement)
        launch_angle = 45 * (1.0 - 0.3 * material.friction)
        angle_noise = self.secure_rng.normal(0, 5, context=f"{ctx_base}_angle")
        launch_angle += angle_noise
        launch_angle = max(20, min(70, launch_angle))
        
        # 6. Convertir en vecteur vitesse
        angle_rad = np.radians(launch_angle)
        direction_angle = self.secure_rng.uniform(0, 2 * np.pi, context=f"{ctx_base}_direction")
        
        velocity = np.array([
            velocity_mag * np.cos(angle_rad) * np.cos(direction_angle),
            velocity_mag * np.cos(angle_rad) * np.sin(direction_angle),
            velocity_mag * np.sin(angle_rad)
        ])
        
        # 7. Effets matériels spécifiques
        material_params = self._material_specific_effects(material, poly_type, ctx_base)
        
        # 8. Orientation initiale aléatoire
        orientation = self._random_quaternion(ctx_base)
        
        throw_id = f"{material.name}_{poly_type.name}_{throw_number}_{int(time.time()*1000)}"
        
        return ThrowParameters(
            position=np.array([0, 0, height]),
            velocity=velocity,
            angular_velocity=spin_axis * spin_magnitude,
            orientation=orientation,
            material_parameters=material_params,
            throw_id=throw_id
        )
    
    def _weighted_random_spin_axis(self, material: MaterialProperties,
                                   poly_type: PolyhedronType,
                                   ctx_base: str) -> np.ndarray:
        """Génère un axe de rotation pondéré avec RNG sécurisé"""
        # Base aléatoire sécurisée
        axis = self.secure_rng.randn(3, context=f"{ctx_base}_spin_axis")
        
        # Biais pour matériaux anisotropes
        if material.anisotropic:
            grain_dir = material.anisotropic.grain_direction
            bias_strength = 0.7
            axis = axis * (1 - bias_strength) + grain_dir * bias_strength
        
        # Biais de densité (effet gyroscopique)
        density_bias = material.density / 20000
        axis[2] *= (1 + density_bias)
        
        return axis / (np.linalg.norm(axis) + 1e-10)
    
    def _material_specific_effects(self, material: MaterialProperties,
                                   poly_type: PolyhedronType,
                                   ctx_base: str) -> Dict:
        """Ajoute des effets spécifiques au matériau avec RNG sécurisé"""
        effects = {
            'base_material': material.name,
            'poly_type': poly_type.name
        }
        
        # Effets thermiques
        if material.thermal and material.thermal.conductivity > 100:
            effects['thermal_gradient'] = self.secure_rng.uniform(
                0.5, 2.0, context=f"{ctx_base}_thermal"
            )
        
        # Effets viscoélastiques
        if material.viscoelasticity > 0:
            effects['relaxation_time'] = 0.01 / (material.viscoelasticity + 0.01)
            effects['creep_factor'] = self.secure_rng.uniform(
                0.95, 1.05, context=f"{ctx_base}_creep"
            )
        
        # Effets acoustiques
        if material.acoustic:
            scale = 0.01  # Taille typique du dé
            effects['resonant_frequency'] = material.acoustic.speed_of_sound / (2 * scale)
        
        return effects
    
    def _random_quaternion(self, ctx_base: str) -> np.ndarray:
        """Génère un quaternion aléatoire uniformément distribué avec RNG sécurisé"""
        u_values = self.secure_rng.random(3, context=f"{ctx_base}_quaternion")
        u1, u2, u3 = u_values
        
        q = np.array([
            np.sqrt(1 - u1) * np.sin(2 * np.pi * u2),
            np.sqrt(1 - u1) * np.cos(2 * np.pi * u2),
            np.sqrt(u1) * np.sin(2 * np.pi * u3),
            np.sqrt(u1) * np.cos(2 * np.pi * u3)
        ])
        
        return q / np.linalg.norm(q)
    
    def get_master_seed(self) -> str:
        """Retourne la master seed pour audit/reproductibilité"""
        return self.secure_rng.get_master_seed_hex()


class CompleteMaterialSimulationPipeline:
    """Pipeline complet de simulation matérielle à fichier .blend"""
    
    def __init__(self):
        self.material_db = PolyhedronMaterialDatabase()
        self.surface_db = SurfaceMaterialDatabase()
        self.initial_conditions_gen = MaterialBasedInitialConditions(self.material_db)
        self.fingerprint_extractor = MaterialFingerprintExtractor(self.material_db)
    
    def run_full_pipeline(self, user_config: Dict) -> Dict:
        """Exécute le pipeline complet"""
        
        results = {
            'user_id': user_config.get('user_id', 'anonymous'),
            'start_time': datetime.now().isoformat(),
            'stages': {}
        }
        
        try:
            # ÉTAPE 1: Configuration
            print("Étape 1: Lecture de la configuration...")
            dice_configs = self._parse_user_configuration(user_config)
            results['stages']['config'] = {'status': 'success', 'num_dice': len(dice_configs)}
            
            # ÉTAPE 2: Simulation physique
            print("Étape 2: Simulation physique...")
            simulation_results = []
            
            for i, die_config in enumerate(dice_configs):
                print(f"  Simulation {i+1}/{len(dice_configs)}: "
                      f"{die_config['type'].name} en {die_config['material'].name}")
                
                sim_result = self._run_single_simulation(
                    die_config, 
                    user_config.get('surface', {})
                )
                simulation_results.append(sim_result)
            
            results['stages']['simulation'] = {
                'status': 'success',
                'num_simulations': len(simulation_results)
            }
            
            # ÉTAPE 3: Extraction d'empreinte
            print("Étape 3: Extraction de l'empreinte matérielle...")
            material_fingerprint = self.fingerprint_extractor.extract_from_simulation_results(
                simulation_results
            )
            results['stages']['fingerprint'] = {
                'status': 'success',
                'composite': material_fingerprint.composite_fingerprint[:32] + '...'
            }
            
            # ÉTAPE 4: Calcul du crypto vertex
            print("Étape 4: Calcul du vertex cryptographique...")
            crypto_vertex = CryptoVertexCalculator.calculate_crypto_vertex(
                material_fingerprint, simulation_results
            )
            results['stages']['crypto_vertex'] = {
                'status': 'success',
                'vertex': crypto_vertex[:32] + '...'
            }
            
            # ÉTAPE 5: Hash de simulation
            print("Étape 5: Génération du hash de simulation...")
            simulation_hash = self._compute_simulation_hash(simulation_results)
            
            # ÉTAPE 6: Validation
            print("Étape 6: Validation de l'intégrité...")
            validation_result = self._validate_results(
                simulation_results, material_fingerprint, crypto_vertex
            )
            
            if not validation_result['valid']:
                raise ValidationError(f"Validation échouée: {validation_result['reason']}")
            
            results['stages']['validation'] = validation_result
            
            # Résultats finaux
            results['success'] = True
            results['material_fingerprint'] = material_fingerprint.to_dict()
            results['crypto_vertex'] = crypto_vertex
            results['simulation_hash'] = simulation_hash
            results['validation_token'] = validation_result['token']
            results['simulation_results'] = [
                {
                    'die_type': sr.get('die_type', 'unknown'),
                    'material': sr.get('material', {}).get('name', 'unknown'),
                    'final_face': sr.get('final_face', 0),
                    'num_collisions': sr.get('material_specific_data', {}).get('num_collisions', 0)
                }
                for sr in simulation_results
            ]
            results['end_time'] = datetime.now().isoformat()
            
            print("\n" + "=" * 60)
            print("PIPELINE TERMINÉ AVEC SUCCÈS")
            print("=" * 60)
            print(f"Utilisateur: {results['user_id']}")
            print(f"Empreinte: {material_fingerprint.composite_fingerprint[:32]}...")
            print(f"Vertex: {crypto_vertex[:32]}...")
            print(f"Faces finales: {[sr['final_face'] for sr in results['simulation_results']]}")
            
        except Exception as e:
            results['success'] = False
            results['error'] = str(e)
            print(f"ERREUR: {e}")
        
        return results
    
    def _parse_user_configuration(self, user_config: Dict) -> List[Dict]:
        """Parse la configuration utilisateur"""
        dice_configs = []
        
        for die_conf in user_config.get('dice_configuration', []):
            # Type de polyèdre
            type_str = die_conf.get('type', 'd6').upper()
            poly_type = getattr(PolyhedronType, type_str, PolyhedronType.D6)
            
            # Matériau
            material_conf = die_conf.get('material', {})
            material_name = material_conf.get('name', 'acrylic')
            material = self.material_db.get_material(material_name)
            
            if not material:
                # Créer un matériau par défaut
                material = MaterialProperties(
                    name=material_name,
                    material_type=MaterialProperties.MaterialType.PLASTIC if hasattr(MaterialProperties, 'MaterialType') else 'plastic',
                    density=material_conf.get('density', 1200),
                    elasticity=material_conf.get('elasticity', 0.6),
                    friction=material_conf.get('friction', 0.35),
                    roughness=material_conf.get('roughness', 0.05),
                    custom_properties=material_conf.get('custom_properties', {})
                )
            
            throw_count = die_conf.get('throw_count', 30)
            
            for i in range(throw_count):
                dice_configs.append({
                    'type': poly_type,
                    'material': material,
                    'throw_number': i,
                    'throw_style': die_conf.get('throw_style', 'standard')
                })
        
        return dice_configs
    
    def _run_single_simulation(self, die_config: Dict, 
                               surface_config: Dict) -> Dict:
        """Exécute une simulation unique"""
        
        # Paramètres initiaux
        initial_params = self.initial_conditions_gen.generate_throw_parameters(
            die_config['material'],
            die_config['type'],
            die_config['throw_number']
        )
        
        # Surface
        surface_type = surface_config.get('type', 'oak_wood')
        surface_props = self.surface_db.get_surface(surface_type) or {
            'hardness': 4.0,
            'friction': 0.5,
            'elasticity': 0.4,
            'damping_coefficient': 0.1
        }
        
        # Moteur physique
        engine = PolyhedronPhysicsEngine(
            die_config['type'],
            die_config['material']
        )
        
        # Simulation
        sim_result = engine.simulate_throw(
            {
                'position': initial_params.position.tolist(),
                'velocity': initial_params.velocity.tolist(),
                'orientation': initial_params.orientation.tolist(),
                'angular_velocity': initial_params.angular_velocity.tolist()
            },
            surface_props
        )
        
        # Enrichir les résultats
        sim_result['die_type'] = die_config['type'].name
        sim_result['material'] = die_config['material'].to_dict()
        sim_result['throw_id'] = initial_params.throw_id
        sim_result['initial_conditions'] = {
            'position': initial_params.position.tolist(),
            'velocity': initial_params.velocity.tolist()
        }
        
        return sim_result
    
    def _compute_simulation_hash(self, simulation_results: List[Dict]) -> str:
        """Calcule un hash global des simulations"""
        data = []
        
        for sim in simulation_results:
            data.append(sim.get('throw_id', ''))
            data.append(str(sim.get('final_face', 0)))
            data.append(sim.get('simulation_hash', ''))
        
        combined = '|'.join(data)
        return hashlib.sha3_512(combined.encode()).hexdigest()
    
    def _validate_results(self, simulation_results: List[Dict],
                         fingerprint: MaterialFingerprint,
                         crypto_vertex: str) -> Dict:
        """Valide les résultats de la simulation"""
        
        # Vérifications de base
        if len(simulation_results) == 0:
            return {'valid': False, 'reason': 'Aucune simulation'}
        
        if not fingerprint.composite_fingerprint:
            return {'valid': False, 'reason': 'Empreinte vide'}
        
        if not crypto_vertex:
            return {'valid': False, 'reason': 'Vertex vide'}
        
        # Vérifier que toutes les simulations ont des faces valides
        for sim in simulation_results:
            face = sim.get('final_face', 0)
            if face < 1:
                return {'valid': False, 'reason': f'Face invalide: {face}'}
        
        # Générer un token de validation
        validation_data = (
            fingerprint.composite_fingerprint + 
            crypto_vertex + 
            str(len(simulation_results))
        )
        validation_token = hashlib.sha256(validation_data.encode()).hexdigest()
        
        return {
            'valid': True,
            'token': validation_token,
            'num_simulations': len(simulation_results),
            'fingerprint_valid': True,
            'vertex_valid': True
        }


def create_sample_user_config(user_id: str = "sample_user") -> Dict:
    """Crée une configuration utilisateur exemple"""
    return {
        "user_id": user_id,
        "dice_configuration": [
            {
                "type": "d20",
                "material": {
                    "name": "tungsten",
                    "custom_properties": {
                        "surface_treatment": "polished"
                    }
                },
                "throw_count": 10,
                "throw_style": "controlled_spin"
            },
            {
                "type": "d12",
                "material": {
                    "name": "ebony"
                },
                "throw_count": 10,
                "throw_style": "high_toss"
            },
            {
                "type": "d6",
                "material": {
                    "name": "acrylic"
                },
                "throw_count": 10,
                "throw_style": "standard"
            }
        ],
        "surface": {
            "type": "oak_wood",
            "temperature": 22.0
        },
        "simulation_parameters": {
            "precision": "high"
        }
    }
