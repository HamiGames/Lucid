"""
Lucid RDP Session Controller Service
Cluster: RDP Session Management
Port: 8092

Features:
- RDP session creation and management
- Connection monitoring and health checks
- Session state tracking and updates
- Session lifecycle management
- RDP protocol handling
- Session authentication and authorization
"""

from .session_controller import SessionController
from .connection_manager import ConnectionManager

__all__ = [
    'SessionController',
    'ConnectionManager'
]

__version__ = "1.0.0"
__cluster__ = "rdp-session-controller"
__port__ = 8092
