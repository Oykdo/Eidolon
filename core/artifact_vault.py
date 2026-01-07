"""
Systeme d'Artefacts Detachables pour Eidolon
=========================================================

Permet de:
- Detacher un artefact de son bloc Genesis
- Stocker les artefacts independamment
- Transferer des artefacts entre vaults
- Generer des artefacts retroactivement pour les anciens blocs
"""

import os
import sys
import json
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict, field
from pathlib import Path
from enum import Enum

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Import du systeme d'artefacts
try:
    from core.artifact_system import (
        SpinorArtifactGenerator, SpinorArtifact, ArtifactRarity,
        RARITY_COLORS, RARITY_MULTIPLIERS, format_artifact_display
    )
except ImportError:
    from artifact_system import (
        SpinorArtifactGenerator, SpinorArtifact, ArtifactRarity,
        RARITY_COLORS, RARITY_MULTIPLIERS, format_artifact_display
    )


class ArtifactStatus(Enum):
    """Statut d'un artefact"""
    ATTACHED = "attached"       # Lie au bloc genesis
    DETACHED = "detached"       # Detache, dans l'inventaire
    TRANSFERRED = "transferred" # Transfere a un autre vault
    LOCKED = "locked"           # Verrouille (ne peut etre detache)
    BURNED = "burned"           # Brule/detruit


@dataclass
class DetachableArtifact:
    """Artefact detachable avec historique de propriete"""
    # Identite
    artifact_id: str
    artifact_data: Dict[str, Any]  # Donnees completes de l'artefact
    
    # Origine
    origin_block_id: str
    origin_vault_number: int
    origin_tier: str
    created_at: str
    
    # Propriete actuelle
    current_owner_vault: Optional[int] = None
    status: ArtifactStatus = ArtifactStatus.ATTACHED
    
    # Historique
    transfer_history: List[Dict[str, Any]] = field(default_factory=list)
    detached_at: Optional[str] = None
    
    # Metadata
    is_founder_artifact: bool = False
    founder_bonus_applied: bool = False
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['status'] = self.status.value
        return d
    
    @classmethod
    def from_dict(cls, data: dict) -> "DetachableArtifact":
        data['status'] = ArtifactStatus(data['status'])
        return cls(**data)
    
    @property
    def name(self) -> str:
        return self.artifact_data.get('name', 'Unknown')
    
    @property
    def rarity(self) -> str:
        return self.artifact_data.get('rarity', 'common')
    
    @property
    def power(self) -> float:
        stats = self.artifact_data.get('stats', {})
        return stats.get('effective_power', 0)
    
    @property
    def color(self) -> str:
        return RARITY_COLORS.get(ArtifactRarity(self.rarity), '#ffffff')


