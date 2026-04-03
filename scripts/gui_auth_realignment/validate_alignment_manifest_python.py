#!/usr/bin/env python3
"""Validate .py paths listed in configs/alignment-mats/*_manifest.json (existence + syntax)."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
REPO = _HERE.parents[1]
MAT_DIR = REPO / "configs" / "alignment-mats"


def main() -> int:
    py_paths: dict[str, list[str]] = {}
    for mf in sorted(MAT_DIR.glob("*_manifest.json")):
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print("BAD JSON", mf.relative_to(REPO), e, file=sys.stderr)
            continue
        for p in data.get("py") or []:
            if not isinstance(p, str):
                continue
            p = p.replace("\\", "/")
            py_paths.setdefault(p, []).append(mf.name)

    unique = sorted(py_paths.keys())
    missing: list[str] = []
    for rel in unique:
        if not (REPO / rel).is_file():
            missing.append(rel)

    compile_fail: list[tuple[str, str]] = []
    for rel in unique:
        fp = REPO / rel
        if not fp.is_file():
            continue
        try:
            compile(fp.read_text(encoding="utf-8"), str(fp), "exec")
        except SyntaxError as e:
            compile_fail.append((rel, f"line {e.lineno}: {e.msg}"))

    print("=== Alignment manifest Python references ===")
    print(f"Unique py paths: {len(unique)}")
    print(f"Missing on disk: {len(missing)}")
    for m in missing:
        refs = ", ".join(py_paths[m][:5])
        extra = f" (+{len(py_paths[m]) - 5})" if len(py_paths[m]) > 5 else ""
        print(f"  MISSING  {m}  <- {refs}{extra}")

    print(f"Syntax errors: {len(compile_fail)}")
    for rel, msg in compile_fail:
        print(f"  SYNTAX  {rel}  {msg}")

    hc = REPO / "infrastructure/containers/host-config.yml"
    print()
    print("=== host-config.yml source_dockerfile ===")
    if not hc.is_file():
        print("  host-config.yml not found")
    else:
        text = hc.read_text(encoding="utf-8", errors="replace")
        df_paths = [p.strip() for p in re.findall(r"source_dockerfile:\s*(.+)", text)]
        dock_missing = [p for p in df_paths if not (REPO / p).is_file()]
        print(f"Entries: {len(df_paths)}")
        print(f"Missing Dockerfiles: {len(dock_missing)}")
        for m in dock_missing:
            print(f"  MISSING  {m}")
        roots = Counter()
        for p in df_paths:
            parts = p.split("/")
            if len(parts) >= 2:
                roots["/".join(parts[:2])] += 1
        print("Path root counts (first two segments):", dict(roots.most_common(12)))

    # infrastructure/docker vs infrastructure/containers mention
    in_cont = sum(1 for p in df_paths if p.startswith("infrastructure/containers/")) if hc.is_file() else 0
    in_dock = sum(1 for p in df_paths if p.startswith("infrastructure/docker/")) if hc.is_file() else 0
    print(f"host-config Dockerfiles under infrastructure/containers/: {in_cont}")
    print(f"host-config Dockerfiles under infrastructure/docker/: {in_dock}")

    return 1 if (missing or compile_fail or (hc.is_file() and dock_missing)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
