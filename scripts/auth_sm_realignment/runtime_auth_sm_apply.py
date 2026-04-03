#!/usr/bin/env python3
"""
File: c:\\Users\\surba\\Desktop\\personal\\THE_FUCKER\\lucid_2\\Lucid\\scripts\\auth_sm_realignment\\runtime_auth_sm_apply.py
Chain subprocess steps: anchors → codegen contracts → compose env (optional --compose).
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo-root", type=Path, default=None)
    path = Path(__file__).resolve()
    lucid_try = path.parents[2]
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--compose", action="store_true", help="Run step_compose_auth_env.py after codegen")
    args, rest = p.parse_known_args()
    repo = (args.repo_root or lucid_try).resolve()
    here = Path(__file__).resolve().parent
    py = sys.executable
    env = {**os.environ, "PYTHONPATH": str(here)}

    steps = [
        [py, str(here / "step_verify_anchors.py"), "--repo-root", str(repo)],
        [py, str(here / "step_codegen_contracts.py"), "--repo-root", str(repo)],
    ]
    if args.compose:
        cmd = [py, str(here / "step_compose_auth_env.py"), "--repo-root", str(repo)]
        if args.dry_run:
            cmd.append("--dry-run")
        steps.append(cmd)
    elif args.dry_run:
        steps[1].append("--dry-run")

    for cmd in steps:
        cmd = cmd + rest
        r = subprocess.run(cmd, env=env)
        if r.returncode != 0:
            return r.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
