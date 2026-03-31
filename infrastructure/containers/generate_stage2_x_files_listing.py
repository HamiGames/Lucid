#!/usr/bin/env python3
"""Generate x-files-listing.txt from Dockerfile final stage paths only."""

from __future__ import annotations

import argparse
import re
import shlex
from pathlib import PurePosixPath, Path


def repo_root_from_here() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def to_repo_rel(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def discover_dockerfiles(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.is_dir():
            continue
        for pattern in ("Dockerfile*", "dockerfile*"):
            for p in root.rglob(pattern):
                if not p.is_file():
                    continue
                if "__pycache__" in p.parts:
                    continue
                if not re.match(r"^[Dd]ockerfile(?:\..+)?$", p.name):
                    continue
                rp = p.resolve()
                if rp in seen:
                    continue
                seen.add(rp)
                out.append(rp)
    return sorted(out, key=lambda p: str(p).lower())


def split_stages(lines: list[str]) -> list[tuple[int, int]]:
    starts: list[int] = []
    for i, line in enumerate(lines):
        if re.match(r"^\s*FROM\s", line, re.IGNORECASE):
            starts.append(i)
    if not starts:
        return [(0, len(lines))]
    out: list[tuple[int, int]] = []
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(lines)
        out.append((s, e))
    return out


def join_with_workdir(workdir: str, token: str) -> str:
    t = token.strip().strip('"').strip("'")
    t = t.lstrip(">").lstrip("<")
    if not t:
        return workdir
    if t.startswith("/"):
        return str(PurePosixPath(t))
    if t.startswith("./"):
        t = t[2:]
    return str(PurePosixPath(workdir) / t)


def normalize_app_path(path: str) -> str | None:
    p = str(PurePosixPath(path))
    if not p.startswith("/app"):
        return None
    if "/dev/null" in p:
        return None
    return p


def normalize_build_path(path: str) -> str | None:
    p = str(PurePosixPath(path))
    if not p.startswith("/build"):
        return None
    return p if p.endswith("/") else p + "/"


def parse_copy_payload(one: str) -> tuple[list[str], str, str | None] | None:
    if "||" in one or "&&" in one or ";" in one:
        return None
    try:
        tokens = shlex.split(one)
    except ValueError:
        tokens = one.split()
    if len(tokens) < 3:
        return None
    ins = tokens[0].upper()
    if ins not in {"COPY", "ADD"}:
        return None
    payload: list[str] = []
    from_stage: str | None = None
    for t in tokens[1:]:
        if t.startswith("--from="):
            from_stage = t.split("=", 1)[1]
            continue
        if t.startswith("--"):
            continue
        payload.append(t)
    if len(payload) < 2:
        return None
    return payload[:-1], payload[-1], from_stage


def parse_instruction_blocks(lines: list[str], start: int, end: int) -> list[str]:
    blocks: list[str] = []
    i = start
    while i < end:
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        block = [line]
        i += 1
        while block[-1].rstrip().endswith("\\") and i < end:
            block.append(lines[i])
            i += 1
        blocks.append("\n".join(block))
    return blocks


def resolve_source_dir(source_token: str, repo_root: Path, dockerfile_dir: Path) -> Path | None:
    src = source_token.strip().strip('"').strip("'")
    if not src or src.startswith("/") or "*" in src:
        return None
    # Prefer repo-root resolution (Lucid build context), then Dockerfile-local fallback.
    cands = [(repo_root / src), (dockerfile_dir / src)]
    for c in cands:
        if c.is_dir():
            return c.resolve()
    return None


def expand_tree_entries(src_dir: Path, max_depth: int) -> set[str]:
    out: set[str] = set()
    for p in src_dir.rglob("*"):
        rel = p.relative_to(src_dir)
        depth = len(rel.parts)
        if depth > max_depth:
            continue
        if p.is_dir():
            out.add(rel.as_posix().rstrip("/") + "/")
        elif p.is_file():
            out.add(rel.as_posix())
    return out


def gather_build_source_maps(
    text: str, repo_root: Path, dockerfile_path: Path
) -> dict[str, list[tuple[Path, str]]]:
    lines = text.splitlines()
    stages = split_stages(lines)
    if not stages:
        return {}
    out: dict[str, list[tuple[Path, str]]] = {}
    # builder stages = everything except final stage
    for s0, s1 in stages[:-1]:
        blocks = parse_instruction_blocks(lines, s0 + 1, s1)
        workdir = "/"
        for block in blocks:
            one = re.sub(r"\\\s*\n\s*", " ", block).strip()
            if not one:
                continue
            if re.match(r"^\s*WORKDIR\s+", one, re.IGNORECASE):
                wd = re.sub(r"^\s*WORKDIR\s+", "", one, flags=re.IGNORECASE).strip()
                workdir = join_with_workdir(workdir, wd)
                continue
            if not re.match(r"^\s*(COPY|ADD)\s+", one, re.IGNORECASE):
                continue
            parsed = parse_copy_payload(one)
            if parsed is None:
                continue
            srcs, dest, from_stage = parsed
            if from_stage is not None:
                continue
            abs_dest = join_with_workdir(workdir, dest)
            bdest = normalize_build_path(abs_dest)
            if bdest is None:
                continue
            for src in srcs:
                src_dir = resolve_source_dir(src, repo_root, dockerfile_path.parent)
                if src_dir is None:
                    continue
                out.setdefault(bdest, []).append((src_dir, src))
    return out


def add_provenance(
    prov: dict[str, set[tuple[str, str]]], runtime_path: str, source_file: str, source_path: str
) -> None:
    prov.setdefault(runtime_path, set()).add((source_file, source_path))


def extract_paths_from_final_stage(
    text: str, repo_root: Path, dockerfile_path: Path, max_tree_depth: int
) -> tuple[set[str], dict[str, set[tuple[str, str]]]]:
    lines = text.splitlines()
    stages = split_stages(lines)
    if not stages:
        return set(), {}
    build_map = gather_build_source_maps(text, repo_root, dockerfile_path)
    s0, s1 = stages[-1]
    blocks = parse_instruction_blocks(lines, s0 + 1, s1)
    workdir = "/"
    out: set[str] = set()
    provenance: dict[str, set[tuple[str, str]]] = {}
    dockerfile_rel = to_repo_rel(dockerfile_path, repo_root)

    for block in blocks:
        one = re.sub(r"\\\s*\n\s*", " ", block).strip()
        if not one:
            continue
        if re.match(r"^\s*WORKDIR\s+", one, re.IGNORECASE):
            wd = re.sub(r"^\s*WORKDIR\s+", "", one, flags=re.IGNORECASE).strip()
            workdir = join_with_workdir(workdir, wd)
            p = normalize_app_path(workdir)
            if p:
                p_out = p if p.endswith("/") else p + "/"
                out.add(p_out)
                add_provenance(provenance, p_out, dockerfile_rel, dockerfile_rel)
            continue

        if re.match(r"^\s*(COPY|ADD)\s+", one, re.IGNORECASE):
            parsed = parse_copy_payload(one)
            if parsed is None:
                continue
            srcs, dest, from_stage = parsed
            abs_dest = join_with_workdir(workdir, dest)
            p = normalize_app_path(abs_dest)
            if p is None:
                continue
            if dest.endswith("/") or len(srcs) > 1:
                p_out = p if p.endswith("/") else p + "/"
                out.add(p_out)
                src_hint = ", ".join(srcs)
                add_provenance(provenance, p_out, src_hint, src_hint)
            else:
                out.add(p)
                add_provenance(provenance, p, srcs[0], srcs[0])
            # Expansion for COPY --from=<stage> /build/<dir>/ /app/<dir> using original builder COPY sources.
            if from_stage is not None and len(srcs) == 1:
                src0 = srcs[0]
                bsrc = normalize_build_path(src0 if src0.startswith("/") else join_with_workdir("/", src0))
                app_dest = p if p.endswith("/") else p + "/"
                if bsrc and bsrc in build_map:
                    for src_dir, src_token in build_map[bsrc]:
                        src_root_rel = to_repo_rel(src_dir, repo_root)
                        for rel in expand_tree_entries(src_dir, max_tree_depth):
                            src_item_rel = f"{src_root_rel}/{rel}".replace("//", "/")
                            if rel.endswith("/"):
                                rp = app_dest + rel
                                out.add(rp)
                                add_provenance(provenance, rp, src_item_rel, src_root_rel)
                            else:
                                rp = app_dest + rel
                                out.add(rp)
                                add_provenance(provenance, rp, src_item_rel, src_root_rel)
                        add_provenance(provenance, app_dest, src_token, src_root_rel)
            continue

        if re.match(r"^\s*RUN\s+", one, re.IGNORECASE):
            body = re.sub(r"^\s*RUN\s+", "", one, flags=re.IGNORECASE)
            for seg in re.split(r"\s*(?:&&|;|\|\|)\s*", body):
                seg = seg.strip()
                if not seg.lower().startswith("mkdir "):
                    continue
                try:
                    toks = shlex.split(seg)
                except ValueError:
                    toks = seg.split()
                if not toks or toks[0] != "mkdir":
                    continue
                for tok in toks[1:]:
                    if tok.startswith("-"):
                        continue
                    abs_p = join_with_workdir(workdir, tok)
                    p = normalize_app_path(abs_p)
                    if p:
                        p_out = p if p.endswith("/") else p + "/"
                        out.add(p_out)
                        add_provenance(provenance, p_out, dockerfile_rel, dockerfile_rel)
            continue
    return out, provenance


def render_listing(root: Path, dockerfiles: list[Path], max_tree_depth: int) -> str:
    lines: list[str] = []
    lines.append("# Auto-generated by generate_stage2_x_files_listing.py")
    lines.append("# Scope: Dockerfile final stage only (last FROM)")
    lines.append("# Roots: infrastructure/containers, infrastructure/docker")
    lines.append("")
    total = 0
    for df in dockerfiles:
        rel = str(df.relative_to(root)).replace("\\", "/")
        paths, provenance = extract_paths_from_final_stage(
            df.read_text(encoding="utf-8", errors="replace"),
            root,
            df,
            max_tree_depth,
        )
        paths = sorted(paths)
        lines.append(f"# --- {rel} ---")
        if not paths:
            lines.append("# (no /app stage-2 paths detected)")
            lines.append("")
            continue
        for p in paths:
            total += 1
            directory = str(PurePosixPath(p).parent) if not p.endswith("/") else p.rstrip("/")
            lines.append('"""')
            lines.append(f"File: {p}")
            lines.append(f"x-lucid-file-path: {p}")
            lines.append(f"x-lucid-file-directory: {directory}")
            lines.append("x-lucid-file-type: docker-stage2")
            src = sorted(provenance.get(p, {("unknown", "unknown")}))
            src_files = "; ".join(x[0] for x in src)
            src_paths = "; ".join(x[1] for x in src)
            lines.append(f"source-file: {src_files}")
            lines.append(f"source-path: {src_paths}")
            lines.append('"""')
            lines.append("")
    lines.append(f"# Total x-lucid-file-path entries: {total}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    root = repo_root_from_here()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--output",
        default="x-files-listing.txt",
        help="Output listing path (repo-relative or absolute).",
    )
    ap.add_argument("--apply", action="store_true", help="Write output file.")
    ap.add_argument(
        "--max-tree-depth",
        type=int,
        default=5,
        help="Max source tree expansion depth for COPY --from=/build -> /app mapping (default: 5).",
    )
    args = ap.parse_args()

    roots = [
        (root / "infrastructure" / "containers").resolve(),
        (root / "infrastructure" / "docker").resolve(),
    ]
    dockerfiles = discover_dockerfiles(roots)
    content = render_listing(root, dockerfiles, max_tree_depth=max(1, args.max_tree_depth))

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = (root / out_path).resolve()

    if args.apply:
        out_path.write_text(content, encoding="utf-8", newline="\n")
        print(f"wrote: {out_path}")
    else:
        print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
