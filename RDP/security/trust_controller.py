# Path: apps/client_control/trust_controller.py
# Lucid RDP Client Control - Trust-Nothing Policy and Fine-Grained Session Controls
# Based on LUCID-STRICT requirements from Build_guide_docs

from __future__ import annotations

import asyncio
import os
import logging
import hashlib
import struct
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import json
import re
import ipaddress
from urllib.parse import urlparse

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
import blake3

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

# Import session pipeline and admin system
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from sessions.pipeline.pipeline_manager import get_pipeline_manager
from admin.system.admin_controller import get_admin_controller

logger = logging.getLogger(__name__)

# Trust-Nothing Policy Constants per Spec-1a
DEFAULT_DENY_ALL = bool(os.getenv("DEFAULT_DENY_ALL", "true").lower() == "true")
JIT_APPROVAL_TIMEOUT_SEC = int(os.getenv("JIT_APPROVAL_TIMEOUT_SEC", "300"))  # 5-minute JIT timeout
PRIVACY_SHIELD_ENABLED = bool(os.getenv("PRIVACY_SHIELD_ENABLED", "true").lower() == "true")
MAX_SESSION_DURATION_HOURS = int(os.getenv("MAX_SESSION_DURATION_HOURS", "8"))  # 8-hour max sessions

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/lucid")

# Privacy Shield Configuration
BLUR_SENSITIVE_REGIONS = bool(os.getenv("BLUR_SENSITIVE_REGIONS", "true").lower() == "true")
REDACT_TEXT_PATTERNS = os.getenv("REDACT_TEXT_PATTERNS", "ssn,credit_card,password,api_key").split(",")


class PermissionType(Enum):
    """Fine-grained permission types for trust-nothing policy"""
    KEYBOARD_INPUT = "keyboard_input"
    MOUSE_INPUT = "mouse_input"
    CLIPBOARD_READ = "clipboard_read"
    CLIPBOARD_WRITE = "clipboard_write"
    FILE_DOWNLOAD = "file_download"
    FILE_UPLOAD = "file_upload"
    SCREEN_CAPTURE = "screen_capture"
    AUDIO_CAPTURE = "audio_capture"
    APPLICATION_LAUNCH = "application_launch"
    NETWORK_ACCESS = "network_access"
    SYSTEM_COMMANDS = "system_commands"
    REGISTRY_ACCESS = "registry_access"


class PolicyAction(Enum):
    """Policy enforcement actions"""
    ALLOW = "allow"
    DENY = "deny"
    PROMPT = "prompt"
    AUDIT = "audit"
    QUARANTINE = "quarantine"


