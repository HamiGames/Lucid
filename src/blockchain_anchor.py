# Lucid RDP Blockchain Anchor System
# REBUILT: Dual-chain architecture with On-System Data Chain as primary, TRON for payments only
# Handles session manifest anchoring to On-System Data Chain and TRON
# Based on LUCID-STRICT requirements for dual-chain architecture

from __future__ import annotations

import asyncio
import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
import httpx
from tronpy import Tron
from tronpy.keys import PrivateKey

# Import updated models from blockchain.core.models
from blockchain.core.models import (
    SessionAnchor, TronPayout, SessionManifest, ChainType, PayoutRouter,
    SessionStatus, PayoutStatus, generate_session_id
)

logger = logging.getLogger(__name__)

# On-System Data Chain Configuration (Primary Blockchain)
ON_SYSTEM_CHAIN_RPC = os.getenv("ON_SYSTEM_CHAIN_RPC", "http://localhost:8545")
LUCID_ANCHORS_ADDRESS = os.getenv("LUCID_ANCHORS_ADDRESS", "")
LUCID_CHUNK_STORE_ADDRESS = os.getenv("LUCID_CHUNK_STORE_ADDRESS", "")

# TRON Payment Service Configuration (Isolated)
TRON_NETWORK = os.getenv("TRON_NETWORK", "shasta")  # shasta for testnet, mainnet for prod
TRON_PRIVATE_KEY = os.getenv("TRON_PRIVATE_KEY", "")  # Must be provided for payments
USDT_TRC20_MAINNET = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
USDT_TRC20_SHASTA = "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs"

# MongoDB Configuration
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/lucid")
BLOCK_ONION = os.getenv("BLOCK_ONION", "")  # Blockchain service onion address

# Legacy configuration (deprecated)
ON_CHAIN_RPC_URL = ON_SYSTEM_CHAIN_RPC
ANCHOR_CONTRACT_ADDRESS = LUCID_ANCHORS_ADDRESS


@dataclass
class AnchorResult:
    """Result of anchoring operation - Updated for dual-chain architecture"""
    session_id: str
    anchor_txid: str
    on_system_chain_txid: Optional[str]  # Primary blockchain transaction
    tron_payment_txid: Optional[str]     # Payment transaction (if applicable)
    anchor_timestamp: datetime
    gas_used: int
    anchor_fee: int  # in ETH/wei (On-System Chain)
    payment_fee: int  # in TRX (TRON payments)
    status: str  # "pending", "confirmed", "failed"
    
    # Legacy compatibility
    on_chain_txid: Optional[str] = None
    tron_txid: Optional[str] = None
    
    def __post_init__(self):
        """Set legacy fields for backward compatibility"""
        if self.on_chain_txid is None:
            self.on_chain_txid = self.on_system_chain_txid
        if self.tron_txid is None:
            self.tron_txid = self.tron_payment_txid


