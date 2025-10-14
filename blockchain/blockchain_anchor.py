# Path: blockchain/blockchain_anchor.py
"""
Lucid RDP Blockchain Anchor System
Handles session manifest anchoring to On-System Data Chain (primary)
TRON isolated to payment service only (not core anchoring)
Based on LUCID-STRICT requirements for dual-chain architecture
REBUILT: On-System Chain as primary, TRON for payments only
"""

from __future__ import annotations

import asyncio
import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
import httpx

from .core.models import SessionManifest, SessionAnchor, ChunkMetadata, PayoutRouter

logger = logging.getLogger(__name__)

# =============================================================================
# ON-SYSTEM DATA CHAIN CONFIGURATION (R-MUST-016)
# =============================================================================

ON_SYSTEM_CHAIN_RPC = os.getenv("ON_SYSTEM_CHAIN_RPC", "http://on-chain-distroless:8545")
LUCID_ANCHORS_ADDRESS = os.getenv("LUCID_ANCHORS_ADDRESS", "")
LUCID_CHUNK_STORE_ADDRESS = os.getenv("LUCID_CHUNK_STORE_ADDRESS", "")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://lucid:lucid@mongo-distroless:27019/lucid?authSource=admin&retryWrites=false&directConnection=true")

# =============================================================================
# TRON PAYMENT LAYER CONFIGURATION (R-MUST-015, R-MUST-018) - ISOLATED
# =============================================================================

# TRON_NETWORK = os.getenv("TRON_NETWORK", "shasta")  # shasta for testnet, mainnet for prod
# TRON_PRIVATE_KEY = os.getenv("TRON_PRIVATE_KEY", "")  # Must be provided
# PAYOUT_ROUTER_V0_ADDRESS = os.getenv("PAYOUT_ROUTER_V0_ADDRESS", "")
# PAYOUT_ROUTER_KYC_ADDRESS = os.getenv("PAYOUT_ROUTER_KYC_ADDRESS", "")


@dataclass
class AnchorResult:
    """
    Result of On-System Chain anchoring operation.
    
    REBUILT: Focused on On-System Chain anchoring only.
    TRON operations are handled separately by payment service.
    """
    session_id: str
    anchor_txid: str  # On-System Chain transaction ID
    block_number: Optional[int] = None
    gas_used: int = 0
    anchor_timestamp: datetime = None
    status: str = "pending"  # "pending", "confirmed", "failed"
    
    def __post_init__(self):
        if self.anchor_timestamp is None:
            self.anchor_timestamp = datetime.now(timezone.utc)


