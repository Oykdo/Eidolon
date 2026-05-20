#!/usr/bin/env python3
"""
Eidolon Daemon CLI
Command-line interface for daemon control and vault operations.

Usage:
    eidolond start [--foreground]
    eidolond stop
    eidolond status
    eidolond vault create <name>
    eidolond vault list
    eidolond vault info <vault_number>
"""

import os
import sys
import argparse
import json
import time
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'


def print_banner():
    """Print Eidolon banner."""
    cyan = '\033[38;2;98;215;217m'
    print(f"""
{Colors.DIM}══════════════════════════════════════════════════════════════{Colors.RESET}
{cyan}{Colors.BOLD}  EIDOLON DAEMON{Colors.RESET}
{Colors.DIM}  Post-Quantum Vault System{Colors.RESET}
{Colors.DIM}══════════════════════════════════════════════════════════════{Colors.RESET}
""")


def print_status(msg: str, status: str = "info"):
    """Print status message."""
    icons = {
        "info": f"{Colors.BLUE}[i]{Colors.RESET}",
        "ok": f"{Colors.GREEN}[✓]{Colors.RESET}",
        "warn": f"{Colors.YELLOW}[!]{Colors.RESET}",
        "error": f"{Colors.RED}[✗]{Colors.RESET}",
    }
    print(f"  {icons.get(status, icons['info'])} {msg}")


