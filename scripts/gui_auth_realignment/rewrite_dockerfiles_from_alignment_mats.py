#!/usr/bin/env python3
"""
File: scripts/gui_auth_realignment/rewrite_dockerfiles_from_alignment_mats.py

Each manifest resolves to one authoritative Dockerfile: typically ``host-config.yml`` ``source_dockerfile``,
else optional manifest ``source_dockerfile``, else the built-in fallback map for unhosted base images.
Duplicate or legacy paths are **not** targets unless resolution points there—use ``-v`` to print paths.

**Canonical entry point:** apply ``configs/alignment-mats/*_manifest.json`` (and related
``mapping_compose_to_service_id.json`` + ``infrastructure/containers/host-config.yml``) to each
service's **authoritative** ``source_dockerfile``. Compose names in manifests are resolved to
host-config keys by the mapping file (GUI aliases), then by ``service_name``, YAML key, or ``tags``
so all manifests under ``configs/alignment-mats/`` can be applied—not only the few rows in the
mapping JSON. A small built-in fallback table covers compose services whose Dockerfiles exist but
have no ``host-config.yml`` block (e.g. ``java-base``, ``python-base``). To **generate** manifest JSON
from the tree, use ``list_gui_service_files.py``; to **apply** mats to Dockerfiles, use this script.

Uses JSON under configs/alignment-mats/ (``*_manifest.json`` with compose_service), plus
mapping_compose_to_service_id.json and infrastructure/containers/host-config.yml,
to rewrite the authoritative Dockerfile (source_dockerfile) for each service:

  - com.lucid.service / com.lucid.expose (expose only if port > 0)
  - LUCID_SERVICE_HTTP_PATH, LUCID_SERVICE_HOST_IP, LUCID_HOST_CONFIG_SERVICE_NAME
  - PORT=, SERVICE_NAME= (when present in ENV)
  - Header lines: # Image:, # Build:, # Port: / # port:

Optional: merge image string from configs/services/gui-services.json when compose_service matches.

If several manifests resolve to the same ``source_dockerfile``, their mat file lists are **merged**
(unique paths), metadata (LABEL/ENV) is taken from the ``host-config.yml`` block for that Dockerfile
(best match on ``service_name`` / compose names), and one write updates the shared image once.

Layout sections (see infrastructure/containers/dockerfile_layout_structure.json):
  #10 COPY (builder plain COPY): from each manifest's ``py``, ``yml``/``yaml``, ``json``, and
  ``alignment_json`` under # LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_* (default on;
  see --no-apply-mat-copy-directories). Default ``--mat-copy-mode files``: one ``COPY`` per manifest
  entry (JSON array form when paths contain whitespace); ``--mat-copy-mode directories`` uses the
  same quoting rules for pruned directory COPY specs.
  When ``# LUCID_ALIGNMENT_MAT_RUNTIME_COPY_BEGIN`` ... ``END`` exists, ``--mat-copy-mode files`` also
  emits one ``COPY --from=builder`` per path into ``/app/...`` (``--no-mat-runtime-file-copies`` to skip).
  #7 COPY_REQUIREMENTS / #8 PIP wheels,   #9 DIRECTORY_SKELETON, #20 COPY_CONTENT are driven by
  infrastructure/containers/inject_dockerfile_x_files_skeleton.py after that when you pass
  --inject-copy-layout (uses x-files-listing.txt). Default is **no** inject — LABEL/ENV/header +
  mat COPY only. Optional
  --inject-strip-build-scaffold runs cleanup before layout inject. Use --validate-x-files-copy
  for x-files.json runtime COPY checks.

Usage (repo root):
  python scripts/gui_auth_realignment/rewrite_dockerfiles_from_alignment_mats.py
  python scripts/gui_auth_realignment/rewrite_dockerfiles_from_alignment_mats.py --dry-run
  python scripts/gui_auth_realignment/rewrite_dockerfiles_from_alignment_mats.py \\
      --no-mat-runtime-file-copies \\
      --only-dockerfile infrastructure/containers/tor/Dockerfile.tor-proxy-02
  python scripts/gui_auth_realignment/rewrite_dockerfiles_from_alignment_mats.py --backup
  python scripts/gui_auth_realignment/rewrite_dockerfiles_from_alignment_mats.py \\
      --inject-copy-layout
  python scripts/gui_auth_realignment/rewrite_dockerfiles_from_alignment_mats.py \\
      --inject-strip-build-scaffold --validate-x-files-copy --strict-x-files-copy

**Default:** layout inject is **off** — it depends on repo-root ``x-files-listing.txt``, which this
workflow does not use. You get host-config metadata + manifest mat COPY (#10) only. Pass
``--inject-copy-layout`` only when you maintain ``x-files-listing.txt`` and want skeleton/runtime
layout sync. Omit ``--dry-run`` to write Dockerfiles.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml  # type: ignore
except ImportError as e:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from e

_HERE = Path(__file__).resolve().parent

DEFAULT_MAT_DIR = Path("configs/alignment-mats")
HOST_CONFIG = Path("infrastructure/containers/host-config.yml")
MAPPING = _HERE / "mapping_compose_to_service_id.json"
GUI_SERVICES = Path("configs/services/gui-services.json")
DEFAULT_X_FILES = Path("x-files.json")
INJECT_SCRIPT = Path("infrastructure/containers/inject_dockerfile_x_files_skeleton.py")

# Compose names with no host-config.yml entry but a single authoritative Dockerfile (repo-relative).
MAT_COMPOSE_TO_DOCKERFILE_FALLBACK: Dict[str, str] = {
    "base-runtime": "infrastructure/containers/base/Dockerfile.base",
    "gui-strap": "infrastructure/docker/distroless/gui/Dockerfile.gui",
    "java-base": "infrastructure/containers/base/Dockerfile.java-base",
    "python-base": "infrastructure/containers/base/Dockerfile.python-base",
    "server-common": "infrastructure/docker/common/Dockerfile",
}


def _compose_alias_strings(compose_service: str, manifest_doc: Optional[Dict[str, Any]]) -> List[str]:
    """Strings to match against host-config ``service_name``, YAML keys, and ``tags``."""
    out: List[str] = []
    cs = compose_service.strip()
    if cs:
        out.extend((cs, cs.replace("-", "_")))
    if manifest_doc:
        for n in manifest_doc.get("associated_needles") or []:
            if not isinstance(n, str):
                continue
            s = n.strip()
            if not s:
                continue
            out.append(s)
            if "-" in s:
                out.append(s.replace("-", "_"))
    seen: set[str] = set()
    uniq: List[str] = []
    for a in out:
        if a not in seen:
            seen.add(a)
            uniq.append(a)
    return uniq

RUNTIME_COPY_BEGIN = "# LUCID_RUNTIME_COPY_FROM_BUILD_BEGIN"
RUNTIME_COPY_END = "# LUCID_RUNTIME_COPY_FROM_BUILD_END"
RE_BUILD_COPY_DIR = re.compile(
    r"^\s*COPY\s+--from=\S+(?:\s+--chown=\S+)?\s+(?P<src>/build/(?P<rel>[^/\s]+)/)\s+",
    re.MULTILINE,
)

MARK_MAT_COPY_BEGIN = "# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_BEGIN"
MARK_MAT_COPY_END = "# LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_END"
RUNTIME_MAT_COPY_BEGIN_PREFIX = "# LUCID_ALIGNMENT_MAT_RUNTIME_COPY_BEGIN"
RUNTIME_MAT_COPY_END = "# LUCID_ALIGNMENT_MAT_RUNTIME_COPY_END"
MARK_SKELETON_END = "# LUCID_X_FILES_SKELETON_END"
MARK_WHEEL_END = "# LUCID_PIP_WHEELS_END"
# Builder plain COPY: not --from=, not heredoc <<
RE_PLAIN_COPY_LINE = re.compile(
    r"^(\s*)COPY\s+(?!--from=)(?!<<)(\S+)\s+(\S+)\s*(\\)?\s*$",
)


def _mat_file_path_to_copy_spec(norm_file: str) -> Optional[Tuple[str, str]]:
    """One repo-relative file → one (host_src/, dest/)."""
    p = norm_file.strip().lstrip("./").replace("\\", "/")
    if not p or "/" not in p:
        return None
    seg = p.split("/")
    # Files under pkg/pkg/... use flattening COPY pkg/pkg/ ./pkg/ (one spec for all such files).
    if len(seg) >= 2 and seg[0] == seg[1]:
        P = seg[0]
        return (f"{P}/{P}/", f"./{P}/")
    parent = p.rsplit("/", 1)[0]
    if not parent:
        return None
    parts = parent.split("/")
    if len(parts) == 1:
        return (f"{parts[0]}/", f"./{parts[0]}/")
    return (f"{parent}/", f"./{parent}/")


def _covers_copy_spec(parent_src: str, parent_dst: str, child_src: str, child_dst: str) -> bool:
    """True if a directory COPY (parent_*) already includes all paths covered by child_*."""
    ps = parent_src.rstrip("/")
    cs = child_src.rstrip("/")
    if not (cs.startswith(ps + "/") or cs == ps):
        return False
    pdd = parent_dst.rstrip("/")
    cdd = child_dst.rstrip("/")
    return cdd.startswith(pdd + "/") or cdd == pdd


def _prune_subsumed_directory_specs(dirs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """Prefer broader COPY (shorter source path) and drop narrower child directory COPYs."""
    ordered = sorted(dirs, key=lambda t: (len(t[0]), t[0], t[1]))
    kept: List[Tuple[str, str]] = []
    for s, d in ordered:
        if any(_covers_copy_spec(pk, pd, s, d) for pk, pd in kept):
            continue
        kept = [(pk, pd) for pk, pd in kept if not _covers_copy_spec(s, d, pk, pd)]
        kept.append((s, d))
    return sorted(kept, key=lambda t: (t[0], t[1]))


def _normalize_mat_relpath(item: str) -> Optional[str]:
    p = item.replace("\\", "/").strip().lstrip("./")
    if not p or p.startswith("#"):
        return None
    return p


def collect_mat_manifest_paths(doc: Dict[str, Any]) -> List[str]:
    """Every repo-relative file path listed in the manifest (ordered, unique)."""
    raw: List[str] = []
    for key in ("py", "yml", "yaml", "json", "alignment_json"):
        for item in doc.get(key) or []:
            if isinstance(item, str):
                n = _normalize_mat_relpath(item)
                if n:
                    raw.append(n)
    seen: set[str] = set()
    out: List[str] = []
    for p in sorted(raw):
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _dockerfile_copy_one(
    src: str,
    dest: str,
    *,
    from_builder: bool = False,
    chown: Optional[str] = None,
) -> str:
    """Single COPY line; JSON form when paths need quoting (spaces etc.)."""
    needs_json = (
        " " in src
        or "\t" in src
        or '"' in src
        or " " in dest
        or "\t" in dest
        or '"' in dest
    )
    if from_builder and chown:
        prefix = f"COPY --from=builder --chown={chown} "
    elif from_builder:
        prefix = "COPY --from=builder "
    else:
        prefix = "COPY "
    if needs_json:
        return prefix + json.dumps([src, dest])
    return prefix + f"{src} {dest}"


def build_mat_copy_block_files(
    rel_files: List[str], compose_service: str, mat_basename: str
) -> str:
    """One plain COPY per manifest path (builder WORKDIR /build)."""
    lines = [
        MARK_MAT_COPY_BEGIN,
        f"# alignment-mat {mat_basename}: compose_service={compose_service!r} "
        f"— explicit manifest paths → {len(rel_files)} builder COPY line(s).",
    ]
    for rel in rel_files:
        lines.append(_dockerfile_copy_one(rel, f"./{rel}", from_builder=False))
    lines.append(MARK_MAT_COPY_END)
    return "\n".join(lines) + "\n"


def _locate_runtime_mat_region(text: str) -> Optional[Tuple[int, int]]:
    """Return [start, end) slice indices covering the full runtime mat block."""
    m0 = re.search(
        rf"^{re.escape(RUNTIME_MAT_COPY_BEGIN_PREFIX)}.*\n",
        text,
        re.MULTILINE,
    )
    if not m0:
        return None
    tail = text[m0.end() :]
    m1 = re.search(rf"^{re.escape(RUNTIME_MAT_COPY_END)}\s*\n?", tail, re.MULTILINE)
    if not m1:
        return None
    return m0.start(), m0.end() + m1.end()


def extract_runtime_chown_for_build_artifacts(text: str) -> str:
    """Default chown for COPY --from=builder /build/... (first match in Dockerfile)."""
    m = re.search(
        r"COPY\s+--from=builder\s+--chown=([^\s]+)\s+/build/",
        text,
    )
    return m.group(1) if m else "65532:65532"


def build_mat_runtime_copy_block_files(
    rel_files: List[str],
    chown: str,
    compose_service: str,
    mat_basename: str,
) -> str:
    """Runtime stage: copy each file from builder → /app (same relpath)."""
    lines = [
        f"{RUNTIME_MAT_COPY_BEGIN_PREFIX} — {compose_service} manifest (explicit files from {mat_basename})",
        f"# alignment-mat: {len(rel_files)} path(s) COPY --from=builder → /app/...",
    ]
    for rel in rel_files:
        lines.append(
            _dockerfile_copy_one(
                f"/build/{rel}",
                f"/app/{rel}",
                from_builder=True,
                chown=chown,
            )
        )
    lines.append(RUNTIME_MAT_COPY_END)
    return "\n".join(lines) + "\n"


def collect_mat_copy_specs(doc: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Directory COPY specs plus optional file COPYs as (src, dst) with src not ending in /."""
    paths: List[str] = []
    for key in ("py", "yml", "yaml", "json", "alignment_json"):
        for item in doc.get(key) or []:
            if isinstance(item, str):
                paths.append(item.replace("\\", "/").strip())

    norm_paths = [p for p in paths if p and not p.startswith("#")]
    flat_pkgs = set()
    for p in norm_paths:
        seg = p.split("/")
        if len(seg) >= 2 and seg[0] == seg[1]:
            flat_pkgs.add(seg[0])

    specs: set[Tuple[str, str]] = set()
    for path in norm_paths:
        spec = _mat_file_path_to_copy_spec(path)
        if spec:
            specs.add(spec)

    # Broad COPY pkg/ ./pkg/ breaks flattening COPY pkg/pkg/ ./pkg/; use per-file COPY for pkg/* roots.
    file_copies: List[Tuple[str, str]] = []
    for P in flat_pkgs:
        broad = (f"{P}/", f"./{P}/")
        if broad not in specs:
            continue
        specs.remove(broad)
        pref = f"{P}/"
        for path in norm_paths:
            if not path.startswith(pref):
                continue
            rest = path[len(pref) :]
            if "/" in rest or not rest:
                continue
            file_copies.append((path, f"./{P}/"))

    dir_only = [(s, d) for s, d in specs if s.endswith("/")]
    dir_pruned = _prune_subsumed_directory_specs(dir_only)
    fc_sorted = sorted(set(file_copies), key=lambda t: (t[0], t[1]))
    out: List[Tuple[str, str]] = []
    out.extend(dir_pruned)
    out.extend(fc_sorted)
    return out


