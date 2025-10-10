# Path: sessions/integration/blockchain_client.py
# LUCID Blockchain Integration Client - Session Blockchain Operations
# Professional blockchain integration for session anchoring and verification
# Multi-platform support for ARM64 Pi and AMD64 development

from __future__ import annotations

import asyncio
import logging
import os
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
import blake3
import httpx

logger = logging.getLogger(__name__)

# Configuration from environment
BLOCKCHAIN_CONFIG_PATH = Path(os.getenv("LUCID_BLOCKCHAIN_CONFIG_PATH", "/data/blockchain"))
TRON_NETWORK_URL = os.getenv("LUCID_TRON_NETWORK_URL", "https://api.trongrid.io")
CONTRACT_ADDRESS = os.getenv("LUCID_CONTRACT_ADDRESS", "TContractAddress")
PRIVATE_KEY = os.getenv("LUCID_PRIVATE_KEY", "")
GAS_LIMIT = int(os.getenv("LUCID_GAS_LIMIT", "1000000"))
GAS_PRICE = int(os.getenv("LUCID_GAS_PRICE", "1000000"))


class BlockchainNetwork(Enum):
    """Supported blockchain networks"""
    TRON_MAINNET = "tron_mainnet"
    TRON_TESTNET = "tron_testnet"
    ETHEREUM_MAINNET = "ethereum_mainnet"
    ETHEREUM_TESTNET = "ethereum_testnet"
    POLYGON = "polygon"
    BSC = "bsc"


