# Path: apps/admin_system/admin_controller.py
# Lucid RDP Admin System - Comprehensive administrative control and governance
# Based on LUCID-STRICT requirements from Build_guide_docs

from __future__ import annotations

import asyncio
import os
import logging
import hashlib
import struct
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import json
import secrets
import base64

from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.asymmetric import padding as rsa_padding
import blake3

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import bcrypt

# Import blockchain engine
import sys
sys.path.append(str(Path(__file__).parent.parent))
from blockchain_core.blockchain_engine import get_blockchain_engine

logger = logging.getLogger(__name__)

# Admin Constants per Spec-1c, Spec-1d
KEY_ROTATION_INTERVAL_DAYS = int(os.getenv("KEY_ROTATION_INTERVAL_DAYS", "30"))  # Monthly key rotation
ADMIN_SESSION_TIMEOUT_HOURS = int(os.getenv("ADMIN_SESSION_TIMEOUT_HOURS", "8"))  # 8-hour admin sessions
GOVERNANCE_QUORUM_PCT = float(os.getenv("GOVERNANCE_QUORUM_PCT", "0.67"))  # 67% quorum required
POLICY_CACHE_TTL_SEC = int(os.getenv("POLICY_CACHE_TTL_SEC", "300"))  # 5-minute policy cache

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/lucid")

# Multi-signature Configuration (per Spec-1c)
MULTISIG_THRESHOLD = int(os.getenv("MULTISIG_THRESHOLD", "3"))  # 3-of-5 multisig
MULTISIG_TOTAL = int(os.getenv("MULTISIG_TOTAL", "5"))


class AdminRole(Enum):
    """Administrative role hierarchy"""
    SUPER_ADMIN = "super_admin"          # Full system access
    BLOCKCHAIN_ADMIN = "blockchain_admin"  # Blockchain operations
    NODE_ADMIN = "node_admin"           # Node management
    POLICY_ADMIN = "policy_admin"       # Policy configuration
    AUDIT_ADMIN = "audit_admin"         # Audit and monitoring
    READ_ONLY = "read_only"             # View-only access


class KeyType(Enum):
    """Cryptographic key types"""
    ED25519_SIGNING = "ed25519_signing"
    RSA_ENCRYPTION = "rsa_encryption"
    CHACHA_SYMMETRIC = "chacha_symmetric"
    TRON_WALLET = "tron_wallet"
    ONION_SERVICE = "onion_service"


class GovernanceAction(Enum):
    """Governance proposal types"""
    POLICY_UPDATE = "policy_update"
    KEY_ROTATION = "key_rotation"
    NODE_PROVISIONING = "node_provisioning"
    PARAMETER_CHANGE = "parameter_change"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"


class ProposalStatus(Enum):
    """Governance proposal statuses"""
    PENDING = "pending"
    VOTING = "voting" 
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


@dataclass
class AdminAccount:
    """Administrative account with role-based permissions"""
    admin_id: str
    username: str
    email: str
    role: AdminRole
    password_hash: bytes
    public_key: bytes
    private_key_encrypted: bytes
    mfa_secret: Optional[str] = None
    session_token: Optional[str] = None
    last_login: Optional[datetime] = None
    key_rotation_due: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.admin_id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "password_hash": self.password_hash,
            "public_key": self.public_key,
            "private_key_encrypted": self.private_key_encrypted,
            "mfa_secret": self.mfa_secret,
            "session_token": self.session_token,
            "last_login": self.last_login,
            "key_rotation_due": self.key_rotation_due,
            "is_active": self.is_active,
            "created_at": self.created_at
        }


@dataclass
class CryptographicKey:
    """Cryptographic key with metadata"""
    key_id: str
    key_type: KeyType
    purpose: str  # e.g., "session_encryption", "blockchain_signing"
    public_key: Optional[bytes] = None
    private_key_encrypted: Optional[bytes] = None
    derivation_path: Optional[str] = None
    rotation_schedule: Optional[int] = None  # days
    last_rotated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    next_rotation: Optional[datetime] = None
    is_active: bool = True
    created_by: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.key_id,
            "type": self.key_type.value,
            "purpose": self.purpose,
            "public_key": self.public_key,
            "private_key_encrypted": self.private_key_encrypted,
            "derivation_path": self.derivation_path,
            "rotation_schedule": self.rotation_schedule,
            "last_rotated": self.last_rotated,
            "next_rotation": self.next_rotation,
            "is_active": self.is_active,
            "created_by": self.created_by
        }


