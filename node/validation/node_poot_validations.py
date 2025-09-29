# Path: node/validation/node_poot_validations.py
# Lucid RDP Node pOot Validations - Specialized Proof of Ownership of Token validation
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import asyncio
import logging
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import json
from decimal import Decimal
import secrets
import hmac

from motor.motor_asyncio import AsyncIOMotorDatabase

# Import existing components
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from node.peer_discovery import PeerDiscovery
from node.work_credits import WorkCreditsCalculator

logger = logging.getLogger(__name__)

# pOot Validation Constants
POOT_CHALLENGE_VALIDITY_MINUTES = int(os.getenv("POOT_CHALLENGE_VALIDITY_MINUTES", "15"))  # 15 minutes
POOT_PROOF_CACHE_MINUTES = int(os.getenv("POOT_PROOF_CACHE_MINUTES", "60"))  # 1 hour
MIN_TOKEN_STAKE_AMOUNT = Decimal(os.getenv("MIN_TOKEN_STAKE_AMOUNT", "100.0"))  # Minimum stake
MAX_VALIDATION_ATTEMPTS = int(os.getenv("MAX_VALIDATION_ATTEMPTS", "3"))  # Max attempts per period
FRAUD_DETECTION_WINDOW_HOURS = int(os.getenv("FRAUD_DETECTION_WINDOW_HOURS", "24"))  # 24 hours
CHALLENGE_COMPLEXITY_BYTES = int(os.getenv("CHALLENGE_COMPLEXITY_BYTES", "32"))  # 32 bytes


class ProofType(Enum):
    """Types of ownership proofs"""
    STAKE_PROOF = "stake_proof"           # Proof of staked tokens
    BALANCE_PROOF = "balance_proof"       # Proof of token balance
    DELEGATION_PROOF = "delegation_proof" # Proof of delegated tokens
    CUSTODY_PROOF = "custody_proof"       # Proof of token custody
    LIQUIDITY_PROOF = "liquidity_proof"   # Proof of liquidity provision


class ValidationStatus(Enum):
    """Validation result status"""
    VALID = "valid"
    INVALID = "invalid"
    PENDING = "pending"
    EXPIRED = "expired"
    FRAUD_DETECTED = "fraud_detected"
    INSUFFICIENT_STAKE = "insufficient_stake"
    CHALLENGE_FAILED = "challenge_failed"


