#!/usr/bin/env python
"""
Poly-Spinor Nexus 7D - Interface Graphique Vault Complete
Authentification par double fichier: .psnx (donnees crypto) + .blend_data (visualisation)

Les deux fichiers sont necessaires pour deverrouiller le vault:
- .psnx: Contient les donnees cryptographiques compressees
- .blend_data: Contient la structure 3D pour verification
"""

import os
import sys
import json
import secrets
import hashlib
import threading
import zlib
import struct
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import base64

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    from core.complete_key_generator import (
        CompletePolySpinorKeyGenerator,
        CompleteKeyFileGenerator,
        CompleteKeyData,
        generate_complete_key,
        BLENDER_AVAILABLE
    )
    GENERATOR_AVAILABLE = True
except ImportError as e:
    GENERATOR_AVAILABLE = False
    print(f"[AVERTISSEMENT] Generateur non disponible: {e}")

try:
    from core.evm_wallet import (
        VaultHDWallet, VaultAssetManager, EVMChain,
        TokenInfo, NFTInfo, TransactionResult, WEB3_AVAILABLE
    )
    EVM_AVAILABLE = WEB3_AVAILABLE
except ImportError as e:
    EVM_AVAILABLE = False
    print(f"[INFO] Module EVM non disponible: {e}")


# ============================================================================
# CLASSES DE DONNEES
# ============================================================================

