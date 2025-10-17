"""
Database Data Models Package

Pydantic models for Lucid database entities:
- User models
- Session models
- Block models (lucid_blocks blockchain)
- Transaction models
- Trust policy models
- Wallet models

All models follow the Lucid API architecture standards
and provide validation, serialization, and type safety.
"""

from .user import User, UserCreate, UserUpdate, UserInDB
from .session import Session, SessionCreate, SessionUpdate, SessionInDB
from .block import Block, BlockCreate, BlockHeader, BlockInDB
from .transaction import Transaction, TransactionCreate, TransactionInDB
from .trust_policy import TrustPolicy, TrustPolicyCreate, TrustPolicyUpdate, TrustPolicyInDB
from .wallet import Wallet, WalletCreate, WalletUpdate, WalletInDB, HardwareWallet

__all__ = [
    # User models
    'User',
    'UserCreate',
    'UserUpdate',
    'UserInDB',
    # Session models
    'Session',
    'SessionCreate',
    'SessionUpdate',
    'SessionInDB',
    # Block models
    'Block',
    'BlockCreate',
    'BlockHeader',
    'BlockInDB',
    # Transaction models
    'Transaction',
    'TransactionCreate',
    'TransactionInDB',
    # Trust policy models
    'TrustPolicy',
    'TrustPolicyCreate',
    'TrustPolicyUpdate',
    'TrustPolicyInDB',
    # Wallet models
    'Wallet',
    'WalletCreate',
    'WalletUpdate',
    'WalletInDB',
    'HardwareWallet',
]

__version__ = '1.0.0'

