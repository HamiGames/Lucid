#!/usr/bin/env python3
"""
Lucid Session Pipeline Package
Main package for session processing pipeline management
"""

# Version information
__version__ = "1.0.0"

# Main classes and components
# Import order matters - import from most basic to most complex to avoid circular dependencies
# chunk processor
from sessions.pipeline.chunk_processor import (
    ChunkConfig,
    ChunkMetadata,
    ChunkProcessor
)

#MAIN
from sessions.pipeline.main import app

#merkle tree builder
from sessions.pipeline.merkle_tree_builder import (
    MerkleTreeConfig,
    MerkleNode,
    MerkleTreeBuilder
)

# State machine components (no dependencies on other pipeline modules)
from sessions.pipeline.state_machine import (
    PipelineState,
    StateTransition,
    StateTransitionRule,
    PipelineStateMachine,
)

# Configuration (depends on pydantic, no pipeline dependencies)
from sessions.pipeline.config import (
    WorkerConfig,
    StageConfig,
    PipelineSettings,
    PipelineConfig,
)

# Pipeline manager (depends on state_machine and config)
from sessions.pipeline.pipeline_manager import (
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
    "PipelineState","StateTransition",
    "StateTransitionRule", "PipelineStateMachine",
    # Main
    "app",
    # Chunk processor
    "ChunkConfig","ChunkMetadata","ChunkProcessor",
    # Configuration
    "WorkerConfig","StageConfig","PipelineSettings","PipelineConfig",
    # Pipeline manager
    "PipelineMetrics", "PipelineStage", "SessionPipeline", "PipelineManager",
    # Merkle tree builder
    "MerkleTreeConfig", "MerkleNode", "MerkleTreeBuilder",
]
