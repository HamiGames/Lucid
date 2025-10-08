# Path: node/consensus/leader_selection.py
# Lucid Node Consensus - Leader Selection Algorithm
# Implements distributed leader selection for consensus protocols
# LUCID-STRICT Layer 1 Core Infrastructure

from __future__ import annotations

import asyncio
import logging
import os
import time
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import aiofiles
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# Configuration from environment
LEADER_SELECTION_INTERVAL = int(os.getenv("LEADER_SELECTION_INTERVAL", "30"))  # seconds
CONSENSUS_ROUND_DURATION = int(os.getenv("CONSENSUS_ROUND_DURATION", "10"))  # seconds
MINIMUM_STAKE_THRESHOLD = float(os.getenv("MINIMUM_STAKE_THRESHOLD", "1000.0"))
LEADER_SELECTION_ALGORITHM = os.getenv("LEADER_SELECTION_ALGORITHM", "weighted_random")
NETWORK_SIZE_ESTIMATE = int(os.getenv("NETWORK_SIZE_ESTIMATE", "100"))


class NodeStatus(Enum):
    """Node status in the network"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class LeaderSelectionMethod(Enum):
    """Leader selection algorithms"""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_RANDOM = "weighted_random"
    PROOF_OF_STAKE = "proof_of_stake"
    PROOF_OF_WORK = "proof_of_work"
    RANDOMIZED_BYZANTINE = "randomized_byzantine"


class ConsensusRole(Enum):
    """Roles in consensus protocol"""
    LEADER = "leader"
    VALIDATOR = "validator"
    OBSERVER = "observer"
    BACKUP_LEADER = "backup_leader"


@dataclass
class NodeInfo:
    """Information about a network node"""
    node_id: str
    public_key: str
    stake_amount: float
    reputation_score: float
    last_seen: datetime
    status: NodeStatus
    network_address: str
    consensus_participation: bool = True
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LeaderSelectionResult:
    """Result of leader selection process"""
    round_number: int
    selected_leader: str
    selection_timestamp: datetime
    selection_method: LeaderSelectionMethod
    selection_proof: str
    backup_leaders: List[str] = field(default_factory=list)
    validators: List[str] = field(default_factory=list)
    selection_confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsensusRound:
    """A consensus round with selected leader"""
    round_number: int
    leader: str
    start_time: datetime
    end_time: datetime
    duration: timedelta
    participants: List[str]
    completed: bool = False
    success: bool = False
    block_hash: Optional[str] = None
    transaction_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class LeaderSelection:
    """Distributed leader selection algorithm"""
    
    def __init__(self, node_id: str, private_key: rsa.RSAPrivateKey):
        self.node_id = node_id
        self.private_key = private_key
        self.public_key = private_key.public_key()
        self.known_nodes: Dict[str, NodeInfo] = {}
        self.current_round = 0
        self.leader_selection_method = LeaderSelectionMethod(LEADER_SELECTION_ALGORITHM)
        self.consensus_rounds: List[ConsensusRound] = []
        self.is_leader = False
        self.current_leader = None
        self.selection_interval = LEADER_SELECTION_INTERVAL
        self.round_duration = timedelta(seconds=CONSENSUS_ROUND_DURATION)
        self.min_stake_threshold = MINIMUM_STAKE_THRESHOLD
        
        # Performance tracking
        self.performance_history: List[Dict[str, Any]] = []
        self.leader_selection_history: List[LeaderSelectionResult] = []
        
        # Initialize with self
        self._register_self()
    
    def _register_self(self):
        """Register this node in the known nodes"""
        public_key_pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        
        self.known_nodes[self.node_id] = NodeInfo(
            node_id=self.node_id,
            public_key=public_key_pem,
            stake_amount=1000.0,  # Default stake
            reputation_score=1.0,
            last_seen=datetime.now(timezone.utc),
            status=NodeStatus.ACTIVE,
            network_address="localhost:8080",  # Default address
            consensus_participation=True
        )
    
    async def start_leader_selection(self):
        """Start the leader selection process"""
        logger.info(f"Starting leader selection for node {self.node_id}")
        
        while True:
            try:
                # Update node information
                await self._update_node_information()
                
                # Perform leader selection
                selection_result = await self._perform_leader_selection()
                
                # Start consensus round if we're the leader
                if selection_result.selected_leader == self.node_id:
                    await self._start_consensus_round(selection_result)
                else:
                    await self._participate_in_consensus_round(selection_result)
                
                # Wait for next selection interval
                await asyncio.sleep(self.selection_interval)
                
            except Exception as e:
                logger.error(f"Error in leader selection: {e}")
                await asyncio.sleep(5)  # Short delay before retry
    
    async def _update_node_information(self):
        """Update information about known nodes"""
        try:
            # In production, this would query the network for node information
            # For now, we'll simulate some updates
            
            current_time = datetime.now(timezone.utc)
            
            for node_id, node_info in self.known_nodes.items():
                # Update last seen time
                if node_id != self.node_id:
                    # Simulate network activity
                    if secrets.randbelow(10) > 2:  # 80% chance of being active
                        node_info.last_seen = current_time
                        node_info.status = NodeStatus.ACTIVE
                    else:
                        node_info.status = NodeStatus.INACTIVE
                
                # Update performance metrics
                node_info.performance_metrics.update({
                    "uptime": secrets.uniform(0.8, 1.0),
                    "response_time": secrets.uniform(10, 100),
                    "consensus_participation": secrets.uniform(0.7, 1.0)
                })
                
                # Update reputation based on performance
                self._update_reputation(node_info)
            
            # Add new nodes occasionally (simulation)
            if len(self.known_nodes) < NETWORK_SIZE_ESTIMATE and secrets.randbelow(100) < 5:
                await self._add_random_node()
                
        except Exception as e:
            logger.error(f"Failed to update node information: {e}")
    
    def _update_reputation(self, node_info: NodeInfo):
        """Update node reputation based on performance"""
        try:
            metrics = node_info.performance_metrics
            
            # Calculate reputation based on various factors
            uptime_score = metrics.get("uptime", 0.5)
            participation_score = metrics.get("consensus_participation", 0.5)
            response_score = max(0, 1.0 - (metrics.get("response_time", 100) / 1000))
            
            # Weighted average
            new_reputation = (
                uptime_score * 0.4 +
                participation_score * 0.4 +
                response_score * 0.2
            )
            
            # Smooth reputation changes
            node_info.reputation_score = (node_info.reputation_score * 0.9) + (new_reputation * 0.1)
            
        except Exception as e:
            logger.error(f"Failed to update reputation for {node_info.node_id}: {e}")
    
    async def _add_random_node(self):
        """Add a random node to the network (simulation)"""
        try:
            new_node_id = f"node_{secrets.token_hex(8)}"
            
            # Generate a random public key (simplified)
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            public_key = private_key.public_key()
            public_key_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ).decode()
            
            self.known_nodes[new_node_id] = NodeInfo(
                node_id=new_node_id,
                public_key=public_key_pem,
                stake_amount=secrets.uniform(100, 10000),
                reputation_score=secrets.uniform(0.5, 1.0),
                last_seen=datetime.now(timezone.utc),
                status=NodeStatus.ACTIVE,
                network_address=f"node_{new_node_id}:8080",
                consensus_participation=True
            )
            
            logger.info(f"Added new node to network: {new_node_id}")
            
        except Exception as e:
            logger.error(f"Failed to add random node: {e}")
    
    async def _perform_leader_selection(self) -> LeaderSelectionResult:
        """Perform leader selection based on the configured algorithm"""
        try:
            self.current_round += 1
            
            # Filter eligible nodes
            eligible_nodes = self._get_eligible_nodes()
            
            if not eligible_nodes:
                raise ValueError("No eligible nodes for leader selection")
            
            # Select leader based on algorithm
            if self.leader_selection_method == LeaderSelectionMethod.ROUND_ROBIN:
                selected_leader = self._round_robin_selection(eligible_nodes)
            elif self.leader_selection_method == LeaderSelectionMethod.WEIGHTED_RANDOM:
                selected_leader = self._weighted_random_selection(eligible_nodes)
            elif self.leader_selection_method == LeaderSelectionMethod.PROOF_OF_STAKE:
                selected_leader = self._proof_of_stake_selection(eligible_nodes)
            else:
                selected_leader = self._weighted_random_selection(eligible_nodes)
            
            # Select backup leaders
            backup_leaders = self._select_backup_leaders(eligible_nodes, selected_leader)
            
            # Select validators
            validators = self._select_validators(eligible_nodes, selected_leader)
            
            # Generate selection proof
            selection_proof = self._generate_selection_proof(selected_leader, self.current_round)
            
            # Create result
            result = LeaderSelectionResult(
                round_number=self.current_round,
                selected_leader=selected_leader,
                selection_timestamp=datetime.now(timezone.utc),
                selection_method=self.leader_selection_method,
                selection_proof=selection_proof,
                backup_leaders=backup_leaders,
                validators=validators,
                selection_confidence=self._calculate_selection_confidence(eligible_nodes, selected_leader)
            )
            
            # Store result
            self.leader_selection_history.append(result)
            
            # Update current leader
            self.current_leader = selected_leader
            self.is_leader = (selected_leader == self.node_id)
            
            logger.info(f"Round {self.current_round}: Selected leader {selected_leader}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to perform leader selection: {e}")
            raise
    
    def _get_eligible_nodes(self) -> List[NodeInfo]:
        """Get nodes eligible for leader selection"""
        eligible = []
        current_time = datetime.now(timezone.utc)
        
        for node_info in self.known_nodes.values():
            # Check if node is active and meets requirements
            if (node_info.status == NodeStatus.ACTIVE and
                node_info.consensus_participation and
                node_info.stake_amount >= self.min_stake_threshold and
                (current_time - node_info.last_seen).total_seconds() < 300):  # 5 minutes
                eligible.append(node_info)
        
        return eligible
    
    def _round_robin_selection(self, eligible_nodes: List[NodeInfo]) -> str:
        """Round-robin leader selection"""
        if not eligible_nodes:
            return self.node_id
        
        # Sort nodes by ID for consistent ordering
        sorted_nodes = sorted(eligible_nodes, key=lambda n: n.node_id)
        
        # Select based on round number
        index = self.current_round % len(sorted_nodes)
        return sorted_nodes[index].node_id
    
    def _weighted_random_selection(self, eligible_nodes: List[NodeInfo]) -> str:
        """Weighted random leader selection based on stake and reputation"""
        if not eligible_nodes:
            return self.node_id
        
        # Calculate weights
        weights = []
        for node in eligible_nodes:
            # Weight based on stake and reputation
            weight = node.stake_amount * node.reputation_score
            weights.append(weight)
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            # Fallback to equal probability
            weights = [1.0] * len(eligible_nodes)
            total_weight = len(eligible_nodes)
        
        normalized_weights = [w / total_weight for w in weights]
        
        # Random selection
        random_value = secrets.random()
        cumulative_weight = 0.0
        
        for i, weight in enumerate(normalized_weights):
            cumulative_weight += weight
            if random_value <= cumulative_weight:
                return eligible_nodes[i].node_id
        
        # Fallback
        return eligible_nodes[-1].node_id
    
    def _proof_of_stake_selection(self, eligible_nodes: List[NodeInfo]) -> str:
        """Proof-of-stake leader selection"""
        if not eligible_nodes:
            return self.node_id
        
        # Sort by stake amount (descending)
        sorted_nodes = sorted(eligible_nodes, key=lambda n: n.stake_amount, reverse=True)
        
        # Select from top stakers with some randomness
        top_count = min(5, len(sorted_nodes))
        top_nodes = sorted_nodes[:top_count]
        
        # Weighted selection among top stakers
        weights = [node.stake_amount for node in top_nodes]
        total_weight = sum(weights)
        
        random_value = secrets.random() * total_weight
        cumulative_weight = 0.0
        
        for i, weight in enumerate(weights):
            cumulative_weight += weight
            if random_value <= cumulative_weight:
                return top_nodes[i].node_id
        
        return top_nodes[0].node_id
    
    def _select_backup_leaders(self, eligible_nodes: List[NodeInfo], primary_leader: str) -> List[str]:
        """Select backup leaders"""
        backup_count = min(3, len(eligible_nodes) - 1)
        backup_leaders = []
        
        # Sort by stake and reputation
        sorted_nodes = sorted(
            [n for n in eligible_nodes if n.node_id != primary_leader],
            key=lambda n: n.stake_amount * n.reputation_score,
            reverse=True
        )
        
        for i in range(min(backup_count, len(sorted_nodes))):
            backup_leaders.append(sorted_nodes[i].node_id)
        
        return backup_leaders
    
    def _select_validators(self, eligible_nodes: List[NodeInfo], leader: str) -> List[str]:
        """Select validators for the consensus round"""
        validator_count = min(7, len(eligible_nodes) - 1)  # Exclude leader
        validators = []
        
        # Sort by reputation and stake
        sorted_nodes = sorted(
            [n for n in eligible_nodes if n.node_id != leader],
            key=lambda n: n.reputation_score * n.stake_amount,
            reverse=True
        )
        
        for i in range(min(validator_count, len(sorted_nodes))):
            validators.append(sorted_nodes[i].node_id)
        
        return validators
    
    def _generate_selection_proof(self, selected_leader: str, round_number: int) -> str:
        """Generate cryptographic proof of leader selection"""
        try:
            # Create proof data
            proof_data = f"{selected_leader}:{round_number}:{self.current_round}"
            
            # Sign with private key
            signature = self.private_key.sign(
                proof_data.encode(),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Encode signature
            proof = base64.b64encode(signature).decode()
            
            return proof
            
        except Exception as e:
            logger.error(f"Failed to generate selection proof: {e}")
            return ""
    
    def _calculate_selection_confidence(self, eligible_nodes: List[NodeInfo], selected_leader: str) -> float:
        """Calculate confidence in the leader selection"""
        try:
            if not eligible_nodes:
                return 0.0
            
            # Find selected node
            selected_node = next((n for n in eligible_nodes if n.node_id == selected_leader), None)
            if not selected_node:
                return 0.0
            
            # Calculate confidence based on node quality and network size
            node_quality = selected_node.reputation_score * (selected_node.stake_amount / 10000.0)
            network_size_factor = min(1.0, len(eligible_nodes) / 10.0)
            
            confidence = node_quality * network_size_factor
            return min(1.0, max(0.0, confidence))
            
        except Exception as e:
            logger.error(f"Failed to calculate selection confidence: {e}")
            return 0.5
    
    async def _start_consensus_round(self, selection_result: LeaderSelectionResult):
        """Start a consensus round as the leader"""
        try:
            logger.info(f"Starting consensus round {selection_result.round_number} as leader")
            
            # Create consensus round
            consensus_round = ConsensusRound(
                round_number=selection_result.round_number,
                leader=self.node_id,
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc) + self.round_duration,
                duration=self.round_duration,
                participants=selection_result.validators + [self.node_id]
            )
            
            self.consensus_rounds.append(consensus_round)
            
            # Simulate consensus process
            await self._simulate_consensus_process(consensus_round)
            
        except Exception as e:
            logger.error(f"Failed to start consensus round: {e}")
    
    async def _participate_in_consensus_round(self, selection_result: LeaderSelectionResult):
        """Participate in a consensus round as a validator"""
        try:
            if self.node_id in selection_result.validators:
                logger.info(f"Participating in consensus round {selection_result.round_number} as validator")
                
                # Simulate validation process
                await self._simulate_validation_process(selection_result)
            
        except Exception as e:
            logger.error(f"Failed to participate in consensus round: {e}")
    
    async def _simulate_consensus_process(self, consensus_round: ConsensusRound):
        """Simulate the consensus process"""
        try:
            # Simulate block creation and validation
            await asyncio.sleep(2)  # Simulate processing time
            
            # Generate mock block hash
            block_data = f"block_{consensus_round.round_number}_{self.node_id}_{time.time()}"
            consensus_round.block_hash = hashlib.sha256(block_data.encode()).hexdigest()
            
            # Simulate transaction processing
            consensus_round.transaction_count = secrets.randint(10, 100)
            
            # Mark as completed
            consensus_round.completed = True
            consensus_round.success = True
            
            logger.info(f"Consensus round {consensus_round.round_number} completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to simulate consensus process: {e}")
            consensus_round.completed = True
            consensus_round.success = False
    
    async def _simulate_validation_process(self, selection_result: LeaderSelectionResult):
        """Simulate the validation process"""
        try:
            # Simulate validation time
            await asyncio.sleep(1)
            
            # Simulate validation success (90% success rate)
            success = secrets.randbelow(10) < 9
            
            if success:
                logger.info(f"Validation successful for round {selection_result.round_number}")
            else:
                logger.warning(f"Validation failed for round {selection_result.round_number}")
            
        except Exception as e:
            logger.error(f"Failed to simulate validation process: {e}")
    
    async def get_leader_selection_history(self, limit: int = 10) -> List[LeaderSelectionResult]:
        """Get recent leader selection history"""
        return self.leader_selection_history[-limit:]
    
    async def get_consensus_rounds(self, limit: int = 10) -> List[ConsensusRound]:
        """Get recent consensus rounds"""
        return self.consensus_rounds[-limit:]
    
    async def get_network_status(self) -> Dict[str, Any]:
        """Get current network status"""
        try:
            active_nodes = [n for n in self.known_nodes.values() if n.status == NodeStatus.ACTIVE]
            
            return {
                "total_nodes": len(self.known_nodes),
                "active_nodes": len(active_nodes),
                "current_round": self.current_round,
                "current_leader": self.current_leader,
                "is_leader": self.is_leader,
                "selection_method": self.leader_selection_method.value,
                "average_stake": sum(n.stake_amount for n in active_nodes) / len(active_nodes) if active_nodes else 0,
                "average_reputation": sum(n.reputation_score for n in active_nodes) / len(active_nodes) if active_nodes else 0,
                "consensus_rounds_completed": len([r for r in self.consensus_rounds if r.completed]),
                "last_selection": self.leader_selection_history[-1].selection_timestamp.isoformat() if self.leader_selection_history else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get network status: {e}")
            return {}


# Global leader selection instance
leader_selection = None


async def initialize_leader_selection(node_id: str, private_key: rsa.RSAPrivateKey):
    """Initialize the leader selection system"""
    global leader_selection
    leader_selection = LeaderSelection(node_id, private_key)
    return leader_selection


async def start_consensus_process():
    """Start the consensus process"""
    if leader_selection:
        await leader_selection.start_leader_selection()
    else:
        raise ValueError("Leader selection not initialized")


async def get_current_leader() -> Optional[str]:
    """Get the current leader"""
    if leader_selection:
        return leader_selection.current_leader
    return None


async def is_current_leader() -> bool:
    """Check if this node is the current leader"""
    if leader_selection:
        return leader_selection.is_leader
    return False


async def get_network_status() -> Dict[str, Any]:
    """Get network status"""
    if leader_selection:
        return await leader_selection.get_network_status()
    return {}


if __name__ == "__main__":
    # Test the leader selection system
    async def test_leader_selection():
        # Generate test keys
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Initialize leader selection
        ls = await initialize_leader_selection("test_node", private_key)
        
        # Run for a few rounds
        for i in range(5):
            result = await ls._perform_leader_selection()
            print(f"Round {result.round_number}: Leader {result.selected_leader}")
            
            # Update network status
            await ls._update_node_information()
            
            await asyncio.sleep(1)
        
        # Get final status
        status = await ls.get_network_status()
        print(f"Network status: {status}")
    
    asyncio.run(test_leader_selection())
