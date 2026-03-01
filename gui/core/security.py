# Path: gui/core/security.py
"""
Certificate pinning and security utilities for Lucid RDP GUI.
Provides comprehensive security features including certificate validation, 
onion address verification, and cryptographic utilities.
"""

import os
import ssl
import time
import hashlib
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import secrets
import base64
import re
import socket

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.x509.oid import NameOID, ExtensionOID
import blake3

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security level classifications"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CertificateValidationError(Exception):
    """Certificate validation related errors"""
    pass


class OnionValidationError(Exception):
    """Onion address validation related errors"""
    pass


class SecurityPolicyError(Exception):
    """Security policy related errors"""
    pass


@dataclass
class CertificateInfo:
    """Certificate information container"""
    subject: str
    issuer: str
    serial_number: str
    not_valid_before: str
    not_valid_after: str
    fingerprint_sha256: str
    fingerprint_sha1: str
    public_key_type: str
    public_key_size: Optional[int] = None
    extensions: List[str] = None
    is_self_signed: bool = False
    
    def __post_init__(self):
        if self.extensions is None:
            self.extensions = []


@dataclass
class OnionAddress:
    """Onion address information"""
    address: str
    version: int  # 2 or 3
    checksum: str
    is_valid: bool
    security_level: SecurityLevel = SecurityLevel.MEDIUM


@dataclass
class SecurityPolicy:
    """Security policy configuration"""
    # Certificate validation
    require_valid_certificate: bool = True
    require_certificate_pinning: bool = True
    allow_self_signed: bool = False
    certificate_cache_duration: int = 3600  # seconds
    
    # Onion address validation
    require_onion_addresses: bool = True
    allowed_onion_versions: List[int] = None  # None means all versions
    onion_address_whitelist: List[str] = None
    
    # Connection security
    require_https: bool = True
    minimum_tls_version: str = "TLSv1.2"
    cipher_suite_blacklist: List[str] = None
    
    # Network security
    connection_timeout: int = 30
    dns_timeout: int = 5
    max_redirects: int = 3
    
    # Logging and monitoring
    log_security_events: bool = True
    log_certificate_changes: bool = True
    security_event_threshold: int = 5  # events per minute
    
    def __post_init__(self):
        if self.allowed_onion_versions is None:
            self.allowed_onion_versions = [2, 3]
        if self.onion_address_whitelist is None:
            self.onion_address_whitelist = []
        if self.cipher_suite_blacklist is None:
            self.cipher_suite_blacklist = [
                "NULL", "EXPORT", "DES", "RC4", "MD5", "SHA1"
            ]


