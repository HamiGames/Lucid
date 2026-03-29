"""
File: /app/server/__init__.py
x-lucid-file-path: /app/server/__init__.py
x-lucid-file-type: python

Server module pack: host-config discovery, mesh validation, uvicorn launch.
"""

from server.build_server import ServerPaths, ServerRuntime, build_server_runtime
from server.host_context import (
    ROLE_LUCID_SERVER_CORE,
    ROLE_LUCID_SERVER_MANAGER,
    ROLE_MAIN_GATEWAY,
    ServerHostBundle,
    default_master_endpoint_path,
    load_server_bundle,
    validate_master_endpoint_registry,
)
from server.launch_server import LaunchParams, launch_subprocess_argv, launch_uvicorn
from server.operators import OperatorAck, OperatorPayload, app, create_app

__all__ = [
    "ROLE_LUCID_SERVER_CORE",
    "ROLE_LUCID_SERVER_MANAGER",
    "ROLE_MAIN_GATEWAY",
    "LaunchParams",
    "OperatorAck",
    "OperatorPayload",
    "ServerHostBundle",
    "ServerPaths",
    "ServerRuntime",
    "app",
    "build_server_runtime",
    "create_app",
    "default_master_endpoint_path",
    "launch_subprocess_argv",
    "launch_uvicorn",
    "load_server_bundle",
    "validate_master_endpoint_registry",
]
