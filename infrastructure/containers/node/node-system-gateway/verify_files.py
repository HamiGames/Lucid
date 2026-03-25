#!/usr/bin/env python3
"""Builder-stage file checks for node-system-gateway (aligned with 03_api_gateway/verify_files.py)."""
import os
import sys

ROOT = "/build/node"
required_files = [
    f"{ROOT}/config/node-system-gateway.connections.json",
    f"{ROOT}/config/openssl-api.yml",
    f"{ROOT}/node_system_gateway_entrypoint.py",
]

for path in required_files:
    if not os.path.isfile(path):
        print(f"ERROR: missing {path}", file=sys.stderr)
        sys.exit(1)
    if os.path.getsize(path) <= 0:
        print(f"ERROR: empty {path}", file=sys.stderr)
        sys.exit(1)

print("node-system-gateway: all required files present")
