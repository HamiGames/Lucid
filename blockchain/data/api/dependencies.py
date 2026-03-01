"""
Data Chain API Dependencies
Dependency injection functions for FastAPI routes
"""

from __future__ import annotations

import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from ..service import DataChainService

logger = logging.getLogger(__name__)

# Global service instance
_data_chain_service: DataChainService | None = None


async def get_data_chain_service() -> DataChainService:
    """Dependency to get data chain service instance."""
    global _data_chain_service
    
    if _data_chain_service is None:
        mongo_url = os.getenv("MONGO_URL") or os.getenv("MONGODB_URL") or os.getenv("MONGODB_URI")
        if not mongo_url:
            raise RuntimeError("MONGO_URL, MONGODB_URL, or MONGODB_URI environment variable not set")
        
        mongo_client = AsyncIOMotorClient(mongo_url)
        _data_chain_service = DataChainService(mongo_client)
        await _data_chain_service.start()
    
    return _data_chain_service


async def shutdown_data_chain_service():
    """Shutdown the data chain service."""
    global _data_chain_service
    if _data_chain_service:
        await _data_chain_service.stop()
        _data_chain_service = None

