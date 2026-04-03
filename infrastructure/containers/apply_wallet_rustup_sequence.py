#!/usr/bin/env python3
"""Inject wallet rustup sequence into Dockerfiles with rustc/cargo."""

from __future__ import annotations

import re
from pathlib import Path


WALLET_SEQUENCE = """RUN apt-get remove -y rustc cargo && rm -rf /root/.cargo /root/.rustup && \\
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
"""


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def discover_dockerfiles(infra_root: Path) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for pat in ("*Dockerfile*", "*dockerfile*"):
        for p in infra_root.rglob(pat):
            if not p.is_file() or "__pycache__" in p.parts:
                continue
            rp = p.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            out.append(rp)
    return sorted(out, key=lambda x: str(x).lower())


def needs_wallet_sequence(text: str) -> bool:
    return ("rustc" in text and "cargo" in text) and ("sh.rustup.rs" not in text)


def inject_before_pip_block(text: str) -> str | None:
    lines = text.splitlines(keepends=False)
    insert_at: int | None = None
    i = 0
    n = len(lines)
    while i < n:
        ln = lines[i]
        if not re.match(r"^\s*RUN\s", ln, re.IGNORECASE):
            i += 1
            continue
        block = [ln]
        j = i + 1
        while block[-1].rstrip().endswith("\\") and j < n:
            block.append(lines[j])
            j += 1
        one = " ".join(block).lower()
        if "pip wheel" in one or "pip install" in one:
            insert_at = i
            break
        i = j
    if insert_at is None:
        return None
    seq_lines = WALLET_SEQUENCE.strip("\n").split("\n")
    new_lines = lines[:insert_at] + seq_lines + [""] + lines[insert_at:]
    out = "\n".join(new_lines)
    if text.endswith("\n"):
        out += "\n"
    return out if out != text else None


def main() -> int:
    root = repo_root_from_here()
    infra = (root / "infrastructure").resolve()
    changed = 0
    for df in discover_dockerfiles(infra):
        raw = df.read_text(encoding="utf-8", errors="replace")
        if not needs_wallet_sequence(raw):
            continue
        patched = inject_before_pip_block(raw)
        if patched is None:
            continue
        df.write_text(patched, encoding="utf-8", newline="\n")
        changed += 1
        print(f"updated: {df}")
    print(f"done: {changed} Dockerfile(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
