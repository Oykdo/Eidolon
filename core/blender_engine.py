"""
Moteur Blender 7D pour Poly-Spinor Nexus
Visualisation des clusters quantiques et matériaux cryptographiques
"""

import numpy as np
import math
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import bpy
    BLENDER_AVAILABLE = True
except ImportError:
    BLENDER_AVAILABLE = False
    
from .quantum_verification import AdvancedBellVerification
from .spatial_capture import SpatialCaptureSystem, Point7D, DieType
from .spinor_crypto import SpinorCryptographicEngine


DIE_TYPES = [
    DieType.D4, DieType.D6, DieType.D8, DieType.D10, DieType.D12,
    DieType.D20, DieType.D100, DieType.D6, DieType.D6, DieType.D20
]


@dataclass
class ClusterConfig:
    """Configuration d'un cluster 7D"""
    die_type: DieType
    num_points: int = 30
    color_base: Tuple[float, float, float] = (0.5, 0.5, 0.5)
    scale_factor: float = 1.0


class PolySpinorBlenderEngine:
    """Moteur de visualisation 7D dans Blender"""
    
    def __init__(self, quantum_data: Optional[Dict] = None):
        self.quantum_data = quantum_data or {}
        self.verification = AdvancedBellVerification()
        self.spatial = SpatialCaptureSystem()
        self.crypto = SpinorCryptographicEngine()
        self.clusters: List[Any] = []
        self.materials: Dict[str, Any] = {}
        
    def clean_scene(self):
        """Nettoie la scène Blender existante"""
        if not BLENDER_AVAILABLE:
            return
            
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        
        for collection in bpy.data.collections:
            if collection.name.startswith("Cluster_"):
                bpy.data.collections.remove(collection)
    
    def create_hyper_cluster_scene(self, data_7d: Optional[Dict] = None) -> List[Any]:
        """Crée une scène hyper-cluster basée sur les données 7D"""
        if not BLENDER_AVAILABLE:
            return self._create_mock_clusters(data_7d)
        
        self.clean_scene()
        self.clusters = []
        
        for i, die_type in enumerate(DIE_TYPES):
            if data_7d and die_type.name in data_7d:
                cluster_data = data_7d[die_type.name]
            else:
                cluster_data = self._generate_cluster_data(die_type, 30)
            
            cluster = self.create_single_cluster(die_type, cluster_data, i)
            self.clusters.append(cluster)
        
        self.apply_spinor_transformations(self.clusters)
        self.create_correlation_fields(self.clusters)
        self.setup_crypto_ui()
        
        return self.clusters
    
    def _generate_cluster_data(self, die_type: DieType, num_points: int) -> List[Point7D]:
        """Génère des données de cluster simulées"""
        points = []
        for _ in range(num_points):
            point = Point7D(
                x=np.random.uniform(0, 10),
                y=np.random.uniform(0, 10),
                alpha=np.random.uniform(0, 360),
                beta=np.random.uniform(0, 360),
                gamma=np.random.uniform(0, 360),
                face_value=np.random.randint(1, die_type.value + 1),
                entropy_contribution=np.random.uniform(0, 1)
            )
            points.append(point)
        return points
    
    def _create_mock_clusters(self, data_7d: Optional[Dict]) -> List[Dict]:
        """Crée des clusters simulés sans Blender"""
        clusters = []
        for i, die_type in enumerate(DIE_TYPES):
            cluster = {
                'name': f"Cluster_{die_type.name}",
                'die_type': die_type,
                'points': self._generate_cluster_data(die_type, 30),
                'index': i
            }
            clusters.append(cluster)
        return clusters
    
    def create_single_cluster(self, die_type: DieType, 
                              points_7d: List[Point7D],
                              cluster_index: int) -> Any:
        """Crée un cluster avec 30 objets 7D"""
        if not BLENDER_AVAILABLE:
            return {'name': f"Cluster_{die_type.name}", 'points': points_7d}
        
        cluster = bpy.data.collections.new(f"Cluster_{die_type.name}")
        bpy.context.scene.collection.children.link(cluster)
        
        for i, point in enumerate(points_7d):
            obj = self.create_7d_object(die_type, point, i, cluster_index)
            self.apply_7d_properties(obj, point)
            
            for coll in obj.users_collection:
                coll.objects.unlink(obj)
            cluster.objects.link(obj)
        
        self.add_cluster_effects(cluster, cluster_index)
        
        return cluster
    
    def create_7d_object(self, die_type: DieType, point: Point7D, 
                         point_index: int, cluster_index: int) -> Any:
        """Crée un objet géométrique représentant un point 7D"""
        if not BLENDER_AVAILABLE:
            return None
        
        mesh_type = self._get_mesh_type_for_die(die_type)
        location = self.calculate_3d_position(point, cluster_index)
        
        if mesh_type == 'tetrahedron':
            bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.3, 
                                            depth=0.4, location=location)
        elif mesh_type == 'cube':
            bpy.ops.mesh.primitive_cube_add(size=0.4, location=location)
        elif mesh_type == 'octahedron':
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, 
                                                   radius=0.25, location=location)
        elif mesh_type == 'dodecahedron':
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, 
                                                   radius=0.25, location=location)
        elif mesh_type == 'icosahedron':
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, 
                                                   radius=0.3, location=location)
        else:
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=location)
        
        obj = bpy.context.active_object
        obj.name = f"Die_{die_type.name}_{point_index}"
        
        return obj
    
    def _get_mesh_type_for_die(self, die_type: DieType) -> str:
        """Retourne le type de mesh approprié pour un type de dé"""
        mesh_map = {
            DieType.D4: 'tetrahedron',
            DieType.D6: 'cube',
            DieType.D8: 'octahedron',
            DieType.D10: 'decahedron',
            DieType.D12: 'dodecahedron',
            DieType.D20: 'icosahedron',
            DieType.D100: 'sphere'
        }
        return mesh_map.get(die_type, 'sphere')
    
    def calculate_3d_position(self, point: Point7D, 
                              cluster_index: int = 0) -> Tuple[float, float, float]:
        """Calcule la position 3D à partir des données 7D"""
        cluster_offset = cluster_index * 5
        
        x = point.x + cluster_offset
        y = point.y
        
        z = (point.alpha / 360.0 + point.beta / 360.0 + point.gamma / 360.0) / 3.0
        z *= point.entropy_contribution * 2
        
        return (x, y, z)
    
    def calculate_spinor_rotation(self, point: Point7D) -> Tuple[float, float, float, float]:
        """Calcule le quaternion de rotation spinorielle"""
        theta = point.alpha * np.pi / 180
        phi = point.beta * np.pi / 180
        psi = point.gamma * np.pi / 180
        
        w = np.cos(theta/2) * np.cos(phi/2) * np.cos(psi/2) + \
            np.sin(theta/2) * np.sin(phi/2) * np.sin(psi/2)
        x = np.sin(theta/2) * np.cos(phi/2) * np.cos(psi/2) - \
            np.cos(theta/2) * np.sin(phi/2) * np.sin(psi/2)
        y = np.cos(theta/2) * np.sin(phi/2) * np.cos(psi/2) + \
            np.sin(theta/2) * np.cos(phi/2) * np.sin(psi/2)
        z = np.cos(theta/2) * np.cos(phi/2) * np.sin(psi/2) - \
            np.sin(theta/2) * np.sin(phi/2) * np.cos(psi/2)
        
        return (w, x, y, z)
    
    def calculate_7d_scale(self, point: Point7D) -> Tuple[float, float, float]:
        """Calcule l'échelle basée sur les dimensions supplémentaires"""
        base_scale = 0.5 + point.entropy_contribution * 0.5
        
        scale_x = base_scale * (1 + 0.1 * np.sin(point.alpha * np.pi / 180))
        scale_y = base_scale * (1 + 0.1 * np.sin(point.beta * np.pi / 180))
        scale_z = base_scale * (1 + 0.1 * np.sin(point.gamma * np.pi / 180))
        
        return (scale_x, scale_y, scale_z)
    
    def apply_7d_properties(self, obj: Any, point: Point7D):
        """Applique les 7 dimensions à un objet Blender"""
        if not BLENDER_AVAILABLE or obj is None:
            return
        
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = self.calculate_spinor_rotation(point)
        obj.scale = self.calculate_7d_scale(point)
        
        material = self.create_crypto_material(point)
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)
        
        self.add_spinor_precession_animation(obj, point)
        self.set_quantum_properties(obj, point)
    
    def create_crypto_material(self, point: Point7D) -> Any:
        """Crée un matériau cryptographique basé sur les données 7D"""
        if not BLENDER_AVAILABLE:
            return None
        
        encoded_value = self.encode_7d(point)
        
        material = bpy.data.materials.new(name=f"CryptoMat_{id(point)}")
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        
        nodes.clear()
        
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        output_node.location = (400, 0)
        
        emission_node = nodes.new(type='ShaderNodeEmission')
        emission_node.location = (200, 0)
        
        hue = encoded_value
        saturation = 0.8
        value = 0.9 + point.entropy_contribution * 0.1
        
        r, g, b = self._hsv_to_rgb(hue, saturation, value)
        emission_node.inputs['Color'].default_value = (r, g, b, 1.0)
        emission_node.inputs['Strength'].default_value = 1.0 + point.entropy_contribution
        
        links.new(emission_node.outputs['Emission'], output_node.inputs['Surface'])
        
        return material
    
    def encode_7d(self, point: Point7D) -> float:
        """Encode les 7 dimensions en une valeur unique"""
        values = point.to_array()
        
        encoding = 0
        for i, value in enumerate(values):
            encoding += value * (256 ** i)
        
        encoded = math.sin(encoding) * 0.5 + 0.5
        
        return encoded
    
    def _hsv_to_rgb(self, h: float, s: float, v: float) -> Tuple[float, float, float]:
        """Convertit HSV en RGB"""
        if s == 0:
            return (v, v, v)
        
        h = h * 6
        i = int(h)
        f = h - i
        p = v * (1 - s)
        q = v * (1 - s * f)
        t = v * (1 - s * (1 - f))
        
        if i == 0:
            return (v, t, p)
        elif i == 1:
            return (q, v, p)
        elif i == 2:
            return (p, v, t)
        elif i == 3:
            return (p, q, v)
        elif i == 4:
            return (t, p, v)
        else:
            return (v, p, q)
    
    def add_spinor_precession_animation(self, obj: Any, point: Point7D):
        """Ajoute une animation de précession spinorielle"""
        if not BLENDER_AVAILABLE or obj is None:
            return
        
        precession_speed = point.entropy_contribution * 0.1
        
        obj.rotation_quaternion = self.calculate_spinor_rotation(point)
        obj.keyframe_insert(data_path="rotation_quaternion", frame=1)
        
        for frame in [30, 60, 90, 120]:
            angle = frame * precession_speed
            q = self.calculate_spinor_rotation(point)
            
            precession_q = (
                np.cos(angle/2),
                0,
                0,
                np.sin(angle/2)
            )
            
            new_q = self._quaternion_multiply(q, precession_q)
            obj.rotation_quaternion = new_q
            obj.keyframe_insert(data_path="rotation_quaternion", frame=frame)
    
    def _quaternion_multiply(self, q1: Tuple, q2: Tuple) -> Tuple:
        """Multiplie deux quaternions"""
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2
        
        w = w1*w2 - x1*x2 - y1*y2 - z1*z2
        x = w1*x2 + x1*w2 + y1*z2 - z1*y2
        y = w1*y2 - x1*z2 + y1*w2 + z1*x2
        z = w1*z2 + x1*y2 - y1*x2 + z1*w2
        
        return (w, x, y, z)
    
    def set_quantum_properties(self, obj: Any, point: Point7D):
        """Définit les propriétés quantiques personnalisées"""
        if not BLENDER_AVAILABLE or obj is None:
            return
        
        obj["quantum_coherence"] = point.entropy_contribution
        obj["spinor_phase"] = point.alpha
        obj["entanglement_strength"] = (point.beta + point.gamma) / 720.0
        obj["bell_correlation"] = np.random.uniform(2.0, 2.828)
        
        for i, val in enumerate(point.to_array()):
            obj[f"dim_{i}"] = float(val)
    
    def add_cluster_effects(self, cluster: Any, cluster_index: int):
        """Ajoute des effets visuels au cluster"""
        if not BLENDER_AVAILABLE:
            return
        
        pass
    
    def apply_spinor_transformations(self, clusters: List[Any]):
        """Applique les transformations spinorielles aux clusters"""
        if not BLENDER_AVAILABLE:
            return
        
        for i, cluster in enumerate(clusters):
            if hasattr(cluster, 'objects'):
                phase = i * 2 * np.pi / len(clusters)
                for obj in cluster.objects:
                    if obj.rotation_mode == 'QUATERNION':
                        current_q = obj.rotation_quaternion
                        phase_q = (np.cos(phase/2), 0, np.sin(phase/2), 0)
                        obj.rotation_quaternion = self._quaternion_multiply(
                            tuple(current_q), phase_q
                        )
    
    def create_correlation_fields(self, clusters: List[Any]):
        """Crée des champs de corrélation visuels entre clusters"""
        if not BLENDER_AVAILABLE:
            return
        
        pass
    
    def setup_crypto_ui(self):
        """Configure l'interface utilisateur cryptographique"""
        if not BLENDER_AVAILABLE:
            return
        
        pass
    
    def create_7d_object_standalone(self, data: Optional[np.ndarray] = None):
        """Crée un objet 7D autonome (compatibilité)"""
        if data is None:
            data = np.random.rand(7)
        
        if not BLENDER_AVAILABLE:
            return {'data': data, 'type': '7D_Object'}
        
        position = (data[0] * 10, data[1] * 10, data[2] * 10)
        
        bpy.ops.mesh.primitive_cube_add(size=1, location=position)
        obj = bpy.context.active_object
        obj.name = "7D_Object"
        
        scale_factor = np.mean(data[3:]) * 2
        obj.scale = (scale_factor, scale_factor, scale_factor)
        
        for i, val in enumerate(data):
            obj[f"dim_{i}"] = float(val)
        
        return obj


