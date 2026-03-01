#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRON Wallet Manager Service Entrypoint
UTF-8 encoded entrypoint script for distroless container

This script serves as the entrypoint for the tron-wallet-manager container,
providing clean startup with environment variable configuration.
No hardcoded values - all configuration from environment variables.
"""

import os
import sys

# Ensure site-packages is in Python path (per master-docker-design.md)
site_packages = '/usr/local/lib/python3.11/site-packages'
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

# Add app directory to path
app_dir = '/app'
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

if __name__ == "__main__":
    # Get configuration from environment variables (from docker-compose)
    port_str = os.getenv('WALLET_MANAGER_PORT', os.getenv('SERVICE_PORT', '8093'))
    host = '0.0.0.0'  # Always bind to all interfaces in container
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid WALLET_MANAGER_PORT value: {port_str}", file=sys.stderr)
        sys.exit(1)
    
    # Import uvicorn and start the application
    try:
        import uvicorn
    except ImportError as e:
        print(f"ERROR: Failed to import uvicorn: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Import the main app
    try:
        # Add payment-systems directory to path
        from pathlib import Path
        payment_systems_dir = Path(__file__).parent.parent
        if str(payment_systems_dir) not in sys.path:
            sys.path.insert(0, str(payment_systems_dir))
        
        from tron.wallet_manager_main import app
    except ImportError as e:
        print(f"ERROR: Failed to import wallet_manager_main: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Start the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.getenv('LOG_LEVEL', 'INFO').lower()
    )

