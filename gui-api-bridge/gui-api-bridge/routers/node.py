"""
Node Operator API Routes
File: gui-api-bridge/gui-api-bridge/routers/node.py
Endpoints: /api/v1/node
Allowed methods: GET, POST, PUT
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/node", tags=["node"])


@router.get("/")
async def list_node_endpoints():
    """List available node endpoints"""
    return {
        "endpoints": [
            "GET /api/v1/node/status",
            "GET /api/v1/node/earnings",
        ]
    }


@router.get("/status")
async def get_node_status(request: Request):
    """Get node operator status"""
    user = getattr(request.state, "user", None)
    if not user or user.get("role") != "node_operator":
        return JSONResponse(status_code=403, content={"detail": "Forbidden"})
    
    return {
        "status": "active",
        "role": "node_operator",
    }
