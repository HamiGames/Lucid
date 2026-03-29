"""
File: /app/server/run_server.py
x-lucid-file-path: /app/server/run_server.py
x-lucid-file-type: python

CLI entry: validate master-endpoint vs host-config, then run uvicorn.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from server.build_server import build_server_runtime, ensure_runtime_dirs
from server.host_context import (
    ROLE_MAIN_GATEWAY,
    load_server_bundle,
    validate_master_endpoint_registry,
)
from server.launch_server import LaunchParams, launch_uvicorn


def validate_mesh_alignment(
    host_config_path: Optional[str] = None,
    master_endpoint_path: Optional[str] = None,
) -> List[str]:
    bundle = load_server_bundle(
        host_config_path=host_config_path,
        master_endpoint_path=master_endpoint_path,
    )
    return validate_master_endpoint_registry(bundle)


def main(argv: Optional[list[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Lucid server pack — mesh validation + uvicorn")
    p.add_argument(
        "--skip-validation",
        action="store_true",
        help="Do not compare master-endpoint.yml services to host-config.yml",
    )
    p.add_argument(
        "--host-config",
        default=None,
        help="Override path to host-config.yml",
    )
    p.add_argument(
        "--master-endpoint",
        default=None,
        help="Override path to master-endpoint.yml",
    )
    p.add_argument("--role", default=None, help="lucid_server_manager | lucid_server_core | aliases")
    p.add_argument("--bind", default=None, help="Override bind host (else LUCID_SERVER_BIND_HOST or 0.0.0.0)")
    p.add_argument("--port", type=int, default=None, help="Override port (else LUCID_SERVER_PORT or host-config)")
    p.add_argument(
        "--app",
        default=None,
        metavar="IMPORT",
        help=(
            "Uvicorn app (module:attr). Default: app.api.app.main:app for main_lucid_gateway; "
            "else server.operators:app"
        ),
    )
    p.add_argument("--log-level", default="info", help="uvicorn log level")
    p.add_argument(
        "--validate-only",
        action="store_true",
        help="Run validation and exit (exit 0 if ok)",
    )
    args = p.parse_args(argv)

    if not args.skip_validation:
        errs = validate_mesh_alignment(
            host_config_path=args.host_config,
            master_endpoint_path=args.master_endpoint,
        )
        if errs:
            for line in errs:
                print(line, file=sys.stderr)
            sys.exit(1)

    if args.validate_only:
        return

    if args.master_endpoint:
        os.environ["LUCID_MASTER_ENDPOINT_PATH"] = args.master_endpoint
    if args.host_config:
        os.environ["LUCID_HOST_CONFIG_PATH"] = args.host_config

    runtime = build_server_runtime(
        role=args.role,
        host_config_path=args.host_config,
        bind_host=args.bind,
        bind_port=args.port,
    )
    ensure_runtime_dirs(runtime)
    app_import = args.app
    if app_import is None:
        app_import = (
            "app.api.app.main:app"
            if runtime.registry_key == ROLE_MAIN_GATEWAY
            else "server.operators:app"
        )
    launch_uvicorn(
        runtime=runtime,
        launch=LaunchParams(log_level=args.log_level, app_import=app_import),
    )


if __name__ == "__main__":
    main()
