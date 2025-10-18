"""
LUCID Payment Systems - TRON Network Client Service
TRON network connectivity and transaction management
Distroless container: lucid-tron-client:latest
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

class NetworkStatus(Enum):
    """TRON network status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    SYNCING = "syncing"
    ERROR = "error"
    MAINTENANCE = "maintenance"

class TransactionType(Enum):
    """Transaction types"""
    TRX_TRANSFER = "trx_transfer"
    USDT_TRANSFER = "usdt_transfer"
    CONTRACT_CALL = "contract_call"
    FREEZE_BALANCE = "freeze_balance"
    UNFREEZE_BALANCE = "unfreeze_balance"
    VOTE_WITNESS = "vote_witness"
    DELEGATE_RESOURCE = "delegate_resource"
    UNDELEGATE_RESOURCE = "undelegate_resource"

@dataclass
class NetworkInfo:
    """TRON network information"""
    network_name: str
    network_id: str
    chain_id: str
    latest_block: int
    block_timestamp: int
    node_url: str
    status: NetworkStatus
    last_updated: datetime
    sync_progress: float = 0.0
    node_count: int = 0
    total_supply: int = 0
    total_transactions: int = 0

@dataclass
class TransactionInfo:
    """Transaction information"""
    txid: str
    block_number: int
    timestamp: int
    from_address: str
    to_address: str
    amount: int
    token_type: str
    fee: int
    energy_used: int
    bandwidth_used: int
    status: str
    raw_data: Optional[Dict[str, Any]] = None

@dataclass
class AccountInfo:
    """Account information"""
    address: str
    balance_trx: float
    balance_sun: int
    energy_available: int
    bandwidth_available: int
    frozen_balance: float
    delegated_energy: int
    delegated_bandwidth: int
    last_updated: datetime
    transaction_count: int = 0

