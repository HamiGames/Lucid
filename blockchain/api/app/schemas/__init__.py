"""
Schema Models Package

This package contains all Pydantic models for the Blockchain API.
Implements the OpenAPI 3.0 specification for all API endpoints.

Modules:
- blockchain: Blockchain information and status models
- block: Block management and validation models
- transaction: Transaction processing models
- anchoring: Session anchoring models
- consensus: Consensus mechanism models
- merkle: Merkle tree operation models
"""

from .blockchain import BlockchainInfo, BlockchainStatus, BlockHeight, NetworkInfo
from .block import (
    BlockDetails, BlockSummary, BlockListResponse, BlockValidationRequest,
    BlockValidationResponse, TransactionSummary, PaginationInfo, BlockValidationResults
)
from .transaction import (
    TransactionSubmitRequest, TransactionResponse, TransactionDetails,
    TransactionListResponse, TransactionBatchRequest, TransactionBatchResponse,
    TransactionSummary as TransactionSummaryModel
)
from .anchoring import (
    SessionAnchoringRequest, SessionAnchoringResponse, SessionAnchoringStatus,
    AnchoringVerificationRequest, AnchoringVerificationResponse, AnchoringServiceStatus
)
from .consensus import (
    ConsensusStatus, ConsensusParticipants, ConsensusVoteRequest,
    ConsensusVoteResponse, ConsensusHistory, ConsensusEvent, NodeInfo
)
from .merkle import (
    MerkleTreeBuildRequest, MerkleTreeResponse, MerkleTreeDetails,
    MerkleProofVerificationRequest, MerkleProofVerificationResponse,
    MerkleValidationStatus, MerkleNode
)

__all__ = [
    # Blockchain models
    "BlockchainInfo", "BlockchainStatus", "BlockHeight", "NetworkInfo",
    
    # Block models
    "BlockDetails", "BlockSummary", "BlockListResponse", "BlockValidationRequest",
    "BlockValidationResponse", "TransactionSummary", "PaginationInfo", "BlockValidationResults",
    
    # Transaction models
    "TransactionSubmitRequest", "TransactionResponse", "TransactionDetails",
    "TransactionListResponse", "TransactionBatchRequest", "TransactionBatchResponse",
    "TransactionSummaryModel",
    
    # Anchoring models
    "SessionAnchoringRequest", "SessionAnchoringResponse", "SessionAnchoringStatus",
    "AnchoringVerificationRequest", "AnchoringVerificationResponse", "AnchoringServiceStatus",
    
    # Consensus models
    "ConsensusStatus", "ConsensusParticipants", "ConsensusVoteRequest",
    "ConsensusVoteResponse", "ConsensusHistory", "ConsensusEvent", "NodeInfo",
    
    # Merkle models
    "MerkleTreeBuildRequest", "MerkleTreeResponse", "MerkleTreeDetails",
    "MerkleProofVerificationRequest", "MerkleProofVerificationResponse",
    "MerkleValidationStatus", "MerkleNode"
]