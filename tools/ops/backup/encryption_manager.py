#!/usr/bin/env python3
"""
LUCID BACKUP ENCRYPTION MANAGER - SPEC-4 Backup Encryption System
Professional backup encryption for Pi deployment
Multi-platform build for ARM64 Pi and AMD64 development

This module provides comprehensive backup encryption including:
- Multi-algorithm encryption support (AES-256-GCM, ChaCha20-Poly1305)
- Key management and rotation
- Encrypted backup creation and restoration
- Integrity verification with HMAC
- Integration with backup systems and storage
- Hardware acceleration support
"""

import asyncio
import hashlib
import json
import logging
import os
import secrets
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union, BinaryIO
from dataclasses import dataclass, asdict
from enum import Enum

import httpx
import structlog
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.hmac import HMAC
from cryptography.exceptions import InvalidTag
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile
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
BACKUP_PATH = os.getenv("BACKUP_PATH", "/opt/lucid/backups")
KEYS_PATH = os.getenv("KEYS_PATH", "/opt/lucid/backup_keys")
ENCRYPTION_PATH = os.getenv("ENCRYPTION_PATH", "/opt/lucid/encrypted")
ENCRYPTION_TIMEOUT_SECONDS = int(os.getenv("ENCRYPTION_TIMEOUT_SECONDS", "600"))
KEY_ROTATION_INTERVAL_DAYS = int(os.getenv("KEY_ROTATION_INTERVAL_DAYS", "30"))
MAX_FILE_SIZE_GB = int(os.getenv("MAX_FILE_SIZE_GB", "100"))
ENCRYPTION_ALGORITHMS = os.getenv("ENCRYPTION_ALGORITHMS", "AES256GCM,ChaCha20Poly1305").split(",")
KDF_ALGORITHMS = os.getenv("KDF_ALGORITHMS", "PBKDF2,Scrypt").split(",")

class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms"""
    AES256GCM = "AES-256-GCM"
    AES256CBC = "AES-256-CBC"
    CHACHA20POLY1305 = "ChaCha20-Poly1305"

class KDFAlgorithm(Enum):
    """Supported Key Derivation Functions"""
    PBKDF2 = "PBKDF2"
    SCRYPT = "Scrypt"
    HKDF = "HKDF"

class EncryptionStatus(Enum):
    """Encryption operation status"""
    PENDING = "pending"
    ENCRYPTING = "encrypting"
    DECRYPTING = "decrypting"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFYING = "verifying"

class KeyStatus(Enum):
    """Key status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"

@dataclass
class EncryptionKey:
    """Encryption key structure"""
    key_id: str
    algorithm: EncryptionAlgorithm
    key_data: bytes
    created_at: datetime
    expires_at: Optional[datetime]
    status: KeyStatus
    usage_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class EncryptionOperation:
    """Encryption operation structure"""
    operation_id: str
    operation_type: str  # "encrypt" or "decrypt"
    file_path: str
    status: EncryptionStatus
    algorithm: EncryptionAlgorithm
    key_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    file_size: int = 0
    encrypted_size: int = 0
    error_message: Optional[str] = None
    checksum: Optional[str] = None

@dataclass
class EncryptionConfig:
    """Encryption configuration"""
    algorithm: EncryptionAlgorithm
    kdf_algorithm: KDFAlgorithm
    key_size: int
    iv_size: int
    tag_size: int
    salt_size: int
    iterations: int
    memory_cost: int
    parallel_cost: int

class EncryptionRequest(BaseModel):
    """Encryption request model"""
    file_path: str
    algorithm: Optional[str] = None
    key_id: Optional[str] = None
    password: Optional[str] = None
    compress: bool = True
    verify_integrity: bool = True

class EncryptionResponse(BaseModel):
    """Encryption response model"""
    success: bool
    message: str
    operation_id: str
    encrypted_file_path: str
    checksum: str
    algorithm: str
    key_id: str

class DecryptionRequest(BaseModel):
    """Decryption request model"""
    encrypted_file_path: str
    key_id: Optional[str] = None
    password: Optional[str] = None
    verify_integrity: bool = True

