"""
Lucid Authentication Service - JWT Handler Utilities
"""

import jwt
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def encode_jwt(
    payload: Dict[str, Any],
    secret_key: str,
    algorithm: str = "HS256",
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Encode JWT token
    
    Args:
        payload: Token payload
        secret_key: Secret key for signing
        algorithm: JWT algorithm (default HS256)
        expires_delta: Expiration time delta
        
    Returns:
        Encoded JWT token string
    """
    try:
        # Add timestamps if not present
        if 'iat' not in payload:
            payload['iat'] = datetime.utcnow()
        
        if expires_delta and 'exp' not in payload:
            payload['exp'] = datetime.utcnow() + expires_delta
        
        # Encode token
        token = jwt.encode(payload, secret_key, algorithm=algorithm)
        
        return token
        
    except Exception as e:
        logger.error(f"Error encoding JWT: {e}")
        raise


def decode_jwt(
    token: str,
    secret_key: str,
    algorithms: list = None,
    verify: bool = True
) -> Dict[str, Any]:
    """
    Decode JWT token
    
    Args:
        token: JWT token string
        secret_key: Secret key for verification
        algorithms: List of allowed algorithms
        verify: Whether to verify signature
        
    Returns:
        Decoded payload dictionary
    """
    try:
        if algorithms is None:
            algorithms = ["HS256"]
        
        options = {
            "verify_signature": verify,
            "verify_exp": verify,
            "verify_nbf": verify,
            "verify_iat": verify,
            "verify_aud": False,
            "require_exp": False,
            "require_iat": False,
            "require_nbf": False
        }
        
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=algorithms,
            options=options
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise
    except Exception as e:
        logger.error(f"Error decoding JWT: {e}")
        raise


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get token expiry time without verification
    
    Args:
        token: JWT token string
        
    Returns:
        Expiry datetime or None
    """
    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        
        if 'exp' in payload:
            return datetime.fromtimestamp(payload['exp'])
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting token expiry: {e}")
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if token is expired without verification
    
    Args:
        token: JWT token string
        
    Returns:
        True if expired, False otherwise
    """
    try:
        expiry = get_token_expiry(token)
        if expiry:
            return datetime.utcnow() > expiry
        return False
        
    except Exception:
        return True


def get_token_payload(token: str) -> Optional[Dict[str, Any]]:
    """
    Get token payload without verification
    
    Args:
        token: JWT token string
        
    Returns:
        Payload dictionary or None
    """
    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        return payload
        
    except Exception as e:
        logger.error(f"Error getting token payload: {e}")
        return None

