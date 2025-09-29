# Path: open-api/api/app/routes/trust_policy.py
# Lucid RDP Trust-Nothing Policy API Blueprint
# Implements zero-trust security policies and compliance verification

from __future__ import annotations

import logging
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Literal
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, Header
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, validator

# Import from our components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trust-policy", tags=["trust-policy"])
security = HTTPBearer()

# Enums
class TrustLevel(str, Enum):
    UNTRUSTED = "untrusted"
    BASIC = "basic"
    VERIFIED = "verified"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class PolicyViolationType(str, Enum):
    AUTHENTICATION_FAILURE = "authentication_failure"
    ENCRYPTION_VIOLATION = "encryption_violation"
    DATA_INTEGRITY_BREACH = "data_integrity_breach"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    COMPLIANCE_VIOLATION = "compliance_violation"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_BEHAVIOR = "suspicious_behavior"

class ComplianceStandard(str, Enum):
    GDPR = "gdpr"
    CCPA = "ccpa"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"

# Pydantic Models
class ZeroTrustVerification(BaseModel):
    """Zero-trust verification request"""
    entity_id: str = Field(..., description="Entity identifier (user, node, session)")
    entity_type: str = Field(..., enum=["user", "node", "session", "api_client"])
    verification_data: Dict[str, Any] = Field(..., description="Verification payload")
    context: Dict[str, str] = Field(..., description="Request context (IP, User-Agent, etc.)")
    requested_permissions: List[str] = Field(..., description="Requested access permissions")

class TrustScore(BaseModel):
    """Trust score calculation result"""
    entity_id: str
    entity_type: str
    trust_level: TrustLevel
    numeric_score: float = Field(..., ge=0, le=100, description="Numeric trust score (0-100)")
    factors: Dict[str, float] = Field(..., description="Contributing trust factors")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = Field(..., description="Trust score expiration")
    risk_indicators: List[str] = Field(default_factory=list, description="Identified risk factors")

class PolicyViolation(BaseModel):
    """Security policy violation record"""
    violation_id: str = Field(..., description="Unique violation identifier")
    entity_id: str = Field(..., description="Entity that violated policy")
    violation_type: PolicyViolationType
    severity: str = Field(..., enum=["low", "medium", "high", "critical"])
    description: str = Field(..., description="Violation description")
    evidence: Dict[str, Any] = Field(..., description="Evidence of violation")
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = Field(default=False)
    resolution_notes: Optional[str] = Field(None, description="Resolution details")

class ComplianceCheck(BaseModel):
    """Compliance verification check"""
    check_id: str = Field(..., description="Compliance check identifier")
    standard: ComplianceStandard
    entity_id: str = Field(..., description="Entity being checked")
    check_type: str = Field(..., description="Type of compliance check")
    status: str = Field(..., enum=["pending", "passed", "failed", "warning"])
    details: Dict[str, Any] = Field(..., description="Check details and results")
    performed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(None, description="Check validity expiration")

class EncryptionPolicy(BaseModel):
    """Encryption policy requirements"""
    policy_id: str = Field(..., description="Policy identifier")
    entity_type: str = Field(..., description="Applicable entity type")
    minimum_key_length: int = Field(..., ge=256, description="Minimum encryption key length")
    allowed_algorithms: List[str] = Field(..., description="Allowed encryption algorithms")
    key_rotation_interval: int = Field(..., description="Key rotation interval in days")
    enforce_perfect_forward_secrecy: bool = Field(default=True)
    require_hardware_security_module: bool = Field(default=False)

class AccessRequest(BaseModel):
    """Access request for zero-trust evaluation"""
    request_id: str = Field(..., description="Request identifier")
    entity_id: str = Field(..., description="Requesting entity")
    resource_path: str = Field(..., description="Requested resource path")
    action: str = Field(..., description="Requested action (read, write, delete, etc.)")
    context: Dict[str, Any] = Field(..., description="Request context")
    justification: Optional[str] = Field(None, description="Access justification")

class AccessDecision(BaseModel):
    """Zero-trust access decision"""
    request_id: str
    decision: str = Field(..., enum=["allow", "deny", "conditional"])
    trust_score_required: float = Field(..., ge=0, le=100)
    conditions: List[str] = Field(default_factory=list, description="Access conditions")
    expires_at: datetime = Field(..., description="Decision validity expiration")
    reasoning: Dict[str, Any] = Field(..., description="Decision reasoning")
    monitoring_required: bool = Field(default=True, description="Whether access should be monitored")

