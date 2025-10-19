#!/usr/bin/env python3
"""
Test script to verify service mesh controller functionality.
File: infrastructure/service-mesh/test_controller.py
Purpose: Smoke test for service mesh controller components
"""

import sys
import os
import asyncio
import traceback

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_module_syntax(module_path, module_name):
    """Test if a module can be imported and has valid syntax."""
    try:
        # Test syntax compilation
        with open(module_path, 'r') as f:
            code = f.read()
        compile(code, module_path, 'exec')
        print(f"✅ {module_name}: Syntax OK")
        return True
    except SyntaxError as e:
        print(f"❌ {module_name}: Syntax Error - {e}")
        return False
    except Exception as e:
        print(f"⚠️  {module_name}: Error - {e}")
        return False

def test_class_instantiation():
    """Test if classes can be instantiated."""
    try:
        # Test ConfigManager
        from controller.config_manager import ConfigManager
        config_manager = ConfigManager()
        print("✅ ConfigManager: Instantiation OK")
        
        # Test HealthChecker
        from controller.health_checker import HealthChecker
        health_checker = HealthChecker()
        print("✅ HealthChecker: Instantiation OK")
        
        # Test PolicyEngine
        from controller.policy_engine import PolicyEngine
        policy_engine = PolicyEngine()
        print("✅ PolicyEngine: Instantiation OK")
        
        return True
    except Exception as e:
        print(f"❌ Class instantiation failed: {e}")
        traceback.print_exc()
        return False

async def test_async_methods():
    """Test async methods."""
    try:
        from controller.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        
        # Test get_status method (should be synchronous)
        status = config_manager.get_status()
        print("✅ ConfigManager.get_status(): OK")
        
        # Test get_config method
        config = config_manager.get_config()
        print("✅ ConfigManager.get_config(): OK")
        
        return True
    except Exception as e:
        print(f"❌ Async methods test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Service Mesh Controller Smoke Tests")
    print("=" * 40)
    
    # Test syntax
    modules_to_test = [
        ("controller/main.py", "ServiceMeshController"),
        ("controller/config_manager.py", "ConfigManager"),
        ("controller/health_checker.py", "HealthChecker"),
        ("controller/policy_engine.py", "PolicyEngine"),
        ("discovery/consul_client.py", "ConsulClient"),
        ("communication/grpc_server.py", "GRPCServer"),
        ("security/mtls_manager.py", "mTLSManager"),
        ("sidecar/proxy/proxy_manager.py", "ProxyManager"),
    ]
    
    syntax_passed = 0
    for module_path, module_name in modules_to_test:
        if test_module_syntax(module_path, module_name):
            syntax_passed += 1
    
    print(f"\nSyntax tests: {syntax_passed}/{len(modules_to_test)} passed")
    
    # Test class instantiation
    print("\nClass Instantiation Tests:")
    print("-" * 30)
    instantiation_passed = test_class_instantiation()
    
    # Test async methods
    print("\nAsync Methods Tests:")
    print("-" * 25)
    async_passed = asyncio.run(test_async_methods())
    
    print("\n" + "=" * 40)
    total_passed = syntax_passed + (1 if instantiation_passed else 0) + (1 if async_passed else 0)
    total_tests = len(modules_to_test) + 2
    
    print(f"Total tests: {total_passed}/{total_tests} passed")
    
    if total_passed == total_tests:
        print("✅ All smoke tests passed!")
        return 0
    else:
        print("❌ Some smoke tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
