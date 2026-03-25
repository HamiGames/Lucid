#!/usr/bin/env python3
"""Builder-stage checks for chain-to-pay gateway."""
import os
import sys

ROOT = "/build/chain"
required_files = [
    f"{ROOT}/config/chain-to-pay.connections.json",
    f"{ROOT}/config/openssl-api.yml",
    f"{ROOT}/chain_to_pay_entrypoint.py",
]

for path in required_files:
    if not os.path.isfile(path):
        print(f"ERROR: missing {path}", file=sys.stderr)
        sys.exit(1)
    if os.path.getsize(path) <= 0:
        print(f"ERROR: empty {path}", file=sys.stderr)
        sys.exit(1)

print("chain-to-pay: all required files present")
