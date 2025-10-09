"""
LUCID Payment Systems - Wallet Integration Manager
Unified wallet integration and management system for payment operations
Distroless container: pickme/lucid:payment-systems:latest
"""

import asyncio
import logging
import os
import time
import hashlib
import json
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import aiofiles
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WalletType(str, Enum):
    """Wallet types supported"""
    SOFTWARE = "software"           # Software wallet (Ed25519)
    HARDWARE = "hardware"           # Hardware wallet integration
    MULTISIG = "multisig"           # Multi-signature wallet
    TRON_NATIVE = "tron_native"     # TRON native wallet
    EXTERNAL = "external"           # External wallet integration

class WalletRole(str, Enum):
    """Wallet roles in the system"""
    NODE_OPERATOR = "node_operator"     # Node operator wallet
    USER_CLIENT = "user_client"         # End-user client wallet
    PAYOUT_ADMIN = "payout_admin"       # Payout administration wallet
    GOVERNANCE = "governance"           # Governance wallet
    TREASURY = "treasury"               # Treasury wallet
    BACKUP = "backup"                   # Backup wallet

class WalletStatus(str, Enum):
    """Wallet status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    SUSPENDED = "suspended"
    MAINTENANCE = "maintenance"

class IntegrationStatus(str, Enum):
    """Integration status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    AUTHENTICATING = "authenticating"
    SYNCING = "syncing"

@dataclass
class WalletInfo:
    """Wallet information"""
    wallet_id: str
    wallet_type: WalletType
    role: WalletRole
    address: str
    public_key: str
    status: WalletStatus
    integration_status: IntegrationStatus
    created_at: datetime
    last_used: Optional[datetime] = None
    balance_trx: float = 0.0
    balance_usdt: float = 0.0
    energy_available: int = 0
    bandwidth_available: int = 0
    frozen_balance: float = 0.0
    delegated_energy: int = 0
    delegated_bandwidth: int = 0
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class WalletCredentials:
    """Wallet credentials and access information"""
    wallet_id: str
    encrypted_private_key: Optional[str] = None
    passphrase_hash: Optional[str] = None
    hardware_device_id: Optional[str] = None
    multisig_threshold: Optional[int] = None
    multisig_signers: Optional[List[str]] = None
    external_api_key: Optional[str] = None
    external_endpoint: Optional[str] = None
    last_rotation: Optional[datetime] = None
    rotation_interval_days: int = 90

@dataclass
class TransactionRequest:
    """Transaction request for wallet operations"""
    wallet_id: str
    transaction_type: str
    recipient_address: str
    amount: float
    token_type: str = "TRX"  # TRX, USDT, etc.
    fee_limit: Optional[int] = None
    energy_limit: Optional[int] = None
    bandwidth_limit: Optional[int] = None
    memo: Optional[str] = None
    contract_address: Optional[str] = None
    function_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    priority: str = "normal"
    expires_at: Optional[datetime] = None

@dataclass
class TransactionResult:
    """Transaction result"""
    transaction_id: str
    wallet_id: str
    txid: Optional[str] = None
    status: str = "pending"
    fee_paid: Optional[float] = None
    gas_used: Optional[int] = None
    energy_used: Optional[int] = None
    created_at: datetime = None
    confirmed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    raw_transaction: Optional[Dict[str, Any]] = None

class WalletIntegrationRequest(BaseModel):
    """Request for wallet integration operations"""
    wallet_id: str = Field(..., description="Wallet ID")
    operation: str = Field(..., description="Operation type")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Operation parameters")

class WalletIntegrationResponse(BaseModel):
    """Response for wallet integration operations"""
    success: bool
    wallet_id: str
    operation: str
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamp: str

