#!/usr/bin/env python3
"""
Scrub ``.env.secrets`` references from Python sources for GUI integration services
listed in ``configs/alignment-mats/gui-services.json``.

Scan roots are derived from each mat entry (``lucid_service``, ``compose_service``,
and fallbacks ``service`` / ``name``), plus shared trees: ``gui/``,
``infrastructure/containers/{gui,electron_gui,node,admin}/``, and canonical dirs for
``admin-interface`` → ``admin/``, ``node-interface`` → ``node/``,
``user-interface`` → ``electron_gui/``. Extra paths: ``--extra-root`` or env
``GUI_SCRUB_EXTRA_ROOTS`` (use ``;`` or ``:`` as separator).

Replaces any remaining mentions with API-gateway-oriented guidance: runtime env vars
(``LUCID_API_GATEWAY_BASE_URL``, ``LUCID_API_GATEWAY_API_KEY``) and optional SSH
material (``LUCID_API_GATEWAY_SSH_HOST``, ``LUCID_API_GATEWAY_SSH_USER``,
``LUCID_API_GATEWAY_SSH_KEY_PATH``). Output must not contain the substring
``.env.secrets``.

Usage:
  gui_scrub_python_env_secrets.py --mode patch|check --project-root <root> \\
      [--gui-services-json <path>]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, MutableSequence, Sequence, Set, Tuple

# After list-literal stripping, apply longest-first replacements so error text stays accurate.
_REPLACEMENT_FRAGMENTS: Tuple[Tuple[str, str], ...] = (
    (
        "docker-compose.yml or .env.secrets",
        "docker-compose.yml or runtime environment variables",
    ),
    (
        "(from .env.foundation, .env.core, .env.secrets)",
        "(from .env.foundation, .env.core; gateway/host credentials via LUCID_API_GATEWAY_* or SSH)",
    ),
    (
        ", .env.secrets",
        "; gateway or host-provisioned credentials (LUCID_API_GATEWAY_BASE_URL, "
        "LUCID_API_GATEWAY_API_KEY; SSH: LUCID_API_GATEWAY_SSH_HOST, "
        "LUCID_API_GATEWAY_SSH_USER, LUCID_API_GATEWAY_SSH_KEY_PATH)",
    ),
)

# Any remaining substring (docstrings, uncommon phrasing).
_GATEWAY_ACCESS_FALLBACK = (
    "gateway or host-provisioned access (LUCID_API_GATEWAY_BASE_URL, "
    "LUCID_API_GATEWAY_API_KEY; optional SSH: LUCID_API_GATEWAY_SSH_HOST, "
    "LUCID_API_GATEWAY_SSH_USER, LUCID_API_GATEWAY_SSH_KEY_PATH)"
)

# Shared Python / container sources for GUI integration (always considered).
_GUI_SHARED_ROOTS: Tuple[str, ...] = (
    "gui",
    "infrastructure/containers/gui",
    "infrastructure/containers/electron_gui",
    "infrastructure/containers/node",
    "infrastructure/containers/admin",
)

_ENV_EXTRA_ROOTS = "GUI_SCRUB_EXTRA_ROOTS"


def _norm_rel(rel: str) -> str:
    rel = rel.strip().replace("\\", "/").lstrip("/")
    if rel.startswith("./"):
        rel = rel[2:]
    return rel


def _add_root(out: MutableSequence[str], seen: Set[str], rel: str) -> None:
    rel = _norm_rel(rel)
    if not rel or rel in seen:
        return
    seen.add(rel)
    out.append(rel)


def _labels_for_service(svc: Dict[str, object]) -> List[str]:
    raw: List[str] = []
    for key in ("lucid_service", "compose_service", "service", "name"):
        v = svc.get(key)
        if isinstance(v, str) and v.strip():
            raw.append(v.strip())
    # De-dupe preserving order
    seen: Set[str] = set()
    out: List[str] = []
    for s in raw:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


# Compose names that do not match top-level folder slugs (admin/ not admin_interface/).
_CANON_TOPLEVEL_BY_LABEL: Dict[str, Tuple[str, ...]] = {
    "admin-interface": ("admin",),
    "node-interface": ("node",),
    "user-interface": ("electron_gui",),
    "user-interfaces": ("electron_gui",),
}


def _candidates_for_label(label: str) -> Tuple[str, ...]:
    """Directory names that might hold this compose/lucid service's Python code."""
    raw = label.strip()
    key = raw.lower()
    if key in _CANON_TOPLEVEL_BY_LABEL:
        return _CANON_TOPLEVEL_BY_LABEL[key]
    under = raw.replace("-", "_")
    hyph = raw
    out: List[str] = [under]
    if hyph != under:
        out.append(hyph)
    return tuple(out)


