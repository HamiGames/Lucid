# LUCID Wallet Key Rotation - Key Rotation System
# Implements automated and manual key rotation for wallet security
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# Configuration from environment
KEY_ROTATION_INTERVAL_DAYS = 90
KEY_ROTATION_WARNING_DAYS = 7
KEY_ROTATION_GRACE_PERIOD_DAYS = 30
MAX_KEY_HISTORY = 10
ROTATION_BATCH_SIZE = 5


class RotationTrigger(Enum):
    """Key rotation trigger types"""
    AUTOMATIC = "automatic"          # Scheduled rotation
    MANUAL = "manual"               # Manual rotation
    SECURITY_EVENT = "security_event"  # Security incident
    COMPLIANCE = "compliance"       # Compliance requirement
    MIGRATION = "migration"         # System migration
    EXPIRY = "expiry"              # Key expiration
    COMPROMISE = "compromise"       # Suspected compromise


class RotationStatus(Enum):
    """Key rotation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ROLLBACK = "rollback"


class KeyStatus(Enum):
    """Key status states"""
    ACTIVE = "active"
    ROTATING = "rotating"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
    COMPROMISED = "compromised"
    EXPIRED = "expired"


@dataclass
class KeyRotationPolicy:
    """Key rotation policy definition"""
    policy_id: str
    name: str
    description: str
    rotation_interval_days: int
    warning_days: int
    grace_period_days: int
    max_key_history: int
    auto_rotation_enabled: bool
    requires_approval: bool
    approval_threshold: int = 1
    approvers: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KeyInfo:
    """Key information for rotation"""
    key_id: str
    key_type: str  # "ed25519", "rsa", "secp256k1"
    public_key: bytes
    private_key_encrypted: bytes
    created_at: datetime
    last_rotation: Optional[datetime] = None
    next_rotation: Optional[datetime] = None
    status: KeyStatus = KeyStatus.ACTIVE
    rotation_count: int = 0
    usage_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RotationTask:
    """Key rotation task"""
    task_id: str
    key_id: str
    wallet_id: str
    trigger: RotationTrigger
    status: RotationStatus
    old_key: Optional[KeyInfo] = None
    new_key: Optional[KeyInfo] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    approvers: List[str] = field(default_factory=list)
    approvals: Dict[str, bool] = field(default_factory=dict)
    rollback_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RotationEvent:
    """Key rotation event"""
    event_id: str
    timestamp: datetime
    event_type: str
    key_id: str
    wallet_id: str
    task_id: Optional[str] = None
    status: RotationStatus = RotationStatus.PENDING
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


class KeyRotationManager:
    """
    Key rotation manager for automated and manual key rotation.
    
    Features:
    - Automated key rotation based on policies
    - Manual key rotation with approval workflows
    - Key lifecycle management
    - Rollback capabilities
    - Comprehensive audit logging
    - Integration with external systems
    - Batch rotation operations
    - Policy-based rotation rules
    """
    
    def __init__(self, wallet_id: str):
        """Initialize key rotation manager"""
        self.wallet_id = wallet_id
        self.rotation_policies: Dict[str, KeyRotationPolicy] = {}
        self.active_keys: Dict[str, KeyInfo] = {}
        self.key_history: Dict[str, List[KeyInfo]] = {}
        self.rotation_tasks: Dict[str, RotationTask] = {}
        self.rotation_events: List[RotationEvent] = []
        
        # Rotation callbacks
        self.rotation_callbacks: List[Callable] = []
        self.approval_callbacks: List[Callable] = []
        self.completion_callbacks: List[Callable] = []
        
        # Initialize default policies
        self._initialize_default_policies()
        
        logger.info(f"KeyRotationManager initialized for wallet: {wallet_id}")
    
    def _initialize_default_policies(self) -> None:
        """Initialize default rotation policies"""
        # Default policy for all keys
        default_policy = KeyRotationPolicy(
            policy_id="default",
            name="Default Key Rotation Policy",
            description="Default policy for automatic key rotation",
            rotation_interval_days=KEY_ROTATION_INTERVAL_DAYS,
            warning_days=KEY_ROTATION_WARNING_DAYS,
            grace_period_days=KEY_ROTATION_GRACE_PERIOD_DAYS,
            max_key_history=MAX_KEY_HISTORY,
            auto_rotation_enabled=True,
            requires_approval=False
        )
        
        self.rotation_policies["default"] = default_policy
        
        # High security policy
        high_security_policy = KeyRotationPolicy(
            policy_id="high_security",
            name="High Security Key Rotation Policy",
            description="Strict rotation policy for high-security keys",
            rotation_interval_days=30,
            warning_days=3,
            grace_period_days=7,
            max_key_history=20,
            auto_rotation_enabled=True,
            requires_approval=True,
            approval_threshold=2,
            conditions={"security_level": "high"}
        )
        
        self.rotation_policies["high_security"] = high_security_policy
        
        # Compliance policy
        compliance_policy = KeyRotationPolicy(
            policy_id="compliance",
            name="Compliance Key Rotation Policy",
            description="Policy for compliance-driven key rotation",
            rotation_interval_days=60,
            warning_days=5,
            grace_period_days=14,
            max_key_history=15,
            auto_rotation_enabled=True,
            requires_approval=True,
            approval_threshold=1,
            conditions={"compliance_required": True}
        )
        
        self.rotation_policies["compliance"] = compliance_policy
    
    async def create_rotation_policy(
        self,
        policy_id: str,
        name: str,
        description: str,
        rotation_interval_days: int,
        warning_days: int = KEY_ROTATION_WARNING_DAYS,
        grace_period_days: int = KEY_ROTATION_GRACE_PERIOD_DAYS,
        max_key_history: int = MAX_KEY_HISTORY,
        auto_rotation_enabled: bool = True,
        requires_approval: bool = False,
        approval_threshold: int = 1,
        approvers: Optional[List[str]] = None,
        conditions: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Create new rotation policy"""
        try:
            policy = KeyRotationPolicy(
                policy_id=policy_id,
                name=name,
                description=description,
                rotation_interval_days=rotation_interval_days,
                warning_days=warning_days,
                grace_period_days=grace_period_days,
                max_key_history=max_key_history,
                auto_rotation_enabled=auto_rotation_enabled,
                requires_approval=requires_approval,
                approval_threshold=approval_threshold,
                approvers=approvers or [],
                conditions=conditions or {},
                metadata=metadata or {}
            )
            
            self.rotation_policies[policy_id] = policy
            
            await self._log_rotation_event(
                event_type="policy_created",
                key_id="",
                message=f"Created rotation policy: {name}",
                details={"policy_id": policy_id}
            )
            
            logger.info(f"Created rotation policy: {policy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create rotation policy: {e}")
            return False
    
    async def assign_policy_to_key(
        self,
        key_id: str,
        policy_id: str,
        assigned_by: str
    ) -> bool:
        """Assign rotation policy to specific key"""
        try:
            if key_id not in self.active_keys:
                return False
            
            if policy_id not in self.rotation_policies:
                return False
            
            key = self.active_keys[key_id]
            policy = self.rotation_policies[policy_id]
            
            # Update key metadata with policy
            key.metadata["rotation_policy"] = policy_id
            key.metadata["policy_assigned_by"] = assigned_by
            key.metadata["policy_assigned_at"] = datetime.now(timezone.utc).isoformat()
            
            # Calculate next rotation date
            key.next_rotation = datetime.now(timezone.utc) + timedelta(days=policy.rotation_interval_days)
            
            await self._log_rotation_event(
                event_type="policy_assigned",
                key_id=key_id,
                message=f"Assigned policy {policy_id} to key {key_id}",
                details={"policy_id": policy_id, "assigned_by": assigned_by}
            )
            
            logger.info(f"Assigned policy {policy_id} to key {key_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign policy to key: {e}")
            return False
    
    async def rotate_key(
        self,
        key_id: str,
        trigger: RotationTrigger,
        initiated_by: str,
        requires_approval: bool = None,
        approvers: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """Initiate key rotation"""
        try:
            if key_id not in self.active_keys:
                return False, "Key not found"
            
            key = self.active_keys[key_id]
            
            # Check if key is already rotating
            if key.status == KeyStatus.ROTATING:
                return False, "Key is already rotating"
            
            # Create rotation task
            task_id = secrets.token_hex(16)
            task = RotationTask(
                task_id=task_id,
                key_id=key_id,
                wallet_id=self.wallet_id,
                trigger=trigger,
                status=RotationStatus.PENDING,
                old_key=key,
                approvers=approvers or [],
                metadata=metadata or {}
            )
            
            # Determine if approval is required
            if requires_approval is None:
                policy_id = key.metadata.get("rotation_policy", "default")
                policy = self.rotation_policies.get(policy_id)
                requires_approval = policy.requires_approval if policy else False
            
            if requires_approval and not approvers:
                return False, "Approval required but no approvers specified"
            
            # Store task
            self.rotation_tasks[task_id] = task
            
            # Update key status
            key.status = KeyStatus.ROTATING
            
            await self._log_rotation_event(
                event_type="rotation_initiated",
                key_id=key_id,
                task_id=task_id,
                message=f"Key rotation initiated by {initiated_by}",
                details={"trigger": trigger.value, "requires_approval": requires_approval}
            )
            
            # Notify callbacks
            await self._notify_rotation_callbacks("rotation_initiated", task)
            
            # Start rotation if no approval required
            if not requires_approval:
                await self._execute_rotation(task_id)
            
            logger.info(f"Key rotation initiated: {key_id}, Task: {task_id}")
            return True, task_id
            
        except Exception as e:
            logger.error(f"Failed to initiate key rotation: {e}")
            return False, f"Error: {str(e)}"
    
    async def approve_rotation(
        self,
        task_id: str,
        approver: str
    ) -> bool:
        """Approve key rotation"""
        try:
            task = self.rotation_tasks.get(task_id)
            if not task:
                return False
            
            if task.status != RotationStatus.PENDING:
                return False
            
            if approver not in task.approvers:
                return False
            
            # Record approval
            task.approvals[approver] = True
            
            await self._log_rotation_event(
                event_type="rotation_approved",
                key_id=task.key_id,
                task_id=task_id,
                message=f"Rotation approved by {approver}",
                details={"approver": approver}
            )
            
            # Check if enough approvals
            policy_id = task.old_key.metadata.get("rotation_policy", "default")
            policy = self.rotation_policies.get(policy_id)
            approval_threshold = policy.approval_threshold if policy else 1
            
            if len(task.approvals) >= approval_threshold:
                await self._execute_rotation(task_id)
            
            logger.info(f"Rotation approved by {approver}: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to approve rotation: {e}")
            return False
    
    async def cancel_rotation(
        self,
        task_id: str,
        cancelled_by: str,
        reason: str = "Manual cancellation"
    ) -> bool:
        """Cancel key rotation"""
        try:
            task = self.rotation_tasks.get(task_id)
            if not task:
                return False
            
            if task.status not in [RotationStatus.PENDING, RotationStatus.IN_PROGRESS]:
                return False
            
            # Update task status
            task.status = RotationStatus.CANCELLED
            task.completed_at = datetime.now(timezone.utc)
            task.error_message = f"Cancelled by {cancelled_by}: {reason}"
            
            # Restore key status
            if task.old_key:
                task.old_key.status = KeyStatus.ACTIVE
            
            await self._log_rotation_event(
                event_type="rotation_cancelled",
                key_id=task.key_id,
                task_id=task_id,
                message=f"Rotation cancelled by {cancelled_by}",
                details={"reason": reason}
            )
            
            # Notify callbacks
            await self._notify_rotation_callbacks("rotation_cancelled", task)
            
            logger.info(f"Rotation cancelled: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel rotation: {e}")
            return False
    
    async def rollback_rotation(
        self,
        task_id: str,
        rolled_back_by: str,
        reason: str = "Manual rollback"
    ) -> bool:
        """Rollback completed rotation"""
        try:
            task = self.rotation_tasks.get(task_id)
            if not task:
                return False
            
            if task.status != RotationStatus.COMPLETED:
                return False
            
            if not task.old_key:
                return False
            
            # Restore old key as active
            task.old_key.status = KeyStatus.ACTIVE
            self.active_keys[task.key_id] = task.old_key
            
            # Archive new key
            if task.new_key:
                task.new_key.status = KeyStatus.ARCHIVED
                await self._archive_key(task.new_key)
            
            # Update task status
            task.status = RotationStatus.ROLLBACK
            task.completed_at = datetime.now(timezone.utc)
            task.error_message = f"Rolled back by {rolled_back_by}: {reason}"
            
            await self._log_rotation_event(
                event_type="rotation_rolled_back",
                key_id=task.key_id,
                task_id=task_id,
                message=f"Rotation rolled back by {rolled_back_by}",
                details={"reason": reason}
            )
            
            # Notify callbacks
            await self._notify_rotation_callbacks("rotation_rolled_back", task)
            
            logger.info(f"Rotation rolled back: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to rollback rotation: {e}")
            return False
    
    async def _execute_rotation(self, task_id: str) -> bool:
        """Execute key rotation"""
        try:
            task = self.rotation_tasks.get(task_id)
            if not task:
                return False
            
            # Update task status
            task.status = RotationStatus.IN_PROGRESS
            task.started_at = datetime.now(timezone.utc)
            
            await self._log_rotation_event(
                event_type="rotation_started",
                key_id=task.key_id,
                task_id=task_id,
                message="Key rotation started",
                details={}
            )
            
            # Generate new key
            old_key = task.old_key
            new_key = await self._generate_new_key(old_key)
            
            if not new_key:
                task.status = RotationStatus.FAILED
                task.error_message = "Failed to generate new key"
                return False
            
            # Store rollback data
            task.rollback_data = {
                "old_key_id": old_key.key_id,
                "old_key_status": old_key.status.value,
                "new_key_id": new_key.key_id
            }
            
            # Update key history
            if task.key_id not in self.key_history:
                self.key_history[task.key_id] = []
            
            self.key_history[task.key_id].append(old_key)
            
            # Limit key history
            policy_id = old_key.metadata.get("rotation_policy", "default")
            policy = self.rotation_policies.get(policy_id)
            max_history = policy.max_key_history if policy else MAX_KEY_HISTORY
            
            if len(self.key_history[task.key_id]) > max_history:
                # Archive oldest keys
                oldest_keys = self.key_history[task.key_id][:-max_history]
                for old_key_item in oldest_keys:
                    await self._archive_key(old_key_item)
                
                self.key_history[task.key_id] = self.key_history[task.key_id][-max_history:]
            
            # Update active key
            old_key.status = KeyStatus.DEPRECATED
            new_key.status = KeyStatus.ACTIVE
            self.active_keys[task.key_id] = new_key
            
            # Update task
            task.new_key = new_key
            task.status = RotationStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            
            await self._log_rotation_event(
                event_type="rotation_completed",
                key_id=task.key_id,
                task_id=task_id,
                message="Key rotation completed successfully",
                details={
                    "old_key_id": old_key.key_id,
                    "new_key_id": new_key.key_id,
                    "rotation_count": new_key.rotation_count
                }
            )
            
            # Notify callbacks
            await self._notify_rotation_callbacks("rotation_completed", task)
            
            logger.info(f"Key rotation completed: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute rotation: {e}")
            
            # Update task status
            task = self.rotation_tasks.get(task_id)
            if task:
                task.status = RotationStatus.FAILED
                task.error_message = str(e)
                task.completed_at = datetime.now(timezone.utc)
            
            await self._log_rotation_event(
                event_type="rotation_failed",
                key_id=task.key_id if task else "",
                task_id=task_id,
                message=f"Key rotation failed: {str(e)}",
                details={"error": str(e)}
            )
            
            return False
    
    async def _generate_new_key(self, old_key: KeyInfo) -> Optional[KeyInfo]:
        """Generate new key based on old key type"""
        try:
            new_key_id = secrets.token_hex(16)
            
            # Generate new key pair based on type
            if old_key.key_type == "ed25519":
                private_key = ed25519.Ed25519PrivateKey.generate()
                public_key = private_key.public_key()
            elif old_key.key_type == "rsa":
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048,
                    backend=default_backend()
                )
                public_key = private_key.public_key()
            else:
                return None
            
            # Serialize keys
            private_key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            # Create new key info
            new_key = KeyInfo(
                key_id=new_key_id,
                key_type=old_key.key_type,
                public_key=public_key_bytes,
                private_key_encrypted=private_key_bytes,  # In real implementation, this would be encrypted
                created_at=datetime.now(timezone.utc),
                last_rotation=datetime.now(timezone.utc),
                rotation_count=old_key.rotation_count + 1,
                metadata=old_key.metadata.copy()
            )
            
            # Calculate next rotation date
            policy_id = old_key.metadata.get("rotation_policy", "default")
            policy = self.rotation_policies.get(policy_id)
            rotation_interval = policy.rotation_interval_days if policy else KEY_ROTATION_INTERVAL_DAYS
            new_key.next_rotation = datetime.now(timezone.utc) + timedelta(days=rotation_interval)
            
            return new_key
            
        except Exception as e:
            logger.error(f"Failed to generate new key: {e}")
            return None
    
    async def _archive_key(self, key: KeyInfo) -> None:
        """Archive key to history storage"""
        try:
            key.status = KeyStatus.ARCHIVED
            # In real implementation, this would store to persistent storage
            
            await self._log_rotation_event(
                event_type="key_archived",
                key_id=key.key_id,
                message=f"Key archived",
                details={"key_type": key.key_type, "rotation_count": key.rotation_count}
            )
            
        except Exception as e:
            logger.error(f"Failed to archive key: {e}")
    
    async def check_rotation_schedule(self) -> List[str]:
        """Check for keys that need rotation"""
        try:
            keys_to_rotate = []
            current_time = datetime.now(timezone.utc)
            
            for key_id, key in self.active_keys.items():
                if key.status != KeyStatus.ACTIVE:
                    continue
                
                if key.next_rotation and current_time >= key.next_rotation:
                    keys_to_rotate.append(key_id)
            
            return keys_to_rotate
            
        except Exception as e:
            logger.error(f"Failed to check rotation schedule: {e}")
            return []
    
    async def get_rotation_status(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get rotation status for key"""
        try:
            key = self.active_keys.get(key_id)
            if not key:
                return None
            
            # Find active rotation task
            active_task = None
            for task in self.rotation_tasks.values():
                if task.key_id == key_id and task.status in [RotationStatus.PENDING, RotationStatus.IN_PROGRESS]:
                    active_task = task
                    break
            
            status = {
                "key_id": key_id,
                "status": key.status.value,
                "created_at": key.created_at.isoformat(),
                "last_rotation": key.last_rotation.isoformat() if key.last_rotation else None,
                "next_rotation": key.next_rotation.isoformat() if key.next_rotation else None,
                "rotation_count": key.rotation_count,
                "usage_count": key.usage_count,
                "active_task": {
                    "task_id": active_task.task_id,
                    "status": active_task.status.value,
                    "trigger": active_task.trigger.value,
                    "created_at": active_task.created_at.isoformat(),
                    "approvers": active_task.approvers,
                    "approvals": active_task.approvals
                } if active_task else None,
                "policy": key.metadata.get("rotation_policy", "default")
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get rotation status: {e}")
            return None
    
    async def get_rotation_history(self, key_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get rotation history for key"""
        try:
            history = []
            
            # Get key history
            if key_id in self.key_history:
                for i, key in enumerate(self.key_history[key_id][-limit:]):
                    history.append({
                        "key_id": key.key_id,
                        "created_at": key.created_at.isoformat(),
                        "status": key.status.value,
                        "rotation_count": key.rotation_count,
                        "usage_count": key.usage_count,
                        "history_index": i
                    })
            
            # Get rotation tasks
            tasks = []
            for task in self.rotation_tasks.values():
                if task.key_id == key_id:
                    tasks.append(task)
            
            # Sort by creation time
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            
            for task in tasks[:limit]:
                history.append({
                    "task_id": task.task_id,
                    "created_at": task.created_at.isoformat(),
                    "status": task.status.value,
                    "trigger": task.trigger.value,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "error_message": task.error_message,
                    "type": "rotation_task"
                })
            
            # Sort combined history by timestamp
            history.sort(key=lambda h: h["created_at"], reverse=True)
            
            return history[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get rotation history: {e}")
            return []
    
    async def _log_rotation_event(
        self,
        event_type: str,
        key_id: str,
        task_id: Optional[str] = None,
        message: str = "",
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log rotation event"""
        try:
            event = RotationEvent(
                event_id=secrets.token_hex(16),
                timestamp=datetime.now(timezone.utc),
                event_type=event_type,
                key_id=key_id,
                wallet_id=self.wallet_id,
                task_id=task_id,
                message=message,
                details=details or {}
            )
            
            self.rotation_events.append(event)
            
            # Limit events in memory
            if len(self.rotation_events) > 10000:
                self.rotation_events = self.rotation_events[-5000:]
            
        except Exception as e:
            logger.error(f"Failed to log rotation event: {e}")
    
    async def _notify_rotation_callbacks(self, event_type: str, task: RotationTask) -> None:
        """Notify rotation callbacks"""
        try:
            for callback in self.rotation_callbacks:
                try:
                    await callback(event_type, task)
                except Exception as e:
                    logger.error(f"Rotation callback error: {e}")
        except Exception as e:
            logger.error(f"Failed to notify rotation callbacks: {e}")
    
    def add_rotation_callback(self, callback: Callable) -> None:
        """Add rotation callback"""
        self.rotation_callbacks.append(callback)
    
    def add_approval_callback(self, callback: Callable) -> None:
        """Add approval callback"""
        self.approval_callbacks.append(callback)
    
    def add_completion_callback(self, callback: Callable) -> None:
        """Add completion callback"""
        self.completion_callbacks.append(callback)
    
    async def get_rotation_manager_status(self) -> Dict[str, Any]:
        """Get rotation manager status"""
        return {
            "wallet_id": self.wallet_id,
            "total_policies": len(self.rotation_policies),
            "active_keys": len([k for k in self.active_keys.values() if k.status == KeyStatus.ACTIVE]),
            "rotating_keys": len([k for k in self.active_keys.values() if k.status == KeyStatus.ROTATING]),
            "pending_tasks": len([t for t in self.rotation_tasks.values() if t.status == RotationStatus.PENDING]),
            "in_progress_tasks": len([t for t in self.rotation_tasks.values() if t.status == RotationStatus.IN_PROGRESS]),
            "completed_tasks": len([t for t in self.rotation_tasks.values() if t.status == RotationStatus.COMPLETED]),
            "failed_tasks": len([t for t in self.rotation_tasks.values() if t.status == RotationStatus.FAILED]),
            "rotation_events_count": len(self.rotation_events),
            "policies": {
                policy_id: {
                    "name": policy.name,
                    "rotation_interval_days": policy.rotation_interval_days,
                    "auto_rotation_enabled": policy.auto_rotation_enabled,
                    "requires_approval": policy.requires_approval
                }
                for policy_id, policy in self.rotation_policies.items()
            }
        }


# Global rotation managers
_rotation_managers: Dict[str, KeyRotationManager] = {}


def get_rotation_manager(wallet_id: str) -> Optional[KeyRotationManager]:
    """Get rotation manager for wallet"""
    return _rotation_managers.get(wallet_id)


def create_rotation_manager(wallet_id: str) -> KeyRotationManager:
    """Create new rotation manager for wallet"""
    rotation_manager = KeyRotationManager(wallet_id)
    _rotation_managers[wallet_id] = rotation_manager
    return rotation_manager


async def main():
    """Main function for testing"""
    import asyncio
    
    # Create rotation manager
    rotation_manager = create_rotation_manager("test_wallet_001")
    
    # Create test key
    key_id = "test_key_001"
    test_key = KeyInfo(
        key_id=key_id,
        key_type="ed25519",
        public_key=b"test_public_key",
        private_key_encrypted=b"test_private_key",
        created_at=datetime.now(timezone.utc),
        metadata={"rotation_policy": "default"}
    )
    rotation_manager.active_keys[key_id] = test_key
    
    # Assign policy
    success = await rotation_manager.assign_policy_to_key(key_id, "default", "admin")
    print(f"Policy assignment: {success}")
    
    # Initiate rotation
    success, task_id = await rotation_manager.rotate_key(
        key_id=key_id,
        trigger=RotationTrigger.MANUAL,
        initiated_by="admin"
    )
    print(f"Rotation initiation: {success}, Task: {task_id}")
    
    # Get rotation status
    status = await rotation_manager.get_rotation_status(key_id)
    print(f"Rotation status: {status}")
    
    # Get rotation history
    history = await rotation_manager.get_rotation_history(key_id)
    print(f"Rotation history: {len(history)} entries")
    
    # Get manager status
    manager_status = await rotation_manager.get_rotation_manager_status()
    print(f"Manager status: {manager_status}")


if __name__ == "__main__":
    asyncio.run(main())
