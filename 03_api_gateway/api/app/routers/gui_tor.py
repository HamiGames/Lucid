"""
GUI Tor Manager Proxy Endpoints Router

File: 03_api_gateway/api/app/routers/gui_tor.py
Purpose: Proxy endpoints to gui_tor_manager service for Tor management via GUI

Architecture Note: This router proxies to gui_tor_manager service
"""


from fastapi import APIRouter, HTTPException
import os
from ..config import Settings, get_settings
log_level = os.getenv(get_settings().LOG_LEVEL(), "INFO").upper()
settings = os.getenv(Settings().LOG_LEVEL(), "INFO").upper()
try:
    from ..utils.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)




router = APIRouter()


@router.get("/info")
async def get_gui_tor_manager_info():
    """Get GUI Tor Manager service information"""
    try:
        from ..services.gui_tor_manager_service import gui_tor_manager_service  # pyright: ignore[reportMissingImports]
        await gui_tor_manager_service.initialize()
        info = await gui_tor_manager_service.get_manager_info()
        return info
    except Exception as e:
        logger.error(f"Failed to get GUI Tor Manager info: {e}")
        raise HTTPException(status_code=503, detail=f"GUI Tor Manager unavailable: {str(e)}")


@router.get("/health")
async def check_gui_tor_manager_health():
    """Check GUI Tor Manager service health"""
    try:
        from ..services.gui_tor_manager_service import gui_tor_manager_service
        is_healthy = await gui_tor_manager_service.health_check()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "gui_tor_manager",
            "connected": is_healthy
        }
    except Exception as e:
        logger.error(f"GUI Tor Manager health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "gui_tor_manager",
            "connected": False,
            "error": str(e)
        }


@router.get("/status")
async def get_tor_status():
    """Get Tor proxy status via GUI Tor Manager"""
    try:
        from ..services.gui_tor_manager_service  import gui_tor_manager_service
        await gui_tor_manager_service.initialize()
        status = await gui_tor_manager_service.get_tor_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get Tor status: {e}")
        raise HTTPException(status_code=503, detail=f"Tor status check failed: {str(e)}")


@router.get("/circuits")
async def list_tor_circuits():
    """List active Tor circuits via GUI Tor Manager"""
    try:
        from ..services.gui_tor_manager_service  import gui_tor_manager_service
        await gui_tor_manager_service.initialize()
        circuits = await gui_tor_manager_service.list_circuits()
        return circuits
    except Exception as e:
        logger.error(f"Failed to list Tor circuits: {e}")
        raise HTTPException(status_code=503, detail=f"Tor circuits listing failed: {str(e)}")


@router.post("/circuits/new")
async def request_new_circuit():
    """Request new Tor circuit via GUI Tor Manager"""
    try:
        from ..services.gui_tor_manager_service  import gui_tor_manager_service
        await gui_tor_manager_service.initialize()
        result = await gui_tor_manager_service.request_new_circuit()
        logger.info("New Tor circuit requested")
        return result
    except Exception as e:
        logger.error(f"Failed to request new Tor circuit: {e}")
        raise HTTPException(status_code=503, detail=f"New circuit request failed: {str(e)}")


@router.get("/onion/address")
async def get_onion_address():
    """Get Tor onion address via GUI Tor Manager"""
    try:
        from ..services.gui_tor_manager_service  import gui_tor_manager_service
        await gui_tor_manager_service.initialize()
        address = await gui_tor_manager_service.get_onion_address()
        return address
    except Exception as e:
        logger.error(f"Failed to get onion address: {e}")
        raise HTTPException(status_code=503, detail=f"Onion address retrieval failed: {str(e)}")
