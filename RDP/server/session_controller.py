# Path: RDP/server/session_controller.py
# Lucid RDP Session Controller - Session lifecycle management
# Implements R-MUST-003: Remote Desktop Host Support with session orchestration
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
import time
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import threading
import psutil
import subprocess

# Import existing project modules
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from session.session_recorder import SessionRecorder, SessionMetadata
from RDP.server.rdp_server_manager import RDPServerManager, RDPSession, SessionStatus

logger = logging.getLogger(__name__)

# Configuration from environment
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "60"))
MAX_CONCURRENT_SESSIONS = int(os.getenv("MAX_CONCURRENT_SESSIONS", "5"))
SESSION_CLEANUP_INTERVAL = int(os.getenv("SESSION_CLEANUP_INTERVAL", "300"))  # 5 minutes
SESSION_HEALTH_CHECK_INTERVAL = int(os.getenv("SESSION_HEALTH_CHECK_INTERVAL", "60"))  # 1 minute


class SessionLifecycleState(Enum):
    """Session lifecycle states"""
    INITIALIZING = "initializing"
    CREATING = "creating"
    STARTING = "starting"
    ACTIVE = "active"
    RECORDING = "recording"
    PAUSING = "pausing"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    CLEANUP = "cleanup"
    FAILED = "failed"
    EXPIRED = "expired"


