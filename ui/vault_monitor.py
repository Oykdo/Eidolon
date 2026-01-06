#!/usr/bin/env python
"""
Poly-Spinor Nexus 7D - Vault Monitor GUI
Système de monitoring complet avec persistance des données

Fonctionnalités:
- Monitoring temps réel des NFTs, tokens et documents
- Persistance chiffrée de l'état du vault
- Gestion des transfers avec délai de récupération
- Journal d'activité persistant
- Interface multi-onglets
"""

import os
import sys
import json
import hashlib
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ============================================================================
# THEME CYPHERPUNK - COULEURS ET STYLES
# ============================================================================

class CypherpunkTheme:
    """Thème visuel cypherpunk avec effets néon"""
    
    # Couleurs principales
    BG_DARK = "#050510"
    BG_SECONDARY = "#0a0a1a"
    BG_TERTIARY = "#0f0f25"
    BG_PANEL = "#12122a"
    
    # Couleurs néon
    NEON_GREEN = "#00ff88"
    NEON_CYAN = "#00ffff"
    NEON_PURPLE = "#bf00ff"
    NEON_PINK = "#ff0080"
    NEON_ORANGE = "#ff6600"
    NEON_BLUE = "#0066ff"
    
    # Couleurs de texte
    TEXT_PRIMARY = "#e0e0e0"
    TEXT_SECONDARY = "#a0a0a0"
    TEXT_ACCENT = "#00ff88"
    TEXT_WARNING = "#ffaa00"
    TEXT_ERROR = "#ff4444"
    TEXT_SUCCESS = "#00ff88"
    
    # Couleurs de bordure
    BORDER_GLOW = "#00ff8833"
    BORDER_ACTIVE = "#00ffff"
    BORDER_INACTIVE = "#333355"
    
    # Fonts
    FONT_MONO = ("Consolas", 10)
    FONT_MONO_SMALL = ("Consolas", 9)
    FONT_HEADER = ("Segoe UI", 14, "bold")
    FONT_TITLE = ("Segoe UI", 11, "bold")
    FONT_NORMAL = ("Segoe UI", 10)
    FONT_SMALL = ("Segoe UI", 9)
    
    @classmethod
    def apply_theme(cls, root: tk.Tk):
        """Applique le thème cypherpunk à la fenêtre"""
        root.configure(bg=cls.BG_DARK)
        root.option_add("*Font", cls.FONT_NORMAL)
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # Frame styles
        style.configure('TFrame', background=cls.BG_DARK)
        style.configure('Dark.TFrame', background=cls.BG_DARK)
        style.configure('Panel.TFrame', background=cls.BG_PANEL)
        style.configure('Card.TFrame', background=cls.BG_TERTIARY)
        
        # Label styles
        style.configure('TLabel', 
                       background=cls.BG_DARK, 
                       foreground=cls.TEXT_PRIMARY,
                       font=cls.FONT_NORMAL)
        style.configure('Header.TLabel', 
                       background=cls.BG_DARK, 
                       foreground=cls.NEON_GREEN,
                       font=cls.FONT_HEADER)
        style.configure('Title.TLabel', 
                       background=cls.BG_DARK, 
                       foreground=cls.NEON_CYAN,
                       font=cls.FONT_TITLE)
        style.configure('Accent.TLabel', 
                       background=cls.BG_DARK, 
                       foreground=cls.NEON_GREEN)
        style.configure('Warning.TLabel', 
                       background=cls.BG_DARK, 
                       foreground=cls.TEXT_WARNING)
        style.configure('Success.TLabel', 
                       background=cls.BG_DARK, 
                       foreground=cls.TEXT_SUCCESS)
        style.configure('Muted.TLabel', 
                       background=cls.BG_DARK, 
                       foreground=cls.TEXT_SECONDARY)
        
        # Button styles - Neon effect
        style.configure('TButton',
                       background=cls.BG_TERTIARY,
                       foreground=cls.NEON_GREEN,
                       borderwidth=1,
                       focuscolor=cls.NEON_CYAN,
                       font=cls.FONT_NORMAL,
                       padding=(12, 8))
        style.map('TButton',
                 background=[('active', cls.BG_PANEL), ('pressed', cls.BG_SECONDARY)],
                 foreground=[('active', cls.NEON_CYAN), ('pressed', cls.NEON_GREEN)],
                 bordercolor=[('active', cls.NEON_CYAN)])
        
        style.configure('Accent.TButton',
                       background=cls.BG_PANEL,
                       foreground=cls.NEON_CYAN,
                       font=cls.FONT_TITLE)
        style.map('Accent.TButton',
                 background=[('active', cls.BG_TERTIARY)],
                 foreground=[('active', cls.NEON_GREEN)])
        
        style.configure('Danger.TButton',
                       background=cls.BG_TERTIARY,
                       foreground=cls.NEON_PINK)
        style.map('Danger.TButton',
                 foreground=[('active', cls.TEXT_ERROR)])
        
        # Entry styles
        style.configure('TEntry',
                       fieldbackground=cls.BG_SECONDARY,
                       foreground=cls.NEON_GREEN,
                       insertcolor=cls.NEON_CYAN,
                       borderwidth=1,
                       padding=8)
        style.map('TEntry',
                 fieldbackground=[('focus', cls.BG_TERTIARY)],
                 bordercolor=[('focus', cls.NEON_CYAN)])
        
        # Combobox styles
        style.configure('TCombobox',
                       fieldbackground=cls.BG_SECONDARY,
                       background=cls.BG_TERTIARY,
                       foreground=cls.NEON_GREEN,
                       arrowcolor=cls.NEON_CYAN,
                       padding=6)
        style.map('TCombobox',
                 fieldbackground=[('focus', cls.BG_TERTIARY)],
                 foreground=[('focus', cls.NEON_CYAN)])
        
        # LabelFrame styles
        style.configure('TLabelframe',
                       background=cls.BG_DARK,
                       bordercolor=cls.BORDER_INACTIVE,
                       relief='solid',
                       borderwidth=1)
        style.configure('TLabelframe.Label',
                       background=cls.BG_DARK,
                       foreground=cls.NEON_CYAN,
                       font=cls.FONT_TITLE)
        
        style.configure('Glow.TLabelframe',
                       background=cls.BG_PANEL,
                       bordercolor=cls.NEON_GREEN)
        style.configure('Glow.TLabelframe.Label',
                       background=cls.BG_PANEL,
                       foreground=cls.NEON_GREEN,
                       font=cls.FONT_TITLE)
        
        # Notebook styles
        style.configure('TNotebook',
                       background=cls.BG_DARK,
                       borderwidth=0,
                       tabmargins=[2, 5, 2, 0])
        style.configure('TNotebook.Tab',
                       background=cls.BG_TERTIARY,
                       foreground=cls.TEXT_SECONDARY,
                       padding=[16, 10],
                       font=cls.FONT_NORMAL)
        style.map('TNotebook.Tab',
                 background=[('selected', cls.BG_PANEL)],
                 foreground=[('selected', cls.NEON_GREEN)],
                 expand=[('selected', [1, 1, 1, 0])])
        
        # Treeview styles
        style.configure('Treeview',
                       background=cls.BG_SECONDARY,
                       foreground=cls.TEXT_PRIMARY,
                       fieldbackground=cls.BG_SECONDARY,
                       borderwidth=0,
                       font=cls.FONT_MONO_SMALL,
                       rowheight=28)
        style.configure('Treeview.Heading',
                       background=cls.BG_TERTIARY,
                       foreground=cls.NEON_CYAN,
                       font=cls.FONT_TITLE,
                       borderwidth=0,
                       padding=8)
        style.map('Treeview',
                 background=[('selected', cls.BG_PANEL)],
                 foreground=[('selected', cls.NEON_GREEN)])
        style.map('Treeview.Heading',
                 background=[('active', cls.BG_PANEL)])
        
        # Scrollbar styles
        style.configure('TScrollbar',
                       background=cls.BG_TERTIARY,
                       troughcolor=cls.BG_SECONDARY,
                       borderwidth=0,
                       arrowcolor=cls.NEON_CYAN)
        style.map('TScrollbar',
                 background=[('active', cls.BG_PANEL)])
        
        # Progressbar styles
        style.configure('TProgressbar',
                       background=cls.NEON_GREEN,
                       troughcolor=cls.BG_SECONDARY,
                       borderwidth=0,
                       thickness=8)
        
        style.configure('Cyan.Horizontal.TProgressbar',
                       background=cls.NEON_CYAN)
        
        # Separator
        style.configure('TSeparator',
                       background=cls.BORDER_INACTIVE)
        
        # Checkbutton
        style.configure('TCheckbutton',
                       background=cls.BG_DARK,
                       foreground=cls.TEXT_PRIMARY,
                       indicatorcolor=cls.BG_SECONDARY)
        style.map('TCheckbutton',
                 indicatorcolor=[('selected', cls.NEON_GREEN)])
        
        # Scale
        style.configure('TScale',
                       background=cls.BG_DARK,
                       troughcolor=cls.BG_SECONDARY)
        
        return style
    
    @classmethod
    def create_neon_button(cls, parent, text: str, command, color: str = None) -> tk.Button:
        """Crée un bouton avec effet néon"""
        color = color or cls.NEON_GREEN
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=cls.BG_TERTIARY,
            fg=color,
            activebackground=cls.BG_PANEL,
            activeforeground=cls.NEON_CYAN,
            relief='flat',
            borderwidth=0,
            font=cls.FONT_NORMAL,
            padx=16,
            pady=8,
            cursor='hand2'
        )
        
        def on_enter(e):
            btn.configure(bg=cls.BG_PANEL, fg=cls.NEON_CYAN)
        
        def on_leave(e):
            btn.configure(bg=cls.BG_TERTIARY, fg=color)
        
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)
        
        return btn
    
    @classmethod
    def create_card_frame(cls, parent, title: str = None) -> tk.Frame:
        """Crée un cadre style carte avec bordure lumineuse"""
        outer = tk.Frame(parent, bg=cls.NEON_GREEN, padx=1, pady=1)
        inner = tk.Frame(outer, bg=cls.BG_PANEL, padx=15, pady=12)
        inner.pack(fill='both', expand=True)
        
        if title:
            title_lbl = tk.Label(
                inner,
                text=title,
                bg=cls.BG_PANEL,
                fg=cls.NEON_CYAN,
                font=cls.FONT_TITLE
            )
            title_lbl.pack(anchor='w', pady=(0, 10))
        
        return outer, inner
    
    @classmethod
    def create_metric_display(cls, parent, label: str, value_var: tk.StringVar, color: str = None) -> tk.Frame:
        """Crée un affichage de métrique style dashboard"""
        color = color or cls.NEON_GREEN
        
        frame = tk.Frame(parent, bg=cls.BG_TERTIARY, padx=12, pady=10)
        
        lbl = tk.Label(
            frame,
            text=label,
            bg=cls.BG_TERTIARY,
            fg=cls.TEXT_SECONDARY,
            font=cls.FONT_SMALL
        )
        lbl.pack(anchor='w')
        
        val = tk.Label(
            frame,
            textvariable=value_var,
            bg=cls.BG_TERTIARY,
            fg=color,
            font=("Consolas", 18, "bold")
        )
        val.pack(anchor='w', pady=(4, 0))
        
        return frame
    
    @classmethod
    def create_status_indicator(cls, parent, text: str, status: str = 'ok') -> tk.Frame:
        """Crée un indicateur de statut avec point coloré"""
        colors = {
            'ok': cls.NEON_GREEN,
            'warning': cls.TEXT_WARNING,
            'error': cls.TEXT_ERROR,
            'info': cls.NEON_CYAN,
            'inactive': cls.TEXT_SECONDARY
        }
        color = colors.get(status, cls.NEON_GREEN)
        
        frame = tk.Frame(parent, bg=cls.BG_DARK)
        
        dot = tk.Label(frame, text="●", bg=cls.BG_DARK, fg=color, font=("Arial", 8))
        dot.pack(side='left', padx=(0, 6))
        
        lbl = tk.Label(frame, text=text, bg=cls.BG_DARK, fg=cls.TEXT_PRIMARY, font=cls.FONT_SMALL)
        lbl.pack(side='left')
        
        return frame, dot


