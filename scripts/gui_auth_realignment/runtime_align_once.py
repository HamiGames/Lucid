#!/usr/bin/env python3
"""Chain T0–T8 subprocess steps for gui_auth_realignment."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(repo: Path, argv_extra: list, ci_check: bool) -> int:
    here = Path(__file__).resolve().parent
    py = sys.executable
    env = {**os.environ, "PYTHONPATH": str(here)}
    steps = [
        [py, str(here / "step_preflight.py"), "--repo-root", str(repo), "--phase", "paths"],
        [py, str(here / "step_preflight.py"), "--repo-root", str(repo), "--phase", "models"],
        [py, str(here / "step_scan_issues.py"), "--repo-root", str(repo)],
    ]
    if not ci_check:
        steps += [
            [py, str(here / "step_propose_alignment.py"), "--repo-root", str(repo)],
            [py, str(here / "step_materialize_gui_json.py"), "--repo-root", str(repo)],
            [py, str(here / "step_materialize_compose.py"), "--repo-root", str(repo)],
        ]
        steps.append([py, str(here / "step_scan_issues.py"), "--repo-root", str(repo), "--fail-on-issues"])
    else:
        steps += [[py, str(here / "step_scan_issues.py"), "--repo-root", str(repo), "--fail-on-issues"]]
    steps += [
        [py, str(here / "step_check_script_edges.py"), "--repo-root", str(repo)],
        [py, str(here / "step_check_called_services.py"), "--repo-root", str(repo)],
        [py, str(here / "step_verify_alignment.py"), "--repo-root", str(repo)],
    ]
    for cmd in steps:
        cmd = cmd + argv_extra
        r = subprocess.run(cmd, env=env)
        if r.returncode != 0:
            return r.returncode
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, default=None)
    p.add_argument("mode", nargs="?", default="run-all", choices=("run-all", "ci-check"))
    args, rest = p.parse_known_args()
    repo = args.repo_root.resolve() if args.repo_root else Path(__file__).resolve().parents[2]
    return run(repo, rest, ci_check=(args.mode == "ci-check"))


if __name__ == "__main__":
    raise SystemExit(main())
