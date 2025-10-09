# LUCID Wallet Policy Validator - Policy Validation Engine
# Implements comprehensive policy validation and enforcement for wallet operations
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import secrets
import json
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, padding
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# Configuration from environment
POLICY_VALIDATION_TIMEOUT_SECONDS = 30
POLICY_VALIDATION_CACHE_SIZE = 1000
POLICY_VALIDATION_MAX_RULES = 10000
POLICY_VALIDATION_AUDIT_RETENTION_DAYS = 365


class PolicyType(Enum):
    """Policy types"""
    ACCESS_CONTROL = "access_control"
    TRANSACTION_LIMITS = "transaction_limits"
    KEY_USAGE = "key_usage"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    AUDIT = "audit"
    COMPLIANCE = "compliance"
    SECURITY = "security"
    BUSINESS_LOGIC = "business_logic"


class PolicyOperator(Enum):
    """Policy operators"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX_MATCH = "regex_match"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class PolicyAction(Enum):
    """Policy actions"""
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"
    REQUIRE_APPROVAL = "require_approval"
    LOG = "log"
    ESCALATE = "escalate"
    QUARANTINE = "quarantine"
    RATE_LIMIT = "rate_limit"


class ValidationResult(Enum):
    """Validation result types"""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    ERROR = "error"
    INCONCLUSIVE = "inconclusive"


class PolicyStatus(Enum):
    """Policy status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    DEPRECATED = "deprecated"
    TESTING = "testing"


