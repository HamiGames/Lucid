"""
Lucid API Gateway - Security Utilities
Security and cryptography utilities.

File: 03-api-gateway/utils/security.py
Lines: ~260
Purpose: Security utilities
Dependencies: cryptography, hashlib
"""

import hashlib
import secrets
import base64
import logging
from typing import Optional
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
from eth_account.messages import encode_defunct
from web3 import Web3

logger = logging.getLogger(__name__)


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple:
    """
    Hash password using PBKDF2.
    
    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)
        
    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_bytes(32)
        
    kdf = PBKDF2(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    key = kdf.derive(password.encode())
    
    # Encode as base64 for storage
    hashed = base64.b64encode(key).decode('utf-8')
    salt_encoded = base64.b64encode(salt).decode('utf-8')
    
    return hashed, salt_encoded


def verify_password(password: str, hashed_password: str, salt: str) -> bool:
    """
    Verify password against hash.
    
    Args:
        password: Plain text password to verify
        hashed_password: Base64 encoded hashed password
        salt: Base64 encoded salt
        
    Returns:
        True if password matches
    """
    try:
        # Decode salt
        salt_bytes = base64.b64decode(salt.encode('utf-8'))
        
        # Hash the provided password
        new_hash, _ = hash_password(password, salt_bytes)
        
        # Compare hashes
        return new_hash == hashed_password
        
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def generate_api_key() -> str:
    """
    Generate secure API key.
    
    Returns:
        Base64 encoded API key
    """
    # Generate 32 bytes of random data
    key_bytes = secrets.token_bytes(32)
    
    # Encode as base64
    api_key = base64.urlsafe_b64encode(key_bytes).decode('utf-8')
    
    return api_key


def hash_api_key(api_key: str) -> str:
    """
    Hash API key for storage.
    
    Args:
        api_key: API key to hash
        
    Returns:
        SHA256 hash of API key
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def verify_signature(
    message: str,
    signature: str,
    address: str
) -> bool:
    """
    Verify TRON signature.
    
    Args:
        message: Original message that was signed
        signature: Signature hex string
        address: Expected signer address
        
    Returns:
        True if signature is valid
    """
    try:
        # Create Web3 instance
        w3 = Web3()
        
        # Encode message
        message_hash = encode_defunct(text=message)
        
        # Recover address from signature
        recovered_address = w3.eth.account.recover_message(
            message_hash,
            signature=signature
        )
        
        # Compare addresses (case-insensitive)
        return recovered_address.lower() == address.lower()
        
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def generate_nonce() -> str:
    """
    Generate random nonce for authentication.
    
    Returns:
        Random nonce string
    """
    return secrets.token_hex(16)


def constant_time_compare(a: str, b: str) -> bool:
    """
    Constant time string comparison to prevent timing attacks.
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        True if strings match
    """
    if len(a) != len(b):
        return False
        
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
        
    return result == 0


def generate_session_token() -> str:
    """
    Generate secure session token.
    
    Returns:
        Session token string
    """
    return secrets.token_urlsafe(32)


def hash_data(data: str) -> str:
    """
    Hash data using SHA256.
    
    Args:
        data: Data to hash
        
    Returns:
        Hex digest of hash
    """
    return hashlib.sha256(data.encode()).hexdigest()


def generate_csrf_token() -> str:
    """
    Generate CSRF token.
    
    Returns:
        CSRF token string
    """
    return secrets.token_urlsafe(32)


def verify_csrf_token(token: str, stored_token: str) -> bool:
    """
    Verify CSRF token.
    
    Args:
        token: Token to verify
        stored_token: Expected token value
        
    Returns:
        True if token is valid
    """
    return constant_time_compare(token, stored_token)


class SecurityHeaders:
    """Security headers for HTTP responses."""
    
    @staticmethod
    def get_headers() -> dict:
        """
        Get recommended security headers.
        
        Returns:
            Dictionary of security headers
        """
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

