#!/usr/bin/env python3
"""
Lucid Session Pipeline Package
Main package for session processing pipeline management
"""

# Version information
__version__ = "1.0.0"

# Main classes and components
# Import order matters - import from most basic to most complex to avoid circular dependencies

# State machine components (no dependencies on other pipeline modules)
from .state_machine import (
    PipelineState,
    StateTransition,
    StateTransitionRule,
    PipelineStateMachine,
)

# Configuration (depends on pydantic, no pipeline dependencies)
from .config import (
    WorkerConfig,
    StageConfig,
    PipelineSettings,
    PipelineConfig,
)

# Pipeline manager (depends on state_machine and config)
from .pipeline_manager import (
    PipelineMetrics,
    PipelineStage,
    SessionPipeline,
    PipelineManager,
)

# Make main components available at package level
__all__ = [
    # Version
    "__version__",
    # State machine
    "PipelineState",
    "StateTransition",
    "StateTransitionRule",
    "PipelineStateMachine",
    # Configuration
    "WorkerConfig",
    "StageConfig",
    "PipelineSettings",
    "PipelineConfig",
    # Pipeline manager
    "PipelineMetrics",
    "PipelineStage",
    "SessionPipeline",
    "PipelineManager",
]
