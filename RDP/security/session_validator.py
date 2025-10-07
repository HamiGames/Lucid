# LUCID RDP Session Validator - Session Security and Validation
# Implements comprehensive session validation for RDP security
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
SESSION_VALIDATION_DB = os.getenv("SESSION_VALIDATION_DB", "lucid_sessions")
JWT_SECRET = os.getenv("JWT_SECRET", "lucid_jwt_secret_key_change_in_production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "60"))
MAX_SESSION_DURATION_HOURS = int(os.getenv("MAX_SESSION_DURATION_HOURS", "8"))
VALIDATION_CACHE_TTL = int(os.getenv("VALIDATION_CACHE_TTL", "300"))  # 5 minutes


class ValidationStatus(Enum):
    """Session validation status"""
    VALID = "valid"
    INVALID = "invalid"
    EXPIRED = "expired"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"
    PENDING = "pending"
    FAILED = "failed"


class ValidationLevel(Enum):
    """Validation security levels"""
    BASIC = "basic"           # Basic session validation
    STANDARD = "standard"     # Standard security validation
    STRICT = "strict"         # Strict security validation
    PARANOID = "paranoid"     # Maximum security validation


class SessionRiskLevel(Enum):
    """Session risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationType(Enum):
    """Types of session validation"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    INTEGRITY = "integrity"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    BEHAVIORAL = "behavioral"
    NETWORK = "network"
    DEVICE = "device"


@dataclass
class SessionValidationRule:
    """Session validation rule definition"""
    rule_id: str
    name: str
    description: str
    validation_type: ValidationType
    validation_level: ValidationLevel
    condition: str  # JSONPath or regex expression
    action: str  # allow, deny, quarantine, alert
    priority: int = 0
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionValidationResult:
    """Result of session validation"""
    validation_id: str
    session_id: str
    validation_type: ValidationType
    status: ValidationStatus
    risk_level: SessionRiskLevel
    timestamp: datetime
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionSecurityContext:
    """Security context for session validation"""
    session_id: str
    user_id: str
    node_id: str
    ip_address: str
    user_agent: str
    device_fingerprint: Optional[str] = None
    location: Optional[str] = None
    trust_score: float = 0.0
    risk_indicators: List[str] = field(default_factory=list)
    session_start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    validation_history: List[SessionValidationResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionIntegrityCheck:
    """Session integrity validation data"""
    session_id: str
    checksum: str
    timestamp: datetime
    data_hash: str
    signature: Optional[str] = None
    public_key: Optional[str] = None
    is_valid: bool = True
    error_message: Optional[str] = None


class SessionValidator:
    """
    Comprehensive session validator for RDP security.
    
    Implements trust-nothing validation with multiple validation layers:
    - Authentication validation
    - Authorization validation  
    - Session integrity validation
    - Timeout validation
    - Resource usage validation
    - Behavioral analysis
    - Network security validation
    - Device fingerprinting
    """
    
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        """Initialize session validator"""
        self.db = db
        self.validation_rules: Dict[str, SessionValidationRule] = {}
        self.active_sessions: Dict[str, SessionSecurityContext] = {}
        self.validation_cache: Dict[str, Tuple[SessionValidationResult, float]] = {}
        self.integrity_checks: Dict[str, SessionIntegrityCheck] = {}
        
        # Validation statistics
        self.stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "blocked_sessions": 0,
            "suspicious_sessions": 0
        }
        
        # Load default validation rules
        self._load_default_rules()
        
        logger.info("SessionValidator initialized with trust-nothing security model")
    
    def _load_default_rules(self) -> None:
        """Load default session validation rules"""
        default_rules = [
            # Authentication validation rules
            SessionValidationRule(
                rule_id="auth_001",
                name="Session Authentication Required",
                description="All sessions must have valid authentication",
                validation_type=ValidationType.AUTHENTICATION,
                validation_level=ValidationLevel.STRICT,
                condition="$.authentication.valid == true",
                action="deny",
                priority=100
            ),
            
            # Authorization validation rules
            SessionValidationRule(
                rule_id="authz_001", 
                name="User Authorization Check",
                description="User must have proper authorization for session",
                validation_type=ValidationType.AUTHORIZATION,
                validation_level=ValidationLevel.STRICT,
                condition="$.authorization.level in ['standard', 'elevated', 'admin']",
                action="deny",
                priority=90
            ),
            
            # Timeout validation rules
            SessionValidationRule(
                rule_id="timeout_001",
                name="Session Timeout Check",
                description="Sessions must not exceed maximum duration",
                validation_type=ValidationType.TIMEOUT,
                validation_level=ValidationLevel.STANDARD,
                condition="$.duration_hours <= 8",
                action="deny",
                priority=80
            ),
            
            # Resource validation rules
            SessionValidationRule(
                rule_id="resource_001",
                name="Resource Usage Limits",
                description="Session resource usage must be within limits",
                validation_type=ValidationType.RESOURCE,
                validation_level=ValidationLevel.STANDARD,
                condition="$.resource_usage.cpu_percent <= 80 and $.resource_usage.memory_mb <= 2048",
                action="alert",
                priority=70
            ),
            
            # Behavioral validation rules
            SessionValidationRule(
                rule_id="behavior_001",
                name="Suspicious Activity Detection",
                description="Detect suspicious session behavior patterns",
                validation_type=ValidationType.BEHAVIORAL,
                validation_level=ValidationLevel.STRICT,
                condition="$.behavior.anomaly_score > 0.7",
                action="quarantine",
                priority=60
            ),
            
            # Network validation rules
            SessionValidationRule(
                rule_id="network_001",
                name="Network Security Check",
                description="Validate network connection security",
                validation_type=ValidationType.NETWORK,
                validation_level=ValidationLevel.STRICT,
                condition="$.network.encrypted == true and $.network.vpn_required == true",
                action="deny",
                priority=85
            ),
            
            # Device validation rules
            SessionValidationRule(
                rule_id="device_001",
                name="Device Fingerprint Validation",
                description="Validate device fingerprint consistency",
                validation_type=ValidationType.DEVICE,
                validation_level=ValidationLevel.STANDARD,
                condition="$.device.fingerprint_verified == true",
                action="alert",
                priority=50
            )
        ]
        
        for rule in default_rules:
            self.validation_rules[rule.rule_id] = rule
        
        logger.info(f"Loaded {len(default_rules)} default validation rules")
    
    async def validate_session(
        self,
        session_id: str,
        validation_type: ValidationType,
        context: Dict[str, Any],
        force_refresh: bool = False
    ) -> SessionValidationResult:
        """Validate session with specified validation type"""
        try:
            # Check cache first (unless force refresh)
            cache_key = f"{session_id}:{validation_type.value}"
            if not force_refresh and cache_key in self.validation_cache:
                cached_result, cache_time = self.validation_cache[cache_key]
                if time.time() - cache_time < VALIDATION_CACHE_TTL:
                    logger.debug(f"Using cached validation result for {session_id}")
                    return cached_result
            
            # Get session security context
            security_context = self.active_sessions.get(session_id)
            if not security_context:
                security_context = await self._create_security_context(session_id, context)
                self.active_sessions[session_id] = security_context
            
            # Perform validation based on type
            if validation_type == ValidationType.AUTHENTICATION:
                result = await self._validate_authentication(session_id, context, security_context)
            elif validation_type == ValidationType.AUTHORIZATION:
                result = await self._validate_authorization(session_id, context, security_context)
            elif validation_type == ValidationType.INTEGRITY:
                result = await self._validate_integrity(session_id, context, security_context)
            elif validation_type == ValidationType.TIMEOUT:
                result = await self._validate_timeout(session_id, context, security_context)
            elif validation_type == ValidationType.RESOURCE:
                result = await self._validate_resource_usage(session_id, context, security_context)
            elif validation_type == ValidationType.BEHAVIORAL:
                result = await self._validate_behavior(session_id, context, security_context)
            elif validation_type == ValidationType.NETWORK:
                result = await self._validate_network(session_id, context, security_context)
            elif validation_type == ValidationType.DEVICE:
                result = await self._validate_device(session_id, context, security_context)
            else:
                result = SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=validation_type,
                    status=ValidationStatus.FAILED,
                    risk_level=SessionRiskLevel.HIGH,
                    timestamp=datetime.now(timezone.utc),
                    message=f"Unknown validation type: {validation_type.value}"
                )
            
            # Cache result
            self.validation_cache[cache_key] = (result, time.time())
            
            # Update statistics
            self.stats["total_validations"] += 1
            if result.status == ValidationStatus.VALID:
                self.stats["successful_validations"] += 1
            else:
                self.stats["failed_validations"] += 1
                if result.status == ValidationStatus.BLOCKED:
                    self.stats["blocked_sessions"] += 1
                elif result.status == ValidationStatus.SUSPICIOUS:
                    self.stats["suspicious_sessions"] += 1
            
            # Add to validation history
            security_context.validation_history.append(result)
            security_context.last_activity = datetime.now(timezone.utc)
            
            logger.info(f"Session validation completed: {session_id} - {validation_type.value} - {result.status.value}")
            return result
            
        except Exception as e:
            logger.error(f"Session validation error for {session_id}: {e}")
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=validation_type,
                status=ValidationStatus.FAILED,
                risk_level=SessionRiskLevel.CRITICAL,
                timestamp=datetime.now(timezone.utc),
                message=f"Validation error: {str(e)}"
            )
    
    async def _validate_authentication(
        self,
        session_id: str,
        context: Dict[str, Any],
        security_context: SessionSecurityContext
    ) -> SessionValidationResult:
        """Validate session authentication"""
        try:
            # Check if authentication data exists
            auth_data = context.get("authentication", {})
            if not auth_data:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.AUTHENTICATION,
                    status=ValidationStatus.INVALID,
                    risk_level=SessionRiskLevel.CRITICAL,
                    timestamp=datetime.now(timezone.utc),
                    message="No authentication data provided"
                )
            
            # Validate JWT token if present
            token = auth_data.get("token")
            if token:
                try:
                    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
                    if payload.get("exp", 0) < time.time():
                        return SessionValidationResult(
                            validation_id=str(uuid.uuid4()),
                            session_id=session_id,
                            validation_type=ValidationType.AUTHENTICATION,
                            status=ValidationStatus.EXPIRED,
                            risk_level=SessionRiskLevel.HIGH,
                            timestamp=datetime.now(timezone.utc),
                            message="Authentication token expired"
                        )
                except jwt.InvalidTokenError as e:
                    return SessionValidationResult(
                        validation_id=str(uuid.uuid4()),
                        session_id=session_id,
                        validation_type=ValidationType.AUTHENTICATION,
                        status=ValidationStatus.INVALID,
                        risk_level=SessionRiskLevel.CRITICAL,
                        timestamp=datetime.now(timezone.utc),
                        message=f"Invalid authentication token: {str(e)}"
                    )
            
            # Validate digital signature if present
            signature = auth_data.get("signature")
            public_key = auth_data.get("public_key")
            message = auth_data.get("message")
            
            if signature and public_key and message:
                if not await self._verify_digital_signature(signature, public_key, message):
                    return SessionValidationResult(
                        validation_id=str(uuid.uuid4()),
                        session_id=session_id,
                        validation_type=ValidationType.AUTHENTICATION,
                        status=ValidationStatus.INVALID,
                        risk_level=SessionRiskLevel.CRITICAL,
                        timestamp=datetime.now(timezone.utc),
                        message="Invalid digital signature"
                    )
            
            # Check authentication validity
            is_valid = auth_data.get("valid", False)
            if not is_valid:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.AUTHENTICATION,
                    status=ValidationStatus.INVALID,
                    risk_level=SessionRiskLevel.CRITICAL,
                    timestamp=datetime.now(timezone.utc),
                    message="Authentication marked as invalid"
                )
            
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.AUTHENTICATION,
                status=ValidationStatus.VALID,
                risk_level=SessionRiskLevel.LOW,
                timestamp=datetime.now(timezone.utc),
                message="Authentication validation successful"
            )
            
        except Exception as e:
            logger.error(f"Authentication validation error: {e}")
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.AUTHENTICATION,
                status=ValidationStatus.FAILED,
                risk_level=SessionRiskLevel.CRITICAL,
                timestamp=datetime.now(timezone.utc),
                message=f"Authentication validation error: {str(e)}"
            )
    
    async def _validate_authorization(
        self,
        session_id: str,
        context: Dict[str, Any],
        security_context: SessionSecurityContext
    ) -> SessionValidationResult:
        """Validate session authorization"""
        try:
            authz_data = context.get("authorization", {})
            if not authz_data:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.AUTHORIZATION,
                    status=ValidationStatus.INVALID,
                    risk_level=SessionRiskLevel.CRITICAL,
                    timestamp=datetime.now(timezone.utc),
                    message="No authorization data provided"
                )
            
            # Check authorization level
            authz_level = authz_data.get("level", "denied")
            if authz_level == "denied":
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.AUTHORIZATION,
                    status=ValidationStatus.BLOCKED,
                    risk_level=SessionRiskLevel.CRITICAL,
                    timestamp=datetime.now(timezone.utc),
                    message="User authorization denied"
                )
            
            # Check required permissions
            required_permissions = context.get("required_permissions", [])
            user_permissions = authz_data.get("permissions", [])
            
            missing_permissions = set(required_permissions) - set(user_permissions)
            if missing_permissions:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.AUTHORIZATION,
                    status=ValidationStatus.INVALID,
                    risk_level=SessionRiskLevel.HIGH,
                    timestamp=datetime.now(timezone.utc),
                    message=f"Missing required permissions: {list(missing_permissions)}"
                )
            
            # Check session ownership
            session_owner = context.get("session_owner")
            user_id = authz_data.get("user_id")
            if session_owner and user_id and session_owner != user_id:
                # Check if user has permission to access other user's session
                if "admin_access" not in user_permissions and "session_manage" not in user_permissions:
                    return SessionValidationResult(
                        validation_id=str(uuid.uuid4()),
                        session_id=session_id,
                        validation_type=ValidationType.AUTHORIZATION,
                        status=ValidationStatus.INVALID,
                        risk_level=SessionRiskLevel.HIGH,
                        timestamp=datetime.now(timezone.utc),
                        message="User not authorized to access this session"
                    )
            
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.AUTHORIZATION,
                status=ValidationStatus.VALID,
                risk_level=SessionRiskLevel.LOW,
                timestamp=datetime.now(timezone.utc),
                message="Authorization validation successful"
            )
            
        except Exception as e:
            logger.error(f"Authorization validation error: {e}")
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.AUTHORIZATION,
                status=ValidationStatus.FAILED,
                risk_level=SessionRiskLevel.CRITICAL,
                timestamp=datetime.now(timezone.utc),
                message=f"Authorization validation error: {str(e)}"
            )
    
    async def _validate_integrity(
        self,
        session_id: str,
        context: Dict[str, Any],
        security_context: SessionSecurityContext
    ) -> SessionValidationResult:
        """Validate session integrity"""
        try:
            # Get session data
            session_data = context.get("session_data", {})
            if not session_data:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.INTEGRITY,
                    status=ValidationStatus.INVALID,
                    risk_level=SessionRiskLevel.HIGH,
                    timestamp=datetime.now(timezone.utc),
                    message="No session data provided for integrity check"
                )
            
            # Calculate data hash
            data_str = str(session_data)
            data_hash = hashlib.sha256(data_str.encode()).hexdigest()
            
            # Check if we have a stored integrity check
            stored_check = self.integrity_checks.get(session_id)
            if stored_check:
                # Verify data hasn't been tampered with
                if stored_check.data_hash != data_hash:
                    return SessionValidationResult(
                        validation_id=str(uuid.uuid4()),
                        session_id=session_id,
                        validation_type=ValidationType.INTEGRITY,
                        status=ValidationStatus.INVALID,
                        risk_level=SessionRiskLevel.CRITICAL,
                        timestamp=datetime.now(timezone.utc),
                        message="Session data integrity violation detected"
                    )
                
                # Verify digital signature if present
                if stored_check.signature and stored_check.public_key:
                    if not await self._verify_data_signature(
                        data_str, stored_check.signature, stored_check.public_key
                    ):
                        return SessionValidationResult(
                            validation_id=str(uuid.uuid4()),
                            session_id=session_id,
                            validation_type=ValidationType.INTEGRITY,
                            status=ValidationStatus.INVALID,
                            risk_level=SessionRiskLevel.CRITICAL,
                            timestamp=datetime.now(timezone.utc),
                            message="Session data signature verification failed"
                        )
            else:
                # Create new integrity check
                integrity_check = SessionIntegrityCheck(
                    session_id=session_id,
                    checksum=hashlib.md5(data_str.encode()).hexdigest(),
                    timestamp=datetime.now(timezone.utc),
                    data_hash=data_hash
                )
                self.integrity_checks[session_id] = integrity_check
            
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.INTEGRITY,
                status=ValidationStatus.VALID,
                risk_level=SessionRiskLevel.LOW,
                timestamp=datetime.now(timezone.utc),
                message="Session integrity validation successful"
            )
            
        except Exception as e:
            logger.error(f"Integrity validation error: {e}")
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.INTEGRITY,
                status=ValidationStatus.FAILED,
                risk_level=SessionRiskLevel.CRITICAL,
                timestamp=datetime.now(timezone.utc),
                message=f"Integrity validation error: {str(e)}"
            )
    
    async def _validate_timeout(
        self,
        session_id: str,
        context: Dict[str, Any],
        security_context: SessionSecurityContext
    ) -> SessionValidationResult:
        """Validate session timeout"""
        try:
            session_start = security_context.session_start_time
            current_time = datetime.now(timezone.utc)
            session_duration = current_time - session_start
            
            # Check maximum session duration
            max_duration = timedelta(hours=MAX_SESSION_DURATION_HOURS)
            if session_duration > max_duration:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.TIMEOUT,
                    status=ValidationStatus.EXPIRED,
                    risk_level=SessionRiskLevel.HIGH,
                    timestamp=datetime.now(timezone.utc),
                    message=f"Session exceeded maximum duration of {MAX_SESSION_DURATION_HOURS} hours"
                )
            
            # Check idle timeout
            last_activity = security_context.last_activity
            idle_time = current_time - last_activity
            idle_timeout = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
            
            if idle_time > idle_timeout:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.TIMEOUT,
                    status=ValidationStatus.EXPIRED,
                    risk_level=SessionRiskLevel.MEDIUM,
                    timestamp=datetime.now(timezone.utc),
                    message=f"Session idle timeout exceeded ({SESSION_TIMEOUT_MINUTES} minutes)"
                )
            
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.TIMEOUT,
                status=ValidationStatus.VALID,
                risk_level=SessionRiskLevel.LOW,
                timestamp=datetime.now(timezone.utc),
                message="Session timeout validation successful"
            )
            
        except Exception as e:
            logger.error(f"Timeout validation error: {e}")
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.TIMEOUT,
                status=ValidationStatus.FAILED,
                risk_level=SessionRiskLevel.CRITICAL,
                timestamp=datetime.now(timezone.utc),
                message=f"Timeout validation error: {str(e)}"
            )
    
    async def _validate_resource_usage(
        self,
        session_id: str,
        context: Dict[str, Any],
        security_context: SessionSecurityContext
    ) -> SessionValidationResult:
        """Validate session resource usage"""
        try:
            resource_data = context.get("resource_usage", {})
            if not resource_data:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.RESOURCE,
                    status=ValidationStatus.SUSPICIOUS,
                    risk_level=SessionRiskLevel.MEDIUM,
                    timestamp=datetime.now(timezone.utc),
                    message="No resource usage data provided"
                )
            
            # Check CPU usage
            cpu_percent = resource_data.get("cpu_percent", 0)
            if cpu_percent > 90:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.RESOURCE,
                    status=ValidationStatus.SUSPICIOUS,
                    risk_level=SessionRiskLevel.HIGH,
                    timestamp=datetime.now(timezone.utc),
                    message=f"High CPU usage detected: {cpu_percent}%"
                )
            
            # Check memory usage
            memory_mb = resource_data.get("memory_mb", 0)
            if memory_mb > 4096:  # 4GB limit
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.RESOURCE,
                    status=ValidationStatus.SUSPICIOUS,
                    risk_level=SessionRiskLevel.HIGH,
                    timestamp=datetime.now(timezone.utc),
                    message=f"High memory usage detected: {memory_mb}MB"
                )
            
            # Check network usage
            network_mbps = resource_data.get("network_mbps", 0)
            if network_mbps > 100:  # 100 Mbps limit
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.RESOURCE,
                    status=ValidationStatus.SUSPICIOUS,
                    risk_level=SessionRiskLevel.MEDIUM,
                    timestamp=datetime.now(timezone.utc),
                    message=f"High network usage detected: {network_mbps}Mbps"
                )
            
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.RESOURCE,
                status=ValidationStatus.VALID,
                risk_level=SessionRiskLevel.LOW,
                timestamp=datetime.now(timezone.utc),
                message="Resource usage validation successful"
            )
            
        except Exception as e:
            logger.error(f"Resource validation error: {e}")
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.RESOURCE,
                status=ValidationStatus.FAILED,
                risk_level=SessionRiskLevel.CRITICAL,
                timestamp=datetime.now(timezone.utc),
                message=f"Resource validation error: {str(e)}"
            )
    
    async def _validate_behavior(
        self,
        session_id: str,
        context: Dict[str, Any],
        security_context: SessionSecurityContext
    ) -> SessionValidationResult:
        """Validate session behavior patterns"""
        try:
            behavior_data = context.get("behavior", {})
            if not behavior_data:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.BEHAVIORAL,
                    status=ValidationStatus.SUSPICIOUS,
                    risk_level=SessionRiskLevel.MEDIUM,
                    timestamp=datetime.now(timezone.utc),
                    message="No behavior data provided"
                )
            
            # Check anomaly score
            anomaly_score = behavior_data.get("anomaly_score", 0.0)
            if anomaly_score > 0.8:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.BEHAVIORAL,
                    status=ValidationStatus.SUSPICIOUS,
                    risk_level=SessionRiskLevel.CRITICAL,
                    timestamp=datetime.now(timezone.utc),
                    message=f"High anomaly score detected: {anomaly_score}"
                )
            
            # Check keystroke patterns
            keystroke_rate = behavior_data.get("keystroke_rate", 0)
            if keystroke_rate > 1000:  # 1000 keystrokes per minute
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.BEHAVIORAL,
                    status=ValidationStatus.SUSPICIOUS,
                    risk_level=SessionRiskLevel.HIGH,
                    timestamp=datetime.now(timezone.utc),
                    message=f"Unusual keystroke rate: {keystroke_rate} per minute"
                )
            
            # Check mouse movement patterns
            mouse_movements = behavior_data.get("mouse_movements", 0)
            if mouse_movements > 5000:  # 5000 movements per minute
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.BEHAVIORAL,
                    status=ValidationStatus.SUSPICIOUS,
                    risk_level=SessionRiskLevel.MEDIUM,
                    timestamp=datetime.now(timezone.utc),
                    message=f"Unusual mouse movement rate: {mouse_movements} per minute"
                )
            
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.BEHAVIORAL,
                status=ValidationStatus.VALID,
                risk_level=SessionRiskLevel.LOW,
                timestamp=datetime.now(timezone.utc),
                message="Behavioral validation successful"
            )
            
        except Exception as e:
            logger.error(f"Behavioral validation error: {e}")
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.BEHAVIORAL,
                status=ValidationStatus.FAILED,
                risk_level=SessionRiskLevel.CRITICAL,
                timestamp=datetime.now(timezone.utc),
                message=f"Behavioral validation error: {str(e)}"
            )
    
    async def _validate_network(
        self,
        session_id: str,
        context: Dict[str, Any],
        security_context: SessionSecurityContext
    ) -> SessionValidationResult:
        """Validate network security"""
        try:
            network_data = context.get("network", {})
            if not network_data:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.NETWORK,
                    status=ValidationStatus.SUSPICIOUS,
                    risk_level=SessionRiskLevel.MEDIUM,
                    timestamp=datetime.now(timezone.utc),
                    message="No network data provided"
                )
            
            # Check encryption
            is_encrypted = network_data.get("encrypted", False)
            if not is_encrypted:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.NETWORK,
                    status=ValidationStatus.INVALID,
                    risk_level=SessionRiskLevel.CRITICAL,
                    timestamp=datetime.now(timezone.utc),
                    message="Network connection not encrypted"
                )
            
            # Check VPN requirement
            vpn_required = network_data.get("vpn_required", False)
            if vpn_required and not network_data.get("vpn_connected", False):
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.NETWORK,
                    status=ValidationStatus.INVALID,
                    risk_level=SessionRiskLevel.HIGH,
                    timestamp=datetime.now(timezone.utc),
                    message="VPN connection required but not active"
                )
            
            # Check IP address consistency
            current_ip = network_data.get("ip_address")
            if current_ip and current_ip != security_context.ip_address:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.NETWORK,
                    status=ValidationStatus.SUSPICIOUS,
                    risk_level=SessionRiskLevel.HIGH,
                    timestamp=datetime.now(timezone.utc),
                    message="IP address changed during session"
                )
            
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.NETWORK,
                status=ValidationStatus.VALID,
                risk_level=SessionRiskLevel.LOW,
                timestamp=datetime.now(timezone.utc),
                message="Network security validation successful"
            )
            
        except Exception as e:
            logger.error(f"Network validation error: {e}")
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.NETWORK,
                status=ValidationStatus.FAILED,
                risk_level=SessionRiskLevel.CRITICAL,
                timestamp=datetime.now(timezone.utc),
                message=f"Network validation error: {str(e)}"
            )
    
    async def _validate_device(
        self,
        session_id: str,
        context: Dict[str, Any],
        security_context: SessionSecurityContext
    ) -> SessionValidationResult:
        """Validate device fingerprint"""
        try:
            device_data = context.get("device", {})
            if not device_data:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.DEVICE,
                    status=ValidationStatus.SUSPICIOUS,
                    risk_level=SessionRiskLevel.MEDIUM,
                    timestamp=datetime.now(timezone.utc),
                    message="No device data provided"
                )
            
            # Check device fingerprint
            current_fingerprint = device_data.get("fingerprint")
            if current_fingerprint and security_context.device_fingerprint:
                if current_fingerprint != security_context.device_fingerprint:
                    return SessionValidationResult(
                        validation_id=str(uuid.uuid4()),
                        session_id=session_id,
                        validation_type=ValidationType.DEVICE,
                        status=ValidationStatus.SUSPICIOUS,
                        risk_level=SessionRiskLevel.HIGH,
                        timestamp=datetime.now(timezone.utc),
                        message="Device fingerprint changed during session"
                    )
            
            # Check device verification
            fingerprint_verified = device_data.get("fingerprint_verified", False)
            if not fingerprint_verified:
                return SessionValidationResult(
                    validation_id=str(uuid.uuid4()),
                    session_id=session_id,
                    validation_type=ValidationType.DEVICE,
                    status=ValidationStatus.SUSPICIOUS,
                    risk_level=SessionRiskLevel.MEDIUM,
                    timestamp=datetime.now(timezone.utc),
                    message="Device fingerprint not verified"
                )
            
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.DEVICE,
                status=ValidationStatus.VALID,
                risk_level=SessionRiskLevel.LOW,
                timestamp=datetime.now(timezone.utc),
                message="Device validation successful"
            )
            
        except Exception as e:
            logger.error(f"Device validation error: {e}")
            return SessionValidationResult(
                validation_id=str(uuid.uuid4()),
                session_id=session_id,
                validation_type=ValidationType.DEVICE,
                status=ValidationStatus.FAILED,
                risk_level=SessionRiskLevel.CRITICAL,
                timestamp=datetime.now(timezone.utc),
                message=f"Device validation error: {str(e)}"
            )
    
    async def _create_security_context(
        self,
        session_id: str,
        context: Dict[str, Any]
    ) -> SessionSecurityContext:
        """Create security context for session"""
        return SessionSecurityContext(
            session_id=session_id,
            user_id=context.get("user_id", "unknown"),
            node_id=context.get("node_id", "unknown"),
            ip_address=context.get("ip_address", "unknown"),
            user_agent=context.get("user_agent", "unknown"),
            device_fingerprint=context.get("device", {}).get("fingerprint"),
            location=context.get("location"),
            trust_score=context.get("trust_score", 0.0),
            risk_indicators=context.get("risk_indicators", []),
            metadata=context.get("metadata", {})
        )
    
    async def _verify_digital_signature(
        self,
        signature: str,
        public_key: str,
        message: str
    ) -> bool:
        """Verify digital signature"""
        try:
            # Convert hex strings to bytes
            signature_bytes = bytes.fromhex(signature)
            public_key_bytes = bytes.fromhex(public_key)
            message_bytes = message.encode('utf-8')
            
            # Create public key object
            public_key_obj = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            
            # Verify signature
            public_key_obj.verify(signature_bytes, message_bytes)
            return True
            
        except Exception as e:
            logger.error(f"Digital signature verification failed: {e}")
            return False
    
    async def _verify_data_signature(
        self,
        data: str,
        signature: str,
        public_key: str
    ) -> bool:
        """Verify data signature"""
        try:
            # Convert hex strings to bytes
            signature_bytes = bytes.fromhex(signature)
            public_key_bytes = bytes.fromhex(public_key)
            data_bytes = data.encode('utf-8')
            
            # Create public key object
            public_key_obj = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            
            # Verify signature
            public_key_obj.verify(signature_bytes, data_bytes)
            return True
            
        except Exception as e:
            logger.error(f"Data signature verification failed: {e}")
            return False
    
    async def add_validation_rule(self, rule: SessionValidationRule) -> bool:
        """Add new validation rule"""
        try:
            self.validation_rules[rule.rule_id] = rule
            logger.info(f"Added validation rule: {rule.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add validation rule: {e}")
            return False
    
    async def remove_validation_rule(self, rule_id: str) -> bool:
        """Remove validation rule"""
        try:
            if rule_id in self.validation_rules:
                del self.validation_rules[rule_id]
                logger.info(f"Removed validation rule: {rule_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove validation rule: {e}")
            return False
    
    async def get_session_validation_history(self, session_id: str) -> List[SessionValidationResult]:
        """Get validation history for session"""
        security_context = self.active_sessions.get(session_id)
        if security_context:
            return security_context.validation_history
        return []
    
    async def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            "stats": self.stats,
            "active_sessions": len(self.active_sessions),
            "validation_rules": len(self.validation_rules),
            "cached_validations": len(self.validation_cache),
            "integrity_checks": len(self.integrity_checks)
        }
    
    async def cleanup_expired_sessions(self) -> int:
        """Cleanup expired sessions"""
        try:
            current_time = datetime.now(timezone.utc)
            expired_sessions = []
            
            for session_id, security_context in self.active_sessions.items():
                session_duration = current_time - security_context.session_start_time
                if session_duration > timedelta(hours=MAX_SESSION_DURATION_HOURS):
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.active_sessions[session_id]
                if session_id in self.integrity_checks:
                    del self.integrity_checks[session_id]
            
            # Clean cache
            cache_keys_to_remove = []
            for key, (_, cache_time) in self.validation_cache.items():
                if time.time() - cache_time > VALIDATION_CACHE_TTL:
                    cache_keys_to_remove.append(key)
            
            for key in cache_keys_to_remove:
                del self.validation_cache[key]
            
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions and {len(cache_keys_to_remove)} cache entries")
            return len(expired_sessions)
            
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")
            return 0


