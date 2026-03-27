# Path: common/governance/param_registry.py
# Lucid RDP Parameter Registry Client
# Implements parameter management for governance-controlled system parameters
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Database integration
try:
    from motor.motor_asyncio import AsyncIOMotorDatabase
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False
    AsyncIOMotorDatabase = None

logger = logging.getLogger(__name__)

# Configuration from environment
PARAM_REGISTRY_DB = os.getenv("PARAM_REGISTRY_DB", "lucid_params")
PARAM_REGISTRY_CONTRACT_ADDRESS = os.getenv("PARAM_REGISTRY_CONTRACT_ADDRESS", "0x0000000000000000000000000000000000000000")
PARAM_UPDATE_DELAY_SECONDS = int(os.getenv("PARAM_UPDATE_DELAY_SECONDS", "3600"))  # 1 hour


class ParameterType(Enum):
    """Types of system parameters"""
    UINT256 = "uint256"
    INT256 = "int256"
    BOOL = "bool"
    ADDRESS = "address"
    BYTES32 = "bytes32"
    STRING = "string"
    ARRAY = "array"
    MAPPING = "mapping"


class ParameterCategory(Enum):
    """Parameter categories"""
    GOVERNANCE = "governance"
    NETWORK = "network"
    SECURITY = "security"
    ECONOMICS = "economics"
    PERFORMANCE = "performance"
    COMPATIBILITY = "compatibility"
    CUSTOM = "custom"


class ParameterStatus(Enum):
    """Parameter status"""
    ACTIVE = "active"
    PENDING_UPDATE = "pending_update"
    DEPRECATED = "deprecated"
    LOCKED = "locked"


