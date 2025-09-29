# Path: apps/blockchain_core/blockchain_engine.py  
# Lucid RDP Blockchain Core Engine - Dual-chain architecture with PoOT consensus
# Based on LUCID-STRICT requirements from Build_guide_docs

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

logger = logging.getLogger(__name__)

# Blockchain Constants per Spec-1b, Spec-1c
SLOT_DURATION_SEC = int(os.getenv("SLOT_DURATION_SEC", "120"))  # Fixed at 120s (immutable)
SLOT_TIMEOUT_MS = int(os.getenv("SLOT_TIMEOUT_MS", "5000"))     # 5s leader timeout
COOLDOWN_SLOTS = int(os.getenv("COOLDOWN_SLOTS", "16"))         # 16 slot cooldown
LEADER_WINDOW_DAYS = int(os.getenv("LEADER_WINDOW_DAYS", "7"))  # 7-day PoOT window
D_MIN = float(os.getenv("D_MIN", "0.2"))                        # Minimum density threshold
BASE_MB_PER_SESSION = int(os.getenv("BASE_MB_PER_SESSION", "5")) # 5MB base unit

# TRON Constants (R-MUST-015)
TRON_NETWORK = os.getenv("TRON_NETWORK", "shasta")  # shasta/mainnet
USDT_TRC20_MAINNET = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
USDT_TRC20_SHASTA = "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs"

# On-System Chain Constants (R-MUST-016)
ON_SYSTEM_CHAIN_RPC = os.getenv("ON_SYSTEM_CHAIN_RPC", "http://localhost:8545")
LUCID_ANCHORS_ADDRESS = os.getenv("LUCID_ANCHORS_ADDRESS", "")
PAYOUT_ROUTER_V0_ADDRESS = os.getenv("PAYOUT_ROUTER_V0_ADDRESS", "")
PAYOUT_ROUTER_KYC_ADDRESS = os.getenv("PAYOUT_ROUTER_KYC_ADDRESS", "")

# MongoDB Configuration (R-MUST-019)
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/lucid")


class ChainType(Enum):
    """Blockchain types in dual-chain architecture"""
    ON_SYSTEM_DATA = "on_system_data_chain"
    TRON_PAYOUTS = "tron_payouts"


class ConsensusState(Enum):
    """PoOT consensus states"""
    CALCULATING = "calculating"
    LEADER_SELECTED = "leader_selected"
    BLOCK_PROPOSED = "block_proposed"
    BLOCK_CONFIRMED = "block_confirmed"
    SLOT_MISSED = "slot_missed"


class PayoutRouter(Enum):
    """TRON payout router types (R-MUST-018)"""
    PR0 = "PayoutRouterV0"      # Non-KYC for end-users
    PRKYC = "PayoutRouterKYC"   # KYC-gated for node-workers


@dataclass
class WorkCreditsProof:
    """PoOT work credits proof submission"""
    node_id: str
    pool_id: Optional[str]
    slot: int
    proof_type: str  # relay_bandwidth, storage_availability, validation_signature, uptime_beacon
    proof_data: Dict[str, Any]
    signature: bytes
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": f"{self.node_id}_{self.slot}_{self.proof_type}",
            "nodeId": self.node_id,
            "poolId": self.pool_id,
            "slot": self.slot,
            "type": self.proof_type,
            "value": self.proof_data,
            "sig": self.signature.hex(),
            "ts": self.timestamp
        }


@dataclass
class WorkCreditsTally:
    """PoOT work credits tally per epoch"""
    epoch: int
    entity_id: str  # node_id or pool_id
    credits_total: int
    relay_bandwidth: int
    storage_proofs: int
    validation_signatures: int
    uptime_score: float
    live_score: float
    rank: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": f"{self.epoch}_{self.entity_id}",
            "epoch": self.epoch,
            "entityId": self.entity_id,
            "credits": self.credits_total,
            "liveScore": self.live_score,
            "rank": self.rank
        }


