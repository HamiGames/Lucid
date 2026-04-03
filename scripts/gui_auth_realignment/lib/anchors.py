"""Load ports.txt (line scan) and host-config.yml (YAML)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore


def load_host_config(repo: Path) -> Dict[str, Any]:
    path = repo / "infrastructure" / "containers" / "host-config.yml"
    if yaml is None:
        raise RuntimeError("PyYAML required: pip install pyyaml")
    raw = path.read_text(encoding="utf-8")
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
    text = path.read_text(encoding="utf-8", errors="replace")
    return bool(re.search(rf"\b{port}\b", text))
