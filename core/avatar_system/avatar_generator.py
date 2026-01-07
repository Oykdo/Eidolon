#!/usr/bin/env python3
"""
Generateur d'avatars 3D uniques bases sur les donnees cryptographiques du vault
Chaque avatar est un NFT unique lie perpetuellement au vault
"""

import hashlib
import json
import struct
import math
import secrets
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ============================================================================
# CONSTANTES
# ============================================================================

AVATAR_VERSION = 1

# Limite des vaults pionniers pouvant obtenir un avatar
PIONEER_AVATAR_LIMIT = 10000  # Seuls les 10,000 premiers vaults peuvent avoir un avatar

# Tiers de pionniers avec bonus RNG
PIONEER_TIERS = {
    "supreme": (1, 33),        # Supreme Architects - RNG maximal
    "legendary": (34, 100),    # Legendary Pioneers - Tres haut RNG
    "elite": (101, 1000),      # Elite Pioneers - Haut RNG
    "pioneer": (1001, 10000),  # Standard Pioneers - RNG normal ameliore
}

# Bonus de rarete par tier de pionnier
PIONEER_RARITY_BONUS = {
    "supreme": 50.0,     # +50 points de rarete (garantit mythical/primordial)
    "legendary": 35.0,   # +35 points (garantit legendary+)
    "elite": 20.0,       # +20 points (garantit epic+)
    "pioneer": 10.0,     # +10 points (ameliore les chances)
}

# Multiplicateurs d'attributs par tier
PIONEER_ATTRIBUTE_MULTIPLIER = {
    "supreme": 2.0,      # x2 sur tous les attributs
    "legendary": 1.75,   # x1.75
    "elite": 1.5,        # x1.5
    "pioneer": 1.25,     # x1.25
}

GEOMETRIC_TYPES = [
    "quantum_sphere",
    "spinor_torus", 
    "bell_polyhedron",
    "clifford_lattice",
    "entropy_fractal",
    "7d_projection",
    "hybrid_form",
    "nexus_crystal"
]

# Types geometriques exclusifs par tier
EXCLUSIVE_GEOMETRIC_TYPES = {
    "supreme": ["nexus_crystal", "7d_projection", "hybrid_form"],  # Types les plus rares
    "legendary": ["nexus_crystal", "7d_projection", "hybrid_form", "entropy_fractal"],
    "elite": GEOMETRIC_TYPES,  # Tous les types
    "pioneer": GEOMETRIC_TYPES,
}

RARITY_TIERS = {
    "common": (0, 20),
    "uncommon": (20, 40),
    "rare": (40, 60),
    "epic": (60, 75),
    "legendary": (75, 90),
    "mythical": (90, 97),
    "primordial": (97, 100)
}

# Rarete minimum garantie par tier
PIONEER_MIN_RARITY = {
    "supreme": "mythical",    # Au minimum mythical
    "legendary": "legendary", # Au minimum legendary
    "elite": "epic",          # Au minimum epic
    "pioneer": "rare",        # Au minimum rare
}


# ============================================================================
# STRUCTURES DE DONNEES
# ============================================================================

@dataclass
class AvatarDNA:
    """ADN cryptographique de l'avatar"""
    vault_hash: str
    seed_values: List[int]
    geometric_type: int
    geometric_name: str
    color_palette: List[str]
    attributes: Dict[str, float]
    rarity_score: float
    rarity_tier: str
    generation: int
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'AvatarDNA':
        return cls(**data)


@dataclass
class Avatar3D:
    """Representation complete d'un avatar 3D"""
    avatar_id: str
    vault_id: str
    dna: AvatarDNA
    
    # Geometrie
    vertices: List[List[float]] = field(default_factory=list)
    faces: List[List[int]] = field(default_factory=list)
    normals: List[List[float]] = field(default_factory=list)
    uvs: List[List[float]] = field(default_factory=list)
    
    # Fichiers
    obj_path: Optional[str] = None
    texture_path: Optional[str] = None
    preview_path: Optional[str] = None
    
    # Metadata
    created_at: str = ""
    version: int = AVATAR_VERSION
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['dna'] = self.dna.to_dict()
        return d


# ============================================================================
# GENERATEUR D'AVATARS
# ============================================================================

