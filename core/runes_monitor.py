#!/usr/bin/env python3
"""
Poly-Spinor Nexus 7D - Runes Asset Monitor
==========================================

Systeme de monitoring des actifs Runes mintes sur le vault.
Permet de suivre les blocs Genesis, les balances de runes,
et l'historique des inscriptions.
"""

import os
import sys
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except:
        pass


class RuneStatus(Enum):
    """Statut d'une rune"""
    PENDING = "pending"           # En attente d'inscription
    SIGNED = "signed"             # Signee localement
    INSCRIBED = "inscribed"       # Inscrite sur Bitcoin
    CONFIRMED = "confirmed"       # Confirmee (6+ blocks)
    TRANSFERRED = "transferred"   # Transferee


@dataclass
class RuneAsset:
    """Represente un actif Rune"""
    inscription_id: str
    vault_number: int
    tier: str
    tier_name: str
    rarity: str
    rune_symbols: str
    rune_names: List[str]
    balance: int
    color: str
    abilities: List[str]
    status: RuneStatus
    signature: Optional[str]
    signer_public_key: Optional[str]
    signed_at: Optional[str]
    created_at: str
    block_hash: str
    merkle_root: str
    strength: float
    ancestry_depth: int
    # Artefact spinoriel
    artifact: Optional[Dict[str, Any]] = None


@dataclass
class RunePortfolio:
    """Portfolio complet des runes"""
    total_balance: int
    total_assets: int
    tier_breakdown: Dict[str, int]
    signed_count: int
    pending_count: int
    total_strength: float
    assets: List[RuneAsset]


