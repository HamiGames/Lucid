"""
File: 03_api_gateway/api/app/services/gui_alignment.py
x-lucid-file-path: /app/03_api_gateway/api/app/services/gui_alignment.py
x-lucid-file-directory: /app/03_api_gateway/api/app/services
x-lucid-file-type: python

Load trusted GUI integration service identities from configs/alignment-mats/gui-services.json
(compose_service / lucid_service / container_name).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import FrozenSet, Optional, Tuple

try:
    from api.app.utils.logging import get_logger

    logger = get_logger()
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


def _resolve_alignment_file(explicit: Optional[str] = None) -> Path:
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return p
    env_path = os.getenv("GUI_SERVICES_ALIGNMENT_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_file():
            return p
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "configs" / "alignment-mats" / "gui-services.json"
        if cand.is_file():
            return cand
    return Path("configs/alignment-mats/gui-services.json")


@lru_cache(maxsize=4)
def _load_trusted_sets(config_path: str) -> Tuple[FrozenSet[str], FrozenSet[str]]:
    path = Path(config_path)
    if not path.is_file():
        logger.warning("GUI alignment file missing at %s — no trusted GUI callers", path)
        return frozenset(), frozenset()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.error("Failed to load GUI alignment %s: %s", path, e)
        return frozenset(), frozenset()

    services = data.get("services") or []
    by_lucid: set[str] = set()
    by_container: set[str] = set()
    for row in services:
        if not isinstance(row, dict):
            continue
        ls = row.get("lucid_service")
        cn = row.get("container_name")
        cs = row.get("compose_service")
        if isinstance(ls, str) and ls.strip():
            by_lucid.add(ls.strip())
        if isinstance(cn, str) and cn.strip():
            by_container.add(cn.strip())
        if isinstance(cs, str) and cs.strip():
            by_lucid.add(cs.strip())
    return frozenset(by_lucid), frozenset(by_container)


def trusted_gui_service_ids(config_path: Optional[str] = None) -> FrozenSet[str]:
    path = _resolve_alignment_file(config_path)
    lucid_ids, _ = _load_trusted_sets(str(path.resolve()))
    return lucid_ids


def is_trusted_gui_caller(
    calling_service: Optional[str],
    config_path: Optional[str] = None,
) -> bool:
    if not calling_service or not calling_service.strip():
        return False
    name = calling_service.strip()
    path = _resolve_alignment_file(config_path)
    lucid_ids, container_ids = _load_trusted_sets(str(path.resolve()))
    return name in lucid_ids or name in container_ids
