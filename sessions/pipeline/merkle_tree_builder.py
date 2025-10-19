#!/usr/bin/env python3
"""
LUCID Merkle Tree Builder - SPEC-1B Implementation
Builds BLAKE3 Merkle trees for session chunk integrity verification
"""

import asyncio
import logging
import time
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MerkleNode:
    """Merkle tree node representation"""
    hash: str
    left_child: Optional['MerkleNode'] = None
    right_child: Optional['MerkleNode'] = None
    parent: Optional['MerkleNode'] = None
    is_leaf: bool = False
    chunk_id: Optional[str] = None
    level: int = 0

@dataclass
class MerkleTreeConfig:
    """Merkle tree configuration"""
    hash_algorithm: str = "BLAKE3"  # BLAKE3 for Merkle trees
    max_leaves_per_level: int = 2  # Binary tree
    tree_height: int = 0
    root_hash: str = ""
    leaf_count: int = 0

class MerkleTreeBuilder:
    """
    LUCID Merkle Tree Builder
    
    Builds BLAKE3 Merkle trees for session chunk integrity verification.
    Supports incremental building as chunks are processed.
    """
    
    def __init__(self, config: MerkleTreeConfig):
        self.config = config
        self.session_trees: Dict[str, Dict[str, Any]] = {}
        self.leaf_nodes: Dict[str, List[MerkleNode]] = {}  # session_id -> leaf nodes
        self.tree_nodes: Dict[str, List[List[MerkleNode]]] = {}  # session_id -> level nodes
        
    async def initialize_session_tree(self, session_id: str) -> str:
        """
        Initialize Merkle tree for session
        
        Args:
            session_id: Session identifier
            
        Returns:
            tree_id: Unique tree identifier
        """
        try:
            logger.info(f"Initializing Merkle tree for session {session_id}")
            
            tree_id = f"tree_{session_id}_{int(time.time())}"
            
            # Initialize session tree data
            self.session_trees[session_id] = {
                "tree_id": tree_id,
                "session_id": session_id,
                "config": self.config.__dict__,
                "created_at": datetime.utcnow(),
                "last_updated": datetime.utcnow(),
                "root_hash": "",
                "tree_height": 0,
                "leaf_count": 0,
                "is_finalized": False
            }
            
            # Initialize node storage
            self.leaf_nodes[session_id] = []
            self.tree_nodes[session_id] = []
            
            logger.info(f"Merkle tree {tree_id} initialized for session {session_id}")
            
            return tree_id
            
        except Exception as e:
            logger.error(f"Failed to initialize Merkle tree for session {session_id}: {e}")
            raise
    
    async def add_chunk_hash(self, session_id: str, chunk_id: str, chunk_hash: str) -> bool:
        """
        Add chunk hash to Merkle tree
        
        Args:
            session_id: Session identifier
            chunk_id: Chunk identifier
            chunk_hash: Chunk hash to add
            
        Returns:
            success: True if hash added successfully
        """
        try:
            if session_id not in self.session_trees:
                raise ValueError(f"No Merkle tree found for session {session_id}")
            
            tree_data = self.session_trees[session_id]
            
            if tree_data["is_finalized"]:
                raise ValueError(f"Merkle tree for session {session_id} is already finalized")
            
            # Create leaf node
            leaf_node = MerkleNode(
                hash=chunk_hash,
                is_leaf=True,
                chunk_id=chunk_id,
                level=0
            )
            
            # Add to leaf nodes
            self.leaf_nodes[session_id].append(leaf_node)
            tree_data["leaf_count"] += 1
            tree_data["last_updated"] = datetime.utcnow()
            
            logger.debug(f"Added chunk {chunk_id} hash to Merkle tree for session {session_id}")
            
            # Rebuild tree if we have enough leaves for a level
            await self._rebuild_tree_levels(session_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to add chunk hash to Merkle tree for session {session_id}: {e}")
            return False
    
    async def _rebuild_tree_levels(self, session_id: str):
        """Rebuild tree levels after adding new leaves"""
        try:
            tree_data = self.session_trees[session_id]
            leaves = self.leaf_nodes[session_id]
            
            if len(leaves) == 0:
                return
            
            # Clear existing tree nodes
            self.tree_nodes[session_id] = []
            
            # Start with leaf nodes as level 0
            current_level = leaves.copy()
            level = 0
            self.tree_nodes[session_id].append(current_level)
            
            # Build levels until we have a single root node
            while len(current_level) > 1:
                next_level = []
                level += 1
                
                # Process pairs of nodes
                for i in range(0, len(current_level), 2):
                    left_node = current_level[i]
                    right_node = current_level[i + 1] if i + 1 < len(current_level) else left_node
                    
                    # Create parent node
                    parent_hash = await self._hash_concatenated(left_node.hash, right_node.hash)
                    parent_node = MerkleNode(
                        hash=parent_hash,
                        left_child=left_node,
                        right_child=right_node,
                        level=level
                    )
                    
                    # Set parent references
                    left_node.parent = parent_node
                    right_node.parent = parent_node
                    
                    next_level.append(parent_node)
                
                self.tree_nodes[session_id].append(next_level)
                current_level = next_level
            
            # Update tree metadata
            tree_data["tree_height"] = level
            tree_data["root_hash"] = current_level[0].hash if current_level else ""
            
            logger.debug(f"Rebuilt Merkle tree for session {string} - height: {level}, root: {tree_data['root_hash'][:16]}...")
            
        except Exception as e:
            logger.error(f"Failed to rebuild tree levels for session {session_id}: {e}")
            raise
    
    async def _hash_concatenated(self, left_hash: str, right_hash: str) -> str:
        """
        Hash concatenated left and right hashes
        
        Args:
            left_hash: Left hash
            right_hash: Right hash
            
        Returns:
            combined_hash: Hash of concatenated hashes
        """
        try:
            # Concatenate hashes (left first, then right)
            combined = left_hash + right_hash
            
            if self.config.hash_algorithm == "BLAKE3":
                # Use blake2b as BLAKE3 equivalent
                hash_obj = hashlib.blake2b(combined.encode(), digest_size=32)
            elif self.config.hash_algorithm == "SHA256":
                hash_obj = hashlib.sha256(combined.encode())
            else:
                # Default to SHA256
                hash_obj = hashlib.sha256(combined.encode())
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            logger.error(f"Hash concatenation failed: {e}")
            raise
    
    async def finalize_tree(self, session_id: str) -> Dict[str, Any]:
        """
        Finalize Merkle tree and generate proof data
        
        Args:
            session_id: Session identifier
            
        Returns:
            tree_proof: Finalized tree proof data
        """
        try:
            if session_id not in self.session_trees:
                raise ValueError(f"No Merkle tree found for session {session_id}")
            
            tree_data = self.session_trees[session_id]
            
            if tree_data["is_finalized"]:
                logger.warning(f"Merkle tree for session {session_id} is already finalized")
                return self._get_tree_proof(session_id)
            
            # Ensure tree is properly built
            await self._rebuild_tree_levels(session_id)
            
            # Mark as finalized
            tree_data["is_finalized"] = True
            tree_data["finalized_at"] = datetime.utcnow()
            
            # Generate proof data
            tree_proof = self._get_tree_proof(session_id)
            
            logger.info(f"Merkle tree finalized for session {session_id} - root: {tree_data['root_hash'][:16]}...")
            
            return tree_proof
            
        except Exception as e:
            logger.error(f"Failed to finalize Merkle tree for session {session_id}: {e}")
            raise
    
    def _get_tree_proof(self, session_id: str) -> Dict[str, Any]:
        """Get complete tree proof data"""
        tree_data = self.session_trees[session_id]
        leaves = self.leaf_nodes[session_id]
        
        return {
            "tree_id": tree_data["tree_id"],
            "session_id": session_id,
            "root_hash": tree_data["root_hash"],
            "tree_height": tree_data["tree_height"],
            "leaf_count": tree_data["leaf_count"],
            "hash_algorithm": self.config.hash_algorithm,
            "created_at": tree_data["created_at"],
            "finalized_at": tree_data.get("finalized_at"),
            "is_finalized": tree_data["is_finalized"],
            "leaf_hashes": [leaf.hash for leaf in leaves],
            "tree_structure": self._serialize_tree_structure(session_id)
        }
    
    def _serialize_tree_structure(self, session_id: str) -> List[Dict[str, Any]]:
        """Serialize tree structure for storage/transmission"""
        tree_levels = self.tree_nodes[session_id]
        serialized = []
        
        for level, nodes in enumerate(tree_levels):
            level_data = {
                "level": level,
                "node_count": len(nodes),
                "nodes": []
            }
            
            for node in nodes:
                node_data = {
                    "hash": node.hash,
                    "level": node.level,
                    "is_leaf": node.is_leaf,
                    "chunk_id": node.chunk_id,
                    "has_left_child": node.left_child is not None,
                    "has_right_child": node.right_child is not None,
                    "has_parent": node.parent is not None
                }
                level_data["nodes"].append(node_data)
            
            serialized.append(level_data)
        
        return serialized
    
    async def verify_chunk_in_tree(self, session_id: str, chunk_id: str, chunk_hash: str) -> Dict[str, Any]:
        """
        Verify chunk is in Merkle tree and generate proof path
        
        Args:
            session_id: Session identifier
            chunk_id: Chunk identifier
            chunk_hash: Chunk hash to verify
            
        Returns:
            verification_result: Verification result with proof path
        """
        try:
            if session_id not in self.session_trees:
                return {"valid": False, "error": f"No Merkle tree found for session {session_id}"}
            
            tree_data = self.session_trees[session_id]
            leaves = self.leaf_nodes[session_id]
            
            # Find leaf node with matching chunk_id and hash
            leaf_node = None
            for leaf in leaves:
                if leaf.chunk_id == chunk_id and leaf.hash == chunk_hash:
                    leaf_node = leaf
                    break
            
            if not leaf_node:
                return {"valid": False, "error": f"Chunk {chunk_id} not found in tree"}
            
            # Generate proof path to root
            proof_path = await self._generate_proof_path(leaf_node)
            
            # Verify proof path
            verification_hash = chunk_hash
            for proof_node in proof_path:
                verification_hash = await self._hash_concatenated(
                    verification_hash, proof_node["hash"]
                )
            
            is_valid = verification_hash == tree_data["root_hash"]
            
            return {
                "valid": is_valid,
                "chunk_id": chunk_id,
                "chunk_hash": chunk_hash,
                "proof_path": proof_path,
                "calculated_hash": verification_hash,
                "tree_root_hash": tree_data["root_hash"],
                "verification_timestamp": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Failed to verify chunk in tree for session {session_id}: {e}")
            return {"valid": False, "error": str(e)}
    
    async def _generate_proof_path(self, leaf_node: MerkleNode) -> List[Dict[str, Any]]:
        """Generate proof path from leaf to root"""
        proof_path = []
        current_node = leaf_node
        
        while current_node.parent is not None:
            parent = current_node.parent
            
            # Determine if current node is left or right child
            is_left_child = parent.left_child == current_node
            
            # Add sibling to proof path
            sibling = parent.right_child if is_left_child else parent.left_child
            proof_path.append({
                "hash": sibling.hash,
                "is_left": not is_left_child,  # Sibling position
                "level": sibling.level
            })
            
            current_node = parent
        
        return proof_path
    
    def get_tree_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get current tree status"""
        if session_id not in self.session_trees:
            return None
        
        tree_data = self.session_trees[session_id]
        leaves = self.leaf_nodes[session_id]
        
        return {
            "session_id": session_id,
            "tree_id": tree_data["tree_id"],
            "leaf_count": tree_data["leaf_count"],
            "tree_height": tree_data["tree_height"],
            "root_hash": tree_data["root_hash"],
            "is_finalized": tree_data["is_finalized"],
            "created_at": tree_data["created_at"],
            "last_updated": tree_data["last_updated"],
            "hash_algorithm": self.config.hash_algorithm,
            "estimated_size_bytes": len(leaves) * 32  # Rough estimate
        }
    
    async def cleanup_session_tree(self, session_id: str):
        """Cleanup session tree resources"""
        try:
            logger.info(f"Cleaning up Merkle tree for session {session_id}")
            
            if session_id in self.session_trees:
                del self.session_trees[session_id]
            
            if session_id in self.leaf_nodes:
                del self.leaf_nodes[session_id]
            
            if session_id in self.tree_nodes:
                del self.tree_nodes[session_id]
            
            logger.info(f"Merkle tree cleanup completed for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup Merkle tree for session {session_id}: {e}")

# Example usage
if __name__ == "__main__":
    async def main():
        # Initialize Merkle tree builder
        config = MerkleTreeConfig(
            hash_algorithm="BLAKE3",
            max_leaves_per_level=2
        )
        
        builder = MerkleTreeBuilder(config)
        
        # Initialize session tree
        session_id = "session_123"
        tree_id = await builder.initialize_session_tree(session_id)
        print(f"Initialized Merkle tree: {tree_id}")
        
        # Add some chunk hashes
        chunk_hashes = [
            "hash1_abcdef123456789",
            "hash2_abcdef123456789",
            "hash3_abcdef123456789",
            "hash4_abcdef123456789",
            "hash5_abcdef123456789"
        ]
        
        for i, chunk_hash in enumerate(chunk_hashes):
            chunk_id = f"chunk_{i}"
            success = await builder.add_chunk_hash(session_id, chunk_id, chunk_hash)
            print(f"Added chunk {chunk_id}: {success}")
        
        # Get tree status
        status = builder.get_tree_status(session_id)
        print(f"\nTree Status:")
        print(f"  Leaf count: {status['leaf_count']}")
        print(f"  Tree height: {status['tree_height']}")
        print(f"  Root hash: {status['root_hash'][:32]}...")
        print(f"  Finalized: {status['is_finalized']}")
        
        # Finalize tree
        tree_proof = await builder.finalize_tree(session_id)
        print(f"\nTree Finalized:")
        print(f"  Root hash: {tree_proof['root_hash'][:32]}...")
        print(f"  Tree height: {tree_proof['tree_height']}")
        print(f"  Leaf count: {tree_proof['leaf_count']}")
        
        # Verify a chunk
        verification = await builder.verify_chunk_in_tree(
            session_id, "chunk_2", "hash3_abcdef123456789"
        )
        print(f"\nChunk Verification:")
        print(f"  Valid: {verification['valid']}")
        print(f"  Proof path length: {len(verification['proof_path'])}")
        
        # Cleanup
        await builder.cleanup_session_tree(session_id)
        print("\nTree cleanup completed")
    
    asyncio.run(main())
