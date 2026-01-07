#!/usr/bin/env python3
"""
Three.js Avatar Renderer - Generation de visualisations 3D WebGL uniques
Chaque avatar est mathematiquement unique base sur son DNA cryptographique
Version 2.0 - Effets avances et rendu cinematographique
"""

import hashlib
import math
import webbrowser
from pathlib import Path
from typing import Dict, Optional


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
        self._generate_unique_params()
    
    def _generate_unique_params(self):
        """Genere TOUS les parametres uniques depuis l'avatar ID (DNA)"""
        h = hashlib.sha512(self.avatar_id.encode()).hexdigest()  # 128 chars
        
        def hash_float(start: int, min_v: float = 0.0, max_v: float = 1.0) -> float:
            """Extrait un float depuis 4 caractères hex"""
            val = int(h[start:start+4], 16) / 65535.0
            return min_v + val * (max_v - min_v)
        
        def hash_int(start: int, min_v: int, max_v: int) -> int:
            """Extrait un int depuis 2 caractères hex"""
            val = int(h[start:start+2], 16)
            return min_v + (val % (max_v - min_v + 1))
        
        # Couleurs uniques (6 chars chacune = 36 premiers chars)
        self.primary_color = self._get_rarity_color()
        self.secondary_color = f"#{h[0:6]}"
        self.tertiary_color = f"#{h[6:12]}"
        self.accent_color = f"#{h[12:18]}"
        self.glow_color = f"#{h[18:24]}"
        self.energy_color = f"#{h[24:30]}"
        
        # Geometrie (a partir de 30)
        self.scale_x = hash_float(30, 0.8, 1.2)
        self.scale_y = hash_float(34, 0.8, 1.2)
        self.scale_z = hash_float(38, 0.8, 1.2)
        self.rot_x = hash_float(42, 0, math.pi * 2)
        self.rot_y = hash_float(46, 0, math.pi * 2)
        self.rot_z = hash_float(50, 0, math.pi * 2)
        
        # Animation
        self.anim_speed = hash_float(54, 0.4, 1.2)
        self.pulse_speed = hash_float(58, 0.8, 2.5)
        self.orbit_speed = hash_float(62, 0.3, 0.8)
        self.wave_freq = hash_float(66, 2, 6)
        self.wave_amp = hash_float(70, 0.05, 0.2)
        
        # Complexite basee sur rarete
        rarity_mult = {"common": 1.0, "uncommon": 1.2, "rare": 1.5, "epic": 1.8, 
                       "legendary": 2.2, "mythical": 2.8, "primordial": 3.5}
        self.complexity = rarity_mult.get(self.rarity_tier.lower(), 1.0)
        
        # Elements
        self.particle_count = hash_int(74, 50, int(200 * self.complexity))
        self.ring_count = hash_int(76, 3, int(8 * self.complexity))
        self.satellite_count = hash_int(78, 6, int(16 * self.complexity))
        self.energy_beams = hash_int(80, 4, int(12 * self.complexity))
        
        # Materiaux
        self.metalness = hash_float(82, 0.2, 0.85)
        self.roughness = hash_float(86, 0.02, 0.3)
        self.clearcoat = hash_float(90, 0.5, 1.0)
        self.emission_intensity = hash_float(94, 0.2, 0.6)
        self.opacity = hash_float(98, 0.7, 0.95)
        self.ior = hash_float(102, 1.5, 2.8)
        self.sheen = hash_float(106, 0.0, 1.0)
        self.iridescence = hash_float(110, 0.0, 1.0)
        
        # Effets
        self.has_aura = self.complexity > 1.3
        self.has_particles = self.complexity > 1.0
        self.has_energy_core = self.complexity > 1.5
        self.has_hologram = self.complexity > 2.0
        self.bloom_strength = hash_float(114, 0.3, 1.5)
        
        # Deformations
        self.deform_a = hash_float(118, -0.2, 0.2)
        self.deform_b = hash_float(122, -0.2, 0.2)
        self.deform_freq = hash_float(126, 2, 6)
        self.noise_scale = hash_float(0, 0.5, 2.0)  # Wrap around
        
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
        r = min(255, int(int(hex_color[0:2], 16) + (255 - int(hex_color[0:2], 16)) * factor))
        g = min(255, int(int(hex_color[2:4], 16) + (255 - int(hex_color[2:4], 16)) * factor))
        b = min(255, int(int(hex_color[4:6], 16) + (255 - int(hex_color[4:6], 16)) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def generate_html(self, output_path: Optional[str] = None, auto_open: bool = True) -> str:
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
        
        base_code = generator()
        effects_code = self._generate_effects_code()
        
        return base_code + effects_code
    
    def _generate_effects_code(self) -> str:
        """Genere les effets visuels avances"""
        code = ""
        
        # Aura energetique
        if self.has_aura:
            code += self._get_aura_code()
        
        # Particules orbitales
        if self.has_particles:
            code += self._get_particles_code()
        
        # Coeur d'energie
        if self.has_energy_core:
            code += self._get_energy_core_code()
        
        # Effet holographique
        if self.has_hologram:
            code += self._get_hologram_code()
        
        return code
    
    def _get_aura_code(self) -> str:
        return '''
            // === AURA ENERGETIQUE ===
            const auraGroup = new THREE.Group();
            scene.add(auraGroup);
            
            // Sphere d'aura externe avec shader
            const auraGeom = new THREE.SphereGeometry(2.2, 64, 64);
            const auraMat = new THREE.ShaderMaterial({
                uniforms: {
                    time: { value: 0 },
                    color1: { value: new THREE.Color('%s') },
                    color2: { value: new THREE.Color('%s') },
                    opacity: { value: 0.15 }
                },
                vertexShader: `
                    varying vec3 vNormal;
                    varying vec3 vPosition;
                    varying vec2 vUv;
                    void main() {
                        vNormal = normalize(normalMatrix * normal);
                        vPosition = position;
                        vUv = uv;
                        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                    }
                `,
                fragmentShader: `
                    uniform float time;
                    uniform vec3 color1;
                    uniform vec3 color2;
                    uniform float opacity;
                    varying vec3 vNormal;
                    varying vec3 vPosition;
                    varying vec2 vUv;
                    
                    void main() {
                        float pulse = sin(time * %.2f) * 0.5 + 0.5;
                        float fresnel = pow(1.0 - abs(dot(vNormal, vec3(0.0, 0.0, 1.0))), 2.5);
                        float wave = sin(vPosition.y * 8.0 + time * 3.0) * 0.5 + 0.5;
                        vec3 color = mix(color1, color2, wave * pulse);
                        float alpha = fresnel * opacity * (0.6 + pulse * 0.4);
                        gl_FragColor = vec4(color, alpha);
                    }
                `,
                transparent: true,
                blending: THREE.AdditiveBlending,
                side: THREE.BackSide,
                depthWrite: false
            });
            const aura = new THREE.Mesh(auraGeom, auraMat);
            auraGroup.add(aura);
            
            // Anneaux d'energie rotatifs
            for (let i = 0; i < 3; i++) {
                const ringGeom = new THREE.TorusGeometry(1.8 + i * 0.3, 0.02, 16, 100);
                const ringMat = new THREE.MeshBasicMaterial({
                    color: '%s',
                    transparent: true,
                    opacity: 0.4 - i * 0.1,
                    blending: THREE.AdditiveBlending
                });
                const ring = new THREE.Mesh(ringGeom, ringMat);
                ring.rotation.x = Math.PI / 2 + i * 0.3;
                ring.rotation.y = i * 0.5;
                auraGroup.add(ring);
                
                animationCallbacks.push((time) => {
                    ring.rotation.z = time * (0.3 + i * 0.15);
                    ring.rotation.x = Math.PI / 2 + Math.sin(time + i) * 0.2;
                });
            }
            
            animationCallbacks.push((time) => {
                auraMat.uniforms.time.value = time;
                aura.rotation.y = time * 0.05;
            });
        ''' % (self.primary_color, self.glow_color, self.pulse_speed, self.energy_color)
    
    def _get_particles_code(self) -> str:
        return '''
            // === PARTICULES ORBITALES DYNAMIQUES ===
            const particleCount = %d;
            const particlesGeom = new THREE.BufferGeometry();
            const positions = new Float32Array(particleCount * 3);
            const colors = new Float32Array(particleCount * 3);
            const sizes = new Float32Array(particleCount);
            const phases = new Float32Array(particleCount * 4);
            
            const colorPalette = [
                new THREE.Color('%s'),
                new THREE.Color('%s'),
                new THREE.Color('%s'),
                new THREE.Color('%s')
            ];
            
            for (let i = 0; i < particleCount; i++) {
                const theta = Math.random() * Math.PI * 2;
                const phi = Math.acos(2 * Math.random() - 1);
                const r = 1.2 + Math.random() * 1.5;
                
                positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
                positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
                positions[i * 3 + 2] = r * Math.cos(phi);
                
                const color = colorPalette[Math.floor(Math.random() * 4)];
                colors[i * 3] = color.r;
                colors[i * 3 + 1] = color.g;
                colors[i * 3 + 2] = color.b;
                
                sizes[i] = 0.02 + Math.random() * 0.08;
                phases[i * 4] = r;
                phases[i * 4 + 1] = theta;
                phases[i * 4 + 2] = phi;
                phases[i * 4 + 3] = 0.2 + Math.random() * %.2f;
            }
            
            particlesGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            particlesGeom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
            particlesGeom.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
            
            const particlesMat = new THREE.PointsMaterial({
                size: 0.1,
                vertexColors: true,
                transparent: true,
                opacity: 0.85,
                blending: THREE.AdditiveBlending,
                depthWrite: false,
                sizeAttenuation: true
            });
            
            const particles = new THREE.Points(particlesGeom, particlesMat);
            scene.add(particles);
            
            animationCallbacks.push((time) => {
                const pos = particles.geometry.attributes.position.array;
                for (let i = 0; i < particleCount; i++) {
                    const r = phases[i * 4];
                    const baseTheta = phases[i * 4 + 1];
                    const basePhi = phases[i * 4 + 2];
                    const speed = phases[i * 4 + 3];
                    
                    const theta = baseTheta + time * speed;
                    const phi = basePhi + Math.sin(time * speed * 0.5) * 0.3;
                    const dynamicR = r + Math.sin(time * 2 + i) * 0.1;
                    
                    pos[i * 3] = dynamicR * Math.sin(phi) * Math.cos(theta);
                    pos[i * 3 + 1] = dynamicR * Math.sin(phi) * Math.sin(theta);
                    pos[i * 3 + 2] = dynamicR * Math.cos(phi);
                }
                particles.geometry.attributes.position.needsUpdate = true;
            });
        ''' % (self.particle_count, self.primary_color, self.secondary_color, 
               self.tertiary_color, self.accent_color, self.orbit_speed)
    
    def _get_energy_core_code(self) -> str:
        return '''
            // === COEUR D'ENERGIE PULSANT ===
            const coreGroup = new THREE.Group();
            scene.add(coreGroup);
            
            // Noyau central
            const coreGeom = new THREE.IcosahedronGeometry(0.2, 3);
            const coreMat = new THREE.MeshPhysicalMaterial({
                color: '%s',
                emissive: '%s',
                emissiveIntensity: 1.5,
                metalness: 0.0,
                roughness: 0.0,
                transparent: true,
                opacity: 0.95,
                envMapIntensity: 2.0
            });
            const core = new THREE.Mesh(coreGeom, coreMat);
            coreGroup.add(core);
            
            // Halo interne
            const haloGeom = new THREE.SphereGeometry(0.35, 32, 32);
            const haloMat = new THREE.MeshBasicMaterial({
                color: '%s',
                transparent: true,
                opacity: 0.3,
                blending: THREE.AdditiveBlending,
                side: THREE.BackSide
            });
            const halo = new THREE.Mesh(haloGeom, haloMat);
            coreGroup.add(halo);
            
            // Rayons d'energie
            for (let i = 0; i < %d; i++) {
                const angle = (i / %d) * Math.PI * 2;
                const rayGeom = new THREE.CylinderGeometry(0.008, 0.002, 2.5, 8);
                const rayMat = new THREE.MeshBasicMaterial({
                    color: '%s',
                    transparent: true,
                    opacity: 0.6,
                    blending: THREE.AdditiveBlending
                });
                const ray = new THREE.Mesh(rayGeom, rayMat);
                ray.position.set(Math.cos(angle) * 0.1, 0, Math.sin(angle) * 0.1);
                ray.rotation.z = Math.PI / 2;
                ray.rotation.y = angle;
                coreGroup.add(ray);
                
                animationCallbacks.push((time) => {
                    ray.scale.y = 0.5 + Math.sin(time * 3 + i) * 0.5;
                    ray.material.opacity = 0.3 + Math.sin(time * 2 + i * 0.5) * 0.3;
                });
            }
            
            // Point light central
            const coreLight = new THREE.PointLight('%s', 3, 5);
            coreGroup.add(coreLight);
            
            animationCallbacks.push((time) => {
                const pulse = 1 + Math.sin(time * %.2f) * 0.3;
                core.scale.setScalar(pulse);
                halo.scale.setScalar(pulse * 1.2);
                coreLight.intensity = 2 + Math.sin(time * %.2f) * 1.5;
                core.rotation.x = time * 0.5;
                core.rotation.y = time * 0.7;
            });
        ''' % (self.glow_color, self.primary_color, self.emission_color,
               self.energy_beams, self.energy_beams, self.accent_color,
               self.primary_color, self.pulse_speed, self.pulse_speed)
    
    def _get_hologram_code(self) -> str:
        return '''
            // === EFFET HOLOGRAPHIQUE ===
            const holoGroup = new THREE.Group();
            scene.add(holoGroup);
            
            // Lignes de scan horizontales
            for (let i = 0; i < 20; i++) {
                const y = -1.5 + i * 0.15;
                const lineGeom = new THREE.PlaneGeometry(3, 0.003);
                const lineMat = new THREE.MeshBasicMaterial({
                    color: '%s',
                    transparent: true,
                    opacity: 0.15,
                    blending: THREE.AdditiveBlending,
                    side: THREE.DoubleSide
                });
                const line = new THREE.Mesh(lineGeom, lineMat);
                line.position.y = y;
                holoGroup.add(line);
            }
            
            // Grille hexagonale de fond
            const hexRadius = 2.5;
            const hexGeom = new THREE.CircleGeometry(hexRadius, 6);
            const hexMat = new THREE.MeshBasicMaterial({
                color: '%s',
                transparent: true,
                opacity: 0.05,
                wireframe: true,
                blending: THREE.AdditiveBlending
            });
            
            for (let layer = 0; layer < 3; layer++) {
                const hex = new THREE.Mesh(hexGeom, hexMat.clone());
                hex.rotation.x = -Math.PI / 2;
                hex.position.y = -1.5 + layer * 0.5;
                hex.scale.setScalar(1 - layer * 0.2);
                holoGroup.add(hex);
            }
            
            // Data streams verticaux
            for (let i = 0; i < 8; i++) {
                const angle = (i / 8) * Math.PI * 2;
                const streamGeom = new THREE.BoxGeometry(0.02, 3, 0.02);
                const streamMat = new THREE.MeshBasicMaterial({
                    color: '%s',
                    transparent: true,
                    opacity: 0.2,
                    blending: THREE.AdditiveBlending
                });
                const stream = new THREE.Mesh(streamGeom, streamMat);
                stream.position.set(Math.cos(angle) * 1.8, 0, Math.sin(angle) * 1.8);
                holoGroup.add(stream);
                
                animationCallbacks.push((time) => {
                    stream.material.opacity = 0.1 + Math.sin(time * 4 + i) * 0.15;
                    stream.scale.y = 0.8 + Math.sin(time * 2 + i * 0.5) * 0.2;
                });
            }
            
            animationCallbacks.push((time) => {
                holoGroup.rotation.y = time * 0.1;
            });
        ''' % (self.primary_color, self.tertiary_color, self.accent_color)
    
    def _generate_quantum_sphere(self) -> str:
        return f'''
            // === QUANTUM SPHERE - Forme Unique ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {self.scale_y:.3f}, {self.scale_z:.3f});
            scene.add(mainGroup);
            
            // Sphere principale avec deformation procedurale
            const sphereGeom = new THREE.IcosahedronGeometry(1, 5);
            const posAttr = sphereGeom.attributes.position;
            
            for (let i = 0; i < posAttr.count; i++) {{
                const x = posAttr.getX(i);
                const y = posAttr.getY(i);
                const z = posAttr.getZ(i);
                const noise = {self.deform_a:.3f} * Math.sin(y * {self.deform_freq:.2f} + x * z * 2.0);
                const factor = 1 + noise;
                posAttr.setXYZ(i, x * factor, y * factor, z * factor);
            }}
            sphereGeom.computeVertexNormals();
            
            const sphereMat = new THREE.MeshPhysicalMaterial({{
                color: '{self.primary_color}',
                metalness: {self.metalness:.3f},
                roughness: {self.roughness:.3f},
                transparent: true,
                opacity: {self.opacity:.3f},
                emissive: '{self.emission_color}',
                emissiveIntensity: {self.emission_intensity:.3f},
                clearcoat: {self.clearcoat:.3f},
                clearcoatRoughness: 0.1,
                iridescence: {self.iridescence:.3f},
                iridescenceIOR: 1.5,
                sheen: {self.sheen:.3f},
                sheenColor: new THREE.Color('{self.secondary_color}'),
                envMapIntensity: 1.5
            }});
            const sphere = new THREE.Mesh(sphereGeom, sphereMat);
            mainGroup.add(sphere);
            
            // Anneaux orbitaux multiples
            for (let i = 0; i < {self.ring_count}; i++) {{
                const ringR = 1.15 + i * 0.18;
                const ringGeom = new THREE.TorusGeometry(ringR, 0.012 + i * 0.003, 16, 100);
                const ringMat = new THREE.MeshBasicMaterial({{
                    color: i % 2 === 0 ? '{self.secondary_color}' : '{self.tertiary_color}',
                    transparent: true,
                    opacity: 0.6 - i * 0.08
                }});
                const ring = new THREE.Mesh(ringGeom, ringMat);
                ring.rotation.x = Math.PI / 2 + i * {self.deform_a:.3f} * 2;
                ring.rotation.y = i * 0.4;
                mainGroup.add(ring);
                
                animationCallbacks.push((time) => {{
                    ring.rotation.z = time * {self.anim_speed:.3f} * (0.4 + i * 0.15);
                    ring.rotation.x = Math.PI / 2 + Math.sin(time * 0.5 + i) * 0.15;
                }});
            }}
            
            // Satellites orbitaux
            for (let i = 0; i < {self.satellite_count}; i++) {{
                const satGeom = new THREE.OctahedronGeometry(0.06 + Math.random() * 0.04, 0);
                const satMat = new THREE.MeshPhysicalMaterial({{
                    color: ['{self.secondary_color}', '{self.tertiary_color}', '{self.accent_color}'][i % 3],
                    metalness: 0.8,
                    roughness: 0.2,
                    emissive: ['{self.secondary_color}', '{self.tertiary_color}', '{self.accent_color}'][i % 3],
                    emissiveIntensity: 0.4
                }});
                const sat = new THREE.Mesh(satGeom, satMat);
                const orbitR = 1.4 + (i % 4) * 0.2;
                const phase = (i / {self.satellite_count}) * Math.PI * 2;
                sat.userData = {{ orbitR, phase, speed: {self.orbit_speed:.3f} * (0.7 + Math.random() * 0.6) }};
                mainGroup.add(sat);
                
                animationCallbacks.push((time) => {{
                    const d = sat.userData;
                    const angle = d.phase + time * d.speed;
                    sat.position.set(
                        Math.cos(angle) * d.orbitR,
                        Math.sin(time * 1.5 + d.phase) * 0.3,
                        Math.sin(angle) * d.orbitR
                    );
                    sat.rotation.x = time * 2;
                    sat.rotation.y = time * 3;
                }});
            }}
            
            animationCallbacks.push((time) => {{
                sphere.rotation.y = time * {self.anim_speed:.3f} * 0.2;
                const pulse = 1 + Math.sin(time * {self.pulse_speed:.2f}) * 0.03;
                sphere.scale.setScalar(pulse);
            }});
        '''
    
    def _generate_nexus_crystal(self) -> str:
        scale_y_stretched = self.scale_y * 1.6
        emission_boosted = self.emission_intensity * 1.5
        return f'''
            // === NEXUS CRYSTAL - Cristal Unique ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {scale_y_stretched:.3f}, {self.scale_z:.3f});
            scene.add(mainGroup);
            
            // Cristal principal avec facettes
            const crystalPoints = [];
            crystalPoints.push(new THREE.Vector3(0, 1.2, 0));
            for (let i = 0; i < 6; i++) {{
                const angle = (i / 6) * Math.PI * 2;
                const r = 0.6 + {self.deform_a:.3f} * Math.sin(i * 2);
                crystalPoints.push(new THREE.Vector3(Math.cos(angle) * r, 0.3, Math.sin(angle) * r));
            }}
            for (let i = 0; i < 6; i++) {{
                const angle = (i / 6) * Math.PI * 2 + Math.PI / 6;
                const r = 0.8 + {self.deform_b:.3f} * Math.cos(i * 3);
                crystalPoints.push(new THREE.Vector3(Math.cos(angle) * r, -0.2, Math.sin(angle) * r));
            }}
            crystalPoints.push(new THREE.Vector3(0, -1.0, 0));
            
            const crystalGeom = new THREE.ConvexGeometry ? 
                new THREE.ConvexGeometry(crystalPoints) : 
                new THREE.OctahedronGeometry(1, 0);
            
            if (!THREE.ConvexGeometry) {{
                crystalGeom.scale(1, 1.5, 1);
            }}
            
            const crystalMat = new THREE.MeshPhysicalMaterial({{
                color: '{self.primary_color}',
                metalness: 0.0,
                roughness: 0.0,
                transparent: true,
                opacity: 0.85,
                emissive: '{self.emission_color}',
                emissiveIntensity: {emission_boosted:.3f},
                clearcoat: 1.0,
                clearcoatRoughness: 0.0,
                ior: {self.ior:.3f},
                transmission: 0.5,
                thickness: 0.5,
                iridescence: 1.0,
                iridescenceIOR: 2.0,
                envMapIntensity: 2.0
            }});
            const crystal = new THREE.Mesh(crystalGeom, crystalMat);
            mainGroup.add(crystal);
            
            // Cristaux satellites
            for (let i = 0; i < {self.satellite_count}; i++) {{
                const angle = (i / {self.satellite_count}) * Math.PI * 2;
                const satGeom = new THREE.OctahedronGeometry(0.15 + Math.random() * 0.1, 0);
                satGeom.scale(1, 1.4, 1);
                const satMat = new THREE.MeshPhysicalMaterial({{
                    color: i % 2 === 0 ? '{self.secondary_color}' : '{self.tertiary_color}',
                    metalness: 0.0,
                    roughness: 0.0,
                    transparent: true,
                    opacity: 0.8,
                    emissive: i % 2 === 0 ? '{self.secondary_color}' : '{self.tertiary_color}',
                    emissiveIntensity: 0.4,
                    transmission: 0.3
                }});
                const sat = new THREE.Mesh(satGeom, satMat);
                sat.userData = {{ angle, baseY: Math.sin(angle * 2) * 0.3 }};
                sat.position.set(Math.cos(angle) * 1.3, sat.userData.baseY, Math.sin(angle) * 1.3);
                sat.rotation.z = angle;
                mainGroup.add(sat);
                
                animationCallbacks.push((time) => {{
                    sat.position.y = sat.userData.baseY + Math.sin(time * {self.pulse_speed:.2f} + i) * 0.2;
                    sat.rotation.y = time * {self.anim_speed:.3f} * 0.5;
                    sat.rotation.x = Math.sin(time + i) * 0.3;
                }});
            }}
            
            // Lumieres internes
            const innerLight = new THREE.PointLight('{self.primary_color}', 4, 6);
            mainGroup.add(innerLight);
            
            const accentLight = new THREE.PointLight('{self.glow_color}', 2, 4);
            accentLight.position.y = 0.5;
            mainGroup.add(accentLight);
            
            animationCallbacks.push((time) => {{
                crystal.rotation.y = time * {self.anim_speed:.3f} * 0.25;
                crystal.position.y = Math.sin(time * {self.pulse_speed:.2f}) * 0.05;
                innerLight.intensity = 3 + Math.sin(time * {self.pulse_speed:.2f}) * 1.5;
            }});
        '''
    
    def _generate_spinor_torus(self) -> str:
        return f'''
            // === SPINOR TORUS - Tore Quantique ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {self.scale_y:.3f}, {self.scale_z:.3f});
            scene.add(mainGroup);
            
            // Tore principal avec ondulations
            const torusGeom = new THREE.TorusGeometry(1, 0.35, 48, 100);
            const torusPos = torusGeom.attributes.position;
            
            for (let i = 0; i < torusPos.count; i++) {{
                const x = torusPos.getX(i);
                const y = torusPos.getY(i);
                const z = torusPos.getZ(i);
                const angle = Math.atan2(z, x);
                const wave = {self.deform_a:.3f} * Math.sin(angle * {self.wave_freq:.1f});
                torusPos.setXYZ(i, x * (1 + wave), y, z * (1 + wave));
            }}
            torusGeom.computeVertexNormals();
            
            const torusMat = new THREE.MeshPhysicalMaterial({{
                color: '{self.primary_color}',
                metalness: {self.metalness:.3f},
                roughness: {self.roughness:.3f},
                transparent: true,
                opacity: {self.opacity:.3f},
                emissive: '{self.emission_color}',
                emissiveIntensity: {self.emission_intensity:.3f},
                clearcoat: {self.clearcoat:.3f},
                iridescence: {self.iridescence:.3f},
                sheen: {self.sheen:.3f},
                sheenColor: new THREE.Color('{self.secondary_color}')
            }});
            const torus = new THREE.Mesh(torusGeom, torusMat);
            mainGroup.add(torus);
            
            // Tores internes en rotation
            for (let i = 0; i < 3; i++) {{
                const innerGeom = new THREE.TorusGeometry(0.75 - i * 0.15, 0.04, 16, 60);
                const innerMat = new THREE.MeshBasicMaterial({{
                    color: ['{self.secondary_color}', '{self.tertiary_color}', '{self.accent_color}'][i],
                    transparent: true,
                    opacity: 0.6 - i * 0.15
                }});
                const inner = new THREE.Mesh(innerGeom, innerMat);
                mainGroup.add(inner);
                
                animationCallbacks.push((time) => {{
                    inner.rotation.x = time * {self.anim_speed:.3f} * (1 + i * 0.3);
                    inner.rotation.y = time * {self.anim_speed:.3f} * 0.5 * (i + 1);
                }});
            }}
            
            // Flux d'energie sur le tore
            for (let i = 0; i < {self.energy_beams}; i++) {{
                const angle = (i / {self.energy_beams}) * Math.PI * 2;
                const fluxGeom = new THREE.SphereGeometry(0.06, 16, 16);
                const fluxMat = new THREE.MeshBasicMaterial({{
                    color: '{self.glow_color}',
                    transparent: true,
                    opacity: 0.9
                }});
                const flux = new THREE.Mesh(fluxGeom, fluxMat);
                flux.userData = {{ baseAngle: angle }};
                mainGroup.add(flux);
                
                animationCallbacks.push((time) => {{
                    const a = flux.userData.baseAngle + time * {self.orbit_speed:.3f} * 2;
                    flux.position.set(
                        Math.cos(a) * 1.0,
                        Math.sin(time * 3 + i) * 0.35,
                        Math.sin(a) * 1.0
                    );
                    flux.scale.setScalar(0.8 + Math.sin(time * 4 + i) * 0.3);
                }});
            }}
            
            animationCallbacks.push((time) => {{
                torus.rotation.x = Math.sin(time * {self.anim_speed:.3f} * 0.3) * 0.2;
                torus.rotation.y = time * {self.anim_speed:.3f} * 0.15;
            }});
        '''
    
    def _generate_bell_polyhedron(self) -> str:
        return f'''
            // === BELL POLYHEDRON - Polyedre Quantique ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {self.scale_y:.3f}, {self.scale_z:.3f});
            scene.add(mainGroup);
            
            // Polyedre principal
            const polyGeom = new THREE.IcosahedronGeometry(1, 1);
            const polyPos = polyGeom.attributes.position;
            
            for (let i = 0; i < polyPos.count; i++) {{
                const x = polyPos.getX(i);
                const y = polyPos.getY(i);
                const z = polyPos.getZ(i);
                const noise = {self.deform_a:.3f} * Math.sin(x * y * {self.deform_freq:.2f});
                polyPos.setXYZ(i, x * (1 + noise), y * (1 + noise), z * (1 + noise));
            }}
            polyGeom.computeVertexNormals();
            
            const polyMat = new THREE.MeshPhysicalMaterial({{
                color: '{self.primary_color}',
                metalness: {self.metalness:.3f},
                roughness: {self.roughness:.3f},
                transparent: true,
                opacity: 0.7,
                emissive: '{self.emission_color}',
                emissiveIntensity: {self.emission_intensity:.3f},
                wireframe: false
            }});
            const poly = new THREE.Mesh(polyGeom, polyMat);
            mainGroup.add(poly);
            
            // Wireframe externe
            const wireGeom = new THREE.IcosahedronGeometry(1.05, 1);
            const wireMat = new THREE.MeshBasicMaterial({{
                color: '{self.secondary_color}',
                wireframe: true,
                transparent: true,
                opacity: 0.5
            }});
            const wire = new THREE.Mesh(wireGeom, wireMat);
            mainGroup.add(wire);
            
            // Noeuds aux sommets avec connexions
            const vertices = [];
            const vertexGeom = new THREE.IcosahedronGeometry(1.1, 0);
            const vPos = vertexGeom.attributes.position;
            
            for (let i = 0; i < 12; i++) {{
                const nodeGeom = new THREE.SphereGeometry(0.07, 16, 16);
                const nodeMat = new THREE.MeshBasicMaterial({{
                    color: ['{self.secondary_color}', '{self.tertiary_color}', '{self.accent_color}'][i % 3]
                }});
                const node = new THREE.Mesh(nodeGeom, nodeMat);
                
                const phi = Math.acos(-1 + (2 * i + 1) / 12);
                const theta = Math.sqrt(12 * Math.PI) * phi;
                node.position.set(
                    1.1 * Math.cos(theta) * Math.sin(phi),
                    1.1 * Math.sin(theta) * Math.sin(phi),
                    1.1 * Math.cos(phi)
                );
                mainGroup.add(node);
                vertices.push(node.position.clone());
                
                animationCallbacks.push((time) => {{
                    node.scale.setScalar(1 + Math.sin(time * {self.pulse_speed:.2f} + i) * 0.3);
                }});
            }}
            
            // Connexions quantiques
            const lineMat = new THREE.LineBasicMaterial({{
                color: '{self.glow_color}',
                transparent: true,
                opacity: 0.3
            }});
            
            for (let i = 0; i < vertices.length; i++) {{
                for (let j = i + 1; j < vertices.length; j++) {{
                    if (vertices[i].distanceTo(vertices[j]) < 1.5) {{
                        const points = [vertices[i], new THREE.Vector3(0, 0, 0), vertices[j]];
                        const lineGeom = new THREE.BufferGeometry().setFromPoints(points);
                        const line = new THREE.Line(lineGeom, lineMat);
                        mainGroup.add(line);
                    }}
                }}
            }}
            
            animationCallbacks.push((time) => {{
                poly.rotation.x = time * {self.anim_speed:.3f} * 0.2;
                poly.rotation.y = time * {self.anim_speed:.3f} * 0.3;
                wire.rotation.x = time * {self.anim_speed:.3f} * 0.2;
                wire.rotation.y = time * {self.anim_speed:.3f} * 0.3;
            }});
        '''
    
    def _generate_clifford_lattice(self) -> str:
        grid_size = min(5, int(3 + self.complexity))
        return f'''
            // === CLIFFORD LATTICE - Reseau Cristallin ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {self.scale_y:.3f}, {self.scale_z:.3f});
            scene.add(mainGroup);
            
            const gridSize = {grid_size};
            const spacing = 0.4;
            const nodes = [];
            const connections = [];
            
            // Creation des noeuds
            for (let x = -gridSize/2; x <= gridSize/2; x++) {{
                for (let y = -gridSize/2; y <= gridSize/2; y++) {{
                    for (let z = -gridSize/2; z <= gridSize/2; z++) {{
                        const dist = Math.sqrt(x*x + y*y + z*z);
                        if (dist < gridSize/2 + 0.5) {{
                            const nodeType = Math.abs(x + y + z) % 3;
                            let nodeGeom;
                            if (nodeType === 0) nodeGeom = new THREE.BoxGeometry(0.08, 0.08, 0.08);
                            else if (nodeType === 1) nodeGeom = new THREE.OctahedronGeometry(0.06, 0);
                            else nodeGeom = new THREE.TetrahedronGeometry(0.07, 0);
                            
                            const colorIdx = (Math.abs(x) + Math.abs(y) + Math.abs(z)) % 4;
                            const colors = ['{self.primary_color}', '{self.secondary_color}', '{self.tertiary_color}', '{self.accent_color}'];
                            
                            const nodeMat = new THREE.MeshPhysicalMaterial({{
                                color: colors[colorIdx],
                                metalness: {self.metalness:.3f},
                                roughness: {self.roughness:.3f},
                                emissive: colors[colorIdx],
                                emissiveIntensity: {self.emission_intensity:.3f}
                            }});
                            
                            const node = new THREE.Mesh(nodeGeom, nodeMat);
                            node.position.set(
                                x * spacing + {self.deform_a:.3f} * Math.sin(y * 2),
                                y * spacing + {self.deform_b:.3f} * Math.cos(z * 2),
                                z * spacing
                            );
                            node.userData = {{ basePos: node.position.clone(), idx: nodes.length }};
                            mainGroup.add(node);
                            nodes.push(node);
                        }}
                    }}
                }}
            }}
            
            // Connexions entre noeuds proches
            const lineMat = new THREE.LineBasicMaterial({{
                color: '{self.glow_color}',
                transparent: true,
                opacity: 0.25
            }});
            
            for (let i = 0; i < nodes.length; i++) {{
                for (let j = i + 1; j < nodes.length; j++) {{
                    const dist = nodes[i].position.distanceTo(nodes[j].position);
                    if (dist < spacing * 1.2) {{
                        const points = [nodes[i].position.clone(), nodes[j].position.clone()];
                        const lineGeom = new THREE.BufferGeometry().setFromPoints(points);
                        const line = new THREE.Line(lineGeom, lineMat);
                        mainGroup.add(line);
                    }}
                }}
            }}
            
            // Cube englobant
            const cubeSize = gridSize * spacing * 1.3;
            const cubeGeom = new THREE.BoxGeometry(cubeSize, cubeSize, cubeSize);
            const cubeMat = new THREE.MeshBasicMaterial({{
                color: '{self.energy_color}',
                wireframe: true,
                transparent: true,
                opacity: 0.15
            }});
            const cube = new THREE.Mesh(cubeGeom, cubeMat);
            mainGroup.add(cube);
            
            animationCallbacks.push((time) => {{
                nodes.forEach((node, i) => {{
                    const pulse = Math.sin(time * {self.pulse_speed:.2f} + i * 0.1);
                    node.scale.setScalar(0.8 + pulse * 0.3);
                    node.position.y = node.userData.basePos.y + Math.sin(time * 1.5 + i * 0.15) * 0.03;
                    node.rotation.x = time * 0.5;
                    node.rotation.y = time * 0.7;
                }});
                mainGroup.rotation.y = time * {self.anim_speed:.3f} * 0.08;
                cube.rotation.x = time * 0.03;
                cube.rotation.z = time * 0.02;
            }});
        '''
    
    def _generate_entropy_fractal(self) -> str:
        return f'''
            // === ENTROPY FRACTAL - Arbre Quantique ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {self.scale_y:.3f}, {self.scale_z:.3f});
            scene.add(mainGroup);
            
            const colors = ['{self.primary_color}', '{self.secondary_color}', '{self.tertiary_color}', '{self.accent_color}'];
            const leaves = [];
            const branches = [];
            
            function createBranch(startPos, direction, length, depth, colorIdx) {{
                if (depth <= 0 || length < 0.03) {{
                    // Feuille/Noeud terminal
                    const leafGeom = new THREE.IcosahedronGeometry(0.04 + depth * 0.01, 0);
                    const leafMat = new THREE.MeshPhysicalMaterial({{
                        color: colors[(colorIdx + depth) % 4],
                        emissive: colors[(colorIdx + depth) % 4],
                        emissiveIntensity: 0.5,
                        metalness: 0.3,
                        roughness: 0.4
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
                const tubeGeom = new THREE.TubeGeometry(curve, 8, length * 0.05, 6, false);
                const tubeMat = new THREE.MeshPhysicalMaterial({{
                    color: colors[colorIdx % 4],
                    metalness: {self.metalness * 0.5:.3f},
                    roughness: {self.roughness:.3f},
                    emissive: colors[colorIdx % 4],
                    emissiveIntensity: {self.emission_intensity * 0.3:.3f}
                }});
                const tube = new THREE.Mesh(tubeGeom, tubeMat);
                mainGroup.add(tube);
                branches.push(tube);
                
                // Sous-branches
                const angleSpread = 25 + {self.deform_a:.3f} * 30;
                const branchAngles = [
                    {{ x: -angleSpread, y: 0 }},
                    {{ x: angleSpread, y: 0 }},
                    {{ x: 0, y: -angleSpread * 0.8 }}
                ];
                
                branchAngles.forEach((angles, i) => {{
                    if (Math.random() > 0.15) {{
                        const newDir = direction.clone();
                        newDir.applyAxisAngle(new THREE.Vector3(1, 0, 0), angles.x * Math.PI / 180);
                        newDir.applyAxisAngle(new THREE.Vector3(0, 0, 1), angles.y * Math.PI / 180);
                        newDir.applyAxisAngle(new THREE.Vector3(0, 1, 0), (i - 1) * Math.PI * 0.35);
                        createBranch(endPos.clone(), newDir, length * 0.7, depth - 1, colorIdx + 1);
                    }}
                }});
            }}
            
            // Arbres principaux
            createBranch(new THREE.Vector3(0, -1.2, 0), new THREE.Vector3(0, 1, 0), 0.5, 6, 0);
            
            for (let i = 0; i < 3; i++) {{
                const angle = (i / 3) * Math.PI * 2 + {self.rot_z:.3f};
                const startPos = new THREE.Vector3(Math.cos(angle) * 0.25, -1.1, Math.sin(angle) * 0.25);
                const dir = new THREE.Vector3(Math.cos(angle) * 0.35, 0.9, Math.sin(angle) * 0.35).normalize();
                createBranch(startPos, dir, 0.35, 5, i + 1);
            }}
            
            animationCallbacks.push((time) => {{
                leaves.forEach((leaf, i) => {{
                    leaf.scale.setScalar(1 + Math.sin(time * {self.pulse_speed:.2f} + i * 0.2) * 0.25);
                    leaf.rotation.x = time + i;
                    leaf.rotation.y = time * 1.5 + i;
                }});
                mainGroup.rotation.y = Math.sin(time * {self.anim_speed:.3f} * 0.2) * 0.1;
            }});
        '''
    
    def _generate_7d_projection(self) -> str:
        return f'''
            // === 7D PROJECTION - Dimensions Multiples ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {self.scale_y:.3f}, {self.scale_z:.3f});
            scene.add(mainGroup);
            
            const dimCount = 7;
            const layers = [];
            
            // Creation des 7 dimensions
            for (let d = 0; d < dimCount; d++) {{
                const layerGroup = new THREE.Group();
                const hue = d / dimCount;
                const color = new THREE.Color().setHSL(hue, 0.9, 0.55);
                
                // Heptagone pour chaque dimension
                const r = 1.25 - d * 0.1 + {self.deform_a:.3f} * Math.sin(d * 2);
                const points = [];
                
                for (let i = 0; i < 7; i++) {{
                    const angle = (i / 7) * Math.PI * 2 + d * {self.deform_b:.3f};
                    points.push(new THREE.Vector3(Math.cos(angle) * r, Math.sin(angle) * r, 0));
                }}
                points.push(points[0].clone());
                
                const lineGeom = new THREE.BufferGeometry().setFromPoints(points);
                const lineMat = new THREE.LineBasicMaterial({{
                    color: color,
                    transparent: true,
                    opacity: 0.85 - d * 0.07
                }});
                const line = new THREE.Line(lineGeom, lineMat);
                layerGroup.add(line);
                
                // Noeuds aux sommets
                for (let i = 0; i < 7; i++) {{
                    const nodeGeom = new THREE.OctahedronGeometry(0.06 - d * 0.005, 0);
                    const nodeMat = new THREE.MeshBasicMaterial({{ color: color }});
                    const node = new THREE.Mesh(nodeGeom, nodeMat);
                    node.position.copy(points[i]);
                    layerGroup.add(node);
                }}
                
                // Rayons vers le centre
                for (let i = 0; i < 7; i++) {{
                    const rayPoints = [points[i], new THREE.Vector3(0, 0, 0)];
                    const rayGeom = new THREE.BufferGeometry().setFromPoints(rayPoints);
                    const rayMat = new THREE.LineBasicMaterial({{
                        color: '{self.glow_color}',
                        transparent: true,
                        opacity: 0.2
                    }});
                    layerGroup.add(new THREE.Line(rayGeom, rayMat));
                }}
                
                layerGroup.position.z = d * 0.15 - 0.5;
                layerGroup.rotation.z = d * 0.1 + {self.rot_z:.3f};
                mainGroup.add(layerGroup);
                layers.push(layerGroup);
                
                animationCallbacks.push((time) => {{
                    layerGroup.rotation.z = d * 0.1 + {self.rot_z:.3f} + time * {self.anim_speed:.3f} * (0.12 + d * 0.04);
                    layerGroup.position.z = (d * 0.15 - 0.5) + Math.sin(time * {self.pulse_speed:.2f} + d * 0.5) * 0.08;
                }});
            }}
            
            // Centre multidimensionnel
            const centerGeom = new THREE.DodecahedronGeometry(0.12, 1);
            const centerMat = new THREE.MeshPhysicalMaterial({{
                color: '{self.primary_color}',
                emissive: '{self.primary_color}',
                emissiveIntensity: 0.8,
                metalness: {self.metalness:.3f},
                roughness: {self.roughness:.3f},
                iridescence: 1.0
            }});
            const center = new THREE.Mesh(centerGeom, centerMat);
            mainGroup.add(center);
            
            const centerLight = new THREE.PointLight('{self.primary_color}', 3, 5);
            mainGroup.add(centerLight);
            
            animationCallbacks.push((time) => {{
                center.rotation.x = time * {self.anim_speed:.3f} * 0.5;
                center.rotation.y = time * {self.anim_speed:.3f} * 0.7;
                center.scale.setScalar(1 + Math.sin(time * {self.pulse_speed:.2f}) * 0.15);
                centerLight.intensity = 2 + Math.sin(time * {self.pulse_speed:.2f}) * 1.5;
            }});
        '''
    
    def _generate_hybrid_form(self) -> str:
        return f'''
            // === HYBRID FORM - Forme Composite ===
            const mainGroup = new THREE.Group();
            mainGroup.scale.set({self.scale_x:.3f}, {self.scale_y:.3f}, {self.scale_z:.3f});
            scene.add(mainGroup);
            
            // Noyau dodecaedre
            const coreGeom = new THREE.DodecahedronGeometry(0.5, 1);
            const corePos = coreGeom.attributes.position;
            
            for (let i = 0; i < corePos.count; i++) {{
                const x = corePos.getX(i);
                const y = corePos.getY(i);
                const z = corePos.getZ(i);
                const noise = {self.deform_a:.3f} * Math.sin(x * y * {self.deform_freq:.2f});
                corePos.setXYZ(i, x * (1 + noise), y * (1 + noise * 0.5), z * (1 + noise));
            }}
            coreGeom.computeVertexNormals();
            
            const coreMat = new THREE.MeshPhysicalMaterial({{
                color: '{self.primary_color}',
                metalness: {self.metalness:.3f},
                roughness: {self.roughness:.3f},
                transparent: true,
                opacity: {self.opacity:.3f},
                emissive: '{self.emission_color}',
                emissiveIntensity: {self.emission_intensity:.3f},
                clearcoat: {self.clearcoat:.3f},
                iridescence: {self.iridescence:.3f}
            }});
            const core = new THREE.Mesh(coreGeom, coreMat);
            mainGroup.add(core);
            
            // Anneaux multiples
            for (let i = 0; i < {self.ring_count}; i++) {{
                const ringR = 0.85 + i * 0.2;
                const ringGeom = new THREE.TorusGeometry(ringR, 0.02 + i * 0.004, 16, 80);
                const ringMat = new THREE.MeshBasicMaterial({{
                    color: ['{self.secondary_color}', '{self.tertiary_color}', '{self.accent_color}', '{self.glow_color}'][i % 4],
                    transparent: true,
                    opacity: 0.55 - i * 0.08
                }});
                const ring = new THREE.Mesh(ringGeom, ringMat);
                ring.rotation.x = i * Math.PI / {self.ring_count} + {self.rot_x:.3f};
                ring.rotation.y = i * 0.25 + {self.rot_y:.3f};
                mainGroup.add(ring);
                
                animationCallbacks.push((time) => {{
                    ring.rotation.z = time * {self.anim_speed:.3f} * (0.2 + i * 0.08);
                }});
            }}
            
            // Satellites polyedriques
            const satTypes = [
                () => new THREE.TetrahedronGeometry(0.1, 0),
                () => new THREE.OctahedronGeometry(0.08, 0),
                () => new THREE.IcosahedronGeometry(0.07, 0)
            ];
            
            for (let i = 0; i < {self.satellite_count}; i++) {{
                const satGeom = satTypes[i % 3]();
                const satMat = new THREE.MeshPhysicalMaterial({{
                    color: ['{self.secondary_color}', '{self.tertiary_color}', '{self.accent_color}'][i % 3],
                    metalness: {self.metalness:.3f},
                    roughness: {self.roughness:.3f},
                    emissive: ['{self.secondary_color}', '{self.tertiary_color}', '{self.accent_color}'][i % 3],
                    emissiveIntensity: 0.35
                }});
                const sat = new THREE.Mesh(satGeom, satMat);
                
                const angle = (i / {self.satellite_count}) * Math.PI * 2;
                const orbitR = 1.3 + (i % 4) * 0.15;
                sat.userData = {{ angle, orbitR, speed: {self.orbit_speed:.3f} * (0.7 + (i % 5) * 0.12) }};
                mainGroup.add(sat);
                
                animationCallbacks.push((time) => {{
                    const d = sat.userData;
                    const a = d.angle + time * d.speed;
                    sat.position.set(
                        Math.cos(a) * d.orbitR,
                        Math.sin(time * {self.pulse_speed:.2f} + i) * 0.25,
                        Math.sin(a) * d.orbitR
                    );
                    sat.rotation.x = time * 1.5;
                    sat.rotation.y = time * 2;
                }});
            }}
            
            animationCallbacks.push((time) => {{
                core.rotation.x = time * {self.anim_speed:.3f} * 0.12;
                core.rotation.y = time * {self.anim_speed:.3f} * 0.18;
                core.scale.setScalar(1 + Math.sin(time * {self.pulse_speed:.2f}) * 0.04);
            }});
        '''
    
    def _create_html_template(self, geometry_code: str) -> str:
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
            background: radial-gradient(ellipse at center, #1a1a2e 0%, #0a0a15 50%, #050508 100%);
            font-family: 'Segoe UI', system-ui, sans-serif;
            color: #e0e0e0;
            overflow: hidden;
        }}
        #container {{ width: 100vw; height: 100vh; position: relative; }}
        #canvas-container {{ width: 100%; height: 100%; }}
        
        #info-panel {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: linear-gradient(135deg, rgba(10,10,30,0.95) 0%, rgba(20,10,40,0.9) 100%);
            border: 1px solid {self.primary_color}66;
            border-radius: 16px;
            padding: 24px;
            min-width: 320px;
            backdrop-filter: blur(20px);
            box-shadow: 0 8px 32px rgba(0,0,0,0.4), 0 0 60px {self.primary_color}22, inset 0 1px 0 rgba(255,255,255,0.05);
        }}
        #info-panel h1 {{
            color: {self.primary_color};
            font-size: 1.4em;
            margin-bottom: 18px;
            text-shadow: 0 0 20px {self.primary_color}88;
            letter-spacing: 2px;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }}
        .info-label {{ color: #666; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1px; }}
        .info-value {{ color: {self.secondary_color}; font-weight: 600; font-size: 1.05em; }}
        .rarity-badge {{
            display: inline-block;
            padding: 5px 14px;
            border-radius: 20px;
            background: linear-gradient(135deg, {self.primary_color}44 0%, {self.primary_color}22 100%);
            border: 1px solid {self.primary_color}88;
            color: {self.primary_color};
            font-size: 0.85em;
            font-weight: 600;
            text-shadow: 0 0 10px {self.primary_color};
            letter-spacing: 1px;
        }}
        .dna-code {{
            font-family: 'Consolas', monospace;
            font-size: 0.7em;
            color: {self.tertiary_color};
            word-break: break-all;
            padding: 10px;
            background: rgba(0,0,0,0.4);
            border-radius: 8px;
            margin-top: 15px;
            border: 1px solid rgba(255,255,255,0.05);
        }}
        
        #power-indicator {{
            position: absolute;
            top: 20px;
            right: 20px;
            width: 100px;
            height: 100px;
            border-radius: 50%;
            background: radial-gradient(circle at 30% 30%, {self.primary_color}44 0%, transparent 60%);
            border: 3px solid {self.primary_color}88;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 40px {self.primary_color}44, inset 0 0 20px {self.primary_color}22;
        }}
        #power-indicator .power-value {{
            font-size: 1.6em;
            font-weight: 700;
            color: {self.primary_color};
            text-shadow: 0 0 15px {self.primary_color};
        }}
        #power-indicator .power-label {{
            font-size: 0.7em;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}
        
        #controls {{
            position: absolute;
            bottom: 25px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 15px;
        }}
        .control-btn {{
            background: linear-gradient(135deg, rgba(10,10,30,0.9) 0%, rgba(20,15,40,0.85) 100%);
            border: 1px solid {self.primary_color}66;
            color: {self.primary_color};
            padding: 14px 28px;
            border-radius: 12px;
            cursor: pointer;
            font-family: inherit;
            font-size: 0.95em;
            font-weight: 500;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            backdrop-filter: blur(10px);
        }}
        .control-btn:hover {{
            background: linear-gradient(135deg, {self.primary_color}33 0%, {self.primary_color}22 100%);
            box-shadow: 0 0 25px {self.primary_color}44;
            transform: translateY(-2px);
        }}
        .control-btn.active {{
            background: linear-gradient(135deg, {self.primary_color} 0%, {self.primary_color}cc 100%);
            color: #000;
            font-weight: 600;
        }}
        
        #unique-params {{
            position: absolute;
            bottom: 90px;
            right: 20px;
            background: linear-gradient(135deg, rgba(10,10,30,0.9) 0%, rgba(15,10,35,0.85) 100%);
            border: 1px solid {self.tertiary_color}44;
            border-radius: 12px;
            padding: 16px;
            font-size: 0.8em;
            backdrop-filter: blur(10px);
        }}
        #unique-params h3 {{
            color: {self.tertiary_color};
            margin-bottom: 12px;
            font-size: 0.95em;
            letter-spacing: 1px;
        }}
        .param-row {{ display: flex; justify-content: space-between; margin: 5px 0; gap: 20px; }}
        .param-name {{ color: #555; }}
        .param-val {{ color: {self.accent_color}; font-family: 'Consolas', monospace; font-weight: 600; }}
        
        #loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: {self.primary_color};
            font-size: 1.3em;
            text-shadow: 0 0 20px {self.primary_color};
        }}
        
        @keyframes glow {{
            0%, 100% {{ text-shadow: 0 0 10px {self.primary_color}, 0 0 20px {self.primary_color}88; }}
            50% {{ text-shadow: 0 0 20px {self.primary_color}, 0 0 40px {self.primary_color}, 0 0 60px {self.primary_color}66; }}
        }}
        .glow {{ animation: glow 3s ease-in-out infinite; }}
    </style>
