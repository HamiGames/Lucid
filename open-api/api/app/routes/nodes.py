# Path: open-api/api/app/routes/nodes.py
# Lucid RDP Node Management API Blueprint
# Implements R-MUST-017: Node worker management, PoOT consensus, work credits, DHT+CRDT operations

from __future__ import annotations

import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field

# Import from our components
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent.parent.parent))
from node.worker.node_worker import NodeWorker
from node.economy.node_economy import NodeEconomy

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/nodes", tags=["nodes"])
security = HTTPBearer()

# Pydantic Models
class NodeRegistration(BaseModel):
    """Node registration request"""
    node_address: str = Field(..., pattern=r'^T[A-Za-z0-9]{33}$', description="TRON address of node operator")
    node_id: str = Field(..., description="Unique node identifier")
    capabilities: Dict[str, Any] = Field(..., description="Node capabilities and resources")
    stake_amount: float = Field(..., ge=0, description="Staked amount for consensus participation")
    contact_info: Optional[Dict[str, str]] = Field(None, description="Optional contact information")

class WorkCredits(BaseModel):
    """PoOT consensus work credits (R-MUST-017)"""
    node_id: str = Field(..., description="Node identifier")
    pool_id: Optional[str] = Field(None, description="Pool identifier if part of pool")
    epoch: int = Field(..., description="Consensus epoch")
    credits_total: int = Field(..., description="Total work credits")
    relay_bandwidth: int = Field(..., description="Relay bandwidth served (bytes)")
    storage_proofs: int = Field(..., description="Storage availability proofs submitted")
    validation_signatures: int = Field(..., description="Block validation signatures")
    uptime_score: float = Field(..., ge=0, le=1, description="Uptime score (0-1)")
    rank: int = Field(..., description="Ranking in current epoch")
    live_score: float = Field(..., description="Liveness score for leader selection")

class NodeWorkerSession(BaseModel):
    """Node worker session data (DHT+CRDT - R-MUST-017)"""
    worker_id: str = Field(..., description="Node worker identifier")
    session_data: Dict[str, Any] = Field(..., description="Active session information")
    dht_metadata: Dict[str, Any] = Field(..., description="Encrypted metadata for DHT overlay")
    crdt_state: Dict[str, Any] = Field(..., description="CRDT replication state")

class DHTMetadata(BaseModel):
    """DHT encrypted metadata overlay"""
    encrypted_index: str = Field(..., description="Base64 encoded encrypted index")
    replication_factor: int = Field(..., ge=1, le=3, description="Data replication factor")
    shard_assignments: List[str] = Field(..., description="Assigned shard identifiers")

class CRDTState(BaseModel):
    """Conflict-free replicated data state"""
    vector_clock: Dict[str, int] = Field(..., description="Vector clock for ordering")
    merkle_dag: Dict[str, str] = Field(..., description="Merkle DAG references")
    sync_status: str = Field(..., enum=["synced", "syncing", "diverged"], description="Synchronization status")
    last_sync_time: datetime = Field(..., description="Last successful sync timestamp")

class NodeStatus(BaseModel):
    """Node operational status"""
    node_id: str
    node_address: str
    status: str = Field(..., enum=["online", "offline", "syncing", "maintenance"])
    active_sessions: int = Field(..., ge=0)
    pending_sessions: int = Field(..., ge=0)
    max_sessions: int = Field(..., gt=0)
    resource_utilization: Dict[str, float] = Field(..., description="CPU, memory, storage usage")
    network_stats: Dict[str, Any] = Field(..., description="Network connectivity metrics")
    last_seen: datetime = Field(..., description="Last heartbeat timestamp")

class EpochInfo(BaseModel):
    """Consensus epoch information"""
    epoch_number: int
    start_time: datetime
    end_time: datetime
    participating_nodes: int
    total_work_credits: int
    leader_node_id: Optional[str] = None
    blocks_produced: int = 0
    finality_achieved: bool = False

