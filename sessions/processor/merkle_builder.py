"""
Merkle Tree Builder Module
Builds and validates Merkle trees from session chunk hashes.

This module provides functionality to build Merkle trees from session chunk hashes
for blockchain anchoring. It supports incremental tree building, proof generation,
and validation for the Lucid session management system.

Features:
- Incremental Merkle tree building
- Merkle proof generation and validation
- Tree serialization and deserialization
- Performance optimization for large trees
- Integration with blockchain anchoring
- Tree integrity verification
"""

import hashlib
import logging
import json
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class MerkleNode:
    """Represents a node in the Merkle tree."""
    hash: str
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    parent: Optional['MerkleNode'] = None
    is_leaf: bool = False
    leaf_index: Optional[int] = None


@dataclass
class MerkleProof:
    """Represents a Merkle proof for a leaf node."""
    leaf_hash: str
    root_hash: str
    path: List[Tuple[str, str]]  # (hash, position) pairs
    leaf_index: int
    tree_size: int


@dataclass
class MerkleTreeMetadata:
    """Metadata for a Merkle tree."""
    root_hash: str
    leaf_count: int
    tree_height: int
    created_at: datetime
    finalized_at: Optional[datetime] = None
    session_id: Optional[str] = None


class MerkleTreeBuilder:
    """
    Builder for Merkle trees from session chunk hashes.
    
    This class provides functionality to build Merkle trees incrementally,
    generate proofs, and validate tree integrity for blockchain anchoring.
    """
    
    def __init__(self, hash_algorithm: str = "sha256"):
        """
        Initialize the Merkle tree builder.
        
        Args:
            hash_algorithm: Hash algorithm to use (default: sha256)
        """
        self.hash_algorithm = hash_algorithm
        self.leaves: List[MerkleNode] = []
        self.root: Optional[MerkleNode] = None
        self.metadata: Optional[MerkleTreeMetadata] = None
        self._is_finalized = False
        
        logger.info(f"MerkleTreeBuilder initialized with {hash_algorithm}")
    
    def add_leaf(self, data_hash: str) -> int:
        """
        Add a leaf node to the tree.
        
        Args:
            data_hash: Hash of the data to add
            
        Returns:
            Index of the added leaf
            
        Raises:
            ValueError: If tree is already finalized
        """
        if self._is_finalized:
            raise ValueError("Cannot add leaves to a finalized tree")
        
        # Create leaf node
        leaf = MerkleNode(
            hash=data_hash,
            is_leaf=True,
            leaf_index=len(self.leaves)
        )
        
        self.leaves.append(leaf)
        
        logger.debug(f"Added leaf {len(self.leaves) - 1} with hash {data_hash}")
        
        return len(self.leaves) - 1
    
    def add_leaves(self, data_hashes: List[str]) -> List[int]:
        """
        Add multiple leaf nodes to the tree.
        
        Args:
            data_hashes: List of data hashes to add
            
        Returns:
            List of indices of the added leaves
        """
        indices = []
        for data_hash in data_hashes:
            index = self.add_leaf(data_hash)
            indices.append(index)
        
        logger.debug(f"Added {len(data_hashes)} leaves to the tree")
        return indices
    
    async def build_tree(self) -> str:
        """
        Build the complete Merkle tree from the leaves.
        
        Returns:
            Root hash of the tree
            
        Raises:
            ValueError: If no leaves have been added
        """
        if not self.leaves:
            raise ValueError("Cannot build tree without leaves")
        
        if self._is_finalized:
            return self.root.hash if self.root else ""
        
        logger.info(f"Building Merkle tree with {len(self.leaves)} leaves")
        
        # Start with leaf nodes
        current_level = self.leaves.copy()
        
        # Build tree level by level
        while len(current_level) > 1:
            next_level = []
            
            # Process pairs of nodes
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else left
                
                # Create parent node
                parent_hash = self._hash_combined(left.hash, right.hash)
                parent = MerkleNode(
                    hash=parent_hash,
                    left=left,
                    right=right
                )
                
                # Set parent references
                left.parent = parent
                right.parent = parent
                
                next_level.append(parent)
            
            current_level = next_level
        
        # Set root
        self.root = current_level[0]
        
        # Create metadata
        self.metadata = MerkleTreeMetadata(
            root_hash=self.root.hash,
            leaf_count=len(self.leaves),
            tree_height=self._calculate_height(),
            created_at=datetime.utcnow()
        )
        
        logger.info(f"Built Merkle tree with root hash: {self.root.hash}")
        
        return self.root.hash
    
    async def finalize_tree(self, data_hashes: List[str]) -> str:
        """
        Build and finalize a Merkle tree from a list of data hashes.
        
        Args:
            data_hashes: List of data hashes to build tree from
            
        Returns:
            Root hash of the finalized tree
        """
        # Clear existing tree
        self.leaves.clear()
        self.root = None
        self._is_finalized = False
        
        # Add all leaves
        self.add_leaves(data_hashes)
        
        # Build tree
        root_hash = await self.build_tree()
        
        # Finalize
        self._is_finalized = True
        if self.metadata:
            self.metadata.finalized_at = datetime.utcnow()
        
        logger.info(f"Finalized Merkle tree with {len(data_hashes)} leaves")
        
        return root_hash
    
    def generate_proof(self, leaf_index: int) -> Optional[MerkleProof]:
        """
        Generate a Merkle proof for a leaf node.
        
        Args:
            leaf_index: Index of the leaf to generate proof for
            
        Returns:
            Merkle proof or None if leaf doesn't exist
        """
        if leaf_index >= len(self.leaves) or leaf_index < 0:
            return None
        
        if not self.root:
            return None
        
        leaf = self.leaves[leaf_index]
        proof_path = []
        current = leaf
        
        # Walk up the tree to build proof path
        while current.parent:
            parent = current.parent
            sibling = parent.right if current == parent.left else parent.left
            
            if sibling:
                position = "right" if current == parent.left else "left"
                proof_path.append((sibling.hash, position))
            
            current = parent
        
        return MerkleProof(
            leaf_hash=leaf.hash,
            root_hash=self.root.hash,
            path=proof_path,
            leaf_index=leaf_index,
            tree_size=len(self.leaves)
        )
    
    def verify_proof(self, proof: MerkleProof) -> bool:
        """
        Verify a Merkle proof.
        
        Args:
            proof: Merkle proof to verify
            
        Returns:
            True if proof is valid
        """
        try:
            current_hash = proof.leaf_hash
            
            # Reconstruct hash by following proof path
            for sibling_hash, position in proof.path:
                if position == "left":
                    current_hash = self._hash_combined(sibling_hash, current_hash)
                else:
                    current_hash = self._hash_combined(current_hash, sibling_hash)
            
            # Check if reconstructed hash matches root
            return current_hash == proof.root_hash
            
        except Exception as e:
            logger.error(f"Proof verification failed: {str(e)}")
            return False
    
    def get_root_hash(self) -> Optional[str]:
        """
        Get the root hash of the tree.
        
        Returns:
            Root hash or None if tree not built
        """
        return self.root.hash if self.root else None
    
    def get_leaf_count(self) -> int:
        """
        Get the number of leaves in the tree.
        
        Returns:
            Number of leaves
        """
        return len(self.leaves)
    
    def get_tree_height(self) -> int:
        """
        Get the height of the tree.
        
        Returns:
            Tree height
        """
        if not self.root:
            return 0
        return self._calculate_height()
    
    def is_finalized(self) -> bool:
        """
        Check if the tree is finalized.
        
        Returns:
            True if tree is finalized
        """
        return self._is_finalized
    
    def get_metadata(self) -> Optional[MerkleTreeMetadata]:
        """
        Get tree metadata.
        
        Returns:
            Tree metadata or None if not available
        """
        return self.metadata
    
    def serialize_tree(self) -> Dict[str, Any]:
        """
        Serialize the tree to a dictionary.
        
        Returns:
            Serialized tree data
        """
        if not self.root:
            return {}
        
        return {
            "root_hash": self.root.hash,
            "leaf_count": len(self.leaves),
            "tree_height": self.get_tree_height(),
            "is_finalized": self._is_finalized,
            "metadata": asdict(self.metadata) if self.metadata else None,
            "leaves": [leaf.hash for leaf in self.leaves]
        }
    
    def deserialize_tree(self, data: Dict[str, Any]) -> bool:
        """
        Deserialize a tree from a dictionary.
        
        Args:
            data: Serialized tree data
            
        Returns:
            True if deserialization successful
        """
        try:
            # Clear existing tree
            self.leaves.clear()
            self.root = None
            self._is_finalized = False
            
            # Restore leaves
            if "leaves" in data:
                for leaf_hash in data["leaves"]:
                    self.add_leaf(leaf_hash)
            
            # Rebuild tree if we have leaves
            if self.leaves:
                asyncio.create_task(self.build_tree())
            
            # Restore metadata
            if "metadata" in data and data["metadata"]:
                metadata_dict = data["metadata"]
                self.metadata = MerkleTreeMetadata(
                    root_hash=metadata_dict["root_hash"],
                    leaf_count=metadata_dict["leaf_count"],
                    tree_height=metadata_dict["tree_height"],
                    created_at=datetime.fromisoformat(metadata_dict["created_at"]),
                    finalized_at=datetime.fromisoformat(metadata_dict["finalized_at"]) if metadata_dict.get("finalized_at") else None,
                    session_id=metadata_dict.get("session_id")
                )
            
            # Restore finalized state
            self._is_finalized = data.get("is_finalized", False)
            
            logger.info("Successfully deserialized Merkle tree")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deserialize tree: {str(e)}")
            return False
    
    def _hash_combined(self, left_hash: str, right_hash: str) -> str:
        """
        Hash two hashes together.
        
        Args:
            left_hash: Left hash
            right_hash: Right hash
            
        Returns:
            Combined hash
        """
        combined = f"{left_hash}{right_hash}"
        
        if self.hash_algorithm == "sha256":
            return hashlib.sha256(combined.encode()).hexdigest()
        elif self.hash_algorithm == "sha3_256":
            return hashlib.sha3_256(combined.encode()).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {self.hash_algorithm}")
    
    def _calculate_height(self) -> int:
        """
        Calculate the height of the tree.
        
        Returns:
            Tree height
        """
        if not self.leaves:
            return 0
        
        # Height = ceil(log2(leaf_count))
        import math
        return math.ceil(math.log2(len(self.leaves)))


