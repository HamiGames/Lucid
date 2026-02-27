"""
Tor integration endpoints
Provides access to Tor proxy services for anonymous transactions
"""

import logging
from fastapi import APIRouter, HTTPException, Request
from typing import Dict, Any, Optional
from pydantic import BaseModel

from gui_hardware_manager.config import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)


class TorStatusResponse(BaseModel):
    """Tor service status response"""
    status: str
    tor_connected: bool
    onion_address: Optional[str] = None
    exit_node: Optional[Dict[str, Any]] = None


class CircuitRotationRequest(BaseModel):
    """Circuit rotation request"""
    reason: Optional[str] = None


class CircuitRotationResponse(BaseModel):
    """Circuit rotation response"""
    status: str
    previous_exit: Optional[str] = None
    new_exit: Optional[str] = None


class TransactionTorRequest(BaseModel):
    """Request to route transaction through Tor"""
    transaction_hex: str
    chain: str = "TRON"
    anonymity_level: str = "high"


@router.get("/tor/status", response_model=TorStatusResponse)
async def get_tor_status(request: Request):
    """
    Get Tor proxy service status and onion address
    
    Returns:
        TorStatusResponse: Tor service status including onion address
    """
    try:
        settings = get_settings()
        
        # Get tor manager from app state if available
        tor_manager = None
        if hasattr(request.app, "state") and hasattr(request.app.state, "tor_manager"):
            tor_manager = request.app.state.tor_manager
        
        if not tor_manager:
            logger.warning("Tor manager not available")
            return TorStatusResponse(
                status="unavailable",
                tor_connected=False
            )
        
        # Check Tor health
        health = await tor_manager.check_health()
        is_operational = health.get("status") == "operational"
        
        # Get onion address
        onion_address = None
        if is_operational:
            onion_address = await tor_manager.get_onion_address()
        
        # Get exit node info
        exit_node = None
        if is_operational:
            exit_node = await tor_manager.get_exit_node_info()
        
        return TorStatusResponse(
            status=health.get("status", "unknown"),
            tor_connected=is_operational,
            onion_address=onion_address,
            exit_node=exit_node
        )
        
    except Exception as e:
        logger.error(f"Failed to get Tor status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get Tor status")


@router.get("/tor/circuit/info")
async def get_circuit_info(request: Request):
    """
    Get information about current Tor circuit
    
    Returns:
        Circuit information including exit node details
    """
    try:
        tor_manager = None
        if hasattr(request.app, "state") and hasattr(request.app.state, "tor_manager"):
            tor_manager = request.app.state.tor_manager
        
        if not tor_manager:
            raise HTTPException(status_code=503, detail="Tor integration unavailable")
        
        circuit_info = await tor_manager.get_tor_circuit_info()
        if circuit_info:
            return circuit_info
        else:
            raise HTTPException(status_code=503, detail="Cannot retrieve circuit information")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get circuit info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get circuit information")


@router.post("/tor/circuit/rotate", response_model=CircuitRotationResponse)
async def rotate_circuit(request: Request, rotation_request: Optional[CircuitRotationRequest] = None):
    """
    Request Tor to rotate circuit (get new exit node)
    
    Args:
        rotation_request: Optional rotation reason
        
    Returns:
        CircuitRotationResponse: Previous and new exit node information
    """
    try:
        tor_manager = None
        if hasattr(request.app, "state") and hasattr(request.app.state, "tor_manager"):
            tor_manager = request.app.state.tor_manager
        
        if not tor_manager:
            raise HTTPException(status_code=503, detail="Tor integration unavailable")
        
        # Get current exit node before rotation
        previous_exit = None
        current_info = await tor_manager.get_exit_node_info()
        if current_info:
            previous_exit = current_info.get("ip") or current_info.get("address")
        
        # Perform rotation
        success = await tor_manager.rotate_circuit()
        if not success:
            raise HTTPException(status_code=500, detail="Circuit rotation failed")
        
        # Get new exit node after rotation
        new_exit = None
        new_info = await tor_manager.get_exit_node_info()
        if new_info:
            new_exit = new_info.get("ip") or new_info.get("address")
        
        reason = rotation_request.reason if rotation_request else None
        if reason:
            logger.info(f"Circuit rotated ({reason}): {previous_exit} -> {new_exit}")
        else:
            logger.info(f"Circuit rotated: {previous_exit} -> {new_exit}")
        
        return CircuitRotationResponse(
            status="rotated",
            previous_exit=previous_exit,
            new_exit=new_exit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rotate circuit: {e}")
        raise HTTPException(status_code=500, detail="Failed to rotate circuit")


@router.post("/tor/transaction/route")
async def route_transaction_through_tor(request: Request, tx_request: TransactionTorRequest):
    """
    Route a transaction through Tor network
    
    Args:
        tx_request: Transaction routing request
        
    Returns:
        Transaction routing status with anonymity metadata
    """
    try:
        tor_manager = None
        if hasattr(request.app, "state") and hasattr(request.app.state, "tor_manager"):
            tor_manager = request.app.state.tor_manager
        
        if not tor_manager:
            raise HTTPException(status_code=503, detail="Tor integration unavailable")
        
        result = await tor_manager.route_transaction_through_tor(
            transaction_hex=tx_request.transaction_hex,
            chain=tx_request.chain
        )
        
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("error", "Routing failed"))
        
        logger.info(f"Transaction routed through Tor: {tx_request.chain}")
        
        return {
            "status": "routed",
            "chain": tx_request.chain,
            "anonymity_level": tx_request.anonymity_level,
            "tor_routing": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to route transaction through Tor: {e}")
        raise HTTPException(status_code=500, detail="Failed to route transaction")


@router.get("/tor/anonymity/verify")
async def verify_anonymity(request: Request):
    """
    Verify current anonymity status
    
    Returns:
        Anonymity verification details
    """
    try:
        tor_manager = None
        if hasattr(request.app, "state") and hasattr(request.app.state, "tor_manager"):
            tor_manager = request.app.state.tor_manager
        
        if not tor_manager:
            return {
                "anonymity": "unavailable",
                "tor_connected": False
            }
        
        verification = await tor_manager.verify_anonymity()
        return verification
        
    except Exception as e:
        logger.error(f"Failed to verify anonymity: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify anonymity")


@router.get("/tor/exit-ip")
async def get_exit_ip(request: Request):
    """
    Get current exit node IP address
    
    Returns:
        Exit node IP and location information
    """
    try:
        tor_manager = None
        if hasattr(request.app, "state") and hasattr(request.app.state, "tor_manager"):
            tor_manager = request.app.state.tor_manager
        
        if not tor_manager:
            raise HTTPException(status_code=503, detail="Tor integration unavailable")
        
        exit_info = await tor_manager.get_exit_node_info()
        if exit_info:
            return {
                "status": "ok",
                "exit_ip": exit_info.get("ip"),
                "exit_node": exit_info
            }
        else:
            raise HTTPException(status_code=503, detail="Cannot retrieve exit node information")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get exit IP: {e}")
        raise HTTPException(status_code=500, detail="Failed to get exit IP")