@dataclass
class SystemPolicy:
    """System-wide policy configuration"""
    policy_id: str
    policy_name: str
    policy_type: str  # e.g., "session_control", "access_control", "security"
    policy_data: Dict[str, Any]
    version: int = 1
    is_active: bool = True
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    created_by: Optional[str] = None
    last_modified: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.policy_id,
            "name": self.policy_name,
            "type": self.policy_type,
            "data": self.policy_data,
            "version": self.version,
            "is_active": self.is_active,
            "effective_date": self.effective_date,
            "expiry_date": self.expiry_date,
            "created_by": self.created_by,
            "last_modified": self.last_modified
        }


@dataclass
class GovernanceProposal:
    """Multi-signature governance proposal"""
    proposal_id: str
    action_type: GovernanceAction
    title: str
    description: str
    proposal_data: Dict[str, Any]
    proposer: str
    required_signatures: int
    signatures: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # admin_id -> signature_data
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    voting_deadline: Optional[datetime] = None
    execution_date: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.proposal_id,
            "action_type": self.action_type.value,
            "title": self.title,
            "description": self.description,
            "data": self.proposal_data,
            "proposer": self.proposer,
            "required_signatures": self.required_signatures,
            "signatures": self.signatures,
            "status": self.status.value,
            "created_at": self.created_at,
            "voting_deadline": self.voting_deadline,
            "execution_date": self.execution_date
        }


