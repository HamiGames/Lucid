"""
File: /app/server/build_server.py
x-lucid-file-path: /app/server/build_server.py
x-lucid-file-type: python

Assemble server process paths, environment, and bound port from host-config.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Mapping, Optional

from common.load_host_config import (
    ServiceEndpoint,
    default_host_config_path,
    load_host_registry,
)

from server.host_context import (
    ROLE_LUCID_SERVER_MANAGER,
    endpoint_for_registry_key,
    resolve_role_registry_key,
)

ENV_SERVER_ROLE = "LUCID_SERVER_ROLE"
ENV_SERVER_HOST = "LUCID_SERVER_BIND_HOST"
ENV_SERVER_PORT = "LUCID_SERVER_PORT"


@dataclass
class ServerPaths:
    config_file: Optional[Path] = None
    log_file: Optional[Path] = None
    pid_file: Optional[Path] = None
    socket_file: Optional[Path] = None
    workdir: Optional[Path] = None


@dataclass
class ServerRuntime:
    registry_key: str
    endpoint: ServiceEndpoint
    bind_host: str
    bind_port: int
    paths: ServerPaths
    env: Dict[str, str] = field(default_factory=dict)
    user: Optional[str] = None
    group: Optional[str] = None


def _pick_paths_from_env() -> ServerPaths:
    def p(name: str) -> Optional[Path]:
        v = os.environ.get(name, "").strip()
        return Path(v) if v else None

    return ServerPaths(
        config_file=p("LUCID_SERVER_CONFIG_FILE"),
        log_file=p("LUCID_SERVER_LOG_FILE"),
        pid_file=p("LUCID_SERVER_PID_FILE"),
        socket_file=p("LUCID_SERVER_SOCKET_FILE"),
        workdir=p("LUCID_SERVER_WORKDIR"),
    )


def build_server_runtime(
    role: Optional[str] = None,
    host_config_path: Optional[Path | str] = None,
    bind_host: Optional[str] = None,
    bind_port: Optional[int] = None,
) -> ServerRuntime:
    rkey = resolve_role_registry_key(
        role or os.environ.get(ENV_SERVER_ROLE, ROLE_LUCID_SERVER_MANAGER)
    )
    hc = Path(host_config_path) if host_config_path else default_host_config_path()
    _, registry = load_host_registry(hc)
    ep = endpoint_for_registry_key(registry, rkey)

    host = (bind_host or os.environ.get(ENV_SERVER_HOST) or "0.0.0.0").strip()
    port = bind_port
    if port is None:
        env_p = os.environ.get(ENV_SERVER_PORT, "").strip()
        port = int(env_p) if env_p else ep.port

    base_env = {
        ENV_SERVER_ROLE: rkey,
        ENV_SERVER_HOST: host,
        ENV_SERVER_PORT: str(port),
        "LUCID_HOST_CONFIG_PATH": str(hc),
    }
    extra = {k: v for k, v in os.environ.items() if k.startswith("LUCID_")}
    merged = {**extra, **base_env}

    return ServerRuntime(
        registry_key=rkey,
        endpoint=ep,
        bind_host=host,
        bind_port=port,
        paths=_pick_paths_from_env(),
        env=merged,
        user=os.environ.get("LUCID_SERVER_USER"),
        group=os.environ.get("LUCID_SERVER_GROUP"),
    )


def apply_runtime_env(runtime: ServerRuntime) -> None:
    os.environ.update(runtime.env)


def ensure_runtime_dirs(runtime: ServerRuntime) -> None:
    for p in (runtime.paths.log_file, runtime.paths.pid_file, runtime.paths.socket_file):
        if p and p.parent and not p.parent.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
    if runtime.paths.workdir:
        runtime.paths.workdir.mkdir(parents=True, exist_ok=True)
