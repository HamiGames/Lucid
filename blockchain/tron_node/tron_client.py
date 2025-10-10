#!/usr/bin/env python3
"""
LUCID TRON Node Client - Legacy Compatibility
Provides backward compatibility for existing TRON client imports

NOTE: This is a compatibility layer. The main TRON functionality
has been moved to blockchain/core/tron_node_system.py for the
new dual-chain architecture.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Import the new TronNodeSystem for actual functionality
from ..core.tron_node_system import TronNodeSystem, create_tron_node_system
from ..core.models import (
    TronTransaction, USDTBalance, TronNetwork, TransactionStatus,
    PayoutRouter, PayoutRequest, PayoutResult
)

logger = logging.getLogger(__name__)


@dataclass
class PayoutRecord:
    """Legacy payout record for backward compatibility"""
    session_id: str
    recipient_address: str
    amount_usdt: float
    router_type: str
    txid: Optional[str] = None
    status: str = "pending"
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)


class TronNodeClient:
    """
    Legacy TRON client for backward compatibility.
    
    This class provides a compatibility layer for existing code that
    imports TronNodeClient. It delegates to the new TronNodeSystem
    which is the actual implementation in the rebuilt architecture.
    """
    
    def __init__(self, network: str = "shasta"):
        self.network = network
        self._tron_system: Optional[TronNodeSystem] = None
        logger.warning(
            "TronNodeClient is deprecated. Use TronNodeSystem from "
            "blockchain.core.tron_node_system instead."
        )
    
    async def connect(self) -> bool:
        """Connect to TRON network"""
        if not self._tron_system:
            self._tron_system = await create_tron_node_system(
                network=self.network
            )
        return await self._tron_system.connect()
    
    async def get_usdt_balance(self, address: str) -> float:
        """Get USDT balance for an address"""
        if not self._tron_system:
            await self.connect()
        return await self._tron_system.get_usdt_balance(address)
    
    async def send_usdt_payout(
        self,
        session_id: str,
        recipient_address: str,
        amount_usdt: float,
        router_type: str = "PayoutRouterV0",
        reason: str = "session_payout"
    ) -> Dict[str, Any]:
        """Send USDT payout (legacy method)"""
        if not self._tron_system:
            await self.connect()
        
        # Convert legacy parameters to new format
        payout_request = PayoutRequest(
            session_id=session_id,
            to_address=recipient_address,
            usdt_amount=amount_usdt,
            router_type=PayoutRouter(router_type),
            reason=reason
        )
        
        result = await self._tron_system.send_usdt_payout(payout_request)
        
        # Convert result to legacy format
        return {
            "txid": result.txid,
            "status": result.status,
            "error": result.error,
            "router": result.router
        }
    
    async def get_transaction_status(self, txid: str) -> Dict[str, Any]:
        """Get transaction status"""
        if not self._tron_system:
            await self.connect()
        
        return await self._tron_system.get_payout_status(txid)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        if not self._tron_system:
            await self.connect()
        
        return await self._tron_system.health_check()
    
    async def close(self):
        """Close connection"""
        if self._tron_system:
            await self._tron_system.close()


# Legacy factory functions for backward compatibility
async def create_tron_client(network: str = "shasta") -> TronNodeClient:
    """Create TRON client (legacy compatibility)"""
    client = TronNodeClient(network=network)
    await client.connect()
    return client


def get_tron_network_info(network: str = "shasta") -> TronNetwork:
    """Get TRON network information"""
    return TronNetwork(
        name=network,
        rpc_url="https://api.shasta.trongrid.io" if network == "shasta" else "https://api.trongrid.io"
    )


# Export all the required classes for backward compatibility
__all__ = [
    'TronNodeClient',
    'TronTransaction', 
    'PayoutRecord',
    'USDTBalance',
    'TronNetwork',
    'TransactionStatus',
    'create_tron_client',
    'get_tron_network_info'
]
