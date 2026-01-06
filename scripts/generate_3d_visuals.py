#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        GENERATEUR D'IMAGES 3D - Poly-Spinor Nexus 7D                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Genere des visualisations 3D ALEATOIRES pour:                               ║
║  - Artefacts avec formes/couleurs/structures variees                         ║
║  - Pierres Philosophales avec auras uniques                                  ║
║  - Gemmes cristallines multi-formes                                          ║
║  - Vue globale du Nexus                                                      ║
║                                                                              ║
║  Chaque objet a une apparence UNIQUE basee sur son ID                        ║
║  Les caracteristiques (rarete, puissance) sont preservees                    ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import json
import math
import hashlib
import struct
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("[WARN] PIL/Pillow not installed. Install with: pip install Pillow")


# ============================================================================
# PALETTES DE COULEURS ALEATOIRES
# ============================================================================

COLOR_PALETTES = [
    # Cyber Neon
    [(0, 255, 136), (255, 0, 136), (0, 136, 255), (255, 255, 0)],
    # Dark Void
    [(75, 0, 130), (138, 43, 226), (148, 0, 211), (186, 85, 211)],
    # Fire Storm
    [(255, 69, 0), (255, 140, 0), (255, 215, 0), (255, 99, 71)],
    # Ice Crystal
    [(0, 191, 255), (135, 206, 250), (176, 224, 230), (240, 248, 255)],
    # Nature
    [(0, 128, 0), (34, 139, 34), (144, 238, 144), (0, 255, 127)],
    # Royal
    [(128, 0, 128), (255, 215, 0), (75, 0, 130), (238, 130, 238)],
    # Blood Moon
    [(139, 0, 0), (178, 34, 34), (220, 20, 60), (255, 0, 0)],
    # Ocean Depths
    [(0, 0, 139), (0, 0, 205), (65, 105, 225), (100, 149, 237)],
    # Cosmic
    [(255, 20, 147), (0, 255, 255), (255, 255, 255), (148, 0, 211)],
    # Ancient Gold
    [(184, 134, 11), (218, 165, 32), (255, 215, 0), (255, 223, 0)],
]

CRYSTAL_SHAPES = [
    "diamond",      # Double pyramide classique
    "obelisk",      # Tour pointue
    "cluster",      # Groupe de cristaux
    "sphere",       # Sphere facettee
    "star",         # Etoile 3D
    "hexagon",      # Prisme hexagonal
    "spiral",       # Spirale cristalline
    "fractal",      # Structure fractale
]

AURA_STYLES = [
    "radial",       # Cercles concentriques
    "spiral",       # Spirale d'energie
    "rays",         # Rayons de lumiere
    "particles",    # Nuage de particules
    "rings",        # Anneaux orbitaux
    "waves",        # Ondes d'energie
    "flames",       # Flammes etherees
    "lightning",    # Eclairs
]

BACKGROUND_STYLES = [
    "starfield",    # Champ d'etoiles
    "nebula",       # Nebuleuse coloree
    "void",         # Noir profond
    "grid",         # Grille holographique
    "vortex",       # Vortex spatial
    "matrix",       # Style matrice
]


# ============================================================================
# CONFIGURATION DES COULEURS DE BASE
# ============================================================================

RARITY_COLORS = {
    "common": (200, 200, 200),
    "uncommon": (0, 200, 0),
    "rare": (0, 136, 255),
    "epic": (170, 0, 255),
    "legendary": (255, 136, 0),
    "mythic": (255, 0, 255),
    "transcendent": (0, 255, 255),
    "primordial": (255, 215, 0),
}

ESSENCE_COLORS = {
    "void": (26, 0, 51),
    "quantum": (0, 255, 136),
    "temporal": (255, 170, 0),
    "spatial": (0, 170, 255),
    "entropic": (255, 51, 102),
    "harmonic": (170, 85, 255),
    "celestial": (255, 255, 170),
}

GEM_COLORS = {
    "cracked": (68, 68, 68),
    "flawed": (102, 102, 102),
    "common": (136, 136, 136),
    "polished": (0, 170, 0),
    "refined": (0, 204, 204),
    "pristine": (136, 85, 255),
    "perfect": (255, 136, 0),
    "flawless": (255, 0, 255),
    "transcendent": (0, 255, 255),
    "divine": (255, 215, 0),
}


# ============================================================================
# GENERATEUR RNG DETERMINISTE AVANCE
# ============================================================================

class DeterministicRNG:
    """Generateur pseudo-aleatoire deterministe base sur un seed"""
    
    def __init__(self, seed: str):
        self.seed = hashlib.sha256(seed.encode()).digest()
        self.index = 0
    
    def next_float(self) -> float:
        """Retourne un float entre 0 et 1"""
        h = hashlib.sha256(self.seed + struct.pack('I', self.index)).digest()
        self.index += 1
        return struct.unpack('I', h[:4])[0] / 0xFFFFFFFF
    
    def next_int(self, min_val: int, max_val: int) -> int:
        """Retourne un entier dans la plage"""
        return min_val + int(self.next_float() * (max_val - min_val + 1))
    
    def next_bool(self, probability: float = 0.5) -> bool:
        """Retourne True avec la probabilite donnee"""
        return self.next_float() < probability
    
    def choice(self, items: list):
        """Choisit un element aleatoire"""
        return items[self.next_int(0, len(items) - 1)]
    
    def shuffle(self, items: list) -> list:
        """Melange une liste"""
        result = items.copy()
        for i in range(len(result) - 1, 0, -1):
            j = self.next_int(0, i)
            result[i], result[j] = result[j], result[i]
        return result
    
    def next_color(self) -> Tuple[int, int, int]:
        """Genere une couleur aleatoire"""
        return (self.next_int(0, 255), self.next_int(0, 255), self.next_int(0, 255))
    
    def next_color_variation(self, base_color: Tuple[int, int, int], 
                            variation: int = 30) -> Tuple[int, int, int]:
        """Variation aleatoire d'une couleur"""
        return tuple(
            max(0, min(255, c + self.next_int(-variation, variation)))
            for c in base_color
        )
    
    def next_palette(self) -> List[Tuple[int, int, int]]:
        """Choisit une palette aleatoire"""
        return self.choice(COLOR_PALETTES)
    
    def blend_colors(self, c1: Tuple[int, int, int], c2: Tuple[int, int, int], 
                    factor: float) -> Tuple[int, int, int]:
        """Melange deux couleurs"""
        return tuple(int(c1[i] * (1 - factor) + c2[i] * factor) for i in range(3))


