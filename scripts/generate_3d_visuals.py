#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        GENERATEUR D'IMAGES 3D - Poly-Spinor Nexus 7D                         ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  Genere des visualisations 3D pour:                                          ║
║  - Artefacts avec glyphes et gemmes orbitales                                ║
║  - Pierres Philosophales avec aura d'energie                                 ║
║  - Gemmes cristallines multi-facettes                                        ║
║  - Constellations de fragments                                               ║
║  - Vue globale du Nexus                                                      ║
║                                                                              ║
║  Utilise PIL/Pillow - pas de dependance matplotlib                           ║
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

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    print("[WARN] numpy not installed. Install with: pip install numpy")


# ============================================================================
# CONFIGURATION DES COULEURS
# ============================================================================

ESSENCE_COLORS = {
    "void": (26, 0, 51),
    "quantum": (0, 255, 136),
    "temporal": (255, 170, 0),
    "spatial": (0, 170, 255),
    "entropic": (255, 51, 102),
    "harmonic": (170, 85, 255),
    "celestial": (255, 255, 170),
}

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
# GENERATEUR RNG DETERMINISTE
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
    
    def next_color_variation(self, base_color: Tuple[int, int, int], 
                            variation: int = 30) -> Tuple[int, int, int]:
        """Variation aleatoire d'une couleur"""
        return tuple(
            max(0, min(255, c + self.next_int(-variation, variation)))
            for c in base_color
        )


# ============================================================================
# FONCTIONS DE DESSIN 3D
# ============================================================================

def draw_glow(draw: ImageDraw, center: Tuple[int, int], radius: int,
              color: Tuple[int, int, int], intensity: float = 1.0):
    """Dessine un effet de lueur/glow"""
    for r in range(radius, 0, -2):
        alpha = int(255 * (r / radius) * intensity * 0.3)
        glow_color = (*color, alpha)
        draw.ellipse([
            center[0] - r, center[1] - r,
            center[0] + r, center[1] + r
        ], fill=glow_color)


def draw_crystal_facet(draw: ImageDraw, points: List[Tuple[int, int]],
                       base_color: Tuple[int, int, int], shade: float):
    """Dessine une facette de cristal avec ombrage"""
    shaded_color = tuple(int(c * shade) for c in base_color)
    draw.polygon(points, fill=shaded_color, outline=(255, 255, 255, 100))


def draw_3d_sphere(img: Image, center: Tuple[int, int], radius: int,
                   color: Tuple[int, int, int], highlight: bool = True):
    """Dessine une sphere 3D avec effet de lumiere"""
    draw = ImageDraw.Draw(img, 'RGBA')
    
    # Ombre
    for i in range(radius, 0, -1):
        shade = 0.3 + 0.7 * (i / radius)
        r, g, b = [int(c * shade) for c in color]
        alpha = int(255 * (i / radius))
        draw.ellipse([
            center[0] - i, center[1] - i,
            center[0] + i, center[1] + i
        ], fill=(r, g, b, alpha))
    
    # Highlight
    if highlight:
        hl_x = center[0] - radius // 3
        hl_y = center[1] - radius // 3
        hl_r = radius // 4
        draw.ellipse([
            hl_x - hl_r, hl_y - hl_r,
            hl_x + hl_r, hl_y + hl_r
        ], fill=(255, 255, 255, 100))