def _infra_container_subdir(label: str) -> str | None:
    """Map service label to infrastructure/containers/<subdir> when obvious."""
    low = label.strip().lower()
    if low.startswith("gui-"):
        return "gui"
    if low == "admin-interface":
        return "admin"
    if low == "node-interface":
        return "node"
    if low in ("user-interface", "user-interfaces"):
        return "electron_gui"
    return None


def _load_mat(json_path: Path) -> dict:
    with json_path.open(encoding="utf-8") as fp:
        return json.load(fp)


def _gather_scan_roots(
    project_root: Path,
    data: dict,
    extra_from_cli: Sequence[str],
) -> Tuple[List[str], List[str]]:
    """
    Returns (existing_relative_roots, missing_relative_roots) in stable order.
    """
    ordered: List[str] = []
    seen: Set[str] = set()

    for r in _GUI_SHARED_ROOTS:
        _add_root(ordered, seen, r)

    for svc in data.get("services") or []:
        if not isinstance(svc, dict):
            continue
        for label in _labels_for_service(svc):
            for cand in _candidates_for_label(label):
                _add_root(ordered, seen, cand)
            sub = _infra_container_subdir(label)
            if sub:
                _add_root(ordered, seen, f"infrastructure/containers/{sub}")

    for raw in extra_from_cli:
        _add_root(ordered, seen, raw)

    env_extra = os.environ.get(_ENV_EXTRA_ROOTS, "").strip()
    if env_extra:
        sep = ";" if ";" in env_extra else ":"
        for part in env_extra.split(sep):
            _add_root(ordered, seen, part)

    existing: List[str] = []
    missing: List[str] = []
    for rel in ordered:
        base = (project_root / rel).resolve()
        if base.is_dir():
            existing.append(rel)
        else:
            missing.append(rel)

    exist_set = set(existing)

    def _redundant_hyphen_miss(rel: str) -> bool:
        if "-" not in rel:
            return False
        alt = rel.replace("-", "_")
        return alt in exist_set

    missing_report = [m for m in missing if not _redundant_hyphen_miss(m)]
    return existing, missing_report


def _collect_py_files(project_root: Path, rel_dirs: Iterable[str]) -> List[Path]:
    seen: set[Path] = set()
    out: List[Path] = []
    for rel in rel_dirs:
        base = (project_root / rel).resolve()
        if not base.is_dir():
            continue
        for p in base.rglob("*.py"):
            rp = p.resolve()
            if rp in seen:
                continue
            # Skip caches / virtualenvs if nested
            parts = set(p.parts)
            if "__pycache__" in parts or ".venv" in parts:
                continue
            seen.add(rp)
            out.append(p)
    return sorted(out)


def _backup(path: Path) -> None:
    if os.environ.get("REBUILD_SKIP_BACKUP", "").strip() in ("1", "true", "yes"):
        return
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = path.with_name(f"{path.name}.bak.{ts}")
    shutil.copy2(path, dest)


def _strip_env_secrets_literals(text: str) -> str:
    """Remove ``.env.secrets`` entries from lists / tuples (Pydantic env_file, etc.)."""
    for _ in range(32):
        old = text
        text = re.sub(r",\s*['\"]\.env\.secrets['\"]", "", text)
        text = re.sub(r"['\"]\.env\.secrets['\"]\s*,", "", text)
        text = re.sub(r"=\s*\[\s*['\"]\.env\.secrets['\"]\s*\]", "= []", text)
        text = re.sub(r"=\s*\(\s*['\"]\.env\.secrets['\"]\s*\)", "= ()", text)
        text = re.sub(r"['\"]\.env\.secrets['\"]", "", text)
        if text == old:
            break
    # Tidy empty-separator artifacts
    text = re.sub(r"\[\s*,\s*", "[", text)
    text = re.sub(r"\(\s*,\s*", "(", text)
    text = re.sub(r",\s*,\s*", ", ", text)
    text = re.sub(r",\s*\]", "]", text)
    text = re.sub(r",\s*\)", ")", text)
    return text


