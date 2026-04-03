#!/usr/bin/env python3
"""T7: mat Tier A compose must not depend_on lucid-auth-service."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib.context import add_repo_root_arg, resolve_repo_root
from lib.mat import load_gui_mat, mat_services

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore


def _depends(block):
    d = block.get("depends_on") if isinstance(block, dict) else None
    if d is None:
        return []
    if isinstance(d, dict):
        return list(d.keys())
    if isinstance(d, list):
        return list(d)
    return []


def main() -> int:
    p = argparse.ArgumentParser()
    add_repo_root_arg(p)
    args = p.parse_args()
    repo = resolve_repo_root(args)
    if yaml is None:
        print("PyYAML required", file=sys.stderr)
        return 1
    path = repo / "configs" / "docker" / "docker-compose.gui-integration.yml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    mat_names = {r.get("compose_service") for r in mat_services(load_gui_mat(repo))}
    services = (data or {}).get("services") or {}
    failed = False
    for name, block in services.items():
        if name not in mat_names:
            continue
        for dep in _depends(block):
            if dep == "lucid-auth-service":
                print(f"CALLED_SERVICES: {name} must not depends_on lucid-auth-service", file=sys.stderr)
                failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
