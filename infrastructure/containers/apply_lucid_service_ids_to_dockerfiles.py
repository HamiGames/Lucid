# Apply Lucid service identifiers to every Dockerfile / Dockerfile.* in the repo.
#
# Full path (repo): infrastructure/containers/apply_lucid_service_ids_to_dockerfiles.py
#
# For each Dockerfile, inserts or updates a managed block (after the last FROM line)
# with LABEL keys:
#   com.lucid.service_id
#   onion.lucid.service_id
#   org.lucid.service_id
# and ENV mirrors (Docker-safe names, same values):
#   COM_LUCID_SERVICE_ID
#   ONION_LUCID_SERVICE_ID
#   ORG_LUCID_SERVICE_ID
#
# ID values are unique per file (repo-relative path), deterministic, and shaped for:
#   com.*   — reverse-DNS style (dots as segment separators)
#   onion.* — single DNS label / Tor logical name: [a-z0-9-], length <= 63
#   org.*   — org-scoped string with path + digest for humans + stability
#
# Run from repo root:
#   python infrastructure/containers/apply_lucid_service_ids_to_dockerfiles.py
#   python infrastructure/containers/apply_lucid_service_ids_to_dockerfiles.py --dry-run
#   python infrastructure/containers/apply_lucid_service_ids_to_dockerfiles.py --verify
#   python infrastructure/containers/apply_lucid_service_ids_to_dockerfiles.py --dump-json
#
# Programmatic capture: load this module via importlib.util.spec_from_file_location, then call:
#   compute_service_ids_for_rel_path(rel_posix)
#   capture_service_ids_for_dockerfile(dockerfile_path, repo_root)
#   capture_service_ids_for_each_dockerfile(repo_root)
#   parse_service_ids_from_dockerfile_text(dockerfile_text)
#   read_captured_service_ids_from_dockerfile(dockerfile_path)
#
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import TypedDict

ROOT = Path(__file__).resolve().parents[2]

BEGIN = "# LUCID_SERVICE_IDS_BEGIN"
END = "# LUCID_SERVICE_IDS_END"

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".tox",
        "dist",
        "build",
    }
)


class LucidServiceIds(TypedDict):
    """Stable service identifiers for one Dockerfile (LABEL / ENV values)."""

    com_lucid_service_id: str
    onion_lucid_service_id: str
    org_lucid_service_id: str


def _posix_rel(path: Path, root: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve())
    except ValueError:
        rel = path
    return rel.as_posix()


def _path_digest(rel_posix: str) -> str:
    return hashlib.sha256(rel_posix.encode("utf-8")).hexdigest()[:16]


def _com_service_id(rel_posix: str, digest: str) -> str:
    dotted = rel_posix.replace("/", ".").replace("\\", ".")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", dotted)
    safe = re.sub(r"\.{2,}", ".", safe).strip(".")
    if not safe:
        safe = "dockerfile"
    return f"com.lucid.dockerfile.v1.{digest}.{safe}"


def _onion_service_id(digest: str, rel_posix: str) -> str:
    """Single-label style: lowercase [a-z0-9-], max 63 (RFC 1035 label)."""
    slug = rel_posix.lower().replace("/", "-").replace(".", "-")
    slug = re.sub(r"[^a-z0-9-]+", "-", slug).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) > 24:
        slug = slug[:24].rstrip("-")
    core = f"lucid-{digest}-{slug}" if slug else f"lucid-{digest}"
    if len(core) > 63:
        core = core[:63].rstrip("-")
    return core


def _org_service_id(rel_posix: str, digest: str) -> str:
    return f"org.lucid.dockerfile.v1.{digest}:{rel_posix}"


def compute_service_ids_for_rel_path(rel_posix: str) -> LucidServiceIds:
    """
    Deterministic Lucid service IDs from a repository-relative POSIX path
    (e.g. infrastructure/containers/rdp/Dockerfile.rdp-controller).
    """
    d = _path_digest(rel_posix)
    return {
        "com_lucid_service_id": _com_service_id(rel_posix, d),
        "onion_lucid_service_id": _onion_service_id(d, rel_posix),
        "org_lucid_service_id": _org_service_id(rel_posix, d),
    }


