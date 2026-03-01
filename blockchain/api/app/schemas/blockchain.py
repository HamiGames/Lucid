"""
Blockchain Schema Models

This module defines Pydantic models for blockchain information API endpoints.
Implements the OpenAPI 3.0 specification for blockchain queries.

Models:
- BlockchainInfo: Comprehensive blockchain network information
- BlockchainStatus: Current blockchain status and health
- BlockHeight: Current block height information
- NetworkInfo: Network topology and peer information
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class BlockchainInfo(BaseModel):
    """Comprehensive information about the lucid_blocks blockchain network."""
    network_name: str = Field(..., description="Name of the blockchain network")
    version: str = Field(..., description="Blockchain version")
    consensus_algorithm: str = Field(..., description="Consensus algorithm used")
    block_time: int = Field(..., description="Target block time in seconds")
    current_height: int = Field(..., description="Current block height")
    total_transactions: int = Field(..., description="Total number of transactions")
    network_hash_rate: str = Field(..., description="Network hash rate")
    difficulty: float = Field(..., description="Current mining difficulty")
    chain_id: str = Field(..., description="Unique chain identifier")
    genesis_block: str = Field(..., description="Genesis block hash")
    last_block_hash: str = Field(..., description="Last block hash")
    last_block_time: datetime = Field(..., description="Last block timestamp")
    total_supply: float = Field(..., description="Total token supply")
    circulating_supply: float = Field(..., description="Circulating token supply")
    staking_rewards: float = Field(..., description="Staking reward percentage")
    validator_count: int = Field(..., description="Total number of validators")
    active_validators: int = Field(..., description="Number of active validators")


class BlockchainStatus(BaseModel):
    """Current status and health of the lucid_blocks blockchain."""
    status: str = Field(..., description="Overall blockchain status", enum=["healthy", "warning", "error"])
    sync_status: str = Field(..., description="Synchronization status", enum=["synced", "syncing", "behind"])
    peer_count: int = Field(..., description="Number of connected peers")
    uptime: int = Field(..., description="System uptime in seconds")
    last_block_time: datetime = Field(..., description="Last block timestamp")
    block_production_rate: float = Field(..., description="Blocks produced per second")
    transaction_throughput: float = Field(..., description="Transactions per second")
    memory_usage: float = Field(..., description="Memory usage in MB")
    cpu_usage: float = Field(..., description="CPU usage percentage")
    disk_usage: float = Field(..., description="Disk usage in GB")
    network_latency: float = Field(..., description="Average network latency in ms")
    consensus_health: str = Field(..., description="Consensus mechanism health")
    validator_status: str = Field(..., description="Validator status")


class BlockHeight(BaseModel):
    """Current block height information."""
    height: int = Field(..., description="Current block height")
    timestamp: datetime = Field(..., description="Block timestamp")
    block_hash: str = Field(..., description="Block hash")
    transaction_count: int = Field(..., description="Number of transactions in block")
    block_size: int = Field(..., description="Block size in bytes")
    validator: str = Field(..., description="Block validator address")


class NetworkInfo(BaseModel):
    """Information about the lucid_blocks network topology and peers."""
    total_peers: int = Field(..., description="Total number of peers")
    active_peers: int = Field(..., description="Number of active peers")
    peer_list: List[Dict[str, Any]] = Field(..., description="List of peer information")
    network_topology: str = Field(..., description="Network topology type")
    average_latency: float = Field(..., description="Average network latency in ms")
    bandwidth_usage: float = Field(..., description="Bandwidth usage in KB/s")
    protocol_version: str = Field(..., description="Network protocol version")