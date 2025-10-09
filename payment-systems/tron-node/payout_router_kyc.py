"""
LUCID Payment Systems - PayoutRouterKYC Integration
KYC-gated USDT payout router for node-workers with compliance signatures
Distroless container: pickme/lucid:payment-systems:latest
"""

import asyncio
import json
import logging
import os
import time
import hashlib
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import aiofiles
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field
import aiohttp
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider
import httpx

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KYCStatus(str, Enum):
    """KYC verification status"""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUSPENDED = "suspended"

class ComplianceLevel(str, Enum):
    """Compliance verification levels"""
    BASIC = "basic"           # Basic KYC verification
    ENHANCED = "enhanced"     # Enhanced due diligence
    INSTITUTIONAL = "institutional"  # Institutional compliance
    GOVERNMENT = "government"  # Government entity compliance

class PayoutStatus(str, Enum):
    """Payout transaction status"""
    PENDING = "pending"
    KYC_PENDING = "kyc_pending"
    COMPLIANCE_PENDING = "compliance_pending"
    APPROVED = "approved"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REJECTED = "rejected"
    EXPIRED = "expired"

class PayoutReason(str, Enum):
    """Payout reason codes for node workers"""
    NODE_OPERATION = "node_operation"
    STORAGE_PROVISION = "storage_provision"
    BANDWIDTH_RELAY = "bandwidth_relay"
    CONSENSUS_PARTICIPATION = "consensus_participation"
    GOVERNANCE_VOTING = "governance_voting"
    VALIDATION_SERVICE = "validation_service"
    UPTIME_REWARD = "uptime_reward"
    MAINTENANCE_REWARD = "maintenance_reward"

@dataclass
class KYCRecord:
    """KYC verification record"""
    node_id: str
    wallet_address: str
    kyc_hash: str
    compliance_level: ComplianceLevel
    status: KYCStatus
    verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    verification_data: Optional[Dict[str, Any]] = None
    compliance_signature: Optional[str] = None
    created_at: datetime = None

@dataclass
class ComplianceSignature:
    """Compliance signature for KYC payouts"""
    node_id: str
    kyc_hash: str
    payout_amount: float
    payout_reason: PayoutReason
    signature: str
    signed_by: str  # Compliance authority
    signature_timestamp: datetime
    signature_valid_until: datetime
    compliance_level: ComplianceLevel
    additional_metadata: Optional[Dict[str, Any]] = None

@dataclass
class KYCPayoutRequest:
    """KYC payout request data"""
    recipient_address: str
    amount_usdt: float
    reason: PayoutReason
    node_id: str
    kyc_hash: str
    compliance_signature: ComplianceSignature
    session_id: Optional[str] = None
    work_credits: Optional[float] = None
    custom_data: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    gas_limit: Optional[int] = None
    energy_limit: Optional[int] = None

@dataclass
class KYCPayoutTransaction:
    """KYC payout transaction record"""
    payout_id: str
    request: KYCPayoutRequest
    txid: Optional[str] = None
    status: PayoutStatus = PayoutStatus.PENDING
    gas_used: Optional[int] = None
    energy_used: Optional[int] = None
    fee_paid: Optional[float] = None
    created_at: datetime = None
    approved_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    compliance_verified: bool = False
    kyc_verified: bool = False

@dataclass
class KYCRouterConfig:
    """PayoutRouterKYC configuration"""
    contract_address: str
    owner_address: str
    private_key: str
    usdt_contract_address: str
    compliance_authority_address: str
    gas_limit: int = 1500000  # Higher for KYC operations
    energy_limit: int = 15000000
    fee_limit: int = 2000000000  # 2 TRX in sun
    max_payout_amount: float = 5000.0  # Higher limit for KYC users
    daily_limit: float = 50000.0  # Higher daily limit
    min_payout_amount: float = 0.01
    kyc_expiry_days: int = 365  # KYC valid for 1 year
    compliance_signature_validity_hours: int = 24  # Compliance signatures valid for 24 hours
    confirmation_blocks: int = 19

class KYCPayoutRequestModel(BaseModel):
    """Pydantic model for KYC payout requests"""
    recipient_address: str = Field(..., description="TRON address to receive USDT")
    amount_usdt: float = Field(..., gt=0, description="Amount in USDT")
    reason: PayoutReason = Field(..., description="Reason for payout")
    node_id: str = Field(..., description="Node ID requesting payout")
    kyc_hash: str = Field(..., description="KYC verification hash")
    compliance_signature: Dict[str, Any] = Field(..., description="Compliance signature data")
    session_id: Optional[str] = Field(default=None, description="Associated session ID")
    work_credits: Optional[float] = Field(default=None, description="Work credits earned")
    custom_data: Optional[Dict[str, Any]] = Field(default=None, description="Custom data")
    expires_at: Optional[str] = Field(default=None, description="Expiration timestamp")

