#!/usr/bin/env python3
"""
Lucid Admin Interface - Audit Logging System
Step 23: Admin Backend APIs Implementation

Comprehensive audit logging system for administrative actions and security events.
"""

import logging
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
import hashlib
import uuid

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Audit event types"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    USER_MANAGEMENT = "user_management"
    SESSION_MANAGEMENT = "session_management"
    BLOCKCHAIN_OPERATION = "blockchain_operation"
    NODE_MANAGEMENT = "node_management"
    SYSTEM_CONFIGURATION = "system_configuration"
    EMERGENCY_ACTION = "emergency_action"
    SECURITY_EVENT = "security_event"
    DATA_ACCESS = "data_access"
    POLICY_CHANGE = "policy_change"
    KEY_ROTATION = "key_rotation"
    GOVERNANCE = "governance"


class AuditEventSeverity(Enum):
    """Audit event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditEventStatus(Enum):
    """Audit event status"""
    SUCCESS = "success"
    FAILURE = "failure"
    PENDING = "pending"
    CANCELLED = "cancelled"


@dataclass
class AuditEvent:
    """Audit event data structure"""
    event_id: str
    timestamp: datetime
    event_type: AuditEventType
    severity: AuditEventSeverity
    status: AuditEventStatus
    admin_id: str
    admin_username: str
    action: str
    resource: str
    resource_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['created_at'] = self.created_at.isoformat()
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditEvent':
        """Create from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
        data['created_at'] = datetime.fromisoformat(data['created_at'].replace('Z', '+00:00'))
        data['event_type'] = AuditEventType(data['event_type'])
        data['severity'] = AuditEventSeverity(data['severity'])
        data['status'] = AuditEventStatus(data['status'])
        return cls(**data)


