#!/usr/bin/env python3
"""
Script to fix database imports in all node modules to use the database adapter.
"""

import os
import re
from pathlib import Path

def fix_motor_imports(file_path):
    """Fix motor imports in a specific file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace motor import with database adapter import
        content = re.sub(
            r'from motor\.motor_asyncio import AsyncIOMotorDatabase',
            '# Database adapter handles compatibility\nfrom ..database_adapter import DatabaseAdapter, get_database_adapter',
            content
        )
        
        # Replace AsyncIOMotorDatabase type hints
        content = re.sub(
            r'AsyncIOMotorDatabase',
            'DatabaseAdapter',
            content
        )
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Fixed: {file_path}")
            return True
        else:
            print(f"- No changes: {file_path}")
            return False
            
    except Exception as e:
        print(f"✗ Error fixing {file_path}: {e}")
        return False

def fix_optional_imports(file_path):
    """Make optional imports safer"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Make aiohttp import optional
        if 'import aiohttp' in content and 'try:' not in content.split('import aiohttp')[0][-50:]:
            content = re.sub(
                r'import aiohttp',
                '''# Optional aiohttp import
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    AIOHTTP_AVAILABLE = False''',
                content,
                count=1
            )
        
        # Make cryptography imports optional
        if 'from cryptography' in content:
            # Find cryptography imports and make them optional
            crypto_imports = re.findall(r'from cryptography[^\n]*', content)
            if crypto_imports:
                for crypto_import in crypto_imports:
                    content = content.replace(
                        crypto_import,
                        f'''# Optional cryptography import
try:
    {crypto_import}
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    # Create mock classes if needed'''
                    )
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ Fixed optional imports: {file_path}")
            return True
        else:
            return False
            
    except Exception as e:
        print(f"✗ Error fixing optional imports in {file_path}: {e}")
        return False

def main():
    """Main function"""
    project_root = Path(__file__).parent.parent
    node_dir = project_root / "node"
    
    print("Fixing node module imports...")
    print("=" * 50)
    
    # Find all Python files in node subdirectories
    python_files = []
    for subdir in ["flags", "governance", "validation", "sync", "pools", "registration", "shards"]:
        subdir_path = node_dir / subdir
        if subdir_path.exists():
            for py_file in subdir_path.glob("*.py"):
                python_files.append(py_file)
    
    if not python_files:
        print("No Python files found to fix")
        return
    
    fixed_count = 0
    
    # Fix motor imports
    print("\nFixing motor imports...")
    for py_file in python_files:
        if fix_motor_imports(py_file):
            fixed_count += 1
    
    # Fix optional imports
    print("\nFixing optional imports...")
    for py_file in python_files:
        if fix_optional_imports(py_file):
            fixed_count += 1
    
    print(f"\n✓ Fixed {fixed_count} files")
    print("Import fixes complete!")

if __name__ == "__main__":
    main()