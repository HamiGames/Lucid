"""
File: /app/server/launch_server.py
x-lucid-file-path: /app/server/launch_server.py
x-lucid-file-type: python

Start the uvicorn process with host-config-derived bind address.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from server.build_server import (
    ServerRuntime,
    apply_runtime_env,
    build_server_runtime,
    ensure_runtime_dirs,
)


@dataclass
class LaunchParams:
    app_import: str = "server.operators:app"
    log_level: str = "info"
    timeout_keep_alive: int = 5
    workers: int = 1


def launch_uvicorn(
    runtime: Optional[ServerRuntime] = None,
    role: Optional[str] = None,
    launch: Optional[LaunchParams] = None,
) -> None:
    import uvicorn

    lp = launch or LaunchParams()
    rt = runtime or build_server_runtime(role=role)
    apply_runtime_env(rt)
    ensure_runtime_dirs(rt)

    uvicorn.run(
        lp.app_import,
        host=rt.bind_host,
        port=rt.bind_port,
        log_level=lp.log_level,
        timeout_keep_alive=lp.timeout_keep_alive,
        workers=lp.workers,
    )


def launch_subprocess_argv(
    runtime: ServerRuntime,
    python_executable: Optional[str] = None,
) -> list[str]:
    """Build argv for ``python -m uvicorn`` (supervisor / systemd style)."""
    exe = python_executable or os.environ.get("LUCID_PYTHON", "python")
    return [
        exe,
        "-m",
        "uvicorn",
        "server.operators:app",
        "--host",
        runtime.bind_host,
        "--port",
        str(runtime.bind_port),
    ]