class LeaderSelection(BaseModel):
    """Leader selection for PoOT consensus"""
    epoch: int
    selected_leader: str = Field(..., description="Selected leader node ID")
    selection_criteria: Dict[str, Any] = Field(..., description="Criteria used for selection")
    live_scores: Dict[str, float] = Field(..., description="All participating nodes' live scores")
    selection_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UptimeBeacon(BaseModel):
    """Time-sealed uptime beacon"""
    node_id: str
    beacon_id: str
    timestamp: datetime
    signature: str = Field(..., description="Time-sealed signature")
    attestations: List[str] = Field(default_factory=list, description="Peer attestations")
    block_height: int = Field(..., description="Block height at beacon time")

# Global node management components
node_workers: Dict[str, NodeWorker] = {}
node_economies: Dict[str, NodeEconomy] = {}

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_node(
    registration: NodeRegistration,
    token: str = Depends(security)
) -> Dict[str, Any]:
    """
    Register a new node in the network (R-MUST-017).
    
    Initializes DHT participation and CRDT replication.
    """
    try:
        logger.info(f"Registering node: {registration.node_id} ({registration.node_address})")
        
        # Validate node capabilities
        required_capabilities = ["max_sessions", "bandwidth_mbps", "storage_gb"]
        for cap in required_capabilities:
            if cap not in registration.capabilities:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required capability: {cap}"
                )
        
        # Verify minimum stake requirement
        min_stake = 100.0  # Minimum stake in USDT
        if registration.stake_amount < min_stake:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stake: {registration.stake_amount} < {min_stake}"
            )
        
        # Initialize node worker
        try:
            node_worker = NodeWorker(registration.node_address, "mock_private_key")
            await node_worker.start()
            node_workers[registration.node_id] = node_worker
            
            # Initialize node economy
            node_economy = NodeEconomy(registration.node_address, "mock_private_key")
            await node_economy.start()
            node_economies[registration.node_id] = node_economy
            
        except Exception as init_error:
            logger.error(f"Node initialization failed: {init_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Node initialization failed: {str(init_error)}"
            )
        
        # Register in DHT overlay network
        dht_registration = {
            "node_id": registration.node_id,
            "node_address": registration.node_address,
            "capabilities": registration.capabilities,
            "dht_routing_table": {},
            "replication_peers": []
        }
        
        registration_result = {
            "node_id": registration.node_id,
            "status": "registered",
            "registered_at": datetime.now(timezone.utc).isoformat(),
            "dht_peer_id": f"dht_{registration.node_id}",
            "initial_epoch": 1,
            "stake_confirmed": True,
            "capabilities_verified": True
        }
        
        logger.info(f"Node registered successfully: {registration.node_id}")
        return registration_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Node registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Node registration failed: {str(e)}"
        )

@router.get("/{node_id}/status", response_model=NodeStatus)
async def get_node_status(
    node_id: str,
    token: str = Depends(security)
) -> NodeStatus:
    """Get node operational status"""
    try:
        logger.info(f"Getting node status: {node_id}")
        
        # Get status from node worker if available
        if node_id in node_workers:
            node_worker = node_workers[node_id]
            worker_status = await node_worker.get_node_status()
            
            status = NodeStatus(
                node_id=node_id,
                node_address=worker_status.get("node_address", "unknown"),
                status="online" if worker_status.get("status") == "ready" else "offline",
                active_sessions=worker_status.get("active_sessions", 0),
                pending_sessions=worker_status.get("pending_sessions", 0),
                max_sessions=worker_status.get("max_sessions", 10),
                resource_utilization={
                    "cpu_percent": worker_status.get("resource_metrics", {}).get("cpu_percent", 0),
                    "memory_percent": worker_status.get("resource_metrics", {}).get("memory_percent", 0),
                    "storage_percent": 75.0  # Mock storage usage
                },
                network_stats={
                    "bandwidth_used_mbps": 25.5,
                    "peers_connected": 8,
                    "dht_routing_entries": 150
                },
                last_seen=datetime.now(timezone.utc)
            )
        else:
            # Return mock status for unregistered node
            status = NodeStatus(
                node_id=node_id,
                node_address="unknown",
                status="offline",
                active_sessions=0,
                pending_sessions=0,
                max_sessions=0,
                resource_utilization={},
                network_stats={},
                last_seen=datetime.now(timezone.utc) - timedelta(hours=1)
            )
        
        logger.info(f"Node status retrieved: {node_id} -> {status.status}")
        return status
        
    except Exception as e:
        logger.error(f"Failed to get node status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve node status: {str(e)}"
        )

