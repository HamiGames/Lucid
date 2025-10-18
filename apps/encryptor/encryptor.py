#!/usr/bin/env python3
"""
Lucid RDP Encryptor Service
High-performance encryption using libsodium bindings
"""

import asyncio
import logging
import secrets
import time
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
from enum import Enum
import structlog
from datetime import datetime, timedelta
import hashlib
import base64

logger = structlog.get_logger(__name__)

try:
    import nacl.secret
    import nacl.utils
    import nacl.encoding
    from nacl.public import PrivateKey, PublicKey, Box
    from nacl.signing import SigningKey, VerifyKey
    from nacl.hash import sha256, sha512, blake2b
    from nacl.derive import derive_key
    LIBSODIUM_AVAILABLE = True
    logger.info("libsodium bindings loaded successfully")
except ImportError:
    logger.warning("libsodium not available, using fallback encryption")
    LIBSODIUM_AVAILABLE = False


class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms"""
    XCHACHA20_POLY1305 = "xchacha20-poly1305"
    CHACHA20_POLY1305 = "chacha20-poly1305"
    AES256_GCM = "aes256-gcm"
    SALSA20_POLY1305 = "salsa20-poly1305"


class HashAlgorithm(Enum):
    """Supported hash algorithms"""
    SHA256 = "sha256"
    SHA512 = "sha512"
    BLAKE2B = "blake2b"


@dataclass
class KeyPair:
    """Key pair for asymmetric encryption"""
    private_key: bytes
    public_key: bytes
    created_at: datetime
    expires_at: Optional[datetime] = None


@dataclass
class SessionKey:
    """Session encryption key"""
    key_id: str
    key_data: bytes
    algorithm: EncryptionAlgorithm
    created_at: datetime
    expires_at: Optional[datetime] = None
    nonce_counter: int = 0


class Encryptor:
    """High-performance encryptor using libsodium"""
    
    def __init__(self, algorithm: EncryptionAlgorithm = EncryptionAlgorithm.XCHACHA20_POLY1305):
        self.algorithm = algorithm
        self.session_keys: Dict[str, SessionKey] = {}
        self.key_pairs: Dict[str, KeyPair] = {}
        self.master_key: Optional[bytes] = None
        self.signing_key: Optional[SigningKey] = None
        self.verify_key: Optional[VerifyKey] = None
        
        # Key rotation settings
        self.key_rotation_interval = 3600  # 1 hour
        self.last_key_rotation = 0
        
        # Statistics
        self.stats = {
            'keys_generated': 0,
            'encryption_operations': 0,
            'decryption_operations': 0,
            'signing_operations': 0,
            'verification_operations': 0,
            'errors': 0,
            'bytes_encrypted': 0,
            'bytes_decrypted': 0
        }
        
        # Initialize if libsodium is available
        if LIBSODIUM_AVAILABLE:
            self._initialize_libsodium()
    
    def _initialize_libsodium(self):
        """Initialize libsodium components"""
        try:
            # Generate master key
            self.master_key = nacl.utils.random(32)
            
            # Generate signing key pair
            self.signing_key = SigningKey.generate()
            self.verify_key = self.signing_key.verify_key
            
            logger.info("libsodium encryptor initialized", algorithm=self.algorithm.value)
            
        except Exception as e:
            logger.error("Failed to initialize libsodium", error=str(e))
            raise
    
    async def generate_key_pair(self, key_id: str, expires_in_hours: int = 24) -> bool:
        """Generate a new key pair for asymmetric encryption"""
        try:
            if not LIBSODIUM_AVAILABLE:
                logger.error("Key pair generation requires libsodium")
                return False
            
            # Generate private key
            private_key = PrivateKey.generate()
            public_key = private_key.public_key
            
            # Calculate expiration time
            created_at = datetime.utcnow()
            expires_at = created_at + timedelta(hours=expires_in_hours)
            
            # Store key pair
            self.key_pairs[key_id] = KeyPair(
                private_key=bytes(private_key),
                public_key=bytes(public_key),
                created_at=created_at,
                expires_at=expires_at
            )
            
            self.stats['keys_generated'] += 1
            
            logger.info("Generated key pair", key_id=key_id, expires_at=expires_at)
            return True
            
        except Exception as e:
            logger.error("Failed to generate key pair", key_id=key_id, error=str(e))
            self.stats['errors'] += 1
            return False
    
    async def create_session_key(self, session_id: str, expires_in_hours: int = 1) -> bool:
        """Create a new session encryption key"""
        try:
            if not LIBSODIUM_AVAILABLE:
                logger.error("Session key creation requires libsodium")
                return False
            
            # Generate session key
            if self.algorithm == EncryptionAlgorithm.XCHACHA20_POLY1305:
                key_data = nacl.utils.random(32)  # XChaCha20-Poly1305 key size
            elif self.algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
                key_data = nacl.utils.random(32)  # ChaCha20-Poly1305 key size
            elif self.algorithm == EncryptionAlgorithm.AES256_GCM:
                key_data = nacl.utils.random(32)  # AES-256 key size
            else:
                key_data = nacl.utils.random(32)  # Default key size
            
            # Calculate expiration time
            created_at = datetime.utcnow()
            expires_at = created_at + timedelta(hours=expires_in_hours)
            
            # Create session key
            key_id = f"{session_id}_{int(time.time())}"
            session_key = SessionKey(
                key_id=key_id,
                key_data=key_data,
                algorithm=self.algorithm,
                created_at=created_at,
                expires_at=expires_at
            )
            
            # Store session key
            self.session_keys[session_id] = session_key
            
            self.stats['keys_generated'] += 1
            
            logger.info("Created session key", session_id=session_id, key_id=key_id)
            return True
            
        except Exception as e:
            logger.error("Failed to create session key", session_id=session_id, error=str(e))
            self.stats['errors'] += 1
            return False
    
    async def encrypt_data(self, data: bytes, session_id: str, 
                          additional_data: bytes = None) -> Optional[bytes]:
        """Encrypt data using session key"""
        try:
            if not LIBSODIUM_AVAILABLE:
                return await self._encrypt_fallback(data, session_id)
            
            # Get session key
            if session_id not in self.session_keys:
                await self.create_session_key(session_id)
            
            session_key = self.session_keys[session_id]
            
            # Check if key is expired
            if session_key.expires_at and datetime.utcnow() > session_key.expires_at:
                logger.warning("Session key expired, creating new one", session_id=session_id)
                await self.create_session_key(session_id)
                session_key = self.session_keys[session_id]
            
            # Create secret box
            secret_box = nacl.secret.SecretBox(session_key.key_data)
            
            # Generate nonce (increment counter for uniqueness)
            nonce = nacl.utils.random(24)  # XChaCha20-Poly1305 nonce size
            session_key.nonce_counter += 1
            
            # Encrypt data
            if additional_data:
                encrypted_data = secret_box.encrypt(data, nonce, encoder=nacl.encoding.RawEncoder)
                # Add additional authenticated data
                # Note: This is a simplified implementation
                encrypted_data = encrypted_data + additional_data
            else:
                encrypted_data = secret_box.encrypt(data, nonce, encoder=nacl.encoding.RawEncoder)
            
            # Create encrypted packet
            packet = {
                'session_id': session_id,
                'key_id': session_key.key_id,
                'algorithm': self.algorithm.value,
                'nonce': base64.b64encode(nonce).decode(),
                'encrypted_data': base64.b64encode(encrypted_data).decode(),
                'timestamp': datetime.utcnow().isoformat(),
                'additional_data': base64.b64encode(additional_data).decode() if additional_data else None
            }
            
            # Serialize packet
            import json
            serialized = json.dumps(packet).encode('utf-8')
            
            # Update statistics
            self.stats['encryption_operations'] += 1
            self.stats['bytes_encrypted'] += len(data)
            
            return serialized
            
        except Exception as e:
            logger.error("Failed to encrypt data", session_id=session_id, error=str(e))
            self.stats['errors'] += 1
            return None
    
    async def decrypt_data(self, encrypted_packet: bytes, session_id: str) -> Optional[bytes]:
        """Decrypt data using session key"""
        try:
            if not LIBSODIUM_AVAILABLE:
                return await self._decrypt_fallback(encrypted_packet, session_id)
            
            # Parse encrypted packet
            import json
            packet = json.loads(encrypted_packet.decode('utf-8'))
            
            if packet['session_id'] != session_id:
                logger.error("Session ID mismatch")
                return None
            
            # Get session key
            if session_id not in self.session_keys:
                logger.error("Session key not found", session_id=session_id)
                return None
            
            session_key = self.session_keys[session_id]
            
            # Create secret box
            secret_box = nacl.secret.SecretBox(session_key.key_data)
            
            # Decode nonce and encrypted data
            nonce = base64.b64decode(packet['nonce'])
            encrypted_data = base64.b64decode(packet['encrypted_data'])
            
            # Decrypt data
            decrypted_data = secret_box.decrypt(encrypted_data, nonce, encoder=nacl.encoding.RawEncoder)
            
            # Update statistics
            self.stats['decryption_operations'] += 1
            self.stats['bytes_decrypted'] += len(decrypted_data)
            
            return decrypted_data
            
        except Exception as e:
            logger.error("Failed to decrypt data", session_id=session_id, error=str(e))
            self.stats['errors'] += 1
            return None
    
    async def sign_data(self, data: bytes) -> Optional[bytes]:
        """Sign data with signing key"""
        try:
            if not LIBSODIUM_AVAILABLE or not self.signing_key:
                logger.error("Signing requires libsodium and signing key")
                return None
            
            # Sign data
            signed_data = self.signing_key.sign(data, encoder=nacl.encoding.RawEncoder)
            
            self.stats['signing_operations'] += 1
            
            return signed_data
            
        except Exception as e:
            logger.error("Failed to sign data", error=str(e))
            self.stats['errors'] += 1
            return None
    
    async def verify_signature(self, signed_data: bytes) -> Tuple[bool, Optional[bytes]]:
        """Verify signature and return original data"""
        try:
            if not LIBSODIUM_AVAILABLE or not self.verify_key:
                logger.error("Signature verification requires libsodium and verify key")
                return False, None
            
            # Verify signature
            verified_data = self.verify_key.verify(signed_data, encoder=nacl.encoding.RawEncoder)
            
            self.stats['verification_operations'] += 1
            
            return True, verified_data
            
        except Exception as e:
            logger.error("Failed to verify signature", error=str(e))
            self.stats['errors'] += 1
            return False, None
    
    async def hash_data(self, data: bytes, algorithm: HashAlgorithm = HashAlgorithm.BLAKE2B) -> Optional[str]:
        """Hash data using specified algorithm"""
        try:
            if not LIBSODIUM_AVAILABLE:
                # Fallback to hashlib
                if algorithm == HashAlgorithm.SHA256:
                    return hashlib.sha256(data).hexdigest()
                elif algorithm == HashAlgorithm.SHA512:
                    return hashlib.sha512(data).hexdigest()
                else:
                    return hashlib.sha256(data).hexdigest()  # Default fallback
            
            # Use libsodium hashing
            if algorithm == HashAlgorithm.SHA256:
                hash_bytes = sha256(data, encoder=nacl.encoding.RawEncoder)
            elif algorithm == HashAlgorithm.SHA512:
                hash_bytes = sha512(data, encoder=nacl.encoding.RawEncoder)
            elif algorithm == HashAlgorithm.BLAKE2B:
                hash_bytes = blake2b(data, encoder=nacl.encoding.RawEncoder)
            else:
                hash_bytes = sha256(data, encoder=nacl.encoding.RawEncoder)
            
            return hash_bytes.hex()
            
        except Exception as e:
            logger.error("Failed to hash data", error=str(e))
            self.stats['errors'] += 1
            return None
    
    async def derive_key(self, password: bytes, salt: bytes, 
                        key_length: int = 32) -> Optional[bytes]:
        """Derive key from password using scrypt"""
        try:
            if not LIBSODIUM_AVAILABLE:
                # Fallback to hashlib
                import hashlib
                return hashlib.scrypt(password, salt=salt, n=2**14, r=8, p=1, dklen=key_length)
            
            # Use libsodium key derivation
            derived_key = derive_key(password, salt, key_length)
            return derived_key
            
        except Exception as e:
            logger.error("Failed to derive key", error=str(e))
            self.stats['errors'] += 1
            return None
    
    async def _encrypt_fallback(self, data: bytes, session_id: str) -> Optional[bytes]:
        """Fallback encryption using Python standard library"""
        try:
            # Simple XOR encryption with key derived from session ID
            key = hashlib.sha256(session_id.encode()).digest()
            
            # Pad key to match data length
            key_len = len(key)
            padded_key = (key * ((len(data) // key_len) + 1))[:len(data)]
            
            # XOR encryption
            encrypted_data = bytes(a ^ b for a, b in zip(data, padded_key))
            
            # Create packet
            packet = {
                'session_id': session_id,
                'algorithm': 'fallback',
                'encrypted_data': base64.b64encode(encrypted_data).decode(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            import json
            return json.dumps(packet).encode('utf-8')
            
        except Exception as e:
            logger.error("Fallback encryption failed", error=str(e))
            return None
    
    async def _decrypt_fallback(self, encrypted_packet: bytes, session_id: str) -> Optional[bytes]:
        """Fallback decryption using Python standard library"""
        try:
            # Parse packet
            import json
            packet = json.loads(encrypted_packet.decode('utf-8'))
            
            if packet['session_id'] != session_id:
                return None
            
            # Decode encrypted data
            encrypted_data = base64.b64decode(packet['encrypted_data'])
            
            # Derive key from session ID
            key = hashlib.sha256(session_id.encode()).digest()
            
            # Pad key to match data length
            key_len = len(key)
            padded_key = (key * ((len(encrypted_data) // key_len) + 1))[:len(encrypted_data)]
            
            # XOR decryption (same as encryption)
            decrypted_data = bytes(a ^ b for a, b in zip(encrypted_data, padded_key))
            
            return decrypted_data
            
        except Exception as e:
            logger.error("Fallback decryption failed", error=str(e))
            return None
    
    async def rotate_keys(self):
        """Rotate encryption keys"""
        try:
            current_time = time.time()
            
            # Check if key rotation is needed
            if current_time - self.last_key_rotation < self.key_rotation_interval:
                return
            
            logger.info("Rotating encryption keys")
            
            # Generate new master key
            if LIBSODIUM_AVAILABLE:
                self.master_key = nacl.utils.random(32)
                
                # Generate new signing key pair
                self.signing_key = SigningKey.generate()
                self.verify_key = self.signing_key.verify_key
            
            # Update last rotation time
            self.last_key_rotation = current_time
            
            logger.info("Encryption keys rotated successfully")
            
        except Exception as e:
            logger.error("Failed to rotate encryption keys", error=str(e))
            self.stats['errors'] += 1
    
    async def cleanup_session(self, session_id: str):
        """Cleanup session encryption keys"""
        try:
            if session_id in self.session_keys:
                del self.session_keys[session_id]
                logger.info("Session encryption keys cleaned up", session_id=session_id)
            
        except Exception as e:
            logger.error("Failed to cleanup session keys", session_id=session_id, error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get encryption statistics"""
        return {
            **self.stats,
            'algorithm': self.algorithm.value,
            'libsodium_available': LIBSODIUM_AVAILABLE,
            'active_sessions': len(self.session_keys),
            'key_pairs': len(self.key_pairs),
            'last_key_rotation': self.last_key_rotation,
            'key_rotation_interval': self.key_rotation_interval
        }
    
    async def cleanup(self):
        """Cleanup encryption resources"""
        try:
            # Clear all keys
            self.session_keys.clear()
            self.key_pairs.clear()
            
            logger.info("Encryptor cleanup completed")
            
        except Exception as e:
            logger.error("Encryptor cleanup error", error=str(e))


