"""
Real-time Event Streaming Router
File: gui-docker-manager/gui-docker-manager/routers/events.py

WebSocket endpoint for real-time Docker event streaming.
"""

import logging
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from typing import Set, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()


class EventConnectionManager:
    """Manages WebSocket connections for event streaming"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """Register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Unregister a WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(f"Client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending to client: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)


manager = EventConnectionManager()


async def get_docker_manager():
    """Dependency to get Docker manager instance"""
    from ..main import docker_manager
    if not docker_manager:
        raise HTTPException(status_code=503, detail="Docker Manager not initialized")
    return docker_manager


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    manager_dep=Depends(get_docker_manager)
):
    """
    WebSocket endpoint for real-time container events

    Usage:
        ws = new WebSocket('ws://localhost:8098/api/v1/events/ws');
        ws.addEventListener('message', (event) => {
            const data = JSON.parse(event.data);
            console.log('Event:', data.action, data.container_name);
        });
    """
    await manager.connect(websocket)

    try:
        while True:
            # Receive filter configuration from client
            data = await websocket.receive_text()

            try:
                filters = json.loads(data)
            except json.JSONDecodeError:
                await manager.send_personal(websocket, {
                    "error": "Invalid JSON",
                    "timestamp": datetime.utcnow().isoformat()
                })
                continue

            # Configure filters
            container_name_filter = filters.get("container_names", [])
            event_types = filters.get("event_types", ["start", "stop", "restart"])

            # Send confirmation
            await manager.send_personal(websocket, {
                "type": "subscription",
                "status": "subscribed",
                "filters": filters,
                "timestamp": datetime.utcnow().isoformat()
            })

            # Stream events (this would normally be done via Docker daemon events)
            await stream_container_events(
                websocket,
                manager_dep,
                container_name_filter,
                event_types
            )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def stream_container_events(
    websocket: WebSocket,
    docker_manager,
    container_name_filter: Optional[list] = None,
    event_types: Optional[list] = None
):
    """
    Stream Docker container events to WebSocket client

    Args:
        websocket: WebSocket connection
        docker_manager: Docker manager service instance
        container_name_filter: Optional list of container names to monitor
        event_types: Optional list of event types to monitor
    """
    try:
        # Subscribe to Docker events
        async for event in docker_manager.docker_client.stream_events():

            # Parse event
            event_type = event.get("Action", "")
            actor = event.get("Actor", {})
            container_id = actor.get("ID", "")
            container_name = actor.get("Attributes", {}).get("name", "")

            # Apply filters
            if container_name_filter and container_name not in container_name_filter:
                continue

            if event_types and event_type not in event_types:
                continue

            # Format event for client
            formatted_event = {
                "type": "container_event",
                "action": event_type,
                "container_id": container_id,
                "container_name": container_name,
                "status": actor.get("Attributes", {}).get("status", ""),
                "timestamp": datetime.utcnow().isoformat(),
                "raw_event": event
            }

            # Send to client
            await websocket.send_json(formatted_event)

    except WebSocketDisconnect:
        logger.info("Client disconnected from event stream")
    except Exception as e:
        logger.error(f"Error streaming events: {e}")
        try:
            await websocket.send_json({
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        except:
            pass


@router.get("/health/stream")
async def get_health_stream(manager=Depends(get_docker_manager)):
    """
    Get health status stream configuration

    Returns info about connecting to the WebSocket endpoint
    """
    return {
        "status": "available",
        "websocket_url": "ws://localhost:8098/api/v1/events/ws",
        "filters_example": {
            "container_names": ["lucid-mongodb", "api-gateway"],
            "event_types": ["start", "stop", "restart"]
        },
        "supported_event_types": [
            "start", "stop", "restart", "pause", "unpause",
            "create", "destroy", "remove", "die", "kill"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/subscribe")
async def subscribe_to_events(
    container_names: Optional[list] = None,
    event_types: Optional[list] = None,
    manager=Depends(get_docker_manager)
):
    """
    REST endpoint to get subscription info (WebSocket URL)

    Returns the WebSocket URL and configuration for event streaming
    """
    return {
        "status": "ready",
        "message": "Use WebSocket endpoint to stream events",
        "websocket_url": "ws://localhost:8098/api/v1/events/ws",
        "subscribe_with": {
            "container_names": container_names or [],
            "event_types": event_types or ["start", "stop", "restart"]
        },
        "supported_actions": [
            "start", "stop", "restart", "pause", "unpause",
            "create", "destroy", "remove", "die", "kill"
        ],
        "timestamp": datetime.utcnow().isoformat()
    }
