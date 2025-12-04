#!/usr/bin/env python3
"""
Lucid Service Mesh Controller - Entrypoint Script
Distroless-compatible entrypoint that ensures proper Python path setup
"""

import sys
import os
import importlib.util

# Set up Python path explicitly (packages are in /usr/local per Dockerfile - standard location)
site_packages = '/usr/local/lib/python3.11/site-packages'
app_path = '/app'

# Add to sys.path if not already present
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)
if app_path not in sys.path:
    sys.path.insert(0, app_path)

# Set PYTHONPATH environment variable
os.environ['PYTHONPATH'] = f'{app_path}:{site_packages}'

# Verify yaml module is available before proceeding
try:
    yaml_spec = importlib.util.find_spec('yaml', package=None)
    if yaml_spec is None:
        print(f"ERROR: yaml module not found. sys.path: {sys.path}", file=sys.stderr)
        print(f"ERROR: site_packages exists: {os.path.exists(site_packages)}", file=sys.stderr)
        if os.path.exists(site_packages):
            print(f"ERROR: site_packages contents: {os.listdir(site_packages)[:20]}", file=sys.stderr)
        sys.exit(1)
    
    import yaml
    print(f'✅ yaml module loaded: {yaml.__file__}')
except ImportError as e:
    print(f"ERROR: Failed to import yaml: {e}", file=sys.stderr)
    print(f"ERROR: sys.path: {sys.path}", file=sys.stderr)
    sys.exit(1)

# Import and run the main function
try:
    import asyncio
    from controller.main import main
    asyncio.run(main())
except Exception as e:
    print(f"ERROR: Failed to start controller: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