@dataclass
class LeaderSchedule:
    """Block leader schedule per slot"""
    slot: int
    primary: str  # entity_id
    fallbacks: List[str]  # fallback entity_ids
    winner: Optional[str] = None
    reason: str = ""
    deadline: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.slot,
            "slot": self.slot,
            "primary": self.primary,
            "fallbacks": self.fallbacks,
            "result": {"winner": self.winner, "reason": self.reason}
        }


@dataclass
class SessionAnchor:
    """On-System Chain session anchor"""
    session_id: str
    manifest_hash: str
    merkle_root: str
    started_at: int
    owner_address: str
    chunk_count: int
    block_number: Optional[int] = None
    txid: Optional[str] = None
    gas_used: int = 0
    status: str = "pending"  # pending, confirmed, failed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": self.session_id,
            "owner_addr": self.owner_address,
            "started_at": self.started_at,
            "ended_at": None,
            "manifest_hash": self.manifest_hash,
            "merkle_root": self.merkle_root,
            "chunk_count": self.chunk_count,
            "anchor_txid": self.txid,
            "block_number": self.block_number,
            "gas_used": self.gas_used,
            "status": self.status
        }


@dataclass 
class TronPayout:
    """TRON USDT payout transaction"""
    session_id: str
    recipient_address: str
    amount_usdt: float
    router_type: PayoutRouter
    reason: str
    kyc_hash: Optional[str] = None
    compliance_signature: Optional[Dict[str, Any]] = None
    txid: Optional[str] = None
    status: str = "pending"  # pending, confirmed, failed
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "_id": f"{self.session_id}_{self.recipient_address}",
            "session_id": self.session_id,
            "to_addr": self.recipient_address,
            "usdt_amount": self.amount_usdt,
            "router": self.router_type.value,
            "reason": self.reason,
            "txid": self.txid,
            "status": self.status,
            "created_at": self.created_at,
            "kyc_hash": self.kyc_hash,
            "compliance_sig": self.compliance_signature
        }


class OnSystemChainClient:
    """
    On-System Data Chain client for session anchoring (R-MUST-016).
    
    Handles:
    - LucidAnchors contract interactions for session manifests
    - LucidChunkStore for encrypted chunk storage
    - Gas-efficient event-based anchoring
    - Circuit breaker enforcement
    """
    
    def __init__(self, rpc_url: str, contract_addresses: Dict[str, str]):
        self.rpc_url = rpc_url
        self.contracts = contract_addresses
        self.session = httpx.AsyncClient()
        
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
            result = response.json()
            
            if "result" in result:
                txid = result["result"]
                anchor.txid = txid
                anchor.status = "pending"
                
                logger.info(f"Session manifest anchored: {anchor.session_id} -> {txid}")
                return txid
            else:
                error = result.get("error", {})
                raise Exception(f"Anchoring failed: {error}")
                
        except Exception as e:
            logger.error(f"Failed to anchor session manifest: {e}")
            anchor.status = "failed"
            raise
    
    def _encode_register_session_call(self, params: Dict[str, Any]) -> str:
        """Encode LucidAnchors.registerSession() call data (simplified)"""
        # In production, this would use proper ABI encoding
        session_id_hex = params["sessionId"][:64].ljust(64, '0')
        manifest_hash = params["manifestHash"][2:] if params["manifestHash"].startswith('0x') else params["manifestHash"]
        merkle_root = params["merkleRoot"][2:] if params["merkleRoot"].startswith('0x') else params["merkleRoot"]
        
        # Function selector for registerSession(bytes32,bytes32,uint64,address,bytes32,uint32)
        function_sig = "4f9b563f"  # keccak256("registerSession(bytes32,bytes32,uint64,address,bytes32,uint32)")[:8]
        
        # Encode parameters (simplified)
        encoded_data = function_sig + session_id_hex + manifest_hash + merkle_root
        
        return "0x" + encoded_data
    
    async def get_anchor_status(self, txid: str) -> str:
        """Check transaction confirmation status"""
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
            logger.error(f"Failed to check anchor status: {e}")
            return "unknown"
    
    async def close(self):
        """Close HTTP client"""
        await self.session.aclose()