def draw_crystal(img: Image, center: Tuple[int, int], size: int,
                 color: Tuple[int, int, int], rng: DeterministicRNG,
                 facets: int = 8):
    """Dessine un cristal 3D multi-facettes"""
    draw = ImageDraw.Draw(img, 'RGBA')
    cx, cy = center
    
    # Points du cristal (double pyramide)
    top = (cx, cy - size)
    bottom = (cx, cy + size)
    
    # Points du milieu
    mid_points = []
    for i in range(facets):
        angle = 2 * math.pi * i / facets - math.pi / 2
        px = cx + int(size * 0.7 * math.cos(angle))
        py = cy + int(size * 0.3 * math.sin(angle))
        mid_points.append((px, py))
    
    # Dessiner les facettes superieures
    for i in range(facets):
        next_i = (i + 1) % facets
        shade = 0.5 + 0.5 * math.cos(2 * math.pi * i / facets)
        points = [top, mid_points[i], mid_points[next_i]]
        draw_crystal_facet(draw, points, color, shade)
    
    # Dessiner les facettes inferieures
    for i in range(facets):
        next_i = (i + 1) % facets
        shade = 0.3 + 0.3 * math.cos(2 * math.pi * i / facets)
        points = [bottom, mid_points[next_i], mid_points[i]]
        draw_crystal_facet(draw, points, color, shade)
    
    # Reflet central
    draw.ellipse([
        cx - size // 6, cy - size // 6,
        cx + size // 6, cy + size // 6
    ], fill=(255, 255, 255, 80))


def draw_glyph_symbol(draw: ImageDraw, center: Tuple[int, int], size: int,
                      glyph_type: str, color: Tuple[int, int, int]):
    """Dessine un symbole de glyphe"""
    cx, cy = center
    
    # Nombre de cotes selon le type
    sides = {
        "void": 6, "quantum": 4, "temporal": 8, "spatial": 3,
        "entropic": 5, "harmonic": 7, "celestial": 12
    }.get(glyph_type, 6)
    
    # Dessiner le polygone
    points = []
    for i in range(sides):
        angle = 2 * math.pi * i / sides - math.pi / 2
        px = cx + int(size * math.cos(angle))
        py = cy + int(size * math.sin(angle))
        points.append((px, py))
    
    # Remplissage avec transparence
    draw.polygon(points, fill=(*color, 150), outline=(*color, 255))
    
    # Cercle interieur
    inner_r = size // 2
    draw.ellipse([
        cx - inner_r, cy - inner_r,
        cx + inner_r, cy + inner_r
    ], fill=(*color, 100), outline=(255, 255, 255, 150))


def draw_orbital_ring(draw: ImageDraw, center: Tuple[int, int], 
                     radius: int, color: Tuple[int, int, int],
                     tilt: float = 0.3, particles: int = 20,
                     rng: DeterministicRNG = None):
    """Dessine un anneau orbital avec particules"""
    cx, cy = center
    
    # Anneau principal (ellipse pour effet 3D)
    ellipse_height = int(radius * tilt)
    draw.ellipse([
        cx - radius, cy - ellipse_height,
        cx + radius, cy + ellipse_height
    ], outline=(*color, 100), width=2)
    
    # Particules sur l'orbite
    if rng:
        for i in range(particles):
            angle = 2 * math.pi * i / particles + rng.next_float() * 0.5
            px = cx + int(radius * math.cos(angle))
            py = cy + int(ellipse_height * math.sin(angle))
            
            # Taille variable
            p_size = 2 + int(rng.next_float() * 4)
            draw.ellipse([
                px - p_size, py - p_size,
                px + p_size, py + p_size
            ], fill=(*color, 200))


def draw_energy_particles(draw: ImageDraw, center: Tuple[int, int],
                         radius: int, color: Tuple[int, int, int],
                         count: int, rng: DeterministicRNG):
    """Dessine des particules d'energie flottantes"""
    cx, cy = center
    
    for _ in range(count):
        # Position aleatoire dans le rayon
        angle = rng.next_float() * 2 * math.pi
        dist = rng.next_float() * radius
        
        px = cx + int(dist * math.cos(angle))
        py = cy + int(dist * math.sin(angle))
        
        # Taille et opacite variables
        size = 1 + int(rng.next_float() * 3)
        alpha = int(100 + rng.next_float() * 155)
        
        draw.ellipse([
            px - size, py - size,
            px + size, py + size
        ], fill=(*color, alpha))


