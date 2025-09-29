#!/usr/bin/env python3

import sys
import traceback

print("Testing FastAPI app imports...")
print(f"Python version: {sys.version}")
print(f"Current working directory: {sys.path[0]}")

try:
    print("\n1. Testing individual router imports...")
    
    from app.routes.meta import router as meta_router
    print("✅ meta_router imported successfully")
    
    from app.routes.auth import router as auth_router  
    print("✅ auth_router imported successfully")
    
    from app.routes.users import router as users_router
    print("✅ users_router imported successfully")
    
    from app.routes.chain_proxy import router as chain_proxy_router
    print("✅ chain_proxy_router imported successfully")
    
    from app.routes.wallets_proxy import router as wallets_proxy_router
    print("✅ wallets_proxy_router imported successfully")
    
    from app.routes.sessions import router as sessions_router
    print("✅ sessions_router imported successfully")
    
    from app.routes.blockchain import router as blockchain_router
    print("✅ blockchain_router imported successfully")
    
    from app.routes.policies import router as policies_router
    print("✅ policies_router imported successfully")
    
    from app.routes.payouts import router as payouts_router
    print("✅ payouts_router imported successfully")
    
    from app.routes.nodes import router as nodes_router
    print("✅ nodes_router imported successfully")
    
    from app.routes.trust_policy import router as trust_policy_router
    print("✅ trust_policy_router imported successfully")
    
    from app.routes.admin import router as admin_router
    print("✅ admin_router imported successfully")
    
    from app.routes.analytics import router as analytics_router
    print("✅ analytics_router imported successfully")
    
    print("\n2. Testing main app import...")
    from app.main import app
    print("✅ SUCCESS: FastAPI app imported with all routers")
    print(f"App title: {app.title}")
    print(f"Total routes: {len(app.routes)}")
    
    print("\n3. Testing route counts by router...")
    route_info = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            route_info.append(f"  {route.methods} {route.path}")
    
    print(f"Found {len(route_info)} routes:")
    for info in route_info[:10]:  # Show first 10 routes
        print(info)
    if len(route_info) > 10:
        print(f"  ... and {len(route_info) - 10} more routes")

except Exception as e:
    print(f"❌ ERROR: {e}")
    print("\nFull traceback:")
    traceback.print_exc()