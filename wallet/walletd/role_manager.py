# LUCID Wallet Role Manager - Role-Based Access Control
# Implements comprehensive role-based access control for wallet operations
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

# Configuration from environment
ROLE_SESSION_TIMEOUT_HOURS = 8
ROLE_MAX_FAILED_ATTEMPTS = 5
ROLE_LOCKOUT_DURATION_MINUTES = 30
ROLE_AUDIT_LOG_RETENTION_DAYS = 90


class WalletRole(Enum):
    """Wallet operation roles"""
    VIEWER = "viewer"                    # Read-only access to wallet info
    USER = "user"                       # Standard wallet operations
    OPERATOR = "operator"               # Wallet management operations
    ADMIN = "admin"                     # Administrative operations
    MASTER = "master"                   # Full control including role management
    AUDITOR = "auditor"                 # Audit and compliance operations
    RECOVERY = "recovery"               # Emergency recovery operations


class Permission(Enum):
    """Wallet permissions"""
    # Viewing permissions
    VIEW_WALLET_INFO = "view_wallet_info"
    VIEW_BALANCE = "view_balance"
    VIEW_TRANSACTION_HISTORY = "view_transaction_history"
    VIEW_KEY_INFO = "view_key_info"
    
    # Transaction permissions
    SEND_TRANSACTION = "send_transaction"
    SIGN_TRANSACTION = "sign_transaction"
    BROADCAST_TRANSACTION = "broadcast_transaction"
    
    # Key management permissions
    GENERATE_KEY = "generate_key"
    IMPORT_KEY = "import_key"
    EXPORT_KEY = "export_key"
    DELETE_KEY = "delete_key"
    ROTATE_KEY = "rotate_key"
    
    # Wallet management permissions
    CREATE_WALLET = "create_wallet"
    DELETE_WALLET = "delete_wallet"
    BACKUP_WALLET = "backup_wallet"
    RESTORE_WALLET = "restore_wallet"
    CHANGE_PASSPHRASE = "change_passphrase"
    
    # Role management permissions
    ASSIGN_ROLE = "assign_role"
    REVOKE_ROLE = "revoke_role"
    MODIFY_ROLE = "modify_role"
    VIEW_ROLES = "view_roles"
    
    # Audit permissions
    VIEW_AUDIT_LOG = "view_audit_log"
    EXPORT_AUDIT_LOG = "export_audit_log"
    
    # Recovery permissions
    EMERGENCY_RECOVERY = "emergency_recovery"
    RESET_WALLET = "reset_wallet"
    
    # Multi-signature permissions
    CREATE_MULTISIG = "create_multisig"
    MANAGE_MULTISIG = "manage_multisig"
    SIGN_MULTISIG = "sign_multisig"


class AccessLevel(Enum):
    """Access level hierarchy"""
    DENIED = "denied"
    READ_ONLY = "read_only"
    LIMITED = "limited"
    STANDARD = "standard"
    ELEVATED = "elevated"
    ADMIN = "admin"
    MASTER = "master"