@dataclass
class PolicyRule:
    """Policy rule definition"""
    rule_id: str
    name: str
    description: str
    policy_type: PolicyType
    conditions: List[Dict[str, Any]]
    action: PolicyAction
    priority: int
    status: PolicyStatus = PolicyStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "policy_type": self.policy_type.value,
            "conditions": self.conditions,
            "action": self.action.value,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PolicyRule:
        """Create from dictionary"""
        return cls(
            rule_id=data["rule_id"],
            name=data["name"],
            description=data["description"],
            policy_type=PolicyType(data["policy_type"]),
            conditions=data["conditions"],
            action=PolicyAction(data["action"]),
            priority=data["priority"],
            status=PolicyStatus(data.get("status", "active")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            metadata=data.get("metadata", {})
        )


@dataclass
class ValidationContext:
    """Context for policy validation"""
    user_id: str
    session_id: str
    operation: str
    resource: str
    timestamp: datetime
    request_data: Dict[str, Any]
    user_context: Dict[str, Any] = field(default_factory=dict)
    system_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Policy validation result"""
    validation_id: str
    context: ValidationContext
    rule_id: str
    result: ValidationResult
    action: PolicyAction
    message: str
    confidence_score: float
    validation_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    execution_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyViolation:
    """Policy violation record"""
    violation_id: str
    rule_id: str
    context: ValidationContext
    severity: str
    description: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PolicyValidator:
    """
    Comprehensive policy validation engine for wallet operations.
    
    Features:
    - Rule-based policy validation
    - Real-time policy enforcement
    - Policy conflict resolution
    - Audit trail and compliance
    - Policy versioning and lifecycle
    - Performance optimization
    - Custom policy functions
    - Policy testing and simulation
    """
    
    def __init__(self, wallet_id: str):
        """Initialize policy validator"""
        self.wallet_id = wallet_id
        self.policy_rules: Dict[str, PolicyRule] = {}
        self.validation_results: List[ValidationResult] = []
        self.policy_violations: List[PolicyViolation] = []
        self.validation_cache: Dict[str, ValidationResult] = {}
        
        # Policy execution context
        self.execution_context: Dict[str, Any] = {}
        
        # Custom functions
        self.custom_functions: Dict[str, Callable] = {}
        
        # Initialize default policies
        self._initialize_default_policies()
        
        logger.info(f"PolicyValidator initialized for wallet: {wallet_id}")
    
    async def validate_policy(
        self,
        context: ValidationContext,
        policy_type: Optional[PolicyType] = None
    ) -> List[ValidationResult]:
        """Validate policies for given context"""
        try:
            validation_results = []
            
            # Filter rules by policy type if specified
            rules_to_check = []
            for rule in self.policy_rules.values():
                if rule.status != PolicyStatus.ACTIVE:
                    continue
                if rule.expires_at and datetime.now(timezone.utc) > rule.expires_at:
                    continue
                if policy_type and rule.policy_type != policy_type:
                    continue
                rules_to_check.append(rule)
            
            # Sort by priority (higher priority first)
            rules_to_check.sort(key=lambda r: r.priority, reverse=True)
            
            # Execute policy rules
            for rule in rules_to_check:
                start_time = time.time()
                
                try:
                    result = await self._execute_policy_rule(rule, context)
                    result.execution_time_ms = (time.time() - start_time) * 1000
                    validation_results.append(result)
                    
                    # Stop execution if rule denies action
                    if result.action == PolicyAction.DENY:
                        break
                        
                except Exception as e:
                    logger.error(f"Policy rule execution error: {e}")
                    # Create error result
                    error_result = ValidationResult(
                        validation_id=secrets.token_hex(16),
                        context=context,
                        rule_id=rule.rule_id,
                        result=ValidationResult.ERROR,
                        action=PolicyAction.DENY,
                        message=f"Policy execution error: {str(e)}",
                        confidence_score=0.0,
                        execution_time_ms=(time.time() - start_time) * 1000
                    )
                    validation_results.append(error_result)
                    break
            
            # Store results
            self.validation_results.extend(validation_results)
            
            # Clean up old results
            await self._cleanup_old_results()
            
            logger.info(f"Policy validation completed: {len(validation_results)} rules evaluated")
            return validation_results
            
        except Exception as e:
            logger.error(f"Policy validation failed: {e}")
            return []
    
    async def create_policy_rule(
        self,
        name: str,
        description: str,
        policy_type: PolicyType,
        conditions: List[Dict[str, Any]],
        action: PolicyAction,
        priority: int = 100,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create new policy rule"""
        try:
            rule_id = secrets.token_hex(16)
            
            rule = PolicyRule(
                rule_id=rule_id,
                name=name,
                description=description,
                policy_type=policy_type,
                conditions=conditions,
                action=action,
                priority=priority,
                expires_at=expires_at,
                metadata=metadata or {}
            )
            
            self.policy_rules[rule_id] = rule
            
            logger.info(f"Created policy rule: {rule_id} - {name}")
            return rule_id
            
        except Exception as e:
            logger.error(f"Failed to create policy rule: {e}")
            raise
    
    async def update_policy_rule(
        self,
        rule_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update existing policy rule"""
        try:
            if rule_id not in self.policy_rules:
                return False
            
            rule = self.policy_rules[rule_id]
            
            # Update fields
            for field, value in updates.items():
                if hasattr(rule, field):
                    setattr(rule, field, value)
            
            rule.updated_at = datetime.now(timezone.utc)
            
            logger.info(f"Updated policy rule: {rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update policy rule: {e}")
            return False
    
    async def delete_policy_rule(self, rule_id: str) -> bool:
        """Delete policy rule"""
        try:
            if rule_id not in self.policy_rules:
                return False
            
            del self.policy_rules[rule_id]
            
            logger.info(f"Deleted policy rule: {rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete policy rule: {e}")
            return False
    
    async def test_policy_rule(
        self,
        rule: PolicyRule,
        test_contexts: List[ValidationContext]
    ) -> List[ValidationResult]:
        """Test policy rule with test contexts"""
        try:
            results = []
            
            for context in test_contexts:
                result = await self._execute_policy_rule(rule, context)
                results.append(result)
            
            logger.info(f"Policy rule tested: {rule.rule_id} with {len(test_contexts)} contexts")
            return results
            
        except Exception as e:
            logger.error(f"Policy rule testing failed: {e}")
            return []
    
    async def simulate_policy_execution(
        self,
        context: ValidationContext,
        policy_changes: List[Dict[str, Any]]
    ) -> List[ValidationResult]:
        """Simulate policy execution with proposed changes"""
        try:
            # Create temporary validator with changes
            temp_validator = PolicyValidator(f"sim_{self.wallet_id}")
            temp_validator.policy_rules = self.policy_rules.copy()
            
            # Apply changes
            for change in policy_changes:
                if change["action"] == "create":
                    await temp_validator.create_policy_rule(**change["data"])
                elif change["action"] == "update":
                    await temp_validator.update_policy_rule(change["rule_id"], change["data"])
                elif change["action"] == "delete":
                    await temp_validator.delete_policy_rule(change["rule_id"])
            
            # Execute validation
            results = await temp_validator.validate_policy(context)
            
            logger.info(f"Policy simulation completed: {len(results)} rules evaluated")
            return results
            
        except Exception as e:
            logger.error(f"Policy simulation failed: {e}")
            return []
    
    async def get_policy_violations(
        self,
        user_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[PolicyViolation]:
        """Get policy violations with filtering"""
        try:
            violations = self.policy_violations
            
            # Apply filters
            if user_id:
                violations = [v for v in violations if v.context.user_id == user_id]
            
            if start_time:
                violations = [v for v in violations if v.detected_at >= start_time]
            
            if end_time:
                violations = [v for v in violations if v.detected_at <= end_time]
            
            if severity:
                violations = [v for v in violations if v.severity == severity]
            
            # Sort by detection time (newest first)
            violations.sort(key=lambda v: v.detected_at, reverse=True)
            
            return violations[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get policy violations: {e}")
            return []
    
    async def resolve_policy_violation(
        self,
        violation_id: str,
        resolution_notes: str
    ) -> bool:
        """Resolve policy violation"""
        try:
            for violation in self.policy_violations:
                if violation.violation_id == violation_id:
                    violation.resolved_at = datetime.now(timezone.utc)
                    violation.resolution_notes = resolution_notes
                    
                    logger.info(f"Policy violation resolved: {violation_id}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to resolve policy violation: {e}")
            return False
    
    async def register_custom_function(
        self,
        function_name: str,
        function: Callable
    ) -> bool:
        """Register custom policy function"""
        try:
            self.custom_functions[function_name] = function
            
            logger.info(f"Registered custom function: {function_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register custom function: {e}")
            return False
    
    async def get_policy_statistics(self) -> Dict[str, Any]:
        """Get policy validation statistics"""
        try:
            total_validations = len(self.validation_results)
            passed_validations = len([r for r in self.validation_results if r.result == ValidationResult.PASS])
            failed_validations = len([r for r in self.validation_results if r.result == ValidationResult.FAIL])
            warning_validations = len([r for r in self.validation_results if r.result == ValidationResult.WARN])
            
            total_violations = len(self.policy_violations)
            unresolved_violations = len([v for v in self.policy_violations if not v.resolved_at])
            
            return {
                "wallet_id": self.wallet_id,
                "active_rules": len([r for r in self.policy_rules.values() if r.status == PolicyStatus.ACTIVE]),
                "total_rules": len(self.policy_rules),
                "total_validations": total_validations,
                "validation_results": {
                    "passed": passed_validations,
                    "failed": failed_validations,
                    "warnings": warning_validations,
                    "pass_rate": passed_validations / total_validations if total_validations > 0 else 0
                },
                "violations": {
                    "total": total_violations,
                    "unresolved": unresolved_violations,
                    "resolution_rate": (total_violations - unresolved_violations) / total_violations if total_violations > 0 else 0
                },
                "custom_functions": len(self.custom_functions),
                "cache_size": len(self.validation_cache)
            }
            
        except Exception as e:
            logger.error(f"Failed to get policy statistics: {e}")
            return {}
    
    async def _execute_policy_rule(
        self,
        rule: PolicyRule,
        context: ValidationContext
    ) -> ValidationResult:
        """Execute individual policy rule"""
        try:
            validation_id = secrets.token_hex(16)
            
            # Evaluate conditions
            condition_results = []
            for condition in rule.conditions:
                result = await self._evaluate_condition(condition, context)
                condition_results.append(result)
            
            # Determine overall result
            if all(condition_results):
                result = ValidationResult.PASS
                action = PolicyAction.ALLOW
                message = f"Policy rule '{rule.name}' passed"
                confidence_score = 1.0
            else:
                result = ValidationResult.FAIL
                action = rule.action
                message = f"Policy rule '{rule.name}' failed"
                confidence_score = 0.0
                
                # Record violation if action is DENY
                if action == PolicyAction.DENY:
                    await self._record_policy_violation(rule, context, message)
            
            return ValidationResult(
                validation_id=validation_id,
                context=context,
                rule_id=rule.rule_id,
                result=result,
                action=action,
                message=message,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Policy rule execution error: {e}")
            return ValidationResult(
                validation_id=secrets.token_hex(16),
                context=context,
                rule_id=rule.rule_id,
                result=ValidationResult.ERROR,
                action=PolicyAction.DENY,
                message=f"Policy execution error: {str(e)}",
                confidence_score=0.0
            )
    
    async def _evaluate_condition(
        self,
        condition: Dict[str, Any],
        context: ValidationContext
    ) -> bool:
        """Evaluate individual condition"""
        try:
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")
            
            if not field or not operator:
                return False
            
            # Get field value from context
            field_value = self._get_field_value(field, context)
            
            # Apply operator
            return await self._apply_operator(operator, field_value, value)
            
        except Exception as e:
            logger.error(f"Condition evaluation error: {e}")
            return False
    
    def _get_field_value(self, field: str, context: ValidationContext) -> Any:
        """Get field value from context"""
        try:
            # Split field path (e.g., "request_data.amount")
            field_parts = field.split(".")
            current_value = context
            
            for part in field_parts:
                if isinstance(current_value, dict):
                    current_value = current_value.get(part)
                elif hasattr(current_value, part):
                    current_value = getattr(current_value, part)
                else:
                    return None
            
            return current_value
            
        except Exception as e:
            logger.error(f"Field value extraction error: {e}")
            return None
    
    async def _apply_operator(
        self,
        operator: str,
        field_value: Any,
        expected_value: Any
    ) -> bool:
        """Apply operator to field value"""
        try:
            op = PolicyOperator(operator)
            
            if op == PolicyOperator.EQUALS:
                return field_value == expected_value
            elif op == PolicyOperator.NOT_EQUALS:
                return field_value != expected_value
            elif op == PolicyOperator.GREATER_THAN:
                return field_value > expected_value
            elif op == PolicyOperator.LESS_THAN:
                return field_value < expected_value
            elif op == PolicyOperator.GREATER_EQUAL:
                return field_value >= expected_value
            elif op == PolicyOperator.LESS_EQUAL:
                return field_value <= expected_value
            elif op == PolicyOperator.CONTAINS:
                return expected_value in field_value if field_value else False
            elif op == PolicyOperator.NOT_CONTAINS:
                return expected_value not in field_value if field_value else True
            elif op == PolicyOperator.STARTS_WITH:
                return field_value.startswith(expected_value) if isinstance(field_value, str) else False
            elif op == PolicyOperator.ENDS_WITH:
                return field_value.endswith(expected_value) if isinstance(field_value, str) else False
            elif op == PolicyOperator.REGEX_MATCH:
                return bool(re.match(expected_value, str(field_value))) if field_value else False
            elif op == PolicyOperator.IN_LIST:
                return field_value in expected_value if isinstance(expected_value, list) else False
            elif op == PolicyOperator.NOT_IN_LIST:
                return field_value not in expected_value if isinstance(expected_value, list) else True
            elif op == PolicyOperator.EXISTS:
                return field_value is not None
            elif op == PolicyOperator.NOT_EXISTS:
                return field_value is None
            else:
                return False
                
        except Exception as e:
            logger.error(f"Operator application error: {e}")
            return False
    
    async def _record_policy_violation(
        self,
        rule: PolicyRule,
        context: ValidationContext,
        description: str
    ) -> None:
        """Record policy violation"""
        try:
            violation = PolicyViolation(
                violation_id=secrets.token_hex(16),
                rule_id=rule.rule_id,
                context=context,
                severity="high" if rule.action == PolicyAction.DENY else "medium",
                description=description,
                detected_at=datetime.now(timezone.utc),
                metadata={"rule_name": rule.name}
            )
            
            self.policy_violations.append(violation)
            
            logger.warning(f"Policy violation recorded: {violation.violation_id}")
            
        except Exception as e:
            logger.error(f"Failed to record policy violation: {e}")
    
    async def _cleanup_old_results(self) -> None:
        """Clean up old validation results"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=POLICY_VALIDATION_AUDIT_RETENTION_DAYS)
            
            # Clean validation results
            self.validation_results = [r for r in self.validation_results if r.validation_time > cutoff_date]
            
            # Clean policy violations
            self.policy_violations = [v for v in self.policy_violations if v.detected_at > cutoff_date]
            
            # Clean cache
            self.validation_cache.clear()
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def _initialize_default_policies(self) -> None:
        """Initialize default policy rules"""
        try:
            # Default access control policy
            self.policy_rules["default_access_control"] = PolicyRule(
                rule_id="default_access_control",
                name="Default Access Control",
                description="Basic access control for wallet operations",
                policy_type=PolicyType.ACCESS_CONTROL,
                conditions=[
                    {
                        "field": "user_id",
                        "operator": "exists",
                        "value": None
                    },
                    {
                        "field": "session_id",
                        "operator": "exists",
                        "value": None
                    }
                ],
                action=PolicyAction.ALLOW,
                priority=1000
            )
            
            # Default transaction limits policy
            self.policy_rules["default_transaction_limits"] = PolicyRule(
                rule_id="default_transaction_limits",
                name="Default Transaction Limits",
                description="Basic transaction limits",
                policy_type=PolicyType.TRANSACTION_LIMITS,
                conditions=[
                    {
                        "field": "request_data.amount",
                        "operator": "less_equal",
                        "value": 1000000  # 1M units
                    }
                ],
                action=PolicyAction.ALLOW,
                priority=900
            )
            
            # Default authentication policy
            self.policy_rules["default_authentication"] = PolicyRule(
                rule_id="default_authentication",
                name="Default Authentication",
                description="Basic authentication requirements",
                policy_type=PolicyType.AUTHENTICATION,
                conditions=[
                    {
                        "field": "user_context.authenticated",
                        "operator": "equals",
                        "value": True
                    }
                ],
                action=PolicyAction.DENY,
                priority=1100
            )
            
            logger.info("Initialized default policy rules")
            
        except Exception as e:
            logger.error(f"Failed to initialize default policies: {e}")


# Global policy validators
_policy_validators: Dict[str, PolicyValidator] = {}


def get_policy_validator(wallet_id: str) -> Optional[PolicyValidator]:
    """Get policy validator for wallet"""
    return _policy_validators.get(wallet_id)


def create_policy_validator(wallet_id: str) -> PolicyValidator:
    """Create new policy validator for wallet"""
    policy_validator = PolicyValidator(wallet_id)
    _policy_validators[wallet_id] = policy_validator
    return policy_validator


async def main():
    """Main function for testing"""
    import asyncio
    
    # Create policy validator
    validator = create_policy_validator("test_wallet_001")
    
    # Create test context
    context = ValidationContext(
        user_id="test_user_001",
        session_id="test_session_001",
        operation="transfer_funds",
        resource="wallet_balance",
        timestamp=datetime.now(timezone.utc),
        request_data={
            "amount": 1000,
            "recipient": "recipient_address",
            "currency": "USDT"
        },
        user_context={
            "authenticated": True,
            "role": "user"
        }
    )
    
    # Validate policies
    results = await validator.validate_policy(context)
    print(f"Policy validation results: {len(results)}")
    
    for result in results:
        print(f"Rule: {result.rule_id}")
        print(f"Result: {result.result.value}")
        print(f"Action: {result.action.value}")
        print(f"Message: {result.message}")
        print(f"Confidence: {result.confidence_score:.2f}")
        print("---")
    
    # Create custom policy rule
    rule_id = await validator.create_policy_rule(
        name="High Value Transfer Policy",
        description="Require approval for high value transfers",
        policy_type=PolicyType.TRANSACTION_LIMITS,
        conditions=[
            {
                "field": "request_data.amount",
                "operator": "greater_than",
                "value": 10000
            }
        ],
        action=PolicyAction.REQUIRE_APPROVAL,
        priority=500
    )
    print(f"Created policy rule: {rule_id}")
    
    # Test with high value transfer
    high_value_context = ValidationContext(
        user_id="test_user_001",
        session_id="test_session_001",
        operation="transfer_funds",
        resource="wallet_balance",
        timestamp=datetime.now(timezone.utc),
        request_data={
            "amount": 15000,  # High value
            "recipient": "recipient_address",
            "currency": "USDT"
        },
        user_context={
            "authenticated": True,
            "role": "user"
        }
    )
    
    high_value_results = await validator.validate_policy(high_value_context)
    print(f"High value transfer validation: {len(high_value_results)} results")
    
    for result in high_value_results:
        print(f"Rule: {result.rule_id}")
        print(f"Result: {result.result.value}")
        print(f"Action: {result.action.value}")
        print("---")
    
    # Get statistics
    stats = await validator.get_policy_statistics()
    print(f"Policy statistics: {stats}")


if __name__ == "__main__":
    asyncio.run(main())