class OnSystemChainClient:
    """
    Client for On-System Data Chain operations.
    
    REBUILT: Primary blockchain client for session anchoring.
    Handles LucidAnchors and LucidChunkStore contract interactions.
    """
    
    def __init__(self, rpc_url: str, contract_addresses: Dict[str, str]):
        self.rpc_url = rpc_url
        self.contracts = contract_addresses
        self.session = httpx.AsyncClient(timeout=30.0)
        
        logger.info(f"On-System Chain client initialized: {rpc_url}")
    
    async def anchor_session_manifest(self, anchor: SessionAnchor) -> str:
        """
        Anchor session manifest to LucidAnchors contract.
        
        Per Spec-1b: registerSession(sessionId, manifestHash, startedAt, owner, merkleRoot, chunkCount)
        Gas-efficient: uses events for data, minimal storage writes
        """
        try:
            # Prepare contract call data
            call_data = {
                "to": self.contracts.get("LucidAnchors", LUCID_ANCHORS_ADDRESS),
                "data": self._encode_register_session_call({
                    "sessionId": anchor.session_id.replace("-", ""),
                    "manifestHash": anchor.manifest_hash,
                    "startedAt": anchor.started_at,
                    "owner": anchor.owner_address,
                    "merkleRoot": anchor.merkle_root,
                    "chunkCount": anchor.chunk_count
                }),
                "gas": "0x15F90",  # 90,000 gas limit
                "gasPrice": "0x3B9ACA00"  # 1 Gwei
            }
            
            # Submit transaction
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_sendTransaction",
                "params": [call_data],
                "id": 1
            }
            
            response = await self.session.post(self.rpc_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if "error" in result:
                raise Exception(f"RPC error: {result['error']}")
            
            txid = result["result"]
            anchor.txid = txid
            anchor.status = "pending"
            
            logger.info(f"Session anchored to On-System Chain: {txid}")
            return txid
            
        except Exception as e:
            logger.error(f"Failed to anchor session manifest: {e}")
            anchor.status = "failed"
            raise
    
    def _encode_register_session_call(self, params: Dict[str, Any]) -> str:
        """Encode registerSession contract call (simplified)"""
        import hashlib
        # Method signature: registerSession(bytes32,bytes32,uint256,address,bytes32,uint256)
        method_sig = "0x" + hashlib.sha3_256(b"registerSession(bytes32,bytes32,uint256,address,bytes32,uint256)").hexdigest()[:8]
        
        # Encode parameters (simplified - would use proper ABI encoding in production)
        encoded_params = ""
        encoded_params += params["sessionId"].ljust(64, "0")  # bytes32
        encoded_params += params["manifestHash"].ljust(64, "0")  # bytes32
        encoded_params += hex(params["startedAt"])[2:].rjust(64, "0")  # uint256
        encoded_params += params["owner"][2:].rjust(64, "0")  # address
        encoded_params += params["merkleRoot"].ljust(64, "0")  # bytes32
        encoded_params += hex(params["chunkCount"])[2:].rjust(64, "0")  # uint256
        
        return method_sig + encoded_params
    
    def _encode_store_chunk_call(self, params: Dict[str, Any]) -> str:
        """Encode storeChunkMetadata contract call (simplified)"""
        import hashlib
        # Method signature: storeChunkMetadata(bytes32,uint256,bytes32,uint256)
        method_sig = "0x" + hashlib.sha3_256(b"storeChunkMetadata(bytes32,uint256,bytes32,uint256)").hexdigest()[:8]
        
        # Encode parameters (simplified - would use proper ABI encoding in production)
        encoded_params = ""
        encoded_params += params["sessionId"].ljust(64, "0")  # bytes32
        encoded_params += hex(params["chunkIndex"])[2:].rjust(64, "0")  # uint256
        encoded_params += params["ciphertextSha256"].ljust(64, "0")  # bytes32
        encoded_params += hex(params["sizeBytes"])[2:].rjust(64, "0")  # uint256
        
        return method_sig + encoded_params
    
    async def get_transaction_status(self, txid: str) -> tuple[str, Optional[int]]:
        """Get On-System Chain transaction confirmation status"""
        try:
            # Get transaction receipt
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_getTransactionReceipt",
                "params": [txid],
                "id": 1
            }
            
            response = await self.session.post(self.rpc_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if "error" in result or not result["result"]:
                return "pending", None
            
            receipt = result["result"]
            if receipt.get("status") == "0x1":
                return "confirmed", int(receipt.get("blockNumber", "0x0"), 16)
            else:
                return "failed", None
                
        except Exception as e:
            logger.error(f"Failed to get transaction status: {e}")
            return "unknown", None
    
    async def store_chunk_metadata(self, session_id: str, chunk_idx: int, metadata: Dict[str, Any]) -> str:
        """
        Store encrypted chunk metadata in LucidChunkStore contract.
        
        Per Spec-1b: storeChunkMetadata(sessionId, chunkIndex, ciphertextSha256, sizeBytes)
        """
        try:
            call_data = {
                "to": self.contracts.get("LucidChunkStore", LUCID_CHUNK_STORE_ADDRESS),
                "data": self._encode_store_chunk_call({
                    "sessionId": session_id.replace("-", ""),
                    "chunkIndex": chunk_idx,
                    "ciphertextSha256": metadata["ciphertext_sha256"],
                    "sizeBytes": metadata["size_bytes"]
                }),
                "gas": "0x13880",  # 80,000 gas limit
                "gasPrice": "0x3B9ACA00"
            }
            
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_sendTransaction",
                "params": [call_data],
                "id": 1
            }
            
            response = await self.session.post(self.rpc_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if "error" in result:
                raise Exception(f"RPC error: {result['error']}")
            
            txid = result["result"]
            logger.info(f"Chunk metadata stored: {txid}")
            return txid
            
        except Exception as e:
            logger.error(f"Failed to store chunk metadata: {e}")
            raise
    
    async def close(self):
        """Close HTTP session"""
        await self.session.aclose()


# =============================================================================
# TRON PAYMENT SERVICE (ISOLATED) - NOT PART OF CORE BLOCKCHAIN
# =============================================================================

# class TronPaymentService:
#     """
#     TRON payment service for USDT-TRC20 payouts only.
#     
#     ISOLATED: This service is completely separate from core blockchain operations.
#     Used only for monthly payout distribution via PayoutRouterV0/PRKYC.
#     """
#     
#     def __init__(self, network: str, private_key_hex: str):
#         # Import TRON dependencies only for payment operations
#         from tronpy import Tron
#         from tronpy.keys import PrivateKey
#         
#         if network == "mainnet":
#             self.tron = Tron()
#         else:
#             # Shasta testnet
#             self.tron = Tron(network="shasta")
#         
#         if private_key_hex:
#             self.private_key = PrivateKey(bytes.fromhex(private_key_hex))
#             self.address = self.private_key.public_key.to_base58check_address()
#         else:
#             self.private_key = None
#             self.address = None
#         
#         logger.info(f"TRON payment service initialized: {network}, address: {self.address}")
#     
#     async def create_usdt_payout(self, session_id: str, to_address: str, 
#                                usdt_amount: float, router_type: PayoutRouter) -> str:
#         """
#         Create USDT-TRC20 payout via specified router.
#         
#         Router selection per Spec-1c:
#         - PayoutRouterV0 (PR0): Non-KYC for end-users
#         - PayoutRouterKYC (PRKYC): KYC-gated for node-workers
#         """
#         if not self.private_key:
#             raise ValueError("TRON private key not configured")
#         
#         try:
#             # Get router contract address
#             router_address = self._get_router_address(router_type)
#             
#             # Get USDT-TRC20 contract address
#             usdt_contract = self._get_usdt_contract_address()
#             
#             # USDT has 6 decimals
#             amount_with_decimals = int(usdt_amount * 1_000_000)
#             
#             # Build payout transaction via router
#             contract = self.tron.get_contract(router_address)
#             
#             if router_type == PayoutRouter.PR0:
#                 # Non-KYC payout via PayoutRouterV0
#                 txn = contract.functions.disburse(
#                     session_id.replace("-", "").encode(),
#                     to_address,
#                     amount_with_decimals,
#                     "session_reward"
#                 )
#             else:  # PRKYC
#                 # KYC-gated payout via PayoutRouterKYC
#                 txn = contract.functions.disburseKYC(
#                     session_id.replace("-", "").encode(),
#                     to_address,
#                     amount_with_decimals,
#                     "session_reward",
#                     b"",  # KYC hash (would be provided in real implementation)
#                     0,    # Expiry (would be calculated in real implementation)
#                     0,    # v (signature component)
#                     b"",  # r (signature component)
#                     b""   # s (signature component)
#                 )
#             
#             txn = txn.with_owner(self.address)
#             txn = txn.fee_limit(100_000_000)  # 100 TRX fee limit
#             
#             # Sign and broadcast
#             txn = txn.build()
#             txn = txn.sign(self.private_key)
#             result = txn.broadcast()
#             
#             txid = result.get("txid")
#             if txid:
#                 logger.info(f"TRON payout created: {txid}, {usdt_amount} USDT to {to_address}")
#                 return txid
#             else:
#                 raise ValueError(f"TRON broadcast failed: {result}")
#                 
#         except Exception as e:
#             logger.error(f"TRON payout failed for session {session_id}: {e}")
#             raise
#     
#     def _get_router_address(self, router_type: PayoutRouter) -> str:
#         """Get router contract address"""
#         if router_type == PayoutRouter.PR0:
#             return PAYOUT_ROUTER_V0_ADDRESS
#         else:
#             return PAYOUT_ROUTER_KYC_ADDRESS
#     
#     def _get_usdt_contract_address(self) -> str:
#         """Get USDT-TRC20 contract address for current network"""
#         if self.tron.is_shasta:
#             return "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs"  # Shasta USDT
#         else:
#             return "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # Mainnet USDT
#     
#     async def get_payout_status(self, txid: str) -> str:
#         """Get status of TRON payout transaction"""
#         try:
#             info = self.tron.get_transaction_info(txid)
#             if info:
#                 if info.get("result") == "SUCCESS":
#                     return "confirmed"
#                 else:
#                     return "failed"
#             else:
#                 return "pending"
#         except Exception as e:
#             logger.error(f"Failed to get TRON payout status for {txid}: {e}")
#             return "unknown"


class BlockchainAnchor:
    """
    Main blockchain anchor service.
    
    REBUILT: On-System Chain as primary, TRON isolated to payment service only.
    Handles session anchoring to On-System Data Chain via LucidAnchors contract.
    """
    
    def __init__(self, mongo_client: AsyncIOMotorClient):
        self.mongo_client = mongo_client
        self.db = mongo_client.get_database("lucid")
        self.sessions_collection: AsyncIOMotorCollection = self.db.sessions
        self.anchors_collection: AsyncIOMotorCollection = self.db.anchors
        self.payouts_collection: AsyncIOMotorCollection = self.db.payouts
        
        # Initialize On-System Chain client (primary blockchain)
        contract_addresses = {
            "LucidAnchors": LUCID_ANCHORS_ADDRESS,
            "LucidChunkStore": LUCID_CHUNK_STORE_ADDRESS
        }
        self.on_chain_client = OnSystemChainClient(ON_SYSTEM_CHAIN_RPC, contract_addresses)
        
        # Initialize TRON payment service (isolated)
        # self.tron_payment_service = TronPaymentService(TRON_NETWORK, TRON_PRIVATE_KEY) if TRON_PRIVATE_KEY else None
        
        logger.info("Blockchain anchor service initialized - On-System Chain primary, TRON payment isolated")
    
    async def anchor_session(self, manifest: SessionManifest) -> AnchorResult:
        """
        Anchor session manifest to On-System Data Chain.
        
        REBUILT: Uses LucidAnchors contract for primary anchoring.
        TRON is not used for core anchoring - only for payments.
        """
        try:
            # Store session in MongoDB first
            await self._store_session_manifest(manifest)
            
            # Create session anchor for On-System Chain
            session_anchor = SessionAnchor(
                session_id=manifest.session_id,
                manifest_hash=manifest.manifest_hash,
                merkle_root=manifest.merkle_root,
                started_at=int(manifest.started_at.timestamp()),
                owner_address=manifest.owner_address,
                chunk_count=manifest.chunk_count
            )
            
            # Anchor to On-System Data Chain via LucidAnchors contract
            txid = await self.on_chain_client.anchor_session_manifest(session_anchor)
            
            # Create anchor result
            anchor_result = AnchorResult(
                session_id=manifest.session_id,
                anchor_txid=txid,
                block_number=None,
                gas_used=90000,  # Gas limit for registerSession
                anchor_timestamp=datetime.now(timezone.utc),
                status="pending"
            )
            
            # Store anchor result
            await self.anchors_collection.insert_one(anchor_result.__dict__)
            
            # Update session with anchor info
            await self.sessions_collection.update_one(
                {"_id": manifest.session_id},
                {"$set": {"anchor_txid": txid, "status": "pending"}}
            )
            
            logger.info(f"Session {manifest.session_id} anchored to On-System Chain: {txid}")
            return anchor_result
            
        except Exception as e:
            logger.error(f"Failed to anchor session {manifest.session_id}: {e}")
            raise
    
    # async def create_payout(self, session_id: str, to_address: str, 
    #                       usdt_amount: float, router_type: PayoutRouter = PayoutRouter.PR0,
    #                       reason: str = "session_reward") -> Optional[str]:
    #     """
    #     Create USDT payout via TRON payment service (isolated).
    #     
    #     REBUILT: Uses isolated TRON payment service, not core blockchain.
    #     Router selection: PayoutRouterV0 (non-KYC) vs PayoutRouterKYC (KYC-gated).
    #     """
    #     if not self.tron_payment_service:
    #         logger.warning("TRON payment service not configured, skipping payout")
    #         return None
    #     
    #     try:
    #         # Create payout transaction via TRON payment service
    #         tron_txid = await self.tron_payment_service.create_usdt_payout(
    #             session_id, to_address, usdt_amount, router_type
    #         )
    #         
    #         # Store payout record
    #         payout_record = {
    #             "_id": f"{session_id}-{datetime.now().isoformat()}",
    #             "session_id": session_id,
    #             "to_addr": to_address,
    #             "usdt_amount": usdt_amount,
    #             "router": router_type.value,
    #             "reason": reason,
    #             "txid": tron_txid,
    #             "status": "pending",
    #             "created_at": datetime.now(timezone.utc)
    #         }
    #         
    #         await self.payouts_collection.insert_one(payout_record)
    #         
    #         logger.info(f"Payout created via {router_type.value}: {usdt_amount} USDT to {to_address}")
    #         return tron_txid
    #         
    #     except Exception as e:
    #         logger.error(f"Failed to create payout for session {session_id}: {e}")
    #         raise
    
    async def check_anchor_confirmations(self) -> None:
        """
        Check and update status of pending On-System Chain anchors.
        
        REBUILT: Only checks On-System Chain confirmations.
        TRON confirmations are handled separately by payment service.
        """
        try:
            pending_anchors = await self.anchors_collection.find(
                {"status": "pending"}
            ).to_list(length=100)
            
            for anchor in pending_anchors:
                # Check On-System Chain status
                status, block_number = await self.on_chain_client.get_transaction_status(
                    anchor["anchor_txid"]
                )
                
                if status == "confirmed":
                    # Update anchor status
                    await self.anchors_collection.update_one(
                        {"_id": anchor["_id"]},
                        {
                            "$set": {
                                "status": "confirmed",
                                "block_number": block_number
                            }
                        }
                    )
                    
                    # Update session status
                    await self.sessions_collection.update_one(
                        {"_id": anchor["session_id"]},
                        {
                            "$set": {
                                "status": "confirmed",
                                "block_number": block_number
                            }
                        }
                    )
                    
                    logger.info(f"Anchor confirmed: {anchor['session_id']} in block {block_number}")
                    
                elif status == "failed":
                    await self.anchors_collection.update_one(
                        {"_id": anchor["_id"]},
                        {"$set": {"status": "failed"}}
                    )
                    
                    await self.sessions_collection.update_one(
                        {"_id": anchor["session_id"]},
                        {"$set": {"status": "failed"}}
                    )
                    
                    logger.warning(f"Anchor failed: {anchor['session_id']}")
                
        except Exception as e:
            logger.error(f"Failed to check anchor confirmations: {e}")
    
    # async def check_payout_confirmations(self) -> None:
    #     """
    #     Check and update status of pending TRON payouts.
    #     
    #     REBUILT: Uses isolated TRON payment service for payout confirmations.
    #     """
    #     try:
    #         if not self.tron_payment_service:
    #             return
    #         
    #         pending_payouts = await self.payouts_collection.find(
    #             {"status": "pending"}
    #         ).to_list(length=100)
    #         
    #         for payout in pending_payouts:
    #             status = await self.tron_payment_service.get_payout_status(payout["txid"])
    #             
    #             if status != "pending":
    #                 await self.payouts_collection.update_one(
    #                     {"_id": payout["_id"]},
    #                     {"$set": {"status": status}}
    #                 )
    #                 
    #                 logger.info(f"Payout {payout['_id']} status updated: {status}")
    #                 
    #     except Exception as e:
    #         logger.error(f"Failed to check payout confirmations: {e}")
    
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
    
    async def store_chunk_metadata(self, session_id: str, chunk_idx: int, metadata: Dict[str, Any]) -> str:
        """
        Store chunk metadata to LucidChunkStore contract.
        
        Per Spec-1b: storeChunkMetadata(sessionId, chunkIndex, ciphertextSha256, sizeBytes)
        """
        try:
            txid = await self.on_chain_client.store_chunk_metadata(session_id, chunk_idx, metadata)
            logger.info(f"Chunk metadata stored: {session_id}[{chunk_idx}] -> {txid}")
            return txid
        except Exception as e:
            logger.error(f"Failed to store chunk metadata: {e}")
            raise
    
    async def get_session_anchors(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all anchor records for a session"""
        anchors = await self.anchors_collection.find(
            {"session_id": session_id}
        ).to_list(length=None)
        
        return anchors
    
    # async def get_session_payouts(self, session_id: str) -> List[Dict[str, Any]]:
    #     """Get all payout records for a session"""
    #     payouts = await self.payouts_collection.find(
    #         {"session_id": session_id}
    #     ).to_list(length=None)
    #     
    #     return payouts
    
    async def close(self):
        """Close blockchain clients"""
        await self.on_chain_client.close()
        logger.info("Blockchain anchor service closed")


class AnchorService:
    """
    Background service for On-System Chain anchor and TRON payout processing.
    
    REBUILT: Separates On-System Chain anchoring from TRON payments.
    """
    
    def __init__(self, anchor: BlockchainAnchor):
        self.anchor = anchor
        self.is_running = False
        self._anchor_task: Optional[asyncio.Task] = None
        self._payout_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start background processing"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start separate tasks for anchor and payout monitoring
        self._anchor_task = asyncio.create_task(self._anchor_monitoring_loop())
        # self._payout_task = asyncio.create_task(self._payout_monitoring_loop())
        
        logger.info("Anchor service started - On-System Chain + TRON payment monitoring")
    
    async def stop(self) -> None:
        """Stop background processing"""
        self.is_running = False
        
        # Cancel tasks
        tasks = [self._anchor_task, self._payout_task]
        for task in tasks:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("Anchor service stopped")
    
    async def _anchor_monitoring_loop(self) -> None:
        """Monitor On-System Chain anchor confirmations"""
        try:
            while self.is_running:
                await self.anchor.check_anchor_confirmations()
                await asyncio.sleep(30)  # Check every 30 seconds
                
        except asyncio.CancelledError:
            logger.info("Anchor monitoring cancelled")
        except Exception as e:
            logger.error(f"Anchor monitoring error: {e}")
            await asyncio.sleep(10)
            if self.is_running:
                await self._anchor_monitoring_loop()
    
    # async def _payout_monitoring_loop(self) -> None:
    #     """Monitor TRON payout confirmations"""
    #     try:
    #         while self.is_running:
    #             await self.anchor.check_payout_confirmations()
    #             await asyncio.sleep(60)  # Check every 60 seconds
    #             
    #     except asyncio.CancelledError:
    #         logger.info("Payout monitoring cancelled")
    #     except Exception as e:
    #         logger.error(f"Payout monitoring error: {e}")
    #         await asyncio.sleep(10)
    #         if self.is_running:
    #             await self._payout_monitoring_loop()
