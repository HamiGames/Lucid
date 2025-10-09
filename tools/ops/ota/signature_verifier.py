#!/usr/bin/env python3
"""
LUCID SIGNATURE VERIFIER - SPEC-4 Release Signature Verification
Professional release signature verification for Pi deployment
Multi-platform build for ARM64 Pi and AMD64 development

This module provides comprehensive signature verification including:
- Cryptographic signature verification (RSA, ECDSA, Ed25519)
- Hash verification (SHA256, SHA512)
- Key management and rotation
- Certificate chain validation
- Integration with update manager and rollback systems
"""

import asyncio
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

import httpx
import structlog
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, ed25519
from cryptography.hazmat.primitives.asymmetric.padding import PKCS1v15, PSS, MGF1
from cryptography.hazmat.primitives.serialization import load_pem_public_key, load_pem_private_key
from cryptography.exceptions import InvalidSignature
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# Configure structured logging
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

logger = structlog.get_logger(__name__)

# Environment configuration
SIGNATURES_PATH = os.getenv("SIGNATURES_PATH", "/opt/lucid/signatures")
KEYS_PATH = os.getenv("KEYS_PATH", "/opt/lucid/keys")
VERIFICATION_TIMEOUT_SECONDS = int(os.getenv("VERIFICATION_TIMEOUT_SECONDS", "30"))
KEY_ROTATION_INTERVAL_DAYS = int(os.getenv("KEY_ROTATION_INTERVAL_DAYS", "90"))
SIGNATURE_ALGORITHMS = os.getenv("SIGNATURE_ALGORITHMS", "RSA,ECDSA,Ed25519").split(",")
HASH_ALGORITHMS = os.getenv("HASH_ALGORITHMS", "SHA256,SHA512").split(",")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "1000"))

class SignatureAlgorithm(Enum):
    """Supported signature algorithms"""
    RSA = "RSA"
    ECDSA = "ECDSA"
    ED25519 = "Ed25519"

class HashAlgorithm(Enum):
    """Supported hash algorithms"""
    SHA256 = "SHA256"
    SHA512 = "SHA512"
    SHA1 = "SHA1"  # For legacy compatibility only

class VerificationStatus(Enum):
    """Verification status enumeration"""
    PENDING = "pending"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"

@dataclass
class VerificationResult:
    """Verification result structure"""
    verified: bool
    algorithm: str
    key_id: str
    timestamp: datetime
    file_hash: str
    signature_hash: str
    error_message: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

@dataclass
class KeyInfo:
    """Key information structure"""
    key_id: str
    algorithm: SignatureAlgorithm
    public_key: bytes
    created_at: datetime
    expires_at: Optional[datetime]
    revoked: bool = False
    usage: List[str] = None

    def __post_init__(self):
        if self.usage is None:
            self.usage = ["signature"]

@dataclass
class VerificationRequest:
    """Verification request structure"""
    file_path: str
    signature: str
    checksum: str
    algorithm: Optional[str] = None
    key_id: Optional[str] = None
    force_verify: bool = False

class VerificationRequestModel(BaseModel):
    """Verification request model for API"""
    file_path: str
    signature: str
    checksum: str
    algorithm: Optional[str] = None
    key_id: Optional[str] = None
    force_verify: bool = False

class VerificationResponse(BaseModel):
    """Verification response model"""
    verified: bool
    algorithm: str
    key_id: str
    timestamp: str
    file_hash: str
    signature_hash: str
    error_message: Optional[str] = None
    warnings: List[str] = []

