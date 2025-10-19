#!/usr/bin/env python3
"""
LUCID Blockchain Consensus Engine - SPEC-1B Implementation
Proof-of-Observation-Time (PoOT) consensus mechanism
"""

import asyncio
import logging
import time
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BlockStatus(Enum):
    """Block validation status"""
    PENDING = "pending"
    VALIDATED = "validated"
    REJECTED = "rejected"
    ANCHORED = "anchored"

class ConsensusState(Enum):
    """Consensus mechanism state"""
    IDLE = "idle"
    COLLECTING = "collecting"
    VALIDATING = "validating"
    COMMITTING = "committing"

@dataclass
class PoOTProof:
    """Proof-of-Observation-Time proof data"""
    node_id: str
    session_id: str
    observation_time: float
    work_credits: float
    merkle_root: str
    proof_hash: str
    timestamp: datetime
    signature: Optional[str] = None

@dataclass
class BlockCandidate:
    """Block candidate for consensus"""
    block_id: str
    height: int
    previous_hash: str
    merkle_root: str
    timestamp: datetime
    proofs: List[PoOTProof]
    proposer_node: str
    block_hash: str
    status: BlockStatus = BlockStatus.PENDING

@dataclass
class ConsensusConfig:
    """Consensus engine configuration"""
    block_time_seconds: int = 10
    min_proofs_per_block: int = 3
    max_proofs_per_block: int = 100
    consensus_threshold: float = 0.67  # 67% consensus required
    max_block_size_mb: int = 1
    observation_time_weight: float = 0.4
    work_credits_weight: float = 0.6
    validator_timeout_seconds: int = 30

