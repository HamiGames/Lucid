#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Node Management Service Entrypoint
UTF-8 encoded entrypoint script for distroless container

This script serves as the entrypoint for the node-management container,
providing clean startup with environment variable configuration.
No hardcoded values - all configuration from environment variables.
"""

import os
import sys

# Ensure site-packages is in sys.path for distroless containers
# This must happen BEFORE any application imports
site_packages = '/usr/local/lib/python3.11/site-packages'
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

if __name__ == "__main__":
    # Get configuration from environment variables (from docker-compose)
    port_str = os.getenv('NODE_MANAGEMENT_PORT', '8095')
    host = '0.0.0.0'  # Always bind to all interfaces in container
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid NODE_MANAGEMENT_PORT value: {port_str}", file=sys.stderr)
        sys.exit(1)
    
    # Import uvicorn and start the application
    try:
        import uvicorn
    except ImportError as e:
        print(f"ERROR: Failed to import uvicorn: {e}", file=sys.stderr)
        sys.exit(1)
    
    uvicorn.run('node.main:app', host=host, port=port)