# ============================================================================
# FONCTIONS DE DESSIN AVANCEES
# ============================================================================

def draw_glow(draw: ImageDraw, center: Tuple[int, int], radius: int,
              color: Tuple[int, int, int], intensity: float = 1.0):
    """Dessine un effet de lueur/glow"""
    for r in range(radius, 0, -3):
        alpha = int(255 * (r / radius) * intensity * 0.25)
        draw.ellipse([
            center[0] - r, center[1] - r,
            center[0] + r, center[1] + r
        ], fill=(*color, alpha))


def draw_spiral_aura(draw: ImageDraw, center: Tuple[int, int], radius: int,
                    color: Tuple[int, int, int], rng: DeterministicRNG, arms: int = 5):
    """Dessine une aura en spirale"""
    cx, cy = center
    rotation = rng.next_float() * 2 * math.pi
    
    for arm in range(arms):
        arm_angle = 2 * math.pi * arm / arms + rotation
        for i in range(50):
            t = i / 50
            r = radius * t
            angle = arm_angle + t * 4 * math.pi
            
            x = cx + int(r * math.cos(angle))
            y = cy + int(r * math.sin(angle))
            
            size = int(3 + (1 - t) * 8)
            alpha = int(200 * (1 - t))
            
            draw.ellipse([x - size, y - size, x + size, y + size],
                        fill=(*rng.next_color_variation(color, 20), alpha))


def draw_ray_aura(draw: ImageDraw, center: Tuple[int, int], radius: int,
                 color: Tuple[int, int, int], rng: DeterministicRNG, rays: int = 12):
    """Dessine des rayons de lumiere"""
    cx, cy = center
    rotation = rng.next_float() * 2 * math.pi
    
    for i in range(rays):
        angle = 2 * math.pi * i / rays + rotation
        length = radius * (0.6 + rng.next_float() * 0.4)
        width = 2 + rng.next_int(0, 5)
        
        end_x = cx + int(length * math.cos(angle))
        end_y = cy + int(length * math.sin(angle))
        
        # Gradient le long du rayon
        for j in range(int(length), 0, -5):
            t = j / length
            px = cx + int(j * math.cos(angle))
            py = cy + int(j * math.sin(angle))
            alpha = int(150 * (1 - t))
            
            draw.ellipse([px - width, py - width, px + width, py + width],
                        fill=(*color, alpha))


def draw_particle_cloud(draw: ImageDraw, center: Tuple[int, int], radius: int,
                       color: Tuple[int, int, int], rng: DeterministicRNG, count: int = 100):
    """Dessine un nuage de particules"""
    cx, cy = center
    
    for _ in range(count):
        angle = rng.next_float() * 2 * math.pi
        dist = rng.next_float() ** 0.5 * radius  # Distribution plus dense au centre
        
        x = cx + int(dist * math.cos(angle))
        y = cy + int(dist * math.sin(angle))
        
        size = 1 + int(rng.next_float() * 4)
        alpha = int(50 + rng.next_float() * 200 * (1 - dist / radius))
        
        particle_color = rng.next_color_variation(color, 40)
        draw.ellipse([x - size, y - size, x + size, y + size],
                    fill=(*particle_color, alpha))


def draw_wave_aura(draw: ImageDraw, center: Tuple[int, int], radius: int,
                  color: Tuple[int, int, int], rng: DeterministicRNG, waves: int = 5):
    """Dessine des ondes concentriques"""
    cx, cy = center
    
    for w in range(waves):
        r = radius * (w + 1) / waves
        distortion = rng.next_float() * 0.3
        
        points = []
        for i in range(60):
            angle = 2 * math.pi * i / 60
            wave_r = r * (1 + math.sin(angle * 8) * distortion)
            x = cx + int(wave_r * math.cos(angle))
            y = cy + int(wave_r * math.sin(angle))
            points.append((x, y))
        
        alpha = int(150 * (1 - w / waves))
        if len(points) > 2:
            draw.polygon(points, outline=(*color, alpha))


def draw_lightning(draw: ImageDraw, start: Tuple[int, int], end: Tuple[int, int],
                  color: Tuple[int, int, int], rng: DeterministicRNG, branches: int = 3):
    """Dessine un eclair"""
    points = [start]
    
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    
    segments = 8
    for i in range(1, segments):
        t = i / segments
        x = start[0] + dx * t + rng.next_int(-30, 30)
        y = start[1] + dy * t + rng.next_int(-30, 30)
        points.append((x, y))
    
    points.append(end)
    
    # Ligne principale
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=(*color, 255), width=2)
        draw.line([points[i], points[i + 1]], fill=(255, 255, 255, 150), width=1)
    
    # Branches
    for _ in range(branches):
        idx = rng.next_int(1, len(points) - 2)
        branch_end = (
            points[idx][0] + rng.next_int(-50, 50),
            points[idx][1] + rng.next_int(-50, 50)
        )
        draw.line([points[idx], branch_end], fill=(*color, 150), width=1)


# ============================================================================
# FORMES DE CRISTAUX
# ============================================================================

def draw_diamond_crystal(img: Image, center: Tuple[int, int], size: int,
                        color: Tuple[int, int, int], rng: DeterministicRNG):
    """Cristal en forme de diamant"""
    draw = ImageDraw.Draw(img, 'RGBA')
    cx, cy = center
    
    # Variation aleatoire des proportions
    top_height = size * (0.8 + rng.next_float() * 0.4)
    bottom_height = size * (0.6 + rng.next_float() * 0.4)
    width_factor = 0.5 + rng.next_float() * 0.3
    
    facets = rng.next_int(6, 12)
    
    top = (cx, int(cy - top_height))
    bottom = (cx, int(cy + bottom_height))
    
    mid_points = []
    for i in range(facets):
        angle = 2 * math.pi * i / facets + rng.next_float() * 0.2
        px = cx + int(size * width_factor * math.cos(angle))
        py = cy + int(size * 0.2 * math.sin(angle))
        mid_points.append((px, py))
    
    # Facettes superieures
    for i in range(facets):
        next_i = (i + 1) % facets
        shade = 0.4 + 0.6 * abs(math.cos(2 * math.pi * i / facets))
        shaded_color = tuple(int(c * shade) for c in color)
        points = [top, mid_points[i], mid_points[next_i]]
        draw.polygon(points, fill=(*shaded_color, 220), outline=(255, 255, 255, 80))
    
    # Facettes inferieures
    for i in range(facets):
        next_i = (i + 1) % facets
        shade = 0.2 + 0.4 * abs(math.cos(2 * math.pi * i / facets))
        shaded_color = tuple(int(c * shade) for c in color)
        points = [bottom, mid_points[next_i], mid_points[i]]
        draw.polygon(points, fill=(*shaded_color, 200), outline=(255, 255, 255, 60))
    
    # Reflet
    hl_size = int(size * 0.15)
    hl_x = cx - int(size * 0.2)
    hl_y = cy - int(size * 0.3)
    draw.ellipse([hl_x - hl_size, hl_y - hl_size, hl_x + hl_size, hl_y + hl_size],
                fill=(255, 255, 255, 120))


