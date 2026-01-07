#!/usr/bin/env python3
"""
Demo Interactive du Systeme Genesis Vault Evolutif
==================================================

Demonstre le systeme Genesis evolutif ou chaque nouveau vault
herite de la force collective de tous les vaults precedents.

Usage:
    python tools/genesis_evolutif_demo.py
    python tools/genesis_evolutif_demo.py --create 5
    python tools/genesis_evolutif_demo.py --visualize
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Ajouter le repertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configuration UTF-8 pour Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    os.system('chcp 65001 >nul 2>&1')

from core.genesis_vault import (
    EvolutiveGenesisManager,
    GenealogyVisualizer,
    BitcoinRuneInscriber,
    TIER_CONFIGS,
    RUNIC_SYMBOLS,
    FounderTier,
    GenesisType
)


# ============================================================================
# COULEURS CONSOLE
# ============================================================================

class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Couleurs de base
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    
    # Couleurs des tiers
    GOLD = '\033[93m'      # Quantum Pioneer
    PURPLE = '\033[95m'    # Spinor Visionary
    TURQUOISE = '\033[96m' # Bell Verifier
    LIME = '\033[92m'      # Post-Quantum Guardian


def get_tier_color(tier):
    """Obtient la couleur pour un tier"""
    if tier == FounderTier.QUANTUM_PIONEER:
        return Colors.GOLD
    elif tier == FounderTier.SPINOR_VISIONARY:
        return Colors.PURPLE
    elif tier == FounderTier.BELL_VERIFIER:
        return Colors.TURQUOISE
    elif tier == FounderTier.POST_QUANTUM_GUARDIAN:
        return Colors.LIME
    return Colors.WHITE


# ============================================================================
# AFFICHAGE
# ============================================================================

def print_banner():
    """Affiche la banniere"""
    banner = f"""
{Colors.CYAN}{'='*70}
{Colors.BOLD}
  ███████╗██╗██████╗  ██████╗ ██╗      ██████╗ ███╗   ██╗
  ██╔════╝██║██╔══██╗██╔═══██╗██║     ██╔═══██╗████╗  ██║
  █████╗  ██║██║  ██║██║   ██║██║     ██║   ██║██╔██╗ ██║
  ██╔══╝  ██║██║  ██║██║   ██║██║     ██║   ██║██║╚██╗██║
  ███████╗██║██████╔╝╚██████╔╝███████╗╚██████╔╝██║ ╚████║
  ╚══════╝╚═╝╚═════╝  ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝
{Colors.RESET}
{Colors.CYAN}{'='*70}{Colors.RESET}
{Colors.YELLOW}  Systeme Genesis Evolutif - Poly-Spinor Nexus 7D{Colors.RESET}
{Colors.CYAN}{'='*70}{Colors.RESET}
"""
    print(banner)


def print_tier_info():
    """Affiche les informations sur les tiers"""
    print(f"\n{Colors.BOLD}{Colors.WHITE}  TIERS FONDATEURS:{Colors.RESET}\n")
    
    for tier, config in TIER_CONFIGS.items():
        color = get_tier_color(tier)
        runes = "".join(RUNIC_SYMBOLS[r] for r in config.runes)
        
        print(f"  {color}{runes} {config.name}{Colors.RESET}")
        print(f"      Rarete: {Colors.BOLD}{config.rarity}{Colors.RESET}")
        print(f"      Numeros: {config.min_number:,} - {config.max_number:,}")
        print(f"      Recompense: {Colors.GOLD}{config.rune_reward:,} runes{Colors.RESET}")
        print(f"      Multiplicateur: {Colors.CYAN}{config.strength_multiplier}x{Colors.RESET}")
        print(f"      Capacites: {', '.join(config.special_abilities)}")
        print()


def print_block_details(block, detailed=True):
    """Affiche les details d'un bloc"""
    color = get_tier_color(block.tier) if block.tier else Colors.WHITE
    
    print(f"\n{Colors.CYAN}{'─'*60}{Colors.RESET}")
    
    # Titre avec runes
    runes = ""
    if block.runic_inscription:
        runes = f" {block.runic_inscription.rune_symbols}"
    
    tier_name = block.tier_config['name'] if block.tier_config else "Standard"
    
    print(f"  {color}{Colors.BOLD}VAULT #{block.vault_number:05d}{runes}{Colors.RESET}")
    print(f"  {color}[{tier_name}]{Colors.RESET}")
    
    if detailed:
        print(f"\n  {Colors.WHITE}Informations:{Colors.RESET}")
        print(f"    Nom: {block.vault_name}")
        print(f"    Type: {block.genesis_type.value}")
        print(f"    Cree le: {block.created_at}")
        
        print(f"\n  {Colors.WHITE}Heritage:{Colors.RESET}")
        print(f"    Parent: #{block.parent_number}" if block.parent_number else "    Parent: (Primordial)")
        print(f"    Profondeur: {block.ancestry_depth}")
        print(f"    Ancetres: {len(block.ancestor_hashes)}")
        
        print(f"\n  {Colors.WHITE}Force:{Colors.RESET}")
        print(f"    Entropie propre: {Colors.CYAN}{block.own_entropy:,} bits{Colors.RESET}")
        print(f"    Force heritee: {Colors.MAGENTA}{block.inherited_strength:,.2f}{Colors.RESET}")
        print(f"    Force totale: {Colors.GREEN}{Colors.BOLD}{block.total_strength:,.2f}{Colors.RESET}")
        
        if block.runic_inscription:
            print(f"\n  {Colors.WHITE}Runes:{Colors.RESET}")
            print(f"    Symboles: {color}{block.runic_inscription.rune_symbols}{Colors.RESET}")
            print(f"    Balance: {Colors.GOLD}{block.rune_balance:,} runes{Colors.RESET}")
        
        print(f"\n  {Colors.WHITE}Cryptographie:{Colors.RESET}")
        print(f"    Block Hash: {block.block_hash[:32]}...")
        print(f"    Spinor Seed: {block.spinor_seed[:16]}...")
    
    print(f"{Colors.CYAN}{'─'*60}{Colors.RESET}")


