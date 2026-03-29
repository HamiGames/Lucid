"""Map cluster calibration YAMLs to Dockerfiles and Python modules.

Uses infrastructure/containers/host-config.yml (authoritative for clusters),
x-files-listing.txt (Python paths under /app/...), and the same prefix rules as
_gen_x_lucid_cluster_calibration.py.

Run (repo venv):

  .venv\\Scripts\\python.exe infrastructure\\containers\\allocate_x_lucid_cluster_calibration.py

Writes:
  infrastructure/containers/services/x_lucid_cluster_calibration/allocation_manifest.yml

Optional:
  --json   Also write allocation_manifest.json next to the yaml.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required: pip install pyyaml", file=sys.stderr)
    raise SystemExit(1)

_CONTAINERS_DIR = Path(__file__).resolve().parent
if str(_CONTAINERS_DIR) not in sys.path:
    sys.path.insert(0, str(_CONTAINERS_DIR))

import _gen_x_lucid_cluster_calibration as _gen_host  # noqa: E402

CLUSTER_APP_PREFIXES = _gen_host.CLUSTER_APP_PREFIXES
CALIBRATION_DIR = _gen_host.OUT_DIR
REPO_ROOT = _gen_host.find_repo_root(_CONTAINERS_DIR)

HOST_CONFIG = REPO_ROOT / "infrastructure" / "containers" / "host-config.yml"
X_FILES_LISTING = REPO_ROOT / "x-files-listing.txt"
MANIFEST_YAML = CALIBRATION_DIR / "allocation_manifest.yml"
MANIFEST_JSON = CALIBRATION_DIR / "allocation_manifest.json"

# Dockerfiles under these trees are scanned (avoids .venv / vendored dirs).
DOCKERFILE_SCAN_ROOTS = (
    REPO_ROOT / "infrastructure" / "containers",
    REPO_ROOT / "auth",
    REPO_ROOT / "blockchain",
    REPO_ROOT / "sessions",
    REPO_ROOT / "node",
    REPO_ROOT / "admin",
    REPO_ROOT / "RDP",
    REPO_ROOT / "gui_api_bridge",
    REPO_ROOT / "electron_gui",
    REPO_ROOT / "03_api_gateway",
    REPO_ROOT / "database",
    REPO_ROOT / "payment_systems",
    REPO_ROOT / "infrastructure" / "docker",
    REPO_ROOT / "infrastructure" / "service_mesh",
)

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "dist",
        "build",
    }
)

SERVICE_LABEL_RE = re.compile(
    r'com\.lucid\.service\s*=\s*(?:"([^"]+)"|\'([^\']+)\'|([^\s\\\n]+))',
    re.MULTILINE,
)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def build_host_indexes(services: dict[str, Any]) -> tuple[dict[str, tuple[str, str, str]], list[str]]:
    """Map lucid service label / service_name / tag -> (host_key, cluster, service_name)."""
    by_label: dict[str, tuple[str, str, str]] = {}
    duplicates: list[str] = []

    for host_key, svc in services.items():
        if not isinstance(svc, dict):
            continue
        labels = svc.get("labels") or {}
        cluster = labels.get("com.lucid.cluster")
        if not cluster:
            continue
        sn = svc.get("service_name") or ""
        host_name = str(host_key)

        def add(key: str) -> None:
            k = key.strip()
            if not k:
                return
            if k in by_label and by_label[k] != (host_name, cluster, sn):
                duplicates.append(
                    f"duplicate index key {k!r}: {by_label[k]} vs {(host_name, cluster, sn)}"
                )
            by_label[k] = (host_name, cluster, sn)

        add(sn)
        add(host_name)
        lucid = labels.get("com.lucid.service")
        if lucid:
            add(str(lucid))
        for t in svc.get("tags") or []:
            add(str(t))

    return by_label, duplicates


def extract_lucid_service_from_dockerfile(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    m = SERVICE_LABEL_RE.search(text)
    if not m:
        return None
    return next(g for g in m.groups() if g)


def iter_dockerfiles() -> list[Path]:
    seen: set[Path] = set()
    out: list[Path] = []
    for root in DOCKERFILE_SCAN_ROOTS:
        if not root.is_dir():
            continue
        for p in root.rglob("Dockerfile*"):
            if not p.is_file():
                continue
            if any(part in SKIP_DIR_NAMES for part in p.parts):
                continue
            rp = p.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            out.append(p)
    return sorted(out, key=lambda x: str(x).lower())


def invert_prefix_map() -> dict[str, list[str]]:
    inv: dict[str, list[str]] = defaultdict(list)
    for cluster, prefixes in CLUSTER_APP_PREFIXES.items():
        for seg in prefixes:
            inv[seg].append(cluster)
    for seg in inv:
        inv[seg] = sorted(set(inv[seg]))
    return dict(inv)


def parse_x_lucid_paths_listing(path: Path) -> list[str]:
    """Repo-relative paths from x-lucid-file-path lines (strip /app/)."""
    rx = re.compile(r"x-lucid-file-path:\s*/app/(.+)")
    out: list[str] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            m = rx.search(line)
            if m:
                out.append(m.group(1).replace("\\", "/"))
    return out


def segment_for_repo_path(repo_path: str) -> str:
    return repo_path.split("/")[0] if repo_path else ""


def calibration_filename(cluster: str) -> str:
    return f"{cluster}-cluster-host-alignment.yml"


def calibration_repo_path(cluster: str) -> str:
    return (
        "infrastructure/containers/services/x_lucid_cluster_calibration/"
        f"{calibration_filename(cluster)}"
    )


def calibration_container_path(cluster: str) -> str:
    return (
        "/app/service_configs/x_lucid_cluster_calibration/"
        f"{calibration_filename(cluster)}"
    )


def build_manifest() -> dict[str, Any]:
    host = load_yaml(HOST_CONFIG)
    services = host.get("services") or {}
    by_label, _dup = build_host_indexes(services)

    inv_seg = invert_prefix_map()
    x_paths = parse_x_lucid_paths_listing(X_FILES_LISTING)

    docker_by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    docker_unmatched: list[dict[str, Any]] = []

    for df in iter_dockerfiles():
        rel = str(df.relative_to(REPO_ROOT)).replace("\\", "/")
        label = extract_lucid_service_from_dockerfile(df)
        if not label:
            docker_unmatched.append(
                {
                    "dockerfile": rel,
                    "reason": "no com.lucid.service label found",
                }
            )
            continue
        hit = by_label.get(label.strip())
        if not hit:
            docker_unmatched.append(
                {
                    "dockerfile": rel,
                    "com.lucid.service": label,
                    "reason": "not indexed from host-config.yml (check tags/service_name)",
                }
            )
            continue
        host_key, cluster, service_name = hit
        rp = calibration_repo_path(cluster)
        cp = calibration_container_path(cluster)
        docker_by_cluster[cluster].append(
            {
                "dockerfile": rel,
                "host_config_key": host_key,
                "com_lucid_service_label": label,
                "service_name": service_name,
                "calibration_repo_path": rp,
                "calibration_container_path": cp,
                "suggested_copy_line": f"COPY {rp} {cp}",
            }
        )

    py_by_cluster: dict[str, list[dict[str, Any]]] = defaultdict(list)
    py_unmapped: list[str] = []
    multi_seg: dict[str, list[str]] = {}

    for repo_path in sorted(set(x_paths)):
        if not repo_path.endswith(".py"):
            continue
        if not (REPO_ROOT / repo_path).is_file():
            continue
        seg = segment_for_repo_path(repo_path)
        clusters = inv_seg.get(seg)
        if not clusters:
            py_unmapped.append(repo_path)
            continue
        if len(clusters) > 1:
            multi_seg[seg] = clusters
        for cl in clusters:
            py_by_cluster[cl].append(
                {
                    "repo_path": repo_path,
                    "segment": seg,
                    "calibration_repo_path": calibration_repo_path(cl),
                    "calibration_container_path": calibration_container_path(cl),
                }
            )

    clusters_sorted = sorted(set(docker_by_cluster.keys()) | set(py_by_cluster.keys()))

    manifest: dict[str, Any] = {
        "x-lucid-allocation-manifest": {
            "version": "1.0",
            "repo_root": str(REPO_ROOT),
            "sources": {
                "host_config": str(HOST_CONFIG.relative_to(REPO_ROOT)).replace(
                    "\\", "/"
                ),
                "x_files_listing": str(X_FILES_LISTING.relative_to(REPO_ROOT)).replace(
                    "\\", "/"
                ),
                "prefix_rules": "infrastructure/containers/_gen_x_lucid_cluster_calibration.py CLUSTER_APP_PREFIXES",
            },
            "clusters": clusters_sorted,
        },
        "dockerfiles": {k: docker_by_cluster[k] for k in sorted(docker_by_cluster)},
        "python_modules": {k: py_by_cluster[k] for k in sorted(py_by_cluster)},
        "dockerfiles_unmatched": docker_unmatched,
        "python_modules_notes": {
            "unmapped_repo_paths": py_unmapped,
            "multi_cluster_segments": multi_seg,
        },
    }
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--json",
        action="store_true",
        help="Also write allocation_manifest.json",
    )
    args = ap.parse_args()

    manifest = build_manifest()
    CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)

    with MANIFEST_YAML.open("w", encoding="utf-8") as f:
        f.write(
            "# allocation_manifest.yml — generated by allocate_x_lucid_cluster_calibration.py\n"
            "# Merge hints: COPY calibration_repo_path -> calibration_container_path in Dockerfiles;\n"
            "# Python: optional docstring line x-lucid-cluster-calibration: <repo path>\n\n"
        )
        yaml.dump(
            manifest,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            width=100,
        )

    print(f"Wrote {MANIFEST_YAML}")
    print(
        f"  dockerfiles matched: {sum(len(v) for v in manifest['dockerfiles'].values())} "
        f"in {len(manifest['dockerfiles'])} clusters"
    )
    print(
        f"  python paths: {sum(len(v) for v in manifest['python_modules'].values())} "
        f"(cluster rows; may duplicate multi-cluster segments)"
    )
    print(f"  dockerfiles unmatched: {len(manifest['dockerfiles_unmatched'])}")
    n_um = len(manifest["python_modules_notes"]["unmapped_repo_paths"])
    print(f"  python unmapped (no segment prefix): {n_um}")

    if args.json:
        with MANIFEST_JSON.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        print(f"Wrote {MANIFEST_JSON}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