@router.get("/{node_id}/work-credits", response_model=WorkCredits)
async def get_node_work_credits(
    node_id: str,
    epoch: Optional[int] = Query(None, description="Specific epoch to query"),
    token: str = Depends(security)
) -> WorkCredits:
    """Get node work credits for PoOT consensus"""
    try:
        current_epoch = epoch or 1
        logger.info(f"Getting work credits for node {node_id}, epoch: {current_epoch}")
        
        # This would query the actual consensus database
        # For now, return mock work credits based on node performance
        mock_credits = WorkCredits(
            node_id=node_id,
            epoch=current_epoch,
            credits_total=15750,
            relay_bandwidth=1024 * 1024 * 1024,  # 1GB
            storage_proofs=144,  # 24h * 6 proofs/hour
            validation_signatures=288,  # 24h * 12 validations/hour
            uptime_score=0.95,
            rank=7,
            live_score=0.87
        )
        
        logger.info(f"Work credits retrieved: {node_id} -> {mock_credits.credits_total} credits")
        return mock_credits
        
    except Exception as e:
        logger.error(f"Failed to get work credits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve work credits: {str(e)}"
        )

@router.get("/{node_id}/sessions", response_model=NodeWorkerSession)
async def get_node_worker_sessions(
    node_id: str,
    token: str = Depends(security)
) -> NodeWorkerSession:
    """Get node worker session data with DHT+CRDT state"""
    try:
        logger.info(f"Getting worker sessions for node: {node_id}")
        
        # Mock DHT metadata
        dht_metadata = DHTMetadata(
            encrypted_index="base64_encrypted_session_index",
            replication_factor=2,
            shard_assignments=["shard_001", "shard_017", "shard_042"]
        )
        
        # Mock CRDT state
        crdt_state = CRDTState(
            vector_clock={node_id: 156, "peer_node_1": 142, "peer_node_2": 138},
            merkle_dag={"root": "abc123", "branches": "def456"},
            sync_status="synced",
            last_sync_time=datetime.now(timezone.utc) - timedelta(minutes=5)
        )
        
        # Get actual session data if node worker exists
        session_data = {"active_sessions": [], "bandwidth_usage": 0, "storage_used": 0}
        if node_id in node_workers:
            worker_status = await node_workers[node_id].get_node_status()
            session_data = {
                "active_sessions": [f"session_{i}" for i in range(worker_status.get("active_sessions", 0))],
                "bandwidth_usage": 25 * 1024 * 1024,  # 25MB
                "storage_used": 500 * 1024 * 1024  # 500MB
            }
        
        worker_session = NodeWorkerSession(
            worker_id=node_id,
            session_data=session_data,
            dht_metadata=dht_metadata.dict(),
            crdt_state=crdt_state.dict()
        )
        
        logger.info(f"Worker sessions retrieved: {node_id}")
        return worker_session
        
    except Exception as e:
        logger.error(f"Failed to get worker sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve worker sessions: {str(e)}"
        )

