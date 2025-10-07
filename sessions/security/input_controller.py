# Path: sessions/security/input_controller.py
# LUCID Input Validation and Control - Security Input Controller
# Professional input validation and control for session security
# Multi-platform support for ARM64 Pi and AMD64 development

from __future__ import annotations

import asyncio
import logging
import os
import time
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
import blake3

logger = logging.getLogger(__name__)

# Configuration from environment
INPUT_CONTROL_PATH = Path(os.getenv("INPUT_CONTROL_PATH", "/data/input_control"))
INPUT_VALIDATION_TIMEOUT = float(os.getenv("INPUT_VALIDATION_TIMEOUT", "5.0"))
MAX_INPUT_SIZE = int(os.getenv("MAX_INPUT_SIZE", "1048576"))  # 1MB


class InputType(Enum):
    """Types of input data"""
    KEYSTROKE = "keystroke"
    MOUSE_CLICK = "mouse_click"
    MOUSE_MOVE = "mouse_move"
    TOUCH = "touch"
    GESTURE = "gesture"
    VOICE = "voice"
    FILE_UPLOAD = "file_upload"
    TEXT_INPUT = "text_input"
    COMMAND = "command"
    URL = "url"
    EMAIL = "email"
    PASSWORD = "password"
    API_REQUEST = "api_request"
    DATABASE_QUERY = "database_query"
    NETWORK_REQUEST = "network_request"


class ValidationResult(Enum):
    """Input validation results"""
    VALID = "valid"
    INVALID = "invalid"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    BLOCKED = "blocked"


