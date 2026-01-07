#!/usr/bin/env python3
"""
Eidolon - Guide de Démarrage Basique
==================================================

Ce fichier montre comment utiliser les fonctionnalités de base du vault.

Prérequis:
    pip install cryptography numpy pillow

Usage:
    python examples/basic_usage.py
"""

import os
import sys
import hashlib
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# 1. CRÉATION ET GESTION D'UN VAULT BASIQUE
# =============================================================================

def exemple_vault_basique():
    """
    Exemple 1: Créer et utiliser un vault simple
    """
    print("\n" + "="*60)
    print("EXEMPLE 1: Vault Basique")
    print("="*60)
    
    from core.persistent_vault import PersistentVaultManager
    
    # Créer une clé à partir d'un mot de passe
    password = "mon_mot_de_passe_secret"
    vault_name = "mon_premier_vault"
    
    # Dériver une clé sécurisée
    salt = hashlib.sha256(vault_name.encode()).digest()[:16]
    vault_key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    
    print(f"[1] Création du vault '{vault_name}'...")
    
    # Créer le gestionnaire de vault
    vault = PersistentVaultManager(vault_key, vault_name)
    
    # Afficher les statistiques
    stats = vault.get_stats()
    print(f"[2] Vault créé!")
    print(f"    - Version: {stats['version']}")
    print(f"    - Créé le: {stats['created']}")
    
    return vault, vault_key


def exemple_ajouter_actifs(vault):
    """
    Exemple 2: Ajouter des actifs au vault
    """
    print("\n" + "="*60)
    print("EXEMPLE 2: Ajouter des Actifs")
    print("="*60)
    
    # Ajouter un NFT
    nft_data = {
        'name': 'Mon Premier NFT',
        'asset_type': 'NFT',
        'contract': '0x1234567890abcdef1234567890abcdef12345678',
        'token_id': '42',
        'chain': 'Ethereum',
        'metadata': {
            'collection': 'Ma Collection',
            'rarity': 'rare'
        }
    }
    
    nft_id = vault.add_asset(nft_data)
    print(f"[1] NFT ajouté avec ID: {nft_id}")
    
    # Ajouter un token
    token_data = {
        'name': 'USDC Savings',
        'asset_type': 'Token',
        'contract': '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
        'chain': 'Ethereum',
        'metadata': {
            'symbol': 'USDC',
            'amount': '1000.00'
        }
    }
    
    token_id = vault.add_asset(token_data)
    print(f"[2] Token ajouté avec ID: {token_id}")
    
    # Lister les actifs
    print(f"\n[3] Liste des actifs:")
    for asset in vault.list_assets():
        print(f"    - [{asset['id'][:8]}] {asset['name']} ({asset['asset_type']})")
    
    return nft_id, token_id


def exemple_documents(vault):
    """
    Exemple 3: Stocker des documents de manière sécurisée
    """
    print("\n" + "="*60)
    print("EXEMPLE 3: Stocker des Documents")
    print("="*60)
    
    # Créer un fichier temporaire pour la démo
    temp_file = Path("exemple_document.txt")
    temp_file.write_text("Ceci est un document confidentiel.\nIl sera chiffré dans le vault.")
    
    print(f"[1] Document créé: {temp_file}")
    
    # Ajouter au vault
    doc_id = vault.add_document(
        str(temp_file),
        metadata={'category': 'confidential', 'author': 'moi'}
    )
    print(f"[2] Document chiffré et ajouté avec ID: {doc_id}")
    
    # Vérifier l'intégrité
    is_valid = vault.verify_document(doc_id)
    print(f"[3] Vérification d'intégrité: {'OK' if is_valid else 'ÉCHEC'}")
    
    # Extraire le document
    output_file = Path("document_extrait.txt")
    vault.extract_document(doc_id, str(output_file))
    print(f"[4] Document extrait vers: {output_file}")
    
    # Vérifier le contenu
    content = output_file.read_text()
    print(f"[5] Contenu: {content[:50]}...")
    
    # Nettoyer
    temp_file.unlink()
    output_file.unlink()
    
    return doc_id


