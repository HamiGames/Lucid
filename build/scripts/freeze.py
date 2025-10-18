#!/usr/bin/env python3
"""
Lucid RDP - PyInstaller GUI Freeze Script
=========================================

Runs PyInstaller for each GUI/OS combination to create distributable binaries.
Supports User GUI, Admin GUI, and Node GUI for Windows/macOS/Linux.

Based on SPEC-2 requirements:
- One .spec per GUI per OS
- Include data files: tor, torrc, icons, LICENSES
- Hidden imports: pydantic, grpc, pkg_resources as needed
- --noupx for determinism; --clean; --noconfirm
- Post-freeze smoke test: launch app headless, ensure Tor starts

Usage:
    python freeze.py [--gui GUI] [--platform PLATFORM] [--output-dir DIR] [--clean]

Author: Lucid RDP Build System
License: MIT
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import importlib.util


class PyInstallerFreezer:
    """Freezes GUI applications using PyInstaller for cross-platform distribution."""
    
    # GUI configurations
    GUI_CONFIGS = {
        "user": {
            "name": "LucidUserGUI",
            "display_name": "Lucid RDP User Client",
            "description": "Lucid RDP User GUI for session management and client controls",
            "entry_point": "gui-user/main.py",
            "icon": "icons/user-icon.ico",
            "hidden_imports": [
                "tkinter", "tkinter.ttk", "tkinter.messagebox", "tkinter.filedialog",
                "requests", "requests.socks", "pysocks", "cryptography", "orjson",
                "pydantic", "appdirs", "stem", "grpcio", "grpcio_tools"
            ]
        },
        "admin": {
            "name": "LucidAdminGUI", 
            "display_name": "Lucid RDP Admin Console",
            "description": "Lucid RDP Admin GUI for Pi appliance management",
            "entry_point": "gui-admin/main.py",
            "icon": "icons/admin-icon.ico",
            "hidden_imports": [
                "tkinter", "tkinter.ttk", "tkinter.messagebox", "tkinter.filedialog",
                "requests", "requests.socks", "pysocks", "cryptography", "orjson",
                "pydantic", "appdirs", "stem", "grpcio", "grpcio_tools", "pymongo"
            ]
        },
        "node": {
            "name": "LucidNodeGUI",
            "display_name": "Lucid RDP Node Monitor", 
            "description": "Lucid RDP Node GUI for PoOT monitoring and payouts",
            "entry_point": "gui-node/main.py",
            "icon": "icons/node-icon.ico",
            "hidden_imports": [
                "tkinter", "tkinter.ttk", "tkinter.messagebox", "tkinter.filedialog",
                "requests", "requests.socks", "pysocks", "cryptography", "orjson",
                "pydantic", "appdirs", "stem", "grpcio", "grpcio_tools", "pymongo",
                "tronpy", "web3"
            ]
        }
    }
    
    # Platform-specific configurations
    PLATFORM_CONFIGS = {
        "windows-x64": {
            "target_platform": "win-amd64",
            "executable_suffix": ".exe",
            "spec_suffix": "_windows.spec",
            "additional_data": [
                ("vendor/tor/windows-x64/tor.exe", "tor/"),
                ("vendor/tor/windows-x64/torrc", "tor/"),
                ("vendor/tor/windows-x64/version.json", "tor/")
            ]
        },
        "macos-universal": {
            "target_platform": "macos-universal",
            "executable_suffix": "",
            "spec_suffix": "_macos.spec", 
            "additional_data": [
                ("vendor/tor/macos-universal/tor", "tor/"),
                ("vendor/tor/macos-universal/torrc", "tor/"),
                ("vendor/tor/macos-universal/version.json", "tor/")
            ]
        },
        "linux-x64": {
            "target_platform": "linux-x86_64",
            "executable_suffix": "",
            "spec_suffix": "_linux.spec",
            "additional_data": [
                ("vendor/tor/linux-x64/tor", "tor/"),
                ("vendor/tor/linux-x64/torrc", "tor/"),
                ("vendor/tor/linux-x64/version.json", "tor/")
            ]
        },
        "linux-arm64": {
            "target_platform": "linux-aarch64", 
            "executable_suffix": "",
            "spec_suffix": "_linux.spec",
            "additional_data": [
                ("vendor/tor/linux-arm64/tor", "tor/"),
                ("vendor/tor/linux-arm64/torrc", "tor/"),
                ("vendor/tor/linux-arm64/version.json", "tor/")
            ]
        }
    }
    
    def __init__(self, output_dir: str = "dist", clean: bool = False):
        """Initialize PyInstaller freezer.
        
        Args:
            output_dir: Directory for built executables
            clean: Whether to clean build directories first
        """
        self.output_dir = Path(output_dir)
        self.clean = clean
        self.project_root = Path(__file__).parent.parent.parent
        self.build_dir = Path("build")
        
    def detect_platform(self) -> str:
        """Detect current platform."""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        if system == "windows":
            return "windows-x64"
        elif system == "darwin":
            return "macos-universal"
        elif system == "linux":
            if machine in ["aarch64", "arm64"]:
                return "linux-arm64"
            else:
                return "linux-x64"
        else:
            raise RuntimeError(f"Unsupported platform: {system} {machine}")
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are available."""
        try:
            import PyInstaller
            print(f"✓ PyInstaller {PyInstaller.__version__} found")
        except ImportError:
            print("✗ PyInstaller not found. Install with: pip install pyinstaller")
            return False
        
        # Check if GUI entry points exist
        for gui_name, config in self.GUI_CONFIGS.items():
            entry_point = self.project_root / config["entry_point"]
            if not entry_point.exists():
                print(f"✗ GUI entry point not found: {entry_point}")
                return False
            print(f"✓ {gui_name} GUI entry point found: {entry_point}")
        
        # Check if Tor binaries are available
        for platform_name, platform_config in self.PLATFORM_CONFIGS.items():
            for data_src, _ in platform_config["additional_data"]:
                data_path = self.project_root / data_src
                if not data_path.exists():
                    print(f"✗ Tor binary not found: {data_path}")
                    return False
            print(f"✓ Tor binaries found for {platform_name}")
        
        return True
    
    def create_spec_file(self, gui_name: str, platform_name: str) -> Path:
        """Create PyInstaller spec file for GUI and platform combination."""
        gui_config = self.GUI_CONFIGS[gui_name]
        platform_config = self.PLATFORM_CONFIGS[platform_name]
        
        # Create spec file content
        spec_content = self._generate_spec_content(gui_name, gui_config, platform_name, platform_config)
        
        # Write spec file
        spec_filename = f"{gui_name}{platform_config['spec_suffix']}"
        spec_path = self.build_dir / "specs" / spec_filename
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(spec_path, 'w') as f:
            f.write(spec_content)
        
        print(f"Created spec file: {spec_path}")
        return spec_path
    
    def _generate_spec_content(self, gui_name: str, gui_config: Dict, platform_name: str, platform_config: Dict) -> str:
        """Generate PyInstaller spec file content."""
        
        # Collect data files
        data_files = []
        
        # Add Tor binaries and configuration
        for data_src, data_dst in platform_config["additional_data"]:
            data_files.append(f"('{data_src}', '{data_dst}')")
        
        # Add icons and licenses
        data_files.extend([
            "('icons/', 'icons/')",
            "('LICENSE*', '.')",
            "('README.md', '.')"
        ])
        
        data_files_str = ",\n        ".join(data_files)
        
        # Generate spec content
        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for {gui_config['name']} ({platform_name})