def draw_obelisk_crystal(img: Image, center: Tuple[int, int], size: int,
                        color: Tuple[int, int, int], rng: DeterministicRNG):
    """Cristal en forme d'obelisque"""
    draw = ImageDraw.Draw(img, 'RGBA')
    cx, cy = center
    
    height = size * (1.5 + rng.next_float() * 0.5)
    width = size * (0.3 + rng.next_float() * 0.2)
    
    # Base
    base_y = cy + int(height * 0.4)
    top_y = cy - int(height * 0.6)
    tip_y = cy - int(height * 0.8)
    
    # 4 faces
    points_front = [
        (cx - width, base_y),
        (cx + width, base_y),
        (cx + width * 0.8, top_y),
        (cx - width * 0.8, top_y)
    ]
    
    points_tip = [
        (cx - width * 0.8, top_y),
        (cx + width * 0.8, top_y),
        (cx, tip_y)
    ]
    
    # Dessiner
    shade1 = 0.7 + rng.next_float() * 0.3
    shade2 = 0.5 + rng.next_float() * 0.2
    
    draw.polygon(points_front, fill=(*[int(c * shade1) for c in color], 220),
                outline=(255, 255, 255, 80))
    draw.polygon(points_tip, fill=(*[int(c * shade2) for c in color], 240),
                outline=(255, 255, 255, 100))
    
    # Lignes de detail
    for i in range(3):
        y = base_y - int((base_y - top_y) * (i + 1) / 4)
        draw.line([(cx - width * 0.9, y), (cx + width * 0.9, y)],
                 fill=(255, 255, 255, 40), width=1)


def draw_cluster_crystal(img: Image, center: Tuple[int, int], size: int,
                        color: Tuple[int, int, int], rng: DeterministicRNG):
    """Groupe de cristaux"""
    count = rng.next_int(4, 8)
    
    for i in range(count):
        # Position aleatoire autour du centre
        angle = 2 * math.pi * i / count + rng.next_float() * 0.5
        dist = size * 0.3 * rng.next_float()
        
        cx = center[0] + int(dist * math.cos(angle))
        cy = center[1] + int(dist * math.sin(angle))
        
        # Taille aleatoire
        crystal_size = int(size * (0.4 + rng.next_float() * 0.6))
        
        # Couleur variee
        crystal_color = rng.next_color_variation(color, 30)
        
        # Dessiner un petit diamant
        draw_diamond_crystal(img, (cx, cy), crystal_size, crystal_color, rng)


def draw_star_crystal(img: Image, center: Tuple[int, int], size: int,
                     color: Tuple[int, int, int], rng: DeterministicRNG):
    """Cristal en etoile"""
    draw = ImageDraw.Draw(img, 'RGBA')
    cx, cy = center
    
    points_count = rng.next_int(5, 8)
    inner_ratio = 0.3 + rng.next_float() * 0.2
    rotation = rng.next_float() * 2 * math.pi
    
    points = []
    for i in range(points_count * 2):
        angle = math.pi * i / points_count + rotation
        if i % 2 == 0:
            r = size
        else:
            r = size * inner_ratio
        
        x = cx + int(r * math.cos(angle))
        y = cy + int(r * math.sin(angle))
        points.append((x, y))
    
    # Gradient de couleur
    for layer in range(3, 0, -1):
        scale = layer / 3
        layer_points = [
            (cx + int((p[0] - cx) * scale), cy + int((p[1] - cy) * scale))
            for p in points
        ]
        shade = 0.3 + 0.7 * scale
        layer_color = tuple(int(c * shade) for c in color)
        alpha = int(150 + 100 * scale)
        draw.polygon(layer_points, fill=(*layer_color, alpha))
    
    # Coeur brillant
    draw.ellipse([cx - size//4, cy - size//4, cx + size//4, cy + size//4],
                fill=(*color, 200))
    draw.ellipse([cx - size//8, cy - size//8, cx + size//8, cy + size//8],
                fill=(255, 255, 255, 150))


def draw_spiral_crystal(img: Image, center: Tuple[int, int], size: int,
                       color: Tuple[int, int, int], rng: DeterministicRNG):
    """Cristal en spirale"""
    draw = ImageDraw.Draw(img, 'RGBA')
    cx, cy = center
    
    turns = 2 + rng.next_float() * 2
    direction = 1 if rng.next_bool() else -1
    
    points = []
    for i in range(100):
        t = i / 100
        angle = t * turns * 2 * math.pi * direction
        r = size * t
        
        x = cx + int(r * math.cos(angle))
        y = cy + int(r * math.sin(angle))
        
        width = int(5 + 15 * t)
        shade = 0.5 + 0.5 * t
        alpha = int(100 + 155 * t)
        
        draw.ellipse([x - width, y - width, x + width, y + width],
                    fill=(*[int(c * shade) for c in color], alpha))
    
    # Centre lumineux
    draw_glow(draw, center, size // 3, color, 0.8)


# ============================================================================
# FONDS ALEATOIRES
# ============================================================================

def draw_starfield_bg(draw: ImageDraw, width: int, height: int, rng: DeterministicRNG):
    """Fond etoile"""
    for _ in range(300):
        x = rng.next_int(0, width)
        y = rng.next_int(0, height)
        size = rng.next_int(1, 3)
        brightness = rng.next_int(50, 255)
        
        draw.ellipse([x - size, y - size, x + size, y + size],
                    fill=(brightness, brightness, brightness, brightness))


def draw_nebula_bg(draw: ImageDraw, width: int, height: int, rng: DeterministicRNG):
    """Fond nebuleuse"""
    palette = rng.next_palette()
    
    # Plusieurs nuages
    for _ in range(5):
        cx = rng.next_int(0, width)
        cy = rng.next_int(0, height)
        radius = rng.next_int(200, 500)
        color = rng.choice(palette)
        
        for r in range(radius, 0, -10):
            alpha = int(30 * (r / radius))
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                        fill=(*color, alpha))
    
    # Etoiles par dessus
    for _ in range(100):
        x = rng.next_int(0, width)
        y = rng.next_int(0, height)
        draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(255, 255, 255, 200))


def draw_void_bg(draw: ImageDraw, width: int, height: int, rng: DeterministicRNG):
    """Fond void avec gradient"""
    # Gradient radial du centre
    cx, cy = width // 2, height // 2
    max_dist = math.sqrt(cx ** 2 + cy ** 2)
    
    for r in range(int(max_dist), 0, -20):
        t = r / max_dist
        brightness = int(10 + 5 * t)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                    fill=(brightness, brightness, brightness + 5, 255))


