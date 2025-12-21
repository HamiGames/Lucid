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

if __name__ == "__main__":
    # Get configuration from environment variables (from docker-compose)
    # SESSION_API_HOST is service name, but bind address must be 0.0.0.0
    port_str = os.getenv('SESSION_API_PORT', '8087')
    host = '0.0.0.0'  # Always bind to all interfaces in container
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid SESSION_API_PORT value: {port_str}", file=sys.stderr)
        sys.exit(1)
    
    # Import uvicorn and start the application
    import uvicorn
    uvicorn.run('sessions.api.main:app', host=host, port=port)

