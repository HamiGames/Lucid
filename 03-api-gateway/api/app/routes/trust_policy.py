# Trust Policy Router Module
# Client-controlled session policy enforcement endpoints

from fastapi import APIRouter, HTTPException, Depends, status
import logging
from typing import Optional

from app.schemas.sessions import (
    TrustPolicy, PolicyValidationRequest, PolicyValidationResponse
)
from app.schemas.errors import ErrorResponse
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency injection for session service
async def get_session_service() -> SessionService:
    """Get session service instance"""
    return SessionService()


@router.post(
    "/{session_id}/policy",
    response_model=PolicyValidationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set session trust policy",
    description="Set client-enforced control policy for session"
)
async def set_session_policy(
    session_id: str,
    policy: TrustPolicy,
    service: SessionService = Depends(get_session_service)
) -> PolicyValidationResponse:
    """
    Set trust policy for a session.
    
    This endpoint:
    1. Validates the policy schema
    2. Checks session exists and is in INITIALIZING state
    3. Stores policy with signature verification
    4. Returns validation results
    
    Args:
        session_id: Session identifier
        policy: Trust policy configuration
        
    Returns:
        Policy validation response with acceptance status
    """
    try:
        logger.info(f"Setting trust policy for session {session_id}")
        
        # Validate session exists and is in correct state
        session_detail = await service.get_session_detail(session_id)
        if not session_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="session_not_found",
                    message=f"Session {session_id} not found"
                ).model_dump()
            )
        
        if session_detail.state.value != "initializing":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code="invalid_session_state",
                    message="Trust policy can only be set for sessions in INITIALIZING state"
                ).model_dump()
            )
        
        # Validate and store policy
        validation_result = await service.set_session_policy(session_id, policy)
        
        logger.info(f"Trust policy set for session {session_id}: {validation_result.valid}")
        return validation_result
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Invalid policy data: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="invalid_policy_data",
                message=str(e)
            ).model_dump()
        )
    except Exception as e:
        logger.error(f"Failed to set session policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="policy_set_failed",
                message="Failed to set session trust policy"
            ).model_dump()
        )


@router.get(
    "/{session_id}/policy",
    response_model=TrustPolicy,
    summary="Get session trust policy",
    description="Retrieve current trust policy for session"
)
async def get_session_policy(
    session_id: str,
    service: SessionService = Depends(get_session_service)
) -> TrustPolicy:
    """
    Get current trust policy for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Current trust policy configuration
    """
    try:
        logger.info(f"Retrieving trust policy for session {session_id}")
        
        policy = await service.get_session_policy(session_id)
        
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="policy_not_found",
                    message=f"No trust policy found for session {session_id}"
                ).model_dump()
            )
        
        return policy
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="policy_retrieval_failed",
                message="Failed to retrieve session trust policy"
            ).model_dump()
        )


@router.put(
    "/{session_id}/policy/validate",
    response_model=PolicyValidationResponse,
    summary="Validate trust policy",
    description="Validate policy configuration before session start"
)
async def validate_session_policy(
    session_id: str,
    validation_request: PolicyValidationRequest,
    service: SessionService = Depends(get_session_service)
) -> PolicyValidationResponse:
    """
    Validate trust policy before session start.
    
    This endpoint:
    1. Validates policy schema and constraints
    2. Checks for conflicts with session requirements
    3. Verifies policy signature (if provided)
    4. Returns validation results with errors/warnings
    
    Args:
        session_id: Session identifier
        validation_request: Policy validation request
        
    Returns:
        Policy validation response with detailed results
    """
    try:
        logger.info(f"Validating trust policy for session {session_id}")
        
        # Validate session exists
        session_detail = await service.get_session_detail(session_id)
        if not session_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="session_not_found",
                    message=f"Session {session_id} not found"
                ).model_dump()
            )
        
        # Validate policy
        validation_result = await service.validate_session_policy(
            session_id, 
            validation_request.policy
        )
        
        logger.info(f"Policy validation completed for session {session_id}: {validation_result.valid}")
        return validation_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate session policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="policy_validation_failed",
                message="Failed to validate session trust policy"
            ).model_dump()
        )


@router.delete(
    "/{session_id}/policy",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove trust policy",
    description="Remove trust policy from session (only if session not started)"
)
async def remove_session_policy(
    session_id: str,
    service: SessionService = Depends(get_session_service)
):
    """
    Remove trust policy from session.
    
    Only allowed if session is in INITIALIZING state.
    
    Args:
        session_id: Session identifier
    """
    try:
        logger.info(f"Removing trust policy for session {session_id}")
        
        # Check session state
        session_detail = await service.get_session_detail(session_id)
        if not session_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="session_not_found",
                    message=f"Session {session_id} not found"
                ).model_dump()
            )
        
        if session_detail.state.value != "initializing":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code="invalid_session_state",
                    message="Trust policy can only be removed from sessions in INITIALIZING state"
                ).model_dump()
            )
        
        # Remove policy
        success = await service.remove_session_policy(session_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="policy_not_found",
                    message=f"No trust policy found for session {session_id}"
                ).model_dump()
            )
        
        logger.info(f"Trust policy removed for session {session_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove session policy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="policy_removal_failed",
                message="Failed to remove session trust policy"
            ).model_dump()
        )


@router.get(
    "/{session_id}/policy/status",
    response_model=dict,
    summary="Get policy enforcement status",
    description="Get current policy enforcement status and violations"
)
async def get_policy_enforcement_status(
    session_id: str,
    service: SessionService = Depends(get_session_service)
) -> dict:
    """
    Get policy enforcement status for active session.
    
    Returns:
        Current enforcement status including:
        - Policy active status
        - Recent violations
        - Enforcement statistics
        - Policy compliance score
    """
    try:
        logger.info(f"Getting policy enforcement status for session {session_id}")
        
        status_info = await service.get_policy_enforcement_status(session_id)
        
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="session_not_found",
                    message=f"Session {session_id} not found"
                ).model_dump()
            )
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get policy enforcement status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="status_retrieval_failed",
                message="Failed to retrieve policy enforcement status"
            ).model_dump()
        )
