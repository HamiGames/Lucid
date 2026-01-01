"""
Wallet Transaction History Service
Tracks and manages transaction history for wallets
"""

import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorCollection


logger = logging.getLogger(__name__)


class WalletTransactionHistoryService:
    """Service for managing wallet transaction history"""
    
    def __init__(self, history_collection: AsyncIOMotorCollection):
        """Initialize transaction history service"""
        self.history_collection = history_collection
        self._initialized = False
    
    async def initialize(self):
        """Initialize service and create indexes"""
        try:
            # Create indexes for efficient queries
            await self.history_collection.create_index("wallet_id")
            await self.history_collection.create_index("address")
            await self.history_collection.create_index("txid", unique=True)
            await self.history_collection.create_index("status")
            await self.history_collection.create_index("timestamp")
            await self.history_collection.create_index([("wallet_id", 1), ("timestamp", -1)])
            await self.history_collection.create_index([("address", 1), ("timestamp", -1)])
            await self.history_collection.create_index([("status", 1), ("timestamp", -1)])
            
            self._initialized = True
            logger.info("Transaction history service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize transaction history service: {e}")
            raise
    
    async def add_transaction(
        self,
        wallet_id: str,
        address: str,
        txid: str,
        transaction_data: Dict[str, Any]
    ) -> str:
        """Add a transaction to history"""
        try:
            history_record = {
                "wallet_id": wallet_id,
                "address": address,
                "txid": txid,
                "timestamp": datetime.now(timezone.utc),
                "status": transaction_data.get("status", "pending"),
                "transaction_data": transaction_data,
                "created_at": datetime.now(timezone.utc)
            }
            
            # Use upsert to avoid duplicates
            result = await self.history_collection.update_one(
                {"txid": txid},
                {"$set": history_record},
                upsert=True
            )
            
            logger.info(f"Added transaction {txid} to history for wallet {wallet_id}")
            return txid
            
        except Exception as e:
            logger.error(f"Failed to add transaction to history: {e}")
            raise
    
    async def get_transaction_history(
        self,
        wallet_id: Optional[str] = None,
        address: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get transaction history with filters"""
        try:
            query = {}
            
            if wallet_id:
                query["wallet_id"] = wallet_id
            if address:
                query["address"] = address
            if status:
                query["status"] = status
            if start_date or end_date:
                query["timestamp"] = {}
                if start_date:
                    query["timestamp"]["$gte"] = start_date
                if end_date:
                    query["timestamp"]["$lte"] = end_date
            
            cursor = self.history_collection.find(query).skip(skip).limit(limit).sort("timestamp", -1)
            transactions = await cursor.to_list(length=limit)
            
            # Convert ObjectId to string and format timestamps
            for tx in transactions:
                if "_id" in tx:
                    tx["_id"] = str(tx["_id"])
                if "timestamp" in tx and isinstance(tx["timestamp"], datetime):
                    tx["timestamp"] = tx["timestamp"].isoformat()
                if "created_at" in tx and isinstance(tx["created_at"], datetime):
                    tx["created_at"] = tx["created_at"].isoformat()
            
            return transactions
            
        except Exception as e:
            logger.error(f"Failed to get transaction history: {e}")
            raise
    
    async def update_transaction_status(
        self,
        txid: str,
        status: str,
        update_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update transaction status"""
        try:
            update_fields = {
                "status": status,
                "updated_at": datetime.now(timezone.utc)
            }
            
            if update_data:
                update_fields.update(update_data)
            
            result = await self.history_collection.update_one(
                {"txid": txid},
                {"$set": update_fields}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to update transaction status: {e}")
            raise
    
    async def get_transaction_stats(
        self,
        wallet_id: Optional[str] = None,
        address: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get transaction statistics"""
        try:
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            query = {"timestamp": {"$gte": start_date}}
            if wallet_id:
                query["wallet_id"] = wallet_id
            if address:
                query["address"] = address
            
            # Get total count
            total_count = await self.history_collection.count_documents(query)
            
            # Get counts by status
            status_counts = {}
            for status in ["pending", "confirmed", "failed", "cancelled"]:
                status_query = {**query, "status": status}
                status_counts[status] = await self.history_collection.count_documents(status_query)
            
            # Get recent transactions
            recent = await self.history_collection.find(query).sort("timestamp", -1).limit(10).to_list(length=10)
            
            return {
                "total_count": total_count,
                "status_counts": status_counts,
                "period_days": days,
                "recent_transactions": len(recent)
            }
            
        except Exception as e:
            logger.error(f"Failed to get transaction stats: {e}")
            raise