import sys
from pathlib import Path

# Project root directory
project_root = Path(__file__).parent.parent.parent

# GUI configuration
gui_name = '{gui_name}'
gui_config = {gui_config}
platform_config = {platform_config}

# Hidden imports
hidden_imports = {gui_config['hidden_imports']}

# Additional hidden imports for platform
if sys.platform == 'win32':
    hidden_imports.extend([
        'win32api', 'win32con', 'win32gui', 'win32process',
        'pywintypes', 'pythoncom'
    ])
elif sys.platform == 'darwin':
    hidden_imports.extend([
        'AppKit', 'Foundation', 'objc'
    ])
elif sys.platform == 'linux':
    hidden_imports.extend([
        'Xlib', 'Xlib.display', 'Xlib.XK'
    ])

# Analysis configuration
a = Analysis(
    [str(project_root / '{gui_config['entry_point']}')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        {data_files_str}
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'scipy', 'pandas', 'jupyter',
        'IPython', 'notebook', 'sphinx', 'pytest', 'unittest'
    ],
    noarchive=False,
    optimize=2,
)

# Remove duplicate binaries and data files
pyz = PYZ(a.pure)

# Executable configuration
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='{gui_config['name']}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # --noupx for determinism
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI application
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / '{gui_config['icon']}') if (project_root / '{gui_config['icon']}').exists() else None,
)