class AuditLog(BaseModel):
    """Security audit log entry"""
    log_id: str = Field(..., description="Log entry identifier")
    entity_id: str = Field(..., description="Entity performing action")
    action: str = Field(..., description="Action performed")
    resource: str = Field(..., description="Resource accessed")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = Field(..., description="Action success status")
    ip_address: str = Field(..., description="Source IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ThreatIntelligence(BaseModel):
    """Threat intelligence data"""
    threat_id: str = Field(..., description="Threat identifier")
    threat_type: str = Field(..., description="Type of threat")
    indicators: Dict[str, List[str]] = Field(..., description="Threat indicators (IPs, domains, etc.)")
    severity: str = Field(..., enum=["low", "medium", "high", "critical"])
    description: str = Field(..., description="Threat description")
    first_seen: datetime = Field(..., description="First detection timestamp")
    last_seen: datetime = Field(..., description="Last seen timestamp")
    confidence: float = Field(..., ge=0, le=1, description="Confidence level (0-1)")

# Global policy storage
trust_scores: Dict[str, TrustScore] = {}
policy_violations: Dict[str, PolicyViolation] = {}
compliance_checks: Dict[str, ComplianceCheck] = {}
audit_logs: List[AuditLog] = []

@router.post("/verify-zero-trust", response_model=TrustScore)
async def verify_zero_trust(
    verification: ZeroTrustVerification,
    token: str = Depends(security)
) -> TrustScore:
    """
    Perform zero-trust verification and calculate trust score.
    
    Evaluates entity trustworthiness based on multiple factors.
    """
    try:
        logger.info(f"Zero-trust verification for {verification.entity_type}: {verification.entity_id}")
        
        # Calculate trust factors
        trust_factors = {}
        numeric_score = 50.0  # Base score
        risk_indicators = []
        
        # Authentication factor
        auth_strength = verification.verification_data.get("auth_strength", 0.5)
        trust_factors["authentication"] = auth_strength * 25
        numeric_score += trust_factors["authentication"]
        
        # Device/Context factor
        known_device = verification.context.get("device_fingerprint") in ["known_device_1", "known_device_2"]
        trust_factors["device_context"] = 15 if known_device else 5
        numeric_score += trust_factors["device_context"]
        
        # Historical behavior factor
        behavior_score = verification.verification_data.get("behavior_score", 0.7)
        trust_factors["behavior"] = behavior_score * 20
        numeric_score += trust_factors["behavior"]
        
        # Network security factor
        secure_network = verification.context.get("network_security", "unknown") == "secure"
        trust_factors["network"] = 10 if secure_network else -5
        numeric_score += trust_factors["network"]
        
        # Check for risk indicators
        suspicious_ip = verification.context.get("ip_address", "").startswith("192.168.")
        if suspicious_ip:
            risk_indicators.append("suspicious_ip_range")
        
        unusual_location = verification.context.get("location") != verification.verification_data.get("usual_location")
        if unusual_location:
            risk_indicators.append("unusual_location")
            numeric_score -= 10
        
        # Determine trust level
        if numeric_score >= 85:
            trust_level = TrustLevel.ENTERPRISE
        elif numeric_score >= 70:
            trust_level = TrustLevel.PREMIUM
        elif numeric_score >= 55:
            trust_level = TrustLevel.VERIFIED
        elif numeric_score >= 35:
            trust_level = TrustLevel.BASIC
        else:
            trust_level = TrustLevel.UNTRUSTED
        
        # Create trust score
        trust_score = TrustScore(
            entity_id=verification.entity_id,
            entity_type=verification.entity_type,
            trust_level=trust_level,
            numeric_score=min(max(numeric_score, 0), 100),
            factors=trust_factors,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            risk_indicators=risk_indicators
        )
        
        # Store trust score
        trust_scores[verification.entity_id] = trust_score
        
        logger.info(f"Trust score calculated: {verification.entity_id} -> {trust_level} ({numeric_score:.1f})")
        return trust_score
        
    except Exception as e:
        logger.error(f"Zero-trust verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Zero-trust verification failed: {str(e)}"
        )

@router.post("/access-request", response_model=AccessDecision)
async def evaluate_access_request(
    access_request: AccessRequest,
    token: str = Depends(security)
) -> AccessDecision:
    """Evaluate access request using zero-trust principles"""
    try:
        logger.info(f"Evaluating access request: {access_request.request_id}")
        
        # Get entity trust score
        entity_trust = trust_scores.get(access_request.entity_id)
        if not entity_trust:
            # Default untrusted score
            required_score = 30.0
            decision = "deny"
            conditions = ["trust_verification_required"]
            reasoning = {"error": "No trust score found for entity"}
        else:
            # Determine required trust score based on resource sensitivity
            if "/admin/" in access_request.resource_path:
                required_score = 80.0
            elif "/sensitive/" in access_request.resource_path:
                required_score = 65.0
            elif access_request.action in ["delete", "modify"]:
                required_score = 55.0
            else:
                required_score = 35.0
            
            # Make access decision
            if entity_trust.numeric_score >= required_score:
                decision = "allow"
                conditions = []
                if entity_trust.risk_indicators:
                    decision = "conditional"
                    conditions = ["enhanced_monitoring", "session_recording"]
            else:
                decision = "deny"
                conditions = ["insufficient_trust_score", "additional_verification_required"]
            
            reasoning = {
                "trust_score": entity_trust.numeric_score,
                "required_score": required_score,
                "risk_indicators": entity_trust.risk_indicators,
                "trust_level": entity_trust.trust_level
            }
        
        access_decision = AccessDecision(
            request_id=access_request.request_id,
            decision=decision,
            trust_score_required=required_score,
            conditions=conditions,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
            reasoning=reasoning,
            monitoring_required=decision in ["allow", "conditional"]
        )
        
        logger.info(f"Access decision: {access_request.request_id} -> {decision}")
        return access_decision
        
    except Exception as e:
        logger.error(f"Access request evaluation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Access request evaluation failed: {str(e)}"
        )

@router.post("/report-violation", response_model=PolicyViolation)
async def report_policy_violation(
    entity_id: str = Body(..., description="Entity that violated policy"),
    violation_type: PolicyViolationType = Body(..., description="Type of violation"),
    severity: str = Body(..., enum=["low", "medium", "high", "critical"]),
    description: str = Body(..., description="Violation description"),
    evidence: Dict[str, Any] = Body(..., description="Evidence of violation"),
    token: str = Depends(security)
) -> PolicyViolation:
    """Report a security policy violation"""
    try:
        violation_id = hashlib.sha256(f"{entity_id}_{violation_type}_{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:16]
        
        violation = PolicyViolation(
            violation_id=violation_id,
            entity_id=entity_id,
            violation_type=violation_type,
            severity=severity,
            description=description,
            evidence=evidence
        )
        
        # Store violation
        policy_violations[violation_id] = violation
        
        # Adjust trust score if entity exists
        if entity_id in trust_scores:
            penalty = {"low": 5, "medium": 15, "high": 30, "critical": 50}[severity]
            trust_scores[entity_id].numeric_score = max(0, trust_scores[entity_id].numeric_score - penalty)
            trust_scores[entity_id].risk_indicators.append(f"policy_violation_{violation_type}")
        
        logger.warning(f"Policy violation reported: {violation_id} - {entity_id} ({violation_type})")
        return violation
        
    except Exception as e:
        logger.error(f"Policy violation reporting failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Policy violation reporting failed: {str(e)}"
        )

@router.post("/compliance-check", response_model=ComplianceCheck)
async def perform_compliance_check(
    entity_id: str = Body(..., description="Entity to check"),
    standard: ComplianceStandard = Body(..., description="Compliance standard"),
    check_type: str = Body(..., description="Type of check to perform"),
    token: str = Depends(security)
) -> ComplianceCheck:
    """Perform compliance verification check"""
    try:
        check_id = f"check_{secrets.token_hex(8)}"
        logger.info(f"Performing compliance check: {check_id} - {standard} for {entity_id}")
        
        # Simulate compliance check based on standard
        check_results = {}
        status_result = "passed"
        
        if standard == ComplianceStandard.GDPR:
            check_results = {
                "data_encryption": True,
                "consent_management": True,
                "right_to_erasure": True,
                "data_portability": True,
                "privacy_by_design": True
            }
        elif standard == ComplianceStandard.SOC2:
            check_results = {
                "security": True,
                "availability": True,
                "processing_integrity": True,
                "confidentiality": True,
                "privacy": True
            }
        elif standard == ComplianceStandard.ISO27001:
            check_results = {
                "information_security_policy": True,
                "risk_management": True,
                "asset_management": True,
                "access_control": True,
                "incident_management": True
            }
        
        # Check for any failures
        if not all(check_results.values()):
            status_result = "failed"
        elif len(check_results) < 3:  # Insufficient checks
            status_result = "warning"
        
        compliance_check = ComplianceCheck(
            check_id=check_id,
            standard=standard,
            entity_id=entity_id,
            check_type=check_type,
            status=status_result,
            details=check_results,
            expires_at=datetime.now(timezone.utc) + timedelta(days=90)
        )
        
        # Store compliance check
        compliance_checks[check_id] = compliance_check
        
        logger.info(f"Compliance check completed: {check_id} -> {status_result}")
        return compliance_check
        
    except Exception as e:
        logger.error(f"Compliance check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compliance check failed: {str(e)}"
        )

@router.get("/trust-score/{entity_id}", response_model=TrustScore)
async def get_trust_score(
    entity_id: str,
    token: str = Depends(security)
) -> TrustScore:
    """Get current trust score for entity"""
    try:
        trust_score = trust_scores.get(entity_id)
        if not trust_score:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trust score not found for entity: {entity_id}"
            )
        
        # Check if score is expired
        if trust_score.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Trust score has expired, re-verification required"
            )
        
        return trust_score
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trust score: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve trust score: {str(e)}"
        )

