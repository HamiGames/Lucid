# LUCID Anchors Client - Session Anchoring System
# Implements comprehensive session anchoring and manifest management
# LUCID-STRICT Layer 2 Service Integration

from __future__ import annotations

import asyncio
import logging
import secrets
import time
import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, padding
from cryptography.hazmat.backends import default_backend
import aiohttp
import aiofiles

logger = logging.getLogger(__name__)

# Configuration from environment
LUCID_ANCHORS_CONTRACT_ADDRESS = "0x1234567890123456789012345678901234567890"
ANCHOR_TIMEOUT_SECONDS = 300
ANCHOR_RETRY_ATTEMPTS = 3
MANIFEST_VERSION = "1.0.0"
MERKLE_TREE_ALGORITHM = "sha256"


class AnchorStatus(Enum):
    """Anchor status states"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    EXPIRED = "expired"


class ManifestStatus(Enum):
    """Manifest status states"""
    DRAFT = "draft"
    READY = "ready"
    ANCHORED = "anchored"
    VERIFIED = "verified"
    INVALID = "invalid"


class ChunkStatus(Enum):
    """Chunk status states"""
    PENDING = "pending"
    STORED = "stored"
    VERIFIED = "verified"
    MISSING = "missing"
    CORRUPTED = "corrupted"


@dataclass
class SessionChunk:
    """Session chunk information"""
    chunk_id: str
    session_id: str
    chunk_hash: str
    size: int
    offset: int
    storage_path: str
    timestamp: datetime
    status: ChunkStatus = ChunkStatus.PENDING
    verification_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "chunkId": self.chunk_id,
            "sessionId": self.session_id,
            "chunkHash": self.chunk_hash,
            "size": self.size,
            "offset": self.offset,
            "storagePath": self.storage_path,
            "timestamp": int(self.timestamp.timestamp()),
            "status": self.status.value,
            "verificationHash": self.verification_hash
        }


@dataclass
class SessionManifest:
    """Session manifest for anchoring"""
    session_id: str
    owner_address: str
    merkle_root: str
    chunks: List[SessionChunk]
    total_size: int
    start_time: datetime
    end_time: datetime
    metadata: Dict[str, Any]
    version: str = MANIFEST_VERSION
    status: ManifestStatus = ManifestStatus.DRAFT
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for blockchain storage"""
        return {
            "sessionId": self.session_id,
            "ownerAddress": self.owner_address,
            "merkleRoot": self.merkle_root,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
            "totalSize": self.total_size,
            "startTime": int(self.start_time.timestamp()),
            "endTime": int(self.end_time.timestamp()),
            "metadata": self.metadata,
            "version": self.version,
            "status": self.status.value
        }
    
    def calculate_merkle_root(self) -> str:
        """Calculate Merkle root from chunks"""
        if not self.chunks:
            return "0x0000000000000000000000000000000000000000000000000000000000000000"
        
        # Sort chunks by offset
        sorted_chunks = sorted(self.chunks, key=lambda c: c.offset)
        
        # Create leaf hashes
        leaf_hashes = []
        for chunk in sorted_chunks:
            leaf_data = f"{chunk.chunk_id}:{chunk.chunk_hash}:{chunk.size}:{chunk.offset}"
            leaf_hash = hashlib.sha256(leaf_data.encode()).hexdigest()
            leaf_hashes.append(leaf_hash)
        
        # Build Merkle tree
        while len(leaf_hashes) > 1:
            next_level = []
            for i in range(0, len(leaf_hashes), 2):
                left = leaf_hashes[i]
                right = leaf_hashes[i + 1] if i + 1 < len(leaf_hashes) else left
                combined = left + right
                parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                next_level.append(parent_hash)
            leaf_hashes = next_level
        
        return f"0x{leaf_hashes[0]}"
    
    def validate_manifest(self) -> Tuple[bool, List[str]]:
        """Validate manifest integrity"""
        errors = []
        
        # Check required fields
        if not self.session_id:
            errors.append("Session ID is required")
        
        if not self.owner_address:
            errors.append("Owner address is required")
        
        if not self.chunks:
            errors.append("At least one chunk is required")
        
        # Validate chunks
        total_size = 0
        for i, chunk in enumerate(self.chunks):
            if not chunk.chunk_id:
                errors.append(f"Chunk {i}: Chunk ID is required")
            
            if not chunk.chunk_hash:
                errors.append(f"Chunk {i}: Chunk hash is required")
            
            if chunk.size <= 0:
                errors.append(f"Chunk {i}: Invalid size")
            
            if chunk.offset < 0:
                errors.append(f"Chunk {i}: Invalid offset")
            
            total_size += chunk.size
        
        # Check total size consistency
        if total_size != self.total_size:
            errors.append(f"Total size mismatch: calculated {total_size}, expected {self.total_size}")
        
        # Validate Merkle root
        calculated_merkle_root = self.calculate_merkle_root()
        if calculated_merkle_root != self.merkle_root:
            errors.append(f"Merkle root mismatch: calculated {calculated_merkle_root}, expected {self.merkle_root}")
        
        return len(errors) == 0, errors


