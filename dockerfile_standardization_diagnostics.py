"""
path: dockerfile_standardization_diagnostics.py
Diagnostic tool for Lucid Dockerfile standardization issues.
Identifies gaps in canonical paths, port mappings, and x-files tracking.

Duplicate declared ports use the same rule as repair_dockerfile_standardization.py:
``ports.port`` from the recalibration map when set; otherwise the first numeric EXPOSE
on disk. Missing-EXPOSE failures still require a real Dockerfile with no numeric EXPOSE.
"""

import argparse
import json
import re
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None


def load_host_services(path: Path) -> Dict[str, dict]:
    """Load host-config.yml ``services`` block (same shape as repair script)."""
    if not path.is_file():
        return {}
    if yaml:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict) and isinstance(raw.get("services"), dict):
                return dict(raw["services"])
        except yaml.YAMLError:
            pass
    return {}


def service_keys_for_port(host: Dict[str, dict], port: int) -> List[str]:
    out: List[str] = []
    for sk, sd in host.items():
        if not isinstance(sd, dict):
            continue
        try:
            if int(sd.get("port")) == int(port):
                out.append(sk)
        except (TypeError, ValueError):
            continue
    return sorted(out)


def write_port_overrides_template(
    issues: Dict,
    dockerfiles: Dict,
    host: Dict[str, dict],
    out_path: Path,
    map_path: Path,
) -> int:
    """
    JSON for manual ``ports_service_key`` choices. Not parseable from ``containers_ports_report.txt``;
    use this file with ``repair_dockerfile_standardization.py --overrides``.
    """
    overrides: Dict[str, Dict[str, object]] = {}
    seen: set[str] = set()
    for block in issues.get("duplicate_port_service_conflicts", []):
        port = block.get("port")
        if port is None:
            continue
        try:
            pnum = int(port)
        except (TypeError, ValueError):
            continue
        candidates = service_keys_for_port(host, pnum)
        for p in block.get("paths", []):
            if p in seen:
                continue
            seen.add(p)
            meta = dockerfiles.get(p, {}) or {}
            cur = meta.get("ports_service_key")
            overrides[p] = {
                "port": pnum,
                "candidates": candidates,
                "ports_service_key": cur if cur in candidates else "",
            }
    doc = {
        "_meta": {
            "note": (
                "containers_ports_report.txt is human-readable only. "
                "Fill ports_service_key (host-config.yml service id) per path, then run repair with --overrides."
            ),
            "repair_command": "python repair_dockerfile_standardization.py --overrides PATH [--in-place]",
            "source_map": str(map_path).replace("\\", "/"),
        },
        "overrides": overrides,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, indent=2), encoding="utf-8", newline="\n")
    return len(overrides)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parent


def extract_expose_ports(dockerfile_path: Path) -> List[int]:
    """All numeric ports from EXPOSE lines (order preserved, deduped). Matches repair script."""
    if not dockerfile_path.is_file():
        return []
    try:
        text = dockerfile_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    found: List[int] = []
    seen: set[int] = set()
    for m in re.finditer(r"^\s*EXPOSE\s+([^\s#\\]+)", text, re.MULTILINE | re.IGNORECASE):
        chunk = m.group(1).strip()
        for tok in re.split(r"[\s/]+", chunk):
            if tok.isdigit():
                p = int(tok)
                if p not in seen:
                    seen.add(p)
                    found.append(p)
    return found


def normalize_path_prefixes(prefixes: Optional[List[str]]) -> List[str]:
    """Normalize repo-relative prefixes (forward slashes, no trailing slash)."""
    if not prefixes:
        return []
    out: List[str] = []
    for raw in prefixes:
        p = raw.strip().replace("\\", "/").rstrip("/")
        if p:
            out.append(p)
    return out


@contextmanager
def tee_stdout_to_file(path: Optional[Path], *, also_stdout: bool = True):
    """
    Duplicate everything written to sys.stdout to ``path`` (UTF-8).
    If ``also_stdout`` is False, stdout is only the file (shell ``> file`` style).
    """
    if path is None:
        yield
        return
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    file_obj = out_path.open("w", encoding="utf-8", newline="\n")
    old_stdout = sys.stdout
    try:
        if also_stdout:

            class _TeeOut:
                __slots__ = ("_a", "_b")

                def __init__(self, a, b):
                    self._a = a
                    self._b = b

                def write(self, s):
                    self._a.write(s)
                    self._b.write(s)
                    return len(s)

                def flush(self):
                    self._a.flush()
                    self._b.flush()

                @property
                def encoding(self):
                    return getattr(self._a, "encoding", "utf-8")

            sys.stdout = _TeeOut(old_stdout, file_obj)
        else:
            sys.stdout = file_obj
        yield
    finally:
        sys.stdout = old_stdout
        file_obj.close()


