"""
Lucid Session Management API Service
Cluster: Session Management
Port: 8080

Features:
- Session creation, retrieval, and management
- Session state tracking and updates
- Session metadata and configuration
- Session lifecycle management
- MongoDB integration for session storage
- Redis caching for session data
- FastAPI-based REST API
"""

from .session_api import SessionAPI
from .routes import router

__all__ = [
    'SessionAPI',
    'router'
]

__version__ = "1.0.0"
__cluster__ = "session-management"
__port__ = 8080