def capture_service_ids_for_dockerfile(dockerfile: Path, root: Path) -> LucidServiceIds:
    """Compute service IDs for a Dockerfile path under root (same rules as the managed LABEL block)."""
    rel = _posix_rel(dockerfile, root)
    return compute_service_ids_for_rel_path(rel)


def _unescape_docker_double_quoted(s: str) -> str:
    i = 0
    buf: list[str] = []
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            buf.append(s[i + 1])
            i += 2
            continue
        buf.append(s[i])
        i += 1
    return "".join(buf)


def parse_service_ids_from_dockerfile_text(text: str) -> LucidServiceIds | None:
    """
    Read com / onion / org lucid.service_id values from a Dockerfile that contains
    the LUCID_SERVICE_IDS managed block. Returns None if the block or keys are missing.
    """
    if BEGIN not in text or END not in text:
        return None
    start = text.index(BEGIN) + len(BEGIN)
    end = text.index(END, start)
    chunk = text[start:end]
    keys = (
        "com.lucid.service_id",
        "onion.lucid.service_id",
        "org.lucid.service_id",
    )
    found: dict[str, str] = {}
    for key in keys:
        esc_key = re.escape(key)
        m = re.search(rf"{esc_key}\s*=\s*\"((?:\\\\.|[^\"\\\\])*)\"", chunk)
        if not m:
            return None
        found[key] = _unescape_docker_double_quoted(m.group(1))
    return {
        "com_lucid_service_id": found["com.lucid.service_id"],
        "onion_lucid_service_id": found["onion.lucid.service_id"],
        "org_lucid_service_id": found["org.lucid.service_id"],
    }


def read_captured_service_ids_from_dockerfile(dockerfile: Path) -> LucidServiceIds | None:
    """Load service IDs from disk if the managed block is present; else None."""
    raw = dockerfile.read_text(encoding="utf-8", errors="replace")
    return parse_service_ids_from_dockerfile_text(raw)


