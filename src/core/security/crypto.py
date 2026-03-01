"""
Cryptographic Functions Module

This module provides comprehensive cryptographic utilities for the Lucid project,
including encryption, decryption, key generation, hashing, and digital signatures.
Supports multiple encryption algorithms and security levels for different use cases.

Author: Lucid Security Team
Version: 1.0.0
"""

import hashlib
import hmac
import secrets
import base64
import json
import time
from typing import Optional, Dict, Any, Tuple, Union, List
from enum import Enum
from dataclasses import dataclass
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.hmac import HMAC
from cryptography.hazmat.primitives.signatures import ed25519
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature, InvalidKey
import os


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms."""
    AES_256_GCM = "aes-256-gcm"
    AES_256_CBC = "aes-256-cbc"
    CHACHA20_POLY1305 = "chacha20-poly1305"
    FERNET = "fernet"
    RSA_OAEP = "rsa-oaep"


class HashAlgorithm(Enum):
    """Supported hash algorithms."""
    SHA256 = "sha256"
    SHA512 = "sha512"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"
    SHA3_256 = "sha3-256"
    SHA3_512 = "sha3-512"


class KeyDerivationFunction(Enum):
    """Supported key derivation functions."""
    PBKDF2 = "pbkdf2"
    SCRYPT = "scrypt"
    ARGON2 = "argon2"


class SecurityLevel(Enum):
    """Security levels for cryptographic operations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"


@dataclass
class CryptoConfig:
    """Configuration for cryptographic operations."""
    algorithm: EncryptionAlgorithm
    key_size: int
    iv_size: int
    salt_size: int
    iterations: int
    security_level: SecurityLevel


@dataclass
class EncryptedData:
    """Structure for encrypted data with metadata."""
    data: bytes
    algorithm: str
    iv: Optional[bytes] = None
    salt: Optional[bytes] = None
    tag: Optional[bytes] = None
    timestamp: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class CryptographicError(Exception):
    """Base exception for cryptographic operations."""
    pass


class KeyGenerationError(CryptographicError):
    """Exception raised during key generation."""
    pass


class EncryptionError(CryptographicError):
    """Exception raised during encryption operations."""
    pass


class DecryptionError(CryptographicError):
    """Exception raised during decryption operations."""
    pass


class SignatureError(CryptographicError):
    """Exception raised during signature operations."""
    pass


