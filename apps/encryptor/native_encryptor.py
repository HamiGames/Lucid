#!/usr/bin/env python3
"""
Native Encryptor Module for Lucid RDP
High-performance encryption using native libsodium bindings
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, Tuple
import structlog
import ctypes
import os
from pathlib import Path

logger = structlog.get_logger(__name__)

# Try to import native extension
try:
    import encryptor_native
    NATIVE_LIBSODIUM_AVAILABLE = True
    logger.info("Native libsodium extension loaded successfully")
except ImportError:
    NATIVE_LIBSODIUM_AVAILABLE = False
    logger.warning("Native libsodium extension not available, using Python fallback")


class NativeEncryptor:
    """High-performance native encryptor using libsodium"""
    
    def __init__(self, algorithm: str = "xchacha20-poly1305"):
        self.algorithm = algorithm
        self.native_encryptor = None
        self.session_keys: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self.stats = {
            'keys_generated': 0,
            'encryption_operations': 0,
            'decryption_operations': 0,
            'bytes_encrypted': 0,
            'bytes_decrypted': 0,
            'native_calls': 0,
            'fallback_calls': 0,
            'errors': 0
        }
        
        # Initialize native encryptor if available
        if NATIVE_LIBSODIUM_AVAILABLE:
            self._initialize_native()
    
    def _initialize_native(self):
        """Initialize native encryptor"""
        try:
            self.native_encryptor = encryptor_native.Encryptor(
                algorithm=self.algorithm
            )
            logger.info("Native encryptor initialized", algorithm=self.algorithm)
        except Exception as e:
            logger.error("Failed to initialize native encryptor", error=str(e))
            self.native_encryptor = None
    
    async def generate_key(self, key_id: str) -> bool:
        """Generate a new encryption key"""
        try:
            if NATIVE_LIBSODIUM_AVAILABLE and self.native_encryptor:
                # Use native key generation
                key_data = self.native_encryptor.generate_key()
                
                if key_data:
                    self.session_keys[key_id] = {
                        'key_data': key_data,
                        'created_at': time.time(),
                        'native': True
                    }
                    
                    self.stats['keys_generated'] += 1
                    self.stats['native_calls'] += 1
                    
                    logger.info("Generated native key", key_id=key_id)
                    return True
                else:
                    logger.error("Native key generation failed", key_id=key_id)
                    return False
            else:
                # Fallback to Python key generation
                import secrets
                key_data = secrets.token_bytes(32)
                
                self.session_keys[key_id] = {
                    'key_data': key_data,
                    'created_at': time.time(),
                    'native': False
                }
                
                self.stats['keys_generated'] += 1
                self.stats['fallback_calls'] += 1
                
                logger.warning("Generated fallback key", key_id=key_id)
                return True
                
        except Exception as e:
            logger.error("Failed to generate key", key_id=key_id, error=str(e))
            self.stats['errors'] += 1
            return False
    
    async def encrypt_data(self, data: bytes, key_id: str, 
                          additional_data: bytes = None) -> Optional[bytes]:
        """Encrypt data using native implementation"""
        try:
            # Check if key exists
            if key_id not in self.session_keys:
                await self.generate_key(key_id)
            
            session_key = self.session_keys[key_id]
            
            if NATIVE_LIBSODIUM_AVAILABLE and self.native_encryptor and session_key['native']:
                # Use native encryption
                encrypted_data = self.native_encryptor.encrypt(
                    data, 
                    session_key['key_data'],
                    additional_data
                )
                
                if encrypted_data:
                    self.stats['encryption_operations'] += 1
                    self.stats['bytes_encrypted'] += len(data)
                    self.stats['native_calls'] += 1
                    
                    # Create encrypted packet
                    packet = {
                        'key_id': key_id,
                        'algorithm': self.algorithm,
                        'encrypted_data': encrypted_data.hex(),
                        'timestamp': time.time(),
                        'native': True
                    }
                    
                    import json
                    return json.dumps(packet).encode('utf-8')
                else:
                    logger.error("Native encryption failed", key_id=key_id)
                    return None
            else:
                # Use Python fallback
                result = await self._encrypt_python_fallback(data, key_id, additional_data)
                if result:
                    self.stats['fallback_calls'] += 1
                return result
                
        except Exception as e:
            logger.error("Failed to encrypt data", key_id=key_id, error=str(e))
            self.stats['errors'] += 1
            return None
    
    async def decrypt_data(self, encrypted_packet: bytes, key_id: str) -> Optional[bytes]:
        """Decrypt data using native implementation"""
        try:
            # Parse encrypted packet
            import json
            packet = json.loads(encrypted_packet.decode('utf-8'))
            
            if packet['key_id'] != key_id:
                logger.error("Key ID mismatch")
                return None
            
            # Check if key exists
            if key_id not in self.session_keys:
                logger.error("Key not found", key_id=key_id)
                return None
            
            session_key = self.session_keys[key_id]
            
            if NATIVE_LIBSODIUM_AVAILABLE and self.native_encryptor and session_key['native']:
                # Use native decryption
                encrypted_data = bytes.fromhex(packet['encrypted_data'])
                decrypted_data = self.native_encryptor.decrypt(
                    encrypted_data,
                    session_key['key_data']
                )
                
                if decrypted_data:
                    self.stats['decryption_operations'] += 1
                    self.stats['bytes_decrypted'] += len(decrypted_data)
                    self.stats['native_calls'] += 1
                    
                    return decrypted_data
                else:
                    logger.error("Native decryption failed", key_id=key_id)
                    return None
            else:
                # Use Python fallback
                result = await self._decrypt_python_fallback(encrypted_packet, key_id)
                if result:
                    self.stats['fallback_calls'] += 1
                return result
                
        except Exception as e:
            logger.error("Failed to decrypt data", key_id=key_id, error=str(e))
            self.stats['errors'] += 1
            return None
    
    async def _encrypt_python_fallback(self, data: bytes, key_id: str, 
                                     additional_data: bytes = None) -> Optional[bytes]:
        """Python fallback encryption"""
        try:
            import hashlib
            
            # Derive key from key_id
            key = hashlib.sha256(key_id.encode()).digest()
            
            # Simple XOR encryption
            key_len = len(key)
            padded_key = (key * ((len(data) // key_len) + 1))[:len(data)]
            encrypted_data = bytes(a ^ b for a, b in zip(data, padded_key))
            
            # Create packet
            packet = {
                'key_id': key_id,
                'algorithm': 'fallback',
                'encrypted_data': encrypted_data.hex(),
                'timestamp': time.time(),
                'native': False
            }
            
            import json
            serialized = json.dumps(packet).encode('utf-8')
            
            self.stats['encryption_operations'] += 1
            self.stats['bytes_encrypted'] += len(data)
            
            return serialized
            
        except Exception as e:
            logger.error("Python fallback encryption failed", error=str(e))
            return None
    
    async def _decrypt_python_fallback(self, encrypted_packet: bytes, key_id: str) -> Optional[bytes]:
        """Python fallback decryption"""
        try:
            import json
            import hashlib
            
            # Parse packet
            packet = json.loads(encrypted_packet.decode('utf-8'))
            
            if packet['key_id'] != key_id:
                return None
            
            # Decode encrypted data
            encrypted_data = bytes.fromhex(packet['encrypted_data'])
            
            # Derive key from key_id
            key = hashlib.sha256(key_id.encode()).digest()
            
            # XOR decryption
            key_len = len(key)
            padded_key = (key * ((len(encrypted_data) // key_len) + 1))[:len(encrypted_data)]
            decrypted_data = bytes(a ^ b for a, b in zip(encrypted_data, padded_key))
            
            self.stats['decryption_operations'] += 1
            self.stats['bytes_decrypted'] += len(decrypted_data)
            
            return decrypted_data
            
        except Exception as e:
            logger.error("Python fallback decryption failed", error=str(e))
            return None
    
    async def sign_data(self, data: bytes) -> Optional[bytes]:
        """Sign data using native implementation"""
        try:
            if NATIVE_LIBSODIUM_AVAILABLE and self.native_encryptor:
                # Use native signing
                signature = self.native_encryptor.sign(data)
                
                if signature:
                    self.stats['native_calls'] += 1
                    return signature
                else:
                    logger.error("Native signing failed")
                    return None
            else:
                # Use Python fallback
                import hashlib
                signature = hashlib.sha256(data).digest()
                self.stats['fallback_calls'] += 1
                return signature
                
        except Exception as e:
            logger.error("Failed to sign data", error=str(e))
            self.stats['errors'] += 1
            return None
    
    async def verify_signature(self, data: bytes, signature: bytes) -> bool:
        """Verify signature using native implementation"""
        try:
            if NATIVE_LIBSODIUM_AVAILABLE and self.native_encryptor:
                # Use native verification
                is_valid = self.native_encryptor.verify(data, signature)
                
                if is_valid is not None:
                    self.stats['native_calls'] += 1
                    return is_valid
                else:
                    logger.error("Native verification failed")
                    return False
            else:
                # Use Python fallback
                import hashlib
                expected_signature = hashlib.sha256(data).digest()
                is_valid = signature == expected_signature
                self.stats['fallback_calls'] += 1
                return is_valid
                
        except Exception as e:
            logger.error("Failed to verify signature", error=str(e))
            self.stats['errors'] += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get encryption statistics"""
        return {
            **self.stats,
            'algorithm': self.algorithm,
            'native_libsodium_available': NATIVE_LIBSODIUM_AVAILABLE,
            'native_initialized': self.native_encryptor is not None,
            'active_keys': len(self.session_keys)
        }
    
    async def cleanup(self):
        """Cleanup encryptor resources"""
        try:
            # Clear all keys
            self.session_keys.clear()
            
            # Cleanup native encryptor
            if self.native_encryptor:
                self.native_encryptor.cleanup()
            
            logger.info("Native encryptor cleanup completed")
            
        except Exception as e:
            logger.error("Native encryptor cleanup error", error=str(e))


