"""
File: /app/node/validation/work_credits.py
x-lucid-file-path: /app/node/validation/work_credits.py
x-lucid-file-type: python

Lucid RDP Node Work Credits - Specialized Work Credits Calculation
parameters for work credits calculations
Based on LUCID-STRICT requirements per Spec-1b

Classes:
- WorkCreditType: Work credit type enumeration
- WorkCreditStatus: Work credit status enumeration
- WorkCredit: Work credit data model
- WorkCreditRequest: Work credit request model
- WorkCreditResponse: Work credit response model
- WorkCreditHistory: Work credit history model
- WorkCreditStats: Work credit statistics model
- WorkCreditReport: Work credit report model
- WorkCreditSettings: Work credit settings model
- WorkCreditPreferences: Work credit preferences model
- WorkCreditVerification: Work credit verification model
- WorkCreditValidation: Work credit validation model
- WorkCreditValidationRequest: Work credit validation request model
- WorkCreditValidationResponse: Work credit validation response model
- WorkCreditValidationHistory: Work credit validation history model
- WorkCreditValidationStats: Work credit validation statistics model
- WorkCreditValidationReport: Work credit validation report model
- WorkCreditValidationSettings: Work credit validation settings model
- WorkCreditValidationPreferences: Work credit validation preferences model
- WorkCreditValidationVerification: Work credit validation verification model
- WorkCreditsCalculator: Work credits calculator class
"""

from __future__ import annotations
import asyncio
import logging
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import json
from decimal import Decimal
import secrets
import dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Load environment variables
dotenv.load_dotenv(".env.node_validation")

# Environment variables
LUCID_NODE_ID = os.getenv("LUCID_NODE_ID", "unknown_node")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
LUCID_BLOCKCHAIN_DATABASE = os.getenv("LUCID_BLOCKCHAIN_DATABASE", "blockchain_db")
LUCID_NODE_DATABASE = os.getenv("LUCID_NODE_DATABASE", "node_db")
LUCID_SESSION_DATABASE = os.getenv("LUCID_SESSION_DATABASE", "session_db")
WORK_CREDITS_COLLECTION = os.getenv("WORK_CREDITS_COLLECTION", "work_credits")
WORK_CREDITS_HISTORY_COLLECTION = os.getenv("WORK_CREDITS_HISTORY_COLLECTION", "work_credits_history")
WORK_CREDITS_VALIDATION_COLLECTION = os.getenv("WORK_CREDITS_VALIDATION_COLLECTION", "work_credits_validation")

# Work credit point assignments from environment
RELAY_BANDWIDTH_POINTS = float(os.getenv("RELAY_BANDWIDTH_POINTS", "1.25"))
STORAGE_AVAILABILITY_POINTS = float(os.getenv("STORAGE_AVAILABILITY_POINTS", "1.5"))
VALIDATION_SIGNATURE_POINTS = float(os.getenv("VALIDATION_SIGNATURE_POINTS", "2.0"))
UPTIME_BEACON_POINTS = float(os.getenv("UPTIME_BEACON_POINTS", "0.5"))
SESSION_PROCESSING_POINTS = float(os.getenv("SESSION_PROCESSING_POINTS", "1.0"))
CHUNK_REPLICATION_POINTS = float(os.getenv("CHUNK_REPLICATION_POINTS", "1.0"))
NETWORK_ROUTING_POINTS = float(os.getenv("NETWORK_ROUTING_POINTS", "0.75"))
CONSENSUS_PARTICIPATION_POINTS = float(os.getenv("CONSENSUS_PARTICIPATION_POINTS", "3.0"))

# Settings
WORK_CREDITS_VERIFICATION_REQUIRED = os.getenv("WORK_CREDITS_VERIFICATION_REQUIRED", "true").lower() == "true"
WORK_CREDITS_SIGNATURE_ALGORITHM = os.getenv("WORK_CREDITS_SIGNATURE_ALGORITHM", "sha256")
WORK_CREDITS_EXPIRATION_DAYS = int(os.getenv("WORK_CREDITS_EXPIRATION_DAYS", "30"))

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkCreditType(Enum):
    """Types of work credits"""
    RELAY_BANDWIDTH = "relay_bandwidth"
    STORAGE_AVAILABILITY = "storage_availability"
    VALIDATION_SIGNATURE = "validation_signature"
    UPTIME_BEACON = "uptime_beacon"
    SESSION_PROCESSING = "session_processing"
    CHUNK_REPLICATION = "chunk_replication"
    NETWORK_ROUTING = "network_routing"
    CONSENSUS_PARTICIPATION = "consensus_participation"


