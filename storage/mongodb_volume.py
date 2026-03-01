# Path: storage/mongodb_volume.py

import asyncio
import logging
from typing import Dict, List, Optional
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


class MongoVolumeManager:
    """Manages MongoDB volume and sharding configuration."""
    
    def __init__(self, connection_string: str):
        try:
            self.client = AsyncIOMotorClient(connection_string)
            self.admin_db = self.client.admin
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
        
    async def setup_sharding(self, database_name: str) -> None:
        """Setup sharding for database collections."""
        try:
            # Enable sharding for database
            await self.admin_db.command("enableSharding", database_name)
            
            # Shard sessions collection
            await self.admin_db.command(
                "shardCollection",
                f"{database_name}.sessions",
                key={"session_id": 1}
            )
            
            # Shard chunks collection  
            await self.admin_db.command(
                "shardCollection", 
                f"{database_name}.chunks",
                key={"session_id": 1, "index": 1}
            )
            
            logger.info(f"Sharding configured for database: {database_name}")
            
        except Exception as e:
            logger.error(f"Failed to setup sharding: {e}")
            raise
            
    async def create_indexes(self, database_name: str) -> None:
        """Create optimized indexes."""
        try:
            db = self.client[database_name]
            
            # Session indexes
            await db.sessions.create_index("session_id", unique=True)
            await db.sessions.create_index("started_at")
            await db.sessions.create_index("participants")
            
            # Chunk indexes
            await db.chunks.create_index([("session_id", 1), ("index", 1)], unique=True)
            await db.chunks.create_index("created_at")
            
            # Peer indexes
            await db.peers.create_index("node_id", unique=True)
            await db.peers.create_index("role")
            
            logger.info("Database indexes created")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            raise