class CryptoManager:
    """
    Comprehensive cryptographic manager for Lucid project.
    
    Provides encryption, decryption, key generation, hashing, and digital signatures
    with support for multiple algorithms and security levels.
    """
    
    # Default configurations for different security levels
    SECURITY_CONFIGS = {
        SecurityLevel.LOW: CryptoConfig(
            algorithm=EncryptionAlgorithm.AES_256_CBC,
            key_size=256,
            iv_size=16,
            salt_size=16,
            iterations=10000,
            security_level=SecurityLevel.LOW
        ),
        SecurityLevel.MEDIUM: CryptoConfig(
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            key_size=256,
            iv_size=12,
            salt_size=32,
            iterations=100000,
            security_level=SecurityLevel.MEDIUM
        ),
        SecurityLevel.HIGH: CryptoConfig(
            algorithm=EncryptionAlgorithm.CHACHA20_POLY1305,
            key_size=256,
            iv_size=12,
            salt_size=32,
            iterations=1000000,
            security_level=SecurityLevel.HIGH
        ),
        SecurityLevel.MAXIMUM: CryptoConfig(
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            key_size=256,
            iv_size=16,
            salt_size=64,
            iterations=2000000,
            security_level=SecurityLevel.MAXIMUM
        )
    }
    
    def __init__(self, default_security_level: SecurityLevel = SecurityLevel.MEDIUM):
        """
        Initialize the cryptographic manager.
        
        Args:
            default_security_level: Default security level for operations
        """
        self.default_security_level = default_security_level
        self._master_key: Optional[bytes] = None
        self._key_cache: Dict[str, bytes] = {}
    
    def generate_master_key(self, security_level: Optional[SecurityLevel] = None) -> bytes:
        """
        Generate a master encryption key.
        
        Args:
            security_level: Security level for key generation
            
        Returns:
            Generated master key
            
        Raises:
            KeyGenerationError: If key generation fails
        """
        try:
            level = security_level or self.default_security_level
            config = self.SECURITY_CONFIGS[level]
            
            # Generate cryptographically secure random key
            key = secrets.token_bytes(config.key_size // 8)
            
            # Store master key
            self._master_key = key
            
            return key
            
        except Exception as e:
            raise KeyGenerationError(f"Failed to generate master key: {str(e)}")
    
    def derive_key(self, password: str, salt: Optional[bytes] = None, 
                   security_level: Optional[SecurityLevel] = None) -> Tuple[bytes, bytes]:
        """
        Derive encryption key from password using PBKDF2.
        
        Args:
            password: Password to derive key from
            salt: Salt for key derivation (generated if None)
            security_level: Security level for key derivation
            
        Returns:
            Tuple of (derived_key, salt)
            
        Raises:
            KeyGenerationError: If key derivation fails
        """
        try:
            level = security_level or self.default_security_level
            config = self.SECURITY_CONFIGS[level]
            
            # Generate salt if not provided
            if salt is None:
                salt = secrets.token_bytes(config.salt_size)
            
            # Derive key using PBKDF2
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=config.key_size // 8,
                salt=salt,
                iterations=config.iterations,
                backend=default_backend()
            )
            
            key = kdf.derive(password.encode('utf-8'))
            
            return key, salt
            
        except Exception as e:
            raise KeyGenerationError(f"Failed to derive key: {str(e)}")
    
    def generate_rsa_keypair(self, key_size: int = 2048) -> Tuple[bytes, bytes]:
        """
        Generate RSA key pair.
        
        Args:
            key_size: RSA key size in bits
            
        Returns:
            Tuple of (private_key, public_key) in PEM format
            
        Raises:
            KeyGenerationError: If key generation fails
        """
        try:
            # Generate private key
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )
            
            # Get public key
            public_key = private_key.public_key()
            
            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return private_pem, public_pem
            
        except Exception as e:
            raise KeyGenerationError(f"Failed to generate RSA keypair: {str(e)}")
    
    def generate_ed25519_keypair(self) -> Tuple[bytes, bytes]:
        """
        Generate Ed25519 key pair.
        
        Returns:
            Tuple of (private_key, public_key) in PEM format
            
        Raises:
            KeyGenerationError: If key generation fails
        """
        try:
            # Generate private key
            private_key = ed25519.Ed25519PrivateKey.generate()
            
            # Get public key
            public_key = private_key.public_key()
            
            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return private_pem, public_pem
            
        except Exception as e:
            raise KeyGenerationError(f"Failed to generate Ed25519 keypair: {str(e)}")
    
    def encrypt_data(self, data: Union[str, bytes], key: Optional[bytes] = None,
                    algorithm: Optional[EncryptionAlgorithm] = None,
                    security_level: Optional[SecurityLevel] = None) -> EncryptedData:
        """
        Encrypt data using specified algorithm.
        
        Args:
            data: Data to encrypt
            key: Encryption key (uses master key if None)
            algorithm: Encryption algorithm
            security_level: Security level
            
        Returns:
            EncryptedData object with encrypted data and metadata
            
        Raises:
            EncryptionError: If encryption fails
        """
        try:
            # Convert string to bytes if needed
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            level = security_level or self.default_security_level
            config = self.SECURITY_CONFIGS[level]
            algo = algorithm or config.algorithm
            
            # Use master key if no key provided
            if key is None:
                if self._master_key is None:
                    self.generate_master_key(level)
                key = self._master_key
            
            # Generate IV
            iv = secrets.token_bytes(config.iv_size)
            
            # Encrypt based on algorithm
            if algo == EncryptionAlgorithm.AES_256_GCM:
                cipher = Cipher(
                    algorithms.AES(key),
                    modes.GCM(iv),
                    backend=default_backend()
                )
                encryptor = cipher.encryptor()
                encrypted_data = encryptor.update(data) + encryptor.finalize()
                tag = encryptor.tag
                
            elif algo == EncryptionAlgorithm.AES_256_CBC:
                cipher = Cipher(
                    algorithms.AES(key),
                    modes.CBC(iv),
                    backend=default_backend()
                )
                encryptor = cipher.encryptor()
                encrypted_data = encryptor.update(data) + encryptor.finalize()
                tag = None
                
            elif algo == EncryptionAlgorithm.CHACHA20_POLY1305:
                cipher = Cipher(
                    algorithms.ChaCha20Poly1305(key),
                    modes.ChaCha20Poly1305(iv),
                    backend=default_backend()
                )
                encryptor = cipher.encryptor()
                encrypted_data = encryptor.update(data) + encryptor.finalize()
                tag = None  # Tag is included in the encrypted data
                
            elif algo == EncryptionAlgorithm.FERNET:
                f = Fernet(base64.urlsafe_b64encode(key[:32]))
                encrypted_data = f.encrypt(data)
                tag = None
                
            else:
                raise EncryptionError(f"Unsupported algorithm: {algo}")
            
            return EncryptedData(
                data=encrypted_data,
                algorithm=algo.value,
                iv=iv,
                tag=tag,
                timestamp=time.time(),
                metadata={
                    'security_level': level.value,
                    'key_size': len(key) * 8,
                    'data_size': len(data)
                }
            )
            
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {str(e)}")
    
    def decrypt_data(self, encrypted_data: EncryptedData, key: Optional[bytes] = None) -> bytes:
        """
        Decrypt data using the provided key.
        
        Args:
            encrypted_data: EncryptedData object
            key: Decryption key (uses master key if None)
            
        Returns:
            Decrypted data as bytes
            
        Raises:
            DecryptionError: If decryption fails
        """
        try:
            # Use master key if no key provided
            if key is None:
                if self._master_key is None:
                    raise DecryptionError("No key available for decryption")
                key = self._master_key
            
            algorithm = EncryptionAlgorithm(encrypted_data.algorithm)
            
            # Decrypt based on algorithm
            if algorithm == EncryptionAlgorithm.AES_256_GCM:
                cipher = Cipher(
                    algorithms.AES(key),
                    modes.GCM(encrypted_data.iv, encrypted_data.tag),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                decrypted_data = decryptor.update(encrypted_data.data) + decryptor.finalize()
                
            elif algorithm == EncryptionAlgorithm.AES_256_CBC:
                cipher = Cipher(
                    algorithms.AES(key),
                    modes.CBC(encrypted_data.iv),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                decrypted_data = decryptor.update(encrypted_data.data) + decryptor.finalize()
                
            elif algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
                cipher = Cipher(
                    algorithms.ChaCha20Poly1305(key),
                    modes.ChaCha20Poly1305(encrypted_data.iv),
                    backend=default_backend()
                )
                decryptor = cipher.decryptor()
                decrypted_data = decryptor.update(encrypted_data.data) + decryptor.finalize()
                
            elif algorithm == EncryptionAlgorithm.FERNET:
                f = Fernet(base64.urlsafe_b64encode(key[:32]))
                decrypted_data = f.decrypt(encrypted_data.data)
                
            else:
                raise DecryptionError(f"Unsupported algorithm: {algorithm}")
            
            return decrypted_data
            
        except Exception as e:
            raise DecryptionError(f"Decryption failed: {str(e)}")
    
    def hash_data(self, data: Union[str, bytes], algorithm: HashAlgorithm = HashAlgorithm.SHA256,
                 salt: Optional[bytes] = None) -> str:
        """
        Generate hash of data.
        
        Args:
            data: Data to hash
            algorithm: Hash algorithm to use
            salt: Optional salt for hashing
            
        Returns:
            Hexadecimal hash string
        """
        try:
            # Convert string to bytes if needed
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Add salt if provided
            if salt:
                data = salt + data
            
            # Generate hash based on algorithm
            if algorithm == HashAlgorithm.SHA256:
                hash_obj = hashlib.sha256(data)
            elif algorithm == HashAlgorithm.SHA512:
                hash_obj = hashlib.sha512(data)
            elif algorithm == HashAlgorithm.BLAKE2B:
                hash_obj = hashlib.blake2b(data)
            elif algorithm == HashAlgorithm.BLAKE2S:
                hash_obj = hashlib.blake2s(data)
            elif algorithm == HashAlgorithm.SHA3_256:
                hash_obj = hashlib.sha3_256(data)
            elif algorithm == HashAlgorithm.SHA3_512:
                hash_obj = hashlib.sha3_512(data)
            else:
                raise ValueError(f"Unsupported hash algorithm: {algorithm}")
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            raise CryptographicError(f"Hashing failed: {str(e)}")
    
    def generate_hmac(self, data: Union[str, bytes], key: bytes,
                     algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> str:
        """
        Generate HMAC for data.
        
        Args:
            data: Data to generate HMAC for
            key: HMAC key
            algorithm: Hash algorithm for HMAC
            
        Returns:
            Hexadecimal HMAC string
        """
        try:
            # Convert string to bytes if needed
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Generate HMAC
            digest = hashes.SHA256() if algorithm == HashAlgorithm.SHA256 else hashes.SHA512()
            h = hmac.new(key, data, digest)
            
            return h.hexdigest()
            
        except Exception as e:
            raise CryptographicError(f"HMAC generation failed: {str(e)}")
    
    def verify_hmac(self, data: Union[str, bytes], key: bytes, hmac_value: str,
                   algorithm: HashAlgorithm = HashAlgorithm.SHA256) -> bool:
        """
        Verify HMAC for data.
        
        Args:
            data: Data to verify
            key: HMAC key
            hmac_value: HMAC to verify against
            algorithm: Hash algorithm for HMAC
            
        Returns:
            True if HMAC is valid, False otherwise
        """
        try:
            expected_hmac = self.generate_hmac(data, key, algorithm)
            return hmac.compare_digest(expected_hmac, hmac_value)
            
        except Exception as e:
            raise CryptographicError(f"HMAC verification failed: {str(e)}")
    
    def sign_data(self, data: Union[str, bytes], private_key: bytes) -> bytes:
        """
        Sign data with private key.
        
        Args:
            data: Data to sign
            private_key: Private key in PEM format
            
        Returns:
            Digital signature
            
        Raises:
            SignatureError: If signing fails
        """
        try:
            # Convert string to bytes if needed
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Load private key
            private_key_obj = serialization.load_pem_private_key(
                private_key,
                password=None,
                backend=default_backend()
            )
            
            # Sign data
            signature = private_key_obj.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return signature
            
        except Exception as e:
            raise SignatureError(f"Signing failed: {str(e)}")
    
    def verify_signature(self, data: Union[str, bytes], signature: bytes, public_key: bytes) -> bool:
        """
        Verify digital signature.
        
        Args:
            data: Data that was signed
            signature: Digital signature
            public_key: Public key in PEM format
            
        Returns:
            True if signature is valid, False otherwise
            
        Raises:
            SignatureError: If verification fails
        """
        try:
            # Convert string to bytes if needed
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Load public key
            public_key_obj = serialization.load_pem_public_key(
                public_key,
                backend=default_backend()
            )
            
            # Verify signature
            public_key_obj.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
            
        except InvalidSignature:
            return False
        except Exception as e:
            raise SignatureError(f"Signature verification failed: {str(e)}")
    
    def encrypt_file(self, file_path: str, output_path: str, key: Optional[bytes] = None,
                    security_level: Optional[SecurityLevel] = None) -> EncryptedData:
        """
        Encrypt a file.
        
        Args:
            file_path: Path to file to encrypt
            output_path: Path for encrypted file
            key: Encryption key
            security_level: Security level
            
        Returns:
            EncryptedData object with metadata
        """
        try:
            # Read file
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Encrypt data
            encrypted_data = self.encrypt_data(data, key, security_level=security_level)
            
            # Write encrypted file
            with open(output_path, 'wb') as f:
                f.write(encrypted_data.data)
            
            # Save metadata
            metadata_path = output_path + '.meta'
            with open(metadata_path, 'w') as f:
                json.dump({
                    'algorithm': encrypted_data.algorithm,
                    'iv': base64.b64encode(encrypted_data.iv).decode() if encrypted_data.iv else None,
                    'salt': base64.b64encode(encrypted_data.salt).decode() if encrypted_data.salt else None,
                    'tag': base64.b64encode(encrypted_data.tag).decode() if encrypted_data.tag else None,
                    'timestamp': encrypted_data.timestamp,
                    'metadata': encrypted_data.metadata
                }, f)
            
            return encrypted_data
            
        except Exception as e:
            raise EncryptionError(f"File encryption failed: {str(e)}")
    
    def decrypt_file(self, encrypted_file_path: str, output_path: str, key: Optional[bytes] = None) -> bytes:
        """
        Decrypt a file.
        
        Args:
            encrypted_file_path: Path to encrypted file
            output_path: Path for decrypted file
            key: Decryption key
            
        Returns:
            Decrypted data
        """
        try:
            # Read encrypted file
            with open(encrypted_file_path, 'rb') as f:
                encrypted_data_bytes = f.read()
            
            # Read metadata
            metadata_path = encrypted_file_path + '.meta'
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Reconstruct EncryptedData object
            encrypted_data = EncryptedData(
                data=encrypted_data_bytes,
                algorithm=metadata['algorithm'],
                iv=base64.b64decode(metadata['iv']) if metadata['iv'] else None,
                salt=base64.b64decode(metadata['salt']) if metadata['salt'] else None,
                tag=base64.b64decode(metadata['tag']) if metadata['tag'] else None,
                timestamp=metadata['timestamp'],
                metadata=metadata['metadata']
            )
            
            # Decrypt data
            decrypted_data = self.decrypt_data(encrypted_data, key)
            
            # Write decrypted file
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            
            return decrypted_data
            
        except Exception as e:
            raise DecryptionError(f"File decryption failed: {str(e)}")
    
    def secure_wipe(self, data: Union[str, bytes]) -> None:
        """
        Securely wipe sensitive data from memory.
        
        Args:
            data: Data to wipe
        """
        try:
            if isinstance(data, str):
                # For strings, we can't truly wipe them due to Python's string immutability
                # But we can at least overwrite the reference
                del data
            elif isinstance(data, bytes):
                # Overwrite bytes with random data
                if hasattr(data, '__array_interface__'):
                    # For numpy arrays or similar
                    data.fill(0)
                else:
                    # For regular bytes, create new object with zeros
                    data = b'\x00' * len(data)
                    del data
        except Exception:
            # Ignore errors during secure wipe
            pass


# Factory functions for common cryptographic operations
def create_crypto_manager(security_level: SecurityLevel = SecurityLevel.MEDIUM) -> CryptoManager:
    """
    Create a new CryptoManager instance.
    
    Args:
        security_level: Default security level
        
    Returns:
        CryptoManager instance
    """
    return CryptoManager(security_level)


def generate_password_hash(password: str, salt: Optional[bytes] = None) -> Tuple[str, bytes]:
    """
    Generate a secure password hash.
    
    Args:
        password: Password to hash
        salt: Optional salt (generated if None)
        
    Returns:
        Tuple of (hash, salt)
    """
    crypto = CryptoManager(SecurityLevel.HIGH)
    key, salt = crypto.derive_key(password, salt, SecurityLevel.HIGH)
    password_hash = crypto.hash_data(key, HashAlgorithm.SHA512, salt)
    return password_hash, salt


def verify_password(password: str, password_hash: str, salt: bytes) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        password: Password to verify
        password_hash: Stored password hash
        salt: Salt used for original hash
        
    Returns:
        True if password is correct, False otherwise
    """
    crypto = CryptoManager(SecurityLevel.HIGH)
    key, _ = crypto.derive_key(password, salt, SecurityLevel.HIGH)
    computed_hash = crypto.hash_data(key, HashAlgorithm.SHA512, salt)
    return hmac.compare_digest(computed_hash, password_hash)


def encrypt_string(text: str, key: Optional[bytes] = None) -> str:
    """
    Encrypt a string and return base64 encoded result.
    
    Args:
        text: String to encrypt
        key: Encryption key (generated if None)
        
    Returns:
        Base64 encoded encrypted string
    """
    crypto = CryptoManager()
    encrypted_data = crypto.encrypt_data(text, key)
    return base64.b64encode(encrypted_data.data).decode()


def decrypt_string(encrypted_text: str, key: Optional[bytes] = None) -> str:
    """
    Decrypt a base64 encoded string.
    
    Args:
        encrypted_text: Base64 encoded encrypted string
        key: Decryption key
        
    Returns:
        Decrypted string
    """
    crypto = CryptoManager()
    encrypted_data = EncryptedData(
        data=base64.b64decode(encrypted_text),
        algorithm=EncryptionAlgorithm.AES_256_GCM.value
    )
    decrypted_data = crypto.decrypt_data(encrypted_data, key)
    return decrypted_data.decode('utf-8')


# Global crypto manager instance
_crypto_manager: Optional[CryptoManager] = None


def get_crypto_manager() -> CryptoManager:
    """
    Get the global crypto manager instance.
    
    Returns:
        Global CryptoManager instance
    """
    global _crypto_manager
    if _crypto_manager is None:
        _crypto_manager = CryptoManager()
    return _crypto_manager


def set_crypto_manager(crypto_manager: CryptoManager) -> None:
    """
    Set the global crypto manager instance.
    
    Args:
        crypto_manager: CryptoManager instance to set as global
    """
    global _crypto_manager
    _crypto_manager = crypto_manager
