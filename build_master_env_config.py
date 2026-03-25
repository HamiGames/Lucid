#!/usr/bin/env python3
"""
One-shot builder: pi-env-configs.txt -> master-env-config.txt
Uses ports.txt as authoritative service_name -> port reference.
Path: c:\\Users\\surba\\Desktop\\personal\\THE_FUCKER\\lucid_2\\Lucid\\build_master_env_config.py
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORTS = ROOT / "ports.txt"
SOURCE = ROOT / "pi-env-configs.txt"
OUT = ROOT / "master-env-config.txt"

ENV_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)\s*$")
# Lookahead allows `}` so ${VAR:-http://host:port} matches (shell default syntax).
URL_RE = re.compile(
    r"(https?://)([^/:?#]+)(?::(\d+))?(?=[/?#\}]|$)",
    re.IGNORECASE,
)


def parse_ports(path: Path) -> dict[str, int]:
    """service_name (lowercase) -> port from ports.txt YAML-like blocks."""
    name_to_port: dict[str, int] = {}
    port: int | None = None
    sname: str | None = None

    def flush() -> None:
        nonlocal port, sname
        if port is not None and sname:
            name_to_port[sname.lower()] = port
        port = None
        sname = None

    text = path.read_text(encoding="utf-8", errors="replace")
    text = text.replace("**session_processor:", "  session_processor:")
    for line in text.splitlines():
        if line.strip().startswith("#"):
            continue
        if re.match(r"^  [a-zA-Z_][a-zA-Z0-9_]*:\s*$", line):
            flush()
            continue
        mp = re.match(r"^    port:\s*(\d+)\s*$", line)
        if mp:
            port = int(mp.group(1))
        ms = re.match(r"^    service_name:\s*([^\s#]+)", line)
        if ms:
            sname = ms.group(1).strip()
    flush()
    return name_to_port


def host_aliases(name_to_port: dict[str, int]) -> dict[str, int]:
    """Map docker hostnames (with optional lucid- prefix) -> port."""
    m: dict[str, int] = {}
    for svc, p in name_to_port.items():
        m[svc] = p
        if not svc.startswith("lucid-"):
            m[f"lucid-{svc}"] = p
        # underscore form sometimes used in NO_PROXY
        u = svc.replace("-", "_")
        m[u] = p
        m[f"lucid_{u}"] = p
    # Short names used in pi-env-configs -> canonical service_name from ports.txt
    if "lucid-service-mesh-controller" in name_to_port:
        p = name_to_port["lucid-service-mesh-controller"]
        m["service-mesh-controller"] = p
        m["service-mesh"] = p
    return m


def kebab_from_env_port_key(key: str) -> str | None:
    if not key.endswith("_PORT"):
        return None
    base = key[: -len("_PORT")]
    return base.lower().replace("_", "-")


def fix_url_ports(value: str, hmap: dict[str, int]) -> str:
    """Fix :port in http(s)://host:port when host maps to a different canonical port."""

    def repl(m: re.Match[str]) -> str:
        proto, host, port_s = m.group(1), m.group(2).lower(), m.group(3)
        hl = host.lower()
        if hl not in hmap:
            return m.group(0)
        expected = hmap[hl]
        if port_s is None:
            return f"{proto}{host}:{expected}"
        if int(port_s) != expected:
            return f"{proto}{host}:{expected}"
        return m.group(0)

    return URL_RE.sub(repl, value)


def canonical_alias_map(name_to_port: dict[str, int]) -> dict[str, str]:
    """lucid-* alias -> canonical service_name from ports.txt (when applicable)."""
    m: dict[str, str] = {}
    for canonical in name_to_port.keys():
        cl = canonical.lower()
        m[cl] = canonical
        if not cl.startswith("lucid-"):
            m["lucid-" + cl] = canonical
    if "lucid-service-mesh-controller" in name_to_port:
        c = "lucid-service-mesh-controller"
        m["service-mesh-controller"] = c
        m["service-mesh"] = c
    return m


def rewrite_canonical_hosts(value: str, cam: dict[str, str]) -> str:
    """Normalize Docker hostnames in http(s) URLs to ports.txt service_name form."""

    def repl(m: re.Match[str]) -> str:
        proto, host, port_s = m.group(1), m.group(2), m.group(3)
        hl = host.lower()
        new_h = cam.get(hl, host)
        if port_s:
            return f"{proto}{new_h}:{port_s}"
        return f"{proto}{new_h}"

    return URL_RE.sub(repl, value)


