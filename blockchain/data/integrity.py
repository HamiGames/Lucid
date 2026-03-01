"""
Integrity Verifier
Handles data integrity verification for chunks and Merkle trees

This module provides integrity verification functionality including
hash verification, checksum validation, and corruption detection.
"""

from __future__ import annotations

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

import blake3
import hashlib

from motor.motor_asyncio import AsyncIOMotorDatabase
from ..config.config import get_blockchain_config
from ..core.merkle_tree_builder import MerkleTreeBuilder, MerkleProof

logger = logging.getLogger(__name__)

# Environment variable configuration (required, no hardcoded defaults)
MONGO_URL = os.getenv("MONGO_URL") or os.getenv("MONGODB_URL") or os.getenv("MONGODB_URI")
if not MONGO_URL:
    raise RuntimeError("MONGO_URL, MONGODB_URL, or MONGODB_URI environment variable not set")

# Integrity configuration from environment
HASH_VERIFICATION_ENABLED = os.getenv("DATA_CHAIN_HASH_VERIFICATION_ENABLED", "true").lower() in ("true", "1", "yes")
VERIFY_CHUNK_HASHES = os.getenv("DATA_CHAIN_VERIFY_CHUNK_HASHES", "true").lower() in ("true", "1", "yes")
VERIFY_MERKLE_ROOT = os.getenv("DATA_CHAIN_VERIFY_MERKLE_ROOT", "true").lower() in ("true", "1", "yes")
VERIFY_PROOF_PATHS = os.getenv("DATA_CHAIN_VERIFY_PROOF_PATHS", "true").lower() in ("true", "1", "yes")
VERIFICATION_ON_RETRIEVAL = os.getenv("DATA_CHAIN_VERIFICATION_ON_RETRIEVAL", "true").lower() in ("true", "1", "yes")
VERIFICATION_ON_STORAGE = os.getenv("DATA_CHAIN_VERIFICATION_ON_STORAGE", "true").lower() in ("true", "1", "yes")
HASH_ALGORITHM = os.getenv("DATA_CHAIN_HASH_ALGORITHM", os.getenv("ANCHORING_HASH_ALGORITHM", "BLAKE3")).upper()

# Periodic verification
PERIODIC_VERIFICATION_ENABLED = os.getenv("DATA_CHAIN_PERIODIC_VERIFICATION_ENABLED", "true").lower() in ("true", "1", "yes")
VERIFICATION_INTERVAL_HOURS = int(os.getenv("DATA_CHAIN_VERIFICATION_INTERVAL_HOURS", os.getenv("VERIFICATION_INTERVAL_HOURS", "24")))
VERIFY_SAMPLE_PERCENTAGE = int(os.getenv("DATA_CHAIN_VERIFY_SAMPLE_PERCENTAGE", os.getenv("VERIFY_SAMPLE_PERCENTAGE", "10")))


