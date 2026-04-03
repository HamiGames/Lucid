#!/usr/bin/env python3
"""
File: infrastructure/containers/organize_dockerfiles_by_layout.py

Reorder Dockerfile content blocks to follow the numbered section order defined in
JSON structure rules, without mutating
the content of each block.

The script:
- parses section order from the template file
- splits Dockerfiles into movable instruction blocks
- classifies each block into a template section using conservative heuristics
- emits a reordered Dockerfile (stable order inside each section)
- keeps every block (unmapped blocks are appended, never discarded)

Usage examples (repo root):
  python infrastructure/containers/organize_dockerfiles_by_layout.py \
    --path infrastructure/containers/admin/dockerfile.admin-overlord \
    --dry-run

  python infrastructure/containers/organize_dockerfiles_by_layout.py \
    --path infrastructure/containers \
    --write
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DIRECTIVE_RE = re.compile(
    r"^\s*(FROM|ARG|ENV|RUN|COPY|ADD|WORKDIR|LABEL|EXPOSE|HEALTHCHECK|USER|ENTRYPOINT|CMD|SHELL|STOPSIGNAL|VOLUME)\b",
    re.IGNORECASE,
)
SECTION_RE = re.compile(r"^\s*(\d+)\.\s*\*\*(.*?)\*\*")


@dataclass
class Block:
    lines: list[str]
    directive: str | None
    stage_index: int
    text: str
    first_line: str


def parse_template_sections(template_text: str) -> list[str]:
    sections: list[tuple[int, str]] = []
    for line in template_text.splitlines():
        m = SECTION_RE.match(line)
        if not m:
            continue
        sections.append((int(m.group(1)), m.group(2).strip()))
    sections.sort(key=lambda x: x[0])
    return [name for _, name in sections]

def load_structure_json(structure_path: Path) -> tuple[list[str], dict[str, str], str]:
    raw = json.loads(structure_path.read_text(encoding="utf-8"))
    sections = sorted(raw.get("sections", []), key=lambda x: int(x.get("number", 0)))
    names = [str(s["name"]) for s in sections]
    id_to_name = {str(s["id"]): str(s["name"]) for s in sections}
    runtime_start_id = str(raw.get("runtime_start_section_id", "DISTROLESS_COMPILER"))
    return names, id_to_name, runtime_start_id


def split_blocks(docker_text: str) -> list[Block]:
    lines = docker_text.splitlines(keepends=True)
    if not lines:
        return []

    blocks: list[Block] = []
    cursor = 0
    stage_index = 0

    first_directive_idx = None
    for i, line in enumerate(lines):
        if DIRECTIVE_RE.match(line):
            first_directive_idx = i
            break

    if first_directive_idx is None:
        return [Block(lines=lines, directive=None, stage_index=0, text="".join(lines), first_line="")]

    if first_directive_idx > 0:
        pre = lines[:first_directive_idx]
        blocks.append(Block(lines=pre, directive=None, stage_index=0, text="".join(pre), first_line=pre[0].strip()))

    def is_continuation_line(prev_line: str) -> bool:
        return prev_line.rstrip().endswith("\\")

    cursor = first_directive_idx
    while cursor < len(lines):
        if not DIRECTIVE_RE.match(lines[cursor]):
            # Safety fallback: attach non-directive debris as standalone block.
            start = cursor
            cursor += 1
            while cursor < len(lines):
                # If previous line continues, current line must stay in same block.
                if cursor > start and is_continuation_line(lines[cursor - 1]):
                    cursor += 1
                    continue
                if DIRECTIVE_RE.match(lines[cursor]):
                    break
                cursor += 1
            chunk = lines[start:cursor]
            blocks.append(
                Block(lines=chunk, directive=None, stage_index=stage_index, text="".join(chunk), first_line=chunk[0].strip())
            )
            continue

        start = cursor
        cursor += 1
        while cursor < len(lines):
            # Keep line continuations with the current instruction, even if they
            # begin with instruction-like tokens (e.g. "    CMD ..." in HEALTHCHECK).
            if is_continuation_line(lines[cursor - 1]):
                cursor += 1
                continue
            if DIRECTIVE_RE.match(lines[cursor]):
                break
            cursor += 1

        chunk = lines[start:cursor]
        first = chunk[0].strip()
        m = DIRECTIVE_RE.match(chunk[0])
        directive = m.group(1).upper() if m else None
        if directive == "FROM":
            stage_index += 1
        blocks.append(
            Block(
                lines=chunk,
                directive=directive,
                stage_index=stage_index if directive != "FROM" else stage_index,
                text="".join(chunk),
                first_line=first,
            )
        )
    return blocks


def count_from_in_text(text: str) -> int:
    return sum(1 for line in text.splitlines() if re.match(r"^\s*FROM\b", line, re.IGNORECASE))


def first_from_line_index(text: str) -> int:
    for i, line in enumerate(text.splitlines()):
        if re.match(r"^\s*FROM\b", line, re.IGNORECASE):
            return i
    return -1


def classify_block(block: Block) -> str | None:
    t = block.text.lower()
    d = (block.directive or "").upper()
    stage1 = block.stage_index <= 1
    stage2 = block.stage_index >= 2

    if block.directive is None and block.stage_index == 0:
        return "HEADER"

    if d == "ARG" and stage1:
        return "ARG"
    if d == "FROM" and stage1:
        return "FIRST_COMPILER"
    if d == "WORKDIR" and "/build" in t:
        # Force builder WORKDIR into stage-1 section, even if a previous run
        # misplaced it after runtime FROM.
        return "FIRST_COMPILER"
    if d == "WORKDIR" and "/app" in t:
        return "SECOND_WORKDIR"
    if d == "WORKDIR" and stage1:
        # Fallback: keep unknown builder WORKDIR near first compiler section.
        return "FIRST_COMPILER"
    if d == "RUN" and "apt-get install" in t:
        return "APT_GET_INSTALLER"
    if d == "RUN" and ("lucid_lib_skeleton" in t or "generate_lib_skeleton_from_runtime_copy.py" in t):
        return "LIB_SKELETON"
    if d == "RUN" and ("rustup" in t or " rustc" in t or " cargo" in t):
        return "RUSTC_AND_CARGO_SUPPORT"
    if d == "COPY" and "requirements" in t:
        return "COPY_REQUIREMENTS"
    if d == "RUN" and ("pip wheel" in t or "pip install --upgrade pip" in t):
        return "PIP_WHEEL_UPDATE_INSTALL"
    if d == "RUN" and ("lucid_x_files_skeleton" in t or "inject_dockerfile_x_files_skeleton.py" in t):
        return "DIRECTORY_SKELETON"
    if d == "COPY" and stage1:
        return "COPY_DIRECTORIES"
    if d == "RUN" and "rm -rf ./configs/environment" in t:
        return "RUN_RM_RF_CONFIGS_ENV"
    if d == "RUN" and stage1:
        return "COPY_CHECK"

    if d == "FROM" and stage2:
        return "DISTROLESS_COMPILER"
    if d == "ARG" and stage2:
        return "DISTROLESS_ARG"
    if d == "WORKDIR" and stage2:
        return "SECOND_WORKDIR"
    if d == "LABEL" and stage2:
        return "LABEL"
    if d == "ENV" and stage2:
        return "DISTROLESS_ENV"
    if d == "COPY" and stage2 and "--from=" in t and "/build/" not in t:
        return "COPY_LIB_DIRECTORIES"
    if d == "COPY" and stage2 and "--from=" in t and "/build/" in t:
        return "COPY_CONTENT"
    if d == "RUN" and stage2:
        return "COMPILER_CHECKS"
    if d == "EXPOSE" and stage2:
        return "EXPOSE_PORT"
    if d == "HEALTHCHECK" and stage2:
        return "HEALTHCHECK"
    if d == "USER" and stage2:
        return "USER"
    if d == "ENTRYPOINT" and stage2:
        return "ENTRYPOINT"
    if d == "CMD" and stage2:
        return "CMD"
    return None


def normalize_section_name(name: str) -> str:
    s = name.strip().replace("**", "")
    s = re.sub(r"\s+", " ", s)
    # Template lines can carry trailing marker punctuation, e.g. "***".
    s = re.sub(r"[*\s]+$", "", s)
    return s


def resolve_template_name_map(id_to_name: dict[str, str]) -> dict[str, str]:
    return dict(id_to_name)


def reorder_blocks(
    blocks: list[Block],
    template_sections: list[str],
    id_to_name: dict[str, str],
    runtime_start_id: str,
) -> tuple[str, list[Block]]:
    section_map = resolve_template_name_map(id_to_name)
    buckets: dict[str, list[Block]] = {name: [] for name in template_sections}
    unmapped_stage1: list[Block] = []
    unmapped_stage2: list[Block] = []

    for block in blocks:
        internal = classify_block(block)
        if internal is None:
            if block.stage_index <= 1:
                unmapped_stage1.append(block)
            else:
                unmapped_stage2.append(block)
            continue
        tpl_name = section_map.get(internal)
        if tpl_name is None:
            if block.stage_index <= 1:
                unmapped_stage1.append(block)
            else:
                unmapped_stage2.append(block)
            continue
        buckets[tpl_name].append(block)

    out_lines: list[str] = []
    runtime_name = id_to_name.get(runtime_start_id, "DISTROLESS COMPILER")
    runtime_from_idx = template_sections.index(runtime_name) if runtime_name in template_sections else len(template_sections)

    for section in template_sections[:runtime_from_idx]:
        for b in buckets.get(section, []):
            out_lines.extend(b.lines)

    # Keep unknown builder content before runtime FROM.
    for b in unmapped_stage1:
        out_lines.extend(b.lines)

    for section in template_sections[runtime_from_idx:]:
        for b in buckets.get(section, []):
            out_lines.extend(b.lines)

    # Keep unknown runtime content in runtime area.
    for b in unmapped_stage2:
        out_lines.extend(b.lines)

    return "".join(out_lines), (unmapped_stage1 + unmapped_stage2)


def iter_targets(path: Path) -> Iterable[Path]:
    def is_real_dockerfile_name(name: str) -> bool:
        lower = name.lower()
        if ".layout.bak" in lower:
            return False
        # Accept Dockerfile, Dockerfile.* and dockerfile.*
        if not lower.startswith("dockerfile"):
            return False
        # Reject helper/source artifacts like dockerfile_*.py/json/txt.
        if lower.endswith((".py", ".pyc", ".json", ".md", ".txt", ".yaml", ".yml", ".log")):
            return False
        return True

    if path.is_file():
        if is_real_dockerfile_name(path.name):
            yield path
        return
    for p in sorted(path.rglob("*")):
        if not p.is_file():
            continue
        if is_real_dockerfile_name(p.name):
            yield p


def process_file(
    file_path: Path,
    template_sections: list[str],
    id_to_name: dict[str, str],
    runtime_start_id: str,
    write: bool,
    max_unmapped: int,
    backup_ext: str | None,
    dry_run: bool,
) -> tuple[bool, int, str]:
    try:
        original = file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False, 0, "skipped-non-utf8"

    blocks = split_blocks(original)
    rebuilt, unmapped = reorder_blocks(blocks, template_sections, id_to_name, runtime_start_id)
    changed = rebuilt != original
    unmapped_count = len(unmapped)

    # Safety gates: do not write if orientation integrity changes.
    if count_from_in_text(original) != count_from_in_text(rebuilt):
        return False, unmapped_count, "skipped-from-mismatch"
    if first_from_line_index(rebuilt) < 0:
        return False, unmapped_count, "skipped-no-from"
    if first_from_line_index(rebuilt) > first_from_line_index(original) + 200:
        # Guard against catastrophic drift of stage start.
        return False, unmapped_count, "skipped-orientation"
    if write and max_unmapped >= 0 and unmapped_count > max_unmapped:
        return False, unmapped_count, "skipped-unmapped"

    if changed and write and not dry_run:
        if backup_ext:
            backup = file_path.with_name(file_path.name + backup_ext)
            backup.write_text(original, encoding="utf-8")
        file_path.write_text(rebuilt, encoding="utf-8")

    return changed, unmapped_count, "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description="Organize Dockerfiles by Dockerfile-layout section order.")
    parser.add_argument(
        "--template",
        default="",
        help="Optional text template path. JSON map remains source of truth.",
    )
    parser.add_argument("--path", required=True, help="Target Dockerfile file or directory.")
    parser.add_argument(
        "--structure-json",
        default="infrastructure/containers/dockerfile_layout_structure.json",
        help="JSON structure rules file.",
    )
    parser.add_argument("--write", action="store_true", help="Rewrite files in place.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing.")
    parser.add_argument("--backup-ext", default="", help="Optional backup extension (example: .layout.bak). Empty means no backup.")
    parser.add_argument(
        "--max-unmapped",
        type=int,
        default=-1,
        help="Write only when unmapped blocks <= this value. Use -1 to disable gating (default: -1).",
    )
    parser.add_argument("--report-json", default="", help="Optional path to write per-file status report JSON.")
    args = parser.parse_args()

    target_path = Path(args.path).resolve()
    structure_path = Path(args.structure_json).resolve()

    if not target_path.exists():
        raise SystemExit(f"Target path not found: {target_path}")
    if not structure_path.exists():
        raise SystemExit(f"Structure JSON not found: {structure_path}")

    json_sections, id_to_name, runtime_start_id = load_structure_json(structure_path)
    template_sections = json_sections

    if args.template:
        template_path = Path(args.template).resolve()
        if not template_path.exists():
            raise SystemExit(f"Template not found: {template_path}")
        # Optional compatibility check only.
        text_sections = parse_template_sections(template_path.read_text(encoding="utf-8"))
        if text_sections and text_sections != json_sections:
            print(f"warning    | template/json mismatch | using JSON order from {structure_path}")

    files = list(iter_targets(target_path))
    if not files:
        raise SystemExit(f"No Dockerfile* files found under: {target_path}")

    total_changed = 0
    report_rows: list[dict[str, object]] = []
    for file_path in files:
        changed, unmapped_count, state = process_file(
            file_path=file_path,
            template_sections=template_sections,
            id_to_name=id_to_name,
            runtime_start_id=runtime_start_id,
            write=args.write,
            max_unmapped=args.max_unmapped,
            backup_ext=(args.backup_ext or None),
            dry_run=args.dry_run,
        )
        report_rows.append(
            {
                "file": str(file_path),
                "state": state,
                "changed": changed,
                "unmapped": unmapped_count,
            }
        )
        if state != "ok":
            print(f"{state:9} | unmapped={'-':>3} | {file_path}")
            continue
        if changed:
            total_changed += 1
        status = "changed" if changed else "unchanged"
        print(f"{status:9} | unmapped={unmapped_count:3d} | {file_path}")

    mode = "write" if args.write and not args.dry_run else "preview"
    print(f"\nProcessed {len(files)} Dockerfile(s); {total_changed} would change [{mode}].")
    if args.report_json:
        Path(args.report_json).write_text(json.dumps(report_rows, indent=2), encoding="utf-8")
        print(f"Report written: {Path(args.report_json).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
