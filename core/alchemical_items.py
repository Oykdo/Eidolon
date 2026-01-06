"""
╔══════════════════════════════════════════════════════════════════════════════╗
║              SYSTEME D'OBJETS ALCHIMIQUES - Poly-Spinor Nexus 7D             ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  10 Categories d'Objets Alchimiques:                                         ║
║  - POTIONS: Effets temporaires puissants                                     ║
║  - ELIXIRS: Bonus permanents mineurs                                         ║
║  - RUNES: Enchantements pour artefacts                                       ║
║  - SCROLLS: Effets uniques puissants                                         ║
║  - ESSENCES: Materiaux de craft                                              ║
║  - TALISMANS: Protection et defense                                          ║
║  - ORBS: Stockage d'energie                                                  ║
║  - SEALS: Verrouillage et controle                                           ║
║  - SIGILS: Marquage et tracking                                              ║
║  - CRYSTALS: Amplificateurs de resonance                                     ║
║                                                                              ║
║  Systeme de COFFRES:                                                         ║
║  - Primordial: 31 objets | Legendary: 20 | Epic: 10 | Rare: 5 | Common: 2   ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import json
import hashlib
import secrets
import math
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ============================================================================
# CATEGORIES D'OBJETS ALCHIMIQUES
# ============================================================================

class AlchemicalCategory(Enum):
    """Les 10 categories d'objets alchimiques"""
    POTION = ("potion", "🧪", "Potion", "Effet temporaire puissant")
    ELIXIR = ("elixir", "⚗️", "Elixir", "Bonus permanent mineur")
    RUNE = ("rune", "ᚱ", "Rune", "Enchantement pour artefact")
    SCROLL = ("scroll", "📜", "Parchemin", "Effet unique puissant")
    ESSENCE = ("essence", "💧", "Essence", "Materiau de craft")
    TALISMAN = ("talisman", "🔮", "Talisman", "Protection et defense")
    ORB = ("orb", "🔵", "Orbe", "Stockage d'energie")
    SEAL = ("seal", "🔏", "Sceau", "Verrouillage et controle")
    SIGIL = ("sigil", "⚝", "Sigil", "Marquage et tracking")
    CRYSTAL = ("crystal", "💎", "Cristal", "Amplificateur de resonance")
    
    def __init__(self, cat_id: str, symbol: str, name: str, description: str):
        self.cat_id = cat_id
        self.symbol = symbol
        self.display_name = name
        self.description = description


# ============================================================================
# RARETES DES OBJETS
# ============================================================================

class ItemRarity(Enum):
    """Raretes des objets alchimiques"""
    CRUDE = ("crude", "Brut", 0.3, "#666666")
    COMMON = ("common", "Commun", 1.0, "#ffffff")
    REFINED = ("refined", "Raffine", 1.8, "#00ff00")
    SUPERIOR = ("superior", "Superieur", 3.0, "#00aaff")
    EXQUISITE = ("exquisite", "Exquis", 5.0, "#aa55ff")
    MASTERWORK = ("masterwork", "Chef-d'oeuvre", 8.0, "#ff8800")
    LEGENDARY = ("legendary", "Legendaire", 15.0, "#ff00ff")
    MYTHICAL = ("mythical", "Mythique", 25.0, "#ffd700")
    PRIMORDIAL = ("primordial", "Primordial", 50.0, "#00ffff")
    
    def __init__(self, rarity_id: str, name: str, multiplier: float, color: str):
        self.rarity_id = rarity_id
        self.display_name = name
        self.multiplier = multiplier
        self.color = color


RARITY_WEIGHTS = {
    ItemRarity.CRUDE: 1500,
    ItemRarity.COMMON: 3000,
    ItemRarity.REFINED: 2500,
    ItemRarity.SUPERIOR: 1500,
    ItemRarity.EXQUISITE: 800,
    ItemRarity.MASTERWORK: 400,
    ItemRarity.LEGENDARY: 200,
    ItemRarity.MYTHICAL: 80,
    ItemRarity.PRIMORDIAL: 20,
}


# ============================================================================
# TYPES D'OBJETS SPECIFIQUES (70+ types)
# ============================================================================

