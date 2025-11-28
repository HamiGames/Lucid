"""
Lucid Authentication Service - Session Routes
GET /sessions, DELETE /sessions/{session_id}, etc.
"""

from fastapi import APIRouter, HTTPException, status
from typing import List
from models.session import SessionResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[SessionResponse])
async def list_sessions():
    """List all active sessions for current user"""
    logger.info("List sessions")
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session by ID"""
    logger.info(f"Get session: {session_id}")
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(session_id: str):
    """Revoke session by ID"""
    logger.info(f"Revoke session: {session_id}")
    raise HTTPException(status_code=501, detail="Not implemented")


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_all_sessions():
    """Revoke all sessions for current user"""
    logger.info("Revoke all sessions")
    raise HTTPException(status_code=501, detail="Not implemented")


# Add router to main router
from . import sessions_router as main_router
main_router.include_router(router)

