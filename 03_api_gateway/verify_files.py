import sys
import pathlib

build_dir = pathlib.Path('/build')
alt_dir = pathlib.Path('./')
base_dir = build_dir if build_dir.exists() else alt_dir

print(f"=== Verification Starting ===")
print(f"Build dir exists: {build_dir.exists()}")
print(f"Alt dir exists: {alt_dir.exists()}")
print(f"Using base_dir: {base_dir}")
print(f"Base dir is absolute: {base_dir.is_absolute()}")
print(f"=== Checking files ===")

required_files = [
    base_dir / 'api/app/main.py',
    base_dir / 'api/app/middleware/__init__.py',
    base_dir / 'api/app/utils/__init__.py',
    base_dir / 'api/app/schemas/__init__.py',
    base_dir / 'api/app/routers/__init__.py',
    base_dir / 'api/app/routes/__init__.py',
    base_dir / 'api/app/services/__init__.py',
    base_dir / 'api/app/models/__init__.py',
    base_dir / 'api/app/database/__init__.py',
    base_dir / 'api/app/scripts/__init__.py',
    base_dir / 'api/app/security/__init__.py',
    base_dir / 'utils/__init__.py',
    base_dir / 'models/__init__.py',
    base_dir / 'services/__init__.py',
    base_dir / 'database/__init__.py',
    base_dir / 'endpoints/__init__.py',
    base_dir / 'common/__init__.py',
    base_dir / 'sessions/__init__.py'
]

missing = [str(f) for f in required_files if not f.is_file()]

if missing:
    print(f'ERROR: Missing {len(missing)} files:')
    for f in missing:
        print(f'  - {f}')
    sys.exit(1)
else:
    print('✅ All required files present')