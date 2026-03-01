# Path: node/repositories/node_repository.py
# Lucid Node Management Repository - Node Repository
# Based on LUCID-STRICT requirements per Spec-1c

"""
Node repository for Lucid system.

This module provides data access methods for:
- Node CRUD operations
- Resource monitoring
- PoOT validation
- Payout management
"""

from typing import List, Optional, Dict, Any, Tuple
import os
from datetime import datetime, timezone, timedelta
import logging
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING
import uuid
import hashlib
import base64

from ..models.node import (
    Node, NodeCreateRequest, NodeUpdateRequest, NodeStatus, NodeType,
    NodeResources, ResourceMetrics, CPUMetrics, MemoryMetrics, 
    DiskMetrics, NetworkMetrics, GPUMetrics, PoOTScore, PoOTValidation,
    PoOTValidationRequest
)
from ..models.payout import Payout, PayoutRequest, BatchPayoutRequest, PayoutStatus

logger = logging.getLogger(__name__)

class NodeRepository:
    """Repository for node management operations"""
    
    def __init__(self, mongo_url: Optional[str] = None, database_name: Optional[str] = None):
        """Initialize node repository"""
        import os
        self.mongo_url = mongo_url or os.getenv("MONGODB_URL")
        self.database_name = database_name or os.getenv("MONGODB_DATABASE", "lucid")
        """Initialize node repository"""
        self.mongo_url = mongo_url
        self.database_name = database_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.mongo_url)
            self.db = self.client[self.database_name]
            
            # Create indexes
            await self._create_indexes()
            
            logger.info("Connected to MongoDB for node repository")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def _create_indexes(self):
        """Create database indexes"""
        try:
            # Nodes collection indexes
            await self.db.nodes.create_index([("node_id", ASCENDING)], unique=True)
            await self.db.nodes.create_index([("name", ASCENDING)], unique=True)
            await self.db.nodes.create_index([("status", ASCENDING)])
            await self.db.nodes.create_index([("pool_id", ASCENDING)])
            await self.db.nodes.create_index([("node_type", ASCENDING)])
            await self.db.nodes.create_index([("last_heartbeat", DESCENDING)])
            await self.db.nodes.create_index([("poot_score", DESCENDING)])
            
            # Resource metrics indexes
            await self.db.resource_metrics.create_index([("node_id", ASCENDING), ("timestamp", DESCENDING)])
            await self.db.resource_metrics.create_index([("timestamp", DESCENDING)], expireAfterSeconds=7776000)  # 90 days
            
            # PoOT validations indexes
            await self.db.poot_validations.create_index([("node_id", ASCENDING), ("timestamp", DESCENDING)])
            await self.db.poot_validations.create_index([("validation_id", ASCENDING)], unique=True)
            await self.db.poot_validations.create_index([("output_hash", ASCENDING)])
            await self.db.poot_validations.create_index([("is_valid", ASCENDING), ("score", DESCENDING)])
            
            # Payouts indexes
            await self.db.payouts.create_index([("payout_id", ASCENDING)], unique=True)
            await self.db.payouts.create_index([("node_id", ASCENDING), ("created_at", DESCENDING)])
            await self.db.payouts.create_index([("status", ASCENDING)])
            await self.db.payouts.create_index([("batch_id", ASCENDING)])
            await self.db.payouts.create_index([("wallet_address", ASCENDING)])
            await self.db.payouts.create_index([("transaction_hash", ASCENDING)])
            await self.db.payouts.create_index([("scheduled_at", ASCENDING)])
            
            logger.info("Created database indexes")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
            raise
    
    # Node CRUD operations
    async def create_node(self, node_data: NodeCreateRequest) -> Node:
        """Create a new node"""
        try:
            # Generate node ID
            node_id = f"node_{uuid.uuid4().hex[:12]}"
            
            # Create node document
            node_doc = {
                "node_id": node_id,
                "name": node_data.name,
                "status": NodeStatus.INACTIVE.value,
                "node_type": node_data.node_type.value,
                "pool_id": node_data.initial_pool_id,
                "hardware_info": node_data.hardware_info.dict(),
                "location": node_data.location.dict(),
                "configuration": node_data.configuration.dict() if node_data.configuration else {},
                "poot_score": None,
                "last_heartbeat": None,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            # Insert node
            result = await self.db.nodes.insert_one(node_doc)
            if not result.inserted_id:
                raise Exception("Failed to create node")
            
            # Return created node
            return Node(**node_doc)
            
        except Exception as e:
            logger.error(f"Failed to create node: {e}")
            raise
    
    async def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by ID"""
        try:
            node_doc = await self.db.nodes.find_one({"node_id": node_id})
            if not node_doc:
                return None
            
            return Node(**node_doc)
            
        except Exception as e:
            logger.error(f"Failed to get node {node_id}: {e}")
            raise
    
    async def get_node_by_name(self, name: str) -> Optional[Node]:
        """Get node by name"""
        try:
            node_doc = await self.db.nodes.find_one({"name": name})
            if not node_doc:
                return None
            
            return Node(**node_doc)
            
        except Exception as e:
            logger.error(f"Failed to get node by name {name}: {e}")
            raise
    
    async def update_node(self, node_id: str, node_data: NodeUpdateRequest) -> Node:
        """Update node"""
        try:
            update_doc = {"updated_at": datetime.now(timezone.utc)}
            
            if node_data.name:
                update_doc["name"] = node_data.name
            if node_data.node_type:
                update_doc["node_type"] = node_data.node_type.value
            if node_data.pool_id:
                update_doc["pool_id"] = node_data.pool_id
            if node_data.status:
                update_doc["status"] = node_data.status.value
            if node_data.configuration:
                update_doc["configuration"] = node_data.configuration.dict()
            
            result = await self.db.nodes.update_one(
                {"node_id": node_id},
                {"$set": update_doc}
            )
            
            if result.matched_count == 0:
                raise Exception("Node not found")
            
            # Return updated node
            return await self.get_node(node_id)
            
        except Exception as e:
            logger.error(f"Failed to update node {node_id}: {e}")
            raise
    
    async def delete_node(self, node_id: str) -> bool:
        """Delete node"""
        try:
            result = await self.db.nodes.delete_one({"node_id": node_id})
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Failed to delete node {node_id}: {e}")
            raise
    
    async def list_nodes(self, page: int = 1, limit: int = 20, filters: Dict[str, Any] = None) -> Tuple[List[Node], int]:
        """List nodes with pagination and filtering"""
        try:
            # Build query
            query = {}
            if filters:
                query.update(filters)
            
            # Get total count
            total_count = await self.db.nodes.count_documents(query)
            
            # Get nodes
            skip = (page - 1) * limit
            cursor = self.db.nodes.find(query).skip(skip).limit(limit).sort("created_at", DESCENDING)
            nodes = []
            
            async for node_doc in cursor:
                nodes.append(Node(**node_doc))
            
            return nodes, total_count
            
        except Exception as e:
            logger.error(f"Failed to list nodes: {e}")
            raise
    
    # Node status operations
    async def start_node(self, node_id: str) -> bool:
        """Start node"""
        try:
            result = await self.db.nodes.update_one(
                {"node_id": node_id},
                {
                    "$set": {
                        "status": NodeStatus.STARTING.value,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to start node {node_id}: {e}")
            raise
    
    async def stop_node(self, node_id: str) -> bool:
        """Stop node"""
        try:
            result = await self.db.nodes.update_one(
                {"node_id": node_id},
                {
                    "$set": {
                        "status": NodeStatus.STOPPING.value,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to stop node {node_id}: {e}")
            raise
    
    async def get_node_status(self, node_id: str) -> Dict[str, Any]:
        """Get node status information"""
        try:
            node = await self.get_node(node_id)
            if not node:
                return {}
            
            # Get additional status information
            status_info = {
                "uptime": None,
                "resource_utilization": None,
                "active_sessions": 0,
                "last_error": None
            }
            
            # Get latest resource metrics
            latest_metrics = await self.db.resource_metrics.find_one(
                {"node_id": node_id},
                sort=[("timestamp", DESCENDING)]
            )
            
            if latest_metrics:
                status_info["resource_utilization"] = {
                    "cpu_percent": latest_metrics.get("cpu", {}).get("usage_percent", 0),
                    "memory_percent": latest_metrics.get("memory", {}).get("used_bytes", 0) / latest_metrics.get("memory", {}).get("total_bytes", 1) * 100,
                    "disk_percent": latest_metrics.get("disk", {}).get("used_bytes", 0) / latest_metrics.get("disk", {}).get("total_bytes", 1) * 100
                }
            
            return status_info
            
        except Exception as e:
            logger.error(f"Failed to get node status {node_id}: {e}")
            raise
    
    # Resource monitoring
    async def get_node_resources(self, node_id: str, time_range: str = "1h") -> NodeResources:
        """Get node resource utilization"""
        try:
            # Calculate time range
            now = datetime.now(timezone.utc)
            if time_range == "1h":
                start_time = now - timedelta(hours=1)
            elif time_range == "6h":
                start_time = now - timedelta(hours=6)
            elif time_range == "24h":
                start_time = now - timedelta(hours=24)
            elif time_range == "7d":
                start_time = now - timedelta(days=7)
            else:
                start_time = now - timedelta(hours=1)
            
            # Get latest resource metrics
            latest_metrics = await self.db.resource_metrics.find_one(
                {"node_id": node_id, "timestamp": {"$gte": start_time}},
                sort=[("timestamp", DESCENDING)]
            )
            
            if not latest_metrics:
                # Return empty metrics if no data
                return NodeResources(
                    node_id=node_id,
                    timestamp=now,
                    cpu=CPUMetrics(usage_percent=0, cores=1, frequency_mhz=0, load_average=[0, 0, 0]),
                    memory=MemoryMetrics(total_bytes=0, used_bytes=0, free_bytes=0, cached_bytes=0, swap_total_bytes=0, swap_used_bytes=0),
                    disk=DiskMetrics(total_bytes=0, used_bytes=0, free_bytes=0, read_iops=0, write_iops=0, read_throughput_mbps=0, write_throughput_mbps=0),
                    network=NetworkMetrics(interfaces=[], total_bytes_in=0, total_bytes_out=0, packets_in=0, packets_out=0, errors_in=0, errors_out=0)
                )
            
            # Convert to NodeResources
            return NodeResources(
                node_id=node_id,
                timestamp=latest_metrics["timestamp"],
                cpu=CPUMetrics(**latest_metrics.get("cpu", {})),
                memory=MemoryMetrics(**latest_metrics.get("memory", {})),
                disk=DiskMetrics(**latest_metrics.get("disk", {})),
                network=NetworkMetrics(**latest_metrics.get("network", {})),
                gpu=GPUMetrics(**latest_metrics.get("gpu", {})) if latest_metrics.get("gpu") else None
            )
            
        except Exception as e:
            logger.error(f"Failed to get node resources {node_id}: {e}")
            raise
    
    async def get_resource_metrics(self, node_id: str, metric_type: str = None, 
                                 granularity: str = "5m", start_time: datetime = None, 
                                 end_time: datetime = None) -> ResourceMetrics:
        """Get detailed resource metrics"""
        try:
            # Set default time range
            if not end_time:
                end_time = datetime.now(timezone.utc)
            if not start_time:
                start_time = end_time - timedelta(hours=1)
            
            # Build query
            query = {
                "node_id": node_id,
                "timestamp": {"$gte": start_time, "$lte": end_time}
            }
            
            if metric_type:
                query[f"{metric_type}.usage_percent"] = {"$exists": True}
            
            # Get metrics
            cursor = self.db.resource_metrics.find(query).sort("timestamp", ASCENDING)
            data_points = []
            
            async for doc in cursor:
                data_points.append({
                    "timestamp": doc["timestamp"],
                    "metrics": {k: v for k, v in doc.items() if k not in ["_id", "node_id", "timestamp"]}
                })
            
            return ResourceMetrics(
                node_id=node_id,
                metric_type=metric_type,
                granularity=granularity,
                start_time=start_time,
                end_time=end_time,
                data_points=data_points
            )
            
        except Exception as e:
            logger.error(f"Failed to get resource metrics {node_id}: {e}")
            raise
    
    # PoOT operations
    async def get_poot_score(self, node_id: str) -> Optional[PoOTScore]:
        """Get current PoOT score for node"""
        try:
            # Get latest PoOT validation
            validation_doc = await self.db.poot_validations.find_one(
                {"node_id": node_id, "is_valid": True},
                sort=[("timestamp", DESCENDING)]
            )
            
            if not validation_doc:
                return None
            
            return PoOTScore(
                node_id=node_id,
                score=validation_doc["score"],
                calculated_at=validation_doc["timestamp"],
                output_hash=validation_doc["output_hash"],
                validation_status="valid",
                confidence=validation_doc["confidence"]
            )
            
        except Exception as e:
            logger.error(f"Failed to get PoOT score {node_id}: {e}")
            raise
    
    async def validate_poot(self, node_id: str, output_data: str, output_hash: str, 
                           timestamp: datetime, nonce: str) -> PoOTValidation:
        """Validate PoOT for node"""
        try:
            # Generate validation ID
            validation_id = str(uuid.uuid4())
            
            # Simple PoOT validation logic (placeholder)
            # In real implementation, this would involve complex validation
            is_valid = True
            score = 85.0  # Placeholder score
            confidence = 0.95
            errors = []
            
            # Create validation document
            validation_doc = {
                "validation_id": validation_id,
                "node_id": node_id,
                "output_data": output_data,
                "output_hash": output_hash,
                "timestamp": timestamp,
                "score": score,
                "confidence": confidence,
                "is_valid": is_valid,
                "validation_time_ms": 150,  # Placeholder
                "errors": errors,
                "created_at": datetime.now(timezone.utc)
            }
            
            # Insert validation
            await self.db.poot_validations.insert_one(validation_doc)
            
            return PoOTValidation(**validation_doc)
            
        except Exception as e:
            logger.error(f"Failed to validate PoOT {node_id}: {e}")
            raise
    
    async def calculate_poot_score(self, node_id: str, output_data: str) -> PoOTScore:
        """Calculate PoOT score for node"""
        try:
            # Calculate hash
            decoded_data = base64.b64decode(output_data)
            output_hash = hashlib.sha256(decoded_data).hexdigest()
            
            # Simple score calculation (placeholder)
            score = 85.0  # Placeholder score
            confidence = 0.95
            
            # Create score document
            score_doc = {
                "node_id": node_id,
                "score": score,
                "calculated_at": datetime.now(timezone.utc),
                "output_hash": output_hash,
                "validation_status": "valid",
                "confidence": confidence
            }
            
            return PoOTScore(**score_doc)
            
        except Exception as e:
            logger.error(f"Failed to calculate PoOT score {node_id}: {e}")
            raise
    
    # Payout operations
    async def create_payout(self, payout_request: PayoutRequest) -> Payout:
        """Create a new payout"""
        try:
            # Generate payout ID
            payout_id = f"payout_{uuid.uuid4().hex[:12]}"
            
            # Create payout document
            payout_doc = {
                "payout_id": payout_id,
                "node_id": payout_request.node_id,
                "amount": payout_request.amount,
                "currency": payout_request.currency.value,
                "wallet_address": payout_request.wallet_address,
                "status": PayoutStatus.PENDING.value,
                "priority": payout_request.priority.value,
                "transaction_hash": None,
                "batch_id": None,
                "scheduled_at": payout_request.scheduled_at,
                "processed_at": None,
                "completed_at": None,
                "error_message": None,
                "retry_count": 0,
                "max_retries": 3,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            
            # Insert payout
            await self.db.payouts.insert_one(payout_doc)
            
            return Payout(**payout_doc)
            
        except Exception as e:
            logger.error(f"Failed to create payout: {e}")
            raise
    
    async def get_payout(self, payout_id: str) -> Optional[Payout]:
        """Get payout by ID"""
        try:
            payout_doc = await self.db.payouts.find_one({"payout_id": payout_id})
            if not payout_doc:
                return None
            
            return Payout(**payout_doc)
            
        except Exception as e:
            logger.error(f"Failed to get payout {payout_id}: {e}")
            raise
    
    async def get_node_payouts(self, node_id: str, page: int = 1, limit: int = 20, 
                              filters: Dict[str, Any] = None) -> Tuple[List[Payout], int]:
        """Get payouts for a node"""
        try:
            # Build query
            query = {"node_id": node_id}
            if filters:
                query.update(filters)
            
            # Get total count
            total_count = await self.db.payouts.count_documents(query)
            
            # Get payouts
            skip = (page - 1) * limit
            cursor = self.db.payouts.find(query).skip(skip).limit(limit).sort("created_at", DESCENDING)
            payouts = []
            
            async for payout_doc in cursor:
                payouts.append(Payout(**payout_doc))
            
            return payouts, total_count
            
        except Exception as e:
            logger.error(f"Failed to get node payouts {node_id}: {e}")
            raise
    
    async def cancel_payout(self, payout_id: str) -> bool:
        """Cancel a payout"""
        try:
            result = await self.db.payouts.update_one(
                {"payout_id": payout_id, "status": PayoutStatus.PENDING.value},
                {
                    "$set": {
                        "status": PayoutStatus.CANCELLED.value,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Failed to cancel payout {payout_id}: {e}")
            raise
