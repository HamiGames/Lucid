# node/consensus/__init__.py
# Lucid Node Consensus Module
# LUCID-STRICT Layer 1 Core Infrastructure

"""
Consensus module for Lucid node operations.

This module provides:
- Leader selection algorithms
- Task proof collection and verification
- Uptime beacon system
- Work credits calculation

Core Components:
- LeaderSelection: Distributed leader selection for consensus protocols
- TaskProofCollector: Task proof collection and verification system
- UptimeBeaconSystem: Uptime monitoring and beacon system
- WorkCreditsCalculator: Work credits calculation and management
"""

from .leader_selection import (
    LeaderSelection,
    LeaderSelectionMethod,
    ConsensusRole,
    NodeStatus,
    NodeInfo,
    LeaderSelectionResult,
    ConsensusRound,
    initialize_leader_selection,
    start_consensus_process,
    get_current_leader,
    is_current_leader,
    get_network_status
)

from .task_proofs import (
    TaskProofCollector,
    TaskType,
    ProofStatus,
    TaskStatus,
    TaskProof,
    ConsensusTask,
    ProofVerificationResult,
    initialize_task_proof_collector,
    create_task,
    submit_proof,
    get_task_status,
    get_proof_statistics
)

from .uptime_beacon import (
    UptimeBeaconSystem,
    BeaconStatus,
    BeaconType,
    UptimeBeacon,
    UptimeMetrics,
    BeaconRequest,
    BeaconResponse,
    send_beacon,
    get_uptime_metrics,
    get_beacon_history,
    get_node_ranking
)

from .work_credits import (
    WorkCreditsCalculator,
    WorkCreditType,
    WorkCreditStatus,
    WorkCredit,
    WorkCreditProof,
    WorkCreditRequest,
    WorkCreditResponse,
    calculate_work_credits,
    get_work_credits,
    get_credit_balance,
    get_credit_ranking
)

__all__ = [
    # Leader Selection
    'LeaderSelection',
    'LeaderSelectionMethod',
    'ConsensusRole',
    'NodeStatus',
    'NodeInfo',
    'LeaderSelectionResult',
    'ConsensusRound',
    'initialize_leader_selection',
    'start_consensus_process',
    'get_current_leader',
    'is_current_leader',
    'get_network_status',
    
    # Task Proofs
    'TaskProofCollector',
    'TaskType',
    'ProofStatus',
    'TaskStatus',
    'TaskProof',
    'ConsensusTask',
    'ProofVerificationResult',
    'initialize_task_proof_collector',
    'create_task',
    'submit_proof',
    'get_task_status',
    'get_proof_statistics',
    
    # Uptime Beacon
    'UptimeBeaconSystem',
    'BeaconStatus',
    'BeaconType',
    'UptimeBeacon',
    'UptimeMetrics',
    'BeaconRequest',
    'BeaconResponse',
    'send_beacon',
    'get_uptime_metrics',
    'get_beacon_history',
    'get_node_ranking',
    
    # Work Credits
    'WorkCreditsCalculator',
    'WorkCreditType',
    'WorkCreditStatus',
    'WorkCredit',
    'WorkCreditProof',
    'WorkCreditRequest',
    'WorkCreditResponse',
    'calculate_work_credits',
    'get_work_credits',
    'get_credit_balance',
    'get_credit_ranking'
]