def print_collective_strength(cs):
    """Affiche la force collective"""
    print(f"\n{Colors.BOLD}{Colors.WHITE}  FORCE COLLECTIVE DU RESEAU:{Colors.RESET}\n")
    
    print(f"    Total Vaults: {Colors.CYAN}{cs.total_vaults:,}{Colors.RESET}")
    print(f"    Entropie Cumulative: {Colors.CYAN}{cs.cumulative_entropy:,} bits{Colors.RESET}")
    print(f"    Force de Base: {Colors.MAGENTA}{cs.base_strength:,.2f}{Colors.RESET}")
    print(f"    Force Boostee: {Colors.GREEN}{Colors.BOLD}{cs.boosted_strength:,.2f}{Colors.RESET}")
    print(f"    Multiplicateur: {Colors.YELLOW}{cs.founder_multiplier:.2f}x{Colors.RESET}")


# ============================================================================
# DEMO INTERACTIVE
# ============================================================================

def demo_create_vaults(manager, count=5):
    """Demo de creation de vaults"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}  Creation de {count} vaults...{Colors.RESET}\n")
    
    vault_names = [
        "Primordial Genesis",
        "Quantum Nexus",
        "Spinor Prime",
        "Bell Entanglement",
        "Post-Quantum Shield",
        "Cryptographic Haven",
        "Entropy Fortress",
        "Merkle Sanctuary",
        "Hash Guardian",
        "Lattice Citadel"
    ]
    
    created_blocks = []
    
    for i in range(count):
        name = vault_names[i % len(vault_names)]
        
        # Creer le bloc
        block = manager.create_genesis_block(name)
        created_blocks.append(block)
        
        # Affichage compact
        color = get_tier_color(block.tier) if block.tier else Colors.WHITE
        runes = block.runic_inscription.rune_symbols if block.runic_inscription else ""
        tier_name = block.tier_config['name'] if block.tier_config else "Standard"
        
        print(f"    {Colors.GREEN}✓{Colors.RESET} #{block.vault_number:05d} {color}{runes} [{tier_name}]{Colors.RESET}")
        print(f"      Force: {block.total_strength:,.0f} | Heritage: {block.inherited_strength:,.0f}")
    
    return created_blocks


def demo_visualize_tree(manager):
    """Demo de visualisation de l'arbre"""
    visualizer = GenealogyVisualizer(manager)
    
    print(f"\n{Colors.BOLD}{Colors.WHITE}  ARBRE GENEALOGIQUE:{Colors.RESET}")
    print(visualizer.generate_ascii_tree(max_depth=15))
    
    print(visualizer.generate_stats_display())


def demo_inscription(manager, vault_number):
    """Demo d'inscription Bitcoin"""
    block = manager.get_block(vault_number)
    
    if not block:
        print(f"{Colors.RED}  Vault #{vault_number} non trouve{Colors.RESET}")
        return
    
    if not block.runic_inscription:
        print(f"{Colors.YELLOW}  Ce vault n'est pas un fondateur, pas d'inscription{Colors.RESET}")
        return
    
    inscriber = BitcoinRuneInscriber(network="testnet")
    
    print(f"\n{Colors.BOLD}{Colors.WHITE}  INSCRIPTION BITCOIN RUNE:{Colors.RESET}\n")
    
    # Preparer l'inscription
    inscription_data = inscriber.prepare_inscription(block)
    
    print(f"    Content-Type: {inscription_data['content_type']}")
    print(f"    Contenu: {inscription_data['content'][:60]}...")
    
    # Estimer les frais
    fees = inscriber.estimate_fees(inscription_data)
    
    print(f"\n  {Colors.WHITE}Estimation des frais:{Colors.RESET}")
    print(f"    Taille: {fees['content_size']} bytes")
    print(f"    Commit: {fees['commit_fee']:,} sats")
    print(f"    Reveal: {fees['reveal_fee']:,} sats")
    print(f"    {Colors.YELLOW}Total: {fees['total_fee']:,} sats{Colors.RESET}")


