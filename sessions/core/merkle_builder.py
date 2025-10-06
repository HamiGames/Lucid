#!/usr/bin/env python3
"""
LUCID Merkle Tree Builder - SPEC-1B Implementation
BLAKE3 Merkle tree construction for session integrity
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict
    import blake3

logger = logging.getLogger(__name__)

@dataclass
class MerkleNode:
    """Merkle tree node structure"""
    hash_value: bytes
    left_child: Optional['MerkleNode'] = None
    right_child: Optional['MerkleNode'] = None
    is_leaf: bool = False
    data_hash: Optional[bytes] = None

@dataclass
class MerkleRoot:
    """Merkle tree root with proof generation capability"""
    root_hash: bytes
    tree_depth: int
    leaf_count: int
    total_nodes: int
    timestamp: float
    session_id: str

@dataclass
class MerkleProof:
    """Merkle proof for a specific leaf"""
    leaf_hash: bytes
    proof_path: List[bytes]
    leaf_index: int
    root_hash: bytes

class MerkleTreeBuilder:
    """
    BLAKE3 Merkle tree construction per SPEC-1b
    """
    
    HASH_ALGORITHM = "BLAKE3"
    
    def __init__(self, output_dir: str = "/data/merkle_roots"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("MerkleTreeBuilder initialized with BLAKE3 hashing")
    
    def _hash_data(self, data: bytes) -> bytes:
        """Hash data using BLAKE3"""
        return blake3.blake3(data).digest()
    
    def _hash_concatenated(self, left_hash: bytes, right_hash: bytes) -> bytes:
        """Hash concatenated left and right hashes"""
        combined = left_hash + right_hash
        return self._hash_data(combined)
    
    async def build_session_merkle_tree(
        self, 
        encrypted_chunks: List[Tuple[str, bytes]], 
        session_id: str
    ) -> MerkleRoot:
        """
        Build BLAKE3-based Merkle tree for session integrity
        
        Args:
            encrypted_chunks: List of (chunk_id, encrypted_data) tuples
            session_id: Session identifier
            
        Returns:
            MerkleRoot object with tree metadata
        """
        if not encrypted_chunks:
            raise ValueError("Cannot build Merkle tree with empty chunk list")
        
        logger.info(f"Building Merkle tree for session {session_id} with {len(encrypted_chunks)} chunks")
        
        # Create leaf nodes
        leaf_nodes = []
        for chunk_id, chunk_data in encrypted_chunks:
            # Hash the chunk data
            chunk_hash = self._hash_data(chunk_data)
            
            # Create leaf node
            leaf_node = MerkleNode(
                hash_value=chunk_hash,
                is_leaf=True,
                data_hash=chunk_hash
            )
            leaf_nodes.append(leaf_node)
        
        # Build tree bottom-up
        current_level = leaf_nodes
        tree_depth = 0
        
        while len(current_level) > 1:
            next_level = []
            
            # Process pairs of nodes
            for i in range(0, len(current_level), 2):
                left_node = current_level[i]
                right_node = current_level[i + 1] if i + 1 < len(current_level) else left_node
                
                # Create parent node
                parent_hash = self._hash_concatenated(
                    left_node.hash_value, 
                    right_node.hash_value
                )
                
                parent_node = MerkleNode(
                    hash_value=parent_hash,
                    left_child=left_node,
                    right_child=right_node,
                    is_leaf=False
                )
                
                next_level.append(parent_node)
            
            current_level = next_level
            tree_depth += 1
        
        # Root node is the only remaining node
        root_node = current_level[0]
        
        # Create MerkleRoot object
        merkle_root = MerkleRoot(
            root_hash=root_node.hash_value,
            tree_depth=tree_depth,
            leaf_count=len(leaf_nodes),
            total_nodes=len(leaf_nodes) + tree_depth,
            timestamp=time.time(),
            session_id=session_id
        )
        
        # Save Merkle root to disk
        await self._save_merkle_root(merkle_root)
        
        logger.info(f"Merkle tree built: depth={tree_depth}, leaves={len(leaf_nodes)}, root={merkle_root.root_hash.hex()[:16]}...")
        
        return merkle_root
    
    async def generate_merkle_proof(
        self, 
        merkle_root: MerkleRoot, 
        chunk_index: int,
        encrypted_chunks: List[Tuple[str, bytes]]
    ) -> MerkleProof:
        """
        Generate Merkle proof for a specific chunk
        
        Args:
            merkle_root: MerkleRoot object
            chunk_index: Index of the chunk to prove
            encrypted_chunks: Original chunk data for verification
            
        Returns:
            MerkleProof object
        """
        if chunk_index >= len(encrypted_chunks):
            raise ValueError(f"Chunk index {chunk_index} out of range")
        
        # Rebuild the tree to get proof path
        leaf_nodes = []
        for chunk_id, chunk_data in encrypted_chunks:
            chunk_hash = self._hash_data(chunk_data)
            leaf_node = MerkleNode(hash_value=chunk_hash, is_leaf=True)
            leaf_nodes.append(leaf_node)
        
        # Build tree and collect proof path
        current_level = leaf_nodes
        proof_path = []
        current_index = chunk_index
        
        while len(current_level) > 1:
            next_level = []
            
            for i in range(0, len(current_level), 2):
                left_node = current_level[i]
                right_node = current_level[i + 1] if i + 1 < len(current_level) else left_node
                
                # Add sibling to proof path if current node is in this pair
                if current_index == i:
                    proof_path.append(right_node.hash_value)
                elif current_index == i + 1:
                    proof_path.append(left_node.hash_value)
                
                # Create parent
                parent_hash = self._hash_concatenated(
                    left_node.hash_value, 
                    right_node.hash_value
                )
                
                parent_node = MerkleNode(
                    hash_value=parent_hash,
                    left_child=left_node,
                    right_child=right_node
                )
                
                next_level.append(parent_node)
            
            current_level = next_level
            current_index //= 2
        
        # Create proof
        target_leaf_hash = leaf_nodes[chunk_index].hash_value
        
        proof = MerkleProof(
            leaf_hash=target_leaf_hash,
            proof_path=proof_path,
            leaf_index=chunk_index,
            root_hash=merkle_root.root_hash
        )
        
        logger.debug(f"Generated Merkle proof for chunk {chunk_index}")
        return proof
    
    def verify_merkle_proof(self, proof: MerkleProof) -> bool:
        """
        Verify a Merkle proof
        
        Args:
            proof: MerkleProof object to verify
            
        Returns:
            True if proof is valid, False otherwise
        """
        current_hash = proof.leaf_hash
        
        # Reconstruct root hash using proof path
        for sibling_hash in proof.proof_path:
            if proof.leaf_index % 2 == 0:
                # Current node is left child
                current_hash = self._hash_concatenated(current_hash, sibling_hash)
                else:
                # Current node is right child
                current_hash = self._hash_concatenated(sibling_hash, current_hash)
            
            proof.leaf_index //= 2
        
        # Verify against root hash
        is_valid = current_hash == proof.root_hash
        
        logger.debug(f"Merkle proof verification: {'PASS' if is_valid else 'FAIL'}")
        return is_valid
    
    async def _save_merkle_root(self, merkle_root: MerkleRoot):
        """Save Merkle root metadata to disk"""
        
        root_filename = f"{merkle_root.session_id}_merkle_root.json"
        root_path = self.output_dir / root_filename
        
        import json
        
        root_data = {
            "session_id": merkle_root.session_id,
            "root_hash": merkle_root.root_hash.hex(),
            "tree_depth": merkle_root.tree_depth,
            "leaf_count": merkle_root.leaf_count,
            "total_nodes": merkle_root.total_nodes,
            "timestamp": merkle_root.timestamp
        }
        
        with open(root_path, 'w') as f:
            json.dump(root_data, f, indent=2)
        
        logger.debug(f"Saved Merkle root to {root_path}")
    
    async def load_merkle_root(self, session_id: str) -> Optional[MerkleRoot]:
        """Load Merkle root from disk"""
        
        root_filename = f"{session_id}_merkle_root.json"
        root_path = self.output_dir / root_filename
        
        if not root_path.exists():
            return None
        
        import json
        
        with open(root_path, 'r') as f:
            root_data = json.load(f)
        
        merkle_root = MerkleRoot(
            root_hash=bytes.fromhex(root_data["root_hash"]),
            tree_depth=root_data["tree_depth"],
            leaf_count=root_data["leaf_count"],
            total_nodes=root_data["total_nodes"],
            timestamp=root_data["timestamp"],
            session_id=root_data["session_id"]
        )
        
        logger.debug(f"Loaded Merkle root for session {session_id}")
        return merkle_root
    
    def get_merkle_stats(self, session_id: str) -> dict:
        """Get Merkle tree statistics for a session"""
        
        root_filename = f"{session_id}_merkle_root.json"
        root_path = self.output_dir / root_filename
        
        if not root_path.exists():
            return {
                "session_id": session_id,
                "has_merkle_root": False
            }
        
        import json
        
        with open(root_path, 'r') as f:
            root_data = json.load(f)
        
        return {
            "session_id": session_id,
            "has_merkle_root": True,
            "tree_depth": root_data["tree_depth"],
            "leaf_count": root_data["leaf_count"],
            "total_nodes": root_data["total_nodes"],
            "root_hash": root_data["root_hash"][:16] + "..."
        }
    
    async def cleanup_session_merkle_root(self, session_id: str) -> bool:
        """Clean up Merkle root for a session"""
        
        root_filename = f"{session_id}_merkle_root.json"
        root_path = self.output_dir / root_filename
        
        if root_path.exists():
            try:
                root_path.unlink()
                logger.info(f"Cleaned up Merkle root for session {session_id}")
                return True
            except OSError as e:
                logger.error(f"Failed to remove Merkle root {root_path}: {e}")
        return False
    
        return True

# CLI interface for testing
async def main():
    """Test the Merkle builder with sample data"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LUCID Merkle Tree Builder")
    parser.add_argument("--session-id", required=True, help="Session ID")
    parser.add_argument("--input-dir", required=True, help="Directory containing encrypted chunks")
    parser.add_argument("--output-dir", default="/data/merkle_roots", help="Output directory")
    parser.add_argument("--verify-proof", type=int, help="Verify proof for chunk index")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create Merkle builder
    builder = MerkleTreeBuilder(args.output_dir)
    
    # Load encrypted chunks
    input_path = Path(args.input_dir)
    chunk_files = list(input_path.glob("*.enc"))
    
    if not chunk_files:
        print("No encrypted chunk files found")
        return
    
    # Read chunk data
    encrypted_chunks = []
    for chunk_file in sorted(chunk_files):
        with open(chunk_file, 'rb') as f:
            chunk_data = f.read()
        chunk_id = chunk_file.stem
        encrypted_chunks.append((chunk_id, chunk_data))
    
    # Build Merkle tree
    merkle_root = await builder.build_session_merkle_tree(
        encrypted_chunks, args.session_id
    )
    
    print(f"Built Merkle tree:")
    print(f"  Root hash: {merkle_root.root_hash.hex()}")
    print(f"  Tree depth: {merkle_root.tree_depth}")
    print(f"  Leaf count: {merkle_root.leaf_count}")
    
    # Test proof generation and verification
    if args.verify_proof is not None:
        proof = await builder.generate_merkle_proof(
            merkle_root, args.verify_proof, encrypted_chunks
        )
        
        is_valid = builder.verify_merkle_proof(proof)
        print(f"Proof for chunk {args.verify_proof}: {'VALID' if is_valid else 'INVALID'}")

if __name__ == "__main__":
    asyncio.run(main())