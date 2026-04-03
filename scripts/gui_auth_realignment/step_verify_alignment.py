#!/usr/bin/env python3
"""T8: compose published host ports vs host-config mapping."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from lib.context import add_repo_root_arg, resolve_repo_root, scripts_dir
from lib.anchors import load_host_config, service_port
from lib.mat import load_gui_mat, mat_services

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore


def _published_ports(compose_text: str, service: str) -> list:
    # Find service block and ports: "pub:int"
    lines = compose_text.splitlines()
    in_svc = False
    indent_svc = 0
    ports = []
    for line in lines:
        if not in_svc:
            m = re.match(rf"^(\s*){re.escape(service)}:\s*$", line)
            if m:
                in_svc = True
                indent_svc = len(m.group(1))
            continue
        curr = len(line) - len(line.lstrip()) if line.strip() else indent_svc + 9
        if line.strip() and curr <= indent_svc and line.strip().endswith(":"):
            break
        m2 = re.match(r"^\s+-\s+\"(\d+):(\d+)\"", line)
        if m2:
            ports.append(int(m2.group(1)))
        m3 = re.match(r"^\s+-\s+'(\d+):(\d+)'", line)
        if m3:
            ports.append(int(m3.group(1)))
    return ports


def main() -> int:
    p = argparse.ArgumentParser()
    add_repo_root_arg(p)
    args = p.parse_args()
    repo = resolve_repo_root(args)
    if yaml is None:
        return 1
    mapping = json.loads((scripts_dir(repo) / "mapping_compose_to_service_id.json").read_text(encoding="utf-8"))
    mmap = mapping.get("mappings") or {}
    hc = load_host_config(repo)
    compose_path = repo / "configs" / "docker" / "docker-compose.gui-integration.yml"
    text = compose_path.read_text(encoding="utf-8")
    failed = False
    for row in mat_services(load_gui_mat(repo)):
        cs = row.get("compose_service")
        sid = mmap.get(cs)
        if not sid:
            continue
        anchor = service_port(hc, sid)
        pub = _published_ports(text, cs)
        if anchor and pub and anchor not in pub:
            print(f"PORT drift: {cs} publishes {pub} host-config {sid} has {anchor}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