def build_mat_copy_block(specs: List[Tuple[str, str]], compose_service: str, mat_basename: str) -> str:
    lines = [
        MARK_MAT_COPY_BEGIN,
        f"# alignment-mat {mat_basename}: compose_service={compose_service!r} "
        f"— manifest py/yml/yaml/json → builder COPY (#10).",
    ]
    for src, dst in specs:
        lines.append(_dockerfile_copy_one(src, dst, from_builder=False))
    lines.append(MARK_MAT_COPY_END)
    return "\n".join(lines) + "\n"


def _warn_missing_mat_paths(repo: Path, doc: Dict[str, Any]) -> None:
    for key in ("py", "yml", "yaml", "json", "alignment_json"):
        for item in doc.get(key) or []:
            if not isinstance(item, str):
                continue
            rel = item.replace("\\", "/").strip().lstrip("./")
            if not rel:
                continue
            p = repo / rel
            if not p.is_file():
                print(f"WARN: alignment mat lists missing path (not a file): {rel}", file=sys.stderr)


def _mat_copy_src_dst_pair(line: str) -> Optional[Tuple[str, str]]:
    """Parse builder plain COPY or JSON-array COPY into (src, dst); None if not a match."""
    s = line.strip()
    if not s.upper().startswith("COPY"):
        return None
    if "<<" in s:
        return None
    # Exec form: optional flags then ["src", "dst"] (required for paths with whitespace).
    lb = s.rfind("[")
    if lb >= 0 and s.rstrip().endswith("]"):
        try:
            arr = json.loads(s[lb:])
            if (
                isinstance(arr, list)
                and len(arr) == 2
                and isinstance(arr[0], str)
                and isinstance(arr[1], str)
            ):
                return arr[0], arr[1]
        except json.JSONDecodeError:
            pass
    m = RE_PLAIN_COPY_LINE.match(s)
    if m:
        return m.group(2), m.group(3)
    return None


