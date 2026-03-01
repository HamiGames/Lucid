"""
Onion Router for GUI Tor Manager
Provides endpoints for onion service management
"""

from fastapi import APIRouter, HTTPException, status
from ..gui_tor_manager_service import get_service
from ..models.onion import (
    OnionService, OnionServiceList, CreateOnionServiceRequest,
    CreateOnionServiceResponse, DeleteOnionServiceRequest,
    DeleteOnionServiceResponse, OnionServiceStatus, OnionServiceType
)
from ..models.common import ErrorResponse
from ..utils.errors import TorOperationError
from datetime import datetime

router = APIRouter(tags=["onion"])


@router.get("/list", response_model=OnionServiceList)
async def list_onion_services():
    """
    Get list of all onion services
    
    Returns:
        OnionServiceList with all services
    """
    try:
        service = await get_service()
        # Implementation to fetch list of onion services would go here
        # For now, return empty list
        return OnionServiceList(
            services=[],
            total=0,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "LIST_SERVICES_ERROR", "message": str(e)}
        )


@router.post("/create", response_model=CreateOnionServiceResponse)
async def create_onion_service(request: CreateOnionServiceRequest):
    """
    Create a new onion service
    
    Args:
        request: Onion service creation request
    
    Returns:
        CreateOnionServiceResponse with created service details
    """
    try:
        if not request.ports:
            raise ValueError("At least one port is required")
        
        service = await get_service()
        result = await service.create_onion_service(
            ports=request.ports,
            targets=request.targets,
            persistent=request.persistent,
        )
        
        return CreateOnionServiceResponse(
            service_id=result.get("service_id", "unknown"),
            address=result.get("address", ""),
            status=OnionServiceStatus.ACTIVE,
            created_at=datetime.utcnow().isoformat(),
        )
    except TorOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": e.code, "message": e.message}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "VALIDATION_ERROR", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "CREATE_SERVICE_ERROR", "message": str(e)}
        )


@router.delete("/delete", response_model=DeleteOnionServiceResponse)
async def delete_onion_service(request: DeleteOnionServiceRequest):
    """
    Delete an onion service
    
    Args:
        request: Onion service deletion request
    
    Returns:
        DeleteOnionServiceResponse with deleted service details
    """
    try:
        if not request.service_id:
            raise ValueError("Service ID is required")
        
        service = await get_service()
        success = await service.delete_onion_service(request.service_id)
        
        if not success:
            raise Exception("Failed to delete onion service")
        
        return DeleteOnionServiceResponse(
            service_id=request.service_id,
            address="",
            deleted_at=datetime.utcnow().isoformat(),
        )
    except TorOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": e.code, "message": e.message}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "VALIDATION_ERROR", "message": str(e)}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "DELETE_SERVICE_ERROR", "message": str(e)}
        )


@router.get("/{service_id}/status")
async def get_onion_service_status(service_id: str):
    """
    Get status of a specific onion service
    
    Args:
        service_id: Service identifier
    
    Returns:
        Service status information
    """
    try:
        service = await get_service()
        # Implementation to fetch service status would go here
        return {
            "service_id": service_id,
            "status": "active",
            "message": "Service is operational",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "STATUS_FETCH_ERROR", "message": str(e)}
        )