def draw_grid_bg(draw: ImageDraw, width: int, height: int, rng: DeterministicRNG):
    """Fond grille holographique"""
    color = rng.choice(rng.next_palette())
    spacing = rng.next_int(30, 60)
    
    # Lignes verticales
    for x in range(0, width, spacing):
        alpha = 20 + rng.next_int(0, 30)
        draw.line([(x, 0), (x, height)], fill=(*color, alpha), width=1)
    
    # Lignes horizontales
    for y in range(0, height, spacing):
        alpha = 20 + rng.next_int(0, 30)
        draw.line([(0, y), (width, y)], fill=(*color, alpha), width=1)
    
    # Points aux intersections
    for x in range(0, width, spacing):
        for y in range(0, height, spacing):
            if rng.next_bool(0.3):
                draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(*color, 150))


def draw_vortex_bg(draw: ImageDraw, width: int, height: int, rng: DeterministicRNG):
    """Fond vortex"""
    cx, cy = width // 2, height // 2
    color = rng.choice(rng.next_palette())
    
    arms = rng.next_int(3, 6)
    
    for arm in range(arms):
        base_angle = 2 * math.pi * arm / arms
        
        for i in range(100):
            t = i / 100
            r = min(width, height) * 0.5 * t
            angle = base_angle + t * 3 * math.pi
            
            x = cx + int(r * math.cos(angle))
            y = cy + int(r * math.sin(angle))
            
            size = int(2 + 10 * (1 - t))
            alpha = int(100 * (1 - t))
            
            draw.ellipse([x - size, y - size, x + size, y + size],
                        fill=(*color, alpha))


# ============================================================================
# GENERATEUR D'ARTEFACT
# ============================================================================

