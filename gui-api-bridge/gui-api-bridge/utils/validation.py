"""
URL Validation Utilities
File: gui-api-bridge/gui-api-bridge/utils/validation.py
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def validate_service_url(url: str) -> bool:
    """
    Validate service URL
    
    Args:
        url: URL to validate
    
    Returns:
        True if URL is valid, False otherwise
    """
    if not url:
        logger.error("URL is empty")
        return False
    
    if "localhost" in url or "127.0.0.1" in url:
        logger.warning(f"URL contains localhost/127.0.0.1: {url}")
        # Still valid, but log warning
        return True
    
    if not url.startswith("http://") and not url.startswith("https://"):
        logger.error(f"URL does not start with http:// or https://: {url}")
        return False
    
    return True


def validate_session_id(session_id: str) -> bool:
    """
    Validate session ID format
    
    Args:
        session_id: Session ID to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not session_id:
        return False
    
    # Session IDs typically are UUIDs or hex strings
    if len(session_id) < 8:
        return False
    
    return True


def validate_address(address: str) -> bool:
    """
    Validate wallet address format
    
    Args:
        address: Address to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not address:
        return False
    
    # Basic validation - should be non-empty string
    if len(address) < 10:
        return False
    
    return True
