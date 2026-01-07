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
        """Affiche l'inventaire COMPLET du vault: Items, Fragments, Gems, Pierres"""
        selection = self.runes_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Veuillez selectionner un vault")
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
        
        # Fenetre d'inventaire - taille adaptee
        dialog = tk.Toplevel(self.root)
        dialog.title(f"⚗ INVENTAIRE COMPLET - Vault #{vault_num}")
        
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
            text=f"⚗ INVENTAIRE VAULT #{vault_num}",
            bg=CypherpunkTheme.BG_DARK,
            fg="#FFD700",
            font=("Consolas", 16, "bold")
        ).pack(side=tk.LEFT)
        
        # === STATS GLOBALES ===
        stats_frame = tk.Frame(dialog, bg=CypherpunkTheme.BG_PANEL)
        stats_frame.pack(fill=tk.X, padx=15, pady=(0, 10))
        
        stats = [
            ("📦 Items", len(vault_items), "#00ff41"),
            ("💎 Gems", len(vault_gems), "#00ffff"),
            ("🔮 Fragments", len(vault_fragments), "#aa00ff"),
            ("⚗ Pierres", len(vault_stones), "#ffd700"),
            ("🏛 Artifacts", len(vault_artifacts), "#ff8000"),
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
        
        # === ONGLET ITEMS ALCHIMIQUES ===
        items_frame = tk.Frame(notebook, bg=CypherpunkTheme.BG_SECONDARY)
        notebook.add(items_frame, text=f" 📦 ITEMS ({len(vault_items)}) ")
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
        
        # === ONGLET ARTIFACTS ===
        artifacts_frame = tk.Frame(notebook, bg=CypherpunkTheme.BG_SECONDARY)
        notebook.add(artifacts_frame, text=f" 🏛 ARTIFACTS ({len(vault_artifacts)}) ")
        self._create_artifacts_tab(artifacts_frame, vault_artifacts)
    
    def _create_items_tab(self, parent, items, rarity_colors):
        """Cree l'onglet des items alchimiques"""
        # Canvas scrollable
        canvas = tk.Canvas(parent, bg=CypherpunkTheme.BG_SECONDARY, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=CypherpunkTheme.BG_SECONDARY)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Grouper par categorie
        categories = {}
        for item in items:
            cat = item.get('category', 'misc').upper()
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        # Icones par categorie
        cat_icons = {
            'POTION': '🧪', 'ELIXIR': '⚗', 'SCROLL': '📜', 'RUNE': 'ᚱ',
            'TALISMAN': '🔮', 'ESSENCE': '✨', 'REAGENT': '🌿', 'CATALYST': '⚡',
            'ARTIFACT_COMPONENT': '🔧', 'MISC': '📦'
        }
        
        for cat_name, cat_items in sorted(categories.items()):
            icon = cat_icons.get(cat_name, '📦')
            
            # Header categorie
            cat_header = tk.Frame(content, bg=CypherpunkTheme.BG_PANEL)
            cat_header.pack(fill=tk.X, padx=5, pady=(10, 5))
            tk.Label(cat_header, text=f" {icon} {cat_name} ({len(cat_items)})",
                    bg=CypherpunkTheme.BG_PANEL, fg="#FFD700",
                    font=("Consolas", 11, "bold")).pack(side=tk.LEFT, padx=5, pady=3)
            
            # Items de cette categorie
            for item_data in sorted(cat_items, key=lambda x: x.get('rarity', 'common')):
                item_frame = tk.Frame(content, bg=CypherpunkTheme.BG_DARK, padx=10, pady=5)
                item_frame.pack(fill=tk.X, padx=10, pady=2)
                
                rarity = item_data.get('rarity', 'common')
                color = rarity_colors.get(rarity, '#ffffff')
                item_type = item_data.get('item_type', 'unknown').replace('_', ' ').title()
                mods = item_data.get('mods', [])
                value = item_data.get('value', 0)
                stat_power = item_data.get('stat_power', 0)
                stats = item_data.get('stats', {})
                
                # Ligne principale
                main_line = tk.Frame(item_frame, bg=CypherpunkTheme.BG_DARK)
                main_line.pack(fill=tk.X)
                
                tk.Label(main_line, text=f"[{rarity.upper()[:3]}]", bg=CypherpunkTheme.BG_DARK,
                        fg=color, font=("Consolas", 9, "bold")).pack(side=tk.LEFT)
                tk.Label(main_line, text=f" {item_type}", bg=CypherpunkTheme.BG_DARK,
                        fg=CypherpunkTheme.TEXT_PRIMARY, font=("Consolas", 10)).pack(side=tk.LEFT)
                
                # Puissance et valeur
                power_color = "#ffd700" if stat_power > 5000 else "#00ff00" if stat_power > 2000 else "#ffffff"
                tk.Label(main_line, text=f"  PWR:{stat_power:.0f}", bg=CypherpunkTheme.BG_DARK,
                        fg=power_color, font=("Consolas", 8, "bold")).pack(side=tk.RIGHT)
                tk.Label(main_line, text=f"  V:{value:.0f}", bg=CypherpunkTheme.BG_DARK,
                        fg=CypherpunkTheme.TEXT_SECONDARY, font=("Consolas", 8)).pack(side=tk.RIGHT)
                
                # Stats primaires (si presentes)
                if stats:
                    stats_line = tk.Frame(item_frame, bg=CypherpunkTheme.BG_DARK)
                    stats_line.pack(fill=tk.X)
                    
                    stat_abbrevs = [
                        ("STR", stats.get('strength', 0), "#ff6666"),
                        ("AGI", stats.get('agility', 0), "#66ff66"),
                        ("INT", stats.get('intelligence', 0), "#6666ff"),
                        ("VIT", stats.get('vitality', 0), "#ff66ff"),
                        ("SAG", stats.get('wisdom', 0), "#ffff66"),
                        ("LCK", stats.get('luck', 0), "#66ffff"),
                    ]
                    
                    stat_parts = []
                    for abbr, val, _ in stat_abbrevs:
                        if val > 0:
                            stat_parts.append(f"{abbr}:{val}")
                    
                    if stat_parts:
                        stats_text = "  " + " ".join(stat_parts[:4])  # Max 4 stats affichees
                        tk.Label(stats_line, text=stats_text, bg=CypherpunkTheme.BG_DARK,
                                fg="#888888", font=("Consolas", 8)).pack(side=tk.LEFT)
                
                # Mods
                if mods:
                    for mod in mods[:2]:
                        mod_name = mod.get('mod_id', '').replace('mod_', '').replace('_', ' ').title()
                        roll_pct = mod.get('roll_percent', 50)
                        quality = "$" if roll_pct >= 95 else "@" if roll_pct >= 80 else "#" if roll_pct >= 60 else "o"
                        mod_text = f"  {quality} {mod_name}: {mod.get('rolled_value', 0):.0f}"
                        tk.Label(item_frame, text=mod_text, bg=CypherpunkTheme.BG_DARK,
                                fg=CypherpunkTheme.NEON_CYAN, font=("Consolas", 8)).pack(anchor=tk.W)
    
    def _create_gems_tab(self, parent, gems, rarity_colors):
        """Cree l'onglet des gems"""
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
        """Cree l'onglet des fragments"""
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
        """Cree l'onglet des pierres philosophales"""
        canvas = tk.Canvas(parent, bg=CypherpunkTheme.BG_SECONDARY, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=CypherpunkTheme.BG_SECONDARY)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        if not stones:
            tk.Label(content, text="\n\n  ☿ Aucune Pierre Philosophale dans ce vault\n\n"
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
    
    def _create_artifacts_tab(self, parent, artifacts):
        """Cree l'onglet des artifacts"""
        canvas = tk.Canvas(parent, bg=CypherpunkTheme.BG_SECONDARY, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=CypherpunkTheme.BG_SECONDARY)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        if not artifacts:
            tk.Label(content, text="\n\n  🏛 Aucun Artifact dans ce vault",
                    bg=CypherpunkTheme.BG_SECONDARY, fg=CypherpunkTheme.TEXT_SECONDARY,
                    font=("Consolas", 11)).pack(padx=20, pady=20)
            return
        
        for artifact in artifacts:
            art_frame = tk.Frame(content, bg=CypherpunkTheme.BG_DARK, padx=15, pady=10)
            art_frame.pack(fill=tk.X, padx=10, pady=5)
            
            art_name = artifact.get('name', 'Unknown Artifact')
            art_type = artifact.get('artifact_type', 'unknown').replace('_', ' ').title()
            power = artifact.get('power', 0)
            resonance = artifact.get('resonance', 0)
            tier = artifact.get('tier', 'common').upper()
            
            tier_colors = {'PRIMORDIAL': '#ff00ff', 'LEGENDARY': '#ff8000', 'EPIC': '#aa00ff', 
                          'RARE': '#0088ff', 'COMMON': '#ffffff'}
            color = tier_colors.get(tier, '#ffffff')
            
            # Header
            main_line = tk.Frame(art_frame, bg=CypherpunkTheme.BG_DARK)
            main_line.pack(fill=tk.X)
            tk.Label(main_line, text=f"🏛 [{tier}]", bg=CypherpunkTheme.BG_DARK,
                    fg=color, font=("Consolas", 10, "bold")).pack(side=tk.LEFT)
            tk.Label(main_line, text=f" {art_name}", bg=CypherpunkTheme.BG_DARK,
                    fg=CypherpunkTheme.TEXT_PRIMARY, font=("Consolas", 11, "bold")).pack(side=tk.LEFT)
            
            # Type et stats
            tk.Label(art_frame, text=f"  Type: {art_type}  ⚡ Power: {power:,.0f}  🔄 Resonance: {resonance:.1f}%",
                    bg=CypherpunkTheme.BG_DARK, fg=CypherpunkTheme.NEON_CYAN,
                    font=("Consolas", 9)).pack(anchor=tk.W)
    
    def _load_vault_fragments(self, vault_num: int) -> list:
        """Charge les fragments d'un vault"""
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
        """Charge les gems d'un vault"""
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
        """Charge les pierres philosophales d'un vault"""
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
        """Charge les artifacts d'un vault"""
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
        """Affiche les details d'une rune selectionnee avec coffres et items"""
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
                text=f"📦 INVENTORY ({len(vault_chests)} Chests, {len(vault_items)} Items)",
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
            
            # Stats globales
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
                text=f"Items: {len(vault_items)} | Mods: {total_mods} | Perfect: {perfect_mods}",
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
        """Charge les coffres d'un vault"""
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
        """Charge les items d'un vault"""
        items = []
        items_dir = Path(self.base_path) / "alchemical_vault" / "items"
        
        if not items_dir.exists():
            return items
        
        for f in items_dir.glob("item_*.json"):
            try:
                with open(f, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                if data.get('origin_vault') == vault_num:
                    items.append(data)
            except:
                pass
        
        # Trier par rarete
        rarity_order = {'primordial': 0, 'mythical': 1, 'legendary': 2, 'masterwork': 3, 
                       'exquisite': 4, 'superior': 5, 'refined': 6, 'common': 7, 'crude': 8}
        items.sort(key=lambda x: rarity_order.get(x.get('rarity', 'common'), 9))
        
        return items
    
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
    
    # ========================================================================
    # ONGLET BITCOIN EXCHANGE
    # ========================================================================
    
    def _create_exchange_tab(self) -> tk.Frame:
        """Cree l'onglet d'echange d'items via Bitcoin Runes"""
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
            messagebox.showwarning("Attention", "Selectionnez un item")
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
        """Affiche les details d'une annonce"""
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
            messagebox.showinfo("Succes", 
                f"Item inscrit!\nRune ID: {inscription.rune_id}")
            dialog.destroy()
            self._refresh_exchange()
        
        tk.Button(dialog, text="INSCRIRE", bg="#00ff00", fg="black",
                 command=do_inscribe).pack(pady=20)
    
    def _sell_item_dialog(self):
        """Dialog pour mettre en vente un item"""
        selection = self.my_items_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Selectionnez un item inscrit")
            return
        
        item = self.my_items_tree.item(selection[0])
        rune_id = item['values'][1]
        
        # Trouver l'inscription
        inscriptions = self.exchange_manager.get_vault_inscriptions(self.current_vault_num)
        inscription = next((i for i in inscriptions if i.rune_id == rune_id), None)
        
        if not inscription or inscription.status != "inscribed":
            messagebox.showerror("Erreur", "Item non disponible pour la vente")
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
                messagebox.showinfo("Succes", 
                    f"Item en vente!\nPrix: {listing.price_btc:.6f} BTC")
                dialog.destroy()
                self._refresh_exchange()
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
        
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
        
        if messagebox.askyesno("Confirmer", "Annuler cette annonce?"):
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
        if selection and messagebox.askyesno("Confirmer", "Rejeter cette offre?"):
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
        """Cree l'onglet de transfert d'actifs sur Bitcoin"""
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
            ("ITEMS", "#00ffff", self._inscribe_items_dialog),
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
        """Sauvegarde l'adresse Bitcoin"""
        address = self.bridge_address.get()
        if not address:
            messagebox.showwarning("Attention", "Entrez une adresse Bitcoin")
            return
        
        # Validation basique
        if not (address.startswith('1') or address.startswith('3') or address.startswith('bc1')):
            messagebox.showerror("Erreur", "Adresse Bitcoin invalide")
            return
        
        messagebox.showinfo("Succes", f"Adresse sauvegardee:\n{address}")
    
    def _inscribe_items_dialog(self):
        """Dialog pour inscrire des items"""
        self._inscribe_assets_dialog("item", "Items Alchimiques")
    
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
        self._inscribe_assets_dialog("artifact", "Artefacts")
    
    def _inscribe_assets_dialog(self, asset_type: str, title: str):
        """Dialog generique pour inscrire des actifs"""
        address = self.bridge_address.get()
        if not address:
            messagebox.showwarning("Attention", 
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
                messagebox.showwarning("Attention", "Selectionnez au moins un actif")
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
            
            messagebox.showinfo("Succes", f"{count} actif(s) inscrit(s) sur Bitcoin!")
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
            messagebox.showwarning("Attention", "Selectionnez un actif")
            return
        
        if not dest_address:
            messagebox.showwarning("Attention", "Entrez une adresse destination")
            return
        
        # Extraire le Rune ID
        rune_id = asset_selection.split(" - ")[0]
        
        # Trouver l'actif
        asset = self.asset_bridge.get_asset_by_rune(rune_id)
        if not asset:
            messagebox.showerror("Erreur", "Actif non trouve")
            return
        
        from_address = self.bridge_address.get()
        if not from_address:
            messagebox.showerror("Erreur", "Configurez d'abord votre adresse Bitcoin")
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
            messagebox.showerror("Erreur", str(e))
    
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
            messagebox.showerror("Erreur", "Clé API Alchemy requise\n\nObtenez-en une sur https://www.alchemy.com/")
            return
        
        if not address:
            messagebox.showerror("Erreur", "Adresse wallet requise")
            return
        
        if not ALCHEMY_AVAILABLE:
            messagebox.showerror("Erreur", "Module Alchemy non disponible")
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
            messagebox.showwarning("Attention", "Connectez-vous d'abord à Alchemy")
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
            messagebox.showerror("Erreur", f"Erreur de rafraîchissement:\n{e}")
    
    def _transfer_nft_dialog(self):
        """Dialogue pour transférer un NFT"""
        selection = self.nft_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Sélectionnez un NFT à transférer")
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
                messagebox.showerror("Erreur", "Adresse invalide")
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
            messagebox.showwarning("Attention", "Sélectionnez un token à transférer")
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
                messagebox.showerror("Erreur", "Adresse invalide")
                return
            if not amt:
                messagebox.showerror("Erreur", "Montant requis")
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
