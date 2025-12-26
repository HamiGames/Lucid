#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Storage Service Entrypoint
UTF-8 encoded entrypoint script for distroless container

This script serves as the entrypoint for the session-storage container,
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
    # SESSION_STORAGE_HOST is service name, but bind address must be 0.0.0.0
    port_str = os.getenv('SESSION_STORAGE_PORT', '8082')
    host = '0.0.0.0'  # Always bind to all interfaces in container
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid SESSION_STORAGE_PORT value: {port_str}", file=sys.stderr)
        sys.exit(1)
    
    # Import uvicorn and start the application
    try:
        import uvicorn
    except ImportError as e:
        print(f"ERROR: Failed to import uvicorn: {e}", file=sys.stderr)
        sys.exit(1)
    
    uvicorn.run('sessions.storage.main:app', host=host, port=port)