class ArtifactImageGenerator:
    """Genere une image 3D unique d'un artefact"""
    
    def __init__(self, width: int = 1024, height: int = 1024):
        self.width = width
        self.height = height
        self.output_dir = Path(__file__).parent.parent / "visuals" / "artifacts"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, artifact_data: dict) -> str:
        """Genere l'image de l'artefact avec apparence aleatoire"""
        if not HAS_PIL:
            return "PIL required"
        
        # Extraire les donnees
        name = artifact_data.get('name', 'Unknown Artifact')
        rarity = artifact_data.get('rarity', 'common')
        artifact_id = artifact_data.get('artifact_id', 'unknown')
        stats = artifact_data.get('stats', {})
        power = stats.get('effective_power', 0)
        glyph_array = artifact_data.get('glyph_array', {})
        
        # RNG deterministe base sur l'ID
        rng = DeterministicRNG(artifact_id)
        
        # Choisir les styles ALEATOIRES
        crystal_shape = rng.choice(CRYSTAL_SHAPES)
        aura_style = rng.choice(AURA_STYLES)
        bg_style = rng.choice(BACKGROUND_STYLES)
        palette = rng.next_palette()
        
        # Couleur de base (influencee par rarete mais variee)
        base_color = RARITY_COLORS.get(rarity, (200, 200, 200))
        main_color = rng.next_color_variation(base_color, 50)
        accent_color = rng.choice(palette)
        
        # Creer l'image
        img = Image.new('RGBA', (self.width, self.height), (5, 5, 15, 255))
        draw = ImageDraw.Draw(img, 'RGBA')
        
        cx, cy = self.width // 2, self.height // 2
        
        # 1. FOND ALEATOIRE
        bg_funcs = {
            "starfield": draw_starfield_bg,
            "nebula": draw_nebula_bg,
            "void": draw_void_bg,
            "grid": draw_grid_bg,
            "vortex": draw_vortex_bg,
            "matrix": draw_grid_bg,
        }
        bg_funcs.get(bg_style, draw_starfield_bg)(draw, self.width, self.height, rng)
        
        # 2. AURA ALEATOIRE
        aura_radius = 250 + rng.next_int(0, 100)
        
        if aura_style == "radial":
            draw_glow(draw, (cx, cy), aura_radius, main_color, 0.4)
        elif aura_style == "spiral":
            draw_spiral_aura(draw, (cx, cy), aura_radius, main_color, rng)
        elif aura_style == "rays":
            draw_ray_aura(draw, (cx, cy), aura_radius, main_color, rng)
        elif aura_style == "particles":
            draw_particle_cloud(draw, (cx, cy), aura_radius, main_color, rng, 200)
        elif aura_style == "rings":
            for i in range(rng.next_int(3, 6)):
                r = 100 + i * 50
                self._draw_orbital_ring(draw, (cx, cy), r, accent_color, rng)
        elif aura_style == "waves":
            draw_wave_aura(draw, (cx, cy), aura_radius, main_color, rng)
        elif aura_style == "flames":
            self._draw_flames(draw, (cx, cy), aura_radius, main_color, rng)
        elif aura_style == "lightning":
            for _ in range(rng.next_int(3, 8)):
                angle = rng.next_float() * 2 * math.pi
                end = (
                    cx + int(aura_radius * math.cos(angle)),
                    cy + int(aura_radius * math.sin(angle))
                )
                draw_lightning(draw, (cx, cy), end, accent_color, rng)
        
        # 3. GLYPHES (positions et styles aleatoires)
        glyphs = glyph_array.get('glyphs', [])
        glyph_count = min(len(glyphs), 7) if glyphs else 7
        glyph_distance = 150 + rng.next_int(0, 50)
        glyph_rotation = rng.next_float() * 2 * math.pi
        
        for i in range(glyph_count):
            angle = 2 * math.pi * i / glyph_count + glyph_rotation
            # Ajouter variation a la distance
            dist = glyph_distance + rng.next_int(-20, 20)
            
            gx = cx + int(dist * math.cos(angle))
            gy = cy + int(dist * math.sin(angle))
            
            # Couleur du glyphe
            if i < len(glyphs):
                glyph_type = glyphs[i].get('glyph_type', 'void').replace('glyph_', '')
                glyph_color = ESSENCE_COLORS.get(glyph_type, rng.next_color())
            else:
                glyph_color = rng.choice(palette)
            
            glyph_color = rng.next_color_variation(glyph_color, 30)
            
            # Connexion avec style aleatoire
            if rng.next_bool(0.7):
                self._draw_connection(draw, (cx, cy), (gx, gy), glyph_color, rng)
            
            # Glyphe avec taille aleatoire
            glyph_size = 25 + rng.next_int(0, 20)
            self._draw_glyph(draw, (gx, gy), glyph_size, glyph_color, rng)
            
            # Gemmes autour (nombre aleatoire)
            if i < len(glyphs):
                gems = glyphs[i].get('gems', [])
                gem_count = min(len(gems), rng.next_int(2, 4))
                for j in range(gem_count):
                    gem_angle = angle + (j - gem_count/2) * 0.4 + rng.next_float() * 0.2
                    gem_dist = dist + 40 + rng.next_int(0, 20)
                    
                    gem_x = cx + int(gem_dist * math.cos(gem_angle))
                    gem_y = cy + int(gem_dist * math.sin(gem_angle))
                    
                    gem_color = rng.choice(palette)
                    gem_size = 5 + rng.next_int(0, 8)
                    
                    draw.ellipse([gem_x - gem_size, gem_y - gem_size,
                                 gem_x + gem_size, gem_y + gem_size],
                                fill=(*gem_color, 200))
        
        # 4. CRISTAL CENTRAL (forme aleatoire)
        core_size = 60 + rng.next_int(0, 40)
        
        crystal_funcs = {
            "diamond": draw_diamond_crystal,
            "obelisk": draw_obelisk_crystal,
            "cluster": draw_cluster_crystal,
            "sphere": lambda img, c, s, col, r: self._draw_sphere(img, c, s, col, r),
            "star": draw_star_crystal,
            "hexagon": draw_diamond_crystal,
            "spiral": draw_spiral_crystal,
            "fractal": draw_cluster_crystal,
        }
        
        crystal_funcs.get(crystal_shape, draw_diamond_crystal)(
            img, (cx, cy), core_size, main_color, rng
        )
        
        # 5. EFFETS ADDITIONNELS ALEATOIRES
        if rng.next_bool(0.5):
            draw_particle_cloud(draw, (cx, cy), 300, accent_color, rng, 50)
        
        if rng.next_bool(0.3):
            for _ in range(rng.next_int(2, 5)):
                angle = rng.next_float() * 2 * math.pi
                end = (cx + int(200 * math.cos(angle)), cy + int(200 * math.sin(angle)))
                draw_lightning(draw, (cx, cy), end, (255, 255, 255), rng, 2)
        
        # 6. TEXTE
        self._draw_text(draw, name, rarity, power, crystal_shape, aura_style)
        
        # Sauvegarder
        filename = f"artifact_{artifact_id[:12]}.png"
        filepath = self.output_dir / filename
        img.save(filepath, 'PNG')
        
        return str(filepath)
    
    def _draw_orbital_ring(self, draw: ImageDraw, center: Tuple[int, int],
                          radius: int, color: Tuple[int, int, int], rng: DeterministicRNG):
        """Anneau orbital avec variation"""
        cx, cy = center
        tilt = 0.2 + rng.next_float() * 0.4
        rotation = rng.next_float() * math.pi
        
        points = []
        for i in range(60):
            angle = 2 * math.pi * i / 60 + rotation
            x = cx + int(radius * math.cos(angle))
            y = cy + int(radius * tilt * math.sin(angle))
            points.append((x, y))
        
        for i in range(len(points)):
            draw.ellipse([points[i][0] - 2, points[i][1] - 2,
                         points[i][0] + 2, points[i][1] + 2],
                        fill=(*color, 150))
    
    def _draw_flames(self, draw: ImageDraw, center: Tuple[int, int],
                    radius: int, color: Tuple[int, int, int], rng: DeterministicRNG):
        """Flammes etherees"""
        cx, cy = center
        
        for _ in range(30):
            angle = rng.next_float() * 2 * math.pi
            height = radius * (0.5 + rng.next_float() * 0.5)
            width = 10 + rng.next_int(0, 20)
            
            base_x = cx + int(radius * 0.3 * math.cos(angle))
            base_y = cy + int(radius * 0.3 * math.sin(angle))
            
            for h in range(int(height), 0, -5):
                t = h / height
                fx = base_x + rng.next_int(-width//2, width//2) * (1 - t)
                fy = base_y - h
                
                size = int(width * (1 - t))
                alpha = int(150 * (1 - t))
                
                flame_color = rng.next_color_variation(color, 30)
                draw.ellipse([fx - size, fy - size, fx + size, fy + size],
                            fill=(*flame_color, alpha))
    
    def _draw_connection(self, draw: ImageDraw, start: Tuple[int, int],
                        end: Tuple[int, int], color: Tuple[int, int, int],
                        rng: DeterministicRNG):
        """Connexion avec style aleatoire"""
        style = rng.next_int(0, 3)
        
        if style == 0:  # Ligne simple avec glow
            draw.line([start, end], fill=(*color, 50), width=5)
            draw.line([start, end], fill=(*color, 150), width=2)
        elif style == 1:  # Pointilles
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            dist = math.sqrt(dx**2 + dy**2)
            for i in range(0, int(dist), 10):
                t = i / dist
                x = int(start[0] + dx * t)
                y = int(start[1] + dy * t)
                draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(*color, 150))
        elif style == 2:  # Courbe
            mid_x = (start[0] + end[0]) // 2 + rng.next_int(-30, 30)
            mid_y = (start[1] + end[1]) // 2 + rng.next_int(-30, 30)
            draw.line([start, (mid_x, mid_y)], fill=(*color, 100), width=2)
            draw.line([(mid_x, mid_y), end], fill=(*color, 100), width=2)
        else:  # Eclair
            draw_lightning(draw, start, end, color, rng, 1)
    
    def _draw_glyph(self, draw: ImageDraw, center: Tuple[int, int],
                   size: int, color: Tuple[int, int, int], rng: DeterministicRNG):
        """Glyphe avec forme aleatoire"""
        cx, cy = center
        sides = rng.next_int(3, 8)
        rotation = rng.next_float() * 2 * math.pi
        
        points = []
        for i in range(sides):
            angle = 2 * math.pi * i / sides + rotation
            r = size * (0.8 + rng.next_float() * 0.4)
            x = cx + int(r * math.cos(angle))
            y = cy + int(r * math.sin(angle))
            points.append((x, y))
        
        draw.polygon(points, fill=(*color, 150), outline=(*color, 255))
        
        # Cercle interieur
        inner_r = size // 2
        draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r],
                    fill=(*color, 100), outline=(255, 255, 255, 150))
    
    def _draw_sphere(self, img: Image, center: Tuple[int, int],
                    size: int, color: Tuple[int, int, int], rng: DeterministicRNG):
        """Sphere avec reflets"""
        draw = ImageDraw.Draw(img, 'RGBA')
        cx, cy = center
        
        # Sphere principale
        for r in range(size, 0, -2):
            t = r / size
            shade = 0.3 + 0.7 * t
            alpha = int(255 * t)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                        fill=(*[int(c * shade) for c in color], alpha))
        
        # Reflet
        hl_x = cx - size // 3
        hl_y = cy - size // 3
        hl_r = size // 4
        draw.ellipse([hl_x - hl_r, hl_y - hl_r, hl_x + hl_r, hl_y + hl_r],
                    fill=(255, 255, 255, 120))
    
    def _draw_text(self, draw: ImageDraw, name: str, rarity: str,
                   power: float, shape: str, aura: str):
        """Texte informatif"""
        color = RARITY_COLORS.get(rarity, (200, 200, 200))
        
        try:
            font_large = ImageFont.truetype("arial.ttf", 28)
            font_medium = ImageFont.truetype("arial.ttf", 18)
            font_small = ImageFont.truetype("arial.ttf", 14)
        except:
            font_large = ImageFont.load_default()
            font_medium = font_large
            font_small = font_large
        
        # Nom
        draw.text((self.width // 2, 35), name, fill=(*color, 255),
                 anchor="mm", font=font_large)
        
        # Rarete et puissance
        draw.text((self.width // 2, 65),
                 f"[{rarity.upper()}] Power: {power:,.0f}",
                 fill=(150, 150, 150, 255), anchor="mm", font=font_medium)
        
        # Style (coin inferieur)
        draw.text((20, self.height - 30),
                 f"Style: {shape} / {aura}",
                 fill=(80, 80, 80, 255), font=font_small)


# ============================================================================
# GENERATEUR DE PIERRE PHILOSOPHALE
# ============================================================================

class PhilosopherStoneImageGenerator:
    """Genere une image 3D unique d'une Pierre Philosophale"""
    
    def __init__(self, width: int = 800, height: int = 800):
        self.width = width
        self.height = height
        self.output_dir = Path(__file__).parent.parent / "visuals" / "stones"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, stone_data: dict) -> str:
        """Genere l'image avec apparence aleatoire"""
        if not HAS_PIL:
            return "PIL required"
        
        stone_id = stone_data.get('stone_id', 'unknown')
        state = stone_data.get('state', 'dormant')
        energy = stone_data.get('current_energy', 0)
        max_energy = stone_data.get('max_energy', 1000)
        
        rng = DeterministicRNG(stone_id)
        
        # Styles aleatoires
        crystal_shape = rng.choice(["diamond", "star", "spiral", "obelisk"])
        aura_style = rng.choice(["radial", "spiral", "flames", "particles"])
        bg_style = rng.choice(["void", "nebula", "vortex"])
        
        # Couleurs selon etat mais avec variation
        state_colors = {
            'dormant': (100, 100, 100),
            'awakened': (255, 100, 0),
            'transcendent': (255, 215, 0),
            'corrupted': (100, 0, 100),
        }
        base_color = state_colors.get(state, (255, 100, 0))
        main_color = rng.next_color_variation(base_color, 40)
        
        img = Image.new('RGBA', (self.width, self.height), (10, 0, 20, 255))
        draw = ImageDraw.Draw(img, 'RGBA')
        
        cx, cy = self.width // 2, self.height // 2
        
        # Fond
        bg_funcs = {
            "void": draw_void_bg,
            "nebula": draw_nebula_bg,
            "vortex": draw_vortex_bg,
        }
        bg_funcs.get(bg_style, draw_void_bg)(draw, self.width, self.height, rng)
        
        # Aura selon energie
        energy_ratio = energy / max_energy if max_energy > 0 else 0
        aura_radius = int(150 + 100 * energy_ratio)
        
        if aura_style == "radial":
            draw_glow(draw, (cx, cy), aura_radius, main_color, 0.5 * energy_ratio + 0.3)
        elif aura_style == "spiral":
            draw_spiral_aura(draw, (cx, cy), aura_radius, main_color, rng)
        elif aura_style == "flames":
            for _ in range(20):
                angle = rng.next_float() * 2 * math.pi
                flame_x = cx + int(50 * math.cos(angle))
                flame_y = cy + int(50 * math.sin(angle))
                for h in range(int(aura_radius * 0.8), 0, -10):
                    t = h / (aura_radius * 0.8)
                    fy = flame_y - h
                    size = int(10 * (1 - t))
                    draw.ellipse([flame_x - size, fy - size, flame_x + size, fy + size],
                                fill=(*main_color, int(150 * (1 - t))))
        else:
            draw_particle_cloud(draw, (cx, cy), aura_radius, main_color, rng, 150)
        
        # Pierre centrale
        stone_size = 80 + rng.next_int(0, 30)
        
        if crystal_shape == "diamond":
            draw_diamond_crystal(img, (cx, cy), stone_size, main_color, rng)
        elif crystal_shape == "star":
            draw_star_crystal(img, (cx, cy), stone_size, main_color, rng)
        elif crystal_shape == "spiral":
            draw_spiral_crystal(img, (cx, cy), stone_size, main_color, rng)
        else:
            draw_obelisk_crystal(img, (cx, cy), stone_size, main_color, rng)
        
        # Particules d'energie
        if state in ['awakened', 'transcendent']:
            count = int(50 + 100 * energy_ratio)
            draw_particle_cloud(draw, (cx, cy), 200, main_color, rng, count)
        
        # Texte
        try:
            font = ImageFont.truetype("arial.ttf", 22)
            font_small = ImageFont.truetype("arial.ttf", 14)
        except:
            font = ImageFont.load_default()
            font_small = font
        
        draw.text((cx, 35), "PHILOSOPHER STONE",
                 fill=(*main_color, 255), anchor="mm", font=font)
        draw.text((cx, 60), f"[{state.upper()}] #{stone_id[:8]}",
                 fill=(150, 150, 150, 255), anchor="mm", font=font_small)
        
        # Barre d'energie
        bar_width, bar_height = 250, 15
        bar_x = (self.width - bar_width) // 2
        bar_y = self.height - 50
        
        draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
                      fill=(30, 30, 30), outline=(80, 80, 80))
        
        fill_w = int(bar_width * energy_ratio)
        if fill_w > 0:
            draw.rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_height],
                          fill=(*main_color, 200))
        
        draw.text((cx, bar_y - 15), f"Energy: {energy}/{max_energy}",
                 fill=(150, 150, 150), anchor="mm", font=font_small)
        
        # Sauvegarder
        filepath = self.output_dir / f"stone_{stone_id[:12]}.png"
        img.save(filepath, 'PNG')
        
        return str(filepath)


