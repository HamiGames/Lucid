# Path: RDP/client/__init__.py
# Lucid RDP Client Module - Client-side RDP functionality
# Implements R-MUST-003: Remote Desktop Host Support with client connectivity
# LUCID-STRICT Layer 2 Service Integration

"""
RDP Client Module

This module provides client-side RDP functionality including:
- RDP client connection management
- Connection pooling and reuse
- Platform-specific RDP clients
- Connection monitoring and metrics
"""

from .rdp_client import RDPClient, ClientConfig, ClientConnectionState, ConnectionMetrics
from .connection_manager import ConnectionManager, ConnectionPoolConfig

__all__ = [
    "RDPClient",
    "ClientConfig",
    "ClientConnectionState", 
    "ConnectionMetrics",
    "ConnectionManager",
    "ConnectionPoolConfig"
]
