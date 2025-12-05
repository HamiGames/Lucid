"""
Lucid Authentication Service - Session Routes
GET /sessions, DELETE /sessions/{session_id}, etc.
"""

from fastapi import APIRouter, HTTPException, status, Request
from typing import List
from auth.models.session import SessionResponse, Session
from auth.main import session_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def get_current_user_id(request: Request) -> str:
    """Extract current user ID from request state (set by AuthMiddleware)"""
    if not hasattr(request.state, 'user_id') or not request.state.authenticated:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return request.state.user_id


@router.get("/", response_model=List[SessionResponse])
async def list_sessions(request: Request):
    """List all active sessions for current user"""
    try:
        user_id = get_current_user_id(request)
        logger.info(f"List sessions for user: {user_id}")
        
        if not session_manager:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Get all user sessions
        sessions = await session_manager.get_user_sessions(user_id)
        
        # Convert to response models
        return [
            SessionResponse(
                session_id=session.session_id,
                user_id=session.user_id,
                created_at=session.created_at,
                expires_at=session.expires_at,
                last_activity_at=session.last_activity_at,
                is_active=session.is_active,
                revoked=session.revoked,
                metadata=session.metadata
            )
            for session in sessions
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, request: Request):
    """Get session by ID"""
    try:
        user_id = get_current_user_id(request)
        logger.info(f"Get session {session_id} for user: {user_id}")
        
        if not session_manager:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Get session
        session = await session_manager.get_session(session_id)
        
        # Verify user owns this session
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        return SessionResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            created_at=session.created_at,
            expires_at=session.expires_at,
            last_activity_at=session.last_activity_at,
            is_active=session.is_active,
            revoked=session.revoked,
            metadata=session.metadata
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(session_id: str, request: Request):
    """Revoke session by ID"""
    try:
        user_id = get_current_user_id(request)
        logger.info(f"Revoke session {session_id} for user: {user_id}")
        
        if not session_manager:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Get session to verify ownership
        session = await session_manager.get_session(session_id)
        if session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Revoke session
        await session_manager.revoke_session(session_id)
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_all_sessions(request: Request):
    """Revoke all sessions for current user"""
    try:
        user_id = get_current_user_id(request)
        logger.info(f"Revoke all sessions for user: {user_id}")
        
        if not session_manager:
            raise HTTPException(status_code=503, detail="Service not initialized")
        
        # Revoke all user sessions
        await session_manager.revoke_all_user_sessions(user_id)
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking all sessions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# Add router to main router
from . import sessions_router as main_router
main_router.include_router(router)

