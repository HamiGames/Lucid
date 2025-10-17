"""
Trust Policy Data Models

Pydantic models for trust policy entities in the Lucid system.
Handles trust policies, rules, and trust relationships.

Database Collection: trust_policies
Phase: Phase 1 - Foundation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class TrustLevel(str, Enum):
    """Trust level enumeration"""
    UNTRUSTED = "untrusted"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"


class PolicyType(str, Enum):
    """Policy type enumeration"""
    USER_TRUST = "user_trust"
    NODE_TRUST = "node_trust"
    SESSION_POLICY = "session_policy"
    CONTENT_POLICY = "content_policy"
    NETWORK_POLICY = "network_policy"


class PolicyStatus(str, Enum):
    """Policy status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    EXPIRED = "expired"


class TrustRule(BaseModel):
    """Trust rule definition"""
    rule_id: str = Field(..., description="Unique rule identifier")
    rule_type: str = Field(..., description="Type of trust rule")
    condition: Dict[str, Any] = Field(..., description="Rule condition specification")
    action: str = Field(..., description="Action to take when rule matches")
    priority: int = Field(default=0, description="Rule priority (higher = higher priority)")
    enabled: bool = Field(default=True, description="Whether rule is enabled")


class TrustScore(BaseModel):
    """Trust score information"""
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Overall trust score (0-100)")
    components: Dict[str, float] = Field(default_factory=dict, description="Trust score components")
    last_updated: datetime = Field(..., description="Last score update timestamp")
    calculation_method: str = Field(..., description="Score calculation method")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class TrustPolicyBase(BaseModel):
    """Base trust policy model with common fields"""
    policy_name: str = Field(..., min_length=1, max_length=200, description="Policy name")
    policy_type: PolicyType = Field(..., description="Policy type")
    trust_level: TrustLevel = Field(default=TrustLevel.MEDIUM, description="Trust level")
    status: PolicyStatus = Field(default=PolicyStatus.ACTIVE, description="Policy status")
    
    class Config:
        use_enum_values = True


class TrustPolicyCreate(TrustPolicyBase):
    """Model for creating a new trust policy"""
    description: Optional[str] = Field(None, max_length=1000, description="Policy description")
    rules: List[TrustRule] = Field(default_factory=list, description="Policy rules")
    scope: Dict[str, Any] = Field(..., description="Policy scope (users, nodes, sessions)")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Policy parameters")


class TrustPolicyUpdate(BaseModel):
    """Model for updating trust policy"""
    policy_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    trust_level: Optional[TrustLevel] = None
    status: Optional[PolicyStatus] = None
    rules: Optional[List[TrustRule]] = None
    parameters: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True


