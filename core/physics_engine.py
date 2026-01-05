"""
Moteur de Simulation Physique Multi-Échelle pour Polyèdres
Dynamique des corps rigides avec interactions matérielles complexes
"""

import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import hashlib

from .material_database import (
    PolyhedronMaterialDatabase, MaterialProperties, 
    SurfaceMaterialDatabase, MATERIAL_DB
)


class PolyhedronType(Enum):
    """Types de polyèdres (dés)"""
    D4 = ("tetrahedron", 4)
    D6 = ("cube", 6)
    D8 = ("octahedron", 8)
    D10 = ("pentagonal_trapezohedron", 10)
    D12 = ("dodecahedron", 12)
    D20 = ("icosahedron", 20)
    D100 = ("sphere", 100)
    
    @property
    def shape_name(self) -> str:
        return self.value[0]
    
    @property
    def num_faces(self) -> int:
        return self.value[1]


@dataclass
class PhysicsState:
    """État physique d'un corps rigide"""
    position: np.ndarray  # [x, y, z]
    velocity: np.ndarray  # [vx, vy, vz]
    orientation: np.ndarray  # Quaternion [w, x, y, z]
    angular_velocity: np.ndarray  # [wx, wy, wz]
    
    def copy(self) -> 'PhysicsState':
        return PhysicsState(
            position=self.position.copy(),
            velocity=self.velocity.copy(),
            orientation=self.orientation.copy(),
            angular_velocity=self.angular_velocity.copy()
        )


@dataclass
class CollisionData:
    """Données d'une collision"""
    time: float
    contact_points: List[np.ndarray]
    normal: np.ndarray
    penetration: float
    impulse: np.ndarray
    energy_loss: float
    
    def to_dict(self) -> Dict:
        return {
            'time': self.time,
            'num_contacts': len(self.contact_points),
            'penetration': self.penetration,
            'energy_loss': self.energy_loss
        }


@dataclass
class Trajectory:
    """Trajectoire complète d'un lancer"""
    states: List[PhysicsState] = field(default_factory=list)
    collisions: List[CollisionData] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)
    
    def add_state(self, state: PhysicsState, time: float):
        self.states.append(state.copy())
        self.timestamps.append(time)
    
    def add_collision(self, collision: CollisionData):
        self.collisions.append(collision)
    
    def get_final_state(self) -> Optional[PhysicsState]:
        return self.states[-1] if self.states else None
    
    def total_energy_loss(self) -> float:
        return sum(c.energy_loss for c in self.collisions)


