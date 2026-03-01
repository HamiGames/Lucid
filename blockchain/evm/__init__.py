"""
EVM (Ethereum Virtual Machine) Components
On-System Chain EVM-compatible client and utilities

This module provides:
- EVMClient: JSON-RPC interface to On-System Chain
- ContractCall: Contract function call utilities
- Transaction monitoring and status checking
- Gas estimation and circuit breakers
"""

from .evm_client import EVMClient, ContractCall, ContractEvent, TransactionStatus
from .gas_estimator import GasEstimator
from .transaction_monitor import TransactionMonitor

__all__ = [
    'EVMClient', 'ContractCall', 'ContractEvent', 'TransactionStatus',
    'GasEstimator', 'TransactionMonitor'
]
