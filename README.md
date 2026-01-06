# Poly-Spinor Nexus 7D

<div align="center">

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![Security](https://img.shields.io/badge/security-10%2F10-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Python](https://img.shields.io/badge/python-3.9+-yellow.svg)

**Systeme cryptographique post-quantique de nouvelle generation**

*Vault securise avec verification Bell 7D, Zero-Knowledge Proofs et support EVM*

</div>

---

## Caracteristiques Principales

| Feature | Description |
|---------|-------------|
| **Entropie Quantique** | Pool hybride QRNG (ANU) + atmospherique + OS |
| **Post-Quantique** | McEliece, HQC, ML-DSA, Falcon, SPHINCS+ (NIST Level 5) |
| **Zero-Knowledge** | Authentification Schnorr sans reveler la cle |
| **Shamir Sharing** | Partage K-of-N pour recuperation et multi-sig |
| **Protection Memoire** | Verrouillage RAM, masquage XOR, effacement DoD |
| **Fichiers Authentifies** | HMAC-SHA256 anti-tampering |
| **Wallet EVM** | Support multi-chaines (ETH, Polygon, Arbitrum...) |

## Installation Rapide

```bash
# Cloner le repo
git clone https://github.com/Oykdo/Eidolon.git
cd Eidolon/poly_spinor_nexus_7d

# Installer les dependances
pip install -r requirements.txt

# Generer votre premiere cle
python scripts/generate_key.py --name "MonVault"
```

## Utilisation

### 1. Generer une Cle Vault

```bash
python scripts/generate_key.py --name "MonVault" --output "./vault_storage/keys"
```

Fichiers generes:
- `vault_key_xxx.psnx` - Donnees cryptographiques (~17 KB)
- `vault_key_xxx.blend_data` - Structure 3D + metadonnees (~156 KB)

**Les DEUX fichiers sont necessaires pour acceder au vault.**

### 2. Lancer le Vault

```bash
python launch_vault_monitor.py --psnx "chemin/vers/cle.psnx" --blend "chemin/vers/cle.blend_data"
```

### 3. Utilisation en Python

```python
from core.security_suite import SecureVaultManager, SecurityConfig

# Configuration
config = SecurityConfig(
    use_quantum_entropy=True,
    memory_protection=True,
    enable_zkp=True,
    shamir_threshold=3,
    shamir_total=5
)

manager = SecureVaultManager(config)

# Generer une cle securisee
vault_key = manager.generate_secure_key("MonVault")

# Creer une preuve de possession (ZKP)
proof = manager.create_ownership_proof("challenge_unique")

# Creer des parts de recuperation
shares = manager.create_recovery_shares(threshold=3, total=5)

# Sauvegarder un fichier authentifie
manager.save_secure_file("data.psnx", my_data)
```

## Architecture

```
poly_spinor_nexus_7d/
|
|-- core/                          # Moteur cryptographique
|   |-- complete_key_generator.py  # Generateur 9 phases
|   |-- security_suite.py          # Suite securite 10/10
|   |-- quantum_entropy.py         # Entropie QRNG
|   |-- zkp_auth.py                # Zero-Knowledge Proofs
|   |-- secret_sharing.py          # Shamir K-of-N
|   |-- secure_memory.py           # Protection memoire
|   |-- authenticated_files.py     # Fichiers HMAC
|   |-- hardware_security.py       # Interface HSM
|   |-- real_post_quantum.py       # Crypto PQ (pqcrypto)
|   |-- spinor_crypto.py           # Algebre Clifford Cl(0,7)
|   |-- quantum_verification.py    # Verification Bell
|   +-- evm_wallet.py              # Wallet multi-chaines
|
|-- protocols/                     # Protocoles avances
|   |-- scheduled_tasks.py         # Taches planifiees
|   +-- vault_monitoring.py        # Surveillance temps reel
|
|-- ui/                            # Interfaces
|   +-- vault_monitor.py           # GUI monitoring
|
|-- scripts/                       # Utilitaires
|   |-- generate_key.py            # Generation de cles
|   +-- vault_launcher.py          # Lanceur unifie
|
+-- tests/                         # Tests
    +-- test_security_suite.py     # Tests securite (7/7)
```

## Les 9 Phases de Generation

| Phase | Description | Entropie |
|-------|-------------|----------|
| 1 | Seed maitre CSPRNG | 512 bits |
| 2 | Capture spatiale 7D + EPR | ~1,050 bits |
| 3 | Simulation physique 7 polyedres | ~700 bits |
| 4 | Transformation spinorielle Cl(0,7) | ~4,096 bits |
| 5 | Verification Bell 7D | ~500 bits |
| 6 | Hash spinoriel composite | 512 bits |
| 7 | Chiffrement post-quantique | 768 bits |
| 8 | Arbre Merkle + Scrypt | 256 bits |
| 9 | Generation fichiers | - |

**Total: ~8,400 bits d'entropie effective**

---

## 🥚 Genesis System - Easter Eggs pour les Fondateurs

Les **100,000 premiers utilisateurs** qui generent un vault recoivent un **Easter Egg exclusif** avec des recompenses uniques!

### Tiers de Fondateurs

| Tier | Inscription | Easter Egg | Rarete | Runes | Multiplicateur | Airdrop |
|------|-------------|------------|--------|-------|----------------|---------|
| 🏆 **FOUNDER_1** | #1 - #100 | Quantum Pioneer | Mythic | 1 Milliard | 10x | ✅ |
| 🥇 **FOUNDER_10** | #101 - #1,000 | Spinor Visionary | Legendary | 100 Millions | 5x | ✅ |
| 🥈 **FOUNDER_100** | #1,001 - #10,000 | Bell Verifier | Epic | 10 Millions | 2.5x | ✅ |
| 🥉 **FOUNDER_1000** | #10,001 - #100,000 | Post-Quantum Guardian | Rare | 1 Million | 1.5x | ❌ |
| ⚪ **STANDARD** | > #100,000 | - | Common | 100,000 | 1x | ❌ |

### Symboles Runiques

Chaque fondateur recoit un **symbole runique unique** base sur son numero d'inscription:

```
#1      → ᛏᚨᛚ•ᚢ      (Tier 1 - Mythic)
#100    → ᛏᚨᛚ•ᚱᚱ     (Tier 1 - Mythic)
#500    → ᚨᚾᚲ•ᛚᛚ     (Tier 2 - Legendary)
#5000   → ᚠᛟᚱ•ᚺᛏᚺ    (Tier 3 - Epic)
#50000  → ᛖᚨᚱ•ᚨᛉᛗᚺ   (Tier 4 - Rare)
```

### Ce que vous recevez

Lors de la generation de votre vault, vous obtenez automatiquement:

1. **Genesis Block** - Bloc mine avec votre numero d'inscription unique
2. **Easter Egg NFT** - Attributs de rarete, couleur, animation
3. **Rune Token** - Symbole runique + allocation de tokens
4. **Inscription Bitcoin** - Format compatible Ordinals/Runes Protocol

### Exemple de sortie

```
============================================================
  GENESIS SYSTEM - EASTER EGG
============================================================

  [INFO] Prochaine inscription: #42
  [INFO] Tier: FOUNDER_1 - Quantum Pioneer
  [INFO] FELICITATIONS! Vous etes un FONDATEUR!

  ==================================================
  VOTRE GENESIS BLOCK
  ==================================================
  Inscription #: 42
  Block Hash: 0000007a3f2b1c8d...
  Rune Symbol: ᛏᚨᛚ•ᚢᛚ
  Rune Amount: 1,000,000,000

  [EASTER EGG]
  Type: Quantum Pioneer
  Tier: FOUNDER_1
  Rarete: Mythic
  Couleur: #FFD700
  Animation: quantum_flare
  Multiplicateur Rune: 10x
  Airdrop Futur: Oui
  Pouvoir Governance: 100
```

### Recompenses des Easter Eggs

| Attribut | FOUNDER_1 | FOUNDER_10 | FOUNDER_100 | FOUNDER_1000 |
|----------|-----------|------------|-------------|--------------|
| Rarete | Mythic | Legendary | Epic | Rare |
| Couleur | #FFD700 (Or) | #C0C0C0 (Argent) | #A335EE (Violet) | #0070DD (Bleu) |
| Glow | ✅ | ✅ | ❌ | ❌ |
| Animation | quantum_flare | spinor_pulse | bell_oscillation | lattice_shield |
| Multiplicateur | 10x | 5x | 2.5x | 1.5x |
| Airdrop Futur | ✅ | ✅ | ✅ | ❌ |
| Pouvoir Governance | 100 | 50 | 25 | 10 |

### Integration Bitcoin (Rune Protocol)

Les inscriptions Genesis sont compatibles avec le **Rune Protocol** de Bitcoin:

```json
{
  "p": "rune",
  "op": "deploy",
  "sym": "ᛏᚨᛚ•ᚢᛚ",
  "amt": "1000000000",
  "dec": "8",
  "genesis": "0000007a3f2b1c8d...",
  "tier": "FOUNDER_1",
  "easter_egg": "a1b2c3d4e5f6"
}
```

---

## Securite

### Score: 10/10

| Composant | Implementation | Status |
|-----------|----------------|--------|
| Entropie | QRNG + mixing multi-sources | OK |
| Memoire | VirtualLock + XOR mask + DoD wipe | OK |
| Fichiers | HMAC-SHA256 authentification | OK |
| Partage | Shamir information-theoretic | OK |
| Timing | Operations constant-time | OK |
| Auth | Schnorr ZKP non-interactif | OK |
| HSM | YubiHSM / TPM / Software | OK |

### Resistance aux Attaques

| Attaque | Protection |
|---------|------------|
| Brute-force classique | ~2^256 operations |
| Grover (quantique) | ~2^128 operations |
| Shor (factorisation) | Post-quantique (lattices) |
| Side-channel | Constant-time ops |
| Cold boot | Memory locking + masking |
| Tampering | HMAC file authentication |

---

## Roadmap

### Phase 1: Fondations (Complete)

- [x] Generateur de cles 9 phases
- [x] Verification Bell 7D
- [x] Chiffrement post-quantique (pqcrypto)
- [x] Wallet EVM multi-chaines
- [x] Interface GUI de base

### Phase 2: Securite Avancee (Complete)

- [x] Entropie quantique (ANU QRNG)
- [x] Protection memoire (VirtualLock, secure wipe)
- [x] Fichiers authentifies HMAC
- [x] Shamir Secret Sharing
- [x] Operations constant-time
- [x] Zero-Knowledge Proofs
- [x] Interface HSM

### Phase 3: Integration (Q1 2026)

- [ ] **API REST securisee**
  - Endpoints authentifies JWT + ZKP
  - Rate limiting et anti-DDoS
  - Documentation OpenAPI

- [ ] **SDK Multi-langages**
  - Python SDK (complet)
  - JavaScript/TypeScript SDK
  - Rust SDK (performance)

- [ ] **Integration Blockchain**
  - Smart contracts de vault on-chain
  - Bridge cross-chain (LayerZero)
  - Support NFT metadata encryption

### Phase 4: Enterprise (Q2 2026)

- [ ] **Multi-tenancy**
  - Isolation des vaults par organisation
  - Roles et permissions granulaires
  - Audit logs immutables

- [ ] **HSM Production**
  - Certification FIPS 140-3
  - Support AWS CloudHSM
  - Support Azure Dedicated HSM

- [ ] **Compliance**
  - GDPR data handling
  - SOC 2 Type II
  - Penetration testing externe

### Phase 5: Decentralisation (Q3 2026)

- [ ] **Vault Distribue**
  - Stockage IPFS/Filecoin chiffre
  - Shamir sur reseau P2P
  - Recovery decentralise

- [ ] **Governance**
  - DAO pour evolution protocole
  - Token de gouvernance
  - Incentives pour validateurs

- [ ] **Interoperabilite**
  - Standard ouvert PSNX
  - Compatibility Keybase/Signal
  - Plugin navigateurs

### Phase 6: Innovation (Q4 2026)

- [ ] **Quantum-Ready**
  - Integration vrais QRNG hardware
  - QKD (Quantum Key Distribution) prep
  - Hybrid classical/quantum schemes

- [ ] **AI Security**
  - Detection anomalies ML
  - Threat intelligence
  - Auto-rotation des cles

- [ ] **Mobile**
  - App iOS/Android
  - Secure Enclave integration
  - Biometric + ZKP auth

---

## Tests

```bash
# Executer tous les tests
python -m pytest tests/ -v

# Tests de securite specifiques
python tests/test_security_suite.py
```

Resultat attendu:
```
======================================================================
  TESTS SECURITY SUITE 10/10 - POLY-SPINOR NEXUS 7D
======================================================================
  [OK] Secure Memory
  [OK] Authenticated Files
  [OK] Quantum Entropy
  [OK] Secret Sharing
  [OK] Constant Time
  [OK] ZKP Auth
  [OK] Integration
======================================================================
  Total: 7/7 tests passes
  Score de securite: 10/10
======================================================================
```

## Contribution

Les contributions sont bienvenues! Voir [CONTRIBUTING.md](CONTRIBUTING.md) pour les guidelines.

```bash
# Fork le repo
# Creer une branche feature
git checkout -b feature/ma-feature

# Commit avec message conventionnel
git commit -m "feat: description"

# Push et creer PR
git push origin feature/ma-feature
```

## Licence

MIT License - voir [LICENSE](LICENSE) pour details.

---

<div align="center">

**Poly-Spinor Nexus 7D** - Cryptographie Post-Quantique de Nouvelle Generation

*Protegez vos donnees contre les menaces d'aujourd'hui et de demain*

</div>
