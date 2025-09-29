# Path: node/__init__.py
"""
Node system package for Lucid RDP.
Implements peer discovery, node management, and distributed node operations.
"""

from .peer_discovery import PeerDiscovery
from .node_manager import NodeManager
from .work_credits import WorkCreditsCalculator

# Optional imports - import only if modules exist
try:
    from .economy.node_economy import NodeEconomy
except ImportError:
    NodeEconomy = None

try:
    from .flags.node_flag_systems import NodeFlagSystem
except ImportError:
    NodeFlagSystem = None

try:
    from .governance.node_vote_systems import NodeVoteSystem
except ImportError:
    NodeVoteSystem = None

try:
    from .validation.node_poot_validations import NodePootValidation
except ImportError:
    NodePootValidation = None

try:
    from .sync.node_operator_sync_systems import NodeOperatorSyncSystem
except ImportError:
    NodeOperatorSyncSystem = None

try:
    from .pools.node_pool_systems import NodePoolSystem
except ImportError:
    NodePoolSystem = None

try:
    from .registration.node_registration_protocol import NodeRegistrationProtocol
except ImportError:
    NodeRegistrationProtocol = None

try:
    from .shards.shard_host_creation import ShardHostCreation
    from .shards.shard_host_management import ShardHostManagement
except ImportError:
    ShardHostCreation = None
    ShardHostManagement = None

try:
    from .worker.node_worker import NodeWorker
except ImportError:
    NodeWorker = None

__all__ = [
    "PeerDiscovery",
    "NodeManager",
    "WorkCreditsCalculator",
    "NodeEconomy",
    "NodeFlagSystem",
    "NodeVoteSystem",
    "NodePootValidation",
    "NodeOperatorSyncSystem",
    "NodePoolSystem",
    "NodeRegistrationProtocol",
    "ShardHostCreation",
    "ShardHostManagement",
    "NodeWorker"
]
