"""
Lucid Session Storage Service
Cluster: Session Storage
Port: 8081

Features:
- Session data storage and retrieval
- Chunk-based data management
- Data compression and encryption
- Storage metrics and monitoring
- MongoDB integration for data persistence
- Redis caching for performance
- FastAPI-based storage API
"""

from .session_storage import SessionStorage, StorageConfig, StorageMetrics
from .chunk_store import ChunkStore, ChunkStoreConfig

__all__ = [
    'SessionStorage',
    'StorageConfig', 
    'StorageMetrics',
    'ChunkStore',
    'ChunkStoreConfig'
]

__version__ = "1.0.0"
__cluster__ = "session-storage"
__port__ = 8081
