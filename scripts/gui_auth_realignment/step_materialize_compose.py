#!/usr/bin/env python3
"""T5: strip env_file for mat-listed services in docker-compose.gui-integration.yml."""

from __future__ import annotations

import argparse
from io import StringIO
from pathlib import Path

from lib.context import add_repo_root_arg, resolve_repo_root
from lib.mat import load_gui_mat, mat_services

try:
    from ruamel.yaml import YAML  # type: ignore
except ImportError:
    YAML = None  # type: ignore


def main() -> int:
    p = argparse.ArgumentParser()
    add_repo_root_arg(p)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    repo = resolve_repo_root(args)
    if YAML is None:
        print("ruamel.yaml required: pip install ruamel.yaml", flush=True)
        return 3

    mat_names = {r.get("compose_service") for r in mat_services(load_gui_mat(repo))}
    compose_path = repo / "configs" / "docker" / "docker-compose.gui-integration.yml"
    y = YAML()
    y.preserve_quotes = True
    data = y.load(compose_path.read_text(encoding="utf-8"))
    services = data.get("services") or {}
    for name in list(services.keys()):
        if name not in mat_names:
            continue
        block = services.get(name)
        if isinstance(block, dict) and "env_file" in block:
            del block["env_file"]
    buf = StringIO()
    y.dump(data, buf)
    out = buf.getvalue()
    if not args.dry_run:
        compose_path.write_text(out, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
