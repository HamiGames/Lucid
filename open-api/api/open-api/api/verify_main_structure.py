#!/usr/bin/env python3
"""
Verify main.py structure and router includes without running full dependencies
"""

import ast
import sys
from pathlib import Path

def analyze_main_py():
    """Analyze main.py structure to verify router includes"""
    
    main_path = Path("app/main.py")
    if not main_path.exists():
        print("❌ ERROR: app/main.py not found")
        return False
    
    with open(main_path, 'r') as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"❌ SYNTAX ERROR in main.py: {e}")
        return False
    
    # Track imports and router includes
    imports = {}
    router_includes = []
    
    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith('app.routes.'):
                for alias in node.names:
                    if alias.name == 'router':
                        router_name = alias.asname or 'router'
                        module_name = node.module.split('.')[-1]  # Get route module name
                        imports[module_name] = router_name
        
        # Check app.include_router calls
        if isinstance(node, ast.Call):
            if (isinstance(node.func, ast.Attribute) and 
                node.func.attr == 'include_router' and
                isinstance(node.func.value, ast.Name) and
                node.func.value.id == 'app'):
                
                if node.args and isinstance(node.args[0], ast.Name):
                    router_includes.append(node.args[0].id)
    
    print("✅ main.py SYNTAX CHECK: PASSED")
    print(f"📊 Found {len(imports)} router imports:")
    for module, router_var in imports.items():
        print(f"  • {module} -> {router_var}")
    
    print(f"📊 Found {len(router_includes)} router includes:")
    for router in router_includes:
        print(f"  • app.include_router({router})")
    
    # Expected routers based on our blueprint implementation
    expected_routers = {
        'meta': 'meta_router',
        'auth': 'auth_router', 
        'users': 'users_router',
        'chain_proxy': 'chain_proxy_router',
        'wallets_proxy': 'wallets_proxy_router',
        'sessions': 'sessions_router',
        'blockchain': 'blockchain_router',
        'policies': 'policies_router',
        'payouts': 'payouts_router',
        'nodes': 'nodes_router',
        'trust_policy': 'trust_policy_router',
        'admin': 'admin_router',
        'analytics': 'analytics_router'
    }
    
    # Verify all expected routers are imported
    missing_imports = []
    for module, expected_var in expected_routers.items():
        if module not in imports:
            missing_imports.append(f"{module} -> {expected_var}")
        elif imports[module] != expected_var:
            missing_imports.append(f"{module} -> {expected_var} (found: {imports[module]})")
    
    # Verify all imported routers are included
    imported_router_vars = set(imports.values())
    included_routers = set(router_includes)
    missing_includes = imported_router_vars - included_routers
    
    if missing_imports:
        print(f"❌ MISSING IMPORTS ({len(missing_imports)}):")
        for missing in missing_imports:
            print(f"  • {missing}")
        return False
    
    if missing_includes:
        print(f"❌ MISSING INCLUDES ({len(missing_includes)}):")
        for missing in missing_includes:
            print(f"  • app.include_router({missing})")
        return False
    
    print("✅ ROUTER IMPORTS: ALL PRESENT")
    print("✅ ROUTER INCLUDES: ALL PRESENT")
    print(f"✅ TOTAL API SURFACE: {len(expected_routers)} router modules integrated")
    
    return True

def check_router_files():
    """Check if all router files exist"""
    
    router_files = [
        'app/routes/meta.py',
        'app/routes/auth.py', 
        'app/routes/users.py',
        'app/routes/chain_proxy.py',
        'app/routes/wallets_proxy.py',
        'app/routes/sessions.py',
        'app/routes/blockchain.py',
        'app/routes/policies.py',
        'app/routes/payouts.py',
        'app/routes/nodes.py',
        'app/routes/trust_policy.py',
        'app/routes/admin.py',
        'app/routes/analytics.py'
    ]
    
    missing_files = []
    for file_path in router_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ MISSING ROUTER FILES ({len(missing_files)}):")
        for missing in missing_files:
            print(f"  • {missing}")
        return False
    
    print(f"✅ ROUTER FILES: All {len(router_files)} files present")
    return True

if __name__ == "__main__":
    print("=== LUCID API MAIN.PY VERIFICATION ===\n")
    
    print("1. Checking router files exist...")
    files_ok = check_router_files()
    print()
    
    print("2. Analyzing main.py structure...")
    structure_ok = analyze_main_py()
    print()
    
    if files_ok and structure_ok:
        print("🎉 SUCCESS: main.py is properly configured with all blueprint routers!")
        print("   Ready for FastAPI application startup")
        sys.exit(0)
    else:
        print("❌ FAILED: Issues found in main.py configuration")
        sys.exit(1)