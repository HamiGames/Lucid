#!/usr/bin/env python3
"""
Lucid Base Images Test Script
Tests the Python base image functionality
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path

def test_python_imports():
    """Test that all required Python packages can be imported"""
    print("🧪 Testing Python package imports...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'motor',
        'redis',
        'psutil',
        'python_dotenv',
        'yaml',
        'structlog',
        'bcrypt',
        'jose',
        'passlib',
        'dnspython',
        'multipart',
        'dateutil',
        'orjson',
        'cryptography',
        'requests',
        'aiohttp'
    ]
    
    failed_imports = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError as e:
            print(f"  ❌ {package}: {e}")
            failed_imports.append(package)
    
    if failed_imports:
        print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
        return False
    else:
        print("\n✅ All required packages imported successfully")
        return True

def test_environment():
    """Test environment variables and configuration"""
    print("\n🧪 Testing environment configuration...")
    
    # Check Python environment
    python_version = sys.version_info
    print(f"  Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # Check environment variables
    env_vars = ['PYTHONDONTWRITEBYTECODE', 'PYTHONUNBUFFERED', 'LANG', 'LC_ALL']
    for var in env_vars:
        value = os.environ.get(var, 'Not set')
        print(f"  {var}: {value}")
    
    # Check working directory
    cwd = os.getcwd()
    print(f"  Working directory: {cwd}")
    
    # Check if we can write to /app
    app_dir = Path('/app')
    if app_dir.exists():
        print(f"  ✅ /app directory exists")
        if os.access('/app', os.W_OK):
            print(f"  ✅ /app directory is writable")
        else:
            print(f"  ❌ /app directory is not writable")
    else:
        print(f"  ❌ /app directory does not exist")
    
    return True

def test_network_connectivity():
    """Test network connectivity"""
    print("\n🧪 Testing network connectivity...")
    
    try:
        import requests
        response = requests.get('https://httpbin.org/get', timeout=5)
        if response.status_code == 200:
            print("  ✅ HTTP requests working")
            return True
        else:
            print(f"  ❌ HTTP request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Network test failed: {e}")
        return False

def test_system_info():
    """Test system information and resources"""
    print("\n🧪 Testing system information...")
    
    try:
        import psutil
        
        # CPU info
        cpu_count = psutil.cpu_count()
        print(f"  CPU cores: {cpu_count}")
        
        # Memory info
        memory = psutil.virtual_memory()
        print(f"  Total memory: {memory.total / (1024**3):.2f} GB")
        print(f"  Available memory: {memory.available / (1024**3):.2f} GB")
        
        # Disk info
        disk = psutil.disk_usage('/')
        print(f"  Total disk: {disk.total / (1024**3):.2f} GB")
        print(f"  Free disk: {disk.free / (1024**3):.2f} GB")
        
        return True
    except Exception as e:
        print(f"  ❌ System info test failed: {e}")
        return False

def test_security():
    """Test security configuration"""
    print("\n🧪 Testing security configuration...")
    
    # Check if running as non-root
    if os.getuid() == 0:
        print("  ❌ Running as root (security risk)")
        return False
    else:
        print(f"  ✅ Running as non-root user (UID: {os.getuid()})")
    
    # Check environment security
    dangerous_vars = ['PATH', 'LD_LIBRARY_PATH']
    for var in dangerous_vars:
        value = os.environ.get(var, '')
        if '..' in value or ';' in value:
            print(f"  ⚠️  Potentially dangerous {var}: {value}")
        else:
            print(f"  ✅ {var} looks safe")
    
    return True

def main():
    """Main test function"""
    print("🚀 Lucid Python Base Image Test")
    print("================================")
    
    tests = [
        test_python_imports,
        test_environment,
        test_network_connectivity,
        test_system_info,
        test_security
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Python base image is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())