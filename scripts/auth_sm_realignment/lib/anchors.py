"""Load ports.txt and host-config.yml for auth ↔ server-manager alignment steps."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore


def _read_text_maybe_utf16(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    return raw.decode("utf-8", errors="replace")


def load_host_config(repo: Path) -> Dict[str, Any]:
    path = repo / "infrastructure" / "containers" / "host-config.yml"
    if yaml is None:
        raise RuntimeError("PyYAML required: pip install pyyaml")
    raw = _read_text_maybe_utf16(path)
    data = yaml.safe_load(raw)
    if not isinstance(data, dict) or "services" not in data:
        raise ValueError("host-config.yml missing services map")
    return data


def service_port(host_config: Dict[str, Any], service_id: str) -> Optional[int]:
    services = host_config.get("services") or {}
    block = services.get(service_id)
    if not isinstance(block, dict):
        return None
    p = block.get("port")
    return int(p) if p is not None and int(p) > 0 else None


def ports_txt_has_port(repo: Path, port: int) -> bool:
    path = repo / "ports.txt"
    if not path.is_file():
        return False
    text = _read_text_maybe_utf16(path)
    # Port as number, not substring of larger int (e.g. 18089)
    return bool(re.search(rf"(?:^|[^\d]){port}(?:[^\d]|$)", text))
