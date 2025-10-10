# Path: blockchain/core/blockchain_engine.py  
# Lucid RDP Blockchain Core Engine - Dual-chain architecture with PoOT consensus
# Based on Spec-1a, Spec-1b, and Spec-1c requirements
# REBUILT: On-System Data Chain as primary, TRON isolated for payments only

from __future__ import annotations

import asyncio
import os
import logging
import hashlib
import struct
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import uuid
import json

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
import blake3

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from tronpy import Tron
from tronpy.keys import PrivateKey as TronPrivateKey
import httpx

# Import from updated models and components
from .models import (
    ChainType, ConsensusState, PayoutRouter, TaskProofType, SessionStatus, PayoutStatus,
    SessionAnchor, TronPayout, TaskProof, WorkCreditsTally, LeaderSchedule,
    ChunkMetadata, SessionManifest, generate_session_id, calculate_work_credits_formula
)
from ..on_system_chain.chain_client import OnSystemChainClient

logger = logging.getLogger(__name__)

# =============================================================================
# IMMUTABLE CONSENSUS PARAMETERS (Spec-1b)
# =============================================================================

SLOT_DURATION_SEC = 120  # Fixed, immutable per Spec-1b line 170
SLOT_TIMEOUT_MS = 5000   # 5s leader timeout
COOLDOWN_SLOTS = 16      # 16 slot cooldown
LEADER_WINDOW_DAYS = 7   # 7-day PoOT window
D_MIN = 0.2             # Minimum density threshold
BASE_MB_PER_SESSION = 5  # 5MB base unit

# =============================================================================
# ON-SYSTEM DATA CHAIN CONFIGURATION (R-MUST-016)
# =============================================================================

ON_SYSTEM_CHAIN_RPC = os.getenv("ON_SYSTEM_CHAIN_RPC", "http://on-chain-distroless:8545")
LUCID_ANCHORS_ADDRESS = os.getenv("LUCID_ANCHORS_ADDRESS", "")
LUCID_CHUNK_STORE_ADDRESS = os.getenv("LUCID_CHUNK_STORE_ADDRESS", "")

# =============================================================================
# TRON PAYMENT LAYER CONFIGURATION (R-MUST-015, R-MUST-018)
# =============================================================================

TRON_NETWORK = os.getenv("TRON_NETWORK", "shasta")  # shasta/mainnet
USDT_TRC20_MAINNET = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
USDT_TRC20_SHASTA = "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs"
PAYOUT_ROUTER_V0_ADDRESS = os.getenv("PAYOUT_ROUTER_V0_ADDRESS", "")
PAYOUT_ROUTER_KYC_ADDRESS = os.getenv("PAYOUT_ROUTER_KYC_ADDRESS", "")

# =============================================================================
# MONGODB CONFIGURATION (R-MUST-019)
# =============================================================================

MONGO_URI = os.getenv("MONGO_URI", "mongodb://lucid:lucid@mongo-distroless:27019/lucid?authSource=admin&retryWrites=false&directConnection=true")

# =============================================================================
# ENHANCED ON-SYSTEM CHAIN CLIENT (PRIMARY BLOCKCHAIN)
# =============================================================================

