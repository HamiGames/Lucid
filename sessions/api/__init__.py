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
from ..api.config import SessionAPISettings, SessionAPIConfig
from ..api.session_api import SessionAPI, SessionStatus, CreateSessionRequest, UpdateSessionRequest, SessionResponse, SessionListResponse, ChunkResponse, ChunkListResponse, PipelineResponse, StatisticsResponse
from ..api.routes import router
from ..api.integration.rdp_controller_client import RDPControllerClient


__all__ = [
   'SessionAPI', 'router', 'SessionStatus', 'CreateSessionRequest', 'UpdateSessionRequest', 'SessionResponse', 'SessionListResponse', 
   'ChunkResponse', 'ChunkListResponse', 'PipelineResponse', 'StatisticsResponse', 'SessionAPISettings',
   'RDPControllerClient', 'SessionAPIConfig'
]

__version__ = "1.0.0"
__cluster__ = "session-management"
__port__ = 8080
