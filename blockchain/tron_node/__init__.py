"""
LUCID TRON Node Components - Payment Service Only
REBUILT: Isolated TRON integration for USDT-TRC20 payouts only

This module provides backward compatibility for existing TRON client imports.
The main TRON functionality has been moved to blockchain.core.tron_node_system
for the new dual-chain architecture where TRON is isolated to payment operations only.

No blockchain consensus or session anchoring is handled here.
"""

from .tron_client import (
    TronNodeClient, 
    TronTransaction, 
    PayoutRecord, 
    USDTBalance, 
    TronNetwork, 
    TransactionStatus,
    create_tron_client,
    get_tron_network_info
)

# Re-export core TRON system for direct access
from ..core.tron_node_system import TronNodeSystem, create_tron_node_system
from ..core.models import PayoutRequest, PayoutResult

__all__ = [
    # Legacy client (backward compatibility)
    'TronNodeClient', 
    'TronTransaction', 
    'PayoutRecord', 
    'USDTBalance', 
    'TronNetwork', 
    'TransactionStatus',
    'create_tron_client',
    'get_tron_network_info',
    
    # New core system (recommended)
    'TronNodeSystem',
    'create_tron_node_system',
    'PayoutRequest',
    'PayoutResult'
]
