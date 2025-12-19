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
from typing import List, Tuple, Optional

# Import tunnel modules (handle import errors gracefully)
try:
    from tunnel_metrics import get_metrics
    from tunnel_status import get_status
    METRICS_AVAILABLE = True
    STATUS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    STATUS_AVAILABLE = False

CONTROL_HOST = os.getenv("CONTROL_HOST", "tor-proxy")
CONTROL_PORT = int(os.getenv("CONTROL_PORT", "9051"))
COOKIE_FILE = Path(os.getenv("COOKIE_FILE", "/var/lib/tor/control_auth_cookie"))
ONION_PORTS = os.getenv("ONION_PORTS", "80 api-gateway:8080")
WRITE_ENV = Path(os.getenv("WRITE_ENV", "/run/lucid/onion/.onion.env"))
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
        with socket.create_connection((CONTROL_HOST, CONTROL_PORT), timeout=10) as sock:
            response_data = b""
            
            # Send all commands
            for cmd in commands:
                sock.sendall(cmd.encode("utf-8") + b"\r\n")
            
            # Send QUIT and close write side
            sock.sendall(b"QUIT\r\n")
            sock.shutdown(socket.SHUT_WR)

            # Read all response data (may need multiple recv calls)
            while True:
                chunk = sock.recv(65535)
                if not chunk:
                    break
                response_data += chunk
                # Stop if we've received a reasonable amount of data
                if len(response_data) > 1024 * 1024:  # 1MB limit
                    break
            
            lines = response_data.decode("utf-8", errors="ignore").splitlines()
            return lines
    except socket.timeout:
        die(f"ControlPort connection timeout to {CONTROL_HOST}:{CONTROL_PORT}")
    except socket.gaierror as exc:
        die(f"ControlPort hostname resolution failed for {CONTROL_HOST}: {exc}")
    except OSError as exc:
        die(f"ControlPort connection failed to {CONTROL_HOST}:{CONTROL_PORT}: {exc}")


def authenticate(cookie_hex: str) -> None:
    lines = send_control_commands([f"AUTHENTICATE {cookie_hex}", "GETINFO version"])
    if not any(line.startswith("250 OK") for line in lines):
        die(f"Tor control authentication failed: {lines}")
    log("Authenticated with Tor ControlPort")


def parse_onion_ports(spec: str) -> List[Tuple[int, str]]:
    """
    Accepts strings like "80 api-gateway:8080, 443 api-gateway:8443".
    Returns list of (virtual_port, target_host:port).
    
    Format: "VIRTUAL_PORT TARGET_HOST:PORT" pairs, comma or space separated.
    Example: "80 api-gateway:8080" or "80 api-gateway:8080, 443 api-gateway:8443"
    """
    # Normalize separators: replace commas with spaces
    tokens = spec.replace(",", " ").split()
    
    if not tokens:
        return []
    
    results = []
    i = 0
    
    while i < len(tokens):
        # Check if current token is a digit (virtual port)
        if tokens[i].isdigit():
            virt_port = int(tokens[i])
            # Next token should be HOST:PORT
            if i + 1 < len(tokens) and ":" in tokens[i + 1]:
                target = tokens[i + 1]
                results.append((virt_port, target))
                i += 2
            else:
                # Invalid format: digit not followed by HOST:PORT
                i += 1
        elif ":" in tokens[i]:
            # Standalone HOST:PORT without virtual port, default to 80
            results.append((80, tokens[i]))
            i += 1
        else:
            # Skip invalid tokens
            i += 1
    
    return results


