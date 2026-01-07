#!/usr/bin/env python3
"""
Eidolon - Quick Connect Interface
Interface de connexion avec gestion des vaults locaux
"""

import sys
import os
import hashlib
import time
import getpass

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    os.system('color')  # Enable ANSI colors on Windows

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.vault_registry import VaultRegistry


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


def get_input(prompt: str, hidden: bool = False) -> str:
    """Get user input with styled prompt"""
    print(f"    {Colors.CYAN}{prompt}{Colors.RESET}")
    if hidden:
        return getpass.getpass(f"    {Colors.DIM}>{Colors.RESET} ")
    return input(f"    {Colors.DIM}>{Colors.RESET} ").strip()


# =============================================================================
# Main Functions
# =============================================================================
def launch_vault(vault_key: bytes, vault_name: str):
    """Launch the vault monitor"""
    try:
        from ui.vault_monitor import VaultMonitorGUI
        
        print()
        print_status("Initializing vault interface...", "wait")
        time.sleep(0.3)
        print_status(f"Vault: {Colors.GREEN}{vault_name}{Colors.RESET}", "ok")
        print_status(f"Key: {Colors.DIM}{vault_key.hex()[:16]}...{Colors.RESET}", "ok")
        print()
        print(f"    {Colors.DIM}Starting GUI...{Colors.RESET}")
        print()
        
        monitor = VaultMonitorGUI(vault_key, vault_name)
        monitor.run()
        
    except ImportError as e:
        print_status(f"Vault monitor not available: {e}", "error")
        sys.exit(1)


def print_menu(registry: VaultRegistry):
    """Print the main menu with registered vaults"""
    vaults = registry.get_registered_vaults()
    
    print(f"""
{Colors.WHITE}{Colors.BOLD}    SELECT ACTION{Colors.RESET}
{Colors.DIM}    ─────────────────────────────────────{Colors.RESET}
""")
    
    if vaults:
        print(f"    {Colors.GREEN}Registered Vaults:{Colors.RESET}")
        for i, vault in enumerate(vaults[:5], 1):  # Show max 5 recent vaults
            last_login = vault.get('last_login', '')[:10] if vault.get('last_login') else 'never'
            print(f"    {Colors.DIM}  • {vault['name']}{Colors.RESET} {Colors.DIM}(last: {last_login}){Colors.RESET}")
        print()
    
    print(f"""    {Colors.CYAN}[1]{Colors.RESET} Login             {Colors.DIM}(Existing vault){Colors.RESET}
    {Colors.CYAN}[2]{Colors.RESET} Genesis           {Colors.DIM}(Create new vault){Colors.RESET}
    {Colors.CYAN}[3]{Colors.RESET} Key Files         {Colors.DIM}(.psnx + .blend_data){Colors.RESET}
    {Colors.CYAN}[4]{Colors.RESET} Demo Mode         {Colors.DIM}(Test vault){Colors.RESET}
    
    {Colors.DIM}[Q]{Colors.RESET} Quit

""")


def login_vault(registry: VaultRegistry):
    """Login to existing vault"""
    print_section("LOGIN TO VAULT")
    
    vaults = registry.get_registered_vaults()
    
    if not vaults:
        print_status("No vaults registered on this device", "warn")
        print_status("Use 'Genesis' to create a new vault", "info")
        print()
        input(f"    {Colors.DIM}Press Enter to continue...{Colors.RESET}")
        return
    
    # Show registered vaults
    print(f"    {Colors.DIM}Registered vaults:{Colors.RESET}")
    for vault in vaults:
        print(f"    {Colors.DIM}  • {vault['name']}{Colors.RESET}")
    print()
    
    # Get vault name
    vault_name = get_input("Vault Name")
    
    if not vault_name:
        print_status("Vault name required", "error")
        return
    
    if not registry.vault_exists(vault_name):
        print_status(f"Vault '{vault_name}' not found", "error")
        print_status("Use 'Genesis' to create a new vault", "info")
        return
    
    print()
    
    # Get password
    password = get_input("Password", hidden=True)
    
    if not password:
        print_status("Password required", "error")
        return
    
    print()
    loading_animation("Verifying credentials", 1.2)
    loading_animation("Deriving vault key", 0.8)
    
    # Authenticate
    success, vault_key, msg = registry.authenticate(vault_name, password)
    
    print()
    
    if not success:
        print_status(msg, "error")
        return
    
    print_status(msg, "ok")
    
    # Launch vault
    launch_vault(vault_key, vault_name)


