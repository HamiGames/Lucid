#!/usr/bin/env python3
"""T0–T1: paths and model preflight for gui_auth_realignment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lib.context import add_repo_root_arg, resolve_repo_root, scripts_dir
from lib.anchors import load_host_config, service_port, ports_txt_has_port
from lib.mat import load_gui_mat, mat_services


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--phase", choices=("paths", "models"), required=True)
    add_repo_root_arg(p)
    args = p.parse_args()
    repo = resolve_repo_root(args)

    if args.phase == "paths":
        need = [
            repo / "ports.txt",
            repo / "infrastructure" / "containers" / "host-config.yml",
            repo / "configs" / "alignment-mats" / "gui-services.json",
            scripts_dir(repo) / "tier_a_json_targets.json",
            scripts_dir(repo) / "mapping_compose_to_service_id.json",
            scripts_dir(repo) / "gui_json_policy.json",
        ]
        for f in need:
            if not f.is_file():
                print(f"MISSING {f}", file=sys.stderr)
                return 2
        return 0

    # models phase
    try:
        hc = load_host_config(repo)
        mapping_path = scripts_dir(repo) / "mapping_compose_to_service_id.json"
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        mmap = mapping.get("mappings") or {}
        mat = load_gui_mat(repo)
        for row in mat_services(mat):
            cs = row.get("compose_service")
            if not cs:
                print("mat row missing compose_service", file=sys.stderr)
                return 2
            sid = mmap.get(cs)
            if not sid:
                print(f"unmapped compose_service: {cs}", file=sys.stderr)
                return 2
            port = service_port(hc, sid)
            if port and not ports_txt_has_port(repo, port):
                print(f"PORT_AGREE warn: {cs} -> {sid} port {port} not found in ports.txt scan", file=sys.stderr)
    except Exception as e:
        print(f"T1 failed: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
