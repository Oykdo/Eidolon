# Poly-Spinor Nexus 7D

Systeme cryptographique post-quantique avec vault securise et support EVM.

## Caracteristiques

- **30,900 bits d'entropie** via 9 phases de generation
- **Authentification double-cle** (.psnx + .blend_data)
- **Chiffrement AES-256-GCM** pour le stockage
- **Post-quantique** (McEliece, HQC, ML-DSA, Falcon, SPHINCS+)
- **Verification Bell 7D** des correlations quantiques
- **Wallet EVM integre** (ERC20/ERC721/ERC1155)
- **Support multi-chaines** (Ethereum, Polygon, Arbitrum, etc.)

## Installation

```bash
pip install web3 eth-account pqcrypto pillow cryptography numpy
```

## Lancement

```bash
python launch_vault.py
```

## Structure

```
poly_spinor_nexus_7d/
├── core/                      # Modules principaux
│   ├── spatial_capture.py     # Capture spatiale 7D
│   ├── spinor_crypto.py       # Chiffrement Clifford Cl(0,7)
│   ├── quantum_verification.py # Verification Bell
│   ├── poly_spinor_hash.py    # Hash spinoriel composite
│   ├── physics_engine.py      # Simulation physique
│   ├── material_database.py   # Base materiaux
│   ├── blender_engine.py      # Visualisation Blender
│   ├── complete_key_generator.py # Generateur 9 phases
│   ├── evm_wallet.py          # Wallet EVM
│   ├── real_post_quantum.py   # Crypto PQ reelle
│   ├── secure_key_storage.py  # Stockage cles
│   └── post_quantum_keys.py   # Legacy PQ (compatibilite)
│
├── protocols/                 # Protocoles d'entiercement
│   ├── document_escrow.py     # Entiercement documents
│   ├── escrow_seal.py         # Sceaux multi-autorites
│   ├── escrow_recovery.py     # Recuperation Bell
│   ├── escrow_dashboard.py    # Monitoring sceaux
│   ├── authority_rotation.py  # Rotation autorites
│   ├── emergency_protocol.py  # Acces d'urgence
│   ├── recovery_protocol.py   # Recuperation quantique
│   ├── hyper_cluster.py       # Clusters 7D
│   ├── material_vault.py      # Vault materiel
│   └── vault_monitoring.py    # Surveillance vault
│
├── ui/                        # Interfaces utilisateur
│   ├── vault_gui_complete.py  # Interface principale (tkinter)
│   ├── main_panel.py          # Panneau Blender
│   ├── visualization.py       # Visualisation quantique
│   └── escrow_interface.py    # Interface entiercement
│
├── scripts/                   # Scripts utilitaires
│   └── import_blend_data.py   # Import dans Blender
│
├── tests/                     # Tests unitaires
│   ├── test_real_pq.py
│   ├── test_secure_storage.py
│   └── ...
│
├── vault_storage/             # Stockage vault
│   ├── keys/                  # Fichiers .psnx et .blend_data
│   ├── data/                  # Donnees chiffrees
│   └── avatars/               # Avatars (legacy)
│
└── utils/                     # Utilitaires
    ├── security_audit.py
    ├── backup_system.py
    └── quantum_math.py
```

## Utilisation

### Generer une nouvelle cle

```python
from core.complete_key_generator import generate_complete_key

path, vault_key, entropy, blend_path = generate_complete_key(
    user_name="Alice",
    output_dir="./vault_storage/keys",
    enable_pq=True,
    generate_blend=True
)
print(f"Cle generee: {path}")
print(f"Entropie: {entropy} bits")
```

### Authentification

```python
from ui.vault_gui_complete import DualKeyAuthenticator

auth = DualKeyAuthenticator()
success, msg = auth.authenticate(
    "vault_storage/keys/complete_key_alice.psnx",
    "vault_storage/keys/complete_key_alice.blend_data"
)
if success:
    vault_key = auth.vault_key  # Cle 32 bytes pour AES-256
```

### Wallet EVM

```python
from core.evm_wallet import VaultHDWallet, EVMChain

wallet = VaultHDWallet(vault_key, "alice_vault")
print(f"Adresse: {wallet.address}")

# Balance ETH
balance = wallet.get_native_balance(EVMChain.ETHEREUM_MAINNET)
print(f"Balance: {balance.formatted_balance()} ETH")

# Envoyer des tokens
result = wallet.send_erc20(
    EVMChain.ETHEREUM_MAINNET,
    "0xToken...",
    "0xDest...",
    amount=1000000  # avec decimales
)
```

## Phases de Generation

| Phase | Composant | Entropie |
|-------|-----------|----------|
| 1 | Master Seed | 512 bits |
| 2 | Capture Spatiale 7D | 17,640 bits |
| 3 | Simulation Physique | 1,708 bits |
| 4 | Transformation Spinorielle | 8,192 bits |
| 5 | Verification Bell | 1,568 bits |
| 6 | Hash Spinoriel | 512 bits |
| 7 | Post-Quantique | 768 bits |
| 8 | Derivation Scrypt | 256 bits |
| 9 | Generation Blender | (visualisation) |

**Total: 30,900 bits**

## Securite

- **Cle vault**: AES-256 (256 bits effectifs)
- **Post-quantique**: NIST Level 5 (McEliece-6960119)
- **Verification**: Violations Bell CHSH > 2.0
- **Brute-force classique**: ~10^59 annees
- **Brute-force quantique (Grover)**: ~10^21 annees

## Licence

MIT License