def genesis_vault(registry: VaultRegistry):
    """Create a new vault (Genesis)"""
    print_section("GENESIS - CREATE NEW VAULT")
    
    print(f"    {Colors.DIM}Create a new vault on this device.{Colors.RESET}")
    print(f"    {Colors.DIM}Your password will be used for all future logins.{Colors.RESET}")
    print()
    
    # Get vault name
    vault_name = get_input("Vault Name")
    
    if not vault_name:
        print_status("Vault name required", "error")
        return
    
    if registry.vault_exists(vault_name):
        print_status(f"Vault '{vault_name}' already exists on this device", "error")
        print_status("Use 'Login' to access it", "info")
        return
    
    print()
    
    # Get password
    print(f"    {Colors.DIM}Password must be at least 8 characters{Colors.RESET}")
    password = get_input("Create Password", hidden=True)
    
    if not password:
        print_status("Password required", "error")
        return
    
    if len(password) < 8:
        print_status("Password must be at least 8 characters", "error")
        return
    
    print()
    
    # Confirm password
    password_confirm = get_input("Confirm Password", hidden=True)
    
    if password != password_confirm:
        print_status("Passwords do not match", "error")
        return
    
    print()
    loading_animation("Generating cryptographic keys", 1.5)
    loading_animation("Creating vault identity", 1.0)
    loading_animation("Securing credentials", 0.8)
    
    # Register vault
    success, vault_key, msg = registry.register_vault(vault_name, password)
    
    print()
    
    if not success:
        print_status(msg, "error")
        return
    
    print_status(msg, "ok")
    print_status(f"Vault '{vault_name}' is now registered on this device", "info")
    
    # Launch vault
    launch_vault(vault_key, vault_name)


def key_files_connect():
    """Connect with key files"""
    print_section("KEY FILES AUTHENTICATION")
    
    # PSNX file
    psnx_path = get_input("Path to .psnx file")
    
    if not psnx_path:
        print_status("PSNX file path required", "error")
        return
    
    # Remove quotes if present (from drag & drop)
    psnx_path = psnx_path.strip('"\'')
    
    if not os.path.exists(psnx_path):
        print_status(f"File not found: {psnx_path}", "error")
        return
    
    print_status(f"PSNX file: {os.path.basename(psnx_path)}", "ok")
    print()
    
    # Blend data file
    blend_path = get_input("Path to .blend_data file")
    
    if not blend_path:
        print_status("Blend data file path required", "error")
        return
    
    # Remove quotes if present
    blend_path = blend_path.strip('"\'')
    
    if not os.path.exists(blend_path):
        print_status(f"File not found: {blend_path}", "error")
        return
    
    print_status(f"Blend file: {os.path.basename(blend_path)}", "ok")
    print()
    
    loading_animation("Reading key files", 1.0)
    loading_animation("Verifying signatures", 1.2)
    loading_animation("Deriving vault key", 0.8)
    
    try:
        from ui.vault_gui_complete import DualKeyAuthenticator
        
        auth = DualKeyAuthenticator()
        success, msg = auth.authenticate(psnx_path, blend_path)
        
        print()
        
        if not success:
            print_status(f"Authentication failed:", "error")
            print(f"    {Colors.DIM}{msg}{Colors.RESET}")
            return
        
        print_status("Authentication successful", "ok")
        
        # Vault name
        print()
        vault_name = get_input("Vault Name (optional)")
        
        if not vault_name:
            vault_name = os.path.splitext(os.path.basename(psnx_path))[0]
        
        launch_vault(auth.vault_key, vault_name)
        
    except ImportError as e:
        print_status(f"Authentication module not available:", "error")
        print(f"    {Colors.DIM}{e}{Colors.RESET}")
    except Exception as e:
        print_status(f"Error during authentication:", "error")
        print(f"    {Colors.DIM}{e}{Colors.RESET}")


def demo_mode():
    """Launch in demo mode"""
    print_section("DEMO MODE")
    
    print_status("Launching demo vault...", "info")
    print(f"    {Colors.DIM}This is a test environment with sample data.{Colors.RESET}")
    print()
    
    loading_animation("Generating demo credentials", 1.0)
    loading_animation("Initializing test environment", 0.8)
    
    vault_key = hashlib.sha256(b"eidolon_demo_vault_2024").digest()
    
    print()
    print_status("Demo vault ready", "ok")
    
    launch_vault(vault_key, "demo_vault")


def main():
    """Main entry point"""
    clear_screen()
    print_header()
    
    # Check Python version
    if sys.version_info < (3, 8):
        print_status("Python 3.8+ required", "error")
        sys.exit(1)
    
    # Initialize registry
    registry = VaultRegistry()
    
    print_status(f"Python {sys.version.split()[0]} detected", "ok")
    print_status(f"Device: {Colors.DIM}{registry._get_device_id()[:12]}...{Colors.RESET}", "ok")
    
    vaults = registry.get_registered_vaults()
    if vaults:
        print_status(f"{len(vaults)} vault(s) registered on this device", "ok")
    else:
        print_status("No vaults registered yet", "info")
    
    while True:
        print_menu(registry)
        
        choice = input(f"    {Colors.CYAN}Select option:{Colors.RESET} ").strip().lower()
        
        if choice == '1':
            clear_screen()
            print_header()
            login_vault(registry)
            break
            
        elif choice == '2':
            clear_screen()
            print_header()
            genesis_vault(registry)
            break
            
        elif choice == '3':
            clear_screen()
            print_header()
            key_files_connect()
            break
            
        elif choice == '4':
            clear_screen()
            print_header()
            demo_mode()
            break
            
        elif choice in ('q', 'quit', 'exit'):
            print()
            print_status("Goodbye!", "info")
            print()
            sys.exit(0)
            
        else:
            print_status("Invalid option", "warn")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_status("Interrupted by user", "warn")
        sys.exit(0)