class CertificatePinner:
    """Certificate pinning implementation"""
    
    def __init__(self, pinning_file: Optional[Path] = None):
        self.pinning_file = pinning_file or Path.home() / ".lucid" / "certificates.txt"
        self.pinned_certificates: Dict[str, str] = {}
        self._load_pinned_certificates()
    
    def _load_pinned_certificates(self) -> None:
        """Load pinned certificates from file"""
        if not self.pinning_file or not self.pinning_file.exists():
            return
        
        try:
            with open(self.pinning_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            hostname, cert_hash = parts
                            self.pinned_certificates[hostname.lower()] = cert_hash.strip()
            
            logger.debug(f"Loaded {len(self.pinned_certificates)} pinned certificates")
            
        except Exception as e:
            logger.error(f"Failed to load pinned certificates: {e}")
    
    def save_pinned_certificates(self) -> None:
        """Save pinned certificates to file"""
        if not self.pinning_file:
            return
        
        try:
            self.pinning_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.pinning_file, 'w') as f:
                f.write("# Certificate pinning file for Lucid RDP GUI\n")
                f.write("# Format: hostname:sha256_hash\n")
                f.write("# Generated automatically - do not edit manually\n\n")
                
                for hostname, cert_hash in self.pinned_certificates.items():
                    f.write(f"{hostname}:{cert_hash}\n")
            
            logger.debug(f"Saved {len(self.pinned_certificates)} pinned certificates")
            
        except Exception as e:
            logger.error(f"Failed to save pinned certificates: {e}")
    
    def pin_certificate(self, hostname: str, certificate: x509.Certificate) -> str:
        """Pin a certificate for a hostname (TOFU - Trust On First Use)"""
        cert_hash = self._calculate_certificate_hash(certificate)
        self.pinned_certificates[hostname.lower()] = cert_hash
        self.save_pinned_certificates()
        logger.info(f"Pinned certificate for {hostname}: {cert_hash}")
        return cert_hash
    
    def verify_certificate_pinning(self, hostname: str, certificate: x509.Certificate) -> bool:
        """Verify certificate pinning for a hostname"""
        cert_hash = self._calculate_certificate_hash(certificate)
        hostname_lower = hostname.lower()
        
        if hostname_lower in self.pinned_certificates:
            expected_hash = self.pinned_certificates[hostname_lower]
            if cert_hash != expected_hash:
                logger.error(f"Certificate pinning failed for {hostname}")
                logger.error(f"Expected: {expected_hash}")
                logger.error(f"Got: {cert_hash}")
                return False
            logger.debug(f"Certificate pinning verified for {hostname}")
            return True
        else:
            # First time seeing this certificate - pin it (TOFU)
            self.pin_certificate(hostname, certificate)
            return True
    
    def _calculate_certificate_hash(self, certificate: x509.Certificate) -> str:
        """Calculate SHA-256 hash of certificate public key"""
        public_key = certificate.public_key()
        public_key_der = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return hashlib.sha256(public_key_der).hexdigest()
    
    def get_pinned_certificate_hash(self, hostname: str) -> Optional[str]:
        """Get pinned certificate hash for hostname"""
        return self.pinned_certificates.get(hostname.lower())
    
    def remove_pinned_certificate(self, hostname: str) -> bool:
        """Remove pinned certificate for hostname"""
        hostname_lower = hostname.lower()
        if hostname_lower in self.pinned_certificates:
            del self.pinned_certificates[hostname_lower]
            self.save_pinned_certificates()
            logger.info(f"Removed pinned certificate for {hostname}")
            return True
        return False


class OnionValidator:
    """Onion address validation and security assessment"""
    
    # Onion v2 pattern: 16 base32 chars + .onion
    ONION_V2_PATTERN = re.compile(r'^[a-z2-7]{16}\.onion$')
    
    # Onion v3 pattern: 56 base32 chars + .onion
    ONION_V3_PATTERN = re.compile(r'^[a-z2-7]{56}\.onion$')
    
    def __init__(self):
        self.known_onion_services: Set[str] = set()
        self.blacklisted_onions: Set[str] = set()
        self._load_onion_lists()
    
    def _load_onion_lists(self) -> None:
        """Load known and blacklisted onion services"""
        # This could be extended to load from external sources
        # For now, we'll keep it minimal
        pass
    
    def validate_onion_address(self, address: str) -> OnionAddress:
        """
        Validate onion address format and determine version.
        
        Args:
            address: Onion address to validate
            
        Returns:
            OnionAddress object with validation results
        """
        address = address.lower().strip()
        
        # Check onion v2 format
        if self.ONION_V2_PATTERN.match(address):
            return OnionAddress(
                address=address,
                version=2,
                checksum=self._calculate_onion_checksum(address),
                is_valid=True,
                security_level=SecurityLevel.MEDIUM  # v2 is deprecated but still functional
            )
        
        # Check onion v3 format
        if self.ONION_V3_PATTERN.match(address):
            return OnionAddress(
                address=address,
                version=3,
                checksum=self._calculate_onion_checksum(address),
                is_valid=True,
                security_level=SecurityLevel.HIGH  # v3 is current standard
            )
        
        # Invalid format
        return OnionAddress(
            address=address,
            version=0,
            checksum="",
            is_valid=False,
            security_level=SecurityLevel.LOW
        )
    
    def _calculate_onion_checksum(self, address: str) -> str:
        """Calculate checksum for onion address"""
        onion_part = address.replace('.onion', '')
        return hashlib.sha256(onion_part.encode()).hexdigest()[:8]
    
    def is_onion_address(self, address: str) -> bool:
        """Check if address is a valid onion address"""
        return self.validate_onion_address(address).is_valid
    
    def is_blacklisted_onion(self, address: str) -> bool:
        """Check if onion address is blacklisted"""
        return address.lower() in self.blacklisted_onions
    
    def add_blacklisted_onion(self, address: str) -> None:
        """Add onion address to blacklist"""
        self.blacklisted_onions.add(address.lower())
        logger.warning(f"Added {address} to onion blacklist")
    
    def remove_blacklisted_onion(self, address: str) -> bool:
        """Remove onion address from blacklist"""
        address_lower = address.lower()
        if address_lower in self.blacklisted_onions:
            self.blacklisted_onions.remove(address_lower)
            logger.info(f"Removed {address} from onion blacklist")
            return True
        return False