# ============================================================================
# GENERATEUR DE GEMME
# ============================================================================

class GemImageGenerator:
    """Genere une image 3D unique d'une gemme"""
    
    def __init__(self, width: int = 512, height: int = 512):
        self.width = width
        self.height = height
        self.output_dir = Path(__file__).parent.parent / "visuals" / "gems"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, gem_data: dict) -> str:
        """Genere l'image avec apparence aleatoire"""
        if not HAS_PIL:
            return "PIL required"
        
        gem_id = gem_data.get('gem_id', 'unknown')
        gem_type = gem_data.get('gem_type', 'crystal')
        rarity = gem_data.get('rarity', 'common')
        power = gem_data.get('effective_power', gem_data.get('base_power', 100))
        
        rng = DeterministicRNG(gem_id)
        
        # Forme aleatoire
        shape = rng.choice(["diamond", "star", "cluster", "sphere"])
        bg_style = rng.choice(["void", "starfield", "nebula"])
        
        # Couleur basee sur rarete avec variation
        base_color = GEM_COLORS.get(rarity, (136, 136, 136))
        main_color = rng.next_color_variation(base_color, 50)
        
        img = Image.new('RGBA', (self.width, self.height), (5, 5, 20, 255))
        draw = ImageDraw.Draw(img, 'RGBA')
        
        cx, cy = self.width // 2, self.height // 2
        
        # Fond
        if bg_style == "starfield":
            draw_starfield_bg(draw, self.width, self.height, rng)
        elif bg_style == "nebula":
            draw_nebula_bg(draw, self.width, self.height, rng)
        else:
            draw_void_bg(draw, self.width, self.height, rng)
        
        # Aura
        aura_size = 100 + int(power / 100)
        draw_glow(draw, (cx, cy), min(aura_size, 180), main_color, 0.4)
        
        # Gemme
        gem_size = 50 + rng.next_int(0, 30)
        
        if shape == "diamond":
            draw_diamond_crystal(img, (cx, cy), gem_size, main_color, rng)
        elif shape == "star":
            draw_star_crystal(img, (cx, cy), gem_size, main_color, rng)
        elif shape == "cluster":
            draw_cluster_crystal(img, (cx, cy), gem_size, main_color, rng)
        else:
            # Sphere
            for r in range(gem_size, 0, -2):
                t = r / gem_size
                draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                            fill=(*[int(c * (0.3 + 0.7 * t)) for c in main_color], int(255 * t)))
            draw.ellipse([cx - gem_size//3, cy - gem_size//3,
                         cx - gem_size//6, cy - gem_size//6],
                        fill=(255, 255, 255, 120))
        
        # Particules
        draw_particle_cloud(draw, (cx, cy), 150, main_color, rng, 40)
        
        # Texte
        try:
            font = ImageFont.truetype("arial.ttf", 18)
            font_small = ImageFont.truetype("arial.ttf", 12)
        except:
            font = ImageFont.load_default()
            font_small = font
        
        display_name = gem_type.replace('_', ' ').title()[:25]
        draw.text((cx, 25), display_name, fill=(*main_color, 255),
                 anchor="mm", font=font)
        draw.text((cx, 45), f"[{rarity.upper()}]",
                 fill=(150, 150, 150), anchor="mm", font=font_small)
        draw.text((cx, self.height - 25), f"Power: {power:,.0f}",
                 fill=(150, 150, 150), anchor="mm", font=font_small)
        
        filepath = self.output_dir / f"gem_{gem_id[:12]}.png"
        img.save(filepath, 'PNG')
        
        return str(filepath)


# ============================================================================
# GENERATEUR DE NEXUS
# ============================================================================

class NexusImageGenerator:
    """Genere une vue globale du Nexus"""
    
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height
        self.output_dir = Path(__file__).parent.parent / "visuals" / "nexus"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, vaults_data: List[dict]) -> str:
        """Genere l'image du Nexus"""
        if not HAS_PIL:
            return "PIL required"
        
        rng = DeterministicRNG("nexus_global_" + str(len(vaults_data)))
        
        img = Image.new('RGBA', (self.width, self.height), (2, 2, 8, 255))
        draw = ImageDraw.Draw(img, 'RGBA')
        
        cx, cy = self.width // 2, self.height // 2
        
        # Fond
        bg_style = rng.choice(["nebula", "vortex", "starfield"])
        if bg_style == "nebula":
            draw_nebula_bg(draw, self.width, self.height, rng)
        elif bg_style == "vortex":
            draw_vortex_bg(draw, self.width, self.height, rng)
        else:
            draw_starfield_bg(draw, self.width, self.height, rng)
        
        # Centre du Nexus
        draw_glow(draw, (cx, cy), 150, (255, 215, 0), 0.6)
        draw_star_crystal(img, (cx, cy), 40, (255, 215, 0), rng)
        
        # Vaults en positions aleatoires mais deterministes
        for i, vault in enumerate(vaults_data):
            vault_rng = DeterministicRNG(f"vault_{vault.get('vault_number', i)}")
            
            vault_num = vault.get('vault_number', i + 1)
            artifact = vault.get('artifact', {})
            rarity = artifact.get('rarity', 'common')
            
            # Position semi-aleatoire
            base_angle = 2 * math.pi * i / max(len(vaults_data), 1)
            angle = base_angle + vault_rng.next_float() * 0.5 - 0.25
            radius = 150 + vault_rng.next_int(50, 200)
            
            vx = cx + int(radius * math.cos(angle))
            vy = cy + int(radius * 0.6 * math.sin(angle))
            
            color = RARITY_COLORS.get(rarity, (200, 200, 200))
            color = vault_rng.next_color_variation(color, 30)
            
            # Connexion
            if vault_rng.next_bool(0.7):
                draw.line([(cx, cy), (vx, vy)], fill=(*color, 50), width=3)
                draw.line([(cx, cy), (vx, vy)], fill=(*color, 100), width=1)
            
            # Vault
            v_size = 12 + vault_num * 2
            draw_glow(draw, (vx, vy), v_size + 10, color, 0.3)
            
            shape = vault_rng.choice(["diamond", "star", "sphere"])
            if shape == "diamond":
                draw_diamond_crystal(img, (vx, vy), v_size, color, vault_rng)
            elif shape == "star":
                draw_star_crystal(img, (vx, vy), v_size, color, vault_rng)
            else:
                for r in range(v_size, 0, -2):
                    draw.ellipse([vx - r, vy - r, vx + r, vy + r],
                                fill=(*color, int(255 * r / v_size)))
            
            # Label
            try:
                font = ImageFont.truetype("arial.ttf", 11)
            except:
                font = ImageFont.load_default()
            draw.text((vx, vy + v_size + 12), f"#{vault_num}",
                     fill=(*color, 200), anchor="mm", font=font)
        
        # Titre
        try:
            font_large = ImageFont.truetype("arial.ttf", 36)
            font_medium = ImageFont.truetype("arial.ttf", 18)
        except:
            font_large = ImageFont.load_default()
            font_medium = font_large
        
        draw.text((cx, 40), "POLY-SPINOR NEXUS 7D",
                 fill=(255, 215, 0, 255), anchor="mm", font=font_large)
        draw.text((cx, 75), f"{len(vaults_data)} Vaults Connected",
                 fill=(150, 150, 150), anchor="mm", font=font_medium)
        
        filepath = self.output_dir / "nexus_overview.png"
        img.save(filepath, 'PNG')
        
        return str(filepath)