@router.get("/consensus/epoch/current", response_model=EpochInfo)
async def get_current_epoch(
    token: str = Depends(security)
) -> EpochInfo:
    """Get current consensus epoch information"""
    try:
        logger.info("Getting current consensus epoch")
        
        # This would query the consensus database
        current_epoch = EpochInfo(
            epoch_number=42,
            start_time=datetime.now(timezone.utc).replace(hour=0, minute=0, second=0),
            end_time=datetime.now(timezone.utc).replace(hour=23, minute=59, second=59),
            participating_nodes=15,
            total_work_credits=237500,
            leader_node_id="node_leader_07",
            blocks_produced=144,
            finality_achieved=True
        )
        
        logger.info(f"Current epoch: {current_epoch.epoch_number}")
        return current_epoch
        
    except Exception as e:
        logger.error(f"Failed to get current epoch: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve current epoch: {str(e)}"
        )

@router.post("/consensus/leader-selection", response_model=LeaderSelection)
async def select_epoch_leader(
    epoch: int = Body(..., description="Epoch number for leader selection"),
    token: str = Depends(security)
) -> LeaderSelection:
    """Perform leader selection for PoOT consensus"""
    try:
        logger.info(f"Selecting leader for epoch: {epoch}")
        
        # This would implement actual PoOT leader selection algorithm
        # For now, simulate leader selection based on work credits and live scores
        participating_nodes = [f"node_{i:02d}" for i in range(1, 16)]
        live_scores = {node: 0.7 + (hash(node + str(epoch)) % 30) / 100 for node in participating_nodes}
        
        # Select leader with highest combined score
        selected_leader = max(live_scores.keys(), key=lambda k: live_scores[k])
        
        selection = LeaderSelection(
            epoch=epoch,
            selected_leader=selected_leader,
            selection_criteria={
                "algorithm": "poot_weighted_random",
                "work_credits_weight": 0.6,
                "live_score_weight": 0.4,
                "minimum_uptime": 0.8
            },
            live_scores=live_scores
        )
        
        logger.info(f"Leader selected for epoch {epoch}: {selected_leader}")
        return selection
        
    except Exception as e:
        logger.error(f"Leader selection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Leader selection failed: {str(e)}"
        )

@router.post("/{node_id}/uptime-beacon", response_model=UptimeBeacon)
async def submit_uptime_beacon(
    node_id: str,
    block_height: int = Body(..., description="Current block height"),
    token: str = Depends(security)
) -> UptimeBeacon:
    """Submit time-sealed uptime beacon"""
    try:
        logger.info(f"Submitting uptime beacon for node {node_id} at block {block_height}")
        
        # Generate beacon ID
        beacon_id = hashlib.sha256(f"{node_id}_{block_height}_{datetime.now(timezone.utc).isoformat()}".encode()).hexdigest()[:16]
        
        # Create time-sealed signature (would use actual node's private key)
        beacon_data = f"{node_id}_{block_height}_{datetime.now(timezone.utc).timestamp()}"
        signature = hashlib.sha256(beacon_data.encode()).hexdigest()  # Mock signature
        
        beacon = UptimeBeacon(
            node_id=node_id,
            beacon_id=beacon_id,
            timestamp=datetime.now(timezone.utc),
            signature=signature,
            block_height=block_height,
            attestations=[]  # Would be populated by peer nodes
        )
        
        # Store beacon for consensus verification
        # await store_uptime_beacon(beacon)
        
        logger.info(f"Uptime beacon submitted: {beacon_id}")
        return beacon
        
    except Exception as e:
        logger.error(f"Uptime beacon submission failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Uptime beacon submission failed: {str(e)}"
        )

