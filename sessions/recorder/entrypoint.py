#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session Recorder Service Entrypoint
UTF-8 encoded entrypoint script for distroless container

This script serves as the entrypoint for the session-recorder container,
providing clean startup with environment variable configuration.
No hardcoded values - all configuration from environment variables.
"""

import os
import sys

if __name__ == "__main__":
    # Get configuration from environment variables (from docker-compose)
    # SESSION_RECORDER_HOST is service name, but bind address must be 0.0.0.0
    port_str = os.getenv('SESSION_RECORDER_PORT', '8090')
    host = '0.0.0.0'  # Always bind to all interfaces in container
    
    try:
        port = int(port_str)
    except ValueError:
        print(f"ERROR: Invalid SESSION_RECORDER_PORT value: {port_str}", file=sys.stderr)
        sys.exit(1)
    
    # Import uvicorn and start the application
    import uvicorn
    uvicorn.run('sessions.recorder.main:app', host=host, port=port)

