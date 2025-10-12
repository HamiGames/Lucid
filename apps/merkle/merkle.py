#!/usr/bin/env python3
"""
Lucid RDP Merkle Tree Builder with BLAKE3
High-performance Merkle tree construction for data integrity verification
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog
from datetime import datetime

logger = structlog.get_logger(__name__)

try:
    import blake3
    BLAKE3_AVAILABLE = True
    logger.info("BLAKE3 library loaded successfully")
except ImportError:
    logger.warning("BLAKE3 not available, using SHA-256 fallback")
    BLAKE3_AVAILABLE = False

try:
    import hashlib
    HASHLIB_AVAILABLE = True
except ImportError:
    HASHLIB_AVAILABLE = False
    logger.error("hashlib not available")


class HashAlgorithm(Enum):
    """Supported hash algorithms"""
    BLAKE3 = "blake3"
    SHA256 = "sha256"
    SHA512 = "sha512"
    SHA3_256 = "sha3-256"
    SHA3_512 = "sha3-512"


@dataclass
class MerkleNode:
    """Merkle tree node"""
    hash_value: str
    left_child: Optional['MerkleNode'] = None
    right_child: Optional['MerkleNode'] = None
    data: Optional[bytes] = None
    is_leaf: bool = False
    index: int = -1


@dataclass
class MerkleProof:
    """Merkle proof for data verification"""
    leaf_hash: str
    path: List[Tuple[str, bool]]  # (hash, is_left)
    root_hash: str
    leaf_index: int
    tree_size: int


class MerkleBuilder:
    """High-performance Merkle tree builder"""
    
    def __init__(self, algorithm: HashAlgorithm = HashAlgorithm.BLAKE3):
        self.algorithm = algorithm
        self.leaves: List[MerkleNode] = []
        self.tree: List[List[MerkleNode]] = []
        self.root_hash: Optional[str] = None
        self.is_finalized = False
        
        # Statistics
        self.stats = {
            'leaves_added': 0,
            'total_bytes': 0,
            'tree_levels': 0,
            'build_time': 0.0,
            'blake3_calls': 0,
            'fallback_calls': 0,
            'errors': 0
        }
    
    async def add_data(self, data: bytes) -> str:
        """Add data to the Merkle tree and return its hash"""
        try:
            # Hash the data
            data_hash = await self._hash_data(data)
            
            # Create leaf node
            leaf_node = MerkleNode(
                hash_value=data_hash,
                data=data,
                is_leaf=True,
                index=len(self.leaves)
            )
            
            # Add to leaves
            self.leaves.append(leaf_node)
            self.stats['leaves_added'] += 1
            self.stats['total_bytes'] += len(data)
            
            logger.debug("Added data to Merkle tree", 
                        index=leaf_node.index,
                        hash=data_hash[:16] + "...",
                        size=len(data))
            
            return data_hash
            
        except Exception as e:
            logger.error("Failed to add data to Merkle tree", error=str(e))
            self.stats['errors'] += 1
            return ""
    
    async def _hash_data(self, data: bytes) -> str:
        """Hash data using the specified algorithm"""
        try:
            if self.algorithm == HashAlgorithm.BLAKE3 and BLAKE3_AVAILABLE:
                # Use BLAKE3 for fast hashing
                hasher = blake3.blake3()
                hasher.update(data)
                hash_bytes = hasher.digest()
                self.stats['blake3_calls'] += 1
                return hash_bytes.hex()
            else:
                # Fallback to hashlib
                if self.algorithm == HashAlgorithm.SHA256:
                    hash_bytes = hashlib.sha256(data).digest()
                elif self.algorithm == HashAlgorithm.SHA512:
                    hash_bytes = hashlib.sha512(data).digest()
                elif self.algorithm == HashAlgorithm.SHA3_256:
                    hash_bytes = hashlib.sha3_256(data).digest()
                elif self.algorithm == HashAlgorithm.SHA3_512:
                    hash_bytes = hashlib.sha3_512(data).digest()
                else:
                    hash_bytes = hashlib.sha256(data).digest()  # Default fallback
                
                self.stats['fallback_calls'] += 1
                return hash_bytes.hex()
                
        except Exception as e:
            logger.error("Failed to hash data", error=str(e))
            self.stats['errors'] += 1
            return ""
    
    async def _hash_pair(self, left_hash: str, right_hash: str) -> str:
        """Hash a pair of hashes"""
        try:
            combined = left_hash + right_hash
            
            if self.algorithm == HashAlgorithm.BLAKE3 and BLAKE3_AVAILABLE:
                hasher = blake3.blake3()
                hasher.update(combined.encode())
                hash_bytes = hasher.digest()
                self.stats['blake3_calls'] += 1
                return hash_bytes.hex()
            else:
                # Fallback to hashlib
                if self.algorithm == HashAlgorithm.SHA256:
                    hash_bytes = hashlib.sha256(combined.encode()).digest()
                elif self.algorithm == HashAlgorithm.SHA512:
                    hash_bytes = hashlib.sha512(combined.encode()).digest()
                elif self.algorithm == HashAlgorithm.SHA3_256:
                    hash_bytes = hashlib.sha3_256(combined.encode()).digest()
                elif self.algorithm == HashAlgorithm.SHA3_512:
                    hash_bytes = hashlib.sha3_512(combined.encode()).digest()
                else:
                    hash_bytes = hashlib.sha256(combined.encode()).digest()
                
                self.stats['fallback_calls'] += 1
                return hash_bytes.hex()
                
        except Exception as e:
            logger.error("Failed to hash pair", error=str(e))
            self.stats['errors'] += 1
            return ""
    
    async def build_tree(self) -> Optional[str]:
        """Build the Merkle tree and return root hash"""
        try:
            if not self.leaves:
                logger.warning("No leaves to build tree")
                return None
            
            logger.info("Building Merkle tree", 
                       leaf_count=len(self.leaves),
                       algorithm=self.algorithm.value)
            
            start_time = time.time()
            
            # Start with leaf level
            current_level = self.leaves.copy()
            self.tree = [current_level]
            level = 0
            
            # Build tree levels
            while len(current_level) > 1:
                next_level = []
                
                # Process pairs of nodes
                for i in range(0, len(current_level), 2):
                    if i + 1 < len(current_level):
                        # Combine two nodes
                        left_node = current_level[i]
                        right_node = current_level[i + 1]
                        
                        parent_hash = await self._hash_pair(
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
                        
                        logger.debug("Created parent node", 
                                   level=level,
                                   index=i // 2,
                                   hash=parent_hash[:16] + "...")
                    else:
                        # Odd number of nodes, promote the last one
                        next_level.append(current_level[i])
                        
                        logger.debug("Promoted node", 
                                   level=level,
                                   index=i // 2,
                                   hash=current_level[i].hash_value[:16] + "...")
                
                current_level = next_level
                self.tree.append(current_level)
                level += 1
            
            # Root hash is the single node at the top level
            if current_level:
                self.root_hash = current_level[0].hash_value
                self.stats['tree_levels'] = len(self.tree)
                self.stats['build_time'] = time.time() - start_time
                
                logger.info("Merkle tree built successfully", 
                           root_hash=self.root_hash[:16] + "...",
                           levels=self.stats['tree_levels'],
                           build_time=self.stats['build_time'])
                
                return self.root_hash
            
            return None
            
        except Exception as e:
            logger.error("Failed to build Merkle tree", error=str(e))
            self.stats['errors'] += 1
            return None
    
    async def finalize(self) -> Optional[str]:
        """Finalize the Merkle tree and return root hash"""
        try:
            if self.is_finalized:
                return self.root_hash
            
            # Build the tree
            root_hash = await self.build_tree()
            
            if root_hash:
                self.is_finalized = True
                logger.info("Merkle tree finalized", 
                           root_hash=root_hash[:16] + "...",
                           leaves=self.stats['leaves_added'],
                           total_bytes=self.stats['total_bytes'])
            
            return root_hash
            
        except Exception as e:
            logger.error("Failed to finalize Merkle tree", error=str(e))
            self.stats['errors'] += 1
            return None
    
    async def generate_proof(self, leaf_index: int) -> Optional[MerkleProof]:
        """Generate a Merkle proof for a leaf"""
        try:
            if not self.is_finalized or leaf_index >= len(self.leaves):
                logger.error("Invalid leaf index for proof generation")
                return None
            
            proof_path = []
            current_index = leaf_index
            
            # Walk up the tree to build the proof
            for level in range(len(self.tree) - 1):
                sibling_index = current_index ^ 1  # XOR to get sibling index
                
                if sibling_index < len(self.tree[level]):
                    is_left = sibling_index < current_index
                    proof_path.append((self.tree[level][sibling_index].hash_value, is_left))
                
                current_index //= 2
            
            # Create proof
            proof = MerkleProof(
                leaf_hash=self.leaves[leaf_index].hash_value,
                path=proof_path,
                root_hash=self.root_hash,
                leaf_index=leaf_index,
                tree_size=len(self.leaves)
            )
            
            logger.debug("Generated Merkle proof", 
                        leaf_index=leaf_index,
                        path_length=len(proof_path))
            
            return proof
            
        except Exception as e:
            logger.error("Failed to generate Merkle proof", leaf_index=leaf_index, error=str(e))
            self.stats['errors'] += 1
            return None
    
    async def verify_proof(self, proof: MerkleProof) -> bool:
        """Verify a Merkle proof"""
        try:
            if not proof:
                return False
            
            # Start with leaf hash
            current_hash = proof.leaf_hash
            
            # Walk up the proof path
            for sibling_hash, is_left in proof.path:
                if is_left:
                    # Current hash is right child
                    current_hash = await self._hash_pair(sibling_hash, current_hash)
                else:
                    # Current hash is left child
                    current_hash = await self._hash_pair(current_hash, sibling_hash)
            
            # Check if we reached the root hash
            is_valid = current_hash == proof.root_hash
            
            logger.debug("Merkle proof verification", 
                        leaf_index=proof.leaf_index,
                        is_valid=is_valid)
            
            return is_valid
            
        except Exception as e:
            logger.error("Failed to verify Merkle proof", error=str(e))
            self.stats['errors'] += 1
            return False
    
    async def verify_data(self, data: bytes, proof: MerkleProof) -> bool:
        """Verify data against a Merkle proof"""
        try:
            # Hash the data
            data_hash = await self._hash_data(data)
            
            # Check if hash matches proof leaf hash
            if data_hash != proof.leaf_hash:
                return False
            
            # Verify the proof
            return await self.verify_proof(proof)
            
        except Exception as e:
            logger.error("Failed to verify data", error=str(e))
            self.stats['errors'] += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get Merkle tree statistics"""
        return {
            **self.stats,
            'algorithm': self.algorithm.value,
            'blake3_available': BLAKE3_AVAILABLE,
            'tree_levels': len(self.tree),
            'root_hash': self.root_hash,
            'is_finalized': self.is_finalized
        }
    
    async def cleanup(self):
        """Cleanup Merkle tree resources"""
        try:
            # Clear all data
            self.leaves.clear()
            self.tree.clear()
            self.root_hash = None
            self.is_finalized = False
            
            # Reset statistics
            self.stats = {
                'leaves_added': 0,
                'total_bytes': 0,
                'tree_levels': 0,
                'build_time': 0.0,
                'blake3_calls': 0,
                'fallback_calls': 0,
                'errors': 0
            }
            
            logger.info("Merkle tree cleanup completed")
            
        except Exception as e:
            logger.error("Merkle tree cleanup error", error=str(e))