def interactive_menu(manager):
    """Menu interactif"""
    while True:
        print(f"\n{Colors.CYAN}{'='*50}{Colors.RESET}")
        print(f"{Colors.BOLD}  MENU PRINCIPAL{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*50}{Colors.RESET}")
        print(f"  1. {Colors.GREEN}Creer un nouveau vault{Colors.RESET}")
        print(f"  2. {Colors.CYAN}Creer plusieurs vaults{Colors.RESET}")
        print(f"  3. {Colors.MAGENTA}Voir l'arbre genealogique{Colors.RESET}")
        print(f"  4. {Colors.YELLOW}Voir la force collective{Colors.RESET}")
        print(f"  5. {Colors.WHITE}Details d'un vault{Colors.RESET}")
        print(f"  6. {Colors.GOLD}Preparer inscription Bitcoin{Colors.RESET}")
        print(f"  7. {Colors.PURPLE}Statistiques des tiers{Colors.RESET}")
        print(f"  0. {Colors.RED}Quitter{Colors.RESET}")
        print(f"{Colors.CYAN}{'='*50}{Colors.RESET}")
        
        try:
            choice = input(f"\n  {Colors.WHITE}Choix: {Colors.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            break
        
        if choice == "1":
            name = input(f"  {Colors.WHITE}Nom du vault: {Colors.RESET}").strip() or "New Vault"
            block = manager.create_genesis_block(name)
            print_block_details(block)
        
        elif choice == "2":
            try:
                count = int(input(f"  {Colors.WHITE}Nombre de vaults: {Colors.RESET}").strip() or "5")
                demo_create_vaults(manager, count)
            except ValueError:
                print(f"{Colors.RED}  Nombre invalide{Colors.RESET}")
        
        elif choice == "3":
            demo_visualize_tree(manager)
        
        elif choice == "4":
            cs = manager.get_collective_strength()
            print_collective_strength(cs)
        
        elif choice == "5":
            try:
                num = int(input(f"  {Colors.WHITE}Numero du vault: {Colors.RESET}").strip())
                block = manager.get_block(num)
                if block:
                    print_block_details(block)
                else:
                    print(f"{Colors.RED}  Vault non trouve{Colors.RESET}")
            except ValueError:
                print(f"{Colors.RED}  Numero invalide{Colors.RESET}")
        
        elif choice == "6":
            try:
                num = int(input(f"  {Colors.WHITE}Numero du vault fondateur: {Colors.RESET}").strip())
                demo_inscription(manager, num)
            except ValueError:
                print(f"{Colors.RED}  Numero invalide{Colors.RESET}")
        
        elif choice == "7":
            stats = manager.get_tier_stats()
            print(f"\n{Colors.BOLD}{Colors.WHITE}  STATISTIQUES DES TIERS:{Colors.RESET}\n")
            
            for tier_key, tier_stats in stats.items():
                color = Colors.GOLD if "pioneer" in tier_key else \
                        Colors.PURPLE if "visionary" in tier_key else \
                        Colors.TURQUOISE if "verifier" in tier_key else Colors.LIME
                
                print(f"  {color}{tier_stats['runes']} {tier_stats['name']}{Colors.RESET}")
                print(f"      Crees: {tier_stats['count']} / {tier_stats['max']}")
                print(f"      Restants: {Colors.YELLOW}{tier_stats['remaining']}{Colors.RESET}")
                print()
        
        elif choice == "0":
            print(f"\n{Colors.CYAN}  Au revoir!{Colors.RESET}\n")
            break
        
        else:
            print(f"{Colors.RED}  Option invalide{Colors.RESET}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Demo Genesis Vault Evolutif")
    parser.add_argument("--create", type=int, help="Creer N vaults")
    parser.add_argument("--visualize", action="store_true", help="Visualiser l'arbre")
    parser.add_argument("--stats", action="store_true", help="Afficher les statistiques")
    parser.add_argument("--data-dir", default="./genesis_data", help="Repertoire des donnees")
    
    args = parser.parse_args()
    
    # Initialiser le gestionnaire
    manager = EvolutiveGenesisManager(args.data_dir)
    
    print_banner()
    
    if args.create:
        demo_create_vaults(manager, args.create)
        demo_visualize_tree(manager)
    elif args.visualize:
        demo_visualize_tree(manager)
    elif args.stats:
        cs = manager.get_collective_strength()
        print_collective_strength(cs)
        print_tier_info()
    else:
        # Mode interactif
        print_tier_info()
        interactive_menu(manager)


if __name__ == "__main__":
    main()
