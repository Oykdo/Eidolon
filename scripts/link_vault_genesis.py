"""
Script pour lier un vault existant a un Genesis Block
et generer ses adresses blockchain
"""

import sys
import os
import json
import zlib
import hashlib
import secrets
from pathlib import Path
from datetime import datetime

# Fix encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# Try web3 imports
try:
    from eth_account import Account
    Account.enable_unaudited_hdwallet_features()
    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    print("[WARN] eth_account not available. Install with: pip install eth-account")


def load_psnx_vault(filepath: Path) -> dict:
    """Charge un fichier vault PSNX"""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # Parse header
    magic = data[:4].decode('ascii')
    if magic != 'PSNX':
        raise ValueError(f"Invalid PSNX file: {magic}")
    
    # Decompress
    decompressed = zlib.decompress(data[22:])
    return json.loads(decompressed)


def derive_master_key(vault_data: dict) -> bytes:
    """Derive une cle maitre depuis les donnees du vault"""
    key_data = vault_data.get('key_data', {})
    
    # Combiner plusieurs sources d'entropie
    sources = []
    
    # Master seed
    master_seed = key_data.get('master_seed', '')
    if isinstance(master_seed, str):
        sources.append(master_seed.encode())
    elif isinstance(master_seed, dict):
        sources.append(json.dumps(master_seed, sort_keys=True).encode())
    
    # Spinor data
    spinor = key_data.get('spinor_data', {})
    if spinor:
        sources.append(json.dumps(spinor, sort_keys=True).encode())
    
    # Hash data
    hash_data = key_data.get('hash_data', {})
    if hash_data:
        sources.append(json.dumps(hash_data, sort_keys=True).encode())
    
    # Combine
    combined = b''.join(sources)
    
    # Derive using HKDF
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'PSNX7D_MASTER_KEY',
        info=b'vault_master_derivation',
    )
    
    return hkdf.derive(hashlib.sha512(combined).digest())


def generate_evm_address(master_key: bytes) -> tuple:
    """Genere une adresse EVM depuis la cle maitre"""
    if not WEB3_AVAILABLE:
        return None, None
    
    # Derive private key
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'PSNX7D_EVM',
        info=b'evm_wallet_derivation',
    )
    private_key = hkdf.derive(master_key)
    
    # Create account
    account = Account.from_key(private_key)
    
    return account.address, private_key.hex()


def generate_bitcoin_addresses(master_key: bytes) -> dict:
    """Genere des adresses Bitcoin depuis la cle maitre"""
    import hashlib
    
    # Derive keys for different address types
    addresses = {}
    
    # P2PKH (Legacy - starts with 1)
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'PSNX7D_BTC_P2PKH',
        info=b'bitcoin_p2pkh',
    )
    p2pkh_key = hkdf.derive(master_key)
    
    # Simple public key derivation (simplified - in production use proper secp256k1)
    pubkey_hash = hashlib.new('ripemd160', hashlib.sha256(p2pkh_key).digest()).digest()
    
    # Base58Check encode for P2PKH
    version = b'\x00'  # Mainnet
    payload = version + pubkey_hash
    checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    addresses['p2pkh'] = base58_encode(payload + checksum)
    
    # P2WPKH (Native SegWit - starts with bc1q)
    addresses['p2wpkh'] = bech32_encode('bc', 0, pubkey_hash)
    
    # P2TR (Taproot - starts with bc1p) - simplified
    hkdf_tr = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'PSNX7D_BTC_P2TR',
        info=b'bitcoin_taproot',
    )
    taproot_key = hkdf_tr.derive(master_key)
    addresses['p2tr'] = bech32_encode('bc', 1, hashlib.sha256(taproot_key).digest()[:32])
    
    return addresses


def base58_encode(data: bytes) -> str:
    """Encode en Base58"""
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    
    # Count leading zeros
    leading_zeros = 0
    for byte in data:
        if byte == 0:
            leading_zeros += 1
        else:
            break
    
    # Convert to big integer
    num = int.from_bytes(data, 'big')
    
    # Encode
    result = ''
    while num > 0:
        num, remainder = divmod(num, 58)
        result = alphabet[remainder] + result
    
    return '1' * leading_zeros + result