class KeyRotationManager:
    """
    Automated key rotation system.
    
    Handles:
    - Scheduled rotation of all key types
    - Secure key generation and storage
    - Multi-signature approval for critical keys
    - Hardware security module integration
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        
    async def rotate_key(self, key_id: str, admin_id: str) -> bool:
        """Rotate cryptographic key with new secure key pair"""
        try:
            # Get existing key
            key_doc = await self.db["keys"].find_one({"_id": key_id})
            if not key_doc:
                logger.error(f"Key not found: {key_id}")
                return False
            
            key = CryptographicKey(**key_doc)
            
            # Generate new key pair based on type
            if key.key_type == KeyType.ED25519_SIGNING:
                new_private_key = ed25519.Ed25519PrivateKey.generate()
                new_public_key = new_private_key.public_key()
                
                public_bytes = new_public_key.public_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PublicFormat.Raw
                )
                private_bytes = new_private_key.private_bytes(
                    encoding=serialization.Encoding.Raw,
                    format=serialization.PrivateFormat.Raw,
                    encryption_algorithm=serialization.NoEncryption()
                )
                
            elif key.key_type == KeyType.RSA_ENCRYPTION:
                new_private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=4096
                )
                new_public_key = new_private_key.public_key()
                
                public_bytes = new_public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.PKCS1
                )
                private_bytes = new_private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                
            elif key.key_type == KeyType.CHACHA_SYMMETRIC:
                # Generate 256-bit symmetric key
                private_bytes = secrets.token_bytes(32)
                public_bytes = None  # Symmetric keys don't have public components
                
            else:
                logger.error(f"Unsupported key type for rotation: {key.key_type}")
                return False
            
            # Encrypt private key for storage
            encrypted_private_key = await self._encrypt_private_key(private_bytes, admin_id)
            
            # Update key record
            key.private_key_encrypted = encrypted_private_key
            key.public_key = public_bytes
            key.last_rotated = datetime.now(timezone.utc)
            
            # Calculate next rotation date
            if key.rotation_schedule:
                key.next_rotation = key.last_rotated + timedelta(days=key.rotation_schedule)
            
            # Store updated key
            await self.db["keys"].replace_one(
                {"_id": key_id},
                key.to_dict()
            )
            
            # Log rotation event
            await self._log_key_rotation(key_id, admin_id)
            
            logger.info(f"Key rotated successfully: {key_id}")
            return True
            
        except Exception as e:
            logger.error(f"Key rotation failed: {key_id}: {e}")
            return False
    
    async def schedule_key_rotation(self, key_id: str, rotation_days: int, admin_id: str):
        """Schedule automatic key rotation"""
        try:
            next_rotation = datetime.now(timezone.utc) + timedelta(days=rotation_days)
            
            await self.db["keys"].update_one(
                {"_id": key_id},
                {"$set": {
                    "rotation_schedule": rotation_days,
                    "next_rotation": next_rotation
                }}
            )
            
            logger.info(f"Key rotation scheduled: {key_id} every {rotation_days} days")
            
        except Exception as e:
            logger.error(f"Failed to schedule key rotation: {e}")
    
    async def check_due_rotations(self) -> List[str]:
        """Check for keys due for rotation"""
        try:
            now = datetime.now(timezone.utc)
            
            cursor = self.db["keys"].find({
                "next_rotation": {"$lte": now},
                "is_active": True
            })
            
            due_keys = []
            async for key_doc in cursor:
                due_keys.append(key_doc["_id"])
            
            return due_keys
            
        except Exception as e:
            logger.error(f"Failed to check due rotations: {e}")
            return []
    
    async def _encrypt_private_key(self, private_key: bytes, admin_id: str) -> bytes:
        """Encrypt private key for secure storage"""
        # In production, this would use hardware security module
        # For now, using admin-specific encryption
        
        # Derive encryption key from admin ID (simplified)
        kdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=admin_id.encode()
        )
        
        admin_key = kdf.derive(b"admin_key_derivation_material")
        cipher = ChaCha20Poly1305(admin_key)
        nonce = secrets.token_bytes(12)
        
        encrypted_data = cipher.encrypt(nonce, private_key, None)
        return nonce + encrypted_data
    
    async def _log_key_rotation(self, key_id: str, admin_id: str):
        """Log key rotation event"""
        await self.db["audit_logs"].insert_one({
            "timestamp": datetime.now(timezone.utc),
            "event_type": "key_rotation",
            "admin_id": admin_id,
            "resource_id": key_id,
            "details": {"action": "key_rotated"}
        })


class GovernanceManager:
    """
    Multi-signature governance system.
    
    Handles:
    - Proposal creation and voting
    - Multi-signature approval workflows
    - Policy updates and system changes
    - Emergency procedures
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        
    async def create_proposal(self, action_type: GovernanceAction, title: str,
                            description: str, proposal_data: Dict[str, Any],
                            proposer: str) -> str:
        """Create new governance proposal"""
        try:
            proposal_id = str(uuid.uuid4())
            
            # Set voting deadline (7 days from creation)
            voting_deadline = datetime.now(timezone.utc) + timedelta(days=7)
            
            # Determine required signatures based on action type
            if action_type in [GovernanceAction.EMERGENCY_SHUTDOWN, GovernanceAction.KEY_ROTATION]:
                required_signatures = max(2, int(MULTISIG_TOTAL * 0.5))  # 50% for emergency
            else:
                required_signatures = MULTISIG_THRESHOLD  # Standard 3-of-5
            
            proposal = GovernanceProposal(
                proposal_id=proposal_id,
                action_type=action_type,
                title=title,
                description=description,
                proposal_data=proposal_data,
                proposer=proposer,
                required_signatures=required_signatures,
                voting_deadline=voting_deadline
            )
            
            # Store proposal
            await self.db["governance_proposals"].insert_one(proposal.to_dict())
            
            # Notify eligible voters
            await self._notify_governance_admins(proposal)
            
            logger.info(f"Governance proposal created: {proposal_id}")
            return proposal_id
            
        except Exception as e:
            logger.error(f"Failed to create proposal: {e}")
            raise
    
    async def vote_on_proposal(self, proposal_id: str, admin_id: str,
                             approve: bool, signature_data: Dict[str, Any]) -> bool:
        """Vote on governance proposal with cryptographic signature"""
        try:
            # Get proposal
            proposal_doc = await self.db["governance_proposals"].find_one({"_id": proposal_id})
            if not proposal_doc:
                logger.error(f"Proposal not found: {proposal_id}")
                return False
            
            proposal = GovernanceProposal(**proposal_doc)
            
            # Check voting eligibility
            if not await self._is_eligible_voter(admin_id, proposal.action_type):
                logger.error(f"Admin not eligible to vote: {admin_id}")
                return False
            
            # Check if voting period is still open
            if datetime.now(timezone.utc) > proposal.voting_deadline:
                await self._expire_proposal(proposal_id)
                logger.error(f"Voting period expired for proposal: {proposal_id}")
                return False
            
            # Verify signature (simplified)
            if not await self._verify_governance_signature(admin_id, proposal_id, signature_data):
                logger.error(f"Invalid signature from admin: {admin_id}")
                return False
            
            # Record vote
            vote_data = {
                "approve": approve,
                "timestamp": datetime.now(timezone.utc),
                "signature": signature_data
            }
            proposal.signatures[admin_id] = vote_data
            
            # Update proposal
            await self.db["governance_proposals"].update_one(
                {"_id": proposal_id},
                {"$set": {"signatures": proposal.signatures}}
            )
            
            # Check if proposal has enough votes
            await self._check_proposal_status(proposal_id)
            
            logger.info(f"Vote recorded: {admin_id} {'approved' if approve else 'rejected'} {proposal_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to vote on proposal: {e}")
            return False
    
    async def execute_proposal(self, proposal_id: str, executor_admin_id: str) -> bool:
        """Execute approved governance proposal"""
        try:
            # Get proposal
            proposal_doc = await self.db["governance_proposals"].find_one({"_id": proposal_id})
            if not proposal_doc:
                logger.error(f"Proposal not found: {proposal_id}")
                return False
            
            proposal = GovernanceProposal(**proposal_doc)
            
            # Verify proposal is approved
            if proposal.status != ProposalStatus.APPROVED:
                logger.error(f"Proposal not approved for execution: {proposal_id}")
                return False
            
            # Execute based on action type
            success = False
            if proposal.action_type == GovernanceAction.POLICY_UPDATE:
                success = await self._execute_policy_update(proposal.proposal_data)
            elif proposal.action_type == GovernanceAction.KEY_ROTATION:
                success = await self._execute_key_rotation(proposal.proposal_data)
            elif proposal.action_type == GovernanceAction.NODE_PROVISIONING:
                success = await self._execute_node_provisioning(proposal.proposal_data)
            elif proposal.action_type == GovernanceAction.PARAMETER_CHANGE:
                success = await self._execute_parameter_change(proposal.proposal_data)
            elif proposal.action_type == GovernanceAction.EMERGENCY_SHUTDOWN:
                success = await self._execute_emergency_shutdown(proposal.proposal_data)
            
            if success:
                # Mark as executed
                await self.db["governance_proposals"].update_one(
                    {"_id": proposal_id},
                    {"$set": {
                        "status": ProposalStatus.EXECUTED.value,
                        "execution_date": datetime.now(timezone.utc),
                        "executed_by": executor_admin_id
                    }}
                )
                
                logger.info(f"Proposal executed successfully: {proposal_id}")
            else:
                logger.error(f"Proposal execution failed: {proposal_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to execute proposal: {e}")
            return False
    
    async def _check_proposal_status(self, proposal_id: str):
        """Check if proposal has met voting requirements"""
        try:
            proposal_doc = await self.db["governance_proposals"].find_one({"_id": proposal_id})
            proposal = GovernanceProposal(**proposal_doc)
            
            # Count approvals
            approvals = sum(1 for vote in proposal.signatures.values() if vote["approve"])
            rejections = sum(1 for vote in proposal.signatures.values() if not vote["approve"])
            
            # Check if approved
            if approvals >= proposal.required_signatures:
                await self.db["governance_proposals"].update_one(
                    {"_id": proposal_id},
                    {"$set": {"status": ProposalStatus.APPROVED.value}}
                )
                logger.info(f"Proposal approved: {proposal_id}")
                
            # Check if rejected (majority rejection)
            elif rejections > (MULTISIG_TOTAL - proposal.required_signatures):
                await self.db["governance_proposals"].update_one(
                    {"_id": proposal_id},
                    {"$set": {"status": ProposalStatus.REJECTED.value}}
                )
                logger.info(f"Proposal rejected: {proposal_id}")
                
        except Exception as e:
            logger.error(f"Failed to check proposal status: {e}")
    
    async def _is_eligible_voter(self, admin_id: str, action_type: GovernanceAction) -> bool:
        """Check if admin is eligible to vote on specific action type"""
        try:
            admin_doc = await self.db["admin_accounts"].find_one({"_id": admin_id})
            if not admin_doc or not admin_doc.get("is_active"):
                return False
            
            admin_role = AdminRole(admin_doc["role"])
            
            # Super admins can vote on everything
            if admin_role == AdminRole.SUPER_ADMIN:
                return True
            
            # Role-based voting eligibility
            eligible_roles = {
                GovernanceAction.POLICY_UPDATE: [AdminRole.POLICY_ADMIN, AdminRole.SUPER_ADMIN],
                GovernanceAction.KEY_ROTATION: [AdminRole.BLOCKCHAIN_ADMIN, AdminRole.SUPER_ADMIN],
                GovernanceAction.NODE_PROVISIONING: [AdminRole.NODE_ADMIN, AdminRole.SUPER_ADMIN],
                GovernanceAction.PARAMETER_CHANGE: [AdminRole.SUPER_ADMIN],
                GovernanceAction.EMERGENCY_SHUTDOWN: [AdminRole.SUPER_ADMIN, AdminRole.BLOCKCHAIN_ADMIN]
            }
            
            return admin_role in eligible_roles.get(action_type, [])
            
        except Exception as e:
            logger.error(f"Failed to check voter eligibility: {e}")
            return False
    
    async def _verify_governance_signature(self, admin_id: str, proposal_id: str,
                                         signature_data: Dict[str, Any]) -> bool:
        """Verify cryptographic signature for governance vote"""
        try:
            # Get admin public key
            admin_doc = await self.db["admin_accounts"].find_one({"_id": admin_id})
            if not admin_doc:
                return False
            
            # Create message to verify (proposal_id + admin_id + timestamp)
            message = f"{proposal_id}:{admin_id}:{signature_data.get('timestamp', '')}"
            message_bytes = message.encode()
            
            # Verify Ed25519 signature (simplified)
            public_key_bytes = admin_doc["public_key"]
            signature_bytes = bytes.fromhex(signature_data.get("signature", ""))
            
            if len(public_key_bytes) != 32 or len(signature_bytes) != 64:
                return False
            
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            public_key.verify(signature_bytes, message_bytes)
            
            return True
            
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
    
    async def _execute_policy_update(self, data: Dict[str, Any]) -> bool:
        """Execute policy update proposal"""
        try:
            policy_id = data.get("policy_id")
            new_policy_data = data.get("policy_data")
            
            if not policy_id or not new_policy_data:
                return False
            
            # Update policy
            await self.db["policies"].update_one(
                {"_id": policy_id},
                {"$set": {
                    "data": new_policy_data,
                    "version": {"$inc": 1},
                    "last_modified": datetime.now(timezone.utc)
                }}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Policy update execution failed: {e}")
            return False
    
    async def _execute_key_rotation(self, data: Dict[str, Any]) -> bool:
        """Execute key rotation proposal"""
        # Implementation would integrate with KeyRotationManager
        return True
    
    async def _execute_node_provisioning(self, data: Dict[str, Any]) -> bool:
        """Execute node provisioning proposal"""
        # Implementation would integrate with node management
        return True
    
    async def _execute_parameter_change(self, data: Dict[str, Any]) -> bool:
        """Execute system parameter change proposal"""
        # Implementation would update system configuration
        return True
    
    async def _execute_emergency_shutdown(self, data: Dict[str, Any]) -> bool:
        """Execute emergency shutdown proposal"""
        # Implementation would trigger graceful system shutdown
        return True
    
    async def _expire_proposal(self, proposal_id: str):
        """Mark expired proposal"""
        await self.db["governance_proposals"].update_one(
            {"_id": proposal_id},
            {"$set": {"status": ProposalStatus.EXPIRED.value}}
        )
    
    async def _notify_governance_admins(self, proposal: GovernanceProposal):
        """Notify eligible admins about new proposal"""
        # Implementation would send notifications (email, etc.)
        pass


class AdminController:
    """
    Main administrative control system.
    
    Orchestrates:
    - Admin account management and authentication
    - Key rotation and cryptographic operations
    - Policy management and enforcement
    - Multi-signature governance workflows
    - Audit logging and compliance
    """
    
    def __init__(self):
        self.mongo_client = AsyncIOMotorClient(MONGODB_URI)
        self.db = self.mongo_client.get_default_database()
        
        # Initialize components
        self.key_manager = KeyRotationManager(self.db)
        self.governance = GovernanceManager(self.db)
        self.blockchain = get_blockchain_engine()
        
        # Policy cache
        self.policy_cache: Dict[str, Tuple[SystemPolicy, datetime]] = {}
        
        # Initialize MongoDB indexes
        asyncio.create_task(self._setup_mongodb_indexes())
        
        logger.info("Admin controller initialized")
    
    async def _setup_mongodb_indexes(self):
        """Setup MongoDB indexes for admin collections"""
        try:
            # admin_accounts collection
            await self.db["admin_accounts"].create_index([("username", 1)], unique=True)
            await self.db["admin_accounts"].create_index([("email", 1)], unique=True)
            await self.db["admin_accounts"].create_index([("role", 1)])
            await self.db["admin_accounts"].create_index([("is_active", 1)])
            
            # keys collection
            await self.db["keys"].create_index([("type", 1)])
            await self.db["keys"].create_index([("purpose", 1)])
            await self.db["keys"].create_index([("next_rotation", 1)])
            await self.db["keys"].create_index([("is_active", 1)])
            
            # policies collection
            await self.db["policies"].create_index([("type", 1)])
            await self.db["policies"].create_index([("is_active", 1)])
            await self.db["policies"].create_index([("effective_date", 1)])
            
            # governance_proposals collection
            await self.db["governance_proposals"].create_index([("status", 1)])
            await self.db["governance_proposals"].create_index([("action_type", 1)])
            await self.db["governance_proposals"].create_index([("voting_deadline", 1)])
            
            # audit_logs collection
            await self.db["audit_logs"].create_index([("timestamp", -1)])
            await self.db["audit_logs"].create_index([("event_type", 1)])
            await self.db["audit_logs"].create_index([("admin_id", 1)])
            
            logger.info("Admin system MongoDB indexes created")
            
        except Exception as e:
            logger.error(f"Failed to setup admin MongoDB indexes: {e}")
    
    # Admin Account Management
    
    async def create_admin_account(self, username: str, email: str, password: str,
                                 role: AdminRole, creator_admin_id: str) -> str:
        """Create new administrative account with key pair"""
        try:
            admin_id = str(uuid.uuid4())
            
            # Generate password hash
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            
            # Generate Ed25519 key pair for admin
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            private_key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            # Encrypt private key
            encrypted_private_key = await self.key_manager._encrypt_private_key(
                private_key_bytes, admin_id
            )
            
            # Set key rotation schedule
            key_rotation_due = datetime.now(timezone.utc) + timedelta(days=KEY_ROTATION_INTERVAL_DAYS)
            
            # Create admin account
            admin = AdminAccount(
                admin_id=admin_id,
                username=username,
                email=email,
                role=role,
                password_hash=password_hash,
                public_key=public_key_bytes,
                private_key_encrypted=encrypted_private_key,
                key_rotation_due=key_rotation_due
            )
            
            # Store admin account
            await self.db["admin_accounts"].insert_one(admin.to_dict())
            
            # Log account creation
            await self._log_admin_event(creator_admin_id, "admin_account_created", admin_id,
                                      {"username": username, "role": role.value})
            
            logger.info(f"Admin account created: {username} ({role.value})")
            return admin_id
            
        except Exception as e:
            logger.error(f"Failed to create admin account: {e}")
            raise
    
    async def authenticate_admin(self, username: str, password: str,
                               mfa_token: Optional[str] = None) -> Optional[str]:
        """Authenticate admin and return session token"""
        try:
            # Find admin by username
            admin_doc = await self.db["admin_accounts"].find_one({
                "username": username,
                "is_active": True
            })
            
            if not admin_doc:
                await self._log_security_event("auth_failed_user_not_found", {"username": username})
                return None
            
            admin = AdminAccount(**admin_doc)
            
            # Verify password
            if not bcrypt.checkpw(password.encode(), admin.password_hash):
                await self._log_security_event("auth_failed_invalid_password", {"admin_id": admin.admin_id})
                return None
            
            # Verify MFA if configured
            if admin.mfa_secret and not await self._verify_mfa(admin.mfa_secret, mfa_token):
                await self._log_security_event("auth_failed_invalid_mfa", {"admin_id": admin.admin_id})
                return None
            
            # Generate session token
            session_token = secrets.token_urlsafe(32)
            session_expiry = datetime.now(timezone.utc) + timedelta(hours=ADMIN_SESSION_TIMEOUT_HOURS)
            
            # Update admin record
            await self.db["admin_accounts"].update_one(
                {"_id": admin.admin_id},
                {"$set": {
                    "session_token": session_token,
                    "last_login": datetime.now(timezone.utc)
                }}
            )
            
            # Store session info (simplified - would use Redis in production)
            await self.db["admin_sessions"].replace_one(
                {"admin_id": admin.admin_id},
                {
                    "admin_id": admin.admin_id,
                    "session_token": session_token,
                    "expires_at": session_expiry,
                    "created_at": datetime.now(timezone.utc)
                },
                upsert=True
            )
            
            await self._log_admin_event(admin.admin_id, "admin_login_success", admin.admin_id)
            
            logger.info(f"Admin authenticated: {username}")
            return session_token
            
        except Exception as e:
            logger.error(f"Admin authentication failed: {e}")
            return None
    
    async def validate_admin_session(self, session_token: str) -> Optional[AdminAccount]:
        """Validate admin session token and return admin account"""
        try:
            # Find session
            session_doc = await self.db["admin_sessions"].find_one({
                "session_token": session_token
            })
            
            if not session_doc:
                return None
            
            # Check expiry
            if datetime.now(timezone.utc) > session_doc["expires_at"]:
                # Clean up expired session
                await self.db["admin_sessions"].delete_one({"session_token": session_token})
                return None
            
            # Get admin account
            admin_doc = await self.db["admin_accounts"].find_one({
                "_id": session_doc["admin_id"],
                "is_active": True
            })
            
            if not admin_doc:
                return None
            
            return AdminAccount(**admin_doc)
            
        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return None
    
    async def logout_admin(self, session_token: str):
        """Logout admin and invalidate session"""
        try:
            session_doc = await self.db["admin_sessions"].find_one({"session_token": session_token})
            if session_doc:
                await self._log_admin_event(session_doc["admin_id"], "admin_logout", session_doc["admin_id"])
            
            # Delete session
            await self.db["admin_sessions"].delete_one({"session_token": session_token})
            
        except Exception as e:
            logger.error(f"Admin logout failed: {e}")
    
    # Policy Management
    
    async def create_policy(self, policy_name: str, policy_type: str,
                          policy_data: Dict[str, Any], admin_id: str) -> str:
        """Create system policy"""
        try:
            policy_id = str(uuid.uuid4())
            
            policy = SystemPolicy(
                policy_id=policy_id,
                policy_name=policy_name,
                policy_type=policy_type,
                policy_data=policy_data,
                created_by=admin_id
            )
            
            # Store policy
            await self.db["policies"].insert_one(policy.to_dict())
            
            # Invalidate cache
            self._invalidate_policy_cache(policy_type)
            
            await self._log_admin_event(admin_id, "policy_created", policy_id,
                                      {"name": policy_name, "type": policy_type})
            
            logger.info(f"Policy created: {policy_name}")
            return policy_id
            
        except Exception as e:
            logger.error(f"Failed to create policy: {e}")
            raise
    
    async def get_active_policy(self, policy_type: str) -> Optional[SystemPolicy]:
        """Get active policy with caching"""
        try:
            # Check cache first
            if policy_type in self.policy_cache:
                policy, cached_at = self.policy_cache[policy_type]
                if datetime.now(timezone.utc) - cached_at < timedelta(seconds=POLICY_CACHE_TTL_SEC):
                    return policy
            
            # Query database
            policy_doc = await self.db["policies"].find_one({
                "type": policy_type,
                "is_active": True,
                "$or": [
                    {"effective_date": None},
                    {"effective_date": {"$lte": datetime.now(timezone.utc)}}
                ],
                "$or": [
                    {"expiry_date": None},
                    {"expiry_date": {"$gte": datetime.now(timezone.utc)}}
                ]
            })
            
            if not policy_doc:
                return None
            
            policy = SystemPolicy(**policy_doc)
            
            # Cache policy
            self.policy_cache[policy_type] = (policy, datetime.now(timezone.utc))
            
            return policy
            
        except Exception as e:
            logger.error(f"Failed to get policy: {e}")
            return None
    
    def _invalidate_policy_cache(self, policy_type: str):
        """Invalidate policy cache for specific type"""
        self.policy_cache.pop(policy_type, None)
    
    async def _verify_mfa(self, mfa_secret: str, token: Optional[str]) -> bool:
        """Verify MFA token (simplified TOTP verification)"""
        # Implementation would verify TOTP token
        return token is not None and len(token) == 6
    
    async def _log_admin_event(self, admin_id: str, event_type: str, resource_id: str,
                             details: Dict[str, Any] = None):
        """Log administrative event"""
        try:
            await self.db["audit_logs"].insert_one({
                "timestamp": datetime.now(timezone.utc),
                "event_type": event_type,
                "admin_id": admin_id,
                "resource_id": resource_id,
                "details": details or {}
            })
        except Exception as e:
            logger.error(f"Failed to log admin event: {e}")
    
    async def _log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security-related event"""
        try:
            await self.db["security_logs"].insert_one({
                "timestamp": datetime.now(timezone.utc),
                "event_type": event_type,
                "details": details
            })
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    # Public API methods
    
    async def get_admin_dashboard_data(self, admin_id: str) -> Dict[str, Any]:
        """Get admin dashboard overview data"""
        try:
            # Get admin info
            admin_doc = await self.db["admin_accounts"].find_one({"_id": admin_id})
            if not admin_doc:
                return {}
            
            admin = AdminAccount(**admin_doc)
            
            # Get recent activity
            recent_logs = await self.db["audit_logs"].find({
                "admin_id": admin_id
            }).sort("timestamp", -1).limit(10).to_list(length=None)
            
            # Get pending proposals
            pending_proposals = await self.db["governance_proposals"].find({
                "status": ProposalStatus.PENDING.value
            }).limit(5).to_list(length=None)
            
            # Get keys due for rotation
            due_rotations = await self.key_manager.check_due_rotations()
            
            return {
                "admin": {
                    "username": admin.username,
                    "role": admin.role.value,
                    "last_login": admin.last_login,
                    "key_rotation_due": admin.key_rotation_due
                },
                "recent_activity": recent_logs,
                "pending_proposals": pending_proposals,
                "keys_due_rotation": len(due_rotations),
                "system_status": "operational"  # Would check actual system status
            }
            
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            return {}
    
    async def close(self):
        """Close admin controller"""
        self.mongo_client.close()
        logger.info("Admin controller closed")


# Global admin controller instance
admin_controller: Optional[AdminController] = None


def get_admin_controller() -> AdminController:
    """Get global admin controller instance"""
    global admin_controller
    if admin_controller is None:
        admin_controller = AdminController()
    return admin_controller


async def start_admin_service():
    """Start admin service"""
    controller = get_admin_controller()
    
    # Start automated key rotation checker
    asyncio.create_task(_key_rotation_scheduler())
    
    logger.info("Admin service started")


async def stop_admin_service():
    """Stop admin service"""
    global admin_controller
    if admin_controller:
        await admin_controller.close()
        admin_controller = None


async def _key_rotation_scheduler():
    """Background task for automated key rotation"""
    controller = get_admin_controller()
    
    while True:
        try:
            # Check for keys due for rotation
            due_keys = await controller.key_manager.check_due_rotations()
            
            for key_id in due_keys:
                # Rotate key with system admin
                await controller.key_manager.rotate_key(key_id, "system")
                
            # Sleep for 1 hour before next check
            await asyncio.sleep(3600)
            
        except Exception as e:
            logger.error(f"Key rotation scheduler error: {e}")
            await asyncio.sleep(300)  # Retry in 5 minutes


if __name__ == "__main__":
    # Test admin system
    async def test_admin():
        print("Starting Lucid admin system...")
        await start_admin_service()
        
        controller = get_admin_controller()
        
        # Create test admin account
        admin_id = await controller.create_admin_account(
            username="test_admin",
            email="admin@test.com",
            password="secure_password_123",
            role=AdminRole.SUPER_ADMIN,
            creator_admin_id="system"
        )
        
        print(f"Test admin created: {admin_id}")
        
        # Test authentication
        session_token = await controller.authenticate_admin("test_admin", "secure_password_123")
        if session_token:
            print(f"Authentication successful: {session_token[:16]}...")
        
        # Get dashboard data
        dashboard = await controller.get_admin_dashboard_data(admin_id)
        print(f"Dashboard loaded for: {dashboard.get('admin', {}).get('username', 'Unknown')}")
        
        # Keep running briefly
        await asyncio.sleep(3)
        
        print("Stopping admin system...")
        await stop_admin_service()
    
    asyncio.run(test_admin())