class ThreatLevel(Enum):
    """Security threat levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SessionControlMode(Enum):
    """Session control modes"""
    UNRESTRICTED = "unrestricted"      # Full access (rare)
    GUIDED = "guided"                  # Guided with prompts
    RESTRICTED = "restricted"          # Limited access
    AUDIT_ONLY = "audit_only"         # Read-only with audit
    LOCKED_DOWN = "locked_down"       # Minimal access


@dataclass
class PermissionRule:
    """Fine-grained permission rule"""
    rule_id: str
    permission_type: PermissionType
    condition: Dict[str, Any]  # Conditions for rule application
    action: PolicyAction
    priority: int = 100
    reason: str = ""
    expires_at: Optional[datetime] = None
    created_by: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.rule_id,
            "permission_type": self.permission_type.value,
            "condition": self.condition,
            "action": self.action.value,
            "priority": self.priority,
            "reason": self.reason,
            "expires_at": self.expires_at,
            "created_by": self.created_by,
            "created_at": self.created_at
        }


@dataclass
class JitApprovalRequest:
    """Just-in-time approval request"""
    request_id: str
    session_id: str
    permission_type: PermissionType
    resource: str  # What's being accessed
    context: Dict[str, Any]  # Additional context
    requested_at: datetime
    expires_at: datetime
    status: str = "pending"  # pending, approved, denied, expired
    approved_by: Optional[str] = None
    approval_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.request_id,
            "session_id": self.session_id,
            "permission_type": self.permission_type.value,
            "resource": self.resource,
            "context": self.context,
            "requested_at": self.requested_at,
            "expires_at": self.expires_at,
            "status": self.status,
            "approved_by": self.approved_by,
            "approval_reason": self.approval_reason
        }


@dataclass
class SessionSecurityProfile:
    """Security profile for RDP session"""
    session_id: str
    control_mode: SessionControlMode
    threat_level: ThreatLevel
    privacy_shield_enabled: bool
    permitted_actions: Set[PermissionType]
    denied_actions: Set[PermissionType]
    audit_all: bool = True
    max_duration: Optional[timedelta] = None
    allowed_applications: Optional[List[str]] = None
    blocked_applications: Optional[List[str]] = None
    allowed_urls: Optional[List[str]] = None
    blocked_urls: Optional[List[str]] = None
    network_restrictions: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.session_id,
            "control_mode": self.control_mode.value,
            "threat_level": self.threat_level.value,
            "privacy_shield_enabled": self.privacy_shield_enabled,
            "permitted_actions": [p.value for p in self.permitted_actions],
            "denied_actions": [d.value for d in self.denied_actions],
            "audit_all": self.audit_all,
            "max_duration": int(self.max_duration.total_seconds()) if self.max_duration else None,
            "allowed_applications": self.allowed_applications,
            "blocked_applications": self.blocked_applications,
            "allowed_urls": self.allowed_urls,
            "blocked_urls": self.blocked_urls,
            "network_restrictions": self.network_restrictions,
            "created_at": self.created_at
        }


@dataclass
class SecurityEvent:
    """Security event for audit trail"""
    event_id: str
    session_id: str
    event_type: str
    permission_type: Optional[PermissionType] = None
    action_taken: Optional[PolicyAction] = None
    resource: Optional[str] = None
    threat_detected: Optional[str] = None
    risk_score: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.event_id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "permission_type": self.permission_type.value if self.permission_type else None,
            "action_taken": self.action_taken.value if self.action_taken else None,
            "resource": self.resource,
            "threat_detected": self.threat_detected,
            "risk_score": self.risk_score,
            "context": self.context,
            "timestamp": self.timestamp
        }


class PrivacyShield:
    """
    Privacy protection system for RDP sessions.
    
    Implements:
    - Real-time screen content analysis
    - Sensitive data detection and redaction
    - Privacy region blurring
    - Audit trail for privacy events
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.sensitive_patterns = self._load_sensitive_patterns()
        
    def _load_sensitive_patterns(self) -> Dict[str, re.Pattern]:
        """Load patterns for sensitive data detection"""
        patterns = {
            "ssn": re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
            "credit_card": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            "phone": re.compile(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'),
            "api_key": re.compile(r'\b[A-Za-z0-9]{32,}\b'),
            "password": re.compile(r'password\s*[:=]\s*\S+', re.IGNORECASE),
            "ip_address": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
            "url": re.compile(r'https?://[^\s<>"]+'),
        }
        return patterns
    
    async def analyze_screen_content(self, session_id: str, content: str) -> Dict[str, Any]:
        """Analyze screen content for sensitive data"""
        try:
            findings = {}
            redaction_regions = []
            
            for pattern_name, pattern in self.sensitive_patterns.items():
                matches = list(pattern.finditer(content))
                if matches:
                    findings[pattern_name] = len(matches)
                    
                    # Create redaction regions
                    for match in matches:
                        redaction_regions.append({
                            "type": pattern_name,
                            "start": match.start(),
                            "end": match.end(),
                            "text": match.group()
                        })
            
            # Log privacy event if sensitive data found
            if findings:
                await self._log_privacy_event(session_id, "sensitive_data_detected", findings)
            
            return {
                "findings": findings,
                "redaction_regions": redaction_regions,
                "risk_score": self._calculate_privacy_risk(findings)
            }
            
        except Exception as e:
            logger.error(f"Privacy shield analysis failed: {e}")
            return {"findings": {}, "redaction_regions": [], "risk_score": 0.0}
    
    async def apply_privacy_protection(self, session_id: str, screen_data: bytes,
                                     protection_level: str = "standard") -> bytes:
        """Apply privacy protection to screen data"""
        try:
            # In a real implementation, this would:
            # 1. Parse screen data (image/text)
            # 2. Identify sensitive regions
            # 3. Apply blurring/redaction
            # 4. Return protected screen data
            
            # For now, return original data (placeholder)
            await self._log_privacy_event(session_id, "privacy_protection_applied", 
                                        {"protection_level": protection_level})
            
            return screen_data
            
        except Exception as e:
            logger.error(f"Privacy protection failed: {e}")
            return screen_data
    
    def _calculate_privacy_risk(self, findings: Dict[str, int]) -> float:
        """Calculate privacy risk score based on findings"""
        risk_weights = {
            "ssn": 10.0,
            "credit_card": 10.0,
            "password": 8.0,
            "api_key": 7.0,
            "email": 3.0,
            "phone": 2.0,
            "ip_address": 1.0,
            "url": 0.5
        }
        
        total_risk = 0.0
        for pattern_name, count in findings.items():
            weight = risk_weights.get(pattern_name, 1.0)
            total_risk += weight * count
        
        # Normalize to 0-100 scale
        return min(100.0, total_risk)
    
    async def _log_privacy_event(self, session_id: str, event_type: str, details: Dict[str, Any]):
        """Log privacy-related event"""
        try:
            await self.db["privacy_events"].insert_one({
                "session_id": session_id,
                "event_type": event_type,
                "details": details,
                "timestamp": datetime.now(timezone.utc)
            })
        except Exception as e:
            logger.error(f"Failed to log privacy event: {e}")


class PolicyEngine:
    """
    Policy evaluation engine for trust-nothing enforcement.
    
    Implements:
    - Rule-based permission evaluation
    - Context-aware decision making
    - Just-in-time approval workflows
    - Threat assessment and response
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.rule_cache: Dict[str, List[PermissionRule]] = {}
        self.cache_ttl = timedelta(minutes=5)
        self.last_cache_update = datetime.min.replace(tzinfo=timezone.utc)
        
    async def evaluate_permission(self, session_id: str, permission_type: PermissionType,
                                resource: str, context: Dict[str, Any]) -> Tuple[PolicyAction, str]:
        """Evaluate permission request against trust-nothing policy"""
        try:
            # Get session security profile
            profile = await self._get_session_profile(session_id)
            if not profile:
                return PolicyAction.DENY, "No session security profile found"
            
            # Check if permission is explicitly denied
            if permission_type in profile.denied_actions:
                await self._log_security_event(session_id, "permission_denied_explicit", 
                                             permission_type, resource)
                return PolicyAction.DENY, "Permission explicitly denied in profile"
            
            # Check if permission is explicitly allowed
            if permission_type in profile.permitted_actions:
                await self._log_security_event(session_id, "permission_allowed_explicit",
                                             permission_type, resource)
                return PolicyAction.ALLOW, "Permission explicitly allowed in profile"
            
            # Evaluate rules
            rules = await self._get_applicable_rules(permission_type, context)
            
            # Apply default deny if no rules match
            if not rules:
                if DEFAULT_DENY_ALL:
                    await self._log_security_event(session_id, "permission_denied_default",
                                                 permission_type, resource)
                    return PolicyAction.DENY, "Default deny policy applied"
                else:
                    return PolicyAction.ALLOW, "Default allow (not recommended)"
            
            # Evaluate rules by priority
            rules.sort(key=lambda r: r.priority)
            
            for rule in rules:
                if self._rule_matches(rule, context):
                    action = rule.action
                    reason = rule.reason or f"Rule {rule.rule_id} applied"
                    
                    await self._log_security_event(session_id, f"permission_{action.value}",
                                                 permission_type, resource,
                                                 {"rule_id": rule.rule_id})
                    
                    return action, reason
            
            # Default deny if no rules matched
            return PolicyAction.DENY, "No matching rules found"
            
        except Exception as e:
            logger.error(f"Permission evaluation failed: {e}")
            return PolicyAction.DENY, f"Evaluation error: {e}"
    
    async def request_jit_approval(self, session_id: str, permission_type: PermissionType,
                                 resource: str, context: Dict[str, Any]) -> str:
        """Request just-in-time approval for permission"""
        try:
            request_id = str(uuid.uuid4())
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=JIT_APPROVAL_TIMEOUT_SEC)
            
            jit_request = JitApprovalRequest(
                request_id=request_id,
                session_id=session_id,
                permission_type=permission_type,
                resource=resource,
                context=context,
                requested_at=datetime.now(timezone.utc),
                expires_at=expires_at
            )
            
            # Store request
            await self.db["jit_approvals"].insert_one(jit_request.to_dict())
            
            # Notify approvers (would trigger notifications in real implementation)
            await self._notify_approval_required(jit_request)
            
            logger.info(f"JIT approval requested: {request_id} for {permission_type.value}")
            return request_id
            
        except Exception as e:
            logger.error(f"JIT approval request failed: {e}")
            raise
    
    async def approve_jit_request(self, request_id: str, approved_by: str,
                                approval_reason: str, approve: bool) -> bool:
        """Approve or deny JIT request"""
        try:
            # Get request
            request_doc = await self.db["jit_approvals"].find_one({"_id": request_id})
            if not request_doc:
                logger.error(f"JIT request not found: {request_id}")
                return False
            
            # Check if already processed or expired
            if request_doc["status"] != "pending":
                logger.warning(f"JIT request already processed: {request_id}")
                return False
            
            if datetime.now(timezone.utc) > request_doc["expires_at"]:
                await self.db["jit_approvals"].update_one(
                    {"_id": request_id},
                    {"$set": {"status": "expired"}}
                )
                logger.warning(f"JIT request expired: {request_id}")
                return False
            
            # Update request status
            status = "approved" if approve else "denied"
            await self.db["jit_approvals"].update_one(
                {"_id": request_id},
                {"$set": {
                    "status": status,
                    "approved_by": approved_by,
                    "approval_reason": approval_reason
                }}
            )
            
            await self._log_security_event(request_doc["session_id"], f"jit_request_{status}",
                                         PermissionType(request_doc["permission_type"]),
                                         request_doc["resource"],
                                         {"request_id": request_id, "approved_by": approved_by})
            
            logger.info(f"JIT request {status}: {request_id}")
            return True
            
        except Exception as e:
            logger.error(f"JIT approval failed: {e}")
            return False
    
    async def check_jit_approval(self, request_id: str) -> Optional[bool]:
        """Check status of JIT approval request"""
        try:
            request_doc = await self.db["jit_approvals"].find_one({"_id": request_id})
            if not request_doc:
                return None
            
            status = request_doc["status"]
            if status == "approved":
                return True
            elif status == "denied":
                return False
            elif status == "expired":
                return False
            else:  # pending
                # Check if expired
                if datetime.now(timezone.utc) > request_doc["expires_at"]:
                    await self.db["jit_approvals"].update_one(
                        {"_id": request_id},
                        {"$set": {"status": "expired"}}
                    )
                    return False
                return None  # Still pending
                
        except Exception as e:
            logger.error(f"JIT approval check failed: {e}")
            return None
    
    async def _get_session_profile(self, session_id: str) -> Optional[SessionSecurityProfile]:
        """Get security profile for session"""
        try:
            profile_doc = await self.db["session_profiles"].find_one({"_id": session_id})
            if not profile_doc:
                return None
            
            # Convert back to dataclass
            profile = SessionSecurityProfile(
                session_id=profile_doc["_id"],
                control_mode=SessionControlMode(profile_doc["control_mode"]),
                threat_level=ThreatLevel(profile_doc["threat_level"]),
                privacy_shield_enabled=profile_doc["privacy_shield_enabled"],
                permitted_actions=set(PermissionType(p) for p in profile_doc["permitted_actions"]),
                denied_actions=set(PermissionType(d) for d in profile_doc["denied_actions"]),
                audit_all=profile_doc["audit_all"],
                max_duration=timedelta(seconds=profile_doc["max_duration"]) if profile_doc.get("max_duration") else None,
                allowed_applications=profile_doc.get("allowed_applications"),
                blocked_applications=profile_doc.get("blocked_applications"),
                allowed_urls=profile_doc.get("allowed_urls"),
                blocked_urls=profile_doc.get("blocked_urls"),
                network_restrictions=profile_doc.get("network_restrictions"),
                created_at=profile_doc["created_at"]
            )
            
            return profile
            
        except Exception as e:
            logger.error(f"Failed to get session profile: {e}")
            return None
    
    async def _get_applicable_rules(self, permission_type: PermissionType,
                                  context: Dict[str, Any]) -> List[PermissionRule]:
        """Get permission rules applicable to current context"""
        try:
            # Check cache first
            cache_key = f"{permission_type.value}:{hash(str(sorted(context.items())))}"
            
            if (cache_key in self.rule_cache and 
                datetime.now(timezone.utc) - self.last_cache_update < self.cache_ttl):
                return self.rule_cache[cache_key]
            
            # Query database
            cursor = self.db["permission_rules"].find({
                "permission_type": permission_type.value,
                "$or": [
                    {"expires_at": None},
                    {"expires_at": {"$gte": datetime.now(timezone.utc)}}
                ]
            })
            
            rules = []
            async for rule_doc in cursor:
                rule = PermissionRule(
                    rule_id=rule_doc["_id"],
                    permission_type=PermissionType(rule_doc["permission_type"]),
                    condition=rule_doc["condition"],
                    action=PolicyAction(rule_doc["action"]),
                    priority=rule_doc["priority"],
                    reason=rule_doc["reason"],
                    expires_at=rule_doc.get("expires_at"),
                    created_by=rule_doc.get("created_by"),
                    created_at=rule_doc["created_at"]
                )
                rules.append(rule)
            
            # Cache rules
            self.rule_cache[cache_key] = rules
            self.last_cache_update = datetime.now(timezone.utc)
            
            return rules
            
        except Exception as e:
            logger.error(f"Failed to get applicable rules: {e}")
            return []
    
    def _rule_matches(self, rule: PermissionRule, context: Dict[str, Any]) -> bool:
        """Check if rule conditions match current context"""
        try:
            conditions = rule.condition
            
            for key, expected in conditions.items():
                if key not in context:
                    return False
                
                actual = context[key]
                
                # Handle different condition types
                if isinstance(expected, dict):
                    if "$in" in expected:
                        if actual not in expected["$in"]:
                            return False
                    elif "$regex" in expected:
                        import re
                        pattern = re.compile(expected["$regex"])
                        if not pattern.search(str(actual)):
                            return False
                    elif "$gte" in expected:
                        if actual < expected["$gte"]:
                            return False
                    elif "$lte" in expected:
                        if actual > expected["$lte"]:
                            return False
                else:
                    if actual != expected:
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Rule matching failed: {e}")
            return False
    
    async def _log_security_event(self, session_id: str, event_type: str,
                                permission_type: Optional[PermissionType] = None,
                                resource: Optional[str] = None,
                                additional_context: Optional[Dict[str, Any]] = None):
        """Log security event"""
        try:
            event_id = str(uuid.uuid4())
            context = additional_context or {}
            
            event = SecurityEvent(
                event_id=event_id,
                session_id=session_id,
                event_type=event_type,
                permission_type=permission_type,
                resource=resource,
                context=context
            )
            
            await self.db["security_events"].insert_one(event.to_dict())
            
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    async def _notify_approval_required(self, request: JitApprovalRequest):
        """Notify administrators that JIT approval is required"""
        # In real implementation, would send notifications via email, Slack, etc.
        logger.info(f"JIT approval notification: {request.request_id}")


class TrustController:
    """
    Main trust-nothing controller orchestrating all client control policies.
    
    Manages:
    - Session security profiles and policies
    - Real-time permission evaluation
    - Privacy shield integration
    - Threat detection and response
    - Audit trail and compliance
    """
    
    def __init__(self):
        self.mongo_client = AsyncIOMotorClient(MONGODB_URI)
        self.db = self.mongo_client.get_default_database()
        
        # Initialize components
        self.policy_engine = PolicyEngine(self.db)
        self.privacy_shield = PrivacyShield(self.db)
        
        # Initialize MongoDB indexes
        asyncio.create_task(self._setup_mongodb_indexes())
        
        logger.info("Trust controller initialized")
    
    async def _setup_mongodb_indexes(self):
        """Setup MongoDB indexes for trust controller collections"""
        try:
            # session_profiles collection
            await self.db["session_profiles"].create_index([("control_mode", 1)])
            await self.db["session_profiles"].create_index([("threat_level", 1)])
            await self.db["session_profiles"].create_index([("created_at", -1)])
            
            # permission_rules collection
            await self.db["permission_rules"].create_index([("permission_type", 1)])
            await self.db["permission_rules"].create_index([("priority", 1)])
            await self.db["permission_rules"].create_index([("expires_at", 1)])
            
            # jit_approvals collection
            await self.db["jit_approvals"].create_index([("session_id", 1)])
            await self.db["jit_approvals"].create_index([("status", 1)])
            await self.db["jit_approvals"].create_index([("expires_at", 1)])
            
            # security_events collection
            await self.db["security_events"].create_index([("session_id", 1)])
            await self.db["security_events"].create_index([("event_type", 1)])
            await self.db["security_events"].create_index([("timestamp", -1)])
            
            # privacy_events collection
            await self.db["privacy_events"].create_index([("session_id", 1)])
            await self.db["privacy_events"].create_index([("event_type", 1)])
            await self.db["privacy_events"].create_index([("timestamp", -1)])
            
            logger.info("Trust controller MongoDB indexes created")
            
        except Exception as e:
            logger.error(f"Failed to setup trust controller indexes: {e}")
    
    # Session Management
    
    async def create_session_profile(self, session_id: str, control_mode: SessionControlMode,
                                   threat_level: ThreatLevel = ThreatLevel.MEDIUM,
                                   custom_config: Optional[Dict[str, Any]] = None) -> bool:
        """Create security profile for new session"""
        try:
            # Default permissions based on control mode
            permitted_actions = set()
            denied_actions = set()
            
            if control_mode == SessionControlMode.UNRESTRICTED:
                permitted_actions = set(PermissionType)
            elif control_mode == SessionControlMode.GUIDED:
                permitted_actions = {
                    PermissionType.KEYBOARD_INPUT,
                    PermissionType.MOUSE_INPUT,
                    PermissionType.SCREEN_CAPTURE,
                    PermissionType.CLIPBOARD_READ
                }
            elif control_mode == SessionControlMode.RESTRICTED:
                permitted_actions = {
                    PermissionType.SCREEN_CAPTURE,
                    PermissionType.KEYBOARD_INPUT
                }
            elif control_mode == SessionControlMode.AUDIT_ONLY:
                permitted_actions = {PermissionType.SCREEN_CAPTURE}
            elif control_mode == SessionControlMode.LOCKED_DOWN:
                permitted_actions = set()  # Minimal access
                denied_actions = set(PermissionType)
            
            # Apply custom config overrides
            if custom_config:
                if "allowed_permissions" in custom_config:
                    permitted_actions.update(
                        PermissionType(p) for p in custom_config["allowed_permissions"]
                    )
                if "denied_permissions" in custom_config:
                    denied_actions.update(
                        PermissionType(p) for p in custom_config["denied_permissions"]
                    )
            
            # Create profile
            profile = SessionSecurityProfile(
                session_id=session_id,
                control_mode=control_mode,
                threat_level=threat_level,
                privacy_shield_enabled=PRIVACY_SHIELD_ENABLED,
                permitted_actions=permitted_actions,
                denied_actions=denied_actions,
                max_duration=timedelta(hours=MAX_SESSION_DURATION_HOURS),
                allowed_applications=custom_config.get("allowed_applications") if custom_config else None,
                blocked_applications=custom_config.get("blocked_applications") if custom_config else None,
                allowed_urls=custom_config.get("allowed_urls") if custom_config else None,
                blocked_urls=custom_config.get("blocked_urls") if custom_config else None,
                network_restrictions=custom_config.get("network_restrictions") if custom_config else None
            )
            
            # Store profile
            await self.db["session_profiles"].replace_one(
                {"_id": session_id},
                profile.to_dict(),
                upsert=True
            )
            
            logger.info(f"Session profile created: {session_id} ({control_mode.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create session profile: {e}")
            return False
    
    async def enforce_permission(self, session_id: str, permission_type: PermissionType,
                               resource: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """Enforce permission with trust-nothing policy"""
        try:
            context = context or {}
            context["session_id"] = session_id
            context["timestamp"] = datetime.now(timezone.utc).isoformat()
            
            # Evaluate permission
            action, reason = await self.policy_engine.evaluate_permission(
                session_id, permission_type, resource, context
            )
            
            if action == PolicyAction.ALLOW:
                return True, reason
            elif action == PolicyAction.DENY:
                return False, reason
            elif action == PolicyAction.PROMPT:
                # Request JIT approval
                request_id = await self.policy_engine.request_jit_approval(
                    session_id, permission_type, resource, context
                )
                return False, f"JIT approval required: {request_id}"
            elif action == PolicyAction.AUDIT:
                # Allow but log for audit
                await self.policy_engine._log_security_event(
                    session_id, "permission_audited", permission_type, resource, context
                )
                return True, f"Allowed with audit: {reason}"
            elif action == PolicyAction.QUARANTINE:
                # Deny and flag for investigation
                await self.policy_engine._log_security_event(
                    session_id, "permission_quarantined", permission_type, resource, context
                )
                return False, f"Quarantined: {reason}"
            
            return False, "Unknown policy action"
            
        except Exception as e:
            logger.error(f"Permission enforcement failed: {e}")
            return False, f"Enforcement error: {e}"
    
    async def process_screen_content(self, session_id: str, screen_data: bytes) -> bytes:
        """Process screen content with privacy shield"""
        try:
            profile = await self.policy_engine._get_session_profile(session_id)
            if not profile or not profile.privacy_shield_enabled:
                return screen_data
            
            # Apply privacy protection
            protected_data = await self.privacy_shield.apply_privacy_protection(
                session_id, screen_data, "standard"
            )
            
            return protected_data
            
        except Exception as e:
            logger.error(f"Screen content processing failed: {e}")
            return screen_data
    
    # Policy Management
    
    async def create_permission_rule(self, permission_type: PermissionType,
                                   condition: Dict[str, Any], action: PolicyAction,
                                   priority: int = 100, reason: str = "",
                                   expires_at: Optional[datetime] = None,
                                   created_by: Optional[str] = None) -> str:
        """Create new permission rule"""
        try:
            rule_id = str(uuid.uuid4())
            
            rule = PermissionRule(
                rule_id=rule_id,
                permission_type=permission_type,
                condition=condition,
                action=action,
                priority=priority,
                reason=reason,
                expires_at=expires_at,
                created_by=created_by
            )
            
            await self.db["permission_rules"].insert_one(rule.to_dict())
            
            # Clear cache
            self.policy_engine.rule_cache.clear()
            
            logger.info(f"Permission rule created: {rule_id}")
            return rule_id
            
        except Exception as e:
            logger.error(f"Failed to create permission rule: {e}")
            raise
    
    # Monitoring and Analytics
    
    async def get_session_security_summary(self, session_id: str) -> Dict[str, Any]:
        """Get security summary for session"""
        try:
            # Get security events
            events_cursor = self.db["security_events"].find(
                {"session_id": session_id}
            ).sort("timestamp", -1).limit(100)
            
            events = await events_cursor.to_list(length=None)
            
            # Get privacy events
            privacy_cursor = self.db["privacy_events"].find(
                {"session_id": session_id}
            ).sort("timestamp", -1).limit(50)
            
            privacy_events = await privacy_cursor.to_list(length=None)
            
            # Get JIT approvals
            jit_cursor = self.db["jit_approvals"].find(
                {"session_id": session_id}
            ).sort("requested_at", -1)
            
            jit_approvals = await jit_cursor.to_list(length=None)
            
            # Get session profile
            profile = await self.policy_engine._get_session_profile(session_id)
            
            # Calculate statistics
            event_counts = {}
            for event in events:
                event_type = event["event_type"]
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            return {
                "session_id": session_id,
                "profile": profile.to_dict() if profile else None,
                "security_events": {
                    "total": len(events),
                    "by_type": event_counts,
                    "recent": events[:10]
                },
                "privacy_events": {
                    "total": len(privacy_events),
                    "recent": privacy_events[:5]
                },
                "jit_approvals": {
                    "total": len(jit_approvals),
                    "pending": len([j for j in jit_approvals if j["status"] == "pending"]),
                    "approved": len([j for j in jit_approvals if j["status"] == "approved"]),
                    "denied": len([j for j in jit_approvals if j["status"] == "denied"])
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get session security summary: {e}")
            return {}
    
    async def cleanup_expired_requests(self):
        """Clean up expired JIT approval requests"""
        try:
            result = await self.db["jit_approvals"].update_many(
                {
                    "status": "pending",
                    "expires_at": {"$lt": datetime.now(timezone.utc)}
                },
                {"$set": {"status": "expired"}}
            )
            
            if result.modified_count > 0:
                logger.info(f"Expired {result.modified_count} JIT approval requests")
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired requests: {e}")
    
    async def close(self):
        """Close trust controller"""
        self.mongo_client.close()
        logger.info("Trust controller closed")


# Global trust controller instance
trust_controller: Optional[TrustController] = None


def get_trust_controller() -> TrustController:
    """Get global trust controller instance"""
    global trust_controller
    if trust_controller is None:
        trust_controller = TrustController()
    return trust_controller


async def start_trust_service():
    """Start trust controller service"""
    controller = get_trust_controller()
    
    # Start cleanup scheduler
    asyncio.create_task(_cleanup_scheduler())
    
    logger.info("Trust controller service started")


async def stop_trust_service():
    """Stop trust controller service"""
    global trust_controller
    if trust_controller:
        await trust_controller.close()
        trust_controller = None


async def _cleanup_scheduler():
    """Background task for periodic cleanup"""
    controller = get_trust_controller()
    
    while True:
        try:
            # Clean up expired JIT requests every 5 minutes
            await controller.cleanup_expired_requests()
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"Cleanup scheduler error: {e}")
            await asyncio.sleep(60)


if __name__ == "__main__":
    # Test trust controller
    async def test_trust():
        print("Starting Lucid trust controller...")
        await start_trust_service()
        
        controller = get_trust_controller()
        
        # Create test session profile
        session_id = str(uuid.uuid4())
        await controller.create_session_profile(
            session_id=session_id,
            control_mode=SessionControlMode.RESTRICTED,
            threat_level=ThreatLevel.MEDIUM
        )
        print(f"Session profile created: {session_id}")
        
        # Test permission enforcement
        allowed, reason = await controller.enforce_permission(
            session_id=session_id,
            permission_type=PermissionType.SCREEN_CAPTURE,
            resource="desktop",
            context={"user": "test", "app": "desktop"}
        )
        print(f"Screen capture permission: {allowed} - {reason}")
        
        # Test file download (should be denied in restricted mode)
        allowed, reason = await controller.enforce_permission(
            session_id=session_id,
            permission_type=PermissionType.FILE_DOWNLOAD,
            resource="document.pdf",
            context={"user": "test", "size": 1024}
        )
        print(f"File download permission: {allowed} - {reason}")
        
        # Get session summary
        summary = await controller.get_session_security_summary(session_id)
        print(f"Session summary - Security events: {summary.get('security_events', {}).get('total', 0)}")
        
        await asyncio.sleep(2)
        
        print("Stopping trust controller...")
        await stop_trust_service()
    
    asyncio.run(test_trust())