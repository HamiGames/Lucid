# node/flags/__init__.py
# Lucid Node Flags Module
# LUCID-STRICT Layer 1 Core Infrastructure

"""
File: /app/node/flags/__init__.py
x-lucid-file-path: /app/node/flags/__init__.py
x-lucid-file-type: python

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

from ..flags.node_flag_systems import (
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
