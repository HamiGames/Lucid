"""
Error Handling Module

This module defines custom exceptions and error handling utilities
for the Blockchain API. Implements blockchain-specific error codes
as specified in the OpenAPI 3.0 specification.
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException, status
import logging

logger = logging.getLogger(__name__)

# Blockchain-specific error codes
class BlockchainErrorCode:
    """Blockchain-specific error codes."""
    
    # Block errors
    BLOCK_NOT_FOUND = "BLOCK_001"
    BLOCK_VALIDATION_FAILED = "BLOCK_002"
    BLOCK_HEIGHT_INVALID = "BLOCK_003"
    BLOCK_HASH_INVALID = "BLOCK_004"
    
    # Transaction errors
    TRANSACTION_NOT_FOUND = "TX_001"
    TRANSACTION_VALIDATION_FAILED = "TX_002"
    TRANSACTION_SIGNATURE_INVALID = "TX_003"
    TRANSACTION_FEE_INSUFFICIENT = "TX_004"
    TRANSACTION_DUPLICATE = "TX_005"
    
    # Anchoring errors
    SESSION_ANCHORING_FAILED = "ANCHOR_001"
    SESSION_NOT_FOUND = "ANCHOR_002"
    ANCHORING_VERIFICATION_FAILED = "ANCHOR_003"
    MERKLE_ROOT_INVALID = "ANCHOR_004"
    
    # Consensus errors
    CONSENSUS_VOTE_INVALID = "CONSENSUS_001"
    CONSENSUS_PARTICIPANT_NOT_FOUND = "CONSENSUS_002"
    CONSENSUS_ROUND_INVALID = "CONSENSUS_003"
    
    # Merkle tree errors
    MERKLE_TREE_BUILD_FAILED = "MERKLE_001"
    MERKLE_PROOF_INVALID = "MERKLE_002"
    MERKLE_TREE_NOT_FOUND = "MERKLE_003"
    
    # Network errors
    NETWORK_UNAVAILABLE = "NETWORK_001"
    PEER_CONNECTION_FAILED = "NETWORK_002"
    SYNC_FAILED = "NETWORK_003"

class BlockchainException(HTTPException):
    """Base exception for blockchain-specific errors."""
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str,
        additional_info: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.additional_info = additional_info or {}
        
        super().__init__(
            status_code=status_code,
            detail={
                "error": detail,
                "error_code": error_code,
                "additional_info": self.additional_info
            }
        )

class BlockNotFoundException(BlockchainException):
    """Exception raised when a block is not found."""
    
    def __init__(self, block_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Block not found: {block_id}",
            error_code=BlockchainErrorCode.BLOCK_NOT_FOUND,
            additional_info={"block_id": block_id}
        )

class BlockValidationException(BlockchainException):
    """Exception raised when block validation fails."""
    
    def __init__(self, validation_errors: list):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Block validation failed",
            error_code=BlockchainErrorCode.BLOCK_VALIDATION_FAILED,
            additional_info={"validation_errors": validation_errors}
        )

class TransactionNotFoundException(BlockchainException):
    """Exception raised when a transaction is not found."""
    
    def __init__(self, tx_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction not found: {tx_id}",
            error_code=BlockchainErrorCode.TRANSACTION_NOT_FOUND,
            additional_info={"tx_id": tx_id}
        )

class TransactionValidationException(BlockchainException):
    """Exception raised when transaction validation fails."""
    
    def __init__(self, validation_errors: list):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transaction validation failed",
            error_code=BlockchainErrorCode.TRANSACTION_VALIDATION_FAILED,
            additional_info={"validation_errors": validation_errors}
        )

class SessionAnchoringException(BlockchainException):
    """Exception raised when session anchoring fails."""
    
    def __init__(self, session_id: str, reason: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Session anchoring failed: {reason}",
            error_code=BlockchainErrorCode.SESSION_ANCHORING_FAILED,
            additional_info={"session_id": session_id, "reason": reason}
        )

class AnchoringVerificationException(BlockchainException):
    """Exception raised when anchoring verification fails."""
    
    def __init__(self, session_id: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anchoring verification failed",
            error_code=BlockchainErrorCode.ANCHORING_VERIFICATION_FAILED,
            additional_info={"session_id": session_id}
        )

class ConsensusVoteException(BlockchainException):
    """Exception raised when consensus vote is invalid."""
    
    def __init__(self, vote_id: str, reason: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Consensus vote invalid: {reason}",
            error_code=BlockchainErrorCode.CONSENSUS_VOTE_INVALID,
            additional_info={"vote_id": vote_id, "reason": reason}
        )

class MerkleTreeException(BlockchainException):
    """Exception raised when Merkle tree operation fails."""
    
    def __init__(self, operation: str, reason: str):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Merkle tree {operation} failed: {reason}",
            error_code=BlockchainErrorCode.MERKLE_TREE_BUILD_FAILED,
            additional_info={"operation": operation, "reason": reason}
        )

class NetworkException(BlockchainException):
    """Exception raised when network operation fails."""
    
    def __init__(self, operation: str, reason: str):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Network {operation} failed: {reason}",
            error_code=BlockchainErrorCode.NETWORK_UNAVAILABLE,
            additional_info={"operation": operation, "reason": reason}
        )

def handle_blockchain_error(error: Exception) -> HTTPException:
    """Handle blockchain-specific errors and convert to appropriate HTTP exceptions."""
    if isinstance(error, BlockchainException):
        return error
    elif isinstance(error, ValueError):
        return BlockchainException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input value",
            error_code="VALIDATION_001",
            additional_info={"original_error": str(error)}
        )
    elif isinstance(error, KeyError):
        return BlockchainException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required field",
            error_code="VALIDATION_002",
            additional_info={"missing_field": str(error)}
        )
    else:
        logger.error(f"Unhandled error: {error}", exc_info=True)
        return BlockchainException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
            error_code="INTERNAL_001",
            additional_info={"original_error": str(error)}
        )
