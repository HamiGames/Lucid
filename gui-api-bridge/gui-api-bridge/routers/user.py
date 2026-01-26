"""
User API Routes
File: gui-api-bridge/gui-api-bridge/routers/user.py
Endpoints: /api/v1/user
Allowed methods: GET, POST
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from ..models.auth import SessionRecoveryRequest, SessionRecoveryResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/user", tags=["user"])


@router.get("/")
async def list_user_endpoints():
    """List available user endpoints"""
    return {
        "endpoints": [
            "GET /api/v1/user/profile",
            "GET /api/v1/user/sessions",
            "POST /api/v1/user/sessions/{session_id}/recover",
        ]
    }


@router.get("/profile")
async def get_user_profile(request: Request):
    """Get user profile"""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    
    return {
        "user_id": user.get("sub"),
        "role": user.get("role"),
    }


@router.get("/sessions")
async def list_user_sessions(request: Request):
    """List user's sessions"""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    
    return {
        "sessions": [],
        "user_id": user.get("sub"),
    }


@router.post("/sessions/{session_id}/recover")
async def recover_session(
    session_id: str,
    request: Request,
    body: SessionRecoveryRequest,
):
    """
    Recover session token from blockchain
    
    Args:
        session_id: Session ID to recover
        request: FastAPI request
        body: Recovery request with owner_address
    
    Returns:
        Recovered session token or error
    """
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
    
    logger.info(f"Session recovery request for {session_id}")
    
    return {
        "status": "success",
        "session_id": session_id,
        "message": "Recovery request received",
    }
