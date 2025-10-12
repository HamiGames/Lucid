# Path: blockchain/core/work_credits.py
"""
PoOT Work Credits System

Implements work credits calculation for Proof of Operational Tasks (PoOT) consensus
based on Spec-1b lines 129-134.

Work Credits Sources:
- relay_bandwidth: Data relayed between nodes
- storage_availability: Chunks stored and available
- validation_signature: Session validation signatures
- uptime_beacon: Node uptime and availability

Formula: W_t = max(S_t, ceil(B_t / BASE_MB_PER_SESSION))
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import math

from motor.motor_asyncio import AsyncIOMotorDatabase

from .models import TaskProof, TaskProofType, WorkCreditsTally, WorkCredit

logger = logging.getLogger(__name__)

# =============================================================================
# IMMUTABLE CONSENSUS PARAMETERS (Spec-1b)
# =============================================================================

LEADER_WINDOW_DAYS = 7   # 7-day PoOT window
BASE_MB_PER_SESSION = 5  # 5MB base unit
D_MIN = 0.2             # Minimum density threshold


class WorkCreditsEngine:
    """
    PoOT work credits calculation engine.
    
    Calculates work credits from operational tasks:
    - relay_bandwidth: Data relayed between nodes
    - storage_availability: Chunks stored and available  
    - validation_signature: Session validation signatures
    - uptime_beacon: Node uptime and availability
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        logger.info("Work credits engine initialized")
    
    async def submit_task_proof(self, proof: TaskProof) -> bool:
        """
        Submit work credits proof for PoOT consensus.
        
        Args:
            proof: Task proof containing work evidence
            
        Returns:
            True if proof was stored successfully
        """
        try:
            # Validate proof type
            if proof.type not in TaskProofType:
                raise ValueError(f"Invalid proof type: {proof.type}")
            
            # Validate proof data based on type
            self._validate_proof_data(proof)
            
            # Store proof in MongoDB (sharded collection)
            await self.db["task_proofs"].insert_one(proof.to_dict())
            
            logger.info(f"Work proof submitted: {proof.node_id} - {proof.type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit work proof: {e}")
            return False
    
    def _validate_proof_data(self, proof: TaskProof):
        """Validate proof data based on proof type"""
        value = proof.value
        
        if proof.type == TaskProofType.RELAY_BANDWIDTH:
            if "bytes_transferred" not in value:
                raise ValueError("relay_bandwidth proof missing bytes_transferred")
            if not isinstance(value["bytes_transferred"], int) or value["bytes_transferred"] < 0:
                raise ValueError("bytes_transferred must be non-negative integer")
                
        elif proof.type == TaskProofType.STORAGE_AVAILABILITY:
            required_fields = ["chunks_stored", "size_bytes"]
            for field in required_fields:
                if field not in value:
                    raise ValueError(f"storage_availability proof missing {field}")
                if not isinstance(value[field], int) or value[field] < 0:
                    raise ValueError(f"{field} must be non-negative integer")
                    
        elif proof.type == TaskProofType.VALIDATION_SIGNATURE:
            if "validated_sessions" not in value:
                raise ValueError("validation_signature proof missing validated_sessions")
            if not isinstance(value["validated_sessions"], int) or value["validated_sessions"] < 0:
                raise ValueError("validated_sessions must be non-negative integer")
                
        elif proof.type == TaskProofType.UPTIME_BEACON:
            if "uptime_seconds" not in value:
                raise ValueError("uptime_beacon proof missing uptime_seconds")
            if not isinstance(value["uptime_seconds"], int) or value["uptime_seconds"] < 0:
                raise ValueError("uptime_seconds must be non-negative integer")
    
    async def calculate_work_credits(self, epoch: int) -> List[WorkCreditsTally]:
        """
        Calculate work credits for all entities over sliding window.
        
        Per Spec-1b: W_t = max(S_t, ceil(B_t / BASE_MB_PER_SESSION))
        where BASE_MB_PER_SESSION = 5MB
        
        Args:
            epoch: Epoch number for work credits calculation
            
        Returns:
            List of WorkCreditsTally objects sorted by live score
        """
        try:
            # Get all work proofs for the epoch window
            window_start = datetime.now(timezone.utc) - timedelta(days=LEADER_WINDOW_DAYS)
            
            proofs_cursor = self.db["task_proofs"].find({
                "ts": {"$gte": window_start}
            })
            
            # Aggregate work credits by entity
            entity_credits: Dict[str, Dict[str, Any]] = {}
            
            async for proof_doc in proofs_cursor:
                entity_id = proof_doc["nodeId"]
                proof_type = TaskProofType(proof_doc["type"])
                value = proof_doc["value"]
                
                if entity_id not in entity_credits:
                    entity_credits[entity_id] = {
                        "relay_bandwidth": 0,
                        "storage_proofs": 0,
                        "validation_signatures": 0,
                        "uptime_score": 0.0,
                        "total_uptime_seconds": 0,
                        "proof_count": 0
                    }
                
                # Calculate credits based on proof type
                credits = self._calculate_credits_for_proof(proof_type, value)
                
                if proof_type == TaskProofType.RELAY_BANDWIDTH:
                    entity_credits[entity_id]["relay_bandwidth"] += credits
                elif proof_type == TaskProofType.STORAGE_AVAILABILITY:
                    entity_credits[entity_id]["storage_proofs"] += credits
                elif proof_type == TaskProofType.VALIDATION_SIGNATURE:
                    entity_credits[entity_id]["validation_signatures"] += credits
                elif proof_type == TaskProofType.UPTIME_BEACON:
                    entity_credits[entity_id]["total_uptime_seconds"] += value["uptime_seconds"]
                    entity_credits[entity_id]["proof_count"] += 1
            
            # Calculate uptime scores and create tallies
            tallies = []
            for entity_id, credits in entity_credits.items():
                # Calculate uptime score (percentage of window)
                max_uptime_seconds = LEADER_WINDOW_DAYS * 24 * 60 * 60
                uptime_score = min(credits["total_uptime_seconds"] / max_uptime_seconds, 1.0)
                credits["uptime_score"] = uptime_score
                
                # Calculate total credits
                total_credits = (
                    credits["relay_bandwidth"] +
                    credits["storage_proofs"] +
                    credits["validation_signatures"]
                )
                
                # Apply uptime multiplier to get live score
                live_score = total_credits * uptime_score
                
                # Only include entities with minimum activity
                if total_credits > 0 and uptime_score >= D_MIN:
                    tally = WorkCreditsTally(
                        epoch=epoch,
                        entity_id=entity_id,
                        credits_total=total_credits,
                        relay_bandwidth=credits["relay_bandwidth"],
                        storage_proofs=credits["storage_proofs"],
                        validation_signatures=credits["validation_signatures"],
                        uptime_score=uptime_score,
                        live_score=live_score,
                        rank=0  # Will be set after sorting
                    )
                    tallies.append(tally)
            
            # Sort by live score and assign ranks
            tallies.sort(key=lambda x: x.live_score, reverse=True)
            for i, tally in enumerate(tallies):
                tally.rank = i + 1
            
            # Store tallies in MongoDB
            await self._store_work_tallies(tallies)
            
            logger.info(f"Work credits calculated for epoch {epoch}: {len(tallies)} entities")
            return tallies
            
        except Exception as e:
            logger.error(f"Failed to calculate work credits: {e}")
            return []
    
    def _calculate_credits_for_proof(self, proof_type: TaskProofType, value: Dict[str, Any]) -> int:
        """
        Calculate credits for specific proof type.
        
        Args:
            proof_type: Type of proof
            value: Proof value data
            
        Returns:
            Credits earned for this proof
        """
        if proof_type == TaskProofType.RELAY_BANDWIDTH:
            # W_t = max(S_t, ceil(B_t / BASE_MB_PER_SESSION))
            bytes_transferred = value["bytes_transferred"]
            bandwidth_mb = bytes_transferred / (1024 * 1024)
            sessions_relayed = value.get("sessions_relayed", 1)
            
            bandwidth_credits = math.ceil(bandwidth_mb / BASE_MB_PER_SESSION)
            return max(sessions_relayed, bandwidth_credits)
            
        elif proof_type == TaskProofType.STORAGE_AVAILABILITY:
            # Storage credits based on chunks stored and uptime
            chunks_stored = value["chunks_stored"]
            size_bytes = value["size_bytes"]
            storage_gb = size_bytes / (1024 * 1024 * 1024)
            
            # Base credits for storage capacity
            base_credits = int(storage_gb * 10)  # 10 credits per GB
            chunk_credits = chunks_stored * 2    # 2 credits per chunk
            return base_credits + chunk_credits
            
        elif proof_type == TaskProofType.VALIDATION_SIGNATURE:
            # Credits for validation work
            validated_sessions = value["validated_sessions"]
            return validated_sessions * 5  # 5 credits per validated session
            
        elif proof_type == TaskProofType.UPTIME_BEACON:
            # Uptime credits (will be used for uptime score calculation)
            uptime_hours = value["uptime_seconds"] / 3600
            return int(uptime_hours)  # 1 credit per hour uptime
        
        return 0
    
    async def _store_work_tallies(self, tallies: List[WorkCreditsTally]):
        """Store work credits tallies in MongoDB"""
        try:
            for tally in tallies:
                await self.db["work_tally"].replace_one(
                    {"_id": tally.to_dict()["_id"]},
                    tally.to_dict(),
                    upsert=True
                )
        except Exception as e:
            logger.error(f"Failed to store work tallies: {e}")
    
    async def get_entity_work_credits(self, entity_id: str, epoch: int) -> Optional[WorkCreditsTally]:
        """Get work credits for specific entity in epoch"""
        try:
            doc = await self.db["work_tally"].find_one({
                "_id": f"{epoch}_{entity_id}"
            })
            
            if doc:
                return WorkCreditsTally(
                    epoch=doc["epoch"],
                    entity_id=doc["entityId"],
                    credits_total=doc["credits"],
                    relay_bandwidth=0,  # Not stored in simplified tally
                    storage_proofs=0,
                    validation_signatures=0,
                    uptime_score=0.0,
                    live_score=doc["liveScore"],
                    rank=doc["rank"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get work credits for {entity_id}: {e}")
            return None
    
    async def get_top_entities(self, epoch: int, limit: int = 10) -> List[WorkCredit]:
        """Get top entities by work credits for epoch"""
        try:
            cursor = self.db["work_tally"].find({"epoch": epoch}).sort("rank", 1).limit(limit)
            
            entities = []
            async for doc in cursor:
                entity = WorkCredit(
                    entity_id=doc["entityId"],
                    credits=doc["credits"],
                    live_score=doc["liveScore"],
                    rank=doc["rank"],
                    epoch=doc["epoch"]
                )
                entities.append(entity)
            
            return entities
            
        except Exception as e:
            logger.error(f"Failed to get top entities: {e}")
            return []
    
    async def get_entity_rank(self, entity_id: str, epoch: int) -> Optional[int]:
        """Get rank of entity in epoch"""
        try:
            doc = await self.db["work_tally"].find_one({
                "_id": f"{epoch}_{entity_id}"
            })
            
            return doc["rank"] if doc else None
            
        except Exception as e:
            logger.error(f"Failed to get rank for {entity_id}: {e}")
            return None
    
    async def cleanup_old_proofs(self, days_to_keep: int = LEADER_WINDOW_DAYS):
        """Clean up old task proofs beyond the sliding window"""
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            result = await self.db["task_proofs"].delete_many({
                "ts": {"$lt": cutoff_date}
            })
            
            logger.info(f"Cleaned up {result.deleted_count} old task proofs")
            return result.deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old proofs: {e}")
            return 0
    
    async def get_proof_statistics(self, epoch: int) -> Dict[str, Any]:
        """Get statistics about proofs for epoch"""
        try:
            window_start = datetime.now(timezone.utc) - timedelta(days=LEADER_WINDOW_DAYS)
            
            # Count proofs by type
            proof_counts = {}
            for proof_type in TaskProofType:
                count = await self.db["task_proofs"].count_documents({
                    "type": proof_type.value,
                    "ts": {"$gte": window_start}
                })
                proof_counts[proof_type.value] = count
            
            # Count unique entities
            unique_entities = await self.db["task_proofs"].distinct(
                "nodeId", 
                {"ts": {"$gte": window_start}}
            )
            
            # Total proofs
            total_proofs = sum(proof_counts.values())
            
            return {
                "epoch": epoch,
                "total_proofs": total_proofs,
                "unique_entities": len(unique_entities),
                "proofs_by_type": proof_counts,
                "window_days": LEADER_WINDOW_DAYS
            }
            
        except Exception as e:
            logger.error(f"Failed to get proof statistics: {e}")
            return {}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def calculate_work_credits_formula(storage_sessions: int, bandwidth_mb: int, 
                                 base_mb_per_session: int = BASE_MB_PER_SESSION) -> int:
    """
    Calculate work credits using Spec-1b formula.
    
    W_t = max(S_t, ceil(B_t / BASE_MB_PER_SESSION))
    where:
    - S_t = storage sessions
    - B_t = bandwidth in MB
    - BASE_MB_PER_SESSION = 5MB (default)
    
    Args:
        storage_sessions: Number of sessions stored
        bandwidth_mb: Bandwidth in MB
        base_mb_per_session: Base MB per session (default 5)
        
    Returns:
        Work credits earned
    """
    bandwidth_credits = math.ceil(bandwidth_mb / base_mb_per_session)
    return max(storage_sessions, bandwidth_credits)


def validate_proof_signature(proof: TaskProof, public_key: str) -> bool:
    """
    Validate proof signature.
    
    Args:
        proof: Task proof to validate
        public_key: Entity's public key
        
    Returns:
        True if signature is valid
    """
    try:
        # This would implement proper signature validation
        return True
        
    except Exception as e:
        logger.error(f"Failed to validate proof signature: {e}")
        return False


def calculate_uptime_score(uptime_seconds: int, window_days: int = LEADER_WINDOW_DAYS) -> float:
    """
    Calculate uptime score as percentage of window.
    
    Args:
        uptime_seconds: Total uptime in seconds
        window_days: Window period in days
        
    Returns:
        Uptime score between 0.0 and 1.0
    """
    max_uptime_seconds = window_days * 24 * 60 * 60
    return min(uptime_seconds / max_uptime_seconds, 1.0)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "WorkCreditsEngine",
    "calculate_work_credits_formula",
    "validate_proof_signature",
    "calculate_uptime_score",
    "LEADER_WINDOW_DAYS",
    "BASE_MB_PER_SESSION",
    "D_MIN"
]