class WalletIntegrationManager:
    """Unified wallet integration and management system"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Data storage
        self.data_dir = Path("/data/payment-systems/wallet-integration")
        self.wallets_dir = self.data_dir / "wallets"
        self.transactions_dir = self.data_dir / "transactions"
        self.logs_dir = self.data_dir / "logs"
        
        # Ensure directories exist
        for directory in [self.wallets_dir, self.transactions_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Wallet registry
        self.wallets: Dict[str, WalletInfo] = {}
        self.credentials: Dict[str, WalletCredentials] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Transaction tracking
        self.pending_transactions: Dict[str, TransactionResult] = {}
        self.completed_transactions: Dict[str, TransactionResult] = {}
        
        # Integration adapters
        self.adapters: Dict[WalletType, Any] = {}
        
        # Security settings
        self.max_concurrent_sessions = int(os.getenv("WALLET_MAX_CONCURRENT_SESSIONS", "10"))
        self.session_timeout_minutes = int(os.getenv("WALLET_SESSION_TIMEOUT", "30"))
        self.key_rotation_interval_days = int(os.getenv("WALLET_KEY_ROTATION_DAYS", "90"))
        
        # Load existing data
        asyncio.create_task(self._load_existing_data())
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_wallets())
        asyncio.create_task(self._monitor_transactions())
        asyncio.create_task(self._cleanup_sessions())
        asyncio.create_task(self._check_key_rotation())
        
        logger.info("WalletIntegrationManager initialized")
    
    async def _load_existing_data(self):
        """Load existing wallets and transactions from disk"""
        try:
            # Load wallets
            wallets_file = self.wallets_dir / "wallets_registry.json"
            if wallets_file.exists():
                async with aiofiles.open(wallets_file, "r") as f:
                    data = await f.read()
                    wallets_data = json.loads(data)
                    
                    for wallet_id, wallet_data in wallets_data.items():
                        wallet_info = self._deserialize_wallet_info(wallet_data)
                        self.wallets[wallet_id] = wallet_info
                    
                logger.info(f"Loaded {len(self.wallets)} wallets")
            
            # Load credentials
            credentials_file = self.wallets_dir / "credentials_registry.json"
            if credentials_file.exists():
                async with aiofiles.open(credentials_file, "r") as f:
                    data = await f.read()
                    credentials_data = json.loads(data)
                    
                    for wallet_id, cred_data in credentials_data.items():
                        credentials = self._deserialize_credentials(cred_data)
                        self.credentials[wallet_id] = credentials
                    
                logger.info(f"Loaded {len(self.credentials)} credential sets")
            
            # Load transactions
            transactions_file = self.transactions_dir / "transactions_registry.json"
            if transactions_file.exists():
                async with aiofiles.open(transactions_file, "r") as f:
                    data = await f.read()
                    transactions_data = json.loads(data)
                    
                    for tx_id, tx_data in transactions_data.items():
                        transaction = self._deserialize_transaction(tx_data)
                        
                        if transaction.status == "pending":
                            self.pending_transactions[tx_id] = transaction
                        else:
                            self.completed_transactions[tx_id] = transaction
                    
                logger.info(f"Loaded {len(self.pending_transactions)} pending and {len(self.completed_transactions)} completed transactions")
                
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
    
    def _deserialize_wallet_info(self, data: Dict[str, Any]) -> WalletInfo:
        """Deserialize wallet info from JSON"""
        for field in ['created_at', 'last_used']:
            if field in data and data[field]:
                data[field] = datetime.fromisoformat(data[field])
        return WalletInfo(**data)
    
    def _deserialize_credentials(self, data: Dict[str, Any]) -> WalletCredentials:
        """Deserialize credentials from JSON"""
        for field in ['last_rotation']:
            if field in data and data[field]:
                data[field] = datetime.fromisoformat(data[field])
        return WalletCredentials(**data)
    
    def _deserialize_transaction(self, data: Dict[str, Any]) -> TransactionResult:
        """Deserialize transaction from JSON"""
        for field in ['created_at', 'confirmed_at']:
            if field in data and data[field]:
                data[field] = datetime.fromisoformat(data[field])
        return TransactionResult(**data)
    
    async def _save_data_registry(self):
        """Save wallets, credentials, and transactions to disk"""
        try:
            # Save wallets
            wallets_data = {}
            for wallet_id, wallet_info in self.wallets.items():
                wallet_dict = asdict(wallet_info)
                for field in ['created_at', 'last_used']:
                    if wallet_dict.get(field):
                        wallet_dict[field] = wallet_dict[field].isoformat()
                wallets_data[wallet_id] = wallet_dict
            
            wallets_file = self.wallets_dir / "wallets_registry.json"
            async with aiofiles.open(wallets_file, "w") as f:
                await f.write(json.dumps(wallets_data, indent=2))
            
            # Save credentials (encrypted in production)
            credentials_data = {}
            for wallet_id, credentials in self.credentials.items():
                cred_dict = asdict(credentials)
                for field in ['last_rotation']:
                    if cred_dict.get(field):
                        cred_dict[field] = cred_dict[field].isoformat()
                credentials_data[wallet_id] = cred_dict
            
            credentials_file = self.wallets_dir / "credentials_registry.json"
            async with aiofiles.open(credentials_file, "w") as f:
                await f.write(json.dumps(credentials_data, indent=2))
            
            # Save transactions
            all_transactions = {**self.pending_transactions, **self.completed_transactions}
            transactions_data = {}
            for tx_id, transaction in all_transactions.items():
                tx_dict = asdict(transaction)
                for field in ['created_at', 'confirmed_at']:
                    if tx_dict.get(field):
                        tx_dict[field] = tx_dict[field].isoformat()
                transactions_data[tx_id] = tx_dict
            
            transactions_file = self.transactions_dir / "transactions_registry.json"
            async with aiofiles.open(transactions_file, "w") as f:
                await f.write(json.dumps(transactions_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving data registry: {e}")
    
    async def register_wallet(self, wallet_id: str, wallet_type: WalletType, 
                            role: WalletRole, address: str, public_key: str,
                            credentials: Optional[WalletCredentials] = None,
                            metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Register a new wallet"""
        try:
            logger.info(f"Registering wallet: {wallet_id} ({wallet_type})")
            
            # Check if wallet already exists
            if wallet_id in self.wallets:
                logger.warning(f"Wallet {wallet_id} already exists")
                return False
            
            # Create wallet info
            wallet_info = WalletInfo(
                wallet_id=wallet_id,
                wallet_type=wallet_type,
                role=role,
                address=address,
                public_key=public_key,
                status=WalletStatus.ACTIVE,
                integration_status=IntegrationStatus.DISCONNECTED,
                created_at=datetime.now(),
                metadata=metadata
            )
            
            # Store wallet
            self.wallets[wallet_id] = wallet_info
            
            # Store credentials if provided
            if credentials:
                self.credentials[wallet_id] = credentials
            
            # Save registry
            await self._save_data_registry()
            
            # Log wallet registration
            await self._log_wallet_event(wallet_id, "wallet_registered", {
                "wallet_type": wallet_type.value,
                "role": role.value,
                "address": address
            })
            
            logger.info(f"Registered wallet: {wallet_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering wallet: {e}")
            return False
    
    async def connect_wallet(self, wallet_id: str, session_data: Dict[str, Any]) -> bool:
        """Connect wallet for operations"""
        try:
            if wallet_id not in self.wallets:
                raise ValueError(f"Wallet {wallet_id} not found")
            
            wallet = self.wallets[wallet_id]
            
            # Check if wallet is active
            if wallet.status != WalletStatus.ACTIVE:
                raise ValueError(f"Wallet {wallet_id} is not active")
            
            # Check session limits
            if len(self.active_sessions) >= self.max_concurrent_sessions:
                raise RuntimeError("Maximum concurrent sessions reached")
            
            # Create session
            session_id = f"{wallet_id}_{int(time.time())}"
            self.active_sessions[session_id] = {
                "wallet_id": wallet_id,
                "created_at": datetime.now(),
                "last_activity": datetime.now(),
                "session_data": session_data
            }
            
            # Update wallet status
            wallet.integration_status = IntegrationStatus.CONNECTED
            wallet.last_used = datetime.now()
            
            # Save registry
            await self._save_data_registry()
            
            # Log connection
            await self._log_wallet_event(wallet_id, "wallet_connected", {
                "session_id": session_id,
                "session_data": session_data
            })
            
            logger.info(f"Connected wallet: {wallet_id} (session: {session_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting wallet: {e}")
            return False
    
    async def disconnect_wallet(self, wallet_id: str, session_id: Optional[str] = None) -> bool:
        """Disconnect wallet"""
        try:
            if wallet_id not in self.wallets:
                return False
            
            # Remove session(s)
            if session_id:
                if session_id in self.active_sessions:
                    del self.active_sessions[session_id]
            else:
                # Remove all sessions for this wallet
                sessions_to_remove = [sid for sid, session in self.active_sessions.items() 
                                    if session["wallet_id"] == wallet_id]
                for sid in sessions_to_remove:
                    del self.active_sessions[sid]
            
            # Update wallet status
            wallet = self.wallets[wallet_id]
            if not any(session["wallet_id"] == wallet_id for session in self.active_sessions.values()):
                wallet.integration_status = IntegrationStatus.DISCONNECTED
            
            # Save registry
            await self._save_data_registry()
            
            # Log disconnection
            await self._log_wallet_event(wallet_id, "wallet_disconnected", {
                "session_id": session_id
            })
            
            logger.info(f"Disconnected wallet: {wallet_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting wallet: {e}")
            return False
    
    async def execute_transaction(self, request: TransactionRequest) -> TransactionResult:
        """Execute a transaction using wallet"""
        try:
            logger.info(f"Executing transaction: {request.transaction_type} for wallet {request.wallet_id}")
            
            # Validate wallet
            if request.wallet_id not in self.wallets:
                raise ValueError(f"Wallet {request.wallet_id} not found")
            
            wallet = self.wallets[request.wallet_id]
            
            # Check wallet status
            if wallet.status != WalletStatus.ACTIVE:
                raise ValueError(f"Wallet {request.wallet_id} is not active")
            
            if wallet.integration_status != IntegrationStatus.CONNECTED:
                raise ValueError(f"Wallet {request.wallet_id} is not connected")
            
            # Generate transaction ID
            transaction_id = await self._generate_transaction_id(request)
            
            # Create transaction result
            transaction_result = TransactionResult(
                transaction_id=transaction_id,
                wallet_id=request.wallet_id,
                created_at=datetime.now()
            )
            
            # Execute based on wallet type
            if wallet.wallet_type == WalletType.SOFTWARE:
                await self._execute_software_transaction(request, transaction_result)
            elif wallet.wallet_type == WalletType.HARDWARE:
                await self._execute_hardware_transaction(request, transaction_result)
            elif wallet.wallet_type == WalletType.MULTISIG:
                await self._execute_multisig_transaction(request, transaction_result)
            elif wallet.wallet_type == WalletType.TRON_NATIVE:
                await self._execute_tron_native_transaction(request, transaction_result)
            elif wallet.wallet_type == WalletType.EXTERNAL:
                await self._execute_external_transaction(request, transaction_result)
            else:
                raise ValueError(f"Unsupported wallet type: {wallet.wallet_type}")
            
            # Store transaction
            if transaction_result.status == "pending":
                self.pending_transactions[transaction_id] = transaction_result
            else:
                self.completed_transactions[transaction_id] = transaction_result
            
            # Update wallet last used
            wallet.last_used = datetime.now()
            
            # Save registry
            await self._save_data_registry()
            
            # Log transaction
            await self._log_transaction_event(transaction_id, "transaction_executed", {
                "wallet_id": request.wallet_id,
                "transaction_type": request.transaction_type,
                "amount": request.amount,
                "recipient_address": request.recipient_address,
                "status": transaction_result.status
            })
            
            logger.info(f"Executed transaction: {transaction_id} -> {transaction_result.txid}")
            return transaction_result
            
        except Exception as e:
            logger.error(f"Error executing transaction: {e}")
            raise
    
    async def _execute_software_transaction(self, request: TransactionRequest, 
                                          result: TransactionResult):
        """Execute transaction using software wallet"""
        try:
            # In production, this would integrate with the actual wallet software
            # For now, we'll simulate the transaction
            
            # Simulate transaction processing
            await asyncio.sleep(1)  # Simulate processing time
            
            # Generate mock transaction ID
            result.txid = f"tx_{int(time.time())}_{hashlib.sha256(request.wallet_id.encode()).hexdigest()[:16]}"
            result.status = "confirmed"
            result.confirmed_at = datetime.now()
            result.fee_paid = 0.1  # Mock fee
            
            logger.info(f"Software transaction executed: {result.txid}")
            
        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            logger.error(f"Software transaction failed: {e}")
    
    async def _execute_hardware_transaction(self, request: TransactionRequest, 
                                          result: TransactionResult):
        """Execute transaction using hardware wallet"""
        try:
            # In production, this would integrate with hardware wallet APIs
            # For now, we'll simulate the transaction
            
            # Simulate hardware wallet interaction
            await asyncio.sleep(2)  # Simulate hardware processing time
            
            # Generate mock transaction ID
            result.txid = f"hw_tx_{int(time.time())}_{hashlib.sha256(request.wallet_id.encode()).hexdigest()[:16]}"
            result.status = "confirmed"
            result.confirmed_at = datetime.now()
            result.fee_paid = 0.15  # Mock fee (slightly higher for hardware)
            
            logger.info(f"Hardware transaction executed: {result.txid}")
            
        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            logger.error(f"Hardware transaction failed: {e}")
    
    async def _execute_multisig_transaction(self, request: TransactionRequest, 
                                          result: TransactionResult):
        """Execute transaction using multisig wallet"""
        try:
            # In production, this would handle multisig coordination
            # For now, we'll simulate the transaction
            
            # Simulate multisig coordination
            await asyncio.sleep(3)  # Simulate multisig processing time
            
            # Generate mock transaction ID
            result.txid = f"ms_tx_{int(time.time())}_{hashlib.sha256(request.wallet_id.encode()).hexdigest()[:16]}"
            result.status = "confirmed"
            result.confirmed_at = datetime.now()
            result.fee_paid = 0.2  # Mock fee (higher for multisig)
            
            logger.info(f"Multisig transaction executed: {result.txid}")
            
        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            logger.error(f"Multisig transaction failed: {e}")
    
    async def _execute_tron_native_transaction(self, request: TransactionRequest, 
                                             result: TransactionResult):
        """Execute transaction using TRON native wallet"""
        try:
            # In production, this would use TRON native APIs
            # For now, we'll simulate the transaction
            
            # Simulate TRON native processing
            await asyncio.sleep(1.5)  # Simulate processing time
            
            # Generate mock transaction ID
            result.txid = f"tr_tx_{int(time.time())}_{hashlib.sha256(request.wallet_id.encode()).hexdigest()[:16]}"
            result.status = "confirmed"
            result.confirmed_at = datetime.now()
            result.fee_paid = 0.12  # Mock fee
            
            logger.info(f"TRON native transaction executed: {result.txid}")
            
        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            logger.error(f"TRON native transaction failed: {e}")
    
    async def _execute_external_transaction(self, request: TransactionRequest, 
                                          result: TransactionResult):
        """Execute transaction using external wallet integration"""
        try:
            # In production, this would integrate with external wallet APIs
            # For now, we'll simulate the transaction
            
            # Simulate external API interaction
            await asyncio.sleep(2.5)  # Simulate external processing time
            
            # Generate mock transaction ID
            result.txid = f"ext_tx_{int(time.time())}_{hashlib.sha256(request.wallet_id.encode()).hexdigest()[:16]}"
            result.status = "confirmed"
            result.confirmed_at = datetime.now()
            result.fee_paid = 0.18  # Mock fee (higher for external)
            
            logger.info(f"External transaction executed: {result.txid}")
            
        except Exception as e:
            result.status = "failed"
            result.error_message = str(e)
            logger.error(f"External transaction failed: {e}")
    
    async def _generate_transaction_id(self, request: TransactionRequest) -> str:
        """Generate unique transaction ID"""
        timestamp = int(time.time())
        wallet_hash = hashlib.sha256(request.wallet_id.encode()).hexdigest()[:8]
        amount_hash = hashlib.sha256(str(request.amount).encode()).hexdigest()[:4]
        
        return f"tx_{timestamp}_{wallet_hash}_{amount_hash}"
    
    async def get_wallet_balance(self, wallet_id: str) -> Dict[str, Any]:
        """Get wallet balance information"""
        try:
            if wallet_id not in self.wallets:
                raise ValueError(f"Wallet {wallet_id} not found")
            
            wallet = self.wallets[wallet_id]
            
            # In production, this would fetch real balance data
            # For now, we'll return mock data
            
            return {
                "wallet_id": wallet_id,
                "address": wallet.address,
                "balance_trx": wallet.balance_trx,
                "balance_usdt": wallet.balance_usdt,
                "energy_available": wallet.energy_available,
                "bandwidth_available": wallet.bandwidth_available,
                "frozen_balance": wallet.frozen_balance,
                "delegated_energy": wallet.delegated_energy,
                "delegated_bandwidth": wallet.delegated_bandwidth,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting wallet balance: {e}")
            return {"error": str(e)}
    
    async def list_wallets(self, role: Optional[WalletRole] = None, 
                          status: Optional[WalletStatus] = None) -> List[Dict[str, Any]]:
        """List wallets with optional filters"""
        try:
            filtered_wallets = []
            
            for wallet_id, wallet in self.wallets.items():
                if role and wallet.role != role:
                    continue
                if status and wallet.status != status:
                    continue
                
                filtered_wallets.append({
                    "wallet_id": wallet.wallet_id,
                    "wallet_type": wallet.wallet_type.value,
                    "role": wallet.role.value,
                    "address": wallet.address,
                    "status": wallet.status.value,
                    "integration_status": wallet.integration_status.value,
                    "created_at": wallet.created_at.isoformat(),
                    "last_used": wallet.last_used.isoformat() if wallet.last_used else None,
                    "balance_trx": wallet.balance_trx,
                    "balance_usdt": wallet.balance_usdt
                })
            
            # Sort by creation time (newest first)
            filtered_wallets.sort(key=lambda x: x["created_at"], reverse=True)
            
            return filtered_wallets
            
        except Exception as e:
            logger.error(f"Error listing wallets: {e}")
            return []
    
    async def get_transaction_history(self, wallet_id: str, 
                                    limit: int = 100) -> List[Dict[str, Any]]:
        """Get transaction history for wallet"""
        try:
            all_transactions = {**self.pending_transactions, **self.completed_transactions}
            
            wallet_transactions = []
            for tx_id, transaction in all_transactions.items():
                if transaction.wallet_id == wallet_id:
                    wallet_transactions.append({
                        "transaction_id": transaction.transaction_id,
                        "wallet_id": transaction.wallet_id,
                        "txid": transaction.txid,
                        "status": transaction.status,
                        "fee_paid": transaction.fee_paid,
                        "created_at": transaction.created_at.isoformat(),
                        "confirmed_at": transaction.confirmed_at.isoformat() if transaction.confirmed_at else None,
                        "error_message": transaction.error_message
                    })
            
            # Sort by creation time (newest first)
            wallet_transactions.sort(key=lambda x: x["created_at"], reverse=True)
            
            # Limit results
            return wallet_transactions[:limit]
            
        except Exception as e:
            logger.error(f"Error getting transaction history: {e}")
            return []
    
    async def _monitor_wallets(self):
        """Monitor wallet status and health"""
        try:
            while True:
                for wallet_id, wallet in self.wallets.items():
                    # Check for inactive wallets
                    if wallet.last_used:
                        time_since_use = datetime.now() - wallet.last_used
                        if time_since_use > timedelta(days=30):
                            if wallet.status == WalletStatus.ACTIVE:
                                wallet.status = WalletStatus.INACTIVE
                                await self._log_wallet_event(wallet_id, "wallet_inactive", {
                                    "days_since_use": time_since_use.days
                                })
                
                # Save registry
                await self._save_data_registry()
                
                # Wait before next check
                await asyncio.sleep(3600)  # Check every hour
                
        except asyncio.CancelledError:
            logger.info("Wallet monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in wallet monitoring: {e}")
    
    async def _monitor_transactions(self):
        """Monitor pending transactions"""
        try:
            while True:
                for tx_id, transaction in list(self.pending_transactions.items()):
                    if transaction.txid:
                        # In production, check actual transaction status
                        # For now, we'll simulate confirmation after some time
                        time_since_creation = datetime.now() - transaction.created_at
                        if time_since_creation > timedelta(minutes=5):
                            transaction.status = "confirmed"
                            transaction.confirmed_at = datetime.now()
                            
                            # Move to completed
                            self.completed_transactions[tx_id] = transaction
                            del self.pending_transactions[tx_id]
                            
                            await self._log_transaction_event(tx_id, "transaction_confirmed", {
                                "txid": transaction.txid,
                                "wallet_id": transaction.wallet_id
                            })
                
                # Save registry
                await self._save_data_registry()
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
        except asyncio.CancelledError:
            logger.info("Transaction monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in transaction monitoring: {e}")
    
    async def _cleanup_sessions(self):
        """Clean up expired sessions"""
        try:
            while True:
                now = datetime.now()
                expired_sessions = []
                
                for session_id, session in self.active_sessions.items():
                    time_since_activity = now - session["last_activity"]
                    if time_since_activity > timedelta(minutes=self.session_timeout_minutes):
                        expired_sessions.append(session_id)
                
                # Remove expired sessions
                for session_id in expired_sessions:
                    wallet_id = self.active_sessions[session_id]["wallet_id"]
                    del self.active_sessions[session_id]
                    
                    # Update wallet status if no active sessions
                    if not any(s["wallet_id"] == wallet_id for s in self.active_sessions.values()):
                        if wallet_id in self.wallets:
                            self.wallets[wallet_id].integration_status = IntegrationStatus.DISCONNECTED
                    
                    await self._log_wallet_event(wallet_id, "session_expired", {
                        "session_id": session_id
                    })
                
                if expired_sessions:
                    await self._save_data_registry()
                    logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
                # Wait before next cleanup
                await asyncio.sleep(300)  # Check every 5 minutes
                
        except asyncio.CancelledError:
            logger.info("Session cleanup cancelled")
        except Exception as e:
            logger.error(f"Error in session cleanup: {e}")
    
    async def _check_key_rotation(self):
        """Check for wallets that need key rotation"""
        try:
            while True:
                rotation_needed = []
                
                for wallet_id, credentials in self.credentials.items():
                    if credentials.last_rotation:
                        time_since_rotation = datetime.now() - credentials.last_rotation
                        if time_since_rotation > timedelta(days=self.key_rotation_interval_days):
                            rotation_needed.append(wallet_id)
                
                # Log rotation alerts
                for wallet_id in rotation_needed:
                    await self._log_wallet_event(wallet_id, "key_rotation_needed", {
                        "days_since_rotation": (datetime.now() - self.credentials[wallet_id].last_rotation).days
                    })
                
                # Wait before next check
                await asyncio.sleep(86400)  # Check every day
                
        except asyncio.CancelledError:
            logger.info("Key rotation check cancelled")
        except Exception as e:
            logger.error(f"Error in key rotation check: {e}")
    
    async def _log_wallet_event(self, wallet_id: str, event_type: str, data: Dict[str, Any]):
        """Log wallet event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "wallet_id": wallet_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"wallet_events_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging wallet event: {e}")
    
    async def _log_transaction_event(self, transaction_id: str, event_type: str, data: Dict[str, Any]):
        """Log transaction event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "transaction_id": transaction_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"transaction_events_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging transaction event: {e}")