def strip_redundant_plain_copies_after_mat_block(text: str, specs: set[Tuple[str, str]]) -> str:
    """Remove following duplicate COPY lines that repeat the same (src, dst) as the mat block."""
    idx = text.find(MARK_MAT_COPY_END)
    if idx < 0:
        return text
    line_break = text.find("\n", idx)
    if line_break < 0:
        return text
    head = text[: line_break + 1]
    tail = text[line_break + 1 :]
    kept: List[str] = []
    for line in tail.splitlines(keepends=True):
        pair = _mat_copy_src_dst_pair(line.rstrip("\n"))
        if pair and pair in specs:
            continue
        kept.append(line)
    return head + "".join(kept)


def _insert_mat_copy_after_x_files_skeleton(text: str, block: str) -> str:
    """Insert mat block immediately after # LUCID_X_FILES_SKELETON_END (typical builder layout)."""
    anchor = MARK_SKELETON_END
    idx = text.find(anchor)
    if idx < 0:
        return text
    line_end = text.find("\n", idx)
    insert_at = (line_end + 1) if line_end >= 0 else idx + len(anchor)
    return text[:insert_at] + "\n" + block + "\n" + text[insert_at:]


def patch_alignment_mat_copies(
    text: str,
    doc: Dict[str, Any],
    repo: Path,
    mat_path: Path,
    *,
    warn_missing: bool,
    mat_copy_mode: str,
    apply_runtime_file_copies: bool,
) -> str:
    """
    Rewrite LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_* from the manifest.

    ``mat_copy_mode``:
      - ``files`` (default): one ``COPY`` per manifest entry (JSON-array form if paths need quoting),
        plus optional runtime ``COPY --from=builder`` file lines inside LUCID_ALIGNMENT_MAT_RUNTIME_COPY_*.
      - ``directories``: legacy directory-pruned COPY specs only (builder), with the same quoting rules.
    """
    if warn_missing:
        _warn_missing_mat_paths(repo, doc)
    cs = str(doc.get("compose_service", ""))
    mat_base = mat_path.name

    if mat_copy_mode == "files":
        rel_files = collect_mat_manifest_paths(doc)
        specs_set: set[Tuple[str, str]] = {(r, f"./{r}") for r in rel_files}
        block = build_mat_copy_block_files(rel_files, cs, mat_base)
    elif mat_copy_mode == "directories":
        specs_list = collect_mat_copy_specs(doc)
        specs_set = set(specs_list)
        block = build_mat_copy_block(specs_list, cs, mat_base)
    else:
        raise ValueError(f"unknown mat_copy_mode: {mat_copy_mode!r}")

    i0 = text.find(MARK_MAT_COPY_BEGIN)
    i1 = text.find(MARK_MAT_COPY_END)
    if i0 >= 0 and i1 > i0:
        before = text[:i0]
        after = text[i1 + len(MARK_MAT_COPY_END) :]
        while after.startswith("\n"):
            after = after[1:]
        merged = before + block + after
    else:
        merged_sk = _insert_mat_copy_after_x_files_skeleton(text, block)
        if merged_sk != text:
            merged = merged_sk
        else:
            merged = _insert_mat_copy_block_before_first_plain_copy(text, block)

    merged = strip_redundant_plain_copies_after_mat_block(merged, specs_set)

    if apply_runtime_file_copies and mat_copy_mode == "files":
        region = _locate_runtime_mat_region(merged)
        if region:
            chown = extract_runtime_chown_for_build_artifacts(merged)
            rt_block = build_mat_runtime_copy_block_files(rel_files, chown, cs, mat_base)
            s, e = region
            merged = merged[:s] + rt_block + merged[e:]
        else:
            print(
                f"NOTE: no {RUNTIME_MAT_COPY_BEGIN_PREFIX} ... {RUNTIME_MAT_COPY_END} region in Dockerfile; "
                f"skipped runtime per-file COPY for {mat_base} ({cs}).",
                file=sys.stderr,
            )

    return merged