# Global session validator instance
_session_validator: Optional[SessionValidator] = None


def get_session_validator() -> Optional[SessionValidator]:
    """Get global session validator instance"""
    return _session_validator


def create_session_validator(db: Optional[AsyncIOMotorDatabase] = None) -> SessionValidator:
    """Create new session validator instance"""
    global _session_validator
    _session_validator = SessionValidator(db)
    return _session_validator


async def start_session_validator():
    """Start session validator service"""
    global _session_validator
    if not _session_validator:
        _session_validator = SessionValidator()
    
    logger.info("Session validator service started")


async def stop_session_validator():
    """Stop session validator service"""
    global _session_validator
    if _session_validator:
        await _session_validator.cleanup_expired_sessions()
        _session_validator = None
    
    logger.info("Session validator service stopped")


async def main():
    """Main function for testing"""
    import asyncio
    
    # Create session validator
    validator = create_session_validator()
    
    # Test session validation
    test_session_id = "test_session_001"
    test_context = {
        "authentication": {
            "valid": True,
            "user_id": "test_user",
            "token": "test_token"
        },
        "authorization": {
            "level": "standard",
            "permissions": ["session_access", "recording_view"]
        },
        "session_data": {
            "session_type": "rdp",
            "owner": "test_user"
        },
        "resource_usage": {
            "cpu_percent": 25.0,
            "memory_mb": 512,
            "network_mbps": 10.0
        },
        "behavior": {
            "anomaly_score": 0.1,
            "keystroke_rate": 50,
            "mouse_movements": 100
        },
        "network": {
            "encrypted": True,
            "vpn_connected": True,
            "ip_address": "192.168.1.100"
        },
        "device": {
            "fingerprint": "test_fingerprint_123",
            "fingerprint_verified": True
        }
    }
    
    # Test different validation types
    validation_types = [
        ValidationType.AUTHENTICATION,
        ValidationType.AUTHORIZATION,
        ValidationType.INTEGRITY,
        ValidationType.TIMEOUT,
        ValidationType.RESOURCE,
        ValidationType.BEHAVIORAL,
        ValidationType.NETWORK,
        ValidationType.DEVICE
    ]
    
    for validation_type in validation_types:
        result = await validator.validate_session(
            test_session_id,
            validation_type,
            test_context
        )
        print(f"{validation_type.value}: {result.status.value} - {result.message}")
    
    # Get statistics
    stats = await validator.get_validation_statistics()
    print(f"\nValidation Statistics: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
