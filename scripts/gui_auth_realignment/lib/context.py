"""Repo root resolution for gui_auth_realignment steps."""

from __future__ import annotations

import argparse
from pathlib import Path


def default_repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def add_repo_root_arg(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Lucid repository root (default: inferred from this package)",
    )


def resolve_repo_root(ns: argparse.Namespace) -> Path:
    root = ns.repo_root or default_repo_root()
    return root.resolve()


def scripts_dir(repo: Path) -> Path:
    return repo / "scripts" / "gui_auth_realignment"