# Global instance
wallet_integration_manager = WalletIntegrationManager()

# Convenience functions for external use
async def register_wallet(wallet_id: str, wallet_type: WalletType, role: WalletRole, 
                        address: str, public_key: str, credentials: Optional[WalletCredentials] = None) -> bool:
    """Register a new wallet"""
    return await wallet_integration_manager.register_wallet(wallet_id, wallet_type, role, address, public_key, credentials)

async def connect_wallet(wallet_id: str, session_data: Dict[str, Any]) -> bool:
    """Connect wallet for operations"""
    return await wallet_integration_manager.connect_wallet(wallet_id, session_data)

async def execute_transaction(request: TransactionRequest) -> TransactionResult:
    """Execute a transaction using wallet"""
    return await wallet_integration_manager.execute_transaction(request)

async def get_wallet_balance(wallet_id: str) -> Dict[str, Any]:
    """Get wallet balance information"""
    return await wallet_integration_manager.get_wallet_balance(wallet_id)

async def list_wallets(role: Optional[WalletRole] = None, status: Optional[WalletStatus] = None) -> List[Dict[str, Any]]:
    """List wallets"""
    return await wallet_integration_manager.list_wallets(role, status)

async def get_transaction_history(wallet_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get transaction history for wallet"""
    return await wallet_integration_manager.get_transaction_history(wallet_id, limit)

if __name__ == "__main__":
    # Example usage
    async def main():
        # Register a software wallet
        software_wallet_registered = await register_wallet(
            wallet_id="wallet_001",
            wallet_type=WalletType.SOFTWARE,
            role=WalletRole.NODE_OPERATOR,
            address="TYourTRONAddressHere123456789",
            public_key="public_key_here"
        )
        print(f"Software wallet registered: {software_wallet_registered}")
        
        # Register a hardware wallet
        hardware_wallet_registered = await register_wallet(
            wallet_id="wallet_002",
            wallet_type=WalletType.HARDWARE,
            role=WalletRole.USER_CLIENT,
            address="TYourHardwareAddressHere123456789",
            public_key="hardware_public_key_here"
        )
        print(f"Hardware wallet registered: {hardware_wallet_registered}")
        
        # Connect wallets
        software_connected = await connect_wallet("wallet_001", {"session_type": "admin"})
        hardware_connected = await connect_wallet("wallet_002", {"session_type": "user"})
        print(f"Software wallet connected: {software_connected}")
        print(f"Hardware wallet connected: {hardware_connected}")
        
        # Execute transactions
        trx_request = TransactionRequest(
            wallet_id="wallet_001",
            transaction_type="TRX_TRANSFER",
            recipient_address="TRecipientAddressHere123456789",
            amount=10.0,
            token_type="TRX"
        )
        
        trx_result = await execute_transaction(trx_request)
        print(f"TRX transaction result: {trx_result.txid}")
        
        usdt_request = TransactionRequest(
            wallet_id="wallet_002",
            transaction_type="USDT_TRANSFER",
            recipient_address="TRecipientAddressHere123456789",
            amount=100.0,
            token_type="USDT"
        )
        
        usdt_result = await execute_transaction(usdt_request)
        print(f"USDT transaction result: {usdt_result.txid}")
        
        # Get wallet balances
        software_balance = await get_wallet_balance("wallet_001")
        hardware_balance = await get_wallet_balance("wallet_002")
        print(f"Software wallet balance: {software_balance}")
        print(f"Hardware wallet balance: {hardware_balance}")
        
        # List wallets
        all_wallets = await list_wallets()
        print(f"All wallets: {len(all_wallets)}")
        
        # Get transaction history
        software_history = await get_transaction_history("wallet_001")
        print(f"Software wallet history: {len(software_history)} transactions")
    
    asyncio.run(main())
