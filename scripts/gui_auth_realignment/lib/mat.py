"""Load gui-services mat JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def load_gui_mat(repo: Path) -> Dict[str, Any]:
    path = repo / "configs" / "alignment-mats" / "gui-services.json"
    return json.loads(path.read_text(encoding="utf-8"))


def mat_services(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    services = data.get("services")
    if not isinstance(services, list):
        return []
    return [s for s in services if isinstance(s, dict)]
