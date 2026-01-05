"""
Base de Données des Propriétés Matérielles des Polyèdres
Propriétés physiques avancées pour simulation de lancers de dés
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class MaterialType(Enum):
    """Types de matériaux supportés"""
    METAL = "metal"
    WOOD = "wood"
    PLASTIC = "plastic"
    CRYSTAL = "crystal"
    CERAMIC = "ceramic"
    COMPOSITE = "composite"


@dataclass
class AcousticProperties:
    """Propriétés acoustiques d'un matériau"""
    speed_of_sound: float  # m/s
    impedance: float  # kg/(m²·s)
    damping_coefficient: float = 0.1
    resonant_frequencies: List[float] = field(default_factory=list)


@dataclass
class ThermalProperties:
    """Propriétés thermiques d'un matériau"""
    conductivity: float  # W/(m·K)
    specific_heat: float = 500.0  # J/(kg·K)
    expansion_coefficient: float = 10e-6  # 1/K
    temperature: float = 22.0  # °C (température ambiante)


@dataclass
class AnisotropicFactors:
    """Facteurs anisotropiques pour matériaux directionnels"""
    parallel: float = 1.0
    perpendicular: float = 1.0
    grain_direction: np.ndarray = field(default_factory=lambda: np.array([0, 0, 1]))


@dataclass
class MaterialProperties:
    """Propriétés complètes d'un matériau"""
    name: str
    material_type: MaterialType
    density: float  # kg/m³
    elasticity: float  # Coefficient de restitution (0-1)
    friction: float  # Coefficient de frottement cinétique
    roughness: float  # Rugosité de surface (0-1)
    hardness: float = 5.0  # Échelle de Mohs
    
    # Propriétés optionnelles
    thermal: Optional[ThermalProperties] = None
    acoustic: Optional[AcousticProperties] = None
    anisotropic: Optional[AnisotropicFactors] = None
    
    # Propriétés spéciales
    viscoelasticity: float = 0.0  # Coefficient viscoélastique
    brittleness: float = 0.0  # Fragilité (0-1)
    translucency: float = 0.0  # Translucidité (0-1)
    
    # Métadonnées
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'type': self.material_type.value,
            'density': self.density,
            'elasticity': self.elasticity,
            'friction': self.friction,
            'roughness': self.roughness,
            'hardness': self.hardness,
            'viscoelasticity': self.viscoelasticity
        }


@dataclass
class CompositeMaterial:
    """Matériau composite avec plusieurs couches"""
    name: str
    core_material: str
    coating_material: str
    coating_thickness: float  # mètres
    interface_bond_strength: float = 150e6  # Pa
    
    def get_effective_properties(self, db: 'PolyhedronMaterialDatabase') -> MaterialProperties:
        """Calcule les propriétés effectives du composite"""
        core = db.get_material(self.core_material)
        coating = db.get_material(self.coating_material)
        
        if not core or not coating:
            raise ValueError(f"Matériaux non trouvés: {self.core_material}, {self.coating_material}")
        
        # Règle des mélanges simplifiée
        core_fraction = 0.9  # 90% core, 10% coating approximativement
        coating_fraction = 1 - core_fraction
        
        effective_density = core.density * core_fraction + coating.density * coating_fraction
        effective_elasticity = (core.elasticity + coating.elasticity) / 2
        effective_friction = coating.friction  # Surface = coating
        effective_roughness = coating.roughness
        
        return MaterialProperties(
            name=self.name,
            material_type=MaterialType.COMPOSITE,
            density=effective_density,
            elasticity=effective_elasticity,
            friction=effective_friction,
            roughness=effective_roughness,
            hardness=(core.hardness + coating.hardness) / 2,
            custom_properties={
                'core': self.core_material,
                'coating': self.coating_material,
                'coating_thickness': self.coating_thickness
            }
        )


