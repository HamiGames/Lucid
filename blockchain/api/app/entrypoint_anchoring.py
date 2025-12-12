#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Anchoring Service Entrypoint
UTF-8 encoded entrypoint script for distroless container

This script serves as the entrypoint for the session-anchoring container,
providing clean startup with environment variable configuration.
No hardcoded values - all configuration from environment variables.
"""

import os
import sys

if __name__ == "__main__":
    # Get configuration from environment variables (defaults match Dockerfile ENV)
    port_str = os.getenv('SESSION_ANCHORING_PORT', '8085')
    host = os.getenv('SESSION_ANCHORING_HOST', '0.0.0.0')
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid SESSION_ANCHORING_PORT value: {port_str}", file=sys.stderr)
        sys.exit(1)
    
    # Import uvicorn and start the application
    import uvicorn
    uvicorn.run('api.app.main:app', host=host, port=port)

