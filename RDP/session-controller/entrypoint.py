#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RDP Controller Service Entrypoint
UTF-8 encoded entrypoint script for distroless container

This script serves as the entrypoint for the rdp-controller container,
providing clean startup with environment variable configuration.
No hardcoded values - all configuration from environment variables.
"""

import os
import sys

# Ensure site-packages is in Python path (per master-docker-design.md)
site_packages = '/usr/local/lib/python3.11/site-packages'
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

if __name__ == "__main__":
    # Get configuration from environment variables (from docker-compose)
    port_str = os.getenv('RDP_CONTROLLER_PORT', '8092')
    host = '0.0.0.0'  # Always bind to all interfaces in container
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid RDP_CONTROLLER_PORT value: {port_str}", file=sys.stderr)
        sys.exit(1)
    
    # Import uvicorn and start the application
    try:
        import uvicorn
    except ImportError as e:
        print(f"ERROR: Failed to import uvicorn: {e}", file=sys.stderr)
        print(f"ERROR: Python path: {sys.path}", file=sys.stderr)
        print(f"ERROR: Site packages exists: {os.path.exists(site_packages)}", file=sys.stderr)
        if os.path.exists(site_packages):
            try:
                contents = os.listdir(site_packages)
                print(f"ERROR: Site packages contents (first 20): {contents[:20]}", file=sys.stderr)
            except Exception as list_err:
                print(f"ERROR: Could not list site packages: {list_err}", file=sys.stderr)
        sys.exit(1)
    
    uvicorn.run('session_controller.main:app', host=host, port=port)

