"""
LUCID Node Consensus - Work Credits Calculation
Implements Proof of Operational Tasks (PoOT) work credits system
Distroless container: pickme/lucid:node-worker:latest
"""

import asyncio
import json
import logging
import os
import time
import hashlib
import hmac
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import aiofiles
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field
import cryptography
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkCreditType(str, Enum):
    RELAY_BANDWIDTH = "relay_bandwidth"
    STORAGE_AVAILABILITY = "storage_availability"
    VALIDATION_SIGNATURE = "validation_signature"
    UPTIME_BEACON = "uptime_beacon"
    SESSION_PROCESSING = "session_processing"
    CHUNK_REPLICATION = "chunk_replication"
    NETWORK_ROUTING = "network_routing"
    CONSENSUS_PARTICIPATION = "consensus_participation"

class WorkCreditStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"

@dataclass
class WorkCredit:
    """Work credit data structure"""
    credit_id: str
    node_id: str
    credit_type: WorkCreditType
    amount: float
    timestamp: datetime
    proof_data: Dict[str, Any]
    signature: str
    status: WorkCreditStatus = WorkCreditStatus.PENDING
    verified_at: Optional[datetime] = None
    verifier_node_id: Optional[str] = None

@dataclass
class WorkCreditProof:
    """Work credit proof data"""
    proof_type: str
    proof_data: Dict[str, Any]
    timestamp: datetime
    node_signature: str
    witness_signatures: List[str] = None

class WorkCreditRequest(BaseModel):
    """Pydantic model for work credit requests"""
    node_id: str = Field(..., description="Node requesting credits")
    credit_type: WorkCreditType = Field(..., description="Type of work credit")
    proof_data: Dict[str, Any] = Field(..., description="Proof of work performed")
    amount: float = Field(..., description="Amount of credits requested")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)

class WorkCreditResponse(BaseModel):
    """Response model for work credit operations"""
    credit_id: str
    status: WorkCreditStatus
    amount: float
    message: str
    verified_at: Optional[datetime] = None

