# Path: 03-api-gateway/api/app/utils/config.py
# Lightweight env config loader (keeps deps minimal).

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    mongo_uri: str
    mongo_db: str
    api_key: str
    api_key_header: str
    block_rpc_url: str


def load_config() -> Config:
    return Config(
        mongo_uri=os.getenv("MONGO_URI", "mongodb://localhost:27017"),
        mongo_db=os.getenv("MONGO_DB", "lucid"),
        api_key=os.getenv("API_KEY", ""),
        api_key_header=os.getenv("API_KEY_HEADER", "X-API-Key"),
        block_rpc_url=os.getenv("BLOCK_RPC_URL", ""),
    )
