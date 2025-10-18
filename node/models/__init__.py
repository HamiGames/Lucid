# Path: node/models/__init__.py
# Lucid Node Management Models Package
# Based on LUCID-STRICT requirements per Spec-1c

"""
Lucid Node Management Data Models Package

This package provides Pydantic models for:
- Node management and configuration
- Pool management and assignment
- Resource monitoring and metrics
- PoOT (Proof of Output) validation
- Payout processing and tracking

All models follow the API specification requirements.
"""

from .node import (
    Node, NodeCreateRequest, NodeUpdateRequest,
    NodeStatus, NodeType, HardwareInfo, NodeLocation,
    NodeConfiguration, ResourceLimits
)
from .pool import (
    NodePool, NodePoolCreateRequest, NodePoolUpdateRequest,
    ScalingPolicy, AutoScalingConfig
)
from .payout import (
    Payout, PayoutRequest, BatchPayoutRequest,
    PayoutStatus, PayoutPriority, Currency
)

__all__ = [
    # Node models
    "Node", "NodeCreateRequest", "NodeUpdateRequest",
    "NodeStatus", "NodeType", "HardwareInfo", "NodeLocation",
    "NodeConfiguration", "ResourceLimits",
    
    # Pool models
    "NodePool", "NodePoolCreateRequest", "NodePoolUpdateRequest",
    "ScalingPolicy", "AutoScalingConfig",
    
    # Payout models
    "Payout", "PayoutRequest", "BatchPayoutRequest",
    "PayoutStatus", "PayoutPriority", "Currency"
]

__version__ = "1.0.0"
__author__ = "Lucid Development Team"
__description__ = "Lucid Node Management Data Models"