class IntegrityVerifier:
    """
    Verifies data integrity for chunks and Merkle trees.
    
    Provides hash verification, checksum validation, and corruption detection.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        """
        Initialize integrity verifier.
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
        self.verification_results_collection = db.integrity_verification_results
        
        # Get configuration
        config = get_blockchain_config()
        data_chain_config = config.get_data_chain_config()
        integrity_config = data_chain_config.get("integrity", {})
        hash_config = integrity_config.get("hash_verification", {})
        data_checks_config = integrity_config.get("data_checks", {})
        
        # Override with environment variables if provided
        self.enabled = HASH_VERIFICATION_ENABLED and hash_config.get("enabled", True)
        self.verify_chunk_hashes = VERIFY_CHUNK_HASHES and hash_config.get("verify_chunk_hashes", True)
        self.verify_merkle_root = VERIFY_MERKLE_ROOT and hash_config.get("verify_merkle_root", True)
        self.verify_proof_paths = VERIFY_PROOF_PATHS and hash_config.get("verify_proof_paths", True)
        self.verification_on_retrieval = VERIFICATION_ON_RETRIEVAL and hash_config.get("verification_on_retrieval", True)
        self.verification_on_storage = VERIFICATION_ON_STORAGE and hash_config.get("verification_on_storage", True)
        
        # Data checks
        self.checksum_verification = os.getenv("DATA_CHAIN_CHECKSUM_VERIFICATION", str(data_checks_config.get("checksum_verification", True))).lower() in ("true", "1", "yes")
        self.size_verification = os.getenv("DATA_CHAIN_SIZE_VERIFICATION", str(data_checks_config.get("size_verification", True))).lower() in ("true", "1", "yes")
        self.corruption_detection = os.getenv("DATA_CHAIN_CORRUPTION_DETECTION", str(data_checks_config.get("corruption_detection", True))).lower() in ("true", "1", "yes")
        
        # Initialize Merkle tree builder
        self.merkle_builder = MerkleTreeBuilder(db)
        
        logger.info(f"IntegrityVerifier initialized: enabled={self.enabled}")
    
    def _compute_hash(self, data: bytes) -> str:
        """Compute hash of data using configured algorithm."""
        if HASH_ALGORITHM == "BLAKE3":
            hasher = blake3.blake3()
            hasher.update(data)
            return hasher.hexdigest()
        elif HASH_ALGORITHM == "SHA256":
            return hashlib.sha256(data).hexdigest()
        else:
            # Default to BLAKE3
            hasher = blake3.blake3()
            hasher.update(data)
            return hasher.hexdigest()
    
    async def verify_chunk(
        self,
        chunk_id: str,
        data: bytes,
        expected_hash: Optional[str] = None,
        expected_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Verify chunk integrity.
        
        Args:
            chunk_id: Chunk identifier
            data: Chunk data bytes
            expected_hash: Expected hash value (optional, will be computed if not provided)
            expected_size: Expected size in bytes (optional)
            
        Returns:
            Dictionary with verification results
        """
        if not self.enabled:
            return {
                "verified": True,
                "reason": "Integrity verification disabled"
            }
        
        try:
            results = {
                "chunk_id": chunk_id,
                "verified": True,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "checks": {}
            }
            
            # Size verification
            if self.size_verification and expected_size is not None:
                size_valid = len(data) == expected_size
                results["checks"]["size"] = {
                    "valid": size_valid,
                    "expected": expected_size,
                    "actual": len(data)
                }
                if not size_valid:
                    results["verified"] = False
                    results["error"] = f"Size mismatch: expected {expected_size}, got {len(data)}"
            
            # Hash verification
            if self.verify_chunk_hashes:
                computed_hash = self._compute_hash(data)
                
                if expected_hash:
                    hash_valid = computed_hash == expected_hash
                    results["checks"]["hash"] = {
                        "valid": hash_valid,
                        "expected": expected_hash,
                        "computed": computed_hash
                    }
                    if not hash_valid:
                        results["verified"] = False
                        results["error"] = f"Hash mismatch: expected {expected_hash}, got {computed_hash}"
                else:
                    # Store computed hash for future verification
                    results["checks"]["hash"] = {
                        "valid": True,
                        "computed": computed_hash
                    }
            
            # Corruption detection
            if self.corruption_detection:
                # Basic corruption checks
                corruption_detected = False
                corruption_reasons = []
                
                # Check for null bytes in unexpected places (basic check)
                if len(data) > 0 and data.count(b'\x00') > len(data) * 0.9:
                    corruption_detected = True
                    corruption_reasons.append("Excessive null bytes")
                
                results["checks"]["corruption"] = {
                    "detected": corruption_detected,
                    "reasons": corruption_reasons
                }
                
                if corruption_detected:
                    results["verified"] = False
                    results["error"] = f"Corruption detected: {', '.join(corruption_reasons)}"
            
            # Store verification result
            await self.verification_results_collection.insert_one({
                "chunk_id": chunk_id,
                "verified": results["verified"],
                "timestamp": datetime.now(timezone.utc),
                "results": results
            })
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to verify chunk {chunk_id}: {e}")
            return {
                "chunk_id": chunk_id,
                "verified": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def verify_merkle_proof(
        self,
        root_hash: str,
        leaf_hash: str,
        proof: MerkleProof,
        leaf_index: int
    ) -> Dict[str, Any]:
        """
        Verify Merkle proof.
        
        Args:
            root_hash: Expected root hash
            leaf_hash: Leaf hash to verify
            proof: Merkle proof
            leaf_index: Leaf index
            
        Returns:
            Dictionary with verification results
        """
        if not self.verify_proof_paths:
            return {
                "verified": True,
                "reason": "Proof verification disabled"
            }
        
        try:
            # Use Merkle tree builder to verify proof
            verified = await self.merkle_builder.verify_proof(
                root_hash,
                leaf_hash,
                proof,
                leaf_index
            )
            
            result = {
                "verified": verified,
                "root_hash": root_hash,
                "leaf_hash": leaf_hash,
                "leaf_index": leaf_index,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            if not verified:
                result["error"] = "Merkle proof verification failed"
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to verify Merkle proof: {e}")
            return {
                "verified": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def verify_session_chunks(
        self,
        session_id: str,
        chunk_ids: List[str],
        expected_merkle_root: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Verify all chunks for a session.
        
        Args:
            session_id: Session identifier
            chunk_ids: List of chunk identifiers
            expected_merkle_root: Expected Merkle root hash (optional)
            
        Returns:
            Dictionary with verification results
        """
        try:
            results = {
                "session_id": session_id,
                "verified": True,
                "chunk_count": len(chunk_ids),
                "chunks_verified": 0,
                "chunks_failed": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "chunk_results": []
            }
            
            # Verify each chunk
            for chunk_id in chunk_ids:
                # Get chunk metadata
                from .storage import DataStorage
                storage = DataStorage(self.db)
                metadata = await storage.get_chunk_metadata(chunk_id)
                
                if not metadata:
                    results["chunks_failed"] += 1
                    results["chunk_results"].append({
                        "chunk_id": chunk_id,
                        "verified": False,
                        "error": "Chunk not found"
                    })
                    continue
                
                # Retrieve chunk data
                data = await storage.retrieve_chunk(chunk_id)
                if not data:
                    results["chunks_failed"] += 1
                    results["chunk_results"].append({
                        "chunk_id": chunk_id,
                        "verified": False,
                        "error": "Failed to retrieve chunk"
                    })
                    continue
                
                # Verify chunk
                chunk_result = await self.verify_chunk(
                    chunk_id,
                    data,
                    expected_hash=metadata.get("hash_value"),
                    expected_size=metadata.get("size_bytes")
                )
                
                if chunk_result.get("verified"):
                    results["chunks_verified"] += 1
                else:
                    results["chunks_failed"] += 1
                    results["verified"] = False
                
                results["chunk_results"].append(chunk_result)
            
            # Verify Merkle root if provided
            if expected_merkle_root and self.verify_merkle_root:
                # Build Merkle tree from chunks
                merkle_tree = await self.merkle_builder.build_tree_from_chunks(chunk_ids)
                root_valid = merkle_tree.root_hash == expected_merkle_root
                
                results["merkle_root"] = {
                    "verified": root_valid,
                    "expected": expected_merkle_root,
                    "computed": merkle_tree.root_hash
                }
                
                if not root_valid:
                    results["verified"] = False
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to verify session chunks for {session_id}: {e}")
            return {
                "session_id": session_id,
                "verified": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_verification_history(
        self,
        chunk_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get verification history.
        
        Args:
            chunk_id: Optional chunk identifier filter
            limit: Maximum number of results
            
        Returns:
            List of verification results
        """
        try:
            query = {}
            if chunk_id:
                query["chunk_id"] = chunk_id
            
            cursor = self.verification_results_collection.find(query).sort("timestamp", -1).limit(limit)
            results = await cursor.to_list(length=limit)
            
            # Convert to list of dictionaries
            for result in results:
                result.pop("_id", None)
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to get verification history: {e}")
            return []

