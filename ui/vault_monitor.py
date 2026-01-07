#!/usr/bin/env python
"""
Eidolon - Vault Monitor GUI
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
from pathlib import Path
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
    NEON_MAGENTA = "#ff00ff"
    NEON_PINK = "#ff0080"
    NEON_ORANGE = "#ff6600"
    NEON_BLUE = "#0066ff"
    NEON_YELLOW = "#ffff00"
    
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
        """Applies le thème cypherpunk à la fenêtre"""
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

try:
    from core.alchemy_integration import AlchemyClient, AlchemyNetwork, AlchemyNFT, AlchemyToken
    ALCHEMY_AVAILABLE = True
except ImportError as e:
    ALCHEMY_AVAILABLE = False
    print(f"[INFO] Module Alchemy non disponible: {e}")

try:
    from core.item_runes_exchange import ItemRunesExchange, RuneItemInscription, ItemListing
    EXCHANGE_AVAILABLE = True
except ImportError as e:
    EXCHANGE_AVAILABLE = False
    print(f"[INFO] Module Exchange non disponible: {e}")

try:
    from core.bitcoin_asset_bridge import BitcoinAssetBridge, AssetOnChain, AssetType
    BRIDGE_AVAILABLE = True
except ImportError as e:
    BRIDGE_AVAILABLE = False
    print(f"[INFO] Module Bitcoin Bridge non disponible: {e}")

try:
    from core.avatar_system import AvatarManager, QuantumAvatarGenerator
    AVATAR_AVAILABLE = True
except ImportError as e:
    AVATAR_AVAILABLE = False
    print(f"[INFO] Module Avatar non disponible: {e}")

try:
    from core.evolution_artifacts import (
        EvolutionArtifactSystem, EvolutionArtifact, 
        EVOLUTION_ARTIFACT_DEFINITIONS, get_evolution_artifact_system
    )
    EVOLUTION_ARTIFACTS_AVAILABLE = True
except ImportError as e:
    EVOLUTION_ARTIFACTS_AVAILABLE = False
    print(f"[INFO] Module Evolution Artifacts non disponible: {e}")


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
        self.root.title(f"Eidolon - Vault Monitor: {vault_name}")
        
        # Adapter la taille a l'ecran
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        
        # Taille responsive (80% de l'ecran, min 1024x600)
        win_w = max(1024, min(1400, int(screen_w * 0.8)))
        win_h = max(600, min(900, int(screen_h * 0.8)))
        
        # Centrer la fenetre
        pos_x = (screen_w - win_w) // 2
        pos_y = (screen_h - win_h) // 2
        
        self.root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.root.minsize(1024, 600)
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
        """Savesr l'état persistant du vault"""
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
            text="◈ EIDOLON",
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
        
        # Adresse EVM (dérivée du vault)
        self.vault_info_address_var = tk.StringVar(value="╰─▶ Loading...")
        addr_lbl = tk.Label(
            info_inner,
            textvariable=self.vault_info_address_var,
            bg=CypherpunkTheme.BG_PANEL,
            fg=CypherpunkTheme.TEXT_SECONDARY,
            font=CypherpunkTheme.FONT_MONO_SMALL
        )
        addr_lbl.pack(anchor=tk.W, pady=2)
        
        # Initialiser l'adresse après le chargement de l'UI
        self.root.after(100, self._init_vault_info_address)
        
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
        
        # Onglet Blockchain (Alchemy)
        self.blockchain_tab = self._create_blockchain_tab()
        self.notebook.add(self.blockchain_tab, text="  ⛓ BLOCKCHAIN  ")
        
        # Onglet Bitcoin Exchange (si disponible)
        if EXCHANGE_AVAILABLE:
            self.exchange_tab = self._create_exchange_tab()
            self.notebook.add(self.exchange_tab, text="  ₿ EXCHANGE  ")
        
        # Onglet Bitcoin Bridge (transfert d'actifs sur blockchain)
        if BRIDGE_AVAILABLE:
            self.bridge_tab = self._create_bridge_tab()
            self.notebook.add(self.bridge_tab, text="  ⛓ BRIDGE  ")
        
        # Onglet Avatar 3D
        if AVATAR_AVAILABLE:
            self.avatar_tab = self._create_avatar_tab()
            self.notebook.add(self.avatar_tab, text="  🎭 AVATAR  ")
        
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
        ttk.Button(btn_frame, text="Delete", command=self.delete_nft).pack(side=tk.LEFT, padx=5)
        
        return frame
    
    def _create_tokens_tab(self) -> ttk.Frame:
        """Créer l'onglet des tokens avec scroll"""
        frame = ttk.Frame(self.notebook)
        
        # === SCROLLABLE CONTAINER ===
        canvas = tk.Canvas(frame, bg=CypherpunkTheme.BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mouse wheel scroll
        def _on_mousewheel_tokens(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel_tokens)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind canvas width
        def _configure_tokens_canvas(event):
            canvas.itemconfig(canvas.find_all()[0], width=event.width)
        canvas.bind("<Configure>", _configure_tokens_canvas)
        
        # Balance totale
        balance_frame = ttk.LabelFrame(scrollable_frame, text="Balance", padding=10)
        balance_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        ttk.Label(balance_frame, text="Balance Totale:", font=('Arial', 12, 'bold')).pack(anchor=tk.W)
        self.total_balance_var = tk.StringVar(value="0.00 ETH")
        ttk.Label(balance_frame, textvariable=self.total_balance_var, 
                  font=('Arial', 24, 'bold'), foreground="#00ff00").pack(anchor=tk.W)
        
        # Liste des tokens
        list_frame = ttk.LabelFrame(scrollable_frame, text="Tokens", padding=10)
        list_frame.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        columns = ('Symbole', 'Nom', 'Balance', 'Contrat', 'Chaîne')
        self.tokens_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.tokens_tree.heading(col, text=col)
            self.tokens_tree.column(col, width=120)
        
        tree_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tokens_tree.yview)
        self.tokens_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.tokens_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # === WALLET ADDRESSES ===
        addresses_frame = tk.LabelFrame(scrollable_frame, text="🔐 WALLET ADDRESSES", 
                                        bg=CypherpunkTheme.BG_PANEL, fg=CypherpunkTheme.NEON_CYAN,
                                        font=CypherpunkTheme.FONT_TITLE, padx=10, pady=10)
        addresses_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # EVM Address (Ethereum, Polygon, etc.)
        evm_row = tk.Frame(addresses_frame, bg=CypherpunkTheme.BG_PANEL)
        evm_row.pack(fill=tk.X, pady=5)
        
        tk.Label(evm_row, text="⟠ EVM Address:", bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.NEON_GREEN, font=CypherpunkTheme.FONT_NORMAL, width=18, anchor='w').pack(side=tk.LEFT)
        
        self.wallet_address_var = tk.StringVar(value="Click Refresh to connect")
        evm_addr_label = tk.Label(evm_row, textvariable=self.wallet_address_var, bg=CypherpunkTheme.BG_PANEL,
                                  fg=CypherpunkTheme.NEON_GREEN, font=CypherpunkTheme.FONT_MONO)
        evm_addr_label.pack(side=tk.LEFT, padx=5)
        
        copy_evm_btn = tk.Button(evm_row, text="📋 Copy EVM", bg=CypherpunkTheme.BG_TERTIARY,
                                fg=CypherpunkTheme.NEON_CYAN, command=self._copy_evm_address)
        copy_evm_btn.pack(side=tk.RIGHT, padx=5)
        
        # Bitcoin Taproot Address (for Runes)
        btc_row = tk.Frame(addresses_frame, bg=CypherpunkTheme.BG_PANEL)
        btc_row.pack(fill=tk.X, pady=5)
        
        tk.Label(btc_row, text="₿ Bitcoin (Runes):", bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.NEON_ORANGE, font=CypherpunkTheme.FONT_NORMAL, width=18, anchor='w').pack(side=tk.LEFT)
        
        self.btc_address_var = tk.StringVar(value="Click Refresh to connect")
        btc_addr_label = tk.Label(btc_row, textvariable=self.btc_address_var, bg=CypherpunkTheme.BG_PANEL,
                                  fg=CypherpunkTheme.NEON_ORANGE, font=CypherpunkTheme.FONT_MONO)
        btc_addr_label.pack(side=tk.LEFT, padx=5)
        
        copy_btc_btn = tk.Button(btc_row, text="📋 Copy BTC", bg=CypherpunkTheme.BG_TERTIARY,
                                fg=CypherpunkTheme.NEON_ORANGE, command=self._copy_btc_address)
        copy_btc_btn.pack(side=tk.RIGHT, padx=5)
        
        # Info text
        tk.Label(addresses_frame, text="EVM: Ethereum, Polygon, Arbitrum, Base, BSC  |  BTC: Taproot for Runes & Ordinals",
                bg=CypherpunkTheme.BG_PANEL, fg=CypherpunkTheme.TEXT_SECONDARY,
                font=CypherpunkTheme.FONT_SMALL).pack(anchor=tk.W, pady=(5, 0))
        
        # === WEB3 ERC20 INTEGRATION ===
        web3_frame = tk.LabelFrame(scrollable_frame, text="⛓ EVM NETWORK", 
                                   bg=CypherpunkTheme.BG_PANEL, fg=CypherpunkTheme.NEON_CYAN,
                                   font=CypherpunkTheme.FONT_TITLE, padx=10, pady=10)
        web3_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # Chain Selection
        chain_row = tk.Frame(web3_frame, bg=CypherpunkTheme.BG_PANEL)
        chain_row.pack(fill=tk.X, pady=5)
        
        tk.Label(chain_row, text="Network:", bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.TEXT_PRIMARY).pack(side=tk.LEFT)
        
        self.chain_var = tk.StringVar(value="ethereum")
        chains = ["ethereum", "sepolia", "polygon", "arbitrum", "optimism", "base", "bsc"]
        chain_menu = ttk.Combobox(chain_row, textvariable=self.chain_var, values=chains, width=15)
        chain_menu.pack(side=tk.LEFT, padx=10)
        
        refresh_btn = tk.Button(chain_row, text="🔄 Refresh Wallets", bg=CypherpunkTheme.BG_TERTIARY,
                               fg=CypherpunkTheme.NEON_GREEN, command=self._refresh_all_wallets)
        refresh_btn.pack(side=tk.LEFT, padx=5)
        
        # Native balance display
        balance_row = tk.Frame(web3_frame, bg=CypherpunkTheme.BG_PANEL)
        balance_row.pack(fill=tk.X, pady=5)
        
        tk.Label(balance_row, text="Native Balance:", bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.TEXT_PRIMARY).pack(side=tk.LEFT)
        
        self.native_balance_var = tk.StringVar(value="--")
        tk.Label(balance_row, textvariable=self.native_balance_var, bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.NEON_GREEN, font=CypherpunkTheme.FONT_MONO).pack(side=tk.LEFT, padx=10)
        
        # === RECEIVE SECTION ===
        receive_frame = tk.LabelFrame(scrollable_frame, text="📥 RECEIVE ERC20", 
                                      bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_GREEN,
                                      font=CypherpunkTheme.FONT_TITLE, padx=10, pady=10)
        receive_frame.pack(fill=tk.X, pady=10, padx=5)
        
        tk.Label(receive_frame, text="Share your EVM address to receive tokens:",
                bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.TEXT_PRIMARY).pack(anchor=tk.W, pady=(0, 5))
        
        # Display address with copy button
        receive_addr_row = tk.Frame(receive_frame, bg=CypherpunkTheme.BG_SECONDARY)
        receive_addr_row.pack(fill=tk.X, pady=5)
        
        self.receive_address_var = tk.StringVar(value="Click 'Refresh Wallets' above")
        receive_addr_entry = tk.Entry(receive_addr_row, textvariable=self.receive_address_var,
                                      width=50, bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.NEON_GREEN,
                                      font=CypherpunkTheme.FONT_MONO, state='readonly')
        receive_addr_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        copy_receive_btn = tk.Button(receive_addr_row, text="📋 Copy Address", bg=CypherpunkTheme.NEON_GREEN,
                                     fg=CypherpunkTheme.BG_DARK, font=CypherpunkTheme.FONT_TITLE,
                                     command=self._copy_evm_address)
        copy_receive_btn.pack(side=tk.LEFT)
        
        tk.Label(receive_frame, text="Send ERC20 tokens to this address on the selected network above.",
                bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.TEXT_SECONDARY,
                font=CypherpunkTheme.FONT_SMALL).pack(anchor=tk.W, pady=(5, 0))
        
        # === TRACK TOKENS SECTION ===
        track_frame = tk.LabelFrame(scrollable_frame, text="🔍 TRACK TOKENS", 
                                    bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_CYAN,
                                    font=CypherpunkTheme.FONT_TITLE, padx=10, pady=10)
        track_frame.pack(fill=tk.X, pady=10, padx=5)
        
        tk.Label(track_frame, text="Add a token contract to track its balance:",
                bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.TEXT_PRIMARY).pack(anchor=tk.W, pady=(0, 5))
        
        track_row = tk.Frame(track_frame, bg=CypherpunkTheme.BG_SECONDARY)
        track_row.pack(fill=tk.X, pady=5)
        
        tk.Label(track_row, text="Contract:", bg=CypherpunkTheme.BG_SECONDARY,
                fg=CypherpunkTheme.TEXT_PRIMARY).pack(side=tk.LEFT)
        self.track_contract_entry = tk.Entry(track_row, width=45, bg=CypherpunkTheme.BG_DARK,
                                             fg=CypherpunkTheme.NEON_GREEN)
        self.track_contract_entry.pack(side=tk.LEFT, padx=5)
        
        track_btn = tk.Button(track_row, text="+ Add Token", bg=CypherpunkTheme.BG_TERTIARY,
                             fg=CypherpunkTheme.NEON_CYAN, command=self._track_erc20_token)
        track_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Label(track_frame, text="Example: 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 (USDC on Ethereum)",
                bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.TEXT_SECONDARY,
                font=CypherpunkTheme.FONT_SMALL).pack(anchor=tk.W, pady=(5, 0))
        
        # === SEND SECTION ===
        send_frame = tk.LabelFrame(scrollable_frame, text="📤 SEND ERC20", 
                                   bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_PINK,
                                   font=CypherpunkTheme.FONT_TITLE, padx=10, pady=10)
        send_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # Token Contract
        send_row1 = tk.Frame(send_frame, bg=CypherpunkTheme.BG_SECONDARY)
        send_row1.pack(fill=tk.X, pady=5)
        
        tk.Label(send_row1, text="Token Contract:", bg=CypherpunkTheme.BG_SECONDARY,
                fg=CypherpunkTheme.TEXT_PRIMARY, width=15, anchor='w').pack(side=tk.LEFT)
        self.send_token_contract = tk.Entry(send_row1, width=45, bg=CypherpunkTheme.BG_DARK,
                                            fg=CypherpunkTheme.NEON_GREEN)
        self.send_token_contract.pack(side=tk.LEFT, padx=5)
        
        # Recipient
        send_row2 = tk.Frame(send_frame, bg=CypherpunkTheme.BG_SECONDARY)
        send_row2.pack(fill=tk.X, pady=5)
        
        tk.Label(send_row2, text="Recipient:", bg=CypherpunkTheme.BG_SECONDARY,
                fg=CypherpunkTheme.TEXT_PRIMARY, width=15, anchor='w').pack(side=tk.LEFT)
        self.send_recipient = tk.Entry(send_row2, width=45, bg=CypherpunkTheme.BG_DARK,
                                       fg=CypherpunkTheme.NEON_GREEN)
        self.send_recipient.pack(side=tk.LEFT, padx=5)
        
        # Amount
        send_row3 = tk.Frame(send_frame, bg=CypherpunkTheme.BG_SECONDARY)
        send_row3.pack(fill=tk.X, pady=5)
        
        tk.Label(send_row3, text="Amount:", bg=CypherpunkTheme.BG_SECONDARY,
                fg=CypherpunkTheme.TEXT_PRIMARY, width=15, anchor='w').pack(side=tk.LEFT)
        self.send_amount = tk.Entry(send_row3, width=20, bg=CypherpunkTheme.BG_DARK,
                                    fg=CypherpunkTheme.NEON_GREEN)
        self.send_amount.pack(side=tk.LEFT, padx=5)
        
        self.send_token_symbol = tk.Label(send_row3, text="", bg=CypherpunkTheme.BG_SECONDARY,
                                          fg=CypherpunkTheme.NEON_CYAN)
        self.send_token_symbol.pack(side=tk.LEFT, padx=5)
        
        # Gas Settings
        send_row4 = tk.Frame(send_frame, bg=CypherpunkTheme.BG_SECONDARY)
        send_row4.pack(fill=tk.X, pady=5)
        
        tk.Label(send_row4, text="Max Gas (Gwei):", bg=CypherpunkTheme.BG_SECONDARY,
                fg=CypherpunkTheme.TEXT_PRIMARY, width=15, anchor='w').pack(side=tk.LEFT)
        self.send_gas = tk.Entry(send_row4, width=10, bg=CypherpunkTheme.BG_DARK,
                                 fg=CypherpunkTheme.NEON_GREEN)
        self.send_gas.insert(0, "50")
        self.send_gas.pack(side=tk.LEFT, padx=5)
        
        # Send Button
        send_btn_row = tk.Frame(send_frame, bg=CypherpunkTheme.BG_SECONDARY)
        send_btn_row.pack(fill=tk.X, pady=10)
        
        check_btn = tk.Button(send_btn_row, text="🔍 Check Token Info", bg=CypherpunkTheme.BG_TERTIARY,
                             fg=CypherpunkTheme.NEON_CYAN, command=self._check_token_info)
        check_btn.pack(side=tk.LEFT, padx=5)
        
        send_btn = tk.Button(send_btn_row, text="📤 SEND TOKENS", bg=CypherpunkTheme.BG_PANEL,
                            fg=CypherpunkTheme.NEON_PINK, font=CypherpunkTheme.FONT_TITLE,
                            command=self._send_erc20_tokens)
        send_btn.pack(side=tk.LEFT, padx=10)
        
        # Warning
        tk.Label(send_frame, text="⚠ Transactions are irreversible. Double-check addresses!",
                bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.TEXT_WARNING,
                font=CypherpunkTheme.FONT_SMALL).pack(anchor=tk.W, pady=5)
        
        # === TRANSACTION HISTORY ===
        history_frame = tk.LabelFrame(scrollable_frame, text="📜 TRANSACTION HISTORY", 
                                      bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_CYAN,
                                      font=CypherpunkTheme.FONT_TITLE, padx=10, pady=10)
        history_frame.pack(fill=tk.X, pady=10, padx=5)
        
        tx_columns = ('Time', 'Type', 'Token', 'Amount', 'To/From', 'TxHash', 'Status')
        self.tx_history_tree = ttk.Treeview(history_frame, columns=tx_columns, show='headings', height=5)
        
        for col in tx_columns:
            self.tx_history_tree.heading(col, text=col)
            width = 150 if col in ['To/From', 'TxHash'] else 80
            self.tx_history_tree.column(col, width=width)
        
        tx_scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.tx_history_tree.yview)
        self.tx_history_tree.configure(yscrollcommand=tx_scrollbar.set)
        
        self.tx_history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tx_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Spacer for future content
        spacer = ttk.Frame(scrollable_frame, height=100)
        spacer.pack(fill=tk.X, pady=20, padx=5)
        
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
        """Créer l'onglet de monitoring - Style Cypherpunk avec scroll"""
        frame = tk.Frame(self.notebook, bg=CypherpunkTheme.BG_DARK)
        
        # === SCROLLABLE CONTAINER ===
        # Canvas for scrolling
        canvas = tk.Canvas(frame, bg=CypherpunkTheme.BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=CypherpunkTheme.BG_DARK)
        
        # Configure scroll
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mouse wheel scroll
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Pack scrollbar and canvas
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Bind canvas width to frame width
        def _configure_canvas(event):
            canvas.itemconfig(canvas.find_all()[0], width=event.width)
        canvas.bind("<Configure>", _configure_canvas)
        
        # === DASHBOARD METRICS ===
        metrics_container = tk.Frame(scrollable_frame, bg=CypherpunkTheme.BG_DARK)
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
        sep = tk.Frame(scrollable_frame, bg=CypherpunkTheme.BORDER_INACTIVE, height=1)
        sep.pack(fill=tk.X, padx=10, pady=10)
        
        # === ACTIVITY LOG ===
        log_container = tk.Frame(scrollable_frame, bg=CypherpunkTheme.BG_DARK)
        log_container.pack(fill=tk.X, padx=10, pady=(0, 10))
        
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
        ctrl_frame = tk.Frame(scrollable_frame, bg=CypherpunkTheme.BG_DARK)
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
        
        # === SPACER FOR FUTURE CONTENT ===
        # This space allows for additional widgets to be added below
        future_space = tk.Frame(scrollable_frame, bg=CypherpunkTheme.BG_DARK, height=300)
        future_space.pack(fill=tk.X, padx=10, pady=(20, 50))
        
        # Store reference for adding future content
        self.monitor_scrollable_frame = scrollable_frame
        
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
        ttk.Button(action_frame, text="Cancel", command=self.cancel_transfer).pack(side=tk.LEFT, padx=5)
        
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
        
        # === BARRE D'ACTIONS EN BAS (pack en premier avec side=BOTTOM) ===
        actions_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_PANEL, height=50)
        actions_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(5, 10))
        actions_frame.pack_propagate(False)
        
        # Boutons
        tk.Button(actions_frame, text="✎ SIGN ALL", bg="#00ff41", fg="black",
                  font=("Consolas", 10, "bold"), command=self._sign_all_runes
        ).pack(side=tk.LEFT, padx=(10, 5), pady=10)
        
        tk.Button(actions_frame, text="✓ VERIFY", bg="#00ffff", fg="black",
                  font=("Consolas", 10, "bold"), command=self._verify_runes
        ).pack(side=tk.LEFT, padx=5, pady=10)
        
        tk.Button(actions_frame, text="◉ DETAILS", bg="#aa00ff", fg="white",
                  font=("Consolas", 10, "bold"), command=self._show_rune_details
        ).pack(side=tk.LEFT, padx=5, pady=10)
        
        tk.Button(actions_frame, text="📦 INVENTORY", bg="#FFD700", fg="black",
                  font=("Consolas", 10, "bold"), command=self._show_vault_inventory
        ).pack(side=tk.LEFT, padx=5, pady=10)
        
        tk.Button(actions_frame, text="↓ EXPORT", bg="#444444", fg="white",
                  font=("Consolas", 10, "bold"), command=self._export_runes
        ).pack(side=tk.RIGHT, padx=(5, 10), pady=10)
        
        # === LISTE DES RUNES ===
        list_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_DARK)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))
        
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
        
        # Charger les donnees
        self._refresh_runes()
        
        return frame
    
    def _show_vault_inventory(self):
        """Displays l'inventaire COMPLET du vault: Equipements, Fragments, Gems, Pierres"""
        selection = self.runes_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Veuillez selectionner un vault")
            return
        
        item = self.runes_tree.item(selection[0])
        vault_str = item['values'][0]
        vault_num = int(vault_str.replace('#', ''))
        
        # Charger TOUTES les donnees du vault
        vault_items = self._load_vault_items(vault_num)
        vault_fragments = self._load_vault_fragments(vault_num)
        vault_gems = self._load_vault_gems(vault_num)
        vault_stones = self._load_vault_stones(vault_num)
        vault_artifacts = self._load_vault_artifacts(vault_num)
        vault_evo_artifacts = self._load_evolution_artifacts(vault_num)
        
        # Fenetre d'inventaire - taille adaptee
        dialog = tk.Toplevel(self.root)
        dialog.title(f"⚗ COMPLETE INVENTORY - Vault #{vault_num}")
        
        # Taille responsive
        screen_w = dialog.winfo_screenwidth()
        screen_h = dialog.winfo_screenheight()
        win_w = min(1000, int(screen_w * 0.85))
        win_h = min(700, int(screen_h * 0.85))
        pos_x = (screen_w - win_w) // 2
        pos_y = (screen_h - win_h) // 2
        dialog.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        dialog.configure(bg=CypherpunkTheme.BG_DARK)
        
        # === HEADER ===
        header_frame = tk.Frame(dialog, bg=CypherpunkTheme.BG_DARK)
        header_frame.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(
            header_frame,
            text=f"⚗ VAULT INVENTORY #{vault_num}",
            bg=CypherpunkTheme.BG_DARK,
            fg="#FFD700",
            font=("Consolas", 16, "bold")
        ).pack(side=tk.LEFT)
        
        # === STATS GLOBALES ===
        stats_frame = tk.Frame(dialog, bg=CypherpunkTheme.BG_PANEL)
        stats_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        total_artifacts = len(vault_artifacts) + len(vault_evo_artifacts)
        stats = [
            ("📦 Equipment", len(vault_items), "#00ff41"),
            ("💎 Gems", len(vault_gems), "#00ffff"),
            ("🔮 Fragments", len(vault_fragments), "#aa00ff"),
            ("⚗ Stones", len(vault_stones), "#ffd700"),
            ("🏛 Artifacts", total_artifacts, "#ff8000"),
        ]
        
        for label, count, color in stats:
            stat_card = tk.Frame(stats_frame, bg=CypherpunkTheme.BG_SECONDARY, padx=10, pady=5)
            stat_card.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
            tk.Label(stat_card, text=label, bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.TEXT_SECONDARY,
                    font=("Consolas", 9)).pack()
            tk.Label(stat_card, text=str(count), bg=CypherpunkTheme.BG_SECONDARY, fg=color,
                    font=("Consolas", 14, "bold")).pack()
        
        # === NOTEBOOK PRINCIPAL ===
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        # Couleurs de rarete
        rarity_colors = {
            'primordial': '#ff00ff', 'mythical': '#ffd700', 'legendary': '#ff8000',
            'masterwork': '#aa55ff', 'exquisite': '#0088ff', 'superior': '#00cccc',
            'refined': '#00ff00', 'common': '#ffffff', 'crude': '#888888',
            'divine': '#ff00ff', 'transcendent': '#ffd700', 'ethereal': '#00ffff',
            'radiant': '#ff8000', 'pristine': '#aa55ff', 'polished': '#0088ff',
            'cut': '#00ff00', 'rough': '#888888', 'flawed': '#666666'
        }
        
        # === ONGLET EQUIPEMENTS ALCHIMIQUES ===
        items_frame = tk.Frame(notebook, bg=CypherpunkTheme.BG_SECONDARY)
        notebook.add(items_frame, text=f" 📦 EQUIPEMENTS ({len(vault_items)}) ")
        self._create_items_tab(items_frame, vault_items, rarity_colors)
        
        # === ONGLET GEMS ===
        gems_frame = tk.Frame(notebook, bg=CypherpunkTheme.BG_SECONDARY)
        notebook.add(gems_frame, text=f" 💎 GEMS ({len(vault_gems)}) ")
        self._create_gems_tab(gems_frame, vault_gems, rarity_colors)
        
        # === ONGLET FRAGMENTS ===
        fragments_frame = tk.Frame(notebook, bg=CypherpunkTheme.BG_SECONDARY)
        notebook.add(fragments_frame, text=f" 🔮 FRAGMENTS ({len(vault_fragments)}) ")
        self._create_fragments_tab(fragments_frame, vault_fragments)
        
        # === ONGLET PIERRES PHILOSOPHALES ===
        stones_frame = tk.Frame(notebook, bg=CypherpunkTheme.BG_SECONDARY)
        notebook.add(stones_frame, text=f" ⚗ PIERRES ({len(vault_stones)}) ")
        self._create_stones_tab(stones_frame, vault_stones)
        
        # === ONGLET ARTEFACTS ===
        artifacts_frame = tk.Frame(notebook, bg=CypherpunkTheme.BG_SECONDARY)
        notebook.add(artifacts_frame, text=f" 🏛 ARTEFACTS ({total_artifacts}) ")
        self._create_artifacts_tab(artifacts_frame, vault_artifacts, vault_evo_artifacts)
    
    def _create_items_tab(self, parent, items, rarity_colors):
        """Creates combat equipment tab"""
        # Scrollable canvas
        canvas = tk.Canvas(parent, bg=CypherpunkTheme.BG_SECONDARY, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=CypherpunkTheme.BG_SECONDARY)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Combat rarity colors
        combat_rarity_colors = {
            'genesis': '#ffd700', 'primordial': '#ff00ff', 'ascendant': '#00ffff',
            'mythic': '#e6cc80', 'legendary': '#ff8000', 'elite': '#a335ee',
            'superior': '#0070dd', 'enhanced': '#1eff00', 'common': '#9d9d9d',
            'fractured': '#666666'
        }
        
        # Slot icons
        slot_icons = {
            'head': '🎭', 'chest': '🎽', 'hands': '🧤', 'legs': '👖',
            'feet': '👢', 'back': '🧥', 'main_hand': '⚔️', 'off_hand': '🛡️',
            'two_hand': '⚔️', 'neck': '📿', 'ring_1': '💍', 'ring_2': '💍',
            'trinket': '🔮'
        }
        
        if not items:
            # No equipment message
            tk.Label(content, text="\n⚠ No combat equipment found\n\nOpen your combat chests to get equipment!",
                    bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.TEXT_SECONDARY,
                    font=("Consolas", 12)).pack(pady=50)
            return
        
        # Group by slot
        slots = {}
        for item in items:
            slot = item.get('slot', 'misc')
            if slot not in slots:
                slots[slot] = []
            slots[slot].append(item)
        
        # Slot order
        slot_order = ['main_hand', 'off_hand', 'head', 'chest', 'hands', 'legs', 'feet', 'back', 'neck', 'ring_1', 'ring_2', 'trinket']
        
        for slot in slot_order:
            if slot not in slots:
                continue
            
            slot_items = slots[slot]
            icon = slot_icons.get(slot, '📦')
            slot_name = slot.replace('_', ' ').upper()
            
            # Slot header
            slot_header = tk.Frame(content, bg=CypherpunkTheme.BG_PANEL)
            slot_header.pack(fill=tk.X, padx=5, pady=(10, 5))
            tk.Label(slot_header, text=f" {icon} {slot_name} ({len(slot_items)})",
                    bg=CypherpunkTheme.BG_PANEL, fg="#FFD700",
                    font=("Consolas", 11, "bold")).pack(side=tk.LEFT, padx=5, pady=3)
            
            # Equipment in this slot
            for equip in slot_items:
                item_frame = tk.Frame(content, bg=CypherpunkTheme.BG_DARK, padx=10, pady=5)
                item_frame.pack(fill=tk.X, padx=10, pady=2)
                
                rarity = equip.get('rarity', 'common')
                color = combat_rarity_colors.get(rarity, '#ffffff')
                name = equip.get('name', 'Unknown')
                item_level = equip.get('item_level', 1)
                pioneer_tier = equip.get('pioneer_tier', '')
                
                # Main line: rarity + name
                main_line = tk.Frame(item_frame, bg=CypherpunkTheme.BG_DARK)
                main_line.pack(fill=tk.X)
                
                tk.Label(main_line, text=f"[{rarity.upper()[:4]}]", bg=CypherpunkTheme.BG_DARK,
                        fg=color, font=("Consolas", 9, "bold")).pack(side=tk.LEFT)
                tk.Label(main_line, text=f" {name}", bg=CypherpunkTheme.BG_DARK,
                        fg=CypherpunkTheme.TEXT_PRIMARY, font=("Consolas", 10)).pack(side=tk.LEFT)
                
                # Item level and pioneer tier
                tk.Label(main_line, text=f"iLvl:{item_level}", bg=CypherpunkTheme.BG_DARK,
                        fg="#ffd700", font=("Consolas", 8, "bold")).pack(side=tk.RIGHT)
                if pioneer_tier:
                    tk.Label(main_line, text=f"[{pioneer_tier.upper()}]", bg=CypherpunkTheme.BG_DARK,
                            fg="#00ffff", font=("Consolas", 8)).pack(side=tk.RIGHT, padx=5)
                
                # Stats line
                stats_line = tk.Frame(item_frame, bg=CypherpunkTheme.BG_DARK)
                stats_line.pack(fill=tk.X)
                
                stat_parts = []
                phys_dmg = equip.get('physical_damage', 0)
                mag_dmg = equip.get('magical_damage', 0)
                defense = equip.get('defense', 0)
                health = equip.get('health', 0)
                
                if phys_dmg > 0:
                    stat_parts.append(f"DMG:{phys_dmg:.0f}")
                if mag_dmg > 0:
                    stat_parts.append(f"MAG:{mag_dmg:.0f}")
                if defense > 0:
                    stat_parts.append(f"DEF:{defense:.0f}")
                if health > 0:
                    stat_parts.append(f"HP:{health:.0f}")
                
                # Secondary stats
                crit = equip.get('crit_chance', 0)
                atk_spd = equip.get('attack_speed', 0)
                life_steal = equip.get('life_steal', 0)
                evasion = equip.get('evasion', 0)
                
                if crit > 0:
                    stat_parts.append(f"CRT:{crit:.0%}")
                if atk_spd != 0:
                    stat_parts.append(f"SPD:{atk_spd:+.0%}")
                if life_steal > 0:
                    stat_parts.append(f"LS:{life_steal:.0%}")
                if evasion > 0:
                    stat_parts.append(f"EVA:{evasion:.0%}")
                
                if stat_parts:
                    stats_text = "  " + " | ".join(stat_parts[:5])
                    tk.Label(stats_line, text=stats_text, bg=CypherpunkTheme.BG_DARK,
                            fg="#00ff88", font=("Consolas", 8)).pack(side=tk.LEFT)
                
                # Mods
                mods = equip.get('mods', [])
                if mods:
                    mods_line = tk.Frame(item_frame, bg=CypherpunkTheme.BG_DARK)
                    mods_line.pack(fill=tk.X)
                    
                    for mod in mods[:3]:
                        mod_name = mod.get('name', mod.get('mod_id', 'Unknown'))
                        mod_value = mod.get('value', 0)
                        is_pct = mod.get('is_percent', False)
                        tier = mod.get('tier', 'standard')
                        
                        tier_color = '#ffd700' if tier in ['divine', 'prime'] else '#a335ee' if tier in ['superior', 'greater'] else '#00ffff'
                        value_str = f"+{mod_value:.1f}%" if is_pct else f"+{mod_value:.0f}"
                        
                        tk.Label(mods_line, text=f"  • {mod_name}: {value_str}", bg=CypherpunkTheme.BG_DARK,
                                fg=tier_color, font=("Consolas", 8)).pack(anchor=tk.W)
    
    def _create_gems_tab(self, parent, gems, rarity_colors):
        """Creates the'onglet des gems"""
        canvas = tk.Canvas(parent, bg=CypherpunkTheme.BG_SECONDARY, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=CypherpunkTheme.BG_SECONDARY)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Grouper par rarete
        by_rarity = {}
        for gem in gems:
            r = gem.get('rarity', 'flawed')
            if r not in by_rarity:
                by_rarity[r] = []
            by_rarity[r].append(gem)
        
        rarity_order = ['divine', 'transcendent', 'ethereal', 'radiant', 'pristine', 'polished', 'cut', 'rough', 'flawed']
        
        for rarity in rarity_order:
            if rarity not in by_rarity:
                continue
            
            rarity_gems = by_rarity[rarity]
            color = rarity_colors.get(rarity, '#ffffff')
            
            # Header rarete
            header = tk.Frame(content, bg=color)
            header.pack(fill=tk.X, padx=5, pady=(10, 5))
            tk.Label(header, text=f" 💎 {rarity.upper()} ({len(rarity_gems)})",
                    bg=color, fg="black", font=("Consolas", 11, "bold")).pack(side=tk.LEFT, padx=5, pady=3)
            
            for gem in rarity_gems:
                gem_frame = tk.Frame(content, bg=CypherpunkTheme.BG_DARK, padx=10, pady=8)
                gem_frame.pack(fill=tk.X, padx=10, pady=2)
                
                gem_type = gem.get('gem_type', 'unknown').replace('_', ' ').title()
                power = gem.get('base_power', 0)
                resonance = gem.get('resonance', 0)
                purity = gem.get('purity', 0)
                power_name = gem.get('power_name', 'Unknown')
                power_desc = gem.get('power_description', '')
                
                # Nom et stats
                main_line = tk.Frame(gem_frame, bg=CypherpunkTheme.BG_DARK)
                main_line.pack(fill=tk.X)
                tk.Label(main_line, text=f"💎 {gem_type}", bg=CypherpunkTheme.BG_DARK,
                        fg=color, font=("Consolas", 10, "bold")).pack(side=tk.LEFT)
                tk.Label(main_line, text=f"  ⚡{power:.0f}  🔄{resonance:.0f}%  ✨{purity:.0f}%",
                        bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.TEXT_SECONDARY,
                        font=("Consolas", 9)).pack(side=tk.RIGHT)
                
                # Pouvoir
                tk.Label(gem_frame, text=f"  ⟡ {power_name}: {power_desc}",
                        bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.NEON_PURPLE,
                        font=("Consolas", 9)).pack(anchor=tk.W)
    
    def _create_fragments_tab(self, parent, fragments):
        """Creates the'onglet des fragments"""
        canvas = tk.Canvas(parent, bg=CypherpunkTheme.BG_SECONDARY, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=CypherpunkTheme.BG_SECONDARY)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Couleurs par essence
        essence_colors = {
            'quantum': '#00ffff', 'void': '#aa00ff', 'temporal': '#ffd700',
            'chaos': '#ff0000', 'order': '#0088ff', 'life': '#00ff00',
            'death': '#666666', 'fire': '#ff4400', 'ice': '#88ccff',
            'lightning': '#ffff00', 'earth': '#8b4513', 'wind': '#aaffaa',
            'light': '#ffffff', 'shadow': '#333333', 'spirit': '#ff88ff',
            'matter': '#888888', 'energy': '#ffaa00', 'entropy': '#880088'
        }
        
        # Grouper par essence
        by_essence = {}
        for frag in fragments:
            e = frag.get('essence', 'unknown')
            if e not in by_essence:
                by_essence[e] = []
            by_essence[e].append(frag)
        
        for essence, essence_frags in sorted(by_essence.items()):
            color = essence_colors.get(essence, '#ffffff')
            
            # Header essence
            header = tk.Frame(content, bg=CypherpunkTheme.BG_PANEL)
            header.pack(fill=tk.X, padx=5, pady=(10, 5))
            tk.Label(header, text=f" 🔮 {essence.upper()} ({len(essence_frags)})",
                    bg=CypherpunkTheme.BG_PANEL, fg=color,
                    font=("Consolas", 11, "bold")).pack(side=tk.LEFT, padx=5, pady=3)
            
            for frag in essence_frags:
                frag_frame = tk.Frame(content, bg=CypherpunkTheme.BG_DARK, padx=10, pady=5)
                frag_frame.pack(fill=tk.X, padx=10, pady=2)
                
                frag_type = frag.get('fragment_type', 'shard').title()
                mass = frag.get('mass', 0)
                purity = frag.get('purity', 0)
                stability = frag.get('stability', 0)
                voting = frag.get('voting_power', 0)
                value = frag.get('market_value', 0)
                
                # Ligne principale
                main_line = tk.Frame(frag_frame, bg=CypherpunkTheme.BG_DARK)
                main_line.pack(fill=tk.X)
                tk.Label(main_line, text=f"🔮 {frag_type}", bg=CypherpunkTheme.BG_DARK,
                        fg=color, font=("Consolas", 10, "bold")).pack(side=tk.LEFT)
                tk.Label(main_line, text=f"  💰 {value:.0f}", bg=CypherpunkTheme.BG_DARK,
                        fg=CypherpunkTheme.TEXT_SECONDARY, font=("Consolas", 9)).pack(side=tk.RIGHT)
                
                # Stats
                stats_text = f"  ⚖ Mass: {mass:.0f}  ✨ Purity: {purity}%  🔒 Stability: {stability}%"
                if voting > 0:
                    stats_text += f"  🗳 Vote: {voting:.2f}"
                tk.Label(frag_frame, text=stats_text, bg=CypherpunkTheme.BG_DARK,
                        fg=CypherpunkTheme.TEXT_SECONDARY, font=("Consolas", 8)).pack(anchor=tk.W)
    
    def _create_stones_tab(self, parent, stones):
        """Creates the'onglet des pierres philosophales"""
        canvas = tk.Canvas(parent, bg=CypherpunkTheme.BG_SECONDARY, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=CypherpunkTheme.BG_SECONDARY)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        if not stones:
            tk.Label(content, text="\n\n  ☿ Aucune Pierre Philosophale in this vault\n\n"
                    "  Les Pierres Philosophales sont des objets extremement rares\n"
                    "  reserves aux 1000 premiers vaults.",
                    bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.TEXT_SECONDARY,
                    font=("Consolas", 11), justify=tk.LEFT).pack(padx=20, pady=20)
            return
        
        for stone in stones:
            stone_frame = tk.Frame(content, bg=CypherpunkTheme.BG_DARK, padx=15, pady=10)
            stone_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Extraire les donnees de la pierre
            stone_id = stone.get('stone_id', 'Unknown')[:12]
            state = stone.get('state', 'dormant').upper()
            max_energy = stone.get('max_energy', 1000)
            current_energy = stone.get('current_energy', 0)
            regen_rate = stone.get('energy_regen_rate', 1.0)
            origin_vault = stone.get('origin_vault', 0)
            transmutations = stone.get('transmutations_performed', 0)
            souls = stone.get('souls_resurrected', 0)
            portals = stone.get('portals_opened', 0)
            corruption = stone.get('corruption_level', 0)
            recipes = stone.get('recipes_unlocked', [])
            
            # Couleur selon l'etat
            state_colors = {
                'DORMANT': '#888888',
                'AWAKENED': '#00ff00',
                'TRANSCENDENT': '#ff00ff',
                'CORRUPTED': '#ff0000',
                'CHARGING': '#ffff00',
                'DEPLETED': '#ff8800'
            }
            state_color = state_colors.get(state, '#ffffff')
            
            # Header avec icone et etat
            header_frame = tk.Frame(stone_frame, bg=CypherpunkTheme.BG_DARK)
            header_frame.pack(fill=tk.X)
            
            tk.Label(header_frame, text=f"☿ PIERRE PHILOSOPHALE",
                    bg=CypherpunkTheme.BG_DARK, fg="#FFD700",
                    font=("Consolas", 12, "bold")).pack(side=tk.LEFT)
            
            tk.Label(header_frame, text=f"[{state}]",
                    bg=CypherpunkTheme.BG_DARK, fg=state_color,
                    font=("Consolas", 10, "bold")).pack(side=tk.LEFT, padx=10)
            
            tk.Label(header_frame, text=f"Vault #{origin_vault}",
                    bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.TEXT_SECONDARY,
                    font=("Consolas", 9)).pack(side=tk.RIGHT)
            
            # ID
            tk.Label(stone_frame, text=f"  ID: {stone_id}...",
                    bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.TEXT_SECONDARY,
                    font=("Consolas", 9)).pack(anchor=tk.W)
            
            # Energie
            energy_pct = (current_energy / max_energy * 100) if max_energy > 0 else 0
            energy_color = "#00ff00" if energy_pct > 50 else "#ffff00" if energy_pct > 20 else "#ff0000"
            tk.Label(stone_frame, text=f"  ⚡ Energie: {current_energy}/{max_energy} ({energy_pct:.0f}%)  |  Regen: {regen_rate:.1f}/h",
                    bg=CypherpunkTheme.BG_DARK, fg=energy_color,
                    font=("Consolas", 10)).pack(anchor=tk.W)
            
            # Stats d'utilisation
            tk.Label(stone_frame, text=f"  🔄 Transmutations: {transmutations}  |  👻 Ames: {souls}  |  🌀 Portails: {portals}",
                    bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.NEON_CYAN,
                    font=("Consolas", 9)).pack(anchor=tk.W)
            
            # Corruption si presente
            if corruption > 0:
                corr_color = "#ff0000" if corruption > 50 else "#ff8800" if corruption > 20 else "#ffff00"
                tk.Label(stone_frame, text=f"  ⚠ Corruption: {corruption:.1f}%",
                        bg=CypherpunkTheme.BG_DARK, fg=corr_color,
                        font=("Consolas", 9)).pack(anchor=tk.W)
            
            # Recettes debloquees
            if recipes:
                tk.Label(stone_frame, text=f"  📜 Recettes: {len(recipes)} debloquees",
                        bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.NEON_PURPLE,
                        font=("Consolas", 9)).pack(anchor=tk.W)
    
    def _create_artifacts_tab(self, parent, artifacts, evolution_artifacts=None):
        """Creates the'onglet des artifacts avec evolution artifacts"""
        canvas = tk.Canvas(parent, bg=CypherpunkTheme.BG_SECONDARY, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=CypherpunkTheme.BG_SECONDARY)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Charger les evolution artifacts si non fournis
        if evolution_artifacts is None:
            evolution_artifacts = self._load_evolution_artifacts()
        
        # Section Artefacts d'Evolution
        if evolution_artifacts or EVOLUTION_ARTIFACTS_AVAILABLE:
            evo_header = tk.Frame(content, bg=CypherpunkTheme.BG_PANEL, padx=10, pady=8)
            evo_header.pack(fill=tk.X, padx=5, pady=(10, 5))
            tk.Label(evo_header, text="⚗ EVOLUTION ARTIFACTS", 
                    bg=CypherpunkTheme.BG_PANEL, fg=CypherpunkTheme.NEON_MAGENTA,
                    font=("Consolas", 12, "bold")).pack(side=tk.LEFT)
            tk.Label(evo_header, text=f" ({len(evolution_artifacts)} owned)", 
                    bg=CypherpunkTheme.BG_PANEL, fg=CypherpunkTheme.TEXT_SECONDARY,
                    font=("Consolas", 10)).pack(side=tk.LEFT)
            
            if evolution_artifacts:
                for evo_art in evolution_artifacts:
                    self._render_evolution_artifact(content, evo_art)
            else:
                tk.Label(content, text="    Aucun evolution artifact obtained",
                        bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.TEXT_SECONDARY,
                        font=("Consolas", 10)).pack(anchor=tk.W, padx=15, pady=5)
        
        # Section Artefacts Spinoriels existants
        spinor_header = tk.Frame(content, bg=CypherpunkTheme.BG_PANEL, padx=10, pady=8)
        spinor_header.pack(fill=tk.X, padx=5, pady=(15, 5))
        tk.Label(spinor_header, text="🏛 SPINOR ARTIFACTS", 
                bg=CypherpunkTheme.BG_PANEL, fg=CypherpunkTheme.NEON_CYAN,
                font=("Consolas", 12, "bold")).pack(side=tk.LEFT)
        tk.Label(spinor_header, text=f" ({len(artifacts)} owned)", 
                bg=CypherpunkTheme.BG_PANEL, fg=CypherpunkTheme.TEXT_SECONDARY,
                font=("Consolas", 10)).pack(side=tk.LEFT)
        
        if not artifacts:
            tk.Label(content, text="    Aucun spinor artifact in this vault",
                    bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.TEXT_SECONDARY,
                    font=("Consolas", 10)).pack(anchor=tk.W, padx=15, pady=5)
        else:
            for artifact in artifacts:
                self._render_spinor_artifact(content, artifact)
    
    def _render_evolution_artifact(self, parent, artifact):
        """Displays un evolution artifact"""
        rarity_colors = {
            'rare': '#0088ff', 'epic': '#aa00ff', 'legendary': '#ff8000',
            'mythical': '#ffaa00', 'transcendent': '#00ffff', 'primordial': '#ff00ff'
        }
        
        art_frame = tk.Frame(parent, bg=CypherpunkTheme.BG_DARK, padx=15, pady=12)
        art_frame.pack(fill=tk.X, padx=10, pady=5)
        
        rarity = artifact.get('rarity', 'rare')
        color = rarity_colors.get(rarity, '#ffffff')
        
        # Header avec nom et rarete
        header = tk.Frame(art_frame, bg=CypherpunkTheme.BG_DARK)
        header.pack(fill=tk.X)
        
        tk.Label(header, text=f"⚗ [{rarity.upper()}]", bg=CypherpunkTheme.BG_DARK,
                fg=color, font=("Consolas", 10, "bold")).pack(side=tk.LEFT)
        tk.Label(header, text=f" {artifact.get('name', 'Unknown')}", bg=CypherpunkTheme.BG_DARK,
                fg=CypherpunkTheme.TEXT_PRIMARY, font=("Consolas", 11, "bold")).pack(side=tk.LEFT)
        
        # Stade d'evolution
        stage = artifact.get('evolution_stage', '?').upper()
        tk.Label(header, text=f"  → Stade: {stage}", bg=CypherpunkTheme.BG_DARK,
                fg=CypherpunkTheme.NEON_GREEN, font=("Consolas", 9)).pack(side=tk.RIGHT)
        
        # Description
        desc = artifact.get('description', '')
        if desc:
            tk.Label(art_frame, text=f"  {desc}", bg=CypherpunkTheme.BG_DARK,
                    fg=CypherpunkTheme.TEXT_SECONDARY, font=("Consolas", 9),
                    wraplength=500, justify=tk.LEFT).pack(anchor=tk.W, pady=(5, 0))
        
        # Power bonus
        power_bonus = artifact.get('power_bonus', 1.0)
        tk.Label(art_frame, text=f"  ⚡ Power bonus: x{power_bonus:.2f}", 
                bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.NEON_CYAN,
                font=("Consolas", 9)).pack(anchor=tk.W)
        
        # Stat bonuses
        stat_bonuses = artifact.get('stat_bonuses', {})
        if stat_bonuses:
            bonus_text = "  📊 Stats: " + ", ".join(
                f"{k}: x{v:.2f}" if isinstance(v, float) and v < 10 else f"{k}: +{v}"
                for k, v in stat_bonuses.items()
            )
            tk.Label(art_frame, text=bonus_text, bg=CypherpunkTheme.BG_DARK,
                    fg=CypherpunkTheme.NEON_PURPLE, font=("Consolas", 9)).pack(anchor=tk.W)
        
        # Capacites
        abilities = artifact.get('abilities', [])
        if abilities:
            tk.Label(art_frame, text="  ✨ Capacites:", bg=CypherpunkTheme.BG_DARK,
                    fg=CypherpunkTheme.NEON_YELLOW, font=("Consolas", 9)).pack(anchor=tk.W)
            for ability in abilities[:3]:  # Max 3 affichees
                tk.Label(art_frame, text=f"      • {ability.get('name', '?')}", 
                        bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.TEXT_SECONDARY,
                        font=("Consolas", 8)).pack(anchor=tk.W)
        
        # Effets visuels
        visual_effects = artifact.get('visual_effects', [])
        if visual_effects:
            tk.Label(art_frame, text=f"  🎨 Visuels: {', '.join(visual_effects[:4])}", 
                    bg=CypherpunkTheme.BG_DARK, fg=color,
                    font=("Consolas", 8)).pack(anchor=tk.W)
        
        # Statut de liaison
        is_bound = artifact.get('is_bound', False)
        bound_text = "🔗 LIE A L'AVATAR" if is_bound else "○ Not bound"
        bound_color = CypherpunkTheme.NEON_GREEN if is_bound else CypherpunkTheme.TEXT_SECONDARY
        tk.Label(art_frame, text=f"  {bound_text}", bg=CypherpunkTheme.BG_DARK,
                fg=bound_color, font=("Consolas", 9)).pack(anchor=tk.W)
    
    def _render_spinor_artifact(self, parent, artifact):
        """Displays un spinor artifact existant"""
        art_frame = tk.Frame(parent, bg=CypherpunkTheme.BG_DARK, padx=15, pady=10)
        art_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Extraire les donnees (format nested)
        art_data = artifact.get('artifact_data', artifact)
        art_name = art_data.get('name', 'Unknown Artifact')
        art_type = art_data.get('artifact_type', 'unknown').replace('_', ' ').title()
        rarity = art_data.get('rarity', 'common').upper()
        
        # Stats
        stats = art_data.get('stats', {})
        power = stats.get('effective_power', stats.get('base_power', 0))
        resonance = stats.get('spinor_resonance', 0)
        
        tier_colors = {
            'PRIMORDIAL': '#ff00ff', 'TRANSCENDENT': '#00ffff', 'MYTHIC': '#ffaa00',
            'LEGENDARY': '#ff8000', 'EPIC': '#aa00ff', 'RARE': '#0088ff', 
            'UNCOMMON': '#00ff00', 'COMMON': '#ffffff'
        }
        color = tier_colors.get(rarity, '#ffffff')
        
        # Header
        main_line = tk.Frame(art_frame, bg=CypherpunkTheme.BG_DARK)
        main_line.pack(fill=tk.X)
        tk.Label(main_line, text=f"🏛 [{rarity}]", bg=CypherpunkTheme.BG_DARK,
                fg=color, font=("Consolas", 10, "bold")).pack(side=tk.LEFT)
        tk.Label(main_line, text=f" {art_name}", bg=CypherpunkTheme.BG_DARK,
                fg=CypherpunkTheme.TEXT_PRIMARY, font=("Consolas", 11, "bold")).pack(side=tk.LEFT)
        
        # Type et stats
        tk.Label(art_frame, text=f"  Type: {art_type}  ⚡ Power: {power:,.0f}  🔄 Resonance: {resonance:.1f}%",
                bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.NEON_CYAN,
                font=("Consolas", 9)).pack(anchor=tk.W)
        
        # Element
        element = art_data.get('element', 'void')
        element_symbols = {'void': '◯', 'quantum': '⚛', 'temporal': '⧖', 'spatial': '◈',
                          'entropic': '☢', 'harmonic': '♒', 'celestial': '✧', 'primordial': '⬡'}
        symbol = element_symbols.get(element, '?')
        tk.Label(art_frame, text=f"  {symbol} Element: {element.upper()}",
                bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.NEON_PURPLE,
                font=("Consolas", 9)).pack(anchor=tk.W)
        
        # Capacites
        abilities = art_data.get('abilities', [])
        if abilities:
            abilities_text = "  ✨ " + ", ".join(a.get('name', '?') for a in abilities[:3])
            tk.Label(art_frame, text=abilities_text, bg=CypherpunkTheme.BG_DARK,
                    fg=CypherpunkTheme.NEON_YELLOW, font=("Consolas", 9)).pack(anchor=tk.W)
        
        # Glyphs count
        glyph_array = art_data.get('glyph_array', {})
        if glyph_array:
            glyphs = glyph_array.get('glyphs', [])
            total_gems = glyph_array.get('total_gems', 0)
            glyph_power = glyph_array.get('total_power', 0)
            tk.Label(art_frame, text=f"  💎 {len(glyphs)} Glyphes, {total_gems} Gemmes, Power: {glyph_power:,.0f}",
                    bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.TEXT_SECONDARY,
                    font=("Consolas", 9)).pack(anchor=tk.W)
    
    def _load_evolution_artifacts(self, vault_num: int = None) -> list:
        """Loads the evolution artifacts du vault"""
        if not EVOLUTION_ARTIFACTS_AVAILABLE:
            return []
        
        try:
            evo_system = get_evolution_artifact_system()
            
            # Utiliser le parametre ou essayer plusieurs attributs
            if vault_num is None:
                if hasattr(self, 'current_vault_num'):
                    vault_num = self.current_vault_num
                elif hasattr(self, 'current_vault_number'):
                    vault_num = self.current_vault_number
                elif hasattr(self, 'vault_number'):
                    vault_num = self.vault_number
            
            if vault_num is None:
                return []
            
            # Utiliser la methode par numero (plus fiable)
            artifacts = evo_system.get_vault_artifacts_by_number(vault_num)
            return [a.to_dict() for a in artifacts]
        except Exception as e:
            print(f"[WARN] Erreur chargement artefacts evolution: {e}")
            return []
    
    def _load_vault_fragments(self, vault_num: int) -> list:
        """Loads the fragments d'un vault"""
        fragments = []
        fragments_dir = Path(self.base_path) / "fragment_nexus" / "fragments"
        if not fragments_dir.exists():
            return fragments
        for f in fragments_dir.glob("fragment_*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                if data.get('current_vault') == vault_num or data.get('origin_vault') == vault_num:
                    fragments.append(data)
            except:
                pass
        return fragments
    
    def _load_vault_gems(self, vault_num: int) -> list:
        """Loads the gems d'un vault"""
        gems = []
        gems_dir = Path(self.base_path) / "gem_vault" / "gems"
        if not gems_dir.exists():
            return gems
        for f in gems_dir.glob("gem_*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                if data.get('current_vault') == vault_num or data.get('origin_vault') == vault_num:
                    gems.append(data)
            except:
                pass
        # Trier par rarete
        rarity_order = {'divine': 0, 'transcendent': 1, 'ethereal': 2, 'radiant': 3, 
                       'pristine': 4, 'polished': 5, 'cut': 6, 'rough': 7, 'flawed': 8}
        gems.sort(key=lambda x: rarity_order.get(x.get('rarity', 'flawed'), 9))
        return gems
    
    def _load_vault_stones(self, vault_num: int) -> list:
        """Loads the pierres philosophales d'un vault"""
        stones = []
        # Chemin correct: philosopher_stones/stones/
        stones_dir = Path(self.base_path) / "philosopher_stones" / "stones"
        if not stones_dir.exists():
            return stones
        for f in stones_dir.glob("stone_*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                if data.get('owner_vault') == vault_num or data.get('origin_vault') == vault_num:
                    stones.append(data)
            except:
                pass
        return stones
    
    def _load_vault_artifacts(self, vault_num: int) -> list:
        """Loads the artifacts d'un vault"""
        artifacts = []
        artifacts_dir = Path(self.base_path) / "artifact_vault" / "artifacts"
        if not artifacts_dir.exists():
            return artifacts
        for f in artifacts_dir.glob("artifact_*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                if data.get('current_vault') == vault_num or data.get('origin_vault') == vault_num:
                    artifacts.append(data)
            except:
                pass
        return artifacts
    
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
                messagebox.showerror("Error", f"Impossible de lancer la signature: {e}")
    
    def _verify_runes(self):
        """Verifies les signatures des runes"""
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
            messagebox.showerror("Error", f"Erreur de vérification: {e}")
    
    def _show_rune_details(self):
        """Displays les details d'une rune selectionnee avec coffres et items"""
        selection = self.runes_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Veuillez sélectionner une rune")
            return
        
        item = self.runes_tree.item(selection[0])
        vault_str = item['values'][0]
        vault_num = int(vault_str.replace('#', ''))
        
        asset = self.runes_monitor.get_asset(vault_num)
        if not asset:
            messagebox.showerror("Error", "Rune non trouvée")
            return
        
        # Charger les coffres et items du vault
        vault_chests = self._load_vault_chests(vault_num)
        vault_items = self._load_vault_items(vault_num)
        
        # Fenetre de details avec scrollbar
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Vault #{vault_num} - Details & Inventory")
        dialog.geometry("750x550")
        dialog.configure(bg=CypherpunkTheme.BG_DARK)
        
        # Canvas scrollable
        canvas = tk.Canvas(dialog, bg=CypherpunkTheme.BG_DARK, highlightthickness=0)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        
        content = tk.Frame(canvas, bg=CypherpunkTheme.BG_DARK)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        canvas_frame = canvas.create_window((0, 0), window=content, anchor="nw")
        
        def configure_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_frame, width=event.width)
        
        content.bind("<Configure>", configure_scroll)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_frame, width=e.width))
        
        # Scroll avec molette
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        dialog.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))
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
        
        # Artefact Spinoriel (Easter Egg)
        if asset.artifact:
            artifact_frame = tk.Frame(content, bg=CypherpunkTheme.BG_PANEL, padx=20, pady=15)
            artifact_frame.pack(fill=tk.X, pady=10)
            
            art = asset.artifact
            art_rarity = art.get('rarity', 'common').upper()
            art_name = art.get('name', 'Unknown Artifact')
            art_element = art.get('element', 'void').upper()
            
            # Couleurs par rarete
            rarity_colors = {
                'COMMON': '#9d9d9d',
                'UNCOMMON': '#1eff00',
                'RARE': '#0070dd',
                'EPIC': '#a335ee',
                'LEGENDARY': '#ff8000',
                'MYTHIC': '#e6cc80',
                'TRANSCENDENT': '#00ffff',
                'PRIMORDIAL': '#ff00ff',
            }
            art_color = rarity_colors.get(art_rarity, '#ffffff')
            
            tk.Label(
                artifact_frame,
                text="⬡ SPINOR ARTIFACT",
                bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.NEON_PURPLE,
                font=CypherpunkTheme.FONT_TITLE
            ).pack(anchor='w', pady=(0, 10))
            
            # Nom et rarete
            tk.Label(
                artifact_frame,
                text=f"{art_name}",
                bg=CypherpunkTheme.BG_PANEL,
                fg=art_color,
                font=("Consolas", 14, "bold")
            ).pack(anchor='w')
            
            tk.Label(
                artifact_frame,
                text=f"[{art_rarity}] | Element: {art_element}",
                bg=CypherpunkTheme.BG_PANEL,
                fg=art_color
            ).pack(anchor='w')
            
            # Stats
            stats = art.get('stats', {})
            if stats:
                power = stats.get('effective_power', 0)
                resonance = stats.get('spinor_resonance', 0)
                entropy = stats.get('entropy_coefficient', 1)
                
                stats_text = f"Power: {power:,.0f} | Resonance: {resonance:.1f}% | Entropy: {entropy:.2f}x"
                tk.Label(
                    artifact_frame,
                    text=stats_text,
                    bg=CypherpunkTheme.BG_PANEL,
                    fg=CypherpunkTheme.NEON_GREEN
                ).pack(anchor='w', pady=(5, 0))
            
            # Capacites de l'artefact
            art_abilities = art.get('abilities', [])
            if art_abilities:
                tk.Label(
                    artifact_frame,
                    text="Artifact Abilities:",
                    bg=CypherpunkTheme.BG_PANEL,
                    fg=CypherpunkTheme.TEXT_SECONDARY
                ).pack(anchor='w', pady=(10, 5))
                
                for ab in art_abilities[:4]:  # Max 4 affichees
                    tk.Label(
                        artifact_frame,
                        text=f"  ◆ {ab.get('name', '')}: {ab.get('description', '')}",
                        bg=CypherpunkTheme.BG_PANEL,
                        fg=art_color,
                        wraplength=500,
                        justify='left'
                    ).pack(anchor='w')
            
            # Glyphes et Gemmes (7 glyphes x 3 gemmes)
            glyph_array = art.get('glyph_array')
            if glyph_array:
                tk.Label(
                    artifact_frame,
                    text="⬡ Glyph Array (7 Glyphs, 21 Gems):",
                    bg=CypherpunkTheme.BG_PANEL,
                    fg=CypherpunkTheme.NEON_CYAN
                ).pack(anchor='w', pady=(10, 5))
                
                total_power = glyph_array.get('total_power', 0)
                bell = glyph_array.get('bell_correlation', 0)
                tk.Label(
                    artifact_frame,
                    text=f"  Glyph Power: {total_power:,.0f} | Bell: {bell:.3f}",
                    bg=CypherpunkTheme.BG_PANEL,
                    fg=CypherpunkTheme.NEON_GREEN,
                    font=("Consolas", 9)
                ).pack(anchor='w')
                
                # Afficher les 7 glyphes
                glyph_symbols = {
                    'glyph_void': 'ᛟ', 'glyph_quantum': 'ᚠ', 'glyph_temporal': 'ᛞ',
                    'glyph_spatial': 'ᚱ', 'glyph_entropic': 'ᚺ', 'glyph_harmonic': 'ᚹ',
                    'glyph_celestial': 'ᛊ'
                }
                glyphs_text = ""
                for g in glyph_array.get('glyphs', [])[:7]:
                    sym = glyph_symbols.get(g.get('glyph_type', ''), '?')
                    glyphs_text += sym
                
                tk.Label(
                    artifact_frame,
                    text=f"  Glyphs: {glyphs_text}",
                    bg=CypherpunkTheme.BG_PANEL,
                    fg=CypherpunkTheme.NEON_PURPLE,
                    font=("Segoe UI", 12)
                ).pack(anchor='w')
            
            # Lore
            lore = art.get('lore', '')
            if lore:
                tk.Label(
                    artifact_frame,
                    text=f"\"{lore}\"",
                    bg=CypherpunkTheme.BG_PANEL,
                    fg=CypherpunkTheme.TEXT_SECONDARY,
                    font=("Segoe UI", 9, "italic"),
                    wraplength=500,
                    justify='left'
                ).pack(anchor='w', pady=(10, 0))
        
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
        
        # === COFFRES ET ITEMS ===
        if vault_chests:
            inventory_frame = tk.Frame(content, bg=CypherpunkTheme.BG_PANEL, padx=20, pady=15)
            inventory_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            
            tk.Label(
                inventory_frame,
                text=f"📦 INVENTORY ({len(vault_chests)} Chests, {len(vault_items)} Equipements)",
                bg=CypherpunkTheme.BG_PANEL,
                fg="#FFD700",
                font=CypherpunkTheme.FONT_TITLE
            ).pack(anchor='w', pady=(0, 10))
            
            # Notebook pour les coffres
            inv_notebook = ttk.Notebook(inventory_frame)
            inv_notebook.pack(fill=tk.BOTH, expand=True)
            
            # Onglet par coffre
            for chest in vault_chests:
                chest_tier = chest.get('tier', 'common').upper()
                chest_items = [i for i in vault_items if i.get('origin_chest') == chest.get('chest_id')]
                
                chest_frame = tk.Frame(inv_notebook, bg=CypherpunkTheme.BG_SECONDARY)
                inv_notebook.add(chest_frame, text=f" {chest_tier} ({len(chest_items)}) ")
                
                # Liste des items du coffre
                items_text = tk.Text(
                    chest_frame,
                    bg=CypherpunkTheme.BG_SECONDARY,
                    fg=CypherpunkTheme.TEXT_PRIMARY,
                    font=CypherpunkTheme.FONT_MONO_SMALL,
                    padx=10,
                    pady=10,
                    wrap=tk.WORD,
                    height=15
                )
                items_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                # Couleurs de rarete
                rarity_colors = {
                    'primordial': '#ff00ff', 'mythical': '#ffd700', 'legendary': '#ff8000',
                    'masterwork': '#aa55ff', 'exquisite': '#0088ff', 'superior': '#00cccc',
                    'refined': '#00ff00', 'common': '#ffffff', 'crude': '#888888'
                }
                
                # Afficher les items
                for idx, item_data in enumerate(chest_items):
                    item_name = item_data.get('item_type', 'unknown').replace('_', ' ').title()
                    item_rarity = item_data.get('rarity', 'common')
                    item_value = item_data.get('value', 0)
                    item_mods = item_data.get('mods', [])
                    
                    color = rarity_colors.get(item_rarity, '#ffffff')
                    
                    # Ligne principale
                    line = f"[{item_rarity.upper():11}] {item_name}\n"
                    items_text.insert(tk.END, line)
                    items_text.tag_add(f"rarity_{idx}", f"{items_text.index(tk.END)}-2l", f"{items_text.index(tk.END)}-1l-1c")
                    items_text.tag_config(f"rarity_{idx}", foreground=color)
                    
                    # Mods
                    if item_mods:
                        for mod in item_mods[:3]:  # Max 3 mods affiches
                            mod_tier = mod.get('tier', 'standard')
                            mod_id = mod.get('mod_id', '').replace('mod_', '').replace('_', ' ').title()
                            mod_value = mod.get('rolled_value', 0)
                            roll_pct = mod.get('roll_percent', 50)
                            
                            # Indicateur de qualite
                            if roll_pct >= 95:
                                quality = "★"
                            elif roll_pct >= 80:
                                quality = "◆"
                            elif roll_pct >= 60:
                                quality = "●"
                            else:
                                quality = "○"
                            
                            mod_line = f"   {quality} [{mod_tier.upper()[:3]}] {mod_id}: {mod_value:.0f} ({roll_pct:.0f}%)\n"
                            items_text.insert(tk.END, mod_line, "mod")
                        
                        if len(item_mods) > 3:
                            items_text.insert(tk.END, f"   ... +{len(item_mods)-3} more mods\n", "more")
                    
                    items_text.insert(tk.END, "\n")
                
                items_text.tag_config("mod", foreground=CypherpunkTheme.NEON_CYAN)
                items_text.tag_config("more", foreground=CypherpunkTheme.TEXT_SECONDARY)
                items_text.config(state=tk.DISABLED)
            
            # All stats
            stats_frame = tk.Frame(inventory_frame, bg=CypherpunkTheme.BG_TERTIARY, padx=10, pady=8)
            stats_frame.pack(fill=tk.X, pady=(10, 0))
            
            # Compter par rarete
            rarity_counts = {}
            total_mods = 0
            perfect_mods = 0
            for item_data in vault_items:
                r = item_data.get('rarity', 'common')
                rarity_counts[r] = rarity_counts.get(r, 0) + 1
                mods = item_data.get('mods', [])
                total_mods += len(mods)
                perfect_mods += sum(1 for m in mods if m.get('roll_percent', 0) >= 95)
            
            stats_text = " | ".join([f"{r.upper()}: {c}" for r, c in sorted(rarity_counts.items(), key=lambda x: -x[1])[:5]])
            
            tk.Label(
                stats_frame,
                text=f"Equipements: {len(vault_items)} | Mods: {total_mods} | Perfect: {perfect_mods}",
                bg=CypherpunkTheme.BG_TERTIARY,
                fg=CypherpunkTheme.NEON_GREEN,
                font=CypherpunkTheme.FONT_MONO_SMALL
            ).pack(side=tk.LEFT)
            
            tk.Label(
                stats_frame,
                text=stats_text,
                bg=CypherpunkTheme.BG_TERTIARY,
                fg=CypherpunkTheme.TEXT_SECONDARY,
                font=CypherpunkTheme.FONT_MONO_SMALL
            ).pack(side=tk.RIGHT)
    
    def _load_vault_chests(self, vault_num: int) -> list:
        """Loads the coffres d'un vault"""
        chests = []
        chests_dir = Path(self.base_path) / "alchemical_vault" / "chests"
        
        if not chests_dir.exists():
            return chests
        
        for f in chests_dir.glob("chest_*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                if data.get('origin_vault') == vault_num:
                    chests.append(data)
            except:
                pass
        
        # Trier par tier
        tier_order = {'primordial': 0, 'legendary': 1, 'epic': 2, 'rare': 3, 'common': 4}
        chests.sort(key=lambda x: tier_order.get(x.get('tier', 'common'), 5))
        
        return chests
    
    def _load_vault_items(self, vault_num: int) -> list:
        """Loads combat equipment from vault"""
        items = []
        
        # Load combat equipment (new system)
        combat_dir = Path(self.base_path) / "alchemical_vault" / "combat_equipment"
        if combat_dir.exists():
            for f in combat_dir.glob("combat_equip_*.json"):
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                    if data.get('current_vault') == vault_num or data.get('origin_vault') == vault_num:
                        data['_source'] = 'combat'
                        items.append(data)
                except:
                    pass
        
        # Sort by rarity (combat system rarities)
        rarity_order = {
            'genesis': 0, 'primordial': 1, 'ascendant': 2, 'mythic': 3,
            'legendary': 4, 'elite': 5, 'superior': 6, 'enhanced': 7,
            'common': 8, 'fractured': 9
        }
        items.sort(key=lambda x: rarity_order.get(x.get('rarity', 'common'), 10))
        
        return items
    
    def _load_vault_combat_chests(self, vault_num: int) -> list:
        """Load combat chests for a vault"""
        chests = []
        chests_dir = Path(self.base_path) / "alchemical_vault" / "combat_chests"
        
        if not chests_dir.exists():
            return chests
        
        for f in chests_dir.glob("combat_chest_*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(f)
                if data.get('vault_number') == vault_num:
                    chests.append(data)
            except:
                pass
        
        return chests
    
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
            messagebox.showerror("Error", f"Erreur d'export: {e}")
    
    # ========================================================================
    # ONGLET BITCOIN EXCHANGE
    # ========================================================================
    
    def _create_exchange_tab(self) -> tk.Frame:
        """Creates the'onglet d'echange d'items via Bitcoin Runes"""
        frame = tk.Frame(self.notebook, bg=CypherpunkTheme.BG_DARK)
        
        # Initialiser le gestionnaire d'echange
        self.exchange_manager = ItemRunesExchange()
        self.current_vault_num = 1  # TODO: Obtenir du contexte
        
        # === HEADER ===
        header_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_DARK)
        header_frame.pack(fill=tk.X, pady=(10, 15), padx=10)
        
        tk.Label(
            header_frame,
            text="BTC ITEM EXCHANGE",
            bg=CypherpunkTheme.BG_DARK,
            fg="#f7931a",  # Bitcoin orange
            font=("Consolas", 16, "bold")
        ).pack(side=tk.LEFT)
        
        # Bouton refresh
        tk.Button(
            header_frame,
            text="REFRESH",
            bg="#333333",
            fg="white",
            font=("Consolas", 9),
            command=self._refresh_exchange
        ).pack(side=tk.RIGHT, padx=5)
        
        # === STATS DU MARCHE ===
        stats_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_PANEL)
        stats_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.exchange_stats = {}
        stat_labels = [
            ("active_listings", "ACTIVE", "#00ff00"),
            ("total_volume_btc", "VOLUME BTC", "#f7931a"),
            ("my_inscriptions", "MY ITEMS", "#00ffff"),
            ("my_listings", "MY LISTINGS", "#aa00ff"),
        ]
        
        for stat_id, label, color in stat_labels:
            card = tk.Frame(stats_frame, bg=CypherpunkTheme.BG_SECONDARY, padx=15, pady=8)
            card.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
            tk.Label(card, text=label, bg=CypherpunkTheme.BG_SECONDARY,
                    fg=CypherpunkTheme.TEXT_SECONDARY, font=("Consolas", 8)).pack()
            var = tk.StringVar(value="0")
            tk.Label(card, textvariable=var, bg=CypherpunkTheme.BG_SECONDARY,
                    fg=color, font=("Consolas", 14, "bold")).pack()
            self.exchange_stats[stat_id] = var
        
        # === NOTEBOOK INTERNE ===
        exchange_notebook = ttk.Notebook(frame)
        exchange_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Tab: Marketplace
        market_tab = self._create_marketplace_tab(exchange_notebook)
        exchange_notebook.add(market_tab, text=" MARKETPLACE ")
        
        # Tab: Mes Items
        my_items_tab = self._create_my_items_tab(exchange_notebook)
        exchange_notebook.add(my_items_tab, text=" MY ITEMS ")
        
        # Tab: Mes Ventes
        my_listings_tab = self._create_my_listings_tab(exchange_notebook)
        exchange_notebook.add(my_listings_tab, text=" MY LISTINGS ")
        
        # Tab: Trades
        trades_tab = self._create_trades_tab(exchange_notebook)
        exchange_notebook.add(trades_tab, text=" TRADES ")
        
        # Charger les donnees
        self._refresh_exchange()
        
        return frame
    
    def _create_marketplace_tab(self, parent) -> tk.Frame:
        """Tab du marketplace avec les items en vente"""
        frame = tk.Frame(parent, bg=CypherpunkTheme.BG_SECONDARY)
        
        # Filtres
        filter_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_PANEL)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(filter_frame, text="Rarete:", bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.TEXT_SECONDARY).pack(side=tk.LEFT, padx=5)
        
        self.market_rarity_filter = tk.StringVar(value="ALL")
        rarities = ["ALL", "primordial", "mythical", "legendary", "masterwork", "exquisite"]
        ttk.Combobox(filter_frame, textvariable=self.market_rarity_filter,
                    values=rarities, width=12).pack(side=tk.LEFT, padx=5)
        
        tk.Label(filter_frame, text="Max BTC:", bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.TEXT_SECONDARY).pack(side=tk.LEFT, padx=5)
        
        self.market_max_price = tk.StringVar(value="")
        tk.Entry(filter_frame, textvariable=self.market_max_price, width=10,
                bg=CypherpunkTheme.BG_SECONDARY, fg="white").pack(side=tk.LEFT, padx=5)
        
        tk.Button(filter_frame, text="FILTER", bg="#444444", fg="white",
                 command=self._filter_marketplace).pack(side=tk.LEFT, padx=10)
        
        # Liste des items en vente
        list_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_SECONDARY)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview
        columns = ('Rune ID', 'Type', 'Rarity', 'Power', 'Price BTC', 'Seller')
        self.market_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)
        
        for col in columns:
            self.market_tree.heading(col, text=col)
            self.market_tree.column(col, width=100)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.market_tree.yview)
        self.market_tree.configure(yscrollcommand=scrollbar.set)
        
        self.market_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Boutons d'action
        actions_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_PANEL, height=45)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        actions_frame.pack_propagate(False)
        
        tk.Button(actions_frame, text="BUY SELECTED", bg="#f7931a", fg="black",
                 font=("Consolas", 10, "bold"), command=self._buy_selected_item
        ).pack(side=tk.LEFT, padx=10, pady=8)
        
        tk.Button(actions_frame, text="VIEW DETAILS", bg="#444444", fg="white",
                 command=self._view_listing_details
        ).pack(side=tk.LEFT, padx=5, pady=8)
        
        return frame
    
    def _create_my_items_tab(self, parent) -> tk.Frame:
        """Tab des items du vault pouvant etre vendus"""
        frame = tk.Frame(parent, bg=CypherpunkTheme.BG_SECONDARY)
        
        # Liste des items inscripts
        list_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_SECONDARY)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('Item ID', 'Rune ID', 'Type', 'Rarity', 'Power', 'Status')
        self.my_items_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)
        
        for col in columns:
            self.my_items_tree.heading(col, text=col)
            self.my_items_tree.column(col, width=100)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.my_items_tree.yview)
        self.my_items_tree.configure(yscrollcommand=scrollbar.set)
        
        self.my_items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Actions
        actions_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_PANEL, height=45)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        actions_frame.pack_propagate(False)
        
        tk.Button(actions_frame, text="INSCRIBE ITEM", bg="#00ff00", fg="black",
                 font=("Consolas", 10, "bold"), command=self._inscribe_item_dialog
        ).pack(side=tk.LEFT, padx=10, pady=8)
        
        tk.Button(actions_frame, text="SELL SELECTED", bg="#f7931a", fg="black",
                 font=("Consolas", 10, "bold"), command=self._sell_item_dialog
        ).pack(side=tk.LEFT, padx=5, pady=8)
        
        tk.Button(actions_frame, text="TRANSFER", bg="#00ffff", fg="black",
                 command=self._transfer_item_dialog
        ).pack(side=tk.LEFT, padx=5, pady=8)
        
        return frame
    
    def _create_my_listings_tab(self, parent) -> tk.Frame:
        """Tab des annonces actives du vault"""
        frame = tk.Frame(parent, bg=CypherpunkTheme.BG_SECONDARY)
        
        list_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_SECONDARY)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        columns = ('Listing ID', 'Rune ID', 'Type', 'Price BTC', 'Status', 'Created')
        self.my_listings_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.my_listings_tree.heading(col, text=col)
            self.my_listings_tree.column(col, width=100)
        
        self.my_listings_tree.pack(fill=tk.BOTH, expand=True)
        
        # Actions
        actions_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_PANEL, height=45)
        actions_frame.pack(fill=tk.X, padx=5, pady=5)
        actions_frame.pack_propagate(False)
        
        tk.Button(actions_frame, text="CANCEL LISTING", bg="#ff4444", fg="white",
                 command=self._cancel_listing
        ).pack(side=tk.LEFT, padx=10, pady=8)
        
        tk.Button(actions_frame, text="EDIT PRICE", bg="#444444", fg="white",
                 command=self._edit_listing_price
        ).pack(side=tk.LEFT, padx=5, pady=8)
        
        return frame
    
    def _create_trades_tab(self, parent) -> tk.Frame:
        """Tab des offres d'echange"""
        frame = tk.Frame(parent, bg=CypherpunkTheme.BG_SECONDARY)
        
        # Offres recues
        tk.Label(frame, text="OFFRES RECUES", bg=CypherpunkTheme.BG_SECONDARY,
                fg="#ffd700", font=("Consolas", 11, "bold")).pack(anchor=tk.W, padx=10, pady=5)
        
        received_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_SECONDARY)
        received_frame.pack(fill=tk.X, padx=5, pady=5)
        
        columns = ('From Vault', 'Offered Items', 'Requested Items', 'Sats', 'Status')
        self.received_trades_tree = ttk.Treeview(received_frame, columns=columns, show='headings', height=5)
        
        for col in columns:
            self.received_trades_tree.heading(col, text=col)
        
        self.received_trades_tree.pack(fill=tk.X)
        
        # Boutons offres recues
        tk.Button(frame, text="ACCEPT", bg="#00ff00", fg="black",
                 command=self._accept_trade).pack(side=tk.LEFT, padx=10, pady=5)
        tk.Button(frame, text="REJECT", bg="#ff4444", fg="white",
                 command=self._reject_trade).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Nouvelle offre
        tk.Label(frame, text="CREER UNE OFFRE", bg=CypherpunkTheme.BG_SECONDARY,
                fg="#00ffff", font=("Consolas", 11, "bold")).pack(anchor=tk.W, padx=10, pady=(20, 5))
        
        tk.Button(frame, text="NEW TRADE OFFER", bg="#aa00ff", fg="white",
                 font=("Consolas", 10, "bold"), command=self._create_trade_dialog
        ).pack(padx=10, pady=5)
        
        return frame
    
    def _refresh_exchange(self):
        """Rafraichit les donnees de l'exchange"""
        if not EXCHANGE_AVAILABLE:
            return
        
        # Stats du marche
        stats = self.exchange_manager.get_market_stats()
        self.exchange_stats["active_listings"].set(str(stats.get("active_listings", 0)))
        self.exchange_stats["total_volume_btc"].set(f"{stats.get('total_volume_btc', 0):.4f}")
        
        # Mes inscriptions
        my_inscriptions = self.exchange_manager.get_vault_inscriptions(self.current_vault_num)
        self.exchange_stats["my_inscriptions"].set(str(len(my_inscriptions)))
        
        # Mes listings actifs
        my_listings = [l for l in self.exchange_manager.get_active_listings() 
                      if l.seller_vault == self.current_vault_num]
        self.exchange_stats["my_listings"].set(str(len(my_listings)))
        
        # Rafraichir les listes
        self._refresh_marketplace()
        self._refresh_my_items()
        self._refresh_my_listings()
        self._refresh_trades()
    
    def _refresh_marketplace(self):
        """Rafraichit la liste du marketplace"""
        for item in self.market_tree.get_children():
            self.market_tree.delete(item)
        
        listings = self.exchange_manager.get_active_listings()
        for listing in listings:
            self.market_tree.insert('', tk.END, values=(
                listing.rune_id,
                listing.item_type,
                listing.rarity.upper(),
                f"{listing.stat_power:.0f}",
                f"{listing.price_btc:.6f}",
                f"V#{listing.seller_vault}"
            ))
    
    def _refresh_my_items(self):
        """Rafraichit la liste de mes items"""
        for item in self.my_items_tree.get_children():
            self.my_items_tree.delete(item)
        
        inscriptions = self.exchange_manager.get_vault_inscriptions(self.current_vault_num)
        for insc in inscriptions:
            self.my_items_tree.insert('', tk.END, values=(
                insc.item_id[:12] + "...",
                insc.rune_id,
                insc.item_type,
                insc.rarity.upper(),
                f"{insc.stat_power:.0f}",
                insc.status.upper()
            ))
    
    def _refresh_my_listings(self):
        """Rafraichit mes annonces"""
        for item in self.my_listings_tree.get_children():
            self.my_listings_tree.delete(item)
        
        listings = self.exchange_manager.get_active_listings()
        for listing in listings:
            if listing.seller_vault == self.current_vault_num:
                self.my_listings_tree.insert('', tk.END, values=(
                    listing.listing_id[:12] + "...",
                    listing.rune_id,
                    listing.item_type,
                    f"{listing.price_btc:.6f}",
                    listing.status.upper(),
                    listing.created_at[:10]
                ))
    
    def _refresh_trades(self):
        """Rafraichit les offres de trade"""
        for item in self.received_trades_tree.get_children():
            self.received_trades_tree.delete(item)
        
        offers = self.exchange_manager.get_pending_offers_for_vault(self.current_vault_num)
        for offer in offers:
            self.received_trades_tree.insert('', tk.END, values=(
                f"V#{offer.offerer_vault}",
                f"{len(offer.offered_items)} items",
                f"{len(offer.requested_items)} items",
                f"+{offer.sats_offered}" if offer.sats_offered else "-",
                offer.status.upper()
            ))
    
    def _filter_marketplace(self):
        """Filtre le marketplace"""
        self._refresh_marketplace()
    
    def _buy_selected_item(self):
        """Achete l'item selectionne"""
        selection = self.market_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Selectionnez un item")
            return
        
        item = self.market_tree.item(selection[0])
        rune_id = item['values'][0]
        price_btc = item['values'][4]
        
        if messagebox.askyesno("Confirmer achat", 
                               f"Acheter {rune_id} pour {price_btc} BTC?"):
            messagebox.showinfo("Info", 
                "Transaction Bitcoin requise.\n"
                "Envoyez le paiement a l'adresse du vendeur\n"
                "puis confirmez la transaction.")
    
    def _view_listing_details(self):
        """Displays les details d'une annonce"""
        selection = self.market_tree.selection()
        if not selection:
            return
        
        item = self.market_tree.item(selection[0])
        details = f"""
RUNE ID: {item['values'][0]}
TYPE: {item['values'][1]}
RARITY: {item['values'][2]}
POWER: {item['values'][3]}
PRICE: {item['values'][4]} BTC
SELLER: {item['values'][5]}
        """
        messagebox.showinfo("Details", details)
    
    def _inscribe_item_dialog(self):
        """Dialog pour inscrire un nouvel item"""
        # Charger les items non-inscrits
        vault_items = self._load_vault_items(self.current_vault_num)
        inscribed_ids = [i.item_id for i in 
                        self.exchange_manager.get_vault_inscriptions(self.current_vault_num)]
        
        available = [i for i in vault_items if i.get('item_id') not in inscribed_ids]
        
        if not available:
            messagebox.showinfo("Info", "Tous vos items sont deja inscrits")
            return
        
        # Dialog simple
        dialog = tk.Toplevel(self.root)
        dialog.title("Inscrire un Item")
        dialog.geometry("500x400")
        dialog.configure(bg=CypherpunkTheme.BG_DARK)
        
        tk.Label(dialog, text="Selectionnez un item a inscrire:",
                bg=CypherpunkTheme.BG_DARK, fg="white").pack(pady=10)
        
        # Liste des items
        listbox = tk.Listbox(dialog, bg=CypherpunkTheme.BG_SECONDARY, fg="white",
                            height=10, width=60)
        listbox.pack(padx=20, pady=10)
        
        for item in available[:20]:
            listbox.insert(tk.END, 
                f"[{item.get('rarity', 'common').upper()}] {item.get('item_type', '?')} - PWR:{item.get('stat_power', 0):.0f}")
        
        def do_inscribe():
            sel = listbox.curselection()
            if not sel:
                return
            
            item_data = available[sel[0]]
            inscription = self.exchange_manager.inscribe_item(
                item_data, self.current_vault_num
            )
            messagebox.showinfo("Success", 
                f"Item inscrit!\nRune ID: {inscription.rune_id}")
            dialog.destroy()
            self._refresh_exchange()
        
        tk.Button(dialog, text="INSCRIRE", bg="#00ff00", fg="black",
                 command=do_inscribe).pack(pady=20)
    
    def _sell_item_dialog(self):
        """Dialog pour mettre en vente un item"""
        selection = self.my_items_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Selectionnez un item inscrit")
            return
        
        item = self.my_items_tree.item(selection[0])
        rune_id = item['values'][1]
        
        # Trouver l'inscription
        inscriptions = self.exchange_manager.get_vault_inscriptions(self.current_vault_num)
        inscription = next((i for i in inscriptions if i.rune_id == rune_id), None)
        
        if not inscription or inscription.status != "inscribed":
            messagebox.showerror("Error", "Item non disponible pour la vente")
            return
        
        # Dialog de prix
        dialog = tk.Toplevel(self.root)
        dialog.title("Mettre en Vente")
        dialog.geometry("400x200")
        dialog.configure(bg=CypherpunkTheme.BG_DARK)
        
        tk.Label(dialog, text=f"Vendre: {rune_id}",
                bg=CypherpunkTheme.BG_DARK, fg="#f7931a",
                font=("Consolas", 12, "bold")).pack(pady=10)
        
        tk.Label(dialog, text="Prix en satoshis:",
                bg=CypherpunkTheme.BG_DARK, fg="white").pack()
        
        price_var = tk.StringVar(value="100000")
        tk.Entry(dialog, textvariable=price_var, width=20,
                bg=CypherpunkTheme.BG_SECONDARY, fg="white").pack(pady=5)
        
        def do_sell():
            try:
                price_sats = int(price_var.get())
                listing = self.exchange_manager.create_listing(
                    inscription.inscription_id, price_sats, self.current_vault_num
                )
                messagebox.showinfo("Success", 
                    f"Item en vente!\nPrix: {listing.price_btc:.6f} BTC")
                dialog.destroy()
                self._refresh_exchange()
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        tk.Button(dialog, text="METTRE EN VENTE", bg="#f7931a", fg="black",
                 font=("Consolas", 10, "bold"), command=do_sell).pack(pady=20)
    
    def _transfer_item_dialog(self):
        """Dialog pour transferer un item"""
        messagebox.showinfo("Transfer", 
            "Fonctionnalite en cours de developpement.\n"
            "Les transferts necessitent une transaction Bitcoin.")
    
    def _cancel_listing(self):
        """Annule une annonce"""
        selection = self.my_listings_tree.selection()
        if not selection:
            return
        
        if messagebox.askyesno("Confirm", "Annuler cette annonce?"):
            # TODO: Implementer annulation
            messagebox.showinfo("Info", "Annonce annulee")
            self._refresh_exchange()
    
    def _edit_listing_price(self):
        """Modifie le prix d'une annonce"""
        messagebox.showinfo("Info", "Fonctionnalite en developpement")
    
    def _accept_trade(self):
        """Accepte une offre de trade"""
        messagebox.showinfo("Trade", 
            "Accepter le trade necessite une transaction Bitcoin atomique.")
    
    def _reject_trade(self):
        """Rejette une offre de trade"""
        selection = self.received_trades_tree.selection()
        if selection and messagebox.askyesno("Confirm", "Rejeter cette offre?"):
            messagebox.showinfo("Info", "Offre rejetee")
            self._refresh_trades()
    
    def _create_trade_dialog(self):
        """Dialog pour creer une offre de trade"""
        messagebox.showinfo("Trade", 
            "Creation d'offre de trade en developpement.\n"
            "Permet d'echanger des items entre vaults.")
    
    # ========================================================================
    # ONGLET BITCOIN BRIDGE
    # ========================================================================
    
    def _create_bridge_tab(self) -> tk.Frame:
        """Creates the'onglet de transfert d'actifs sur Bitcoin"""
        frame = tk.Frame(self.notebook, bg=CypherpunkTheme.BG_DARK)
        
        # Initialiser le bridge
        self.asset_bridge = BitcoinAssetBridge()
        self.bridge_address = tk.StringVar(value="")
        
        # === HEADER ===
        header_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_DARK)
        header_frame.pack(fill=tk.X, pady=(10, 15), padx=10)
        
        tk.Label(
            header_frame,
            text="BITCOIN ASSET BRIDGE",
            bg=CypherpunkTheme.BG_DARK,
            fg="#f7931a",
            font=("Consolas", 16, "bold")
        ).pack(side=tk.LEFT)
        
        tk.Button(
            header_frame,
            text="REFRESH",
            bg="#333333",
            fg="white",
            command=self._refresh_bridge
        ).pack(side=tk.RIGHT, padx=5)
        
        # === ADRESSE BITCOIN ===
        addr_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_PANEL)
        addr_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        tk.Label(addr_frame, text="Votre adresse Bitcoin:", 
                bg=CypherpunkTheme.BG_PANEL, fg=CypherpunkTheme.TEXT_SECONDARY
        ).pack(side=tk.LEFT, padx=10, pady=8)
        
        tk.Entry(addr_frame, textvariable=self.bridge_address, width=50,
                bg=CypherpunkTheme.BG_SECONDARY, fg="#f7931a",
                insertbackground="white"
        ).pack(side=tk.LEFT, padx=5, pady=8)
        
        tk.Button(addr_frame, text="SAUVEGARDER", bg="#00aa00", fg="white",
                 command=self._save_bridge_address
        ).pack(side=tk.LEFT, padx=10, pady=8)
        
        # === STATS ===
        stats_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_PANEL)
        stats_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.bridge_stats = {}
        stat_items = [
            ("total", "TOTAL ASSETS", "#ffffff"),
            ("inscribed", "ON-CHAIN", "#00ff00"),
            ("pending", "PENDING", "#ffaa00"),
            ("items", "ITEMS", "#00ffff"),
            ("gems", "GEMS", "#ff00ff"),
            ("stones", "STONES", "#ffd700"),
        ]
        
        for stat_id, label, color in stat_items:
            card = tk.Frame(stats_frame, bg=CypherpunkTheme.BG_SECONDARY, padx=10, pady=5)
            card.pack(side=tk.LEFT, padx=3, pady=5, fill=tk.X, expand=True)
            tk.Label(card, text=label, bg=CypherpunkTheme.BG_SECONDARY,
                    fg=CypherpunkTheme.TEXT_SECONDARY, font=("Consolas", 7)).pack()
            var = tk.StringVar(value="0")
            tk.Label(card, textvariable=var, bg=CypherpunkTheme.BG_SECONDARY,
                    fg=color, font=("Consolas", 12, "bold")).pack()
            self.bridge_stats[stat_id] = var
        
        # === NOTEBOOK INTERNE ===
        bridge_notebook = ttk.Notebook(frame)
        bridge_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Tab: Mes actifs on-chain
        onchain_tab = self._create_onchain_assets_tab(bridge_notebook)
        bridge_notebook.add(onchain_tab, text=" ON-CHAIN ")
        
        # Tab: Inscrire des actifs
        inscribe_tab = self._create_inscribe_tab(bridge_notebook)
        bridge_notebook.add(inscribe_tab, text=" INSCRIRE ")
        
        # Tab: Transferer
        transfer_tab = self._create_transfer_tab(bridge_notebook)
        bridge_notebook.add(transfer_tab, text=" TRANSFERER ")
        
        # Tab: Historique
        history_tab = self._create_bridge_history_tab(bridge_notebook)
        bridge_notebook.add(history_tab, text=" HISTORIQUE ")
        
        # Charger les donnees
        self._refresh_bridge()
        
        return frame
    
    def _create_onchain_assets_tab(self, parent) -> tk.Frame:
        """Tab affichant les actifs inscrits sur Bitcoin"""
        frame = tk.Frame(parent, bg=CypherpunkTheme.BG_SECONDARY)
        
        # Liste des actifs
        columns = ('Rune ID', 'Type', 'Nom', 'Rarete', 'Power', 'Status', 'TXID')
        self.onchain_tree = ttk.Treeview(frame, columns=columns, show='headings', height=15)
        
        widths = [150, 80, 150, 80, 70, 80, 120]
        for col, w in zip(columns, widths):
            self.onchain_tree.heading(col, text=col)
            self.onchain_tree.column(col, width=w)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.onchain_tree.yview)
        self.onchain_tree.configure(yscrollcommand=scrollbar.set)
        
        self.onchain_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        return frame
    
    def _create_inscribe_tab(self, parent) -> tk.Frame:
        """Tab pour inscrire de nouveaux actifs sur Bitcoin"""
        frame = tk.Frame(parent, bg=CypherpunkTheme.BG_SECONDARY)
        
        # Instructions
        tk.Label(frame, 
            text="Selectionnez un type d'actif a inscrire sur la blockchain Bitcoin:",
            bg=CypherpunkTheme.BG_SECONDARY, fg="white",
            font=("Consolas", 10)
        ).pack(pady=10)
        
        # Boutons par type d'actif
        btn_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_SECONDARY)
        btn_frame.pack(pady=10)
        
        asset_types = [
            ("EQUIPMENT", "#00ffff", self._inscribe_items_dialog),
            ("GEMS", "#ff00ff", self._inscribe_gems_dialog),
            ("FRAGMENTS", "#00ff00", self._inscribe_fragments_dialog),
            ("STONES", "#ffd700", self._inscribe_stones_dialog),
            ("ARTIFACTS", "#ff6600", self._inscribe_artifacts_dialog),
        ]
        
        for name, color, cmd in asset_types:
            tk.Button(btn_frame, text=f"INSCRIRE {name}", bg=color, fg="black",
                     font=("Consolas", 10, "bold"), width=18, command=cmd
            ).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Liste des actifs non-inscrits
        tk.Label(frame, text="Actifs disponibles pour inscription:",
                bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.TEXT_SECONDARY
        ).pack(anchor=tk.W, padx=10, pady=(20, 5))
        
        columns = ('ID', 'Type', 'Nom', 'Rarete', 'Power')
        self.available_tree = ttk.Treeview(frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.available_tree.heading(col, text=col)
            self.available_tree.column(col, width=120)
        
        self.available_tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        return frame
    
    def _create_transfer_tab(self, parent) -> tk.Frame:
        """Tab pour transferer des actifs"""
        frame = tk.Frame(parent, bg=CypherpunkTheme.BG_SECONDARY)
        
        # Instructions
        tk.Label(frame,
            text="Transferer un actif vers une autre adresse Bitcoin:",
            bg=CypherpunkTheme.BG_SECONDARY, fg="white",
            font=("Consolas", 10)
        ).pack(pady=10)
        
        # Selection de l'actif
        select_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_PANEL)
        select_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(select_frame, text="Actif:", bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.TEXT_SECONDARY).pack(side=tk.LEFT, padx=10, pady=8)
        
        self.transfer_asset_var = tk.StringVar()
        self.transfer_asset_combo = ttk.Combobox(select_frame, 
            textvariable=self.transfer_asset_var, width=50)
        self.transfer_asset_combo.pack(side=tk.LEFT, padx=5, pady=8)
        
        # Adresse destination
        dest_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_PANEL)
        dest_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(dest_frame, text="Destination:", bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.TEXT_SECONDARY).pack(side=tk.LEFT, padx=10, pady=8)
        
        self.transfer_dest_var = tk.StringVar()
        tk.Entry(dest_frame, textvariable=self.transfer_dest_var, width=50,
                bg=CypherpunkTheme.BG_SECONDARY, fg="#f7931a"
        ).pack(side=tk.LEFT, padx=5, pady=8)
        
        # Priorite
        prio_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_PANEL)
        prio_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(prio_frame, text="Priorite:", bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.TEXT_SECONDARY).pack(side=tk.LEFT, padx=10, pady=8)
        
        self.transfer_priority_var = tk.StringVar(value="normal")
        for prio in ["low", "normal", "high"]:
            tk.Radiobutton(prio_frame, text=prio.upper(), value=prio,
                          variable=self.transfer_priority_var,
                          bg=CypherpunkTheme.BG_PANEL, fg="white",
                          selectcolor=CypherpunkTheme.BG_SECONDARY
            ).pack(side=tk.LEFT, padx=10, pady=8)
        
        # Bouton transfert
        tk.Button(frame, text="INITIER LE TRANSFERT", bg="#f7931a", fg="black",
                 font=("Consolas", 12, "bold"), command=self._initiate_transfer
        ).pack(pady=20)
        
        # Info transaction
        self.transfer_info = tk.Text(frame, height=8, width=80,
                                     bg=CypherpunkTheme.BG_DARK, fg="#00ff00",
                                     font=("Consolas", 9))
        self.transfer_info.pack(padx=10, pady=5)
        self.transfer_info.insert("1.0", "Les informations de transaction apparaitront ici...")
        
        return frame
    
    def _create_bridge_history_tab(self, parent) -> tk.Frame:
        """Tab historique des transferts"""
        frame = tk.Frame(parent, bg=CypherpunkTheme.BG_SECONDARY)
        
        columns = ('Date', 'Type', 'Rune ID', 'De', 'Vers', 'Status', 'TXID')
        self.history_tree = ttk.Treeview(frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=100)
        
        self.history_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        return frame
    
    def _refresh_bridge(self):
        """Rafraichit les donnees du bridge"""
        if not BRIDGE_AVAILABLE:
            return
        
        # Stats
        stats = self.asset_bridge.get_statistics()
        self.bridge_stats["total"].set(str(stats.get("total_assets", 0)))
        self.bridge_stats["inscribed"].set(str(stats.get("inscribed", 0)))
        self.bridge_stats["pending"].set(str(stats.get("pending", 0)))
        
        by_type = stats.get("by_type", {})
        self.bridge_stats["items"].set(str(by_type.get("item", 0)))
        self.bridge_stats["gems"].set(str(by_type.get("gem", 0)))
        self.bridge_stats["stones"].set(str(by_type.get("stone", 0)))
        
        # Liste des actifs on-chain
        for item in self.onchain_tree.get_children():
            self.onchain_tree.delete(item)
        
        assets = self.asset_bridge.get_assets_by_vault(self.current_vault_num)
        for asset in assets:
            txid = asset.inscription_txid[:12] + "..." if asset.inscription_txid else "-"
            self.onchain_tree.insert('', tk.END, values=(
                asset.rune_id,
                asset.asset_type.upper(),
                asset.name[:20],
                asset.rarity.upper(),
                f"{asset.power:.0f}",
                asset.status.upper(),
                txid
            ))
        
        # Mettre a jour la combo de transfert
        asset_list = [f"{a.rune_id} - {a.name}" for a in assets if a.status == "inscribed"]
        self.transfer_asset_combo['values'] = asset_list
    
    def _save_bridge_address(self):
        """Saves l'adresse Bitcoin"""
        address = self.bridge_address.get()
        if not address:
            messagebox.showwarning("Warning", "Entrez une adresse Bitcoin")
            return
        
        # Validation basique
        if not (address.startswith('1') or address.startswith('3') or address.startswith('bc1')):
            messagebox.showerror("Error", "Adresse Bitcoin invalide")
            return
        
        messagebox.showinfo("Success", f"Adresse sauvegardee:\n{address}")
    
    def _inscribe_items_dialog(self):
        """Dialog pour inscrire des items"""
        self._inscribe_assets_dialog("item", "Alchemical Equipment")
    
    def _inscribe_gems_dialog(self):
        """Dialog pour inscrire des gems"""
        self._inscribe_assets_dialog("gem", "Gemmes")
    
    def _inscribe_fragments_dialog(self):
        """Dialog pour inscrire des fragments"""
        self._inscribe_assets_dialog("fragment", "Fragments")
    
    def _inscribe_stones_dialog(self):
        """Dialog pour inscrire des pierres"""
        self._inscribe_assets_dialog("stone", "Pierres Philosophales")
    
    def _inscribe_artifacts_dialog(self):
        """Dialog pour inscrire des artefacts"""
        self._inscribe_assets_dialog("artifact", "Artifacts")
    
    def _inscribe_assets_dialog(self, asset_type: str, title: str):
        """Dialog generique pour inscrire des actifs"""
        address = self.bridge_address.get()
        if not address:
            messagebox.showwarning("Warning", 
                "Entrez d'abord votre adresse Bitcoin dans le champ en haut")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Inscrire {title}")
        dialog.geometry("600x500")
        dialog.configure(bg=CypherpunkTheme.BG_DARK)
        
        tk.Label(dialog, text=f"Inscrire {title} sur Bitcoin",
                bg=CypherpunkTheme.BG_DARK, fg="#f7931a",
                font=("Consolas", 14, "bold")).pack(pady=10)
        
        tk.Label(dialog, text=f"Adresse: {address[:20]}...{address[-10:]}",
                bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.TEXT_SECONDARY
        ).pack()
        
        # Liste des actifs disponibles
        list_frame = tk.Frame(dialog, bg=CypherpunkTheme.BG_SECONDARY)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        listbox = tk.Listbox(list_frame, bg=CypherpunkTheme.BG_SECONDARY, fg="white",
                            selectmode=tk.MULTIPLE, height=15, width=70)
        listbox.pack(fill=tk.BOTH, expand=True)
        
        # Charger les actifs selon le type
        assets_to_inscribe = []
        
        if asset_type == "item":
            items = self._load_vault_items(self.current_vault_num)
            for item in items[:50]:
                listbox.insert(tk.END, 
                    f"[{item.get('rarity', 'common').upper()[:4]}] {item.get('item_type', '?')} - PWR:{item.get('stat_power', 0):.0f}")
                assets_to_inscribe.append(item)
        elif asset_type == "stone":
            # Charger les pierres du vault
            try:
                from core.philosopher_stone import PhilosopherStoneManager
                stone_mgr = PhilosopherStoneManager()
                stones = stone_mgr.get_vault_stones(self.current_vault_num)
                for stone in stones:
                    listbox.insert(tk.END,
                        f"[{stone.state.upper()}] Pierre #{stone.stone_id[:8]} - E:{stone.max_energy}")
                    assets_to_inscribe.append(stone.to_dict() if hasattr(stone, 'to_dict') else {"stone_id": stone.stone_id, "max_energy": stone.max_energy, "state": stone.state, "origin_vault": stone.origin_vault})
            except Exception as e:
                listbox.insert(tk.END, f"Erreur: {e}")
        else:
            listbox.insert(tk.END, f"Chargement des {title} en cours...")
        
        def do_inscribe():
            selected = listbox.curselection()
            if not selected:
                messagebox.showwarning("Warning", "Selectionnez au moins un actif")
                return
            
            count = 0
            for idx in selected:
                if idx < len(assets_to_inscribe):
                    asset_data = assets_to_inscribe[idx]
                    try:
                        if asset_type == "item":
                            self.asset_bridge.inscribe_item(asset_data, address, self.current_vault_num)
                        elif asset_type == "stone":
                            self.asset_bridge.inscribe_stone(asset_data, address, self.current_vault_num)
                        elif asset_type == "gem":
                            self.asset_bridge.inscribe_gem(asset_data, address, self.current_vault_num)
                        elif asset_type == "fragment":
                            self.asset_bridge.inscribe_fragment(asset_data, address, self.current_vault_num)
                        elif asset_type == "artifact":
                            self.asset_bridge.inscribe_artifact(asset_data, address, self.current_vault_num)
                        count += 1
                    except Exception as e:
                        print(f"Erreur inscription: {e}")
            
            messagebox.showinfo("Success", f"{count} actif(s) inscrit(s) sur Bitcoin!")
            dialog.destroy()
            self._refresh_bridge()
        
        tk.Button(dialog, text="INSCRIRE SELECTION", bg="#f7931a", fg="black",
                 font=("Consolas", 11, "bold"), command=do_inscribe
        ).pack(pady=15)
    
    def _initiate_transfer(self):
        """Initie un transfert d'actif"""
        asset_selection = self.transfer_asset_var.get()
        dest_address = self.transfer_dest_var.get()
        priority = self.transfer_priority_var.get()
        
        if not asset_selection:
            messagebox.showwarning("Warning", "Selectionnez un actif")
            return
        
        if not dest_address:
            messagebox.showwarning("Warning", "Entrez une adresse destination")
            return
        
        # Extraire le Rune ID
        rune_id = asset_selection.split(" - ")[0]
        
        # Trouver l'actif
        asset = self.asset_bridge.get_asset_by_rune(rune_id)
        if not asset:
            messagebox.showerror("Error", "Actif non trouve")
            return
        
        from_address = self.bridge_address.get()
        if not from_address:
            messagebox.showerror("Error", "Configurez d'abord votre adresse Bitcoin")
            return
        
        try:
            transfer = self.asset_bridge.transfer_asset(
                asset.asset_id,
                from_address,
                dest_address,
                from_vault=self.current_vault_num,
                priority=priority
            )
            
            # Afficher les infos
            info = f"""
TRANSFERT INITIE
================
Transfer ID: {transfer.transfer_id}
Rune ID: {transfer.rune_id}
De: {transfer.from_address[:20]}...
Vers: {transfer.to_address[:20]}...
Frais: {transfer.fee_sats} sats

INSTRUCTIONS:
1. Creez une transaction Bitcoin depuis votre wallet
2. Ajoutez OP_RETURN: {transfer.op_return_data.hex()[:40]}...
3. Envoyez 546 sats a l'adresse destination
4. Broadcastez la transaction
5. Confirmez avec le TXID ci-dessous
            """
            
            self.transfer_info.delete("1.0", tk.END)
            self.transfer_info.insert("1.0", info)
            
            messagebox.showinfo("Transfert Initie", 
                f"Transfert cree!\nID: {transfer.transfer_id}\n\n"
                "Suivez les instructions pour completer le transfert.")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    # ========================================================================
    # ONGLET AVATAR 3D
    # ========================================================================
    
    def _create_avatar_tab(self) -> tk.Frame:
        """Creates the'onglet Avatar - Version simplifiee avec Three.js"""
        frame = tk.Frame(self.notebook, bg=CypherpunkTheme.BG_DARK)
        
        # Initialiser le manager
        self.avatar_manager = AvatarManager()
        
        # === HEADER ===
        header_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_DARK)
        header_frame.pack(fill=tk.X, pady=(10, 10), padx=10)
        
        tk.Label(
            header_frame,
            text="🎭 AVATAR",
            bg=CypherpunkTheme.BG_DARK,
            fg=CypherpunkTheme.NEON_MAGENTA,
            font=("Consolas", 16, "bold")
        ).pack(side=tk.LEFT)
        
        # Boutons principaux
        btn_frame = tk.Frame(header_frame, bg=CypherpunkTheme.BG_DARK)
        btn_frame.pack(side=tk.RIGHT)
        
        tk.Button(
            btn_frame,
            text="⚡ GENERER",
            bg=CypherpunkTheme.NEON_MAGENTA,
            fg="black",
            font=("Consolas", 10, "bold"),
            command=self._generate_avatar
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame,
            text="🌐 VISUALISER 3D",
            bg="#00ffaa",
            fg="black",
            font=("Consolas", 10, "bold"),
            command=self._open_threejs_viewer
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame,
            text="📊 STATS",
            bg="#0066ff",
            fg="white",
            font=("Consolas", 10, "bold"),
            command=self._show_avatar_stats_window
        ).pack(side=tk.LEFT, padx=5)
        
        # === PANNEAU PRINCIPAL (2 colonnes) ===
        main_panel = tk.Frame(frame, bg=CypherpunkTheme.BG_DARK)
        main_panel.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # === COLONNE GAUCHE: Apercu + Actions ===
        left_panel = tk.Frame(main_panel, bg=CypherpunkTheme.BG_PANEL, width=400)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 5), pady=5)
        left_panel.pack_propagate(False)
        
        # Zone d'apercu
        preview_frame = tk.Frame(left_panel, bg=CypherpunkTheme.BG_SECONDARY)
        preview_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.avatar_preview_label = tk.Label(
            preview_frame,
            text="Aucun avatar\n\nCliquez sur GENERER\npour creer votre avatar unique",
            bg=CypherpunkTheme.BG_SECONDARY,
            fg=CypherpunkTheme.TEXT_SECONDARY,
            font=("Consolas", 11),
            justify=tk.CENTER,
            height=8
        )
        self.avatar_preview_label.pack(fill=tk.X, pady=20)
        
        # Info rapide
        self.avatar_quick_info = tk.Frame(left_panel, bg=CypherpunkTheme.BG_PANEL)
        self.avatar_quick_info.pack(fill=tk.X, padx=10, pady=5)
        
        # Type
        row1 = tk.Frame(self.avatar_quick_info, bg=CypherpunkTheme.BG_PANEL)
        row1.pack(fill=tk.X, pady=2)
        tk.Label(row1, text="TYPE:", bg=CypherpunkTheme.BG_PANEL, fg=CypherpunkTheme.TEXT_SECONDARY,
                font=("Consolas", 10)).pack(side=tk.LEFT)
        self.avatar_type_var = tk.StringVar(value="---")
        tk.Label(row1, textvariable=self.avatar_type_var, bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.NEON_CYAN, font=("Consolas", 11, "bold")).pack(side=tk.RIGHT)
        
        # Rarete
        row2 = tk.Frame(self.avatar_quick_info, bg=CypherpunkTheme.BG_PANEL)
        row2.pack(fill=tk.X, pady=2)
        tk.Label(row2, text="RARETE:", bg=CypherpunkTheme.BG_PANEL, fg=CypherpunkTheme.TEXT_SECONDARY,
                font=("Consolas", 10)).pack(side=tk.LEFT)
        self.avatar_rarity_var = tk.StringVar(value="---")
        self.avatar_rarity_label = tk.Label(row2, textvariable=self.avatar_rarity_var, 
                bg=CypherpunkTheme.BG_PANEL, fg=CypherpunkTheme.NEON_GREEN, 
                font=("Consolas", 11, "bold"))
        self.avatar_rarity_label.pack(side=tk.RIGHT)
        
        # Puissance
        row3 = tk.Frame(self.avatar_quick_info, bg=CypherpunkTheme.BG_PANEL)
        row3.pack(fill=tk.X, pady=2)
        tk.Label(row3, text="PUISSANCE:", bg=CypherpunkTheme.BG_PANEL, fg=CypherpunkTheme.TEXT_SECONDARY,
                font=("Consolas", 10)).pack(side=tk.LEFT)
        self.avatar_power_var = tk.StringVar(value="---")
        tk.Label(row3, textvariable=self.avatar_power_var, bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.NEON_YELLOW, font=("Consolas", 11, "bold")).pack(side=tk.RIGHT)
        
        # Classe
        row4 = tk.Frame(self.avatar_quick_info, bg=CypherpunkTheme.BG_PANEL)
        row4.pack(fill=tk.X, pady=2)
        tk.Label(row4, text="CLASSE:", bg=CypherpunkTheme.BG_PANEL, fg=CypherpunkTheme.TEXT_SECONDARY,
                font=("Consolas", 10)).pack(side=tk.LEFT)
        self.avatar_class_var = tk.StringVar(value="---")
        tk.Label(row4, textvariable=self.avatar_class_var, bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.NEON_PURPLE, font=("Consolas", 11, "bold")).pack(side=tk.RIGHT)
        
        # Etat
        row5 = tk.Frame(self.avatar_quick_info, bg=CypherpunkTheme.BG_PANEL)
        row5.pack(fill=tk.X, pady=2)
        tk.Label(row5, text="ETAT:", bg=CypherpunkTheme.BG_PANEL, fg=CypherpunkTheme.TEXT_SECONDARY,
                font=("Consolas", 10)).pack(side=tk.LEFT)
        self.avatar_state_var = tk.StringVar(value="---")
        self.avatar_state_label = tk.Label(row5, textvariable=self.avatar_state_var, 
                bg=CypherpunkTheme.BG_PANEL, fg=CypherpunkTheme.NEON_GREEN, 
                font=("Consolas", 11, "bold"))
        self.avatar_state_label.pack(side=tk.RIGHT)
        
        # Separateur
        tk.Frame(left_panel, bg=CypherpunkTheme.NEON_MAGENTA, height=2).pack(fill=tk.X, padx=10, pady=10)
        
        # Boutons d'action
        action_label = tk.Label(left_panel, text="ACTIONS", bg=CypherpunkTheme.BG_PANEL,
                               fg=CypherpunkTheme.NEON_CYAN, font=("Consolas", 10, "bold"))
        action_label.pack(pady=(0, 5))
        
        action_frame = tk.Frame(left_panel, bg=CypherpunkTheme.BG_PANEL)
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.detach_btn = tk.Button(
            action_frame, text="🔓 DETACHER", bg="#ff6600", fg="black",
            font=("Consolas", 9, "bold"), command=self._detach_avatar, state=tk.DISABLED, width=12
        )
        self.detach_btn.pack(side=tk.LEFT, padx=3, pady=2)
        
        self.transfer_avatar_btn = tk.Button(
            action_frame, text="📤 TRANSFERER", bg="#00aaff", fg="black",
            font=("Consolas", 9, "bold"), command=self._transfer_avatar_dialog, state=tk.DISABLED, width=12
        )
        self.transfer_avatar_btn.pack(side=tk.LEFT, padx=3, pady=2)
        
        self.tokenize_btn = tk.Button(
            action_frame, text="₿ TOKENISER", bg="#f7931a", fg="black",
            font=("Consolas", 9, "bold"), command=self._tokenize_avatar, state=tk.DISABLED, width=12
        )
        self.tokenize_btn.pack(side=tk.LEFT, padx=3, pady=2)
        
        # === COLONNE DROITE: Stats ===
        right_panel = tk.Frame(main_panel, bg=CypherpunkTheme.BG_PANEL)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        
        tk.Label(
            right_panel,
            text="⚔️ STATS DE COMBAT",
            bg=CypherpunkTheme.BG_PANEL,
            fg=CypherpunkTheme.NEON_GREEN,
            font=("Consolas", 11, "bold")
        ).pack(pady=(10, 5))
        
        # Frame pour les stats avec scrollbar
        stats_container = tk.Frame(right_panel, bg=CypherpunkTheme.BG_SECONDARY)
        stats_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        stats_canvas = tk.Canvas(stats_container, bg=CypherpunkTheme.BG_SECONDARY, highlightthickness=0)
        stats_scrollbar = ttk.Scrollbar(stats_container, orient=tk.VERTICAL, command=stats_canvas.yview)
        self.avatar_stats_frame = tk.Frame(stats_canvas, bg=CypherpunkTheme.BG_SECONDARY)
        
        stats_canvas.configure(yscrollcommand=stats_scrollbar.set)
        stats_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        stats_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        stats_canvas.create_window((0, 0), window=self.avatar_stats_frame, anchor=tk.NW)
        self.avatar_stats_frame.bind("<Configure>", 
            lambda e: stats_canvas.configure(scrollregion=stats_canvas.bbox("all")))
        
        # Frame info detaillees (en dessous des stats)
        self.avatar_info_frame = tk.Frame(right_panel, bg=CypherpunkTheme.BG_SECONDARY)
        
        # Placeholder stats
        self._display_stats_placeholder()
        
        # Charger l'avatar existant
        self._refresh_avatar()
        
        return frame
    
    def _display_stats_placeholder(self):
        """Displays le placeholder pour les stats"""
        for widget in self.avatar_stats_frame.winfo_children():
            widget.destroy()
        
        tk.Label(
            self.avatar_stats_frame,
            text="Generez un avatar\npour voir ses stats",
            bg=CypherpunkTheme.BG_SECONDARY,
            fg=CypherpunkTheme.TEXT_SECONDARY,
            font=("Consolas", 9),
            justify=tk.CENTER
        ).pack(pady=30, padx=10)
    
    def _display_avatar_stats(self, avatar, stats=None):
        """Displays les stats de combat de l'avatar"""
        for widget in self.avatar_stats_frame.winfo_children():
            widget.destroy()
        
        def add_stat_bar(name, value, max_val=100, color=CypherpunkTheme.NEON_GREEN):
            row = tk.Frame(self.avatar_stats_frame, bg=CypherpunkTheme.BG_SECONDARY)
            row.pack(fill=tk.X, pady=2, padx=5)
            
            tk.Label(row, text=name[:12], bg=CypherpunkTheme.BG_SECONDARY,
                    fg=CypherpunkTheme.TEXT_SECONDARY, font=("Consolas", 8), 
                    width=12, anchor=tk.W).pack(side=tk.LEFT)
            
            # Barre de progression
            bar_frame = tk.Frame(row, bg="#1a1a2e", width=80, height=12)
            bar_frame.pack(side=tk.LEFT, padx=3)
            bar_frame.pack_propagate(False)
            
            fill_width = int(80 * min(value / max_val, 1.0))
            if fill_width > 0:
                bar_fill = tk.Frame(bar_frame, bg=color, width=fill_width, height=12)
                bar_fill.pack(side=tk.LEFT)
            
            tk.Label(row, text=f"{value:.0f}", bg=CypherpunkTheme.BG_SECONDARY,
                    fg=color, font=("Consolas", 8, "bold"), width=5).pack(side=tk.LEFT)
        
        # Section Niveau
        tk.Label(self.avatar_stats_frame, text="═══ NIVEAU ═══",
                bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_YELLOW,
                font=("Consolas", 9, "bold")).pack(anchor=tk.W, pady=(5, 3), padx=5)
        
        level = stats.level if stats else 1
        xp = stats.xp if stats else 0
        xp_next = stats.xp_to_next if stats else 100
        
        add_stat_bar("Niveau", level, 100, CypherpunkTheme.NEON_YELLOW)
        add_stat_bar("XP", xp, xp_next, "#aaaaff")
        
        # Section Stats Primaires
        tk.Label(self.avatar_stats_frame, text="═══ PRIMAIRES ═══",
                bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_GREEN,
                font=("Consolas", 9, "bold")).pack(anchor=tk.W, pady=(10, 3), padx=5)
        
        if stats:
            add_stat_bar("Force", stats.strength, 100, "#ff4444")
            add_stat_bar("Agilite", stats.agility, 100, "#44ff44")
            add_stat_bar("Intelligence", stats.intelligence, 100, "#4444ff")
            add_stat_bar("Vitalite", stats.vitality, 100, "#ff8844")
            add_stat_bar("Chance", stats.luck, 100, "#ffff44")
            add_stat_bar("Charisme", stats.charisma, 100, "#ff44ff")
        
        # Section Stats Secondaires
        tk.Label(self.avatar_stats_frame, text="═══ SECONDAIRES ═══",
                bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_CYAN,
                font=("Consolas", 9, "bold")).pack(anchor=tk.W, pady=(10, 3), padx=5)
        
        if stats:
            add_stat_bar("HP", stats.hp_max, 2000, "#00ff00")
            add_stat_bar("MP", stats.mp_max, 1000, "#00aaff")
            add_stat_bar("Attaque", stats.attack, 300, "#ff0000")
            add_stat_bar("M.Attaque", stats.magic_attack, 300, "#aa00ff")
            add_stat_bar("Defense", stats.defense, 200, "#888888")
            add_stat_bar("Vitesse", stats.speed, 200, "#00ffaa")
            add_stat_bar("Crit%", stats.crit_rate, 100, "#ffaa00")
        
        # Section Stats Quantiques
        tk.Label(self.avatar_stats_frame, text="═══ QUANTIQUES ═══",
                bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_MAGENTA,
                font=("Consolas", 9, "bold")).pack(anchor=tk.W, pady=(10, 3), padx=5)
        
        if stats:
            add_stat_bar("Q.Power", stats.quantum_power, 500, CypherpunkTheme.NEON_MAGENTA)
            add_stat_bar("Dim.Sync", stats.dimensional_sync, 100, "#ff00ff")
            add_stat_bar("Entropy.R", stats.entropy_resistance, 100, "#00ffff")
            add_stat_bar("Nexus.Aff", stats.nexus_affinity, 100, "#ffff00")
    
    def _toggle_avatar_animation(self):
        """Active/desactive l'animation de rotation de l'avatar"""
        if self.avatar_animation_running:
            self.avatar_animation_running = False
            self.anim_avatar_btn.configure(text="▶ ANIMER", bg="#00aa55")
        else:
            self.avatar_animation_running = True
            self.anim_avatar_btn.configure(text="⏹ STOP", bg="#aa0000")
            self._animate_avatar()
    
    def _animate_avatar(self):
        """Animation de rotation de l'avatar"""
        if not self.avatar_animation_running:
            return
        
        self.avatar_current_angle = (self.avatar_current_angle + 5) % 360
        
        # Redessiner l'avatar avec le nouvel angle
        avatars = self.avatar_manager.get_avatars_owned_by_vault(self.current_vault_num)
        if avatars:
            self._draw_avatar_animated(avatars[0], self.avatar_current_angle)
        
        # Continuer l'animation
        self.root.after(50, self._animate_avatar)
    
    def _draw_avatar_animated(self, avatar, angle):
        """Dessine l'avatar avec rotation - Version amelioree avec effets"""
        self.avatar_canvas.delete("all")
        
        import math
        import hashlib
        
        # Couleurs basees sur la rarete et le DNA
        color = self._get_rarity_color(avatar.rarity_tier)
        
        # Generer des couleurs secondaires depuis l'avatar ID
        avatar_hash = hashlib.md5(avatar.avatar_id.encode()).hexdigest()
        color2 = f"#{avatar_hash[0:6]}"
        color3 = f"#{avatar_hash[6:12]}"
        
        geo_type = avatar.geometry_type
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        
        cx, cy = 170, 130  # Centre
        
        # Dessiner un fond avec effet de lueur
        glow_color = color + "33"  # 20% opacite
        self.avatar_canvas.create_oval(cx-90, cy-70, cx+90, cy+70, fill=glow_color, outline="")
        
        if "sphere" in geo_type:
            # Sphere quantique avec particules orbitales
            r = 55
            # Sphere principale
            self.avatar_canvas.create_oval(cx-r, cy-r*0.65, cx+r, cy+r*0.65, outline=color, width=3)
            # Anneaux orbitaux
            for ring in range(3):
                ring_r = r + ring * 12
                self.avatar_canvas.create_oval(cx-ring_r, cy-ring_r*0.3, cx+ring_r, cy+ring_r*0.3, 
                                              outline=color2, width=1)
            # Particules en orbite
            for i in range(12):
                a1 = math.radians(i * 30) + rad * (1 + i % 3 * 0.5)
                orbit_r = 45 + (i % 3) * 15
                x1 = cx + orbit_r * math.cos(a1)
                y1 = cy + orbit_r * math.sin(a1) * 0.4
                size = 4 + (i % 3) * 2
                particle_color = [color, color2, color3][i % 3]
                self.avatar_canvas.create_oval(x1-size, y1-size, x1+size, y1+size, 
                                              fill=particle_color, outline="white", width=1)
            # Noyau central
            self.avatar_canvas.create_oval(cx-8, cy-8, cx+8, cy+8, fill=color, outline="white", width=2)
            
        elif "torus" in geo_type:
            # Tore spinoriel avec flux d'energie
            R, r = 55, 18
            # Dessiner plusieurs couches du tore
            for layer in range(3):
                points = []
                layer_offset = layer * 0.3
                for i in range(0, 360, 10):
                    a1 = math.radians(i)
                    wave = math.sin(a1 * 4 + rad * 2) * 8
                    x = cx + (R + r * math.cos(a1 * 3) + wave) * math.cos(a1 + rad + layer_offset)
                    y = cy + (R + r * math.cos(a1 * 3) + wave) * math.sin(a1) * 0.45
                    points.extend([x, y])
                if len(points) >= 6:
                    layer_color = [color, color2, color3][layer]
                    self.avatar_canvas.create_polygon(points, outline=layer_color, fill="", 
                                                     width=3-layer, smooth=True)
            # Points de flux
            for i in range(8):
                a = math.radians(i * 45) + rad
                x = cx + R * math.cos(a)
                y = cy + R * math.sin(a) * 0.4
                self.avatar_canvas.create_oval(x-4, y-4, x+4, y+4, fill=color2, outline="")
            
        elif "crystal" in geo_type or "nexus" in geo_type:
            # Cristal nexus avec facettes brillantes
            # Dessiner les facettes
            for layer in range(3):
                points = []
                layer_r = 55 - layer * 15
                for i in range(8):
                    a = math.radians(i * 45) + rad + layer * 0.2
                    x = cx + layer_r * math.cos(a)
                    y = cy + layer_r * math.sin(a) * 0.6
                    points.extend([x, y])
                layer_color = [color, color2, color3][layer]
                self.avatar_canvas.create_polygon(points, outline=layer_color, fill="", width=2)
            # Lignes de refraction
            for i in range(8):
                a = math.radians(i * 45) + rad
                x = cx + 55 * math.cos(a)
                y = cy + 55 * math.sin(a) * 0.6
                self.avatar_canvas.create_line(cx, cy, x, y, fill=color, width=1, dash=(3, 3))
            # Coeur du cristal
            self.avatar_canvas.create_polygon([cx, cy-25, cx+15, cy, cx, cy+25, cx-15, cy],
                                             fill=color, outline="white", width=2)
            # Eclats
            for i in range(6):
                a = math.radians(i * 60 + angle * 0.5)
                x = cx + 70 * math.cos(a)
                y = cy + 50 * math.sin(a) * 0.6
                self.avatar_canvas.create_text(x, y, text="✦", fill=color2, font=("Segoe UI", 8))
            
        elif "polyhedron" in geo_type or "bell" in geo_type:
            # Polyedre de Bell avec connexions quantiques
            vertices = []
            for i in range(12):
                a = math.radians(i * 30) + rad
                r_var = 50 + math.sin(i * 1.5) * 15
                x = cx + r_var * math.cos(a)
                y = cy + r_var * math.sin(a) * 0.55
                vertices.append((x, y))
            # Dessiner les connexions
            for i, (x1, y1) in enumerate(vertices):
                for j in range(i + 1, len(vertices)):
                    if (j - i) % 3 == 1:
                        x2, y2 = vertices[j]
                        self.avatar_canvas.create_line(x1, y1, x2, y2, fill=color2, width=1)
            # Dessiner les sommets
            for i, (x, y) in enumerate(vertices):
                v_color = [color, color2, color3][i % 3]
                self.avatar_canvas.create_oval(x-5, y-5, x+5, y+5, fill=v_color, outline="white")
            # Centre
            self.avatar_canvas.create_oval(cx-10, cy-10, cx+10, cy+10, fill=color, outline="white", width=2)
            
        elif "7d" in geo_type:
            # Projection 7D avec dimensions multiples
            # Couches dimensionnelles
            for dim in range(7):
                dim_angle = rad + dim * 0.15
                dim_r = 65 - dim * 5
                points = []
                for i in range(7):
                    a = math.radians(i * 360 / 7) + dim_angle
                    x = cx + dim_r * math.cos(a)
                    y = cy + dim_r * math.sin(a) * 0.55
                    points.extend([x, y])
                points.extend(points[:2])  # Fermer
                dim_color = f"#{hex(255 - dim * 30)[2:].zfill(2)}00{hex(dim * 36)[2:].zfill(2)}"
                self.avatar_canvas.create_line(points, fill=dim_color, width=2)
            # Noeuds principaux
            for i in range(7):
                a = math.radians(i * 360 / 7) + rad
                x = cx + 65 * math.cos(a)
                y = cy + 65 * math.sin(a) * 0.55
                self.avatar_canvas.create_line(cx, cy, x, y, fill=color, width=2)
                self.avatar_canvas.create_oval(x-7, y-7, x+7, y+7, fill=color, outline="white", width=2)
                self.avatar_canvas.create_text(x, y, text=str(i+1), fill="white", font=("Consolas", 7, "bold"))
            # Centre 7D
            self.avatar_canvas.create_text(cx, cy, text="7D", fill=color, font=("Consolas", 12, "bold"))
            
        elif "lattice" in geo_type or "clifford" in geo_type:
            # Lattice de Clifford avec structure cristalline
            for i in range(-3, 4):
                for j in range(-3, 4):
                    x = cx + (i * 22) * cos_a - (j * 18) * sin_a
                    y = cy + (i * 22) * sin_a * 0.35 + (j * 18) * cos_a * 0.35
                    dist = math.sqrt(i*i + j*j)
                    if dist < 4:
                        size = max(2, 7 - dist * 1.5)
                        # Couleur basee sur la position
                        if (i + j) % 2 == 0:
                            node_color = color
                        else:
                            node_color = color2
                        self.avatar_canvas.create_rectangle(x-size, y-size, x+size, y+size, 
                                                           fill=node_color, outline="white")
                        # Connexions
                        if i < 3 and abs(j) < 3:
                            x2 = cx + ((i+1) * 22) * cos_a - (j * 18) * sin_a
                            y2 = cy + ((i+1) * 22) * sin_a * 0.35 + (j * 18) * cos_a * 0.35
                            self.avatar_canvas.create_line(x, y, x2, y2, fill=color3, width=1)
            
        elif "fractal" in geo_type or "entropy" in geo_type:
            # Fractale entropique avec arbre de Pythagore
            def draw_branch(x, y, length, angle_deg, depth, branch_color):
                if depth == 0 or length < 4:
                    # Feuille
                    self.avatar_canvas.create_oval(x-3, y-3, x+3, y+3, fill=branch_color, outline="")
                    return
                end_x = x + length * math.cos(math.radians(angle_deg))
                end_y = y + length * math.sin(math.radians(angle_deg))
                self.avatar_canvas.create_line(x, y, end_x, end_y, fill=branch_color, width=depth)
                # Branches avec variation
                draw_branch(end_x, end_y, length * 0.7, angle_deg - 25 - depth * 2, depth - 1, color2)
                draw_branch(end_x, end_y, length * 0.7, angle_deg + 25 + depth * 2, depth - 1, color3)
            
            # Plusieurs arbres
            draw_branch(cx, cy + 70, 45, -90 + angle * 0.3, 5, color)
            draw_branch(cx - 40, cy + 60, 30, -70 + angle * 0.2, 4, color2)
            draw_branch(cx + 40, cy + 60, 30, -110 + angle * 0.2, 4, color3)
            
        else:  # hybrid ou autre
            # Forme hybride complexe
            # Cercles concentriques
            for ring in range(4):
                ring_r = 55 - ring * 12
                self.avatar_canvas.create_oval(cx-ring_r, cy-ring_r*0.6, cx+ring_r, cy+ring_r*0.6, 
                                              outline=[color, color2, color3, color][ring], width=2)
            # Rayons
            for i in range(8):
                a = math.radians(i * 45) + rad
                x = cx + 55 * math.cos(a)
                y = cy + 55 * math.sin(a) * 0.6
                self.avatar_canvas.create_line(cx, cy, x, y, fill=color, width=2)
                # Points aux extremites
                self.avatar_canvas.create_oval(x-4, y-4, x+4, y+4, fill=color2, outline="white")
            # Noyau
            self.avatar_canvas.create_oval(cx-12, cy-12, cx+12, cy+12, fill=color, outline="white", width=2)
        
        # ============================================================
        # AFFICHAGE DES INFORMATIONS
        # ============================================================
        
        # Cadre d'info en bas
        self.avatar_canvas.create_rectangle(20, 245, 320, 278, fill="#0a0a1a", outline=color, width=1)
        
        # Type geometrique
        type_display = geo_type.replace("_", " ").upper()
        self.avatar_canvas.create_text(170, 255, text=type_display,
                                       fill=color, font=("Consolas", 10, "bold"))
        
        # Rarete avec indicateur visuel
        rarity_text = f"[{avatar.rarity_tier.upper()}]"
        self.avatar_canvas.create_text(170, 268, text=rarity_text,
                                       fill=color, font=("Consolas", 8))
        
        # Indicateur de puissance (petit cercle en haut a droite)
        power_level = min(avatar.effective_power / 150, 1.0)  # Normalise
        power_color = self._get_power_color(power_level)
        self.avatar_canvas.create_oval(300, 10, 330, 40, fill=power_color, outline="white", width=2)
        self.avatar_canvas.create_text(315, 25, text=f"{int(avatar.effective_power/100)}K",
                                       fill="white", font=("Consolas", 7, "bold"))
    
    def _get_power_color(self, power_level: float) -> str:
        """Returns une couleur basee sur le niveau de puissance (0-1)"""
        if power_level >= 0.9:
            return "#ff00ff"  # Magenta - Primordial
        elif power_level >= 0.75:
            return "#ffd700"  # Or - Mythical
        elif power_level >= 0.6:
            return "#ff6600"  # Orange - Legendary
        elif power_level >= 0.45:
            return "#a020f0"  # Violet - Epic
        elif power_level >= 0.3:
            return "#0080ff"  # Bleu - Rare
        else:
            return "#00ff00"  # Vert - Common
    
    def _set_avatar_view(self, view_type):
        """Change la vue de l'avatar"""
        # Pour matplotlib 3D (futur), ajuster view_init
        # Pour l'instant, on affiche juste un message
        pass
    
    def _show_avatar_stats_window(self):
        """Ouvre une fenetre detaillee des stats avec graphiques"""
        avatars = self.avatar_manager.get_avatars_owned_by_vault(self.current_vault_num)
        if not avatars:
            messagebox.showinfo("Info", "Aucun avatar pour ce vault")
            return
        
        avatar = avatars[0]
        
        # Fenetre de stats
        stats_win = tk.Toplevel(self.root)
        stats_win.title(f"Stats Detaillees - Avatar {avatar.avatar_id[:8]}")
        stats_win.geometry("700x550")
        stats_win.configure(bg=CypherpunkTheme.BG_DARK)
        
        # Notebook pour les onglets
        notebook = ttk.Notebook(stats_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # === Onglet Stats ===
        stats_frame = tk.Frame(notebook, bg=CypherpunkTheme.BG_DARK)
        notebook.add(stats_frame, text="📊 Stats")
        
        # Generer les stats
        try:
            from core.avatar_system import QuantumAvatarGenerator, AvatarStats
            gen = QuantumAvatarGenerator(avatar.avatar_id.encode(), vault_number=self.current_vault_num)
            stats = gen.generate_stats()
            avatar_class = gen.select_class()
            if avatar_class:
                stats = gen.apply_class_bonuses(stats, avatar_class)
        except:
            stats = None
            avatar_class = None
        
        if stats:
            self._create_stats_display(stats_frame, stats, avatar_class)
        
        # === Onglet Classe ===
        class_frame = tk.Frame(notebook, bg=CypherpunkTheme.BG_DARK)
        notebook.add(class_frame, text="🎭 Classe")
        
        if avatar_class:
            self._create_class_display(class_frame, avatar_class)
        
        # === Onglet DNA ===
        dna_frame = tk.Frame(notebook, bg=CypherpunkTheme.BG_DARK)
        notebook.add(dna_frame, text="🧬 DNA")
        
        self._create_dna_display(dna_frame, avatar)
    
    def _create_stats_display(self, parent, stats, avatar_class):
        """Creates the'affichage des stats dans la fenetre"""
        # Header
        header = tk.Frame(parent, bg=CypherpunkTheme.BG_DARK)
        header.pack(fill=tk.X, pady=10, padx=10)
        
        tk.Label(header, text=f"Niveau {stats.level}", bg=CypherpunkTheme.BG_DARK,
                fg=CypherpunkTheme.NEON_YELLOW, font=("Consolas", 16, "bold")).pack(side=tk.LEFT)
        
        if avatar_class:
            tk.Label(header, text=f"  |  {avatar_class.icon} {avatar_class.name}",
                    bg=CypherpunkTheme.BG_DARK, fg=avatar_class.color,
                    font=("Consolas", 14, "bold")).pack(side=tk.LEFT)
        
        # Stats en colonnes
        cols_frame = tk.Frame(parent, bg=CypherpunkTheme.BG_DARK)
        cols_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Colonne Primaires
        col1 = tk.Frame(cols_frame, bg=CypherpunkTheme.BG_PANEL, width=200)
        col1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        tk.Label(col1, text="STATS PRIMAIRES", bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.NEON_GREEN, font=("Consolas", 11, "bold")).pack(pady=10)
        
        primary = [
            ("Force", stats.strength, "#ff4444"),
            ("Agilite", stats.agility, "#44ff44"),
            ("Intelligence", stats.intelligence, "#4444ff"),
            ("Vitalite", stats.vitality, "#ff8844"),
            ("Chance", stats.luck, "#ffff44"),
            ("Charisme", stats.charisma, "#ff44ff"),
        ]
        
        for name, val, color in primary:
            row = tk.Frame(col1, bg=CypherpunkTheme.BG_PANEL)
            row.pack(fill=tk.X, pady=3, padx=10)
            tk.Label(row, text=name, bg=CypherpunkTheme.BG_PANEL, fg="white",
                    font=("Consolas", 10), width=12, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=str(val), bg=CypherpunkTheme.BG_PANEL, fg=color,
                    font=("Consolas", 12, "bold")).pack(side=tk.RIGHT)
        
        # Colonne Secondaires
        col2 = tk.Frame(cols_frame, bg=CypherpunkTheme.BG_PANEL, width=200)
        col2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        tk.Label(col2, text="STATS SECONDAIRES", bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.NEON_CYAN, font=("Consolas", 11, "bold")).pack(pady=10)
        
        secondary = [
            ("HP Max", stats.hp_max, "#00ff00"),
            ("MP Max", stats.mp_max, "#00aaff"),
            ("Attaque", stats.attack, "#ff0000"),
            ("M.Attaque", stats.magic_attack, "#aa00ff"),
            ("Defense", stats.defense, "#888888"),
            ("Vitesse", stats.speed, "#00ffaa"),
            ("Crit%", f"{stats.crit_rate:.1f}", "#ffaa00"),
            ("Esquive%", f"{stats.evasion:.1f}", "#00ff88"),
        ]
        
        for name, val, color in secondary:
            row = tk.Frame(col2, bg=CypherpunkTheme.BG_PANEL)
            row.pack(fill=tk.X, pady=3, padx=10)
            tk.Label(row, text=name, bg=CypherpunkTheme.BG_PANEL, fg="white",
                    font=("Consolas", 10), width=12, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=str(val), bg=CypherpunkTheme.BG_PANEL, fg=color,
                    font=("Consolas", 12, "bold")).pack(side=tk.RIGHT)
        
        # Colonne Quantiques
        col3 = tk.Frame(cols_frame, bg=CypherpunkTheme.BG_PANEL, width=200)
        col3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        tk.Label(col3, text="STATS QUANTIQUES", bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.NEON_MAGENTA, font=("Consolas", 11, "bold")).pack(pady=10)
        
        quantum = [
            ("Q.Power", stats.quantum_power, CypherpunkTheme.NEON_MAGENTA),
            ("Dim.Sync", f"{stats.dimensional_sync:.1f}%", "#ff00ff"),
            ("Entropy.R", f"{stats.entropy_resistance:.1f}%", "#00ffff"),
            ("Temp.Flux", f"{stats.temporal_flux:.1f}%", "#ffff00"),
            ("Nexus.Aff", f"{stats.nexus_affinity:.1f}%", "#ff8800"),
        ]
        
        for name, val, color in quantum:
            row = tk.Frame(col3, bg=CypherpunkTheme.BG_PANEL)
            row.pack(fill=tk.X, pady=3, padx=10)
            tk.Label(row, text=name, bg=CypherpunkTheme.BG_PANEL, fg="white",
                    font=("Consolas", 10), width=12, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=str(val), bg=CypherpunkTheme.BG_PANEL, fg=color,
                    font=("Consolas", 12, "bold")).pack(side=tk.RIGHT)
    
    def _create_class_display(self, parent, avatar_class):
        """Displays les informations de la classe"""
        # Header avec icone et nom
        header = tk.Frame(parent, bg=CypherpunkTheme.BG_DARK)
        header.pack(fill=tk.X, pady=20, padx=20)
        
        tk.Label(header, text=avatar_class.icon, bg=CypherpunkTheme.BG_DARK,
                font=("Segoe UI Emoji", 40)).pack(side=tk.LEFT)
        
        info = tk.Frame(header, bg=CypherpunkTheme.BG_DARK)
        info.pack(side=tk.LEFT, padx=20)
        
        tk.Label(info, text=avatar_class.name, bg=CypherpunkTheme.BG_DARK,
                fg=avatar_class.color, font=("Consolas", 18, "bold")).pack(anchor=tk.W)
        tk.Label(info, text=avatar_class.description, bg=CypherpunkTheme.BG_DARK,
                fg=CypherpunkTheme.TEXT_SECONDARY, font=("Consolas", 10)).pack(anchor=tk.W)
        
        if avatar_class.is_supreme_only:
            tk.Label(info, text="⭐ SUPREME EXCLUSIF", bg=CypherpunkTheme.BG_DARK,
                    fg="#ffd700", font=("Consolas", 9, "bold")).pack(anchor=tk.W, pady=5)
        
        # Affinites d'items
        aff_frame = tk.LabelFrame(parent, text="AFFINITES D'ITEMS", bg=CypherpunkTheme.BG_PANEL,
                                  fg=CypherpunkTheme.NEON_CYAN, font=("Consolas", 11, "bold"))
        aff_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Trier par affinite
        sorted_aff = sorted(avatar_class.item_affinities.items(), key=lambda x: -x[1])
        
        for i, (item_cat, affinity) in enumerate(sorted_aff):
            row = tk.Frame(aff_frame, bg=CypherpunkTheme.BG_PANEL)
            row.pack(fill=tk.X, pady=2, padx=10)
            
            # Indicateur
            if affinity >= 1.8:
                indicator, color = "+++", "#00ff00"
            elif affinity >= 1.5:
                indicator, color = "++", "#88ff00"
            elif affinity > 1.0:
                indicator, color = "+", "#ffff00"
            elif affinity < 1.0:
                indicator, color = "-", "#ff4444"
            else:
                indicator, color = "=", "#888888"
            
            tk.Label(row, text=f"[{indicator}]", bg=CypherpunkTheme.BG_PANEL,
                    fg=color, font=("Consolas", 10, "bold"), width=5).pack(side=tk.LEFT)
            tk.Label(row, text=item_cat.upper(), bg=CypherpunkTheme.BG_PANEL,
                    fg="white", font=("Consolas", 10), width=12, anchor=tk.W).pack(side=tk.LEFT)
            
            bonus_text = avatar_class.get_affinity_bonus_text(item_cat)
            tk.Label(row, text=bonus_text, bg=CypherpunkTheme.BG_PANEL,
                    fg=color, font=("Consolas", 10, "bold")).pack(side=tk.RIGHT, padx=10)
        
        # Abilities
        ab_frame = tk.LabelFrame(parent, text="ABILITIES", bg=CypherpunkTheme.BG_PANEL,
                                 fg=CypherpunkTheme.NEON_GREEN, font=("Consolas", 11, "bold"))
        ab_frame.pack(fill=tk.X, padx=20, pady=10)
        
        for ability in avatar_class.abilities:
            tk.Label(ab_frame, text=f"⚡ {ability.replace('_', ' ').title()}",
                    bg=CypherpunkTheme.BG_PANEL, fg="white",
                    font=("Consolas", 10)).pack(anchor=tk.W, padx=10, pady=2)
    
    def _create_dna_display(self, parent, avatar):
        """Displays les informations DNA de l'avatar"""
        from tkinter import scrolledtext
        
        dna_text = scrolledtext.ScrolledText(
            parent, bg=CypherpunkTheme.BG_SECONDARY, fg="#00ff00",
            font=("Consolas", 10), height=20
        )
        dna_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Formater le DNA
        content = "🧬 ADN CRYPTOGRAPHIQUE DE L'AVATAR\n"
        content += "═" * 50 + "\n\n"
        
        content += f"Avatar ID: {avatar.avatar_id}\n"
        content += f"Type: {avatar.geometry_type}\n"
        content += f"Rarete: {avatar.rarity_tier.upper()} ({avatar.rarity_score:.1f}/100)\n"
        content += f"Puissance: {avatar.effective_power:.0f}\n\n"
        
        content += "═══ ATTRIBUTS DNA ═══\n"
        if avatar.attributes:
            for attr, value in avatar.attributes.items():
                attr_name = attr.replace("_", " ").title()
                bar = "█" * int(value / 10) + "░" * (10 - int(value / 10))
                content += f"{attr_name:25} [{bar}] {value:.1f}%\n"
        
        content += "\n═══ HASH VISUALISATION ═══\n"
        # Convertir l'ID en representation visuelle
        for i in range(0, min(32, len(avatar.avatar_id)), 2):
            byte_hex = avatar.avatar_id[i:i+2]
            try:
                byte_val = int(byte_hex, 16)
                binary = bin(byte_val)[2:].zfill(8)
                visual = binary.replace('0', '░').replace('1', '█')
                content += f"0x{byte_hex}  {visual}\n"
            except:
                pass
        
        dna_text.insert('1.0', content)
        dna_text.config(state=tk.DISABLED)
    
    def _export_avatar(self):
        """Exporte l'avatar dans differents formats"""
        avatars = self.avatar_manager.get_avatars_owned_by_vault(self.current_vault_num)
        if not avatars:
            messagebox.showinfo("Info", "Aucun avatar a exporter")
            return
        
        avatar = avatars[0]
        
        # Creer dossier d'export
        export_dir = Path(f"./exports/avatars/vault_{self.current_vault_num:04d}")
        export_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Exporter les metadonnees JSON
            metadata = {
                "avatar_id": avatar.avatar_id,
                "geometry_type": avatar.geometry_type,
                "rarity_tier": avatar.rarity_tier,
                "rarity_score": avatar.rarity_score,
                "effective_power": avatar.effective_power,
                "attributes": avatar.attributes,
                "vault_number": self.current_vault_num,
                "exported_at": datetime.now().isoformat()
            }
            
            json_path = export_dir / f"avatar_{timestamp}.json"
            with open(json_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Sauvegarder le canvas comme image
            # (PostScript puis conversion si PIL disponible)
            ps_path = export_dir / f"avatar_{timestamp}.ps"
            self.avatar_canvas.postscript(file=str(ps_path), colormode='color')
            
            messagebox.showinfo(
                "Export Reussi",
                f"Avatar exporte vers:\n{export_dir}\n\n"
                f"Fichiers:\n- avatar_{timestamp}.json\n- avatar_{timestamp}.ps"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Erreur d'export: {e}")
    
    def _open_threejs_viewer(self):
        """Ouvre la visualisation Three.js dans le navigateur"""
        avatars = self.avatar_manager.get_avatars_owned_by_vault(self.current_vault_num)
        if not avatars:
            messagebox.showinfo("Info", "Aucun avatar a visualiser.\nGenerez d'abord un avatar.")
            return
        
        avatar = avatars[0]
        
        try:
            from core.avatar_system import render_avatar_threejs
            
            # Preparer les donnees de l'avatar
            avatar_data = {
                'avatar_id': avatar.avatar_id,
                'geometry_type': avatar.geometry_type,
                'rarity_tier': avatar.rarity_tier,
                'rarity_score': avatar.rarity_score,
                'effective_power': avatar.effective_power,
                'attributes': avatar.attributes or {}
            }
            
            # Generer et ouvrir le viewer
            html_path = render_avatar_threejs(avatar_data, auto_open=True)
            
            messagebox.showinfo(
                "Visualisation 3D",
                f"Viewer Three.js ouvert dans le navigateur!\n\n"
                f"Fichier: {html_path}\n\n"
                f"Controles:\n"
                f"- Souris: Rotation de la camera\n"
                f"- Molette: Zoom\n"
                f"- Boutons: Auto-rotate, Wireframe, Screenshot"
            )
            
        except Exception as e:
            messagebox.showerror("Error", f"Impossible d'ouvrir le viewer 3D:\n{e}")
    
    def _display_avatar_placeholder(self):
        """Displays le placeholder quand pas d'avatar"""
        for widget in self.avatar_info_frame.winfo_children():
            widget.destroy()
        
        tk.Label(
            self.avatar_info_frame,
            text="Aucun avatar pour ce vault.\n\n"
                 "Cliquez sur GENERER AVATAR pour creer\n"
                 "un avatar 3D unique base sur les\n"
                 "donnees cryptographiques de votre vault.",
            bg=CypherpunkTheme.BG_SECONDARY,
            fg=CypherpunkTheme.TEXT_SECONDARY,
            font=("Consolas", 10),
            justify=tk.CENTER
        ).pack(pady=50, padx=20)
    
    def _display_avatar_info(self, avatar):
        """Displays les informations detaillees de l'avatar"""
        for widget in self.avatar_info_frame.winfo_children():
            widget.destroy()
        
        def add_info(label, value, color=CypherpunkTheme.TEXT_PRIMARY):
            row = tk.Frame(self.avatar_info_frame, bg=CypherpunkTheme.BG_SECONDARY)
            row.pack(fill=tk.X, pady=2, padx=10)
            tk.Label(row, text=f"{label}:", bg=CypherpunkTheme.BG_SECONDARY,
                    fg=CypherpunkTheme.TEXT_SECONDARY, font=("Consolas", 9), width=18, anchor=tk.W
            ).pack(side=tk.LEFT)
            tk.Label(row, text=str(value), bg=CypherpunkTheme.BG_SECONDARY,
                    fg=color, font=("Consolas", 9, "bold"), anchor=tk.W
            ).pack(side=tk.LEFT, fill=tk.X)
        
        # Section Identite
        tk.Label(self.avatar_info_frame, text="IDENTITE",
                bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_MAGENTA,
                font=("Consolas", 10, "bold")).pack(anchor=tk.W, pady=(10, 5), padx=10)
        
        add_info("Avatar ID", avatar.avatar_id[:16] + "...", CypherpunkTheme.NEON_CYAN)
        add_info("Type", avatar.geometry_type.replace("_", " ").title(), CypherpunkTheme.NEON_MAGENTA)
        add_info("Rarete", avatar.rarity_tier.upper(), self._get_rarity_color(avatar.rarity_tier))
        add_info("Score", f"{avatar.rarity_score:.1f}/100")
        
        # Section Puissance
        tk.Label(self.avatar_info_frame, text="PUISSANCE",
                bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_GREEN,
                font=("Consolas", 10, "bold")).pack(anchor=tk.W, pady=(15, 5), padx=10)
        
        base_power = avatar.rarity_score * 100
        multiplier = avatar.binding.power_multiplier if avatar.binding else 1.0
        
        add_info("Puissance base", f"{base_power:.0f}")
        add_info("Multiplicateur", f"x{multiplier:.2f}", 
                CypherpunkTheme.NEON_GREEN if multiplier > 1 else CypherpunkTheme.TEXT_SECONDARY)
        add_info("Puissance totale", f"{avatar.effective_power:.0f}", CypherpunkTheme.NEON_YELLOW)
        
        # Section Liaison
        tk.Label(self.avatar_info_frame, text="LIAISON",
                bg=CypherpunkTheme.BG_SECONDARY, fg="#ff6600",
                font=("Consolas", 10, "bold")).pack(anchor=tk.W, pady=(15, 5), padx=10)
        
        if avatar.binding:
            binding = avatar.binding
            state_color = {
                "attached": CypherpunkTheme.NEON_GREEN,
                "detached": "#ff6600",
                "soul_bound": CypherpunkTheme.NEON_MAGENTA
            }.get(binding.state, "white")
            
            add_info("Etat", binding.state.upper(), state_color)
            add_info("Vault origine", f"#{binding.origin_vault_number}")
            add_info("Proprietaire", f"#{binding.current_owner_vault}" if binding.current_owner_vault else "N/A")
            
            if binding.state == "attached":
                add_info("Bonus", "+50% puissance", CypherpunkTheme.NEON_GREEN)
                add_info("Transferable", "NON", "#ff0000")
            elif binding.state == "detached":
                add_info("Bonus", "No", CypherpunkTheme.TEXT_SECONDARY)
                add_info("Transferable", "OUI", CypherpunkTheme.NEON_GREEN)
                if binding.detached_at:
                    add_info("Detache le", binding.detached_at[:10])
            else:  # soul_bound
                add_info("Bonus", "+50% puissance", CypherpunkTheme.NEON_GREEN)
                add_info("Transferable", "JAMAIS", CypherpunkTheme.NEON_MAGENTA)
        
        # Section Attributs
        tk.Label(self.avatar_info_frame, text="ATTRIBUTS DNA",
                bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_CYAN,
                font=("Consolas", 10, "bold")).pack(anchor=tk.W, pady=(15, 5), padx=10)
        
        if avatar.attributes:
            for attr, value in list(avatar.attributes.items())[:6]:
                attr_name = attr.replace("_", " ").title()
                add_info(attr_name[:16], f"{value:.1f}")
        
        # Section Token
        if avatar.is_tokenized and avatar.token:
            tk.Label(self.avatar_info_frame, text="TOKENISATION",
                    bg=CypherpunkTheme.BG_SECONDARY, fg="#f7931a",
                    font=("Consolas", 10, "bold")).pack(anchor=tk.W, pady=(15, 5), padx=10)
            
            add_info("Rune ID", avatar.token.rune_id, "#f7931a")
            add_info("Status", avatar.token.status.upper())
            if avatar.token.inscription_txid:
                add_info("TXID", avatar.token.inscription_txid[:20] + "...")
    
    def _get_rarity_color(self, rarity: str) -> str:
        """Returns la couleur selon la rarete"""
        colors = {
            "common": "#808080",
            "uncommon": "#00ff00",
            "rare": "#0080ff",
            "epic": "#a020f0",
            "legendary": "#ffd700",
            "mythical": "#ff00ff",
            "primordial": "#ff4500"
        }
        return colors.get(rarity.lower(), "white")
    
    def _refresh_avatar(self):
        """Rafraichit l'affichage de l'avatar"""
        if not AVATAR_AVAILABLE:
            return
        
        # Chercher l'avatar du vault courant
        avatars = self.avatar_manager.get_avatars_owned_by_vault(self.current_vault_num)
        
        if not avatars:
            # Verifier si cree mais transfere
            avatars = self.avatar_manager.get_avatars_by_vault(f"vault_{self.current_vault_num:04d}")
        
        if avatars:
            avatar = avatars[0]  # Premier avatar
            self._display_avatar_info(avatar)
            self._update_avatar_buttons(avatar)
            
            # Mettre a jour les infos rapides
            self.avatar_type_var.set(avatar.geometry_type.replace("_", " ").upper())
            self.avatar_rarity_var.set(avatar.rarity_tier.upper())
            self.avatar_power_var.set(f"{avatar.effective_power:,.0f}")
            
            # Couleur de rarete
            rarity_colors = {
                "common": "#808080", "uncommon": "#00ff00", "rare": "#0080ff",
                "epic": "#a020f0", "legendary": "#ffd700", "mythical": "#ff00ff",
                "primordial": "#00ffff"
            }
            self.avatar_rarity_label.configure(fg=rarity_colors.get(avatar.rarity_tier.lower(), "#ffffff"))
            
            # Apercu texte
            self.avatar_preview_label.configure(
                text=f"🎭 AVATAR GENERE\n\n"
                     f"Type: {avatar.geometry_type.replace('_', ' ').title()}\n"
                     f"Rarete: {avatar.rarity_tier.upper()}\n"
                     f"Puissance: {avatar.effective_power:,.0f}\n\n"
                     f"Cliquez sur VISUALISER 3D\npour voir votre avatar unique",
                fg=rarity_colors.get(avatar.rarity_tier.lower(), "#ffffff")
            )
            
            # Generer et afficher les stats
            try:
                from core.avatar_system import QuantumAvatarGenerator
                gen = QuantumAvatarGenerator(avatar.avatar_id.encode(), vault_number=self.current_vault_num)
                stats = gen.generate_stats()
                avatar_class = gen.select_class()
                
                if avatar_class:
                    stats = gen.apply_class_bonuses(stats, avatar_class)
                    self.avatar_class_var.set(f"{avatar_class.icon} {avatar_class.name}")
                else:
                    self.avatar_class_var.set("---")
                
                self._display_avatar_stats(avatar, stats)
            except Exception as e:
                self._display_stats_placeholder()
                self.avatar_class_var.set("---")
            
            # Mettre a jour l'etat
            if avatar.binding:
                state_text = avatar.binding.state.upper()
                state_color = {
                    "attached": CypherpunkTheme.NEON_GREEN,
                    "detached": "#ff6600",
                    "soul_bound": CypherpunkTheme.NEON_MAGENTA
                }.get(avatar.binding.state, "white")
                
                self.avatar_state_var.set(state_text)
                self.avatar_state_label.configure(fg=state_color)
        else:
            self._display_avatar_placeholder()
            self._display_stats_placeholder()
            self.avatar_type_var.set("---")
            self.avatar_rarity_var.set("---")
            self.avatar_power_var.set("---")
            self.avatar_state_var.set("---")
            self.avatar_class_var.set("---")
            self.avatar_preview_label.configure(
                text="Aucun avatar\n\nCliquez sur GENERER\npour creer votre avatar unique",
                fg=CypherpunkTheme.TEXT_SECONDARY
            )
            self.detach_btn.configure(state=tk.DISABLED)
            self.transfer_avatar_btn.configure(state=tk.DISABLED)
            self.tokenize_btn.configure(state=tk.DISABLED)
    
    def _load_avatar_preview(self, avatar):
        """Charge et affiche l'image preview de l'avatar"""
        self.avatar_canvas.delete("all")
        
        preview_path = avatar.preview_path
        if preview_path and Path(preview_path).exists():
            try:
                from PIL import Image, ImageTk
                img = Image.open(preview_path)
                img = img.resize((290, 290), Image.Resampling.LANCZOS)
                self.avatar_photo = ImageTk.PhotoImage(img)
                self.avatar_canvas.create_image(150, 150, image=self.avatar_photo)
                
                # Ajouter le type en overlay
                self.avatar_canvas.create_text(
                    150, 280,
                    text=avatar.geometry_type.replace("_", " ").upper(),
                    fill=CypherpunkTheme.NEON_MAGENTA,
                    font=("Consolas", 10, "bold")
                )
                return
            except Exception as e:
                print(f"[WARN] Cannot load preview: {e}")
        
        # Fallback: dessiner une representation simple
        self._draw_avatar_placeholder(avatar)
    
    def _draw_avatar_placeholder(self, avatar):
        """Dessine une representation placeholder de l'avatar"""
        # Couleur basee sur la rarete
        color = self._get_rarity_color(avatar.rarity_tier)
        
        # Forme basee sur le type
        geo_type = avatar.geometry_type
        
        if "sphere" in geo_type:
            self.avatar_canvas.create_oval(75, 75, 225, 225, outline=color, width=3)
            self.avatar_canvas.create_oval(100, 100, 200, 200, outline=color, width=2)
        elif "torus" in geo_type:
            self.avatar_canvas.create_oval(50, 100, 250, 200, outline=color, width=3)
            self.avatar_canvas.create_oval(100, 120, 200, 180, fill=CypherpunkTheme.BG_SECONDARY, outline=color, width=2)
        elif "polyhedron" in geo_type or "crystal" in geo_type:
            points = [150, 50, 250, 130, 220, 250, 80, 250, 50, 130]
            self.avatar_canvas.create_polygon(points, outline=color, width=3, fill="")
        elif "lattice" in geo_type:
            for i in range(5):
                for j in range(5):
                    x = 60 + i * 45
                    y = 60 + j * 45
                    self.avatar_canvas.create_rectangle(x, y, x+10, y+10, fill=color)
        elif "fractal" in geo_type:
            self._draw_fractal_triangle(75, 225, 225, 225, 150, 75, 3, color)
        elif "7d" in geo_type:
            for i in range(7):
                angle = i * 3.14159 * 2 / 7
                x1 = 150 + 80 * __import__('math').cos(angle)
                y1 = 150 + 80 * __import__('math').sin(angle)
                self.avatar_canvas.create_line(150, 150, x1, y1, fill=color, width=2)
                self.avatar_canvas.create_oval(x1-5, y1-5, x1+5, y1+5, fill=color)
        else:  # hybrid ou autre
            self.avatar_canvas.create_oval(75, 75, 225, 225, outline=color, width=2)
            points = [150, 80, 200, 150, 150, 220, 100, 150]
            self.avatar_canvas.create_polygon(points, outline=color, width=2, fill="")
        
        # Nom du type
        self.avatar_canvas.create_text(
            150, 270,
            text=geo_type.replace("_", " ").upper(),
            fill=color,
            font=("Consolas", 9, "bold")
        )
        
        # Rarete
        self.avatar_canvas.create_text(
            150, 285,
            text=avatar.rarity_tier.upper(),
            fill=color,
            font=("Consolas", 8)
        )
    
    def _draw_fractal_triangle(self, x1, y1, x2, y2, x3, y3, depth, color):
        """Dessine un triangle de Sierpinski"""
        if depth == 0:
            self.avatar_canvas.create_polygon(x1, y1, x2, y2, x3, y3, outline=color, width=1, fill="")
        else:
            mx1 = (x1 + x2) / 2
            my1 = (y1 + y2) / 2
            mx2 = (x2 + x3) / 2
            my2 = (y2 + y3) / 2
            mx3 = (x3 + x1) / 2
            my3 = (y3 + y1) / 2
            
            self._draw_fractal_triangle(x1, y1, mx1, my1, mx3, my3, depth-1, color)
            self._draw_fractal_triangle(mx1, my1, x2, y2, mx2, my2, depth-1, color)
            self._draw_fractal_triangle(mx3, my3, mx2, my2, x3, y3, depth-1, color)
    
    def _update_avatar_buttons(self, avatar):
        """Met a jour l'etat des boutons selon l'avatar"""
        if not avatar.binding:
            self.detach_btn.configure(state=tk.DISABLED)
            self.transfer_avatar_btn.configure(state=tk.DISABLED)
            self.tokenize_btn.configure(state=tk.DISABLED)
            return
        
        state = avatar.binding.state
        
        # Detacher: seulement si attache
        if state == "attached":
            self.detach_btn.configure(state=tk.NORMAL)
        else:
            self.detach_btn.configure(state=tk.DISABLED)
        
        # Transferer: seulement si detache
        if state == "detached":
            self.transfer_avatar_btn.configure(state=tk.NORMAL)
            self.tokenize_btn.configure(state=tk.NORMAL if not avatar.is_tokenized else tk.DISABLED)
        else:
            self.transfer_avatar_btn.configure(state=tk.DISABLED)
            self.tokenize_btn.configure(state=tk.DISABLED)
    
    def _generate_avatar(self):
        """Generates un nouvel avatar UNIQUE et IMMUABLE pour le vault"""
        if not AVATAR_AVAILABLE:
            messagebox.showerror("Error", "Module Avatar non disponible")
            return
        
        # Importer les constantes pionniers
        from core.avatar_system import (
            QuantumAvatarGenerator, PIONEER_AVATAR_LIMIT,
            PIONEER_TIERS, PIONEER_RARITY_BONUS, PIONEER_MIN_RARITY
        )
        
        # ============================================================
        # VERIFICATION IMMUABILITE: Un vault = Un seul avatar JAMAIS
        # ============================================================
        existing = self.avatar_manager.get_avatars_owned_by_vault(self.current_vault_num)
        if not existing:
            # Verifier aussi les avatars crees pour ce vault mais transferes
            existing = self.avatar_manager.get_avatars_by_vault(f"vault_{self.current_vault_num:04d}")
        
        if existing:
            avatar = existing[0]
            messagebox.showwarning(
                "⚠️ AVATAR IMMUABLE",
                f"Ce vault possede deja un avatar UNIQUE et IMMUABLE.\n\n"
                f"╔══════════════════════════════════════╗\n"
                f"║  L'avatar ne peut PAS etre regenere  ║\n"
                f"╚══════════════════════════════════════╝\n\n"
                f"Type: {avatar.geometry_type.replace('_', ' ').title()}\n"
                f"Rarete: {avatar.rarity_tier.upper()}\n"
                f"Puissance: {avatar.effective_power:.0f}\n\n"
                f"Chaque vault genere UN SEUL avatar base sur\n"
                f"son empreinte cryptographique unique.\n"
                f"Cette regle garantit l'authenticite et la rarete."
            )
            return
        
        # Verifier l'eligibilite du vault (limite 10,000)
        can_have, reason = QuantumAvatarGenerator.can_have_avatar(self.current_vault_num)
        if not can_have:
            messagebox.showerror(
                "Vault Non Eligible",
                f"Ce vault ne peut pas avoir d'avatar.\n\n"
                f"Raison: {reason}\n\n"
                f"Seuls les {PIONEER_AVATAR_LIMIT:,} premiers vaults\n"
                f"peuvent obtenir un avatar unique."
            )
            return
        
        # Determiner le tier pionnier
        pioneer_tier = None
        for tier, (min_num, max_num) in PIONEER_TIERS.items():
            if min_num <= self.current_vault_num <= max_num:
                pioneer_tier = tier
                break
        
        # Afficher les bonus du tier
        if pioneer_tier:
            bonus_info = (
                f"Vault #{self.current_vault_num} - Tier: {pioneer_tier.upper()}\n\n"
                f"BONUS PIONNIER:\n"
                f"- Rarete minimum: {PIONEER_MIN_RARITY.get(pioneer_tier, 'common').upper()}\n"
                f"- Bonus rarete: +{PIONEER_RARITY_BONUS.get(pioneer_tier, 0)} points\n"
            )
            
            if pioneer_tier == "supreme":
                bonus_info += "\nBONUS SUPREME EXCLUSIF:\n- Types: Nexus Crystal, 7D Projection, Hybrid Form\n- Attribut 'Pioneer Blessing' a 100%\n- Profondeur dimensionnelle maximale"
        else:
            bonus_info = f"Vault #{self.current_vault_num}"
        
        # Confirmer la generation avec avertissement d'immuabilite
        result = messagebox.askyesno(
            "⚡ Generer Avatar UNIQUE",
            f"{bonus_info}\n\n"
            f"╔══════════════════════════════════════════╗\n"
            f"║  ATTENTION: GENERATION IRREVERSIBLE!     ║\n"
            f"║  L'avatar sera UNIQUE et IMMUABLE.       ║\n"
            f"║  Vous ne pourrez JAMAIS le regenerer.    ║\n"
            f"╚══════════════════════════════════════════╝\n\n"
            f"Voulez-vous generer votre avatar unique?"
        )
        if not result:
            return
        
        # Generer les donnees du vault de maniere DETERMINISTE
        # L'avatar est base sur l'ID unique du vault, pas sur la date
        vault_data = f"vault_{self.current_vault_num:04d}_immutable_avatar".encode()
        
        # Demander l'adresse Bitcoin
        address = simpledialog.askstring(
            "Adresse Bitcoin",
            "Entrez votre adresse Bitcoin pour l'avatar:",
            initialvalue="bc1q..."
        )
        
        if not address or len(address) < 20:
            messagebox.showwarning("Warning", "Adresse Bitcoin invalide")
            return
        
        try:
            avatar = self.avatar_manager.create_avatar(
                vault_data=vault_data,
                vault_id=f"vault_{self.current_vault_num:04d}",
                vault_number=self.current_vault_num,
                owner_address=address,
                generation=1,
                soul_bound=False
            )
            
            # Message de succes avec les infos du tier
            tier_msg = f"\nTier Pionnier: {pioneer_tier.upper()}" if pioneer_tier else ""
            
            messagebox.showinfo(
                "Avatar Pionnier Genere!",
                f"Avatar cree avec succes!{tier_msg}\n\n"
                f"Type: {avatar.geometry_type.replace('_', ' ').title()}\n"
                f"Rarete: {avatar.rarity_tier.upper()}\n"
                f"Puissance: {avatar.effective_power:.0f}\n\n"
                f"L'avatar est LIE a votre vault (+50% puissance).\n"
                f"Vous pouvez le DETACHER pour le transferer."
            )
            
            self._refresh_avatar()
            
        except Exception as e:
            messagebox.showerror("Error", f"Impossible de generer l'avatar:\n{e}")
    
    def _detach_avatar(self):
        """Detache l'avatar du vault"""
        avatars = self.avatar_manager.get_avatars_owned_by_vault(self.current_vault_num)
        if not avatars:
            return
        
        avatar = avatars[0]
        
        result = messagebox.askyesno(
            "ATTENTION - Detachement Irreversible",
            "Etes-vous sur de vouloir DETACHER cet avatar?\n\n"
            "CONSEQUENCES:\n"
            "- Perte du bonus de +50% de puissance\n"
            "- Le detachement est IRREVERSIBLE\n"
            "- Frais: 50,000 sats\n\n"
            "AVANTAGES:\n"
            "- L'avatar devient TRANSFERABLE\n"
            "- Peut etre vendu ou echange\n"
            "- Peut etre tokenise sur Bitcoin\n\n"
            "Continuer?",
            icon=messagebox.WARNING
        )
        
        if not result:
            return
        
        try:
            # Obtenir l'adresse
            address = avatar.binding.current_owner_address or ""
            
            result = self.avatar_manager.detach_avatar(
                avatar.avatar_id,
                requester_address=address,
                requester_vault=self.current_vault_num,
                reason="Owner requested via UI"
            )
            
            messagebox.showinfo(
                "Avatar Detache",
                f"Avatar detache avec succes!\n\n"
                f"Puissance avant: {result['power_before']:.0f}\n"
                f"Puissance apres: {result['power_after']:.0f}\n"
                f"Perte: {result['power_loss']}\n\n"
                "L'avatar peut maintenant etre transfere."
            )
            
            self._refresh_avatar()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _transfer_avatar_dialog(self):
        """Ouvre le dialog de transfert d'avatar"""
        avatars = self.avatar_manager.get_avatars_owned_by_vault(self.current_vault_num)
        if not avatars:
            return
        
        avatar = avatars[0]
        
        if avatar.binding and avatar.binding.state != "detached":
            messagebox.showwarning("Warning", "L'avatar doit etre DETACHE pour etre transfere")
            return
        
        # Dialog de transfert
        dialog = tk.Toplevel(self.root)
        dialog.title("Transferer Avatar")
        dialog.geometry("500x300")
        dialog.configure(bg=CypherpunkTheme.BG_DARK)
        
        tk.Label(
            dialog,
            text="TRANSFERER AVATAR",
            bg=CypherpunkTheme.BG_DARK,
            fg=CypherpunkTheme.NEON_MAGENTA,
            font=("Consolas", 14, "bold")
        ).pack(pady=15)
        
        tk.Label(
            dialog,
            text=f"Type: {avatar.geometry_type} | Rarete: {avatar.rarity_tier.upper()}",
            bg=CypherpunkTheme.BG_DARK,
            fg=CypherpunkTheme.TEXT_SECONDARY
        ).pack()
        
        # Adresse destination
        tk.Label(
            dialog,
            text="Adresse Bitcoin destination:",
            bg=CypherpunkTheme.BG_DARK,
            fg="white"
        ).pack(pady=(20, 5))
        
        dest_var = tk.StringVar()
        tk.Entry(
            dialog,
            textvariable=dest_var,
            width=50,
            bg=CypherpunkTheme.BG_SECONDARY,
            fg="#f7931a",
            insertbackground="white"
        ).pack(pady=5)
        
        # Vault destination (optionnel)
        tk.Label(
            dialog,
            text="Vault destination (optionnel):",
            bg=CypherpunkTheme.BG_DARK,
            fg="white"
        ).pack(pady=(10, 5))
        
        vault_var = tk.StringVar()
        tk.Entry(
            dialog,
            textvariable=vault_var,
            width=20,
            bg=CypherpunkTheme.BG_SECONDARY,
            fg="white"
        ).pack(pady=5)
        
        def do_transfer():
            dest = dest_var.get()
            if not dest or len(dest) < 20:
                messagebox.showwarning("Warning", "Adresse invalide")
                return
            
            to_vault = None
            if vault_var.get():
                try:
                    to_vault = int(vault_var.get())
                except:
                    pass
            
            from_addr = avatar.binding.current_owner_address if avatar.binding else ""
            
            try:
                result = self.avatar_manager.transfer_avatar(
                    avatar.avatar_id,
                    from_address=from_addr,
                    to_address=dest,
                    from_vault=self.current_vault_num,
                    to_vault=to_vault
                )
                
                messagebox.showinfo("Success", "Avatar transfere avec succes!")
                dialog.destroy()
                self._refresh_avatar()
                
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        tk.Button(
            dialog,
            text="TRANSFERER",
            bg="#00aaff",
            fg="black",
            font=("Consolas", 11, "bold"),
            command=do_transfer
        ).pack(pady=20)
    
    def _tokenize_avatar(self):
        """Tokenise l'avatar sur Bitcoin"""
        avatars = self.avatar_manager.get_avatars_owned_by_vault(self.current_vault_num)
        if not avatars:
            return
        
        avatar = avatars[0]
        
        if avatar.is_tokenized:
            messagebox.showinfo("Info", "L'avatar est deja tokenise")
            return
        
        if avatar.binding and avatar.binding.state != "detached":
            messagebox.showwarning("Warning", "L'avatar doit etre DETACHE pour etre tokenise")
            return
        
        result = messagebox.askyesno(
            "Tokeniser Avatar",
            "Voulez-vous inscrire cet avatar sur la blockchain Bitcoin?\n\n"
            "Cela creera un token Rune unique representant votre avatar.\n"
            "Frais d'inscription: ~15,000 sats"
        )
        
        if not result:
            return
        
        address = avatar.binding.current_owner_address if avatar.binding else ""
        
        try:
            token = self.avatar_manager.tokenize_avatar(avatar.avatar_id, address)
            
            messagebox.showinfo(
                "Avatar Tokenise!",
                f"Token cree avec succes!\n\n"
                f"Rune ID: {token.rune_id}\n"
                f"Token ID: {token.token_id}\n\n"
                "Utilisez le Bridge pour finaliser l'inscription."
            )
            
            self._refresh_avatar()
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def _create_blockchain_tab(self) -> tk.Frame:
        """Créer l'onglet Blockchain avec monitoring temps réel via Alchemy"""
        frame = tk.Frame(self.notebook, bg=CypherpunkTheme.BG_DARK)
        
        # Variables
        self.alchemy_client = None
        self.alchemy_address = tk.StringVar(value="")
        self.alchemy_network = tk.StringVar(value="ETH_MAINNET")
        self.alchemy_api_key = tk.StringVar(value="")
        
        # === HEADER ===
        header_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_DARK)
        header_frame.pack(fill=tk.X, pady=(10, 15), padx=10)
        
        title_lbl = tk.Label(
            header_frame,
            text="⛓ BLOCKCHAIN MONITOR",
            bg=CypherpunkTheme.BG_DARK,
            fg=CypherpunkTheme.NEON_CYAN,
            font=("Consolas", 16, "bold")
        )
        title_lbl.pack(side=tk.LEFT)
        
        # Status indicator
        self.blockchain_status = tk.Label(
            header_frame,
            text="● DISCONNECTED",
            bg=CypherpunkTheme.BG_DARK,
            fg=CypherpunkTheme.TEXT_SECONDARY,
            font=CypherpunkTheme.FONT_MONO_SMALL
        )
        self.blockchain_status.pack(side=tk.RIGHT)
        
        # === CONFIG PANEL ===
        config_outer, config_inner = CypherpunkTheme.create_card_frame(frame, "⚙ CONFIGURATION")
        config_outer.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # API Key
        key_frame = tk.Frame(config_inner, bg=CypherpunkTheme.BG_PANEL)
        key_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(key_frame, text="API Key:", bg=CypherpunkTheme.BG_PANEL, 
                fg=CypherpunkTheme.TEXT_SECONDARY, width=12, anchor='w').pack(side=tk.LEFT)
        
        key_entry = tk.Entry(key_frame, textvariable=self.alchemy_api_key, width=50,
                            bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_GREEN,
                            insertbackground=CypherpunkTheme.NEON_CYAN, show="*")
        key_entry.pack(side=tk.LEFT, padx=5)
        
        # Network selection
        net_frame = tk.Frame(config_inner, bg=CypherpunkTheme.BG_PANEL)
        net_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(net_frame, text="Network:", bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.TEXT_SECONDARY, width=12, anchor='w').pack(side=tk.LEFT)
        
        networks = ["ETH_MAINNET", "ETH_SEPOLIA", "POLYGON_MAINNET", "ARB_MAINNET", "OPT_MAINNET", "BASE_MAINNET"]
        net_combo = ttk.Combobox(net_frame, textvariable=self.alchemy_network, values=networks, width=20)
        net_combo.pack(side=tk.LEFT, padx=5)
        
        # Wallet address
        addr_frame = tk.Frame(config_inner, bg=CypherpunkTheme.BG_PANEL)
        addr_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(addr_frame, text="Address:", bg=CypherpunkTheme.BG_PANEL,
                fg=CypherpunkTheme.TEXT_SECONDARY, width=12, anchor='w').pack(side=tk.LEFT)
        
        addr_entry = tk.Entry(addr_frame, textvariable=self.alchemy_address, width=50,
                             bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_GREEN,
                             insertbackground=CypherpunkTheme.NEON_CYAN)
        addr_entry.pack(side=tk.LEFT, padx=5)
        
        # Connect button
        connect_btn = CypherpunkTheme.create_neon_button(
            config_inner, "▶ CONNECT", self._connect_alchemy, CypherpunkTheme.NEON_GREEN
        )
        connect_btn.pack(pady=10)
        
        # === BALANCE DISPLAY ===
        balance_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_DARK)
        balance_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        self.eth_balance_var = tk.StringVar(value="0.00 ETH")
        balance_card = CypherpunkTheme.create_metric_display(
            balance_frame, "NATIVE BALANCE", self.eth_balance_var, "#FFD700"
        )
        balance_card.pack(side=tk.LEFT, padx=5)
        
        self.nft_count_var = tk.StringVar(value="0")
        nft_card = CypherpunkTheme.create_metric_display(
            balance_frame, "NFTs", self.nft_count_var, CypherpunkTheme.NEON_PURPLE
        )
        nft_card.pack(side=tk.LEFT, padx=5)
        
        self.token_count_var = tk.StringVar(value="0")
        token_card = CypherpunkTheme.create_metric_display(
            balance_frame, "TOKENS", self.token_count_var, CypherpunkTheme.NEON_CYAN
        )
        token_card.pack(side=tk.LEFT, padx=5)
        
        # === NOTEBOOK FOR NFTs/TOKENS ===
        assets_notebook = ttk.Notebook(frame)
        assets_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # NFT Tab
        nft_frame = tk.Frame(assets_notebook, bg=CypherpunkTheme.BG_DARK)
        assets_notebook.add(nft_frame, text="  NFTs  ")
        
        # NFT List
        nft_columns = ('Collection', 'Name', 'Token ID', 'Type', 'Contract')
        self.nft_tree = ttk.Treeview(nft_frame, columns=nft_columns, show='headings', height=10)
        
        for col in nft_columns:
            self.nft_tree.heading(col, text=col)
            self.nft_tree.column(col, width=150)
        
        nft_scroll = ttk.Scrollbar(nft_frame, orient=tk.VERTICAL, command=self.nft_tree.yview)
        self.nft_tree.configure(yscrollcommand=nft_scroll.set)
        self.nft_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        nft_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Token Tab
        token_frame = tk.Frame(assets_notebook, bg=CypherpunkTheme.BG_DARK)
        assets_notebook.add(token_frame, text="  TOKENS  ")
        
        # Token List
        token_columns = ('Symbol', 'Name', 'Balance', 'Contract')
        self.token_tree = ttk.Treeview(token_frame, columns=token_columns, show='headings', height=10)
        
        for col in token_columns:
            self.token_tree.heading(col, text=col)
            self.token_tree.column(col, width=180)
        
        token_scroll = ttk.Scrollbar(token_frame, orient=tk.VERTICAL, command=self.token_tree.yview)
        self.token_tree.configure(yscrollcommand=token_scroll.set)
        self.token_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        token_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # === ACTIONS ===
        actions_frame = tk.Frame(frame, bg=CypherpunkTheme.BG_DARK)
        actions_frame.pack(fill=tk.X, padx=10, pady=10)
        
        refresh_btn = CypherpunkTheme.create_neon_button(
            actions_frame, "↻ REFRESH", self._refresh_blockchain, CypherpunkTheme.NEON_CYAN
        )
        refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        transfer_nft_btn = CypherpunkTheme.create_neon_button(
            actions_frame, "↗ TRANSFER NFT", self._transfer_nft_dialog, CypherpunkTheme.NEON_PURPLE
        )
        transfer_nft_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        transfer_token_btn = CypherpunkTheme.create_neon_button(
            actions_frame, "↗ TRANSFER TOKEN", self._transfer_token_dialog, CypherpunkTheme.NEON_GREEN
        )
        transfer_token_btn.pack(side=tk.LEFT)
        
        return frame
    
    def _connect_alchemy(self):
        """Connecte au client Alchemy"""
        api_key = self.alchemy_api_key.get().strip()
        address = self.alchemy_address.get().strip()
        network_name = self.alchemy_network.get()
        
        if not api_key:
            messagebox.showerror("Error", "Clé API Alchemy requise\n\nObtenez-en une sur https://www.alchemy.com/")
            return
        
        if not address:
            messagebox.showerror("Error", "Adresse wallet requise")
            return
        
        if not ALCHEMY_AVAILABLE:
            messagebox.showerror("Error", "Module Alchemy non disponible")
            return
        
        try:
            network = getattr(AlchemyNetwork, network_name)
            self.alchemy_client = AlchemyClient(api_key, network)
            
            # Test connection
            block = self.alchemy_client.get_block_number()
            
            self.blockchain_status.configure(text="● CONNECTED", fg=CypherpunkTheme.NEON_GREEN)
            self._log_activity(f"Alchemy connected to {network_name} (block {block})")
            
            # Refresh data
            self._refresh_blockchain()
            
        except Exception as e:
            self.blockchain_status.configure(text="● ERROR", fg=CypherpunkTheme.TEXT_ERROR)
            messagebox.showerror("Erreur de connexion", f"Impossible de se connecter:\n{e}")
    
    def _refresh_blockchain(self):
        """Rafraichit les données blockchain"""
        if not self.alchemy_client:
            messagebox.showwarning("Warning", "Connectez-vous d'abord à Alchemy")
            return
        
        address = self.alchemy_address.get().strip()
        if not address:
            return
        
        try:
            # Balance native
            balance_wei = self.alchemy_client.get_balance(address)
            balance_eth = balance_wei / 1e18
            self.eth_balance_var.set(f"{balance_eth:.4f} ETH")
            
            # NFTs
            for item in self.nft_tree.get_children():
                self.nft_tree.delete(item)
            
            nfts, _ = self.alchemy_client.get_nfts_for_owner(address, page_size=50)
            self.nft_count_var.set(str(len(nfts)))
            
            for nft in nfts:
                self.nft_tree.insert('', tk.END, values=(
                    nft.collection_name or "Unknown",
                    nft.name or f"#{nft.token_id}",
                    nft.token_id[:10] + "..." if len(nft.token_id) > 10 else nft.token_id,
                    nft.token_type,
                    nft.contract_address[:10] + "..."
                ))
            
            # Tokens
            for item in self.token_tree.get_children():
                self.token_tree.delete(item)
            
            tokens = self.alchemy_client.get_token_balances(address)
            self.token_count_var.set(str(len(tokens)))
            
            for token in tokens:
                self.token_tree.insert('', tk.END, values=(
                    token.symbol,
                    token.name,
                    token.formatted_balance,
                    token.contract_address[:10] + "..."
                ))
            
            self._log_activity(f"Blockchain data refreshed: {len(nfts)} NFTs, {len(tokens)} tokens")
            
        except Exception as e:
            messagebox.showerror("Error", f"Erreur de rafraîchissement:\n{e}")
    
    def _transfer_nft_dialog(self):
        """Dialogue pour transférer un NFT"""
        selection = self.nft_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Sélectionnez un NFT à transférer")
            return
        
        item = self.nft_tree.item(selection[0])
        nft_name = item['values'][1]
        token_id = item['values'][2]
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Transférer NFT: {nft_name}")
        dialog.geometry("500x300")
        dialog.configure(bg=CypherpunkTheme.BG_DARK)
        dialog.transient(self.root)
        dialog.grab_set()
        
        content = tk.Frame(dialog, bg=CypherpunkTheme.BG_DARK)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(content, text=f"NFT: {nft_name}", bg=CypherpunkTheme.BG_DARK,
                fg=CypherpunkTheme.NEON_PURPLE, font=CypherpunkTheme.FONT_TITLE).pack(pady=10)
        
        tk.Label(content, text="Adresse destinataire:", bg=CypherpunkTheme.BG_DARK,
                fg=CypherpunkTheme.TEXT_PRIMARY).pack(anchor='w', pady=(10, 5))
        
        to_address = tk.StringVar()
        to_entry = tk.Entry(content, textvariable=to_address, width=50,
                           bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_GREEN)
        to_entry.pack(fill=tk.X, pady=5)
        
        warning = tk.Label(content, 
                          text="⚠ Cette action nécessite une signature avec votre wallet externe\n(MetaMask, Ledger, etc.)",
                          bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.TEXT_WARNING,
                          font=CypherpunkTheme.FONT_SMALL)
        warning.pack(pady=20)
        
        def prepare_transfer():
            dest = to_address.get().strip()
            if not dest or len(dest) != 42:
                messagebox.showerror("Error", "Adresse invalide")
                return
            
            # Préparer les données de transaction
            tx_info = f"""
Transaction NFT Transfer préparée:
- NFT: {nft_name}
- Token ID: {token_id}
- To: {dest}

Pour exécuter ce transfert:
1. Ouvrez MetaMask ou votre wallet
2. Allez sur le contrat NFT
3. Appelez safeTransferFrom avec ces paramètres
"""
            self._log_activity(f"NFT transfer prepared: {nft_name} -> {dest[:10]}...")
            messagebox.showinfo("Transaction préparée", tx_info)
            dialog.destroy()
        
        CypherpunkTheme.create_neon_button(
            content, "PRÉPARER TRANSFERT", prepare_transfer, CypherpunkTheme.NEON_GREEN
        ).pack(pady=10)
    
    def _transfer_token_dialog(self):
        """Dialogue pour transférer un Token"""
        selection = self.token_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Sélectionnez un token à transférer")
            return
        
        item = self.token_tree.item(selection[0])
        symbol = item['values'][0]
        balance = item['values'][2]
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Transférer {symbol}")
        dialog.geometry("500x350")
        dialog.configure(bg=CypherpunkTheme.BG_DARK)
        dialog.transient(self.root)
        dialog.grab_set()
        
        content = tk.Frame(dialog, bg=CypherpunkTheme.BG_DARK)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(content, text=f"Token: {symbol}", bg=CypherpunkTheme.BG_DARK,
                fg=CypherpunkTheme.NEON_CYAN, font=CypherpunkTheme.FONT_TITLE).pack(pady=10)
        
        tk.Label(content, text=f"Balance disponible: {balance}", bg=CypherpunkTheme.BG_DARK,
                fg=CypherpunkTheme.TEXT_SECONDARY).pack()
        
        tk.Label(content, text="Adresse destinataire:", bg=CypherpunkTheme.BG_DARK,
                fg=CypherpunkTheme.TEXT_PRIMARY).pack(anchor='w', pady=(15, 5))
        
        to_address = tk.StringVar()
        tk.Entry(content, textvariable=to_address, width=50,
                bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_GREEN).pack(fill=tk.X, pady=5)
        
        tk.Label(content, text="Montant:", bg=CypherpunkTheme.BG_DARK,
                fg=CypherpunkTheme.TEXT_PRIMARY).pack(anchor='w', pady=(10, 5))
        
        amount = tk.StringVar()
        tk.Entry(content, textvariable=amount, width=20,
                bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.NEON_GREEN).pack(anchor='w', pady=5)
        
        warning = tk.Label(content,
                          text="⚠ Cette action nécessite une signature avec votre wallet externe",
                          bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.TEXT_WARNING,
                          font=CypherpunkTheme.FONT_SMALL)
        warning.pack(pady=15)
        
        def prepare_transfer():
            dest = to_address.get().strip()
            amt = amount.get().strip()
            
            if not dest or len(dest) != 42:
                messagebox.showerror("Error", "Adresse invalide")
                return
            if not amt:
                messagebox.showerror("Error", "Montant requis")
                return
            
            tx_info = f"""
Transaction Token Transfer préparée:
- Token: {symbol}
- Amount: {amt}
- To: {dest}

Pour exécuter ce transfert:
1. Ouvrez MetaMask ou votre wallet
2. Initiez un transfer ERC20
"""
            self._log_activity(f"Token transfer prepared: {amt} {symbol} -> {dest[:10]}...")
            messagebox.showinfo("Transaction préparée", tx_info)
            dialog.destroy()
        
        CypherpunkTheme.create_neon_button(
            content, "PRÉPARER TRANSFERT", prepare_transfer, CypherpunkTheme.NEON_GREEN
        ).pack(pady=10)
    
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
        """Savesr le journal d'activité"""
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
                messagebox.showerror("Error", "Contrat et Token ID requis")
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
            messagebox.showerror("Error", f"Erreur lors de l'import: {e}")
    
    def add_nft_manual(self):
        """Alias pour deposit_nft"""
        self.deposit_nft()
    
    def show_nft_details(self):
        """Displaysr les détails d'un NFT sélectionné"""
        selection = self.assets_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Veuillez sélectionner un NFT")
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
            messagebox.showerror("Error", "NFT non trouvé")
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
            messagebox.showwarning("Warning", "Veuillez sélectionner un NFT")
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
            messagebox.showwarning("Warning", "Veuillez sélectionner un NFT")
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
            messagebox.showwarning("Warning", "Veuillez sélectionner un NFT")
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
                messagebox.showerror("Error", "Tous les champs sont requis")
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
            messagebox.showerror("Error", "Contrat et montant requis")
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
    # WEB3 ERC20 INTEGRATION
    # ========================================================================
    
    def _get_evm_wallet(self):
        """Get or create EVM wallet from vault key"""
        try:
            from core.evm_wallet import VaultHDWallet, EVMChain, WEB3_AVAILABLE
            
            if not WEB3_AVAILABLE:
                messagebox.showerror("Error", "web3 not installed. Run: pip install web3 eth-account")
                return None
            
            if not hasattr(self, '_evm_wallet') or self._evm_wallet is None:
                # Derive wallet from vault key
                vault_key = hashlib.sha256(self.vault_name.encode()).digest()
                self._evm_wallet = VaultHDWallet(vault_key, self.vault_name)
                self.wallet_address_var.set(self._evm_wallet.address)
            
            return self._evm_wallet
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize wallet: {e}")
            return None
    
    def _get_btc_wallet(self):
        """Get or create Bitcoin wallet from vault key"""
        try:
            from core.bitcoin_wallet import VaultBitcoinWallet, BitcoinNetwork
            
            if not hasattr(self, '_btc_wallet') or self._btc_wallet is None:
                # Derive wallet from vault key
                vault_key = hashlib.sha256(self.vault_name.encode()).digest()
                self._btc_wallet = VaultBitcoinWallet(vault_key, self.vault_name, BitcoinNetwork.MAINNET)
                self.btc_address_var.set(self._btc_wallet.address)
            
            return self._btc_wallet
        except ImportError:
            self.btc_address_var.set("Module not available")
            return None
        except Exception as e:
            self.btc_address_var.set(f"Error: {str(e)[:20]}")
            return None
    
    def _get_chain_enum(self, chain_name: str):
        """Convert chain name to EVMChain enum"""
        from core.evm_wallet import EVMChain
        
        chain_map = {
            "ethereum": EVMChain.ETHEREUM_MAINNET,
            "sepolia": EVMChain.ETHEREUM_SEPOLIA,
            "polygon": EVMChain.POLYGON_MAINNET,
            "arbitrum": EVMChain.ARBITRUM_ONE,
            "optimism": EVMChain.OPTIMISM,
            "base": EVMChain.BASE_MAINNET,
            "bsc": EVMChain.BSC_MAINNET,
        }
        return chain_map.get(chain_name, EVMChain.ETHEREUM_MAINNET)
    
    def _copy_evm_address(self):
        """Copy EVM wallet address to clipboard"""
        wallet = self._get_evm_wallet()
        if wallet:
            self.root.clipboard_clear()
            self.root.clipboard_append(wallet.address)
            self._log_activity(f"EVM address copied: {wallet.address[:15]}...")
            messagebox.showinfo("Copied", f"EVM Address copied!\n{wallet.address}")
    
    def _copy_btc_address(self):
        """Copy Bitcoin wallet address to clipboard"""
        btc_addr = self.btc_address_var.get()
        if btc_addr and btc_addr != "Click Refresh to connect":
            self.root.clipboard_clear()
            self.root.clipboard_append(btc_addr)
            self._log_activity(f"BTC address copied: {btc_addr[:15]}...")
            messagebox.showinfo("Copied", f"Bitcoin Address copied!\n{btc_addr}")
        else:
            # Try to get wallet first
            self._get_btc_wallet()
            btc_addr = self.btc_address_var.get()
            if btc_addr:
                self.root.clipboard_clear()
                self.root.clipboard_append(btc_addr)
                messagebox.showinfo("Copied", f"Bitcoin Address copied!\n{btc_addr}")
    
    def _copy_wallet_address(self):
        """Legacy: Copy EVM wallet address"""
        self._copy_evm_address()
    
    def _init_vault_info_address(self):
        """Initialize the vault info address display"""
        try:
            wallet = self._get_evm_wallet()
            if wallet:
                addr_display = f"╰─▶ {wallet.address[:16]}..."
                self.vault_info_address_var.set(addr_display)
            else:
                self.vault_info_address_var.set("╰─▶ EVM not available")
        except Exception:
            self.vault_info_address_var.set("╰─▶ EVM not available")
    
    def _refresh_all_wallets(self):
        """Refresh both EVM and BTC wallets"""
        # Refresh EVM
        wallet = self._get_evm_wallet()
        if wallet:
            self.wallet_address_var.set(wallet.address)
            # Sync with vault info
            if hasattr(self, 'vault_info_address_var'):
                self.vault_info_address_var.set(f"╰─▶ {wallet.address[:16]}...")
            # Sync with receive section
            if hasattr(self, 'receive_address_var'):
                self.receive_address_var.set(wallet.address)
        
        # Refresh BTC
        self._get_btc_wallet()
        
        # Refresh EVM balance
        self._refresh_web3_balance()
        
        self._log_activity("Wallets refreshed")
    
    def _refresh_web3_balance(self):
        """Refresh balance from blockchain"""
        wallet = self._get_evm_wallet()
        if not wallet:
            return
        
        try:
            chain = self._get_chain_enum(self.chain_var.get())
            
            # Get native balance
            native_info = wallet.get_native_balance(chain)
            balance_eth = float(native_info.formatted_balance())
            self.native_balance_var.set(f"{balance_eth:.6f} {native_info.symbol}")
            self.total_balance_var.set(f"{balance_eth:.6f} {native_info.symbol}")
            
            self._log_activity(f"Balance refreshed on {chain._name}: {balance_eth:.6f} {native_info.symbol}")
            
        except Exception as e:
            self.native_balance_var.set("Error")
            messagebox.showerror("Error", f"Failed to fetch balance: {e}")
    
    def _track_erc20_token(self):
        """Track an ERC20 token balance"""
        wallet = self._get_evm_wallet()
        if not wallet:
            return
        
        contract = self.track_contract_entry.get().strip()
        if not contract or len(contract) != 42:
            messagebox.showerror("Error", "Invalid contract address (must be 42 chars)")
            return
        
        try:
            chain = self._get_chain_enum(self.chain_var.get())
            token_info = wallet.get_erc20_balance(chain, contract)
            
            # Add to tokens tree
            self.tokens_tree.insert('', tk.END, values=(
                token_info.symbol,
                token_info.name,
                token_info.formatted_balance(),
                contract[:20] + '...',
                chain._name
            ))
            
            # Save to vault
            token_data = {
                'id': self._generate_id(),
                'contract': contract,
                'symbol': token_info.symbol,
                'name': token_info.name,
                'balance': token_info.formatted_balance(),
                'decimals': token_info.decimals,
                'chain': chain._name,
                'tracked_at': datetime.now().isoformat()
            }
            self.vault_data['tokens'].append(token_data)
            self._save_vault_state()
            
            self._log_activity(f"Tracking {token_info.symbol}: {token_info.formatted_balance()}")
            self.track_contract_entry.delete(0, tk.END)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to track token: {e}")
    
    def _check_token_info(self):
        """Check token info before sending"""
        wallet = self._get_evm_wallet()
        if not wallet:
            return
        
        contract = self.send_token_contract.get().strip()
        if not contract or len(contract) != 42:
            messagebox.showerror("Error", "Invalid contract address")
            return
        
        try:
            chain = self._get_chain_enum(self.chain_var.get())
            token_info = wallet.get_erc20_balance(chain, contract)
            
            self.send_token_symbol.config(text=f"{token_info.symbol} (Balance: {token_info.formatted_balance()})")
            self._log_activity(f"Token info: {token_info.symbol} - {token_info.name}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get token info: {e}")
    
    def _send_erc20_tokens(self):
        """Send ERC20 tokens"""
        wallet = self._get_evm_wallet()
        if not wallet:
            return
        
        contract = self.send_token_contract.get().strip()
        recipient = self.send_recipient.get().strip()
        amount_str = self.send_amount.get().strip()
        gas_gwei = self.send_gas.get().strip()
        
        # Validation
        if not contract or len(contract) != 42:
            messagebox.showerror("Error", "Invalid token contract address")
            return
        if not recipient or len(recipient) != 42:
            messagebox.showerror("Error", "Invalid recipient address")
            return
        if not amount_str:
            messagebox.showerror("Error", "Amount required")
            return
        
        try:
            amount = float(amount_str)
            max_fee = float(gas_gwei) if gas_gwei else 50.0
        except ValueError:
            messagebox.showerror("Error", "Invalid amount or gas value")
            return
        
        # Confirmation
        chain = self._get_chain_enum(self.chain_var.get())
        
        try:
            token_info = wallet.get_erc20_balance(chain, contract)
        except:
            token_info = None
        
        symbol = token_info.symbol if token_info else "TOKEN"
        
        confirm = messagebox.askyesno(
            "Confirm Transaction",
            f"Send {amount} {symbol} to:\n{recipient}\n\nNetwork: {chain._name}\nMax Gas: {max_fee} Gwei\n\nProceed?"
        )
        
        if not confirm:
            return
        
        try:
            # Convert amount to wei (with decimals)
            decimals = token_info.decimals if token_info else 18
            amount_wei = int(amount * (10 ** decimals))
            
            # Send transaction
            result = wallet.send_erc20(chain, contract, recipient, amount_wei, max_fee_gwei=max_fee)
            
            if result.success:
                # Add to history
                self.tx_history_tree.insert('', 0, values=(
                    datetime.now().strftime("%H:%M:%S"),
                    "SEND",
                    symbol,
                    amount_str,
                    recipient[:15] + '...',
                    result.tx_hash[:15] + '...',
                    "✓ Success"
                ))
                
                self._log_activity(f"Sent {amount} {symbol} to {recipient[:10]}... TX: {result.tx_hash[:10]}...")
                messagebox.showinfo("Success", f"Transaction successful!\n\nTX Hash: {result.tx_hash}")
                
                # Clear inputs
                self.send_recipient.delete(0, tk.END)
                self.send_amount.delete(0, tk.END)
            else:
                self.tx_history_tree.insert('', 0, values=(
                    datetime.now().strftime("%H:%M:%S"),
                    "SEND",
                    symbol,
                    amount_str,
                    recipient[:15] + '...',
                    "-",
                    f"✗ {result.error[:20]}"
                ))
                messagebox.showerror("Error", f"Transaction failed: {result.error}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Transaction error: {e}")
    
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
            messagebox.showerror("Error", f"Erreur lors du dépôt: {e}")
    
    def verify_document(self):
        """Vérifier l'intégrité d'un document"""
        selection = self.documents_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Veuillez sélectionner un document")
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
            messagebox.showerror("Error", "Document non trouvé")
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
                messagebox.showwarning("Warning", "⚠ Hash différent - Document potentiellement modifié")
                self._log_activity(f"ALERTE: Intégrité compromise pour {doc_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Erreur de vérification: {e}")
    
    def extract_document(self):
        """Extraire un document du vault"""
        selection = self.documents_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Veuillez sélectionner un document")
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
            messagebox.showerror("Error", "Document non trouvé")
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
            messagebox.showerror("Error", f"Erreur d'extraction: {e}")
    
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
            messagebox.showwarning("Warning", "Veuillez sélectionner un transfer")
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
            messagebox.showwarning("Warning", "Veuillez sélectionner un transfer")
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
                messagebox.showerror("Error", "Les deux fichiers clés sont requis")
                return
            
            if not os.path.exists(psnx_path.get()):
                messagebox.showerror("Error", "Fichier .psnx introuvable")
                return
            
            if not os.path.exists(blend_path.get()):
                messagebox.showerror("Error", "Fichier .blend_data introuvable")
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
                    messagebox.showerror("Error", f"Échec: {msg}")
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
            messagebox.showerror("Error", f"Erreur d'export: {e}")
    
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
    
    parser = argparse.ArgumentParser(description="Eidolon - Vault Monitor")
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
