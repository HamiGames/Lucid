"""
MongoDB Sharding Management Module
LUCID Project - Storage Layer

This module provides comprehensive MongoDB sharding configuration and management
for the Lucid project, supporting horizontal scaling and distributed data storage.

Author: Lucid Development Team
Created: 2025-01-27
Version: 1.0.0
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import json
import hashlib

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import (
    OperationFailure, 
    ConfigurationError, 
    ServerSelectionTimeoutError,
    DuplicateKeyError
)
from pymongo import ASCENDING, DESCENDING

logger = logging.getLogger(__name__)


class ShardStatus(Enum):
    """Shard status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    MIGRATING = "migrating"
    ERROR = "error"


class ShardingStrategy(Enum):
    """Sharding strategy enumeration."""
    RANGE = "range"
    HASH = "hash"
    ZONED = "zoned"


class ShardKeyType(Enum):
    """Shard key type enumeration."""
    SIMPLE = "simple"
    COMPOUND = "compound"
    HASHED = "hashed"


class ShardKey:
    """Represents a shard key configuration."""
    
    def __init__(self, fields: Dict[str, int], strategy: ShardingStrategy = ShardingStrategy.RANGE):
        """
        Initialize shard key.
        
        Args:
            fields: Dictionary of field names and sort orders (1 for ASC, -1 for DESC)
            strategy: Sharding strategy to use
        """
        self.fields = fields
        self.strategy = strategy
        self.key_type = self._determine_key_type()
        
    def _determine_key_type(self) -> ShardKeyType:
        """Determine the type of shard key."""
        if len(self.fields) == 1:
            return ShardKeyType.SIMPLE
        else:
            return ShardKeyType.COMPOUND
    
    def to_mongo_key(self) -> Dict[str, int]:
        """Convert to MongoDB shard key format."""
        if self.strategy == ShardingStrategy.HASH:
            # For hashed sharding, use a single field with hash value
            if len(self.fields) == 1:
                field_name = list(self.fields.keys())[0]
                return {field_name: "hashed"}
            else:
                raise ValueError("Hashed sharding requires exactly one field")
        
        return self.fields
    
    def __str__(self) -> str:
        return f"ShardKey({self.fields}, strategy={self.strategy.value})"


class ShardInfo:
    """Information about a MongoDB shard."""
    
    def __init__(self, name: str, host: str, status: ShardStatus = ShardStatus.ACTIVE):
        self.name = name
        self.host = host
        self.status = status
        self.chunks_count = 0
        self.data_size_mb = 0
        self.last_updated = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "host": self.host,
            "status": self.status.value,
            "chunks_count": self.chunks_count,
            "data_size_mb": self.data_size_mb,
            "last_updated": self.last_updated.isoformat()
        }


class CollectionShardConfig:
    """Configuration for sharding a specific collection."""
    
    def __init__(
        self,
        collection_name: str,
        shard_key: ShardKey,
        unique: bool = False,
        presplit_chunks: Optional[List[Dict[str, Any]]] = None
    ):
        self.collection_name = collection_name
        self.shard_key = shard_key
        self.unique = unique
        self.presplit_chunks = presplit_chunks or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "collection_name": self.collection_name,
            "shard_key": {
                "fields": self.shard_key.fields,
                "strategy": self.shard_key.strategy.value
            },
            "unique": self.unique,
            "presplit_chunks": self.presplit_chunks
        }


