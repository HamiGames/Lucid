#!/usr/bin/env python3
"""Align Dockerfile service metadata using infrastructure/containers/config-listings.json."""

from __future__ import annotations

import argparse
from pathlib import Path

from dockerfile_alignment import align_dockerfile_text, load_alignment_criteria, normalize_repo_rel


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def discover_dockerfiles(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for pattern in ("Dockerfile*", "dockerfile*"):
            for p in root.rglob(pattern):
                if not p.is_file():
                    continue
                rp = p.resolve()
                if rp in seen:
                    continue
                seen.add(rp)
                found.append(rp)
    return sorted(found, key=lambda p: str(p).lower())


def main() -> int:
    root = repo_root_from_here()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--config",
        default="infrastructure/containers/config-listings.json",
        help="Alignment config path (repo-relative or absolute).",
    )
    ap.add_argument(
        "--scan-root",
        action="append",
        default=["infrastructure/containers", "infrastructure/docker"],
        help="Dockerfile scan roots (repeatable).",
    )
    ap.add_argument("--apply", action="store_true", help="Write updated Dockerfiles.")
    args = ap.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = (root / config_path).resolve()
    if not config_path.is_file():
        raise SystemExit(f"error: config not found: {config_path}")

    criteria_by_file = load_alignment_criteria(config_path)
    scan_roots: list[Path] = []
    for r in args.scan_root:
        rp = Path(r)
        if not rp.is_absolute():
            rp = (root / rp).resolve()
        scan_roots.append(rp)

    dockerfiles = discover_dockerfiles(scan_roots)
    changed = 0
    matched = 0
    for df in dockerfiles:
        rel = normalize_repo_rel(str(df.relative_to(root)))
        criteria = criteria_by_file.get(rel)
        if criteria is None:
            continue
        matched += 1
        text = df.read_text(encoding="utf-8", errors="replace")
        new_text, did_change = align_dockerfile_text(text, criteria)
        if not did_change:
            continue
        changed += 1
        if args.apply:
            df.write_text(new_text, encoding="utf-8", newline="\n")
            print(f"updated: {rel}")
        else:
            print(f"[dry-run] would update: {rel}")

    mode = "changed" if args.apply else "would change"
    print(f"done: {changed} file(s) {mode}, {matched} matched config entries")
    if not args.apply and changed > 0:
        print("note: rerun with --apply to write changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
