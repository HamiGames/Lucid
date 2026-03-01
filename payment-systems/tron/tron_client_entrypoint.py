#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRON Client Service Entrypoint
UTF-8 encoded entrypoint script for distroless container
"""

import os
import sys

# Ensure site-packages and app directory are in Python path
site_packages = '/opt/venv/lib/python3.11/site-packages'
app_dir = '/app'

if site_packages not in sys.path:
    sys.path.insert(0, site_packages)
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

if __name__ == "__main__":
    # Set SERVICE_NAME for main.py service detection
    os.environ['SERVICE_NAME'] = 'lucid-tron-client'
    
    port_str = os.getenv('SERVICE_PORT', os.getenv('TRON_CLIENT_PORT', '8091'))
    host = os.getenv('SERVICE_HOST', '0.0.0.0')  # Always bind to all interfaces
    workers_str = os.getenv('WORKERS', '1')
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid SERVICE_PORT value: {port_str}", file=sys.stderr)
        sys.exit(1)
    
    try:
        workers = int(workers_str)
    except ValueError:
        print(f"ERROR: Invalid WORKERS value: {workers_str}", file=sys.stderr)
        sys.exit(1)
    
    try:
        import uvicorn
        from main import app
    except ImportError as e:
        print(f"ERROR: Failed to import: {e}", file=sys.stderr)
        sys.exit(1)
    
    uvicorn.run(app, host=host, port=port, workers=workers)