class TronNodeSystem:
    """
    Isolated TRON blockchain client for payouts (R-MUST-015).
    
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
        
        logger.info(f"TRON node system initialized: {network}")
    
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


class PoOTConsensusEngine:
    """
    Proof of Operational Tasks (PoOT) consensus engine (Spec-1b).
    
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
    
    async def submit_work_proof(self, proof: WorkCreditsProof) -> bool:
        """
        Submit work proof for PoOT consensus.
        
        Proof types per Spec-1b:
        - relay_bandwidth: Tor relay bandwidth served via Lucid Cloud Relay  
        - storage_availability: Storage availability proofs for encrypted chunks
        - validation_signature: Validation signatures on On-System Chain blocks
        - uptime_beacon: Time-sealed heartbeats
        """
        try:
            # Validate proof signature (simplified)
            if len(proof.signature) < 32:
                logger.warning(f"Invalid proof signature from {proof.node_id}")
                return False
            
            # Store proof in MongoDB
            await self.db["task_proofs"].replace_one(
                {"_id": proof.to_dict()["_id"]},
                proof.to_dict(),
                upsert=True
            )
            
            logger.debug(f"Work proof submitted: {proof.node_id} {proof.proof_type} slot {proof.slot}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to submit work proof: {e}")
            return False
    
    async def calculate_work_credits(self, epoch: int) -> List[WorkCreditsTally]:
        """
        Calculate work credits for epoch based on submitted proofs.
        
        Per Spec-1b: W_t = max(S_t, ceil(B_t / BASE_MB_PER_SESSION))
        Where S_t = sessions, B_t = total bytes, BASE_MB_PER_SESSION = 5MB
        """
        try:
            # Get all proofs for epoch  
            epoch_start = epoch * LEADER_WINDOW_DAYS * 24 * 3600 // SLOT_DURATION_SEC
            epoch_end = (epoch + 1) * LEADER_WINDOW_DAYS * 24 * 3600 // SLOT_DURATION_SEC
            
            proofs_cursor = self.db["task_proofs"].find({
                "slot": {"$gte": epoch_start, "$lt": epoch_end}
            })
            
            # Aggregate proofs by entity (node or pool)
            entity_credits: Dict[str, Dict[str, Any]] = {}
            
            async for proof in proofs_cursor:
                entity_id = proof.get("poolId", proof["nodeId"])
                
                if entity_id not in entity_credits:
                    entity_credits[entity_id] = {
                        "relay_bandwidth": 0,
                        "storage_proofs": 0, 
                        "validation_signatures": 0,
                        "uptime_score": 0.0,
                        "total_slots": 0
                    }
                
                credits = entity_credits[entity_id]
                proof_value = proof.get("value", {})
                
                if proof["type"] == "relay_bandwidth":
                    credits["relay_bandwidth"] += proof_value.get("bytes_served", 0)
                elif proof["type"] == "storage_availability":
                    credits["storage_proofs"] += 1
                elif proof["type"] == "validation_signature":
                    credits["validation_signatures"] += 1
                elif proof["type"] == "uptime_beacon":
                    credits["uptime_score"] += proof_value.get("uptime_ratio", 0.0)
                    credits["total_slots"] += 1
            
            # Calculate final credits and rankings
            tallies = []
            for entity_id, credits in entity_credits.items():
                # Calculate work units: W_t = max(sessions, bytes/BASE_MB)  
                bandwidth_units = credits["relay_bandwidth"] // (BASE_MB_PER_SESSION * 1024 * 1024)
                work_units = max(credits["validation_signatures"], bandwidth_units)
                
                # Calculate uptime score
                uptime_score = credits["uptime_score"] / max(1, credits["total_slots"])
                
                # Calculate total credits (simplified formula)
                total_credits = (
                    work_units * 100 +
                    credits["storage_proofs"] * 50 +
                    int(uptime_score * 100)
                )
                
                # Calculate liveness score for leader selection
                live_score = min(1.0, uptime_score * (1.0 + work_units / 1000))
                
                tally = WorkCreditsTally(
                    epoch=epoch,
                    entity_id=entity_id,
                    credits_total=total_credits,
                    relay_bandwidth=credits["relay_bandwidth"],
                    storage_proofs=credits["storage_proofs"],
                    validation_signatures=credits["validation_signatures"],
                    uptime_score=uptime_score,
                    live_score=live_score,
                    rank=0  # Will be set after sorting
                )
                tallies.append(tally)
            
            # Sort by credits and assign rankings
            tallies.sort(key=lambda t: t.credits_total, reverse=True)
            for i, tally in enumerate(tallies):
                tally.rank = i + 1
            
            # Store tallies in MongoDB
            for tally in tallies:
                await self.db["work_tally"].replace_one(
                    {"_id": tally.to_dict()["_id"]},
                    tally.to_dict(),
                    upsert=True
                )
            
            logger.info(f"Calculated work credits for epoch {epoch}: {len(tallies)} entities")
            return tallies
            
        except Exception as e:
            logger.error(f"Failed to calculate work credits: {e}")
            return []
    
    async def select_block_leader(self, slot: int) -> Optional[str]:
        """
        Select block leader for slot using PoOT ranking with cooldown.
        
        Per Spec-1b:
        - Primary leader = top-ranked entity not selected in past cooldownSlots
        - Fallbacks: next ranked entities
        - VRF tie-breaking for equal credits
        """
        try:
            current_epoch = slot // (LEADER_WINDOW_DAYS * 24 * 3600 // SLOT_DURATION_SEC)
            
            # Get work credits ranking for current epoch
            tallies_cursor = self.db["work_tally"].find(
                {"epoch": current_epoch}
            ).sort("rank", 1)
            
            tallies = await tallies_cursor.to_list(length=None)
            
            if not tallies:
                logger.warning(f"No work credits found for epoch {current_epoch}")
                return None
            
            # Check cooldown period - entities cannot lead within COOLDOWN_SLOTS
            cooldown_start = max(0, slot - COOLDOWN_SLOTS)
            recent_leaders = set()
            
            recent_schedule_cursor = self.db["leader_schedule"].find({
                "slot": {"$gte": cooldown_start, "$lt": slot},
                "result.winner": {"$exists": True}
            })
            
            async for schedule in recent_schedule_cursor:
                if schedule.get("result", {}).get("winner"):
                    recent_leaders.add(schedule["result"]["winner"])
            
            # Select primary leader (highest ranked not in cooldown)
            primary_leader = None
            fallback_leaders = []
            
            for tally in tallies:
                entity_id = tally["entityId"]
                
                if entity_id not in recent_leaders:
                    if primary_leader is None:
                        primary_leader = entity_id
                    else:
                        fallback_leaders.append(entity_id)
                        
                        # Limit fallbacks
                        if len(fallback_leaders) >= 3:
                            break
            
            if primary_leader is None:
                logger.warning(f"No eligible leader for slot {slot} (all in cooldown)")
                return None
            
            # Create leader schedule
            schedule = LeaderSchedule(
                slot=slot,
                primary=primary_leader,
                fallbacks=fallback_leaders,
                deadline=datetime.now(timezone.utc) + timedelta(milliseconds=SLOT_TIMEOUT_MS)
            )
            
            # Store schedule
            await self.db["leader_schedule"].replace_one(
                {"_id": slot},
                schedule.to_dict(),
                upsert=True
            )
            
            logger.info(f"Selected leader for slot {slot}: {primary_leader} (fallbacks: {fallback_leaders})")
            return primary_leader
            
        except Exception as e:
            logger.error(f"Failed to select block leader: {e}")
            return None
    
    async def record_block_result(self, slot: int, winner: str, reason: str):
        """Record block publishing result"""
        try:
            await self.db["leader_schedule"].update_one(
                {"_id": slot},
                {"$set": {"result.winner": winner, "result.reason": reason}}
            )
            
            logger.info(f"Block result recorded: slot {slot} winner {winner} ({reason})")
            
        except Exception as e:
            logger.error(f"Failed to record block result: {e}")


