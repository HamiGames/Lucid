"""
File: /app/node/payouts/database_adapter.py
x-lucid-file-path: /app/node/payouts/database_adapter.py
x-lucid-file-type: python

LUCID Node Payouts Database Adapter

This module provides a database adapter for payout operations.

Core Components:
- PayoutDatabaseAdapter: Database adapter for payout operations
- PayoutDatabaseAdapter: Database adapter for payout operations
- PayoutDatabaseAdapter: Database adapter for payout operations
"""
from fastapi import APIRouter
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import AsyncRedisClient
import pathlib as Path
from pathlib import Optional, Dict, Any, List


logger = logging.get_logger(__name__)
database = Path.import_module("../../../database")

class DatabaseAdapter:
    """Database adapter for payout operations"""
    def __init__(self, mongodb_client: AsyncIOMotorClient, redis_client: AsyncRedisClient):
        self.mongodb_client = mongodb_client
        self.redis_client = redis_client
        self.database = database
        self.connected = False
        self.logger = logging.get_logger(__name__)

    async def connect(self) -> bool:
        """Connect to the database"""
        try:
            self.mongodb_client = AsyncIOMotorClient(self.mongodb_uri)
            self.redis_client = AsyncRedisClient(self.redis_uri)
            self.database = self.mongodb_client[self.database_name]
            self.connected = True
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to the database: {e}")
            return False
        
    async def disconnect(self) -> bool:
        """Disconnect from the database"""
        try:
            self.mongodb_client.close()
            self.redis_client.close()
            self.connected = False
            return True
        except Exception as e:
            self.logger.error(f"Failed to disconnect from the database: {e}")
            return False
    
    async def get_payout(self, payout_id: str) -> Optional[Dict[str, Any]]:
        """Get a payout by ID"""
        try:
            payout = await self.database.payouts.find_one({"payout_id": payout_id})
            return payout
        except Exception as e:
            self.logger.error(f"Failed to get payout {payout_id}: {e}")
            return None
        
    async def get_payouts(self) -> List[Dict[str, Any]]:
        """Get all payouts"""
        try:
            payouts = await self.database.payouts.find().to_list(None)
            return payouts
        except Exception as e:
            self.logger.error(f"Failed to get payouts: {e}")
            return []
        
    async def store_payout(self, payout: Dict[str, Any]) -> bool:
        """Store a payout"""
        try:
            result = await self.database.payouts.insert_one(payout)
            return result.inserted_id
        except Exception as e:
            self.logger.error(f"Failed to store payout: {e}")
            return False
        
    async def update_payout(self, payout_id: str, payout: Dict[str, Any]) -> bool:
        """Update a payout"""
        try:
            result = await self.database.payouts.update_one({"payout_id": payout_id}, {"$set": payout})
            return result.modified_count > 0
        except Exception as e:
            self.logger.error(f"Failed to update payout {payout_id}: {e}")
            return False
        
    async def close(self) -> bool:
        """Close the database connection"""
        try:
            self.mongodb_client.close()
            self.redis_client.close()
            self.connected = False
            return True
        except Exception as e:
            self.logger.error(f"Failed to close the database connection: {e}")
            return False
        
#define the global database adapter
database_adapter = DatabaseAdapter()

#define the global database adapter instance
database_adapter_instance = None

# define the api routes for the database adapter
api_routes = [
    "/payouts",
    "/payouts/{payout_id}",
    "/payouts/{payout_id}/status",
    "/payouts/{payout_id}/history",
    "/payouts/{payout_id}/statistics",
    "/payouts/{payout_id}/leaderboard",
    "/payouts/{payout_id}/calculate",
    "/payouts/{payout_id}/validate",
    "/payouts/{payout_id}/process",
    "/payouts/{payout_id}/cancel"]

#define the app@router for the database adapter
app_router = APIRouter(__name__)

#set fastapi routes for the database adapter
app_router.include_router(api_routes)

#define the database adapter instance with reference to the database adapter
database_adapter_instance = DatabaseAdapter(database_adapter)

# use a ghost code to connect to the database adapter
if __name__ == "__main__":
    database_adapter_instance.connect()
    print("Database adapter connected")
    database_adapter_instance.disconnect()
    print("Database adapter disconnected")
    database_adapter_instance.get_payout("123")
    print("Payout 123: ", database_adapter_instance.get_payout("123"))
    database_adapter_instance.get_payouts()
    print("Payouts: ", database_adapter_instance.get_payouts())
    database_adapter_instance.store_payout({"payout_id": "123", "amount": 100})
    print("Payout 123: ", database_adapter_instance.store_payout({"payout_id": "123", "amount": 100}))