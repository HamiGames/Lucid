# src/api/services/blockchain_service.py
# LUCID API Blockchain Service - On-System Data Chain Integration
# Updated to use On-System Data Chain as primary blockchain (not TRON)
# TRON is isolated for payments only per dual-chain architecture

from __future__ import annotations

import asyncio
import os
import logging
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# On-System Data Chain Configuration
ON_SYSTEM_CHAIN_RPC = os.getenv("ON_SYSTEM_CHAIN_RPC", "http://localhost:8545")
LUCID_ANCHORS_ADDRESS = os.getenv("LUCID_ANCHORS_ADDRESS", "")
LUCID_CHUNK_STORE_ADDRESS = os.getenv("LUCID_CHUNK_STORE_ADDRESS", "")

# TRON Payment Service Configuration (isolated)
TRON_NETWORK = os.getenv("TRON_NETWORK", "shasta")
USDT_TRC20_MAINNET = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
USDT_TRC20_SHASTA = "TG3XXyExBkPp9nzdajDZsozEu4BkaSJozs"


async def on_system_chain_health(timeout_s: float = 2.0) -> Dict[str, Any]:
    """
    Check On-System Data Chain health by making a simple RPC call.
    Returns health status and any error information.
    """
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout_s)) as session:
            # Simple RPC call to get latest block number
            payload = {
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            }
            
            async with session.post(
                ON_SYSTEM_CHAIN_RPC,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "chain_type": "on_system_data_chain",
                        "latest_block": data.get("result", "unknown"),
                        "rpc_url": ON_SYSTEM_CHAIN_RPC,
                        "contracts": {
                            "lucid_anchors": LUCID_ANCHORS_ADDRESS,
                            "lucid_chunk_store": LUCID_CHUNK_STORE_ADDRESS
                        },
                        "error": None,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "chain_type": "on_system_data_chain",
                        "latest_block": None,
                        "error": f"HTTP {response.status}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "chain_type": "on_system_data_chain",
            "latest_block": None,
            "error": f"Request timed out after {timeout_s}s",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "chain_type": "on_system_data_chain",
            "latest_block": None,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def tron_payment_health(timeout_s: float = 2.0) -> Dict[str, Any]:
    """
    Check TRON payment service health (isolated service only).
    Returns health status for USDT-TRC20 payment operations.
    """
    try:
        # Check TRON network connectivity
        tron_rpc_url = "https://api.trongrid.io" if TRON_NETWORK == "mainnet" else "https://api.shasta.trongrid.io"
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout_s)) as session:
            # Simple API call to check TRON network
            async with session.get(f"{tron_rpc_url}/wallet/getnowblock") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "service_type": "tron_payment_only",
                        "network": TRON_NETWORK,
                        "latest_block": data.get("block_header", {}).get("raw_data", {}).get("number", "unknown"),
                        "usdt_contract": USDT_TRC20_MAINNET if TRON_NETWORK == "mainnet" else USDT_TRC20_SHASTA,
                        "error": None,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "service_type": "tron_payment_only",
                        "network": TRON_NETWORK,
                        "latest_block": None,
                        "error": f"HTTP {response.status}",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "service_type": "tron_payment_only",
            "network": TRON_NETWORK,
            "latest_block": None,
            "error": f"Request timed out after {timeout_s}s",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "service_type": "tron_payment_only",
            "network": TRON_NETWORK,
            "latest_block": None,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def blockchain_system_health(timeout_s: float = 2.0) -> Dict[str, Any]:
    """
    Check overall blockchain system health including both On-System Chain and TRON payment service.
    Returns comprehensive health status for dual-chain architecture.
    """
    try:
        # Check both services in parallel
        on_chain_health_task = asyncio.create_task(on_system_chain_health(timeout_s))
        tron_health_task = asyncio.create_task(tron_payment_health(timeout_s))
        
        on_chain_health_result = await on_chain_health_task
        tron_health_result = await tron_health_task
        
        # Determine overall system health
        overall_status = "healthy"
        if on_chain_health_result["status"] != "healthy":
            overall_status = "degraded"
        if tron_health_result["status"] != "healthy":
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
    logger.warning("Using deprecated node_health() function. Use blockchain_system_health() for full status.")
    return await on_system_chain_health(timeout_s)
