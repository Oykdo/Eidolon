"""
Galerie d'Artefacts Interactive pour Poly-Spinor Nexus 7D
=========================================================

Interface de visualisation des artefacts avec:
- Cartes d'artefacts animees
- Details complets avec stats
- Filtres et tri
- Vue grille/liste
- Export et partage
"""

import sys
import json
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Dict, List, Any
from datetime import datetime
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Imports
try:
    from core.artifact_vault import ArtifactVault, DetachableArtifact, ArtifactStatus
    from core.artifact_system import (
        ArtifactRarity, RARITY_COLORS, ElementalAffinity, 
        ELEMENT_SYMBOLS, ELEMENT_COLORS, ARTIFACT_EMOJIS, ArtifactType
    )
    from core.artifact_ranking import ArtifactPowerSystem, POWER_TIER_CONFIG, PowerTier
except ImportError:
    pass


# ============================================================================
# THEME GALERIE
# ============================================================================

class GalleryTheme:
    """Theme visuel pour la galerie"""
    # Backgrounds
    BG_DARK = "#0a0a15"
    BG_CARD = "#12121f"
    BG_CARD_HOVER = "#1a1a2f"
    BG_HEADER = "#0f0f1a"
    
    # Accents
    NEON_PURPLE = "#bf00ff"
    NEON_CYAN = "#00ffff"
    NEON_GREEN = "#00ff88"
    NEON_GOLD = "#ffd700"
    
    # Text
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#888899"
    TEXT_MUTED = "#555566"
    
    # Rarity colors
    RARITY_COLORS = {
        'common': '#9d9d9d',
        'uncommon': '#1eff00',
        'rare': '#0070dd',
        'epic': '#a335ee',
        'legendary': '#ff8000',
        'mythic': '#e6cc80',
        'transcendent': '#00ffff',
        'primordial': '#ff00ff',
    }
    
    # Fonts
    FONT_TITLE = ("Consolas", 16, "bold")
    FONT_SUBTITLE = ("Consolas", 12, "bold")
    FONT_NORMAL = ("Segoe UI", 10)
    FONT_SMALL = ("Segoe UI", 9)
    FONT_MONO = ("Consolas", 10)


# ============================================================================
# CARTE D'ARTEFACT
# ============================================================================