class ConsensusEngine:
    """
    LUCID Blockchain Consensus Engine
    
    Implements Proof-of-Observation-Time (PoOT) consensus:
    1. Nodes submit observation proofs
    2. Proofs are collected and validated
    3. Block candidates are proposed
    4. Consensus is reached through proof validation
    5. Valid blocks are committed to blockchain
    """
    
    def __init__(self, config: ConsensusConfig):
        self.config = config
        self.state = ConsensusState.IDLE
        self.current_height = 0
        self.pending_proofs: Dict[str, PoOTProof] = {}
        self.block_candidates: List[BlockCandidate] = []
        self.validated_blocks: List[BlockCandidate] = []
        self.validator_nodes: Dict[str, Dict[str, Any]] = {}
        self.consensus_round = 0
        self.last_block_time = datetime.utcnow()
        
    async def start_consensus(self) -> bool:
        """
        Start consensus mechanism
        
        Returns:
            success: True if consensus started successfully
        """
        try:
            logger.info("Starting consensus engine")
            
            self.state = ConsensusState.IDLE
            self.consensus_round = 0
            
            # Start consensus loop
            asyncio.create_task(self._consensus_loop())
            
            logger.info("Consensus engine started successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start consensus engine: {e}")
            return False
    
    async def submit_proof(self, proof: PoOTProof) -> bool:
        """
        Submit PoOT proof for consensus
        
        Args:
            proof: Proof-of-Observation-Time proof
            
        Returns:
            success: True if proof submitted successfully
        """
        try:
            # Validate proof
            if not await self._validate_proof(proof):
                logger.warning(f"Invalid proof submitted by node {proof.node_id}")
                return False
            
            # Store proof
            proof_key = f"{proof.node_id}:{proof.session_id}:{int(proof.timestamp.timestamp())}"
            self.pending_proofs[proof_key] = proof
            
            logger.info(f"Proof submitted by node {proof.node_id} for session {proof.session_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit proof: {e}")
            return False
    
    async def _validate_proof(self, proof: PoOTProof) -> bool:
        """
        Validate PoOT proof
        
        Args:
            proof: Proof to validate
            
        Returns:
            valid: True if proof is valid
        """
        try:
            # Check observation time
            if proof.observation_time <= 0:
                logger.warning(f"Invalid observation time: {proof.observation_time}")
                return False
            
            # Check work credits
            if proof.work_credits <= 0:
                logger.warning(f"Invalid work credits: {proof.work_credits}")
                return False
            
            # Validate merkle root format
            if len(proof.merkle_root) != 64:  # SHA256 hex length
                logger.warning(f"Invalid merkle root format: {proof.merkle_root}")
                return False
            
            # Verify proof hash
            expected_hash = self._calculate_proof_hash(proof)
            if proof.proof_hash != expected_hash:
                logger.warning(f"Proof hash mismatch: {proof.proof_hash} != {expected_hash}")
                return False
            
            # Check timestamp (not too old)
            age_seconds = (datetime.utcnow() - proof.timestamp).total_seconds()
            if age_seconds > self.config.validator_timeout_seconds:
                logger.warning(f"Proof too old: {age_seconds} seconds")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Proof validation failed: {e}")
            return False
    
    async def _consensus_loop(self):
        """Main consensus loop"""
        while True:
            try:
                await self._consensus_round()
                await asyncio.sleep(self.config.block_time_seconds)
                
            except Exception as e:
                logger.error(f"Consensus loop error: {e}")
                await asyncio.sleep(5)  # Wait before retry
    
    async def _consensus_round(self):
        """Execute one consensus round"""
        try:
            current_time = datetime.utcnow()
            
            # Check if we have enough proofs for a block
            if len(self.pending_proofs) >= self.config.min_proofs_per_block:
                
                # Transition to collecting state
                self.state = ConsensusState.COLLECTING
                
                # Collect proofs for block
                block_proofs = await self._collect_proofs_for_block()
                
                if len(block_proofs) > 0:
                    # Create block candidate
                    block_candidate = await self._create_block_candidate(block_proofs)
                    
                    # Validate block candidate
                    if await self._validate_block_candidate(block_candidate):
                        
                        # Transition to validating state
                        self.state = ConsensusState.VALIDATING
                        
                        # Reach consensus
                        consensus_reached = await self._reach_consensus(block_candidate)
                        
                        if consensus_reached:
                            # Transition to committing state
                            self.state = ConsensusState.COMMITTING
                            
                            # Commit block
                            await self._commit_block(block_candidate)
                            
                            # Update state
                            self.current_height += 1
                            self.last_block_time = current_time
                            self.consensus_round += 1
                            
                            logger.info(f"Block {block_candidate.height} committed successfully")
                        
                        # Clean up used proofs
                        await self._cleanup_used_proofs(block_proofs)
                    
                    else:
                        logger.warning("Block candidate validation failed")
                
                else:
                    logger.info("No valid proofs collected for block")
            
            else:
                logger.debug(f"Not enough proofs for block: {len(self.pending_proofs)}/{self.config.min_proofs_per_block}")
            
            # Return to idle state
            self.state = ConsensusState.IDLE
            
        except Exception as e:
            logger.error(f"Consensus round failed: {e}")
            self.state = ConsensusState.IDLE
    
    async def _collect_proofs_for_block(self) -> List[PoOTProof]:
        """Collect proofs for current block"""
        try:
            # Sort proofs by work credits and observation time
            sorted_proofs = sorted(
                self.pending_proofs.values(),
                key=lambda p: (p.work_credits * self.config.work_credits_weight + 
                              p.observation_time * self.config.observation_time_weight),
                reverse=True
            )
            
            # Take up to max_proofs_per_block
            selected_proofs = sorted_proofs[:self.config.max_proofs_per_block]
            
            logger.info(f"Collected {len(selected_proofs)} proofs for block")
            
            return selected_proofs
            
        except Exception as e:
            logger.error(f"Failed to collect proofs: {e}")
            return []
    
    async def _create_block_candidate(self, proofs: List[PoOTProof]) -> BlockCandidate:
        """Create block candidate from proofs"""
        try:
            # Calculate block hash
            previous_hash = self.validated_blocks[-1].block_hash if self.validated_blocks else "0" * 64
            merkle_root = self._calculate_block_merkle_root(proofs)
            timestamp = datetime.utcnow()
            
            # Create block data
            block_data = {
                "height": self.current_height + 1,
                "previous_hash": previous_hash,
                "merkle_root": merkle_root,
                "timestamp": timestamp.isoformat(),
                "proofs": [asdict(proof) for proof in proofs],
                "proposer_node": proofs[0].node_id if proofs else "unknown"
            }
            
            # Calculate block hash
            block_hash = self._calculate_block_hash(block_data)
            
            block_candidate = BlockCandidate(
                block_id=f"block_{self.current_height + 1}_{int(timestamp.timestamp())}",
                height=self.current_height + 1,
                previous_hash=previous_hash,
                merkle_root=merkle_root,
                timestamp=timestamp,
                proofs=proofs,
                proposer_node=proofs[0].node_id if proofs else "unknown",
                block_hash=block_hash
            )
            
            logger.info(f"Created block candidate {block_candidate.block_id} with {len(proofs)} proofs")
            
            return block_candidate
            
        except Exception as e:
            logger.error(f"Failed to create block candidate: {e}")
            raise
    
    async def _validate_block_candidate(self, block_candidate: BlockCandidate) -> bool:
        """Validate block candidate"""
        try:
            # Check block size
            block_size = len(json.dumps(asdict(block_candidate), default=str).encode())
            if block_size > self.config.max_block_size_mb * 1024 * 1024:
                logger.warning(f"Block size too large: {block_size} bytes")
                return False
            
            # Validate proofs in block
            for proof in block_candidate.proofs:
                if not await self._validate_proof(proof):
                    logger.warning(f"Invalid proof in block candidate: {proof.node_id}")
                    return False
            
            # Validate merkle root
            expected_merkle_root = self._calculate_block_merkle_root(block_candidate.proofs)
            if block_candidate.merkle_root != expected_merkle_root:
                logger.warning(f"Merkle root mismatch: {block_candidate.merkle_root} != {expected_merkle_root}")
                return False
            
            # Validate block hash
            expected_hash = self._calculate_block_hash(asdict(block_candidate))
            if block_candidate.block_hash != expected_hash:
                logger.warning(f"Block hash mismatch: {block_candidate.block_hash} != {expected_hash}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Block candidate validation failed: {e}")
            return False
    
    async def _reach_consensus(self, block_candidate: BlockCandidate) -> bool:
        """Reach consensus on block candidate"""
        try:
            # For PoOT consensus, we validate based on proof quality
            total_work_credits = sum(proof.work_credits for proof in block_candidate.proofs)
            total_observation_time = sum(proof.observation_time for proof in block_candidate.proofs)
            
            # Calculate consensus score
            consensus_score = (
                total_work_credits * self.config.work_credits_weight +
                total_observation_time * self.config.observation_time_weight
            )
            
            # Normalize score (simplified consensus mechanism)
            max_possible_score = (
                self.config.max_proofs_per_block * 100 * self.config.work_credits_weight +
                self.config.max_proofs_per_block * 3600 * self.config.observation_time_weight  # 1 hour max
            )
            
            normalized_score = consensus_score / max_possible_score if max_possible_score > 0 else 0
            
            consensus_reached = normalized_score >= self.config.consensus_threshold
            
            logger.info(f"Consensus score: {normalized_score:.3f}, threshold: {self.config.consensus_threshold}, reached: {consensus_reached}")
            
            return consensus_reached
            
        except Exception as e:
            logger.error(f"Consensus mechanism failed: {e}")
            return False
    
    async def _commit_block(self, block_candidate: BlockCandidate):
        """Commit validated block to blockchain"""
        try:
            # Mark block as validated and anchored
            block_candidate.status = BlockStatus.ANCHORED
            
            # Add to validated blocks
            self.validated_blocks.append(block_candidate)
            
            # Store in persistent storage (placeholder)
            await self._persist_block(block_candidate)
            
            logger.info(f"Block {block_candidate.height} committed to blockchain")
            
        except Exception as e:
            logger.error(f"Failed to commit block: {e}")
            raise
    
    async def _persist_block(self, block_candidate: BlockCandidate):
        """Persist block to storage (placeholder for database integration)"""
        # This would integrate with the blockchain storage service
        logger.debug(f"Persisting block {block_candidate.block_id} to storage")
        pass
    
    async def _cleanup_used_proofs(self, used_proofs: List[PoOTProof]):
        """Clean up proofs that were used in committed block"""
        try:
            # Remove used proofs from pending
            for proof in used_proofs:
                proof_key = f"{proof.node_id}:{proof.session_id}:{int(proof.timestamp.timestamp())}"
                if proof_key in self.pending_proofs:
                    del self.pending_proofs[proof_key]
            
            logger.debug(f"Cleaned up {len(used_proofs)} used proofs")
            
        except Exception as e:
            logger.error(f"Failed to cleanup used proofs: {e}")
    
    def _calculate_proof_hash(self, proof: PoOTProof) -> str:
        """Calculate hash for proof"""
        proof_data = f"{proof.node_id}:{proof.session_id}:{proof.observation_time}:{proof.work_credits}:{proof.merkle_root}:{proof.timestamp.isoformat()}"
        return hashlib.sha256(proof_data.encode()).hexdigest()
    
    def _calculate_block_merkle_root(self, proofs: List[PoOTProof]) -> str:
        """Calculate Merkle root for block proofs"""
        if not proofs:
            return "0" * 64
        
        # Simple Merkle tree calculation (in practice, use proper Merkle tree)
        proof_hashes = [proof.proof_hash for proof in proofs]
        
        while len(proof_hashes) > 1:
            next_level = []
            for i in range(0, len(proof_hashes), 2):
                left = proof_hashes[i]
                right = proof_hashes[i + 1] if i + 1 < len(proof_hashes) else left
                combined = hashlib.sha256((left + right).encode()).hexdigest()
                next_level.append(combined)
            proof_hashes = next_level
        
        return proof_hashes[0]
    
    def _calculate_block_hash(self, block_data: Dict[str, Any]) -> str:
        """Calculate hash for block"""
        # Remove block_hash field if present
        block_data_copy = block_data.copy()
        block_data_copy.pop("block_hash", None)
        
        block_string = json.dumps(block_data_copy, sort_keys=True, default=str)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def get_consensus_status(self) -> Dict[str, Any]:
        """Get current consensus status"""
        return {
            "state": self.state.value,
            "current_height": self.current_height,
            "consensus_round": self.consensus_round,
            "pending_proofs": len(self.pending_proofs),
            "validated_blocks": len(self.validated_blocks),
            "last_block_time": self.last_block_time.isoformat(),
            "config": asdict(self.config)
        }
    
    def get_blockchain_info(self) -> Dict[str, Any]:
        """Get blockchain information"""
        return {
            "current_height": self.current_height,
            "total_blocks": len(self.validated_blocks),
            "last_block_hash": self.validated_blocks[-1].block_hash if self.validated_blocks else None,
            "last_block_time": self.last_block_time.isoformat(),
            "consensus_algorithm": "PoOT",
            "block_time_seconds": self.config.block_time_seconds
        }

