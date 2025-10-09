# Path: payment-systems/tron-node/usdt_trc20.py
# Lucid RDP USDT-TRC20 Operations - TRON USDT token operations
# Based on LUCID-STRICT requirements per Spec-1c and R-MUST-015

from __future__ import annotations

import os
import asyncio
import logging
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import json

from tronpy import Tron
from tronpy.keys import PrivateKey as TronPrivateKey
from tronpy.providers import HTTPProvider
from tronpy.contract import Contract

logger = logging.getLogger(__name__)

# USDT-TRC20 Contract Constants
USDT_TRC20_MAINNET = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # Mainnet USDT
USDT_TRC20_SHASTA = "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs"   # Shasta testnet USDT
USDT_DECIMALS = 6  # USDT has 6 decimal places
MIN_TRX_FEE = 10_000_000  # 10 TRX minimum fee (in sun)
MAX_TRX_FEE = 100_000_000  # 100 TRX maximum fee (in sun)

# Network Configuration
TRON_NETWORK = os.getenv("TRON_NETWORK", "shasta")  # shasta/mainnet
TRON_API_KEY = os.getenv("TRON_API_KEY", "")
TRON_API_ENDPOINT = os.getenv("TRON_API_ENDPOINT", "")


class TransactionStatus(Enum):
    """USDT transaction status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TransferType(Enum):
    """Types of USDT transfers"""
    PAYMENT = "payment"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    REFUND = "refund"
    REWARD = "reward"
    FEE = "fee"


@dataclass
class USDTTransfer:
    """USDT transfer transaction data"""
    from_address: str
    to_address: str
    amount_usdt: float
    transfer_type: TransferType
    session_id: Optional[str] = None
    reference_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime = None
    txid: Optional[str] = None
    status: TransactionStatus = TransactionStatus.PENDING
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


@dataclass
class USDTBalance:
    """USDT balance information"""
    address: str
    balance_usdt: float
    balance_raw: int  # Raw balance (with decimals)
    last_updated: datetime
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now(timezone.utc)


class USDTTRC20Client:
    """
    USDT-TRC20 operations client for Lucid RDP.
    
    Handles:
    - USDT-TRC20 token transfers per R-MUST-015
    - Balance queries and monitoring
    - Transaction status tracking
    - Fee management and optimization
    - Error handling and retry logic
    
    Network support:
    - Mainnet (production)
    - Shasta testnet (development)
    """
    
    def __init__(self, network: str = None, private_key_hex: str = None):
        """
        Initialize USDT-TRC20 client.
        
        Args:
            network: TRON network (mainnet/shasta)
            private_key_hex: Private key for transaction signing (optional)
        """
        self.network = network or TRON_NETWORK
        self.is_mainnet = self.network == "mainnet"
        self.usdt_contract_address = USDT_TRC20_MAINNET if self.is_mainnet else USDT_TRC20_SHASTA
        
        # Initialize TRON client
        self._initialize_tron_client()
        
        # Private key setup
        self.private_key = None
        self.sender_address = None
        if private_key_hex:
            self.set_private_key(private_key_hex)
        
        # Contract instance
        self.usdt_contract = None
        self._initialize_contract()
        
        logger.info(f"USDT-TRC20 client initialized: {self.network}")
    
    def _initialize_tron_client(self):
        """Initialize TRON client with appropriate network configuration"""
        try:
            if self.is_mainnet:
                self.tron = Tron()
            else:
                # Shasta testnet configuration
                provider = HTTPProvider("https://api.shasta.trongrid.io")
                self.tron = Tron(provider=provider)
            
            logger.info(f"TRON client connected to {self.network}")
        except Exception as e:
            logger.error(f"Failed to initialize TRON client: {e}")
            raise
    
    def _initialize_contract(self):
        """Initialize USDT contract instance"""
        try:
            self.usdt_contract = self.tron.get_contract(self.usdt_contract_address)
            logger.info(f"USDT contract initialized: {self.usdt_contract_address}")
        except Exception as e:
            logger.error(f"Failed to initialize USDT contract: {e}")
            raise
    
    def set_private_key(self, private_key_hex: str):
        """
        Set private key for transaction signing.
        
        Args:
            private_key_hex: Private key in hexadecimal format
        """
        try:
            self.private_key = TronPrivateKey(bytes.fromhex(private_key_hex))
            self.sender_address = self.private_key.public_key.to_base58check_address()
            logger.info(f"Private key set for address: {self.sender_address}")
        except Exception as e:
            logger.error(f"Failed to set private key: {e}")
            raise
    
    def _usdt_to_raw(self, amount_usdt: float) -> int:
        """Convert USDT amount to raw value (with decimals)"""
        return int(amount_usdt * (10 ** USDT_DECIMALS))
    
    def _raw_to_usdt(self, amount_raw: int) -> float:
        """Convert raw value to USDT amount"""
        return amount_raw / (10 ** USDT_DECIMALS)
    
    async def get_balance(self, address: str) -> USDTBalance:
        """
        Get USDT balance for an address.
        
        Args:
            address: TRON address to query
            
        Returns:
            USDTBalance object with balance information
        """
        try:
            # Call balanceOf function on USDT contract
            result = self.usdt_contract.functions.balanceOf(address)
            balance_raw = result.call()
            
            balance_usdt = self._raw_to_usdt(balance_raw)
            
            balance = USDTBalance(
                address=address,
                balance_usdt=balance_usdt,
                balance_raw=balance_raw,
                last_updated=datetime.now(timezone.utc)
            )
            
            logger.info(f"Balance query: {address} = {balance_usdt} USDT")
            return balance
            
        except Exception as e:
            logger.error(f"Failed to get balance for {address}: {e}")
            raise
    
    async def get_allowance(self, owner_address: str, spender_address: str) -> float:
        """
        Get USDT allowance for a spender.
        
        Args:
            owner_address: Address that owns the tokens
            spender_address: Address that can spend the tokens
            
        Returns:
            Allowance amount in USDT
        """
        try:
            result = self.usdt_contract.functions.allowance(owner_address, spender_address)
            allowance_raw = result.call()
            
            allowance_usdt = self._raw_to_usdt(allowance_raw)
            
            logger.info(f"Allowance query: {spender_address} can spend {allowance_usdt} USDT from {owner_address}")
            return allowance_usdt
            
        except Exception as e:
            logger.error(f"Failed to get allowance: {e}")
            raise
    
    async def approve(self, spender_address: str, amount_usdt: float, 
                     fee_limit_trx: int = 50) -> str:
        """
        Approve USDT spending for a spender address.
        
        Args:
            spender_address: Address to approve for spending
            amount_usdt: Amount to approve (0 for unlimited)
            fee_limit_trx: Fee limit in TRX (in sun)
            
        Returns:
            Transaction ID
        """
        if not self.private_key:
            raise ValueError("Private key required for approval transaction")
        
        try:
            amount_raw = self._usdt_to_raw(amount_usdt)
            
            # Build approval transaction
            txn = self.usdt_contract.functions.approve(spender_address, amount_raw)
            txn = txn.with_owner(self.sender_address)
            txn = txn.fee_limit(fee_limit_trx * 1_000_000)  # Convert TRX to sun
            
            # Sign and broadcast
            txn = txn.build()
            txn = txn.sign(self.private_key)
            result = txn.broadcast()
            
            txid = result.get("txid")
            if txid:
                logger.info(f"Approval transaction created: {txid}, {amount_usdt} USDT for {spender_address}")
                return txid
            else:
                raise ValueError(f"Approval transaction failed: {result}")
                
        except Exception as e:
            logger.error(f"Approval transaction failed: {e}")
            raise
    
    async def transfer(self, to_address: str, amount_usdt: float, 
                      transfer_type: TransferType = TransferType.PAYMENT,
                      session_id: str = None, reference_id: str = None,
                      metadata: Dict[str, Any] = None,
                      fee_limit_trx: int = 50) -> USDTTransfer:
        """
        Transfer USDT to another address.
        
        Args:
            to_address: Destination address
            amount_usdt: Amount to transfer in USDT
            transfer_type: Type of transfer
            session_id: Associated session ID (optional)
            reference_id: Reference ID for tracking (optional)
            metadata: Additional metadata (optional)
            fee_limit_trx: Fee limit in TRX (in sun)
            
        Returns:
            USDTTransfer object with transaction details
        """
        if not self.private_key:
            raise ValueError("Private key required for transfer transaction")
        
        try:
            amount_raw = self._usdt_to_raw(amount_usdt)
            
            # Check balance before transfer
            balance = await self.get_balance(self.sender_address)
            if balance.balance_usdt < amount_usdt:
                raise ValueError(f"Insufficient balance: {balance.balance_usdt} USDT < {amount_usdt} USDT")
            
            # Create transfer object
            transfer = USDTTransfer(
                from_address=self.sender_address,
                to_address=to_address,
                amount_usdt=amount_usdt,
                transfer_type=transfer_type,
                session_id=session_id,
                reference_id=reference_id,
                metadata=metadata
            )
            
            # Build transfer transaction
            txn = self.usdt_contract.functions.transfer(to_address, amount_raw)
            txn = txn.with_owner(self.sender_address)
            txn = txn.fee_limit(fee_limit_trx * 1_000_000)  # Convert TRX to sun
            
            # Sign and broadcast
            txn = txn.build()
            txn = txn.sign(self.private_key)
            result = txn.broadcast()
            
            txid = result.get("txid")
            if txid:
                transfer.txid = txid
                transfer.status = TransactionStatus.PENDING
                
                logger.info(f"Transfer transaction created: {txid}, {amount_usdt} USDT from {self.sender_address} to {to_address}")
                return transfer
            else:
                transfer.status = TransactionStatus.FAILED
                raise ValueError(f"Transfer transaction failed: {result}")
                
        except Exception as e:
            logger.error(f"Transfer transaction failed: {e}")
            raise
    
    async def transfer_from(self, from_address: str, to_address: str, amount_usdt: float,
                           transfer_type: TransferType = TransferType.PAYMENT,
                           session_id: str = None, reference_id: str = None,
                           metadata: Dict[str, Any] = None,
                           fee_limit_trx: int = 50) -> USDTTransfer:
        """
        Transfer USDT from one address to another (requires approval).
        
        Args:
            from_address: Source address (must have approved this contract)
            to_address: Destination address
            amount_usdt: Amount to transfer in USDT
            transfer_type: Type of transfer
            session_id: Associated session ID (optional)
            reference_id: Reference ID for tracking (optional)
            metadata: Additional metadata (optional)
            fee_limit_trx: Fee limit in TRX (in sun)
            
        Returns:
            USDTTransfer object with transaction details
        """
        if not self.private_key:
            raise ValueError("Private key required for transferFrom transaction")
        
        try:
            amount_raw = self._usdt_to_raw(amount_usdt)
            
            # Check allowance
            allowance = await self.get_allowance(from_address, self.sender_address)
            if allowance < amount_usdt:
                raise ValueError(f"Insufficient allowance: {allowance} USDT < {amount_usdt} USDT")
            
            # Create transfer object
            transfer = USDTTransfer(
                from_address=from_address,
                to_address=to_address,
                amount_usdt=amount_usdt,
                transfer_type=transfer_type,
                session_id=session_id,
                reference_id=reference_id,
                metadata=metadata
            )
            
            # Build transferFrom transaction
            txn = self.usdt_contract.functions.transferFrom(from_address, to_address, amount_raw)
            txn = txn.with_owner(self.sender_address)
            txn = txn.fee_limit(fee_limit_trx * 1_000_000)  # Convert TRX to sun
            
            # Sign and broadcast
            txn = txn.build()
            txn = txn.sign(self.private_key)
            result = txn.broadcast()
            
            txid = result.get("txid")
            if txid:
                transfer.txid = txid
                transfer.status = TransactionStatus.PENDING
                
                logger.info(f"TransferFrom transaction created: {txid}, {amount_usdt} USDT from {from_address} to {to_address}")
                return transfer
            else:
                transfer.status = TransactionStatus.FAILED
                raise ValueError(f"TransferFrom transaction failed: {result}")
                
        except Exception as e:
            logger.error(f"TransferFrom transaction failed: {e}")
            raise
    
    async def get_transaction_status(self, txid: str) -> TransactionStatus:
        """
        Get transaction status by transaction ID.
        
        Args:
            txid: Transaction ID to check
            
        Returns:
            TransactionStatus enum value
        """
        try:
            # Get transaction info from TRON network
            tx_info = self.tron.get_transaction_info(txid)
            
            if not tx_info:
                return TransactionStatus.PENDING
            
            # Check transaction result
            result = tx_info.get("result", "")
            if result == "SUCCESS":
                return TransactionStatus.CONFIRMED
            elif result == "FAILED":
                return TransactionStatus.FAILED
            else:
                return TransactionStatus.PENDING
                
        except Exception as e:
            logger.error(f"Failed to get transaction status for {txid}: {e}")
            return TransactionStatus.PENDING
    
    async def wait_for_confirmation(self, txid: str, timeout_seconds: int = 300, 
                                   check_interval: int = 10) -> TransactionStatus:
        """
        Wait for transaction confirmation.
        
        Args:
            txid: Transaction ID to monitor
            timeout_seconds: Maximum time to wait
            check_interval: Seconds between status checks
            
        Returns:
            Final transaction status
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout_seconds:
            status = await self.get_transaction_status(txid)
            
            if status in [TransactionStatus.CONFIRMED, TransactionStatus.FAILED]:
                logger.info(f"Transaction {txid} final status: {status}")
                return status
            
            await asyncio.sleep(check_interval)
        
        logger.warning(f"Transaction {txid} confirmation timeout after {timeout_seconds} seconds")
        return TransactionStatus.PENDING
    
    async def batch_transfer(self, transfers: List[Dict[str, Any]], 
                           fee_limit_trx: int = 50) -> List[USDTTransfer]:
        """
        Execute multiple transfers in sequence.
        
        Args:
            transfers: List of transfer dictionaries with required fields
            fee_limit_trx: Fee limit per transaction in TRX
            
        Returns:
            List of USDTTransfer objects
        """
        results = []
        
        for transfer_data in transfers:
            try:
                transfer = await self.transfer(
                    to_address=transfer_data["to_address"],
                    amount_usdt=transfer_data["amount_usdt"],
                    transfer_type=TransferType(transfer_data.get("transfer_type", "payment")),
                    session_id=transfer_data.get("session_id"),
                    reference_id=transfer_data.get("reference_id"),
                    metadata=transfer_data.get("metadata"),
                    fee_limit_trx=fee_limit_trx
                )
                results.append(transfer)
                
                # Small delay between transfers to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Batch transfer failed for {transfer_data}: {e}")
                # Create failed transfer object
                failed_transfer = USDTTransfer(
                    from_address=self.sender_address,
                    to_address=transfer_data["to_address"],
                    amount_usdt=transfer_data["amount_usdt"],
                    transfer_type=TransferType(transfer_data.get("transfer_type", "payment")),
                    session_id=transfer_data.get("session_id"),
                    reference_id=transfer_data.get("reference_id"),
                    metadata=transfer_data.get("metadata"),
                    status=TransactionStatus.FAILED
                )
                results.append(failed_transfer)
        
        logger.info(f"Batch transfer completed: {len(results)} transactions")
        return results
    
    async def get_transaction_history(self, address: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get transaction history for an address (USDT-related only).
        
        Args:
            address: Address to query
            limit: Maximum number of transactions to return
            
        Returns:
            List of transaction dictionaries
        """
        try:
            # Note: This is a simplified implementation
            # In production, you might want to use a TRON API service
            # that provides better transaction filtering
            
            transactions = self.tron.get_account_transactions(address, limit=limit)
            
            usdt_transactions = []
            for tx in transactions:
                # Filter for USDT contract interactions
                if (tx.get("raw_data", {}).get("contract", [{}])[0]
                    .get("parameter", {}).get("value", {})
                    .get("contract_address") == self.usdt_contract_address):
                    
                    usdt_transactions.append({
                        "txid": tx.get("txID"),
                        "timestamp": tx.get("timestamp"),
                        "block_number": tx.get("blockNumber"),
                        "from": tx.get("raw_data", {}).get("contract", [{}])[0]
                               .get("parameter", {}).get("value", {}).get("owner_address"),
                        "to": tx.get("raw_data", {}).get("contract", [{}])[0]
                             .get("parameter", {}).get("value", {}).get("to_address"),
                        "amount_raw": tx.get("raw_data", {}).get("contract", [{}])[0]
                                    .get("parameter", {}).get("value", {}).get("amount"),
                        "status": "confirmed" if tx.get("ret", [{}])[0].get("contractRet") == "SUCCESS" else "failed"
                    })
            
            logger.info(f"Retrieved {len(usdt_transactions)} USDT transactions for {address}")
            return usdt_transactions
            
        except Exception as e:
            logger.error(f"Failed to get transaction history for {address}: {e}")
            return []
    
    def close(self):
        """Close client connections"""
        try:
            if hasattr(self, 'tron') and self.tron:
                # TRON client cleanup if needed
                pass
            logger.info("USDT-TRC20 client closed")
        except Exception as e:
            logger.error(f"Error closing USDT-TRC20 client: {e}")


# Utility functions for common operations

async def create_session_payment(client: USDTTRC20Client, session_id: str, 
                                node_address: str, cost_usdt: float) -> str:
    """
    Create a session payment transaction.
    
    Args:
        client: USDT-TRC20 client instance
        session_id: Session identifier
        node_address: Node address to receive payment
        cost_usdt: Payment amount in USDT
        
    Returns:
        Transaction ID
    """
    try:
        transfer = await client.transfer(
            to_address=node_address,
            amount_usdt=cost_usdt,
            transfer_type=TransferType.PAYMENT,
            session_id=session_id,
            metadata={"type": "session_payment", "session_id": session_id}
        )
        
        logger.info(f"Session payment created: {transfer.txid} for session {session_id}")
        return transfer.txid
        
    except Exception as e:
        logger.error(f"Session payment failed for session {session_id}: {e}")
        raise


async def create_payout_transfer(client: USDTTRC20Client, recipient_address: str,
                               amount_usdt: float, payout_type: str,
                               reference_id: str = None) -> str:
    """
    Create a payout transfer transaction.
    
    Args:
        client: USDT-TRC20 client instance
        recipient_address: Address to receive payout
        amount_usdt: Payout amount in USDT
        payout_type: Type of payout (reward, fee, etc.)
        reference_id: Reference ID for tracking
        
    Returns:
        Transaction ID
    """
    try:
        transfer = await client.transfer(
            to_address=recipient_address,
            amount_usdt=amount_usdt,
            transfer_type=TransferType.REWARD,
            reference_id=reference_id,
            metadata={"type": "payout", "payout_type": payout_type}
        )
        
        logger.info(f"Payout transfer created: {transfer.txid} for {recipient_address}")
        return transfer.txid
        
    except Exception as e:
        logger.error(f"Payout transfer failed for {recipient_address}: {e}")
        raise


# Export main classes and functions
__all__ = [
    'USDTTRC20Client',
    'USDTTransfer',
    'USDTBalance',
    'TransactionStatus',
    'TransferType',
    'create_session_payment',
    'create_payout_transfer'
]
