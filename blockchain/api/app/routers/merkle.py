"""
Merkle Router

This module contains the Merkle tree operation endpoints.
Implements the OpenAPI 3.0 specification for Merkle tree operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging

from ..schemas.merkle import (
    MerkleTreeBuildRequest, MerkleTreeResponse, MerkleTreeDetails,
    MerkleProofVerificationRequest, MerkleProofVerificationResponse, MerkleValidationStatus
)
from ..dependencies import get_current_user, verify_api_key, require_read_permission, require_write_permission
from ..services.merkle_service import MerkleService
from ..errors import MerkleTreeException

router = APIRouter(
    prefix="/merkle",
    tags=["Merkle"],
    responses={404: {"description": "Merkle tree not found"}},
)

logger = logging.getLogger(__name__)

@router.post("/build", response_model=MerkleTreeResponse)
async def build_merkle_tree(
    build_request: MerkleTreeBuildRequest,
    user = Depends(require_write_permission)
):
    """
    Builds a Merkle tree for session data validation.
    
    Creates a Merkle tree from provided data blocks for:
    - Data integrity verification
    - Efficient proof generation
    - Session data validation
    - Blockchain anchoring
    
    Build process:
    1. Validates input data blocks
    2. Constructs Merkle tree structure
    3. Calculates root hash
    4. Returns tree metadata
    
    Supported algorithms:
    - SHA256: Standard SHA-256 hashing
    - SHA3-256: SHA-3 256-bit hashing
    
    Returns tree information including:
    - Root hash
    - Leaf count and tree depth
    - Build time and creation timestamp
    """
    try:
        logger.info("Building Merkle tree")
        tree_response = await MerkleService.build_tree(build_request.dict())
        return MerkleTreeResponse(**tree_response)
    except Exception as e:
        logger.error(f"Failed to build Merkle tree: {e}")
        raise MerkleTreeException(
            operation="build",
            reason=str(e)
        )

@router.get("/{root_hash}", response_model=MerkleTreeDetails)
async def get_merkle_tree_details(
    root_hash: str,
    user = Depends(require_read_permission)
):
    """
    Returns detailed information about a Merkle tree.
    
    Provides comprehensive tree information including:
    - Tree structure and metadata
    - All nodes in the tree
    - Creation timestamp and algorithm
    - Associated session ID
    - Tree depth and leaf count
    
    Tree structure includes:
    - Root node information
    - Internal node details
    - Leaf node data
    - Node relationships
    
    Useful for tree analysis and verification.
    """
    try:
        logger.info(f"Fetching Merkle tree details for root hash: {root_hash}")
        tree_details = await MerkleService.get_tree_details(root_hash)
        if not tree_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Merkle tree not found"
            )
        return MerkleTreeDetails(**tree_details)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch Merkle tree details for root hash {root_hash}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve Merkle tree details"
        )

@router.post("/verify", response_model=MerkleProofVerificationResponse)
async def verify_merkle_tree_proof(
    verification_request: MerkleProofVerificationRequest,
    user = Depends(require_read_permission)
):
    """
    Verifies a Merkle tree proof for data integrity.
    
    Validates that a specific data block is included in the Merkle tree
    using a cryptographic proof without revealing the entire tree.
    
    Verification process:
    1. Validates proof path structure
    2. Reconstructs root hash from proof
    3. Compares with provided root hash
    4. Returns verification result
    
    Proof components:
    - Root hash of the tree
    - Leaf hash to verify
    - Proof path (sibling hashes)
    - Leaf index in the tree
    
    Returns verification results including:
    - Verification status (verified/not verified)
    - Verification time
    - Proof path used
    """
    try:
        logger.info("Verifying Merkle tree proof")
        verification_response = await MerkleService.verify_proof(verification_request.dict())
        return MerkleProofVerificationResponse(**verification_response)
    except Exception as e:
        logger.error(f"Failed to verify Merkle tree proof: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify Merkle tree proof"
        )

@router.get("/validation/{session_id}", response_model=MerkleValidationStatus)
async def get_merkle_tree_validation_status(
    session_id: str,
    user = Depends(require_read_permission)
):
    """
    Returns the validation status of a Merkle tree for a session.
    
    Provides validation status information including:
    - Current validation status
    - Validation timestamp
    - Detailed validation results
    - Associated root hash
    
    Validation statuses:
    - pending: Validation not yet started
    - validating: Validation in progress
    - valid: Validation completed successfully
    - invalid: Validation failed
    
    Validation results include:
    - Structure validation
    - Proof validation
    - Integrity validation
    - Error details if validation failed
    
    Useful for monitoring validation progress and results.
    """
    try:
        logger.info(f"Fetching Merkle tree validation status for session ID: {session_id}")
        validation_status = await MerkleService.get_validation_status(session_id)
        if not validation_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Validation status not found"
            )
        return MerkleValidationStatus(**validation_status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch Merkle tree validation status for session ID {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve validation status"
        )