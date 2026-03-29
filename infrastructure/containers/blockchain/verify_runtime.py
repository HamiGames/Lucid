#!/usr/bin/env python3
"""Build-time layout check for distroless blockchain images (engine + consensus-engine)."""
from __future__ import annotations

import os
import sys

# Layout produced by Dockerfile.engine (flattened blockchain tree under /app).
ENGINE_DIRS: tuple[str, ...] = (
    "/app/api",
    "/app/core",
    "/app/utils",
    "/app/config",
    "/app/contracts",
    "/app/deployment",
    "/app/chain_client",
    "/app/evm",
    "/app/on_system_chain",
    "/app/scripts",
    "/app/tests",
    "/app/configs",
)

# Additional paths only in Dockerfile.consensus-engine.
CONSENSUS_EXTRA_DIRS: tuple[str, ...] = (
    "/app/blockchain",
    "/app/sessions",
    "/app/node",
    "/app/RDP",
    "/app/admin",
    "/app/database",
    "/app/security",
    "/app/server",
    "/app/storage",
    "/app/user",
    "/app/payment_systems",
    "/app/service_configs",
)

REQUIRED_FILES: tuple[str, ...] = (
    "/app/api/app/entrypoint.py",
    "/app/api/app/main.py",
)


def main() -> int:
    variant = os.environ.get("LUCID_RUNTIME_VERIFY_VARIANT", "engine").strip().lower()
    if variant not in ("engine", "consensus"):
        print(
            f"verify_runtime: LUCID_RUNTIME_VERIFY_VARIANT must be 'engine' or 'consensus', got {variant!r}",
            file=sys.stderr,
        )
        return 1

    dirs = list(ENGINE_DIRS)
    if variant == "consensus":
        dirs.extend(CONSENSUS_EXTRA_DIRS)

    missing_dirs = [d for d in dirs if not os.path.isdir(d)]
    if missing_dirs:
        print("verify_runtime: missing directories:", file=sys.stderr)
        for d in missing_dirs:
            print(f"  - {d}", file=sys.stderr)
        return 1

    missing_files = [f for f in REQUIRED_FILES if not os.path.isfile(f)]
    if missing_files:
        print("verify_runtime: missing files:", file=sys.stderr)
        for f in missing_files:
            print(f"  - {f}", file=sys.stderr)
        return 1

    print(f"verify_runtime OK ({variant}): {len(dirs)} directories, {len(REQUIRED_FILES)} required files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
