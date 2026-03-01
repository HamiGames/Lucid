#!/usr/bin/env python3
"""
Lucid RDP Wallet Daemon
Secure key management and wallet operations
"""

import asyncio
import logging
import secrets
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import structlog
from datetime import datetime, timedelta
import hashlib
import base64
import json
from pathlib import Path

logger = structlog.get_logger(__name__)

try:
    import nacl.secret
    import nacl.utils
    import nacl.encoding
    from nacl.public import PrivateKey, PublicKey, Box
    from nacl.signing import SigningKey, VerifyKey
    LIBSODIUM_AVAILABLE = True
    logger.info("libsodium bindings loaded successfully")
except ImportError:
    logger.warning("libsodium not available, using fallback encryption")
    LIBSODIUM_AVAILABLE = False


class KeyType(Enum):
    """Supported key types"""
    ED25519 = "ed25519"
    SECP256K1 = "secp256k1"
    RSA = "rsa"
    AES = "aes"


class WalletStatus(Enum):
    """Wallet status"""
    ACTIVE = "active"
    LOCKED = "locked"
    DISABLED = "disabled"
    ARCHIVED = "archived"


@dataclass
class KeyPair:
    """Key pair for asymmetric operations"""
    key_id: str
    key_type: KeyType
    private_key: bytes
    public_key: bytes
    created_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = None


@dataclass
class Wallet:
    """Wallet container"""
    wallet_id: str
    name: str
    status: WalletStatus
    created_at: datetime
    last_accessed: datetime
    keys: List[str]  # Key IDs
    metadata: Dict[str, Any] = None


