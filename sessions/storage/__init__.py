"""
Lucid Session Storage Service
Cluster: Session Storage
Port: 8082

Features:
- Session data storage and retrieval
- Chunk-based data management
- Data compression and encryption
- Storage metrics and monitoring
- MongoDB integration for data persistence
- Redis caching for performance
- FastAPI-based storage API
"""

from sessions.storage.session_storage import StorageConfig, StorageMetrics, SessionStorage
from sessions.storage.chunk_store import ChunkStore, ChunkStoreConfig
from sessions.storage.config import (
    StorageSettings, 
    StorageConfig,
    create_default_config_file,
    load_config,
    get_config,
    set_config
)
from sessions.storage.session_storage_service import (
    StorageConfig,
    StorageDocument,
    ChunkDocument,
    SessionStorageService
)

__all__ = [
    'SessionStorage',
    'StorageConfig', 
    'StorageMetrics',
    'ChunkStore',
    'ChunkStoreConfig',
    'StorageSettings',
    'create_default_config_file',
    'load_config',
    'get_config',
    'set_config',
    'StorageDocument',
    'ChunkDocument',
    'SessionStorageService'
]

__version__ = "1.0.0"
__cluster__ = "session-storage"
__port__ = 8082