def exemple_transfers(vault):
    """
    Exemple 4: Programmer des transfers avec délai
    """
    print("\n" + "="*60)
    print("EXEMPLE 4: Transfers Programmés")
    print("="*60)
    
    from datetime import datetime, timedelta
    
    # Programmer un transfer
    transfer_data = {
        'transfer_type': 'NFT',
        'asset_id': 'nft_exemple_123',
        'destination': '0xabcdef1234567890abcdef1234567890abcdef12',
        'delay_days': 7,  # Transfer dans 7 jours
        'metadata': {
            'reason': 'Transfer programmé de test',
            'beneficiary': 'Alice'
        }
    }
    
    transfer_id = vault.schedule_transfer(transfer_data)
    print(f"[1] Transfer programmé avec ID: {transfer_id}")
    
    # Voir les transfers en attente
    pending = vault.get_pending_transfers()
    print(f"[2] Transfers en attente: {len(pending)}")
    
    for t in pending:
        expiry = datetime.fromisoformat(t['expiry'])
        days_left = (expiry - datetime.now()).days
        print(f"    - [{t['id'][:8]}] {t['transfer_type']} -> expire dans {days_left} jours")
    
    # Annuler le transfer (pour la démo)
    vault.cancel_transfer(transfer_id)
    print(f"[3] Transfer annulé")
    
    return transfer_id


def exemple_monitoring():
    """
    Exemple 5: Utiliser le monitoring
    """
    print("\n" + "="*60)
    print("EXEMPLE 5: Monitoring du Vault")
    print("="*60)
    
    from protocols.vault_monitoring import VaultActivityMonitor
    
    # Créer une clé de test
    vault_key = hashlib.sha256(b"monitoring_test").digest()
    vault_name = "vault_monitore"
    
    # Créer le monitor
    monitor = VaultActivityMonitor(vault_key, vault_name)
    
    print(f"[1] Monitor créé pour '{vault_name}'")
    
    # Obtenir les métriques
    metrics = monitor.get_metrics()
    print(f"[2] Métriques initiales:")
    print(f"    - Score de sécurité: {metrics['security_score']}%")
    print(f"    - Intégrité Bell: {metrics['bell_integrity']:.2%}")
    print(f"    - Actifs: {metrics['asset_count']}")
    
    # Générer un rapport
    report = monitor.generate_report()
    print(f"[3] Rapport généré:")
    print(f"    - Recommandations: {len(report['recommendations'])}")
    
    for rec in report['recommendations']:
        print(f"      * [{rec['priority']}] {rec['action']}")
    
    return monitor


def exemple_configuration():
    """
    Exemple 6: Utiliser la configuration
    """
    print("\n" + "="*60)
    print("EXEMPLE 6: Configuration du Vault")
    print("="*60)
    
    from config import config, get_chain_rpc
    
    # Lire la configuration
    print(f"[1] Configuration chargée")
    
    # Obtenir les chaînes activées
    chains = config.enabled_chains
    print(f"[2] Chaînes blockchain activées:")
    for name, chain in chains.items():
        print(f"    - {name}: Chain ID {chain.chain_id}")
    
    # Obtenir un paramètre spécifique
    check_interval = config.get('vault_settings', 'monitoring', 'check_interval')
    print(f"[3] Intervalle de monitoring: {check_interval} secondes")
    
    # Paramètres de sécurité
    security = config.security
    print(f"[4] Paramètres de sécurité:")
    print(f"    - Double clé requise: {security.get('require_dual_key')}")
    print(f"    - Tentatives max: {security.get('max_login_attempts')}")
    
    return config


# =============================================================================
# 2. EXEMPLE COMPLET: WORKFLOW DE VAULT
# =============================================================================

