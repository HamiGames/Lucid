#!/usr/bin/env python3
"""
Alignment helpers for scripts/re-build/*.sh using configs/alignment-mats/gui-services.json.

Subcommands:
  is-gui-compose-file <abs_compose_path> <project_root> <gui_services.json>
  list-gui-compose-files <project_root> <gui_services.json>
  restore [--check] [--stdin] <project_root> <gui_services.json> [compose_file ...]
    With --stdin, compose paths are read from stdin (one per line); avoids Windows argv limits.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List, Set, Tuple


def norm_rel_path(abs_path: str, root: str) -> str:
    return os.path.normpath(
        os.path.relpath(os.path.realpath(abs_path), os.path.realpath(root))
    ).replace("\\", "/")


def norm_json_path(p: str) -> str:
    return p.replace("\\", "/")


def load_gui_index(json_path: str) -> Tuple[Set[str], Set[Tuple[str, str]]]:
    with open(json_path, encoding="utf-8") as fp:
        data = json.load(fp)
    files: Set[str] = set()
    pairs: Set[Tuple[str, str]] = set()
    for svc in data.get("services") or []:
        name = (svc.get("compose_service") or "").strip()
        for cf in svc.get("compose_files") or []:
            cf_n = norm_json_path(cf)
            files.add(cf_n)
            if name:
                pairs.add((cf_n, name))
    return files, pairs


def _is_gui_compose_rel_legacy(rel: str, abs_compose: str, root: str) -> bool:
    """Path heuristics aligned with scripts/re-build/00_rebuild_lib.sh is_gui_compose_file."""
    r = rel.replace("\\", "/")
    needles = (
        "infrastructure/containers/gui/",
        "configs/container/gui/",
        "infrastructure/containers/electron_gui/",
        "configs/container/electron_gui/",
        "gui_api_bridge/",
        "apps/gui-",
    )
    if any(n in r for n in needles):
        return True
    if "electron_gui" in r:
        return True
    if "infrastructure/containers/node/" in r and "gui" in r.lower():
        return True
    if "configs/container/node/" in r and "gui" in r.lower():
        return True
    if "configs/services/gui-" in r:
        return True
    if "infrastructure/containers/services/gui-" in r:
        return True
    if "configs/services/admin-interface" in r:
        return True
    if "configs/services/user-interface" in r:
        return True
    if "infrastructure/containers/services/admin-interface" in r:
        return True
    if "infrastructure/containers/services/user-interface" in r:
        return True

    extra = os.environ.get("EXTRA_GUI_SCAN_DIRS", "")
    if not extra.strip():
        return False
    root_real = os.path.realpath(root)
    abs_real = os.path.realpath(abs_compose)
    for raw in extra.split(":"):
        entry = raw.strip()
        if not entry:
            continue
        if entry.startswith("/") or (len(entry) > 2 and entry[1] == ":"):
            base = os.path.realpath(entry)
        else:
            base = os.path.realpath(os.path.join(root_real, entry.lstrip("./")))
        if abs_real == base or abs_real.startswith(base + os.sep):
            return True
    return False


def is_gui_compose_file(abs_compose: str, root: str, json_path: str) -> bool:
    root_r = os.path.realpath(root)
    abs_c = os.path.realpath(abs_compose)
    rel = norm_rel_path(abs_c, root_r)

    if os.path.isfile(json_path):
        files, _ = load_gui_index(json_path)
        if rel.replace("\\", "/") in files:
            return True

    return _is_gui_compose_rel_legacy(rel, abs_c, root_r)


def is_gui_service(rel_compose: str, service_name: str, pairs: Set[Tuple[str, str]]) -> bool:
    rel = norm_json_path(rel_compose)
    return (rel, service_name) in pairs


def rel_env_paths(compose_file: str, root: str) -> Tuple[str, str]:
    root_p = Path(root).resolve()
    cd = Path(compose_file).resolve().parent
    ed = root_p / "configs" / "environment"
    master = os.path.relpath(ed / ".env.master", cd).replace("\\", "/")
    secrets = os.path.relpath(ed / ".env.secrets", cd).replace("\\", "/")
    return master, secrets


def _env_file_has_suffix(entries: Any, suffix: str) -> bool:
    if entries is None:
        return False
    if isinstance(entries, str):
        return entries.endswith(suffix)
    if isinstance(entries, list):
        for e in entries:
            if isinstance(e, str) and e.rstrip().endswith(suffix):
                return True
    return False


def _volume_covers_env_file(vols: Any, marker: str) -> bool:
    if not vols:
        return False
    if isinstance(vols, list):
        for v in vols:
            if isinstance(v, str) and marker in v:
                return True
            if isinstance(v, dict):
                src = str(v.get("source", ""))
                tgt = str(v.get("target", ""))
                if marker in src or marker in tgt:
                    return True
    return False


def _volumes_use_long_form(vols: Any) -> bool:
    if not isinstance(vols, list):
        return False
    for v in vols:
        if isinstance(v, dict) and v.get("type") == "bind":
            return True
    return False


def _ensure_env_file(svc: dict[str, Any], master: str, secrets: str) -> bool:
    changed = False
    ef = svc.get("env_file")
    if ef is None:
        svc["env_file"] = [master, secrets]
        return True
    if isinstance(ef, str):
        lst = [ef]
        svc["env_file"] = lst
        ef = lst
        changed = True
    if not isinstance(ef, list):
        return changed
    if not _env_file_has_suffix(ef, ".env.master"):
        ef.insert(0, master)
        changed = True
    if not _env_file_has_suffix(ef, ".env.secrets"):
        ef.append(secrets)
        changed = True
    return changed


def _ensure_volumes(svc: dict[str, Any], master: str, secrets: str) -> bool:
    changed = False
    vols = svc.get("volumes")
    if vols is None:
        vols = []
        svc["volumes"] = vols
        changed = True
    if isinstance(vols, dict):
        return changed
    if not isinstance(vols, list):
        return changed

    long_form = _volumes_use_long_form(vols)
    master_bind = f"{master}:/app/configs/.env.master:ro"
    secrets_bind = f"{secrets}:/app/configs/.env.secrets:ro"

    if not _volume_covers_env_file(vols, ".env.master"):
        if long_form:
            vols.append(
                {
                    "type": "bind",
                    "source": master,
                    "target": "/app/configs/.env.master",
                    "read_only": True,
                }
            )
        else:
            vols.append(master_bind)
        changed = True
    if not _volume_covers_env_file(vols, ".env.secrets"):
        if long_form:
            vols.append(
                {
                    "type": "bind",
                    "source": secrets,
                    "target": "/app/configs/.env.secrets",
                    "read_only": True,
                }
            )
        else:
            vols.append(secrets_bind)
        changed = True
    return changed


def restore_compose_file(
    compose_path: str,
    root: str,
    json_path: str,
    *,
    check_only: bool,
) -> Tuple[bool, list[str]]:
    import yaml  # noqa: PLC0415 — optional heavy dep for restore only

    root = str(Path(root).resolve())
    abs_c = str(Path(compose_path).resolve())
    path = Path(abs_c)
    # Never touch timestamped backups; never mutate GUI / user-point stacks.
    if ".bak." in path.name:
        return False, []
    if is_gui_compose_file(abs_c, root, json_path):
        return False, []

    rel = norm_rel_path(abs_c, root)
    _, pairs = load_gui_index(json_path)
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    services = data.get("services")
    if not isinstance(services, dict):
        return False, []

    issues: list[str] = []
    changed = False
    master, secrets = rel_env_paths(abs_c, root)

    for svc_name, svc in list(services.items()):
        if not isinstance(svc, dict):
            continue
        if is_gui_service(rel, svc_name, pairs):
            continue

        if check_only:
            need_ef = not (
                _env_file_has_suffix(svc.get("env_file"), ".env.master")
                and _env_file_has_suffix(svc.get("env_file"), ".env.secrets")
            )
            need_vol = not (
                _volume_covers_env_file(svc.get("volumes"), ".env.master")
                and _volume_covers_env_file(svc.get("volumes"), ".env.secrets")
            )
            if need_ef or need_vol:
                issues.append(f"{rel}: service {svc_name!r} missing .env.master/.env.secrets wiring")
            continue

        if _ensure_env_file(svc, master, secrets):
            changed = True
        if _ensure_volumes(svc, master, secrets):
            changed = True

    if changed and not check_only:
        out = yaml.dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )
        _maybe_backup_compose(path)
        path.write_text(out, encoding="utf-8", newline="\n")

    return changed, issues


def _maybe_backup_compose(path: Path) -> None:
    if os.environ.get("REBUILD_SKIP_BACKUP", "").strip() == "1":
        return
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bak = path.parent / f"{path.name}.bak.{ts}"
    shutil.copy2(path, bak)


def cmd_is_gui_compose_file(args: argparse.Namespace) -> int:
    ok = is_gui_compose_file(args.compose_path, args.root, args.json)
    return 0 if ok else 1


def cmd_list_gui_compose_files(args: argparse.Namespace) -> int:
    files, _ = load_gui_index(args.json)
    for f in sorted(files):
        print(f)
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    try:
        import yaml  # noqa: F401, PLC0415 — required for restore; fail fast
    except ImportError:
        print("restore requires PyYAML (e.g. pip install pyyaml)", file=sys.stderr)
        return 2

    if getattr(args, "stdin", False):
        paths: List[str] = [ln.strip() for ln in sys.stdin if ln.strip()]
    else:
        paths = list(args.compose_paths or [])

    if not paths:
        return 0

    all_issues: list[str] = []
    patched = 0
    errors = 0
    for c in paths:
        if not c.endswith((".yml", ".yaml")):
            continue
        if ".bak." in os.path.basename(c):
            continue
        if not os.path.isfile(c):
            continue
        try:
            changed, issues = restore_compose_file(
                c, args.root, args.json, check_only=args.check
            )
        except Exception as exc:  # noqa: BLE001 — surface YAML/OS errors per file
            print(f"[restore] skip (error): {c}: {exc}", file=sys.stderr)
            errors += 1
            continue
        all_issues.extend(issues)
        if changed:
            patched += 1
            rel = norm_rel_path(c, args.root)
            print(f"[restore] patched: {rel}", file=sys.stderr)

    if args.check and all_issues:
        for line in all_issues:
            print(line, file=sys.stderr)
        return 1
    if args.check:
        return 0
    if errors:
        return 3
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(description="Lucid GUI alignment / compose restore helpers")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_ig = sub.add_parser("is-gui-compose-file", help="Exit 0 if compose file is listed in gui-services.json")
    p_ig.add_argument("compose_path")
    p_ig.add_argument("root")
    p_ig.add_argument("json")
    p_ig.set_defaults(func=cmd_is_gui_compose_file)

    p_l = sub.add_parser("list-gui-compose-files", help="Print compose_files paths from gui-services.json")
    p_l.add_argument("root")
    p_l.add_argument("json")
    p_l.set_defaults(func=cmd_list_gui_compose_files)

    p_r = sub.add_parser("restore", help="Restore env_file + volumes for non-GUI services")
    p_r.add_argument("--check", action="store_true", help="Only verify; exit 1 if anything missing")
    p_r.add_argument(
        "--stdin",
        action="store_true",
        help="Read compose file paths from stdin (one per line); avoids Windows command-line length limits",
    )
    p_r.add_argument("root")
    p_r.add_argument("json")
    p_r.add_argument("compose_paths", nargs="*")
    p_r.set_defaults(func=cmd_restore)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
