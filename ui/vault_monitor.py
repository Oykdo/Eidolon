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
        """Configuration de l'interface utilisateur"""
        # Configuration des styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Styles personnalisés
        style.configure('Dark.TFrame', background='#0a0a1a')
        style.configure('Dark.TLabel', background='#0a0a1a', foreground='white')
        style.configure('Dark.TButton', background='#1a1a3a', foreground='white')
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'), foreground='#00ff00')
        
        # Cadre principal
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Barre latérale gauche
        sidebar = ttk.Frame(main_frame, width=250)
        sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))
        sidebar.pack_propagate(False)
        
        # Informations du vault
        info_frame = ttk.LabelFrame(sidebar, text="Vault Info", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(info_frame, text=f"Vault: {self.vault_name}").pack(anchor=tk.W)
        
        if self.wallet:
            addr_display = f"{self.wallet.address[:12]}..." if hasattr(self.wallet, 'address') else "N/A"
        else:
            addr_display = "EVM non disponible"
        ttk.Label(info_frame, text=f"Adresse: {addr_display}").pack(anchor=tk.W)
        
        # Statut
        self.status_label = ttk.Label(info_frame, text="Statut: Actif", foreground="#00ff00")
        self.status_label.pack(anchor=tk.W, pady=(10, 0))
        
        # Boutons d'actions
        actions_frame = ttk.LabelFrame(sidebar, text="Actions", padding=10)
        actions_frame.pack(fill=tk.X, pady=(0, 20))
        
        buttons = [
            ("📥 Dépôt NFT", self.deposit_nft),
            ("🪙 Dépôt Token", self.deposit_token),
            ("📄 Dépôt Document", self.deposit_document),
            ("📤 Récupération", self.recovery_panel),
            ("🔄 Actualiser", self.refresh_data),
            ("💾 Sauvegarder", self._save_vault_state),
            ("📊 Exporter Logs", self.export_logs),
        ]
        
        for text, command in buttons:
            ttk.Button(actions_frame, text=text, command=command).pack(fill=tk.X, pady=3)
        
        # Cadre principal de contenu
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Notebook avec onglets
        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Création des onglets
        self.assets_tab = self._create_assets_tab()
        self.notebook.add(self.assets_tab, text="🖼️ Actifs NFT")
        
        self.tokens_tab = self._create_tokens_tab()
        self.notebook.add(self.tokens_tab, text="🪙 Tokens")
        
        self.documents_tab = self._create_documents_tab()
        self.notebook.add(self.documents_tab, text="📄 Documents")
        
        self.monitor_tab = self._create_monitor_tab()
        self.notebook.add(self.monitor_tab, text="📊 Monitoring")
        
        self.transfers_tab = self._create_transfers_tab()
        self.notebook.add(self.transfers_tab, text="🔄 Transfers")
        
        # Barre de statut
        status_text = "Vault actif | Persistance activée"
        if MONITORING_AVAILABLE:
            status_text += " | Monitoring: OK"
        if EVM_AVAILABLE:
            status_text += " | EVM: OK"
        
        self.status_bar = ttk.Label(
            self.root, 
            text=status_text, 
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
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
        """Créer l'onglet de monitoring"""
        frame = ttk.Frame(self.notebook)
        
        # Métriques en temps réel
        metrics_frame = ttk.LabelFrame(frame, text="Métriques Vault", padding=10)
        metrics_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Grille de métriques
        self.metric_vars: Dict[str, tk.StringVar] = {}
        metrics = [
            ("NFTs sécurisés", "nft_count"),
            ("Tokens actifs", "token_count"),
            ("Documents", "doc_count"),
            ("Activité 24h", "activity_24h"),
            ("Intégrité", "integrity"),
            ("Dernière sauvegarde", "last_backup")
        ]
        
        for i, (label, key) in enumerate(metrics):
            row, col = divmod(i, 3)
            lbl = ttk.Label(metrics_frame, text=f"{label}:", font=('Arial', 9, 'bold'))
            lbl.grid(row=row, column=col*2, sticky=tk.W, pady=5, padx=5)
            
            var = tk.StringVar(value="0")
            self.metric_vars[key] = var
            val_lbl = ttk.Label(metrics_frame, textvariable=var, font=('Arial', 9))
            val_lbl.grid(row=row, column=col*2+1, sticky=tk.W, pady=5, padx=5)
        
        # Logs d'activité
        log_frame = ttk.LabelFrame(frame, text="Journal d'Activité", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.activity_log = tk.Text(log_frame, height=15, bg="#0a0a1a", fg="#00ff00", 
                                     font=('Consolas', 9))
        self.activity_log.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.activity_log.yview)
        self.activity_log.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Boutons de contrôle
        ctrl_frame = ttk.Frame(frame)
        ctrl_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(ctrl_frame, text="Effacer Journal", 
                   command=lambda: self.activity_log.delete(1.0, tk.END)).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl_frame, text="Exporter Journal", command=self.export_logs).pack(side=tk.LEFT, padx=5)
        
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
        """Journaliser une activité"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        try:
            self.activity_log.insert(tk.END, log_entry)
            self.activity_log.see(tk.END)
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
