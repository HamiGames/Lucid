"""
Anchoring Router

This module contains the session anchoring endpoints.
Implements the OpenAPI 3.0 specification for session manifest anchoring.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging

from ..schemas.anchoring import (
    SessionAnchoringRequest, SessionAnchoringResponse, SessionAnchoringStatus,
    AnchoringVerificationRequest, AnchoringVerificationResponse, AnchoringServiceStatus
)
from ..dependencies import get_current_user, verify_api_key, require_read_permission, require_write_permission
from ..services.anchoring_service import AnchoringService
from ..errors import SessionAnchoringException, AnchoringVerificationException

router = APIRouter(
    prefix="/anchoring",
    tags=["Anchoring"],
    responses={404: {"description": "Anchoring not found"}},
)

logger = logging.getLogger(__name__)

@router.post("/session", response_model=SessionAnchoringResponse, status_code=status.HTTP_202_ACCEPTED)
async def anchor_session_manifest(
    anchoring_request: SessionAnchoringRequest,
    user = Depends(require_write_permission)
):
    """
    Anchors a session manifest to the lucid_blocks blockchain.
    
    This endpoint initiates the process of anchoring a session manifest
    to the blockchain for data integrity and immutability.
    
    The anchoring process:
    1. Validates the session manifest data
    2. Creates a transaction to anchor the manifest
    3. Submits the transaction to the blockchain
    4. Returns anchoring ID and status
    
    Session manifest must include:
    - Valid session UUID
    - Merkle tree root hash
    - Session data payload
    - Optional user signature
    """
    try:
        logger.info("Initiating session anchoring")
        anchoring_response = await AnchoringService.anchor_session(anchoring_request.dict())
        return SessionAnchoringResponse(**anchoring_response)
    except Exception as e:
        logger.error(f"Failed to initiate session anchoring: {e}")
        raise SessionAnchoringException(
            session_id=anchoring_request.session_id,
            reason=str(e)
        )

@router.get("/session/{session_id}", response_model=SessionAnchoringStatus)
async def get_session_anchoring_status(
    session_id: str,
    user = Depends(require_read_permission)
):
    """
    Returns the anchoring status for a specific session.
    
    Provides real-time status information about the session anchoring process:
    - Current anchoring status (pending, processing, confirmed, failed)
    - Submission and confirmation timestamps
    - Block height where session was anchored
    - Transaction ID of the anchoring
    - Merkle root hash
    
    Status values:
    - pending: Anchoring request submitted, waiting for processing
    - processing: Anchoring transaction being processed
    - confirmed: Session successfully anchored to blockchain
    - failed: Anchoring failed due to error
    """
    try:
        logger.info(f"Fetching session anchoring status for session ID: {session_id}")
        status_data = await AnchoringService.get_anchoring_status(session_id)
        if not status_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session anchoring not found"
            )
        return SessionAnchoringStatus(**status_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch session anchoring status for session ID {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session anchoring status"
        )

@router.post("/verify", response_model=AnchoringVerificationResponse)
async def verify_session_anchoring(
    verification_request: AnchoringVerificationRequest,
    user = Depends(require_read_permission)
):
    """
    Verifies the anchoring of a session manifest on the blockchain.
    
    This endpoint verifies that a session manifest has been properly
    anchored to the blockchain and validates the anchoring integrity.
    
    Verification process:
    1. Checks if session exists in blockchain
    2. Validates Merkle root hash
    3. Verifies anchoring transaction
    4. Confirms data integrity
    
    Returns verification results including:
    - Verification status (verified/not verified)
    - Block height and transaction ID
    - Confirmation timestamp
    - Merkle proof validation
    """
    try:
        logger.info("Verifying session anchoring")
        verification_response = await AnchoringService.verify_anchoring(verification_request.dict())
        return AnchoringVerificationResponse(**verification_response)
    except Exception as e:
        logger.error(f"Failed to verify session anchoring: {e}")
        raise AnchoringVerificationException(verification_request.session_id)

@router.get("/status", response_model=AnchoringServiceStatus)
async def get_anchoring_service_status(
    user = Depends(require_read_permission)
):
    """
    Returns the current status of the anchoring service.
    
    Provides service health and performance metrics:
    - Service status (healthy, busy, error)
    - Number of pending and processing anchorings
    - Completed anchorings today
    - Average confirmation time
    - Service performance indicators
    
    Useful for monitoring service health and performance.
    """
    try:
        logger.info("Fetching anchoring service status")
        service_status = await AnchoringService.get_service_status()
        return AnchoringServiceStatus(**service_status)
    except Exception as e:
        logger.error(f"Failed to fetch anchoring service status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve anchoring service status"
        )