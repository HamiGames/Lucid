# Path: node/__init__.py
"""
Node system package for Lucid RDP.
Implements peer discovery, metadata syncing, and node management components.
"""

from node.peer_discovery import PeerDiscovery
from node.metadata_sync import MetadataSync
from node.node_manager import NodeManager
from node.work_credits import WorkCreditsCalculator
from node.consensus_manager import ConsensusManager

__all__ = [
    "PeerDiscovery",
    "MetadataSync", 
    "NodeManager",
    "WorkCreditsCalculator",
    "ConsensusManager"
]