def interactive_mode():
    """Interactive menu when launched without arguments."""
    while True:
        print(f"""
  {Colors.BOLD}Menu Principal{Colors.RESET}
  
  {Colors.CYAN}1{Colors.RESET}  Créer un nouveau vault
  {Colors.CYAN}2{Colors.RESET}  Lister les vaults
  {Colors.CYAN}3{Colors.RESET}  Informations sur un vault
  {Colors.CYAN}4{Colors.RESET}  Démarrer le daemon API
  {Colors.CYAN}5{Colors.RESET}  Statut du daemon
  {Colors.CYAN}6{Colors.RESET}  Tester la pipeline (démo)
  {Colors.CYAN}q{Colors.RESET}  Quitter
""")
        try:
            choice = input(f"  {Colors.CYAN}>{Colors.RESET} ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        
        if choice == '1':
            # Create vault
            print()
            try:
                name = input(f"  Nom du vault: ").strip()
                if name:
                    # Create a namespace-like object for args
                    class Args:
                        pass
                    args = Args()
                    args.name = name
                    args.output = None
                    args.pq = True
                    cmd_vault_create(args)
            except (EOFError, KeyboardInterrupt):
                print()
                continue
                
        elif choice == '2':
            # List vaults
            print()
            cmd_vault_list(None)
            
        elif choice == '3':
            # Vault info
            print()
            try:
                num = input(f"  Numéro du vault: ").strip()
                if num.isdigit():
                    class Args:
                        pass
                    args = Args()
                    args.vault_number = int(num)
                    cmd_vault_info(args)
            except (EOFError, KeyboardInterrupt):
                print()
                continue
                
        elif choice == '4':
            # Start daemon
            print()
            class Args:
                pass
            args = Args()
            args.host = "127.0.0.1"
            args.port = 8420
            args.foreground = True
            print_status("Démarrage du daemon (Ctrl+C pour arrêter)...", "info")
            cmd_start(args)
            
        elif choice == '5':
            # Status
            print()
            cmd_status(None)
            
        elif choice == '6':
            # Demo pipeline
            print()
            demo_pipeline()
            
        elif choice in ('q', 'quit', 'exit'):
            print()
            print_status("Au revoir!", "ok")
            break
        
        input(f"\n  {Colors.DIM}Appuyez sur Entrée pour continuer...{Colors.RESET}")
        print_banner()
    
    return 0


def demo_pipeline():
    """Demonstrate the 9-phase pipeline."""
    print_status("Démonstration de la pipeline 9-phases...", "info")
    print()
    
    try:
        import eidolon_crypto
        
        print(f"  {Colors.DIM}Phase 1: Génération du seed maître (512 bits)...{Colors.RESET}")
        print(f"  {Colors.DIM}Phase 2: Capture spatiale 7D + EPR...{Colors.RESET}")
        print(f"  {Colors.DIM}Phase 3: Simulation physique (256 matériaux)...{Colors.RESET}")
        print(f"  {Colors.DIM}Phase 4: Transformation Cl(0,7) (128D)...{Colors.RESET}")
        print(f"  {Colors.DIM}Phase 5: Vérification Bell 7D...{Colors.RESET}")
        print(f"  {Colors.DIM}Phase 6: Hash composite SHA3-512...{Colors.RESET}")
        print(f"  {Colors.DIM}Phase 7: Post-Quantum (Kyber + Dilithium)...{Colors.RESET}")
        print(f"  {Colors.DIM}Phase 8: Dérivation Scrypt + HKDF...{Colors.RESET}")
        print(f"  {Colors.DIM}Phase 9: Arbre Merkle + Genesis...{Colors.RESET}")
        print()
        
        result = eidolon_crypto.pipeline_generate("Demo", True, "granite")
        
        print_status("Pipeline complète!", "ok")
        print()
        print(f"  {Colors.CYAN}Key ID:{Colors.RESET}        {result['key_id']}")
        print(f"  {Colors.CYAN}Merkle Root:{Colors.RESET}   {result['merkle_root'][:32]}...")
        print(f"  {Colors.CYAN}Entropie:{Colors.RESET}      {result['min_entropy_bits']} bits (source)")
        print(f"  {Colors.CYAN}Complexité:{Colors.RESET}    {result['computational_complexity_bits']} bits")
        print(f"  {Colors.CYAN}Post-Quantum:{Colors.RESET}  {'Oui (Kyber1024 + Dilithium5)' if result['pq_enabled'] else 'Non'}")
        print()
        
        if result['pq_enabled']:
            print(f"  {Colors.DIM}Kyber public key:    {len(result['pq_kem_public_key'])} bytes{Colors.RESET}")
            print(f"  {Colors.DIM}Dilithium public key: {len(result['pq_sig_public_key'])} bytes{Colors.RESET}")
            print(f"  {Colors.DIM}Signature:           {len(result['pq_signature'])} bytes{Colors.RESET}")
        
    except ImportError:
        print_status("Module eidolon_crypto non trouvé", "error")
        print_status("Installez avec: pip install eidolon_crypto-*.whl", "info")
    except Exception as e:
        print_status(f"Erreur: {e}", "error")


def cmd_start(args):
    """Start the daemon."""
    from src.daemon.service import get_daemon, DaemonConfig
    
    config = DaemonConfig(
        host=args.host,
        port=args.port,
    )
    daemon = get_daemon(config)
    
    status = daemon.status()
    if status.running:
        print_status(f"Daemon already running (PID {status.pid})", "warn")
        print_status(f"API: {status.api_url}", "info")
        return 1
    
    print_status("Starting Eidolon daemon...", "info")
    
    if args.foreground:
        success = daemon.start(foreground=True)
    else:
        success = daemon.start(foreground=False)
        if success:
            print_status("Daemon started in background", "ok")
            status = daemon.status()
            print_status(f"API: {status.api_url}", "info")
            print_status(f"PID: {status.pid}", "info")
    
    return 0 if success else 1


def cmd_stop(args):
    """Stop the daemon."""
    from src.daemon.service import get_daemon
    
    daemon = get_daemon()
    status = daemon.status()
    
    if not status.running:
        print_status("Daemon is not running", "warn")
        return 1
    
    print_status(f"Stopping daemon (PID {status.pid})...", "info")
    
    pid = status.pid
    if sys.platform == 'win32':
        os.system(f'taskkill /PID {pid} /F >nul 2>&1')
    else:
        os.system(f'kill {pid} 2>/dev/null')
    
    daemon._remove_pid()
    print_status("Daemon stopped", "ok")
    return 0


def cmd_status(args):
    """Show daemon status."""
    from src.daemon.service import get_daemon
    
    daemon = get_daemon()
    status = daemon.status()
    
    if status.running:
        print_status("Daemon is running", "ok")
        print(f"""
  {Colors.DIM}PID:{Colors.RESET}      {status.pid}
  {Colors.DIM}API:{Colors.RESET}      {status.api_url}
  {Colors.DIM}Vaults:{Colors.RESET}   {status.vaults_registered} registered
  {Colors.DIM}Version:{Colors.RESET}  {status.version}
""")
    else:
        print_status("Daemon is not running", "warn")
        print(f"\n  Run {Colors.CYAN}eidolond start{Colors.RESET} to start the daemon\n")
    
    return 0


def cmd_vault_create(args):
    """Create a new vault using the protected Rust pipeline."""
    from src.identity.vault_identity import VaultIdentityManager
    from config.paths import get_keys_dir
    import os
    import json
    import zlib
    import hashlib
    from datetime import datetime
    
    name = args.name
    output_dir = args.output or str(get_keys_dir())
    os.makedirs(output_dir, exist_ok=True)
    
    print_status(f"Creating vault: {name}", "info")
    print_status(f"Output: {output_dir}", "info")
    print()
    
    # Use protected Rust pipeline (required)
    try:
        import eidolon_crypto
        print_status("Using native Rust pipeline (protected)", "ok")
    except ImportError:
        print_status("ERROR: eidolon_crypto module not found", "error")
        print_status("Install with: pip install eidolon_crypto-*.whl", "info")
        return 1
    
    try:
        # Use protected Rust 9-phase pipeline
        enable_pq = args.pq if hasattr(args, 'pq') else True
        print_status(f"Running 9-phase pipeline (PQ: {'enabled' if enable_pq else 'disabled'})...", "info")
        
        result = eidolon_crypto.pipeline_generate(name, enable_pq, "granite")
        
        vault_key = bytes(result['vault_key'])
        key_id = result['key_id']
        
        # Display phase results
        print_status(f"Key ID: {key_id}", "ok")
        print_status(f"Merkle root: {result['merkle_root'][:16]}... ({result['merkle_proof_count']} leaves)", "info")
        print_status(f"Complexity: {result['computational_complexity_bits']} bits", "info")
        if result['pq_enabled']:
            print_status(f"Post-Quantum: Kyber1024 + Dilithium5", "ok")
        
        # Write PSNX file (generated by Rust Phase 9)
        psnx_path = os.path.join(output_dir, f"{name}.psnx")
        with open(psnx_path, 'wb') as f:
            f.write(bytes(result['psnx_bytes']))
        
        # Write blend_data file (generated by Rust Phase 9)
        blend_path = os.path.join(output_dir, f"{name}.blend_data")
        with open(blend_path, 'w', encoding='utf-8') as f:
            f.write(result['blend_json'])
        
        print_status("Vault files created (from Rust genesis)", "ok")
        
        print_status("Registering vault identity...", "info")
        identity_mgr = VaultIdentityManager()
        registered, identity, message = identity_mgr.register_vault(
            vault_name=name,
            psnx_path=str(psnx_path),
            blend_path=str(blend_path),
            vault_key=vault_key,
        )
        
        if registered:
            print()
            print_status("Vault created successfully!", "ok")
            print(f"""
  {Colors.CYAN}Vault Name:{Colors.RESET}    {name}
  {Colors.CYAN}Vault Number:{Colors.RESET}  #{identity.vault_number}
  {Colors.CYAN}Vault ID:{Colors.RESET}      {identity.vault_id[:16]}...
  
  {Colors.CYAN}Files:{Colors.RESET}
    {Colors.DIM}PSNX:{Colors.RESET}       {psnx_path}
    {Colors.DIM}Blend:{Colors.RESET}      {blend_path}

  {Colors.YELLOW}IMPORTANT:{Colors.RESET} Keep both files safe. They are required to unlock your vault.
""")
            return 0
        else:
            print_status(f"Registration failed: {message}", "error")
            return 1
            
    except Exception as e:
        print_status(f"Error: {e}", "error")
        import traceback
        traceback.print_exc()
        return 1


def cmd_vault_list(args):
    """List registered vaults."""
    from src.identity.vault_identity import VaultIdentityManager
    
    try:
        manager = VaultIdentityManager()
        vaults = manager.list_vaults()
        
        if not vaults:
            print_status("No vaults registered", "warn")
            print(f"\n  Run {Colors.CYAN}eidolond vault create <name>{Colors.RESET} to create one\n")
            return 0
        
        print(f"\n  {Colors.BOLD}Registered Vaults ({len(vaults)}){Colors.RESET}\n")
        print(f"  {Colors.DIM}{'#':<6} {'Name':<20} {'Tier':<12} {'EIDOLON':<12}{Colors.RESET}")
        print(f"  {Colors.DIM}{'-'*50}{Colors.RESET}")
        
        for v in vaults:
            tier = getattr(v, 'pioneer_tier', 'standard')
            balance = getattr(v, 'eidolon_balance', 0)
            print(f"  {v.vault_number:<6} {v.vault_name:<20} {tier:<12} {balance:<12.2f}")
        
        print()
        return 0
        
    except Exception as e:
        print_status(f"Error: {e}", "error")
        return 1


def cmd_vault_info(args):
    """Show vault info."""
    from src.identity.vault_identity import VaultIdentityManager
    
    try:
        manager = VaultIdentityManager()
        identity = manager.get_vault_by_number(args.vault_number)
        
        if not identity:
            print_status(f"Vault #{args.vault_number} not found", "error")
            return 1
        
        print(f"""
  {Colors.BOLD}Vault #{identity.vault_number}{Colors.RESET}
  
  {Colors.DIM}Name:{Colors.RESET}           {identity.vault_name}
  {Colors.DIM}ID:{Colors.RESET}             {identity.vault_id}
  {Colors.DIM}Pioneer Tier:{Colors.RESET}   {identity.pioneer_tier}
  {Colors.DIM}EIDOLON:{Colors.RESET}        {identity.eidolon_balance:.4f}
  {Colors.DIM}Resonance:{Colors.RESET}      {identity.resonance_score:.1f}
  {Colors.DIM}Entropy:{Colors.RESET}        {identity.operational_entropy:.1f}
  {Colors.DIM}Holo Depth:{Colors.RESET}     {identity.holographic_depth_level}
  {Colors.DIM}Created:{Colors.RESET}        {identity.created_at}
""")
        return 0
        
    except Exception as e:
        print_status(f"Error: {e}", "error")
        return 1


def main():
    """Main entry point."""
    if sys.platform == 'win32':
        os.system('color')
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    
    parser = argparse.ArgumentParser(
        prog='eidolond',
        description='Eidolon Daemon - Post-Quantum Vault System',
    )
    parser.add_argument('--version', action='version', version='eidolond 1.1.0')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # start
    start_parser = subparsers.add_parser('start', help='Start the daemon')
    start_parser.add_argument('--foreground', '-f', action='store_true', help='Run in foreground')
    start_parser.add_argument('--host', default='127.0.0.1', help='API host (default: 127.0.0.1)')
    start_parser.add_argument('--port', type=int, default=8420, help='API port (default: 8420)')
    
    # stop
    subparsers.add_parser('stop', help='Stop the daemon')
    
    # status
    subparsers.add_parser('status', help='Show daemon status')
    
    # vault
    vault_parser = subparsers.add_parser('vault', help='Vault operations')
    vault_sub = vault_parser.add_subparsers(dest='vault_command', help='Vault commands')
    
    # vault create
    create_parser = vault_sub.add_parser('create', help='Create a new vault')
    create_parser.add_argument('name', help='Vault name')
    create_parser.add_argument('--output', '-o', help='Output directory')
    
    # vault list
    vault_sub.add_parser('list', help='List vaults')
    
    # vault info
    info_parser = vault_sub.add_parser('info', help='Show vault info')
    info_parser.add_argument('vault_number', type=int, help='Vault number')
    
    args = parser.parse_args()
    
    if not args.command:
        print_banner()
        return interactive_mode()
    
    print_banner()
    
    if args.command == 'start':
        return cmd_start(args)
    elif args.command == 'stop':
        return cmd_stop(args)
    elif args.command == 'status':
        return cmd_status(args)
    elif args.command == 'vault':
        if args.vault_command == 'create':
            return cmd_vault_create(args)
        elif args.vault_command == 'list':
            return cmd_vault_list(args)
        elif args.vault_command == 'info':
            return cmd_vault_info(args)
        else:
            vault_parser.print_help()
            return 0
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