class SessionStatus(Enum):
    """Role session status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


@dataclass
class RoleDefinition:
    """Role definition with permissions"""
    role_id: str
    name: str
    description: str
    permissions: Set[Permission]
    access_level: AccessLevel
    max_session_duration: timedelta = timedelta(hours=ROLE_SESSION_TIMEOUT_HOURS)
    can_assign_roles: List[WalletRole] = field(default_factory=list)
    requires_mfa: bool = False
    requires_approval: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoleSession:
    """Active role session"""
    session_id: str
    user_id: str
    wallet_id: str
    role: WalletRole
    permissions: Set[Permission]
    created_at: datetime
    expires_at: datetime
    last_activity: datetime
    status: SessionStatus = SessionStatus.ACTIVE
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoleAssignment:
    """Role assignment to user"""
    assignment_id: str
    user_id: str
    wallet_id: str
    role: WalletRole
    assigned_by: str
    assigned_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditEvent:
    """Audit event for role operations"""
    event_id: str
    timestamp: datetime
    event_type: str
    user_id: str
    wallet_id: str
    role: Optional[WalletRole]
    action: str
    resource: str
    result: str  # success, failure, denied
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class RoleManager:
    """
    Role-based access control manager for wallet operations.
    
    Features:
    - Hierarchical role system with granular permissions
    - Session-based access control with timeout
    - Role assignment and revocation
    - Comprehensive audit logging
    - Multi-factor authentication support
    - Emergency access procedures
    - Permission inheritance and delegation
    """
    
    def __init__(self, wallet_id: str):
        """Initialize role manager for wallet"""
        self.wallet_id = wallet_id
        self.role_definitions: Dict[WalletRole, RoleDefinition] = {}
        self.active_sessions: Dict[str, RoleSession] = {}
        self.role_assignments: Dict[str, RoleAssignment] = {}
        self.audit_events: List[AuditEvent] = []
        
        # Security settings
        self.max_failed_attempts = ROLE_MAX_FAILED_ATTEMPTS
        self.lockout_duration = timedelta(minutes=ROLE_LOCKOUT_DURATION_MINUTES)
        self.audit_retention_days = ROLE_AUDIT_LOG_RETENTION_DAYS
        
        # Failed attempts tracking
        self.failed_attempts: Dict[str, Dict[str, Any]] = {}
        
        # Initialize default roles
        self._initialize_default_roles()
        
        logger.info(f"RoleManager initialized for wallet: {wallet_id}")
    
    def _initialize_default_roles(self) -> None:
        """Initialize default role definitions"""
        # Viewer role - read-only access
        self.role_definitions[WalletRole.VIEWER] = RoleDefinition(
            role_id="viewer",
            name="Wallet Viewer",
            description="Read-only access to wallet information",
            permissions={
                Permission.VIEW_WALLET_INFO,
                Permission.VIEW_BALANCE,
                Permission.VIEW_TRANSACTION_HISTORY,
                Permission.VIEW_KEY_INFO
            },
            access_level=AccessLevel.READ_ONLY
        )
        
        # User role - standard operations
        self.role_definitions[WalletRole.USER] = RoleDefinition(
            role_id="user",
            name="Wallet User",
            description="Standard wallet operations",
            permissions={
                Permission.VIEW_WALLET_INFO,
                Permission.VIEW_BALANCE,
                Permission.VIEW_TRANSACTION_HISTORY,
                Permission.VIEW_KEY_INFO,
                Permission.SEND_TRANSACTION,
                Permission.SIGN_TRANSACTION,
                Permission.BACKUP_WALLET
            },
            access_level=AccessLevel.STANDARD
        )
        
        # Operator role - wallet management
        self.role_definitions[WalletRole.OPERATOR] = RoleDefinition(
            role_id="operator",
            name="Wallet Operator",
            description="Wallet management operations",
            permissions={
                Permission.VIEW_WALLET_INFO,
                Permission.VIEW_BALANCE,
                Permission.VIEW_TRANSACTION_HISTORY,
                Permission.VIEW_KEY_INFO,
                Permission.SEND_TRANSACTION,
                Permission.SIGN_TRANSACTION,
                Permission.BROADCAST_TRANSACTION,
                Permission.GENERATE_KEY,
                Permission.IMPORT_KEY,
                Permission.EXPORT_KEY,
                Permission.DELETE_KEY,
                Permission.BACKUP_WALLET,
                Permission.RESTORE_WALLET,
                Permission.CHANGE_PASSPHRASE,
                Permission.ROTATE_KEY
            },
            access_level=AccessLevel.ELEVATED,
            can_assign_roles=[WalletRole.VIEWER, WalletRole.USER]
        )
        
        # Admin role - administrative operations
        self.role_definitions[WalletRole.ADMIN] = RoleDefinition(
            role_id="admin",
            name="Wallet Administrator",
            description="Administrative wallet operations",
            permissions=set(Permission),  # All permissions except role management
            access_level=AccessLevel.ADMIN,
            can_assign_roles=[WalletRole.VIEWER, WalletRole.USER, WalletRole.OPERATOR],
            requires_mfa=True
        )
        # Remove role management permissions
        admin_perms = self.role_definitions[WalletRole.ADMIN].permissions
        admin_perms.discard(Permission.ASSIGN_ROLE)
        admin_perms.discard(Permission.REVOKE_ROLE)
        admin_perms.discard(Permission.MODIFY_ROLE)
        
        # Master role - full control
        self.role_definitions[WalletRole.MASTER] = RoleDefinition(
            role_id="master",
            name="Wallet Master",
            description="Full wallet control including role management",
            permissions=set(Permission),  # All permissions
            access_level=AccessLevel.MASTER,
            can_assign_roles=list(WalletRole),
            requires_mfa=True,
            requires_approval=True
        )
        
        # Auditor role - audit operations
        self.role_definitions[WalletRole.AUDITOR] = RoleDefinition(
            role_id="auditor",
            name="Wallet Auditor",
            description="Audit and compliance operations",
            permissions={
                Permission.VIEW_WALLET_INFO,
                Permission.VIEW_TRANSACTION_HISTORY,
                Permission.VIEW_KEY_INFO,
                Permission.VIEW_ROLES,
                Permission.VIEW_AUDIT_LOG,
                Permission.EXPORT_AUDIT_LOG
            },
            access_level=AccessLevel.READ_ONLY,
            requires_mfa=True
        )
        
        # Recovery role - emergency recovery
        self.role_definitions[WalletRole.RECOVERY] = RoleDefinition(
            role_id="recovery",
            name="Recovery Agent",
            description="Emergency recovery operations",
            permissions={
                Permission.VIEW_WALLET_INFO,
                Permission.EMERGENCY_RECOVERY,
                Permission.RESET_WALLET,
                Permission.RESTORE_WALLET,
                Permission.CHANGE_PASSPHRASE
            },
            access_level=AccessLevel.MASTER,
            requires_mfa=True,
            requires_approval=True
        )
    
    async def assign_role(
        self,
        user_id: str,
        role: WalletRole,
        assigned_by: str,
        expires_at: Optional[datetime] = None,
        conditions: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """Assign role to user"""
        try:
            # Check if assigner has permission
            if not await self._check_permission(assigned_by, Permission.ASSIGN_ROLE):
                await self._log_audit_event(
                    assigned_by, "assign_role", f"role_assignment_{role.value}",
                    "denied", f"Insufficient permissions to assign {role.value} role"
                )
                return False, "Insufficient permissions to assign role"
            
            # Check if assigner can assign this role
            assigner_role = await self._get_user_active_role(assigned_by)
            if not assigner_role:
                return False, "Assigner has no active role"
            
            assigner_definition = self.role_definitions.get(assigner_role)
            if not assigner_definition or role not in assigner_definition.can_assign_roles:
                await self._log_audit_event(
                    assigned_by, "assign_role", f"role_assignment_{role.value}",
                    "denied", f"Cannot assign {role.value} role"
                )
                return False, f"Cannot assign {role.value} role"
            
            # Create role assignment
            assignment_id = secrets.token_hex(16)
            assignment = RoleAssignment(
                assignment_id=assignment_id,
                user_id=user_id,
                wallet_id=self.wallet_id,
                role=role,
                assigned_by=assigned_by,
                assigned_at=datetime.now(timezone.utc),
                expires_at=expires_at,
                conditions=conditions or {},
                metadata=metadata or {}
            )
            
            self.role_assignments[assignment_id] = assignment
            
            await self._log_audit_event(
                assigned_by, "assign_role", f"role_assignment_{role.value}",
                "success", f"Assigned {role.value} role to {user_id}"
            )
            
            logger.info(f"Role {role.value} assigned to user {user_id} by {assigned_by}")
            return True, assignment_id
            
        except Exception as e:
            logger.error(f"Failed to assign role: {e}")
            await self._log_audit_event(
                assigned_by, "assign_role", f"role_assignment_{role.value}",
                "failure", f"Error: {str(e)}"
            )
            return False, f"Error: {str(e)}"
    
    async def revoke_role(
        self,
        user_id: str,
        role: WalletRole,
        revoked_by: str,
        reason: str = "Manual revocation"
    ) -> bool:
        """Revoke role from user"""
        try:
            # Check if revoker has permission
            if not await self._check_permission(revoked_by, Permission.REVOKE_ROLE):
                await self._log_audit_event(
                    revoked_by, "revoke_role", f"role_revocation_{role.value}",
                    "denied", f"Insufficient permissions to revoke {role.value} role"
                )
                return False
            
            # Find and revoke assignment
            revoked_count = 0
            for assignment in self.role_assignments.values():
                if (assignment.user_id == user_id and 
                    assignment.role == role and 
                    assignment.is_active):
                    assignment.is_active = False
                    revoked_count += 1
            
            # Revoke active sessions
            for session in self.active_sessions.values():
                if session.user_id == user_id and session.role == role:
                    session.status = SessionStatus.REVOKED
            
            await self._log_audit_event(
                revoked_by, "revoke_role", f"role_revocation_{role.value}",
                "success", f"Revoked {role.value} role from {user_id}. Reason: {reason}"
            )
            
            logger.info(f"Role {role.value} revoked from user {user_id} by {revoked_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke role: {e}")
            await self._log_audit_event(
                revoked_by, "revoke_role", f"role_revocation_{role.value}",
                "failure", f"Error: {str(e)}"
            )
            return False
    
    async def create_session(
        self,
        user_id: str,
        role: WalletRole,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """Create new role session"""
        try:
            # Check if user has active role assignment
            has_assignment = False
            for assignment in self.role_assignments.values():
                if (assignment.user_id == user_id and 
                    assignment.role == role and 
                    assignment.is_active and
                    (not assignment.expires_at or assignment.expires_at > datetime.now(timezone.utc))):
                    has_assignment = True
                    break
            
            if not has_assignment:
                await self._log_audit_event(
                    user_id, "create_session", f"session_{role.value}",
                    "denied", f"No active assignment for {role.value} role"
                )
                return False, "No active role assignment"
            
            # Check role requirements
            role_definition = self.role_definitions.get(role)
            if not role_definition or not role_definition.is_active:
                return False, "Role not available"
            
            # Create session
            session_id = secrets.token_hex(16)
            session = RoleSession(
                session_id=session_id,
                user_id=user_id,
                wallet_id=self.wallet_id,
                role=role,
                permissions=role_definition.permissions,
                created_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + role_definition.max_session_duration,
                last_activity=datetime.now(timezone.utc),
                ip_address=ip_address,
                user_agent=user_agent,
                metadata=metadata or {}
            )
            
            self.active_sessions[session_id] = session
            
            await self._log_audit_event(
                user_id, "create_session", f"session_{role.value}",
                "success", f"Created session {session_id} with {role.value} role"
            )
            
            logger.info(f"Created session {session_id} for user {user_id} with {role.value} role")
            return True, session_id
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            await self._log_audit_event(
                user_id, "create_session", f"session_{role.value}",
                "failure", f"Error: {str(e)}"
            )
            return False, None
    
    async def check_permission(
        self,
        session_id: str,
        permission: Permission
    ) -> bool:
        """Check if session has specific permission"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                return False
            
            # Check session status
            if session.status != SessionStatus.ACTIVE:
                return False
            
            # Check session expiration
            if datetime.now(timezone.utc) > session.expires_at:
                session.status = SessionStatus.EXPIRED
                return False
            
            # Update last activity
            session.last_activity = datetime.now(timezone.utc)
            
            # Check permission
            has_permission = permission in session.permissions
            
            await self._log_audit_event(
                session.user_id, "check_permission", permission.value,
                "success" if has_permission else "denied",
                f"Permission check for {permission.value}"
            )
            
            return has_permission
            
        except Exception as e:
            logger.error(f"Failed to check permission: {e}")
            return False
    
    async def get_user_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active roles for user"""
        try:
            user_roles = []
            
            for assignment in self.role_assignments.values():
                if (assignment.user_id == user_id and 
                    assignment.is_active and
                    (not assignment.expires_at or assignment.expires_at > datetime.now(timezone.utc))):
                    
                    role_definition = self.role_definitions.get(assignment.role)
                    if role_definition:
                        user_roles.append({
                            "role": assignment.role.value,
                            "role_name": role_definition.name,
                            "permissions": [p.value for p in role_definition.permissions],
                            "access_level": role_definition.access_level.value,
                            "assigned_at": assignment.assigned_at.isoformat(),
                            "expires_at": assignment.expires_at.isoformat() if assignment.expires_at else None,
                            "assigned_by": assignment.assigned_by,
                            "conditions": assignment.conditions,
                            "metadata": assignment.metadata
                        })
            
            return user_roles
            
        except Exception as e:
            logger.error(f"Failed to get user roles: {e}")
            return []
    
    async def get_active_sessions(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get active sessions"""
        try:
            sessions = []
            
            for session in self.active_sessions.values():
                if user_id and session.user_id != user_id:
                    continue
                
                if session.status == SessionStatus.ACTIVE:
                    sessions.append({
                        "session_id": session.session_id,
                        "user_id": session.user_id,
                        "role": session.role.value,
                        "created_at": session.created_at.isoformat(),
                        "expires_at": session.expires_at.isoformat(),
                        "last_activity": session.last_activity.isoformat(),
                        "ip_address": session.ip_address,
                        "user_agent": session.user_agent,
                        "metadata": session.metadata
                    })
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get active sessions: {e}")
            return []
    
    async def revoke_session(self, session_id: str, revoked_by: str, reason: str = "Manual revocation") -> bool:
        """Revoke specific session"""
        try:
            session = self.active_sessions.get(session_id)
            if not session:
                return False
            
            session.status = SessionStatus.REVOKED
            
            await self._log_audit_event(
                revoked_by, "revoke_session", f"session_{session.session_id}",
                "success", f"Revoked session for user {session.user_id}. Reason: {reason}"
            )
            
            logger.info(f"Session {session_id} revoked by {revoked_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke session: {e}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Cleanup expired sessions"""
        try:
            current_time = datetime.now(timezone.utc)
            expired_sessions = []
            
            for session_id, session in self.active_sessions.items():
                if (session.status == SessionStatus.EXPIRED or 
                    current_time > session.expires_at):
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                session = self.active_sessions[session_id]
                session.status = SessionStatus.EXPIRED
                
                await self._log_audit_event(
                    session.user_id, "session_expired", f"session_{session_id}",
                    "success", "Session expired automatically"
                )
            
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            return len(expired_sessions)
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def get_audit_log(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get audit log entries"""
        try:
            filtered_events = []
            
            for event in self.audit_events:
                # Apply filters
                if start_time and event.timestamp < start_time:
                    continue
                if end_time and event.timestamp > end_time:
                    continue
                if user_id and event.user_id != user_id:
                    continue
                if event_type and event.event_type != event_type:
                    continue
                
                filtered_events.append({
                    "event_id": event.event_id,
                    "timestamp": event.timestamp.isoformat(),
                    "event_type": event.event_type,
                    "user_id": event.user_id,
                    "wallet_id": event.wallet_id,
                    "role": event.role.value if event.role else None,
                    "action": event.action,
                    "resource": event.resource,
                    "result": event.result,
                    "ip_address": event.ip_address,
                    "user_agent": event.user_agent,
                    "details": event.details
                })
            
            # Sort by timestamp (newest first) and limit
            filtered_events.sort(key=lambda x: x["timestamp"], reverse=True)
            return filtered_events[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            return []
    
    async def _check_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if user has specific permission"""
        try:
            # Check active sessions
            for session in self.active_sessions.values():
                if (session.user_id == user_id and 
                    session.status == SessionStatus.ACTIVE and
                    datetime.now(timezone.utc) <= session.expires_at):
                    if permission in session.permissions:
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check permission: {e}")
            return False
    
    async def _get_user_active_role(self, user_id: str) -> Optional[WalletRole]:
        """Get user's active role"""
        try:
            for session in self.active_sessions.values():
                if (session.user_id == user_id and 
                    session.status == SessionStatus.ACTIVE and
                    datetime.now(timezone.utc) <= session.expires_at):
                    return session.role
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get user active role: {e}")
            return None
    
    async def _log_audit_event(
        self,
        user_id: str,
        action: str,
        resource: str,
        result: str,
        details: str,
        role: Optional[WalletRole] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """Log audit event"""
        try:
            event = AuditEvent(
                event_id=secrets.token_hex(16),
                timestamp=datetime.now(timezone.utc),
                event_type=action,
                user_id=user_id,
                wallet_id=self.wallet_id,
                role=role,
                action=action,
                resource=resource,
                result=result,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"message": details}
            )
            
            self.audit_events.append(event)
            
            # Cleanup old audit events
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.audit_retention_days)
            self.audit_events = [e for e in self.audit_events if e.timestamp > cutoff_date]
            
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
    
    async def get_role_manager_status(self) -> Dict[str, Any]:
        """Get role manager status"""
        return {
            "wallet_id": self.wallet_id,
            "total_roles": len(self.role_definitions),
            "active_assignments": len([a for a in self.role_assignments.values() if a.is_active]),
            "active_sessions": len([s for s in self.active_sessions.values() if s.status == SessionStatus.ACTIVE]),
            "audit_events_count": len(self.audit_events),
            "role_definitions": {
                role.value: {
                    "name": definition.name,
                    "description": definition.description,
                    "permissions_count": len(definition.permissions),
                    "access_level": definition.access_level.value,
                    "requires_mfa": definition.requires_mfa,
                    "requires_approval": definition.requires_approval
                }
                for role, definition in self.role_definitions.items()
            }
        }


# Global role managers
_role_managers: Dict[str, RoleManager] = {}


def get_role_manager(wallet_id: str) -> Optional[RoleManager]:
    """Get role manager for wallet"""
    return _role_managers.get(wallet_id)


def create_role_manager(wallet_id: str) -> RoleManager:
    """Create new role manager for wallet"""
    role_manager = RoleManager(wallet_id)
    _role_managers[wallet_id] = role_manager
    return role_manager


async def main():
    """Main function for testing"""
    import asyncio
    
    # Create role manager
    role_manager = create_role_manager("test_wallet_001")
    
    # Assign master role to admin user
    success, assignment_id = await role_manager.assign_role(
        user_id="admin_user",
        role=WalletRole.MASTER,
        assigned_by="system"
    )
    print(f"Role assignment: {success}, ID: {assignment_id}")
    
    # Create session
    success, session_id = await role_manager.create_session(
        user_id="admin_user",
        role=WalletRole.MASTER,
        ip_address="192.168.1.100",
        user_agent="test_client"
    )
    print(f"Session creation: {success}, ID: {session_id}")
    
    if success and session_id:
        # Check permissions
        can_view = await role_manager.check_permission(session_id, Permission.VIEW_WALLET_INFO)
        can_assign = await role_manager.check_permission(session_id, Permission.ASSIGN_ROLE)
        print(f"Can view wallet: {can_view}")
        print(f"Can assign roles: {can_assign}")
        
        # Assign user role to regular user
        success, _ = await role_manager.assign_role(
            user_id="regular_user",
            role=WalletRole.USER,
            assigned_by="admin_user"
        )
        print(f"User role assignment: {success}")
    
    # Get user roles
    admin_roles = await role_manager.get_user_roles("admin_user")
    print(f"Admin roles: {len(admin_roles)}")
    
    # Get audit log
    audit_log = await role_manager.get_audit_log(limit=10)
    print(f"Audit events: {len(audit_log)}")
    
    # Get status
    status = await role_manager.get_role_manager_status()
    print(f"Role manager status: {status}")


if __name__ == "__main__":
    asyncio.run(main())
