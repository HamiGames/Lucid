"""
LUCID Node Components
Complete node management system including DHT/CRDT, consensus, economy, and more.
"""

# Core DHT/CRDT Components
from .dht_crdt import DHTCRDTNode, DHTNode, DHTEntry, CRDTEntry, GossipMessage, NodeStatus, MessageType

# Database and Peer Discovery
from .database_adapter import DatabaseAdapter, CollectionAdapter, get_database_adapter
from .peer_discovery import PeerDiscovery, PeerInfo

# Node Management
from .node_manager import NodeManager, NodeConfig, create_node_config

# Consensus Components
from .consensus import (
    LeaderSelection, LeaderSelectionMethod, ConsensusRole,
    TaskProofCollector, TaskType, ProofStatus, TaskStatus,
    UptimeBeaconSystem, BeaconStatus, BeaconType,
    WorkCreditsCalculator, WorkCreditType, WorkCreditStatus
)

# Economy Components
from .economy.node_economy import NodeEconomy, RevenueMetrics, PayoutRecord, EconomicStatus, PayoutStatus

# Flag System
from .flags.node_flag_systems import NodeFlagSystem, NodeFlag, FlagType, FlagSeverity, FlagStatus, FlagSource

# Governance Components
from .governance.node_vote_systems import (
    NodeVoteSystem, GovernanceProposal, ProposalType, ProposalStatus,
    GovernanceVote, VoteChoice, VoteWeight, VoteDelegation, VoteTally
)

# Pool Management
from .pools.node_pool_systems import (
    NodePoolSystem, NodePool, PoolStatus, MemberStatus, PoolRole,
    PoolMember, PoolConfiguration, JoinRequest, PoolSyncOperation
)

# Registration Protocol
from .registration.node_registration_protocol import (
    NodeRegistrationProtocol, NodeRegistration, RegistrationStatus,
    RegistrationChallenge, ChallengeType
)

# Shard Management
from .shards.shard_host_creation import (
    ShardHostCreationSystem, ShardInfo, ShardHost, HostStatus,
    ShardStatus, ShardCreationTask
)

from .shards.shard_host_management import (
    ShardHostManagementSystem, PerformanceMetrics, MaintenanceWindow,
    ShardIntegrityCheck, DataRepairOperation, MaintenanceType, OperationStatus
)

# Sync Systems
from .sync.node_operator_sync_systems import (
    NodeOperatorSyncSystem, OperatorInfo, OperatorRole, SyncStatus,
    SyncOperation, OperationType, StateCheckpoint, SyncConflict,
    ConflictType, OperatorMetrics
)

# Tor Components
from .tor import (
    OnionServiceManager, OnionServiceType, OnionKeyType, OnionServiceStatus,
    SocksProxyManager, SocksVersion, SocksAuthMethod, ProxyStatus,
    TorManager, TorServiceStatus, TorConnectionType
)

# Validation Systems
from .validation.node_poot_validations import (
    NodePootValidation, TokenOwnershipChallenge, TokenOwnershipProof,
    ProofType, ValidationStatus, StakeValidation, FraudDetectionEvent,
    FraudRisk, ValidationStats
)

# Worker Components
from .worker.node_worker import NodeWorker, RDPSession, SessionState, NodeStatus as WorkerNodeStatus, ResourceMetrics

# Work Credits (Legacy)
from .work_credits import WorkCreditsCalculator as LegacyWorkCreditsCalculator, WorkProof, WorkTally

__all__ = [
    # Core DHT/CRDT
    'DHTCRDTNode', 'DHTNode', 'DHTEntry', 'CRDTEntry', 'GossipMessage', 'NodeStatus', 'MessageType',
    
    # Database and Discovery
    'DatabaseAdapter', 'CollectionAdapter', 'get_database_adapter', 'PeerDiscovery', 'PeerInfo',
    
    # Node Management
    'NodeManager', 'NodeConfig', 'create_node_config',
    
    # Consensus
    'LeaderSelection', 'LeaderSelectionMethod', 'ConsensusRole',
    'TaskProofCollector', 'TaskType', 'ProofStatus', 'TaskStatus',
    'UptimeBeaconSystem', 'BeaconStatus', 'BeaconType',
    'WorkCreditsCalculator', 'WorkCreditType', 'WorkCreditStatus',
    
    # Economy
    'NodeEconomy', 'RevenueMetrics', 'PayoutRecord', 'EconomicStatus', 'PayoutStatus',
    
    # Flags
    'NodeFlagSystem', 'NodeFlag', 'FlagType', 'FlagSeverity', 'FlagStatus', 'FlagSource',
    
    # Governance
    'NodeVoteSystem', 'GovernanceProposal', 'ProposalType', 'ProposalStatus',
    'GovernanceVote', 'VoteChoice', 'VoteWeight', 'VoteDelegation', 'VoteTally',
    
    # Pools
    'NodePoolSystem', 'NodePool', 'PoolStatus', 'MemberStatus', 'PoolRole',
    'PoolMember', 'PoolConfiguration', 'JoinRequest', 'PoolSyncOperation',
    
    # Registration
    'NodeRegistrationProtocol', 'NodeRegistration', 'RegistrationStatus',
    'RegistrationChallenge', 'ChallengeType',
    
    # Shards
    'ShardHostCreationSystem', 'ShardInfo', 'ShardHost', 'HostStatus',
    'ShardStatus', 'ShardCreationTask', 'ShardHostManagementSystem',
    'PerformanceMetrics', 'MaintenanceWindow', 'ShardIntegrityCheck',
    'DataRepairOperation', 'MaintenanceType', 'OperationStatus',
    
    # Sync
    'NodeOperatorSyncSystem', 'OperatorInfo', 'OperatorRole', 'SyncStatus',
    'SyncOperation', 'OperationType', 'StateCheckpoint', 'SyncConflict',
    'ConflictType', 'OperatorMetrics',
    
    # Tor
    'OnionServiceManager', 'OnionServiceType', 'OnionKeyType', 'OnionServiceStatus',
    'SocksProxyManager', 'SocksVersion', 'SocksAuthMethod', 'ProxyStatus',
    'TorManager', 'TorServiceStatus', 'TorConnectionType',
    
    # Validation
    'NodePootValidation', 'TokenOwnershipChallenge', 'TokenOwnershipProof',
    'ProofType', 'ValidationStatus', 'StakeValidation', 'FraudDetectionEvent',
    'FraudRisk', 'ValidationStats',
    
    # Worker
    'NodeWorker', 'RDPSession', 'SessionState', 'WorkerNodeStatus', 'ResourceMetrics',
    
    # Legacy Work Credits
    'LegacyWorkCreditsCalculator', 'WorkProof', 'WorkTally'
]