class WorkCreditStatus(Enum):
    """Work credit status"""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CLAIMED = "claimed"


class WorkCreditValidationStatus(Enum):
    """Work credit validation status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISPUTED = "disputed"


@dataclass
class WorkCredit:
    """Work credit data model"""
    work_credit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str = ""
    work_credit_type: WorkCreditType = WorkCreditType.RELAY_BANDWIDTH
    work_credit_amount: float = 0.0
    work_credit_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    work_credit_proof_data: Dict[str, Any] = field(default_factory=dict)
    work_credit_signature: str = ""
    work_credit_status: WorkCreditStatus = WorkCreditStatus.PENDING
    work_credit_verified_at: Optional[datetime] = None
    work_credit_verifier_node_id: Optional[str] = None
    work_credit_verified: bool = False
    work_credit_expiration_date: Optional[datetime] = None
    work_credit_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkCreditRequest:
    """Work credit request model"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str = ""
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    work_credit_type: WorkCreditType = WorkCreditType.RELAY_BANDWIDTH
    amount: float = 0.0
    proof_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkCreditResponse:
    """Work credit response model"""
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    work_credit: Optional[WorkCredit] = None
    status: str = "pending"
    message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkCreditHistory:
    """Work credit history model"""
    history_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    work_credit_id: str = ""
    node_id: str = ""
    action: str = ""
    previous_status: str = ""
    new_status: str = ""
    changed_by: str = ""
    changed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""


@dataclass
class WorkCreditStats:
    """Work credit statistics model"""
    stats_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str = ""
    total_credits: float = 0.0
    total_verified_credits: float = 0.0
    total_pending_credits: float = 0.0
    total_rejected_credits: float = 0.0
    total_operations: int = 0
    by_type: Dict[str, float] = field(default_factory=dict)
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkCreditReport:
    """Work credit report model"""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str = ""
    period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stats: WorkCreditStats = field(default_factory=WorkCreditStats)
    top_operations: List[Dict[str, Any]] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkCreditSettings:
    """Work credit settings model"""
    settings_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str = ""
    verification_required: bool = WORK_CREDITS_VERIFICATION_REQUIRED
    signature_algorithm: str = WORK_CREDITS_SIGNATURE_ALGORITHM
    expiration_days: int = WORK_CREDITS_EXPIRATION_DAYS
    operation_points: Dict[str, float] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkCreditPreferences:
    """Work credit preferences model"""
    preference_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str = ""
    auto_claim_credits: bool = False
    notification_enabled: bool = True
    preferred_operation_types: List[WorkCreditType] = field(default_factory=list)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkCreditVerification:
    """Work credit verification model"""
    verification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    work_credit_id: str = ""
    verifier_node_id: str = ""
    verification_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verification_signature: str = ""
    verification_status: str = "pending"
    verification_notes: str = ""
    verification_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkCreditValidation:
    """Work credit validation model"""
    validation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    work_credit_id: str = ""
    validation_type: str = ""
    validation_status: WorkCreditValidationStatus = WorkCreditValidationStatus.PENDING
    validation_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    validation_result: bool = False
    validation_notes: str = ""
    validation_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkCreditValidationRequest:
    """Work credit validation request model"""
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    work_credit_id: str = ""
    requestor_node_id: str = ""
    validation_type: str = ""
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkCreditValidationResponse:
    """Work credit validation response model"""
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    validation: Optional[WorkCreditValidation] = None
    status: str = "pending"
    message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkCreditValidationHistory:
    """Work credit validation history model"""
    history_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    validation_id: str = ""
    work_credit_id: str = ""
    action: str = ""
    previous_status: str = ""
    new_status: str = ""
    changed_by: str = ""
    changed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    notes: str = ""


