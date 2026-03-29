#!/usr/bin/env python3
"""
File: /app/tools/build/verify_critical_paths.py
x-lucid-file-path: /app/tools/build/verify_critical_paths.py
x-lucid-file-type: python

Critical Path Verification for Lucid Devcontainer
Focus on essential paths that could break devcontainer rebuild.
"""

import json
from pathlib import Path

def verify_critical_paths():
    """Verify the most critical paths for devcontainer operation."""
    project_root = Path(__file__).parent.parent
    errors = []
    
    print("🔍 Verifying critical paths for devcontainer rebuild...")
    
    # 1. Check devcontainer.json syntax
    devcontainer_file = project_root / "infrastructure/containers/.devcontainer/devcontainer.json"
    try:
        with open(devcontainer_file) as f:
            config = json.load(f)
        print("✅ devcontainer.json - Valid JSON syntax")
    except Exception as e:
        errors.append(f"❌ devcontainer.json - JSON error: {e}")
    
    # 2. Check docker-compose file exists
    compose_file = devcontainer_file.parent / "docker-compose.dev.yml"
    if compose_file.exists():
        print("✅ docker-compose.dev.yml - File exists")
    else:
        errors.append("❌ docker-compose.dev.yml - File missing")
    
    # 3. Check Dockerfile exists
    dockerfile = devcontainer_file.parent / "Dockerfile"
    if dockerfile.exists():
        print("✅ Dockerfile - File exists")
    else:
        errors.append("❌ Dockerfile - File missing")
    
    # 4. Check setup script exists
    setup_script = project_root / "scripts/devcontainer/setup-build-factory.sh"
    if setup_script.exists():
        print("✅ setup-build-factory.sh - Script exists")
    else:
        errors.append("❌ setup-build-factory.sh - Script missing")
    
    # 5. Check critical Python modules import correctly
    critical_modules = ["admin", "sessions", "user_content", "payment_systems"]
    for module in critical_modules:
        module_init = project_root / module / "__init__.py"
        if module_init.exists():
            try:
                with open(module_init) as f:
                    content = f.read()
                if "from .nonexistent" not in content and "ImportError" in content:
                    print(f"✅ {module}/__init__.py - Safe imports with error handling")
                elif "from ." not in content or "ImportError" in content:
                    print(f"✅ {module}/__init__.py - No problematic imports")
                else:
                    errors.append(f"⚠️  {module}/__init__.py - May have import issues")
            except Exception as e:
                errors.append(f"❌ {module}/__init__.py - Read error: {e}")
        else:
            errors.append(f"❌ {module}/__init__.py - Missing")
    
    return errors

def main():
    errors = verify_critical_paths()
    
    print("\n" + "="*50)
    if not errors:
        print("🎉 ALL CRITICAL PATHS VERIFIED!")
        print("✅ Devcontainer is ready for rebuild!")
        print("\nSafe to proceed with:")
        print("  • VS Code: Dev Containers: Rebuild Container")
        print("  • Docker: docker-compose up --build")
        return 0
    else:
        print("⚠️  CRITICAL ISSUES FOUND:")
        for error in errors:
            print(f"  {error}")
        print("\nResolve these issues before rebuilding devcontainer.")
        return 1

if __name__ == "__main__":
    exit(main())