class SessionPriority(Enum):
    """Session priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SessionLifecycleEvent:
    """Session lifecycle event"""
    event_id: str
    session_id: str
    event_type: str
    state_from: SessionLifecycleState
    state_to: SessionLifecycleState
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


@dataclass
class SessionLifecycleConfig:
    """Session lifecycle configuration"""
    max_concurrent_sessions: int = MAX_CONCURRENT_SESSIONS
    session_timeout_minutes: int = SESSION_TIMEOUT_MINUTES
    cleanup_interval_seconds: int = SESSION_CLEANUP_INTERVAL
    health_check_interval_seconds: int = SESSION_HEALTH_CHECK_INTERVAL
    auto_cleanup_enabled: bool = True
    health_monitoring_enabled: bool = True
    resource_monitoring_enabled: bool = True
    event_logging_enabled: bool = True


@dataclass
class SessionResourceMetrics:
    """Session resource usage metrics"""
    session_id: str
    cpu_percent: float
    memory_mb: float
    network_bytes_sent: int
    network_bytes_received: int
    disk_io_read: int
    disk_io_write: int
    timestamp: datetime
    process_count: int = 0


class SessionController:
    """
    Manages the complete lifecycle of RDP sessions including creation,
    monitoring, resource management, and cleanup.
    """
    
    def __init__(self, config: Optional[SessionLifecycleConfig] = None):
        self.config = config or SessionLifecycleConfig()
        self.active_sessions: Dict[str, RDPSession] = {}
        self.session_lifecycle_events: List[SessionLifecycleEvent] = []
        self.session_resource_metrics: Dict[str, List[SessionResourceMetrics]] = {}
        self.session_callbacks: Dict[str, List[Callable]] = {}
        
        # Lifecycle management
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # Integration components
        self.rdp_server_manager: Optional[RDPServerManager] = None
        self.session_recorder: Optional[SessionRecorder] = None
        
        logger.info(f"SessionController initialized with config: {self.config}")
    
    async def start(self) -> None:
        """Start the session controller"""
        if self._running:
            logger.warning("SessionController is already running")
            return
        
        try:
            self._running = True
            
            # Initialize RDP server manager
            self.rdp_server_manager = RDPServerManager()
            await self.rdp_server_manager.start()
            
            # Initialize session recorder
            self.session_recorder = SessionRecorder()
            await self.session_recorder.start()
            
            # Start background tasks
            if self.config.auto_cleanup_enabled:
                self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            if self.config.health_monitoring_enabled:
                self._health_check_task = asyncio.create_task(self._health_check_loop())
            
            logger.info("SessionController started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start SessionController: {e}")
            await self.stop()
            raise
    
    async def stop(self) -> None:
        """Stop the session controller"""
        if not self._running:
            return
        
        logger.info("Stopping SessionController...")
        self._running = False
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Stop all active sessions
        await self._stop_all_sessions()
        
        # Stop integration components
        if self.session_recorder:
            await self.session_recorder.stop()
        
        if self.rdp_server_manager:
            await self.rdp_server_manager.stop()
        
        logger.info("SessionController stopped")
    
    async def create_session(
        self,
        owner_address: str,
        session_config: Optional[Dict[str, Any]] = None,
        priority: SessionPriority = SessionPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new RDP session"""
        async with self._lock:
            # Check session limits
            if len(self.active_sessions) >= self.config.max_concurrent_sessions:
                raise RuntimeError(f"Maximum concurrent sessions ({self.config.max_concurrent_sessions}) exceeded")
            
            session_id = str(uuid.uuid4())
            
            try:
                # Log session creation event
                await self._log_lifecycle_event(
                    session_id, "create_session", SessionLifecycleState.INITIALIZING, 
                    SessionLifecycleState.CREATING, {"owner_address": owner_address}
                )
                
                # Create RDP session
                rdp_session = RDPSession(
                    session_id=session_id,
                    owner_address=owner_address,
                    status=SessionStatus.CREATING,
                    created_at=datetime.now(timezone.utc),
                    config=session_config or {},
                    metadata=metadata or {}
                )
                
                # Add to active sessions
                self.active_sessions[session_id] = rdp_session
                self.session_resource_metrics[session_id] = []
                
                # Initialize RDP session
                await self.rdp_server_manager.create_session(rdp_session)
                
                # Start session recording
                if self.session_recorder:
                    session_metadata = SessionMetadata(
                        session_id=session_id,
                        owner_address=owner_address,
                        started_at=datetime.now(timezone.utc),
                        metadata=metadata or {}
                    )
                    await self.session_recorder.start_recording(session_metadata)
                
                # Log session started event
                await self._log_lifecycle_event(
                    session_id, "session_started", SessionLifecycleState.CREATING,
                    SessionLifecycleState.ACTIVE, {"priority": priority.value}
                )
                
                logger.info(f"Created session {session_id} for owner {owner_address}")
                return session_id
                
            except Exception as e:
                logger.error(f"Failed to create session {session_id}: {e}")
                await self._log_lifecycle_event(
                    session_id, "create_failed", SessionLifecycleState.CREATING,
                    SessionLifecycleState.FAILED, error_message=str(e)
                )
                
                # Cleanup failed session
                await self._cleanup_session(session_id)
                raise
    
    async def start_session(self, session_id: str) -> bool:
        """Start an existing session"""
        async with self._lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.active_sessions[session_id]
            
            try:
                await self._log_lifecycle_event(
                    session_id, "start_session", SessionLifecycleState.CREATING,
                    SessionLifecycleState.STARTING
                )
                
                # Start RDP session
                await self.rdp_server_manager.start_session(session_id)
                
                # Update session status
                session.status = SessionStatus.ACTIVE
                session.started_at = datetime.now(timezone.utc)
                
                await self._log_lifecycle_event(
                    session_id, "session_started", SessionLifecycleState.STARTING,
                    SessionLifecycleState.ACTIVE
                )
                
                logger.info(f"Started session {session_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start session {session_id}: {e}")
                await self._log_lifecycle_event(
                    session_id, "start_failed", SessionLifecycleState.STARTING,
                    SessionLifecycleState.FAILED, error_message=str(e)
                )
                return False
    
    async def pause_session(self, session_id: str) -> bool:
        """Pause an active session"""
        async with self._lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.active_sessions[session_id]
            
            try:
                await self._log_lifecycle_event(
                    session_id, "pause_session", SessionLifecycleState.ACTIVE,
                    SessionLifecycleState.PAUSING
                )
                
                # Pause RDP session
                await self.rdp_server_manager.pause_session(session_id)
                
                # Pause recording
                if self.session_recorder:
                    await self.session_recorder.pause_recording(session_id)
                
                # Update session status
                session.status = SessionStatus.PAUSED
                session.paused_at = datetime.now(timezone.utc)
                
                await self._log_lifecycle_event(
                    session_id, "session_paused", SessionLifecycleState.PAUSING,
                    SessionLifecycleState.PAUSED
                )
                
                logger.info(f"Paused session {session_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to pause session {session_id}: {e}")
                await self._log_lifecycle_event(
                    session_id, "pause_failed", SessionLifecycleState.PAUSING,
                    SessionLifecycleState.ACTIVE, error_message=str(e)
                )
                return False
    
    async def resume_session(self, session_id: str) -> bool:
        """Resume a paused session"""
        async with self._lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.active_sessions[session_id]
            
            if session.status != SessionStatus.PAUSED:
                raise ValueError(f"Session {session_id} is not paused")
            
            try:
                await self._log_lifecycle_event(
                    session_id, "resume_session", SessionLifecycleState.PAUSED,
                    SessionLifecycleState.ACTIVE
                )
                
                # Resume RDP session
                await self.rdp_server_manager.resume_session(session_id)
                
                # Resume recording
                if self.session_recorder:
                    await self.session_recorder.resume_recording(session_id)
                
                # Update session status
                session.status = SessionStatus.ACTIVE
                session.paused_at = None
                
                await self._log_lifecycle_event(
                    session_id, "session_resumed", SessionLifecycleState.PAUSED,
                    SessionLifecycleState.ACTIVE
                )
                
                logger.info(f"Resumed session {session_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to resume session {session_id}: {e}")
                await self._log_lifecycle_event(
                    session_id, "resume_failed", SessionLifecycleState.PAUSED,
                    SessionLifecycleState.FAILED, error_message=str(e)
                )
                return False
    
    async def stop_session(self, session_id: str, force: bool = False) -> bool:
        """Stop an active session"""
        async with self._lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.active_sessions[session_id]
            
            try:
                await self._log_lifecycle_event(
                    session_id, "stop_session", SessionLifecycleState.ACTIVE,
                    SessionLifecycleState.STOPPING, {"force": force}
                )
                
                # Stop RDP session
                await self.rdp_server_manager.stop_session(session_id, force=force)
                
                # Stop recording
                if self.session_recorder:
                    await self.session_recorder.stop_recording(session_id)
                
                # Update session status
                session.status = SessionStatus.COMPLETED
                session.stopped_at = datetime.now(timezone.utc)
                
                await self._log_lifecycle_event(
                    session_id, "session_stopped", SessionLifecycleState.STOPPING,
                    SessionLifecycleState.STOPPED
                )
                
                # Schedule cleanup
                asyncio.create_task(self._cleanup_session(session_id))
                
                logger.info(f"Stopped session {session_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to stop session {session_id}: {e}")
                await self._log_lifecycle_event(
                    session_id, "stop_failed", SessionLifecycleState.STOPPING,
                    SessionLifecycleState.FAILED, error_message=str(e)
                )
                return False
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed session status"""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        
        # Get resource metrics
        latest_metrics = None
        if session_id in self.session_resource_metrics:
            metrics_list = self.session_resource_metrics[session_id]
            if metrics_list:
                latest_metrics = metrics_list[-1]
        
        return {
            "session_id": session_id,
            "owner_address": session.owner_address,
            "status": session.status.value,
            "created_at": session.created_at.isoformat(),
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "stopped_at": session.stopped_at.isoformat() if session.stopped_at else None,
            "duration_seconds": self._calculate_session_duration(session),
            "resource_metrics": latest_metrics.__dict__ if latest_metrics else None,
            "config": session.config,
            "metadata": session.metadata
        }
    
    async def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions"""
        sessions = []
        for session_id in self.active_sessions:
            session_status = await self.get_session_status(session_id)
            if session_status:
                sessions.append(session_status)
        return sessions
    
    async def _cleanup_session(self, session_id: str) -> None:
        """Cleanup a stopped session"""
        try:
            await self._log_lifecycle_event(
                session_id, "cleanup_session", SessionLifecycleState.STOPPED,
                SessionLifecycleState.CLEANUP
            )
            
            # Remove from active sessions
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            # Clean up resource metrics (keep last 100 entries)
            if session_id in self.session_resource_metrics:
                metrics = self.session_resource_metrics[session_id]
                if len(metrics) > 100:
                    self.session_resource_metrics[session_id] = metrics[-100:]
            
            # Clean up lifecycle events (keep last 50 events per session)
            session_events = [e for e in self.session_lifecycle_events if e.session_id == session_id]
            if len(session_events) > 50:
                # Remove old events
                self.session_lifecycle_events = [
                    e for e in self.session_lifecycle_events 
                    if e.session_id != session_id or e in session_events[-50:]
                ]
            
            await self._log_lifecycle_event(
                session_id, "session_cleaned", SessionLifecycleState.CLEANUP,
                SessionLifecycleState.STOPPED
            )
            
            logger.info(f"Cleaned up session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop"""
        while self._running:
            try:
                await asyncio.sleep(self.config.cleanup_interval_seconds)
                
                if not self._running:
                    break
                
                # Check for expired sessions
                current_time = datetime.now(timezone.utc)
                expired_sessions = []
                
                for session_id, session in self.active_sessions.items():
                    if session.started_at:
                        session_duration = current_time - session.started_at
                        if session_duration.total_seconds() > (self.config.session_timeout_minutes * 60):
                            expired_sessions.append(session_id)
                
                # Stop expired sessions
                for session_id in expired_sessions:
                    logger.warning(f"Session {session_id} expired, stopping...")
                    await self.stop_session(session_id, force=True)
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _health_check_loop(self) -> None:
        """Background health check loop"""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval_seconds)
                
                if not self._running:
                    break
                
                # Check health of active sessions
                for session_id, session in self.active_sessions.items():
                    if session.status in [SessionStatus.ACTIVE, SessionStatus.RECORDING]:
                        await self._check_session_health(session_id)
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(30)  # Wait before retrying
    
    async def _check_session_health(self, session_id: str) -> None:
        """Check health of a specific session"""
        try:
            # Get resource metrics
            metrics = await self._collect_session_metrics(session_id)
            if metrics:
                self.session_resource_metrics[session_id].append(metrics)
                
                # Check for resource limits
                if metrics.cpu_percent > 90:
                    logger.warning(f"Session {session_id} high CPU usage: {metrics.cpu_percent}%")
                
                if metrics.memory_mb > 1024:  # 1GB
                    logger.warning(f"Session {session_id} high memory usage: {metrics.memory_mb}MB")
            
            # Check RDP server health
            if self.rdp_server_manager:
                is_healthy = await self.rdp_server_manager.check_session_health(session_id)
                if not is_healthy:
                    logger.error(f"Session {session_id} health check failed")
                    await self._log_lifecycle_event(
                        session_id, "health_check_failed", SessionLifecycleState.ACTIVE,
                        SessionLifecycleState.FAILED
                    )
        
        except Exception as e:
            logger.error(f"Failed to check health for session {session_id}: {e}")
    
    async def _collect_session_metrics(self, session_id: str) -> Optional[SessionResourceMetrics]:
        """Collect resource metrics for a session"""
        try:
            # This is a simplified implementation
            # In a real implementation, you would collect actual process metrics
            return SessionResourceMetrics(
                session_id=session_id,
                cpu_percent=psutil.cpu_percent(),
                memory_mb=psutil.virtual_memory().used / 1024 / 1024,
                network_bytes_sent=0,  # Would be collected from network interfaces
                network_bytes_received=0,
                disk_io_read=0,  # Would be collected from disk I/O
                disk_io_write=0,
                timestamp=datetime.now(timezone.utc),
                process_count=len(psutil.pids())
            )
        except Exception as e:
            logger.error(f"Failed to collect metrics for session {session_id}: {e}")
            return None
    
    async def _log_lifecycle_event(
        self,
        session_id: str,
        event_type: str,
        state_from: SessionLifecycleState,
        state_to: SessionLifecycleState,
        metadata: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Log a session lifecycle event"""
        if not self.config.event_logging_enabled:
            return
        
        event = SessionLifecycleEvent(
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            event_type=event_type,
            state_from=state_from,
            state_to=state_to,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
            error_message=error_message
        )
        
        self.session_lifecycle_events.append(event)
        
        # Trigger callbacks
        if session_id in self.session_callbacks:
            for callback in self.session_callbacks[session_id]:
                try:
                    await callback(event)
                except Exception as e:
                    logger.error(f"Error in session callback: {e}")
    
    async def _stop_all_sessions(self) -> None:
        """Stop all active sessions"""
        session_ids = list(self.active_sessions.keys())
        for session_id in session_ids:
            try:
                await self.stop_session(session_id, force=True)
            except Exception as e:
                logger.error(f"Failed to stop session {session_id}: {e}")
    
    def _calculate_session_duration(self, session: RDPSession) -> Optional[float]:
        """Calculate session duration in seconds"""
        if not session.started_at:
            return None
        
        end_time = session.stopped_at or datetime.now(timezone.utc)
        duration = end_time - session.started_at
        return duration.total_seconds()
    
    def add_session_callback(self, session_id: str, callback: Callable) -> None:
        """Add a callback for session events"""
        if session_id not in self.session_callbacks:
            self.session_callbacks[session_id] = []
        self.session_callbacks[session_id].append(callback)
    
    def remove_session_callback(self, session_id: str, callback: Callable) -> None:
        """Remove a session callback"""
        if session_id in self.session_callbacks:
            try:
                self.session_callbacks[session_id].remove(callback)
            except ValueError:
                pass


# Global session controller instance
_session_controller: Optional[SessionController] = None


def get_session_controller() -> SessionController:
    """Get the global session controller instance"""
    global _session_controller
    if _session_controller is None:
        _session_controller = SessionController()
    return _session_controller


async def start_session_controller():
    """Start the global session controller"""
    controller = get_session_controller()
    await controller.start()


async def stop_session_controller():
    """Stop the global session controller"""
    global _session_controller
    if _session_controller:
        await _session_controller.stop()
        _session_controller = None


if __name__ == "__main__":
    async def test_session_controller():
        """Test the session controller"""
        controller = SessionController()
        
        try:
            await controller.start()
            
            # Create a test session
            session_id = await controller.create_session(
                owner_address="test_user_123",
                session_config={"resolution": "1920x1080"},
                metadata={"test": True}
            )
            
            print(f"Created session: {session_id}")
            
            # Start the session
            await controller.start_session(session_id)
            
            # Get session status
            status = await controller.get_session_status(session_id)
            print(f"Session status: {status}")
            
            # List active sessions
            sessions = await controller.list_active_sessions()
            print(f"Active sessions: {len(sessions)}")
            
            # Wait a bit
            await asyncio.sleep(5)
            
            # Stop the session
            await controller.stop_session(session_id)
            
        finally:
            await controller.stop()
    
    # Run test
    asyncio.run(test_session_controller())
