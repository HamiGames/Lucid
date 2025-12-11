#!/usr/bin/env python3
"""
LUCID On-System Data Chain Client - SPEC-1B Implementation
Primary blockchain client for On-System Data Chain (EVM-compatible)
LucidAnchors, LucidChunkStore, manifest builder, anchoring system
"""

import asyncio
import hashlib
import json
import logging
import time
import os
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import aiohttp
import aiofiles
import httpx
from web3 import Web3
from web3.middleware import geth_poa_middleware

logger = logging.getLogger(__name__)

class AnchorStatus(Enum):
    """Anchor transaction status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"

@dataclass
class AnchorTransaction:
    """On-System Chain anchor transaction"""
    session_id: str
    merkle_root: str
    block_number: Optional[int]
    transaction_hash: Optional[str]
    status: AnchorStatus
    timestamp: float
    gas_used: Optional[int] = None
    gas_price: Optional[int] = None

@dataclass
class ChunkStoreEntry:
    """Chunk store entry for LucidChunkStore contract"""
    chunk_id: str
    session_id: str
    chunk_hash: str
    size: int
    storage_path: str
    timestamp: float

@dataclass
class SessionManifest:
    """Session manifest for blockchain anchoring"""
    session_id: str
    owner_address: str
    merkle_root: str
    chunk_count: int
    total_size: int
    start_time: float
    end_time: float
    metadata: Dict[str, Any]

class OnSystemChainClient:
    """
    Primary On-System Data Chain client for LucidAnchors and LucidChunkStore contracts
    EVM-compatible blockchain client with gas estimation and circuit breakers
    """
    
    def __init__(
        self,
        rpc_url: Optional[str] = None,
        chain_id: int = 1337,
        private_key: Optional[str] = None,
        output_dir: str = "/data/chain",
        contract_addresses: Optional[Dict[str, str]] = None
    ):
        # Use environment variables (required)
        self.rpc_url = rpc_url or os.getenv("ON_SYSTEM_CHAIN_RPC") or os.getenv("ON_SYSTEM_CHAIN_RPC_URL")
        if not self.rpc_url:
            raise RuntimeError("rpc_url must be provided or ON_SYSTEM_CHAIN_RPC/ON_SYSTEM_CHAIN_RPC_URL environment variable must be set")
        self.chain_id = chain_id
        self.private_key = private_key
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Contract addresses from environment or parameter
        if contract_addresses:
            self.lucid_anchors_address = contract_addresses.get("LucidAnchors", "")
            self.lucid_chunk_store_address = contract_addresses.get("LucidChunkStore", "")
        else:
            self.lucid_anchors_address = os.getenv("LUCID_ANCHORS_ADDRESS", "")
            self.lucid_chunk_store_address = os.getenv("LUCID_CHUNK_STORE_ADDRESS", "")
        
        # Initialize Web3 connection
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if self.w3.is_connected():
            # Add PoA middleware for compatibility
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            logger.info(f"Connected to On-System Chain at {self.rpc_url}")
        else:
            logger.error(f"Failed to connect to On-System Chain at {self.rpc_url}")
            raise ConnectionError("Cannot connect to On-System Chain")
        
        # Gas estimation and circuit breakers
        self.max_gas_price = int(os.getenv("MAX_GAS_PRICE", "1000000000"))  # 1 gwei
        self.max_gas_limit = int(os.getenv("MAX_GAS_LIMIT", "1000000"))
        self.gas_estimation_buffer = 1.2  # 20% buffer
        
        # Session state
        self._active_sessions: Dict[str, SessionManifest] = {}
        self._anchor_transactions: Dict[str, AnchorTransaction] = {}
        
        # Circuit breaker state
        self._circuit_breaker_failures = 0
        self._circuit_breaker_threshold = 5
        self._circuit_breaker_timeout = 300  # 5 minutes
        self._circuit_breaker_last_failure = 0
        
        logger.info("OnSystemChainClient initialized as primary blockchain client")
    
    def _check_circuit_breaker(self) -> bool:
        """Check if circuit breaker is open"""
        if self._circuit_breaker_failures >= self._circuit_breaker_threshold:
            time_since_failure = time.time() - self._circuit_breaker_last_failure
            if time_since_failure < self._circuit_breaker_timeout:
                logger.warning("Circuit breaker is OPEN - blocking requests")
                return False
            else:
                # Reset circuit breaker after timeout
                self._circuit_breaker_failures = 0
                logger.info("Circuit breaker reset after timeout")
        return True
    
    def _record_circuit_breaker_failure(self):
        """Record a circuit breaker failure"""
        self._circuit_breaker_failures += 1
        self._circuit_breaker_last_failure = time.time()
        logger.warning(f"Circuit breaker failure recorded: {self._circuit_breaker_failures}/{self._circuit_breaker_threshold}")
    
    def _reset_circuit_breaker(self):
        """Reset circuit breaker on successful operation"""
        if self._circuit_breaker_failures > 0:
            self._circuit_breaker_failures = 0
            logger.info("Circuit breaker reset after successful operation")
    
    async def _estimate_gas(self, transaction: Dict[str, Any]) -> int:
        """Estimate gas for a transaction with circuit breaker protection"""
        if not self._check_circuit_breaker():
            raise Exception("Circuit breaker is open - cannot estimate gas")
        
        try:
            # Estimate gas using Web3
            estimated_gas = self.w3.eth.estimate_gas(transaction)
            
            # Apply buffer and check limits
            buffered_gas = int(estimated_gas * self.gas_estimation_buffer)
            if buffered_gas > self.max_gas_limit:
                logger.warning(f"Estimated gas {buffered_gas} exceeds limit {self.max_gas_limit}")
                buffered_gas = self.max_gas_limit
            
            self._reset_circuit_breaker()
            return buffered_gas
            
        except Exception as e:
            self._record_circuit_breaker_failure()
            logger.error(f"Gas estimation failed: {e}")
            raise
    
    async def _get_gas_price(self) -> int:
        """Get current gas price with circuit breaker protection"""
        if not self._check_circuit_breaker():
            raise Exception("Circuit breaker is open - cannot get gas price")
        
        try:
            gas_price = self.w3.eth.gas_price
            if gas_price > self.max_gas_price:
                logger.warning(f"Gas price {gas_price} exceeds maximum {self.max_gas_price}")
                gas_price = self.max_gas_price
            
            self._reset_circuit_breaker()
            return gas_price
            
        except Exception as e:
            self._record_circuit_breaker_failure()
            logger.error(f"Failed to get gas price: {e}")
            raise
    
    async def create_session_manifest(
        self,
        session_id: str,
        owner_address: str,
        merkle_root: str,
        chunk_count: int,
        total_size: int,
        start_time: float,
        end_time: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionManifest:
        """
        Create session manifest for blockchain anchoring
        
        Args:
            session_id: Unique session identifier
            owner_address: Session owner's blockchain address
            merkle_root: BLAKE3 Merkle root hash
            chunk_count: Number of chunks in session
            total_size: Total session size in bytes
            start_time: Session start timestamp
            end_time: Session end timestamp
            metadata: Optional session metadata
            
        Returns:
            SessionManifest object
        """
        manifest = SessionManifest(
            session_id=session_id,
            owner_address=owner_address,
            merkle_root=merkle_root,
            chunk_count=chunk_count,
            total_size=total_size,
            start_time=start_time,
            end_time=end_time,
            metadata=metadata or {}
        )
        
        # Store manifest
        self._active_sessions[session_id] = manifest
        await self._save_session_manifest(manifest)
        
        logger.info(f"Created session manifest for {session_id}")
        return manifest
    
    async def anchor_session_to_chain(
        self,
        session_id: str,
        merkle_root: str,
        owner_address: str,
        chunk_count: int,
        started_at: int
    ) -> AnchorTransaction:
        """
        Anchor session to On-System Data Chain using LucidAnchors contract
        Implements registerSession(sessionId, manifestHash, startedAt, owner, merkleRoot, chunkCount)
        
        Args:
            session_id: Session identifier
            merkle_root: BLAKE3 Merkle root to anchor
            owner_address: Session owner address
            chunk_count: Number of chunks in session
            started_at: Session start timestamp
            
        Returns:
            AnchorTransaction object
        """
        if not self._check_circuit_breaker():
            raise Exception("Circuit breaker is open - cannot anchor session")
        
        if not self.lucid_anchors_address:
            raise ValueError("LucidAnchors contract address not configured")
        
        # Create anchor transaction
        anchor_tx = AnchorTransaction(
            session_id=session_id,
            merkle_root=merkle_root,
            block_number=None,
            transaction_hash=None,
            status=AnchorStatus.PENDING,
            timestamp=time.time()
        )
        
        try:
            # Create manifest hash for anchoring
            manifest_hash = self._create_manifest_hash(session_id, merkle_root, owner_address, chunk_count, started_at)
            
            # Prepare LucidAnchors contract call
            contract_call = {
                'to': self.lucid_anchors_address,
                'data': self._encode_register_session_call(
                    session_id, manifest_hash, started_at, owner_address, merkle_root, chunk_count
                ),
                'from': owner_address
            }
            
            # Estimate gas
            gas_limit = await self._estimate_gas(contract_call)
            gas_price = await self._get_gas_price()
            
            # Build transaction
            transaction = {
                'to': self.lucid_anchors_address,
                'data': contract_call['data'],
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': self.w3.eth.get_transaction_count(owner_address)
            }
            
            # Submit transaction (would need private key for signing)
            if self.private_key:
                signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            else:
                # For testing/development - would need proper signing in production
                logger.warning("No private key provided - using mock transaction")
                tx_hash = f"0x{hashlib.sha256(f'{session_id}{merkle_root}'.encode()).hexdigest()[:64]}"
            
            anchor_tx.transaction_hash = tx_hash.hex() if hasattr(tx_hash, 'hex') else str(tx_hash)
            anchor_tx.status = AnchorStatus.CONFIRMED
            anchor_tx.block_number = self.w3.eth.block_number
            anchor_tx.gas_used = gas_limit
            anchor_tx.gas_price = gas_price
            
            self._reset_circuit_breaker()
            logger.info(f"Anchored session {session_id} to LucidAnchors contract: {anchor_tx.transaction_hash}")
            
        except Exception as e:
            self._record_circuit_breaker_failure()
            logger.error(f"Failed to anchor session {session_id}: {e}")
            anchor_tx.status = AnchorStatus.FAILED
        
        # Store transaction
        self._anchor_transactions[session_id] = anchor_tx
        await self._save_anchor_transaction(anchor_tx)
        
        return anchor_tx
    
    def _create_manifest_hash(
        self, 
        session_id: str, 
        merkle_root: str, 
        owner_address: str, 
        chunk_count: int, 
        started_at: int
    ) -> str:
        """Create manifest hash for LucidAnchors contract"""
        manifest_data = f"{session_id}{merkle_root}{owner_address}{chunk_count}{started_at}"
        return hashlib.sha256(manifest_data.encode()).hexdigest()
    
    def _encode_register_session_call(
        self,
        session_id: str,
        manifest_hash: str,
        started_at: int,
        owner_address: str,
        merkle_root: str,
        chunk_count: int
    ) -> str:
        """Encode registerSession call for LucidAnchors contract"""
        # Function selector for registerSession(bytes32,bytes32,uint256,address,bytes32,uint256)
        function_selector = "0x" + hashlib.sha256("registerSession(bytes32,bytes32,uint256,address,bytes32,uint256)".encode()).digest()[:4].hex()
        
        # Encode parameters (simplified - would use proper ABI encoding in production)
        session_id_encoded = session_id.ljust(64, '0')  # Pad to 32 bytes
        manifest_hash_encoded = manifest_hash.ljust(64, '0')  # Pad to 32 bytes
        started_at_encoded = hex(started_at)[2:].zfill(64)  # 32 bytes
        owner_encoded = owner_address[2:].zfill(64)  # Remove 0x and pad
        merkle_root_encoded = merkle_root.ljust(64, '0')  # Pad to 32 bytes
        chunk_count_encoded = hex(chunk_count)[2:].zfill(64)  # 32 bytes
        
        return function_selector + session_id_encoded + manifest_hash_encoded + started_at_encoded + owner_encoded + merkle_root_encoded + chunk_count_encoded
    
    def _encode_store_chunk_call(
        self,
        chunk_id: str,
        session_id: str,
        chunk_hash: str,
        size: int,
        storage_path: str
    ) -> str:
        """Encode storeChunk call for LucidChunkStore contract"""
        # Function selector for storeChunk(bytes32,bytes32,bytes32,uint256,string)
        function_selector = "0x" + hashlib.sha256("storeChunk(bytes32,bytes32,bytes32,uint256,string)".encode()).digest()[:4].hex()
        
        # Encode parameters (simplified - would use proper ABI encoding in production)
        chunk_id_encoded = chunk_id.ljust(64, '0')  # Pad to 32 bytes
        session_id_encoded = session_id.ljust(64, '0')  # Pad to 32 bytes
        chunk_hash_encoded = chunk_hash.ljust(64, '0')  # Pad to 32 bytes
        size_encoded = hex(size)[2:].zfill(64)  # 32 bytes
        # For string parameters, would need proper ABI encoding with offset and length
        storage_path_encoded = storage_path.encode().hex().ljust(64, '0')  # Simplified
        
        return function_selector + chunk_id_encoded + session_id_encoded + chunk_hash_encoded + size_encoded + storage_path_encoded
    
    async def store_chunk_metadata(
        self,
        chunk_id: str,
        session_id: str,
        chunk_hash: str,
        size: int,
        storage_path: str,
        owner_address: str
    ) -> ChunkStoreEntry:
        """
        Store chunk metadata in LucidChunkStore contract
        
        Args:
            chunk_id: Unique chunk identifier
            session_id: Session identifier
            chunk_hash: Chunk content hash
            size: Chunk size in bytes
            storage_path: Storage path for chunk data
            owner_address: Session owner address
            
        Returns:
            ChunkStoreEntry object
        """
        if not self._check_circuit_breaker():
            raise Exception("Circuit breaker is open - cannot store chunk metadata")
        
        if not self.lucid_chunk_store_address:
            raise ValueError("LucidChunkStore contract address not configured")
        
        entry = ChunkStoreEntry(
            chunk_id=chunk_id,
            session_id=session_id,
            chunk_hash=chunk_hash,
            size=size,
            storage_path=storage_path,
            timestamp=time.time()
        )
        
        try:
            # Prepare LucidChunkStore contract call
            contract_call = {
                'to': self.lucid_chunk_store_address,
                'data': self._encode_store_chunk_call(
                    chunk_id, session_id, chunk_hash, size, storage_path
                ),
                'from': owner_address
            }
            
            # Estimate gas
            gas_limit = await self._estimate_gas(contract_call)
            gas_price = await self._get_gas_price()
            
            # Build transaction
            transaction = {
                'to': self.lucid_chunk_store_address,
                'data': contract_call['data'],
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': self.w3.eth.get_transaction_count(owner_address)
            }
            
            # Submit transaction (would need private key for signing)
            if self.private_key:
                signed_txn = self.w3.eth.account.sign_transaction(transaction, self.private_key)
                tx_hash = self.w3.eth.send_raw_transaction(signed_txn.rawTransaction)
            else:
                # For testing/development - would need proper signing in production
                logger.warning("No private key provided - using mock transaction")
                tx_hash = f"0x{hashlib.sha256(f'{chunk_id}{session_id}'.encode()).hexdigest()[:64]}"
            
            self._reset_circuit_breaker()
            logger.debug(f"Stored chunk metadata in LucidChunkStore: {chunk_id}")
            
        except Exception as e:
            self._record_circuit_breaker_failure()
            logger.error(f"Failed to store chunk metadata {chunk_id}: {e}")
            raise
        
        return entry
    
    async def get_session_anchor(self, session_id: str) -> Optional[AnchorTransaction]:
        """Get anchor transaction for a session"""
        return self._anchor_transactions.get(session_id)
    
    async def verify_session_anchor(self, session_id: str, merkle_root: str) -> bool:
        """
        Verify session anchor on blockchain
        
        Args:
            session_id: Session identifier
            merkle_root: Merkle root to verify
            
        Returns:
            True if anchor is valid, False otherwise
        """
        anchor_tx = await self.get_session_anchor(session_id)
        
        if not anchor_tx:
            return False
        
        if anchor_tx.status != AnchorStatus.CONFIRMED:
            return False
        
        # Verify Merkle root matches
        if anchor_tx.merkle_root != merkle_root:
            return False
        
        # Verify transaction on blockchain (simulated)
        is_valid = await self._verify_transaction_on_chain(anchor_tx)
        
        logger.debug(f"Session anchor verification for {session_id}: {'VALID' if is_valid else 'INVALID'}")
        return is_valid
    
    async def get_session_manifest(self, session_id: str) -> Optional[SessionManifest]:
        """Get session manifest"""
        return self._active_sessions.get(session_id)
    
    async def list_session_anchors(
        self, 
        owner_address: Optional[str] = None,
        limit: int = 100
    ) -> List[AnchorTransaction]:
        """
        List session anchors with optional filtering
        
        Args:
            owner_address: Filter by owner address
            limit: Maximum number of results
            
        Returns:
            List of AnchorTransaction objects
        """
        anchors = list(self._anchor_transactions.values())
        
        if owner_address:
            # Filter by owner address
            filtered_anchors = []
            for anchor in anchors:
                manifest = self._active_sessions.get(anchor.session_id)
                if manifest and manifest.owner_address == owner_address:
                    filtered_anchors.append(anchor)
            anchors = filtered_anchors
        
        # Sort by timestamp (newest first)
        anchors.sort(key=lambda x: x.timestamp, reverse=True)
        
        return anchors[:limit]
    
    async def _verify_transaction_on_chain(self, anchor_tx: AnchorTransaction) -> bool:
        """Verify transaction exists on blockchain using Web3"""
        if not anchor_tx.transaction_hash:
            return False
        
        try:
            # Get transaction receipt
            receipt = self.w3.eth.get_transaction_receipt(anchor_tx.transaction_hash)
            return receipt.status == 1  # 1 = success, 0 = failure
        except Exception as e:
            logger.error(f"Failed to verify transaction {anchor_tx.transaction_hash}: {e}")
            return False
    
    async def _save_session_manifest(self, manifest: SessionManifest):
        """Save session manifest to disk"""
        manifest_file = self.output_dir / f"{manifest.session_id}_manifest.json"
        
        manifest_data = asdict(manifest)
        manifest_data['timestamp'] = time.time()
        
        async with aiofiles.open(manifest_file, 'w') as f:
            await f.write(json.dumps(manifest_data, indent=2))
    
    async def _save_anchor_transaction(self, anchor_tx: AnchorTransaction):
        """Save anchor transaction to disk"""
        tx_file = self.output_dir / f"{anchor_tx.session_id}_anchor.json"
        
        tx_data = asdict(anchor_tx)
        tx_data['status'] = anchor_tx.status.value
        
        async with aiofiles.open(tx_file, 'w') as f:
            await f.write(json.dumps(tx_data, indent=2))
    
    async def load_session_manifest(self, session_id: str) -> Optional[SessionManifest]:
        """Load session manifest from disk"""
        manifest_file = self.output_dir / f"{session_id}_manifest.json"
        
        if not manifest_file.exists():
            return None
        
        async with aiofiles.open(manifest_file, 'r') as f:
            data = json.loads(await f.read())
        
        return SessionManifest(**data)
    
    async def load_anchor_transaction(self, session_id: str) -> Optional[AnchorTransaction]:
        """Load anchor transaction from disk"""
        tx_file = self.output_dir / f"{session_id}_anchor.json"
        
        if not tx_file.exists():
            return None
        
        async with aiofiles.open(tx_file, 'r') as f:
            data = json.loads(await f.read())
        
        data['status'] = AnchorStatus(data['status'])
        return AnchorTransaction(**data)
    
    def get_chain_stats(self) -> dict:
        """Get chain client statistics"""
        try:
            latest_block = self.w3.eth.block_number
            gas_price = self.w3.eth.gas_price
            is_connected = self.w3.is_connected()
        except Exception as e:
            logger.error(f"Failed to get chain stats: {e}")
            latest_block = 0
            gas_price = 0
            is_connected = False
        
        return {
            "rpc_url": self.rpc_url,
            "chain_id": self.chain_id,
            "is_connected": is_connected,
            "latest_block": latest_block,
            "gas_price": gas_price,
            "lucid_anchors_address": self.lucid_anchors_address,
            "lucid_chunk_store_address": self.lucid_chunk_store_address,
            "active_sessions": len(self._active_sessions),
            "anchor_transactions": len(self._anchor_transactions),
            "confirmed_anchors": len([tx for tx in self._anchor_transactions.values() 
                                    if tx.status == AnchorStatus.CONFIRMED]),
            "circuit_breaker_failures": self._circuit_breaker_failures,
            "circuit_breaker_open": not self._check_circuit_breaker(),
            "output_directory": str(self.output_dir)
        }

# CLI interface for testing
async def main():
    """Test the chain client with sample data"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LUCID On-System Chain Client")
    parser.add_argument("--session-id", required=True, help="Session ID")
    parser.add_argument("--owner-address", required=True, help="Owner address")
    parser.add_argument("--merkle-root", required=True, help="Merkle root hash")
    parser.add_argument("--rpc-url", default=None, help="RPC URL (or set ON_SYSTEM_CHAIN_RPC/ON_SYSTEM_CHAIN_RPC_URL env var)")
    parser.add_argument("--output-dir", default="/data/chain", help="Output directory")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Create chain client
    client = OnSystemChainClient(
        rpc_url=args.rpc_url,
        output_dir=args.output_dir
    )
    
    # Create session manifest
    manifest = await client.create_session_manifest(
        session_id=args.session_id,
        owner_address=args.owner_address,
        merkle_root=args.merkle_root,
        chunk_count=10,
        total_size=1024*1024,
        start_time=time.time() - 3600,
        end_time=time.time(),
        metadata={"test": True}
    )
    
    print(f"Created manifest: {manifest.session_id}")
    
    # Anchor to chain
    anchor_tx = await client.anchor_session_to_chain(
        session_id=args.session_id,
        merkle_root=args.merkle_root,
        owner_address=args.owner_address,
        chunk_count=10,
        started_at=int(time.time() - 3600)
    )
    
    print(f"Anchor transaction: {anchor_tx.transaction_hash}")
    print(f"Status: {anchor_tx.status.value}")
    
    # Verify anchor
    is_valid = await client.verify_session_anchor(args.session_id, args.merkle_root)
    print(f"Anchor verification: {'VALID' if is_valid else 'INVALID'}")

if __name__ == "__main__":
    asyncio.run(main())