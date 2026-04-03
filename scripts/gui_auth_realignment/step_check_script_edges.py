#!/usr/bin/env python3
"""T6 GRAPH_TIERA: Tier A must not hardcode direct lucid-auth-service calls."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from lib.context import add_repo_root_arg, resolve_repo_root

FORBIDDEN = re.compile(r"lucid-auth-service", re.IGNORECASE)


def main() -> int:
    p = argparse.ArgumentParser()
    add_repo_root_arg(p)
    args = p.parse_args()
    repo = resolve_repo_root(args)
    roots = [
        repo / "gui_api_bridge" / "gui_api_bridge",
        repo / "gui_docker_manager" / "gui_docker_manager",
        repo / "gui_hardware_manager" / "gui_hardware_manager",
        repo / "gui_tor_manager" / "gui_tor_manager",
    ]
    bad = []
    for root in roots:
        if not root.is_dir():
            continue
        for py in root.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if FORBIDDEN.search(text):
                bad.append(str(py.relative_to(repo)))
    if bad:
        for b in bad:
            print(f"GRAPH_TIERA: suspicious reference in {b}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
