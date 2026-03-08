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

from sessions.api.session_api import SessionAPI, SessionStatus, RDPConfig, RecordingConfig, StorageConfig, SessionMetadata, CreateSessionRequest, UpdateSessionRequest, SessionResponse, SessionListResponse, ChunkResponse, ChunkListResponse, PipelineResponse, StatisticsResponse
from sessions.api.routes import router
from sessions.api.config import SessionAPISettings
from sessions.api.integration.rdp_controller_client import RDPControllerClient
from  sessions.encryption.encryptor import SessionEncryptor, EncryptedChunk
from sessions.processor.chunk_processor import ChunkProcessor , ChunkProcessorService, ChunkMetadata

__all__ = [
    'SessionAPI',
    'router',
    'SessionAPISettings',
    'RDPControllerClient',
    'SessionEncryptor',
    'ChunkProcessor',
    'ChunkProcessorService',
    'ChunkMetadata',
    'SessionStatus',
    'RDPConfig',
    'RecordingConfig',
    'StorageConfig',
    'SessionMetadata',
    'CreateSessionRequest',
    'UpdateSessionRequest',
    'SessionResponse',
]

__version__ = "1.0.0"
__cluster__ = "session-management"
__port__ = 8080
