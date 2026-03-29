#!/usr/bin/env python3
"""
File: /app/admin/services/__init__.py
x-lucid-file-path: /app/admin/services/__init__.py
x-lucid-file-type: python

Lucid Admin Interface - Cross-Container Service Modules
Step 24: Admin Container & Integration

Cross-container linking modules for inter-service communication.
Provides service discovery, HTTP client wrappers, and service registry integration.
"""

from admin.services.service_client import(
    ServiceClient, get_service_client, ServiceStatus, ServiceEndpoint, close_service_client)
from admin.services.service_discovery import (
    ServiceDiscovery, get_service_discovery, DiscoveryMethod, ServiceInfo, close_service_discovery)
from admin.services.service_registry import (
    ServiceRegistry, get_service_registry, ServiceRegistry, get_service_registry)
from admin.utils.logging import get_logger
logger = get_logger(__name__)

__all__ = [
    "ServiceClient",
    "get_service_client",
    "ServiceDiscovery",
    "get_service_discovery",
    "ServiceRegistry",
    "get_service_registry",
    "ServiceStatus", "ServiceEndpoint", "close_service_client",
    "DiscoveryMethod", "ServiceInfo", "close_service_discovery",
    "ServiceRegistry", "get_service_registry", "close_service_registry",
    "logger", "logging"
]