ALCHEMICAL_ITEMS = {
    # === POTIONS (10 types) ===
    "potion_power": {
        "category": "potion", "name": "Potion de Puissance",
        "effect": "Augmente la puissance de {value}% pendant {duration}h",
        "value_range": (10, 50), "duration_range": (1, 24),
        "can_stack": False, "max_uses": 1
    },
    "potion_resonance": {
        "category": "potion", "name": "Potion de Resonance",
        "effect": "Amplifie la resonance de {value}% pendant {duration}h",
        "value_range": (15, 60), "duration_range": (2, 12),
        "can_stack": False, "max_uses": 1
    },
    "potion_luck": {
        "category": "potion", "name": "Potion de Chance",
        "effect": "Augmente les chances de {value}% pendant {duration}h",
        "value_range": (5, 30), "duration_range": (1, 6),
        "can_stack": False, "max_uses": 1
    },
    "potion_transmutation": {
        "category": "potion", "name": "Potion de Transmutation",
        "effect": "Bonus de {value}% aux transmutations pendant {duration}h",
        "value_range": (20, 80), "duration_range": (1, 4),
        "can_stack": False, "max_uses": 1
    },
    "potion_revelation": {
        "category": "potion", "name": "Potion de Revelation",
        "effect": "Revele {value} secrets caches",
        "value_range": (1, 7), "duration_range": (0, 0),
        "can_stack": False, "max_uses": 1
    },
    "potion_protection": {
        "category": "potion", "name": "Potion de Protection",
        "effect": "Bouclier de {value} points pendant {duration}h",
        "value_range": (100, 1000), "duration_range": (6, 48),
        "can_stack": False, "max_uses": 1
    },
    "potion_regeneration": {
        "category": "potion", "name": "Potion de Regeneration",
        "effect": "Regenere {value} points/heure pendant {duration}h",
        "value_range": (10, 100), "duration_range": (12, 72),
        "can_stack": True, "max_uses": 3
    },
    "potion_haste": {
        "category": "potion", "name": "Potion de Celerite",
        "effect": "Accelere les actions de {value}% pendant {duration}h",
        "value_range": (25, 100), "duration_range": (1, 8),
        "can_stack": False, "max_uses": 1
    },
    "potion_insight": {
        "category": "potion", "name": "Potion de Clairvoyance",
        "effect": "Voit {value} cycles dans le futur",
        "value_range": (1, 5), "duration_range": (0, 0),
        "can_stack": False, "max_uses": 1
    },
    "potion_primordial": {
        "category": "potion", "name": "Potion Primordiale",
        "effect": "Effet aleatoire puissant (puissance {value})",
        "value_range": (50, 200), "duration_range": (1, 24),
        "can_stack": False, "max_uses": 1, "min_rarity": "legendary"
    },
    
    # === ELIXIRS (8 types) - Effets permanents ===
    "elixir_strength": {
        "category": "elixir", "name": "Elixir de Force",
        "effect": "Augmente la force de base de {value} (permanent)",
        "value_range": (5, 50), "duration_range": (0, 0),
        "permanent": True, "can_stack": True, "max_uses": 1
    },
    "elixir_wisdom": {
        "category": "elixir", "name": "Elixir de Sagesse",
        "effect": "Augmente la sagesse de {value} (permanent)",
        "value_range": (3, 30), "duration_range": (0, 0),
        "permanent": True, "can_stack": True, "max_uses": 1
    },
    "elixir_purity": {
        "category": "elixir", "name": "Elixir de Purete",
        "effect": "Augmente la purete max de {value}% (permanent)",
        "value_range": (1, 10), "duration_range": (0, 0),
        "permanent": True, "can_stack": True, "max_uses": 1
    },
    "elixir_stability": {
        "category": "elixir", "name": "Elixir de Stabilite",
        "effect": "Augmente la stabilite de {value}% (permanent)",
        "value_range": (2, 15), "duration_range": (0, 0),
        "permanent": True, "can_stack": True, "max_uses": 1
    },
    "elixir_longevity": {
        "category": "elixir", "name": "Elixir de Longevite",
        "effect": "Reduit le decay de {value}% (permanent)",
        "value_range": (5, 30), "duration_range": (0, 0),
        "permanent": True, "can_stack": True, "max_uses": 1
    },
    "elixir_affinity": {
        "category": "elixir", "name": "Elixir d'Affinite",
        "effect": "Augmente l'affinite {essence} de {value}%",
        "value_range": (5, 25), "duration_range": (0, 0),
        "permanent": True, "requires_essence": True, "max_uses": 1
    },
    "elixir_transcendence": {
        "category": "elixir", "name": "Elixir de Transcendance",
        "effect": "Progresse vers la transcendance de {value}%",
        "value_range": (1, 10), "duration_range": (0, 0),
        "permanent": True, "can_stack": True, "max_uses": 1, "min_rarity": "masterwork"
    },
    "elixir_immortality": {
        "category": "elixir", "name": "Elixir d'Immortalite",
        "effect": "Immunite totale au decay (permanent)",
        "value_range": (100, 100), "duration_range": (0, 0),
        "permanent": True, "can_stack": False, "max_uses": 1, "min_rarity": "primordial"
    },
    
    # === RUNES (12 types) - Enchantements ===
    "rune_fehu": {
        "category": "rune", "name": "Rune Fehu ᚠ",
        "effect": "Genere {value} PSNX par jour",
        "value_range": (1, 100), "duration_range": (0, 0),
        "enchant_type": "artifact", "can_stack": True, "max_uses": 1
    },
    "rune_uruz": {
        "category": "rune", "name": "Rune Uruz ᚢ",
        "effect": "Augmente la puissance de {value}%",
        "value_range": (5, 30), "duration_range": (0, 0),
        "enchant_type": "artifact", "can_stack": True, "max_uses": 1
    },
    "rune_thurisaz": {
        "category": "rune", "name": "Rune Thurisaz ᚦ",
        "effect": "Renvoie {value}% des degats",
        "value_range": (10, 50), "duration_range": (0, 0),
        "enchant_type": "artifact", "can_stack": False, "max_uses": 1
    },
    "rune_ansuz": {
        "category": "rune", "name": "Rune Ansuz ᚨ",
        "effect": "Revele {value} propheties supplementaires",
        "value_range": (1, 5), "duration_range": (0, 0),
        "enchant_type": "artifact", "can_stack": True, "max_uses": 1
    },
    "rune_raidho": {
        "category": "rune", "name": "Rune Raidho ᚱ",
        "effect": "Reduit les couts de transfert de {value}%",
        "value_range": (10, 50), "duration_range": (0, 0),
        "enchant_type": "gem", "can_stack": True, "max_uses": 1
    },
    "rune_kenaz": {
        "category": "rune", "name": "Rune Kenaz ᚲ",
        "effect": "Augmente les chances de transmutation de {value}%",
        "value_range": (5, 25), "duration_range": (0, 0),
        "enchant_type": "artifact", "can_stack": True, "max_uses": 1
    },
    "rune_gebo": {
        "category": "rune", "name": "Rune Gebo ᚷ",
        "effect": "Bonus de {value}% aux echanges",
        "value_range": (5, 20), "duration_range": (0, 0),
        "enchant_type": "gem", "can_stack": True, "max_uses": 1
    },
    "rune_wunjo": {
        "category": "rune", "name": "Rune Wunjo ᚹ",
        "effect": "Augmente le bonheur de {value}% (bonus global)",
        "value_range": (5, 15), "duration_range": (0, 0),
        "enchant_type": "artifact", "can_stack": True, "max_uses": 1
    },
    "rune_hagalaz": {
        "category": "rune", "name": "Rune Hagalaz ᚺ",
        "effect": "Inflige {value} degats de chaos",
        "value_range": (50, 500), "duration_range": (0, 0),
        "enchant_type": "artifact", "can_stack": False, "max_uses": 1
    },
    "rune_sowilo": {
        "category": "rune", "name": "Rune Sowilo ᛊ",
        "effect": "Illumine {value} dimensions",
        "value_range": (1, 7), "duration_range": (0, 0),
        "enchant_type": "artifact", "can_stack": False, "max_uses": 1
    },
    "rune_othala": {
        "category": "rune", "name": "Rune Othala ᛟ",
        "effect": "Heritage de {value}% des stats ancestrales",
        "value_range": (10, 50), "duration_range": (0, 0),
        "enchant_type": "artifact", "can_stack": True, "max_uses": 1
    },
    "rune_dagaz": {
        "category": "rune", "name": "Rune Dagaz ᛞ",
        "effect": "Transformation complete - reset a purete {value}%",
        "value_range": (80, 100), "duration_range": (0, 0),
        "enchant_type": "gem", "can_stack": False, "max_uses": 1, "min_rarity": "legendary"
    },
    
    # === SCROLLS (8 types) - Effets uniques ===
    "scroll_teleport": {
        "category": "scroll", "name": "Parchemin de Teleportation",
        "effect": "Teleporte un objet vers un autre vault",
        "value_range": (1, 1), "duration_range": (0, 0),
        "one_time": True, "max_uses": 1
    },
    "scroll_duplication": {
        "category": "scroll", "name": "Parchemin de Duplication",
        "effect": "Duplique un fragment (qualite {value}%)",
        "value_range": (50, 90), "duration_range": (0, 0),
        "one_time": True, "max_uses": 1, "min_rarity": "exquisite"
    },
    "scroll_purification": {
        "category": "scroll", "name": "Parchemin de Purification",
        "effect": "Purifie completement un objet corrompu",
        "value_range": (100, 100), "duration_range": (0, 0),
        "one_time": True, "max_uses": 1
    },
    "scroll_binding": {
        "category": "scroll", "name": "Parchemin de Lien",
        "effect": "Lie {value} objets ensemble (synergies)",
        "value_range": (2, 7), "duration_range": (0, 0),
        "one_time": True, "max_uses": 1
    },
    "scroll_summoning": {
        "category": "scroll", "name": "Parchemin d'Invocation",
        "effect": "Invoque {value} fragments aleatoires",
        "value_range": (1, 5), "duration_range": (0, 0),
        "one_time": True, "max_uses": 1, "min_rarity": "legendary"
    },
    "scroll_transmutation": {
        "category": "scroll", "name": "Parchemin de Transmutation",
        "effect": "Transmutation garantie (succes {value}%)",
        "value_range": (100, 100), "duration_range": (0, 0),
        "one_time": True, "max_uses": 1, "min_rarity": "masterwork"
    },
    "scroll_prophecy": {
        "category": "scroll", "name": "Parchemin de Prophetie",
        "effect": "Genere {value} propheties majeures",
        "value_range": (1, 3), "duration_range": (0, 0),
        "one_time": True, "max_uses": 1
    },
    "scroll_genesis": {
        "category": "scroll", "name": "Parchemin de Genese",
        "effect": "Cree un fragment primordial",
        "value_range": (1, 1), "duration_range": (0, 0),
        "one_time": True, "max_uses": 1, "min_rarity": "primordial"
    },
    
    # === ESSENCES (7 types) - Materiaux ===
    "essence_void": {
        "category": "essence", "name": "Essence du Vide",
        "effect": "Materiau de craft - {value} unites",
        "value_range": (10, 100), "duration_range": (0, 0),
        "essence_type": "void", "craftable": True
    },
    "essence_quantum": {
        "category": "essence", "name": "Essence Quantique",
        "effect": "Materiau de craft - {value} unites",
        "value_range": (10, 100), "duration_range": (0, 0),
        "essence_type": "quantum", "craftable": True
    },
    "essence_temporal": {
        "category": "essence", "name": "Essence Temporelle",
        "effect": "Materiau de craft - {value} unites",
        "value_range": (10, 100), "duration_range": (0, 0),
        "essence_type": "temporal", "craftable": True
    },
    "essence_spatial": {
        "category": "essence", "name": "Essence Spatiale",
        "effect": "Materiau de craft - {value} unites",
        "value_range": (10, 100), "duration_range": (0, 0),
        "essence_type": "spatial", "craftable": True
    },
    "essence_entropic": {
        "category": "essence", "name": "Essence Entropique",
        "effect": "Materiau de craft - {value} unites",
        "value_range": (10, 100), "duration_range": (0, 0),
        "essence_type": "entropic", "craftable": True
    },
    "essence_harmonic": {
        "category": "essence", "name": "Essence Harmonique",
        "effect": "Materiau de craft - {value} unites",
        "value_range": (10, 100), "duration_range": (0, 0),
        "essence_type": "harmonic", "craftable": True
    },
    "essence_celestial": {
        "category": "essence", "name": "Essence Celeste",
        "effect": "Materiau de craft - {value} unites",
        "value_range": (10, 100), "duration_range": (0, 0),
        "essence_type": "celestial", "craftable": True
    },
    
    # === TALISMANS (7 types) - Protection ===
    "talisman_shield": {
        "category": "talisman", "name": "Talisman de Bouclier",
        "effect": "Absorbe {value} degats",
        "value_range": (100, 2000), "duration_range": (0, 0),
        "protective": True, "charges": 3
    },
    "talisman_ward": {
        "category": "talisman", "name": "Talisman de Protection",
        "effect": "Protege contre la corruption ({value} points)",
        "value_range": (50, 500), "duration_range": (0, 0),
        "protective": True, "charges": 5
    },
    "talisman_luck": {
        "category": "talisman", "name": "Talisman de Chance",
        "effect": "Annule {value} echecs critiques",
        "value_range": (1, 10), "duration_range": (0, 0),
        "protective": True, "charges": "value"
    },
    "talisman_return": {
        "category": "talisman", "name": "Talisman de Retour",
        "effect": "Ramene un objet perdu (puissance {value}%)",
        "value_range": (50, 100), "duration_range": (0, 0),
        "protective": True, "charges": 1
    },
    "talisman_stealth": {
        "category": "talisman", "name": "Talisman de Discretion",
        "effect": "Cache un objet pendant {value} cycles",
        "value_range": (1, 10), "duration_range": (0, 0),
        "protective": True, "charges": 3
    },
    "talisman_anchor": {
        "category": "talisman", "name": "Talisman d'Ancrage",
        "effect": "Empeche le transfert involontaire",
        "value_range": (1, 1), "duration_range": (0, 0),
        "protective": True, "permanent": True
    },
    "talisman_resurrection": {
        "category": "talisman", "name": "Talisman de Resurrection",
        "effect": "Restaure un objet detruit (puissance {value}%)",
        "value_range": (30, 80), "duration_range": (0, 0),
        "protective": True, "charges": 1, "min_rarity": "legendary"
    },
    
    # === ORBS (6 types) - Energie ===
    "orb_energy": {
        "category": "orb", "name": "Orbe d'Energie",
        "effect": "Stocke {value} points d'energie",
        "value_range": (100, 1000), "duration_range": (0, 0),
        "storage": True, "energy_type": "generic"
    },
    "orb_power": {
        "category": "orb", "name": "Orbe de Puissance",
        "effect": "Stocke {value} points de puissance",
        "value_range": (50, 500), "duration_range": (0, 0),
        "storage": True, "energy_type": "power"
    },
    "orb_resonance": {
        "category": "orb", "name": "Orbe de Resonance",
        "effect": "Stocke {value} points de resonance",
        "value_range": (50, 500), "duration_range": (0, 0),
        "storage": True, "energy_type": "resonance"
    },
    "orb_philosopher": {
        "category": "orb", "name": "Orbe Philosophale",
        "effect": "Stocke {value} energie de Pierre",
        "value_range": (100, 500), "duration_range": (0, 0),
        "storage": True, "energy_type": "philosopher", "min_rarity": "masterwork"
    },
    "orb_dimensional": {
        "category": "orb", "name": "Orbe Dimensionnelle",
        "effect": "Contient {value} dimensions",
        "value_range": (1, 7), "duration_range": (0, 0),
        "storage": True, "energy_type": "dimensional", "min_rarity": "legendary"
    },
    "orb_primordial": {
        "category": "orb", "name": "Orbe Primordiale",
        "effect": "Contient l'essence de {value} origines",
        "value_range": (1, 3), "duration_range": (0, 0),
        "storage": True, "energy_type": "primordial", "min_rarity": "primordial"
    },
    
    # === SEALS (6 types) - Controle ===
    "seal_lock": {
        "category": "seal", "name": "Sceau de Verrouillage",
        "effect": "Verrouille un objet (niveau {value})",
        "value_range": (1, 10), "duration_range": (0, 0),
        "lock_type": "object"
    },
    "seal_vault": {
        "category": "seal", "name": "Sceau de Vault",
        "effect": "Protege un vault (puissance {value})",
        "value_range": (100, 1000), "duration_range": (0, 0),
        "lock_type": "vault"
    },
    "seal_portal": {
        "category": "seal", "name": "Sceau de Portail",
        "effect": "Scelle ou ouvre un portail",
        "value_range": (1, 1), "duration_range": (0, 0),
        "lock_type": "portal"
    },
    "seal_contract": {
        "category": "seal", "name": "Sceau de Contrat",
        "effect": "Cree un contrat inviolable ({value} clauses)",
        "value_range": (1, 7), "duration_range": (0, 0),
        "lock_type": "contract", "min_rarity": "exquisite"
    },
    "seal_authority": {
        "category": "seal", "name": "Sceau d'Autorite",
        "effect": "Confere l'autorite niveau {value}",
        "value_range": (1, 5), "duration_range": (0, 0),
        "lock_type": "authority", "min_rarity": "legendary"
    },
    "seal_crown": {
        "category": "seal", "name": "Sceau de la Couronne",
        "effect": "Sceau royal de gouvernance supreme",
        "value_range": (1, 1), "duration_range": (0, 0),
        "lock_type": "crown", "min_rarity": "primordial"
    },
    
    # === SIGILS (5 types) - Tracking ===
    "sigil_mark": {
        "category": "sigil", "name": "Sigil de Marquage",
        "effect": "Marque un objet (visible {value} cycles)",
        "value_range": (10, 100), "duration_range": (0, 0),
        "tracking": True
    },
    "sigil_trace": {
        "category": "sigil", "name": "Sigil de Trace",
        "effect": "Trace les mouvements sur {value} cycles",
        "value_range": (5, 50), "duration_range": (0, 0),
        "tracking": True
    },
    "sigil_ownership": {
        "category": "sigil", "name": "Sigil de Propriete",
        "effect": "Marque la propriete (puissance {value})",
        "value_range": (100, 1000), "duration_range": (0, 0),
        "tracking": True, "permanent": True
    },
    "sigil_beacon": {
        "category": "sigil", "name": "Sigil de Balise",
        "effect": "Balise visible a {value} dimensions",
        "value_range": (1, 7), "duration_range": (0, 0),
        "tracking": True
    },
    "sigil_nexus": {
        "category": "sigil", "name": "Sigil du Nexus",
        "effect": "Connexion directe au Nexus",
        "value_range": (1, 1), "duration_range": (0, 0),
        "tracking": True, "min_rarity": "mythical"
    },
    
    # === CRYSTALS (6 types) - Amplification ===
    "crystal_amplifier": {
        "category": "crystal", "name": "Cristal Amplificateur",
        "effect": "Amplifie de {value}%",
        "value_range": (10, 100), "duration_range": (0, 0),
        "amplifies": "generic"
    },
    "crystal_resonance": {
        "category": "crystal", "name": "Cristal de Resonance",
        "effect": "Resonne a frequence {value}",
        "value_range": (1000, 10000), "duration_range": (0, 0),
        "amplifies": "resonance"
    },
    "crystal_focus": {
        "category": "crystal", "name": "Cristal de Focalisation",
        "effect": "Focalise l'energie ({value}% efficacite)",
        "value_range": (50, 150), "duration_range": (0, 0),
        "amplifies": "focus"
    },
    "crystal_harmony": {
        "category": "crystal", "name": "Cristal d'Harmonie",
        "effect": "Harmonise {value} objets",
        "value_range": (2, 10), "duration_range": (0, 0),
        "amplifies": "harmony"
    },
    "crystal_dimensional": {
        "category": "crystal", "name": "Cristal Dimensionnel",
        "effect": "Amplifie {value} dimensions",
        "value_range": (1, 7), "duration_range": (0, 0),
        "amplifies": "dimensional", "min_rarity": "legendary"
    },
    "crystal_infinity": {
        "category": "crystal", "name": "Cristal de l'Infini",
        "effect": "Amplification infinie (x{value})",
        "value_range": (2, 10), "duration_range": (0, 0),
        "amplifies": "infinite", "min_rarity": "primordial"
    },
}