class PolyhedronGeometry:
    """Géométrie des polyèdres"""
    
    VERTICES = {
        PolyhedronType.D4: np.array([
            [1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]
        ]) / np.sqrt(3),
        
        PolyhedronType.D6: np.array([
            [1, 0, 0], [-1, 0, 0], [0, 1, 0], 
            [0, -1, 0], [0, 0, 1], [0, 0, -1]
        ]) * 0.5,
        
        PolyhedronType.D8: np.array([
            [1, 0, 0], [-1, 0, 0], [0, 1, 0],
            [0, -1, 0], [0, 0, 1], [0, 0, -1]
        ]),
        
        PolyhedronType.D20: None  # Généré dynamiquement
    }
    
    @classmethod
    def get_vertices(cls, poly_type: PolyhedronType, scale: float = 0.01) -> np.ndarray:
        """Retourne les sommets d'un polyèdre"""
        if poly_type in cls.VERTICES and cls.VERTICES[poly_type] is not None:
            return cls.VERTICES[poly_type] * scale
        
        # Génération pour les types complexes
        if poly_type == PolyhedronType.D20:
            return cls._generate_icosahedron_vertices(scale)
        elif poly_type == PolyhedronType.D12:
            return cls._generate_dodecahedron_vertices(scale)
        
        return cls._generate_sphere_vertices(20, scale)
    
    @classmethod
    def _generate_icosahedron_vertices(cls, scale: float) -> np.ndarray:
        """Génère les sommets d'un icosaèdre"""
        phi = (1 + np.sqrt(5)) / 2  # Nombre d'or
        vertices = []
        
        for s1 in [-1, 1]:
            for s2 in [-1, 1]:
                vertices.append([0, s1, s2 * phi])
                vertices.append([s1, s2 * phi, 0])
                vertices.append([s2 * phi, 0, s1])
        
        vertices = np.array(vertices)
        vertices = vertices / np.linalg.norm(vertices[0]) * scale
        return vertices
    
    @classmethod
    def _generate_dodecahedron_vertices(cls, scale: float) -> np.ndarray:
        """Génère les sommets d'un dodécaèdre"""
        phi = (1 + np.sqrt(5)) / 2
        vertices = []
        
        # Cube
        for s1 in [-1, 1]:
            for s2 in [-1, 1]:
                for s3 in [-1, 1]:
                    vertices.append([s1, s2, s3])
        
        # Rectangles
        for s1 in [-1, 1]:
            for s2 in [-1, 1]:
                vertices.append([0, s1 * phi, s2 / phi])
                vertices.append([s1 / phi, 0, s2 * phi])
                vertices.append([s1 * phi, s2 / phi, 0])
        
        vertices = np.array(vertices)
        vertices = vertices / np.linalg.norm(vertices[0]) * scale
        return vertices
    
    @classmethod
    def _generate_sphere_vertices(cls, n: int, scale: float) -> np.ndarray:
        """Génère des sommets approximant une sphère"""
        vertices = []
        for i in range(n):
            phi = np.arccos(1 - 2 * (i + 0.5) / n)
            theta = np.pi * (1 + np.sqrt(5)) * (i + 0.5)
            
            x = np.sin(phi) * np.cos(theta)
            y = np.sin(phi) * np.sin(theta)
            z = np.cos(phi)
            
            vertices.append([x, y, z])
        
        return np.array(vertices) * scale
    
    @classmethod
    def calculate_inertia_tensor(cls, poly_type: PolyhedronType, 
                                  mass: float, scale: float = 0.01) -> np.ndarray:
        """Calcule le tenseur d'inertie d'un polyèdre"""
        vertices = cls.get_vertices(poly_type, scale)
        
        # Approximation: sphère de même volume
        if poly_type == PolyhedronType.D100:
            r = scale
            I = 2/5 * mass * r**2
            return np.eye(3) * I
        
        # Calcul pour polyèdres
        I = np.zeros((3, 3))
        n = len(vertices)
        
        for v in vertices:
            r_squared = np.sum(v**2)
            I += mass / n * (r_squared * np.eye(3) - np.outer(v, v))
        
        return I


