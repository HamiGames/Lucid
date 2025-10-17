# Path: blockchain/core/merkle_tree_builder.py
# Lucid Blockchain Core - Merkle Tree Builder
# Builds and validates Merkle trees for session chunks and transactions
# Based on BUILD_REQUIREMENTS_GUIDE.md Step 11 and blockchain cluster specifications

from __future__ import annotations

import asyncio
import logging
import hashlib
import struct
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase
import blake3

from .models import (
    ChunkMetadata, SessionManifest, SessionAnchor, Transaction,
    generate_session_id
)

logger = logging.getLogger(__name__)

# Merkle tree configuration
MERKLE_TREE_HEIGHT_MAX = 20    # Maximum tree height (supports ~1M leaves)
HASH_ALGORITHM = "blake3"      # Hash algorithm for Merkle tree
LEAF_PREFIX = b"leaf:"         # Prefix for leaf nodes
INTERNAL_PREFIX = b"internal:" # Prefix for internal nodes

@dataclass
class MerkleNode:
    """Represents a node in the Merkle tree"""
    hash: str
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    is_leaf: bool = False
    data: Optional[str] = None
    index: int = 0

@dataclass
class MerkleProof:
    """Merkle proof for a specific leaf"""
    leaf_hash: str
    leaf_index: int
    proof_hashes: List[str]
    proof_directions: List[bool]  # True = right, False = left
    root_hash: str