class SecurityValidator:
    """Comprehensive security validation"""
    
    def __init__(self, policy: Optional[SecurityPolicy] = None):
        self.policy = policy or SecurityPolicy()
        self.certificate_pinner = CertificatePinner()
        self.onion_validator = OnionValidator()
        self.security_events: List[Dict[str, Any]] = []
        self.event_timestamps: List[float] = []
    
    def validate_certificate(self, hostname: str, certificate: x509.Certificate) -> bool:
        """Validate certificate according to security policy"""
        try:
            # Check certificate validity period
            current_time = time.time()
            not_valid_before = certificate.not_valid_before.timestamp()
            not_valid_after = certificate.not_valid_after.timestamp()
            
            if current_time < not_valid_before:
                logger.error(f"Certificate for {hostname} not yet valid")
                return False
            
            if current_time > not_valid_after:
                logger.error(f"Certificate for {hostname} has expired")
                return False
            
            # Check if self-signed certificates are allowed
            if certificate.issuer == certificate.subject:
                if not self.policy.allow_self_signed:
                    logger.error(f"Self-signed certificate not allowed for {hostname}")
                    return False
                logger.warning(f"Self-signed certificate detected for {hostname}")
            
            # Verify certificate pinning
            if self.policy.require_certificate_pinning:
                if not self.certificate_pinner.verify_certificate_pinning(hostname, certificate):
                    self._log_security_event("certificate_pinning_failed", hostname)
                    return False
            
            logger.debug(f"Certificate validation passed for {hostname}")
            return True
            
        except Exception as e:
            logger.error(f"Certificate validation failed for {hostname}: {e}")
            self._log_security_event("certificate_validation_error", hostname, error=str(e))
            return False
    
    def validate_onion_address(self, address: str) -> Tuple[bool, Optional[str]]:
        """Validate onion address according to security policy"""
        try:
            onion_info = self.onion_validator.validate_onion_address(address)
            
            if not onion_info.is_valid:
                return False, f"Invalid onion address format: {address}"
            
            if self.policy.allowed_onion_versions and onion_info.version not in self.policy.allowed_onion_versions:
                return False, f"Onion version {onion_info.version} not allowed"
            
            if self.onion_validator.is_blacklisted_onion(address):
                return False, f"Onion address is blacklisted: {address}"
            
            if self.policy.onion_address_whitelist and address not in self.policy.onion_address_whitelist:
                return False, f"Onion address not in whitelist: {address}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Onion address validation failed for {address}: {e}")
            self._log_security_event("onion_validation_error", address, error=str(e))
            return False, f"Validation error: {e}"
    
    def validate_url_security(self, url: str) -> Tuple[bool, Optional[str]]:
        """Validate URL security according to policy"""
        try:
            from urllib.parse import urlparse
            
            parsed = urlparse(url)
            hostname = parsed.hostname
            
            if not hostname:
                return False, "No hostname in URL"
            
            # Check if onion address is required
            if self.policy.require_onion_addresses:
                is_valid, error = self.validate_onion_address(hostname)
                if not is_valid:
                    return False, error
            
            # Check HTTPS requirement
            if self.policy.require_https and parsed.scheme != 'https':
                return False, "HTTPS required but not used"
            
            # Check for clearnet addresses when onion is required
            if self.policy.require_onion_addresses and not self.onion_validator.is_onion_address(hostname):
                return False, "Onion address required but clearnet address provided"
            
            return True, None
            
        except Exception as e:
            logger.error(f"URL security validation failed for {url}: {e}")
            self._log_security_event("url_validation_error", url, error=str(e))
            return False, f"Validation error: {e}"
    
    def get_certificate_info(self, hostname: str, port: int = 443) -> Optional[CertificateInfo]:
        """Get certificate information for a hostname"""
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            with socket.create_connection((hostname, port), timeout=self.policy.connection_timeout) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert_der = ssock.getpeercert(binary_form=True)
                    cert = x509.load_der_x509_certificate(cert_der)
                    
                    # Extract certificate information
                    subject = cert.subject.rfc4514_string()
                    issuer = cert.issuer.rfc4514_string()
                    serial_number = str(cert.serial_number)
                    not_valid_before = cert.not_valid_before.isoformat()
                    not_valid_after = cert.not_valid_after.isoformat()
                    
                    # Calculate fingerprints
                    cert_der = cert.public_bytes(serialization.Encoding.DER)
                    fingerprint_sha256 = hashlib.sha256(cert_der).hexdigest()
                    fingerprint_sha1 = hashlib.sha1(cert_der).hexdigest()
                    
                    # Get public key information
                    public_key = cert.public_key()
                    if isinstance(public_key, rsa.RSAPublicKey):
                        public_key_type = "RSA"
                        public_key_size = public_key.key_size
                    elif isinstance(public_key, ed25519.Ed25519PublicKey):
                        public_key_type = "Ed25519"
                        public_key_size = None
                    else:
                        public_key_type = "Unknown"
                        public_key_size = None
                    
                    # Get extensions
                    extensions = []
                    for ext in cert.extensions:
                        extensions.append(f"{ext.oid._name}: {ext.value}")
                    
                    # Check if self-signed
                    is_self_signed = cert.issuer == cert.subject
                    
                    return CertificateInfo(
                        subject=subject,
                        issuer=issuer,
                        serial_number=serial_number,
                        not_valid_before=not_valid_before,
                        not_valid_after=not_valid_after,
                        fingerprint_sha256=fingerprint_sha256,
                        fingerprint_sha1=fingerprint_sha1,
                        public_key_type=public_key_type,
                        public_key_size=public_key_size,
                        extensions=extensions,
                        is_self_signed=is_self_signed
                    )
                    
        except Exception as e:
            logger.error(f"Failed to get certificate info for {hostname}:{port}: {e}")
            self._log_security_event("certificate_info_error", f"{hostname}:{port}", error=str(e))
            return None
    
    def _log_security_event(self, event_type: str, target: str, **kwargs) -> None:
        """Log security event with rate limiting"""
        if not self.policy.log_security_events:
            return
        
        current_time = time.time()
        
        # Clean old events (older than 1 minute)
        self.event_timestamps = [ts for ts in self.event_timestamps if current_time - ts < 60]
        
        # Check rate limit
        if len(self.event_timestamps) >= self.policy.security_event_threshold:
            logger.warning(f"Security event rate limit exceeded for {event_type}")
            return
        
        # Log the event
        event = {
            "timestamp": current_time,
            "type": event_type,
            "target": target,
            **kwargs
        }
        
        self.security_events.append(event)
        self.event_timestamps.append(current_time)
        
        logger.warning(f"Security event: {event_type} for {target}")
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security validation summary"""
        return {
            "policy": self.policy.__dict__,
            "pinned_certificates_count": len(self.certificate_pinner.pinned_certificates),
            "blacklisted_onions_count": len(self.onion_validator.blacklisted_onions),
            "recent_security_events": len([e for e in self.security_events if time.time() - e["timestamp"] < 3600]),
            "security_events_total": len(self.security_events)
        }


class CryptographicUtils:
    """Cryptographic utility functions"""
    
    @staticmethod
    def generate_secure_random(length: int = 32) -> bytes:
        """Generate cryptographically secure random bytes"""
        return secrets.token_bytes(length)
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate cryptographically secure random token (base64)"""
        return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode('ascii').rstrip('=')
    
    @staticmethod
    def derive_key(password: str, salt: bytes, length: int = 32) -> bytes:
        """Derive key from password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode())
    
    @staticmethod
    def derive_key_hkdf(key_material: bytes, salt: bytes, info: bytes, length: int = 32) -> bytes:
        """Derive key using HKDF"""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=length,
            salt=salt,
            info=info,
        )
        return hkdf.derive(key_material)
    
    @staticmethod
    def encrypt_data(data: bytes, key: bytes) -> Tuple[bytes, bytes]:
        """Encrypt data using ChaCha20-Poly1305"""
        nonce = secrets.token_bytes(12)
        cipher = ChaCha20Poly1305(key)
        encrypted_data = cipher.encrypt(nonce, data, None)
        return nonce, encrypted_data
    
    @staticmethod
    def decrypt_data(nonce: bytes, encrypted_data: bytes, key: bytes) -> bytes:
        """Decrypt data using ChaCha20-Poly1305"""
        cipher = ChaCha20Poly1305(key)
        return cipher.decrypt(nonce, encrypted_data, None)
    
    @staticmethod
    def calculate_hash(data: bytes, algorithm: str = "sha256") -> str:
        """Calculate hash of data"""
        if algorithm == "sha256":
            return hashlib.sha256(data).hexdigest()
        elif algorithm == "sha1":
            return hashlib.sha1(data).hexdigest()
        elif algorithm == "blake3":
            return blake3.blake3(data).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    @staticmethod
    def verify_hash(data: bytes, expected_hash: str, algorithm: str = "sha256") -> bool:
        """Verify hash of data"""
        actual_hash = CryptographicUtils.calculate_hash(data, algorithm)
        return actual_hash == expected_hash


# Global security validator instance
_security_validator: Optional[SecurityValidator] = None


def get_security_validator(policy: Optional[SecurityPolicy] = None) -> SecurityValidator:
    """Get global security validator instance"""
    global _security_validator
    
    if _security_validator is None:
        _security_validator = SecurityValidator(policy)
    
    return _security_validator


def cleanup_security_validator() -> None:
    """Cleanup global security validator"""
    global _security_validator
    _security_validator = None


# Convenience functions
def validate_onion_address(address: str) -> bool:
    """Validate onion address"""
    validator = OnionValidator()
    return validator.validate_onion_address(address).is_valid


def validate_certificate_pinning(hostname: str, certificate: x509.Certificate) -> bool:
    """Validate certificate pinning"""
    pinner = CertificatePinner()
    return pinner.verify_certificate_pinning(hostname, certificate)


def get_certificate_hash(certificate: x509.Certificate) -> str:
    """Get certificate hash for pinning"""
    public_key = certificate.public_key()
    public_key_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return hashlib.sha256(public_key_der).hexdigest()


def is_secure_url(url: str, require_onion: bool = True, require_https: bool = True) -> Tuple[bool, Optional[str]]:
    """Check if URL meets security requirements"""
    validator = get_security_validator()
    policy = validator.policy
    policy.require_onion_addresses = require_onion
    policy.require_https = require_https
    
    return validator.validate_url_security(url)