def draw_connection_line(draw: ImageDraw, start: Tuple[int, int],
                        end: Tuple[int, int], color: Tuple[int, int, int],
                        glow: bool = True):
    """Dessine une ligne de connexion avec effet glow"""
    if glow:
        # Ligne glow (plus large, plus transparente)
        draw.line([start, end], fill=(*color, 50), width=5)
        draw.line([start, end], fill=(*color, 100), width=3)
    
    draw.line([start, end], fill=(*color, 200), width=1)


# ============================================================================
# GENERATEUR D'ARTEFACT
# ============================================================================

class ArtifactImageGenerator:
    """Genere une image 3D d'un artefact"""
    
    def __init__(self, width: int = 1024, height: int = 1024):
        self.width = width
        self.height = height
        self.output_dir = Path(__file__).parent.parent / "visuals" / "artifacts"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, artifact_data: dict) -> str:
        """Genere l'image de l'artefact"""
        if not HAS_PIL:
            return "PIL required"
        
        # Creer l'image de base
        img = Image.new('RGBA', (self.width, self.height), (5, 5, 15, 255))
        draw = ImageDraw.Draw(img, 'RGBA')
        
        # Extraire les donnees
        name = artifact_data.get('name', 'Unknown Artifact')
        rarity = artifact_data.get('rarity', 'common')
        artifact_id = artifact_data.get('artifact_id', 'unknown')
        stats = artifact_data.get('stats', {})
        power = stats.get('effective_power', 0)
        glyph_array = artifact_data.get('glyph_array', {})
        
        # RNG deterministe
        rng = DeterministicRNG(artifact_id)
        
        # Couleur de base
        base_color = RARITY_COLORS.get(rarity, (200, 200, 200))
        
        cx, cy = self.width // 2, self.height // 2
        
        # 1. Fond etoile
        self._draw_starfield(draw, rng)
        
        # 2. Aura externe
        draw_glow(draw, (cx, cy), 300, base_color, 0.3)
        
        # 3. Anneaux orbitaux
        for i, radius in enumerate([250, 320, 380]):
            ring_color = rng.next_color_variation(base_color, 40)
            draw_orbital_ring(draw, (cx, cy), radius, ring_color, 
                            tilt=0.2 + i * 0.1, particles=15 + i * 5, rng=rng)
        
        # 4. Glyphes (7 autour du centre)
        glyphs = glyph_array.get('glyphs', [])
        for i in range(7):
            angle = 2 * math.pi * i / 7 - math.pi / 2
            glyph_dist = 180
            gx = cx + int(glyph_dist * math.cos(angle))
            gy = cy + int(glyph_dist * math.sin(angle))
            
            # Couleur du glyphe
            if i < len(glyphs):
                glyph_type = glyphs[i].get('glyph_type', 'void').replace('glyph_', '')
                glyph_color = ESSENCE_COLORS.get(glyph_type, (150, 150, 150))
            else:
                glyph_type = list(ESSENCE_COLORS.keys())[i % 7]
                glyph_color = ESSENCE_COLORS[glyph_type]
            
            # Connexion au centre
            draw_connection_line(draw, (cx, cy), (gx, gy), glyph_color)
            
            # Dessiner le glyphe
            draw_glyph_symbol(draw, (gx, gy), 35, glyph_type, glyph_color)
            
            # Gemmes autour du glyphe (3 par glyphe)
            if i < len(glyphs):
                gems = glyphs[i].get('gems', [])
                for j, gem in enumerate(gems[:3]):
                    gem_angle = angle + (j - 1) * 0.4
                    gem_dist = glyph_dist + 50
                    gem_x = cx + int(gem_dist * math.cos(gem_angle))
                    gem_y = cy + int(gem_dist * math.sin(gem_angle))
                    
                    gem_rarity = gem.get('rarity', 'common')
                    gem_color = GEM_COLORS.get(gem_rarity, (136, 136, 136))
                    
                    # Petite gemme
                    gem_size = 8 + int(gem.get('base_power', 50) / 50)
                    draw_3d_sphere(img, (gem_x, gem_y), gem_size, gem_color)
                    
                    # Lien glyphe-gemme
                    draw.line([(gx, gy), (gem_x, gem_y)], 
                             fill=(*gem_color, 80), width=1)
        
        # 5. Coeur central (artefact)
        core_size = 80
        draw_glow(draw, (cx, cy), core_size + 30, base_color, 0.5)
        draw_crystal(img, (cx, cy), core_size, base_color, rng, facets=12)
        
        # 6. Particules d'energie
        draw_energy_particles(draw, (cx, cy), 350, base_color, 100, rng)
        
        # 7. Texte
        self._draw_text(draw, name, rarity, power, glyph_array)
        
        # Appliquer un leger flou pour adoucir
        img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
        
        # Sauvegarder
        filename = f"artifact_{artifact_id[:12]}.png"
        filepath = self.output_dir / filename
        img.save(filepath, 'PNG')
        
        return str(filepath)
    
    def _draw_starfield(self, draw: ImageDraw, rng: DeterministicRNG):
        """Dessine un fond etoile"""
        for _ in range(200):
            x = rng.next_int(0, self.width)
            y = rng.next_int(0, self.height)
            size = rng.next_int(1, 3)
            brightness = rng.next_int(50, 200)
            draw.ellipse([x - size, y - size, x + size, y + size],
                        fill=(brightness, brightness, brightness, brightness))
    
    def _draw_text(self, draw: ImageDraw, name: str, rarity: str, 
                   power: float, glyph_array: dict):
        """Dessine le texte informatif"""
        color = RARITY_COLORS.get(rarity, (200, 200, 200))
        
        # Titre
        try:
            font_large = ImageFont.truetype("arial.ttf", 32)
            font_medium = ImageFont.truetype("arial.ttf", 20)
            font_small = ImageFont.truetype("arial.ttf", 16)
        except:
            font_large = ImageFont.load_default()
            font_medium = font_large
            font_small = font_large
        
        # Nom de l'artefact
        draw.text((self.width // 2, 40), name, fill=(*color, 255),
                 anchor="mm", font=font_large)
        
        # Rarete et puissance
        draw.text((self.width // 2, 80), 
                 f"[{rarity.upper()}] Power: {power:,.0f}",
                 fill=(150, 150, 150, 255), anchor="mm", font=font_medium)
        
        # Stats glyphes
        total_gems = glyph_array.get('total_gems', 0)
        glyph_power = glyph_array.get('total_power', 0)
        bell = glyph_array.get('bell_correlation', 0)
        
        y_pos = self.height - 80
        draw.text((30, y_pos), f"Glyphs: 7 | Gems: {total_gems}",
                 fill=(100, 100, 100, 255), font=font_small)
        draw.text((30, y_pos + 25), f"Glyph Power: {glyph_power:,.0f}",
                 fill=(100, 100, 100, 255), font=font_small)
        draw.text((30, y_pos + 50), f"Bell Correlation: {bell:.4f}",
                 fill=(100, 100, 100, 255), font=font_small)


# ============================================================================
# GENERATEUR DE PIERRE PHILOSOPHALE
# ============================================================================

class PhilosopherStoneImageGenerator:
    """Genere une image 3D d'une Pierre Philosophale"""
    
    def __init__(self, width: int = 800, height: int = 800):
        self.width = width
        self.height = height
        self.output_dir = Path(__file__).parent.parent / "visuals" / "stones"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, stone_data: dict) -> str:
        """Genere l'image de la pierre"""
        if not HAS_PIL:
            return "PIL required"
        
        img = Image.new('RGBA', (self.width, self.height), (10, 0, 20, 255))
        draw = ImageDraw.Draw(img, 'RGBA')
        
        stone_id = stone_data.get('stone_id', 'unknown')
        state = stone_data.get('state', 'dormant')
        energy = stone_data.get('current_energy', 0)
        max_energy = stone_data.get('max_energy', 1000)
        
        rng = DeterministicRNG(stone_id)
        
        # Couleurs selon l'etat
        state_colors = {
            'dormant': (100, 100, 100),
            'awakened': (255, 100, 0),
            'transcendent': (255, 215, 0),
            'corrupted': (100, 0, 100),
        }
        base_color = state_colors.get(state, (255, 100, 0))
        
        cx, cy = self.width // 2, self.height // 2
        
        # Fond
        for _ in range(100):
            x = rng.next_int(0, self.width)
            y = rng.next_int(0, self.height)
            size = rng.next_int(1, 2)
            draw.ellipse([x - size, y - size, x + size, y + size],
                        fill=(50, 50, 80, 100))
        
        # Aura selon energie
        energy_ratio = energy / max_energy if max_energy > 0 else 0
        aura_intensity = 0.3 + energy_ratio * 0.7
        
        draw_glow(draw, (cx, cy), int(250 * energy_ratio) + 100, 
                 base_color, aura_intensity)
        
        # Anneaux d'energie
        if state in ['awakened', 'transcendent']:
            for i in range(3):
                ring_r = 150 + i * 40
                ring_alpha = int(150 * energy_ratio)
                draw.ellipse([
                    cx - ring_r, cy - int(ring_r * 0.3),
                    cx + ring_r, cy + int(ring_r * 0.3)
                ], outline=(*base_color, ring_alpha), width=2)
        
        # Pierre centrale
        stone_size = 100
        draw_crystal(img, (cx, cy), stone_size, base_color, rng, facets=12)
        
        # Particules selon etat
        if state == 'transcendent':
            draw_energy_particles(draw, (cx, cy), 280, (255, 215, 0), 150, rng)
        elif state == 'awakened':
            draw_energy_particles(draw, (cx, cy), 200, base_color, 80, rng)
        
        # Lueur centrale
        draw_glow(draw, (cx, cy), 40, (255, 255, 255), 0.5)
        
        # Texte
        try:
            font = ImageFont.truetype("arial.ttf", 24)
            font_small = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
            font_small = font
        
        draw.text((cx, 40), "PHILOSOPHER STONE", 
                 fill=(*base_color, 255), anchor="mm", font=font)
        draw.text((cx, 70), f"[{state.upper()}] #{stone_id[:8]}",
                 fill=(150, 150, 150, 255), anchor="mm", font=font_small)
        
        # Barre d'energie
        bar_y = self.height - 60
        bar_width = 300
        bar_height = 20
        bar_x = (self.width - bar_width) // 2
        
        # Fond barre
        draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
                      fill=(30, 30, 30, 255), outline=(80, 80, 80, 255))
        
        # Remplissage
        fill_width = int(bar_width * energy_ratio)
        if fill_width > 0:
            draw.rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height],
                          fill=(*base_color, 200))
        
        draw.text((cx, bar_y - 10), f"Energy: {energy}/{max_energy}",
                 fill=(150, 150, 150, 255), anchor="mm", font=font_small)
        
        # Sauvegarder
        filename = f"stone_{stone_id[:12]}.png"
        filepath = self.output_dir / filename
        img.save(filepath, 'PNG')
        
        return str(filepath)


