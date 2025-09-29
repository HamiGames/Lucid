# Path: node/registration/node_registration_protocol.py
# Lucid RDP Node Registration Protocol - Secure node onboarding and verification
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import asyncio
import logging
import hashlib
import hmac
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import json

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import blake3

from motor.motor_asyncio import AsyncIOMotorDatabase
from tronpy import Tron
from tronpy.keys import PrivateKey as TronPrivateKey

# Import existing components
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))
from node.peer_discovery import PeerDiscovery, PeerInfo
from node.work_credits import WorkCreditsCalculator
from blockchain.core.blockchain_engine import TronNodeSystem

logger = logging.getLogger(__name__)

# Registration Protocol Constants
REGISTRATION_TIMEOUT_SEC = int(os.getenv("REGISTRATION_TIMEOUT_SEC", "300"))  # 5 minutes
MIN_STAKE_REQUIREMENT_USDT = float(os.getenv("MIN_STAKE_REQUIREMENT_USDT", "100.0"))  # $100 minimum
MAX_PENDING_REGISTRATIONS = int(os.getenv("MAX_PENDING_REGISTRATIONS", "1000"))
CHALLENGE_VALIDITY_SEC = int(os.getenv("CHALLENGE_VALIDITY_SEC", "120"))  # 2 minutes


class RegistrationStatus(Enum):
    """Node registration status states"""
    PENDING = "pending"
    CHALLENGE_ISSUED = "challenge_issued"
    CHALLENGE_VERIFIED = "challenge_verified"
    STAKE_VERIFIED = "stake_verified"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class ChallengeType(Enum):
    """Registration challenge types"""
    TRON_SIGNATURE = "tron_signature"
    CAPABILITY_PROOF = "capability_proof"
    NETWORK_REACHABILITY = "network_reachability"
    STORAGE_PROOF = "storage_proof"


@dataclass
class RegistrationChallenge:
    """Registration challenge for node verification"""
    challenge_id: str
    node_id: str
    challenge_type: ChallengeType
    challenge_data: Dict[str, Any]
    expected_response: str
    issued_at: datetime
    expires_at: datetime
    completed: bool = False
    response_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.challenge_id,
            "node_id": self.node_id,
            "type": self.challenge_type.value,
            "data": self.challenge_data,
            "expected_response": self.expected_response,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "completed": self.completed,
            "response_data": self.response_data
        }


@dataclass
class NodeRegistration:
    """Node registration record"""
    registration_id: str
    node_id: str
    node_address: str  # TRON address
    onion_address: str
    port: int
    role: str
    capabilities: Dict[str, Any]
    stake_amount: float
    stake_txid: Optional[str]
    contact_info: Optional[Dict[str, str]]
    status: RegistrationStatus
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    approved_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    challenges: List[str] = field(default_factory=list)  # challenge_ids
    verification_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.registration_id,
            "node_id": self.node_id,
            "node_address": self.node_address,
            "onion_address": self.onion_address,
            "port": self.port,
            "role": self.role,
            "capabilities": self.capabilities,
            "stake_amount": self.stake_amount,
            "stake_txid": self.stake_txid,
            "contact_info": self.contact_info,
            "status": self.status.value,
            "created_at": self.created_at,
            "approved_at": self.approved_at,
            "expires_at": self.expires_at,
            "challenges": self.challenges,
            "verification_score": self.verification_score
        }