# Example usage
if __name__ == "__main__":
    async def main():
        # Initialize consensus engine
        config = ConsensusConfig(
            block_time_seconds=10,
            min_proofs_per_block=3,
            max_proofs_per_block=10,
            consensus_threshold=0.67
        )
        
        consensus = ConsensusEngine(config)
        
        # Start consensus
        success = await consensus.start_consensus()
        print(f"Consensus started: {success}")
        
        if success:
            # Submit some sample proofs
            for i in range(5):
                proof = PoOTProof(
                    node_id=f"node_{i}",
                    session_id=f"session_{i}",
                    observation_time=100.0 + i * 10,
                    work_credits=50.0 + i * 5,
                    merkle_root="a" * 64,  # Placeholder
                    proof_hash="",  # Will be calculated
                    timestamp=datetime.utcnow()
                )
                
                # Calculate proof hash
                proof.proof_hash = consensus._calculate_proof_hash(proof)
                
                # Submit proof
                submitted = await consensus.submit_proof(proof)
                print(f"Proof {i} submitted: {submitted}")
            
            # Wait for consensus rounds
            await asyncio.sleep(15)
            
            # Get status
            status = consensus.get_consensus_status()
            print(f"Consensus status: {status}")
            
            # Get blockchain info
            blockchain_info = consensus.get_blockchain_info()
            print(f"Blockchain info: {blockchain_info}")
    
    asyncio.run(main())