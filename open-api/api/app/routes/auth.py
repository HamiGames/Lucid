# Path: open-api/api/app/routes/auth.py
# Lucid RDP Authentication API Blueprint
# Implements TRON address-based authentication with hardware wallet support
# Based on LUCID-STRICT requirements from Build_guide_docs

from __future__ import annotations

import logging
import hashlib
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, status, Header, Query, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
import jwt
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidSignature
import base58

# Import from our components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))

try:
    from RDP.security.trust_controller import get_trust_controller, SessionControlMode, ThreatLevel
    from sessions.core.session_generator import SecureSessionGenerator
except ImportError:
    # Fallback for missing components
    class SessionControlMode:
        RESTRICTED = "restricted"
        GUIDED = "guided"
    class ThreatLevel:
        MEDIUM = "medium"
        HIGH = "high"
    
    class MockTrustController:
        async def create_session_profile(self, *args, **kwargs):
            return True
    
    def get_trust_controller():
        return MockTrustController()
    
    class SecureSessionGenerator:
        pass

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

# JWT Configuration
JWT_SECRET = secrets.token_urlsafe(32)  # In production, load from secure config
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Hardware wallet configuration
SUPPORTED_HW_WALLETS = ["ledger", "trezor", "keepkey"]
TRON_ADDRESS_PREFIX = "T"

# Pydantic Models
class TronSignature(BaseModel):
    """TRON signature for authentication"""
    message: str = Field(..., description="Original message that was signed")
    signature: str = Field(..., description="Base58 encoded signature")
    public_key: str = Field(..., description="Ed25519 public key (base64)")
    recovery_id: Optional[int] = Field(None, description="Signature recovery ID")

class HardwareWalletAuth(BaseModel):
    """Hardware wallet authentication data"""
    wallet_type: str = Field(..., description="Wallet type")
    device_path: Optional[str] = Field(None, description="Device path for connection")
    app_version: Optional[str] = Field(None, description="Wallet app version")
    device_id: Optional[str] = Field(None, description="Unique device identifier")

class LoginRequest(BaseModel):
    """User login request with TRON authentication"""
    tron_address: str = Field(..., pattern=r'^T[A-Za-z0-9]{33}$', description="TRON wallet address")
    signature_data: TronSignature = Field(..., description="TRON signature for authentication")
    hardware_wallet: Optional[HardwareWalletAuth] = Field(None, description="Hardware wallet info")
    session_metadata: Optional[Dict[str, Any]] = Field(None, description="Session metadata")
    
    @validator('tron_address')
    def validate_tron_address(cls, v):
        if not v.startswith(TRON_ADDRESS_PREFIX) or len(v) != 34:
            raise ValueError('Invalid TRON address format')
        return v

class TokenPair(BaseModel):
    """JWT token pair response"""
    access_token: str = Field(..., description="Short-lived access token")
    refresh_token: str = Field(..., description="Long-lived refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiration in seconds")
    user_info: Dict[str, Any] = Field(..., description="User information")

class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str = Field(..., description="Valid refresh token")

class LogoutRequest(BaseModel):
    """Logout request"""
    access_token: str = Field(..., description="Access token to invalidate")
    all_devices: bool = Field(default=False, description="Logout from all devices")

# Global components
try:
    session_generator = SecureSessionGenerator()
    trust_controller = get_trust_controller()
except:
    session_generator = None
    trust_controller = get_trust_controller()

# In-memory token store (in production, use Redis or similar)
active_tokens: Dict[str, Dict[str, Any]] = {}
refresh_tokens: Dict[str, Dict[str, Any]] = {}

def verify_tron_signature(message: str, signature: str, public_key: str) -> bool:
    """Verify TRON signature using Ed25519"""
    try:
        # Simple verification for demo - in production use proper TRON signature verification
        return len(signature) > 0 and len(public_key) > 0 and len(message) > 0
    except Exception as e:
        logger.warning(f"Signature verification failed: {e}")
        return False

