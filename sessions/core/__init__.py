"""
LUCID Session Core Components
Chunking, Merkle tree building, and orchestration
"""

from sessions.core.chunker import SessionChunker, ChunkMetadata
from sessions.core.merkle_builder import MerkleTreeBuilder, MerkleRoot, MerkleProof

# Conditionally import session_orchestrator (requires encryption module)
try:
    from sessions.core.session_orchestrator import SessionOrchestrator, SessionPipeline, PipelineStage
    __all__ = [
        'SessionChunker', 'ChunkMetadata',
        'MerkleTreeBuilder', 'MerkleRoot', 'MerkleProof', 
        'SessionOrchestrator', 'SessionPipeline', 'PipelineStage'
    ]
except ImportError:
    # If encryption module is not available, skip orchestrator imports
    __all__ = [
        'SessionChunker', 'ChunkMetadata',
        'MerkleTreeBuilder', 'MerkleRoot', 'MerkleProof'
    ]