def patch_alignment_mat_copy_directories(
    text: str,
    doc: Dict[str, Any],
    repo: Path,
    mat_path: Path,
    *,
    warn_missing: bool,
) -> str:
    """Backward-compatible wrapper: directory-only mat COPY (legacy)."""
    return patch_alignment_mat_copies(
        text,
        doc,
        repo,
        mat_path,
        warn_missing=warn_missing,
        mat_copy_mode="directories",
        apply_runtime_file_copies=False,
    )


def _insert_mat_copy_block_before_first_plain_copy(text: str, block: str) -> str:
    anchor = MARK_SKELETON_END
    idx = text.rfind(anchor)
    if idx < 0:
        idx = text.rfind(MARK_WHEEL_END)
    if idx < 0:
        print(
            "WARN: no LUCID_X_FILES_SKELETON_END / LUCID_PIP_WHEELS_END; "
            "appending mat COPY block at EOF.",
            file=sys.stderr,
        )
        return text.rstrip() + "\n\n" + block

    line_start = text.find("\n", idx)
    if line_start < 0:
        return text.rstrip() + "\n\n" + block
    line_start += 1
    pos = line_start
    for line in text[line_start:].splitlines(keepends=True):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            pos += len(line)
            continue
        if RE_PLAIN_COPY_LINE.match(line.rstrip("\n")):
            return text[:pos] + block + text[pos:]
        pos += len(line)
    return text.rstrip() + "\n\n" + block


def _repo_root(arg: Optional[str]) -> Path:
    if arg:
        return Path(arg).resolve()
    return Path(__file__).resolve().parents[2]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _gui_services_by_compose(repo: Path) -> Dict[str, Dict[str, Any]]:
    p = repo / GUI_SERVICES
    if not p.is_file():
        return {}
    data = _load_json(p)
    out: Dict[str, Dict[str, Any]] = {}
    for row in data.get("services") or []:
        if isinstance(row, dict) and row.get("compose_service"):
            out[str(row["compose_service"])] = row
    return out


def _iter_manifests(mat_dir: Path) -> List[Path]:
    if not mat_dir.is_dir():
        return []
    out: List[Path] = []
    for p in sorted(mat_dir.glob("*_manifest.json")):
        if p.name.startswith("."):
            continue
        try:
            doc = _load_json(p)
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(doc, dict) and doc.get("compose_service"):
            out.append(p)
    return out


