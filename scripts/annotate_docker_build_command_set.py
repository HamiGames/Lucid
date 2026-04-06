#!/usr/bin/env python3
# Path: scripts/annotate_docker_build_command_set.py
# File (repo): Lucid/scripts/annotate_docker_build_command_set.py
#
# Builds dockerfile path -> compose / calibration service name mappings from the repo,
# then refreshes Docker-Build-command-set.txt comment lines to include:
#   actual -t image tag, service name, and Dockerfile path.

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Set, Tuple

try:
    import yaml  # type: ignore
except ImportError:
    print("error: PyYAML required (pip install pyyaml)", file=sys.stderr)
    sys.exit(1)

# Path: scripts/annotate_docker_build_command_set.py
EXCLUDE_DIR_PARTS = frozenset(
    {
        "node_modules",
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        ".idea",
    }
)

DOCKERFILE_VAR = re.compile(r"^\$\{[^:]+:-([^}]+)\}\s*$")
FLAG_F = re.compile(r"^\s*-f\s+(\S+)\s*\\?\s*$")
FLAG_T = re.compile(r"^\s*-t\s+(\S+)\s*\\?\s*$")

# Repo paths with no reliable compose/allocation service_name (override only if map lacks key).
EXPLICIT_DOCKERFILE_SERVICE: Dict[str, str] = {
    "infrastructure/containers/.devcontainer/Dockerfile.network-friendly": "devcontainer-network-friendly",
    "infrastructure/containers/.devcontainer/Dockerfile.simple": "devcontainer-simple",
}


