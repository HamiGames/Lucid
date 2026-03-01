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
import sys
import importlib.util
from pathlib import Path

# Get the parent directory (node/) and models.py file path
_parent_dir = Path(__file__).parent.parent
_models_file = _parent_dir / "models.py"

# Try multiple import strategies for maximum compatibility
_legacy_models = None

# Strategy 1: Direct file import using importlib
if _models_file.exists():
    try:
        _models_file_abs = str(_models_file.resolve())
        spec = importlib.util.spec_from_file_location("node_models_legacy", _models_file_abs)
        if spec is not None and spec.loader is not None:
            _legacy_models = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_legacy_models)
    except Exception:
        pass

# Strategy 2: Import via sys.path manipulation with explicit file import
if _legacy_models is None:
    try:
        _parent_dir_str = str(_parent_dir.resolve())
        # Temporarily remove 'models' from sys.modules to force file import
        _models_key = None
        if 'models' in sys.modules:
            _models_key = 'models'
            _temp_models = sys.modules.pop('models')
        
        if _parent_dir_str not in sys.path:
            sys.path.insert(0, _parent_dir_str)
        
        # Import the file explicitly using a unique name
        _models_spec = importlib.util.spec_from_file_location("node_models_file", str(_models_file))
        if _models_spec is not None and _models_spec.loader is not None:
            _legacy_models_module = importlib.util.module_from_spec(_models_spec)
            _models_spec.loader.exec_module(_legacy_models_module)
            _legacy_models = _legacy_models_module
        
        # Restore if needed
        if _models_key:
            sys.modules[_models_key] = _temp_models
    except Exception:
        pass

# Extract models from legacy module
if _legacy_models is None:
    raise ImportError(f"Could not import legacy models from {_models_file}. Tried multiple import strategies.")

NodeInfo = _legacy_models.NodeInfo
PoolInfo = _legacy_models.PoolInfo
PayoutInfo = _legacy_models.PayoutInfo
PoOTProof = _legacy_models.PoOTProof
NodeMetrics = _legacy_models.NodeMetrics
PoolMetrics = _legacy_models.PoolMetrics
PayoutStatistics = _legacy_models.PayoutStatistics
HealthCheck = _legacy_models.HealthCheck
ErrorResponse = _legacy_models.ErrorResponse
SuccessResponse = _legacy_models.SuccessResponse
ProofType = _legacy_models.ProofType
PoolStatus = _legacy_models.PoolStatus

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
