"""
Security validation logic for Lucid project.

This module provides comprehensive security validation functionality including:
- Security policy validation
- Authentication validation
- Authorization validation
- Input validation
- Security configuration validation
- Cryptographic validation
"""

import os
import re
import hashlib
import hmac
import secrets
import base64
import logging
from typing import Any, Dict, List, Optional, Union, Tuple, Callable
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass
import ipaddress
import socket
import ssl
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.hmac import HMAC
from cryptography.hazmat.primitives.signatures import ed25519
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature, InvalidKey
from pydantic import BaseModel, Field, validator, root_validator
from pydantic.types import SecretStr

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security level classifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"


class ValidationResult(Enum):
    """Validation result enumeration."""
    VALID = "valid"
    INVALID = "invalid"
    WARNING = "warning"
    ERROR = "error"


class SecurityValidationError(Exception):
    """Base exception for security validation errors."""
    pass


class AuthenticationError(SecurityValidationError):
    """Raised when authentication validation fails."""
    pass


class AuthorizationError(SecurityValidationError):
    """Raised when authorization validation fails."""
    pass


class InputValidationError(SecurityValidationError):
    """Raised when input validation fails."""
    pass


class CryptographicValidationError(SecurityValidationError):
    """Raised when cryptographic validation fails."""
    pass


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    result: ValidationResult
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class SecurityPolicy:
    """Security policy configuration."""
    name: str
    description: str
    rules: List[Dict[str, Any]]
    severity: SecurityLevel
    enabled: bool = True
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)


class PasswordValidator:
    """Password validation utility."""
    
    def __init__(self, min_length: int = 8, max_length: int = 128):
        self.min_length = min_length
        self.max_length = max_length
        self.required_patterns = [
            (r'[A-Z]', 'uppercase letter'),
            (r'[a-z]', 'lowercase letter'),
            (r'[0-9]', 'digit'),
            (r'[^A-Za-z0-9]', 'special character')
        ]
    
    def validate(self, password: str) -> ValidationResult:
        """Validate password strength."""
        errors = []
        warnings = []
        
        # Check length
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        elif len(password) > self.max_length:
            errors.append(f"Password must be no more than {self.max_length} characters long")
        
        # Check required patterns
        for pattern, description in self.required_patterns:
            if not re.search(pattern, password):
                warnings.append(f"Password should contain at least one {description}")
        
        # Check for common patterns
        if self._is_common_password(password):
            errors.append("Password is too common")
        
        if self._has_sequential_chars(password):
            warnings.append("Password contains sequential characters")
        
        if self._has_repeated_chars(password):
            warnings.append("Password contains repeated characters")
        
        if errors:
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.ERROR,
                message="Password validation failed",
                details={'errors': errors, 'warnings': warnings}
            )
        elif warnings:
            return ValidationResult(
                is_valid=True,
                result=ValidationResult.WARNING,
                message="Password validation passed with warnings",
                details={'warnings': warnings}
            )
        else:
            return ValidationResult(
                is_valid=True,
                result=ValidationResult.VALID,
                message="Password validation passed"
            )
    
    def _is_common_password(self, password: str) -> bool:
        """Check if password is common."""
        common_passwords = [
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey'
        ]
        return password.lower() in common_passwords
    
    def _has_sequential_chars(self, password: str) -> bool:
        """Check for sequential characters."""
        for i in range(len(password) - 2):
            if (ord(password[i+1]) == ord(password[i]) + 1 and 
                ord(password[i+2]) == ord(password[i]) + 2):
                return True
        return False
    
    def _has_repeated_chars(self, password: str) -> bool:
        """Check for repeated characters."""
        for i in range(len(password) - 2):
            if password[i] == password[i+1] == password[i+2]:
                return True
        return False