def bech32_encode(hrp: str, witver: int, witprog: bytes) -> str:
    """Encode une adresse Bech32/Bech32m"""
    CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    
    def bech32_polymod(values):
        GEN = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
        chk = 1
        for v in values:
            b = chk >> 25
            chk = ((chk & 0x1ffffff) << 5) ^ v
            for i in range(5):
                chk ^= GEN[i] if ((b >> i) & 1) else 0
        return chk
    
    def bech32_hrp_expand(s):
        return [ord(x) >> 5 for x in s] + [0] + [ord(x) & 31 for x in s]
    
    def bech32_create_checksum(hrp, data, spec):
        values = bech32_hrp_expand(hrp) + data
        const = 0x2bc830a3 if spec == 'm' else 1
        polymod = bech32_polymod(values + [0,0,0,0,0,0]) ^ const
        return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]
    
    # Convert witness program to 5-bit groups
    data = [witver]
    acc = 0
    bits = 0
    for byte in witprog:
        acc = (acc << 8) | byte
        bits += 8
        while bits >= 5:
            bits -= 5
            data.append((acc >> bits) & 31)
    if bits:
        data.append((acc << (5 - bits)) & 31)
    
    spec = 'm' if witver > 0 else '1'
    checksum = bech32_create_checksum(hrp, data, spec)
    
    return hrp + '1' + ''.join([CHARSET[d] for d in data + checksum])


def create_genesis_block(vault_name: str, vault_fingerprint: str, 
                        spinor_data: dict, genesis_dir: Path) -> dict:
    """Cree un nouveau Genesis Block pour le vault"""
    # Trouver le prochain numero
    existing = list(genesis_dir.glob("block_*.json"))
    next_num = len(existing) + 1
    
    # Determiner le tier
    if next_num <= 100:
        tier = "quantum_pioneer"
        tier_config = {
            "name": "Quantum Pioneer",
            "rarity": "Mythic",
            "min_number": 1,
            "max_number": 100,
            "rune_reward": 1_000_000_000,
            "strength_multiplier": 10.0,
            "color": "#FFD700",
            "special_abilities": [
                "quantum_resonance",
                "primordial_link",
                "infinite_inheritance",
                "rune_mastery"
            ]
        }
        rune_balance = 1_000_000_000
    elif next_num <= 1000:
        tier = "spinor_visionary"
        tier_config = {
            "name": "Spinor Visionary",
            "rarity": "Legendary",
            "min_number": 101,
            "max_number": 1000,
            "rune_reward": 100_000_000,
            "strength_multiplier": 5.0,
            "color": "#9400D3",
            "special_abilities": ["spinor_mastery", "vision_7d", "enhanced_inheritance"]
        }
        rune_balance = 100_000_000
    else:
        tier = "standard"
        tier_config = None
        rune_balance = 0
    
    # Calculer la force heritee
    total_inherited = 0
    ancestor_hashes = []
    for block_file in sorted(existing):
        with open(block_file, 'r', encoding='utf-8') as f:
            prev_block = json.load(f)
        total_inherited += prev_block.get('total_strength', 0)
        ancestor_hashes.append(prev_block.get('block_hash', ''))
    
    # Entropie propre
    own_entropy = spinor_data.get('total_entropy_bits', 8192)
    
    # Force totale
    multiplier = tier_config['strength_multiplier'] if tier_config else 1.0
    total_strength = (total_inherited * 0.1 + own_entropy) * multiplier
    
    # Spinor seed
    spinor_seed = hashlib.sha256(
        json.dumps(spinor_data, sort_keys=True).encode()
    ).hexdigest()
    
    # Block ID
    block_id = f"genesis_{next_num:08d}_{secrets.token_hex(8)}"
    
    # Runic inscription
    runic_inscription = {
        "inscription_id": f"rune_{next_num:08d}_{secrets.token_hex(4)}",
        "tier": tier,
        "rune_symbols": "ᚠᛊᛞᛟ" if tier == "quantum_pioneer" else "ᚨᚲᛈᛗ",
        "runes": ["FEHU", "SOWILO", "DAGAZ", "OTHALA"] if tier == "quantum_pioneer" else ["ANSUZ", "KENAZ", "PERTHRO", "MANNAZ"],
        "content": f"Genesis Block #{next_num} - {vault_name}",
        "status": "pending"
    }
    
    # Genesis block
    block = {
        "block_id": block_id,
        "vault_number": next_num,
        "vault_name": vault_name,
        "vault_fingerprint": vault_fingerprint,
        "genesis_type": "founder" if next_num <= 100000 else "standard",
        "created_at": datetime.now().isoformat(),
        "parent_hash": ancestor_hashes[-1] if ancestor_hashes else None,
        "parent_number": next_num - 1 if next_num > 1 else None,
        "ancestry_depth": len(ancestor_hashes),
        "ancestor_hashes": ancestor_hashes[-10:],  # Keep last 10
        "inherited_strength": total_inherited * 0.1,
        "own_entropy": own_entropy,
        "total_strength": total_strength,
        "tier": tier,
        "tier_config": tier_config,
        "is_founder": tier in ["quantum_pioneer", "spinor_visionary", "bell_verifier", "post_quantum_guardian"],
        "runic_inscription": runic_inscription,
        "rune_balance": rune_balance,
        "block_hash": "",
        "signature": "",
        "signer_public_key": "",
        "signed_at": None,
        "spinor_seed": spinor_seed,
        "bell_proof": secrets.token_hex(64),
        "merkle_root": secrets.token_hex(32),
        "artifact": None  # Will be generated
    }
    
    # Compute hash
    hash_data = {
        "block_id": block["block_id"],
        "vault_number": block["vault_number"],
        "parent_hash": block["parent_hash"],
        "created_at": block["created_at"],
        "own_entropy": block["own_entropy"],
        "spinor_seed": block["spinor_seed"]
    }
    block["block_hash"] = hashlib.sha256(
        json.dumps(hash_data, sort_keys=True).encode()
    ).hexdigest()
    
    return block