class AuditLogger:
    """
    Comprehensive audit logging system for administrative actions and security events.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.audit_collection: AsyncIOMotorCollection = db.audit_events
        self.audit_indexes_created = False
        self._setup_audit_indexes()
    
    async def _setup_audit_indexes(self):
        """Setup audit collection indexes"""
        if self.audit_indexes_created:
            return
        
        try:
            # Create indexes for efficient querying
            await self.audit_collection.create_index("timestamp")
            await self.audit_collection.create_index("event_type")
            await self.audit_collection.create_index("admin_id")
            await self.audit_collection.create_index("severity")
            await self.audit_collection.create_index("status")
            await self.audit_collection.create_index("resource")
            await self.audit_collection.create_index("correlation_id")
            await self.audit_collection.create_index([("timestamp", -1), ("event_type", 1)])
            await self.audit_collection.create_index([("admin_id", 1), ("timestamp", -1)])
            
            # TTL index for automatic cleanup (retain for 1 year)
            await self.audit_collection.create_index("created_at", expireAfterSeconds=365*24*60*60)
            
            self.audit_indexes_created = True
            logger.info("Audit collection indexes created successfully")
        except Exception as e:
            logger.error(f"Failed to create audit indexes: {e}")
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        return f"audit_{uuid.uuid4().hex[:12]}"
    
    def _generate_correlation_id(self) -> str:
        """Generate correlation ID for related events"""
        return f"corr_{uuid.uuid4().hex[:8]}"
    
    async def log_event(
        self,
        event_type: AuditEventType,
        severity: AuditEventSeverity,
        status: AuditEventStatus,
        admin_id: str,
        admin_username: str,
        action: str,
        resource: str,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Log an audit event
        
        Args:
            event_type: Type of audit event
            severity: Severity level
            status: Event status
            admin_id: Admin user ID
            admin_username: Admin username
            action: Action performed
            resource: Resource affected
            resource_id: ID of the resource
            details: Additional event details
            ip_address: Client IP address
            user_agent: Client user agent
            session_id: Session ID
            correlation_id: Correlation ID for related events
            tags: Event tags
        
        Returns:
            Event ID
        """
        try:
            event_id = self._generate_event_id()
            if not correlation_id:
                correlation_id = self._generate_correlation_id()
            
            event = AuditEvent(
                event_id=event_id,
                timestamp=datetime.now(timezone.utc),
                event_type=event_type,
                severity=severity,
                status=status,
                admin_id=admin_id,
                admin_username=admin_username,
                action=action,
                resource=resource,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                correlation_id=correlation_id,
                tags=tags or []
            )
            
            await self.audit_collection.insert_one(event.to_dict())
            
            logger.info(f"Audit event logged: {event_id} - {action} on {resource}")
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            raise
    
    async def log_authentication(
        self,
        admin_id: str,
        admin_username: str,
        action: str,
        status: AuditEventStatus,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log authentication events"""
        severity = AuditEventSeverity.HIGH if status == AuditEventStatus.FAILURE else AuditEventSeverity.MEDIUM
        return await self.log_event(
            event_type=AuditEventType.AUTHENTICATION,
            severity=severity,
            status=status,
            admin_id=admin_id,
            admin_username=admin_username,
            action=action,
            resource="authentication",
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    async def log_user_management(
        self,
        admin_id: str,
        admin_username: str,
        action: str,
        target_user_id: str,
        target_username: str,
        status: AuditEventStatus,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log user management events"""
        severity = AuditEventSeverity.HIGH if action in ["create", "suspend", "activate"] else AuditEventSeverity.MEDIUM
        return await self.log_event(
            event_type=AuditEventType.USER_MANAGEMENT,
            severity=severity,
            status=status,
            admin_id=admin_id,
            admin_username=admin_username,
            action=action,
            resource="user",
            resource_id=target_user_id,
            details={**details or {}, "target_username": target_username}
        )
    
    async def log_session_management(
        self,
        admin_id: str,
        admin_username: str,
        action: str,
        session_id: str,
        target_user_id: Optional[str] = None,
        status: AuditEventStatus,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log session management events"""
        severity = AuditEventSeverity.MEDIUM if action == "terminate" else AuditEventSeverity.LOW
        return await self.log_event(
            event_type=AuditEventType.SESSION_MANAGEMENT,
            severity=severity,
            status=status,
            admin_id=admin_id,
            admin_username=admin_username,
            action=action,
            resource="session",
            resource_id=session_id,
            details={**details or {}, "target_user_id": target_user_id}
        )
    
    async def log_blockchain_operation(
        self,
        admin_id: str,
        admin_username: str,
        action: str,
        status: AuditEventStatus,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log blockchain operations"""
        severity = AuditEventSeverity.HIGH if action in ["resync", "anchor"] else AuditEventSeverity.MEDIUM
        return await self.log_event(
            event_type=AuditEventType.BLOCKCHAIN_OPERATION,
            severity=severity,
            status=status,
            admin_id=admin_id,
            admin_username=admin_username,
            action=action,
            resource="blockchain",
            details=details
        )
    
    async def log_node_management(
        self,
        admin_id: str,
        admin_username: str,
        action: str,
        node_id: str,
        status: AuditEventStatus,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log node management events"""
        severity = AuditEventSeverity.HIGH if action in ["restart", "maintenance"] else AuditEventSeverity.MEDIUM
        return await self.log_event(
            event_type=AuditEventType.NODE_MANAGEMENT,
            severity=severity,
            status=status,
            admin_id=admin_id,
            admin_username=admin_username,
            action=action,
            resource="node",
            resource_id=node_id,
            details=details
        )
    
    async def log_emergency_action(
        self,
        admin_id: str,
        admin_username: str,
        action: str,
        status: AuditEventStatus,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log emergency actions"""
        return await self.log_event(
            event_type=AuditEventType.EMERGENCY_ACTION,
            severity=AuditEventSeverity.CRITICAL,
            status=status,
            admin_id=admin_id,
            admin_username=admin_username,
            action=action,
            resource="system",
            details=details
        )
    
    async def log_security_event(
        self,
        admin_id: str,
        admin_username: str,
        action: str,
        severity: AuditEventSeverity,
        status: AuditEventStatus,
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log security events"""
        return await self.log_event(
            event_type=AuditEventType.SECURITY_EVENT,
            severity=severity,
            status=status,
            admin_id=admin_id,
            admin_username=admin_username,
            action=action,
            resource="security",
            details=details
        )
    
    async def get_audit_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_types: Optional[List[AuditEventType]] = None,
        severities: Optional[List[AuditEventSeverity]] = None,
        admin_id: Optional[str] = None,
        resource: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get audit events with filtering"""
        try:
            query = {}
            
            if start_time or end_time:
                time_filter = {}
                if start_time:
                    time_filter["$gte"] = start_time
                if end_time:
                    time_filter["$lte"] = end_time
                query["timestamp"] = time_filter
            
            if event_types:
                query["event_type"] = {"$in": [et.value for et in event_types]}
            
            if severities:
                query["severity"] = {"$in": [s.value for s in severities]}
            
            if admin_id:
                query["admin_id"] = admin_id
            
            if resource:
                query["resource"] = resource
            
            if correlation_id:
                query["correlation_id"] = correlation_id
            
            # Get total count
            total = await self.audit_collection.count_documents(query)
            
            # Get events
            cursor = self.audit_collection.find(query).sort("timestamp", -1).skip(offset).limit(limit)
            events = await cursor.to_list(length=limit)
            
            return {
                "events": events,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Failed to get audit events: {e}")
            raise
    
    async def get_audit_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get audit summary statistics"""
        try:
            if not start_time:
                start_time = datetime.now(timezone.utc) - timedelta(days=7)
            if not end_time:
                end_time = datetime.now(timezone.utc)
            
            pipeline = [
                {"$match": {"timestamp": {"$gte": start_time, "$lte": end_time}}},
                {"$group": {
                    "_id": None,
                    "total_events": {"$sum": 1},
                    "by_type": {"$push": {"type": "$event_type", "severity": "$severity"}},
                    "by_severity": {"$push": "$severity"},
                    "by_status": {"$push": "$status"}
                }}
            ]
            
            result = await self.audit_collection.aggregate(pipeline).to_list(1)
            
            if not result:
                return {"total_events": 0, "by_type": {}, "by_severity": {}, "by_status": {}}
            
            data = result[0]
            
            # Process by type
            by_type = {}
            for item in data.get("by_type", []):
                event_type = item["type"]
                if event_type not in by_type:
                    by_type[event_type] = 0
                by_type[event_type] += 1
            
            # Process by severity
            by_severity = {}
            for severity in data.get("by_severity", []):
                by_severity[severity] = by_severity.get(severity, 0) + 1
            
            # Process by status
            by_status = {}
            for status in data.get("by_status", []):
                by_status[status] = by_status.get(status, 0) + 1
            
            return {
                "total_events": data.get("total_events", 0),
                "by_type": by_type,
                "by_severity": by_severity,
                "by_status": by_status,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get audit summary: {e}")
            raise
    
    async def export_audit_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_types: Optional[List[AuditEventType]] = None,
        format: str = "json"
    ) -> Union[str, Dict[str, Any]]:
        """Export audit events"""
        try:
            events_data = await self.get_audit_events(
                start_time=start_time,
                end_time=end_time,
                event_types=event_types,
                limit=10000  # Large limit for export
            )
            
            if format == "json":
                return {
                    "export_timestamp": datetime.now(timezone.utc).isoformat(),
                    "time_range": {
                        "start": start_time.isoformat() if start_time else None,
                        "end": end_time.isoformat() if end_time else None
                    },
                    "event_types": [et.value for et in event_types] if event_types else None,
                    "total_events": events_data["total"],
                    "events": events_data["events"]
                }
            elif format == "csv":
                # TODO: Implement CSV export
                raise NotImplementedError("CSV export not yet implemented")
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            logger.error(f"Failed to export audit events: {e}")
            raise
    
    async def cleanup_old_events(self, days_to_keep: int = 365) -> int:
        """Cleanup old audit events"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            result = await self.audit_collection.delete_many({"created_at": {"$lt": cutoff_date}})
            logger.info(f"Cleaned up {result.deleted_count} old audit events")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Failed to cleanup old audit events: {e}")
            raise


# Dependency for FastAPI
async def get_audit_logger() -> AuditLogger:
    """Get audit logger instance"""
    from admin.system.admin_controller import get_admin_controller
    return AuditLogger(get_admin_controller().db)


if __name__ == "__main__":
    # Test audit logger
    print("Audit Logger System")
    print("==================")
    
    # Test event types
    print("Event Types:")
    for event_type in AuditEventType:
        print(f"  {event_type.value}")
    
    print("\nSeverity Levels:")
    for severity in AuditEventSeverity:
        print(f"  {severity.value}")
    
    print("\nStatus Types:")
    for status in AuditEventStatus:
        print(f"  {status.value}")
    
    print("\nAudit Logger initialized successfully")