def score_value(key: str, val: str) -> tuple[int, int]:
    """
    Higher is better for choosing among duplicate keys.
    Prefer non-empty, no bare IPs for URLs, no WORKERS=*.
    """
    score = 0
    if val.strip():
        score += 10
    if val.strip() == "":
        score -= 100
    if key == "WORKERS" and val.strip() == "*":
        score -= 50
    # Bind/listen addresses must win over service hostnames (duplicate templates).
    if key.endswith("_HOST") or key in ("HOST", "BIND_ADDRESS"):
        if val.strip() in ("0.0.0.0", "::", "[::]"):
            score += 100
    if "_URL" in key or key.endswith("_URI") or "URL" in key:
        if re.search(r"https?://\d+\.\d+\.\d+\.\d+:", val):
            score -= 5
        if re.search(r"https?://[a-z0-9.-]+:\d+", val) and not re.search(
            r"https?://\d+\.\d+\.\d+\.\d+:", val
        ):
            score += 3
    return (score, len(val))


def main() -> None:
    name_to_port = parse_ports(PORTS)
    hmap = host_aliases(name_to_port)
    cam = canonical_alias_map(name_to_port)

    # key -> list of (score, value) from all occurrences
    candidates: dict[str, list[tuple[tuple[int, int], str]]] = defaultdict(list)

    raw_lines = SOURCE.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in raw_lines:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # Orphan URL line (invalid in source): attach to DATA_CHAIN_HEALTH_URL if missing key
        if s.startswith("http://") and "=" not in s:
            s = f"DATA_CHAIN_HEALTH_URL={s}"
        m = ENV_KEY_RE.match(line.rstrip())
        if not m:
            continue
        key, val = m.group(1), m.group(2)
        candidates[key].append((score_value(key, val), val))

    merged: dict[str, str] = {}
    for key, cands in candidates.items():
        best = max(cands, key=lambda x: x[0])
        merged[key] = best[1]

    # Correct *_PORT from ports.txt when kebab key matches a service_name
    for key, val in list(merged.items()):
        ksvc = kebab_from_env_port_key(key)
        if ksvc and ksvc in name_to_port:
            merged[key] = str(name_to_port[ksvc])
            continue
        # admin-ui-backend style exceptions
        if key == "ADMIN_INTERFACE_PORT":
            merged[key] = str(name_to_port.get("admin-ui-backend", int(val) if val.isdigit() else 8120))

    # Fix URLs: port alignment, then canonical hostnames per ports.txt
    for key, val in list(merged.items()):
        if "://" not in val:
            continue
        val = fix_url_ports(val, hmap)
        merged[key] = rewrite_canonical_hosts(val, cam)

    # Special: SESSION_MANAGEMENT_URL / SESSION_API often confused with 8087 in source
    if "session-api" in name_to_port:
        p = name_to_port["session-api"]
        for k in ("SESSION_API_URL", "SESSION_MANAGEMENT_URL", "SESSION_MANAGEMENT_URI"):
            if k in merged and "session" in merged[k].lower() and "8113" not in merged[k]:
                merged[k] = re.sub(
                    r"(https?://[^/:]+:)(\d+)",
                    lambda m: f"{m.group(1)}{p}",
                    merged[k],
                    count=1,
                )

    # WORKERS: drop wildcard
    if merged.get("WORKERS") == "*":
        merged["WORKERS"] = "4"

    # Admin UI listens as admin-ui-backend per ports.txt (not lucid-admin-interface:8083).
    if "admin-ui-backend" in name_to_port:
        p = name_to_port["admin-ui-backend"]
        merged["ADMIN_INTERFACE_URL"] = f"http://admin-ui-backend:{p}"

    # Primary HTTP for Consul / service mesh controller (ports.txt: lucid-service-mesh-controller:8500).
    if "lucid-service-mesh-controller" in name_to_port:
        p = name_to_port["lucid-service-mesh-controller"]
        merged["SERVICE_MESH_CONTROLLER_PORT"] = str(p)
        merged["SERVICE_MESH_CONTROLLER_HOST"] = "lucid-service-mesh-controller"

    # Sort keys for stable output
    ordered = sorted(merged.keys(), key=lambda x: (x.upper(), x))

    header = f"""# =============================================================================
# Lucid — master environment reference (deduplicated)
# Path: {OUT.as_posix()}
# Generated from: {SOURCE.name} + authoritative ports: {PORTS.name}
# Rules: one entry per key; duplicate keys resolved by best-scoring value then ports.txt alignment.
# Service hostnames and ports follow Docker DNS names in {PORTS.name} (service_name + port).
# Secrets remain as ${{...}} — fill via .env.secrets / deployment.
# =============================================================================

"""
    body = "\n".join(f"{k}={merged[k]}" for k in ordered) + "\n"
    OUT.write_text(header + body, encoding="utf-8")
    print(f"Wrote {OUT} ({len(merged)} unique keys)")


if __name__ == "__main__":
    main()
