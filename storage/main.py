#!/usr/bin/env python3
"""
Lucid storage plane service — hardware-backed capacity, mount layout, and health.
Database organisation (indexes, sharding, query access) belongs in the database layer, not here.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

project_root = os.getenv("LUCID_PROJECT_ROOT", str(Path(__file__).parent.parent))
sys.path.insert(0, project_root)

from .plane import ensure_storage_plane, run_forever

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger.info("Starting Lucid storage plane (capacity / layout / utility)")

    try:
        ensure_storage_plane()
        logger.info("Storage plane initialized")
        await run_forever(float(os.getenv("LUCID_STORAGE_RECHECK_SECONDS", "60")))
    except Exception as e:
        logger.error("Storage plane error: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
