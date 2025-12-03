# Path: auth/user_manager.py
# User Management and Role-Based Access Control for Lucid RDP
# Implements user profiles, permissions, and session ownership verification

from __future__ import annotations

import logging
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from motor.motor_asyncio import AsyncIOMotorDatabase
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import hashes, serialization

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """User roles in the Lucid RDP system"""
    USER = "user"                    # Regular user - session participant
    NODE_WORKER = "node_worker"      # Node worker - validates and processes
    ADMIN = "admin"                  # System administrator
    OBSERVER = "observer"            # Read-only observer
    SERVER = "server"                # Original server node
    DEV = "dev"                      # Developer with elevated access

class KYCStatus(Enum):
    """KYC verification status"""
    NONE = "none"
    PENDING = "pending" 
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"

class SessionPermission(Enum):
    """Session-level permissions"""
    CREATE_SESSION = "session_create"
    JOIN_SESSION = "session_join"
    OBSERVE_SESSION = "session_observe"
    TERMINATE_SESSION = "session_terminate"
    MANAGE_POLICY = "policy_manage"
    VIEW_AUDIT = "audit_view"
    EXPORT_DATA = "data_export"
    ADMIN_ACCESS = "admin_access"

@dataclass
class UserProfile:
    """Complete user profile with authentication and authorization data"""
    user_id: str
    tron_address: str
    role: UserRole = UserRole.USER
    kyc_status: KYCStatus = KYCStatus.NONE
    permissions: Set[SessionPermission] = field(default_factory=set)
    
    # Authentication data
    public_key: Optional[str] = None
    hardware_wallet_verified: bool = False
    hardware_wallet_info: Optional[Dict[str, Any]] = None
    
    # Session data
    active_sessions: List[str] = field(default_factory=list)
    session_count_total: int = 0
    session_count_monthly: int = 0
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    # Security
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    
    # Metadata
    device_fingerprints: List[str] = field(default_factory=list)
    ip_addresses: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "_id": self.user_id,
            "tron_address": self.tron_address,
            "role": self.role.value,
            "kyc_status": self.kyc_status.value,
            "permissions": [p.value for p in self.permissions],
            "public_key": self.public_key,
            "hardware_wallet_verified": self.hardware_wallet_verified,
            "hardware_wallet_info": self.hardware_wallet_info,
            "active_sessions": self.active_sessions,
            "session_count_total": self.session_count_total,
            "session_count_monthly": self.session_count_monthly,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "last_activity": self.last_activity,
            "failed_login_attempts": self.failed_login_attempts,
            "locked_until": self.locked_until,
            "password_changed_at": self.password_changed_at,
            "device_fingerprints": self.device_fingerprints,
            "ip_addresses": self.ip_addresses
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UserProfile:
        """Create from dictionary from database"""
        return cls(
            user_id=data["_id"],
            tron_address=data["tron_address"],
            role=UserRole(data.get("role", "user")),
            kyc_status=KYCStatus(data.get("kyc_status", "none")),
            permissions=set(SessionPermission(p) for p in data.get("permissions", [])),
            public_key=data.get("public_key"),
            hardware_wallet_verified=data.get("hardware_wallet_verified", False),
            hardware_wallet_info=data.get("hardware_wallet_info"),
            active_sessions=data.get("active_sessions", []),
            session_count_total=data.get("session_count_total", 0),
            session_count_monthly=data.get("session_count_monthly", 0),
            created_at=data.get("created_at", datetime.now(timezone.utc)),
            last_login=data.get("last_login"),
            last_activity=data.get("last_activity"),
            failed_login_attempts=data.get("failed_login_attempts", 0),
            locked_until=data.get("locked_until"),
            password_changed_at=data.get("password_changed_at"),
            device_fingerprints=data.get("device_fingerprints", []),
            ip_addresses=data.get("ip_addresses", [])
        )

