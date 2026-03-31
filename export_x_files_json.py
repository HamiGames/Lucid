"""
Build ``x-files.json`` from ``x-files-listing.txt`` for tooling / calibration.

Repository path: ``export_x_files_json.py`` (run from repository root).

Uses the same parsing rules as ``correct_py_paths_from_x_files_listing.py``.

Run::

    python export_x_files_json.py
    python export_x_files_json.py --out configs/x-files.json
    python export_x_files_json.py --listing path/to/x-files-listing.txt --out x-files.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from correct_py_paths_from_x_files_listing import (
    LISTING_NAME,
    REPO,
    listing_blocks_as_dicts,
    parse_listing_header_comment_paths,
    parse_x_files_listing,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Emit x-files.json from x-files-listing.txt")
    p.add_argument(
        "--listing",
        type=Path,
        default=REPO / LISTING_NAME,
        help="Path to x-files-listing.txt",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=REPO / "x-files.json",
        help="Output JSON path (default: ./x-files.json)",
    )
    p.add_argument(
        "--no-valid-dirs",
        action="store_true",
        help="Omit valid_app_dirs (smaller file)",
    )
    args = p.parse_args()

    listing_path = args.listing.resolve()
    if not listing_path.is_file():
        print(f"error: listing not found: {listing_path}")
        return 1

    raw = listing_path.read_text(encoding="utf-8")
    if raw.startswith("\ufeff"):
        raw = raw[1:]
    raw_n = raw.replace("\r\n", "\n")

    rel_to_canonical, valid_paths, valid_dirs = parse_x_files_listing(listing_path)
    entries = listing_blocks_as_dicts(listing_path)
    header_paths = sorted(parse_listing_header_comment_paths(raw_n))

    try:
        source_rel = str(listing_path.relative_to(REPO))
    except ValueError:
        source_rel = str(listing_path)

    payload: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_listing": source_rel,
        "section_to_canonical": dict(sorted(rel_to_canonical.items())),
        "header_comment_app_paths": header_paths,
        "valid_app_paths": sorted(valid_paths),
        "entries": entries,
    }
    if not args.no_valid_dirs:
        payload["valid_app_dirs"] = sorted(valid_dirs)

    out_path = args.out.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"wrote {out_path} ({len(entries)} blocks, "
        f"{len(rel_to_canonical)} section->canonical, {len(valid_paths)} valid paths)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