class WorkCreditsCalculator:
    """Calculates and manages work credits for Proof of Operational Tasks (PoOT)"""
    
    def __init__(self):
        self.data_dir = Path("/data/node/work_credits")
        self.cache_dir = Path("/data/node/cache")
        self.logs_dir = Path("/data/node/logs")
        
        # Ensure directories exist
        for directory in [self.data_dir, self.cache_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.node_id = os.getenv("NODE_ID", "node-001")
        self.mongodb_url = os.getenv("MONGODB_URL", "mongodb://lucid:lucid@lucid_mongo:27017/lucid")
        self.consensus_api_url = os.getenv("CONSENSUS_API_URL", "http://consensus-api:8080")
        
        # Work credit parameters
        self.credit_weights = {
            WorkCreditType.RELAY_BANDWIDTH: 1.0,
            WorkCreditType.STORAGE_AVAILABILITY: 2.0,
            WorkCreditType.VALIDATION_SIGNATURE: 3.0,
            WorkCreditType.UPTIME_BEACON: 0.5,
            WorkCreditType.SESSION_PROCESSING: 4.0,
            WorkCreditType.CHUNK_REPLICATION: 2.5,
            WorkCreditType.NETWORK_ROUTING: 1.5,
            WorkCreditType.CONSENSUS_PARTICIPATION: 5.0
        }
        
        # Credit calculation parameters
        self.base_credit_amount = 1.0
        self.max_credit_per_type = 100.0
        self.credit_decay_factor = 0.95
        self.verification_threshold = 0.6  # 60% of nodes must verify
        
        # Node key pair for signing
        # Initialize node key asynchronously
        self.node_private_key = None
        asyncio.create_task(self._initialize_node_key())
        self.node_public_key = self.node_private_key.public_key()
        
        # Work credit cache
        self.credit_cache: Dict[str, WorkCredit] = {}
        self.verification_cache: Dict[str, List[str]] = {}
        
        # Load existing credits
        asyncio.create_task(self._load_work_credits())
    
    async def _load_or_generate_key(self) -> ed25519.Ed25519PrivateKey:
        """Load or generate node private key"""
        try:
            key_file = self.data_dir / "node_key.pem"
            
            if key_file.exists():
                async with aiofiles.open(key_file, "rb") as f:
                    key_data = await f.read()
                return serialization.load_pem_private_key(key_data, password=None)
            else:
                # Generate new key
                private_key = ed25519.Ed25519PrivateKey.generate()
                
                # Save key
                key_data = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                
                async with aiofiles.open(key_file, "wb") as f:
                    await f.write(key_data)
                
                logger.info("Generated new node private key")
                return private_key
                
        except Exception as e:
            logger.error(f"Error loading/generating key: {e}")
            # Fallback to generating new key
            return ed25519.Ed25519PrivateKey.generate()
    
    async def _load_work_credits(self):
        """Load existing work credits from disk"""
        try:
            credits_file = self.data_dir / "work_credits.json"
            if credits_file.exists():
                async with aiofiles.open(credits_file, "r") as f:
                    data = await f.read()
                    credits_data = json.loads(data)
                    
                    for credit_id, credit_data in credits_data.items():
                        credit = WorkCredit(**credit_data)
                        self.credit_cache[credit_id] = credit
                    
                logger.info(f"Loaded {len(self.credit_cache)} work credits")
        except Exception as e:
            logger.error(f"Error loading work credits: {e}")
    
    async def _save_work_credits(self):
        """Save work credits to disk"""
        try:
            credits_data = {k: asdict(v) for k, v in self.credit_cache.items()}
            
            credits_file = self.data_dir / "work_credits.json"
            async with aiofiles.open(credits_file, "w") as f:
                await f.write(json.dumps(credits_data, indent=2, default=str))
                
        except Exception as e:
            logger.error(f"Error saving work credits: {e}")
    
    async def calculate_work_credits(self, request: WorkCreditRequest) -> WorkCreditResponse:
        """Calculate work credits for a given request"""
        try:
            # Validate request
            await self._validate_work_credit_request(request)
            
            # Calculate credit amount
            credit_amount = await self._calculate_credit_amount(request)
            
            # Create work credit
            credit_id = await self._generate_credit_id(request)
            proof_data = await self._create_work_proof(request)
            signature = await self._sign_work_credit(credit_id, request, credit_amount)
            
            work_credit = WorkCredit(
                credit_id=credit_id,
                node_id=request.node_id,
                credit_type=request.credit_type,
                amount=credit_amount,
                timestamp=request.timestamp or datetime.now(),
                proof_data=proof_data,
                signature=signature,
                status=WorkCreditStatus.PENDING
            )
            
            # Store credit
            self.credit_cache[credit_id] = work_credit
            await self._save_work_credits()
            
            # Log credit creation
            await self._log_work_credit_event(credit_id, "credit_created", {
                "node_id": request.node_id,
                "credit_type": request.credit_type,
                "amount": credit_amount
            })
            
            # Start verification process
            asyncio.create_task(self._verify_work_credit(credit_id))
            
            logger.info(f"Calculated work credits: {credit_id} - {credit_amount} credits")
            
            return WorkCreditResponse(
                credit_id=credit_id,
                status=WorkCreditStatus.PENDING,
                amount=credit_amount,
                message="Work credits calculated and submitted for verification"
            )
            
        except Exception as e:
            logger.error(f"Error calculating work credits: {e}")
            raise
    
    async def _validate_work_credit_request(self, request: WorkCreditRequest):
        """Validate work credit request"""
        if not request.node_id:
            raise ValueError("Node ID is required")
        
        if request.amount <= 0:
            raise ValueError("Credit amount must be positive")
        
        if request.amount > self.max_credit_per_type:
            raise ValueError(f"Credit amount exceeds maximum: {self.max_credit_per_type}")
        
        # Validate proof data based on credit type
        await self._validate_proof_data(request.credit_type, request.proof_data)
    
    async def _validate_proof_data(self, credit_type: WorkCreditType, proof_data: Dict[str, Any]):
        """Validate proof data based on credit type"""
        if credit_type == WorkCreditType.RELAY_BANDWIDTH:
            required_fields = ["bytes_relayed", "duration_seconds", "bandwidth_mbps"]
            for field in required_fields:
                if field not in proof_data:
                    raise ValueError(f"Missing required field for relay bandwidth: {field}")
        
        elif credit_type == WorkCreditType.STORAGE_AVAILABILITY:
            required_fields = ["storage_size_gb", "availability_percentage", "duration_hours"]
            for field in required_fields:
                if field not in proof_data:
                    raise ValueError(f"Missing required field for storage availability: {field}")
        
        elif credit_type == WorkCreditType.VALIDATION_SIGNATURE:
            required_fields = ["transaction_hash", "validation_result", "signature"]
            for field in required_fields:
                if field not in proof_data:
                    raise ValueError(f"Missing required field for validation signature: {field}")
        
        elif credit_type == WorkCreditType.UPTIME_BEACON:
            required_fields = ["uptime_percentage", "beacon_interval", "total_beacons"]
            for field in required_fields:
                if field not in proof_data:
                    raise ValueError(f"Missing required field for uptime beacon: {field}")
        
        elif credit_type == WorkCreditType.SESSION_PROCESSING:
            required_fields = ["session_id", "processing_time_ms", "chunks_processed"]
            for field in required_fields:
                if field not in proof_data:
                    raise ValueError(f"Missing required field for session processing: {field}")
        
        elif credit_type == WorkCreditType.CHUNK_REPLICATION:
            required_fields = ["chunk_id", "replication_count", "storage_nodes"]
            for field in required_fields:
                if field not in proof_data:
                    raise ValueError(f"Missing required field for chunk replication: {field}")
        
        elif credit_type == WorkCreditType.NETWORK_ROUTING:
            required_fields = ["routes_created", "packets_routed", "latency_ms"]
            for field in required_fields:
                if field not in proof_data:
                    raise ValueError(f"Missing required field for network routing: {field}")
        
        elif credit_type == WorkCreditType.CONSENSUS_PARTICIPATION:
            required_fields = ["consensus_round", "participation_type", "contribution_score"]
            for field in required_fields:
                if field not in proof_data:
                    raise ValueError(f"Missing required field for consensus participation: {field}")
    
    async def _calculate_credit_amount(self, request: WorkCreditRequest) -> float:
        """Calculate credit amount based on work performed"""
        try:
            base_amount = self.base_credit_amount
            weight = self.credit_weights.get(request.credit_type, 1.0)
            
            # Calculate based on credit type
            if request.credit_type == WorkCreditType.RELAY_BANDWIDTH:
                bytes_relayed = request.proof_data.get("bytes_relayed", 0)
                duration = request.proof_data.get("duration_seconds", 1)
                bandwidth = bytes_relayed / duration / (1024 * 1024)  # MB/s
                amount = base_amount * weight * (bandwidth / 10.0)  # 10 MB/s = 1x base
            
            elif request.credit_type == WorkCreditType.STORAGE_AVAILABILITY:
                storage_size = request.proof_data.get("storage_size_gb", 0)
                availability = request.proof_data.get("availability_percentage", 0) / 100.0
                duration = request.proof_data.get("duration_hours", 1)
                amount = base_amount * weight * storage_size * availability * (duration / 24.0)
            
            elif request.credit_type == WorkCreditType.VALIDATION_SIGNATURE:
                # Fixed amount for validation work
                amount = base_amount * weight * 2.0
            
            elif request.credit_type == WorkCreditType.UPTIME_BEACON:
                uptime = request.proof_data.get("uptime_percentage", 0) / 100.0
                total_beacons = request.proof_data.get("total_beacons", 1)
                amount = base_amount * weight * uptime * (total_beacons / 100.0)
            
            elif request.credit_type == WorkCreditType.SESSION_PROCESSING:
                chunks_processed = request.proof_data.get("chunks_processed", 0)
                processing_time = request.proof_data.get("processing_time_ms", 1)
                efficiency = chunks_processed / (processing_time / 1000.0)  # chunks per second
                amount = base_amount * weight * (efficiency / 10.0)  # 10 chunks/s = 1x base
            
            elif request.credit_type == WorkCreditType.CHUNK_REPLICATION:
                replication_count = request.proof_data.get("replication_count", 0)
                storage_nodes = request.proof_data.get("storage_nodes", 1)
                redundancy = replication_count / storage_nodes
                amount = base_amount * weight * redundancy
            
            elif request.credit_type == WorkCreditType.NETWORK_ROUTING:
                routes_created = request.proof_data.get("routes_created", 0)
                packets_routed = request.proof_data.get("packets_routed", 0)
                amount = base_amount * weight * (routes_created / 10.0) * (packets_routed / 1000.0)
            
            elif request.credit_type == WorkCreditType.CONSENSUS_PARTICIPATION:
                contribution_score = request.proof_data.get("contribution_score", 0)
                amount = base_amount * weight * (contribution_score / 10.0)
            
            else:
                amount = base_amount * weight
            
            # Apply decay factor for recent work
            time_since_work = (datetime.now() - request.timestamp).total_seconds() / 3600.0  # hours
            decay_factor = self.credit_decay_factor ** (time_since_work / 24.0)  # daily decay
            
            final_amount = amount * decay_factor
            
            # Cap at maximum
            return min(final_amount, self.max_credit_per_type)
            
        except Exception as e:
            logger.error(f"Error calculating credit amount: {e}")
            return self.base_credit_amount
    
    async def _generate_credit_id(self, request: WorkCreditRequest) -> str:
        """Generate unique credit ID"""
        timestamp = int(time.time())
        node_hash = hashlib.sha256(request.node_id.encode()).hexdigest()[:8]
        type_hash = hashlib.sha256(request.credit_type.value.encode()).hexdigest()[:8]
        proof_hash = hashlib.sha256(json.dumps(request.proof_data, sort_keys=True).encode()).hexdigest()[:8]
        
        return f"credit_{timestamp}_{node_hash}_{type_hash}_{proof_hash}"
    
    async def _create_work_proof(self, request: WorkCreditRequest) -> Dict[str, Any]:
        """Create work proof data"""
        proof = {
            "proof_type": request.credit_type.value,
            "node_id": request.node_id,
            "timestamp": request.timestamp.isoformat() if request.timestamp else datetime.now().isoformat(),
            "proof_data": request.proof_data,
            "node_public_key": self.node_public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            ).hex()
        }
        
        return proof
    
    async def _sign_work_credit(self, credit_id: str, request: WorkCreditRequest, amount: float) -> str:
        """Sign work credit"""
        try:
            # Create signature data
            signature_data = {
                "credit_id": credit_id,
                "node_id": request.node_id,
                "credit_type": request.credit_type.value,
                "amount": amount,
                "timestamp": request.timestamp.isoformat() if request.timestamp else datetime.now().isoformat()
            }
            
            # Serialize data
            data_string = json.dumps(signature_data, sort_keys=True)
            data_bytes = data_string.encode()
            
            # Sign data
            signature = self.node_private_key.sign(data_bytes)
            
            return signature.hex()
            
        except Exception as e:
            logger.error(f"Error signing work credit: {e}")
            raise
    
    async def _verify_work_credit(self, credit_id: str):
        """Verify work credit with other nodes"""
        try:
            if credit_id not in self.credit_cache:
                logger.error(f"Credit not found for verification: {credit_id}")
                return
            
            work_credit = self.credit_cache[credit_id]
            
            # Simulate verification process
            await asyncio.sleep(1)
            
            # Check if enough nodes have verified
            verification_count = len(self.verification_cache.get(credit_id, []))
            total_nodes = 10  # This would be dynamic in production
            
            if verification_count >= (total_nodes * self.verification_threshold):
                # Mark as verified
                work_credit.status = WorkCreditStatus.VERIFIED
                work_credit.verified_at = datetime.now()
                work_credit.verifier_node_id = self.node_id
                
                await self._save_work_credits()
                
                # Log verification
                await self._log_work_credit_event(credit_id, "credit_verified", {
                    "verification_count": verification_count,
                    "total_nodes": total_nodes
                })
                
                logger.info(f"Work credit verified: {credit_id}")
            else:
                # Still pending verification
                logger.info(f"Work credit pending verification: {credit_id} ({verification_count}/{total_nodes})")
            
        except Exception as e:
            logger.error(f"Error verifying work credit: {e}")
    
    async def get_work_credits(self, node_id: Optional[str] = None, 
                             credit_type: Optional[WorkCreditType] = None,
                             status: Optional[WorkCreditStatus] = None) -> List[WorkCredit]:
        """Get work credits with optional filtering"""
        try:
            credits = list(self.credit_cache.values())
            
            # Apply filters
            if node_id:
                credits = [c for c in credits if c.node_id == node_id]
            
            if credit_type:
                credits = [c for c in credits if c.credit_type == credit_type]
            
            if status:
                credits = [c for c in credits if c.status == status]
            
            # Sort by timestamp (newest first)
            credits.sort(key=lambda x: x.timestamp, reverse=True)
            
            return credits
            
        except Exception as e:
            logger.error(f"Error getting work credits: {e}")
            return []
    
    async def get_credit_balance(self, node_id: str) -> float:
        """Get total credit balance for a node"""
        try:
            verified_credits = await self.get_work_credits(
                node_id=node_id,
                status=WorkCreditStatus.VERIFIED
            )
            
            total_balance = sum(credit.amount for credit in verified_credits)
            return total_balance
            
        except Exception as e:
            logger.error(f"Error getting credit balance: {e}")
            return 0.0
    
    async def get_credit_ranking(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get credit ranking of all nodes"""
        try:
            node_balances = {}
            
            # Calculate balances for all nodes
            for credit in self.credit_cache.values():
                if credit.status == WorkCreditStatus.VERIFIED:
                    if credit.node_id not in node_balances:
                        node_balances[credit.node_id] = 0.0
                    node_balances[credit.node_id] += credit.amount
            
            # Create ranking
            ranking = []
            for node_id, balance in node_balances.items():
                ranking.append({
                    "node_id": node_id,
                    "total_credits": balance,
                    "verified_credits": len([c for c in self.credit_cache.values() 
                                           if c.node_id == node_id and c.status == WorkCreditStatus.VERIFIED])
                })
            
            # Sort by total credits (descending)
            ranking.sort(key=lambda x: x["total_credits"], reverse=True)
            
            return ranking[:limit]
            
        except Exception as e:
            logger.error(f"Error getting credit ranking: {e}")
            return []
    
    async def _log_work_credit_event(self, credit_id: str, event_type: str, data: Dict[str, Any]):
        """Log work credit event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "credit_id": credit_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"work_credits_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging work credit event: {e}")
    
    async def cleanup_expired_credits(self, max_age_days: int = 30):
        """Clean up expired work credits"""
        try:
            cutoff_time = datetime.now() - timedelta(days=max_age_days)
            
            to_remove = []
            for credit_id, credit in self.credit_cache.items():
                if (credit.status in [WorkCreditStatus.REJECTED, WorkCreditStatus.EXPIRED] 
                    and credit.timestamp < cutoff_time):
                    to_remove.append(credit_id)
            
            for credit_id in to_remove:
                del self.credit_cache[credit_id]
            
            if to_remove:
                await self._save_work_credits()
                logger.info(f"Cleaned up {len(to_remove)} expired work credits")
                
        except Exception as e:
            logger.error(f"Error cleaning up expired credits: {e}")