def merge_manifest_mat_docs(docs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Union ``py``/``yml``/``yaml``/``json``/``alignment_json`` paths from several mats (deduped, stable)."""
    keys = ("py", "yml", "yaml", "json", "alignment_json")
    merged: Dict[str, Any] = {}
    for k in keys:
        bucket: List[str] = []
        seen_norm: set[str] = set()
        for d in docs:
            for item in d.get(k) or []:
                if not isinstance(item, str):
                    continue
                n = _normalize_mat_relpath(item)
                if not n or n in seen_norm:
                    continue
                seen_norm.add(n)
                bucket.append(n)
        merged[k] = bucket
    return merged


def _host_blocks_by_source_dockerfile(
    services: Dict[str, Any],
) -> Dict[str, List[Tuple[str, Dict[str, Any]]]]:
    """Normalized ``source_dockerfile`` path → [(host key, block), ...]."""
    by_dfp: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
    for sid, block in services.items():
        if not isinstance(block, dict):
            continue
        sdf = str(block.get("source_dockerfile") or "").replace("\\", "/").strip()
        if not sdf:
            continue
        by_dfp.setdefault(sdf, []).append((str(sid), block))
    return by_dfp


def _pick_host_meta_for_dfp(
    dfp: str,
    host_by_dfp: Dict[str, List[Tuple[str, Dict[str, Any]]]],
    compose_services_in_group: List[str],
) -> Optional[Tuple[str, Dict[str, Any]]]:
    rows = host_by_dfp.get(dfp)
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0]
    want = set(compose_services_in_group)
    for sid, block in rows:
        sn = str(block.get("service_name") or "")
        if sn in want:
            return (sid, block)
    for sid, block in rows:
        tags = block.get("tags") or []
        if isinstance(tags, list) and want.intersection(str(t) for t in tags):
            return (sid, block)
    return rows[0]


def _gui_image_for(
    gui_by: Dict[str, Dict[str, Any]],
    service_name: str,
    compose_candidates: List[str],
) -> Optional[str]:
    for key in [service_name, *compose_candidates]:
        if not key:
            continue
        row = gui_by.get(key)
        if isinstance(row, dict) and row.get("image"):
            return str(row["image"])
    return None


def patch_dockerfile_text(
    text: str,
    *,
    service_name: str,
    service_id: str,
    host_ip: str,
    port: int,
    http_path: str,
    image: Optional[str],
) -> str:
    """Apply deterministic replacements; avoid touching com.lucid.service_id hashes."""
    s = text

    s = re.sub(r'com\.lucid\.service="[^"]*"', f'com.lucid.service="{service_name}"', s)
    s = re.sub(r'com\.lucid\.expose="[^"]*"', f'com.lucid.expose="{port}"', s)

    s = re.sub(
        r"LUCID_SERVICE_HTTP_PATH=[^\s\\\n]+",
        f"LUCID_SERVICE_HTTP_PATH={http_path}",
        s,
    )
    # With or without quotes
    s = re.sub(
        r'LUCID_SERVICE_HOST_IP="[^"]*"',
        f'LUCID_SERVICE_HOST_IP="{host_ip}"',
        s,
    )
    s = re.sub(
        r"LUCID_SERVICE_HOST_IP=[^\s\\\n]+",
        f"LUCID_SERVICE_HOST_IP={host_ip}",
        s,
    )
    s = re.sub(
        r"LUCID_HOST_CONFIG_SERVICE_NAME=[^\s\\\n]+",
        f"LUCID_HOST_CONFIG_SERVICE_NAME={service_id}",
        s,
    )
    s = re.sub(r'PORT="[0-9]+"', f'PORT="{port}"', s)
    s = re.sub(r'SERVICE_NAME="[^"]*"', f'SERVICE_NAME="{service_name}"', s)

    if image:
        s = re.sub(r"^#\s*Image:\s*.*$", f"# Image: {image}", s, flags=re.MULTILINE)
        s = re.sub(
            r"(docker build[^\n]*\s-t\s+)([^\s]+)",
            lambda m: m.group(1) + image,
            s,
            count=1,
            flags=re.MULTILINE,
        )

    s = re.sub(r"^#\s*[Pp]ort:\s*.*$", f"# Port: {port}", s, flags=re.MULTILINE)

    return s


def resolve_host_config_service_id(
    services: Dict[str, Any],
    compose_service: str,
    mapping: Dict[str, str],
    manifest_doc: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """
    Map manifest ``compose_service`` to a ``host-config.yml`` services key.

    Order: explicit ``mapping_compose_to_service_id.json`` entry, then best match in host-config
    (``service_name``, YAML key, hyphen→underscore key, ``tags`` exact match, then tag prefix match
    for manifest ``associated_needles`` e.g. ``lucid_elasticsearch`` vs ``lucid_elasticsearch_http``).
    Returns ``None`` if no block exists (caller may use manifest / fallback Dockerfile path).
    """
    cs = compose_service.strip()
    if not cs:
        return None

    if cs in mapping:
        sid = mapping[cs]
        if not isinstance(services.get(sid), dict):
            raise KeyError(
                f"mapping maps compose_service {cs!r} to host-config key {sid!r}, "
                f"but services.{sid} is missing or not a mapping"
            )
        return str(sid)

    aliases = _compose_alias_strings(cs, manifest_doc)
    alias_set = set(aliases)
    by_sid: Dict[str, int] = {}

    for sid, block in services.items():
        if not isinstance(block, dict):
            continue
        sid_s = str(sid)
        ranks: List[int] = []
        sn = str(block.get("service_name") or "")
        if sn in alias_set:
            ranks.append(0)
        if sid_s in alias_set:
            ranks.append(1)
        tags = block.get("tags") or []
        tags_str = [str(t) for t in tags] if isinstance(tags, list) else []
        if alias_set.intersection(tags_str):
            ranks.append(3)
        else:
            for a in aliases:
                if not a or len(a) < 3:
                    continue
                for t in tags_str:
                    if t == a or t.startswith(a + "_") or t.startswith(a + "-"):
                        ranks.append(4)
                        break
                if any(x == 4 for x in ranks):
                    break
        if not ranks:
            continue
        rmin = min(ranks)
        prev = by_sid.get(sid_s)
        if prev is None or rmin < prev:
            by_sid[sid_s] = rmin

    if not by_sid:
        return None
    best_rank = min(by_sid.values())
    best_sids = sorted(sid for sid, r in by_sid.items() if r == best_rank)
    if len(best_sids) > 1:
        raise ValueError(
            f"compose_service {cs!r} is ambiguous in host-config (multiple entries tie at "
            f"rank {best_rank}): {best_sids!r}"
        )
    return best_sids[0]


def resolve_meta(
    repo: Path,
    compose_service: str,
    mapping: Dict[str, str],
    services: Dict[str, Any],
    gui_row: Optional[Dict[str, Any]],
    manifest_doc: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Dict[str, Any]]:
    sid = resolve_host_config_service_id(services, compose_service, mapping, manifest_doc)

    image: Optional[str] = None
    if gui_row and gui_row.get("image"):
        image = str(gui_row["image"])

    if sid is not None:
        block = services.get(sid)
        if not isinstance(block, dict):
            raise KeyError(f"host-config services.{sid} missing")
        service_name = str(block.get("service_name") or compose_service)
        port = int(block.get("port") or 0)
        http_path = str(block.get("http_path") or f"http://{service_name}:{port}/app")
        host_ip = str(block.get("host_ip") or "")
        dockerfile_rel = str(block.get("source_dockerfile") or "").replace("\\", "/")
        if not dockerfile_rel:
            raise ValueError(f"host-config {sid} has no source_dockerfile")

        meta = {
            "compose_service": compose_service,
            "host_config_service_id": sid,
            "service_name": service_name,
            "service_id": sid,
            "port": port,
            "http_path": http_path,
            "host_ip": host_ip,
            "dockerfile_rel": dockerfile_rel,
            "image": image,
        }
        return meta["dockerfile_rel"], meta

    dockerfile_rel = ""
    if manifest_doc and isinstance(manifest_doc.get("source_dockerfile"), str):
        dockerfile_rel = manifest_doc["source_dockerfile"].strip().replace("\\", "/")
    if not dockerfile_rel:
        dockerfile_rel = MAT_COMPOSE_TO_DOCKERFILE_FALLBACK.get(compose_service, "").replace("\\", "/")
    if not dockerfile_rel:
        raise KeyError(
            f"compose_service {compose_service!r} has no host-config entry, no manifest "
            f'"source_dockerfile", and no built-in MAT_COMPOSE_TO_DOCKERFILE_FALLBACK path'
        )
    full = repo / dockerfile_rel
    if not full.is_file():
        raise ValueError(f"resolved Dockerfile missing for {compose_service!r}: {full}")

    synthetic_id = compose_service.replace("-", "_")
    port = 0
    meta = {
        "compose_service": compose_service,
        "host_config_service_id": synthetic_id,
        "service_name": compose_service,
        "service_id": synthetic_id,
        "port": port,
        "http_path": f"http://{compose_service}:{port}/app",
        "host_ip": "",
        "dockerfile_rel": dockerfile_rel,
        "image": image,
    }
    return meta["dockerfile_rel"], meta


def _load_x_files_canonical(repo: Path, xfiles_path: Path) -> Dict[str, str]:
    p = xfiles_path if xfiles_path.is_absolute() else repo / xfiles_path
    data = _load_json(p)
    m = data.get("section_to_canonical") or {}
    if not isinstance(m, dict):
        raise ValueError(f"{p}: section_to_canonical must be an object")
    return {str(k).replace("\\", "/"): str(v) for k, v in m.items()}


def _x_files_allows_build_dir(canonical_paths: Dict[str, str], dir_rel: str) -> bool:
    """True if some repo path key is dir_rel or starts with dir_rel/."""
    d = dir_rel.strip("/").replace("\\", "/")
    if not d:
        return False
    for k in canonical_paths:
        kn = k.replace("\\", "/")
        if kn == d or kn.startswith(d + "/"):
            return True
    return False


def validate_runtime_copy_against_x_files(
    repo: Path, dockerfile: Path, canonical_paths: Dict[str, str]
) -> List[str]:
    """Return human-readable issues for COPY_CONTENT (runtime) dirs not covered by x-files.json keys."""
    text = dockerfile.read_text(encoding="utf-8")
    i0 = text.find(RUNTIME_COPY_BEGIN)
    i1 = text.find(RUNTIME_COPY_END)
    if i0 < 0 or i1 < 0 or i1 <= i0:
        return []
    chunk = text[i0 : i1 + len(RUNTIME_COPY_END)]
    seen_dirs: set[str] = set()
    issues: List[str] = []
    for m in RE_BUILD_COPY_DIR.finditer(chunk):
        rel = m.group("rel")
        if rel in seen_dirs:
            continue
        seen_dirs.add(rel)
        if not _x_files_allows_build_dir(canonical_paths, rel):
            rel_df = dockerfile.relative_to(repo).as_posix() if dockerfile.is_relative_to(repo) else str(dockerfile)
            issues.append(
                f"{rel_df}: runtime COPY /build/{rel}/ not covered by any x-files.json "
                f"section_to_canonical key prefixed by {rel!r}/"
            )
    return issues


def _inject_script_path(repo: Path) -> Optional[Path]:
    inj = repo / INJECT_SCRIPT
    return inj if inj.is_file() else None


def run_inject_strip_build_scaffold(
    repo: Path,
    dockerfile_rel_posix: str,
    *,
    apply_write: bool,
) -> int:
    inj = _inject_script_path(repo)
    if not inj:
        print(f"ERROR: inject script missing: {repo / INJECT_SCRIPT}", file=sys.stderr)
        return 2
    cmd: List[str] = [
        sys.executable,
        str(inj),
        "--only",
        dockerfile_rel_posix,
        "--strip-build-scaffold",
        "--verbose",
    ]
    if apply_write:
        cmd.append("--apply")
    print(f"+ {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=str(repo))


def run_inject_copy_layout(
    repo: Path,
    dockerfile_rel_posix: str,
    *,
    apply_write: bool,
    no_wheels: bool,
) -> int:
    inj = _inject_script_path(repo)
    if not inj:
        print(f"ERROR: inject script missing: {repo / INJECT_SCRIPT}", file=sys.stderr)
        return 2
    cmd: List[str] = [
        sys.executable,
        str(inj),
        "--only",
        dockerfile_rel_posix,
        "--run-full-with-sync",
        "--verbose",
    ]
    if no_wheels:
        cmd.append("--no-wheels")
    if apply_write:
        cmd.append("--apply")
    print(f"+ {' '.join(cmd)}", flush=True)
    return subprocess.call(cmd, cwd=str(repo))


def _norm_only_dockerfile_path(p: str) -> str:
    """Repo-relative POSIX path for --only-dockerfile matching."""
    return Path(p.strip()).as_posix().lstrip("./")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Alignment mats → Dockerfiles: apply configs/alignment-mats manifests + host-config "
            "(and built-in Dockerfile fallbacks when unset) to each service source_dockerfile "
            "(metadata, mat py/yml COPY block #10, optional inject for layout #7-9/#20)."
        ),
        epilog=(
            "To apply changes: omit --dry-run. Layout inject is off by default (no x-files-listing.txt). "
            "Pass --inject-copy-layout only if you use that listing + inject_dockerfile_x_files_skeleton."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--mat-dir", default=str(DEFAULT_MAT_DIR), help="Dir of *_manifest.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--backup", action="store_true")
    ap.add_argument(
        "--apply-mat-copy-directories",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "After metadata patch, rewrite # LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_* from manifest "
            "py/yml/json paths. Default: on. --no-apply-mat-copy-directories: skip mat-driven COPY lines."
        ),
    )
    ap.add_argument(
        "--mat-copy-mode",
        choices=("files", "directories"),
        default="files",
        help=(
            "When mat COPY is enabled: 'files' = one COPY per manifest path under "
            "LUCID_ALIGNMENT_MAT_COPY_DIRECTORIES_* (default; JSON-array COPY when a path contains "
            "whitespace); optional runtime per-file COPY under LUCID_ALIGNMENT_MAT_RUNTIME_COPY_* "
            "when --mat-runtime-file-copies. "
            "'directories' = legacy pruned directory COPY specs only (no runtime file expansion)."
        ),
    )
    ap.add_argument(
        "--mat-runtime-file-copies",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "With --mat-copy-mode files, rewrite LUCID_ALIGNMENT_MAT_RUNTIME_COPY_BEGIN…END to "
            "one COPY --from=builder line per manifest path. Default: on. "
            "No-op if that region is missing in the Dockerfile."
        ),
    )
    ap.add_argument(
        "--inject-copy-layout",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "After metadata + optional mat COPY, run inject_dockerfile_x_files_skeleton.py "
            "--run-full-with-sync per target Dockerfile (layout #7-9, #20). Requires repo-root "
            "x-files-listing.txt. Default: off (alignment rewrite does not use that file). "
            "With --dry-run, inject runs without --apply."
        ),
    )
    ap.add_argument(
        "--inject-strip-build-scaffold",
        action=argparse.BooleanOptionalAction,
        default=False,
        help=(
            "Before layout inject, run --strip-build-scaffold per Dockerfile (remove redundant "
            "mkdir-only RUN blocks under /build). Default: off. Respects --dry-run."
        ),
    )
    ap.add_argument(
        "--inject-no-wheels",
        action="store_true",
        help="With layout inject, pass --no-wheels to the injector.",
    )
    ap.add_argument(
        "--x-files",
        type=Path,
        default=DEFAULT_X_FILES,
        help="x-files.json path (repo-relative) for --validate-x-files-copy",
    )
    ap.add_argument(
        "--validate-x-files-copy",
        action="store_true",
        help=(
            "After writes, check LUCID_RUNTIME_COPY_FROM_BUILD_* dirs against "
            "section_to_canonical keys in x-files.json."
        ),
    )
    ap.add_argument(
        "--strict-x-files-copy",
        action="store_true",
        help="With --validate-x-files-copy, exit 3 if any runtime COPY dir is not in x-files.",
    )
    ap.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print absolute repo root and per-target Dockerfile + alignment mat paths (stdout).",
    )
    ap.add_argument(
        "--only-dockerfile",
        action="append",
        default=[],
        metavar="REPO_REL_PATH",
        help=(
            "Limit rewrites to this host-config source_dockerfile (repo-relative, forward slashes). "
            "Repeat to allow several paths. Example: infrastructure/containers/tor/Dockerfile.tor-proxy-02"
        ),
    )
    args = ap.parse_args()
    repo = _repo_root(args.repo_root)
    if args.verbose:
        print(f"Repo root (absolute): {repo.resolve()}", flush=True)
    mat_dir = Path(args.mat_dir)
    if not mat_dir.is_absolute():
        mat_dir = repo / mat_dir

    hc_path = repo / HOST_CONFIG
    if not hc_path.is_file():
        print(f"Missing {hc_path}", file=sys.stderr)
        return 2
    hc = _load_yaml(hc_path)
    services = hc.get("services") or {}
    if not isinstance(services, dict):
        print("host-config services invalid", file=sys.stderr)
        return 2

    mp = _load_json(MAPPING)
    cmap = mp.get("mappings") or {}
    if not isinstance(cmap, dict):
        print("mapping file invalid", file=sys.stderr)
        return 2
    cmap = {str(k): str(v) for k, v in cmap.items()}

    gui_by = _gui_services_by_compose(repo)
    manifests = _iter_manifests(mat_dir)
    if not manifests:
        print(f"No manifests with compose_service under {mat_dir}", file=sys.stderr)
        return 2

    resolved: List[Tuple[Path, Dict[str, Any], str, Dict[str, Any]]] = []
    manifests_skipped = 0

    for mf in manifests:
        doc = _load_json(mf)
        cs = str(doc.get("compose_service"))
        try:
            dfp, meta = resolve_meta(repo, cs, cmap, services, gui_by.get(cs), doc)
        except (KeyError, ValueError) as e:
            manifests_skipped += 1
            print(f"SKIP {mf.name}: {e}", file=sys.stderr)
            continue
        full = repo / Path(dfp)
        if not full.is_file():
            manifests_skipped += 1
            print(f"SKIP {cs}: Dockerfile missing {full}", file=sys.stderr)
            continue
        resolved.append((mf, doc, dfp, meta))

    host_by_dfp = _host_blocks_by_source_dockerfile(services)
    by_dfp: Dict[str, List[Tuple[Path, Dict[str, Any], Dict[str, Any]]]] = defaultdict(list)
    for mf, doc, dfp, meta in resolved:
        by_dfp[dfp].append((mf, doc, meta))

    plan: List[Tuple[Path, str, Dict[str, Any]]] = []
    for dfp in sorted(by_dfp.keys()):
        grp = by_dfp[dfp]
        mfs = [t[0] for t in grp]
        docs = [t[1] for t in grp]
        metas = [t[2] for t in grp]
        compose_ss = sorted({str(d.get("compose_service")) for d in docs})
        merged_doc = merge_manifest_mat_docs(docs)
        merged_doc["compose_service"] = "+".join(compose_ss)

        picked = _pick_host_meta_for_dfp(dfp, host_by_dfp, compose_ss)
        alignment_mats_posix = [
            p.resolve().relative_to(repo.resolve()).as_posix() for p in mfs
        ]
        if picked:
            sid, block = picked
            sn = str(block.get("service_name") or compose_ss[0])
            port = int(block.get("port") or 0)
            http_path = str(block.get("http_path") or f"http://{sn}:{port}/app")
            plan_meta: Dict[str, Any] = {
                "compose_service": "+".join(compose_ss),
                "merged_compose_services": compose_ss,
                "host_config_service_id": sid,
                "service_name": sn,
                "service_id": sid,
                "port": port,
                "http_path": http_path,
                "host_ip": str(block.get("host_ip") or ""),
                "dockerfile_rel": dfp,
                "image": _gui_image_for(gui_by, sn, compose_ss),
                "alignment_mats": alignment_mats_posix,
                "alignment_mat": alignment_mats_posix[0],
                "_merged_mat_document": merged_doc,
            }
        else:
            stable = sorted(zip(mfs, docs, metas), key=lambda x: str(x[1].get("compose_service")))
            _, _, m0 = stable[0]
            plan_meta = {
                **m0,
                "compose_service": "+".join(compose_ss),
                "merged_compose_services": compose_ss,
                "image": _gui_image_for(gui_by, str(m0.get("service_name") or ""), compose_ss)
                or m0.get("image"),
                "alignment_mats": alignment_mats_posix,
                "alignment_mat": alignment_mats_posix[0],
                "_merged_mat_document": merged_doc,
            }
        plan.append((repo / Path(dfp), dfp, plan_meta))
        if len(grp) > 1:
            print(
                f"MERGED {len(grp)} alignment mats -> {dfp}: {' + '.join(compose_ss)}",
                flush=True,
            )

    if args.only_dockerfile:
        want = {_norm_only_dockerfile_path(x) for x in args.only_dockerfile if str(x).strip()}
        prev_n = len(plan)
        plan = [
            (path, dfp, meta)
            for path, dfp, meta in plan
            if _norm_only_dockerfile_path(dfp) in want
        ]
        if prev_n and not plan:
            print(
                "No plan entries match --only-dockerfile "
                f"{sorted(want)!r} (had {prev_n} resolved Dockerfile(s); "
                "paths must match host-config source_dockerfile exactly).",
                file=sys.stderr,
            )
            return 1
        print(
            f"Filtered plan: {len(plan)} Dockerfile(s) (--only-dockerfile {sorted(want)!r})",
            flush=True,
        )

    if not plan:
        print("Nothing to rewrite.", file=sys.stderr)
        return 1

    all_compose = sorted({c for _, _, m in plan for c in m.get("merged_compose_services") or []})
    services_line = ", ".join(all_compose)
    skip_frag = f", {manifests_skipped} manifest(s) skipped" if manifests_skipped else ""
    print(
        f"Plan: {len(plan)} Dockerfile(s); {len(resolved)} manifest row(s) resolved"
        f"{skip_frag}; services: {services_line}",
        flush=True,
    )

    if args.inject_copy_layout or args.inject_strip_build_scaffold or args.apply_mat_copy_directories:
        print(
            "Note: UNCHANGED/WROTE refers to this step's Dockerfile text (metadata + optional mat COPY #10; "
            "with --inject-copy-layout, inject may then refine #7-9/#20 after save).",
            flush=True,
        )

    metadata_mat_pass_writes = 0

    for path, dfp, meta in plan:
        mat_rel = str(meta.get("alignment_mat") or "")
        mat_path = repo / mat_rel if mat_rel else repo
        merged_doc = meta.get("_merged_mat_document")
        raw = path.read_text(encoding="utf-8")
        patched = patch_dockerfile_text(
            raw,
            service_name=meta["service_name"],
            service_id=meta["service_id"],
            host_ip=meta["host_ip"],
            port=meta["port"],
            http_path=meta["http_path"],
            image=meta.get("image"),
        )
        if args.apply_mat_copy_directories:
            if not isinstance(merged_doc, dict):
                print(f"ERROR: internal: missing merged mat document for {dfp}", file=sys.stderr)
                return 2
            if not mat_rel or not mat_path.is_file():
                print(f"ERROR: alignment mat not found for {dfp}: {mat_path}", file=sys.stderr)
                return 2
            new = patch_alignment_mat_copies(
                patched,
                merged_doc,
                repo,
                mat_path,
                warn_missing=True,
                mat_copy_mode=str(args.mat_copy_mode),
                apply_runtime_file_copies=bool(
                    args.mat_runtime_file_copies and str(args.mat_copy_mode) == "files"
                ),
            )
        else:
            new = patched
        if new != raw:
            metadata_mat_pass_writes += 1
        if new == raw:
            print(f"UNCHANGED {dfp} ({meta['compose_service']})", flush=True)
            if args.verbose:
                print(f"  Dockerfile (absolute): {path.resolve()}", flush=True)
                for am in meta.get("alignment_mats") or []:
                    print(f"  alignment mat (absolute): {(repo / am).resolve()}", flush=True)
            continue
        if args.dry_run:
            print(f"[dry-run] would rewrite {dfp} ({meta['compose_service']})", flush=True)
            if args.verbose:
                print(f"  Dockerfile (absolute): {path.resolve()}", flush=True)
                for am in meta.get("alignment_mats") or []:
                    print(f"  alignment mat (absolute): {(repo / am).resolve()}", flush=True)
            continue
        if args.backup:
            bak = path.with_suffix(path.suffix + f".bak.{_utc()}")
            shutil.copy2(path, bak)
        path.write_text(new, encoding="utf-8")
        print(f"WROTE {dfp} ({meta['compose_service']} -> {meta['service_name']})", flush=True)
        if args.verbose:
            print(f"  Dockerfile (absolute): {path.resolve()}", flush=True)
            for am in meta.get("alignment_mats") or []:
                print(f"  alignment mat (absolute): {(repo / am).resolve()}", flush=True)

    x_canon: Optional[Dict[str, str]] = None
    if (args.validate_x_files_copy or args.strict_x_files_copy) and not args.dry_run:
        try:
            x_canon = _load_x_files_canonical(repo, args.x_files)
        except (OSError, json.JSONDecodeError, ValueError) as e:
            print(f"ERROR: x-files load: {e}", file=sys.stderr)
            return 2
    elif args.validate_x_files_copy or args.strict_x_files_copy:
        print("NOTE: skipping x-files validation while --dry-run (no stable on-disk state).", file=sys.stderr)

    inject_writes = not args.dry_run
    inject_apply = bool(args.inject_copy_layout and inject_writes)
    strip_apply = bool(args.inject_strip_build_scaffold and inject_writes)

    if args.inject_copy_layout or args.inject_strip_build_scaffold:
        if args.dry_run:
            print(
                "NOTE: --dry-run runs injector subprocess(es) WITHOUT --apply (no Dockerfile writes "
                "from inject). Omit --dry-run to patch metadata and apply layout/cleanup on disk.",
                file=sys.stderr,
            )
        seen_inj: set[str] = set()
        for _path, dfp, _meta in plan:
            if dfp in seen_inj:
                continue
            seen_inj.add(dfp)
            if args.inject_strip_build_scaffold:
                rc = run_inject_strip_build_scaffold(repo, dfp, apply_write=strip_apply)
                if rc != 0:
                    print(f"ERROR: inject --strip-build-scaffold exited {rc} for {dfp}", file=sys.stderr)
                    return rc
            if args.inject_copy_layout:
                rc = run_inject_copy_layout(
                    repo,
                    dfp,
                    apply_write=inject_apply,
                    no_wheels=bool(args.inject_no_wheels),
                )
                if rc != 0:
                    print(f"ERROR: inject --run-full-with-sync exited {rc} for {dfp}", file=sys.stderr)
                    return rc
        inj_n = len(seen_inj)
        parts: List[str] = []
        if args.inject_strip_build_scaffold:
            parts.append(
                f"strip-build-scaffold: {inj_n} Dockerfile(s) ({'applied' if strip_apply else 'dry-run'})"
            )
        if args.inject_copy_layout:
            parts.append(
                f"layout (#7-#20): {inj_n} Dockerfile(s) ({'--apply' if inject_apply else 'dry-run'})"
            )
        print(f"Inject pass: {'; '.join(parts)}", flush=True)

    if (
        metadata_mat_pass_writes == 0
        and (
            args.apply_mat_copy_directories or args.inject_copy_layout or args.inject_strip_build_scaffold
        )
    ):
        print(
            "Note: metadata + mat COPY (#10) already match every target Dockerfile on disk (no first-pass writes). "
            "The injector may still report updated/unchanged per file. "
            "If you expected edits, regenerate configs/alignment-mats/*_manifest.json, confirm you are in the same "
            "clone as this repo root, and open only host-config source_dockerfile paths (use -v to print them).",
            file=sys.stderr,
        )

    if x_canon and (args.validate_x_files_copy or args.strict_x_files_copy) and not args.dry_run:
        all_issues: List[str] = []
        seen_v: set[str] = set()
        for path, dfp, _meta in plan:
            if dfp in seen_v:
                continue
            seen_v.add(dfp)
            all_issues.extend(validate_runtime_copy_against_x_files(repo, path, x_canon))
        for line in all_issues:
            print(line, file=sys.stderr)
        if all_issues and args.strict_x_files_copy:
            return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
