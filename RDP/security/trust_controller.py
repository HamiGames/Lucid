# Path: RDP/security/trust_controller.py
# Lucid RDP Security - Trust Controller
# Manages trust relationships and security policies for RDP connections
# LUCID-STRICT Layer 1 Core Infrastructure

from __future__ import annotations

import asyncio
import logging
import os
import time
import hashlib
import secrets
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import aiofiles
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import jwt
from jwt.exceptions import InvalidTokenError

logger = logging.getLogger(__name__)

# Configuration from environment
TRUST_STORAGE_PATH = Path(os.getenv("TRUST_STORAGE_PATH", "/data/rdp/trust"))
TRUST_CERTIFICATE_PATH = Path(os.getenv("TRUST_CERTIFICATE_PATH", "/secrets/rdp/certificates"))
TRUST_POLICY_PATH = Path(os.getenv("TRUST_POLICY_PATH", "/data/rdp/policies"))
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "60"))
MAX_FAILED_ATTEMPTS = int(os.getenv("MAX_FAILED_ATTEMPTS", "5"))
TRUST_SCORE_THRESHOLD = float(os.getenv("TRUST_SCORE_THRESHOLD", "0.7"))
CERTIFICATE_VALIDITY_DAYS = int(os.getenv("CERTIFICATE_VALIDITY_DAYS", "365"))


class TrustLevel(Enum):
    """Trust levels for entities"""
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    FULLY_TRUSTED = "fully_trusted"


class EntityType(Enum):
    """Types of entities in the trust system"""
    USER = "user"
    DEVICE = "device"
    NETWORK = "network"
    SERVICE = "service"
    CERTIFICATE = "certificate"
    SESSION = "session"


class TrustEvent(Enum):
    """Trust-related events"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    POLICY_VIOLATION = "policy_violation"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    CERTIFICATE_EXPIRED = "certificate_expired"
    TRUST_SCORE_CHANGE = "trust_score_change"


class SecurityPolicy(Enum):
    """Security policy types"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ENCRYPTION = "encryption"
    SESSION_MANAGEMENT = "session_management"
    NETWORK_ACCESS = "network_access"
    DATA_PROTECTION = "data_protection"


@dataclass
class TrustEntity:
    """Represents a trusted entity"""
    entity_id: str
    entity_type: EntityType
    public_key: str
    trust_level: TrustLevel
    trust_score: float
    created_at: datetime
    last_updated: datetime
    last_seen: datetime
    certificate_data: Optional[str] = None
    certificate_expiry: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    policy_violations: int = 0
    failed_attempts: int = 0
    is_active: bool = True


@dataclass
class TrustEvent:
    """Trust-related event record"""
    event_id: str
    event_type: TrustEvent
    entity_id: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    trust_score_impact: float = 0.0
    severity: str = "info"
    source_ip: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class SecurityPolicy:
    """Security policy definition"""
    policy_id: str
    policy_type: SecurityPolicy
    name: str
    description: str
    rules: List[Dict[str, Any]] = field(default_factory=list)
    is_enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    enforcement_level: str = "strict"  # strict, moderate, permissive


