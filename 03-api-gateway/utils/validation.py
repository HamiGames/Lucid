"""
Lucid API Gateway - Validation Utilities
Input validation and sanitization.

File: 03-api-gateway/utils/validation.py
Lines: ~240
Purpose: Input validation
Dependencies: Pydantic, re
"""

import re
import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, ValidationError, validator
import uuid

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Validation error exception."""
    pass


def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid
    """
    if not email:
        return False
        
    # Basic email regex pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    return bool(re.match(pattern, email))


def validate_tron_address(address: str) -> bool:
    """
    Validate TRON wallet address format.
    
    Args:
        address: TRON address to validate
        
    Returns:
        True if valid
    """
    if not address:
        return False
        
    # TRON addresses start with 'T' and are 34 characters long
    if not address.startswith('T'):
        return False
        
    if len(address) != 34:
        return False
        
    # Check if it's base58 encoded
    base58_pattern = r'^[1-9A-HJ-NP-Za-km-z]+$'
    
    return bool(re.match(base58_pattern, address))


def validate_session_id(session_id: str) -> bool:
    """
    Validate session ID format.
    
    Args:
        session_id: Session ID to validate
        
    Returns:
        True if valid
    """
    if not session_id:
        return False
        
    # Session IDs should be valid UUIDs or custom format
    try:
        # Try parsing as UUID
        uuid.UUID(session_id)
        return True
    except ValueError:
        # Check custom format (alphanumeric, hyphens, underscores)
        pattern = r'^[a-zA-Z0-9_-]+$'
        if re.match(pattern, session_id) and len(session_id) >= 8:
            return True
        return False


def validate_user_id(user_id: str) -> bool:
    """
    Validate user ID format.
    
    Args:
        user_id: User ID to validate
        
    Returns:
        True if valid
    """
    if not user_id:
        return False
        
    try:
        # Try parsing as UUID
        uuid.UUID(user_id)
        return True
    except ValueError:
        # Check custom format
        pattern = r'^[a-zA-Z0-9_-]+$'
        if re.match(pattern, user_id) and len(user_id) >= 8:
            return True
        return False


def validate_port(port: int) -> bool:
    """
    Validate port number.
    
    Args:
        port: Port number to validate
        
    Returns:
        True if valid
    """
    return isinstance(port, int) and 1 <= port <= 65535


def validate_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid
    """
    if not url:
        return False
        
    # Basic URL pattern
    pattern = r'^https?://[a-zA-Z0-9.-]+(?:\:[0-9]{1,5})?(?:/.*)?$'
    
    return bool(re.match(pattern, url))


def validate_ipv4(ip: str) -> bool:
    """
    Validate IPv4 address.
    
    Args:
        ip: IP address to validate
        
    Returns:
        True if valid
    """
    if not ip:
        return False
        
    pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    
    if not re.match(pattern, ip):
        return False
        
    # Check each octet is 0-255
    octets = ip.split('.')
    for octet in octets:
        if int(octet) > 255:
            return False
            
    return True


def sanitize_string(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input string.
    
    Args:
        text: Text to sanitize
        max_length: Maximum allowed length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
        
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Trim whitespace
    text = text.strip()
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
        
    return text


def validate_pagination(skip: int, limit: int) -> tuple:
    """
    Validate and normalize pagination parameters.
    
    Args:
        skip: Number of items to skip
        limit: Maximum number of items to return
        
    Returns:
        Tuple of (skip, limit) with normalized values
    """
    # Ensure non-negative
    skip = max(0, skip)
    
    # Limit maximum page size
    limit = max(1, min(limit, 1000))
    
    return skip, limit


def validate_request_data(
    data: Dict[str, Any],
    model: BaseModel
) -> BaseModel:
    """
    Validate request data against Pydantic model.
    
    Args:
        data: Request data dictionary
        model: Pydantic model class
        
    Returns:
        Validated model instance
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        return model(**data)
    except ValidationError as e:
        logger.warning(f"Request validation error: {e}")
        raise ValidationError(f"Invalid request data: {e}")


def validate_file_size(size_bytes: int, max_size_mb: int = 100) -> bool:
    """
    Validate file size.
    
    Args:
        size_bytes: File size in bytes
        max_size_mb: Maximum allowed size in MB
        
    Returns:
        True if valid
    """
    max_bytes = max_size_mb * 1024 * 1024
    return 0 < size_bytes <= max_bytes


def validate_chunk_size(size_bytes: int) -> bool:
    """
    Validate chunk size (max 10MB).
    
    Args:
        size_bytes: Chunk size in bytes
        
    Returns:
        True if valid
    """
    max_chunk_size = 10 * 1024 * 1024  # 10MB
    return 0 < size_bytes <= max_chunk_size

