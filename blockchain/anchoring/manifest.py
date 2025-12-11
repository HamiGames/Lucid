"""
Manifest Builder Module
Handles construction and validation of session manifests

This module provides utilities for building and validating session manifests
for blockchain anchoring.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from ..core.models import SessionManifest, ChunkMetadata

logger = logging.getLogger(__name__)


class ManifestBuilder:
    """
    Builder for session manifests.
    
    Handles construction and validation of session manifests for anchoring.
    """
    
    def __init__(self):
        """Initialize manifest builder."""
        logger.info("ManifestBuilder initialized")
    
    def build_manifest(
        self,
        session_id: str,
        owner_address: str,
        chunks: List[ChunkMetadata],
        started_at: Optional[datetime] = None,
        ended_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionManifest:
        """
        Build session manifest from components.
        
        Args:
            session_id: Unique session identifier
            owner_address: Ethereum address of session owner
            chunks: List of chunk metadata
            started_at: Optional session start time
            ended_at: Optional session end time
            metadata: Optional session metadata
            
        Returns:
            SessionManifest instance
        """
        if started_at is None:
            started_at = datetime.now(timezone.utc)
        
        manifest = SessionManifest(
            session_id=session_id,
            owner_address=owner_address,
            started_at=started_at,
            ended_at=ended_at,
            chunks=chunks,
            manifest_hash="",  # Will be calculated in __post_init__
            merkle_root="",    # Will be calculated in __post_init__
            chunk_count=len(chunks)
        )
        
        logger.debug(f"Built manifest for session: {session_id}")
        return manifest
    
    def calculate_manifest_hash(
        self,
        session_id: str,
        owner_address: str,
        started_at: datetime,
        chunk_count: int
    ) -> str:
        """
        Calculate manifest hash.
        
        Args:
            session_id: Session identifier
            owner_address: Owner address
            started_at: Session start time
            chunk_count: Number of chunks
            
        Returns:
            Manifest hash as hex string
        """
        manifest_data = {
            "session_id": session_id,
            "owner_address": owner_address,
            "started_at": started_at.isoformat(),
            "chunk_count": chunk_count
        }
        
        manifest_str = str(sorted(manifest_data.items()))
        hash_obj = hashlib.sha256(manifest_str.encode())
        return "0x" + hash_obj.hexdigest()
    
    def validate_manifest(self, manifest: SessionManifest) -> Tuple[bool, Optional[str]]:
        """
        Validate session manifest.
        
        Args:
            manifest: SessionManifest instance to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Validate session ID
            if not manifest.session_id or len(manifest.session_id) == 0:
                return False, "Session ID is required"
            
            # Validate owner address
            if not manifest.owner_address or len(manifest.owner_address) == 0:
                return False, "Owner address is required"
            
            # Validate merkle root
            if not manifest.merkle_root or len(manifest.merkle_root) == 0:
                return False, "Merkle root is required"
            
            # Validate chunk count matches chunks list
            if manifest.chunk_count != len(manifest.chunks):
                return False, f"Chunk count mismatch: {manifest.chunk_count} != {len(manifest.chunks)}"
            
            # Validate chunks
            for i, chunk in enumerate(manifest.chunks):
                if not chunk.ciphertext_sha256:
                    return False, f"Chunk {i} missing ciphertext hash"
                if chunk.size_bytes <= 0:
                    return False, f"Chunk {i} has invalid size"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Failed to validate manifest: {e}")
            return False, str(e)
    
    def manifest_to_dict(self, manifest: SessionManifest) -> Dict[str, Any]:
        """
        Convert manifest to dictionary.
        
        Args:
            manifest: SessionManifest instance
            
        Returns:
            Dictionary representation
        """
        return manifest.to_dict()

