#!/usr/bin/env python3
"""
Lucid Storage Service
Manages distributed storage and data persistence.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Distroless-safe path resolution
project_root = os.getenv('LUCID_PROJECT_ROOT', str(Path(__file__).parent.parent))
sys.path.insert(0, project_root)

from storage.mongodb_volume import MongoVolumeManager

logger = logging.getLogger(__name__)


async def main():
    """Main storage service entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting Lucid Storage Service")
    
    try:
        # Initialize storage manager
        connection_string = "mongodb://localhost:27017"
        storage_manager = MongoVolumeManager(connection_string)
        
        # Setup storage
        await storage_manager.setup_sharding("lucid")
        await storage_manager.create_indexes("lucid")
        
        logger.info("Storage service initialized successfully")
        
        # Keep service running
        while True:
            await asyncio.sleep(60)
            
    except Exception as e:
        logger.error(f"Storage service error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