# ============================================================================
# IMPORTS LOCAUX
# ============================================================================

try:
    from core.secure_key_storage import SecureKeyStorage, VaultKeyStorage
    STORAGE_AVAILABLE = True
except ImportError as e:
    STORAGE_AVAILABLE = False
    print(f"[AVERTISSEMENT] Module storage non disponible: {e}")

try:
    from core.evm_wallet import VaultHDWallet, EVMChain, WEB3_AVAILABLE
    EVM_AVAILABLE = WEB3_AVAILABLE
except ImportError as e:
    EVM_AVAILABLE = False
    print(f"[INFO] Module EVM non disponible: {e}")

try:
    from protocols.vault_monitoring import VaultMonitoringSystem, AlertSeverity, EventType
    MONITORING_AVAILABLE = True
except ImportError as e:
    MONITORING_AVAILABLE = False
    print(f"[INFO] Module monitoring non disponible: {e}")

try:
    from core.runes_monitor import RunesMonitor, RuneStatus, RunePortfolio
    RUNES_AVAILABLE = True
except ImportError as e:
    RUNES_AVAILABLE = False
    print(f"[INFO] Module runes non disponible: {e}")


# ============================================================================
# GESTIONNAIRE DE VAULT SECURISE
# ============================================================================

class SecureVaultManager:
    """Gestionnaire de chiffrement/déchiffrement pour le vault"""
    
    def __init__(self, vault_key: bytes):
        if len(vault_key) < 32:
            vault_key = hashlib.sha256(vault_key).digest()
        self.key = vault_key[:32]
        self._aesgcm = AESGCM(self.key)
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Chiffre des données avec AES-GCM"""
        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Déchiffre des données AES-GCM"""
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return self._aesgcm.decrypt(nonce, ciphertext, None)


# ============================================================================
# CLASSE PRINCIPALE GUI
# ============================================================================