@dataclass
class VaultObject:
    """Objet stocke dans le vault"""
    object_id: str
    name: str
    object_type: str
    size_bytes: int
    encrypted_data: bytes
    metadata: Dict[str, Any]
    created_at: str
    modified_at: str
    checksum: str
    tags: List[str]
    
    def to_dict(self) -> Dict:
        return {
            'object_id': self.object_id,
            'name': self.name,
            'object_type': self.object_type,
            'size_bytes': self.size_bytes,
            'encrypted_data': base64.b64encode(self.encrypted_data).decode(),
            'metadata': self.metadata,
            'created_at': self.created_at,
            'modified_at': self.modified_at,
            'checksum': self.checksum,
            'tags': self.tags
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> 'VaultObject':
        return cls(
            object_id=d['object_id'],
            name=d['name'],
            object_type=d['object_type'],
            size_bytes=d['size_bytes'],
            encrypted_data=base64.b64decode(d['encrypted_data']),
            metadata=d['metadata'],
            created_at=d['created_at'],
            modified_at=d['modified_at'],
            checksum=d['checksum'],
            tags=d.get('tags', [])
        )


class DualKeyAuthenticator:
    """Authentificateur a double cle (PSNX + BLEND_DATA)"""
    
    PSNX_MARKER = b'PSNX7D_COMPLETE_V2'
    BLEND_DATA_FORMAT = 'PSNX_BLEND_DATA'
    
    def __init__(self):
        self.psnx_path: Optional[str] = None
        self.blend_data_path: Optional[str] = None
        self.key_data: Optional[CompleteKeyData] = None
        self.vault_key: Optional[bytes] = None
        self.is_authenticated = False
    
    def validate_psnx_file(self, path: str) -> Tuple[bool, str]:
        """Valide un fichier .psnx"""
        if not os.path.exists(path):
            return False, "Fichier non trouve"
        
        try:
            with open(path, 'rb') as f:
                marker = f.read(len(self.PSNX_MARKER))
                if marker != self.PSNX_MARKER:
                    return False, "Format PSNX invalide"
            return True, "Fichier PSNX valide"
        except Exception as e:
            return False, f"Erreur lecture: {e}"
    
    def validate_blend_data_file(self, path: str) -> Tuple[bool, str]:
        """Valide un fichier .blend_data"""
        if not os.path.exists(path):
            return False, "Fichier non trouve"
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('format') != self.BLEND_DATA_FORMAT:
                return False, "Format BLEND_DATA invalide"
            
            # Verifier les champs requis
            required = ['key_id', 'clusters', 'key_polyhedra', 'crypto_properties']
            for field in required:
                if field not in data:
                    return False, f"Champ manquant: {field}"
            
            return True, "Fichier BLEND_DATA valide"
        except json.JSONDecodeError:
            return False, "JSON invalide"
        except Exception as e:
            return False, f"Erreur lecture: {e}"
    
    def verify_key_match(self, psnx_path: str, blend_data_path: str) -> Tuple[bool, str]:
        """Verifie que les deux fichiers correspondent"""
        try:
            # Lire le key_id du fichier PSNX
            with open(psnx_path, 'rb') as f:
                f.read(len(self.PSNX_MARKER))  # Skip marker
                length = struct.unpack('>I', f.read(4))[0]
                compressed = f.read(length)
            
            json_bytes = zlib.decompress(compressed)
            psnx_data = json.loads(json_bytes.decode('utf-8'))
            psnx_key_id = psnx_data['key_data']['key_id']
            
            # Lire le key_id du fichier BLEND_DATA
            with open(blend_data_path, 'r', encoding='utf-8') as f:
                blend_data = json.load(f)
            blend_key_id = blend_data.get('key_id', '')
            
            if psnx_key_id != blend_key_id:
                return False, f"Key ID mismatch: {psnx_key_id[:8]}... vs {blend_key_id[:8]}..."
            
            return True, f"Correspondance verifiee: {psnx_key_id}"
            
        except Exception as e:
            return False, f"Erreur verification: {e}"
    
    def authenticate(self, psnx_path: str, blend_data_path: str) -> Tuple[bool, str]:
        """Authentifie avec les deux fichiers"""
        
        # Valider PSNX
        valid, msg = self.validate_psnx_file(psnx_path)
        if not valid:
            return False, f"PSNX: {msg}"
        
        # Valider BLEND_DATA
        valid, msg = self.validate_blend_data_file(blend_data_path)
        if not valid:
            return False, f"BLEND_DATA: {msg}"
        
        # Verifier correspondance
        valid, msg = self.verify_key_match(psnx_path, blend_data_path)
        if not valid:
            return False, msg
        
        # Extraire la cle vault
        try:
            generator = CompletePolySpinorKeyGenerator()
            file_gen = CompleteKeyFileGenerator(generator)
            
            self.key_data, self.vault_key = file_gen.extract_key_from_file(psnx_path)
            self.psnx_path = psnx_path
            self.blend_data_path = blend_data_path
            self.is_authenticated = True
            
            return True, f"Authentification reussie! Entropie: {self.key_data.total_entropy_bits:,} bits"
            
        except Exception as e:
            return False, f"Erreur extraction cle: {e}"
    
    def get_vault_info(self) -> Dict[str, Any]:
        """Retourne les informations du vault"""
        if not self.is_authenticated or not self.key_data:
            return {}
        
        return {
            'key_id': self.key_data.key_id,
            'user_name': self.key_data.user_name,
            'created_at': self.key_data.created_at,
            'entropy_bits': self.key_data.total_entropy_bits,
            'bell_quantum': self.key_data.bell_data.is_quantum,
            'bell_max_violation': self.key_data.bell_data.max_violation,
            'bell_violations': len(self.key_data.bell_data.violations),
            'pq_active': self.key_data.pq_data is not None,
            'spatial_points': self.key_data.spatial_data.total_points,
            'physics_collisions': self.key_data.physics_data.total_collisions,
            'merkle_root': self.key_data.merkle_root[:16] + '...'
        }


class SecureVaultStorage:
    """Stockage securise des objets vault"""
    
    def __init__(self, storage_dir: str, master_key: bytes):
        self.storage_dir = storage_dir
        self.master_key = master_key
        self.objects_dir = os.path.join(storage_dir, 'objects')
        self.index_file = os.path.join(storage_dir, 'vault_index.enc')
        
        os.makedirs(self.objects_dir, exist_ok=True)
        self._index: Dict[str, Dict] = {}
        self._load_index()
    
    def _get_aesgcm(self) -> AESGCM:
        return AESGCM(self.master_key[:32])
    
    def _encrypt(self, data: bytes) -> bytes:
        nonce = secrets.token_bytes(12)
        ciphertext = self._get_aesgcm().encrypt(nonce, data, None)
        return nonce + ciphertext
    
    def _decrypt(self, encrypted_data: bytes) -> bytes:
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]
        return self._get_aesgcm().decrypt(nonce, ciphertext, None)
    
    def _load_index(self):
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'rb') as f:
                    encrypted = f.read()
                decrypted = self._decrypt(encrypted)
                self._index = json.loads(decrypted.decode('utf-8'))
            except Exception:
                self._index = {}
        else:
            self._index = {}
    
    def _save_index(self):
        data = json.dumps(self._index).encode('utf-8')
        encrypted = self._encrypt(data)
        with open(self.index_file, 'wb') as f:
            f.write(encrypted)
    
    def store_object(self, name: str, data: bytes, object_type: str,
                    metadata: Optional[Dict] = None, tags: Optional[List[str]] = None) -> VaultObject:
        """Stocke un nouvel objet"""
        object_id = secrets.token_hex(16)
        now = datetime.utcnow().isoformat()
        checksum = hashlib.sha256(data).hexdigest()
        
        encrypted_data = self._encrypt(data)
        
        obj = VaultObject(
            object_id=object_id,
            name=name,
            object_type=object_type,
            size_bytes=len(data),
            encrypted_data=encrypted_data,
            metadata=metadata or {},
            created_at=now,
            modified_at=now,
            checksum=checksum,
            tags=tags or []
        )
        
        # Sauvegarder
        obj_path = os.path.join(self.objects_dir, f"{object_id}.enc")
        with open(obj_path, 'wb') as f:
            f.write(encrypted_data)
        
        # Mettre a jour l'index
        self._index[object_id] = {
            'name': name,
            'type': object_type,
            'size': len(data),
            'created': now,
            'checksum': checksum,
            'tags': tags or []
        }
        self._save_index()
        
        return obj
    
    def retrieve_object(self, object_id: str) -> Optional[bytes]:
        """Recupere un objet"""
        if object_id not in self._index:
            return None
        
        obj_path = os.path.join(self.objects_dir, f"{object_id}.enc")
        if not os.path.exists(obj_path):
            return None
        
        with open(obj_path, 'rb') as f:
            encrypted = f.read()
        
        return self._decrypt(encrypted)
    
    def delete_object(self, object_id: str) -> bool:
        """Supprime un objet"""
        if object_id not in self._index:
            return False
        
        obj_path = os.path.join(self.objects_dir, f"{object_id}.enc")
        if os.path.exists(obj_path):
            os.remove(obj_path)
        
        del self._index[object_id]
        self._save_index()
        return True
    
    def list_objects(self) -> List[Dict]:
        """Liste tous les objets"""
        return [
            {'id': oid, **info}
            for oid, info in self._index.items()
        ]
    
    def search_objects(self, query: str) -> List[Dict]:
        """Recherche des objets"""
        query = query.lower()
        results = []
        for oid, info in self._index.items():
            if query in info['name'].lower() or query in ' '.join(info.get('tags', [])).lower():
                results.append({'id': oid, **info})
        return results


