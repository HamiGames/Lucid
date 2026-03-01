"""
LUCID TRON Payment Client
Professional TRON blockchain client for payment processing
Handles TRX and USDT-TRC20 transactions for Lucid session payments
LUCID-STRICT Mode: Enhanced security with comprehensive error handling
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Union, Any
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum

import httpx
import tronpy
from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.providers import HTTPProvider
from tronpy.contract import Contract
from cryptography.fernet import Fernet
import structlog

# Configure structured logging
logger = structlog.get_logger(__name__)


class TronNetwork(Enum):
    """TRON network configurations"""
    SHASTA = "shasta"
    MAINNET = "mainnet"
    NILE = "nile"


class PaymentStatus(Enum):
    """Payment transaction status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class PaymentTransaction:
    """Payment transaction data structure"""
    tx_hash: str
    from_address: str
    to_address: str
    amount: Decimal
    token_type: str  # "TRX" or "USDT-TRC20"
    status: PaymentStatus
    timestamp: int
    block_number: Optional[int] = None
    gas_used: Optional[int] = None
    fee: Optional[Decimal] = None


@dataclass
class WalletBalance:
    """Wallet balance information"""
    address: str
    trx_balance: Decimal
    usdt_balance: Decimal
    energy: int
    bandwidth: int
    last_updated: int