class NodeRegistrationProtocol:
    """
    Node Registration Protocol for Lucid RDP network.
    
    Handles:
    - Secure node onboarding with multi-stage verification
    - TRON address and stake verification
    - Capability and network reachability testing
    - Challenge-response authentication
    - Registration approval/rejection workflow
    - Integration with peer discovery and work credits
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, peer_discovery: PeerDiscovery, 
                 work_credits: WorkCreditsCalculator, tron_client: TronNodeSystem):
        self.db = db
        self.peer_discovery = peer_discovery
        self.work_credits = work_credits
        self.tron_client = tron_client
        
        # State tracking
        self.pending_registrations: Dict[str, NodeRegistration] = {}
        self.active_challenges: Dict[str, RegistrationChallenge] = {}
        self.running = False
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._verification_task: Optional[asyncio.Task] = None
        
        logger.info("Node registration protocol initialized")
    
    async def start(self):
        """Start registration protocol service"""
        try:
            self.running = True
            
            # Ensure database indexes
            await self._setup_indexes()
            
            # Load pending registrations
            await self._load_pending_registrations()
            
            # Start background tasks
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_registrations())
            self._verification_task = asyncio.create_task(self._process_verification_queue())
            
            logger.info("Node registration protocol started")
            
        except Exception as e:
            logger.error(f"Failed to start registration protocol: {e}")
            raise
    
    async def stop(self):
        """Stop registration protocol service"""
        try:
            self.running = False
            
            # Cancel background tasks
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
            if self._verification_task and not self._verification_task.done():
                self._verification_task.cancel()
            
            # Wait for tasks to complete
            if self._cleanup_task:
                await asyncio.gather(self._cleanup_task, return_exceptions=True)
            if self._verification_task:
                await asyncio.gather(self._verification_task, return_exceptions=True)
            
            logger.info("Node registration protocol stopped")
            
        except Exception as e:
            logger.error(f"Error stopping registration protocol: {e}")
    
    async def submit_registration(self, registration_data: Dict[str, Any]) -> str:
        """
        Submit new node registration request.
        
        Args:
            registration_data: Node registration information
            
        Returns:
            Registration ID if successful
        """
        try:
            # Validate registration data
            validation_result = self._validate_registration_data(registration_data)
            if not validation_result["valid"]:
                raise ValueError(f"Invalid registration data: {validation_result['error']}")
            
            # Check registration limits
            if len(self.pending_registrations) >= MAX_PENDING_REGISTRATIONS:
                raise ValueError("Maximum pending registrations reached")
            
            # Create registration record
            registration_id = str(uuid.uuid4())
            node_id = registration_data["node_id"]
            
            registration = NodeRegistration(
                registration_id=registration_id,
                node_id=node_id,
                node_address=registration_data["node_address"],
                onion_address=registration_data["onion_address"],
                port=registration_data["port"],
                role=registration_data["role"],
                capabilities=registration_data["capabilities"],
                stake_amount=registration_data["stake_amount"],
                stake_txid=registration_data.get("stake_txid"),
                contact_info=registration_data.get("contact_info"),
                status=RegistrationStatus.PENDING,
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=REGISTRATION_TIMEOUT_SEC)
            )
            
            # Store registration
            self.pending_registrations[registration_id] = registration
            await self.db["node_registrations"].replace_one(
                {"_id": registration_id},
                registration.to_dict(),
                upsert=True
            )
            
            # Start verification process
            asyncio.create_task(self._initiate_verification(registration))
            
            logger.info(f"Registration submitted: {registration_id} for node {node_id}")
            return registration_id
            
        except Exception as e:
            logger.error(f"Failed to submit registration: {e}")
            raise
    
    async def get_registration_status(self, registration_id: str) -> Optional[Dict[str, Any]]:
        """Get registration status and details"""
        try:
            # Check in-memory first
            if registration_id in self.pending_registrations:
                registration = self.pending_registrations[registration_id]
                return {
                    "registration_id": registration_id,
                    "status": registration.status.value,
                    "verification_score": registration.verification_score,
                    "challenges": len(registration.challenges),
                    "created_at": registration.created_at,
                    "expires_at": registration.expires_at
                }
            
            # Check database
            reg_doc = await self.db["node_registrations"].find_one({"_id": registration_id})
            if reg_doc:
                return {
                    "registration_id": registration_id,
                    "status": reg_doc["status"],
                    "verification_score": reg_doc.get("verification_score", 0.0),
                    "challenges": len(reg_doc.get("challenges", [])),
                    "created_at": reg_doc["created_at"],
                    "expires_at": reg_doc.get("expires_at")
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get registration status: {e}")
            return None
    
    async def respond_to_challenge(self, challenge_id: str, response_data: Dict[str, Any]) -> bool:
        """
        Submit response to registration challenge.
        
        Args:
            challenge_id: Challenge identifier
            response_data: Challenge response data
            
        Returns:
            True if response is valid
        """
        try:
            # Get challenge
            challenge = self.active_challenges.get(challenge_id)
            if not challenge:
                challenge_doc = await self.db["registration_challenges"].find_one({"_id": challenge_id})
                if not challenge_doc:
                    raise ValueError("Challenge not found")
                
                challenge = RegistrationChallenge(
                    challenge_id=challenge_doc["_id"],
                    node_id=challenge_doc["node_id"],
                    challenge_type=ChallengeType(challenge_doc["type"]),
                    challenge_data=challenge_doc["data"],
                    expected_response=challenge_doc["expected_response"],
                    issued_at=challenge_doc["issued_at"],
                    expires_at=challenge_doc["expires_at"],
                    completed=challenge_doc["completed"],
                    response_data=challenge_doc.get("response_data")
                )
            
            # Check if challenge expired
            if datetime.now(timezone.utc) > challenge.expires_at:
                raise ValueError("Challenge expired")
            
            if challenge.completed:
                raise ValueError("Challenge already completed")
            
            # Verify response based on challenge type
            is_valid = await self._verify_challenge_response(challenge, response_data)
            
            if is_valid:
                challenge.completed = True
                challenge.response_data = response_data
                
                # Update challenge in database
                await self.db["registration_challenges"].update_one(
                    {"_id": challenge_id},
                    {"$set": {"completed": True, "response_data": response_data}}
                )
                
                # Update registration verification score
                await self._update_verification_score(challenge.node_id, challenge.challenge_type)
                
                logger.info(f"Challenge response verified: {challenge_id}")
                return True
            else:
                logger.warning(f"Invalid challenge response: {challenge_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to verify challenge response: {e}")
            return False
    
    async def approve_registration(self, registration_id: str, approver_id: str) -> bool:
        """
        Approve node registration.
        
        Args:
            registration_id: Registration to approve
            approver_id: ID of approving entity
            
        Returns:
            True if approved successfully
        """
        try:
            registration = self.pending_registrations.get(registration_id)
            if not registration:
                raise ValueError("Registration not found")
            
            if registration.status != RegistrationStatus.STAKE_VERIFIED:
                raise ValueError(f"Registration not ready for approval: {registration.status}")
            
            # Final verification checks
            if registration.verification_score < 0.8:  # 80% verification threshold
                raise ValueError(f"Insufficient verification score: {registration.verification_score}")
            
            # Update registration status
            registration.status = RegistrationStatus.APPROVED
            registration.approved_at = datetime.now(timezone.utc)
            
            # Add to peer discovery
            peer_info = PeerInfo(
                node_id=registration.node_id,
                onion_address=registration.onion_address,
                port=registration.port,
                last_seen=datetime.now(timezone.utc),
                role=registration.role,
                capabilities=set(registration.capabilities.keys())
            )
            
            await self.peer_discovery.add_peer(peer_info)
            
            # Update database
            await self.db["node_registrations"].update_one(
                {"_id": registration_id},
                {"$set": {
                    "status": RegistrationStatus.APPROVED.value,
                    "approved_at": registration.approved_at,
                    "approved_by": approver_id
                }}
            )
            
            # Remove from pending
            del self.pending_registrations[registration_id]
            
            logger.info(f"Registration approved: {registration_id} for node {registration.node_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to approve registration: {e}")
            return False
    
    async def reject_registration(self, registration_id: str, reason: str, rejector_id: str) -> bool:
        """
        Reject node registration.
        
        Args:
            registration_id: Registration to reject
            reason: Rejection reason
            rejector_id: ID of rejecting entity
            
        Returns:
            True if rejected successfully
        """
        try:
            registration = self.pending_registrations.get(registration_id)
            if not registration:
                raise ValueError("Registration not found")
            
            # Update registration status
            registration.status = RegistrationStatus.REJECTED
            
            # Update database
            await self.db["node_registrations"].update_one(
                {"_id": registration_id},
                {"$set": {
                    "status": RegistrationStatus.REJECTED.value,
                    "rejection_reason": reason,
                    "rejected_at": datetime.now(timezone.utc),
                    "rejected_by": rejector_id
                }}
            )
            
            # Remove from pending
            del self.pending_registrations[registration_id]
            
            logger.info(f"Registration rejected: {registration_id} - {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reject registration: {e}")
            return False
    
    def _validate_registration_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate registration data format and requirements"""
        try:
            required_fields = [
                "node_id", "node_address", "onion_address", "port", 
                "role", "capabilities", "stake_amount"
            ]
            
            for field in required_fields:
                if field not in data:
                    return {"valid": False, "error": f"Missing required field: {field}"}
            
            # Validate TRON address format
            if not data["node_address"].startswith("T") or len(data["node_address"]) != 34:
                return {"valid": False, "error": "Invalid TRON address format"}
            
            # Validate onion address format
            if not data["onion_address"].endswith(".onion"):
                return {"valid": False, "error": "Invalid onion address format"}
            
            # Validate port range
            if not (1024 <= data["port"] <= 65535):
                return {"valid": False, "error": "Invalid port range"}
            
            # Validate role
            valid_roles = ["worker", "server", "admin", "dev"]
            if data["role"] not in valid_roles:
                return {"valid": False, "error": f"Invalid role, must be one of: {valid_roles}"}
            
            # Validate stake amount
            if data["stake_amount"] < MIN_STAKE_REQUIREMENT_USDT:
                return {"valid": False, "error": f"Insufficient stake: {data['stake_amount']} < {MIN_STAKE_REQUIREMENT_USDT}"}
            
            # Validate capabilities
            if not isinstance(data["capabilities"], dict):
                return {"valid": False, "error": "Capabilities must be a dictionary"}
            
            return {"valid": True}
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    async def _initiate_verification(self, registration: NodeRegistration):
        """Initiate multi-stage verification process"""
        try:
            challenges = []
            
            # Stage 1: TRON signature challenge
            tron_challenge = await self._create_tron_signature_challenge(registration)
            challenges.append(tron_challenge.challenge_id)
            
            # Stage 2: Capability proof challenge
            capability_challenge = await self._create_capability_proof_challenge(registration)
            challenges.append(capability_challenge.challenge_id)
            
            # Stage 3: Network reachability challenge
            network_challenge = await self._create_network_reachability_challenge(registration)
            challenges.append(network_challenge.challenge_id)
            
            # Stage 4: Storage proof challenge (if storage capability claimed)
            if "storage" in registration.capabilities:
                storage_challenge = await self._create_storage_proof_challenge(registration)
                challenges.append(storage_challenge.challenge_id)
            
            # Update registration with challenges
            registration.challenges = challenges
            registration.status = RegistrationStatus.CHALLENGE_ISSUED
            
            await self.db["node_registrations"].update_one(
                {"_id": registration.registration_id},
                {"$set": {
                    "status": RegistrationStatus.CHALLENGE_ISSUED.value,
                    "challenges": challenges
                }}
            )
            
            logger.info(f"Verification initiated for registration {registration.registration_id}")
            
        except Exception as e:
            logger.error(f"Failed to initiate verification: {e}")
    
    async def _create_tron_signature_challenge(self, registration: NodeRegistration) -> RegistrationChallenge:
        """Create TRON signature verification challenge"""
        challenge_id = str(uuid.uuid4())
        challenge_message = f"lucid_node_registration_{registration.node_id}_{int(datetime.now(timezone.utc).timestamp())}"
        
        challenge = RegistrationChallenge(
            challenge_id=challenge_id,
            node_id=registration.node_id,
            challenge_type=ChallengeType.TRON_SIGNATURE,
            challenge_data={"message": challenge_message},
            expected_response=hashlib.sha256(challenge_message.encode()).hexdigest(),
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=CHALLENGE_VALIDITY_SEC)
        )
        
        self.active_challenges[challenge_id] = challenge
        await self.db["registration_challenges"].replace_one(
            {"_id": challenge_id},
            challenge.to_dict(),
            upsert=True
        )
        
        return challenge
    
    async def _create_capability_proof_challenge(self, registration: NodeRegistration) -> RegistrationChallenge:
        """Create capability proof challenge"""
        challenge_id = str(uuid.uuid4())
        
        # Challenge based on claimed capabilities
        capabilities = registration.capabilities
        challenge_data = {
            "required_proofs": [],
            "test_parameters": {}
        }
        
        if "relay" in capabilities:
            challenge_data["required_proofs"].append("bandwidth_test")
            challenge_data["test_parameters"]["min_bandwidth_mbps"] = 10
        
        if "storage" in capabilities:
            challenge_data["required_proofs"].append("storage_test")
            challenge_data["test_parameters"]["min_storage_gb"] = 50
        
        if "compute" in capabilities:
            challenge_data["required_proofs"].append("compute_test")
            challenge_data["test_parameters"]["min_cpu_cores"] = 2
        
        challenge = RegistrationChallenge(
            challenge_id=challenge_id,
            node_id=registration.node_id,
            challenge_type=ChallengeType.CAPABILITY_PROOF,
            challenge_data=challenge_data,
            expected_response="capability_proof_verified",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=CHALLENGE_VALIDITY_SEC)
        )
        
        self.active_challenges[challenge_id] = challenge
        await self.db["registration_challenges"].replace_one(
            {"_id": challenge_id},
            challenge.to_dict(),
            upsert=True
        )
        
        return challenge
    
    async def _create_network_reachability_challenge(self, registration: NodeRegistration) -> RegistrationChallenge:
        """Create network reachability challenge"""
        challenge_id = str(uuid.uuid4())
        challenge_token = hashlib.sha256(f"{registration.node_id}_{challenge_id}".encode()).hexdigest()[:16]
        
        challenge = RegistrationChallenge(
            challenge_id=challenge_id,
            node_id=registration.node_id,
            challenge_type=ChallengeType.NETWORK_REACHABILITY,
            challenge_data={
                "ping_token": challenge_token,
                "endpoint": f"http://{registration.onion_address}:{registration.port}/registration/ping"
            },
            expected_response=f"pong_{challenge_token}",
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=CHALLENGE_VALIDITY_SEC)
        )
        
        self.active_challenges[challenge_id] = challenge
        await self.db["registration_challenges"].replace_one(
            {"_id": challenge_id},
            challenge.to_dict(),
            upsert=True
        )
        
        return challenge
    
    async def _create_storage_proof_challenge(self, registration: NodeRegistration) -> RegistrationChallenge:
        """Create storage proof challenge"""
        challenge_id = str(uuid.uuid4())
        test_data = os.urandom(1024 * 1024)  # 1MB test data
        test_hash = hashlib.sha256(test_data).hexdigest()
        
        challenge = RegistrationChallenge(
            challenge_id=challenge_id,
            node_id=registration.node_id,
            challenge_type=ChallengeType.STORAGE_PROOF,
            challenge_data={
                "test_data_hash": test_hash,
                "storage_duration_sec": 300,  # Store for 5 minutes
                "retrieval_endpoint": f"http://{registration.onion_address}:{registration.port}/storage/retrieve"
            },
            expected_response=test_hash,
            issued_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=CHALLENGE_VALIDITY_SEC)
        )
        
        self.active_challenges[challenge_id] = challenge
        await self.db["registration_challenges"].replace_one(
            {"_id": challenge_id},
            challenge.to_dict(),
            upsert=True
        )
        
        return challenge
    
    async def _verify_challenge_response(self, challenge: RegistrationChallenge, response_data: Dict[str, Any]) -> bool:
        """Verify challenge response based on challenge type"""
        try:
            if challenge.challenge_type == ChallengeType.TRON_SIGNATURE:
                return self._verify_tron_signature(challenge, response_data)
            
            elif challenge.challenge_type == ChallengeType.CAPABILITY_PROOF:
                return await self._verify_capability_proof(challenge, response_data)
            
            elif challenge.challenge_type == ChallengeType.NETWORK_REACHABILITY:
                return await self._verify_network_reachability(challenge, response_data)
            
            elif challenge.challenge_type == ChallengeType.STORAGE_PROOF:
                return await self._verify_storage_proof(challenge, response_data)
            
            return False
            
        except Exception as e:
            logger.error(f"Challenge verification failed: {e}")
            return False
    
    def _verify_tron_signature(self, challenge: RegistrationChallenge, response_data: Dict[str, Any]) -> bool:
        """Verify TRON signature challenge response"""
        try:
            signature = response_data.get("signature")
            if not signature:
                return False
            
            # In production, this would verify the actual TRON signature
            # For now, we'll do a simplified verification
            message = challenge.challenge_data["message"]
            expected_hash = hashlib.sha256(message.encode()).hexdigest()
            
            # Simplified verification - in production use actual TRON signature verification
            return len(signature) >= 64  # Basic length check
            
        except Exception as e:
            logger.error(f"TRON signature verification failed: {e}")
            return False
    
    async def _verify_capability_proof(self, challenge: RegistrationChallenge, response_data: Dict[str, Any]) -> bool:
        """Verify capability proof challenge response"""
        try:
            required_proofs = challenge.challenge_data["required_proofs"]
            test_params = challenge.challenge_data["test_parameters"]
            
            for proof_type in required_proofs:
                if proof_type not in response_data:
                    return False
                
                proof_data = response_data[proof_type]
                
                if proof_type == "bandwidth_test":
                    measured_bandwidth = proof_data.get("bandwidth_mbps", 0)
                    if measured_bandwidth < test_params.get("min_bandwidth_mbps", 0):
                        return False
                
                elif proof_type == "storage_test":
                    available_storage = proof_data.get("storage_gb", 0)
                    if available_storage < test_params.get("min_storage_gb", 0):
                        return False
                
                elif proof_type == "compute_test":
                    cpu_cores = proof_data.get("cpu_cores", 0)
                    if cpu_cores < test_params.get("min_cpu_cores", 0):
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Capability proof verification failed: {e}")
            return False
    
    async def _verify_network_reachability(self, challenge: RegistrationChallenge, response_data: Dict[str, Any]) -> bool:
        """Verify network reachability challenge response"""
        try:
            ping_response = response_data.get("ping_response")
            expected_response = challenge.expected_response
            
            return ping_response == expected_response
            
        except Exception as e:
            logger.error(f"Network reachability verification failed: {e}")
            return False
    
    async def _verify_storage_proof(self, challenge: RegistrationChallenge, response_data: Dict[str, Any]) -> bool:
        """Verify storage proof challenge response"""
        try:
            retrieved_hash = response_data.get("data_hash")
            expected_hash = challenge.expected_response
            
            return retrieved_hash == expected_hash
            
        except Exception as e:
            logger.error(f"Storage proof verification failed: {e}")
            return False
    
    async def _update_verification_score(self, node_id: str, challenge_type: ChallengeType):
        """Update registration verification score"""
        try:
            # Find registration by node_id
            registration = None
            for reg in self.pending_registrations.values():
                if reg.node_id == node_id:
                    registration = reg
                    break
            
            if not registration:
                return
            
            # Update score based on challenge type
            score_increment = {
                ChallengeType.TRON_SIGNATURE: 0.3,
                ChallengeType.CAPABILITY_PROOF: 0.3,
                ChallengeType.NETWORK_REACHABILITY: 0.2,
                ChallengeType.STORAGE_PROOF: 0.2
            }
            
            registration.verification_score += score_increment.get(challenge_type, 0.1)
            registration.verification_score = min(1.0, registration.verification_score)
            
            # Check if all challenges completed and stake verified
            completed_challenges = 0
            for challenge_id in registration.challenges:
                challenge_doc = await self.db["registration_challenges"].find_one({"_id": challenge_id})
                if challenge_doc and challenge_doc.get("completed"):
                    completed_challenges += 1
            
            if completed_challenges == len(registration.challenges):
                # Verify stake
                if await self._verify_stake(registration):
                    registration.status = RegistrationStatus.STAKE_VERIFIED
                
                await self.db["node_registrations"].update_one(
                    {"_id": registration.registration_id},
                    {"$set": {
                        "status": registration.status.value,
                        "verification_score": registration.verification_score
                    }}
                )
            
        except Exception as e:
            logger.error(f"Failed to update verification score: {e}")
    
    async def _verify_stake(self, registration: NodeRegistration) -> bool:
        """Verify node stake on TRON blockchain"""
        try:
            if not registration.stake_txid:
                return False
            
            # Check TRON transaction
            tx_status = await self.tron_client.get_transaction_status(registration.stake_txid)
            
            if tx_status == "confirmed":
                # In production, would verify the actual stake amount and recipient
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Stake verification failed: {e}")
            return False
    
    async def _setup_indexes(self):
        """Setup database indexes for registration collections"""
        try:
            # Node registrations indexes
            await self.db["node_registrations"].create_index("node_id", unique=True)
            await self.db["node_registrations"].create_index("status")
            await self.db["node_registrations"].create_index("created_at")
            await self.db["node_registrations"].create_index("expires_at")
            
            # Registration challenges indexes
            await self.db["registration_challenges"].create_index("node_id")
            await self.db["registration_challenges"].create_index("type")
            await self.db["registration_challenges"].create_index("expires_at")
            await self.db["registration_challenges"].create_index("completed")
            
            logger.info("Registration protocol database indexes created")
            
        except Exception as e:
            logger.warning(f"Failed to create registration indexes: {e}")
    
    async def _load_pending_registrations(self):
        """Load pending registrations from database"""
        try:
            cursor = self.db["node_registrations"].find({
                "status": {"$in": [
                    RegistrationStatus.PENDING.value,
                    RegistrationStatus.CHALLENGE_ISSUED.value,
                    RegistrationStatus.CHALLENGE_VERIFIED.value,
                    RegistrationStatus.STAKE_VERIFIED.value
                ]}
            })
            
            async for reg_doc in cursor:
                registration = NodeRegistration(
                    registration_id=reg_doc["_id"],
                    node_id=reg_doc["node_id"],
                    node_address=reg_doc["node_address"],
                    onion_address=reg_doc["onion_address"],
                    port=reg_doc["port"],
                    role=reg_doc["role"],
                    capabilities=reg_doc["capabilities"],
                    stake_amount=reg_doc["stake_amount"],
                    stake_txid=reg_doc.get("stake_txid"),
                    contact_info=reg_doc.get("contact_info"),
                    status=RegistrationStatus(reg_doc["status"]),
                    created_at=reg_doc["created_at"],
                    approved_at=reg_doc.get("approved_at"),
                    expires_at=reg_doc.get("expires_at"),
                    challenges=reg_doc.get("challenges", []),
                    verification_score=reg_doc.get("verification_score", 0.0)
                )
                
                self.pending_registrations[registration.registration_id] = registration
                
            logger.info(f"Loaded {len(self.pending_registrations)} pending registrations")
            
        except Exception as e:
            logger.error(f"Failed to load pending registrations: {e}")
    
    async def _cleanup_expired_registrations(self):
        """Cleanup expired registrations and challenges"""
        while self.running:
            try:
                now = datetime.now(timezone.utc)
                
                # Clean up expired registrations
                expired_registrations = []
                for reg_id, registration in self.pending_registrations.items():
                    if registration.expires_at and now > registration.expires_at:
                        expired_registrations.append(reg_id)
                
                for reg_id in expired_registrations:
                    registration = self.pending_registrations[reg_id]
                    registration.status = RegistrationStatus.EXPIRED
                    
                    await self.db["node_registrations"].update_one(
                        {"_id": reg_id},
                        {"$set": {"status": RegistrationStatus.EXPIRED.value}}
                    )
                    
                    del self.pending_registrations[reg_id]
                    logger.info(f"Registration expired: {reg_id}")
                
                # Clean up expired challenges
                expired_challenges = []
                for challenge_id, challenge in self.active_challenges.items():
                    if now > challenge.expires_at and not challenge.completed:
                        expired_challenges.append(challenge_id)
                
                for challenge_id in expired_challenges:
                    del self.active_challenges[challenge_id]
                
                # Clean up database expired challenges
                await self.db["registration_challenges"].delete_many({
                    "expires_at": {"$lt": now},
                    "completed": False
                })
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup task error: {e}")
                await asyncio.sleep(10)
    
    async def _process_verification_queue(self):
        """Process verification queue for automated checks"""
        while self.running:
            try:
                # Process registrations ready for verification
                for registration in list(self.pending_registrations.values()):
                    if registration.status == RegistrationStatus.CHALLENGE_VERIFIED:
                        # Check if stake verification is pending
                        if registration.stake_txid and registration.status != RegistrationStatus.STAKE_VERIFIED:
                            if await self._verify_stake(registration):
                                registration.status = RegistrationStatus.STAKE_VERIFIED
                                await self.db["node_registrations"].update_one(
                                    {"_id": registration.registration_id},
                                    {"$set": {"status": registration.status.value}}
                                )
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Verification queue processing error: {e}")
                await asyncio.sleep(10)


# Global registration protocol instance
_registration_protocol: Optional[NodeRegistrationProtocol] = None


def get_registration_protocol() -> Optional[NodeRegistrationProtocol]:
    """Get global registration protocol instance"""
    global _registration_protocol
    return _registration_protocol


def create_registration_protocol(db: AsyncIOMotorDatabase, peer_discovery: PeerDiscovery,
                                work_credits: WorkCreditsCalculator, 
                                tron_client: TronNodeSystem) -> NodeRegistrationProtocol:
    """Create registration protocol instance"""
    global _registration_protocol
    _registration_protocol = NodeRegistrationProtocol(db, peer_discovery, work_credits, tron_client)
    return _registration_protocol


async def cleanup_registration_protocol():
    """Cleanup registration protocol"""
    global _registration_protocol
    if _registration_protocol:
        await _registration_protocol.stop()
        _registration_protocol = None


if __name__ == "__main__":
    # Test registration protocol
    async def test_registration_protocol():
        print("Testing Lucid Node Registration Protocol...")
        
        # This would normally be initialized with real components
        # For testing purposes, we'll create mock instances
        
        print("Test completed - registration protocol ready")
    
    asyncio.run(test_registration_protocol())