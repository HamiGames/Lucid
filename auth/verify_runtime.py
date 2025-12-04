#!/usr/bin/env python3
"""
Lucid Auth Service - Runtime Verification Script
Verifies all source files, imports, and package structure in distroless runtime
"""

import os
import sys
import importlib.util

def verify_source_files():
    """Verify all required source files exist"""
    required_files = [
        '/app/auth/main.py',
        '/app/auth/session_manager.py',
        '/app/auth/config.py',
        '/app/auth/authentication_service.py',
        '/app/auth/user_manager.py',
        '/app/auth/hardware_wallet.py',
        '/app/auth/permissions.py',
        '/app/auth/healthcheck.py',
    ]
    
    required_dirs = [
        '/app/auth/api',
        '/app/auth/middleware',
        '/app/auth/models',
        '/app/auth/utils',
    ]
    
    errors = []
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            errors.append(f'ERROR: {file_path} missing')
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            errors.append(f'ERROR: {dir_path} directory missing')
    
    # Check marker file
    marker_path = '/app/auth/middleware/.lucid-middleware-marker'
    if not os.path.exists(marker_path):
        errors.append(f'ERROR: middleware marker file missing: {marker_path}')
    
    # Check for unwanted cache files
    cache_dirs = [
        '/app/auth/api/__pycache__',
        '/app/auth/middleware/__pycache__',
        '/app/auth/models/__pycache__',
        '/app/auth/utils/__pycache__',
    ]
    
    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            errors.append(f'ERROR: __pycache__ found in {cache_dir}')
    
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return False
    
    print('✅ All source files and directories verified')
    return True


def verify_module_imports():
    """Verify auth.main module can be imported"""
    try:
        spec = importlib.util.find_spec('auth.main', package=None)
        if spec is None:
            print('ERROR: auth.main module not importable', file=sys.stderr)
            return False
        print('✅ auth.main module is importable')
        return True
    except Exception as e:
        print(f'ERROR: Failed to import auth.main: {e}', file=sys.stderr)
        return False


def verify_route_imports():
    """Verify all route files have correct imports (auth.models.* not models.*)"""
    route_files = [
        '/app/auth/api/auth_routes.py',
        '/app/auth/api/user_routes.py',
        '/app/auth/api/session_routes.py',
        '/app/auth/api/hardware_wallet_routes.py',
    ]
    
    errors = []
    
    for route_file in route_files:
        if not os.path.exists(route_file):
            errors.append(f'ERROR: Route file missing: {route_file}')
            continue
        
        try:
            with open(route_file, 'r') as f:
                content = f.read()
            
            # Check for correct imports
            if 'from auth.models.' not in content and 'from auth.' not in content:
                errors.append(f'ERROR: {route_file} missing auth.models.* or auth.* imports')
            
            # Check for incorrect imports
            if 'from models.' in content:
                errors.append(f'ERROR: {route_file} contains incorrect import from models.* (should be from auth.models.*)')
            
            if 'import models' in content:
                errors.append(f'ERROR: {route_file} contains incorrect import models (should be auth.models)')
            
            print(f'✅ Verified imports in {os.path.basename(route_file)}')
            
        except Exception as e:
            errors.append(f'ERROR: Failed to read {route_file}: {e}')
    
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return False
    
    return True


def main():
    """Main verification function"""
    print('Starting runtime verification...')
    
    success = True
    
    # Verify source files
    if not verify_source_files():
        success = False
    
    # Verify module imports
    if not verify_module_imports():
        success = False
    
    # Verify route imports
    if not verify_route_imports():
        success = False
    
    if success:
        print('✅ Auth source code verified in runtime stage - correct imports and no unwanted files present')
        sys.exit(0)
    else:
        print('❌ Runtime verification failed', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

