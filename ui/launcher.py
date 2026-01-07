#!/usr/bin/env python3
"""
Eidolon - Main Launcher
Professional CLI interface with ANSI styling
"""

import sys
import os
import time
import subprocess

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    os.system('color')

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# ANSI Colors
# =============================================================================
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_BLUE = '\033[44m'
    BG_CYAN = '\033[46m'


# =============================================================================
# UI Helpers
# =============================================================================
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Print the application header"""
    print(f"""
{Colors.CYAN}{Colors.BOLD}
    ███████╗██╗██████╗  ██████╗ ██╗      ██████╗ ███╗   ██╗
    ██╔════╝██║██╔══██╗██╔═══██╗██║     ██╔═══██╗████╗  ██║
    █████╗  ██║██║  ██║██║   ██║██║     ██║   ██║██╔██╗ ██║
    ██╔══╝  ██║██║  ██║██║   ██║██║     ██║   ██║██║╚██╗██║
    ███████╗██║██████╔╝╚██████╔╝███████╗╚██████╔╝██║ ╚████║
    ╚══════╝╚═╝╚═════╝  ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝  ╚═══╝
{Colors.RESET}
{Colors.DIM}    Quantum-Secured Digital Vault System{Colors.RESET}
{Colors.DIM}    ══════════════════════════════════════════════════════{Colors.RESET}
""")


def print_status(message: str, status: str = "info"):
    """Print a status message"""
    icons = {
        "info": f"{Colors.BLUE}[i]{Colors.RESET}",
        "ok": f"{Colors.GREEN}[✓]{Colors.RESET}",
        "warn": f"{Colors.YELLOW}[!]{Colors.RESET}",
        "error": f"{Colors.RED}[✗]{Colors.RESET}",
        "wait": f"{Colors.CYAN}[~]{Colors.RESET}",
        "run": f"{Colors.MAGENTA}[>]{Colors.RESET}",
    }
    icon = icons.get(status, icons["info"])
    print(f"    {icon} {message}")


def loading_animation(message: str, duration: float = 1.0):
    """Show a simple loading animation"""
    frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        print(f"\r    {Colors.CYAN}{frames[i % len(frames)]}{Colors.RESET} {message}", end='', flush=True)
        time.sleep(0.1)
        i += 1
    print(f"\r    {Colors.GREEN}✓{Colors.RESET} {message}   ")


def print_section(title: str):
    """Print a section header"""
    print(f"""
{Colors.WHITE}{Colors.BOLD}    {title}{Colors.RESET}
{Colors.DIM}    ─────────────────────────────────────{Colors.RESET}
""")


def run_script(script_path: str, args: list = None, wait: bool = True):
    """Run a Python script"""
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    
    try:
        if wait:
            result = subprocess.run(cmd, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            return result.returncode == 0
        else:
            subprocess.Popen(cmd, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            return True
    except Exception as e:
        print_status(f"Error: {e}", "error")
        return False


# =============================================================================
# Menu Functions
# =============================================================================
def print_main_menu():
    """Print the main menu"""
    print(f"""
{Colors.WHITE}{Colors.BOLD}    MAIN MENU{Colors.RESET}
{Colors.DIM}    ─────────────────────────────────────{Colors.RESET}

    {Colors.CYAN}[1]{Colors.RESET} Quick Connect       {Colors.DIM}(Login/Genesis/Key Files){Colors.RESET}
    {Colors.CYAN}[2]{Colors.RESET} Generate New Key    {Colors.DIM}(Create .psnx + .blend_data){Colors.RESET}
    {Colors.CYAN}[3]{Colors.RESET} Vault Monitor       {Colors.DIM}(Full GUI Interface){Colors.RESET}

{Colors.WHITE}{Colors.BOLD}    GENESIS & IDENTITY{Colors.RESET}
{Colors.DIM}    ─────────────────────────────────────{Colors.RESET}

    {Colors.CYAN}[4]{Colors.RESET} List Identities     {Colors.DIM}(Registered identities){Colors.RESET}
    {Colors.CYAN}[5]{Colors.RESET} Sign Genesis Blocks {Colors.DIM}(ECDSA signatures){Colors.RESET}
    {Colors.CYAN}[6]{Colors.RESET} Verify Signatures   {Colors.DIM}(Check block integrity){Colors.RESET}

