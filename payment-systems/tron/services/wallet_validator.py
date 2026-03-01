"""
Wallet Validation Service
Validates wallet addresses, private keys, and transaction data
"""

import logging
import re
from typing import Optional, Dict, Any, Tuple
from tronpy.keys import PrivateKey, PublicKey
from tronpy.providers import HTTPProvider


logger = logging.getLogger(__name__)


class WalletValidator:
    """Service for wallet validation"""
    
    # TRON address pattern: T followed by 33 alphanumeric characters
    TRON_ADDRESS_PATTERN = re.compile(r'^T[1-9A-HJ-NP-Za-km-z]{33}$')
    
    # Private key pattern: 64 hex characters
    PRIVATE_KEY_PATTERN = re.compile(r'^[0-9a-fA-F]{64}$')
    
    def __init__(self, tron_provider: Optional[HTTPProvider] = None):
        """Initialize validator"""
        self.tron_provider = tron_provider
    
    def validate_address(self, address: str) -> Tuple[bool, Optional[str]]:
        """Validate TRON address format"""
        try:
            if not address:
                return False, "Address is empty"
            
            if not isinstance(address, str):
                return False, "Address must be a string"
            
            if len(address) != 34:
                return False, f"Address length must be 34 characters, got {len(address)}"
            
            if not self.TRON_ADDRESS_PATTERN.match(address):
                return False, "Address format is invalid (must start with T and contain 33 valid characters)"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating address: {e}")
            return False, str(e)
    
    def validate_private_key(self, private_key: str) -> Tuple[bool, Optional[str]]:
        """Validate private key format"""
        try:
            if not private_key:
                return False, "Private key is empty"
            
            if not isinstance(private_key, str):
                return False, "Private key must be a string"
            
            # Check hex format
            if not self.PRIVATE_KEY_PATTERN.match(private_key):
                return False, "Private key must be 64 hex characters"
            
            # Try to create PrivateKey object to validate
            try:
                PrivateKey(bytes.fromhex(private_key))
            except Exception as e:
                return False, f"Invalid private key format: {str(e)}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating private key: {e}")
            return False, str(e)
    
    def validate_address_and_key_match(
        self,
        address: str,
        private_key: str
    ) -> Tuple[bool, Optional[str]]:
        """Validate that address matches private key"""
        try:
            # Validate address format
            valid, error = self.validate_address(address)
            if not valid:
                return False, f"Invalid address: {error}"
            
            # Validate private key format
            valid, error = self.validate_private_key(private_key)
            if not valid:
                return False, f"Invalid private key: {error}"
            
            # Derive address from private key
            try:
                priv_key = PrivateKey(bytes.fromhex(private_key))
                derived_address = priv_key.public_key.to_base58check_address()
                
                if derived_address != address:
                    return False, "Address does not match private key"
                
                return True, None
                
            except Exception as e:
                return False, f"Failed to derive address from private key: {str(e)}"
            
        except Exception as e:
            logger.error(f"Error validating address/key match: {e}")
            return False, str(e)
    
    def validate_amount(self, amount: float, min_amount: float = 0.000001, max_amount: float = 1000000.0) -> Tuple[bool, Optional[str]]:
        """Validate transaction amount"""
        try:
            if not isinstance(amount, (int, float)):
                return False, "Amount must be a number"
            
            if amount < min_amount:
                return False, f"Amount must be at least {min_amount} TRX"
            
            if amount > max_amount:
                return False, f"Amount must not exceed {max_amount} TRX"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating amount: {e}")
            return False, str(e)
    
    def validate_wallet_data(self, wallet_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Validate wallet data structure"""
        try:
            required_fields = ["wallet_id", "address", "wallet_type", "status"]
            
            for field in required_fields:
                if field not in wallet_data:
                    return False, f"Missing required field: {field}"
            
            # Validate address
            valid, error = self.validate_address(wallet_data["address"])
            if not valid:
                return False, f"Invalid address: {error}"
            
            # Validate wallet_type
            valid_types = ["hot", "cold", "warm"]
            if wallet_data["wallet_type"] not in valid_types:
                return False, f"Invalid wallet_type: must be one of {valid_types}"
            
            # Validate status
            valid_statuses = ["active", "inactive", "locked", "deleted"]
            if wallet_data["status"] not in valid_statuses:
                return False, f"Invalid status: must be one of {valid_statuses}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating wallet data: {e}")
            return False, str(e)