class MerkleService:
    """Service for managing multiple Merkle trees"""
    
    def __init__(self):
        self.trees: Dict[str, MerkleBuilder] = {}
        self.is_running = False
    
    async def start(self):
        """Start the Merkle service"""
        self.is_running = True
        logger.info("Merkle service started")
    
    async def stop(self):
        """Stop the Merkle service"""
        self.is_running = False
        
        # Cleanup all trees
        for tree in self.trees.values():
            await tree.cleanup()
        
        self.trees.clear()
        logger.info("Merkle service stopped")
    
    async def create_tree(self, tree_id: str, algorithm: HashAlgorithm = HashAlgorithm.BLAKE3) -> MerkleBuilder:
        """Create a new Merkle tree"""
        try:
            if tree_id in self.trees:
                logger.warning("Tree already exists", tree_id=tree_id)
                return self.trees[tree_id]
            
            # Create tree
            tree = MerkleBuilder(algorithm=algorithm)
            self.trees[tree_id] = tree
            
            logger.info("Created Merkle tree", tree_id=tree_id, algorithm=algorithm.value)
            return tree
            
        except Exception as e:
            logger.error("Failed to create Merkle tree", tree_id=tree_id, error=str(e))
            return None
    
    async def get_tree(self, tree_id: str) -> Optional[MerkleBuilder]:
        """Get Merkle tree by ID"""
        return self.trees.get(tree_id)
    
    async def remove_tree(self, tree_id: str):
        """Remove Merkle tree"""
        try:
            if tree_id in self.trees:
                tree = self.trees[tree_id]
                await tree.cleanup()
                del self.trees[tree_id]
                logger.info("Removed Merkle tree", tree_id=tree_id)
        except Exception as e:
            logger.error("Failed to remove Merkle tree", tree_id=tree_id, error=str(e))
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service-wide statistics"""
        stats = {
            'is_running': self.is_running,
            'active_trees': len(self.trees),
            'tree_ids': list(self.trees.keys()),
            'blake3_available': BLAKE3_AVAILABLE
        }
        
        # Aggregate tree stats
        total_stats = {
            'leaves_added': 0,
            'total_bytes': 0,
            'tree_levels': 0,
            'build_time': 0.0,
            'blake3_calls': 0,
            'fallback_calls': 0,
            'errors': 0
        }
        
        for tree in self.trees.values():
            tree_stats = tree.get_stats()
            for key in total_stats:
                if key in tree_stats:
                    total_stats[key] += tree_stats[key]
        
        stats['aggregate_stats'] = total_stats
        return stats


async def main():
    """Main entry point for Merkle service"""
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Create and start service
    service = MerkleService()
    
    try:
        await service.start()
        
        # Keep running
        logger.info("Merkle service running")
        while service.is_running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
