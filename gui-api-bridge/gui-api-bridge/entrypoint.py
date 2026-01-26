#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI API Bridge Service Entrypoint
UTF-8 encoded entrypoint script for distroless container

This script serves as the entrypoint for the gui-api-bridge container,
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
    port_str = os.getenv('PORT', '8102')
    host = '0.0.0.0'  # Always bind to all interfaces in container
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid PORT value: {port_str}", file=sys.stderr)
        sys.exit(1)
    
    # Import uvicorn and start the application
    try:
        import uvicorn
    except ImportError as e:
        print(f"ERROR: Failed to import uvicorn: {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        from gui_api_bridge.main import app
    except ImportError as e:
        print(f"ERROR: Failed to import gui_api_bridge.main: {e}", file=sys.stderr)
        sys.exit(1)
    
    uvicorn.run(app, host=host, port=port)