@dataclass
class TrustDecision:
    """Result of trust evaluation"""
    entity_id: str
    decision: bool
    trust_level: TrustLevel
    trust_score: float
    confidence: float
    reasoning: List[str] = field(default_factory=list)
    applied_policies: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TrustController:
    """Centralized trust management and security controller"""
    
    def __init__(self):
        self.storage_path = TRUST_STORAGE_PATH
        self.certificate_path = TRUST_CERTIFICATE_PATH
        self.policy_path = TRUST_POLICY_PATH
        self.trust_entities: Dict[str, TrustEntity] = {}
        self.security_policies: Dict[str, SecurityPolicy] = {}
        self.trust_events: List[TrustEvent] = []
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.failed_attempts: Dict[str, List[datetime]] = {}
        
        # Trust scoring parameters
        self.trust_weights = {
            "authentication_success": 0.1,
            "authentication_failure": -0.2,
            "session_duration": 0.05,
            "policy_violation": -0.3,
            "suspicious_activity": -0.4,
            "certificate_validity": 0.2,
            "network_behavior": 0.1
        }
        
        self._initialize_storage()
        self._load_default_policies()
    
    def _initialize_storage(self):
        """Initialize trust storage directories"""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.certificate_path.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.policy_path.mkdir(parents=True, exist_ok=True, mode=0o700)
            logger.info("Trust storage initialized")
        except Exception as e:
            logger.error(f"Failed to initialize trust storage: {e}")
            raise
    
    def _load_default_policies(self):
        """Load default security policies"""
        default_policies = {
            "authentication_policy": SecurityPolicy(
                policy_id="auth_001",
                policy_type=SecurityPolicy.AUTHENTICATION,
                name="Authentication Policy",
                description="Default authentication security policy",
                rules=[
                    {"action": "require_strong_password", "enforcement": "strict"},
                    {"action": "limit_failed_attempts", "threshold": MAX_FAILED_ATTEMPTS},
                    {"action": "session_timeout", "minutes": SESSION_TIMEOUT_MINUTES},
                    {"action": "require_mfa", "enforcement": "moderate"}
                ]
            ),
            "encryption_policy": SecurityPolicy(
                policy_id="enc_001",
                policy_type=SecurityPolicy.ENCRYPTION,
                name="Encryption Policy",
                description="Default encryption security policy",
                rules=[
                    {"action": "require_tls", "version": "1.3"},
                    {"action": "encrypt_session_data", "algorithm": "AES-256"},
                    {"action": "certificate_validation", "enforcement": "strict"}
                ]
            ),
            "session_policy": SecurityPolicy(
                policy_id="sess_001",
                policy_type=SecurityPolicy.SESSION_MANAGEMENT,
                name="Session Management Policy",
                description="Default session security policy",
                rules=[
                    {"action": "session_timeout", "minutes": SESSION_TIMEOUT_MINUTES},
                    {"action": "concurrent_session_limit", "limit": 3},
                    {"action": "idle_timeout", "minutes": 15},
                    {"action": "session_encryption", "required": True}
                ]
            )
        }
        
        self.security_policies = default_policies
        logger.info(f"Loaded {len(default_policies)} default security policies")
    
    async def register_entity(self, entity_id: str, entity_type: EntityType, 
                            public_key: str, certificate_data: Optional[str] = None,
                            initial_trust_level: TrustLevel = TrustLevel.MEDIUM) -> bool:
        """Register a new entity in the trust system"""
        try:
            if entity_id in self.trust_entities:
                logger.warning(f"Entity {entity_id} already registered")
                return False
            
            # Validate certificate if provided
            certificate_expiry = None
            if certificate_data:
                certificate_expiry = self._parse_certificate_expiry(certificate_data)
            
            entity = TrustEntity(
                entity_id=entity_id,
                entity_type=entity_type,
                public_key=public_key,
                trust_level=initial_trust_level,
                trust_score=self._trust_level_to_score(initial_trust_level),
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                last_seen=datetime.now(timezone.utc),
                certificate_data=certificate_data,
                certificate_expiry=certificate_expiry
            )
            
            self.trust_entities[entity_id] = entity
            
            # Log registration event
            await self._log_trust_event(
                TrustEvent.TRUST_SCORE_CHANGE,
                entity_id,
                {"action": "entity_registered", "trust_level": initial_trust_level.value}
            )
            
            # Save entity
            await self._save_entity(entity)
            
            logger.info(f"Registered entity {entity_id} with trust level {initial_trust_level.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register entity {entity_id}: {e}")
            return False
    
    async def evaluate_trust(self, entity_id: str, context: Dict[str, Any]) -> TrustDecision:
        """Evaluate trust for an entity in a specific context"""
        try:
            entity = self.trust_entities.get(entity_id)
            if not entity:
                return TrustDecision(
                    entity_id=entity_id,
                    decision=False,
                    trust_level=TrustLevel.UNTRUSTED,
                    trust_score=0.0,
                    confidence=1.0,
                    reasoning=["Entity not registered in trust system"]
                )
            
            # Update last seen
            entity.last_seen = datetime.now(timezone.utc)
            
            # Calculate trust score
            trust_score = await self._calculate_trust_score(entity, context)
            trust_level = self._score_to_trust_level(trust_score)
            
            # Apply security policies
            decision, reasoning, warnings = await self._apply_security_policies(entity, context)
            
            # Update entity trust score
            entity.trust_score = trust_score
            entity.trust_level = trust_level
            entity.last_updated = datetime.now(timezone.utc)
            
            # Save updated entity
            await self._save_entity(entity)
            
            # Log trust evaluation
            await self._log_trust_event(
                TrustEvent.TRUST_SCORE_CHANGE,
                entity_id,
                {
                    "old_score": entity.trust_score,
                    "new_score": trust_score,
                    "decision": decision,
                    "context": context
                }
            )
            
            return TrustDecision(
                entity_id=entity_id,
                decision=decision,
                trust_level=trust_level,
                trust_score=trust_score,
                confidence=self._calculate_confidence(entity, context),
                reasoning=reasoning,
                warnings=warnings,
                timestamp=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            logger.error(f"Failed to evaluate trust for {entity_id}: {e}")
            return TrustDecision(
                entity_id=entity_id,
                decision=False,
                trust_level=TrustLevel.UNTRUSTED,
                trust_score=0.0,
                confidence=0.0,
                reasoning=[f"Trust evaluation failed: {e}"]
            )
    
    async def _calculate_trust_score(self, entity: TrustEntity, context: Dict[str, Any]) -> float:
        """Calculate trust score for an entity"""
        try:
            base_score = entity.trust_score
            
            # Factor in recent events
            recent_events = self._get_recent_events(entity.entity_id, hours=24)
            
            score_adjustment = 0.0
            for event in recent_events:
                impact = self.trust_weights.get(event.event_type.value, 0.0)
                score_adjustment += impact * event.trust_score_impact
            
            # Factor in certificate validity
            if entity.certificate_expiry:
                if entity.certificate_expiry > datetime.now(timezone.utc):
                    days_until_expiry = (entity.certificate_expiry - datetime.now(timezone.utc)).days
                    if days_until_expiry > 30:
                        score_adjustment += self.trust_weights["certificate_validity"]
                    elif days_until_expiry < 7:
                        score_adjustment -= 0.1  # Certificate expiring soon
                else:
                    score_adjustment -= 0.5  # Expired certificate
            
            # Factor in failed attempts
            if entity.failed_attempts > 0:
                score_adjustment -= entity.failed_attempts * 0.1
            
            # Factor in policy violations
            if entity.policy_violations > 0:
                score_adjustment -= entity.policy_violations * 0.2
            
            # Factor in session duration (if applicable)
            if "session_duration" in context:
                duration_hours = context["session_duration"] / 3600
                if duration_hours > 1:  # Long sessions indicate trust
                    score_adjustment += self.trust_weights["session_duration"]
            
            # Factor in network behavior
            if "network_behavior_score" in context:
                network_score = context["network_behavior_score"]
                score_adjustment += network_score * self.trust_weights["network_behavior"]
            
            # Apply bounds
            new_score = max(0.0, min(1.0, base_score + score_adjustment))
            
            return new_score
            
        except Exception as e:
            logger.error(f"Failed to calculate trust score: {e}")
            return entity.trust_score
    
    async def _apply_security_policies(self, entity: TrustEntity, context: Dict[str, Any]) -> Tuple[bool, List[str], List[str]]:
        """Apply security policies to determine access decision"""
        try:
            reasoning = []
            warnings = []
            decision = True
            
            # Check authentication policy
            auth_policy = self.security_policies.get("authentication_policy")
            if auth_policy and auth_policy.is_enabled:
                auth_decision, auth_reasoning, auth_warnings = self._check_authentication_policy(entity, context, auth_policy)
                decision &= auth_decision
                reasoning.extend(auth_reasoning)
                warnings.extend(auth_warnings)
            
            # Check encryption policy
            enc_policy = self.security_policies.get("encryption_policy")
            if enc_policy and enc_policy.is_enabled:
                enc_decision, enc_reasoning, enc_warnings = self._check_encryption_policy(entity, context, enc_policy)
                decision &= enc_decision
                reasoning.extend(enc_reasoning)
                warnings.extend(enc_warnings)
            
            # Check session policy
            sess_policy = self.security_policies.get("session_policy")
            if sess_policy and sess_policy.is_enabled:
                sess_decision, sess_reasoning, sess_warnings = self._check_session_policy(entity, context, sess_policy)
                decision &= sess_decision
                reasoning.extend(sess_reasoning)
                warnings.extend(sess_warnings)
            
            # Check trust threshold
            if entity.trust_score < TRUST_SCORE_THRESHOLD:
                decision = False
                reasoning.append(f"Trust score {entity.trust_score:.2f} below threshold {TRUST_SCORE_THRESHOLD}")
            
            return decision, reasoning, warnings
            
        except Exception as e:
            logger.error(f"Failed to apply security policies: {e}")
            return False, [f"Policy evaluation failed: {e}"], []
    
    def _check_authentication_policy(self, entity: TrustEntity, context: Dict[str, Any], policy: SecurityPolicy) -> Tuple[bool, List[str], List[str]]:
        """Check authentication policy compliance"""
        reasoning = []
        warnings = []
        decision = True
        
        # Check failed attempts
        failed_rule = next((r for r in policy.rules if r["action"] == "limit_failed_attempts"), None)
        if failed_rule and entity.failed_attempts >= failed_rule["threshold"]:
            decision = False
            reasoning.append(f"Failed attempts {entity.failed_attempts} exceeds threshold {failed_rule['threshold']}")
        
        # Check session timeout
        timeout_rule = next((r for r in policy.rules if r["action"] == "session_timeout"), None)
        if timeout_rule and "session_duration" in context:
            max_duration = timeout_rule["minutes"] * 60
            if context["session_duration"] > max_duration:
                warnings.append(f"Session duration exceeds policy limit of {timeout_rule['minutes']} minutes")
        
        return decision, reasoning, warnings
    
    def _check_encryption_policy(self, entity: TrustEntity, context: Dict[str, Any], policy: SecurityPolicy) -> Tuple[bool, List[str], List[str]]:
        """Check encryption policy compliance"""
        reasoning = []
        warnings = []
        decision = True
        
        # Check certificate validity
        cert_rule = next((r for r in policy.rules if r["action"] == "certificate_validation"), None)
        if cert_rule and entity.certificate_expiry:
            if entity.certificate_expiry <= datetime.now(timezone.utc):
                decision = False
                reasoning.append("Certificate has expired")
            elif (entity.certificate_expiry - datetime.now(timezone.utc)).days < 7:
                warnings.append("Certificate expires within 7 days")
        
        # Check TLS requirement
        tls_rule = next((r for r in policy.rules if r["action"] == "require_tls"), None)
        if tls_rule and context.get("protocol") != "tls":
            decision = False
            reasoning.append("TLS connection required")
        
        return decision, reasoning, warnings
    
    def _check_session_policy(self, entity: TrustEntity, context: Dict[str, Any], policy: SecurityPolicy) -> Tuple[bool, List[str], List[str]]:
        """Check session policy compliance"""
        reasoning = []
        warnings = []
        decision = True
        
        # Check concurrent session limit
        concurrent_rule = next((r for r in policy.rules if r["action"] == "concurrent_session_limit"), None)
        if concurrent_rule:
            active_sessions = len([s for s in self.active_sessions.values() if s.get("entity_id") == entity.entity_id])
            if active_sessions >= concurrent_rule["limit"]:
                decision = False
                reasoning.append(f"Concurrent session limit {concurrent_rule['limit']} exceeded")
        
        # Check idle timeout
        idle_rule = next((r for r in policy.rules if r["action"] == "idle_timeout"), None)
        if idle_rule and "last_activity" in context:
            idle_time = (datetime.now(timezone.utc) - context["last_activity"]).total_seconds()
            if idle_time > idle_rule["minutes"] * 60:
                warnings.append(f"Session idle time exceeds {idle_rule['minutes']} minutes")
        
        return decision, reasoning, warnings
    
    async def record_trust_event(self, event_type: TrustEvent, entity_id: str, 
                               details: Dict[str, Any], trust_score_impact: float = 0.0,
                               severity: str = "info", source_ip: Optional[str] = None,
                               session_id: Optional[str] = None):
        """Record a trust-related event"""
        try:
            event = TrustEvent(
                event_id=self._generate_event_id(),
                event_type=event_type,
                entity_id=entity_id,
                timestamp=datetime.now(timezone.utc),
                details=details,
                trust_score_impact=trust_score_impact,
                severity=severity,
                source_ip=source_ip,
                session_id=session_id
            )
            
            self.trust_events.append(event)
            
            # Update entity based on event
            if entity_id in self.trust_entities:
                entity = self.trust_entities[entity_id]
                
                if event_type == TrustEvent.LOGIN_FAILURE:
                    entity.failed_attempts += 1
                elif event_type == TrustEvent.LOGIN_SUCCESS:
                    entity.failed_attempts = 0  # Reset on successful login
                elif event_type == TrustEvent.POLICY_VIOLATION:
                    entity.policy_violations += 1
                
                entity.last_seen = datetime.now(timezone.utc)
                await self._save_entity(entity)
            
            # Save event
            await self._save_trust_event(event)
            
            logger.info(f"Recorded trust event {event_type.value} for entity {entity_id}")
            
        except Exception as e:
            logger.error(f"Failed to record trust event: {e}")
    
    async def create_session(self, entity_id: str, session_id: str, context: Dict[str, Any]) -> bool:
        """Create a new trusted session"""
        try:
            if entity_id not in self.trust_entities:
                logger.warning(f"Entity {entity_id} not found for session creation")
                return False
            
            # Evaluate trust for session creation
            trust_decision = await self.evaluate_trust(entity_id, context)
            
            if not trust_decision.decision:
                await self.record_trust_event(
                    TrustEvent.POLICY_VIOLATION,
                    entity_id,
                    {"action": "session_creation_denied", "reasoning": trust_decision.reasoning},
                    trust_score_impact=-0.1,
                    severity="warning"
                )
                return False
            
            # Create session
            session_data = {
                "session_id": session_id,
                "entity_id": entity_id,
                "created_at": datetime.now(timezone.utc),
                "last_activity": datetime.now(timezone.utc),
                "trust_score": trust_decision.trust_score,
                "context": context
            }
            
            self.active_sessions[session_id] = session_data
            
            # Log session creation
            await self.record_trust_event(
                TrustEvent.SESSION_START,
                entity_id,
                {"session_id": session_id, "trust_score": trust_decision.trust_score},
                session_id=session_id
            )
            
            logger.info(f"Created trusted session {session_id} for entity {entity_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            return False
    
    async def end_session(self, session_id: str) -> bool:
        """End a trusted session"""
        try:
            if session_id not in self.active_sessions:
                logger.warning(f"Session {session_id} not found")
                return False
            
            session_data = self.active_sessions[session_id]
            entity_id = session_data["entity_id"]
            
            # Calculate session duration
            session_duration = (datetime.now(timezone.utc) - session_data["created_at"]).total_seconds()
            
            # Log session end
            await self.record_trust_event(
                TrustEvent.SESSION_END,
                entity_id,
                {
                    "session_id": session_id,
                    "duration_seconds": session_duration,
                    "trust_score": session_data["trust_score"]
                },
                session_id=session_id
            )
            
            # Remove session
            del self.active_sessions[session_id]
            
            logger.info(f"Ended session {session_id} for entity {entity_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to end session {session_id}: {e}")
            return False
    
    def _trust_level_to_score(self, trust_level: TrustLevel) -> float:
        """Convert trust level to numerical score"""
        mapping = {
            TrustLevel.UNTRUSTED: 0.0,
            TrustLevel.LOW: 0.25,
            TrustLevel.MEDIUM: 0.5,
            TrustLevel.HIGH: 0.75,
            TrustLevel.FULLY_TRUSTED: 1.0
        }
        return mapping.get(trust_level, 0.0)
    
    def _score_to_trust_level(self, score: float) -> TrustLevel:
        """Convert numerical score to trust level"""
        if score >= 0.9:
            return TrustLevel.FULLY_TRUSTED
        elif score >= 0.7:
            return TrustLevel.HIGH
        elif score >= 0.5:
            return TrustLevel.MEDIUM
        elif score >= 0.25:
            return TrustLevel.LOW
        else:
            return TrustLevel.UNTRUSTED
    
    def _calculate_confidence(self, entity: TrustEntity, context: Dict[str, Any]) -> float:
        """Calculate confidence in trust decision"""
        try:
            # Base confidence on entity history and context completeness
            history_factor = min(1.0, len(self._get_recent_events(entity.entity_id, days=30)) / 10)
            context_factor = len(context) / 10  # More context = higher confidence
            certificate_factor = 1.0 if entity.certificate_data else 0.5
            
            confidence = (history_factor + context_factor + certificate_factor) / 3
            return min(1.0, max(0.0, confidence))
            
        except Exception as e:
            logger.error(f"Failed to calculate confidence: {e}")
            return 0.5
    
    def _get_recent_events(self, entity_id: str, hours: int = 24, days: int = 0) -> List[TrustEvent]:
        """Get recent events for an entity"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours, days=days)
        return [e for e in self.trust_events if e.entity_id == entity_id and e.timestamp >= cutoff_time]
    
    def _parse_certificate_expiry(self, certificate_data: str) -> Optional[datetime]:
        """Parse certificate expiry date"""
        try:
            # In production, this would parse actual certificate data
            # For now, return a future date
            return datetime.now(timezone.utc) + timedelta(days=CERTIFICATE_VALIDITY_DAYS)
        except Exception:
            return None
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        random_suffix = secrets.token_hex(4)
        return f"event_{timestamp}_{random_suffix}"
    
    async def _save_entity(self, entity: TrustEntity):
        """Save entity to storage"""
        try:
            entity_file = self.storage_path / f"entity_{entity.entity_id}.json"
            entity_dict = {
                "entity_id": entity.entity_id,
                "entity_type": entity.entity_type.value,
                "public_key": entity.public_key,
                "trust_level": entity.trust_level.value,
                "trust_score": entity.trust_score,
                "created_at": entity.created_at.isoformat(),
                "last_updated": entity.last_updated.isoformat(),
                "last_seen": entity.last_seen.isoformat(),
                "certificate_data": entity.certificate_data,
                "certificate_expiry": entity.certificate_expiry.isoformat() if entity.certificate_expiry else None,
                "metadata": entity.metadata,
                "policy_violations": entity.policy_violations,
                "failed_attempts": entity.failed_attempts,
                "is_active": entity.is_active
            }
            
            async with aiofiles.open(entity_file, 'w') as f:
                await f.write(json.dumps(entity_dict, indent=2))
                
        except Exception as e:
            logger.error(f"Failed to save entity {entity.entity_id}: {e}")
    
    async def _save_trust_event(self, event: TrustEvent):
        """Save trust event to storage"""
        try:
            event_file = self.storage_path / f"event_{event.event_id}.json"
            event_dict = {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "entity_id": event.entity_id,
                "timestamp": event.timestamp.isoformat(),
                "details": event.details,
                "trust_score_impact": event.trust_score_impact,
                "severity": event.severity,
                "source_ip": event.source_ip,
                "session_id": event.session_id
            }
            
            async with aiofiles.open(event_file, 'w') as f:
                await f.write(json.dumps(event_dict, indent=2))
                
        except Exception as e:
            logger.error(f"Failed to save trust event {event.event_id}: {e}")
    
    async def get_trust_statistics(self) -> Dict[str, Any]:
        """Get trust system statistics"""
        try:
            total_entities = len(self.trust_entities)
            active_entities = len([e for e in self.trust_entities.values() if e.is_active])
            active_sessions = len(self.active_sessions)
            
            trust_level_counts = {}
            for level in TrustLevel:
                trust_level_counts[level.value] = len([e for e in self.trust_entities.values() if e.trust_level == level])
            
            recent_events = len([e for e in self.trust_events if e.timestamp >= datetime.now(timezone.utc) - timedelta(hours=24)])
            
            return {
                "total_entities": total_entities,
                "active_entities": active_entities,
                "active_sessions": active_sessions,
                "trust_level_distribution": trust_level_counts,
                "recent_events_24h": recent_events,
                "total_events": len(self.trust_events),
                "security_policies": len(self.security_policies)
            }
            
        except Exception as e:
            logger.error(f"Failed to get trust statistics: {e}")
            return {}


# Global trust controller instance
trust_controller = TrustController()


async def register_trusted_entity(entity_id: str, entity_type: EntityType, 
                                public_key: str, **kwargs) -> bool:
    """Register a new trusted entity"""
    return await trust_controller.register_entity(entity_id, entity_type, public_key, **kwargs)


async def evaluate_entity_trust(entity_id: str, context: Dict[str, Any]) -> TrustDecision:
    """Evaluate trust for an entity"""
    return await trust_controller.evaluate_trust(entity_id, context)


async def create_trusted_session(entity_id: str, session_id: str, context: Dict[str, Any]) -> bool:
    """Create a new trusted session"""
    return await trust_controller.create_session(entity_id, session_id, context)


async def record_trust_event(event_type: TrustEvent, entity_id: str, details: Dict[str, Any], **kwargs):
    """Record a trust-related event"""
    await trust_controller.record_trust_event(event_type, entity_id, details, **kwargs)


async def get_trust_statistics() -> Dict[str, Any]:
    """Get trust system statistics"""
    return await trust_controller.get_trust_statistics()


if __name__ == "__main__":
    # Test the trust controller
    async def test_trust_controller():
        # Register a test entity
        success = await register_trusted_entity(
            "test_user_001",
            EntityType.USER,
            "test_public_key",
            initial_trust_level=TrustLevel.MEDIUM
        )
        print(f"Entity registration: {success}")
        
        # Evaluate trust
        context = {"protocol": "tls", "session_duration": 3600}
        decision = await evaluate_entity_trust("test_user_001", context)
        print(f"Trust decision: {decision.decision}, Score: {decision.trust_score:.2f}")
        
        # Create session
        session_created = await create_trusted_session("test_user_001", "session_001", context)
        print(f"Session created: {session_created}")
        
        # Get statistics
        stats = await get_trust_statistics()
        print(f"Trust statistics: {stats}")
    
    asyncio.run(test_trust_controller())
