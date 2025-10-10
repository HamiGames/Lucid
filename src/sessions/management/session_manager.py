# Session Management Module for Lucid Project
# Comprehensive session management with lifecycle, encryption, and audit capabilities

import os
import json
import uuid
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import threading
import queue
import time

# Configure logging
logger = logging.getLogger(__name__)

class SessionState(Enum):
    """Session state enumeration"""
    CREATED = "created"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    SUSPENDED = "suspended"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    ERROR = "error"

class SessionType(Enum):
    """Session type enumeration"""
    RDP = "rdp"
    SSH = "ssh"
    VNC = "vnc"
    BLOCKCHAIN = "blockchain"
    NODE = "node"
    ADMIN = "admin"
    USER = "user"

class EncryptionLevel(Enum):
    """Encryption level enumeration"""
    NONE = "none"
    BASIC = "basic"
    STANDARD = "standard"
    HIGH = "high"
    MAXIMUM = "maximum"

@dataclass
class SessionMetadata:
    """Session metadata data structure"""
    session_id: str
    name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    created_by: Optional[str] = None
    organization: Optional[str] = None
    project: Optional[str] = None
    environment: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionMetadata':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class SessionConfig:
    """Session configuration data structure"""
    session_type: SessionType
    timeout: int = 3600  # 1 hour default
    max_idle_time: int = 1800  # 30 minutes default
    encryption_level: EncryptionLevel = EncryptionLevel.STANDARD
    audit_logging: bool = True
    resource_monitoring: bool = True
    auto_save: bool = True
    save_interval: int = 300  # 5 minutes default
    max_connections: int = 1
    allow_multiple_users: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Convert enums to strings
        data['session_type'] = self.session_type.value
        data['encryption_level'] = self.encryption_level.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionConfig':
        """Create from dictionary"""
        # Convert string enums back to enum objects
        data['session_type'] = SessionType(data['session_type'])
        data['encryption_level'] = EncryptionLevel(data['encryption_level'])
        return cls(**data)

@dataclass
class SessionConnection:
    """Session connection data structure"""
    connection_id: str
    user_id: str
    connected_at: str
    last_activity: str
    ip_address: str
    user_agent: Optional[str] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionConnection':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class SessionStats:
    """Session statistics data structure"""
    total_connections: int = 0
    active_connections: int = 0
    bytes_transferred: int = 0
    commands_executed: int = 0
    errors_count: int = 0
    uptime_seconds: int = 0
    last_activity: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionStats':
        """Create from dictionary"""
        return cls(**data)

@dataclass
class Session:
    """Complete session data structure"""
    session_id: str
    metadata: SessionMetadata
    config: SessionConfig
    state: SessionState
    connections: List[SessionConnection]
    stats: SessionStats
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    encryption_key: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Convert enums to strings
        data['state'] = self.state.value
        data['metadata'] = self.metadata.to_dict()
        data['config'] = self.config.to_dict()
        data['connections'] = [conn.to_dict() for conn in self.connections]
        data['stats'] = self.stats.to_dict()
        # Don't include encryption key in serialization
        data['encryption_key'] = None
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Session':
        """Create from dictionary"""
        # Convert string enums back to enum objects
        data['state'] = SessionState(data['state'])
        data['metadata'] = SessionMetadata.from_dict(data['metadata'])
        data['config'] = SessionConfig.from_dict(data['config'])
        data['connections'] = [SessionConnection.from_dict(conn) for conn in data['connections']]
        data['stats'] = SessionStats.from_dict(data['stats'])
        return cls(**data)

