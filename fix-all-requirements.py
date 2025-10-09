#!/usr/bin/env python3
"""
Fix all requirements files to use only available package versions
"""
import os
import re
from pathlib import Path

def fix_requirements_file(file_path):
    """Fix a single requirements file"""
    print(f"Fixing {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Common fixes for problematic packages
    fixes = {
        # Hardware wallet packages - use available versions
        'ledgercomm>=1.3.0': 'ledgercomm>=1.2.2.dev7',
        'ledgercomm>=1.2.2': 'ledgercomm>=1.2.2.dev7',
        'trezorlib>=0.13.0': 'trezorlib>=0.13.0',  # Keep as is
        'hidapi>=0.14.0': 'hidapi>=0.14.0',  # Keep as is
        
        # TRON packages
        'tronapi>=3.2.0': 'tronapi>=3.1.6',
        'tronapi>=3.1.6': 'tronapi>=3.1.6',  # Already fixed
        
        # Non-existent packages - remove or replace
        'python-hsm>=0.9.0': '# python-hsm>=0.9.0  # Package does not exist',
        
        # Other potentially problematic packages
        'asyncio-mqtt>=0.16.0': 'asyncio-mqtt>=0.16.0',  # Keep as is
        'argon2-cffi>=21.3.0': 'argon2-cffi>=21.3.0',  # Keep as is
        'hkdf>=0.0.3': 'hkdf>=0.0.3',  # Keep as is
        'blake3>=0.3.3': 'blake3>=0.3.3',  # Keep as is
    }
    
    # Apply fixes
    for old, new in fixes.items():
        if old in content:
            content = content.replace(old, new)
            print(f"  Fixed: {old} -> {new}")
    
    # Write back
    with open(file_path, 'w') as f:
        f.write(content)

def main():
    """Fix all requirements files"""
    requirements_files = [
        'auth/requirements.auth.txt',
        'sessions/encryption/requirements.encryptor.txt',
        'sessions/core/requirements.chunker.txt',
        'sessions/core/requirements.merkle.txt',
        'sessions/core/requirements.orchestrator.txt',
    ]
    
    for req_file in requirements_files:
        if os.path.exists(req_file):
            fix_requirements_file(req_file)
        else:
            print(f"File not found: {req_file}")
    
    print("\nAll requirements files have been fixed!")

if __name__ == "__main__":
    main()
