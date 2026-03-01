# LUCID RDP Access Controller - Security and Permissions Management
# Implements trust-nothing access control for RDP sessions
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# Database integration
try:
    from motor.motor_asyncio import AsyncIOMotorDatabase
    HAS_MOTOR = True
except ImportError:
    HAS_MOTOR = False
    AsyncIOMotorDatabase = None

logger = logging.getLogger(__name__)

# Configuration from environment
ACCESS_CONTROL_DB = os.getenv("ACCESS_CONTROL_DB", "lucid_access")
JWT_SECRET = os.getenv("JWT_SECRET", "lucid_jwt_secret_key_change_in_production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
MAX_FAILED_ATTEMPTS = int(os.getenv("MAX_FAILED_ATTEMPTS", "5"))
LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))


class AccessLevel(Enum):
    """Access level hierarchy"""
    DENIED = "denied"           # No access
    READ_ONLY = "read_only"     # View-only access
    LIMITED = "limited"         # Limited functionality
    STANDARD = "standard"       # Standard user access
    ELEVATED = "elevated"       # Elevated privileges
    ADMIN = "admin"            # Administrative access
    SUPER_ADMIN = "super_admin" # Full system access


class ResourceType(Enum):
    """Resource types for access control"""
    SESSION = "session"
    RECORDING = "recording"
    CLIPBOARD = "clipboard"
    FILE_TRANSFER = "file_transfer"
    AUDIO = "audio"
    VIDEO = "video"
    SYSTEM = "system"
    ADMIN = "admin"
    BLOCKCHAIN = "blockchain"
    WALLET = "wallet"


