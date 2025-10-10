#!/usr/bin/env python3
"""
LUCID On-System Data Chain Client - SPEC-1B Implementation
LucidAnchors, LucidChunkStore, manifest builder, anchoring system
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import aiohttp
import aiofiles

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
    On-System Data Chain client for LucidAnchors and LucidChunkStore contracts
    """
    
    def __init__(
        self,
        rpc_url: str = "http://on-chain-distroless:8545",
        chain_id: int = 1337,
        private_key: Optional[str] = None,
        output_dir: str = "/data/chain"
    ):
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.private_key = private_key
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Contract addresses (would be deployed addresses)
        self.lucid_anchors_address = "0x1234567890123456789012345678901234567890"  # Placeholder
        self.lucid_chunk_store_address = "0x2345678901234567890123456789012345678901"  # Placeholder
        
        # Session state
        self._active_sessions: Dict[str, SessionManifest] = {}
        self._anchor_transactions: Dict[str, AnchorTransaction] = {}
        
        logger.info("OnSystemChainClient initialized")
    
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
        gas_limit: int = 100000
    ) -> AnchorTransaction:
        """
        Anchor session Merkle root to On-System Data Chain
        
        Args:
            session_id: Session identifier
            merkle_root: BLAKE3 Merkle root to anchor
            gas_limit: Gas limit for transaction
            
        Returns:
            AnchorTransaction object
        """
        if session_id not in self._active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        manifest = self._active_sessions[session_id]
        
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
            # Simulate blockchain transaction (would use actual Web3/Ethereum client)
            transaction_hash = await self._submit_anchor_transaction(
                session_id, merkle_root, gas_limit
            )
            
            anchor_tx.transaction_hash = transaction_hash
            anchor_tx.status = AnchorStatus.CONFIRMED
            anchor_tx.block_number = await self._get_latest_block_number()
            
            logger.info(f"Anchored session {session_id} to chain: {transaction_hash}")
            
        except Exception as e:
            logger.error(f"Failed to anchor session {session_id}: {e}")
            anchor_tx.status = AnchorStatus.FAILED
        
        # Store transaction
        self._anchor_transactions[session_id] = anchor_tx
        await self._save_anchor_transaction(anchor_tx)
        
        return anchor_tx
    
    async def store_chunk_metadata(
        self,
        chunk_id: str,
        session_id: str,
        chunk_hash: str,
        size: int,
        storage_path: str
    ) -> ChunkStoreEntry:
        """
        Store chunk metadata in LucidChunkStore contract
        
        Args:
            chunk_id: Unique chunk identifier
            session_id: Session identifier
            chunk_hash: Chunk content hash
            size: Chunk size in bytes
            storage_path: Storage path for chunk data
            
        Returns:
            ChunkStoreEntry object
        """
        entry = ChunkStoreEntry(
            chunk_id=chunk_id,
            session_id=session_id,
            chunk_hash=chunk_hash,
            size=size,
            storage_path=storage_path,
            timestamp=time.time()
        )
        
        # Store in contract (simulated)
        await self._store_chunk_in_contract(entry)
        
        logger.debug(f"Stored chunk metadata: {chunk_id}")
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
    
    async def _submit_anchor_transaction(
        self, 
        session_id: str, 
        merkle_root: str, 
        gas_limit: int
    ) -> str:
        """Submit anchor transaction to blockchain (simulated)"""
        
        # Simulate transaction submission
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # Generate mock transaction hash
        tx_data = f"{session_id}:{merkle_root}:{int(time.time())}"
        tx_hash = hashlib.sha256(tx_data.encode()).hexdigest()
        
        logger.debug(f"Submitted anchor transaction: {tx_hash}")
        return tx_hash
    
    async def _get_latest_block_number(self) -> int:
        """Get latest block number (simulated)"""
        # Simulate blockchain call
        await asyncio.sleep(0.05)
        return int(time.time()) % 1000000  # Mock block number
    
    async def _store_chunk_in_contract(self, entry: ChunkStoreEntry):
        """Store chunk metadata in contract (simulated)"""
        # Simulate contract interaction
        await asyncio.sleep(0.01)
        logger.debug(f"Stored chunk {entry.chunk_id} in contract")
    
    async def _verify_transaction_on_chain(self, anchor_tx: AnchorTransaction) -> bool:
        """Verify transaction exists on blockchain (simulated)"""
        # Simulate blockchain verification
        await asyncio.sleep(0.05)
        return anchor_tx.status == AnchorStatus.CONFIRMED
    
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
        return {
            "rpc_url": self.rpc_url,
            "chain_id": self.chain_id,
            "active_sessions": len(self._active_sessions),
            "anchor_transactions": len(self._anchor_transactions),
            "confirmed_anchors": len([tx for tx in self._anchor_transactions.values() 
                                    if tx.status == AnchorStatus.CONFIRMED]),
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
    parser.add_argument("--rpc-url", default="http://on-chain-distroless:8545", help="RPC URL")
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
        args.session_id, args.merkle_root
    )
    
    print(f"Anchor transaction: {anchor_tx.transaction_hash}")
    print(f"Status: {anchor_tx.status.value}")
    
    # Verify anchor
    is_valid = await client.verify_session_anchor(args.session_id, args.merkle_root)
    print(f"Anchor verification: {'VALID' if is_valid else 'INVALID'}")

if __name__ == "__main__":
    asyncio.run(main())