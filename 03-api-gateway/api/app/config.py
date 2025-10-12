from functools import lru_cache
from pydantic import BaseModel
import os


class Settings(BaseModel):
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "lucid-api")
    VERSION: str = os.getenv("VERSION", "0.1.0")
    LUCID_ENV: str = os.getenv("LUCID_ENV", "dev")
    
    # MongoDB
    MONGO_URL: str = os.getenv("LUCID_MONGODB_URL", "mongodb://localhost:27017/lucid")
    
    # Tor
    TOR_SOCKS_PROXY: str = os.getenv("LUCID_TOR_SOCKS_URL", "socks5://localhost:9050")
    TOR_CONTROL_PORT: int = int(os.getenv("LUCID_TOR_CONTROL_PORT", "9051"))
    ONION_ADDRESS: str = os.getenv("LUCID_API_ONION_ADDRESS", "")
    
    # Blockchain (On-System Chain)
    BLOCKCHAIN_RPC_URL: str = os.getenv("LUCID_BLOCKCHAIN_RPC_URL", "http://lucid-blockchain:8545")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
