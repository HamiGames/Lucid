#!/usr/bin/env python3
"""
Lucid Node Management - PoOT (Proof of Ownership of Token) Calculator
Implements PoOT calculation for node ownership verification
"""

import asyncio
import logging
import hashlib
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from decimal import Decimal
import secrets
import hmac

from .database_adapter import DatabaseAdapter
from .models import PoOTProof, NodeInfo

logger = logging.getLogger(__name__)

# PoOT Configuration
POOT_CHALLENGE_VALIDITY_MINUTES = int(os.getenv("POOT_CHALLENGE_VALIDITY_MINUTES", "15"))
POOT_PROOF_CACHE_MINUTES = int(os.getenv("POOT_PROOF_CACHE_MINUTES", "60"))
MIN_TOKEN_STAKE_AMOUNT = Decimal(os.getenv("MIN_TOKEN_STAKE_AMOUNT", "100.0"))
MAX_VALIDATION_ATTEMPTS = int(os.getenv("MAX_VALIDATION_ATTEMPTS", "3"))
CHALLENGE_COMPLEXITY_BYTES = int(os.getenv("CHALLENGE_COMPLEXITY_BYTES", "32"))

class PoOTCalculator:
    """
    PoOT (Proof of Ownership of Token) Calculator
    
    Handles:
    - Token ownership verification
    - Stake amount validation
    - Challenge generation and validation
    - Proof caching and expiration
    - Fraud detection and prevention
    """
    
    def __init__(self, db_adapter: DatabaseAdapter):
        self.db = db_adapter
        self.active_challenges: Dict[str, Dict[str, Any]] = {}
        self.proof_cache: Dict[str, PoOTProof] = {}
        self.fraud_detection: Dict[str, List[datetime]] = {}
        
        logger.info("PoOT Calculator initialized")
    
    async def calculate_poot(self, node_id: str) -> Optional[PoOTProof]:
        """
        Calculate PoOT proof for a specific node
        
        Args:
            node_id: Node identifier
            
        Returns:
            PoOTProof object if successful, None otherwise
        """
        try:
            logger.info(f"Calculating PoOT for node {node_id}")
            
            # Check cache first
            if node_id in self.proof_cache:
                cached_proof = self.proof_cache[node_id]
                if self._is_proof_valid(cached_proof):
                    logger.info(f"Using cached PoOT proof for node {node_id}")
                    return cached_proof
                else:
                    # Remove expired proof
                    del self.proof_cache[node_id]
            
            # Get node information
            node_info = await self._get_node_info(node_id)
            if not node_info:
                logger.warning(f"Node {node_id} not found")
                return None
            
            # Validate node has sufficient stake
            if not await self._validate_stake_amount(node_info):
                logger.warning(f"Node {node_id} has insufficient stake")
                return None
            
            # Generate challenge
            challenge = await self._generate_challenge(node_id)
            if not challenge:
                logger.error(f"Failed to generate challenge for node {node_id}")
                return None
            
            # Calculate proof
            proof_data = await self._calculate_proof(node_info, challenge)
            if not proof_data:
                logger.error(f"Failed to calculate proof for node {node_id}")
                return None
            
            # Create PoOT proof
            proof = PoOTProof(
                node_id=node_id,
                proof_type="stake_proof",
                stake_amount=node_info.stake_amount,
                challenge=challenge["challenge"],
                proof_hash=proof_data["proof_hash"],
                signature=proof_data["signature"],
                timestamp=datetime.now(timezone.utc),
                valid_until=datetime.now(timezone.utc) + timedelta(minutes=POOT_PROOF_CACHE_MINUTES),
                confidence_score=proof_data["confidence_score"]
            )
            
            # Cache the proof
            self.proof_cache[node_id] = proof
            
            # Store in database
            await self._store_proof(proof)
            
            logger.info(f"PoOT proof calculated successfully for node {node_id}")
            return proof
            
        except Exception as e:
            logger.error(f"Error calculating PoOT for node {node_id}: {e}")
            return None
    
    async def calculate_all_poots(self) -> Dict[str, Any]:
        """
        Calculate PoOT proofs for all active nodes
        
        Returns:
            Dictionary with calculation results
        """
        try:
            logger.info("Calculating PoOT proofs for all nodes")
            
            # Get all active nodes
            nodes = await self._get_all_active_nodes()
            if not nodes:
                logger.warning("No active nodes found")
                return {"success": True, "processed": 0, "results": []}
            
            results = []
            successful = 0
            failed = 0
            
            for node in nodes:
                try:
                    proof = await self.calculate_poot(node.node_id)
                    if proof:
                        results.append({
                            "node_id": node.node_id,
                            "status": "success",
                            "proof": proof.to_dict()
                        })
                        successful += 1
                    else:
                        results.append({
                            "node_id": node.node_id,
                            "status": "failed",
                            "error": "Proof calculation failed"
                        })
                        failed += 1
                except Exception as e:
                    logger.error(f"Error calculating PoOT for node {node.node_id}: {e}")
                    results.append({
                        "node_id": node.node_id,
                        "status": "error",
                        "error": str(e)
                    })
                    failed += 1
            
            logger.info(f"PoOT calculation completed: {successful} successful, {failed} failed")
            return {
                "success": True,
                "processed": len(nodes),
                "successful": successful,
                "failed": failed,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error in calculate_all_poots: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_poot_proof(self, node_id: str) -> Optional[PoOTProof]:
        """
        Get PoOT proof for a specific node
        
        Args:
            node_id: Node identifier
            
        Returns:
            PoOTProof object if found and valid, None otherwise
        """
        try:
            # Check cache first
            if node_id in self.proof_cache:
                cached_proof = self.proof_cache[node_id]
                if self._is_proof_valid(cached_proof):
                    return cached_proof
                else:
                    del self.proof_cache[node_id]
            
            # Load from database
            proof = await self._load_proof(node_id)
            if proof and self._is_proof_valid(proof):
                # Cache the proof
                self.proof_cache[node_id] = proof
                return proof
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting PoOT proof for node {node_id}: {e}")
            return None
    
    async def validate_proof(self, node_id: str, proof: PoOTProof) -> bool:
        """
        Validate a PoOT proof
        
        Args:
            node_id: Node identifier
            proof: PoOT proof to validate
            
        Returns:
            True if proof is valid, False otherwise
        """
        try:
            # Check if proof is expired
            if not self._is_proof_valid(proof):
                logger.warning(f"PoOT proof for node {node_id} is expired")
                return False
            
            # Verify proof signature
            if not await self._verify_proof_signature(proof):
                logger.warning(f"PoOT proof signature for node {node_id} is invalid")
                return False
            
            # Check fraud detection
            if await self._check_fraud_detection(node_id):
                logger.warning(f"Fraud detected for node {node_id}")
                return False
            
            # Record validation attempt
            await self._record_validation_attempt(node_id)
            
            logger.info(f"PoOT proof for node {node_id} is valid")
            return True
            
        except Exception as e:
            logger.error(f"Error validating PoOT proof for node {node_id}: {e}")
            return False
    
    async def _get_node_info(self, node_id: str) -> Optional[NodeInfo]:
        """Get node information from database"""
        try:
            # This would typically query the database
            # For now, return a mock node info
            return NodeInfo(
                node_id=node_id,
                address="mock_address",
                stake_amount=Decimal("1000.0"),
                status="active",
                created_at=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.error(f"Error getting node info for {node_id}: {e}")
            return None
    
    async def _get_all_active_nodes(self) -> List[NodeInfo]:
        """Get all active nodes from database"""
        try:
            # This would typically query the database
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Error getting active nodes: {e}")
            return []
    
    async def _validate_stake_amount(self, node_info: NodeInfo) -> bool:
        """Validate that node has sufficient stake"""
        try:
            return node_info.stake_amount >= MIN_TOKEN_STAKE_AMOUNT
        except Exception as e:
            logger.error(f"Error validating stake amount: {e}")
            return False
    
    async def _generate_challenge(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Generate a challenge for PoOT calculation"""
        try:
            challenge_data = secrets.token_bytes(CHALLENGE_COMPLEXITY_BYTES)
            challenge_hash = hashlib.sha256(challenge_data).hexdigest()
            
            challenge = {
                "challenge": challenge_hash,
                "data": challenge_data.hex(),
                "timestamp": datetime.now(timezone.utc),
                "valid_until": datetime.now(timezone.utc) + timedelta(minutes=POOT_CHALLENGE_VALIDITY_MINUTES)
            }
            
            # Store challenge
            self.active_challenges[node_id] = challenge
            
            return challenge
            
        except Exception as e:
            logger.error(f"Error generating challenge for node {node_id}: {e}")
            return None
    
    async def _calculate_proof(self, node_info: NodeInfo, challenge: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calculate PoOT proof based on node info and challenge"""
        try:
            # Create proof data
            proof_data = {
                "node_id": node_info.node_id,
                "stake_amount": str(node_info.stake_amount),
                "challenge": challenge["challenge"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Calculate proof hash
            proof_string = json.dumps(proof_data, sort_keys=True)
            proof_hash = hashlib.sha256(proof_string.encode()).hexdigest()
            
            # Generate signature (simplified)
            signature = hmac.new(
                challenge["data"].encode(),
                proof_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Calculate confidence score based on stake amount
            confidence_score = min(1.0, float(node_info.stake_amount) / 10000.0)
            
            return {
                "proof_hash": proof_hash,
                "signature": signature,
                "confidence_score": confidence_score
            }
            
        except Exception as e:
            logger.error(f"Error calculating proof: {e}")
            return None
    
    async def _verify_proof_signature(self, proof: PoOTProof) -> bool:
        """Verify PoOT proof signature"""
        try:
            # This would implement actual signature verification
            # For now, return True as a placeholder
            return True
        except Exception as e:
            logger.error(f"Error verifying proof signature: {e}")
            return False
    
    def _is_proof_valid(self, proof: PoOTProof) -> bool:
        """Check if PoOT proof is still valid"""
        try:
            return datetime.now(timezone.utc) < proof.valid_until
        except Exception as e:
            logger.error(f"Error checking proof validity: {e}")
            return False
    
    async def _check_fraud_detection(self, node_id: str) -> bool:
        """Check for fraud patterns"""
        try:
            now = datetime.now(timezone.utc)
            window_start = now - timedelta(hours=24)
            
            # Get validation attempts in the last 24 hours
            attempts = self.fraud_detection.get(node_id, [])
            recent_attempts = [attempt for attempt in attempts if attempt > window_start]
            
            # Check if too many attempts
            if len(recent_attempts) > MAX_VALIDATION_ATTEMPTS:
                logger.warning(f"Fraud detected for node {node_id}: too many validation attempts")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in fraud detection for node {node_id}: {e}")
            return False
    
    async def _record_validation_attempt(self, node_id: str):
        """Record a validation attempt for fraud detection"""
        try:
            now = datetime.now(timezone.utc)
            if node_id not in self.fraud_detection:
                self.fraud_detection[node_id] = []
            
            self.fraud_detection[node_id].append(now)
            
            # Clean old attempts
            window_start = now - timedelta(hours=24)
            self.fraud_detection[node_id] = [
                attempt for attempt in self.fraud_detection[node_id] 
                if attempt > window_start
            ]
            
        except Exception as e:
            logger.error(f"Error recording validation attempt for node {node_id}: {e}")
    
    async def _store_proof(self, proof: PoOTProof):
        """Store PoOT proof in database"""
        try:
            # This would store the proof in the database
            logger.info(f"Storing PoOT proof for node {proof.node_id}")
        except Exception as e:
            logger.error(f"Error storing proof: {e}")
    
    async def _load_proof(self, node_id: str) -> Optional[PoOTProof]:
        """Load PoOT proof from database"""
        try:
            # This would load the proof from the database
            # For now, return None
            return None
        except Exception as e:
            logger.error(f"Error loading proof for node {node_id}: {e}")
            return None
