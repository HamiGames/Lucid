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
path: ..storage
file: sessions/storage/__init__.py
the storage calls the sessions storage
"""

from sessions.core.logging import get_logger, setup_logging

__all__ = [
    'setup_logging',
    'get_logger'
]