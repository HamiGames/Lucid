#!/usr/bin/env python3
"""
Test script for LUCID validation scripts

This script tests the validation scripts to ensure they work correctly.
"""

import sys
import subprocess
from pathlib import Path

def test_python_validation():
    """Test Python validation script"""
    print("Testing Python validation script...")
    
    script_path = Path("scripts/validation/validate-python-build-alignment.py")
    if not script_path.exists():
        print(f"❌ Python validation script not found: {script_path}")
        return False
    
    try:
        result = subprocess.run([sys.executable, str(script_path), "--help"], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ Python validation script is working")
            return True
        else:
            print(f"❌ Python validation script failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing Python validation: {e}")
        return False

def test_gui_validation():
    """Test GUI validation script"""
    print("Testing GUI validation script...")
    
    script_path = Path("scripts/validation/validate-electron_gui-alignment.py")
    if not script_path.exists():
        print(f"❌ GUI validation script not found: {script_path}")
        return False
    
    try:
        result = subprocess.run([sys.executable, str(script_path), "--help"], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ GUI validation script is working")
            return True
        else:
            print(f"❌ GUI validation script failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing GUI validation: {e}")
        return False

def test_complete_validation():
    """Test complete validation script"""
    print("Testing complete validation script...")
    
    script_path = Path("scripts/validation/run-complete-validation.py")
    if not script_path.exists():
        print(f"❌ Complete validation script not found: {script_path}")
        return False
    
    try:
        result = subprocess.run([sys.executable, str(script_path), "--help"], 
                              capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ Complete validation script is working")
            return True
        else:
            print(f"❌ Complete validation script failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error testing complete validation: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing LUCID validation scripts...")
    print("=" * 50)
    
    tests = [
        test_python_validation,
        test_gui_validation,
        test_complete_validation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All validation scripts are working correctly!")
        return True
    else:
        print("❌ Some validation scripts have issues!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
