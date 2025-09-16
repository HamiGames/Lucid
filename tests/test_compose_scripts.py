from __future__ import annotations

from pathlib import Path


def test_compose_file_exists():
    # Avoid indexing Path.parents to keep Pylance happy; walk up explicitly
    this_file = Path(__file__).resolve()
    root = this_file.parent.parent  # tests/ -> repo root
    compose = root / "06-orchestration-runtime" / "compose" / "lucid-dev.yaml"
    assert compose.exists(), f"Missing compose file: {compose}"
