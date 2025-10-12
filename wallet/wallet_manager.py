# Path: wallet/wallet_manager.py

from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import secrets
from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)


@dataclass
class WalletInfo:
    """Wallet information."""
    wallet_id: str
    address: str
    public_key: str
    created_at: datetime
    wallet_type: str = "software"  # software, hardware, multisig
    is_encrypted: bool = True
    
    def to_dict(self) -> dict:
        return {
            "wallet_id": self.wallet_id,
            "address": self.address,
            "public_key": self.public_key,
            "created_at": self.created_at.isoformat(),
            "wallet_type": self.wallet_type,
            "is_encrypted": self.is_encrypted
        }


class WalletManager:
    """
    Manages cryptographic wallets for Lucid RDP.
    Supports software and hardware wallet integration.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, wallet_dir: Optional[str] = None):
        self.db = db
        self.wallet_dir = Path(wallet_dir or "./data/wallets")
        self.wallet_dir.mkdir(parents=True, exist_ok=True)
        self.active_wallets: Dict[str, Any] = {}
        
    async def create_wallet(
        self,
        wallet_id: str,
        passphrase: Optional[str] = None,
        wallet_type: str = "software"
    ) -> WalletInfo:
        """Create a new wallet."""
        try:
            # Generate Ed25519 key pair
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            # Serialize keys
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.BestAvailableEncryption(
                    passphrase.encode() if passphrase else b""
                )
            )
            
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            # Generate address (simplified)
            address = self._generate_address(public_key)
            
            # Save wallet file
            wallet_file = self.wallet_dir / f"{wallet_id}.json"
            wallet_data = {
                "wallet_id": wallet_id,
                "address": address,
                "public_key": public_pem.decode(),
                "private_key": private_pem.decode(),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "wallet_type": wallet_type,
                "is_encrypted": bool(passphrase)
            }
            
            with open(wallet_file, 'w') as f:
                json.dump(wallet_data, f, indent=2)
                
            # Create wallet info
            wallet_info = WalletInfo(
                wallet_id=wallet_id,
                address=address,
                public_key=public_pem.decode(),
                created_at=datetime.now(timezone.utc),
                wallet_type=wallet_type,
                is_encrypted=bool(passphrase)
            )
            
            # Store in database
            await self.db["wallets"].insert_one(wallet_info.to_dict())
            
            logger.info(f"Created wallet: {wallet_id}")
            return wallet_info
            
        except Exception as e:
            logger.error(f"Failed to create wallet: {e}")
            raise
            
    def _generate_address(self, public_key: ed25519.Ed25519PublicKey) -> str:
        """Generate address from public key."""
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        # Simplified address generation
        digest = hashes.Hash(hashes.BLAKE2b(20))
        digest.update(public_bytes)
        return f"lucid{digest.finalize().hex()}"
        
    async def load_wallet(self, wallet_id: str, passphrase: Optional[str] = None) -> bool:
        """Load wallet into memory."""
        try:
            wallet_file = self.wallet_dir / f"{wallet_id}.json"
            if not wallet_file.exists():
                return False
                
            with open(wallet_file, 'r') as f:
                wallet_data = json.load(f)
                
            # Load private key
            private_pem = wallet_data["private_key"].encode()
            private_key = serialization.load_pem_private_key(
                private_pem,
                password=passphrase.encode() if passphrase else None
            )
            
            self.active_wallets[wallet_id] = {
                "private_key": private_key,
                "public_key": private_key.public_key(),
                "address": wallet_data["address"],
                "wallet_type": wallet_data["wallet_type"]
            }
            
            logger.info(f"Loaded wallet: {wallet_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load wallet: {e}")
            return False
            
    async def sign_transaction(
        self,
        wallet_id: str,
        transaction_data: bytes
    ) -> Optional[bytes]:
        """Sign transaction with wallet."""
        try:
            if wallet_id not in self.active_wallets:
                logger.error(f"Wallet {wallet_id} not loaded")
                return None
                
            private_key = self.active_wallets[wallet_id]["private_key"]
            signature = private_key.sign(transaction_data)
            
            return signature
            
        except Exception as e:
            logger.error(f"Failed to sign transaction: {e}")
            return None