def generate_artifact_for_block(block: dict) -> dict:
    """Genere un artefact pour le bloc"""
    from core.artifact_system import SpinorArtifactGenerator, ArtifactRarity
    
    tier = block.get('tier', 'standard')
    spinor_seed = block.get('spinor_seed', secrets.token_hex(32))
    
    # Create generator
    try:
        seed_bytes = bytes.fromhex(spinor_seed)
    except:
        seed_bytes = hashlib.sha256(spinor_seed.encode()).digest()
    
    generator = SpinorArtifactGenerator(seed_bytes)
    
    # Determine rarity based on tier
    force_rarity = None
    if tier == "quantum_pioneer":
        roll = secrets.randbelow(100)
        if roll < 10:
            force_rarity = ArtifactRarity.PRIMORDIAL
        elif roll < 30:
            force_rarity = ArtifactRarity.TRANSCENDENT
        elif roll < 60:
            force_rarity = ArtifactRarity.MYTHIC
        else:
            force_rarity = ArtifactRarity.LEGENDARY
    elif tier == "spinor_visionary":
        roll = secrets.randbelow(100)
        if roll < 5:
            force_rarity = ArtifactRarity.MYTHIC
        elif roll < 25:
            force_rarity = ArtifactRarity.LEGENDARY
        else:
            force_rarity = ArtifactRarity.EPIC
    
    # Generate
    artifact = generator.generate(
        genesis_block_id=block['block_id'],
        vault_number=block['vault_number'],
        force_rarity=force_rarity
    )
    
    return artifact.to_dict()


