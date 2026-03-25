#!/usr/bin/env python3
"""
Lucid Admin System Gateway — distroless portal (aligned with 03_api_gateway layout).
Loads /app/node/config/openssl-api.yml (TLS policy) and connections.json (routes).
Env overrides: ADMIN_GATEWAY_* and ADMIN_GATEWAY_UPSTREAM_<NAME>_HOST|PORT.
"""
from __future__ import annotations

import json
import os
import re
import signal
import socket
import ssl
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore

LOG = "[admin-system-gateway]"


def log(msg: str) -> None:
    print(f"{LOG} {msg}", flush=True)


def _route_env_key(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name.upper()).strip("_")


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        log(f"openssl-api yaml missing or not a file: {path} (using defaults)")
        return {}
    raw = path.read_text(encoding="utf-8")
    if yaml is None:
        log("WARNING: PyYAML not available; openssl-api.yml ignored")
        return {}
    data = yaml.safe_load(raw)
    return data if isinstance(data, dict) else {}


def load_connections(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        log(f"FATAL: connections json not found: {path}")
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def merge_route(
    route: Dict[str, Any],
    openssl_api: Dict[str, Any],
    env: os._Environ,
) -> Dict[str, Any]:
    name = str(route.get("name", "route"))
    key = _route_env_key(name)
    host = route.get("upstream_host", "127.0.0.1")
    port = int(route.get("upstream_port", 0))
    eh = env.get(f"ADMIN_GATEWAY_UPSTREAM_{key}_HOST")
    ep = env.get(f"ADMIN_GATEWAY_UPSTREAM_{key}_PORT")
    if eh:
        host = eh.strip()
    if ep:
        port = int(ep.strip())
    listen = int(route.get("listen_port", 0))
    lp = env.get(f"ADMIN_GATEWAY_LISTEN_{key}_PORT")
    if lp:
        listen = int(lp.strip())
    tls_up = bool(route.get("tls_upstream", False))
    tls_env = env.get(f"ADMIN_GATEWAY_UPSTREAM_{key}_TLS")
    if tls_env is not None:
        tls_up = tls_env.strip().lower() in ("1", "true", "yes", "on")
    profile = route.get("tls_profile")
    return {
        "name": name,
        "listen_port": listen,
        "upstream_host": host,
        "upstream_port": port,
        "tls_upstream": tls_up,
        "tls_profile": profile,
        "_openssl_api": openssl_api,
    }


def build_ssl_context(route: Dict[str, Any]) -> ssl.SSLContext:
    api = route.get("_openssl_api") or {}
    defaults = api.get("tls_client_defaults") or {}
    profiles = api.get("tls_profiles") or {}
    profile_name = route.get("tls_profile")
    prof = profiles.get(profile_name, {}) if profile_name else {}
    merged: Dict[str, Any] = {**defaults, **prof}

    cafile = os.getenv("ADMIN_GATEWAY_SSL_CA_FILE") or merged.get("cafile") or None
    certfile = os.getenv("ADMIN_GATEWAY_SSL_CERT_FILE") or merged.get("certfile") or None
    keyfile = os.getenv("ADMIN_GATEWAY_SSL_KEY_FILE") or merged.get("keyfile") or None
    if cafile == "":
        cafile = None
    if certfile == "":
        certfile = None
    if keyfile == "":
        keyfile = None

    min_ver_s = str(merged.get("minimum_version", "TLSv1_2"))
    verify_s = str(merged.get("verify_mode", "CERT_REQUIRED"))
    check_hostname = bool(merged.get("check_hostname", True))

    ctx = ssl.create_default_context(cafile=cafile)
    if min_ver_s == "TLSv1_3":
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    else:
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2

    if verify_s == "CERT_NONE":
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    else:
        ctx.check_hostname = check_hostname
        ctx.verify_mode = ssl.CERT_REQUIRED

    ciphers = api.get("ciphers") or ""
    if isinstance(ciphers, str) and ciphers.strip():
        ctx.set_ciphers(ciphers)

    if certfile and keyfile:
        ctx.load_cert_chain(certfile, keyfile)

    return ctx


def _pump(src: socket.socket, dst: socket.socket) -> None:
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        try:
            src.close()
        except OSError:
            pass
        try:
            dst.close()
        except OSError:
            pass


def _plain_forward_session(client: socket.socket, upstream_host: str, upstream_port: int) -> None:
    upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        upstream.connect((upstream_host, upstream_port))
    except OSError as exc:
        log(f"TCP upstream connect failed {upstream_host}:{upstream_port}: {exc}")
        client.close()
        return
    t1 = threading.Thread(target=_pump, args=(client, upstream), daemon=True)
    t2 = threading.Thread(target=_pump, args=(upstream, client), daemon=True)
    t1.start()
    t2.start()


def plain_tcp_forward_worker(listen_port: int, upstream_host: str, upstream_port: int) -> None:
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("0.0.0.0", listen_port))
    server_sock.listen(128)
    log(f"TCP forward listening on 0.0.0.0:{listen_port} -> {upstream_host}:{upstream_port}")
    while True:
        client, _ = server_sock.accept()
        threading.Thread(
            target=_plain_forward_session,
            args=(client, upstream_host, upstream_port),
            daemon=True,
        ).start()


