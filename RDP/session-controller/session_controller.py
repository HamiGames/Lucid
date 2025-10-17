"""
RDP Session Controller - Session Management Service

This module provides session management functionality for RDP connections,
including session creation, monitoring, and termination.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4
import json

from .connection_manager import ConnectionManager
from ..common.models import RdpSession, SessionStatus, SessionMetrics
from ..security.session_validator import SessionValidator

logger = logging.getLogger(__name__)

class SessionController:
    """Manages RDP session lifecycle and monitoring"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.session_validator = SessionValidator()
        self.active_sessions: Dict[UUID, RdpSession] = {}
        self.session_metrics: Dict[UUID, SessionMetrics] = {}
        
    async def create_session(
        self, 
        user_id: str, 
        server_id: UUID,
        session_config: Dict[str, Any]
    ) -> RdpSession:
        """Create a new RDP session"""
        try:
            session_id = uuid4()
            
            # Validate session configuration
            await self.session_validator.validate_session_config(session_config)
            
            # Create session object
            session = RdpSession(
                session_id=session_id,
                user_id=user_id,
                server_id=server_id,
                status=SessionStatus.CREATING,
                created_at=datetime.utcnow(),
                config=session_config
            )
            
            # Initialize connection
            connection = await self.connection_manager.create_connection(
                server_id=server_id,
                session_config=session_config
            )
            
            session.connection_id = connection.connection_id
            session.status = SessionStatus.ACTIVE
            
            # Store session
            self.active_sessions[session_id] = session
            
            # Initialize metrics
            self.session_metrics[session_id] = SessionMetrics(
                session_id=session_id,
                start_time=datetime.utcnow()
            )
            
            logger.info(f"Session {session_id} created for user {user_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    async def get_session(self, session_id: UUID) -> Optional[RdpSession]:
        """Get session by ID"""
        return self.active_sessions.get(session_id)
    
    async def list_user_sessions(self, user_id: str) -> List[RdpSession]:
        """List all sessions for a user"""
        return [
            session for session in self.active_sessions.values()
            if session.user_id == user_id
        ]
    
    async def update_session_status(
        self, 
        session_id: UUID, 
        status: SessionStatus
    ) -> bool:
        """Update session status"""
        try:
            if session_id not in self.active_sessions:
                return False
                
            session = self.active_sessions[session_id]
            session.status = status
            session.updated_at = datetime.utcnow()
            
            logger.info(f"Session {session_id} status updated to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session status: {e}")
            return False
    
    async def terminate_session(self, session_id: UUID) -> bool:
        """Terminate a session"""
        try:
            if session_id not in self.active_sessions:
                return False
                
            session = self.active_sessions[session_id]
            
            # Close connection
            if session.connection_id:
                await self.connection_manager.close_connection(session.connection_id)
            
            # Update session status
            session.status = SessionStatus.TERMINATED
            session.terminated_at = datetime.utcnow()
            
            # Clean up metrics
            if session_id in self.session_metrics:
                del self.session_metrics[session_id]
            
            logger.info(f"Session {session_id} terminated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to terminate session: {e}")
            return False
    
    async def get_session_metrics(self, session_id: UUID) -> Optional[SessionMetrics]:
        """Get session metrics"""
        return self.session_metrics.get(session_id)
    
    async def update_session_metrics(
        self, 
        session_id: UUID, 
        metrics_data: Dict[str, Any]
    ) -> bool:
        """Update session metrics"""
        try:
            if session_id not in self.session_metrics:
                return False
                
            metrics = self.session_metrics[session_id]
            metrics.update_from_dict(metrics_data)
            metrics.last_updated = datetime.utcnow()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session metrics: {e}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        try:
            current_time = datetime.utcnow()
            expired_sessions = []
            
            for session_id, session in self.active_sessions.items():
                # Check if session is expired (idle timeout)
                if session.status == SessionStatus.ACTIVE:
                    idle_time = current_time - session.last_activity
                    if idle_time > timedelta(minutes=30):  # 30 minute idle timeout
                        expired_sessions.append(session_id)
            
            # Terminate expired sessions
            for session_id in expired_sessions:
                await self.terminate_session(session_id)
            
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            return len(expired_sessions)
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def get_session_health(self, session_id: UUID) -> Dict[str, Any]:
        """Get session health status"""
        try:
            session = await self.get_session(session_id)
            if not session:
                return {"status": "not_found"}
            
            # Check connection health
            connection_health = await self.connection_manager.check_connection_health(
                session.connection_id
            )
            
            # Get metrics
            metrics = await self.get_session_metrics(session_id)
            
            return {
                "session_id": str(session_id),
                "status": session.status.value,
                "connection_health": connection_health,
                "metrics": metrics.to_dict() if metrics else None,
                "last_activity": session.last_activity.isoformat() if session.last_activity else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get session health: {e}")
            return {"status": "error", "error": str(e)}
    
    async def start_session_monitoring(self):
        """Start background session monitoring"""
        while True:
            try:
                # Clean up expired sessions
                await self.cleanup_expired_sessions()
                
                # Update metrics for active sessions
                for session_id, session in self.active_sessions.items():
                    if session.status == SessionStatus.ACTIVE:
                        # Get connection metrics
                        if session.connection_id:
                            connection_metrics = await self.connection_manager.get_connection_metrics(
                                session.connection_id
                            )
                            await self.update_session_metrics(session_id, connection_metrics)
                
                # Wait 30 seconds before next check
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Session monitoring error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
