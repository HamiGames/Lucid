"""
LUCID TRON Relay Service
Core relay functionality for TRON network operations

SECURITY: READ-ONLY operations only - no private key access
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

import httpx
from tronpy import Tron
from tronpy.providers import HTTPProvider

from config import config

logger = logging.getLogger(__name__)


class RelayService:
    """
    TRON Relay Service - Read-only network operations
    
    Provides:
    - TRON blockchain queries (cached)
    - Transaction verification
    - Account balance checks
    - Block information
    
    Does NOT provide:
    - Transaction signing
    - Transaction broadcasting
    - Private key operations
    """
    
    def __init__(self):
        self.tron: Optional[Tron] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.initialized = False
        self.last_block_number = 0
        self.last_sync_time: Optional[datetime] = None
        
    async def initialize(self):
        """Initialize the relay service"""
        try:
            # Get TRON endpoint
            endpoint = config.get_tron_endpoint()
            api_key = config.get_api_key()
            
            logger.info(f"Connecting to TRON network: {config.tron_network}")
            logger.info(f"Endpoint: {endpoint}")
            
            # Initialize TRON client with HTTPProvider
            if api_key:
                # With API key
                provider = HTTPProvider(endpoint, api_key=api_key)
                self.tron = Tron(provider=provider)
                logger.info("TRON client initialized with API key")
            else:
                # Without API key (rate limited)
                if config.tron_network == "mainnet":
                    self.tron = Tron()
                elif config.tron_network in ["shasta", "testnet"]:
                    self.tron = Tron(network="shasta")
                else:
                    self.tron = Tron()
                logger.info("TRON client initialized without API key (rate limited)")
            
            # Initialize HTTP client for direct API calls
            headers = {}
            if api_key:
                headers["TRON-PRO-API-KEY"] = api_key
                
            self.http_client = httpx.AsyncClient(
                base_url=endpoint,
                timeout=30.0,
                headers=headers
            )
            
            # Test connection
            if await self.check_tron_connection():
                self.initialized = True
                logger.info("✅ TRON relay service initialized successfully")
            else:
                logger.warning("⚠️ TRON connection test failed - service degraded")
                
        except Exception as e:
            logger.error(f"Failed to initialize relay service: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the relay service"""
        if self.http_client:
            await self.http_client.aclose()
            logger.info("HTTP client closed")
        self.initialized = False
    
    async def check_tron_connection(self) -> bool:
        """Check if TRON network is accessible"""
        try:
            block = await self.get_latest_block()
            if block and "block_header" in block:
                self.last_block_number = block.get("block_header", {}).get("raw_data", {}).get("number", 0)
                self.last_sync_time = datetime.utcnow()
                return True
            return False
        except Exception as e:
            logger.error(f"TRON connection check failed: {e}")
            return False
    
    # ==========================================================================
    # BLOCK OPERATIONS (Read-only)
    # ==========================================================================
    
    async def get_latest_block(self) -> Optional[Dict[str, Any]]:
        """Get the latest block from TRON network"""
        try:
            if self.http_client:
                response = await self.http_client.post("/wallet/getnowblock")
                if response.status_code == 200:
                    return response.json()
            return None
        except Exception as e:
            logger.error(f"Failed to get latest block: {e}")
            return None
    
    async def get_block_by_number(self, block_number: int) -> Optional[Dict[str, Any]]:
        """Get block by number"""
        try:
            if self.http_client:
                response = await self.http_client.post(
                    "/wallet/getblockbynum",
                    json={"num": block_number}
                )
                if response.status_code == 200:
                    return response.json()
            return None
        except Exception as e:
            logger.error(f"Failed to get block {block_number}: {e}")
            return None
    
    async def get_block_by_id(self, block_id: str) -> Optional[Dict[str, Any]]:
        """Get block by ID/hash"""
        try:
            if self.http_client:
                response = await self.http_client.post(
                    "/wallet/getblockbyid",
                    json={"value": block_id}
                )
                if response.status_code == 200:
                    return response.json()
            return None
        except Exception as e:
            logger.error(f"Failed to get block {block_id}: {e}")
            return None
    
    # ==========================================================================
    # TRANSACTION OPERATIONS (Read-only)
    # ==========================================================================
    
    async def get_transaction_by_id(self, txid: str) -> Optional[Dict[str, Any]]:
        """Get transaction by ID"""
        try:
            if self.http_client:
                response = await self.http_client.post(
                    "/wallet/gettransactionbyid",
                    json={"value": txid}
                )
                if response.status_code == 200:
                    data = response.json()
                    if data:  # Empty dict means not found
                        return data
            return None
        except Exception as e:
            logger.error(f"Failed to get transaction {txid}: {e}")
            return None
    
    async def get_transaction_info(self, txid: str) -> Optional[Dict[str, Any]]:
        """Get transaction info (includes receipt)"""
        try:
            if self.http_client:
                response = await self.http_client.post(
                    "/wallet/gettransactioninfobyid",
                    json={"value": txid}
                )
                if response.status_code == 200:
                    data = response.json()
                    if data:  # Empty dict means not found
                        return data
            return None
        except Exception as e:
            logger.error(f"Failed to get transaction info {txid}: {e}")
            return None
    
    async def get_transaction_confirmations(self, txid: str) -> int:
        """Get number of confirmations for a transaction"""
        try:
            tx_info = await self.get_transaction_info(txid)
            if tx_info and "blockNumber" in tx_info:
                tx_block = tx_info["blockNumber"]
                
                latest = await self.get_latest_block()
                if latest and "block_header" in latest:
                    current_block = latest["block_header"]["raw_data"]["number"]
                    return max(0, current_block - tx_block)
            return 0
        except Exception as e:
            logger.error(f"Failed to get confirmations for {txid}: {e}")
            return 0
    
    # ==========================================================================
    # ACCOUNT OPERATIONS (Read-only)
    # ==========================================================================
    
    async def get_account(self, address: str) -> Optional[Dict[str, Any]]:
        """Get account information"""
        try:
            if self.http_client:
                response = await self.http_client.post(
                    "/wallet/getaccount",
                    json={"address": address, "visible": True}
                )
                if response.status_code == 200:
                    return response.json()
            return None
        except Exception as e:
            logger.error(f"Failed to get account {address}: {e}")
            return None
    
    async def get_account_balance(self, address: str) -> Optional[Dict[str, Any]]:
        """Get account balance (TRX and TRC20)"""
        try:
            account = await self.get_account(address)
            if account:
                balance_trx = account.get("balance", 0) / 1_000_000  # Convert from SUN
                
                # Get TRC20 balances
                trc20_balances = {}
                for token in account.get("trc20", []):
                    for contract, amount in token.items():
                        trc20_balances[contract] = int(amount)
                
                return {
                    "address": address,
                    "balance_trx": balance_trx,
                    "balance_sun": account.get("balance", 0),
                    "trc20_balances": trc20_balances,
                    "bandwidth": account.get("net_usage", 0),
                    "energy": account.get("account_resource", {}).get("energy_usage", 0)
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {e}")
            return None
    
    async def get_account_resource(self, address: str) -> Optional[Dict[str, Any]]:
        """Get account resources (bandwidth, energy)"""
        try:
            if self.http_client:
                response = await self.http_client.post(
                    "/wallet/getaccountresource",
                    json={"address": address, "visible": True}
                )
                if response.status_code == 200:
                    return response.json()
            return None
        except Exception as e:
            logger.error(f"Failed to get resources for {address}: {e}")
            return None
    
    # ==========================================================================
    # TRC20 TOKEN OPERATIONS (Read-only)
    # ==========================================================================
    
    async def get_trc20_balance(self, address: str, contract_address: str) -> Optional[int]:
        """Get TRC20 token balance for an address"""
        try:
            if self.http_client:
                # Call balanceOf function
                response = await self.http_client.post(
                    "/wallet/triggerconstantcontract",
                    json={
                        "owner_address": address,
                        "contract_address": contract_address,
                        "function_selector": "balanceOf(address)",
                        "parameter": address.replace("T", "41").ljust(64, "0"),
                        "visible": True
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("result", {}).get("result"):
                        constant_result = data.get("constant_result", [])
                        if constant_result:
                            balance = int(constant_result[0], 16)
                            return balance
            return None
        except Exception as e:
            logger.error(f"Failed to get TRC20 balance: {e}")
            return None
    
    # ==========================================================================
    # NETWORK INFO (Read-only)
    # ==========================================================================
    
    async def get_chain_parameters(self) -> Optional[Dict[str, Any]]:
        """Get blockchain parameters"""
        try:
            if self.http_client:
                response = await self.http_client.get("/wallet/getchainparameters")
                if response.status_code == 200:
                    return response.json()
            return None
        except Exception as e:
            logger.error(f"Failed to get chain parameters: {e}")
            return None
    
    async def get_node_info(self) -> Optional[Dict[str, Any]]:
        """Get connected node info"""
        try:
            if self.http_client:
                response = await self.http_client.get("/wallet/getnodeinfo")
                if response.status_code == 200:
                    return response.json()
            return None
        except Exception as e:
            logger.error(f"Failed to get node info: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get relay service statistics"""
        return {
            "initialized": self.initialized,
            "network": config.tron_network,
            "endpoint": config.get_tron_endpoint(),
            "has_api_key": bool(config.get_api_key()),
            "last_block_number": self.last_block_number,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None
        }


# Global relay service instance
relay_service = RelayService()