def path_under_prefixes(rel_path: str, prefixes: List[str]) -> bool:
    """True if rel_path is exactly a prefix or under one of the given directory prefixes."""
    if not prefixes:
        return True
    rel = rel_path.replace("\\", "/")
    for p in prefixes:
        if rel == p or rel.startswith(p + "/"):
            return True
    return False


def load_json(path: str) -> dict:
    """Load JSON file with error handling."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR loading {path}: {e}", file=sys.stderr)
        return {}


def print_report_preamble(prefixes: List[str], n_scoped: int, n_all: int) -> None:
    """Title banner and optional --under scope lines (must run inside tee when writing -o)."""
    if prefixes:
        print(f"(Scoped to {len(prefixes)} path prefix(es): {', '.join(prefixes)})")
        print(f"Dockerfiles in scope: {n_scoped} of {n_all}")
        print()
    print("=" * 80)
    print("DOCKERFILE STANDARDIZATION DIAGNOSTIC REPORT")
    print("=" * 80)
    print()


def analyze_recalibration_map(
    recal_path: str,
    path_prefixes: Optional[List[str]] = None,
    repo_root: Optional[Path] = None,
) -> Tuple[Dict, Dict, int, List[str]]:
    """
    Analyze the recalibration map and identify issues. Returns (issues, dockerfiles, n_all, prefixes).

    Missing EXPOSE uses Dockerfile on disk. Duplicate declared ports group the same way as
    repair_dockerfile_standardization.py: map ``ports.port`` when set, else first EXPOSE on disk.
    """
    data = load_json(recal_path)
    root = repo_root if repo_root is not None else repo_root_from_script()

    dockerfiles_all = data.get("dockerfiles", {})
    prefixes = normalize_path_prefixes(path_prefixes)
    dockerfiles = {
        k: v
        for k, v in dockerfiles_all.items()
        if path_under_prefixes(k, prefixes)
    }
    issues = {
        "missing_canonical_path": [],
        "missing_port_mapping": [],
        "missing_dockerfile_file": [],
        "map_port_mismatch": [],
        "missing_x_files_entry": [],
        "missing_infrastructure_rel": [],
        "missing_service_ids": [],
        "duplicate_ports": defaultdict(list),
        "duplicate_port_service_conflicts": [],
        "ambiguous_mappings": [],
    }

    declared_port_map = defaultdict(list)

    # Analyze each Dockerfile
    for dockerfile_path, metadata in dockerfiles.items():
        # Check canonical path
        if not metadata.get("canonical_path"):
            issues["missing_canonical_path"].append(dockerfile_path)

        full = root / dockerfile_path.replace("\\", "/")
        expose_ports = extract_expose_ports(full) if full.is_file() else []

        map_port: Optional[int] = None
        ports_block = metadata.get("ports")
        if isinstance(ports_block, dict) and ports_block.get("port") is not None:
            try:
                map_port = int(ports_block["port"])
            except (TypeError, ValueError):
                map_port = None

        if not full.is_file():
            issues["missing_dockerfile_file"].append(dockerfile_path)
        elif not expose_ports:
            issues["missing_port_mapping"].append(dockerfile_path)
        elif map_port is not None and map_port != expose_ports[0]:
            issues["map_port_mismatch"].append(
                {
                    "path": dockerfile_path,
                    "map_port": map_port,
                    "expose_primary": expose_ports[0],
                }
            )

        # Declared port for duplicate grouping (same precedence as repair script)
        declared: Optional[int] = None
        if map_port is not None:
            declared = map_port
        elif full.is_file() and expose_ports:
            declared = expose_ports[0]
        if declared is not None:
            declared_port_map[declared].append(dockerfile_path)

        # Check x-files entry
        if not metadata.get("in_x_files"):
            issues["missing_x_files_entry"].append(dockerfile_path)

        # Check infrastructure_containers_rel
        if not metadata.get("infrastructure_containers_rel"):
            issues["missing_infrastructure_rel"].append(dockerfile_path)

        # Check service IDs
        if not metadata.get("lucid_service_ids"):
            issues["missing_service_ids"].append(dockerfile_path)
    
    # Same declared port (map port if set, else first EXPOSE); sorted paths match repair remap order
    for port, dockerfiles_list in declared_port_map.items():
        if len(dockerfiles_list) > 1:
            issues["duplicate_ports"][port] = sorted(dockerfiles_list)

    # Same Dockerfile EXPOSE port: map metadata disagrees on service / key
    issues["duplicate_port_service_conflicts"] = []
    for port, paths in issues["duplicate_ports"].items():
        metas = [dockerfiles[p] for p in paths if p in dockerfiles]
        keys = {m.get("ports_service_key") for m in metas}
        names = {m.get("ports", {}).get("service_name") for m in metas if m.get("ports")}
        keys.discard(None)
        names.discard(None)
        if len(keys) > 1 or len(names) > 1:
            issues["duplicate_port_service_conflicts"].append(
                {
                    "port": port,
                    "paths": list(paths),
                    "ports_service_keys": sorted(keys),
                    "service_names": sorted(names),
                }
            )

    return issues, dockerfiles, len(dockerfiles_all), prefixes

def print_issue_summary(issues: Dict, total_dockerfiles: int):
    """Print summary of identified issues."""
    print("\nISSUE SUMMARY:\n")
    print(
        "(Duplicate port groups: map ports.port when set, else first EXPOSE on disk — same as repair script.)\n"
    )

    issue_counts = {
        "Missing Canonical Paths": len(issues["missing_canonical_path"]),
        "Missing EXPOSE (Dockerfile on disk)": len(issues["missing_port_mapping"]),
        "Dockerfile path not on disk": len(issues.get("missing_dockerfile_file", [])),
        "Map port != Dockerfile EXPOSE": len(issues.get("map_port_mismatch", [])),
        "Missing X-Files Entries": len(issues["missing_x_files_entry"]),
        "Missing Infrastructure Rel": len(issues["missing_infrastructure_rel"]),
        "Missing Service IDs": len(issues["missing_service_ids"]),
        "Duplicate declared ports (map or EXPOSE)": len(issues["duplicate_ports"]),
        "Port+service mismatches": len(issues.get("duplicate_port_service_conflicts", [])),
    }
    
    for issue_type, count in issue_counts.items():
        percentage = (count / total_dockerfiles) * 100
        status = "[FAIL]" if count > 0 else "[ OK ]"
        print(f"{status} {issue_type}: {count}/{total_dockerfiles} ({percentage:.1f}%)")
    
    print()


def _print_numbered_paths(title: str, paths: List[str], detail_limit: int) -> None:
    """Print numbered paths; if detail_limit > 0 and len(paths) exceeds it, truncate with a remainder line."""
    if not paths:
        return
    n = len(paths)
    print(f"{title} ({n} files):")
    cap = detail_limit if detail_limit > 0 else n
    shown = paths if n <= cap else paths[:cap]
    for i, path in enumerate(shown):
        print(f"   {i+1}. {path}")
    if n > cap:
        print(f"   ... and {n - cap} more")
    print()


def _print_numbered_subpaths(paths: List[str], detail_limit: int, indent: str = "   ") -> None:
    """Numbered list (1. 2. 3.) for duplicate-port groups; same cap as other detail printers."""
    n = len(paths)
    cap = detail_limit if detail_limit > 0 else n
    shown = paths if n <= cap else paths[:cap]
    for i, p in enumerate(shown, start=1):
        print(f"{indent}{i}. {p}")
    if n > cap:
        print(f"{indent}... and {n - cap} more")


def _sort_port_keys(ports_dict: Dict[Any, Any]) -> List[Any]:
    """Stable sort for report: numeric ports ascending, None last."""

    def key_fn(p):
        if p is None:
            return (1, 0)
        try:
            return (0, int(p))
        except (TypeError, ValueError):
            return (0, 0)

    return sorted(ports_dict.keys(), key=key_fn)


def print_detailed_issues(issues: Dict, detail_limit: int = 0):
    """
    Print detailed issue breakdown.

    detail_limit: max paths per large [FAIL] sections (canonical, x-files, etc.).
    Use 0 for no limit. A positive N truncates with ``... and M more``.
    Duplicate-port, port+service mismatch, and map-vs-EXPOSE mismatch blocks always list
    every row, numbered 1..N where applicable; they ignore detail_limit.
    """
    print("\nDETAILED ISSUES:\n")

    # Missing canonical paths
    if issues["missing_canonical_path"]:
        _print_numbered_paths(
            "[FAIL] MISSING CANONICAL PATHS",
            issues["missing_canonical_path"],
            detail_limit,
        )

    # No numeric EXPOSE on existing file
    if issues["missing_port_mapping"]:
        _print_numbered_paths(
            "[FAIL] MISSING EXPOSE PORT (Dockerfile on disk has no numeric EXPOSE)",
            issues["missing_port_mapping"],
            detail_limit,
        )

    if issues.get("missing_dockerfile_file"):
        _print_numbered_paths(
            "[FAIL] DOCKERFILE PATH IN MAP BUT FILE MISSING ON DISK",
            issues["missing_dockerfile_file"],
            detail_limit,
        )

    mismatches = issues.get("map_port_mismatch") or []
    if mismatches:
        print(f"[WARN] MAP PORT != DOCKERFILE EXPOSE ({len(mismatches)} files):")
        print("   (Recalibration map JSON is stale vs first EXPOSE — run repair_dockerfile_standardization.py.)")
        for i, row in enumerate(mismatches, start=1):
            print(
                f"   {i}. {row['path']}  map={row['map_port']}  EXPOSE_first={row['expose_primary']}"
            )
        print()

    # Missing x-files entries
    if issues["missing_x_files_entry"]:
        _print_numbered_paths(
            "[FAIL] MISSING X-FILES ENTRIES",
            issues["missing_x_files_entry"],
            detail_limit,
        )

    # Missing infrastructure rel
    if issues.get("missing_infrastructure_rel"):
        _print_numbered_paths(
            "[FAIL] MISSING INFRASTRUCTURE REL",
            issues["missing_infrastructure_rel"],
            detail_limit,
        )

    if issues.get("missing_service_ids"):
        _print_numbered_paths(
            "[FAIL] MISSING SERVICE IDS",
            issues["missing_service_ids"],
            detail_limit,
        )

    # Duplicate declared ports: always full numbered list (matches repair_dockerfile_standardization.py order)
    if issues["duplicate_ports"]:
        print(f"[WARN] DUPLICATE DECLARED PORT ({len(issues['duplicate_ports'])} ports):")
        print("   (Numbered paths: repair keeps #1 at P, #2 -> P+2, #3 -> P+3, ...)\n")
        for port in _sort_port_keys(dict(issues["duplicate_ports"])):
            dockerfiles_list = issues["duplicate_ports"][port]
            ordered = sorted(dockerfiles_list)
            print(f"   Port {port}: {len(ordered)} dockerfiles")
            _print_numbered_subpaths(ordered, 0)
        print()

    if issues.get("duplicate_port_service_conflicts"):
        print(
            f"[WARN] PORT + SERVICE MISMATCHES ({len(issues['duplicate_port_service_conflicts'])} ports):"
        )
        for block in issues["duplicate_port_service_conflicts"]:
            print(
                f"   Port {block['port']}: keys={block['ports_service_keys']} names={block['service_names']}"
            )
            ordered = sorted(block["paths"])
            _print_numbered_subpaths(ordered, 0)
        print()

def print_recommendations(issues: Dict, total_dockerfiles: int):
    """Print recommendations to fix issues."""
    print("\nRECOMMENDATIONS TO FIX:\n")
    
    if issues['missing_canonical_path']:
        percentage = (len(issues['missing_canonical_path']) / total_dockerfiles) * 100
        print(f"1. CANONICAL PATHS ({percentage:.1f}% missing):")
        print("   ACTION: Update apply_lucid_service_ids_to_dockerfiles.py to:")
        print("   - Add canonical_path resolution from host-config.yml service_name")
        print("   - Match Dockerfile ports to canonical host-config.yml entries")
        print()
    
    if issues["missing_port_mapping"]:
        percentage = (len(issues["missing_port_mapping"]) / total_dockerfiles) * 100
        print(f"2. MISSING EXPOSE ({percentage:.1f}% of scoped Dockerfiles):")
        print("   ACTION: Add a numeric EXPOSE <port> to each Dockerfile (diagnostics use it as source of truth).")
        print("   Then run repair_dockerfile_standardization.py to sync dockerfile_recalibration_map.json.")
        print()

    if issues.get("missing_dockerfile_file"):
        n = len(issues["missing_dockerfile_file"])
        pct = (n / total_dockerfiles) * 100
        print(f"2b. ORPHAN MAP KEYS ({pct:.1f}% — file deleted but path still in map):")
        print("   ACTION: Remove keys from infrastructure/containers/service_id-list.json (and x-files.json if listed).")
        print("   Then: python infrastructure/containers/build_dockerfile_recalibration_map.py")
        print()

    if issues.get("map_port_mismatch"):
        print("2c. STALE MAP PORTS (map JSON disagrees with Dockerfile EXPOSE):")
        print("   ACTION: python repair_dockerfile_standardization.py [--in-place]")
        print()
    
    if issues['missing_x_files_entry']:
        percentage = (len(issues['missing_x_files_entry']) / total_dockerfiles) * 100
        print(f"3. X-FILES TRACKING ({percentage:.1f}% missing):")
        print("   ACTION: Update inject_dockerfile_x_files_skeleton.py:")
        print("   - Scan all Dockerfiles for COPY/ADD commands")
        print("   - Add missing entries to x-files-listing.txt")
        print()
    
    if issues['duplicate_ports']:
        print(f"4. DUPLICATE PORTS ({len(issues['duplicate_ports'])} conflicts):")
        print("   ACTION: Review collision_notes in host-config.yml")
        print("   - Use distinct service_name hostnames for co-hosted services")
        print("   - Remap ports for multi-instance services")
        print(
            "   - repair_dockerfile_standardization.py assigns 2nd/3rd... paths (sorted) to P+2, P+3... "
            "in the recalibration map; align EXPOSE / compose with host-config as needed."
        )
        print(
            "   - For explicit service keys: dockerfile_standardization_diagnostics.py "
            "--emit-port-overrides infrastructure/containers/port_conflict_overrides.json"
        )
        print(
            "     then edit JSON and run repair_dockerfile_standardization.py --overrides <that file>"
        )
        print()

def main():
    """Run diagnostic."""
    ap = argparse.ArgumentParser(description="Dockerfile recalibration map diagnostics.")
    ap.add_argument(
        "--map",
        type=Path,
        default=Path("infrastructure/containers/dockerfile_recalibration_map.json"),
        help="Path to dockerfile_recalibration_map.json (or REPAIRED output)",
    )
    ap.add_argument(
        "--under",
        action="append",
        default=[],
        metavar="PREFIX",
        help=(
            "Restrict analysis to Dockerfile keys under this repo-relative prefix "
            "(repeatable). Example: --under infrastructure/containers/tor "
            "--under 02_network_security/tor"
        ),
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Write the same report to this file (UTF-8). "
            "Default: still print to stdout as well; use --no-stdout for file only."
        ),
    )
    ap.add_argument(
        "--no-stdout",
        action="store_true",
        help="With --output, write only to the file (do not print the report to stdout).",
    )
    ap.add_argument(
        "--emit-port-overrides",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Write JSON template listing port+service conflicts with candidate host-config keys. "
            "Edit ports_service_key per Dockerfile path; apply with repair --overrides. "
            "(containers_ports_report.txt is not machine-readable; use this for automation.)"
        ),
    )
    ap.add_argument(
        "--host-config",
        type=Path,
        default=Path("infrastructure/containers/host-config.yml"),
        help="Used with --emit-port-overrides to fill candidates (default: infrastructure/containers/host-config.yml).",
    )
    ap.add_argument(
        "--detail-limit",
        type=int,
        default=0,
        metavar="N",
        help=(
            "Max paths per large [FAIL] section (canonical, x-files, missing EXPOSE, etc.). "
            "Default 0 = full listing. Duplicate-port, port+mismatch, and map-vs-EXPOSE sections "
            "are always complete, numbered 1..N, regardless of this value."
        ),
    )
    ap.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        metavar="DIR",
        help="Repo root for resolving Dockerfile paths (default: directory containing this script).",
    )
    args = ap.parse_args()
    recal_path = args.map

    if not recal_path.exists():
        print(f"ERROR: {recal_path} not found", file=sys.stderr)
        return 1

    if args.no_stdout and args.output is None:
        print("ERROR: --no-stdout requires --output", file=sys.stderr)
        return 1

    root = args.repo_root.resolve() if args.repo_root is not None else None
    issues, dockerfiles, n_all, prefixes = analyze_recalibration_map(
        str(recal_path), path_prefixes=args.under or None, repo_root=root
    )
    total = len(dockerfiles)

    if args.emit_port_overrides is not None:
        host = load_host_services(args.host_config)
        if not host:
            print(
                f"WARNING: no services loaded from {args.host_config} (install PyYAML?); "
                "override template will have empty candidates.",
                file=sys.stderr,
            )
        n_paths = write_port_overrides_template(
            issues, dockerfiles, host, args.emit_port_overrides, recal_path
        )
        print(
            f"Port overrides template: {n_paths} Dockerfile path(s) -> {args.emit_port_overrides.resolve()}",
            file=sys.stderr,
        )

    with tee_stdout_to_file(args.output, also_stdout=not args.no_stdout):
        print_report_preamble(prefixes, total, n_all)
        print_issue_summary(issues, total)
        print_detailed_issues(issues, detail_limit=args.detail_limit)
        print_recommendations(issues, total)

        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)

    if args.output is not None:
        print(f"Report written to {args.output.resolve()}", file=sys.stderr)

    return 0

if __name__ == '__main__':
    sys.exit(main())