# Global work credits calculator instance
work_credits_calculator = WorkCreditsCalculator()

# Convenience functions for external use
async def calculate_work_credits(request: WorkCreditRequest) -> WorkCreditResponse:
    """Calculate work credits for a given request"""
    return await work_credits_calculator.calculate_work_credits(request)

async def get_work_credits(node_id: Optional[str] = None, 
                         credit_type: Optional[WorkCreditType] = None,
                         status: Optional[WorkCreditStatus] = None) -> List[WorkCredit]:
    """Get work credits with optional filtering"""
    return await work_credits_calculator.get_work_credits(node_id, credit_type, status)

async def get_credit_balance(node_id: str) -> float:
    """Get total credit balance for a node"""
    return await work_credits_calculator.get_credit_balance(node_id)

async def get_credit_ranking(limit: int = 100) -> List[Dict[str, Any]]:
    """Get credit ranking of all nodes"""
    return await work_credits_calculator.get_credit_ranking(limit)

if __name__ == "__main__":
    # Example usage
    async def main():
        # Create a work credit request
        request = WorkCreditRequest(
            node_id="node-001",
            credit_type=WorkCreditType.RELAY_BANDWIDTH,
            proof_data={
                "bytes_relayed": 1024000,
                "duration_seconds": 60,
                "bandwidth_mbps": 10.0
            },
            amount=5.0
        )
        
        response = await calculate_work_credits(request)
        print(f"Work credits calculated: {response}")
        
        # Get credit balance
        balance = await get_credit_balance("node-001")
        print(f"Credit balance: {balance}")
    
    asyncio.run(main())
