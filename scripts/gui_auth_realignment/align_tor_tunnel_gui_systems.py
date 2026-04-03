#!/usr/bin/env python3
"""
File: scripts/gui_auth_realignment/align_tor_tunnel_gui_systems.py

Aligns **A7 gui-tor-manager** Tier A manifest + **tor_socks / tunnel_tools** compose/config
counterparts with the GUI token auth realignment plan (two anchors only):

  - ports.txt
  - infrastructure/containers/host-config.yml

Plan refs: client metadata + bridge/gateway bootstrap in Tier A JSON only; no secrets in JSON;
Tier A -> gui-api-bridge -> api-gateway -> lucid-auth-service (never emit lucid-auth URLs in Tier A
manifests). See .cursor/plans/gui_token_auth_realignment_04c1ab54.plan.md.

Touches (repo-root relative):
  - configs/gui-alignment/gui-tor-manager.json — policy-validated (gui_json_policy.json)
  - configs/docker/docker-compose.gui-integration.yml — gui-tor-manager: drop duplicate gateway env;
    tor plane env from anchors (operational shim until app loads JSON only)
  - configs/container/tor/docker-compose.proxy-systems.yml — tunnel-tools / tor-proxy labels+env
  - 02_network_security/tunnels/config/tunnel-config.yaml
  - 02_network_security/tunnels/config/env-tunnel-tools.template

Does not modify anchors. Defaults: policy validation is strict (exit 2 on violation).

Usage:
  python scripts/gui_auth_realignment/align_tor_tunnel_gui_systems.py [--repo-root PATH] [--dry-run]
      [--backup] [--no-strict] [--verify]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

try:
    import yaml  # type: ignore
except ImportError as e:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from e

try:
    from ruamel.yaml import YAML  # type: ignore
except ImportError:  # pragma: no cover
    YAML = None  # type: ignore

from lib.gui_json_policy import load_policy, validate_manifest  # noqa: E402

TOR_CONTROL_PORT_DEFAULT = 9051

ANCHOR_HOST_CONFIG = Path("infrastructure/containers/host-config.yml")
ANCHOR_PORTS_TXT = Path("ports.txt")
GUI_TOR_MANAGER_JSON = Path("configs/gui-alignment/gui-tor-manager.json")
GUI_INTEGRATION_COMPOSE = Path("configs/docker/docker-compose.gui-integration.yml")
PROXY_COMPOSE = Path("configs/container/tor/docker-compose.proxy-systems.yml")
TUNNEL_CONFIG_YAML = Path("02_network_security/tunnels/config/tunnel-config.yaml")
ENV_TUNNEL_TEMPLATE = Path("02_network_security/tunnels/config/env-tunnel-tools.template")

# Print PyYAML fallback note at most once (two compose files call _load_yaml_roundtrip).
_PYYAML_FALLBACK_NOTED = False


@dataclass(frozen=True)
class ResolvedTorTunnelGui:
    tor_socks_host: str
    tor_socks_port: int
    tunnel_tools_host: str
    tunnel_tools_port: int
    api_gateway_url: str
    gui_api_bridge_url: str
    gui_api_bridge_public_url: str
    gui_tor_listen_port: int
    gui_tor_calling_service: str
    gui_tor_http_path: str
    gateway_service_id: str
    bridge_service_id: str
    tor_service_id: str
    tunnel_service_id: str
    gui_tor_service_id: str


def _repo_root(repo: Optional[str]) -> Path:
    if repo:
        return Path(repo).resolve()
    return Path(__file__).resolve().parents[2]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _read_text_flexible(path: Path) -> str:
    raw = path.read_bytes()
    if len(raw) >= 2 and raw[0:2] == b"\xff\xfe":
        return raw.decode("utf-16-le")
    if len(raw) >= 2 and raw[0:2] == b"\xfe\xff":
        return raw.decode("utf-16-be")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    return raw.decode("utf-8", errors="replace")


def _read_yaml(path: Path) -> Any:
    return yaml.safe_load(_read_text_flexible(path))


def _http_base_from_path(http_path: str) -> str:
    s = (http_path or "").strip()
    if s.endswith("/app"):
        s = s[: -len("/app")]
    return s.rstrip("/") or s


def _service_block(services: Mapping[str, Any], service_id: str) -> Dict[str, Any]:
    raw = services.get(service_id)
    if not isinstance(raw, dict):
        raise KeyError(f"host-config services.{service_id} missing or not a mapping")
    return raw


def resolve_from_anchors(repo: Path) -> ResolvedTorTunnelGui:
    hc_path = repo / ANCHOR_HOST_CONFIG
    if not hc_path.is_file():
        raise FileNotFoundError(hc_path)
    ports_path = repo / ANCHOR_PORTS_TXT
    if not ports_path.is_file():
        raise FileNotFoundError(ports_path)

    data = _read_yaml(hc_path)
    services = data.get("services")
    if not isinstance(services, dict):
        raise ValueError("host-config.yml: services map required")

    tor = _service_block(services, "tor_socks")
    tun = _service_block(services, "tunnel_tools")
    gw = _service_block(services, "main_lucid_gateway")
    bridge = _service_block(services, "gui_api_bridge")
    gtm = _service_block(services, "gui_tor_manager_http")

    tor_host = str(tor["service_name"])
    tor_port = int(tor["port"])
    tun_host = str(tun["service_name"])
    tun_port = int(tun["port"])

    gw_base = _http_base_from_path(str(gw.get("http_path", "")))
    bridge_base = _http_base_from_path(str(bridge.get("http_path", "")))
    if not gw_base or "://" not in gw_base:
        gw_base = f"http://{gw['service_name']}:{gw['port']}"
    if not bridge_base or "://" not in bridge_base:
        bridge_base = f"http://{bridge['service_name']}:{bridge['port']}"

    listen = int(gtm["port"])
    calling = str(gtm["service_name"])
    gtm_path = str(gtm.get("http_path") or f"http://{calling}:{listen}/app")

    if tor_port <= 0 or tun_port <= 0:
        raise ValueError("tor_socks and tunnel_tools ports must be positive in host-config")
    if listen <= 0:
        raise ValueError("gui_tor_manager_http.port must be positive in host-config")

    ports_text = _read_text_flexible(ports_path)
    for p in (tor_port, tun_port, TOR_CONTROL_PORT_DEFAULT, int(gw["port"]), int(bridge["port"]), listen):
        if not re.search(rf"(?<![0-9]){int(p)}(?![0-9])", ports_text):
            raise ValueError(
                f"Port {p} from host-config not found in {ANCHOR_PORTS_TXT} - reconcile anchors first."
            )

    public_bridge = bridge_base  # in-network public URL for bridge discovery (Docker DNS base)

    return ResolvedTorTunnelGui(
        tor_socks_host=tor_host,
        tor_socks_port=tor_port,
        tunnel_tools_host=tun_host,
        tunnel_tools_port=tun_port,
        api_gateway_url=gw_base,
        gui_api_bridge_url=bridge_base,
        gui_api_bridge_public_url=public_bridge,
        gui_tor_listen_port=listen,
        gui_tor_calling_service=calling,
        gui_tor_http_path=gtm_path,
        gateway_service_id="main_lucid_gateway",
        bridge_service_id="gui_api_bridge",
        tor_service_id="tor_socks",
        tunnel_service_id="tunnel_tools",
        gui_tor_service_id="gui_tor_manager_http",
    )


def _maybe_backup(path: Path, backup: bool) -> None:
    if not backup or not path.is_file():
        return
    bak = path.with_suffix(path.suffix + f".bak.{_utc_stamp()}")
    shutil.copy2(path, bak)


def _dump_yaml(root: Any) -> str:
    if YAML is not None:
        y = YAML()
        y.preserve_quotes = True
        y.width = 4096
        buf = StringIO()
        y.dump(root, buf)
        return buf.getvalue()
    return yaml.safe_dump(
        root,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=120,
    )


def _load_yaml_roundtrip(raw: str) -> tuple[Any, bool]:
    global _PYYAML_FALLBACK_NOTED
    if YAML is not None:
        y = YAML()
        y.preserve_quotes = True
        y.width = 4096
        return y.load(raw), True
    if not _PYYAML_FALLBACK_NOTED:
        print(
            "NOTE: ruamel.yaml not installed; using PyYAML (compose layout may shift). "
            "Install: pip install -r scripts/gui_auth_realignment/requirements.txt",
            file=sys.stderr,
        )
        _PYYAML_FALLBACK_NOTED = True
    return yaml.safe_load(raw), False


def _manifest_auth_bypass_check(manifest: Dict[str, Any]) -> List[str]:
    """Tier A must not name lucid-auth directly; bootstrap is bridge + gateway only."""
    issues: List[str] = []
    blob = json.dumps(manifest, ensure_ascii=False)
    if "lucid-auth-service" in blob:
        issues.append("manifest must not reference lucid-auth-service (use api_gateway_url + bridge only)")
    # :8089 alone is too loose; require auth hostname pattern
    if re.search(r"lucid-auth[^\s\"']*:\s*8089|8089\/auth", blob, re.I):
        issues.append("manifest must not embed direct auth service URL/port for clients")
    return issues


def build_gui_tor_manifest(existing: Dict[str, Any], r: ResolvedTorTunnelGui, policy: Dict[str, Any]) -> Dict[str, Any]:
    """Tier A JSON per plan + gui_json_policy required_non_secret_fields and injection map."""
    inj = policy.get("injection_from_anchors") or {}
    merged = dict(existing)
    merged["schema_version"] = merged.get("schema_version", 1)
    merged["compose_service"] = "gui-tor-manager"
    merged["calling_service"] = r.gui_tor_calling_service
    merged["listen_port"] = r.gui_tor_listen_port
    merged["api_gateway_url"] = r.api_gateway_url
    merged["machine_id"] = merged.get("machine_id", "")
    merged["location"] = merged.get("location", "")

    bridge_field = str(inj.get("gui_api_bridge", "gui_api_bridge_public_url"))
    merged[bridge_field] = r.gui_api_bridge_public_url
    merged["gui_api_bridge_url"] = r.gui_api_bridge_url

    merged["host_config_alignment"] = {
        "schema_version": 1,
        "gateway": {
            "service_id": r.gateway_service_id,
            "http_path": f"{r.api_gateway_url}/app",
        },
        "gui_api_bridge": {
            "service_id": r.bridge_service_id,
            "http_path": f"{r.gui_api_bridge_url}/app",
        },
        "tor_socks": {"service_id": r.tor_service_id, "service_name": r.tor_socks_host, "port": r.tor_socks_port},
        "tunnel_tools": {
            "service_id": r.tunnel_service_id,
            "service_name": r.tunnel_tools_host,
            "port": r.tunnel_tools_port,
        },
        "gui_tor_manager": {
            "service_id": r.gui_tor_service_id,
            "service_name": r.gui_tor_calling_service,
            "port": r.gui_tor_listen_port,
            "http_path": r.gui_tor_http_path,
        },
    }
    merged["tor_socks_host"] = r.tor_socks_host
    merged["tor_socks_port"] = r.tor_socks_port
    merged["tor_control_host"] = r.tor_socks_host
    merged["tor_control_port"] = TOR_CONTROL_PORT_DEFAULT
    merged["tor_control_url"] = f"http://{r.tor_socks_host}:{TOR_CONTROL_PORT_DEFAULT}"
    merged["tunnel_tools_host"] = r.tunnel_tools_host
    merged["tunnel_tools_port"] = r.tunnel_tools_port
    merged["tunnel_tools_base_url"] = f"http://{r.tunnel_tools_host}:{r.tunnel_tools_port}"
    return merged


def _patch_gui_tor_manager_json(
    repo: Path, r: ResolvedTorTunnelGui, policy: Dict[str, Any], strict: bool, dry_run: bool, backup: bool
) -> int:
    path = repo / GUI_TOR_MANAGER_JSON
    existing: Dict[str, Any] = {}
    if path.is_file():
        existing = json.loads(_read_text_flexible(path))

    merged = build_gui_tor_manifest(existing, r, policy)
    policy_issues = validate_manifest(merged, policy)
    bypass_issues = _manifest_auth_bypass_check(merged)
    all_issues = policy_issues + bypass_issues
    if all_issues:
        for i in all_issues:
            print(f"manifest policy: {i}", file=sys.stderr)
        if strict:
            return 2

    text = json.dumps(merged, indent=2, sort_keys=False) + "\n"
    if dry_run:
        print(f"[dry-run] would write {path} ({len(text)} bytes)")
        return 0
    if backup:
        _maybe_backup(path, True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return 0


def _mutate_proxy_compose_tree(root: Any, r: ResolvedTorTunnelGui) -> None:
    if not isinstance(root, dict) or "services" not in root:
        raise ValueError(f"{PROXY_COMPOSE}: expected mapping with services")
    services = root["services"]
    if not isinstance(services, dict):
        raise ValueError(f"{PROXY_COMPOSE}: services must be a mapping")

    tor = services.get("tor-proxy")
    if isinstance(tor, dict):
        labels = tor.get("labels")
        if isinstance(labels, dict):
            labels["com.lucid.service"] = r.tor_socks_host

    tun = services.get("tunnel-tools")
    if isinstance(tun, dict):
        env = tun.get("environment")
        if not isinstance(env, dict):
            env = {}
            tun["environment"] = env
        env["CONTROL_HOST"] = r.tor_socks_host
        env["CONTROL_PORT"] = str(TOR_CONTROL_PORT_DEFAULT)
        env["TUNNEL_PORT"] = str(r.tunnel_tools_port)
        env["TOR_PROXY"] = f"{r.tor_socks_host}:{r.tor_socks_port}"


def _patch_proxy_compose(repo: Path, r: ResolvedTorTunnelGui, dry_run: bool, backup: bool) -> None:
    path = repo / PROXY_COMPOSE
    if not path.is_file():
        print(f"skip missing {PROXY_COMPOSE}")
        return
    raw = _read_text_flexible(path)
    root, _ = _load_yaml_roundtrip(raw)
    _mutate_proxy_compose_tree(root, r)
    out = _dump_yaml(root)
    if dry_run:
        print(f"[dry-run] would write {path}")
        return
    if backup:
        _maybe_backup(path, True)
    path.write_text(out, encoding="utf-8")


def _mutate_gui_integration_tor_manager(root: Any, r: ResolvedTorTunnelGui) -> None:
    """gui-tor-manager: remove duplicate API_GATEWAY_URL; tor env from anchors (compose counterpart)."""
    if not isinstance(root, dict) or "services" not in root:
        raise ValueError(f"{GUI_INTEGRATION_COMPOSE}: expected mapping with services")
    services = root["services"]
    if not isinstance(services, dict):
        raise ValueError(f"{GUI_INTEGRATION_COMPOSE}: services must be a mapping")
    svc = services.get("gui-tor-manager")
    if not isinstance(svc, dict):
        print(f"skip: no gui-tor-manager in {GUI_INTEGRATION_COMPOSE}", file=sys.stderr)
        return
    env = svc.get("environment")
    if not isinstance(env, dict):
        env = {}
        svc["environment"] = env
    env.pop("API_GATEWAY_URL", None)
    env["LUCID_GUI_ALIGNMENT_JSON"] = "/app/configs/gui-alignment/gui-tor-manager.json"
    env["TOR_PROXY_HOST"] = r.tor_socks_host
    env["TOR_PROXY_URL"] = f"http://{r.tor_socks_host}:{TOR_CONTROL_PORT_DEFAULT}"
    env["TOR_SOCKS_PORT"] = str(r.tor_socks_port)
    env["TOR_CONTROL_PORT"] = str(TOR_CONTROL_PORT_DEFAULT)


def _patch_gui_integration_compose(repo: Path, r: ResolvedTorTunnelGui, dry_run: bool, backup: bool) -> None:
    path = repo / GUI_INTEGRATION_COMPOSE
    if not path.is_file():
        print(f"skip missing {GUI_INTEGRATION_COMPOSE}")
        return
    raw = _read_text_flexible(path)
    root, _ = _load_yaml_roundtrip(raw)
    _mutate_gui_integration_tor_manager(root, r)
    out = _dump_yaml(root)
    if dry_run:
        print(f"[dry-run] would write {path}")
        return
    if backup:
        _maybe_backup(path, True)
    path.write_text(out, encoding="utf-8")


def _patch_tunnel_config_yaml(repo: Path, r: ResolvedTorTunnelGui, dry_run: bool, backup: bool) -> None:
    path = repo / TUNNEL_CONFIG_YAML
    if not path.is_file():
        print(f"skip missing {TUNNEL_CONFIG_YAML}")
        return
    data = _read_yaml(path)
    if not isinstance(data, dict):
        raise ValueError(f"{TUNNEL_CONFIG_YAML}: root must be mapping")
    g = data.get("global")
    if not isinstance(g, dict):
        g = {}
        data["global"] = g
    g["tor_control_host"] = r.tor_socks_host
    g["tor_control_port"] = TOR_CONTROL_PORT_DEFAULT
    g["tor_proxy_host"] = r.tor_socks_host
    g["tor_proxy_port"] = r.tor_socks_port
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)
    if dry_run:
        print(f"[dry-run] would write {path}")
        return
    if backup:
        _maybe_backup(path, True)
    path.write_text(text, encoding="utf-8")


def _patch_env_tunnel_template(repo: Path, r: ResolvedTorTunnelGui, dry_run: bool, backup: bool) -> None:
    path = repo / ENV_TUNNEL_TEMPLATE
    if not path.is_file():
        print(f"skip missing {ENV_TUNNEL_TEMPLATE}")
        return
    lines = _read_text_flexible(path).splitlines(keepends=True)
    replacements = {
        "CONTROL_HOST=": f"CONTROL_HOST={r.tor_socks_host}\n",
        "CONTROL_PORT=": f"CONTROL_PORT={TOR_CONTROL_PORT_DEFAULT}\n",
        "TOR_PROXY=": f"TOR_PROXY={r.tor_socks_host}:{r.tor_socks_port}\n",
        "TOR_PROXY_HOST=": f"TOR_PROXY_HOST={r.tor_socks_host}\n",
        "TOR_PROXY_PORT=": f"TOR_PROXY_PORT={r.tor_socks_port}\n",
        "SERVICE_PORT=": f"SERVICE_PORT={r.tunnel_tools_port}\n",
        "TUNNEL_PORT=": f"TUNNEL_PORT={r.tunnel_tools_port}\n",
    }
    keys_ordered = list(replacements.keys())
    out: list[str] = []
    for line in lines:
        replaced = False
        for key in keys_ordered:
            if line.startswith(key) and not line.strip().startswith("#"):
                out.append(replacements[key])
                replaced = True
                break
        if not replaced:
            out.append(line)
    text = "".join(out)
    if dry_run:
        print(f"[dry-run] would write {path}")
        return
    if backup:
        _maybe_backup(path, True)
    path.write_text(text, encoding="utf-8")


def _run_verify(repo: Path) -> int:
    verify = _HERE / "step_verify_alignment.py"
    if not verify.is_file():
        print("WARNING: --verify skipped (step_verify_alignment.py missing).", file=sys.stderr)
        return 0
    print("T8: running step_verify_alignment.py ...", flush=True)
    rc = subprocess.call([sys.executable, str(verify), "--repo-root", str(repo)])
    status = "PASS" if rc == 0 else "FAIL"
    print(f"T8: step_verify_alignment.py finished ({status}, exit {rc}).", flush=True)
    return rc


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Align gui-tor-manager Tier A JSON + tor/tunnel counterparts to host-config + ports.txt (plan)."
    )
    ap.add_argument("--repo-root", default=None, help="Repository root (default: Lucid repo root)")
    ap.add_argument("--dry-run", action="store_true", help="Do not write files.")
    ap.add_argument("--backup", action="store_true", help="Write .bak.<UTC> before each overwrite.")
    ap.add_argument(
        "--no-strict",
        action="store_true",
        help="Log manifest policy violations but do not exit 2 (not recommended).",
    )
    ap.add_argument(
        "--verify",
        action="store_true",
        help="After writes, run step_verify_alignment.py (T8 mat port check).",
    )
    args = ap.parse_args()
    repo = _repo_root(args.repo_root)
    strict = not args.no_strict

    policy = load_policy(repo)
    r = resolve_from_anchors(repo)
    print(
        "Resolved anchors (counterparts derive from these only):\n"
        f"  {r.tor_service_id} -> {r.tor_socks_host}:{r.tor_socks_port}\n"
        f"  {r.tunnel_service_id} -> {r.tunnel_tools_host}:{r.tunnel_tools_port}\n"
        f"  {r.gateway_service_id} -> {r.api_gateway_url}\n"
        f"  {r.bridge_service_id} -> {r.gui_api_bridge_url} (policy field: gui_api_bridge_public_url)\n"
        f"  {r.gui_tor_service_id} -> {r.gui_tor_calling_service}:{r.gui_tor_listen_port}\n"
    )

    rc = _patch_gui_tor_manager_json(repo, r, policy, strict, args.dry_run, args.backup)
    if rc != 0:
        return rc

    _patch_gui_integration_compose(repo, r, args.dry_run, args.backup)
    _patch_proxy_compose(repo, r, args.dry_run, args.backup)
    _patch_tunnel_config_yaml(repo, r, args.dry_run, args.backup)
    _patch_env_tunnel_template(repo, r, args.dry_run, args.backup)

    target_paths = [
        GUI_TOR_MANAGER_JSON,
        GUI_INTEGRATION_COMPOSE,
        PROXY_COMPOSE,
        TUNNEL_CONFIG_YAML,
        ENV_TUNNEL_TEMPLATE,
    ]
    if args.dry_run:
        print("[dry-run] No files modified. Would consider:", flush=True)
        for rel in target_paths:
            print(f"  - {rel.as_posix()}", flush=True)
        if args.verify:
            print("[dry-run] --verify not run (no writes).", flush=True)
        return 0

    print("OK: alignment pass finished (each path updated if it exists; missing paths logged above).", flush=True)
    for rel in target_paths:
        mark = "ok" if (repo / rel).is_file() else "MISSING"
        print(f"  [{mark}] {rel.as_posix()}", flush=True)

    if args.verify:
        return _run_verify(repo)
    print("T8: skipped (use --verify to run step_verify_alignment.py).", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