class InputSeverity(Enum):
    """Input security severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InputAction(Enum):
    """Input control actions"""
    ALLOW = "allow"
    BLOCK = "block"
    SANITIZE = "sanitize"
    QUARANTINE = "quarantine"
    LOG = "log"
    ALERT = "alert"
    REDIRECT = "redirect"


@dataclass
class InputData:
    """Input data structure"""
    input_id: str
    session_id: str
    input_type: InputType
    data: Any
    timestamp: datetime
    source: str
    target: str
    size: int = 0
    encoding: str = "utf-8"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationRule:
    """Input validation rule"""
    rule_id: str
    name: str
    description: str
    input_type: InputType
    pattern: str  # Regex pattern or validation logic
    action: InputAction
    severity: InputSeverity
    enabled: bool = True
    priority: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Input validation result"""
    validation_id: str
    input_id: str
    rule_id: Optional[str]
    result: ValidationResult
    action: InputAction
    severity: InputSeverity
    timestamp: datetime
    message: str
    sanitized_data: Optional[Any] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InputViolation:
    """Input security violation"""
    violation_id: str
    session_id: str
    input_id: str
    validation_id: str
    violation_type: str
    severity: InputSeverity
    timestamp: datetime
    actor_identity: str
    input_data: Any
    blocked_data: Optional[Any] = None
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class InputController:
    """
    Professional input validation and control for Lucid RDP sessions.
    
    Provides comprehensive input validation, sanitization, and security
    enforcement with real-time threat detection.
    """
    
    def __init__(self):
        """Initialize input controller"""
        # Validation rules
        self.validation_rules: Dict[str, ValidationRule] = {}
        self.rule_cache: Dict[str, List[ValidationRule]] = {}
        
        # Validation results and violations
        self.validation_results: List[ValidationResult] = []
        self.input_violations: List[InputViolation] = []
        
        # Callbacks
        self.validation_callbacks: List[Callable] = []
        self.violation_callbacks: List[Callable] = []
        
        # Statistics
        self.validation_stats = {
            "total_validations": 0,
            "valid_inputs": 0,
            "invalid_inputs": 0,
            "blocked_inputs": 0,
            "sanitized_inputs": 0,
            "violations": 0
        }
        
        # Create directories
        self._create_directories()
        
        # Load default validation rules
        self._load_default_rules()
        
        logger.info("Input controller initialized")
    
    def _create_directories(self) -> None:
        """Create required directories"""
        INPUT_CONTROL_PATH.mkdir(parents=True, exist_ok=True)
        (INPUT_CONTROL_PATH / "rules").mkdir(exist_ok=True)
        (INPUT_CONTROL_PATH / "violations").mkdir(exist_ok=True)
        (INPUT_CONTROL_PATH / "quarantine").mkdir(exist_ok=True)
        logger.info(f"Created input control directories: {INPUT_CONTROL_PATH}")
    
    def _load_default_rules(self) -> None:
        """Load default input validation rules"""
        try:
            # SQL injection patterns
            self.add_validation_rule(ValidationRule(
                rule_id="sql_injection",
                name="SQL Injection Prevention",
                description="Block SQL injection attempts",
                input_type=InputType.TEXT_INPUT,
                pattern=r"(union\s+select|drop\s+table|delete\s+from|insert\s+into|update\s+set|exec\s*\(|script\s*>|<\s*script)",
                action=InputAction.BLOCK,
                severity=InputSeverity.HIGH,
                priority=100
            ))
            
            # XSS patterns
            self.add_validation_rule(ValidationRule(
                rule_id="xss_prevention",
                name="XSS Prevention",
                description="Block cross-site scripting attempts",
                input_type=InputType.TEXT_INPUT,
                pattern=r"<script[^>]*>|javascript:|on\w+\s*=|eval\s*\(|alert\s*\(",
                action=InputAction.BLOCK,
                severity=InputSeverity.HIGH,
                priority=200
            ))
            
            # Command injection patterns
            self.add_validation_rule(ValidationRule(
                rule_id="command_injection",
                name="Command Injection Prevention",
                description="Block command injection attempts",
                input_type=InputType.COMMAND,
                pattern=r"[;&|`$(){}[\]<>]|cat\s+|\s+rm\s+|wget\s+|curl\s+|nc\s+|netcat",
                action=InputAction.BLOCK,
                severity=InputSeverity.CRITICAL,
                priority=50
            ))
            
            # Path traversal patterns
            self.add_validation_rule(ValidationRule(
                rule_id="path_traversal",
                name="Path Traversal Prevention",
                description="Block path traversal attempts",
                input_type=InputType.FILE_UPLOAD,
                pattern=r"\.\./|\.\.\\|%2e%2e%2f|%2e%2e%5c",
                action=InputAction.BLOCK,
                severity=InputSeverity.HIGH,
                priority=150
            ))
            
            # Malicious URL patterns
            self.add_validation_rule(ValidationRule(
                rule_id="malicious_url",
                name="Malicious URL Detection",
                description="Block malicious URLs",
                input_type=InputType.URL,
                pattern=r"(bit\.ly|tinyurl|t\.co|goo\.gl|ow\.ly|is\.gd|v\.gd|short\.link)",
                action=InputAction.SANITIZE,
                severity=InputSeverity.MEDIUM,
                priority=300
            ))
            
            # Password strength validation
            self.add_validation_rule(ValidationRule(
                rule_id="password_strength",
                name="Password Strength Validation",
                description="Enforce strong passwords",
                input_type=InputType.PASSWORD,
                pattern=r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$",
                action=InputAction.ALLOW,
                severity=InputSeverity.MEDIUM,
                priority=400
            ))
            
            # Email validation
            self.add_validation_rule(ValidationRule(
                rule_id="email_validation",
                name="Email Format Validation",
                description="Validate email format",
                input_type=InputType.EMAIL,
                pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
                action=InputAction.ALLOW,
                severity=InputSeverity.LOW,
                priority=500
            ))
            
            # File size limits
            self.add_validation_rule(ValidationRule(
                rule_id="file_size_limit",
                name="File Size Limit",
                description="Enforce file size limits",
                input_type=InputType.FILE_UPLOAD,
                pattern=f"size <= {MAX_INPUT_SIZE}",
                action=InputAction.BLOCK,
                severity=InputSeverity.MEDIUM,
                priority=250
            ))
            
            logger.info("Loaded default input validation rules")
            
        except Exception as e:
            logger.error(f"Failed to load default rules: {e}")
    
    def add_validation_rule(self, rule: ValidationRule) -> bool:
        """Add a new validation rule"""
        try:
            # Validate rule
            if not self._validate_rule(rule):
                logger.error(f"Invalid validation rule: {rule.rule_id}")
                return False
            
            # Store rule
            self.validation_rules[rule.rule_id] = rule
            
            # Clear cache
            self._clear_cache_for_input_type(rule.input_type)
            
            # Save to disk
            self._save_validation_rule(rule)
            
            logger.info(f"Added validation rule: {rule.rule_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add validation rule: {e}")
            return False
    
    def remove_validation_rule(self, rule_id: str) -> bool:
        """Remove a validation rule"""
        try:
            if rule_id in self.validation_rules:
                rule = self.validation_rules[rule_id]
                del self.validation_rules[rule_id]
                
                # Clear cache
                self._clear_cache_for_input_type(rule.input_type)
                
                # Remove from disk
                self._remove_validation_rule_file(rule_id)
                
                logger.info(f"Removed validation rule: {rule_id}")
                return True
            else:
                logger.warning(f"Validation rule not found: {rule_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to remove validation rule: {e}")
            return False
    
    async def validate_input(self, input_data: InputData) -> ValidationResult:
        """Validate input data"""
        try:
            self.validation_stats["total_validations"] += 1
            
            # Generate validation ID
            validation_id = str(uuid.uuid4())
            
            # Get applicable rules
            applicable_rules = self._get_applicable_rules(input_data.input_type)
            
            # Sort by priority
            applicable_rules.sort(key=lambda r: r.priority)
            
            # Validate against rules
            for rule in applicable_rules:
                if not rule.enabled:
                    continue
                
                # Apply rule validation
                validation_result = await self._apply_rule_validation(rule, input_data)
                
                if validation_result.result != ValidationResult.VALID:
                    # Rule violation detected
                    result = ValidationResult(
                        validation_id=validation_id,
                        input_id=input_data.input_id,
                        rule_id=rule.rule_id,
                        result=validation_result.result,
                        action=rule.action,
                        severity=rule.severity,
                        timestamp=datetime.now(timezone.utc),
                        message=validation_result.message,
                        sanitized_data=validation_result.sanitized_data,
                        confidence=validation_result.confidence,
                        metadata={
                            "rule_name": rule.name,
                            "pattern": rule.pattern
                        }
                    )
                    
                    # Store result
                    self.validation_results.append(result)
                    
                    # Handle violation
                    await self._handle_validation_violation(result, input_data)
                    
                    # Update statistics
                    self._update_validation_stats(result)
                    
                    return result
            
            # No violations found
            result = ValidationResult(
                validation_id=validation_id,
                input_id=input_data.input_id,
                rule_id=None,
                result=ValidationResult.VALID,
                action=InputAction.ALLOW,
                severity=InputSeverity.LOW,
                timestamp=datetime.now(timezone.utc),
                message="Input validation passed",
                confidence=1.0
            )
            
            self.validation_results.append(result)
            self.validation_stats["valid_inputs"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Input validation failed: {e}")
            return ValidationResult(
                validation_id=str(uuid.uuid4()),
                input_id=input_data.input_id,
                rule_id=None,
                result=ValidationResult.INVALID,
                action=InputAction.BLOCK,
                severity=InputSeverity.CRITICAL,
                timestamp=datetime.now(timezone.utc),
                message=f"Validation error: {str(e)}",
                confidence=0.0
            )
    
    def _validate_rule(self, rule: ValidationRule) -> bool:
        """Validate a validation rule"""
        try:
            # Check required fields
            if not rule.rule_id or not rule.name or not rule.pattern:
                return False
            
            # Validate pattern syntax
            if not self._validate_pattern_syntax(rule.pattern):
                return False
            
            # Check for duplicate rule ID
            if rule.rule_id in self.validation_rules:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Rule validation failed: {e}")
            return False
    
    def _validate_pattern_syntax(self, pattern: str) -> bool:
        """Validate pattern syntax"""
        try:
            # Try to compile regex pattern
            re.compile(pattern)
            return True
        except re.error:
            # Check for special validation patterns
            if pattern.startswith("size ") or pattern.startswith("length "):
                return True
            return False
    
    def _get_applicable_rules(self, input_type: InputType) -> List[ValidationRule]:
        """Get rules applicable to input type"""
        cache_key = input_type.value
        
        if cache_key in self.rule_cache:
            return self.rule_cache[cache_key]
        
        applicable_rules = [
            rule for rule in self.validation_rules.values()
            if rule.input_type == input_type and rule.enabled
        ]
        
        self.rule_cache[cache_key] = applicable_rules
        return applicable_rules
    
    async def _apply_rule_validation(self, rule: ValidationRule, input_data: InputData) -> ValidationResult:
        """Apply a validation rule to input data"""
        try:
            # Convert input data to string for pattern matching
            input_string = str(input_data.data)
            
            # Check for size/length patterns
            if rule.pattern.startswith("size "):
                # Size validation
                size_condition = rule.pattern.replace("size ", "")
                if "<=" in size_condition:
                    limit = int(size_condition.split("<=")[1].strip())
                    if input_data.size > limit:
                        return ValidationResult(
                            result=ValidationResult.INVALID,
                            message=f"Input size {input_data.size} exceeds limit {limit}",
                            confidence=1.0
                        )
                elif ">=" in size_condition:
                    limit = int(size_condition.split(">=")[1].strip())
                    if input_data.size < limit:
                        return ValidationResult(
                            result=ValidationResult.INVALID,
                            message=f"Input size {input_data.size} below minimum {limit}",
                            confidence=1.0
                        )
                return ValidationResult(result=ValidationResult.VALID, confidence=1.0)
            
            # Regex pattern matching
            if re.search(rule.pattern, input_string, re.IGNORECASE):
                # Pattern matched - potential violation
                if rule.action == InputAction.BLOCK:
                    return ValidationResult(
                        result=ValidationResult.MALICIOUS,
                        message=f"Input matches blocked pattern: {rule.name}",
                        confidence=0.9
                    )
                elif rule.action == InputAction.SANITIZE:
                    sanitized = await self._sanitize_input(input_string, rule.pattern)
                    return ValidationResult(
                        result=ValidationResult.SUSPICIOUS,
                        message=f"Input sanitized due to pattern match: {rule.name}",
                        sanitized_data=sanitized,
                        confidence=0.7
                    )
                else:
                    return ValidationResult(
                        result=ValidationResult.SUSPICIOUS,
                        message=f"Input matches pattern: {rule.name}",
                        confidence=0.5
                    )
            
            return ValidationResult(result=ValidationResult.VALID, confidence=1.0)
            
        except Exception as e:
            logger.error(f"Rule validation application failed: {e}")
            return ValidationResult(
                result=ValidationResult.INVALID,
                message=f"Validation error: {str(e)}",
                confidence=0.0
            )
    
    async def _sanitize_input(self, input_string: str, pattern: str) -> str:
        """Sanitize input data"""
        try:
            # Basic sanitization
            sanitized = input_string
            
            # Remove script tags
            sanitized = re.sub(r'<script[^>]*>.*?</script>', '', sanitized, flags=re.IGNORECASE | re.DOTALL)
            
            # Remove javascript: protocols
            sanitized = re.sub(r'javascript:', '', sanitized, flags=re.IGNORECASE)
            
            # Remove dangerous HTML attributes
            sanitized = re.sub(r'on\w+\s*=', '', sanitized, flags=re.IGNORECASE)
            
            # Remove SQL keywords
            sql_keywords = ['union', 'select', 'drop', 'delete', 'insert', 'update', 'exec']
            for keyword in sql_keywords:
                sanitized = re.sub(rf'\b{keyword}\b', '', sanitized, flags=re.IGNORECASE)
            
            # Remove path traversal sequences
            sanitized = re.sub(r'\.\./', '', sanitized)
            sanitized = re.sub(r'\.\.\\', '', sanitized)
            
            # Trim whitespace
            sanitized = sanitized.strip()
            
            return sanitized
            
        except Exception as e:
            logger.error(f"Input sanitization failed: {e}")
            return input_string
    
    async def _handle_validation_violation(self, result: ValidationResult, input_data: InputData) -> None:
        """Handle validation violation"""
        try:
            # Create violation record
            violation = InputViolation(
                violation_id=str(uuid.uuid4()),
                session_id=input_data.session_id,
                input_id=input_data.input_id,
                validation_id=result.validation_id,
                violation_type=result.result.value,
                severity=result.severity,
                timestamp=result.timestamp,
                actor_identity=input_data.source,
                input_data=input_data.data,
                blocked_data=result.sanitized_data,
                metadata={
                    "rule_id": result.rule_id,
                    "message": result.message,
                    "confidence": result.confidence
                }
            )
            
            # Store violation
            self.input_violations.append(violation)
            
            # Save to disk
            self._save_input_violation(violation)
            
            # Quarantine if needed
            if result.action == InputAction.QUARANTINE:
                await self._quarantine_input(input_data)
            
            # Notify callbacks
            await self._notify_violation_callbacks(violation)
            
            logger.warning(f"Input validation violation: {violation.violation_id}")
            
        except Exception as e:
            logger.error(f"Violation handling failed: {e}")
    
    async def _quarantine_input(self, input_data: InputData) -> None:
        """Quarantine suspicious input"""
        try:
            quarantine_file = INPUT_CONTROL_PATH / "quarantine" / f"{input_data.input_id}.json"
            
            quarantine_data = {
                "input_id": input_data.input_id,
                "session_id": input_data.session_id,
                "input_type": input_data.input_type.value,
                "data": str(input_data.data),
                "timestamp": input_data.timestamp.isoformat(),
                "source": input_data.source,
                "target": input_data.target,
                "size": input_data.size,
                "metadata": input_data.metadata
            }
            
            with open(quarantine_file, 'w') as f:
                json.dump(quarantine_data, f, indent=2)
            
            logger.info(f"Input quarantined: {input_data.input_id}")
            
        except Exception as e:
            logger.error(f"Input quarantine failed: {e}")
    
    def _update_validation_stats(self, result: ValidationResult) -> None:
        """Update validation statistics"""
        try:
            if result.result == ValidationResult.INVALID:
                self.validation_stats["invalid_inputs"] += 1
            elif result.result == ValidationResult.MALICIOUS:
                self.validation_stats["blocked_inputs"] += 1
            elif result.result == ValidationResult.SUSPICIOUS:
                self.validation_stats["sanitized_inputs"] += 1
            
            if result.action in [InputAction.BLOCK, InputAction.QUARANTINE]:
                self.validation_stats["violations"] += 1
                
        except Exception as e:
            logger.error(f"Statistics update failed: {e}")
    
    def _clear_cache_for_input_type(self, input_type: InputType) -> None:
        """Clear cache for input type"""
        try:
            cache_key = input_type.value
            if cache_key in self.rule_cache:
                del self.rule_cache[cache_key]
                logger.debug(f"Cleared rule cache for type: {input_type.value}")
        except Exception as e:
            logger.error(f"Cache clearing failed: {e}")
    
    def _save_validation_rule(self, rule: ValidationRule) -> None:
        """Save validation rule to disk"""
        try:
            rule_file = INPUT_CONTROL_PATH / "rules" / f"{rule.rule_id}.json"
            rule_data = {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "input_type": rule.input_type.value,
                "pattern": rule.pattern,
                "action": rule.action.value,
                "severity": rule.severity.value,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "created_at": rule.created_at.isoformat(),
                "updated_at": rule.updated_at.isoformat(),
                "metadata": rule.metadata
            }
            
            with open(rule_file, 'w') as f:
                json.dump(rule_data, f, indent=2)
            
            logger.debug(f"Saved validation rule: {rule.rule_id}")
            
        except Exception as e:
            logger.error(f"Failed to save validation rule: {e}")
    
    def _remove_validation_rule_file(self, rule_id: str) -> None:
        """Remove validation rule file"""
        try:
            rule_file = INPUT_CONTROL_PATH / "rules" / f"{rule_id}.json"
            if rule_file.exists():
                rule_file.unlink()
                logger.debug(f"Removed validation rule file: {rule_id}")
        except Exception as e:
            logger.error(f"Failed to remove validation rule file: {e}")
    
    def _save_input_violation(self, violation: InputViolation) -> None:
        """Save input violation to disk"""
        try:
            violation_file = INPUT_CONTROL_PATH / "violations" / f"{violation.violation_id}.json"
            violation_data = {
                "violation_id": violation.violation_id,
                "session_id": violation.session_id,
                "input_id": violation.input_id,
                "validation_id": violation.validation_id,
                "violation_type": violation.violation_type,
                "severity": violation.severity.value,
                "timestamp": violation.timestamp.isoformat(),
                "actor_identity": violation.actor_identity,
                "input_data": str(violation.input_data),
                "blocked_data": str(violation.blocked_data) if violation.blocked_data else None,
                "is_resolved": violation.is_resolved,
                "resolved_at": violation.resolved_at.isoformat() if violation.resolved_at else None,
                "resolved_by": violation.resolved_by,
                "metadata": violation.metadata
            }
            
            with open(violation_file, 'w') as f:
                json.dump(violation_data, f, indent=2)
            
            logger.debug(f"Saved input violation: {violation.violation_id}")
            
        except Exception as e:
            logger.error(f"Failed to save input violation: {e}")
    
    async def _notify_violation_callbacks(self, violation: InputViolation) -> None:
        """Notify violation callbacks"""
        try:
            for callback in self.violation_callbacks:
                try:
                    await callback(violation)
                except Exception as e:
                    logger.error(f"Violation callback failed: {e}")
        except Exception as e:
            logger.error(f"Violation callback notification failed: {e}")
    
    def add_validation_callback(self, callback: Callable) -> None:
        """Add validation callback"""
        self.validation_callbacks.append(callback)
    
    def add_violation_callback(self, callback: Callable) -> None:
        """Add violation callback"""
        self.violation_callbacks.append(callback)
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get input validation statistics"""
        return {
            "rules": {
                "total_rules": len(self.validation_rules),
                "active_rules": len([r for r in self.validation_rules.values() if r.enabled]),
                "by_input_type": {
                    input_type.value: len([r for r in self.validation_rules.values() if r.input_type == input_type])
                    for input_type in InputType
                }
            },
            "validations": self.validation_stats.copy(),
            "violations": {
                "total": len(self.input_violations),
                "by_severity": {
                    severity.value: len([v for v in self.input_violations if v.severity == severity])
                    for severity in InputSeverity
                },
                "by_type": {
                    violation_type: len([v for v in self.input_violations if v.violation_type == violation_type])
                    for violation_type in ["invalid", "suspicious", "malicious", "blocked"]
                }
            },
            "cache": {
                "cached_types": len(self.rule_cache)
            }
        }


# Global input controller instance
input_controller = InputController()
