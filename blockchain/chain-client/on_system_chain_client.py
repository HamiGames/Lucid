# LUCID On-System Chain Client - LucidAnchors Integration
# Implements comprehensive on-system chain client for session anchoring and data storage
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
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import aiohttp
import aiofiles

logger = logging.getLogger(__name__)

# Configuration from environment
ON_SYSTEM_CHAIN_RPC_URL = "http://localhost:8545"
ON_SYSTEM_CHAIN_ID = 1337
LUCID_ANCHORS_CONTRACT_ADDRESS = "0x1234567890123456789012345678901234567890"
LUCID_CHUNK_STORE_CONTRACT_ADDRESS = "0x2345678901234567890123456789012345678901"
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 2
GAS_LIMIT_DEFAULT = 1000000
GAS_PRICE_DEFAULT = 20000000000  # 20 gwei


class ChainStatus(Enum):
    """On-system chain status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    SYNCING = "syncing"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class TransactionStatus(Enum):
    """Transaction status"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    DROPPED = "dropped"


class SessionStatus(Enum):
    """Session status"""
    ACTIVE = "active"
    ANCHORED = "anchored"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ChainInfo:
    """On-system chain information"""
    chain_id: int
    network_name: str
    latest_block: int
    block_time: float
    gas_price: int
    status: ChainStatus
    rpc_url: str
    contract_addresses: Dict[str, str]


@dataclass
class SessionManifest:
    """Session manifest for blockchain anchoring"""
    session_id: str
    owner_address: str
    merkle_root: str
    chunk_count: int
    total_size: int
    start_time: datetime
    end_time: datetime
    metadata: Dict[str, Any]
    version: str = "1.0.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for blockchain storage"""
        return {
            "sessionId": self.session_id,
            "ownerAddress": self.owner_address,
            "merkleRoot": self.merkle_root,
            "chunkCount": self.chunk_count,
            "totalSize": self.total_size,
            "startTime": int(self.start_time.timestamp()),
            "endTime": int(self.end_time.timestamp()),
            "metadata": self.metadata,
            "version": self.version
        }
    
    def calculate_hash(self) -> str:
        """Calculate manifest hash"""
        manifest_data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(manifest_data.encode()).hexdigest()


@dataclass
class AnchorTransaction:
    """Anchor transaction record"""
    tx_id: str
    session_id: str
    manifest_hash: str
    block_number: Optional[int]
    transaction_hash: Optional[str]
    status: TransactionStatus
    gas_used: Optional[int]
    gas_price: Optional[int]
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class ChunkMetadata:
    """Chunk metadata for storage"""
    chunk_id: str
    session_id: str
    chunk_hash: str
    size: int
    storage_path: str
    timestamp: datetime
    encrypted: bool = False
    compression_ratio: Optional[float] = None


@dataclass
class StorageProof:
    """Proof of storage for chunks"""
    chunk_id: str
    proof_hash: str
    proof_data: bytes
    timestamp: datetime
    validator_signature: Optional[bytes] = None