class PolyhedronMaterialDatabase:
    """Base de données des propriétés physiques des matériaux de dés"""
    
    def __init__(self):
        self.materials: Dict[str, MaterialProperties] = {}
        self.composites: Dict[str, CompositeMaterial] = {}
        self._initialize_default_materials()
        self._initialize_default_composites()
    
    def _initialize_default_materials(self):
        """Initialise les matériaux par défaut"""
        
        # === MÉTAUX ===
        self.materials["tungsten"] = MaterialProperties(
            name="tungsten",
            material_type=MaterialType.METAL,
            density=19300,
            elasticity=0.15,
            friction=0.35,
            roughness=0.02,
            hardness=7.5,
            thermal=ThermalProperties(conductivity=173),
            acoustic=AcousticProperties(speed_of_sound=5170, impedance=101.2e6)
        )
        
        self.materials["aluminum"] = MaterialProperties(
            name="aluminum",
            material_type=MaterialType.METAL,
            density=2700,
            elasticity=0.30,
            friction=0.42,
            roughness=0.08,
            hardness=2.75,
            thermal=ThermalProperties(conductivity=237),
            acoustic=AcousticProperties(speed_of_sound=6320, impedance=17.0e6)
        )
        
        self.materials["brass"] = MaterialProperties(
            name="brass",
            material_type=MaterialType.METAL,
            density=8500,
            elasticity=0.25,
            friction=0.38,
            roughness=0.05,
            hardness=3.5,
            thermal=ThermalProperties(conductivity=109)
        )
        
        self.materials["steel"] = MaterialProperties(
            name="steel",
            material_type=MaterialType.METAL,
            density=7850,
            elasticity=0.20,
            friction=0.40,
            roughness=0.04,
            hardness=6.0,
            thermal=ThermalProperties(conductivity=50),
            acoustic=AcousticProperties(speed_of_sound=5960, impedance=46.7e6)
        )
        
        self.materials["titanium"] = MaterialProperties(
            name="titanium",
            material_type=MaterialType.METAL,
            density=4500,
            elasticity=0.22,
            friction=0.36,
            roughness=0.03,
            hardness=6.0,
            thermal=ThermalProperties(conductivity=22)
        )
        
        # === BOIS ===
        self.materials["ebony"] = MaterialProperties(
            name="ebony",
            material_type=MaterialType.WOOD,
            density=1200,
            elasticity=0.45,
            friction=0.55,
            roughness=0.15,
            hardness=4.0,
            anisotropic=AnisotropicFactors(parallel=1.0, perpendicular=0.6),
            custom_properties={
                'grain_pattern': 'irregular',
                'moisture_content': 0.08
            }
        )
        
        self.materials["maple"] = MaterialProperties(
            name="maple",
            material_type=MaterialType.WOOD,
            density=750,
            elasticity=0.52,
            friction=0.62,
            roughness=0.12,
            hardness=3.5,
            anisotropic=AnisotropicFactors(parallel=1.0, perpendicular=0.55),
            custom_properties={
                'grain_pattern': 'curly',
                'moisture_content': 0.12
            }
        )
        
        self.materials["oak"] = MaterialProperties(
            name="oak",
            material_type=MaterialType.WOOD,
            density=750,
            elasticity=0.48,
            friction=0.58,
            roughness=0.14,
            hardness=4.0,
            anisotropic=AnisotropicFactors(parallel=1.0, perpendicular=0.5)
        )
        
        self.materials["rosewood"] = MaterialProperties(
            name="rosewood",
            material_type=MaterialType.WOOD,
            density=900,
            elasticity=0.42,
            friction=0.50,
            roughness=0.10,
            hardness=4.5
        )
        
        # === PLASTIQUES/RÉSINES ===
        self.materials["acrylic"] = MaterialProperties(
            name="acrylic",
            material_type=MaterialType.PLASTIC,
            density=1180,
            elasticity=0.65,
            friction=0.28,
            roughness=0.01,
            hardness=3.0,
            viscoelasticity=0.15,
            translucency=0.8,
            thermal=ThermalProperties(conductivity=0.2, expansion_coefficient=70e-6)
        )
        
        self.materials["polycarbonate"] = MaterialProperties(
            name="polycarbonate",
            material_type=MaterialType.PLASTIC,
            density=1200,
            elasticity=0.70,
            friction=0.32,
            roughness=0.03,
            hardness=2.5,
            viscoelasticity=0.20,
            translucency=0.9,
            custom_properties={'impact_resistance': 'high'}
        )
        
        self.materials["abs"] = MaterialProperties(
            name="abs",
            material_type=MaterialType.PLASTIC,
            density=1050,
            elasticity=0.60,
            friction=0.35,
            roughness=0.05,
            hardness=2.0,
            viscoelasticity=0.12
        )
        
        self.materials["resin"] = MaterialProperties(
            name="resin",
            material_type=MaterialType.PLASTIC,
            density=1150,
            elasticity=0.55,
            friction=0.30,
            roughness=0.02,
            hardness=3.5,
            translucency=0.6
        )
        
        # === CRISTAUX/PIERRES ===
        self.materials["obsidian"] = MaterialProperties(
            name="obsidian",
            material_type=MaterialType.CRYSTAL,
            density=2500,
            elasticity=0.08,
            friction=0.45,
            roughness=0.25,
            hardness=5.5,
            brittleness=0.95,
            acoustic=AcousticProperties(speed_of_sound=4500, impedance=11.25e6)
        )
        
        self.materials["quartz"] = MaterialProperties(
            name="quartz",
            material_type=MaterialType.CRYSTAL,
            density=2650,
            elasticity=0.10,
            friction=0.40,
            roughness=0.02,
            hardness=7.0,
            brittleness=0.85,
            translucency=0.7
        )
        
        self.materials["sapphire"] = MaterialProperties(
            name="sapphire",
            material_type=MaterialType.CRYSTAL,
            density=3980,
            elasticity=0.12,
            friction=0.25,
            roughness=0.005,
            hardness=9.0,
            brittleness=0.70,
            translucency=0.85
        )
        
        self.materials["jade"] = MaterialProperties(
            name="jade",
            material_type=MaterialType.CRYSTAL,
            density=3300,
            elasticity=0.18,
            friction=0.35,
            roughness=0.08,
            hardness=6.5,
            translucency=0.4
        )
        
        # === CÉRAMIQUES ===
        self.materials["zirconia"] = MaterialProperties(
            name="zirconia",
            material_type=MaterialType.CERAMIC,
            density=5680,
            elasticity=0.12,
            friction=0.22,
            roughness=0.005,
            hardness=8.5,
            thermal=ThermalProperties(conductivity=2)
        )
        
        self.materials["porcelain"] = MaterialProperties(
            name="porcelain",
            material_type=MaterialType.CERAMIC,
            density=2400,
            elasticity=0.15,
            friction=0.30,
            roughness=0.01,
            hardness=7.0,
            brittleness=0.80
        )
        
        self.materials["bone"] = MaterialProperties(
            name="bone",
            material_type=MaterialType.CERAMIC,
            density=1900,
            elasticity=0.35,
            friction=0.45,
            roughness=0.12,
            hardness=3.5,
            custom_properties={'organic': True}
        )
    
    def _initialize_default_composites(self):
        """Initialise les matériaux composites par défaut"""
        
        self.composites["tungsten_carbide_core"] = CompositeMaterial(
            name="tungsten_carbide_core",
            core_material="tungsten",
            coating_material="zirconia",
            coating_thickness=0.001,
            interface_bond_strength=150e6
        )
        
        self.composites["wood_resin_inlay"] = CompositeMaterial(
            name="wood_resin_inlay",
            core_material="ebony",
            coating_material="acrylic",
            coating_thickness=0.0005
        )
        
        self.composites["metal_ceramic"] = CompositeMaterial(
            name="metal_ceramic",
            core_material="steel",
            coating_material="zirconia",
            coating_thickness=0.002
        )
    
    def get_material(self, name: str) -> Optional[MaterialProperties]:
        """Récupère un matériau par son nom"""
        if name in self.materials:
            return self.materials[name]
        
        if name in self.composites:
            return self.composites[name].get_effective_properties(self)
        
        return None
    
    def add_material(self, material: MaterialProperties):
        """Ajoute un nouveau matériau"""
        self.materials[material.name] = material
    
    def add_composite(self, composite: CompositeMaterial):
        """Ajoute un nouveau matériau composite"""
        self.composites[composite.name] = composite
    
    def list_materials(self, material_type: Optional[MaterialType] = None) -> List[str]:
        """Liste les matériaux disponibles"""
        if material_type:
            return [
                name for name, mat in self.materials.items()
                if mat.material_type == material_type
            ]
        return list(self.materials.keys()) + list(self.composites.keys())
    
    def get_material_by_density_range(self, min_density: float, 
                                      max_density: float) -> List[MaterialProperties]:
        """Récupère les matériaux dans une plage de densité"""
        return [
            mat for mat in self.materials.values()
            if min_density <= mat.density <= max_density
        ]
    
    def calculate_effective_restitution(self, mat1: str, mat2: str) -> float:
        """Calcule le coefficient de restitution effectif entre deux matériaux"""
        m1 = self.get_material(mat1)
        m2 = self.get_material(mat2)
        
        if not m1 or not m2:
            return 0.5
        
        # Formule simplifiée pour le coefficient de restitution effectif
        return np.sqrt(m1.elasticity * m2.elasticity)
    
    def calculate_friction_coefficient(self, mat1: str, mat2: str) -> float:
        """Calcule le coefficient de frottement entre deux matériaux"""
        m1 = self.get_material(mat1)
        m2 = self.get_material(mat2)
        
        if not m1 or not m2:
            return 0.4
        
        # Moyenne géométrique des coefficients de frottement
        return np.sqrt(m1.friction * m2.friction)


