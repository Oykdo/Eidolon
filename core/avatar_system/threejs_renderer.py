#!/usr/bin/env python3
"""
Three.js Avatar Renderer - Génération de visualisations 3D WebGL
Crée des fichiers HTML autonomes avec rendu 3D interactif
"""

import os
import json
import hashlib
import math
import webbrowser
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class AvatarMesh:
    """Données de mesh pour l'avatar"""
    vertices: List[List[float]]
    faces: List[List[int]]
    colors: List[str]
    normals: Optional[List[List[float]]] = None


class ThreeJSAvatarRenderer:
    """Générateur de visualisation Three.js pour avatars"""
    
    # Templates de géométrie Three.js
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
        """
        Initialise le renderer avec les données de l'avatar
        
        Args:
            avatar_data: Dictionnaire contenant les infos de l'avatar
                - avatar_id: ID unique
                - geometry_type: Type géométrique
                - rarity_tier: Niveau de rareté
                - rarity_score: Score de rareté
                - attributes: Attributs DNA
                - effective_power: Puissance
        """
        self.avatar_data = avatar_data
        self.avatar_id = avatar_data.get('avatar_id', 'unknown')
        self.geometry_type = avatar_data.get('geometry_type', 'quantum_sphere')
        self.rarity_tier = avatar_data.get('rarity_tier', 'common')
        self.rarity_score = avatar_data.get('rarity_score', 50)
        self.attributes = avatar_data.get('attributes', {})
        self.power = avatar_data.get('effective_power', 5000)
        
        # Générer les couleurs depuis le DNA
        self._generate_colors()
    
    def _generate_colors(self):
        """Génère la palette de couleurs depuis l'avatar ID"""
        hash_val = hashlib.sha256(self.avatar_id.encode()).hexdigest()
        
        # Couleur principale basée sur la rareté
        self.primary_color = self._get_rarity_color()
        
        # Couleurs secondaires depuis le hash
        self.secondary_color = f"#{hash_val[0:6]}"
        self.tertiary_color = f"#{hash_val[6:12]}"
        self.accent_color = f"#{hash_val[12:18]}"
        
        # Couleur d'émission (glow)
        self.emission_color = self._lighten_color(self.primary_color, 0.3)
    
    def _get_rarity_color(self) -> str:
        """Retourne la couleur basée sur la rareté"""
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
        """Éclaircit une couleur hex"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def generate_html(self, output_path: Optional[str] = None, 
                      auto_open: bool = True) -> str:
        """
        Génère le fichier HTML avec la visualisation Three.js
        
        Args:
            output_path: Chemin de sortie (auto-généré si None)
            auto_open: Ouvrir automatiquement dans le navigateur
            
        Returns:
            Chemin du fichier HTML généré
        """
        # Générer le code de géométrie spécifique
        geometry_code = self._generate_geometry_code()
        
        # Créer le HTML complet
        html_content = self._create_html_template(geometry_code)
        
        # Déterminer le chemin de sortie
        if output_path is None:
            output_dir = Path(__file__).parent.parent.parent / "avatars" / "viewers"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"avatar_{self.avatar_id[:16]}.html"
        else:
            output_path = Path(output_path)
        
        # Écrire le fichier
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Ouvrir dans le navigateur si demandé
        if auto_open:
            webbrowser.open(f'file://{output_path.absolute()}')
        
        return str(output_path)
    
    def _generate_geometry_code(self) -> str:
        """Génère le code JavaScript pour la géométrie spécifique"""
        generator_name = self.GEOMETRY_GENERATORS.get(
            self.geometry_type, 
            "_generate_quantum_sphere"
        )
        generator = getattr(self, generator_name, self._generate_quantum_sphere)
        return generator()
    
    def _generate_quantum_sphere(self) -> str:
        """Génère une sphère quantique avec particules orbitales"""
        return f'''
            // Sphère quantique principale
            const sphereGeom = new THREE.SphereGeometry(1, 64, 64);
            const sphereMat = new THREE.MeshPhysicalMaterial({{
                color: '{self.primary_color}',
                metalness: 0.3,
                roughness: 0.2,
                transparent: true,
                opacity: 0.85,
                emissive: '{self.emission_color}',
                emissiveIntensity: 0.2,
                clearcoat: 1.0,
                clearcoatRoughness: 0.1
            }});
            const sphere = new THREE.Mesh(sphereGeom, sphereMat);
            scene.add(sphere);
            
            // Anneaux orbitaux
            for (let i = 0; i < 3; i++) {{
                const ringGeom = new THREE.TorusGeometry(1.3 + i * 0.3, 0.02, 16, 100);
                const ringMat = new THREE.MeshBasicMaterial({{
                    color: '{self.secondary_color}',
                    transparent: true,
                    opacity: 0.6
                }});
                const ring = new THREE.Mesh(ringGeom, ringMat);
                ring.rotation.x = Math.PI / 2 + i * 0.3;
                ring.rotation.y = i * 0.5;
                scene.add(ring);
                
                // Animation des anneaux
                animationCallbacks.push((time) => {{
                    ring.rotation.z = time * (0.5 + i * 0.2);
                }});
            }}
            
            // Particules orbitales
            const particleCount = 50;
            const particleGeom = new THREE.BufferGeometry();
            const positions = new Float32Array(particleCount * 3);
            const colors = new Float32Array(particleCount * 3);
            
            for (let i = 0; i < particleCount; i++) {{
                const theta = Math.random() * Math.PI * 2;
                const phi = Math.random() * Math.PI;
                const r = 1.5 + Math.random() * 0.5;
                
                positions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
                positions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
                positions[i * 3 + 2] = r * Math.cos(phi);
                
                const color = new THREE.Color(i % 2 === 0 ? '{self.secondary_color}' : '{self.tertiary_color}');
                colors[i * 3] = color.r;
                colors[i * 3 + 1] = color.g;
                colors[i * 3 + 2] = color.b;
            }}
            
            particleGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            particleGeom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
            
            const particleMat = new THREE.PointsMaterial({{
                size: 0.08,
                vertexColors: true,
                transparent: true,
                opacity: 0.8
            }});
            const particles = new THREE.Points(particleGeom, particleMat);
            scene.add(particles);
            
            // Animation des particules
            animationCallbacks.push((time) => {{
                particles.rotation.y = time * 0.3;
                particles.rotation.x = Math.sin(time * 0.5) * 0.2;
            }});
            
            // Noyau lumineux
            const coreGeom = new THREE.SphereGeometry(0.15, 32, 32);
            const coreMat = new THREE.MeshBasicMaterial({{
                color: '#ffffff',
                transparent: true,
                opacity: 0.9
            }});
            const core = new THREE.Mesh(coreGeom, coreMat);
            scene.add(core);
            
            // Point light au centre
            const coreLight = new THREE.PointLight('{self.primary_color}', 2, 5);
            scene.add(coreLight);
        '''
    
    def _generate_spinor_torus(self) -> str:
        """Génère un tore spinoriel avec flux d'énergie"""
        return f'''
            // Tore principal
            const torusGeom = new THREE.TorusGeometry(1, 0.4, 32, 100);
            const torusMat = new THREE.MeshPhysicalMaterial({{
                color: '{self.primary_color}',
                metalness: 0.5,
                roughness: 0.3,
                transparent: true,
                opacity: 0.8,
                emissive: '{self.emission_color}',
                emissiveIntensity: 0.15
            }});
            const torus = new THREE.Mesh(torusGeom, torusMat);
            scene.add(torus);
            
            // Tores internes (flux spinoriel)
            for (let i = 0; i < 3; i++) {{
                const innerGeom = new THREE.TorusGeometry(0.8 - i * 0.15, 0.05, 16, 50);
                const innerMat = new THREE.MeshBasicMaterial({{
                    color: i === 0 ? '{self.secondary_color}' : '{self.tertiary_color}',
                    transparent: true,
                    opacity: 0.7 - i * 0.15
                }});
                const inner = new THREE.Mesh(innerGeom, innerMat);
                inner.rotation.x = i * 0.3;
                scene.add(inner);
                
                animationCallbacks.push((time) => {{
                    inner.rotation.z = time * (1 + i * 0.5);
                }});
            }}
            
            // Lignes de flux
            const fluxCount = 12;
            for (let i = 0; i < fluxCount; i++) {{
                const curve = new THREE.CatmullRomCurve3([
                    new THREE.Vector3(Math.cos(i / fluxCount * Math.PI * 2) * 1.4, 0, Math.sin(i / fluxCount * Math.PI * 2) * 1.4),
                    new THREE.Vector3(Math.cos(i / fluxCount * Math.PI * 2) * 0.6, 0.5, Math.sin(i / fluxCount * Math.PI * 2) * 0.6),
                    new THREE.Vector3(Math.cos(i / fluxCount * Math.PI * 2) * 1.4, 0, Math.sin(i / fluxCount * Math.PI * 2) * 1.4)
                ]);
                const tubeGeom = new THREE.TubeGeometry(curve, 20, 0.02, 8, false);
                const tubeMat = new THREE.MeshBasicMaterial({{
                    color: '{self.accent_color}',
                    transparent: true,
                    opacity: 0.5
                }});
                const tube = new THREE.Mesh(tubeGeom, tubeMat);
                scene.add(tube);
            }}
            
            // Animation du tore principal
            animationCallbacks.push((time) => {{
                torus.rotation.x = Math.sin(time * 0.5) * 0.3;
                torus.rotation.y = time * 0.2;
            }});
        '''
    
    def _generate_nexus_crystal(self) -> str:
        """Génère un cristal nexus avec facettes brillantes"""
        return f'''
            // Cristal principal (octaèdre allongé)
            const crystalGeom = new THREE.OctahedronGeometry(1, 0);
            crystalGeom.scale(1, 1.8, 1);
            
            const crystalMat = new THREE.MeshPhysicalMaterial({{
                color: '{self.primary_color}',
                metalness: 0.1,
                roughness: 0.05,
                transparent: true,
                opacity: 0.75,
                emissive: '{self.emission_color}',
                emissiveIntensity: 0.3,
                clearcoat: 1.0,
                clearcoatRoughness: 0.0,
                reflectivity: 1.0,
                ior: 2.4
            }});
            const crystal = new THREE.Mesh(crystalGeom, crystalMat);
            scene.add(crystal);
            
            // Cristaux secondaires
            for (let i = 0; i < 6; i++) {{
                const angle = (i / 6) * Math.PI * 2;
                const smallCrystal = new THREE.Mesh(
                    new THREE.OctahedronGeometry(0.3, 0),
                    new THREE.MeshPhysicalMaterial({{
                        color: i % 2 === 0 ? '{self.secondary_color}' : '{self.tertiary_color}',
                        metalness: 0.1,
                        roughness: 0.1,
                        transparent: true,
                        opacity: 0.7,
                        emissive: i % 2 === 0 ? '{self.secondary_color}' : '{self.tertiary_color}',
                        emissiveIntensity: 0.2
                    }})
                );
                smallCrystal.position.set(
                    Math.cos(angle) * 1.5,
                    Math.sin(angle) * 0.3,
                    Math.sin(angle) * 1.5
                );
                smallCrystal.scale.set(1, 1.5, 1);
                smallCrystal.rotation.z = angle;
                scene.add(smallCrystal);
                
                // Animation des petits cristaux
                animationCallbacks.push((time) => {{
                    smallCrystal.position.y = Math.sin(time * 2 + i) * 0.2;
                    smallCrystal.rotation.y = time * 0.5;
                }});
            }}
            
            // Rayons de lumière
            const rayGeom = new THREE.CylinderGeometry(0.01, 0.01, 3, 8);
            for (let i = 0; i < 8; i++) {{
                const rayMat = new THREE.MeshBasicMaterial({{
                    color: '{self.primary_color}',
                    transparent: true,
                    opacity: 0.3
                }});
                const ray = new THREE.Mesh(rayGeom, rayMat);
                ray.rotation.z = (i / 8) * Math.PI * 2;
                ray.rotation.x = Math.PI / 2;
                scene.add(ray);
            }}
            
            // Animation rotation principale
            animationCallbacks.push((time) => {{
                crystal.rotation.y = time * 0.3;
                crystal.position.y = Math.sin(time) * 0.1;
            }});
            
            // Lumière centrale
            const crystalLight = new THREE.PointLight('{self.primary_color}', 3, 8);
            scene.add(crystalLight);
        '''
    
    def _generate_bell_polyhedron(self) -> str:
        """Génère un polyèdre de Bell avec connexions quantiques"""
        return f'''
            // Icosaèdre principal
            const icoGeom = new THREE.IcosahedronGeometry(1, 0);
            const icoMat = new THREE.MeshPhysicalMaterial({{
                color: '{self.primary_color}',
                metalness: 0.4,
                roughness: 0.3,
                transparent: true,
                opacity: 0.6,
                wireframe: false,
                emissive: '{self.emission_color}',
                emissiveIntensity: 0.2
            }});
            const ico = new THREE.Mesh(icoGeom, icoMat);
            scene.add(ico);
            
            // Wireframe
            const wireGeom = new THREE.IcosahedronGeometry(1.02, 0);
            const wireMat = new THREE.MeshBasicMaterial({{
                color: '{self.secondary_color}',
                wireframe: true,
                transparent: true,
                opacity: 0.8
            }});
            const wire = new THREE.Mesh(wireGeom, wireMat);
            scene.add(wire);
            
            // Sommets lumineux
            const vertices = icoGeom.attributes.position;
            const vertexSpheres = [];
            for (let i = 0; i < vertices.count; i += 3) {{
                const sphereGeom = new THREE.SphereGeometry(0.08, 16, 16);
                const sphereMat = new THREE.MeshBasicMaterial({{
                    color: i % 2 === 0 ? '{self.secondary_color}' : '{self.tertiary_color}'
                }});
                const sphere = new THREE.Mesh(sphereGeom, sphereMat);
                sphere.position.set(
                    vertices.getX(i) * 1.05,
                    vertices.getY(i) * 1.05,
                    vertices.getZ(i) * 1.05
                );
                scene.add(sphere);
                vertexSpheres.push(sphere);
            }}
            
            // Connexions quantiques (lignes entre sommets aléatoires)
            const lineMat = new THREE.LineBasicMaterial({{
                color: '{self.accent_color}',
                transparent: true,
                opacity: 0.4
            }});
            
            for (let i = 0; i < 10; i++) {{
                const points = [];
                const idx1 = Math.floor(Math.random() * vertexSpheres.length);
                const idx2 = Math.floor(Math.random() * vertexSpheres.length);
                points.push(vertexSpheres[idx1].position);
                points.push(new THREE.Vector3(0, 0, 0));
                points.push(vertexSpheres[idx2].position);
                
                const lineGeom = new THREE.BufferGeometry().setFromPoints(points);
                const line = new THREE.Line(lineGeom, lineMat);
                scene.add(line);
            }}
            
            // Animation
            animationCallbacks.push((time) => {{
                ico.rotation.x = time * 0.2;
                ico.rotation.y = time * 0.3;
                wire.rotation.x = time * 0.2;
                wire.rotation.y = time * 0.3;
                
                vertexSpheres.forEach((s, i) => {{
                    s.scale.setScalar(1 + Math.sin(time * 3 + i) * 0.2);
                }});
            }});
        '''
    
    def _generate_clifford_lattice(self) -> str:
        """Génère une lattice de Clifford 3D"""
        return f'''
            // Grille de points 3D
            const gridSize = 5;
            const spacing = 0.5;
            const nodes = [];
            
            for (let x = -gridSize/2; x <= gridSize/2; x++) {{
                for (let y = -gridSize/2; y <= gridSize/2; y++) {{
                    for (let z = -gridSize/2; z <= gridSize/2; z++) {{
                        const dist = Math.sqrt(x*x + y*y + z*z);
                        if (dist < gridSize/2) {{
                            const nodeGeom = new THREE.BoxGeometry(0.1, 0.1, 0.1);
                            const nodeMat = new THREE.MeshPhysicalMaterial({{
                                color: (x + y + z) % 2 === 0 ? '{self.primary_color}' : '{self.secondary_color}',
                                metalness: 0.5,
                                roughness: 0.3,
                                emissive: (x + y + z) % 2 === 0 ? '{self.primary_color}' : '{self.secondary_color}',
                                emissiveIntensity: 0.3
                            }});
                            const node = new THREE.Mesh(nodeGeom, nodeMat);
                            node.position.set(x * spacing, y * spacing, z * spacing);
                            scene.add(node);
                            nodes.push({{mesh: node, x, y, z}});
                        }}
                    }}
                }}
            }}
            
            // Connexions entre noeuds adjacents
            const lineMat = new THREE.LineBasicMaterial({{
                color: '{self.tertiary_color}',
                transparent: true,
                opacity: 0.3
            }});
            
            nodes.forEach((node, i) => {{
                nodes.forEach((other, j) => {{
                    if (i < j) {{
                        const dx = Math.abs(node.x - other.x);
                        const dy = Math.abs(node.y - other.y);
                        const dz = Math.abs(node.z - other.z);
                        if (dx + dy + dz === 1) {{
                            const points = [node.mesh.position, other.mesh.position];
                            const lineGeom = new THREE.BufferGeometry().setFromPoints(points);
                            const line = new THREE.Line(lineGeom, lineMat);
                            scene.add(line);
                        }}
                    }}
                }});
            }});
            
            // Cube englobant
            const cubeGeom = new THREE.BoxGeometry(gridSize * spacing, gridSize * spacing, gridSize * spacing);
            const cubeMat = new THREE.MeshBasicMaterial({{
                color: '{self.accent_color}',
                wireframe: true,
                transparent: true,
                opacity: 0.2
            }});
            const cube = new THREE.Mesh(cubeGeom, cubeMat);
            scene.add(cube);
            
            // Animation
            animationCallbacks.push((time) => {{
                nodes.forEach((node, i) => {{
                    node.mesh.scale.setScalar(0.8 + Math.sin(time * 2 + i * 0.1) * 0.3);
                }});
                cube.rotation.x = time * 0.1;
                cube.rotation.y = time * 0.15;
            }});
        '''
    
    def _generate_entropy_fractal(self) -> str:
        """Génère une fractale entropique (arbre 3D)"""
        return f'''
            // Fonction récursive pour créer les branches
            function createBranch(startPos, direction, length, depth, parent) {{
                if (depth <= 0 || length < 0.05) return;
                
                const endPos = startPos.clone().add(direction.clone().multiplyScalar(length));
                
                // Tube pour la branche
                const curve = new THREE.LineCurve3(startPos, endPos);
                const tubeGeom = new THREE.TubeGeometry(curve, 8, length * 0.08, 8, false);
                const tubeMat = new THREE.MeshPhysicalMaterial({{
                    color: depth > 3 ? '{self.primary_color}' : (depth > 1 ? '{self.secondary_color}' : '{self.tertiary_color}'),
                    metalness: 0.2,
                    roughness: 0.5,
                    emissive: depth > 3 ? '{self.primary_color}' : '{self.secondary_color}',
                    emissiveIntensity: 0.1 * depth
                }});
                const tube = new THREE.Mesh(tubeGeom, tubeMat);
                scene.add(tube);
                
                // Feuille au bout
                if (depth <= 1) {{
                    const leafGeom = new THREE.SphereGeometry(0.05, 8, 8);
                    const leafMat = new THREE.MeshBasicMaterial({{
                        color: '{self.accent_color}',
                        transparent: true,
                        opacity: 0.8
                    }});
                    const leaf = new THREE.Mesh(leafGeom, leafMat);
                    leaf.position.copy(endPos);
                    scene.add(leaf);
                    
                    animationCallbacks.push((time) => {{
                        leaf.scale.setScalar(1 + Math.sin(time * 3 + endPos.x * 10) * 0.3);
                    }});
                }}
                
                // Créer les sous-branches
                const branchCount = 2 + Math.floor(Math.random() * 2);
                for (let i = 0; i < branchCount; i++) {{
                    const newDir = direction.clone();
                    newDir.applyAxisAngle(new THREE.Vector3(1, 0, 0), (Math.random() - 0.5) * 0.8);
                    newDir.applyAxisAngle(new THREE.Vector3(0, 0, 1), (Math.random() - 0.5) * 0.8);
                    newDir.normalize();
                    
                    createBranch(endPos, newDir, length * 0.7, depth - 1);
                }}
            }}
            
            // Créer l'arbre principal
            createBranch(
                new THREE.Vector3(0, -1.5, 0),
                new THREE.Vector3(0, 1, 0),
                0.8,
                6
            );
            
            // Ajouter des branches secondaires
            for (let i = 0; i < 3; i++) {{
                const angle = (i / 3) * Math.PI * 2;
                createBranch(
                    new THREE.Vector3(Math.cos(angle) * 0.3, -1.3, Math.sin(angle) * 0.3),
                    new THREE.Vector3(Math.cos(angle) * 0.5, 0.8, Math.sin(angle) * 0.5).normalize(),
                    0.5,
                    4
                );
            }}
        '''
    
    def _generate_7d_projection(self) -> str:
        """Génère une projection 7D"""
        return f'''
            // Créer 7 dimensions projetées
            const dimCount = 7;
            const layers = [];
            
            for (let d = 0; d < dimCount; d++) {{
                const layerGroup = new THREE.Group();
                
                // Heptagone pour chaque dimension
                const points = [];
                for (let i = 0; i < 7; i++) {{
                    const angle = (i / 7) * Math.PI * 2;
                    const r = 1.2 - d * 0.12;
                    points.push(new THREE.Vector3(
                        Math.cos(angle) * r,
                        Math.sin(angle) * r,
                        0
                    ));
                }}
                points.push(points[0].clone());
                
                const lineGeom = new THREE.BufferGeometry().setFromPoints(points);
                const lineMat = new THREE.LineBasicMaterial({{
                    color: new THREE.Color().setHSL(d / dimCount, 1, 0.5),
                    transparent: true,
                    opacity: 0.8 - d * 0.08
                }});
                const line = new THREE.Line(lineGeom, lineMat);
                layerGroup.add(line);
                
                // Noeuds aux sommets
                for (let i = 0; i < 7; i++) {{
                    const nodeGeom = new THREE.SphereGeometry(0.08 - d * 0.008, 16, 16);
                    const nodeMat = new THREE.MeshBasicMaterial({{
                        color: new THREE.Color().setHSL(d / dimCount, 1, 0.6)
                    }});
                    const node = new THREE.Mesh(nodeGeom, nodeMat);
                    node.position.copy(points[i]);
                    layerGroup.add(node);
                }}
                
                // Lignes vers le centre
                for (let i = 0; i < 7; i++) {{
                    const centerLine = new THREE.BufferGeometry().setFromPoints([
                        points[i],
                        new THREE.Vector3(0, 0, 0)
                    ]);
                    const centerLineMat = new THREE.LineBasicMaterial({{
                        color: '{self.primary_color}',
                        transparent: true,
                        opacity: 0.3
                    }});
                    layerGroup.add(new THREE.Line(centerLine, centerLineMat));
                }}
                
                layerGroup.position.z = d * 0.15 - 0.5;
                layerGroup.rotation.z = d * 0.1;
                scene.add(layerGroup);
                layers.push(layerGroup);
                
                // Animation
                animationCallbacks.push((time) => {{
                    layerGroup.rotation.z = d * 0.1 + time * (0.2 + d * 0.05);
                    layerGroup.position.z = (d * 0.15 - 0.5) + Math.sin(time + d) * 0.1;
                }});
            }}
            
            // Centre 7D
            const centerGeom = new THREE.DodecahedronGeometry(0.15, 0);
            const centerMat = new THREE.MeshPhysicalMaterial({{
                color: '{self.primary_color}',
                emissive: '{self.primary_color}',
                emissiveIntensity: 0.5,
                metalness: 0.8,
                roughness: 0.2
            }});
            const center = new THREE.Mesh(centerGeom, centerMat);
            scene.add(center);
            
            animationCallbacks.push((time) => {{
                center.rotation.x = time * 0.5;
                center.rotation.y = time * 0.7;
            }});
            
            // Texte 7D
            const loader = new THREE.FontLoader();
        '''
    
    def _generate_hybrid_form(self) -> str:
        """Génère une forme hybride complexe"""
        return f'''
            // Forme centrale (combinaison sphère + polyèdre)
            const coreGeom = new THREE.DodecahedronGeometry(0.6, 1);
            const coreMat = new THREE.MeshPhysicalMaterial({{
                color: '{self.primary_color}',
                metalness: 0.6,
                roughness: 0.2,
                transparent: true,
                opacity: 0.8,
                emissive: '{self.emission_color}',
                emissiveIntensity: 0.3
            }});
            const core = new THREE.Mesh(coreGeom, coreMat);
            scene.add(core);
            
            // Anneaux multiples
            for (let i = 0; i < 4; i++) {{
                const ringGeom = new THREE.TorusGeometry(1 + i * 0.2, 0.03, 16, 100);
                const ringMat = new THREE.MeshBasicMaterial({{
                    color: i % 2 === 0 ? '{self.secondary_color}' : '{self.tertiary_color}',
                    transparent: true,
                    opacity: 0.6 - i * 0.1
                }});
                const ring = new THREE.Mesh(ringGeom, ringMat);
                ring.rotation.x = i * Math.PI / 4;
                scene.add(ring);
                
                animationCallbacks.push((time) => {{
                    ring.rotation.z = time * (0.3 + i * 0.1);
                }});
            }}
            
            // Satellites
            const satCount = 8;
            for (let i = 0; i < satCount; i++) {{
                const satGeom = new THREE.TetrahedronGeometry(0.15, 0);
                const satMat = new THREE.MeshPhysicalMaterial({{
                    color: '{self.accent_color}',
                    metalness: 0.5,
                    roughness: 0.3,
                    emissive: '{self.accent_color}',
                    emissiveIntensity: 0.2
                }});
                const sat = new THREE.Mesh(satGeom, satMat);
                
                const angle = (i / satCount) * Math.PI * 2;
                sat.position.set(
                    Math.cos(angle) * 1.5,
                    Math.sin(angle * 2) * 0.3,
                    Math.sin(angle) * 1.5
                );
                scene.add(sat);
                
                // Lien vers le centre
                const linkGeom = new THREE.BufferGeometry().setFromPoints([
                    sat.position,
                    new THREE.Vector3(0, 0, 0)
                ]);
                const linkMat = new THREE.LineBasicMaterial({{
                    color: '{self.primary_color}',
                    transparent: true,
                    opacity: 0.3
                }});
                scene.add(new THREE.Line(linkGeom, linkMat));
                
                animationCallbacks.push((time) => {{
                    const newAngle = angle + time * 0.5;
                    sat.position.set(
                        Math.cos(newAngle) * 1.5,
                        Math.sin(time * 2 + i) * 0.3,
                        Math.sin(newAngle) * 1.5
                    );
                    sat.rotation.x = time;
                    sat.rotation.y = time * 1.5;
                }});
            }}
            
            // Animation du noyau
            animationCallbacks.push((time) => {{
                core.rotation.x = time * 0.2;
                core.rotation.y = time * 0.3;
                core.scale.setScalar(1 + Math.sin(time * 2) * 0.05);
            }});
        '''
    
    def _create_html_template(self, geometry_code: str) -> str:
        """Crée le template HTML complet avec Three.js"""
        
        # Informations de l'avatar pour l'affichage
        info_json = json.dumps({
            'id': self.avatar_id[:16] + '...',
            'type': self.geometry_type.replace('_', ' ').title(),
            'rarity': self.rarity_tier.upper(),
            'score': f"{self.rarity_score:.1f}",
            'power': f"{self.power:,.0f}"
        })
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Avatar 3D - {self.geometry_type.replace('_', ' ').title()} | Poly-Spinor Nexus 7D</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            background: linear-gradient(135deg, #0a0a1a 0%, #1a0a2a 50%, #0a1a2a 100%);
            font-family: 'Segoe UI', 'Consolas', monospace;
            color: #e0e0e0;
            overflow: hidden;
        }}
        
        #container {{
            width: 100vw;
            height: 100vh;
            position: relative;
        }}
        
        #canvas-container {{
            width: 100%;
            height: 100%;
        }}
        
        #info-panel {{
            position: absolute;
            top: 20px;
            left: 20px;
            background: rgba(10, 10, 30, 0.85);
            border: 1px solid {self.primary_color};
            border-radius: 10px;
            padding: 20px;
            min-width: 280px;
            backdrop-filter: blur(10px);
            box-shadow: 0 0 30px {self.primary_color}33;
        }}
        
        #info-panel h1 {{
            color: {self.primary_color};
            font-size: 1.4em;
            margin-bottom: 15px;
            text-shadow: 0 0 10px {self.primary_color};
        }}
        
        .info-row {{
            display: flex;
            justify-content: space-between;
            margin: 8px 0;
            padding: 5px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        
        .info-label {{
            color: #888;
            font-size: 0.9em;
        }}
        
        .info-value {{
            color: {self.secondary_color};
            font-weight: bold;
        }}
        
        .rarity-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 15px;
            background: {self.primary_color}33;
            border: 1px solid {self.primary_color};
            color: {self.primary_color};
            font-size: 0.85em;
            text-shadow: 0 0 5px {self.primary_color};
        }}
        
        #controls {{
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 10px;
        }}
        
        .control-btn {{
            background: rgba(10, 10, 30, 0.8);
            border: 1px solid {self.primary_color};
            color: {self.primary_color};
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-family: inherit;
            transition: all 0.3s;
        }}
        
        .control-btn:hover {{
            background: {self.primary_color}33;
            box-shadow: 0 0 15px {self.primary_color}55;
        }}
        
        .control-btn.active {{
            background: {self.primary_color};
            color: #000;
        }}
        
        #power-indicator {{
            position: absolute;
            top: 20px;
            right: 20px;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: radial-gradient(circle, {self.primary_color}55 0%, transparent 70%);
            border: 3px solid {self.primary_color};
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 30px {self.primary_color}55;
        }}
        
        #power-indicator .power-value {{
            font-size: 1.2em;
            font-weight: bold;
            color: {self.primary_color};
        }}
        
        #power-indicator .power-label {{
            font-size: 0.7em;
            color: #888;
        }}
        
        #loading {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: {self.primary_color};
            font-size: 1.5em;
        }}
        
        .glow {{
            animation: glow 2s ease-in-out infinite alternate;
        }}
        
        @keyframes glow {{
            from {{ text-shadow: 0 0 5px {self.primary_color}, 0 0 10px {self.primary_color}; }}
            to {{ text-shadow: 0 0 10px {self.primary_color}, 0 0 20px {self.primary_color}, 0 0 30px {self.primary_color}; }}
        }}
    </style>
