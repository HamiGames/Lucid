#!/usr/bin/env python3
"""
Lucid Tunnel Tools entrypoint — manages ephemeral onions through pickme/lucid-tor-proxy.
Assumes:
  * `/var/lib/tor/control_auth_cookie` is mounted from the tor-proxy container
  * The tunnel container can reach the tor ControlPort (default tor-proxy:9051)
  * Environment variables mirror the compose stack
"""

import os
import sys
import time
import socket
import binascii
from pathlib import Path
from typing import List, Tuple

CONTROL_HOST = os.getenv("CONTROL_HOST", "tor-proxy")
CONTROL_PORT = int(os.getenv("CONTROL_PORT", "9051"))
COOKIE_FILE = Path(os.getenv("COOKIE_FILE", "/var/lib/tor/control_auth_cookie"))
ONION_PORTS = os.getenv("ONION_PORTS", "80 lucid_api:8081")
WRITE_ENV = Path(os.getenv("WRITE_ENV", "/app/scripts/.onion.env"))
ROTATE_INTERVAL = int(os.getenv("ROTATE_INTERVAL", "0"))  # minutes; 0 = create once

LOG_PREFIX = "[tunnel-tools]"


def log(msg: str) -> None:
    print(f"{LOG_PREFIX} {msg}", flush=True)


def die(msg: str) -> None:
    log(f"ERROR: {msg}")
    sys.exit(1)


def wait_for_file(path: Path, timeout: int = 120) -> None:
    log(f"Waiting for {path} (timeout {timeout}s)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if path.exists() and path.stat().st_size > 0:
            log(f"Found {path}")
            return
        time.sleep(1)
    die(f"File not present: {path}")


def read_cookie_hex(path: Path) -> str:
    try:
        data = path.read_bytes()
        return binascii.hexlify(data).decode()
    except Exception as exc:
        die(f"Unable to read control cookie {path}: {exc}")


def send_control_commands(commands: List[str]) -> List[str]:
    """
    Send commands to Tor ControlPort and return response lines.
    """
    try:
        with socket.create_connection((CONTROL_HOST, CONTROL_PORT), timeout=5) as sock:
            for cmd in commands:
                sock.sendall(cmd.encode("utf-8") + b"\r\n")
            sock.sendall(b"QUIT\r\n")
            sock.shutdown(socket.SHUT_WR)

            data = sock.recv(65535)
            lines = data.decode("utf-8", errors="ignore").splitlines()
            return lines
    except OSError as exc:
        die(f"ControlPort connection failed: {exc}")


def authenticate(cookie_hex: str) -> None:
    lines = send_control_commands([f"AUTHENTICATE {cookie_hex}", "GETINFO version"])
    if not any(line.startswith("250 OK") for line in lines):
        die(f"Tor control authentication failed: {lines}")
    log("Authenticated with Tor ControlPort")


def parse_onion_ports(spec: str) -> List[Tuple[int, str]]:
    """
    Accepts strings like "80 lucid_api:8081, 443 gateway:8443".
    Returns list of (virtual_port, target_host:port).
    """
    pairs = []
    for chunk in spec.replace(",", " ").split():
        if ":" in chunk:
            # treat as HOST:PORT; use default virtual port 80
            pairs.append((80, chunk))
        else:
            # expect pattern: <virt_port> <host:port>
            continue  # handled by next iteration
    tokens = spec.replace(",", " ").split()
    i = 0
    results = []
    while i < len(tokens):
        tok = tokens[i]
        if tok.isdigit() and i + 1 < len(tokens):
            results.append((int(tok), tokens[i + 1]))
            i += 2
        else:
            i += 1
    return results or pairs


def create_onion(cookie_hex: str) -> str:
    port_mappings = parse_onion_ports(ONION_PORTS)
    if not port_mappings:
        die(f"No valid ONION_PORTS definition: {ONION_PORTS}")

    add_onion_cmd = "ADD_ONION NEW:ED25519-V3"
    for virt, backend in port_mappings:
        add_onion_cmd += f" Port={virt},{backend}"

    lines = send_control_commands([f"AUTHENTICATE {cookie_hex}", add_onion_cmd])
    for line in lines:
        if line.startswith("250-ServiceID="):
            onion = line.split("=", 1)[1].strip() + ".onion"
            log(f"Created onion: {onion}")
            WRITE_ENV.parent.mkdir(parents=True, exist_ok=True)
            WRITE_ENV.write_text(f"ONION={onion}\n")
            return onion

    die(f"ADD_ONION failed: {lines}")
    return ""


def main() -> None:
    log("Starting Lucid Tunnel Tools entrypoint")
    wait_for_file(COOKIE_FILE, timeout=120)
    cookie_hex = read_cookie_hex(COOKIE_FILE)
    authenticate(cookie_hex)

    def run_once():
        try:
            create_onion(cookie_hex)
        except Exception as exc:
            log(f"Onion creation failed: {exc}")

    run_once()
    if ROTATE_INTERVAL <= 0:
        log("ROTATE_INTERVAL=0; sleeping indefinitely")
        while True:
            time.sleep(3600)
    else:
        log(f"Rotation enabled every {ROTATE_INTERVAL} minute(s)")
        while True:
            time.sleep(ROTATE_INTERVAL * 60)
            run_once()

if __name__ == "__main__":
    main()