class MongoShardingManager:
    """
    Comprehensive MongoDB sharding management for the Lucid project.
    
    This class handles:
    - Sharding configuration and setup
    - Shard management and monitoring
    - Collection sharding strategies
    - Shard balancing and optimization
    - Performance monitoring and metrics
    """
    
    def __init__(self, connection_string: str, database_name: str = "lucid"):
        """
        Initialize MongoDB sharding manager.
        
        Args:
            connection_string: MongoDB connection string
            database_name: Name of the database to manage
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.admin_db: Optional[AsyncIOMotorDatabase] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        
        # Sharding configurations for Lucid collections
        self.collection_configs = self._initialize_collection_configs()
        
    def _initialize_collection_configs(self) -> Dict[str, CollectionShardConfig]:
        """Initialize sharding configurations for Lucid collections."""
        configs = {}
        
        # Sessions collection - shard on session_id for even distribution
        configs["sessions"] = CollectionShardConfig(
            collection_name="sessions",
            shard_key=ShardKey({"session_id": 1}, ShardingStrategy.HASH),
            unique=True
        )
        
        # Chunks collection - shard on session_id + sequence_number for co-location
        configs["chunks"] = CollectionShardConfig(
            collection_name="chunks",
            shard_key=ShardKey({
                "session_id": 1,
                "sequence_number": 1
            }, ShardingStrategy.RANGE),
            unique=True
        )
        
        # Encrypted chunks - same strategy as chunks
        configs["encrypted_chunks"] = CollectionShardConfig(
            collection_name="encrypted_chunks",
            shard_key=ShardKey({
                "session_id": 1,
                "sequence_number": 1
            }, ShardingStrategy.RANGE),
            unique=True
        )
        
        # Work proofs - shard on node_id + slot for consensus distribution
        configs["work_proofs"] = CollectionShardConfig(
            collection_name="work_proofs",
            shard_key=ShardKey({
                "node_id": 1,
                "slot": 1
            }, ShardingStrategy.RANGE)
        )
        
        # Task proofs - shard on node_id for node-based distribution
        configs["task_proofs"] = CollectionShardConfig(
            collection_name="task_proofs",
            shard_key=ShardKey({"node_id": 1}, ShardingStrategy.HASH)
        )
        
        # Work tally - shard on slot for time-based distribution
        configs["work_tally"] = CollectionShardConfig(
            collection_name="work_tally",
            shard_key=ShardKey({"slot": 1}, ShardingStrategy.HASH)
        )
        
        # Leader schedule - shard on slot for time-based distribution
        configs["leader_schedule"] = CollectionShardConfig(
            collection_name="leader_schedule",
            shard_key=ShardKey({"slot": 1}, ShardingStrategy.RANGE)
        )
        
        # Payouts - shard on node_id for node-based distribution
        configs["payouts"] = CollectionShardConfig(
            collection_name="payouts",
            shard_key=ShardKey({"node_id": 1}, ShardingStrategy.HASH)
        )
        
        # Authentication - shard on tron_address for user-based distribution
        configs["authentication"] = CollectionShardConfig(
            collection_name="authentication",
            shard_key=ShardKey({"tron_address": 1}, ShardingStrategy.HASH),
            unique=True
        )
        
        # Encryption keys - shard on session_id for session-based distribution
        configs["encryption_keys"] = CollectionShardConfig(
            collection_name="encryption_keys",
            shard_key=ShardKey({"session_id": 1}, ShardingStrategy.HASH)
        )
        
        return configs
    
    async def connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            self.client = AsyncIOMotorClient(self.connection_string)
            self.admin_db = self.client.admin
            self.database = self.client[self.database_name]
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info(f"Connected to MongoDB: {self.database_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def enable_sharding(self) -> bool:
        """
        Enable sharding for the database.
        
        Returns:
            bool: True if sharding was enabled successfully
        """
        try:
            result = await self.admin_db.command("enableSharding", self.database_name)
            logger.info(f"Sharding enabled for database: {self.database_name}")
            return result.get("ok") == 1
            
        except OperationFailure as e:
            if "already enabled" in str(e).lower():
                logger.info(f"Sharding already enabled for database: {self.database_name}")
                return True
            else:
                logger.error(f"Failed to enable sharding: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error enabling sharding: {e}")
            raise
    
    async def add_shard(self, shard_name: str, shard_host: str) -> bool:
        """
        Add a new shard to the cluster.
        
        Args:
            shard_name: Name of the shard
            shard_host: Host connection string for the shard
            
        Returns:
            bool: True if shard was added successfully
        """
        try:
            result = await self.admin_db.command("addShard", shard_host, name=shard_name)
            logger.info(f"Added shard '{shard_name}' at {shard_host}")
            return result.get("ok") == 1
            
        except OperationFailure as e:
            if "already exists" in str(e).lower():
                logger.info(f"Shard '{shard_name}' already exists")
                return True
            else:
                logger.error(f"Failed to add shard '{shard_name}': {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error adding shard: {e}")
            raise
    
    async def remove_shard(self, shard_name: str, force: bool = False) -> bool:
        """
        Remove a shard from the cluster.
        
        Args:
            shard_name: Name of the shard to remove
            force: Force removal even if data migration is required
            
        Returns:
            bool: True if shard was removed successfully
        """
        try:
            if force:
                # Force removal - data will be lost
                result = await self.admin_db.command("removeShard", shard_name, force=True)
            else:
                # Normal removal with data migration
                result = await self.admin_db.command("removeShard", shard_name)
            
            logger.info(f"Removed shard '{shard_name}' (force={force})")
            return result.get("ok") == 1
            
        except Exception as e:
            logger.error(f"Failed to remove shard '{shard_name}': {e}")
            raise
    
    async def get_shard_status(self) -> Dict[str, ShardInfo]:
        """
        Get status information for all shards.
        
        Returns:
            Dict mapping shard names to ShardInfo objects
        """
        try:
            shard_status = {}
            
            # Get shard list
            shard_list = await self.admin_db.command("listShards")
            
            for shard in shard_list.get("shards", []):
                shard_name = shard["_id"]
                shard_host = shard["host"]
                
                # Get shard statistics
                stats = await self.admin_db.command("shardConnPoolStats")
                
                shard_info = ShardInfo(
                    name=shard_name,
                    host=shard_host,
                    status=ShardStatus.ACTIVE
                )
                
                # Get chunk count and data size
                try:
                    chunk_stats = await self.admin_db.command(
                        "dataSize",
                        f"{self.database_name}",
                        keyPattern={"shard": shard_name}
                    )
                    shard_info.chunks_count = chunk_stats.get("numObjects", 0)
                    shard_info.data_size_mb = chunk_stats.get("size", 0) / (1024 * 1024)
                except:
                    pass  # Stats might not be available
                
                shard_status[shard_name] = shard_info
            
            return shard_status
            
        except Exception as e:
            logger.error(f"Failed to get shard status: {e}")
            raise
    
    async def shard_collection(self, collection_name: str, config: Optional[CollectionShardConfig] = None) -> bool:
        """
        Shard a collection using the specified configuration.
        
        Args:
            collection_name: Name of the collection to shard
            config: Sharding configuration (uses default if not provided)
            
        Returns:
            bool: True if collection was sharded successfully
        """
        try:
            if config is None:
                config = self.collection_configs.get(collection_name)
                if config is None:
                    raise ValueError(f"No sharding configuration found for collection: {collection_name}")
            
            # Get the shard key in MongoDB format
            shard_key = config.shard_key.to_mongo_key()
            
            # Shard the collection
            result = await self.admin_db.command(
                "shardCollection",
                f"{self.database_name}.{collection_name}",
                key=shard_key,
                unique=config.unique
            )
            
            logger.info(f"Sharded collection '{collection_name}' with key: {shard_key}")
            
            # Apply presplit chunks if configured
            if config.presplit_chunks:
                await self._apply_presplit_chunks(collection_name, config.presplit_chunks)
            
            return result.get("ok") == 1
            
        except OperationFailure as e:
            if "already sharded" in str(e).lower():
                logger.info(f"Collection '{collection_name}' is already sharded")
                return True
            else:
                logger.error(f"Failed to shard collection '{collection_name}': {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error sharding collection: {e}")
            raise
    
    async def _apply_presplit_chunks(self, collection_name: str, presplit_chunks: List[Dict[str, Any]]) -> None:
        """Apply presplit chunks to a collection."""
        try:
            for chunk in presplit_chunks:
                await self.admin_db.command(
                    "split",
                    f"{self.database_name}.{collection_name}",
                    middle=chunk["middle"]
                )
                logger.debug(f"Applied presplit chunk for {collection_name}: {chunk['middle']}")
        except Exception as e:
            logger.warning(f"Failed to apply presplit chunks for {collection_name}: {e}")
    
    async def setup_all_collections(self) -> Dict[str, bool]:
        """
        Setup sharding for all configured collections.
        
        Returns:
            Dict mapping collection names to success status
        """
        results = {}
        
        # First, enable sharding for the database
        await self.enable_sharding()
        
        # Then shard each collection
        for collection_name, config in self.collection_configs.items():
            try:
                success = await self.shard_collection(collection_name, config)
                results[collection_name] = success
                logger.info(f"Sharding setup for '{collection_name}': {'Success' if success else 'Failed'}")
            except Exception as e:
                logger.error(f"Failed to setup sharding for '{collection_name}': {e}")
                results[collection_name] = False
        
        return results
    
    async def get_collection_shard_status(self, collection_name: str) -> Dict[str, Any]:
        """
        Get sharding status for a specific collection.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            Dict containing sharding status information
        """
        try:
            # Get collection stats
            stats = await self.database.command("collStats", collection_name)
            
            # Get shard distribution
            shard_dist = await self.admin_db.command(
                "dataSize",
                f"{self.database_name}.{collection_name}"
            )
            
            # Get chunk information
            chunks_info = await self.admin_db.command(
                "listCollections",
                filter={"name": collection_name}
            )
            
            return {
                "collection_name": collection_name,
                "sharded": stats.get("sharded", False),
                "shard_key": stats.get("shardKey"),
                "chunks_count": stats.get("nchunks", 0),
                "data_size_mb": stats.get("size", 0) / (1024 * 1024),
                "document_count": stats.get("count", 0),
                "shard_distribution": shard_dist,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get shard status for collection '{collection_name}': {e}")
            raise
    
    async def balance_shards(self) -> bool:
        """
        Trigger shard balancing to redistribute chunks.
        
        Returns:
            bool: True if balancing was triggered successfully
        """
        try:
            result = await self.admin_db.command("balancerStart")
            logger.info("Shard balancing started")
            return result.get("ok") == 1
            
        except Exception as e:
            logger.error(f"Failed to start shard balancing: {e}")
            raise
    
    async def get_balancer_status(self) -> Dict[str, Any]:
        """Get the current status of the shard balancer."""
        try:
            result = await self.admin_db.command("balancerStatus")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get balancer status: {e}")
            raise
    
    async def optimize_shard_keys(self) -> Dict[str, Any]:
        """
        Analyze and suggest optimizations for shard keys.
        
        Returns:
            Dict containing optimization suggestions
        """
        try:
            optimizations = {}
            
            for collection_name, config in self.collection_configs.items():
                # Get collection statistics
                stats = await self.get_collection_shard_status(collection_name)
                
                suggestions = []
                
                # Check for hotspots (too many chunks on one shard)
                if stats["chunks_count"] > 0:
                    chunk_ratio = stats["chunks_count"] / len(await self.get_shard_status())
                    if chunk_ratio > 10:  # More than 10 chunks per shard on average
                        suggestions.append("Consider using hashed sharding to improve distribution")
                
                # Check for query patterns
                if config.shard_key.strategy == ShardingStrategy.RANGE:
                    suggestions.append("Range sharding detected - monitor for hotspots")
                
                # Check for compound keys
                if config.shard_key.key_type == ShardKeyType.COMPOUND:
                    suggestions.append("Compound shard key - ensure proper field ordering")
                
                optimizations[collection_name] = {
                    "current_config": config.to_dict(),
                    "statistics": stats,
                    "suggestions": suggestions
                }
            
            return optimizations
            
        except Exception as e:
            logger.error(f"Failed to analyze shard key optimizations: {e}")
            raise
    
    async def migrate_chunks(self, collection_name: str, from_shard: str, to_shard: str, 
                           chunk_ranges: List[Dict[str, Any]]) -> bool:
        """
        Migrate chunks between shards.
        
        Args:
            collection_name: Name of the collection
            from_shard: Source shard name
            to_shard: Destination shard name
            chunk_ranges: List of chunk ranges to migrate
            
        Returns:
            bool: True if migration was successful
        """
        try:
            for chunk_range in chunk_ranges:
                await self.admin_db.command(
                    "moveChunk",
                    f"{self.database_name}.{collection_name}",
                    find=chunk_range["find"],
                    to=to_shard
                )
                logger.info(f"Migrated chunk from {from_shard} to {to_shard}: {chunk_range['find']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to migrate chunks: {e}")
            raise
    
    async def get_sharding_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive sharding metrics and statistics.
        
        Returns:
            Dict containing sharding metrics
        """
        try:
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "database_name": self.database_name,
                "shards": {},
                "collections": {},
                "balancer": {},
                "overall_stats": {}
            }
            
            # Get shard information
            shard_status = await self.get_shard_status()
            for shard_name, shard_info in shard_status.items():
                metrics["shards"][shard_name] = shard_info.to_dict()
            
            # Get collection information
            for collection_name in self.collection_configs.keys():
                metrics["collections"][collection_name] = await self.get_collection_shard_status(collection_name)
            
            # Get balancer status
            metrics["balancer"] = await self.get_balancer_status()
            
            # Calculate overall statistics
            total_chunks = sum(
                metrics["collections"][col]["chunks_count"] 
                for col in metrics["collections"]
            )
            total_data_mb = sum(
                metrics["collections"][col]["data_size_mb"] 
                for col in metrics["collections"]
            )
            
            metrics["overall_stats"] = {
                "total_shards": len(metrics["shards"]),
                "total_collections": len(metrics["collections"]),
                "total_chunks": total_chunks,
                "total_data_mb": total_data_mb,
                "avg_chunks_per_shard": total_chunks / len(metrics["shards"]) if metrics["shards"] else 0,
                "avg_data_per_shard_mb": total_data_mb / len(metrics["shards"]) if metrics["shards"] else 0
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get sharding metrics: {e}")
            raise
    
    async def export_sharding_config(self, file_path: str) -> None:
        """
        Export current sharding configuration to a file.
        
        Args:
            file_path: Path to save the configuration file
        """
        try:
            config = {
                "database_name": self.database_name,
                "connection_string": self.connection_string,
                "collection_configs": {
                    name: config.to_dict() 
                    for name, config in self.collection_configs.items()
                },
                "exported_at": datetime.utcnow().isoformat()
            }
            
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Sharding configuration exported to: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to export sharding configuration: {e}")
            raise
    
    async def import_sharding_config(self, file_path: str) -> None:
        """
        Import sharding configuration from a file.
        
        Args:
            file_path: Path to the configuration file
        """
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
            
            # Update collection configurations
            self.collection_configs.clear()
            
            for name, config_dict in config["collection_configs"].items():
                shard_key = ShardKey(
                    fields=config_dict["shard_key"]["fields"],
                    strategy=ShardingStrategy(config_dict["shard_key"]["strategy"])
                )
                
                collection_config = CollectionShardConfig(
                    collection_name=name,
                    shard_key=shard_key,
                    unique=config_dict["unique"],
                    presplit_chunks=config_dict["presplit_chunks"]
                )
                
                self.collection_configs[name] = collection_config
            
            logger.info(f"Sharding configuration imported from: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to import sharding configuration: {e}")
            raise


# Utility functions for sharding operations

async def create_sharding_manager(
    connection_string: str,
    database_name: str = "lucid"
) -> MongoShardingManager:
    """
    Create and initialize a MongoDB sharding manager.
    
    Args:
        connection_string: MongoDB connection string
        database_name: Name of the database to manage
        
    Returns:
        Initialized MongoShardingManager instance
    """
    manager = MongoShardingManager(connection_string, database_name)
    await manager.connect()
    return manager


async def setup_lucid_sharding(connection_string: str) -> Dict[str, bool]:
    """
    Setup sharding for the entire Lucid project.
    
    Args:
        connection_string: MongoDB connection string
        
    Returns:
        Dict mapping collection names to setup success status
    """
    manager = await create_sharding_manager(connection_string)
    
    try:
        results = await manager.setup_all_collections()
        logger.info("Lucid sharding setup completed")
        return results
    finally:
        await manager.disconnect()


# Example usage and testing functions

async def example_usage():
    """Example usage of the MongoDB sharding manager."""
    
    # Connection string for MongoDB
    connection_string = "mongodb://localhost:27017"
    
    # Create sharding manager
    manager = await create_sharding_manager(connection_string, "lucid")
    
    try:
        # Enable sharding
        await manager.enable_sharding()
        
        # Add shards (example)
        # await manager.add_shard("shard1", "localhost:27018")
        # await manager.add_shard("shard2", "localhost:27019")
        
        # Setup all collections
        results = await manager.setup_all_collections()
        print("Setup results:", results)
        
        # Get sharding metrics
        metrics = await manager.get_sharding_metrics()
        print("Sharding metrics:", json.dumps(metrics, indent=2))
        
        # Get optimization suggestions
        optimizations = await manager.optimize_shard_keys()
        print("Optimization suggestions:", json.dumps(optimizations, indent=2))
        
    finally:
        await manager.disconnect()


if __name__ == "__main__":
    # Run example usage
    asyncio.run(example_usage())
