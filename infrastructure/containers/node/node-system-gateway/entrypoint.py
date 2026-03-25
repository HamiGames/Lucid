#!/usr/bin/env python3
"""
Lucid node system gateway — HTTP reverse proxy (node plane → api-gateway, admin-system-gateway).
Config: NODE_SYSTEM_GATEWAY_CONFIG (default /app/node/config/node-system-gateway.connections.json).
TLS policy: NODE_SYSTEM_GATEWAY_OPENSSL_API_YAML (default /app/node/config/openssl-api.yml).
Env overrides per route: NODE_GATEWAY_UPSTREAM_<NAME>_HOST, NODE_GATEWAY_UPSTREAM_<NAME>_PORT
(NAME derived from route name: non-alnum → underscore, uppercased).
"""
from __future__ import annotations

import json
import os
import re
import signal
import ssl
import sys
from http.client import HTTPConnection, HTTPSConnection, HTTPException, ResponseNotReady
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore

LOG = "[node-system-gateway]"


def log(msg: str) -> None:
    print(f"{LOG} {msg}", flush=True)


def _route_env_key(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name.upper()).strip("_")


def load_config(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        log(f"FATAL: config not found: {path}")
        sys.exit(1)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        log("FATAL: config root must be an object")
        sys.exit(1)
    return data


def load_openssl_api(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        log(f"openssl-api yaml missing: {path} (using empty TLS policy)")
        return {}
    if yaml is None:
        log("WARNING: PyYAML not installed; openssl-api.yml ignored")
        return {}
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    return data if isinstance(data, dict) else {}


def build_ssl_context(route: Dict[str, Any], openssl_api: Dict[str, Any]) -> ssl.SSLContext:
    defaults = openssl_api.get("tls_client_defaults") or {}
    profiles = openssl_api.get("tls_profiles") or {}
    profile_name = route.get("tls_profile")
    prof = profiles.get(profile_name, {}) if profile_name else {}
    merged: Dict[str, Any] = {**defaults, **prof}

    cafile = os.getenv("NODE_SYSTEM_GATEWAY_SSL_CA_FILE") or merged.get("cafile") or None
    certfile = os.getenv("NODE_SYSTEM_GATEWAY_SSL_CERT_FILE") or merged.get("certfile") or None
    keyfile = os.getenv("NODE_SYSTEM_GATEWAY_SSL_KEY_FILE") or merged.get("keyfile") or None
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

    ciphers = openssl_api.get("ciphers") or ""
    if isinstance(ciphers, str) and ciphers.strip():
        ctx.set_ciphers(ciphers)

    if certfile and keyfile:
        ctx.load_cert_chain(certfile, keyfile)

    return ctx


def merge_routes(doc: Dict[str, Any], env: os._Environ) -> Tuple[str, int, List[Dict[str, Any]]]:
    bind = str(doc.get("listen_bind") or env.get("NODE_SYSTEM_GATEWAY_BIND", "0.0.0.0"))
    port = int(doc.get("listen_port") or env.get("NODE_SYSTEM_GATEWAY_LISTEN_PORT", "8640"))
    raw = doc.get("routes")
    if not isinstance(raw, list):
        log("FATAL: config.routes must be an array")
        sys.exit(1)
    out: List[Dict[str, Any]] = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        name = str(r.get("name", "route"))
        key = _route_env_key(name)
        host = str(r.get("upstream_host", "127.0.0.1"))
        port_u = int(r.get("upstream_port", 0))
        eh = env.get(f"NODE_GATEWAY_UPSTREAM_{key}_HOST")
        ep = env.get(f"NODE_GATEWAY_UPSTREAM_{key}_PORT")
        if eh:
            host = eh.strip()
        if ep:
            port_u = int(ep.strip())
        prefix = str(r.get("path_prefix", "/"))
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        strip = bool(r.get("strip_prefix", False))
        tls = bool(r.get("tls_upstream", False))
        tls_env = os.getenv(f"NODE_GATEWAY_UPSTREAM_{key}_TLS")
        if tls_env is not None:
            tls = tls_env.strip().lower() in ("1", "true", "yes", "on")
        tls_profile = r.get("tls_profile")
        out.append(
            {
                "name": name,
                "path_prefix": prefix.rstrip("/") or "/",
                "upstream_host": host,
                "upstream_port": port_u,
                "strip_prefix": strip,
                "tls_upstream": tls,
                "tls_profile": tls_profile,
            }
        )
    out.sort(key=lambda x: len(x["path_prefix"]), reverse=True)
    return bind, port, out


def match_route(
    path: str, routes: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    for r in routes:
        pfx = r["path_prefix"]
        if pfx == "/":
            return r
        if path == pfx or path.startswith(pfx + "/"):
            return r
    return None


def forward_path(path: str, route: Dict[str, Any]) -> str:
    pfx = route["path_prefix"]
    if not route["strip_prefix"]:
        return path
    if pfx == "/":
        return path
    if path == pfx:
        return "/"
    return path[len(pfx) :] or "/"


HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
}


def filter_headers(items: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    return [(k, v) for k, v in items if k.lower() not in HOP_BY_HOP]


def make_handler_class(routes: List[Dict[str, Any]], openssl_api: Dict[str, Any]):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: Any) -> None:
            pass

        def do_GET(self) -> None:
            self._handle()

        def do_HEAD(self) -> None:
            self._handle()

        def do_POST(self) -> None:
            self._handle()

        def do_PUT(self) -> None:
            self._handle()

        def do_PATCH(self) -> None:
            self._handle()

        def do_DELETE(self) -> None:
            self._handle()

        def do_OPTIONS(self) -> None:
            self._handle()

        def _local_health(self) -> None:
            body = json.dumps(
                {
                    "service": "node-system-gateway",
                    "ok": True,
                    "routes": [r["name"] for r in routes],
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _handle(self) -> None:
            parsed = urlparse(self.path)
            path_only = parsed.path or "/"
            if path_only in ("/health", "/health/"):
                self._local_health()
                return

            route = match_route(path_only, routes)
            if route is None:
                self.send_error(502, "no upstream route for path")
                return

            up_host = route["upstream_host"]
            up_port = int(route["upstream_port"])
            if up_port <= 0:
                self.send_error(502, "invalid upstream port")
                return

            tgt_path = forward_path(path_only, route)
            if parsed.query:
                tgt_path = f"{tgt_path}?{parsed.query}"

            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length > 0 else None

            fwd_headers = filter_headers(list(self.headers.items()))
            hdrs = {k: v for k, v in fwd_headers if k.lower() != "host"}
            hdrs["Host"] = (
                up_host
                if (route.get("tls_upstream") and up_port == 443)
                or (not route.get("tls_upstream") and up_port == 80)
                else f"{up_host}:{up_port}"
            )
            try:
                if route.get("tls_upstream"):
                    ctx = build_ssl_context(route, openssl_api)
                    conn = HTTPSConnection(
                        up_host, up_port, context=ctx, timeout=120
                    )
                else:
                    conn = HTTPConnection(up_host, up_port, timeout=120)
                conn.request(
                    self.command,
                    tgt_path,
                    body=body,
                    headers=hdrs,
                )
                resp = conn.getresponse()
                data = resp.read()
                self.send_response(resp.status)
                for hk, hv in resp.getheaders():
                    if hk.lower() in HOP_BY_HOP:
                        continue
                    self.send_header(hk, hv)
                if "Content-Length" not in {h[0].lower() for h in resp.getheaders()}:
                    self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(data)
                conn.close()
            except (OSError, HTTPException, ResponseNotReady) as exc:
                log(f"upstream error {up_host}:{up_port} {tgt_path}: {exc}")
                self.send_error(502, f"upstream error: {exc}")

    return H


def _shutdown(_sig: int, _frame: Any) -> None:
    sys.exit(0)


def main() -> None:
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    env = os.environ
    cfg_path = Path(
        env.get(
            "NODE_SYSTEM_GATEWAY_CONFIG",
            "/app/node/config/node-system-gateway.connections.json",
        )
    )
    yaml_path = Path(
        env.get(
            "NODE_SYSTEM_GATEWAY_OPENSSL_API_YAML",
            "/app/node/config/openssl-api.yml",
        )
    )
    doc = load_config(cfg_path)
    openssl_api = load_openssl_api(yaml_path)
    bind, port, routes = merge_routes(doc, env)
    if not routes:
        log("FATAL: no routes in config")
        sys.exit(1)

    handler = make_handler_class(routes, openssl_api)
    srv = ThreadingHTTPServer((bind, port), handler)
    log(f"listening http://{bind}:{port}/ (health /health; proxy routes loaded)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
