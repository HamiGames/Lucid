"""
WebSocket Service
File: gui-api-bridge/gui-api-bridge/services/websocket_service.py
"""

import logging

logger = logging.getLogger(__name__)


class WebSocketService:
    """WebSocket connection management"""
    
    def __init__(self):
        """Initialize WebSocket service"""
        self.connections = []
    
    async def connect(self, websocket):
        """Accept and track WebSocket connection"""
        await websocket.accept()
        self.connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.connections)}")
    
    async def disconnect(self, websocket):
        """Remove WebSocket connection"""
        self.connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.connections)}")
    
    async def broadcast(self, message: str):
        """Broadcast message to all connections"""
        for connection in self.connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {e}")
