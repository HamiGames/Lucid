#!/usr/bin/env python3
"""
Lucid Admin Interface - Emergency Controls
Step 23: Admin Backend APIs Implementation

Emergency control system for system lockdown, session management, and critical operations.
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import uuid

logger = logging.getLogger(__name__)


class EmergencyAction(Enum):
    """Emergency action types"""
    LOCKDOWN = "lockdown"
    STOP_ALL_SESSIONS = "stop_all_sessions"
    DISABLE_NEW_SESSIONS = "disable_new_sessions"
    ENABLE_NEW_SESSIONS = "enable_new_sessions"
    SYSTEM_SHUTDOWN = "system_shutdown"
    NODE_ISOLATION = "node_isolation"
    NETWORK_ISOLATION = "network_isolation"
    DATA_BACKUP = "data_backup"
    EMERGENCY_RESTORE = "emergency_restore"


class EmergencyStatus(Enum):
    """Emergency status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EmergencySeverity(Enum):
    """Emergency severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EmergencyControl:
    """Emergency control configuration"""
    control_id: str
    name: str
    description: str
    action: EmergencyAction
    severity: EmergencySeverity
    is_active: bool = False
    requires_approval: bool = True
    auto_revert: bool = False
    revert_after_hours: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    activated_at: Optional[datetime] = None
    activated_by: Optional[str] = None
    reverted_at: Optional[datetime] = None
    reverted_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        if self.activated_at:
            data['activated_at'] = self.activated_at.isoformat()
        if self.reverted_at:
            data['reverted_at'] = self.reverted_at.isoformat()
        data['action'] = self.action.value
        data['severity'] = self.severity.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmergencyControl':
        """Create from dictionary"""
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        if data.get('activated_at'):
            data['activated_at'] = datetime.fromisoformat(data['activated_at'].replace('Z', '+00:00'))
        if data.get('reverted_at'):
            data['reverted_at'] = datetime.fromisoformat(data['reverted_at'].replace('Z', '+00:00'))
        data['action'] = EmergencyAction(data['action'])
        data['severity'] = EmergencySeverity(data['severity'])
        return cls(**data)


@dataclass
class EmergencyEvent:
    """Emergency event log"""
    event_id: str
    control_id: str
    action: EmergencyAction
    status: EmergencyStatus
    admin_id: str
    admin_username: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['action'] = self.action.value
        data['status'] = self.status.value
        return data


class EmergencyControls:
    """
    Emergency control system for critical system operations.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.controls_collection: AsyncIOMotorCollection = db.emergency_controls
        self.events_collection: AsyncIOMotorCollection = db.emergency_events
        self.controls_indexes_created = False
        self.events_indexes_created = False
        self._setup_indexes()
        
        # Initialize default emergency controls
        self._initialize_default_controls()
    
    async def _setup_indexes(self):
        """Setup collection indexes"""
        try:
            # Controls collection indexes
            if not self.controls_indexes_created:
                await self.controls_collection.create_index("control_id", unique=True)
                await self.controls_collection.create_index("action")
                await self.controls_collection.create_index("is_active")
                await self.controls_collection.create_index("severity")
                self.controls_indexes_created = True
            
            # Events collection indexes
            if not self.events_indexes_created:
                await self.events_collection.create_index("event_id", unique=True)
                await self.events_collection.create_index("control_id")
                await self.events_collection.create_index("timestamp")
                await self.events_collection.create_index("admin_id")
                await self.events_collection.create_index("status")
                await self.events_collection.create_index([("timestamp", -1), ("action", 1)])
                self.events_indexes_created = True
            
            logger.info("Emergency controls indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to create emergency controls indexes: {e}")
    
    async def _initialize_default_controls(self):
        """Initialize default emergency controls"""
        try:
            default_controls = [
                EmergencyControl(
                    control_id="lockdown_system",
                    name="System Lockdown",
                    description="Complete system lockdown - disable all operations",
                    action=EmergencyAction.LOCKDOWN,
                    severity=EmergencySeverity.CRITICAL,
                    requires_approval=True,
                    auto_revert=True,
                    revert_after_hours=24
                ),
                EmergencyControl(
                    control_id="stop_all_sessions",
                    name="Stop All Sessions",
                    description="Immediately terminate all active user sessions",
                    action=EmergencyAction.STOP_ALL_SESSIONS,
                    severity=EmergencySeverity.HIGH,
                    requires_approval=True,
                    auto_revert=False
                ),
                EmergencyControl(
                    control_id="disable_new_sessions",
                    name="Disable New Sessions",
                    description="Prevent new user sessions from being created",
                    action=EmergencyAction.DISABLE_NEW_SESSIONS,
                    severity=EmergencySeverity.MEDIUM,
                    requires_approval=False,
                    auto_revert=True,
                    revert_after_hours=12
                ),
                EmergencyControl(
                    control_id="enable_new_sessions",
                    name="Enable New Sessions",
                    description="Re-enable new user session creation",
                    action=EmergencyAction.ENABLE_NEW_SESSIONS,
                    severity=EmergencySeverity.LOW,
                    requires_approval=False,
                    auto_revert=False
                ),
                EmergencyControl(
                    control_id="system_shutdown",
                    name="System Shutdown",
                    description="Emergency system shutdown",
                    action=EmergencyAction.SYSTEM_SHUTDOWN,
                    severity=EmergencySeverity.CRITICAL,
                    requires_approval=True,
                    auto_revert=False
                ),
                EmergencyControl(
                    control_id="data_backup",
                    name="Emergency Data Backup",
                    description="Create emergency data backup",
                    action=EmergencyAction.DATA_BACKUP,
                    severity=EmergencySeverity.HIGH,
                    requires_approval=False,
                    auto_revert=False
                )
            ]
            
            for control in default_controls:
                existing = await self.controls_collection.find_one({"control_id": control.control_id})
                if not existing:
                    await self.controls_collection.insert_one(control.to_dict())
                    logger.info(f"Initialized emergency control: {control.control_id}")
        
        except Exception as e:
            logger.error(f"Failed to initialize default emergency controls: {e}")
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        return f"emergency_{uuid.uuid4().hex[:12]}"
    
    def _generate_correlation_id(self) -> str:
        """Generate correlation ID for related events"""
        return f"emergency_corr_{uuid.uuid4().hex[:8]}"
    
    async def _log_emergency_event(
        self,
        control_id: str,
        action: EmergencyAction,
        status: EmergencyStatus,
        admin_id: str,
        admin_username: str,
        details: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> str:
        """Log emergency event"""
        try:
            event_id = self._generate_event_id()
            if not correlation_id:
                correlation_id = self._generate_correlation_id()
            
            event = EmergencyEvent(
                event_id=event_id,
                control_id=control_id,
                action=action,
                status=status,
                admin_id=admin_id,
                admin_username=admin_username,
                timestamp=datetime.now(timezone.utc),
                details=details or {},
                error_message=error_message,
                correlation_id=correlation_id
            )
            
            await self.events_collection.insert_one(event.to_dict())
            logger.info(f"Emergency event logged: {event_id} - {action.value} - {status.value}")
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to log emergency event: {e}")
            raise
    
    async def get_emergency_controls(self) -> List[Dict[str, Any]]:
        """Get all emergency controls"""
        try:
            cursor = self.controls_collection.find({}).sort("severity", 1)
            controls = await cursor.to_list(length=None)
            return controls
        except Exception as e:
            logger.error(f"Failed to get emergency controls: {e}")
            raise
    
    async def get_emergency_control(self, control_id: str) -> Optional[Dict[str, Any]]:
        """Get specific emergency control"""
        try:
            control = await self.controls_collection.find_one({"control_id": control_id})
            return control
        except Exception as e:
            logger.error(f"Failed to get emergency control {control_id}: {e}")
            raise
    
    async def activate_emergency_control(
        self,
        control_id: str,
        admin_id: str,
        admin_username: str,
        force: bool = False,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Activate emergency control"""
        try:
            control_data = await self.get_emergency_control(control_id)
            if not control_data:
                raise ValueError(f"Emergency control {control_id} not found")
            
            control = EmergencyControl.from_dict(control_data)
            
            # Check if already active
            if control.is_active:
                return {"status": "already_active", "message": f"Control {control_id} is already active"}
            
            # Check approval requirement
            if control.requires_approval and not force:
                return {"status": "approval_required", "message": f"Control {control_id} requires approval"}
            
            # Activate control
            control.is_active = True
            control.activated_at = datetime.now(timezone.utc)
            control.activated_by = admin_id
            
            await self.controls_collection.update_one(
                {"control_id": control_id},
                {"$set": control.to_dict()}
            )
            
            # Log event
            await self._log_emergency_event(
                control_id=control_id,
                action=control.action,
                status=EmergencyStatus.ACTIVE,
                admin_id=admin_id,
                admin_username=admin_username,
                details=details
            )
            
            # Execute control action
            await self._execute_emergency_action(control, admin_id, admin_username, details)
            
            logger.warning(f"Emergency control activated: {control_id} by {admin_username}")
            return {"status": "activated", "message": f"Control {control_id} activated successfully"}
            
        except Exception as e:
            logger.error(f"Failed to activate emergency control {control_id}: {e}")
            await self._log_emergency_event(
                control_id=control_id,
                action=EmergencyAction.LOCKDOWN,  # Default action
                status=EmergencyStatus.FAILED,
                admin_id=admin_id,
                admin_username=admin_username,
                error_message=str(e)
            )
            raise
    
    async def deactivate_emergency_control(
        self,
        control_id: str,
        admin_id: str,
        admin_username: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Deactivate emergency control"""
        try:
            control_data = await self.get_emergency_control(control_id)
            if not control_data:
                raise ValueError(f"Emergency control {control_id} not found")
            
            control = EmergencyControl.from_dict(control_data)
            
            # Check if already inactive
            if not control.is_active:
                return {"status": "already_inactive", "message": f"Control {control_id} is already inactive"}
            
            # Deactivate control
            control.is_active = False
            control.reverted_at = datetime.now(timezone.utc)
            control.reverted_by = admin_id
            
            await self.controls_collection.update_one(
                {"control_id": control_id},
                {"$set": control.to_dict()}
            )
            
            # Log event
            await self._log_emergency_event(
                control_id=control_id,
                action=control.action,
                status=EmergencyStatus.INACTIVE,
                admin_id=admin_id,
                admin_username=admin_username,
                details=details
            )
            
            # Execute deactivation action
            await self._execute_emergency_deactivation(control, admin_id, admin_username, details)
            
            logger.info(f"Emergency control deactivated: {control_id} by {admin_username}")
            return {"status": "deactivated", "message": f"Control {control_id} deactivated successfully"}
            
        except Exception as e:
            logger.error(f"Failed to deactivate emergency control {control_id}: {e}")
            raise
    
    async def _execute_emergency_action(
        self,
        control: EmergencyControl,
        admin_id: str,
        admin_username: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Execute emergency action"""
        try:
            if control.action == EmergencyAction.LOCKDOWN:
                await self._execute_lockdown(admin_id, admin_username, details)
            elif control.action == EmergencyAction.STOP_ALL_SESSIONS:
                await self._execute_stop_all_sessions(admin_id, admin_username, details)
            elif control.action == EmergencyAction.DISABLE_NEW_SESSIONS:
                await self._execute_disable_new_sessions(admin_id, admin_username, details)
            elif control.action == EmergencyAction.ENABLE_NEW_SESSIONS:
                await self._execute_enable_new_sessions(admin_id, admin_username, details)
            elif control.action == EmergencyAction.SYSTEM_SHUTDOWN:
                await self._execute_system_shutdown(admin_id, admin_username, details)
            elif control.action == EmergencyAction.DATA_BACKUP:
                await self._execute_data_backup(admin_id, admin_username, details)
            else:
                logger.warning(f"Unknown emergency action: {control.action}")
        
        except Exception as e:
            logger.error(f"Failed to execute emergency action {control.action}: {e}")
            raise
    
    async def _execute_emergency_deactivation(
        self,
        control: EmergencyControl,
        admin_id: str,
        admin_username: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Execute emergency deactivation"""
        try:
            if control.action == EmergencyAction.LOCKDOWN:
                await self._execute_lockdown_revert(admin_id, admin_username, details)
            elif control.action == EmergencyAction.DISABLE_NEW_SESSIONS:
                await self._execute_enable_new_sessions(admin_id, admin_username, details)
            # Other actions may not have specific deactivation logic
            else:
                logger.info(f"No specific deactivation for action: {control.action}")
        
        except Exception as e:
            logger.error(f"Failed to execute emergency deactivation {control.action}: {e}")
            raise
    
    async def _execute_lockdown(self, admin_id: str, admin_username: str, details: Optional[Dict[str, Any]] = None):
        """Execute system lockdown"""
        logger.critical(f"SYSTEM LOCKDOWN INITIATED by {admin_username}")
        # TODO: Implement actual lockdown logic
        # - Disable all user sessions
        # - Disable new session creation
        # - Disable non-critical services
        # - Enable only emergency access
        pass
    
    async def _execute_lockdown_revert(self, admin_id: str, admin_username: str, details: Optional[Dict[str, Any]] = None):
        """Revert system lockdown"""
        logger.info(f"SYSTEM LOCKDOWN REVERTED by {admin_username}")
        # TODO: Implement lockdown revert logic
        pass
    
    async def _execute_stop_all_sessions(self, admin_id: str, admin_username: str, details: Optional[Dict[str, Any]] = None):
        """Execute stop all sessions"""
        logger.warning(f"STOPPING ALL SESSIONS by {admin_username}")
        # TODO: Implement session termination logic
        # - Get all active sessions
        # - Terminate each session
        # - Log termination events
        pass
    
    async def _execute_disable_new_sessions(self, admin_id: str, admin_username: str, details: Optional[Dict[str, Any]] = None):
        """Execute disable new sessions"""
        logger.warning(f"DISABLING NEW SESSIONS by {admin_username}")
        # TODO: Implement session creation disable logic
        # - Set global flag to prevent new sessions
        # - Update session manager configuration
        pass
    
    async def _execute_enable_new_sessions(self, admin_id: str, admin_username: str, details: Optional[Dict[str, Any]] = None):
        """Execute enable new sessions"""
        logger.info(f"ENABLING NEW SESSIONS by {admin_username}")
        # TODO: Implement session creation enable logic
        # - Clear global flag to allow new sessions
        # - Update session manager configuration
        pass
    
    async def _execute_system_shutdown(self, admin_id: str, admin_username: str, details: Optional[Dict[str, Any]] = None):
        """Execute system shutdown"""
        logger.critical(f"EMERGENCY SYSTEM SHUTDOWN INITIATED by {admin_username}")
        # TODO: Implement system shutdown logic
        # - Graceful shutdown of services
        # - Data backup before shutdown
        # - System halt
        pass
    
    async def _execute_data_backup(self, admin_id: str, admin_username: str, details: Optional[Dict[str, Any]] = None):
        """Execute emergency data backup"""
        logger.warning(f"EMERGENCY DATA BACKUP INITIATED by {admin_username}")
        # TODO: Implement emergency backup logic
        # - Create full system backup
        # - Store in secure location
        # - Verify backup integrity
        pass
    
    async def get_emergency_status(self) -> Dict[str, Any]:
        """Get current emergency status"""
        try:
            active_controls = await self.controls_collection.find({"is_active": True}).to_list(length=None)
            
            status = {
                "is_locked_down": False,
                "new_sessions_enabled": True,
                "active_controls": len(active_controls),
                "controls": []
            }
            
            for control_data in active_controls:
                control = EmergencyControl.from_dict(control_data)
                status["controls"].append({
                    "control_id": control.control_id,
                    "name": control.name,
                    "action": control.action.value,
                    "severity": control.severity.value,
                    "activated_at": control.activated_at.isoformat() if control.activated_at else None,
                    "activated_by": control.activated_by
                })
                
                if control.action == EmergencyAction.LOCKDOWN:
                    status["is_locked_down"] = True
                elif control.action == EmergencyAction.DISABLE_NEW_SESSIONS:
                    status["new_sessions_enabled"] = False
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get emergency status: {e}")
            raise
    
    async def get_emergency_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        control_id: Optional[str] = None,
        admin_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get emergency events"""
        try:
            query = {}
            
            if start_time or end_time:
                time_filter = {}
                if start_time:
                    time_filter["$gte"] = start_time
                if end_time:
                    time_filter["$lte"] = end_time
                query["timestamp"] = time_filter
            
            if control_id:
                query["control_id"] = control_id
            
            if admin_id:
                query["admin_id"] = admin_id
            
            # Get total count
            total = await self.events_collection.count_documents(query)
            
            # Get events
            cursor = self.events_collection.find(query).sort("timestamp", -1).skip(offset).limit(limit)
            events = await cursor.to_list(length=limit)
            
            return {
                "events": events,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Failed to get emergency events: {e}")
            raise
    
    async def check_auto_revert(self):
        """Check and execute auto-revert for controls"""
        try:
            current_time = datetime.now(timezone.utc)
            controls = await self.controls_collection.find({
                "is_active": True,
                "auto_revert": True,
                "revert_after_hours": {"$exists": True, "$ne": None}
            }).to_list(length=None)
            
            for control_data in controls:
                control = EmergencyControl.from_dict(control_data)
                if control.activated_at and control.revert_after_hours:
                    revert_time = control.activated_at + timedelta(hours=control.revert_after_hours)
                    if current_time >= revert_time:
                        logger.info(f"Auto-reverting control: {control.control_id}")
                        await self.deactivate_emergency_control(
                            control.control_id,
                            "system",
                            "auto_revert",
                            {"reason": "auto_revert", "revert_time": revert_time.isoformat()}
                        )
        
        except Exception as e:
            logger.error(f"Failed to check auto-revert: {e}")


# Dependency for FastAPI
async def get_emergency_controls() -> EmergencyControls:
    """Get emergency controls instance"""
    from admin.system.admin_controller import get_admin_controller
    return EmergencyControls(get_admin_controller().db)


if __name__ == "__main__":
    # Test emergency controls
    print("Emergency Controls System")
    print("========================")
    
    # Test action types
    print("Emergency Actions:")
    for action in EmergencyAction:
        print(f"  {action.value}")
    
    print("\nEmergency Status:")
    for status in EmergencyStatus:
        print(f"  {status.value}")
    
    print("\nSeverity Levels:")
    for severity in EmergencySeverity:
        print(f"  {severity.value}")
    
    print("\nEmergency Controls initialized successfully")