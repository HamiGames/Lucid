"""
LUCID Payment Systems - Wallet Module
Unified wallet integration and management system for payment operations

This module provides comprehensive wallet integration capabilities including:
- Software wallets (Ed25519)
- Hardware wallet integration
- Multi-signature wallets
- TRON native wallets
- External wallet integration

Distroless container: pickme/lucid:payment-systems:latest
"""

from .integration_manager import (
    # Core classes
    WalletType,
    WalletRole,
    WalletStatus,
    IntegrationStatus,
    WalletInfo,
    WalletCredentials,
    TransactionRequest,
    TransactionResult,
    WalletIntegrationRequest,
    WalletIntegrationResponse,
    WalletIntegrationManager,
    
    # Global instance
    wallet_integration_manager,
    
    # Convenience functions
    register_wallet,
    connect_wallet,
    disconnect_wallet,
    execute_transaction,
    get_wallet_balance,
    list_wallets,
    get_transaction_history,
)

# Version information
__version__ = "1.0.0"
__author__ = "HamiGames/Lucid Team"
__description__ = "Unified wallet integration and management system"

# Public API exports
__all__ = [
    # Enums
    "WalletType",
    "WalletRole", 
    "WalletStatus",
    "IntegrationStatus",
    
    # Data classes
    "WalletInfo",
    "WalletCredentials",
    "TransactionRequest",
    "TransactionResult",
    
    # Request/Response models
    "WalletIntegrationRequest",
    "WalletIntegrationResponse",
    
    # Core manager
    "WalletIntegrationManager",
    "wallet_integration_manager",
    
    # Convenience functions
    "register_wallet",
    "connect_wallet", 
    "disconnect_wallet",
    "execute_transaction",
    "get_wallet_balance",
    "list_wallets",
    "get_transaction_history",
    
    # Metadata
    "__version__",
    "__author__",
    "__description__",
]

# Module initialization
import logging

# Configure module-level logging
logger = logging.getLogger(__name__)

def get_wallet_module_info():
    """Get wallet module information"""
    return {
        "module": "lucid.payment_systems.wallet",
        "version": __version__,
        "description": __description__,
        "author": __author__,
        "supported_wallet_types": [wt.value for wt in WalletType],
        "supported_roles": [wr.value for wr in WalletRole],
        "supported_statuses": [ws.value for ws in WalletStatus],
    }

def initialize_wallet_system():
    """Initialize the wallet integration system"""
    try:
        logger.info("Initializing LUCID Wallet Integration System")
        logger.info(f"Module version: {__version__}")
        logger.info(f"Supported wallet types: {[wt.value for wt in WalletType]}")
        logger.info(f"Supported roles: {[wr.value for wr in WalletRole]}")
        
        # The global wallet_integration_manager is automatically initialized
        # when the module is imported via its __init__ method
        
        logger.info("Wallet Integration System initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize wallet system: {e}")
        return False

# Auto-initialize on import
_initialized = initialize_wallet_system()
