# Path: sessions/core/session_generator.py
# Lucid RDP Session ID Generator - Secure session identifier generation
# Based on LUCID-STRICT requirements per R-MUST-012

from __future__ import annotations

import os
import secrets
import uuid
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import blake3

logger = logging.getLogger(__name__)

# Session ID Constants per R-MUST-012
SESSION_ID_ENTROPY_BITS = int(os.getenv("SESSION_ID_ENTROPY_BITS", "256"))  # 256-bit entropy
SESSION_EXPIRY_HOURS = int(os.getenv("SESSION_EXPIRY_HOURS", "8"))  # 8-hour sessions
SESSION_CLEANUP_HOURS = int(os.getenv("SESSION_CLEANUP_HOURS", "24"))  # 24-hour cleanup


class SessionType(Enum):
    """Types of sessions in Lucid RDP system"""
    RDP_USER = "rdp_user"           # Standard user RDP session
    RDP_ADMIN = "rdp_admin"         # Administrative RDP session  
    API_USER = "api_user"           # User API session
    API_ADMIN = "api_admin"         # Admin API session
    API_NODE = "api_node"           # Node API session
    BLOCKCHAIN = "blockchain"       # Blockchain operation session
    TEMP_UPLOAD = "temp_upload"     # Temporary file upload session


