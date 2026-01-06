#!/usr/bin/env python3
"""
Poly-Spinor Nexus 7D - Multi-Platform Build Script

Builds standalone executables for Windows, macOS, and Linux using PyInstaller.

Usage:
    python build_all_platforms.py              # Build for current platform
    python build_all_platforms.py --all        # Build for all platforms (requires cross-compilation setup)
    python build_all_platforms.py --platform windows
    python build_all_platforms.py --clean      # Clean build artifacts
"""

import os
import sys
import shutil
import subprocess
import platform
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# =============================================================================
# Configuration
# =============================================================================

PROJECT_NAME = "PolySpinorNexus7D"
VERSION = "1.0.0"
AUTHOR = "Poly-Spinor Team"

# Directories
ROOT_DIR = Path(__file__).parent.parent
BUILD_DIR = ROOT_DIR / "build"
DIST_DIR = ROOT_DIR / "dist"
SPEC_DIR = ROOT_DIR / "specs"

# Entry points
ENTRY_POINTS = {
    "vault_monitor": {
        "script": "launch_vault_monitor.py",
        "name": "VaultMonitor",
        "icon": "assets/icons/vault_monitor",
        "console": False,
    },
    "vault_launcher": {
        "script": "scripts/vault_launcher.py",
        "name": "VaultLauncher",
        "icon": "assets/icons/vault_launcher",
        "console": True,
    },
    "vault_cli": {
        "script": "scripts/vault_launcher.py",
        "name": "VaultCLI",
        "icon": "assets/icons/vault_cli",
        "console": True,
    },
}

# Platform-specific configurations
PLATFORM_CONFIG = {
    "windows": {
        "extension": ".exe",
        "icon_ext": ".ico",
        "separator": ";",
        "hidden_imports": [
            "win32api",
            "win32con",
            "pywintypes",
        ],
    },
    "darwin": {
        "extension": ".app",
        "icon_ext": ".icns",
        "separator": ":",
        "hidden_imports": [
            "AppKit",
            "Foundation",
        ],
    },
    "linux": {
        "extension": "",
        "icon_ext": ".png",
        "separator": ":",
        "hidden_imports": [],
    },
}

# Common hidden imports
COMMON_HIDDEN_IMPORTS = [
    "cryptography",
    "cryptography.fernet",
    "cryptography.hazmat.primitives",
    "cryptography.hazmat.primitives.ciphers",
    "cryptography.hazmat.primitives.kdf.pbkdf2",
    "cryptography.hazmat.primitives.kdf.scrypt",
    "cryptography.hazmat.backends.openssl",
    "numpy",
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
    "tkinter",
    "tkinter.ttk",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "json",
    "hashlib",
    "secrets",
    "threading",
    "queue",
    "dataclasses",
    "typing",
    "pathlib",
    "datetime",
    "enum",
    "collections",
    "base64",
    "zlib",
    "struct",
]

# Data files to include
DATA_FILES = [
    ("config/*.json", "config"),
    ("config/*.yaml", "config"),
    ("assets/icons/*", "assets/icons"),
    ("README.md", "."),
    ("LICENSE", "."),
]

# Excluded modules (reduce size)
EXCLUDED_MODULES = [
    "matplotlib",
    "scipy",
    "pandas",
    "IPython",
    "notebook",
    "jupyter",
    "pytest",
    "sphinx",
    "setuptools",
    "pip",
    "wheel",
]


# =============================================================================
# Helper Functions
# =============================================================================