class DecryptionResponse(BaseModel):
    """Decryption response model"""
    success: bool
    message: str
    operation_id: str
    decrypted_file_path: str
    checksum: str
    algorithm: str
    key_id: str

class KeyGenerationRequest(BaseModel):
    """Key generation request model"""
    algorithm: str
    key_id: Optional[str] = None
    expires_in_days: int = KEY_ROTATION_INTERVAL_DAYS

class EncryptionManager:
    """Main encryption manager class"""
    
    def __init__(self):
        self.app = FastAPI(
            title="Lucid Backup Encryption Manager",
            description="Backup Encryption Service",
            version="1.0.0"
        )
        self.setup_middleware()
        self.setup_routes()
        
        # State management
        self.keys: Dict[str, EncryptionKey] = {}
        self.active_operations: Dict[str, EncryptionOperation] = {}
        self.operation_history: List[EncryptionOperation] = []
        self.default_configs: Dict[EncryptionAlgorithm, EncryptionConfig] = {}
        
        # Background tasks
        self.key_rotation_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Initialize default configurations
        self._init_default_configs()
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Load existing keys
        self._load_keys()
        
        # Generate default keys if none exist
        if not self.keys:
            self._generate_default_keys()
        
        logger.info("Encryption Manager initialized", 
                   loaded_keys=len(self.keys),
                   supported_algorithms=ENCRYPTION_ALGORITHMS)

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
                "service": "encryption_manager",
                "version": "1.0.0",
                "loaded_keys": len(self.keys),
                "supported_algorithms": ENCRYPTION_ALGORITHMS,
                "active_operations": len(self.active_operations)
            }
        
        @self.app.post("/encrypt", response_model=EncryptionResponse)
        async def encrypt_file(request: EncryptionRequest, background_tasks: BackgroundTasks):
            """Encrypt a file"""
            try:
                operation_id = f"encrypt_{int(time.time())}_{secrets.token_hex(8)}"
                background_tasks.add_task(self._execute_encryption, operation_id, request)
                
                return EncryptionResponse(
                    success=True,
                    message="Encryption started",
                    operation_id=operation_id,
                    encrypted_file_path="",  # Will be updated when operation completes
                    checksum="",
                    algorithm=request.algorithm or "AES-256-GCM",
                    key_id=request.key_id or "default"
                )
            except Exception as e:
                logger.error("Failed to start encryption", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/decrypt", response_model=DecryptionResponse)
        async def decrypt_file(request: DecryptionRequest, background_tasks: BackgroundTasks):
            """Decrypt a file"""
            try:
                operation_id = f"decrypt_{int(time.time())}_{secrets.token_hex(8)}"
                background_tasks.add_task(self._execute_decryption, operation_id, request)
                
                return DecryptionResponse(
                    success=True,
                    message="Decryption started",
                    operation_id=operation_id,
                    decrypted_file_path="",  # Will be updated when operation completes
                    checksum="",
                    algorithm="",  # Will be determined from encrypted file
                    key_id=request.key_id or "default"
                )
            except Exception as e:
                logger.error("Failed to start decryption", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/keys/generate")
        async def generate_key(request: KeyGenerationRequest):
            """Generate a new encryption key"""
            try:
                key = await self._generate_key(
                    algorithm=request.algorithm,
                    key_id=request.key_id,
                    expires_in_days=request.expires_in_days
                )
                return {
                    "success": True,
                    "key_id": key.key_id,
                    "algorithm": key.algorithm.value,
                    "created_at": key.created_at.isoformat(),
                    "expires_at": key.expires_at.isoformat() if key.expires_at else None
                }
            except Exception as e:
                logger.error("Failed to generate key", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/keys")
        async def list_keys():
            """List available encryption keys"""
            return {
                "keys": [
                    {
                        "key_id": key.key_id,
                        "algorithm": key.algorithm.value,
                        "created_at": key.created_at.isoformat(),
                        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                        "status": key.status.value,
                        "usage_count": key.usage_count
                    }
                    for key in self.keys.values()
                ]
            }
        
        @self.app.get("/operation/{operation_id}")
        async def get_operation_status(operation_id: str):
            """Get operation status"""
            if operation_id in self.active_operations:
                return asdict(self.active_operations[operation_id])
            else:
                # Check history
                for op in self.operation_history:
                    if op.operation_id == operation_id:
                        return asdict(op)
                raise HTTPException(status_code=404, detail="Operation not found")
        
        @self.app.get("/operations")
        async def list_operations():
            """List recent operations"""
            return {
                "active": [asdict(op) for op in self.active_operations.values()],
                "recent": [asdict(op) for op in self.operation_history[-20:]]
            }
        
        @self.app.post("/verify/{operation_id}")
        async def verify_operation(operation_id: str):
            """Verify operation integrity"""
            try:
                result = await self._verify_operation(operation_id)
                return {"success": True, "verified": result}
            except Exception as e:
                logger.error("Verification failed", operation_id=operation_id, error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

    def _init_default_configs(self):
        """Initialize default encryption configurations"""
        self.default_configs = {
            EncryptionAlgorithm.AES256GCM: EncryptionConfig(
                algorithm=EncryptionAlgorithm.AES256GCM,
                kdf_algorithm=KDFAlgorithm.PBKDF2,
                key_size=32,  # 256 bits
                iv_size=12,   # 96 bits for GCM
                tag_size=16,  # 128 bits
                salt_size=32, # 256 bits
                iterations=100000,
                memory_cost=0,
                parallel_cost=0
            ),
            EncryptionAlgorithm.CHACHA20POLY1305: EncryptionConfig(
                algorithm=EncryptionAlgorithm.CHACHA20POLY1305,
                kdf_algorithm=KDFAlgorithm.SCRYPT,
                key_size=32,  # 256 bits
                iv_size=12,   # 96 bits
                tag_size=16,  # 128 bits
                salt_size=32, # 256 bits
                iterations=0,
                memory_cost=16384,
                parallel_cost=1
            )
        }

    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [BACKUP_PATH, KEYS_PATH, ENCRYPTION_PATH]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.debug("Ensured directory exists", directory=directory)

    def _load_keys(self):
        """Load encryption keys from storage"""
        keys_file = Path(KEYS_PATH) / "keys.json"
        if keys_file.exists():
            try:
                with open(keys_file) as f:
                    keys_data = json.load(f)
                
                for key_data in keys_data.get("keys", []):
                    key = EncryptionKey(
                        key_id=key_data["key_id"],
                        algorithm=EncryptionAlgorithm(key_data["algorithm"]),
                        key_data=bytes.fromhex(key_data["key_data"]),
                        created_at=datetime.fromisoformat(key_data["created_at"]),
                        expires_at=datetime.fromisoformat(key_data["expires_at"]) if key_data.get("expires_at") else None,
                        status=KeyStatus(key_data["status"]),
                        usage_count=key_data.get("usage_count", 0),
                        metadata=key_data.get("metadata", {})
                    )
                    self.keys[key.key_id] = key
                
                logger.info("Loaded keys from storage", count=len(self.keys))
                
            except Exception as e:
                logger.error("Failed to load keys", error=str(e))

    async def _save_keys(self):
        """Save keys to storage"""
        try:
            keys_data = {
                "keys": [
                    {
                        "key_id": key.key_id,
                        "algorithm": key.algorithm.value,
                        "key_data": key.key_data.hex(),
                        "created_at": key.created_at.isoformat(),
                        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                        "status": key.status.value,
                        "usage_count": key.usage_count,
                        "metadata": key.metadata
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

    def _generate_default_keys(self):
        """Generate default encryption keys"""
        try:
            # Generate AES-256-GCM key
            aes_key = EncryptionKey(
                key_id="lucid-aes-default",
                algorithm=EncryptionAlgorithm.AES256GCM,
                key_data=secrets.token_bytes(32),
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=KEY_ROTATION_INTERVAL_DAYS),
                status=KeyStatus.ACTIVE
            )
            self.keys[aes_key.key_id] = aes_key
            
            # Generate ChaCha20-Poly1305 key
            chacha_key = EncryptionKey(
                key_id="lucid-chacha-default",
                algorithm=EncryptionAlgorithm.CHACHA20POLY1305,
                key_data=secrets.token_bytes(32),
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=KEY_ROTATION_INTERVAL_DAYS),
                status=KeyStatus.ACTIVE
            )
            self.keys[chacha_key.key_id] = chacha_key
            
            # Save keys
            asyncio.create_task(self._save_keys())
            
            logger.info("Generated default keys", 
                       aes_key=aes_key.key_id,
                       chacha_key=chacha_key.key_id)
            
        except Exception as e:
            logger.error("Failed to generate default keys", error=str(e))

    async def _generate_key(self, algorithm: str, key_id: Optional[str] = None, expires_in_days: int = 30) -> EncryptionKey:
        """Generate a new encryption key"""
        try:
            algorithm_enum = EncryptionAlgorithm(algorithm.upper().replace("-", ""))
            
            if not key_id:
                key_id = f"lucid-{algorithm.lower().replace('-', '')}-{int(time.time())}"
            
            # Generate key material
            key_data = secrets.token_bytes(32)  # 256 bits
            
            key = EncryptionKey(
                key_id=key_id,
                algorithm=algorithm_enum,
                key_data=key_data,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=expires_in_days),
                status=KeyStatus.ACTIVE
            )
            
            self.keys[key_id] = key
            await self._save_keys()
            
            logger.info("Generated new key", 
                       key_id=key_id,
                       algorithm=algorithm_enum.value)
            
            return key
            
        except Exception as e:
            logger.error("Failed to generate key", error=str(e))
            raise

    def _get_encryption_key(self, key_id: Optional[str], algorithm: Optional[str]) -> EncryptionKey:
        """Get encryption key by ID or algorithm"""
        if key_id and key_id in self.keys:
            key = self.keys[key_id]
            if key.status == KeyStatus.ACTIVE and (not key.expires_at or key.expires_at > datetime.now()):
                return key
        
        # Find key by algorithm
        if algorithm:
            algorithm_enum = EncryptionAlgorithm(algorithm.upper().replace("-", ""))
            for key in self.keys.values():
                if (key.algorithm == algorithm_enum and 
                    key.status == KeyStatus.ACTIVE and 
                    (not key.expires_at or key.expires_at > datetime.now())):
                    return key
        
        # Return first active key
        for key in self.keys.values():
            if key.status == KeyStatus.ACTIVE and (not key.expires_at or key.expires_at > datetime.now()):
                return key
        
        raise ValueError("No suitable encryption key found")

    async def _execute_encryption(self, operation_id: str, request: EncryptionRequest):
        """Execute file encryption"""
        try:
            # Validate file exists
            file_path = Path(request.file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {request.file_path}")
            
            file_size = file_path.stat().st_size
            
            # Check file size limit
            if file_size > MAX_FILE_SIZE_GB * 1024**3:
                raise ValueError(f"File too large: {file_size} bytes > {MAX_FILE_SIZE_GB}GB")
            
            # Get encryption key
            encryption_key = self._get_encryption_key(request.key_id, request.algorithm)
            
            # Create operation
            operation = EncryptionOperation(
                operation_id=operation_id,
                operation_type="encrypt",
                file_path=request.file_path,
                status=EncryptionStatus.ENCRYPTING,
                algorithm=encryption_key.algorithm,
                key_id=encryption_key.key_id,
                start_time=datetime.now(),
                file_size=file_size
            )
            
            self.active_operations[operation_id] = operation
            
            # Generate output path
            output_path = Path(ENCRYPTION_PATH) / f"{file_path.stem}_encrypted_{operation_id}{file_path.suffix}"
            
            # Perform encryption
            await self._encrypt_file(file_path, output_path, encryption_key, request)
            
            # Update operation
            operation.status = EncryptionStatus.COMPLETED
            operation.end_time = datetime.now()
            operation.encrypted_size = output_path.stat().st_size
            operation.checksum = await self._calculate_file_hash(output_path)
            
            # Update key usage
            encryption_key.usage_count += 1
            
            # Move to history
            self.operation_history.append(operation)
            del self.active_operations[operation_id]
            
            logger.info("Encryption completed",
                       operation_id=operation_id,
                       file_size=file_size,
                       encrypted_size=operation.encrypted_size)
            
        except Exception as e:
            logger.error("Encryption failed", operation_id=operation_id, error=str(e))
            if operation_id in self.active_operations:
                operation = self.active_operations[operation_id]
                operation.status = EncryptionStatus.FAILED
                operation.error_message = str(e)
                operation.end_time = datetime.now()
                self.operation_history.append(operation)
                del self.active_operations[operation_id]

    async def _encrypt_file(self, input_path: Path, output_path: Path, key: EncryptionKey, request: EncryptionRequest):
        """Encrypt a file"""
        try:
            config = self.default_configs[key.algorithm]
            
            # Generate salt and IV
            salt = secrets.token_bytes(config.salt_size)
            iv = secrets.token_bytes(config.iv_size)
            
            # Derive key from master key
            derived_key = await self._derive_key(key.key_data, salt, config)
            
            # Read and encrypt file
            with open(input_path, 'rb') as infile, open(output_path, 'wb') as outfile:
                # Write header
                header = {
                    "algorithm": key.algorithm.value,
                    "key_id": key.key_id,
                    "salt": salt.hex(),
                    "iv": iv.hex(),
                    "timestamp": datetime.now().isoformat(),
                    "original_size": input_path.stat().st_size,
                    "compressed": request.compress
                }
                
                header_json = json.dumps(header).encode('utf-8')
                header_size = len(header_json)
                
                # Write header size and header
                outfile.write(header_size.to_bytes(4, 'big'))
                outfile.write(header_json)
                
                # Initialize cipher
                if key.algorithm == EncryptionAlgorithm.AES256GCM:
                    cipher = Cipher(algorithms.AES(derived_key), modes.GCM(iv))
                    encryptor = cipher.encryptor()
                elif key.algorithm == EncryptionAlgorithm.CHACHA20POLY1305:
                    cipher = Cipher(algorithms.ChaCha20(derived_key, iv), modes.Poly1305())
                    encryptor = cipher.encryptor()
                else:
                    raise ValueError(f"Unsupported algorithm: {key.algorithm}")
                
                # Encrypt file data
                if request.compress:
                    # Compress before encryption
                    import gzip
                    with gzip.GzipFile(fileobj=infile, mode='rb') as gzfile:
                        data = gzfile.read()
                else:
                    data = infile.read()
                
                encrypted_data = encryptor.update(data) + encryptor.finalize()
                
                # Write encrypted data and tag
                outfile.write(encrypted_data)
                outfile.write(encryptor.tag)
                
                # Calculate and write HMAC for integrity
                if request.verify_integrity:
                    hmac_key = hashlib.sha256(derived_key + salt).digest()
                    hmac = HMAC(hmac_key, hashes.SHA256())
                    hmac.update(header_json + encrypted_data + encryptor.tag)
                    hmac_digest = hmac.finalize()
                    outfile.write(hmac_digest)
            
            logger.info("File encrypted successfully",
                       input_path=str(input_path),
                       output_path=str(output_path),
                       algorithm=key.algorithm.value)
            
        except Exception as e:
            logger.error("File encryption failed", error=str(e))
            raise

    async def _execute_decryption(self, operation_id: str, request: DecryptionRequest):
        """Execute file decryption"""
        try:
            # Validate encrypted file exists
            encrypted_path = Path(request.encrypted_file_path)
            if not encrypted_path.exists():
                raise FileNotFoundError(f"Encrypted file not found: {request.encrypted_file_path}")
            
            # Create operation
            operation = EncryptionOperation(
                operation_id=operation_id,
                operation_type="decrypt",
                file_path=request.encrypted_file_path,
                status=EncryptionStatus.DECRYPTING,
                algorithm=EncryptionAlgorithm.AES256GCM,  # Will be updated from file
                key_id=request.key_id or "unknown",
                start_time=datetime.now(),
                file_size=encrypted_path.stat().st_size
            )
            
            self.active_operations[operation_id] = operation
            
            # Read header and determine algorithm
            with open(encrypted_path, 'rb') as infile:
                header_size = int.from_bytes(infile.read(4), 'big')
                header_json = infile.read(header_size)
                header = json.loads(header_json.decode('utf-8'))
                
                algorithm = EncryptionAlgorithm(header['algorithm'])
                key_id = header['key_id']
                
                # Update operation
                operation.algorithm = algorithm
                operation.key_id = key_id
                
                # Get encryption key
                encryption_key = self._get_encryption_key(key_id, None)
                
                # Generate output path
                output_path = Path(ENCRYPTION_PATH) / f"{encrypted_path.stem}_decrypted_{operation_id}"
                
                # Perform decryption
                await self._decrypt_file(encrypted_path, output_path, encryption_key, header, request)
            
            # Update operation
            operation.status = EncryptionStatus.COMPLETED
            operation.end_time = datetime.now()
            operation.encrypted_size = output_path.stat().st_size
            operation.checksum = await self._calculate_file_hash(output_path)
            
            # Update key usage
            encryption_key.usage_count += 1
            
            # Move to history
            self.operation_history.append(operation)
            del self.active_operations[operation_id]
            
            logger.info("Decryption completed",
                       operation_id=operation_id,
                       original_size=operation.file_size,
                       decrypted_size=operation.encrypted_size)
            
        except Exception as e:
            logger.error("Decryption failed", operation_id=operation_id, error=str(e))
            if operation_id in self.active_operations:
                operation = self.active_operations[operation_id]
                operation.status = EncryptionStatus.FAILED
                operation.error_message = str(e)
                operation.end_time = datetime.now()
                self.operation_history.append(operation)
                del self.active_operations[operation_id]

    async def _decrypt_file(self, input_path: Path, output_path: Path, key: EncryptionKey, header: dict, request: DecryptionRequest):
        """Decrypt a file"""
        try:
            config = self.default_configs[key.algorithm]
            
            # Extract salt and IV from header
            salt = bytes.fromhex(header['salt'])
            iv = bytes.fromhex(header['iv'])
            
            # Derive key
            derived_key = await self._derive_key(key.key_data, salt, config)
            
            with open(input_path, 'rb') as infile:
                # Skip header
                header_size = int.from_bytes(infile.read(4), 'big')
                infile.seek(4 + header_size)
                
                # Read encrypted data
                remaining_data = infile.read()
                
                # Extract HMAC if present
                if request.verify_integrity:
                    hmac_digest = remaining_data[-32:]  # SHA256 HMAC is 32 bytes
                    encrypted_data_with_tag = remaining_data[:-32]
                else:
                    encrypted_data_with_tag = remaining_data
                
                # Extract tag
                tag = encrypted_data_with_tag[-config.tag_size:]
                encrypted_data = encrypted_data_with_tag[:-config.tag_size]
                
                # Verify HMAC if requested
                if request.verify_integrity:
                    hmac_key = hashlib.sha256(derived_key + salt).digest()
                    hmac = HMAC(hmac_key, hashes.SHA256())
                    hmac.update(remaining_data[:-32])  # All data except HMAC
                    expected_hmac = hmac.finalize()
                    
                    if not secrets.compare_digest(hmac_digest, expected_hmac):
                        raise InvalidTag("HMAC verification failed")
                
                # Initialize cipher
                if key.algorithm == EncryptionAlgorithm.AES256GCM:
                    cipher = Cipher(algorithms.AES(derived_key), modes.GCM(iv, tag))
                    decryptor = cipher.decryptor()
                elif key.algorithm == EncryptionAlgorithm.CHACHA20POLY1305:
                    cipher = Cipher(algorithms.ChaCha20(derived_key, iv), modes.Poly1305(tag))
                    decryptor = cipher.decryptor()
                else:
                    raise ValueError(f"Unsupported algorithm: {key.algorithm}")
                
                # Decrypt data
                decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
                
                # Decompress if needed
                if header.get('compressed', False):
                    import gzip
                    decrypted_data = gzip.decompress(decrypted_data)
                
                # Write decrypted data
                with open(output_path, 'wb') as outfile:
                    outfile.write(decrypted_data)
            
            logger.info("File decrypted successfully",
                       input_path=str(input_path),
                       output_path=str(output_path),
                       algorithm=key.algorithm.value)
            
        except Exception as e:
            logger.error("File decryption failed", error=str(e))
            raise

    async def _derive_key(self, master_key: bytes, salt: bytes, config: EncryptionConfig) -> bytes:
        """Derive encryption key from master key"""
        try:
            if config.kdf_algorithm == KDFAlgorithm.PBKDF2:
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=config.key_size,
                    salt=salt,
                    iterations=config.iterations
                )
                return kdf.derive(master_key)
            
            elif config.kdf_algorithm == KDFAlgorithm.SCRYPT:
                kdf = Scrypt(
                    length=config.key_size,
                    salt=salt,
                    n=config.memory_cost,
                    r=8,
                    p=config.parallel_cost
                )
                return kdf.derive(master_key)
            
            elif config.kdf_algorithm == KDFAlgorithm.HKDF:
                kdf = HKDF(
                    algorithm=hashes.SHA256(),
                    length=config.key_size,
                    salt=salt,
                    info=b'lucid-backup-encryption'
                )
                return kdf.derive(master_key)
            
            else:
                raise ValueError(f"Unsupported KDF algorithm: {config.kdf_algorithm}")
                
        except Exception as e:
            logger.error("Key derivation failed", error=str(e))
            raise

    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error("Failed to calculate file hash", error=str(e))
            return ""

    async def _verify_operation(self, operation_id: str) -> bool:
        """Verify operation integrity"""
        try:
            # Find operation
            operation = None
            for op in self.operation_history:
                if op.operation_id == operation_id:
                    operation = op
                    break
            
            if not operation:
                raise ValueError("Operation not found")
            
            if operation.status != EncryptionStatus.COMPLETED:
                return False
            
            # Verify file checksum
            if operation.operation_type == "encrypt":
                file_path = Path(ENCRYPTION_PATH) / f"{Path(operation.file_path).stem}_encrypted_{operation_id}{Path(operation.file_path).suffix}"
            else:
                file_path = Path(ENCRYPTION_PATH) / f"{Path(operation.file_path).stem}_decrypted_{operation_id}"
            
            if not file_path.exists():
                return False
            
            current_checksum = await self._calculate_file_hash(file_path)
            return current_checksum == operation.checksum
            
        except Exception as e:
            logger.error("Operation verification failed", error=str(e))
            return False

    async def start_background_tasks(self):
        """Start background monitoring tasks"""
        self.key_rotation_task = asyncio.create_task(self._key_rotation_monitor())
        self.cleanup_task = asyncio.create_task(self._cleanup_monitor())
        logger.info("Background tasks started")

    async def _key_rotation_monitor(self):
        """Monitor key rotation and expiration"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                current_time = datetime.now()
                expired_keys = []
                
                for key_id, key in self.keys.items():
                    if key.expires_at and key.expires_at <= current_time:
                        expired_keys.append(key_id)
                
                if expired_keys:
                    logger.warning("Keys expired", expired_keys=expired_keys)
                    # Mark as expired
                    for key_id in expired_keys:
                        self.keys[key_id].status = KeyStatus.EXPIRED
                    
                    await self._save_keys()
                
            except Exception as e:
                logger.error("Error in key rotation monitor", error=str(e))

    async def _cleanup_monitor(self):
        """Cleanup old operations and temporary files"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                # Clean up old operations from history
                cutoff_time = datetime.now() - timedelta(days=7)
                self.operation_history = [
                    op for op in self.operation_history 
                    if op.start_time > cutoff_time
                ]
                
                # Clean up temporary files
                temp_files = Path(ENCRYPTION_PATH).glob("*_temp_*")
                for temp_file in temp_files:
                    if temp_file.stat().st_mtime < (time.time() - 86400):  # 24 hours old
                        temp_file.unlink()
                        logger.debug("Cleaned up temporary file", file=str(temp_file))
                
            except Exception as e:
                logger.error("Error in cleanup monitor", error=str(e))

    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("Shutting down encryption manager")
        
        if self.key_rotation_task:
            self.key_rotation_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Wait for tasks to complete
        tasks = [t for t in [self.key_rotation_task, self.cleanup_task] if t]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Save keys before shutdown
        await self._save_keys()

async def main():
    """Main entry point"""
    encryption_manager = EncryptionManager()
    
    # Start background tasks
    await encryption_manager.start_background_tasks()
    
    # Start the server
    config = uvicorn.Config(
        encryption_manager.app,
        host="0.0.0.0",
        port=8115,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await encryption_manager.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