# ============================================================================
# OBJET ALCHIMIQUE
# ============================================================================

@dataclass
class AlchemicalItem:
    """Un objet alchimique"""
    item_id: str
    item_type: str  # Cle dans ALCHEMICAL_ITEMS
    category: str   # AlchemicalCategory
    rarity: str     # ItemRarity
    
    # Stats
    value: float
    duration: float
    charges: int = 1
    max_charges: int = 1
    
    # Etat
    is_used: bool = False
    is_bound: bool = False
    bound_to: Optional[str] = None  # ID de l'objet lie
    
    # Liens avec gemmes/artefacts
    linked_gem_id: Optional[str] = None
    linked_artifact_id: Optional[str] = None
    enchanted_on: Optional[str] = None
    
    # Origine
    origin_vault: int = 0
    origin_chest: Optional[str] = None
    created_at: str = ""
    
    # Position
    current_vault: Optional[int] = None
    status: str = "inventory"  # inventory, equipped, consumed, destroyed
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "AlchemicalItem":
        return cls(**data)
    
    @property
    def display_name(self) -> str:
        item_def = ALCHEMICAL_ITEMS.get(self.item_type, {})
        return item_def.get('name', self.item_type)
    
    @property
    def effect_description(self) -> str:
        item_def = ALCHEMICAL_ITEMS.get(self.item_type, {})
        effect = item_def.get('effect', '')
        return effect.format(value=self.value, duration=self.duration)
    
    @property
    def effective_power(self) -> float:
        rarity_enum = next((r for r in ItemRarity if r.rarity_id == self.rarity), ItemRarity.COMMON)
        return self.value * rarity_enum.multiplier