def _replace_remaining_substring(text: str) -> str:
    if ".env.secrets" not in text:
        return text
    for old, new in _REPLACEMENT_FRAGMENTS:
        text = text.replace(old, new)
    if ".env.secrets" in text:
        text = text.replace(".env.secrets", _GATEWAY_ACCESS_FALLBACK)
    return text


def scrub_python_text(text: str) -> str:
    text = _strip_env_secrets_literals(text)
    text = _replace_remaining_substring(text)
    return text


def _assert_no_secrets_substring(path: Path, text: str) -> None:
    if ".env.secrets" in text:
        raise SystemExit(
            f"Scrub incomplete (still contains legacy secrets filename): {path}"
        )


def run(
    mode: str,
    project_root: Path,
    gui_services_json: Path,
    extra_roots: Sequence[str],
) -> int:
    data = _load_mat(gui_services_json)
    existing, missing = _gather_scan_roots(project_root, data, extra_roots)

    for rel in missing:
        abs_try = (project_root / rel).resolve()
        print(
            f"[WARN] GUI scrub: scan root missing (skipped): {rel} -> {abs_try}",
            file=sys.stderr,
        )

    if not existing:
        print(
            "[ERR ] GUI scrub: no scan roots exist under project root. "
            f"Project root: {project_root.resolve()}",
            file=sys.stderr,
        )
        print(
            "[INFO] Set GUI_SCRUB_EXTRA_ROOTS (colon or semicolon separated rel paths) "
            "or pass --extra-root for your layout.",
            file=sys.stderr,
        )
        return 3

    if os.environ.get("GUI_SCRUB_LIST_ROOTS", "").strip() in ("1", "true", "yes"):
        print("GUI scrub scan roots (existing):", file=sys.stderr)
        for rel in existing:
            print(f"  - {rel}", file=sys.stderr)

    py_files = _collect_py_files(project_root, existing)
    if not py_files:
        print(
            "[WARN] No Python files (*.py) found under resolved GUI scan roots.",
            file=sys.stderr,
        )

    pending: List[Tuple[Path, str]] = []
    for path in py_files:
        raw = path.read_text(encoding="utf-8")
        if ".env.secrets" not in raw:
            continue
        new = scrub_python_text(raw)
        _assert_no_secrets_substring(path, new)
        if new != raw:
            pending.append((path, new))

    if mode == "check":
        if pending:
            rels = "\n".join(str(p.relative_to(project_root)) for p, _ in pending)
            print(
                "Python files still need scrub (run MODE=patch):\n" + rels,
                file=sys.stderr,
            )
            return 1
        return 0

    for path, new in pending:
        _backup(path)
        path.write_text(new, encoding="utf-8")
        print(f"[ OK ] scrubbed {path.relative_to(project_root)}")

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Scrub .env.secrets from GUI-service Python trees.")
    p.add_argument("--mode", choices=("patch", "check"), default="patch")
    p.add_argument("--project-root", type=Path, required=True)
    p.add_argument(
        "--gui-services-json",
        type=Path,
        default=None,
        help="Defaults to <project-root>/configs/alignment-mats/gui-services.json",
    )
    p.add_argument(
        "--extra-root",
        action="append",
        default=[],
        metavar="REL_PATH",
        help="Additional repo-relative directory to scan (repeatable). "
        "Also see env GUI_SCRUB_EXTRA_ROOTS.",
    )
    args = p.parse_args(list(argv) if argv is not None else None)

    root = args.project_root.resolve()
    gj = args.gui_services_json or (root / "configs" / "alignment-mats" / "gui-services.json")
    gj = gj.resolve()
    if not gj.is_file():
        print(f"Missing gui services mat: {gj}", file=sys.stderr)
        return 2

    return run(args.mode, root, gj, args.extra_root)


if __name__ == "__main__":
    raise SystemExit(main())
