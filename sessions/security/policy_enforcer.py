# Path: sessions/security/policy_enforcer.py
# LUCID Trust-Nothing Policy Enforcement - Security Policy Engine
# Professional trust-nothing policy enforcement for session security
# Multi-platform support for ARM64 Pi and AMD64 development

from __future__ import annotations

import asyncio
import logging
import os
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid
import re

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
import blake3

logger = logging.getLogger(__name__)

# Configuration from environment
POLICY_PATH = Path(os.getenv("POLICY_PATH", "/data/policies"))
POLICY_CACHE_SIZE = int(os.getenv("POLICY_CACHE_SIZE", "1000"))
POLICY_CACHE_TTL = int(os.getenv("POLICY_CACHE_TTL", "3600"))  # 1 hour


class PolicyType(Enum):
    """Types of security policies"""
    ACCESS_CONTROL = "access_control"
    DATA_PROTECTION = "data_protection"
    ENCRYPTION = "encryption"
    NETWORK = "network"
    RESOURCE = "resource"
    SESSION = "session"
    COMPLIANCE = "compliance"
    AUDIT = "audit"


class PolicyAction(Enum):
    """Policy enforcement actions"""
    ALLOW = "allow"
    DENY = "deny"
    QUARANTINE = "quarantine"
    LOG = "log"
    ALERT = "alert"
    BLOCK = "block"
    REDIRECT = "redirect"


class PolicySeverity(Enum):
    """Policy violation severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PolicyStatus(Enum):
    """Policy status states"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    DEPRECATED = "deprecated"
    ERROR = "error"


