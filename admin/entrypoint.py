#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Admin Interface Service Entrypoint
UTF-8 encoded entrypoint script for distroless container

This script serves as the entrypoint for the admin-interface container,
providing clean startup with environment variable configuration.
No hardcoded values - all configuration from environment variables.
"""

import os
import sys

# Ensure site-packages is in Python path (per master-docker-design.md)
site_packages = '/usr/local/lib/python3.11/site-packages'
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

# Ensure app directory is in Python path
app_path = '/app'
if app_path not in sys.path:
    sys.path.insert(0, app_path)

if __name__ == "__main__":
    # Get configuration from environment variables (from docker-compose)
    port_str = os.getenv('ADMIN_INTERFACE_PORT', '8120')
    host = os.getenv('ADMIN_INTERFACE_HOST', '0.0.0.0')  # Configurable host binding
    
    try:
        port = int(port_str)
        if not (1 <= port <= 65535):
            raise ValueError(f"Port {port} out of range")
    except ValueError:
        print(f"ERROR: Invalid ADMIN_INTERFACE_PORT value: {port_str}", file=sys.stderr)
        sys.exit(1)
    
    # Import uvicorn and start the application
    try:
        import uvicorn
    except ImportError as e:
        print(f"ERROR: Failed to import uvicorn: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Start the application with error handling
    try:
        uvicorn.run('admin.main:app', host=host, port=port, log_level='info')
    except Exception as e:
        print(f"ERROR: Failed to start application: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(2)

