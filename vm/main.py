#!/usr/bin/env python3
"""
Lucid VM Management Service
Manages lightweight VM instances using Docker containers.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Distroless-safe path resolution
project_root = os.getenv('LUCID_PROJECT_ROOT', str(Path(__file__).parent.parent))
sys.path.insert(0, project_root)

from vm.vm_manager import VMManager

logger = logging.getLogger(__name__)


async def main():
    """Main VM service entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting Lucid VM Management Service")
    
    try:
        # Initialize VM manager with error handling
        try:
            vm_manager = VMManager()
            logger.info("VM management service initialized successfully")
        except Exception as init_error:
            logger.error(f"Failed to initialize VM manager: {init_error}")
            raise
        
        # Keep service running
        while True:
            await asyncio.sleep(60)
            
    except Exception as e:
        logger.error(f"VM service error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
