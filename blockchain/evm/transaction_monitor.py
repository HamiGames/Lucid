#!/usr/bin/env python3
"""
Transaction Monitor for EVM Transactions
Based on rebuild-blockchain-engine.md specifications

Provides transaction monitoring for On-System Chain:
- Real-time transaction status tracking
- Confirmation monitoring
- Failed transaction handling
- Transaction timeout management
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class TransactionEvent(Enum):
    """Transaction events"""
    SUBMITTED = "submitted"
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class TransactionInfo:
    """Transaction information"""
    tx_hash: str
    contract_address: str
    function_name: str
    gas_limit: int
    gas_price: int
    status: str
    block_number: Optional[int]
    gas_used: Optional[int]
    submitted_at: datetime
    confirmed_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class TransactionCallback:
    """Transaction status callback"""
    tx_hash: str
    callback: Callable[[TransactionInfo, TransactionEvent], None]
    event_types: Set[TransactionEvent]


class TransactionMonitor:
    """
    Transaction monitor for EVM transactions.
    
    Provides real-time monitoring with:
    - Status tracking
    - Confirmation monitoring
    - Callback notifications
    - Timeout handling
    """
    
    def __init__(self, evm_client, poll_interval: float = 2.0, timeout_minutes: int = 10):
        self.evm_client = evm_client
        self.poll_interval = poll_interval
        self.timeout_minutes = timeout_minutes
        self.logger = logging.getLogger(__name__)
        
        # Transaction tracking
        self._transactions: Dict[str, TransactionInfo] = {}
        self._callbacks: Dict[str, List[TransactionCallback]] = defaultdict(list)
        
        # Monitoring state
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Statistics
        self._stats = {
            "total_monitored": 0,
            "confirmed": 0,
            "failed": 0,
            "timeout": 0
        }
    
    async def start_monitoring(self):
        """Start transaction monitoring"""
        try:
            if self._monitoring:
                self.logger.warning("Transaction monitoring already started")
                return
            
            self._monitoring = True
            self._monitor_task = asyncio.create_task(self._monitoring_loop())
            
            self.logger.info("Transaction monitoring started")
            
        except Exception as e:
            self.logger.error(f"Failed to start transaction monitoring: {e}")
            raise
    
    async def stop_monitoring(self):
        """Stop transaction monitoring"""
        try:
            self._monitoring = False
            
            if self._monitor_task:
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
                self._monitor_task = None
            
            self.logger.info("Transaction monitoring stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop transaction monitoring: {e}")
    
    async def monitor_transaction(
        self,
        tx_hash: str,
        contract_address: str,
        function_name: str,
        gas_limit: int,
        gas_price: int
    ) -> TransactionInfo:
        """
        Start monitoring a transaction.
        
        Args:
            tx_hash: Transaction hash
            contract_address: Contract address
            function_name: Function name
            gas_limit: Gas limit
            gas_price: Gas price
            
        Returns:
            TransactionInfo object
        """
        try:
            # Create transaction info
            tx_info = TransactionInfo(
                tx_hash=tx_hash,
                contract_address=contract_address,
                function_name=function_name,
                gas_limit=gas_limit,
                gas_price=gas_price,
                status="pending",
                block_number=None,
                gas_used=None,
                submitted_at=datetime.now(timezone.utc)
            )
            
            # Store transaction
            self._transactions[tx_hash] = tx_info
            
            # Update statistics
            self._stats["total_monitored"] += 1
            
            # Trigger submitted callback
            await self._trigger_callbacks(tx_hash, TransactionEvent.SUBMITTED)
            
            self.logger.info(f"Started monitoring transaction: {tx_hash}")
            return tx_info
            
        except Exception as e:
            self.logger.error(f"Failed to start monitoring transaction {tx_hash}: {e}")
            raise
    
    async def add_callback(
        self,
        tx_hash: str,
        callback: Callable[[TransactionInfo, TransactionEvent], None],
        event_types: Optional[Set[TransactionEvent]] = None
    ):
        """
        Add callback for transaction events.
        
        Args:
            tx_hash: Transaction hash
            callback: Callback function
            event_types: Event types to listen for (None for all)
        """
        try:
            if event_types is None:
                event_types = set(TransactionEvent)
            
            callback_obj = TransactionCallback(
                tx_hash=tx_hash,
                callback=callback,
                event_types=event_types
            )
            
            self._callbacks[tx_hash].append(callback_obj)
            
            self.logger.debug(f"Added callback for transaction {tx_hash}")
            
        except Exception as e:
            self.logger.error(f"Failed to add callback for transaction {tx_hash}: {e}")
    
    async def get_transaction_info(self, tx_hash: str) -> Optional[TransactionInfo]:
        """Get transaction information"""
        try:
            return self._transactions.get(tx_hash)
            
        except Exception as e:
            self.logger.error(f"Failed to get transaction info for {tx_hash}: {e}")
            return None
    
    async def get_transaction_status(self, tx_hash: str) -> Optional[str]:
        """Get transaction status"""
        try:
            tx_info = self._transactions.get(tx_hash)
            if tx_info:
                return tx_info.status
            
            # Fallback to EVM client
            if hasattr(self.evm_client, 'get_transaction_status'):
                return await self.evm_client.get_transaction_status(tx_hash)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get transaction status for {tx_hash}: {e}")
            return None
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        try:
            while self._monitoring:
                await self._check_all_transactions()
                await asyncio.sleep(self.poll_interval)
                
        except asyncio.CancelledError:
            self.logger.info("Transaction monitoring loop cancelled")
        except Exception as e:
            self.logger.error(f"Error in transaction monitoring loop: {e}")
    
    async def _check_all_transactions(self):
        """Check all monitored transactions"""
        try:
            current_time = datetime.now(timezone.utc)
            
            for tx_hash, tx_info in list(self._transactions.items()):
                # Check for timeout
                if self._is_transaction_timeout(tx_info, current_time):
                    await self._handle_transaction_timeout(tx_hash, tx_info)
                    continue
                
                # Check transaction status
                await self._check_transaction_status(tx_hash, tx_info)
                
        except Exception as e:
            self.logger.error(f"Error checking transactions: {e}")
    
    async def _check_transaction_status(self, tx_hash: str, tx_info: TransactionInfo):
        """Check status of a specific transaction"""
        try:
            # Get status from EVM client
            status = await self.evm_client.get_transaction_status(tx_hash)
            
            if not status:
                return
            
            # Check if status changed
            if status != tx_info.status:
                old_status = tx_info.status
                tx_info.status = status
                
                # Handle status change
                if status == "confirmed":
                    await self._handle_transaction_confirmed(tx_hash, tx_info)
                elif status == "failed":
                    await self._handle_transaction_failed(tx_hash, tx_info)
                elif status == "pending" and old_status != "pending":
                    await self._trigger_callbacks(tx_hash, TransactionEvent.PENDING)
                
                self.logger.info(f"Transaction {tx_hash} status changed: {old_status} -> {status}")
            
        except Exception as e:
            self.logger.error(f"Failed to check status for transaction {tx_hash}: {e}")
    
    async def _handle_transaction_confirmed(self, tx_hash: str, tx_info: TransactionInfo):
        """Handle confirmed transaction"""
        try:
            # Get transaction receipt for additional info
            if hasattr(self.evm_client, 'get_transaction_receipt'):
                receipt = await self.evm_client.get_transaction_receipt(tx_hash)
                if receipt:
                    tx_info.block_number = receipt.get("blockNumber")
                    tx_info.gas_used = receipt.get("gasUsed")
            
            tx_info.confirmed_at = datetime.now(timezone.utc)
            
            # Update statistics
            self._stats["confirmed"] += 1
            
            # Trigger callback
            await self._trigger_callbacks(tx_hash, TransactionEvent.CONFIRMED)
            
            self.logger.info(f"Transaction confirmed: {tx_hash}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle confirmed transaction {tx_hash}: {e}")
    
    async def _handle_transaction_failed(self, tx_hash: str, tx_info: TransactionInfo):
        """Handle failed transaction"""
        try:
            # Get error message if available
            if hasattr(self.evm_client, 'get_transaction_receipt'):
                receipt = await self.evm_client.get_transaction_receipt(tx_hash)
                if receipt:
                    tx_info.error_message = receipt.get("errorMessage", "Transaction failed")
            
            # Update statistics
            self._stats["failed"] += 1
            
            # Trigger callback
            await self._trigger_callbacks(tx_hash, TransactionEvent.FAILED)
            
            self.logger.warning(f"Transaction failed: {tx_hash}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle failed transaction {tx_hash}: {e}")
    
    async def _handle_transaction_timeout(self, tx_hash: str, tx_info: TransactionInfo):
        """Handle transaction timeout"""
        try:
            tx_info.status = "timeout"
            tx_info.error_message = f"Transaction timeout after {self.timeout_minutes} minutes"
            
            # Update statistics
            self._stats["timeout"] += 1
            
            # Trigger callback
            await self._trigger_callbacks(tx_hash, TransactionEvent.TIMEOUT)
            
            self.logger.warning(f"Transaction timeout: {tx_hash}")
            
        except Exception as e:
            self.logger.error(f"Failed to handle timeout for transaction {tx_hash}: {e}")
    
    def _is_transaction_timeout(self, tx_info: TransactionInfo, current_time: datetime) -> bool:
        """Check if transaction has timed out"""
        try:
            timeout_delta = timedelta(minutes=self.timeout_minutes)
            return current_time - tx_info.submitted_at > timeout_delta
            
        except Exception:
            return False
    
    async def _trigger_callbacks(self, tx_hash: str, event: TransactionEvent):
        """Trigger callbacks for transaction event"""
        try:
            tx_info = self._transactions.get(tx_hash)
            if not tx_info:
                return
            
            callbacks = self._callbacks.get(tx_hash, [])
            
            for callback_obj in callbacks:
                try:
                    if event in callback_obj.event_types:
                        callback_obj.callback(tx_info, event)
                except Exception as e:
                    self.logger.error(f"Error in transaction callback: {e}")
            
        except Exception as e:
            self.logger.error(f"Failed to trigger callbacks for transaction {tx_hash}: {e}")
    
    async def cleanup_completed_transactions(self, max_age_hours: int = 24):
        """Cleanup completed transactions older than specified age"""
        try:
            current_time = datetime.now(timezone.utc)
            cutoff_time = current_time - timedelta(hours=max_age_hours)
            
            completed_statuses = {"confirmed", "failed", "timeout"}
            
            to_remove = []
            for tx_hash, tx_info in self._transactions.items():
                if (tx_info.status in completed_statuses and 
                    tx_info.submitted_at < cutoff_time):
                    to_remove.append(tx_hash)
            
            for tx_hash in to_remove:
                del self._transactions[tx_hash]
                if tx_hash in self._callbacks:
                    del self._callbacks[tx_hash]
            
            if to_remove:
                self.logger.info(f"Cleaned up {len(to_remove)} completed transactions")
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup completed transactions: {e}")
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics"""
        try:
            current_stats = self._stats.copy()
            current_stats.update({
                "active_monitoring": len(self._transactions),
                "pending_transactions": len([t for t in self._transactions.values() if t.status == "pending"]),
                "monitoring_active": self._monitoring
            })
            
            return current_stats
            
        except Exception as e:
            self.logger.error(f"Failed to get monitoring stats: {e}")
            return {}


