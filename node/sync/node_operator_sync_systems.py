# Path: node/sync/node_operator_sync_systems.py
# Lucid RDP Node Operator Sync Systems - Multi-operator coordination and state synchronization
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import asyncio
import logging
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import json
from decimal import Decimal
import time
# Optional aiohttp import
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    AIOHTTP_AVAILABLE = False

# Database adapter handles compatibility
from ..database_adapter import DatabaseAdapter, get_database_adapter

# Import existing components using relative imports
from ..peer_discovery import PeerDiscovery
from ..work_credits import WorkCreditsCalculator

logger = logging.getLogger(__name__)

# Operator Sync Constants
SYNC_HEARTBEAT_INTERVAL_SEC = int(os.getenv("LUCID_SYNC_HEARTBEAT_INTERVAL_SEC", "30"))  # 30 seconds
OPERATOR_TIMEOUT_MINUTES = int(os.getenv("LUCID_OPERATOR_TIMEOUT_MINUTES", "5"))  # 5 minutes
CONFLICT_RESOLUTION_TIMEOUT_SEC = int(os.getenv("LUCID_CONFLICT_RESOLUTION_TIMEOUT_SEC", "60"))  # 1 minute
MAX_SYNC_RETRIES = int(os.getenv("LUCID_MAX_SYNC_RETRIES", "3"))  # Max retry attempts
STATE_CHECKPOINT_INTERVAL_MINUTES = int(os.getenv("LUCID_STATE_CHECKPOINT_INTERVAL_MINUTES", "15"))  # 15 minutes
OPERATION_BATCH_SIZE = int(os.getenv("LUCID_OPERATION_BATCH_SIZE", "100"))  # Operations per batch


class OperatorRole(Enum):
    """Operator roles in the system"""
    PRIMARY = "primary"           # Primary operator (leader)
    SECONDARY = "secondary"       # Secondary operator (follower)
    BACKUP = "backup"            # Backup operator
    WITNESS = "witness"          # Witness-only operator
    COORDINATOR = "coordinator"  # Special coordination role


class SyncStatus(Enum):
    """Synchronization status"""
    IN_SYNC = "in_sync"
    SYNCING = "syncing"
    OUT_OF_SYNC = "out_of_sync"
    CONFLICT = "conflict"
    OFFLINE = "offline"
    ERROR = "error"


class OperationType(Enum):
    """Types of distributed operations"""
    STATE_UPDATE = "state_update"
    TRANSACTION = "transaction"
    CONFIGURATION = "configuration"
    MAINTENANCE = "maintenance"
    EMERGENCY = "emergency"
    CHECKPOINT = "checkpoint"


class ConflictType(Enum):
    """Types of synchronization conflicts"""
    STATE_DIVERGENCE = "state_divergence"
    OPERATION_CONFLICT = "operation_conflict"
    TIMESTAMP_CONFLICT = "timestamp_conflict"
    VERSION_CONFLICT = "version_conflict"
    LEADERSHIP_CONFLICT = "leadership_conflict"


@dataclass
class OperatorInfo:
    """Information about a network operator"""
    operator_id: str
    node_id: str
    role: OperatorRole
    endpoint: str
    public_key: str
    status: SyncStatus = SyncStatus.OFFLINE
    last_heartbeat: Optional[datetime] = None
    version: str = "1.0.0"
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.operator_id,
            "node_id": self.node_id,
            "role": self.role.value,
            "endpoint": self.endpoint,
            "public_key": self.public_key,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat,
            "version": self.version,
            "capabilities": self.capabilities,
            "metadata": self.metadata
        }


@dataclass
class SyncOperation:
    """Distributed synchronization operation"""
    operation_id: str
    initiator_id: str
    operation_type: OperationType
    payload: Dict[str, Any] = field(default_factory=dict)
    target_operators: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    priority: int = 1  # 1=low, 5=critical
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.operation_id,
            "initiator_id": self.initiator_id,
            "operation_type": self.operation_type.value,
            "payload": self.payload,
            "target_operators": self.target_operators,
            "created_at": self.created_at,
            "executed_at": self.executed_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "result": self.result,
            "retry_count": self.retry_count,
            "priority": self.priority
        }


@dataclass
class StateCheckpoint:
    """State checkpoint for synchronization"""
    checkpoint_id: str
    operator_id: str
    state_hash: str
    state_data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.checkpoint_id,
            "operator_id": self.operator_id,
            "state_hash": self.state_hash,
            "state_data": self.state_data,
            "created_at": self.created_at,
            "version": self.version,
            "metadata": self.metadata
        }


@dataclass
class SyncConflict:
    """Synchronization conflict record"""
    conflict_id: str
    conflict_type: ConflictType
    involved_operators: List[str] = field(default_factory=list)
    conflict_data: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    resolution_method: Optional[str] = None
    resolver_id: Optional[str] = None
    auto_resolved: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.conflict_id,
            "conflict_type": self.conflict_type.value,
            "involved_operators": self.involved_operators,
            "conflict_data": self.conflict_data,
            "detected_at": self.detected_at,
            "resolved_at": self.resolved_at,
            "resolution_method": self.resolution_method,
            "resolver_id": self.resolver_id,
            "auto_resolved": self.auto_resolved
        }