def workflow_complet():
    """
    Workflow complet d'utilisation du vault
    """
    print("\n" + "#"*60)
    print("# WORKFLOW COMPLET DU VAULT")
    print("#"*60)
    
    # Étape 1: Créer le vault
    vault, vault_key = exemple_vault_basique()
    
    # Étape 2: Ajouter des actifs
    nft_id, token_id = exemple_ajouter_actifs(vault)
    
    # Étape 3: Stocker des documents
    doc_id = exemple_documents(vault)
    
    # Étape 4: Programmer des transfers
    transfer_id = exemple_transfers(vault)
    
    # Étape 5: Monitoring
    monitor = exemple_monitoring()
    
    # Étape 6: Configuration
    config = exemple_configuration()
    
    # Résumé final
    print("\n" + "="*60)
    print("RÉSUMÉ FINAL")
    print("="*60)
    
    stats = vault.get_stats()
    print(f"Vault: {stats['vault_name']}")
    print(f"  - Actifs: {stats['asset_count']}")
    print(f"  - Documents: {stats['document_count']}")
    print(f"  - Transfers en attente: {stats['pending_transfers']}")
    
    # Exporter le vault
    print(f"\n[!] Pour exporter votre vault:")
    print(f"    vault.export_vault('./mes_backups/')")
    
    print(f"\n[!] Pour lancer l'interface graphique:")
    print(f"    python launch_vault_monitor.py --demo")
    
    return vault


# =============================================================================
# 3. SNIPPETS RAPIDES
# =============================================================================

def snippets():
    """
    Snippets de code réutilisables
    """
    print("\n" + "#"*60)
    print("# SNIPPETS RAPIDES")
    print("#"*60)
    
    print("""
# --- Créer un vault avec mot de passe ---
from core.persistent_vault import PersistentVaultManager
import hashlib

password = "mon_mot_de_passe"
vault_name = "mon_vault"
salt = hashlib.sha256(vault_name.encode()).digest()[:16]
vault_key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
vault = PersistentVaultManager(vault_key, vault_name)


# --- Ajouter un NFT ---
nft_id = vault.add_asset({
    'name': 'Mon NFT',
    'asset_type': 'NFT',
    'contract': '0x...',
    'token_id': '1',
    'chain': 'Ethereum'
})


# --- Stocker un document ---
doc_id = vault.add_document('/chemin/vers/document.pdf')


# --- Programmer un transfer ---
transfer_id = vault.schedule_transfer({
    'transfer_type': 'NFT',
    'asset_id': nft_id,
    'destination': '0x...',
    'delay_days': 30
})


# --- Lancer le monitoring ---
from protocols.vault_monitoring import VaultActivityMonitor
monitor = VaultActivityMonitor(vault_key, vault_name)
monitor.start_monitoring(interval=60)


# --- Exporter le vault ---
vault.export_vault('./backups/')


# --- Lancer l'interface graphique ---
from ui.vault_monitor import VaultMonitorGUI
gui = VaultMonitorGUI(vault_key, vault_name)
gui.run()
    """)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════╗
║     Eidolon - Guide de Démarrage                    ║
║     Exemples d'utilisation du système de vault                   ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Exécuter le workflow complet
        workflow_complet()
        
        # Afficher les snippets
        snippets()
        
        print("\n" + "="*60)
        print("PROCHAINES ÉTAPES")
        print("="*60)
        print("""
1. Lancer l'interface graphique:
   python launch_vault_monitor.py --demo

2. Créer votre propre vault:
   python scripts/vault_launcher.py setup

3. Utiliser le CLI:
   python scripts/vault_launcher.py cli --vault mon_vault --password

4. Lire la documentation:
   - README.md
   - CONTRIBUTING.md
   - config/vault_config.json (configuration)
        """)
        
    except ImportError as e:
        print(f"\n[ERREUR] Module manquant: {e}")
        print("Installez les dépendances: pip install -r requirements.txt")
    except Exception as e:
        print(f"\n[ERREUR] {e}")
        import traceback
        traceback.print_exc()