class CryptoMaterialGenerator:
    """Générateur de matériaux cryptographiques pour Blender"""
    
    def __init__(self, crypto_engine: Optional[SpinorCryptographicEngine] = None):
        self.crypto_engine = crypto_engine or SpinorCryptographicEngine()
        self.crypto_engine.generate_key_pair()
    
    def create_7d_material(self, point_data: Point7D) -> Any:
        """Crée un matériau représentant 7 dimensions"""
        if not BLENDER_AVAILABLE:
            return None
        
        material = bpy.data.materials.new(name="7D_Crypto_Material")
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()
        
        output_node = nodes.new(type='ShaderNodeOutputMaterial')
        output_node.location = (600, 0)
        
        mix_shader = nodes.new(type='ShaderNodeMixShader')
        mix_shader.location = (400, 0)
        
        emission_node = nodes.new(type='ShaderNodeEmission')
        emission_node.location = (200, 100)
        
        glossy_node = nodes.new(type='ShaderNodeBsdfGlossy')
        glossy_node.location = (200, -100)
        
        encoded = self._encode_7d_to_color(point_data)
        emission_node.inputs['Color'].default_value = (*encoded, 1.0)
        emission_node.inputs['Strength'].default_value = 2.0
        
        glossy_node.inputs['Color'].default_value = (*encoded, 1.0)
        glossy_node.inputs['Roughness'].default_value = 0.1
        
        mix_shader.inputs['Fac'].default_value = point_data.entropy_contribution
        
        links.new(emission_node.outputs['Emission'], mix_shader.inputs[1])
        links.new(glossy_node.outputs['BSDF'], mix_shader.inputs[2])
        links.new(mix_shader.outputs['Shader'], output_node.inputs['Surface'])
        
        return material
    
    def _encode_7d_to_color(self, point: Point7D) -> Tuple[float, float, float]:
        """Encode les données 7D en couleur RGB"""
        arr = point.to_array()
        
        r = (arr[0] + arr[3]) / 2
        g = (arr[1] + arr[4]) / 2
        b = (arr[2] + arr[5]) / 2
        
        r = (np.sin(r) + 1) / 2
        g = (np.sin(g) + 1) / 2
        b = (np.sin(b) + 1) / 2
        
        return (float(r), float(g), float(b))
    
    def generate_material(self, data: Any) -> Any:
        """Génère un matériau basé sur le hash cryptographique"""
        if not BLENDER_AVAILABLE:
            return None
        
        if isinstance(data, str):
            data = data.encode()
        elif isinstance(data, Point7D):
            data = str(data.to_dict()).encode()
        
        hash_val = self.crypto_engine.hash_data(data)
        
        color_hex = hash_val[:6]
        r = int(color_hex[0:2], 16) / 255.0
        g = int(color_hex[2:4], 16) / 255.0
        b = int(color_hex[4:6], 16) / 255.0
        
        mat = bpy.data.materials.new(name=f"CryptoMat_{hash_val[:8]}")
        mat.diffuse_color = (r, g, b, 1)
        mat.metallic = 0.5
        mat.roughness = 0.2
        
        return mat
    
    def generate_texture(self, data: Any, size: int = 256) -> Any:
        """Génère une texture procédurale basée sur l'aléa quantique"""
        if not BLENDER_AVAILABLE:
            return None
        
        random_bytes = self.crypto_engine.simulate_quantum_key_distribution(
            length=size * size * 3
        )
        pixels = np.frombuffer(random_bytes, dtype=np.uint8).astype(np.float32) / 255.0
        
        if len(pixels) < size * size * 4:
            pixels = np.tile(pixels, size * size * 4 // len(pixels) + 1)
        
        rgba_pixels = np.zeros(size * size * 4)
        for i in range(size * size):
            idx = i * 3
            if idx + 2 < len(pixels):
                rgba_pixels[i * 4] = pixels[idx]
                rgba_pixels[i * 4 + 1] = pixels[idx + 1]
                rgba_pixels[i * 4 + 2] = pixels[idx + 2]
                rgba_pixels[i * 4 + 3] = 1.0
        
        image = bpy.data.images.new(name="CryptoTexture", width=size, height=size)
        image.pixels = rgba_pixels.tolist()
        
        return image