def _escape_label_value(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _escape_env_value(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def build_block(com_v: str, onion_v: str, org_v: str) -> str:
    c, o, g = (
        _escape_label_value(com_v),
        _escape_label_value(onion_v),
        _escape_label_value(org_v),
    )
    ec, eo, eg = (
        _escape_env_value(com_v),
        _escape_env_value(onion_v),
        _escape_env_value(org_v),
    )
    lines = [
        BEGIN,
        "# managed by apply_lucid_service_ids_to_dockerfiles.py",
        f'LABEL com.lucid.service_id="{c}" \\',
        f'      onion.lucid.service_id="{o}" \\',
        f'      org.lucid.service_id="{g}"',
        f'ENV COM_LUCID_SERVICE_ID="{ec}" \\',
        f'    ONION_LUCID_SERVICE_ID="{eo}" \\',
        f'    ORG_LUCID_SERVICE_ID="{eg}"',
        END,
        "",
    ]
    return "\n".join(lines)


def is_dockerfile_file(path: Path) -> bool:
    if not path.is_file():
        return False
    name = path.name
    if name in ("Dockerfile", "dockerfile"):
        return True
    lower = name.lower()
    return lower.startswith("dockerfile.") and not lower.endswith(".md")


def iter_dockerfiles(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in p.parts):
            continue
        if is_dockerfile_file(p):
            out.append(p)
    out.sort(key=lambda x: _posix_rel(x, root).lower())
    return out


def capture_service_ids_for_each_dockerfile(root: Path) -> dict[str, LucidServiceIds]:
    """Map repo-relative POSIX path -> service IDs for every Dockerfile under root."""
    root = root.resolve()
    out: dict[str, LucidServiceIds] = {}
    for path in iter_dockerfiles(root):
        rel = _posix_rel(path, root)
        out[rel] = compute_service_ids_for_rel_path(rel)
    return out


def last_from_line_index(lines: list[str]) -> int | None:
    idx: int | None = None
    for i, line in enumerate(lines):
        if re.match(r"^\s*FROM\s", line, re.IGNORECASE):
            idx = i
    return idx


def replace_or_insert_block(text: str, block: str) -> tuple[str, str]:
    """
    Returns (new_text, action) where action is 'replaced' | 'inserted' | 'unchanged'.
    """
    if BEGIN in text and END in text:
        pattern = re.compile(
            re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?",
            re.DOTALL,
        )
        new_text, n = pattern.subn(block.rstrip("\n") + "\n", text, count=1)
        if n != 1:
            return text, "unchanged"
        if new_text == text:
            return text, "unchanged"
        return new_text, "replaced"

    lines = text.splitlines(keepends=True)
    j = last_from_line_index([ln.rstrip("\n") for ln in lines])
    if j is None:
        return text, "unchanged"

    insert_at = j + 1
    # Avoid duplicating if block already there without markers (legacy)
    new_lines = lines[:insert_at] + ["\n", block] + lines[insert_at:]
    return "".join(new_lines), "inserted"


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply Lucid service_id LABEL/ENV blocks to Dockerfiles.")
    ap.add_argument("--root", type=Path, default=ROOT, help="Repository root (default: inferred).")
    ap.add_argument("--dry-run", action="store_true", help="Print actions only; do not write files.")
    ap.add_argument("--verify", action="store_true", help="Exit 1 if IDs collide or a Dockerfile has no FROM.")
    ap.add_argument(
        "--dump-json",
        action="store_true",
        help="Print captured service_id map (path -> com/onion/org) as JSON and exit.",
    )
    args = ap.parse_args()
    root: Path = args.root.resolve()

    paths = iter_dockerfiles(root)
    by_file: dict[str, tuple[str, str, str]] = {}
    com_set: set[str] = set()
    onion_set: set[str] = set()
    org_set: set[str] = set()

    for path in paths:
        rel = _posix_rel(path, root)
        ids = compute_service_ids_for_rel_path(rel)
        com_v = ids["com_lucid_service_id"]
        onion_v = ids["onion_lucid_service_id"]
        org_v = ids["org_lucid_service_id"]
        by_file[rel] = (com_v, onion_v, org_v)
        com_set.add(com_v)
        onion_set.add(onion_v)
        org_set.add(org_v)

    if len(com_set) != len(by_file) or len(onion_set) != len(by_file) or len(org_set) != len(by_file):
        print("error: generated ID collision — extend digest length in script.", file=sys.stderr)
        return 1

    if args.dump_json:
        payload = {
            rel: {
                "com_lucid_service_id": t[0],
                "onion_lucid_service_id": t[1],
                "org_lucid_service_id": t[2],
            }
            for rel, t in sorted(by_file.items())
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.verify:
        bad = 0
        for path in paths:
            rel = _posix_rel(path, root)
            raw = path.read_text(encoding="utf-8", errors="replace")
            if last_from_line_index(raw.splitlines()) is None:
                print(f"verify: no FROM — {rel}", file=sys.stderr)
                bad += 1
            if BEGIN not in raw or END not in raw:
                print(f"verify: missing service id block — {rel}", file=sys.stderr)
                bad += 1
        return 1 if bad else 0

    changed = 0
    for path in paths:
        rel = _posix_rel(path, root)
        com_v, onion_v, org_v = by_file[rel]
        block = build_block(com_v, onion_v, org_v)
        raw = path.read_text(encoding="utf-8", errors="replace")
        if last_from_line_index(raw.splitlines()) is None:
            print(f"skip (no FROM): {rel}", file=sys.stderr)
            continue
        new_raw, action = replace_or_insert_block(raw, block)
        if action == "unchanged":
            continue
        changed += 1
        msg = f"{action}: {rel}"
        print(msg)
        if not args.dry_run:
            path.write_text(new_raw, encoding="utf-8", newline="\n")

    print(f"done. {changed} file(s) {'would change' if args.dry_run else 'updated'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
