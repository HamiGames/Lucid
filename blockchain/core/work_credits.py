#!/usr/bin/env python3
"""
Work Credits System for PoOT Consensus
Based on rebuild-blockchain-engine.md specifications

Implements work credits calculation and validation for:
- Relay bandwidth proofs
- Storage availability proofs  
- Validation signature proofs
- Uptime beacon proofs
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import secrets

logger = logging.getLogger(__name__)

# Work Credits Constants
BASE_MB_PER_SESSION = 5  # 5MB base unit per Spec-1b
RELAY_BANDWIDTH_MULTIPLIER = 1.0
STORAGE_PROOF_MULTIPLIER = 2.0
VALIDATION_SIGNATURE_MULTIPLIER = 3.0
UPTIME_SCORE_MULTIPLIER = 10.0


class WorkCreditsType(Enum):
    """Types of work credits"""
    RELAY_BANDWIDTH = "relay_bandwidth"
    STORAGE_AVAILABILITY = "storage_availability"
    VALIDATION_SIGNATURE = "validation_signature"
    UPTIME_BEACON = "uptime_beacon"


@dataclass
class BandwidthProof:
    """Relay bandwidth proof data"""
    bytes_transferred: int
    duration_seconds: float
    timestamp: datetime
    
    @property
    def bandwidth_mbps(self) -> float:
        """Calculate bandwidth in MB/s"""
        if self.duration_seconds <= 0:
            return 0.0
        return (self.bytes_transferred / (1024 * 1024)) / self.duration_seconds
    
    @property
    def bandwidth_credits(self) -> int:
        """Calculate credits based on bandwidth"""
        return max(1, int(self.bandwidth_mbps / BASE_MB_PER_SESSION))


@dataclass
class StorageProof:
    """Storage availability proof data"""
    total_capacity_bytes: int
    available_capacity_bytes: int
    chunks_stored: int
    verification_hash: str
    timestamp: datetime
    
    @property
    def availability_ratio(self) -> float:
        """Calculate storage availability ratio"""
        if self.total_capacity_bytes <= 0:
            return 0.0
        return self.available_capacity_bytes / self.total_capacity_bytes
    
    @property
    def storage_credits(self) -> int:
        """Calculate credits based on storage availability and chunks"""
        base_credits = int(self.availability_ratio * 10)  # 0-10 credits
        chunk_bonus = min(self.chunks_stored, 20)  # Up to 20 bonus credits
        return base_credits + chunk_bonus


@dataclass
class ValidationProof:
    """Validation signature proof data"""
    message_hash: str
    signature: bytes
    validator_address: str
    validation_count: int
    timestamp: datetime
    
    @property
    def validation_credits(self) -> int:
        """Calculate credits based on validation count"""
        return min(self.validation_count * VALIDATION_SIGNATURE_MULTIPLIER, 50)


@dataclass
class UptimeProof:
    """Uptime beacon proof data"""
    uptime_percentage: float
    consecutive_uptime_hours: int
    last_heartbeat: datetime
    timestamp: datetime
    
    @property
    def uptime_credits(self) -> int:
        """Calculate credits based on uptime"""
        base_credits = int(self.uptime_percentage * UPTIME_SCORE_MULTIPLIER)
        consecutive_bonus = min(self.consecutive_uptime_hours // 24, 20)  # Daily bonus
        return base_credits + consecutive_bonus


@dataclass
class WorkCreditsEntry:
    """Individual work credits entry"""
    node_id: str
    pool_id: Optional[str]
    credits_type: WorkCreditsType
    credits_amount: int
    proof_data: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "nodeId": self.node_id,
            "poolId": self.pool_id,
            "type": self.credits_type.value,
            "amount": self.credits_amount,
            "data": self.proof_data,
            "timestamp": self.timestamp
        }


class WorkCreditsCalculator:
    """Calculates work credits from various proof types"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_bandwidth_credits(self, proof: BandwidthProof) -> int:
        """
        Calculate credits from relay bandwidth proof.
        
        Formula: W_t = max(S_t, ceil(B_t / BASE_MB_PER_SESSION))
        where BASE_MB_PER_SESSION = 5MB
        """
        try:
            # Calculate bandwidth in MB/s
            bandwidth_mbps = proof.bandwidth_mbps
            
            # Apply work formula
            credits = max(1, int(bandwidth_mbps / BASE_MB_PER_SESSION))
            
            self.logger.debug(f"Bandwidth credits: {bandwidth_mbps:.2f} MB/s -> {credits} credits")
            return credits
            
        except Exception as e:
            self.logger.error(f"Failed to calculate bandwidth credits: {e}")
            return 0
    
    def calculate_storage_credits(self, proof: StorageProof) -> int:
        """Calculate credits from storage availability proof"""
        try:
            # Base credits from availability ratio
            availability_ratio = proof.availability_ratio
            base_credits = int(availability_ratio * 10)  # 0-10 credits
            
            # Bonus credits for stored chunks
            chunk_bonus = min(proof.chunks_stored, 20)  # Up to 20 bonus credits
            
            total_credits = base_credits + chunk_bonus
            
            self.logger.debug(f"Storage credits: {availability_ratio:.2f} availability, {proof.chunks_stored} chunks -> {total_credits} credits")
            return total_credits
            
        except Exception as e:
            self.logger.error(f"Failed to calculate storage credits: {e}")
            return 0
    
    def calculate_validation_credits(self, proof: ValidationProof) -> int:
        """Calculate credits from validation signature proof"""
        try:
            # Credits based on validation count
            credits = min(proof.validation_count * VALIDATION_SIGNATURE_MULTIPLIER, 50)
            
            self.logger.debug(f"Validation credits: {proof.validation_count} validations -> {credits} credits")
            return credits
            
        except Exception as e:
            self.logger.error(f"Failed to calculate validation credits: {e}")
            return 0
    
    def calculate_uptime_credits(self, proof: UptimeProof) -> int:
        """Calculate credits from uptime beacon proof"""
        try:
            # Base credits from uptime percentage
            base_credits = int(proof.uptime_percentage * UPTIME_SCORE_MULTIPLIER)
            
            # Bonus credits for consecutive uptime
            consecutive_bonus = min(proof.consecutive_uptime_hours // 24, 20)  # Daily bonus
            
            total_credits = base_credits + consecutive_bonus
            
            self.logger.debug(f"Uptime credits: {proof.uptime_percentage:.2f}% uptime, {proof.consecutive_uptime_hours}h consecutive -> {total_credits} credits")
            return total_credits
            
        except Exception as e:
            self.logger.error(f"Failed to calculate uptime credits: {e}")
            return 0


class WorkCreditsValidator:
    """Validates work credits proofs"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_bandwidth_proof(self, proof: BandwidthProof) -> bool:
        """Validate relay bandwidth proof"""
        try:
            # Check basic constraints
            if proof.bytes_transferred < 0:
                return False
            
            if proof.duration_seconds <= 0:
                return False
            
            # Check for reasonable bandwidth (max 1 GB/s)
            max_bandwidth = 1024 * 1024 * 1024  # 1 GB
            if proof.bytes_transferred / proof.duration_seconds > max_bandwidth:
                return False
            
            # Check timestamp is recent (within 1 hour)
            now = datetime.now(timezone.utc)
            if (now - proof.timestamp).total_seconds() > 3600:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate bandwidth proof: {e}")
            return False
    
    def validate_storage_proof(self, proof: StorageProof) -> bool:
        """Validate storage availability proof"""
        try:
            # Check basic constraints
            if proof.total_capacity_bytes <= 0:
                return False
            
            if proof.available_capacity_bytes < 0:
                return False
            
            if proof.available_capacity_bytes > proof.total_capacity_bytes:
                return False
            
            if proof.chunks_stored < 0:
                return False
            
            # Validate verification hash format
            if not proof.verification_hash or len(proof.verification_hash) != 64:
                return False
            
            # Check timestamp is recent (within 1 hour)
            now = datetime.now(timezone.utc)
            if (now - proof.timestamp).total_seconds() > 3600:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate storage proof: {e}")
            return False
    
    def validate_validation_proof(self, proof: ValidationProof) -> bool:
        """Validate validation signature proof"""
        try:
            # Check basic constraints
            if not proof.message_hash or len(proof.message_hash) != 64:
                return False
            
            if not proof.signature or len(proof.signature) == 0:
                return False
            
            if not proof.validator_address:
                return False
            
            if proof.validation_count < 0:
                return False
            
            # Check timestamp is recent (within 1 hour)
            now = datetime.now(timezone.utc)
            if (now - proof.timestamp).total_seconds() > 3600:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate validation proof: {e}")
            return False
    
    def validate_uptime_proof(self, proof: UptimeProof) -> bool:
        """Validate uptime beacon proof"""
        try:
            # Check basic constraints
            if not 0 <= proof.uptime_percentage <= 100:
                return False
            
            if proof.consecutive_uptime_hours < 0:
                return False
            
            # Check timestamp is recent (within 1 hour)
            now = datetime.now(timezone.utc)
            if (now - proof.timestamp).total_seconds() > 3600:
                return False
            
            # Check last heartbeat is recent (within 5 minutes)
            if (now - proof.last_heartbeat).total_seconds() > 300:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to validate uptime proof: {e}")
            return False


class WorkCreditsAggregator:
    """Aggregates work credits over time windows"""
    
    def __init__(self, window_hours: int = 24):
        self.window_hours = window_hours
        self.logger = logging.getLogger(__name__)
    
    def aggregate_credits(self, entries: List[WorkCreditsEntry]) -> Dict[str, int]:
        """
        Aggregate work credits by entity over time window.
        
        Args:
            entries: List of work credits entries
            
        Returns:
            Dictionary mapping entity_id -> total_credits
        """
        try:
            entity_credits: Dict[str, int] = {}
            window_start = datetime.now(timezone.utc).timestamp() - (self.window_hours * 3600)
            
            for entry in entries:
                # Filter by time window
                if entry.timestamp.timestamp() < window_start:
                    continue
                
                # Use pool_id if available, otherwise node_id
                entity_id = entry.pool_id if entry.pool_id else entry.node_id
                
                if entity_id not in entity_credits:
                    entity_credits[entity_id] = 0
                
                entity_credits[entity_id] += entry.credits_amount
            
            self.logger.info(f"Aggregated credits for {len(entity_credits)} entities over {self.window_hours}h window")
            return entity_credits
            
        except Exception as e:
            self.logger.error(f"Failed to aggregate credits: {e}")
            return {}
    
    def rank_entities(self, entity_credits: Dict[str, int]) -> List[Tuple[str, int]]:
        """
        Rank entities by total credits.
        
        Args:
            entity_credits: Dictionary mapping entity_id -> total_credits
            
        Returns:
            List of (entity_id, credits) tuples sorted by credits descending
        """
        try:
            # Sort by credits descending
            ranked = sorted(entity_credits.items(), key=lambda x: x[1], reverse=True)
            
            self.logger.info(f"Ranked {len(ranked)} entities by work credits")
            return ranked
            
        except Exception as e:
            self.logger.error(f"Failed to rank entities: {e}")
            return []


# Global instances
_calculator = WorkCreditsCalculator()
_validator = WorkCreditsValidator()
_aggregator = WorkCreditsAggregator()


def get_calculator() -> WorkCreditsCalculator:
    """Get global work credits calculator"""
    return _calculator


def get_validator() -> WorkCreditsValidator:
    """Get global work credits validator"""
    return _validator


def get_aggregator() -> WorkCreditsAggregator:
    """Get global work credits aggregator"""
    return _aggregator


if __name__ == "__main__":
    async def test_work_credits():
        """Test work credits system"""
        
        # Test bandwidth proof
        bandwidth_proof = BandwidthProof(
            bytes_transferred=100 * 1024 * 1024,  # 100 MB
            duration_seconds=10.0,  # 10 seconds
            timestamp=datetime.now(timezone.utc)
        )
        
        bandwidth_credits = _calculator.calculate_bandwidth_credits(bandwidth_proof)
        print(f"Bandwidth proof: {bandwidth_proof.bandwidth_mbps:.2f} MB/s -> {bandwidth_credits} credits")
        
        # Test storage proof
        storage_proof = StorageProof(
            total_capacity_bytes=1000 * 1024 * 1024 * 1024,  # 1 TB
            available_capacity_bytes=800 * 1024 * 1024 * 1024,  # 800 GB
            chunks_stored=150,
            verification_hash="a" * 64,
            timestamp=datetime.now(timezone.utc)
        )
        
        storage_credits = _calculator.calculate_storage_credits(storage_proof)
        print(f"Storage proof: {storage_proof.availability_ratio:.2f} availability -> {storage_credits} credits")
        
        # Test validation proof
        validation_proof = ValidationProof(
            message_hash="b" * 64,
            signature=b"test_signature",
            validator_address="0x1234567890123456789012345678901234567890",
            validation_count=25,
            timestamp=datetime.now(timezone.utc)
        )
        
        validation_credits = _calculator.calculate_validation_credits(validation_proof)
        print(f"Validation proof: {validation_proof.validation_count} validations -> {validation_credits} credits")
        
        # Test uptime proof
        uptime_proof = UptimeProof(
            uptime_percentage=99.5,
            consecutive_uptime_hours=168,  # 1 week
            last_heartbeat=datetime.now(timezone.utc),
            timestamp=datetime.now(timezone.utc)
        )
        
        uptime_credits = _calculator.calculate_uptime_credits(uptime_proof)
        print(f"Uptime proof: {uptime_proof.uptime_percentage}% uptime -> {uptime_credits} credits")
        
        # Test aggregation
        entries = [
            WorkCreditsEntry("node1", None, WorkCreditsType.RELAY_BANDWIDTH, bandwidth_credits, {}, datetime.now(timezone.utc)),
            WorkCreditsEntry("node1", None, WorkCreditsType.STORAGE_AVAILABILITY, storage_credits, {}, datetime.now(timezone.utc)),
            WorkCreditsEntry("node2", "pool1", WorkCreditsType.VALIDATION_SIGNATURE, validation_credits, {}, datetime.now(timezone.utc)),
            WorkCreditsEntry("node3", "pool1", WorkCreditsType.UPTIME_BEACON, uptime_credits, {}, datetime.now(timezone.utc)),
        ]
        
        entity_credits = _aggregator.aggregate_credits(entries)
        ranked = _aggregator.rank_entities(entity_credits)
        
        print(f"Aggregated credits: {entity_credits}")
        print(f"Ranked entities: {ranked}")
    
    # Run test
    asyncio.run(test_work_credits())
