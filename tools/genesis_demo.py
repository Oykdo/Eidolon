#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo du Systeme Genesis + Easter Egg + Rune Protocol
"""
import sys
import os

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.genesis_system import (
    GenesisManager, 
    EasterEggGenerator,
    RuneSymbolGenerator,
    GenesisTier,
    create_user_genesis,
    get_genesis_info,
    preview_next_inscription
)


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║     POLY-SPINOR NEXUS 7D - GENESIS SYSTEM                    ║
║     Easter Eggs + Rune Protocol Bitcoin                      ║
╚══════════════════════════════════════════════════════════════╝
    """)


def print_tier_table():
    """Afficher le tableau des tiers"""
    print("\n" + "="*70)
    print("  TABLEAU DES TIERS GENESIS")
    print("="*70)
    
    tiers = [
        ("FOUNDER_1", "1-100", "Quantum Pioneer", "Mythic", "1 Milliard", "10x"),
        ("FOUNDER_10", "101-1,000", "Spinor Visionary", "Legendary", "100 Millions", "5x"),
        ("FOUNDER_100", "1,001-10,000", "Bell Verifier", "Epic", "10 Millions", "2.5x"),
        ("FOUNDER_1000", "10,001-100,000", "Post-Quantum Guardian", "Rare", "1 Million", "1.5x"),
        ("STANDARD", ">100,000", "Standard User", "Common", "100,000", "1x"),
    ]
    
    print(f"\n  {'Tier':<15} {'Range':<15} {'Easter Egg':<22} {'Rarete':<12} {'Runes':<15} {'Mult'}")
    print("-"*95)
    
    for tier, range_, egg, rarity, runes, mult in tiers:
        print(f"  {tier:<15} {range_:<15} {egg:<22} {rarity:<12} {runes:<15} {mult}")
    
    print()


def demo_preview():
    """Previsualiser la prochaine inscription"""
    print("\n" + "="*70)
    print("  PREVISUALISATION PROCHAINE INSCRIPTION")
    print("="*70)
    
    preview = preview_next_inscription()
    
    print(f"\n  Numero d'inscription: #{preview['next_inscription_number']}")
    
    tier_info = preview['tier_info']
    print(f"  Tier: {tier_info['tier']}")
    print(f"  Nom: {tier_info['name']}")
    print(f"  Symbole Rune: {tier_info['rune_symbol']}")
    print(f"  Montant Rune: {tier_info['rune_amount']:,}")
    print(f"  Fondateur: {'Oui' if tier_info['is_founder'] else 'Non'}")
    
    if preview['easter_egg']:
        egg = preview['easter_egg']
        print(f"\n  Easter Egg: {egg['name']}")
        print(f"  Rarete: {egg['attributes']['rarity']}")
        print(f"  Couleur: {egg['attributes']['color']}")
        print(f"  Multiplicateur Rune: {egg['rewards']['rune_multiplier']}x")
        print(f"  Airdrop Futur: {'Oui' if egg['rewards']['future_airdrop'] else 'Non'}")
    
    print()


def demo_create_genesis():
    """Creer un bloc genesis de demonstration"""
    print("\n" + "="*70)
    print("  CREATION D'UN BLOC GENESIS")
    print("="*70)
    
    wallet = input("\n  Entrez une adresse wallet (ou appuyez sur Entree pour demo): ").strip()
    
    if not wallet:
        wallet = "0x" + os.urandom(20).hex()
        print(f"  Wallet demo genere: {wallet}")
    
    print("\n  Mining du bloc genesis...")
    
    genesis = create_user_genesis(wallet)
    
    print(f"\n  [+] BLOC GENESIS CREE!")
    print(f"  {'='*50}")
    print(f"  Inscription #: {genesis.inscription_number}")
    print(f"  User ID: {genesis.user_id}")
    print(f"  Block Hash: {genesis.block_hash[:32]}...")
    print(f"  Nonce: {genesis.nonce}")
    print(f"  Timestamp: {genesis.timestamp}")
    
    print(f"\n  [RUNE]")
    print(f"  Symbole: {genesis.rune_symbol}")
    print(f"  Montant: {genesis.rune_amount:,}")
    print(f"  Divisibilite: {genesis.rune_divisibility}")
    
    if genesis.easter_egg_type:
        print(f"\n  [EASTER EGG]")
        print(f"  Type: {genesis.easter_egg_type}")
        print(f"  Tier: {genesis.tier}")
        if genesis.easter_egg_data:
            print(f"  Rarete: {genesis.easter_egg_data.get('attributes', {}).get('rarity', 'N/A')}")
            print(f"  Hash Unique: {genesis.easter_egg_data.get('unique_hash', 'N/A')}")
    
    print()
    return genesis


def demo_stats():
    """Afficher les statistiques du systeme"""
    print("\n" + "="*70)
    print("  STATISTIQUES GENESIS")
    print("="*70)
    
    stats = get_genesis_info()
    
    print(f"\n  Total Inscriptions: {stats['total_inscriptions']}")
    print(f"  Prochaine Inscription: #{stats['next_inscription_number']}")
    print(f"  Places Fondateur Restantes: {stats['remaining_founder_slots']:,}")
    
    print(f"\n  [FONDATEURS PAR TIER]")
    for tier, count in stats['founders_by_tier'].items():
        print(f"  {tier}: {count}")
    
    print(f"\n  [PLACES RESTANTES PAR TIER]")
    for tier, remaining in stats['remaining_by_tier'].items():
        print(f"  {tier}: {remaining:,}")
    
    print()


def demo_rune_symbols():
    """Demonstrer les symboles runiques"""
    print("\n" + "="*70)
    print("  EXEMPLES DE SYMBOLES RUNIQUES")
    print("="*70)
    
    examples = [1, 50, 100, 500, 1000, 5000, 10000, 50000, 100000, 150000]
    
    print(f"\n  {'#':<10} {'Symbole':<20} {'Montant':<20} {'Tier'}")
    print("-"*70)
    
    for num in examples:
        symbol = RuneSymbolGenerator.generate_symbol(num)
        amount = RuneSymbolGenerator.calculate_amount(num)
        tier = EasterEggGenerator.get_tier(num).name
        print(f"  {num:<10} {symbol:<20} {amount:>15,} {tier}")
    
    print()


def main_menu():
    """Menu principal"""
    while True:
        print("\n" + "="*70)
        print("  MENU PRINCIPAL")
        print("="*70)
        print("""
  [1] Voir le tableau des tiers
  [2] Previsualiser la prochaine inscription
  [3] Creer un bloc genesis
  [4] Voir les statistiques
  [5] Voir les symboles runiques
  [0] Quitter
        """)
        
        choice = input("  Choix: ").strip()
        
        if choice == '1':
            print_tier_table()
        elif choice == '2':
            demo_preview()
        elif choice == '3':
            demo_create_genesis()
        elif choice == '4':
            demo_stats()
        elif choice == '5':
            demo_rune_symbols()
        elif choice == '0':
            print("\n  Au revoir!\n")
            break
        else:
            print("\n  Choix invalide!")
        
        input("\n  Appuyez sur Entree pour continuer...")


def main():
    print_banner()
    print_tier_table()
    main_menu()


if __name__ == "__main__":
    main()