{Colors.WHITE}{Colors.BOLD}    ASSETS & MONITORING{Colors.RESET}
{Colors.DIM}    ─────────────────────────────────────{Colors.RESET}

    {Colors.CYAN}[7]{Colors.RESET} Runes Portfolio     {Colors.DIM}(Bitcoin Runes balance){Colors.RESET}
    {Colors.CYAN}[8]{Colors.RESET} Asset Statistics    {Colors.DIM}(Items, equipment, potions){Colors.RESET}

{Colors.WHITE}{Colors.BOLD}    SYSTEM{Colors.RESET}
{Colors.DIM}    ─────────────────────────────────────{Colors.RESET}

    {Colors.CYAN}[9]{Colors.RESET} Install Dependencies
    {Colors.CYAN}[K]{Colors.RESET} Open Keys Folder
    {Colors.CYAN}[D]{Colors.RESET} Demo Mode

    {Colors.DIM}[Q]{Colors.RESET} Quit

""")


def quick_connect():
    """Launch Quick Connect interface"""
    print_section("QUICK CONNECT")
    print_status("Launching Quick Connect...", "run")
    print()
    
    script = os.path.join(os.path.dirname(__file__), "quick_connect.py")
    run_script(script)


def generate_key():
    """Generate new vault key"""
    print_section("GENERATE NEW KEY")
    
    # Check machine lock first
    try:
        from core.machine_lock import MachineLock, MachineIdentifier
        lock = MachineLock()
        can_create, message = lock.can_create_vault()
        
        if not can_create:
            print_status("This machine already has a registered vault!", "error")
            print()
            
            vault_info = lock.get_registered_vault()
            if vault_info:
                print(f"    {Colors.YELLOW}Existing Vault:{Colors.RESET} {vault_info.get('vault_name', 'Unknown')}")
                print(f"    {Colors.DIM}Number: #{vault_info.get('vault_number', '?')}{Colors.RESET}")
                print(f"    {Colors.DIM}Created: {vault_info.get('created_at', '')[:19]}{Colors.RESET}")
                print(f"    {Colors.DIM}Machine ID: {MachineIdentifier.get_short_id()}{Colors.RESET}")
            
            print()
            print(f"    {Colors.DIM}Only ONE vault is allowed per machine to ensure{Colors.RESET}")
            print(f"    {Colors.DIM}fair item distribution and rewards.{Colors.RESET}")
            print()
            print_status("Use Quick Connect to access your existing vault", "info")
            return
    except ImportError:
        pass
    
    print(f"    {Colors.DIM}This will create a new cryptographic key pair:{Colors.RESET}")
    print(f"    {Colors.DIM}  • .psnx file (encrypted key data){Colors.RESET}")
    print(f"    {Colors.DIM}  • .blend_data file (3D entropy data){Colors.RESET}")
    print()
    
    confirm = input(f"    {Colors.CYAN}Continue? (y/n):{Colors.RESET} ").strip().lower()
    
    if confirm not in ('y', 'yes', 'o', 'oui'):
        print_status("Cancelled", "info")
        return
    
    print()
    loading_animation("Initializing entropy sources", 0.5)
    
    script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "generate_key.py")
    if os.path.exists(script):
        run_script(script)
    else:
        print_status("Key generator script not found", "error")


def vault_monitor():
    """Launch Vault Monitor GUI"""
    print_section("VAULT MONITOR")
    print_status("Launching Vault Monitor...", "run")
    print()
    
    script = os.path.join(os.path.dirname(__file__), "vault_monitor.py")
    run_script(script, ["--auth"])


def list_identities():
    """List registered identities"""
    print_section("REGISTERED IDENTITIES")
    
    loading_animation("Loading identities", 0.5)
    print()
    
    script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "generate_key.py")
    if os.path.exists(script):
        run_script(script, ["--list"])
    else:
        # Fallback: list from identity registry
        try:
            from core.identity_registry import IdentityRegistry
            registry = IdentityRegistry()
            identities = registry.list_identities()
            
            if not identities:
                print_status("No identities registered", "info")
            else:
                for identity in identities:
                    name = identity.get('name', 'Unknown')
                    created = identity.get('created', '')[:10]
                    print(f"    {Colors.GREEN}•{Colors.RESET} {name} {Colors.DIM}({created}){Colors.RESET}")
        except Exception as e:
            print_status(f"Could not load identities: {e}", "error")


def sign_genesis():
    """Sign genesis blocks"""
    print_section("SIGN GENESIS BLOCKS")
    
    print(f"""
    {Colors.CYAN}[1]{Colors.RESET} Sign all unsigned blocks
    {Colors.CYAN}[2]{Colors.RESET} Sign specific block
    {Colors.CYAN}[3]{Colors.RESET} Back
