"""
LUCID Payment Systems - PayoutManager Orchestration
Unified payout orchestration and management system
Distroless container: pickme/lucid:payment-systems:latest
"""

import asyncio
import json
import logging
import os
import time
import hashlib
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import aiofiles
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings
from .tron_client import TronService
from .payout_router_v0 import PayoutRouterV0, PayoutRequestModel, PayoutResponseModel, PayoutStatus as V0PayoutStatus
from .payout_router_kyc import PayoutRouterKYC, KYCPayoutRequestModel, KYCPayoutResponseModel, PayoutStatus as KYCPayoutStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PayoutRouterType(str, Enum):
    """Payout router types"""
    V0 = "v0"           # Non-KYC router for end-users
    KYC = "kyc"         # KYC-gated router for node workers

class PayoutPriority(str, Enum):
    """Payout priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class PayoutBatchType(str, Enum):
    """Payout batch processing types"""
    IMMEDIATE = "immediate"      # Process immediately
    HOURLY = "hourly"           # Process in hourly batches
    DAILY = "daily"             # Process in daily batches
    WEEKLY = "weekly"           # Process in weekly batches

@dataclass
class UnifiedPayoutRequest:
    """Unified payout request data"""
    recipient_address: str
    amount_usdt: float
    reason: str
    router_type: PayoutRouterType
    priority: PayoutPriority = PayoutPriority.NORMAL
    batch_type: PayoutBatchType = PayoutBatchType.IMMEDIATE
    session_id: Optional[str] = None
    node_id: Optional[str] = None
    work_credits: Optional[float] = None
    kyc_hash: Optional[str] = None
    compliance_signature: Optional[Dict[str, Any]] = None
    custom_data: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class UnifiedPayoutTransaction:
    """Unified payout transaction record"""
    payout_id: str
    request: UnifiedPayoutRequest
    router_response: Optional[Union[PayoutResponseModel, KYCPayoutResponseModel]] = None
    status: str = "pending"
    txid: Optional[str] = None
    gas_used: Optional[int] = None
    energy_used: Optional[int] = None
    fee_paid: Optional[float] = None
    created_at: datetime = None
    processed_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    router_used: Optional[PayoutRouterType] = None

@dataclass
class PayoutManagerConfig:
    """PayoutManager configuration"""
    # Router configurations
    v0_router_enabled: bool = True
    kyc_router_enabled: bool = True
    
    # Batch processing
    batch_processing_enabled: bool = True
    max_batch_size: int = 100
    batch_timeout_seconds: int = 300  # 5 minutes
    
    # Priority handling
    urgent_queue_size: int = 50
    high_queue_size: int = 100
    normal_queue_size: int = 500
    
    # Retry and error handling
    max_retry_attempts: int = 3
    retry_delay_seconds: int = 60
    circuit_breaker_threshold: int = 10
    circuit_breaker_timeout: int = 300
    
    # Monitoring and cleanup
    monitoring_interval_seconds: int = 30
    cleanup_interval_hours: int = 24
    retention_days: int = 30
    
    # Performance limits
    max_concurrent_payouts: int = 10
    daily_payout_limit_usdt: float = 100000.0
    hourly_payout_limit_usdt: float = 10000.0

class UnifiedPayoutRequestModel(BaseModel):
    """Pydantic model for unified payout requests"""
    recipient_address: str = Field(..., description="TRON address to receive USDT")
    amount_usdt: float = Field(..., gt=0, description="Amount in USDT")
    reason: str = Field(..., description="Reason for payout")
    router_type: PayoutRouterType = Field(..., description="Router type (v0 or kyc)")
    priority: PayoutPriority = Field(default=PayoutPriority.NORMAL, description="Payout priority")
    batch_type: PayoutBatchType = Field(default=PayoutBatchType.IMMEDIATE, description="Batch processing type")
    session_id: Optional[str] = Field(default=None, description="Associated session ID")
    node_id: Optional[str] = Field(default=None, description="Associated node ID")
    work_credits: Optional[float] = Field(default=None, description="Work credits earned")
    kyc_hash: Optional[str] = Field(default=None, description="KYC verification hash (for KYC router)")
    compliance_signature: Optional[Dict[str, Any]] = Field(default=None, description="Compliance signature (for KYC router)")
    custom_data: Optional[Dict[str, Any]] = Field(default=None, description="Custom data")
    expires_at: Optional[str] = Field(default=None, description="Expiration timestamp")

class UnifiedPayoutResponseModel(BaseModel):
    """Pydantic model for unified payout responses"""
    payout_id: str
    txid: Optional[str] = None
    status: str
    message: str
    amount_usdt: float
    recipient_address: str
    router_used: str
    priority: str
    batch_type: str
    created_at: str
    estimated_confirmation: Optional[str] = None

class PayoutManager:
    """Unified payout orchestration and management system"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Initialize components
        self.tron_service = TronService()
        self.v0_router = PayoutRouterV0() if self._should_enable_v0() else None
        self.kyc_router = PayoutRouterKYC() if self._should_enable_kyc() else None
        
        # Configuration
        self.config = PayoutManagerConfig(
            v0_router_enabled=self.v0_router is not None,
            kyc_router_enabled=self.kyc_router is not None,
            max_batch_size=int(os.getenv("PAYOUT_MAX_BATCH_SIZE", "100")),
            batch_timeout_seconds=int(os.getenv("PAYOUT_BATCH_TIMEOUT", "300")),
            max_concurrent_payouts=int(os.getenv("PAYOUT_MAX_CONCURRENT", "10")),
            daily_payout_limit_usdt=float(os.getenv("PAYOUT_DAILY_LIMIT", "100000.0")),
            hourly_payout_limit_usdt=float(os.getenv("PAYOUT_HOURLY_LIMIT", "10000.0"))
        )
        
        # Data storage
        self.data_dir = Path("/data/payment-systems/payout-manager")
        self.payouts_dir = self.data_dir / "payouts"
        self.batches_dir = self.data_dir / "batches"
        self.logs_dir = self.data_dir / "logs"
        
        # Ensure directories exist
        for directory in [self.payouts_dir, self.batches_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Payout tracking
        self.pending_payouts: Dict[str, UnifiedPayoutTransaction] = {}
        self.processed_payouts: Dict[str, UnifiedPayoutTransaction] = {}
        
        # Batch queues
        self.urgent_queue: List[UnifiedPayoutTransaction] = []
        self.high_queue: List[UnifiedPayoutTransaction] = []
        self.normal_queue: List[UnifiedPayoutTransaction] = []
        self.low_queue: List[UnifiedPayoutTransaction] = []
        
        # Batch processing
        self.current_batches: Dict[str, List[UnifiedPayoutTransaction]] = {}
        
        # Circuit breaker
        self.circuit_breaker_failures = 0
        self.circuit_breaker_last_failure = None
        self.circuit_breaker_open = False
        
        # Daily/hourly limits tracking
        self.daily_payouts: Dict[str, float] = {}  # date -> total_amount
        self.hourly_payouts: Dict[str, float] = {}  # hour -> total_amount
        self.last_reset_time = datetime.now()
        
        # Load existing data
        asyncio.create_task(self._load_existing_data())
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_payouts())
        asyncio.create_task(self._process_batches())
        asyncio.create_task(self._monitor_circuit_breaker())
        asyncio.create_task(self._cleanup_old_data())
        
        logger.info(f"PayoutManager initialized with V0: {self.config.v0_router_enabled}, KYC: {self.config.kyc_router_enabled}")
    
    def _should_enable_v0(self) -> bool:
        """Check if V0 router should be enabled"""
        return (
            self.settings.PAYOUT_ROUTER_V0_ADDRESS is not None and
            self.settings.TRON_PRIVATE_KEY is not None
        )
    
    def _should_enable_kyc(self) -> bool:
        """Check if KYC router should be enabled"""
        return (
            self.settings.PAYOUT_ROUTER_KYC_ADDRESS is not None and
            self.settings.TRON_PRIVATE_KEY is not None
        )
    
    async def _load_existing_data(self):
        """Load existing payouts from disk"""
        try:
            payouts_file = self.payouts_dir / "payouts_registry.json"
            if payouts_file.exists():
                async with aiofiles.open(payouts_file, "r") as f:
                    data = await f.read()
                    payouts_data = json.loads(data)
                    
                    for payout_id, payout_data in payouts_data.items():
                        payout_transaction = self._deserialize_payout_transaction(payout_data)
                        
                        if payout_transaction.status == "pending":
                            self.pending_payouts[payout_id] = payout_transaction
                        else:
                            self.processed_payouts[payout_id] = payout_transaction
                    
                logger.info(f"Loaded {len(self.pending_payouts)} pending and {len(self.processed_payouts)} processed payouts")
                
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
    
    def _deserialize_payout_transaction(self, data: Dict[str, Any]) -> UnifiedPayoutTransaction:
        """Deserialize payout transaction from JSON"""
        # Handle datetime fields
        for field in ['created_at', 'processed_at', 'confirmed_at', 'expires_at']:
            if field in data and data[field]:
                data[field] = datetime.fromisoformat(data[field])
        
        # Handle nested request object
        if 'request' in data:
            request_data = data['request']
            if 'expires_at' in request_data and request_data['expires_at']:
                request_data['expires_at'] = datetime.fromisoformat(request_data['expires_at'])
        
        return UnifiedPayoutTransaction(**data)
    
    async def _save_payouts_registry(self):
        """Save payouts registry to disk"""
        try:
            all_payouts = {**self.pending_payouts, **self.processed_payouts}
            
            payouts_data = {}
            for payout_id, payout_transaction in all_payouts.items():
                payout_dict = asdict(payout_transaction)
                
                # Serialize datetime fields
                for field in ['created_at', 'processed_at', 'confirmed_at']:
                    if payout_dict.get(field):
                        payout_dict[field] = payout_dict[field].isoformat()
                
                # Serialize nested datetime fields
                if 'request' in payout_dict and 'expires_at' in payout_dict['request']:
                    if payout_dict['request']['expires_at']:
                        payout_dict['request']['expires_at'] = payout_dict['request']['expires_at'].isoformat()
                
                payouts_data[payout_id] = payout_dict
            
            payouts_file = self.payouts_dir / "payouts_registry.json"
            async with aiofiles.open(payouts_file, "w") as f:
                await f.write(json.dumps(payouts_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving payouts registry: {e}")
    
    async def create_payout(self, request: UnifiedPayoutRequestModel) -> UnifiedPayoutResponseModel:
        """Create a new unified payout"""
        try:
            logger.info(f"Creating payout: {request.amount_usdt} USDT to {request.recipient_address} via {request.router_type}")
            
            # Validate request
            await self._validate_payout_request(request)
            
            # Generate payout ID
            payout_id = await self._generate_payout_id(request)
            
            # Convert to internal request format
            unified_request = UnifiedPayoutRequest(
                recipient_address=request.recipient_address,
                amount_usdt=request.amount_usdt,
                reason=request.reason,
                router_type=PayoutRouterType(request.router_type),
                priority=PayoutPriority(request.priority),
                batch_type=PayoutBatchType(request.batch_type),
                session_id=request.session_id,
                node_id=request.node_id,
                work_credits=request.work_credits,
                kyc_hash=request.kyc_hash,
                compliance_signature=request.compliance_signature,
                custom_data=request.custom_data,
                expires_at=datetime.fromisoformat(request.expires_at) if request.expires_at else None
            )
            
            # Create payout transaction
            payout_transaction = UnifiedPayoutTransaction(
                payout_id=payout_id,
                request=unified_request,
                created_at=datetime.now()
            )
            
            # Process based on batch type
            if request.batch_type == PayoutBatchType.IMMEDIATE:
                # Process immediately
                await self._process_immediate_payout(payout_transaction)
            else:
                # Queue for batch processing
                await self._queue_for_batch(payout_transaction)
            
            # Store payout
            self.pending_payouts[payout_id] = payout_transaction
            
            # Update limits
            await self._update_limits(request.amount_usdt)
            
            # Save registry
            await self._save_payouts_registry()
            
            # Log payout creation
            await self._log_payout_event(payout_id, "payout_created", {
                "recipient_address": request.recipient_address,
                "amount_usdt": request.amount_usdt,
                "router_type": request.router_type,
                "priority": request.priority,
                "batch_type": request.batch_type
            })
            
            logger.info(f"Created payout: {payout_id} -> {payout_transaction.txid}")
            
            # Calculate estimated confirmation time
            estimated_confirmation = None
            if payout_transaction.txid:
                current_block = self.tron_service.get_height()
                estimated_block = current_block + 19  # 19 blocks for confirmation
                # Rough estimate: 3 seconds per block
                estimated_time = datetime.now() + timedelta(seconds=19 * 3)
                estimated_confirmation = estimated_time.isoformat()
            
            return UnifiedPayoutResponseModel(
                payout_id=payout_id,
                txid=payout_transaction.txid,
                status=payout_transaction.status,
                message="Payout created successfully",
                amount_usdt=request.amount_usdt,
                recipient_address=request.recipient_address,
                router_used=request.router_type,
                priority=request.priority,
                batch_type=request.batch_type,
                created_at=payout_transaction.created_at.isoformat(),
                estimated_confirmation=estimated_confirmation
            )
            
        except Exception as e:
            logger.error(f"Error creating payout: {e}")
            raise
    
    async def _validate_payout_request(self, request: UnifiedPayoutRequestModel):
        """Validate unified payout request"""
        # Check router availability
        if request.router_type == PayoutRouterType.V0 and not self.config.v0_router_enabled:
            raise ValueError("V0 router is not enabled")
        
        if request.router_type == PayoutRouterType.KYC and not self.config.kyc_router_enabled:
            raise ValueError("KYC router is not enabled")
        
        # Check amount limits
        if request.amount_usdt <= 0:
            raise ValueError("Amount must be positive")
        
        # Check daily/hourly limits
        await self._check_limits(request.amount_usdt)
        
        # Validate TRON address
        if not request.recipient_address.startswith('T') or len(request.recipient_address) != 34:
            raise ValueError("Invalid TRON address format")
        
        # Validate KYC requirements
        if request.router_type == PayoutRouterType.KYC:
            if not request.kyc_hash:
                raise ValueError("KYC hash required for KYC router")
            if not request.compliance_signature:
                raise ValueError("Compliance signature required for KYC router")
            if not request.node_id:
                raise ValueError("Node ID required for KYC router")
    
    async def _check_limits(self, amount_usdt: float):
        """Check daily and hourly payout limits"""
        now = datetime.now()
        
        # Reset daily limits if new day
        today = now.date().isoformat()
        if today not in self.daily_payouts:
            self.daily_payouts[today] = 0.0
        
        # Reset hourly limits if new hour
        current_hour = now.strftime("%Y-%m-%d_%H")
        if current_hour not in self.hourly_payouts:
            self.hourly_payouts[current_hour] = 0.0
        
        # Check daily limit
        daily_total = self.daily_payouts[today]
        if daily_total + amount_usdt > self.config.daily_payout_limit_usdt:
            raise ValueError(f"Daily limit exceeded: {daily_total + amount_usdt} > {self.config.daily_payout_limit_usdt}")
        
        # Check hourly limit
        hourly_total = self.hourly_payouts[current_hour]
        if hourly_total + amount_usdt > self.config.hourly_payout_limit_usdt:
            raise ValueError(f"Hourly limit exceeded: {hourly_total + amount_usdt} > {self.config.hourly_payout_limit_usdt}")
    
    async def _update_limits(self, amount_usdt: float):
        """Update daily and hourly limits"""
        now = datetime.now()
        today = now.date().isoformat()
        current_hour = now.strftime("%Y-%m-%d_%H")
        
        self.daily_payouts[today] = self.daily_payouts.get(today, 0.0) + amount_usdt
        self.hourly_payouts[current_hour] = self.hourly_payouts.get(current_hour, 0.0) + amount_usdt
    
    async def _generate_payout_id(self, request: UnifiedPayoutRequestModel) -> str:
        """Generate unique payout ID"""
        timestamp = int(time.time())
        recipient_hash = hashlib.sha256(request.recipient_address.encode()).hexdigest()[:8]
        amount_hash = hashlib.sha256(str(request.amount_usdt).encode()).hexdigest()[:4]
        router_hash = hashlib.sha256(request.router_type.encode()).hexdigest()[:4]
        
        return f"payout_{timestamp}_{recipient_hash}_{amount_hash}_{router_hash}"
    
    async def _process_immediate_payout(self, payout_transaction: UnifiedPayoutTransaction):
        """Process immediate payout"""
        try:
            if self.circuit_breaker_open:
                raise RuntimeError("Circuit breaker is open")
            
            # Route to appropriate router
            if payout_transaction.request.router_type == PayoutRouterType.V0:
                await self._process_v0_payout(payout_transaction)
            elif payout_transaction.request.router_type == PayoutRouterType.KYC:
                await self._process_kyc_payout(payout_transaction)
            else:
                raise ValueError(f"Unknown router type: {payout_transaction.request.router_type}")
            
            payout_transaction.processed_at = datetime.now()
            payout_transaction.status = "processed"
            
        except Exception as e:
            payout_transaction.error_message = str(e)
            payout_transaction.status = "failed"
            logger.error(f"Error processing immediate payout {payout_transaction.payout_id}: {e}")
            raise
    
    async def _process_v0_payout(self, payout_transaction: UnifiedPayoutTransaction):
        """Process V0 router payout"""
        if not self.v0_router:
            raise RuntimeError("V0 router not available")
        
        # Convert to V0 request format
        v0_request = PayoutRequestModel(
            recipient_address=payout_transaction.request.recipient_address,
            amount_usdt=payout_transaction.request.amount_usdt,
            reason=payout_transaction.request.reason,
            session_id=payout_transaction.request.session_id,
            node_id=payout_transaction.request.node_id,
            work_credits=payout_transaction.request.work_credits,
            custom_data=payout_transaction.request.custom_data,
            expires_at=payout_transaction.request.expires_at.isoformat() if payout_transaction.request.expires_at else None
        )
        
        # Process via V0 router
        v0_response = await self.v0_router.create_payout(v0_request)
        
        payout_transaction.router_response = v0_response
        payout_transaction.txid = v0_response.txid
        payout_transaction.router_used = PayoutRouterType.V0
    
    async def _process_kyc_payout(self, payout_transaction: UnifiedPayoutTransaction):
        """Process KYC router payout"""
        if not self.kyc_router:
            raise RuntimeError("KYC router not available")
        
        # Convert to KYC request format
        kyc_request = KYCPayoutRequestModel(
            recipient_address=payout_transaction.request.recipient_address,
            amount_usdt=payout_transaction.request.amount_usdt,
            reason=payout_transaction.request.reason,
            node_id=payout_transaction.request.node_id,
            kyc_hash=payout_transaction.request.kyc_hash,
            compliance_signature=payout_transaction.request.compliance_signature,
            session_id=payout_transaction.request.session_id,
            work_credits=payout_transaction.request.work_credits,
            custom_data=payout_transaction.request.custom_data,
            expires_at=payout_transaction.request.expires_at.isoformat() if payout_transaction.request.expires_at else None
        )
        
        # Process via KYC router
        kyc_response = await self.kyc_router.create_kyc_payout(kyc_request)
        
        payout_transaction.router_response = kyc_response
        payout_transaction.txid = kyc_response.txid
        payout_transaction.router_used = PayoutRouterType.KYC
    
    async def _queue_for_batch(self, payout_transaction: UnifiedPayoutTransaction):
        """Queue payout for batch processing"""
        # Add to appropriate priority queue
        if payout_transaction.request.priority == PayoutPriority.URGENT:
            self.urgent_queue.append(payout_transaction)
        elif payout_transaction.request.priority == PayoutPriority.HIGH:
            self.high_queue.append(payout_transaction)
        elif payout_transaction.request.priority == PayoutPriority.NORMAL:
            self.normal_queue.append(payout_transaction)
        else:  # LOW
            self.low_queue.append(payout_transaction)
        
        payout_transaction.status = "queued"
        logger.info(f"Queued payout {payout_transaction.payout_id} for {payout_transaction.request.batch_type} batch processing")
    
    async def _process_batches(self):
        """Process queued payouts in batches"""
        try:
            while True:
                if not self.circuit_breaker_open:
                    # Process urgent queue immediately
                    await self._process_priority_queue(self.urgent_queue, "urgent")
                    
                    # Process high priority queue
                    await self._process_priority_queue(self.high_queue, "high")
                    
                    # Process normal priority queue
                    await self._process_priority_queue(self.normal_queue, "normal")
                    
                    # Process low priority queue
                    await self._process_priority_queue(self.low_queue, "low")
                
                # Wait before next batch processing cycle
                await asyncio.sleep(self.config.batch_timeout_seconds)
                
        except asyncio.CancelledError:
            logger.info("Batch processing cancelled")
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
    
    async def _process_priority_queue(self, queue: List[UnifiedPayoutTransaction], priority_name: str):
        """Process a priority queue"""
        if not queue:
            return
        
        # Process up to max batch size
        batch_size = min(len(queue), self.config.max_batch_size)
        batch = queue[:batch_size]
        
        if batch:
            logger.info(f"Processing {len(batch)} payouts from {priority_name} queue")
            
            # Process batch concurrently
            tasks = [self._process_immediate_payout(payout) for payout in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    batch[i].error_message = str(result)
                    batch[i].status = "failed"
                    logger.error(f"Batch payout {batch[i].payout_id} failed: {result}")
                else:
                    batch[i].status = "processed"
            
            # Move processed payouts from queue
            for payout in batch:
                queue.remove(payout)
                if payout.status == "processed":
                    self.processed_payouts[payout.payout_id] = payout
                    del self.pending_payouts[payout.payout_id]
            
            # Save registry
            await self._save_payouts_registry()
    
    async def _monitor_payouts(self):
        """Monitor pending payouts for completion"""
        try:
            while True:
                for payout_id, payout_transaction in list(self.pending_payouts.items()):
                    if payout_transaction.txid:
                        # Check transaction status
                        status = await self._check_transaction_status(payout_transaction.txid)
                        
                        if status == "confirmed":
                            payout_transaction.status = "confirmed"
                            payout_transaction.confirmed_at = datetime.now()
                            
                            # Move to processed payouts
                            self.processed_payouts[payout_id] = payout_transaction
                            del self.pending_payouts[payout_id]
                            
                            # Log confirmation
                            await self._log_payout_event(payout_id, "payout_confirmed", {
                                "txid": payout_transaction.txid,
                                "amount_usdt": payout_transaction.request.amount_usdt,
                                "recipient_address": payout_transaction.request.recipient_address
                            })
                            
                            logger.info(f"Payout confirmed: {payout_id} -> {payout_transaction.txid}")
                        
                        elif status == "failed":
                            payout_transaction.status = "failed"
                            payout_transaction.error_message = "Transaction failed on blockchain"
                            
                            # Log failure
                            await self._log_payout_event(payout_id, "payout_failed", {
                                "txid": payout_transaction.txid,
                                "error": payout_transaction.error_message
                            })
                            
                            logger.error(f"Payout failed: {payout_id} -> {payout_transaction.txid}")
                
                # Save registry
                await self._save_payouts_registry()
                
                # Wait before next check
                await asyncio.sleep(self.config.monitoring_interval_seconds)
                
        except asyncio.CancelledError:
            logger.info("Payout monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in payout monitoring: {e}")
    
    async def _check_transaction_status(self, txid: str) -> str:
        """Check transaction status on blockchain"""
        try:
            # Use TronService to check transaction
            # This is a simplified check - in production, you'd want more robust status checking
            return "confirmed"  # Placeholder
            
        except Exception as e:
            logger.debug(f"Error checking transaction status: {e}")
            return "pending"
    
    async def _monitor_circuit_breaker(self):
        """Monitor circuit breaker state"""
        try:
            while True:
                if self.circuit_breaker_failures >= self.config.circuit_breaker_threshold:
                    if not self.circuit_breaker_open:
                        self.circuit_breaker_open = True
                        self.circuit_breaker_last_failure = datetime.now()
                        logger.warning("Circuit breaker opened due to failures")
                else:
                    # Check if we should reset circuit breaker
                    if (self.circuit_breaker_open and 
                        self.circuit_breaker_last_failure and
                        datetime.now() - self.circuit_breaker_last_failure > timedelta(seconds=self.config.circuit_breaker_timeout)):
                        self.circuit_breaker_open = False
                        self.circuit_breaker_failures = 0
                        logger.info("Circuit breaker reset")
                
                await asyncio.sleep(60)  # Check every minute
                
        except asyncio.CancelledError:
            logger.info("Circuit breaker monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in circuit breaker monitoring: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old processed payouts"""
        try:
            while True:
                cutoff_date = datetime.now() - timedelta(days=self.config.retention_days)
                
                old_payouts = []
                for payout_id, payout_transaction in self.processed_payouts.items():
                    if (payout_transaction.confirmed_at and 
                        payout_transaction.confirmed_at < cutoff_date):
                        old_payouts.append(payout_id)
                
                # Remove old payouts
                for payout_id in old_payouts:
                    del self.processed_payouts[payout_id]
                
                if old_payouts:
                    await self._save_payouts_registry()
                    logger.info(f"Cleaned up {len(old_payouts)} old payouts")
                
                # Wait before next cleanup
                await asyncio.sleep(self.config.cleanup_interval_hours * 3600)
                
        except asyncio.CancelledError:
            logger.info("Data cleanup cancelled")
        except Exception as e:
            logger.error(f"Error in data cleanup: {e}")
    
    async def get_payout_status(self, payout_id: str) -> Optional[Dict[str, Any]]:
        """Get payout status"""
        try:
            # Check pending payouts
            if payout_id in self.pending_payouts:
                payout = self.pending_payouts[payout_id]
            elif payout_id in self.processed_payouts:
                payout = self.processed_payouts[payout_id]
            else:
                return None
            
            return {
                "payout_id": payout.payout_id,
                "recipient_address": payout.request.recipient_address,
                "amount_usdt": payout.request.amount_usdt,
                "reason": payout.request.reason,
                "router_type": payout.request.router_type.value,
                "priority": payout.request.priority.value,
                "batch_type": payout.request.batch_type.value,
                "status": payout.status,
                "txid": payout.txid,
                "router_used": payout.router_used.value if payout.router_used else None,
                "created_at": payout.created_at.isoformat(),
                "processed_at": payout.processed_at.isoformat() if payout.processed_at else None,
                "confirmed_at": payout.confirmed_at.isoformat() if payout.confirmed_at else None,
                "error_message": payout.error_message,
                "retry_count": payout.request.retry_count
            }
            
        except Exception as e:
            logger.error(f"Error getting payout status: {e}")
            return None
    
    async def list_payouts(self, status: Optional[str] = None, 
                          router_type: Optional[PayoutRouterType] = None,
                          limit: int = 100) -> List[Dict[str, Any]]:
        """List payouts with optional filters"""
        try:
            all_payouts = {**self.pending_payouts, **self.processed_payouts}
            
            filtered_payouts = {}
            for payout_id, payout in all_payouts.items():
                if status and payout.status != status:
                    continue
                if router_type and payout.request.router_type != router_type:
                    continue
                filtered_payouts[payout_id] = payout
            
            # Sort by creation time (newest first)
            sorted_payouts = sorted(filtered_payouts.items(), 
                                  key=lambda x: x[1].created_at, reverse=True)
            
            # Limit results
            limited_payouts = sorted_payouts[:limit]
            
            payouts_list = []
            for payout_id, payout in limited_payouts:
                payouts_list.append({
                    "payout_id": payout.payout_id,
                    "recipient_address": payout.request.recipient_address,
                    "amount_usdt": payout.request.amount_usdt,
                    "reason": payout.request.reason,
                    "router_type": payout.request.router_type.value,
                    "priority": payout.request.priority.value,
                    "status": payout.status,
                    "txid": payout.txid,
                    "created_at": payout.created_at.isoformat(),
                    "confirmed_at": payout.confirmed_at.isoformat() if payout.confirmed_at else None,
                    "error_message": payout.error_message
                })
            
            return payouts_list
            
        except Exception as e:
            logger.error(f"Error listing payouts: {e}")
            return []
    
    async def get_payout_stats(self) -> Dict[str, Any]:
        """Get payout statistics"""
        try:
            all_payouts = {**self.pending_payouts, **self.processed_payouts}
            
            total_payouts = len(all_payouts)
            pending_payouts = len(self.pending_payouts)
            processed_payouts = len(self.processed_payouts)
            confirmed_payouts = sum(1 for p in all_payouts.values() if p.status == "confirmed")
            failed_payouts = sum(1 for p in all_payouts.values() if p.status == "failed")
            
            total_amount = sum(p.request.amount_usdt for p in all_payouts.values())
            confirmed_amount = sum(p.request.amount_usdt for p in all_payouts.values() if p.status == "confirmed")
            
            # Queue statistics
            queue_stats = {
                "urgent": len(self.urgent_queue),
                "high": len(self.high_queue),
                "normal": len(self.normal_queue),
                "low": len(self.low_queue)
            }
            
            # Router statistics
            v0_payouts = sum(1 for p in all_payouts.values() if p.request.router_type == PayoutRouterType.V0)
            kyc_payouts = sum(1 for p in all_payouts.values() if p.request.router_type == PayoutRouterType.KYC)
            
            # Daily/hourly statistics
            today = datetime.now().date().isoformat()
            current_hour = datetime.now().strftime("%Y-%m-%d_%H")
            daily_amount = self.daily_payouts.get(today, 0.0)
            hourly_amount = self.hourly_payouts.get(current_hour, 0.0)
            
            return {
                "total_payouts": total_payouts,
                "pending_payouts": pending_payouts,
                "processed_payouts": processed_payouts,
                "confirmed_payouts": confirmed_payouts,
                "failed_payouts": failed_payouts,
                "total_amount_usdt": total_amount,
                "confirmed_amount_usdt": confirmed_amount,
                "daily_amount_usdt": daily_amount,
                "hourly_amount_usdt": hourly_amount,
                "daily_limit_usdt": self.config.daily_payout_limit_usdt,
                "hourly_limit_usdt": self.config.hourly_payout_limit_usdt,
                "queue_stats": queue_stats,
                "router_stats": {
                    "v0_payouts": v0_payouts,
                    "kyc_payouts": kyc_payouts
                },
                "circuit_breaker": {
                    "open": self.circuit_breaker_open,
                    "failures": self.circuit_breaker_failures,
                    "last_failure": self.circuit_breaker_last_failure.isoformat() if self.circuit_breaker_last_failure else None
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting payout stats: {e}")
            return {"error": str(e)}
    
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

# Global instance
payout_manager = PayoutManager()

# Convenience functions for external use
async def create_payout(request: UnifiedPayoutRequestModel) -> UnifiedPayoutResponseModel:
    """Create a new unified payout"""
    return await payout_manager.create_payout(request)

async def get_payout_status(payout_id: str) -> Optional[Dict[str, Any]]:
    """Get payout status"""
    return await payout_manager.get_payout_status(payout_id)

async def list_payouts(status: Optional[str] = None, 
                      router_type: Optional[PayoutRouterType] = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
    """List payouts"""
    return await payout_manager.list_payouts(status, router_type, limit)

async def get_payout_stats() -> Dict[str, Any]:
    """Get payout statistics"""
    return await payout_manager.get_payout_stats()

if __name__ == "__main__":
    # Lucid RDP Payment Systems Integration
    async def main():
        """
        Lucid RDP PayoutManager Integration Examples
        
        This demonstrates proper usage within the Lucid RDP ecosystem:
        - Node worker session payouts via V0 router
        - KYC-gated node operator rewards via KYC router
        - Integration with node economy and trust scoring
        """
        
        # Example 1: Node worker session payout (V0 router)
        # This would be called from node/worker/node_worker.py after session completion
        session_payout_request = UnifiedPayoutRequestModel(
            recipient_address=os.getenv("NODE_WORKER_WALLET_ADDRESS", ""),
            amount_usdt=float(os.getenv("SESSION_REWARD_USDT", "5.0")),
            reason="session_relay",
            router_type=PayoutRouterType.V0,
            priority=PayoutPriority.NORMAL,
            batch_type=PayoutBatchType.IMMEDIATE,
            session_id=os.getenv("CURRENT_SESSION_ID", "session_lucid_rdp_001"),
            node_id=os.getenv("NODE_ID", "lucid_node_001"),
            work_credits=float(os.getenv("SESSION_WORK_CREDITS", "10.0"))
        )
        
        # Example 2: KYC node operator reward (KYC router)
        # This would be called from node/economy/node_economy.py for verified operators
        node_reward_request = UnifiedPayoutRequestModel(
            recipient_address=os.getenv("NODE_OPERATOR_WALLET_ADDRESS", ""),
            amount_usdt=float(os.getenv("NODE_REWARD_USDT", "50.0")),
            reason="node_operation",
            router_type=PayoutRouterType.KYC,
            priority=PayoutPriority.HIGH,
            batch_type=PayoutBatchType.HOURLY,
            node_id=os.getenv("NODE_ID", "lucid_node_001"),
            kyc_hash=os.getenv("NODE_KYC_HASH", ""),
            compliance_signature={
                "signature": os.getenv("COMPLIANCE_SIGNATURE", ""),
                "signed_by": os.getenv("COMPLIANCE_AUTHORITY", "lucid_compliance"),
                "signature_timestamp": datetime.now().isoformat(),
                "signature_valid_until": (datetime.now() + timedelta(hours=24)).isoformat(),
                "compliance_level": os.getenv("NODE_COMPLIANCE_LEVEL", "ENHANCED")
            },
            work_credits=float(os.getenv("NODE_WORK_CREDITS", "100.0"))
        )
        
        # Example 3: Governance participation reward
        governance_reward_request = UnifiedPayoutRequestModel(
            recipient_address=os.getenv("GOVERNANCE_PARTICIPANT_ADDRESS", ""),
            amount_usdt=float(os.getenv("GOVERNANCE_REWARD_USDT", "25.0")),
            reason="governance_participation",
            router_type=PayoutRouterType.V0,
            priority=PayoutPriority.NORMAL,
            batch_type=PayoutBatchType.DAILY,
            custom_data={
                "governance_proposal_id": os.getenv("PROPOSAL_ID", ""),
                "vote_weight": float(os.getenv("VOTE_WEIGHT", "1.0")),
                "consensus_contribution": float(os.getenv("CONSENSUS_CONTRIBUTION", "5.0"))
            }
        )
        
        try:
            # Process session payout (immediate processing)
            if session_payout_request.recipient_address:
                session_response = await create_payout(session_payout_request)
                logger.info(f"Session payout created: {session_response.payout_id}")
                
                # Monitor payout status
                payout_status = await get_payout_status(session_response.payout_id)
                logger.info(f"Session payout status: {payout_status['status']}")
            
            # Process node operator reward (batch processing)
            if node_reward_request.recipient_address and node_reward_request.kyc_hash:
                node_response = await create_payout(node_reward_request)
                logger.info(f"Node operator reward queued: {node_response.payout_id}")
            
            # Process governance reward (daily batch)
            if governance_reward_request.recipient_address:
                governance_response = await create_payout(governance_reward_request)
                logger.info(f"Governance reward queued: {governance_response.payout_id}")
            
            # Get system statistics for monitoring
            system_stats = await get_payout_stats()
            logger.info(f"Payment system stats: {system_stats['total_payouts']} total payouts")
            logger.info(f"Daily volume: {system_stats['daily_amount_usdt']:.2f} USDT")
            
            # List recent payouts for audit trail
            recent_payouts = await list_payouts(limit=20)
            logger.info(f"Recent payouts: {len(recent_payouts)} transactions")
            
        except Exception as e:
            logger.error(f"Payout processing error: {e}")
            # In production, this would trigger alerting and fallback mechanisms
    
    # Integration points for Lucid RDP components:
    """
    Integration with other Lucid RDP components:
    
    1. node/worker/node_worker.py:
       - Call create_payout() after successful RDP session completion
       - Use session metrics for work_credits calculation
       
    2. node/economy/node_economy.py:
       - Call create_payout() for node operator rewards
       - Integrate with trust scoring and performance metrics
       
    3. blockchain/core/blockchain_engine.py:
       - Use payout_manager for USDT distribution via TronNodeSystem
       - Coordinate with PoOT consensus rewards
       
    4. user_content/wallet/user_wallet.py:
       - Query payout status for user payment confirmations
       - Display payout history in user interface
    """
    
    asyncio.run(main())