class NativeEncryptorService:
    """Service for managing multiple native encryptors"""
    
    def __init__(self):
        self.encryptors: Dict[str, NativeEncryptor] = {}
        self.is_running = False
    
    async def start(self):
        """Start the native encryptor service"""
        self.is_running = True
        logger.info("Native encryptor service started")
    
    async def stop(self):
        """Stop the native encryptor service"""
        self.is_running = False
        
        # Cleanup all encryptors
        for encryptor in self.encryptors.values():
            await encryptor.cleanup()
        
        self.encryptors.clear()
        logger.info("Native encryptor service stopped")
    
    async def create_encryptor(self, session_id: str, algorithm: str = "xchacha20-poly1305") -> NativeEncryptor:
        """Create a new encryptor for a session"""
        try:
            if session_id in self.encryptors:
                logger.warning("Encryptor already exists for session", session_id=session_id)
                return self.encryptors[session_id]
            
            # Create encryptor
            encryptor = NativeEncryptor(algorithm=algorithm)
            self.encryptors[session_id] = encryptor
            
            logger.info("Created native encryptor for session", session_id=session_id, algorithm=algorithm)
            return encryptor
            
        except Exception as e:
            logger.error("Failed to create encryptor", session_id=session_id, error=str(e))
            return None
    
    async def get_encryptor(self, session_id: str) -> Optional[NativeEncryptor]:
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
            'native_libsodium_available': NATIVE_LIBSODIUM_AVAILABLE
        }
        
        # Aggregate encryptor stats
        total_stats = {
            'keys_generated': 0,
            'encryption_operations': 0,
            'decryption_operations': 0,
            'bytes_encrypted': 0,
            'bytes_decrypted': 0,
            'native_calls': 0,
            'fallback_calls': 0,
            'errors': 0
        }
        
        for encryptor in self.encryptors.values():
            encryptor_stats = encryptor.get_stats()
            for key in total_stats:
                if key in encryptor_stats:
                    total_stats[key] += encryptor_stats[key]
        
        stats['aggregate_stats'] = total_stats
        return stats


async def main():
    """Main entry point for native encryptor service"""
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
    service = NativeEncryptorService()
    
    try:
        await service.start()
        
        # Keep running
        logger.info("Native encryptor service running")
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
