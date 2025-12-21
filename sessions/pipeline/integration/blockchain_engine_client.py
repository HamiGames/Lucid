#!/usr/bin/env python3
"""
Blockchain Engine Integration Client
Handles interaction with blockchain-engine service for anchoring and verification
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime

from .service_base import ServiceClientBase, ServiceError
from core.logging import get_logger

logger = get_logger(__name__)


class BlockchainEngineClient(ServiceClientBase):
    """
    Client for interacting with blockchain-engine service
    Handles session anchoring, Merkle tree operations, and blockchain queries
    """
    
    def __init__(self, base_url: Optional[str] = None, **kwargs):
        """
        Initialize Blockchain Engine client
        
        Args:
            base_url: Base URL for blockchain-engine (from BLOCKCHAIN_ENGINE_URL env var if not provided)
            **kwargs: Additional arguments passed to ServiceClientBase
        """
        url = base_url or os.getenv('BLOCKCHAIN_ENGINE_URL', '')
        if not url:
            raise ValueError("BLOCKCHAIN_ENGINE_URL environment variable is required")
        
        super().__init__(base_url=url, **kwargs)
    
    async def anchor_session_merkle_root(
        self,
        session_id: str,
        merkle_root: str,
        chunk_count: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Anchor session Merkle root to blockchain
        
        Args:
            session_id: Session identifier
            merkle_root: Merkle root hash
            chunk_count: Number of chunks in the session
            metadata: Optional additional metadata
            
        Returns:
            Anchoring transaction details
        """
        try:
            payload = {
                "session_id": session_id,
                "merkle_root": merkle_root,
                "chunk_count": chunk_count,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            response = await self._make_request(
                method='POST',
                endpoint='/api/v1/anchoring/session',
                json_data=payload
            )
            
            logger.info(f"Anchored session {session_id} Merkle root {merkle_root} to blockchain")
            return response
            
        except Exception as e:
            logger.error(f"Failed to anchor session {session_id}: {str(e)}")
            raise ServiceError(f"Blockchain anchoring failed: {str(e)}")
    
    async def get_session_anchoring_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get anchoring status for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Anchoring status information
        """
        try:
            response = await self._make_request(
                method='GET',
                endpoint=f'/api/v1/anchoring/session/{session_id}'
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get anchoring status for session {session_id}: {str(e)}")
            raise ServiceError(f"Failed to get anchoring status: {str(e)}")
    
    async def verify_session_anchoring(
        self,
        session_id: str,
        merkle_root: str,
        proof_path: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Verify session anchoring on blockchain
        
        Args:
            session_id: Session identifier
            merkle_root: Merkle root hash to verify
            proof_path: Optional Merkle proof path
            
        Returns:
            Verification result
        """
        try:
            payload = {
                "session_id": session_id,
                "merkle_root": merkle_root,
                "proof_path": proof_path or []
            }
            
            response = await self._make_request(
                method='POST',
                endpoint='/api/v1/anchoring/verify',
                json_data=payload
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to verify anchoring for session {session_id}: {str(e)}")
            raise ServiceError(f"Anchoring verification failed: {str(e)}")
    
    async def get_blockchain_status(self) -> Dict[str, Any]:
        """
        Get blockchain engine status
        
        Returns:
            Blockchain status information
        """
        try:
            response = await self._make_request(
                method='GET',
                endpoint='/api/v1/chain/status'
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get blockchain status: {str(e)}")
            raise ServiceError(f"Failed to get blockchain status: {str(e)}")
    
    async def get_blockchain_info(self) -> Dict[str, Any]:
        """
        Get blockchain network information
        
        Returns:
            Blockchain information
        """
        try:
            response = await self._make_request(
                method='GET',
                endpoint='/api/v1/chain/info'
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to get blockchain info: {str(e)}")
            raise ServiceError(f"Failed to get blockchain info: {str(e)}")
    
    async def build_merkle_tree(
        self,
        session_id: str,
        chunk_hashes: List[str]
    ) -> Dict[str, Any]:
        """
        Build Merkle tree for session chunks
        
        Args:
            session_id: Session identifier
            chunk_hashes: List of chunk hashes
            
        Returns:
            Merkle tree information including root hash
        """
        try:
            payload = {
                "session_id": session_id,
                "chunk_hashes": chunk_hashes
            }
            
            response = await self._make_request(
                method='POST',
                endpoint='/api/v1/merkle/build',
                json_data=payload
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to build Merkle tree for session {session_id}: {str(e)}")
            raise ServiceError(f"Merkle tree build failed: {str(e)}")
    
    async def verify_merkle_proof(
        self,
        root_hash: str,
        leaf_hash: str,
        proof_path: List[str]
    ) -> Dict[str, Any]:
        """
        Verify Merkle proof
        
        Args:
            root_hash: Merkle root hash
            leaf_hash: Leaf hash to verify
            proof_path: Merkle proof path
            
        Returns:
            Verification result
        """
        try:
            payload = {
                "root_hash": root_hash,
                "leaf_hash": leaf_hash,
                "proof_path": proof_path
            }
            
            response = await self._make_request(
                method='POST',
                endpoint='/api/v1/merkle/verify',
                json_data=payload
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to verify Merkle proof: {str(e)}")
            raise ServiceError(f"Merkle proof verification failed: {str(e)}")

