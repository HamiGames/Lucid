"""
LUCID Payment Systems - USDT Manager Service
USDT-TRC20 token management and operations
Distroless container: lucid-usdt-manager:latest
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
import httpx
from tronpy import Tron
from tronpy.keys import PrivateKey
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

class TokenStatus(Enum):
    """Token status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class TransactionStatus(Enum):
    """Transaction status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TokenInfo:
    """Token information"""
    token_id: str
    symbol: str
    name: str
    contract_address: str
    decimals: int
    total_supply: int
    status: TokenStatus
    created_at: datetime
    last_updated: datetime

@dataclass
class TokenBalance:
    """Token balance information"""
    wallet_address: str
    token_address: str
    balance: float
    balance_raw: int
    last_updated: datetime

@dataclass
class TokenTransaction:
    """Token transaction"""
    transaction_id: str
    wallet_address: str
    token_address: str
    txid: str
    from_address: str
    to_address: str
    amount: float
    amount_raw: int
    fee: float
    status: TransactionStatus
    block_number: int
    timestamp: int
    created_at: datetime
    raw_data: Optional[Dict[str, Any]] = None

class TokenTransferRequest(BaseModel):
    """Token transfer request"""
    from_address: str = Field(..., description="Sender address")
    to_address: str = Field(..., description="Recipient address")
    amount: float = Field(..., gt=0, description="Amount to transfer")
    private_key: str = Field(..., description="Private key for signing")
    token_address: str = Field(..., description="Token contract address")

class TokenTransferResponse(BaseModel):
    """Token transfer response"""
    transaction_id: str
    txid: str
    status: str
    amount: float
    from_address: str
    to_address: str
    fee: float
    created_at: str

class TokenBalanceRequest(BaseModel):
    """Token balance request"""
    wallet_address: str = Field(..., description="Wallet address")
    token_address: str = Field(..., description="Token contract address")

class TokenBalanceResponse(BaseModel):
    """Token balance response"""
    wallet_address: str
    token_address: str
    balance: float
    balance_raw: int
    symbol: str
    decimals: int
    last_updated: str

class USDTManagerService:
    """USDT-TRC20 manager service"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # TRON client configuration - from environment variables
        self.tron_client_url = os.getenv("TRON_CLIENT_URL", os.getenv("USDT_MANAGER_TRON_CLIENT_URL", "http://lucid-tron-client:8091"))
        
        # Initialize TRON client
        self._initialize_tron_client()
        
        # Data storage - from environment variables
        data_base = os.getenv("DATA_DIRECTORY", os.getenv("TRON_DATA_DIR", "/data/payment-systems"))
        self.data_dir = Path(data_base) / "usdt-manager"
        self.tokens_dir = self.data_dir / "tokens"
        self.transactions_dir = self.data_dir / "transactions"
        self.balances_dir = self.data_dir / "balances"
        self.logs_dir = self.data_dir / "logs"
        
        # Ensure directories exist
        for directory in [self.tokens_dir, self.transactions_dir, self.balances_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Token tracking
        self.tokens: Dict[str, TokenInfo] = {}
        self.token_balances: Dict[str, TokenBalance] = {}
        self.token_transactions: Dict[str, List[TokenTransaction]] = {}
        
        # USDT contract address - from environment variable
        self.usdt_contract_address = os.getenv("USDT_CONTRACT_ADDRESS", os.getenv("USDT_MANAGER_CONTRACT_ADDRESS", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"))
        
        # Load existing data
        asyncio.create_task(self._load_existing_data())
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_tokens())
        asyncio.create_task(self._monitor_balances())
        asyncio.create_task(self._cleanup_old_data())
        
        logger.info("USDTManagerService initialized")
    
    def _initialize_tron_client(self):
        """Initialize TRON client connection"""
        try:
            # In production, this would connect to the TRON client service
            # For now, we'll use direct TRON connection
            self.tron = Tron()
            logger.info("TRON client initialized for USDT management")
        except Exception as e:
            logger.error(f"Failed to initialize TRON client: {e}")
            raise
    
    async def _load_existing_data(self):
        """Load existing data from disk"""
        try:
            # Load tokens
            tokens_file = self.tokens_dir / "tokens_registry.json"
            if tokens_file.exists():
                async with aiofiles.open(tokens_file, "r") as f:
                    data = await f.read()
                    tokens_data = json.loads(data)
                    
                    for token_id, token_data in tokens_data.items():
                        # Convert datetime strings back to datetime objects
                        for field in ['created_at', 'last_updated']:
                            if field in token_data and token_data[field]:
                                token_data[field] = datetime.fromisoformat(token_data[field])
                        
                        token_info = TokenInfo(**token_data)
                        self.tokens[token_id] = token_info
                    
                logger.info(f"Loaded {len(self.tokens)} existing tokens")
            
            # Load balances
            balances_file = self.balances_dir / "balances_registry.json"
            if balances_file.exists():
                async with aiofiles.open(balances_file, "r") as f:
                    data = await f.read()
                    balances_data = json.loads(data)
                    
                    for balance_key, balance_data in balances_data.items():
                        # Convert datetime strings back to datetime objects
                        if 'last_updated' in balance_data and balance_data['last_updated']:
                            balance_data['last_updated'] = datetime.fromisoformat(balance_data['last_updated'])
                        
                        token_balance = TokenBalance(**balance_data)
                        self.token_balances[balance_key] = token_balance
                    
                logger.info(f"Loaded {len(self.token_balances)} existing balances")
                
        except Exception as e:
            logger.error(f"Error loading existing data: {e}")
    
    async def _save_tokens_registry(self):
        """Save tokens registry to disk"""
        try:
            tokens_data = {}
            for token_id, token_info in self.tokens.items():
                # Convert to dict and handle datetime serialization
                token_dict = asdict(token_info)
                for field in ['created_at', 'last_updated']:
                    if token_dict.get(field):
                        token_dict[field] = token_dict[field].isoformat()
                tokens_data[token_id] = token_dict
            
            tokens_file = self.tokens_dir / "tokens_registry.json"
            async with aiofiles.open(tokens_file, "w") as f:
                await f.write(json.dumps(tokens_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving tokens registry: {e}")
    
    async def _save_balances_registry(self):
        """Save balances registry to disk"""
        try:
            balances_data = {}
            for balance_key, token_balance in self.token_balances.items():
                # Convert to dict and handle datetime serialization
                balance_dict = asdict(token_balance)
                if balance_dict.get('last_updated'):
                    balance_dict['last_updated'] = balance_dict['last_updated'].isoformat()
                balances_data[balance_key] = balance_dict
            
            balances_file = self.balances_dir / "balances_registry.json"
            async with aiofiles.open(balances_file, "w") as f:
                await f.write(json.dumps(balances_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving balances registry: {e}")
    
    async def register_token(self, contract_address: str, symbol: str, name: str) -> TokenInfo:
        """Register a new token"""
        try:
            logger.info(f"Registering token: {symbol} at {contract_address}")
            
            # Get token contract
            contract = self.tron.get_contract(contract_address)
            
            # Get token info
            decimals = contract.functions.decimals()
            total_supply = contract.functions.totalSupply()
            
            # Generate token ID
            token_id = f"token_{int(time.time())}_{hashlib.sha256(contract_address.encode()).hexdigest()[:8]}"
            
            # Create token info
            token_info = TokenInfo(
                token_id=token_id,
                symbol=symbol,
                name=name,
                contract_address=contract_address,
                decimals=decimals,
                total_supply=total_supply,
                status=TokenStatus.ACTIVE,
                created_at=datetime.now(),
                last_updated=datetime.now()
            )
            
            # Store token
            self.tokens[token_id] = token_info
            
            # Save registry
            await self._save_tokens_registry()
            
            # Log token registration
            await self._log_token_event(token_id, "token_registered", {
                "symbol": symbol,
                "name": name,
                "contract_address": contract_address
            })
            
            logger.info(f"Registered token: {token_id} -> {symbol}")
            return token_info
            
        except Exception as e:
            logger.error(f"Error registering token: {e}")
            raise
    
    async def get_token_balance(self, request: TokenBalanceRequest) -> TokenBalanceResponse:
        """Get token balance for wallet"""
        try:
            logger.info(f"Getting token balance: {request.wallet_address} -> {request.token_address}")
            
            # Get token contract
            contract = self.tron.get_contract(request.token_address)
            
            # Get balance
            balance_raw = contract.functions.balanceOf(request.wallet_address)
            
            # Get token decimals
            decimals = contract.functions.decimals()
            balance = balance_raw / (10 ** decimals)
            
            # Get token symbol
            symbol = contract.functions.symbol()
            
            # Create balance key
            balance_key = f"{request.wallet_address}_{request.token_address}"
            
            # Create token balance
            token_balance = TokenBalance(
                wallet_address=request.wallet_address,
                token_address=request.token_address,
                balance=balance,
                balance_raw=balance_raw,
                last_updated=datetime.now()
            )
            
            # Store balance
            self.token_balances[balance_key] = token_balance
            
            # Save registry
            await self._save_balances_registry()
            
            logger.info(f"Token balance: {balance} {symbol}")
            
            return TokenBalanceResponse(
                wallet_address=request.wallet_address,
                token_address=request.token_address,
                balance=balance,
                balance_raw=balance_raw,
                symbol=symbol,
                decimals=decimals,
                last_updated=token_balance.last_updated.isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error getting token balance: {e}")
            raise
    
    async def transfer_token(self, request: TokenTransferRequest) -> TokenTransferResponse:
        """Transfer tokens"""
        try:
            logger.info(f"Transferring tokens: {request.amount} from {request.from_address} to {request.to_address}")
            
            # Get token contract
            contract = self.tron.get_contract(request.token_address)
            
            # Get token decimals
            decimals = contract.functions.decimals()
            amount_raw = int(request.amount * (10 ** decimals))
            
            # Create transfer transaction
            private_key = PrivateKey(bytes.fromhex(request.private_key))
            
            # Build transaction
            txn = contract.functions.transfer(
                request.to_address,
                amount_raw
            ).with_owner(request.from_address).build().sign(private_key)
            
            # Broadcast transaction
            result = txn.broadcast()
            
            if result.get("result"):
                txid = result["txid"]
                
                # Generate transaction ID
                transaction_id = f"tx_{int(time.time())}_{hashlib.sha256(txid.encode()).hexdigest()[:16]}"
                
                # Create transaction record
                token_transaction = TokenTransaction(
                    transaction_id=transaction_id,
                    wallet_address=request.from_address,
                    token_address=request.token_address,
                    txid=txid,
                    from_address=request.from_address,
                    to_address=request.to_address,
                    amount=request.amount,
                    amount_raw=amount_raw,
                    fee=0.0,  # Will be updated when confirmed
                    status=TransactionStatus.PENDING,
                    block_number=0,
                    timestamp=int(time.time() * 1000),
                    created_at=datetime.now(),
                    raw_data=result
                )
                
                # Store transaction
                if request.from_address not in self.token_transactions:
                    self.token_transactions[request.from_address] = []
                self.token_transactions[request.from_address].append(token_transaction)
                
                # Log transaction
                await self._log_token_event(transaction_id, "token_transfer", {
                    "from_address": request.from_address,
                    "to_address": request.to_address,
                    "amount": request.amount,
                    "txid": txid
                })
                
                logger.info(f"Token transfer initiated: {transaction_id} -> {txid}")
                
                return TokenTransferResponse(
                    transaction_id=transaction_id,
                    txid=txid,
                    status=TransactionStatus.PENDING.value,
                    amount=request.amount,
                    from_address=request.from_address,
                    to_address=request.to_address,
                    fee=0.0,
                    created_at=token_transaction.created_at.isoformat()
                )
            else:
                raise RuntimeError(f"Token transfer failed: {result}")
                
        except Exception as e:
            logger.error(f"Error transferring tokens: {e}")
            raise
    
    async def get_token_info(self, token_address: str) -> Optional[TokenInfo]:
        """Get token information"""
        try:
            # Find token by contract address
            for token_info in self.tokens.values():
                if token_info.contract_address == token_address:
                    return token_info
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting token info: {e}")
            return None
    
    async def list_tokens(self, status: Optional[TokenStatus] = None) -> List[TokenInfo]:
        """List tokens with optional status filter"""
        try:
            tokens_list = []
            
            for token_info in self.tokens.values():
                if status is None or token_info.status == status:
                    tokens_list.append(token_info)
            
            return tokens_list
            
        except Exception as e:
            logger.error(f"Error listing tokens: {e}")
            return []
    
    async def _monitor_tokens(self):
        """Monitor token status and updates"""
        try:
            while True:
                for token_id, token_info in self.tokens.items():
                    try:
                        # Update token info from contract
                        contract = self.tron.get_contract(token_info.contract_address)
                        
                        # Get updated info
                        total_supply = contract.functions.totalSupply()
                        
                        # Update token info
                        token_info.total_supply = total_supply
                        token_info.last_updated = datetime.now()
                        
                    except Exception as e:
                        logger.error(f"Error monitoring token {token_id}: {e}")
                
                # Save registry
                await self._save_tokens_registry()
                
                # Wait before next check
                await asyncio.sleep(3600)  # Check every hour
                
        except asyncio.CancelledError:
            logger.info("Token monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in token monitoring: {e}")
    
    async def _monitor_balances(self):
        """Monitor token balances"""
        try:
            while True:
                for balance_key, token_balance in self.token_balances.items():
                    try:
                        # Update balance from contract
                        contract = self.tron.get_contract(token_balance.token_address)
                        balance_raw = contract.functions.balanceOf(token_balance.wallet_address)
                        decimals = contract.functions.decimals()
                        balance = balance_raw / (10 ** decimals)
                        
                        # Update balance
                        token_balance.balance = balance
                        token_balance.balance_raw = balance_raw
                        token_balance.last_updated = datetime.now()
                        
                    except Exception as e:
                        logger.error(f"Error monitoring balance {balance_key}: {e}")
                
                # Save registry
                await self._save_balances_registry()
                
                # Wait before next check
                await asyncio.sleep(1800)  # Check every 30 minutes
                
        except asyncio.CancelledError:
            logger.info("Balance monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in balance monitoring: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old data"""
        try:
            while True:
                cutoff_date = datetime.now() - timedelta(days=30)
                
                # Clean up old transactions
                for wallet_address, transactions in self.token_transactions.items():
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
    
    async def _log_token_event(self, token_id: str, event_type: str, data: Dict[str, Any]):
        """Log token event"""
        try:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "token_id": token_id,
                "event_type": event_type,
                "data": data
            }
            
            log_file = self.logs_dir / f"token_events_{datetime.now().strftime('%Y%m%d')}.log"
            async with aiofiles.open(log_file, "a") as f:
                await f.write(json.dumps(log_entry) + "\n")
                
        except Exception as e:
            logger.error(f"Error logging token event: {e}")
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        try:
            total_tokens = len(self.tokens)
            active_tokens = len([t for t in self.tokens.values() if t.status == TokenStatus.ACTIVE])
            total_balances = len(self.token_balances)
            
            return {
                "total_tokens": total_tokens,
                "active_tokens": active_tokens,
                "total_balances": total_balances,
                "token_status": {
                    status.value: len([t for t in self.tokens.values() if t.status == status])
                    for status in TokenStatus
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            return {"error": str(e)}

# Global instance
usdt_manager_service = USDTManagerService()

# Convenience functions for external use
async def register_token(contract_address: str, symbol: str, name: str) -> TokenInfo:
    """Register a new token"""
    return await usdt_manager_service.register_token(contract_address, symbol, name)

async def get_token_balance(request: TokenBalanceRequest) -> TokenBalanceResponse:
    """Get token balance"""
    return await usdt_manager_service.get_token_balance(request)

async def transfer_token(request: TokenTransferRequest) -> TokenTransferResponse:
    """Transfer tokens"""
    return await usdt_manager_service.transfer_token(request)

async def get_token_info(token_address: str) -> Optional[TokenInfo]:
    """Get token information"""
    return await usdt_manager_service.get_token_info(token_address)

async def list_tokens(status: Optional[TokenStatus] = None) -> List[TokenInfo]:
    """List tokens"""
    return await usdt_manager_service.list_tokens(status)

async def get_service_stats() -> Dict[str, Any]:
    """Get service statistics"""
    return await usdt_manager_service.get_service_stats()

if __name__ == "__main__":
    # Example usage
    async def main():
        try:
            # Register USDT token - use environment variable for contract address
            usdt_contract = os.getenv("USDT_CONTRACT_ADDRESS", os.getenv("USDT_MANAGER_CONTRACT_ADDRESS", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"))
            test_address = os.getenv("TRON_TEST_ADDRESS", "TYourTRONAddressHere123456789")
            
            usdt_token = await register_token(
                usdt_contract,
                "USDT",
                "Tether USD"
            )
            print(f"Registered token: {usdt_token}")
            
            # Get token balance
            balance_request = TokenBalanceRequest(
                wallet_address=test_address,
                token_address=usdt_contract
            )
            balance = await get_token_balance(balance_request)
            print(f"Token balance: {balance}")
            
            # List tokens
            tokens = await list_tokens()
            print(f"Total tokens: {len(tokens)}")
            
            # Get service stats
            stats = await get_service_stats()
            print(f"Service stats: {stats}")
            
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main())
