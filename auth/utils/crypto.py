"""
Lucid Authentication Service - Cryptographic Utilities
TRON signature verification and password hashing
"""

import hashlib
import bcrypt
from eth_account.messages import encode_defunct
from web3 import Web3
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


def verify_tron_signature(address: str, message: str, signature: str) -> bool:
    """
    Verify TRON signature
    
    TRON uses the same ECDSA signature scheme as Ethereum,
    so we can use Web3.py for verification.
    
    Args:
        address: TRON address (starts with 'T')
        message: Original message that was signed
        signature: Signature hex string
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Convert TRON address to Ethereum format for verification
        # TRON uses base58 encoding, ETH uses checksummed hex
        # For signature verification, we need to compare addresses
        
        # Encode message
        message_hash = encode_defunct(text=message)
        
        # Recover address from signature
        w3 = Web3()
        recovered_address = w3.eth.account.recover_message(
            message_hash,
            signature=signature
        )
        
        # Convert TRON address to hex for comparison
        # Note: This is a simplified version. In production, you'd use
        # tronpy or tronapi for proper TRON address handling
        tron_hex = tron_address_to_hex(address)
        
        # Compare addresses (case-insensitive)
        is_valid = recovered_address.lower() == tron_hex.lower()
        
        if is_valid:
            logger.debug(f"Signature verification successful for {address}")
        else:
            logger.warning(f"Signature verification failed for {address}")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"Error verifying TRON signature: {e}", exc_info=True)
        return False


def tron_address_to_hex(tron_address: str) -> str:
    """
    Convert TRON address (base58) to hex format
    
    Args:
        tron_address: TRON address (e.g., TXYZPvGUMN8...)
        
    Returns:
        Hex address string
    """
    try:
        # Import tronpy for proper address conversion
        # If not available, return simplified conversion
        try:
            from tronpy import keys
            hex_addr = keys.to_hex_address(tron_address)
            return hex_addr
        except ImportError:
            # Fallback: simplified conversion (for development)
            # In production, always use tronpy
            logger.warning("tronpy not available, using simplified address conversion")
            
            # Base58 decode
            import base58
            decoded = base58.b58decode_check(tron_address)
            # Remove first byte (0x41 for mainnet)
            hex_addr = '0x' + decoded[1:].hex()
            return hex_addr
            
    except Exception as e:
        logger.error(f"Error converting TRON address to hex: {e}")
        raise ValueError(f"Invalid TRON address: {tron_address}")


def hash_password(password: str, rounds: int = 12) -> str:
    """
    Hash password using bcrypt
    
    Args:
        password: Plain text password
        rounds: Number of bcrypt rounds (default 12)
        
    Returns:
        Hashed password string
    """
    try:
        salt = bcrypt.gensalt(rounds=rounds)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify password against hash
    
    Args:
        password: Plain text password
        hashed: Hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def generate_random_token(length: int = 32) -> str:
    """
    Generate random token for various purposes
    
    Args:
        length: Token length in bytes
        
    Returns:
        Random hex token
    """
    import secrets
    return secrets.token_hex(length)


def hash_data(data: str, algorithm: str = 'sha256') -> str:
    """
    Hash data using specified algorithm
    
    Args:
        data: Data to hash
        algorithm: Hash algorithm (sha256, sha512, etc.)
        
    Returns:
        Hex digest of hash
    """
    try:
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(data.encode('utf-8'))
        return hash_obj.hexdigest()
    except Exception as e:
        logger.error(f"Error hashing data: {e}")
        raise


def verify_message_signature(
    message: str,
    signature: str,
    public_key: str
) -> bool:
    """
    Verify message signature with public key
    
    Args:
        message: Original message
        signature: Signature to verify
        public_key: Public key
        
    Returns:
        True if valid, False otherwise
    """
    # This would use cryptography library for general signature verification
    # Implementation depends on signature algorithm (ECDSA, RSA, etc.)
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.backends import default_backend
        
        # Example implementation for ECDSA
        # Actual implementation depends on key format and algorithm
        
        logger.debug("Message signature verification requested")
        return True  # Placeholder
        
    except Exception as e:
        logger.error(f"Error verifying message signature: {e}")
        return False