""")
    
    choice = input(f"    {Colors.CYAN}Select:{Colors.RESET} ").strip()
    
    script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "sign_genesis.py")
    
    if choice == '1':
        loading_animation("Signing blocks", 0.5)
        run_script(script, ["--all"])
    elif choice == '2':
        block_num = input(f"    {Colors.CYAN}Block number:{Colors.RESET} ").strip()
        if block_num.isdigit():
            loading_animation(f"Signing block {block_num}", 0.5)
            run_script(script, ["--block", block_num])
        else:
            print_status("Invalid block number", "error")


def verify_signatures():
    """Verify genesis signatures"""
    print_section("VERIFY SIGNATURES")
    
    loading_animation("Checking signatures", 0.8)
    print()
    
    script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts", "sign_genesis.py")
    run_script(script, ["--list"])
    print()
    run_script(script, ["--verify"])


def runes_portfolio():
    """Show Runes portfolio"""
    print_section("RUNES PORTFOLIO")
    
    loading_animation("Fetching Runes data", 0.8)
    print()
    
    try:
        from core.runes_monitor import RunesMonitor
        monitor = RunesMonitor()
        print(monitor.get_runes_display())
    except ImportError:
        print_status("Runes monitor not available", "error")
    except Exception as e:
        print_status(f"Error: {e}", "error")


def asset_statistics():
    """Show asset statistics"""
    print_section("ASSET STATISTICS")
    
    loading_animation("Counting assets", 0.5)
    print()
    
    from pathlib import Path
    base = Path(os.path.dirname(os.path.dirname(__file__))) / "alchemical_vault"
    
    stats = {
        "Items": len(list((base / "items").glob("*.json"))) if (base / "items").exists() else 0,
        "Equipment": len(list((base / "combat_equipment").glob("*.json"))) if (base / "combat_equipment").exists() else 0,
        "Potions": len(list((base / "potions").glob("*.json"))) if (base / "potions").exists() else 0,
        "Gems": len(list((base / "mobile_gems").glob("*.json"))) if (base / "mobile_gems").exists() else 0,
        "Stones": len(list((base / "philosopher_stones").glob("*.json"))) if (base / "philosopher_stones").exists() else 0,
        "Artifacts": len(list((base / "evolution_artifacts").glob("*.json"))) if (base / "evolution_artifacts").exists() else 0,
    }
    
    total = sum(stats.values())
    
    print(f"    {Colors.WHITE}{Colors.BOLD}Asset Inventory{Colors.RESET}")
    print(f"    {Colors.DIM}─────────────────────────{Colors.RESET}")
    
    for category, count in stats.items():
        if count > 0:
            bar = "█" * min(count // 5, 20)
            print(f"    {category:12} {Colors.GREEN}{count:4}{Colors.RESET} {Colors.DIM}{bar}{Colors.RESET}")
    
    print(f"    {Colors.DIM}─────────────────────────{Colors.RESET}")
    print(f"    {Colors.WHITE}Total:{Colors.RESET}       {Colors.CYAN}{Colors.BOLD}{total:4}{Colors.RESET}")
    
    # Vault count
    vaults = len(list((base / "vaults").glob("vault_*.json"))) if (base / "vaults").exists() else 0
    print()
    print(f"    {Colors.DIM}Vaults: {vaults}{Colors.RESET}")


def install_dependencies():
    """Install Python dependencies"""
    print_section("INSTALL DEPENDENCIES")
    
    print_status("Installing from requirements.txt...", "run")
    print()
    
    req_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "requirements.txt")
    
    if os.path.exists(req_file):
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", req_file])
        print()
        if result.returncode == 0:
            print_status("Dependencies installed successfully", "ok")
        else:
            print_status("Some dependencies failed to install", "warn")
    else:
        print_status("requirements.txt not found", "error")


def open_keys_folder():
    """Open keys folder in file explorer"""
    print_section("KEYS FOLDER")
    
    keys_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "vault_storage", "keys")
    
    if not os.path.exists(keys_path):
        os.makedirs(keys_path, exist_ok=True)
    
    print_status(f"Opening: {keys_path}", "run")
    
    if sys.platform == 'win32':
        os.startfile(keys_path)
    elif sys.platform == 'darwin':
        subprocess.run(['open', keys_path])
    else:
        subprocess.run(['xdg-open', keys_path])


def demo_mode():
    """Launch demo mode"""
    print_section("DEMO MODE")
    
    print(f"    {Colors.DIM}Launching demo environment...{Colors.RESET}")
    print()
    
    # Try demo script first
    demo_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tools", "genesis_evolutif_demo.py")
    
    if os.path.exists(demo_script):
        run_script(demo_script)
    else:
        # Fallback to quick connect demo
        print_status("Launching Quick Connect demo...", "run")
        script = os.path.join(os.path.dirname(__file__), "quick_connect.py")
        run_script(script)


def main():
    """Main entry point"""
    clear_screen()
    print_header()
    
    # System info
    print_status(f"Python {sys.version.split()[0]}", "ok")
    print_status(f"Platform: {sys.platform}", "ok")
    
    # Check machine lock
    try:
        from core.machine_lock import MachineLock, MachineIdentifier
        lock = MachineLock()
        vault_info = lock.get_registered_vault()
        machine_id = MachineIdentifier.get_short_id()
        
        if vault_info:
            print_status(f"Machine ID: {Colors.DIM}{machine_id}{Colors.RESET}", "ok")
            print_status(f"Locked to: {Colors.GREEN}{vault_info.get('vault_name')}{Colors.RESET} (#{vault_info.get('vault_number', '?')})", "ok")
        else:
            print_status(f"Machine ID: {Colors.DIM}{machine_id}{Colors.RESET}", "ok")
            print_status("Machine not locked (can create vault)", "info")
    except:
        pass
    
    # Check for vaults
    try:
        from core.vault_registry import VaultRegistry
        registry = VaultRegistry()
        vaults = registry.get_registered_vaults()
        if vaults:
            print_status(f"{len(vaults)} vault(s) on this device", "ok")
        else:
            print_status("No vaults registered yet", "info")
    except:
        pass
    
    while True:
        print_main_menu()
        
        choice = input(f"    {Colors.CYAN}Select option:{Colors.RESET} ").strip().lower()
        
        if choice == '1':
            clear_screen()
            print_header()
            quick_connect()
            input(f"\n    {Colors.DIM}Press Enter to continue...{Colors.RESET}")
            clear_screen()
            print_header()
            
        elif choice == '2':
            clear_screen()
            print_header()
            generate_key()
            input(f"\n    {Colors.DIM}Press Enter to continue...{Colors.RESET}")
            clear_screen()
            print_header()
            
        elif choice == '3':
            clear_screen()
            print_header()
            vault_monitor()
            clear_screen()
            print_header()
            
        elif choice == '4':
            clear_screen()
            print_header()
            list_identities()
            input(f"\n    {Colors.DIM}Press Enter to continue...{Colors.RESET}")
            clear_screen()
            print_header()
            
        elif choice == '5':
            clear_screen()
            print_header()
            sign_genesis()
            input(f"\n    {Colors.DIM}Press Enter to continue...{Colors.RESET}")
            clear_screen()
            print_header()
            
        elif choice == '6':
            clear_screen()
            print_header()
            verify_signatures()
            input(f"\n    {Colors.DIM}Press Enter to continue...{Colors.RESET}")
            clear_screen()
            print_header()
            
        elif choice == '7':
            clear_screen()
            print_header()
            runes_portfolio()
            input(f"\n    {Colors.DIM}Press Enter to continue...{Colors.RESET}")
            clear_screen()
            print_header()
            
        elif choice == '8':
            clear_screen()
            print_header()
            asset_statistics()
            input(f"\n    {Colors.DIM}Press Enter to continue...{Colors.RESET}")
            clear_screen()
            print_header()
            
        elif choice == '9':
            clear_screen()
            print_header()
            install_dependencies()
            input(f"\n    {Colors.DIM}Press Enter to continue...{Colors.RESET}")
            clear_screen()
            print_header()
            
        elif choice == 'k':
            clear_screen()
            print_header()
            open_keys_folder()
            time.sleep(1)
            clear_screen()
            print_header()
            
        elif choice == 'd':
            clear_screen()
            print_header()
            demo_mode()
            input(f"\n    {Colors.DIM}Press Enter to continue...{Colors.RESET}")
            clear_screen()
            print_header()
            
        elif choice in ('q', 'quit', 'exit'):
            clear_screen()
            print(f"""
{Colors.CYAN}
    Thank you for using Eidolon
    
{Colors.DIM}    "Quantum Security for the Future"{Colors.RESET}

""")
            time.sleep(1)
            sys.exit(0)
            
        else:
            print_status("Invalid option", "warn")
            time.sleep(0.5)
            clear_screen()
            print_header()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_status("Interrupted by user", "warn")
        sys.exit(0)