def create_onion(cookie_hex: str, old_onion: Optional[str] = None) -> str:
    port_mappings = parse_onion_ports(ONION_PORTS)
    if not port_mappings:
        die(f"No valid ONION_PORTS definition: {ONION_PORTS}")

    add_onion_cmd = "ADD_ONION NEW:ED25519-V3"
    port_list = []
    for virt, backend in port_mappings:
        # Validate backend format (should be HOST:PORT)
        if ":" not in backend:
            die(f"Invalid backend format (expected HOST:PORT): {backend}")
        add_onion_cmd += f" Port={virt},{backend}"
        port_list.append({"virtual_port": virt, "target": backend})

    lines = send_control_commands([f"AUTHENTICATE {cookie_hex}", add_onion_cmd])
    
    # Check for authentication success
    auth_ok = False
    onion_id = None
    
    for line in lines:
        if line.startswith("250 OK"):
            auth_ok = True
        elif line.startswith("250-ServiceID="):
            onion_id = line.split("=", 1)[1].strip()
    
    if not auth_ok:
        # Record error in metrics if available
        if METRICS_AVAILABLE:
            try:
                metrics = get_metrics()
                metrics.record_error("authentication_failed", "Tor control authentication failed")
            except Exception:
                pass
        die(f"Tor control authentication failed: {lines}")
    
    if not onion_id:
        # Record error in metrics if available
        if METRICS_AVAILABLE:
            try:
                metrics = get_metrics()
                metrics.record_error("onion_creation_failed", "No ServiceID in response")
            except Exception:
                pass
        die(f"ADD_ONION failed - no ServiceID in response: {lines}")
    
    onion = onion_id + ".onion"
    log(f"Created onion: {onion}")
    
    # Update status and metrics
    if STATUS_AVAILABLE:
        try:
            status = get_status()
            status.set_onion_address(onion, port_list)
            status.set_status("active")
            status.set_health("healthy")
            status.set_tor_authenticated(True)
        except Exception as e:
            log(f"WARNING: Failed to update status: {e}")
    
    if METRICS_AVAILABLE:
        try:
            metrics = get_metrics()
            if old_onion:
                metrics.record_onion_rotation(old_onion, onion)
            else:
                metrics.record_onion_creation(onion)
        except Exception as e:
            log(f"WARNING: Failed to update metrics: {e}")
    
    # Write onion address to file
    try:
        WRITE_ENV.parent.mkdir(parents=True, exist_ok=True)
        WRITE_ENV.write_text(f"ONION={onion}\n")
        log(f"Wrote onion address to {WRITE_ENV}")
    except (OSError, PermissionError) as exc:
        log(f"WARNING: Failed to write onion address to {WRITE_ENV}: {exc}")
        log(f"Onion address: {onion} (please save manually)")
    
    return onion


def main() -> None:
    log("Starting Lucid Tunnel Tools entrypoint")
    log(f"Configuration: CONTROL_HOST={CONTROL_HOST}, CONTROL_PORT={CONTROL_PORT}")
    log(f"Onion ports: {ONION_PORTS}")
    log(f"Write env: {WRITE_ENV}")
    
    # Initialize status and metrics if available
    if STATUS_AVAILABLE:
        try:
            status = get_status()
            status.set_status("initializing")
            status.check_tor_connection()
            log("Status module initialized")
        except Exception as e:
            log(f"WARNING: Failed to initialize status module: {e}")
    
    if METRICS_AVAILABLE:
        try:
            metrics = get_metrics()
            log("Metrics module initialized")
        except Exception as e:
            log(f"WARNING: Failed to initialize metrics module: {e}")
    
    # Wait for cookie file to be available
    wait_for_file(COOKIE_FILE, timeout=120)
    cookie_hex = read_cookie_hex(COOKIE_FILE)
    
    # Authenticate with Tor control port
    authenticate(cookie_hex)
    
    # Update status after authentication
    if STATUS_AVAILABLE:
        try:
            status = get_status()
            status.set_tor_authenticated(True)
            status.set_status("ready")
        except Exception:
            pass

    current_onion: Optional[str] = None
    
    def run_once():
        nonlocal current_onion
        try:
            onion = create_onion(cookie_hex, current_onion)
            if onion:
                log(f"Onion service active: {onion}")
                current_onion = onion
        except Exception as exc:
            log(f"Onion creation failed: {exc}")
            # Record error in metrics if available
            if METRICS_AVAILABLE:
                try:
                    metrics = get_metrics()
                    metrics.record_error("onion_creation_exception", str(exc))
                except Exception:
                    pass
            # Update status to error
            if STATUS_AVAILABLE:
                try:
                    status = get_status()
                    status.set_status("error")
                    status.set_health("unhealthy")
                except Exception:
                    pass
            # Don't exit on error, allow retry on next rotation
            import traceback
            log(f"Traceback: {traceback.format_exc()}")

    # Create initial onion
    run_once()
    
    # Handle rotation
    if ROTATE_INTERVAL <= 0:
        log("ROTATE_INTERVAL=0; sleeping indefinitely (no rotation)")
        while True:
            time.sleep(3600)
    else:
        log(f"Rotation enabled every {ROTATE_INTERVAL} minute(s)")
        while True:
            time.sleep(ROTATE_INTERVAL * 60)
            log("Rotating onion service...")
            run_once()

if __name__ == "__main__":
    main()