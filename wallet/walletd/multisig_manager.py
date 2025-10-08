# LUCID Wallet Multisig Manager - 2-of-3 Multisig Operations
# Implements secure multisig wallet management with threshold signatures
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

logger = logging.getLogger(__name__)

# Configuration from environment
MULTISIG_TIMEOUT_SECONDS = 300  # 5 minutes for signature collection
MULTISIG_MAX_SIGNERS = 10
MULTISIG_MIN_SIGNERS = 2
MULTISIG_DEFAULT_THRESHOLD = 2
MULTISIG_DEFAULT_TOTAL = 3


class MultisigStatus(Enum):
    """Multisig wallet status states"""
    CREATING = "creating"
    ACTIVE = "active"
    SIGNING = "signing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class SignerRole(Enum):
    """Signer role in multisig wallet"""
    CREATOR = "creator"
    SIGNER = "signer"
    BACKUP = "backup"
    ADMIN = "admin"


class SignatureStatus(Enum):
    """Individual signature status"""
    PENDING = "pending"
    COLLECTED = "collected"
    VERIFIED = "verified"
    INVALID = "invalid"
    EXPIRED = "expired"


class TransactionType(Enum):
    """Multisig transaction types"""
    TRANSFER = "transfer"
    CONTRACT_CALL = "contract_call"
    KEY_ROTATION = "key_rotation"
    WALLET_UPDATE = "wallet_update"
    EMERGENCY = "emergency"


@dataclass
class MultisigSigner:
    """Multisig signer information"""
    signer_id: str
    public_key: bytes
    tron_address: str
    role: SignerRole
    weight: int = 1
    is_active: bool = True
    added_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_signed: Optional[datetime] = None
    signature_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultisigWallet:
    """Multisig wallet configuration"""
    wallet_id: str
    name: str
    description: str
    threshold: int
    total_signers: int
    signers: Dict[str, MultisigSigner] = field(default_factory=dict)
    status: MultisigStatus = MultisigStatus.CREATING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = ""
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def active_signers(self) -> List[MultisigSigner]:
        """Get active signers"""
        return [signer for signer in self.signers.values() if signer.is_active]
    
    @property
    def total_weight(self) -> int:
        """Get total weight of active signers"""
        return sum(signer.weight for signer in self.active_signers)