# ============================================================================
# COFFRES
# ============================================================================

class ChestTier(Enum):
    """Tiers de coffres"""
    PRIMORDIAL = ("primordial", "Coffre Primordial", 31, "#00ffff", 1)
    LEGENDARY = ("legendary", "Coffre Legendaire", 20, "#ffd700", 5)
    EPIC = ("epic", "Coffre Epique", 10, "#ff00ff", 15)
    RARE = ("rare", "Coffre Rare", 5, "#0088ff", 50)
    COMMON = ("common", "Coffre Commun", 2, "#ffffff", 100)
    
    def __init__(self, tier_id: str, name: str, item_count: int, color: str, weight: int):
        self.tier_id = tier_id
        self.display_name = name
        self.item_count = item_count
        self.color = color
        self.drop_weight = weight


@dataclass
class AlchemicalChest:
    """Un coffre contenant des objets alchimiques"""
    chest_id: str
    tier: str  # ChestTier
    
    # Contenu
    items: List[str] = field(default_factory=list)  # Liste d'item_ids
    item_count: int = 0
    
    # Etat
    is_opened: bool = False
    opened_at: Optional[str] = None
    opened_by_vault: Optional[int] = None
    
    # Origine
    origin_vault: int = 0
    created_at: str = ""
    
    # Bonus
    bonus_rarity_boost: float = 0.0  # Boost de rarete pour les items
    guaranteed_legendary: bool = False
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "AlchemicalChest":
        return cls(**data)


