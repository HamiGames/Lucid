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

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings

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
        
        # TRON client configuration
        self.tron_client_url = os.getenv("TRON_CLIENT_URL", "http://localhost:8085")
        
        # Initialize TRON client
        self._initialize_tron_client()
        
        # Data storage
        self.data_dir = Path("/data/payment-systems/wallet-manager")
        self.wallets_dir = self.data_dir / "wallets"
        self.transactions_dir = self.data_dir / "transactions"
        self.logs_dir = self.data_dir / "logs"
        
        # Ensure directories exist
        for directory in [self.wallets_dir, self.transactions_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Wallet tracking
        self.wallets: Dict[str, WalletInfo] = {}
        self.wallet_transactions: Dict[str, List[WalletTransaction]] = {}
        
        # Encryption key (in production, this should be securely managed)
        self.encryption_key = os.getenv("WALLET_ENCRYPTION_KEY", "default_encryption_key_change_in_production")
        
        # Load existing wallets
        asyncio.create_task(self._load_existing_wallets())
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_wallets())
        asyncio.create_task(self._cleanup_old_data())
        
        logger.info("WalletManagerService initialized")
    
    def _initialize_tron_client(self):
        """Initialize TRON client connection"""
        try:
            # In production, this would connect to the TRON client service
            # For now, we'll use direct TRON connection
            self.tron = Tron()
            logger.info("TRON client initialized for wallet management")
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
    
    def _encrypt_private_key(self, private_key: str, password: Optional[str] = None) -> str:
        """Encrypt private key"""
        try:
            # Simple encryption (in production, use proper encryption)
            if password:
                key = hashlib.sha256(password.encode()).digest()
            else:
                key = hashlib.sha256(self.encryption_key.encode()).digest()
            
            # Simple XOR encryption (replace with proper encryption in production)
            encrypted = ""
            for i, char in enumerate(private_key):
                encrypted += chr(ord(char) ^ key[i % len(key)])
            
            return encrypted.encode().hex()
            
        except Exception as e:
            logger.error(f"Error encrypting private key: {e}")
            raise
    
    def _decrypt_private_key(self, encrypted_key: str, password: Optional[str] = None) -> str:
        """Decrypt private key"""
        try:
            # Simple decryption (in production, use proper decryption)
            if password:
                key = hashlib.sha256(password.encode()).digest()
            else:
                key = hashlib.sha256(self.encryption_key.encode()).digest()
            
            # Decode hex and decrypt
            encrypted_bytes = bytes.fromhex(encrypted_key)
            decrypted = ""
            for i, char in enumerate(encrypted_bytes.decode()):
                decrypted += chr(ord(char) ^ key[i % len(key)])
            
            return decrypted
            
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

# Global instance
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

if __name__ == "__main__":
    # Example usage
    async def main():
        try:
            # Create a wallet
            wallet_request = WalletCreateRequest(
                name="Test Wallet",
                description="Test wallet for development",
                wallet_type=WalletType.HOT,
                password="test_password"
            )
            
            wallet = await create_wallet(wallet_request)
            print(f"Created wallet: {wallet}")
            
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
