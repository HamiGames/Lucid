#!/usr/bin/env python3
"""
Lucid Admin Interface - Cross-Container Service Modules
Step 24: Admin Container & Integration

Cross-container linking modules for inter-service communication.
Provides service discovery, HTTP client wrappers, and service registry integration.
"""

from .service_client import ServiceClient, get_service_client
from .service_discovery import ServiceDiscovery, get_service_discovery
from .service_registry import ServiceRegistry, get_service_registry

__all__ = [
    "ServiceClient",
    "get_service_client",
    "ServiceDiscovery",
    "get_service_discovery",
    "ServiceRegistry",
    "get_service_registry",
]

