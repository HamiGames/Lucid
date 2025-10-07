"""
LUCID Session System
Complete session management, recording, processing, security, and integration
"""

# Core session components
from .core import (
    SessionChunker, ChunkMetadata,
    MerkleTreeBuilder, MerkleRoot, MerkleProof,
    SessionOrchestrator, SessionPipeline, PipelineStage
)

# Session recording components
from .recorder import (
    SessionRecorder, RecordingStatus,
    VideoCapture, CaptureStatus,
    AuditTrailLogger, AuditEventType,
    KeystrokeMonitor, KeystrokeEventType,
    ResourceMonitor, ResourceType,
    WindowFocusMonitor, WindowEventType
)

# Session processing components
from .processor import (
    SessionCompressor, CompressionAlgorithm,
    SessionManifestGenerator, SessionManifest, ManifestType
)

# Session security components
from .security import (
    TrustNothingPolicyEnforcer, PolicyType, PolicyAction,
    InputController, InputType, ValidationResult, InputAction
)

# Session integration components
from .integration import (
    BlockchainClient, BlockchainNetwork, TransactionStatus, AnchorType
)

__version__ = "1.0.0"
__author__ = "LUCID RDP Team"

__all__ = [
    # Core
    'SessionChunker', 'ChunkMetadata',
    'MerkleTreeBuilder', 'MerkleRoot', 'MerkleProof',
    'SessionOrchestrator', 'SessionPipeline', 'PipelineStage',
    
    # Recording
    'SessionRecorder', 'RecordingStatus',
    'VideoCapture', 'CaptureStatus',
    'AuditTrailLogger', 'AuditEventType',
    'KeystrokeMonitor', 'KeystrokeEventType',
    'ResourceMonitor', 'ResourceType',
    'WindowFocusMonitor', 'WindowEventType',
    
    # Processing
    'SessionCompressor', 'CompressionAlgorithm',
    'SessionManifestGenerator', 'SessionManifest', 'ManifestType',
    
    # Security
    'TrustNothingPolicyEnforcer', 'PolicyType', 'PolicyAction',
    'InputController', 'InputType', 'ValidationResult', 'InputAction',
    
    # Integration
    'BlockchainClient', 'BlockchainNetwork', 'TransactionStatus', 'AnchorType'
]