def norm_repo_rel(repo_root: Path, posix_path: str) -> str:
    """Stable repo-relative key using resolved path when the file exists."""
    raw = posix_path.strip().strip('"').strip("'")
    raw = raw.replace("\\", "/")
    p = (repo_root / raw).resolve()
    try:
        return str(p.relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return raw


def expand_dockerfile_value(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip().strip('"').strip("'")
    if not s or s == "null":
        return None
    m = DOCKERFILE_VAR.match(s)
    if m:
        return m.group(1).strip()
    if "${" in s:
        return None
    return s


def resolve_dockerfile_path(repo_root: Path, compose_dir: Path, context: str, dockerfile: str) -> Optional[str]:
    df = expand_dockerfile_value(dockerfile)
    if not df:
        return None
    if df.startswith("/"):
        return None
    ctx = (context or ".").strip()
    if ctx.startswith("/"):
        return None
    # Repo-root-relative dockerfile (common in Lucid compose)
    if "/" in df and not df.startswith(("./", "../")):
        return norm_repo_rel(repo_root, df)
    ctx_path = (compose_dir / ctx).resolve()
    full = (ctx_path / df).resolve()
    try:
        return str(full.relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return None


def iter_yaml_files(repo_root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(repo_root):
        parts = set(Path(dirpath).parts)
        if parts & EXCLUDE_DIR_PARTS:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIR_PARTS]
        for name in filenames:
            low = name.lower()
            if low.endswith((".yml", ".yaml")):
                yield Path(dirpath) / name


def load_allocation_map(repo_root: Path, manifest: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not manifest.is_file():
        return out
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return out

    def add_from_dockerfiles_groups() -> None:
        dockerfiles = data.get("dockerfiles")
        if not isinstance(dockerfiles, dict):
            return
        for _group, items in dockerfiles.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                df = item.get("dockerfile")
                sn = item.get("service_name")
                if df is None or sn is None:
                    continue
                dfs = str(df).strip()
                if " " in dfs and not (dfs.startswith('"') and dfs.endswith('"')):
                    continue
                key = norm_repo_rel(repo_root, dfs.strip('"').strip("'"))
                out[key] = str(sn).strip()

    def add_from_unmatched() -> None:
        du = data.get("dockerfiles_unmatched")
        if not isinstance(du, list):
            return
        for item in du:
            if not isinstance(item, dict):
                continue
            df = item.get("dockerfile")
            if not isinstance(df, str):
                continue
            dfs = df.strip()
            if dfs.endswith((".md", ".py", ".json")):
                continue
            lab = item.get("com.lucid.service")
            if not isinstance(lab, str):
                continue
            key = norm_repo_rel(repo_root, dfs)
            out.setdefault(key, lab.strip())

    add_from_dockerfiles_groups()
    add_from_unmatched()
    return out


def walk_for_dockerfile_service_pairs(obj: Any, acc: List[Tuple[str, str]]) -> None:
    if isinstance(obj, dict):
        if "dockerfile" in obj and "service_name" in obj:
            df = obj.get("dockerfile")
            sn = obj.get("service_name")
            if isinstance(df, str) and isinstance(sn, str):
                acc.append((df.strip(), sn.strip()))
        for v in obj.values():
            walk_for_dockerfile_service_pairs(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            walk_for_dockerfile_service_pairs(v, acc)


def collect_compose_mappings(repo_root: Path) -> DefaultDict[str, Set[str]]:
    multi: DefaultDict[str, Set[str]] = defaultdict(set)
    for yml in iter_yaml_files(repo_root):
        try:
            data = yaml.safe_load(yml.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        services = data.get("services")
        if isinstance(services, dict):
            for svc_name, svc_body in services.items():
                if not isinstance(svc_body, dict):
                    continue
                build = svc_body.get("build")
                if not isinstance(build, dict):
                    continue
                df = expand_dockerfile_value(build.get("dockerfile"))
                if not df:
                    continue
                ctx = str(build.get("context", ".") or ".")
                resolved = resolve_dockerfile_path(repo_root, yml.parent, ctx, df)
                if resolved:
                    multi[resolved].add(str(svc_name))
        extra_pairs: List[Tuple[str, str]] = []
        walk_for_dockerfile_service_pairs(data, extra_pairs)
        for df, sn in extra_pairs:
            key = norm_repo_rel(repo_root, df)
            multi[key].add(sn)
    return multi


def basename_fallback(repo_root: Path, norm_key: str, path_map: Dict[str, str]) -> Optional[str]:
    name = Path(norm_key).name
    if name == "Dockerfile" or not name.startswith("Dockerfile."):
        return None
    lookup_file = repo_root / norm_key.replace("/", os.sep)
    if not lookup_file.is_file():
        return None
    hits: Set[str] = set()
    for p, svc in path_map.items():
        cand = repo_root / p.replace("/", os.sep)
        if not cand.is_file():
            continue
        if Path(p).name == name:
            hits.add(svc)
    if len(hits) == 1:
        return next(iter(hits))
    return None


def build_resolver(
    repo_root: Path,
    allocation: Dict[str, str],
    compose_multi: DefaultDict[str, Set[str]],
) -> Tuple[Dict[str, str], List[str]]:
    """path -> single service string; logs unresolved in dry report."""
    combined: Dict[str, str] = {}
    for path, names in compose_multi.items():
        if len(names) == 1:
            combined[path] = next(iter(names))
        else:
            combined[path] = " | ".join(sorted(names))
    # Allocation overrides compose (calibrated names)
    for path, name in allocation.items():
        combined[path] = name
    for logical, svc in EXPLICIT_DOCKERFILE_SERVICE.items():
        k = norm_repo_rel(repo_root, logical)
        combined.setdefault(k, svc)
    warnings: List[str] = []
    return combined, warnings


def resolve_service(repo_root: Path, norm_df: str, path_map: Dict[str, str]) -> str:
    if norm_df in path_map:
        return path_map[norm_df]
    fb = basename_fallback(repo_root, norm_df, path_map)
    if fb:
        return fb
    return "?"


def annotate_text(repo_root: Path, text: str, path_map: Dict[str, str]) -> Tuple[str, List[str]]:
    lines = text.splitlines(keepends=False)
    indices = [i for i, line in enumerate(lines) if line.startswith("# pickme/")]
    issues: List[str] = []
    new_lines = list(lines)

    for k, start in enumerate(indices):
        end = indices[k + 1] if k + 1 < len(indices) else len(lines)
        stanza = lines[start:end]
        df_tag: Optional[str] = None
        image_tag: Optional[str] = None
        for line in stanza:
            fm = FLAG_F.match(line)
            if fm:
                df_tag = fm.group(1)
            tm = FLAG_T.match(line)
            if tm:
                image_tag = tm.group(1)
        if not df_tag or not image_tag:
            issues.append(f"line {start + 1}: missing -f or -t in stanza")
            continue
        key = norm_repo_rel(repo_root, df_tag)
        svc = resolve_service(repo_root, key, path_map)
        if svc == "?":
            issues.append(f"line {start + 1}: unresolved service for {df_tag}")
        new_lines[start] = f"# {image_tag}  service: {svc}  ({df_tag})"

    return "\n".join(new_lines) + ("\n" if text.endswith("\n") else ""), issues


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    parser = argparse.ArgumentParser(
        description="Annotate Docker-Build-command-set.txt with compose/calibration service names."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Lucid repository root",
    )
    parser.add_argument(
        "--commands-file",
        type=Path,
        default=None,
        help="Path to Docker-Build-command-set.txt (default: <repo-root>/Docker-Build-command-set.txt)",
    )
    parser.add_argument(
        "--allocation-manifest",
        type=Path,
        default=None,
        help="allocation_manifest.yml path",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write updated content to --commands-file",
    )
    parser.add_argument(
        "--emit-stdout",
        action="store_true",
        help="When not using --write, print full annotated file to stdout (default: summary only)",
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    cmd_file = (args.commands_file or repo_root / "Docker-Build-command-set.txt").resolve()
    manifest = (
        args.allocation_manifest
        or repo_root
        / "infrastructure/containers/services/x_lucid_cluster_calibration/allocation_manifest.yml"
    ).resolve()

    if not cmd_file.is_file():
        print(f"error: commands file not found: {cmd_file}", file=sys.stderr)
        return 1

    allocation = load_allocation_map(repo_root, manifest)
    compose_multi = collect_compose_mappings(repo_root)
    path_map, _ = build_resolver(repo_root, allocation, compose_multi)

    original = cmd_file.read_text(encoding="utf-8-sig")
    updated, issues = annotate_text(repo_root, original, path_map)

    for msg in issues:
        print(msg, file=sys.stderr)

    if args.write:
        cmd_file.write_text(updated, encoding="utf-8", newline="\n")
        print(f"Wrote {cmd_file}")
    elif args.emit_stdout:
        sys.stdout.write(updated)
    else:
        print(f"Annotated {cmd_file.name}: {len(issues)} stanza note(s). Use --write to save or --emit-stdout to print.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
