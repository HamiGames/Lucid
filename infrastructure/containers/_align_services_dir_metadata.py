"""
Align YAML under infrastructure/containers/services/ with x-files.json and host-config.yml.

1. Comment header (File / x-lucid-file-path / x-lucid-file-directory / x-lucid-file-type)
   matches x-files.json section_to_canonical for each repo path.
2. One alignment comment ties host-config + x-files.json to every file.
3. Normalizes http_path_template to host-config form: http://${service_name}:${port}/app
   (replaces legacy http://{service_name}:{port}/app).

Authoritative registry: infrastructure/containers/host-config.yml
Path index: x-files.json (section_to_canonical)

Run from repo root (PyYAML optional — not required for this script):
  python infrastructure/containers/_align_services_dir_metadata.py
  python infrastructure/containers/_align_services_dir_metadata.py --apply
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICES_DIR = REPO_ROOT / "infrastructure" / "containers" / "services"
X_FILES = REPO_ROOT / "x-files.json"

# Matches host-config.yml http_path_template
HOST_HTTP_TEMPLATE = "http://${service_name}:${port}/app"
LEGACY_TEMPLATE_PATTERN = re.compile(
    r"http://\{service_name\}:\{port\}/app"
)

ALIGNMENT_COMMENT = (
    "# Lucid alignment: host_registry=infrastructure/containers/host-config.yml "
    "(container /app/configs/host-config.yml); path_index=x-files.json section_to_canonical"
)


def load_canonical_map() -> dict[str, str]:
    with X_FILES.open(encoding="utf-8") as f:
        data = json.load(f)
    m = data.get("section_to_canonical") or {}
    if not isinstance(m, dict):
        return {}
    return {str(k): str(v) for k, v in m.items()}


def build_header_lines(canonical: str) -> list[str]:
    parent = str(PurePosixPath(canonical).parent)
    return [
        f"# File: {canonical}",
        f"# x-lucid-file-path: {canonical}",
        f"# x-lucid-file-directory: {parent}",
        "# x-lucid-file-type: YAML",
        ALIGNMENT_COMMENT,
    ]


def find_header_slice(lines: list[str]) -> tuple[int, int]:
    """Return [start, end) line indices of the standard Lucid header block, or (0,0) if none."""
    if not lines or not lines[0].startswith("# File:"):
        return (0, 0)
    end = 0
    found_type = False
    for i, line in enumerate(lines):
        if line.startswith("# x-lucid-file-type:"):
            found_type = True
            end = i + 1
            break
    if not found_type:
        return (0, 0)
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    while end < len(lines) and lines[end].startswith("# Lucid alignment:"):
        end += 1
    while end < len(lines) and lines[end].strip() == "":
        end += 1
    return (0, end)


def process_text(rel_repo: str, canonical: str, raw: str) -> tuple[str, bool]:
    lines = raw.splitlines()
    start, end = find_header_slice(lines)
    header_lines = build_header_lines(canonical)
    if start == end == 0:
        body = lines
    else:
        body = lines[end:]

    if body and body[0].startswith("# Lucid alignment:"):
        body = body[1:]
        if body and body[0].strip() == "":
            body = body[1:]

    new_lines = header_lines + [""] + body
    intermediate = "\n".join(new_lines)
    if not intermediate.endswith("\n"):
        intermediate += "\n"

    updated, n_sub = LEGACY_TEMPLATE_PATTERN.subn(HOST_HTTP_TEMPLATE, intermediate)
    changed = (updated != raw) or n_sub > 0
    return updated, changed


def iter_service_yaml() -> list[Path]:
    out: list[Path] = []
    for p in sorted(SERVICES_DIR.rglob("*")):
        if not p.is_file():
            continue
        if p.suffix.lower() not in (".yml", ".yaml"):
            continue
        out.append(p)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes; default is dry-run summary only.",
    )
    args = parser.parse_args()
    canon = load_canonical_map()
    if not canon:
        print("ERROR: empty section_to_canonical in x-files.json", file=sys.stderr)
        return 1

    missing: list[str] = []
    changed_files: list[str] = []
    for path in iter_service_yaml():
        rel = path.relative_to(REPO_ROOT).as_posix()
        expected = canon.get(rel)
        if expected is None:
            missing.append(rel)
            continue
        raw = path.read_text(encoding="utf-8")
        new_text, changed = process_text(rel, expected, raw)
        if changed:
            changed_files.append(rel)
            if args.apply:
                path.write_text(new_text, encoding="utf-8", newline="\n")

    if missing:
        print("WARN: not in x-files.json (skipped):", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)

    print(f"{'Would update' if not args.apply else 'Updated'} {len(changed_files)} file(s).")
    for c in changed_files[:50]:
        print(f"  {c}")
    if len(changed_files) > 50:
        print(f"  ... and {len(changed_files) - 50} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
