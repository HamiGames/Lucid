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

# Import legacy models from node.models (models.py file)
# These models are still used by various parts of the codebase
import importlib.util
from pathlib import Path

# Import from parent directory's models.py file
_parent_dir = Path(__file__).parent.parent
_models_file = _parent_dir / "models.py"
if _models_file.exists():
    spec = importlib.util.spec_from_file_location("node_models_legacy", _models_file)
    legacy_models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy_models)
    
    # Extract models from legacy module
    NodeInfo = legacy_models.NodeInfo
    PoolInfo = legacy_models.PoolInfo
    PayoutInfo = legacy_models.PayoutInfo
    PoOTProof = legacy_models.PoOTProof
    NodeMetrics = legacy_models.NodeMetrics
    PoolMetrics = legacy_models.PoolMetrics
    PayoutStatistics = legacy_models.PayoutStatistics
    HealthCheck = legacy_models.HealthCheck
    ErrorResponse = legacy_models.ErrorResponse
    SuccessResponse = legacy_models.SuccessResponse
    ProofType = legacy_models.ProofType
    PoolStatus = legacy_models.PoolStatus
else:
    raise ImportError(f"Could not find models.py at {_models_file}")

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
    "PayoutStatus", "PayoutPriority", "Currency",
    
    # Legacy models (from models.py)
    "NodeInfo", "PoolInfo", "PayoutInfo",
    "PoOTProof", "NodeMetrics", "PoolMetrics",
    "PayoutStatistics", "HealthCheck", "ErrorResponse",
    "SuccessResponse", "ProofType", "PoolStatus"
]

__version__ = "1.0.0"
__author__ = "Lucid Development Team"
__description__ = "Lucid Node Management Data Models"
