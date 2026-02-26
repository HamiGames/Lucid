#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI Hardware Manager Service Entrypoint
UTF-8 encoded entrypoint script for distroless container
Reads configuration from environment variables
"""

import os
import sys
import logging

# Ensure site-packages is in Python path
site_packages = '/usr/local/lib/python3.11/site-packages'
if site_packages not in sys.path:
    sys.path.insert(0, site_packages)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        # Import main application after path setup
        from gui_hardware_manager.main import app
        import uvicorn
        
        # Get configuration from environment (aligned with docker-compose)
        port_str = os.getenv('PORT', '8099')
        host = os.getenv('HOST', '0.0.0.0')
        log_level = os.getenv('LOG_LEVEL', 'info').lower()
        
        try:
            port = int(port_str)
        except ValueError:
            logger.error(f"ERROR: Invalid PORT value: {port_str}")
            sys.exit(1)
        
        if not 1 <= port <= 65535:
            logger.error(f"ERROR: PORT must be between 1-65535, got: {port}")
            sys.exit(1)
        
        logger.info(f"Starting GUI Hardware Manager on {host}:{port}")
        logger.info(f"Environment: {os.getenv('LUCID_ENV', 'production')}")
        logger.info(f"Platform: {os.getenv('LUCID_PLATFORM', 'arm64')}")
        
        # Run the application
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=log_level,
            access_log=True,
            use_colors=False
        )
        
    except ImportError as e:
        logger.error(f"ERROR: Failed to import: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"ERROR: Application failed: {e}")
        sys.exit(1)