class OnSystemChainClient:
    """
    On-System Chain client for LucidAnchors and LucidChunkStore integration.
    
    Features:
    - Session manifest anchoring
    - Chunk metadata storage
    - Storage proof verification
    - Transaction monitoring
    - Contract interaction
    - Error handling and retry logic
    """
    
    def __init__(
        self,
        rpc_url: str = ON_SYSTEM_CHAIN_RPC_URL,
        chain_id: int = ON_SYSTEM_CHAIN_ID,
        private_key: Optional[str] = None,
        output_dir: str = "/data/chain-client"
    ):
        """Initialize on-system chain client"""
        self.rpc_url = rpc_url
        self.chain_id = chain_id
        self.private_key = private_key
        self.output_dir = Path(output_dir)
        
        # Contract addresses
        self.contract_addresses = {
            "LucidAnchors": LUCID_ANCHORS_CONTRACT_ADDRESS,
            "LucidChunkStore": LUCID_CHUNK_STORE_CONTRACT_ADDRESS
        }
        
        # Client state
        self.status = ChainStatus.DISCONNECTED
        self.chain_info: Optional[ChainInfo] = None
        self.session_manifests: Dict[str, SessionManifest] = {}
        self.anchor_transactions: Dict[str, AnchorTransaction] = {}
        self.chunk_metadata: Dict[str, ChunkMetadata] = {}
        
        # HTTP session
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"OnSystemChainClient initialized: {rpc_url}")
    
    async def start(self) -> bool:
        """Start the chain client"""
        try:
            # Create HTTP session
            timeout = aiohttp.ClientTimeout(total=30)
            self.http_session = aiohttp.ClientSession(timeout=timeout)
            
            # Connect to chain
            if await self._connect_to_chain():
                self.status = ChainStatus.CONNECTED
                logger.info("On-system chain client started successfully")
                return True
            else:
                self.status = ChainStatus.ERROR
                return False
                
        except Exception as e:
            logger.error(f"Failed to start chain client: {e}")
            self.status = ChainStatus.ERROR
            return False
    
    async def stop(self) -> None:
        """Stop the chain client"""
        try:
            if self.http_session:
                await self.http_session.close()
            
            self.status = ChainStatus.DISCONNECTED
            logger.info("On-system chain client stopped")
            
        except Exception as e:
            logger.error(f"Error stopping chain client: {e}")
    
    async def anchor_session_manifest(
        self,
        session_id: str,
        manifest: SessionManifest,
        gas_limit: int = GAS_LIMIT_DEFAULT
    ) -> Optional[str]:
        """Anchor session manifest to blockchain"""
        try:
            if self.status != ChainStatus.CONNECTED:
                raise ValueError("Chain client not connected")
            
            # Store manifest locally
            self.session_manifests[session_id] = manifest
            
            # Prepare transaction data
            tx_data = await self._prepare_anchor_transaction(manifest)
            
            # Submit transaction
            tx_hash = await self._submit_transaction(
                contract_address=self.contract_addresses["LucidAnchors"],
                function_name="anchorSession",
                parameters=tx_data,
                gas_limit=gas_limit
            )
            
            if tx_hash:
                # Create transaction record
                anchor_tx = AnchorTransaction(
                    tx_id=secrets.token_hex(16),
                    session_id=session_id,
                    manifest_hash=manifest.calculate_hash(),
                    block_number=None,
                    transaction_hash=tx_hash,
                    status=TransactionStatus.PENDING,
                    gas_used=None,
                    gas_price=None,
                    created_at=datetime.now(timezone.utc)
                )
                
                self.anchor_transactions[session_id] = anchor_tx
                
                # Start monitoring transaction
                asyncio.create_task(self._monitor_transaction(anchor_tx))
                
                logger.info(f"Session manifest anchored: {session_id} -> {tx_hash}")
                return tx_hash
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to anchor session manifest: {e}")
            return None
    
    async def store_chunk_metadata(
        self,
        chunk_metadata: ChunkMetadata,
        gas_limit: int = GAS_LIMIT_DEFAULT
    ) -> Optional[str]:
        """Store chunk metadata on blockchain"""
        try:
            if self.status != ChainStatus.CONNECTED:
                raise ValueError("Chain client not connected")
            
            # Store metadata locally
            self.chunk_metadata[chunk_metadata.chunk_id] = chunk_metadata
            
            # Prepare transaction data
            tx_data = {
                "chunkId": chunk_metadata.chunk_id,
                "sessionId": chunk_metadata.session_id,
                "chunkHash": chunk_metadata.chunk_hash,
                "size": chunk_metadata.size,
                "storagePath": chunk_metadata.storage_path,
                "timestamp": int(chunk_metadata.timestamp.timestamp()),
                "encrypted": chunk_metadata.encrypted,
                "compressionRatio": chunk_metadata.compression_ratio or 1.0
            }
            
            # Submit transaction
            tx_hash = await self._submit_transaction(
                contract_address=self.contract_addresses["LucidChunkStore"],
                function_name="storeChunkMetadata",
                parameters=tx_data,
                gas_limit=gas_limit
            )
            
            if tx_hash:
                logger.info(f"Chunk metadata stored: {chunk_metadata.chunk_id} -> {tx_hash}")
                return tx_hash
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to store chunk metadata: {e}")
            return None
    
    async def verify_storage_proof(
        self,
        storage_proof: StorageProof
    ) -> bool:
        """Verify storage proof for chunk"""
        try:
            if self.status != ChainStatus.CONNECTED:
                return False
            
            # Prepare verification data
            verification_data = {
                "chunkId": storage_proof.chunk_id,
                "proofHash": storage_proof.proof_hash,
                "proofData": storage_proof.proof_data.hex(),
                "timestamp": int(storage_proof.timestamp.timestamp())
            }
            
            # Call contract method
            result = await self._call_contract_method(
                contract_address=self.contract_addresses["LucidChunkStore"],
                function_name="verifyStorageProof",
                parameters=verification_data
            )
            
            return result.get("verified", False)
            
        except Exception as e:
            logger.error(f"Failed to verify storage proof: {e}")
            return False
    
    async def get_session_anchor_status(self, session_id: str) -> Optional[AnchorTransaction]:
        """Get anchor transaction status for session"""
        return self.anchor_transactions.get(session_id)
    
    async def get_chain_info(self) -> Optional[ChainInfo]:
        """Get current chain information"""
        return self.chain_info
    
    async def get_session_manifest(self, session_id: str) -> Optional[SessionManifest]:
        """Get session manifest by ID"""
        return self.session_manifests.get(session_id)
    
    async def list_session_manifests(
        self,
        owner_address: Optional[str] = None,
        limit: int = 100
    ) -> List[SessionManifest]:
        """List session manifests with optional filtering"""
        manifests = list(self.session_manifests.values())
        
        # Filter by owner address if specified
        if owner_address:
            manifests = [m for m in manifests if m.owner_address == owner_address]
        
        # Sort by start time (newest first)
        manifests.sort(key=lambda m: m.start_time, reverse=True)
        
        return manifests[:limit]
    
    async def get_chunk_metadata(self, chunk_id: str) -> Optional[ChunkMetadata]:
        """Get chunk metadata by ID"""
        return self.chunk_metadata.get(chunk_id)
    
    async def list_chunk_metadata(
        self,
        session_id: Optional[str] = None,
        limit: int = 100
    ) -> List[ChunkMetadata]:
        """List chunk metadata with optional filtering"""
        chunks = list(self.chunk_metadata.values())
        
        # Filter by session ID if specified
        if session_id:
            chunks = [c for c in chunks if c.session_id == session_id]
        
        # Sort by timestamp (newest first)
        chunks.sort(key=lambda c: c.timestamp, reverse=True)
        
        return chunks[:limit]
    
    async def _connect_to_chain(self) -> bool:
        """Connect to on-system chain"""
        try:
            # Get chain info
            chain_info = await self._get_chain_info()
            if chain_info:
                self.chain_info = chain_info
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to connect to chain: {e}")
            return False
    
    async def _get_chain_info(self) -> Optional[ChainInfo]:
        """Get chain information from RPC"""
        try:
            # Get latest block number
            latest_block = await self._call_rpc_method("eth_blockNumber")
            if not latest_block:
                return None
            
            block_number = int(latest_block, 16)
            
            # Get block details
            block = await self._call_rpc_method("eth_getBlockByNumber", [hex(block_number), False])
            if not block:
                return None
            
            # Get gas price
            gas_price = await self._call_rpc_method("eth_gasPrice")
            if not gas_price:
                return None
            
            return ChainInfo(
                chain_id=self.chain_id,
                network_name="Lucid On-System Chain",
                latest_block=block_number,
                block_time=float(block.get("timestamp", "0x0"), 16),
                gas_price=int(gas_price, 16),
                status=ChainStatus.CONNECTED,
                rpc_url=self.rpc_url,
                contract_addresses=self.contract_addresses
            )
            
        except Exception as e:
            logger.error(f"Failed to get chain info: {e}")
            return None
    
    async def _prepare_anchor_transaction(self, manifest: SessionManifest) -> Dict[str, Any]:
        """Prepare anchor transaction data"""
        return {
            "sessionId": manifest.session_id,
            "ownerAddress": manifest.owner_address,
            "merkleRoot": manifest.merkle_root,
            "chunkCount": manifest.chunk_count,
            "totalSize": manifest.total_size,
            "startTime": int(manifest.start_time.timestamp()),
            "endTime": int(manifest.end_time.timestamp()),
            "metadata": json.dumps(manifest.metadata),
            "manifestHash": manifest.calculate_hash()
        }
    
    async def _submit_transaction(
        self,
        contract_address: str,
        function_name: str,
        parameters: Dict[str, Any],
        gas_limit: int = GAS_LIMIT_DEFAULT
    ) -> Optional[str]:
        """Submit transaction to blockchain"""
        try:
            # Encode function call
            function_call = await self._encode_function_call(
                contract_address, function_name, parameters
            )
            
            # Get gas price
            gas_price = self.chain_info.gas_price if self.chain_info else GAS_PRICE_DEFAULT
            
            # Prepare transaction
            transaction = {
                "to": contract_address,
                "data": function_call,
                "gas": hex(gas_limit),
                "gasPrice": hex(gas_price),
                "value": "0x0"
            }
            
            # Add private key if available
            if self.private_key:
                transaction["from"] = await self._get_address_from_private_key()
            
            # Submit transaction
            tx_hash = await self._call_rpc_method("eth_sendTransaction", [transaction])
            
            if tx_hash:
                logger.info(f"Transaction submitted: {tx_hash}")
                return tx_hash
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to submit transaction: {e}")
            return None
    
    async def _call_contract_method(
        self,
        contract_address: str,
        function_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call contract method (read-only)"""
        try:
            # Encode function call
            function_call = await self._encode_function_call(
                contract_address, function_name, parameters
            )
            
            # Prepare call
            call_data = {
                "to": contract_address,
                "data": function_call
            }
            
            # Make call
            result = await self._call_rpc_method("eth_call", [call_data, "latest"])
            
            if result:
                # Decode result
                return await self._decode_function_result(function_name, result)
            
            return {}
            
        except Exception as e:
            logger.error(f"Failed to call contract method: {e}")
            return {}
    
    async def _encode_function_call(
        self,
        contract_address: str,
        function_name: str,
        parameters: Dict[str, Any]
    ) -> str:
        """Encode function call data"""
        # Simplified function signature encoding
        # In production, use proper ABI encoding
        function_signature = hashlib.sha3_256(
            f"{function_name}({','.join(parameters.keys())})".encode()
        ).hexdigest()[:8]
        
        # Encode parameters (simplified)
        encoded_params = ""
        for key, value in parameters.items():
            if isinstance(value, str):
                encoded_params += value.encode().hex()
            elif isinstance(value, int):
                encoded_params += hex(value)[2:].zfill(64)
            else:
                encoded_params += str(value).encode().hex()
        
        return f"0x{function_signature}{encoded_params}"
    
    async def _decode_function_result(
        self,
        function_name: str,
        result: str
    ) -> Dict[str, Any]:
        """Decode function result"""
        # Simplified result decoding
        # In production, use proper ABI decoding
        try:
            # Remove 0x prefix
            result_data = result[2:] if result.startswith("0x") else result
            
            # Decode based on function name
            if function_name == "verifyStorageProof":
                return {"verified": result_data == "1"}
            elif function_name == "getSessionManifest":
                # Decode manifest data
                return {"manifest": json.loads(bytes.fromhex(result_data).decode())}
            else:
                return {"result": result_data}
                
        except Exception as e:
            logger.error(f"Failed to decode function result: {e}")
            return {}
    
    async def _call_rpc_method(self, method: str, params: List[Any] = None) -> Any:
        """Call RPC method"""
        if not self.http_session:
            raise ValueError("HTTP session not initialized")
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": secrets.randbelow(10000)
        }
        
        try:
            async with self.http_session.post(
                self.rpc_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    if "error" in result:
                        logger.error(f"RPC error: {result['error']}")
                        return None
                    return result.get("result")
                else:
                    logger.error(f"RPC request failed: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"RPC call failed: {e}")
            return None
    
    async def _monitor_transaction(self, anchor_tx: AnchorTransaction) -> None:
        """Monitor transaction confirmation"""
        try:
            max_attempts = 10
            attempt = 0
            
            while attempt < max_attempts and anchor_tx.status == TransactionStatus.PENDING:
                await asyncio.sleep(5)  # Wait 5 seconds between checks
                attempt += 1
                
                # Get transaction receipt
                receipt = await self._call_rpc_method(
                    "eth_getTransactionReceipt",
                    [anchor_tx.transaction_hash]
                )
                
                if receipt:
                    # Transaction confirmed
                    anchor_tx.status = TransactionStatus.CONFIRMED
                    anchor_tx.block_number = int(receipt.get("blockNumber", "0x0"), 16)
                    anchor_tx.gas_used = int(receipt.get("gasUsed", "0x0"), 16)
                    anchor_tx.confirmed_at = datetime.now(timezone.utc)
                    
                    logger.info(f"Transaction confirmed: {anchor_tx.transaction_hash}")
                    break
                else:
                    # Check if transaction was dropped
                    tx_data = await self._call_rpc_method(
                        "eth_getTransactionByHash",
                        [anchor_tx.transaction_hash]
                    )
                    
                    if not tx_data:
                        anchor_tx.status = TransactionStatus.DROPPED
                        anchor_tx.error_message = "Transaction dropped from mempool"
                        logger.warning(f"Transaction dropped: {anchor_tx.transaction_hash}")
                        break
            
            # Mark as failed if still pending after max attempts
            if anchor_tx.status == TransactionStatus.PENDING:
                anchor_tx.status = TransactionStatus.FAILED
                anchor_tx.error_message = "Transaction timeout"
                logger.error(f"Transaction timeout: {anchor_tx.transaction_hash}")
                
        except Exception as e:
            logger.error(f"Error monitoring transaction: {e}")
            anchor_tx.status = TransactionStatus.FAILED
            anchor_tx.error_message = str(e)
    
    async def _get_address_from_private_key(self) -> str:
        """Get address from private key"""
        # Simplified address derivation
        # In production, use proper key derivation
        if self.private_key:
            # Remove 0x prefix if present
            private_key_hex = self.private_key[2:] if self.private_key.startswith("0x") else self.private_key
            
            # Generate address (simplified)
            address = hashlib.sha256(private_key_hex.encode()).hexdigest()[:40]
            return f"0x{address}"
        
        return "0x0000000000000000000000000000000000000000"


# Global chain client
_chain_client: Optional[OnSystemChainClient] = None


def get_chain_client() -> Optional[OnSystemChainClient]:
    """Get global chain client instance"""
    return _chain_client


def create_chain_client(
    rpc_url: str = ON_SYSTEM_CHAIN_RPC_URL,
    chain_id: int = ON_SYSTEM_CHAIN_ID,
    private_key: Optional[str] = None,
    output_dir: str = "/data/chain-client"
) -> OnSystemChainClient:
    """Create new chain client instance"""
    global _chain_client
    _chain_client = OnSystemChainClient(rpc_url, chain_id, private_key, output_dir)
    return _chain_client


async def main():
    """Main function for testing"""
    import asyncio
    
    # Create chain client
    client = create_chain_client()
    
    # Start client
    if await client.start():
        print("Chain client started successfully")
        
        # Get chain info
        chain_info = await client.get_chain_info()
        if chain_info:
            print(f"Chain info: {chain_info.network_name}")
            print(f"Latest block: {chain_info.latest_block}")
            print(f"Gas price: {chain_info.gas_price}")
        
        # Create test session manifest
        manifest = SessionManifest(
            session_id="test_session_001",
            owner_address="0x1234567890123456789012345678901234567890",
            merkle_root="0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            chunk_count=10,
            total_size=1024000,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            metadata={"test": True, "version": "1.0"}
        )
        
        # Anchor session manifest
        tx_hash = await client.anchor_session_manifest("test_session_001", manifest)
        print(f"Session anchored: {tx_hash}")
        
        # Create test chunk metadata
        chunk_metadata = ChunkMetadata(
            chunk_id="test_chunk_001",
            session_id="test_session_001",
            chunk_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            size=1024,
            storage_path="/data/chunks/test_chunk_001",
            timestamp=datetime.now(timezone.utc)
        )
        
        # Store chunk metadata
        chunk_tx_hash = await client.store_chunk_metadata(chunk_metadata)
        print(f"Chunk metadata stored: {chunk_tx_hash}")
        
        # Wait for transactions to be processed
        await asyncio.sleep(10)
        
        # Check transaction status
        anchor_status = await client.get_session_anchor_status("test_session_001")
        if anchor_status:
            print(f"Anchor status: {anchor_status.status.value}")
        
        # List session manifests
        manifests = await client.list_session_manifests()
        print(f"Session manifests: {len(manifests)}")
        
        # List chunk metadata
        chunks = await client.list_chunk_metadata()
        print(f"Chunk metadata: {len(chunks)}")
        
        # Stop client
        await client.stop()
        print("Chain client stopped")
    
    else:
        print("Failed to start chain client")


if __name__ == "__main__":
    asyncio.run(main())