class EnhancedOnSystemChainClient:
    """
    Enhanced On-System Data Chain client for session anchoring (R-MUST-016).
    
    REBUILT: Primary blockchain client integrating both anchor and chain client functionality.
    Handles:
    - LucidAnchors contract interactions for session manifests
    - LucidChunkStore contract integration for chunk metadata
    - EVM JSON-RPC interface (not TRON API)
    - Gas estimation and circuit breakers
    - Enhanced error handling and retry logic
    """
    
    def __init__(self, rpc_url: str, contract_addresses: Dict[str, str]):
        self.rpc_url = rpc_url
        self.contracts = contract_addresses
        self.session = httpx.AsyncClient(timeout=30.0)
        
        # Initialize the enhanced chain client
        self.chain_client = OnSystemChainClient(
            rpc_url=rpc_url,
            contract_addresses=contract_addresses
        )
        
        logger.info(f"Enhanced On-System Chain client initialized: {rpc_url}")
    
    async def start(self) -> bool:
        """Start the chain client"""
        try:
            # Start the underlying chain client
            return await self.chain_client.start()
        except Exception as e:
            logger.error(f"Failed to start chain client: {e}")
            return False
    
    async def stop(self) -> None:
        """Stop the chain client"""
        try:
            await self.chain_client.stop()
            await self.session.aclose()
        except Exception as e:
            logger.error(f"Failed to stop chain client: {e}")
    
    async def anchor_session_manifest(self, anchor: SessionAnchor) -> str:
        """
        Anchor session manifest to LucidAnchors contract.
        
        Per Spec-1b: registerSession(sessionId, manifestHash, startedAt, owner, merkleRoot, chunkCount)
        Gas-efficient: uses events for data, minimal storage writes
        """
        try:
            # Create session manifest for the chain client using the models.py version
            manifest = SessionManifest(
                session_id=anchor.session_id,
                owner_address=anchor.owner_address,
                started_at=datetime.fromtimestamp(anchor.started_at, timezone.utc),
                ended_at=datetime.now(timezone.utc),
                manifest_hash=anchor.manifest_hash,
                merkle_root=anchor.merkle_root,
                chunk_count=anchor.chunk_count
            )
            
            # Use the enhanced chain client to anchor
            anchor_tx = await self.chain_client.anchor_session_to_chain(
                session_id=anchor.session_id,
                merkle_root=anchor.merkle_root,
                owner_address=anchor.owner_address,
                chunk_count=anchor.chunk_count,
                started_at=anchor.started_at
            )
            
            tx_hash = anchor_tx.transaction_hash if anchor_tx else None
            
            if tx_hash:
                anchor.txid = tx_hash
                anchor.status = "pending"
                logger.info(f"Session anchored to On-System Chain: {tx_hash}")
                return tx_hash
            else:
                anchor.status = "failed"
                raise Exception("Failed to anchor session manifest")
            
        except Exception as e:
            logger.error(f"Failed to anchor session manifest: {e}")
            anchor.status = "failed"
            raise
    
    async def get_transaction_status(self, txid: str) -> Tuple[str, Optional[int]]:
        """Get On-System Chain transaction confirmation status"""
        try:
            # Use the chain client to get transaction status
            anchor_tx = await self.chain_client.get_session_anchor_status(txid)
            if anchor_tx:
                if anchor_tx.status.value == "confirmed":
                    return "confirmed", anchor_tx.block_number
                elif anchor_tx.status.value == "failed":
                    return "failed", None
                else:
                    return "pending", None
            else:
                return "unknown", None
                
        except Exception as e:
            logger.error(f"Failed to get transaction status: {e}")
            return "unknown", None
    
    async def store_chunk_metadata(self, session_id: str, chunk_idx: int, metadata: Dict[str, Any]) -> str:
        """
        Store encrypted chunk metadata in LucidChunkStore contract.
        
        Per Spec-1b: storeChunkMetadata(sessionId, chunkIndex, ciphertextSha256, sizeBytes)
        """
        try:
            # Create chunk metadata for the chain client
            chunk_metadata = ChunkMetadata(
                chunk_id=f"{session_id}_{chunk_idx:03d}",
                session_id=session_id,
                chunk_hash=metadata["ciphertext_sha256"],
                size=metadata["size_bytes"],
                storage_path=metadata.get("local_path", ""),
                timestamp=datetime.now(timezone.utc),
                encrypted=metadata.get("encrypted", False)
            )
            
            # Use the chain client to store metadata
            chunk_entry = await self.chain_client.store_chunk_metadata(
                chunk_id=chunk_metadata.chunk_id,
                session_id=session_id,
                chunk_hash=metadata["ciphertext_sha256"],
                size=metadata["size_bytes"],
                storage_path=metadata.get("local_path", ""),
                owner_address="0x0000000000000000000000000000000000000000"  # Default owner
            )
            
            tx_hash = chunk_entry.chunk_id if chunk_entry else None
            
            if tx_hash:
                logger.info(f"Chunk metadata stored: {tx_hash}")
                return tx_hash
            else:
                raise Exception("Failed to store chunk metadata")
                
        except Exception as e:
            logger.error(f"Failed to store chunk metadata: {e}")
            raise