# ============================================================================
# GENERATEUR DE GEMME
# ============================================================================

class GemImageGenerator:
    """Genere une image 3D d'une gemme"""
    
    def __init__(self, width: int = 512, height: int = 512):
        self.width = width
        self.height = height
        self.output_dir = Path(__file__).parent.parent / "visuals" / "gems"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate(self, gem_data: dict) -> str:
        """Genere l'image de la gemme"""
        if not HAS_PIL:
            return "PIL required"
        
        img = Image.new('RGBA', (self.width, self.height), (5, 5, 20, 255))
        draw = ImageDraw.Draw(img, 'RGBA')
        
        gem_id = gem_data.get('gem_id', 'unknown')
        gem_type = gem_data.get('gem_type', 'void_crystal')
        rarity = gem_data.get('rarity', 'common')
        power = gem_data.get('effective_power', gem_data.get('base_power', 100))
        
        rng = DeterministicRNG(gem_id)
        
        # Couleur
        base_color = GEM_COLORS.get(rarity, (136, 136, 136))
        
        cx, cy = self.width // 2, self.height // 2
        
        # Fond particules
        for _ in range(50):
            x = rng.next_int(0, self.width)
            y = rng.next_int(0, self.height)
            draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(40, 40, 60, 100))
        
        # Aura
        draw_glow(draw, (cx, cy), 150, base_color, 0.4)
        
        # Gemme centrale
        gem_size = 80 + int(power / 100)
        draw_crystal(img, (cx, cy), min(gem_size, 120), base_color, rng, facets=8)
        
        # Particules
        draw_energy_particles(draw, (cx, cy), 180, base_color, 40, rng)
        
        # Texte
        try:
            font = ImageFont.truetype("arial.ttf", 20)
            font_small = ImageFont.truetype("arial.ttf", 14)
        except:
            font = ImageFont.load_default()
            font_small = font
        
        display_name = gem_type.replace('_', ' ').title()
        draw.text((cx, 30), display_name, fill=(*base_color, 255), 
                 anchor="mm", font=font)
        draw.text((cx, 55), f"[{rarity.upper()}]", 
                 fill=(150, 150, 150, 255), anchor="mm", font=font_small)
        draw.text((cx, self.height - 30), f"Power: {power:,.0f}",
                 fill=(150, 150, 150, 255), anchor="mm", font=font_small)
        
        # Sauvegarder
        filename = f"gem_{gem_id[:12]}.png"
        filepath = self.output_dir / filename
        img.save(filepath, 'PNG')
        
        return str(filepath)


