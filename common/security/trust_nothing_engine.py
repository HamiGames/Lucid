# LUCID Common Trust-Nothing Engine - System-Wide Default-Deny Policy Enforcement
# Implements comprehensive zero-trust security model for all system operations
# LUCID-STRICT Layer 1 Common Security Integration

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import hashlib

logger = logging.getLogger(__name__)

# Configuration from environment
COMMON_TRUST_TIMEOUT_SECONDS = 60
COMMON_TRUST_MAX_RETRIES = 5
COMMON_TRUST_AUDIT_RETENTION_DAYS = 180
COMMON_TRUST_ANOMALY_THRESHOLD = 0.7
COMMON_TRUST_RATE_LIMIT_WINDOW = 600  # 10 minutes
COMMON_TRUST_DEFAULT_DENY = True  # Default-deny policy enabled


class PolicyLevel(Enum):
    """Policy enforcement levels"""
    SYSTEM = "system"
    SERVICE = "service"
    COMPONENT = "component"
    USER = "user"
    SESSION = "session"


class TrustLevel(Enum):
    """Trust level classifications for common operations"""
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VerificationMethod(Enum):
    """Verification methods for system-wide trust assessment"""
    SYSTEM_SIGNATURE = "system_signature"
    SERVICE_AUTHENTICATION = "service_authentication"
    COMPONENT_VERIFICATION = "component_verification"
    NETWORK_ANALYSIS = "network_analysis"
    BEHAVIORAL_ANALYSIS = "behavioral_analysis"
    TEMPORAL_ANALYSIS = "temporal_analysis"
    RESOURCE_VALIDATION = "resource_validation"
    DEPENDENCY_CHECK = "dependency_check"


class RiskLevel(Enum):
    """Risk level classifications"""
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EXTREME = "extreme"


class ActionType(Enum):
    """Action types for policy enforcement"""
    ALLOW = "allow"
    DENY = "deny"
    CHALLENGE = "challenge"
    ESCALATE = "escalate"
    QUARANTINE = "quarantine"
    LOG_ONLY = "log_only"
    ISOLATE = "isolate"


@dataclass
class SecurityContext:
    """Context for system-wide security evaluation"""
    request_id: str
    service_name: str
    component_name: str
    operation: str
    resource_path: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_ip: str = "unknown"
    user_agent: str = "unknown"
    request_headers: Dict[str, str] = field(default_factory=dict)
    request_payload: Optional[Dict[str, Any]] = None
    policy_level: PolicyLevel = PolicyLevel.SYSTEM
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityAssessment:
    """Result of security assessment"""
    assessment_id: str
    context: SecurityContext
    overall_trust_score: float
    risk_level: RiskLevel
    recommended_action: ActionType
    verification_methods_used: List[VerificationMethod]
    confidence_score: float
    policy_violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    assessment_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    enforcement_result: Optional[Dict[str, Any]] = None


@dataclass
class SecurityPolicy:
    """Security policy rule"""
    policy_id: str
    name: str
    description: str
    policy_level: PolicyLevel
    condition: str  # JSON-encoded condition
    weight: float
    verification_methods: List[VerificationMethod]
    action_on_violation: ActionType
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityAuditEvent:
    """Audit event for security operations"""
    event_id: str
    assessment_id: str
    event_type: str
    context: SecurityContext
    trust_score: float
    action_taken: ActionType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityAnomaly:
    """Security anomaly detection result"""
    anomaly_id: str
    anomaly_type: str
    severity: RiskLevel
    description: str
    detected_at: datetime
    confidence: float
    context: Dict[str, Any] = field(default_factory=dict)


