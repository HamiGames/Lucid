#!/usr/bin/env python3
"""
Lucid Node Management - Database Adapter
Database interface for node management service
"""

import asyncio
import logging
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)

# Database Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "lucid_node_management")
REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379")

class DatabaseAdapter:
    """
    Database adapter for node management service
    
    Handles:
    - MongoDB operations for persistent data
    - Redis operations for caching
    - Connection management
    - Error handling and retries
    """
    
    def __init__(self, mongodb_uri: str = MONGODB_URI, redis_uri: str = REDIS_URI):
        self.mongodb_uri = mongodb_uri
        self.redis_uri = redis_uri
        self.mongodb_client = None
        self.redis_client = None
        self.database = None
        self.connected = False
        
        logger.info("Database adapter initialized")
    
    async def connect(self) -> bool:
        """
        Connect to databases
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Connect to MongoDB
            try:
                import motor.motor_asyncio
                self.mongodb_client = motor.motor_asyncio.AsyncIOMotorClient(self.mongodb_uri)
                self.database = self.mongodb_client[MONGODB_DATABASE]
                
                # Test connection
                await self.mongodb_client.admin.command('ping')
                logger.info("Connected to MongoDB")
            except ImportError:
                logger.warning("Motor not available - MongoDB operations disabled")
                self.mongodb_client = None
            except Exception as e:
                logger.warning(f"Failed to connect to MongoDB: {e}")
                self.mongodb_client = None
            
            # Connect to Redis
            try:
                import redis.asyncio as redis
                self.redis_client = redis.from_url(self.redis_uri)
                
                # Test connection
                await self.redis_client.ping()
                logger.info("Connected to Redis")
            except ImportError:
                logger.warning("Redis not available - Redis operations disabled")
                self.redis_client = None
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self.redis_client = None
            
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to databases: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from databases"""
        try:
            if self.mongodb_client:
                self.mongodb_client.close()
                logger.info("Disconnected from MongoDB")
            
            if self.redis_client:
                await self.redis_client.close()
                logger.info("Disconnected from Redis")
            
            self.connected = False
            
        except Exception as e:
            logger.error(f"Error disconnecting from databases: {e}")
    
    async def store_node(self, node_data: Dict[str, Any]) -> bool:
        """
        Store node data
        
        Args:
            node_data: Node data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.mongodb_client:
                logger.warning("MongoDB not available - storing node data in memory")
                return True
            
            collection = self.database.nodes
            result = await collection.insert_one(node_data)
            
            if result.inserted_id:
                logger.info(f"Node stored with ID: {result.inserted_id}")
                return True
            else:
                logger.error("Failed to store node")
                return False
                
        except Exception as e:
            logger.error(f"Error storing node: {e}")
            return False
    
    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get node data
        
        Args:
            node_id: Node identifier
            
        Returns:
            Node data dictionary if found, None otherwise
        """
        try:
            if not self.mongodb_client:
                logger.warning("MongoDB not available - returning None for node")
                return None
            
            collection = self.database.nodes
            node = await collection.find_one({"node_id": node_id})
            
            if node:
                # Convert ObjectId to string
                node["_id"] = str(node["_id"])
                return node
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting node {node_id}: {e}")
            return None
    
    async def update_node(self, node_id: str, update_data: Dict[str, Any]) -> bool:
        """
        Update node data
        
        Args:
            node_id: Node identifier
            update_data: Update data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.mongodb_client:
                logger.warning("MongoDB not available - update not persisted")
                return True
            
            collection = self.database.nodes
            result = await collection.update_one(
                {"node_id": node_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"Node {node_id} updated")
                return True
            else:
                logger.warning(f"Node {node_id} not found for update")
                return False
                
        except Exception as e:
            logger.error(f"Error updating node {node_id}: {e}")
            return False
    
    async def list_nodes(self, filter_dict: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        List nodes with optional filtering
        
        Args:
            filter_dict: Optional filter dictionary
            
        Returns:
            List of node data dictionaries
        """
        try:
            if not self.mongodb_client:
                logger.warning("MongoDB not available - returning empty list")
                return []
            
            collection = self.database.nodes
            cursor = collection.find(filter_dict or {})
            nodes = await cursor.to_list(length=None)
            
            # Convert ObjectIds to strings
            for node in nodes:
                node["_id"] = str(node["_id"])
            
            return nodes
            
        except Exception as e:
            logger.error(f"Error listing nodes: {e}")
            return []
    
    async def store_pool(self, pool_data: Dict[str, Any]) -> bool:
        """
        Store pool data
        
        Args:
            pool_data: Pool data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.mongodb_client:
                logger.warning("MongoDB not available - storing pool data in memory")
                return True
            
            collection = self.database.pools
            result = await collection.insert_one(pool_data)
            
            if result.inserted_id:
                logger.info(f"Pool stored with ID: {result.inserted_id}")
                return True
            else:
                logger.error("Failed to store pool")
                return False
                
        except Exception as e:
            logger.error(f"Error storing pool: {e}")
            return False
    
    async def get_pool(self, pool_id: str) -> Optional[Dict[str, Any]]:
        """
        Get pool data
        
        Args:
            pool_id: Pool identifier
            
        Returns:
            Pool data dictionary if found, None otherwise
        """
        try:
            if not self.mongodb_client:
                logger.warning("MongoDB not available - returning None for pool")
                return None
            
            collection = self.database.pools
            pool = await collection.find_one({"pool_id": pool_id})
            
            if pool:
                pool["_id"] = str(pool["_id"])
                return pool
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting pool {pool_id}: {e}")
            return None
    
    async def store_payout(self, payout_data: Dict[str, Any]) -> bool:
        """
        Store payout data
        
        Args:
            payout_data: Payout data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.mongodb_client:
                logger.warning("MongoDB not available - storing payout data in memory")
                return True
            
            collection = self.database.payouts
            result = await collection.insert_one(payout_data)
            
            if result.inserted_id:
                logger.info(f"Payout stored with ID: {result.inserted_id}")
                return True
            else:
                logger.error("Failed to store payout")
                return False
                
        except Exception as e:
            logger.error(f"Error storing payout: {e}")
            return False
    
    async def get_payout(self, payout_id: str) -> Optional[Dict[str, Any]]:
        """
        Get payout data
        
        Args:
            payout_id: Payout identifier
            
        Returns:
            Payout data dictionary if found, None otherwise
        """
        try:
            if not self.mongodb_client:
                logger.warning("MongoDB not available - returning None for payout")
                return None
            
            collection = self.database.payouts
            payout = await collection.find_one({"payout_id": payout_id})
            
            if payout:
                payout["_id"] = str(payout["_id"])
                return payout
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting payout {payout_id}: {e}")
            return None
    
    async def cache_set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set cache value
        
        Args:
            key: Cache key
            value: Cache value
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                logger.warning("Redis not available - cache not set")
                return True
            
            # Serialize value
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            await self.redis_client.set(key, value, ex=ttl)
            logger.debug(f"Cache set: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache {key}: {e}")
            return False
    
    async def cache_get(self, key: str) -> Optional[Any]:
        """
        Get cache value
        
        Args:
            key: Cache key
            
        Returns:
            Cache value if found, None otherwise
        """
        try:
            if not self.redis_client:
                logger.warning("Redis not available - cache not available")
                return None
            
            value = await self.redis_client.get(key)
            if value:
                # Try to deserialize JSON
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value.decode() if isinstance(value, bytes) else value
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting cache {key}: {e}")
            return None
    
    async def cache_delete(self, key: str) -> bool:
        """
        Delete cache value
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.redis_client:
                logger.warning("Redis not available - cache not deleted")
                return True
            
            result = await self.redis_client.delete(key)
            logger.debug(f"Cache deleted: {key}")
            return result > 0
            
        except Exception as e:
            logger.error(f"Error deleting cache {key}: {e}")
            return False

# Global database adapter instance
_db_adapter: Optional[DatabaseAdapter] = None

async def get_database_adapter() -> DatabaseAdapter:
    """
    Get global database adapter instance
    
    Returns:
        DatabaseAdapter instance
    """
    global _db_adapter
    
    if _db_adapter is None:
        _db_adapter = DatabaseAdapter()
        await _db_adapter.connect()
    
    return _db_adapter

async def close_database_adapter():
    """Close global database adapter"""
    global _db_adapter
    
    if _db_adapter:
        await _db_adapter.disconnect()
        _db_adapter = None