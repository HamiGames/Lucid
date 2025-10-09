# Path: sessions/recorder/audit_trail.py
# Lucid RDP Session Audit Trail - Session audit logging
# Implements R-MUST-005: Session Audit Trail with actor identity, timestamps, resource access
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import os
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import uuid
import hashlib
import threading
import structlog

# Database imports
try:
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False
    AsyncIOMotorClient = None
    AsyncIOMotorDatabase = None

logger = logging.getLogger(__name__)

# Configuration from environment
AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "/var/log/lucid/audit"))
AUDIT_SESSIONS_PATH = Path(os.getenv("AUDIT_SESSIONS_PATH", "/var/log/lucid/sessions"))
AUDIT_KEYSTROKES_PATH = Path(os.getenv("AUDIT_KEYSTROKES_PATH", "/var/log/lucid/keystrokes"))
AUDIT_WINDOWS_PATH = Path(os.getenv("AUDIT_WINDOWS_PATH", "/var/log/lucid/windows"))
AUDIT_RESOURCES_PATH = Path(os.getenv("AUDIT_RESOURCES_PATH", "/var/log/lucid/resources"))
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://lucid:lucid@lucid_mongo:27017/lucid?authSource=admin")


class AuditEventType(Enum):
    """Types of audit events"""
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    SESSION_PAUSE = "session_pause"
    SESSION_RESUME = "session_resume"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    RDP_CONNECT = "rdp_connect"
    RDP_DISCONNECT = "rdp_disconnect"
    RESOURCE_ACCESS = "resource_access"
    RESOURCE_DENIED = "resource_denied"
    KEYSTROKE = "keystroke"
    WINDOW_FOCUS = "window_focus"
    WINDOW_OPEN = "window_open"
    WINDOW_CLOSE = "window_close"
    FILE_ACCESS = "file_access"
    CLIPBOARD_ACCESS = "clipboard_access"
    NETWORK_ACCESS = "network_access"
    SYSTEM_COMMAND = "system_command"
    SECURITY_VIOLATION = "security_violation"
    POLICY_VIOLATION = "policy_violation"


