#!/usr/bin/env python3
"""Distroless runtime verification for chain-to-pay."""
import json
import os
import sys

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore

dirs = [
    "/app/chain",
    "/app/chain/config",
    "/app/usr/local/lib/python3.11/site-packages",
    "/app/wheels",
]

for d in dirs:
    if not os.path.isdir(d):
        print(f"ERROR: {d} missing", file=sys.stderr)
        sys.exit(1)
    if not os.listdir(d):
        print(f"ERROR: {d} empty", file=sys.stderr)
        sys.exit(1)

conn = "/app/chain/config/chain-to-pay.connections.json"
yaml_path = "/app/chain/config/openssl-api.yml"
entry = "/app/chain/chain_to_pay_entrypoint.py"

for path in (conn, yaml_path, entry):
    if not os.path.isfile(path):
        print(f"ERROR: {path} missing", file=sys.stderr)
        sys.exit(1)

with open(conn, encoding="utf-8") as f:
    doc = json.load(f)
if not isinstance(doc.get("routes"), list) or not doc["routes"]:
    print("ERROR: connections.json must contain non-empty routes", file=sys.stderr)
    sys.exit(1)

if yaml is None:
    print("ERROR: PyYAML not importable", file=sys.stderr)
    sys.exit(1)

with open(yaml_path, encoding="utf-8") as f:
    ydoc = yaml.safe_load(f)
if not isinstance(ydoc, dict):
    print("ERROR: openssl-api.yml must parse to a mapping", file=sys.stderr)
    sys.exit(1)

print("chain-to-pay runtime layout OK")