@dataclass
class PolicyRule:
    """Individual policy rule definition"""
    rule_id: str
    policy_type: PolicyType
    name: str
    description: str
    condition: str  # JSONPath or regex expression
    action: PolicyAction
    severity: PolicySeverity
    priority: int = 0
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyViolation:
    """Policy violation record"""
    violation_id: str
    session_id: str
    rule_id: str
    policy_type: PolicyType
    severity: PolicySeverity
    timestamp: datetime
    actor_identity: str
    actor_type: str
    resource_accessed: Optional[str] = None
    action_attempted: Optional[str] = None
    violation_data: Dict[str, Any] = field(default_factory=dict)
    enforcement_action: PolicyAction = PolicyAction.DENY
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyContext:
    """Context for policy evaluation"""
    session_id: str
    actor_identity: str
    actor_type: str
    resource_type: str
    resource_path: Optional[str] = None
    action: str = "access"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    session_data: Dict[str, Any] = field(default_factory=dict)
    environment_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyEvaluationResult:
    """Result of policy evaluation"""
    allowed: bool
    action: PolicyAction
    severity: PolicySeverity
    violation_id: Optional[str] = None
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class TrustNothingPolicyEnforcer:
    """
    Trust-nothing policy enforcement engine for Lucid RDP sessions.
    
    Implements comprehensive security policies with real-time enforcement,
    violation tracking, and compliance monitoring.
    """
    
    def __init__(self):
        """Initialize policy enforcer"""
        # Policy storage
        self.policies: Dict[str, PolicyRule] = {}
        self.policy_cache: Dict[str, Any] = {}
        self.violations: List[PolicyViolation] = []
        
        # Enforcement callbacks
        self.enforcement_callbacks: List[Callable] = []
        self.violation_callbacks: List[Callable] = []
        
        # Statistics
        self.evaluation_stats = {
            "total_evaluations": 0,
            "allowed_actions": 0,
            "denied_actions": 0,
            "violations": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Create directories
        self._create_directories()
        
        # Load default policies
        self._load_default_policies()
        
        logger.info("Trust-nothing policy enforcer initialized")
    
    def _create_directories(self) -> None:
        """Create required directories"""
        POLICY_PATH.mkdir(parents=True, exist_ok=True)
        (POLICY_PATH / "rules").mkdir(exist_ok=True)
        (POLICY_PATH / "violations").mkdir(exist_ok=True)
        logger.info(f"Created policy directories: {POLICY_PATH}")
    
    def _load_default_policies(self) -> None:
        """Load default security policies"""
        try:
            # Default access control policies
            self.add_policy_rule(PolicyRule(
                rule_id="default_deny_all",
                policy_type=PolicyType.ACCESS_CONTROL,
                name="Default Deny All",
                description="Deny all access by default unless explicitly allowed",
                condition="true",
                action=PolicyAction.DENY,
                severity=PolicySeverity.HIGH,
                priority=1000
            ))
            
            # Session security policies
            self.add_policy_rule(PolicyRule(
                rule_id="session_timeout",
                policy_type=PolicyType.SESSION,
                name="Session Timeout",
                description="Enforce session timeout limits",
                condition="session_duration > 28800",  # 8 hours
                action=PolicyAction.DENY,
                severity=PolicySeverity.MEDIUM,
                priority=100
            ))
            
            # Data protection policies
            self.add_policy_rule(PolicyRule(
                rule_id="sensitive_data_access",
                policy_type=PolicyType.DATA_PROTECTION,
                name="Sensitive Data Access",
                description="Monitor access to sensitive data",
                condition="resource_path matches '.*/(passwd|shadow|sam|security).*'",
                action=PolicyAction.LOG,
                severity=PolicySeverity.HIGH,
                priority=200
            ))
            
            # Network security policies
            self.add_policy_rule(PolicyRule(
                rule_id="blocked_ports",
                policy_type=PolicyType.NETWORK,
                name="Blocked Ports",
                description="Block access to dangerous ports",
                condition="port in [22, 23, 135, 139, 445, 1433, 3389]",
                action=PolicyAction.DENY,
                severity=PolicySeverity.HIGH,
                priority=300
            ))
            
            # Resource access policies
            self.add_policy_rule(PolicyRule(
                rule_id="system_files",
                policy_type=PolicyType.RESOURCE,
                name="System Files Protection",
                description="Protect critical system files",
                condition="resource_path matches '.*/(system32|bin|sbin|etc).*'",
                action=PolicyAction.LOG,
                severity=PolicySeverity.MEDIUM,
                priority=400
            ))
            
            logger.info("Loaded default security policies")
            
        except Exception as e:
            logger.error(f"Failed to load default policies: {e}")
    
    def add_policy_rule(self, rule: PolicyRule) -> bool:
        """Add a new policy rule"""
        try:
            # Validate rule
            if not self._validate_rule(rule):
                logger.error(f"Invalid policy rule: {rule.rule_id}")
                return False
            
            # Store rule
            self.policies[rule.rule_id] = rule
            
            # Save to disk
            self._save_policy_rule(rule)
            
            # Clear cache for this policy type
            self._clear_cache_for_policy_type(rule.policy_type)
            
            logger.info(f"Added policy rule: {rule.rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add policy rule: {e}")
            return False
    
    def remove_policy_rule(self, rule_id: str) -> bool:
        """Remove a policy rule"""
        try:
            if rule_id in self.policies:
                rule = self.policies[rule_id]
                del self.policies[rule_id]
                
                # Remove from disk
                self._remove_policy_rule_file(rule_id)
                
                # Clear cache
                self._clear_cache_for_policy_type(rule.policy_type)
                
                logger.info(f"Removed policy rule: {rule_id}")
                return True
            else:
                logger.warning(f"Policy rule not found: {rule_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove policy rule: {e}")
            return False
    
    def update_policy_rule(self, rule: PolicyRule) -> bool:
        """Update an existing policy rule"""
        try:
            if rule.rule_id not in self.policies:
                logger.error(f"Policy rule not found: {rule.rule_id}")
                return False
            
            # Validate rule
            if not self._validate_rule(rule):
                logger.error(f"Invalid policy rule: {rule.rule_id}")
                return False
            
            # Update rule
            rule.updated_at = datetime.now(timezone.utc)
            self.policies[rule.rule_id] = rule
            
            # Save to disk
            self._save_policy_rule(rule)
            
            # Clear cache
            self._clear_cache_for_policy_type(rule.policy_type)
            
            logger.info(f"Updated policy rule: {rule.rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update policy rule: {e}")
            return False
    
    async def evaluate_policy(self, context: PolicyContext) -> PolicyEvaluationResult:
        """Evaluate policies against a context"""
        try:
            self.evaluation_stats["total_evaluations"] += 1
            
            # Check cache first
            cache_key = self._generate_cache_key(context)
            if cache_key in self.policy_cache:
                self.evaluation_stats["cache_hits"] += 1
                cached_result = self.policy_cache[cache_key]
                if time.time() - cached_result["timestamp"] < POLICY_CACHE_TTL:
                    return cached_result["result"]
                else:
                    del self.policy_cache[cache_key]
            
            self.evaluation_stats["cache_misses"] += 1
            
            # Evaluate policies by priority
            applicable_policies = self._get_applicable_policies(context)
            applicable_policies.sort(key=lambda r: r.priority)
            
            for rule in applicable_policies:
                if not rule.enabled:
                    continue
                
                # Evaluate rule condition
                if self._evaluate_condition(rule.condition, context):
                    # Rule matched - determine action
                    result = PolicyEvaluationResult(
                        allowed=(rule.action == PolicyAction.ALLOW),
                        action=rule.action,
                        severity=rule.severity,
                        message=f"Policy rule '{rule.name}' matched",
                        metadata={
                            "rule_id": rule.rule_id,
                            "policy_type": rule.policy_type.value,
                            "condition": rule.condition
                        }
                    )
                    
                    # Handle violation if action is not ALLOW
                    if rule.action != PolicyAction.ALLOW:
                        violation = await self._create_violation(rule, context)
                        result.violation_id = violation.violation_id
                        result.message = f"Policy violation: {rule.name}"
                        
                        # Execute enforcement action
                        await self._execute_enforcement_action(rule.action, context, violation)
                    
                    # Cache result
                    self.policy_cache[cache_key] = {
                        "result": result,
                        "timestamp": time.time()
                    }
                    
                    # Update statistics
                    if result.allowed:
                        self.evaluation_stats["allowed_actions"] += 1
                    else:
                        self.evaluation_stats["denied_actions"] += 1
                        self.evaluation_stats["violations"] += 1
                    
                    return result
            
            # No rules matched - default deny
            result = PolicyEvaluationResult(
                allowed=False,
                action=PolicyAction.DENY,
                severity=PolicySeverity.HIGH,
                message="No policy rules matched - default deny",
                metadata={"default_policy": True}
            )
            
            self.evaluation_stats["denied_actions"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Policy evaluation failed: {e}")
            return PolicyEvaluationResult(
                allowed=False,
                action=PolicyAction.DENY,
                severity=PolicySeverity.CRITICAL,
                message=f"Policy evaluation error: {str(e)}",
                metadata={"error": True}
            )
    
    def _validate_rule(self, rule: PolicyRule) -> bool:
        """Validate a policy rule"""
        try:
            # Check required fields
            if not rule.rule_id or not rule.name or not rule.condition:
                return False
            
            # Validate condition syntax
            if not self._validate_condition_syntax(rule.condition):
                return False
            
            # Check for duplicate rule ID
            if rule.rule_id in self.policies:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Rule validation failed: {e}")
            return False
    
    def _validate_condition_syntax(self, condition: str) -> bool:
        """Validate condition syntax"""
        try:
            # Basic syntax validation
            if not condition or len(condition.strip()) == 0:
                return False
            
            # Check for balanced parentheses
            if condition.count('(') != condition.count(')'):
                return False
            
            # Check for balanced brackets
            if condition.count('[') != condition.count(']'):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Condition syntax validation failed: {e}")
            return False
    
    def _get_applicable_policies(self, context: PolicyContext) -> List[PolicyRule]:
        """Get policies applicable to the context"""
        applicable = []
        
        for rule in self.policies.values():
            # Check if rule applies to this context type
            if self._rule_applies_to_context(rule, context):
                applicable.append(rule)
        
        return applicable
    
    def _rule_applies_to_context(self, rule: PolicyRule, context: PolicyContext) -> bool:
        """Check if a rule applies to the given context"""
        try:
            # Policy type matching
            if rule.policy_type == PolicyType.ACCESS_CONTROL:
                return True  # Access control applies to all contexts
            elif rule.policy_type == PolicyType.SESSION:
                return context.session_data is not None
            elif rule.policy_type == PolicyType.DATA_PROTECTION:
                return context.resource_type in ["file", "data"]
            elif rule.policy_type == PolicyType.NETWORK:
                return context.resource_type == "network"
            elif rule.policy_type == PolicyType.RESOURCE:
                return context.resource_type in ["file", "process", "service"]
            elif rule.policy_type == PolicyType.ENCRYPTION:
                return context.action in ["encrypt", "decrypt", "key_access"]
            elif rule.policy_type == PolicyType.COMPLIANCE:
                return True  # Compliance applies to all contexts
            elif rule.policy_type == PolicyType.AUDIT:
                return True  # Audit applies to all contexts
            
            return False
            
        except Exception as e:
            logger.error(f"Rule applicability check failed: {e}")
            return False
    
    def _evaluate_condition(self, condition: str, context: PolicyContext) -> bool:
        """Evaluate a policy condition against context"""
        try:
            # Simple condition evaluation
            # This is a simplified implementation - in production would use a proper expression engine
            
            # Replace context variables
            evaluated_condition = condition
            
            # Session data
            if context.session_data:
                for key, value in context.session_data.items():
                    evaluated_condition = evaluated_condition.replace(f"session_{key}", str(value))
            
            # Environment data
            if context.environment_data:
                for key, value in context.environment_data.items():
                    evaluated_condition = evaluated_condition.replace(f"env_{key}", str(value))
            
            # Context data
            evaluated_condition = evaluated_condition.replace("session_id", f"'{context.session_id}'")
            evaluated_condition = evaluated_condition.replace("actor_identity", f"'{context.actor_identity}'")
            evaluated_condition = evaluated_condition.replace("actor_type", f"'{context.actor_type}'")
            evaluated_condition = evaluated_condition.replace("resource_type", f"'{context.resource_type}'")
            evaluated_condition = evaluated_condition.replace("action", f"'{context.action}'")
            
            if context.resource_path:
                evaluated_condition = evaluated_condition.replace("resource_path", f"'{context.resource_path}'")
            
            # Simple evaluation (in production, use a proper expression engine)
            if evaluated_condition == "true":
                return True
            elif evaluated_condition == "false":
                return False
            
            # Regex matching for resource paths
            if "matches" in evaluated_condition:
                # Extract regex pattern
                match = re.search(r"'([^']+)'", evaluated_condition)
                if match and context.resource_path:
                    pattern = match.group(1)
                    return bool(re.match(pattern, context.resource_path))
            
            # List membership
            if " in " in evaluated_condition:
                # Simple list membership check
                if "port" in evaluated_condition and "[" in evaluated_condition:
                    # Extract port list
                    port_list_match = re.search(r'\[([^\]]+)\]', evaluated_condition)
                    if port_list_match:
                        ports = [int(p.strip()) for p in port_list_match.group(1).split(',')]
                        # Check if context has port information
                        if "port" in context.metadata:
                            return context.metadata["port"] in ports
            
            # Numeric comparisons
            if ">" in evaluated_condition:
                # Simple numeric comparison
                if "session_duration" in evaluated_condition:
                    duration_match = re.search(r'session_duration > (\d+)', evaluated_condition)
                    if duration_match and "duration" in context.session_data:
                        threshold = int(duration_match.group(1))
                        return context.session_data["duration"] > threshold
            
            # Default to false for unmatched conditions
            return False
            
        except Exception as e:
            logger.error(f"Condition evaluation failed: {e}")
            return False
    
    async def _create_violation(self, rule: PolicyRule, context: PolicyContext) -> PolicyViolation:
        """Create a policy violation record"""
        try:
            violation = PolicyViolation(
                violation_id=str(uuid.uuid4()),
                session_id=context.session_id,
                rule_id=rule.rule_id,
                policy_type=rule.policy_type,
                severity=rule.severity,
                timestamp=context.timestamp,
                actor_identity=context.actor_identity,
                actor_type=context.actor_type,
                resource_accessed=context.resource_path,
                action_attempted=context.action,
                violation_data={
                    "condition": rule.condition,
                    "context": context.__dict__
                },
                enforcement_action=rule.action,
                metadata={
                    "rule_name": rule.name,
                    "rule_description": rule.description
                }
            )
            
            # Store violation
            self.violations.append(violation)
            
            # Save to disk
            self._save_violation(violation)
            
            # Notify callbacks
            await self._notify_violation_callbacks(violation)
            
            logger.warning(f"Policy violation created: {violation.violation_id}")
            
            return violation
            
        except Exception as e:
            logger.error(f"Failed to create violation: {e}")
            raise
    
    async def _execute_enforcement_action(self, action: PolicyAction, context: PolicyContext, violation: PolicyViolation) -> None:
        """Execute policy enforcement action"""
        try:
            if action == PolicyAction.DENY:
                logger.info(f"Access denied: {context.actor_identity} -> {context.resource_path}")
            elif action == PolicyAction.BLOCK:
                logger.warning(f"Access blocked: {context.actor_identity} -> {context.resource_path}")
            elif action == PolicyAction.QUARANTINE:
                logger.warning(f"Resource quarantined: {context.resource_path}")
            elif action == PolicyAction.LOG:
                logger.info(f"Action logged: {context.actor_identity} -> {context.resource_path}")
            elif action == PolicyAction.ALERT:
                logger.warning(f"Security alert: {context.actor_identity} -> {context.resource_path}")
            elif action == PolicyAction.REDIRECT:
                logger.info(f"Access redirected: {context.actor_identity} -> {context.resource_path}")
            
            # Notify enforcement callbacks
            await self._notify_enforcement_callbacks(action, context, violation)
            
        except Exception as e:
            logger.error(f"Enforcement action execution failed: {e}")
    
    def _generate_cache_key(self, context: PolicyContext) -> str:
        """Generate cache key for context"""
        key_data = {
            "session_id": context.session_id,
            "actor_identity": context.actor_identity,
            "actor_type": context.actor_type,
            "resource_type": context.resource_type,
            "action": context.action,
            "resource_path": context.resource_path
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return blake3.blake3(key_string.encode()).hexdigest()
    
    def _clear_cache_for_policy_type(self, policy_type: PolicyType) -> None:
        """Clear cache entries for a policy type"""
        try:
            # Simple cache clearing - in production would be more sophisticated
            self.policy_cache.clear()
            logger.debug(f"Cleared policy cache for type: {policy_type.value}")
        except Exception as e:
            logger.error(f"Cache clearing failed: {e}")
    
    def _save_policy_rule(self, rule: PolicyRule) -> None:
        """Save policy rule to disk"""
        try:
            rule_file = POLICY_PATH / "rules" / f"{rule.rule_id}.json"
            rule_data = {
                "rule_id": rule.rule_id,
                "policy_type": rule.policy_type.value,
                "name": rule.name,
                "description": rule.description,
                "condition": rule.condition,
                "action": rule.action.value,
                "severity": rule.severity.value,
                "priority": rule.priority,
                "enabled": rule.enabled,
                "created_at": rule.created_at.isoformat(),
                "updated_at": rule.updated_at.isoformat(),
                "metadata": rule.metadata
            }
            
            with open(rule_file, 'w') as f:
                json.dump(rule_data, f, indent=2)
            
            logger.debug(f"Saved policy rule: {rule.rule_id}")
            
        except Exception as e:
            logger.error(f"Failed to save policy rule: {e}")
    
    def _remove_policy_rule_file(self, rule_id: str) -> None:
        """Remove policy rule file from disk"""
        try:
            rule_file = POLICY_PATH / "rules" / f"{rule_id}.json"
            if rule_file.exists():
                rule_file.unlink()
                logger.debug(f"Removed policy rule file: {rule_id}")
        except Exception as e:
            logger.error(f"Failed to remove policy rule file: {e}")
    
    def _save_violation(self, violation: PolicyViolation) -> None:
        """Save violation to disk"""
        try:
            violation_file = POLICY_PATH / "violations" / f"{violation.violation_id}.json"
            violation_data = {
                "violation_id": violation.violation_id,
                "session_id": violation.session_id,
                "rule_id": violation.rule_id,
                "policy_type": violation.policy_type.value,
                "severity": violation.severity.value,
                "timestamp": violation.timestamp.isoformat(),
                "actor_identity": violation.actor_identity,
                "actor_type": violation.actor_type,
                "resource_accessed": violation.resource_accessed,
                "action_attempted": violation.action_attempted,
                "violation_data": violation.violation_data,
                "enforcement_action": violation.enforcement_action.value,
                "is_resolved": violation.is_resolved,
                "resolved_at": violation.resolved_at.isoformat() if violation.resolved_at else None,
                "resolved_by": violation.resolved_by,
                "metadata": violation.metadata
            }
            
            with open(violation_file, 'w') as f:
                json.dump(violation_data, f, indent=2)
            
            logger.debug(f"Saved violation: {violation.violation_id}")
            
        except Exception as e:
            logger.error(f"Failed to save violation: {e}")
    
    async def _notify_enforcement_callbacks(self, action: PolicyAction, context: PolicyContext, violation: PolicyViolation) -> None:
        """Notify enforcement callbacks"""
        try:
            for callback in self.enforcement_callbacks:
                try:
                    await callback(action, context, violation)
                except Exception as e:
                    logger.error(f"Enforcement callback failed: {e}")
        except Exception as e:
            logger.error(f"Enforcement callback notification failed: {e}")
    
    async def _notify_violation_callbacks(self, violation: PolicyViolation) -> None:
        """Notify violation callbacks"""
        try:
            for callback in self.violation_callbacks:
                try:
                    await callback(violation)
                except Exception as e:
                    logger.error(f"Violation callback failed: {e}")
        except Exception as e:
            logger.error(f"Violation callback notification failed: {e}")
    
    def add_enforcement_callback(self, callback: Callable) -> None:
        """Add enforcement callback"""
        self.enforcement_callbacks.append(callback)
    
    def add_violation_callback(self, callback: Callable) -> None:
        """Add violation callback"""
        self.violation_callbacks.append(callback)
    
    def get_policy_stats(self) -> Dict[str, Any]:
        """Get policy enforcement statistics"""
        return {
            "policies": {
                "total_rules": len(self.policies),
                "active_rules": len([r for r in self.policies.values() if r.enabled]),
                "inactive_rules": len([r for r in self.policies.values() if not r.enabled])
            },
            "evaluations": self.evaluation_stats.copy(),
            "violations": {
                "total": len(self.violations),
                "by_severity": {
                    severity.value: len([v for v in self.violations if v.severity == severity])
                    for severity in PolicySeverity
                },
                "by_type": {
                    policy_type.value: len([v for v in self.violations if v.policy_type == policy_type])
                    for policy_type in PolicyType
                }
            },
            "cache": {
                "size": len(self.policy_cache),
                "hit_rate": self.evaluation_stats["cache_hits"] / max(1, self.evaluation_stats["total_evaluations"])
            }
        }


# Global policy enforcer instance
policy_enforcer = TrustNothingPolicyEnforcer()
