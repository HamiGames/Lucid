"""
Integration Manager for Backend Services
File: gui-api-bridge/gui-api-bridge/integration/integration_manager.py
Pattern: Follow sessions/pipeline/integration/ structure
Lazy initialization of all backend service clients
"""

import logging
from typing import Optional
from ..config import GuiAPIBridgeSettings
from .blockchain_client import BlockchainEngineClient
from .api_gateway_client import APIGatewayClient
from .auth_service_client import AuthServiceClient
from .session_api_client import SessionAPIClient
from .node_management_client import NodeManagementClient
from .admin_interface_client import AdminInterfaceClient
from .tron_client import TronClient

logger = logging.getLogger(__name__)


class IntegrationManager:
    """
    Centralized manager for all backend service integrations
    Handles lazy initialization and lifecycle management
    """
    
    def __init__(self, config: GuiAPIBridgeSettings):
        """Initialize integration manager"""
        self.config = config
        
        # Lazy-loaded clients
        self._api_gateway_client: Optional[APIGatewayClient] = None
        self._blockchain_client: Optional[BlockchainEngineClient] = None
        self._auth_service_client: Optional[AuthServiceClient] = None
        self._session_api_client: Optional[SessionAPIClient] = None
        self._node_management_client: Optional[NodeManagementClient] = None
        self._admin_interface_client: Optional[AdminInterfaceClient] = None
        self._tron_client: Optional[TronClient] = None
        
        self._initialized = False
    
    async def initialize(self):
        """Initialize all backend service clients"""
        try:
            logger.info("Initializing backend service clients")
            
            # Initialize all clients
            await self._init_api_gateway_client()
            await self._init_blockchain_client()
            await self._init_auth_service_client()
            await self._init_session_api_client()
            await self._init_node_management_client()
            await self._init_admin_interface_client()
            await self._init_tron_client()
            
            self._initialized = True
            logger.info("All backend service clients initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize integration manager: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup all backend service clients"""
        try:
            logger.info("Cleaning up backend service clients")
            
            clients = [
                self._api_gateway_client,
                self._blockchain_client,
                self._auth_service_client,
                self._session_api_client,
                self._node_management_client,
                self._admin_interface_client,
                self._tron_client,
            ]
            
            for client in clients:
                if client:
                    await client.cleanup()
            
            logger.info("All backend service clients cleaned up")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def _init_api_gateway_client(self):
        """Initialize API Gateway client"""
        try:
            self._api_gateway_client = APIGatewayClient(self.config)
            await self._api_gateway_client.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize API Gateway client: {e}")
            raise
    
    async def _init_blockchain_client(self):
        """Initialize Blockchain Engine client"""
        try:
            self._blockchain_client = BlockchainEngineClient(self.config)
            await self._blockchain_client.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize Blockchain Engine client: {e}")
            raise
    
    async def _init_auth_service_client(self):
        """Initialize Auth Service client"""
        try:
            self._auth_service_client = AuthServiceClient(self.config)
            await self._auth_service_client.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize Auth Service client: {e}")
            raise
    
    async def _init_session_api_client(self):
        """Initialize Session API client"""
        try:
            self._session_api_client = SessionAPIClient(self.config)
            await self._session_api_client.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize Session API client: {e}")
            raise
    
    async def _init_node_management_client(self):
        """Initialize Node Management client"""
        try:
            self._node_management_client = NodeManagementClient(self.config)
            await self._node_management_client.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize Node Management client: {e}")
            raise
    
    async def _init_admin_interface_client(self):
        """Initialize Admin Interface client"""
        try:
            self._admin_interface_client = AdminInterfaceClient(self.config)
            await self._admin_interface_client.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize Admin Interface client: {e}")
            raise
    
    async def _init_tron_client(self):
        """Initialize TRON Payment client"""
        try:
            self._tron_client = TronClient(self.config)
            await self._tron_client.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize TRON Payment client: {e}")
            raise
    
    # Properties for lazy access
    @property
    def api_gateway_client(self) -> APIGatewayClient:
        """Get API Gateway client"""
        if not self._api_gateway_client:
            raise RuntimeError("API Gateway client not initialized")
        return self._api_gateway_client
    
    @property
    def blockchain_client(self) -> BlockchainEngineClient:
        """Get Blockchain Engine client"""
        if not self._blockchain_client:
            raise RuntimeError("Blockchain Engine client not initialized")
        return self._blockchain_client
    
    @property
    def auth_service_client(self) -> AuthServiceClient:
        """Get Auth Service client"""
        if not self._auth_service_client:
            raise RuntimeError("Auth Service client not initialized")
        return self._auth_service_client
    
    @property
    def session_api_client(self) -> SessionAPIClient:
        """Get Session API client"""
        if not self._session_api_client:
            raise RuntimeError("Session API client not initialized")
        return self._session_api_client
    
    @property
    def node_management_client(self) -> NodeManagementClient:
        """Get Node Management client"""
        if not self._node_management_client:
            raise RuntimeError("Node Management client not initialized")
        return self._node_management_client
    
    @property
    def admin_interface_client(self) -> AdminInterfaceClient:
        """Get Admin Interface client"""
        if not self._admin_interface_client:
            raise RuntimeError("Admin Interface client not initialized")
        return self._admin_interface_client
    
    @property
    def tron_client(self) -> TronClient:
        """Get TRON Payment client"""
        if not self._tron_client:
            raise RuntimeError("TRON Payment client not initialized")
        return self._tron_client
