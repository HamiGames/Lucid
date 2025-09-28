# Path: node/work_credits.py

from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
import hashlib
import hmac

logger = logging.getLogger(__name__)


@dataclass
class WorkProof:
    """Proof of operational work performed by a node."""
    node_id: str
    pool_id: Optional[str]
    slot: int
    task_type: str  # relay_bandwidth, storage_proof, validation_sig, uptime_beacon
    value: float
    signature: str
    timestamp: datetime
    
    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "pool_id": self.pool_id,
            "slot": self.slot,
            "task_type": self.task_type,
            "value": self.value,
            "signature": self.signature,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> WorkProof:
        return cls(
            node_id=data["node_id"],
            pool_id=data.get("pool_id"),
            slot=data["slot"],
            task_type=data["task_type"],
            value=data["value"],
            signature=data["signature"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )


@dataclass
class WorkTally:
    """Aggregated work credits for an entity (node or pool)."""
    entity_id: str
    epoch: int
    credits: float
    live_score: float
    rank: int
    last_selected_slot: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            "entity_id": self.entity_id,
            "epoch": self.epoch,
            "credits": self.credits,
            "live_score": self.live_score,
            "rank": self.rank,
            "last_selected_slot": self.last_selected_slot
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> WorkTally:
        return cls(
            entity_id=data["entity_id"],
            epoch=data["epoch"],
            credits=data["credits"],
            live_score=data["live_score"],
            rank=data["rank"],
            last_selected_slot=data.get("last_selected_slot")
        )


class WorkCreditsCalculator:
    """
    Calculates work credits for Proof of Operational Tasks (PoOT) consensus.
    Tracks and validates operational work proofs from network nodes.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, slot_duration_sec: int = 120):
        self.db = db
        self.slot_duration_sec = slot_duration_sec
        self.current_epoch = self._calculate_epoch()
        
        # Task weights for credit calculation
        self.task_weights = {
            "relay_bandwidth": 1.0,     # Per GB relayed
            "storage_proof": 0.5,       # Per storage challenge passed
            "validation_sig": 0.3,      # Per validation signature
            "uptime_beacon": 0.1        # Per uptime beacon
        }
        
    def _calculate_epoch(self) -> int:
        """Calculate current epoch (monthly periods)."""
        now = datetime.now(timezone.utc)
        # Epoch 0 starts at 2025-01-01 00:00:00 UTC
        epoch_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        delta = now - epoch_start
        return int(delta.days // 30)  # Monthly epochs
        
    def _calculate_slot(self, timestamp: datetime) -> int:
        """Calculate slot number from timestamp."""
        epoch_start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        delta = timestamp - epoch_start
        return int(delta.total_seconds() // self.slot_duration_sec)
        
    async def submit_work_proof(self, proof: WorkProof) -> bool:
        """Submit and validate a work proof."""
        try:
            # Validate proof signature (simplified - would use actual crypto in production)
            if not self._validate_proof_signature(proof):
                logger.warning(f"Invalid proof signature from {proof.node_id}")
                return False
                
            # Check if proof already exists
            existing = await self.db["task_proofs"].find_one({
                "node_id": proof.node_id,
                "slot": proof.slot,
                "task_type": proof.task_type
            })
            
            if existing:
                logger.debug(f"Duplicate proof from {proof.node_id} for slot {proof.slot}")
                return False
                
            # Store proof
            await self.db["task_proofs"].insert_one(proof.to_dict())
            logger.info(f"Accepted work proof: {proof.task_type} from {proof.node_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit work proof: {e}")
            return False
            
    async def calculate_work_credits(
        self, 
        entity_id: str, 
        window_days: int = 7
    ) -> float:
        """Calculate work credits for an entity over a sliding window."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=window_days)
            cutoff_slot = self._calculate_slot(cutoff_time)
            
            # Query proofs for this entity
            query = {
                "slot": {"$gte": cutoff_slot},
                "$or": [
                    {"node_id": entity_id},
                    {"pool_id": entity_id}
                ]
            }
            
            total_credits = 0.0
            cursor = self.db["task_proofs"].find(query)
            
            async for proof_doc in cursor:
                proof = WorkProof.from_dict(proof_doc)
                weight = self.task_weights.get(proof.task_type, 0.1)
                credits = proof.value * weight
                total_credits += credits
                
            return total_credits
            
        except Exception as e:
            logger.error(f"Failed to calculate work credits for {entity_id}: {e}")
            return 0.0
            
    async def update_work_tally(self, epoch: Optional[int] = None) -> None:
        """Update work tally for all entities."""
        if epoch is None:
            epoch = self.current_epoch
            
        try:
            # Get all unique entities (nodes and pools)
            entities = set()
            
            # Add individual nodes
            cursor = self.db["task_proofs"].find({}, {"node_id": 1})
            async for doc in cursor:
                entities.add(doc["node_id"])
                
            # Add pools
            cursor = self.db["task_proofs"].find(
                {"pool_id": {"$ne": None}}, 
                {"pool_id": 1}
            )
            async for doc in cursor:
                if doc.get("pool_id"):
                    entities.add(doc["pool_id"])
                    
            # Calculate credits for each entity
            tallies = []
            for entity_id in entities:
                credits = await self.calculate_work_credits(entity_id)
                
                # Calculate live score (uptime-based penalty)
                live_score = await self._calculate_live_score(entity_id)
                
                tally = WorkTally(
                    entity_id=entity_id,
                    epoch=epoch,
                    credits=credits,
                    live_score=live_score,
                    rank=0  # Will be set after sorting
                )
                tallies.append(tally)
                
            # Sort by credits (descending) and assign ranks
            tallies.sort(key=lambda x: x.credits, reverse=True)
            for i, tally in enumerate(tallies):
                tally.rank = i + 1
                
            # Save to database
            for tally in tallies:
                await self.db["work_tally"].replace_one(
                    {"entity_id": tally.entity_id, "epoch": epoch},
                    tally.to_dict(),
                    upsert=True
                )
                
            logger.info(f"Updated work tally for epoch {epoch}, {len(tallies)} entities")
            
        except Exception as e:
            logger.error(f"Failed to update work tally: {e}")
            
    async def get_top_entities(self, limit: int = 10, epoch: Optional[int] = None) -> List[WorkTally]:
        """Get top entities by work credits."""
        if epoch is None:
            epoch = self.current_epoch
            
        try:
            cursor = self.db["work_tally"].find(
                {"epoch": epoch}
            ).sort("rank", 1).limit(limit)
            
            tallies = []
            async for doc in cursor:
                tallies.append(WorkTally.from_dict(doc))
                
            return tallies
            
        except Exception as e:
            logger.error(f"Failed to get top entities: {e}")
            return []
            
    async def get_entity_rank(self, entity_id: str, epoch: Optional[int] = None) -> Optional[int]:
        """Get rank for specific entity."""
        if epoch is None:
            epoch = self.current_epoch
            
        try:
            doc = await self.db["work_tally"].find_one({
                "entity_id": entity_id,
                "epoch": epoch
            })
            
            if doc:
                return doc["rank"]
                
        except Exception as e:
            logger.error(f"Failed to get entity rank: {e}")
            
        return None
        
    async def record_uptime_beacon(self, node_id: str, pool_id: Optional[str] = None) -> None:
        """Record an uptime beacon from a node."""
        try:
            now = datetime.now(timezone.utc)
            slot = self._calculate_slot(now)
            
            # Create simple signature for uptime beacon
            message = f"{node_id}:{slot}:uptime_beacon"
            signature = hashlib.sha256(message.encode()).hexdigest()
            
            proof = WorkProof(
                node_id=node_id,
                pool_id=pool_id,
                slot=slot,
                task_type="uptime_beacon",
                value=1.0,  # Simple uptime value
                signature=signature,
                timestamp=now
            )
            
            await self.submit_work_proof(proof)
            
        except Exception as e:
            logger.error(f"Failed to record uptime beacon: {e}")
            
    async def record_relay_bandwidth(
        self, 
        node_id: str, 
        bytes_relayed: int, 
        pool_id: Optional[str] = None
    ) -> None:
        """Record bandwidth relayed by a node."""
        try:
            now = datetime.now(timezone.utc)
            slot = self._calculate_slot(now)
            gb_relayed = bytes_relayed / (1024 ** 3)  # Convert to GB
            
            message = f"{node_id}:{slot}:relay_bandwidth:{bytes_relayed}"
            signature = hashlib.sha256(message.encode()).hexdigest()
            
            proof = WorkProof(
                node_id=node_id,
                pool_id=pool_id,
                slot=slot,
                task_type="relay_bandwidth",
                value=gb_relayed,
                signature=signature,
                timestamp=now
            )
            
            await self.submit_work_proof(proof)
            
        except Exception as e:
            logger.error(f"Failed to record relay bandwidth: {e}")
            
    def _validate_proof_signature(self, proof: WorkProof) -> bool:
        """Validate proof signature (simplified implementation)."""
        # In production, this would use proper cryptographic verification
        message = f"{proof.node_id}:{proof.slot}:{proof.task_type}:{proof.value}"
        expected_sig = hashlib.sha256(message.encode()).hexdigest()
        return proof.signature == expected_sig
        
    async def _calculate_live_score(self, entity_id: str) -> float:
        """Calculate live score based on missed slots and penalties."""
        # Simplified implementation - would track missed slots in production
        try:
            # Count recent uptime beacons as a proxy for liveness
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            cutoff_slot = self._calculate_slot(cutoff_time)
            
            beacon_count = await self.db["task_proofs"].count_documents({
                "$or": [
                    {"node_id": entity_id},
                    {"pool_id": entity_id}
                ],
                "task_type": "uptime_beacon",
                "slot": {"$gte": cutoff_slot}
            })
            
            # Expected beacons in 24 hours (one per slot)
            expected_beacons = 24 * 3600 // self.slot_duration_sec
            live_score = min(1.0, beacon_count / expected_beacons)
            
            return live_score
            
        except Exception as e:
            logger.error(f"Failed to calculate live score for {entity_id}: {e}")
            return 0.5  # Default score
            
    async def ensure_indexes(self) -> None:
        """Ensure database indexes for work credits collections."""
        try:
            # Task proofs indexes
            await self.db["task_proofs"].create_index([
                ("slot", 1), ("node_id", 1)
            ])
            await self.db["task_proofs"].create_index([
                ("node_id", 1), ("slot", 1), ("task_type", 1)
            ], unique=True)
            await self.db["task_proofs"].create_index("pool_id")
            
            # Work tally indexes  
            await self.db["work_tally"].create_index([
                ("entity_id", 1), ("epoch", 1)
            ], unique=True)
            await self.db["work_tally"].create_index([
                ("epoch", 1), ("rank", 1)
            ])
            
        except Exception as e:
            logger.warning(f"Failed to create work credits indexes: {e}")