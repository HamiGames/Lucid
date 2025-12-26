#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RDP Resource Monitor Service Entrypoint
UTF-8 encoded entrypoint script for distroless container

This script serves as the entrypoint for the rdp-monitor container,
providing clean startup with environment variable configuration.
No hardcoded values - all configuration from environment variables.
"""

import os
import sys

# Ensure site-packages and app directory are in Python path (defensive programming)
site_packages = '/usr/local/lib/python3.11/site-packages'
app_path = '/app'

# Add to sys.path if not already present (order matters - app_path first so our modules take precedence)
if app_path not in sys.path:
    sys.path.insert(0, app_path)
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

if __name__ == "__main__":
    # Get configuration from environment variables (from docker-compose)
    # RDP_MONITOR_HOST is service name, but bind address must be 0.0.0.0
    port_str = os.getenv('RDP_MONITOR_PORT', os.getenv('MONITOR_PORT', '8093'))
    host = '0.0.0.0'  # Always bind to all interfaces in container
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid RDP_MONITOR_PORT/MONITOR_PORT value: {port_str}", file=sys.stderr)
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
    
    # Import the app directly to ensure sys.path is respected
    try:
        from resource_monitor.main import app
    except ImportError as e:
        print(f"ERROR: Failed to import resource_monitor.main: {e}", file=sys.stderr)
        print(f"ERROR: Python path: {sys.path}", file=sys.stderr)
        print(f"ERROR: App path exists: {os.path.exists(app_path)}", file=sys.stderr)
        if os.path.exists(app_path):
            try:
                contents = os.listdir(app_path)
                print(f"ERROR: App directory contents: {contents}", file=sys.stderr)
            except Exception as list_err:
                print(f"ERROR: Could not list app directory: {list_err}", file=sys.stderr)
        sys.exit(1)
    
    uvicorn.run(app, host=host, port=port)

