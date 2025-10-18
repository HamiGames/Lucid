# Sessions Router Module
# Core session lifecycle management endpoints

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
import logging
from datetime import datetime

from app.schemas.sessions import (
    SessionCreate, SessionResponse, SessionDetail, SessionList, 
    SessionStateUpdate, SessionState
)
from app.schemas.errors import ErrorResponse
from app.db.models.session import RDPSession
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency injection for session service
async def get_session_service() -> SessionService:
    """Get session service instance"""
    return SessionService()


@router.post(
    "/",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new session",
    description="Create a new RDP session with unique ID generation and pipeline initialization"
)
async def create_session(
    session_data: SessionCreate,
    service: SessionService = Depends(get_session_service)
) -> SessionResponse:
    """
    Create a new session with the specified parameters.
    
    This endpoint:
    1. Generates a unique session ID
    2. Initializes the session pipeline
    3. Creates session record in MongoDB
    4. Returns session details
    """
    try:
        logger.info(f"Creating session for user {session_data.user_id} on node {session_data.node_id}")
        
        # Create session via service layer
        session_response = await service.create_session(
            user_id=session_data.user_id,
            owner_address=session_data.owner_address,
            node_id=session_data.node_id,
            policy_hash=session_data.policy_hash
        )
        
        logger.info(f"Session created successfully: {session_response.session_id}")
        return session_response
        
    except ValueError as e:
        logger.error(f"Invalid session data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="invalid_session_data",
                message=str(e)
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="session_creation_failed",
                message="Failed to create session"
            ).model_dump()
        )


@router.get(
    "/",
    response_model=SessionList,
    summary="List user sessions",
    description="Get paginated list of sessions for the authenticated user"
)
async def list_sessions(
    user_id: str = Query(..., description="User identifier"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    state: Optional[SessionState] = Query(None, description="Filter by session state"),
    service: SessionService = Depends(get_session_service)
) -> SessionList:
    """
    List sessions for a user with optional filtering by state.
    
    Supports pagination and state filtering.
    """
    try:
        logger.info(f"Listing sessions for user {user_id}, page {page}, size {page_size}")
        
        session_list = await service.list_sessions(
            user_id=user_id,
            page=page,
            page_size=page_size,
            state=state
        )
        
        return session_list
        
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="session_list_failed",
                message="Failed to retrieve sessions"
            ).model_dump()
        )


@router.get(
    "/{session_id}",
    response_model=SessionDetail,
    summary="Get session details",
    description="Get detailed information about a specific session"
)
async def get_session(
    session_id: str,
    service: SessionService = Depends(get_session_service)
) -> SessionDetail:
    """
    Get detailed session information including blockchain metadata.
    
    Returns session details with manifest hash, merkle root, and anchor transaction ID
    if the session has been finalized and anchored.
    """
    try:
        logger.info(f"Retrieving session details for {session_id}")
        
        session_detail = await service.get_session_detail(session_id)
        
        if not session_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="session_not_found",
                    message=f"Session {session_id} not found"
                ).model_dump()
            )
        
        return session_detail
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="session_retrieval_failed",
                message="Failed to retrieve session details"
            ).model_dump()
        )


@router.put(
    "/{session_id}/start",
    response_model=SessionResponse,
    summary="Start session recording",
    description="Begin recording for the specified session"
)
async def start_session(
    session_id: str,
    service: SessionService = Depends(get_session_service)
) -> SessionResponse:
    """
    Start session recording.
    
    This endpoint:
    1. Validates session is in INITIALIZING state
    2. Transitions session to RECORDING state
    3. Starts the session pipeline
    4. Returns updated session details
    """
    try:
        logger.info(f"Starting session recording for {session_id}")
        
        session_response = await service.start_session_recording(session_id)
        
        logger.info(f"Session recording started: {session_id}")
        return session_response
        
    except ValueError as e:
        logger.error(f"Invalid session state for start: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="invalid_session_state",
                message=str(e)
            ).model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start session recording: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="session_start_failed",
                message="Failed to start session recording"
            ).model_dump()
        )


@router.put(
    "/{session_id}/finalize",
    response_model=SessionDetail,
    summary="Finalize session",
    description="Finalize session and trigger blockchain anchoring"
)
async def finalize_session(
    session_id: str,
    service: SessionService = Depends(get_session_service)
) -> SessionDetail:
    """
    Finalize session and trigger blockchain anchoring.
    
    This endpoint:
    1. Validates session is in RECORDING state
    2. Transitions session to FINALIZING state
    3. Triggers session pipeline finalization
    4. Initiates blockchain anchoring
    5. Returns session details with anchor metadata
    """
    try:
        logger.info(f"Finalizing session {session_id}")
        
        session_detail = await service.finalize_session(session_id)
        
        logger.info(f"Session finalized and anchored: {session_id}")
        return session_detail
        
    except ValueError as e:
        logger.error(f"Invalid session state for finalization: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="invalid_session_state",
                message=str(e)
            ).model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to finalize session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="session_finalization_failed",
                message="Failed to finalize session"
            ).model_dump()
        )


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel session",
    description="Cancel/void session (only allowed before recording starts)"
)
async def cancel_session(
    session_id: str,
    service: SessionService = Depends(get_session_service)
):
    """
    Cancel session before recording starts.
    
    Only allowed for sessions in INITIALIZING state.
    Sessions that have started recording cannot be cancelled.
    """
    try:
        logger.info(f"Cancelling session {session_id}")
        
        success = await service.cancel_session(session_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code="session_cannot_be_cancelled",
                    message="Session cannot be cancelled in current state"
                ).model_dump()
            )
        
        logger.info(f"Session cancelled: {session_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="session_cancellation_failed",
                message="Failed to cancel session"
            ).model_dump()
        )


@router.get(
    "/{session_id}/state",
    response_model=dict,
    summary="Get session state",
    description="Get real-time session state information"
)
async def get_session_state(
    session_id: str,
    service: SessionService = Depends(get_session_service)
) -> dict:
    """
    Get real-time session state information.
    
    Returns current state, timestamps, and processing status.
    """
    try:
        logger.info(f"Getting session state for {session_id}")
        
        state_info = await service.get_session_state(session_id)
        
        if not state_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="session_not_found",
                    message=f"Session {session_id} not found"
                ).model_dump()
            )
        
        return state_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="session_state_retrieval_failed",
                message="Failed to retrieve session state"
            ).model_dump()
        )