def get_current_platform() -> str:
    """Get current platform identifier."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "darwin":
        return "darwin"
    else:
        return "linux"


def ensure_pyinstaller():
    """Ensure PyInstaller is installed."""
    try:
        import PyInstaller
        print(f"[OK] PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("[INFO] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller installed")


def clean_build():
    """Clean build artifacts."""
    print("[INFO] Cleaning build artifacts...")
    
    dirs_to_clean = [BUILD_DIR, DIST_DIR, SPEC_DIR]
    
    for dir_path in dirs_to_clean:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"  Removed: {dir_path}")
    
    # Clean .spec files in root
    for spec_file in ROOT_DIR.glob("*.spec"):
        spec_file.unlink()
        print(f"  Removed: {spec_file}")
    
    # Clean __pycache__
    for pycache in ROOT_DIR.rglob("__pycache__"):
        shutil.rmtree(pycache)
    
    print("[OK] Clean complete")


def create_directories():
    """Create necessary directories."""
    for dir_path in [BUILD_DIR, DIST_DIR, SPEC_DIR]:
        dir_path.mkdir(parents=True, exist_ok=True)
    
    # Create assets/icons if not exists
    icons_dir = ROOT_DIR / "assets" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)


def get_icon_path(entry_config: Dict, target_platform: str) -> Optional[str]:
    """Get icon path for platform."""
    icon_base = entry_config.get("icon")
    if not icon_base:
        return None
    
    icon_ext = PLATFORM_CONFIG[target_platform]["icon_ext"]
    icon_path = ROOT_DIR / f"{icon_base}{icon_ext}"
    
    if icon_path.exists():
        return str(icon_path)
    return None


def generate_spec_file(entry_name: str, entry_config: Dict, target_platform: str) -> Path:
    """Generate PyInstaller spec file."""
    platform_cfg = PLATFORM_CONFIG[target_platform]
    
    script_path = ROOT_DIR / entry_config["script"]
    app_name = entry_config["name"]
    is_console = entry_config.get("console", True)
    icon_path = get_icon_path(entry_config, target_platform)
    
    # Collect hidden imports
    hidden_imports = COMMON_HIDDEN_IMPORTS + platform_cfg.get("hidden_imports", [])
    hidden_imports_str = ",\n        ".join([f"'{imp}'" for imp in hidden_imports])
    
    # Collect data files
    datas_str = ""
    for src, dest in DATA_FILES:
        src_path = ROOT_DIR / src
        if any(src_path.parent.glob(src_path.name)):
            datas_str += f"    ('{src}', '{dest}'),\n"
    
    # Excluded modules
    excludes_str = ",\n        ".join([f"'{mod}'" for mod in EXCLUDED_MODULES])
    
    # Generate spec content
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
# Auto-generated spec file for {app_name}
# Platform: {target_platform}
# Generated: {datetime.now().isoformat()}

import sys
from pathlib import Path

block_cipher = None

# Project root
ROOT = Path(r'{ROOT_DIR}')

a = Analysis(
    [r'{script_path}'],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
{datas_str}    ],
    hiddenimports=[
        {hidden_imports_str}
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        {excludes_str}
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{app_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console={is_console},
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
'''
    
    if icon_path:
        spec_content += f"    icon=r'{icon_path}',\n"
    
    spec_content += ")\n"
    
    # macOS specific: create .app bundle
    if target_platform == "darwin" and not is_console:
        spec_content += f'''
app = BUNDLE(
    exe,
    name='{app_name}.app',
    icon=r'{icon_path}' if {bool(icon_path)} else None,
    bundle_identifier='io.polyspinor.{app_name.lower()}',
    info_plist={{
        'CFBundleName': '{app_name}',
        'CFBundleDisplayName': '{app_name}',
        'CFBundleVersion': '{VERSION}',
        'CFBundleShortVersionString': '{VERSION}',
        'NSHighResolutionCapable': True,
    }},
)
'''
    
    # Write spec file
    spec_path = SPEC_DIR / f"{app_name}_{target_platform}.spec"
    spec_path.write_text(spec_content)
    
    return spec_path


def build_executable(spec_path: Path, target_platform: str) -> bool:
    """Build executable from spec file."""
    print(f"\n[INFO] Building from {spec_path.name}...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        f"--distpath={DIST_DIR / target_platform}",
        f"--workpath={BUILD_DIR / target_platform}",
        str(spec_path),
    ]
    
    try:
        subprocess.check_call(cmd, cwd=ROOT_DIR)
        print(f"[OK] Build successful: {spec_path.stem}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Build failed: {e}")
        return False


def create_archive(platform_name: str) -> Optional[Path]:
    """Create distribution archive."""
    dist_platform_dir = DIST_DIR / platform_name
    
    if not dist_platform_dir.exists():
        return None
    
    archive_name = f"{PROJECT_NAME}-{VERSION}-{platform_name}"
    
    if platform_name == "windows":
        archive_path = DIST_DIR / f"{archive_name}.zip"
        shutil.make_archive(
            str(DIST_DIR / archive_name),
            "zip",
            dist_platform_dir
        )
    else:
        archive_path = DIST_DIR / f"{archive_name}.tar.gz"
        shutil.make_archive(
            str(DIST_DIR / archive_name),
            "gztar",
            dist_platform_dir
        )
    
    print(f"[OK] Archive created: {archive_path.name}")
    return archive_path


def build_for_platform(target_platform: str, entries: List[str] = None) -> bool:
    """Build all entries for a specific platform."""
    print(f"\n{'='*60}")
    print(f"Building for {target_platform.upper()}")
    print('='*60)
    
    if entries is None:
        entries = list(ENTRY_POINTS.keys())
    
    success = True
    
    for entry_name in entries:
        if entry_name not in ENTRY_POINTS:
            print(f"[WARN] Unknown entry point: {entry_name}")
            continue
        
        entry_config = ENTRY_POINTS[entry_name]
        
        # Generate spec file
        spec_path = generate_spec_file(entry_name, entry_config, target_platform)
        print(f"[OK] Generated spec: {spec_path.name}")
        
        # Build executable
        if not build_executable(spec_path, target_platform):
            success = False
    
    # Create archive
    if success:
        create_archive(target_platform)
    
    return success


def generate_build_info():
    """Generate build information file."""
    build_info = {
        "project": PROJECT_NAME,
        "version": VERSION,
        "build_date": datetime.now().isoformat(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "entries": list(ENTRY_POINTS.keys()),
    }
    
    info_path = DIST_DIR / "build_info.json"
    info_path.write_text(json.dumps(build_info, indent=2))
    print(f"[OK] Build info: {info_path}")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Build Poly-Spinor Nexus 7D for multiple platforms"
    )
    parser.add_argument(
        "--platform", "-p",
        choices=["windows", "darwin", "linux", "current"],
        default="current",
        help="Target platform (default: current)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Build for all platforms"
    )
    parser.add_argument(
        "--entry", "-e",
        action="append",
        help="Specific entry point to build (can be repeated)"
    )
    parser.add_argument(
        "--clean", "-c",
        action="store_true",
        help="Clean build artifacts"
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Don't create distribution archive"
    )
    
    args = parser.parse_args()
    
    print(f"\n{'#'*60}")
    print(f"# Poly-Spinor Nexus 7D - Build System")
    print(f"# Version: {VERSION}")
    print(f"{'#'*60}\n")
    
    # Clean if requested
    if args.clean:
        clean_build()
        if not args.all and args.platform == "current":
            return
    
    # Ensure PyInstaller
    ensure_pyinstaller()
    
    # Create directories
    create_directories()
    
    # Determine platforms to build
    if args.all:
        # Note: Cross-compilation requires special setup
        print("[WARN] Cross-compilation requires platform-specific setup")
        platforms = ["windows", "darwin", "linux"]
    elif args.platform == "current":
        platforms = [get_current_platform()]
    else:
        platforms = [args.platform]
    
    # Build for each platform
    results = {}
    for target_platform in platforms:
        current = get_current_platform()
        
        if target_platform != current:
            print(f"[WARN] Cross-compilation to {target_platform} from {current}")
            print("       This may not work without proper setup")
        
        results[target_platform] = build_for_platform(
            target_platform,
            args.entry
        )
    
    # Generate build info
    generate_build_info()
    
    # Summary
    print(f"\n{'='*60}")
    print("BUILD SUMMARY")
    print('='*60)
    
    for plat, success in results.items():
        status = "SUCCESS" if success else "FAILED"
        print(f"  {plat}: {status}")
    
    print(f"\nOutput directory: {DIST_DIR}")
    
    # Exit with appropriate code
    if all(results.values()):
        print("\n[OK] All builds completed successfully!")
        sys.exit(0)
    else:
        print("\n[ERROR] Some builds failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
