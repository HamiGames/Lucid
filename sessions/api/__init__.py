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
from sessions.pipeline.pipeline_manager import PipelineManager, PipelineState, PipelineStage
from sessions.pipeline.config import PipelineConfig, PipelineSettings
from sessions.pipeline.state_machine import PipelineState, StateTransition, StateTransitionRule
from sessions.pipeline.integration.integration_manager import IntegrationManager
from sessions.pipeline.main import PipelineManager
from sessions.pipeline.config import PipelineConfig, PipelineSettings
from sessions.pipeline.state_machine import PipelineState, StateTransition, StateTransitionRule
from sessions.pipeline.integration.integration_manager import IntegrationManager
from sessions.pipeline.main import PipelineManager, PipelineMetrics, SessionPipeline
from sessions.api.session_api import SessionAPI, SessionStatus, RDPConfig, RecordingConfig, StorageConfig, SessionMetadata, CreateSessionRequest, UpdateSessionRequest, SessionResponse, SessionListResponse, ChunkResponse, ChunkListResponse, PipelineResponse, StatisticsResponse
from sessions.api.routes import router
from sessions.pipeline.integration.integration_manager import IntegrationManager, IntegrationState, IntegrationStage
from sessions.pipeline.integration.service_base import ServiceClientBase, ServiceError, ServiceTimeoutError
from sessions.pipeline.integration.auth_service_client import AuthServiceClient
from sessions.pipeline.integration.blockchain_engine_client import BlockchainEngineClient
from sessions.pipeline.integration.node_manager_client import NodeManagerClient
from sessions.pipeline.integration.api_gateway_client import APIGatewayClient
from sessions.storage.session_storage import SessionStorage, StorageConfig, StorageMetrics
from sessions.storage.chunk_store import ChunkStore, ChunkStoreConfig
from sessions.storage.config import StorageSettings, StorageConfig as StorageConfigManager
from sessions.api.config import SessionAPISettings
from sessions.api.integration.rdp_controller_client import RDPControllerClient
from  sessions.encryption.encryptor import SessionEncryptor, EncryptedChunk
from sessions.processor.chunk_processor import ChunkProcessor , ChunkProcessorService, ChunkMetadata

__all__ = [
    'SessionAPI',
    'PipelineManager', 'PipelineState','SessionPipeline','SessionAPISettings', 'IntegrationManager', 'IntegrationState', 'IntegrationStage',
    'PipelineStage', 'PipelineConfig','PipelineMetrics', 'RDPControllerClient', 'ServiceClientBase', 'ServiceError', 'ServiceTimeoutError', 'AuthServiceClient', 'BlockchainEngineClient', 'NodeManagerClient', 'APIGatewayClient', 'SessionPipelineClient', 'SessionStorageClient',
    'PipelineSettings', 'StateTransition', 'StateTransitionRule', 'EncryptedChunk',
    'PipelineManager',   'router', 'SessionEncryptor', 'ChunkProcessor', 'ChunkProcessorService', 'ChunkMetadata', 'ProcessingResult',
    'ChunkProcessorService', 'ChunkMetadata', 'ProcessingResult', 'SessionStorage', 'StorageConfig', 'StorageMetrics', 'ChunkStore', 'ChunkStoreConfig', 'StorageSettings', 'StorageConfigManager',
    'SessionStatus', 'RDPConfig', 'RecordingConfig', 'StorageConfig', 'SessionMetadata',
    'CreateSessionRequest', 'UpdateSessionRequest', 'SessionResponse', 'SessionListResponse', 
    'ChunkResponse', 'ChunkListResponse', 'PipelineResponse', 'StatisticsResponse'
]

__version__ = "1.0.0"
__cluster__ = "session-management"
__port__ = 8080