class ArtifactVault:
    """Gestionnaire de vault d'artefacts detachables"""
    
    FOUNDER_TIERS = ["quantum_pioneer", "spinor_visionary", "bell_verifier", "post_quantum_guardian"]
    
    def __init__(self, data_dir: str = None):
        base_path = Path(__file__).parent.parent
        self.data_dir = Path(data_dir) if data_dir else base_path / "artifact_vault"
        self.artifacts_dir = self.data_dir / "artifacts"
        self.inventory_dir = self.data_dir / "inventory"
        self.genesis_dir = base_path / "genesis_data" / "blocks"
        
        # Creer les repertoires
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.inventory_dir.mkdir(parents=True, exist_ok=True)
        
        # Cache
        self._artifacts: Dict[str, DetachableArtifact] = {}
        self._load_artifacts()
    
    def _load_artifacts(self):
        """Charge tous les artefacts"""
        for artifact_file in self.artifacts_dir.glob("artifact_*.json"):
            try:
                with open(artifact_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                artifact = DetachableArtifact.from_dict(data)
                self._artifacts[artifact.artifact_id] = artifact
            except Exception as e:
                print(f"[WARN] Erreur chargement {artifact_file}: {e}")
    
    def _save_artifact(self, artifact: DetachableArtifact):
        """Sauvegarde un artefact"""
        filepath = self.artifacts_dir / f"artifact_{artifact.artifact_id}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(artifact.to_dict(), f, indent=2, ensure_ascii=False)
        self._artifacts[artifact.artifact_id] = artifact
    
    def generate_artifact_for_block(self, block_data: Dict, force: bool = False) -> Optional[DetachableArtifact]:
        """
        Genere un artefact pour un bloc genesis existant.
        
        Args:
            block_data: Donnees du bloc genesis
            force: Regenerer meme si un artefact existe deja
        
        Returns:
            DetachableArtifact genere
        """
        vault_number = block_data.get('vault_number')
        block_id = block_data.get('block_id', f"genesis_{vault_number:08d}")
        
        # Verifier si artefact existe deja
        existing = self.get_artifact_by_origin(vault_number)
        if existing and not force:
            print(f"[INFO] Artefact existe deja pour vault #{vault_number}")
            return existing
        
        # Determiner le tier et le bonus fondateur
        tier = block_data.get('tier', 'standard')
        spinor_seed = block_data.get('spinor_seed', secrets.token_hex(32))
        
        # Creer le generateur avec le seed du bloc
        try:
            seed_bytes = bytes.fromhex(spinor_seed)
        except:
            seed_bytes = hashlib.sha256(spinor_seed.encode()).digest()
        
        generator = SpinorArtifactGenerator(seed_bytes)
        
        # Determiner la rarete forcee selon le tier fondateur
        force_rarity = self._get_founder_rarity(tier)
        
        # Generer l'artefact
        artifact = generator.generate(
            genesis_block_id=block_id,
            vault_number=vault_number,
            force_rarity=force_rarity
        )
        
        # Creer l'artefact detachable
        detachable = DetachableArtifact(
            artifact_id=artifact.artifact_id,
            artifact_data=artifact.to_dict(),
            origin_block_id=block_id,
            origin_vault_number=vault_number,
            origin_tier=tier,
            created_at=datetime.now().isoformat(),
            current_owner_vault=vault_number,
            status=ArtifactStatus.ATTACHED,
            is_founder_artifact=tier in self.FOUNDER_TIERS,
            founder_bonus_applied=force_rarity is not None
        )
        
        # Sauvegarder
        self._save_artifact(detachable)
        
        return detachable
    
    def _get_founder_rarity(self, tier: str) -> Optional[ArtifactRarity]:
        """Determine la rarete minimale selon le tier fondateur"""
        if tier == "quantum_pioneer":
            roll = secrets.randbelow(100)
            if roll < 10:
                return ArtifactRarity.PRIMORDIAL
            elif roll < 30:
                return ArtifactRarity.TRANSCENDENT
            elif roll < 60:
                return ArtifactRarity.MYTHIC
            else:
                return ArtifactRarity.LEGENDARY
        elif tier == "spinor_visionary":
            roll = secrets.randbelow(100)
            if roll < 5:
                return ArtifactRarity.MYTHIC
            elif roll < 25:
                return ArtifactRarity.LEGENDARY
            else:
                return ArtifactRarity.EPIC
        elif tier == "bell_verifier":
            roll = secrets.randbelow(100)
            if roll < 15:
                return ArtifactRarity.LEGENDARY
            elif roll < 45:
                return ArtifactRarity.EPIC
            else:
                return ArtifactRarity.RARE
        elif tier == "post_quantum_guardian":
            roll = secrets.randbelow(100)
            if roll < 20:
                return ArtifactRarity.EPIC
            elif roll < 50:
                return ArtifactRarity.RARE
            else:
                return ArtifactRarity.UNCOMMON
        return None
    
    def generate_all_missing_artifacts(self) -> List[DetachableArtifact]:
        """Genere les artefacts pour tous les blocs genesis sans artefact"""
        generated = []
        
        if not self.genesis_dir.exists():
            print(f"[WARN] Repertoire genesis non trouve: {self.genesis_dir}")
            return generated
        
        for block_file in sorted(self.genesis_dir.glob("block_*.json")):
            try:
                with open(block_file, 'r', encoding='utf-8') as f:
                    block_data = json.load(f)
                
                vault_number = block_data.get('vault_number')
                
                # Verifier si artefact existe
                existing = self.get_artifact_by_origin(vault_number)
                if existing:
                    continue
                
                # Generer
                artifact = self.generate_artifact_for_block(block_data)
                if artifact:
                    generated.append(artifact)
                    print(f"[+] Vault #{vault_number}: {artifact.name} [{artifact.rarity.upper()}]")
                    
            except Exception as e:
                print(f"[ERR] Erreur pour {block_file}: {e}")
        
        return generated
    
    def detach_artifact(self, artifact_id: str) -> bool:
        """
        Detache un artefact de son bloc genesis.
        L'artefact devient transferable.
        """
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            print(f"[ERR] Artefact {artifact_id} non trouve")
            return False
        
        if artifact.status == ArtifactStatus.LOCKED:
            print(f"[ERR] Artefact {artifact_id} est verrouille")
            return False
        
        if artifact.status == ArtifactStatus.DETACHED:
            print(f"[INFO] Artefact deja detache")
            return True
        
        # Detacher
        artifact.status = ArtifactStatus.DETACHED
        artifact.detached_at = datetime.now().isoformat()
        artifact.transfer_history.append({
            "action": "detach",
            "from_vault": artifact.current_owner_vault,
            "timestamp": artifact.detached_at
        })
        
        self._save_artifact(artifact)
        return True
    
    def attach_artifact(self, artifact_id: str, vault_number: int) -> bool:
        """
        Attache un artefact a un vault.
        """
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            print(f"[ERR] Artefact {artifact_id} non trouve")
            return False
        
        if artifact.status not in [ArtifactStatus.DETACHED, ArtifactStatus.TRANSFERRED]:
            print(f"[ERR] Artefact doit etre detache pour etre attache")
            return False
        
        # Attacher
        old_owner = artifact.current_owner_vault
        artifact.current_owner_vault = vault_number
        artifact.status = ArtifactStatus.ATTACHED
        artifact.transfer_history.append({
            "action": "attach",
            "from_vault": old_owner,
            "to_vault": vault_number,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_artifact(artifact)
        return True
    
    def transfer_artifact(self, artifact_id: str, to_vault: int) -> bool:
        """
        Transfere un artefact a un autre vault.
        """
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            return False
        
        if artifact.status == ArtifactStatus.LOCKED:
            print(f"[ERR] Artefact verrouille")
            return False
        
        # Transferer
        old_owner = artifact.current_owner_vault
        artifact.current_owner_vault = to_vault
        artifact.status = ArtifactStatus.TRANSFERRED
        artifact.transfer_history.append({
            "action": "transfer",
            "from_vault": old_owner,
            "to_vault": to_vault,
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_artifact(artifact)
        return True
    
    def lock_artifact(self, artifact_id: str) -> bool:
        """Verrouille un artefact (ne peut plus etre detache/transfere)"""
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            return False
        
        artifact.status = ArtifactStatus.LOCKED
        artifact.transfer_history.append({
            "action": "lock",
            "timestamp": datetime.now().isoformat()
        })
        
        self._save_artifact(artifact)
        return True
    
    def get_artifact(self, artifact_id: str) -> Optional[DetachableArtifact]:
        """Obtient un artefact par son ID"""
        return self._artifacts.get(artifact_id)
    
    def get_artifact_by_origin(self, vault_number: int) -> Optional[DetachableArtifact]:
        """Obtient l'artefact original d'un vault"""
        for artifact in self._artifacts.values():
            if artifact.origin_vault_number == vault_number:
                return artifact
        return None
    
    def get_artifacts_by_owner(self, vault_number: int) -> List[DetachableArtifact]:
        """Obtient tous les artefacts possedes par un vault"""
        return [a for a in self._artifacts.values() 
                if a.current_owner_vault == vault_number]
    
    def get_all_artifacts(self) -> List[DetachableArtifact]:
        """Obtient tous les artefacts"""
        return list(self._artifacts.values())
    
    def get_inventory(self, vault_number: int) -> Dict[str, Any]:
        """Obtient l'inventaire complet d'un vault"""
        artifacts = self.get_artifacts_by_owner(vault_number)
        
        # Stats
        total_power = sum(a.power for a in artifacts)
        rarity_counts = {}
        for a in artifacts:
            rarity_counts[a.rarity] = rarity_counts.get(a.rarity, 0) + 1
        
        return {
            "vault_number": vault_number,
            "artifact_count": len(artifacts),
            "total_power": total_power,
            "rarity_breakdown": rarity_counts,
            "artifacts": [a.to_dict() for a in artifacts],
            "founder_artifacts": len([a for a in artifacts if a.is_founder_artifact])
        }
    
    def update_genesis_blocks_with_artifacts(self):
        """Met a jour les blocs genesis avec les artefacts generes"""
        updated = 0
        
        for artifact in self._artifacts.values():
            vault_num = artifact.origin_vault_number
            block_file = self.genesis_dir / f"block_{vault_num:08d}.json"
            
            if not block_file.exists():
                continue
            
            try:
                with open(block_file, 'r', encoding='utf-8') as f:
                    block_data = json.load(f)
                
                # Ajouter l'artefact si absent
                if not block_data.get('artifact'):
                    block_data['artifact'] = artifact.artifact_data
                    
                    with open(block_file, 'w', encoding='utf-8') as f:
                        json.dump(block_data, f, indent=2, ensure_ascii=False)
                    
                    updated += 1
                    print(f"[+] Updated block #{vault_num} with artifact")
                    
            except Exception as e:
                print(f"[ERR] Erreur update block #{vault_num}: {e}")
        
        return updated


def display_artifact_summary(artifact: DetachableArtifact) -> str:
    """Affiche un resume de l'artefact"""
    art = artifact.artifact_data
    status_icons = {
        ArtifactStatus.ATTACHED: "🔗",
        ArtifactStatus.DETACHED: "📦",
        ArtifactStatus.TRANSFERRED: "↗️",
        ArtifactStatus.LOCKED: "🔒",
        ArtifactStatus.BURNED: "🔥"
    }
    
    icon = status_icons.get(artifact.status, "?")
    founder = "⭐" if artifact.is_founder_artifact else ""
    
    return (f"{icon} [{artifact.rarity.upper()[:4]}] {artifact.name} "
            f"| PWR:{artifact.power:,.0f} | Origin:#{artifact.origin_vault_number} "
            f"| Owner:#{artifact.current_owner_vault} {founder}")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestionnaire d'Artefacts Detachables")
    parser.add_argument("--generate-all", action="store_true", help="Generer les artefacts manquants")
    parser.add_argument("--update-blocks", action="store_true", help="Mettre a jour les blocs genesis")
    parser.add_argument("--list", action="store_true", help="Lister tous les artefacts")
    parser.add_argument("--inventory", type=int, help="Afficher l'inventaire d'un vault")
    parser.add_argument("--detach", type=str, help="Detacher un artefact (ID)")
    parser.add_argument("--transfer", nargs=2, metavar=('ID', 'VAULT'), help="Transferer un artefact")
    
    args = parser.parse_args()
    
    vault = ArtifactVault()
    
    print("\n" + "="*70)
    print("  ARTIFACT VAULT - Eidolon")
    print("="*70 + "\n")
    
    if args.generate_all:
        print("[*] Generation des artefacts manquants...\n")
        generated = vault.generate_all_missing_artifacts()
        print(f"\n[+] {len(generated)} artefacts generes")
        
        if args.update_blocks:
            print("\n[*] Mise a jour des blocs genesis...")
            updated = vault.update_genesis_blocks_with_artifacts()
            print(f"[+] {updated} blocs mis a jour")
    
    elif args.update_blocks:
        print("[*] Mise a jour des blocs genesis...")
        updated = vault.update_genesis_blocks_with_artifacts()
        print(f"[+] {updated} blocs mis a jour")
    
    elif args.list:
        artifacts = vault.get_all_artifacts()
        if not artifacts:
            print("[INFO] Aucun artefact trouve")
        else:
            print(f"[*] {len(artifacts)} artefacts:\n")
            for art in sorted(artifacts, key=lambda x: x.power, reverse=True):
                print("  " + display_artifact_summary(art))
    
    elif args.inventory:
        inv = vault.get_inventory(args.inventory)
        print(f"[*] Inventaire Vault #{args.inventory}:\n")
        print(f"    Artefacts: {inv['artifact_count']}")
        print(f"    Puissance totale: {inv['total_power']:,.0f}")
        print(f"    Artefacts fondateurs: {inv['founder_artifacts']}")
        print(f"    Raretes: {inv['rarity_breakdown']}")
        
        if inv['artifacts']:
            print("\n    Artefacts:")
            for a in inv['artifacts']:
                art = DetachableArtifact.from_dict(a)
                print("      " + display_artifact_summary(art))
    
    elif args.detach:
        if vault.detach_artifact(args.detach):
            print(f"[+] Artefact {args.detach} detache avec succes")
        else:
            print(f"[ERR] Echec du detachement")
    
    elif args.transfer:
        artifact_id, to_vault = args.transfer
        if vault.transfer_artifact(artifact_id, int(to_vault)):
            print(f"[+] Artefact transfere au vault #{to_vault}")
        else:
            print(f"[ERR] Echec du transfert")
    
    else:
        # Par defaut, afficher les stats
        artifacts = vault.get_all_artifacts()
        print(f"  Artefacts totaux: {len(artifacts)}")
        
        founder_count = len([a for a in artifacts if a.is_founder_artifact])
        print(f"  Artefacts fondateurs: {founder_count}")
        
        if artifacts:
            total_power = sum(a.power for a in artifacts)
            print(f"  Puissance totale: {total_power:,.0f}")
            
            print("\n  Utilisez --generate-all pour creer les artefacts manquants")
            print("  Utilisez --list pour voir tous les artefacts")
