"""
Admin API Routes
File: gui-api-bridge/gui-api-bridge/routers/admin.py
Endpoints: /api/v1/admin
Allowed methods: GET, POST, PUT, DELETE, PATCH
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/")
async def list_admin_endpoints():
    """List available admin endpoints"""
    return {
        "endpoints": [
            "GET /api/v1/admin/status",
            "GET /api/v1/admin/services",
            "POST /api/v1/admin/sessions/{session_id}/recover",
        ]
    }


@router.get("/status")
async def get_admin_status(request: Request):
    """Get admin status"""
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    
    return {
        "status": "active",
        "role": "admin",
    }


@router.get("/services")
async def list_services(request: Request):
    """List backend services"""
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "admin":
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    
    return {
        "services": [
            "api-gateway",
            "blockchain-engine",
            "auth-service",
            "session-api",
            "node-management",
            "admin-interface",
            "tron-client",
        ]
    }