class TransactionStatus(Enum):
    """Transaction status states"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REVERTED = "reverted"


class AnchorType(Enum):
    """Types of blockchain anchors"""
    SESSION_MANIFEST = "session_manifest"
    SESSION_DATA = "session_data"
    SESSION_CHUNK = "session_chunk"
    SESSION_METADATA = "session_metadata"
    SESSION_VERIFICATION = "session_verification"


@dataclass
class BlockchainTransaction:
    """Blockchain transaction data"""
    tx_hash: str
    block_number: int
    block_hash: str
    status: TransactionStatus
    gas_used: int
    gas_price: int
    timestamp: datetime
    from_address: str
    to_address: str
    value: int
    data: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionAnchor:
    """Session anchor data structure"""
    anchor_id: str
    session_id: str
    anchor_type: AnchorType
    data_hash: str
    merkle_root: str
    transaction: Optional[BlockchainTransaction] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confirmed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BlockchainConfig:
    """Blockchain configuration"""
    network: BlockchainNetwork
    rpc_url: str
    contract_address: str
    private_key: str
    gas_limit: int
    gas_price: int
    timeout_seconds: int = 30
    retry_attempts: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


class BlockchainClient:
    """
    Professional blockchain integration client for Lucid RDP sessions.
    
    Provides comprehensive blockchain operations including session anchoring,
    transaction verification, and smart contract interactions.
    """
    
    def __init__(self, config: Optional[BlockchainConfig] = None):
        """Initialize blockchain client"""
        # Configuration
        self.config = config or self._load_default_config()
        
        # HTTP client
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout_seconds),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
        
        # Transaction tracking
        self.pending_transactions: Dict[str, BlockchainTransaction] = {}
        self.session_anchors: Dict[str, SessionAnchor] = {}
        
        # Statistics
        self.blockchain_stats = {
            "total_transactions": 0,
            "successful_transactions": 0,
            "failed_transactions": 0,
            "total_gas_used": 0,
            "average_confirmation_time": 0.0
        }
        
        # Create directories
        self._create_directories()
        
        logger.info(f"Blockchain client initialized for {self.config.network.value}")
    
    def _load_default_config(self) -> BlockchainConfig:
        """Load default blockchain configuration"""
        return BlockchainConfig(
            network=BlockchainNetwork.TRON_MAINNET,
            rpc_url=TRON_NETWORK_URL,
            contract_address=CONTRACT_ADDRESS,
            private_key=PRIVATE_KEY,
            gas_limit=GAS_LIMIT,
            gas_price=GAS_PRICE,
            timeout_seconds=30,
            retry_attempts=3
        )
    
    def _create_directories(self) -> None:
        """Create required directories"""
        BLOCKCHAIN_CONFIG_PATH.mkdir(parents=True, exist_ok=True)
        (BLOCKCHAIN_CONFIG_PATH / "transactions").mkdir(exist_ok=True)
        (BLOCKCHAIN_CONFIG_PATH / "anchors").mkdir(exist_ok=True)
        (BLOCKCHAIN_CONFIG_PATH / "logs").mkdir(exist_ok=True)
        logger.info(f"Created blockchain directories: {BLOCKCHAIN_CONFIG_PATH}")
    
    async def anchor_session_manifest(self,
                                     session_id: str,
                                     manifest_hash: str,
                                     merkle_root: str,
                                     owner_address: str) -> SessionAnchor:
        """Anchor session manifest to blockchain"""
        try:
            # Generate anchor ID
            anchor_id = f"{session_id}_manifest_anchor"
            
            # Create anchor data
            anchor_data = {
                "session_id": session_id,
                "manifest_hash": manifest_hash,
                "merkle_root": merkle_root,
                "owner_address": owner_address,
                "anchor_type": AnchorType.SESSION_MANIFEST.value,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Create session anchor
            anchor = SessionAnchor(
                anchor_id=anchor_id,
                session_id=session_id,
                anchor_type=AnchorType.SESSION_MANIFEST,
                data_hash=manifest_hash,
                merkle_root=merkle_root,
                metadata=anchor_data
            )
            
            # Submit transaction
            transaction = await self._submit_anchor_transaction(anchor)
            anchor.transaction = transaction
            
            # Store anchor
            self.session_anchors[anchor_id] = anchor
            
            # Save to disk
            await self._save_session_anchor(anchor)
            
            logger.info(f"Session manifest anchored: {anchor_id} -> {transaction.tx_hash}")
            
            return anchor
            
        except Exception as e:
            logger.error(f"Session manifest anchoring failed: {e}")
            raise Exception(f"Session manifest anchoring failed: {str(e)}")
    
    async def anchor_session_chunk(self,
                                  session_id: str,
                                  chunk_id: str,
                                  chunk_hash: str,
                                  owner_address: str) -> SessionAnchor:
        """Anchor session chunk to blockchain"""
        try:
            # Generate anchor ID
            anchor_id = f"{session_id}_chunk_{chunk_id}_anchor"
            
            # Create anchor data
            anchor_data = {
                "session_id": session_id,
                "chunk_id": chunk_id,
                "chunk_hash": chunk_hash,
                "owner_address": owner_address,
                "anchor_type": AnchorType.SESSION_CHUNK.value,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Create session anchor
            anchor = SessionAnchor(
                anchor_id=anchor_id,
                session_id=session_id,
                anchor_type=AnchorType.SESSION_CHUNK,
                data_hash=chunk_hash,
                merkle_root="",  # Chunks don't have merkle roots
                metadata=anchor_data
            )
            
            # Submit transaction
            transaction = await self._submit_anchor_transaction(anchor)
            anchor.transaction = transaction
            
            # Store anchor
            self.session_anchors[anchor_id] = anchor
            
            # Save to disk
            await self._save_session_anchor(anchor)
            
            logger.info(f"Session chunk anchored: {anchor_id} -> {transaction.tx_hash}")
            
            return anchor
            
        except Exception as e:
            logger.error(f"Session chunk anchoring failed: {e}")
            raise Exception(f"Session chunk anchoring failed: {str(e)}")
    
    async def verify_session_anchor(self, anchor_id: str) -> bool:
        """Verify session anchor on blockchain"""
        try:
            if anchor_id not in self.session_anchors:
                logger.error(f"Anchor not found: {anchor_id}")
                return False
            
            anchor = self.session_anchors[anchor_id]
            
            if not anchor.transaction:
                logger.error(f"No transaction for anchor: {anchor_id}")
                return False
            
            # Check transaction status
            tx_status = await self._get_transaction_status(anchor.transaction.tx_hash)
            
            if tx_status == TransactionStatus.CONFIRMED:
                anchor.confirmed_at = datetime.now(timezone.utc)
                await self._save_session_anchor(anchor)
                logger.info(f"Anchor verified: {anchor_id}")
                return True
            elif tx_status == TransactionStatus.FAILED:
                logger.error(f"Anchor transaction failed: {anchor_id}")
                return False
            else:
                logger.warning(f"Anchor transaction pending: {anchor_id}")
                return False
            
        except Exception as e:
            logger.error(f"Anchor verification failed: {e}")
            return False
    
    async def get_session_anchors(self, session_id: str) -> List[SessionAnchor]:
        """Get all anchors for a session"""
        try:
            session_anchors = [
                anchor for anchor in self.session_anchors.values()
                if anchor.session_id == session_id
            ]
            
            return session_anchors
            
        except Exception as e:
            logger.error(f"Failed to get session anchors: {e}")
            return []
    
    async def _submit_anchor_transaction(self, anchor: SessionAnchor) -> BlockchainTransaction:
        """Submit anchor transaction to blockchain"""
        try:
            # Prepare transaction data
            tx_data = {
                "anchor_id": anchor.anchor_id,
                "session_id": anchor.session_id,
                "anchor_type": anchor.anchor_type.value,
                "data_hash": anchor.data_hash,
                "merkle_root": anchor.merkle_root,
                "metadata": json.dumps(anchor.metadata)
            }
            
            # Submit transaction based on network
            if self.config.network in [BlockchainNetwork.TRON_MAINNET, BlockchainNetwork.TRON_TESTNET]:
                tx_hash = await self._submit_tron_transaction(tx_data)
            else:
                tx_hash = await self._submit_ethereum_transaction(tx_data)
            
            # Create transaction record
            transaction = BlockchainTransaction(
                tx_hash=tx_hash,
                block_number=0,  # Will be updated when confirmed
                block_hash="",
                status=TransactionStatus.PENDING,
                gas_used=0,
                gas_price=self.config.gas_price,
                timestamp=datetime.now(timezone.utc),
                from_address=self._get_from_address(),
                to_address=self.config.contract_address,
                value=0,
                data=json.dumps(tx_data)
            )
            
            # Store pending transaction
            self.pending_transactions[tx_hash] = transaction
            
            # Save transaction
            await self._save_transaction(transaction)
            
            # Update statistics
            self.blockchain_stats["total_transactions"] += 1
            
            return transaction
            
        except Exception as e:
            logger.error(f"Transaction submission failed: {e}")
            raise
    
    async def _submit_tron_transaction(self, tx_data: Dict[str, Any]) -> str:
        """Submit transaction to Tron network"""
        try:
            # Prepare Tron transaction
            tron_tx = {
                "contract_address": self.config.contract_address,
                "function_selector": "anchorSessionData(string,string,string,string,string)",
                "parameter": [
                    {"type": "string", "value": tx_data["anchor_id"]},
                    {"type": "string", "value": tx_data["session_id"]},
                    {"type": "string", "value": tx_data["anchor_type"]},
                    {"type": "string", "value": tx_data["data_hash"]},
                    {"type": "string", "value": tx_data["merkle_root"]}
                ],
                "fee_limit": self.config.gas_limit,
                "call_value": 0,
                "owner_address": self._get_from_address()
            }
            
            # Submit transaction
            response = await self.http_client.post(
                f"{self.config.rpc_url}/wallet/triggersmartcontract",
                json=tron_tx
            )
            
            if response.status_code != 200:
                raise Exception(f"Tron transaction failed: {response.status_code}")
            
            result = response.json()
            
            if "result" not in result or not result["result"]["result"]:
                raise Exception("Tron transaction rejected")
            
            tx_hash = result["txid"]
            
            logger.debug(f"Tron transaction submitted: {tx_hash}")
            
            return tx_hash
            
        except Exception as e:
            logger.error(f"Tron transaction submission failed: {e}")
            raise
    
    async def _submit_ethereum_transaction(self, tx_data: Dict[str, Any]) -> str:
        """Submit transaction to Ethereum-compatible network"""
        try:
            # Prepare Ethereum transaction
            eth_tx = {
                "to": self.config.contract_address,
                "data": self._encode_contract_data(tx_data),
                "gas": hex(self.config.gas_limit),
                "gasPrice": hex(self.config.gas_price),
                "value": "0x0"
            }
            
            # Submit transaction
            response = await self.http_client.post(
                self.config.rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_sendTransaction",
                    "params": [eth_tx],
                    "id": 1
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Ethereum transaction failed: {response.status_code}")
            
            result = response.json()
            
            if "error" in result:
                raise Exception(f"Ethereum transaction error: {result['error']}")
            
            tx_hash = result["result"]
            
            logger.debug(f"Ethereum transaction submitted: {tx_hash}")
            
            return tx_hash
            
        except Exception as e:
            logger.error(f"Ethereum transaction submission failed: {e}")
            raise
    
    def _encode_contract_data(self, tx_data: Dict[str, Any]) -> str:
        """Encode contract data for Ethereum transaction"""
        try:
            # Simple encoding - in production would use proper ABI encoding
            data_string = json.dumps(tx_data)
            data_bytes = data_string.encode()
            return "0x" + data_bytes.hex()
        except Exception as e:
            logger.error(f"Contract data encoding failed: {e}")
            raise
    
    async def _get_transaction_status(self, tx_hash: str) -> TransactionStatus:
        """Get transaction status from blockchain"""
        try:
            if self.config.network in [BlockchainNetwork.TRON_MAINNET, BlockchainNetwork.TRON_TESTNET]:
                return await self._get_tron_transaction_status(tx_hash)
            else:
                return await self._get_ethereum_transaction_status(tx_hash)
                
        except Exception as e:
            logger.error(f"Transaction status check failed: {e}")
            return TransactionStatus.FAILED
    
    async def _get_tron_transaction_status(self, tx_hash: str) -> TransactionStatus:
        """Get Tron transaction status"""
        try:
            response = await self.http_client.get(
                f"{self.config.rpc_url}/wallet/gettransactionbyid",
                params={"value": tx_hash}
            )
            
            if response.status_code != 200:
                return TransactionStatus.FAILED
            
            result = response.json()
            
            if not result:
                return TransactionStatus.PENDING
            
            # Check if transaction is confirmed
            if "blockNumber" in result and result["blockNumber"] > 0:
                return TransactionStatus.CONFIRMED
            
            return TransactionStatus.PENDING
            
        except Exception as e:
            logger.error(f"Tron transaction status check failed: {e}")
            return TransactionStatus.FAILED
    
    async def _get_ethereum_transaction_status(self, tx_hash: str) -> TransactionStatus:
        """Get Ethereum transaction status"""
        try:
            response = await self.http_client.post(
                self.config.rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_getTransactionReceipt",
                    "params": [tx_hash],
                    "id": 1
                }
            )
            
            if response.status_code != 200:
                return TransactionStatus.FAILED
            
            result = response.json()
            
            if "error" in result:
                return TransactionStatus.FAILED
            
            receipt = result.get("result")
            
            if not receipt:
                return TransactionStatus.PENDING
            
            # Check transaction status
            if receipt.get("status") == "0x1":
                return TransactionStatus.CONFIRMED
            elif receipt.get("status") == "0x0":
                return TransactionStatus.REVERTED
            else:
                return TransactionStatus.FAILED
            
        except Exception as e:
            logger.error(f"Ethereum transaction status check failed: {e}")
            return TransactionStatus.FAILED
    
    def _get_from_address(self) -> str:
        """Get from address from private key"""
        try:
            # This is a simplified implementation
            # In production, would properly derive address from private key
            if self.config.private_key:
                # Extract address from private key (simplified)
                key_hash = hashlib.sha256(self.config.private_key.encode()).hexdigest()
                return f"T{key_hash[:33]}"
            else:
                return "TDefaultAddress"
        except Exception as e:
            logger.error(f"Address derivation failed: {e}")
            return "TDefaultAddress"
    
    async def _save_transaction(self, transaction: BlockchainTransaction) -> None:
        """Save transaction to disk"""
        try:
            tx_file = BLOCKCHAIN_CONFIG_PATH / "transactions" / f"{transaction.tx_hash}.json"
            
            tx_data = {
                "tx_hash": transaction.tx_hash,
                "block_number": transaction.block_number,
                "block_hash": transaction.block_hash,
                "status": transaction.status.value,
                "gas_used": transaction.gas_used,
                "gas_price": transaction.gas_price,
                "timestamp": transaction.timestamp.isoformat(),
                "from_address": transaction.from_address,
                "to_address": transaction.to_address,
                "value": transaction.value,
                "data": transaction.data,
                "metadata": transaction.metadata
            }
            
            with open(tx_file, 'w') as f:
                json.dump(tx_data, f, indent=2)
            
            logger.debug(f"Saved transaction: {transaction.tx_hash}")
            
        except Exception as e:
            logger.error(f"Transaction saving failed: {e}")
    
    async def _save_session_anchor(self, anchor: SessionAnchor) -> None:
        """Save session anchor to disk"""
        try:
            anchor_file = BLOCKCHAIN_CONFIG_PATH / "anchors" / f"{anchor.anchor_id}.json"
            
            anchor_data = {
                "anchor_id": anchor.anchor_id,
                "session_id": anchor.session_id,
                "anchor_type": anchor.anchor_type.value,
                "data_hash": anchor.data_hash,
                "merkle_root": anchor.merkle_root,
                "transaction": {
                    "tx_hash": anchor.transaction.tx_hash if anchor.transaction else None,
                    "status": anchor.transaction.status.value if anchor.transaction else None,
                    "block_number": anchor.transaction.block_number if anchor.transaction else None
                },
                "created_at": anchor.created_at.isoformat(),
                "confirmed_at": anchor.confirmed_at.isoformat() if anchor.confirmed_at else None,
                "metadata": anchor.metadata
            }
            
            with open(anchor_file, 'w') as f:
                json.dump(anchor_data, f, indent=2)
            
            logger.debug(f"Saved session anchor: {anchor.anchor_id}")
            
        except Exception as e:
            logger.error(f"Session anchor saving failed: {e}")
    
    async def monitor_pending_transactions(self) -> None:
        """Monitor pending transactions for confirmation"""
        try:
            for tx_hash, transaction in list(self.pending_transactions.items()):
                status = await self._get_transaction_status(tx_hash)
                
                if status == TransactionStatus.CONFIRMED:
                    transaction.status = TransactionStatus.CONFIRMED
                    self.blockchain_stats["successful_transactions"] += 1
                    
                    # Update corresponding anchor
                    for anchor in self.session_anchors.values():
                        if anchor.transaction and anchor.transaction.tx_hash == tx_hash:
                            anchor.confirmed_at = datetime.now(timezone.utc)
                            await self._save_session_anchor(anchor)
                    
                    # Remove from pending
                    del self.pending_transactions[tx_hash]
                    
                    logger.info(f"Transaction confirmed: {tx_hash}")
                    
                elif status == TransactionStatus.FAILED:
                    transaction.status = TransactionStatus.FAILED
                    self.blockchain_stats["failed_transactions"] += 1
                    
                    # Remove from pending
                    del self.pending_transactions[tx_hash]
                    
                    logger.warning(f"Transaction failed: {tx_hash}")
            
        except Exception as e:
            logger.error(f"Transaction monitoring failed: {e}")
    
    def get_blockchain_stats(self) -> Dict[str, Any]:
        """Get blockchain operation statistics"""
        return {
            "network": self.config.network.value,
            "contract_address": self.config.contract_address,
            "statistics": self.blockchain_stats.copy(),
            "pending_transactions": len(self.pending_transactions),
            "session_anchors": len(self.session_anchors),
            "confirmed_anchors": len([a for a in self.session_anchors.values() if a.confirmed_at])
        }
    
    async def close(self) -> None:
        """Close blockchain client"""
        try:
            await self.http_client.aclose()
            logger.info("Blockchain client closed")
        except Exception as e:
            logger.error(f"Blockchain client close failed: {e}")


# Global blockchain client instance
blockchain_client: Optional[BlockchainClient] = None


def get_blockchain_client() -> BlockchainClient:
    """Get global blockchain client instance"""
    global blockchain_client
    if blockchain_client is None:
        blockchain_client = BlockchainClient()
    return blockchain_client


async def initialize_blockchain_client(config: Optional[BlockchainConfig] = None) -> BlockchainClient:
    """Initialize blockchain client"""
    global blockchain_client
    blockchain_client = BlockchainClient(config)
    logger.info("Blockchain client initialized")
    return blockchain_client


async def shutdown_blockchain_client() -> None:
    """Shutdown blockchain client"""
    global blockchain_client
    if blockchain_client:
        await blockchain_client.close()
        blockchain_client = None
    logger.info("Blockchain client shutdown")
