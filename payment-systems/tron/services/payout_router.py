"""
LUCID Payment Systems - Payout Router Service
Payout routing and processing for TRON payments
Distroless container: lucid-payout-router:latest
"""

import asyncio
import logging
import os
import time
import hashlib
import json
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import aiofiles
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field
import httpx
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PayoutStatus(Enum):
    """Payout status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

class PayoutType(Enum):
    """Payout types"""
    IMMEDIATE = "immediate"
    SCHEDULED = "scheduled"
    BATCH = "batch"
    EMERGENCY = "emergency"

class PayoutReason(Enum):
    """Payout reasons"""
    SESSION_RELAY = "session_relay"
    STORAGE_PROOF = "storage_proof"
    VALIDATION_SIGNATURE = "validation_signature"
    UPTIME_REWARD = "uptime_reward"
    GOVERNANCE_PARTICIPATION = "governance_participation"
    CUSTOM = "custom"

@dataclass
class PayoutRequest:
    """Payout request data"""
    payout_id: str
    recipient_address: str
    amount_usdt: float
    payout_type: PayoutType
    reason: PayoutReason
    session_id: Optional[str] = None
    node_id: Optional[str] = None
    work_credits: Optional[float] = None
    custom_data: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    priority: int = 1
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class PayoutResult:
    """Payout result data"""
    payout_id: str
    request: PayoutRequest
    txid: Optional[str] = None
    status: PayoutStatus = PayoutStatus.PENDING
    processing_started: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    fee_paid: Optional[float] = None
    gas_used: Optional[int] = None
    energy_used: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 3

class PayoutRequestModel(BaseModel):
    """Pydantic model for payout requests"""
    recipient_address: str = Field(..., description="TRON address to receive USDT")
    amount_usdt: float = Field(..., gt=0, description="Amount in USDT")
    payout_type: PayoutType = Field(default=PayoutType.IMMEDIATE, description="Type of payout")
    reason: PayoutReason = Field(..., description="Reason for payout")
    session_id: Optional[str] = Field(default=None, description="Associated session ID")
    node_id: Optional[str] = Field(default=None, description="Associated node ID")
    work_credits: Optional[float] = Field(default=None, description="Work credits earned")
    custom_data: Optional[Dict[str, Any]] = Field(default=None, description="Custom data")
    expires_at: Optional[str] = Field(default=None, description="Expiration timestamp")
    priority: int = Field(default=1, description="Priority level (1-10)")

class PayoutResponseModel(BaseModel):
    """Pydantic model for payout responses"""
    payout_id: str
    txid: Optional[str] = None
    status: str
    message: str
    amount_usdt: float
    recipient_address: str
    created_at: str
    estimated_completion: Optional[str] = None

class PayoutRouterService:
    """Payout router service for TRON payments"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # TRON client configuration - from environment variables
        self.tron_client_url = os.getenv("TRON_CLIENT_URL", os.getenv("PAYOUT_ROUTER_TRON_CLIENT_URL", "http://lucid-tron-client:8091"))
        
        # Initialize TRON client
        self._initialize_tron_client()
        
        # Data storage - from environment variables
        data_base = os.getenv("DATA_DIRECTORY", os.getenv("TRON_DATA_DIR", "/data/payment-systems"))
        self.data_dir = Path(data_base) / "payout-router"
        self.payouts_dir = self.data_dir / "payouts"
        self.batches_dir = self.data_dir / "batches"
        self.logs_dir = self.data_dir / "logs"
        
        # Ensure directories exist
        for directory in [self.payouts_dir, self.batches_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Payout tracking
        self.pending_payouts: Dict[str, PayoutResult] = {}
        self.processing_payouts: Dict[str, PayoutResult] = {}
        self.completed_payouts: Dict[str, PayoutResult] = {}
        self.failed_payouts: Dict[str, PayoutResult] = {}
        
        # Batch processing
        self.batch_queue: List[PayoutRequest] = []
        self.batch_size = int(os.getenv("PAYOUT_BATCH_SIZE", "50"))
        self.batch_interval = int(os.getenv("PAYOUT_BATCH_INTERVAL", "300"))  # 5 minutes
        
        # Limits and validation
        self.max_payout_amount = float(os.getenv("MAX_PAYOUT_AMOUNT", "1000.0"))
        self.min_payout_amount = float(os.getenv("MIN_PAYOUT_AMOUNT", "0.01"))
        self.daily_limit = float(os.getenv("DAILY_PAYOUT_LIMIT", "10000.0"))
        self.daily_payouts: Dict[str, float] = {}  # date -> total_amount
        
        # Load existing data
        asyncio.create_task(self._load_existing_data())
        
        # Start processing tasks
        asyncio.create_task(self._process_immediate_payouts())
        asyncio.create_task(self._process_batch_payouts())
        asyncio.create_task(self._monitor_payouts())
        asyncio.create_task(self._cleanup_old_payouts())
        
        logger.info("PayoutRouterService initialized")
    
    def _initialize_tron_client(self):
        """Initialize TRON client connection"""
        try:
            # In production, this would connect to the TRON client service
            # For now, we'll use direct TRON connection
            self.tron = Tron()
            logger.info("TRON client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize TRON client: {e}")
            raise
    
    async def _load_existing_data(self):
        """Load existing payouts from disk"""
        try:
            # Load payouts
            payouts_file = self.payouts_dir / "payouts_registry.json"
            if payouts_file.exists():
                async with aiofiles.open(payouts_file, "r") as f:
                    data = await f.read()
                    payouts_data = json.loads(data)
                    
                    for payout_id, payout_data in payouts_data.items():
                        # Convert datetime strings back to datetime objects
                        for field in ['created_at', 'processing_started', 'completed_at', 'expires_at']:
                            if field in payout_data and payout_data[field]:
                                payout_data[field] = datetime.fromisoformat(payout_data[field])
                        
                        payout_result = PayoutResult(**payout_data)
                        
                        if payout_result.status == PayoutStatus.PENDING:
                            self.pending_payouts[payout_id] = payout_result
                        elif payout_result.status == PayoutStatus.PROCESSING:
                            self.processing_payouts[payout_id] = payout_result
                        elif payout_result.status == PayoutStatus.COMPLETED:
                            self.completed_payouts[payout_id] = payout_result
                        elif payout_result.status == PayoutStatus.FAILED:
                            self.failed_payouts[payout_id] = payout_result
                    
                logger.info(f"Loaded {len(self.pending_payouts)} pending, {len(self.processing_payouts)} processing, {len(self.completed_payouts)} completed, {len(self.failed_payouts)} failed payouts")
                
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
    
    async def _save_payouts_registry(self):
        """Save payouts registry to disk"""
        try:
            all_payouts = {
                **self.pending_payouts,
                **self.processing_payouts,
                **self.completed_payouts,
                **self.failed_payouts
            }
            
            payouts_data = {}
            for payout_id, payout_result in all_payouts.items():
                # Convert to dict and handle datetime serialization
                payout_dict = asdict(payout_result)
                for field in ['created_at', 'processing_started', 'completed_at', 'expires_at']:
                    if payout_dict.get(field):
                        payout_dict[field] = payout_dict[field].isoformat()
                payouts_data[payout_id] = payout_dict
            
            payouts_file = self.payouts_dir / "payouts_registry.json"
            async with aiofiles.open(payouts_file, "w") as f:
                await f.write(json.dumps(payouts_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving payouts registry: {e}")
    
    async def create_payout(self, request: PayoutRequestModel) -> PayoutResponseModel:
        """Create a new payout"""
        try:
            logger.info(f"Creating payout: {request.amount_usdt} USDT to {request.recipient_address}")
            
            # Validate payout request
            await self._validate_payout_request(request)
            
            # Generate payout ID
            payout_id = await self._generate_payout_id(request)
            
            # Convert to internal request format
            payout_request = PayoutRequest(
                payout_id=payout_id,
                recipient_address=request.recipient_address,
                amount_usdt=request.amount_usdt,
                payout_type=PayoutType(request.payout_type),
                reason=PayoutReason(request.reason),
                session_id=request.session_id,
                node_id=request.node_id,
                work_credits=request.work_credits,
                custom_data=request.custom_data,
                expires_at=datetime.fromisoformat(request.expires_at) if request.expires_at else None,
                priority=request.priority
            )
            
            # Create payout result
            payout_result = PayoutResult(
                payout_id=payout_id,
                request=payout_request,
                status=PayoutStatus.PENDING
            )
            
            # Process based on type
            if request.payout_type == PayoutType.IMMEDIATE:
                # Process immediately
                payout_result.status = PayoutStatus.PROCESSING
                payout_result.processing_started = datetime.now()
                self.processing_payouts[payout_id] = payout_result
                
                # Execute payout
                await self._execute_payout(payout_result)
                
            elif request.payout_type == PayoutType.BATCH:
                # Add to batch queue
                self.batch_queue.append(payout_request)
                self.pending_payouts[payout_id] = payout_result
                
            else:
                # Schedule for later processing
                self.pending_payouts[payout_id] = payout_result
            
            # Update daily limits
            await self._update_daily_limits(request.amount_usdt)
            
            # Save registry
            await self._save_payouts_registry()
            
            # Log payout creation
            await self._log_payout_event(payout_id, "payout_created", {
                "recipient_address": request.recipient_address,
                "amount_usdt": request.amount_usdt,
                "payout_type": request.payout_type,
                "reason": request.reason
            })
            
            logger.info(f"Created payout: {payout_id}")
            
            # Calculate estimated completion time
            estimated_completion = None
            if payout_result.txid:
                estimated_completion = (datetime.now() + timedelta(minutes=5)).isoformat()
            
            return PayoutResponseModel(
                payout_id=payout_id,
                txid=payout_result.txid,
                status=payout_result.status.value,
                message="Payout created successfully",
                amount_usdt=request.amount_usdt,
                recipient_address=request.recipient_address,
                created_at=payout_result.request.created_at.isoformat(),
                estimated_completion=estimated_completion
            )
            
        except Exception as e:
            logger.error(f"Error creating payout: {e}")
            raise
    
    async def _validate_payout_request(self, request: PayoutRequestModel):
        """Validate payout request"""
        # Check amount limits
        if request.amount_usdt < self.min_payout_amount:
            raise ValueError(f"Amount too small: {request.amount_usdt} < {self.min_payout_amount}")
        
        if request.amount_usdt > self.max_payout_amount:
            raise ValueError(f"Amount too large: {request.amount_usdt} > {self.max_payout_amount}")
        
        # Check daily limits
        today = datetime.now().date().isoformat()
        daily_total = self.daily_payouts.get(today, 0.0)
        if daily_total + request.amount_usdt > self.daily_limit:
            raise ValueError(f"Daily limit exceeded: {daily_total + request.amount_usdt} > {self.daily_limit}")
        
        # Validate TRON address
        if not request.recipient_address.startswith('T') or len(request.recipient_address) != 34:
            raise ValueError("Invalid TRON address format")
        
        # Check expiration
        if request.expires_at:
            expires_at = datetime.fromisoformat(request.expires_at)
            if expires_at < datetime.now():
                raise ValueError("Payout request has expired")
    
    async def _generate_payout_id(self, request: PayoutRequestModel) -> str:
        """Generate unique payout ID"""
        timestamp = int(time.time())
        recipient_hash = hashlib.sha256(request.recipient_address.encode()).hexdigest()[:8]
        amount_hash = hashlib.sha256(str(request.amount_usdt).encode()).hexdigest()[:4]
        
        return f"payout_{timestamp}_{recipient_hash}_{amount_hash}"
    
    async def _execute_payout(self, payout_result: PayoutResult):
        """Execute payout transaction"""
        try:
            logger.info(f"Executing payout: {payout_result.payout_id}")
            
            # In production, this would integrate with the actual TRON client service
            # For now, we'll simulate the transaction
            
            # Simulate transaction processing
            await asyncio.sleep(2)  # Simulate processing time
            
            # Generate mock transaction ID
            txid = f"tx_{int(time.time())}_{hashlib.sha256(payout_result.payout_id.encode()).hexdigest()[:16]}"
            
            # Update payout result
            payout_result.txid = txid
            payout_result.status = PayoutStatus.COMPLETED
            payout_result.completed_at = datetime.now()
            payout_result.fee_paid = 0.1  # Mock fee
            
            # Move to completed
            self.completed_payouts[payout_result.payout_id] = payout_result
            if payout_result.payout_id in self.processing_payouts:
                del self.processing_payouts[payout_result.payout_id]
            
            # Log completion
            await self._log_payout_event(payout_result.payout_id, "payout_completed", {
                "txid": txid,
                "amount_usdt": payout_result.request.amount_usdt,
                "recipient_address": payout_result.request.recipient_address
            })
            
            logger.info(f"Payout completed: {payout_result.payout_id} -> {txid}")
            
        except Exception as e:
            logger.error(f"Error executing payout {payout_result.payout_id}: {e}")
            payout_result.status = PayoutStatus.FAILED
            payout_result.error_message = str(e)
            
            # Move to failed
            self.failed_payouts[payout_result.payout_id] = payout_result
            if payout_result.payout_id in self.processing_payouts:
                del self.processing_payouts[payout_result.payout_id]
            
            # Log failure
            await self._log_payout_event(payout_result.payout_id, "payout_failed", {
                "error": str(e)
            })
    
    async def _process_immediate_payouts(self):
        """Process immediate payouts"""
        try:
            while True:
                # Process any pending immediate payouts
                for payout_id, payout_result in list(self.pending_payouts.items()):
                    if payout_result.request.payout_type == PayoutType.IMMEDIATE:
                        # Move to processing
                        payout_result.status = PayoutStatus.PROCESSING
                        payout_result.processing_started = datetime.now()
                        self.processing_payouts[payout_id] = payout_result
                        del self.pending_payouts[payout_id]
                        
                        # Execute payout
                        await self._execute_payout(payout_result)
                
                # Wait before next check
                await asyncio.sleep(10)  # Check every 10 seconds
                
        except asyncio.CancelledError:
            logger.info("Immediate payout processing cancelled")
        except Exception as e:
            logger.error(f"Error in immediate payout processing: {e}")
    
    async def _process_batch_payouts(self):
        """Process batch payouts"""
        try:
            while True:
                if len(self.batch_queue) >= self.batch_size:
                    # Process batch
                    batch_payouts = self.batch_queue[:self.batch_size]
                    self.batch_queue = self.batch_queue[self.batch_size:]
                    
                    logger.info(f"Processing batch of {len(batch_payouts)} payouts")
                    
                    for payout_request in batch_payouts:
                        payout_result = self.pending_payouts.get(payout_request.payout_id)
                        if payout_result:
                            # Move to processing
                            payout_result.status = PayoutStatus.PROCESSING
                            payout_result.processing_started = datetime.now()
                            self.processing_payouts[payout_request.payout_id] = payout_result
                            del self.pending_payouts[payout_request.payout_id]
                            
                            # Execute payout
                            await self._execute_payout(payout_result)
                
                # Wait before next check
                await asyncio.sleep(self.batch_interval)
                
        except asyncio.CancelledError:
            logger.info("Batch payout processing cancelled")
        except Exception as e:
            logger.error(f"Error in batch payout processing: {e}")
    
    async def _monitor_payouts(self):
        """Monitor payout status"""
        try:
            while True:
                # Check for expired payouts
                now = datetime.now()
                expired_payouts = []
                
                for payout_id, payout_result in self.pending_payouts.items():
                    if payout_result.request.expires_at and payout_result.request.expires_at < now:
                        payout_result.status = PayoutStatus.EXPIRED
                        expired_payouts.append(payout_id)
                
                # Remove expired payouts
                for payout_id in expired_payouts:
                    del self.pending_payouts[payout_id]
                    logger.info(f"Payout expired: {payout_id}")
                
                # Save registry
                if expired_payouts:
                    await self._save_payouts_registry()
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
        except asyncio.CancelledError:
            logger.info("Payout monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in payout monitoring: {e}")
    
    async def _cleanup_old_payouts(self):
        """Clean up old completed payouts"""
        try:
            while True:
                cutoff_date = datetime.now() - timedelta(days=30)
                
                old_payouts = []
                for payout_id, payout_result in self.completed_payouts.items():
                    if payout_result.completed_at and payout_result.completed_at < cutoff_date:
                        old_payouts.append(payout_id)
                
                # Remove old payouts
                for payout_id in old_payouts:
                    del self.completed_payouts[payout_id]
                
                if old_payouts:
                    await self._save_payouts_registry()
                    logger.info(f"Cleaned up {len(old_payouts)} old payouts")
                
                # Wait before next cleanup
                await asyncio.sleep(3600)  # Clean up every hour
                
        except asyncio.CancelledError:
            logger.info("Payout cleanup cancelled")
        except Exception as e:
            logger.error(f"Error in payout cleanup: {e}")
    
    async def _update_daily_limits(self, amount_usdt: float):
        """Update daily payout limits"""
        today = datetime.now().date().isoformat()
        self.daily_payouts[today] = self.daily_payouts.get(today, 0.0) + amount_usdt
    
    async def _log_payout_event(self, payout_id: str, event_type: str, data: Dict[str, Any]):
        """Log payout event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "payout_id": payout_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"payout_events_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging payout event: {e}")
    
    async def get_payout_status(self, payout_id: str) -> Optional[Dict[str, Any]]:
        """Get payout status"""
        try:
            # Check all payout collections
            all_payouts = {
                **self.pending_payouts,
                **self.processing_payouts,
                **self.completed_payouts,
                **self.failed_payouts
            }
            
            if payout_id not in all_payouts:
                return None
            
            payout_result = all_payouts[payout_id]
            
            return {
                "payout_id": payout_result.payout_id,
                "recipient_address": payout_result.request.recipient_address,
                "amount_usdt": payout_result.request.amount_usdt,
                "payout_type": payout_result.request.payout_type.value,
                "reason": payout_result.request.reason.value,
                "status": payout_result.status.value,
                "txid": payout_result.txid,
                "created_at": payout_result.request.created_at.isoformat(),
                "processing_started": payout_result.processing_started.isoformat() if payout_result.processing_started else None,
                "completed_at": payout_result.completed_at.isoformat() if payout_result.completed_at else None,
                "error_message": payout_result.error_message,
                "fee_paid": payout_result.fee_paid,
                "retry_count": payout_result.retry_count
            }
            
        except Exception as e:
            logger.error(f"Error getting payout status: {e}")
            return None
    
    async def list_payouts(self, status: Optional[PayoutStatus] = None, 
                          limit: int = 100) -> List[Dict[str, Any]]:
        """List payouts with optional status filter"""
        try:
            all_payouts = {
                **self.pending_payouts,
                **self.processing_payouts,
                **self.completed_payouts,
                **self.failed_payouts
            }
            
            if status:
                filtered_payouts = {k: v for k, v in all_payouts.items() 
                                  if v.status == status}
            else:
                filtered_payouts = all_payouts
            
            # Sort by creation time (newest first)
            sorted_payouts = sorted(filtered_payouts.items(), 
                                  key=lambda x: x[1].request.created_at, reverse=True)
            
            # Limit results
            limited_payouts = sorted_payouts[:limit]
            
            payouts_list = []
            for payout_id, payout_result in limited_payouts:
                payouts_list.append({
                    "payout_id": payout_result.payout_id,
                    "recipient_address": payout_result.request.recipient_address,
                    "amount_usdt": payout_result.request.amount_usdt,
                    "payout_type": payout_result.request.payout_type.value,
                    "reason": payout_result.request.reason.value,
                    "status": payout_result.status.value,
                    "txid": payout_result.txid,
                    "created_at": payout_result.request.created_at.isoformat(),
                    "completed_at": payout_result.completed_at.isoformat() if payout_result.completed_at else None,
                    "error_message": payout_result.error_message
                })
            
            return payouts_list
            
        except Exception as e:
            logger.error(f"Error listing payouts: {e}")
            return []
    
    async def get_payout_stats(self) -> Dict[str, Any]:
        """Get payout statistics"""
        try:
            all_payouts = {
                **self.pending_payouts,
                **self.processing_payouts,
                **self.completed_payouts,
                **self.failed_payouts
            }
            
            total_payouts = len(all_payouts)
            pending_payouts = len(self.pending_payouts)
            processing_payouts = len(self.processing_payouts)
            completed_payouts = len(self.completed_payouts)
            failed_payouts = len(self.failed_payouts)
            
            total_amount = sum(p.request.amount_usdt for p in all_payouts.values())
            completed_amount = sum(p.request.amount_usdt for p in all_payouts.values() 
                                 if p.status == PayoutStatus.COMPLETED)
            
            # Daily statistics
            today = datetime.now().date().isoformat()
            daily_amount = self.daily_payouts.get(today, 0.0)
            daily_count = sum(1 for p in all_payouts.values() 
                            if p.request.created_at.date().isoformat() == today)
            
            return {
                "total_payouts": total_payouts,
                "pending_payouts": pending_payouts,
                "processing_payouts": processing_payouts,
                "completed_payouts": completed_payouts,
                "failed_payouts": failed_payouts,
                "total_amount_usdt": total_amount,
                "completed_amount_usdt": completed_amount,
                "daily_amount_usdt": daily_amount,
                "daily_count": daily_count,
                "daily_limit_usdt": self.daily_limit,
                "batch_queue_size": len(self.batch_queue),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting payout stats: {e}")
            return {"error": str(e)}

# Global instance
payout_router_service = PayoutRouterService()

# Convenience functions for external use
async def create_payout(request: PayoutRequestModel) -> PayoutResponseModel:
    """Create a new payout"""
    return await payout_router_service.create_payout(request)

async def get_payout_status(payout_id: str) -> Optional[Dict[str, Any]]:
    """Get payout status"""
    return await payout_router_service.get_payout_status(payout_id)

async def list_payouts(status: Optional[PayoutStatus] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """List payouts"""
    return await payout_router_service.list_payouts(status, limit)

async def get_payout_stats() -> Dict[str, Any]:
    """Get payout statistics"""
    return await payout_router_service.get_payout_stats()

if __name__ == "__main__":
    # Example usage
    async def main():
        # Create a payout request
        payout_request = PayoutRequestModel(
            recipient_address="TYourTRONAddressHere123456789",
            amount_usdt=10.0,
            payout_type=PayoutType.IMMEDIATE,
            reason=PayoutReason.SESSION_RELAY,
            session_id="session_123",
            work_credits=5.5
        )
        
        try:
            # Create payout
            response = await create_payout(payout_request)
            print(f"Payout created: {response}")
            
            # Get status
            status = await get_payout_status(response.payout_id)
            print(f"Payout status: {status}")
            
            # List recent payouts
            payouts = await list_payouts(limit=10)
            print(f"Recent payouts: {len(payouts)}")
            
            # Get statistics
            stats = await get_payout_stats()
            print(f"Payout stats: {stats}")
            
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main())
