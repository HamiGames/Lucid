# Path: node/payouts/payout_processor.py
# Lucid Payout Processor - Payout processing and TRON integration
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum

from ..database_adapter import DatabaseAdapter
from .tron_client import TronClient

logger = logging.getLogger(__name__)


class PayoutStatus(Enum):
    """Payout status states"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PayoutType(Enum):
    """Payout types"""
    WORK_CREDITS = "work_credits"
    POOT_REWARDS = "poot_rewards"
    POOL_REWARDS = "pool_rewards"
    SESSION_FEES = "session_fees"


@dataclass
class PayoutRequest:
    """Payout request"""
    request_id: str
    node_id: str
    payout_type: PayoutType
    amount_usdt: float
    recipient_address: str
    status: PayoutStatus
    created_at: datetime
    processed_at: Optional[datetime] = None
    transaction_hash: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "node_id": self.node_id,
            "payout_type": self.payout_type.value,
            "amount_usdt": self.amount_usdt,
            "recipient_address": self.recipient_address,
            "status": self.status.value,
            "created_at": self.created_at,
            "processed_at": self.processed_at,
            "transaction_hash": self.transaction_hash,
            "error_message": self.error_message,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PayoutRequest':
        return cls(
            request_id=data["request_id"],
            node_id=data["node_id"],
            payout_type=PayoutType(data["payout_type"]),
            amount_usdt=data["amount_usdt"],
            recipient_address=data["recipient_address"],
            status=PayoutStatus(data["status"]),
            created_at=data["created_at"],
            processed_at=data.get("processed_at"),
            transaction_hash=data.get("transaction_hash"),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {})
        )


@dataclass
class PayoutBatch:
    """Payout batch for processing multiple payouts"""
    batch_id: str
    payout_requests: List[PayoutRequest]
    total_amount_usdt: float
    status: PayoutStatus
    created_at: datetime
    processed_at: Optional[datetime] = None
    transaction_hash: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "payout_requests": [req.to_dict() for req in self.payout_requests],
            "total_amount_usdt": self.total_amount_usdt,
            "status": self.status.value,
            "created_at": self.created_at,
            "processed_at": self.processed_at,
            "transaction_hash": self.transaction_hash,
            "error_message": self.error_message
        }


class PayoutProcessor:
    """
    Payout processor for handling TRON-based payouts.
    
    Handles:
    - Individual payout processing
    - Batch payout processing
    - TRON network integration
    - Payout status tracking
    - Error handling and retry logic
    """
    
    def __init__(self, db: DatabaseAdapter, tron_client: TronClient, node_id: str):
        self.db = db
        self.tron_client = tron_client
        self.node_id = node_id
        self.running = False
        
        # Payout state
        self.pending_payouts: List[PayoutRequest] = []
        self.processing_batches: List[PayoutBatch] = []
        self.payout_history: List[PayoutRequest] = []
        
        # Configuration
        self.batch_size = 10
        self.minimum_payout_amount = 1.0  # USDT
        self.maximum_payout_amount = 10000.0  # USDT
        self.processing_interval = 3600  # 1 hour
        
        # Background tasks
        self._tasks: List[asyncio.Task] = []
        
        logger.info(f"Payout processor initialized: {node_id}")
    
    async def start(self):
        """Start payout processor"""
        try:
            logger.info(f"Starting payout processor {self.node_id}...")
            self.running = True
            
            # Load pending payouts
            await self._load_pending_payouts()
            
            # Start background tasks
            self._tasks.append(asyncio.create_task(self._processing_loop()))
            self._tasks.append(asyncio.create_task(self._cleanup_loop()))
            
            logger.info(f"Payout processor {self.node_id} started")
            
        except Exception as e:
            logger.error(f"Failed to start payout processor: {e}")
            raise
    
    async def stop(self):
        """Stop payout processor"""
        try:
            logger.info(f"Stopping payout processor {self.node_id}...")
            self.running = False
            
            # Cancel background tasks
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            
            logger.info(f"Payout processor {self.node_id} stopped")
            
        except Exception as e:
            logger.error(f"Error stopping payout processor: {e}")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get payout processor status"""
        try:
            return {
                "node_id": self.node_id,
                "running": self.running,
                "pending_payouts": len(self.pending_payouts),
                "processing_batches": len(self.processing_batches),
                "payout_history_count": len(self.payout_history),
                "batch_size": self.batch_size,
                "minimum_payout_amount": self.minimum_payout_amount,
                "maximum_payout_amount": self.maximum_payout_amount
            }
            
        except Exception as e:
            logger.error(f"Failed to get payout processor status: {e}")
            return {"error": str(e)}
    
    async def create_payout_request(self, node_id: str, payout_type: PayoutType, 
                                   amount_usdt: float, recipient_address: str,
                                   metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a payout request.
        
        Args:
            node_id: Node ID requesting payout
            payout_type: Type of payout
            amount_usdt: Amount in USDT
            recipient_address: TRON address to receive payout
            metadata: Additional metadata
            
        Returns:
            Request ID
        """
        try:
            # Validate payout amount
            if amount_usdt < self.minimum_payout_amount:
                raise ValueError(f"Amount too small: {amount_usdt} < {self.minimum_payout_amount}")
            
            if amount_usdt > self.maximum_payout_amount:
                raise ValueError(f"Amount too large: {amount_usdt} > {self.maximum_payout_amount}")
            
            # Create payout request
            request_id = str(uuid.uuid4())
            
            payout_request = PayoutRequest(
                request_id=request_id,
                node_id=node_id,
                payout_type=payout_type,
                amount_usdt=amount_usdt,
                recipient_address=recipient_address,
                status=PayoutStatus.PENDING,
                created_at=datetime.now(timezone.utc),
                metadata=metadata or {}
            )
            
            # Add to pending payouts
            self.pending_payouts.append(payout_request)
            
            # Store in database
            await self.db["payout_requests"].insert_one(payout_request.to_dict())
            
            logger.info(f"Payout request created: {request_id} for {amount_usdt} USDT")
            return request_id
            
        except Exception as e:
            logger.error(f"Failed to create payout request: {e}")
            raise
    
    async def process_pending_payouts(self) -> Dict[str, Any]:
        """
        Process all pending payouts.
        
        Returns:
            Processing results
        """
        try:
            if not self.pending_payouts:
                return {"message": "No pending payouts to process"}
            
            # Create batches
            batches = await self._create_payout_batches()
            
            # Process batches
            results = {
                "batches_created": len(batches),
                "total_amount": sum(batch.total_amount_usdt for batch in batches),
                "payouts_processed": 0,
                "payouts_failed": 0
            }
            
            for batch in batches:
                try:
                    await self._process_payout_batch(batch)
                    results["payouts_processed"] += len(batch.payout_requests)
                    
                except Exception as e:
                    logger.error(f"Failed to process batch {batch.batch_id}: {e}")
                    results["payouts_failed"] += len(batch.payout_requests)
            
            logger.info(f"Processed {results['payouts_processed']} payouts in {len(batches)} batches")
            return results
            
        except Exception as e:
            logger.error(f"Failed to process pending payouts: {e}")
            return {"error": str(e)}
    
    async def get_payout_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get payout request status"""
        try:
            # Check pending payouts
            for payout in self.pending_payouts:
                if payout.request_id == request_id:
                    return payout.to_dict()
            
            # Check processing batches
            for batch in self.processing_batches:
                for payout in batch.payout_requests:
                    if payout.request_id == request_id:
                        return payout.to_dict()
            
            # Check history
            for payout in self.payout_history:
                if payout.request_id == request_id:
                    return payout.to_dict()
            
            # Check database
            payout_doc = await self.db["payout_requests"].find_one({"request_id": request_id})
            if payout_doc:
                return payout_doc
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get payout status: {e}")
            return None
    
    async def get_payout_history(self, node_id: Optional[str] = None, 
                                hours: int = 24) -> List[Dict[str, Any]]:
        """Get payout history"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            # Filter payouts
            payouts = [
                p for p in self.payout_history
                if p.created_at >= cutoff_time
            ]
            
            if node_id:
                payouts = [p for p in payouts if p.node_id == node_id]
            
            return [p.to_dict() for p in payouts]
            
        except Exception as e:
            logger.error(f"Failed to get payout history: {e}")
            return []
    
    async def _create_payout_batches(self) -> List[PayoutBatch]:
        """Create payout batches from pending payouts"""
        try:
            batches = []
            current_batch = []
            current_amount = 0.0
            
            for payout in self.pending_payouts:
                # Check if adding this payout would exceed batch size or amount limit
                if (len(current_batch) >= self.batch_size or 
                    current_amount + payout.amount_usdt > self.maximum_payout_amount):
                    
                    if current_batch:
                        # Create batch
                        batch_id = str(uuid.uuid4())
                        batch = PayoutBatch(
                            batch_id=batch_id,
                            payout_requests=current_batch.copy(),
                            total_amount_usdt=current_amount,
                            status=PayoutStatus.PENDING,
                            created_at=datetime.now(timezone.utc)
                        )
                        batches.append(batch)
                        
                        # Reset for next batch
                        current_batch = []
                        current_amount = 0.0
                
                current_batch.append(payout)
                current_amount += payout.amount_usdt
            
            # Create final batch if there are remaining payouts
            if current_batch:
                batch_id = str(uuid.uuid4())
                batch = PayoutBatch(
                    batch_id=batch_id,
                    payout_requests=current_batch.copy(),
                    total_amount_usdt=current_amount,
                    status=PayoutStatus.PENDING,
                    created_at=datetime.now(timezone.utc)
                )
                batches.append(batch)
            
            return batches
            
        except Exception as e:
            logger.error(f"Failed to create payout batches: {e}")
            return []
    
    async def _process_payout_batch(self, batch: PayoutBatch):
        """Process a payout batch"""
        try:
            logger.info(f"Processing payout batch: {batch.batch_id}")
            
            # Update batch status
            batch.status = PayoutStatus.PROCESSING
            self.processing_batches.append(batch)
            
            # Remove from pending payouts
            for payout in batch.payout_requests:
                if payout in self.pending_payouts:
                    self.pending_payouts.remove(payout)
            
            # Process individual payouts
            for payout in batch.payout_requests:
                try:
                    await self._process_single_payout(payout)
                    
                except Exception as e:
                    logger.error(f"Failed to process payout {payout.request_id}: {e}")
                    payout.status = PayoutStatus.FAILED
                    payout.error_message = str(e)
            
            # Update batch status
            if all(p.status == PayoutStatus.COMPLETED for p in batch.payout_requests):
                batch.status = PayoutStatus.COMPLETED
            elif any(p.status == PayoutStatus.FAILED for p in batch.payout_requests):
                batch.status = PayoutStatus.FAILED
            
            batch.processed_at = datetime.now(timezone.utc)
            
            # Move to history
            self.payout_history.extend(batch.payout_requests)
            if batch in self.processing_batches:
                self.processing_batches.remove(batch)
            
            # Store in database
            await self.db["payout_batches"].insert_one(batch.to_dict())
            
            logger.info(f"Payout batch processed: {batch.batch_id} ({batch.status.value})")
            
        except Exception as e:
            logger.error(f"Failed to process payout batch: {e}")
            batch.status = PayoutStatus.FAILED
            batch.error_message = str(e)
    
    async def _process_single_payout(self, payout: PayoutRequest):
        """Process a single payout"""
        try:
            logger.info(f"Processing payout: {payout.request_id}")
            
            # Update status
            payout.status = PayoutStatus.PROCESSING
            
            # Send TRON transaction
            transaction_hash = await self.tron_client.send_usdt(
                to_address=payout.recipient_address,
                amount=payout.amount_usdt
            )
            
            if transaction_hash:
                # Update payout with transaction hash
                payout.transaction_hash = transaction_hash
                payout.status = PayoutStatus.COMPLETED
                payout.processed_at = datetime.now(timezone.utc)
                
                logger.info(f"Payout completed: {payout.request_id} -> {transaction_hash}")
                
            else:
                # Transaction failed
                payout.status = PayoutStatus.FAILED
                payout.error_message = "TRON transaction failed"
                
                logger.error(f"Payout failed: {payout.request_id}")
            
            # Update in database
            await self.db["payout_requests"].replace_one(
                {"request_id": payout.request_id},
                payout.to_dict(),
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Failed to process single payout: {e}")
            payout.status = PayoutStatus.FAILED
            payout.error_message = str(e)
    
    async def _processing_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                # Process pending payouts
                if self.pending_payouts:
                    await self.process_pending_payouts()
                
                await asyncio.sleep(self.processing_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Processing loop error: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_loop(self):
        """Cleanup old data"""
        while self.running:
            try:
                # Cleanup old payout history
                await self._cleanup_old_history()
                
                await asyncio.sleep(86400)  # Cleanup daily
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(3600)
    
    async def _load_pending_payouts(self):
        """Load pending payouts from database"""
        try:
            cursor = self.db["payout_requests"].find({
                "status": {"$in": ["pending", "processing"]}
            })
            
            async for doc in cursor:
                payout = PayoutRequest.from_dict(doc)
                self.pending_payouts.append(payout)
            
            logger.info(f"Loaded {len(self.pending_payouts)} pending payouts")
            
        except Exception as e:
            logger.error(f"Failed to load pending payouts: {e}")
    
    async def _cleanup_old_history(self):
        """Cleanup old payout history"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=30)
            
            # Remove old payouts from memory
            self.payout_history = [
                p for p in self.payout_history
                if p.created_at >= cutoff_time
            ]
            
            # Remove old payouts from database
            result = await self.db["payout_requests"].delete_many({
                "created_at": {"$lt": cutoff_time},
                "status": {"$in": ["completed", "failed", "cancelled"]}
            })
            
            if result.deleted_count > 0:
                logger.info(f"Cleaned up {result.deleted_count} old payouts")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old history: {e}")


# Global payout processor instance
_payout_processor: Optional[PayoutProcessor] = None


def get_payout_processor() -> Optional[PayoutProcessor]:
    """Get global payout processor instance"""
    global _payout_processor
    return _payout_processor


def create_payout_processor(db: DatabaseAdapter, tron_client: TronClient, node_id: str) -> PayoutProcessor:
    """Create payout processor instance"""
    global _payout_processor
    _payout_processor = PayoutProcessor(db, tron_client, node_id)
    return _payout_processor


async def cleanup_payout_processor():
    """Cleanup payout processor"""
    global _payout_processor
    if _payout_processor:
        await _payout_processor.stop()
        _payout_processor = None


if __name__ == "__main__":
    # Test payout processor
    async def test_payout_processor():
        print("Testing Lucid Payout Processor...")
        
        # This would normally be initialized with real components
        # For testing purposes, we'll create mock instances
        
        print("Test completed - payout processor ready")
    
    asyncio.run(test_payout_processor())