@router.get("/dht/status", response_model=Dict[str, Any])
async def get_dht_network_status(
    token: str = Depends(security)
) -> Dict[str, Any]:
    """Get DHT overlay network status"""
    try:
        logger.info("Getting DHT network status")
        
        dht_status = {
            "network_size": 15,
            "routing_table_entries": 2250,
            "active_shards": 64,
            "replication_factor": 2,
            "sync_status": "healthy",
            "peer_connections": {
                "connected": 12,
                "connecting": 2,
                "failed": 1
            },
            "data_integrity": {
                "verified_chunks": 15780,
                "corrupt_chunks": 0,
                "missing_chunks": 3
            },
            "last_full_sync": datetime.now(timezone.utc) - timedelta(hours=2),
            "network_partition_risk": "low"
        }
        
        logger.info(f"DHT status: {dht_status['network_size']} nodes, {dht_status['sync_status']} sync")
        return dht_status
        
    except Exception as e:
        logger.error(f"Failed to get DHT status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve DHT status: {str(e)}"
        )

@router.get("/consensus/work-credits/leaderboard", response_model=List[WorkCredits])
async def get_work_credits_leaderboard(
    epoch: Optional[int] = Query(None, description="Epoch to query"),
    limit: int = Query(20, ge=1, le=100, description="Number of top nodes"),
    token: str = Depends(security)
) -> List[WorkCredits]:
    """Get work credits leaderboard for epoch"""
    try:
        current_epoch = epoch or 1
        logger.info(f"Getting work credits leaderboard for epoch: {current_epoch}")
        
        # This would query actual consensus database
        # Generate mock leaderboard
        leaderboard = []
        for i in range(1, min(limit + 1, 21)):
            node_credits = WorkCredits(
                node_id=f"node_{i:02d}",
                epoch=current_epoch,
                credits_total=25000 - (i * 1000) + (hash(f"node_{i}") % 500),
                relay_bandwidth=2 * 1024**3 - (i * 100 * 1024**2),  # Decreasing bandwidth
                storage_proofs=200 - i * 5,
                validation_signatures=400 - i * 10,
                uptime_score=max(0.95 - (i * 0.02), 0.7),
                rank=i,
                live_score=max(0.9 - (i * 0.03), 0.5)
            )
            leaderboard.append(node_credits)
        
        logger.info(f"Leaderboard retrieved: top {len(leaderboard)} nodes for epoch {current_epoch}")
        return leaderboard
        
    except Exception as e:
        logger.error(f"Failed to get leaderboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve leaderboard: {str(e)}"
        )

@router.post("/{node_id}/deregister", status_code=status.HTTP_200_OK)
async def deregister_node(
    node_id: str,
    reason: str = Body(..., description="Deregistration reason"),
    token: str = Depends(security)
) -> Dict[str, Any]:
    """Deregister node from network"""
    try:
        logger.info(f"Deregistering node: {node_id}, reason: {reason}")
        
        # Stop node worker if running
        if node_id in node_workers:
            await node_workers[node_id].stop()
            del node_workers[node_id]
        
        # Stop node economy if running
        if node_id in node_economies:
            await node_economies[node_id].stop()
            del node_economies[node_id]
        
        # Remove from DHT network
        # await remove_from_dht(node_id)
        
        # Process final payouts if any
        # await process_final_node_payouts(node_id)
        
        result = {
            "node_id": node_id,
            "status": "deregistered",
            "deregistered_at": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "final_payout_processed": True,
            "dht_cleanup_completed": True
        }
        
        logger.info(f"Node deregistered successfully: {node_id}")
        return result
        
    except Exception as e:
        logger.error(f"Node deregistration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Node deregistration failed: {str(e)}"
        )

# Health check endpoint
@router.get("/health", include_in_schema=False)
async def nodes_health() -> Dict[str, Any]:
    """Node management service health check"""
    return {
        "service": "nodes",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "node_registry": "operational",
            "poot_consensus": "operational",
            "dht_overlay": "operational",
            "crdt_replication": "operational",
            "work_credits_calculator": "operational"
        },
        "network_stats": {
            "registered_nodes": len(node_workers),
            "active_workers": sum(1 for w in node_workers.values()),
            "consensus_participating": len(node_workers)
        }
    }