class AuditSeverity(Enum):
    """Audit event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event data structure"""
    event_id: str
    session_id: str
    timestamp: datetime
    event_type: AuditEventType
    actor_identity: str
    actor_type: str  # user, system, service, etc.
    resource_accessed: Optional[str] = None
    action_performed: Optional[str] = None
    result: str = "success"  # success, failure, denied, error
    severity: AuditSeverity = AuditSeverity.INFO
    source_address: Optional[str] = None
    target_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "actor_identity": self.actor_identity,
            "actor_type": self.actor_type,
            "resource_accessed": self.resource_accessed,
            "action_performed": self.action_performed,
            "result": self.result,
            "severity": self.severity.value,
            "source_address": self.source_address,
            "target_address": self.target_address,
            "user_agent": self.user_agent,
            "session_data": self.session_data,
            "metadata": self.metadata,
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AuditEvent:
        """Create from dictionary"""
        return cls(
            event_id=data["event_id"],
            session_id=data["session_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=AuditEventType(data["event_type"]),
            actor_identity=data["actor_identity"],
            actor_type=data["actor_type"],
            resource_accessed=data.get("resource_accessed"),
            action_performed=data.get("action_performed"),
            result=data.get("result", "success"),
            severity=AuditSeverity(data.get("severity", "info")),
            source_address=data.get("source_address"),
            target_address=data.get("target_address"),
            user_agent=data.get("user_agent"),
            session_data=data.get("session_data"),
            metadata=data.get("metadata", {}),
            hash=data.get("hash")
        )


@dataclass
class AuditTrailConfig:
    """Audit trail configuration"""
    session_id: str
    enabled: bool = True
    log_level: str = "INFO"
    compress_logs: bool = True
    encrypt_logs: bool = True
    retention_days: int = 90
    max_events_per_session: int = 10000
    batch_size: int = 100
    flush_interval_seconds: int = 30
    include_keystrokes: bool = True
    include_window_focus: bool = True
    include_resource_access: bool = True
    include_network_events: bool = True
    sensitive_data_masking: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class AuditTrailLogger:
    """
    Session audit trail logger for Lucid RDP.
    
    Provides:
    - Comprehensive event logging and tracking
    - Actor identity and timestamp recording
    - Resource access monitoring
    - Security violation detection
    - Data integrity and tamper protection
    - Real-time event streaming
    """
    
    def __init__(self, config: AuditTrailConfig):
        self.config = config
        self.is_enabled = config.enabled
        
        # Database connection
        self.db_client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        
        # Event storage
        self.event_buffer: List[AuditEvent] = []
        self.event_callbacks: List[Callable] = []
        
        # Threading
        self.flush_thread: Optional[threading.Thread] = None
        self.flush_running = False
        
        # Statistics
        self.event_count = 0
        self.error_count = 0
        
        # Create required directories
        self._create_directories()
        
        # Setup structured logging
        self._setup_logging()
        
        logger.info(f"Audit Trail Logger initialized for session: {config.session_id}")
    
    def _create_directories(self) -> None:
        """Create required directories for audit logging"""
        directories = [
            AUDIT_LOG_PATH,
            AUDIT_SESSIONS_PATH,
            AUDIT_KEYSTROKES_PATH,
            AUDIT_WINDOWS_PATH,
            AUDIT_RESOURCES_PATH,
            AUDIT_LOG_PATH / self.config.session_id,
            AUDIT_SESSIONS_PATH / self.config.session_id,
            AUDIT_KEYSTROKES_PATH / self.config.session_id,
            AUDIT_WINDOWS_PATH / self.config.session_id,
            AUDIT_RESOURCES_PATH / self.config.session_id
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {directory}")
    
    def _setup_logging(self) -> None:
        """Setup structured logging"""
        try:
            # Configure structlog
            structlog.configure(
                processors=[
                    structlog.stdlib.filter_by_level,
                    structlog.stdlib.add_logger_name,
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.PositionalArgumentsFormatter(),
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.StackInfoRenderer(),
                    structlog.processors.format_exc_info,
                    structlog.processors.UnicodeDecoder(),
                    structlog.processors.JSONRenderer()
                ],
                context_class=dict,
                logger_factory=structlog.stdlib.LoggerFactory(),
                wrapper_class=structlog.stdlib.BoundLogger,
                cache_logger_on_first_use=True,
            )
            
            # Create session-specific logger
            self.session_logger = structlog.get_logger(f"audit_trail_{self.config.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to setup structured logging: {e}")
            self.session_logger = logger
    
    async def start(self) -> bool:
        """Start the audit trail logger"""
        try:
            if not self.is_enabled:
                logger.info("Audit trail logger disabled")
                return True
            
            logger.info("Starting Audit Trail Logger...")
            
            # Connect to database
            await self._connect_database()
            
            # Start flush thread
            await self._start_flush_thread()
            
            # Log session start
            await self.log_event(
                event_type=AuditEventType.SESSION_START,
                actor_identity="system",
                actor_type="system",
                action_performed="audit_trail_started",
                metadata={"config": self.config.metadata}
            )
            
            logger.info("Audit Trail Logger started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Audit Trail Logger: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the audit trail logger"""
        try:
            logger.info("Stopping Audit Trail Logger...")
            
            # Log session end
            await self.log_event(
                event_type=AuditEventType.SESSION_END,
                actor_identity="system",
                actor_type="system",
                action_performed="audit_trail_stopped",
                metadata={"event_count": self.event_count, "error_count": self.error_count}
            )
            
            # Flush remaining events
            await self._flush_events()
            
            # Stop flush thread
            await self._stop_flush_thread()
            
            # Disconnect from database
            await self._disconnect_database()
            
            logger.info("Audit Trail Logger stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop Audit Trail Logger: {e}")
            return False
    
    async def log_event(
        self,
        event_type: AuditEventType,
        actor_identity: str,
        actor_type: str = "user",
        resource_accessed: Optional[str] = None,
        action_performed: Optional[str] = None,
        result: str = "success",
        severity: AuditSeverity = AuditSeverity.INFO,
        source_address: Optional[str] = None,
        target_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log an audit event"""
        try:
            if not self.is_enabled:
                return ""
            
            # Generate event ID
            event_id = str(uuid.uuid4())
            
            # Create audit event
            event = AuditEvent(
                event_id=event_id,
                session_id=self.config.session_id,
                timestamp=datetime.now(timezone.utc),
                event_type=event_type,
                actor_identity=actor_identity,
                actor_type=actor_type,
                resource_accessed=resource_accessed,
                action_performed=action_performed,
                result=result,
                severity=severity,
                source_address=source_address,
                target_address=target_address,
                user_agent=user_agent,
                session_data=session_data,
                metadata=metadata or {}
            )
            
            # Calculate event hash for integrity
            event.hash = self._calculate_event_hash(event)
            
            # Add to buffer
            self.event_buffer.append(event)
            self.event_count += 1
            
            # Check buffer size
            if len(self.event_buffer) >= self.config.batch_size:
                await self._flush_events()
            
            # Log to structured logger
            self.session_logger.info(
                "audit_event",
                event_id=event_id,
                event_type=event_type.value,
                actor_identity=actor_identity,
                actor_type=actor_type,
                resource_accessed=resource_accessed,
                action_performed=action_performed,
                result=result,
                severity=severity.value
            )
            
            # Notify callbacks
            await self._notify_callbacks("audit_event", event)
            
            return event_id
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            self.error_count += 1
            return ""
    
    async def log_resource_access(
        self,
        resource_type: str,
        resource_path: str,
        action: str,
        actor_identity: str,
        result: str = "success",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log resource access event"""
        return await self.log_event(
            event_type=AuditEventType.RESOURCE_ACCESS,
            actor_identity=actor_identity,
            actor_type="user",
            resource_accessed=f"{resource_type}:{resource_path}",
            action_performed=action,
            result=result,
            severity=AuditSeverity.INFO,
            metadata=metadata
        )
    
    async def log_security_violation(
        self,
        violation_type: str,
        actor_identity: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log security violation"""
        return await self.log_event(
            event_type=AuditEventType.SECURITY_VIOLATION,
            actor_identity=actor_identity,
            actor_type="user",
            action_performed=violation_type,
            result="failure",
            severity=AuditSeverity.CRITICAL,
            metadata=dict(metadata or {}, description=description)
        )
    
    async def log_policy_violation(
        self,
        policy_name: str,
        actor_identity: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Log policy violation"""
        return await self.log_event(
            event_type=AuditEventType.POLICY_VIOLATION,
            actor_identity=actor_identity,
            actor_type="user",
            action_performed=policy_name,
            result="failure",
            severity=AuditSeverity.WARNING,
            metadata=dict(metadata or {}, description=description)
        )
    
    async def get_events(
        self,
        event_types: Optional[List[AuditEventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[AuditEvent]:
        """Get audit events with filtering"""
        try:
            if not self.db:
                return []
            
            # Build query
            query = {"session_id": self.config.session_id}
            
            if event_types:
                query["event_type"] = {"$in": [et.value for et in event_types]}
            
            if start_time:
                query["timestamp"] = {"$gte": start_time}
            
            if end_time:
                if "timestamp" in query:
                    query["timestamp"]["$lte"] = end_time
                else:
                    query["timestamp"] = {"$lte": end_time}
            
            # Execute query
            cursor = self.db.audit_events.find(query).sort("timestamp", -1).limit(limit)
            events = []
            
            async for doc in cursor:
                events.append(AuditEvent.from_dict(doc))
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get audit events: {e}")
            return []
    
    async def get_session_summary(self) -> Dict[str, Any]:
        """Get session audit summary"""
        try:
            if not self.db:
                return {}
            
            # Get event counts by type
            pipeline = [
                {"$match": {"session_id": self.config.session_id}},
                {"$group": {
                    "_id": "$event_type",
                    "count": {"$sum": 1}
                }}
            ]
            
            cursor = self.db.audit_events.aggregate(pipeline)
            event_counts = {}
            
            async for doc in cursor:
                event_counts[doc["_id"]] = doc["count"]
            
            # Get session duration
            first_event = await self.db.audit_events.find_one(
                {"session_id": self.config.session_id},
                sort=[("timestamp", 1)]
            )
            last_event = await self.db.audit_events.find_one(
                {"session_id": self.config.session_id},
                sort=[("timestamp", -1)]
            )
            
            duration = None
            if first_event and last_event:
                start_time = datetime.fromisoformat(first_event["timestamp"])
                end_time = datetime.fromisoformat(last_event["timestamp"])
                duration = (end_time - start_time).total_seconds()
            
            return {
                "session_id": self.config.session_id,
                "event_count": self.event_count,
                "error_count": self.error_count,
                "event_counts": event_counts,
                "duration_seconds": duration,
                "first_event": first_event["timestamp"] if first_event else None,
                "last_event": last_event["timestamp"] if last_event else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get session summary: {e}")
            return {}
    
    async def _connect_database(self) -> None:
        """Connect to MongoDB database"""
        try:
            if not HAS_MOTOR:
                logger.warning("Motor not available, database operations disabled")
                return
            
            self.db_client = AsyncIOMotorClient(MONGODB_URL)
            self.db = self.db_client.lucid
            
            # Test connection
            await self.db_client.admin.command('ping')
            logger.info("Database connection established")
            
            # Create indexes
            await self._create_database_indexes()
            
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            self.db_client = None
            self.db = None
    
    async def _disconnect_database(self) -> None:
        """Disconnect from database"""
        try:
            if self.db_client:
                self.db_client.close()
                self.db_client = None
                self.db = None
                logger.info("Database connection closed")
                
        except Exception as e:
            logger.error(f"Failed to disconnect from database: {e}")
    
    async def _create_database_indexes(self) -> None:
        """Create database indexes for audit events"""
        if not self.db:
            return
        
        try:
            # Audit events collection indexes
            await self.db.audit_events.create_index("session_id")
            await self.db.audit_events.create_index("timestamp")
            await self.db.audit_events.create_index("event_type")
            await self.db.audit_events.create_index("actor_identity")
            await self.db.audit_events.create_index([("session_id", 1), ("timestamp", -1)])
            await self.db.audit_events.create_index([("event_type", 1), ("timestamp", -1)])
            
            logger.info("Database indexes created")
            
        except Exception as e:
            logger.error(f"Database index creation failed: {e}")
    
    async def _start_flush_thread(self) -> None:
        """Start the flush thread"""
        try:
            if self.flush_running:
                return
            
            self.flush_running = True
            self.flush_thread = threading.Thread(target=self._flush_loop)
            self.flush_thread.daemon = True
            self.flush_thread.start()
            
            logger.info("Flush thread started")
            
        except Exception as e:
            logger.error(f"Failed to start flush thread: {e}")
    
    async def _stop_flush_thread(self) -> None:
        """Stop the flush thread"""
        try:
            self.flush_running = False
            
            if self.flush_thread:
                self.flush_thread.join(timeout=5)
            
            logger.info("Flush thread stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop flush thread: {e}")
    
    def _flush_loop(self) -> None:
        """Flush loop (runs in separate thread)"""
        while self.flush_running:
            try:
                time.sleep(self.config.flush_interval_seconds)
                asyncio.create_task(self._flush_events())
            except Exception as e:
                logger.error(f"Flush loop error: {e}")
                time.sleep(1)
    
    async def _flush_events(self) -> None:
        """Flush events to database"""
        try:
            if not self.event_buffer or not self.db:
                return
            
            # Prepare events for database
            events_data = [event.to_dict() for event in self.event_buffer]
            
            # Insert events
            await self.db.audit_events.insert_many(events_data)
            
            # Clear buffer
            self.event_buffer.clear()
            
            logger.debug(f"Flushed {len(events_data)} audit events to database")
            
        except Exception as e:
            logger.error(f"Failed to flush events: {e}")
            self.error_count += 1
    
    def _calculate_event_hash(self, event: AuditEvent) -> str:
        """Calculate hash for event integrity"""
        try:
            # Create hashable string from event data
            hash_data = f"{event.session_id}{event.timestamp.isoformat()}{event.event_type.value}{event.actor_identity}{event.actor_type}"
            if event.resource_accessed:
                hash_data += event.resource_accessed
            if event.action_performed:
                hash_data += event.action_performed
            hash_data += event.result
            
            return hashlib.sha256(hash_data.encode('utf-8')).hexdigest()
            
        except Exception as e:
            logger.error(f"Failed to calculate event hash: {e}")
            return ""
    
    async def _notify_callbacks(self, event_type: str, data: Any) -> None:
        """Notify event callbacks"""
        for callback in self.event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event_type, data)
                else:
                    callback(event_type, data)
            except Exception as e:
                logger.error(f"Error in audit callback: {e}")
    
    def add_event_callback(self, callback: Callable) -> None:
        """Add an event callback"""
        self.event_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Get logger status"""
        return {
            "enabled": self.is_enabled,
            "session_id": self.config.session_id,
            "event_count": self.event_count,
            "error_count": self.error_count,
            "buffer_size": len(self.event_buffer),
            "database_connected": self.db is not None,
            "flush_running": self.flush_running,
            "include_keystrokes": self.config.include_keystrokes,
            "include_window_focus": self.config.include_window_focus,
            "include_resource_access": self.config.include_resource_access,
            "include_network_events": self.config.include_network_events
        }


# Global Audit Trail Logger instance
_audit_trail_logger: Optional[AuditTrailLogger] = None


def get_audit_trail_logger() -> Optional[AuditTrailLogger]:
    """Get the global audit trail logger instance"""
    return _audit_trail_logger


async def initialize_audit_trail_logger(config: AuditTrailConfig) -> AuditTrailLogger:
    """Initialize the global audit trail logger"""
    global _audit_trail_logger
    
    if _audit_trail_logger is None:
        _audit_trail_logger = AuditTrailLogger(config)
        await _audit_trail_logger.start()
    
    return _audit_trail_logger


async def shutdown_audit_trail_logger() -> None:
    """Shutdown the global audit trail logger"""
    global _audit_trail_logger
    
    if _audit_trail_logger:
        await _audit_trail_logger.stop()
        _audit_trail_logger = None


# Main entry point for testing
async def main():
    """Main entry point for testing"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='[audit-trail] %(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create test configuration
    config = AuditTrailConfig(
        session_id="lucid_audit_001",
        enabled=True,
        log_level="INFO",
        compress_logs=True,
        encrypt_logs=True,
        retention_days=90,
        max_events_per_session=10000,
        batch_size=100,
        flush_interval_seconds=30,
        include_keystrokes=True,
        include_window_focus=True,
        include_resource_access=True,
        include_network_events=True,
        sensitive_data_masking=True
    )
    
    # Initialize and start logger
    logger_instance = await initialize_audit_trail_logger(config)
    
    try:
        # Test audit logging
        await logger_instance.log_event(
            event_type=AuditEventType.SESSION_START,
            actor_identity="test_user",
            actor_type="user",
            action_performed="test_session_start"
        )
        
        await logger_instance.log_resource_access(
            resource_type="file",
            resource_path="/tmp/test.txt",
            action="read",
            actor_identity="test_user"
        )
        
        # Get session summary
        summary = await logger_instance.get_session_summary()
        print(f"Session summary: {summary}")
        
        # Keep logger running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down Audit Trail Logger...")
        await shutdown_audit_trail_logger()


if __name__ == "__main__":
    asyncio.run(main())