class WalletManager:
    """Secure wallet and key management"""
    
    def __init__(self, storage_path: str = "/opt/lucid/wallets"):
        self.storage_path = Path(storage_path)
        self.wallets: Dict[str, Wallet] = {}
        self.keys: Dict[str, KeyPair] = {}
        self.master_key: Optional[bytes] = None
        self.is_initialized = False
        
        # Security settings
        self.key_rotation_interval = 86400  # 24 hours
        self.max_failed_attempts = 3
        self.lockout_duration = 300  # 5 minutes
        
        # Statistics
        self.stats = {
            'wallets_created': 0,
            'keys_generated': 0,
            'operations_performed': 0,
            'failed_attempts': 0,
            'last_rotation': 0
        }
        
        # Create storage directory
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self) -> bool:
        """Initialize wallet manager"""
        try:
            logger.info("Initializing wallet manager")
            
            # Generate master key if not exists
            if not self.master_key:
                await self._generate_master_key()
            
            # Load existing wallets and keys
            await self._load_wallets()
            await self._load_keys()
            
            self.is_initialized = True
            logger.info("Wallet manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize wallet manager", error=str(e))
            return False
    
    async def _generate_master_key(self):
        """Generate master encryption key"""
        try:
            if LIBSODIUM_AVAILABLE:
                self.master_key = nacl.utils.random(32)
            else:
                self.master_key = secrets.token_bytes(32)
            
            logger.info("Master key generated")
        except Exception as e:
            logger.error("Failed to generate master key", error=str(e))
            raise
    
    async def create_wallet(self, name: str, key_type: KeyType = KeyType.ED25519) -> Optional[str]:
        """Create a new wallet"""
        try:
            wallet_id = f"wallet_{secrets.token_hex(16)}"
            
            # Create wallet
            wallet = Wallet(
                wallet_id=wallet_id,
                name=name,
                status=WalletStatus.ACTIVE,
                created_at=datetime.utcnow(),
                last_accessed=datetime.utcnow(),
                keys=[]
            )
            
            # Generate initial key pair
            key_pair = await self._generate_key_pair(key_type)
            if not key_pair:
                return None
            
            # Add key to wallet
            wallet.keys.append(key_pair.key_id)
            self.keys[key_pair.key_id] = key_pair
            self.wallets[wallet_id] = wallet
            
            # Save wallet
            await self._save_wallet(wallet)
            
            self.stats['wallets_created'] += 1
            self.stats['keys_generated'] += 1
            
            logger.info("Wallet created", wallet_id=wallet_id, name=name)
            return wallet_id
            
        except Exception as e:
            logger.error("Failed to create wallet", error=str(e))
            return None
    
    async def _generate_key_pair(self, key_type: KeyType) -> Optional[KeyPair]:
        """Generate a new key pair"""
        try:
            key_id = f"key_{secrets.token_hex(16)}"
            
            if key_type == KeyType.ED25519 and LIBSODIUM_AVAILABLE:
                # Generate Ed25519 key pair
                private_key = PrivateKey.generate()
                public_key = private_key.public_key
                
                key_pair = KeyPair(
                    key_id=key_id,
                    key_type=key_type,
                    private_key=bytes(private_key),
                    public_key=bytes(public_key),
                    created_at=datetime.utcnow()
                )
            else:
                # Fallback key generation
                private_key = secrets.token_bytes(32)
                public_key = hashlib.sha256(private_key).digest()
                
                key_pair = KeyPair(
                    key_id=key_id,
                    key_type=key_type,
                    private_key=private_key,
                    public_key=public_key,
                    created_at=datetime.utcnow()
                )
            
            # Encrypt private key
            encrypted_private_key = await self._encrypt_key(key_pair.private_key)
            key_pair.private_key = encrypted_private_key
            
            # Save key
            await self._save_key(key_pair)
            
            self.stats['keys_generated'] += 1
            logger.info("Key pair generated", key_id=key_id, key_type=key_type.value)
            
            return key_pair
            
        except Exception as e:
            logger.error("Failed to generate key pair", error=str(e))
            return None
    
    async def _encrypt_key(self, key_data: bytes) -> bytes:
        """Encrypt key data with master key"""
        try:
            if LIBSODIUM_AVAILABLE:
                # Use libsodium encryption
                secret_box = nacl.secret.SecretBox(self.master_key)
                nonce = nacl.utils.random(24)
                encrypted = secret_box.encrypt(key_data, nonce)
                return encrypted
            else:
                # Simple XOR encryption
                key_len = len(self.master_key)
                padded_key = (self.master_key * ((len(key_data) // key_len) + 1))[:len(key_data)]
                return bytes(a ^ b for a, b in zip(key_data, padded_key))
                
        except Exception as e:
            logger.error("Failed to encrypt key", error=str(e))
            return key_data
    
    async def _decrypt_key(self, encrypted_key: bytes) -> bytes:
        """Decrypt key data with master key"""
        try:
            if LIBSODIUM_AVAILABLE:
                # Use libsodium decryption
                secret_box = nacl.secret.SecretBox(self.master_key)
                decrypted = secret_box.decrypt(encrypted_key)
                return decrypted
            else:
                # Simple XOR decryption
                key_len = len(self.master_key)
                padded_key = (self.master_key * ((len(encrypted_key) // key_len) + 1))[:len(encrypted_key)]
                return bytes(a ^ b for a, b in zip(encrypted_key, padded_key))
                
        except Exception as e:
            logger.error("Failed to decrypt key", error=str(e))
            return encrypted_key
    
    async def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """Get wallet by ID"""
        try:
            if wallet_id not in self.wallets:
                return None
            
            wallet = self.wallets[wallet_id]
            wallet.last_accessed = datetime.utcnow()
            
            return wallet
            
        except Exception as e:
            logger.error("Failed to get wallet", wallet_id=wallet_id, error=str(e))
            return None
    
    async def get_key(self, key_id: str, decrypt: bool = False) -> Optional[KeyPair]:
        """Get key by ID"""
        try:
            if key_id not in self.keys:
                return None
            
            key_pair = self.keys[key_id]
            
            if decrypt:
                # Decrypt private key
                decrypted_private_key = await self._decrypt_key(key_pair.private_key)
                key_pair.private_key = decrypted_private_key
            
            return key_pair
            
        except Exception as e:
            logger.error("Failed to get key", key_id=key_id, error=str(e))
            return None
    
    async def sign_data(self, wallet_id: str, key_id: str, data: bytes) -> Optional[bytes]:
        """Sign data with wallet key"""
        try:
            # Get wallet
            wallet = await self.get_wallet(wallet_id)
            if not wallet:
                return None
            
            # Get key
            key_pair = await self.get_key(key_id, decrypt=True)
            if not key_pair:
                return None
            
            if key_pair.key_type == KeyType.ED25519 and LIBSODIUM_AVAILABLE:
                # Use libsodium signing
                signing_key = SigningKey(key_pair.private_key)
                signed_data = signing_key.sign(data)
                return signed_data
            else:
                # Fallback signing
                signature = hashlib.sha256(data + key_pair.private_key).digest()
                return signature
            
        except Exception as e:
            logger.error("Failed to sign data", error=str(e))
            return None
    
    async def verify_signature(self, public_key: bytes, data: bytes, signature: bytes) -> bool:
        """Verify signature"""
        try:
            if LIBSODIUM_AVAILABLE:
                # Use libsodium verification
                verify_key = VerifyKey(public_key)
                try:
                    verify_key.verify(data, signature)
                    return True
                except:
                    return False
            else:
                # Fallback verification
                expected_signature = hashlib.sha256(data + public_key).digest()
                return signature == expected_signature
            
        except Exception as e:
            logger.error("Failed to verify signature", error=str(e))
            return False
    
    async def _save_wallet(self, wallet: Wallet):
        """Save wallet to storage"""
        try:
            wallet_file = self.storage_path / f"{wallet.wallet_id}.json"
            
            wallet_data = {
                'wallet_id': wallet.wallet_id,
                'name': wallet.name,
                'status': wallet.status.value,
                'created_at': wallet.created_at.isoformat(),
                'last_accessed': wallet.last_accessed.isoformat(),
                'keys': wallet.keys,
                'metadata': wallet.metadata or {}
            }
            
            with open(wallet_file, 'w') as f:
                json.dump(wallet_data, f, indent=2)
            
        except Exception as e:
            logger.error("Failed to save wallet", error=str(e))
    
    async def _save_key(self, key_pair: KeyPair):
        """Save key to storage"""
        try:
            key_file = self.storage_path / f"{key_pair.key_id}.json"
            
            key_data = {
                'key_id': key_pair.key_id,
                'key_type': key_pair.key_type.value,
                'private_key': base64.b64encode(key_pair.private_key).decode(),
                'public_key': base64.b64encode(key_pair.public_key).decode(),
                'created_at': key_pair.created_at.isoformat(),
                'expires_at': key_pair.expires_at.isoformat() if key_pair.expires_at else None,
                'metadata': key_pair.metadata or {}
            }
            
            with open(key_file, 'w') as f:
                json.dump(key_data, f, indent=2)
            
        except Exception as e:
            logger.error("Failed to save key", error=str(e))
    
    async def _load_wallets(self):
        """Load wallets from storage"""
        try:
            for wallet_file in self.storage_path.glob("wallet_*.json"):
                with open(wallet_file, 'r') as f:
                    wallet_data = json.load(f)
                
                wallet = Wallet(
                    wallet_id=wallet_data['wallet_id'],
                    name=wallet_data['name'],
                    status=WalletStatus(wallet_data['status']),
                    created_at=datetime.fromisoformat(wallet_data['created_at']),
                    last_accessed=datetime.fromisoformat(wallet_data['last_accessed']),
                    keys=wallet_data['keys'],
                    metadata=wallet_data.get('metadata', {})
                )
                
                self.wallets[wallet.wallet_id] = wallet
            
            logger.info(f"Loaded {len(self.wallets)} wallets")
            
        except Exception as e:
            logger.error("Failed to load wallets", error=str(e))
    
    async def _load_keys(self):
        """Load keys from storage"""
        try:
            for key_file in self.storage_path.glob("key_*.json"):
                with open(key_file, 'r') as f:
                    key_data = json.load(f)
                
                key_pair = KeyPair(
                    key_id=key_data['key_id'],
                    key_type=KeyType(key_data['key_type']),
                    private_key=base64.b64decode(key_data['private_key']),
                    public_key=base64.b64decode(key_data['public_key']),
                    created_at=datetime.fromisoformat(key_data['created_at']),
                    expires_at=datetime.fromisoformat(key_data['expires_at']) if key_data['expires_at'] else None,
                    metadata=key_data.get('metadata', {})
                )
                
                self.keys[key_pair.key_id] = key_pair
            
            logger.info(f"Loaded {len(self.keys)} keys")
            
        except Exception as e:
            logger.error("Failed to load keys", error=str(e))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get wallet manager statistics"""
        return {
            **self.stats,
            'wallets_count': len(self.wallets),
            'keys_count': len(self.keys),
            'is_initialized': self.is_initialized,
            'libsodium_available': LIBSODIUM_AVAILABLE
        }


class WalletService:
    """Service for managing wallet operations"""
    
    def __init__(self):
        self.wallet_manager = WalletManager()
        self.is_running = False
    
    async def start(self):
        """Start the wallet service"""
        try:
            await self.wallet_manager.initialize()
            self.is_running = True
            logger.info("Wallet service started")
        except Exception as e:
            logger.error("Failed to start wallet service", error=str(e))
            raise
    
    async def stop(self):
        """Stop the wallet service"""
        self.is_running = False
        logger.info("Wallet service stopped")
    
    async def create_wallet(self, name: str, key_type: KeyType = KeyType.ED25519) -> Optional[str]:
        """Create a new wallet"""
        return await self.wallet_manager.create_wallet(name, key_type)
    
    async def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """Get wallet by ID"""
        return await self.wallet_manager.get_wallet(wallet_id)
    
    async def get_key(self, key_id: str, decrypt: bool = False) -> Optional[KeyPair]:
        """Get key by ID"""
        return await self.wallet_manager.get_key(key_id, decrypt)
    
    async def sign_data(self, wallet_id: str, key_id: str, data: bytes) -> Optional[bytes]:
        """Sign data with wallet key"""
        return await self.wallet_manager.sign_data(wallet_id, key_id, data)
    
    async def verify_signature(self, public_key: bytes, data: bytes, signature: bytes) -> bool:
        """Verify signature"""
        return await self.wallet_manager.verify_signature(public_key, data, signature)
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return self.wallet_manager.get_stats()


async def main():
    """Main entry point for wallet daemon"""
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
    service = WalletService()
    
    try:
        await service.start()
        
        # Keep running
        logger.info("Wallet daemon running")
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
