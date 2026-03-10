"""
LUCID TRON Relay - Relay API Endpoints
Relay management and status endpoints
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

from config import config
from services.relay_service import relay_service
from services.cache_manager import cache_manager
from services.verification_service import verification_service

router = APIRouter()


class RelayStatusResponse(BaseModel):
    """Relay status response"""
    relay_id: str
    node_id: Optional[str]
    mode: str
    network: str
    initialized: bool
    tron_connected: bool
    registered_with_master: bool
    uptime_seconds: float
    started_at: str


class RelayStatsResponse(BaseModel):
    """Relay statistics response"""
    relay_stats: Dict[str, Any]
    cache_stats: Dict[str, Any]
    verification_stats: Dict[str, Any]


class RegisterRequest(BaseModel):
    """Registration request from this relay to master"""
    master_url: str = Field(..., description="Master service URL to register with")


class RegistrationResponse(BaseModel):
    """Registration response"""
    success: bool
    message: str
    relay_id: str


@router.get("/status", response_model=RelayStatusResponse)
async def get_relay_status():
    """Get relay status"""
    from main import service_state
    
    tron_connected = await relay_service.check_tron_connection()
    
    uptime = 0
    if service_state.get("started_at"):
        started = datetime.fromisoformat(service_state["started_at"])
        uptime = (datetime.utcnow() - started).total_seconds()
    
    return RelayStatusResponse(
        relay_id=config.relay_id,
        node_id=config.node_id,
        mode=config.relay_mode.value,
        network=config.tron_network,
        initialized=relay_service.initialized,
        tron_connected=tron_connected,
        registered_with_master=service_state.get("registered_with_master", False),
        uptime_seconds=uptime,
        started_at=service_state.get("started_at", "")
    )


@router.get("/stats", response_model=RelayStatsResponse)
async def get_relay_stats():
    """Get relay statistics"""
    return RelayStatsResponse(
        relay_stats=relay_service.get_stats(),
        cache_stats=cache_manager.get_stats(),
        verification_stats=verification_service.get_stats()
    )


@router.get("/capabilities")
async def get_capabilities():
    """Get relay capabilities"""
    return {
        "relay_id": config.relay_id,
        "mode": config.relay_mode.value,
        "capabilities": {
            "cache": config.cache_enabled,
            "verification": config.verification_enabled,
            "rate_limit": config.rate_limit_enabled,
            "metrics": config.metrics_enabled
        },
        "network": config.tron_network,
        "has_api_key": bool(config.get_api_key()),
        "confirmation_threshold": config.confirmation_threshold,
        "cache_ttls": {
            "block": config.cache_block_ttl,
            "transaction": config.cache_transaction_ttl,
            "account": config.cache_account_ttl
        },
        "security": "READ-ONLY - No private key access"
    }


@router.post("/register", response_model=RegistrationResponse)
async def register_with_master(request: RegisterRequest):
    """Register this relay with a master service"""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            registration_data = {
                "relay_id": config.relay_id,
                "node_id": config.node_id,
                "relay_url": f"http://{config.service_host}:{config.service_port}",
                "capabilities": ["cache", "verify", "monitor"],
                "mode": config.relay_mode.value,
                "api_key_available": bool(config.get_api_key()),
                "network": config.tron_network
            }
            
            response = await client.post(
                f"{request.master_url}/api/v1/relays/register",
                json=registration_data
            )
            
            if response.status_code == 200:
                from main import service_state
                service_state["registered_with_master"] = True
                
                return RegistrationResponse(
                    success=True,
                    message=f"Successfully registered with master: {request.master_url}",
                    relay_id=config.relay_id
                )
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Registration failed: {response.text}"
                )
                
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to master: {str(e)}"
        )


@router.post("/deregister")
async def deregister_from_master():
    """Deregister this relay from master"""
    import httpx
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{config.tron_master_url}/api/v1/relays/deregister",
                json={"relay_id": config.relay_id}
            )
            
            from main import service_state
            service_state["registered_with_master"] = False
            
            return {
                "success": True,
                "message": "Deregistered from master",
                "relay_id": config.relay_id
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Deregistration error: {str(e)}",
            "relay_id": config.relay_id
        }


@router.get("/config")
async def get_config():
    """Get relay configuration (non-sensitive)"""
    return {
        "relay_id": config.relay_id,
        "node_id": config.node_id,
        "service_name": config.service_name,
        "service_version": config.service_version,
        "service_port": config.service_port,
        "mode": config.relay_mode.value,
        "network": config.tron_network,
        "tron_endpoint": config.get_tron_endpoint(),
        "master_url": config.tron_master_url,
        "cache_enabled": config.cache_enabled,
        "cache_max_size_mb": config.cache_max_size_mb,
        "verification_enabled": config.verification_enabled,
        "confirmation_threshold": config.confirmation_threshold,
        "rate_limit_enabled": config.rate_limit_enabled,
        "log_level": config.log_level.value,
        "security": "READ-ONLY - No private key access"
    }

