"""
File: /app/auth/api/auth_routes.py
x-lucid-file-path: /app/auth/api/auth_routes.py
x-lucid-file-directory: /app/auth/api
x-lucid-file-type: python

Lucid Authentication Service - Authentication Routes
POST /auth/login, /auth/register, /auth/refresh, /auth/logout
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from auth.models.user import (
    CREDENTIAL_TRON_PLACEHOLDER,
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserResponse,
)
from auth.config import settings
from auth.services.sm_login_verify import (
    registry_user_with_server_manager,
    verify_preauth_with_server_manager,
    verify_with_server_manager,
)
from auth.models.session import RefreshTokenRequest, RefreshTokenResponse, TokenPayload, TokenType
from auth.utils.exceptions import TokenExpiredError, InvalidTokenError
from auth.main import user_manager, session_manager, mongodb_db
from datetime import datetime
from typing import Optional, Tuple
import uuid
import logging
import bcrypt

logger = logging.getLogger(__name__)

def _sm_timeout() -> float:
    return float(settings.SERVER_MANAGEMENT_HTTP_TIMEOUT)


async def _require_preauth(
    intent: str, token: Optional[str], user_id: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    if not settings.SERVER_MANAGEMENT_VERIFY_ENABLED:
        return True, None
    if not token:
        return False, "pre_auth_required"
    ok, reason, _ = await verify_preauth_with_server_manager(
        settings.SERVER_MANAGEMENT_BASE_URL,
        settings.SERVER_MANAGEMENT_PREAUTH_VERIFY_PATH,
        token,
        intent,
        user_id,
        timeout=_sm_timeout(),
    )
    return ok, reason

router = APIRouter()


def get_current_user_id(request: Request) -> str:
    """Extract current user ID from request state (set by AuthMiddleware)"""
    if not hasattr(request.state, 'user_id') or not request.state.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.state.user_id


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserCreate):
    """
    Register new user: TRON signature path or credential (user_id + password) + SM pre-auth when enabled.
    """
    try:
        if not user_manager or not mongodb_db:
            raise HTTPException(status_code=503, detail="Service not initialized")

        from auth.user_manager import UserProfile, UserRole, KYCStatus

        if request.user_id and request.password:
            logger.info("User credential registration attempt: %s", request.user_id[:8])
            if len(request.password) < settings.PASSWORD_MIN_LENGTH:
                raise HTTPException(status_code=400, detail="password_too_short")
            ok, reason = await _require_preauth("register", request.pre_auth_token)
            if not ok:
                raise HTTPException(
                    status_code=503 if reason == "server_manager_unreachable" else 403,
                    detail=reason or "preauth_failed",
                )
            existing = await user_manager.get_user_by_id(request.user_id)
            if existing:
                raise HTTPException(status_code=409, detail="User already exists")
            tron = request.tron_address or CREDENTIAL_TRON_PLACEHOLDER
            pw_hash = bcrypt.hashpw(
                request.password.encode("utf-8"),
                bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS),
            ).decode("ascii")
            user_profile = UserProfile(
                user_id=request.user_id,
                tron_address=tron,
                role=UserRole.USER,
                kyc_status=KYCStatus.NONE,
                created_at=datetime.utcnow(),
                registration_key=request.registration_key,
                password_hash=pw_hash,
            )
            if settings.SERVER_MANAGEMENT_VERIFY_ENABLED:
                ok, reason = await verify_with_server_manager(
                    settings.SERVER_MANAGEMENT_BASE_URL,
                    settings.SERVER_MANAGEMENT_VERIFY_PATH,
                    {
                        "phase": "register",
                        "user_id": user_profile.user_id,
                        "tron_address": tron,
                        "registration_key": request.registration_key,
                        "pre_auth_token": request.pre_auth_token,
                        "client_metadata": request.client_metadata,
                    },
                    timeout=_sm_timeout(),
                )
                if not ok:
                    raise HTTPException(
                        status_code=503 if reason == "server_manager_unreachable" else 403,
                        detail=reason or "verify_failed",
                    )
            success = await user_manager.create_user_from_profile(user_profile)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to create user")
            if settings.SERVER_MANAGEMENT_VERIFY_ENABLED and request.registration_key:
                reg_ok, reg_reason = await registry_user_with_server_manager(
                    settings.SERVER_MANAGEMENT_BASE_URL,
                    settings.SERVER_MANAGEMENT_REGISTRY_PATH,
                    user_profile.user_id,
                    request.registration_key,
                    timeout=_sm_timeout(),
                )
                if not reg_ok:
                    logger.warning("server-manager registry failed: %s", reg_reason)
            return UserResponse(
                user_id=user_profile.user_id,
                tron_address=user_profile.tron_address,
                role=user_profile.role.value,
                created_at=user_profile.created_at,
                updated_at=user_profile.created_at,
            )

        logger.info(f"User registration attempt: {request.tron_address}")
        existing_user = await user_manager.get_user_by_tron_address(request.tron_address or "")
        if existing_user:
            raise HTTPException(status_code=409, detail="User already exists")

        user_profile = UserProfile(
            user_id=str(uuid.uuid4()),
            tron_address=request.tron_address or "",
            role=UserRole.USER,
            kyc_status=KYCStatus.NONE,
            created_at=datetime.utcnow(),
            registration_key=request.registration_key,
        )

        if settings.SERVER_MANAGEMENT_VERIFY_ENABLED:
            ok, reason = await verify_with_server_manager(
                settings.SERVER_MANAGEMENT_BASE_URL,
                settings.SERVER_MANAGEMENT_VERIFY_PATH,
                {
                    "phase": "register",
                    "user_id": user_profile.user_id,
                    "tron_address": request.tron_address,
                    "registration_key": request.registration_key,
                    "pre_auth_token": request.pre_auth_token,
                    "client_metadata": request.client_metadata,
                },
                timeout=_sm_timeout(),
            )
            if not ok:
                raise HTTPException(
                    status_code=503 if reason == "server_manager_unreachable" else 403,
                    detail=reason or "verify_failed",
                )

        success = await user_manager.create_user_from_profile(user_profile)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create user")
        if settings.SERVER_MANAGEMENT_VERIFY_ENABLED and request.registration_key:
            reg_ok, reg_reason = await registry_user_with_server_manager(
                settings.SERVER_MANAGEMENT_BASE_URL,
                settings.SERVER_MANAGEMENT_REGISTRY_PATH,
                user_profile.user_id,
                request.registration_key,
                timeout=_sm_timeout(),
            )
            if not reg_ok:
                logger.warning("server-manager registry failed: %s", reg_reason)

        return UserResponse(
            user_id=user_profile.user_id,
            tron_address=user_profile.tron_address,
            role=user_profile.role.value,
            created_at=user_profile.created_at,
            updated_at=user_profile.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """
    Login: TRON signature path or credential (user_id + password) + SM verification when enabled.
    """
    try:
        if not user_manager or not session_manager or not mongodb_db:
            raise HTTPException(status_code=503, detail="Service not initialized")

        if request.user_id and request.password:
            logger.info("Credential login attempt: %s", request.user_id[:8])
            ok, reason = await _require_preauth("login", request.pre_auth_token, request.user_id)
            if not ok:
                raise HTTPException(
                    status_code=503 if reason == "server_manager_unreachable" else 403,
                    detail=reason or "preauth_failed",
                )
            user_profile = await user_manager.get_user_by_id(request.user_id)
            if not user_profile or not user_profile.password_hash:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            if not bcrypt.checkpw(
                request.password.encode("utf-8"),
                user_profile.password_hash.encode("utf-8"),
            ):
                raise HTTPException(status_code=401, detail="Invalid credentials")
        else:
            logger.info(f"Login attempt: {request.tron_address}")
            user_profile = await user_manager.get_user_by_tron_address(request.tron_address or "")
            if not user_profile:
                raise HTTPException(status_code=401, detail="Invalid credentials")

        if settings.SERVER_MANAGEMENT_VERIFY_ENABLED:
            ok, reason = await verify_with_server_manager(
                settings.SERVER_MANAGEMENT_BASE_URL,
                settings.SERVER_MANAGEMENT_VERIFY_PATH,
                {
                    "phase": "login",
                    "user_id": user_profile.user_id,
                    "tron_address": user_profile.tron_address,
                    "registration_key": getattr(user_profile, "registration_key", None),
                    "pre_auth_token": request.pre_auth_token,
                    "client_metadata": request.client_metadata,
                },
                timeout=_sm_timeout(),
            )
            if not ok:
                raise HTTPException(
                    status_code=503 if reason == "server_manager_unreachable" else 403,
                    detail=reason or "verify_failed",
                )

        access_token = session_manager.generate_access_token(
            user_id=user_profile.user_id,
            role=user_profile.role.value,
        )
        refresh_token = session_manager.generate_refresh_token(user_id=user_profile.user_id)

        await session_manager.create_session(
            user_id=user_profile.user_id,
            role=user_profile.role.value,
            metadata={
                "tron_address": user_profile.tron_address,
                "client_metadata": request.client_metadata or {},
            },
        )

        user_profile.last_login = datetime.utcnow()
        await user_manager.update_user(user_profile)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=900,
            user=UserResponse(
                user_id=user_profile.user_id,
                tron_address=user_profile.tron_address,
                role=user_profile.role.value,
                created_at=user_profile.created_at,
                updated_at=user_profile.created_at,
            ),
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


@router.post("/token/introspect")
async def token_introspect(request: Request):
    """
    Validate access token for internal callers (e.g. lucid-api-gateway).

    Intended for Docker-internal traffic only; protect at the network layer.
    Returns minimal identity fields — no credentials or refresh material.
    """
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    token = authorization.split(None, 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    if not session_manager:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        payload = await session_manager.validate_token(token, TokenType.ACCESS)
        return {
            "valid": True,
            "user_id": payload.user_id,
            "role": payload.role or "USER",
            "jti": payload.jti,
        }
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Token expired")
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token introspection error: {e}", exc_info=True)
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

