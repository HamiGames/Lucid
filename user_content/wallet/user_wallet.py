# Path: user_content/wallet/user_wallet.py
# Lucid RDP User Wallet - TRON wallet integration for users
# Based on LUCID-STRICT requirements per Spec-1c

from __future__ import annotations

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json

from tronpy import Tron
from tronpy.keys import PrivateKey as TronPrivateKey
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# Import from reorganized structure
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "payment-systems"))
from tron_node.tron_client import TronNodeClient
from blockchain.core.blockchain_engine import PayoutRouter

logger = logging.getLogger(__name__)

# User Wallet Constants
TRON_NETWORK = os.getenv("TRON_NETWORK", "shasta")  # shasta/mainnet
USDT_CONTRACT = os.getenv("USDT_TRC20_ADDRESS", "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs")  # Shasta testnet
MIN_BALANCE_USDT = float(os.getenv("MIN_BALANCE_USDT", "1.0"))  # $1 minimum balance
SESSION_COST_PER_GB = float(os.getenv("SESSION_COST_PER_GB", "0.01"))  # $0.01 per GB


class TransactionType(Enum):
    """Types of wallet transactions"""
    SESSION_PAYMENT = "session_payment"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    REFUND = "refund"


class TransactionStatus(Enum):
    """Transaction status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Transaction:
    """User wallet transaction"""
    tx_id: str
    tx_type: TransactionType
    amount_usdt: float
    from_address: str
    to_address: str
    session_id: Optional[str] = None
    tron_txid: Optional[str] = None
    status: TransactionStatus = TransactionStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.tx_id,
            "type": self.tx_type.value,
            "amount_usdt": self.amount_usdt,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "session_id": self.session_id,
            "tron_txid": self.tron_txid,
            "status": self.status.value,
            "created_at": self.created_at,
            "confirmed_at": self.confirmed_at
        }


class UserWallet:
    """
    User wallet for Lucid RDP payments.
    
    Handles:
    - TRON USDT-TRC20 transactions per R-MUST-015
    - Session payment processing
    - Balance management and monitoring
    - Transaction history and receipts
    """
    
    def __init__(self, user_address: str, private_key: Optional[str] = None):
        self.user_address = user_address
        self.private_key = private_key
        self.tron_client = TronNodeSystem(TRON_NETWORK)
        
        # Transaction tracking
        self.pending_transactions: Dict[str, Transaction] = {}
        self.transaction_history: List[Transaction] = []
        
        # Balance cache
        self._balance_cache: Optional[float] = None
        self._balance_updated: Optional[datetime] = None
        self._balance_cache_ttl = 300  # 5 minutes
        
        logger.info(f"User wallet initialized for address: {user_address}")
    
    async def get_balance(self, force_refresh: bool = False) -> float:
        """
        Get USDT balance for user address.
        
        Args:
            force_refresh: Force refresh from blockchain
            
        Returns:
            USDT balance
        """
        try:
            # Check cache validity
            now = datetime.now(timezone.utc)
            
            if (not force_refresh and self._balance_cache is not None and 
                self._balance_updated and 
                (now - self._balance_updated).total_seconds() < self._balance_cache_ttl):
                return self._balance_cache
            
            # Get USDT balance from TRON network
            balance_data = self.tron_client.get_usdt_balance(self.user_address)
            balance_usdt = balance_data.get("balance", 0.0)
            
            # Update cache
            self._balance_cache = balance_usdt
            self._balance_updated = now
            
            logger.debug(f"USDT balance for {self.user_address}: ${balance_usdt}")
            return balance_usdt
            
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return 0.0
    
    async def process_session_payment(self, session_id: str, cost_usdt: float, 
                                    node_address: str) -> Optional[str]:
        """
        Process payment for RDP session.
        
        Args:
            session_id: Session identifier
            cost_usdt: Session cost in USDT
            node_address: Node operator address
            
        Returns:
            Transaction ID if successful
        """
        try:
            # Check sufficient balance
            balance = await self.get_balance()
            if balance < cost_usdt:
                logger.error(f"Insufficient balance: ${balance} < ${cost_usdt}")
                return None
            
            if balance < MIN_BALANCE_USDT:
                logger.warning(f"Balance below minimum threshold: ${balance}")
            
            # Create transaction record
            tx_id = f"session_payment_{session_id}_{int(datetime.now(timezone.utc).timestamp())}"
            
            transaction = Transaction(
                tx_id=tx_id,
                tx_type=TransactionType.SESSION_PAYMENT,
                amount_usdt=cost_usdt,
                from_address=self.user_address,
                to_address=node_address,
                session_id=session_id,
                status=TransactionStatus.PENDING
            )
            
            # Store pending transaction
            self.pending_transactions[tx_id] = transaction
            
            # Process payment via PayoutRouterV0 (non-KYC for users)
            if self.private_key:
                tron_txid = await self.tron_client.create_session_payment(
                    session_id=session_id,
                    from_address=self.user_address,
                    to_address=node_address,
                    amount_usdt=cost_usdt,
                    private_key=self.private_key
                )
                
                if tron_txid:
                    transaction.tron_txid = tron_txid
                    transaction.status = TransactionStatus.PENDING
                    
                    # Start transaction monitoring
                    asyncio.create_task(self._monitor_transaction(tx_id))
                    
                    logger.info(f"Session payment initiated: {tx_id} -> {tron_txid}")
                    return tx_id
                else:
                    transaction.status = TransactionStatus.FAILED
                    logger.error(f"TRON transaction failed for session payment: {tx_id}")
                    return None
            else:
                logger.error("Private key required for session payments")
                return None
                
        except Exception as e:
            logger.error(f"Session payment failed: {e}")
            return None
    
    async def deposit_usdt(self, amount_usdt: float, from_external: bool = True) -> Optional[str]:
        """
        Deposit USDT to user wallet.
        
        Args:
            amount_usdt: Amount to deposit
            from_external: Whether deposit is from external wallet
            
        Returns:
            Transaction ID if successful
        """
        try:
            tx_id = f"deposit_{int(datetime.now(timezone.utc).timestamp())}"
            
            transaction = Transaction(
                tx_id=tx_id,
                tx_type=TransactionType.DEPOSIT,
                amount_usdt=amount_usdt,
                from_address="external" if from_external else self.user_address,
                to_address=self.user_address,
                status=TransactionStatus.PENDING
            )
            
            self.pending_transactions[tx_id] = transaction
            
            if from_external:
                # External deposit - provide deposit address
                logger.info(f"Deposit {amount_usdt} USDT to address: {self.user_address}")
                logger.info("Please send USDT-TRC20 to the above address")
            else:
                # Internal transfer (not implemented in this version)
                logger.warning("Internal deposits not implemented")
                transaction.status = TransactionStatus.FAILED
                return None
            
            return tx_id
            
        except Exception as e:
            logger.error(f"Deposit failed: {e}")
            return None
    
    async def withdraw_usdt(self, amount_usdt: float, to_address: str) -> Optional[str]:
        """
        Withdraw USDT from user wallet.
        
        Args:
            amount_usdt: Amount to withdraw
            to_address: Destination TRON address
            
        Returns:
            Transaction ID if successful
        """
        try:
            # Check sufficient balance
            balance = await self.get_balance()
            if balance < amount_usdt:
                logger.error(f"Insufficient balance for withdrawal: ${balance} < ${amount_usdt}")
                return None
            
            tx_id = f"withdrawal_{int(datetime.now(timezone.utc).timestamp())}"
            
            transaction = Transaction(
                tx_id=tx_id,
                tx_type=TransactionType.WITHDRAWAL,
                amount_usdt=amount_usdt,
                from_address=self.user_address,
                to_address=to_address,
                status=TransactionStatus.PENDING
            )
            
            self.pending_transactions[tx_id] = transaction
            
            # Process withdrawal
            if self.private_key:
                tron_txid = await self.tron_client.send_usdt(
                    from_address=self.user_address,
                    to_address=to_address,
                    amount_usdt=amount_usdt,
                    private_key=self.private_key
                )
                
                if tron_txid:
                    transaction.tron_txid = tron_txid
                    
                    # Start transaction monitoring
                    asyncio.create_task(self._monitor_transaction(tx_id))
                    
                    logger.info(f"Withdrawal initiated: {tx_id} -> {tron_txid}")
                    return tx_id
                else:
                    transaction.status = TransactionStatus.FAILED
                    logger.error(f"TRON withdrawal failed: {tx_id}")
                    return None
            else:
                logger.error("Private key required for withdrawals")
                return None
                
        except Exception as e:
            logger.error(f"Withdrawal failed: {e}")
            return None
    
    async def get_transaction_status(self, tx_id: str) -> Optional[Transaction]:
        """
        Get transaction status.
        
        Args:
            tx_id: Transaction identifier
            
        Returns:
            Transaction object if found
        """
        try:
            # Check pending transactions
            transaction = self.pending_transactions.get(tx_id)
            if transaction:
                return transaction
            
            # Check transaction history
            for tx in self.transaction_history:
                if tx.tx_id == tx_id:
                    return tx
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get transaction status: {e}")
            return None
    
    async def get_transaction_history(self, limit: int = 50) -> List[Transaction]:
        """
        Get transaction history.
        
        Args:
            limit: Maximum number of transactions
            
        Returns:
            List of transactions
        """
        try:
            # Combine pending and completed transactions
            all_transactions = list(self.pending_transactions.values()) + self.transaction_history
            
            # Sort by creation date (newest first)
            all_transactions.sort(key=lambda t: t.created_at, reverse=True)
            
            return all_transactions[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get transaction history: {e}")
            return []
    
    async def _monitor_transaction(self, tx_id: str):
        """Monitor transaction confirmation status"""
        try:
            transaction = self.pending_transactions.get(tx_id)
            if not transaction or not transaction.tron_txid:
                return
            
            # Poll for confirmation (max 5 minutes)
            max_polls = 60  # 5 minutes with 5-second intervals
            poll_count = 0
            
            while poll_count < max_polls:
                status = await self.tron_client.get_transaction_status(transaction.tron_txid)
                
                if status == "confirmed":
                    transaction.status = TransactionStatus.CONFIRMED
                    transaction.confirmed_at = datetime.now(timezone.utc)
                    
                    # Move to history
                    self.transaction_history.append(transaction)
                    del self.pending_transactions[tx_id]
                    
                    # Clear balance cache
                    self._balance_cache = None
                    
                    logger.info(f"Transaction confirmed: {tx_id}")
                    break
                    
                elif status == "failed":
                    transaction.status = TransactionStatus.FAILED
                    logger.error(f"Transaction failed: {tx_id}")
                    break
                
                # Wait before next poll
                await asyncio.sleep(5)
                poll_count += 1
            
            # If still pending after timeout
            if transaction.status == TransactionStatus.PENDING:
                logger.warning(f"Transaction monitoring timeout: {tx_id}")
            
        except Exception as e:
            logger.error(f"Transaction monitoring failed: {e}")
    
    def get_wallet_info(self) -> Dict[str, Any]:
        """Get wallet information summary"""
        try:
            pending_count = len(self.pending_transactions)
            history_count = len(self.transaction_history)
            
            # Calculate pending amounts
            pending_outgoing = sum(
                tx.amount_usdt for tx in self.pending_transactions.values()
                if tx.tx_type in [TransactionType.SESSION_PAYMENT, TransactionType.WITHDRAWAL]
            )
            
            return {
                "address": self.user_address,
                "network": TRON_NETWORK,
                "has_private_key": self.private_key is not None,
                "balance_cached": self._balance_cache,
                "balance_updated": self._balance_updated,
                "transactions": {
                    "pending": pending_count,
                    "history": history_count,
                    "pending_outgoing_usdt": pending_outgoing
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get wallet info: {e}")
            return {}
    
    def set_private_key(self, private_key: str) -> bool:
        """Set private key for transactions"""
        try:
            # Validate private key
            test_key = TronPrivateKey(bytes.fromhex(private_key))
            test_address = test_key.public_key.to_base58check_address()
            
            if test_address != self.user_address:
                logger.error("Private key does not match user address")
                return False
            
            self.private_key = private_key
            logger.info("Private key set successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set private key: {e}")
            return False


# Global user wallet instances
_user_wallets: Dict[str, UserWallet] = {}


def get_user_wallet(user_address: str, private_key: Optional[str] = None) -> UserWallet:
    """Get user wallet instance"""
    global _user_wallets
    
    if user_address not in _user_wallets:
        _user_wallets[user_address] = UserWallet(user_address, private_key)
    elif private_key and not _user_wallets[user_address].private_key:
        _user_wallets[user_address].set_private_key(private_key)
    
    return _user_wallets[user_address]


def create_user_wallet(user_address: str, private_key: str) -> UserWallet:
    """Create new user wallet with private key"""
    wallet = UserWallet(user_address, private_key)
    _user_wallets[user_address] = wallet
    return wallet


async def cleanup_user_wallets():
    """Cleanup all user wallet instances"""
    global _user_wallets
    _user_wallets.clear()
    logger.info("User wallets cleaned up")


if __name__ == "__main__":
    # Test user wallet
    async def test_user_wallet():
        print("Testing Lucid User Wallet...")
        
        # Test with sample TRON address
        test_address = "TTestUserAddress123456789012345"
        wallet = get_user_wallet(test_address)
        
        # Get wallet info
        info = wallet.get_wallet_info()
        print(f"Wallet info: {info}")
        
        # Get balance (will fail without real address)
        try:
            balance = await wallet.get_balance()
            print(f"Balance: ${balance} USDT")
        except Exception as e:
            print(f"Balance check failed (expected): {e}")
        
        # Test deposit
        deposit_tx = await wallet.deposit_usdt(10.0)
        print(f"Deposit transaction: {deposit_tx}")
        
        # Get transaction history
        history = await wallet.get_transaction_history()
        print(f"Transaction history: {len(history)} transactions")
        
        print("Test completed")
    
    asyncio.run(test_user_wallet())
