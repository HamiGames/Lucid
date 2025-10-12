# Manifests Router Module
# Session manifest and proof retrieval endpoints

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
import logging

from app.schemas.sessions import (
    ManifestResponse, ChunkMetadata, MerkleProof, AnchorReceipt
)
from app.schemas.errors import ErrorResponse
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter()

# Dependency injection for session service
async def get_session_service() -> SessionService:
    """Get session service instance"""
    return SessionService()


@router.get(
    "/{session_id}/manifest",
    response_model=ManifestResponse,
    summary="Get session manifest",
    description="Retrieve session manifest with chunk metadata and blockchain anchoring information"
)
async def get_session_manifest(
    session_id: str,
    service: SessionService = Depends(get_session_service)
) -> ManifestResponse:
    """
    Get session manifest with chunk metadata.
    
    Returns:
    - Session manifest hash (BLAKE3)
    - Merkle tree root
    - Chunk count and total size
    - Blockchain anchor transaction ID (if anchored)
    """
    try:
        logger.info(f"Retrieving manifest for session {session_id}")
        
        manifest = await service.get_session_manifest(session_id)
        
        if not manifest:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="manifest_not_found",
                    message=f"Manifest not found for session {session_id}"
                ).model_dump()
            )
        
        return manifest
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session manifest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="manifest_retrieval_failed",
                message="Failed to retrieve session manifest"
            ).model_dump()
        )


@router.get(
    "/{session_id}/merkle-proof",
    response_model=MerkleProof,
    summary="Get Merkle proof",
    description="Generate Merkle proof for chunk verification"
)
async def get_merkle_proof(
    session_id: str,
    chunk_id: str = Query(..., description="Chunk identifier for proof generation"),
    service: SessionService = Depends(get_session_service)
) -> MerkleProof:
    """
    Generate Merkle proof for chunk verification.
    
    Args:
        session_id: Session identifier
        chunk_id: Specific chunk identifier
        
    Returns:
        Merkle proof with verification path and validity
    """
    try:
        logger.info(f"Generating Merkle proof for session {session_id}, chunk {chunk_id}")
        
        proof = await service.get_merkle_proof(session_id, chunk_id)
        
        if not proof:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="proof_not_found",
                    message=f"Merkle proof not found for chunk {chunk_id}"
                ).model_dump()
            )
        
        return proof
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate Merkle proof: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="proof_generation_failed",
                message="Failed to generate Merkle proof"
            ).model_dump()
        )


@router.get(
    "/{session_id}/anchor-receipt",
    response_model=AnchorReceipt,
    summary="Get anchor receipt",
    description="Retrieve blockchain anchor transaction receipt"
)
async def get_anchor_receipt(
    session_id: str,
    service: SessionService = Depends(get_session_service)
) -> AnchorReceipt:
    """
    Get blockchain anchor transaction receipt.
    
    Returns:
    - Transaction ID
    - Block number (if confirmed)
    - Gas used
    - Transaction status
    - Confirmation timestamp
    """
    try:
        logger.info(f"Retrieving anchor receipt for session {session_id}")
        
        receipt = await service.get_anchor_receipt(session_id)
        
        if not receipt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="receipt_not_found",
                    message=f"Anchor receipt not found for session {session_id}"
                ).model_dump()
            )
        
        return receipt
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get anchor receipt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="receipt_retrieval_failed",
                message="Failed to retrieve anchor receipt"
            ).model_dump()
        )


@router.get(
    "/{session_id}/chunks",
    response_model=List[ChunkMetadata],
    summary="List session chunks",
    description="Get paginated list of session chunks with metadata"
)
async def list_session_chunks(
    session_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    service: SessionService = Depends(get_session_service)
) -> List[ChunkMetadata]:
    """
    List session chunks with pagination.
    
    Args:
        session_id: Session identifier
        page: Page number (1-based)
        page_size: Items per page
        
    Returns:
        List of chunk metadata with pagination
    """
    try:
        logger.info(f"Listing chunks for session {session_id}, page {page}")
        
        chunks = await service.list_session_chunks(
            session_id=session_id,
            page=page,
            page_size=page_size
        )
        
        return chunks
        
    except Exception as e:
        logger.error(f"Failed to list session chunks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="chunks_list_failed",
                message="Failed to retrieve session chunks"
            ).model_dump()
        )


@router.get(
    "/{session_id}/chunks/{chunk_id}",
    response_model=ChunkMetadata,
    summary="Get chunk metadata",
    description="Get detailed metadata for a specific chunk"
)
async def get_chunk_metadata(
    session_id: str,
    chunk_id: str,
    service: SessionService = Depends(get_session_service)
) -> ChunkMetadata:
    """
    Get detailed metadata for a specific chunk.
    
    Args:
        session_id: Session identifier
        chunk_id: Chunk identifier
        
    Returns:
        Detailed chunk metadata
    """
    try:
        logger.info(f"Retrieving metadata for chunk {chunk_id} in session {session_id}")
        
        chunk_metadata = await service.get_chunk_metadata(session_id, chunk_id)
        
        if not chunk_metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="chunk_not_found",
                    message=f"Chunk {chunk_id} not found in session {session_id}"
                ).model_dump()
            )
        
        return chunk_metadata
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chunk metadata: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="chunk_metadata_failed",
                message="Failed to retrieve chunk metadata"
            ).model_dump()
        )


@router.get(
    "/{session_id}/verification",
    response_model=dict,
    summary="Verify session integrity",
    description="Verify session integrity using Merkle proofs and blockchain anchoring"
)
async def verify_session_integrity(
    session_id: str,
    service: SessionService = Depends(get_session_service)
) -> dict:
    """
    Verify session integrity using Merkle proofs and blockchain anchoring.
    
    Returns:
        Verification results including:
        - Merkle tree integrity
        - Blockchain anchor confirmation
        - Chunk hash verification
        - Overall verification status
    """
    try:
        logger.info(f"Verifying session integrity for {session_id}")
        
        verification_result = await service.verify_session_integrity(session_id)
        
        if not verification_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ErrorResponse(
                    error_code="session_not_found",
                    message=f"Session {session_id} not found for verification"
                ).model_dump()
            )
        
        return verification_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to verify session integrity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="verification_failed",
                message="Failed to verify session integrity"
            ).model_dump()
        )
