# Path: apps/merkle/merkle_builder.py
# Lucid RDP Merkle Tree Builder - BLAKE3 for session chunk anchoring
# Based on LUCID-STRICT requirements per Spec-1b

from __future__ import annotations

import logging
from typing import List, Optional, Tuple, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib

try:
    import blake3
    HAS_BLAKE3 = True
except ImportError:
    HAS_BLAKE3 = False
    logger.warning("blake3 module not available, falling back to hashlib")

from sessions.encryption.encryptor import EncryptedChunk

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MerkleNode:
    """Node in a Merkle tree"""
    hash: bytes
    level: int
    position: int
    left_child: Optional[MerkleNode] = None
    right_child: Optional[MerkleNode] = None
    
    def is_leaf(self) -> bool:
        """Check if this is a leaf node."""
        return self.left_child is None and self.right_child is None
    
    @property
    def hash_hex(self) -> str:
        """Get hex representation of hash."""
        return self.hash.hex()


@dataclass
class MerkleProof:
    """Merkle proof for chunk verification"""
    chunk_hash: str
    root_hash: str
    proof_hashes: List[str]
    positions: List[bool]  # True = right, False = left
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for storage/transmission."""
        return {
            "chunk_hash": self.chunk_hash,
            "root_hash": self.root_hash,
            "proof_hashes": self.proof_hashes,
            "positions": self.positions
        }


class LucidMerkleBuilder:
    """
    BLAKE3-based Merkle tree builder for session chunks.
    
    Per Spec-1b:
    - Uses BLAKE3 for all hashing operations
    - Builds Merkle root over encrypted chunk ciphertext hashes
    - Provides proofs for individual chunks
    - Root is anchored to On-System Data Chain via LucidAnchors contract
    """
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.chunk_hashes: List[str] = []
        self.merkle_root: Optional[str] = None
        self.merkle_tree: Optional[MerkleNode] = None
        
        logger.info(f"Merkle builder initialized for session {session_id}")
    
    def _hash_data(self, data: bytes) -> bytes:
        """
        Hash data using BLAKE3.
        
        Args:
            data: Data to hash
            
        Returns:
            32-byte BLAKE3 hash
        """
        if HAS_BLAKE3:
            return blake3.blake3(data).digest()
        else:
            # Fallback to hashlib implementation
            hasher = hashlib.new('blake2b', digest_size=32)
            hasher.update(data)
            return hasher.digest()
    
    def add_chunk_hash(self, chunk_hash: str) -> None:
        """
        Add encrypted chunk hash to the tree.
        
        Args:
            chunk_hash: SHA256 hash of encrypted chunk ciphertext
        """
        self.chunk_hashes.append(chunk_hash)
        # Clear cached tree/root since we have new data
        self.merkle_tree = None
        self.merkle_root = None
        
        logger.debug(f"Added chunk hash to session {self.session_id}: {chunk_hash[:16]}...")
    
    def build_tree(self) -> MerkleNode:
        """
        Build complete Merkle tree from chunk hashes.
        
        Returns:
            Root node of the Merkle tree
        """
        if not self.chunk_hashes:
            raise ValueError("No chunk hashes to build tree from")
        
        # Convert hex hashes to bytes for processing
        leaf_hashes = [bytes.fromhex(h) for h in self.chunk_hashes]
        
        # Build tree bottom-up
        current_level = []
        for i, leaf_hash in enumerate(leaf_hashes):
            node = MerkleNode(hash=leaf_hash, level=0, position=i)
            current_level.append(node)
        
        level = 0
        while len(current_level) > 1:
            next_level = []
            level += 1
            
            # Process pairs at current level
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                
                # Handle odd number of nodes by duplicating the last one
                if i + 1 < len(current_level):
                    right = current_level[i + 1]
                else:
                    right = left  # Duplicate for odd count
                
                # Create parent node
                combined_data = left.hash + right.hash
                parent_hash = self._hash_data(combined_data)
                
                parent = MerkleNode(
                    hash=parent_hash,
                    level=level,
                    position=i // 2,
                    left_child=left,
                    right_child=right
                )
                
                next_level.append(parent)
            
            current_level = next_level
        
        # Cache the tree and root
        self.merkle_tree = current_level[0]
        self.merkle_root = self.merkle_tree.hash_hex
        
        logger.info(f"Built Merkle tree for session {self.session_id}: "
                   f"root={self.merkle_root[:16]}..., chunks={len(self.chunk_hashes)}")
        
        return self.merkle_tree
    
    def get_root_hash(self) -> str:
        """
        Get Merkle root hash, building tree if necessary.
        
        Returns:
            Hex-encoded Merkle root hash
        """
        if self.merkle_root is None:
            self.build_tree()
        
        return self.merkle_root
    
    def generate_proof(self, chunk_index: int) -> MerkleProof:
        """
        Generate Merkle proof for a specific chunk.
        
        Args:
            chunk_index: Index of chunk to prove (0-based)
            
        Returns:
            Merkle proof for the chunk
        """
        if chunk_index >= len(self.chunk_hashes):
            raise IndexError(f"Chunk index {chunk_index} out of range")
        
        if self.merkle_tree is None:
            self.build_tree()
        
        chunk_hash = self.chunk_hashes[chunk_index]
        proof_hashes = []
        positions = []
        
        # Traverse tree from leaf to root, collecting sibling hashes
        current_index = chunk_index
        current_level_size = len(self.chunk_hashes)
        
        while current_level_size > 1:
            # Determine sibling position and hash
            if current_index % 2 == 0:
                # Current node is left child, sibling is right
                sibling_index = current_index + 1
                positions.append(True)  # Sibling is on the right
            else:
                # Current node is right child, sibling is left
                sibling_index = current_index - 1
                positions.append(False)  # Sibling is on the left
            
            # Add sibling hash to proof (if it exists)
            if sibling_index < current_level_size:
                if len(self.chunk_hashes) == current_level_size:
                    # At leaf level, use chunk hashes
                    sibling_hash = self.chunk_hashes[sibling_index]
                    proof_hashes.append(sibling_hash)
                else:
                    # At internal levels, need to compute hash
                    # This is a simplified approach - in production would traverse tree
                    pass
            else:
                # Odd number of nodes, sibling is the same as current
                if len(self.chunk_hashes) == current_level_size:
                    sibling_hash = self.chunk_hashes[current_index]
                    proof_hashes.append(sibling_hash)
            
            # Move up to next level
            current_index = current_index // 2
            current_level_size = (current_level_size + 1) // 2
        
        return MerkleProof(
            chunk_hash=chunk_hash,
            root_hash=self.get_root_hash(),
            proof_hashes=proof_hashes,
            positions=positions
        )
    
    def verify_proof(self, proof: MerkleProof) -> bool:
        """
        Verify a Merkle proof against the current root.
        
        Args:
            proof: Merkle proof to verify
            
        Returns:
            True if proof is valid
        """
        try:
            current_hash = bytes.fromhex(proof.chunk_hash)
            
            # Reconstruct path to root using proof
            for sibling_hex, is_right in zip(proof.proof_hashes, proof.positions):
                sibling_hash = bytes.fromhex(sibling_hex)
                
                if is_right:
                    # Sibling is on the right
                    combined = current_hash + sibling_hash
                else:
                    # Sibling is on the left
                    combined = sibling_hash + current_hash
                
                current_hash = self._hash_data(combined)
            
            # Compare with expected root
            calculated_root = current_hash.hex()
            return calculated_root == proof.root_hash
            
        except Exception as e:
            logger.error(f"Proof verification failed: {e}")
            return False
    
    def get_tree_stats(self) -> Dict[str, Any]:
        """Get statistics about the current tree."""
        return {
            "session_id": self.session_id,
            "chunk_count": len(self.chunk_hashes),
            "has_tree": self.merkle_tree is not None,
            "root_hash": self.merkle_root,
            "tree_height": self._calculate_tree_height()
        }
    
    def _calculate_tree_height(self) -> int:
        """Calculate the height of the Merkle tree."""
        if not self.chunk_hashes:
            return 0
        
        import math
        chunk_count = len(self.chunk_hashes)
        return math.ceil(math.log2(chunk_count)) if chunk_count > 1 else 0


class SessionMerkleManager:
    """
    Manages Merkle tree building for multiple sessions.
    Interfaces with encryptor and On-System Chain client.
    """
    
    def __init__(self):
        self.active_builders: Dict[str, LucidMerkleBuilder] = {}
        logger.info("Session Merkle manager initialized")
    
    def start_session(self, session_id: str) -> None:
        """Start Merkle tree building for a new session."""
        if session_id in self.active_builders:
            logger.warning(f"Merkle builder already exists for session {session_id}")
            return
        
        builder = LucidMerkleBuilder(session_id)
        self.active_builders[session_id] = builder
        
        logger.info(f"Started Merkle building for session {session_id}")
    
    def add_encrypted_chunk(self, session_id: str, encrypted_chunk: EncryptedChunk) -> None:
        """Add encrypted chunk to session's Merkle tree."""
        builder = self.active_builders.get(session_id)
        if not builder:
            raise ValueError(f"No Merkle builder found for session {session_id}")
        
        builder.add_chunk_hash(encrypted_chunk.ciphertext_sha256)
    
    def finalize_session(self, session_id: str) -> str:
        """
        Finalize Merkle tree for session and return root hash.
        
        Args:
            session_id: Session to finalize
            
        Returns:
            Hex-encoded Merkle root hash for anchoring
        """
        builder = self.active_builders.get(session_id)
        if not builder:
            raise ValueError(f"No Merkle builder found for session {session_id}")
        
        root_hash = builder.get_root_hash()
        
        # Keep builder for proof generation
        logger.info(f"Finalized Merkle tree for session {session_id}: {root_hash[:16]}...")
        return root_hash
    
    def generate_chunk_proof(self, session_id: str, chunk_index: int) -> MerkleProof:
        """Generate proof for a specific chunk in a session."""
        builder = self.active_builders.get(session_id)
        if not builder:
            raise ValueError(f"No Merkle builder found for session {session_id}")
        
        return builder.generate_proof(chunk_index)
    
    def verify_chunk_proof(self, session_id: str, proof: MerkleProof) -> bool:
        """Verify a chunk proof against a session's Merkle root."""
        builder = self.active_builders.get(session_id)
        if not builder:
            raise ValueError(f"No Merkle builder found for session {session_id}")
        
        return builder.verify_proof(proof)
    
    def cleanup_session(self, session_id: str) -> None:
        """Remove Merkle builder for completed session."""
        if session_id in self.active_builders:
            del self.active_builders[session_id]
            logger.info(f"Cleaned up Merkle builder for session {session_id}")
    
    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get Merkle tree statistics for a session."""
        builder = self.active_builders.get(session_id)
        return builder.get_tree_stats() if builder else None
    
    def get_active_sessions(self) -> List[str]:
        """Get list of sessions with active Merkle builders."""
        return list(self.active_builders.keys())


# Module-level instance for service integration
merkle_manager = SessionMerkleManager()


def validate_merkle_root_format(root_hash: str) -> bool:
    """
    Validate that a Merkle root hash is properly formatted.
    
    Args:
        root_hash: Hex-encoded hash to validate
        
    Returns:
        True if format is valid (64 hex characters for BLAKE3)
    """
    if not isinstance(root_hash, str):
        return False
    
    if len(root_hash) != 64:  # 32 bytes = 64 hex chars
        return False
    
    try:
        bytes.fromhex(root_hash)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    # Test Merkle tree functionality
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python merkle_builder.py <session_id>")
        sys.exit(1)
    
    session_id = sys.argv[1]
    builder = LucidMerkleBuilder(session_id)
    
    # Add some test chunk hashes
    test_hashes = [
        "a1b2c3d4e5f67890" * 8,  # 64 chars
        "f0e1d2c3b4a59687" * 8,
        "9876543210abcdef" * 8,
        "fedcba0987654321" * 8
    ]
    
    for i, test_hash in enumerate(test_hashes):
        builder.add_chunk_hash(test_hash)
        print(f"Added chunk {i}: {test_hash[:16]}...")
    
    root_hash = builder.get_root_hash()
    print(f"Merkle root: {root_hash}")
    
    # Test proof generation
    proof = builder.generate_proof(0)
    is_valid = builder.verify_proof(proof)
    print(f"Proof for chunk 0 valid: {is_valid}")
    
    stats = builder.get_tree_stats()
    print(f"Tree stats: {stats}")