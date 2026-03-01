# node/flags/__init__.py
# Lucid Node Flags Module
# LUCID-STRICT Layer 1 Core Infrastructure

"""
Flags module for Lucid node operations.

This module provides:
- Node flag system management
- Flag creation, acknowledgment, and resolution
- Flag rules and automated flag generation
- Network-wide flag monitoring

Core Components:
- NodeFlagSystem: Main flag management system
- NodeFlag: Individual flag representation
- FlagRule: Flag generation rules
- FlagEvent: Flag lifecycle events
"""

from .node_flag_systems import (
    NodeFlagSystem,
    NodeFlag,
    FlagType,
    FlagSeverity,
    FlagStatus,
    FlagSource,
    FlagRule,
    FlagEvent,
    NodeFlagSummary,
    get_node_flag_system,
    create_node_flag_system,
    cleanup_node_flag_system
)

__all__ = [
    'NodeFlagSystem',
    'NodeFlag',
    'FlagType',
    'FlagSeverity',
    'FlagStatus',
    'FlagSource',
    'FlagRule',
    'FlagEvent',
    'NodeFlagSummary',
    'get_node_flag_system',
    'create_node_flag_system',
    'cleanup_node_flag_system'
]