@dataclass
class MerkleTree:
    """Complete Merkle tree structure"""
    root: MerkleNode
    leaves: List[MerkleNode]
    height: int
    total_leaves: int
    session_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class MerkleTreeBuilder:
    """
    Merkle Tree Builder for the lucid_blocks blockchain
    
    Responsibilities:
    - Build Merkle trees for session chunks
    - Build Merkle trees for block transactions
    - Generate and verify Merkle proofs
    - Store and retrieve Merkle tree data
    - Validate Merkle tree integrity
    - Support incremental tree updates
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, storage_path: Optional[str] = None):
        self.db = db
        self.storage_path = storage_path or "/data/merkle"
        
        # Tree cache for recent trees
        self.tree_cache: Dict[str, MerkleTree] = {}
        self.proof_cache: Dict[str, MerkleProof] = {}
        
        # Statistics
        self.trees_built = 0
        self.proofs_generated = 0
        self.verifications_performed = 0
        
        logger.info("Merkle tree builder initialized")
    
    async def start(self) -> bool:
        """Start the Merkle tree builder"""
        try:
            # Setup MongoDB indexes
            await self._setup_mongodb_indexes()
            
            # Load recent trees into cache
            await self._load_tree_cache()
            
            logger.info("Merkle tree builder started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Merkle tree builder: {e}")
            return False
    
    async def stop(self):
        """Stop the Merkle tree builder"""
        try:
            # Clear caches
            self.tree_cache.clear()
            self.proof_cache.clear()
            
            logger.info("Merkle tree builder stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop Merkle tree builder: {e}")
    
    async def _setup_mongodb_indexes(self):
        """Setup MongoDB indexes for Merkle tree collections"""
        try:
            # Merkle trees collection
            await self.db["merkle_trees"].create_index([("root_hash", 1)], unique=True)
            await self.db["merkle_trees"].create_index([("session_id", 1)])
            await self.db["merkle_trees"].create_index([("created_at", -1)])
            await self.db["merkle_trees"].create_index([("height", 1)])
            
            # Merkle proofs collection
            await self.db["merkle_proofs"].create_index([("root_hash", 1), ("leaf_index", 1)])
            await self.db["merkle_proofs"].create_index([("leaf_hash", 1)])
            
            # Merkle nodes collection (for large trees)
            await self.db["merkle_nodes"].create_index([("tree_id", 1), ("node_hash", 1)])
            await self.db["merkle_nodes"].create_index([("tree_id", 1), ("level", 1), ("index", 1)])
            
            logger.info("Merkle tree builder MongoDB indexes created")
            
        except Exception as e:
            logger.error(f"Failed to setup MongoDB indexes: {e}")
    
    async def _load_tree_cache(self):
        """Load recent Merkle trees into cache"""
        try:
            # Load last 50 trees
            cursor = self.db["merkle_trees"].find({}).sort("created_at", -1).limit(50)
            
            async for tree_doc in cursor:
                tree = await self._doc_to_merkle_tree(tree_doc)
                if tree:
                    self.tree_cache[tree.root.hash] = tree
            
            logger.info(f"Loaded {len(self.tree_cache)} Merkle trees into cache")
            
        except Exception as e:
            logger.error(f"Failed to load tree cache: {e}")
    
    async def build_session_merkle_tree(self, session_id: str, chunks: List[ChunkMetadata]) -> MerkleTree:
        """Build Merkle tree for session chunks"""
        try:
            if not chunks:
                raise ValueError("Cannot build Merkle tree with no chunks")
            
            # Create leaf nodes from chunk hashes
            leaves = []
            for i, chunk in enumerate(chunks):
                leaf_data = f"{chunk.chunk_id}:{chunk.chunk_hash}:{chunk.size}"
                leaf_hash = self._hash_leaf(leaf_data)
                
                leaf_node = MerkleNode(
                    hash=leaf_hash,
                    is_leaf=True,
                    data=leaf_data,
                    index=i
                )
                leaves.append(leaf_node)
            
            # Build the tree
            root = await self._build_tree_from_leaves(leaves)
            
            # Create tree structure
            tree = MerkleTree(
                root=root,
                leaves=leaves,
                height=self._calculate_tree_height(len(leaves)),
                total_leaves=len(leaves),
                session_id=session_id
            )
            
            # Store tree in database
            await self._store_merkle_tree(tree)
            
            # Add to cache
            self.tree_cache[root.hash] = tree
            
            self.trees_built += 1
            logger.info(f"Session Merkle tree built: {session_id}, root: {root.hash}")
            
            return tree
            
        except Exception as e:
            logger.error(f"Failed to build session Merkle tree: {e}")
            raise
    
    async def build_transaction_merkle_tree(self, transactions: List[Transaction]) -> MerkleTree:
        """Build Merkle tree for block transactions"""
        try:
            if not transactions:
                # Empty tree for blocks with no transactions
                empty_hash = self._hash_leaf("")
                root = MerkleNode(hash=empty_hash, is_leaf=True, data="", index=0)
                
                return MerkleTree(
                    root=root,
                    leaves=[root],
                    height=0,
                    total_leaves=0
                )
            
            # Create leaf nodes from transaction hashes
            leaves = []
            for i, tx in enumerate(transactions):
                leaf_data = f"{tx.id}:{tx.from_address}:{tx.to_address}:{tx.value}"
                leaf_hash = self._hash_leaf(leaf_data)
                
                leaf_node = MerkleNode(
                    hash=leaf_hash,
                    is_leaf=True,
                    data=leaf_data,
                    index=i
                )
                leaves.append(leaf_node)
            
            # Build the tree
            root = await self._build_tree_from_leaves(leaves)
            
            # Create tree structure
            tree = MerkleTree(
                root=root,
                leaves=leaves,
                height=self._calculate_tree_height(len(leaves)),
                total_leaves=len(leaves)
            )
            
            # Store tree in database
            await self._store_merkle_tree(tree)
            
            # Add to cache
            self.tree_cache[root.hash] = tree
            
            self.trees_built += 1
            logger.info(f"Transaction Merkle tree built: root: {root.hash}")
            
            return tree
            
        except Exception as e:
            logger.error(f"Failed to build transaction Merkle tree: {e}")
            raise
    
    async def _build_tree_from_leaves(self, leaves: List[MerkleNode]) -> MerkleNode:
        """Build Merkle tree from leaf nodes"""
        try:
            if not leaves:
                raise ValueError("Cannot build tree with no leaves")
            
            if len(leaves) == 1:
                return leaves[0]
            
            # Ensure we have an even number of nodes (duplicate last if odd)
            current_level = leaves[:]
            if len(current_level) % 2 == 1:
                current_level.append(current_level[-1])  # Duplicate last node
            
            # Build tree level by level
            while len(current_level) > 1:
                next_level = []
                
                for i in range(0, len(current_level), 2):
                    left = current_level[i]
                    right = current_level[i + 1] if i + 1 < len(current_level) else left
                    
                    # Create internal node
                    combined_data = f"{left.hash}:{right.hash}"
                    internal_hash = self._hash_internal(combined_data)
                    
                    internal_node = MerkleNode(
                        hash=internal_hash,
                        left=left,
                        right=right,
                        is_leaf=False,
                        index=i // 2
                    )
                    
                    next_level.append(internal_node)
                
                current_level = next_level
                
                # Ensure even number for next iteration
                if len(current_level) > 1 and len(current_level) % 2 == 1:
                    current_level.append(current_level[-1])
            
            return current_level[0]
            
        except Exception as e:
            logger.error(f"Failed to build tree from leaves: {e}")
            raise
    
    def _hash_leaf(self, data: str) -> str:
        """Hash leaf node data"""
        return blake3.blake3(LEAF_PREFIX + data.encode()).hexdigest()
    
    def _hash_internal(self, data: str) -> str:
        """Hash internal node data"""
        return blake3.blake3(INTERNAL_PREFIX + data.encode()).hexdigest()
    
    def _calculate_tree_height(self, num_leaves: int) -> int:
        """Calculate the height of a Merkle tree"""
        if num_leaves <= 1:
            return 0
        return math.ceil(math.log2(num_leaves))
    
    async def generate_merkle_proof(self, tree_root_hash: str, leaf_index: int) -> Optional[MerkleProof]:
        """Generate Merkle proof for a specific leaf"""
        try:
            # Get tree from cache or database
            tree = await self._get_merkle_tree(tree_root_hash)
            if not tree:
                logger.error(f"Tree not found: {tree_root_hash}")
                return None
            
            if leaf_index >= len(tree.leaves):
                logger.error(f"Leaf index out of range: {leaf_index}")
                return None
            
            # Generate proof path
            proof_hashes = []
            proof_directions = []
            
            current_node = tree.leaves[leaf_index]
            current_index = leaf_index
            
            # Traverse up the tree
            await self._generate_proof_path(tree.root, current_node, current_index, proof_hashes, proof_directions)
            
            # Create proof
            proof = MerkleProof(
                leaf_hash=current_node.hash,
                leaf_index=leaf_index,
                proof_hashes=proof_hashes,
                proof_directions=proof_directions,
                root_hash=tree.root.hash
            )
            
            # Store proof in database
            await self._store_merkle_proof(proof)
            
            # Add to cache
            proof_key = f"{tree_root_hash}:{leaf_index}"
            self.proof_cache[proof_key] = proof
            
            self.proofs_generated += 1
            logger.debug(f"Merkle proof generated for leaf {leaf_index}")
            
            return proof
            
        except Exception as e:
            logger.error(f"Failed to generate Merkle proof: {e}")
            return None
    
    async def _generate_proof_path(self, root: MerkleNode, target_node: MerkleNode, 
                                 current_index: int, proof_hashes: List[str], 
                                 proof_directions: List[bool]):
        """Recursively generate proof path"""
        try:
            # This is a simplified implementation
            # In a full implementation, we would traverse the tree structure
            # For now, we'll create a basic proof structure
            
            # Add sibling hashes to proof (this is a placeholder)
            # Real implementation would traverse the tree and collect sibling hashes
            
            pass  # Placeholder for full implementation
            
        except Exception as e:
            logger.error(f"Failed to generate proof path: {e}")
    
    async def verify_merkle_proof(self, proof: MerkleProof) -> bool:
        """Verify a Merkle proof"""
        try:
            if not proof.proof_hashes:
                # Single leaf tree
                return proof.leaf_hash == proof.root_hash
            
            # Start with leaf hash
            current_hash = proof.leaf_hash
            
            # Apply proof hashes
            for i, (proof_hash, is_right) in enumerate(zip(proof.proof_hashes, proof.proof_directions)):
                if is_right:
                    # Sibling is on the right
                    combined_data = f"{current_hash}:{proof_hash}"
                else:
                    # Sibling is on the left
                    combined_data = f"{proof_hash}:{current_hash}"
                
                current_hash = self._hash_internal(combined_data)
            
            # Check if we reached the root
            is_valid = current_hash == proof.root_hash
            
            self.verifications_performed += 1
            
            if is_valid:
                logger.debug(f"Merkle proof verified successfully")
            else:
                logger.warning(f"Merkle proof verification failed")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Failed to verify Merkle proof: {e}")
            return False
    
    async def _store_merkle_tree(self, tree: MerkleTree):
        """Store Merkle tree in database"""
        try:
            tree_doc = {
                "root_hash": tree.root.hash,
                "session_id": tree.session_id,
                "height": tree.height,
                "total_leaves": tree.total_leaves,
                "created_at": tree.created_at,
                "root_node": self._node_to_dict(tree.root),
                "leaves": [self._node_to_dict(leaf) for leaf in tree.leaves]
            }
            
            await self.db["merkle_trees"].insert_one(tree_doc)
            
            # Store individual nodes for large trees
            if tree.total_leaves > 100:
                await self._store_tree_nodes(tree.root.hash, tree.root, 0)
            
        except Exception as e:
            logger.error(f"Failed to store Merkle tree: {e}")
            raise
    
    async def _store_tree_nodes(self, tree_id: str, node: MerkleNode, level: int):
        """Store tree nodes recursively for large trees"""
        try:
            node_doc = {
                "tree_id": tree_id,
                "node_hash": node.hash,
                "level": level,
                "index": node.index,
                "is_leaf": node.is_leaf,
                "data": node.data,
                "left_hash": node.left.hash if node.left else None,
                "right_hash": node.right.hash if node.right else None
            }
            
            await self.db["merkle_nodes"].insert_one(node_doc)
            
            # Recursively store children
            if node.left:
                await self._store_tree_nodes(tree_id, node.left, level + 1)
            if node.right and node.right != node.left:  # Avoid duplicates
                await self._store_tree_nodes(tree_id, node.right, level + 1)
            
        except Exception as e:
            logger.error(f"Failed to store tree nodes: {e}")
    
    async def _store_merkle_proof(self, proof: MerkleProof):
        """Store Merkle proof in database"""
        try:
            proof_doc = {
                "root_hash": proof.root_hash,
                "leaf_hash": proof.leaf_hash,
                "leaf_index": proof.leaf_index,
                "proof_hashes": proof.proof_hashes,
                "proof_directions": proof.proof_directions,
                "created_at": datetime.now(timezone.utc)
            }
            
            await self.db["merkle_proofs"].insert_one(proof_doc)
            
        except Exception as e:
            logger.error(f"Failed to store Merkle proof: {e}")
    
    async def _get_merkle_tree(self, root_hash: str) -> Optional[MerkleTree]:
        """Get Merkle tree by root hash"""
        try:
            # Check cache first
            if root_hash in self.tree_cache:
                return self.tree_cache[root_hash]
            
            # Query database
            tree_doc = await self.db["merkle_trees"].find_one({"root_hash": root_hash})
            if tree_doc:
                tree = await self._doc_to_merkle_tree(tree_doc)
                if tree:
                    self.tree_cache[root_hash] = tree
                return tree
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get Merkle tree: {e}")
            return None
    
    async def _doc_to_merkle_tree(self, doc: Dict[str, Any]) -> Optional[MerkleTree]:
        """Convert MongoDB document to MerkleTree object"""
        try:
            # Reconstruct root node
            root = self._dict_to_node(doc["root_node"])
            
            # Reconstruct leaves
            leaves = [self._dict_to_node(leaf_doc) for leaf_doc in doc["leaves"]]
            
            return MerkleTree(
                root=root,
                leaves=leaves,
                height=doc["height"],
                total_leaves=doc["total_leaves"],
                session_id=doc.get("session_id"),
                created_at=doc["created_at"]
            )
            
        except Exception as e:
            logger.error(f"Failed to convert document to Merkle tree: {e}")
            return None
    
    def _node_to_dict(self, node: MerkleNode) -> Dict[str, Any]:
        """Convert MerkleNode to dictionary"""
        return {
            "hash": node.hash,
            "is_leaf": node.is_leaf,
            "data": node.data,
            "index": node.index,
            "left": self._node_to_dict(node.left) if node.left else None,
            "right": self._node_to_dict(node.right) if node.right else None
        }
    
    def _dict_to_node(self, doc: Dict[str, Any]) -> MerkleNode:
        """Convert dictionary to MerkleNode"""
        node = MerkleNode(
            hash=doc["hash"],
            is_leaf=doc["is_leaf"],
            data=doc.get("data"),
            index=doc["index"]
        )
        
        if doc.get("left"):
            node.left = self._dict_to_node(doc["left"])
        if doc.get("right"):
            node.right = self._dict_to_node(doc["right"])
        
        return node
    
    async def get_merkle_tree_info(self, root_hash: str) -> Optional[Dict[str, Any]]:
        """Get information about a Merkle tree"""
        try:
            tree = await self._get_merkle_tree(root_hash)
            if not tree:
                return None
            
            return {
                "root_hash": tree.root.hash,
                "session_id": tree.session_id,
                "height": tree.height,
                "total_leaves": tree.total_leaves,
                "created_at": tree.created_at.isoformat(),
                "leaf_hashes": [leaf.hash for leaf in tree.leaves]
            }
            
        except Exception as e:
            logger.error(f"Failed to get Merkle tree info: {e}")
            return None
    
    async def validate_session_integrity(self, session_id: str, chunks: List[ChunkMetadata]) -> Dict[str, Any]:
        """Validate the integrity of a session using its Merkle tree"""
        try:
            # Find the Merkle tree for this session
            tree_doc = await self.db["merkle_trees"].find_one({"session_id": session_id})
            if not tree_doc:
                return {"is_valid": False, "error": "Merkle tree not found"}
            
            # Rebuild tree from current chunks
            rebuilt_tree = await self.build_session_merkle_tree(f"{session_id}_validation", chunks)
            
            # Compare root hashes
            original_root = tree_doc["root_hash"]
            rebuilt_root = rebuilt_tree.root.hash
            
            is_valid = original_root == rebuilt_root
            
            return {
                "is_valid": is_valid,
                "original_root": original_root,
                "rebuilt_root": rebuilt_root,
                "session_id": session_id,
                "chunk_count": len(chunks),
                "validation_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to validate session integrity: {e}")
            return {"is_valid": False, "error": str(e)}
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get Merkle tree builder statistics"""
        try:
            total_trees = await self.db["merkle_trees"].count_documents({})
            total_proofs = await self.db["merkle_proofs"].count_documents({})
            
            return {
                "trees_built": self.trees_built,
                "proofs_generated": self.proofs_generated,
                "verifications_performed": self.verifications_performed,
                "total_trees_stored": total_trees,
                "total_proofs_stored": total_proofs,
                "trees_in_cache": len(self.tree_cache),
                "proofs_in_cache": len(self.proof_cache)
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {}
    
    async def cleanup_old_trees(self, days_old: int = 30):
        """Clean up old Merkle trees and proofs"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
            
            # Remove old trees
            trees_result = await self.db["merkle_trees"].delete_many({
                "created_at": {"$lt": cutoff_date}
            })
            
            # Remove old proofs
            proofs_result = await self.db["merkle_proofs"].delete_many({
                "created_at": {"$lt": cutoff_date}
            })
            
            # Remove old nodes
            nodes_result = await self.db["merkle_nodes"].delete_many({
                "tree_id": {"$in": []}  # This would be populated with old tree IDs
            })
            
            logger.info(f"Cleaned up {trees_result.deleted_count} trees, {proofs_result.deleted_count} proofs")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old trees: {e}")
