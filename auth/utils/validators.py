"""
Lucid Authentication Service - Input Validators
"""

import re
from typing import Optional, Tuple
import jwt
import logging

logger = logging.getLogger(__name__)


def validate_tron_address(address: str) -> Tuple[bool, Optional[str]]:
    """
    Validate TRON address format
    
    TRON addresses:
    - Start with 'T' (mainnet) or other prefixes for testnets
    - Are 34 characters long
    - Use Base58 encoding
    
    Args:
        address: TRON address to validate
        
    Returns:
        (is_valid, error_message)
    """
    if not address:
        return False, "TRON address is required"
    
    if not isinstance(address, str):
        return False, "TRON address must be a string"
    
    # Check prefix
    if not address.startswith('T'):
        return False, "TRON address must start with 'T' for mainnet"
    
    # Check length
    if len(address) != 34:
        return False, f"TRON address must be 34 characters, got {len(address)}"
    
    # Check characters (Base58: alphanumeric excluding 0, O, I, l)
    base58_pattern = r'^[1-9A-HJ-NP-Za-km-z]+$'
    if not re.match(base58_pattern, address):
        return False, "TRON address contains invalid characters"
    
    # Optional: Verify checksum (requires tronpy)
    try:
        from tronpy import keys
        keys.to_hex_address(address)  # Will raise if invalid
        return True, None
    except ImportError:
        # If tronpy not available, basic validation passed
        logger.debug("tronpy not available for checksum verification")
        return True, None
    except Exception as e:
        return False, f"Invalid TRON address checksum: {str(e)}"


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email format
    
    Args:
        email: Email address to validate
        
    Returns:
        (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    if not isinstance(email, str):
        return False, "Email must be a string"
    
    # Basic email regex pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(email_pattern, email):
        return False, "Invalid email format"
    
    # Check length
    if len(email) > 254:
        return False, "Email too long (max 254 characters)"
    
    # Check local part length (before @)
    local_part = email.split('@')[0]
    if len(local_part) > 64:
        return False, "Email local part too long (max 64 characters)"
    
    return True, None


def validate_jwt_token(token: str) -> Tuple[bool, Optional[str]]:
    """
    Validate JWT token format (without signature verification)
    
    Args:
        token: JWT token string
        
    Returns:
        (is_valid, error_message)
    """
    if not token:
        return False, "Token is required"
    
    if not isinstance(token, str):
        return False, "Token must be a string"
    
    # JWT should have 3 parts separated by dots
    parts = token.split('.')
    if len(parts) != 3:
        return False, f"Invalid JWT format: expected 3 parts, got {len(parts)}"
    
    # Try to decode without verification (just format check)
    try:
        jwt.decode(token, options={"verify_signature": False})
        return True, None
    except jwt.DecodeError as e:
        return False, f"Invalid JWT format: {str(e)}"
    except Exception as e:
        return False, f"JWT validation error: {str(e)}"


def validate_password(password: str, min_length: int = 12) -> Tuple[bool, Optional[str]]:
    """
    Validate password strength
    
    Requirements:
    - Minimum length
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    
    Args:
        password: Password to validate
        min_length: Minimum password length
        
    Returns:
        (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, None


def validate_signature(signature: str) -> Tuple[bool, Optional[str]]:
    """
    Validate signature format
    
    Args:
        signature: Signature hex string
        
    Returns:
        (is_valid, error_message)
    """
    if not signature:
        return False, "Signature is required"
    
    if not isinstance(signature, str):
        return False, "Signature must be a string"
    
    # Remove 0x prefix if present
    sig = signature[2:] if signature.startswith('0x') else signature
    
    # Check if hex
    if not re.match(r'^[0-9a-fA-F]+$', sig):
        return False, "Signature must be a valid hex string"
    
    # ECDSA signature should be 65 bytes (130 hex chars)
    # Or 64 bytes (128 hex chars) without recovery id
    if len(sig) not in [128, 130]:
        return False, f"Invalid signature length: expected 128 or 130 hex chars, got {len(sig)}"
    
    return True, None


def validate_user_id(user_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate user ID format
    
    Args:
        user_id: User ID to validate
        
    Returns:
        (is_valid, error_message)
    """
    if not user_id:
        return False, "User ID is required"
    
    if not isinstance(user_id, str):
        return False, "User ID must be a string"
    
    # User ID should be alphanumeric with optional underscores/hyphens
    if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
        return False, "User ID can only contain alphanumeric characters, underscores, and hyphens"
    
    # Check length
    if len(user_id) < 3:
        return False, "User ID must be at least 3 characters"
    
    if len(user_id) > 64:
        return False, "User ID must be at most 64 characters"
    
    return True, None


def validate_session_id(session_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate session ID format
    
    Args:
        session_id: Session ID to validate
        
    Returns:
        (is_valid, error_message)
    """
    if not session_id:
        return False, "Session ID is required"
    
    if not isinstance(session_id, str):
        return False, "Session ID must be a string"
    
    # Session ID should be alphanumeric with optional underscores/hyphens
    if not re.match(r'^[a-zA-Z0-9_-]+$', session_id):
        return False, "Session ID can only contain alphanumeric characters, underscores, and hyphens"
    
    return True, None


def sanitize_input(input_str: str, max_length: Optional[int] = None) -> str:
    """
    Sanitize user input by removing potentially dangerous characters
    
    Args:
        input_str: Input string to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized string
    """
    if not input_str:
        return ""
    
    # Remove null bytes
    sanitized = input_str.replace('\x00', '')
    
    # Trim whitespace
    sanitized = sanitized.strip()
    
    # Truncate if needed
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate URL format
    
    Args:
        url: URL to validate
        
    Returns:
        (is_valid, error_message)
    """
    if not url:
        return False, "URL is required"
    
    if not isinstance(url, str):
        return False, "URL must be a string"
    
    # Basic URL regex
    url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
    
    if not re.match(url_pattern, url):
        return False, "Invalid URL format"
    
    return True, None

