#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI Hardware Manager Service Entrypoint
UTF-8 encoded entrypoint script for distroless container
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
        
        # Get configuration from environment
        port_str = os.getenv('GUI_HARDWARE_MANAGER_PORT', '8099')
        host = '0.0.0.0'  # Always bind to all interfaces
        
        try:
            port = int(port_str)
        except ValueError:
            logger.error(f"ERROR: Invalid GUI_HARDWARE_MANAGER_PORT value: {port_str}")
            sys.exit(1)
        
        logger.info(f"Starting GUI Hardware Manager on {host}:{port}")
        
        # Run the application
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            use_colors=False
        )
        
    except ImportError as e:
        logger.error(f"ERROR: Failed to import: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"ERROR: Application failed: {e}")
        sys.exit(1)