class MerkleTreeManager:
    """
    Manager for multiple Merkle trees.
    
    This class provides functionality to manage multiple Merkle trees,
    typically one per session, with efficient storage and retrieval.
    """
    
    def __init__(self):
        """Initialize the Merkle tree manager."""
        self.trees: Dict[str, MerkleTreeBuilder] = {}
        self.tree_metadata: Dict[str, MerkleTreeMetadata] = {}
        
        logger.info("MerkleTreeManager initialized")
    
    async def create_tree(self, session_id: str) -> MerkleTreeBuilder:
        """
        Create a new Merkle tree for a session.
        
        Args:
            session_id: ID of the session
            
        Returns:
            New Merkle tree builder
        """
        if session_id in self.trees:
            logger.warning(f"Tree for session {session_id} already exists")
            return self.trees[session_id]
        
        tree = MerkleTreeBuilder()
        self.trees[session_id] = tree
        
        logger.info(f"Created new Merkle tree for session {session_id}")
        return tree
    
    async def add_chunk_hash(self, session_id: str, chunk_hash: str) -> int:
        """
        Add a chunk hash to a session's tree.
        
        Args:
            session_id: ID of the session
            chunk_hash: Hash of the chunk
            
        Returns:
            Index of the added leaf
        """
        if session_id not in self.trees:
            await self.create_tree(session_id)
        
        tree = self.trees[session_id]
        return tree.add_leaf(chunk_hash)
    
    async def finalize_session_tree(self, session_id: str) -> Optional[str]:
        """
        Finalize a session's Merkle tree.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Root hash of the finalized tree
        """
        if session_id not in self.trees:
            logger.warning(f"No tree found for session {session_id}")
            return None
        
        tree = self.trees[session_id]
        root_hash = await tree.build_tree()
        
        # Store metadata
        self.tree_metadata[session_id] = tree.get_metadata()
        
        logger.info(f"Finalized tree for session {session_id} with root: {root_hash}")
        return root_hash
    
    def get_session_root(self, session_id: str) -> Optional[str]:
        """
        Get the root hash for a session's tree.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Root hash or None if not found
        """
        if session_id in self.trees:
            return self.trees[session_id].get_root_hash()
        return None
    
    def generate_chunk_proof(self, session_id: str, chunk_index: int) -> Optional[MerkleProof]:
        """
        Generate a proof for a chunk in a session's tree.
        
        Args:
            session_id: ID of the session
            chunk_index: Index of the chunk
            
        Returns:
            Merkle proof or None if not found
        """
        if session_id in self.trees:
            return self.trees[session_id].generate_proof(chunk_index)
        return None
    
    def verify_chunk_proof(self, session_id: str, proof: MerkleProof) -> bool:
        """
        Verify a proof for a chunk in a session's tree.
        
        Args:
            session_id: ID of the session
            proof: Merkle proof to verify
            
        Returns:
            True if proof is valid
        """
        if session_id in self.trees:
            return self.trees[session_id].verify_proof(proof)
        return False
    
    def get_session_metadata(self, session_id: str) -> Optional[MerkleTreeMetadata]:
        """
        Get metadata for a session's tree.
        
        Args:
            session_id: ID of the session
            
        Returns:
            Tree metadata or None if not found
        """
        return self.tree_metadata.get(session_id)
    
    def cleanup_session(self, session_id: str):
        """
        Clean up resources for a session.
        
        Args:
            session_id: ID of the session to clean up
        """
        if session_id in self.trees:
            del self.trees[session_id]
        
        if session_id in self.tree_metadata:
            del self.tree_metadata[session_id]
        
        logger.info(f"Cleaned up Merkle tree resources for session {session_id}")
    
    def get_all_sessions(self) -> List[str]:
        """
        Get list of all active sessions.
        
        Returns:
            List of session IDs
        """
        return list(self.trees.keys())
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """
        Get statistics for the manager.
        
        Returns:
            Dictionary containing manager statistics
        """
        return {
            "active_sessions": len(self.trees),
            "total_trees": len(self.tree_metadata),
            "sessions": list(self.trees.keys())
        }


