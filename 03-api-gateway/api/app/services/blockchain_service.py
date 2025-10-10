# Path: 03-api-gateway/api/app/services/blockchain_service.py
# LUCID API Gateway Blockchain Service - On-System Data Chain Integration
# Updated to use On-System Data Chain as primary blockchain (not TRON)
# TRON is isolated for payments only per dual-chain architecture

import os
import httpx
from datetime import datetime, timezone
from typing import Dict, Any
from ..utils.logger import get_logger

log = get_logger(__name__)

# On-System Data Chain Configuration (Primary Blockchain)
ON_SYSTEM_CHAIN_RPC = os.getenv("ON_SYSTEM_CHAIN_RPC", "http://localhost:8545")
LUCID_ANCHORS_ADDRESS = os.getenv("LUCID_ANCHORS_ADDRESS", "")
LUCID_CHUNK_STORE_ADDRESS = os.getenv("LUCID_CHUNK_STORE_ADDRESS", "")

# TRON Payment Service Configuration (Isolated)
TRON_NETWORK = os.getenv("TRON_NETWORK", "shasta")
USDT_TRC20_MAINNET = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
USDT_TRC20_SHASTA = "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs"

# Legacy configuration (deprecated)
BLOCK_RPC_URL = ON_SYSTEM_CHAIN_RPC


async def on_system_chain_health(timeout_s: float = 2.0) -> Dict[str, Any]:
    """Check On-System Data Chain health"""
    if not ON_SYSTEM_CHAIN_RPC:
        return {"status": "disabled", "reason": "ON_SYSTEM_CHAIN_RPC not set"}
    
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            # JSON-RPC call to get latest block number
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            }
            
            resp = await client.post(
                ON_SYSTEM_CHAIN_RPC,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "ok",
                    "chain_type": "on_system_data_chain",
                    "latest_block": data.get("result", "unknown"),
                    "rpc_url": ON_SYSTEM_CHAIN_RPC,
                    "contracts": {
                        "lucid_anchors": LUCID_ANCHORS_ADDRESS,
                        "lucid_chunk_store": LUCID_CHUNK_STORE_ADDRESS
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    "status": "degraded",
                    "chain_type": "on_system_data_chain",
                    "error": f"HTTP {resp.status_code}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
    except Exception as e:
        log.warning("on_system_chain_unreachable", extra={"error": str(e)})
        return {
            "status": "degraded",
            "chain_type": "on_system_data_chain",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def tron_payment_health(timeout_s: float = 2.0) -> Dict[str, Any]:
    """Check TRON payment service health (isolated service only)"""
    try:
        tron_rpc_url = "https://api.trongrid.io" if TRON_NETWORK == "mainnet" else "https://api.shasta.trongrid.io"
        
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            # Simple API call to check TRON network
            resp = await client.get(f"{tron_rpc_url}/wallet/getnowblock")
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "status": "ok",
                    "service_type": "tron_payment_only",
                    "network": TRON_NETWORK,
                    "latest_block": data.get("block_header", {}).get("raw_data", {}).get("number", "unknown"),
                    "usdt_contract": USDT_TRC20_MAINNET if TRON_NETWORK == "mainnet" else USDT_TRC20_SHASTA,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {
                    "status": "degraded",
                    "service_type": "tron_payment_only",
                    "network": TRON_NETWORK,
                    "error": f"HTTP {resp.status_code}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
    except Exception as e:
        log.warning("tron_payment_unreachable", extra={"error": str(e)})
        return {
            "status": "degraded",
            "service_type": "tron_payment_only",
            "network": TRON_NETWORK,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def blockchain_system_health(timeout_s: float = 2.0) -> Dict[str, Any]:
    """Check overall blockchain system health including both On-System Chain and TRON payment service"""
    try:
        import asyncio
        
        # Check both services in parallel
        on_chain_health_task = asyncio.create_task(on_system_chain_health(timeout_s))
        tron_health_task = asyncio.create_task(tron_payment_health(timeout_s))
        
        on_chain_health_result = await on_chain_health_task
        tron_health_result = await tron_health_task
        
        # Determine overall system health
        overall_status = "ok"
        if on_chain_health_result["status"] != "ok":
            overall_status = "degraded"
        if tron_health_result["status"] != "ok":
            overall_status = "degraded"
        
        return {
            "status": overall_status,
            "architecture": "dual_chain",
            "services": {
                "on_system_chain": on_chain_health_result,
                "tron_payment": tron_health_result
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        log.error("blockchain_system_health_failed", extra={"error": str(e)})
        return {
            "status": "error",
            "architecture": "dual_chain",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Legacy compatibility - redirects to On-System Chain health check
async def node_health(timeout_s: float = 2.0) -> Dict[str, Any]:
    """
    Legacy compatibility function - now checks On-System Data Chain health.
    Use blockchain_system_health() for comprehensive dual-chain status.
    """
    log.warning("Using deprecated node_health() function. Use blockchain_system_health() for full status.")
    return await on_system_chain_health(timeout_s)