</head>
<body>
    <div id="container">
        <div id="canvas-container"></div>
        
        <div id="info-panel">
            <h1 class="glow">✦ AVATAR UNIQUE</h1>
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
            <span class="power-label">Power</span>
        </div>
        
        <div id="unique-params">
            <h3>⚙ PARAMETRES</h3>
            <div class="param-row"><span class="param-name">Scale</span><span class="param-val">{self.scale_x:.2f}×{self.scale_y:.2f}×{self.scale_z:.2f}</span></div>
            <div class="param-row"><span class="param-name">Metalness</span><span class="param-val">{self.metalness:.2f}</span></div>
            <div class="param-row"><span class="param-name">IOR</span><span class="param-val">{self.ior:.2f}</span></div>
            <div class="param-row"><span class="param-name">Iridescence</span><span class="param-val">{self.iridescence:.2f}</span></div>
            <div class="param-row"><span class="param-name">Complexity</span><span class="param-val">{self.complexity:.1f}×</span></div>
        </div>
        
        <div id="controls">
            <button class="control-btn active" onclick="toggleRotation()">⟳ Rotation</button>
            <button class="control-btn" onclick="resetCamera()">⌖ Reset</button>
            <button class="control-btn" onclick="toggleWireframe()">◇ Wireframe</button>
            <button class="control-btn" onclick="screenshot()">📷 Capture</button>
        </div>
        
        <div id="loading">Chargement...</div>
    </div>
    
    <script type="importmap">
    {{
        "imports": {{
            "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
            "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
        }}
    }}
    </script>
    
    <script type="module">
        import * as THREE from 'three';
        import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
        
        let scene, camera, renderer, controls;
        let autoRotate = true;
        let wireframeMode = false;
        const animationCallbacks = [];
        
        function init() {{
            // Scene avec brouillard
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x050508);
            scene.fog = new THREE.FogExp2(0x050508, 0.06);
            
            // Camera
            camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.set(4, 3, 4);
            
            // Renderer haute qualite
            renderer = new THREE.WebGLRenderer({{ 
                antialias: true, 
                alpha: true,
                powerPreference: "high-performance"
            }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            renderer.toneMapping = THREE.ACESFilmicToneMapping;
            renderer.toneMappingExposure = 1.4;
            document.getElementById('canvas-container').appendChild(renderer.domElement);
            
            // Controles
            controls = new OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.04;
            controls.autoRotate = autoRotate;
            controls.autoRotateSpeed = 0.6;
            controls.minDistance = 2.5;
            controls.maxDistance = 15;
            controls.maxPolarAngle = Math.PI * 0.85;
            
            // === ECLAIRAGE CINEMATOGRAPHIQUE ===
            const ambientLight = new THREE.AmbientLight(0x202030, 0.4);
            scene.add(ambientLight);
            
            // Key light
            const keyLight = new THREE.DirectionalLight(0xffffff, 1.5);
            keyLight.position.set(5, 8, 5);
            keyLight.castShadow = true;
            keyLight.shadow.mapSize.width = 2048;
            keyLight.shadow.mapSize.height = 2048;
            scene.add(keyLight);
            
            // Fill light (couleur primaire)
            const fillLight = new THREE.DirectionalLight('{self.primary_color}', 0.8);
            fillLight.position.set(-5, 3, -3);
            scene.add(fillLight);
            
            // Back light (accent)
            const backLight = new THREE.DirectionalLight('{self.secondary_color}', 0.5);
            backLight.position.set(0, -3, -5);
            scene.add(backLight);
            
            // Rim light
            const rimLight = new THREE.DirectionalLight('{self.tertiary_color}', 0.4);
            rimLight.position.set(4, 0, -4);
            scene.add(rimLight);
            
            // Sol avec grille
            const gridHelper = new THREE.GridHelper(15, 30, '{self.primary_color}', 0x151520);
            gridHelper.position.y = -2;
            gridHelper.material.opacity = 0.25;
            gridHelper.material.transparent = true;
            scene.add(gridHelper);
            
            // Cercle de sol lumineux
            const floorGeom = new THREE.RingGeometry(0.5, 3, 64);
            const floorMat = new THREE.MeshBasicMaterial({{
                color: '{self.primary_color}',
                transparent: true,
                opacity: 0.08,
                side: THREE.DoubleSide
            }});
            const floor = new THREE.Mesh(floorGeom, floorMat);
            floor.rotation.x = -Math.PI / 2;
            floor.position.y = -1.99;
            scene.add(floor);
            
            // === GEOMETRIE AVATAR ===
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
        
        window.toggleRotation = function() {{
            autoRotate = !autoRotate;
            controls.autoRotate = autoRotate;
            event.target.classList.toggle('active', autoRotate);
        }};
        
        window.resetCamera = function() {{
            camera.position.set(4, 3, 4);
            controls.target.set(0, 0, 0);
            controls.update();
        }};
        
        window.toggleWireframe = function() {{
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
        }};
        
        window.screenshot = function() {{
            renderer.render(scene, camera);
            const link = document.createElement('a');
            link.download = 'avatar_3d_{self.avatar_id[:8]}.png';
            link.href = renderer.domElement.toDataURL('image/png');
            link.click();
        }};
        
        init();
    </script>
</body>
</html>'''


def render_avatar_threejs(avatar_data: Dict, output_path: str = None, auto_open: bool = True) -> str:
    """Fonction utilitaire pour rendre un avatar en Three.js"""
    renderer = ThreeJSAvatarRenderer(avatar_data)
    return renderer.generate_html(output_path, auto_open)