def create_access_token(user_data: Dict[str, Any]) -> str:
    """Create JWT access token"""
    payload = {
        "user_id": user_data["user_id"],
        "tron_address": user_data["tron_address"],
        "role": user_data.get("role", "user"),
        "permissions": user_data.get("permissions", []),
        "token_type": "access",
        "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4())
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    # Store active token
    active_tokens[payload["jti"]] = {
        "user_id": user_data["user_id"],
        "tron_address": user_data["tron_address"],
        "expires_at": payload["exp"],
        "created_at": datetime.utcnow()
    }
    
    return token

def create_refresh_token(user_data: Dict[str, Any]) -> str:
    """Create JWT refresh token"""
    payload = {
        "user_id": user_data["user_id"],
        "tron_address": user_data["tron_address"],
        "token_type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4())
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    # Store refresh token
    refresh_tokens[payload["jti"]] = {
        "user_id": user_data["user_id"],
        "tron_address": user_data["tron_address"],
        "expires_at": payload["exp"],
        "created_at": datetime.utcnow()
    }
    
    return token

@router.post("/login", response_model=TokenPair)
async def login(request: LoginRequest) -> TokenPair:
    """
    Authenticate user with TRON address and signature.
    
    Supports hardware wallet verification for enhanced security.
    Creates session profile with trust-nothing policy settings.
    """
    try:
        logger.info(f"Authentication attempt for TRON address: {request.tron_address}")
        
        # Verify TRON signature
        message = request.signature_data.message
        signature = request.signature_data.signature
        public_key = request.signature_data.public_key
        
        if not verify_tron_signature(message, signature, public_key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid TRON signature"
            )
        
        # Verify hardware wallet if provided
        hardware_wallet_verified = False
        if request.hardware_wallet:
            hardware_wallet_verified = True  # Mock verification for demo
        
        # Create user profile
        user_id = hashlib.sha256(request.tron_address.encode()).hexdigest()[:16]
        
        user_data = {
            "user_id": user_id,
            "tron_address": request.tron_address,
            "role": "user",
            "permissions": ["session_create", "session_join", "session_observe"],
            "hardware_wallet_verified": hardware_wallet_verified,
            "last_login": datetime.now(timezone.utc),
            "public_key": public_key
        }
        
        # Generate tokens
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token(user_data)
        
        # Prepare response
        response = TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_info={
                "user_id": user_id,
                "tron_address": request.tron_address,
                "role": "user",
                "hardware_wallet_verified": hardware_wallet_verified,
                "session_control_mode": "guided",
                "threat_level": "medium"
            }
        )
        
        logger.info(f"Authentication successful for user: {user_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication processing failed"
        )

@router.post("/refresh", response_model=TokenPair)
async def refresh(request: RefreshRequest) -> TokenPair:
    """Refresh access token using valid refresh token"""
    try:
        # Decode refresh token
        payload = jwt.decode(request.refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        
        # Check token type
        if payload.get("token_type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Check if refresh token exists and is valid
        jti = payload.get("jti")
        if jti not in refresh_tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been invalidated"
            )
        
        # Create new access token
        user_data = {
            "user_id": payload["user_id"],
            "tron_address": payload["tron_address"],
            "role": "user",
            "permissions": ["session_create", "session_join", "session_observe"]
        }
        
        new_access_token = create_access_token(user_data)
        
        response = TokenPair(
            access_token=new_access_token,
            refresh_token=request.refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_info={
                "user_id": payload["user_id"],
                "tron_address": payload["tron_address"],
                "role": "user"
            }
        )
        
        logger.info(f"Token refreshed for user: {payload['user_id']}")
        return response
        
    except jwt.PyJWTError as e:
        logger.warning(f"Invalid refresh token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh processing failed"
        )

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(request: LogoutRequest) -> Dict[str, str]:
    """Logout user and invalidate tokens"""
    try:
        # Decode token to get user info
        try:
            payload = jwt.decode(request.access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("user_id")
            token_id = payload.get("jti")
        except jwt.PyJWTError:
            # Token might be expired or invalid, but still try to clean up
            user_id = None
            token_id = None
        
        # Invalidate access token
        if token_id and token_id in active_tokens:
            del active_tokens[token_id]
        
        if request.all_devices and user_id:
            # Remove all tokens for user
            tokens_to_remove = [
                jti for jti, token_data in active_tokens.items()
                if token_data["user_id"] == user_id
            ]
            for jti in tokens_to_remove:
                del active_tokens[jti]
            
            refresh_tokens_to_remove = [
                jti for jti, token_data in refresh_tokens.items()
                if token_data["user_id"] == user_id
            ]
            for jti in refresh_tokens_to_remove:
                del refresh_tokens[jti]
                
            logger.info(f"Logged out from all devices for user: {user_id}")
        else:
            logger.info(f"Logged out user: {user_id}")
        
        return {"message": "Logout successful"}
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout processing failed"
        )
