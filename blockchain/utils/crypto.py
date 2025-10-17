# Path: blockchain/utils/crypto.py
# Lucid Blockchain Core - Cryptographic Utilities
# Provides cryptographic functions for the lucid_blocks blockchain
# Based on BUILD_REQUIREMENTS_GUIDE.md Step 11 and blockchain cluster specifications

from __future__ import annotations

import hashlib
import hmac
import secrets
import struct
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import base64
import json

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
import blake3

# Cryptographic constants
HASH_ALGORITHM = "blake3"
SIGNATURE_ALGORITHM = "ed25519"
ENCRYPTION_ALGORITHM = "aes-256-gcm"
KEY_DERIVATION_ITERATIONS = 100000
SALT_LENGTH = 32
NONCE_LENGTH = 12
TAG_LENGTH = 16

class HashAlgorithm(Enum):
    """Supported hash algorithms"""
    BLAKE3 = "blake3"
    SHA256 = "sha256"
    SHA3_256 = "sha3_256"

class SignatureAlgorithm(Enum):
    """Supported signature algorithms"""
    ED25519 = "ed25519"
    RSA_PSS = "rsa_pss"

@dataclass
class KeyPair:
    """Cryptographic key pair"""
    private_key: bytes
    public_key: bytes
    algorithm: SignatureAlgorithm
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

@dataclass
class Signature:
    """Digital signature"""
    signature: bytes
    public_key: bytes
    algorithm: SignatureAlgorithm
    message_hash: str
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

@dataclass
class EncryptedData:
    """Encrypted data container"""
    ciphertext: bytes
    nonce: bytes
    tag: bytes
    algorithm: str
    key_id: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