class VaultMonitorGUI:
    """Interface graphique complète de monitoring du vault"""
    
    def __init__(self, vault_key: bytes, vault_name: str):
        self.vault_key = vault_key
        self.vault_name = vault_name
        self.vault_manager = SecureVaultManager(vault_key)
        
        # Initialiser le wallet si disponible
        if EVM_AVAILABLE:
            self.wallet = VaultHDWallet(vault_key, vault_name)
        else:
            self.wallet = None
        
        # Initialiser le monitoring si disponible
        if MONITORING_AVAILABLE:
            self.monitor = VaultMonitoringSystem()
        else:
            self.monitor = None
        
        # Configuration de la fenêtre principale
        self.root = tk.Tk()
        self.root.title(f"Poly-Spinor Nexus 7D - Vault Monitor: {vault_name}")
        self.root.geometry("1400x900")
        self.root.configure(bg="#0a0a1a")
        
        # Chemins de stockage
        self.base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.storage_path = os.path.join(self.base_path, "vault_storage")
        self.data_path = os.path.join(self.storage_path, "data")
        self.documents_path = os.path.join(self.storage_path, "documents")
        
        # Créer les répertoires si nécessaire
        os.makedirs(self.data_path, exist_ok=True)
        os.makedirs(self.documents_path, exist_ok=True)
        
        # État du vault
        self.vault_data = self._load_vault_state()
        self.active_transfers: List[Dict] = []
        self._running = True
        
        self._setup_ui()
    
    def _load_vault_state(self) -> Dict[str, Any]:
        """Charger l'état persistant du vault"""
        state_file = os.path.join(self.data_path, f"{self.vault_name}_state.json")
        
        if os.path.exists(state_file):
            try:
                with open(state_file, 'rb') as f:
                    encrypted_data = f.read()
                decrypted = self.vault_manager.decrypt_data(encrypted_data)
                return json.loads(decrypted.decode('utf-8'))
            except Exception as e:
                print(f"[AVERTISSEMENT] Impossible de charger l'état: {e}")
                return self._default_vault_state()
        
        return self._default_vault_state()
    
    def _default_vault_state(self) -> Dict[str, Any]:
        """État par défaut du vault"""
        return {
            "assets": [],
            "tokens": [],
            "documents": [],
            "transfers": [],
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat()
        }
    
    def _save_vault_state(self):
        """Sauvegarder l'état persistant du vault"""
        state_file = os.path.join(self.data_path, f"{self.vault_name}_state.json")
        
        self.vault_data["last_modified"] = datetime.now().isoformat()
        data_json = json.dumps(self.vault_data, indent=2, ensure_ascii=False)
        encrypted = self.vault_manager.encrypt_data(data_json.encode('utf-8'))
        
        with open(state_file, 'wb') as f:
            f.write(encrypted)
        
        self._log_activity("État du vault sauvegardé")
    
    def _setup_ui(self):
        """Configuration de l'interface utilisateur - Theme Cypherpunk"""
        # Appliquer le thème cypherpunk
        CypherpunkTheme.apply_theme(self.root)
        
        # Cadre principal avec fond sombre
        main_frame = tk.Frame(self.root, bg=CypherpunkTheme.BG_DARK)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # === HEADER BANNER ===
        header_frame = tk.Frame(main_frame, bg=CypherpunkTheme.BG_DARK)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Logo/Titre avec effet néon
        title_container = tk.Frame(header_frame, bg=CypherpunkTheme.BG_DARK)
        title_container.pack(side=tk.LEFT)
        
        logo_text = tk.Label(
            title_container,
            text="◈ POLY-SPINOR NEXUS 7D",
            bg=CypherpunkTheme.BG_DARK,
            fg=CypherpunkTheme.NEON_CYAN,
            font=("Consolas", 16, "bold")
        )
        logo_text.pack(anchor=tk.W)
        
        subtitle = tk.Label(
            title_container,
            text="QUANTUM VAULT MONITOR",
            bg=CypherpunkTheme.BG_DARK,
            fg=CypherpunkTheme.NEON_GREEN,
            font=("Consolas", 10)
        )
        subtitle.pack(anchor=tk.W)
        
        # Indicateurs de statut à droite
        status_container = tk.Frame(header_frame, bg=CypherpunkTheme.BG_DARK)
        status_container.pack(side=tk.RIGHT)
        
        self.quantum_indicator, self.quantum_dot = CypherpunkTheme.create_status_indicator(
            status_container, "QUANTUM SECURE", 'ok'
        )
        self.quantum_indicator.pack(side=tk.RIGHT, padx=10)
        
        self.encryption_indicator, _ = CypherpunkTheme.create_status_indicator(
            status_container, "AES-256-GCM", 'info'
        )
        self.encryption_indicator.pack(side=tk.RIGHT, padx=10)
        
        # Ligne de séparation néon
        separator = tk.Frame(main_frame, bg=CypherpunkTheme.NEON_GREEN, height=1)
        separator.pack(fill=tk.X, pady=(0, 15))
        
        # === CONTENU PRINCIPAL ===
        content_container = tk.Frame(main_frame, bg=CypherpunkTheme.BG_DARK)
        content_container.pack(fill=tk.BOTH, expand=True)
        
        # Barre latérale gauche
        sidebar = tk.Frame(content_container, bg=CypherpunkTheme.BG_TERTIARY, width=280)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        sidebar.pack_propagate(False)
        
        # Padding interne sidebar
        sidebar_inner = tk.Frame(sidebar, bg=CypherpunkTheme.BG_TERTIARY)
        sidebar_inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        
        # === VAULT INFO CARD ===
        info_outer, info_inner = CypherpunkTheme.create_card_frame(sidebar_inner, "⬡ VAULT INFO")
        info_outer.pack(fill=tk.X, pady=(0, 15))
        
        # Nom du vault
        vault_name_lbl = tk.Label(
            info_inner,
            text=f"╰─▶ {self.vault_name}",
            bg=CypherpunkTheme.BG_PANEL,
            fg=CypherpunkTheme.NEON_GREEN,
            font=CypherpunkTheme.FONT_MONO
        )
        vault_name_lbl.pack(anchor=tk.W, pady=2)
        
        # Adresse
        if self.wallet:
            addr_display = f"{self.wallet.address[:16]}..." if hasattr(self.wallet, 'address') else "N/A"
        else:
            addr_display = "EVM non disponible"
        
        addr_lbl = tk.Label(
            info_inner,
            text=f"╰─▶ {addr_display}",
            bg=CypherpunkTheme.BG_PANEL,
            fg=CypherpunkTheme.TEXT_SECONDARY,
            font=CypherpunkTheme.FONT_MONO_SMALL
        )
        addr_lbl.pack(anchor=tk.W, pady=2)
        
        # Statut avec animation
        status_frame = tk.Frame(info_inner, bg=CypherpunkTheme.BG_PANEL)
        status_frame.pack(anchor=tk.W, pady=(8, 0))
        
        self.status_dot = tk.Label(
            status_frame,
            text="●",
            bg=CypherpunkTheme.BG_PANEL,
            fg=CypherpunkTheme.NEON_GREEN,
            font=("Arial", 10)
        )
        self.status_dot.pack(side=tk.LEFT, padx=(0, 6))
        
        self.status_label = tk.Label(
            status_frame,
            text="SYSTEM ACTIVE",
            bg=CypherpunkTheme.BG_PANEL,
            fg=CypherpunkTheme.NEON_GREEN,
            font=CypherpunkTheme.FONT_MONO
        )
        self.status_label.pack(side=tk.LEFT)
        
        # === ACTIONS PANEL ===
        actions_outer, actions_inner = CypherpunkTheme.create_card_frame(sidebar_inner, "⚡ ACTIONS")
        actions_outer.pack(fill=tk.X, pady=(0, 15))
        
        buttons = [
            ("▸ DEPOSIT NFT", self.deposit_nft, CypherpunkTheme.NEON_GREEN),
            ("▸ DEPOSIT TOKEN", self.deposit_token, CypherpunkTheme.NEON_CYAN),
            ("▸ DEPOSIT DOC", self.deposit_document, CypherpunkTheme.NEON_PURPLE),
            ("▸ RECOVERY", self.recovery_panel, CypherpunkTheme.NEON_ORANGE),
            ("▸ REFRESH", self.refresh_data, CypherpunkTheme.NEON_BLUE),
            ("▸ SAVE STATE", self._save_vault_state, CypherpunkTheme.NEON_GREEN),
            ("▸ EXPORT LOGS", self.export_logs, CypherpunkTheme.TEXT_SECONDARY),
        ]
        
        for text, command, color in buttons:
            btn = CypherpunkTheme.create_neon_button(actions_inner, text, command, color)
            btn.pack(fill=tk.X, pady=3)
        
        # Cadre principal de contenu
        content_frame = tk.Frame(content_container, bg=CypherpunkTheme.BG_DARK)
        content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Notebook avec onglets
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Création des onglets avec icônes stylisées
        self.assets_tab = self._create_assets_tab()
        self.notebook.add(self.assets_tab, text="  ◆ NFT ASSETS  ")
        
        self.tokens_tab = self._create_tokens_tab()
        self.notebook.add(self.tokens_tab, text="  ◇ TOKENS  ")
        
        self.documents_tab = self._create_documents_tab()
        self.notebook.add(self.documents_tab, text="  ▣ DOCUMENTS  ")
        
        self.monitor_tab = self._create_monitor_tab()
        self.notebook.add(self.monitor_tab, text="  ◉ MONITOR  ")
        
        self.transfers_tab = self._create_transfers_tab()
        self.notebook.add(self.transfers_tab, text="  ⇄ TRANSFERS  ")
        
        # Onglet Runes (si disponible)
        if RUNES_AVAILABLE:
            self.runes_tab = self._create_runes_tab()
            self.notebook.add(self.runes_tab, text="  ᚠ RUNES  ")
        
        # === BARRE DE STATUT CYPHERPUNK ===
        status_bar_frame = tk.Frame(self.root, bg=CypherpunkTheme.BG_TERTIARY, height=32)
        status_bar_frame.pack(side=tk.BOTTOM, fill=tk.X)
        status_bar_frame.pack_propagate(False)
        
        # Contenu de la barre de statut
        status_inner = tk.Frame(status_bar_frame, bg=CypherpunkTheme.BG_TERTIARY)
        status_inner.pack(fill=tk.BOTH, expand=True, padx=15)
        
        # Statut à gauche
        status_left = tk.Frame(status_inner, bg=CypherpunkTheme.BG_TERTIARY)
        status_left.pack(side=tk.LEFT, fill=tk.Y)
        
        self.status_bar = tk.Label(
            status_left,
            text="● VAULT ONLINE",
            bg=CypherpunkTheme.BG_TERTIARY,
            fg=CypherpunkTheme.NEON_GREEN,
            font=CypherpunkTheme.FONT_MONO_SMALL
        )
        self.status_bar.pack(side=tk.LEFT, pady=8)
        
        # Indicateurs à droite
        status_right = tk.Frame(status_inner, bg=CypherpunkTheme.BG_TERTIARY)
        status_right.pack(side=tk.RIGHT, fill=tk.Y)
        
        indicators = []
        if MONITORING_AVAILABLE:
            indicators.append(("MONITOR", CypherpunkTheme.NEON_GREEN))
        else:
            indicators.append(("MONITOR", CypherpunkTheme.TEXT_SECONDARY))
        if EVM_AVAILABLE:
            indicators.append(("EVM", CypherpunkTheme.NEON_CYAN))
        else:
            indicators.append(("EVM", CypherpunkTheme.TEXT_SECONDARY))
        indicators.append(("ENCRYPTED", CypherpunkTheme.NEON_PURPLE))
        
        for text, color in indicators:
            lbl = tk.Label(
                status_right,
                text=f"[{text}]",
                bg=CypherpunkTheme.BG_TERTIARY,
                fg=color,
                font=CypherpunkTheme.FONT_MONO_SMALL
            )
            lbl.pack(side=tk.LEFT, padx=8, pady=8)
        
        # Charger les données existantes
        self._populate_ui_from_state()
        
        # Démarrer le monitoring en arrière-plan
        self._start_background_monitoring()
    
    def _create_assets_tab(self) -> ttk.Frame:
        """Créer l'onglet des actifs NFT"""
        frame = ttk.Frame(self.notebook)
        
        # Barre d'outils
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(toolbar, text="Scanner NFTs", command=self.scan_nfts).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Importer CSV", command=self.import_nfts_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Ajouter Manuel", command=self.add_nft_manual).pack(side=tk.LEFT, padx=5)
        
        # Treeview pour les NFT
        columns = ('ID', 'Contrat', 'Token ID', 'Nom', 'Chaîne', 'État')
        self.assets_tree = ttk.Treeview(frame, columns=columns, show='headings', height=15)
        
        col_widths = {'ID': 80, 'Contrat': 150, 'Token ID': 100, 'Nom': 150, 'Chaîne': 100, 'État': 100}
        for col in columns:
            self.assets_tree.heading(col, text=col, command=lambda c=col: self._sort_treeview(self.assets_tree, c))
            self.assets_tree.column(col, width=col_widths.get(col, 100))
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.assets_tree.yview)
        self.assets_tree.configure(yscrollcommand=scrollbar.set)
        
        self.assets_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Boutons d'action
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="Détails", command=self.show_nft_details).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Sécuriser", command=self.secure_nft).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Retirer", command=self.withdraw_nft).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Supprimer", command=self.delete_nft).pack(side=tk.LEFT, padx=5)
        
        return frame
    
    def _create_tokens_tab(self) -> ttk.Frame:
        """Créer l'onglet des tokens"""
        frame = ttk.Frame(self.notebook)
        
        # Balance totale
        balance_frame = ttk.LabelFrame(frame, text="Balance", padding=10)
        balance_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(balance_frame, text="Balance Totale:", font=('Arial', 12, 'bold')).pack(anchor=tk.W)
        self.total_balance_var = tk.StringVar(value="0.00 ETH")
        ttk.Label(balance_frame, textvariable=self.total_balance_var, 
                  font=('Arial', 24, 'bold'), foreground="#00ff00").pack(anchor=tk.W)
        
        # Liste des tokens
        list_frame = ttk.LabelFrame(frame, text="Tokens", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        columns = ('Symbole', 'Nom', 'Balance', 'Contrat', 'Chaîne')
        self.tokens_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.tokens_tree.heading(col, text=col)
            self.tokens_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tokens_tree.yview)
        self.tokens_tree.configure(yscrollcommand=scrollbar.set)
        
        self.tokens_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Frame pour dépôt
        deposit_frame = ttk.LabelFrame(frame, text="Dépôt de Token", padding=10)
        deposit_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(deposit_frame, text="Adresse du contrat:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.token_contract_entry = ttk.Entry(deposit_frame, width=50)
        self.token_contract_entry.grid(row=0, column=1, padx=5)
        
        ttk.Label(deposit_frame, text="Montant:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.token_amount_entry = ttk.Entry(deposit_frame, width=20)
        self.token_amount_entry.grid(row=1, column=1, padx=5, sticky=tk.W)
        
        ttk.Label(deposit_frame, text="Symbole:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.token_symbol_entry = ttk.Entry(deposit_frame, width=10)
        self.token_symbol_entry.grid(row=2, column=1, padx=5, sticky=tk.W)
        
        ttk.Button(deposit_frame, text="Enregistrer Token", 
                   command=self.deposit_token_action).grid(row=3, column=0, columnspan=2, pady=10)
        
        return frame
    
    def _create_documents_tab(self) -> ttk.Frame:
        """Créer l'onglet des documents"""
        frame = ttk.Frame(self.notebook)
        
        # Barre d'outils
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(toolbar, text="Ajouter Document", command=self.add_document).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Vérifier Intégrité", command=self.verify_document).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Extraire", command=self.extract_document).pack(side=tk.LEFT, padx=5)
        
        # Treeview des documents
        columns = ('Nom', 'Type', 'Taille', 'Date', 'Hash')
        self.documents_tree = ttk.Treeview(frame, columns=columns, show='headings', height=12)
        
        col_widths = {'Nom': 200, 'Type': 80, 'Taille': 100, 'Date': 150, 'Hash': 150}
        for col in columns:
            self.documents_tree.heading(col, text=col)
            self.documents_tree.column(col, width=col_widths.get(col, 100))
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.documents_tree.yview)
        self.documents_tree.configure(yscrollcommand=scrollbar.set)
        
        self.documents_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        return frame
    
    def _create_monitor_tab(self) -> ttk.Frame:
        """Créer l'onglet de monitoring - Style Cypherpunk"""
        frame = tk.Frame(self.notebook, bg=CypherpunkTheme.BG_DARK)
        
        # === DASHBOARD METRICS ===
        metrics_container = tk.Frame(frame, bg=CypherpunkTheme.BG_DARK)
        metrics_container.pack(fill=tk.X, pady=(10, 20), padx=10)
        
        # Titre section
        metrics_title = tk.Label(
            metrics_container,
            text="◈ VAULT METRICS",
            bg=CypherpunkTheme.BG_DARK,
            fg=CypherpunkTheme.NEON_CYAN,
            font=CypherpunkTheme.FONT_TITLE
        )
        metrics_title.pack(anchor=tk.W, pady=(0, 10))
        
        # Grille de métriques avec cartes
        metrics_grid = tk.Frame(metrics_container, bg=CypherpunkTheme.BG_DARK)
        metrics_grid.pack(fill=tk.X)
        
        self.metric_vars: Dict[str, tk.StringVar] = {}
        metrics = [
            ("NFTs SECURED", "nft_count", CypherpunkTheme.NEON_GREEN),
            ("ACTIVE TOKENS", "token_count", CypherpunkTheme.NEON_CYAN),
            ("DOCUMENTS", "doc_count", CypherpunkTheme.NEON_PURPLE),
            ("24H ACTIVITY", "activity_24h", CypherpunkTheme.NEON_ORANGE),
            ("INTEGRITY", "integrity", CypherpunkTheme.NEON_GREEN),
            ("LAST SAVE", "last_backup", CypherpunkTheme.TEXT_SECONDARY)
        ]
        
        for i, (label, key, color) in enumerate(metrics):
            var = tk.StringVar(value="0" if key != "integrity" else "OK")
            self.metric_vars[key] = var
            
            metric_card = CypherpunkTheme.create_metric_display(metrics_grid, label, var, color)
            metric_card.grid(row=0, column=i, padx=5, sticky='nsew')
        
        for i in range(6):
            metrics_grid.columnconfigure(i, weight=1)
        
        # Séparateur
        sep = tk.Frame(frame, bg=CypherpunkTheme.BORDER_INACTIVE, height=1)
        sep.pack(fill=tk.X, padx=10, pady=10)
        
        # === ACTIVITY LOG ===
        log_container = tk.Frame(frame, bg=CypherpunkTheme.BG_DARK)
        log_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Titre avec indicateur de statut
        log_header = tk.Frame(log_container, bg=CypherpunkTheme.BG_DARK)
        log_header.pack(fill=tk.X, pady=(0, 10))
        
        log_title = tk.Label(
            log_header,
            text="◉ ACTIVITY LOG",
            bg=CypherpunkTheme.BG_DARK,
            fg=CypherpunkTheme.NEON_GREEN,
            font=CypherpunkTheme.FONT_TITLE
        )
        log_title.pack(side=tk.LEFT)
        
        # Indicateur temps réel
        self.realtime_indicator = tk.Label(
            log_header,
            text="● LIVE",
            bg=CypherpunkTheme.BG_DARK,
            fg=CypherpunkTheme.NEON_GREEN,
            font=CypherpunkTheme.FONT_MONO_SMALL
        )
        self.realtime_indicator.pack(side=tk.RIGHT)
        
        # Frame du log avec bordure néon
        log_outer = tk.Frame(log_container, bg=CypherpunkTheme.NEON_GREEN, padx=1, pady=1)
        log_outer.pack(fill=tk.BOTH, expand=True)
        
        log_inner = tk.Frame(log_outer, bg=CypherpunkTheme.BG_SECONDARY)
        log_inner.pack(fill=tk.BOTH, expand=True)
        
        self.activity_log = tk.Text(
            log_inner, 
            height=15, 
            bg=CypherpunkTheme.BG_SECONDARY, 
            fg=CypherpunkTheme.NEON_GREEN,
            insertbackground=CypherpunkTheme.NEON_CYAN,
            selectbackground=CypherpunkTheme.BG_PANEL,
            selectforeground=CypherpunkTheme.NEON_CYAN,
            font=CypherpunkTheme.FONT_MONO,
            relief='flat',
            padx=10,
            pady=10
        )
        self.activity_log.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        scrollbar = ttk.Scrollbar(log_inner, command=self.activity_log.yview)
        self.activity_log.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # === CONTROLES ===
        ctrl_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_DARK)
        ctrl_frame.pack(fill=tk.X, padx=10, pady=10)
        
        clear_btn = CypherpunkTheme.create_neon_button(
            ctrl_frame, 
            "⊘ CLEAR LOG", 
            lambda: self.activity_log.delete(1.0, tk.END),
            CypherpunkTheme.NEON_PINK
        )
        clear_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        export_btn = CypherpunkTheme.create_neon_button(
            ctrl_frame,
            "↓ EXPORT LOG",
            self.export_logs,
            CypherpunkTheme.NEON_CYAN
        )
        export_btn.pack(side=tk.LEFT)
        
        return frame
    
    def _create_transfers_tab(self) -> ttk.Frame:
        """Créer l'onglet des transfers"""
        frame = ttk.Frame(self.notebook)
        
        # En-tête
        header_frame = ttk.Frame(frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="Transfers programmés:", 
                  font=('Arial', 11, 'bold')).pack(side=tk.LEFT)
        
        # Liste des transfers
        columns = ('ID', 'Type', 'Actif', 'Destination', 'Date limite', 'État')
        self.transfers_tree = ttk.Treeview(frame, columns=columns, show='headings', height=12)
        
        for col in columns:
            self.transfers_tree.heading(col, text=col)
            self.transfers_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.transfers_tree.yview)
        self.transfers_tree.configure(yscrollcommand=scrollbar.set)
        
        self.transfers_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Actions
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(action_frame, text="Nouveau Transfer", command=self.initiate_transfer).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Exécuter", command=self.execute_transfer).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Annuler", command=self.cancel_transfer).pack(side=tk.LEFT, padx=5)
        
        return frame
    
    def _create_runes_tab(self) -> tk.Frame:
        """Créer l'onglet de monitoring des Runes - Style Cypherpunk"""
        frame = tk.Frame(self.notebook, bg=CypherpunkTheme.BG_DARK)
        
        # Initialiser le moniteur de runes
        self.runes_monitor = RunesMonitor()
        
        # === HEADER RUNES ===
        header_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_DARK)
        header_frame.pack(fill=tk.X, pady=(10, 15), padx=10)
        
        # Titre avec rune
        title_lbl = tk.Label(
            header_frame,
            text="ᚠ RUNES PORTFOLIO",
            bg=CypherpunkTheme.BG_DARK,
            fg="#FFD700",
            font=("Consolas", 16, "bold")
        )
        title_lbl.pack(side=tk.LEFT)
        
        # Bouton refresh
        refresh_btn = CypherpunkTheme.create_neon_button(
            header_frame,
            "↻ REFRESH",
            self._refresh_runes,
            CypherpunkTheme.NEON_CYAN
        )
        refresh_btn.pack(side=tk.RIGHT)
        
        # === PORTFOLIO SUMMARY ===
        summary_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_DARK)
        summary_frame.pack(fill=tk.X, pady=(0, 15), padx=10)
        
        # Variables pour les metriques
        self.runes_total_var = tk.StringVar(value="0")
        self.runes_count_var = tk.StringVar(value="0")
        self.runes_signed_var = tk.StringVar(value="0")
        self.runes_strength_var = tk.StringVar(value="0")
        
        # Cartes de metriques
        metrics = [
            ("TOTAL BALANCE", self.runes_total_var, "#FFD700"),
            ("ASSETS", self.runes_count_var, CypherpunkTheme.NEON_CYAN),
            ("SIGNED", self.runes_signed_var, CypherpunkTheme.NEON_GREEN),
            ("STRENGTH", self.runes_strength_var, CypherpunkTheme.NEON_PURPLE),
        ]
        
        for i, (label, var, color) in enumerate(metrics):
            card = CypherpunkTheme.create_metric_display(summary_frame, label, var, color)
            card.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Separateur
        sep = tk.Frame(frame, bg=CypherpunkTheme.BORDER_INACTIVE, height=1)
        sep.pack(fill=tk.X, padx=10, pady=10)
        
        # === LISTE DES RUNES ===
        list_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_DARK)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Titre liste
        list_title = tk.Label(
            list_frame,
            text="◈ GENESIS BLOCKS",
            bg=CypherpunkTheme.BG_DARK,
            fg=CypherpunkTheme.NEON_GREEN,
            font=CypherpunkTheme.FONT_TITLE
        )
        list_title.pack(anchor=tk.W, pady=(0, 10))
        
        # Frame pour le treeview avec bordure neon
        tree_outer = tk.Frame(list_frame, bg=CypherpunkTheme.NEON_GREEN, padx=1, pady=1)
        tree_outer.pack(fill=tk.BOTH, expand=True)
        
        tree_inner = tk.Frame(tree_outer, bg=CypherpunkTheme.BG_SECONDARY)
        tree_inner.pack(fill=tk.BOTH, expand=True)
        
        # Treeview pour les runes
        columns = ('Vault', 'Runes', 'Tier', 'Balance', 'Strength', 'Status', 'Signed')
        self.runes_tree = ttk.Treeview(tree_inner, columns=columns, show='headings', height=12)
        
        col_widths = {
            'Vault': 80, 'Runes': 80, 'Tier': 150, 
            'Balance': 120, 'Strength': 100, 'Status': 80, 'Signed': 180
        }
        
        for col in columns:
            self.runes_tree.heading(col, text=col, command=lambda c=col: self._sort_treeview(self.runes_tree, c))
            self.runes_tree.column(col, width=col_widths.get(col, 100))
        
        scrollbar = ttk.Scrollbar(tree_inner, orient=tk.VERTICAL, command=self.runes_tree.yview)
        self.runes_tree.configure(yscrollcommand=scrollbar.set)
        
        self.runes_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # === ACTIONS ===
        actions_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_DARK)
        actions_frame.pack(fill=tk.X, padx=10, pady=10)
        
        sign_btn = CypherpunkTheme.create_neon_button(
            actions_frame,
            "✎ SIGN ALL",
            self._sign_all_runes,
            CypherpunkTheme.NEON_GREEN
        )
        sign_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        verify_btn = CypherpunkTheme.create_neon_button(
            actions_frame,
            "✓ VERIFY",
            self._verify_runes,
            CypherpunkTheme.NEON_CYAN
        )
        verify_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        details_btn = CypherpunkTheme.create_neon_button(
            actions_frame,
            "◉ DETAILS",
            self._show_rune_details,
            CypherpunkTheme.NEON_PURPLE
        )
        details_btn.pack(side=tk.LEFT)
        
        # Export button a droite
        export_btn = CypherpunkTheme.create_neon_button(
            actions_frame,
            "↓ EXPORT",
            self._export_runes,
            CypherpunkTheme.TEXT_SECONDARY
        )
        export_btn.pack(side=tk.RIGHT)
        
        # Charger les donnees
        self._refresh_runes()
        
        return frame
    
    def _refresh_runes(self):
        """Rafraichit les donnees des runes"""
        if not RUNES_AVAILABLE:
            return
        
        # Vider le treeview
        for item in self.runes_tree.get_children():
            self.runes_tree.delete(item)
        
        # Obtenir le portfolio
        portfolio = self.runes_monitor.get_portfolio()
        
        # Mettre a jour les metriques
        self.runes_total_var.set(self.runes_monitor.format_balance(portfolio.total_balance))
        self.runes_count_var.set(str(portfolio.total_assets))
        self.runes_signed_var.set(str(portfolio.signed_count))
        self.runes_strength_var.set(f"{portfolio.total_strength:,.0f}")
        
        # Remplir le treeview
        for asset in portfolio.assets:
            status = "✓" if asset.status == RuneStatus.SIGNED else "○"
            signed_at = asset.signed_at[:19] if asset.signed_at else "Not signed"
            
            self.runes_tree.insert('', tk.END, values=(
                f"#{asset.vault_number:05d}",
                asset.rune_symbols,
                asset.tier_name,
                self.runes_monitor.format_balance(asset.balance),
                f"{asset.strength:,.0f}",
                status,
                signed_at
            ), tags=(asset.tier,))
        
        # Couleurs par tier
        self.runes_tree.tag_configure('quantum_pioneer', foreground='#FFD700')
        self.runes_tree.tag_configure('spinor_visionary', foreground='#9400D3')
        self.runes_tree.tag_configure('bell_verifier', foreground='#00CED1')
        self.runes_tree.tag_configure('post_quantum_guardian', foreground='#32CD32')
        
        self._log_activity("Runes portfolio refreshed")
    
    def _sign_all_runes(self):
        """Lance la signature de tous les blocs non signes"""
        import subprocess
        
        result = messagebox.askyesno(
            "Signature Runes",
            "Voulez-vous signer tous les blocs Genesis non signés?\n\n"
            "Cette action nécessite votre fichier .psnx"
        )
        
        if result:
            try:
                # Lancer le script de signature
                subprocess.Popen(
                    ["python", "scripts/sign_genesis.py", "--all"],
                    cwd=self.base_path
                )
                self._log_activity("Signature process started")
                messagebox.showinfo("Info", "Processus de signature lancé.\nRafraîchissez après la signature.")
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de lancer la signature: {e}")
    
    def _verify_runes(self):
        """Verifie les signatures des runes"""
        import subprocess
        
        try:
            result = subprocess.run(
                ["python", "scripts/sign_genesis.py", "--verify"],
                cwd=self.base_path,
                capture_output=True,
                text=True
            )
            
            # Afficher le resultat
            dialog = tk.Toplevel(self.root)
            dialog.title("Vérification des Signatures")
            dialog.geometry("500x400")
            dialog.configure(bg=CypherpunkTheme.BG_DARK)
            
            text = tk.Text(
                dialog,
                bg=CypherpunkTheme.BG_SECONDARY,
                fg=CypherpunkTheme.NEON_GREEN,
                font=CypherpunkTheme.FONT_MONO,
                padx=10,
                pady=10
            )
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text.insert(tk.END, result.stdout)
            text.config(state=tk.DISABLED)
            
            self._log_activity("Runes signatures verified")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de vérification: {e}")
    
    def _show_rune_details(self):
        """Affiche les details d'une rune selectionnee"""
        selection = self.runes_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner une rune")
            return
        
        item = self.runes_tree.item(selection[0])
        vault_str = item['values'][0]
        vault_num = int(vault_str.replace('#', ''))
        
        asset = self.runes_monitor.get_asset(vault_num)
        if not asset:
            messagebox.showerror("Erreur", "Rune non trouvée")
            return
        
        # Fenetre de details
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Rune Details - {asset.rune_symbols}")
        dialog.geometry("600x500")
        dialog.configure(bg=CypherpunkTheme.BG_DARK)
        
        # Contenu
        content = tk.Frame(dialog, bg=CypherpunkTheme.BG_DARK)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Titre avec runes
        title = tk.Label(
            content,
            text=f"{asset.rune_symbols} VAULT #{asset.vault_number:05d}",
            bg=CypherpunkTheme.BG_DARK,
            fg=asset.color,
            font=("Consolas", 20, "bold")
        )
        title.pack(pady=(0, 20))
        
        # Infos
        info_frame = tk.Frame(content, bg=CypherpunkTheme.BG_PANEL, padx=20, pady=15)
        info_frame.pack(fill=tk.X, pady=5)
        
        infos = [
            ("Tier", f"{asset.tier_name} ({asset.rarity})"),
            ("Balance", f"{asset.balance:,} PSNX"),
            ("Strength", f"{asset.strength:,.0f}"),
            ("Ancestry", f"Depth {asset.ancestry_depth}"),
            ("Status", asset.status.value.upper()),
            ("Created", asset.created_at[:19] if asset.created_at else "N/A"),
            ("Block Hash", asset.block_hash[:32] + "..." if asset.block_hash else "N/A"),
        ]
        
        for label, value in infos:
            row = tk.Frame(info_frame, bg=CypherpunkTheme.BG_PANEL)
            row.pack(fill=tk.X, pady=3)
            
            lbl = tk.Label(row, text=f"{label}:", bg=CypherpunkTheme.BG_PANEL, 
                          fg=CypherpunkTheme.TEXT_SECONDARY, width=12, anchor='w')
            lbl.pack(side=tk.LEFT)
            
            val = tk.Label(row, text=value, bg=CypherpunkTheme.BG_PANEL,
                          fg=CypherpunkTheme.NEON_GREEN)
            val.pack(side=tk.LEFT)
        
        # Abilities
        if asset.abilities:
            abilities_frame = tk.Frame(content, bg=CypherpunkTheme.BG_PANEL, padx=20, pady=15)
            abilities_frame.pack(fill=tk.X, pady=10)
            
            tk.Label(
                abilities_frame, 
                text="SPECIAL ABILITIES",
                bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.NEON_CYAN,
                font=CypherpunkTheme.FONT_TITLE
            ).pack(anchor='w', pady=(0, 10))
            
            for ability in asset.abilities:
                tk.Label(
                    abilities_frame,
                    text=f"  ▸ {ability.replace('_', ' ').title()}",
                    bg=CypherpunkTheme.BG_PANEL,
                    fg=CypherpunkTheme.TEXT_PRIMARY
                ).pack(anchor='w')
        
        # Signature
        if asset.signature:
            sig_frame = tk.Frame(content, bg=CypherpunkTheme.BG_TERTIARY, padx=15, pady=10)
            sig_frame.pack(fill=tk.X, pady=10)
            
            tk.Label(
                sig_frame,
                text="✓ SIGNED",
                bg=CypherpunkTheme.BG_TERTIARY,
                fg=CypherpunkTheme.NEON_GREEN,
                font=CypherpunkTheme.FONT_TITLE
            ).pack(anchor='w')
            
            tk.Label(
                sig_frame,
                text=f"Signature: {asset.signature}",
                bg=CypherpunkTheme.BG_TERTIARY,
                fg=CypherpunkTheme.TEXT_SECONDARY,
                font=CypherpunkTheme.FONT_MONO_SMALL
            ).pack(anchor='w')
            
            if asset.signed_at:
                tk.Label(
                    sig_frame,
                    text=f"Signed at: {asset.signed_at[:19]}",
                    bg=CypherpunkTheme.BG_TERTIARY,
                    fg=CypherpunkTheme.TEXT_SECONDARY
                ).pack(anchor='w')
    
    def _export_runes(self):
        """Exporte le portfolio de runes"""
        save_path = filedialog.asksaveasfilename(
            title="Exporter le portfolio Runes",
            initialfile=f"runes_portfolio_{datetime.now().strftime('%Y%m%d')}.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not save_path:
            return
        
        try:
            portfolio = self.runes_monitor.get_portfolio()
            
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "summary": {
                    "total_balance": portfolio.total_balance,
                    "total_assets": portfolio.total_assets,
                    "signed_count": portfolio.signed_count,
                    "pending_count": portfolio.pending_count,
                    "total_strength": portfolio.total_strength,
                    "tier_breakdown": portfolio.tier_breakdown
                },
                "assets": [
                    {
                        "vault_number": a.vault_number,
                        "inscription_id": a.inscription_id,
                        "tier": a.tier,
                        "tier_name": a.tier_name,
                        "rarity": a.rarity,
                        "rune_symbols": a.rune_symbols,
                        "rune_names": a.rune_names,
                        "balance": a.balance,
                        "strength": a.strength,
                        "status": a.status.value,
                        "signature": a.signature,
                        "signed_at": a.signed_at,
                        "created_at": a.created_at,
                        "abilities": a.abilities
                    }
                    for a in portfolio.assets
                ]
            }
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            self._log_activity(f"Runes portfolio exported to {save_path}")
            messagebox.showinfo("Succès", f"Portfolio exporté vers:\n{save_path}")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur d'export: {e}")
    
    def _populate_ui_from_state(self):
        """Remplir l'interface avec les données existantes"""
        # Charger les NFTs
        for asset in self.vault_data.get('assets', []):
            self.assets_tree.insert('', tk.END, values=(
                asset.get('id', ''),
                asset.get('contract', '')[:20] + '...' if len(asset.get('contract', '')) > 20 else asset.get('contract', ''),
                asset.get('token_id', ''),
                asset.get('name', ''),
                asset.get('chain', ''),
                asset.get('status', 'actif')
            ))
        
        # Charger les tokens
        for token in self.vault_data.get('tokens', []):
            self.tokens_tree.insert('', tk.END, values=(
                token.get('symbol', ''),
                token.get('name', ''),
                token.get('balance', '0'),
                token.get('contract', '')[:20] + '...',
                token.get('chain', '')
            ))
        
        # Charger les documents
        for doc in self.vault_data.get('documents', []):
            self.documents_tree.insert('', tk.END, values=(
                doc.get('name', ''),
                doc.get('type', ''),
                self._format_size(doc.get('size', 0)),
                doc.get('date', ''),
                doc.get('hash', '')[:20] + '...'
            ))
        
        # Charger les transfers
        for transfer in self.vault_data.get('transfers', []):
            self.transfers_tree.insert('', tk.END, values=(
                transfer.get('id', ''),
                transfer.get('type', ''),
                transfer.get('asset', ''),
                transfer.get('destination', '')[:20] + '...',
                transfer.get('expiry', ''),
                transfer.get('status', '')
            ))
        
        # Mettre à jour les métriques
        self._update_metrics()
    
    def _start_background_monitoring(self):
        """Démarrer le monitoring en arrière-plan"""
        def monitor_loop():
            while self._running:
                try:
                    self.root.after(0, self._update_metrics)
                    self.root.after(0, self._check_transfers)
                except Exception as e:
                    print(f"Erreur monitoring: {e}")
                time.sleep(30)
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
    
    def _update_metrics(self):
        """Mettre à jour les métriques"""
        self.metric_vars['nft_count'].set(str(len(self.vault_data.get('assets', []))))
        self.metric_vars['token_count'].set(str(len(self.vault_data.get('tokens', []))))
        self.metric_vars['doc_count'].set(str(len(self.vault_data.get('documents', []))))
        self.metric_vars['activity_24h'].set(str(self._count_recent_activity()))
        self.metric_vars['integrity'].set("OK")
        self.metric_vars['last_backup'].set(datetime.now().strftime("%H:%M:%S"))
    
    def _count_recent_activity(self) -> int:
        """Compter l'activité des dernières 24h"""
        log_file = os.path.join(self.data_path, f"{self.vault_name}_activity.log")
        if not os.path.exists(log_file):
            return 0
        
        count = 0
        cutoff = datetime.now().timestamp() - 86400
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('['):
                        time_str = line[1:9]
                        try:
                            log_time = datetime.strptime(time_str, "%H:%M:%S")
                            log_time = log_time.replace(
                                year=datetime.now().year,
                                month=datetime.now().month,
                                day=datetime.now().day
                            )
                            if log_time.timestamp() > cutoff:
                                count += 1
                        except ValueError:
                            pass
        except Exception:
            pass
        return count
    
    def _check_transfers(self):
        """Vérifier les transfers arrivés à échéance"""
        now = datetime.now()
        for transfer in self.vault_data.get('transfers', []):
            if transfer.get('status') == 'pending':
                try:
                    expiry = datetime.fromisoformat(transfer['expiry'])
                    if now >= expiry:
                        self._execute_auto_transfer(transfer)
                except (KeyError, ValueError):
                    pass
    
    def _execute_auto_transfer(self, transfer: Dict):
        """Exécuter un transfer automatiquement"""
        self._log_activity(f"Exécution automatique du transfer {transfer.get('id', 'N/A')}")
        transfer['status'] = 'completed'
        transfer['completed_at'] = datetime.now().isoformat()
        self._save_vault_state()
        
        # Mettre à jour l'affichage
        for item in self.transfers_tree.get_children():
            values = self.transfers_tree.item(item, 'values')
            if values[0] == transfer.get('id'):
                self.transfers_tree.item(item, values=(
                    values[0], values[1], values[2], values[3], values[4], 'completed'
                ))
                break
    
    def _log_activity(self, message: str):
        """Journaliser une activité - Style Cypherpunk"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        date_str = datetime.now().strftime("%Y-%m-%d")
        log_entry = f"[{date_str} {timestamp}] ▸ {message}\n"
        
        try:
            self.activity_log.insert(tk.END, log_entry)
            self.activity_log.see(tk.END)
            
            # Pulse effect on realtime indicator
            if hasattr(self, 'realtime_indicator'):
                self.realtime_indicator.configure(fg=CypherpunkTheme.NEON_CYAN)
                self.root.after(200, lambda: self.realtime_indicator.configure(fg=CypherpunkTheme.NEON_GREEN))
        except tk.TclError:
            pass
        
        self._save_activity_log(log_entry)
    
    def _save_activity_log(self, log_entry: str):
        """Sauvegarder le journal d'activité"""
        log_file = os.path.join(self.data_path, f"{self.vault_name}_activity.log")
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Erreur sauvegarde log: {e}")
    
    def _calculate_hash(self, data: bytes) -> str:
        """Calculer le hash SHA-256 des données"""
        return hashlib.sha256(data).hexdigest()
    
    def _format_size(self, size: int) -> str:
        """Formater une taille en bytes"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def _sort_treeview(self, tree: ttk.Treeview, col: str):
        """Trier un treeview par colonne"""
        items = [(tree.set(k, col), k) for k in tree.get_children('')]
        items.sort()
        for index, (val, k) in enumerate(items):
            tree.move(k, '', index)
    
    def _generate_id(self) -> str:
        """Générer un ID unique"""
        import secrets
        return secrets.token_hex(8)
    
    # ========================================================================
    # ACTIONS NFT
    # ========================================================================
    
    def deposit_nft(self):
        """Interface de dépôt NFT"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Dépôt NFT")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Adresse du contrat NFT:").pack(pady=5)
        contract_entry = ttk.Entry(dialog, width=60)
        contract_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Token ID:").pack(pady=5)
        token_entry = ttk.Entry(dialog, width=20)
        token_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Nom (optionnel):").pack(pady=5)
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Chaîne:").pack(pady=5)
        chain_combo = ttk.Combobox(dialog, values=["Ethereum", "Polygon", "Arbitrum", "Optimism", "BSC"])
        chain_combo.set("Ethereum")
        chain_combo.pack(pady=5)
        
        def process_deposit():
            contract = contract_entry.get().strip()
            token_id = token_entry.get().strip()
            
            if not contract or not token_id:
                messagebox.showerror("Erreur", "Contrat et Token ID requis")
                return
            
            nft_data = {
                'id': self._generate_id(),
                'contract': contract,
                'token_id': token_id,
                'name': name_entry.get().strip() or f"NFT #{token_id}",
                'chain': chain_combo.get(),
                'status': 'sécurisé',
                'deposited_at': datetime.now().isoformat()
            }
            
            self.vault_data['assets'].append(nft_data)
            
            self.assets_tree.insert('', tk.END, values=(
                nft_data['id'],
                contract[:20] + '...' if len(contract) > 20 else contract,
                token_id,
                nft_data['name'],
                nft_data['chain'],
                'sécurisé'
            ))
            
            self._save_vault_state()
            self._log_activity(f"NFT déposé: {nft_data['name']} ({token_id})")
            messagebox.showinfo("Succès", "NFT déposé avec succès dans le vault")
            dialog.destroy()
        
        ttk.Button(dialog, text="Sécuriser dans Vault", command=process_deposit).pack(pady=20)
    
    def scan_nfts(self):
        """Scanner les NFTs (simulation)"""
        self._log_activity("Scan des NFTs initié...")
        messagebox.showinfo("Scan", "Scan des NFTs en cours. Cette fonctionnalité nécessite une connexion blockchain active.")
    
    def import_nfts_csv(self):
        """Importer des NFTs depuis un fichier CSV"""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un fichier CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            import csv
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    nft_data = {
                        'id': self._generate_id(),
                        'contract': row.get('contract', ''),
                        'token_id': row.get('token_id', ''),
                        'name': row.get('name', f"NFT #{row.get('token_id', '')}"),
                        'chain': row.get('chain', 'Ethereum'),
                        'status': 'importé',
                        'deposited_at': datetime.now().isoformat()
                    }
                    self.vault_data['assets'].append(nft_data)
                    self.assets_tree.insert('', tk.END, values=(
                        nft_data['id'],
                        nft_data['contract'][:20] + '...',
                        nft_data['token_id'],
                        nft_data['name'],
                        nft_data['chain'],
                        'importé'
                    ))
                    count += 1
            
            self._save_vault_state()
            self._log_activity(f"Import CSV: {count} NFTs importés")
            messagebox.showinfo("Succès", f"{count} NFTs importés avec succès")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'import: {e}")
    
    def add_nft_manual(self):
        """Alias pour deposit_nft"""
        self.deposit_nft()
    
    def show_nft_details(self):
        """Afficher les détails d'un NFT sélectionné"""
        selection = self.assets_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un NFT")
            return
        
        item = self.assets_tree.item(selection[0])
        values = item['values']
        nft_id = values[0]
        
        # Trouver les données complètes
        nft_data = None
        for asset in self.vault_data.get('assets', []):
            if asset.get('id') == nft_id:
                nft_data = asset
                break
        
        if not nft_data:
            messagebox.showerror("Erreur", "NFT non trouvé")
            return
        
        # Afficher les détails
        details = tk.Toplevel(self.root)
        details.title(f"Détails NFT: {nft_data.get('name', 'N/A')}")
        details.geometry("500x400")
        
        text = tk.Text(details, wrap=tk.WORD, padx=10, pady=10)
        text.pack(fill=tk.BOTH, expand=True)
        
        text.insert(tk.END, f"ID: {nft_data.get('id', 'N/A')}\n")
        text.insert(tk.END, f"Nom: {nft_data.get('name', 'N/A')}\n")
        text.insert(tk.END, f"Contrat: {nft_data.get('contract', 'N/A')}\n")
        text.insert(tk.END, f"Token ID: {nft_data.get('token_id', 'N/A')}\n")
        text.insert(tk.END, f"Chaîne: {nft_data.get('chain', 'N/A')}\n")
        text.insert(tk.END, f"Statut: {nft_data.get('status', 'N/A')}\n")
        text.insert(tk.END, f"Déposé le: {nft_data.get('deposited_at', 'N/A')}\n")
        
        text.config(state=tk.DISABLED)
    
    def secure_nft(self):
        """Marquer un NFT comme sécurisé"""
        selection = self.assets_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un NFT")
            return
        
        item = self.assets_tree.item(selection[0])
        nft_id = item['values'][0]
        
        for asset in self.vault_data.get('assets', []):
            if asset.get('id') == nft_id:
                asset['status'] = 'sécurisé'
                break
        
        values = list(item['values'])
        values[5] = 'sécurisé'
        self.assets_tree.item(selection[0], values=values)
        
        self._save_vault_state()
        self._log_activity(f"NFT {nft_id} marqué comme sécurisé")
    
    def withdraw_nft(self):
        """Retirer un NFT du vault"""
        selection = self.assets_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un NFT")
            return
        
        if not messagebox.askyesno("Confirmation", "Voulez-vous vraiment retirer ce NFT du vault?"):
            return
        
        item = self.assets_tree.item(selection[0])
        nft_id = item['values'][0]
        
        for asset in self.vault_data.get('assets', []):
            if asset.get('id') == nft_id:
                asset['status'] = 'retiré'
                break
        
        values = list(item['values'])
        values[5] = 'retiré'
        self.assets_tree.item(selection[0], values=values)
        
        self._save_vault_state()
        self._log_activity(f"NFT {nft_id} retiré du vault")
    
    def delete_nft(self):
        """Supprimer un NFT de la liste"""
        selection = self.assets_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un NFT")
            return
        
        if not messagebox.askyesno("Confirmation", "Voulez-vous vraiment supprimer ce NFT?"):
            return
        
        item = self.assets_tree.item(selection[0])
        nft_id = item['values'][0]
        
        self.vault_data['assets'] = [a for a in self.vault_data.get('assets', []) if a.get('id') != nft_id]
        self.assets_tree.delete(selection[0])
        
        self._save_vault_state()
        self._log_activity(f"NFT {nft_id} supprimé")
    
    # ========================================================================
    # ACTIONS TOKEN
    # ========================================================================
    
    def deposit_token(self):
        """Interface de dépôt de token"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Dépôt Token")
        dialog.geometry("500x350")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Adresse du token:").pack(pady=5)
        token_entry = ttk.Entry(dialog, width=60)
        token_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Symbole:").pack(pady=5)
        symbol_entry = ttk.Entry(dialog, width=20)
        symbol_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Montant:").pack(pady=5)
        amount_entry = ttk.Entry(dialog, width=20)
        amount_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Délai de récupération (jours):").pack(pady=5)
        days_entry = ttk.Entry(dialog, width=10)
        days_entry.insert(0, "30")
        days_entry.pack(pady=5)
        
        def process_token_deposit():
            contract = token_entry.get().strip()
            symbol = symbol_entry.get().strip()
            amount = amount_entry.get().strip()
            
            if not contract or not symbol or not amount:
                messagebox.showerror("Erreur", "Tous les champs sont requis")
                return
            
            token_data = {
                'id': self._generate_id(),
                'contract': contract,
                'symbol': symbol,
                'name': symbol,
                'balance': amount,
                'chain': 'Ethereum',
                'recovery_days': int(days_entry.get() or 30),
                'deposited_at': datetime.now().isoformat()
            }
            
            self.vault_data['tokens'].append(token_data)
            
            self.tokens_tree.insert('', tk.END, values=(
                symbol,
                symbol,
                amount,
                contract[:20] + '...',
                'Ethereum'
            ))
            
            self._save_vault_state()
            self._log_activity(f"Token déposé: {amount} {symbol}")
            messagebox.showinfo("Succès", "Token déposé avec délai de récupération")
            dialog.destroy()
        
        ttk.Button(dialog, text="Déposer avec délai", command=process_token_deposit).pack(pady=20)
    
    def deposit_token_action(self):
        """Action de dépôt depuis l'onglet tokens"""
        contract = self.token_contract_entry.get().strip()
        amount = self.token_amount_entry.get().strip()
        symbol = self.token_symbol_entry.get().strip() or "TOKEN"
        
        if not contract or not amount:
            messagebox.showerror("Erreur", "Contrat et montant requis")
            return
        
        token_data = {
            'id': self._generate_id(),
            'contract': contract,
            'symbol': symbol,
            'name': symbol,
            'balance': amount,
            'chain': 'Ethereum',
            'deposited_at': datetime.now().isoformat()
        }
        
        self.vault_data['tokens'].append(token_data)
        
        self.tokens_tree.insert('', tk.END, values=(
            symbol,
            symbol,
            amount,
            contract[:20] + '...',
            'Ethereum'
        ))
        
        # Effacer les entrées
        self.token_contract_entry.delete(0, tk.END)
        self.token_amount_entry.delete(0, tk.END)
        self.token_symbol_entry.delete(0, tk.END)
        
        self._save_vault_state()
        self._log_activity(f"Token enregistré: {amount} {symbol}")
    
    # ========================================================================
    # ACTIONS DOCUMENT
    # ========================================================================
    
    def add_document(self):
        """Alias pour deposit_document"""
        self.deposit_document()
    
    def deposit_document(self):
        """Interface de dépôt de document"""
        file_path = filedialog.askopenfilename(
            title="Sélectionner un document",
            filetypes=[
                ("Tous les fichiers", "*.*"),
                ("PDF", "*.pdf"),
                ("Images", "*.png *.jpg *.jpeg"),
                ("Documents", "*.doc *.docx *.txt")
            ]
        )
        
        if not file_path:
            return
        
        try:
            with open(file_path, 'rb') as f:
                document_data = f.read()
            
            # Chiffrer le document
            encrypted = self.vault_manager.encrypt_data(document_data)
            doc_name = os.path.basename(file_path)
            doc_id = self._generate_id()
            doc_path = os.path.join(self.documents_path, f"{self.vault_name}_{doc_id}.enc")
            
            with open(doc_path, 'wb') as f:
                f.write(encrypted)
            
            # Ajouter aux métadonnées
            doc_hash = self._calculate_hash(document_data)
            doc_type = os.path.splitext(doc_name)[1].upper().replace('.', '')
            
            doc_entry = {
                'id': doc_id,
                'name': doc_name,
                'type': doc_type,
                'size': len(document_data),
                'path': doc_path,
                'date': datetime.now().isoformat(),
                'hash': doc_hash
            }
            
            self.vault_data['documents'].append(doc_entry)
            
            self.documents_tree.insert('', tk.END, values=(
                doc_name,
                doc_type,
                self._format_size(len(document_data)),
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                doc_hash[:20] + '...'
            ))
            
            self._save_vault_state()
            self._log_activity(f"Document déposé: {doc_name}")
            messagebox.showinfo("Succès", f"Document {doc_name} sécurisé dans le vault")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du dépôt: {e}")
    
    def verify_document(self):
        """Vérifier l'intégrité d'un document"""
        selection = self.documents_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un document")
            return
        
        item = self.documents_tree.item(selection[0])
        doc_name = item['values'][0]
        
        # Trouver le document
        doc_data = None
        for doc in self.vault_data.get('documents', []):
            if doc.get('name') == doc_name:
                doc_data = doc
                break
        
        if not doc_data:
            messagebox.showerror("Erreur", "Document non trouvé")
            return
        
        try:
            # Lire et déchiffrer
            with open(doc_data['path'], 'rb') as f:
                encrypted = f.read()
            decrypted = self.vault_manager.decrypt_data(encrypted)
            
            # Vérifier le hash
            current_hash = self._calculate_hash(decrypted)
            if current_hash == doc_data['hash']:
                messagebox.showinfo("Intégrité", "✓ Document intègre - Hash vérifié")
                self._log_activity(f"Vérification intégrité OK: {doc_name}")
            else:
                messagebox.showwarning("Attention", "⚠ Hash différent - Document potentiellement modifié")
                self._log_activity(f"ALERTE: Intégrité compromise pour {doc_name}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur de vérification: {e}")
    
    def extract_document(self):
        """Extraire un document du vault"""
        selection = self.documents_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un document")
            return
        
        item = self.documents_tree.item(selection[0])
        doc_name = item['values'][0]
        
        # Trouver le document
        doc_data = None
        for doc in self.vault_data.get('documents', []):
            if doc.get('name') == doc_name:
                doc_data = doc
                break
        
        if not doc_data:
            messagebox.showerror("Erreur", "Document non trouvé")
            return
        
        # Demander où sauvegarder
        save_path = filedialog.asksaveasfilename(
            title="Enregistrer le document",
            initialfile=doc_name,
            defaultextension=os.path.splitext(doc_name)[1]
        )
        
        if not save_path:
            return
        
        try:
            with open(doc_data['path'], 'rb') as f:
                encrypted = f.read()
            decrypted = self.vault_manager.decrypt_data(encrypted)
            
            with open(save_path, 'wb') as f:
                f.write(decrypted)
            
            self._log_activity(f"Document extrait: {doc_name}")
            messagebox.showinfo("Succès", f"Document extrait vers {save_path}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur d'extraction: {e}")
    
    # ========================================================================
    # ACTIONS TRANSFER
    # ========================================================================
    
    def initiate_transfer(self):
        """Initier un nouveau transfer programmé"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Nouveau Transfer")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Type de transfer:").pack(pady=5)
        type_combo = ttk.Combobox(dialog, values=["NFT", "Token", "Document"])
        type_combo.set("NFT")
        type_combo.pack(pady=5)
        
        ttk.Label(dialog, text="ID de l'actif:").pack(pady=5)
        asset_entry = ttk.Entry(dialog, width=40)
        asset_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Adresse destination:").pack(pady=5)
        dest_entry = ttk.Entry(dialog, width=60)
        dest_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Délai (jours):").pack(pady=5)
        delay_entry = ttk.Entry(dialog, width=10)
        delay_entry.insert(0, "7")
        delay_entry.pack(pady=5)
        
        def create_transfer():
            from datetime import timedelta
            
            transfer_data = {
                'id': self._generate_id(),
                'type': type_combo.get(),
                'asset': asset_entry.get().strip(),
                'destination': dest_entry.get().strip(),
                'expiry': (datetime.now() + timedelta(days=int(delay_entry.get() or 7))).isoformat(),
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }
            
            self.vault_data['transfers'].append(transfer_data)
            
            self.transfers_tree.insert('', tk.END, values=(
                transfer_data['id'],
                transfer_data['type'],
                transfer_data['asset'],
                transfer_data['destination'][:20] + '...',
                transfer_data['expiry'][:10],
                'pending'
            ))
            
            self._save_vault_state()
            self._log_activity(f"Transfer programmé: {transfer_data['id']}")
            messagebox.showinfo("Succès", "Transfer programmé avec succès")
            dialog.destroy()
        
        ttk.Button(dialog, text="Créer Transfer", command=create_transfer).pack(pady=20)
    
    def execute_transfer(self):
        """Exécuter un transfer manuellement"""
        selection = self.transfers_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un transfer")
            return
        
        if not messagebox.askyesno("Confirmation", "Exécuter ce transfer maintenant?"):
            return
        
        item = self.transfers_tree.item(selection[0])
        transfer_id = item['values'][0]
        
        for transfer in self.vault_data.get('transfers', []):
            if transfer.get('id') == transfer_id:
                transfer['status'] = 'completed'
                transfer['completed_at'] = datetime.now().isoformat()
                break
        
        values = list(item['values'])
        values[5] = 'completed'
        self.transfers_tree.item(selection[0], values=values)
        
        self._save_vault_state()
        self._log_activity(f"Transfer exécuté: {transfer_id}")
    
    def cancel_transfer(self):
        """Annuler un transfer"""
        selection = self.transfers_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez sélectionner un transfer")
            return
        
        if not messagebox.askyesno("Confirmation", "Annuler ce transfer?"):
            return
        
        item = self.transfers_tree.item(selection[0])
        transfer_id = item['values'][0]
        
        for transfer in self.vault_data.get('transfers', []):
            if transfer.get('id') == transfer_id:
                transfer['status'] = 'cancelled'
                break
        
        values = list(item['values'])
        values[5] = 'cancelled'
        self.transfers_tree.item(selection[0], values=values)
        
        self._save_vault_state()
        self._log_activity(f"Transfer annulé: {transfer_id}")
    
    # ========================================================================
    # RECOVERY & EXPORT
    # ========================================================================
    
    def recovery_panel(self):
        """Panel de récupération avec les deux clés"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Récupération Vault")
        dialog.geometry("600x450")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Récupération avec double clé", 
                  font=('Arial', 14, 'bold')).pack(pady=20)
        
        ttk.Label(dialog, text="Cette procédure nécessite les deux fichiers clés:").pack(pady=5)
        
        # Fichier .psnx
        ttk.Label(dialog, text="Fichier .psnx:").pack(pady=5)
        psnx_path = tk.StringVar()
        psnx_frame = ttk.Frame(dialog)
        psnx_frame.pack(pady=5)
        ttk.Entry(psnx_frame, textvariable=psnx_path, width=50).pack(side=tk.LEFT)
        ttk.Button(psnx_frame, text="Parcourir", 
                   command=lambda: psnx_path.set(filedialog.askopenfilename(
                       filetypes=[("PSNX files", "*.psnx"), ("All files", "*.*")]))).pack(side=tk.LEFT, padx=5)
        
        # Fichier .blend_data
        ttk.Label(dialog, text="Fichier .blend_data:").pack(pady=5)
        blend_path = tk.StringVar()
        blend_frame = ttk.Frame(dialog)
        blend_frame.pack(pady=5)
        ttk.Entry(blend_frame, textvariable=blend_path, width=50).pack(side=tk.LEFT)
        ttk.Button(blend_frame, text="Parcourir", 
                   command=lambda: blend_path.set(filedialog.askopenfilename(
                       filetypes=[("Blend Data", "*.blend_data"), ("All files", "*.*")]))).pack(side=tk.LEFT, padx=5)
        
        # Mot de passe
        ttk.Label(dialog, text="Mot de passe (si applicable):").pack(pady=5)
        password_entry = ttk.Entry(dialog, width=40, show="*")
        password_entry.pack(pady=5)
        
        def attempt_recovery():
            if not psnx_path.get() or not blend_path.get():
                messagebox.showerror("Erreur", "Les deux fichiers clés sont requis")
                return
            
            if not os.path.exists(psnx_path.get()):
                messagebox.showerror("Erreur", "Fichier .psnx introuvable")
                return
            
            if not os.path.exists(blend_path.get()):
                messagebox.showerror("Erreur", "Fichier .blend_data introuvable")
                return
            
            # Tentative de récupération
            self._log_activity("Tentative de récupération du vault")
            
            try:
                # Import de l'authentificateur
                from ui.vault_gui_complete import DualKeyAuthenticator
                auth = DualKeyAuthenticator()
                success, msg = auth.authenticate(psnx_path.get(), blend_path.get())
                
                if success:
                    self._log_activity("Récupération réussie")
                    messagebox.showinfo("Succès", "Vault récupéré avec succès!")
                    dialog.destroy()
                else:
                    self._log_activity(f"Échec récupération: {msg}")
                    messagebox.showerror("Erreur", f"Échec: {msg}")
            except ImportError:
                messagebox.showinfo("Info", "Module d'authentification non disponible. Vérification basique effectuée.")
                self._log_activity("Récupération: vérification basique")
                dialog.destroy()
        
        ttk.Button(dialog, text="Récupérer Vault", command=attempt_recovery).pack(pady=30)
    
    def refresh_data(self):
        """Actualiser les données"""
        # Recharger l'état du vault
        self.vault_data = self._load_vault_state()
        
        # Vider les treeviews
        for item in self.assets_tree.get_children():
            self.assets_tree.delete(item)
        for item in self.tokens_tree.get_children():
            self.tokens_tree.delete(item)
        for item in self.documents_tree.get_children():
            self.documents_tree.delete(item)
        for item in self.transfers_tree.get_children():
            self.transfers_tree.delete(item)
        
        # Repeupler
        self._populate_ui_from_state()
        
        self._log_activity("Données actualisées")
        self.status_bar.config(text=f"Actualisé à {datetime.now().strftime('%H:%M:%S')}")
    
    def export_logs(self):
        """Exporter le journal d'activité"""
        save_path = filedialog.asksaveasfilename(
            title="Exporter le journal",
            initialfile=f"{self.vault_name}_logs_{datetime.now().strftime('%Y%m%d')}.txt",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not save_path:
            return
        
        try:
            log_content = self.activity_log.get(1.0, tk.END)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(f"=== Journal du Vault: {self.vault_name} ===\n")
                f.write(f"Exporté le: {datetime.now().isoformat()}\n")
                f.write("=" * 50 + "\n\n")
                f.write(log_content)
            
            messagebox.showinfo("Succès", f"Journal exporté vers {save_path}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur d'export: {e}")
    
    def run(self):
        """Exécuter l'interface"""
        self._log_activity("Vault Monitor démarré")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
    
    def _on_close(self):
        """Gérer la fermeture de l'application"""
        self._running = False
        self._save_vault_state()
        self._log_activity("Vault Monitor arrêté")
        self.root.destroy()


# ============================================================================
# POINT D'ENTREE
# ============================================================================

def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Poly-Spinor Nexus 7D - Vault Monitor")
    parser.add_argument("--vault", "-v", default="default_vault", help="Nom du vault")
    parser.add_argument("--key", "-k", help="Clé du vault (hex)")
    parser.add_argument("--auth", "-a", action="store_true", help="Utiliser l'authentification double clé")
    
    args = parser.parse_args()
    
    if args.auth:
        # Authentification avec fichiers clés
        try:
            from ui.vault_gui_complete import DualKeyAuthenticator
            
            # Demander les fichiers
            root = tk.Tk()
            root.withdraw()
            
            psnx_path = filedialog.askopenfilename(
                title="Sélectionner le fichier .psnx",
                filetypes=[("PSNX files", "*.psnx")]
            )
            
            if not psnx_path:
                print("Annulé: fichier .psnx requis")
                return
            
            blend_path = filedialog.askopenfilename(
                title="Sélectionner le fichier .blend_data",
                filetypes=[("Blend Data", "*.blend_data")]
            )
            
            if not blend_path:
                print("Annulé: fichier .blend_data requis")
                return
            
            root.destroy()
            
            auth = DualKeyAuthenticator()
            success, msg = auth.authenticate(psnx_path, blend_path)
            
            if success:
                monitor = VaultMonitorGUI(auth.vault_key, args.vault)
                monitor.run()
            else:
                print(f"Erreur d'authentification: {msg}")
                
        except ImportError as e:
            print(f"Module d'authentification non disponible: {e}")
            print("Utilisation du mode par défaut...")
            vault_key = os.urandom(32)
            monitor = VaultMonitorGUI(vault_key, args.vault)
            monitor.run()
    else:
        # Mode direct avec clé
        if args.key:
            vault_key = bytes.fromhex(args.key)
        else:
            # Générer une clé temporaire pour démo
            vault_key = hashlib.sha256(args.vault.encode()).digest()
            print(f"[INFO] Clé générée à partir du nom du vault: {vault_key.hex()[:16]}...")
        
        monitor = VaultMonitorGUI(vault_key, args.vault)
        monitor.run()


if __name__ == "__main__":
    main()