# ============================================================================
# INTERFACE GRAPHIQUE
# ============================================================================

class VaultCompleteGUI:
    """Interface graphique complete pour le vault"""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Poly-Spinor Nexus 7D - Vault")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Etat
        self.authenticator = DualKeyAuthenticator()
        self.storage: Optional[SecureVaultStorage] = None
        self.evm_wallet: Optional[VaultHDWallet] = None
        self.asset_manager: Optional[VaultAssetManager] = None
        self.psnx_var = tk.StringVar()
        self.blend_var = tk.StringVar()
        self.selected_chain = tk.StringVar(value="ethereum")
        
        # Style
        self.setup_styles()
        
        # Interface
        self.create_login_frame()
        self.main_frame: Optional[ttk.Frame] = None
    
    def setup_styles(self):
        """Configure les styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Couleurs
        style.configure('Title.TLabel', font=('Helvetica', 16, 'bold'))
        style.configure('Header.TLabel', font=('Helvetica', 12, 'bold'))
        style.configure('Info.TLabel', font=('Consolas', 10))
        style.configure('Success.TLabel', foreground='green')
        style.configure('Error.TLabel', foreground='red')
        style.configure('Accent.TButton', font=('Helvetica', 11, 'bold'))
    
    def create_login_frame(self):
        """Cree le cadre de connexion"""
        self.login_frame = ttk.Frame(self.root, padding=20)
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        
        # Titre
        title_frame = ttk.Frame(self.login_frame)
        title_frame.pack(pady=20)
        
        ttk.Label(
            title_frame,
            text="POLY-SPINOR NEXUS 7D",
            style='Title.TLabel'
        ).pack()
        
        ttk.Label(
            title_frame,
            text="Authentification Double Cle",
            font=('Helvetica', 10)
        ).pack(pady=5)
        
        # Illustration
        self.create_key_illustration(self.login_frame)
        
        # Fichiers
        files_frame = ttk.LabelFrame(self.login_frame, text="Fichiers d'authentification", padding=15)
        files_frame.pack(fill=tk.X, pady=20, padx=50)
        
        # Fichier PSNX
        psnx_frame = ttk.Frame(files_frame)
        psnx_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(psnx_frame, text="Fichier PSNX:", width=15).pack(side=tk.LEFT)
        ttk.Entry(psnx_frame, textvariable=self.psnx_var, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(psnx_frame, text="Parcourir...", command=self.browse_psnx).pack(side=tk.LEFT)
        self.psnx_status = ttk.Label(psnx_frame, text="")
        self.psnx_status.pack(side=tk.LEFT, padx=10)
        
        # Fichier BLEND_DATA
        blend_frame = ttk.Frame(files_frame)
        blend_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(blend_frame, text="Fichier BLEND:", width=15).pack(side=tk.LEFT)
        ttk.Entry(blend_frame, textvariable=self.blend_var, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(blend_frame, text="Parcourir...", command=self.browse_blend).pack(side=tk.LEFT)
        self.blend_status = ttk.Label(blend_frame, text="")
        self.blend_status.pack(side=tk.LEFT, padx=10)
        
        # Boutons
        btn_frame = ttk.Frame(self.login_frame)
        btn_frame.pack(pady=20)
        
        ttk.Button(
            btn_frame,
            text="Deverrouiller le Vault",
            style='Accent.TButton',
            command=self.authenticate
        ).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(
            btn_frame,
            text="Generer Nouvelle Cle",
            command=self.generate_new_key
        ).pack(side=tk.LEFT, padx=10)
        
        # Status
        self.status_label = ttk.Label(self.login_frame, text="", style='Info.TLabel')
        self.status_label.pack(pady=10)
    
    def create_key_illustration(self, parent):
        """Cree une illustration des 7 polyedres"""
        if not PIL_AVAILABLE:
            return
        
        canvas_frame = ttk.Frame(parent)
        canvas_frame.pack(pady=10)
        
        # Creer une image des 7 polyedres
        img_size = 400
        img = Image.new('RGB', (img_size, 100), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # Couleurs des materiaux
        colors = [
            '#4a5568',  # tungsten
            '#d69e2e',  # brass
            '#718096',  # titanium
            '#a0aec0',  # steel
            '#e2e8f0',  # aluminum
            '#1a202c',  # obsidian
            '#3182ce',  # sapphire
        ]
        
        labels = ['D4', 'D6', 'D8', 'D10', 'D12', 'D20', 'D100']
        
        # Dessiner les 7 polyedres
        x_start = 30
        spacing = 50
        
        for i, (color, label) in enumerate(zip(colors, labels)):
            x = x_start + i * spacing
            y = 50
            
            # Forme selon le type
            if label == 'D4':  # Triangle
                draw.polygon([(x, y-20), (x-15, y+15), (x+15, y+15)], fill=color, outline='white')
            elif label == 'D6':  # Carre
                draw.rectangle([x-12, y-12, x+12, y+12], fill=color, outline='white')
            elif label in ['D8', 'D20']:  # Losange
                draw.polygon([(x, y-15), (x+15, y), (x, y+15), (x-15, y)], fill=color, outline='white')
            elif label == 'D12':  # Pentagone
                from math import cos, sin, pi
                pts = [(x + 12*cos(2*pi*k/5 - pi/2), y + 12*sin(2*pi*k/5 - pi/2)) for k in range(5)]
                draw.polygon(pts, fill=color, outline='white')
            else:  # Cercle
                draw.ellipse([x-12, y-12, x+12, y+12], fill=color, outline='white')
            
            # Label
            draw.text((x-8, y+20), label, fill='white')
        
        # Convertir en PhotoImage
        self.key_img = ImageTk.PhotoImage(img)
        
        label = ttk.Label(canvas_frame, image=self.key_img)
        label.pack()
    
    def browse_psnx(self):
        """Parcourir pour le fichier PSNX"""
        path = filedialog.askopenfilename(
            title="Selectionner le fichier PSNX",
            filetypes=[("Fichiers PSNX", "*.psnx"), ("Tous", "*.*")]
        )
        if path:
            self.psnx_var.set(path)
            valid, msg = self.authenticator.validate_psnx_file(path)
            if valid:
                self.psnx_status.config(text="OK", style='Success.TLabel')
            else:
                self.psnx_status.config(text="Invalide", style='Error.TLabel')
    
    def browse_blend(self):
        """Parcourir pour le fichier BLEND_DATA"""
        path = filedialog.askopenfilename(
            title="Selectionner le fichier BLEND_DATA",
            filetypes=[("Fichiers BLEND_DATA", "*.blend_data"), ("Tous", "*.*")]
        )
        if path:
            self.blend_var.set(path)
            valid, msg = self.authenticator.validate_blend_data_file(path)
            if valid:
                self.blend_status.config(text="OK", style='Success.TLabel')
            else:
                self.blend_status.config(text="Invalide", style='Error.TLabel')
    
    def authenticate(self):
        """Authentifie l'utilisateur"""
        psnx_path = self.psnx_var.get()
        blend_path = self.blend_var.get()
        
        if not psnx_path or not blend_path:
            messagebox.showerror("Erreur", "Veuillez selectionner les deux fichiers")
            return
        
        self.status_label.config(text="Verification en cours...")
        self.root.update()
        
        # Authentifier dans un thread
        def auth_thread():
            success, msg = self.authenticator.authenticate(psnx_path, blend_path)
            self.root.after(0, lambda: self.on_auth_complete(success, msg))
        
        threading.Thread(target=auth_thread, daemon=True).start()
    
    def on_auth_complete(self, success: bool, message: str):
        """Callback apres authentification"""
        if success:
            self.status_label.config(text=message, style='Success.TLabel')
            
            # Initialiser le stockage
            storage_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'vault_storage', 'data', self.authenticator.key_data.key_id
            )
            self.storage = SecureVaultStorage(storage_dir, self.authenticator.vault_key)
            
            # Initialiser le wallet EVM si disponible
            if EVM_AVAILABLE:
                try:
                    self.evm_wallet = VaultHDWallet(
                        self.authenticator.vault_key,
                        self.authenticator.key_data.key_id
                    )
                    self.asset_manager = VaultAssetManager(
                        self.evm_wallet,
                        os.path.join(storage_dir, 'evm')
                    )
                except Exception as e:
                    print(f"[WARN] Erreur init EVM: {e}")
            
            # Passer a l'interface principale
            self.root.after(1000, self.show_main_interface)
        else:
            self.status_label.config(text=message, style='Error.TLabel')
            messagebox.showerror("Authentification echouee", message)
    
    def generate_new_key(self):
        """Genere une nouvelle paire de cles"""
        if not GENERATOR_AVAILABLE:
            messagebox.showerror("Erreur", "Generateur non disponible")
            return
        
        # Demander le nom d'utilisateur
        user_name = tk.simpledialog.askstring(
            "Nouveau Vault",
            "Entrez votre nom d'utilisateur:"
        )
        if not user_name:
            return
        
        # Choisir le dossier de sortie
        output_dir = filedialog.askdirectory(title="Dossier de sauvegarde des cles")
        if not output_dir:
            return
        
        self.status_label.config(text="Generation en cours... (peut prendre 15-20 secondes)")
        self.root.update()
        
        # Generer dans un thread
        def gen_thread():
            try:
                path, vault_key, entropy, blend_path = generate_complete_key(
                    user_name=user_name,
                    output_dir=output_dir,
                    surface="granite",
                    enable_pq=True,
                    generate_blend=True
                )
                self.root.after(0, lambda: self.on_generation_complete(path, blend_path, entropy))
            except Exception as e:
                self.root.after(0, lambda: self.on_generation_error(str(e)))
        
        threading.Thread(target=gen_thread, daemon=True).start()
    
    def on_generation_complete(self, psnx_path: str, blend_path: str, entropy: int):
        """Callback apres generation"""
        self.psnx_var.set(psnx_path)
        self.blend_var.set(blend_path)
        self.psnx_status.config(text="OK", style='Success.TLabel')
        self.blend_status.config(text="OK", style='Success.TLabel')
        self.status_label.config(
            text=f"Cles generees! Entropie: {entropy:,} bits",
            style='Success.TLabel'
        )
        
        messagebox.showinfo(
            "Cles generees",
            f"Vos fichiers de cle ont ete generes:\n\n"
            f"PSNX: {os.path.basename(psnx_path)}\n"
            f"BLEND: {os.path.basename(blend_path)}\n\n"
            f"Entropie: {entropy:,} bits\n\n"
            f"IMPORTANT: Conservez ces deux fichiers en lieu sur!"
        )
    
    def on_generation_error(self, error: str):
        """Callback en cas d'erreur de generation"""
        self.status_label.config(text=f"Erreur: {error}", style='Error.TLabel')
        messagebox.showerror("Erreur de generation", error)
    
    def show_main_interface(self):
        """Affiche l'interface principale du vault"""
        self.login_frame.pack_forget()
        
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = ttk.Frame(self.main_frame)
        header.pack(fill=tk.X, pady=5)
        
        ttk.Label(
            header,
            text=f"VAULT: {self.authenticator.key_data.user_name}",
            style='Title.TLabel'
        ).pack(side=tk.LEFT)
        
        # Afficher l'adresse EVM si disponible
        if self.evm_wallet:
            ttk.Label(
                header,
                text=f"EVM: {self.evm_wallet.address[:10]}...{self.evm_wallet.address[-8:]}",
                style='Info.TLabel'
            ).pack(side=tk.LEFT, padx=20)
        
        ttk.Button(
            header,
            text="Deconnexion",
            command=self.logout
        ).pack(side=tk.RIGHT)
        
        # Notebook avec onglets
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Onglet Fichiers
        files_tab = ttk.Frame(self.notebook)
        self.notebook.add(files_tab, text="Fichiers")
        
        files_paned = ttk.PanedWindow(files_tab, orient=tk.HORIZONTAL)
        files_paned.pack(fill=tk.BOTH, expand=True)
        
        info_frame = self.create_info_panel(files_paned)
        files_paned.add(info_frame, weight=1)
        
        objects_frame = self.create_objects_panel(files_paned)
        files_paned.add(objects_frame, weight=2)
        
        # Onglet EVM (si disponible)
        if EVM_AVAILABLE and self.evm_wallet:
            evm_tab = ttk.Frame(self.notebook)
            self.notebook.add(evm_tab, text="Crypto (EVM)")
            self.create_evm_panel(evm_tab)
        
        # Charger les objets
        self.refresh_objects_list()
    
    def create_info_panel(self, parent) -> ttk.Frame:
        """Cree le panneau d'informations"""
        frame = ttk.LabelFrame(parent, text="Informations Vault", padding=10)
        
        info = self.authenticator.get_vault_info()
        
        labels = [
            ("Key ID:", info.get('key_id', '')),
            ("Utilisateur:", info.get('user_name', '')),
            ("Cree le:", info.get('created_at', '')[:10]),
            ("", ""),
            ("Entropie:", f"{info.get('entropy_bits', 0):,} bits"),
            ("Bell Quantique:", "Oui" if info.get('bell_quantum') else "Non"),
            ("Violation Max:", f"{info.get('bell_max_violation', 0):.3f}"),
            ("Violations:", str(info.get('bell_violations', 0))),
            ("", ""),
            ("Post-Quantique:", "Actif" if info.get('pq_active') else "Inactif"),
            ("Points Spatiaux:", str(info.get('spatial_points', 0))),
            ("Collisions:", str(info.get('physics_collisions', 0))),
            ("", ""),
            ("Merkle Root:", info.get('merkle_root', '')[:20] + '...')
        ]
        
        for label, value in labels:
            row = ttk.Frame(frame)
            row.pack(fill=tk.X, pady=2)
            if label:
                ttk.Label(row, text=label, width=15).pack(side=tk.LEFT)
                ttk.Label(row, text=value, style='Info.TLabel').pack(side=tk.LEFT)
        
        return frame
    
    def create_objects_panel(self, parent) -> ttk.Frame:
        """Cree le panneau des objets"""
        frame = ttk.LabelFrame(parent, text="Objets du Vault", padding=10)
        
        # Toolbar
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, pady=5)
        
        ttk.Button(toolbar, text="Importer", command=self.import_object).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Exporter", command=self.export_object).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Supprimer", command=self.delete_object).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Rafraichir", command=self.refresh_objects_list).pack(side=tk.LEFT, padx=2)
        
        # Recherche
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side=tk.RIGHT)
        self.search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.search_var, width=20).pack(side=tk.LEFT, padx=2)
        ttk.Button(search_frame, text="Rechercher", command=self.search_objects).pack(side=tk.LEFT)
        
        # Liste
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ('name', 'type', 'size', 'created')
        self.objects_tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        self.objects_tree.heading('name', text='Nom')
        self.objects_tree.heading('type', text='Type')
        self.objects_tree.heading('size', text='Taille')
        self.objects_tree.heading('created', text='Date')
        
        self.objects_tree.column('name', width=200)
        self.objects_tree.column('type', width=100)
        self.objects_tree.column('size', width=80)
        self.objects_tree.column('created', width=100)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.objects_tree.yview)
        self.objects_tree.configure(yscrollcommand=scrollbar.set)
        
        self.objects_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        return frame
    
    def refresh_objects_list(self):
        """Rafraichit la liste des objets"""
        for item in self.objects_tree.get_children():
            self.objects_tree.delete(item)
        
        if not self.storage:
            return
        
        objects = self.storage.list_objects()
        for obj in objects:
            size_str = self.format_size(obj['size'])
            date_str = obj['created'][:10]
            self.objects_tree.insert('', tk.END, iid=obj['id'], values=(
                obj['name'],
                obj['type'],
                size_str,
                date_str
            ))
    
    def format_size(self, size: int) -> str:
        """Formate la taille"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size/1024:.1f} KB"
        else:
            return f"{size/1024/1024:.1f} MB"
    
    def import_object(self):
        """Importe un objet dans le vault"""
        path = filedialog.askopenfilename(title="Importer un fichier")
        if not path:
            return
        
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()
        
        type_map = {
            '.txt': 'text', '.md': 'text',
            '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image',
            '.pdf': 'document', '.doc': 'document', '.docx': 'document',
            '.json': 'data', '.xml': 'data', '.csv': 'data',
            '.key': 'key', '.pem': 'key', '.pub': 'key',
        }
        object_type = type_map.get(ext, 'binary')
        
        try:
            with open(path, 'rb') as f:
                data = f.read()
            
            obj = self.storage.store_object(name, data, object_type)
            self.refresh_objects_list()
            messagebox.showinfo("Import reussi", f"'{name}' importe avec succes")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur d'import: {e}")
    
    def export_object(self):
        """Exporte un objet du vault"""
        selection = self.objects_tree.selection()
        if not selection:
            messagebox.showwarning("Selection", "Selectionnez un objet a exporter")
            return
        
        object_id = selection[0]
        obj_info = None
        for item in self.storage.list_objects():
            if item['id'] == object_id:
                obj_info = item
                break
        
        if not obj_info:
            return
        
        path = filedialog.asksaveasfilename(
            title="Exporter",
            initialfile=obj_info['name']
        )
        if not path:
            return
        
        try:
            data = self.storage.retrieve_object(object_id)
            if data:
                with open(path, 'wb') as f:
                    f.write(data)
                messagebox.showinfo("Export reussi", f"Exporte vers {path}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur d'export: {e}")
    
    def delete_object(self):
        """Supprime un objet du vault"""
        selection = self.objects_tree.selection()
        if not selection:
            messagebox.showwarning("Selection", "Selectionnez un objet a supprimer")
            return
        
        object_id = selection[0]
        
        if messagebox.askyesno("Confirmer", "Supprimer cet objet?"):
            if self.storage.delete_object(object_id):
                self.refresh_objects_list()
                messagebox.showinfo("Supprime", "Objet supprime")
    
    def search_objects(self):
        """Recherche des objets"""
        query = self.search_var.get()
        if not query:
            self.refresh_objects_list()
            return
        
        for item in self.objects_tree.get_children():
            self.objects_tree.delete(item)
        
        results = self.storage.search_objects(query)
        for obj in results:
            size_str = self.format_size(obj['size'])
            date_str = obj['created'][:10]
            self.objects_tree.insert('', tk.END, iid=obj['id'], values=(
                obj['name'],
                obj['type'],
                size_str,
                date_str
            ))
    
    def logout(self):
        """Deconnexion"""
        self.authenticator = DualKeyAuthenticator()
        self.storage = None
        self.evm_wallet = None
        self.asset_manager = None
        
        if self.main_frame:
            self.main_frame.pack_forget()
            self.main_frame = None
        
        self.psnx_var.set("")
        self.blend_var.set("")
        self.psnx_status.config(text="")
        self.blend_status.config(text="")
        self.status_label.config(text="")
        
        self.login_frame.pack(fill=tk.BOTH, expand=True)
    
    # ========================================================================
    # PANNEAU EVM
    # ========================================================================
    
    def create_evm_panel(self, parent):
        """Cree le panneau de gestion des actifs EVM"""
        # Frame principale
        main_frame = ttk.Frame(parent, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Section Wallet
        wallet_frame = ttk.LabelFrame(main_frame, text="Wallet EVM", padding=10)
        wallet_frame.pack(fill=tk.X, pady=5)
        
        # Adresse
        addr_frame = ttk.Frame(wallet_frame)
        addr_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(addr_frame, text="Adresse:", width=12).pack(side=tk.LEFT)
        self.evm_address_var = tk.StringVar(value=self.evm_wallet.address)
        addr_entry = ttk.Entry(addr_frame, textvariable=self.evm_address_var, width=50, state='readonly')
        addr_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(addr_frame, text="Copier", command=self.copy_evm_address).pack(side=tk.LEFT)
        
        # Selection de chaine
        chain_frame = ttk.Frame(wallet_frame)
        chain_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(chain_frame, text="Reseau:", width=12).pack(side=tk.LEFT)
        chains = ["ethereum", "polygon", "arbitrum", "optimism", "bsc", "base", "sepolia"]
        chain_combo = ttk.Combobox(chain_frame, textvariable=self.selected_chain, 
                                   values=chains, state='readonly', width=20)
        chain_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(chain_frame, text="Rafraichir Balance", command=self.refresh_native_balance).pack(side=tk.LEFT, padx=5)
        
        # Balance native
        self.native_balance_var = tk.StringVar(value="Cliquez Rafraichir")
        balance_frame = ttk.Frame(wallet_frame)
        balance_frame.pack(fill=tk.X, pady=5)
        ttk.Label(balance_frame, text="Balance:", width=12).pack(side=tk.LEFT)
        ttk.Label(balance_frame, textvariable=self.native_balance_var, style='Info.TLabel').pack(side=tk.LEFT)
        
        # Section Actions
        actions_frame = ttk.LabelFrame(main_frame, text="Actions", padding=10)
        actions_frame.pack(fill=tk.X, pady=5)
        
        btn_frame = ttk.Frame(actions_frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="Ajouter Token ERC20", command=self.add_erc20_token).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Ajouter NFT", command=self.add_nft).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Envoyer", command=self.send_asset_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Sync Actifs", command=self.sync_assets).pack(side=tk.LEFT, padx=5)
        
        # Liste des actifs
        assets_frame = ttk.LabelFrame(main_frame, text="Actifs EVM", padding=10)
        assets_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        columns = ('name', 'type', 'chain', 'balance', 'address')
        self.assets_tree = ttk.Treeview(assets_frame, columns=columns, show='headings')
        
        self.assets_tree.heading('name', text='Nom')
        self.assets_tree.heading('type', text='Type')
        self.assets_tree.heading('chain', text='Reseau')
        self.assets_tree.heading('balance', text='Balance')
        self.assets_tree.heading('address', text='Contrat')
        
        self.assets_tree.column('name', width=150)
        self.assets_tree.column('type', width=80)
        self.assets_tree.column('chain', width=80)
        self.assets_tree.column('balance', width=100)
        self.assets_tree.column('address', width=150)
        
        scrollbar = ttk.Scrollbar(assets_frame, orient=tk.VERTICAL, command=self.assets_tree.yview)
        self.assets_tree.configure(yscrollcommand=scrollbar.set)
        
        self.assets_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Charger les actifs existants
        self.refresh_assets_list()
    
    def copy_evm_address(self):
        """Copie l'adresse EVM dans le presse-papier"""
        self.root.clipboard_clear()
        self.root.clipboard_append(self.evm_wallet.address)
        messagebox.showinfo("Copie", "Adresse copiee dans le presse-papier")
    
    def get_selected_chain(self) -> EVMChain:
        """Obtient la chaine selectionnee"""
        chain_map = {
            "ethereum": EVMChain.ETHEREUM_MAINNET,
            "sepolia": EVMChain.ETHEREUM_SEPOLIA,
            "polygon": EVMChain.POLYGON_MAINNET,
            "arbitrum": EVMChain.ARBITRUM_ONE,
            "optimism": EVMChain.OPTIMISM,
            "bsc": EVMChain.BSC_MAINNET,
            "base": EVMChain.BASE_MAINNET,
        }
        return chain_map.get(self.selected_chain.get(), EVMChain.ETHEREUM_MAINNET)
    
    def refresh_native_balance(self):
        """Rafraichit le solde natif"""
        self.native_balance_var.set("Chargement...")
        self.root.update()
        
        def fetch():
            try:
                chain = self.get_selected_chain()
                info = self.evm_wallet.get_native_balance(chain)
                balance_str = f"{info.formatted_balance()} {info.symbol}"
                self.root.after(0, lambda: self.native_balance_var.set(balance_str))
            except Exception as e:
                self.root.after(0, lambda: self.native_balance_var.set(f"Erreur: {str(e)[:30]}"))
        
        threading.Thread(target=fetch, daemon=True).start()
    
    def refresh_assets_list(self):
        """Rafraichit la liste des actifs"""
        for item in self.assets_tree.get_children():
            self.assets_tree.delete(item)
        
        if not self.asset_manager:
            return
        
        assets = self.asset_manager.list_assets()
        for asset in assets:
            # Formater la balance
            if asset.asset_type == 'ERC20':
                decimals = asset.metadata.get('decimals', 18)
                from decimal import Decimal
                balance_str = str(Decimal(asset.amount) / Decimal(10 ** decimals))
            else:
                balance_str = str(asset.amount)
            
            # Tronquer l'adresse
            addr_short = f"{asset.contract_address[:8]}...{asset.contract_address[-6:]}"
            
            self.assets_tree.insert('', tk.END, iid=asset.asset_id, values=(
                asset.name,
                asset.asset_type,
                asset.chain,
                balance_str,
                addr_short
            ))
    
    def add_erc20_token(self):
        """Ajoute un token ERC20 au suivi"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Ajouter Token ERC20")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Adresse du contrat:").pack(pady=10)
        contract_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=contract_var, width=50).pack(pady=5)
        
        def add():
            address = contract_var.get().strip()
            if not address:
                messagebox.showerror("Erreur", "Adresse requise")
                return
            
            try:
                chain = self.get_selected_chain()
                asset = self.asset_manager.track_erc20(chain, address)
                self.refresh_assets_list()
                dialog.destroy()
                messagebox.showinfo("Succes", f"Token {asset.symbol} ajoute")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
        
        ttk.Button(dialog, text="Ajouter", command=add).pack(pady=10)
    
    def add_nft(self):
        """Ajoute un NFT au suivi"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Ajouter NFT")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Adresse du contrat:").pack(pady=5)
        contract_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=contract_var, width=50).pack(pady=5)
        
        ttk.Label(dialog, text="Token ID:").pack(pady=5)
        token_id_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=token_id_var, width=20).pack(pady=5)
        
        def add():
            address = contract_var.get().strip()
            token_id_str = token_id_var.get().strip()
            
            if not address or not token_id_str:
                messagebox.showerror("Erreur", "Adresse et Token ID requis")
                return
            
            try:
                token_id = int(token_id_str)
                chain = self.get_selected_chain()
                asset = self.asset_manager.track_nft(chain, address, token_id)
                self.refresh_assets_list()
                dialog.destroy()
                messagebox.showinfo("Succes", f"NFT {asset.name} ajoute")
            except ValueError:
                messagebox.showerror("Erreur", "Token ID doit etre un nombre")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))
        
        ttk.Button(dialog, text="Ajouter", command=add).pack(pady=10)
    
    def send_asset_dialog(self):
        """Dialogue pour envoyer un actif"""
        selection = self.assets_tree.selection()
        if not selection:
            messagebox.showwarning("Selection", "Selectionnez un actif a envoyer")
            return
        
        asset_id = selection[0]
        asset = self.asset_manager.get_asset(asset_id)
        if not asset:
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Envoyer {asset.name}")
        dialog.geometry("450x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text=f"Actif: {asset.name} ({asset.asset_type})").pack(pady=10)
        
        ttk.Label(dialog, text="Adresse destinataire:").pack(pady=5)
        to_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=to_var, width=50).pack(pady=5)
        
        amount_var = tk.StringVar(value="1" if asset.asset_type != 'ERC20' else "")
        if asset.asset_type == 'ERC20':
            ttk.Label(dialog, text="Montant:").pack(pady=5)
            ttk.Entry(dialog, textvariable=amount_var, width=20).pack(pady=5)
        
        status_var = tk.StringVar()
        ttk.Label(dialog, textvariable=status_var).pack(pady=5)
        
        def send():
            to_address = to_var.get().strip()
            if not to_address:
                messagebox.showerror("Erreur", "Adresse destinataire requise")
                return
            
            # Confirmation
            if not messagebox.askyesno("Confirmer", 
                f"Envoyer {asset.name} a {to_address[:10]}...?"):
                return
            
            status_var.set("Envoi en cours...")
            dialog.update()
            
            def do_send():
                try:
                    amount = None
                    if asset.asset_type == 'ERC20' and amount_var.get():
                        decimals = asset.metadata.get('decimals', 18)
                        amount = int(float(amount_var.get()) * (10 ** decimals))
                    
                    result = self.asset_manager.send_asset(asset_id, to_address, amount)
                    
                    if result.success:
                        self.root.after(0, lambda: messagebox.showinfo(
                            "Succes", f"Transaction envoyee!\nTx: {result.tx_hash[:20]}..."
                        ))
                        self.root.after(0, dialog.destroy)
                        self.root.after(100, self.refresh_assets_list)
                    else:
                        self.root.after(0, lambda: status_var.set(f"Erreur: {result.error}"))
                        
                except Exception as e:
                    self.root.after(0, lambda: status_var.set(f"Erreur: {str(e)[:40]}"))
            
            threading.Thread(target=do_send, daemon=True).start()
        
        ttk.Button(dialog, text="Envoyer", command=send).pack(pady=10)
    
    def sync_assets(self):
        """Synchronise tous les actifs"""
        self.native_balance_var.set("Synchronisation...")
        self.root.update()
        
        def do_sync():
            try:
                chain = self.get_selected_chain()
                self.asset_manager.sync_all(chain)
                self.root.after(0, self.refresh_assets_list)
                self.root.after(0, self.refresh_native_balance)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Erreur sync", str(e)))
        
        threading.Thread(target=do_sync, daemon=True).start()


# ============================================================================
# POINT D'ENTREE
# ============================================================================

def main():
    """Point d'entree principal"""
    root = tk.Tk()
    
    # Icone (si disponible)
    try:
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'icon.ico')
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except:
        pass
    
    app = VaultCompleteGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
