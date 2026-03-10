#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI Tor Manager Entrypoint
Entry point for the GUI Tor Manager service
Reads environment variables and starts uvicorn server
"""

import os
import sys
from pathlib import Path

# Setup Python path
sys.path.insert(0, "/usr/local/lib/python3.11/site-packages")
sys.path.insert(0, "/app")

try:
    import uvicorn
    from gui_tor_manager.main import app
    
    # Read environment variables
    port = int(os.getenv("PORT", "8097"))
    host = os.getenv("HOST", "0.0.0.0")
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    
    # Validate port
    if not 1 <= port <= 65535:
        raise ValueError(f"Invalid PORT: {port}. Must be between 1 and 65535")
    
    # Start uvicorn server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=True,
        server_header=False,
    )
    
except ImportError as e:
    print(f"ERROR: Failed to import required module: {e}", file=sys.stderr)
    sys.exit(1)
except ValueError as e:
    print(f"ERROR: Configuration error: {e}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Unexpected error: {e}", file=sys.stderr)
    sys.exit(1)
