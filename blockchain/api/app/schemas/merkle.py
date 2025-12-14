"""
Merkle Tree Schema Models

This module defines Pydantic models for Merkle tree API endpoints.
Implements the OpenAPI 3.0 specification for Merkle tree operations and validation.

Models:
- MerkleTreeBuildRequest: Merkle tree build request
- MerkleTreeResponse: Merkle tree build response
- MerkleTreeDetails: Detailed Merkle tree information
- MerkleProofVerificationRequest: Merkle proof verification request
- MerkleProofVerificationResponse: Merkle proof verification response
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class MerkleTreeBuildRequest(BaseModel):
    """Request for building a Merkle tree."""
    data_blocks: List[str] = Field(..., description="List of data blocks to include in the tree", min_items=1)
    algorithm: str = Field("SHA256", description="Hashing algorithm", enum=["SHA256", "SHA3-256"])
    session_id: Optional[str] = Field(None, description="Associated session ID")


class MerkleTreeResponse(BaseModel):
    """Response after building a Merkle tree."""
    root_hash: str = Field(..., description="Merkle tree root hash", pattern=r'^[a-fA-F0-9]{64}$')
    leaf_count: int = Field(..., description="Number of leaves in the tree")
    tree_depth: int = Field(..., description="Depth of the Merkle tree")
    build_time: float = Field(..., description="Time taken to build the tree in seconds")
    created_at: datetime = Field(..., description="Tree creation timestamp")


class MerkleNode(BaseModel):
    """A node in the Merkle tree."""
    hash: str = Field(..., description="Node hash")
    level: int = Field(..., description="Node level in the tree")
    index: int = Field(..., description="Node index at its level")
    is_leaf: bool = Field(..., description="Whether this is a leaf node")


class MerkleTreeDetails(BaseModel):
    """Detailed information about a Merkle tree."""
    root_hash: str = Field(..., description="Merkle tree root hash")
    leaf_count: int = Field(..., description="Number of leaves in the tree")
    tree_depth: int = Field(..., description="Depth of the Merkle tree")
    algorithm: str = Field(..., description="Hashing algorithm used")
    created_at: datetime = Field(..., description="Tree creation timestamp")
    nodes: List[MerkleNode] = Field(..., description="All nodes in the tree")
    session_id: Optional[str] = Field(None, description="Associated session ID")


class MerkleProofVerificationRequest(BaseModel):
    """Request for verifying a Merkle tree proof."""
    root_hash: str = Field(..., description="Merkle tree root hash", pattern=r'^[a-fA-F0-9]{64}$')
    leaf_hash: str = Field(..., description="Leaf hash to verify", pattern=r'^[a-fA-F0-9]{64}$')
    proof_path: List[str] = Field(..., description="Merkle proof path", min_items=1)
    leaf_index: int = Field(..., description="Index of the leaf in the tree", ge=0)


class MerkleProofVerificationResponse(BaseModel):
    """Response containing Merkle proof verification results."""
    verified: bool = Field(..., description="Whether the proof is valid")
    root_hash: str = Field(..., description="Merkle tree root hash")
    leaf_hash: str = Field(..., description="Leaf hash that was verified")
    proof_path: List[str] = Field(..., description="Merkle proof path used")
    verification_time: float = Field(..., description="Time taken to verify the proof in seconds")


class MerkleValidationStatus(BaseModel):
    """Validation status of a Merkle tree for a session."""
    session_id: str = Field(..., description="Session UUID")
    root_hash: str = Field(..., description="Merkle tree root hash")
    status: str = Field(..., description="Validation status", enum=["pending", "validating", "valid", "invalid"])
    validated_at: Optional[datetime] = Field(None, description="Validation timestamp")
    validation_results: Dict[str, Any] = Field(..., description="Detailed validation results")