class OnSystemChainClient:
    """Client for On-System Data Chain operations - Updated for dual-chain architecture"""
    
    def __init__(self, rpc_url: str = None, contract_address: str = None):
        self.rpc_url = rpc_url or ON_SYSTEM_CHAIN_RPC
        self.contract_address = contract_address or LUCID_ANCHORS_ADDRESS
        self.chunk_store_address = LUCID_CHUNK_STORE_ADDRESS
        self.session = httpx.AsyncClient()
        
        logger.info(f"OnSystemChainClient initialized: {self.rpc_url}")
        logger.info(f"Contracts: Anchors={self.contract_address}, ChunkStore={self.chunk_store_address}")
    
    async def anchor_manifest(self, manifest: SessionManifest) -> str:
        """Anchor session manifest to On-System Data Chain"""
        try:
            # Prepare anchor data
            anchor_data = {
                "session_id": manifest.session_id,
                "owner_address": manifest.owner_address,
                "merkle_root": manifest.merkle_root,
                "manifest_hash": manifest.manifest_hash,
                "chunk_count": manifest.chunk_count,
                "timestamp": manifest.started_at.isoformat()
            }
            
            # Call LucidAnchors contract
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_sendTransaction",
                "params": [{
                    "to": self.contract_address,
                    "data": self._encode_anchor_call(anchor_data),
                    "gas": "0x5208"  # 21000 gas
                }],
                "id": 1
            }
            
            response = await self.session.post(self.rpc_url, json=payload)
            result = response.json()
            
            if "result" in result:
                txid = result["result"]
                logger.info(f"Anchored session {manifest.session_id} to On-Chain: {txid}")
                return txid
            else:
                raise ValueError(f"On-chain anchor failed: {result.get('error')}")
                
        except Exception as e:
            logger.error(f"On-chain anchoring failed for {manifest.session_id}: {e}")
            raise
    
    def _encode_anchor_call(self, anchor_data: Dict[str, Any]) -> str:
        """Encode contract call data for LucidAnchors.registerSession()"""
        # This would use proper ABI encoding in production
        # Simplified for demonstration
        session_id_hex = anchor_data["session_id"].replace("-", "")
        merkle_root = anchor_data["merkle_root"]
        return f"0x{session_id_hex}{merkle_root}"
    
    async def get_anchor_status(self, txid: str) -> str:
        """Get status of anchor transaction"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [txid],
                "id": 1
            }
            
            response = await self.session.post(self.rpc_url, json=payload)
            result = response.json()
            
            if result.get("result"):
                receipt = result["result"]
                if receipt.get("status") == "0x1":
                    return "confirmed"
                else:
                    return "failed"
            else:
                return "pending"
                
        except Exception as e:
            logger.error(f"Failed to get anchor status for {txid}: {e}")
            return "unknown"
    
    async def close(self):
        """Close HTTP session"""
        await self.session.aclose()


class TronChainClient:
    """Client for TRON blockchain operations (isolated payment service only)"""
    
    def __init__(self, network: str = None, private_key_hex: str = None):
        network = network or TRON_NETWORK
        private_key_hex = private_key_hex or TRON_PRIVATE_KEY
        
        if network == "mainnet":
            self.tron = Tron()
            self.usdt_contract = USDT_TRC20_MAINNET
        else:
            # Shasta testnet
            self.tron = Tron(network="shasta")
            self.usdt_contract = USDT_TRC20_SHASTA
        
        if private_key_hex:
            self.private_key = PrivateKey(bytes.fromhex(private_key_hex))
            self.address = self.private_key.public_key.to_base58check_address()
        else:
            self.private_key = None
            self.address = None
        
        logger.info(f"TRON payment client initialized: {network}, address: {self.address}")
        logger.info(f"USDT contract: {self.usdt_contract}")
    
    async def create_payout(self, session_id: str, to_address: str, 
                          usdt_amount: int, reason: str) -> str:
        """Create USDT-TRC20 payout transaction"""
        if not self.private_key:
            raise ValueError("TRON private key not configured")
        
        try:
            # Build transfer transaction using configured USDT contract
            contract = self.tron.get_contract(self.usdt_contract)
            
            # USDT has 6 decimals
            amount_with_decimals = usdt_amount * (10 ** 6)
            
            txn = contract.functions.transfer(to_address, amount_with_decimals)
            txn = txn.with_owner(self.address)
            txn = txn.fee_limit(100_000_000)  # 100 TRX fee limit
            
            # Sign and broadcast
            txn = txn.build()
            txn = txn.sign(self.private_key)
            result = txn.broadcast()
            
            txid = result.get("txid")
            if txid:
                logger.info(f"TRON payout created: {txid}, {usdt_amount} USDT to {to_address}")
                return txid
            else:
                raise ValueError(f"TRON broadcast failed: {result}")
                
        except Exception as e:
            logger.error(f"TRON payout failed for session {session_id}: {e}")
            raise
    
    async def get_transaction_status(self, txid: str) -> str:
        """Get status of TRON transaction"""
        try:
            info = self.tron.get_transaction_info(txid)
            if info:
                if info.get("result") == "SUCCESS":
                    return "confirmed"
                else:
                    return "failed"
            else:
                return "pending"
        except Exception as e:
            logger.error(f"Failed to get TRON tx status for {txid}: {e}")
            return "unknown"


class BlockchainAnchor:
    """Main blockchain anchor service"""
    
    def __init__(self, mongo_client: AsyncIOMotorClient):
        self.mongo_client = mongo_client
        self.db = mongo_client.get_database("lucid")
        self.sessions_collection: AsyncIOMotorCollection = self.db.sessions
        self.anchors_collection: AsyncIOMotorCollection = self.db.anchors
        self.payouts_collection: AsyncIOMotorCollection = self.db.payouts
        
        # Initialize chain clients
        self.on_chain_client = OnSystemChainClient()  # Uses default configuration
        self.tron_client = TronChainClient() if TRON_PRIVATE_KEY else None
        
        logger.info("Blockchain anchor service initialized")
    
    async def anchor_session(self, manifest: SessionManifest) -> AnchorResult:
        """Anchor session manifest to blockchain"""
        try:
            # Store session in MongoDB first
            await self._store_session_manifest(manifest)
            
            # Anchor to On-System Data Chain
            on_chain_txid = await self.on_chain_client.anchor_manifest(manifest)
            
            # Create anchor result
            anchor_result = AnchorResult(
                session_id=manifest.session_id,
                anchor_txid=on_chain_txid,
                on_system_chain_txid=on_chain_txid,
                tron_payment_txid=None,
                anchor_timestamp=datetime.now(timezone.utc),
                gas_used=21000,  # Estimate
                anchor_fee=0,  # Free for On-System Chain
                payment_fee=0,  # No TRON payment in session anchoring
                status="pending"
            )
            
            # Store anchor result
            await self.anchors_collection.insert_one(anchor_result.__dict__)
            
            # Update session with anchor info
            await self.sessions_collection.update_one(
                {"_id": manifest.session_id},
                {"$set": {"anchor_txid": on_chain_txid}}
            )
            
            logger.info(f"Session {manifest.session_id} anchored successfully")
            return anchor_result
            
        except Exception as e:
            logger.error(f"Failed to anchor session {manifest.session_id}: {e}")
            raise
    
    async def create_payout(self, session_id: str, to_address: str, 
                          usdt_amount: int, reason: str = "session_reward") -> Optional[str]:
        """Create USDT payout for session"""
        if not self.tron_client:
            logger.warning("TRON client not configured, skipping payout")
            return None
        
        try:
            # Create payout transaction
            tron_txid = await self.tron_client.create_payout(
                session_id, to_address, usdt_amount, reason
            )
            
            # Store payout record
            payout_record = {
                "_id": f"{session_id}-{datetime.now().isoformat()}",
                "session_id": session_id,
                "to_addr": to_address,
                "usdt_amount": usdt_amount,
                "router": "PayoutRouterV0" if TRON_NETWORK == "mainnet" else "PayoutRouterKYC",
                "reason": reason,
                "txid": tron_txid,
                "status": "pending",
                "created_at": datetime.now(timezone.utc),
                "network": TRON_NETWORK,
                "service_type": "tron_payment_only"
            }
            
            await self.payouts_collection.insert_one(payout_record)
            
            logger.info(f"Payout created: {usdt_amount} USDT to {to_address}")
            return tron_txid
            
        except Exception as e:
            logger.error(f"Failed to create payout for session {session_id}: {e}")
            raise
    
    async def check_anchor_confirmations(self) -> None:
        """Check and update status of pending anchors"""
        try:
            pending_anchors = await self.anchors_collection.find(
                {"status": "pending"}
            ).to_list(length=100)
            
            for anchor in pending_anchors:
                # Check On-System Chain status
                on_chain_status = await self.on_chain_client.get_anchor_status(
                    anchor.get("on_system_chain_txid") or anchor.get("on_chain_txid")
                )
                
                # Check TRON status if applicable (for payments only)
                tron_status = "confirmed"
                if anchor.get("tron_payment_txid") or anchor.get("tron_txid"):
                    tron_txid = anchor.get("tron_payment_txid") or anchor.get("tron_txid")
                    tron_status = await self.tron_client.get_transaction_status(tron_txid)
                
                # Update status if both chains confirmed
                if on_chain_status == "confirmed" and tron_status == "confirmed":
                    await self.anchors_collection.update_one(
                        {"_id": anchor["_id"]},
                        {"$set": {"status": "confirmed"}}
                    )
                    logger.info(f"Anchor confirmed: {anchor['session_id']}")
                
        except Exception as e:
            logger.error(f"Failed to check anchor confirmations: {e}")
    
    async def check_payout_confirmations(self) -> None:
        """Check and update status of pending payouts"""
        try:
            if not self.tron_client:
                return
            
            pending_payouts = await self.payouts_collection.find(
                {"status": "pending"}
            ).to_list(length=100)
            
            for payout in pending_payouts:
                status = await self.tron_client.get_transaction_status(payout["txid"])
                
                if status != "pending":
                    await self.payouts_collection.update_one(
                        {"_id": payout["_id"]},
                        {"$set": {"status": status}}
                    )
                    
                    logger.info(f"Payout {payout['_id']} status updated: {status}")
                    
        except Exception as e:
            logger.error(f"Failed to check payout confirmations: {e}")
    
    async def _store_session_manifest(self, manifest: SessionManifest) -> None:
        """Store session manifest in MongoDB"""
        session_doc = manifest.to_dict()
        
        # Upsert session document
        await self.sessions_collection.replace_one(
            {"_id": manifest.session_id},
            session_doc,
            upsert=True
        )
        
        # Store individual chunks in sharded collection
        if manifest.chunks:
            chunk_docs = [chunk.to_dict() for chunk in manifest.chunks]
            await self.db.chunks.insert_many(chunk_docs, ordered=False)
    
    async def get_session_anchors(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all anchor records for a session"""
        anchors = await self.anchors_collection.find(
            {"session_id": session_id}
        ).to_list(length=None)
        
        return anchors
    
    async def get_session_payouts(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all payout records for a session"""
        payouts = await self.payouts_collection.find(
            {"session_id": session_id}
        ).to_list(length=None)
        
        return payouts
    
    async def close(self):
        """Close blockchain clients"""
        await self.on_chain_client.close()


class AnchorService:
    """Background service for anchor and payout processing"""
    
    def __init__(self, anchor: BlockchainAnchor):
        self.anchor = anchor
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start background processing"""
        if self.is_running:
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._processing_loop())
        logger.info("Anchor service started")
    
    async def stop(self) -> None:
        """Stop background processing"""
        self.is_running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Anchor service stopped")
    
    async def _processing_loop(self) -> None:
        """Background processing loop"""
        try:
            while self.is_running:
                # Check anchor confirmations every 30 seconds
                await self.anchor.check_anchor_confirmations()
                
                # Check payout confirmations every 60 seconds
                await self.anchor.check_payout_confirmations()
                
                # Wait before next iteration
                await asyncio.sleep(30)
                
        except asyncio.CancelledError:
            logger.info("Anchor service processing cancelled")
        except Exception as e:
            logger.error(f"Anchor service error: {e}")
            # Restart after error
            await asyncio.sleep(10)
            if self.is_running:
                await self._processing_loop()