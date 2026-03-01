"""
Authentication Models
File: gui-api-bridge/gui-api-bridge/models/auth.py
"""

from pydantic import BaseModel
from typing import Optional


class TokenPayload(BaseModel):
    """JWT token payload model"""
    sub: str  # Subject (user ID)
    role: str
    exp: int  # Expiration time
    iat: int  # Issued at
    jti: Optional[str] = None  # JWT ID


class SessionRecoveryRequest(BaseModel):
    """Session recovery request model"""
    owner_address: str
    session_id: Optional[str] = None


class SessionRecoveryResponse(BaseModel):
    """Session recovery response model"""
    status: str
    session_id: str
    token: Optional[str] = None
    message: Optional[str] = None