class TrustPolicy(TrustPolicyBase):
    """Trust policy model for API responses"""
    policy_id: str = Field(..., description="Unique policy identifier")
    
    # Policy details
    description: Optional[str] = Field(None, description="Policy description")
    version: int = Field(default=1, description="Policy version")
    
    # Policy rules
    rules: List[TrustRule] = Field(default_factory=list, description="Policy rules")
    rule_count: int = Field(default=0, ge=0, description="Number of rules")
    
    # Policy scope
    scope: Dict[str, Any] = Field(..., description="Policy scope specification")
    applies_to_users: bool = Field(default=False, description="Whether policy applies to users")
    applies_to_nodes: bool = Field(default=False, description="Whether policy applies to nodes")
    applies_to_sessions: bool = Field(default=False, description="Whether policy applies to sessions")
    
    # Policy parameters
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Policy parameters")
    
    # Enforcement
    enforcement_level: str = Field(default="strict", description="Enforcement level (strict, moderate, lenient)")
    auto_remediation: bool = Field(default=False, description="Whether to auto-remediate violations")
    
    # Statistics
    applications_count: int = Field(default=0, ge=0, description="Number of times applied")
    violations_count: int = Field(default=0, ge=0, description="Number of violations detected")
    last_applied: Optional[datetime] = Field(None, description="Last application timestamp")
    
    # Ownership and permissions
    created_by: str = Field(..., description="User ID that created policy")
    owner_id: str = Field(..., description="Policy owner ID")
    is_system_policy: bool = Field(default=False, description="Whether this is a system policy")
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    effective_from: Optional[datetime] = Field(None, description="Policy effective start date")
    effective_until: Optional[datetime] = Field(None, description="Policy expiration date")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tags: List[str] = Field(default_factory=list, description="Policy tags")
    
    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class TrustPolicyInDB(TrustPolicy):
    """Trust policy model as stored in database (includes internal fields)"""
    
    # Internal processing fields
    compiled_rules: Optional[bytes] = Field(None, description="Compiled rules (binary)")
    rule_cache: Optional[Dict[str, Any]] = Field(None, description="Rule evaluation cache")
    
    # Performance metrics
    avg_evaluation_time_ms: Optional[float] = Field(None, description="Average evaluation time")
    total_evaluations: int = Field(default=0, description="Total number of evaluations")
    
    # Audit fields
    updated_by: Optional[str] = Field(None, description="User ID that last updated policy")
    deleted_at: Optional[datetime] = Field(None, description="Soft delete timestamp")
    version_history: List[Dict[str, Any]] = Field(default_factory=list, description="Version history")
    
    class Config:
        orm_mode = True
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class TrustRelationship(BaseModel):
    """Trust relationship between entities"""
    relationship_id: str = Field(..., description="Unique relationship identifier")
    subject_type: str = Field(..., description="Subject type (user, node)")
    subject_id: str = Field(..., description="Subject identifier")
    target_type: str = Field(..., description="Target type (user, node)")
    target_id: str = Field(..., description="Target identifier")
    
    # Trust information
    trust_level: TrustLevel = Field(..., description="Trust level")
    trust_score: Optional[TrustScore] = Field(None, description="Trust score details")
    
    # Relationship details
    relationship_type: str = Field(..., description="Type of relationship")
    bidirectional: bool = Field(default=False, description="Whether trust is bidirectional")
    
    # Timestamps
    established_at: datetime = Field(..., description="Relationship establishment timestamp")
    last_verified: Optional[datetime] = Field(None, description="Last verification timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class PolicyViolation(BaseModel):
    """Policy violation record"""
    violation_id: str = Field(..., description="Unique violation identifier")
    policy_id: str = Field(..., description="Policy that was violated")
    violator_type: str = Field(..., description="Violator type (user, node, session)")
    violator_id: str = Field(..., description="Violator identifier")
    
    # Violation details
    violation_type: str = Field(..., description="Type of violation")
    severity: str = Field(..., description="Violation severity (low, medium, high, critical)")
    description: str = Field(..., description="Violation description")
    
    # Rule information
    violated_rule_id: Optional[str] = Field(None, description="Specific rule that was violated")
    violation_data: Dict[str, Any] = Field(..., description="Violation data and context")
    
    # Actions taken
    action_taken: Optional[str] = Field(None, description="Action taken in response")
    auto_remediated: bool = Field(default=False, description="Whether auto-remediation was applied")
    
    # Timestamps
    occurred_at: datetime = Field(..., description="Violation occurrence timestamp")
    detected_at: datetime = Field(..., description="Detection timestamp")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    
    # Resolution
    resolved: bool = Field(default=False, description="Whether violation is resolved")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class PolicyStatistics(BaseModel):
    """Trust policy statistics"""
    policy_id: str = Field(..., description="Policy identifier")
    
    # Application metrics
    total_applications: int = Field(..., description="Total number of applications")
    applications_last_24h: int = Field(..., description="Applications in last 24 hours")
    applications_last_7d: int = Field(..., description="Applications in last 7 days")
    
    # Violation metrics
    total_violations: int = Field(..., description="Total violations detected")
    violations_last_24h: int = Field(..., description="Violations in last 24 hours")
    violations_last_7d: int = Field(..., description="Violations in last 7 days")
    violation_rate: float = Field(..., description="Violation rate (percentage)")
    
    # Performance metrics
    avg_evaluation_time_ms: float = Field(..., description="Average evaluation time")
    max_evaluation_time_ms: float = Field(..., description="Maximum evaluation time")
    
    # Effectiveness metrics
    auto_remediation_rate: float = Field(..., description="Auto-remediation success rate")
    false_positive_rate: Optional[float] = Field(None, description="False positive rate")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