# ============================================================================
# GESTIONNAIRE D'OBJETS ALCHIMIQUES
# ============================================================================

class AlchemicalItemManager:
    """Gestionnaire des objets alchimiques et coffres"""
    
    def __init__(self, data_dir: str = None):
        base_path = Path(__file__).parent.parent
        self.data_dir = Path(data_dir) if data_dir else base_path / "alchemical_vault"
        
        self.items_dir = self.data_dir / "items"
        self.chests_dir = self.data_dir / "chests"
        
        self.items_dir.mkdir(parents=True, exist_ok=True)
        self.chests_dir.mkdir(parents=True, exist_ok=True)
        
        self._items: Dict[str, AlchemicalItem] = {}
        self._chests: Dict[str, AlchemicalChest] = {}
        self._load_all()
    
    def _load_all(self):
        """Charge tous les objets et coffres"""
        for f in self.items_dir.glob("item_*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                self._items[data['item_id']] = AlchemicalItem.from_dict(data)
            except Exception as e:
                print(f"[WARN] Error loading {f}: {e}")
        
        for f in self.chests_dir.glob("chest_*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                self._chests[data['chest_id']] = AlchemicalChest.from_dict(data)
            except Exception as e:
                print(f"[WARN] Error loading {f}: {e}")
    
    def _save_item(self, item: AlchemicalItem):
        filepath = self.items_dir / f"item_{item.item_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(item.to_dict(), f, indent=2, ensure_ascii=False)
        self._items[item.item_id] = item
    
    def _save_chest(self, chest: AlchemicalChest):
        filepath = self.chests_dir / f"chest_{chest.chest_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(chest.to_dict(), f, indent=2, ensure_ascii=False)
        self._chests[chest.chest_id] = chest
    
    # ========================================================================
    # GENERATION D'OBJETS
    # ========================================================================
    
    def generate_item(self, vault_number: int,
                     item_type: str = None,
                     force_rarity: ItemRarity = None,
                     rarity_boost: float = 0.0) -> AlchemicalItem:
        """Genere un nouvel objet alchimique"""
        
        # Type d'objet
        if item_type and item_type in ALCHEMICAL_ITEMS:
            chosen_type = item_type
        else:
            # Choisir un type aleatoire
            available = list(ALCHEMICAL_ITEMS.keys())
            chosen_type = secrets.choice(available)
        
        item_def = ALCHEMICAL_ITEMS[chosen_type]
        
        # Rarete
        if force_rarity:
            rarity = force_rarity
        else:
            # Verifier la rarete minimum
            min_rarity = item_def.get('min_rarity')
            if min_rarity:
                min_idx = [r.rarity_id for r in ItemRarity].index(min_rarity)
                eligible = [r for r in ItemRarity if [r2.rarity_id for r2 in ItemRarity].index(r.rarity_id) >= min_idx]
            else:
                eligible = list(ItemRarity)
            
            # Poids avec boost
            weights = {}
            for r in eligible:
                base_weight = RARITY_WEIGHTS.get(r, 100)
                if rarity_boost > 0:
                    # Le boost favorise les raretes plus elevees
                    idx = list(ItemRarity).index(r)
                    boost_factor = 1 + (rarity_boost * idx / 10)
                    weights[r] = base_weight * boost_factor
                else:
                    weights[r] = base_weight
            
            # Selection
            total = sum(weights.values())
            roll = secrets.randbelow(int(total))
            cumulative = 0
            rarity = ItemRarity.COMMON
            for r, w in weights.items():
                cumulative += w
                if roll < cumulative:
                    rarity = r
                    break
        
        # Valeurs
        min_val, max_val = item_def.get('value_range', (1, 100))
        value = min_val + secrets.randbelow(int(max_val - min_val + 1))
        value *= rarity.multiplier
        
        min_dur, max_dur = item_def.get('duration_range', (0, 0))
        duration = min_dur + secrets.randbelow(max(1, int(max_dur - min_dur + 1))) if max_dur > 0 else 0
        
        # Charges
        max_charges = item_def.get('charges', 1) if isinstance(item_def.get('charges'), int) else 1
        
        # ID unique
        item_id = hashlib.sha256(
            f"{chosen_type}{rarity.rarity_id}{datetime.now().isoformat()}{secrets.token_hex(8)}".encode()
        ).hexdigest()[:16]
        
        item = AlchemicalItem(
            item_id=item_id,
            item_type=chosen_type,
            category=item_def['category'],
            rarity=rarity.rarity_id,
            value=round(value, 2),
            duration=duration,
            charges=max_charges,
            max_charges=max_charges,
            origin_vault=vault_number,
            current_vault=vault_number,
            created_at=datetime.now().isoformat()
        )
        
        self._save_item(item)
        return item
    
    # ========================================================================
    # COFFRES
    # ========================================================================
    
    def generate_chest(self, vault_number: int, 
                      tier: ChestTier = None,
                      tier_name: str = None) -> AlchemicalChest:
        """Genere un nouveau coffre"""
        
        # Determiner le tier
        if tier:
            chosen_tier = tier
        elif tier_name:
            chosen_tier = next((t for t in ChestTier if t.tier_id == tier_name.lower()), ChestTier.COMMON)
        else:
            # Aleatoire avec poids
            total = sum(t.drop_weight for t in ChestTier)
            roll = secrets.randbelow(total)
            cumulative = 0
            chosen_tier = ChestTier.COMMON
            for t in ChestTier:
                cumulative += t.drop_weight
                if roll < cumulative:
                    chosen_tier = t
                    break
        
        # ID unique
        chest_id = hashlib.sha256(
            f"chest_{chosen_tier.tier_id}{datetime.now().isoformat()}{secrets.token_hex(8)}".encode()
        ).hexdigest()[:16]
        
        # Bonus selon le tier
        rarity_boost = {
            ChestTier.PRIMORDIAL: 2.0,
            ChestTier.LEGENDARY: 1.5,
            ChestTier.EPIC: 1.0,
            ChestTier.RARE: 0.5,
            ChestTier.COMMON: 0.0,
        }.get(chosen_tier, 0.0)
        
        guaranteed_legendary = chosen_tier in [ChestTier.PRIMORDIAL, ChestTier.LEGENDARY]
        
        chest = AlchemicalChest(
            chest_id=chest_id,
            tier=chosen_tier.tier_id,
            item_count=chosen_tier.item_count,
            origin_vault=vault_number,
            created_at=datetime.now().isoformat(),
            bonus_rarity_boost=rarity_boost,
            guaranteed_legendary=guaranteed_legendary
        )
        
        self._save_chest(chest)
        return chest
    
    def open_chest(self, chest_id: str, opener_vault: int) -> Tuple[bool, List[AlchemicalItem], str]:
        """Ouvre un coffre et genere son contenu"""
        
        chest = self._chests.get(chest_id)
        if not chest:
            return False, [], "Coffre non trouve"
        
        if chest.is_opened:
            return False, [], "Coffre deja ouvert"
        
        tier = next((t for t in ChestTier if t.tier_id == chest.tier), ChestTier.COMMON)
        
        # Generer les items
        items = []
        
        # Item legendaire garanti?
        if chest.guaranteed_legendary:
            item = self.generate_item(
                opener_vault,
                force_rarity=ItemRarity.LEGENDARY,
                rarity_boost=chest.bonus_rarity_boost
            )
            items.append(item)
            chest.items.append(item.item_id)
        
        # Reste des items
        remaining = chest.item_count - len(items)
        for _ in range(remaining):
            item = self.generate_item(
                opener_vault,
                rarity_boost=chest.bonus_rarity_boost
            )
            items.append(item)
            chest.items.append(item.item_id)
        
        # Marquer comme ouvert
        chest.is_opened = True
        chest.opened_at = datetime.now().isoformat()
        chest.opened_by_vault = opener_vault
        
        self._save_chest(chest)
        
        return True, items, f"Coffre {tier.display_name} ouvert! {len(items)} objets obtenus."
    
    # ========================================================================
    # DISTRIBUTION PAR TIER DE VAULT
    # ========================================================================
    
    def distribute_chests_for_vault(self, vault_number: int, vault_tier: str,
                                   artifact_rarity: str = None) -> List[AlchemicalChest]:
        """Distribue des coffres selon le tier du vault"""
        
        # Configuration par tier
        TIER_CHEST_CONFIG = {
            "primordial": [
                (ChestTier.PRIMORDIAL, 1),
                (ChestTier.LEGENDARY, 2),
                (ChestTier.EPIC, 3),
            ],
            "transcendent": [
                (ChestTier.LEGENDARY, 1),
                (ChestTier.EPIC, 2),
                (ChestTier.RARE, 3),
            ],
            "mythic": [
                (ChestTier.LEGENDARY, 1),
                (ChestTier.EPIC, 1),
                (ChestTier.RARE, 3),
            ],
            "legendary": [
                (ChestTier.EPIC, 1),
                (ChestTier.RARE, 2),
                (ChestTier.COMMON, 2),
            ],
            "epic": [
                (ChestTier.RARE, 2),
                (ChestTier.COMMON, 3),
            ],
            "rare": [
                (ChestTier.RARE, 1),
                (ChestTier.COMMON, 2),
            ],
            "quantum_pioneer": [
                (ChestTier.LEGENDARY, 1),
                (ChestTier.EPIC, 2),
                (ChestTier.RARE, 2),
            ],
        }
        
        # Bonus pour rarete d'artefact elevee
        artifact_bonus = {
            "primordial": [(ChestTier.PRIMORDIAL, 1)],
            "transcendent": [(ChestTier.LEGENDARY, 1)],
            "mythic": [(ChestTier.EPIC, 1)],
        }
        
        config = TIER_CHEST_CONFIG.get(vault_tier.lower(), [(ChestTier.COMMON, 1)])
        
        # Ajouter bonus artefact
        if artifact_rarity and artifact_rarity.lower() in artifact_bonus:
            config = config + artifact_bonus[artifact_rarity.lower()]
        
        chests = []
        for tier, count in config:
            for _ in range(count):
                chest = self.generate_chest(vault_number, tier=tier)
                chests.append(chest)
        
        return chests
    
    # ========================================================================
    # LIENS AVEC GEMMES ET ARTEFACTS
    # ========================================================================
    
    def link_to_gem(self, item_id: str, gem_id: str) -> Tuple[bool, str]:
        """Lie un objet a une gemme"""
        item = self._items.get(item_id)
        if not item:
            return False, "Objet non trouve"
        
        item_def = ALCHEMICAL_ITEMS.get(item.item_type, {})
        
        # Verifier si l'objet peut etre lie a une gemme
        if item_def.get('enchant_type') not in ['gem', None]:
            if not item_def.get('enchant_type') == 'artifact':
                pass  # OK pour les items generiques
            else:
                return False, "Cet objet ne peut etre lie qu'a un artefact"
        
        item.linked_gem_id = gem_id
        item.is_bound = True
        item.bound_to = gem_id
        
        self._save_item(item)
        return True, f"Objet lie a la gemme {gem_id[:8]}"
    
    def link_to_artifact(self, item_id: str, artifact_id: str) -> Tuple[bool, str]:
        """Lie un objet a un artefact"""
        item = self._items.get(item_id)
        if not item:
            return False, "Objet non trouve"
        
        item_def = ALCHEMICAL_ITEMS.get(item.item_type, {})
        
        # Verifier si l'objet peut etre lie a un artefact
        if item_def.get('enchant_type') == 'gem':
            return False, "Cet objet ne peut etre lie qu'a une gemme"
        
        item.linked_artifact_id = artifact_id
        item.is_bound = True
        item.bound_to = artifact_id
        
        self._save_item(item)
        return True, f"Objet lie a l'artefact {artifact_id[:8]}"
    
    def enchant(self, item_id: str, target_id: str, target_type: str) -> Tuple[bool, str]:
        """Enchante un objet cible avec une rune"""
        item = self._items.get(item_id)
        if not item:
            return False, "Objet non trouve"
        
        if item.category != "rune":
            return False, "Seules les runes peuvent enchanter"
        
        if item.charges <= 0:
            return False, "Plus de charges"
        
        item.enchanted_on = target_id
        item.charges -= 1
        
        if item.charges <= 0:
            item.status = "consumed"
        
        self._save_item(item)
        return True, f"Enchantement applique: {item.effect_description}"
    
    # ========================================================================
    # UTILITAIRES
    # ========================================================================
    
    def get_item(self, item_id: str) -> Optional[AlchemicalItem]:
        return self._items.get(item_id)
    
    def get_chest(self, chest_id: str) -> Optional[AlchemicalChest]:
        return self._chests.get(chest_id)
    
    def get_vault_items(self, vault_number: int) -> List[AlchemicalItem]:
        return [i for i in self._items.values() 
                if i.current_vault == vault_number and i.status != "consumed"]
    
    def get_vault_chests(self, vault_number: int, unopened_only: bool = False) -> List[AlchemicalChest]:
        chests = [c for c in self._chests.values() if c.origin_vault == vault_number]
        if unopened_only:
            chests = [c for c in chests if not c.is_opened]
        return chests
    
    def get_statistics(self) -> Dict:
        """Statistiques globales"""
        items = list(self._items.values())
        chests = list(self._chests.values())
        
        by_category = {}
        by_rarity = {}
        
        for item in items:
            by_category[item.category] = by_category.get(item.category, 0) + 1
            by_rarity[item.rarity] = by_rarity.get(item.rarity, 0) + 1
        
        return {
            "total_items": len(items),
            "total_chests": len(chests),
            "unopened_chests": sum(1 for c in chests if not c.is_opened),
            "by_category": by_category,
            "by_rarity": by_rarity,
            "total_value": sum(i.effective_power for i in items),
        }


# ============================================================================
# AFFICHAGE
# ============================================================================

def format_item_display(item: AlchemicalItem) -> str:
    """Format d'affichage d'un objet"""
    cat = next((c for c in AlchemicalCategory if c.cat_id == item.category), None)
    rarity = next((r for r in ItemRarity if r.rarity_id == item.rarity), ItemRarity.COMMON)
    
    symbol = cat.symbol if cat else "?"
    charges = f" [{item.charges}/{item.max_charges}]" if item.max_charges > 1 else ""
    
    return f"{symbol} [{rarity.display_name[:4].upper()}] {item.display_name}{charges}"


def format_chest_display(chest: AlchemicalChest) -> str:
    """Format d'affichage d'un coffre"""
    tier = next((t for t in ChestTier if t.tier_id == chest.tier), ChestTier.COMMON)
    status = "✓ Ouvert" if chest.is_opened else f"🔒 {chest.item_count} objets"
    
    return f"📦 {tier.display_name} | {status}"


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  ALCHEMICAL ITEMS SYSTEM")
    print("="*70)
    
    manager = AlchemicalItemManager()
    stats = manager.get_statistics()
    
    print(f"\n  Total Items: {stats['total_items']}")
    print(f"  Total Chests: {stats['total_chests']}")
    print(f"  Unopened: {stats['unopened_chests']}")
    
    print(f"\n  ITEM TYPES ({len(ALCHEMICAL_ITEMS)}):")
    for cat in AlchemicalCategory:
        count = len([k for k, v in ALCHEMICAL_ITEMS.items() if v['category'] == cat.cat_id])
        print(f"    {cat.symbol} {cat.display_name:15}: {count} types")
    
    print(f"\n  CHEST TIERS:")
    for tier in ChestTier:
        print(f"    📦 {tier.display_name:20} | {tier.item_count:2} items | Weight: {tier.drop_weight}")
    
    print(f"\n  RARITIES:")
    for rarity in ItemRarity:
        print(f"    [{rarity.display_name:12}] x{rarity.multiplier:.1f}")
    
    print("\n" + "="*70)
