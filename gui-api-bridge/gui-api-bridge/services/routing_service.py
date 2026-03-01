"""
Routing Service for API Request Routing
File: gui-api-bridge/gui-api-bridge/services/routing_service.py
"""

import logging
from typing import Optional, Dict, Any
from fastapi import Request
from ..config import GuiAPIBridgeSettings
from ..integration.integration_manager import IntegrationManager

logger = logging.getLogger(__name__)


class RoutingService:
    """Service for routing API requests to appropriate backend services"""
    
    def __init__(self, config: GuiAPIBridgeSettings, integration_manager: IntegrationManager):
        """Initialize routing service"""
        self.config = config
        self.integration_manager = integration_manager
    
    async def route_request(
        self,
        request: Request,
        path: str,
        method: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Route request to appropriate backend service
        
        Args:
            request: FastAPI request object
            path: API path being requested
            method: HTTP method
        
        Returns:
            Response from backend service or None
        """
        try:
            logger.debug(f"Routing {method} {path}")
            
            # Determine target service based on path
            if path.startswith("/api/v1/user/"):
                return await self._route_user_request(request, path, method)
            elif path.startswith("/api/v1/developer/"):
                return await self._route_developer_request(request, path, method)
            elif path.startswith("/api/v1/node/"):
                return await self._route_node_request(request, path, method)
            elif path.startswith("/api/v1/admin/"):
                return await self._route_admin_request(request, path, method)
            else:
                logger.warning(f"Unknown route: {path}")
                return None
        
        except Exception as e:
            logger.error(f"Error routing request: {e}")
            return None
    
    async def _route_user_request(
        self,
        request: Request,
        path: str,
        method: str,
    ) -> Optional[Dict[str, Any]]:
        """Route user API requests"""
        # Handle session recovery
        if "/sessions/" in path and "/recover" in path:
            return await self._handle_session_recovery(request, path)
        
        return None
    
    async def _route_developer_request(
        self,
        request: Request,
        path: str,
        method: str,
    ) -> Optional[Dict[str, Any]]:
        """Route developer API requests"""
        if "/sessions/" in path and "/recover" in path:
            return await self._handle_session_recovery(request, path)
        
        return None
    
    async def _route_node_request(
        self,
        request: Request,
        path: str,
        method: str,
    ) -> Optional[Dict[str, Any]]:
        """Route node operator API requests"""
        return None
    
    async def _route_admin_request(
        self,
        request: Request,
        path: str,
        method: str,
    ) -> Optional[Dict[str, Any]]:
        """Route admin API requests"""
        if "/sessions/" in path and "/recover" in path:
            return await self._handle_session_recovery(request, path)
        
        return None
    
    async def _handle_session_recovery(
        self,
        request: Request,
        path: str,
    ) -> Optional[Dict[str, Any]]:
        """Handle session token recovery request"""
        try:
            # Extract session_id from path
            # Format: /api/v1/{role}/sessions/{session_id}/recover
            parts = path.split("/")
            if len(parts) < 5:
                logger.warning(f"Invalid session recovery path: {path}")
                return None
            
            session_id = parts[4]
            
            # Get request body
            try:
                body = await request.json()
            except:
                body = {}
            
            owner_address = body.get("owner_address")
            if not owner_address:
                logger.warning(f"Missing owner_address for session recovery")
                return {"error": "owner_address required"}
            
            # Call blockchain client to recover token
            token = await self.integration_manager.blockchain_client.recover_session_token(
                session_id,
                owner_address,
            )
            
            if token:
                return {
                    "status": "success",
                    "session_id": session_id,
                    "token": token,
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to recover session token",
                }
        
        except Exception as e:
            logger.error(f"Error handling session recovery: {e}")
            return {"error": str(e)}
    
    def get_service_for_endpoint(self, endpoint: str) -> str:
        """Determine which service to route to based on endpoint"""
        if "session" in endpoint:
            return "session-api"
        elif "blockchain" in endpoint:
            return "blockchain-engine"
        elif "auth" in endpoint:
            return "auth-service"
        elif "node" in endpoint:
            return "node-management"
        elif "admin" in endpoint:
            return "admin-interface"
        else:
            return "api-gateway"
