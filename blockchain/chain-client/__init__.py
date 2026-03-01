"""
Blockchain Chain Client Module
Manages session manifests, merkle trees, and blockchain anchoring

REBUILT: Updated for dual-chain architecture with On-System Chain as primary.
"""

from .manifest_manager import (
    ManifestManager,
    ManifestStatus,
    ChunkStatus,
    ChunkInfo,
    get_manifest_manager,
    create_manifest_manager,
    cleanup_manifest_manager
)

from .on_system_chain_client import OnSystemChainClient

from .lucid_anchors_client import LucidAnchorsClient
from .lucid_chunk_store_client import LucidChunkStoreClient

__all__ = [
    "ManifestManager",
    "ManifestStatus", 
    "ChunkStatus",
    "ChunkInfo",
    "get_manifest_manager",
    "create_manifest_manager",
    "cleanup_manifest_manager",
    "OnSystemChainClient",
    "LucidAnchorsClient",
    "LucidChunkStoreClient"
]