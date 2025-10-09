# node/shards/__init__.py
# Lucid Node Shards Module
# LUCID-STRICT Layer 1 Core Infrastructure

"""
Shards module for Lucid node operations.

This module provides:
- Shard host creation and management
- Shard assignment and replication
- Storage host monitoring and maintenance
- Data integrity and repair operations

Core Components:
- ShardHostCreationSystem: Shard creation and assignment
- ShardHostManagementSystem: Host management and maintenance
- ShardInfo: Shard metadata and information
- ShardHost: Host node information
"""

from .shard_host_creation import (
    ShardHostCreationSystem,
    ShardInfo,
    ShardHost,
    HostStatus,
    ShardStatus,
    ShardCreationTask,
    get_shard_host_creation,
    create_shard_host_creation,
    cleanup_shard_host_creation
)

from .shard_host_management import (
    ShardHostManagementSystem,
    PerformanceMetrics,
    MaintenanceWindow,
    ShardIntegrityCheck,
    DataRepairOperation,
    MaintenanceType,
    OperationStatus,
    get_shard_host_management,
    create_shard_host_management,
    cleanup_shard_host_management
)

__all__ = [
    # Host Creation
    'ShardHostCreationSystem',
    'ShardInfo',
    'ShardHost',
    'HostStatus',
    'ShardStatus',
    'ShardCreationTask',
    'get_shard_host_creation',
    'create_shard_host_creation',
    'cleanup_shard_host_creation',
    
    # Host Management
    'ShardHostManagementSystem',
    'PerformanceMetrics',
    'MaintenanceWindow',
    'ShardIntegrityCheck',
    'DataRepairOperation',
    'MaintenanceType',
    'OperationStatus',
    'get_shard_host_management',
    'create_shard_host_management',
    'cleanup_shard_host_management'
]