# Global transaction monitor instance
_transaction_monitor: Optional[TransactionMonitor] = None


def get_transaction_monitor() -> Optional[TransactionMonitor]:
    """Get global transaction monitor instance"""
    return _transaction_monitor


def create_transaction_monitor(evm_client, poll_interval: float = 2.0, timeout_minutes: int = 10) -> TransactionMonitor:
    """Create and initialize transaction monitor"""
    global _transaction_monitor
    _transaction_monitor = TransactionMonitor(evm_client, poll_interval, timeout_minutes)
    return _transaction_monitor


async def cleanup_transaction_monitor():
    """Cleanup transaction monitor"""
    global _transaction_monitor
    if _transaction_monitor:
        await _transaction_monitor.stop_monitoring()
        _transaction_monitor = None


if __name__ == "__main__":
    async def test_transaction_monitor():
        """Test transaction monitor"""
        from .evm_client import EVMClient
        
        # Mock EVM client for testing
        evm_client = EVMClient("http://localhost:8545")
        
        # Create transaction monitor
        monitor = create_transaction_monitor(evm_client)
        
        try:
            # Start monitoring
            await monitor.start_monitoring()
            
            # Test callback
            def test_callback(tx_info: TransactionInfo, event: TransactionEvent):
                print(f"Callback triggered: {tx_info.tx_hash} - {event.value}")
            
            # Monitor a transaction
            tx_info = await monitor.monitor_transaction(
                tx_hash="0x1234567890123456789012345678901234567890",
                contract_address="0xabcdef1234567890123456789012345678901234",
                function_name="testFunction",
                gas_limit=100000,
                gas_price=20000000000
            )
            
            # Add callback
            await monitor.add_callback(tx_info.tx_hash, test_callback)
            
            print(f"Monitoring transaction: {tx_info.tx_hash}")
            
            # Wait for some monitoring
            await asyncio.sleep(5)
            
            # Get stats
            stats = monitor.get_monitoring_stats()
            print(f"Monitoring stats: {stats}")
            
        finally:
            await monitor.stop_monitoring()
            await evm_client.close()
    
    # Run test
    asyncio.run(test_transaction_monitor())