@dataclass
class AnchorTransaction:
    """Anchor transaction record"""
    anchor_id: str
    session_id: str
    manifest_hash: str
    transaction_hash: Optional[str]
    block_number: Optional[int]
    status: AnchorStatus
    gas_used: Optional[int]
    gas_price: Optional[int]
    created_at: datetime
    submitted_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0


@dataclass
class AnchorProof:
    """Proof of anchoring"""
    anchor_id: str
    session_id: str
    merkle_root: str
    block_number: int
    transaction_hash: str
    block_hash: str
    block_timestamp: int
    proof_data: bytes
    validator_signature: Optional[bytes] = None


class LucidAnchorsClient:
    """
    Lucid Anchors client for session manifest anchoring.
    
    Features:
    - Session manifest creation and validation
    - Merkle tree generation and verification
    - Blockchain anchoring with retry logic
    - Anchor proof generation and verification
    - Chunk integrity validation
    - Transaction monitoring and status tracking
    """
    
    def __init__(
        self,
        contract_address: str = LUCID_ANCHORS_CONTRACT_ADDRESS,
        rpc_url: Optional[str] = None,
        private_key: Optional[str] = None,
        output_dir: str = "/data/anchors"
    ):
        """Initialize Lucid Anchors client"""
        import os
        self.contract_address = contract_address
        self.rpc_url = rpc_url or os.getenv("ON_SYSTEM_CHAIN_RPC") or os.getenv("ON_SYSTEM_CHAIN_RPC_URL")
        if not self.rpc_url:
            raise RuntimeError("rpc_url must be provided or ON_SYSTEM_CHAIN_RPC/ON_SYSTEM_CHAIN_RPC_URL environment variable must be set")
        self.private_key = private_key
        self.output_dir = Path(output_dir)
        
        # Client state
        self.session_manifests: Dict[str, SessionManifest] = {}
        self.anchor_transactions: Dict[str, AnchorTransaction] = {}
        self.anchor_proofs: Dict[str, AnchorProof] = {}
        
        # HTTP session
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"LucidAnchorsClient initialized: {contract_address}")
    
    async def start(self) -> bool:
        """Start the anchors client"""
        try:
            # Create HTTP session
            timeout = aiohttp.ClientTimeout(total=30)
            self.http_session = aiohttp.ClientSession(timeout=timeout)
            
            logger.info("Lucid Anchors client started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start anchors client: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop the anchors client"""
        try:
            if self.http_session:
                await self.http_session.close()
            
            logger.info("Lucid Anchors client stopped")
            
        except Exception as e:
            logger.error(f"Error stopping anchors client: {e}")
    
    async def create_session_manifest(
        self,
        session_id: str,
        owner_address: str,
        chunks: List[SessionChunk],
        start_time: datetime,
        end_time: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionManifest:
        """Create session manifest from chunks"""
        try:
            # Calculate total size
            total_size = sum(chunk.size for chunk in chunks)
            
            # Create manifest
            manifest = SessionManifest(
                session_id=session_id,
                owner_address=owner_address,
                merkle_root="",  # Will be calculated
                chunks=chunks,
                total_size=total_size,
                start_time=start_time,
                end_time=end_time,
                metadata=metadata or {},
                status=ManifestStatus.DRAFT
            )
            
            # Calculate Merkle root
            manifest.merkle_root = manifest.calculate_merkle_root()
            
            # Validate manifest
            is_valid, errors = manifest.validate_manifest()
            if not is_valid:
                raise ValueError(f"Invalid manifest: {', '.join(errors)}")
            
            # Store manifest
            self.session_manifests[session_id] = manifest
            manifest.status = ManifestStatus.READY
            
            logger.info(f"Session manifest created: {session_id}")
            return manifest
            
        except Exception as e:
            logger.error(f"Failed to create session manifest: {e}")
            raise
    
    async def anchor_session_manifest(
        self,
        session_id: str,
        gas_limit: int = 1000000
    ) -> Optional[str]:
        """Anchor session manifest to blockchain"""
        try:
            # Get manifest
            manifest = self.session_manifests.get(session_id)
            if not manifest:
                raise ValueError(f"Session manifest not found: {session_id}")
            
            if manifest.status != ManifestStatus.READY:
                raise ValueError(f"Manifest not ready for anchoring: {manifest.status.value}")
            
            # Create anchor transaction
            anchor_id = secrets.token_hex(16)
            anchor_tx = AnchorTransaction(
                anchor_id=anchor_id,
                session_id=session_id,
                manifest_hash=manifest.calculate_merkle_root(),
                transaction_hash=None,
                block_number=None,
                status=AnchorStatus.PENDING,
                gas_used=None,
                gas_price=None,
                created_at=datetime.now(timezone.utc)
            )
            
            # Submit to blockchain
            tx_hash = await self._submit_anchor_transaction(manifest, gas_limit)
            
            if tx_hash:
                anchor_tx.transaction_hash = tx_hash
                anchor_tx.status = AnchorStatus.SUBMITTED
                anchor_tx.submitted_at = datetime.now(timezone.utc)
                
                # Store transaction
                self.anchor_transactions[session_id] = anchor_tx
                
                # Start monitoring
                asyncio.create_task(self._monitor_anchor_transaction(anchor_tx))
                
                # Update manifest status
                manifest.status = ManifestStatus.ANCHORED
                
                logger.info(f"Session manifest anchored: {session_id} -> {tx_hash}")
                return tx_hash
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to anchor session manifest: {e}")
            return None
    
    async def verify_anchor_proof(
        self,
        session_id: str,
        proof_data: bytes
    ) -> bool:
        """Verify anchor proof for session"""
        try:
            # Get anchor transaction
            anchor_tx = self.anchor_transactions.get(session_id)
            if not anchor_tx:
                return False
            
            if anchor_tx.status != AnchorStatus.CONFIRMED:
                return False
            
            # Get manifest
            manifest = self.session_manifests.get(session_id)
            if not manifest:
                return False
            
            # Verify proof
            is_valid = await self._verify_anchor_proof_data(
                manifest, anchor_tx, proof_data
            )
            
            if is_valid:
                # Create anchor proof
                anchor_proof = AnchorProof(
                    anchor_id=anchor_tx.anchor_id,
                    session_id=session_id,
                    merkle_root=manifest.merkle_root,
                    block_number=anchor_tx.block_number,
                    transaction_hash=anchor_tx.transaction_hash,
                    block_hash="",  # Would be retrieved from blockchain
                    block_timestamp=int(datetime.now(timezone.utc).timestamp()),
                    proof_data=proof_data
                )
                
                self.anchor_proofs[session_id] = anchor_proof
                manifest.status = ManifestStatus.VERIFIED
                
                logger.info(f"Anchor proof verified: {session_id}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Failed to verify anchor proof: {e}")
            return False
    
    async def get_session_manifest(self, session_id: str) -> Optional[SessionManifest]:
        """Get session manifest by ID"""
        return self.session_manifests.get(session_id)
    
    async def get_anchor_status(self, session_id: str) -> Optional[AnchorTransaction]:
        """Get anchor transaction status"""
        return self.anchor_transactions.get(session_id)
    
    async def get_anchor_proof(self, session_id: str) -> Optional[AnchorProof]:
        """Get anchor proof for session"""
        return self.anchor_proofs.get(session_id)
    
    async def list_session_manifests(
        self,
        owner_address: Optional[str] = None,
        status: Optional[ManifestStatus] = None,
        limit: int = 100
    ) -> List[SessionManifest]:
        """List session manifests with filtering"""
        manifests = list(self.session_manifests.values())
        
        # Apply filters
        if owner_address:
            manifests = [m for m in manifests if m.owner_address == owner_address]
        
        if status:
            manifests = [m for m in manifests if m.status == status]
        
        # Sort by start time (newest first)
        manifests.sort(key=lambda m: m.start_time, reverse=True)
        
        return manifests[:limit]
    
    async def validate_chunk_integrity(
        self,
        session_id: str,
        chunk_id: str,
        chunk_data: bytes
    ) -> bool:
        """Validate chunk integrity against manifest"""
        try:
            # Get manifest
            manifest = self.session_manifests.get(session_id)
            if not manifest:
                return False
            
            # Find chunk in manifest
            chunk = None
            for c in manifest.chunks:
                if c.chunk_id == chunk_id:
                    chunk = c
                    break
            
            if not chunk:
                return False
            
            # Calculate hash of chunk data
            chunk_hash = hashlib.sha256(chunk_data).hexdigest()
            
            # Verify hash matches
            if chunk_hash != chunk.chunk_hash:
                return False
            
            # Verify size matches
            if len(chunk_data) != chunk.size:
                return False
            
            # Update chunk status
            chunk.status = ChunkStatus.VERIFIED
            chunk.verification_hash = chunk_hash
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to validate chunk integrity: {e}")
            return False
    
    async def generate_merkle_proof(
        self,
        session_id: str,
        chunk_id: str
    ) -> Optional[List[str]]:
        """Generate Merkle proof for specific chunk"""
        try:
            # Get manifest
            manifest = self.session_manifests.get(session_id)
            if not manifest:
                return None
            
            # Sort chunks by offset
            sorted_chunks = sorted(manifest.chunks, key=lambda c: c.offset)
            
            # Find chunk index
            chunk_index = -1
            for i, chunk in enumerate(sorted_chunks):
                if chunk.chunk_id == chunk_id:
                    chunk_index = i
                    break
            
            if chunk_index == -1:
                return None
            
            # Generate Merkle proof
            proof = []
            current_level = []
            
            # Create leaf hashes
            for chunk in sorted_chunks:
                leaf_data = f"{chunk.chunk_id}:{chunk.chunk_hash}:{chunk.size}:{chunk.offset}"
                leaf_hash = hashlib.sha256(leaf_data.encode()).hexdigest()
                current_level.append(leaf_hash)
            
            # Build proof path
            level_index = chunk_index
            while len(current_level) > 1:
                next_level = []
                for i in range(0, len(current_level), 2):
                    left = current_level[i]
                    right = current_level[i + 1] if i + 1 < len(current_level) else left
                    
                    # Add sibling to proof if needed
                    if i == level_index:
                        proof.append(right)
                    elif i + 1 == level_index:
                        proof.append(left)
                    
                    combined = left + right
                    parent_hash = hashlib.sha256(combined.encode()).hexdigest()
                    next_level.append(parent_hash)
                
                current_level = next_level
                level_index = level_index // 2
            
            return proof
            
        except Exception as e:
            logger.error(f"Failed to generate Merkle proof: {e}")
            return None
    
    async def _submit_anchor_transaction(
        self,
        manifest: SessionManifest,
        gas_limit: int
    ) -> Optional[str]:
        """Submit anchor transaction to blockchain"""
        try:
            if not self.http_session:
                raise ValueError("HTTP session not initialized")
            
            # Prepare transaction data
            tx_data = {
                "sessionId": manifest.session_id,
                "ownerAddress": manifest.owner_address,
                "merkleRoot": manifest.merkle_root,
                "chunkCount": len(manifest.chunks),
                "totalSize": manifest.total_size,
                "startTime": int(manifest.start_time.timestamp()),
                "endTime": int(manifest.end_time.timestamp()),
                "metadata": json.dumps(manifest.metadata),
                "manifestHash": hashlib.sha256(json.dumps(manifest.to_dict(), sort_keys=True).encode()).hexdigest()
            }
            
            # Encode function call
            function_call = await self._encode_anchor_function_call(tx_data)
            
            # Prepare transaction
            transaction = {
                "to": self.contract_address,
                "data": function_call,
                "gas": hex(gas_limit),
                "gasPrice": hex(20000000000),  # 20 gwei
                "value": "0x0"
            }
            
            # Submit transaction
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_sendTransaction",
                "params": [transaction],
                "id": secrets.randbelow(10000)
            }
            
            async with self.http_session.post(
                self.rpc_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "error" in result:
                        logger.error(f"Transaction error: {result['error']}")
                        return None
                    return result.get("result")
                else:
                    logger.error(f"Transaction failed: {response.status}")
                    return None
            
        except Exception as e:
            logger.error(f"Failed to submit anchor transaction: {e}")
            return None
    
    async def _encode_anchor_function_call(self, tx_data: Dict[str, Any]) -> str:
        """Encode anchor function call"""
        # Simplified function signature encoding
        function_signature = hashlib.sha256(
            "anchorSession(string,address,bytes32,uint256,uint256,uint256,uint256,string,bytes32)".encode()
        ).hexdigest()[:8]
        
        # Encode parameters (simplified)
        encoded_params = ""
        for key, value in tx_data.items():
            if isinstance(value, str):
                # Encode string parameter
                encoded_params += value.encode().hex()
            elif isinstance(value, int):
                # Encode uint256 parameter
                encoded_params += hex(value)[2:].zfill(64)
            else:
                encoded_params += str(value).encode().hex()
        
        return f"0x{function_signature}{encoded_params}"
    
    async def _monitor_anchor_transaction(self, anchor_tx: AnchorTransaction) -> None:
        """Monitor anchor transaction confirmation"""
        try:
            max_attempts = 20
            attempt = 0
            
            while attempt < max_attempts and anchor_tx.status == AnchorStatus.SUBMITTED:
                await asyncio.sleep(10)  # Wait 10 seconds between checks
                attempt += 1
                
                # Get transaction receipt
                receipt = await self._get_transaction_receipt(anchor_tx.transaction_hash)
                
                if receipt:
                    # Transaction confirmed
                    anchor_tx.status = AnchorStatus.CONFIRMED
                    anchor_tx.block_number = int(receipt.get("blockNumber", "0x0"), 16)
                    anchor_tx.gas_used = int(receipt.get("gasUsed", "0x0"), 16)
                    anchor_tx.confirmed_at = datetime.now(timezone.utc)
                    
                    logger.info(f"Anchor transaction confirmed: {anchor_tx.transaction_hash}")
                    break
                else:
                    # Check if transaction was dropped
                    tx_data = await self._get_transaction_by_hash(anchor_tx.transaction_hash)
                    
                    if not tx_data:
                        anchor_tx.status = AnchorStatus.FAILED
                        anchor_tx.error_message = "Transaction dropped from mempool"
                        logger.warning(f"Anchor transaction dropped: {anchor_tx.transaction_hash}")
                        break
            
            # Mark as failed if still pending after max attempts
            if anchor_tx.status == AnchorStatus.SUBMITTED:
                anchor_tx.status = AnchorStatus.FAILED
                anchor_tx.error_message = "Transaction timeout"
                logger.error(f"Anchor transaction timeout: {anchor_tx.transaction_hash}")
                
        except Exception as e:
            logger.error(f"Error monitoring anchor transaction: {e}")
            anchor_tx.status = AnchorStatus.FAILED
            anchor_tx.error_message = str(e)
    
    async def _verify_anchor_proof_data(
        self,
        manifest: SessionManifest,
        anchor_tx: AnchorTransaction,
        proof_data: bytes
    ) -> bool:
        """Verify anchor proof data"""
        try:
            # Decode proof data
            proof_info = json.loads(proof_data.decode())
            
            # Verify Merkle root
            if proof_info.get("merkleRoot") != manifest.merkle_root:
                return False
            
            # Verify transaction hash
            if proof_info.get("transactionHash") != anchor_tx.transaction_hash:
                return False
            
            # Verify block number
            if proof_info.get("blockNumber") != anchor_tx.block_number:
                return False
            
            # Additional verification logic would go here
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify anchor proof data: {e}")
            return False
    
    async def _get_transaction_receipt(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get transaction receipt"""
        try:
            if not self.http_session:
                return None
            
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [tx_hash],
                "id": secrets.randbelow(10000)
            }
            
            async with self.http_session.post(
                self.rpc_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "error" in result:
                        return None
                    return result.get("result")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get transaction receipt: {e}")
            return None
    
    async def _get_transaction_by_hash(self, tx_hash: str) -> Optional[Dict[str, Any]]:
        """Get transaction by hash"""
        try:
            if not self.http_session:
                return None
            
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getTransactionByHash",
                "params": [tx_hash],
                "id": secrets.randbelow(10000)
            }
            
            async with self.http_session.post(
                self.rpc_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "error" in result:
                        return None
                    return result.get("result")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get transaction: {e}")
            return None


# Global anchors client
_anchors_client: Optional[LucidAnchorsClient] = None


def get_anchors_client() -> Optional[LucidAnchorsClient]:
    """Get global anchors client instance"""
    return _anchors_client


def create_anchors_client(
    contract_address: str = LUCID_ANCHORS_CONTRACT_ADDRESS,
    rpc_url: Optional[str] = None,
    private_key: Optional[str] = None,
    output_dir: str = "/data/anchors"
) -> LucidAnchorsClient:
    """Create new anchors client instance"""
    global _anchors_client
    _anchors_client = LucidAnchorsClient(contract_address, rpc_url, private_key, output_dir)
    return _anchors_client


async def main():
    """Main function for testing"""
    import asyncio
    
    # Create anchors client
    client = create_anchors_client()
    
    # Start client
    if await client.start():
        print("Anchors client started successfully")
        
        # Create test chunks
        chunks = []
        for i in range(5):
            chunk = SessionChunk(
                chunk_id=f"test_chunk_{i:03d}",
                session_id="test_session_001",
                chunk_hash=f"0x{'a' * 64}",  # Placeholder hash
                size=1024 * (i + 1),
                offset=i * 1024,
                storage_path=f"/data/chunks/test_chunk_{i:03d}",
                timestamp=datetime.now(timezone.utc)
            )
            chunks.append(chunk)
        
        # Create session manifest
        manifest = await client.create_session_manifest(
            session_id="test_session_001",
            owner_address="0x1234567890123456789012345678901234567890",
            chunks=chunks,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            metadata={"test": True, "version": "1.0"}
        )
        
        print(f"Manifest created: {manifest.session_id}")
        print(f"Merkle root: {manifest.merkle_root}")
        print(f"Total size: {manifest.total_size}")
        print(f"Chunk count: {len(manifest.chunks)}")
        
        # Validate manifest
        is_valid, errors = manifest.validate_manifest()
        print(f"Manifest valid: {is_valid}")
        if errors:
            print(f"Errors: {errors}")
        
        # Anchor manifest
        tx_hash = await client.anchor_session_manifest("test_session_001")
        print(f"Manifest anchored: {tx_hash}")
        
        # Wait for transaction
        await asyncio.sleep(10)
        
        # Check anchor status
        anchor_status = await client.get_anchor_status("test_session_001")
        if anchor_status:
            print(f"Anchor status: {anchor_status.status.value}")
        
        # Generate Merkle proof for first chunk
        proof = await client.generate_merkle_proof("test_session_001", "test_chunk_000")
        if proof:
            print(f"Merkle proof generated: {len(proof)} elements")
        
        # List manifests
        manifests = await client.list_session_manifests()
        print(f"Total manifests: {len(manifests)}")
        
        # Stop client
        await client.stop()
        print("Anchors client stopped")
    
    else:
        print("Failed to start anchors client")


if __name__ == "__main__":
    asyncio.run(main())