class RunesMonitor:
    """Moniteur des actifs Runes"""
    
    TIER_COLORS = {
        "quantum_pioneer": "#FFD700",      # Or
        "spinor_visionary": "#9400D3",     # Violet
        "bell_verifier": "#00CED1",        # Cyan
        "post_quantum_guardian": "#32CD32", # Vert
        "standard": "#808080"               # Gris
    }
    
    TIER_NAMES = {
        "quantum_pioneer": "Quantum Pioneer",
        "spinor_visionary": "Spinor Visionary",
        "bell_verifier": "Bell Verifier",
        "post_quantum_guardian": "Post-Quantum Guardian",
        "standard": "Standard"
    }
    
    def __init__(self, genesis_dir: str = None):
        base_path = Path(__file__).parent.parent
        
        # Chercher genesis blocks dans plusieurs emplacements
        possible_paths = [
            Path(genesis_dir) if genesis_dir else None,
            base_path / "genesis_data" / "blocks",
            base_path / "genesis_data",
            base_path / "vault_storage" / "genesis_data" / "blocks",
        ]
        
        self.genesis_dir = None
        self.blocks_dir = None
        
        for path in possible_paths:
            if path and path.exists():
                # Verifier si c'est directement un dossier avec des blocs
                if any(path.glob("block_*.json")):
                    self.blocks_dir = path
                    self.genesis_dir = path.parent if path.name == "blocks" else path
                    break
                # Ou un dossier parent contenant "blocks"
                blocks_subdir = path / "blocks"
                if blocks_subdir.exists() and any(blocks_subdir.glob("block_*.json")):
                    self.genesis_dir = path
                    self.blocks_dir = blocks_subdir
                    break
        
        # Si aucun dossier trouve, utiliser le defaut
        if self.blocks_dir is None:
            self.genesis_dir = base_path / "genesis_data"
            self.blocks_dir = self.genesis_dir / "blocks"
        
        self._cache: Dict[int, RuneAsset] = {}
        self._last_scan: Optional[datetime] = None
    
    def scan_runes(self, force: bool = False) -> List[RuneAsset]:
        """Scanne tous les blocs Genesis et extrait les runes"""
        if not self.blocks_dir.exists():
            return []
        
        # Cache de 30 secondes
        if not force and self._last_scan:
            delta = (datetime.now() - self._last_scan).total_seconds()
            if delta < 30 and self._cache:
                return list(self._cache.values())
        
        assets = []
        
        for block_file in sorted(self.blocks_dir.glob("block_*.json")):
            try:
                with open(block_file, 'r', encoding='utf-8') as f:
                    block_data = json.load(f)
                
                asset = self._parse_block_to_asset(block_data)
                if asset:
                    assets.append(asset)
                    self._cache[asset.vault_number] = asset
                    
            except Exception as e:
                print(f"[WARN] Erreur lecture {block_file}: {e}")
        
        self._last_scan = datetime.now()
        return assets
    
    def _parse_block_to_asset(self, block_data: Dict) -> Optional[RuneAsset]:
        """Parse un bloc Genesis en RuneAsset"""
        try:
            inscription = block_data.get("runic_inscription", {})
            tier_config = block_data.get("tier_config", {})
            
            # Determiner le statut
            signature = block_data.get("signature")
            if signature:
                status = RuneStatus.SIGNED
            else:
                status = RuneStatus.PENDING
            
            # Verifier si inscrit sur Bitcoin
            if inscription.get("txid"):
                if inscription.get("status") == "confirmed":
                    status = RuneStatus.CONFIRMED
                else:
                    status = RuneStatus.INSCRIBED
            
            tier = block_data.get("tier", "standard")
            
            return RuneAsset(
                inscription_id=inscription.get("inscription_id", ""),
                vault_number=block_data.get("vault_number", 0),
                tier=tier,
                tier_name=tier_config.get("name", self.TIER_NAMES.get(tier, "Standard")),
                rarity=tier_config.get("rarity", "Common"),
                rune_symbols=inscription.get("rune_symbols", ""),
                rune_names=inscription.get("runes", []),
                balance=block_data.get("rune_balance", 0),
                color=tier_config.get("color", self.TIER_COLORS.get(tier, "#808080")),
                abilities=tier_config.get("special_abilities", []),
                status=status,
                signature=signature[:32] + "..." if signature and len(signature) > 32 else signature,
                signer_public_key=block_data.get("signer_public_key"),
                signed_at=block_data.get("signed_at"),
                created_at=block_data.get("created_at", ""),
                block_hash=block_data.get("block_hash", ""),
                merkle_root=block_data.get("merkle_root", ""),
                strength=block_data.get("total_strength", 0),
                ancestry_depth=block_data.get("ancestry_depth", 0),
                artifact=block_data.get("artifact")
            )
        except Exception as e:
            print(f"[WARN] Erreur parsing bloc: {e}")
            return None
    
    def get_portfolio(self) -> RunePortfolio:
        """Obtient le portfolio complet des runes"""
        assets = self.scan_runes()
        
        total_balance = sum(a.balance for a in assets)
        tier_breakdown = {}
        signed_count = 0
        pending_count = 0
        total_strength = 0
        
        for asset in assets:
            # Tier breakdown
            tier_breakdown[asset.tier_name] = tier_breakdown.get(asset.tier_name, 0) + 1
            
            # Compteurs
            if asset.status == RuneStatus.SIGNED:
                signed_count += 1
            elif asset.status == RuneStatus.PENDING:
                pending_count += 1
            
            total_strength += asset.strength
        
        return RunePortfolio(
            total_balance=total_balance,
            total_assets=len(assets),
            tier_breakdown=tier_breakdown,
            signed_count=signed_count,
            pending_count=pending_count,
            total_strength=total_strength,
            assets=assets
        )
    
    def get_asset(self, vault_number: int) -> Optional[RuneAsset]:
        """Obtient un actif par son numero de vault"""
        if vault_number in self._cache:
            return self._cache[vault_number]
        
        self.scan_runes()
        return self._cache.get(vault_number)
    
    def get_total_balance(self) -> int:
        """Obtient la balance totale de runes"""
        assets = self.scan_runes()
        return sum(a.balance for a in assets)
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtient les statistiques globales"""
        portfolio = self.get_portfolio()
        
        return {
            "total_runes": portfolio.total_balance,
            "total_assets": portfolio.total_assets,
            "signed": portfolio.signed_count,
            "pending": portfolio.pending_count,
            "strength": portfolio.total_strength,
            "tiers": portfolio.tier_breakdown
        }
    
    def format_balance(self, balance: int) -> str:
        """Formate une balance de runes"""
        if balance >= 1_000_000_000:
            return f"{balance / 1_000_000_000:.2f}B"
        elif balance >= 1_000_000:
            return f"{balance / 1_000_000:.2f}M"
        elif balance >= 1_000:
            return f"{balance / 1_000:.2f}K"
        return str(balance)
    
    def get_runes_display(self) -> str:
        """Genere un affichage texte des runes"""
        portfolio = self.get_portfolio()
        
        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("  POLY-SPINOR NEXUS 7D - RUNES PORTFOLIO")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"  Total Balance: {self.format_balance(portfolio.total_balance)} PSNX")
        lines.append(f"  Total Assets:  {portfolio.total_assets}")
        lines.append(f"  Signed:        {portfolio.signed_count}")
        lines.append(f"  Pending:       {portfolio.pending_count}")
        lines.append(f"  Total Strength:{portfolio.total_strength:,.0f}")
        lines.append("")
        lines.append("  " + "-" * 66)
        lines.append("  ASSETS:")
        lines.append("  " + "-" * 66)
        
        for asset in portfolio.assets:
            status_icon = "✓" if asset.status == RuneStatus.SIGNED else "○"
            lines.append(f"  {status_icon} #{asset.vault_number:05d} | {asset.rune_symbols} | {asset.tier_name}")
            lines.append(f"    Balance: {self.format_balance(asset.balance)} | Strength: {asset.strength:,.0f}")
            if asset.signature:
                lines.append(f"    Signature: {asset.signature}")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


def create_runes_monitor(genesis_dir: str = None) -> RunesMonitor:
    """Factory pour creer un moniteur de runes"""
    return RunesMonitor(genesis_dir)


# Test
if __name__ == "__main__":
    monitor = RunesMonitor()
    print(monitor.get_runes_display())
