#!/usr/bin/env python3
"""
Merkle Tree Builder Module for Lucid RDP Recorder
Builds Merkle trees for session data integrity verification
"""

import asyncio
import logging
import hashlib
from typing import Optional, Dict, Any, List
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)

try:
    import blake3
    BLAKE3_AVAILABLE = True
except ImportError:
    logger.warning("BLAKE3 not available, using SHA-256 fallback")
    BLAKE3_AVAILABLE = False


class MerkleBuilder:
    """Builds Merkle trees for data integrity verification"""
    
    def __init__(self, hash_algorithm: str = "BLAKE3"):
        self.hash_algorithm = hash_algorithm.upper()
        self.chunks: List[bytes] = []
        self.merkle_tree: List[List[str]] = []
        self.root_hash: Optional[str] = None
        self.is_finalized = False
        
        # Statistics
        self.stats = {
            'chunks_added': 0,
            'total_size': 0,
            'tree_levels': 0,
            'final_hash': None
        }
    
    async def add_chunk(self, chunk_data: bytes):
        """Add a chunk to the Merkle tree"""
        try:
            if self.is_finalized:
                logger.warning("Cannot add chunks to finalized Merkle tree")
                return
            
            # Hash the chunk data
            chunk_hash = await self._hash_data(chunk_data)
            
            # Store chunk data and hash
            self.chunks.append(chunk_data)
            self.stats['chunks_added'] += 1
            self.stats['total_size'] += len(chunk_data)
            
            logger.debug("Added chunk to Merkle tree", 
                        chunk_index=self.stats['chunks_added'] - 1,
                        chunk_size=len(chunk_data),
                        chunk_hash=chunk_hash[:16] + "...")
            
        except Exception as e:
            logger.error("Failed to add chunk to Merkle tree", error=str(e))
    
    async def _hash_data(self, data: bytes) -> str:
        """Hash data using the specified algorithm"""
        try:
            if self.hash_algorithm == "BLAKE3" and BLAKE3_AVAILABLE:
                # Use BLAKE3 for fast hashing
                hasher = blake3.blake3()
                hasher.update(data)
                return hasher.hexdigest()
            else:
                # Fallback to SHA-256
                hasher = hashlib.sha256()
                hasher.update(data)
                return hasher.hexdigest()
                
        except Exception as e:
            logger.error("Failed to hash data", error=str(e))
            # Fallback to SHA-1 if everything else fails
            hasher = hashlib.sha1()
            hasher.update(data)
            return hasher.hexdigest()
    
    async def build_tree(self):
        """Build the Merkle tree from chunks"""
        try:
            if not self.chunks:
                logger.warning("No chunks to build Merkle tree")
                return
            
            logger.info("Building Merkle tree", 
                       chunk_count=len(self.chunks),
                       algorithm=self.hash_algorithm)
            
            # Start with leaf hashes
            current_level = []
            for i, chunk_data in enumerate(self.chunks):
                chunk_hash = await self._hash_data(chunk_data)
                current_level.append(chunk_hash)
                logger.debug("Created leaf hash", 
                           chunk_index=i,
                           hash=chunk_hash[:16] + "...")
            
            # Build tree levels
            self.merkle_tree = [current_level]
            level = 0
            
            while len(current_level) > 1:
                next_level = []
                
                # Process pairs of hashes
                for i in range(0, len(current_level), 2):
                    if i + 1 < len(current_level):
                        # Combine two hashes
                        combined = current_level[i] + current_level[i + 1]
                        parent_hash = await self._hash_data(combined.encode())
                        next_level.append(parent_hash)
                        
                        logger.debug("Created parent hash", 
                                   level=level,
                                   index=i // 2,
                                   hash=parent_hash[:16] + "...")
                    else:
                        # Odd number of hashes, promote the last one
                        next_level.append(current_level[i])
                        
                        logger.debug("Promoted hash", 
                                   level=level,
                                   index=i // 2,
                                   hash=current_level[i][:16] + "...")
                
                current_level = next_level
                self.merkle_tree.append(current_level)
                level += 1
            
            # Root hash is the single hash at the top level
            if current_level:
                self.root_hash = current_level[0]
                self.stats['tree_levels'] = len(self.merkle_tree)
                self.stats['final_hash'] = self.root_hash
                
                logger.info("Merkle tree built successfully", 
                           root_hash=self.root_hash[:16] + "...",
                           levels=self.stats['tree_levels'])
            
        except Exception as e:
            logger.error("Failed to build Merkle tree", error=str(e))
    
    async def finalize(self) -> Optional[str]:
        """Finalize the Merkle tree and return root hash"""
        try:
            if self.is_finalized:
                return self.root_hash
            
            # Build the tree
            await self.build_tree()
            
            self.is_finalized = True
            
            logger.info("Merkle tree finalized", 
                       root_hash=self.root_hash[:16] + "..." if self.root_hash else "None",
                       chunks=self.stats['chunks_added'],
                       total_size=self.stats['total_size'])
            
            return self.root_hash
            
        except Exception as e:
            logger.error("Failed to finalize Merkle tree", error=str(e))
            return None
    
    async def verify_chunk(self, chunk_data: bytes, chunk_index: int, proof: List[str]) -> bool:
        """Verify a chunk against the Merkle tree using a proof"""
        try:
            if not self.is_finalized or not self.root_hash:
                logger.error("Merkle tree not finalized")
                return False
            
            # Hash the chunk data
            chunk_hash = await self._hash_data(chunk_data)
            
            # Verify the proof
            current_hash = chunk_hash
            proof_index = chunk_index
            
            for proof_hash in proof:
                if proof_index % 2 == 0:
                    # Current hash is left child
                    combined = current_hash + proof_hash
                else:
                    # Current hash is right child
                    combined = proof_hash + current_hash
                
                current_hash = await self._hash_data(combined.encode())
                proof_index //= 2
            
            # Check if we reached the root hash
            is_valid = current_hash == self.root_hash
            
            logger.debug("Chunk verification", 
                        chunk_index=chunk_index,
                        is_valid=is_valid,
                        chunk_hash=chunk_hash[:16] + "...")
            
            return is_valid
            
        except Exception as e:
            logger.error("Failed to verify chunk", chunk_index=chunk_index, error=str(e))
            return False
    
    async def generate_proof(self, chunk_index: int) -> Optional[List[str]]:
        """Generate a Merkle proof for a chunk"""
        try:
            if not self.is_finalized or chunk_index >= len(self.chunks):
                logger.error("Invalid chunk index for proof generation")
                return None
            
            proof = []
            current_index = chunk_index
            
            # Walk up the tree to build the proof
            for level in range(len(self.merkle_tree) - 1):
                sibling_index = current_index ^ 1  # XOR to get sibling index
                
                if sibling_index < len(self.merkle_tree[level]):
                    proof.append(self.merkle_tree[level][sibling_index])
                else:
                    # No sibling, this is an odd node at the end
                    pass
                
                current_index //= 2
            
            logger.debug("Generated Merkle proof", 
                        chunk_index=chunk_index,
                        proof_length=len(proof))
            
            return proof
            
        except Exception as e:
            logger.error("Failed to generate Merkle proof", chunk_index=chunk_index, error=str(e))
            return None
    
    def get_tree_info(self) -> Dict[str, Any]:
        """Get information about the Merkle tree"""
        return {
            'algorithm': self.hash_algorithm,
            'chunks_count': len(self.chunks),
            'total_size': self.stats['total_size'],
            'tree_levels': self.stats['tree_levels'],
            'root_hash': self.root_hash,
            'is_finalized': self.is_finalized,
            'blake3_available': BLAKE3_AVAILABLE
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Merkle tree statistics"""
        return {
            **self.stats,
            'algorithm': self.hash_algorithm,
            'chunks_count': len(self.chunks),
            'tree_levels': len(self.merkle_tree),
            'is_finalized': self.is_finalized
        }
    
    async def cleanup(self):
        """Cleanup Merkle tree resources"""
        try:
            # Clear all data
            self.chunks.clear()
            self.merkle_tree.clear()
            self.root_hash = None
            self.is_finalized = False
            
            # Reset statistics
            self.stats = {
                'chunks_added': 0,
                'total_size': 0,
                'tree_levels': 0,
                'final_hash': None
            }
            
            logger.info("Merkle tree cleanup completed")
            
        except Exception as e:
            logger.error("Merkle tree cleanup error", error=str(e))