# Utility functions for Merkle tree operations

def calculate_merkle_tree_size(leaf_count: int) -> int:
    """
    Calculate the total number of nodes in a Merkle tree.
    
    Args:
        leaf_count: Number of leaves in the tree
        
    Returns:
        Total number of nodes
    """
    if leaf_count == 0:
        return 0
    
    # For a complete binary tree: 2 * leaf_count - 1
    return 2 * leaf_count - 1


def calculate_merkle_tree_height(leaf_count: int) -> int:
    """
    Calculate the height of a Merkle tree.
    
    Args:
        leaf_count: Number of leaves in the tree
        
    Returns:
        Tree height
    """
    if leaf_count == 0:
        return 0
    
    import math
    return math.ceil(math.log2(leaf_count))


def validate_merkle_proof_structure(proof: MerkleProof) -> bool:
    """
    Validate the structure of a Merkle proof.
    
    Args:
        proof: Merkle proof to validate
        
    Returns:
        True if proof structure is valid
    """
    try:
        # Check required fields
        if not proof.leaf_hash or not proof.root_hash:
            return False
        
        if proof.leaf_index < 0 or proof.leaf_index >= proof.tree_size:
            return False
        
        if not proof.path:
            return False
        
        # Validate path structure
        for hash_val, position in proof.path:
            if not hash_val or position not in ["left", "right"]:
                return False
        
        return True
        
    except Exception:
        return False