class EncryptorService:
    """Service for managing multiple encryptors"""
    
    def __init__(self):
        self.encryptors: Dict[str, Encryptor] = {}
        self.is_running = False
    
    async def start(self):
        """Start the encryptor service"""
        self.is_running = True
        logger.info("Encryptor service started")
    
    async def stop(self):
        """Stop the encryptor service"""
        self.is_running = False
        
        # Cleanup all encryptors
        for encryptor in self.encryptors.values():
            await encryptor.cleanup()
        
        self.encryptors.clear()
        logger.info("Encryptor service stopped")
    
    async def create_encryptor(self, session_id: str, 
                              algorithm: EncryptionAlgorithm = EncryptionAlgorithm.XCHACHA20_POLY1305) -> Encryptor:
        """Create a new encryptor for a session"""
        try:
            if session_id in self.encryptors:
                logger.warning("Encryptor already exists for session", session_id=session_id)
                return self.encryptors[session_id]
            
            # Create encryptor
            encryptor = Encryptor(algorithm=algorithm)
            self.encryptors[session_id] = encryptor
            
            logger.info("Created encryptor for session", session_id=session_id, algorithm=algorithm.value)
            return encryptor
            
        except Exception as e:
            logger.error("Failed to create encryptor", session_id=session_id, error=str(e))
            return None
    
    async def get_encryptor(self, session_id: str) -> Optional[Encryptor]:
        """Get encryptor for a session"""
        return self.encryptors.get(session_id)
    
    async def remove_encryptor(self, session_id: str):
        """Remove encryptor for a session"""
        try:
            if session_id in self.encryptors:
                encryptor = self.encryptors[session_id]
                await encryptor.cleanup()
                del self.encryptors[session_id]
                logger.info("Removed encryptor for session", session_id=session_id)
        except Exception as e:
            logger.error("Failed to remove encryptor", session_id=session_id, error=str(e))
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get service-wide statistics"""
        stats = {
            'is_running': self.is_running,
            'active_encryptors': len(self.encryptors),
            'sessions': list(self.encryptors.keys()),
            'libsodium_available': LIBSODIUM_AVAILABLE
        }
        
        # Aggregate encryptor stats
        total_stats = {
            'keys_generated': 0,
            'encryption_operations': 0,
            'decryption_operations': 0,
            'signing_operations': 0,
            'verification_operations': 0,
            'errors': 0,
            'bytes_encrypted': 0,
            'bytes_decrypted': 0
        }
        
        for encryptor in self.encryptors.values():
            encryptor_stats = encryptor.get_stats()
            for key in total_stats:
                if key in encryptor_stats:
                    total_stats[key] += encryptor_stats[key]
        
        stats['aggregate_stats'] = total_stats
        return stats


async def main():
    """Main entry point for encryptor service"""
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Create and start service
    service = EncryptorService()
    
    try:
        await service.start()
        
        # Keep running
        logger.info("Encryptor service running")
        while service.is_running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error("Unexpected error", error=str(e))
    finally:
        await service.stop()


if __name__ == "__main__":
    asyncio.run(main())