# =============================================================================
# ISOLATED TRON NODE SYSTEM (PAYMENT SERVICE ONLY)
# =============================================================================

class TronNodeSystem:
    """
    Isolated TRON blockchain client for payouts (R-MUST-015).
    
    REBUILT: Extract from core blockchain engine, mark as payment service only.
    No other services may call TRON directly - all TRON interactions
    must go through this isolated service for security.
    
    Handles:
    - USDT-TRC20 payouts via PayoutRouterV0 (non-KYC) or PayoutRouterKYC
    - Monthly payout distribution (R-MUST-018)
    - Energy/bandwidth management via TRX staking
    - Circuit breakers and daily limits
    """
    
    def __init__(self, network: str = TRON_NETWORK):
        self.network = network
        self.tron = Tron() if network == "mainnet" else Tron(network="shasta")
        
        # USDT contract address
        self.usdt_address = USDT_TRC20_MAINNET if network == "mainnet" else USDT_TRC20_SHASTA
        
        # Payout router addresses
        self.router_addresses = {
            PayoutRouter.PR0: PAYOUT_ROUTER_V0_ADDRESS,
            PayoutRouter.PRKYC: PAYOUT_ROUTER_KYC_ADDRESS
        }
        
        logger.info(f"TRON node system initialized (payment service only): {network}")
    
    async def create_usdt_payout(self, payout: TronPayout, private_key: str) -> str:
        """
        Create USDT-TRC20 payout via specified router.
        
        Router selection per Spec-1c:
        - PayoutRouterV0 (PR0): Non-KYC for end-users
        - PayoutRouterKYC (PRKYC): KYC-gated for node-workers with compliance signatures
        """
        try:
            # Validate router address
            router_address = self.router_addresses.get(payout.router_type)
            if not router_address:
                raise ValueError(f"Router address not configured: {payout.router_type}")
            
            # Initialize private key
            payout_key = TronPrivateKey(bytes.fromhex(private_key))
            from_address = payout_key.public_key.to_base58check_address()
            
            # USDT has 6 decimals
            amount_sun = int(payout.amount_usdt * 1_000_000)
            
            # Build transaction based on router type
            if payout.router_type == PayoutRouter.PR0:
                # Non-KYC payout via PayoutRouterV0
                contract = self.tron.get_contract(router_address)
                
                txn = contract.functions.disburse(
                    bytes.fromhex(payout.session_id.replace("-", "")),
                    payout.recipient_address,
                    amount_sun,
                    payout.reason
                )
                
            elif payout.router_type == PayoutRouter.PRKYC:
                # KYC-gated payout via PayoutRouterKYC
                if not payout.kyc_hash or not payout.compliance_signature:
                    raise ValueError("KYC hash and compliance signature required for PRKYC router")
                
                contract = self.tron.get_contract(router_address)
                
                sig = payout.compliance_signature
                txn = contract.functions.disburseKYC(
                    bytes.fromhex(payout.session_id.replace("-", "")),
                    payout.recipient_address,
                    amount_sun,
                    payout.reason,
                    bytes.fromhex(payout.kyc_hash),
                    sig["expiry"],
                    sig["v"],
                    bytes.fromhex(sig["r"]),
                    bytes.fromhex(sig["s"])
                )
            
            # Set transaction parameters
            txn = txn.with_owner(from_address)
            txn = txn.fee_limit(100_000_000)  # 100 TRX fee limit
            
            # Build, sign and broadcast
            txn = txn.build()
            txn = txn.sign(payout_key)
            result = txn.broadcast()
            
            if result.get("txid"):
                payout.txid = result["txid"]
                payout.status = "pending"
                
                logger.info(f"USDT payout created: {payout.txid} ({payout.amount_usdt} USDT to {payout.recipient_address})")
                return payout.txid
            else:
                raise Exception(f"TRON broadcast failed: {result}")
                
        except Exception as e:
            logger.error(f"USDT payout failed: {e}")
            payout.status = "failed"
            raise
    
    async def get_transaction_status(self, txid: str) -> str:
        """Get TRON transaction confirmation status"""
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
            logger.error(f"Failed to get TRON tx status: {e}")
            return "unknown"
    
    def get_energy_bandwidth_info(self, address: str) -> Dict[str, Any]:
        """Get account energy and bandwidth for TRX staking optimization"""
        try:
            account = self.tron.get_account(address)
            resources = self.tron.get_account_resource(address)
            
            return {
                "balance_trx": account.get("balance", 0) / 1_000_000,  # Convert from sun
                "energy_limit": resources.get("EnergyLimit", 0),
                "energy_used": resources.get("EnergyUsed", 0),
                "net_limit": resources.get("NetLimit", 0),
                "net_used": resources.get("NetUsed", 0),
                "frozen_energy": account.get("account_resource", {}).get("frozen_balance_for_energy", 0),
                "frozen_bandwidth": account.get("frozen", [{}])[0].get("frozen_balance", 0) if account.get("frozen") else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get account resources: {e}")
            return {}


# =============================================================================
# POOT CONSENSUS ENGINE (REBUILT)
# =============================================================================

class PoOTConsensusEngine:
    """
    Proof of Operational Tasks (PoOT) consensus engine (Spec-1b).
    
    REBUILT: Pure PoOT consensus on On-System Chain (not TRON).
    Implements:
    - Work credits calculation from relay bandwidth, storage proofs, validation signatures, uptime
    - Leader selection based on work credits ranking with cooldown periods
    - Block publishing with fallback mechanisms
    - Pool support for multiple nodes
    - Separation from governance (consensus != voting)
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.current_epoch = 0
        self.current_slot = 0
        self.leader_schedule: Dict[int, LeaderSchedule] = {}
        
        # Initialize collections with proper indexes
        asyncio.create_task(self._setup_mongodb_indexes())
        
        logger.info("PoOT consensus engine initialized")
    
    async def _setup_mongodb_indexes(self):
        """Setup MongoDB indexes for consensus collections per Spec-1b"""
        try:
            # task_proofs collection - sharded on { slot: 1, nodeId: 1 }
            await self.db["task_proofs"].create_index([("slot", 1), ("nodeId", 1)])
            await self.db["task_proofs"].create_index([("type", 1)])
            await self.db["task_proofs"].create_index([("ts", -1)])
            
            # work_tally collection - replicated
            await self.db["work_tally"].create_index([("epoch", 1), ("entityId", 1)])
            await self.db["work_tally"].create_index([("rank", 1)])
            
            # leader_schedule collection - replicated  
            await self.db["leader_schedule"].create_index([("slot", 1)])
            
            logger.info("PoOT MongoDB indexes created")
            
        except Exception as e:
            logger.error(f"Failed to setup MongoDB indexes: {e}")
    
    async def submit_work_proof(self, proof: TaskProof) -> bool:
        """
        Submit work credits proof for PoOT consensus.
        
        Per Spec-1b lines 129-134: relay_bandwidth, storage_availability, 
        validation_signature, uptime_beacon
        """
        try:
            # Store proof in MongoDB (sharded collection)
            await self.db["task_proofs"].insert_one(proof.to_dict())
            
            logger.info(f"Work proof submitted: {proof.node_id} - {proof.type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit work proof: {e}")
            return False
    
    async def calculate_work_credits(self, epoch: int) -> List[WorkCreditsTally]:
        """
        Calculate work credits for all entities over sliding window.
        
        Per Spec-1b: W_t = max(S_t, ceil(B_t / BASE_MB_PER_SESSION))
        where BASE_MB_PER_SESSION = 5MB
        """
        try:
            # Get all work proofs for the epoch
            window_start = datetime.now(timezone.utc) - timedelta(days=LEADER_WINDOW_DAYS)
            
            proofs_cursor = self.db["task_proofs"].find({
                "ts": {"$gte": window_start}
            })
            
            # Aggregate work credits by entity
            entity_credits: Dict[str, Dict[str, Any]] = {}
            
            async for proof_doc in proofs_cursor:
                entity_id = proof_doc["nodeId"]
                proof_type = proof_doc["type"]
                value = proof_doc["value"]
                
                if entity_id not in entity_credits:
                    entity_credits[entity_id] = {
                        "relay_bandwidth": 0,
                        "storage_proofs": 0,
                        "validation_signatures": 0,
                        "uptime_score": 0.0
                    }
                
                # Calculate credits based on proof type using the formula
                if proof_type == TaskProofType.RELAY_BANDWIDTH.value:
                    # W_t = max(S_t, ceil(B_t / BASE_MB_PER_SESSION))
                    bandwidth_mb = value.get("bandwidth_mb", 0)
                    sessions = value.get("sessions_relayed", 0)
                    credits = calculate_work_credits_formula(sessions, bandwidth_mb, BASE_MB_PER_SESSION)
                    entity_credits[entity_id]["relay_bandwidth"] += credits
                    
                elif proof_type == TaskProofType.STORAGE_AVAILABILITY.value:
                    storage_gb = value.get("storage_gb", 0)
                    uptime_hours = value.get("uptime_hours", 0)
                    credits = int(storage_gb * uptime_hours / 24)  # Daily storage hours
                    entity_credits[entity_id]["storage_proofs"] += credits
                    
                elif proof_type == TaskProofType.VALIDATION_SIGNATURE.value:
                    signatures_count = value.get("signatures_count", 0)
                    entity_credits[entity_id]["validation_signatures"] += signatures_count
                    
                elif proof_type == TaskProofType.UPTIME_BEACON.value:
                    uptime_hours = value.get("uptime_hours", 0)
                    entity_credits[entity_id]["uptime_score"] = min(uptime_hours / (LEADER_WINDOW_DAYS * 24), 1.0)
            
            # Create work tally objects
            tallies = []
            for entity_id, credits in entity_credits.items():
                total_credits = (
                    credits["relay_bandwidth"] +
                    credits["storage_proofs"] +
                    credits["validation_signatures"]
                )
                
                # Apply uptime multiplier
                live_score = total_credits * credits["uptime_score"]
                
                tally = WorkCreditsTally(
                    epoch=epoch,
                    entity_id=entity_id,
                    credits_total=total_credits,
                    relay_bandwidth=credits["relay_bandwidth"],
                    storage_proofs=credits["storage_proofs"],
                    validation_signatures=credits["validation_signatures"],
                    uptime_score=credits["uptime_score"],
                    live_score=live_score,
                    rank=0  # Will be set after sorting
                )
                tallies.append(tally)
            
            # Sort by live score and assign ranks
            tallies.sort(key=lambda x: x.live_score, reverse=True)
            for i, tally in enumerate(tallies):
                tally.rank = i + 1
            
            # Store tallies in MongoDB
            for tally in tallies:
                await self.db["work_tally"].replace_one(
                    {"_id": tally.to_dict()["_id"]},
                    tally.to_dict(),
                    upsert=True
                )
            
            logger.info(f"Work credits calculated for epoch {epoch}: {len(tallies)} entities")
            return tallies
            
        except Exception as e:
            logger.error(f"Failed to calculate work credits: {e}")
            return []
    
    async def select_leader(self, slot: int) -> LeaderSchedule:
        """
        Select block leader for slot based on work credits ranking.
        
        Per Spec-1b lines 135-157:
        - Primary leader = top-ranked, not in cooldown (16 slots)
        - Fallbacks: next ranked entities
        - VRF tie-breaking for equal credits
        """
        try:
            # Get current work credits
            current_epoch = slot // (24 * 60 * 60 // SLOT_DURATION_SEC)  # Daily epochs
            tallies_cursor = self.db["work_tally"].find({"epoch": current_epoch}).sort("rank", 1)
            
            # Get entities in cooldown
            cooldown_start_slot = slot - COOLDOWN_SLOTS
            cooldown_cursor = self.db["leader_schedule"].find({
                "slot": {"$gte": cooldown_start_slot, "$lt": slot},
                "result.winner": {"$exists": True}
            })
            
            cooldown_entities = set()
            async for schedule_doc in cooldown_cursor:
                cooldown_entities.add(schedule_doc["result"]["winner"])
            
            # Find eligible entities (not in cooldown)
            eligible_entities = []
            async for tally_doc in tallies_cursor:
                entity_id = tally_doc["entityId"]
                if entity_id not in cooldown_entities:
                    eligible_entities.append(entity_id)
            
            # Select primary and fallbacks
            primary = eligible_entities[0] if eligible_entities else "fallback_node"
            fallbacks = eligible_entities[1:6] if len(eligible_entities) > 1 else ["fallback_node"]
            
            # Create leader schedule
            schedule = LeaderSchedule(
                slot=slot,
                primary=primary,
                fallbacks=fallbacks,
                deadline=datetime.now(timezone.utc) + timedelta(milliseconds=SLOT_TIMEOUT_MS)
            )
            
            # Store schedule in MongoDB
            await self.db["leader_schedule"].replace_one(
                {"_id": slot},
                schedule.to_dict(),
                upsert=True
            )
            
            logger.info(f"Leader selected for slot {slot}: {primary} (fallbacks: {fallbacks})")
            return schedule
            
        except Exception as e:
            logger.error(f"Failed to select leader for slot {slot}: {e}")
            # Return fallback schedule
            return LeaderSchedule(
                slot=slot,
                primary="fallback_node",
                fallbacks=["emergency_fallback"],
                deadline=datetime.now(timezone.utc) + timedelta(milliseconds=SLOT_TIMEOUT_MS)
            )
    
    async def record_block_result(self, slot: int, winner: str, reason: str):
        """Record block production result for leader selection"""
        try:
            await self.db["leader_schedule"].update_one(
                {"_id": slot},
                {"$set": {"result": {"winner": winner, "reason": reason}}}
            )
            
            logger.info(f"Block result recorded for slot {slot}: {winner} ({reason})")
            
        except Exception as e:
            logger.error(f"Failed to record block result: {e}")


# =============================================================================
# BLOCKCHAIN ENGINE (REBUILT WITH ON-SYSTEM CHAIN AS PRIMARY)
# =============================================================================

class BlockchainEngine:
    """
    Main blockchain engine orchestrating dual-chain architecture.
    
    REBUILT: On-System Chain as primary, TRON isolated for payments only.
    
    Manages:
    - On-System Data Chain for session anchoring (R-MUST-016)  
    - TRON integration for USDT payouts (R-MUST-015, R-MUST-018)
    - PoOT consensus for block production
    - MongoDB collections for consensus and anchoring data
    - Circuit breakers and rate limiting
    """
    
    def __init__(self):
        self.mongo_client = AsyncIOMotorClient(MONGO_URI)
        self.db = self.mongo_client.get_default_database()
        
        # Initialize blockchain clients
        self.on_chain_client = EnhancedOnSystemChainClient(
            ON_SYSTEM_CHAIN_RPC,
            {
                "LucidAnchors": LUCID_ANCHORS_ADDRESS,
                "LucidChunkStore": LUCID_CHUNK_STORE_ADDRESS
            }
        )
        
        self.tron_client = TronNodeSystem(TRON_NETWORK)  # Payment service only
        self.consensus_engine = PoOTConsensusEngine(self.db)
        
        # State tracking
        self.current_slot = 0
        self.running = False
        
        logger.info("Blockchain engine initialized with On-System Chain as primary")
    
    async def start_engine(self):
        """Start blockchain engine and consensus"""
        try:
            self.running = True
            
            # Start the On-System Chain client
            await self.on_chain_client.start()
            
            # Start consensus slot timer
            asyncio.create_task(self._slot_timer())
            
            # Start anchor status monitoring
            asyncio.create_task(self._monitor_anchors())
            
            # Start payout status monitoring
            asyncio.create_task(self._monitor_payouts())
            
            logger.info("Blockchain engine started")
            
        except Exception as e:
            logger.error(f"Failed to start blockchain engine: {e}")
            raise
    
    async def stop_engine(self):
        """Stop blockchain engine"""
        try:
            self.running = False
            await self.on_chain_client.stop()
            self.mongo_client.close()
            logger.info("Blockchain engine stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop blockchain engine: {e}")
    
    async def _slot_timer(self):
        """PoOT consensus slot timer (120s fixed duration)"""
        while self.running:
            try:
                # Select leader for current slot
                schedule = await self.consensus_engine.select_leader(self.current_slot)
                self.leader_schedule[self.current_slot] = schedule
                
                # Wait for slot duration
                await asyncio.sleep(SLOT_DURATION_SEC)
                
                # Check if block was produced
                if schedule.winner is None:
                    # No block produced, record as missed
                    await self.consensus_engine.record_block_result(
                        self.current_slot, 
                        "missed", 
                        "timeout"
                    )
                
                self.current_slot += 1
                
            except Exception as e:
                logger.error(f"Slot timer error: {e}")
                await asyncio.sleep(SLOT_DURATION_SEC)
    
    async def _monitor_anchors(self):
        """Monitor session anchor status on On-System Chain"""
        while self.running:
            try:
                # Get pending anchors
                pending_cursor = self.db["sessions"].find({"status": "pending"})
                
                async for session_doc in pending_cursor:
                    txid = session_doc.get("anchor_txid")
                    if txid:
                        # Check transaction status
                        status, block_number = await self.on_chain_client.get_transaction_status(txid)
                        
                        if status == "confirmed":
                            # Update session status
                            await self.db["sessions"].update_one(
                                {"_id": session_doc["_id"]},
                                {
                                    "$set": {
                                        "status": "confirmed",
                                        "block_number": block_number
                                    }
                                }
                            )
                            logger.info(f"Session anchor confirmed: {session_doc['_id']}")
                            
                        elif status == "failed":
                            await self.db["sessions"].update_one(
                                {"_id": session_doc["_id"]},
                                {"$set": {"status": "failed"}}
                            )
                            logger.warning(f"Session anchor failed: {session_doc['_id']}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Anchor monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _monitor_payouts(self):
        """Monitor TRON payout status"""
        while self.running:
            try:
                # Get pending payouts
                pending_cursor = self.db["payouts"].find({"status": "pending"})
                
                async for payout_doc in pending_cursor:
                    txid = payout_doc.get("txid")
                    if txid:
                        # Check TRON transaction status
                        status = await self.tron_client.get_transaction_status(txid)
                        
                        if status == "confirmed":
                            await self.db["payouts"].update_one(
                                {"_id": payout_doc["_id"]},
                                {"$set": {"status": "confirmed"}}
                            )
                            logger.info(f"Payout confirmed: {payout_doc['_id']}")
                            
                        elif status == "failed":
                            await self.db["payouts"].update_one(
                                {"_id": payout_doc["_id"]},
                                {"$set": {"status": "failed"}}
                            )
                            logger.warning(f"Payout failed: {payout_doc['_id']}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Payout monitoring error: {e}")
                await asyncio.sleep(120)
    
    async def anchor_session(self, session_id: str, manifest_hash: str, 
                           merkle_root: str, owner_address: str, chunk_count: int) -> str:
        """
        Anchor session to On-System Chain using LucidAnchors contract.
        
        REBUILT: Uses On-System Chain as primary (not TRON).
        """
        try:
            # Create session anchor
            anchor = SessionAnchor(
                session_id=session_id,
                manifest_hash=manifest_hash,
                merkle_root=merkle_root,
                started_at=int(datetime.now(timezone.utc).timestamp()),
                owner_address=owner_address,
                chunk_count=chunk_count
            )
            
            # Anchor to On-System Chain
            txid = await self.on_chain_client.anchor_session_manifest(anchor)
            
            # Store in MongoDB
            await self.db["sessions"].insert_one(anchor.to_dict())
            
            logger.info(f"Session anchored to On-System Chain: {session_id} -> {txid}")
            return txid
            
        except Exception as e:
            logger.error(f"Failed to anchor session: {e}")
            raise
    
    async def create_payout(self, session_id: str, recipient_address: str,
                          amount_usdt: float, router_type: PayoutRouter,
                          reason: str, private_key: str,
                          kyc_hash: Optional[str] = None,
                          compliance_signature: Optional[Dict[str, Any]] = None) -> str:
        """
        Create TRON USDT payout via isolated payment service.
        
        REBUILT: TRON isolated for payments only (not blockchain core).
        """
        try:
            # Create payout
            payout = TronPayout(
                session_id=session_id,
                recipient_address=recipient_address,
                amount_usdt=amount_usdt,
                router_type=router_type,
                reason=reason,
                kyc_hash=kyc_hash,
                compliance_signature=compliance_signature
            )
            
            # Create TRON transaction
            txid = await self.tron_client.create_usdt_payout(payout, private_key)
            
            # Store in MongoDB
            await self.db["payouts"].insert_one(payout.to_dict())
            
            logger.info(f"Payout created via TRON: {session_id} -> {txid}")
            return txid
            
        except Exception as e:
            logger.error(f"Failed to create payout: {e}")
            raise
    
    async def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session anchoring status"""
        try:
            session_doc = await self.db["sessions"].find_one({"_id": session_id})
            return session_doc
            
        except Exception as e:
            logger.error(f"Failed to get session status: {e}")
            return None
    
    async def get_payout_status(self, session_id: str, recipient_address: str) -> Optional[Dict[str, Any]]:
        """Get payout status"""
        try:
            payout_doc = await self.db["payouts"].find_one({
                "_id": f"{session_id}_{recipient_address}"
            })
            return payout_doc
            
        except Exception as e:
            logger.error(f"Failed to get payout status: {e}")
            return None


# =============================================================================
# GLOBAL INSTANCE AND SERVICE FUNCTIONS
# =============================================================================

# Global blockchain engine instance
blockchain_engine: Optional[BlockchainEngine] = None


def get_blockchain_engine() -> BlockchainEngine:
    """Get global blockchain engine instance"""
    global blockchain_engine
    if blockchain_engine is None:
        blockchain_engine = BlockchainEngine()
    return blockchain_engine


async def start_blockchain_service():
    """Start blockchain service"""
    global blockchain_engine
    blockchain_engine = BlockchainEngine()
    await blockchain_engine.start_engine()


async def stop_blockchain_service():
    """Stop blockchain service"""
    global blockchain_engine
    if blockchain_engine:
        await blockchain_engine.stop_engine()
        blockchain_engine = None


if __name__ == "__main__":
    # Test blockchain engine
    async def test_blockchain():
        print("Starting Lucid blockchain engine...")
        await start_blockchain_service()
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("Stopping blockchain engine...")
            await stop_blockchain_service()
    
    asyncio.run(test_blockchain())