from __future__ import annotations

import jwt as JWT
from typing import Dict, Any
from datetime import datetime, timedelta, timezone
import uuid
import os

import logging

logger = logging.get_logger(__name__)

JWT_SECRET = os.getenv("JWT_SECRET", "lucid_jwt_secret_key_change_in_production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "15"))
JWT_EXPIRE_DAYS = int(os.getenv("JWT_EXPIRE_DAYS", "7"))
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "1"))
JWT_EXPIRE_SECONDS = int(os.getenv("JWT_EXPIRE_SECONDS", "0"))
JWT_EXPIRE_MILLISECONDS = int(os.getenv("JWT_EXPIRE_MILLISECONDS", "0"))
JWT_EXPIRE_MICROSECONDS = int(os.getenv("JWT_EXPIRE_MICROSECONDS", "0"))
JWT_EXPIRE_NANOSECONDS = int(os.getenv("JWT_EXPIRE_NANOSECONDS", "0"))
JWT_EXPIRE_TIMEZONE = os.getenv("JWT_EXPIRE_TIMEZONE", "UTC")
blacklisted_tokens = []

def encode_jwt(payload: Dict[str, Any]) -> str:
    """Encode a JWT token"""
    try:
        payload = payload.copy()
        payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
        payload["iat"] = datetime.now(timezone.utc)
        payload["jti"] = str(uuid.uuid4())
        payload["iss"] = "api-gateway"
        payload["aud"] = "lucid-blockchain"
        return JWT.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    except Exception as e:
        logger.error(f"Error encoding JWT: {e}")
        raise

def decode_jwt(token: str) -> Dict[str, Any]:
    """Decode a JWT token"""
    try:
        return JWT.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception as e:
        logger.error(f"Error decoding JWT: {e}")
        raise

def verify_jwt(token: str) -> bool:
    """Verify a JWT token"""
    try:
        return JWT.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception as e:
        logger.error(f"Error verifying JWT: {e}")
        raise

def extract_token_from_header(authorization: str) -> str:
    """Extract a JWT token from the authorization header"""
    try:
        return JWT.decode(authorization.split(" ")[1], JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception as e:
        logger.error(f"Error extracting token from header: {e}")
        raise

def create_token_payload(user_id: str, role: str) -> Dict[str, Any]:
    """Create a JWT token payload"""
    try:
        return {
            "sub": user_id,
            "role": role,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES),
            "iat": datetime.now(timezone.utc),
            "jti": str(uuid.uuid4()),
            "iss": "api-gateway",
            "aud": "lucid-blockchain"
        }
    except Exception as e:
        logger.error(f"Error creating token payload: {e}")
        raise

def is_token_expired(token: str) -> bool:
    """Check if a JWT token is expired"""
    try:
        return JWT.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])["exp"] < datetime.now(timezone.utc)
    except Exception as e:
        logger.error(f"Error checking if token is expired: {e}")
        raise

def get_token_expiry(token: str) -> datetime:
    """Get the expiry time of a JWT token"""
    try:
        return JWT.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])["exp"] if "exp" in JWT.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM]) else None
    except Exception as e:
        logger.error(f"Error getting token expiry: {e}")
        raise

def get_token_payload(token: str) -> Dict[str, Any]:
    """Get the payload of a JWT token"""
    try:
        return JWT.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception as e:
        logger.error(f"Error getting token payload: {e}")
        raise

def is_token_valid(token: str) -> bool:
    """Check if a JWT token is valid"""
    try:
        return JWT.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM]) is not None
    except Exception as e:
        logger.error(f"Error checking if token is valid: {e}")
        raise

def is_token_blacklisted(token: str) -> bool:
    """Check if a JWT token is blacklisted"""
    
    return JWT.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])["jti"] in blacklisted_tokens

def blacklist_token(token: str) -> None:
    """Blacklist a JWT token"""
    blacklisted_tokens.append(JWT.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])["jti"])

def cleanup_expired_tokens() -> None:
    """Cleanup expired tokens"""
    for token in blacklisted_tokens:
        if is_token_expired(token):
            blacklisted_tokens.remove(token)

def get_blacklisted_tokens() -> list[str]:
    """Get the list of blacklisted tokens"""
    return blacklisted_tokens