class SurfaceMaterialDatabase:
    """Base de données des propriétés de surfaces de lancer"""
    
    SURFACES = {
        "granite": {
            "hardness": 7.0,
            "roughness_profile": "fractal",
            "fractal_dimension": 2.3,
            "friction": 0.45,
            "elasticity": 0.10,
            "temperature_variation": 2.0,
            "micro_texture": "crystalline"
        },
        "oak_wood": {
            "hardness": 4.0,
            "roughness_profile": "directional",
            "grain_spacing": 0.002,
            "friction": 0.55,
            "elasticity": 0.40,
            "damping_coefficient": 0.12,
            "temperature_variation": 1.5
        },
        "leather": {
            "hardness": 2.5,
            "roughness_profile": "random",
            "friction": 0.65,
            "elasticity": 0.60,
            "compliance": 0.15,
            "hysteresis": 0.08,
            "temperature_variation": 0.5
        },
        "steel_plate": {
            "hardness": 8.0,
            "roughness_profile": "machined",
            "surface_waviness": 0.0001,
            "friction": 0.35,
            "elasticity": 0.15,
            "temperature_variation": 0.2
        },
        "felt": {
            "hardness": 1.5,
            "roughness_profile": "random",
            "friction": 0.70,
            "elasticity": 0.75,
            "compliance": 0.25,
            "damping_coefficient": 0.30
        },
        "rubber": {
            "hardness": 2.0,
            "roughness_profile": "uniform",
            "friction": 0.80,
            "elasticity": 0.85,
            "viscoelasticity": 0.20,
            "damping_coefficient": 0.25
        },
        "glass": {
            "hardness": 6.5,
            "roughness_profile": "smooth",
            "friction": 0.25,
            "elasticity": 0.08,
            "brittleness": 0.90,
            "temperature_variation": 0.1
        },
        "marble": {
            "hardness": 4.5,
            "roughness_profile": "polished",
            "friction": 0.35,
            "elasticity": 0.12,
            "temperature_variation": 1.0
        }
    }
    
    @classmethod
    def get_surface(cls, name: str) -> Optional[Dict]:
        """Récupère les propriétés d'une surface"""
        return cls.SURFACES.get(name)
    
    @classmethod
    def list_surfaces(cls) -> List[str]:
        """Liste les surfaces disponibles"""
        return list(cls.SURFACES.keys())
    
    @classmethod
    def create_custom_surface(cls, name: str, properties: Dict) -> Dict:
        """Crée une surface personnalisée"""
        required = ['hardness', 'friction', 'elasticity']
        for prop in required:
            if prop not in properties:
                raise ValueError(f"Propriété requise manquante: {prop}")
        
        cls.SURFACES[name] = properties
        return properties


# Instance globale de la base de données
MATERIAL_DB = PolyhedronMaterialDatabase()
SURFACE_DB = SurfaceMaterialDatabase()
