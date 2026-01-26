"""
Developer API Routes
File: gui-api-bridge/gui-api-bridge/routers/developer.py
Endpoints: /api/v1/developer
Allowed methods: GET, POST, PUT, DELETE
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/developer", tags=["developer"])


@router.get("/")
async def list_developer_endpoints():
    """List available developer endpoints"""
    return {
        "endpoints": [
            "GET /api/v1/developer/status",
            "GET /api/v1/developer/sessions",
            "POST /api/v1/developer/sessions/{session_id}/recover",
        ]
    }


@router.get("/status")
async def get_developer_status(request: Request):
    """Get developer status"""
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "developer":
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    
    return {
        "status": "active",
        "role": "developer",
    }
