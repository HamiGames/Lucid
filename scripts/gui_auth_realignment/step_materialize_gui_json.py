#!/usr/bin/env python3
"""T4: write GUI JSON files from proposed_alignment.json."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

from lib.context import add_repo_root_arg, resolve_repo_root, scripts_dir


def main() -> int:
    p = argparse.ArgumentParser()
    add_repo_root_arg(p)
    p.add_argument("--from", dest="from_file", default=".cache/proposed_alignment.json")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--backup", action="store_true")
    args = p.parse_args()
    repo = resolve_repo_root(args)
    prop_path = scripts_dir(repo) / args.from_file
    if not prop_path.is_file():
        return 3
    proposal = json.loads(prop_path.read_text(encoding="utf-8"))
    for item in proposal.get("json_files") or []:
        rel = item.get("path")
        body = item.get("full_body")
        if not rel or body is None:
            continue
        dest = repo / rel
        if args.backup and dest.is_file():
            bak = dest.with_suffix(dest.suffix + f".bak.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
            shutil.copy2(dest, bak)
        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
