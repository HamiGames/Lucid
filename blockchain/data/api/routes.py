"""
Data Chain API Routes
REST API endpoints for data chain operations
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, status, Depends, Body, Query
from pydantic import BaseModel, Field

from ..service import DataChainService
from .main import get_data_chain_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models
class ChunkStoreRequest(BaseModel):
    """Request model for storing a chunk."""
    data: str = Field(..., description="Base64-encoded chunk data")
    session_id: Optional[str] = Field(None, description="Session identifier")
    index: int = Field(0, description="Chunk index in sequence")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional chunk metadata")


class ChunkResponse(BaseModel):
    """Response model for chunk operations."""
    chunk_id: str
    session_id: Optional[str] = None
    index: int
    size_bytes: int
    hash_value: str
    created_at: str
    metadata: Optional[Dict[str, Any]] = None


class MerkleTreeBuildRequest(BaseModel):
    """Request model for building Merkle tree."""
    chunk_ids: List[str] = Field(..., description="List of chunk identifiers")
    session_id: Optional[str] = Field(None, description="Session identifier")


class MerkleTreeResponse(BaseModel):
    """Response model for Merkle tree operations."""
    root_hash: str
    leaf_count: int
    tree_depth: int
    session_id: Optional[str] = None
    created_at: str


class MerkleProofVerificationRequest(BaseModel):
    """Request model for Merkle proof verification."""
    root_hash: str = Field(..., description="Expected root hash")
    leaf_hash: str = Field(..., description="Leaf hash to verify")
    proof_path: List[str] = Field(..., description="Merkle proof path")
    leaf_index: int = Field(..., description="Leaf index")


class VerificationResponse(BaseModel):
    """Response model for verification operations."""
    verified: bool
    timestamp: str
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Chunk endpoints
@router.post("/chunks", response_model=ChunkResponse, status_code=status.HTTP_201_CREATED)
async def store_chunk(
    request: ChunkStoreRequest,
    service: DataChainService = Depends(get_data_chain_service)
):
    """
    Store a data chunk.
    
    Stores chunk data and returns chunk metadata including hash and identifier.
    """
    try:
        import base64
        data = base64.b64decode(request.data)
        
        result = await service.store_chunk(
            data,
            request.session_id,
            request.index,
            request.metadata
        )
        
        return ChunkResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to store chunk: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store chunk: {str(e)}"
        )


@router.get("/chunks/{chunk_id}", response_model=Dict[str, Any])
async def get_chunk(
    chunk_id: str,
    service: DataChainService = Depends(get_data_chain_service)
):
    """
    Retrieve a data chunk.
    
    Returns chunk data and metadata. Data is base64-encoded in response.
    """
    try:
        result = await service.retrieve_chunk(chunk_id)
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chunk {chunk_id} not found"
            )
        
        # Encode data as base64
        import base64
        result["data"] = base64.b64encode(result["data"]).decode("utf-8")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve chunk {chunk_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chunk: {str(e)}"
        )


@router.get("/chunks", response_model=List[Dict[str, Any]])
async def list_chunks(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of chunks"),
    offset: int = Query(0, ge=0, description="Number of chunks to skip"),
    service: DataChainService = Depends(get_data_chain_service)
):
    """
    List chunks with optional filtering.
    
    Returns list of chunk metadata.
    """
    try:
        chunks = await service.chunk_manager.list_chunks(session_id, limit, offset)
        return chunks
        
    except Exception as e:
        logger.error(f"Failed to list chunks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list chunks: {str(e)}"
        )


@router.delete("/chunks/{chunk_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chunk(
    chunk_id: str,
    service: DataChainService = Depends(get_data_chain_service)
):
    """
    Delete a data chunk.
    """
    try:
        deleted = await service.chunk_manager.delete_chunk(chunk_id)
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chunk {chunk_id} not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete chunk {chunk_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chunk: {str(e)}"
        )


# Merkle tree endpoints
@router.post("/merkle/build", response_model=MerkleTreeResponse)
async def build_merkle_tree(
    request: MerkleTreeBuildRequest,
    service: DataChainService = Depends(get_data_chain_service)
):
    """
    Build Merkle tree from chunks.
    
    Constructs a Merkle tree from the provided chunk identifiers.
    """
    try:
        result = await service.build_merkle_tree(
            request.chunk_ids,
            request.session_id
        )
        
        return MerkleTreeResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to build Merkle tree: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build Merkle tree: {str(e)}"
        )


@router.post("/merkle/verify", response_model=VerificationResponse)
async def verify_merkle_proof(
    request: MerkleProofVerificationRequest,
    service: DataChainService = Depends(get_data_chain_service)
):
    """
    Verify Merkle proof.
    
    Verifies that a leaf hash is included in the Merkle tree with the given root hash.
    """
    try:
        from ....core.merkle_tree_builder import MerkleProof
        
        proof = MerkleProof(
            leaf_hash=request.leaf_hash,
            leaf_index=request.leaf_index,
            proof_path=request.proof_path
        )
        
        result = await service.verify_merkle_proof(
            request.root_hash,
            request.leaf_hash,
            proof,
            request.leaf_index
        )
        
        return VerificationResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to verify Merkle proof: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify Merkle proof: {str(e)}"
        )


# Integrity verification endpoints
@router.post("/verify/session/{session_id}", response_model=VerificationResponse)
async def verify_session(
    session_id: str,
    expected_merkle_root: Optional[str] = Query(None, description="Expected Merkle root hash"),
    service: DataChainService = Depends(get_data_chain_service)
):
    """
    Verify all chunks for a session.
    
    Verifies integrity of all chunks associated with a session.
    """
    try:
        result = await service.verify_session(session_id, expected_merkle_root)
        return VerificationResponse(**result)
        
    except Exception as e:
        logger.error(f"Failed to verify session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify session: {str(e)}"
        )


# Service status endpoint
@router.get("/status", response_model=Dict[str, Any])
async def get_service_status(
    service: DataChainService = Depends(get_data_chain_service)
):
    """
    Get data chain service status.
    
    Returns service health and statistics.
    """
    try:
        return await service.get_service_status()
        
    except Exception as e:
        logger.error(f"Failed to get service status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service status: {str(e)}"
        )

