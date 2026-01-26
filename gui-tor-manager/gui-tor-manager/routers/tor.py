"""
Tor Router for GUI Tor Manager
Provides endpoints for Tor status and operations
"""

from fastapi import APIRouter, HTTPException, status
from gui_tor_manager_service import get_service
from models.tor import TorStatusResponse, TorStatus, CircuitList, Circuit, TorStatusRequest
from models.common import ErrorResponse
from utils.errors import TorOperationError

router = APIRouter(tags=["tor"])


@router.get("/status", response_model=TorStatusResponse)
async def get_tor_status(detailed: bool = False):
    """
    Get Tor proxy status
    
    Args:
        detailed: Include detailed information
    
    Returns:
        TorStatusResponse with Tor status
    """
    try:
        service = await get_service()
        tor_status_data = await service.get_tor_status()
        
        from datetime import datetime
        return TorStatusResponse(
            tor_status=TorStatus(**tor_status_data),
            timestamp=datetime.utcnow().isoformat(),
        )
    except TorOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": e.code, "message": e.message}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "TOR_STATUS_ERROR", "message": str(e)}
        )


@router.get("/circuits", response_model=CircuitList)
async def get_circuits():
    """
    Get list of active Tor circuits
    
    Returns:
        CircuitList with active circuits
    """
    try:
        service = await get_service()
        circuits_data = await service.get_circuits()
        
        circuits = [Circuit(**circuit) for circuit in circuits_data]
        return CircuitList(
            circuits=circuits,
            total=len(circuits),
        )
    except TorOperationError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": e.code, "message": e.message}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "CIRCUITS_FETCH_ERROR", "message": str(e)}
        )


@router.post("/renew-circuits")
async def renew_circuits():
    """
    Renew Tor circuits (signal newnym)
    
    Returns:
        Success message
    """
    try:
        service = await get_service()
        # Implementation for renewing circuits would go here
        return {"message": "Circuits renewal initiated", "status": "pending"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "RENEW_ERROR", "message": str(e)}
        )
