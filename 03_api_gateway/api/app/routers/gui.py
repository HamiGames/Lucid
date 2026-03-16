"""
GUI API Bridge Proxy Endpoints Router

File: 03_api_gateway/api/app/routers/gui.py
Purpose: Proxy endpoints to gui_api_bridge service for Electron GUI integration

Architecture Note: This router proxies to gui_api_bridge service (isolated GUI integration)
"""

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


from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from ..services.gui_bridge_service import gui_bridge_service
router = APIRouter()


class ElectronConnectionRequest(BaseModel):
    """Electron GUI connection request"""
    session_id: str
    client_version: str
    platform: str


class ElectronDisconnectionRequest(BaseModel):
    """Electron GUI disconnection request"""
    session_id: str


@router.get("/info")
async def get_gui_bridge_info():
    """Get GUI API Bridge service information"""
    try:
        from ..services.gui_bridge_service import gui_bridge_service
        await gui_bridge_service.initialize()
        info = await gui_bridge_service.get_bridge_info()
        return info
    except Exception as e:
        logger.error(f"Failed to get GUI bridge info: {e}")
        raise HTTPException(status_code=503, detail=f"GUI Bridge unavailable: {str(e)}")


@router.get("/health")
async def check_gui_bridge_health():
    """Check GUI API Bridge service health"""
    try:
        from ..services.gui_bridge_service import gui_bridge_service
        is_healthy = await gui_bridge_service.health_check()
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "service": "gui_api_bridge",
            "connected": is_healthy
        }
    except Exception as e:
        logger.error(f"GUI bridge health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "gui_api_bridge",
            "connected": False,
            "error": str(e)
        }


@router.get("/status")
async def get_gui_bridge_status():
    """Get GUI API Bridge status"""
    try:
        from ..services.gui_bridge_service import gui_bridge_service
        await gui_bridge_service.initialize()
        return {
            "connected": gui_bridge_service.is_connected,
            "last_check": gui_bridge_service.last_check.isoformat() if gui_bridge_service.last_check else None,
            "base_url": gui_bridge_service.base_url,
            "status": "connected" if gui_bridge_service.is_connected else "disconnected"
        }
    except Exception as e:
        logger.error(f"Failed to get GUI bridge status: {e}")
        raise HTTPException(status_code=503, detail=f"GUI Bridge unavailable: {str(e)}")


@router.post("/electron/connect")
async def electron_gui_connect(request: ElectronConnectionRequest = Body(...)):
    """Handle Electron GUI connection to API Gateway"""
    try:
        from ..services.gui_bridge_service import gui_bridge_service
        await gui_bridge_service.initialize()
        result = await gui_bridge_service.handle_electron_connect(request.dict())
        logger.info(f"Electron GUI connected: session_id={request.session_id}")
        return result
    except Exception as e:
        logger.error(f"Electron GUI connection failed: {e}")
        raise HTTPException(status_code=503, detail=f"Connection failed: {str(e)}")


@router.post("/electron/disconnect")
async def electron_gui_disconnect(request: ElectronDisconnectionRequest = Body(...)):
    """Handle Electron GUI disconnection from API Gateway"""
    try:
        from ..services.gui_bridge_service import gui_bridge_service
        await gui_bridge_service.initialize()
        result = await gui_bridge_service.handle_electron_disconnect(request.session_id)
        logger.info(f"Electron GUI disconnected: session_id={request.session_id}")
        return result
    except Exception as e:
        logger.error(f"Electron GUI disconnection failed: {e}")
        raise HTTPException(status_code=503, detail=f"Disconnection failed: {str(e)}")


@router.get("/electron/routes")
async def list_electron_gui_routes():
    """List available routes for Electron GUI"""
    return {
        "routes": [
            "GET /api/v1/gui/info",
            "GET /api/v1/gui/health",
            "GET /api/v1/gui/status",
            "POST /api/v1/gui/electron/connect",
            "POST /api/v1/gui/electron/disconnect",
            "GET /api/v1/gui/electron/routes"
        ],
        "description": "GUI API Bridge integration endpoints for Electron GUI"
    }
