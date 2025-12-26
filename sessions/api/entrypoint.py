#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session API Service Entrypoint
UTF-8 encoded entrypoint script for distroless container

This script serves as the entrypoint for the session-api container,
providing clean startup with environment variable configuration.
No hardcoded values - all configuration from environment variables.
"""

import os
import sys

# Ensure site-packages and app directory are in Python path (defensive programming)
site_packages = '/usr/local/lib/python3.11/site-packages'
app_path = '/app'

# Get script directory and remove it from sys.path if present (prevents Python from adding it automatically)
# We want /app in sys.path, not /app/sessions/api
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir in sys.path:
    sys.path.remove(script_dir)

# Add to sys.path if not already present (order matters - app_path first so our modules take precedence)
if app_path not in sys.path:
    sys.path.insert(0, app_path)
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

if __name__ == "__main__":
    # Get configuration from environment variables (from docker-compose)
    # SESSION_API_HOST is service name, but bind address must be 0.0.0.0
    port_str = os.getenv('SESSION_API_PORT', '8113')
    host = '0.0.0.0'  # Always bind to all interfaces in container
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid SESSION_API_PORT value: {port_str}", file=sys.stderr)
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
        # Verify sessions is a package before importing
        sessions_path = os.path.join(app_path, 'sessions')
        init_file = os.path.join(sessions_path, '__init__.py')
        if not os.path.exists(init_file):
            print(f"ERROR: sessions/__init__.py not found at {init_file}", file=sys.stderr)
            print(f"ERROR: sessions directory exists: {os.path.exists(sessions_path)}", file=sys.stderr)
            if os.path.exists(sessions_path):
                try:
                    contents = os.listdir(sessions_path)
                    print(f"ERROR: sessions directory contents: {contents}", file=sys.stderr)
                except Exception as list_err:
                    print(f"ERROR: Could not list sessions directory: {list_err}", file=sys.stderr)
            sys.exit(1)
        
        from sessions.api.main import app
        uvicorn.run(app, host=host, port=port)
    except ImportError as e:
        print(f"ERROR: Failed to import sessions.api.main: {e}", file=sys.stderr)
        print(f"ERROR: Python path: {sys.path}", file=sys.stderr)
        print(f"ERROR: App path: {app_path}", file=sys.stderr)
        if os.path.exists(app_path):
            try:
                contents = os.listdir(app_path)
                print(f"ERROR: App directory contents: {contents}", file=sys.stderr)
            except Exception as list_err:
                print(f"ERROR: Could not list app directory: {list_err}", file=sys.stderr)
        sys.exit(1)

