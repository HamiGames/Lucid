"""
RDP Session Controller Integration Clients

This module provides HTTP clients for integrating with session-recorder,
session-processor, and rdp-xrdp services.
"""

from .session_recorder_client import SessionRecorderClient
from .session_processor_client import SessionProcessorClient
from .xrdp_client import XRDPClient
from .integration_manager import IntegrationManager

__all__ = [
    'SessionRecorderClient',
    'SessionProcessorClient',
    'XRDPClient',
    'IntegrationManager'
]

