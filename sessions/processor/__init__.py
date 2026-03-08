"""
LUCID Session Processor Components
Chunk processing, encryption, and Merkle tree building for session data
"""

from sessions.processor.compressor import SessionCompressor, CompressionAlgorithm, CompressionResult
from sessions.processor.session_manifest import SessionManifestGenerator, SessionManifest, ManifestType
from sessions.processor.chunk_processor import ChunkProcessor, ChunkProcessorService, ChunkMetadata, ProcessingResult
from sessions.processor.encryption import ChunkEncryptor, EncryptionManager, EncryptionError, KeyDerivationError, EncryptionValidationError
from sessions.processor.merkle_builder import MerkleTreeBuilder, MerkleTreeManager, MerkleNode, MerkleProof, MerkleTreeMetadata
from sessions.processor.config import ChunkProcessorConfig, EncryptionConfig, WorkerConfig, StorageConfig, PerformanceConfig, SecurityConfig, MonitoringConfig

__all__ = [
    # Legacy components
    'SessionCompressor', 'CompressionAlgorithm', 'CompressionResult',
    'SessionManifestGenerator', 'SessionManifest', 'ManifestType',
    
    # New chunk processing components
    'ChunkProcessor', 'ChunkProcessorService', 'ChunkMetadata', 'ProcessingResult',
    
    # Encryption components
    'ChunkEncryptor', 'EncryptionManager', 'EncryptionError', 'KeyDerivationError', 'EncryptionValidationError',
    
    # Merkle tree components
    'MerkleTreeBuilder', 'MerkleTreeManager', 'MerkleNode', 'MerkleProof', 'MerkleTreeMetadata',
    
    # Configuration components
    'ChunkProcessorConfig', 'EncryptionConfig', 'WorkerConfig', 'StorageConfig', 'PerformanceConfig', 'SecurityConfig', 'MonitoringConfig'
]
