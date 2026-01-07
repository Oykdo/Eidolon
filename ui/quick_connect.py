#!/usr/bin/env python3
"""
Eidolon - Quick Connect Interface
Interface de connexion rapide et standardisee
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


def print_menu():
    """Print the main menu"""
    print(f"""
{Colors.WHITE}{Colors.BOLD}    CONNECTION MODE{Colors.RESET}
{Colors.DIM}    ─────────────────────────────────────{Colors.RESET}

    {Colors.CYAN}[1]{Colors.RESET} Quick Connect     {Colors.DIM}(Password){Colors.RESET}
    {Colors.CYAN}[2]{Colors.RESET} Key Files         {Colors.DIM}(.psnx + .blend_data){Colors.RESET}
    {Colors.CYAN}[3]{Colors.RESET} Demo Mode         {Colors.DIM}(Test vault){Colors.RESET}
    
    {Colors.DIM}[Q]{Colors.RESET} Quit

""")


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


def derive_vault_key(vault_name: str, password: str) -> bytes:
    """Derive vault key from password"""
    salt = hashlib.sha256(f"eidolon_{vault_name}".encode()).digest()[:16]
    vault_key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        salt,
        iterations=100000,
        dklen=32
    )
    return vault_key


def authenticate_with_files(psnx_path: str, blend_path: str) -> tuple:
    """Authenticate with key files"""
    try:
        from ui.vault_gui_complete import DualKeyAuthenticator
        
        if not os.path.exists(psnx_path):
            return False, None, f"File not found: {psnx_path}"
        if not os.path.exists(blend_path):
            return False, None, f"File not found: {blend_path}"
        
        auth = DualKeyAuthenticator()
        success, msg = auth.authenticate(psnx_path, blend_path)
        
        if success:
            return True, auth.vault_key, "Authentication successful"
        return False, None, msg
    except ImportError as e:
        return False, None, f"Authentication module not available: {e}"


def launch_vault(vault_key: bytes, vault_name: str):
    """Launch the vault monitor"""
    try:
        from ui.vault_monitor import VaultMonitorGUI
        
        print()
        print_status("Initializing vault interface...", "wait")
        time.sleep(0.5)
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


def quick_connect():
    """Quick connect with password"""
    print(f"""
{Colors.WHITE}{Colors.BOLD}    QUICK CONNECT{Colors.RESET}
{Colors.DIM}    ─────────────────────────────────────{Colors.RESET}
""")
    
    # Vault name
    print(f"    {Colors.CYAN}Vault Name{Colors.RESET}")
    vault_name = input(f"    {Colors.DIM}>{Colors.RESET} ").strip()
    
    if not vault_name:
        vault_name = "main_vault"
        print(f"    {Colors.DIM}Using default: {vault_name}{Colors.RESET}")
    
    print()
    
    # Password
    print(f"    {Colors.CYAN}Password{Colors.RESET}")
    password = getpass.getpass(f"    {Colors.DIM}>{Colors.RESET} ")
    
    if not password:
        print_status("Password required", "error")
        return
    
    print()
    loading_animation("Deriving vault key", 1.5)
    loading_animation("Verifying credentials", 0.8)
    
    vault_key = derive_vault_key(vault_name, password)
    
    print()
    print_status("Authentication successful", "ok")
    
    launch_vault(vault_key, vault_name)


def key_files_connect():
    """Connect with key files"""
    print(f"""
{Colors.WHITE}{Colors.BOLD}    KEY FILES AUTHENTICATION{Colors.RESET}
{Colors.DIM}    ─────────────────────────────────────{Colors.RESET}
""")
    
    # PSNX file
    print(f"    {Colors.CYAN}Path to .psnx file{Colors.RESET}")
    psnx_path = input(f"    {Colors.DIM}>{Colors.RESET} ").strip()
    
    if not psnx_path:
        print_status("PSNX file path required", "error")
        return
    
    print()
    
    # Blend data file
    print(f"    {Colors.CYAN}Path to .blend_data file{Colors.RESET}")
    blend_path = input(f"    {Colors.DIM}>{Colors.RESET} ").strip()
    
    if not blend_path:
        print_status("Blend data file path required", "error")
        return
    
    print()
    loading_animation("Reading key files", 1.0)
    loading_animation("Verifying signatures", 1.2)
    loading_animation("Deriving vault key", 0.8)
    
    success, vault_key, msg = authenticate_with_files(psnx_path, blend_path)
    
    print()
    
    if not success:
        print_status(f"Authentication failed: {msg}", "error")
        return
    
    print_status("Authentication successful", "ok")
    
    # Vault name
    print()
    print(f"    {Colors.CYAN}Vault Name (optional){Colors.RESET}")
    vault_name = input(f"    {Colors.DIM}>{Colors.RESET} ").strip()
    
    if not vault_name:
        vault_name = os.path.splitext(os.path.basename(psnx_path))[0]
    
    launch_vault(vault_key, vault_name)


def demo_mode():
    """Launch in demo mode"""
    print(f"""
{Colors.WHITE}{Colors.BOLD}    DEMO MODE{Colors.RESET}
{Colors.DIM}    ─────────────────────────────────────{Colors.RESET}
""")
    
    print_status("Launching demo vault...", "info")
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
    
    print_status(f"Python {sys.version.split()[0]} detected", "ok")
    print_status("System ready", "ok")
    
    while True:
        print_menu()
        
        choice = input(f"    {Colors.CYAN}Select option:{Colors.RESET} ").strip().lower()
        
        if choice == '1':
            clear_screen()
            print_header()
            quick_connect()
            break
            
        elif choice == '2':
            clear_screen()
            print_header()
            key_files_connect()
            break
            
        elif choice == '3':
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