@router.get("/violations", response_model=List[PolicyViolation])
async def list_policy_violations(
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    violation_type: Optional[PolicyViolationType] = Query(None, description="Filter by violation type"),
    severity: Optional[str] = Query(None, enum=["low", "medium", "high", "critical"]),
    resolved: Optional[bool] = Query(None, description="Filter by resolution status"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
    token: str = Depends(security)
) -> List[PolicyViolation]:
    """List policy violations with optional filters"""
    try:
        violations = list(policy_violations.values())
        
        # Apply filters
        if entity_id:
            violations = [v for v in violations if v.entity_id == entity_id]
        if violation_type:
            violations = [v for v in violations if v.violation_type == violation_type]
        if severity:
            violations = [v for v in violations if v.severity == severity]
        if resolved is not None:
            violations = [v for v in violations if v.resolved == resolved]
        
        # Sort by detection time (newest first)
        violations.sort(key=lambda v: v.detected_at, reverse=True)
        
        return violations[:limit]
        
    except Exception as e:
        logger.error(f"Failed to list violations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list violations: {str(e)}"
        )

@router.post("/audit-log", response_model=AuditLog)
async def create_audit_log(
    entity_id: str = Body(..., description="Entity performing action"),
    action: str = Body(..., description="Action performed"),
    resource: str = Body(..., description="Resource accessed"),
    success: bool = Body(..., description="Action success status"),
    ip_address: str = Body(..., description="Source IP address"),
    user_agent: Optional[str] = Body(None, description="User agent string"),
    metadata: Dict[str, Any] = Body(default_factory=dict, description="Additional metadata"),
    token: str = Depends(security)
) -> AuditLog:
    """Create security audit log entry"""
    try:
        log_id = f"log_{secrets.token_hex(12)}"
        
        audit_log = AuditLog(
            log_id=log_id,
            entity_id=entity_id,
            action=action,
            resource=resource,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata
        )
        
        # Store audit log
        audit_logs.append(audit_log)
        
        logger.info(f"Audit log created: {log_id} - {entity_id} {action} {resource}")
        return audit_log
        
    except Exception as e:
        logger.error(f"Audit log creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit log creation failed: {str(e)}"
        )

@router.get("/encryption-policy/{entity_type}", response_model=EncryptionPolicy)
async def get_encryption_policy(
    entity_type: str,
    token: str = Depends(security)
) -> EncryptionPolicy:
    """Get encryption policy for entity type"""
    try:
        # Define encryption policies by entity type
        policies = {
            "user": EncryptionPolicy(
                policy_id="enc_user_001",
                entity_type="user",
                minimum_key_length=256,
                allowed_algorithms=["AES-256-GCM", "ChaCha20-Poly1305"],
                key_rotation_interval=90,
                enforce_perfect_forward_secrecy=True,
                require_hardware_security_module=False
            ),
            "node": EncryptionPolicy(
                policy_id="enc_node_001",
                entity_type="node",
                minimum_key_length=384,
                allowed_algorithms=["AES-256-GCM", "ChaCha20-Poly1305", "AES-256-CBC"],
                key_rotation_interval=30,
                enforce_perfect_forward_secrecy=True,
                require_hardware_security_module=True
            ),
            "session": EncryptionPolicy(
                policy_id="enc_session_001",
                entity_type="session",
                minimum_key_length=256,
                allowed_algorithms=["ChaCha20-Poly1305"],
                key_rotation_interval=1,  # Daily rotation
                enforce_perfect_forward_secrecy=True,
                require_hardware_security_module=False
            )
        }
        
        policy = policies.get(entity_type)
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Encryption policy not found for entity type: {entity_type}"
            )
        
        return policy
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get encryption policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve encryption policy: {str(e)}"
        )