# ============================================================================
# CLI
# ============================================================================

def main():
    print("\n" + "="*70)
    print("  3D VISUAL GENERATOR - Poly-Spinor Nexus 7D")
    print("  >> RANDOM APPEARANCE MODE <<")
    print("="*70)
    
    if not HAS_PIL:
        print("\n[ERROR] PIL/Pillow is required")
        print("Install with: pip install Pillow")
        return
    
    base_path = Path(__file__).parent.parent
    genesis_dir = base_path / "genesis_data" / "blocks"
    
    print("\n[*] Loading data...")
    
    vaults_data = []
    for block_file in sorted(genesis_dir.glob("block_*.json")):
        with open(block_file, 'r', encoding='utf-8') as f:
            vaults_data.append(json.load(f))
    
    print(f"    Found {len(vaults_data)} vaults")
    
    print("\n[*] Generating RANDOM 3D visuals...\n")
    
    # Artefacts
    print("  === ARTIFACTS ===")
    artifact_gen = ArtifactImageGenerator()
    for vault in vaults_data:
        artifact = vault.get('artifact', {})
        if artifact:
            path = artifact_gen.generate(artifact)
            name = artifact.get('name', 'Unknown')[:35]
            print(f"  [+] {name}")
            print(f"      -> {path}")
    
    # Pierres
    stones_dir = base_path / "philosopher_stones" / "stones"
    if stones_dir.exists():
        print("\n  === PHILOSOPHER STONES ===")
        stone_gen = PhilosopherStoneImageGenerator()
        for stone_file in stones_dir.glob("stone_*.json"):
            with open(stone_file, 'r', encoding='utf-8') as f:
                stone_data = json.load(f)
            path = stone_gen.generate(stone_data)
            print(f"  [+] Stone #{stone_data.get('stone_id', '')[:8]}")
            print(f"      -> {path}")
    
    # Gemmes (quelques unes)
    gems_dir = base_path / "gem_vault" / "gems"
    if gems_dir.exists():
        print("\n  === GEMS (sample) ===")
        gem_gen = GemImageGenerator()
        for gem_file in list(gems_dir.glob("gem_*.json"))[:5]:
            with open(gem_file, 'r', encoding='utf-8') as f:
                gem_data = json.load(f)
            path = gem_gen.generate(gem_data)
            rarity = gem_data.get('rarity', 'common')
            print(f"  [+] [{rarity.upper()}] {gem_data.get('gem_type', 'unknown')[:20]}")
            print(f"      -> {path}")
    
    # Nexus
    print("\n  === NEXUS OVERVIEW ===")
    nexus_gen = NexusImageGenerator()
    path = nexus_gen.generate(vaults_data)
    print(f"  [+] Nexus with {len(vaults_data)} vaults")
    print(f"      -> {path}")
    
    print("\n" + "="*70)
    print("  GENERATION COMPLETE - Each object has UNIQUE appearance!")
    print("="*70)
    
    visuals_dir = base_path / "visuals"
    total = sum(1 for _ in visuals_dir.rglob("*.png")) if visuals_dir.exists() else 0
    print(f"\n  Output: {visuals_dir}")
    print(f"  Total images: {total}")


if __name__ == "__main__":
    main()
