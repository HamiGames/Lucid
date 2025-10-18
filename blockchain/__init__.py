"""
LUCID Blockchain Components - Blockchain Architecture (lucid_blocks)
REBUILT: On-System Data Chain (primary) + Isolated payment service

Based on Spec-1a, Spec-1b, and Spec-1c requirements.
- On-System Data Chain: Primary blockchain for session anchoring and consensus
- Payment services: Isolated in payment-systems/ directory
- PoOT Consensus: Runs on On-System Chain
"""

# Core blockchain components (using factory functions to avoid dependency issues)
from .core import (
    get_blockchain_engine,
    get_poot_consensus_engine
)

# Create aliases for backward compatibility (lazy loading)
def get_BlockchainEngine():
    return get_blockchain_engine()

def get_PoOTConsensusEngine():
    return get_poot_consensus_engine()

# Payment service integration is handled by isolated payment-systems service

# Data models
from .core.models import (
    # Enums
    ChainType, ConsensusState, TaskProofType,
    SessionStatus, PayoutStatus,
    
    # Session and Chunk Models
    ChunkMetadata, SessionManifest, SessionAnchor,
    
    # On-System Chain Models
    AnchorTransaction, ChunkStoreEntry,
    
    # PoOT Consensus Models
    TaskProof, WorkCredit, WorkCreditsTally, LeaderSchedule,
    
    # Network Models
    TransactionStatus,
    
    # Utility Functions
    generate_session_id, validate_ethereum_address,
    calculate_work_credits_formula
)

# On-System Chain client (primary blockchain)
try:
    from .on_system_chain.chain_client import OnSystemChainClient
except ImportError:
    OnSystemChainClient = None

# Chain client components
try:
    import importlib
    chain_client_module = importlib.import_module('blockchain.chain-client')
    ManifestManager = chain_client_module.ManifestManager
    ManifestStatus = chain_client_module.ManifestStatus
    ChunkStatus = chain_client_module.ChunkStatus
    ChunkInfo = chain_client_module.ChunkInfo
    get_manifest_manager = chain_client_module.get_manifest_manager
    create_manifest_manager = chain_client_module.create_manifest_manager
    cleanup_manifest_manager = chain_client_module.cleanup_manifest_manager
except ImportError:
    ManifestManager = None
    ManifestStatus = None
    ChunkStatus = None
    ChunkInfo = None
    get_manifest_manager = None
    create_manifest_manager = None
    cleanup_manifest_manager = None

# Payment service integration is handled by isolated payment-systems service

__all__ = [
    # Core blockchain engine and consensus (On-System Chain primary)
    'get_BlockchainEngine',
    'get_PoOTConsensusEngine',
    
    # Data models
    'ChainType', 'ConsensusState', 'TaskProofType',
    'SessionStatus', 'PayoutStatus',
    'ChunkMetadata', 'SessionManifest', 'SessionAnchor',
    'AnchorTransaction', 'ChunkStoreEntry',
    'TaskProof', 'WorkCredit', 'WorkCreditsTally', 'LeaderSchedule',
    'TransactionStatus',
    'generate_session_id', 'validate_ethereum_address',
    'calculate_work_credits_formula',
    
    # On-System Chain (primary blockchain)
    'OnSystemChainClient',
    
    # Chain client
    'ManifestManager', 'ManifestStatus', 'ChunkStatus', 'ChunkInfo',
    'get_manifest_manager', 'create_manifest_manager', 'cleanup_manifest_manager',
    
    # Payment service integration handled by isolated payment-systems service
]