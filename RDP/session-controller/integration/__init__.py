"""
RDP Session Controller Integration Clients

This module provides HTTP clients for integrating with session-recorder,
session-processor, rdp-xrdp, rdp-server-manager, and rdp-monitor services.
"""

from .session_recorder_client import SessionRecorderClient
from .session_processor_client import SessionProcessorClient
from .xrdp_client import XRDPClient
from .rdp_server_manager_client import RDPServerManagerClient
from .rdp_monitor_client import RDPMonitorClient
from .integration_manager import IntegrationManager
from .service_base import ServiceClientBase, ServiceError, ServiceTimeoutError, ServiceNotFoundError

__all__ = [
    'SessionRecorderClient',
    'SessionProcessorClient',
    'XRDPClient',
    'RDPServerManagerClient',
    'RDPMonitorClient',
    'IntegrationManager',
    'ServiceClientBase',
    'ServiceError',
    'ServiceTimeoutError',
    'ServiceNotFoundError'
]