class TronClientService:
    """TRON network client service for payment operations"""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Network configuration
        self.network = self.settings.TRON_NETWORK
        self.is_mainnet = self.network == "mainnet"
        self.node_url = self._resolve_endpoint()
        
        # Initialize TRON client
        self._initialize_tron_client()
        
        # Data storage
        self.data_dir = Path("/data/payment-systems/tron-client")
        self.network_dir = self.data_dir / "network"
        self.transactions_dir = self.data_dir / "transactions"
        self.accounts_dir = self.data_dir / "accounts"
        self.logs_dir = self.data_dir / "logs"
        
        # Ensure directories exist
        for directory in [self.network_dir, self.transactions_dir, self.accounts_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Network state
        self.network_info: Optional[NetworkInfo] = None
        self.connection_status = NetworkStatus.DISCONNECTED
        self.last_sync_time = None
        
        # Transaction tracking
        self.pending_transactions: Dict[str, TransactionInfo] = {}
        self.confirmed_transactions: Dict[str, TransactionInfo] = {}
        
        # Account cache
        self.account_cache: Dict[str, AccountInfo] = {}
        
        # Monitoring tasks
        self.monitoring_tasks = []
        
        # Start monitoring
        asyncio.create_task(self._start_monitoring())
        
        logger.info(f"TronClientService initialized: {self.network} -> {self.node_url}")
    
    def _resolve_endpoint(self) -> str:
        """Resolve TRON endpoint"""
        if self.settings.TRON_HTTP_ENDPOINT:
            return self.settings.TRON_HTTP_ENDPOINT
        
        if self.network.lower() == "shasta":
            return "https://api.shasta.trongrid.io"
        
        return "https://api.trongrid.io"
    
    def _initialize_tron_client(self):
        """Initialize TRON client with network configuration"""
        try:
            headers = {}
            if self.settings.TRONGRID_API_KEY:
                headers["TRON-PRO-API-KEY"] = self.settings.TRONGRID_API_KEY
            
            provider = HTTPProvider(
                self.node_url,
                client=httpx.Client(headers=headers, timeout=30)
            )
            self.tron = Tron(provider=provider)
            
            logger.info(f"TRON client connected to {self.network}")
        except Exception as e:
            logger.error(f"Failed to initialize TRON client: {e}")
            raise
    
    async def _start_monitoring(self):
        """Start network monitoring tasks"""
        try:
            # Start network monitoring
            self.monitoring_tasks.append(
                asyncio.create_task(self._monitor_network())
            )
            
            # Start transaction monitoring
            self.monitoring_tasks.append(
                asyncio.create_task(self._monitor_transactions())
            )
            
            # Start account monitoring
            self.monitoring_tasks.append(
                asyncio.create_task(self._monitor_accounts())
            )
            
            # Start cleanup tasks
            self.monitoring_tasks.append(
                asyncio.create_task(self._cleanup_old_data())
            )
            
            logger.info("Network monitoring started")
            
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}")
    
    async def get_network_info(self) -> NetworkInfo:
        """Get current network information"""
        try:
            # Get latest block
            latest_block = self.tron.get_latest_block()
            block_number = latest_block["block_header"]["raw_data"]["number"]
            block_timestamp = latest_block["block_header"]["raw_data"]["timestamp"]
            
            # Get network parameters
            network_params = self.tron.get_chain_parameters()
            
            # Create network info
            network_info = NetworkInfo(
                network_name=self.network,
                network_id=self.tron.chain_id,
                chain_id=hex(self.tron.chain_id),
                latest_block=block_number,
                block_timestamp=block_timestamp,
                node_url=self.node_url,
                status=NetworkStatus.CONNECTED,
                last_updated=datetime.now(),
                sync_progress=100.0,  # Assume synced
                node_count=len(self.tron.get_nodes()),
                total_supply=network_params.get("getTotalSupply", 0),
                total_transactions=network_params.get("getTotalTransactionCount", 0)
            )
            
            # Update connection status
            self.connection_status = NetworkStatus.CONNECTED
            self.network_info = network_info
            self.last_sync_time = datetime.now()
            
            # Save network info
            await self._save_network_info(network_info)
            
            logger.info(f"Network info updated: block {block_number}")
            return network_info
            
        except Exception as e:
            logger.error(f"Error getting network info: {e}")
            self.connection_status = NetworkStatus.ERROR
            raise
    
    async def get_account_info(self, address: str) -> AccountInfo:
        """Get account information"""
        try:
            # Check cache first
            if address in self.account_cache:
                cached_account = self.account_cache[address]
                # Return cached if less than 5 minutes old
                if datetime.now() - cached_account.last_updated < timedelta(minutes=5):
                    return cached_account
            
            # Get account from TRON network
            account = self.tron.get_account(address)
            
            # Get account resources
            account_resources = self.tron.get_account_resources(address)
            
            # Create account info
            account_info = AccountInfo(
                address=address,
                balance_trx=account.get("balance", 0) / 1_000_000,  # Convert sun to TRX
                balance_sun=account.get("balance", 0),
                energy_available=account_resources.get("EnergyLimit", 0),
                bandwidth_available=account_resources.get("NetLimit", 0),
                frozen_balance=account.get("frozen", [{}])[0].get("frozen_balance", 0) / 1_000_000,
                delegated_energy=account_resources.get("delegated_frozenV2_energy", 0),
                delegated_bandwidth=account_resources.get("delegated_frozenV2_bandwidth", 0),
                last_updated=datetime.now(),
                transaction_count=account.get("transaction_count", 0)
            )
            
            # Update cache
            self.account_cache[address] = account_info
            
            # Save account info
            await self._save_account_info(account_info)
            
            logger.info(f"Account info updated: {address}")
            return account_info
            
        except Exception as e:
            logger.error(f"Error getting account info for {address}: {e}")
            raise
    
    async def get_balance(self, address: str) -> float:
        """Get TRX balance for address"""
        try:
            account_info = await self.get_account_info(address)
            return account_info.balance_trx
        except Exception as e:
            logger.error(f"Error getting balance for {address}: {e}")
            raise
    
    async def get_transaction(self, txid: str) -> Optional[TransactionInfo]:
        """Get transaction information"""
        try:
            # Check cache first
            if txid in self.confirmed_transactions:
                return self.confirmed_transactions[txid]
            if txid in self.pending_transactions:
                return self.pending_transactions[txid]
            
            # Get transaction from TRON network
            tx_info = self.tron.get_transaction_info(txid)
            
            if not tx_info:
                return None
            
            # Parse transaction info
            transaction_info = TransactionInfo(
                txid=txid,
                block_number=tx_info.get("blockNumber", 0),
                timestamp=tx_info.get("blockTimeStamp", 0),
                from_address=tx_info.get("from", ""),
                to_address=tx_info.get("to", ""),
                amount=tx_info.get("amount", 0),
                token_type=tx_info.get("tokenType", "TRX"),
                fee=tx_info.get("fee", 0),
                energy_used=tx_info.get("energy_used", 0),
                bandwidth_used=tx_info.get("net_usage", 0),
                status=tx_info.get("result", "UNKNOWN"),
                raw_data=tx_info
            )
            
            # Cache transaction
            if transaction_info.status == "SUCCESS":
                self.confirmed_transactions[txid] = transaction_info
            else:
                self.pending_transactions[txid] = transaction_info
            
            # Save transaction info
            await self._save_transaction_info(transaction_info)
            
            logger.info(f"Transaction info retrieved: {txid}")
            return transaction_info
            
        except Exception as e:
            logger.error(f"Error getting transaction {txid}: {e}")
            return None
    
    async def broadcast_transaction(self, transaction_data: Dict[str, Any]) -> str:
        """Broadcast transaction to TRON network"""
        try:
            # Build transaction
            txn = self.tron.trx.transfer(
                transaction_data["from_address"],
                transaction_data["to_address"],
                transaction_data["amount"]
            ).build()
            
            # Sign transaction if private key provided
            if "private_key" in transaction_data:
                private_key = PrivateKey(bytes.fromhex(transaction_data["private_key"]))
                txn = txn.sign(private_key)
            
            # Broadcast transaction
            result = txn.broadcast()
            
            if result.get("result"):
                txid = result["txid"]
                
                # Create transaction info
                transaction_info = TransactionInfo(
                    txid=txid,
                    block_number=0,  # Will be updated when confirmed
                    timestamp=int(time.time() * 1000),
                    from_address=transaction_data["from_address"],
                    to_address=transaction_data["to_address"],
                    amount=transaction_data["amount"],
                    token_type=transaction_data.get("token_type", "TRX"),
                    fee=transaction_data.get("fee", 0),
                    energy_used=0,
                    bandwidth_used=0,
                    status="PENDING",
                    raw_data=result
                )
                
                # Add to pending transactions
                self.pending_transactions[txid] = transaction_info
                
                # Save transaction info
                await self._save_transaction_info(transaction_info)
                
                logger.info(f"Transaction broadcasted: {txid}")
                return txid
            else:
                raise RuntimeError(f"Transaction broadcast failed: {result}")
                
        except Exception as e:
            logger.error(f"Error broadcasting transaction: {e}")
            raise
    
    async def wait_for_confirmation(self, txid: str, timeout_seconds: int = 300) -> bool:
        """Wait for transaction confirmation"""
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout_seconds:
                transaction_info = await self.get_transaction(txid)
                
                if transaction_info and transaction_info.status == "SUCCESS":
                    logger.info(f"Transaction confirmed: {txid}")
                    return True
                elif transaction_info and transaction_info.status == "FAILED":
                    logger.error(f"Transaction failed: {txid}")
                    return False
                
                await asyncio.sleep(10)  # Check every 10 seconds
            
            logger.warning(f"Transaction confirmation timeout: {txid}")
            return False
            
        except Exception as e:
            logger.error(f"Error waiting for confirmation: {e}")
            return False
    
    async def _monitor_network(self):
        """Monitor network status and sync"""
        try:
            while True:
                try:
                    # Update network info
                    await self.get_network_info()
                    
                    # Check connection health
                    if self.connection_status == NetworkStatus.CONNECTED:
                        logger.debug("Network monitoring: Connected")
                    else:
                        logger.warning(f"Network monitoring: {self.connection_status}")
                    
                except Exception as e:
                    logger.error(f"Network monitoring error: {e}")
                    self.connection_status = NetworkStatus.ERROR
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
        except asyncio.CancelledError:
            logger.info("Network monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in network monitoring: {e}")
    
    async def _monitor_transactions(self):
        """Monitor pending transactions"""
        try:
            while True:
                for txid, transaction in list(self.pending_transactions.items()):
                    try:
                        # Check transaction status
                        updated_transaction = await self.get_transaction(txid)
                        
                        if updated_transaction and updated_transaction.status == "SUCCESS":
                            # Move to confirmed
                            self.confirmed_transactions[txid] = updated_transaction
                            del self.pending_transactions[txid]
                            
                            logger.info(f"Transaction confirmed: {txid}")
                            
                        elif updated_transaction and updated_transaction.status == "FAILED":
                            # Remove failed transaction
                            del self.pending_transactions[txid]
                            
                            logger.error(f"Transaction failed: {txid}")
                            
                    except Exception as e:
                        logger.error(f"Error monitoring transaction {txid}: {e}")
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
        except asyncio.CancelledError:
            logger.info("Transaction monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in transaction monitoring: {e}")
    
    async def _monitor_accounts(self):
        """Monitor account balances and resources"""
        try:
            while True:
                for address, account in list(self.account_cache.items()):
                    try:
                        # Update account info
                        updated_account = await self.get_account_info(address)
                        
                        # Check for significant changes
                        if abs(updated_account.balance_trx - account.balance_trx) > 0.001:
                            logger.info(f"Balance change detected for {address}: {account.balance_trx} -> {updated_account.balance_trx}")
                        
                    except Exception as e:
                        logger.error(f"Error monitoring account {address}: {e}")
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
        except asyncio.CancelledError:
            logger.info("Account monitoring cancelled")
        except Exception as e:
            logger.error(f"Error in account monitoring: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old data"""
        try:
            while True:
                cutoff_date = datetime.now() - timedelta(days=7)
                
                # Clean up old confirmed transactions
                old_transactions = []
                for txid, transaction in self.confirmed_transactions.items():
                    if datetime.fromtimestamp(transaction.timestamp / 1000) < cutoff_date:
                        old_transactions.append(txid)
                
                for txid in old_transactions:
                    del self.confirmed_transactions[txid]
                
                if old_transactions:
                    logger.info(f"Cleaned up {len(old_transactions)} old transactions")
                
                # Clean up old account cache
                old_accounts = []
                for address, account in self.account_cache.items():
                    if account.last_updated < cutoff_date:
                        old_accounts.append(address)
                
                for address in old_accounts:
                    del self.account_cache[address]
                
                if old_accounts:
                    logger.info(f"Cleaned up {len(old_accounts)} old accounts")
                
                # Wait before next cleanup
                await asyncio.sleep(3600)  # Clean up every hour
                
        except asyncio.CancelledError:
            logger.info("Data cleanup cancelled")
        except Exception as e:
            logger.error(f"Error in data cleanup: {e}")
    
    async def _save_network_info(self, network_info: NetworkInfo):
        """Save network info to disk"""
        try:
            network_data = asdict(network_info)
            network_data["last_updated"] = network_info.last_updated.isoformat()
            
            network_file = self.network_dir / "network_info.json"
            async with aiofiles.open(network_file, "w") as f:
                await f.write(json.dumps(network_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving network info: {e}")
    
    async def _save_transaction_info(self, transaction_info: TransactionInfo):
        """Save transaction info to disk"""
        try:
            transaction_data = asdict(transaction_info)
            if transaction_data["raw_data"]:
                transaction_data["raw_data"] = str(transaction_data["raw_data"])
            
            transaction_file = self.transactions_dir / f"{transaction_info.txid}.json"
            async with aiofiles.open(transaction_file, "w") as f:
                await f.write(json.dumps(transaction_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving transaction info: {e}")
    
    async def _save_account_info(self, account_info: AccountInfo):
        """Save account info to disk"""
        try:
            account_data = asdict(account_info)
            account_data["last_updated"] = account_info.last_updated.isoformat()
            
            account_file = self.accounts_dir / f"{account_info.address}.json"
            async with aiofiles.open(account_file, "w") as f:
                await f.write(json.dumps(account_data, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving account info: {e}")
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        try:
            return {
                "network": self.network,
                "node_url": self.node_url,
                "connection_status": self.connection_status.value,
                "network_info": asdict(self.network_info) if self.network_info else None,
                "pending_transactions": len(self.pending_transactions),
                "confirmed_transactions": len(self.confirmed_transactions),
                "cached_accounts": len(self.account_cache),
                "monitoring_tasks": len(self.monitoring_tasks),
                "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting service stats: {e}")
            return {"error": str(e)}
    
    async def stop(self):
        """Stop the service"""
        try:
            # Cancel monitoring tasks
            for task in self.monitoring_tasks:
                task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
            
            logger.info("TronClientService stopped")
            
        except Exception as e:
            logger.error(f"Error stopping service: {e}")

# Global instance
tron_client_service = TronClientService()

# Convenience functions for external use
async def get_network_info() -> NetworkInfo:
    """Get current network information"""
    return await tron_client_service.get_network_info()

async def get_account_info(address: str) -> AccountInfo:
    """Get account information"""
    return await tron_client_service.get_account_info(address)

async def get_balance(address: str) -> float:
    """Get TRX balance for address"""
    return await tron_client_service.get_balance(address)

async def get_transaction(txid: str) -> Optional[TransactionInfo]:
    """Get transaction information"""
    return await tron_client_service.get_transaction(txid)

async def broadcast_transaction(transaction_data: Dict[str, Any]) -> str:
    """Broadcast transaction to TRON network"""
    return await tron_client_service.broadcast_transaction(transaction_data)

async def wait_for_confirmation(txid: str, timeout_seconds: int = 300) -> bool:
    """Wait for transaction confirmation"""
    return await tron_client_service.wait_for_confirmation(txid, timeout_seconds)

async def get_service_stats() -> Dict[str, Any]:
    """Get service statistics"""
    return await tron_client_service.get_service_stats()

if __name__ == "__main__":
    # Example usage
    async def main():
        try:
            # Get network info
            network_info = await get_network_info()
            print(f"Network: {network_info.network_name}, Block: {network_info.latest_block}")
            
            # Get account info
            test_address = "TYourTRONAddressHere123456789"
            account_info = await get_account_info(test_address)
            print(f"Account balance: {account_info.balance_trx} TRX")
            
            # Get service stats
            stats = await get_service_stats()
            print(f"Service stats: {stats}")
            
        except Exception as e:
            print(f"Error: {e}")
    
    asyncio.run(main())