class UpdateStatus(Enum):
    """Parameter update status"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class SystemParameter:
    """System parameter definition"""
    param_id: str
    name: str
    description: str
    category: ParameterCategory
    param_type: ParameterType
    current_value: Any
    default_value: Any
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    allowed_values: Optional[List[Any]] = None
    status: ParameterStatus = ParameterStatus.ACTIVE
    is_governance_controlled: bool = True
    update_delay_seconds: int = PARAM_UPDATE_DELAY_SECONDS
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: str = "system"
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParameterUpdate:
    """Parameter update request"""
    update_id: str
    param_id: str
    new_value: Any
    reason: str
    proposer: str
    scheduled_time: Optional[datetime] = None
    status: UpdateStatus = UpdateStatus.PENDING
    executed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParameterEvent:
    """Parameter event"""
    event_id: str
    event_type: str
    param_id: Optional[str] = None
    update_id: Optional[str] = None
    member: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class LucidParameterRegistry:
    """
    Lucid RDP Parameter Registry Client
    
    Implements parameter management with:
    - Parameter definition and validation
    - Update scheduling and execution
    - Version control and history
    - Access control and permissions
    - Change tracking and auditing
    """
    
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        """Initialize Lucid Parameter Registry"""
        self.db = db
        self.parameters: Dict[str, SystemParameter] = {}
        self.updates: Dict[str, ParameterUpdate] = {}
        self.events: List[ParameterEvent] = []
        
        # Initialize default parameters
        self._initialize_default_parameters()
        
        logger.info("Lucid Parameter Registry initialized")
    
    def _initialize_default_parameters(self) -> None:
        """Initialize default system parameters"""
        default_params = [
            SystemParameter(
                param_id="voting_period_days",
                name="Voting Period (Days)",
                description="Number of days for governance voting period",
                category=ParameterCategory.GOVERNANCE,
                param_type=ParameterType.UINT256,
                current_value=3,
                default_value=3,
                min_value=1,
                max_value=30,
                is_governance_controlled=True
            ),
            SystemParameter(
                param_id="quorum_threshold",
                name="Quorum Threshold",
                description="Minimum percentage of total voting power required for quorum",
                category=ParameterCategory.GOVERNANCE,
                param_type=ParameterType.UINT256,
                current_value=10,  # 10%
                default_value=10,
                min_value=1,
                max_value=50,
                is_governance_controlled=True
            ),
            SystemParameter(
                param_id="support_threshold",
                name="Support Threshold",
                description="Minimum percentage of votes required for proposal success",
                category=ParameterCategory.GOVERNANCE,
                param_type=ParameterType.UINT256,
                current_value=50,  # 50%
                default_value=50,
                min_value=25,
                max_value=75,
                is_governance_controlled=True
            ),
            SystemParameter(
                param_id="execution_delay_hours",
                name="Execution Delay (Hours)",
                description="Delay between proposal success and execution",
                category=ParameterCategory.GOVERNANCE,
                param_type=ParameterType.UINT256,
                current_value=24,
                default_value=24,
                min_value=1,
                max_value=168,  # 1 week
                is_governance_controlled=True
            ),
            SystemParameter(
                param_id="max_proposal_count",
                name="Maximum Active Proposals",
                description="Maximum number of active proposals allowed",
                category=ParameterCategory.GOVERNANCE,
                param_type=ParameterType.UINT256,
                current_value=10,
                default_value=10,
                min_value=1,
                max_value=100,
                is_governance_controlled=True
            ),
            SystemParameter(
                param_id="network_timeout_seconds",
                name="Network Timeout (Seconds)",
                description="Default network timeout for RDP connections",
                category=ParameterCategory.NETWORK,
                param_type=ParameterType.UINT256,
                current_value=30,
                default_value=30,
                min_value=5,
                max_value=300,
                is_governance_controlled=False
            ),
            SystemParameter(
                param_id="max_session_duration_hours",
                name="Maximum Session Duration (Hours)",
                description="Maximum allowed RDP session duration",
                category=ParameterCategory.SECURITY,
                param_type=ParameterType.UINT256,
                current_value=8,
                default_value=8,
                min_value=1,
                max_value=24,
                is_governance_controlled=True
            ),
            SystemParameter(
                param_id="enable_emergency_mode",
                name="Emergency Mode",
                description="Enable emergency governance mode",
                category=ParameterCategory.SECURITY,
                param_type=ParameterType.BOOL,
                current_value=False,
                default_value=False,
                is_governance_controlled=True
            ),
            SystemParameter(
                param_id="treasury_address",
                name="Treasury Address",
                description="Address of the governance treasury",
                category=ParameterCategory.ECONOMICS,
                param_type=ParameterType.ADDRESS,
                current_value="0x0000000000000000000000000000000000000000",
                default_value="0x0000000000000000000000000000000000000000",
                is_governance_controlled=True
            ),
            SystemParameter(
                param_id="chunk_size_bytes",
                name="Chunk Size (Bytes)",
                description="Default chunk size for data transfer",
                category=ParameterCategory.PERFORMANCE,
                param_type=ParameterType.UINT256,
                current_value=8388608,  # 8MB
                default_value=8388608,
                min_value=1048576,  # 1MB
                max_value=67108864,  # 64MB
                is_governance_controlled=False
            )
        ]
        
        for param in default_params:
            self.parameters[param.param_id] = param
        
        logger.info(f"Initialized {len(default_params)} default parameters")
    
    async def start(self) -> bool:
        """Start the parameter registry service"""
        try:
            if self.db:
                await self._setup_database_indexes()
                await self._load_parameter_data()
            
            # Start background tasks
            asyncio.create_task(self._process_updates())
            asyncio.create_task(self._cleanup_old_events())
            
            logger.info("Lucid Parameter Registry started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Lucid Parameter Registry: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the parameter registry service"""
        try:
            if self.db:
                await self._save_parameter_data()
            
            logger.info("Lucid Parameter Registry stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping Lucid Parameter Registry: {e}")
            return False
    
    async def get_parameter(self, param_id: str) -> Optional[SystemParameter]:
        """Get parameter by ID"""
        return self.parameters.get(param_id)
    
    async def get_parameter_value(self, param_id: str) -> Optional[Any]:
        """Get current value of a parameter"""
        param = self.parameters.get(param_id)
        return param.current_value if param else None
    
    async def list_parameters(
        self,
        category: Optional[ParameterCategory] = None,
        status: Optional[ParameterStatus] = None,
        governance_controlled: Optional[bool] = None,
        limit: int = 100
    ) -> List[SystemParameter]:
        """List parameters with optional filters"""
        params = list(self.parameters.values())
        
        # Apply filters
        if category:
            params = [p for p in params if p.category == category]
        
        if status:
            params = [p for p in params if p.status == status]
        
        if governance_controlled is not None:
            params = [p for p in params if p.is_governance_controlled == governance_controlled]
        
        # Sort by name
        params.sort(key=lambda p: p.name)
        
        return params[:limit]
    
    async def update_parameter(
        self,
        param_id: str,
        new_value: Any,
        reason: str,
        proposer: str,
        immediate: bool = False
    ) -> str:
        """Update a parameter value"""
        try:
            # Validate parameter
            if param_id not in self.parameters:
                raise ValueError(f"Parameter not found: {param_id}")
            
            param = self.parameters[param_id]
            
            # Check if parameter is locked
            if param.status == ParameterStatus.LOCKED:
                raise ValueError(f"Parameter is locked: {param_id}")
            
            # Validate new value
            if not self._validate_parameter_value(param, new_value):
                raise ValueError(f"Invalid value for parameter {param_id}: {new_value}")
            
            # Check if value is actually different
            if param.current_value == new_value:
                raise ValueError(f"New value is same as current value: {new_value}")
            
            # Generate update ID
            update_id = f"upd_{uuid.uuid4().hex[:8]}"
            
            # Calculate scheduled time
            scheduled_time = None
            if not immediate and param.is_governance_controlled:
                scheduled_time = datetime.now(timezone.utc) + timedelta(seconds=param.update_delay_seconds)
            
            # Create update
            update = ParameterUpdate(
                update_id=update_id,
                param_id=param_id,
                new_value=new_value,
                reason=reason,
                proposer=proposer,
                scheduled_time=scheduled_time,
                status=UpdateStatus.SCHEDULED if scheduled_time else UpdateStatus.PENDING
            )
            
            self.updates[update_id] = update
            
            # Update parameter status
            param.status = ParameterStatus.PENDING_UPDATE
            
            if self.db:
                await self.db.updates.insert_one(update.__dict__)
                await self.db.parameters.replace_one(
                    {"param_id": param_id},
                    param.__dict__
                )
            
            # Create parameter event
            event = ParameterEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                event_type="parameter_update_scheduled",
                param_id=param_id,
                update_id=update_id,
                member=proposer,
                metadata={"new_value": str(new_value), "reason": reason, "immediate": immediate}
            )
            self.events.append(event)
            
            # Execute immediately if requested
            if immediate:
                await self._execute_update(update_id)
            
            logger.info(f"Scheduled parameter update: {param_id} = {new_value} by {proposer}")
            return update_id
            
        except Exception as e:
            logger.error(f"Failed to update parameter: {e}")
            raise
    
    async def execute_update(self, update_id: str) -> bool:
        """Execute a scheduled parameter update"""
        try:
            # Validate update
            if update_id not in self.updates:
                raise ValueError(f"Update not found: {update_id}")
            
            update = self.updates[update_id]
            
            # Check if update can be executed
            if update.status not in [UpdateStatus.PENDING, UpdateStatus.SCHEDULED]:
                raise ValueError(f"Update cannot be executed: {update.status.value}")
            
            # Check if update is ready (if scheduled)
            if update.scheduled_time and datetime.now(timezone.utc) < update.scheduled_time:
                raise ValueError("Update is not yet ready for execution")
            
            return await self._execute_update(update_id)
            
        except Exception as e:
            logger.error(f"Failed to execute update: {e}")
            return False
    
    async def cancel_update(self, update_id: str, canceller: str) -> bool:
        """Cancel a parameter update"""
        try:
            # Validate update
            if update_id not in self.updates:
                raise ValueError(f"Update not found: {update_id}")
            
            update = self.updates[update_id]
            
            # Check if update can be cancelled
            if update.status not in [UpdateStatus.PENDING, UpdateStatus.SCHEDULED]:
                raise ValueError(f"Update cannot be cancelled: {update.status.value}")
            
            # Cancel update
            update.status = UpdateStatus.CANCELLED
            update.cancelled_at = datetime.now(timezone.utc)
            update.cancelled_by = canceller
            
            # Reset parameter status
            param = self.parameters.get(update.param_id)
            if param:
                param.status = ParameterStatus.ACTIVE
            
            if self.db:
                await self.db.updates.replace_one(
                    {"update_id": update_id},
                    update.__dict__
                )
                if param:
                    await self.db.parameters.replace_one(
                        {"param_id": update.param_id},
                        param.__dict__
                    )
            
            # Create parameter event
            event = ParameterEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                event_type="parameter_update_cancelled",
                param_id=update.param_id,
                update_id=update_id,
                member=canceller,
                metadata={"cancellation_time": update.cancelled_at.isoformat()}
            )
            self.events.append(event)
            
            logger.info(f"Cancelled parameter update: {update_id} by {canceller}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel update: {e}")
            return False
    
    async def get_parameter_history(self, param_id: str, limit: int = 50) -> List[ParameterUpdate]:
        """Get parameter update history"""
        updates = [update for update in self.updates.values() if update.param_id == param_id]
        updates.sort(key=lambda u: u.created_at, reverse=True)
        return updates[:limit]
    
    async def get_pending_updates(self) -> List[ParameterUpdate]:
        """Get all pending parameter updates"""
        return [update for update in self.updates.values() if update.status == UpdateStatus.PENDING]
    
    async def get_scheduled_updates(self) -> List[ParameterUpdate]:
        """Get all scheduled parameter updates"""
        return [update for update in self.updates.values() if update.status == UpdateStatus.SCHEDULED]
    
    async def get_parameter_stats(self) -> Dict[str, Any]:
        """Get parameter registry statistics"""
        total_params = len(self.parameters)
        active_params = len([p for p in self.parameters.values() if p.status == ParameterStatus.ACTIVE])
        pending_params = len([p for p in self.parameters.values() if p.status == ParameterStatus.PENDING_UPDATE])
        governance_params = len([p for p in self.parameters.values() if p.is_governance_controlled])
        total_updates = len(self.updates)
        pending_updates = len([u for u in self.updates.values() if u.status == UpdateStatus.PENDING])
        scheduled_updates = len([u for u in self.updates.values() if u.status == UpdateStatus.SCHEDULED])
        executed_updates = len([u for u in self.updates.values() if u.status == UpdateStatus.EXECUTED])
        
        return {
            "total_parameters": total_params,
            "active_parameters": active_params,
            "pending_parameters": pending_params,
            "governance_controlled_parameters": governance_params,
            "total_updates": total_updates,
            "pending_updates": pending_updates,
            "scheduled_updates": scheduled_updates,
            "executed_updates": executed_updates
        }
    
    def _validate_parameter_value(self, param: SystemParameter, value: Any) -> bool:
        """Validate parameter value against constraints"""
        try:
            # Type validation
            if param.param_type == ParameterType.UINT256:
                if not isinstance(value, int) or value < 0:
                    return False
            elif param.param_type == ParameterType.INT256:
                if not isinstance(value, int):
                    return False
            elif param.param_type == ParameterType.BOOL:
                if not isinstance(value, bool):
                    return False
            elif param.param_type == ParameterType.ADDRESS:
                if not isinstance(value, str) or not value.startswith("0x"):
                    return False
            elif param.param_type == ParameterType.STRING:
                if not isinstance(value, str):
                    return False
            
            # Range validation
            if param.min_value is not None and value < param.min_value:
                return False
            
            if param.max_value is not None and value > param.max_value:
                return False
            
            # Allowed values validation
            if param.allowed_values is not None and value not in param.allowed_values:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _execute_update(self, update_id: str) -> bool:
        """Execute a parameter update"""
        try:
            update = self.updates[update_id]
            param = self.parameters[update.param_id]
            
            # Store old value for rollback
            old_value = param.current_value
            
            # Update parameter
            param.current_value = update.new_value
            param.last_updated = datetime.now(timezone.utc)
            param.updated_by = update.proposer
            param.version += 1
            param.status = ParameterStatus.ACTIVE
            
            # Update update status
            update.status = UpdateStatus.EXECUTED
            update.executed_at = datetime.now(timezone.utc)
            
            if self.db:
                await self.db.parameters.replace_one(
                    {"param_id": update.param_id},
                    param.__dict__
                )
                await self.db.updates.replace_one(
                    {"update_id": update_id},
                    update.__dict__
                )
            
            # Create parameter event
            event = ParameterEvent(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                event_type="parameter_updated",
                param_id=update.param_id,
                update_id=update_id,
                member=update.proposer,
                metadata={
                    "old_value": str(old_value),
                    "new_value": str(update.new_value),
                    "version": param.version
                }
            )
            self.events.append(event)
            
            logger.info(f"Executed parameter update: {update.param_id} = {update.new_value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute update: {e}")
            # Mark update as failed
            update.status = UpdateStatus.FAILED
            return False
    
    async def _process_updates(self) -> None:
        """Background task to process parameter updates"""
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                
                # Process scheduled updates that are ready
                for update in self.updates.values():
                    if (update.status == UpdateStatus.SCHEDULED and 
                        update.scheduled_time and 
                        current_time >= update.scheduled_time):
                        await self._execute_update(update.update_id)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error processing updates: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_old_events(self) -> None:
        """Background task to cleanup old events"""
        while True:
            try:
                # Cleanup old events (keep last 1000)
                if len(self.events) > 1000:
                    self.events = self.events[-1000:]
                
                await asyncio.sleep(3600)  # Cleanup every hour
                
            except Exception as e:
                logger.error(f"Error cleaning up old events: {e}")
                await asyncio.sleep(3600)
    
    async def _setup_database_indexes(self) -> None:
        """Setup database indexes for parameter registry"""
        try:
            if not self.db:
                return
            
            # Parameters indexes
            await self.db.parameters.create_index("param_id", unique=True)
            await self.db.parameters.create_index("category")
            await self.db.parameters.create_index("status")
            await self.db.parameters.create_index("is_governance_controlled")
            
            # Updates indexes
            await self.db.updates.create_index("update_id", unique=True)
            await self.db.updates.create_index("param_id")
            await self.db.updates.create_index("status")
            await self.db.updates.create_index("scheduled_time")
            await self.db.updates.create_index("created_at")
            
            logger.info("Database indexes created for parameter registry")
            
        except Exception as e:
            logger.error(f"Failed to setup database indexes: {e}")
    
    async def _load_parameter_data(self) -> None:
        """Load parameter data from database"""
        try:
            if not self.db:
                return
            
            # Load parameters
            params_cursor = self.db.parameters.find({})
            async for param_doc in params_cursor:
                param = SystemParameter(**param_doc)
                self.parameters[param.param_id] = param
            
            # Load updates
            updates_cursor = self.db.updates.find({})
            async for update_doc in updates_cursor:
                update = ParameterUpdate(**update_doc)
                self.updates[update.update_id] = update
            
            logger.info(f"Loaded parameter data: {len(self.parameters)} parameters, {len(self.updates)} updates")
            
        except Exception as e:
            logger.error(f"Failed to load parameter data: {e}")
    
    async def _save_parameter_data(self) -> None:
        """Save parameter data to database"""
        try:
            if not self.db:
                return
            
            # Save parameters
            for param in self.parameters.values():
                await self.db.parameters.replace_one(
                    {"param_id": param.param_id},
                    param.__dict__,
                    upsert=True
                )
            
            # Save updates
            for update in self.updates.values():
                await self.db.updates.replace_one(
                    {"update_id": update.update_id},
                    update.__dict__,
                    upsert=True
                )
            
            logger.info("Saved parameter data to database")
            
        except Exception as e:
            logger.error(f"Failed to save parameter data: {e}")