# ============================================================================
# GENERATEUR DE NEXUS (Vue globale)
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
        
        img = Image.new('RGBA', (self.width, self.height), (2, 2, 8, 255))
        draw = ImageDraw.Draw(img, 'RGBA')
        
        rng = DeterministicRNG("nexus_global")
        
        cx, cy = self.width // 2, self.height // 2
        
        # Etoiles de fond
        for _ in range(500):
            x = rng.next_int(0, self.width)
            y = rng.next_int(0, self.height)
            size = rng.next_int(1, 2)
            brightness = rng.next_int(30, 150)
            draw.ellipse([x - size, y - size, x + size, y + size],
                        fill=(brightness, brightness, brightness + 20, brightness))
        
        # Centre du Nexus
        draw_glow(draw, (cx, cy), 200, (255, 215, 0), 0.5)
        draw_3d_sphere(img, (cx, cy), 50, (255, 215, 0))
        
        # Anneaux
        for r in [150, 250, 350, 450]:
            draw.ellipse([cx - r, cy - int(r * 0.3), cx + r, cy + int(r * 0.3)],
                        outline=(50, 70, 100, 100), width=1)
        
        # Vaults
        for i, vault in enumerate(vaults_data):
            vault_num = vault.get('vault_number', i + 1)
            artifact = vault.get('artifact', {})
            rarity = artifact.get('rarity', 'common')
            
            # Position en spirale
            angle = 2 * math.pi * i / max(len(vaults_data), 1) + i * 0.3
            radius = 120 + i * 40
            
            vx = cx + int(radius * math.cos(angle))
            vy = cy + int(radius * 0.4 * math.sin(angle))
            
            color = RARITY_COLORS.get(rarity, (200, 200, 200))
            
            # Connexion au centre
            draw_connection_line(draw, (cx, cy), (vx, vy), color)
            
            # Vault
            v_size = 15 + vault_num
            draw_3d_sphere(img, (vx, vy), v_size, color)
            
            # Label
            try:
                font = ImageFont.truetype("arial.ttf", 12)
            except:
                font = ImageFont.load_default()
            draw.text((vx, vy + v_size + 10), f"#{vault_num}",
                     fill=(*color, 200), anchor="mm", font=font)
        
        # Titre
        try:
            font_large = ImageFont.truetype("arial.ttf", 40)
            font_medium = ImageFont.truetype("arial.ttf", 20)
        except:
            font_large = ImageFont.load_default()
            font_medium = font_large
        
        draw.text((cx, 50), "POLY-SPINOR NEXUS 7D",
                 fill=(255, 215, 0, 255), anchor="mm", font=font_large)
        draw.text((cx, 90), f"{len(vaults_data)} Vaults Connected",
                 fill=(150, 150, 150, 255), anchor="mm", font=font_medium)
        
        # Sauvegarder
        filename = "nexus_overview.png"
        filepath = self.output_dir / filename
        img.save(filepath, 'PNG')
        
        return str(filepath)


