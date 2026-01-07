#!/usr/bin/env python3
"""
Three.js Avatar Renderer - Generation de visualisations 3D WebGL uniques
Chaque avatar est mathematiquement unique base sur son DNA cryptographique
"""

import os
import json
import hashlib
import math
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional


class ThreeJSAvatarRenderer:
    """Generateur de visualisation Three.js pour avatars uniques"""
    
    GEOMETRY_GENERATORS = {
        "quantum_sphere": "_generate_quantum_sphere",
        "spinor_torus": "_generate_spinor_torus", 
        "bell_polyhedron": "_generate_bell_polyhedron",
        "clifford_lattice": "_generate_clifford_lattice",
        "entropy_fractal": "_generate_entropy_fractal",
        "7d_projection": "_generate_7d_projection",
        "hybrid_form": "_generate_hybrid_form",
        "nexus_crystal": "_generate_nexus_crystal",
    }
    
    def __init__(self, avatar_data: Dict):
        self.avatar_data = avatar_data
        self.avatar_id = avatar_data.get('avatar_id', 'unknown')
        self.geometry_type = avatar_data.get('geometry_type', 'quantum_sphere')
        self.rarity_tier = avatar_data.get('rarity_tier', 'common')
        self.rarity_score = avatar_data.get('rarity_score', 50)
        self.attributes = avatar_data.get('attributes', {})
        self.power = avatar_data.get('effective_power', 5000)
        
        # Generer les parametres uniques depuis le DNA
        self._generate_unique_params()
    
    def _generate_unique_params(self):
        """Genere TOUS les parametres uniques depuis l'avatar ID (DNA)"""
        # Hash principal pour la generation
        h = hashlib.sha512(self.avatar_id.encode()).hexdigest()
        
        # === COULEURS UNIQUES ===
        self.primary_color = self._get_rarity_color()
        self.secondary_color = f"#{h[0:6]}"
        self.tertiary_color = f"#{h[6:12]}"
        self.accent_color = f"#{h[12:18]}"
        self.glow_color = f"#{h[18:24]}"
        
        # === PARAMETRES GEOMETRIQUES UNIQUES ===
        # Extraire des valeurs numeriques du hash
        def hash_float(start: int, end: int, min_v: float = 0.0, max_v: float = 1.0) -> float:
            """Extrait un float du hash"""
            val = int(h[start:end], 16) / (16 ** (end - start))
            return min_v + val * (max_v - min_v)
        
        def hash_int(start: int, end: int, min_v: int, max_v: int) -> int:
            """Extrait un int du hash"""
            val = int(h[start:end], 16)
            return min_v + (val % (max_v - min_v + 1))
        
        # Forme principale
        self.scale_x = hash_float(24, 28, 0.7, 1.3)
        self.scale_y = hash_float(28, 32, 0.7, 1.3)
        self.scale_z = hash_float(32, 36, 0.7, 1.3)
        
        # Rotation initiale unique
        self.rot_x = hash_float(36, 40, 0, math.pi * 2)
        self.rot_y = hash_float(40, 44, 0, math.pi * 2)
        self.rot_z = hash_float(44, 48, 0, math.pi * 2)
        
        # Vitesse d'animation unique
        self.anim_speed = hash_float(48, 52, 0.3, 1.5)
        self.pulse_speed = hash_float(52, 56, 0.5, 2.0)
        self.orbit_speed = hash_float(56, 60, 0.2, 1.0)
        
        # Complexite geometrique (basee sur la rarete)
        rarity_mult = {"common": 1.0, "uncommon": 1.2, "rare": 1.4, "epic": 1.6, 
                       "legendary": 1.8, "mythical": 2.0, "primordial": 2.5}
        self.complexity = rarity_mult.get(self.rarity_tier.lower(), 1.0)
        
        # Nombre d'elements
        self.particle_count = hash_int(60, 64, 30, int(100 * self.complexity))
        self.ring_count = hash_int(64, 66, 2, int(5 * self.complexity))
        self.satellite_count = hash_int(66, 68, 4, int(12 * self.complexity))
        self.branch_depth = hash_int(68, 70, 3, int(7 * self.complexity))
        
        # Materiaux uniques
        self.metalness = hash_float(70, 74, 0.1, 0.9)
        self.roughness = hash_float(74, 78, 0.05, 0.5)
        self.clearcoat = hash_float(78, 82, 0.3, 1.0)
        self.emission_intensity = hash_float(82, 86, 0.1, 0.5)
        self.opacity = hash_float(86, 90, 0.6, 0.95)
        self.ior = hash_float(90, 94, 1.3, 2.5)  # Indice de refraction
        
        # Effets speciaux uniques
        self.has_aura = hash_int(94, 96, 0, 100) > 50
        self.has_particles = hash_int(96, 98, 0, 100) > 30
        self.has_trails = hash_int(98, 100, 0, 100) > 60
        self.distortion = hash_float(100, 104, 0, 0.3)
        
        # Forme de base unique (deformations)
        self.deform_a = hash_float(104, 108, -0.3, 0.3)
        self.deform_b = hash_float(108, 112, -0.3, 0.3)
        self.deform_freq = hash_float(112, 116, 1, 5)
        
        # Couleur emission calculee
        self.emission_color = self._lighten_color(self.primary_color, 0.4)
    
    def _get_rarity_color(self) -> str:
        colors = {
            "common": "#808080",
            "uncommon": "#00ff00",
            "rare": "#0080ff",
            "epic": "#a020f0",
            "legendary": "#ffd700",
            "mythical": "#ff00ff",
            "primordial": "#00ffff",
        }
        return colors.get(self.rarity_tier.lower(), "#ffffff")
    
    def _lighten_color(self, hex_color: str, factor: float) -> str:
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def generate_html(self, output_path: Optional[str] = None, auto_open: bool = True) -> str:
        """Genere le fichier HTML avec la visualisation Three.js unique"""
        geometry_code = self._generate_geometry_code()
        html_content = self._create_html_template(geometry_code)
        
        if output_path is None:
            output_dir = Path(__file__).parent.parent.parent / "avatars" / "viewers"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"avatar_{self.avatar_id[:16]}.html"
        else:
            output_path = Path(output_path)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        if auto_open:
            webbrowser.open(f'file://{output_path.absolute()}')
        
        return str(output_path)
    
    def _generate_geometry_code(self) -> str:
        generator_name = self.GEOMETRY_GENERATORS.get(self.geometry_type, "_generate_quantum_sphere")
        generator = getattr(self, generator_name, self._generate_quantum_sphere)
        return generator()
    
    def _get_unique_material_code(self, name: str = "mainMat", color_var: str = "primary") -> str:
        """Genere le code pour un materiau unique"""
        color = getattr(self, f"{color_var}_color", self.primary_color)
        return f'''
            const {name} = new THREE.MeshPhysicalMaterial({{
                color: '{color}',
                metalness: {self.metalness:.3f},
                roughness: {self.roughness:.3f},
                transparent: true,
                opacity: {self.opacity:.3f},
                emissive: '{self.emission_color}',
                emissiveIntensity: {self.emission_intensity:.3f},
                clearcoat: {self.clearcoat:.3f},
                clearcoatRoughness: {self.roughness * 0.5:.3f},
                reflectivity: {1.0 - self.roughness:.3f},
                ior: {self.ior:.3f}
            }});
        '''
    
    def _get_aura_code(self) -> str:
        """Genere le code pour l'aura lumineuse"""
        if not self.has_aura:
            return ""
        
        pulse_speed = self.pulse_speed
        emission = self.emission_intensity
        
        # Shader sans f-string pour eviter les conflits
        shader_code = '''
            // Aura lumineuse unique
            const auraGeom = new THREE.SphereGeometry(2.5, 32, 32);
            const auraMat = new THREE.ShaderMaterial({
                uniforms: {
                    time: { value: 0 },
                    color1: { value: new THREE.Color('%s') },
                    color2: { value: new THREE.Color('%s') },
                    intensity: { value: %.3f }
                },
                vertexShader: `
                    varying vec3 vNormal;
                    varying vec3 vPosition;
                    void main() {
                        vNormal = normalize(normalMatrix * normal);
                        vPosition = position;
                        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                    }
                `,
                fragmentShader: `
                    uniform float time;
                    uniform vec3 color1;
                    uniform vec3 color2;
                    uniform float intensity;
                    varying vec3 vNormal;
                    varying vec3 vPosition;
                    void main() {
                        float pulse = sin(time * %.2f) * 0.5 + 0.5;
                        float fresnel = pow(1.0 - abs(dot(vNormal, vec3(0.0, 0.0, 1.0))), 3.0);
                        vec3 color = mix(color1, color2, pulse);
                        float alpha = fresnel * intensity * (0.5 + pulse * 0.5);
                        gl_FragColor = vec4(color, alpha * 0.3);
                    }
                `,
                transparent: true,
                blending: THREE.AdditiveBlending,
                side: THREE.BackSide,
                depthWrite: false
            });
            const aura = new THREE.Mesh(auraGeom, auraMat);
            scene.add(aura);
            animationCallbacks.push((time) => {
                auraMat.uniforms.time.value = time;
                aura.rotation.y = time * 0.1;
            });
        ''' % (self.primary_color, self.glow_color, emission, pulse_speed)
        
        return shader_code
    
    def _get_particles_code(self) -> str:
        """Genere le code pour les particules orbitales"""
        if not self.has_particles:
            return ""
        
        # Utiliser % formatting pour eviter conflits avec accolades JS
        code = '''
            // Particules orbitales uniques
            const particleCount = %d;
            const particleGeom = new THREE.BufferGeometry();
            const positions = new Float32Array(particleCount * 3);
            const colors = new Float32Array(particleCount * 3);
            const sizes = new Float32Array(particleCount);
            const orbits = new Float32Array(particleCount * 3);
            
            for (let i = 0; i < particleCount; i++) {
                const theta = Math.random() * Math.PI * 2;
                const phi = Math.acos(2 * Math.random() - 1);
                const r = 1.5 + Math.random() * 1.0;
                
                positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
                positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
                positions[i * 3 + 2] = r * Math.cos(phi);
                
                const colorChoice = Math.random();
                let color;
                if (colorChoice < 0.33) color = new THREE.Color('%s');
                else if (colorChoice < 0.66) color = new THREE.Color('%s');
                else color = new THREE.Color('%s');
                
                colors[i * 3] = color.r;
                colors[i * 3 + 1] = color.g;
                colors[i * 3 + 2] = color.b;
                
                sizes[i] = 0.02 + Math.random() * 0.06;
                orbits[i * 3] = r;
                orbits[i * 3 + 1] = 0.2 + Math.random() * %.2f;
                orbits[i * 3 + 2] = Math.random() * Math.PI * 2;
            }
            
            particleGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            particleGeom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
            particleGeom.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
            
            const particleMat = new THREE.PointsMaterial({
                size: 0.08,
                vertexColors: true,
                transparent: true,
                opacity: 0.9,
                blending: THREE.AdditiveBlending,
                depthWrite: false
            });
            const particles = new THREE.Points(particleGeom, particleMat);
            scene.add(particles);
            
            animationCallbacks.push((time) => {
                const pos = particles.geometry.attributes.position.array;
                for (let i = 0; i < particleCount; i++) {
                    const r = orbits[i * 3];
                    const speed = orbits[i * 3 + 1];
                    const phase = orbits[i * 3 + 2];
                    const angle = time * speed + phase;
                    
                    pos[i * 3] = r * Math.cos(angle) * Math.cos(phase);
                    pos[i * 3 + 1] = r * Math.sin(angle * 0.7) * 0.5;
                    pos[i * 3 + 2] = r * Math.sin(angle) * Math.sin(phase);
                }
                particles.geometry.attributes.position.needsUpdate = true;
                particles.rotation.y = time * 0.1;
            });
        ''' % (self.particle_count, self.secondary_color, self.tertiary_color, 
               self.accent_color, self.orbit_speed)
        
        return code
    
    def _generate_quantum_sphere(self) -> str:
        """Sphere quantique avec orbitales uniques"""
        return f'''
            // === QUANTUM SPHERE UNIQUE ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {self.scale_y:.3f}, {self.scale_z:.3f});
            mainGroup.rotation.set({self.rot_x:.3f}, {self.rot_y:.3f}, {self.rot_z:.3f});
            scene.add(mainGroup);
            
            // Sphere principale avec deformation unique
            const sphereGeom = new THREE.SphereGeometry(1, 64, 64);
            const posAttr = sphereGeom.attributes.position;
            for (let i = 0; i < posAttr.count; i++) {{
                const x = posAttr.getX(i);
                const y = posAttr.getY(i);
                const z = posAttr.getZ(i);
                const dist = Math.sqrt(x*x + y*y + z*z);
                const deform = 1 + {self.deform_a:.3f} * Math.sin(y * {self.deform_freq:.2f}) 
                             + {self.deform_b:.3f} * Math.cos(x * z * {self.deform_freq:.2f});
                posAttr.setXYZ(i, x * deform, y * deform, z * deform);
            }}
            sphereGeom.computeVertexNormals();
            
            {self._get_unique_material_code("sphereMat", "primary")}
            const sphere = new THREE.Mesh(sphereGeom, sphereMat);
            mainGroup.add(sphere);
            
            // Anneaux orbitaux uniques
            for (let i = 0; i < {self.ring_count}; i++) {{
                const ringR = 1.2 + i * 0.25;
                const ringGeom = new THREE.TorusGeometry(ringR, 0.015 + i * 0.005, 16, 100);
                const ringMat = new THREE.MeshBasicMaterial({{
                    color: i % 2 === 0 ? '{self.secondary_color}' : '{self.tertiary_color}',
                    transparent: true,
                    opacity: 0.7 - i * 0.1
                }});
                const ring = new THREE.Mesh(ringGeom, ringMat);
                ring.rotation.x = Math.PI / 2 + i * {self.deform_a:.3f};
                ring.rotation.y = i * {self.deform_b:.3f};
                mainGroup.add(ring);
                
                animationCallbacks.push((time) => {{
                    ring.rotation.z = time * {self.anim_speed:.3f} * (0.5 + i * 0.2);
                }});
            }}
            
            // Noyau lumineux pulse
            const coreGeom = new THREE.IcosahedronGeometry(0.15, 2);
            const coreMat = new THREE.MeshBasicMaterial({{
                color: '{self.glow_color}',
                transparent: true,
                opacity: 0.95
            }});
            const core = new THREE.Mesh(coreGeom, coreMat);
            mainGroup.add(core);
            
            const coreLight = new THREE.PointLight('{self.primary_color}', 2, 5);
            mainGroup.add(coreLight);
            
            animationCallbacks.push((time) => {{
                const pulse = 1 + Math.sin(time * {self.pulse_speed:.2f}) * 0.2;
                core.scale.setScalar(pulse);
                coreLight.intensity = 1.5 + Math.sin(time * {self.pulse_speed:.2f}) * 0.5;
                sphere.rotation.y = time * {self.anim_speed:.3f} * 0.3;
            }});
            
            {self._get_aura_code()}
            {self._get_particles_code()}
        '''
    
    def _generate_spinor_torus(self) -> str:
        """Tore spinoriel avec flux d'energie uniques"""
        return f'''
            // === SPINOR TORUS UNIQUE ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {self.scale_y:.3f}, {self.scale_z:.3f});
            scene.add(mainGroup);
            
            // Tore principal deforme
            const torusGeom = new THREE.TorusGeometry(1, 0.35, 32, 100);
            const torusPos = torusGeom.attributes.position;
            for (let i = 0; i < torusPos.count; i++) {{
                const x = torusPos.getX(i);
                const y = torusPos.getY(i);
                const z = torusPos.getZ(i);
                const angle = Math.atan2(z, x);
                const wave = {self.deform_a:.3f} * Math.sin(angle * {self.deform_freq:.1f});
                torusPos.setXYZ(i, x * (1 + wave), y, z * (1 + wave));
            }}
            torusGeom.computeVertexNormals();
            
            {self._get_unique_material_code("torusMat", "primary")}
            const torus = new THREE.Mesh(torusGeom, torusMat);
            mainGroup.add(torus);
            
            // Tores internes (flux spinoriel)
            for (let i = 0; i < 3; i++) {{
                const innerGeom = new THREE.TorusGeometry(0.85 - i * 0.15, 0.04, 16, 50);
                const innerMat = new THREE.MeshBasicMaterial({{
                    color: ['{self.secondary_color}', '{self.tertiary_color}', '{self.accent_color}'][i],
                    transparent: true,
                    opacity: 0.7 - i * 0.15
                }});
                const inner = new THREE.Mesh(innerGeom, innerMat);
                inner.rotation.x = i * 0.3 + {self.rot_x:.3f};
                mainGroup.add(inner);
                
                animationCallbacks.push((time) => {{
                    inner.rotation.z = time * {self.anim_speed:.3f} * (1 + i * 0.5);
                }});
            }}
            
            // Lignes de flux energetiques
            const fluxCount = {self.satellite_count};
            for (let i = 0; i < fluxCount; i++) {{
                const angle = (i / fluxCount) * Math.PI * 2;
                const curve = new THREE.CatmullRomCurve3([
                    new THREE.Vector3(Math.cos(angle) * 1.4, 0, Math.sin(angle) * 1.4),
                    new THREE.Vector3(Math.cos(angle) * 0.7, 0.4 + {self.deform_b:.3f}, Math.sin(angle) * 0.7),
                    new THREE.Vector3(Math.cos(angle + 0.3) * 1.4, 0, Math.sin(angle + 0.3) * 1.4)
                ]);
                const tubeGeom = new THREE.TubeGeometry(curve, 20, 0.015, 8, false);
                const tubeMat = new THREE.MeshBasicMaterial({{
                    color: '{self.accent_color}',
                    transparent: true,
                    opacity: 0.5
                }});
                const tube = new THREE.Mesh(tubeGeom, tubeMat);
                mainGroup.add(tube);
            }}
            
            // Points de flux
            for (let i = 0; i < 8; i++) {{
                const a = (i / 8) * Math.PI * 2;
                const pGeom = new THREE.SphereGeometry(0.05, 16, 16);
                const pMat = new THREE.MeshBasicMaterial({{ color: '{self.glow_color}' }});
                const p = new THREE.Mesh(pGeom, pMat);
                p.position.set(Math.cos(a) * 1.35, 0, Math.sin(a) * 1.35);
                mainGroup.add(p);
                
                animationCallbacks.push((time) => {{
                    const newA = a + time * {self.orbit_speed:.3f};
                    p.position.set(Math.cos(newA) * 1.35, Math.sin(time * 2 + i) * 0.1, Math.sin(newA) * 1.35);
                    p.scale.setScalar(1 + Math.sin(time * 3 + i) * 0.3);
                }});
            }}
            
            animationCallbacks.push((time) => {{
                torus.rotation.x = Math.sin(time * {self.anim_speed:.3f} * 0.5) * 0.2;
                torus.rotation.y = time * {self.anim_speed:.3f} * 0.2;
            }});
            
            {self._get_aura_code()}
            {self._get_particles_code()}
        '''
    
    def _generate_nexus_crystal(self) -> str:
        """Cristal nexus avec facettes uniques"""
        return f'''
            // === NEXUS CRYSTAL UNIQUE ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {self.scale_y:.3f * 1.5:.3f}, {self.scale_z:.3f});
            scene.add(mainGroup);
            
            // Cristal principal (octaedre deforme)
            const crystalGeom = new THREE.OctahedronGeometry(1, 0);
            const crystalPos = crystalGeom.attributes.position;
            for (let i = 0; i < crystalPos.count; i++) {{
                const y = crystalPos.getY(i);
                const stretch = 1 + {self.deform_a:.3f} * Math.abs(y);
                crystalPos.setY(i, y * (1.5 + stretch));
            }}
            crystalGeom.computeVertexNormals();
            
            const crystalMat = new THREE.MeshPhysicalMaterial({{
                color: '{self.primary_color}',
                metalness: 0.05,
                roughness: 0.02,
                transparent: true,
                opacity: 0.8,
                emissive: '{self.emission_color}',
                emissiveIntensity: {self.emission_intensity * 1.5:.3f},
                clearcoat: 1.0,
                clearcoatRoughness: 0.0,
                reflectivity: 1.0,
                ior: {self.ior:.3f},
                transmission: 0.3
            }});
            const crystal = new THREE.Mesh(crystalGeom, crystalMat);
            mainGroup.add(crystal);
            
            // Cristaux satellites uniques
            for (let i = 0; i < {self.satellite_count}; i++) {{
                const angle = (i / {self.satellite_count}) * Math.PI * 2;
                const smallGeom = new THREE.OctahedronGeometry(0.2 + Math.random() * 0.15, 0);
                smallGeom.scale(1, 1.3 + {self.deform_b:.3f}, 1);
                
                const smallMat = new THREE.MeshPhysicalMaterial({{
                    color: i % 2 === 0 ? '{self.secondary_color}' : '{self.tertiary_color}',
                    metalness: 0.1,
                    roughness: 0.1,
                    transparent: true,
                    opacity: 0.75,
                    emissive: i % 2 === 0 ? '{self.secondary_color}' : '{self.tertiary_color}',
                    emissiveIntensity: 0.3
                }});
                const small = new THREE.Mesh(smallGeom, smallMat);
                small.position.set(
                    Math.cos(angle) * 1.4,
                    Math.sin(angle * 2 + {self.rot_x:.3f}) * 0.3,
                    Math.sin(angle) * 1.4
                );
                small.rotation.set(angle, angle * 0.5, 0);
                mainGroup.add(small);
                
                animationCallbacks.push((time) => {{
                    small.position.y = Math.sin(time * {self.pulse_speed:.2f} + i) * 0.25;
                    small.rotation.y = time * {self.anim_speed:.3f} * 0.5;
                    small.rotation.z = time * {self.anim_speed:.3f} * 0.3;
                }});
            }}
            
            // Rayons de lumiere internes
            for (let i = 0; i < 6; i++) {{
                const rayGeom = new THREE.CylinderGeometry(0.008, 0.008, 2.5, 8);
                const rayMat = new THREE.MeshBasicMaterial({{
                    color: '{self.glow_color}',
                    transparent: true,
                    opacity: 0.4
                }});
                const ray = new THREE.Mesh(rayGeom, rayMat);
                ray.rotation.z = (i / 6) * Math.PI;
                ray.rotation.x = Math.PI / 2;
                mainGroup.add(ray);
            }}
            
            // Lumiere centrale
            const crystalLight = new THREE.PointLight('{self.primary_color}', 3, 8);
            mainGroup.add(crystalLight);
            
            animationCallbacks.push((time) => {{
                crystal.rotation.y = time * {self.anim_speed:.3f} * 0.3;
                crystal.position.y = Math.sin(time * {self.pulse_speed:.2f}) * 0.08;
                crystalLight.intensity = 2.5 + Math.sin(time * {self.pulse_speed:.2f}) * 0.5;
            }});
            
            {self._get_aura_code()}
            {self._get_particles_code()}
        '''
    
    def _generate_bell_polyhedron(self) -> str:
        """Polyedre de Bell avec connexions quantiques uniques"""
        return f'''
            // === BELL POLYHEDRON UNIQUE ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {self.scale_y:.3f}, {self.scale_z:.3f});
            scene.add(mainGroup);
            
            // Icosaedre principal deforme
            const icoGeom = new THREE.IcosahedronGeometry(1, 1);
            const icoPos = icoGeom.attributes.position;
            for (let i = 0; i < icoPos.count; i++) {{
                const x = icoPos.getX(i);
                const y = icoPos.getY(i);
                const z = icoPos.getZ(i);
                const noise = {self.deform_a:.3f} * Math.sin(x * y * {self.deform_freq:.2f}) 
                            + {self.deform_b:.3f} * Math.cos(y * z * {self.deform_freq:.2f});
                const factor = 1 + noise;
                icoPos.setXYZ(i, x * factor, y * factor, z * factor);
            }}
            icoGeom.computeVertexNormals();
            
            {self._get_unique_material_code("icoMat", "primary")}
            const ico = new THREE.Mesh(icoGeom, icoMat);
            mainGroup.add(ico);
            
            // Wireframe
            const wireGeom = new THREE.IcosahedronGeometry(1.03, 1);
            const wireMat = new THREE.MeshBasicMaterial({{
                color: '{self.secondary_color}',
                wireframe: true,
                transparent: true,
                opacity: 0.6
            }});
            const wire = new THREE.Mesh(wireGeom, wireMat);
            mainGroup.add(wire);
            
            // Sommets lumineux
            const vertices = [];
            for (let i = 0; i < 12; i++) {{
                const phi = Math.acos(-1 + (2 * i) / 11);
                const theta = Math.sqrt(11 * Math.PI) * phi;
                const sphereGeom = new THREE.SphereGeometry(0.06 + {self.deform_a:.3f} * 0.02, 16, 16);
                const sphereMat = new THREE.MeshBasicMaterial({{
                    color: ['{self.secondary_color}', '{self.tertiary_color}', '{self.accent_color}'][i % 3]
                }});
                const sphere = new THREE.Mesh(sphereGeom, sphereMat);
                sphere.position.set(
                    1.1 * Math.cos(theta) * Math.sin(phi),
                    1.1 * Math.sin(theta) * Math.sin(phi),
                    1.1 * Math.cos(phi)
                );
                mainGroup.add(sphere);
                vertices.push(sphere);
            }}
            
            // Connexions quantiques (lignes entre sommets)
            const lineMat = new THREE.LineBasicMaterial({{
                color: '{self.glow_color}',
                transparent: true,
                opacity: 0.4
            }});
            
            for (let i = 0; i < vertices.length; i++) {{
                for (let j = i + 1; j < vertices.length; j++) {{
                    if ((i + j) % 3 === 0) {{
                        const points = [
                            vertices[i].position,
                            new THREE.Vector3(0, 0, 0),
                            vertices[j].position
                        ];
                        const lineGeom = new THREE.BufferGeometry().setFromPoints(points);
                        const line = new THREE.Line(lineGeom, lineMat);
                        mainGroup.add(line);
                    }}
                }}
            }}
            
            animationCallbacks.push((time) => {{
                ico.rotation.x = time * {self.anim_speed:.3f} * 0.2;
                ico.rotation.y = time * {self.anim_speed:.3f} * 0.3;
                wire.rotation.x = time * {self.anim_speed:.3f} * 0.2;
                wire.rotation.y = time * {self.anim_speed:.3f} * 0.3;
                
                vertices.forEach((s, i) => {{
                    s.scale.setScalar(1 + Math.sin(time * {self.pulse_speed:.2f} + i * 0.5) * 0.3);
                }});
            }});
            
            {self._get_aura_code()}
            {self._get_particles_code()}
        '''
    
    def _generate_clifford_lattice(self) -> str:
        """Lattice de Clifford 3D unique"""
        grid_size = min(5, int(3 + self.complexity))
        return f'''
            // === CLIFFORD LATTICE UNIQUE ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {self.scale_y:.3f}, {self.scale_z:.3f});
            scene.add(mainGroup);
            
            const gridSize = {grid_size};
            const spacing = 0.45;
            const nodes = [];
            
            for (let x = -gridSize/2; x <= gridSize/2; x++) {{
                for (let y = -gridSize/2; y <= gridSize/2; y++) {{
                    for (let z = -gridSize/2; z <= gridSize/2; z++) {{
                        const dist = Math.sqrt(x*x + y*y + z*z);
                        if (dist < gridSize/2 + 0.5) {{
                            // Forme unique par noeud
                            const nodeType = Math.abs(x + y + z) % 3;
                            let nodeGeom;
                            if (nodeType === 0) nodeGeom = new THREE.BoxGeometry(0.08, 0.08, 0.08);
                            else if (nodeType === 1) nodeGeom = new THREE.OctahedronGeometry(0.06, 0);
                            else nodeGeom = new THREE.TetrahedronGeometry(0.07, 0);
                            
                            const colorIndex = (Math.abs(x) + Math.abs(y) + Math.abs(z)) % 3;
                            const colors = ['{self.primary_color}', '{self.secondary_color}', '{self.tertiary_color}'];
                            
                            const nodeMat = new THREE.MeshPhysicalMaterial({{
                                color: colors[colorIndex],
                                metalness: {self.metalness:.3f},
                                roughness: {self.roughness:.3f},
                                emissive: colors[colorIndex],
                                emissiveIntensity: {self.emission_intensity:.3f}
                            }});
                            const node = new THREE.Mesh(nodeGeom, nodeMat);
                            node.position.set(
                                x * spacing + {self.deform_a:.3f} * Math.sin(y),
                                y * spacing + {self.deform_b:.3f} * Math.cos(z),
                                z * spacing
                            );
                            mainGroup.add(node);
                            nodes.push({{mesh: node, x, y, z, basePos: node.position.clone()}});
                        }}
                    }}
                }}
            }}
            
            // Connexions entre noeuds adjacents
            const lineMat = new THREE.LineBasicMaterial({{
                color: '{self.accent_color}',
                transparent: true,
                opacity: 0.35
            }});
            
            nodes.forEach((node, i) => {{
                nodes.forEach((other, j) => {{
                    if (i < j) {{
                        const dx = Math.abs(node.x - other.x);
                        const dy = Math.abs(node.y - other.y);
                        const dz = Math.abs(node.z - other.z);
                        if (dx + dy + dz === 1) {{
                            const points = [node.mesh.position.clone(), other.mesh.position.clone()];
                            const lineGeom = new THREE.BufferGeometry().setFromPoints(points);
                            const line = new THREE.Line(lineGeom, lineMat);
                            mainGroup.add(line);
                        }}
                    }}
                }});
            }});
            
            // Cube englobant
            const cubeGeom = new THREE.BoxGeometry(gridSize * spacing * 1.2, gridSize * spacing * 1.2, gridSize * spacing * 1.2);
            const cubeMat = new THREE.MeshBasicMaterial({{
                color: '{self.glow_color}',
                wireframe: true,
                transparent: true,
                opacity: 0.2
            }});
            const cube = new THREE.Mesh(cubeGeom, cubeMat);
            mainGroup.add(cube);
            
            animationCallbacks.push((time) => {{
                nodes.forEach((node, i) => {{
                    const pulse = Math.sin(time * {self.pulse_speed:.2f} + i * 0.1);
                    node.mesh.scale.setScalar(0.8 + pulse * 0.3);
                    node.mesh.position.y = node.basePos.y + Math.sin(time * 2 + i * 0.2) * 0.03;
                }});
                mainGroup.rotation.y = time * {self.anim_speed:.3f} * 0.1;
                cube.rotation.x = time * 0.05;
            }});
            
            {self._get_particles_code()}
        '''
    
    def _generate_entropy_fractal(self) -> str:
        """Fractale entropique unique"""
        return f'''
            // === ENTROPY FRACTAL UNIQUE ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {self.scale_y:.3f}, {self.scale_z:.3f});
            scene.add(mainGroup);
            
            const colors = ['{self.primary_color}', '{self.secondary_color}', '{self.tertiary_color}', '{self.accent_color}'];
            const leaves = [];
            
            function createBranch(startPos, direction, length, depth, colorIndex) {{
                if (depth <= 0 || length < 0.04) {{
                    // Feuille/Noeud terminal
                    const leafGeom = new THREE.SphereGeometry(0.04 + depth * 0.01, 12, 12);
                    const leafMat = new THREE.MeshBasicMaterial({{
                        color: colors[(colorIndex + depth) % 4],
                        transparent: true,
                        opacity: 0.85
                    }});
                    const leaf = new THREE.Mesh(leafGeom, leafMat);
                    leaf.position.copy(startPos);
                    mainGroup.add(leaf);
                    leaves.push(leaf);
                    return;
                }}
                
                const endPos = startPos.clone().add(direction.clone().multiplyScalar(length));
                
                // Branche
                const curve = new THREE.LineCurve3(startPos, endPos);
                const tubeGeom = new THREE.TubeGeometry(curve, 8, length * 0.06, 6, false);
                const tubeMat = new THREE.MeshPhysicalMaterial({{
                    color: colors[colorIndex % 4],
                    metalness: {self.metalness * 0.5:.3f},
                    roughness: {self.roughness:.3f},
                    emissive: colors[colorIndex % 4],
                    emissiveIntensity: {self.emission_intensity * 0.5:.3f}
                }});
                const tube = new THREE.Mesh(tubeGeom, tubeMat);
                mainGroup.add(tube);
                
                // Sous-branches
                const branchAngles = [
                    {{ x: -{25 + self.deform_a * 10:.1f}, y: 0 }},
                    {{ x: {25 + self.deform_b * 10:.1f}, y: 0 }},
                    {{ x: 0, y: -{20 + self.deform_a * 8:.1f} }},
                ];
                
                branchAngles.forEach((angles, i) => {{
                    if (Math.random() > 0.2) {{
                        const newDir = direction.clone();
                        newDir.applyAxisAngle(new THREE.Vector3(1, 0, 0), angles.x * Math.PI / 180);
                        newDir.applyAxisAngle(new THREE.Vector3(0, 0, 1), angles.y * Math.PI / 180);
                        newDir.applyAxisAngle(new THREE.Vector3(0, 1, 0), (i - 1) * Math.PI * 0.4);
                        createBranch(endPos.clone(), newDir, length * 0.72, depth - 1, colorIndex + 1);
                    }}
                }});
            }}
            
            // Creer plusieurs arbres
            createBranch(new THREE.Vector3(0, -1.2, 0), new THREE.Vector3(0, 1, 0), 0.5, {self.branch_depth}, 0);
            
            for (let i = 0; i < 3; i++) {{
                const angle = (i / 3) * Math.PI * 2 + {self.rot_z:.3f};
                const startPos = new THREE.Vector3(Math.cos(angle) * 0.3, -1.1, Math.sin(angle) * 0.3);
                const dir = new THREE.Vector3(Math.cos(angle) * 0.4, 0.9, Math.sin(angle) * 0.4).normalize();
                createBranch(startPos, dir, 0.35, {self.branch_depth} - 1, i + 1);
            }}
            
            animationCallbacks.push((time) => {{
                leaves.forEach((leaf, i) => {{
                    leaf.scale.setScalar(1 + Math.sin(time * {self.pulse_speed:.2f} + i * 0.3) * 0.25);
                }});
                mainGroup.rotation.y = Math.sin(time * {self.anim_speed:.3f} * 0.3) * 0.1;
            }});
            
            {self._get_particles_code()}
        '''
    
    def _generate_7d_projection(self) -> str:
        """Projection 7D unique"""
        return f'''
            // === 7D PROJECTION UNIQUE ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {self.scale_y:.3f}, {self.scale_z:.3f});
            scene.add(mainGroup);
            
            const dimCount = 7;
            const layers = [];
            
            for (let d = 0; d < dimCount; d++) {{
                const layerGroup = new THREE.Group();
                const hue = d / dimCount;
                const color = new THREE.Color().setHSL(hue, 0.8, 0.5);
                
                // Heptagone unique par dimension
                const points = [];
                const r = 1.3 - d * 0.12 + {self.deform_a:.3f} * Math.sin(d);
                for (let i = 0; i < 7; i++) {{
                    const angle = (i / 7) * Math.PI * 2 + d * {self.deform_b:.3f};
                    points.push(new THREE.Vector3(
                        Math.cos(angle) * r,
                        Math.sin(angle) * r,
                        0
                    ));
                }}
                points.push(points[0].clone());
                
                const lineGeom = new THREE.BufferGeometry().setFromPoints(points);
                const lineMat = new THREE.LineBasicMaterial({{
                    color: color,
                    transparent: true,
                    opacity: 0.85 - d * 0.08
                }});
                const line = new THREE.Line(lineGeom, lineMat);
                layerGroup.add(line);
                
                // Noeuds aux sommets
                for (let i = 0; i < 7; i++) {{
                    const nodeGeom = new THREE.IcosahedronGeometry(0.06 - d * 0.005, 0);
                    const nodeMat = new THREE.MeshBasicMaterial({{ color: color }});
                    const node = new THREE.Mesh(nodeGeom, nodeMat);
                    node.position.copy(points[i]);
                    layerGroup.add(node);
                }}
                
                // Lignes vers le centre
                for (let i = 0; i < 7; i++) {{
                    const centerPoints = [points[i], new THREE.Vector3(0, 0, 0)];
                    const centerGeom = new THREE.BufferGeometry().setFromPoints(centerPoints);
                    const centerMat = new THREE.LineBasicMaterial({{
                        color: '{self.glow_color}',
                        transparent: true,
                        opacity: 0.25
                    }});
                    layerGroup.add(new THREE.Line(centerGeom, centerMat));
                }}
                
                layerGroup.position.z = d * 0.18 - 0.6;
                layerGroup.rotation.z = d * 0.12 + {self.rot_z:.3f};
                mainGroup.add(layerGroup);
                layers.push(layerGroup);
                
                animationCallbacks.push((time) => {{
                    layerGroup.rotation.z = d * 0.12 + {self.rot_z:.3f} + time * {self.anim_speed:.3f} * (0.15 + d * 0.05);
                    layerGroup.position.z = (d * 0.18 - 0.6) + Math.sin(time * {self.pulse_speed:.2f} + d * 0.5) * 0.08;
                }});
            }}
            
            // Centre 7D
            const centerGeom = new THREE.DodecahedronGeometry(0.12, 0);
            const centerMat = new THREE.MeshPhysicalMaterial({{
                color: '{self.primary_color}',
                emissive: '{self.primary_color}',
                emissiveIntensity: {self.emission_intensity * 2:.3f},
                metalness: {self.metalness:.3f},
                roughness: {self.roughness:.3f}
            }});
            const center = new THREE.Mesh(centerGeom, centerMat);
            mainGroup.add(center);
            
            const centerLight = new THREE.PointLight('{self.primary_color}', 2, 4);
            mainGroup.add(centerLight);
            
            animationCallbacks.push((time) => {{
                center.rotation.x = time * {self.anim_speed:.3f} * 0.5;
                center.rotation.y = time * {self.anim_speed:.3f} * 0.7;
                center.scale.setScalar(1 + Math.sin(time * {self.pulse_speed:.2f}) * 0.15);
            }});
            
            {self._get_aura_code()}
            {self._get_particles_code()}
        '''
    
    def _generate_hybrid_form(self) -> str:
        """Forme hybride complexe unique"""
        return f'''
            // === HYBRID FORM UNIQUE ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {self.scale_y:.3f}, {self.scale_z:.3f});
            scene.add(mainGroup);
            
            // Forme centrale (dodecaedre deforme)
            const coreGeom = new THREE.DodecahedronGeometry(0.55, 1);
            const corePos = coreGeom.attributes.position;
            for (let i = 0; i < corePos.count; i++) {{
                const x = corePos.getX(i);
                const y = corePos.getY(i);
                const z = corePos.getZ(i);
                const noise = {self.deform_a:.3f} * Math.sin(x * y * {self.deform_freq:.2f});
                corePos.setXYZ(i, x * (1 + noise), y * (1 + noise * 0.5), z * (1 + noise));
            }}
            coreGeom.computeVertexNormals();
            
            {self._get_unique_material_code("coreMat", "primary")}
            const core = new THREE.Mesh(coreGeom, coreMat);
            mainGroup.add(core);
            
            // Anneaux multiples uniques
            for (let i = 0; i < {self.ring_count}; i++) {{
                const ringR = 0.9 + i * 0.22;
                const ringGeom = new THREE.TorusGeometry(ringR, 0.025 + i * 0.005, 16, 80);
                const ringMat = new THREE.MeshBasicMaterial({{
                    color: ['{self.secondary_color}', '{self.tertiary_color}', '{self.accent_color}', '{self.glow_color}'][i % 4],
                    transparent: true,
                    opacity: 0.65 - i * 0.1
                }});
                const ring = new THREE.Mesh(ringGeom, ringMat);
                ring.rotation.x = i * Math.PI / {self.ring_count} + {self.rot_x:.3f};
                ring.rotation.y = i * 0.3 + {self.rot_y:.3f};
                mainGroup.add(ring);
                
                animationCallbacks.push((time) => {{
                    ring.rotation.z = time * {self.anim_speed:.3f} * (0.25 + i * 0.1);
                }});
            }}
            
            // Satellites uniques
            const satCount = {self.satellite_count};
            const satellites = [];
            for (let i = 0; i < satCount; i++) {{
                const satType = i % 3;
                let satGeom;
                if (satType === 0) satGeom = new THREE.TetrahedronGeometry(0.12, 0);
                else if (satType === 1) satGeom = new THREE.OctahedronGeometry(0.1, 0);
                else satGeom = new THREE.IcosahedronGeometry(0.09, 0);
                
                const satMat = new THREE.MeshPhysicalMaterial({{
                    color: ['{self.secondary_color}', '{self.tertiary_color}', '{self.accent_color}'][i % 3],
                    metalness: {self.metalness:.3f},
                    roughness: {self.roughness:.3f},
                    emissive: ['{self.secondary_color}', '{self.tertiary_color}', '{self.accent_color}'][i % 3],
                    emissiveIntensity: {self.emission_intensity:.3f}
                }});
                const sat = new THREE.Mesh(satGeom, satMat);
                
                const angle = (i / satCount) * Math.PI * 2;
                const orbitR = 1.4 + (i % 3) * 0.15;
                sat.userData = {{ angle, orbitR, speed: {self.orbit_speed:.3f} * (0.8 + (i % 4) * 0.15) }};
                sat.position.set(Math.cos(angle) * orbitR, 0, Math.sin(angle) * orbitR);
                mainGroup.add(sat);
                satellites.push(sat);
                
                // Lien vers le centre
                const linkMat = new THREE.LineBasicMaterial({{
                    color: '{self.glow_color}',
                    transparent: true,
                    opacity: 0.25
                }});
                const linkGeom = new THREE.BufferGeometry().setFromPoints([
                    sat.position.clone(), new THREE.Vector3(0, 0, 0)
                ]);
                const link = new THREE.Line(linkGeom, linkMat);
                link.userData.satellite = sat;
                mainGroup.add(link);
            }}
            
            animationCallbacks.push((time) => {{
                core.rotation.x = time * {self.anim_speed:.3f} * 0.15;
                core.rotation.y = time * {self.anim_speed:.3f} * 0.25;
                core.scale.setScalar(1 + Math.sin(time * {self.pulse_speed:.2f}) * 0.04);
                
                satellites.forEach((sat, i) => {{
                    const d = sat.userData;
                    const newAngle = d.angle + time * d.speed;
                    sat.position.set(
                        Math.cos(newAngle) * d.orbitR,
                        Math.sin(time * {self.pulse_speed:.2f} * 2 + i) * 0.2,
                        Math.sin(newAngle) * d.orbitR
                    );
                    sat.rotation.x = time * 1.5;
                    sat.rotation.y = time * 2;
                }});
            }});
            
            {self._get_aura_code()}
            {self._get_particles_code()}
        '''
    
    def _create_html_template(self, geometry_code: str) -> str:
        """Cree le template HTML complet"""
        
        # DNA signature unique
        dna_display = self.avatar_id[:32] + "..."
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Avatar 3D - {self.geometry_type.replace('_', ' ').title()} | Poly-Spinor Nexus 7D</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: linear-gradient(135deg, #0a0a1a 0%, #1a0a2a 50%, #0a1a2a 100%);
            font-family: 'Segoe UI', 'Consolas', monospace;
            color: #e0e0e0;
            overflow: hidden;
        }}
        #container {{ width: 100vw; height: 100vh; position: relative; }}
        #canvas-container {{ width: 100%; height: 100%; }}
        
        #info-panel {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(10, 10, 30, 0.9);
            border: 1px solid {self.primary_color};
            border-radius: 12px;
            padding: 20px;
            min-width: 300px;
            backdrop-filter: blur(10px);
            box-shadow: 0 0 40px {self.primary_color}44;
        }}
        #info-panel h1 {{
            color: {self.primary_color};
            font-size: 1.3em;
            margin-bottom: 15px;
            text-shadow: 0 0 15px {self.primary_color};
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            margin: 8px 0;
            padding: 6px 0;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }}
        .info-label {{ color: #777; font-size: 0.9em; }}
        .info-value {{ color: {self.secondary_color}; font-weight: bold; }}
        .rarity-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            background: {self.primary_color}33;
            border: 1px solid {self.primary_color};
            color: {self.primary_color};
            font-size: 0.85em;
            text-shadow: 0 0 8px {self.primary_color};
        }}
        .dna-code {{
            font-family: monospace;
            font-size: 0.7em;
            color: {self.tertiary_color};
            word-break: break-all;
            padding: 8px;
            background: rgba(0,0,0,0.3);
            border-radius: 4px;
            margin-top: 10px;
        }}
        
        #power-indicator {{
            position: absolute;
            top: 20px;
            right: 20px;
            width: 90px;
            height: 90px;
            border-radius: 50%;
            background: radial-gradient(circle, {self.primary_color}55 0%, transparent 70%);
            border: 3px solid {self.primary_color};
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 35px {self.primary_color}66;
        }}
        #power-indicator .power-value {{
            font-size: 1.4em;
            font-weight: bold;
            color: {self.primary_color};
        }}
        #power-indicator .power-label {{
            font-size: 0.7em;
            color: #888;
        }}
        
        #controls {{
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 12px;
        }}
        .control-btn {{
            background: rgba(10, 10, 30, 0.85);
            border: 1px solid {self.primary_color};
            color: {self.primary_color};
            padding: 12px 22px;
            border-radius: 6px;
            cursor: pointer;
            font-family: inherit;
            font-size: 0.9em;
            transition: all 0.3s;
        }}
        .control-btn:hover {{
            background: {self.primary_color}33;
            box-shadow: 0 0 20px {self.primary_color}55;
        }}
        .control-btn.active {{
            background: {self.primary_color};
            color: #000;
        }}
        
        #unique-params {{
            position: absolute;
            bottom: 80px;
            right: 20px;
            background: rgba(10, 10, 30, 0.85);
            border: 1px solid {self.tertiary_color};
            border-radius: 8px;
            padding: 12px;
            font-size: 0.75em;
        }}
        #unique-params h3 {{
            color: {self.tertiary_color};
            margin-bottom: 8px;
            font-size: 0.9em;
        }}
        .param-row {{
            display: flex;
            justify-content: space-between;
            margin: 3px 0;
        }}
        .param-name {{ color: #666; }}
        .param-val {{ color: {self.accent_color}; font-family: monospace; }}
        
        #loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: {self.primary_color};
            font-size: 1.5em;
        }}
        
        @keyframes glow {{
            from {{ text-shadow: 0 0 5px {self.primary_color}, 0 0 10px {self.primary_color}; }}
            to {{ text-shadow: 0 0 15px {self.primary_color}, 0 0 25px {self.primary_color}; }}
        }}
        .glow {{ animation: glow 2s ease-in-out infinite alternate; }}
    </style>
