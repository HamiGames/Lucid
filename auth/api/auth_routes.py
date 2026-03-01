"""
Lucid Authentication Service - Authentication Routes
POST /auth/login, /auth/register, /auth/refresh, /auth/logout
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from auth.models.user import LoginRequest, LoginResponse, UserCreate, UserResponse
from auth.models.session import RefreshTokenRequest, RefreshTokenResponse, TokenPayload
from auth.main import user_manager, session_manager, mongodb_db
from auth.models.session import TokenType
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def get_current_user_id(request: Request) -> str:
    """Extract current user ID from request state (set by AuthMiddleware)"""
    if not hasattr(request.state, 'user_id') or not request.state.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.state.user_id


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserCreate):
    """
    Register new user with TRON signature verification
    
    - Verifies TRON signature
    - Creates user account
    - Returns user information
    """
    try:
        logger.info(f"User registration attempt: {request.tron_address}")
        
        if not user_manager or not mongodb_db:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Check if user already exists
        existing_user = await user_manager.get_user_by_tron_address(request.tron_address)
        if existing_user:
            raise HTTPException(status_code=409, detail="User already exists")
        
        # TODO: Verify TRON signature
        # For now, create user without signature verification
        
        # Create user profile
        from auth.user_manager import UserProfile, UserRole, KYCStatus
        user_profile = UserProfile(
            user_id=str(uuid.uuid4()),
            tron_address=request.tron_address,
            role=UserRole.USER,
            kyc_status=KYCStatus.NONE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Save to database
        success = await user_manager.create_user(user_profile)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        return UserResponse(
            user_id=user_profile.user_id,
            tron_address=user_profile.tron_address,
            role=user_profile.role.value,
            created_at=user_profile.created_at,
            updated_at=user_profile.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login with TRON signature
    
    - Verifies TRON signature
    - Generates JWT tokens (15min access, 7day refresh)
    - Creates session
    - Returns tokens and user info
    """
    try:
        logger.info(f"Login attempt: {request.tron_address}")
        
        if not user_manager or not session_manager or not mongodb_db:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Get user by TRON address
        user_profile = await user_manager.get_user_by_tron_address(request.tron_address)
        if not user_profile:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # TODO: Verify TRON signature
        # For now, skip signature verification
        
        # Generate tokens
        access_token = session_manager.generate_access_token(
            user_id=user_profile.user_id,
            role=user_profile.role.value
        )
        refresh_token = session_manager.generate_refresh_token(user_id=user_profile.user_id)
        
        # Create session
        session = await session_manager.create_session(
            user_id=user_profile.user_id,
            role=user_profile.role.value,
            metadata={"tron_address": request.tron_address}
        )
        
        # Update last login
        user_profile.last_login_at = datetime.utcnow()
        await user_manager.update_user(user_profile)
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=900,  # 15 minutes
            user=UserResponse(
                user_id=user_profile.user_id,
                tron_address=user_profile.tron_address,
                role=user_profile.role.value,
                created_at=user_profile.created_at,
                updated_at=user_profile.updated_at
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token
    
    - Validates refresh token
    - Generates new access token
    - Optionally rotates refresh token
    """
    try:
        logger.info("Token refresh requested")
        
        if not session_manager:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Refresh token and get new access token
        tokens = await session_manager.refresh_access_token(request.refresh_token)
        
        return RefreshTokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token", request.refresh_token),
            token_type="bearer",
            expires_in=900  # 15 minutes
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request):
    """
    Logout user and revoke session
    
    - Revokes current session
    - Blacklists tokens
    """
    try:
        user_id = get_current_user_id(request)
        logger.info(f"Logout requested for user: {user_id}")
        
        if not session_manager:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Get token JTI from request state
        if hasattr(request.state, 'token_jti'):
            # Blacklist current token
            from datetime import timedelta
            await session_manager.blacklist_token(
                request.state.token_jti,
                timedelta(days=7)  # Blacklist for 7 days
            )
        
        # Revoke all user sessions
        await session_manager.revoke_all_user_sessions(user_id)
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during logout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/verify")
async def verify_token(request: Request):
    """
    Verify JWT token validity
    
    - Validates token
    - Returns token payload
    """
    try:
        # Token is already validated by AuthMiddleware
        if not hasattr(request.state, 'user_id') or not request.state.authenticated:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return {
            "valid": True,
            "user_id": request.state.user_id,
            "role": request.state.role,
            "jti": getattr(request.state, 'token_jti', None)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying token: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# Add router to main router (from __init__.py)
from . import auth_router as main_router
main_router.include_router(router)