@router.get("/threat-intelligence", response_model=List[ThreatIntelligence])
async def get_threat_intelligence(
    threat_type: Optional[str] = Query(None, description="Filter by threat type"),
    severity: Optional[str] = Query(None, enum=["low", "medium", "high", "critical"]),
    active_only: bool = Query(True, description="Only return active threats"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    token: str = Depends(security)
) -> List[ThreatIntelligence]:
    """Get current threat intelligence data"""
    try:
        # Mock threat intelligence data
        threats = [
            ThreatIntelligence(
                threat_id="threat_001",
                threat_type="malicious_ip",
                indicators={"ips": ["192.168.1.100", "10.0.0.50"], "domains": []},
                severity="high",
                description="Known botnet command and control IPs",
                first_seen=datetime.now(timezone.utc) - timedelta(days=5),
                last_seen=datetime.now(timezone.utc) - timedelta(hours=2),
                confidence=0.95
            ),
            ThreatIntelligence(
                threat_id="threat_002",
                threat_type="phishing_domain",
                indicators={"ips": [], "domains": ["malicious-site.com", "fake-bank.net"]},
                severity="medium",
                description="Phishing domains targeting financial institutions",
                first_seen=datetime.now(timezone.utc) - timedelta(days=10),
                last_seen=datetime.now(timezone.utc) - timedelta(hours=6),
                confidence=0.87
            )
        ]
        
        # Apply filters
        if threat_type:
            threats = [t for t in threats if t.threat_type == threat_type]
        if severity:
            threats = [t for t in threats if t.severity == severity]
        if active_only:
            # Consider threats active if seen within last 24 hours
            cutoff = datetime.now(timezone.utc) - timedelta(days=1)
            threats = [t for t in threats if t.last_seen > cutoff]
        
        # Sort by severity and recency
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        threats.sort(key=lambda t: (severity_order.get(t.severity, 0), t.last_seen), reverse=True)
        
        return threats[:limit]
        
    except Exception as e:
        logger.error(f"Failed to get threat intelligence: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve threat intelligence: {str(e)}"
        )

@router.post("/violations/{violation_id}/resolve", response_model=PolicyViolation)
async def resolve_policy_violation(
    violation_id: str,
    resolution_notes: str = Body(..., description="Resolution details"),
    token: str = Depends(security)
) -> PolicyViolation:
    """Resolve a policy violation"""
    try:
        violation = policy_violations.get(violation_id)
        if not violation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy violation not found: {violation_id}"
            )
        
        violation.resolved = True
        violation.resolution_notes = resolution_notes
        
        logger.info(f"Policy violation resolved: {violation_id}")
        return violation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve violation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve violation: {str(e)}"
        )

# Health check endpoint
@router.get("/health", include_in_schema=False)
async def trust_policy_health() -> Dict[str, Any]:
    """Trust policy service health check"""
    return {
        "service": "trust-policy",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "zero_trust_engine": "operational",
            "compliance_checker": "operational",
            "threat_intelligence": "operational",
            "audit_logger": "operational",
            "policy_enforcer": "operational"
        },
        "statistics": {
            "active_trust_scores": len([t for t in trust_scores.values() if t.expires_at > datetime.now(timezone.utc)]),
            "unresolved_violations": len([v for v in policy_violations.values() if not v.resolved]),
            "compliance_checks_today": len([c for c in compliance_checks.values() if c.performed_at.date() == datetime.now(timezone.utc).date()]),
            "audit_logs_today": len([l for l in audit_logs if l.timestamp.date() == datetime.now(timezone.utc).date()])
        }
    }