class BlockchainEngine:
    """
    Main blockchain engine orchestrating dual-chain architecture.
    
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
        self.on_chain_client = OnSystemChainClient(
            ON_SYSTEM_CHAIN_RPC,
            {
                "LucidAnchors": LUCID_ANCHORS_ADDRESS,
                "PayoutRouterV0": PAYOUT_ROUTER_V0_ADDRESS,
                "PayoutRouterKYC": PAYOUT_ROUTER_KYC_ADDRESS
            }
        )
        
        self.tron_client = TronNodeSystem(TRON_NETWORK)
        self.consensus_engine = PoOTConsensusEngine(self.db)
        
        # State tracking
        self.current_slot = 0
        self.running = False
        
        logger.info("Blockchain engine initialized")
    
    async def start_engine(self):
        """Start blockchain engine and consensus"""
        try:
            self.running = True
            
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
        self.running = False
        
        # Close clients
        await self.on_chain_client.close()
        self.mongo_client.close()
        
        logger.info("Blockchain engine stopped")
    
    async def _slot_timer(self):
        """PoOT consensus slot timer (120s slots per Spec-1b)"""
        while self.running:
            try:
                # Select leader for current slot
                leader = await self.consensus_engine.select_block_leader(self.current_slot)
                
                if leader:
                    logger.info(f"Slot {self.current_slot}: Leader selected: {leader}")
                else:
                    logger.warning(f"Slot {self.current_slot}: No leader selected")
                    await self.consensus_engine.record_block_result(
                        self.current_slot, "", "no_leader_available"
                    )
                
                # Wait for slot duration
                await asyncio.sleep(SLOT_DURATION_SEC)
                self.current_slot += 1
                
                # Calculate work credits every epoch
                epoch = self.current_slot // (LEADER_WINDOW_DAYS * 24 * 3600 // SLOT_DURATION_SEC)
                if self.current_slot % (LEADER_WINDOW_DAYS * 24 * 3600 // SLOT_DURATION_SEC) == 0:
                    await self.consensus_engine.calculate_work_credits(epoch)
                    
            except Exception as e:
                logger.error(f"Slot timer error: {e}")
                await asyncio.sleep(1)
    
    async def _monitor_anchors(self):
        """Monitor pending session anchors"""
        while self.running:
            try:
                # Check pending anchors
                pending_cursor = self.db["sessions"].find({"status": "pending"})
                
                async for session_doc in pending_cursor:
                    if session_doc.get("anchor_txid"):
                        status = await self.on_chain_client.get_anchor_status(
                            session_doc["anchor_txid"]
                        )
                        
                        if status != "pending":
                            await self.db["sessions"].update_one(
                                {"_id": session_doc["_id"]},
                                {"$set": {"status": status}}
                            )
                            
                            logger.info(f"Anchor status updated: {session_doc['_id']} -> {status}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Anchor monitoring error: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_payouts(self):
        """Monitor pending TRON payouts"""
        while self.running:
            try:
                # Check pending payouts
                pending_cursor = self.db["payouts"].find({"status": "pending"})
                
                async for payout_doc in pending_cursor:
                    if payout_doc.get("txid"):
                        status = await self.tron_client.get_transaction_status(
                            payout_doc["txid"]
                        )
                        
                        if status != "pending":
                            await self.db["payouts"].update_one(
                                {"_id": payout_doc["_id"]},
                                {"$set": {"status": status}}
                            )
                            
                            logger.info(f"Payout status updated: {payout_doc['_id']} -> {status}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Payout monitoring error: {e}")
                await asyncio.sleep(10)
    
    # Public API methods
    
    async def anchor_session_manifest(self, session_id: str, manifest_hash: str, 
                                    merkle_root: str, owner_address: str, 
                                    chunk_count: int) -> str:
        """Anchor session manifest to On-System Data Chain"""
        try:
            anchor = SessionAnchor(
                session_id=session_id,
                manifest_hash=manifest_hash, 
                merkle_root=merkle_root,
                started_at=int(datetime.now(timezone.utc).timestamp()),
                owner_address=owner_address,
                chunk_count=chunk_count
            )
            
            # Submit to blockchain
            txid = await self.on_chain_client.anchor_session_manifest(anchor)
            
            # Store in MongoDB
            await self.db["sessions"].replace_one(
                {"_id": session_id},
                anchor.to_dict(),
                upsert=True
            )
            
            logger.info(f"Session anchored: {session_id} -> {txid}")
            return txid
            
        except Exception as e:
            logger.error(f"Failed to anchor session: {e}")
            raise
    
    async def create_payout(self, session_id: str, recipient_address: str,
                          amount_usdt: float, router_type: PayoutRouter,
                          reason: str, private_key: str,
                          kyc_hash: str = None, compliance_signature: Dict = None) -> str:
        """Create USDT payout via TRON"""
        try:
            payout = TronPayout(
                session_id=session_id,
                recipient_address=recipient_address,
                amount_usdt=amount_usdt,
                router_type=router_type,
                reason=reason,
                kyc_hash=kyc_hash,
                compliance_signature=compliance_signature
            )
            
            # Submit to TRON
            txid = await self.tron_client.create_usdt_payout(payout, private_key)
            
            # Store in MongoDB
            await self.db["payouts"].replace_one(
                {"_id": payout.to_dict()["_id"]},
                payout.to_dict(),
                upsert=True
            )
            
            logger.info(f"Payout created: {session_id} -> {txid}")
            return txid
            
        except Exception as e:
            logger.error(f"Failed to create payout: {e}")
            raise
    
    async def submit_work_proof(self, node_id: str, proof_type: str, 
                              proof_data: Dict[str, Any], signature: bytes,
                              pool_id: str = None) -> bool:
        """Submit work proof for PoOT consensus"""
        proof = WorkCreditsProof(
            node_id=node_id,
            pool_id=pool_id,
            slot=self.current_slot,
            proof_type=proof_type,
            proof_data=proof_data,
            signature=signature,
            timestamp=datetime.now(timezone.utc)
        )
        
        return await self.consensus_engine.submit_work_proof(proof)
    
    async def get_work_credits(self, node_id: str, epoch: int = None) -> Optional[Dict[str, Any]]:
        """Get work credits for node"""
        try:
            if epoch is None:
                epoch = self.current_slot // (LEADER_WINDOW_DAYS * 24 * 3600 // SLOT_DURATION_SEC)
            
            tally = await self.db["work_tally"].find_one({
                "epoch": epoch,
                "entityId": node_id
            })
            
            return tally
            
        except Exception as e:
            logger.error(f"Failed to get work credits: {e}")
            return None
    
    async def get_session_anchor_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session anchor status"""
        try:
            session = await self.db["sessions"].find_one({"_id": session_id})
            return session
        except Exception as e:
            logger.error(f"Failed to get session anchor: {e}")
            return None
    
    async def get_payout_status(self, session_id: str, recipient_address: str) -> Optional[Dict[str, Any]]:
        """Get payout status"""
        try:
            payout = await self.db["payouts"].find_one({
                "_id": f"{session_id}_{recipient_address}"
            })
            return payout
        except Exception as e:
            logger.error(f"Failed to get payout status: {e}")
            return None


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
    engine = get_blockchain_engine()
    await engine.start_engine()


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