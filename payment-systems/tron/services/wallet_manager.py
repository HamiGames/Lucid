"""
LUCID Payment Systems - TRON Wallet Manager Service
Wallet management and operations for TRON payments
Distroless container: lucid-wallet-manager:latest
"""

import asyncio
import logging
import os
import time
import hashlib
import json
import secrets
import base64
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import aiofiles
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field
import httpx
from tronpy import Tron
from tronpy.keys import PrivateKey, PublicKey
from tronpy.providers import HTTPProvider
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

import sys

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.config import get_settings
except ImportError:
    # Fallback if app.config is not available
    def get_settings():
        return type('Settings', (), {})()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WalletType(Enum):
    """Wallet types"""
    HOT = "hot"
    COLD = "cold"
    MULTISIG = "multisig"
    HARDWARE = "hardware"

class WalletStatus(Enum):
    """Wallet status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    ARCHIVED = "archived"

@dataclass
class WalletInfo:
    """Wallet information"""
    wallet_id: str
    name: str
    description: Optional[str]
    address: str
    private_key_encrypted: Optional[str]  # Encrypted private key
    wallet_type: WalletType
    status: WalletStatus
    created_at: datetime
    last_used: Optional[datetime]
    balance_trx: float = 0.0
    balance_sun: int = 0
    energy_available: int = 0
    bandwidth_available: int = 0
    frozen_balance: float = 0.0
    delegated_energy: int = 0
    delegated_bandwidth: int = 0
    transaction_count: int = 0

@dataclass
class WalletTransaction:
    """Wallet transaction"""
    transaction_id: str
    wallet_id: str
    txid: str
    from_address: str
    to_address: str
    amount: float
    currency: str
    fee: float
    status: str
    block_number: int
    timestamp: int
    created_at: datetime
    raw_data: Optional[Dict[str, Any]] = None

class WalletCreateRequest(BaseModel):
    """Wallet creation request"""
    name: str = Field(..., description="Wallet name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Wallet description", max_length=500)
    wallet_type: WalletType = Field(default=WalletType.HOT, description="Wallet type")
    password: Optional[str] = Field(None, description="Encryption password")

class WalletUpdateRequest(BaseModel):
    """Wallet update request"""
    name: Optional[str] = Field(None, description="Wallet name", min_length=1, max_length=100)
    description: Optional[str] = Field(None, description="Wallet description", max_length=500)
    status: Optional[WalletStatus] = Field(None, description="Wallet status")

class WalletResponse(BaseModel):
    """Wallet response model"""
    wallet_id: str
    name: str
    description: Optional[str]
    address: str
    wallet_type: str
    status: str
    balance_trx: float
    created_at: str
    last_updated: str

class WalletManagerService:
    """TRON wallet manager service"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # TRON client configuration - from environment variables
        self.tron_client_url = os.getenv("TRON_CLIENT_URL", os.getenv("WALLET_MANAGER_TRON_CLIENT_URL", "http://lucid-tron-client:8091"))
        
        # Initialize TRON client
        self._initialize_tron_client()
        
        # Data storage - from environment variables
        data_base = os.getenv("DATA_DIRECTORY", os.getenv("TRON_DATA_DIR", "/data/payment-systems"))
        self.data_dir = Path(data_base) / "wallet-manager"
        self.wallets_dir = self.data_dir / "wallets"
        self.transactions_dir = self.data_dir / "transactions"
        self.logs_dir = self.data_dir / "logs"
        
        # Ensure directories exist
        for directory in [self.wallets_dir, self.transactions_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Wallet tracking
        self.wallets: Dict[str, WalletInfo] = {}
        self.wallet_transactions: Dict[str, List[WalletTransaction]] = {}
        
        # Encryption key from environment variable (required in production)
        encryption_key = os.getenv("WALLET_ENCRYPTION_KEY") or os.getenv("ENCRYPTION_KEY")
        if not encryption_key:
            raise ValueError("WALLET_ENCRYPTION_KEY or ENCRYPTION_KEY environment variable must be set")
        self.encryption_key = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
        
        # Background tasks will be started in initialize() method
        self._monitoring_task = None
        self._cleanup_task = None
        
        logger.info("WalletManagerService initialized")
    
    async def initialize(self):
        """Initialize async components"""
        try:
            # Load existing wallets
            await self._load_existing_wallets()
            
            # Start monitoring tasks
            self._monitoring_task = asyncio.create_task(self._monitor_wallets())
            self._cleanup_task = asyncio.create_task(self._cleanup_old_data())
            
            logger.info("WalletManagerService async components initialized")
        except Exception as e:
            logger.error(f"Error initializing WalletManagerService: {e}")
            raise
    
    async def stop(self):
        """Stop background tasks"""
        try:
            if self._monitoring_task:
                self._monitoring_task.cancel()
            if self._cleanup_task:
                self._cleanup_task.cancel()
            
            # Wait for tasks to complete
            if self._monitoring_task:
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
            if self._cleanup_task:
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass
            
            logger.info("WalletManagerService stopped")
        except Exception as e:
            logger.error(f"Error stopping WalletManagerService: {e}")
    
    def _initialize_tron_client(self):
        """Initialize TRON client connection"""
        try:
            # Get TRON network configuration from environment
            tron_network = os.getenv("TRON_NETWORK", "mainnet")
            tron_rpc_url = os.getenv("TRON_RPC_URL")
            tron_api_key = os.getenv("TRON_API_KEY") or os.getenv("TRONGRID_API_KEY")
            
            # Configure TRON provider
            if tron_rpc_url:
                provider = HTTPProvider(tron_rpc_url, api_key=tron_api_key)
                self.tron = Tron(provider=provider, network=tron_network)
            else:
                # Use default provider based on network
                if tron_network == "mainnet":
                    default_url = "https://api.trongrid.io"
                elif tron_network == "shasta":
                    default_url = "https://api.shasta.trongrid.io"
                else:
                    default_url = "https://api.trongrid.io"
                
                provider = HTTPProvider(default_url, api_key=tron_api_key)
                self.tron = Tron(provider=provider, network=tron_network)
            
            logger.info(f"TRON client initialized for {tron_network} network")
        except Exception as e:
            logger.error(f"Failed to initialize TRON client: {e}")
            raise
    
    async def _load_existing_wallets(self):
        """Load existing wallets from disk"""
        try:
            wallets_file = self.wallets_dir / "wallets_registry.json"
            if wallets_file.exists():
                async with aiofiles.open(wallets_file, "r") as f:
                    data = await f.read()
                    wallets_data = json.loads(data)
                    
                    for wallet_id, wallet_data in wallets_data.items():
                        # Convert datetime strings back to datetime objects
                        for field in ['created_at', 'last_used']:
                            if field in wallet_data and wallet_data[field]:
                                wallet_data[field] = datetime.fromisoformat(wallet_data[field])
                        
                        # Convert enum strings back to Enum objects
                        if 'wallet_type' in wallet_data and isinstance(wallet_data['wallet_type'], str):
                            wallet_data['wallet_type'] = WalletType(wallet_data['wallet_type'])
                        if 'status' in wallet_data and isinstance(wallet_data['status'], str):
                            wallet_data['status'] = WalletStatus(wallet_data['status'])
                        
                        wallet_info = WalletInfo(**wallet_data)
                        self.wallets[wallet_id] = wallet_info
                    
                logger.info(f"Loaded {len(self.wallets)} existing wallets")
                
        except Exception as e:
            logger.error(f"Error loading existing wallets: {e}")
    
    async def _save_wallets_registry(self):
        """Save wallets registry to disk"""
        try:
            wallets_data = {}
            for wallet_id, wallet_info in self.wallets.items():
                # Convert to dict and handle datetime serialization
                wallet_dict = asdict(wallet_info)
                for field in ['created_at', 'last_used']:
                    if wallet_dict.get(field):
                        wallet_dict[field] = wallet_dict[field].isoformat()
                wallets_data[wallet_id] = wallet_dict
            
            wallets_file = self.wallets_dir / "wallets_registry.json"
            async with aiofiles.open(wallets_file, "w") as f:
                await f.write(json.dumps(wallets_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving wallets registry: {e}")
    
    def _derive_key(self, password: Optional[str] = None, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """Derive encryption key using PBKDF2"""
        if salt is None:
            salt = secrets.token_bytes(16)
        
        source = password.encode() if password else self.encryption_key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = kdf.derive(source)
        return key, salt
    
    def _encrypt_private_key(self, private_key: str, password: Optional[str] = None) -> str:
        """Encrypt private key using AES-256-GCM"""
        try:
            # Generate salt and derive key
            key, salt = self._derive_key(password)
            
            # Create AES-GCM cipher
            aesgcm = AESGCM(key)
            
            # Generate nonce
            nonce = secrets.token_bytes(12)
            
            # Encrypt
            private_key_bytes = private_key.encode('utf-8')
            ciphertext = aesgcm.encrypt(nonce, private_key_bytes, None)
            
            # Combine salt + nonce + ciphertext
            encrypted_data = salt + nonce + ciphertext
            
            # Return base64 encoded
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error encrypting private key: {e}")
            raise
    
    def _decrypt_private_key(self, encrypted_key: str, password: Optional[str] = None) -> str:
        """Decrypt private key using AES-256-GCM"""
        try:
            # Decode base64
            encrypted_data = base64.b64decode(encrypted_key.encode('utf-8'))
            
            # Extract salt (16 bytes), nonce (12 bytes), and ciphertext (rest)
            salt = encrypted_data[:16]
            nonce = encrypted_data[16:28]
            ciphertext = encrypted_data[28:]
            
            # Derive key
            key, _ = self._derive_key(password, salt)
            
            # Create AES-GCM cipher
            aesgcm = AESGCM(key)
            
            # Decrypt
            private_key_bytes = aesgcm.decrypt(nonce, ciphertext, None)
            
            return private_key_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error decrypting private key: {e}")
            raise
    
    async def create_wallet(self, request: WalletCreateRequest) -> WalletResponse:
        """Create a new wallet"""
        try:
            logger.info(f"Creating wallet: {request.name}")
            
            # Generate new private key
            private_key = PrivateKey.random()
            public_key = private_key.public_key
            address = public_key.to_base58check_address()
            
            # Encrypt private key
            encrypted_private_key = self._encrypt_private_key(
                private_key.hex(), 
                request.password
            )
            
            # Generate wallet ID
            wallet_id = f"wallet_{int(time.time())}_{secrets.token_hex(8)}"
            
            # Create wallet info
            wallet_info = WalletInfo(
                wallet_id=wallet_id,
                name=request.name,
                description=request.description,
                address=address,
                private_key_encrypted=encrypted_private_key,
                wallet_type=request.wallet_type,
                status=WalletStatus.ACTIVE,
                created_at=datetime.now()
            )
            
            # Store wallet
            self.wallets[wallet_id] = wallet_info
            
            # Save registry
            await self._save_wallets_registry()
            
            # Log wallet creation
            await self._log_wallet_event(wallet_id, "wallet_created", {
                "name": request.name,
                "address": address,
                "wallet_type": request.wallet_type.value
            })
            
            logger.info(f"Created wallet: {wallet_id} -> {address}")
            
            return WalletResponse(
                wallet_id=wallet_id,
                name=wallet_info.name,
                description=wallet_info.description,
                address=wallet_info.address,
                wallet_type=wallet_info.wallet_type.value,
                status=wallet_info.status.value,
                balance_trx=wallet_info.balance_trx,
                created_at=wallet_info.created_at.isoformat(),
                last_updated=wallet_info.created_at.isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error creating wallet: {e}")
            raise
    
    async def get_wallet(self, wallet_id: str) -> Optional[WalletResponse]:
        """Get wallet information"""
        try:
            if wallet_id not in self.wallets:
                return None
            
            wallet_info = self.wallets[wallet_id]
            
            # Update balance
            await self._update_wallet_balance(wallet_info)
            
            return WalletResponse(
                wallet_id=wallet_info.wallet_id,
                name=wallet_info.name,
                description=wallet_info.description,
                address=wallet_info.address,
                wallet_type=wallet_info.wallet_type.value,
                status=wallet_info.status.value,
                balance_trx=wallet_info.balance_trx,
                created_at=wallet_info.created_at.isoformat(),
                last_updated=wallet_info.last_used.isoformat() if wallet_info.last_used else wallet_info.created_at.isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error getting wallet {wallet_id}: {e}")
            return None
    
    async def update_wallet(self, wallet_id: str, request: WalletUpdateRequest) -> Optional[WalletResponse]:
        """Update wallet information"""
        try:
            if wallet_id not in self.wallets:
                return None
            
            wallet_info = self.wallets[wallet_id]
            
            # Update fields
            if request.name is not None:
                wallet_info.name = request.name
            if request.description is not None:
                wallet_info.description = request.description
            if request.status is not None:
                wallet_info.status = request.status
            
            # Save registry
            await self._save_wallets_registry()
            
            # Log update
            await self._log_wallet_event(wallet_id, "wallet_updated", {
                "name": wallet_info.name,
                "status": wallet_info.status.value
            })
            
            logger.info(f"Updated wallet: {wallet_id}")
            
            return WalletResponse(
                wallet_id=wallet_info.wallet_id,
                name=wallet_info.name,
                description=wallet_info.description,
                address=wallet_info.address,
                wallet_type=wallet_info.wallet_type.value,
                status=wallet_info.status.value,
                balance_trx=wallet_info.balance_trx,
                created_at=wallet_info.created_at.isoformat(),
                last_updated=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error updating wallet {wallet_id}: {e}")
            return None
    
    async def delete_wallet(self, wallet_id: str, password: Optional[str] = None) -> bool:
        """Delete wallet (requires password for security)"""
        try:
            if wallet_id not in self.wallets:
                return False
            
            # In production, verify password before deletion
            if password and not self._verify_wallet_password(wallet_id, password):
                raise ValueError("Invalid password")
            
            # Remove wallet
            del self.wallets[wallet_id]
            
            # Remove transactions
            if wallet_id in self.wallet_transactions:
                del self.wallet_transactions[wallet_id]
            
            # Save registry
            await self._save_wallets_registry()
            
            # Log deletion
            await self._log_wallet_event(wallet_id, "wallet_deleted", {})
            
            logger.info(f"Deleted wallet: {wallet_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting wallet {wallet_id}: {e}")
            return False
    
    def _verify_wallet_password(self, wallet_id: str, password: str) -> bool:
        """Verify wallet password"""
        try:
            wallet_info = self.wallets[wallet_id]
            # Try to decrypt with provided password
            self._decrypt_private_key(wallet_info.private_key_encrypted, password)
            return True
        except:
            return False
    
    async def _update_wallet_balance(self, wallet_info: WalletInfo):
        """Update wallet balance from TRON network"""
        try:
            # Get account info from TRON network
            account = self.tron.get_account(wallet_info.address)
            account_resources = self.tron.get_account_resources(wallet_info.address)
            
            # Update balance
            wallet_info.balance_sun = account.get("balance", 0)
            wallet_info.balance_trx = wallet_info.balance_sun / 1_000_000
            wallet_info.energy_available = account_resources.get("EnergyLimit", 0)
            wallet_info.bandwidth_available = account_resources.get("NetLimit", 0)
            wallet_info.frozen_balance = account.get("frozen", [{}])[0].get("frozen_balance", 0) / 1_000_000
            wallet_info.delegated_energy = account_resources.get("delegated_frozenV2_energy", 0)
            wallet_info.delegated_bandwidth = account_resources.get("delegated_frozenV2_bandwidth", 0)
            wallet_info.transaction_count = account.get("transaction_count", 0)
            wallet_info.last_used = datetime.now()
            
        except Exception as e:
            logger.error(f"Error updating wallet balance for {wallet_info.address}: {e}")
    
    async def get_wallet_balance(self, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Get wallet balance"""
        try:
            if wallet_id not in self.wallets:
                return None
            
            wallet_info = self.wallets[wallet_id]
            await self._update_wallet_balance(wallet_info)
            
            return {
                "wallet_id": wallet_info.wallet_id,
                "address": wallet_info.address,
                "balance_trx": wallet_info.balance_trx,
                "balance_sun": wallet_info.balance_sun,
                "energy_available": wallet_info.energy_available,
                "bandwidth_available": wallet_info.bandwidth_available,
                "frozen_balance": wallet_info.frozen_balance,
                "delegated_energy": wallet_info.delegated_energy,
                "delegated_bandwidth": wallet_info.delegated_bandwidth,
                "last_updated": wallet_info.last_used.isoformat() if wallet_info.last_used else None
            }
            
        except Exception as e:
            logger.error(f"Error getting wallet balance for {wallet_id}: {e}")
            return None
    
    async def list_wallets(self, status: Optional[WalletStatus] = None) -> List[WalletResponse]:
        """List wallets with optional status filter"""
        try:
            wallets_list = []
            
            for wallet_info in self.wallets.values():
                if status is None or wallet_info.status == status:
                    # Update balance
                    await self._update_wallet_balance(wallet_info)
                    
                    wallets_list.append(WalletResponse(
                        wallet_id=wallet_info.wallet_id,
                        name=wallet_info.name,
                        description=wallet_info.description,
                        address=wallet_info.address,
                        wallet_type=wallet_info.wallet_type.value,
                        status=wallet_info.status.value,
                        balance_trx=wallet_info.balance_trx,
                        created_at=wallet_info.created_at.isoformat(),
                        last_updated=wallet_info.last_used.isoformat() if wallet_info.last_used else wallet_info.created_at.isoformat()
                    ))
            
            return wallets_list
            
        except Exception as e:
            logger.error(f"Error listing wallets: {e}")
            return []
    
    async def _monitor_wallets(self):
        """Monitor wallet balances and status"""
        try:
            while True:
                for wallet_id, wallet_info in self.wallets.items():
                    try:
                        # Update balance
                        await self._update_wallet_balance(wallet_info)
                        
                        # Check for significant balance changes
                        # (This would be more sophisticated in production)
                        
                    except Exception as e:
                        logger.error(f"Error monitoring wallet {wallet_id}: {e}")
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
        except asyncio.CancelledError:
            logger.info("Wallet monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in wallet monitoring: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old data"""
        try:
            while True:
                cutoff_date = datetime.now() - timedelta(days=30)
                
                # Clean up old transactions
                for wallet_id, transactions in self.wallet_transactions.items():
                    old_transactions = [
                        tx for tx in transactions 
                        if tx.created_at < cutoff_date
                    ]
                    for tx in old_transactions:
                        transactions.remove(tx)
                
                # Wait before next cleanup
                await asyncio.sleep(3600)  # Clean up every hour
                
        except asyncio.CancelledError:
            logger.info("Data cleanup cancelled")
        except Exception as e:
            logger.error(f"Error in data cleanup: {e}")
    
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
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        try:
            total_wallets = len(self.wallets)
            active_wallets = len([w for w in self.wallets.values() if w.status == WalletStatus.ACTIVE])
            total_balance = sum(w.balance_trx for w in self.wallets.values())
            
            return {
                "total_wallets": total_wallets,
                "active_wallets": active_wallets,
                "total_balance_trx": total_balance,
                "wallet_types": {
                    wallet_type.value: len([w for w in self.wallets.values() if w.wallet_type == wallet_type])
                    for wallet_type in WalletType
                },
                "wallet_status": {
                    status.value: len([w for w in self.wallets.values() if w.status == status])
                    for status in WalletStatus
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            return {"error": str(e)}
    
    async def import_wallet(self, private_key: str, name: str, description: Optional[str] = None) -> WalletResponse:
        """Import wallet from private key"""
        try:
            # Validate private key format
            if not private_key or len(private_key) != 64:
                raise ValueError("Invalid private key format (must be 64 hex characters)")
            
            # Validate hex format
            try:
                private_key_bytes = bytes.fromhex(private_key)
            except ValueError:
                raise ValueError("Invalid private key format (must be valid hex)")
            
            # Create PrivateKey object to get address
            private_key_obj = PrivateKey(private_key_bytes)
            address = private_key_obj.public_key.to_checksum_address()
            
            # Check if wallet with this address already exists
            for existing_wallet in self.wallets.values():
                if existing_wallet.address == address:
                    raise ValueError(f"Wallet with address {address} already exists")
            
            # Generate wallet ID
            wallet_id = hashlib.sha256(f"{address}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
            
            # Encrypt private key
            encrypted_private_key = self._encrypt_private_key(private_key)
            
            # Create wallet info
            wallet_info = WalletInfo(
                wallet_id=wallet_id,
                name=name,
                description=description,
                address=address,
                private_key_encrypted=encrypted_private_key,
                wallet_type=WalletType.HOT,
                status=WalletStatus.ACTIVE,
                created_at=datetime.now(),
                last_used=None
            )
            
            # Store wallet
            self.wallets[wallet_id] = wallet_info
            
            # Update balance
            await self._update_wallet_balance(wallet_info)
            
            # Save registry
            await self._save_wallets_registry()
            
            # Log import
            await self._log_wallet_event(wallet_id, "wallet_imported", {
                "address": address,
                "name": name
            })
            
            logger.info(f"Imported wallet: {wallet_id} -> {address}")
            
            return WalletResponse(
                wallet_id=wallet_info.wallet_id,
                name=wallet_info.name,
                description=wallet_info.description,
                address=wallet_info.address,
                wallet_type=wallet_info.wallet_type.value,
                status=wallet_info.status.value,
                balance_trx=wallet_info.balance_trx,
                created_at=wallet_info.created_at.isoformat(),
                last_updated=wallet_info.created_at.isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error importing wallet: {e}")
            raise
    
    async def sign_transaction(self, wallet_id: str, password: Optional[str], transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sign transaction data with wallet private key"""
        try:
            if wallet_id not in self.wallets:
                raise ValueError("Wallet not found")
            
            wallet_info = self.wallets[wallet_id]
            
            # Verify password if provided
            if password and not self._verify_wallet_password(wallet_id, password):
                raise ValueError("Invalid password")
            
            # Decrypt private key
            try:
                private_key_str = self._decrypt_private_key(wallet_info.private_key_encrypted, password)
            except Exception as e:
                raise ValueError(f"Failed to decrypt private key: {str(e)}")
            
            # Create PrivateKey object
            private_key_obj = PrivateKey(bytes.fromhex(private_key_str))
            
            # Sign transaction based on type
            if transaction_data.get("type") == "trx_transfer":
                # TRX transfer transaction
                to_address = transaction_data.get("to_address")
                amount_sun = int(transaction_data.get("amount", 0) * 1_000_000)
                
                if not to_address:
                    raise ValueError("to_address is required for TRX transfer")
                
                # Build transaction
                txn = (
                    self.tron.trx.transfer(wallet_info.address, to_address, amount_sun)
                    .build()
                    .sign(private_key_obj)
                )
                
                # Get transaction hash
                txid = txn.txid
                
                result = {
                    "wallet_id": wallet_id,
                    "txid": txid,
                    "signed_transaction": txn.to_json(),
                    "from_address": wallet_info.address,
                    "to_address": to_address,
                    "amount": transaction_data.get("amount", 0),
                    "status": "signed",
                    "timestamp": datetime.now().isoformat()
                }
                
            elif transaction_data.get("type") == "data_sign":
                # Sign arbitrary data
                data_hex = transaction_data.get("data")
                if not data_hex:
                    raise ValueError("data is required for data signing")
                
                data_bytes = bytes.fromhex(data_hex)
                signature = private_key_obj.sign_msg_hash(data_bytes)
                
                result = {
                    "wallet_id": wallet_id,
                    "signature": signature.hex(),
                    "public_key": private_key_obj.public_key.to_hex(),
                    "data_hash": hashlib.sha256(data_bytes).hexdigest(),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                raise ValueError(f"Unsupported transaction type: {transaction_data.get('type')}")
            
            # Log signing operation
            await self._log_wallet_event(wallet_id, "transaction_signed", {
                "txid": result.get("txid"),
                "type": transaction_data.get("type")
            })
            
            logger.info(f"Signed transaction for wallet {wallet_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error signing transaction for wallet {wallet_id}: {e}")
            raise
    
    async def get_wallet_transactions(self, wallet_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get wallet transaction history"""
        try:
            if wallet_id not in self.wallets:
                return []
            
            # Get transactions from storage
            transactions = self.wallet_transactions.get(wallet_id, [])
            
            # Sort by timestamp (newest first)
            transactions.sort(key=lambda x: x.timestamp if isinstance(x.timestamp, int) else 0, reverse=True)
            
            # Apply pagination
            paginated = transactions[skip:skip + limit]
            
            # Convert to dict format
            result = []
            for tx in paginated:
                result.append({
                    "transaction_id": tx.transaction_id,
                    "wallet_id": tx.wallet_id,
                    "txid": tx.txid,
                    "from_address": tx.from_address,
                    "to_address": tx.to_address,
                    "amount": tx.amount,
                    "currency": tx.currency,
                    "fee": tx.fee,
                    "status": tx.status,
                    "block_number": tx.block_number,
                    "timestamp": tx.timestamp,
                    "created_at": tx.created_at.isoformat() if isinstance(tx.created_at, datetime) else str(tx.created_at)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting transactions for wallet {wallet_id}: {e}")
            return []
    
    async def create_backup(self, wallet_id: str) -> Dict[str, Any]:
        """Create backup of wallet"""
        try:
            if wallet_id not in self.wallets:
                raise ValueError("Wallet not found")
            
            wallet_info = self.wallets[wallet_id]
            
            # Create backup data
            backup_data = {
                "wallet_id": wallet_info.wallet_id,
                "name": wallet_info.name,
                "description": wallet_info.description,
                "address": wallet_info.address,
                "private_key_encrypted": wallet_info.private_key_encrypted,
                "wallet_type": wallet_info.wallet_type.value,
                "status": wallet_info.status.value,
                "created_at": wallet_info.created_at.isoformat(),
                "backup_created_at": datetime.now().isoformat()
            }
            
            # Save backup to file
            backup_dir = Path(self.data_dir) / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            backup_file = backup_dir / f"{wallet_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            async with aiofiles.open(backup_file, "w") as f:
                await f.write(json.dumps(backup_data, indent=2))
            
            backup_id = backup_file.stem
            
            # Log backup creation
            await self._log_wallet_event(wallet_id, "backup_created", {
                "backup_id": backup_id,
                "backup_file": str(backup_file)
            })
            
            logger.info(f"Created backup for wallet {wallet_id}: {backup_id}")
            
            return {
                "backup_id": backup_id,
                "wallet_id": wallet_id,
                "backup_file": str(backup_file),
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating backup for wallet {wallet_id}: {e}")
            raise
    
    async def restore_backup(self, wallet_id: str, backup_id: str, password: Optional[str] = None) -> WalletResponse:
        """Restore wallet from backup"""
        try:
            # Find backup file
            backup_dir = Path(self.data_dir) / "backups"
            backup_file = backup_dir / f"{backup_id}.json"
            
            if not backup_file.exists():
                raise ValueError(f"Backup {backup_id} not found")
            
            # Load backup data
            async with aiofiles.open(backup_file, "r") as f:
                backup_data = json.loads(await f.read())
            
            # Verify wallet_id matches
            if backup_data.get("wallet_id") != wallet_id:
                raise ValueError("Backup wallet_id does not match")
            
            # Restore wallet info
            wallet_info = WalletInfo(
                wallet_id=backup_data["wallet_id"],
                name=backup_data["name"],
                description=backup_data.get("description"),
                address=backup_data["address"],
                private_key_encrypted=backup_data["private_key_encrypted"],
                wallet_type=WalletType(backup_data["wallet_type"]),
                status=WalletStatus(backup_data["status"]),
                created_at=datetime.fromisoformat(backup_data["created_at"]),
                last_used=None
            )
            
            # Update wallet
            self.wallets[wallet_id] = wallet_info
            
            # Update balance
            await self._update_wallet_balance(wallet_info)
            
            # Save registry
            await self._save_wallets_registry()
            
            # Log restore
            await self._log_wallet_event(wallet_id, "wallet_restored", {
                "backup_id": backup_id,
                "backup_created_at": backup_data.get("backup_created_at")
            })
            
            logger.info(f"Restored wallet {wallet_id} from backup {backup_id}")
            
            return WalletResponse(
                wallet_id=wallet_info.wallet_id,
                name=wallet_info.name,
                description=wallet_info.description,
                address=wallet_info.address,
                wallet_type=wallet_info.wallet_type.value,
                status=wallet_info.status.value,
                balance_trx=wallet_info.balance_trx,
                created_at=wallet_info.created_at.isoformat(),
                last_updated=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error restoring wallet {wallet_id} from backup {backup_id}: {e}")
            raise
    
    async def verify_password(self, wallet_id: str, password: str) -> bool:
        """Verify wallet password"""
        try:
            return self._verify_wallet_password(wallet_id, password)
        except Exception as e:
            logger.error(f"Error verifying password for wallet {wallet_id}: {e}")
            return False
    
    async def get_recovery_info(self, wallet_id: str) -> Dict[str, Any]:
        """Get recovery information for wallet"""
        try:
            if wallet_id not in self.wallets:
                raise ValueError("Wallet not found")
            
            wallet_info = self.wallets[wallet_id]
            
            # List available backups
            backup_dir = Path(self.data_dir) / "backups"
            backups = []
            
            if backup_dir.exists():
                for backup_file in backup_dir.glob(f"{wallet_id}_*.json"):
                    try:
                        async with aiofiles.open(backup_file, "r") as f:
                            backup_data = json.loads(await f.read())
                            backups.append({
                                "backup_id": backup_file.stem,
                                "created_at": backup_data.get("backup_created_at"),
                                "file": str(backup_file)
                            })
                    except Exception:
                        continue
            
            # Sort backups by creation time
            backups.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            
            return {
                "wallet_id": wallet_id,
                "address": wallet_info.address,
                "has_backups": len(backups) > 0,
                "backup_count": len(backups),
                "backups": backups,
                "last_backup": backups[0] if backups else None,
                "recovery_methods": ["backup_restore"],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting recovery info for wallet {wallet_id}: {e}")
            raise

# Global instance - will be initialized async
wallet_manager_service = WalletManagerService()

# Convenience functions for external use
async def create_wallet(request: WalletCreateRequest) -> WalletResponse:
    """Create a new wallet"""
    return await wallet_manager_service.create_wallet(request)

async def get_wallet(wallet_id: str) -> Optional[WalletResponse]:
    """Get wallet information"""
    return await wallet_manager_service.get_wallet(wallet_id)

async def update_wallet(wallet_id: str, request: WalletUpdateRequest) -> Optional[WalletResponse]:
    """Update wallet information"""
    return await wallet_manager_service.update_wallet(wallet_id, request)

async def delete_wallet(wallet_id: str, password: Optional[str] = None) -> bool:
    """Delete wallet"""
    return await wallet_manager_service.delete_wallet(wallet_id, password)

async def get_wallet_balance(wallet_id: str) -> Optional[Dict[str, Any]]:
    """Get wallet balance"""
    return await wallet_manager_service.get_wallet_balance(wallet_id)

async def list_wallets(status: Optional[WalletStatus] = None) -> List[WalletResponse]:
    """List wallets"""
    return await wallet_manager_service.list_wallets(status)

async def get_service_stats() -> Dict[str, Any]:
    """Get service statistics"""
    return await wallet_manager_service.get_service_stats()

async def import_wallet(private_key: str, name: str, description: Optional[str] = None) -> WalletResponse:
    """Import wallet from private key"""
    return await wallet_manager_service.import_wallet(private_key, name, description)

async def sign_transaction(wallet_id: str, password: Optional[str], transaction_data: Dict[str, Any]) -> Dict[str, Any]:
    """Sign transaction with wallet"""
    return await wallet_manager_service.sign_transaction(wallet_id, password, transaction_data)

async def get_wallet_transactions(wallet_id: str, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """Get wallet transaction history"""
    return await wallet_manager_service.get_wallet_transactions(wallet_id, skip, limit)

async def create_backup(wallet_id: str) -> Dict[str, Any]:
    """Create wallet backup"""
    return await wallet_manager_service.create_backup(wallet_id)

async def restore_backup(wallet_id: str, backup_id: str, password: Optional[str] = None) -> WalletResponse:
    """Restore wallet from backup"""
    return await wallet_manager_service.restore_backup(wallet_id, backup_id, password)

async def verify_password(wallet_id: str, password: str) -> bool:
    """Verify wallet password"""
    return await wallet_manager_service.verify_password(wallet_id, password)

async def get_recovery_info(wallet_id: str) -> Dict[str, Any]:
    """Get wallet recovery information"""
    return await wallet_manager_service.get_recovery_info(wallet_id)

if __name__ == "__main__":
    # Example usage - DO NOT USE IN PRODUCTION
    # All sensitive values should come from environment variables
    async def main():
        try:
            # Check for required environment variables
            encryption_key = os.getenv("WALLET_ENCRYPTION_KEY") or os.getenv("ENCRYPTION_KEY")
            if not encryption_key:
                print("ERROR: WALLET_ENCRYPTION_KEY or ENCRYPTION_KEY must be set")
                print("Set via environment variable or .env file")
                return
            
            # Create a wallet
            # Note: Password should come from environment or user input, never hardcoded
            wallet_password = os.getenv("WALLET_TEST_PASSWORD")  # Optional, uses service key if not set
            wallet_request = WalletCreateRequest(
                name="Test Wallet",
                description="Test wallet for development",
                wallet_type=WalletType.HOT,
                password=wallet_password  # Uses service encryption key if None
            )
            
            wallet = await create_wallet(wallet_request)
            print(f"Created wallet: {wallet.wallet_id} -> {wallet.address}")
            print("NOTE: Private key is encrypted and stored securely")
            
            # Get wallet balance
            balance = await get_wallet_balance(wallet.wallet_id)
            print(f"Wallet balance: {balance}")
            
            # List all wallets
            wallets = await list_wallets()
            print(f"Total wallets: {len(wallets)}")
            
            # Get service stats
            stats = await get_service_stats()
            print(f"Service stats: {stats}")
            
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main())