def main():
    print("\n" + "="*70)
    print("  VAULT TO GENESIS LINKER - Poly-Spinor Nexus 7D")
    print("="*70 + "\n")
    
    # Paths
    base_path = Path(__file__).parent.parent
    vault_file = base_path / "vault_storage" / "keys" / "vault_key_zgo_cc147844.psnx"
    genesis_dir = base_path / "genesis_data" / "blocks"
    
    genesis_dir.mkdir(parents=True, exist_ok=True)
    
    # Load vault
    print("[1] Loading vault zgo...")
    vault_data = load_psnx_vault(vault_file)
    vault_name = vault_data.get('user_name', 'zgo')
    vault_fingerprint = "cc147844"
    key_data = vault_data.get('key_data', {})
    
    print(f"    Name: {vault_name}")
    print(f"    Fingerprint: {vault_fingerprint}")
    print(f"    Entropy: {key_data.get('total_entropy_bits', 0)} bits")
    
    # Derive master key
    print("\n[2] Deriving master key...")
    master_key = derive_master_key(vault_data)
    print(f"    Master key derived (32 bytes)")
    
    # Generate EVM address
    print("\n[3] Generating EVM address...")
    if WEB3_AVAILABLE:
        evm_address, evm_private = generate_evm_address(master_key)
        print(f"    EVM Address: {evm_address}")
    else:
        evm_address = None
        print("    [SKIP] eth-account not installed")
    
    # Generate Bitcoin addresses
    print("\n[4] Generating Bitcoin addresses...")
    btc_addresses = generate_bitcoin_addresses(master_key)
    for addr_type, addr in btc_addresses.items():
        print(f"    {addr_type.upper()}: {addr}")
    
    # Create Genesis Block
    print("\n[5] Creating Genesis Block...")
    block = create_genesis_block(
        vault_name=vault_name,
        vault_fingerprint=vault_fingerprint,
        spinor_data=key_data,
        genesis_dir=genesis_dir
    )
    
    print(f"    Block ID: {block['block_id']}")
    print(f"    Vault Number: #{block['vault_number']}")
    print(f"    Tier: {block['tier']}")
    print(f"    Rune Balance: {block['rune_balance']:,} PSNX")
    print(f"    Strength: {block['total_strength']:,.0f}")
    
    # Add blockchain addresses to block
    block['evm_address'] = evm_address
    block['bitcoin_addresses'] = btc_addresses
    
    # Generate artifact
    print("\n[6] Generating Founder Artifact...")
    artifact = generate_artifact_for_block(block)
    block['artifact'] = artifact
    
    print(f"    Name: {artifact['name']}")
    print(f"    Rarity: {artifact['rarity'].upper()}")
    print(f"    Power: {artifact['stats']['effective_power']:,.0f}")
    print(f"    Element: {artifact['element'].upper()}")
    
    # Save block
    block_file = genesis_dir / f"block_{block['vault_number']:08d}.json"
    with open(block_file, 'w', encoding='utf-8') as f:
        json.dump(block, f, indent=2, ensure_ascii=False)
    
    print(f"\n[7] Saved to: {block_file}")
    
    # Create detachable artifact entry
    print("\n[8] Creating detachable artifact entry...")
    artifact_vault_dir = base_path / "artifact_vault" / "artifacts"
    artifact_vault_dir.mkdir(parents=True, exist_ok=True)
    
    detachable = {
        "artifact_id": artifact['artifact_id'],
        "artifact_data": artifact,
        "origin_block_id": block['block_id'],
        "origin_vault_number": block['vault_number'],
        "origin_tier": block['tier'],
        "created_at": datetime.now().isoformat(),
        "current_owner_vault": block['vault_number'],
        "status": "attached",
        "transfer_history": [],
        "detached_at": None,
        "is_founder_artifact": block['is_founder'],
        "founder_bonus_applied": True
    }
    
    artifact_file = artifact_vault_dir / f"artifact_{artifact['artifact_id']}.json"
    with open(artifact_file, 'w', encoding='utf-8') as f:
        json.dump(detachable, f, indent=2, ensure_ascii=False)
    
    print(f"    Saved to: {artifact_file}")
    
    # Summary
    print("\n" + "="*70)
    print("  SUMMARY - VAULT ZGO LINKED TO BLOCKCHAIN")
    print("="*70)
    print(f"""
  Vault: {vault_name} ({vault_fingerprint})
  
  GENESIS BLOCK #{block['vault_number']}:
    Tier: {block['tier'].upper().replace('_', ' ')}
    Rune Balance: {block['rune_balance']:,} PSNX
    Strength: {block['total_strength']:,.0f}
  
  BLOCKCHAIN ADDRESSES:
    EVM (Ethereum/Polygon/etc): {evm_address or 'Not generated'}
    Bitcoin P2PKH (Legacy):     {btc_addresses.get('p2pkh', 'N/A')}
    Bitcoin P2WPKH (SegWit):    {btc_addresses.get('p2wpkh', 'N/A')}
    Bitcoin P2TR (Taproot):     {btc_addresses.get('p2tr', 'N/A')}
  
  FOUNDER ARTIFACT:
    [{artifact['rarity'].upper()}] {artifact['name']}
    Power: {artifact['stats']['effective_power']:,.0f}
    Element: {artifact['element'].upper()}
    Abilities: {len(artifact['abilities'])}
""")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
