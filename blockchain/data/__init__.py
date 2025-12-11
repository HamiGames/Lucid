"""
Data Chain Service Package
Handles data chunk management, Merkle tree construction, and integrity verification

This package provides the data chain service for the Lucid blockchain system,
managing data chunks, Merkle trees, and data integrity verification.
"""

from .service import DataChainService
from .chunk_manager import ChunkManager
from .storage import DataStorage
from .integrity import IntegrityVerifier
from .deduplication import DeduplicationManager

__all__ = [
    "DataChainService",
    "ChunkManager",
    "DataStorage",
    "IntegrityVerifier",
    "DeduplicationManager",
]

