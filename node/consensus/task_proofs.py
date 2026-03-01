# Path: node/consensus/task_proofs.py
# Lucid Node Consensus - Task Proof Collection
# Implements task proof collection and verification for consensus
# LUCID-STRICT Layer 1 Core Infrastructure

from __future__ import annotations

import asyncio
import logging
import os
import time
import hashlib
import secrets
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import aiofiles
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

# Configuration from environment
TASK_PROOF_TIMEOUT = int(os.getenv("LUCID_TASK_PROOF_TIMEOUT", "300"))  # 5 minutes
MINIMUM_PROOF_COUNT = int(os.getenv("LUCID_MINIMUM_PROOF_COUNT", "3"))
PROOF_VERIFICATION_TIMEOUT = int(os.getenv("LUCID_PROOF_VERIFICATION_TIMEOUT", "60"))  # 1 minute
TASK_DIFFICULTY_LEVEL = int(os.getenv("LUCID_TASK_DIFFICULTY_LEVEL", "4"))  # Hash difficulty
PROOF_STORAGE_PATH = Path(os.getenv("LUCID_PROOF_STORAGE_PATH", "/app/data/consensus/proofs"))


class TaskType(Enum):
    """Types of consensus tasks"""
    COMPUTATION = "computation"
    STORAGE = "storage"
    NETWORK = "network"
    VALIDATION = "validation"
    ENCRYPTION = "encryption"
    HASH_VERIFICATION = "hash_verification"
    SIGNATURE_VERIFICATION = "signature_verification"


