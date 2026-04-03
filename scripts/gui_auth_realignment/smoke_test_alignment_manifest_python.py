#!/usr/bin/env python3
"""
File: scripts/gui_auth_realignment/smoke_test_alignment_manifest_python.py

Smoke-test every .py path listed under \"py\" in configs/alignment-mats/*_manifest.json.

Modes:
  default (byte-compile):
    Runs the same check as `python -m py_compile <file>` per path (subprocess, CWD=repo root).
    Verifies the interpreter can parse/compile each file without executing top-level imports.

  --exec-top-level:
    Executes each file via runpy.run_path(..., __name__='__smoke__').
    Expect failures for package modules (relative imports), optional deps not installed, or
    name clashes (e.g. admin.utils.logging vs stdlib logging). Use a fully provisioned venv +
    the same PYTHONPATH your apps use if you rely on this mode.

Usage (repo root):
  python scripts/gui_auth_realignment/smoke_test_alignment_manifest_python.py
  python scripts/gui_auth_realignment/smoke_test_alignment_manifest_python.py --python .venv\\Scripts\\python.exe
  python scripts/gui_auth_realignment/smoke_test_alignment_manifest_python.py --exec-top-level --timeout 25
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
REPO = _HERE.parents[1]
MAT_DIR = REPO / "configs" / "alignment-mats"

RUNNER = r"""
import runpy
import sys
path = sys.argv[1]
runpy.run_path(path, init_globals={"__name__": "__smoke__"})
"""


def collect_py_paths() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for mf in sorted(MAT_DIR.glob("*_manifest.json")):
        data = json.loads(mf.read_text(encoding="utf-8"))
        for p in data.get("py") or []:
            if not isinstance(p, str):
                continue
            p = p.replace("\\", "/")
            out.setdefault(p, []).append(mf.name)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Smoke-test Python files from alignment manifests.")
    ap.add_argument("--timeout", type=float, default=15.0, help="Subprocess timeout for --exec-top-level (default 15)")
    ap.add_argument(
        "--exec-top-level",
        action="store_true",
        help="Run each file with run_path (__smoke__); many files may fail without package context / deps",
    )
    ap.add_argument(
        "--python",
        default=None,
        help="Python executable to use (default: current interpreter)",
    )
    args = ap.parse_args()
    py_exe = args.python or sys.executable

    py_map = collect_py_paths()
    unique = sorted(py_map.keys())
    missing = [p for p in unique if not (REPO / p).is_file()]

    print(f"Manifests scanned: {len(list(MAT_DIR.glob('*_manifest.json')))}")
    print(f"Unique py paths: {len(unique)}")
    print(f"Python: {py_exe}")
    if args.exec_top_level:
        print("Mode: exec-top-level (run_path, __name__=__smoke__)")
    else:
        print("Mode: byte-compile (python -m py_compile)")

    if missing:
        print("Missing files:", len(missing))
        for m in missing:
            print(f"  {m}")
        return 1

    failures: list[tuple[str, str]] = []

    for i, rel in enumerate(unique, 1):
        fp = (REPO / rel).resolve()
        if not args.exec_top_level:
            proc = subprocess.run(
                [py_exe, "-m", "py_compile", str(fp)],
                cwd=str(REPO),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if proc.returncode != 0:
                tail = (proc.stderr or proc.stdout or "").strip()
                failures.append((rel, f"py_compile exit {proc.returncode}\n{tail}"))
        else:
            proc = subprocess.run(
                [py_exe, "-c", RUNNER, str(fp)],
                cwd=str(REPO),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=args.timeout,
            )
            if proc.returncode != 0:
                tail = (proc.stderr or proc.stdout or "").strip()
                if len(tail) > 2000:
                    tail = tail[-2000:]
                failures.append((rel, f"exit {proc.returncode}\n{tail}"))

        if i % 40 == 0 or i == len(unique):
            print(f"  ... {i}/{len(unique)}", flush=True)

    print()
    if failures:
        print(f"FAILURES: {len(failures)}")
        for rel, msg in failures:
            print(f"--- {rel} ---")
            print(msg)
            print()
        return 1

    print(f"OK: all {len(unique)} files passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