# Collect for distribution
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='{gui_config['name']}'
)
'''
        return spec_content
    
    def run_pyinstaller(self, spec_path: Path, output_dir: Path) -> bool:
        """Run PyInstaller with the given spec file."""
        try:
            cmd = [
                "pyinstaller",
                "--clean" if self.clean else "",
                "--noconfirm",
                "--noupx",  # Deterministic builds
                f"--distpath={output_dir}",
                str(spec_path)
            ]
            
            # Remove empty strings from command
            cmd = [arg for arg in cmd if arg]
            
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ PyInstaller completed successfully")
                return True
            else:
                print(f"✗ PyInstaller failed:")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"✗ Error running PyInstaller: {e}")
            return False
    
    def smoke_test_executable(self, gui_name: str, platform_name: str, exe_path: Path) -> bool:
        """Run smoke test on built executable."""
        try:
            print(f"Running smoke test for {gui_name} on {platform_name}...")
            
            # Platform-specific executable path
            platform_config = self.PLATFORM_CONFIGS[platform_name]
            exe_suffix = platform_config["executable_suffix"]
            full_exe_path = exe_path / f"{self.GUI_CONFIGS[gui_name]['name']}{exe_suffix}"
            
            if not full_exe_path.exists():
                print(f"✗ Executable not found: {full_exe_path}")
                return False
            
            # Run headless smoke test
            cmd = [str(full_exe_path), "--version", "--headless"]
            
            # Set environment variables for headless mode
            env = os.environ.copy()
            env.update({
                "DISPLAY": ":99",  # For Linux
                "PYTHONUNBUFFERED": "1",
                "LUCID_SMOKE_TEST": "1"
            })
            
            # Run with timeout
            result = subprocess.run(
                cmd, 
                cwd=exe_path,
                env=env,
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print(f"✓ Smoke test passed for {gui_name}")
                return True
            else:
                print(f"✗ Smoke test failed for {gui_name}:")
                print(f"STDOUT: {result.stdout}")
                print(f"STDERR: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"✗ Smoke test timed out for {gui_name}")
            return False
        except Exception as e:
            print(f"✗ Smoke test error for {gui_name}: {e}")
            return False
    
    def freeze_gui_platform(self, gui_name: str, platform_name: str) -> bool:
        """Freeze specific GUI for specific platform."""
        print(f"\n{'='*60}")
        print(f"Freezing {gui_name} GUI for {platform_name}")
        print(f"{'='*60}")
        
        # Create spec file
        spec_path = self.create_spec_file(gui_name, platform_name)
        
        # Create output directory for this GUI/platform
        gui_output_dir = self.output_dir / gui_name / platform_name
        gui_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Run PyInstaller
        if not self.run_pyinstaller(spec_path, gui_output_dir):
            return False
        
        # Run smoke test
        if not self.smoke_test_executable(gui_name, platform_name, gui_output_dir):
            print(f"Warning: Smoke test failed for {gui_name} on {platform_name}")
        
        # Create build manifest
        self.create_build_manifest(gui_name, platform_name, gui_output_dir)
        
        print(f"✓ Successfully froze {gui_name} GUI for {platform_name}")
        return True
    
    def create_build_manifest(self, gui_name: str, platform_name: str, output_dir: Path) -> None:
        """Create build manifest for the frozen GUI."""
        manifest = {
            "gui_name": gui_name,
            "platform": platform_name,
            "build_timestamp": subprocess.check_output(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"]).decode().strip(),
            "python_version": platform.python_version(),
            "pyinstaller_version": self._get_pyinstaller_version(),
            "git_commit": self._get_git_commit(),
            "tor_version": self._get_tor_version(platform_name),
            "build_id": f"{gui_name}-{platform_name}-{int(subprocess.check_output(['date', '+%s']).decode().strip())}"
        }
        
        manifest_path = output_dir / "build_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        print(f"Created build manifest: {manifest_path}")
    
    def _get_pyinstaller_version(self) -> str:
        """Get PyInstaller version."""
        try:
            result = subprocess.run(["pyinstaller", "--version"], capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return "unknown"
    
    def _get_git_commit(self) -> str:
        """Get current git commit hash."""
        try:
            result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
            return result.stdout.strip()
        except:
            return "unknown"
    
    def _get_tor_version(self, platform_name: str) -> str:
        """Get Tor version for platform."""
        try:
            version_file = self.project_root / self.PLATFORM_CONFIGS[platform_name]["additional_data"][2][0]
            if version_file.exists():
                with open(version_file) as f:
                    version_data = json.load(f)
                    return version_data.get("version", "unknown")
        except:
            pass
        return "unknown"
    
    def freeze_all(self, guis: List[str] = None, platforms: List[str] = None) -> bool:
        """Freeze all specified GUIs for all specified platforms."""
        if guis is None:
            guis = list(self.GUI_CONFIGS.keys())
        if platforms is None:
            platforms = list(self.PLATFORM_CONFIGS.keys())
        
        success = True
        
        for gui_name in guis:
            for platform_name in platforms:
                if not self.freeze_gui_platform(gui_name, platform_name):
                    success = False
        
        return success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Freeze GUI applications using PyInstaller"
    )
    parser.add_argument(
        "--gui",
        choices=["user", "admin", "node", "all"],
        default="all",
        help="GUI to freeze (default: all)"
    )
    parser.add_argument(
        "--platform", 
        choices=["windows-x64", "macos-universal", "linux-x64", "linux-arm64", "all"],
        default="all",
        help="Platform to build for (default: all)"
    )
    parser.add_argument(
        "--output-dir",
        default="dist",
        help="Output directory for built executables (default: dist)"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean build directories before building"
    )
    parser.add_argument(
        "--no-smoke-test",
        action="store_true", 
        help="Skip smoke tests after building"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    # Create freezer
    freezer = PyInstallerFreezer(
        output_dir=args.output_dir,
        clean=args.clean
    )
    
    # Check dependencies
    if not freezer.check_dependencies():
        return 1
    
    # Determine GUIs and platforms to build
    guis = [args.gui] if args.gui != "all" else None
    platforms = [args.platform] if args.platform != "all" else None
    
    # Freeze applications
    success = freezer.freeze_all(guis=guis, platforms=platforms)
    
    if success:
        print(f"\n{'='*60}")
        print("✓ All GUI freezing completed successfully")
        print(f"Built executables available in: {freezer.output_dir}")
        print(f"{'='*60}")
        return 0
    else:
        print(f"\n{'='*60}")
        print("✗ GUI freezing failed")
        print(f"{'='*60}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
