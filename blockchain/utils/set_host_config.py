"""
File: /app/blockchain/utils/set_host_config.py
x-lucid-file-path: /app/blockchain/utils/set_host_config.py
x-lucid-file-type: python

Derive blockchain runtime targets from Lucid host-config.
Read-only alignment with /app/configs/host-config.yml (repository:
infrastructure/containers/host-config.yml). Does not rewrite host-config.
Optional blockchain-config.yaml via LUCID_BLOCKCHAIN_CONFIG.
"""



from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

from common.load_host_config import (
    ServiceEndpoint,
    default_host_config_path,
    endpoint_by_service_name,
    load_host_registry,
    load_yaml_file,
    merge_config_layers,
)
try: 
    from blockchain.config.yaml_loader import load_yaml_config
except ImportError:  # pragma: no cover
    load_yaml_config = None  # type: ignore

ENV_BLOCKCHAIN_CONFIG = "LUCID_BLOCKCHAIN_CONFIG"
DEFAULT_BLOCKCHAIN_CONFIG = Path("/app/config/blockchain-config.yaml")


def resolve_blockchain_config_path() -> Optional[Path]:
    env = os.environ.get(ENV_BLOCKCHAIN_CONFIG, "").strip()
    if env:
        p = Path(env)
        return p if p.is_file() else None
    if DEFAULT_BLOCKCHAIN_CONFIG.is_file():
        return DEFAULT_BLOCKCHAIN_CONFIG
    repo = Path(__file__).resolve().parents[2]
    for name in ("blockchain-config.yaml", "blockchain-config.yml"):
        cand = repo / "blockchain" / "config" / name
        if cand.is_file():
            return cand
    return None


def load_blockchain_yaml_layer() -> Mapping[str, Any]:
    path = resolve_blockchain_config_path()
    if not path:
        return {}
    if load_yaml_config is not None:
        try:
            return load_yaml_config(str(path)) or {}
        except Exception:
            pass
    return load_yaml_file(path)


def load_blockchain_host_context(
    host_config_path: Optional[Path | str] = None,
) -> Tuple[Mapping[str, Any], Dict[str, ServiceEndpoint], Mapping[str, Any]]:
    raw, registry = load_host_registry(host_config_path or default_host_config_path())
    chain_layer = load_blockchain_yaml_layer()
    return raw, registry, chain_layer


def set_blockchain_host_config_view(
    host_config_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """
    Return a merged view: host metadata, service snapshots for chain-related
    DNS names, optional blockchain YAML, and quick resolver URLs.
    """
    raw, registry, chain_layer = load_blockchain_host_context(host_config_path)
    snap = {k: {"service_name": v.service_name, "port": v.port, "host_ip": v.host_ip} for k, v in registry.items()}

    def _url(service_name: str) -> Optional[str]:
        ep = endpoint_by_service_name(registry, service_name)
        return ep.base_url() if ep else None

    chain_urls = {
        "blockchain_engine": _url("blockchain-engine"),
        "blockchain_consensus_engine": _url("blockchain-consensus-engine"),
        "block_manager": _url("block-manager"),
        "data_chain": _url("data-chain"),
        "api_gateway": _url("api-gateway"),
    }
    return merge_config_layers(
        {k: v for k, v in raw.items() if k != "services"},
        {
            "services": snap,
            "blockchain_config": chain_layer,
            "blockchain_urls": chain_urls,
        },
    )


def apply_blockchain_service_env(registry: Dict[str, ServiceEndpoint]) -> None:
    """
    Optionally export common URL parts into the environment (no-op if env keys
    already set). Flexibility: callers choose whether to invoke this.
    """
    pairs = (
        ("LUCID_BLOCKCHAIN_ENGINE_URL", endpoint_by_service_name(registry, "blockchain-engine")),
        ("LUCID_BLOCK_MANAGER_URL", endpoint_by_service_name(registry, "block-manager")),
        ("LUCID_DATA_CHAIN_URL", endpoint_by_service_name(registry, "data-chain")),
    )
    for key, ep in pairs:
        if ep and not os.environ.get(key):
            os.environ[key] = ep.base_url()
