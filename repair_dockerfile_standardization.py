"""Repair Dockerfile standardization metadata in dockerfile_recalibration_map.json.

Fills canonical_path, ports, ports_service_key, infrastructure_containers_rel using
infrastructure/containers/host-config.yml and Dockerfile paths / EXPOSE lines.

When multiple host-config services share the same container port, picks the best match
by path + tags (resolves recalibration map conflicts without changing Dockerfiles).

Duplicate container ports among in-scope Dockerfiles (same numbering as diagnostics):
sorted paths 1..N for port P — entry 1 keeps P; entry n uses P + n. Remapped entries
get that port in recalibration map metadata (host-config service pick still uses P).
Does not edit Dockerfile EXPOSE lines.

path: repair_dockerfile_standardization.py (repository root)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


def normalize_path_prefixes(prefixes: Optional[List[str]]) -> List[str]:
    if not prefixes:
        return []
    out: List[str] = []
    for raw in prefixes:
        p = raw.strip().replace("\\", "/").rstrip("/")
        if p:
            out.append(p)
    return out


def path_under_prefixes(rel_path: str, prefixes: List[str]) -> bool:
    if not prefixes:
        return True
    rel = rel_path.replace("\\", "/")
    for p in prefixes:
        if rel == p or rel.startswith(p + "/"):
            return True
    return False

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parent


def load_host_config(path: Path) -> Dict[str, Dict[str, Any]]:
    """Return services dict: service_key -> config."""
    if not path.is_file():
        return {}
    raw_text = path.read_text(encoding="utf-8", errors="replace")
    if yaml:
        try:
            raw = yaml.safe_load(raw_text)
            if isinstance(raw, dict) and isinstance(raw.get("services"), dict):
                return dict(raw["services"])
        except yaml.YAMLError:
            pass
    # Minimal fallback: only top-level `key:` with nested `port:`
    services: Dict[str, Dict[str, Any]] = {}
    current: Optional[str] = None
    bucket: Dict[str, Any] = {}
    for line in raw_text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0 and stripped.endswith(":") and " " not in stripped.split(":")[0]:
            if current is not None:
                services[current] = bucket
            current = stripped[:-1].strip()
            bucket = {}
        elif indent > 0 and current and ":" in stripped:
            k, _, v = stripped.partition(":")
            k, v = k.strip(), v.strip().strip("'\"")
            if v == "" or v == "null":
                continue
            if k == "port":
                try:
                    bucket["port"] = int(v)
                except ValueError:
                    bucket["port"] = v
            elif k == "tags" or k == "labels":
                continue
            else:
                bucket[k] = v
    if current is not None:
        services[current] = bucket
    return services


def extract_expose_ports(dockerfile_path: Path) -> List[int]:
    """All numeric ports from EXPOSE lines (order preserved, deduped)."""
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


def extract_initial_chosen_port(
    rel: str,
    meta: Dict[str, Any],
    full: Path,
    ovr_map: Dict[str, Dict[str, Any]],
) -> Optional[int]:
    """First EXPOSE / existing map port / override port (same precedence as repair loop)."""
    expose_ports = extract_expose_ports(full)
    chosen_port: Optional[int] = None
    existing = meta.get("ports")
    if isinstance(existing, dict) and existing.get("port") is not None:
        try:
            chosen_port = int(existing["port"])
        except (TypeError, ValueError):
            chosen_port = None
    if chosen_port is None and expose_ports:
        chosen_port = expose_ports[0]
    ovr = ovr_map.get(rel)
    if isinstance(ovr, dict) and ovr.get("port") is not None:
        try:
            chosen_port = int(ovr["port"])
        except (TypeError, ValueError):
            pass
    return chosen_port


def build_duplicate_port_remap(
    initial_by_rel: Dict[str, int],
) -> Tuple[Dict[str, int], Dict[str, int], Set[str]]:
    """
    Align with dockerfile_standardization_diagnostics duplicate listing: ``sorted(paths)``.
    For shared port P: index 1 -> P; index n (n>=2) -> P + n.
    """
    port_to_rels: Dict[int, List[str]] = defaultdict(list)
    for rel, p in initial_by_rel.items():
        port_to_rels[p].append(rel)
    final_port: Dict[str, int] = {}
    group_base: Dict[str, int] = {}
    secondaries: Set[str] = set()
    for p, rels in port_to_rels.items():
        if len(rels) <= 1:
            continue
        for idx, rel in enumerate(sorted(rels), start=1):
            group_base[rel] = p
            if idx == 1:
                final_port[rel] = p
            else:
                final_port[rel] = p + idx
                secondaries.add(rel)
    return final_port, group_base, secondaries


def services_for_port(host: Dict[str, Dict[str, Any]], port: int) -> List[str]:
    out: List[str] = []
    for sk, sd in host.items():
        if not isinstance(sd, dict):
            continue
        try:
            p = int(sd.get("port"))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if p == port:
            out.append(sk)
    return out


def score_path_vs_service(dockerfile_rel: str, service_key: str, sd: Dict[str, Any]) -> float:
    """Higher = better match for this Dockerfile belonging to this host-config service."""
    path = dockerfile_rel.lower().replace("\\", "/")
    sk = service_key.lower()
    sn = str(sd.get("service_name") or "").lower()
    score = 0.0

    # Filename / path fragments
    if "dockerfile.server-gateway" in path or "dockerfile.server_gateway" in path:
        if "server_gateway" in sk or "server-gateway" in sn:
            score += 20
    if "/server/" in path and "server-gateway" in path:
        if "server_gateway" in sk:
            score += 15
    if "03_api_gateway" in path or "/api_gateway/" in path or "api-gateway" in path:
        if sk == "main_lucid_gateway":
            score += 15
    if "payment" in path and "tron" in path:
        if "tron_payment" in sk:
            score += 15
    if "anchoring" in path or "session-anchoring" in path:
        if "session_anchoring" in sk:
            score += 15
    if "anchoring" in path or "session-anchoring" in path.replace("_", "-"):
        if "session_anchoring" in sk:
            score += 18
    if ("consensus" in path or "block-manager" in path) and "anchoring" not in path:
        if "blockchain_consensus" in sk:
            score += 18
    if "merkle" in path:
        if "session_merkle" in sk or "merkle_tree" in sk:
            score += 18
    if "payout" in path or "payment-router" in path:
        if "payout_router" in sk:
            score += 18
    if "recorder" in path and "session" in path:
        if "session_recorder" in sk:
            score += 18
    if "rdp" in path and "server-manager" in path.replace("_", "-"):
        if "rdp_server_manager" in sk:
            score += 18
    if "processor" in path and "session" in path and "tron" not in path:
        if "session_processor" in sk:
            score += 18
    if "tron" in path and "client" in path:
        if "tron_client" in sk:
            score += 18
    if "node_management" in path or "node-management" in path:
        if "node_management_staging" in sk and "staging" in path:
            score += 18
        elif "node_management" in sk and "staging" not in path:
            score += 12
    if "gui_hardware" in path or "gui-hardware" in path:
        if "gui_hardware_manager" in sk:
            score += 18
    if "admin" in path and "ui" in path and "backend" in path:
        if "admin_ui_backend" in sk:
            score += 15
    if "overlord" in path and "database" in path:
        if "database_overlord" in sk:
            score += 15
    if "gui" in path and "tor" in path:
        if "gui_tor" in sk:
            score += 15
    if "payment" in path and "gateway" in path and "wallet" not in path:
        if "payment_system_gateway" in sk:
            score += 12

    # Tags
    tags = sd.get("tags") or []
    if isinstance(tags, list):
        for tag in tags:
            t = str(tag).lower().replace("_", "-")
            if len(t) >= 5 and t in path.replace("_", "-"):
                score += 4

    # Service key / name substring
    for frag in sk.split("_"):
        if len(frag) >= 5 and frag in path.replace("-", "").replace("_", ""):
            score += 1.5
    if sn and sn.replace("-", "") in path.replace("-", "").replace("_", ""):
        score += 2

    return score


def load_port_overrides(path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    """
    Load JSON from ``--overrides`` (see dockerfile_standardization_diagnostics --emit-port-overrides).
    Accepts either ``{\"overrides\": { path: {...} }}`` or a flat path -> dict map.
    """
    if path is None or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"WARNING: could not load overrides {path}: {e}", file=sys.stderr)
        return {}
    if isinstance(data, dict) and "overrides" in data:
        raw = data["overrides"]
    else:
        raw = data
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for k, v in raw.items():
        if str(k).startswith("_"):
            continue
        if isinstance(v, dict):
            out[str(k).replace("\\", "/")] = v
    return out


def pick_service_for_dockerfile(
    dockerfile_rel: str, port: int, host: Dict[str, Dict[str, Any]]
) -> Optional[str]:
    candidates = services_for_port(host, port)
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    return max(
        candidates,
        key=lambda sk: score_path_vs_service(dockerfile_rel, sk, host.get(sk, {})),
    )


def repair_recalibration_map(
    recal_data: Dict[str, Any],
    host: Dict[str, Dict[str, Any]],
    repo_root: Path,
    path_prefixes: Optional[List[str]] = None,
    overrides: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[Dict[str, Any], Dict[str, int]]:
    repaired = deepcopy(recal_data)
    dockerfiles = repaired.setdefault("dockerfiles", {})
    prefixes = normalize_path_prefixes(path_prefixes)
    ovr_map = overrides or {}
    fixed = {
        "canonical_paths": 0,
        "port_mappings": 0,
        "port_reassignments": 0,
        "duplicate_port_remaps": 0,
        "infrastructure_rels": 0,
        "skipped_out_of_scope": 0,
        "override_applied": 0,
        "override_invalid": 0,
    }

    initial_by_rel: Dict[str, int] = {}
    for rel, meta in dockerfiles.items():
        if not isinstance(meta, dict):
            continue
        if not path_under_prefixes(rel, prefixes):
            continue
        full0 = repo_root / rel.replace("\\", "/")
        p0 = extract_initial_chosen_port(rel, meta, full0, ovr_map)
        if p0 is not None:
            initial_by_rel[rel] = p0

    final_port, group_base, secondaries = build_duplicate_port_remap(initial_by_rel)

    for rel, meta in dockerfiles.items():
        if not isinstance(meta, dict):
            continue
        if not path_under_prefixes(rel, prefixes):
            fixed["skipped_out_of_scope"] += 1
            continue
        full = repo_root / rel.replace("\\", "/")

        # infrastructure_containers_rel
        if not meta.get("infrastructure_containers_rel"):
            if rel.startswith("infrastructure/containers/"):
                meta["infrastructure_containers_rel"] = rel[len("infrastructure/containers/") :]
                fixed["infrastructure_rels"] += 1

        if rel in final_port:
            chosen_port = final_port[rel]
        else:
            chosen_port = extract_initial_chosen_port(rel, meta, full, ovr_map)

        service_pick_port = group_base.get(rel, chosen_port)

        if chosen_port is not None:
            best_sk: Optional[str] = None
            ovr = ovr_map.get(rel)
            if isinstance(ovr, dict):
                sk_raw = str(ovr.get("ports_service_key") or "").strip()
                if sk_raw:
                    if sk_raw in host:
                        best_sk = sk_raw
                        fixed["override_applied"] += 1
                    else:
                        fixed["override_invalid"] += 1
                        print(
                            f"WARNING: overrides unknown ports_service_key {sk_raw!r} for {rel}",
                            file=sys.stderr,
                        )
            if best_sk is None:
                best_sk = pick_service_for_dockerfile(rel, service_pick_port, host)
            if best_sk and best_sk in host:
                sd = host[best_sk]
                try:
                    hp = int(sd.get("port"))
                except (TypeError, ValueError):
                    hp = chosen_port
                meta_port = chosen_port if rel in secondaries else hp
                if rel in secondaries:
                    fixed["duplicate_port_remaps"] += 1
                sn = sd.get("service_name", best_sk)
                if rel in secondaries:
                    http_path = f"http://{sn}:{meta_port}/app"
                else:
                    http_path = sd.get(
                        "http_path",
                        f"http://{sn}:{meta_port}/app",
                    )
                new_ports = {
                    "port": meta_port,
                    "service_name": sn,
                    "http_path": http_path,
                }
                old_sk = meta.get("ports_service_key")
                old_ports = meta.get("ports")
                meta["ports"] = new_ports
                meta["ports_service_key"] = best_sk
                if not meta.get("canonical_path"):
                    meta["canonical_path"] = sd.get("service_name")
                    fixed["canonical_paths"] += 1
                elif meta.get("canonical_path") == sd.get("service_name"):
                    pass
                if old_ports != new_ports or old_sk != best_sk:
                    fixed["port_reassignments"] += 1
                fixed["port_mappings"] += 1
        elif not meta.get("canonical_path"):
            # No port: try weak path match to fill canonical only
            best_sk = None
            best_score = 0.0
            for sk, sd in host.items():
                if not isinstance(sd, dict):
                    continue
                s = score_path_vs_service(rel, sk, sd)
                if s > best_score:
                    best_score = s
                    best_sk = sk
            if best_sk and best_score >= 6:
                sd = host[best_sk]
                meta["canonical_path"] = sd.get("service_name", best_sk)
                fixed["canonical_paths"] += 1

        if not meta.get("in_x_files"):
            meta["_requires_x_files_scan"] = True

    return repaired, fixed


def main() -> int:
    ap = argparse.ArgumentParser(description="Repair dockerfile_recalibration_map.json from host-config.yml.")
    ap.add_argument(
        "--in-place",
        action="store_true",
        help="Write dockerfile_recalibration_map.json instead of *_REPAIRED.json",
    )
    ap.add_argument(
        "--under",
        action="append",
        default=[],
        metavar="PREFIX",
        help=(
            "Only repair Dockerfile keys under this repo-relative prefix (repeatable). "
            "Other map entries are left unchanged. Example: --under infrastructure/containers/tor"
        ),
    )
    ap.add_argument(
        "--overrides",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "JSON from dockerfile_standardization_diagnostics.py --emit-port-overrides: "
            "set ports_service_key (and optional port) per Dockerfile path to force host-config alignment."
        ),
    )
    args = ap.parse_args()

    root = repo_root_from_script()
    recal_path = root / "infrastructure" / "containers" / "dockerfile_recalibration_map.json"
    host_path = root / "infrastructure" / "containers" / "host-config.yml"
    out_path = (
        recal_path
        if args.in_place
        else root / "infrastructure" / "containers" / "dockerfile_recalibration_map_REPAIRED.json"
    )

    if not recal_path.is_file():
        print(f"ERROR: missing {recal_path}", file=sys.stderr)
        return 1
    if not host_path.is_file():
        print(f"ERROR: missing {host_path}", file=sys.stderr)
        return 1

    host = load_host_config(host_path)
    if not host:
        print("ERROR: host-config.yml produced empty services map", file=sys.stderr)
        return 1

    recal_data = json.loads(recal_path.read_text(encoding="utf-8"))
    prefixes = normalize_path_prefixes(args.under or None)
    print(f"Loaded host-config: {len(host)} services")
    n_df = len(recal_data.get("dockerfiles", {}))
    print(f"Loaded recalibration map: {n_df} dockerfiles")
    if prefixes:
        in_scope = sum(
            1 for k in recal_data.get("dockerfiles", {}) if path_under_prefixes(k, prefixes)
        )
        print(f"Repair scope: {in_scope} dockerfiles under {prefixes}")
    print()

    ovr = load_port_overrides(args.overrides)
    if ovr:
        print(f"Loaded {len(ovr)} port override entr(y/ies) from {args.overrides}\n")

    repaired, fixed = repair_recalibration_map(
        recal_data,
        host,
        root,
        path_prefixes=args.under or None,
        overrides=ovr or None,
    )
    total = len(repaired.get("dockerfiles", {}))

    print("Repair counters (incremental):")
    for k, v in fixed.items():
        if k == "skipped_out_of_scope" and v == 0:
            continue
        if k == "override_applied" and v == 0:
            continue
        if k == "override_invalid" and v == 0:
            continue
        if k == "duplicate_port_remaps" and v == 0:
            continue
        print(f"  {k}: {v}")
    print()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(repaired, indent=2), encoding="utf-8", newline="\n")
    print(f"Wrote {out_path}")

    still_no_ports = sum(
        1
        for m in repaired.get("dockerfiles", {}).values()
        if isinstance(m, dict) and not m.get("ports")
    )
    if still_no_ports:
        print(f"\nNOTE: {still_no_ports} dockerfiles still have no ports (add EXPOSE or host-config entry).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