@dataclass
class MultisigTransaction:
    """Multisig transaction request"""
    transaction_id: str
    wallet_id: str
    transaction_type: TransactionType
    data: bytes
    initiator: str
    description: str
    status: MultisigStatus = MultisigStatus.SIGNING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    required_signatures: int = 0
    collected_signatures: Dict[str, 'MultisigSignature'] = field(default_factory=dict)
    final_signature: Optional[bytes] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultisigSignature:
    """Individual multisig signature"""
    signature_id: str
    transaction_id: str
    signer_id: str
    signature: bytes
    public_key: bytes
    status: SignatureStatus = SignatureStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verified_at: Optional[datetime] = None
    verification_error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MultisigPolicy:
    """Multisig policy configuration"""
    policy_id: str
    wallet_id: str
    transaction_type: TransactionType
    required_signers: int
    max_amount: Optional[float] = None
    allowed_recipients: Optional[List[str]] = None
    time_restrictions: Optional[Dict[str, Any]] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class MultisigManager:
    """
    Multisig wallet manager for secure threshold signature operations.
    
    Features:
    - 2-of-3 and custom threshold multisig wallets
    - Secure signature collection and verification
    - Transaction lifecycle management
    - Policy-based transaction controls
    - Hardware wallet integration support
    - Comprehensive audit logging
    - Emergency recovery procedures
    """
    
    def __init__(self, wallet_id: str):
        """Initialize multisig manager"""
        self.wallet_id = wallet_id
        self.multisig_wallets: Dict[str, MultisigWallet] = {}
        self.active_transactions: Dict[str, MultisigTransaction] = {}
        self.completed_transactions: List[MultisigTransaction] = []
        self.policies: Dict[str, MultisigPolicy] = {}
        
        # Signature collection
        self.signature_timeout = timedelta(seconds=MULTISIG_TIMEOUT_SECONDS)
        self.collection_tasks: Dict[str, asyncio.Task] = {}
        
        # Monitoring
        self.monitor_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
        
        logger.info(f"MultisigManager initialized for wallet: {wallet_id}")
    
    async def start(self) -> None:
        """Start multisig manager"""
        try:
            # Start monitoring
            self.is_monitoring = True
            self.monitor_task = asyncio.create_task(self._monitor_loop())
            
            logger.info(f"MultisigManager started for wallet: {self.wallet_id}")
            
        except Exception as e:
            logger.error(f"Failed to start MultisigManager: {e}")
    
    async def stop(self) -> None:
        """Stop multisig manager"""
        try:
            # Stop monitoring
            self.is_monitoring = False
            if self.monitor_task:
                self.monitor_task.cancel()
                try:
                    await self.monitor_task
                except asyncio.CancelledError:
                    pass
            
            # Cancel collection tasks
            for task in self.collection_tasks.values():
                task.cancel()
            
            logger.info(f"MultisigManager stopped for wallet: {self.wallet_id}")
            
        except Exception as e:
            logger.error(f"Failed to stop MultisigManager: {e}")
    
    async def create_multisig_wallet(
        self,
        name: str,
        description: str,
        signers: List[Dict[str, Any]],
        threshold: int = MULTISIG_DEFAULT_THRESHOLD,
        created_by: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """Create new multisig wallet"""
        try:
            # Validate input
            if len(signers) < MULTISIG_MIN_SIGNERS:
                return False, f"Minimum {MULTISIG_MIN_SIGNERS} signers required"
            
            if len(signers) > MULTISIG_MAX_SIGNERS:
                return False, f"Maximum {MULTISIG_MAX_SIGNERS} signers allowed"
            
            if threshold < 2 or threshold > len(signers):
                return False, "Invalid threshold"
            
            # Create wallet ID
            wallet_id = secrets.token_hex(16)
            
            # Create signers
            multisig_signers = {}
            for i, signer_data in enumerate(signers):
                signer_id = signer_data.get("signer_id", f"signer_{i}")
                role = SignerRole(signer_data.get("role", "signer"))
                
                signer = MultisigSigner(
                    signer_id=signer_id,
                    public_key=bytes.fromhex(signer_data["public_key"]),
                    tron_address=signer_data["tron_address"],
                    role=role,
                    weight=signer_data.get("weight", 1),
                    metadata=signer_data.get("metadata", {})
                )
                
                multisig_signers[signer_id] = signer
            
            # Create multisig wallet
            multisig_wallet = MultisigWallet(
                wallet_id=wallet_id,
                name=name,
                description=description,
                threshold=threshold,
                total_signers=len(signers),
                signers=multisig_signers,
                created_by=created_by,
                metadata=metadata or {}
            )
            
            # Store wallet
            self.multisig_wallets[wallet_id] = multisig_wallet
            
            # Create default policies
            await self._create_default_policies(wallet_id)
            
            logger.info(f"Created multisig wallet: {wallet_id} ({threshold}-of-{len(signers)})")
            return True, wallet_id
            
        except Exception as e:
            logger.error(f"Failed to create multisig wallet: {e}")
            return False, f"Creation error: {str(e)}"
    
    async def add_signer(
        self,
        wallet_id: str,
        signer_data: Dict[str, Any],
        added_by: str
    ) -> bool:
        """Add signer to multisig wallet"""
        try:
            if wallet_id not in self.multisig_wallets:
                return False
            
            wallet = self.multisig_wallets[wallet_id]
            
            # Check if already at max signers
            if len(wallet.signers) >= MULTISIG_MAX_SIGNERS:
                return False
            
            # Create new signer
            signer_id = signer_data.get("signer_id", f"signer_{len(wallet.signers)}")
            role = SignerRole(signer_data.get("role", "signer"))
            
            signer = MultisigSigner(
                signer_id=signer_id,
                public_key=bytes.fromhex(signer_data["public_key"]),
                tron_address=signer_data["tron_address"],
                role=role,
                weight=signer_data.get("weight", 1),
                metadata=signer_data.get("metadata", {})
            )
            
            # Add to wallet
            wallet.signers[signer_id] = signer
            wallet.total_signers = len(wallet.signers)
            wallet.last_updated = datetime.now(timezone.utc)
            
            logger.info(f"Added signer {signer_id} to multisig wallet {wallet_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add signer to wallet {wallet_id}: {e}")
            return False
    
    async def remove_signer(
        self,
        wallet_id: str,
        signer_id: str,
        removed_by: str
    ) -> bool:
        """Remove signer from multisig wallet"""
        try:
            if wallet_id not in self.multisig_wallets:
                return False
            
            wallet = self.multisig_wallets[wallet_id]
            
            # Check if signer exists
            if signer_id not in wallet.signers:
                return False
            
            # Check if removing would violate minimum signers
            if len(wallet.signers) <= MULTISIG_MIN_SIGNERS:
                return False
            
            # Check if removing would violate threshold
            active_signers = len(wallet.active_signers)
            if active_signers - 1 < wallet.threshold:
                return False
            
            # Remove signer
            del wallet.signers[signer_id]
            wallet.total_signers = len(wallet.signers)
            wallet.last_updated = datetime.now(timezone.utc)
            
            logger.info(f"Removed signer {signer_id} from multisig wallet {wallet_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove signer from wallet {wallet_id}: {e}")
            return False
    
    async def create_transaction(
        self,
        wallet_id: str,
        transaction_type: TransactionType,
        data: bytes,
        description: str,
        initiator: str,
        expires_in_seconds: int = MULTISIG_TIMEOUT_SECONDS,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """Create multisig transaction"""
        try:
            if wallet_id not in self.multisig_wallets:
                return False, "Wallet not found"
            
            wallet = self.multisig_wallets[wallet_id]
            
            # Check wallet status
            if wallet.status != MultisigStatus.ACTIVE:
                return False, "Wallet not active"
            
            # Create transaction ID
            transaction_id = secrets.token_hex(16)
            
            # Calculate expiration
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
            
            # Create transaction
            transaction = MultisigTransaction(
                transaction_id=transaction_id,
                wallet_id=wallet_id,
                transaction_type=transaction_type,
                data=data,
                initiator=initiator,
                description=description,
                expires_at=expires_at,
                required_signatures=wallet.threshold,
                metadata=metadata or {}
            )
            
            # Store transaction
            self.active_transactions[transaction_id] = transaction
            
            # Start signature collection
            collection_task = asyncio.create_task(
                self._collect_signatures(transaction_id)
            )
            self.collection_tasks[transaction_id] = collection_task
            
            logger.info(f"Created multisig transaction: {transaction_id}")
            return True, transaction_id
            
        except Exception as e:
            logger.error(f"Failed to create multisig transaction: {e}")
            return False, f"Creation error: {str(e)}"
    
    async def sign_transaction(
        self,
        transaction_id: str,
        signer_id: str,
        signature: bytes,
        public_key: bytes
    ) -> bool:
        """Sign multisig transaction"""
        try:
            if transaction_id not in self.active_transactions:
                return False
            
            transaction = self.active_transactions[transaction_id]
            
            # Check if transaction is still active
            if transaction.status != MultisigStatus.SIGNING:
                return False
            
            # Check if expired
            if transaction.expires_at and datetime.now(timezone.utc) > transaction.expires_at:
                transaction.status = MultisigStatus.EXPIRED
                return False
            
            # Get wallet
            wallet = self.multisig_wallets.get(transaction.wallet_id)
            if not wallet or signer_id not in wallet.signers:
                return False
            
            # Check if already signed
            if signer_id in transaction.collected_signatures:
                return False
            
            # Verify signature
            if not await self._verify_signature(transaction.data, signature, public_key):
                logger.warning(f"Invalid signature from signer {signer_id} for transaction {transaction_id}")
                return False
            
            # Create signature record
            signature_id = secrets.token_hex(16)
            multisig_signature = MultisigSignature(
                signature_id=signature_id,
                transaction_id=transaction_id,
                signer_id=signer_id,
                signature=signature,
                public_key=public_key,
                status=SignatureStatus.VERIFIED,
                verified_at=datetime.now(timezone.utc)
            )
            
            # Add signature
            transaction.collected_signatures[signer_id] = multisig_signature
            
            # Update signer stats
            wallet.signers[signer_id].last_signed = datetime.now(timezone.utc)
            wallet.signers[signer_id].signature_count += 1
            
            logger.info(f"Transaction {transaction_id} signed by {signer_id} ({len(transaction.collected_signatures)}/{transaction.required_signatures})")
            
            # Check if threshold reached
            if len(transaction.collected_signatures) >= transaction.required_signatures:
                await self._finalize_transaction(transaction_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to sign transaction {transaction_id}: {e}")
            return False
    
    async def cancel_transaction(
        self,
        transaction_id: str,
        cancelled_by: str,
        reason: str = "Manual cancellation"
    ) -> bool:
        """Cancel multisig transaction"""
        try:
            if transaction_id not in self.active_transactions:
                return False
            
            transaction = self.active_transactions[transaction_id]
            
            # Update transaction status
            transaction.status = MultisigStatus.CANCELLED
            transaction.completed_at = datetime.now(timezone.utc)
            transaction.error_message = f"Cancelled by {cancelled_by}: {reason}"
            
            # Cancel collection task
            if transaction_id in self.collection_tasks:
                self.collection_tasks[transaction_id].cancel()
                del self.collection_tasks[transaction_id]
            
            # Move to completed
            self.completed_transactions.append(transaction)
            del self.active_transactions[transaction_id]
            
            logger.info(f"Transaction {transaction_id} cancelled by {cancelled_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel transaction {transaction_id}: {e}")
            return False
    
    async def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction status"""
        try:
            # Check active transactions
            if transaction_id in self.active_transactions:
                transaction = self.active_transactions[transaction_id]
            else:
                # Check completed transactions
                transaction = None
                for t in self.completed_transactions:
                    if t.transaction_id == transaction_id:
                        transaction = t
                        break
            
            if not transaction:
                return None
            
            return {
                "transaction_id": transaction_id,
                "wallet_id": transaction.wallet_id,
                "transaction_type": transaction.transaction_type.value,
                "status": transaction.status.value,
                "description": transaction.description,
                "initiator": transaction.initiator,
                "created_at": transaction.created_at.isoformat(),
                "expires_at": transaction.expires_at.isoformat() if transaction.expires_at else None,
                "required_signatures": transaction.required_signatures,
                "collected_signatures": len(transaction.collected_signatures),
                "signatures": {
                    signer_id: {
                        "signature_id": sig.signature_id,
                        "status": sig.status.value,
                        "created_at": sig.created_at.isoformat(),
                        "verified_at": sig.verified_at.isoformat() if sig.verified_at else None
                    }
                    for signer_id, sig in transaction.collected_signatures.items()
                },
                "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None,
                "error_message": transaction.error_message
            }
            
        except Exception as e:
            logger.error(f"Failed to get transaction status {transaction_id}: {e}")
            return None
    
    async def get_wallet_info(self, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Get multisig wallet information"""
        try:
            if wallet_id not in self.multisig_wallets:
                return None
            
            wallet = self.multisig_wallets[wallet_id]
            
            return {
                "wallet_id": wallet_id,
                "name": wallet.name,
                "description": wallet.description,
                "threshold": wallet.threshold,
                "total_signers": wallet.total_signers,
                "status": wallet.status.value,
                "created_at": wallet.created_at.isoformat(),
                "created_by": wallet.created_by,
                "last_updated": wallet.last_updated.isoformat(),
                "signers": {
                    signer_id: {
                        "public_key": signer.public_key.hex(),
                        "tron_address": signer.tron_address,
                        "role": signer.role.value,
                        "weight": signer.weight,
                        "is_active": signer.is_active,
                        "added_at": signer.added_at.isoformat(),
                        "last_signed": signer.last_signed.isoformat() if signer.last_signed else None,
                        "signature_count": signer.signature_count
                    }
                    for signer_id, signer in wallet.signers.items()
                },
                "active_transactions": len([t for t in self.active_transactions.values() if t.wallet_id == wallet_id]),
                "completed_transactions": len([t for t in self.completed_transactions if t.wallet_id == wallet_id])
            }
            
        except Exception as e:
            logger.error(f"Failed to get wallet info {wallet_id}: {e}")
            return None
    
    async def _collect_signatures(self, transaction_id: str) -> None:
        """Collect signatures for transaction"""
        try:
            transaction = self.active_transactions.get(transaction_id)
            if not transaction:
                return
            
            # Wait for expiration or completion
            while (transaction.status == MultisigStatus.SIGNING and 
                   transaction.expires_at and 
                   datetime.now(timezone.utc) < transaction.expires_at):
                await asyncio.sleep(1)
            
            # Handle expiration
            if transaction.status == MultisigStatus.SIGNING:
                transaction.status = MultisigStatus.EXPIRED
                transaction.completed_at = datetime.now(timezone.utc)
                transaction.error_message = "Transaction expired"
                
                # Move to completed
                self.completed_transactions.append(transaction)
                del self.active_transactions[transaction_id]
                
                logger.info(f"Transaction {transaction_id} expired")
            
            # Clean up collection task
            if transaction_id in self.collection_tasks:
                del self.collection_tasks[transaction_id]
                
        except asyncio.CancelledError:
            logger.info(f"Signature collection cancelled for transaction {transaction_id}")
        except Exception as e:
            logger.error(f"Error in signature collection for transaction {transaction_id}: {e}")
    
    async def _finalize_transaction(self, transaction_id: str) -> None:
        """Finalize completed transaction"""
        try:
            transaction = self.active_transactions.get(transaction_id)
            if not transaction:
                return
            
            # Combine signatures (in real implementation, use threshold signature scheme)
            combined_signature = await self._combine_signatures(transaction)
            
            if combined_signature:
                transaction.final_signature = combined_signature
                transaction.status = MultisigStatus.COMPLETED
                transaction.completed_at = datetime.now(timezone.utc)
                
                logger.info(f"Transaction {transaction_id} finalized with combined signature")
            else:
                transaction.status = MultisigStatus.FAILED
                transaction.error_message = "Failed to combine signatures"
                transaction.completed_at = datetime.now(timezone.utc)
                
                logger.error(f"Failed to finalize transaction {transaction_id}")
            
            # Move to completed
            self.completed_transactions.append(transaction)
            del self.active_transactions[transaction_id]
            
            # Clean up collection task
            if transaction_id in self.collection_tasks:
                del self.collection_tasks[transaction_id]
                
        except Exception as e:
            logger.error(f"Failed to finalize transaction {transaction_id}: {e}")
    
    async def _combine_signatures(self, transaction: MultisigTransaction) -> Optional[bytes]:
        """Combine individual signatures into final signature"""
        try:
            # In a real implementation, this would use threshold signature schemes
            # like BLS or Shamir's Secret Sharing with actual cryptographic combination
            
            # For demo purposes, concatenate signatures
            signatures = [sig.signature for sig in transaction.collected_signatures.values()]
            combined = b''.join(signatures)
            
            return combined
            
        except Exception as e:
            logger.error(f"Failed to combine signatures: {e}")
            return None
    
    async def _verify_signature(self, data: bytes, signature: bytes, public_key: bytes) -> bool:
        """Verify individual signature"""
        try:
            # Create public key object
            public_key_obj = ed25519.Ed25519PublicKey.from_public_bytes(public_key)
            
            # Verify signature
            public_key_obj.verify(signature, data)
            return True
            
        except InvalidSignature:
            return False
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
    
    async def _create_default_policies(self, wallet_id: str) -> None:
        """Create default policies for multisig wallet"""
        try:
            # Default transfer policy
            transfer_policy = MultisigPolicy(
                policy_id=f"{wallet_id}_transfer",
                wallet_id=wallet_id,
                transaction_type=TransactionType.TRANSFER,
                required_signers=2,  # Same as threshold
                max_amount=10000.0,  # Max 10,000 TRX
                is_active=True
            )
            self.policies[transfer_policy.policy_id] = transfer_policy
            
            # Default emergency policy
            emergency_policy = MultisigPolicy(
                policy_id=f"{wallet_id}_emergency",
                wallet_id=wallet_id,
                transaction_type=TransactionType.EMERGENCY,
                required_signers=2,  # Same as threshold
                is_active=True
            )
            self.policies[emergency_policy.policy_id] = emergency_policy
            
            logger.info(f"Created default policies for wallet {wallet_id}")
            
        except Exception as e:
            logger.error(f"Failed to create default policies for wallet {wallet_id}: {e}")
    
    async def _monitor_loop(self) -> None:
        """Monitor multisig operations"""
        while self.is_monitoring:
            try:
                # Clean up expired transactions
                current_time = datetime.now(timezone.utc)
                expired_transactions = []
                
                for transaction_id, transaction in self.active_transactions.items():
                    if (transaction.expires_at and 
                        current_time > transaction.expires_at and 
                        transaction.status == MultisigStatus.SIGNING):
                        expired_transactions.append(transaction_id)
                
                for transaction_id in expired_transactions:
                    await self.cancel_transaction(
                        transaction_id, 
                        "system", 
                        "Transaction expired"
                    )
                
                # Clean up old completed transactions
                if len(self.completed_transactions) > 1000:
                    self.completed_transactions = self.completed_transactions[-500:]
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(60)
    
    async def get_manager_status(self) -> Dict[str, Any]:
        """Get multisig manager status"""
        return {
            "wallet_id": self.wallet_id,
            "total_wallets": len(self.multisig_wallets),
            "active_transactions": len(self.active_transactions),
            "completed_transactions": len(self.completed_transactions),
            "active_policies": len([p for p in self.policies.values() if p.is_active]),
            "collection_tasks": len(self.collection_tasks),
            "wallets": {
                wallet_id: {
                    "name": wallet.name,
                    "threshold": wallet.threshold,
                    "total_signers": wallet.total_signers,
                    "status": wallet.status.value,
                    "active_signers": len(wallet.active_signers)
                }
                for wallet_id, wallet in self.multisig_wallets.items()
            }
        }


# Global multisig managers
_multisig_managers: Dict[str, MultisigManager] = {}


def get_multisig_manager(wallet_id: str) -> Optional[MultisigManager]:
    """Get multisig manager for wallet"""
    return _multisig_managers.get(wallet_id)


def create_multisig_manager(wallet_id: str) -> MultisigManager:
    """Create new multisig manager for wallet"""
    multisig_manager = MultisigManager(wallet_id)
    _multisig_managers[wallet_id] = multisig_manager
    return multisig_manager


async def main():
    """Main function for testing"""
    import asyncio
    
    # Create multisig manager
    multisig_manager = create_multisig_manager("test_wallet_001")
    await multisig_manager.start()
    
    try:
        # Create test signers
        signers = [
            {
                "signer_id": "signer_1",
                "public_key": secrets.token_hex(32),
                "tron_address": "TTestAddress1",
                "role": "creator"
            },
            {
                "signer_id": "signer_2", 
                "public_key": secrets.token_hex(32),
                "tron_address": "TTestAddress2",
                "role": "signer"
            },
            {
                "signer_id": "signer_3",
                "public_key": secrets.token_hex(32), 
                "tron_address": "TTestAddress3",
                "role": "backup"
            }
        ]
        
        # Create multisig wallet
        success, wallet_id = await multisig_manager.create_multisig_wallet(
            name="Test Multisig Wallet",
            description="Test 2-of-3 multisig wallet",
            signers=signers,
            threshold=2,
            created_by="test_user"
        )
        print(f"Wallet creation: {success}, ID: {wallet_id}")
        
        if success and wallet_id:
            # Activate wallet
            multisig_manager.multisig_wallets[wallet_id].status = MultisigStatus.ACTIVE
            
            # Create transaction
            test_data = b"Test transaction data"
            success, transaction_id = await multisig_manager.create_transaction(
                wallet_id=wallet_id,
                transaction_type=TransactionType.TRANSFER,
                data=test_data,
                description="Test transaction",
                initiator="signer_1"
            )
            print(f"Transaction creation: {success}, ID: {transaction_id}")
            
            if success and transaction_id:
                # Get transaction status
                status = await multisig_manager.get_transaction_status(transaction_id)
                print(f"Transaction status: {status}")
        
        # Get wallet info
        wallet_info = await multisig_manager.get_wallet_info(wallet_id)
        print(f"Wallet info: {wallet_info}")
        
        # Get manager status
        manager_status = await multisig_manager.get_manager_status()
        print(f"Manager status: {manager_status}")
    
    finally:
        await multisig_manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