class QuantumAvatarGenerator:
    """Generateur d'avatars 3D base sur l'entropie quantique du vault"""
    
    def __init__(self, vault_data: bytes = None, vault_id: str = None, 
                 vault_path: str = None, generation: int = 1,
                 vault_number: int = None):
        """
        Initialise le generateur d'avatar.
        
        Args:
            vault_data: Donnees brutes du vault (bytes)
            vault_id: ID du vault
            vault_path: Chemin vers le fichier .blend_data
            generation: Generation de l'avatar
            vault_number: Numero du vault (1-10000 pour les pionniers)
        """
        self.generation = generation
        self.vault_id = vault_id or secrets.token_hex(8)
        self.vault_number = vault_number
        
        # Determiner le tier du pionnier
        self.pioneer_tier = self._get_pioneer_tier(vault_number)
        
        # Charger les donnees
        if vault_data:
            self.raw_data = vault_data
        elif vault_path:
            with open(vault_path, 'rb') as f:
                self.raw_data = f.read()
        else:
            # Generer des donnees aleatoires pour demo
            self.raw_data = secrets.token_bytes(1024)
        
        # Extraire l'ADN
        self.dna = self._extract_dna()
        self.avatar: Optional[Avatar3D] = None
    
    @staticmethod
    def can_have_avatar(vault_number: int) -> Tuple[bool, str]:
        """
        Verifie si un vault peut avoir un avatar.
        Seuls les 10,000 premiers vaults peuvent en avoir un.
        
        Returns:
            (can_have, reason)
        """
        if vault_number is None:
            return False, "Numero de vault requis"
        
        if vault_number < 1:
            return False, "Numero de vault invalide"
        
        if vault_number > PIONEER_AVATAR_LIMIT:
            return False, f"Seuls les {PIONEER_AVATAR_LIMIT:,} premiers vaults peuvent avoir un avatar"
        
        return True, "OK"
    
    def _get_pioneer_tier(self, vault_number: int) -> Optional[str]:
        """Determine le tier du pionnier selon son numero de vault"""
        if vault_number is None:
            return None
        
        for tier, (min_num, max_num) in PIONEER_TIERS.items():
            if min_num <= vault_number <= max_num:
                return tier
        
        return None
    
    def _extract_dna(self) -> AvatarDNA:
        """Extrait l'ADN cryptographique des donnees du vault avec bonus pionnier"""
        # Hash principal
        vault_hash = hashlib.sha256(self.raw_data).hexdigest()
        
        # Generer des valeurs de seed
        seed_bytes = bytes.fromhex(vault_hash[:32])
        seed_values = [int(b) for b in seed_bytes[:16]]
        
        # Type geometrique (avec restriction pour certains tiers)
        geometric_name = self._select_geometric_type(seed_values)
        geometric_type = GEOMETRIC_TYPES.index(geometric_name)
        
        # Palette de couleurs (amelioree pour pionniers)
        color_palette = self._generate_color_palette(vault_hash)
        
        # Attributs (avec multiplicateur pionnier)
        attributes = self._calculate_attributes(seed_values)
        
        # Rarete (avec bonus pionnier)
        rarity_score = self._calculate_rarity(seed_values, vault_hash)
        rarity_tier = self._get_rarity_tier(rarity_score)
        
        return AvatarDNA(
            vault_hash=vault_hash,
            seed_values=seed_values,
            geometric_type=geometric_type,
            geometric_name=geometric_name,
            color_palette=color_palette,
            attributes=attributes,
            rarity_score=rarity_score,
            rarity_tier=rarity_tier,
            generation=self.generation
        )
    
    def _select_geometric_type(self, seed_values: List[int]) -> str:
        """Selectionne le type geometrique selon le tier"""
        if self.pioneer_tier and self.pioneer_tier in EXCLUSIVE_GEOMETRIC_TYPES:
            available_types = EXCLUSIVE_GEOMETRIC_TYPES[self.pioneer_tier]
        else:
            available_types = GEOMETRIC_TYPES
        
        # Selection basee sur le seed
        type_index = sum(seed_values[:4]) % len(available_types)
        return available_types[type_index]
    
    def _generate_color_palette(self, vault_hash: str) -> List[str]:
        """Genere une palette de couleurs unique"""
        colors = []
        
        # 3 couleurs primaires du hash
        for i in range(0, 18, 6):
            hex_color = vault_hash[i:i+6]
            colors.append(f'#{hex_color}')
        
        # Couleur complementaire
        base_r = int(vault_hash[0:2], 16)
        base_g = int(vault_hash[2:4], 16)
        base_b = int(vault_hash[4:6], 16)
        
        comp_r = 255 - base_r
        comp_g = 255 - base_g
        comp_b = 255 - base_b
        colors.append(f'#{comp_r:02x}{comp_g:02x}{comp_b:02x}')
        
        # Couleur accentuee
        accent_r = (base_r + 128) % 256
        accent_g = (base_g + 64) % 256
        accent_b = (base_b + 192) % 256
        colors.append(f'#{accent_r:02x}{accent_g:02x}{accent_b:02x}')
        
        return colors[:5]
    
    def _calculate_attributes(self, seed_values: List[int]) -> Dict[str, float]:
        """Calcule les attributs de l'avatar avec multiplicateur pionnier"""
        # Multiplicateur selon le tier
        multiplier = 1.0
        if self.pioneer_tier and self.pioneer_tier in PIONEER_ATTRIBUTE_MULTIPLIER:
            multiplier = PIONEER_ATTRIBUTE_MULTIPLIER[self.pioneer_tier]
        
        # Attributs de base
        base_attrs = {
            'quantum_entropy': (sum(seed_values[:4]) / 1024) * 100,
            'spinor_complexity': (seed_values[4] / 255) * 100,
            'bell_verification': (seed_values[5] / 255) * 100,
            'polyhedral_symmetry': (seed_values[6] / 255) * 100,
            'cryptographic_strength': (seed_values[7] / 255) * 100,
            'temporal_stability': (seed_values[8] / 255) * 100,
            'spatial_coherence': (seed_values[9] / 255) * 100,
            'dimensional_depth': (seed_values[10] / 255) * 7,
            'fractal_dimension': 1.0 + (seed_values[11] / 255) * 2,
            'energy_resonance': (seed_values[12] / 255) * 100
        }
        
        # Appliquer le multiplicateur (cap a 100 sauf pour certains attributs)
        result = {}
        for attr, value in base_attrs.items():
            boosted = value * multiplier
            if attr in ['dimensional_depth', 'fractal_dimension']:
                result[attr] = round(boosted, 3)
            else:
                result[attr] = round(min(100, boosted), 2)
        
        # Bonus special pour les Supreme (1-33)
        if self.pioneer_tier == "supreme":
            result['pioneer_blessing'] = 100.0  # Attribut exclusif
            result['dimensional_depth'] = 7.0   # Maximum
        
        return result
    
    def _calculate_rarity(self, seed_values: List[int], vault_hash: str) -> float:
        """Calcule le score de rarete (0-100) avec bonus pionnier"""
        # Base sur les valeurs extremes
        extreme_count = sum(1 for v in seed_values if v < 10 or v > 245)
        extreme_bonus = extreme_count * 5
        
        # Base sur les patterns rares dans le hash
        rare_patterns = ['00', 'ff', '777', '888', 'abc', 'def']
        pattern_bonus = sum(3 for p in rare_patterns if p in vault_hash.lower())
        
        # Base sur l'entropie
        entropy_score = (seed_values[13] / 255) * 30
        
        # Score final de base
        base_score = (seed_values[14] / 255) * 40
        total = base_score + extreme_bonus + pattern_bonus + entropy_score
        
        # Appliquer le bonus pionnier
        if self.pioneer_tier and self.pioneer_tier in PIONEER_RARITY_BONUS:
            pioneer_bonus = PIONEER_RARITY_BONUS[self.pioneer_tier]
            total += pioneer_bonus
        
        # S'assurer que le score respecte le minimum garanti du tier
        if self.pioneer_tier and self.pioneer_tier in PIONEER_MIN_RARITY:
            min_rarity = PIONEER_MIN_RARITY[self.pioneer_tier]
            min_score = RARITY_TIERS.get(min_rarity, (0, 0))[0]
            total = max(total, min_score + 1)  # +1 pour etre dans le tier
        
        return min(100, max(0, round(total, 2)))
    
    def _get_rarity_tier(self, score: float) -> str:
        """Determine le tier de rarete"""
        for tier, (min_val, max_val) in RARITY_TIERS.items():
            if min_val <= score < max_val:
                return tier
        return "primordial"
    
    def get_pioneer_info(self) -> Optional[Dict]:
        """Retourne les informations du tier pionnier"""
        if not self.pioneer_tier:
            return None
        
        return {
            'tier': self.pioneer_tier,
            'vault_number': self.vault_number,
            'rarity_bonus': PIONEER_RARITY_BONUS.get(self.pioneer_tier, 0),
            'attribute_multiplier': PIONEER_ATTRIBUTE_MULTIPLIER.get(self.pioneer_tier, 1.0),
            'min_rarity': PIONEER_MIN_RARITY.get(self.pioneer_tier, 'common'),
            'exclusive_types': EXCLUSIVE_GEOMETRIC_TYPES.get(self.pioneer_tier, [])
        }
    
    def generate_geometry(self) -> Dict:
        """Genere la geometrie 3D de l'avatar"""
        dna = self.dna
        
        # Choisir la methode selon le type
        generators = {
            0: self._create_quantum_sphere,
            1: self._create_spinor_torus,
            2: self._create_bell_polyhedron,
            3: self._create_clifford_lattice,
            4: self._create_entropy_fractal,
            5: self._create_7d_projection,
            6: self._create_hybrid_form,
            7: self._create_nexus_crystal
        }
        
        generator = generators.get(dna.geometric_type, self._create_quantum_sphere)
        vertices, faces = generator()
        
        # Appliquer les transformations
        vertices = self._apply_transformations(vertices)
        
        # Calculer les normales
        normals = self._calculate_normals(vertices, faces)
        
        # Generer les UVs
        uvs = self._generate_uvs(vertices)
        
        return {
            'vertices': vertices,
            'faces': faces,
            'normals': normals,
            'uvs': uvs,
            'type': dna.geometric_name,
            'colors': dna.color_palette
        }
    
    def _create_quantum_sphere(self) -> Tuple[List, List]:
        """Cree une sphere quantique avec perturbations"""
        vertices = []
        faces = []
        
        n_lat = 16
        n_lon = 24
        radius = 1.0
        
        # Perturbation basee sur l'ADN
        perturb = self.dna.seed_values[0] / 500
        
        for i in range(n_lat + 1):
            theta = math.pi * i / n_lat
            for j in range(n_lon):
                phi = 2 * math.pi * j / n_lon
                
                # Perturbation quantique
                noise = perturb * math.sin(theta * 5) * math.cos(phi * 3)
                r = radius + noise
                
                x = r * math.sin(theta) * math.cos(phi)
                y = r * math.sin(theta) * math.sin(phi)
                z = r * math.cos(theta)
                
                vertices.append([x, y, z])
        
        # Generer les faces
        for i in range(n_lat):
            for j in range(n_lon):
                v1 = i * n_lon + j
                v2 = i * n_lon + (j + 1) % n_lon
                v3 = (i + 1) * n_lon + j
                v4 = (i + 1) * n_lon + (j + 1) % n_lon
                
                faces.append([v1, v2, v3])
                faces.append([v2, v4, v3])
        
        return vertices, faces
    
    def _create_spinor_torus(self) -> Tuple[List, List]:
        """Cree un tore spinoriel"""
        vertices = []
        faces = []
        
        R = 1.0 + self.dna.seed_values[1] / 500
        r = 0.4 + self.dna.seed_values[2] / 1000
        
        n_u = 24
        n_v = 16
        
        twist = self.dna.seed_values[3] / 100
        
        for i in range(n_u):
            u = 2 * math.pi * i / n_u
            for j in range(n_v):
                v = 2 * math.pi * j / n_v
                
                x = (R + r * math.cos(v)) * math.cos(u)
                y = (R + r * math.cos(v)) * math.sin(u)
                z = r * math.sin(v)
                
                # Twist spinoriel
                x += twist * math.sin(5 * v)
                y += twist * math.cos(5 * v)
                
                vertices.append([x, y, z])
        
        # Generer les faces
        for i in range(n_u):
            for j in range(n_v):
                v1 = i * n_v + j
                v2 = i * n_v + (j + 1) % n_v
                v3 = ((i + 1) % n_u) * n_v + j
                v4 = ((i + 1) % n_u) * n_v + (j + 1) % n_v
                
                faces.append([v1, v2, v3])
                faces.append([v2, v4, v3])
        
        return vertices, faces
    
    def _create_bell_polyhedron(self) -> Tuple[List, List]:
        """Cree un polyedre de Bell (icosaedre modifie)"""
        # Golden ratio
        phi = (1 + math.sqrt(5)) / 2
        
        # Vertices de l'icosaedre
        base_vertices = [
            [-1, phi, 0], [1, phi, 0], [-1, -phi, 0], [1, -phi, 0],
            [0, -1, phi], [0, 1, phi], [0, -1, -phi], [0, 1, -phi],
            [phi, 0, -1], [phi, 0, 1], [-phi, 0, -1], [-phi, 0, 1]
        ]
        
        # Modifier selon l'ADN
        scale = 0.8 + self.dna.seed_values[4] / 500
        vertices = [[v[0] * scale, v[1] * scale, v[2] * scale] for v in base_vertices]
        
        # Faces de l'icosaedre
        faces = [
            [0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
            [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
            [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
            [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]
        ]
        
        return vertices, faces
    
    def _create_clifford_lattice(self) -> Tuple[List, List]:
        """Cree un reseau de Clifford"""
        vertices = []
        faces = []
        
        size = 3
        spacing = 0.5 + self.dna.seed_values[5] / 500
        
        # Creer les points du reseau
        for i in range(-size, size + 1):
            for j in range(-size, size + 1):
                for k in range(-size, size + 1):
                    if (i + j + k) % 2 == 0:  # Pattern alterné
                        x = i * spacing
                        y = j * spacing
                        z = k * spacing
                        
                        # Deformation basee sur l'ADN
                        distort = self.dna.seed_values[6] / 1000
                        x += distort * math.sin(y * 2)
                        y += distort * math.cos(z * 2)
                        z += distort * math.sin(x * 2)
                        
                        vertices.append([x, y, z])
        
        # Connecter les points proches
        for i in range(len(vertices)):
            for j in range(i + 1, min(i + 10, len(vertices))):
                dist = sum((vertices[i][k] - vertices[j][k])**2 for k in range(3))**0.5
                if dist < spacing * 1.5:
                    # Creer un triangle avec le point suivant
                    if j + 1 < len(vertices):
                        faces.append([i, j, (j + 1) % len(vertices)])
        
        return vertices, faces
    
    def _create_entropy_fractal(self) -> Tuple[List, List]:
        """Cree un fractal base sur l'entropie"""
        # Tetraedre de base
        vertices = [
            [1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]
        ]
        faces = [
            [0, 1, 2], [0, 1, 3], [0, 2, 3], [1, 2, 3]
        ]
        
        # Subdiviser selon l'ADN
        iterations = min(3, self.dna.seed_values[7] // 80)
        
        for _ in range(iterations):
            new_vertices = list(vertices)
            new_faces = []
            
            for face in faces:
                # Points milieux
                mid_points = []
                for i in range(3):
                    p1 = vertices[face[i]]
                    p2 = vertices[face[(i + 1) % 3]]
                    mid = [(p1[k] + p2[k]) / 2 for k in range(3)]
                    
                    # Deplacer vers l'exterieur
                    length = sum(m**2 for m in mid)**0.5
                    if length > 0:
                        scale = 1.1
                        mid = [m * scale / length * length for m in mid]
                    
                    new_vertices.append(mid)
                    mid_points.append(len(new_vertices) - 1)
                
                # Creer 4 nouveaux triangles
                new_faces.append([face[0], mid_points[0], mid_points[2]])
                new_faces.append([face[1], mid_points[1], mid_points[0]])
                new_faces.append([face[2], mid_points[2], mid_points[1]])
                new_faces.append([mid_points[0], mid_points[1], mid_points[2]])
            
            vertices = new_vertices
            faces = new_faces
        
        return vertices, faces
    
    def _create_7d_projection(self) -> Tuple[List, List]:
        """Cree une projection 3D d'un objet 7D"""
        vertices = []
        faces = []
        
        # Creer un hypercube simplifie projete
        n_points = 32
        
        for i in range(n_points):
            t = 2 * math.pi * i / n_points
            
            # Coordonnees 7D projetees en 3D
            d1 = math.sin(t)
            d2 = math.cos(t)
            d3 = math.sin(2 * t)
            d4 = math.cos(2 * t)
            d5 = math.sin(3 * t)
            d6 = math.cos(3 * t)
            d7 = math.sin(4 * t)
            
            # Projection en 3D avec poids de l'ADN
            w = [self.dna.seed_values[k] / 255 for k in range(7)]
            
            x = d1 * w[0] + d4 * w[3] + d7 * w[6]
            y = d2 * w[1] + d5 * w[4]
            z = d3 * w[2] + d6 * w[5]
            
            vertices.append([x, y, z])
        
        # Connecter les points
        for i in range(n_points):
            j = (i + 1) % n_points
            k = (i + 2) % n_points
            faces.append([i, j, k])
        
        return vertices, faces
    
    def _create_hybrid_form(self) -> Tuple[List, List]:
        """Cree une forme hybride combinant plusieurs geometries"""
        # Combiner sphere et tore
        sphere_v, sphere_f = self._create_quantum_sphere()
        torus_v, torus_f = self._create_spinor_torus()
        
        # Reduire le tore
        torus_v = [[v[0] * 0.5, v[1] * 0.5, v[2] * 0.5 + 1.5] for v in torus_v]
        
        # Combiner
        offset = len(sphere_v)
        torus_f = [[f[0] + offset, f[1] + offset, f[2] + offset] for f in torus_f]
        
        vertices = sphere_v + torus_v
        faces = sphere_f + torus_f
        
        return vertices, faces
    
    def _create_nexus_crystal(self) -> Tuple[List, List]:
        """Cree un cristal du Nexus"""
        vertices = []
        
        # Pointe superieure
        vertices.append([0, 0, 1.5])
        
        # Anneau superieur
        n_sides = 6 + (self.dna.seed_values[8] % 4)
        for i in range(n_sides):
            angle = 2 * math.pi * i / n_sides
            r = 0.8
            vertices.append([r * math.cos(angle), r * math.sin(angle), 0.5])
        
        # Anneau central (plus large)
        for i in range(n_sides):
            angle = 2 * math.pi * i / n_sides + math.pi / n_sides
            r = 1.2
            vertices.append([r * math.cos(angle), r * math.sin(angle), 0])
        
        # Anneau inferieur
        for i in range(n_sides):
            angle = 2 * math.pi * i / n_sides
            r = 0.8
            vertices.append([r * math.cos(angle), r * math.sin(angle), -0.5])
        
        # Pointe inferieure
        vertices.append([0, 0, -1.5])
        
        # Faces
        faces = []
        
        # Pointe superieure vers anneau superieur
        for i in range(n_sides):
            faces.append([0, 1 + i, 1 + (i + 1) % n_sides])
        
        # Anneau superieur vers central
        for i in range(n_sides):
            faces.append([1 + i, 1 + n_sides + i, 1 + (i + 1) % n_sides])
            faces.append([1 + (i + 1) % n_sides, 1 + n_sides + i, 1 + n_sides + (i + 1) % n_sides])
        
        # Central vers inferieur
        for i in range(n_sides):
            faces.append([1 + n_sides + i, 1 + 2 * n_sides + i, 1 + n_sides + (i + 1) % n_sides])
            faces.append([1 + n_sides + (i + 1) % n_sides, 1 + 2 * n_sides + i, 1 + 2 * n_sides + (i + 1) % n_sides])
        
        # Anneau inferieur vers pointe
        bottom_idx = 1 + 3 * n_sides
        for i in range(n_sides):
            faces.append([1 + 2 * n_sides + i, bottom_idx, 1 + 2 * n_sides + (i + 1) % n_sides])
        
        return vertices, faces
    
    def _apply_transformations(self, vertices: List) -> List:
        """Applique des transformations basees sur l'ADN"""
        dna = self.dna
        
        # Scaling
        sx = 1.0 + dna.seed_values[9] / 500
        sy = 1.0 + dna.seed_values[10] / 500
        sz = 1.0 + dna.seed_values[11] / 500
        
        # Rotation angles
        ax = dna.seed_values[12] * math.pi / 128
        ay = dna.seed_values[13] * math.pi / 128
        az = dna.seed_values[14] * math.pi / 128
        
        result = []
        for v in vertices:
            x, y, z = v[0] * sx, v[1] * sy, v[2] * sz
            
            # Rotation X
            y2 = y * math.cos(ax) - z * math.sin(ax)
            z2 = y * math.sin(ax) + z * math.cos(ax)
            y, z = y2, z2
            
            # Rotation Y
            x2 = x * math.cos(ay) + z * math.sin(ay)
            z2 = -x * math.sin(ay) + z * math.cos(ay)
            x, z = x2, z2
            
            # Rotation Z
            x2 = x * math.cos(az) - y * math.sin(az)
            y2 = x * math.sin(az) + y * math.cos(az)
            x, y = x2, y2
            
            result.append([round(x, 6), round(y, 6), round(z, 6)])
        
        return result
    
    def _calculate_normals(self, vertices: List, faces: List) -> List:
        """Calcule les normales pour chaque vertex"""
        normals = [[0, 0, 0] for _ in vertices]
        
        for face in faces:
            if len(face) >= 3:
                v0 = vertices[face[0]]
                v1 = vertices[face[1]]
                v2 = vertices[face[2]]
                
                # Vecteurs
                u = [v1[i] - v0[i] for i in range(3)]
                v = [v2[i] - v0[i] for i in range(3)]
                
                # Produit vectoriel
                n = [
                    u[1] * v[2] - u[2] * v[1],
                    u[2] * v[0] - u[0] * v[2],
                    u[0] * v[1] - u[1] * v[0]
                ]
                
                # Ajouter aux vertices de la face
                for idx in face:
                    for i in range(3):
                        normals[idx][i] += n[i]
        
        # Normaliser
        for i, n in enumerate(normals):
            length = sum(x**2 for x in n)**0.5
            if length > 0:
                normals[i] = [round(x / length, 6) for x in n]
            else:
                normals[i] = [0, 0, 1]
        
        return normals
    
    def _generate_uvs(self, vertices: List) -> List:
        """Genere les coordonnees UV"""
        uvs = []
        for v in vertices:
            # Projection spherique simple
            length = (v[0]**2 + v[1]**2 + v[2]**2)**0.5
            if length > 0:
                u = 0.5 + math.atan2(v[1], v[0]) / (2 * math.pi)
                vv = 0.5 - math.asin(max(-1, min(1, v[2] / length))) / math.pi
            else:
                u, vv = 0.5, 0.5
            uvs.append([round(u, 4), round(vv, 4)])
        return uvs
    
    def generate_avatar(self) -> Avatar3D:
        """Genere l'avatar complet"""
        geometry = self.generate_geometry()
        
        avatar_id = hashlib.sha256(
            f"{self.vault_id}{self.dna.vault_hash}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        self.avatar = Avatar3D(
            avatar_id=avatar_id,
            vault_id=self.vault_id,
            dna=self.dna,
            vertices=geometry['vertices'],
            faces=geometry['faces'],
            normals=geometry['normals'],
            uvs=geometry['uvs'],
            created_at=datetime.now().isoformat(),
            version=AVATAR_VERSION
        )
        
        return self.avatar
    
    def export_obj(self, output_path: str) -> str:
        """Exporte l'avatar en format OBJ"""
        if not self.avatar:
            self.generate_avatar()
        
        avatar = self.avatar
        output_path = Path(output_path)
        
        with open(output_path, 'w') as f:
            f.write(f"# Poly-Spinor Nexus 7D Avatar\n")
            f.write(f"# Vault: {avatar.vault_id}\n")
            f.write(f"# Avatar ID: {avatar.avatar_id}\n")
            f.write(f"# Type: {avatar.dna.geometric_name}\n")
            f.write(f"# Rarity: {avatar.dna.rarity_tier} ({avatar.dna.rarity_score:.1f})\n")
            f.write(f"# Generated: {avatar.created_at}\n\n")
            
            # Vertices
            for v in avatar.vertices:
                f.write(f"v {v[0]} {v[1]} {v[2]}\n")
            
            f.write("\n")
            
            # UVs
            for uv in avatar.uvs:
                f.write(f"vt {uv[0]} {uv[1]}\n")
            
            f.write("\n")
            
            # Normals
            for n in avatar.normals:
                f.write(f"vn {n[0]} {n[1]} {n[2]}\n")
            
            f.write("\n")
            
            # Faces
            for face in avatar.faces:
                f.write(f"f {face[0]+1}/{face[0]+1}/{face[0]+1} "
                       f"{face[1]+1}/{face[1]+1}/{face[1]+1} "
                       f"{face[2]+1}/{face[2]+1}/{face[2]+1}\n")
        
        avatar.obj_path = str(output_path)
        return str(output_path)
    
    def generate_texture(self, output_path: str, size: int = 512) -> str:
        """Genere une texture unique pour l'avatar"""
        if not PIL_AVAILABLE:
            print("[WARN] PIL not available for texture generation")
            return ""
        
        if not self.avatar:
            self.generate_avatar()
        
        texture = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(texture)
        
        dna = self.dna
        
        # Fond avec gradient
        for y in range(size):
            for x in range(size):
                # Couleur basee sur la position et l'ADN
                idx = ((x + y) // 64) % len(dna.color_palette)
                base_color = dna.color_palette[idx]
                
                r = int(base_color[1:3], 16)
                g = int(base_color[3:5], 16)
                b = int(base_color[5:7], 16)
                
                # Variation
                noise = (dna.seed_values[(x * y) % 16] % 30) - 15
                r = max(0, min(255, r + noise))
                g = max(0, min(255, g + noise))
                b = max(0, min(255, b + noise))
                
                texture.putpixel((x, y), (r, g, b, 200))
        
        # Motifs geometriques
        cell_size = 64
        for i in range(0, size, cell_size):
            for j in range(0, size, cell_size):
                color_idx = ((i + j) // cell_size) % len(dna.color_palette)
                color = dna.color_palette[color_idx]
                rgba = (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16), 150)
                
                pattern = (i * j) % 4
                
                if pattern == 0:
                    draw.ellipse([i + 8, j + 8, i + cell_size - 8, j + cell_size - 8], 
                               fill=rgba, outline=rgba)
                elif pattern == 1:
                    draw.rectangle([i + 8, j + 8, i + cell_size - 8, j + cell_size - 8],
                                 fill=rgba, outline=rgba)
                elif pattern == 2:
                    points = [
                        (i + cell_size // 2, j + 8),
                        (i + cell_size - 8, j + cell_size - 8),
                        (i + 8, j + cell_size - 8)
                    ]
                    draw.polygon(points, fill=rgba, outline=rgba)
                else:
                    draw.line([i + 8, j + 8, i + cell_size - 8, j + cell_size - 8], 
                             fill=rgba, width=3)
                    draw.line([i + cell_size - 8, j + 8, i + 8, j + cell_size - 8],
                             fill=rgba, width=3)
        
        # Appliquer un flou leger
        texture = texture.filter(ImageFilter.GaussianBlur(radius=1))
        
        texture.save(output_path)
        self.avatar.texture_path = str(output_path)
        
        return str(output_path)
    
    def generate_preview(self, output_path: str, size: int = 400) -> str:
        """Genere une image de previsualisation 2D"""
        if not PIL_AVAILABLE:
            print("[WARN] PIL not available for preview generation")
            return ""
        
        if not self.avatar:
            self.generate_avatar()
        
        img = Image.new('RGBA', (size, size), (20, 20, 30, 255))
        draw = ImageDraw.Draw(img)
        
        avatar = self.avatar
        dna = self.dna
        
        # Projection 2D simple
        center_x, center_y = size // 2, size // 2
        scale = size // 4
        
        # Dessiner les edges
        for face in avatar.faces[:100]:  # Limiter pour la performance
            points = []
            for idx in face:
                v = avatar.vertices[idx]
                # Projection orthographique
                x = center_x + int(v[0] * scale)
                y = center_y - int(v[1] * scale)  # Y inverse
                points.append((x, y))
            
            if len(points) >= 3:
                color_idx = face[0] % len(dna.color_palette)
                color = dna.color_palette[color_idx]
                rgba = (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16), 180)
                
                draw.polygon(points, fill=rgba, outline=(255, 255, 255, 100))
        
        # Ajouter le titre
        title = f"{dna.geometric_name.replace('_', ' ').title()}"
        draw.text((10, 10), title, fill=(255, 255, 255, 255))
        draw.text((10, size - 30), f"Rarity: {dna.rarity_tier.upper()}", 
                 fill=(255, 215, 0, 255))
        
        img.save(output_path)
        self.avatar.preview_path = str(output_path)
        
        return str(output_path)
    
    def get_metadata(self) -> Dict:
        """Retourne les metadonnees completes de l'avatar"""
        if not self.avatar:
            self.generate_avatar()
        
        return {
            'avatar_id': self.avatar.avatar_id,
            'vault_id': self.vault_id,
            'version': AVATAR_VERSION,
            'dna': self.dna.to_dict(),
            'geometry': {
                'type': self.dna.geometric_name,
                'vertex_count': len(self.avatar.vertices),
                'face_count': len(self.avatar.faces)
            },
            'files': {
                'obj': self.avatar.obj_path,
                'texture': self.avatar.texture_path,
                'preview': self.avatar.preview_path
            },
            'created_at': self.avatar.created_at
        }


# ============================================================================
# TEST
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  QUANTUM AVATAR GENERATOR TEST")
    print("=" * 60)
    
    # Generer un avatar de test
    generator = QuantumAvatarGenerator(
        vault_id="test_vault_001",
        generation=1
    )
    
    print(f"\nDNA Extract:")
    print(f"  Vault Hash: {generator.dna.vault_hash[:16]}...")
    print(f"  Geometric Type: {generator.dna.geometric_name}")
    print(f"  Rarity: {generator.dna.rarity_tier} ({generator.dna.rarity_score:.1f})")
    print(f"  Colors: {generator.dna.color_palette}")
    
    print(f"\nAttributes:")
    for attr, value in generator.dna.attributes.items():
        print(f"  {attr}: {value:.2f}")
    
    # Generer l'avatar
    avatar = generator.generate_avatar()
    print(f"\nAvatar Generated:")
    print(f"  ID: {avatar.avatar_id}")
    print(f"  Vertices: {len(avatar.vertices)}")
    print(f"  Faces: {len(avatar.faces)}")
    
    # Exporter (si dossier existe)
    from pathlib import Path
    output_dir = Path(__file__).parent.parent.parent / "avatars"
    output_dir.mkdir(exist_ok=True)
    
    obj_path = generator.export_obj(output_dir / f"avatar_{avatar.avatar_id}.obj")
    print(f"\nExported OBJ: {obj_path}")
    
    if PIL_AVAILABLE:
        texture_path = generator.generate_texture(output_dir / f"texture_{avatar.avatar_id}.png")
        print(f"Generated Texture: {texture_path}")
        
        preview_path = generator.generate_preview(output_dir / f"preview_{avatar.avatar_id}.png")
        print(f"Generated Preview: {preview_path}")
    
    print("\n" + "=" * 60)
    print("  TEST COMPLETE")
    print("=" * 60)
