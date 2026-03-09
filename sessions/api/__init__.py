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
from sessions.api.config import SessionAPISettings, SessionAPIConfig
from sessions.api.session_api import SessionStatus, RDPConfig, RecordingConfig, StorageConfig, SessionMetadata, CreateSessionRequest, UpdateSessionRequest, SessionResponse, SessionListResponse, ChunkResponse, ChunkListResponse, PipelineResponse, SessionAPI
from sessions.api.routes import router
import sessions.api.integration as integration
import sessions.api.integration.rdp_controller_client as rdp_controller_client
import sessions.api.entrypoint as entrypoint
import sessions.api.main as main

__all__ = [
   'SessionAPI', 'router', 'SessionStatus', 'CreateSessionRequest', 'UpdateSessionRequest',
   'SessionResponse', 'SessionListResponse', 
   'ChunkResponse', 'ChunkListResponse', 'PipelineResponse', 'StatisticsResponse',
   'SessionAPISettings','integration', 'entrypoint', 'rdp_controller_client',
   'main', 'SessionAPIConfig', 'RDPConfig', 'RecordingConfig', 'StorageConfig', 'SessionMetadata'
]

__version__ = "1.0.0"
__cluster__ = "session-management"
__port__ = 8080
