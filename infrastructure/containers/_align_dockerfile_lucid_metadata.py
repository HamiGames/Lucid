"""
Align LABEL (com.lucid.* + OCI + org.lucid.layer) and the following ENV block in
Dockerfiles across the repository (skips .git, .venv, node_modules, etc.).

Sets com.lucid.layer and org.lucid.layer to the same value on every LABEL block
that includes com.lucid.service or org.lucid.service.

Authoritative service metadata: infrastructure/containers/host-config.yml
(same registry family as x-files-listing.txt / x-files.json for Lucid paths).

When a LABEL's service matches host-config (by com.lucid.service, org.lucid.service,
or tags), all com.lucid.* keys present in that registry entry overwrite the Dockerfile.
If the registry has no com.lucid.plane, plane is inferred (e.g. core chain services → chain).
org.lucid.service/plane/expose/cluster are aligned to com.lucid.* when those org keys exist.

Run from repo root (PyYAML required):
  .venv\\Scripts\\python.exe infrastructure\\containers\\_align_dockerfile_lucid_metadata.py --apply
Only Dockerfiles under a subtree (repeatable):
  python infrastructure/containers/_align_dockerfile_lucid_metadata.py --under infrastructure/docker --apply
Dry run:
  .venv\\Scripts\\python.exe infrastructure\\containers\\_align_dockerfile_lucid_metadata.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: pip install pyyaml", file=sys.stderr)
    raise SystemExit(1)

REPO_ROOT = Path(__file__).resolve().parents[2]
HOST_CONFIG = REPO_ROOT / "infrastructure" / "containers" / "host-config.yml"

SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".cursor",
    }
)
SKIP_PATH_PARTS = frozenset({".devcontainer"})

# Standard ENV keys first; remainder sorted alphabetically (service-specific kept).
ENV_PRIMARY_ORDER = (
    "PATH",
    "PYTHONUNBUFFERED",
    "PYTHONDONTWRITEBYTECODE",
    "PYTHONPATH",
    "PYTHONIOENCODING",
    "LANG",
    "LC_ALL",
)


def _label_scalar_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v).strip().strip("'\"")


def load_host_index(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    services: dict[str, Any] = data.get("services") or {}
    by_alias: dict[str, dict[str, str]] = {}
    for host_key, svc in services.items():
        if not isinstance(svc, dict):
            continue
        labels = dict(svc.get("labels") or {})
        sn = (svc.get("service_name") or "").strip()
        lucid_svc = (labels.get("com.lucid.service") or sn or "").strip()
        if not lucid_svc:
            continue
        flat: dict[str, str] = {"com.lucid.service": lucid_svc}
        for k, v in labels.items():
            ks = str(k)
            if not ks.startswith("com.lucid.") or ks == "com.lucid.service":
                continue
            sv = _label_scalar_str(v)
            if sv:
                flat[ks] = sv
        port = svc.get("port")
        if port is not None and (
            "com.lucid.expose" not in flat or not flat["com.lucid.expose"]
        ):
            flat["com.lucid.expose"] = str(port).strip().strip("'\"")
        flat.setdefault("com.lucid.platform", "arm64")
        flat.setdefault("com.lucid.security", "distroless")
        for alias in {host_key, sn, lucid_svc, *([str(t) for t in (svc.get("tags") or [])])}:
            a = (alias or "").strip()
            if a:
                by_alias[a] = flat
    return by_alias


def infer_build_layer(cluster: str, service: str, relpath: str) -> str:
    """Spec-4 stage number as string (0–6), aligned with LUCID-BUILD-RULES.md."""
    cl = (cluster or "").strip().lower()
    s = (service or "").strip().lower()
    p = relpath.replace("\\", "/").lower()
    by_cluster = {
        "foundation": "0",
        "database": "0",
        "core": "1",
        "processing": "2",
        "application": "3",
        "gui-integration": "3",
        "payment": "4",
        "storage": "5",
        "monitoring": "5",
    }
    if cl in by_cluster:
        return by_cluster[cl]
    if "/blockchain/" in p:
        return "1"
    if "/sessions/" in p:
        return "2"
    if "/node/" in p or "/rdp" in p or "/vm/" in p:
        return "3"
    if "/wallet/" in p or "/payment_systems/" in p or "/payment-systems/" in p:
        return "4"
    if "/admin/" in p:
        return "4"
    if "/storage/" in p:
        return "5"
    if "/tor/" in p or "/base/" in p or "dockerfile.base" in p:
        return "0"
    if "/gui/" in p or "electron_gui" in p:
        return "3"
    if "/database/" in p:
        return "0"
    if "multi-stage" in p and "blockchain" in p:
        return "1"
    if s.startswith("blockchain") or s in ("block-manager", "data-chain"):
        return "1"
    if s.startswith("session") or "merkle" in s or "anchoring" in s:
        return "2"
    if "tron" in s or "wallet" in s or "payout" in s or "usdt" in s:
        return "4"
    return "0"


def resolve_layer_value(
    labels: dict[str, str], cluster: str, service: str, relpath: str
) -> str:
    lc = str(labels.get("com.lucid.layer", "")).strip()
    lo = str(labels.get("org.lucid.layer", "")).strip()
    if lc and lo and lc != lo:
        return lc
    if lc:
        return lc
    if lo:
        return lo
    return infer_build_layer(cluster, service, relpath)


def infer_plane(cluster: str, service: str) -> str:
    if cluster == "payment":
        return "support"
    if cluster == "gui-integration":
        return "support"
    chain_names = frozenset(
        {
            "blockchain-engine",
            "blockchain-consensus-engine",
            "block-manager",
            "data-chain",
        }
    )
    if cluster == "core" and service in chain_names:
        return "chain"
    return "ops"


def default_env_config(service: str, cluster: str) -> str:
    s = service.lower()
    if "tor" in s and cluster != "payment":
        return ".env.tunnel-tools,.env.secrets,.env.foundation"
    if cluster == "payment":
        if "wallet" in s or service == "wallet-manager":
            return ".env.support,.env.tron-wallet-manager,.env.secrets,.env.foundation"
        if "payment-gateway" in s or "gateway" in s:
            return ".env.support,.env.tron-payment-gateway,.env.secrets,.env.foundation"
        return ".env.foundation,.env.secrets,.env.support"
    if cluster == "core" and service in (
        "blockchain-engine",
        "blockchain-consensus-engine",
        "block-manager",
        "data-chain",
    ):
        return ".env.foundation,.env.core,.env.secrets,.env.blockchain"
    return ".env.foundation,.env.secrets"


def find_all_label_spans(text: str) -> list[tuple[int, int]]:
    starts = [m.start() for m in re.finditer(r"(?m)^LABEL\s+", text)]
    spans: list[tuple[int, int]] = []
    for start in starts:
        p = start
        end = start
        while p < len(text):
            nl = text.find("\n", p)
            if nl == -1:
                end = len(text)
                break
            line = text[p:nl]
            end = nl + 1
            p = nl + 1
            if line.rstrip().endswith("\\"):
                continue
            break
        spans.append((start, end))
    return spans


def find_last_label_span(text: str) -> tuple[int, int] | None:
    spans = find_all_label_spans(text)
    return spans[-1] if spans else None


def parse_label_block(block: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in block.splitlines():
        line = raw.strip()
        if line.endswith("\\"):
            line = line[:-1].strip()
        if line.startswith("LABEL "):
            line = line[6:].strip()
        if not line or "=" not in line:
            continue
        key, _, rest = line.partition("=")
        key = key.strip()
        val = rest.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        out[key] = val
    return out


def parse_label_block_ordered(block: str) -> tuple[dict[str, str], list[str]]:
    out: dict[str, str] = {}
    order: list[str] = []
    for raw in block.splitlines():
        line = raw.strip()
        if line.endswith("\\"):
            line = line[:-1].strip()
        if line.startswith("LABEL "):
            line = line[6:].strip()
        if not line or "=" not in line:
            continue
        key, _, rest = line.partition("=")
        key = key.strip()
        val = rest.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key not in out:
            order.append(key)
        out[key] = val
    return out, order


def normalize_org_to_com(labels: dict[str, str]) -> dict[str, str]:
    """Fill com.lucid.* from org.lucid.* when com is empty (same LABEL block)."""
    m = dict(labels)
    pairs = (
        ("com.lucid.service", "org.lucid.service"),
        ("com.lucid.plane", "org.lucid.plane"),
        ("com.lucid.expose", "org.lucid.expose"),
        ("com.lucid.cluster", "org.lucid.cluster"),
    )
    for ck, ok in pairs:
        if not str(m.get(ck, "")).strip() and str(m.get(ok, "")).strip():
            m[ck] = str(m[ok]).strip().strip("'\"")
    return m


def sync_org_lucid_from_com(merged: dict[str, str], had_old_keys: set[str]) -> None:
    """Keep org.lucid.* in sync with com.lucid.* when the block already used org.lucid.*."""
    pairs = (
        ("org.lucid.service", "com.lucid.service"),
        ("org.lucid.plane", "com.lucid.plane"),
        ("org.lucid.expose", "com.lucid.expose"),
        ("org.lucid.cluster", "com.lucid.cluster"),
    )
    for orgk, comk in pairs:
        if orgk in had_old_keys and str(merged.get(comk, "")).strip():
            merged[orgk] = merged[comk]


def format_label_block(labels: dict[str, str], order_keys: list[str]) -> str:
    lines: list[str] = []
    first = True
    for k in order_keys:
        if k not in labels:
            continue
        v = labels[k]
        esc = v.replace("\\", "\\\\").replace('"', '\\"')
        prefix = "LABEL " if first else "      "
        first = False
        lines.append(f'{prefix}{k}="{esc}" \\')
    if lines:
        lines[-1] = lines[-1].rstrip(" \\")
    return "\n".join(lines) + "\n"


def build_label_order(merged: dict[str, str]) -> list[str]:
    oci = [
        "maintainer",
        "version",
        "description",
        "org.opencontainers.image.title",
        "org.opencontainers.image.description",
        "org.opencontainers.image.version",
        "org.opencontainers.image.revision",
        "org.opencontainers.image.created",
    ]
    lucid = [
        "com.lucid.plane",
        "org.lucid.plane",
        "com.lucid.service",
        "org.lucid.service",
        "com.lucid.layer",
        "org.lucid.layer",
        "com.lucid.platform",
        "com.lucid.architecture",
        "com.lucid.security",
        "com.lucid.vulnerabilities",
        "com.lucid.expose",
        "org.lucid.expose",
        "com.lucid.cluster",
        "org.lucid.cluster",
        "com.lucid.tor.compatible",
        "com.lucid.env.config",
    ]
    order: list[str] = []
    for k in oci + lucid:
        if k in merged and k not in order:
            order.append(k)
    for k in merged:
        if k not in order:
            order.append(k)
    return order


def merge_labels(
    old: dict[str, str],
    host: dict[str, str] | None,
    relpath: str,
) -> dict[str, str]:
    merged = normalize_org_to_com(dict(old))
    lookup_svc = (merged.get("com.lucid.service") or "").strip()

    if host:
        merged["com.lucid.service"] = host["com.lucid.service"]
        for k, v in host.items():
            if not k.startswith("com.lucid.") or k == "com.lucid.service":
                continue
            sv = _label_scalar_str(v)
            if sv:
                merged[k] = sv
    else:
        merged["com.lucid.service"] = lookup_svc

    svc = str(merged.get("com.lucid.service", "")).strip()
    cluster = str(merged.get("com.lucid.cluster", "")).strip()

    if host and str(host.get("com.lucid.plane", "")).strip():
        merged["com.lucid.plane"] = _label_scalar_str(host["com.lucid.plane"])
    else:
        merged["com.lucid.plane"] = infer_plane(cluster, svc)

    if not str(merged.get("com.lucid.architecture", "")).strip():
        merged["com.lucid.architecture"] = "linux/arm64"
    if not str(merged.get("com.lucid.vulnerabilities", "")).strip():
        merged["com.lucid.vulnerabilities"] = "zero"
    if not str(merged.get("com.lucid.tor.compatible", "")).strip():
        merged["com.lucid.tor.compatible"] = "true"
    if not str(merged.get("com.lucid.env.config", "")).strip():
        merged["com.lucid.env.config"] = default_env_config(svc, cluster)

    if not host:
        if not str(merged.get("com.lucid.platform", "")).strip():
            merged["com.lucid.platform"] = "arm64"
        if not str(merged.get("com.lucid.security", "")).strip():
            merged["com.lucid.security"] = "distroless"

    layer = resolve_layer_value(merged, cluster, svc, relpath)
    merged["com.lucid.layer"] = layer
    merged["org.lucid.layer"] = layer
    return merged


def find_env_span_after(text: str, label_end: int) -> tuple[int, int] | None:
    sub = text[label_end:]
    m = re.search(r"(?m)^ENV\s+", sub)
    if not m:
        return None
    start = label_end + m.start()
    p = start
    while p < len(text):
        nl = text.find("\n", p)
        if nl == -1:
            return start, len(text)
        line = text[p:nl]
        p = nl + 1
        if line.rstrip().endswith("\\"):
            continue
        return start, nl + 1
    return start, len(text)


def parse_env_block(block: str) -> dict[str, str]:
    s = block.strip()
    if s.upper().startswith("ENV"):
        s = s[3:].lstrip()
    s = re.sub(r"\\\s*\n\s*", "", s)
    pairs: dict[str, str] = {}
    i = 0
    n = len(s)
    while i < n:
        while i < n and s[i].isspace():
            i += 1
        if i >= n:
            break
        m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)=", s[i:])
        if not m:
            break
        key = m.group(1)
        i += m.end()
        if i < n and s[i] == '"':
            i += 1
            val_chars: list[str] = []
            while i < n:
                if s[i] == "\\" and i + 1 < n:
                    val_chars.append(s[i + 1])
                    i += 2
                    continue
                if s[i] == '"':
                    i += 1
                    break
                val_chars.append(s[i])
                i += 1
            pairs[key] = "".join(val_chars)
        else:
            val_chars = []
            while i < n:
                if s[i].isspace():
                    break
                val_chars.append(s[i])
                i += 1
            pairs[key] = "".join(val_chars)
    return pairs


def _env_value_token(v: str) -> str:
    if "$" in v:
        return v
    esc = v.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{esc}"'


def format_env_block(pairs: dict[str, str]) -> str:
    ordered_keys: list[str] = []
    for k in ENV_PRIMARY_ORDER:
        if k in pairs:
            ordered_keys.append(k)
    for k in sorted(pairs.keys()):
        if k not in ordered_keys:
            ordered_keys.append(k)
    lines: list[str] = []
    for i, k in enumerate(ordered_keys):
        v = pairs[k]
        tok = _env_value_token(v)
        cont = " \\" if i < len(ordered_keys) - 1 else ""
        if i == 0:
            lines.append(f"ENV {k}={tok}{cont}")
        else:
            lines.append(f"    {k}={tok}{cont}")
    return "\n".join(lines) + "\n"


def is_project_dockerfile(path: Path) -> bool:
    """True for Dockerfile / dockerfile or Dockerfile.* / dockerfile.* (case on 'Dockerfile' varies).

    Excludes names like dockerfile-design.md (no dot after dockerfile) and *.md tails.
    """
    n = path.name.lower()
    if n == "dockerfile":
        return True
    if n.startswith("dockerfile."):
        return not n.endswith(".md")
    return False


def iter_dockerfiles(under: list[Path] | None = None) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    # Linux/macOS: Dockerfile* misses dockerfile.admin-overlord; scan both casings.
    for pattern in ("Dockerfile*", "dockerfile*"):
        for p in REPO_ROOT.rglob(pattern):
            if not p.is_file():
                continue
            if not is_project_dockerfile(p):
                continue
            if any(part in SKIP_DIR_NAMES for part in p.parts):
                continue
            if any(part in SKIP_PATH_PARTS for part in p.parts):
                continue
            key = str(p.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    resolved = sorted(out, key=lambda x: str(x).lower())
    if not under:
        return resolved
    bases = [(REPO_ROOT / u).resolve() for u in under]
    filtered: list[Path] = []
    for p in resolved:
        pr = p.resolve()
        for b in bases:
            try:
                pr.relative_to(b)
            except ValueError:
                continue
            filtered.append(p)
            break
    return filtered


def process_file(path: Path, host_index: dict[str, dict[str, str]], apply: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(REPO_ROOT).as_posix()
    spans = find_all_label_spans(text)
    if not spans:
        return False

    new_text = text
    changed = False
    for start, end in reversed(spans):
        old_block = new_text[start:end]
        old_labels, _ = parse_label_block_ordered(old_block)
        had_keys = set(old_labels.keys())
        svc = (
            old_labels.get("com.lucid.service") or old_labels.get("org.lucid.service") or ""
        ).strip()
        if not svc:
            continue
        host = host_index.get(svc)
        merged = merge_labels(old_labels, host, rel)
        sync_org_lucid_from_com(merged, had_keys)
        order = build_label_order(merged)
        new_label = format_label_block(merged, order)

        if new_label != old_block:
            new_text = new_text[:start] + new_label + new_text[end:]
            changed = True

    if not changed:
        return False

    last = find_last_label_span(new_text)
    if last:
        _, end = last
        env_span = find_env_span_after(new_text, end)
        if env_span:
            es, ee = env_span
            env_block = new_text[es:ee]
            pairs = parse_env_block(env_block)
            new_env = format_env_block(pairs)
            rebuilt = new_text[:es] + new_env + new_text[ee:]
            if rebuilt != new_text:
                new_text = rebuilt

    if new_text == text:
        return False
    if apply:
        path.write_text(new_text, encoding="utf-8", newline="\n")
    print(f"{'WROTE' if apply else 'DRY'} {rel}")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Write changes (default is dry-run)",
    )
    ap.add_argument(
        "--under",
        type=Path,
        action="append",
        default=None,
        metavar="REL_PATH",
        help=(
            "Only Dockerfiles under this path relative to the repo root (repeatable). "
            "Example: infrastructure/docker"
        ),
    )
    args = ap.parse_args()
    if not HOST_CONFIG.is_file():
        print(f"Missing {HOST_CONFIG}", file=sys.stderr)
        return 1
    host_index = load_host_index(HOST_CONFIG)
    n = 0
    for p in iter_dockerfiles(args.under):
        if process_file(p, host_index, args.apply):
            n += 1
    print(f"{'Updated' if args.apply else 'Would update'} {n} file(s).")
    if n == 0 and not args.apply:
        print(
            "Note: 0 changes can mean labels already match this script's rules, or "
            "no LABEL had com.lucid.service/org.lucid.service, or the service name is "
            "not in host-config.yml (no registry row / tag alias). "
            "Dry-run never writes; use --apply to save."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