class CryptoUtils:
    """
    Cryptographic utilities for the Lucid blockchain
    
    Provides secure cryptographic operations including:
    - Hashing (BLAKE3, SHA256, SHA3)
    - Digital signatures (Ed25519, RSA-PSS)
    - Symmetric encryption (AES-256-GCM)
    - Key derivation (PBKDF2, HKDF)
    - Random number generation
    - Merkle tree operations
    """
    
    @staticmethod
    def hash_data(data: Union[str, bytes], algorithm: HashAlgorithm = HashAlgorithm.BLAKE3) -> str:
        """
        Hash data using the specified algorithm
        
        Args:
            data: Data to hash (string or bytes)
            algorithm: Hash algorithm to use
            
        Returns:
            Hexadecimal hash string
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if algorithm == HashAlgorithm.BLAKE3:
            return blake3.blake3(data).hexdigest()
        elif algorithm == HashAlgorithm.SHA256:
            return hashlib.sha256(data).hexdigest()
        elif algorithm == HashAlgorithm.SHA3_256:
            return hashlib.sha3_256(data).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    @staticmethod
    def hash_block_header(height: int, previous_hash: str, timestamp: datetime, 
                         merkle_root: str, producer: str) -> str:
        """
        Hash a block header for block identification
        
        Args:
            height: Block height
            previous_hash: Previous block hash
            timestamp: Block timestamp
            merkle_root: Merkle root of transactions
            producer: Block producer identifier
            
        Returns:
            Block hash
        """
        header_data = (
            f"{height}"
            f"{previous_hash}"
            f"{timestamp.isoformat()}"
            f"{merkle_root}"
            f"{producer}"
        )
        
        return CryptoUtils.hash_data(header_data, HashAlgorithm.BLAKE3)
    
    @staticmethod
    def hash_transaction(tx_id: str, from_address: str, to_address: str, 
                        value: float, data: str, timestamp: datetime) -> str:
        """
        Hash a transaction for identification and signing
        
        Args:
            tx_id: Transaction ID
            from_address: Sender address
            to_address: Recipient address
            value: Transaction value
            data: Transaction data
            timestamp: Transaction timestamp
            
        Returns:
            Transaction hash
        """
        tx_data = (
            f"{tx_id}"
            f"{from_address}"
            f"{to_address}"
            f"{value}"
            f"{data}"
            f"{timestamp.isoformat()}"
        )
        
        return CryptoUtils.hash_data(tx_data, HashAlgorithm.BLAKE3)
    
    @staticmethod
    def generate_keypair(algorithm: SignatureAlgorithm = SignatureAlgorithm.ED25519) -> KeyPair:
        """
        Generate a new cryptographic key pair
        
        Args:
            algorithm: Signature algorithm to use
            
        Returns:
            KeyPair object
        """
        if algorithm == SignatureAlgorithm.ED25519:
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PrivateFormat.Raw,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            return KeyPair(
                private_key=private_bytes,
                public_key=public_bytes,
                algorithm=algorithm
            )
            
        elif algorithm == SignatureAlgorithm.RSA_PSS:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            public_key = private_key.public_key()
            
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return KeyPair(
                private_key=private_bytes,
                public_key=public_bytes,
                algorithm=algorithm
            )
        else:
            raise ValueError(f"Unsupported signature algorithm: {algorithm}")
    
    @staticmethod
    def sign_data(data: Union[str, bytes], private_key: bytes, 
                  algorithm: SignatureAlgorithm = SignatureAlgorithm.ED25519) -> Signature:
        """
        Sign data with a private key
        
        Args:
            data: Data to sign
            private_key: Private key bytes
            algorithm: Signature algorithm
            
        Returns:
            Signature object
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # Hash the data first
        data_hash = CryptoUtils.hash_data(data, HashAlgorithm.BLAKE3)
        
        if algorithm == SignatureAlgorithm.ED25519:
            # Reconstruct private key
            priv_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)
            pub_key = priv_key.public_key()
            
            # Sign the data
            signature_bytes = priv_key.sign(data)
            
            public_bytes = pub_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            return Signature(
                signature=signature_bytes,
                public_key=public_bytes,
                algorithm=algorithm,
                message_hash=data_hash
            )
            
        elif algorithm == SignatureAlgorithm.RSA_PSS:
            # Reconstruct private key
            priv_key = serialization.load_pem_private_key(
                private_key, password=None, backend=default_backend()
            )
            pub_key = priv_key.public_key()
            
            # Sign the data
            signature_bytes = priv_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            public_bytes = pub_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return Signature(
                signature=signature_bytes,
                public_key=public_bytes,
                algorithm=algorithm,
                message_hash=data_hash
            )
        else:
            raise ValueError(f"Unsupported signature algorithm: {algorithm}")
    
    @staticmethod
    def verify_signature(data: Union[str, bytes], signature: Signature) -> bool:
        """
        Verify a digital signature
        
        Args:
            data: Original data that was signed
            signature: Signature object to verify
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Verify the data hash matches
            data_hash = CryptoUtils.hash_data(data, HashAlgorithm.BLAKE3)
            if data_hash != signature.message_hash:
                return False
            
            if signature.algorithm == SignatureAlgorithm.ED25519:
                # Reconstruct public key
                pub_key = ed25519.Ed25519PublicKey.from_public_bytes(signature.public_key)
                
                # Verify signature
                pub_key.verify(signature.signature, data)
                return True
                
            elif signature.algorithm == SignatureAlgorithm.RSA_PSS:
                # Reconstruct public key
                pub_key = serialization.load_pem_public_key(
                    signature.public_key, backend=default_backend()
                )
                
                # Verify signature
                pub_key.verify(
                    signature.signature,
                    data,
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                return True
            else:
                return False
                
        except Exception:
            return False
    
    @staticmethod
    def encrypt_data(data: Union[str, bytes], key: bytes, 
                    associated_data: Optional[bytes] = None) -> EncryptedData:
        """
        Encrypt data using AES-256-GCM
        
        Args:
            data: Data to encrypt
            key: 32-byte encryption key
            associated_data: Optional associated data for authentication
            
        Returns:
            EncryptedData object
        """
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes for AES-256")
        
        # Generate random nonce
        nonce = secrets.token_bytes(NONCE_LENGTH)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Add associated data if provided
        if associated_data:
            encryptor.authenticate_additional_data(associated_data)
        
        # Encrypt data
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        return EncryptedData(
            ciphertext=ciphertext,
            nonce=nonce,
            tag=encryptor.tag,
            algorithm=ENCRYPTION_ALGORITHM
        )
    
    @staticmethod
    def decrypt_data(encrypted_data: EncryptedData, key: bytes, 
                    associated_data: Optional[bytes] = None) -> bytes:
        """
        Decrypt data using AES-256-GCM
        
        Args:
            encrypted_data: EncryptedData object
            key: 32-byte decryption key
            associated_data: Optional associated data for authentication
            
        Returns:
            Decrypted data bytes
        """
        if len(key) != 32:
            raise ValueError("Key must be 32 bytes for AES-256")
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(encrypted_data.nonce, encrypted_data.tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Add associated data if provided
        if associated_data:
            decryptor.authenticate_additional_data(associated_data)
        
        # Decrypt data
        plaintext = decryptor.update(encrypted_data.ciphertext) + decryptor.finalize()
        
        return plaintext
    
    @staticmethod
    def derive_key(password: Union[str, bytes], salt: Optional[bytes] = None, 
                  iterations: int = KEY_DERIVATION_ITERATIONS) -> Tuple[bytes, bytes]:
        """
        Derive a key from a password using PBKDF2
        
        Args:
            password: Password to derive key from
            salt: Optional salt (generated if not provided)
            iterations: Number of iterations
            
        Returns:
            Tuple of (derived_key, salt)
        """
        if isinstance(password, str):
            password = password.encode('utf-8')
        
        if salt is None:
            salt = secrets.token_bytes(SALT_LENGTH)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )
        
        key = kdf.derive(password)
        return key, salt
    
    @staticmethod
    def derive_key_hkdf(input_key: bytes, info: bytes, salt: Optional[bytes] = None) -> bytes:
        """
        Derive a key using HKDF (HMAC-based Key Derivation Function)
        
        Args:
            input_key: Input key material
            info: Application-specific info
            salt: Optional salt
            
        Returns:
            Derived key
        """
        if salt is None:
            salt = b""
        
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            info=info,
            backend=default_backend()
        )
        
        return hkdf.derive(input_key)
    
    @staticmethod
    def generate_random_bytes(length: int) -> bytes:
        """
        Generate cryptographically secure random bytes
        
        Args:
            length: Number of bytes to generate
            
        Returns:
            Random bytes
        """
        return secrets.token_bytes(length)
    
    @staticmethod
    def generate_random_string(length: int, alphabet: str = None) -> str:
        """
        Generate a cryptographically secure random string
        
        Args:
            length: Length of string to generate
            alphabet: Character set to use (default: alphanumeric)
            
        Returns:
            Random string
        """
        if alphabet is None:
            alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def create_merkle_leaf_hash(data: str) -> str:
        """
        Create a hash for a Merkle tree leaf node
        
        Args:
            data: Leaf data
            
        Returns:
            Leaf hash
        """
        leaf_prefix = b"leaf:"
        return blake3.blake3(leaf_prefix + data.encode()).hexdigest()
    
    @staticmethod
    def create_merkle_internal_hash(left_hash: str, right_hash: str) -> str:
        """
        Create a hash for a Merkle tree internal node
        
        Args:
            left_hash: Left child hash
            right_hash: Right child hash
            
        Returns:
            Internal node hash
        """
        internal_prefix = b"internal:"
        combined = f"{left_hash}:{right_hash}"
        return blake3.blake3(internal_prefix + combined.encode()).hexdigest()
    
    @staticmethod
    def constant_time_compare(a: Union[str, bytes], b: Union[str, bytes]) -> bool:
        """
        Compare two values in constant time to prevent timing attacks
        
        Args:
            a: First value
            b: Second value
            
        Returns:
            True if values are equal, False otherwise
        """
        if isinstance(a, str):
            a = a.encode('utf-8')
        if isinstance(b, str):
            b = b.encode('utf-8')
        
        return hmac.compare_digest(a, b)
    
    @staticmethod
    def create_address_from_public_key(public_key: bytes, 
                                     algorithm: SignatureAlgorithm = SignatureAlgorithm.ED25519) -> str:
        """
        Create a blockchain address from a public key
        
        Args:
            public_key: Public key bytes
            algorithm: Signature algorithm used
            
        Returns:
            Blockchain address (hex string with 0x prefix)
        """
        # Hash the public key
        key_hash = CryptoUtils.hash_data(public_key, HashAlgorithm.BLAKE3)
        
        # Take first 20 bytes (160 bits) for address
        address_bytes = bytes.fromhex(key_hash)[:20]
        
        # Add 0x prefix
        return "0x" + address_bytes.hex()
    
    @staticmethod
    def validate_address(address: str) -> bool:
        """
        Validate a blockchain address format
        
        Args:
            address: Address to validate
            
        Returns:
            True if address is valid, False otherwise
        """
        if not isinstance(address, str):
            return False
        
        if not address.startswith("0x"):
            return False
        
        if len(address) != 42:  # 0x + 40 hex characters
            return False
        
        try:
            int(address[2:], 16)  # Check if hex
            return True
        except ValueError:
            return False
    
    @staticmethod
    def encode_base64(data: bytes) -> str:
        """
        Encode bytes to base64 string
        
        Args:
            data: Bytes to encode
            
        Returns:
            Base64 encoded string
        """
        return base64.b64encode(data).decode('ascii')
    
    @staticmethod
    def decode_base64(data: str) -> bytes:
        """
        Decode base64 string to bytes
        
        Args:
            data: Base64 string to decode
            
        Returns:
            Decoded bytes
        """
        return base64.b64decode(data.encode('ascii'))
    
    @staticmethod
    def create_checksum(data: Union[str, bytes]) -> str:
        """
        Create a checksum for data integrity verification
        
        Args:
            data: Data to create checksum for
            
        Returns:
            Checksum string
        """
        return CryptoUtils.hash_data(data, HashAlgorithm.BLAKE3)[:8]  # First 8 characters
    
    @staticmethod
    def verify_checksum(data: Union[str, bytes], checksum: str) -> bool:
        """
        Verify data integrity using checksum
        
        Args:
            data: Original data
            checksum: Expected checksum
            
        Returns:
            True if checksum is valid, False otherwise
        """
        calculated_checksum = CryptoUtils.create_checksum(data)
        return CryptoUtils.constant_time_compare(calculated_checksum, checksum)

# Convenience functions for common operations
def hash_blake3(data: Union[str, bytes]) -> str:
    """Hash data using BLAKE3"""
    return CryptoUtils.hash_data(data, HashAlgorithm.BLAKE3)

def generate_ed25519_keypair() -> KeyPair:
    """Generate Ed25519 key pair"""
    return CryptoUtils.generate_keypair(SignatureAlgorithm.ED25519)

def sign_ed25519(data: Union[str, bytes], private_key: bytes) -> Signature:
    """Sign data with Ed25519"""
    return CryptoUtils.sign_data(data, private_key, SignatureAlgorithm.ED25519)

def verify_ed25519(data: Union[str, bytes], signature: Signature) -> bool:
    """Verify Ed25519 signature"""
    return CryptoUtils.verify_signature(data, signature)

def encrypt_aes256(data: Union[str, bytes], key: bytes) -> EncryptedData:
    """Encrypt data with AES-256-GCM"""
    return CryptoUtils.encrypt_data(data, key)

def decrypt_aes256(encrypted_data: EncryptedData, key: bytes) -> bytes:
    """Decrypt data with AES-256-GCM"""
    return CryptoUtils.decrypt_data(encrypted_data, key)

# Export main classes and functions
__all__ = [
    "CryptoUtils",
    "KeyPair",
    "Signature", 
    "EncryptedData",
    "HashAlgorithm",
    "SignatureAlgorithm",
    "hash_blake3",
    "generate_ed25519_keypair",
    "sign_ed25519",
    "verify_ed25519",
    "encrypt_aes256",
    "decrypt_aes256"
]