# ============================================================================
# CLI
# ============================================================================

def main():
    print("\n" + "="*70)
    print("  3D VISUAL GENERATOR - Poly-Spinor Nexus 7D")
    print("="*70)
    
    if not HAS_PIL:
        print("\n[ERROR] PIL/Pillow is required")
        print("Install with: pip install Pillow")
        return
    
    base_path = Path(__file__).parent.parent
    genesis_dir = base_path / "genesis_data" / "blocks"
    
    print("\n[*] Loading data...")
    
    # Charger les vaults
    vaults_data = []
    for block_file in sorted(genesis_dir.glob("block_*.json")):
        with open(block_file, 'r', encoding='utf-8') as f:
            vaults_data.append(json.load(f))
    
    print(f"    Found {len(vaults_data)} vaults")
    
    print("\n[*] Generating 3D visuals...\n")
    
    # 1. Artefacts
    print("  === ARTIFACTS ===")
    artifact_gen = ArtifactImageGenerator()
    for vault in vaults_data[:3]:
        artifact = vault.get('artifact', {})
        if artifact:
            path = artifact_gen.generate(artifact)
            print(f"  [+] {artifact.get('name', 'Unknown')[:40]}")
            print(f"      -> {path}")
    
    # 2. Pierres Philosophales
    stones_dir = base_path / "philosopher_stones" / "stones"
    if stones_dir.exists():
        print("\n  === PHILOSOPHER STONES ===")
        stone_gen = PhilosopherStoneImageGenerator()
        for stone_file in list(stones_dir.glob("stone_*.json"))[:2]:
            with open(stone_file, 'r', encoding='utf-8') as f:
                stone_data = json.load(f)
            path = stone_gen.generate(stone_data)
            print(f"  [+] Stone #{stone_data.get('stone_id', '')[:8]}")
            print(f"      -> {path}")
    
    # 3. Gemmes
    gems_dir = base_path / "gem_vault" / "gems"
    if gems_dir.exists():
        print("\n  === GEMS ===")
        gem_gen = GemImageGenerator()
        for gem_file in list(gems_dir.glob("gem_*.json"))[:3]:
            with open(gem_file, 'r', encoding='utf-8') as f:
                gem_data = json.load(f)
            path = gem_gen.generate(gem_data)
            rarity = gem_data.get('rarity', 'common')
            print(f"  [+] [{rarity.upper()}] {gem_data.get('gem_type', 'unknown')}")
            print(f"      -> {path}")
    
    # 4. Nexus global
    print("\n  === NEXUS OVERVIEW ===")
    nexus_gen = NexusImageGenerator()
    path = nexus_gen.generate(vaults_data)
    print(f"  [+] Nexus with {len(vaults_data)} vaults")
    print(f"      -> {path}")
    
    print("\n" + "="*70)
    print("  GENERATION COMPLETE")
    print("="*70)
    
    visuals_dir = base_path / "visuals"
    total_files = sum(1 for _ in visuals_dir.rglob("*.png")) if visuals_dir.exists() else 0
    print(f"\n  Output: {visuals_dir}")
    print(f"  Total images: {total_files}")


if __name__ == "__main__":
    main()
