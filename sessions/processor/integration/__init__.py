#!/usr/bin/env python3
"""
Session Processor Integration Module
Provides clients for interacting with external services
"""

from .service_base import ServiceClientBase, ServiceError, ServiceTimeoutError
from .integration_manager import IntegrationManager

# Import clients if available
try:
    from .session_pipeline_client import SessionPipelineClient
    from .session_storage_client import SessionStorageClient
except ImportError:
    SessionPipelineClient = None
    SessionStorageClient = None

__all__ = [
    'ServiceClientBase',
    'ServiceError',
    'ServiceTimeoutError',
    'IntegrationManager',
    'SessionPipelineClient',
    'SessionStorageClient',
]