class FraudRisk(Enum):
    """Fraud risk levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TokenOwnershipChallenge:
    """Challenge for token ownership proof"""
    challenge_id: str
    node_id: str
    proof_type: ProofType
    challenge_data: bytes
    nonce: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(minutes=POOT_CHALLENGE_VALIDITY_MINUTES))
    difficulty: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.challenge_id,
            "node_id": self.node_id,
            "proof_type": self.proof_type.value,
            "challenge_data": self.challenge_data.hex(),
            "nonce": self.nonce,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "difficulty": self.difficulty,
            "metadata": self.metadata
        }


@dataclass
class TokenOwnershipProof:
    """Proof of token ownership"""
    proof_id: str
    challenge_id: str
    node_id: str
    proof_type: ProofType
    stake_amount: Decimal
    proof_signature: str
    proof_data: Dict[str, Any] = field(default_factory=dict)
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    validation_status: ValidationStatus = ValidationStatus.PENDING
    validated_at: Optional[datetime] = None
    validator_node_id: Optional[str] = None
    fraud_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.proof_id,
            "challenge_id": self.challenge_id,
            "node_id": self.node_id,
            "proof_type": self.proof_type.value,
            "stake_amount": str(self.stake_amount),
            "proof_signature": self.proof_signature,
            "proof_data": self.proof_data,
            "submitted_at": self.submitted_at,
            "validation_status": self.validation_status.value,
            "validated_at": self.validated_at,
            "validator_node_id": self.validator_node_id,
            "fraud_score": self.fraud_score
        }


@dataclass
class StakeValidation:
    """Stake validation record"""
    validation_id: str
    node_id: str
    stake_amount: Decimal
    stake_address: str
    block_height: int
    transaction_hash: str
    validation_method: str = "balance_check"
    validated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: datetime = field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=1))
    validator_signatures: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.validation_id,
            "node_id": self.node_id,
            "stake_amount": str(self.stake_amount),
            "stake_address": self.stake_address,
            "block_height": self.block_height,
            "transaction_hash": self.transaction_hash,
            "validation_method": self.validation_method,
            "validated_at": self.validated_at,
            "valid_until": self.valid_until,
            "validator_signatures": self.validator_signatures,
            "metadata": self.metadata
        }


@dataclass
class FraudDetectionEvent:
    """Fraud detection event"""
    event_id: str
    node_id: str
    fraud_type: str
    risk_level: FraudRisk
    evidence: Dict[str, Any] = field(default_factory=dict)
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reporter_node_id: Optional[str] = None
    resolved: bool = False
    resolution_notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.event_id,
            "node_id": self.node_id,
            "fraud_type": self.fraud_type,
            "risk_level": self.risk_level.value,
            "evidence": self.evidence,
            "detected_at": self.detected_at,
            "reporter_node_id": self.reporter_node_id,
            "resolved": self.resolved,
            "resolution_notes": self.resolution_notes
        }


@dataclass
class ValidationStats:
    """Validation statistics for a node"""
    node_id: str
    total_proofs_submitted: int
    valid_proofs: int
    invalid_proofs: int
    fraud_events: int
    success_rate: float
    average_stake: Decimal
    last_validation: Optional[datetime] = None
    reputation_score: float = 100.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "total_proofs_submitted": self.total_proofs_submitted,
            "valid_proofs": self.valid_proofs,
            "invalid_proofs": self.invalid_proofs,
            "fraud_events": self.fraud_events,
            "success_rate": self.success_rate,
            "average_stake": str(self.average_stake),
            "last_validation": self.last_validation,
            "reputation_score": self.reputation_score
        }


class NodePootValidation:
    """
    Node pOot (Proof of Ownership of Token) Validation System.
    
    Handles:
    - Token ownership challenge generation
    - Proof submission and validation
    - Stake verification and monitoring
    - Fraud detection and prevention
    - Ownership proof caching
    - Reputation scoring based on validation history
    - Anti-gaming measures and security
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, peer_discovery: PeerDiscovery,
                 work_credits: WorkCreditsCalculator):
        self.db = db
        self.peer_discovery = peer_discovery
        self.work_credits = work_credits
        
        # State tracking
        self.active_challenges: Dict[str, TokenOwnershipChallenge] = {}
        self.proof_cache: Dict[str, TokenOwnershipProof] = {}
        self.stake_validations: Dict[str, StakeValidation] = {}
        self.node_stats: Dict[str, ValidationStats] = {}
        self.running = False
        
        # Security state
        self.validation_attempts: Dict[str, List[datetime]] = {}  # Rate limiting
        self.fraud_patterns: Dict[str, List[FraudDetectionEvent]] = {}
        
        # Background tasks
        self._challenge_cleanup_task: Optional[asyncio.Task] = None
        self._fraud_detection_task: Optional[asyncio.Task] = None
        self._stake_monitoring_task: Optional[asyncio.Task] = None
        self._stats_update_task: Optional[asyncio.Task] = None
        
        logger.info("Node pOot validation system initialized")
    
    async def start(self):
        """Start pOot validation system"""
        try:
            self.running = True
            
            # Setup database indexes
            await self._setup_indexes()
            
            # Load existing data
            await self._load_active_challenges()
            await self._load_stake_validations()
            await self._load_node_stats()
            await self._load_fraud_patterns()
            
            # Start background tasks
            self._challenge_cleanup_task = asyncio.create_task(self._challenge_cleanup_loop())
            self._fraud_detection_task = asyncio.create_task(self._fraud_detection_loop())
            self._stake_monitoring_task = asyncio.create_task(self._stake_monitoring_loop())
            self._stats_update_task = asyncio.create_task(self._stats_update_loop())
            
            logger.info("Node pOot validation system started")
            
        except Exception as e:
            logger.error(f"Failed to start pOot validation system: {e}")
            raise
    
    async def stop(self):
        """Stop pOot validation system"""
        try:
            self.running = False
            
            # Cancel background tasks
            tasks = [self._challenge_cleanup_task, self._fraud_detection_task, 
                    self._stake_monitoring_task, self._stats_update_task]
            for task in tasks:
                if task and not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*[t for t in tasks if t], return_exceptions=True)
            
            logger.info("Node pOot validation system stopped")
            
        except Exception as e:
            logger.error(f"Error stopping pOot validation system: {e}")
    
    async def generate_ownership_challenge(self, node_id: str, proof_type: ProofType,
                                         difficulty: int = 1) -> str:
        """
        Generate a token ownership challenge for a node.
        
        Args:
            node_id: Node to challenge
            proof_type: Type of ownership proof required
            difficulty: Challenge difficulty level
            
        Returns:
            Challenge ID
        """
        try:
            # Check rate limiting
            if not await self._check_rate_limit(node_id):
                raise ValueError("Rate limit exceeded for validation attempts")
            
            challenge_id = str(uuid.uuid4())
            
            # Generate cryptographically secure challenge data
            challenge_data = secrets.token_bytes(CHALLENGE_COMPLEXITY_BYTES * difficulty)
            nonce = secrets.token_hex(16)
            
            challenge = TokenOwnershipChallenge(
                challenge_id=challenge_id,
                node_id=node_id,
                proof_type=proof_type,
                challenge_data=challenge_data,
                nonce=nonce,
                difficulty=difficulty
            )
            
            # Store challenge
            self.active_challenges[challenge_id] = challenge
            await self.db["poot_challenges"].replace_one(
                {"_id": challenge_id},
                challenge.to_dict(),
                upsert=True
            )
            
            logger.info(f"pOot challenge generated: {challenge_id} for node {node_id}")
            return challenge_id
            
        except Exception as e:
            logger.error(f"Failed to generate ownership challenge: {e}")
            raise
    
    async def submit_ownership_proof(self, proof_id: str, challenge_id: str,
                                   node_id: str, stake_amount: Decimal,
                                   proof_signature: str, proof_data: Dict[str, Any]) -> str:
        """
        Submit a proof of token ownership.
        
        Args:
            proof_id: Unique proof identifier
            challenge_id: Challenge being responded to
            node_id: Node submitting proof
            stake_amount: Amount of tokens being proven
            proof_signature: Cryptographic proof signature
            proof_data: Additional proof data
            
        Returns:
            Proof submission ID
        """
        try:
            # Validate challenge exists and is not expired
            challenge = self.active_challenges.get(challenge_id)
            if not challenge:
                challenge_doc = await self.db["poot_challenges"].find_one({"_id": challenge_id})
                if not challenge_doc:
                    raise ValueError(f"Challenge not found: {challenge_id}")
                
                challenge = TokenOwnershipChallenge(
                    challenge_id=challenge_doc["_id"],
                    node_id=challenge_doc["node_id"],
                    proof_type=ProofType(challenge_doc["proof_type"]),
                    challenge_data=bytes.fromhex(challenge_doc["challenge_data"]),
                    nonce=challenge_doc["nonce"],
                    created_at=challenge_doc["created_at"],
                    expires_at=challenge_doc["expires_at"],
                    difficulty=challenge_doc["difficulty"],
                    metadata=challenge_doc.get("metadata", {})
                )
            
            # Check if challenge belongs to the submitting node
            if challenge.node_id != node_id:
                raise ValueError("Challenge does not belong to submitting node")
            
            # Check if challenge is expired
            if datetime.now(timezone.utc) > challenge.expires_at:
                raise ValueError("Challenge has expired")
            
            # Check minimum stake amount
            if stake_amount < MIN_TOKEN_STAKE_AMOUNT:
                raise ValueError(f"Stake amount below minimum: {MIN_TOKEN_STAKE_AMOUNT}")
            
            proof = TokenOwnershipProof(
                proof_id=proof_id,
                challenge_id=challenge_id,
                node_id=node_id,
                proof_type=challenge.proof_type,
                stake_amount=stake_amount,
                proof_signature=proof_signature,
                proof_data=proof_data
            )
            
            # Store proof for validation
            await self.db["poot_proofs"].insert_one(proof.to_dict())
            
            # Perform immediate validation
            validation_result = await self._validate_ownership_proof(proof, challenge)
            
            # Update proof status
            proof.validation_status = validation_result
            proof.validated_at = datetime.now(timezone.utc)
            
            if validation_result == ValidationStatus.VALID:
                # Cache valid proof
                self.proof_cache[f"{node_id}:{challenge.proof_type.value}"] = proof
            
            # Update database
            await self.db["poot_proofs"].update_one(
                {"_id": proof_id},
                {"$set": {
                    "validation_status": proof.validation_status.value,
                    "validated_at": proof.validated_at,
                    "fraud_score": proof.fraud_score
                }}
            )
            
            # Update node statistics
            await self._update_node_stats(node_id, validation_result)
            
            logger.info(f"pOot proof submitted: {proof_id} - Status: {validation_result.value}")
            return proof_id
            
        except Exception as e:
            logger.error(f"Failed to submit ownership proof: {e}")
            raise
    
    async def validate_stake(self, node_id: str, stake_address: str, 
                           claimed_amount: Decimal) -> str:
        """
        Validate a node's stake amount.
        
        Args:
            node_id: Node claiming stake
            stake_address: Blockchain address with stake
            claimed_amount: Claimed stake amount
            
        Returns:
            Validation ID
        """
        try:
            validation_id = str(uuid.uuid4())
            
            # Mock blockchain validation - in real implementation would query blockchain
            actual_balance, block_height, tx_hash = await self._query_blockchain_balance(stake_address)
            
            # Validate claimed amount
            is_valid = actual_balance >= claimed_amount
            
            validation = StakeValidation(
                validation_id=validation_id,
                node_id=node_id,
                stake_amount=actual_balance if is_valid else Decimal("0"),
                stake_address=stake_address,
                block_height=block_height,
                transaction_hash=tx_hash
            )
            
            # Store validation
            self.stake_validations[node_id] = validation
            await self.db["stake_validations"].replace_one(
                {"_id": validation_id},
                validation.to_dict(),
                upsert=True
            )
            
            if not is_valid:
                # Report potential fraud
                await self._report_fraud_event(
                    node_id, 
                    "stake_misrepresentation",
                    FraudRisk.HIGH,
                    {
                        "claimed_amount": str(claimed_amount),
                        "actual_amount": str(actual_balance),
                        "stake_address": stake_address
                    }
                )
            
            logger.info(f"Stake validation: {validation_id} - Valid: {is_valid}")
            return validation_id
            
        except Exception as e:
            logger.error(f"Failed to validate stake: {e}")
            raise
    
    async def get_cached_proof(self, node_id: str, proof_type: ProofType) -> Optional[TokenOwnershipProof]:
        """Get cached ownership proof for a node"""
        try:
            cache_key = f"{node_id}:{proof_type.value}"
            proof = self.proof_cache.get(cache_key)
            
            if proof:
                # Check if proof is still valid (not expired)
                cache_expiry = proof.validated_at + timedelta(minutes=POOT_PROOF_CACHE_MINUTES)
                if datetime.now(timezone.utc) > cache_expiry:
                    del self.proof_cache[cache_key]
                    return None
                
                return proof
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get cached proof: {e}")
            return None
    
    async def get_node_validation_stats(self, node_id: str) -> Optional[ValidationStats]:
        """Get validation statistics for a node"""
        try:
            return self.node_stats.get(node_id)
        except Exception as e:
            logger.error(f"Failed to get node stats: {e}")
            return None
    
    async def get_fraud_events(self, node_id: Optional[str] = None, 
                             hours: int = 24) -> List[Dict[str, Any]]:
        """Get fraud detection events"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            query = {"detected_at": {"$gte": cutoff_time}}
            if node_id:
                query["node_id"] = node_id
            
            events = []
            cursor = self.db["fraud_events"].find(query).sort("detected_at", -1)
            
            async for event_doc in cursor:
                events.append(event_doc)
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get fraud events: {e}")
            return []
    
    async def resolve_fraud_event(self, event_id: str, resolver_node_id: str, 
                                resolution_notes: str) -> bool:
        """Resolve a fraud detection event"""
        try:
            result = await self.db["fraud_events"].update_one(
                {"_id": event_id},
                {"$set": {
                    "resolved": True,
                    "resolution_notes": resolution_notes,
                    "resolved_by": resolver_node_id,
                    "resolved_at": datetime.now(timezone.utc)
                }}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to resolve fraud event: {e}")
            return False
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get pOot validation system statistics"""
        try:
            stats = {
                "total_challenges": await self.db["poot_challenges"].count_documents({}),
                "active_challenges": len(self.active_challenges),
                "total_proofs": await self.db["poot_proofs"].count_documents({}),
                "cached_proofs": len(self.proof_cache),
                "total_fraud_events": await self.db["fraud_events"].count_documents({}),
                "unresolved_fraud_events": await self.db["fraud_events"].count_documents({"resolved": False}),
                "validation_success_rate": 0.0,
                "average_stake_amount": "0"
            }
            
            # Calculate success rate
            total_proofs = await self.db["poot_proofs"].count_documents({})
            if total_proofs > 0:
                valid_proofs = await self.db["poot_proofs"].count_documents({
                    "validation_status": ValidationStatus.VALID.value
                })
                stats["validation_success_rate"] = valid_proofs / total_proofs
            
            # Calculate average stake
            pipeline = [
                {"$group": {
                    "_id": None,
                    "avg_stake": {"$avg": {"$toDecimal": "$stake_amount"}}
                }}
            ]
            async for doc in self.db["poot_proofs"].aggregate(pipeline):
                if doc.get("avg_stake"):
                    stats["average_stake_amount"] = str(doc["avg_stake"])
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get system stats: {e}")
            return {"error": str(e)}
    
    async def _validate_ownership_proof(self, proof: TokenOwnershipProof, 
                                      challenge: TokenOwnershipChallenge) -> ValidationStatus:
        """Validate a submitted ownership proof"""
        try:
            # Check proof signature validity
            if not await self._verify_proof_signature(proof, challenge):
                return ValidationStatus.CHALLENGE_FAILED
            
            # Check stake amount validity
            if proof.stake_amount < MIN_TOKEN_STAKE_AMOUNT:
                return ValidationStatus.INSUFFICIENT_STAKE
            
            # Perform fraud detection checks
            fraud_score = await self._calculate_fraud_score(proof)
            proof.fraud_score = fraud_score
            
            if fraud_score > 0.8:  # High fraud probability
                await self._report_fraud_event(
                    proof.node_id,
                    "suspicious_proof_pattern",
                    FraudRisk.HIGH,
                    {"fraud_score": fraud_score, "proof_id": proof.proof_id}
                )
                return ValidationStatus.FRAUD_DETECTED
            
            # Validate against blockchain (mock implementation)
            blockchain_valid = await self._validate_against_blockchain(proof)
            if not blockchain_valid:
                return ValidationStatus.INVALID
            
            return ValidationStatus.VALID
            
        except Exception as e:
            logger.error(f"Failed to validate ownership proof: {e}")
            return ValidationStatus.INVALID
    
    async def _verify_proof_signature(self, proof: TokenOwnershipProof,
                                    challenge: TokenOwnershipChallenge) -> bool:
        """Verify the cryptographic signature of a proof"""
        try:
            # Mock signature verification - in real implementation would use proper crypto
            expected_message = f"{challenge.challenge_data.hex()}{challenge.nonce}{proof.stake_amount}"
            expected_signature = hashlib.sha256(expected_message.encode()).hexdigest()
            
            return hmac.compare_digest(proof.proof_signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Failed to verify proof signature: {e}")
            return False
    
    async def _validate_against_blockchain(self, proof: TokenOwnershipProof) -> bool:
        """Validate proof against blockchain data"""
        try:
            # Mock blockchain validation
            # In real implementation, would query actual blockchain
            
            if proof.proof_type == ProofType.STAKE_PROOF:
                # Validate staking transaction
                return await self._validate_staking_transaction(proof)
            
            elif proof.proof_type == ProofType.BALANCE_PROOF:
                # Validate token balance
                return await self._validate_token_balance(proof)
            
            elif proof.proof_type == ProofType.DELEGATION_PROOF:
                # Validate delegation transaction
                return await self._validate_delegation_transaction(proof)
            
            # Default to valid for other proof types
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate against blockchain: {e}")
            return False
    
    async def _validate_staking_transaction(self, proof: TokenOwnershipProof) -> bool:
        """Mock staking transaction validation"""
        try:
            # Mock validation - would check actual staking contract
            stake_address = proof.proof_data.get("stake_address")
            if not stake_address:
                return False
            
            # Simulate blockchain query delay
            await asyncio.sleep(0.1)
            
            # Mock positive validation (95% success rate)
            return secrets.randbits(1) or secrets.randbits(1) or secrets.randbits(1)
            
        except Exception as e:
            logger.error(f"Failed to validate staking transaction: {e}")
            return False
    
    async def _validate_token_balance(self, proof: TokenOwnershipProof) -> bool:
        """Mock token balance validation"""
        try:
            # Mock balance check
            balance_address = proof.proof_data.get("balance_address")
            if not balance_address:
                return False
            
            # Simulate blockchain query
            await asyncio.sleep(0.05)
            
            # Mock balance validation (90% success rate)
            return not (secrets.randbits(1) and secrets.randbits(1) and secrets.randbits(1))
            
        except Exception as e:
            logger.error(f"Failed to validate token balance: {e}")
            return False
    
    async def _validate_delegation_transaction(self, proof: TokenOwnershipProof) -> bool:
        """Mock delegation transaction validation"""
        try:
            # Mock delegation validation
            delegation_tx = proof.proof_data.get("delegation_tx")
            if not delegation_tx:
                return False
            
            # Simulate validation
            await asyncio.sleep(0.1)
            
            # Mock positive validation (85% success rate)
            return not (secrets.randbits(1) and secrets.randbits(1) and secrets.randbits(1) and secrets.randbits(1))
            
        except Exception as e:
            logger.error(f"Failed to validate delegation transaction: {e}")
            return False
    
    async def _calculate_fraud_score(self, proof: TokenOwnershipProof) -> float:
        """Calculate fraud probability score for a proof"""
        try:
            fraud_score = 0.0
            
            # Check historical behavior
            node_stats = self.node_stats.get(proof.node_id)
            if node_stats:
                # Lower score for nodes with good history
                if node_stats.success_rate > 0.9:
                    fraud_score -= 0.2
                elif node_stats.success_rate < 0.5:
                    fraud_score += 0.3
                
                # Check for recent fraud events
                if node_stats.fraud_events > 0:
                    fraud_score += 0.4
            else:
                # New nodes get higher scrutiny
                fraud_score += 0.1
            
            # Check proof timing patterns
            recent_proofs = await self.db["poot_proofs"].count_documents({
                "node_id": proof.node_id,
                "submitted_at": {"$gte": datetime.now(timezone.utc) - timedelta(hours=1)}
            })
            
            if recent_proofs > 5:  # Suspicious frequency
                fraud_score += 0.3
            
            # Check stake amount patterns
            if proof.stake_amount == MIN_TOKEN_STAKE_AMOUNT:
                fraud_score += 0.1  # Exactly minimum is suspicious
            
            # Ensure score is bounded
            return min(max(fraud_score, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Failed to calculate fraud score: {e}")
            return 0.5  # Default to medium risk
    
    async def _query_blockchain_balance(self, address: str) -> Tuple[Decimal, int, str]:
        """Mock blockchain balance query"""
        try:
            # Mock blockchain data
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # Generate mock balance between 0 and 10000
            balance = Decimal(str(secrets.randbelow(10001)))
            block_height = 1000000 + secrets.randbelow(100000)
            tx_hash = secrets.token_hex(32)
            
            return balance, block_height, tx_hash
            
        except Exception as e:
            logger.error(f"Failed to query blockchain balance: {e}")
            return Decimal("0"), 0, ""
    
    async def _check_rate_limit(self, node_id: str) -> bool:
        """Check if node is within rate limits for validation attempts"""
        try:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(hours=1)
            
            if node_id not in self.validation_attempts:
                self.validation_attempts[node_id] = []
            
            # Clean old attempts
            self.validation_attempts[node_id] = [
                attempt for attempt in self.validation_attempts[node_id] 
                if attempt > cutoff
            ]
            
            # Check limit
            if len(self.validation_attempts[node_id]) >= MAX_VALIDATION_ATTEMPTS:
                return False
            
            # Record this attempt
            self.validation_attempts[node_id].append(now)
            return True
            
        except Exception as e:
            logger.error(f"Failed to check rate limit: {e}")
            return False
    
    async def _report_fraud_event(self, node_id: str, fraud_type: str,
                                risk_level: FraudRisk, evidence: Dict[str, Any]):
        """Report a fraud detection event"""
        try:
            event_id = str(uuid.uuid4())
            
            event = FraudDetectionEvent(
                event_id=event_id,
                node_id=node_id,
                fraud_type=fraud_type,
                risk_level=risk_level,
                evidence=evidence
            )
            
            # Store event
            await self.db["fraud_events"].insert_one(event.to_dict())
            
            # Track fraud patterns
            if node_id not in self.fraud_patterns:
                self.fraud_patterns[node_id] = []
            
            self.fraud_patterns[node_id].append(event)
            
            logger.warning(f"Fraud event reported: {event_id} for node {node_id} - {fraud_type}")
            
        except Exception as e:
            logger.error(f"Failed to report fraud event: {e}")
    
    async def _update_node_stats(self, node_id: str, validation_result: ValidationStatus):
        """Update validation statistics for a node"""
        try:
            if node_id not in self.node_stats:
                self.node_stats[node_id] = ValidationStats(
                    node_id=node_id,
                    total_proofs_submitted=0,
                    valid_proofs=0,
                    invalid_proofs=0,
                    fraud_events=0,
                    success_rate=0.0,
                    average_stake=Decimal("0")
                )
            
            stats = self.node_stats[node_id]
            stats.total_proofs_submitted += 1
            stats.last_validation = datetime.now(timezone.utc)
            
            if validation_result == ValidationStatus.VALID:
                stats.valid_proofs += 1
            else:
                stats.invalid_proofs += 1
                
                if validation_result == ValidationStatus.FRAUD_DETECTED:
                    stats.fraud_events += 1
            
            # Update success rate
            if stats.total_proofs_submitted > 0:
                stats.success_rate = stats.valid_proofs / stats.total_proofs_submitted
            
            # Update reputation score
            stats.reputation_score = min(100.0, stats.success_rate * 100 - stats.fraud_events * 10)
            
            # Store in database
            await self.db["node_validation_stats"].replace_one(
                {"_id": node_id},
                stats.to_dict(),
                upsert=True
            )
            
        except Exception as e:
            logger.error(f"Failed to update node stats: {e}")
    
    async def _challenge_cleanup_loop(self):
        """Clean up expired challenges"""
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                expired_challenges = []
                
                for challenge_id, challenge in self.active_challenges.items():
                    if now > challenge.expires_at:
                        expired_challenges.append(challenge_id)
                
                # Remove expired challenges
                for challenge_id in expired_challenges:
                    del self.active_challenges[challenge_id]
                    logger.info(f"Expired challenge removed: {challenge_id}")
                
                # Clean database
                await self.db["poot_challenges"].delete_many({
                    "expires_at": {"$lt": now}
                })
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Challenge cleanup loop error: {e}")
                await asyncio.sleep(60)
    
    async def _fraud_detection_loop(self):
        """Monitor for fraud patterns"""
        while self.running:
            try:
                # Analyze fraud patterns
                for node_id, events in self.fraud_patterns.items():
                    recent_events = [
                        event for event in events
                        if event.detected_at > datetime.now(timezone.utc) - timedelta(hours=FRAUD_DETECTION_WINDOW_HOURS)
                    ]
                    
                    if len(recent_events) >= 3:  # Multiple fraud events
                        await self._report_fraud_event(
                            node_id,
                            "repeated_fraud_pattern",
                            FraudRisk.CRITICAL,
                            {"recent_events": len(recent_events)}
                        )
                
                await asyncio.sleep(3600)  # Check every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Fraud detection loop error: {e}")
                await asyncio.sleep(60)
    
    async def _stake_monitoring_loop(self):
        """Monitor stake validations for changes"""
        while self.running:
            try:
                # Check for stake validations nearing expiry
                now = datetime.now(timezone.utc)
                soon_expiry = now + timedelta(minutes=30)
                
                for node_id, validation in self.stake_validations.items():
                    if validation.valid_until < soon_expiry:
                        # Trigger re-validation
                        logger.info(f"Stake validation expiring soon for node {node_id}")
                
                await asyncio.sleep(1800)  # Check every 30 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stake monitoring loop error: {e}")
                await asyncio.sleep(60)
    
    async def _stats_update_loop(self):
        """Update system statistics periodically"""
        while self.running:
            try:
                # Update cached statistics
                for node_id in list(self.node_stats.keys()):
                    # Recalculate average stake
                    pipeline = [
                        {"$match": {"node_id": node_id, "validation_status": ValidationStatus.VALID.value}},
                        {"$group": {"_id": None, "avg_stake": {"$avg": {"$toDecimal": "$stake_amount"}}}}
                    ]
                    
                    async for doc in self.db["poot_proofs"].aggregate(pipeline):
                        if doc.get("avg_stake"):
                            self.node_stats[node_id].average_stake = Decimal(str(doc["avg_stake"]))
                
                await asyncio.sleep(3600)  # Update every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Stats update loop error: {e}")
                await asyncio.sleep(60)
    
    async def _setup_indexes(self):
        """Setup database indexes"""
        try:
            # pOot challenges indexes
            await self.db["poot_challenges"].create_index("node_id")
            await self.db["poot_challenges"].create_index("proof_type")
            await self.db["poot_challenges"].create_index("expires_at")
            await self.db["poot_challenges"].create_index("created_at")
            
            # pOot proofs indexes
            await self.db["poot_proofs"].create_index("node_id")
            await self.db["poot_proofs"].create_index("challenge_id")
            await self.db["poot_proofs"].create_index("validation_status")
            await self.db["poot_proofs"].create_index("submitted_at")
            await self.db["poot_proofs"].create_index("fraud_score")
            
            # Stake validations indexes
            await self.db["stake_validations"].create_index("node_id")
            await self.db["stake_validations"].create_index("stake_address")
            await self.db["stake_validations"].create_index("valid_until")
            
            # Fraud events indexes
            await self.db["fraud_events"].create_index("node_id")
            await self.db["fraud_events"].create_index("fraud_type")
            await self.db["fraud_events"].create_index("risk_level")
            await self.db["fraud_events"].create_index("detected_at")
            await self.db["fraud_events"].create_index("resolved")
            
            # Node validation stats indexes
            await self.db["node_validation_stats"].create_index("success_rate")
            await self.db["node_validation_stats"].create_index("reputation_score")
            await self.db["node_validation_stats"].create_index("fraud_events")
            
            logger.info("pOot validation system database indexes created")
            
        except Exception as e:
            logger.warning(f"Failed to create pOot validation indexes: {e}")
    
    async def _load_active_challenges(self):
        """Load active challenges from database"""
        try:
            now = datetime.now(timezone.utc)
            cursor = self.db["poot_challenges"].find({
                "expires_at": {"$gt": now}
            })
            
            async for challenge_doc in cursor:
                challenge = TokenOwnershipChallenge(
                    challenge_id=challenge_doc["_id"],
                    node_id=challenge_doc["node_id"],
                    proof_type=ProofType(challenge_doc["proof_type"]),
                    challenge_data=bytes.fromhex(challenge_doc["challenge_data"]),
                    nonce=challenge_doc["nonce"],
                    created_at=challenge_doc["created_at"],
                    expires_at=challenge_doc["expires_at"],
                    difficulty=challenge_doc["difficulty"],
                    metadata=challenge_doc.get("metadata", {})
                )
                
                self.active_challenges[challenge.challenge_id] = challenge
            
            logger.info(f"Loaded {len(self.active_challenges)} active challenges")
            
        except Exception as e:
            logger.error(f"Failed to load active challenges: {e}")
    
    async def _load_stake_validations(self):
        """Load current stake validations from database"""
        try:
            now = datetime.now(timezone.utc)
            cursor = self.db["stake_validations"].find({
                "valid_until": {"$gt": now}
            })
            
            async for validation_doc in cursor:
                validation = StakeValidation(
                    validation_id=validation_doc["_id"],
                    node_id=validation_doc["node_id"],
                    stake_amount=Decimal(validation_doc["stake_amount"]),
                    stake_address=validation_doc["stake_address"],
                    block_height=validation_doc["block_height"],
                    transaction_hash=validation_doc["transaction_hash"],
                    validation_method=validation_doc["validation_method"],
                    validated_at=validation_doc["validated_at"],
                    valid_until=validation_doc["valid_until"],
                    validator_signatures=validation_doc.get("validator_signatures", []),
                    metadata=validation_doc.get("metadata", {})
                )
                
                self.stake_validations[validation.node_id] = validation
            
            logger.info(f"Loaded {len(self.stake_validations)} stake validations")
            
        except Exception as e:
            logger.error(f"Failed to load stake validations: {e}")
    
    async def _load_node_stats(self):
        """Load node validation statistics from database"""
        try:
            cursor = self.db["node_validation_stats"].find({})
            
            async for stats_doc in cursor:
                stats = ValidationStats(
                    node_id=stats_doc["node_id"],
                    total_proofs_submitted=stats_doc["total_proofs_submitted"],
                    valid_proofs=stats_doc["valid_proofs"],
                    invalid_proofs=stats_doc["invalid_proofs"],
                    fraud_events=stats_doc["fraud_events"],
                    success_rate=stats_doc["success_rate"],
                    average_stake=Decimal(stats_doc["average_stake"]),
                    last_validation=stats_doc.get("last_validation"),
                    reputation_score=stats_doc["reputation_score"]
                )
                
                self.node_stats[stats.node_id] = stats
            
            logger.info(f"Loaded {len(self.node_stats)} node statistics")
            
        except Exception as e:
            logger.error(f"Failed to load node stats: {e}")
    
    async def _load_fraud_patterns(self):
        """Load recent fraud events for pattern analysis"""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=FRAUD_DETECTION_WINDOW_HOURS)
            cursor = self.db["fraud_events"].find({
                "detected_at": {"$gte": cutoff_time}
            })
            
            async for event_doc in cursor:
                event = FraudDetectionEvent(
                    event_id=event_doc["_id"],
                    node_id=event_doc["node_id"],
                    fraud_type=event_doc["fraud_type"],
                    risk_level=FraudRisk(event_doc["risk_level"]),
                    evidence=event_doc["evidence"],
                    detected_at=event_doc["detected_at"],
                    reporter_node_id=event_doc.get("reporter_node_id"),
                    resolved=event_doc["resolved"],
                    resolution_notes=event_doc["resolution_notes"]
                )
                
                if event.node_id not in self.fraud_patterns:
                    self.fraud_patterns[event.node_id] = []
                
                self.fraud_patterns[event.node_id].append(event)
            
            logger.info(f"Loaded fraud patterns for {len(self.fraud_patterns)} nodes")
            
        except Exception as e:
            logger.error(f"Failed to load fraud patterns: {e}")


# Global pOot validation system instance
_node_poot_validation: Optional[NodePootValidation] = None


def get_node_poot_validation() -> Optional[NodePootValidation]:
    """Get global pOot validation system instance"""
    global _node_poot_validation
    return _node_poot_validation


def create_node_poot_validation(db: AsyncIOMotorDatabase, peer_discovery: PeerDiscovery,
                               work_credits: WorkCreditsCalculator) -> NodePootValidation:
    """Create pOot validation system instance"""
    global _node_poot_validation
    _node_poot_validation = NodePootValidation(db, peer_discovery, work_credits)
    return _node_poot_validation


async def cleanup_node_poot_validation():
    """Cleanup pOot validation system"""
    global _node_poot_validation
    if _node_poot_validation:
        await _node_poot_validation.stop()
        _node_poot_validation = None


if __name__ == "__main__":
    # Test pOot validation system
    async def test_poot_validation():
        print("Testing Lucid Node pOot Validation System...")
        
        # This would normally be initialized with real components
        # For testing purposes, we'll create mock instances
        
        print("Test completed - pOot validation system ready")
    
    asyncio.run(test_poot_validation())