class KYCPayoutResponseModel(BaseModel):
    """Pydantic model for KYC payout responses"""
    payout_id: str
    txid: Optional[str] = None
    status: str
    message: str
    amount_usdt: float
    recipient_address: str
    node_id: str
    kyc_verified: bool
    compliance_verified: bool
    created_at: str
    estimated_confirmation: Optional[str] = None

class PayoutRouterKYC:
    """PayoutRouterKYC contract integration for KYC-gated USDT payouts"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # TRON network configuration
        self.network = self.settings.TRON_NETWORK
        self.endpoint = self._resolve_endpoint()
        
        # Contract addresses
        self.payout_router_address = self.settings.PAYOUT_ROUTER_KYC_ADDRESS
        self.usdt_address = self._get_usdt_address()
        
        # Initialize TRON client
        headers = {}
        if self.settings.TRONGRID_API_KEY:
            headers["TRON-PRO-API-KEY"] = self.settings.TRONGRID_API_KEY
        
        self.provider = HTTPProvider(
            self.endpoint, 
            client=httpx.Client(headers=headers, timeout=30)
        )
        self.tron = Tron(provider=self.provider)
        
        # Router configuration
        self.config = KYCRouterConfig(
            contract_address=self.payout_router_address,
            owner_address=self.settings.TRON_ADDRESS or "",
            private_key=self.settings.TRON_PRIVATE_KEY or "",
            usdt_contract_address=self.usdt_address,
            compliance_authority_address=os.getenv("COMPLIANCE_AUTHORITY_ADDRESS", ""),
            gas_limit=int(os.getenv("KYC_PAYOUT_GAS_LIMIT", "1500000")),
            energy_limit=int(os.getenv("KYC_PAYOUT_ENERGY_LIMIT", "15000000")),
            fee_limit=int(os.getenv("KYC_PAYOUT_FEE_LIMIT", "2000000000")),
            max_payout_amount=float(os.getenv("KYC_MAX_PAYOUT_AMOUNT", "5000.0")),
            daily_limit=float(os.getenv("KYC_DAILY_PAYOUT_LIMIT", "50000.0")),
            min_payout_amount=float(os.getenv("KYC_MIN_PAYOUT_AMOUNT", "0.01")),
            kyc_expiry_days=int(os.getenv("KYC_EXPIRY_DAYS", "365")),
            compliance_signature_validity_hours=int(os.getenv("COMPLIANCE_SIGNATURE_VALIDITY_HOURS", "24")),
            confirmation_blocks=int(os.getenv("CONFIRMATION_BLOCKS", "19"))
        )
        
        # Data storage
        self.data_dir = Path("/data/payment-systems/payout-router-kyc")
        self.payouts_dir = self.data_dir / "payouts"
        self.kyc_dir = self.data_dir / "kyc"
        self.logs_dir = self.data_dir / "logs"
        
        # Ensure directories exist
        for directory in [self.payouts_dir, self.kyc_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Payout tracking
        self.pending_payouts: Dict[str, KYCPayoutTransaction] = {}
        self.confirmed_payouts: Dict[str, KYCPayoutTransaction] = {}
        
        # KYC registry
        self.kyc_records: Dict[str, KYCRecord] = {}
        
        # Daily limits tracking
        self.daily_payouts: Dict[str, float] = {}  # date -> total_amount
        self.last_reset_date = datetime.now().date()
        
        # Load existing data
        asyncio.create_task(self._load_existing_data())
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_pending_payouts())
        asyncio.create_task(self._monitor_kyc_expiry())
        asyncio.create_task(self._cleanup_old_payouts())
        
        logger.info(f"PayoutRouterKYC initialized: {self.network} -> {self.endpoint}")
    
    def _resolve_endpoint(self) -> str:
        """Resolve TRON endpoint"""
        if self.settings.TRON_HTTP_ENDPOINT:
            return self.settings.TRON_HTTP_ENDPOINT
        
        if self.network.lower() == "shasta":
            return "https://api.shasta.trongrid.io"
        
        return "https://api.trongrid.io"
    
    def _get_usdt_address(self) -> str:
        """Get USDT contract address for network"""
        if self.network.lower() == "mainnet":
            return "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # USDT-TRC20 mainnet
        else:
            return "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs"  # USDT-TRC20 shasta
    
    async def _load_existing_data(self):
        """Load existing payouts and KYC records from disk"""
        try:
            # Load payouts
            payouts_file = self.payouts_dir / "payouts_registry.json"
            if payouts_file.exists():
                async with aiofiles.open(payouts_file, "r") as f:
                    data = await f.read()
                    payouts_data = json.loads(data)
                    
                    for payout_id, payout_data in payouts_data.items():
                        # Convert datetime strings back to datetime objects
                        payout_transaction = self._deserialize_payout_transaction(payout_data)
                        
                        if payout_transaction.status == PayoutStatus.PENDING:
                            self.pending_payouts[payout_id] = payout_transaction
                        else:
                            self.confirmed_payouts[payout_id] = payout_transaction
                    
                logger.info(f"Loaded {len(self.pending_payouts)} pending and {len(self.confirmed_payouts)} confirmed KYC payouts")
            
            # Load KYC records
            kyc_file = self.kyc_dir / "kyc_registry.json"
            if kyc_file.exists():
                async with aiofiles.open(kyc_file, "r") as f:
                    data = await f.read()
                    kyc_data = json.loads(data)
                    
                    for node_id, kyc_record_data in kyc_data.items():
                        kyc_record = self._deserialize_kyc_record(kyc_record_data)
                        self.kyc_records[node_id] = kyc_record
                    
                logger.info(f"Loaded {len(self.kyc_records)} KYC records")
                
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
    
    def _deserialize_payout_transaction(self, data: Dict[str, Any]) -> KYCPayoutTransaction:
        """Deserialize payout transaction from JSON"""
        # Handle datetime fields
        for field in ['created_at', 'approved_at', 'confirmed_at', 'expires_at']:
            if field in data and data[field]:
                data[field] = datetime.fromisoformat(data[field])
        
        # Handle nested objects
        if 'request' in data and 'compliance_signature' in data['request']:
            cs_data = data['request']['compliance_signature']
            if 'signature_timestamp' in cs_data and cs_data['signature_timestamp']:
                cs_data['signature_timestamp'] = datetime.fromisoformat(cs_data['signature_timestamp'])
            if 'signature_valid_until' in cs_data and cs_data['signature_valid_until']:
                cs_data['signature_valid_until'] = datetime.fromisoformat(cs_data['signature_valid_until'])
        
        return KYCPayoutTransaction(**data)
    
    def _deserialize_kyc_record(self, data: Dict[str, Any]) -> KYCRecord:
        """Deserialize KYC record from JSON"""
        # Handle datetime fields
        for field in ['created_at', 'verified_at', 'expires_at']:
            if field in data and data[field]:
                data[field] = datetime.fromisoformat(data[field])
        
        return KYCRecord(**data)
    
    async def _save_data_registry(self):
        """Save payouts and KYC registries to disk"""
        try:
            # Save payouts
            all_payouts = {**self.pending_payouts, **self.confirmed_payouts}
            
            payouts_data = {}
            for payout_id, payout_transaction in all_payouts.items():
                payout_dict = asdict(payout_transaction)
                # Serialize datetime fields
                for field in ['created_at', 'approved_at', 'confirmed_at']:
                    if payout_dict.get(field):
                        payout_dict[field] = payout_dict[field].isoformat()
                
                # Serialize nested datetime fields
                if 'request' in payout_dict and 'compliance_signature' in payout_dict['request']:
                    cs_data = payout_dict['request']['compliance_signature']
                    for field in ['signature_timestamp', 'signature_valid_until']:
                        if cs_data.get(field):
                            cs_data[field] = cs_data[field].isoformat()
                
                payouts_data[payout_id] = payout_dict
            
            payouts_file = self.payouts_dir / "payouts_registry.json"
            async with aiofiles.open(payouts_file, "w") as f:
                await f.write(json.dumps(payouts_data, indent=2))
            
            # Save KYC records
            kyc_data = {}
            for node_id, kyc_record in self.kyc_records.items():
                kyc_dict = asdict(kyc_record)
                # Serialize datetime fields
                for field in ['created_at', 'verified_at', 'expires_at']:
                    if kyc_dict.get(field):
                        kyc_dict[field] = kyc_dict[field].isoformat()
                kyc_data[node_id] = kyc_dict
            
            kyc_file = self.kyc_dir / "kyc_registry.json"
            async with aiofiles.open(kyc_file, "w") as f:
                await f.write(json.dumps(kyc_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving data registry: {e}")
    
    async def register_kyc(self, node_id: str, wallet_address: str, 
                          kyc_hash: str, compliance_level: ComplianceLevel,
                          verification_data: Optional[Dict[str, Any]] = None) -> bool:
        """Register KYC verification for a node"""
        try:
            logger.info(f"Registering KYC for node: {node_id}")
            
            # Validate KYC hash
            if not self._validate_kyc_hash(kyc_hash):
                raise ValueError("Invalid KYC hash format")
            
            # Check if node already has KYC
            if node_id in self.kyc_records:
                existing_record = self.kyc_records[node_id]
                if existing_record.status == KYCStatus.VERIFIED and not self._is_kyc_expired(existing_record):
                    logger.warning(f"Node {node_id} already has valid KYC")
                    return True
            
            # Create KYC record
            kyc_record = KYCRecord(
                node_id=node_id,
                wallet_address=wallet_address,
                kyc_hash=kyc_hash,
                compliance_level=compliance_level,
                status=KYCStatus.PENDING,
                verification_data=verification_data,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=self.config.kyc_expiry_days)
            )
            
            # Store KYC record
            self.kyc_records[node_id] = kyc_record
            
            # Save registry
            await self._save_data_registry()
            
            # Log KYC registration
            await self._log_kyc_event(node_id, "kyc_registered", {
                "wallet_address": wallet_address,
                "kyc_hash": kyc_hash,
                "compliance_level": compliance_level.value
            })
            
            logger.info(f"KYC registered for node: {node_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering KYC: {e}")
            return False
    
    async def verify_kyc(self, node_id: str, compliance_signature: str) -> bool:
        """Verify KYC for a node"""
        try:
            if node_id not in self.kyc_records:
                raise ValueError(f"KYC record not found for node: {node_id}")
            
            kyc_record = self.kyc_records[node_id]
            
            # Verify compliance signature
            if not await self._verify_compliance_signature(compliance_signature, kyc_record):
                raise ValueError("Invalid compliance signature")
            
            # Update KYC status
            kyc_record.status = KYCStatus.VERIFIED
            kyc_record.verified_at = datetime.now()
            kyc_record.compliance_signature = compliance_signature
            
            # Save registry
            await self._save_data_registry()
            
            # Log KYC verification
            await self._log_kyc_event(node_id, "kyc_verified", {
                "compliance_signature": compliance_signature,
                "compliance_level": kyc_record.compliance_level.value
            })
            
            logger.info(f"KYC verified for node: {node_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying KYC: {e}")
            return False
    
    def _validate_kyc_hash(self, kyc_hash: str) -> bool:
        """Validate KYC hash format"""
        try:
            # Basic validation - should be a hex string of reasonable length
            return len(kyc_hash) == 64 and all(c in '0123456789abcdefABCDEF' for c in kyc_hash)
        except Exception:
            return False
    
    def _is_kyc_expired(self, kyc_record: KYCRecord) -> bool:
        """Check if KYC record is expired"""
        if not kyc_record.expires_at:
            return False
        return datetime.now() > kyc_record.expires_at
    
    async def _verify_compliance_signature(self, signature: str, kyc_record: KYCRecord) -> bool:
        """Verify compliance signature"""
        try:
            # In a real implementation, this would verify the signature against
            # the compliance authority's public key
            # For now, we'll do basic validation
            
            if not signature or len(signature) < 64:
                return False
            
            # Additional signature validation would go here
            return True
            
        except Exception as e:
            logger.error(f"Error verifying compliance signature: {e}")
            return False
    
    async def create_kyc_payout(self, request: KYCPayoutRequestModel) -> KYCPayoutResponseModel:
        """Create a new KYC-gated USDT payout"""
        try:
            logger.info(f"Creating KYC payout: {request.amount_usdt} USDT to {request.recipient_address}")
            
            # Validate payout request
            await self._validate_kyc_payout_request(request)
            
            # Generate payout ID
            payout_id = await self._generate_payout_id(request)
            
            # Parse compliance signature
            compliance_signature = ComplianceSignature(**request.compliance_signature)
            
            # Convert to internal request format
            kyc_payout_request = KYCPayoutRequest(
                recipient_address=request.recipient_address,
                amount_usdt=request.amount_usdt,
                reason=PayoutReason(request.reason),
                node_id=request.node_id,
                kyc_hash=request.kyc_hash,
                compliance_signature=compliance_signature,
                session_id=request.session_id,
                work_credits=request.work_credits,
                custom_data=request.custom_data,
                expires_at=datetime.fromisoformat(request.expires_at) if request.expires_at else None
            )
            
            # Create payout transaction
            payout_transaction = KYCPayoutTransaction(
                payout_id=payout_id,
                request=kyc_payout_request,
                created_at=datetime.now()
            )
            
            # Verify KYC and compliance
            kyc_verified = await self._verify_node_kyc(request.node_id, request.kyc_hash)
            compliance_verified = await self._verify_compliance_signature_validity(compliance_signature)
            
            payout_transaction.kyc_verified = kyc_verified
            payout_transaction.compliance_verified = compliance_verified
            
            if kyc_verified and compliance_verified:
                payout_transaction.status = PayoutStatus.APPROVED
                
                # Execute payout
                txid = await self._execute_kyc_payout(payout_transaction)
                payout_transaction.txid = txid
                payout_transaction.status = PayoutStatus.CONFIRMED
                payout_transaction.confirmed_at = datetime.now()
                
            elif not kyc_verified:
                payout_transaction.status = PayoutStatus.KYC_PENDING
            elif not compliance_verified:
                payout_transaction.status = PayoutStatus.COMPLIANCE_PENDING
            
            # Store payout
            if payout_transaction.status == PayoutStatus.CONFIRMED:
                self.confirmed_payouts[payout_id] = payout_transaction
            else:
                self.pending_payouts[payout_id] = payout_transaction
            
            # Update daily limits
            await self._update_daily_limits(request.amount_usdt)
            
            # Save registry
            await self._save_data_registry()
            
            # Log payout creation
            await self._log_payout_event(payout_id, "kyc_payout_created", {
                "recipient_address": request.recipient_address,
                "amount_usdt": request.amount_usdt,
                "reason": request.reason,
                "node_id": request.node_id,
                "kyc_verified": kyc_verified,
                "compliance_verified": compliance_verified,
                "txid": payout_transaction.txid
            })
            
            logger.info(f"Created KYC payout: {payout_id} -> {payout_transaction.txid}")
            
            # Calculate estimated confirmation time
            estimated_confirmation = None
            if payout_transaction.txid:
                current_block = self.tron.get_latest_block_number()
                estimated_block = current_block + self.config.confirmation_blocks
                # Rough estimate: 3 seconds per block
                estimated_time = datetime.now() + timedelta(seconds=self.config.confirmation_blocks * 3)
                estimated_confirmation = estimated_time.isoformat()
            
            return KYCPayoutResponseModel(
                payout_id=payout_id,
                txid=payout_transaction.txid,
                status=payout_transaction.status.value,
                message="KYC payout created successfully",
                amount_usdt=request.amount_usdt,
                recipient_address=request.recipient_address,
                node_id=request.node_id,
                kyc_verified=kyc_verified,
                compliance_verified=compliance_verified,
                created_at=payout_transaction.created_at.isoformat(),
                estimated_confirmation=estimated_confirmation
            )
            
        except Exception as e:
            logger.error(f"Error creating KYC payout: {e}")
            raise
    
    async def _validate_kyc_payout_request(self, request: KYCPayoutRequestModel):
        """Validate KYC payout request"""
        # Check amount limits
        if request.amount_usdt < self.config.min_payout_amount:
            raise ValueError(f"Amount too small: {request.amount_usdt} < {self.config.min_payout_amount}")
        
        if request.amount_usdt > self.config.max_payout_amount:
            raise ValueError(f"Amount too large: {request.amount_usdt} > {self.config.max_payout_amount}")
        
        # Check daily limits
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.daily_payouts = {}
            self.last_reset_date = today
        
        daily_total = self.daily_payouts.get(today.isoformat(), 0.0)
        if daily_total + request.amount_usdt > self.config.daily_limit:
            raise ValueError(f"Daily limit exceeded: {daily_total + request.amount_usdt} > {self.config.daily_limit}")
        
        # Validate TRON address
        try:
            if not request.recipient_address.startswith('T') or len(request.recipient_address) != 34:
                raise ValueError("Invalid TRON address format")
        except Exception as e:
            raise ValueError(f"Invalid recipient address: {e}")
        
        # Check contract balance
        await self._check_contract_balance(request.amount_usdt)
    
    async def _verify_node_kyc(self, node_id: str, kyc_hash: str) -> bool:
        """Verify node KYC status"""
        try:
            if node_id not in self.kyc_records:
                return False
            
            kyc_record = self.kyc_records[node_id]
            
            # Check KYC status
            if kyc_record.status != KYCStatus.VERIFIED:
                return False
            
            # Check if expired
            if self._is_kyc_expired(kyc_record):
                kyc_record.status = KYCStatus.EXPIRED
                return False
            
            # Verify KYC hash matches
            if kyc_record.kyc_hash != kyc_hash:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verifying node KYC: {e}")
            return False
    
    async def _verify_compliance_signature_validity(self, compliance_signature: ComplianceSignature) -> bool:
        """Verify compliance signature validity"""
        try:
            # Check signature timestamp
            now = datetime.now()
            if compliance_signature.signature_timestamp > now:
                return False  # Future signature
            
            # Check signature expiry
            if compliance_signature.signature_valid_until < now:
                return False  # Expired signature
            
            # Verify signature format and authority
            if not compliance_signature.signature or len(compliance_signature.signature) < 64:
                return False
            
            # Additional signature validation would go here
            return True
            
        except Exception as e:
            logger.error(f"Error verifying compliance signature validity: {e}")
            return False
    
    async def _check_contract_balance(self, amount_usdt: float):
        """Check if contract has sufficient USDT balance"""
        try:
            # Get contract USDT balance
            usdt_contract = self.tron.get_contract(self.usdt_address)
            balance_response = usdt_contract.functions.balanceOf(self.config.contract_address)
            
            # Convert from smallest unit (6 decimals for USDT)
            balance_usdt = balance_response / 1_000_000
            
            if balance_usdt < amount_usdt:
                raise RuntimeError(f"Insufficient contract balance: {balance_usdt} < {amount_usdt}")
            
            logger.debug(f"Contract USDT balance: {balance_usdt}")
            
        except Exception as e:
            logger.error(f"Error checking contract balance: {e}")
            raise
    
    async def _generate_payout_id(self, request: KYCPayoutRequestModel) -> str:
        """Generate unique payout ID"""
        timestamp = int(time.time())
        recipient_hash = hashlib.sha256(request.recipient_address.encode()).hexdigest()[:8]
        node_hash = hashlib.sha256(request.node_id.encode()).hexdigest()[:6]
        amount_hash = hashlib.sha256(str(request.amount_usdt).encode()).hexdigest()[:4]
        
        return f"kyc_payout_{timestamp}_{recipient_hash}_{node_hash}_{amount_hash}"
    
    async def _execute_kyc_payout(self, payout_transaction: KYCPayoutTransaction) -> str:
        """Execute KYC USDT payout"""
        try:
            if not self.config.private_key:
                raise RuntimeError("Private key not configured")
            
            # Initialize private key
            private_key = PrivateKey(bytes.fromhex(self.config.private_key))
            from_address = private_key.public_key.to_base58check_address()
            
            # Get contract instance
            payout_contract = self.tron.get_contract(self.config.contract_address)
            
            # Convert amount to smallest unit
            amount_sun = int(payout_transaction.request.amount_usdt * 1_000_000)
            
            # Build KYC payout transaction
            transaction = payout_contract.functions.payoutKYC(
                payout_transaction.request.recipient_address,
                amount_sun,
                payout_transaction.request.node_id,
                payout_transaction.request.kyc_hash,
                payout_transaction.request.compliance_signature.signature
            ).with_owner(from_address).fee_limit(self.config.fee_limit)
            
            # Sign and broadcast transaction
            signed_tx = transaction.build().sign(private_key)
            result = signed_tx.broadcast()
            
            if result.get('result'):
                txid = result['txid']
                logger.info(f"KYC payout transaction broadcasted: {txid}")
                return txid
            else:
                raise RuntimeError(f"Transaction failed: {result}")
                
        except Exception as e:
            logger.error(f"Error executing KYC payout: {e}")
            raise
    
    async def _update_daily_limits(self, amount_usdt: float):
        """Update daily payout limits"""
        today = datetime.now().date().isoformat()
        self.daily_payouts[today] = self.daily_payouts.get(today, 0.0) + amount_usdt
    
    async def _monitor_pending_payouts(self):
        """Monitor pending payouts for confirmation"""
        try:
            while True:
                for payout_id, payout_transaction in list(self.pending_payouts.items()):
                    if payout_transaction.txid:
                        # Check transaction status
                        status = await self._check_transaction_status(payout_transaction.txid)
                        
                        if status == "confirmed":
                            payout_transaction.status = PayoutStatus.CONFIRMED
                            payout_transaction.confirmed_at = datetime.now()
                            
                            # Move to confirmed payouts
                            self.confirmed_payouts[payout_id] = payout_transaction
                            del self.pending_payouts[payout_id]
                            
                            # Log confirmation
                            await self._log_payout_event(payout_id, "kyc_payout_confirmed", {
                                "txid": payout_transaction.txid,
                                "amount_usdt": payout_transaction.request.amount_usdt,
                                "recipient_address": payout_transaction.request.recipient_address,
                                "node_id": payout_transaction.request.node_id
                            })
                            
                            logger.info(f"KYC payout confirmed: {payout_id} -> {payout_transaction.txid}")
                        
                        elif status == "failed":
                            payout_transaction.status = PayoutStatus.FAILED
                            payout_transaction.error_message = "Transaction failed on blockchain"
                            
                            # Log failure
                            await self._log_payout_event(payout_id, "kyc_payout_failed", {
                                "txid": payout_transaction.txid,
                                "error": payout_transaction.error_message
                            })
                            
                            logger.error(f"KYC payout failed: {payout_id} -> {payout_transaction.txid}")
                
                # Save registry
                await self._save_data_registry()
                
                # Wait before next check
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            logger.info("KYC payout monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in KYC payout monitoring: {e}")
    
    async def _monitor_kyc_expiry(self):
        """Monitor KYC records for expiry"""
        try:
            while True:
                expired_nodes = []
                
                for node_id, kyc_record in self.kyc_records.items():
                    if self._is_kyc_expired(kyc_record):
                        kyc_record.status = KYCStatus.EXPIRED
                        expired_nodes.append(node_id)
                        
                        # Log KYC expiry
                        await self._log_kyc_event(node_id, "kyc_expired", {
                            "expires_at": kyc_record.expires_at.isoformat(),
                            "compliance_level": kyc_record.compliance_level.value
                        })
                
                if expired_nodes:
                    await self._save_data_registry()
                    logger.info(f"Expired KYC for {len(expired_nodes)} nodes")
                
                # Wait before next check
                await asyncio.sleep(3600)  # Check every hour
                
        except asyncio.CancelledError:
            logger.info("KYC expiry monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in KYC expiry monitoring: {e}")
    
    async def _check_transaction_status(self, txid: str) -> str:
        """Check transaction status on blockchain"""
        try:
            transaction_info = self.tron.get_transaction_info(txid)
            
            if not transaction_info:
                return "pending"
            
            receipt = transaction_info.get('receipt', {})
            if receipt.get('result') == 'SUCCESS':
                return "confirmed"
            else:
                return "failed"
                
        except Exception as e:
            logger.debug(f"Error checking transaction status: {e}")
            return "pending"
    
    async def _cleanup_old_payouts(self):
        """Clean up old confirmed payouts"""
        try:
            while True:
                cutoff_date = datetime.now() - timedelta(days=30)
                
                old_payouts = []
                for payout_id, payout_transaction in self.confirmed_payouts.items():
                    if (payout_transaction.confirmed_at and 
                        payout_transaction.confirmed_at < cutoff_date):
                        old_payouts.append(payout_id)
                
                # Remove old payouts
                for payout_id in old_payouts:
                    del self.confirmed_payouts[payout_id]
                
                if old_payouts:
                    await self._save_data_registry()
                    logger.info(f"Cleaned up {len(old_payouts)} old KYC payouts")
                
                # Wait before next cleanup
                await asyncio.sleep(3600)  # 1 hour
                
        except asyncio.CancelledError:
            logger.info("KYC payout cleanup cancelled")
        except Exception as e:
            logger.error(f"Error in KYC payout cleanup: {e}")
    
    async def get_kyc_status(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get KYC status for a node"""
        try:
            if node_id not in self.kyc_records:
                return None
            
            kyc_record = self.kyc_records[node_id]
            
            return {
                "node_id": kyc_record.node_id,
                "wallet_address": kyc_record.wallet_address,
                "kyc_hash": kyc_record.kyc_hash,
                "compliance_level": kyc_record.compliance_level.value,
                "status": kyc_record.status.value,
                "verified_at": kyc_record.verified_at.isoformat() if kyc_record.verified_at else None,
                "expires_at": kyc_record.expires_at.isoformat() if kyc_record.expires_at else None,
                "is_expired": self._is_kyc_expired(kyc_record),
                "created_at": kyc_record.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting KYC status: {e}")
            return None
    
    async def get_payout_status(self, payout_id: str) -> Optional[Dict[str, Any]]:
        """Get KYC payout status"""
        try:
            # Check pending payouts
            if payout_id in self.pending_payouts:
                payout = self.pending_payouts[payout_id]
            elif payout_id in self.confirmed_payouts:
                payout = self.confirmed_payouts[payout_id]
            else:
                return None
            
            return {
                "payout_id": payout.payout_id,
                "recipient_address": payout.request.recipient_address,
                "amount_usdt": payout.request.amount_usdt,
                "reason": payout.request.reason.value,
                "node_id": payout.request.node_id,
                "kyc_hash": payout.request.kyc_hash,
                "status": payout.status.value,
                "txid": payout.txid,
                "kyc_verified": payout.kyc_verified,
                "compliance_verified": payout.compliance_verified,
                "created_at": payout.created_at.isoformat(),
                "confirmed_at": payout.confirmed_at.isoformat() if payout.confirmed_at else None,
                "error_message": payout.error_message,
                "retry_count": payout.retry_count
            }
            
        except Exception as e:
            logger.error(f"Error getting KYC payout status: {e}")
            return None
    
    async def list_kyc_payouts(self, status: Optional[PayoutStatus] = None, 
                              limit: int = 100) -> List[Dict[str, Any]]:
        """List KYC payouts with optional status filter"""
        try:
            all_payouts = {**self.pending_payouts, **self.confirmed_payouts}
            
            if status:
                filtered_payouts = {k: v for k, v in all_payouts.items() 
                                  if v.status == status}
            else:
                filtered_payouts = all_payouts
            
            # Sort by creation time (newest first)
            sorted_payouts = sorted(filtered_payouts.items(), 
                                  key=lambda x: x[1].created_at, reverse=True)
            
            # Limit results
            limited_payouts = sorted_payouts[:limit]
            
            payouts_list = []
            for payout_id, payout in limited_payouts:
                payouts_list.append({
                    "payout_id": payout.payout_id,
                    "recipient_address": payout.request.recipient_address,
                    "amount_usdt": payout.request.amount_usdt,
                    "reason": payout.request.reason.value,
                    "node_id": payout.request.node_id,
                    "status": payout.status.value,
                    "txid": payout.txid,
                    "kyc_verified": payout.kyc_verified,
                    "compliance_verified": payout.compliance_verified,
                    "created_at": payout.created_at.isoformat(),
                    "confirmed_at": payout.confirmed_at.isoformat() if payout.confirmed_at else None,
                    "error_message": payout.error_message
                })
            
            return payouts_list
            
        except Exception as e:
            logger.error(f"Error listing KYC payouts: {e}")
            return []
    
    async def get_kyc_payout_stats(self) -> Dict[str, Any]:
        """Get KYC payout statistics"""
        try:
            all_payouts = {**self.pending_payouts, **self.confirmed_payouts}
            
            total_payouts = len(all_payouts)
            pending_payouts = len(self.pending_payouts)
            confirmed_payouts = len(self.confirmed_payouts)
            failed_payouts = sum(1 for p in all_payouts.values() 
                               if p.status == PayoutStatus.FAILED)
            
            total_amount = sum(p.request.amount_usdt for p in all_payouts.values())
            confirmed_amount = sum(p.request.amount_usdt for p in all_payouts.values() 
                                 if p.status == PayoutStatus.CONFIRMED)
            
            # KYC statistics
            total_kyc_records = len(self.kyc_records)
            verified_kyc = sum(1 for k in self.kyc_records.values() 
                             if k.status == KYCStatus.VERIFIED)
            expired_kyc = sum(1 for k in self.kyc_records.values() 
                            if self._is_kyc_expired(k))
            
            # Daily statistics
            today = datetime.now().date().isoformat()
            daily_amount = self.daily_payouts.get(today, 0.0)
            daily_count = sum(1 for p in all_payouts.values() 
                            if p.created_at.date().isoformat() == today)
            
            return {
                "total_payouts": total_payouts,
                "pending_payouts": pending_payouts,
                "confirmed_payouts": confirmed_payouts,
                "failed_payouts": failed_payouts,
                "total_amount_usdt": total_amount,
                "confirmed_amount_usdt": confirmed_amount,
                "daily_amount_usdt": daily_amount,
                "daily_count": daily_count,
                "daily_limit_usdt": self.config.daily_limit,
                "kyc_records": {
                    "total": total_kyc_records,
                    "verified": verified_kyc,
                    "expired": expired_kyc
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting KYC payout stats: {e}")
            return {"error": str(e)}
    
    async def _log_payout_event(self, payout_id: str, event_type: str, data: Dict[str, Any]):
        """Log KYC payout event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "payout_id": payout_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"kyc_payout_events_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging KYC payout event: {e}")
    
    async def _log_kyc_event(self, node_id: str, event_type: str, data: Dict[str, Any]):
        """Log KYC event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "node_id": node_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"kyc_events_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging KYC event: {e}")

# Global instance
payout_router_kyc = PayoutRouterKYC()

# Convenience functions for external use
async def register_kyc(node_id: str, wallet_address: str, kyc_hash: str, 
                      compliance_level: ComplianceLevel) -> bool:
    """Register KYC for a node"""
    return await payout_router_kyc.register_kyc(node_id, wallet_address, kyc_hash, compliance_level)

async def verify_kyc(node_id: str, compliance_signature: str) -> bool:
    """Verify KYC for a node"""
    return await payout_router_kyc.verify_kyc(node_id, compliance_signature)

async def create_kyc_payout(request: KYCPayoutRequestModel) -> KYCPayoutResponseModel:
    """Create a new KYC payout"""
    return await payout_router_kyc.create_kyc_payout(request)

async def get_kyc_status(node_id: str) -> Optional[Dict[str, Any]]:
    """Get KYC status for a node"""
    return await payout_router_kyc.get_kyc_status(node_id)

async def get_payout_status(payout_id: str) -> Optional[Dict[str, Any]]:
    """Get KYC payout status"""
    return await payout_router_kyc.get_payout_status(payout_id)

async def list_kyc_payouts(status: Optional[PayoutStatus] = None, 
                          limit: int = 100) -> List[Dict[str, Any]]:
    """List KYC payouts"""
    return await payout_router_kyc.list_kyc_payouts(status, limit)

async def get_kyc_payout_stats() -> Dict[str, Any]:
    """Get KYC payout statistics"""
    return await payout_router_kyc.get_kyc_payout_stats()

if __name__ == "__main__":
    # Example usage
    async def main():
        # Register KYC for a node
        kyc_registered = await register_kyc(
            node_id="node_123",
            wallet_address="TYourTRONAddressHere123456789",
            kyc_hash="a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
            compliance_level=ComplianceLevel.ENHANCED
        )
        print(f"KYC registered: {kyc_registered}")
        
        # Create a KYC payout request
        compliance_signature_data = {
            "node_id": "node_123",
            "kyc_hash": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
            "payout_amount": 100.0,
            "payout_reason": "NODE_OPERATION",
            "signature": "compliance_signature_here",
            "signed_by": "compliance_authority",
            "signature_timestamp": datetime.now().isoformat(),
            "signature_valid_until": (datetime.now() + timedelta(hours=24)).isoformat(),
            "compliance_level": "ENHANCED"
        }
        
        kyc_payout_request = KYCPayoutRequestModel(
            recipient_address="TYourTRONAddressHere123456789",
            amount_usdt=100.0,
            reason=PayoutReason.NODE_OPERATION,
            node_id="node_123",
            kyc_hash="a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456",
            compliance_signature=compliance_signature_data,
            work_credits=50.0
        )
        
        try:
            # Create KYC payout
            response = await create_kyc_payout(kyc_payout_request)
            print(f"KYC payout created: {response}")
            
            # Get KYC status
            kyc_status = await get_kyc_status("node_123")
            print(f"KYC status: {kyc_status}")
            
            # Get payout status
            payout_status = await get_payout_status(response.payout_id)
            print(f"Payout status: {payout_status}")
            
            # Get statistics
            stats = await get_kyc_payout_stats()
            print(f"KYC payout stats: {stats}")
            
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main())
