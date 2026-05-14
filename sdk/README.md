# Eidolon SDKs

SDKs officiels pour interagir avec le système Eidolon.

## Langages Supportés

| Langage | Package | Version | Features |
|---------|---------|---------|----------|
| **TypeScript/JavaScript** | `@psnx/sdk` | 1.0.0 | Vault, ZKP, Sharing, Web3 |
| **Python** | `psnx-sdk` | 1.0.0 | Vault, ZKP, Sharing, Web3 |
| **Rust** | `psnx-sdk` | 1.0.0 | Vault, ZKP, Sharing, Web3 |
| **Go** | `github.com/poly-spinor/psnx-sdk-go` | 1.0.0 | Vault, ZKP, Sharing, Web3 |

## Features Communes

Tous les SDKs implémentent:

- **KeyGenerator**: Génération de clés vault sécurisées
- **Vault**: Chiffrement AES-256-GCM avec dérivation HKDF
- **SecretSharing**: Partage de secret Shamir (k-of-n)
- **ZKP**: Authentification Zero-Knowledge (Schnorr)
- **Web3**: Wallet HD dérivé + backup décentralisé IPFS/blockchain

## Installation

### JavaScript/TypeScript

```bash
npm install @psnx/sdk
# ou
yarn add @psnx/sdk
```

### Python

```bash
pip install psnx-sdk
```

### Rust

```toml
# Cargo.toml
[dependencies]
psnx-sdk = "1.0"
```

### Go

```bash
go get github.com/poly-spinor/psnx-sdk-go
```

## Exemples d'Utilisation

### Vault (Chiffrement)

<details>
<summary><b>TypeScript</b></summary>

```typescript
import { KeyGenerator, Vault } from '@psnx/sdk';

const keyGen = new KeyGenerator();
const vaultKey = await keyGen.generate();

const vault = new Vault(vaultKey);
const encrypted = await vault.encrypt(new TextEncoder().encode('secret'));
const decrypted = await vault.decrypt(encrypted);
```
</details>

<details>
<summary><b>Python</b></summary>

```python
from psnx_sdk import KeyGenerator, Vault

key_gen = KeyGenerator()
vault_key = key_gen.generate()

vault = Vault(vault_key)
encrypted = vault.encrypt(b"secret")
decrypted = vault.decrypt(encrypted)
```
</details>

<details>
<summary><b>Rust</b></summary>

```rust
use psnx_sdk::{KeyGenerator, Vault};

let key_gen = KeyGenerator::new();
let vault_key = key_gen.generate()?;

let vault = Vault::new(&vault_key)?;
let encrypted = vault.encrypt(b"secret")?;
let decrypted = vault.decrypt(&encrypted)?;
```
</details>

<details>
<summary><b>Go</b></summary>

```go
import "github.com/poly-spinor/psnx-sdk-go"

keyGen := psnx.NewKeyGenerator()
vaultKey, _ := keyGen.Generate()

vault, _ := psnx.NewVault(vaultKey)
encrypted, _ := vault.Encrypt([]byte("secret"))
decrypted, _ := vault.Decrypt(encrypted)
```
</details>

### ZKP (Authentification)

<details>
<summary><b>TypeScript</b></summary>

```typescript
import { ZKPProver, ZKPVerifier } from '@psnx/sdk';

const prover = await ZKPProver.create(vaultKey);
const proof = await prover.createProof('challenge_from_server');

// Côté serveur
const result = await ZKPVerifier.verify(proof, 'challenge_from_server');
console.log(result.valid); // true
```
</details>

<details>
<summary><b>Python</b></summary>

```python
from psnx_sdk import ZKPProver, ZKPVerifier

prover = ZKPProver(vault_key)
proof = prover.create_proof("challenge_from_server")

# Côté serveur
valid, reason = ZKPVerifier.verify(proof, "challenge_from_server")
print(valid)  # True
```
</details>

### Secret Sharing (Shamir)

<details>
<summary><b>TypeScript</b></summary>

```typescript
import { SecretSharing } from '@psnx/sdk';

const sharing = new SecretSharing(3, 5); // 3-of-5
const shares = await sharing.split(vaultKey);

// Distribuer les parts...

// Reconstruction avec 3 parts
const recovered = await sharing.reconstruct([shares[0], shares[2], shares[4]]);
```
</details>

<details>
<summary><b>Python</b></summary>

```python
from psnx_sdk import SecretSharing

sharing = SecretSharing(threshold=3, total=5)
shares = sharing.split(vault_key)

# Distribuer les parts...

# Reconstruction avec 3 parts
recovered = sharing.reconstruct([shares[0], shares[2], shares[4]])
```
</details>

### Web3 (Backup Décentralisé)

<details>
<summary><b>TypeScript</b></summary>

```typescript
import { DecentralizedBackupManager } from '@psnx/sdk';

const manager = await DecentralizedBackupManager.create(vaultKey, {
  chain: 'sepolia',
  autoUploadIPFS: true
});

console.log('Wallet:', manager.getWalletAddress());

// Créer un backup
const record = await manager.createBackup('backup_001', backupData, {
  uploadToIPFS: true,
  registerOnChain: true
});

// Vérifier l'intégrité
const result = await manager.verifyBackup('backup_001', backupData);
console.log('Valid:', result.valid);
```
</details>

<details>
<summary><b>Python</b></summary>

```python
from psnx_sdk import DecentralizedBackupManager, EVMChain

manager = DecentralizedBackupManager(
    vault_key,
    chain=EVMChain.SEPOLIA,
    auto_upload_ipfs=True
)

print(f"Wallet: {manager.address}")

# Créer un backup
record = manager.create_backup("backup_001", backup_data, upload_to_ipfs=True)

# Vérifier l'intégrité
result = manager.verify_backup("backup_001", backup_data)
print(f"Valid: {result['valid']}")
```
</details>

## Chaînes EVM Supportées

| Chaîne | Chain ID | Symbole |
|--------|----------|---------|
| Ethereum Mainnet | 1 | ETH |
| Ethereum Sepolia | 11155111 | ETH |
| Polygon | 137 | MATIC |
| Arbitrum One | 42161 | ETH |
| Base | 8453 | ETH |
| Optimism | 10 | ETH |

## Architecture

```
vault_key (32 bytes)
    │
    ├── Vault ──────────── AES-256-GCM encryption
    │
    ├── ZKP ────────────── Schnorr proof (authentication)
    │
    ├── SecretSharing ──── Shamir k-of-n (recovery)
    │
    └── Web3Wallet ─────── HD wallet (backup registration)
            │
            ├── IPFS ──────── Decentralized storage
            │
            └── Blockchain ── On-chain verification
```

## Compatibilité Cross-Language

Les SDKs sont compatibles entre eux:
- Même `vault_key` → même adresse Web3
- Même `vault_key` → même clé publique ZKP
- Données chiffrées par un SDK → déchiffrables par un autre
- Parts Shamir générées par un SDK → reconstructibles par un autre

## Tests

```bash
# TypeScript
cd sdk/javascript && npm test

# Python
cd sdk/python && pytest

# Rust
cd sdk/rust && cargo test

# Go
cd sdk/go && go test ./...
```

## License

Proprietary commercial license - see [LICENSE](../LICENSE)