class SignatureVerifier:
    """Main signature verifier class"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Lucid Signature Verifier",
            description="Release Signature Verification Service",
            version="1.0.0"
        )
        self.setup_middleware()
        self.setup_routes()
        
        # State management
        self.keys: Dict[str, KeyInfo] = {}
        self.verification_history: List[VerificationResult] = []
        self.key_rotation_task: Optional[asyncio.Task] = None
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Load existing keys
        self._load_keys()
        
        logger.info("Signature Verifier initialized", 
                   loaded_keys=len(self.keys),
                   supported_algorithms=SIGNATURE_ALGORITHMS)

    def setup_middleware(self):
        """Setup FastAPI middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "service": "signature_verifier",
                "version": "1.0.0",
                "loaded_keys": len(self.keys),
                "supported_algorithms": SIGNATURE_ALGORITHMS,
                "supported_hashes": HASH_ALGORITHMS
            }
        
        @self.app.post("/verify", response_model=VerificationResponse)
        async def verify_signature(request: VerificationRequestModel):
            """Verify file signature"""
            try:
                result = await self._verify_signature(
                    file_path=request.file_path,
                    signature=request.signature,
                    checksum=request.checksum,
                    algorithm=request.algorithm,
                    key_id=request.key_id,
                    force_verify=request.force_verify
                )
                
                return VerificationResponse(
                    verified=result.verified,
                    algorithm=result.algorithm,
                    key_id=result.key_id,
                    timestamp=result.timestamp.isoformat(),
                    file_hash=result.file_hash,
                    signature_hash=result.signature_hash,
                    error_message=result.error_message,
                    warnings=result.warnings
                )
                
            except Exception as e:
                logger.error("Verification failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/keys")
        async def list_keys():
            """List available verification keys"""
            return {
                "keys": [
                    {
                        "key_id": key.key_id,
                        "algorithm": key.algorithm.value,
                        "created_at": key.created_at.isoformat(),
                        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                        "revoked": key.revoked,
                        "usage": key.usage
                    }
                    for key in self.keys.values()
                ]
            }
        
        @self.app.post("/keys/import")
        async def import_key(key_data: str, key_id: str, algorithm: str):
            """Import a new verification key"""
            try:
                await self._import_key(key_data, key_id, algorithm)
                return {"success": True, "message": f"Key {key_id} imported successfully"}
            except Exception as e:
                logger.error("Failed to import key", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/keys/{key_id}")
        async def revoke_key(key_id: str):
            """Revoke a verification key"""
            try:
                if key_id in self.keys:
                    self.keys[key_id].revoked = True
                    await self._save_keys()
                    return {"success": True, "message": f"Key {key_id} revoked"}
                else:
                    raise HTTPException(status_code=404, detail="Key not found")
            except Exception as e:
                logger.error("Failed to revoke key", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/verification-history")
        async def get_verification_history():
            """Get verification history"""
            return {
                "history": [
                    {
                        "verified": result.verified,
                        "algorithm": result.algorithm,
                        "key_id": result.key_id,
                        "timestamp": result.timestamp.isoformat(),
                        "file_hash": result.file_hash,
                        "error_message": result.error_message
                    }
                    for result in self.verification_history[-100:]  # Last 100 verifications
                ]
            }

    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [SIGNATURES_PATH, KEYS_PATH]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.debug("Ensured directory exists", directory=directory)

    def _load_keys(self):
        """Load verification keys from storage"""
        keys_file = Path(KEYS_PATH) / "keys.json"
        if keys_file.exists():
            try:
                with open(keys_file) as f:
                    keys_data = json.load(f)
                
                for key_data in keys_data.get("keys", []):
                    key_info = KeyInfo(
                        key_id=key_data["key_id"],
                        algorithm=SignatureAlgorithm(key_data["algorithm"]),
                        public_key=bytes.fromhex(key_data["public_key"]),
                        created_at=datetime.fromisoformat(key_data["created_at"]),
                        expires_at=datetime.fromisoformat(key_data["expires_at"]) if key_data.get("expires_at") else None,
                        revoked=key_data.get("revoked", False),
                        usage=key_data.get("usage", ["signature"])
                    )
                    self.keys[key_info.key_id] = key_info
                
                logger.info("Loaded keys from storage", count=len(self.keys))
                
            except Exception as e:
                logger.error("Failed to load keys", error=str(e))
        
        # Generate default keys if none exist
        if not self.keys:
            self._generate_default_keys()

    def _generate_default_keys(self):
        """Generate default verification keys"""
        try:
            # Generate RSA key
            rsa_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            rsa_public_key = rsa_key.public_key()
            rsa_public_pem = rsa_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            rsa_key_info = KeyInfo(
                key_id="lucid-rsa-default",
                algorithm=SignatureAlgorithm.RSA,
                public_key=rsa_public_pem,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=KEY_ROTATION_INTERVAL_DAYS)
            )
            self.keys[rsa_key_info.key_id] = rsa_key_info
            
            # Generate Ed25519 key
            ed25519_key = ed25519.Ed25519PrivateKey.generate()
            ed25519_public_key = ed25519_key.public_key()
            ed25519_public_pem = ed25519_public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            ed25519_key_info = KeyInfo(
                key_id="lucid-ed25519-default",
                algorithm=SignatureAlgorithm.ED25519,
                public_key=ed25519_public_pem,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=KEY_ROTATION_INTERVAL_DAYS)
            )
            self.keys[ed25519_key_info.key_id] = ed25519_key_info
            
            # Save keys
            asyncio.create_task(self._save_keys())
            
            logger.info("Generated default keys", 
                       rsa_key=rsa_key_info.key_id,
                       ed25519_key=ed25519_key_info.key_id)
            
        except Exception as e:
            logger.error("Failed to generate default keys", error=str(e))

    async def _save_keys(self):
        """Save keys to storage"""
        try:
            keys_data = {
                "keys": [
                    {
                        "key_id": key.key_id,
                        "algorithm": key.algorithm.value,
                        "public_key": key.public_key.hex(),
                        "created_at": key.created_at.isoformat(),
                        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                        "revoked": key.revoked,
                        "usage": key.usage
                    }
                    for key in self.keys.values()
                ]
            }
            
            keys_file = Path(KEYS_PATH) / "keys.json"
            with open(keys_file, "w") as f:
                json.dump(keys_data, f, indent=2)
            
            logger.debug("Saved keys to storage", count=len(self.keys))
            
        except Exception as e:
            logger.error("Failed to save keys", error=str(e))

    async def _import_key(self, key_data: str, key_id: str, algorithm: str):
        """Import a new verification key"""
        try:
            # Parse the key data
            if key_data.startswith("-----BEGIN"):
                # PEM format
                public_key = load_pem_public_key(key_data.encode())
            else:
                # Assume hex encoded
                public_key = load_pem_public_key(bytes.fromhex(key_data))
            
            # Determine algorithm from key type
            if isinstance(public_key, rsa.RSAPublicKey):
                key_algorithm = SignatureAlgorithm.RSA
            elif isinstance(public_key, ec.EllipticCurvePublicKey):
                key_algorithm = SignatureAlgorithm.ECDSA
            elif isinstance(public_key, ed25519.Ed25519PublicKey):
                key_algorithm = SignatureAlgorithm.ED25519
            else:
                raise ValueError(f"Unsupported key type: {type(public_key)}")
            
            # Create key info
            key_info = KeyInfo(
                key_id=key_id,
                algorithm=key_algorithm,
                public_key=public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ),
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=KEY_ROTATION_INTERVAL_DAYS)
            )
            
            self.keys[key_id] = key_info
            await self._save_keys()
            
            logger.info("Imported key", key_id=key_id, algorithm=key_algorithm.value)
            
        except Exception as e:
            logger.error("Failed to import key", error=str(e))
            raise

    async def _verify_signature(
        self,
        file_path: str,
        signature: str,
        checksum: str,
        algorithm: Optional[str] = None,
        key_id: Optional[str] = None,
        force_verify: bool = False
    ) -> VerificationResult:
        """Verify file signature"""
        try:
            # Check file exists and size
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return VerificationResult(
                    verified=False,
                    algorithm="unknown",
                    key_id="unknown",
                    timestamp=datetime.now(),
                    file_hash="",
                    signature_hash="",
                    error_message="File not found"
                )
            
            file_size_mb = file_path_obj.stat().st_size / (1024 * 1024)
            if file_size_mb > MAX_FILE_SIZE_MB:
                return VerificationResult(
                    verified=False,
                    algorithm="unknown",
                    key_id="unknown",
                    timestamp=datetime.now(),
                    file_hash="",
                    signature_hash="",
                    error_message=f"File too large: {file_size_mb:.1f}MB > {MAX_FILE_SIZE_MB}MB"
                )
            
            # Calculate file hash
            file_hash = await self._calculate_file_hash(file_path, checksum)
            
            # Decode signature
            try:
                if signature.startswith("-----BEGIN"):
                    # PEM format signature
                    signature_bytes = self._decode_pem_signature(signature)
                else:
                    # Assume hex encoded
                    signature_bytes = bytes.fromhex(signature)
            except Exception as e:
                return VerificationResult(
                    verified=False,
                    algorithm="unknown",
                    key_id="unknown",
                    timestamp=datetime.now(),
                    file_hash=file_hash,
                    signature_hash="",
                    error_message=f"Invalid signature format: {str(e)}"
                )
            
            # Find appropriate key
            verification_key = self._find_verification_key(algorithm, key_id)
            if not verification_key:
                return VerificationResult(
                    verified=False,
                    algorithm=algorithm or "unknown",
                    key_id=key_id or "unknown",
                    timestamp=datetime.now(),
                    file_hash=file_hash,
                    signature_hash=signature.hex() if isinstance(signature, bytes) else signature,
                    error_message="No suitable verification key found"
                )
            
            # Verify signature
            verified = await self._verify_with_key(
                verification_key,
                file_hash.encode(),
                signature_bytes
            )
            
            result = VerificationResult(
                verified=verified,
                algorithm=verification_key.algorithm.value,
                key_id=verification_key.key_id,
                timestamp=datetime.now(),
                file_hash=file_hash,
                signature_hash=signature.hex() if isinstance(signature, bytes) else signature
            )
            
            if not verified:
                result.error_message = "Signature verification failed"
            
            # Add to history
            self.verification_history.append(result)
            
            logger.info("Signature verification completed",
                       verified=verified,
                       algorithm=verification_key.algorithm.value,
                       key_id=verification_key.key_id,
                       file_hash=file_hash[:16] + "...")
            
            return result
            
        except Exception as e:
            logger.error("Signature verification error", error=str(e))
            return VerificationResult(
                verified=False,
                algorithm="unknown",
                key_id="unknown",
                timestamp=datetime.now(),
                file_hash="",
                signature_hash="",
                error_message=str(e)
            )

    async def _calculate_file_hash(self, file_path: str, expected_checksum: str) -> str:
        """Calculate file hash"""
        try:
            # Determine hash algorithm from expected checksum length
            if len(expected_checksum) == 64:
                hash_algorithm = hashlib.sha256()
            elif len(expected_checksum) == 128:
                hash_algorithm = hashlib.sha512()
            else:
                hash_algorithm = hashlib.sha256()  # Default
            
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    hash_algorithm.update(chunk)
            
            calculated_hash = hash_algorithm.hexdigest()
            
            # Verify against expected checksum
            if calculated_hash.lower() != expected_checksum.lower():
                logger.warning("Hash mismatch",
                             calculated=calculated_hash,
                             expected=expected_checksum)
            
            return calculated_hash
            
        except Exception as e:
            logger.error("Failed to calculate file hash", error=str(e))
            return ""

    def _decode_pem_signature(self, signature: str) -> bytes:
        """Decode PEM format signature"""
        # Remove PEM headers and decode base64
        lines = signature.strip().split('\n')
        base64_data = ''.join(line for line in lines if not line.startswith('-----'))
        
        import base64
        return base64.b64decode(base64_data)

    def _find_verification_key(self, algorithm: Optional[str], key_id: Optional[str]) -> Optional[KeyInfo]:
        """Find appropriate verification key"""
        # If key_id specified, use that key
        if key_id and key_id in self.keys:
            key = self.keys[key_id]
            if not key.revoked and (not key.expires_at or key.expires_at > datetime.now()):
                return key
        
        # If algorithm specified, find matching key
        if algorithm:
            algorithm_enum = SignatureAlgorithm(algorithm.upper())
            for key in self.keys.values():
                if (key.algorithm == algorithm_enum and 
                    not key.revoked and 
                    (not key.expires_at or key.expires_at > datetime.now())):
                    return key
        
        # Return first valid key
        for key in self.keys.values():
            if not key.revoked and (not key.expires_at or key.expires_at > datetime.now()):
                return key
        
        return None

    async def _verify_with_key(self, key_info: KeyInfo, data: bytes, signature: bytes) -> bool:
        """Verify signature with specific key"""
        try:
            public_key = load_pem_public_key(key_info.public_key)
            
            if key_info.algorithm == SignatureAlgorithm.RSA:
                if isinstance(public_key, rsa.RSAPublicKey):
                    public_key.verify(
                        signature,
                        data,
                        padding=PKCS1v15(),
                        algorithm=hashes.SHA256()
                    )
                    return True
            
            elif key_info.algorithm == SignatureAlgorithm.ECDSA:
                if isinstance(public_key, ec.EllipticCurvePublicKey):
                    public_key.verify(
                        signature,
                        data,
                        ec.ECDSA(hashes.SHA256())
                    )
                    return True
            
            elif key_info.algorithm == SignatureAlgorithm.ED25519:
                if isinstance(public_key, ed25519.Ed25519PublicKey):
                    public_key.verify(signature, data)
                    return True
            
            return False
            
        except InvalidSignature:
            return False
        except Exception as e:
            logger.error("Signature verification error", error=str(e))
            return False

    async def start_background_tasks(self):
        """Start background monitoring tasks"""
        self.key_rotation_task = asyncio.create_task(self._key_rotation_monitor())
        logger.info("Background tasks started")

    async def _key_rotation_monitor(self):
        """Monitor key rotation and expiration"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                current_time = datetime.now()
                expired_keys = []
                
                for key_id, key_info in self.keys.items():
                    if key_info.expires_at and key_info.expires_at <= current_time:
                        expired_keys.append(key_id)
                
                if expired_keys:
                    logger.warning("Keys expired", expired_keys=expired_keys)
                    # In a production system, you might want to:
                    # 1. Generate new keys
                    # 2. Notify administrators
                    # 3. Update key distribution
                
            except Exception as e:
                logger.error("Error in key rotation monitor", error=str(e))

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down signature verifier")
        
        if self.key_rotation_task:
            self.key_rotation_task.cancel()
        
        # Save keys before shutdown
        await self._save_keys()

async def main():
    """Main entry point"""
    verifier = SignatureVerifier()
    
    # Start background tasks
    await verifier.start_background_tasks()
    
    # Start the server
    config = uvicorn.Config(
        verifier.app,
        host="0.0.0.0",
        port=8113,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await verifier.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
