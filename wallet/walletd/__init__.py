"""
Wallet Daemon Module

This module provides hardware wallet management, key rotation, keystore management,
multisig management, role management, and software vault functionality for the Lucid project.

Distroless-compliant module structure following Python package standards.
"""

from .hardware_wallet import HardwareWallet
from .key_rotation import KeyRotation
from .keystore_manager import KeystoreManager
from .multisig_manager import MultisigManager
from .role_manager import RoleManager
from .software_vault import SoftwareVault

__all__ = [
    'HardwareWallet',
    'KeyRotation', 
    'KeystoreManager',
    'MultisigManager',
    'RoleManager',
    'SoftwareVault'
]

__version__ = '1.0.0'