class ArtifactCard(tk.Frame):
    """Carte visuelle d'un artefact"""
    
    def __init__(self, parent, artifact: DetachableArtifact, on_click=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.artifact = artifact
        self.on_click = on_click
        self.selected = False
        
        self.configure(
            bg=GalleryTheme.BG_CARD,
            highlightthickness=2,
            highlightbackground=GalleryTheme.RARITY_COLORS.get(artifact.rarity, '#333'),
            padx=10,
            pady=10
        )
        
        self._create_card()
        self._bind_events()
    
    def _create_card(self):
        """Cree le contenu de la carte"""
        art = self.artifact.artifact_data
        rarity = self.artifact.rarity
        color = GalleryTheme.RARITY_COLORS.get(rarity, '#fff')
        
        # Header avec type et element
        header = tk.Frame(self, bg=GalleryTheme.BG_CARD)
        header.pack(fill=tk.X, pady=(0, 5))
        
        art_type = art.get('artifact_type', 'unknown')
        emoji = ARTIFACT_EMOJIS.get(ArtifactType(art_type), '?') if art_type != 'unknown' else '?'
        
        type_lbl = tk.Label(
            header,
            text=emoji,
            bg=GalleryTheme.BG_CARD,
            fg=color,
            font=("Segoe UI", 20)
        )
        type_lbl.pack(side=tk.LEFT)
        
        element = art.get('element', 'void')
        try:
            element_sym = ELEMENT_SYMBOLS.get(ElementalAffinity(element), '?')
            element_color = ELEMENT_COLORS.get(ElementalAffinity(element), '#fff')
        except:
            element_sym = '?'
            element_color = '#fff'
        
        element_lbl = tk.Label(
            header,
            text=element_sym,
            bg=GalleryTheme.BG_CARD,
            fg=element_color,
            font=("Segoe UI", 16)
        )
        element_lbl.pack(side=tk.RIGHT)
        
        # Rarete
        rarity_lbl = tk.Label(
            self,
            text=f"[{rarity.upper()}]",
            bg=GalleryTheme.BG_CARD,
            fg=color,
            font=GalleryTheme.FONT_SMALL
        )
        rarity_lbl.pack()
        
        # Nom
        name_lbl = tk.Label(
            self,
            text=art.get('name', 'Unknown'),
            bg=GalleryTheme.BG_CARD,
            fg=color,
            font=GalleryTheme.FONT_SUBTITLE,
            wraplength=180
        )
        name_lbl.pack(pady=5)
        
        # Puissance
        stats = art.get('stats', {})
        power = stats.get('effective_power', 0)
        
        power_frame = tk.Frame(self, bg=GalleryTheme.BG_CARD)
        power_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(
            power_frame,
            text="PWR",
            bg=GalleryTheme.BG_CARD,
            fg=GalleryTheme.TEXT_SECONDARY,
            font=GalleryTheme.FONT_SMALL
        ).pack(side=tk.LEFT)
        
        tk.Label(
            power_frame,
            text=f"{power:,.0f}",
            bg=GalleryTheme.BG_CARD,
            fg=GalleryTheme.NEON_GREEN,
            font=GalleryTheme.FONT_MONO
        ).pack(side=tk.RIGHT)
        
        # Stats secondaires
        resonance = stats.get('spinor_resonance', 0)
        stability = stats.get('stability', 0)
        
        stats_frame = tk.Frame(self, bg=GalleryTheme.BG_CARD)
        stats_frame.pack(fill=tk.X)
        
        tk.Label(
            stats_frame,
            text=f"RES:{resonance:.0f}%",
            bg=GalleryTheme.BG_CARD,
            fg=GalleryTheme.TEXT_MUTED,
            font=("Consolas", 8)
        ).pack(side=tk.LEFT)
        
        tk.Label(
            stats_frame,
            text=f"STB:{stability}%",
            bg=GalleryTheme.BG_CARD,
            fg=GalleryTheme.TEXT_MUTED,
            font=("Consolas", 8)
        ).pack(side=tk.RIGHT)
        
        # Status
        status_icons = {
            ArtifactStatus.ATTACHED: ("🔗", GalleryTheme.NEON_GREEN),
            ArtifactStatus.DETACHED: ("📦", GalleryTheme.NEON_CYAN),
            ArtifactStatus.TRANSFERRED: ("↗", GalleryTheme.NEON_PURPLE),
            ArtifactStatus.LOCKED: ("🔒", GalleryTheme.NEON_GOLD),
        }
        
        icon, status_color = status_icons.get(
            self.artifact.status, 
            ("?", GalleryTheme.TEXT_MUTED)
        )
        
        status_lbl = tk.Label(
            self,
            text=f"{icon} {self.artifact.status.value.upper()}",
            bg=GalleryTheme.BG_CARD,
            fg=status_color,
            font=GalleryTheme.FONT_SMALL
        )
        status_lbl.pack(pady=(5, 0))
        
        # Origine
        origin_lbl = tk.Label(
            self,
            text=f"Origin: #{self.artifact.origin_vault_number}",
            bg=GalleryTheme.BG_CARD,
            fg=GalleryTheme.TEXT_MUTED,
            font=("Consolas", 8)
        )
        origin_lbl.pack()
        
        # Badge fondateur
        if self.artifact.is_founder_artifact:
            founder_lbl = tk.Label(
                self,
                text="⭐ FOUNDER",
                bg=GalleryTheme.BG_CARD,
                fg=GalleryTheme.NEON_GOLD,
                font=("Consolas", 9, "bold")
            )
            founder_lbl.pack(pady=(5, 0))
    
    def _bind_events(self):
        """Lie les evenements"""
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        
        # Propager aux enfants
        for child in self.winfo_children():
            child.bind("<Button-1>", self._on_click)
    
    def _on_enter(self, event):
        self.configure(bg=GalleryTheme.BG_CARD_HOVER)
        for child in self.winfo_children():
            if isinstance(child, (tk.Label, tk.Frame)):
                try:
                    child.configure(bg=GalleryTheme.BG_CARD_HOVER)
                except:
                    pass
    
    def _on_leave(self, event):
        bg = GalleryTheme.BG_CARD if not self.selected else GalleryTheme.BG_CARD_HOVER
        self.configure(bg=bg)
        for child in self.winfo_children():
            if isinstance(child, (tk.Label, tk.Frame)):
                try:
                    child.configure(bg=bg)
                except:
                    pass
    
    def _on_click(self, event):
        if self.on_click:
            self.on_click(self.artifact)
    
    def set_selected(self, selected: bool):
        self.selected = selected
        color = GalleryTheme.NEON_CYAN if selected else GalleryTheme.RARITY_COLORS.get(self.artifact.rarity, '#333')
        self.configure(highlightbackground=color)


# ============================================================================
# GALERIE PRINCIPALE
# ============================================================================

class ArtifactGallery(tk.Toplevel):
    """Fenetre de galerie d'artefacts"""
    
    def __init__(self, parent, vault_number: int = None):
        super().__init__(parent)
        
        self.vault_number = vault_number
        self.artifact_vault = ArtifactVault()
        self.power_system = ArtifactPowerSystem(self.artifact_vault)
        
        self.selected_artifact: Optional[DetachableArtifact] = None
        self.cards: List[ArtifactCard] = []
        
        # Filtres
        self.filter_rarity = tk.StringVar(value="all")
        self.filter_element = tk.StringVar(value="all")
        self.filter_status = tk.StringVar(value="all")
        self.sort_by = tk.StringVar(value="power")
        
        self._setup_window()
        self._create_ui()
        self._load_artifacts()
    
    def _setup_window(self):
        """Configure la fenetre"""
        title = f"Artifact Gallery - Vault #{self.vault_number}" if self.vault_number else "Artifact Gallery - All"
        self.title(title)
        self.geometry("1200x800")
        self.configure(bg=GalleryTheme.BG_DARK)
        self.minsize(900, 600)
    
    def _create_ui(self):
        """Cree l'interface"""
        # Header
        self._create_header()
        
        # Main content
        main = tk.Frame(self, bg=GalleryTheme.BG_DARK)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left: Filters + Gallery
        left_frame = tk.Frame(main, bg=GalleryTheme.BG_DARK)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self._create_filters(left_frame)
        self._create_gallery(left_frame)
        
        # Right: Details panel
        self._create_details_panel(main)
    
    def _create_header(self):
        """Cree le header"""
        header = tk.Frame(self, bg=GalleryTheme.BG_HEADER, height=60)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        # Titre
        title_frame = tk.Frame(header, bg=GalleryTheme.BG_HEADER)
        title_frame.pack(side=tk.LEFT, padx=20, pady=10)
        
        tk.Label(
            title_frame,
            text="⬡ ARTIFACT GALLERY",
            bg=GalleryTheme.BG_HEADER,
            fg=GalleryTheme.NEON_PURPLE,
            font=GalleryTheme.FONT_TITLE
        ).pack(side=tk.LEFT)
        
        # Stats rapides
        self.stats_label = tk.Label(
            header,
            text="",
            bg=GalleryTheme.BG_HEADER,
            fg=GalleryTheme.TEXT_SECONDARY,
            font=GalleryTheme.FONT_NORMAL
        )
        self.stats_label.pack(side=tk.RIGHT, padx=20)
    
    def _create_filters(self, parent):
        """Cree la barre de filtres"""
        filter_frame = tk.Frame(parent, bg=GalleryTheme.BG_DARK)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Rarete
        tk.Label(
            filter_frame,
            text="Rarity:",
            bg=GalleryTheme.BG_DARK,
            fg=GalleryTheme.TEXT_SECONDARY
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        rarity_options = ["all", "primordial", "transcendent", "mythic", "legendary", "epic", "rare", "uncommon", "common"]
        rarity_combo = ttk.Combobox(filter_frame, textvariable=self.filter_rarity, values=rarity_options, width=12)
        rarity_combo.pack(side=tk.LEFT, padx=(0, 15))
        rarity_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        
        # Element
        tk.Label(
            filter_frame,
            text="Element:",
            bg=GalleryTheme.BG_DARK,
            fg=GalleryTheme.TEXT_SECONDARY
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        element_options = ["all", "void", "quantum", "temporal", "spatial", "entropic", "harmonic", "celestial", "primordial"]
        element_combo = ttk.Combobox(filter_frame, textvariable=self.filter_element, values=element_options, width=12)
        element_combo.pack(side=tk.LEFT, padx=(0, 15))
        element_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        
        # Status
        tk.Label(
            filter_frame,
            text="Status:",
            bg=GalleryTheme.BG_DARK,
            fg=GalleryTheme.TEXT_SECONDARY
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        status_options = ["all", "attached", "detached", "transferred", "locked"]
        status_combo = ttk.Combobox(filter_frame, textvariable=self.filter_status, values=status_options, width=12)
        status_combo.pack(side=tk.LEFT, padx=(0, 15))
        status_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        
        # Sort
        tk.Label(
            filter_frame,
            text="Sort:",
            bg=GalleryTheme.BG_DARK,
            fg=GalleryTheme.TEXT_SECONDARY
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        sort_options = ["power", "rarity", "name", "origin"]
        sort_combo = ttk.Combobox(filter_frame, textvariable=self.sort_by, values=sort_options, width=10)
        sort_combo.pack(side=tk.LEFT)
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
    
    def _create_gallery(self, parent):
        """Cree la zone de galerie scrollable"""
        # Container avec scroll
        gallery_container = tk.Frame(parent, bg=GalleryTheme.BG_DARK)
        gallery_container.pack(fill=tk.BOTH, expand=True)
        
        # Canvas + scrollbar
        self.canvas = tk.Canvas(gallery_container, bg=GalleryTheme.BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(gallery_container, orient=tk.VERTICAL, command=self.canvas.yview)
        
        self.gallery_frame = tk.Frame(self.canvas, bg=GalleryTheme.BG_DARK)
        
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.gallery_frame, anchor=tk.NW)
        
        # Bind resize
        self.gallery_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Mouse wheel scroll
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
    
    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
    
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _create_details_panel(self, parent):
        """Cree le panneau de details"""
        self.details_frame = tk.Frame(parent, bg=GalleryTheme.BG_CARD, width=350)
        self.details_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.details_frame.pack_propagate(False)
        
        # Placeholder
        self.details_placeholder = tk.Label(
            self.details_frame,
            text="Select an artifact\nto view details",
            bg=GalleryTheme.BG_CARD,
            fg=GalleryTheme.TEXT_MUTED,
            font=GalleryTheme.FONT_NORMAL,
            justify=tk.CENTER
        )
        self.details_placeholder.pack(expand=True)
    
    def _load_artifacts(self):
        """Charge les artefacts"""
        if self.vault_number:
            self.artifacts = self.artifact_vault.get_artifacts_by_owner(self.vault_number)
        else:
            self.artifacts = self.artifact_vault.get_all_artifacts()
        
        self._update_stats()
        self._apply_filters()
    
    def _update_stats(self):
        """Met a jour les stats"""
        total_power = sum(a.power for a in self.artifacts)
        self.stats_label.configure(
            text=f"📦 {len(self.artifacts)} artifacts | ⚡ {total_power:,.0f} total power"
        )
    
    def _apply_filters(self):
        """Applique les filtres et rafraichit la galerie"""
        # Filtrer
        filtered = self.artifacts.copy()
        
        if self.filter_rarity.get() != "all":
            filtered = [a for a in filtered if a.rarity == self.filter_rarity.get()]
        
        if self.filter_element.get() != "all":
            filtered = [a for a in filtered 
                       if a.artifact_data.get('element') == self.filter_element.get()]
        
        if self.filter_status.get() != "all":
            filtered = [a for a in filtered 
                       if a.status.value == self.filter_status.get()]
        
        # Trier
        sort_key = self.sort_by.get()
        if sort_key == "power":
            filtered.sort(key=lambda x: x.power, reverse=True)
        elif sort_key == "rarity":
            rarity_order = ['primordial', 'transcendent', 'mythic', 'legendary', 'epic', 'rare', 'uncommon', 'common']
            filtered.sort(key=lambda x: rarity_order.index(x.rarity) if x.rarity in rarity_order else 99)
        elif sort_key == "name":
            filtered.sort(key=lambda x: x.name)
        elif sort_key == "origin":
            filtered.sort(key=lambda x: x.origin_vault_number)
        
        self._display_artifacts(filtered)
    
    def _display_artifacts(self, artifacts: List[DetachableArtifact]):
        """Affiche les artefacts dans la galerie"""
        # Clear
        for card in self.cards:
            card.destroy()
        self.cards = []
        
        # Calculer le nombre de colonnes
        col_count = 4
        
        # Creer les cartes
        for i, artifact in enumerate(artifacts):
            row = i // col_count
            col = i % col_count
            
            card = ArtifactCard(
                self.gallery_frame,
                artifact,
                on_click=self._on_artifact_click
            )
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            self.cards.append(card)
        
        # Configure grid weights
        for i in range(col_count):
            self.gallery_frame.columnconfigure(i, weight=1)
    
    def _on_artifact_click(self, artifact: DetachableArtifact):
        """Gere le clic sur un artefact"""
        # Deselectionner l'ancien
        for card in self.cards:
            card.set_selected(card.artifact.artifact_id == artifact.artifact_id)
        
        self.selected_artifact = artifact
        self._show_details(artifact)
    
    def _show_details(self, artifact: DetachableArtifact):
        """Affiche les details d'un artefact"""
        # Clear details frame
        for child in self.details_frame.winfo_children():
            child.destroy()
        
        art = artifact.artifact_data
        rarity = artifact.rarity
        color = GalleryTheme.RARITY_COLORS.get(rarity, '#fff')
        
        # Scroll frame
        canvas = tk.Canvas(self.details_frame, bg=GalleryTheme.BG_CARD, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.details_frame, orient=tk.VERTICAL, command=canvas.yview)
        content = tk.Frame(canvas, bg=GalleryTheme.BG_CARD)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0, 0), window=content, anchor=tk.NW, width=330)
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Header
        tk.Label(
            content,
            text=f"[{rarity.upper()}]",
            bg=GalleryTheme.BG_CARD,
            fg=color,
            font=GalleryTheme.FONT_SMALL
        ).pack(pady=(15, 0))
        
        tk.Label(
            content,
            text=art.get('name', 'Unknown'),
            bg=GalleryTheme.BG_CARD,
            fg=color,
            font=GalleryTheme.FONT_TITLE,
            wraplength=300
        ).pack(pady=5)
        
        # Type et Element
        art_type = art.get('artifact_type', 'unknown').replace('_', ' ').title()
        element = art.get('element', 'void').upper()
        
        tk.Label(
            content,
            text=f"{art_type} | {element}",
            bg=GalleryTheme.BG_CARD,
            fg=GalleryTheme.TEXT_SECONDARY,
            font=GalleryTheme.FONT_NORMAL
        ).pack()
        
        # Separator
        ttk.Separator(content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15, padx=20)
        
        # Stats
        stats_frame = tk.Frame(content, bg=GalleryTheme.BG_CARD)
        stats_frame.pack(fill=tk.X, padx=20)
        
        stats = art.get('stats', {})
        stat_items = [
            ("Power", f"{stats.get('effective_power', 0):,.0f}", GalleryTheme.NEON_GREEN),
            ("Resonance", f"{stats.get('spinor_resonance', 0):.1f}%", GalleryTheme.NEON_CYAN),
            ("Entropy", f"{stats.get('entropy_coefficient', 1):.2f}x", GalleryTheme.NEON_PURPLE),
            ("Stability", f"{stats.get('stability', 0)}%", GalleryTheme.TEXT_PRIMARY),
            ("Purity", f"{stats.get('purity', 0)}%", GalleryTheme.TEXT_PRIMARY),
            ("Coherence", f"{stats.get('coherence', 0)}%", GalleryTheme.TEXT_PRIMARY),
        ]
        
        for label, value, fg_color in stat_items:
            row = tk.Frame(stats_frame, bg=GalleryTheme.BG_CARD)
            row.pack(fill=tk.X, pady=2)
            
            tk.Label(row, text=label, bg=GalleryTheme.BG_CARD, 
                    fg=GalleryTheme.TEXT_SECONDARY, width=12, anchor='w').pack(side=tk.LEFT)
            tk.Label(row, text=value, bg=GalleryTheme.BG_CARD, 
                    fg=fg_color, font=GalleryTheme.FONT_MONO).pack(side=tk.RIGHT)
        
        # Separator
        ttk.Separator(content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15, padx=20)
        
        # Abilities
        abilities = art.get('abilities', [])
        if abilities:
            tk.Label(
                content,
                text="ABILITIES",
                bg=GalleryTheme.BG_CARD,
                fg=GalleryTheme.NEON_PURPLE,
                font=GalleryTheme.FONT_SUBTITLE
            ).pack(anchor='w', padx=20)
            
            for ab in abilities:
                ab_frame = tk.Frame(content, bg=GalleryTheme.BG_CARD)
                ab_frame.pack(fill=tk.X, padx=20, pady=3)
                
                tk.Label(
                    ab_frame,
                    text=f"◆ {ab.get('name', '')}",
                    bg=GalleryTheme.BG_CARD,
                    fg=color,
                    font=GalleryTheme.FONT_SMALL
                ).pack(anchor='w')
                
                tk.Label(
                    ab_frame,
                    text=ab.get('description', ''),
                    bg=GalleryTheme.BG_CARD,
                    fg=GalleryTheme.TEXT_SECONDARY,
                    font=("Segoe UI", 8),
                    wraplength=280,
                    justify='left'
                ).pack(anchor='w', padx=(10, 0))
        
        # Separator
        ttk.Separator(content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15, padx=20)
        
        # Signature
        signature = art.get('signature', {})
        if signature:
            tk.Label(
                content,
                text="SPINOR SIGNATURE",
                bg=GalleryTheme.BG_CARD,
                fg=GalleryTheme.NEON_CYAN,
                font=GalleryTheme.FONT_SUBTITLE
            ).pack(anchor='w', padx=20)
            
            sig_items = [
                ("Bell Violation", f"{signature.get('bell_violation', 0):.3f}"),
                ("Entanglement", f"{signature.get('entanglement_degree', 0):.3f}"),
                ("Quantum State", signature.get('quantum_state', 'N/A')[:16]),
            ]
            
            for label, value in sig_items:
                row = tk.Frame(content, bg=GalleryTheme.BG_CARD)
                row.pack(fill=tk.X, padx=20, pady=1)
                
                tk.Label(row, text=label, bg=GalleryTheme.BG_CARD,
                        fg=GalleryTheme.TEXT_SECONDARY, font=("Consolas", 8)).pack(side=tk.LEFT)
                tk.Label(row, text=value, bg=GalleryTheme.BG_CARD,
                        fg=GalleryTheme.TEXT_PRIMARY, font=("Consolas", 8)).pack(side=tk.RIGHT)
        
        # Separator
        ttk.Separator(content, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15, padx=20)
        
        # Lore
        lore = art.get('lore', '')
        if lore:
            tk.Label(
                content,
                text=f"\"{lore}\"",
                bg=GalleryTheme.BG_CARD,
                fg=GalleryTheme.TEXT_MUTED,
                font=("Segoe UI", 9, "italic"),
                wraplength=280,
                justify='center'
            ).pack(padx=20, pady=5)
        
        # Actions
        actions_frame = tk.Frame(content, bg=GalleryTheme.BG_CARD)
        actions_frame.pack(fill=tk.X, padx=20, pady=15)
        
        if artifact.status == ArtifactStatus.ATTACHED:
            detach_btn = tk.Button(
                actions_frame,
                text="📦 DETACH",
                command=lambda: self._detach_artifact(artifact),
                bg=GalleryTheme.BG_DARK,
                fg=GalleryTheme.NEON_CYAN,
                font=GalleryTheme.FONT_SMALL,
                relief=tk.FLAT,
                cursor="hand2"
            )
            detach_btn.pack(side=tk.LEFT, padx=2)
        
        if artifact.status in [ArtifactStatus.DETACHED, ArtifactStatus.TRANSFERRED]:
            lock_btn = tk.Button(
                actions_frame,
                text="🔒 LOCK",
                command=lambda: self._lock_artifact(artifact),
                bg=GalleryTheme.BG_DARK,
                fg=GalleryTheme.NEON_GOLD,
                font=GalleryTheme.FONT_SMALL,
                relief=tk.FLAT,
                cursor="hand2"
            )
            lock_btn.pack(side=tk.LEFT, padx=2)
        
        export_btn = tk.Button(
            actions_frame,
            text="💾 EXPORT",
            command=lambda: self._export_artifact(artifact),
            bg=GalleryTheme.BG_DARK,
            fg=GalleryTheme.TEXT_SECONDARY,
            font=GalleryTheme.FONT_SMALL,
            relief=tk.FLAT,
            cursor="hand2"
        )
        export_btn.pack(side=tk.RIGHT, padx=2)
    
    def _detach_artifact(self, artifact: DetachableArtifact):
        if messagebox.askyesno("Detach", f"Detach '{artifact.name}' from its genesis block?"):
            if self.artifact_vault.detach_artifact(artifact.artifact_id):
                messagebox.showinfo("Success", "Artifact detached successfully!")
                self._load_artifacts()
            else:
                messagebox.showerror("Error", "Failed to detach artifact")
    
    def _lock_artifact(self, artifact: DetachableArtifact):
        if messagebox.askyesno("Lock", f"Lock '{artifact.name}'? This cannot be undone!"):
            if self.artifact_vault.lock_artifact(artifact.artifact_id):
                messagebox.showinfo("Success", "Artifact locked!")
                self._load_artifacts()
    
    def _export_artifact(self, artifact: DetachableArtifact):
        filepath = filedialog.asksaveasfilename(
            title="Export Artifact",
            initialfile=f"artifact_{artifact.artifact_id}.json",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")]
        )
        
        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(artifact.to_dict(), f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Success", f"Artifact exported to {filepath}")


# ============================================================================
# FONCTION DE LANCEMENT
# ============================================================================

def launch_gallery(vault_number: int = None):
    """Lance la galerie d'artefacts"""
    root = tk.Tk()
    root.withdraw()
    
    gallery = ArtifactGallery(root, vault_number)
    gallery.mainloop()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Artifact Gallery")
    parser.add_argument("--vault", "-v", type=int, help="Filter by vault number")
    args = parser.parse_args()
    
    launch_gallery(args.vault)
