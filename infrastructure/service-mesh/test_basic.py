#!/usr/bin/env python3
"""
Basic smoke test for service mesh controller without external dependencies.
File: infrastructure/service-mesh/test_basic.py
Purpose: Basic functionality test
"""

import sys
import os
import traceback

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config_manager():
    """Test ConfigManager basic functionality."""
    try:
        from controller.config_manager import ConfigManager
        
        # Create instance
        config_manager = ConfigManager()
        
        # Test basic methods
        config = config_manager.get_config()
        status = config_manager.get_status()
        
        print("✅ ConfigManager: Basic functionality OK")
        return True
    except Exception as e:
        print(f"❌ ConfigManager failed: {e}")
        return False

def test_policy_engine():
    """Test PolicyEngine basic functionality."""
    try:
        from controller.policy_engine import PolicyEngine
        
        # Create instance
        policy_engine = PolicyEngine()
        
        # Test basic methods
        policies = policy_engine.get_all_policies()
        status = policy_engine.get_status()
        
        print("✅ PolicyEngine: Basic functionality OK")
        return True
    except Exception as e:
        print(f"❌ PolicyEngine failed: {e}")
        return False

def test_main_controller():
    """Test main controller basic functionality."""
    try:
        from controller.main import ServiceMeshController
        
        # Create instance
        controller = ServiceMeshController()
        
        # Test basic methods
        status = controller.get_status()
        
        print("✅ ServiceMeshController: Basic functionality OK")
        return True
    except Exception as e:
        print(f"❌ ServiceMeshController failed: {e}")
        return False

def test_file_structure():
    """Test that all required files exist."""
    required_files = [
        "controller/main.py",
        "controller/config_manager.py", 
        "controller/health_checker.py",
        "controller/policy_engine.py",
        "discovery/consul_client.py",
        "communication/grpc_server.py",
        "security/mtls_manager.py",
        "sidecar/proxy/proxy_manager.py",
        "sidecar/envoy/config/bootstrap.yaml",
        "requirements.txt"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def test_dockerfile():
    """Test Dockerfile syntax and structure."""
    try:
        dockerfile_path = "../../service-mesh/Dockerfile.controller"
        if not os.path.exists(dockerfile_path):
            print("❌ Dockerfile not found")
            return False
            
        with open(dockerfile_path, 'r') as f:
            content = f.read()
            
        # Basic Dockerfile validation
        if "FROM python:3.11-slim as builder" not in content:
            print("❌ Missing builder stage")
            return False
            
        if "FROM gcr.io/distroless/python3-debian12" not in content:
            print("❌ Missing distroless stage")
            return False
            
        if "CMD [\"python\", \"-m\", \"controller.main\"]" not in content:
            print("❌ Missing CMD instruction")
            return False
            
        print("✅ Dockerfile structure OK")
        return True
    except Exception as e:
        print(f"❌ Dockerfile test failed: {e}")
        return False

def main():
    """Run basic smoke tests."""
    print("Service Mesh Controller Basic Smoke Tests")
    print("=" * 45)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Dockerfile", test_dockerfile),
        ("ConfigManager", test_config_manager),
        ("PolicyEngine", test_policy_engine),
        ("ServiceMeshController", test_main_controller),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * len(test_name))
        if test_func():
            passed += 1
    
    print("\n" + "=" * 45)
    print(f"Basic tests: {passed}/{total} passed")
    
    if passed == total:
        print("✅ All basic smoke tests passed!")
        return 0
    else:
        print("❌ Some basic smoke tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