@dataclass
class SessionOwnership:
    """Session ownership record"""
    session_id: str
    owner_address: str
    owner_user_id: str
    created_at: datetime
    access_level: str = "full"  # full, observer, restricted
    participants: List[str] = field(default_factory=list)
    observers: List[str] = field(default_factory=list)
    terminated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.session_id,
            "owner_address": self.owner_address,
            "owner_user_id": self.owner_user_id,
            "created_at": self.created_at,
            "access_level": self.access_level,
            "participants": self.participants,
            "observers": self.observers,
            "terminated_at": self.terminated_at
        }

class UserManager:
    """
    Manages user accounts, authentication, and authorization.
    
    Handles user profiles, role-based access control, session ownership,
    and integration with hardware wallet authentication.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.role_permissions = self._initialize_role_permissions()
    
    def _initialize_role_permissions(self) -> Dict[UserRole, Set[SessionPermission]]:
        """Initialize default permissions for each role"""
        return {
            UserRole.USER: {
                SessionPermission.CREATE_SESSION,
                SessionPermission.JOIN_SESSION,
                SessionPermission.OBSERVE_SESSION,
                SessionPermission.VIEW_AUDIT
            },
            UserRole.NODE_WORKER: {
                SessionPermission.CREATE_SESSION,
                SessionPermission.JOIN_SESSION,
                SessionPermission.OBSERVE_SESSION,
                SessionPermission.TERMINATE_SESSION,
                SessionPermission.VIEW_AUDIT,
                SessionPermission.EXPORT_DATA
            },
            UserRole.ADMIN: set(SessionPermission),  # All permissions
            UserRole.OBSERVER: {
                SessionPermission.OBSERVE_SESSION,
                SessionPermission.VIEW_AUDIT
            },
            UserRole.SERVER: set(SessionPermission),  # All permissions
            UserRole.DEV: {
                SessionPermission.CREATE_SESSION,
                SessionPermission.JOIN_SESSION,
                SessionPermission.OBSERVE_SESSION,
                SessionPermission.TERMINATE_SESSION,
                SessionPermission.MANAGE_POLICY,
                SessionPermission.VIEW_AUDIT,
                SessionPermission.EXPORT_DATA
            }
        }
    
    async def create_user(
        self, 
        tron_address: str, 
        public_key: Optional[str] = None,
        role: UserRole = UserRole.USER,
        hardware_wallet_info: Optional[Dict[str, Any]] = None
    ) -> UserProfile:
        """Create new user profile"""
        try:
            # Generate user ID from TRON address
            user_id = hashlib.sha256(tron_address.encode()).hexdigest()[:16]
            
            # Get default permissions for role
            default_permissions = self.role_permissions.get(role, set())
            
            user = UserProfile(
                user_id=user_id,
                tron_address=tron_address,
                role=role,
                permissions=default_permissions.copy(),
                public_key=public_key,
                hardware_wallet_verified=bool(hardware_wallet_info),
                hardware_wallet_info=hardware_wallet_info
            )
            
            # Store in database
            await self.db["users"].replace_one(
                {"_id": user_id},
                user.to_dict(),
                upsert=True
            )
            
            logger.info(f"Created user: {user_id} with role: {role.value}")
            return user
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
    
    async def get_user_by_tron_address(self, tron_address: str) -> Optional[UserProfile]:
        """Get user by TRON address"""
        try:
            user_id = hashlib.sha256(tron_address.encode()).hexdigest()[:16]
            return await self.get_user_by_id(user_id)
        except Exception as e:
            logger.error(f"Failed to get user by TRON address: {e}")
            return None
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserProfile]:
        """Get user by user ID"""
        try:
            doc = await self.db["users"].find_one({"_id": user_id})
            if doc:
                return UserProfile.from_dict(doc)
            return None
        except Exception as e:
            logger.error(f"Failed to get user by ID: {e}")
            return None
    
    async def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Get user by user ID (alias for get_user_by_id for compatibility)"""
        return await self.get_user_by_id(user_id)
    
    async def update_user(self, user: UserProfile) -> bool:
        """Update user profile"""
        try:
            result = await self.db["users"].replace_one(
                {"_id": user.user_id},
                user.to_dict()
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update user: {e}")
            return False
    
    async def authenticate_user(
        self, 
        tron_address: str, 
        signature: str, 
        message: str,
        public_key: str,
        hardware_wallet_info: Optional[Dict[str, Any]] = None
    ) -> Optional[UserProfile]:
        """Authenticate user with TRON signature"""
        try:
            # Get or create user
            user = await self.get_user_by_tron_address(tron_address)
            if not user:
                # Create new user on first login
                user = await self.create_user(
                    tron_address=tron_address,
                    public_key=public_key,
                    hardware_wallet_info=hardware_wallet_info
                )
            
            # Check if account is locked
            if user.locked_until and datetime.now(timezone.utc) < user.locked_until:
                logger.warning(f"User account locked: {user.user_id}")
                return None
            
            # Verify signature (simplified for demo)
            # In production, implement proper TRON signature verification
            signature_valid = len(signature) > 0 and len(public_key) > 0
            
            if signature_valid:
                # Reset failed attempts on successful login
                user.failed_login_attempts = 0
                user.locked_until = None
                user.last_login = datetime.now(timezone.utc)
                user.last_activity = datetime.now(timezone.utc)
                
                # Update public key if provided
                if public_key and user.public_key != public_key:
                    user.public_key = public_key
                
                # Update hardware wallet info
                if hardware_wallet_info:
                    user.hardware_wallet_verified = True
                    user.hardware_wallet_info = hardware_wallet_info
                
                await self.update_user(user)
                logger.info(f"User authenticated: {user.user_id}")
                return user
            else:
                # Increment failed attempts
                user.failed_login_attempts += 1
                
                # Lock account after 5 failed attempts
                if user.failed_login_attempts >= 5:
                    user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
                    logger.warning(f"User account locked after failed attempts: {user.user_id}")
                
                await self.update_user(user)
                return None
                
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return None
    
    async def verify_session_ownership(
        self, 
        session_id: str, 
        user_id: str, 
        access_level: str = "full"
    ) -> bool:
        """Verify user owns or has access to session"""
        try:
            ownership = await self.db["session_ownership"].find_one({"_id": session_id})
            
            if not ownership:
                return False
            
            # Check if user is the owner
            if ownership["owner_user_id"] == user_id:
                return True
            
            # Check if user is a participant
            if user_id in ownership.get("participants", []):
                return True
            
            # Check if user is an observer and requesting observer access
            if access_level == "observer" and user_id in ownership.get("observers", []):
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to verify session ownership: {e}")
            return False
    
    async def create_session_ownership(
        self, 
        session_id: str, 
        owner_address: str, 
        access_level: str = "full"
    ) -> bool:
        """Create session ownership record"""
        try:
            # Get owner user ID
            owner_user_id = hashlib.sha256(owner_address.encode()).hexdigest()[:16]
            
            ownership = SessionOwnership(
                session_id=session_id,
                owner_address=owner_address,
                owner_user_id=owner_user_id,
                created_at=datetime.now(timezone.utc),
                access_level=access_level
            )
            
            await self.db["session_ownership"].insert_one(ownership.to_dict())
            
            # Update user's active sessions
            user = await self.get_user_by_id(owner_user_id)
            if user:
                user.active_sessions.append(session_id)
                user.session_count_total += 1
                user.session_count_monthly += 1
                await self.update_user(user)
            
            logger.info(f"Session ownership created: {session_id} -> {owner_user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create session ownership: {e}")
            return False
    
    async def add_session_participant(
        self, 
        session_id: str, 
        participant_address: str,
        role: str = "participant"
    ) -> bool:
        """Add participant to session"""
        try:
            participant_user_id = hashlib.sha256(participant_address.encode()).hexdigest()[:16]
            
            update_field = "participants" if role == "participant" else "observers"
            
            result = await self.db["session_ownership"].update_one(
                {"_id": session_id},
                {"$addToSet": {update_field: participant_user_id}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to add session participant: {e}")
            return False
    
    async def has_permission(self, user_id: str, permission: SessionPermission) -> bool:
        """Check if user has specific permission"""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False
            
            return permission in user.permissions
            
        except Exception as e:
            logger.error(f"Failed to check user permission: {e}")
            return False
    
    async def update_user_role(self, user_id: str, new_role: UserRole) -> bool:
        """Update user role and permissions"""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False
            
            user.role = new_role
            user.permissions = self.role_permissions.get(new_role, set()).copy()
            
            return await self.update_user(user)
            
        except Exception as e:
            logger.error(f"Failed to update user role: {e}")
            return False
    
    async def update_kyc_status(self, user_id: str, kyc_status: KYCStatus) -> bool:
        """Update user KYC status"""
        try:
            user = await self.get_user_by_id(user_id)
            if not user:
                return False
            
            user.kyc_status = kyc_status
            
            # Update permissions based on KYC status
            if kyc_status == KYCStatus.VERIFIED:
                # Add additional permissions for verified users
                user.permissions.add(SessionPermission.EXPORT_DATA)
            
            return await self.update_user(user)
            
        except Exception as e:
            logger.error(f"Failed to update KYC status: {e}")
            return False
    
    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's sessions (owned and participating)"""
        try:
            sessions = []
            
            # Get owned sessions
            owned_cursor = self.db["session_ownership"].find({"owner_user_id": user_id})
            async for doc in owned_cursor:
                sessions.append({
                    "session_id": doc["_id"],
                    "role": "owner",
                    "access_level": doc["access_level"],
                    "created_at": doc["created_at"]
                })
            
            # Get participating sessions
            participating_cursor = self.db["session_ownership"].find(
                {"participants": user_id}
            )
            async for doc in participating_cursor:
                sessions.append({
                    "session_id": doc["_id"],
                    "role": "participant", 
                    "access_level": "restricted",
                    "created_at": doc["created_at"]
                })
            
            # Get observer sessions
            observer_cursor = self.db["session_ownership"].find(
                {"observers": user_id}
            )
            async for doc in observer_cursor:
                sessions.append({
                    "session_id": doc["_id"],
                    "role": "observer",
                    "access_level": "observer",
                    "created_at": doc["created_at"]
                })
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get user sessions: {e}")
            return []
    
    async def cleanup_expired_sessions(self):
        """Clean up expired session ownerships"""
        try:
            # Remove sessions older than 24 hours that are not explicitly terminated
            cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            
            result = await self.db["session_ownership"].delete_many({
                "created_at": {"$lt": cutoff},
                "terminated_at": None
            })
            
            if result.deleted_count > 0:
                logger.info(f"Cleaned up {result.deleted_count} expired session ownerships")
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
    
    async def ensure_indexes(self):
        """Ensure database indexes"""
        try:
            # Users collection indexes
            await self.db["users"].create_index("tron_address", unique=True)
            await self.db["users"].create_index("role")
            await self.db["users"].create_index("kyc_status")
            await self.db["users"].create_index("last_login")
            
            # Session ownership indexes
            await self.db["session_ownership"].create_index("owner_user_id")
            await self.db["session_ownership"].create_index("participants")
            await self.db["session_ownership"].create_index("observers")
            await self.db["session_ownership"].create_index("created_at")
            
            logger.info("User manager indexes created")
            
        except Exception as e:
            logger.warning(f"Failed to create user manager indexes: {e}")


# Global user manager
_user_manager: Optional[UserManager] = None

def get_user_manager(db: AsyncIOMotorDatabase) -> UserManager:
    """Get global user manager instance"""
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager(db)
    return _user_manager