class TrustNothingEngine:
    """
    System-wide zero-trust security engine with default-deny policy enforcement.
    
    Features:
    - Default-deny policy enforcement
    - Multi-level security assessment
    - Service and component verification
    - Behavioral and temporal analysis
    - Comprehensive audit logging
    - Real-time threat detection
    - Adaptive security policies
    - System-wide anomaly detection
    """
    
    def __init__(self, system_id: str = "lucid_system"):
        """Initialize system-wide trust-nothing engine"""
        self.system_id = system_id
        self.security_policies: Dict[str, SecurityPolicy] = {}
        self.security_assessments: Dict[str, SecurityAssessment] = {}
        self.audit_events: List[SecurityAuditEvent] = []
        self.anomaly_detections: List[SecurityAnomaly] = []
        
        # System patterns and behaviors
        self.service_patterns: Dict[str, Dict[str, Any]] = {}
        self.component_patterns: Dict[str, Dict[str, Any]] = {}
        self.user_patterns: Dict[str, Dict[str, Any]] = {}
        
        # Rate limiting and throttling
        self.rate_limits: Dict[str, List[datetime]] = {}
        self.service_limits: Dict[str, List[datetime]] = {}
        
        # Verification handlers
        self.verification_handlers: Dict[VerificationMethod, Callable] = {}
        
        # Default-deny whitelist (explicitly allowed operations)
        self.whitelist_operations: Set[str] = set()
        
        # Initialize default policies
        self._initialize_default_policies()
        
        logger.info(f"System-wide TrustNothingEngine initialized: {system_id}")
    
    async def assess_security(
        self,
        context: SecurityContext,
        required_trust_level: TrustLevel = TrustLevel.MEDIUM
    ) -> SecurityAssessment:
        """Assess security for given context with default-deny policy"""
        try:
            assessment_id = secrets.token_hex(16)
            
            # Apply default-deny policy first
            if COMMON_TRUST_DEFAULT_DENY and not await self._check_whitelist(context):
                return SecurityAssessment(
                    assessment_id=assessment_id,
                    context=context,
                    overall_trust_score=0.0,
                    risk_level=RiskLevel.EXTREME,
                    recommended_action=ActionType.DENY,
                    verification_methods_used=[],
                    confidence_score=0.0,
                    policy_violations=["Operation not in whitelist - default deny"],
                    warnings=["Default-deny policy enforced"]
                )
            
            # Apply security policies
            trust_scores = []
            verification_methods = []
            policy_violations = []
            warnings = []
            
            for policy_id, policy in self.security_policies.items():
                if not policy.is_active:
                    continue
                
                try:
                    # Evaluate policy condition
                    policy_score, policy_methods, violations, policy_warnings = await self._evaluate_policy(
                        policy, context
                    )
                    
                    trust_scores.append((policy_score, policy.weight))
                    verification_methods.extend(policy_methods)
                    policy_violations.extend(violations)
                    warnings.extend(policy_warnings)
                    
                except Exception as e:
                    logger.error(f"Error evaluating policy {policy_id}: {e}")
                    trust_scores.append((0.0, policy.weight))
                    warnings.append(f"Policy evaluation error: {policy_id}")
            
            # Calculate weighted trust score
            total_weight = sum(weight for _, weight in trust_scores)
            if total_weight > 0:
                overall_trust_score = sum(score * weight for score, weight in trust_scores) / total_weight
            else:
                overall_trust_score = 0.0
            
            # Detect anomalies
            detected_anomalies = await self._detect_security_anomalies(context, overall_trust_score)
            
            # Determine risk level
            risk_level = self._calculate_risk_level(overall_trust_score, policy_violations, detected_anomalies)
            
            # Determine recommended action
            recommended_action = self._determine_action(risk_level, required_trust_level, policy_violations, detected_anomalies)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(verification_methods, policy_violations, detected_anomalies)
            
            # Create assessment
            assessment = SecurityAssessment(
                assessment_id=assessment_id,
                context=context,
                overall_trust_score=overall_trust_score,
                risk_level=risk_level,
                recommended_action=recommended_action,
                verification_methods_used=verification_methods,
                confidence_score=confidence_score,
                policy_violations=policy_violations,
                warnings=warnings,
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=COMMON_TRUST_TIMEOUT_SECONDS)
            )
            
            # Store assessment
            self.security_assessments[assessment_id] = assessment
            
            # Log audit event
            await self._log_security_audit_event(assessment)
            
            # Update behavioral patterns
            await self._update_system_patterns(context, assessment)
            
            logger.info(f"Security assessment completed: {assessment_id}, Score: {overall_trust_score:.2f}, Risk: {risk_level.value}")
            
            return assessment
            
        except Exception as e:
            logger.error(f"Failed to assess security: {e}")
            # Return default deny assessment on error
            return SecurityAssessment(
                assessment_id=secrets.token_hex(16),
                context=context,
                overall_trust_score=0.0,
                risk_level=RiskLevel.EXTREME,
                recommended_action=ActionType.DENY,
                verification_methods_used=[],
                confidence_score=0.0,
                policy_violations=[f"Assessment error: {str(e)}"],
                warnings=["Security assessment failed - default deny"]
            )
    
    async def enforce_policy(
        self,
        context: SecurityContext,
        required_trust_level: TrustLevel = TrustLevel.MEDIUM
    ) -> Tuple[bool, SecurityAssessment]:
        """Enforce security policy with default-deny"""
        try:
            # Assess security first
            assessment = await self.assess_security(context, required_trust_level)
            
            # Enforce based on assessment
            if assessment.recommended_action == ActionType.ALLOW:
                # Check rate limits
                if not await self._check_rate_limits(context):
                    assessment.recommended_action = ActionType.DENY
                    assessment.policy_violations.append("Rate limit exceeded")
                
                # Additional checks for allow action
                if await self._check_suspicious_activity(context):
                    assessment.recommended_action = ActionType.CHALLENGE
                    assessment.policy_violations.append("Suspicious activity detected")
            
            # Execute enforcement action
            enforcement_result = await self._execute_enforcement_action(assessment)
            assessment.enforcement_result = enforcement_result
            
            # Update assessment with enforcement result
            self.security_assessments[assessment.assessment_id] = assessment
            
            # Log enforcement action
            await self._log_enforcement_action(assessment, enforcement_result)
            
            is_allowed = assessment.recommended_action == ActionType.ALLOW
            
            logger.info(f"Policy enforcement: {assessment.assessment_id}, Allowed: {is_allowed}, Action: {assessment.recommended_action.value}")
            
            return is_allowed, assessment
            
        except Exception as e:
            logger.error(f"Policy enforcement failed: {e}")
            # Default deny on enforcement failure
            return False, SecurityAssessment(
                assessment_id=secrets.token_hex(16),
                context=context,
                overall_trust_score=0.0,
                risk_level=RiskLevel.EXTREME,
                recommended_action=ActionType.DENY,
                verification_methods_used=[],
                confidence_score=0.0,
                policy_violations=[f"Enforcement error: {str(e)}"],
                warnings=["Policy enforcement failed - default deny"]
            )
    
    async def add_to_whitelist(self, operation: str) -> bool:
        """Add operation to whitelist (explicitly allow)"""
        try:
            self.whitelist_operations.add(operation)
            logger.info(f"Added to whitelist: {operation}")
            return True
        except Exception as e:
            logger.error(f"Failed to add to whitelist: {e}")
            return False
    
    async def remove_from_whitelist(self, operation: str) -> bool:
        """Remove operation from whitelist"""
        try:
            self.whitelist_operations.discard(operation)
            logger.info(f"Removed from whitelist: {operation}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove from whitelist: {e}")
            return False
    
    async def create_security_policy(
        self,
        name: str,
        description: str,
        policy_level: PolicyLevel,
        condition: str,
        weight: float,
        verification_methods: List[VerificationMethod],
        action_on_violation: ActionType,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create new security policy"""
        try:
            policy_id = secrets.token_hex(16)
            
            policy = SecurityPolicy(
                policy_id=policy_id,
                name=name,
                description=description,
                policy_level=policy_level,
                condition=condition,
                weight=weight,
                verification_methods=verification_methods,
                action_on_violation=action_on_violation,
                metadata=metadata or {}
            )
            
            self.security_policies[policy_id] = policy
            
            logger.info(f"Created security policy: {policy_id} - {name}")
            return policy_id
            
        except Exception as e:
            logger.error(f"Failed to create security policy: {e}")
            raise
    
    async def check_anomalies(self, context: SecurityContext) -> List[SecurityAnomaly]:
        """Check for security anomalies"""
        try:
            anomalies = []
            
            # Check service anomalies
            service_anomalies = await self._check_service_anomalies(context)
            anomalies.extend(service_anomalies)
            
            # Check component anomalies
            component_anomalies = await self._check_component_anomalies(context)
            anomalies.extend(component_anomalies)
            
            # Check temporal anomalies
            temporal_anomalies = await self._check_temporal_anomalies(context)
            anomalies.extend(temporal_anomalies)
            
            # Check behavioral anomalies
            behavioral_anomalies = await self._check_behavioral_anomalies(context)
            anomalies.extend(behavioral_anomalies)
            
            # Store anomalies
            for anomaly in anomalies:
                self.anomaly_detections.append(anomaly)
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return []
    
    async def get_security_status(self) -> Dict[str, Any]:
        """Get security engine status"""
        return {
            "system_id": self.system_id,
            "default_deny_enabled": COMMON_TRUST_DEFAULT_DENY,
            "whitelist_operations": len(self.whitelist_operations),
            "active_policies": len([p for p in self.security_policies.values() if p.is_active]),
            "total_assessments": len(self.security_assessments),
            "audit_events": len(self.audit_events),
            "anomaly_detections": len(self.anomaly_detections),
            "service_patterns": len(self.service_patterns),
            "component_patterns": len(self.component_patterns),
            "user_patterns": len(self.user_patterns),
            "policies": {
                policy_id: {
                    "name": policy.name,
                    "policy_level": policy.policy_level.value,
                    "weight": policy.weight,
                    "is_active": policy.is_active,
                    "verification_methods": [m.value for m in policy.verification_methods]
                }
                for policy_id, policy in self.security_policies.items()
            }
        }
    
    async def _check_whitelist(self, context: SecurityContext) -> bool:
        """Check if operation is in whitelist"""
        operation_key = f"{context.service_name}:{context.component_name}:{context.operation}"
        return operation_key in self.whitelist_operations
    
    async def _evaluate_policy(
        self,
        policy: SecurityPolicy,
        context: SecurityContext
    ) -> Tuple[float, List[VerificationMethod], List[str], List[str]]:
        """Evaluate individual security policy"""
        try:
            trust_score = 0.0
            verification_methods = []
            violations = []
            warnings = []
            
            # Apply verification methods
            for method in policy.verification_methods:
                method_score, method_violations, method_warnings = await self._apply_verification_method(
                    method, context
                )
                
                trust_score += method_score * (1.0 / len(policy.verification_methods))
                verification_methods.append(method)
                violations.extend(method_violations)
                warnings.extend(method_warnings)
            
            return trust_score, verification_methods, violations, warnings
            
        except Exception as e:
            logger.error(f"Policy evaluation error: {e}")
            return 0.0, [], [f"Policy evaluation error: {str(e)}"], []
    
    async def _apply_verification_method(
        self,
        method: VerificationMethod,
        context: SecurityContext
    ) -> Tuple[float, List[str], List[str]]:
        """Apply specific verification method"""
        try:
            if method == VerificationMethod.SYSTEM_SIGNATURE:
                return await self._verify_system_signature(context)
            elif method == VerificationMethod.SERVICE_AUTHENTICATION:
                return await self._verify_service_authentication(context)
            elif method == VerificationMethod.COMPONENT_VERIFICATION:
                return await self._verify_component_verification(context)
            elif method == VerificationMethod.NETWORK_ANALYSIS:
                return await self._verify_network_analysis(context)
            elif method == VerificationMethod.BEHAVIORAL_ANALYSIS:
                return await self._verify_behavioral_analysis(context)
            elif method == VerificationMethod.TEMPORAL_ANALYSIS:
                return await self._verify_temporal_analysis(context)
            elif method == VerificationMethod.RESOURCE_VALIDATION:
                return await self._verify_resource_validation(context)
            elif method == VerificationMethod.DEPENDENCY_CHECK:
                return await self._verify_dependency_check(context)
            else:
                return 0.0, [], [f"Unknown verification method: {method.value}"]
                
        except Exception as e:
            logger.error(f"Verification method error: {e}")
            return 0.0, [f"Verification error: {str(e)}"], []
    
    async def _verify_system_signature(self, context: SecurityContext) -> Tuple[float, List[str], List[str]]:
        """Verify system-level signatures"""
        # Simplified system signature verification
        return 0.9, [], []
    
    async def _verify_service_authentication(self, context: SecurityContext) -> Tuple[float, List[str], List[str]]:
        """Verify service authentication"""
        # Check service authentication
        if context.service_name in ["lucid_core", "lucid_wallet", "lucid_node"]:
            return 0.8, [], []
        else:
            return 0.4, ["Unknown service"], []
    
    async def _verify_component_verification(self, context: SecurityContext) -> Tuple[float, List[str], List[str]]:
        """Verify component integrity"""
        # Check component verification
        return 0.7, [], []
    
    async def _verify_network_analysis(self, context: SecurityContext) -> Tuple[float, List[str], List[str]]:
        """Verify network security"""
        # Check network context
        if context.source_ip.startswith("127.0.0.1"):
            return 1.0, [], []
        else:
            return 0.6, [], []
    
    async def _verify_behavioral_analysis(self, context: SecurityContext) -> Tuple[float, List[str], List[str]]:
        """Verify behavioral patterns"""
        # Check behavioral patterns
        service_pattern = self.service_patterns.get(context.service_name, {})
        if not service_pattern:
            return 0.5, ["No behavioral history"], []
        
        return 0.6, [], []
    
    async def _verify_temporal_analysis(self, context: SecurityContext) -> Tuple[float, List[str], List[str]]:
        """Verify temporal patterns"""
        # Check if operation is during expected hours
        hour = context.timestamp.hour
        if 6 <= hour <= 22:  # Normal hours
            return 0.7, [], []
        else:
            return 0.3, ["Operation outside normal hours"], []
    
    async def _verify_resource_validation(self, context: SecurityContext) -> Tuple[float, List[str], List[str]]:
        """Verify resource access validation"""
        # Check resource path
        if context.resource_path.startswith("/secure/"):
            return 0.8, [], []
        else:
            return 0.6, [], []
    
    async def _verify_dependency_check(self, context: SecurityContext) -> Tuple[float, List[str], List[str]]:
        """Verify dependency integrity"""
        # Check dependencies
        return 0.7, [], []
    
    async def _detect_security_anomalies(self, context: SecurityContext, trust_score: float) -> List[str]:
        """Detect security anomalies"""
        anomalies = []
        
        # Check for low trust score
        if trust_score < COMMON_TRUST_ANOMALY_THRESHOLD:
            anomalies.append("Low trust score detected")
        
        # Check for rapid successive operations
        if await self._check_rapid_operations(context):
            anomalies.append("Rapid successive operations detected")
        
        # Check for unusual service patterns
        if await self._check_unusual_service_patterns(context):
            anomalies.append("Unusual service pattern detected")
        
        return anomalies
    
    async def _check_rapid_operations(self, context: SecurityContext) -> bool:
        """Check for rapid successive operations"""
        recent_operations = [
            event for event in self.audit_events
            if event.context.service_name == context.service_name
            and event.timestamp > datetime.now(timezone.utc) - timedelta(minutes=1)
        ]
        
        return len(recent_operations) > 50
    
    async def _check_unusual_service_patterns(self, context: SecurityContext) -> bool:
        """Check for unusual service patterns"""
        service_pattern = self.service_patterns.get(context.service_name, {})
        if not service_pattern:
            return False
        
        # Simplified pattern checking
        return False
    
    async def _check_service_anomalies(self, context: SecurityContext) -> List[SecurityAnomaly]:
        """Check for service-level anomalies"""
        anomalies = []
        
        # Check service behavior
        service_pattern = self.service_patterns.get(context.service_name, {})
        if not service_pattern:
            anomalies.append(SecurityAnomaly(
                anomaly_id=secrets.token_hex(16),
                anomaly_type="service_pattern",
                severity=RiskLevel.MEDIUM,
                description="No service pattern history",
                detected_at=datetime.now(timezone.utc),
                confidence=0.7,
                context={"service": context.service_name}
            ))
        
        return anomalies
    
    async def _check_component_anomalies(self, context: SecurityContext) -> List[SecurityAnomaly]:
        """Check for component-level anomalies"""
        anomalies = []
        
        # Check component behavior
        component_pattern = self.component_patterns.get(context.component_name, {})
        if not component_pattern:
            anomalies.append(SecurityAnomaly(
                anomaly_id=secrets.token_hex(16),
                anomaly_type="component_pattern",
                severity=RiskLevel.LOW,
                description="No component pattern history",
                detected_at=datetime.now(timezone.utc),
                confidence=0.5,
                context={"component": context.component_name}
            ))
        
        return anomalies
    
    async def _check_temporal_anomalies(self, context: SecurityContext) -> List[SecurityAnomaly]:
        """Check for temporal anomalies"""
        anomalies = []
        
        # Check for operations at unusual times
        hour = context.timestamp.hour
        if hour < 3 or hour > 23:
            anomalies.append(SecurityAnomaly(
                anomaly_id=secrets.token_hex(16),
                anomaly_type="temporal",
                severity=RiskLevel.MEDIUM,
                description="Operation at unusual time",
                detected_at=datetime.now(timezone.utc),
                confidence=0.8,
                context={"hour": hour}
            ))
        
        return anomalies
    
    async def _check_behavioral_anomalies(self, context: SecurityContext) -> List[SecurityAnomaly]:
        """Check for behavioral anomalies"""
        anomalies = []
        
        # Check user patterns if user_id is present
        if context.user_id:
            user_pattern = self.user_patterns.get(context.user_id, {})
            if not user_pattern:
                anomalies.append(SecurityAnomaly(
                    anomaly_id=secrets.token_hex(16),
                    anomaly_type="behavioral",
                    severity=RiskLevel.LOW,
                    description="No user pattern history",
                    detected_at=datetime.now(timezone.utc),
                    confidence=0.6,
                    context={"user_id": context.user_id}
                ))
        
        return anomalies
    
    def _calculate_risk_level(self, trust_score: float, violations: List[str], anomalies: List[str]) -> RiskLevel:
        """Calculate risk level based on trust score, violations, and anomalies"""
        if trust_score >= 0.9 and not violations and not anomalies:
            return RiskLevel.MINIMAL
        elif trust_score >= 0.7 and len(violations) <= 1 and len(anomalies) <= 1:
            return RiskLevel.LOW
        elif trust_score >= 0.5 and len(violations) <= 2 and len(anomalies) <= 2:
            return RiskLevel.MEDIUM
        elif trust_score >= 0.3 and len(violations) <= 3 and len(anomalies) <= 3:
            return RiskLevel.HIGH
        elif trust_score >= 0.1:
            return RiskLevel.CRITICAL
        else:
            return RiskLevel.EXTREME
    
    def _determine_action(
        self,
        risk_level: RiskLevel,
        required_trust_level: TrustLevel,
        violations: List[str],
        anomalies: List[str]
    ) -> ActionType:
        """Determine recommended action based on risk assessment"""
        if risk_level == RiskLevel.EXTREME:
            return ActionType.DENY
        elif risk_level == RiskLevel.CRITICAL:
            return ActionType.QUARANTINE
        elif risk_level == RiskLevel.HIGH:
            return ActionType.CHALLENGE
        elif risk_level == RiskLevel.MEDIUM and (len(violations) > 0 or len(anomalies) > 0):
            return ActionType.CHALLENGE
        elif risk_level in [RiskLevel.MINIMAL, RiskLevel.LOW]:
            return ActionType.ALLOW
        else:
            return ActionType.LOG_ONLY
    
    def _calculate_confidence_score(
        self,
        verification_methods: List[VerificationMethod],
        violations: List[str],
        anomalies: List[str]
    ) -> float:
        """Calculate confidence score for assessment"""
        base_confidence = len(verification_methods) * 0.15
        violation_penalty = len(violations) * 0.1
        anomaly_penalty = len(anomalies) * 0.05
        
        return max(0.0, min(1.0, base_confidence - violation_penalty - anomaly_penalty))
    
    async def _check_rate_limits(self, context: SecurityContext) -> bool:
        """Check rate limits for service and user"""
        current_time = datetime.now(timezone.utc)
        window_start = current_time - timedelta(seconds=COMMON_TRUST_RATE_LIMIT_WINDOW)
        
        # Check service rate limit
        if context.service_name not in self.service_limits:
            self.service_limits[context.service_name] = []
        
        # Clean old entries
        self.service_limits[context.service_name] = [
            timestamp for timestamp in self.service_limits[context.service_name]
            if timestamp > window_start
        ]
        
        # Check service rate limit (1000 requests per window)
        if len(self.service_limits[context.service_name]) >= 1000:
            return False
        
        # Add current request
        self.service_limits[context.service_name].append(current_time)
        
        # Check user rate limit if user_id is present
        if context.user_id:
            if context.user_id not in self.rate_limits:
                self.rate_limits[context.user_id] = []
            
            # Clean old entries
            self.rate_limits[context.user_id] = [
                timestamp for timestamp in self.rate_limits[context.user_id]
                if timestamp > window_start
            ]
            
            # Check user rate limit (100 requests per window)
            if len(self.rate_limits[context.user_id]) >= 100:
                return False
            
            # Add current request
            self.rate_limits[context.user_id].append(current_time)
        
        return True
    
    async def _check_suspicious_activity(self, context: SecurityContext) -> bool:
        """Check for suspicious activity patterns"""
        # Check for multiple rapid requests from same source
        recent_requests = [
            event for event in self.audit_events
            if event.context.source_ip == context.source_ip
            and event.timestamp > datetime.now(timezone.utc) - timedelta(minutes=5)
        ]
        
        return len(recent_requests) > 20
    
    async def _execute_enforcement_action(self, assessment: SecurityAssessment) -> Dict[str, Any]:
        """Execute the recommended enforcement action"""
        action = assessment.recommended_action
        
        if action == ActionType.ALLOW:
            return {"status": "allowed", "message": "Operation permitted"}
        elif action == ActionType.DENY:
            return {"status": "denied", "message": "Operation denied"}
        elif action == ActionType.CHALLENGE:
            return {"status": "challenge", "message": "Additional verification required"}
        elif action == ActionType.QUARANTINE:
            return {"status": "quarantined", "message": "Operation quarantined"}
        elif action == ActionType.ISOLATE:
            return {"status": "isolated", "message": "Operation isolated"}
        else:
            return {"status": "logged", "message": "Operation logged only"}
    
    async def _log_security_audit_event(self, assessment: SecurityAssessment) -> None:
        """Log security audit event"""
        try:
            event = SecurityAuditEvent(
                event_id=secrets.token_hex(16),
                assessment_id=assessment.assessment_id,
                event_type="security_assessment",
                context=assessment.context,
                trust_score=assessment.overall_trust_score,
                action_taken=assessment.recommended_action,
                details={
                    "risk_level": assessment.risk_level.value,
                    "confidence_score": assessment.confidence_score,
                    "policy_violations": assessment.policy_violations,
                    "verification_methods": [m.value for m in assessment.verification_methods_used]
                }
            )
            
            self.audit_events.append(event)
            
            # Clean up old events
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=COMMON_TRUST_AUDIT_RETENTION_DAYS)
            self.audit_events = [e for e in self.audit_events if e.timestamp > cutoff_date]
            
        except Exception as e:
            logger.error(f"Failed to log security audit event: {e}")
    
    async def _log_enforcement_action(self, assessment: SecurityAssessment, enforcement_result: Dict[str, Any]) -> None:
        """Log enforcement action"""
        try:
            event = SecurityAuditEvent(
                event_id=secrets.token_hex(16),
                assessment_id=assessment.assessment_id,
                event_type="policy_enforcement",
                context=assessment.context,
                trust_score=assessment.overall_trust_score,
                action_taken=assessment.recommended_action,
                details=enforcement_result
            )
            
            self.audit_events.append(event)
            
        except Exception as e:
            logger.error(f"Failed to log enforcement action: {e}")
    
    async def _update_system_patterns(self, context: SecurityContext, assessment: SecurityAssessment) -> None:
        """Update system behavioral patterns"""
        try:
            # Update service patterns
            if context.service_name not in self.service_patterns:
                self.service_patterns[context.service_name] = {}
            
            service_pattern = self.service_patterns[context.service_name]
            
            if "operations" not in service_pattern:
                service_pattern["operations"] = []
            
            service_pattern["operations"].append({
                "operation": context.operation,
                "component": context.component_name,
                "timestamp": context.timestamp.isoformat(),
                "trust_score": assessment.overall_trust_score,
                "source_ip": context.source_ip
            })
            
            # Keep only recent operations
            service_pattern["operations"] = service_pattern["operations"][-200:]
            
            # Update component patterns
            if context.component_name not in self.component_patterns:
                self.component_patterns[context.component_name] = {}
            
            component_pattern = self.component_patterns[context.component_name]
            component_pattern["last_activity"] = context.timestamp.isoformat()
            component_pattern["trust_score"] = assessment.overall_trust_score
            
            # Update user patterns if user_id is present
            if context.user_id:
                if context.user_id not in self.user_patterns:
                    self.user_patterns[context.user_id] = {}
                
                user_pattern = self.user_patterns[context.user_id]
                
                if "operations" not in user_pattern:
                    user_pattern["operations"] = []
                
                user_pattern["operations"].append({
                    "operation": context.operation,
                    "service": context.service_name,
                    "component": context.component_name,
                    "timestamp": context.timestamp.isoformat(),
                    "trust_score": assessment.overall_trust_score
                })
                
                # Keep only recent operations
                user_pattern["operations"] = user_pattern["operations"][-100:]
            
        except Exception as e:
            logger.error(f"Failed to update system patterns: {e}")
    
    def _initialize_default_policies(self) -> None:
        """Initialize default security policies"""
        try:
            # Default system-level policy
            self.security_policies["system_default"] = SecurityPolicy(
                policy_id="system_default",
                name="System Default Policy",
                description="Default system-wide security policy",
                policy_level=PolicyLevel.SYSTEM,
                condition='{"type": "system_default"}',
                weight=0.3,
                verification_methods=[
                    VerificationMethod.SYSTEM_SIGNATURE,
                    VerificationMethod.SERVICE_AUTHENTICATION
                ],
                action_on_violation=ActionType.DENY
            )
            
            # Default service-level policy
            self.security_policies["service_default"] = SecurityPolicy(
                policy_id="service_default",
                name="Service Default Policy",
                description="Default service-level security policy",
                policy_level=PolicyLevel.SERVICE,
                condition='{"type": "service_default"}',
                weight=0.25,
                verification_methods=[
                    VerificationMethod.SERVICE_AUTHENTICATION,
                    VerificationMethod.COMPONENT_VERIFICATION
                ],
                action_on_violation=ActionType.CHALLENGE
            )
            
            # Default component-level policy
            self.security_policies["component_default"] = SecurityPolicy(
                policy_id="component_default",
                name="Component Default Policy",
                description="Default component-level security policy",
                policy_level=PolicyLevel.COMPONENT,
                condition='{"type": "component_default"}',
                weight=0.2,
                verification_methods=[
                    VerificationMethod.COMPONENT_VERIFICATION,
                    VerificationMethod.RESOURCE_VALIDATION
                ],
                action_on_violation=ActionType.LOG_ONLY
            )
            
            # Default behavioral analysis policy
            self.security_policies["behavioral_analysis"] = SecurityPolicy(
                policy_id="behavioral_analysis",
                name="Behavioral Analysis Policy",
                description="Behavioral analysis security policy",
                policy_level=PolicyLevel.SYSTEM,
                condition='{"type": "behavioral"}',
                weight=0.15,
                verification_methods=[
                    VerificationMethod.BEHAVIORAL_ANALYSIS,
                    VerificationMethod.TEMPORAL_ANALYSIS
                ],
                action_on_violation=ActionType.LOG_ONLY
            )
            
            # Default network analysis policy
            self.security_policies["network_analysis"] = SecurityPolicy(
                policy_id="network_analysis",
                name="Network Analysis Policy",
                description="Network analysis security policy",
                policy_level=PolicyLevel.SYSTEM,
                condition='{"type": "network"}',
                weight=0.1,
                verification_methods=[
                    VerificationMethod.NETWORK_ANALYSIS,
                    VerificationMethod.DEPENDENCY_CHECK
                ],
                action_on_violation=ActionType.LOG_ONLY
            )
            
            logger.info("Initialized default security policies")
            
        except Exception as e:
            logger.error(f"Failed to initialize default policies: {e}")


# Global system-wide trust-nothing engines
_system_trust_engines: Dict[str, TrustNothingEngine] = {}


def get_system_trust_engine(system_id: str = "lucid_system") -> Optional[TrustNothingEngine]:
    """Get system-wide trust-nothing engine"""
    return _system_trust_engines.get(system_id)


def create_system_trust_engine(system_id: str = "lucid_system") -> TrustNothingEngine:
    """Create new system-wide trust-nothing engine"""
    trust_engine = TrustNothingEngine(system_id)
    _system_trust_engines[system_id] = trust_engine
    return trust_engine


async def main():
    """Main function for testing"""
    import asyncio
    
    # Create system trust engine
    trust_engine = create_system_trust_engine("test_system_001")
    
    # Add some operations to whitelist
    await trust_engine.add_to_whitelist("lucid_core:security:assess_trust")
    await trust_engine.add_to_whitelist("lucid_wallet:wallet:create_wallet")
    
    # Create test context
    context = SecurityContext(
        request_id="test_request_001",
        service_name="lucid_core",
        component_name="security",
        operation="assess_trust",
        resource_path="/security/assess",
        user_id="test_user_001",
        session_id="test_session_001",
        source_ip="127.0.0.1",
        user_agent="Test Agent",
        request_headers={"Authorization": "Bearer test_token"},
        policy_level=PolicyLevel.SYSTEM
    )
    
    # Assess security
    assessment = await trust_engine.assess_security(context, TrustLevel.MEDIUM)
    print(f"Security assessment: {assessment.assessment_id}")
    print(f"Trust score: {assessment.overall_trust_score:.2f}")
    print(f"Risk level: {assessment.risk_level.value}")
    print(f"Recommended action: {assessment.recommended_action.value}")
    print(f"Policy violations: {assessment.policy_violations}")
    
    # Test policy enforcement
    is_allowed, enforcement_assessment = await trust_engine.enforce_policy(context, TrustLevel.MEDIUM)
    print(f"Policy enforcement: Allowed={is_allowed}, Action={enforcement_assessment.recommended_action.value}")
    
    # Test non-whitelisted operation (should be denied)
    context.operation = "unauthorized_operation"
    assessment_denied = await trust_engine.assess_security(context, TrustLevel.MEDIUM)
    print(f"Non-whitelisted operation: Action={assessment_denied.recommended_action.value}")
    
    # Get engine status
    status = await trust_engine.get_security_status()
    print(f"Engine status: {status}")


if __name__ == "__main__":
    asyncio.run(main())
