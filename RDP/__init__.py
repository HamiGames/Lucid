# Path: RDP/__init__.py
# Lucid RDP Module - Main RDP package initialization
# Implements R-MUST-003: Remote Desktop Host Support
# LUCID-STRICT Layer 2 Service Integration

"""
Lucid RDP Module

This package provides comprehensive Remote Desktop Protocol (RDP) functionality
for the Lucid RDP system, including:

- Client connection management
- Server session handling
- Protocol implementation
- Recording capabilities
- Security controls
- Access management

Modules:
- client: RDP client connection management
- server: RDP server and session management
- protocol: RDP protocol implementation
- recorder: Session recording and monitoring
- security: Access control and validation
"""

__version__ = "1.0.0"
__author__ = "Lucid RDP Team"
__description__ = "Lucid RDP Remote Desktop Protocol Implementation"

# Import main components for easy access
from .client.rdp_client import RDPClient, ClientConfig
from .server.session_controller import SessionController
from .security.access_controller import AccessController

__all__ = [
    "RDPClient",
    "ClientConfig", 
    "SessionController",
    "AccessController"
]
