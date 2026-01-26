"""
WebSocket Routes
File: gui-api-bridge/gui-api-bridge/routers/websocket.py
Endpoints: /ws
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..services.websocket_service import WebSocketService

logger = logging.getLogger(__name__)

router = APIRouter()
ws_service = WebSocketService()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    try:
        await ws_service.connect(websocket)
        logger.info("WebSocket connected")
        
        while True:
            data = await websocket.receive_text()
            logger.debug(f"WebSocket message: {data}")
            
            # Echo message back
            await websocket.send_text(f"Echo: {data}")
    
    except WebSocketDisconnect:
        await ws_service.disconnect(websocket)
        logger.info("WebSocket disconnected")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await ws_service.disconnect(websocket)
