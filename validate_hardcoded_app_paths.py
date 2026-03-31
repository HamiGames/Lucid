"""
Scan the repository for hardcoded ``/app/...`` paths and check them against ``x-files.json``.

Repository path: ``validate_hardcoded_app_paths.py`` (run from repository root).

Uses ``valid_app_paths`` / ``valid_app_dirs`` from ``x-files.json``, plus canonical paths from
``section_to_canonical`` values and ``header_comment_app_paths`` (same calibration family as
``correct_py_paths_from_x_files_listing.py``). JSON is read as UTF-8 with BOM stripped
(``utf-8-sig``). Scan files that are not UTF-8 are skipped. Optionally verifies listing
``section`` paths exist on disk.

Run::

    python export_x_files_json.py
    python validate_hardcoded_app_paths.py
    python validate_hardcoded_app_paths.py --section-exists

Requires an up-to-date ``x-files.json`` (regenerate after ``x-files-listing.txt`` changes).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

REPO = Path(__file__).resolve().parent

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "dist",
        "build",
        ".eggs",
    }
)

# Same character class as correct_py_paths_from_x_files_listing (header comments).
RE_APP_PATH = re.compile(r"/app/[A-Za-z0-9_./@-]+")

# Files / patterns to skip scanning (content is calibration or huge generated text).
SKIP_SCAN_NAMES = frozenset(
    {
        "x-files.json",
        "x-files-listing.txt",
    }
)

TEXT_SUFFIXES = frozenset(
    {
        ".py",
        ".sh",
        ".bash",
        ".yml",
        ".yaml",
        ".md",
        ".toml",
        ".env",
        ".template",
        ".txt",
        ".json",
        ".gradle",
        ".properties",
        ".xml",
        ".sql",
        ".http",
        ".graphql",
    }
)


def _strip_trailing_punct(p: str) -> str:
    return p.rstrip(").,;\"'")

def _is_valid_app_path(path: str, valid_paths: set[str], valid_dirs: set[str]) -> bool:
    """Match correct_py_paths_from_x_files_listing._is_valid_app_path."""
    p = path.rstrip("/")
    if p in valid_paths:
        return True
    if p in valid_dirs:
        return True
    if any(f.startswith(p + "/") for f in valid_paths):
        return True
    return False


def _build_valid_dirs_from_paths(valid_paths: Iterable[str]) -> set[str]:
    dirs: set[str] = set()
    for p in valid_paths:
        if not p.startswith("/app/"):
            continue
        parts = p.strip("/").split("/")
        for n in range(1, len(parts)):
            dirs.add("/" + "/".join(parts[:n]))
    return dirs


def _load_calibration(json_path: Path) -> tuple[set[str], set[str], dict[str, str]]:
    raw = json_path.read_text(encoding="utf-8-sig")
    data = json.loads(raw)
    paths = set(data.get("valid_app_paths") or [])
    section_map = dict(data.get("section_to_canonical") or {})
    for v in section_map.values():
        if isinstance(v, str) and v.startswith("/app/"):
            paths.add(v)
    for h in data.get("header_comment_app_paths") or []:
        if isinstance(h, str) and h.startswith("/app/"):
            paths.add(h)
    dirs = set(data.get("valid_app_dirs") or [])
    dirs |= _build_valid_dirs_from_paths(paths)
    return paths, dirs, section_map


def _should_scan_file(path: Path, repo: Path, include_md: bool) -> bool:
    if path.name in SKIP_SCAN_NAMES:
        return False
    try:
        rel = path.relative_to(repo)
    except ValueError:
        return False
    if any(part in SKIP_DIR_NAMES for part in rel.parts):
        return False
    name = path.name.lower()
    if name.startswith("dockerfile") or name.endswith(".dockerfile"):
        return True
    if not include_md and path.suffix.lower() == ".md":
        return False
    return path.suffix.lower() in TEXT_SUFFIXES


def _iter_scan_files(repo: Path, include_md: bool) -> list[Path]:
    out: list[Path] = []
    for p in repo.rglob("*"):
        if not p.is_file():
            continue
        if _should_scan_file(p, repo, include_md):
            out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


def _find_app_paths_in_text(text: str) -> list[tuple[int, str, str]]:
    """Return (line_no, full_match, normalized_path) for each /app/... occurrence."""
    hits: list[tuple[int, str, str]] = []
    lines = text.replace("\r\n", "\n").split("\n")
    for i, line in enumerate(lines, start=1):
        for m in RE_APP_PATH.finditer(line):
            raw = m.group(0)
            norm = _strip_trailing_punct(raw)
            hits.append((i, raw, norm))
    return hits


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Validate hardcoded /app/... paths against x-files.json calibration.",
    )
    ap.add_argument(
        "--json",
        type=Path,
        default=REPO / "x-files.json",
        help="Path to x-files.json",
    )
    ap.add_argument("--repo", type=Path, default=REPO, help="Repository root")
    ap.add_argument(
        "--include-md",
        action="store_true",
        help="Also scan *.md (noisy; off by default)",
    )
    ap.add_argument(
        "--section-exists",
        action="store_true",
        help="Warn when section_to_canonical keys are missing on disk under repo root",
    )
    args = ap.parse_args(list(argv) if argv is not None else None)

    repo = args.repo.resolve()
    jpath = args.json.resolve()
    if not jpath.is_file():
        print(f"error: {jpath} not found. Run: python export_x_files_json.py")
        return 2

    valid_paths, valid_dirs, section_map = _load_calibration(jpath)
    if not valid_paths:
        print("error: valid_app_paths empty in JSON")
        return 2

    bad_hits: list[tuple[str, int, str]] = []
    for fpath in _iter_scan_files(repo, args.include_md):
        if fpath.resolve() == Path(__file__).resolve():
            continue
        try:
            text = fpath.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if text.startswith("\ufeff"):
            text = text[1:]
        rel = fpath.relative_to(repo).as_posix()
        for line_no, _raw, norm in _find_app_paths_in_text(text):
            if not _is_valid_app_path(norm, valid_paths, valid_dirs):
                bad_hits.append((rel, line_no, norm))

    missing_sections: list[str] = []
    if args.section_exists:
        for section in sorted(section_map):
            if ".." in section or section.startswith("/"):
                continue
            p = repo / section
            if not p.exists():
                missing_sections.append(section)

    for rel, line_no, norm in sorted(bad_hits):
        print(f"INVALID /app path: {norm}")
        print(f"  {rel}:{line_no}")

    for section in missing_sections[:500]:
        print(f"MISSING FILE (listing section, not on disk): {section}")
    if len(missing_sections) > 500:
        print(f"... and {len(missing_sections) - 500} more missing sections")

    print(
        f"\nSummary: scanned calibration from {jpath.name}; "
        f"invalid /app literals: {len(bad_hits)}; "
        f"missing section files: {len(missing_sections)}."
    )
    if bad_hits:
        print("Fix: update x-files-listing.txt / regenerate JSON, or correct the path literal.")
        return 1
    if missing_sections and args.section_exists:
        print("Note: missing sections can be normal if paths are image-only or generated at build.")
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
