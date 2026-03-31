"""
File: /app/common/contact_profile_env.py
x-lucid-file-path: /app/common/contact_profile_env.py
x-lucid-file-directory: /app/common
x-lucid-file-type: python

Merge per-contact-profile secret overlays with base .env-style files.
Correlates with user documents: users.contact_profile_key and profile.metadata.contact_profile_key.

Base file: ${LUCID_SECRETS_BASE_PATH}/.env.secrets (or /.env.secrets in container)
Overlay:    ${LUCID_SECRETS_BASE_PATH}/profiles/<profile_key>/.env.secrets
Optional:  ${LUCID_SECRETS_OVERLAY_PATH} (single file, wins last)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Optional

ENV_CONTACT_PROFILE_KEY = "LUCID_CONTACT_PROFILE_KEY"
ENV_SECRETS_BASE_PATH = "LUCID_SECRETS_BASE_PATH"
ENV_SECRETS_OVERLAY_PATH = "LUCID_SECRETS_OVERLAY_PATH"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_secrets_base_path() -> Path:
    env = os.environ.get(ENV_SECRETS_BASE_PATH, "").strip()
    if env:
        return Path(env)
    for cand in (
        Path("/app/configs/environment"),
        _repo_root() / "configs" / "environment",
    ):
        if cand.is_dir():
            return cand
    return _repo_root() / "configs" / "environment"


def parse_dotenv_lines(text: str) -> Dict[str, str]:
    """Parse KEY=VAL lines (no multiline values). Ignores comments and blank lines."""
    out: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, rest = line.partition("=")
        key = key.strip()
        val = rest.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        if key:
            out[key] = val
    return out


def load_dotenv_file(path: Path) -> Dict[str, str]:
    if not path.is_file():
        return {}
    try:
        return parse_dotenv_lines(path.read_text(encoding="utf-8"))
    except OSError:
        return {}


def resolve_contact_profile_key(
    explicit: Optional[str] = None,
    user_doc: Optional[Mapping[str, Any]] = None,
) -> Optional[str]:
    """
    Priority: explicit arg > LUCID_CONTACT_PROFILE_KEY env >
    user_doc.contact_profile_key > user_doc.profile.metadata.contact_profile_key
    """
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    env = os.environ.get(ENV_CONTACT_PROFILE_KEY, "").strip()
    if env:
        return env
    if not user_doc:
        return None
    top = user_doc.get("contact_profile_key")
    if top:
        return str(top).strip() or None
    prof = user_doc.get("profile")
    if isinstance(prof, dict):
        meta = prof.get("metadata")
        if isinstance(meta, dict) and meta.get("contact_profile_key"):
            return str(meta["contact_profile_key"]).strip() or None
        if prof.get("contact_profile_key"):
            return str(prof["contact_profile_key"]).strip() or None
    return None


def collect_secret_layers(
    profile_key: Optional[str] = None,
    base_path: Optional[Path] = None,
) -> list[tuple[str, Dict[str, str]]]:
    """Ordered list of (label, mapping) for merge; later layers override earlier."""
    base = base_path or default_secrets_base_path()
    layers: list[tuple[str, Dict[str, str]]] = []

    main = base / ".env.secrets"
    layers.append(("base:.env.secrets", load_dotenv_file(main)))

    pk = (profile_key or "").strip()
    if pk:
        overlay = base / "profiles" / pk / ".env.secrets"
        layers.append((f"profile:{pk}", load_dotenv_file(overlay)))

    extra = os.environ.get(ENV_SECRETS_OVERLAY_PATH, "").strip()
    if extra:
        p = Path(extra)
        layers.append((f"overlay:{p}", load_dotenv_file(p)))

    return layers


def merge_secret_layers(layers: list[tuple[str, Dict[str, str]]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for _label, m in layers:
        for k, v in m.items():
            out[k] = v
    return out


def merged_secrets_for_profile(
    profile_key: Optional[str] = None,
    base_path: Optional[Path] = None,
) -> Dict[str, str]:
    return merge_secret_layers(collect_secret_layers(profile_key, base_path))


def apply_secrets_to_environ(
    secrets: Mapping[str, str],
    *,
    overwrite: bool = False,
    keys_only: Optional[set[str]] = None,
) -> None:
    """Apply mapping to os.environ; if overwrite is False, only set missing keys."""
    for k, v in secrets.items():
        if keys_only is not None and k not in keys_only:
            continue
        if overwrite or k not in os.environ:
            os.environ[k] = v


def bootstrap_contact_profile_env(
    profile_key: Optional[str] = None,
    *,
    user_doc: Optional[Mapping[str, Any]] = None,
    overwrite: bool = False,
    base_path: Optional[Path] = None,
) -> Dict[str, str]:
    """
    Resolve profile from args/user_doc/env, merge secret files, apply to os.environ.
    Call once at process startup for services that need profile-scoped credentials.
    """
    pk = resolve_contact_profile_key(profile_key, user_doc)
    merged = merged_secrets_for_profile(pk, base_path)
    apply_secrets_to_environ(merged, overwrite=overwrite)
    return merged
