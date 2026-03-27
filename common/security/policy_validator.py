# LUCID Common Policy Validator - Just-In-Time Approval System
# Implements dynamic policy validation and JIT approval workflows
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
import uuid

from .trust_nothing_engine import (
    SecurityContext, SecurityAssessment, SecurityPolicy, 
    PolicyLevel, TrustLevel, RiskLevel, ActionType, VerificationMethod,
    TrustNothingEngine
)

logger = logging.getLogger(__name__)

# JIT Policy Configuration
JIT_APPROVAL_TIMEOUT_SECONDS = 300  # 5 minutes
JIT_APPROVAL_MAX_ATTEMPTS = 3
JIT_APPROVAL_CACHE_TTL_SECONDS = 3600  # 1 hour
JIT_APPROVAL_ESCALATION_THRESHOLD = 0.8
JIT_APPROVAL_AUTO_APPROVE_THRESHOLD = 0.95


class ApprovalStatus(Enum):
    """JIT approval status states"""
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    ESCALATED = "escalated"
    AUTO_APPROVED = "auto_approved"
    CHALLENGED = "challenged"
    REVOKED = "revoked"


class ApprovalMethod(Enum):
    """Approval methods for JIT decisions"""
    AUTOMATIC = "automatic"
    ADMIN_APPROVAL = "admin_approval"
    USER_CONFIRMATION = "user_confirmation"
    POLICY_BASED = "policy_based"
    ESCALATION = "escalation"
    CHALLENGE_RESPONSE = "challenge_response"


class PolicyViolationType(Enum):
    """Types of policy violations"""
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    RESOURCE_MISUSE = "resource_misuse"
    DATA_EXFILTRATION = "data_exfiltration"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    COMPLIANCE_VIOLATION = "compliance_violation"
    TEMPORAL_VIOLATION = "temporal_violation"
    NETWORK_VIOLATION = "network_violation"


@dataclass
class PolicyValidationRequest:
    """Request for policy validation and JIT approval"""
    request_id: str
    context: SecurityContext
    required_trust_level: TrustLevel
    policy_violations: List[str] = field(default_factory=list)
    risk_indicators: List[str] = field(default_factory=list)
    approval_metadata: Dict[str, Any] = field(default_factory=dict)
    requested_by: Optional[str] = None
    approval_deadline: Optional[datetime] = None
    escalation_level: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PolicyValidationResult:
    """Result of policy validation"""
    validation_id: str
    request: PolicyValidationRequest
    is_valid: bool
    approval_status: ApprovalStatus
    approval_method: ApprovalMethod
    trust_score: float
    risk_level: RiskLevel
    violations_found: List[str]
    recommendations: List[str]
    approval_token: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    escalation_required: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovalChallenge:
    """Challenge for additional verification"""
    challenge_id: str
    validation_id: str
    challenge_type: str
    challenge_data: Dict[str, Any]
    expires_at: datetime
    max_attempts: int = 3
    attempts_used: int = 0
    is_resolved: bool = False


