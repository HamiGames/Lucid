# Path: storage/plane.py
"""
File: /app/storage/plane.py
x-lucid-file-path: /app/storage/plane.py
x-lucid-file-type: python

Lucid storage plane: bind to mounted capacity, layout, and free-space health (not database logic).
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def _free_bytes(path: Path) -> int:
    if hasattr(os, "statvfs"):
        stv = os.statvfs(path)
        return int(stv.f_bavail * stv.f_frsize)
    return int(shutil.disk_usage(path).free)


def _roots() -> list[Path]:
    raw = os.getenv("LUCID_STORAGE_ROOTS", os.getenv("LUCID_STORAGE_ROOT", "/var/lib/lucid/storage"))
    return [Path(p.strip()) for p in raw.split(",") if p.strip()]


def _min_free_mib() -> int:
    try:
        return max(16, int(os.getenv("LUCID_STORAGE_MIN_FREE_MIB", "128")))
    except ValueError:
        return 128


def _layout_subdirs() -> list[str]:
    raw = os.getenv(
        "LUCID_STORAGE_LAYOUT_SUBDIRS",
        "mongo,redis,elasticsearch,shared",
    )
    return [s.strip() for s in raw.split(",") if s.strip()]


def ensure_storage_plane() -> None:
    """Verify roots exist (or create), are writable, and meet minimum free capacity."""
    roots = _roots()
    if not roots:
        raise RuntimeError("LUCID_STORAGE_ROOT(S) resolved empty")

    min_free = _min_free_mib() * 1024 * 1024
    subdirs = _layout_subdirs()

    for root in roots:
        root.mkdir(parents=True, exist_ok=True)
        if not os.access(root, os.W_OK):
            raise PermissionError(f"storage root not writable: {root}")

        for name in subdirs:
            p = root / name
            p.mkdir(parents=True, exist_ok=True)
            probe = p / ".lucid-storage-probe"
            probe.write_text("ok\n", encoding="utf-8")
            probe.unlink(missing_ok=True)

        free = _free_bytes(root)
        if free < min_free:
            raise OSError(
                f"insufficient free space under {root}: {free // (1024 * 1024)} MiB "
                f"(need >= {_min_free_mib()} MiB)"
            )
        logger.info(
            "storage plane OK root=%s free_mib=%s",
            root,
            free // (1024 * 1024),
        )


def healthcheck() -> None:
    """Lightweight import + free-space re-check for distroless HEALTHCHECK."""
    ensure_storage_plane()
    sys.stdout.write("storage-plane-ok\n")


async def run_forever(interval_s: float = 60.0) -> None:
    ensure_storage_plane()
    while True:
        await asyncio.sleep(interval_s)
        ensure_storage_plane()