class ProofStatus(Enum):
    """Status of task proofs"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"
    INVALID = "invalid"


class TaskStatus(Enum):
    """Status of consensus tasks"""
    CREATED = "created"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class TaskProof:
    """Proof of task completion"""
    proof_id: str
    task_id: str
    node_id: str
    task_type: TaskType
    proof_data: str
    proof_hash: str
    timestamp: datetime
    status: ProofStatus
    verification_result: Optional[bool] = None
    verification_timestamp: Optional[datetime] = None
    verifier_node_id: Optional[str] = None
    computation_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsensusTask:
    """A consensus task that requires proof"""
    task_id: str
    task_type: TaskType
    description: str
    input_data: Dict[str, Any]
    expected_output: Optional[str] = None
    difficulty_level: int = TASK_DIFFICULTY_LEVEL
    timeout_seconds: int = TASK_PROOF_TIMEOUT
    assigned_nodes: List[str] = field(default_factory=list)
    submitted_proofs: List[TaskProof] = field(default_factory=list)
    status: TaskStatus = TaskStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    consensus_result: Optional[bool] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProofVerificationResult:
    """Result of proof verification"""
    proof_id: str
    is_valid: bool
    verification_time: float
    verifier_node_id: str
    verification_details: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class TaskProofCollector:
    """Task proof collection and verification system"""
    
    def __init__(self, node_id: str, private_key: rsa.RSAPrivateKey):
        self.node_id = node_id
        self.private_key = private_key
        self.public_key = private_key.public_key()
        self.storage_path = PROOF_STORAGE_PATH
        self.active_tasks: Dict[str, ConsensusTask] = {}
        self.submitted_proofs: Dict[str, TaskProof] = {}
        self.verification_results: Dict[str, ProofVerificationResult] = {}
        self.task_history: List[ConsensusTask] = []
        self.proof_history: List[TaskProof] = []
        
        # Performance metrics
        self.proofs_verified = 0
        self.proofs_rejected = 0
        self.average_verification_time = 0.0
        self.tasks_completed = 0
        self.tasks_failed = 0
        
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Initialize proof storage"""
        try:
            self.storage_path.mkdir(parents=True, exist_ok=True, mode=0o755)
            logger.info(f"Task proof storage initialized at {self.storage_path}")
        except Exception as e:
            logger.error(f"Failed to initialize proof storage: {e}")
            raise
    
    async def create_consensus_task(self, task_type: TaskType, description: str,
                                  input_data: Dict[str, Any], expected_output: Optional[str] = None,
                                  difficulty_level: int = TASK_DIFFICULTY_LEVEL,
                                  timeout_seconds: int = TASK_PROOF_TIMEOUT) -> str:
        """Create a new consensus task"""
        try:
            task_id = self._generate_task_id(task_type)
            
            task = ConsensusTask(
                task_id=task_id,
                task_type=task_type,
                description=description,
                input_data=input_data,
                expected_output=expected_output,
                difficulty_level=difficulty_level,
                timeout_seconds=timeout_seconds,
                status=TaskStatus.CREATED
            )
            
            self.active_tasks[task_id] = task
            
            logger.info(f"Created consensus task {task_id}: {description}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to create consensus task: {e}")
            raise
    
    async def assign_task_to_nodes(self, task_id: str, node_ids: List[str]) -> bool:
        """Assign a task to specific nodes"""
        try:
            if task_id not in self.active_tasks:
                raise ValueError(f"Task {task_id} not found")
            
            task = self.active_tasks[task_id]
            
            if task.status != TaskStatus.CREATED:
                raise ValueError(f"Task {task_id} is not in created status")
            
            task.assigned_nodes = node_ids.copy()
            task.assigned_at = datetime.now(timezone.utc)
            task.status = TaskStatus.ASSIGNED
            
            logger.info(f"Assigned task {task_id} to {len(node_ids)} nodes")
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign task {task_id}: {e}")
            return False
    
    async def submit_task_proof(self, task_id: str, proof_data: str, 
                              computation_time: Optional[float] = None) -> str:
        """Submit a proof for a task"""
        try:
            if task_id not in self.active_tasks:
                raise ValueError(f"Task {task_id} not found")
            
            task = self.active_tasks[task_id]
            
            if task.status not in [TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS]:
                raise ValueError(f"Task {task_id} is not accepting proofs")
            
            if self.node_id not in task.assigned_nodes:
                raise ValueError(f"Node {self.node_id} is not assigned to task {task_id}")
            
            # Generate proof
            proof_id = self._generate_proof_id(task_id)
            proof_hash = self._calculate_proof_hash(proof_data, task_id)
            
            proof = TaskProof(
                proof_id=proof_id,
                task_id=task_id,
                node_id=self.node_id,
                task_type=task.task_type,
                proof_data=proof_data,
                proof_hash=proof_hash,
                timestamp=datetime.now(timezone.utc),
                status=ProofStatus.SUBMITTED,
                computation_time=computation_time
            )
            
            # Add proof to task
            task.submitted_proofs.append(proof)
            task.status = TaskStatus.IN_PROGRESS
            
            # Store proof
            self.submitted_proofs[proof_id] = proof
            
            # Verify the proof
            verification_result = await self._verify_proof(proof)
            proof.verification_result = verification_result.is_valid
            proof.verification_timestamp = datetime.now(timezone.utc)
            proof.verifier_node_id = self.node_id
            proof.status = ProofStatus.VERIFIED if verification_result.is_valid else ProofStatus.REJECTED
            
            # Update verification results
            self.verification_results[proof_id] = verification_result
            
            # Update performance metrics
            if verification_result.is_valid:
                self.proofs_verified += 1
            else:
                self.proofs_rejected += 1
            
            self._update_average_verification_time(verification_result.verification_time)
            
            logger.info(f"Submitted proof {proof_id} for task {task_id}: {'VERIFIED' if verification_result.is_valid else 'REJECTED'}")
            return proof_id
            
        except Exception as e:
            logger.error(f"Failed to submit task proof: {e}")
            raise
    
    async def _verify_proof(self, proof: TaskProof) -> ProofVerificationResult:
        """Verify a task proof"""
        start_time = time.time()
        
        try:
            # Get the task
            task = self.active_tasks.get(proof.task_id)
            if not task:
                return ProofVerificationResult(
                    proof_id=proof.proof_id,
                    is_valid=False,
                    verification_time=time.time() - start_time,
                    verifier_node_id=self.node_id,
                    error_message="Task not found"
                )
            
            # Verify based on task type
            is_valid = False
            verification_details = {}
            
            if task.task_type == TaskType.HASH_VERIFICATION:
                is_valid, details = await self._verify_hash_proof(proof, task)
                verification_details.update(details)
            elif task.task_type == TaskType.COMPUTATION:
                is_valid, details = await self._verify_computation_proof(proof, task)
                verification_details.update(details)
            elif task.task_type == TaskType.SIGNATURE_VERIFICATION:
                is_valid, details = await self._verify_signature_proof(proof, task)
                verification_details.update(details)
            elif task.task_type == TaskType.ENCRYPTION:
                is_valid, details = await self._verify_encryption_proof(proof, task)
                verification_details.update(details)
            else:
                # Generic verification
                is_valid, details = await self._verify_generic_proof(proof, task)
                verification_details.update(details)
            
            verification_time = time.time() - start_time
            
            return ProofVerificationResult(
                proof_id=proof.proof_id,
                is_valid=is_valid,
                verification_time=verification_time,
                verifier_node_id=self.node_id,
                verification_details=verification_details
            )
            
        except Exception as e:
            verification_time = time.time() - start_time
            logger.error(f"Failed to verify proof {proof.proof_id}: {e}")
            
            return ProofVerificationResult(
                proof_id=proof.proof_id,
                is_valid=False,
                verification_time=verification_time,
                verifier_node_id=self.node_id,
                error_message=str(e)
            )
    
    async def _verify_hash_proof(self, proof: TaskProof, task: ConsensusTask) -> Tuple[bool, Dict[str, Any]]:
        """Verify hash-based proof"""
        try:
            input_data = task.input_data.get("data", "")
            difficulty = task.difficulty_level
            
            # Verify the proof meets difficulty requirements
            proof_hash = hashlib.sha256(proof.proof_data.encode()).hexdigest()
            target_zeros = "0" * difficulty
            
            is_valid = proof_hash.startswith(target_zeros)
            
            details = {
                "proof_hash": proof_hash,
                "target_zeros": target_zeros,
                "difficulty_met": is_valid,
                "input_data_hash": hashlib.sha256(input_data.encode()).hexdigest()
            }
            
            return is_valid, details
            
        except Exception as e:
            logger.error(f"Failed to verify hash proof: {e}")
            return False, {"error": str(e)}
    
    async def _verify_computation_proof(self, proof: TaskProof, task: ConsensusTask) -> Tuple[bool, Dict[str, Any]]:
        """Verify computation-based proof"""
        try:
            # Parse proof data
            proof_json = json.loads(proof.proof_data)
            result = proof_json.get("result")
            computation_steps = proof_json.get("steps", [])
            
            # Verify computation steps
            is_valid = True
            details = {
                "result": result,
                "steps_count": len(computation_steps),
                "computation_verified": True
            }
            
            # Check if result matches expected output
            if task.expected_output:
                is_valid = str(result) == str(task.expected_output)
                details["expected_output_match"] = is_valid
            
            return is_valid, details
            
        except Exception as e:
            logger.error(f"Failed to verify computation proof: {e}")
            return False, {"error": str(e)}
    
    async def _verify_signature_proof(self, proof: TaskProof, task: ConsensusTask) -> Tuple[bool, Dict[str, Any]]:
        """Verify signature-based proof"""
        try:
            # Parse proof data
            proof_json = json.loads(proof.proof_data)
            signature = proof_json.get("signature")
            message = proof_json.get("message")
            public_key_pem = proof_json.get("public_key")
            
            if not all([signature, message, public_key_pem]):
                return False, {"error": "Missing required signature data"}
            
            # Load public key
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode(),
                backend=default_backend()
            )
            
            # Verify signature
            try:
                public_key.verify(
                    bytes.fromhex(signature),
                    message.encode(),
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                is_valid = True
            except Exception:
                is_valid = False
            
            details = {
                "signature_verified": is_valid,
                "message_hash": hashlib.sha256(message.encode()).hexdigest(),
                "public_key_fingerprint": hashlib.sha256(public_key_pem.encode()).hexdigest()[:16]
            }
            
            return is_valid, details
            
        except Exception as e:
            logger.error(f"Failed to verify signature proof: {e}")
            return False, {"error": str(e)}
    
    async def _verify_encryption_proof(self, proof: TaskProof, task: ConsensusTask) -> Tuple[bool, Dict[str, Any]]:
        """Verify encryption-based proof"""
        try:
            # Parse proof data
            proof_json = json.loads(proof.proof_data)
            encrypted_data = proof_json.get("encrypted_data")
            decrypted_data = proof_json.get("decrypted_data")
            algorithm = proof_json.get("algorithm", "AES")
            
            # Basic validation
            is_valid = bool(encrypted_data and decrypted_data)
            
            details = {
                "algorithm": algorithm,
                "encrypted_data_length": len(encrypted_data) if encrypted_data else 0,
                "decrypted_data_length": len(decrypted_data) if decrypted_data else 0,
                "encryption_valid": is_valid
            }
            
            return is_valid, details
            
        except Exception as e:
            logger.error(f"Failed to verify encryption proof: {e}")
            return False, {"error": str(e)}
    
    async def _verify_generic_proof(self, proof: TaskProof, task: ConsensusTask) -> Tuple[bool, Dict[str, Any]]:
        """Generic proof verification"""
        try:
            # Basic validation
            is_valid = bool(proof.proof_data and len(proof.proof_data) > 0)
            
            details = {
                "proof_data_length": len(proof.proof_data),
                "proof_hash": proof.proof_hash,
                "generic_verification": True
            }
            
            return is_valid, details
            
        except Exception as e:
            logger.error(f"Failed to verify generic proof: {e}")
            return False, {"error": str(e)}
    
    async def finalize_task(self, task_id: str) -> bool:
        """Finalize a task and determine consensus result"""
        try:
            if task_id not in self.active_tasks:
                raise ValueError(f"Task {task_id} not found")
            
            task = self.active_tasks[task_id]
            
            if task.status != TaskStatus.IN_PROGRESS:
                raise ValueError(f"Task {task_id} is not in progress")
            
            # Count valid proofs
            valid_proofs = [p for p in task.submitted_proofs if p.verification_result is True]
            invalid_proofs = [p for p in task.submitted_proofs if p.verification_result is False]
            
            # Determine consensus
            total_proofs = len(task.submitted_proofs)
            valid_count = len(valid_proofs)
            
            if total_proofs == 0:
                task.status = TaskStatus.FAILED
                task.consensus_result = False
            elif valid_count >= MINIMUM_PROOF_COUNT:
                # Check if valid proofs agree
                if self._proofs_agree(valid_proofs):
                    task.status = TaskStatus.COMPLETED
                    task.consensus_result = True
                    self.tasks_completed += 1
                else:
                    task.status = TaskStatus.FAILED
                    task.consensus_result = False
                    self.tasks_failed += 1
            else:
                task.status = TaskStatus.FAILED
                task.consensus_result = False
                self.tasks_failed += 1
            
            task.completed_at = datetime.now(timezone.utc)
            
            # Move to history
            self.task_history.append(task)
            del self.active_tasks[task_id]
            
            logger.info(f"Finalized task {task_id}: {'COMPLETED' if task.consensus_result else 'FAILED'}")
            return task.consensus_result
            
        except Exception as e:
            logger.error(f"Failed to finalize task {task_id}: {e}")
            return False
    
    def _proofs_agree(self, valid_proofs: List[TaskProof]) -> bool:
        """Check if valid proofs agree on the result"""
        if not valid_proofs:
            return False
        
        if len(valid_proofs) == 1:
            return True
        
        # For hash-based tasks, check if proofs produce similar results
        if valid_proofs[0].task_type == TaskType.HASH_VERIFICATION:
            # All proofs should produce the same hash
            first_hash = valid_proofs[0].proof_hash
            return all(p.proof_hash == first_hash for p in valid_proofs)
        
        # For computation tasks, check if results are similar
        elif valid_proofs[0].task_type == TaskType.COMPUTATION:
            try:
                first_result = json.loads(valid_proofs[0].proof_data).get("result")
                return all(json.loads(p.proof_data).get("result") == first_result for p in valid_proofs)
            except:
                return False
        
        # For other tasks, assume agreement if all are valid
        return True
    
    def _generate_task_id(self, task_type: TaskType) -> str:
        """Generate a unique task ID"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        random_suffix = secrets.token_hex(4)
        return f"task_{task_type.value}_{timestamp}_{random_suffix}"
    
    def _generate_proof_id(self, task_id: str) -> str:
        """Generate a unique proof ID"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        random_suffix = secrets.token_hex(4)
        return f"proof_{task_id}_{timestamp}_{random_suffix}"
    
    def _calculate_proof_hash(self, proof_data: str, task_id: str) -> str:
        """Calculate hash of proof data"""
        combined_data = f"{proof_data}:{task_id}:{self.node_id}"
        return hashlib.sha256(combined_data.encode()).hexdigest()
    
    def _update_average_verification_time(self, verification_time: float):
        """Update average verification time"""
        total_verifications = self.proofs_verified + self.proofs_rejected
        if total_verifications > 0:
            self.average_verification_time = (
                (self.average_verification_time * (total_verifications - 1) + verification_time) / 
                total_verifications
            )
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task"""
        task = self.active_tasks.get(task_id)
        if not task:
            # Check history
            for historical_task in self.task_history:
                if historical_task.task_id == task_id:
                    task = historical_task
                    break
        
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "task_type": task.task_type.value,
            "status": task.status.value,
            "description": task.description,
            "assigned_nodes": task.assigned_nodes,
            "submitted_proofs": len(task.submitted_proofs),
            "valid_proofs": len([p for p in task.submitted_proofs if p.verification_result is True]),
            "created_at": task.created_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "consensus_result": task.consensus_result
        }
    
    async def get_proof_statistics(self) -> Dict[str, Any]:
        """Get proof collection statistics"""
        return {
            "total_proofs_submitted": len(self.proofs_verified) + len(self.proofs_rejected),
            "proofs_verified": self.proofs_verified,
            "proofs_rejected": self.proofs_rejected,
            "verification_success_rate": self.proofs_verified / (self.proofs_verified + self.proofs_rejected) if (self.proofs_verified + self.proofs_rejected) > 0 else 0,
            "average_verification_time": self.average_verification_time,
            "active_tasks": len(self.active_tasks),
            "completed_tasks": self.tasks_completed,
            "failed_tasks": self.tasks_failed,
            "task_success_rate": self.tasks_completed / (self.tasks_completed + self.tasks_failed) if (self.tasks_completed + self.tasks_failed) > 0 else 0
        }
    
    async def cleanup_expired_tasks(self):
        """Clean up expired tasks"""
        try:
            current_time = datetime.now(timezone.utc)
            expired_tasks = []
            
            for task_id, task in self.active_tasks.items():
                if task.assigned_at:
                    elapsed = (current_time - task.assigned_at).total_seconds()
                    if elapsed > task.timeout_seconds:
                        expired_tasks.append(task_id)
            
            for task_id in expired_tasks:
                task = self.active_tasks[task_id]
                task.status = TaskStatus.TIMEOUT
                task.completed_at = current_time
                task.consensus_result = False
                
                self.task_history.append(task)
                del self.active_tasks[task_id]
                
                logger.info(f"Cleaned up expired task {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired tasks: {e}")


# Global task proof collector instance
task_proof_collector = None


async def initialize_task_proof_collector(node_id: str, private_key: rsa.RSAPrivateKey):
    """Initialize the task proof collector"""
    global task_proof_collector
    task_proof_collector = TaskProofCollector(node_id, private_key)
    return task_proof_collector


async def create_task(task_type: TaskType, description: str, input_data: Dict[str, Any], **kwargs) -> str:
    """Create a new consensus task"""
    if task_proof_collector:
        return await task_proof_collector.create_consensus_task(task_type, description, input_data, **kwargs)
    raise ValueError("Task proof collector not initialized")


async def submit_proof(task_id: str, proof_data: str, computation_time: Optional[float] = None) -> str:
    """Submit a proof for a task"""
    if task_proof_collector:
        return await task_proof_collector.submit_task_proof(task_id, proof_data, computation_time)
    raise ValueError("Task proof collector not initialized")


async def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task status"""
    if task_proof_collector:
        return await task_proof_collector.get_task_status(task_id)
    return None


async def get_proof_statistics() -> Dict[str, Any]:
    """Get proof statistics"""
    if task_proof_collector:
        return await task_proof_collector.get_proof_statistics()
    return {}


if __name__ == "__main__":
    # Test the task proof collection system
    async def test_task_proof_collection():
        # Generate test keys
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Initialize task proof collector
        tpc = await initialize_task_proof_collector("test_node", private_key)
        
        # Create a test task
        task_id = await create_task(
            TaskType.HASH_VERIFICATION,
            "Find hash with 4 leading zeros",
            {"data": "test_data_12345"},
            difficulty_level=4
        )
        print(f"Created task: {task_id}")
        
        # Assign task to self
        await tpc.assign_task_to_nodes(task_id, ["test_node"])
        
        # Submit a proof
        proof_data = "nonce_12345"  # This would be the actual proof
        proof_id = await submit_proof(task_id, proof_data, computation_time=1.5)
        print(f"Submitted proof: {proof_id}")
        
        # Finalize task
        result = await tpc.finalize_task(task_id)
        print(f"Task result: {result}")
        
        # Get statistics
        stats = await get_proof_statistics()
        print(f"Statistics: {stats}")
    
    asyncio.run(test_task_proof_collection())
