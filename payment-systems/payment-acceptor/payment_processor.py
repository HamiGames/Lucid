"""
Payment Processor Module for Lucid Network
Handles payment processing, routing, and settlement
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from uuid import uuid4

from pydantic import BaseModel, Field

# Import existing payment system components
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tron_node.tron_client import TronService
from tron_node.usdt_trc20 import USDTTRC20Client, TransferType, TransactionStatus
from tron_node.payout_manager import PayoutManager, UnifiedPayoutRequestModel, PayoutRouterType, PayoutPriority
from wallet.integration_manager import WalletIntegrationManager, WalletType, WalletRole, TransactionRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProcessingStatus(str, Enum):
    """Payment processing status"""
    QUEUED = "queued"
    PROCESSING = "processing"
    ROUTED = "routed"
    SETTLED = "settled"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ProcessingType(str, Enum):
    """Payment processing types"""
    IMMEDIATE = "immediate"          # Immediate processing
    BATCH = "batch"                 # Batch processing
    SCHEDULED = "scheduled"         # Scheduled processing
    CONDITIONAL = "conditional"     # Conditional processing

class SettlementType(str, Enum):
    """Settlement types"""
    INTERNAL = "internal"           # Internal settlement
    EXTERNAL = "external"           # External settlement
    HYBRID = "hybrid"              # Hybrid settlement

@dataclass
class ProcessingRule:
    """Payment processing rule"""
    rule_id: str
    name: str
    conditions: Dict[str, Any]
    actions: List[Dict[str, Any]]
    priority: int = 0
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class ProcessingJob:
    """Payment processing job"""
    job_id: str
    payment_id: str
    processing_type: ProcessingType
    settlement_type: SettlementType
    amount: float
    token_type: str
    source_address: str
    destination_address: str
    routing_path: List[str] = field(default_factory=list)
    processing_rules: List[str] = field(default_factory=list)
    status: ProcessingStatus = ProcessingStatus.QUEUED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class SettlementRecord:
    """Settlement record"""
    settlement_id: str
    job_id: str
    payment_id: str
    amount: float
    token_type: str
    from_address: str
    to_address: str
    txid: Optional[str] = None
    block_height: Optional[int] = None
    gas_used: Optional[int] = None
    energy_used: Optional[int] = None
    fee_paid: Optional[float] = None
    settled_at: Optional[datetime] = None
    status: str = "pending"

class ProcessingJobModel(BaseModel):
    """Pydantic model for processing jobs"""
    payment_id: str = Field(..., description="Payment ID to process")
    processing_type: ProcessingType = Field(..., description="Processing type")
    settlement_type: SettlementType = Field(..., description="Settlement type")
    amount: float = Field(..., gt=0, description="Amount to process")
    token_type: str = Field(..., description="Token type")
    source_address: str = Field(..., description="Source address")
    destination_address: str = Field(..., description="Destination address")
    routing_path: Optional[List[str]] = Field(default=None, description="Routing path")
    processing_rules: Optional[List[str]] = Field(default=None, description="Processing rules")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

class ProcessingJobResponseModel(BaseModel):
    """Pydantic model for processing job responses"""
    job_id: str
    payment_id: str
    status: str
    message: str
    processing_type: str
    settlement_type: str
    amount: float
    token_type: str
    created_at: str
    estimated_completion: Optional[str] = None

class PaymentProcessor:
    """Payment processing and settlement system"""
    
    def __init__(self):
        self.processing_jobs: Dict[str, ProcessingJob] = {}
        self.settlement_records: Dict[str, SettlementRecord] = {}
        self.processing_rules: Dict[str, ProcessingRule] = {}
        self.processing_queue: List[str] = []
        self.active_jobs: Dict[str, ProcessingJob] = {}
        
        # Initialize services
        self.tron_service = TronService()
        self.usdt_client = USDTTRC20Client()
        self.payout_manager = PayoutManager()
        self.wallet_manager = WalletIntegrationManager()
        
        # Configuration
        self.config = {
            "max_concurrent_jobs": 20,
            "processing_timeout_seconds": 300,
            "settlement_timeout_seconds": 600,
            "batch_size": 50,
            "batch_interval_seconds": 60,
            "retry_attempts": 3,
            "retry_delay_seconds": 30,
            "default_gas_limit": 1000000,
            "default_energy_limit": 10000000,
            "fee_limit_trx": 1.0
        }
        
        # Initialize default processing rules
        self._initialize_default_rules()
        
        # Start background tasks
        asyncio.create_task(self._process_job_queue())
        asyncio.create_task(self._monitor_active_jobs())
        asyncio.create_task(self._process_batch_settlements())
        asyncio.create_task(self._cleanup_completed_jobs())
        
        logger.info("PaymentProcessor initialized")

    def _initialize_default_rules(self):
        """Initialize default processing rules"""
        # Rule 1: High amount processing
        high_amount_rule = ProcessingRule(
            rule_id="high_amount_rule",
            name="High Amount Processing",
            conditions={
                "amount_greater_than": 1000.0,
                "token_type": "USDT"
            },
            actions=[
                {"action": "require_manual_approval"},
                {"action": "use_kyc_router"},
                {"action": "set_priority", "value": "high"}
            ],
            priority=100
        )
        self.processing_rules["high_amount_rule"] = high_amount_rule
        
        # Rule 2: Node operator payments
        node_operator_rule = ProcessingRule(
            rule_id="node_operator_rule",
            name="Node Operator Payments",
            conditions={
                "destination_type": "node_operator",
                "payment_type": "node_registration"
            },
            actions=[
                {"action": "use_kyc_router"},
                {"action": "require_kyc_verification"},
                {"action": "set_batch_processing"}
            ],
            priority=80
        )
        self.processing_rules["node_operator_rule"] = node_operator_rule
        
        # Rule 3: Session payments
        session_rule = ProcessingRule(
            rule_id="session_rule",
            name="Session Payments",
            conditions={
                "payment_type": "session_payment",
                "amount_less_than": 100.0
            },
            actions=[
                {"action": "use_v0_router"},
                {"action": "immediate_processing"},
                {"action": "set_priority", "value": "normal"}
            ],
            priority=60
        )
        self.processing_rules["session_rule"] = session_rule
        
        # Rule 4: Emergency processing
        emergency_rule = ProcessingRule(
            rule_id="emergency_rule",
            name="Emergency Processing",
            conditions={
                "priority": "urgent",
                "payment_type": "emergency"
            },
            actions=[
                {"action": "immediate_processing"},
                {"action": "bypass_validation"},
                {"action": "use_any_router"},
                {"action": "set_priority", "value": "urgent"}
            ],
            priority=200
        )
        self.processing_rules["emergency_rule"] = emergency_rule

    async def create_processing_job(self, request: ProcessingJobModel) -> ProcessingJobResponseModel:
        """Create a new payment processing job"""
        try:
            # Generate unique job ID
            job_id = f"JOB_{uuid4().hex[:16].upper()}"
            
            # Create processing job
            job = ProcessingJob(
                job_id=job_id,
                payment_id=request.payment_id,
                processing_type=request.processing_type,
                settlement_type=request.settlement_type,
                amount=request.amount,
                token_type=request.token_type,
                source_address=request.source_address,
                destination_address=request.destination_address,
                routing_path=request.routing_path or [],
                processing_rules=request.processing_rules or [],
                metadata=request.metadata
            )
            
            # Apply processing rules
            await self._apply_processing_rules(job)
            
            # Store job
            self.processing_jobs[job_id] = job
            
            # Add to processing queue
            if job.processing_type == ProcessingType.IMMEDIATE:
                self.processing_queue.insert(0, job_id)  # High priority
            else:
                self.processing_queue.append(job_id)
            
            # Log job creation
            await self._log_processing_event(job_id, "created", {
                "payment_id": request.payment_id,
                "amount": request.amount,
                "type": request.processing_type.value
            })
            
            return ProcessingJobResponseModel(
                job_id=job_id,
                payment_id=request.payment_id,
                status=job.status.value,
                message="Processing job created successfully",
                processing_type=job.processing_type.value,
                settlement_type=job.settlement_type.value,
                amount=request.amount,
                token_type=request.token_type,
                created_at=job.created_at.isoformat(),
                estimated_completion=self._estimate_completion_time(job)
            )
            
        except Exception as e:
            logger.error(f"Error creating processing job: {e}")
            return ProcessingJobResponseModel(
                job_id="",
                payment_id=request.payment_id,
                status="failed",
                message=f"Failed to create processing job: {str(e)}",
                processing_type=request.processing_type.value,
                settlement_type=request.settlement_type.value,
                amount=request.amount,
                token_type=request.token_type,
                created_at=datetime.now(timezone.utc).isoformat()
            )

    async def _apply_processing_rules(self, job: ProcessingJob):
        """Apply processing rules to job"""
        for rule_id, rule in self.processing_rules.items():
            if not rule.enabled:
                continue
            
            if await self._evaluate_rule_conditions(rule.conditions, job):
                # Apply rule actions
                for action in rule.actions:
                    await self._apply_rule_action(action, job)
                
                # Add rule to job
                if rule_id not in job.processing_rules:
                    job.processing_rules.append(rule_id)

    async def _evaluate_rule_conditions(self, conditions: Dict[str, Any], job: ProcessingJob) -> bool:
        """Evaluate rule conditions"""
        try:
            # Amount conditions
            if "amount_greater_than" in conditions:
                if job.amount <= conditions["amount_greater_than"]:
                    return False
            
            if "amount_less_than" in conditions:
                if job.amount >= conditions["amount_less_than"]:
                    return False
            
            # Token type conditions
            if "token_type" in conditions:
                if job.token_type != conditions["token_type"]:
                    return False
            
            # Payment type conditions (would need to be passed from payment request)
            if "payment_type" in conditions:
                # This would require access to the original payment request
                pass
            
            # Priority conditions
            if "priority" in conditions:
                # This would require priority information
                pass
            
            return True
            
        except Exception as e:
            logger.error(f"Error evaluating rule conditions: {e}")
            return False

    async def _apply_rule_action(self, action: Dict[str, Any], job: ProcessingJob):
        """Apply rule action to job"""
        try:
            action_type = action["action"]
            
            if action_type == "require_manual_approval":
                job.metadata = job.metadata or {}
                job.metadata["requires_approval"] = True
            
            elif action_type == "use_kyc_router":
                job.metadata = job.metadata or {}
                job.metadata["router_type"] = "kyc"
            
            elif action_type == "use_v0_router":
                job.metadata = job.metadata or {}
                job.metadata["router_type"] = "v0"
            
            elif action_type == "require_kyc_verification":
                job.metadata = job.metadata or {}
                job.metadata["requires_kyc"] = True
            
            elif action_type == "set_batch_processing":
                job.processing_type = ProcessingType.BATCH
            
            elif action_type == "immediate_processing":
                job.processing_type = ProcessingType.IMMEDIATE
            
            elif action_type == "bypass_validation":
                job.metadata = job.metadata or {}
                job.metadata["bypass_validation"] = True
            
            elif action_type == "use_any_router":
                job.metadata = job.metadata or {}
                job.metadata["router_type"] = "any"
            
            elif action_type == "set_priority":
                job.metadata = job.metadata or {}
                job.metadata["priority"] = action.get("value", "normal")
                
        except Exception as e:
            logger.error(f"Error applying rule action: {e}")

    def _estimate_completion_time(self, job: ProcessingJob) -> str:
        """Estimate job completion time"""
        if job.processing_type == ProcessingType.IMMEDIATE:
            return "1-2 minutes"
        elif job.processing_type == ProcessingType.BATCH:
            return "5-10 minutes"
        elif job.processing_type == ProcessingType.SCHEDULED:
            return "As scheduled"
        else:
            return "5-15 minutes"

    async def _process_job_queue(self):
        """Process job queue"""
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # Process jobs if we have capacity
                while (len(self.active_jobs) < self.config["max_concurrent_jobs"] and 
                       self.processing_queue):
                    
                    job_id = self.processing_queue.pop(0)
                    if job_id in self.processing_jobs:
                        job = self.processing_jobs[job_id]
                        
                        if job.status == ProcessingStatus.QUEUED:
                            # Start processing job
                            asyncio.create_task(self._process_job(job_id))
                            
            except Exception as e:
                logger.error(f"Error in job queue processing: {e}")

    async def _process_job(self, job_id: str):
        """Process individual job"""
        try:
            job = self.processing_jobs[job_id]
            job.status = ProcessingStatus.PROCESSING
            job.started_at = datetime.now(timezone.utc)
            
            # Add to active jobs
            self.active_jobs[job_id] = job
            
            await self._log_processing_event(job_id, "started", {})
            
            # Check if manual approval is required
            if job.metadata and job.metadata.get("requires_approval"):
                job.status = ProcessingStatus.QUEUED
                await self._log_processing_event(job_id, "awaiting_approval", {})
                return
            
            # Process based on type
            if job.processing_type == ProcessingType.IMMEDIATE:
                await self._process_immediate_job(job)
            elif job.processing_type == ProcessingType.BATCH:
                await self._process_batch_job(job)
            elif job.processing_type == ProcessingType.SCHEDULED:
                await self._process_scheduled_job(job)
            else:
                await self._process_conditional_job(job)
            
            # Remove from active jobs
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
            
            job.completed_at = datetime.now(timezone.utc)
            
            await self._log_processing_event(job_id, "completed", {
                "status": job.status.value
            })
            
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            
            if job_id in self.processing_jobs:
                job = self.processing_jobs[job_id]
                job.status = ProcessingStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.now(timezone.utc)
            
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
            
            await self._log_processing_event(job_id, "failed", {
                "error": str(e)
            })

    async def _process_immediate_job(self, job: ProcessingJob):
        """Process immediate job"""
        try:
            # Determine routing
            router_type = await self._determine_router_type(job)
            
            # Execute settlement
            settlement_id = await self._execute_settlement(job, router_type)
            
            if settlement_id:
                job.status = ProcessingStatus.SETTLED
                job.routing_path.append(settlement_id)
            else:
                job.status = ProcessingStatus.FAILED
                job.error_message = "Settlement failed"
                
        except Exception as e:
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
            raise

    async def _process_batch_job(self, job: ProcessingJob):
        """Process batch job"""
        try:
            # Add to batch queue for later processing
            job.status = ProcessingStatus.QUEUED
            job.metadata = job.metadata or {}
            job.metadata["batch_queued"] = True
            
            await self._log_processing_event(job.job_id, "batch_queued", {})
            
        except Exception as e:
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
            raise

    async def _process_scheduled_job(self, job: ProcessingJob):
        """Process scheduled job"""
        try:
            # Check if it's time to process
            schedule_time = job.metadata.get("schedule_time") if job.metadata else None
            
            if schedule_time and datetime.now(timezone.utc) >= datetime.fromisoformat(schedule_time):
                await self._process_immediate_job(job)
            else:
                # Reschedule
                job.status = ProcessingStatus.QUEUED
                self.processing_queue.append(job.job_id)
                
        except Exception as e:
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
            raise

    async def _process_conditional_job(self, job: ProcessingJob):
        """Process conditional job"""
        try:
            # Check conditions
            conditions_met = await self._check_conditional_requirements(job)
            
            if conditions_met:
                await self._process_immediate_job(job)
            else:
                # Reschedule
                job.status = ProcessingStatus.QUEUED
                self.processing_queue.append(job.job_id)
                
        except Exception as e:
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
            raise

    async def _determine_router_type(self, job: ProcessingJob) -> str:
        """Determine router type for job"""
        if job.metadata and "router_type" in job.metadata:
            return job.metadata["router_type"]
        
        # Default logic based on amount and type
        if job.amount > 1000.0:
            return "kyc"
        else:
            return "v0"

    async def _execute_settlement(self, job: ProcessingJob, router_type: str) -> Optional[str]:
        """Execute settlement for job"""
        try:
            # Generate settlement ID
            settlement_id = f"SETTLE_{uuid4().hex[:16].upper()}"
            
            # Create settlement record
            settlement = SettlementRecord(
                settlement_id=settlement_id,
                job_id=job.job_id,
                payment_id=job.payment_id,
                amount=job.amount,
                token_type=job.token_type,
                from_address=job.source_address,
                to_address=job.destination_address
            )
            
            self.settlement_records[settlement_id] = settlement
            
            # Execute based on settlement type
            if job.settlement_type == SettlementType.INTERNAL:
                txid = await self._execute_internal_settlement(job, router_type)
            elif job.settlement_type == SettlementType.EXTERNAL:
                txid = await self._execute_external_settlement(job, router_type)
            else:
                txid = await self._execute_hybrid_settlement(job, router_type)
            
            if txid:
                settlement.txid = txid
                settlement.status = "confirmed"
                settlement.settled_at = datetime.now(timezone.utc)
                
                # Update job status
                job.status = ProcessingStatus.SETTLED
                
                await self._log_processing_event(job.job_id, "settled", {
                    "settlement_id": settlement_id,
                    "txid": txid
                })
                
                return settlement_id
            else:
                settlement.status = "failed"
                return None
                
        except Exception as e:
            logger.error(f"Error executing settlement for job {job.job_id}: {e}")
            return None

    async def _execute_internal_settlement(self, job: ProcessingJob, router_type: str) -> Optional[str]:
        """Execute internal settlement"""
        try:
            # Use payout manager for internal settlements
            payout_request = UnifiedPayoutRequestModel(
                recipient_address=job.destination_address,
                amount_usdt=job.amount,
                reason="internal_settlement",
                router_type=PayoutRouterType.KYC if router_type == "kyc" else PayoutRouterType.V0,
                priority=PayoutPriority.HIGH if job.metadata and job.metadata.get("priority") == "urgent" else PayoutPriority.NORMAL,
                session_id=job.metadata.get("session_id") if job.metadata else None,
                node_id=job.metadata.get("node_id") if job.metadata else None
            )
            
            response = await self.payout_manager.create_payout(payout_request)
            
            if response.status == "success":
                return response.txid
            else:
                logger.error(f"Payout failed: {response.message}")
                return None
                
        except Exception as e:
            logger.error(f"Error in internal settlement: {e}")
            return None

    async def _execute_external_settlement(self, job: ProcessingJob, router_type: str) -> Optional[str]:
        """Execute external settlement"""
        try:
            # Use wallet manager for external settlements
            transaction_request = TransactionRequest(
                wallet_id=job.metadata.get("wallet_id") if job.metadata else "default",
                transaction_type="transfer",
                recipient_address=job.destination_address,
                amount=job.amount,
                token_type=job.token_type,
                fee_limit=self.config["fee_limit_trx"] * 1000000,  # Convert to sun
                energy_limit=self.config["default_energy_limit"]
            )
            
            result = await self.wallet_manager.execute_transaction(transaction_request)
            
            if result.status == "confirmed":
                return result.txid
            else:
                logger.error(f"External settlement failed: {result.error_message}")
                return None
                
        except Exception as e:
            logger.error(f"Error in external settlement: {e}")
            return None

    async def _execute_hybrid_settlement(self, job: ProcessingJob, router_type: str) -> Optional[str]:
        """Execute hybrid settlement"""
        try:
            # Try internal first, fallback to external
            txid = await self._execute_internal_settlement(job, router_type)
            
            if not txid:
                txid = await self._execute_external_settlement(job, router_type)
            
            return txid
            
        except Exception as e:
            logger.error(f"Error in hybrid settlement: {e}")
            return None

    async def _check_conditional_requirements(self, job: ProcessingJob) -> bool:
        """Check conditional requirements for job"""
        try:
            # This would implement conditional logic based on job metadata
            # For now, return True to process immediately
            return True
            
        except Exception as e:
            logger.error(f"Error checking conditional requirements: {e}")
            return False

    async def _process_batch_settlements(self):
        """Process batch settlements"""
        while True:
            try:
                await asyncio.sleep(self.config["batch_interval_seconds"])
                
                # Find batch jobs
                batch_jobs = [
                    job for job in self.processing_jobs.values()
                    if (job.status == ProcessingStatus.QUEUED and 
                        job.metadata and 
                        job.metadata.get("batch_queued"))
                ]
                
                if batch_jobs:
                    # Process batch
                    await self._process_batch(batch_jobs[:self.config["batch_size"]])
                    
            except Exception as e:
                logger.error(f"Error in batch settlement processing: {e}")

    async def _process_batch(self, jobs: List[ProcessingJob]):
        """Process batch of jobs"""
        try:
            for job in jobs:
                job.status = ProcessingStatus.PROCESSING
                job.started_at = datetime.now(timezone.utc)
                
                # Process job
                await self._process_immediate_job(job)
                
                job.completed_at = datetime.now(timezone.utc)
                
        except Exception as e:
            logger.error(f"Error processing batch: {e}")

    async def _monitor_active_jobs(self):
        """Monitor active jobs for timeouts"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                current_time = datetime.now(timezone.utc)
                timeout_seconds = self.config["processing_timeout_seconds"]
                
                for job_id, job in list(self.active_jobs.items()):
                    if (job.started_at and 
                        (current_time - job.started_at).total_seconds() > timeout_seconds):
                        
                        # Timeout job
                        job.status = ProcessingStatus.FAILED
                        job.error_message = "Processing timeout"
                        job.completed_at = current_time
                        
                        del self.active_jobs[job_id]
                        
                        await self._log_processing_event(job_id, "timeout", {})
                        
            except Exception as e:
                logger.error(f"Error monitoring active jobs: {e}")

    async def _cleanup_completed_jobs(self):
        """Cleanup completed jobs"""
        while True:
            try:
                await asyncio.sleep(3600)  # Cleanup every hour
                
                current_time = datetime.now(timezone.utc)
                completed_jobs = []
                
                for job_id, job in self.processing_jobs.items():
                    if (job.status in [ProcessingStatus.SETTLED, ProcessingStatus.FAILED, ProcessingStatus.CANCELLED] and
                        job.completed_at and
                        (current_time - job.completed_at).days > 7):
                        completed_jobs.append(job_id)
                
                for job_id in completed_jobs:
                    del self.processing_jobs[job_id]
                    # Also cleanup related settlement records
                    for settlement_id, settlement in list(self.settlement_records.items()):
                        if settlement.job_id == job_id:
                            del self.settlement_records[settlement_id]
                
                if completed_jobs:
                    logger.info(f"Cleaned up {len(completed_jobs)} completed jobs")
                    
            except Exception as e:
                logger.error(f"Error in job cleanup: {e}")

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status"""
        if job_id not in self.processing_jobs:
            return None
        
        job = self.processing_jobs[job_id]
        settlement = None
        
        # Find related settlement
        for settlement_record in self.settlement_records.values():
            if settlement_record.job_id == job_id:
                settlement = settlement_record
                break
        
        return {
            "job_id": job_id,
            "payment_id": job.payment_id,
            "status": job.status.value,
            "processing_type": job.processing_type.value,
            "settlement_type": job.settlement_type.value,
            "amount": job.amount,
            "token_type": job.token_type,
            "source_address": job.source_address,
            "destination_address": job.destination_address,
            "routing_path": job.routing_path,
            "processing_rules": job.processing_rules,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error_message": job.error_message,
            "settlement_id": settlement.settlement_id if settlement else None,
            "txid": settlement.txid if settlement else None,
            "settled_at": settlement.settled_at.isoformat() if settlement and settlement.settled_at else None
        }

    async def list_jobs(self, status: Optional[ProcessingStatus] = None, 
                       processing_type: Optional[ProcessingType] = None,
                       limit: int = 100) -> List[Dict[str, Any]]:
        """List processing jobs"""
        jobs = []
        
        for job_id, job in self.processing_jobs.items():
            if status and job.status != status:
                continue
            if processing_type and job.processing_type != processing_type:
                continue
            
            job_data = await self.get_job_status(job_id)
            if job_data:
                jobs.append(job_data)
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x["created_at"], reverse=True)
        
        return jobs[:limit]

    async def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        total_jobs = len(self.processing_jobs)
        status_counts = {}
        type_counts = {}
        total_amount_processed = 0.0
        
        for job in self.processing_jobs.values():
            # Status counts
            status = job.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
            
            # Type counts
            processing_type = job.processing_type.value
            type_counts[processing_type] = type_counts.get(processing_type, 0) + 1
            
            # Total amount processed
            if job.status == ProcessingStatus.SETTLED:
                total_amount_processed += job.amount
        
        return {
            "total_jobs": total_jobs,
            "active_jobs": len(self.active_jobs),
            "queued_jobs": len(self.processing_queue),
            "status_breakdown": status_counts,
            "type_breakdown": type_counts,
            "total_amount_processed": total_amount_processed,
            "total_settlements": len(self.settlement_records),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def _log_processing_event(self, job_id: str, event_type: str, data: Dict[str, Any]):
        """Log processing event"""
        try:
            log_data = {
                "job_id": job_id,
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data
            }
            
            logger.info(f"Processing Event: {json.dumps(log_data)}")
            
        except Exception as e:
            logger.error(f"Error logging processing event: {e}")

# Global instance
payment_processor = PaymentProcessor()

# Public API functions
async def create_processing_job(request: ProcessingJobModel) -> ProcessingJobResponseModel:
    """Create a new processing job"""
    return await payment_processor.create_processing_job(request)

async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job status"""
    return await payment_processor.get_job_status(job_id)

async def list_jobs(status: Optional[ProcessingStatus] = None, 
                   processing_type: Optional[ProcessingType] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
    """List processing jobs"""
    return await payment_processor.list_jobs(status, processing_type, limit)

async def get_processing_statistics() -> Dict[str, Any]:
    """Get processing statistics"""
    return await payment_processor.get_processing_statistics()

async def main():
    """Main function for testing"""
    # Create a test processing job
    request = ProcessingJobModel(
        payment_id="PAY_TEST123",
        processing_type=ProcessingType.IMMEDIATE,
        settlement_type=SettlementType.INTERNAL,
        amount=10.0,
        token_type="USDT",
        source_address="TSourceAddress1234567890123456789012345",
        destination_address="TDestAddress1234567890123456789012345"
    )
    
    response = await create_processing_job(request)
    print(f"Processing job created: {response}")
    
    # Get job status
    status = await get_job_status(response.job_id)
    print(f"Job status: {status}")
    
    # Get statistics
    stats = await get_processing_statistics()
    print(f"Processing statistics: {stats}")

if __name__ == "__main__":
    asyncio.run(main())