class PolyhedronPhysicsEngine:
    """Moteur de simulation physique multi-échelle pour les lancers de dés"""
    
    GRAVITY = np.array([0, 0, -9.81])
    AIR_DENSITY = 1.225  # kg/m³
    AIR_VISCOSITY = 1.81e-5  # Pa·s
    
    def __init__(self, polyhedron_type: PolyhedronType, 
                 material: MaterialProperties,
                 scale: float = 0.01):
        self.poly_type = polyhedron_type
        self.material = material
        self.scale = scale
        
        # Calcul des propriétés physiques
        self.volume = self._calculate_volume()
        self.mass = self.volume * material.density
        self.inertia_tensor = PolyhedronGeometry.calculate_inertia_tensor(
            polyhedron_type, self.mass, scale
        )
        self.inertia_tensor_inv = np.linalg.inv(self.inertia_tensor)
        
        # Paramètres de simulation
        self.dt = 0.0001  # 0.1ms timestep
        self.substeps = 10
    
    def _calculate_volume(self) -> float:
        """Calcule le volume approximatif du polyèdre"""
        # Approximation: sphère inscrite
        r = self.scale
        return 4/3 * np.pi * r**3
    
    def simulate_throw(self, initial_conditions: Dict,
                       surface_properties: Dict,
                       max_time: float = 5.0) -> Dict:
        """Simule un lancer complet avec interactions matérielles"""
        
        # État initial
        state = PhysicsState(
            position=np.array(initial_conditions['position']),
            velocity=np.array(initial_conditions['velocity']),
            orientation=self._normalize_quaternion(
                np.array(initial_conditions.get('orientation', [1, 0, 0, 0]))
            ),
            angular_velocity=np.array(initial_conditions.get('angular_velocity', [0, 0, 0]))
        )
        
        trajectory = Trajectory()
        time = 0.0
        
        # Phase 1: Vol
        while time < max_time and state.position[2] > 0:
            # Détection de collision avec le sol
            if state.position[2] <= self.scale:
                collision = self._handle_collision(state, surface_properties, time)
                trajectory.add_collision(collision)
                
                # Appliquer la réponse de collision
                state = self._apply_collision_response(state, collision)
                
                # Vérifier si le dé s'est arrêté
                if np.linalg.norm(state.velocity) < 0.01 and \
                   np.linalg.norm(state.angular_velocity) < 0.1:
                    break
            
            # Intégration RK4
            state = self._rk4_step(state)
            trajectory.add_state(state, time)
            time += self.dt
        
        # Phase finale: stabilisation
        final_state = self._stabilization_phase(state, trajectory, surface_properties)
        
        # Calculs additionnels
        thermal_effects = self._calculate_thermal_dissipation(trajectory)
        acoustic_signature = self._calculate_acoustic_signature(trajectory)
        
        return {
            'final_orientation': final_state.orientation,
            'final_position': final_state.position,
            'final_face': self._determine_top_face(final_state.orientation),
            'trajectory': trajectory,
            'material_specific_data': {
                'thermal_dissipation': thermal_effects,
                'acoustic_signature': acoustic_signature,
                'energy_loss_profile': trajectory.total_energy_loss(),
                'num_collisions': len(trajectory.collisions)
            },
            'simulation_hash': self._compute_simulation_hash(trajectory)
        }
    
    def _rk4_step(self, state: PhysicsState) -> PhysicsState:
        """Intégration Runge-Kutta 4"""
        k1 = self._compute_derivatives(state)
        
        state2 = self._apply_derivatives(state, k1, self.dt / 2)
        k2 = self._compute_derivatives(state2)
        
        state3 = self._apply_derivatives(state, k2, self.dt / 2)
        k3 = self._compute_derivatives(state3)
        
        state4 = self._apply_derivatives(state, k3, self.dt)
        k4 = self._compute_derivatives(state4)
        
        # Combinaison
        new_state = PhysicsState(
            position=state.position + self.dt / 6 * (
                k1['velocity'] + 2*k2['velocity'] + 2*k3['velocity'] + k4['velocity']
            ),
            velocity=state.velocity + self.dt / 6 * (
                k1['acceleration'] + 2*k2['acceleration'] + 
                2*k3['acceleration'] + k4['acceleration']
            ),
            orientation=self._normalize_quaternion(
                state.orientation + self.dt / 6 * (
                    k1['orientation_deriv'] + 2*k2['orientation_deriv'] + 
                    2*k3['orientation_deriv'] + k4['orientation_deriv']
                )
            ),
            angular_velocity=state.angular_velocity + self.dt / 6 * (
                k1['angular_acceleration'] + 2*k2['angular_acceleration'] + 
                2*k3['angular_acceleration'] + k4['angular_acceleration']
            )
        )
        
        return new_state
    
    def _compute_derivatives(self, state: PhysicsState) -> Dict:
        """Calcule les dérivées des variables d'état"""
        # Forces
        gravity_force = self.mass * self.GRAVITY
        drag_force = self._calculate_drag(state)
        total_force = gravity_force + drag_force
        
        # Accélération linéaire
        acceleration = total_force / self.mass
        
        # Dérivée du quaternion
        omega = state.angular_velocity
        q = state.orientation
        omega_quat = np.array([0, omega[0], omega[1], omega[2]])
        orientation_deriv = 0.5 * self._quaternion_multiply(q, omega_quat)
        
        # Accélération angulaire (équations d'Euler)
        angular_momentum = self.inertia_tensor @ omega
        torque = np.cross(omega, angular_momentum)  # Effet gyroscopique
        angular_acceleration = self.inertia_tensor_inv @ (-torque)
        
        return {
            'velocity': state.velocity,
            'acceleration': acceleration,
            'orientation_deriv': orientation_deriv,
            'angular_acceleration': angular_acceleration
        }
    
    def _apply_derivatives(self, state: PhysicsState, derivatives: Dict, 
                          dt: float) -> PhysicsState:
        """Applique les dérivées à l'état"""
        return PhysicsState(
            position=state.position + derivatives['velocity'] * dt,
            velocity=state.velocity + derivatives['acceleration'] * dt,
            orientation=self._normalize_quaternion(
                state.orientation + derivatives['orientation_deriv'] * dt
            ),
            angular_velocity=state.angular_velocity + derivatives['angular_acceleration'] * dt
        )
    
    def _calculate_drag(self, state: PhysicsState) -> np.ndarray:
        """Calcule la traînée aérodynamique"""
        v = state.velocity
        speed = np.linalg.norm(v)
        
        if speed < 1e-6:
            return np.zeros(3)
        
        # Coefficient de traînée (approximation sphère)
        Cd = 0.47
        
        # Surface frontale approximative
        A = np.pi * self.scale**2
        
        # Force de traînée
        drag_magnitude = 0.5 * self.AIR_DENSITY * Cd * A * speed**2
        drag_direction = -v / speed
        
        return drag_magnitude * drag_direction
    
    def _handle_collision(self, state: PhysicsState, 
                          surface_props: Dict, time: float) -> CollisionData:
        """Gère une collision avec la surface"""
        # Point de contact (simplifié)
        contact_point = state.position.copy()
        contact_point[2] = 0
        
        # Normale de surface
        normal = np.array([0, 0, 1])
        
        # Pénétration
        penetration = self.scale - state.position[2]
        
        # Coefficient de restitution effectif
        e = np.sqrt(self.material.elasticity * surface_props.get('elasticity', 0.5))
        
        # Vitesse relative au point de contact
        v_rel = state.velocity + np.cross(state.angular_velocity, 
                                          contact_point - state.position)
        v_n = np.dot(v_rel, normal)
        
        # Impulsion normale
        j_n = -(1 + e) * v_n * self.mass
        impulse = j_n * normal
        
        # Frottement
        v_t = v_rel - v_n * normal
        v_t_mag = np.linalg.norm(v_t)
        if v_t_mag > 1e-6:
            mu = np.sqrt(self.material.friction * surface_props.get('friction', 0.5))
            j_t = min(mu * abs(j_n), self.mass * v_t_mag)
            impulse -= j_t * v_t / v_t_mag
        
        # Perte d'énergie
        ke_before = 0.5 * self.mass * np.sum(state.velocity**2)
        v_after = state.velocity + impulse / self.mass
        ke_after = 0.5 * self.mass * np.sum(v_after**2)
        energy_loss = ke_before - ke_after
        
        return CollisionData(
            time=time,
            contact_points=[contact_point],
            normal=normal,
            penetration=penetration,
            impulse=impulse,
            energy_loss=max(0, energy_loss)
        )
    
    def _apply_collision_response(self, state: PhysicsState, 
                                   collision: CollisionData) -> PhysicsState:
        """Applique la réponse de collision à l'état"""
        new_state = state.copy()
        
        # Correction de position
        new_state.position[2] = max(self.scale, new_state.position[2])
        
        # Application de l'impulsion
        new_state.velocity += collision.impulse / self.mass
        
        # Modification de la rotation (moment angulaire)
        r = collision.contact_points[0] - state.position
        angular_impulse = np.cross(r, collision.impulse)
        new_state.angular_velocity += self.inertia_tensor_inv @ angular_impulse
        
        return new_state
    
    def _stabilization_phase(self, state: PhysicsState, trajectory: Trajectory,
                             surface_props: Dict) -> PhysicsState:
        """Phase de stabilisation finale"""
        damping = surface_props.get('damping_coefficient', 0.1)
        
        for _ in range(100):
            state.velocity *= (1 - damping * self.dt * 100)
            state.angular_velocity *= (1 - damping * self.dt * 100)
            
            if np.linalg.norm(state.velocity) < 0.001 and \
               np.linalg.norm(state.angular_velocity) < 0.01:
                break
        
        state.velocity = np.zeros(3)
        state.angular_velocity = np.zeros(3)
        
        return state
    
    def _determine_top_face(self, orientation: np.ndarray) -> int:
        """Détermine la face supérieure basée sur l'orientation"""
        # Vecteur "up" dans le repère du dé
        up_world = np.array([0, 0, 1])
        up_local = self._rotate_vector_by_quaternion_inverse(up_world, orientation)
        
        # Pour un d6, les normales des faces sont ±x, ±y, ±z
        if self.poly_type == PolyhedronType.D6:
            normals = [
                ([1, 0, 0], 1), ([-1, 0, 0], 6),
                ([0, 1, 0], 2), ([0, -1, 0], 5),
                ([0, 0, 1], 3), ([0, 0, -1], 4)
            ]
            
            best_face = 1
            best_dot = -2
            for normal, face in normals:
                dot = np.dot(up_local, normal)
                if dot > best_dot:
                    best_dot = dot
                    best_face = face
            
            return best_face
        
        # Pour les autres polyèdres, retourner une valeur basée sur le hash
        hash_val = int(hashlib.md5(orientation.tobytes()).hexdigest()[:8], 16)
        return (hash_val % self.poly_type.num_faces) + 1
    
    def _calculate_thermal_dissipation(self, trajectory: Trajectory) -> Dict:
        """Calcule la dissipation thermique"""
        total_loss = trajectory.total_energy_loss()
        
        if self.material.thermal:
            heat_capacity = self.mass * self.material.thermal.specific_heat
            temp_rise = total_loss / heat_capacity if heat_capacity > 0 else 0
        else:
            temp_rise = total_loss / (self.mass * 500)  # Capacité par défaut
        
        return {
            'total_energy_loss_J': total_loss,
            'temperature_rise_K': temp_rise,
            'thermal_conductivity': self.material.thermal.conductivity if self.material.thermal else 0
        }
    
    def _calculate_acoustic_signature(self, trajectory: Trajectory) -> Dict:
        """Calcule la signature acoustique"""
        if not trajectory.collisions:
            return {'peak_frequency': 0, 'total_energy': 0}
        
        # Fréquence caractéristique basée sur le matériau
        if self.material.acoustic:
            speed = self.material.acoustic.speed_of_sound
            freq = speed / (2 * self.scale)
        else:
            freq = 1000  # 1kHz par défaut
        
        # Énergie acoustique (fraction de l'énergie de collision)
        acoustic_fraction = 0.01  # 1% de l'énergie en son
        acoustic_energy = trajectory.total_energy_loss() * acoustic_fraction
        
        return {
            'peak_frequency_Hz': freq,
            'total_acoustic_energy_J': acoustic_energy,
            'num_impacts': len(trajectory.collisions)
        }
    
    def _compute_simulation_hash(self, trajectory: Trajectory) -> str:
        """Calcule un hash de la simulation"""
        data = []
        for state in trajectory.states[::10]:  # Échantillonnage
            data.extend(state.position.tolist())
            data.extend(state.orientation.tolist())
        
        data_bytes = np.array(data).tobytes()
        return hashlib.sha256(data_bytes).hexdigest()
    
    # === Utilitaires quaternion ===
    
    @staticmethod
    def _normalize_quaternion(q: np.ndarray) -> np.ndarray:
        """Normalise un quaternion"""
        norm = np.linalg.norm(q)
        return q / norm if norm > 1e-10 else np.array([1, 0, 0, 0])
    
    @staticmethod
    def _quaternion_multiply(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
        """Multiplie deux quaternions"""
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2
        
        return np.array([
            w1*w2 - x1*x2 - y1*y2 - z1*z2,
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2
        ])
    
    @staticmethod
    def _rotate_vector_by_quaternion(v: np.ndarray, q: np.ndarray) -> np.ndarray:
        """Tourne un vecteur par un quaternion"""
        q_conj = np.array([q[0], -q[1], -q[2], -q[3]])
        v_quat = np.array([0, v[0], v[1], v[2]])
        
        result = PolyhedronPhysicsEngine._quaternion_multiply(
            PolyhedronPhysicsEngine._quaternion_multiply(q, v_quat),
            q_conj
        )
        
        return result[1:4]
    
    @staticmethod
    def _rotate_vector_by_quaternion_inverse(v: np.ndarray, q: np.ndarray) -> np.ndarray:
        """Tourne un vecteur par l'inverse d'un quaternion"""
        q_inv = np.array([q[0], -q[1], -q[2], -q[3]])
        return PolyhedronPhysicsEngine._rotate_vector_by_quaternion(v, q_inv)
