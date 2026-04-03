#!/usr/bin/env python3
"""
File: c:\\Users\\surba\\Desktop\\personal\\THE_FUCKER\\lucid_2\\Lucid\\scripts\\auth_sm_realignment\\step_compose_auth_env.py
Patch configs/container/auth/docker-compose.auth.yml lucid-auth-service environment
for SERVER_MANAGEMENT_* (defaults align with host-config lucid_server_manager:8081).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from ruamel.yaml import YAML  # type: ignore
except ImportError:
    YAML = None  # type: ignore


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, required=True)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    repo = args.repo_root.resolve()
    compose_path = repo / "configs" / "container" / "auth" / "docker-compose.auth.yml"
    if not compose_path.is_file():
        print(f"I/O error: missing {compose_path}", file=sys.stderr)
        return 3
    if YAML is None:
        print("I/O error: ruamel.yaml required: pip install ruamel.yaml", file=sys.stderr)
        return 3

    yaml = YAML()
    yaml.preserve_quotes = True
    data = yaml.load(compose_path.read_text(encoding="utf-8"))
    services = data.get("services") or {}
    auth = services.get("lucid-auth-service")
    if not isinstance(auth, dict):
        print("compose error: lucid-auth-service not found", file=sys.stderr)
        return 3

    env = auth.get("environment")
    if env is None:
        env = []
        auth["environment"] = env
    if not isinstance(env, list):
        print("compose error: lucid-auth-service.environment must be a list", file=sys.stderr)
        return 3

    want = {
        "SERVER_MANAGEMENT_BASE_URL": "http://lucid-server-manager:8081",
        "SERVER_MANAGEMENT_VERIFY_PATH": "/app/auth/verify-login",
        "SERVER_MANAGEMENT_PREAUTH_VERIFY_PATH": "/app/auth/verify-preauth",
        "SERVER_MANAGEMENT_REGISTRY_PATH": "/app/registry/users",
        # JWT_SECRET_KEY: signing for auth token lease only (introspect); not shared with gateway by design.
    }
    keys_present = set()
    for i, item in enumerate(env):
        if isinstance(item, str) and "=" in item:
            k = item.split("=", 1)[0]
            keys_present.add(k)

    added = []
    for k, v in want.items():
        if k not in keys_present:
            env.append(f"{k}={v}")
            added.append(k)

    if args.dry_run:
        print("dry-run: would add env keys:", ", ".join(added) if added else "(none)")
        return 0

    if added:
        # ruamel round-trip write
        from io import StringIO

        buf = StringIO()
        yaml.dump(data, buf)
        compose_path.write_text(buf.getvalue(), encoding="utf-8")
        print("updated:", compose_path, "added:", added)
    else:
        print("no changes:", compose_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
