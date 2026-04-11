# Path: scripts/_check_infra_container_copy.py
# One-off: list COPY sources under infrastructure/containers Dockerfiles missing from repo root.
from __future__ import annotations

import os
import re
import sys

root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ic = os.path.join(root, "infrastructure", "containers")
copy_re = re.compile(r"^\s*COPY\s+", re.I)
from_re = re.compile(r"--from=")
bracket = re.compile(r"^\s*COPY\s+\[")


def strip_comment(line: str) -> str:
    if " #" in line:
        line = line.split(" #", 1)[0]
    return line.rstrip()


def parse_copy_sources(rest: str) -> list[str]:
    parts: list[str] = []
    cur = ""
    inq: str | None = None
    j = 0
    while j < len(rest):
        c = rest[j]
        if inq:
            if c == inq:
                parts.append(cur)
                cur = ""
                inq = None
            else:
                cur += c
            j += 1
            continue
        if c in "\"'":
            inq = c
            j += 1
            continue
        if c.isspace():
            if cur:
                parts.append(cur)
                cur = ""
            j += 1
            continue
        if rest[j : j + 2] == "--":
            if cur:
                parts.append(cur)
                cur = ""
            while j < len(rest) and not rest[j].isspace():
                j += 1
            continue
        cur += c
        j += 1
    if cur:
        parts.append(cur)
    return parts


def is_dockerfile_name(fn: str) -> bool:
    if fn.endswith(".bak") or ".bak." in fn:
        return False
    return bool(re.match(r"(?i)^dockerfile([.-]|$)", fn))


def main() -> int:
    missing: list[tuple[str, int, str]] = []
    files_checked = 0
    for dp, _dns, fns in os.walk(ic):
        for fn in fns:
            if not is_dockerfile_name(fn):
                continue
            path = os.path.join(dp, fn)
            files_checked += 1
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
            except OSError as e:
                print(f"READ_FAIL {path}: {e}", file=sys.stderr)
                continue
            for i, line in enumerate(lines, 1):
                raw = line.replace("\r", "").rstrip("\n")
                s = strip_comment(raw)
                if not copy_re.match(s):
                    continue
                if from_re.search(s):
                    continue
                if bracket.match(s):
                    continue
                rest = copy_re.sub("", s).strip()
                parts = parse_copy_sources(rest)
                if len(parts) < 2:
                    continue
                for src in parts[:-1]:
                    if src.startswith("$"):
                        continue
                    if src.startswith("/"):
                        continue
                    full = os.path.normpath(os.path.join(root, src))
                    if not os.path.lexists(full):
                        missing.append((path, i, src))

    print(f"files_checked={files_checked}")
    print(f"missing_copy_sources={len(missing)}")
    for p, ln, src in missing:
        rel = os.path.relpath(p, root)
        print(f"{rel}:{ln}: missing {src}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