# Global parameter registry instance
_param_registry: Optional[LucidParameterRegistry] = None


def get_parameter_registry() -> Optional[LucidParameterRegistry]:
    """Get the global parameter registry instance"""
    return _param_registry


def create_parameter_registry(db: Optional[AsyncIOMotorDatabase] = None) -> LucidParameterRegistry:
    """Create and configure parameter registry"""
    global _param_registry
    _param_registry = LucidParameterRegistry(db)
    return _param_registry


async def start_parameter_registry():
    """Start the parameter registry service"""
    global _param_registry
    if _param_registry:
        await _param_registry.start()


async def stop_parameter_registry():
    """Stop the parameter registry service"""
    global _param_registry
    if _param_registry:
        await _param_registry.stop()


# Example usage and testing
async def test_parameter_registry():
    """Test parameter registry functionality"""
    try:
        # Create parameter registry
        registry = create_parameter_registry()
        await registry.start()
        
        # Get a parameter
        voting_period = await registry.get_parameter("voting_period_days")
        print(f"Current voting period: {voting_period.current_value} days")
        
        # Update a parameter
        update_id = await registry.update_parameter(
            param_id="voting_period_days",
            new_value=5,
            reason="Increase voting period for better participation",
            proposer="0x0000000000000000000000000000000000000001",
            immediate=True
        )
        
        print(f"Updated parameter: {update_id}")
        
        # Get updated parameter
        updated_voting_period = await registry.get_parameter("voting_period_days")
        print(f"New voting period: {updated_voting_period.current_value} days")
        
        # List governance parameters
        gov_params = await registry.list_parameters(
            category=ParameterCategory.GOVERNANCE,
            governance_controlled=True
        )
        print(f"Governance parameters: {len(gov_params)}")
        
        # Get parameter stats
        stats = await registry.get_parameter_stats()
        print(f"Parameter stats: {stats}")
        
        await registry.stop()
        print("Parameter registry test completed successfully")
        
    except Exception as e:
        print(f"Parameter registry test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_parameter_registry())