class PermissionType(Enum):
    """Permission types"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    MANAGE = "manage"
    EXPORT = "export"
    IMPORT = "import"
    AUDIT = "audit"


class SecurityPolicy(Enum):
    """Security policy levels"""
    TRUST_NOTHING = "trust_nothing"     # Default-deny, explicit allow
    ZERO_TRUST = "zero_trust"           # Continuous verification
    STRICT = "strict"                   # High security requirements
    STANDARD = "standard"              # Standard security
    PERMISSIVE = "permissive"          # Lower security, higher usability


@dataclass
class AccessRule:
    """Access control rule definition"""
    rule_id: str
    name: str
    description: str
    resource_type: ResourceType
    permission_type: PermissionType
    access_level: AccessLevel
    conditions: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "resource_type": self.resource_type.value,
            "permission_type": self.permission_type.value,
            "access_level": self.access_level.value,
            "conditions": self.conditions,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "is_active": self.is_active
        }


@dataclass
class AccessRequest:
    """Access request for resource access"""
    request_id: str
    user_id: str
    session_id: str
    resource_type: ResourceType
    permission_type: PermissionType
    resource_id: str
    context: Dict[str, Any] = field(default_factory=dict)
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    justification: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.request_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "resource_type": self.resource_type.value,
            "permission_type": self.permission_type.value,
            "resource_id": self.resource_id,
            "context": self.context,
            "requested_at": self.requested_at,
            "expires_at": self.expires_at,
            "justification": self.justification
        }


@dataclass
class AccessDecision:
    """Access control decision result"""
    request_id: str
    decision: str  # "allow", "deny", "conditional"
    access_level: AccessLevel
    conditions: List[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None
    reasoning: Dict[str, Any] = field(default_factory=dict)
    decided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    decided_by: str = "system"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.request_id,
            "decision": self.decision,
            "access_level": self.access_level.value,
            "conditions": self.conditions,
            "expires_at": self.expires_at,
            "reasoning": self.reasoning,
            "decided_at": self.decided_at,
            "decided_by": self.decided_by
        }


@dataclass
class SecurityContext:
    """Security context for access decisions"""
    user_id: str
    session_id: str
    ip_address: str
    user_agent: str
    location: Optional[str] = None
    device_fingerprint: Optional[str] = None
    trust_score: float = 0.0
    risk_indicators: List[str] = field(default_factory=list)
    security_policy: SecurityPolicy = SecurityPolicy.TRUST_NOTHING
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "location": self.location,
            "device_fingerprint": self.device_fingerprint,
            "trust_score": self.trust_score,
            "risk_indicators": self.risk_indicators,
            "security_policy": self.security_policy.value,
            "timestamp": self.timestamp
        }


@dataclass
class SessionAccess:
    """Session-specific access permissions"""
    session_id: str
    user_id: str
    permissions: Set[Tuple[ResourceType, PermissionType]] = field(default_factory=set)
    access_level: AccessLevel = AccessLevel.STANDARD
    restrictions: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": f"{self.session_id}_{self.user_id}",
            "session_id": self.session_id,
            "user_id": self.user_id,
            "permissions": [(rt.value, pt.value) for rt, pt in self.permissions],
            "access_level": self.access_level.value,
            "restrictions": self.restrictions,
            "expires_at": self.expires_at,
            "created_at": self.created_at
        }


class AccessController:
    """
    Comprehensive access control system for Lucid RDP.
    
    Implements trust-nothing security model with:
    - Role-based access control (RBAC)
    - Attribute-based access control (ABAC)
    - Zero-trust continuous verification
    - Session-based permissions
    - Resource-level access control
    - Audit logging and monitoring
    """
    
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        self.db = db
        self.active_sessions: Dict[str, SessionAccess] = {}
        self.access_rules: Dict[str, AccessRule] = {}
        self.security_contexts: Dict[str, SecurityContext] = {}
        self.failed_attempts: Dict[str, List[datetime]] = {}
        self.lockouts: Dict[str, datetime] = {}
        
        # Security policies
        self.default_policy = SecurityPolicy.TRUST_NOTHING
        self.policy_rules = self._initialize_policy_rules()
        
        # JWT configuration
        self.jwt_secret = JWT_SECRET
        self.jwt_algorithm = JWT_ALGORITHM
        
        logger.info("Access Controller initialized with trust-nothing security model")
    
    def _initialize_policy_rules(self) -> Dict[SecurityPolicy, Dict[str, Any]]:
        """Initialize security policy rules"""
        return {
            SecurityPolicy.TRUST_NOTHING: {
                "default_decision": "deny",
                "require_explicit_allow": True,
                "continuous_verification": True,
                "audit_all_actions": True,
                "max_session_duration": 60,  # minutes
                "require_mfa": True
            },
            SecurityPolicy.ZERO_TRUST: {
                "default_decision": "deny",
                "require_explicit_allow": True,
                "continuous_verification": True,
                "audit_all_actions": True,
                "max_session_duration": 30,  # minutes
                "require_mfa": True,
                "device_verification": True
            },
            SecurityPolicy.STRICT: {
                "default_decision": "deny",
                "require_explicit_allow": True,
                "continuous_verification": False,
                "audit_all_actions": True,
                "max_session_duration": 120,  # minutes
                "require_mfa": False
            },
            SecurityPolicy.STANDARD: {
                "default_decision": "allow",
                "require_explicit_allow": False,
                "continuous_verification": False,
                "audit_all_actions": False,
                "max_session_duration": 480,  # minutes
                "require_mfa": False
            },
            SecurityPolicy.PERMISSIVE: {
                "default_decision": "allow",
                "require_explicit_allow": False,
                "continuous_verification": False,
                "audit_all_actions": False,
                "max_session_duration": 1440,  # minutes
                "require_mfa": False
            }
        }
    
    async def start(self):
        """Start the access controller service"""
        try:
            if self.db:
                await self._setup_database_indexes()
                await self._load_access_rules()
                await self._load_active_sessions()
            
            # Start background tasks
            asyncio.create_task(self._cleanup_expired_sessions())
            asyncio.create_task(self._monitor_security_events())
            asyncio.create_task(self._update_trust_scores())
            
            logger.info("Access Controller started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Access Controller: {e}")
            return False
    
    async def stop(self):
        """Stop the access controller service"""
        try:
            # Save current state
            if self.db:
                await self._save_active_sessions()
                await self._save_access_rules()
            
            logger.info("Access Controller stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping Access Controller: {e}")
            return False
    
    async def create_access_rule(self, 
                                name: str,
                                description: str,
                                resource_type: ResourceType,
                                permission_type: PermissionType,
                                access_level: AccessLevel,
                                conditions: Optional[Dict[str, Any]] = None,
                                expires_at: Optional[datetime] = None,
                                created_by: str = "system") -> str:
        """Create a new access control rule"""
        try:
            rule_id = f"rule_{uuid.uuid4().hex[:8]}"
            
            rule = AccessRule(
                rule_id=rule_id,
                name=name,
                description=description,
                resource_type=resource_type,
                permission_type=permission_type,
                access_level=access_level,
                conditions=conditions or {},
                expires_at=expires_at,
                created_by=created_by
            )
            
            self.access_rules[rule_id] = rule
            
            if self.db:
                await self.db.access_rules.insert_one(rule.to_dict())
            
            logger.info(f"Created access rule: {rule_id}")
            return rule_id
            
        except Exception as e:
            logger.error(f"Failed to create access rule: {e}")
            raise
    
    async def evaluate_access(self, 
                            user_id: str,
                            session_id: str,
                            resource_type: ResourceType,
                            permission_type: PermissionType,
                            resource_id: str,
                            context: Optional[Dict[str, Any]] = None) -> AccessDecision:
        """Evaluate access request using trust-nothing model"""
        try:
            request_id = f"req_{uuid.uuid4().hex[:8]}"
            
            # Create access request
            access_request = AccessRequest(
                request_id=request_id,
                user_id=user_id,
                session_id=session_id,
                resource_type=resource_type,
                permission_type=permission_type,
                resource_id=resource_id,
                context=context or {}
            )
            
            # Get security context
            security_context = await self._get_security_context(user_id, session_id)
            
            # Apply trust-nothing policy
            decision = await self._apply_trust_nothing_policy(access_request, security_context)
            
            # Log decision
            await self._log_access_decision(decision)
            
            return decision
            
        except Exception as e:
            logger.error(f"Access evaluation failed: {e}")
            return AccessDecision(
                request_id=request_id,
                decision="deny",
                access_level=AccessLevel.DENIED,
                reasoning={"error": str(e)}
            )
    
    async def grant_session_access(self, 
                                 session_id: str,
                                 user_id: str,
                                 permissions: Set[Tuple[ResourceType, PermissionType]],
                                 access_level: AccessLevel = AccessLevel.STANDARD,
                                 expires_at: Optional[datetime] = None) -> bool:
        """Grant access permissions for a session"""
        try:
            session_access = SessionAccess(
                session_id=session_id,
                user_id=user_id,
                permissions=permissions,
                access_level=access_level,
                expires_at=expires_at
            )
            
            self.active_sessions[f"{session_id}_{user_id}"] = session_access
            
            if self.db:
                await self.db.session_access.replace_one(
                    {"_id": f"{session_id}_{user_id}"},
                    session_access.to_dict(),
                    upsert=True
                )
            
            logger.info(f"Granted session access: {session_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to grant session access: {e}")
            return False
    
    async def revoke_session_access(self, session_id: str, user_id: str) -> bool:
        """Revoke access permissions for a session"""
        try:
            key = f"{session_id}_{user_id}"
            
            if key in self.active_sessions:
                del self.active_sessions[key]
            
            if self.db:
                await self.db.session_access.delete_one({"_id": key})
            
            logger.info(f"Revoked session access: {session_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke session access: {e}")
            return False
    
    async def check_permission(self, 
                             user_id: str,
                             session_id: str,
                             resource_type: ResourceType,
                             permission_type: PermissionType) -> bool:
        """Check if user has specific permission in session"""
        try:
            key = f"{session_id}_{user_id}"
            session_access = self.active_sessions.get(key)
            
            if not session_access:
                return False
            
            # Check if session has expired
            if session_access.expires_at and datetime.now(timezone.utc) > session_access.expires_at:
                await self.revoke_session_access(session_id, user_id)
                return False
            
            # Check permission
            required_permission = (resource_type, permission_type)
            return required_permission in session_access.permissions
            
        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return False
    
    async def get_user_permissions(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Get all permissions for a user in a session"""
        try:
            key = f"{session_id}_{user_id}"
            session_access = self.active_sessions.get(key)
            
            if not session_access:
                return {"permissions": [], "access_level": "denied"}
            
            return {
                "permissions": [(rt.value, pt.value) for rt, pt in session_access.permissions],
                "access_level": session_access.access_level.value,
                "restrictions": session_access.restrictions,
                "expires_at": session_access.expires_at
            }
            
        except Exception as e:
            logger.error(f"Failed to get user permissions: {e}")
            return {"permissions": [], "access_level": "denied"}
    
    async def _apply_trust_nothing_policy(self, 
                                        access_request: AccessRequest,
                                        security_context: SecurityContext) -> AccessDecision:
        """Apply trust-nothing security policy"""
        try:
            # Default deny
            decision = "deny"
            access_level = AccessLevel.DENIED
            conditions = []
            reasoning = {}
            
            # Check for explicit allow rules
            for rule in self.access_rules.values():
                if not rule.is_active:
                    continue
                
                if rule.expires_at and datetime.now(timezone.utc) > rule.expires_at:
                    continue
                
                # Check rule conditions
                if self._evaluate_rule_conditions(rule, access_request, security_context):
                    decision = "allow"
                    access_level = rule.access_level
                    conditions = ["explicit_rule_match"]
                    reasoning = {
                        "rule_id": rule.rule_id,
                        "rule_name": rule.name,
                        "access_level": rule.access_level.value
                    }
                    break
            
            # Check session access
            if decision == "deny":
                session_key = f"{access_request.session_id}_{access_request.user_id}"
                session_access = self.active_sessions.get(session_key)
                
                if session_access:
                    required_permission = (access_request.resource_type, access_request.permission_type)
                    if required_permission in session_access.permissions:
                        decision = "allow"
                        access_level = session_access.access_level
                        conditions = ["session_permission_match"]
                        reasoning = {
                            "session_id": access_request.session_id,
                            "access_level": session_access.access_level.value
                        }
            
            # Apply security policy restrictions
            policy_rules = self.policy_rules.get(security_context.security_policy, {})
            if policy_rules.get("require_explicit_allow", True) and decision == "allow":
                # Additional verification required
                if not self._verify_explicit_allow(access_request, security_context):
                    decision = "conditional"
                    conditions.append("explicit_verification_required")
                    reasoning["verification_required"] = True
            
            return AccessDecision(
                request_id=access_request.request_id,
                decision=decision,
                access_level=access_level,
                conditions=conditions,
                reasoning=reasoning
            )
            
        except Exception as e:
            logger.error(f"Trust-nothing policy application failed: {e}")
            return AccessDecision(
                request_id=access_request.request_id,
                decision="deny",
                access_level=AccessLevel.DENIED,
                reasoning={"error": str(e)}
            )
    
    def _evaluate_rule_conditions(self, 
                                rule: AccessRule,
                                access_request: AccessRequest,
                                security_context: SecurityContext) -> bool:
        """Evaluate rule conditions for access request"""
        try:
            conditions = rule.conditions
            
            # Check user conditions
            if "user_id" in conditions:
                if access_request.user_id not in conditions["user_id"]:
                    return False
            
            # Check session conditions
            if "session_id" in conditions:
                if access_request.session_id not in conditions["session_id"]:
                    return False
            
            # Check resource conditions
            if "resource_type" in conditions:
                if access_request.resource_type.value not in conditions["resource_type"]:
                    return False
            
            # Check permission conditions
            if "permission_type" in conditions:
                if access_request.permission_type.value not in conditions["permission_type"]:
                    return False
            
            # Check trust score conditions
            if "min_trust_score" in conditions:
                if security_context.trust_score < conditions["min_trust_score"]:
                    return False
            
            # Check time conditions
            if "time_restrictions" in conditions:
                current_hour = datetime.now().hour
                allowed_hours = conditions["time_restrictions"].get("allowed_hours", [])
                if allowed_hours and current_hour not in allowed_hours:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Rule condition evaluation failed: {e}")
            return False
    
    def _verify_explicit_allow(self, 
                             access_request: AccessRequest,
                             security_context: SecurityContext) -> bool:
        """Verify explicit allow for trust-nothing model"""
        try:
            # Check for explicit allow in session permissions
            session_key = f"{access_request.session_id}_{access_request.user_id}"
            session_access = self.active_sessions.get(session_key)
            
            if not session_access:
                return False
            
            required_permission = (access_request.resource_type, access_request.permission_type)
            return required_permission in session_access.permissions
            
        except Exception as e:
            logger.error(f"Explicit allow verification failed: {e}")
            return False
    
    async def _get_security_context(self, user_id: str, session_id: str) -> SecurityContext:
        """Get or create security context for user/session"""
        try:
            context_key = f"{user_id}_{session_id}"
            
            if context_key not in self.security_contexts:
                # Create new security context
                self.security_contexts[context_key] = SecurityContext(
                    user_id=user_id,
                    session_id=session_id,
                    ip_address="unknown",
                    user_agent="unknown",
                    security_policy=self.default_policy
                )
            
            return self.security_contexts[context_key]
            
        except Exception as e:
            logger.error(f"Failed to get security context: {e}")
            return SecurityContext(
                user_id=user_id,
                session_id=session_id,
                ip_address="unknown",
                user_agent="unknown",
                security_policy=self.default_policy
            )
    
    async def _log_access_decision(self, decision: AccessDecision):
        """Log access control decision"""
        try:
            if self.db:
                await self.db.access_decisions.insert_one(decision.to_dict())
            
            logger.info(f"Access decision: {decision.decision} for request {decision.request_id}")
            
        except Exception as e:
            logger.error(f"Failed to log access decision: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Clean up expired session access"""
        while True:
            try:
                current_time = datetime.now(timezone.utc)
                expired_sessions = []
                
                for key, session_access in self.active_sessions.items():
                    if session_access.expires_at and current_time > session_access.expires_at:
                        expired_sessions.append(key)
                
                for key in expired_sessions:
                    session_id, user_id = key.split("_", 1)
                    await self.revoke_session_access(session_id, user_id)
                
                if expired_sessions:
                    logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Session cleanup failed: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_security_events(self):
        """Monitor security events and update trust scores"""
        while True:
            try:
                # Update trust scores based on recent activity
                for context_key, context in self.security_contexts.items():
                    # Simple trust score calculation
                    # In production, this would be more sophisticated
                    context.trust_score = min(100.0, context.trust_score + 1.0)
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error(f"Security monitoring failed: {e}")
                await asyncio.sleep(300)
    
    async def _update_trust_scores(self):
        """Update trust scores based on user behavior"""
        while True:
            try:
                # This would integrate with behavioral analysis
                # For now, just maintain existing scores
                await asyncio.sleep(600)  # Update every 10 minutes
                
            except Exception as e:
                logger.error(f"Trust score update failed: {e}")
                await asyncio.sleep(600)
    
    async def _setup_database_indexes(self):
        """Setup database indexes for access control"""
        try:
            if not self.db:
                return
            
            # Access rules indexes
            await self.db.access_rules.create_index("resource_type")
            await self.db.access_rules.create_index("permission_type")
            await self.db.access_rules.create_index("access_level")
            await self.db.access_rules.create_index("is_active")
            await self.db.access_rules.create_index("expires_at")
            
            # Session access indexes
            await self.db.session_access.create_index("session_id")
            await self.db.session_access.create_index("user_id")
            await self.db.session_access.create_index("expires_at")
            
            # Access decisions indexes
            await self.db.access_decisions.create_index("request_id")
            await self.db.access_decisions.create_index("decision")
            await self.db.access_decisions.create_index("decided_at")
            
            logger.info("Database indexes created for access control")
            
        except Exception as e:
            logger.error(f"Failed to setup database indexes: {e}")
    
    async def _load_access_rules(self):
        """Load access rules from database"""
        try:
            if not self.db:
                return
            
            rules_cursor = self.db.access_rules.find({"is_active": True})
            async for rule_doc in rules_cursor:
                rule = AccessRule(
                    rule_id=rule_doc["_id"],
                    name=rule_doc["name"],
                    description=rule_doc["description"],
                    resource_type=ResourceType(rule_doc["resource_type"]),
                    permission_type=PermissionType(rule_doc["permission_type"]),
                    access_level=AccessLevel(rule_doc["access_level"]),
                    conditions=rule_doc.get("conditions", {}),
                    expires_at=rule_doc.get("expires_at"),
                    created_at=rule_doc["created_at"],
                    created_by=rule_doc.get("created_by", ""),
                    is_active=rule_doc.get("is_active", True)
                )
                self.access_rules[rule.rule_id] = rule
            
            logger.info(f"Loaded {len(self.access_rules)} access rules")
            
        except Exception as e:
            logger.error(f"Failed to load access rules: {e}")
    
    async def _load_active_sessions(self):
        """Load active session access from database"""
        try:
            if not self.db:
                return
            
            sessions_cursor = self.db.session_access.find({})
            async for session_doc in sessions_cursor:
                session_access = SessionAccess(
                    session_id=session_doc["session_id"],
                    user_id=session_doc["user_id"],
                    permissions=set((ResourceType(rt), PermissionType(pt)) 
                                  for rt, pt in session_doc.get("permissions", [])),
                    access_level=AccessLevel(session_doc["access_level"]),
                    restrictions=session_doc.get("restrictions", {}),
                    expires_at=session_doc.get("expires_at"),
                    created_at=session_doc["created_at"]
                )
                key = f"{session_access.session_id}_{session_access.user_id}"
                self.active_sessions[key] = session_access
            
            logger.info(f"Loaded {len(self.active_sessions)} active sessions")
            
        except Exception as e:
            logger.error(f"Failed to load active sessions: {e}")
    
    async def _save_active_sessions(self):
        """Save active session access to database"""
        try:
            if not self.db:
                return
            
            for session_access in self.active_sessions.values():
                await self.db.session_access.replace_one(
                    {"_id": f"{session_access.session_id}_{session_access.user_id}"},
                    session_access.to_dict(),
                    upsert=True
                )
            
            logger.info("Saved active sessions to database")
            
        except Exception as e:
            logger.error(f"Failed to save active sessions: {e}")
    
    async def _save_access_rules(self):
        """Save access rules to database"""
        try:
            if not self.db:
                return
            
            for rule in self.access_rules.values():
                await self.db.access_rules.replace_one(
                    {"_id": rule.rule_id},
                    rule.to_dict(),
                    upsert=True
                )
            
            logger.info("Saved access rules to database")
            
        except Exception as e:
            logger.error(f"Failed to save access rules: {e}")


# Global access controller instance
_access_controller: Optional[AccessController] = None


def get_access_controller() -> Optional[AccessController]:
    """Get the global access controller instance"""
    return _access_controller


def create_access_controller(db: Optional[AsyncIOMotorDatabase] = None) -> AccessController:
    """Create and configure access controller"""
    global _access_controller
    _access_controller = AccessController(db)
    return _access_controller


async def start_access_controller():
    """Start the access controller service"""
    global _access_controller
    if _access_controller:
        await _access_controller.start()


async def stop_access_controller():
    """Stop the access controller service"""
    global _access_controller
    if _access_controller:
        await _access_controller.stop()


# Example usage and testing
async def test_access_controller():
    """Test access controller functionality"""
    try:
        # Create access controller
        controller = create_access_controller()
        await controller.start()
        
        # Create access rule
        rule_id = await controller.create_access_rule(
            name="Session Recording Access",
            description="Allow session recording for standard users",
            resource_type=ResourceType.RECORDING,
            permission_type=PermissionType.CREATE,
            access_level=AccessLevel.STANDARD
        )
        
        # Grant session access
        permissions = {
            (ResourceType.SESSION, PermissionType.CREATE),
            (ResourceType.RECORDING, PermissionType.CREATE),
            (ResourceType.CLIPBOARD, PermissionType.READ)
        }
        
        await controller.grant_session_access(
            session_id="test_session_001",
            user_id="test_user_001",
            permissions=permissions,
            access_level=AccessLevel.STANDARD
        )
        
        # Evaluate access
        decision = await controller.evaluate_access(
            user_id="test_user_001",
            session_id="test_session_001",
            resource_type=ResourceType.RECORDING,
            permission_type=PermissionType.CREATE,
            resource_id="recording_001"
        )
        
        print(f"Access decision: {decision.decision}")
        print(f"Access level: {decision.access_level.value}")
        print(f"Reasoning: {decision.reasoning}")
        
        # Check permission
        has_permission = await controller.check_permission(
            user_id="test_user_001",
            session_id="test_session_001",
            resource_type=ResourceType.CLIPBOARD,
            permission_type=PermissionType.READ
        )
        
        print(f"Has clipboard read permission: {has_permission}")
        
        # Get user permissions
        user_permissions = await controller.get_user_permissions(
            user_id="test_user_001",
            session_id="test_session_001"
        )
        
        print(f"User permissions: {user_permissions}")
        
        await controller.stop()
        print("Access controller test completed successfully")
        
    except Exception as e:
        print(f"Access controller test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_access_controller())