def tls_tcp_forward_worker(
    listen_port: int,
    upstream_host: str,
    upstream_port: int,
    ssl_ctx: ssl.SSLContext,
) -> None:
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("0.0.0.0", listen_port))
    server_sock.listen(128)
    log(f"TLS forward listening on 0.0.0.0:{listen_port} -> {upstream_host}:{upstream_port}")

    while True:
        client, _ = server_sock.accept()
        threading.Thread(
            target=_tls_forward_session,
            args=(client, upstream_host, upstream_port, ssl_ctx),
            daemon=True,
        ).start()


def _tls_forward_session(
    client: socket.socket,
    upstream_host: str,
    upstream_port: int,
    ssl_ctx: ssl.SSLContext,
) -> None:
    upstream = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        upstream.connect((upstream_host, upstream_port))
        tls_sock = ssl_ctx.wrap_socket(upstream, server_hostname=upstream_host)
    except OSError as exc:
        log(f"TLS upstream connect failed {upstream_host}:{upstream_port}: {exc}")
        client.close()
        return

    t1 = threading.Thread(target=_pump, args=(client, tls_sock), daemon=True)
    t2 = threading.Thread(target=_pump, args=(tls_sock, client), daemon=True)
    t1.start()
    t2.start()


def start_health_server(bind: str, port: int, state: Dict[str, Any]) -> HTTPServer:
    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: Any) -> None:
            pass

        def do_GET(self) -> None:
            if self.path not in ("/health", "/health/", "/"):
                self.send_error(404)
                return
            body = json.dumps(
                {
                    "service": "admin-system-gateway",
                    "ok": True,
                    "routes": state.get("routes", []),
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = HTTPServer((bind, port), H)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    log(f"Health on http://{bind}:{port}/health")
    return srv


def _shutdown(_sig: int, _frame: Any) -> None:
    sys.exit(0)


def main() -> None:
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    env = os.environ
    yaml_path = Path(env.get("ADMIN_GATEWAY_OPENSSL_API_YAML", "/app/node/config/openssl-api.yml"))
    conn_path = Path(env.get("ADMIN_GATEWAY_CONNECTIONS_JSON", "/app/node/config/connections.json"))

    openssl_api = load_yaml(yaml_path)
    doc = load_connections(conn_path)
    routes_in = doc.get("routes")
    if not isinstance(routes_in, list):
        log("FATAL: connections.json must contain a routes array")
        sys.exit(1)

    merged_routes: List[Dict[str, Any]] = []
    for r in routes_in:
        if not isinstance(r, dict):
            continue
        merged_routes.append(merge_route(r, openssl_api, env))

    state: Dict[str, Any] = {"routes": [r["name"] for r in merged_routes]}

    health_bind = env.get("ADMIN_GATEWAY_HEALTH_BIND", "0.0.0.0")
    health_port = int(env.get("ADMIN_GATEWAY_HEALTH_PORT", "8155"))
    start_health_server(health_bind, health_port, state)

    for route in merged_routes:
        lp = int(route["listen_port"])
        uh = str(route["upstream_host"])
        up = int(route["upstream_port"])
        if lp <= 0 or up <= 0:
            log(f"Skip invalid route {route.get('name')}: listen_port={lp} upstream_port={up}")
            continue
        if route.get("tls_upstream"):
            ctx = build_ssl_context(route)
            threading.Thread(
                target=tls_tcp_forward_worker,
                args=(lp, uh, up, ctx),
                daemon=True,
            ).start()
            log(f"Route {route['name']}: TLS 0.0.0.0:{lp} -> {uh}:{up}")
        else:
            threading.Thread(
                target=plain_tcp_forward_worker,
                args=(lp, uh, up),
                daemon=True,
            ).start()
            log(f"Route {route['name']}: TCP 0.0.0.0:{lp} -> {uh}:{up}")

    log("Admin system gateway ready")
    signal.pause() if hasattr(signal, "pause") else _idle_forever()


def _idle_forever() -> None:
    import time

    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
