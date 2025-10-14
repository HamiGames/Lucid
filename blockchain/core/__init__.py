"""
LUCID Blockchain Core Components
Dual-chain architecture with On-System Data Chain and isolated TRON payments

Based on Spec-1a, Spec-1b, and Spec-1c requirements.
REBUILT: On-System Chain as primary, TRON isolated for payments only.
"""

# Data models (no dependencies)
from .models import (
    # Enums
    ChainType, ConsensusState, PayoutRouter, TaskProofType,
    SessionStatus, PayoutStatus,
    
    # Session and Chunk Models
    ChunkMetadata, SessionManifest, SessionAnchor,
    
    # On-System Chain Models
    AnchorTransaction, ChunkStoreEntry,
    
    # PoOT Consensus Models
    TaskProof, WorkCredit, WorkCreditsTally, LeaderSchedule,
    
    # Payout Models
    PayoutRequest, PayoutResult,
    
    # Network Models
    TransactionStatus,
    
    # Utility Functions
    generate_session_id, validate_ethereum_address,
    calculate_work_credits_formula
)

# Legacy components (for backward compatibility) - lazy loading to avoid dependencies
def get_Storage():
    """Get Storage class (imports on demand)"""
    from .storage import Storage
    return Storage

def get_Node():
    """Get Node class (imports on demand)"""
    from .node import Node
    return Node

# Core blockchain components (import on demand to avoid dependency issues)
def get_blockchain_engine():
    """Get BlockchainEngine (imports on demand)"""
    from .blockchain_engine import BlockchainEngine
    return BlockchainEngine

def get_poot_consensus_engine():
    """Get PoOTConsensusEngine (imports on demand)"""
    from .poot_consensus import PoOTConsensusEngine
    return PoOTConsensusEngine

def get_leader_selection_engine():
    """Get LeaderSelectionEngine (imports on demand)"""
    from .leader_selection import LeaderSelectionEngine
    return LeaderSelectionEngine

def get_work_credits_engine():
    """Get WorkCreditsEngine (imports on demand)"""
    from .work_credits import WorkCreditsEngine
    return WorkCreditsEngine

__all__ = [
    # Data models
    "ChainType", "ConsensusState", "PayoutRouter", "TaskProofType",
    "SessionStatus", "PayoutStatus",
    "ChunkMetadata", "SessionManifest", "SessionAnchor",
    "AnchorTransaction", "ChunkStoreEntry",
    "TaskProof", "WorkCredit", "WorkCreditsTally", "LeaderSchedule",
    "PayoutRequest", "PayoutResult", "TransactionStatus",
    "generate_session_id", "validate_ethereum_address",
    "calculate_work_credits_formula",
    
    # Factory functions for core blockchain components
    "get_blockchain_engine", "get_poot_consensus_engine", 
    "get_leader_selection_engine", "get_work_credits_engine",
    
    # Factory functions for legacy components
    "get_Storage", "get_Node"
]