</head>
<body>
    <div id="container">
        <div id="canvas-container"></div>
        
        <div id="info-panel">
            <h1 class="glow">🎭 AVATAR 3D</h1>
            <div class="info-row">
                <span class="info-label">Type</span>
                <span class="info-value">{self.geometry_type.replace('_', ' ').title()}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Rareté</span>
                <span class="rarity-badge">{self.rarity_tier.upper()}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Score</span>
                <span class="info-value">{self.rarity_score:.1f}/100</span>
            </div>
            <div class="info-row">
                <span class="info-label">ID</span>
                <span class="info-value" style="font-size:0.8em">{self.avatar_id[:16]}...</span>
            </div>
        </div>
        
        <div id="power-indicator">
            <span class="power-value">{int(self.power/1000)}K</span>
            <span class="power-label">POWER</span>
        </div>
        
        <div id="controls">
            <button class="control-btn active" onclick="toggleRotation()">⟳ Auto-Rotate</button>
            <button class="control-btn" onclick="resetCamera()">⌖ Reset View</button>
            <button class="control-btn" onclick="toggleWireframe()">◇ Wireframe</button>
            <button class="control-btn" onclick="screenshot()">📷 Screenshot</button>
        </div>
        
        <div id="loading">Chargement de l'avatar 3D...</div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
    
    <script>
        let scene, camera, renderer, controls;
        let autoRotate = true;
        let wireframeMode = false;
        const animationCallbacks = [];
        
        function init() {{
            // Scene
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x0a0a1a);
            scene.fog = new THREE.Fog(0x0a0a1a, 5, 15);
            
            // Camera
            camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.set(3, 2, 3);
            
            // Renderer
            renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            renderer.toneMapping = THREE.ACESFilmicToneMapping;
            renderer.toneMappingExposure = 1.2;
            document.getElementById('canvas-container').appendChild(renderer.domElement);
            
            // Controls
            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.autoRotate = autoRotate;
            controls.autoRotateSpeed = 1.0;
            controls.minDistance = 2;
            controls.maxDistance = 10;
            
            // Lighting
            const ambientLight = new THREE.AmbientLight(0x404040, 0.5);
            scene.add(ambientLight);
            
            const mainLight = new THREE.DirectionalLight(0xffffff, 1);
            mainLight.position.set(5, 5, 5);
            mainLight.castShadow = true;
            scene.add(mainLight);
            
            const fillLight = new THREE.DirectionalLight('{self.primary_color}', 0.5);
            fillLight.position.set(-5, 0, -5);
            scene.add(fillLight);
            
            const backLight = new THREE.DirectionalLight('{self.secondary_color}', 0.3);
            backLight.position.set(0, -5, 0);
            scene.add(backLight);
            
            // Grille de sol
            const gridHelper = new THREE.GridHelper(10, 20, '{self.primary_color}', 0x222244);
            gridHelper.position.y = -2;
            scene.add(gridHelper);
            
            // Créer la géométrie de l'avatar
            {geometry_code}
            
            // Masquer le loading
            document.getElementById('loading').style.display = 'none';
            
            // Event listeners
            window.addEventListener('resize', onWindowResize);
            
            // Animation loop
            animate();
        }}
        
        function animate() {{
            requestAnimationFrame(animate);
            
            const time = performance.now() * 0.001;
            
            // Exécuter les callbacks d'animation
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
            document.querySelector('.control-btn').classList.toggle('active', autoRotate);
        }}
        
        function resetCamera() {{
            camera.position.set(3, 2, 3);
            controls.target.set(0, 0, 0);
            controls.update();
        }}
        
        function toggleWireframe() {{
            wireframeMode = !wireframeMode;
            scene.traverse((child) => {{
                if (child.isMesh && child.material) {{
                    if (Array.isArray(child.material)) {{
                        child.material.forEach(m => m.wireframe = wireframeMode);
                    }} else {{
                        child.material.wireframe = wireframeMode;
                    }}
                }}
            }});
        }}
        
        function screenshot() {{
            renderer.render(scene, camera);
            const link = document.createElement('a');
            link.download = 'avatar_3d_{self.avatar_id[:8]}.png';
            link.href = renderer.domElement.toDataURL('image/png');
            link.click();
        }}
        
        // Initialisation
        init();
    </script>
</body>
</html>'''


def render_avatar_threejs(avatar_data: Dict, output_path: str = None, 
                          auto_open: bool = True) -> str:
    """
    Fonction utilitaire pour rendre un avatar en Three.js
    
    Args:
        avatar_data: Données de l'avatar
        output_path: Chemin de sortie (optionnel)
        auto_open: Ouvrir dans le navigateur
        
    Returns:
        Chemin du fichier HTML généré
    """
    renderer = ThreeJSAvatarRenderer(avatar_data)
    return renderer.generate_html(output_path, auto_open)


if __name__ == "__main__":
    # Test avec un avatar exemple
    test_avatar = {
        'avatar_id': 'test_avatar_12345678abcdef',
        'geometry_type': 'nexus_crystal',
        'rarity_tier': 'legendary',
        'rarity_score': 78.5,
        'effective_power': 12500,
        'attributes': {
            'quantum_entropy': 85.2,
            'dimensional_sync': 72.1
        }
    }
    
    path = render_avatar_threejs(test_avatar)
    print(f"Avatar rendu: {path}")