class PolicyValidator:
    """
    Just-In-Time Policy Validation Engine
    
    Provides dynamic policy validation, approval workflows, and JIT access control
    for the LUCID system with comprehensive audit trails and escalation mechanisms.
    """
    
    def __init__(self, trust_engine: Optional[TrustNothingEngine] = None):
        self.trust_engine = trust_engine or TrustNothingEngine()
        self.active_validations: Dict[str, PolicyValidationResult] = {}
        self.approval_cache: Dict[str, PolicyValidationResult] = {}
        self.escalation_queue: List[PolicyValidationRequest] = []
        self.challenges: Dict[str, ApprovalChallenge] = {}
        self.policy_cache: Dict[str, SecurityPolicy] = {}
        self.validation_history: List[PolicyValidationResult] = []
        
        # Rate limiting
        self.validation_attempts: Dict[str, List[datetime]] = {}
        self.max_validations_per_minute = 60
        
        # Initialize default policies
        self._initialize_default_policies()
        
        logger.info("Policy Validator initialized with JIT approval system")
    
    async def validate_policy(
        self,
        context: SecurityContext,
        required_trust_level: TrustLevel = TrustLevel.MEDIUM,
        auto_approve: bool = False,
        approval_timeout: int = JIT_APPROVAL_TIMEOUT_SECONDS
    ) -> PolicyValidationResult:
        """
        Validate policy and determine JIT approval requirements
        
        Args:
            context: Security context for validation
            required_trust_level: Minimum trust level required
            auto_approve: Whether to attempt automatic approval
            approval_timeout: Timeout for approval process in seconds
            
        Returns:
            PolicyValidationResult with approval status and recommendations
        """
        validation_id = str(uuid.uuid4())
        
        # Create validation request
        request = PolicyValidationRequest(
            request_id=validation_id,
            context=context,
            required_trust_level=required_trust_level,
            approval_deadline=datetime.now(timezone.utc) + timedelta(seconds=approval_timeout)
        )
        
        try:
            # Check rate limits
            if not await self._check_rate_limits(context):
                return await self._create_denied_result(
                    request, "Rate limit exceeded", ApprovalStatus.DENIED
                )
            
            # Check cache for recent approvals
            cache_key = self._generate_cache_key(context)
            if cache_key in self.approval_cache:
                cached_result = self.approval_cache[cache_key]
                if self._is_cache_valid(cached_result):
                    logger.info(f"Using cached approval for {validation_id}")
                    return cached_result
            
            # Perform security assessment
            assessment = await self.trust_engine.assess_security(context, required_trust_level)
            
            # Analyze policy violations
            violations = await self._analyze_policy_violations(context, assessment)
            request.policy_violations = violations
            
            # Determine approval requirements
            approval_status, approval_method = await self._determine_approval_requirements(
                assessment, violations, auto_approve
            )
            
            # Create validation result
            result = PolicyValidationResult(
                validation_id=validation_id,
                request=request,
                is_valid=approval_status in [ApprovalStatus.APPROVED, ApprovalStatus.AUTO_APPROVED],
                approval_status=approval_status,
                approval_method=approval_method,
                trust_score=assessment.overall_trust_score,
                risk_level=assessment.risk_level,
                violations_found=violations,
                recommendations=assessment.policy_violations,
                escalation_required=assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.EXTREME]
            )
            
            # Handle different approval statuses
            if approval_status == ApprovalStatus.AUTO_APPROVED:
                result.approved_by = "system"
                result.approved_at = datetime.now(timezone.utc)
                result.expires_at = datetime.now(timezone.utc) + timedelta(seconds=JIT_APPROVAL_CACHE_TTL_SECONDS)
                result.approval_token = self._generate_approval_token()
                
            elif approval_status == ApprovalStatus.PENDING:
                # Add to escalation queue if required
                if result.escalation_required:
                    self.escalation_queue.append(request)
                
                # Create challenge if needed
                if assessment.recommended_action == ActionType.CHALLENGE:
                    await self._create_approval_challenge(result)
            
            # Cache the result
            self.approval_cache[cache_key] = result
            self.active_validations[validation_id] = result
            self.validation_history.append(result)
            
            # Log validation event
            await self._log_validation_event(result)
            
            logger.info(f"Policy validation completed: {validation_id}, status: {approval_status.value}")
            return result
            
        except Exception as e:
            logger.error(f"Policy validation failed for {validation_id}: {e}")
            return await self._create_denied_result(
                request, f"Validation error: {str(e)}", ApprovalStatus.DENIED
            )
    
    async def approve_validation(
        self,
        validation_id: str,
        approved_by: str,
        approval_reason: str = "",
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Approve a pending validation request
        
        Args:
            validation_id: ID of validation to approve
            approved_by: User/service that approved the request
            approval_reason: Reason for approval
            additional_metadata: Additional metadata for approval
            
        Returns:
            True if approval was successful, False otherwise
        """
        if validation_id not in self.active_validations:
            logger.warning(f"Validation not found: {validation_id}")
            return False
        
        result = self.active_validations[validation_id]
        
        # Check if validation is still pending
        if result.approval_status != ApprovalStatus.PENDING:
            logger.warning(f"Validation {validation_id} is not pending: {result.approval_status.value}")
            return False
        
        # Check if validation has expired
        if result.request.approval_deadline and datetime.now(timezone.utc) > result.request.approval_deadline:
            result.approval_status = ApprovalStatus.EXPIRED
            logger.warning(f"Validation {validation_id} has expired")
            return False
        
        # Update validation result
        result.approval_status = ApprovalStatus.APPROVED
        result.approved_by = approved_by
        result.approved_at = datetime.now(timezone.utc)
        result.expires_at = datetime.now(timezone.utc) + timedelta(seconds=JIT_APPROVAL_CACHE_TTL_SECONDS)
        result.approval_token = self._generate_approval_token()
        
        if additional_metadata:
            result.metadata.update(additional_metadata)
        
        # Remove from escalation queue if present
        self.escalation_queue = [
            req for req in self.escalation_queue 
            if req.request_id != validation_id
        ]
        
        # Update cache
        cache_key = self._generate_cache_key(result.request.context)
        self.approval_cache[cache_key] = result
        
        logger.info(f"Validation approved: {validation_id} by {approved_by}")
        await self._log_approval_event(result, approved_by, approval_reason)
        
        return True
    
    async def deny_validation(
        self,
        validation_id: str,
        denied_by: str,
        denial_reason: str,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Deny a pending validation request
        
        Args:
            validation_id: ID of validation to deny
            denied_by: User/service that denied the request
            denial_reason: Reason for denial
            additional_metadata: Additional metadata for denial
            
        Returns:
            True if denial was successful, False otherwise
        """
        if validation_id not in self.active_validations:
            logger.warning(f"Validation not found: {validation_id}")
            return False
        
        result = self.active_validations[validation_id]
        
        # Update validation result
        result.approval_status = ApprovalStatus.DENIED
        result.approved_by = denied_by
        result.approved_at = datetime.now(timezone.utc)
        result.is_valid = False
        
        if additional_metadata:
            result.metadata.update(additional_metadata)
        
        # Remove from escalation queue if present
        self.escalation_queue = [
            req for req in self.escalation_queue 
            if req.request_id != validation_id
        ]
        
        logger.info(f"Validation denied: {validation_id} by {denied_by}, reason: {denial_reason}")
        await self._log_denial_event(result, denied_by, denial_reason)
        
        return True
    
    async def resolve_challenge(
        self,
        challenge_id: str,
        challenge_response: Dict[str, Any],
        responder: str
    ) -> bool:
        """
        Resolve an approval challenge
        
        Args:
            challenge_id: ID of challenge to resolve
            challenge_response: Response to the challenge
            responder: Entity responding to challenge
            additional_metadata: Additional metadata
            
        Returns:
            True if challenge was resolved successfully, False otherwise
        """
        if challenge_id not in self.challenges:
            logger.warning(f"Challenge not found: {challenge_id}")
            return False
        
        challenge = self.challenges[challenge_id]
        
        # Check if challenge has expired
        if datetime.now(timezone.utc) > challenge.expires_at:
            logger.warning(f"Challenge {challenge_id} has expired")
            challenge.is_resolved = False
            return False
        
        # Check attempt limits
        challenge.attempts_used += 1
        if challenge.attempts_used > challenge.max_attempts:
            logger.warning(f"Challenge {challenge_id} exceeded max attempts")
            challenge.is_resolved = False
            return False
        
        # Validate challenge response
        is_valid = await self._validate_challenge_response(challenge, challenge_response)
        
        if is_valid:
            challenge.is_resolved = True
            
            # Update associated validation
            validation_id = challenge.validation_id
            if validation_id in self.active_validations:
                result = self.active_validations[validation_id]
                result.approval_status = ApprovalStatus.APPROVED
                result.approved_by = responder
                result.approved_at = datetime.now(timezone.utc)
                result.approval_token = self._generate_approval_token()
                
                logger.info(f"Challenge resolved successfully: {challenge_id}")
                await self._log_challenge_resolution(challenge, challenge_response, responder)
                return True
        else:
            logger.warning(f"Invalid challenge response for {challenge_id}")
        
        return False
    
    async def get_validation_status(self, validation_id: str) -> Optional[PolicyValidationResult]:
        """Get current status of a validation request"""
        return self.active_validations.get(validation_id)
    
    async def list_pending_validations(self) -> List[PolicyValidationResult]:
        """Get list of all pending validation requests"""
        return [
            result for result in self.active_validations.values()
            if result.approval_status == ApprovalStatus.PENDING
        ]
    
    async def list_escalated_validations(self) -> List[PolicyValidationRequest]:
        """Get list of validation requests requiring escalation"""
        return self.escalation_queue.copy()
    
    async def cleanup_expired_validations(self) -> int:
        """Clean up expired validations and return count of cleaned items"""
        current_time = datetime.now(timezone.utc)
        cleaned_count = 0
        
        # Clean expired active validations
        expired_validations = []
        for validation_id, result in self.active_validations.items():
            if (result.request.approval_deadline and 
                current_time > result.request.approval_deadline and
                result.approval_status == ApprovalStatus.PENDING):
                result.approval_status = ApprovalStatus.EXPIRED
                expired_validations.append(validation_id)
                cleaned_count += 1
        
        for validation_id in expired_validations:
            del self.active_validations[validation_id]
        
        # Clean expired cache entries
        expired_cache_keys = []
        for cache_key, result in self.approval_cache.items():
            if (result.expires_at and current_time > result.expires_at):
                expired_cache_keys.append(cache_key)
                cleaned_count += 1
        
        for cache_key in expired_cache_keys:
            del self.approval_cache[cache_key]
        
        # Clean expired challenges
        expired_challenges = []
        for challenge_id, challenge in self.challenges.items():
            if current_time > challenge.expires_at:
                expired_challenges.append(challenge_id)
                cleaned_count += 1
        
        for challenge_id in expired_challenges:
            del self.challenges[challenge_id]
        
        logger.info(f"Cleaned up {cleaned_count} expired validations and challenges")
        return cleaned_count
    
    async def _analyze_policy_violations(
        self,
        context: SecurityContext,
        assessment: SecurityAssessment
    ) -> List[str]:
        """Analyze and categorize policy violations"""
        violations = []
        
        # Check for unauthorized access patterns
        if context.operation in ["admin_access", "privilege_escalation"]:
            violations.append(PolicyViolationType.UNAUTHORIZED_ACCESS.value)
        
        # Check for suspicious resource access
        if context.resource_path.startswith("/system/") or context.resource_path.startswith("/admin/"):
            violations.append(PolicyViolationType.PRIVILEGE_ESCALATION.value)
        
        # Check for data access patterns
        if "data" in context.resource_path.lower() and context.operation == "read":
            violations.append(PolicyViolationType.DATA_EXFILTRATION.value)
        
        # Check for temporal violations
        current_hour = datetime.now().hour
        if current_hour < 6 or current_hour > 22:
            violations.append(PolicyViolationType.TEMPORAL_VIOLATION.value)
        
        # Add assessment violations
        violations.extend(assessment.policy_violations)
        
        return violations
    
    async def _determine_approval_requirements(
        self,
        assessment: SecurityAssessment,
        violations: List[str],
        auto_approve: bool
    ) -> Tuple[ApprovalStatus, ApprovalMethod]:
        """Determine approval requirements based on assessment and violations"""
        
        # Auto-approve high trust scenarios
        if (assessment.overall_trust_score >= JIT_APPROVAL_AUTO_APPROVE_THRESHOLD and 
            not violations and 
            assessment.risk_level in [RiskLevel.MINIMAL, RiskLevel.LOW]):
            return ApprovalStatus.AUTO_APPROVED, ApprovalMethod.AUTOMATIC
        
        # Check if escalation is required
        if (assessment.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL, RiskLevel.EXTREME] or
            any(violation in violations for violation in [
                PolicyViolationType.PRIVILEGE_ESCALATION.value,
                PolicyViolationType.UNAUTHORIZED_ACCESS.value
            ])):
            return ApprovalStatus.ESCALATED, ApprovalMethod.ESCALATION
        
        # Check if challenge is required
        if assessment.recommended_action == ActionType.CHALLENGE:
            return ApprovalStatus.CHALLENGED, ApprovalMethod.CHALLENGE_RESPONSE
        
        # Default to pending approval
        return ApprovalStatus.PENDING, ApprovalMethod.ADMIN_APPROVAL
    
    async def _create_approval_challenge(self, result: PolicyValidationResult) -> None:
        """Create an approval challenge for additional verification"""
        challenge_id = str(uuid.uuid4())
        
        # Determine challenge type based on context
        challenge_type = "knowledge_based"
        challenge_data = {
            "question": "What is the primary purpose of this operation?",
            "expected_keywords": ["development", "testing", "maintenance", "analysis"]
        }
        
        challenge = ApprovalChallenge(
            challenge_id=challenge_id,
            validation_id=result.validation_id,
            challenge_type=challenge_type,
            challenge_data=challenge_data,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
        )
        
        self.challenges[challenge_id] = challenge
        result.metadata["challenge_id"] = challenge_id
        
        logger.info(f"Created approval challenge: {challenge_id} for validation: {result.validation_id}")
    
    async def _validate_challenge_response(
        self,
        challenge: ApprovalChallenge,
        response: Dict[str, Any]
    ) -> bool:
        """Validate challenge response"""
        if challenge.challenge_type == "knowledge_based":
            answer = response.get("answer", "").lower()
            expected_keywords = challenge.challenge_data.get("expected_keywords", [])
            
            return any(keyword in answer for keyword in expected_keywords)
        
        return False
    
    async def _check_rate_limits(self, context: SecurityContext) -> bool:
        """Check rate limits for validation requests"""
        client_key = f"{context.source_ip}:{context.user_id}"
        current_time = datetime.now(timezone.utc)
        
        # Clean old attempts
        if client_key in self.validation_attempts:
            self.validation_attempts[client_key] = [
                attempt for attempt in self.validation_attempts[client_key]
                if current_time - attempt < timedelta(minutes=1)
            ]
        else:
            self.validation_attempts[client_key] = []
        
        # Check limit
        if len(self.validation_attempts[client_key]) >= self.max_validations_per_minute:
            return False
        
        # Add current attempt
        self.validation_attempts[client_key].append(current_time)
        return True
    
    def _generate_cache_key(self, context: SecurityContext) -> str:
        """Generate cache key for validation results"""
        key_data = f"{context.service_name}:{context.component_name}:{context.operation}:{context.resource_path}"
        return hashlib.sha256(key_data.encode()).hexdigest()
    
    def _is_cache_valid(self, result: PolicyValidationResult) -> bool:
        """Check if cached result is still valid"""
        if not result.expires_at:
            return False
        
        return datetime.now(timezone.utc) < result.expires_at
    
    def _generate_approval_token(self) -> str:
        """Generate secure approval token"""
        return secrets.token_urlsafe(32)
    
    async def _create_denied_result(
        self,
        request: PolicyValidationRequest,
        reason: str,
        status: ApprovalStatus
    ) -> PolicyValidationResult:
        """Create a denied validation result"""
        return PolicyValidationResult(
            validation_id=request.request_id,
            request=request,
            is_valid=False,
            approval_status=status,
            approval_method=ApprovalMethod.POLICY_BASED,
            trust_score=0.0,
            risk_level=RiskLevel.HIGH,
            violations_found=[reason],
            recommendations=[f"Request denied: {reason}"]
        )
    
    async def _log_validation_event(self, result: PolicyValidationResult) -> None:
        """Log validation event for audit trail"""
        event_data = {
            "validation_id": result.validation_id,
            "service": result.request.context.service_name,
            "component": result.request.context.component_name,
            "operation": result.request.context.operation,
            "trust_score": result.trust_score,
            "risk_level": result.risk_level.value,
            "approval_status": result.approval_status.value,
            "violations": result.violations_found,
            "timestamp": result.request.context.timestamp.isoformat()
        }
        
        logger.info(f"Policy validation event: {json.dumps(event_data)}")
    
    async def _log_approval_event(
        self,
        result: PolicyValidationResult,
        approved_by: str,
        reason: str
    ) -> None:
        """Log approval event for audit trail"""
        event_data = {
            "validation_id": result.validation_id,
            "approved_by": approved_by,
            "approval_reason": reason,
            "trust_score": result.trust_score,
            "timestamp": result.approved_at.isoformat() if result.approved_at else None
        }
        
        logger.info(f"Policy approval event: {json.dumps(event_data)}")
    
    async def _log_denial_event(
        self,
        result: PolicyValidationResult,
        denied_by: str,
        reason: str
    ) -> None:
        """Log denial event for audit trail"""
        event_data = {
            "validation_id": result.validation_id,
            "denied_by": denied_by,
            "denial_reason": reason,
            "violations": result.violations_found,
            "timestamp": result.approved_at.isoformat() if result.approved_at else None
        }
        
        logger.info(f"Policy denial event: {json.dumps(event_data)}")
    
    async def _log_challenge_resolution(
        self,
        challenge: ApprovalChallenge,
        response: Dict[str, Any],
        responder: str
    ) -> None:
        """Log challenge resolution event"""
        event_data = {
            "challenge_id": challenge.challenge_id,
            "validation_id": challenge.validation_id,
            "challenge_type": challenge.challenge_type,
            "responder": responder,
            "attempts_used": challenge.attempts_used,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Challenge resolution event: {json.dumps(event_data)}")
    
    def _initialize_default_policies(self) -> None:
        """Initialize default security policies"""
        # High-risk operation policy
        high_risk_policy = SecurityPolicy(
            policy_id="high_risk_operations",
            name="High Risk Operations Policy",
            description="Policy for high-risk operations requiring approval",
            policy_level=PolicyLevel.SYSTEM,
            condition=json.dumps({
                "operations": ["admin_access", "privilege_escalation", "system_config"],
                "trust_threshold": 0.8
            }),
            weight=0.9,
            verification_methods=[VerificationMethod.SERVICE_AUTHENTICATION, VerificationMethod.COMPONENT_VERIFICATION],
            action_on_violation=ActionType.CHALLENGE
        )
        
        # Data access policy
        data_access_policy = SecurityPolicy(
            policy_id="data_access_control",
            name="Data Access Control Policy",
            description="Policy for controlling data access",
            policy_level=PolicyLevel.SERVICE,
            condition=json.dumps({
                "resource_patterns": ["/data/*", "/user/*", "/system/*"],
                "trust_threshold": 0.7
            }),
            weight=0.8,
            verification_methods=[VerificationMethod.RESOURCE_VALIDATION, VerificationMethod.BEHAVIORAL_ANALYSIS],
            action_on_violation=ActionType.CHALLENGE
        )
        
        self.policy_cache[high_risk_policy.policy_id] = high_risk_policy
        self.policy_cache[data_access_policy.policy_id] = data_access_policy
        
        logger.info("Default security policies initialized")


# Global policy validator instance
_policy_validator: Optional[PolicyValidator] = None


def get_policy_validator() -> Optional[PolicyValidator]:
    """Get global policy validator instance"""
    return _policy_validator


def create_policy_validator(trust_engine: Optional[TrustNothingEngine] = None) -> PolicyValidator:
    """Create new policy validator instance"""
    global _policy_validator
    _policy_validator = PolicyValidator(trust_engine)
    return _policy_validator


async def main():
    """Main function for testing"""
    # Initialize policy validator
    validator = create_policy_validator()
    
    # Create test context
    context = SecurityContext(
        request_id="test-request-001",
        service_name="test_service",
        component_name="test_component",
        operation="admin_access",
        resource_path="/system/admin",
        user_id="test_user"
    )
    
    # Test validation
    result = await validator.validate_policy(context, TrustLevel.HIGH)
    print(f"Validation result: {result.approval_status.value}")
    print(f"Trust score: {result.trust_score}")
    print(f"Violations: {result.violations_found}")


if __name__ == "__main__":
    asyncio.run(main())