</head>
<body>
    <div id="container">
        <div id="canvas-container"></div>
        
        <div id="info-panel">
            <h1 class="glow">🎭 AVATAR UNIQUE</h1>
            <div class="info-row">
                <span class="info-label">Type</span>
                <span class="info-value">{self.geometry_type.replace('_', ' ').title()}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Rarete</span>
                <span class="rarity-badge">{self.rarity_tier.upper()}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Score</span>
                <span class="info-value">{self.rarity_score:.1f}/100</span>
            </div>
            <div class="info-row">
                <span class="info-label">Puissance</span>
                <span class="info-value">{self.power:,.0f}</span>
            </div>
            <div class="dna-code">DNA: {dna_display}</div>
        </div>
        
        <div id="power-indicator">
            <span class="power-value">{int(self.power/1000)}K</span>
            <span class="power-label">POWER</span>
        </div>
        
        <div id="unique-params">
            <h3>⚙️ PARAMETRES UNIQUES</h3>
            <div class="param-row"><span class="param-name">Scale</span><span class="param-val">{self.scale_x:.2f}x{self.scale_y:.2f}x{self.scale_z:.2f}</span></div>
            <div class="param-row"><span class="param-name">Metalness</span><span class="param-val">{self.metalness:.2f}</span></div>
            <div class="param-row"><span class="param-name">IOR</span><span class="param-val">{self.ior:.2f}</span></div>
            <div class="param-row"><span class="param-name">Particles</span><span class="param-val">{self.particle_count}</span></div>
            <div class="param-row"><span class="param-name">Complexity</span><span class="param-val">{self.complexity:.1f}x</span></div>
        </div>
        
        <div id="controls">
            <button class="control-btn active" onclick="toggleRotation()">⟳ Auto-Rotate</button>
            <button class="control-btn" onclick="resetCamera()">⌖ Reset</button>
            <button class="control-btn" onclick="toggleWireframe()">◇ Wireframe</button>
            <button class="control-btn" onclick="screenshot()">📷 Screenshot</button>
        </div>
        
        <div id="loading">Chargement de l'avatar unique...</div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    
    <script>
        let scene, camera, renderer, controls;
        let autoRotate = true;
        let wireframeMode = false;
        const animationCallbacks = [];
        
        function init() {{
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x0a0a1a);
            scene.fog = new THREE.FogExp2(0x0a0a1a, 0.08);
            
            camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.set(3.5, 2.5, 3.5);
            
            renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            renderer.toneMapping = THREE.ACESFilmicToneMapping;
            renderer.toneMappingExposure = 1.3;
            renderer.outputEncoding = THREE.sRGBEncoding;
            document.getElementById('canvas-container').appendChild(renderer.domElement);
            
            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.autoRotate = autoRotate;
            controls.autoRotateSpeed = 0.8;
            controls.minDistance = 2;
            controls.maxDistance = 12;
            
            // Eclairage avance
            const ambientLight = new THREE.AmbientLight(0x404050, 0.4);
            scene.add(ambientLight);
            
            const mainLight = new THREE.DirectionalLight(0xffffff, 1.2);
            mainLight.position.set(5, 8, 5);
            mainLight.castShadow = true;
            scene.add(mainLight);
            
            const fillLight = new THREE.DirectionalLight('{self.primary_color}', 0.6);
            fillLight.position.set(-5, 2, -5);
            scene.add(fillLight);
            
            const backLight = new THREE.DirectionalLight('{self.secondary_color}', 0.4);
            backLight.position.set(0, -5, -3);
            scene.add(backLight);
            
            const rimLight = new THREE.DirectionalLight('{self.tertiary_color}', 0.3);
            rimLight.position.set(3, 0, -5);
            scene.add(rimLight);
            
            // Grille de sol
            const gridHelper = new THREE.GridHelper(12, 24, '{self.primary_color}', 0x222244);
            gridHelper.position.y = -2;
            gridHelper.material.opacity = 0.3;
            gridHelper.material.transparent = true;
            scene.add(gridHelper);
            
            // Creer la geometrie unique de l'avatar
            {geometry_code}
            
            document.getElementById('loading').style.display = 'none';
            window.addEventListener('resize', onWindowResize);
            animate();
        }}
        
        function animate() {{
            requestAnimationFrame(animate);
            const time = performance.now() * 0.001;
            animationCallbacks.forEach(cb => cb(time));
            controls.update();
            renderer.render(scene, camera);
        }}
        
        function onWindowResize() {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }}
        
        function toggleRotation() {{
            autoRotate = !autoRotate;
            controls.autoRotate = autoRotate;
            event.target.classList.toggle('active', autoRotate);
        }}
        
        function resetCamera() {{
            camera.position.set(3.5, 2.5, 3.5);
            controls.target.set(0, 0, 0);
            controls.update();
        }}
        
        function toggleWireframe() {{
            wireframeMode = !wireframeMode;
            scene.traverse((child) => {{
                if (child.isMesh && child.material && !child.material.isShaderMaterial) {{
                    if (Array.isArray(child.material)) {{
                        child.material.forEach(m => m.wireframe = wireframeMode);
                    }} else {{
                        child.material.wireframe = wireframeMode;
                    }}
                }}
            }});
            event.target.classList.toggle('active', wireframeMode);
        }}
        
        function screenshot() {{
            renderer.render(scene, camera);
            const link = document.createElement('a');
            link.download = 'avatar_3d_{self.avatar_id[:8]}.png';
            link.href = renderer.domElement.toDataURL('image/png');
            link.click();
        }}
        
        init();
    </script>
</body>
</html>'''


def render_avatar_threejs(avatar_data: Dict, output_path: str = None, auto_open: bool = True) -> str:
    """Fonction utilitaire pour rendre un avatar en Three.js"""
    renderer = ThreeJSAvatarRenderer(avatar_data)
    return renderer.generate_html(output_path, auto_open)


if __name__ == "__main__":
    test_avatar = {
        'avatar_id': 'test_avatar_12345678abcdef_unique_dna_signature',
        'geometry_type': 'nexus_crystal',
        'rarity_tier': 'legendary',
        'rarity_score': 78.5,
        'effective_power': 12500,
        'attributes': {'quantum_entropy': 85.2, 'dimensional_sync': 72.1}
    }
    
    path = render_avatar_threejs(test_avatar)
    print(f"Avatar rendu: {path}")
