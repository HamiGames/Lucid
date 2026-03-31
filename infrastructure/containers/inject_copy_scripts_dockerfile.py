"""
File: infrastructure/containers/inject_copy_scripts_dockerfile.py
x-lucid-file-path: infrastructure/containers/inject_copy_scripts_dockerfile.py
x-lucid-file-directory: infrastructure/containers
x-lucid-file-type: python

Add ``COPY scripts/ ./scripts/`` to Dockerfiles under ``infrastructure/containers/`` and
``infrastructure/docker/`` when missing.

Insertion rules (first ``FROM`` stage only for skeleton anchoring):

1. If ``# LUCID_X_FILES_SKELETON_END`` exists in that stage: place ``COPY scripts/ ./scripts/``
   **immediately after** the **last** such line in the stage. If the Dockerfile already contains
   that ``COPY`` but **before** that marker, it is **removed and re-inserted** after the marker
   (skeleton ``mkdir`` layout must exist before copying repo ``scripts/``).
2. Else if there is a ``WORKDIR /build`` line: insert immediately after the **first** occurrence.
3. Else if there is a ``WORKDIR`` before the first plain ``COPY`` (not ``COPY --from`` / ``ADD --from``): insert after that **last** ``WORKDIR`` before that ``COPY``.
4. Else if there is a plain ``COPY`` / ``ADD``: insert immediately **before** the first such line.
5. Else: skip (no plain ``COPY`` / ``ADD``).

Default: dry-run. Pass ``--apply`` to write.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_REL_ROOTS = (
    "infrastructure/containers",
    "infrastructure/docker",
)

RE_COPY_SCRIPTS_LINE = re.compile(
    r"^\s*COPY(?:\s+--[\w=.-]+)*\s+scripts/\s+\./scripts/\s*$",
)

RE_SKELETON_END = re.compile(r"^\s*#\s*LUCID_X_FILES_SKELETON_END\s*(?:#.*)?\s*$")
RE_FROM = re.compile(r"^\s*FROM\s+", re.IGNORECASE)

RE_WORKDIR_BUILD = re.compile(r"^\s*WORKDIR\s+/build(?:\s+#.*)?\s*$")
RE_WORKDIR_ANY = re.compile(r"^\s*WORKDIR\s+(\S+)(?:\s+#.*)?\s*$")
RE_PLAIN_COPY = re.compile(r"^\s*COPY\s+(?!--from=)")
RE_PLAIN_ADD = re.compile(r"^\s*ADD\s+(?!--from=)")


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def iter_dockerfiles() -> list[Path]:
    root = repo_root()
    out: list[Path] = []
    for rel in REPO_REL_ROOTS:
        base = root / rel
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            n = p.name
            if (
                n == "Dockerfile"
                or n.startswith("Dockerfile.")
                or n.startswith("Dockerfile ")
                or n.startswith("dockerfile.")
            ):
                out.append(p)
    return out


def line_key(ln: str) -> str:
    return ln.rstrip("\r\n")


def _first_stage_range(bodies: list[str]) -> tuple[int, int]:
    starts = [i for i, b in enumerate(bodies) if RE_FROM.match(b)]
    if not starts:
        return (0, len(bodies))
    end = starts[1] if len(starts) > 1 else len(bodies)
    return (starts[0], end)


def _skeleton_end_indices_in_first_stage(bodies: list[str]) -> list[int]:
    s0, e0 = _first_stage_range(bodies)
    return [i for i in range(s0, e0) if RE_SKELETON_END.match(bodies[i])]


def _copy_scripts_indices(bodies: list[str]) -> list[int]:
    return [i for i, b in enumerate(bodies) if RE_COPY_SCRIPTS_LINE.match(b)]


def insert_copy_scripts(text: str) -> tuple[str, str]:
    """
    Return (new_text, action).
    action: unchanged-has-copy | unchanged-no-copy-instruction | inserted-after-skeleton |
            relocated-after-skeleton | inserted-after-workdir-build | inserted-after-workdir |
            inserted-before-first-copy
    """
    lines = text.splitlines(keepends=True)
    bodies = [line_key(ln) for ln in lines]

    skeleton_ends = _skeleton_end_indices_in_first_stage(bodies)
    copy_idxs = _copy_scripts_indices(bodies)

    if copy_idxs:
        if not skeleton_ends:
            return text, "unchanged-has-copy"
        anchor = skeleton_ends[-1]
        if min(copy_idxs) > anchor:
            return text, "unchanged-has-copy"
        # COPY scripts/ appeared before skeleton end — drop all such lines and insert once after skeleton.
        drop = set(copy_idxs)
        keep = [ln for i, ln in enumerate(lines) if i not in drop]
        bodies2 = [line_key(ln) for ln in keep]
        sk2 = _skeleton_end_indices_in_first_stage(bodies2)
        if not sk2:
            return text, "unchanged-has-copy"
        a2 = sk2[-1]
        nl = "\r\n" if keep[a2].endswith("\r\n") else "\n"
        insert = f"COPY scripts/ ./scripts/{nl}"
        new_lines = keep[: a2 + 1] + [insert] + keep[a2 + 1 :]
        return "".join(new_lines), "relocated-after-skeleton"

    if skeleton_ends:
        anchor = skeleton_ends[-1]
        nl = "\r\n" if lines[anchor].endswith("\r\n") else "\n"
        insert = f"COPY scripts/ ./scripts/{nl}"
        new_lines = lines[: anchor + 1] + [insert] + lines[anchor + 1 :]
        return "".join(new_lines), "inserted-after-skeleton"

    # No x-files skeleton in first stage — preserve previous WORKDIR / COPY heuristics.
    for i, b in enumerate(bodies):
        if RE_WORKDIR_BUILD.match(b):
            nl = "\r\n" if lines[i].endswith("\r\n") else "\n"
            ins = f"COPY scripts/ ./scripts/{nl}"
            new_lines = lines[: i + 1] + [ins] + lines[i + 1 :]
            return "".join(new_lines), "inserted-after-workdir-build"

    first_copy_idx: int | None = None
    for j, b in enumerate(bodies):
        if RE_PLAIN_COPY.match(b) or RE_PLAIN_ADD.match(b):
            first_copy_idx = j
            break
    if first_copy_idx is None:
        return text, "unchanged-no-copy-instruction"

    last_workdir_before = None
    for j in range(first_copy_idx):
        if RE_WORKDIR_ANY.match(bodies[j]):
            last_workdir_before = j
    if last_workdir_before is not None:
        i = last_workdir_before
        nl = "\r\n" if lines[i].endswith("\r\n") else "\n"
        ins = f"COPY scripts/ ./scripts/{nl}"
        new_lines = lines[: i + 1] + [ins] + lines[i + 1 :]
        return "".join(new_lines), "inserted-after-workdir"

    j = first_copy_idx
    nl = "\r\n" if lines[j].endswith("\r\n") else "\n"
    ins = f"COPY scripts/ ./scripts/{nl}"
    new_lines = lines[:j] + [ins] + lines[j:]
    return "".join(new_lines), "inserted-before-first-copy"


def main() -> int:
    ap = argparse.ArgumentParser(description="Inject COPY scripts/ ./scripts/ into Lucid Dockerfiles.")
    ap.add_argument("--apply", action="store_true", help="Write changes (default: dry-run).")
    ap.add_argument("--only", action="append", default=[], metavar="PATH", help="Repo-relative Dockerfile path.")
    args = ap.parse_args()
    root = repo_root()

    if args.only:
        paths = []
        for o in args.only:
            p = (root / o).resolve()
            if p.is_file():
                paths.append(p)
            else:
                print(f"skip (not a file): {o}", file=sys.stderr)
    else:
        paths = iter_dockerfiles()

    changed = 0
    for path in paths:
        rel = path.relative_to(root)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"read error {rel}: {e}", file=sys.stderr)
            continue
        new_text, action = insert_copy_scripts(text)
        if new_text != text:
            changed += 1
            print(f"{action}: {rel}")
            if args.apply:
                path.write_text(new_text, encoding="utf-8", newline="\n")
        elif action == "unchanged-no-copy-instruction":
            print(f"skip (no plain COPY/ADD in Dockerfile): {rel}", file=sys.stderr)
        elif action == "unchanged-has-copy":
            pass

    print(f"Scanned {len(paths)} file(s); {changed} updated.", file=sys.stderr)
    if changed and not args.apply:
        print("Dry-run: pass --apply to write.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