@dataclass
class SessionMetadata:
    """Metadata for generated sessions per R-MUST-012"""
    session_id: str
    session_type: SessionType
    owner_address: Optional[str]
    node_id: Optional[str]
    ephemeral_keypair: ed25519.Ed25519PrivateKey
    public_key: ed25519.Ed25519PublicKey
    created_at: datetime
    expires_at: datetime
    is_single_use: bool = True
    is_replayable: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to MongoDB document format"""
        return {
            "_id": self.session_id,
            "type": self.session_type.value,
            "owner_address": self.owner_address,
            "node_id": self.node_id,
            "public_key": self.public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            ).hex(),
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "single_use": self.is_single_use,
            "replayable": self.is_replayable,
            "status": "active"
        }
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now(timezone.utc) > self.expires_at
    
    def get_remaining_time(self) -> timedelta:
        """Get remaining session time"""
        now = datetime.now(timezone.utc)
        if now > self.expires_at:
            return timedelta(0)
        return self.expires_at - now


class SessionIdGenerator:
    """
    Secure session ID generator for Lucid RDP system.
    
    Per R-MUST-012:
    - Single-use session identifiers
    - Non-replayable sessions
    - Ephemeral keypairs per session
    - Secure entropy generation
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, SessionMetadata] = {}
        logger.info("Session ID generator initialized")
    
    def generate_session_id(self, 
                          session_type: SessionType,
                          owner_address: Optional[str] = None,
                          node_id: Optional[str] = None,
                          custom_expiry: Optional[datetime] = None) -> SessionMetadata:
        """
        Generate secure session ID with ephemeral keypair.
        
        Args:
            session_type: Type of session to create
            owner_address: TRON address of session owner
            node_id: Node ID for node sessions
            custom_expiry: Custom expiry time (default: 8 hours)
            
        Returns:
            Complete session metadata
        """
        try:
            # Generate cryptographically secure session ID
            session_id = self._generate_secure_id(session_type)
            
            # Generate ephemeral keypair for this session
            ephemeral_private = ed25519.Ed25519PrivateKey.generate()
            ephemeral_public = ephemeral_private.public_key()
            
            # Set expiry time
            created_at = datetime.now(timezone.utc)
            if custom_expiry:
                expires_at = custom_expiry
            else:
                expires_at = created_at + timedelta(hours=SESSION_EXPIRY_HOURS)
            
            # Create session metadata
            session_meta = SessionMetadata(
                session_id=session_id,
                session_type=session_type,
                owner_address=owner_address,
                node_id=node_id,
                ephemeral_keypair=ephemeral_private,
                public_key=ephemeral_public,
                created_at=created_at,
                expires_at=expires_at,
                is_single_use=True,
                is_replayable=False
            )
            
            # Store in active sessions
            self.active_sessions[session_id] = session_meta
            
            logger.info(f"Generated session ID: {session_id} (type: {session_type.value})")
            
            return session_meta
            
        except Exception as e:
            logger.error(f"Session ID generation failed: {e}")
            raise
    
    def _generate_secure_id(self, session_type: SessionType) -> str:
        """
        Generate cryptographically secure session ID.
        
        Args:
            session_type: Type of session
            
        Returns:
            Secure session identifier
        """
        # Generate high-entropy random bytes
        entropy = secrets.token_bytes(SESSION_ID_ENTROPY_BITS // 8)  # 32 bytes for 256-bit
        
        # Create session-specific context
        timestamp = datetime.now(timezone.utc).isoformat().encode()
        session_context = f"{session_type.value}:{uuid.uuid4()}".encode()
        
        # Combine entropy with context using BLAKE3
        hasher = blake3.blake3()
        hasher.update(entropy)
        hasher.update(timestamp)
        hasher.update(session_context)
        
        # Generate final session ID
        session_hash = hasher.hexdigest()
        
        # Format as UUID-like string for readability
        session_id = f"{session_hash[:8]}-{session_hash[8:12]}-{session_hash[12:16]}-{session_hash[16:20]}-{session_hash[20:32]}"
        
        return session_id
    
    def validate_session_id(self, session_id: str) -> Optional[SessionMetadata]:
        """
        Validate session ID and return metadata if valid.
        
        Args:
            session_id: Session identifier to validate
            
        Returns:
            Session metadata if valid, None otherwise
        """
        try:
            session_meta = self.active_sessions.get(session_id)
            if not session_meta:
                logger.warning(f"Session ID not found: {session_id}")
                return None
            
            # Check if session is expired
            if session_meta.is_expired():
                logger.warning(f"Session ID expired: {session_id}")
                self._cleanup_expired_session(session_id)
                return None
            
            return session_meta
            
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return None
    
    def invalidate_session(self, session_id: str, reason: str = "manual_invalidation") -> bool:
        """
        Invalidate session ID (single-use enforcement).
        
        Args:
            session_id: Session identifier to invalidate
            reason: Reason for invalidation
            
        Returns:
            True if successfully invalidated
        """
        try:
            if session_id in self.active_sessions:
                session_meta = self.active_sessions[session_id]
                
                # Log invalidation for audit trail
                logger.info(f"Invalidating session {session_id}: {reason}")
                
                # Remove from active sessions
                del self.active_sessions[session_id]
                
                return True
            else:
                logger.warning(f"Attempted to invalidate non-existent session: {session_id}")
                return False
                
        except Exception as e:
            logger.error(f"Session invalidation failed: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions from memory.
        
        Returns:
            Number of sessions cleaned up
        """
        try:
            now = datetime.now(timezone.utc)
            expired_sessions = []
            
            # Find expired sessions
            for session_id, session_meta in self.active_sessions.items():
                if session_meta.is_expired():
                    expired_sessions.append(session_id)
            
            # Remove expired sessions
            cleanup_count = 0
            for session_id in expired_sessions:
                self._cleanup_expired_session(session_id)
                cleanup_count += 1
            
            if cleanup_count > 0:
                logger.info(f"Cleaned up {cleanup_count} expired sessions")
            
            return cleanup_count
            
        except Exception as e:
            logger.error(f"Session cleanup failed: {e}")
            return 0
    
    def _cleanup_expired_session(self, session_id: str):
        """Clean up a specific expired session"""
        try:
            if session_id in self.active_sessions:
                session_meta = self.active_sessions[session_id]
                logger.debug(f"Cleaning up expired session: {session_id} (expired: {session_meta.expires_at})")
                del self.active_sessions[session_id]
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about active sessions"""
        try:
            total_sessions = len(self.active_sessions)
            session_by_type = {}
            expired_count = 0
            
            for session_meta in self.active_sessions.values():
                session_type = session_meta.session_type.value
                session_by_type[session_type] = session_by_type.get(session_type, 0) + 1
                
                if session_meta.is_expired():
                    expired_count += 1
            
            return {
                "total_sessions": total_sessions,
                "by_type": session_by_type,
                "expired_pending_cleanup": expired_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get session stats: {e}")
            return {}
    
    def force_cleanup_all(self) -> int:
        """Force cleanup of all sessions (for shutdown)"""
        try:
            session_count = len(self.active_sessions)
            self.active_sessions.clear()
            
            logger.info(f"Force cleaned up {session_count} sessions")
            return session_count
            
        except Exception as e:
            logger.error(f"Force cleanup failed: {e}")
            return 0


# Global session generator instance
_session_generator: Optional[SessionIdGenerator] = None


def get_session_generator() -> SessionIdGenerator:
    """Get global session generator instance"""
    global _session_generator
    if _session_generator is None:
        _session_generator = SessionIdGenerator()
    return _session_generator


def generate_session_id(session_type: SessionType, 
                       owner_address: Optional[str] = None,
                       node_id: Optional[str] = None) -> SessionMetadata:
    """Convenience function to generate session ID"""
    generator = get_session_generator()
    return generator.generate_session_id(session_type, owner_address, node_id)


def validate_session_id(session_id: str) -> Optional[SessionMetadata]:
    """Convenience function to validate session ID"""
    generator = get_session_generator()
    return generator.validate_session_id(session_id)


def invalidate_session_id(session_id: str, reason: str = "used") -> bool:
    """Convenience function to invalidate session ID"""
    generator = get_session_generator()
    return generator.invalidate_session(session_id, reason)


if __name__ == "__main__":
    # Test session ID generation
    generator = SessionIdGenerator()
    
    # Generate test sessions
    user_session = generator.generate_session_id(
        SessionType.RDP_USER, 
        owner_address="TTestUserAddress123456789012345"
    )
    
    admin_session = generator.generate_session_id(
        SessionType.RDP_ADMIN,
        owner_address="TTestAdminAddress123456789012345"
    )
    
    node_session = generator.generate_session_id(
        SessionType.API_NODE,
        node_id="test_node_001"
    )
    
    print(f"Generated sessions:")
    print(f"User: {user_session.session_id}")
    print(f"Admin: {admin_session.session_id}")
    print(f"Node: {node_session.session_id}")
    
    # Test validation
    validated = generator.validate_session_id(user_session.session_id)
    print(f"Validation successful: {validated is not None}")
    
    # Test stats
    stats = generator.get_session_stats()
    print(f"Session stats: {stats}")