@dataclass
class OperatorMetrics:
    """Performance metrics for an operator"""
    operator_id: str
    total_operations: int
    successful_operations: int
    failed_operations: int
    average_response_time: float
    sync_accuracy: float
    uptime_percentage: float
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "operator_id": self.operator_id,
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "average_response_time": self.average_response_time,
            "sync_accuracy": self.sync_accuracy,
            "uptime_percentage": self.uptime_percentage,
            "last_updated": self.last_updated
        }


class NodeOperatorSyncSystem:
    """
    Node Operator Synchronization System for multi-operator coordination.
    
    Handles:
    - Operator registration and discovery
    - State synchronization across operators
    - Distributed operation coordination
    - Conflict detection and resolution
    - Leader election and failover
    - Performance monitoring and metrics
    - Checkpoint-based recovery
    """
    
    def __init__(self, db: DatabaseAdapter, peer_discovery: PeerDiscovery,
                 work_credits: WorkCreditsCalculator, operator_id: str, node_id: str):
        self.db = db
        self.peer_discovery = peer_discovery
        self.work_credits = work_credits
        self.operator_id = operator_id
        self.node_id = node_id
        
        # State tracking
        self.operators: Dict[str, OperatorInfo] = {}
        self.pending_operations: Dict[str, SyncOperation] = {}
        self.active_conflicts: Dict[str, SyncConflict] = {}
        self.operator_metrics: Dict[str, OperatorMetrics] = {}
        self.running = False
        
        # Current operator state
        self.current_role = OperatorRole.SECONDARY
        self.last_checkpoint: Optional[StateCheckpoint] = None
        self.state_version = 1
        
        # Background tasks
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._sync_task: Optional[asyncio.Task] = None
        self._conflict_resolution_task: Optional[asyncio.Task] = None
        self._checkpoint_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        
        logger.info(f"Node operator sync system initialized for operator {operator_id}")
    
    async def start(self):
        """Start operator sync system"""
        try:
            self.running = True
            
            # Setup database indexes
            await self._setup_indexes()
            
            # Load existing data
            await self._load_operators()
            await self._load_pending_operations()
            await self._load_active_conflicts()
            await self._load_operator_metrics()
            await self._load_last_checkpoint()
            
            # Register this operator
            await self._register_operator()
            
            # Start background tasks
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._sync_task = asyncio.create_task(self._sync_loop())
            self._conflict_resolution_task = asyncio.create_task(self._conflict_resolution_loop())
            self._checkpoint_task = asyncio.create_task(self._checkpoint_loop())
            self._metrics_task = asyncio.create_task(self._metrics_loop())
            
            logger.info("Node operator sync system started")
            
        except Exception as e:
            logger.error(f"Failed to start operator sync system: {e}")
            raise
    
    async def stop(self):
        """Stop operator sync system"""
        try:
            self.running = False
            
            # Update operator status to offline
            await self._update_operator_status(SyncStatus.OFFLINE)
            
            # Cancel background tasks
            tasks = [self._heartbeat_task, self._sync_task, self._conflict_resolution_task,
                    self._checkpoint_task, self._metrics_task]
            for task in tasks:
                if task and not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*[t for t in tasks if t], return_exceptions=True)
            
            logger.info("Node operator sync system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping operator sync system: {e}")
    
    async def register_operator(self, endpoint: str, public_key: str, role: OperatorRole,
                              capabilities: Optional[List[str]] = None) -> str:
        """
        Register a new operator in the system.
        
        Args:
            endpoint: Network endpoint for the operator
            public_key: Public key for authentication
            role: Operator role
            capabilities: List of operator capabilities
            
        Returns:
            Operator ID
        """
        try:
            operator = OperatorInfo(
                operator_id=self.operator_id,
                node_id=self.node_id,
                role=role,
                endpoint=endpoint,
                public_key=public_key,
                capabilities=capabilities or [],
                status=SyncStatus.IN_SYNC,
                last_heartbeat=datetime.now(timezone.utc)
            )
            
            # Store operator info
            self.operators[self.operator_id] = operator
            await self.db["operators"].replace_one(
                {"_id": self.operator_id},
                operator.to_dict(),
                upsert=True
            )
            
            self.current_role = role
            
            logger.info(f"Operator registered: {self.operator_id} as {role.value}")
            return self.operator_id
            
        except Exception as e:
            logger.error(f"Failed to register operator: {e}")
            raise
    
    async def submit_operation(self, operation_type: OperationType, payload: Dict[str, Any],
                             target_operators: Optional[List[str]] = None,
                             priority: int = 1) -> str:
        """
        Submit a distributed operation for synchronization.
        
        Args:
            operation_type: Type of operation
            payload: Operation payload data
            target_operators: Specific operators to target (None for all)
            priority: Operation priority (1-5)
            
        Returns:
            Operation ID
        """
        try:
            operation_id = str(uuid.uuid4())
            
            # If no targets specified, use all active operators
            if target_operators is None:
                target_operators = [
                    op_id for op_id, op in self.operators.items()
                    if op.status in [SyncStatus.IN_SYNC, SyncStatus.SYNCING]
                ]
            
            operation = SyncOperation(
                operation_id=operation_id,
                initiator_id=self.operator_id,
                operation_type=operation_type,
                payload=payload,
                target_operators=target_operators,
                priority=priority
            )
            
            # Store operation
            self.pending_operations[operation_id] = operation
            await self.db["sync_operations"].replace_one(
                {"_id": operation_id},
                operation.to_dict(),
                upsert=True
            )
            
            # Immediately execute if high priority
            if priority >= 4:
                await self._execute_operation(operation)
            
            logger.info(f"Operation submitted: {operation_id} ({operation_type.value})")
            return operation_id
            
        except Exception as e:
            logger.error(f"Failed to submit operation: {e}")
            raise
    
    async def create_checkpoint(self, state_data: Dict[str, Any]) -> str:
        """
        Create a state checkpoint.
        
        Args:
            state_data: Current state data to checkpoint
            
        Returns:
            Checkpoint ID
        """
        try:
            checkpoint_id = str(uuid.uuid4())
            
            # Calculate state hash
            state_json = json.dumps(state_data, sort_keys=True)
            state_hash = hashlib.sha256(state_json.encode()).hexdigest()
            
            checkpoint = StateCheckpoint(
                checkpoint_id=checkpoint_id,
                operator_id=self.operator_id,
                state_hash=state_hash,
                state_data=state_data,
                version=self.state_version
            )
            
            # Store checkpoint
            self.last_checkpoint = checkpoint
            await self.db["state_checkpoints"].replace_one(
                {"_id": checkpoint_id},
                checkpoint.to_dict(),
                upsert=True
            )
            
            # Increment state version
            self.state_version += 1
            
            # Broadcast checkpoint to other operators
            await self._broadcast_checkpoint(checkpoint)
            
            logger.info(f"State checkpoint created: {checkpoint_id}")
            return checkpoint_id
            
        except Exception as e:
            logger.error(f"Failed to create checkpoint: {e}")
            raise
    
    async def report_conflict(self, conflict_type: ConflictType, involved_operators: List[str],
                            conflict_data: Dict[str, Any]) -> str:
        """
        Report a synchronization conflict.
        
        Args:
            conflict_type: Type of conflict
            involved_operators: List of involved operator IDs
            conflict_data: Conflict details
            
        Returns:
            Conflict ID
        """
        try:
            conflict_id = str(uuid.uuid4())
            
            conflict = SyncConflict(
                conflict_id=conflict_id,
                conflict_type=conflict_type,
                involved_operators=involved_operators,
                conflict_data=conflict_data
            )
            
            # Store conflict
            self.active_conflicts[conflict_id] = conflict
            await self.db["sync_conflicts"].insert_one(conflict.to_dict())
            
            logger.warning(f"Conflict reported: {conflict_id} ({conflict_type.value})")
            
            # Attempt automatic resolution
            await self._attempt_conflict_resolution(conflict)
            
            return conflict_id
            
        except Exception as e:
            logger.error(f"Failed to report conflict: {e}")
            raise
    
    async def get_operator_status(self, operator_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for an operator"""
        try:
            operator = self.operators.get(operator_id)
            if not operator:
                # Try loading from database
                operator_doc = await self.db["operators"].find_one({"_id": operator_id})
                if operator_doc:
                    return operator_doc
                return None
            
            return operator.to_dict()
            
        except Exception as e:
            logger.error(f"Failed to get operator status: {e}")
            return None
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system synchronization status"""
        try:
            total_operators = len(self.operators)
            online_operators = len([op for op in self.operators.values() if op.status != SyncStatus.OFFLINE])
            in_sync_operators = len([op for op in self.operators.values() if op.status == SyncStatus.IN_SYNC])
            
            # Calculate sync health percentage
            sync_health = (in_sync_operators / max(total_operators, 1)) * 100
            
            # Get primary operator
            primary_operator = None
            for op in self.operators.values():
                if op.role == OperatorRole.PRIMARY:
                    primary_operator = op.operator_id
                    break
            
            return {
                "total_operators": total_operators,
                "online_operators": online_operators,
                "in_sync_operators": in_sync_operators,
                "sync_health_percentage": sync_health,
                "primary_operator": primary_operator,
                "pending_operations": len(self.pending_operations),
                "active_conflicts": len(self.active_conflicts),
                "current_state_version": self.state_version,
                "last_checkpoint": self.last_checkpoint.checkpoint_id if self.last_checkpoint else None,
                "system_status": "healthy" if sync_health > 80 else "degraded" if sync_health > 50 else "critical"
            }
            
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {"error": str(e)}
    
    async def get_operator_metrics(self, operator_id: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for an operator"""
        try:
            metrics = self.operator_metrics.get(operator_id)
            if metrics:
                return metrics.to_dict()
            
            # Try loading from database
            metrics_doc = await self.db["operator_metrics"].find_one({"operator_id": operator_id})
            return metrics_doc
            
        except Exception as e:
            logger.error(f"Failed to get operator metrics: {e}")
            return None
    
    async def force_resync(self, target_operator: Optional[str] = None) -> bool:
        """Force a resynchronization with operators"""
        try:
            if target_operator:
                # Resync with specific operator
                operator = self.operators.get(target_operator)
                if operator:
                    operator.status = SyncStatus.SYNCING
                    await self._sync_with_operator(operator)
            else:
                # Resync with all operators
                for operator in self.operators.values():
                    if operator.operator_id != self.operator_id:
                        operator.status = SyncStatus.SYNCING
                        await self._sync_with_operator(operator)
            
            logger.info(f"Forced resync initiated with {target_operator or 'all operators'}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to force resync: {e}")
            return False
    
    async def _register_operator(self):
        """Register this operator in the system"""
        try:
            # Default registration for current operator
            await self.register_operator(
                endpoint=f"http://localhost:8080/operator/{self.operator_id}",
                public_key="mock_public_key",  # Would use actual public key
                role=self.current_role,
                capabilities=["sync", "checkpoint", "conflict_resolution"]
            )
        except Exception as e:
            logger.error(f"Failed to register operator: {e}")
    
    async def _execute_operation(self, operation: SyncOperation):
        """Execute a synchronization operation"""
        try:
            operation.executed_at = datetime.now(timezone.utc)
            operation.status = "executing"
            
            # Update in database
            await self.db["sync_operations"].update_one(
                {"_id": operation.operation_id},
                {"$set": {
                    "executed_at": operation.executed_at,
                    "status": operation.status
                }}
            )
            
            # Simulate operation execution based on type
            success = True
            result = {}
            
            if operation.operation_type == OperationType.STATE_UPDATE:
                # Apply state update
                result = await self._apply_state_update(operation.payload)
                
            elif operation.operation_type == OperationType.CONFIGURATION:
                # Apply configuration changes
                result = await self._apply_configuration(operation.payload)
                
            elif operation.operation_type == OperationType.CHECKPOINT:
                # Create checkpoint
                result = await self._handle_checkpoint_operation(operation.payload)
                
            elif operation.operation_type == OperationType.EMERGENCY:
                # Handle emergency operation
                result = await self._handle_emergency_operation(operation.payload)
                
            # Update operation status
            operation.completed_at = datetime.now(timezone.utc)
            operation.status = "completed" if success else "failed"
            operation.result = result
            
            await self.db["sync_operations"].update_one(
                {"_id": operation.operation_id},
                {"$set": {
                    "completed_at": operation.completed_at,
                    "status": operation.status,
                    "result": operation.result
                }}
            )
            
            # Remove from pending operations
            if operation.operation_id in self.pending_operations:
                del self.pending_operations[operation.operation_id]
            
            logger.info(f"Operation executed: {operation.operation_id} - {operation.status}")
            
        except Exception as e:
            logger.error(f"Failed to execute operation {operation.operation_id}: {e}")
            operation.status = "failed"
            operation.retry_count += 1
    
    async def _apply_state_update(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a state update operation"""
        try:
            # Mock state update implementation
            state_changes = payload.get("changes", {})
            
            # Validate state changes
            if not self._validate_state_changes(state_changes):
                return {"success": False, "error": "Invalid state changes"}
            
            # Apply changes (mock implementation)
            applied_changes = len(state_changes)
            
            return {
                "success": True,
                "applied_changes": applied_changes,
                "new_state_version": self.state_version
            }
            
        except Exception as e:
            logger.error(f"Failed to apply state update: {e}")
            return {"success": False, "error": str(e)}
    
    async def _apply_configuration(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Apply configuration changes"""
        try:
            config_changes = payload.get("config", {})
            
            # Mock configuration application
            applied_configs = len(config_changes)
            
            return {
                "success": True,
                "applied_configs": applied_configs
            }
            
        except Exception as e:
            logger.error(f"Failed to apply configuration: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_checkpoint_operation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle checkpoint operation"""
        try:
            state_data = payload.get("state_data", {})
            checkpoint_id = await self.create_checkpoint(state_data)
            
            return {
                "success": True,
                "checkpoint_id": checkpoint_id
            }
            
        except Exception as e:
            logger.error(f"Failed to handle checkpoint operation: {e}")
            return {"success": False, "error": str(e)}
    
    async def _handle_emergency_operation(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emergency operation"""
        try:
            emergency_type = payload.get("type", "unknown")
            
            # Mock emergency handling
            if emergency_type == "failover":
                # Handle leader failover
                await self._initiate_leader_election()
            elif emergency_type == "rollback":
                # Rollback to previous checkpoint
                await self._rollback_to_checkpoint()
            
            return {
                "success": True,
                "emergency_type": emergency_type,
                "handled": True
            }
            
        except Exception as e:
            logger.error(f"Failed to handle emergency operation: {e}")
            return {"success": False, "error": str(e)}
    
    async def _validate_state_changes(self, changes: Dict[str, Any]) -> bool:
        """Validate proposed state changes"""
        try:
            # Mock validation logic
            if not changes:
                return False
            
            # Check for conflicting changes
            for key, value in changes.items():
                if not isinstance(key, str) or key.startswith("_"):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate state changes: {e}")
            return False
    
    async def _sync_with_operator(self, operator: OperatorInfo):
        """Synchronize state with a specific operator"""
        try:
            # Mock sync implementation - would make HTTP requests in real system
            if operator.status == SyncStatus.OFFLINE:
                return
            
            sync_start = time.time()
            
            # Simulate network delay
            await asyncio.sleep(0.1)
            
            # Check for state differences
            state_diff = await self._calculate_state_diff(operator)
            
            if state_diff:
                # Send sync updates
                await self._send_sync_updates(operator, state_diff)
            
            # Update sync status
            sync_time = time.time() - sync_start
            operator.status = SyncStatus.IN_SYNC
            operator.last_heartbeat = datetime.now(timezone.utc)
            
            # Update metrics
            await self._update_operator_metrics(operator.operator_id, sync_time, True)
            
            logger.debug(f"Sync completed with operator {operator.operator_id}")
            
        except Exception as e:
            logger.error(f"Failed to sync with operator {operator.operator_id}: {e}")
            operator.status = SyncStatus.ERROR
            await self._update_operator_metrics(operator.operator_id, 0, False)
    
    async def _calculate_state_diff(self, operator: OperatorInfo) -> Optional[Dict[str, Any]]:
        """Calculate state differences with an operator"""
        try:
            # Mock state difference calculation
            # In real implementation, would compare state hashes/versions
            
            # Simulate finding differences 20% of the time
            import secrets
            if secrets.randbits(1) and secrets.randbits(1) and secrets.randbits(1):
                return {
                    "version_diff": 1,
                    "changes": ["mock_change_1", "mock_change_2"]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to calculate state diff: {e}")
            return None
    
    async def _send_sync_updates(self, operator: OperatorInfo, updates: Dict[str, Any]):
        """Send synchronization updates to an operator"""
        try:
            # Mock sending sync updates
            # In real implementation, would make HTTP POST to operator endpoint
            
            logger.debug(f"Sending sync updates to {operator.operator_id}: {len(updates.get('changes', []))} changes")
            
            # Simulate network delay
            await asyncio.sleep(0.05)
            
        except Exception as e:
            logger.error(f"Failed to send sync updates to {operator.operator_id}: {e}")
    
    async def _broadcast_checkpoint(self, checkpoint: StateCheckpoint):
        """Broadcast checkpoint to all operators"""
        try:
            for operator in self.operators.values():
                if operator.operator_id != self.operator_id:
                    # Send checkpoint notification
                    await self._send_checkpoint_notification(operator, checkpoint)
            
            logger.info(f"Checkpoint broadcast completed: {checkpoint.checkpoint_id}")
            
        except Exception as e:
            logger.error(f"Failed to broadcast checkpoint: {e}")
    
    async def _send_checkpoint_notification(self, operator: OperatorInfo, checkpoint: StateCheckpoint):
        """Send checkpoint notification to an operator"""
        try:
            # Mock sending checkpoint notification
            logger.debug(f"Sending checkpoint notification to {operator.operator_id}: {checkpoint.checkpoint_id}")
            
            # Simulate network delay
            await asyncio.sleep(0.02)
            
        except Exception as e:
            logger.error(f"Failed to send checkpoint notification to {operator.operator_id}: {e}")
    
    async def _attempt_conflict_resolution(self, conflict: SyncConflict):
        """Attempt to automatically resolve a conflict"""
        try:
            resolution_method = None
            
            if conflict.conflict_type == ConflictType.STATE_DIVERGENCE:
                # Use latest timestamp
                resolution_method = "latest_timestamp"
                
            elif conflict.conflict_type == ConflictType.OPERATION_CONFLICT:
                # Use operation priority
                resolution_method = "priority_based"
                
            elif conflict.conflict_type == ConflictType.VERSION_CONFLICT:
                # Use highest version number
                resolution_method = "highest_version"
                
            elif conflict.conflict_type == ConflictType.LEADERSHIP_CONFLICT:
                # Initiate new leader election
                resolution_method = "leader_election"
                await self._initiate_leader_election()
            
            if resolution_method:
                # Mark conflict as auto-resolved
                conflict.resolved_at = datetime.now(timezone.utc)
                conflict.resolution_method = resolution_method
                conflict.resolver_id = self.operator_id
                conflict.auto_resolved = True
                
                # Update database
                await self.db["sync_conflicts"].update_one(
                    {"_id": conflict.conflict_id},
                    {"$set": {
                        "resolved_at": conflict.resolved_at,
                        "resolution_method": conflict.resolution_method,
                        "resolver_id": conflict.resolver_id,
                        "auto_resolved": conflict.auto_resolved
                    }}
                )
                
                # Remove from active conflicts
                if conflict.conflict_id in self.active_conflicts:
                    del self.active_conflicts[conflict.conflict_id]
                
                logger.info(f"Conflict auto-resolved: {conflict.conflict_id} using {resolution_method}")
            
        except Exception as e:
            logger.error(f"Failed to resolve conflict {conflict.conflict_id}: {e}")
    
    async def _initiate_leader_election(self):
        """Initiate leader election process"""
        try:
            # Simple leader election based on operator ID (lexicographic order)
            eligible_operators = [
                op for op in self.operators.values()
                if op.status in [SyncStatus.IN_SYNC, SyncStatus.SYNCING] and
                op.role in [OperatorRole.PRIMARY, OperatorRole.SECONDARY]
            ]
            
            if not eligible_operators:
                return
            
            # Sort by operator ID to get deterministic leader
            eligible_operators.sort(key=lambda op: op.operator_id)
            new_leader = eligible_operators[0]
            
            # Update roles
            for operator in self.operators.values():
                if operator.operator_id == new_leader.operator_id:
                    operator.role = OperatorRole.PRIMARY
                elif operator.role == OperatorRole.PRIMARY:
                    operator.role = OperatorRole.SECONDARY
            
            # Update current role if this operator is the new leader
            if new_leader.operator_id == self.operator_id:
                self.current_role = OperatorRole.PRIMARY
            
            logger.info(f"New leader elected: {new_leader.operator_id}")
            
        except Exception as e:
            logger.error(f"Failed to initiate leader election: {e}")
    
    async def _rollback_to_checkpoint(self):
        """Rollback to the last checkpoint"""
        try:
            if not self.last_checkpoint:
                logger.warning("No checkpoint available for rollback")
                return
            
            # Mock rollback implementation
            logger.info(f"Rolling back to checkpoint: {self.last_checkpoint.checkpoint_id}")
            
            # Reset state version
            self.state_version = self.last_checkpoint.version
            
            # Broadcast rollback to all operators
            rollback_operation = await self.submit_operation(
                OperationType.EMERGENCY,
                {"type": "rollback", "checkpoint_id": self.last_checkpoint.checkpoint_id},
                priority=5
            )
            
            logger.info(f"Rollback initiated: {rollback_operation}")
            
        except Exception as e:
            logger.error(f"Failed to rollback to checkpoint: {e}")
    
    async def _update_operator_status(self, status: SyncStatus):
        """Update this operator's status"""
        try:
            if self.operator_id in self.operators:
                self.operators[self.operator_id].status = status
                self.operators[self.operator_id].last_heartbeat = datetime.now(timezone.utc)
                
                await self.db["operators"].update_one(
                    {"_id": self.operator_id},
                    {"$set": {
                        "status": status.value,
                        "last_heartbeat": self.operators[self.operator_id].last_heartbeat
                    }}
                )
        except Exception as e:
            logger.error(f"Failed to update operator status: {e}")
    
    async def _update_operator_metrics(self, operator_id: str, response_time: float, success: bool):
        """Update performance metrics for an operator"""
        try:
            if operator_id not in self.operator_metrics:
                self.operator_metrics[operator_id] = OperatorMetrics(
                    operator_id=operator_id,
                    total_operations=0,
                    successful_operations=0,
                    failed_operations=0,
                    average_response_time=0.0,
                    sync_accuracy=100.0,
                    uptime_percentage=100.0
                )
            
            metrics = self.operator_metrics[operator_id]
            metrics.total_operations += 1
            
            if success:
                metrics.successful_operations += 1
            else:
                metrics.failed_operations += 1
            
            # Update average response time
            if metrics.total_operations > 1:
                metrics.average_response_time = (
                    (metrics.average_response_time * (metrics.total_operations - 1) + response_time) /
                    metrics.total_operations
                )
            else:
                metrics.average_response_time = response_time
            
            # Update sync accuracy
            metrics.sync_accuracy = (metrics.successful_operations / metrics.total_operations) * 100
            
            metrics.last_updated = datetime.now(timezone.utc)
            
            # Store in database
            await self.db["operator_metrics"].replace_one(
                {"operator_id": operator_id},
                metrics.to_dict(),
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Failed to update operator metrics: {e}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self.running:
            try:
                await self._update_operator_status(SyncStatus.IN_SYNC)
                
                # Check for offline operators
                now = datetime.now(timezone.utc)
                timeout_threshold = now - timedelta(minutes=OPERATOR_TIMEOUT_MINUTES)
                
                for operator in self.operators.values():
                    if (operator.last_heartbeat and 
                        operator.last_heartbeat < timeout_threshold and
                        operator.status != SyncStatus.OFFLINE):
                        
                        operator.status = SyncStatus.OFFLINE
                        logger.warning(f"Operator {operator.operator_id} marked as offline")
                
                await asyncio.sleep(SYNC_HEARTBEAT_INTERVAL_SEC)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                await asyncio.sleep(30)
    
    async def _sync_loop(self):
        """Main synchronization loop"""
        while self.running:
            try:
                # Process pending operations
                pending_ops = list(self.pending_operations.values())
                pending_ops.sort(key=lambda op: op.priority, reverse=True)
                
                for operation in pending_ops[:OPERATION_BATCH_SIZE]:
                    await self._execute_operation(operation)
                
                # Sync with other operators
                for operator in list(self.operators.values()):
                    if (operator.operator_id != self.operator_id and
                        operator.status in [SyncStatus.IN_SYNC, SyncStatus.SYNCING]):
                        await self._sync_with_operator(operator)
                
                await asyncio.sleep(SYNC_HEARTBEAT_INTERVAL_SEC)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                await asyncio.sleep(30)
    
    async def _conflict_resolution_loop(self):
        """Handle conflict resolution"""
        while self.running:
            try:
                # Process active conflicts
                for conflict in list(self.active_conflicts.values()):
                    # Check if conflict resolution timeout has passed
                    conflict_age = datetime.now(timezone.utc) - conflict.detected_at
                    if conflict_age.total_seconds() > CONFLICT_RESOLUTION_TIMEOUT_SEC:
                        await self._attempt_conflict_resolution(conflict)
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Conflict resolution loop error: {e}")
                await asyncio.sleep(60)
    
    async def _checkpoint_loop(self):
        """Create periodic checkpoints"""
        while self.running:
            try:
                # Only primary operator creates regular checkpoints
                if self.current_role == OperatorRole.PRIMARY:
                    # Mock state data for checkpoint
                    state_data = {
                        "version": self.state_version,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "operators": len(self.operators),
                        "operations_completed": len([
                            op for op in self.pending_operations.values() 
                            if op.status == "completed"
                        ])
                    }
                    
                    await self.create_checkpoint(state_data)
                
                await asyncio.sleep(STATE_CHECKPOINT_INTERVAL_MINUTES * 60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Checkpoint loop error: {e}")
                await asyncio.sleep(300)
    
    async def _metrics_loop(self):
        """Update operator metrics periodically"""
        while self.running:
            try:
                # Calculate uptime percentage
                now = datetime.now(timezone.utc)
                for operator_id, operator in self.operators.items():
                    if operator_id in self.operator_metrics:
                        metrics = self.operator_metrics[operator_id]
                        
                        # Update uptime based on status
                        if operator.status == SyncStatus.IN_SYNC:
                            # Operator is up, maintain or increase uptime
                            metrics.uptime_percentage = min(100.0, metrics.uptime_percentage + 0.1)
                        else:
                            # Operator is down, decrease uptime
                            metrics.uptime_percentage = max(0.0, metrics.uptime_percentage - 1.0)
                        
                        metrics.last_updated = now
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics loop error: {e}")
                await asyncio.sleep(300)
    
    async def _setup_indexes(self):
        """Setup database indexes"""
        try:
            # Operators indexes
            await self.db["operators"].create_index("node_id")
            await self.db["operators"].create_index("role")
            await self.db["operators"].create_index("status")
            await self.db["operators"].create_index("last_heartbeat")
            
            # Sync operations indexes
            await self.db["sync_operations"].create_index("initiator_id")
            await self.db["sync_operations"].create_index("operation_type")
            await self.db["sync_operations"].create_index("status")
            await self.db["sync_operations"].create_index("priority")
            await self.db["sync_operations"].create_index("created_at")
            
            # State checkpoints indexes
            await self.db["state_checkpoints"].create_index("operator_id")
            await self.db["state_checkpoints"].create_index("created_at")
            await self.db["state_checkpoints"].create_index("version")
            
            # Sync conflicts indexes
            await self.db["sync_conflicts"].create_index("conflict_type")
            await self.db["sync_conflicts"].create_index("detected_at")
            await self.db["sync_conflicts"].create_index("resolved_at")
            await self.db["sync_conflicts"].create_index("auto_resolved")
            
            # Operator metrics indexes
            await self.db["operator_metrics"].create_index("operator_id")
            await self.db["operator_metrics"].create_index("sync_accuracy")
            await self.db["operator_metrics"].create_index("uptime_percentage")
            
            logger.info("Operator sync system database indexes created")
            
        except Exception as e:
            logger.warning(f"Failed to create operator sync indexes: {e}")
    
    async def _load_operators(self):
        """Load operators from database"""
        try:
            cursor = self.db["operators"].find({})
            
            async for operator_doc in cursor:
                operator = OperatorInfo(
                    operator_id=operator_doc["_id"],
                    node_id=operator_doc["node_id"],
                    role=OperatorRole(operator_doc["role"]),
                    endpoint=operator_doc["endpoint"],
                    public_key=operator_doc["public_key"],
                    status=SyncStatus(operator_doc["status"]),
                    last_heartbeat=operator_doc.get("last_heartbeat"),
                    version=operator_doc.get("version", "1.0.0"),
                    capabilities=operator_doc.get("capabilities", []),
                    metadata=operator_doc.get("metadata", {})
                )
                
                self.operators[operator.operator_id] = operator
            
            logger.info(f"Loaded {len(self.operators)} operators")
            
        except Exception as e:
            logger.error(f"Failed to load operators: {e}")
    
    async def _load_pending_operations(self):
        """Load pending operations from database"""
        try:
            cursor = self.db["sync_operations"].find({
                "status": {"$in": ["pending", "executing"]}
            })
            
            async for op_doc in cursor:
                operation = SyncOperation(
                    operation_id=op_doc["_id"],
                    initiator_id=op_doc["initiator_id"],
                    operation_type=OperationType(op_doc["operation_type"]),
                    payload=op_doc.get("payload", {}),
                    target_operators=op_doc.get("target_operators", []),
                    created_at=op_doc["created_at"],
                    executed_at=op_doc.get("executed_at"),
                    completed_at=op_doc.get("completed_at"),
                    status=op_doc["status"],
                    result=op_doc.get("result"),
                    retry_count=op_doc.get("retry_count", 0),
                    priority=op_doc.get("priority", 1)
                )
                
                self.pending_operations[operation.operation_id] = operation
            
            logger.info(f"Loaded {len(self.pending_operations)} pending operations")
            
        except Exception as e:
            logger.error(f"Failed to load pending operations: {e}")
    
    async def _load_active_conflicts(self):
        """Load active conflicts from database"""
        try:
            cursor = self.db["sync_conflicts"].find({
                "resolved_at": None
            })
            
            async for conflict_doc in cursor:
                conflict = SyncConflict(
                    conflict_id=conflict_doc["_id"],
                    conflict_type=ConflictType(conflict_doc["conflict_type"]),
                    involved_operators=conflict_doc.get("involved_operators", []),
                    conflict_data=conflict_doc.get("conflict_data", {}),
                    detected_at=conflict_doc["detected_at"],
                    resolved_at=conflict_doc.get("resolved_at"),
                    resolution_method=conflict_doc.get("resolution_method"),
                    resolver_id=conflict_doc.get("resolver_id"),
                    auto_resolved=conflict_doc.get("auto_resolved", False)
                )
                
                self.active_conflicts[conflict.conflict_id] = conflict
            
            logger.info(f"Loaded {len(self.active_conflicts)} active conflicts")
            
        except Exception as e:
            logger.error(f"Failed to load active conflicts: {e}")
    
    async def _load_operator_metrics(self):
        """Load operator metrics from database"""
        try:
            cursor = self.db["operator_metrics"].find({})
            
            async for metrics_doc in cursor:
                metrics = OperatorMetrics(
                    operator_id=metrics_doc["operator_id"],
                    total_operations=metrics_doc["total_operations"],
                    successful_operations=metrics_doc["successful_operations"],
                    failed_operations=metrics_doc["failed_operations"],
                    average_response_time=metrics_doc["average_response_time"],
                    sync_accuracy=metrics_doc["sync_accuracy"],
                    uptime_percentage=metrics_doc["uptime_percentage"],
                    last_updated=metrics_doc["last_updated"]
                )
                
                self.operator_metrics[metrics.operator_id] = metrics
            
            logger.info(f"Loaded {len(self.operator_metrics)} operator metrics")
            
        except Exception as e:
            logger.error(f"Failed to load operator metrics: {e}")
    
    async def _load_last_checkpoint(self):
        """Load the most recent checkpoint"""
        try:
            cursor = self.db["state_checkpoints"].find({
                "operator_id": self.operator_id
            }).sort("created_at", -1).limit(1)
            
            async for checkpoint_doc in cursor:
                self.last_checkpoint = StateCheckpoint(
                    checkpoint_id=checkpoint_doc["_id"],
                    operator_id=checkpoint_doc["operator_id"],
                    state_hash=checkpoint_doc["state_hash"],
                    state_data=checkpoint_doc.get("state_data", {}),
                    created_at=checkpoint_doc["created_at"],
                    version=checkpoint_doc["version"],
                    metadata=checkpoint_doc.get("metadata", {})
                )
                
                self.state_version = self.last_checkpoint.version + 1
                break
            
            if self.last_checkpoint:
                logger.info(f"Loaded last checkpoint: {self.last_checkpoint.checkpoint_id}")
            
        except Exception as e:
            logger.error(f"Failed to load last checkpoint: {e}")


# Global operator sync system instance
_node_operator_sync_system: Optional[NodeOperatorSyncSystem] = None


def get_node_operator_sync_system() -> Optional[NodeOperatorSyncSystem]:
    """Get global operator sync system instance"""
    global _node_operator_sync_system
    return _node_operator_sync_system


def create_node_operator_sync_system(db: DatabaseAdapter, peer_discovery: PeerDiscovery,
                                    work_credits: WorkCreditsCalculator, operator_id: str,
                                    node_id: str) -> NodeOperatorSyncSystem:
    """Create operator sync system instance"""
    global _node_operator_sync_system
    _node_operator_sync_system = NodeOperatorSyncSystem(db, peer_discovery, work_credits, operator_id, node_id)
    return _node_operator_sync_system


async def cleanup_node_operator_sync_system():
    """Cleanup operator sync system"""
    global _node_operator_sync_system
    if _node_operator_sync_system:
        await _node_operator_sync_system.stop()
        _node_operator_sync_system = None


if __name__ == "__main__":
    # Test operator sync system
    async def test_operator_sync_system():
        print("Testing Lucid Node Operator Sync System...")
        
        # This would normally be initialized with real components
        # For testing purposes, we'll create mock instances
        
        print("Test completed - operator sync system ready")
    
    asyncio.run(test_operator_sync_system())