@dataclass
class WorkCreditValidationStats:
    """Work credit validation statistics model"""
    stats_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    work_credit_id: str = ""
    total_validations: int = 0
    approved_validations: int = 0
    rejected_validations: int = 0
    disputed_validations: int = 0
    average_validation_time: float = 0.0
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkCreditValidationReport:
    """Work credit validation report model"""
    report_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    work_credit_id: str = ""
    period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stats: WorkCreditValidationStats = field(default_factory=WorkCreditValidationStats)
    validations: List[WorkCreditValidation] = field(default_factory=list)
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkCreditValidationSettings:
    """Work credit validation settings model"""
    settings_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    validation_algorithm: str = "majority_consensus"
    required_validators: int = 3
    approval_threshold: float = 0.66
    validation_timeout_seconds: int = 3600
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkCreditValidationPreferences:
    """Work credit validation preferences model"""
    preference_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str = ""
    participate_in_validation: bool = True
    validation_response_time_preference: int = 300
    validation_types_supported: List[str] = field(default_factory=list)
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkCreditValidationVerification:
    """Work credit validation verification model"""
    verification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    validation_id: str = ""
    verifier_node_id: str = ""
    verification_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verification_signature: str = ""
    verification_status: str = "pending"
    verification_notes: str = ""


class WorkCreditsCalculator:
    """Work credits calculator class with MongoDB integration"""
    
    # Operation points mapping from environment
    OPERATION_POINTS = {
        WorkCreditType.RELAY_BANDWIDTH: RELAY_BANDWIDTH_POINTS,
        WorkCreditType.STORAGE_AVAILABILITY: STORAGE_AVAILABILITY_POINTS,
        WorkCreditType.VALIDATION_SIGNATURE: VALIDATION_SIGNATURE_POINTS,
        WorkCreditType.UPTIME_BEACON: UPTIME_BEACON_POINTS,
        WorkCreditType.SESSION_PROCESSING: SESSION_PROCESSING_POINTS,
        WorkCreditType.CHUNK_REPLICATION: CHUNK_REPLICATION_POINTS,
        WorkCreditType.NETWORK_ROUTING: NETWORK_ROUTING_POINTS,
        WorkCreditType.CONSENSUS_PARTICIPATION: CONSENSUS_PARTICIPATION_POINTS,
    }
    
    def __init__(self, node_id: str = LUCID_NODE_ID):
        """Initialize WorkCreditsCalculator
        
        Args:
            node_id: The node ID to calculate credits for
        """
        self.node_id = node_id
        self.mongo_uri = MONGODB_URI
        self.blockchain_db_name = LUCID_BLOCKCHAIN_DATABASE
        self.node_db_name = LUCID_NODE_DATABASE
        self.session_db_name = LUCID_SESSION_DATABASE
        
        # MongoDB client
        self._client: Optional[MongoClient] = None
        self._blockchain_db = None
        self._node_db = None
        self._session_db = None
        
        self._connect_mongodb()
    
    def _connect_mongodb(self) -> bool:
        """Connect to MongoDB
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self._client = MongoClient(self.mongo_uri)
            self._client.admin.command('ping')
            self._blockchain_db = self._client[self.blockchain_db_name]
            self._node_db = self._client[self.node_db_name]
            self._session_db = self._client[self.session_db_name]
            logger.info(f"Connected to MongoDB for node {self.node_id}")
            return True
        except PyMongoError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
    
    def count_relay_bandwidth(self) -> int:
        """Count relay bandwidth operations"""
        try:
            collection = self._blockchain_db[WORK_CREDITS_COLLECTION]
            count = collection.count_documents({
                'node_id': self.node_id,
                'work_credit_type': WorkCreditType.RELAY_BANDWIDTH.value,
                'work_credit_status': {'$in': [WorkCreditStatus.VERIFIED.value, WorkCreditStatus.CLAIMED.value]}
            })
            return count
        except PyMongoError as e:
            logger.error(f"Failed to count relay bandwidth operations: {e}")
            return 0
    
    def count_storage_availability(self) -> int:
        """Count storage availability operations"""
        try:
            collection = self._blockchain_db[WORK_CREDITS_COLLECTION]
            count = collection.count_documents({
                'node_id': self.node_id,
                'work_credit_type': WorkCreditType.STORAGE_AVAILABILITY.value,
                'work_credit_status': {'$in': [WorkCreditStatus.VERIFIED.value, WorkCreditStatus.CLAIMED.value]}
            })
            return count
        except PyMongoError as e:
            logger.error(f"Failed to count storage availability operations: {e}")
            return 0
    
    def count_validation_signature(self) -> int:
        """Count validation signature operations"""
        try:
            collection = self._blockchain_db[WORK_CREDITS_COLLECTION]
            count = collection.count_documents({
                'node_id': self.node_id,
                'work_credit_type': WorkCreditType.VALIDATION_SIGNATURE.value,
                'work_credit_status': {'$in': [WorkCreditStatus.VERIFIED.value, WorkCreditStatus.CLAIMED.value]}
            })
            return count
        except PyMongoError as e:
            logger.error(f"Failed to count validation signature operations: {e}")
            return 0
    
    def count_uptime_beacon(self) -> int:
        """Count uptime beacon operations"""
        try:
            collection = self._blockchain_db[WORK_CREDITS_COLLECTION]
            count = collection.count_documents({
                'node_id': self.node_id,
                'work_credit_type': WorkCreditType.UPTIME_BEACON.value,
                'work_credit_status': {'$in': [WorkCreditStatus.VERIFIED.value, WorkCreditStatus.CLAIMED.value]}
            })
            return count
        except PyMongoError as e:
            logger.error(f"Failed to count uptime beacon operations: {e}")
            return 0
    
    def count_session_processing(self) -> int:
        """Count session processing operations"""
        try:
            collection = self._blockchain_db[WORK_CREDITS_COLLECTION]
            count = collection.count_documents({
                'node_id': self.node_id,
                'work_credit_type': WorkCreditType.SESSION_PROCESSING.value,
                'work_credit_status': {'$in': [WorkCreditStatus.VERIFIED.value, WorkCreditStatus.CLAIMED.value]}
            })
            return count
        except PyMongoError as e:
            logger.error(f"Failed to count session processing operations: {e}")
            return 0
    
    def count_chunk_replication(self) -> int:
        """Count chunk replication operations"""
        try:
            collection = self._blockchain_db[WORK_CREDITS_COLLECTION]
            count = collection.count_documents({
                'node_id': self.node_id,
                'work_credit_type': WorkCreditType.CHUNK_REPLICATION.value,
                'work_credit_status': {'$in': [WorkCreditStatus.VERIFIED.value, WorkCreditStatus.CLAIMED.value]}
            })
            return count
        except PyMongoError as e:
            logger.error(f"Failed to count chunk replication operations: {e}")
            return 0
    
    def count_network_routing(self) -> int:
        """Count network routing operations"""
        try:
            collection = self._blockchain_db[WORK_CREDITS_COLLECTION]
            count = collection.count_documents({
                'node_id': self.node_id,
                'work_credit_type': WorkCreditType.NETWORK_ROUTING.value,
                'work_credit_status': {'$in': [WorkCreditStatus.VERIFIED.value, WorkCreditStatus.CLAIMED.value]}
            })
            return count
        except PyMongoError as e:
            logger.error(f"Failed to count network routing operations: {e}")
            return 0
    
    def count_consensus_participation(self) -> int:
        """Count consensus participation operations"""
        try:
            collection = self._blockchain_db[WORK_CREDITS_COLLECTION]
            count = collection.count_documents({
                'node_id': self.node_id,
                'work_credit_type': WorkCreditType.CONSENSUS_PARTICIPATION.value,
                'work_credit_status': {'$in': [WorkCreditStatus.VERIFIED.value, WorkCreditStatus.CLAIMED.value]}
            })
            return count
        except PyMongoError as e:
            logger.error(f"Failed to count consensus participation operations: {e}")
            return 0
    
    def calculate_work_credits(self) -> Optional[float]:
        """Calculate total work credits based on work performed by the node
        
        Assesses:
        - Contribution to network via session processing
        - Network uptime and availability via beacons
        - Storage availability
        - Validation signatures
        - Consensus participation
        - Chunk replication
        - Network routing
        - Relay bandwidth
        
        Returns:
            float: Total work credits, or None if calculation fails
        """
        try:
            session_processing = self.count_session_processing()
            uptime_beacon = self.count_uptime_beacon()
            storage_availability = self.count_storage_availability()
            validation_signature = self.count_validation_signature()
            consensus_participation = self.count_consensus_participation()
            chunk_replication = self.count_chunk_replication()
            network_routing = self.count_network_routing()
            relay_bandwidth = self.count_relay_bandwidth()
            
            work_credits = (
                session_processing * self.OPERATION_POINTS[WorkCreditType.SESSION_PROCESSING] +
                uptime_beacon * self.OPERATION_POINTS[WorkCreditType.UPTIME_BEACON] +
                storage_availability * self.OPERATION_POINTS[WorkCreditType.STORAGE_AVAILABILITY] +
                validation_signature * self.OPERATION_POINTS[WorkCreditType.VALIDATION_SIGNATURE] +
                consensus_participation * self.OPERATION_POINTS[WorkCreditType.CONSENSUS_PARTICIPATION] +
                chunk_replication * self.OPERATION_POINTS[WorkCreditType.CHUNK_REPLICATION] +
                network_routing * self.OPERATION_POINTS[WorkCreditType.NETWORK_ROUTING] +
                relay_bandwidth * self.OPERATION_POINTS[WorkCreditType.RELAY_BANDWIDTH]
            )
            
            logger.info(f"Calculated {work_credits} work credits for node {self.node_id}")
            return work_credits
        
        except Exception as e:
            logger.error(f"Failed to calculate work credits: {e}")
            return None
    
    def calculate_work_credits_amount(self) -> Optional[float]:
        """Calculate the work credits amount based on work performed by the node
        
        Returns:
            float: Work credits amount, or None if calculation fails
        """
        try:
            return self.calculate_work_credits()
        except Exception as e:
            logger.error(f"Failed to calculate work credits amount: {e}")
            return None
    
    def calculate_work_credits_signature(self, work_credit: WorkCredit) -> Optional[str]:
        """Calculate the work credits signature based on work performed by the node
        
        Args:
            work_credit: WorkCredit instance to sign
            
        Returns:
            str: Work credits signature hash, or None if calculation fails
        """
        try:
            proof_payload = {
                'node_id': work_credit.node_id,
                'work_credit_id': work_credit.work_credit_id,
                'work_credit_type': work_credit.work_credit_type.value,
                'work_credit_amount': work_credit.work_credit_amount,
                'work_credit_timestamp': work_credit.work_credit_timestamp.isoformat(),
                'proof_data': work_credit.work_credit_proof_data,
            }
            
            payload_string = json.dumps(proof_payload, sort_keys=True)
            
            if WORK_CREDITS_SIGNATURE_ALGORITHM == "sha256":
                signature = hashlib.sha256(payload_string.encode()).hexdigest()
            elif WORK_CREDITS_SIGNATURE_ALGORITHM == "sha512":
                signature = hashlib.sha512(payload_string.encode()).hexdigest()
            else:
                signature = hashlib.sha256(payload_string.encode()).hexdigest()
            
            logger.debug(f"Generated signature for work credit {work_credit.work_credit_id}")
            return signature
        
        except Exception as e:
            logger.error(f"Failed to calculate work credits signature: {e}")
            return None
    
    def calculate_work_credits_breakdown(self) -> Optional[Dict[str, float]]:
        """Calculate work credits with breakdown by operation type
        
        Returns:
            dict: Breakdown of credits by operation type, or None if calculation fails
        """
        try:
            breakdown = {
                'session_processing': self.count_session_processing() * self.OPERATION_POINTS[WorkCreditType.SESSION_PROCESSING],
                'uptime_beacon': self.count_uptime_beacon() * self.OPERATION_POINTS[WorkCreditType.UPTIME_BEACON],
                'storage_availability': self.count_storage_availability() * self.OPERATION_POINTS[WorkCreditType.STORAGE_AVAILABILITY],
                'validation_signature': self.count_validation_signature() * self.OPERATION_POINTS[WorkCreditType.VALIDATION_SIGNATURE],
                'consensus_participation': self.count_consensus_participation() * self.OPERATION_POINTS[WorkCreditType.CONSENSUS_PARTICIPATION],
                'chunk_replication': self.count_chunk_replication() * self.OPERATION_POINTS[WorkCreditType.CHUNK_REPLICATION],
                'network_routing': self.count_network_routing() * self.OPERATION_POINTS[WorkCreditType.NETWORK_ROUTING],
                'relay_bandwidth': self.count_relay_bandwidth() * self.OPERATION_POINTS[WorkCreditType.RELAY_BANDWIDTH],
            }
            breakdown['total'] = sum(breakdown.values())
            return breakdown
        
        except Exception as e:
            logger.error(f"Failed to calculate work credits breakdown: {e}")
            return None
    
    def create_work_credit(self, credit_type: WorkCreditType, amount: float, proof_data: Dict[str, Any] = None) -> Optional[WorkCredit]:
        """Create a new work credit record
        
        Args:
            credit_type: Type of work credit
            amount: Amount of work credit
            proof_data: Proof data for the credit
            
        Returns:
            WorkCredit: Created work credit, or None if creation fails
        """
        try:
            work_credit = WorkCredit(
                node_id=self.node_id,
                work_credit_type=credit_type,
                work_credit_amount=amount,
                work_credit_proof_data=proof_data or {},
                work_credit_status=WorkCreditStatus.PENDING,
                work_credit_expiration_date=datetime.now(timezone.utc) + timedelta(days=WORK_CREDITS_EXPIRATION_DAYS)
            )
            
            # Generate signature
            signature = self.calculate_work_credits_signature(work_credit)
            if signature:
                work_credit.work_credit_signature = signature
            
            logger.info(f"Created work credit {work_credit.work_credit_id} for node {self.node_id}")
            return work_credit
        
        except Exception as e:
            logger.error(f"Failed to create work credit: {e}")
            return None
    
    def save_work_credit(self, work_credit: WorkCredit) -> Optional[str]:
        """Save work credit to database
        
        Args:
            work_credit: WorkCredit to save
            
        Returns:
            str: Inserted document ID, or None if save fails
        """
        if not self._blockchain_db:
            logger.error("MongoDB connection not available")
            return None
        
        try:
            collection = self._blockchain_db[WORK_CREDITS_COLLECTION]
            
            document = {
                'work_credit_id': work_credit.work_credit_id,
                'node_id': work_credit.node_id,
                'work_credit_type': work_credit.work_credit_type.value,
                'work_credit_amount': work_credit.work_credit_amount,
                'work_credit_timestamp': work_credit.work_credit_timestamp,
                'work_credit_proof_data': work_credit.work_credit_proof_data,
                'work_credit_signature': work_credit.work_credit_signature,
                'work_credit_status': work_credit.work_credit_status.value,
                'work_credit_verified_at': work_credit.work_credit_verified_at,
                'work_credit_verifier_node_id': work_credit.work_credit_verifier_node_id,
                'work_credit_verified': work_credit.work_credit_verified,
                'work_credit_expiration_date': work_credit.work_credit_expiration_date,
                'work_credit_metadata': work_credit.work_credit_metadata,
            }
            
            result = collection.insert_one(document)
            logger.info(f"Saved work credit {work_credit.work_credit_id} to database")
            return str(result.inserted_id)
        
        except PyMongoError as e:
            logger.error(f"Failed to save work credit to database: {e}")
            return None
    
    def verify_work_credit(self, work_credit_id: str, verifier_node_id: str, verification_data: Dict[str, Any] = None) -> bool:
        """Verify a work credit
        
        Args:
            work_credit_id: ID of work credit to verify
            verifier_node_id: ID of verifying node
            verification_data: Additional verification data
            
        Returns:
            bool: True if verification successful, False otherwise
        """
        try:
            collection = self._blockchain_db[WORK_CREDITS_COLLECTION]
            
            update_data = {
                'work_credit_verified': True,
                'work_credit_verified_at': datetime.now(timezone.utc),
                'work_credit_verifier_node_id': verifier_node_id,
                'work_credit_status': WorkCreditStatus.VERIFIED.value,
            }
            
            result = collection.update_one(
                {'work_credit_id': work_credit_id},
                {'$set': update_data}
            )
            
            if result.modified_count > 0:
                logger.info(f"Verified work credit {work_credit_id}")
                return True
            else:
                logger.warning(f"No work credit found with ID {work_credit_id}")
                return False
        
        except PyMongoError as e:
            logger.error(f"Failed to verify work credit: {e}")
            return False
    
    def get_work_credits_stats(self) -> Optional[WorkCreditStats]:
        """Get work credits statistics for the node
        
        Returns:
            WorkCreditStats: Statistics, or None if retrieval fails
        """
        try:
            collection = self._blockchain_db[WORK_CREDITS_COLLECTION]
            
            total_verified = collection.count_documents({
                'node_id': self.node_id,
                'work_credit_status': WorkCreditStatus.VERIFIED.value
            })
            
            total_pending = collection.count_documents({
                'node_id': self.node_id,
                'work_credit_status': WorkCreditStatus.PENDING.value
            })
            
            total_rejected = collection.count_documents({
                'node_id': self.node_id,
                'work_credit_status': WorkCreditStatus.REJECTED.value
            })
            
            # Calculate total credits by type
            by_type = {}
            for credit_type in WorkCreditType:
                amount = collection.aggregate([
                    {
                        '$match': {
                            'node_id': self.node_id,
                            'work_credit_type': credit_type.value,
                            'work_credit_status': WorkCreditStatus.VERIFIED.value
                        }
                    },
                    {
                        '$group': {
                            '_id': None,
                            'total': {'$sum': '$work_credit_amount'}
                        }
                    }
                ])
                
                amount_list = list(amount)
                by_type[credit_type.value] = amount_list[0]['total'] if amount_list else 0.0
            
            total_credits = sum(by_type.values())
            
            stats = WorkCreditStats(
                node_id=self.node_id,
                total_credits=total_credits,
                total_verified_credits=total_verified,
                total_pending_credits=total_pending,
                total_rejected_credits=total_rejected,
                total_operations=total_verified + total_pending + total_rejected,
                by_type=by_type
            )
            
            logger.info(f"Generated work credits stats for node {self.node_id}")
            return stats
        
        except PyMongoError as e:
            logger.error(f"Failed to get work credits stats: {e}")
            return None
    
    def get_node_leaderboard(self, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
        """Get top nodes by work credits
        
        Args:
            limit: Number of top nodes to return
            
        Returns:
            list: Top nodes with their credits, or None if retrieval fails
        """
        try:
            collection = self._blockchain_db[WORK_CREDITS_COLLECTION]
            
            pipeline = [
                {
                    '$match': {'work_credit_status': WorkCreditStatus.VERIFIED.value}
                },
                {
                    '$group': {
                        '_id': '$node_id',
                        'total_credits': {'$sum': '$work_credit_amount'},
                        'operations_count': {'$sum': 1}
                    }
                },
                {
                    '$sort': {'total_credits': -1}
                },
                {
                    '$limit': limit
                }
            ]
            
            leaderboard = list(collection.aggregate(pipeline))
            logger.info(f"Retrieved leaderboard with {len(leaderboard)} entries")
            return leaderboard
        
        except PyMongoError as e:
            logger.error(f"Failed to get leaderboard: {e}")
            return None
    
    def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed")


# Example usage
if __name__ == '__main__':
    logger.info("Starting Work Credits Calculator")
    
    # Create calculator for current node
    calculator = WorkCreditsCalculator()
    
    # Calculate total work credits
    total_credits = calculator.calculate_work_credits()
    print(f"\nTotal Work Credits: {total_credits}")
    
    # Get breakdown by operation type
    breakdown = calculator.calculate_work_credits_breakdown()
    if breakdown:
        print("\nWork Credits Breakdown:")
        for operation, credits in breakdown.items():
            if operation != 'total':
                print(f"  {operation}: {credits}")
        print(f"  TOTAL: {breakdown['total']}")
    
    # Get statistics
    stats = calculator.get_work_credits_stats()
    if stats:
        print(f"\nWork Credits Stats:")
        print(f"  Total Credits: {stats.total_credits}")
        print(f"  Verified: {stats.total_verified_credits}")
        print(f"  Pending: {stats.total_pending_credits}")
        print(f"  Rejected: {stats.total_rejected_credits}")
    
    # Get leaderboard
    leaderboard = calculator.get_node_leaderboard(limit=5)
    if leaderboard:
        print("\nTop 5 Nodes by Work Credits:")
        for rank, entry in enumerate(leaderboard, 1):
            print(f"  {rank}. {entry['_id']}: {entry['total_credits']} credits ({entry['operations_count']} operations)")
    
    calculator.close()
    logger.info("Work Credits Calculator completed")