class InputValidator:
    """Input validation utility."""
    
    @staticmethod
    def validate_email(email: str) -> ValidationResult:
        """Validate email address."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(pattern, email):
            return ValidationResult(
                is_valid=True,
                result=ValidationResult.VALID,
                message="Valid email address"
            )
        else:
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.INVALID,
                message="Invalid email address format"
            )
    
    @staticmethod
    def validate_url(url: str) -> ValidationResult:
        """Validate URL."""
        try:
            result = urlparse(url)
            if all([result.scheme, result.netloc]):
                return ValidationResult(
                    is_valid=True,
                    result=ValidationResult.VALID,
                    message="Valid URL"
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    result=ValidationResult.INVALID,
                    message="Invalid URL format"
                )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.INVALID,
                message=f"URL validation error: {str(e)}"
            )
    
    @staticmethod
    def validate_ip_address(ip: str) -> ValidationResult:
        """Validate IP address."""
        try:
            ipaddress.ip_address(ip)
            return ValidationResult(
                is_valid=True,
                result=ValidationResult.VALID,
                message="Valid IP address"
            )
        except ValueError:
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.INVALID,
                message="Invalid IP address format"
            )
    
    @staticmethod
    def validate_port(port: Union[int, str]) -> ValidationResult:
        """Validate port number."""
        try:
            port_num = int(port)
            if 1 <= port_num <= 65535:
                return ValidationResult(
                    is_valid=True,
                    result=ValidationResult.VALID,
                    message="Valid port number"
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    result=ValidationResult.INVALID,
                    message="Port number must be between 1 and 65535"
                )
        except ValueError:
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.INVALID,
                message="Invalid port number format"
            )
    
    @staticmethod
    def validate_hostname(hostname: str) -> ValidationResult:
        """Validate hostname."""
        if len(hostname) > 253:
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.INVALID,
                message="Hostname too long"
            )
        
        if hostname.endswith('.'):
            hostname = hostname[:-1]
        
        if not hostname:
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.INVALID,
                message="Empty hostname"
            )
        
        # Check each label
        for label in hostname.split('.'):
            if not label or len(label) > 63:
                return ValidationResult(
                    is_valid=False,
                    result=ValidationResult.INVALID,
                    message="Invalid hostname label"
                )
            
            if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', label):
                return ValidationResult(
                    is_valid=False,
                    result=ValidationResult.INVALID,
                    message="Invalid hostname characters"
                )
        
        return ValidationResult(
            is_valid=True,
            result=ValidationResult.VALID,
            message="Valid hostname"
        )


class CryptographicValidator:
    """Cryptographic validation utility."""
    
    @staticmethod
    def validate_private_key(key_data: bytes, key_type: str = "RSA") -> ValidationResult:
        """Validate private key format and strength."""
        try:
            if key_type.upper() == "RSA":
                private_key = serialization.load_pem_private_key(
                    key_data, password=None, backend=default_backend()
                )
                if isinstance(private_key, rsa.RSAPrivateKey):
                    key_size = private_key.key_size
                    if key_size < 2048:
                        return ValidationResult(
                            is_valid=False,
                            result=ValidationResult.WARNING,
                            message=f"RSA key size {key_size} is below recommended minimum of 2048 bits"
                        )
                    return ValidationResult(
                        is_valid=True,
                        result=ValidationResult.VALID,
                        message=f"Valid RSA private key ({key_size} bits)"
                    )
            
            elif key_type.upper() == "ED25519":
                private_key = serialization.load_pem_private_key(
                    key_data, password=None, backend=default_backend()
                )
                if isinstance(private_key, ed25519.Ed25519PrivateKey):
                    return ValidationResult(
                        is_valid=True,
                        result=ValidationResult.VALID,
                        message="Valid Ed25519 private key"
                    )
            
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.INVALID,
                message=f"Invalid {key_type} private key"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.INVALID,
                message=f"Private key validation error: {str(e)}"
            )
    
    @staticmethod
    def validate_public_key(key_data: bytes, key_type: str = "RSA") -> ValidationResult:
        """Validate public key format and strength."""
        try:
            if key_type.upper() == "RSA":
                public_key = serialization.load_pem_public_key(
                    key_data, backend=default_backend()
                )
                if isinstance(public_key, rsa.RSAPublicKey):
                    key_size = public_key.key_size
                    if key_size < 2048:
                        return ValidationResult(
                            is_valid=False,
                            result=ValidationResult.WARNING,
                            message=f"RSA key size {key_size} is below recommended minimum of 2048 bits"
                        )
                    return ValidationResult(
                        is_valid=True,
                        result=ValidationResult.VALID,
                        message=f"Valid RSA public key ({key_size} bits)"
                    )
            
            elif key_type.upper() == "ED25519":
                public_key = serialization.load_pem_public_key(
                    key_data, backend=default_backend()
                )
                if isinstance(public_key, ed25519.Ed25519PublicKey):
                    return ValidationResult(
                        is_valid=True,
                        result=ValidationResult.VALID,
                        message="Valid Ed25519 public key"
                    )
            
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.INVALID,
                message=f"Invalid {key_type} public key"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.INVALID,
                message=f"Public key validation error: {str(e)}"
            )
    
    @staticmethod
    def validate_certificate(cert_data: bytes) -> ValidationResult:
        """Validate X.509 certificate."""
        try:
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            # Check validity period
            now = datetime.now(timezone.utc)
            if now < cert.not_valid_before.replace(tzinfo=timezone.utc):
                return ValidationResult(
                    is_valid=False,
                    result=ValidationResult.INVALID,
                    message="Certificate not yet valid"
                )
            
            if now > cert.not_valid_after.replace(tzinfo=timezone.utc):
                return ValidationResult(
                    is_valid=False,
                    result=ValidationResult.INVALID,
                    message="Certificate has expired"
                )
            
            # Check if certificate expires soon (within 30 days)
            expiry_date = cert.not_valid_after.replace(tzinfo=timezone.utc)
            if expiry_date - now < timedelta(days=30):
                return ValidationResult(
                    is_valid=True,
                    result=ValidationResult.WARNING,
                    message=f"Certificate expires soon: {expiry_date.isoformat()}"
                )
            
            return ValidationResult(
                is_valid=True,
                result=ValidationResult.VALID,
                message="Valid certificate"
            )
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.INVALID,
                message=f"Certificate validation error: {str(e)}"
            )
    
    @staticmethod
    def validate_signature(data: bytes, signature: bytes, public_key: bytes) -> ValidationResult:
        """Validate digital signature."""
        try:
            public_key_obj = serialization.load_pem_public_key(
                public_key, backend=default_backend()
            )
            
            public_key_obj.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return ValidationResult(
                is_valid=True,
                result=ValidationResult.VALID,
                message="Valid signature"
            )
            
        except InvalidSignature:
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.INVALID,
                message="Invalid signature"
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.INVALID,
                message=f"Signature validation error: {str(e)}"
            )


class SecurityPolicyValidator:
    """Security policy validation utility."""
    
    def __init__(self):
        self.policies: Dict[str, SecurityPolicy] = {}
        self._load_default_policies()
    
    def _load_default_policies(self) -> None:
        """Load default security policies."""
        default_policies = [
            SecurityPolicy(
                name="password_policy",
                description="Password security requirements",
                rules=[
                    {"type": "min_length", "value": 8},
                    {"type": "max_length", "value": 128},
                    {"type": "require_uppercase", "value": True},
                    {"type": "require_lowercase", "value": True},
                    {"type": "require_digits", "value": True},
                    {"type": "require_special", "value": True}
                ],
                severity=SecurityLevel.HIGH
            ),
            SecurityPolicy(
                name="input_validation",
                description="Input validation requirements",
                rules=[
                    {"type": "max_string_length", "value": 10000},
                    {"type": "sanitize_html", "value": True},
                    {"type": "validate_email", "value": True},
                    {"type": "validate_url", "value": True}
                ],
                severity=SecurityLevel.MEDIUM
            ),
            SecurityPolicy(
                name="cryptographic_requirements",
                description="Cryptographic security requirements",
                rules=[
                    {"type": "min_key_size", "value": 2048},
                    {"type": "require_https", "value": True},
                    {"type": "certificate_validation", "value": True}
                ],
                severity=SecurityLevel.HIGH
            )
        ]
        
        for policy in default_policies:
            self.policies[policy.name] = policy
    
    def add_policy(self, policy: SecurityPolicy) -> None:
        """Add a security policy."""
        self.policies[policy.name] = policy
    
    def remove_policy(self, policy_name: str) -> bool:
        """Remove a security policy."""
        if policy_name in self.policies:
            del self.policies[policy_name]
            return True
        return False
    
    def validate_against_policy(self, policy_name: str, data: Any) -> ValidationResult:
        """Validate data against a specific policy."""
        if policy_name not in self.policies:
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.ERROR,
                message=f"Policy '{policy_name}' not found"
            )
        
        policy = self.policies[policy_name]
        if not policy.enabled:
            return ValidationResult(
                is_valid=True,
                result=ValidationResult.VALID,
                message=f"Policy '{policy_name}' is disabled"
            )
        
        errors = []
        warnings = []
        
        for rule in policy.rules:
            rule_result = self._validate_rule(rule, data)
            if not rule_result.is_valid:
                if policy.severity == SecurityLevel.HIGH:
                    errors.append(rule_result.message)
                else:
                    warnings.append(rule_result.message)
        
        if errors:
            return ValidationResult(
                is_valid=False,
                result=ValidationResult.ERROR,
                message=f"Policy '{policy_name}' validation failed",
                details={'errors': errors, 'warnings': warnings}
            )
        elif warnings:
            return ValidationResult(
                is_valid=True,
                result=ValidationResult.WARNING,
                message=f"Policy '{policy_name}' validation passed with warnings",
                details={'warnings': warnings}
            )
        else:
            return ValidationResult(
                is_valid=True,
                result=ValidationResult.VALID,
                message=f"Policy '{policy_name}' validation passed"
            )
    
    def _validate_rule(self, rule: Dict[str, Any], data: Any) -> ValidationResult:
        """Validate a single rule."""
        rule_type = rule.get('type')
        rule_value = rule.get('value')
        
        if rule_type == 'min_length' and isinstance(data, str):
            if len(data) < rule_value:
                return ValidationResult(
                    is_valid=False,
                    result=ValidationResult.INVALID,
                    message=f"String length {len(data)} is below minimum {rule_value}"
                )
        
        elif rule_type == 'max_length' and isinstance(data, str):
            if len(data) > rule_value:
                return ValidationResult(
                    is_valid=False,
                    result=ValidationResult.INVALID,
                    message=f"String length {len(data)} exceeds maximum {rule_value}"
                )
        
        elif rule_type == 'require_uppercase' and isinstance(data, str):
            if rule_value and not re.search(r'[A-Z]', data):
                return ValidationResult(
                    is_valid=False,
                    result=ValidationResult.INVALID,
                    message="String must contain uppercase letters"
                )
        
        elif rule_type == 'require_lowercase' and isinstance(data, str):
            if rule_value and not re.search(r'[a-z]', data):
                return ValidationResult(
                    is_valid=False,
                    result=ValidationResult.INVALID,
                    message="String must contain lowercase letters"
                )
        
        elif rule_type == 'require_digits' and isinstance(data, str):
            if rule_value and not re.search(r'[0-9]', data):
                return ValidationResult(
                    is_valid=False,
                    result=ValidationResult.INVALID,
                    message="String must contain digits"
                )
        
        elif rule_type == 'require_special' and isinstance(data, str):
            if rule_value and not re.search(r'[^A-Za-z0-9]', data):
                return ValidationResult(
                    is_valid=False,
                    result=ValidationResult.INVALID,
                    message="String must contain special characters"
                )
        
        elif rule_type == 'validate_email' and isinstance(data, str):
            email_result = InputValidator.validate_email(data)
            if not email_result.is_valid:
                return email_result
        
        elif rule_type == 'validate_url' and isinstance(data, str):
            url_result = InputValidator.validate_url(data)
            if not url_result.is_valid:
                return url_result
        
        return ValidationResult(
            is_valid=True,
            result=ValidationResult.VALID,
            message="Rule validation passed"
        )


class SecurityValidator:
    """Main security validation class."""
    
    def __init__(self):
        self.password_validator = PasswordValidator()
        self.input_validator = InputValidator()
        self.crypto_validator = CryptographicValidator()
        self.policy_validator = SecurityPolicyValidator()
    
    def validate_password(self, password: str) -> ValidationResult:
        """Validate password security."""
        return self.password_validator.validate(password)
    
    def validate_email(self, email: str) -> ValidationResult:
        """Validate email address."""
        return self.input_validator.validate_email(email)
    
    def validate_url(self, url: str) -> ValidationResult:
        """Validate URL."""
        return self.input_validator.validate_url(url)
    
    def validate_ip_address(self, ip: str) -> ValidationResult:
        """Validate IP address."""
        return self.input_validator.validate_ip_address(ip)
    
    def validate_port(self, port: Union[int, str]) -> ValidationResult:
        """Validate port number."""
        return self.input_validator.validate_port(port)
    
    def validate_hostname(self, hostname: str) -> ValidationResult:
        """Validate hostname."""
        return self.input_validator.validate_hostname(hostname)
    
    def validate_private_key(self, key_data: bytes, key_type: str = "RSA") -> ValidationResult:
        """Validate private key."""
        return self.crypto_validator.validate_private_key(key_data, key_type)
    
    def validate_public_key(self, key_data: bytes, key_type: str = "RSA") -> ValidationResult:
        """Validate public key."""
        return self.crypto_validator.validate_public_key(key_data, key_type)
    
    def validate_certificate(self, cert_data: bytes) -> ValidationResult:
        """Validate certificate."""
        return self.crypto_validator.validate_certificate(cert_data)
    
    def validate_signature(self, data: bytes, signature: bytes, public_key: bytes) -> ValidationResult:
        """Validate digital signature."""
        return self.crypto_validator.validate_signature(data, signature, public_key)
    
    def validate_against_policy(self, policy_name: str, data: Any) -> ValidationResult:
        """Validate data against security policy."""
        return self.policy_validator.validate_against_policy(policy_name, data)
    
    def add_security_policy(self, policy: SecurityPolicy) -> None:
        """Add a security policy."""
        self.policy_validator.add_policy(policy)
    
    def remove_security_policy(self, policy_name: str) -> bool:
        """Remove a security policy."""
        return self.policy_validator.remove_policy(policy_name)
    
    def get_security_policies(self) -> Dict[str, SecurityPolicy]:
        """Get all security policies."""
        return self.policy_validator.policies.copy()


# Global security validator instance
_security_validator: Optional[SecurityValidator] = None


def get_security_validator() -> SecurityValidator:
    """Get global security validator instance."""
    global _security_validator
    if _security_validator is None:
        _security_validator = SecurityValidator()
    return _security_validator


def validate_password(password: str) -> ValidationResult:
    """Validate password security."""
    return get_security_validator().validate_password(password)


def validate_email(email: str) -> ValidationResult:
    """Validate email address."""
    return get_security_validator().validate_email(email)


def validate_url(url: str) -> ValidationResult:
    """Validate URL."""
    return get_security_validator().validate_url(url)


def validate_ip_address(ip: str) -> ValidationResult:
    """Validate IP address."""
    return get_security_validator().validate_ip_address(ip)


def validate_port(port: Union[int, str]) -> ValidationResult:
    """Validate port number."""
    return get_security_validator().validate_port(port)


def validate_hostname(hostname: str) -> ValidationResult:
    """Validate hostname."""
    return get_security_validator().validate_hostname(hostname)


def validate_private_key(key_data: bytes, key_type: str = "RSA") -> ValidationResult:
    """Validate private key."""
    return get_security_validator().validate_private_key(key_data, key_type)


def validate_public_key(key_data: bytes, key_type: str = "RSA") -> ValidationResult:
    """Validate public key."""
    return get_security_validator().validate_public_key(key_data, key_type)


def validate_certificate(cert_data: bytes) -> ValidationResult:
    """Validate certificate."""
    return get_security_validator().validate_certificate(cert_data)


def validate_signature(data: bytes, signature: bytes, public_key: bytes) -> ValidationResult:
    """Validate digital signature."""
    return get_security_validator().validate_signature(data, signature, public_key)


def validate_against_policy(policy_name: str, data: Any) -> ValidationResult:
    """Validate data against security policy."""
    return get_security_validator().validate_against_policy(policy_name, data)