class TronPaymentClient:
    """
    Professional TRON payment client for Lucid session payments
    
    Handles:
    - TRX transactions for session fees
    - USDT-TRC20 payments for premium services
    - Payment verification and confirmation
    - Wallet balance monitoring
    - Transaction history tracking
    """
    
    def __init__(
        self,
        network: TronNetwork = TronNetwork.SHASTA,
        api_key: Optional[str] = None,
        private_key: Optional[str] = None,
        encryption_key: Optional[str] = None
    ):
        """
        Initialize TRON payment client
        
        Args:
            network: TRON network (shasta for testnet, mainnet for production)
            api_key: TRON Grid API key for enhanced rate limits
            private_key: Wallet private key for transaction signing
            encryption_key: Encryption key for secure key storage
        """
        self.network = network
        self.api_key = api_key
        self.encryption_key = encryption_key
        self._private_key = private_key
        self._tron_client = None
        self._usdt_contract = None
        self._session = None
        
        # Network configurations
        self._network_configs = {
            TronNetwork.SHASTA: {
                "rpc_url": "https://api.shasta.trongrid.io",
                "explorer": "https://shasta.tronscan.org",
                "usdt_contract": "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs"  # Shasta USDT
            },
            TronNetwork.MAINNET: {
                "rpc_url": "https://api.trongrid.io",
                "explorer": "https://tronscan.org",
                "usdt_contract": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # Mainnet USDT
            },
            TronNetwork.NILE: {
                "rpc_url": "https://api.nileex.io",
                "explorer": "https://nile.tronscan.org",
                "usdt_contract": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"  # Nile USDT
            }
        }
        
        # Initialize HTTP session
        self._init_http_session()
        
        # Initialize TRON client
        self._init_tron_client()
        
        logger.info(
            "TronPaymentClient initialized",
            network=network.value,
            has_api_key=bool(api_key),
            has_private_key=bool(private_key)
        )
    
    def _init_http_session(self) -> None:
        """Initialize HTTP session with proper headers"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Lucid-TronClient/1.0.0"
        }
        
        if self.api_key:
            headers["TRON-PRO-API-KEY"] = self.api_key
        
        self._session = httpx.AsyncClient(
            headers=headers,
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    def _init_tron_client(self) -> None:
        """Initialize TRON client with network configuration"""
        config = self._network_configs[self.network]
        
        try:
            provider = HTTPProvider(config["rpc_url"])
            self._tron_client = Tron(provider)
            
            # Initialize USDT contract
            self._usdt_contract = self._tron_client.get_contract(config["usdt_contract"])
            
            logger.info("TRON client initialized successfully", network=self.network.value)
            
        except Exception as e:
            logger.error("Failed to initialize TRON client", error=str(e), network=self.network.value)
            raise
    
    async def get_wallet_balance(self, address: str) -> WalletBalance:
        """
        Get comprehensive wallet balance information
        
        Args:
            address: TRON wallet address
            
        Returns:
            WalletBalance object with TRX, USDT, energy, and bandwidth info
        """
        try:
            # Get account info
            account_info = await self._get_account_info(address)
            
            # Get TRX balance
            trx_balance = Decimal(str(account_info.get("balance", 0))) / Decimal("1000000")  # Convert from sun
            
            # Get USDT balance
            usdt_balance = await self._get_usdt_balance(address)
            
            # Get resource info
            energy = account_info.get("energy", 0)
            bandwidth = account_info.get("bandwidth", 0)
            
            balance = WalletBalance(
                address=address,
                trx_balance=trx_balance,
                usdt_balance=usdt_balance,
                energy=energy,
                bandwidth=bandwidth,
                last_updated=int(time.time())
            )
            
            logger.info(
                "Wallet balance retrieved",
                address=address,
                trx_balance=float(trx_balance),
                usdt_balance=float(usdt_balance),
                energy=energy,
                bandwidth=bandwidth
            )
            
            return balance
            
        except Exception as e:
            logger.error("Failed to get wallet balance", address=address, error=str(e))
            raise
    
    async def _get_account_info(self, address: str) -> Dict[str, Any]:
        """Get account information from TRON network"""
        try:
            response = await self._session.get(
                f"{self._network_configs[self.network]['rpc_url']}/wallet/getaccount",
                json={"address": address}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to get account info", address=address, error=str(e))
            raise
    
    async def _get_usdt_balance(self, address: str) -> Decimal:
        """Get USDT-TRC20 balance for address"""
        try:
            if not self._usdt_contract:
                return Decimal("0")
            
            # Call balanceOf function
            balance = self._usdt_contract.functions.balanceOf(address)
            balance_sun = balance.call()
            
            # Convert from smallest unit (6 decimals for USDT)
            return Decimal(str(balance_sun)) / Decimal("1000000")
            
        except Exception as e:
            logger.error("Failed to get USDT balance", address=address, error=str(e))
            return Decimal("0")
    
    async def send_trx(
        self,
        to_address: str,
        amount: Decimal,
        from_private_key: Optional[str] = None,
        memo: Optional[str] = None
    ) -> PaymentTransaction:
        """
        Send TRX payment
        
        Args:
            to_address: Recipient TRON address
            amount: Amount in TRX
            from_private_key: Sender's private key (if not set in constructor)
            memo: Optional transaction memo
            
        Returns:
            PaymentTransaction object
        """
        try:
            private_key = from_private_key or self._private_key
            if not private_key:
                raise ValueError("Private key required for sending transactions")
            
            # Convert amount to sun (smallest TRX unit)
            amount_sun = int(amount * Decimal("1000000"))
            
            # Create transaction
            txn = (
                self._tron_client.trx.transfer(
                    to_address,
                    amount_sun,
                    memo=memo
                )
                .memo(memo or f"Lucid payment - {int(time.time())}")
                .build()
                .sign(PrivateKey(bytes.fromhex(private_key)))
            )
            
            # Broadcast transaction
            result = txn.broadcast()
            
            if result.get("result", False):
                tx_hash = result["txid"]
                
                transaction = PaymentTransaction(
                    tx_hash=tx_hash,
                    from_address=self._get_address_from_private_key(private_key),
                    to_address=to_address,
                    amount=amount,
                    token_type="TRX",
                    status=PaymentStatus.PENDING,
                    timestamp=int(time.time())
                )
                
                logger.info(
                    "TRX transaction sent",
                    tx_hash=tx_hash,
                    to_address=to_address,
                    amount=float(amount)
                )
                
                return transaction
            else:
                raise Exception(f"Transaction failed: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            logger.error("Failed to send TRX", to_address=to_address, amount=float(amount), error=str(e))
            raise
    
    async def send_usdt(
        self,
        to_address: str,
        amount: Decimal,
        from_private_key: Optional[str] = None,
        memo: Optional[str] = None
    ) -> PaymentTransaction:
        """
        Send USDT-TRC20 payment
        
        Args:
            to_address: Recipient TRON address
            amount: Amount in USDT
            from_private_key: Sender's private key (if not set in constructor)
            memo: Optional transaction memo
            
        Returns:
            PaymentTransaction object
        """
        try:
            private_key = from_private_key or self._private_key
            if not private_key:
                raise ValueError("Private key required for sending transactions")
            
            if not self._usdt_contract:
                raise ValueError("USDT contract not initialized")
            
            # Convert amount to smallest USDT unit (6 decimals)
            amount_smallest = int(amount * Decimal("1000000"))
            
            # Create transfer transaction
            txn = (
                self._usdt_contract.functions.transfer(to_address, amount_smallest)
                .with_owner(self._get_address_from_private_key(private_key))
                .fee_limit(10_000_000)  # 10 TRX fee limit
                .build()
                .sign(PrivateKey(bytes.fromhex(private_key)))
            )
            
            # Broadcast transaction
            result = txn.broadcast()
            
            if result.get("result", False):
                tx_hash = result["txid"]
                
                transaction = PaymentTransaction(
                    tx_hash=tx_hash,
                    from_address=self._get_address_from_private_key(private_key),
                    to_address=to_address,
                    amount=amount,
                    token_type="USDT-TRC20",
                    status=PaymentStatus.PENDING,
                    timestamp=int(time.time())
                )
                
                logger.info(
                    "USDT transaction sent",
                    tx_hash=tx_hash,
                    to_address=to_address,
                    amount=float(amount)
                )
                
                return transaction
            else:
                raise Exception(f"Transaction failed: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            logger.error("Failed to send USDT", to_address=to_address, amount=float(amount), error=str(e))
            raise
    
    async def get_transaction_status(self, tx_hash: str) -> PaymentTransaction:
        """
        Get transaction status and details
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            PaymentTransaction object with updated status
        """
        try:
            # Get transaction info
            tx_info = await self._get_transaction_info(tx_hash)
            
            if not tx_info:
                raise ValueError(f"Transaction not found: {tx_hash}")
            
            # Determine status
            if tx_info.get("ret", [{}])[0].get("contractRet") == "SUCCESS":
                status = PaymentStatus.CONFIRMED
            elif tx_info.get("ret", [{}])[0].get("contractRet") == "REVERT":
                status = PaymentStatus.FAILED
            else:
                status = PaymentStatus.PENDING
            
            # Extract transaction details
            contract = tx_info.get("raw_data", {}).get("contract", [{}])[0]
            parameter = contract.get("parameter", {}).get("value", {})
            
            # Determine token type and amount
            if contract.get("type") == "TransferContract":
                token_type = "TRX"
                amount = Decimal(str(parameter.get("amount", 0))) / Decimal("1000000")
            else:
                # Assume USDT for other contract types
                token_type = "USDT-TRC20"
                amount = Decimal("0")  # Would need to parse contract data for exact amount
            
            transaction = PaymentTransaction(
                tx_hash=tx_hash,
                from_address=parameter.get("owner_address", ""),
                to_address=parameter.get("to_address", ""),
                amount=amount,
                token_type=token_type,
                status=status,
                timestamp=tx_info.get("raw_data", {}).get("timestamp", 0),
                block_number=tx_info.get("blockNumber"),
                gas_used=tx_info.get("receipt", {}).get("energy_used"),
                fee=Decimal(str(tx_info.get("receipt", {}).get("fee", 0))) / Decimal("1000000")
            )
            
            logger.info(
                "Transaction status retrieved",
                tx_hash=tx_hash,
                status=status.value,
                token_type=token_type,
                amount=float(amount)
            )
            
            return transaction
            
        except Exception as e:
            logger.error("Failed to get transaction status", tx_hash=tx_hash, error=str(e))
            raise
    
    async def _get_transaction_info(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get transaction information from TRON network"""
        try:
            response = await self._session.get(
                f"{self._network_configs[self.network]['rpc_url']}/wallet/gettransactionbyid",
                params={"value": tx_hash}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Failed to get transaction info", tx_hash=tx_hash, error=str(e))
            return None
    
    def _get_address_from_private_key(self, private_key: str) -> str:
        """Get TRON address from private key"""
        try:
            key = PrivateKey(bytes.fromhex(private_key))
            return key.public_key.to_base58check_address()
        except Exception as e:
            logger.error("Failed to get address from private key", error=str(e))
            raise
    
    async def verify_payment(
        self,
        tx_hash: str,
        expected_amount: Decimal,
        expected_recipient: str,
        token_type: str = "TRX"
    ) -> bool:
        """
        Verify payment transaction meets expected criteria
        
        Args:
            tx_hash: Transaction hash to verify
            expected_amount: Expected payment amount
            expected_recipient: Expected recipient address
            token_type: Expected token type ("TRX" or "USDT-TRC20")
            
        Returns:
            True if payment is verified, False otherwise
        """
        try:
            transaction = await self.get_transaction_status(tx_hash)
            
            # Check if transaction is confirmed
            if transaction.status != PaymentStatus.CONFIRMED:
                logger.warning(
                    "Payment not confirmed",
                    tx_hash=tx_hash,
                    status=transaction.status.value
                )
                return False
            
            # Check recipient
            if transaction.to_address.lower() != expected_recipient.lower():
                logger.warning(
                    "Payment recipient mismatch",
                    tx_hash=tx_hash,
                    expected=expected_recipient,
                    actual=transaction.to_address
                )
                return False
            
            # Check amount (with small tolerance for fees)
            amount_tolerance = Decimal("0.001")  # 0.001 TRX/USDT tolerance
            if abs(transaction.amount - expected_amount) > amount_tolerance:
                logger.warning(
                    "Payment amount mismatch",
                    tx_hash=tx_hash,
                    expected=float(expected_amount),
                    actual=float(transaction.amount)
                )
                return False
            
            # Check token type
            if transaction.token_type != token_type:
                logger.warning(
                    "Payment token type mismatch",
                    tx_hash=tx_hash,
                    expected=token_type,
                    actual=transaction.token_type
                )
                return False
            
            logger.info(
                "Payment verified successfully",
                tx_hash=tx_hash,
                amount=float(transaction.amount),
                recipient=transaction.to_address,
                token_type=transaction.token_type
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to verify payment", tx_hash=tx_hash, error=str(e))
            return False
    
    async def get_transaction_history(
        self,
        address: str,
        limit: int = 50,
        token_type: Optional[str] = None
    ) -> List[PaymentTransaction]:
        """
        Get transaction history for an address
        
        Args:
            address: TRON address
            limit: Maximum number of transactions to return
            token_type: Filter by token type ("TRX" or "USDT-TRC20")
            
        Returns:
            List of PaymentTransaction objects
        """
        try:
            # This would typically use TRON Grid API for comprehensive history
            # For now, return empty list as this requires more complex implementation
            logger.info("Transaction history requested", address=address, limit=limit, token_type=token_type)
            return []
            
        except Exception as e:
            logger.error("Failed to get transaction history", address=address, error=str(e))
            return []
    
    async def close(self) -> None:
        """Close HTTP session and cleanup resources"""
        if self._session:
            await self._session.aclose()
        logger.info("TronPaymentClient closed")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Example usage and testing functions
async def main():
    """Example usage of TronPaymentClient"""
    
    # Initialize client for Shasta testnet
    async with TronPaymentClient(
        network=TronNetwork.SHASTA,
        api_key="your_tron_api_key_here"
    ) as client:
        
        # Get wallet balance
        address = "TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH"
        balance = await client.get_wallet_balance(address)
        print(f"Balance: {balance.trx_balance} TRX, {balance.usdt_balance} USDT")
        
        # Example transaction (commented out for safety)
        # transaction = await client.send_trx(
        #     to_address="TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH",
        #     amount=Decimal("1.0"),
        #     from_private_key="your_private_key_here"
        # )
        # print(f"Transaction sent: {transaction.tx_hash}")


if __name__ == "__main__":
    asyncio.run(main())
