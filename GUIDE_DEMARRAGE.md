# Guide de Demarrage - Poly-Spinor Nexus 7D

## Introduction

Ce guide vous explique comment generer vos cles cryptographiques et creer votre vault securise.

---

## Prerequis

- Python 3.8+
- Dependances installees:

```bash
cd poly_spinor_nexus_7d
pip install -r requirements.txt
```

---

## 1. Generer une Cle de Vault

### Methode Simple

```bash
python scripts/generate_key.py --name "MonVault" --output "./mes_cles"
```

### Methode Complete (9 phases)

```bash
python scripts/generate_key.py --name "MonVault" --output "./mes_cles" --full
```

### Ce qui se passe

Le generateur execute 9 phases pour creer une cle ultra-securisee:

| Phase | Description | Entropie |
|-------|-------------|----------|
| 1 | Seed aleatoire | 512 bits |
| 2 | Capture spatiale 7D | ~1000 bits |
| 3 | Simulation physique | ~700 bits |
| 4 | Transformation spinorielle | 4096 bits |
| 5 | Verification Bell | 500 bits |
| 6 | Hash composite | 512 bits |
| 7 | Chiffrement post-quantique | 768 bits |
| 8 | Arbre de Merkle | 256 bits |
| 9 | Generation fichiers | - |

**Total: ~8000+ bits d'entropie**

### Fichiers Generes

Apres generation, vous aurez 2 fichiers:

```
mes_cles/
├── vault_key_monvault_XXXXXXXX.psnx        # Cle chiffree (16 KB)
└── vault_key_monvault_XXXXXXXX.blend_data  # Structure 3D (155 KB)
```

> **IMPORTANT**: Les DEUX fichiers sont necessaires pour acceder au vault. Sauvegardez-les en lieu sur!

---

## 2. Se Connecter au Vault

### Via Script Python

```python
from core.complete_key_generator import CompleteKeyFileGenerator, CompletePolySpinorKeyGenerator
from core.persistent_vault import PersistentVaultManager

# Charger la cle
generator = CompletePolySpinorKeyGenerator()
file_gen = CompleteKeyFileGenerator(generator)
key_data, vault_key = file_gen.extract_key_from_file("chemin/vers/fichier.psnx")

# Creer le vault
vault = PersistentVaultManager(vault_key, key_data.user_name)

print(f"Connecte au vault: {key_data.user_name}")
```

### Via le Script de Connexion

```bash
python connect_vault.py
```

### Via l'Interface CLI

```bash
python vault_cli.py
```

---

## 3. Utiliser le Vault

### Ajouter un Actif

```python
asset_id = vault.add_asset({
    'name': 'Mon NFT',
    'asset_type': 'NFT',
    'contract': '0x...',
    'token_id': '1234',
    'chain': 'Ethereum'
})
```

### Ajouter un Document Chiffre

```python
doc_id = vault.add_document("mon_fichier_secret.txt", metadata={
    'category': 'credentials',
    'sensitivity': 'critical'
})
```

### Chiffrer des Donnees

```python
from sdk.python.psnx_sdk import Vault

crypto = Vault(vault_key)

# Chiffrer
encrypted = crypto.encrypt(b"Mes donnees secretes")

# Dechiffrer
decrypted = crypto.decrypt(encrypted)
```

### Lister le Contenu

```python
# Actifs
assets = vault.list_assets()
for a in assets:
    print(f"{a['name']} - {a['asset_type']}")

# Documents
docs = vault.list_documents()

# Statistiques
stats = vault.get_stats()
print(f"Actifs: {stats['asset_count']}")
```

---

## 4. Wallets Blockchain

### Wallet Ethereum/EVM

```python
from sdk.python.psnx_sdk import VaultWeb3Wallet, EVMChain

wallet = VaultWeb3Wallet(vault_key, EVMChain.ETHEREUM)
print(f"Adresse: {wallet.address}")
```

### Wallet Bitcoin

```python
from core.bitcoin_wallet import VaultBitcoinWallet, BitcoinNetwork, AddressType

wallet = VaultBitcoinWallet(vault_key, vault_id, BitcoinNetwork.MAINNET, AddressType.P2TR)
print(f"Adresse Taproot: {wallet.address}")
```

---

## 5. Sauvegarder le Vault

### Exporter

```python
backup_file = vault.export_vault("./backups")
print(f"Backup cree: {backup_file}")
```

### Partage de Secret (Shamir)

Divisez votre cle en plusieurs parts:

```python
from sdk.python.psnx_sdk import SecretSharing

# Creer 5 parts, 3 necessaires pour reconstruire
sharing = SecretSharing(threshold=3, total=5)
shares = sharing.split(vault_key)

# Sauvegarder chaque part separement
for share in shares:
    print(f"Part {share.index}: {share.data.hex()[:20]}...")
```

Reconstruire:

```python
# Avec 3 parts minimum
recovered_key = sharing.reconstruct([shares[0], shares[2], shares[4]])
```

---

## 6. Commandes Rapides

| Action | Commande |
|--------|----------|
| Generer une cle | `python scripts/generate_key.py --name "NomVault"` |
| Se connecter | `python connect_vault.py` |
| Interface CLI | `python vault_cli.py` |
| Interface GUI | `python launch_gui.py` |
| Demo Bitcoin | `python bitcoin_demo.py` |
| Voir le contenu | `python show_vault.py` |

---

## 7. Securite

### A Faire

- Sauvegarder les fichiers `.psnx` et `.blend_data` sur plusieurs supports
- Utiliser le partage Shamir pour les cles critiques
- Ne jamais partager vos fichiers de cle
- Verifier l'integrite avec `vault.verify_document(doc_id)`

### A Ne Pas Faire

- Ne jamais stocker les cles dans le cloud non chiffre
- Ne jamais partager la cle privee WIF
- Ne jamais supprimer les fichiers `.blend_data`

---

## 8. Structure des Fichiers

```
poly_spinor_nexus_7d/
├── core/                    # Modules principaux
│   ├── complete_key_generator.py
│   ├── bitcoin_wallet.py
│   ├── evm_wallet.py
│   └── persistent_vault.py
├── sdk/                     # SDKs (Python, JS, Go, Rust)
├── scripts/                 # Scripts utilitaires
│   └── generate_key.py
├── vault_cli.py             # Interface CLI
├── connect_vault.py         # Script de connexion
└── vault_storage/           # Stockage local (gitignore)
    └── keys/                # Vos cles
```

---

## Besoin d'Aide?

- Consultez les exemples dans le dossier `examples/`
- Lancez `python vault_cli.py` pour l'interface interactive
- Verifiez les logs pour les erreurs

---

*Poly-Spinor Nexus 7D - Cryptographie post-quantique avec verification Bell*
