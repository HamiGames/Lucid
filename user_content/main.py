#!/usr/bin/env python3
"""
Lucid User Content Service
Manages user content, profiles, and client interactions.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Distroless-safe path resolution
project_root = os.getenv('LUCID_PROJECT_ROOT', str(Path(__file__).parent.parent))
sys.path.insert(0, project_root)

from user_content.client.user_client import LucidUserClient, get_user_client

logger = logging.getLogger(__name__)


async def main():
    """Main user content service entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting Lucid User Content Service")
    
    try:
        # Initialize user content service
        # This service manages user profiles, content, and client interactions
        
        logger.info("User content service initialized successfully")
        
        # Keep service running
        while True:
            await asyncio.sleep(60)
            
    except Exception as e:
        logger.error(f"User content service error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
