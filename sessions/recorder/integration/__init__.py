#!/usr/bin/env python3
"""
Session Recorder Integration Module
Provides clients for interacting with external services
"""

from .service_base import ServiceClientBase, ServiceError, ServiceTimeoutError
from .integration_manager import IntegrationManager

# Import clients if needed
try:
    from .blockchain_engine_client import BlockchainEngineClient
    from .node_manager_client import NodeManagerClient
    from .api_gateway_client import APIGatewayClient
    from .auth_service_client import AuthServiceClient
    from .session_pipeline_client import SessionPipelineClient
except ImportError:
    # Clients will be created dynamically
    pass

__all__ = [
    'ServiceClientBase',
    'ServiceError',
    'ServiceTimeoutError',
    'IntegrationManager',
]

