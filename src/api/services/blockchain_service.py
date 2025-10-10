# src/api/services/blockchain_service.py
from __future__ import annotations

import asyncio
import aiohttp
from typing import Dict, Any


async def node_health(timeout_s: float = 2.0) -> dict:
    """
    Check blockchain node health by making a simple RPC call.
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
                "http://localhost:8545",  # Default blockchain RPC port
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "latest_block": data.get("result", "unknown"),
                        "error": None
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "latest_block": None,
                        "error": f"HTTP {response.status}"
                    }
                    
    except asyncio.TimeoutError:
        return {
            "status": "timeout",
            "latest_block": None,
            "error": f"Request timed out after {timeout_s}s"
        }
    except Exception as e:
        return {
            "status": "error",
            "latest_block": None,
            "error": str(e)
        }
