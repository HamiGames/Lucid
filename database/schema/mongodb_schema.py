#!/usr/bin/env python3
"""
LUCID MongoDB Database Schema - SPEC-1B Implementation
Database schema initialization and validation for Lucid system
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MongoDBManager:
    """
    LUCID MongoDB Database Manager
    
    Manages MongoDB collections and schemas for:
    1. User sessions and authentication
    2. Blockchain data and consensus
    3. RDP session recordings
    4. Node management and PoOT data
    5. Audit logs and system events
    """
    
    def __init__(self, mongodb_uri: str):
        self.mongodb_uri = mongodb_uri
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.collections = {}
        
    async def initialize(self) -> bool:
        """
        Initialize MongoDB connection and create collections
        
        Returns:
            success: True if initialization successful
        """
        try:
            logger.info("Initializing MongoDB database")
            
            # Connect to MongoDB
            self.client = AsyncIOMotorClient(self.mongodb_uri)
            self.database = self.client.get_database()
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("MongoDB connection established")
            
            # Create collections and indexes
            await self._create_collections()
            await self._create_indexes()
            
            logger.info("MongoDB database initialized successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB: {e}")
            return False
    
    async def _create_collections(self):
        """Create all required collections"""
        collections_config = {
            # User and Authentication Collections
            "users": {
                "description": "User accounts and profiles",
                "validation": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["user_id", "username", "email", "created_at", "is_active"],
                        "properties": {
                            "user_id": {"bsonType": "string"},
                            "username": {"bsonType": "string", "minLength": 3, "maxLength": 50},
                            "email": {"bsonType": "string", "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"},
                            "password_hash": {"bsonType": "string"},
                            "role": {"enum": ["USER", "NODE_OPERATOR", "ADMIN", "SUPER_ADMIN"]},
                            "hardware_wallet_address": {"bsonType": "string"},
                            "created_at": {"bsonType": "date"},
                            "last_login": {"bsonType": "date"},
                            "is_active": {"bsonType": "bool"},
                            "permissions": {
                                "bsonType": "array",
                                "items": {"bsonType": "string"}
                            }
                        }
                    }
                }
            },
            
            "user_sessions": {
                "description": "User session management",
                "validation": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["session_id", "user_id", "created_at", "state"],
                        "properties": {
                            "session_id": {"bsonType": "string"},
                            "user_id": {"bsonType": "string"},
                            "state": {"enum": ["initializing", "connecting", "authenticating", "active", "suspending", "terminating"]},
                            "created_at": {"bsonType": "date"},
                            "last_updated": {"bsonType": "date"},
                            "expires_at": {"bsonType": "date"},
                            "rdp_connection": {"bsonType": "object"},
                            "config": {"bsonType": "object"},
                            "metrics": {"bsonType": "object"},
                            "is_active": {"bsonType": "bool"}
                        }
                    }
                }
            },
            
            # Session Data Collections
            "session_chunks": {
                "description": "Session recording chunks",
                "validation": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["chunk_id", "session_id", "sequence_number", "created_at"],
                        "properties": {
                            "chunk_id": {"bsonType": "string"},
                            "session_id": {"bsonType": "string"},
                            "sequence_number": {"bsonType": "int", "minimum": 0},
                            "metadata": {"bsonType": "object"},
                            "data": {"bsonType": "binData"},
                            "hash": {"bsonType": "string"},
                            "created_at": {"bsonType": "date"},
                            "expires_at": {"bsonType": "date"}
                        }
                    }
                }
            },
            
            "merkle_trees": {
                "description": "Merkle tree structures for session integrity",
                "validation": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["tree_id", "session_id", "root_hash", "created_at"],
                        "properties": {
                            "tree_id": {"bsonType": "string"},
                            "session_id": {"bsonType": "string"},
                            "root_hash": {"bsonType": "string"},
                            "tree_height": {"bsonType": "int", "minimum": 0},
                            "leaf_count": {"bsonType": "int", "minimum": 0},
                            "hash_algorithm": {"bsonType": "string"},
                            "tree_structure": {"bsonType": "array"},
                            "created_at": {"bsonType": "date"},
                            "finalized_at": {"bsonType": "date"},
                            "is_finalized": {"bsonType": "bool"}
                        }
                    }
                }
            },
            
            # Blockchain Collections
            "blocks": {
                "description": "Blockchain blocks",
                "validation": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["block_id", "height", "previous_hash", "merkle_root", "timestamp"],
                        "properties": {
                            "block_id": {"bsonType": "string"},
                            "height": {"bsonType": "int", "minimum": 0},
                            "previous_hash": {"bsonType": "string"},
                            "merkle_root": {"bsonType": "string"},
                            "block_hash": {"bsonType": "string"},
                            "timestamp": {"bsonType": "date"},
                            "proposer_node": {"bsonType": "string"},
                            "proofs": {"bsonType": "array"},
                            "size_bytes": {"bsonType": "int", "minimum": 0},
                            "status": {"enum": ["pending", "validated", "rejected", "anchored"]}
                        }
                    }
                }
            },
            
            "poot_proofs": {
                "description": "Proof-of-Observation-Time proofs",
                "validation": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["proof_id", "node_id", "session_id", "timestamp"],
                        "properties": {
                            "proof_id": {"bsonType": "string"},
                            "node_id": {"bsonType": "string"},
                            "session_id": {"bsonType": "string"},
                            "observation_time": {"bsonType": "double", "minimum": 0},
                            "work_credits": {"bsonType": "double", "minimum": 0},
                            "merkle_root": {"bsonType": "string"},
                            "proof_hash": {"bsonType": "string"},
                            "timestamp": {"bsonType": "date"},
                            "signature": {"bsonType": "string"},
                            "is_valid": {"bsonType": "bool"},
                            "block_height": {"bsonType": "int", "minimum": 0}
                        }
                    }
                }
            },
            
            # Node Management Collections
            "nodes": {
                "description": "Node management and status",
                "validation": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["node_id", "node_type", "status", "registered_at"],
                        "properties": {
                            "node_id": {"bsonType": "string"},
                            "node_type": {"enum": ["WORKER", "VALIDATOR", "STORAGE", "GATEWAY"]},
                            "status": {"enum": ["OFFLINE", "ONLINE", "MAINTENANCE", "ERROR"]},
                            "owner_id": {"bsonType": "string"},
                            "ip_address": {"bsonType": "string"},
                            "port": {"bsonType": "int", "minimum": 1, "maximum": 65535},
                            "hardware_specs": {"bsonType": "object"},
                            "performance_metrics": {"bsonType": "object"},
                            "registered_at": {"bsonType": "date"},
                            "last_heartbeat": {"bsonType": "date"},
                            "is_active": {"bsonType": "bool"}
                        }
                    }
                }
            },
            
            "node_pools": {
                "description": "Node pool management",
                "validation": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["pool_id", "name", "created_at"],
                        "properties": {
                            "pool_id": {"bsonType": "string"},
                            "name": {"bsonType": "string"},
                            "description": {"bsonType": "string"},
                            "node_ids": {"bsonType": "array", "items": {"bsonType": "string"}},
                            "min_nodes": {"bsonType": "int", "minimum": 1},
                            "max_nodes": {"bsonType": "int", "minimum": 1},
                            "created_at": {"bsonType": "date"},
                            "is_active": {"bsonType": "bool"}
                        }
                    }
                }
            },
            
            # RDP Services Collections
            "rdp_servers": {
                "description": "RDP server instances",
                "validation": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["server_id", "session_id", "port", "status"],
                        "properties": {
                            "server_id": {"bsonType": "string"},
                            "session_id": {"bsonType": "string"},
                            "port": {"bsonType": "int", "minimum": 1, "maximum": 65535},
                            "status": {"enum": ["stopped", "starting", "running", "stopping", "error"]},
                            "config": {"bsonType": "object"},
                            "process_id": {"bsonType": "int"},
                            "start_time": {"bsonType": "date"},
                            "last_activity": {"bsonType": "date"},
                            "connection_count": {"bsonType": "int", "minimum": 0},
                            "error_message": {"bsonType": "string"}
                        }
                    }
                }
            },
            
            "rdp_connections": {
                "description": "RDP connection tracking",
                "validation": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["connection_id", "server_id", "connected_at"],
                        "properties": {
                            "connection_id": {"bsonType": "string"},
                            "server_id": {"bsonType": "string"},
                            "client_ip": {"bsonType": "string"},
                            "client_port": {"bsonType": "int", "minimum": 1, "maximum": 65535},
                            "connected_at": {"bsonType": "date"},
                            "last_activity": {"bsonType": "date"},
                            "session_type": {"enum": ["user_session", "admin_session", "guest_session"]},
                            "is_active": {"bsonType": "bool"}
                        }
                    }
                }
            },
            
            # Audit and Logging Collections
            "audit_logs": {
                "description": "System audit logs",
                "validation": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["log_id", "event_type", "timestamp"],
                        "properties": {
                            "log_id": {"bsonType": "string"},
                            "event_type": {"bsonType": "string"},
                            "user_id": {"bsonType": "string"},
                            "session_id": {"bsonType": "string"},
                            "action": {"bsonType": "string"},
                            "resource": {"bsonType": "string"},
                            "result": {"enum": ["SUCCESS", "FAILURE", "PENDING"]},
                            "details": {"bsonType": "object"},
                            "ip_address": {"bsonType": "string"},
                            "user_agent": {"bsonType": "string"},
                            "timestamp": {"bsonType": "date"}
                        }
                    }
                }
            },
            
            "system_events": {
                "description": "System events and notifications",
                "validation": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["event_id", "event_type", "timestamp", "severity"],
                        "properties": {
                            "event_id": {"bsonType": "string"},
                            "event_type": {"bsonType": "string"},
                            "severity": {"enum": ["INFO", "WARNING", "ERROR", "CRITICAL"]},
                            "message": {"bsonType": "string"},
                            "component": {"bsonType": "string"},
                            "details": {"bsonType": "object"},
                            "timestamp": {"bsonType": "date"},
                            "resolved": {"bsonType": "bool"},
                            "resolved_at": {"bsonType": "date"}
                        }
                    }
                }
            },
            
            # TRON Payment Collections (Isolated)
            "tron_transactions": {
                "description": "TRON payment transactions",
                "validation": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["tx_id", "from_address", "to_address", "amount", "timestamp"],
                        "properties": {
                            "tx_id": {"bsonType": "string"},
                            "from_address": {"bsonType": "string"},
                            "to_address": {"bsonType": "string"},
                            "amount": {"bsonType": "double", "minimum": 0},
                            "currency": {"enum": ["TRX", "USDT"]},
                            "transaction_type": {"enum": ["PAYOUT", "STAKING", "TRANSFER"]},
                            "status": {"enum": ["PENDING", "CONFIRMED", "FAILED"]},
                            "block_number": {"bsonType": "int"},
                            "timestamp": {"bsonType": "date"},
                            "fee": {"bsonType": "double"},
                            "metadata": {"bsonType": "object"}
                        }
                    }
                }
            },
            
            "tron_wallets": {
                "description": "TRON wallet management",
                "validation": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["wallet_id", "address", "created_at"],
                        "properties": {
                            "wallet_id": {"bsonType": "string"},
                            "address": {"bsonType": "string"},
                            "owner_id": {"bsonType": "string"},
                            "wallet_type": {"enum": ["HOT", "COLD", "HARDWARE"]},
                            "balance_trx": {"bsonType": "double", "minimum": 0},
                            "balance_usdt": {"bsonType": "double", "minimum": 0},
                            "is_active": {"bsonType": "bool"},
                            "created_at": {"bsonType": "date"},
                            "last_updated": {"bsonType": "date"}
                        }
                    }
                }
            }
        }
        
        for collection_name, config in collections_config.items():
            try:
                # Create collection with validation
                collection = self.database.create_collection(
                    collection_name,
                    validator=config["validation"]
                )
                
                self.collections[collection_name] = collection
                logger.info(f"Created collection: {collection_name}")
                
            except Exception as e:
                logger.warning(f"Collection {collection_name} might already exist: {e}")
                self.collections[collection_name] = self.database[collection_name]
    
    async def _create_indexes(self):
        """Create database indexes for performance"""
        indexes_config = {
            "users": [
                ("user_id", {"unique": True}),
                ("username", {"unique": True}),
                ("email", {"unique": True}),
                ("role", {}),
                ("is_active", {}),
                ("created_at", {})
            ],
            
            "user_sessions": [
                ("session_id", {"unique": True}),
                ("user_id", {}),
                ("state", {}),
                ("created_at", {}),
                ("expires_at", {}),
                ("is_active", {}),
                ([("user_id", 1), ("is_active", 1)], {})
            ],
            
            "session_chunks": [
                ("chunk_id", {"unique": True}),
                ("session_id", {}),
                ("sequence_number", {}),
                ("created_at", {}),
                ("expires_at", {}),
                ([("session_id", 1), ("sequence_number", 1)], {})
            ],
            
            "merkle_trees": [
                ("tree_id", {"unique": True}),
                ("session_id", {}),
                ("root_hash", {}),
                ("is_finalized", {}),
                ("created_at", {})
            ],
            
            "blocks": [
                ("block_id", {"unique": True}),
                ("height", {"unique": True}),
                ("block_hash", {"unique": True}),
                ("timestamp", {}),
                ("status", {}),
                ("proposer_node", {})
            ],
            
            "poot_proofs": [
                ("proof_id", {"unique": True}),
                ("node_id", {}),
                ("session_id", {}),
                ("timestamp", {}),
                ("is_valid", {}),
                ("block_height", {}),
                ([("node_id", 1), ("timestamp", 1)], {})
            ],
            
            "nodes": [
                ("node_id", {"unique": True}),
                ("node_type", {}),
                ("status", {}),
                ("owner_id", {}),
                ("is_active", {}),
                ("registered_at", {}),
                ("last_heartbeat", {})
            ],
            
            "node_pools": [
                ("pool_id", {"unique": True}),
                ("name", {"unique": True}),
                ("is_active", {}),
                ("created_at", {})
            ],
            
            "rdp_servers": [
                ("server_id", {"unique": True}),
                ("session_id", {}),
                ("port", {"unique": True}),
                ("status", {}),
                ("start_time", {}),
                ("last_activity", {})
            ],
            
            "rdp_connections": [
                ("connection_id", {"unique": True}),
                ("server_id", {}),
                ("client_ip", {}),
                ("connected_at", {}),
                ("is_active", {}),
                ([("server_id", 1), ("connected_at", 1)], {})
            ],
            
            "audit_logs": [
                ("log_id", {"unique": True}),
                ("event_type", {}),
                ("user_id", {}),
                ("session_id", {}),
                ("timestamp", {}),
                ("result", {}),
                ([("event_type", 1), ("timestamp", 1)], {})
            ],
            
            "system_events": [
                ("event_id", {"unique": True}),
                ("event_type", {}),
                ("severity", {}),
                ("component", {}),
                ("timestamp", {}),
                ("resolved", {}),
                ([("severity", 1), ("timestamp", 1)], {})
            ],
            
            "tron_transactions": [
                ("tx_id", {"unique": True}),
                ("from_address", {}),
                ("to_address", {}),
                ("transaction_type", {}),
                ("status", {}),
                ("timestamp", {}),
                ("block_number", {}),
                ([("from_address", 1), ("timestamp", 1)], {})
            ],
            
            "tron_wallets": [
                ("wallet_id", {"unique": True}),
                ("address", {"unique": True}),
                ("owner_id", {}),
                ("wallet_type", {}),
                ("is_active", {}),
                ("created_at", {}),
                ("last_updated", {})
            ]
        }
        
        for collection_name, indexes in indexes_config.items():
            if collection_name in self.collections:
                collection = self.collections[collection_name]
                
                for index_spec in indexes:
                    try:
                        if isinstance(index_spec[0], list):
                            # Compound index
                            index_fields = index_spec[0]
                            index_options = index_spec[1]
                            await collection.create_index(index_fields, **index_options)
                        else:
                            # Single field index
                            index_field = index_spec[0]
                            index_options = index_spec[1]
                            await collection.create_index(index_field, **index_options)
                        
                        logger.info(f"Created index on {collection_name}: {index_spec[0]}")
                        
                    except Exception as e:
                        logger.warning(f"Index might already exist on {collection_name}: {e}")
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics for all collections"""
        stats = {}
        
        for collection_name, collection in self.collections.items():
            try:
                count = await collection.count_documents({})
                stats[collection_name] = {
                    "document_count": count,
                    "indexes": len(await collection.list_indexes().to_list(length=None))
                }
            except Exception as e:
                stats[collection_name] = {"error": str(e)}
        
        return stats
    
    async def cleanup_expired_data(self) -> Dict[str, int]:
        """Cleanup expired data from collections"""
        cleanup_stats = {}
        current_time = datetime.utcnow()
        
        # Cleanup expired sessions
        try:
            session_result = await self.collections["user_sessions"].delete_many({
                "expires_at": {"$lt": current_time}
            })
            cleanup_stats["expired_sessions"] = session_result.deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
        
        # Cleanup expired chunks
        try:
            chunk_result = await self.collections["session_chunks"].delete_many({
                "expires_at": {"$lt": current_time}
            })
            cleanup_stats["expired_chunks"] = chunk_result.deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup expired chunks: {e}")
        
        # Cleanup old audit logs (keep last 90 days)
        try:
            cutoff_date = current_time.replace(day=current_time.day - 90)
            audit_result = await self.collections["audit_logs"].delete_many({
                "timestamp": {"$lt": cutoff_date}
            })
            cleanup_stats["old_audit_logs"] = audit_result.deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup old audit logs: {e}")
        
        # Cleanup resolved system events older than 30 days
        try:
            cutoff_date = current_time.replace(day=current_time.day - 30)
            event_result = await self.collections["system_events"].delete_many({
                "resolved": True,
                "timestamp": {"$lt": cutoff_date}
            })
            cleanup_stats["old_system_events"] = event_result.deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup old system events: {e}")
        
        return cleanup_stats
    
    async def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

# Example usage
if __name__ == "__main__":
    async def main():
        # Initialize MongoDB manager
        mongodb_uri = "mongodb://localhost:27017/lucid"
        manager = MongoDBManager(mongodb_uri)
        
        # Initialize database
        success = await manager.initialize()
        print(f"MongoDB initialized: {success}")
        
        if success:
            # Get collection statistics
            stats = await manager.get_collection_stats()
            print("Collection Statistics:")
            for collection, stat in stats.items():
                print(f"  {collection}: {stat}")
            
            # Test cleanup
            cleanup_stats = await manager.cleanup_expired_data()
            print(f"Cleanup Statistics: {cleanup_stats}")
            
            # Close connection
            await manager.close()
            print("MongoDB connection closed")
    
    asyncio.run(main())