class SessionManager:
    """Main session manager class"""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """Initialize session manager"""
        self.storage_dir = storage_dir or os.path.join(os.path.expanduser("~"), ".lucid", "sessions")
        self.sessions: Dict[str, Session] = {}
        self.session_lock = threading.RLock()
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.cleanup_task: Optional[asyncio.Task] = None
        self._ensure_storage_dir()
        self._load_existing_sessions()
    
    def _ensure_storage_dir(self):
        """Ensure storage directory exists"""
        os.makedirs(self.storage_dir, exist_ok=True)
    
    def _load_existing_sessions(self):
        """Load existing sessions from storage"""
        try:
            for filename in os.listdir(self.storage_dir):
                if filename.endswith('.json'):
                    session_id = filename[:-5]  # Remove .json extension
                    self._load_session_from_file(session_id)
        except Exception as e:
            logger.error(f"Failed to load existing sessions: {e}")
    
    def _load_session_from_file(self, session_id: str) -> bool:
        """Load session from file"""
        try:
            filepath = os.path.join(self.storage_dir, f"{session_id}.json")
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            session = Session.from_dict(data)
            self.sessions[session_id] = session
            logger.info(f"Session loaded from file: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return False
    
    def _save_session_to_file(self, session: Session) -> bool:
        """Save session to file"""
        try:
            filepath = os.path.join(self.storage_dir, f"{session.session_id}.json")
            with open(filepath, 'w') as f:
                json.dump(session.to_dict(), f, indent=2)
            
            logger.debug(f"Session saved to file: {session.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {e}")
            return False
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return str(uuid.uuid4())
    
    def _generate_encryption_key(self, encryption_level: EncryptionLevel) -> str:
        """Generate encryption key based on level"""
        if encryption_level == EncryptionLevel.NONE:
            return None
        
        # Generate key based on encryption level
        if encryption_level in [EncryptionLevel.BASIC, EncryptionLevel.STANDARD]:
            key_length = 32  # 256 bits
        elif encryption_level == EncryptionLevel.HIGH:
            key_length = 32  # 256 bits with additional entropy
        else:  # MAXIMUM
            key_length = 64  # 512 bits
        
        key = secrets.token_bytes(key_length)
        return base64.b64encode(key).decode()
    
    def _emit_event(self, event_type: str, session: Session, **kwargs):
        """Emit session event to registered handlers"""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    handler(session, **kwargs)
                except Exception as e:
                    logger.error(f"Event handler error for {event_type}: {e}")
    
    def create_session(
        self,
        name: str,
        session_type: SessionType,
        config: Optional[SessionConfig] = None,
        metadata: Optional[SessionMetadata] = None,
        **kwargs
    ) -> Session:
        """Create new session"""
        with self.session_lock:
            session_id = self._generate_session_id()
            now = datetime.utcnow().isoformat()
            
            # Create default config if not provided
            if config is None:
                config = SessionConfig(session_type=session_type)
            
            # Create default metadata if not provided
            if metadata is None:
                metadata = SessionMetadata(
                    session_id=session_id,
                    name=name
                )
            
            # Generate encryption key
            encryption_key = self._generate_encryption_key(config.encryption_level)
            
            # Create session
            session = Session(
                session_id=session_id,
                metadata=metadata,
                config=config,
                state=SessionState.CREATED,
                connections=[],
                stats=SessionStats(),
                created_at=now,
                updated_at=now,
                encryption_key=encryption_key,
                data=kwargs.get('data', {})
            )
            
            # Store session
            self.sessions[session_id] = session
            self._save_session_to_file(session)
            
            # Emit event
            self._emit_event('session_created', session)
            
            logger.info(f"Session created: {session_id}")
            return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        with self.session_lock:
            return self.sessions.get(session_id)
    
    def list_sessions(self, state: Optional[SessionState] = None) -> List[Session]:
        """List sessions, optionally filtered by state"""
        with self.session_lock:
            sessions = list(self.sessions.values())
            if state:
                sessions = [s for s in sessions if s.state == state]
            return sessions
    
    def update_session_state(self, session_id: str, new_state: SessionState) -> bool:
        """Update session state"""
        with self.session_lock:
            session = self.sessions.get(session_id)
            if not session:
                logger.warning(f"Session not found: {session_id}")
                return False
            
            old_state = session.state
            session.state = new_state
            session.updated_at = datetime.utcnow().isoformat()
            
            # Update timestamps based on state
            if new_state == SessionState.ACTIVE and not session.started_at:
                session.started_at = session.updated_at
            elif new_state == SessionState.TERMINATED:
                session.ended_at = session.updated_at
            
            self._save_session_to_file(session)
            
            # Emit event
            self._emit_event('session_state_changed', session, 
                           old_state=old_state, new_state=new_state)
            
            logger.info(f"Session state updated: {session_id} {old_state.value} -> {new_state.value}")
            return True
    
    def add_connection(self, session_id: str, user_id: str, ip_address: str, 
                      user_agent: Optional[str] = None) -> Optional[str]:
        """Add connection to session"""
        with self.session_lock:
            session = self.sessions.get(session_id)
            if not session:
                logger.warning(f"Session not found: {session_id}")
                return None
            
            # Check connection limits
            if len(session.connections) >= session.config.max_connections:
                logger.warning(f"Connection limit reached for session: {session_id}")
                return None
            
            # Check if user already connected (if not allowing multiple users)
            if not session.config.allow_multiple_users:
                existing_connection = next(
                    (conn for conn in session.connections if conn.user_id == user_id and conn.is_active),
                    None
                )
                if existing_connection:
                    logger.warning(f"User already connected to session: {session_id}")
                    return None
            
            # Create connection
            connection_id = str(uuid.uuid4())
            now = datetime.utcnow().isoformat()
            
            connection = SessionConnection(
                connection_id=connection_id,
                user_id=user_id,
                connected_at=now,
                last_activity=now,
                ip_address=ip_address,
                user_agent=user_agent,
                is_active=True
            )
            
            session.connections.append(connection)
            session.stats.total_connections += 1
            session.stats.active_connections += 1
            session.updated_at = now
            
            self._save_session_to_file(session)
            
            # Emit event
            self._emit_event('connection_added', session, connection=connection)
            
            logger.info(f"Connection added to session: {session_id}, connection: {connection_id}")
            return connection_id
    
    def remove_connection(self, session_id: str, connection_id: str) -> bool:
        """Remove connection from session"""
        with self.session_lock:
            session = self.sessions.get(session_id)
            if not session:
                logger.warning(f"Session not found: {session_id}")
                return False
            
            # Find and remove connection
            for i, connection in enumerate(session.connections):
                if connection.connection_id == connection_id:
                    connection.is_active = False
                    session.stats.active_connections -= 1
                    session.updated_at = datetime.utcnow().isoformat()
                    
                    self._save_session_to_file(session)
                    
                    # Emit event
                    self._emit_event('connection_removed', session, connection=connection)
                    
                    logger.info(f"Connection removed from session: {session_id}, connection: {connection_id}")
                    return True
            
            logger.warning(f"Connection not found: {connection_id}")
            return False
    
    def update_connection_activity(self, session_id: str, connection_id: str) -> bool:
        """Update connection activity timestamp"""
        with self.session_lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
            
            # Find connection and update activity
            for connection in session.connections:
                if connection.connection_id == connection_id and connection.is_active:
                    connection.last_activity = datetime.utcnow().isoformat()
                    session.stats.last_activity = connection.last_activity
                    session.updated_at = connection.last_activity
                    
                    self._save_session_to_file(session)
                    return True
            
            return False
    
    def update_session_stats(self, session_id: str, **kwargs) -> bool:
        """Update session statistics"""
        with self.session_lock:
            session = self.sessions.get(session_id)
            if not session:
                return False
            
            # Update stats
            for key, value in kwargs.items():
                if hasattr(session.stats, key):
                    setattr(session.stats, key, value)
            
            session.updated_at = datetime.utcnow().isoformat()
            self._save_session_to_file(session)
            return True
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        with self.session_lock:
            session = self.sessions.get(session_id)
            if not session:
                logger.warning(f"Session not found: {session_id}")
                return False
            
            # Remove from memory
            del self.sessions[session_id]
            
            # Remove file
            filepath = os.path.join(self.storage_dir, f"{session_id}.json")
            if os.path.exists(filepath):
                os.remove(filepath)
            
            # Emit event
            self._emit_event('session_deleted', session)
            
            logger.info(f"Session deleted: {session_id}")
            return True
    
    def cleanup_expired_sessions(self) -> int:
        """Cleanup expired sessions"""
        with self.session_lock:
            cleaned_count = 0
            now = datetime.utcnow()
            
            for session_id, session in list(self.sessions.items()):
                # Check for timeout
                if session.state == SessionState.ACTIVE:
                    created_at = datetime.fromisoformat(session.created_at)
                    if now - created_at > timedelta(seconds=session.config.timeout):
                        logger.info(f"Session timeout: {session_id}")
                        self.update_session_state(session_id, SessionState.TERMINATED)
                        cleaned_count += 1
                        continue
                
                # Check for idle timeout
                if session.stats.last_activity:
                    last_activity = datetime.fromisoformat(session.stats.last_activity)
                    if now - last_activity > timedelta(seconds=session.config.max_idle_time):
                        logger.info(f"Session idle timeout: {session_id}")
                        self.update_session_state(session_id, SessionState.SUSPENDED)
                        cleaned_count += 1
                        continue
                
                # Check for terminated sessions older than 24 hours
                if session.state == SessionState.TERMINATED and session.ended_at:
                    ended_at = datetime.fromisoformat(session.ended_at)
                    if now - ended_at > timedelta(hours=24):
                        logger.info(f"Cleaning up old terminated session: {session_id}")
                        self.delete_session(session_id)
                        cleaned_count += 1
            
            return cleaned_count
    
    def register_event_handler(self, event_type: str, handler: Callable):
        """Register event handler"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        self.event_handlers[event_type].append(handler)
    
    def unregister_event_handler(self, event_type: str, handler: Callable):
        """Unregister event handler"""
        if event_type in self.event_handlers:
            try:
                self.event_handlers[event_type].remove(handler)
            except ValueError:
                pass
    
    async def start_cleanup_task(self, interval: int = 300):
        """Start background cleanup task"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval)
                    cleaned = self.cleanup_expired_sessions()
                    if cleaned > 0:
                        logger.info(f"Cleanup task: {cleaned} sessions processed")
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Cleanup task error: {e}")
        
        self.cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Cleanup task started")
    
    def stop_cleanup_task(self):
        """Stop background cleanup task"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            self.cleanup_task = None
            logger.info("Cleanup task stopped")

# Import datetime at module level
import datetime

# Factory functions for common session types
def create_rdp_session(
    name: str,
    host: str,
    port: int = 3389,
    timeout: int = 3600,
    encryption_level: EncryptionLevel = EncryptionLevel.STANDARD
) -> Session:
    """Create RDP session"""
    manager = SessionManager()
    config = SessionConfig(
        session_type=SessionType.RDP,
        timeout=timeout,
        encryption_level=encryption_level,
        resource_monitoring=True,
        audit_logging=True
    )
    metadata = SessionMetadata(
        name=name,
        description=f"RDP session to {host}:{port}"
    )
    return manager.create_session(
        name=name,
        session_type=SessionType.RDP,
        config=config,
        metadata=metadata,
        data={'host': host, 'port': port}
    )

def create_blockchain_session(
    name: str,
    network: str = "shasta",
    timeout: int = 7200,
    encryption_level: EncryptionLevel = EncryptionLevel.HIGH
) -> Session:
    """Create blockchain session"""
    manager = SessionManager()
    config = SessionConfig(
        session_type=SessionType.BLOCKCHAIN,
        timeout=timeout,
        encryption_level=encryption_level,
        resource_monitoring=True,
        audit_logging=True,
        max_connections=5
    )
    metadata = SessionMetadata(
        name=name,
        description=f"Blockchain session for {network} network"
    )
    return manager.create_session(
        name=name,
        session_type=SessionType.BLOCKCHAIN,
        config=config,
        metadata=metadata,
        data={'network': network}
    )

def create_node_session(
    name: str,
    node_type: str = "consensus",
    timeout: int = 1800,
    encryption_level: EncryptionLevel = EncryptionLevel.HIGH
) -> Session:
    """Create node session"""
    manager = SessionManager()
    config = SessionConfig(
        session_type=SessionType.NODE,
        timeout=timeout,
        encryption_level=encryption_level,
        resource_monitoring=True,
        audit_logging=True,
        max_connections=10
    )
    metadata = SessionMetadata(
        name=name,
        description=f"Node session for {node_type} operations"
    )
    return manager.create_session(
        name=name,
        session_type=SessionType.NODE,
        config=config,
        metadata=metadata,
        data={'node_type': node_type}
    )
