"""
Input validation utilities
"""

import re
from typing import Optional
from gui_hardware_manager.utils.errors import InvalidTransactionError


def validate_hex_string(value: str, name: str = "hex string") -> str:
    """Validate hex string format"""
    if not re.match(r'^0x[0-9a-fA-F]*$', value):
        raise ValueError(f"Invalid {name}: must be valid hex format")
    return value


def validate_transaction_hex(tx_hex: str) -> str:
    """Validate transaction hex format"""
    if not tx_hex:
        raise InvalidTransactionError("Transaction cannot be empty")
    
    if not tx_hex.startswith("0x"):
        raise InvalidTransactionError("Transaction must start with 0x")
    
    if len(tx_hex) % 2 != 0:
        raise InvalidTransactionError("Transaction must be valid hex (even length)")
    
    try:
        int(tx_hex, 16)
    except ValueError:
        raise InvalidTransactionError("Transaction contains invalid hex characters")
    
    return tx_hex


def validate_device_id(device_id: str) -> str:
    """Validate device ID format"""
    if not device_id or len(device_id) == 0:
        raise ValueError("Device ID cannot be empty")
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', device_id):
        raise ValueError("Device ID contains invalid characters")
    
    return device_id


def validate_wallet_id(wallet_id: str) -> str:
    """Validate wallet ID format"""
    if not wallet_id or len(wallet_id) == 0:
        raise ValueError("Wallet ID cannot be empty")
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', wallet_id):
        raise ValueError("Wallet ID contains invalid characters")
    
    return wallet_id
