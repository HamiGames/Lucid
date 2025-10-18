#!/usr/bin/env python3
"""
Session Encryptor Module for Lucid RDP Recorder
Provides encryption for session data using libsodium
"""

import asyncio
import logging
import secrets
import time
from typing import Optional, Dict, Any, Tuple
import structlog
from datetime import datetime, timedelta
import hashlib

logger = structlog.get_logger(__name__)

try:
    import nacl.secret
    import nacl.utils
    import nacl.encoding
    from nacl.public import PrivateKey, PublicKey, Box
    from nacl.signing import SigningKey, VerifyKey
    LIBSODIUM_AVAILABLE = True
except ImportError:
    logger.warning("libsodium not available, using fallback encryption")
    LIBSODIUM_AVAILABLE = False


class SessionEncryptor:
    """Encrypts session data using libsodium"""
    
    def __init__(self, algorithm: str = "XChaCha20-Poly1305"):
        self.algorithm = algorithm
        self.session_keys: Dict[str, Dict[str, Any]] = {}
        self.key_rotation_interval = 3600  # 1 hour
        self.last_key_rotation = 0
        
        if not LIBSODIUM_AVAILABLE:
            logger.warning("Using fallback encryption (libsodium not available)")
            self.algorithm = "fallback"
    
    async def generate_keys(self) -> bool:
        """Generate encryption keys"""
        try:
            if LIBSODIUM_AVAILABLE:
                # Generate master key
                self.master_key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
                
                # Generate signing key pair
                self.signing_key = SigningKey.generate()
                self.verify_key = self.signing_key.verify_key
                
                logger.info("Encryption keys generated successfully")
                return True
            else:
                # Fallback to simple key generation
                self.master_key = secrets.token_bytes(32)
                logger.warning("Using fallback key generation")
                return True
                
        except Exception as e:
            logger.error("Failed to generate encryption keys", error=str(e))
            return False
    
    async def create_session_key(self, session_id: str) -> bool:
        """Create encryption key for a session"""
        try:
            if LIBSODIUM_AVAILABLE:
                # Generate session-specific key
                session_key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
                
                # Create secret box for this session
                secret_box = nacl.secret.SecretBox(session_key)
                
                # Store session key info
                self.session_keys[session_id] = {
                    'key': session_key,
                    'secret_box': secret_box,
                    'created_at': time.time(),
                    'nonce_counter': 0
                }
                
                logger.info("Session encryption key created", session_id=session_id)
                return True
            else:
                # Fallback session key
                session_key = secrets.token_bytes(32)
                self.session_keys[session_id] = {
                    'key': session_key,
                    'created_at': time.time(),
                    'nonce_counter': 0
                }
                logger.warning("Using fallback session key", session_id=session_id)
                return True
                
        except Exception as e:
            logger.error("Failed to create session key", session_id=session_id, error=str(e))
            return False
    
    async def encrypt_chunk(self, chunk_data: bytes, session_id: str) -> Optional[bytes]:
        """Encrypt a chunk of data"""
        try:
            # Check if session key exists
            if session_id not in self.session_keys:
                await self.create_session_key(session_id)
            
            session_info = self.session_keys[session_id]
            
            if LIBSODIUM_AVAILABLE:
                # Use libsodium encryption
                secret_box = session_info['secret_box']
                
                # Generate nonce (increment counter for uniqueness)
                nonce_counter = session_info['nonce_counter']
                nonce = nonce_counter.to_bytes(24, byteorder='big')
                session_info['nonce_counter'] += 1
                
                # Encrypt data
                encrypted_data = secret_box.encrypt(chunk_data, nonce)
                
                # Create encrypted chunk with metadata
                encrypted_chunk = {
                    'session_id': session_id,
                    'algorithm': self.algorithm,
                    'nonce': nonce.hex(),
                    'encrypted_data': encrypted_data.hex(),
                    'timestamp': datetime.utcnow().isoformat(),
                    'size': len(chunk_data)
                }
                
                # Serialize encrypted chunk
                import json
                serialized = json.dumps(encrypted_chunk).encode('utf-8')
                
                return serialized
            else:
                # Fallback encryption (simple XOR with key)
                session_key = session_info['key']
                
                # Pad key to match data length
                key_len = len(session_key)
                padded_key = (session_key * ((len(chunk_data) // key_len) + 1))[:len(chunk_data)]
                
                # XOR encryption
                encrypted_data = bytes(a ^ b for a, b in zip(chunk_data, padded_key))
                
                # Create encrypted chunk with metadata
                encrypted_chunk = {
                    'session_id': session_id,
                    'algorithm': 'fallback',
                    'encrypted_data': encrypted_data.hex(),
                    'timestamp': datetime.utcnow().isoformat(),
                    'size': len(chunk_data)
                }
                
                # Serialize encrypted chunk
                import json
                serialized = json.dumps(encrypted_chunk).encode('utf-8')
                
                return serialized
                
        except Exception as e:
            logger.error("Failed to encrypt chunk", session_id=session_id, error=str(e))
            return None
    
    async def decrypt_chunk(self, encrypted_chunk: bytes, session_id: str) -> Optional[bytes]:
        """Decrypt a chunk of data"""
        try:
            # Parse encrypted chunk
            import json
            chunk_info = json.loads(encrypted_chunk.decode('utf-8'))
            
            if chunk_info['session_id'] != session_id:
                logger.error("Session ID mismatch")
                return None
            
            # Check if session key exists
            if session_id not in self.session_keys:
                logger.error("Session key not found", session_id=session_id)
                return None
            
            session_info = self.session_keys[session_id]
            
            if LIBSODIUM_AVAILABLE and chunk_info['algorithm'] != 'fallback':
                # Use libsodium decryption
                secret_box = session_info['secret_box']
                
                # Parse nonce
                nonce = bytes.fromhex(chunk_info['nonce'])
                
                # Parse encrypted data
                encrypted_data = bytes.fromhex(chunk_info['encrypted_data'])
                
                # Decrypt data
                decrypted_data = secret_box.decrypt(encrypted_data, nonce)
                
                return decrypted_data
            else:
                # Fallback decryption
                session_key = session_info['key']
                
                # Parse encrypted data
                encrypted_data = bytes.fromhex(chunk_info['encrypted_data'])
                
                # Pad key to match data length
                key_len = len(session_key)
                padded_key = (session_key * ((len(encrypted_data) // key_len) + 1))[:len(encrypted_data)]
                
                # XOR decryption (same as encryption)
                decrypted_data = bytes(a ^ b for a, b in zip(encrypted_data, padded_key))
                
                return decrypted_data
                
        except Exception as e:
            logger.error("Failed to decrypt chunk", session_id=session_id, error=str(e))
            return None
    
    async def sign_data(self, data: bytes) -> Optional[bytes]:
        """Sign data with signing key"""
        try:
            if not LIBSODIUM_AVAILABLE:
                logger.warning("Signing not available without libsodium")
                return None
            
            # Sign data
            signed_data = self.signing_key.sign(data)
            
            return signed_data
            
        except Exception as e:
            logger.error("Failed to sign data", error=str(e))
            return None
    
    async def verify_signature(self, signed_data: bytes) -> Tuple[bool, Optional[bytes]]:
        """Verify signature and return data"""
        try:
            if not LIBSODIUM_AVAILABLE:
                logger.warning("Signature verification not available without libsodium")
                return False, None
            
            # Verify signature
            verified_data = self.verify_key.verify(signed_data)
            
            return True, verified_data
            
        except Exception as e:
            logger.error("Failed to verify signature", error=str(e))
            return False, None
    
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
                self.master_key = nacl.utils.random(nacl.secret.SecretBox.KEY_SIZE)
            else:
                self.master_key = secrets.token_bytes(32)
            
            # Update last rotation time
            self.last_key_rotation = current_time
            
            logger.info("Encryption keys rotated successfully")
            
        except Exception as e:
            logger.error("Failed to rotate encryption keys", error=str(e))
    
    async def cleanup_session(self, session_id: str):
        """Cleanup session encryption keys"""
        try:
            if session_id in self.session_keys:
                del self.session_keys[session_id]
                logger.info("Session encryption keys cleaned up", session_id=session_id)
            
        except Exception as e:
            logger.error("Failed to cleanup session keys", session_id=session_id, error=str(e))
    
    def get_encryption_stats(self) -> Dict[str, Any]:
        """Get encryption statistics"""
        return {
            'algorithm': self.algorithm,
            'libsodium_available': LIBSODIUM_AVAILABLE,
            'active_sessions': len(self.session_keys),
            'last_key_rotation': self.last_key_rotation,
            'key_rotation_interval': self.key_rotation_interval
        }
    
    async def cleanup(self):
        """Cleanup encryption resources"""
        try:
            # Clear all session keys
            self.session_keys.clear()
            
            logger.info("Encryptor cleanup completed")
            
        except Exception as e:
            logger.error("Encryptor cleanup error", error=str(e))
