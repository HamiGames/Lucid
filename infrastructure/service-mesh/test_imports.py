#!/usr/bin/env python3
"""
Test script to verify service mesh controller imports.
File: infrastructure/service-mesh/test_imports.py
Purpose: Smoke test for service mesh dependencies
"""

import sys
import importlib
import traceback

def test_import(module_name, description):
    """Test importing a module."""
    try:
        importlib.import_module(module_name)
        print(f"✅ {description}: {module_name}")
        return True
    except ImportError as e:
        print(f"❌ {description}: {module_name} - {e}")
        return False
    except Exception as e:
        print(f"⚠️  {description}: {module_name} - {e}")
        return False

def main():
    """Run import tests."""
    print("Testing Service Mesh Controller Dependencies...")
    print("=" * 50)
    
    tests = [
        ("asyncio", "AsyncIO"),
        ("logging", "Logging"),
        ("yaml", "YAML"),
        ("json", "JSON"),
        ("datetime", "DateTime"),
        ("pathlib", "PathLib"),
        ("typing", "Typing"),
        ("enum", "Enum"),
    ]
    
    optional_tests = [
        ("consul", "Consul"),
        ("grpc", "gRPC"),
        ("cryptography", "Cryptography"),
        ("aiohttp", "Async HTTP"),
        ("ssl", "SSL"),
    ]
    
    passed = 0
    total = len(tests)
    
    # Test core dependencies
    for module, desc in tests:
        if test_import(module, desc):
            passed += 1
    
    print("\nOptional Dependencies:")
    print("-" * 30)
    
    for module, desc in optional_tests:
        test_import(module, desc)
    
    print("\n" + "=" * 50)
    print(f"Core dependencies: {passed}/{total} passed")
    
    if passed == total:
        print("✅ All core dependencies available")
        return 0
    else:
        print("❌ Some core dependencies missing")
        return 1

if __name__ == "__main__":
    sys.exit(main())
