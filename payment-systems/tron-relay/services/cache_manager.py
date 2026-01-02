"""
LUCID TRON Relay - Cache Manager
Manages caching of TRON blockchain data for improved performance

SECURITY: Caches READ-ONLY data only - no sensitive information
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from cachetools import TTLCache
import json
import os

from config import config

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata"""
    key: str
    data: Any
    created_at: float
    ttl: int
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        return time.time() - self.created_at > self.ttl
    
    def size_bytes(self) -> int:
        """Estimate size in bytes"""
        try:
            return len(json.dumps(self.data).encode())
        except:
            return 0


class CacheManager:
    """
    Cache Manager for TRON Relay
    
    Provides tiered caching for different data types:
    - Blocks: Medium TTL (5 minutes)
    - Transactions: Long TTL (1 hour) - immutable once confirmed
    - Accounts: Short TTL (30 seconds) - balances change frequently
    """
    
    def __init__(self):
        self.initialized = False
        
        # Different caches for different data types with appropriate TTLs
        self._block_cache: Dict[str, CacheEntry] = {}
        self._transaction_cache: Dict[str, CacheEntry] = {}
        self._account_cache: Dict[str, CacheEntry] = {}
        self._generic_cache: Dict[str, CacheEntry] = {}
        
        # Stats
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "size_bytes": 0
        }
        
        # Cache limits
        self._max_entries_per_cache = 10000
        self._max_size_bytes = config.cache_max_size_mb * 1024 * 1024
        
        # Locks for thread safety
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the cache manager"""
        logger.info("Initializing cache manager")
        logger.info(f"Cache max size: {config.cache_max_size_mb} MB")
        logger.info(f"Block TTL: {config.cache_block_ttl}s")
        logger.info(f"Transaction TTL: {config.cache_transaction_ttl}s")
        logger.info(f"Account TTL: {config.cache_account_ttl}s")
        
        self.initialized = True
        logger.info("✅ Cache manager initialized")
    
    async def shutdown(self):
        """Shutdown the cache manager"""
        logger.info("Shutting down cache manager")
        await self.clear_all()
        self.initialized = False
    
    # ==========================================================================
    # BLOCK CACHE
    # ==========================================================================
    
    async def get_block(self, key: str) -> Optional[Dict[str, Any]]:
        """Get block from cache"""
        return await self._get_from_cache(self._block_cache, f"block:{key}")
    
    async def set_block(self, key: str, data: Dict[str, Any]):
        """Set block in cache"""
        await self._set_in_cache(
            self._block_cache,
            f"block:{key}",
            data,
            config.cache_block_ttl
        )
    
    # ==========================================================================
    # TRANSACTION CACHE
    # ==========================================================================
    
    async def get_transaction(self, txid: str) -> Optional[Dict[str, Any]]:
        """Get transaction from cache"""
        return await self._get_from_cache(self._transaction_cache, f"tx:{txid}")
    
    async def set_transaction(self, txid: str, data: Dict[str, Any]):
        """Set transaction in cache"""
        await self._set_in_cache(
            self._transaction_cache,
            f"tx:{txid}",
            data,
            config.cache_transaction_ttl
        )
    
    async def get_transaction_info(self, txid: str) -> Optional[Dict[str, Any]]:
        """Get transaction info from cache"""
        return await self._get_from_cache(self._transaction_cache, f"txinfo:{txid}")
    
    async def set_transaction_info(self, txid: str, data: Dict[str, Any]):
        """Set transaction info in cache"""
        await self._set_in_cache(
            self._transaction_cache,
            f"txinfo:{txid}",
            data,
            config.cache_transaction_ttl
        )
    
    # ==========================================================================
    # ACCOUNT CACHE
    # ==========================================================================
    
    async def get_account(self, address: str) -> Optional[Dict[str, Any]]:
        """Get account from cache"""
        return await self._get_from_cache(self._account_cache, f"account:{address}")
    
    async def set_account(self, address: str, data: Dict[str, Any]):
        """Set account in cache"""
        await self._set_in_cache(
            self._account_cache,
            f"account:{address}",
            data,
            config.cache_account_ttl
        )
    
    async def get_balance(self, address: str) -> Optional[Dict[str, Any]]:
        """Get balance from cache"""
        return await self._get_from_cache(self._account_cache, f"balance:{address}")
    
    async def set_balance(self, address: str, data: Dict[str, Any]):
        """Set balance in cache"""
        await self._set_in_cache(
            self._account_cache,
            f"balance:{address}",
            data,
            config.cache_account_ttl
        )
    
    # ==========================================================================
    # GENERIC CACHE
    # ==========================================================================
    
    async def get(self, key: str) -> Optional[Any]:
        """Get from generic cache"""
        return await self._get_from_cache(self._generic_cache, key)
    
    async def set(self, key: str, data: Any, ttl: Optional[int] = None):
        """Set in generic cache"""
        await self._set_in_cache(
            self._generic_cache,
            key,
            data,
            ttl or config.cache_ttl_seconds
        )
    
    # ==========================================================================
    # INTERNAL METHODS
    # ==========================================================================
    
    async def _get_from_cache(
        self,
        cache: Dict[str, CacheEntry],
        key: str
    ) -> Optional[Any]:
        """Get item from a cache"""
        async with self._lock:
            entry = cache.get(key)
            
            if entry is None:
                self._stats["misses"] += 1
                return None
            
            if entry.is_expired():
                del cache[key]
                self._stats["misses"] += 1
                self._stats["evictions"] += 1
                return None
            
            entry.access_count += 1
            entry.last_accessed = time.time()
            self._stats["hits"] += 1
            
            return entry.data
    
    async def _set_in_cache(
        self,
        cache: Dict[str, CacheEntry],
        key: str,
        data: Any,
        ttl: int
    ):
        """Set item in a cache"""
        async with self._lock:
            # Check cache limits
            if len(cache) >= self._max_entries_per_cache:
                await self._evict_oldest(cache)
            
            entry = CacheEntry(
                key=key,
                data=data,
                created_at=time.time(),
                ttl=ttl
            )
            
            cache[key] = entry
            self._stats["size_bytes"] = await self._calculate_total_size()
    
    async def _evict_oldest(self, cache: Dict[str, CacheEntry]):
        """Evict oldest entries from cache"""
        if not cache:
            return
        
        # Sort by last accessed time
        sorted_entries = sorted(
            cache.items(),
            key=lambda x: x[1].last_accessed
        )
        
        # Evict oldest 10%
        evict_count = max(1, len(sorted_entries) // 10)
        for i in range(evict_count):
            key = sorted_entries[i][0]
            del cache[key]
            self._stats["evictions"] += 1
    
    async def _calculate_total_size(self) -> int:
        """Calculate total cache size in bytes"""
        total = 0
        for cache in [self._block_cache, self._transaction_cache, 
                      self._account_cache, self._generic_cache]:
            for entry in cache.values():
                total += entry.size_bytes()
        return total
    
    # ==========================================================================
    # MAINTENANCE
    # ==========================================================================
    
    async def cleanup_expired(self) -> int:
        """Clean up expired entries"""
        cleaned = 0
        async with self._lock:
            for cache in [self._block_cache, self._transaction_cache,
                          self._account_cache, self._generic_cache]:
                expired_keys = [
                    k for k, v in cache.items() if v.is_expired()
                ]
                for key in expired_keys:
                    del cache[key]
                    cleaned += 1
                    self._stats["evictions"] += 1
        
        return cleaned
    
    async def clear_all(self):
        """Clear all caches"""
        async with self._lock:
            self._block_cache.clear()
            self._transaction_cache.clear()
            self._account_cache.clear()
            self._generic_cache.clear()
            self._stats["size_bytes"] = 0
    
    async def get_cache_size(self) -> int:
        """Get current cache size in bytes"""
        return await self._calculate_total_size()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = (
            len(self._block_cache) +
            len(self._transaction_cache) +
            len(self._account_cache) +
            len(self._generic_cache)
        )
        
        hit_rate = 0
        total_requests = self._stats["hits"] + self._stats["misses"]
        if total_requests > 0:
            hit_rate = self._stats["hits"] / total_requests * 100
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate_percent": round(hit_rate, 2),
            "evictions": self._stats["evictions"],
            "total_entries": total_entries,
            "block_entries": len(self._block_cache),
            "transaction_entries": len(self._transaction_cache),
            "account_entries": len(self._account_cache),
            "generic_entries": len(self._generic_cache),
            "size_bytes": self._stats["size_bytes"],
            "max_size_bytes": self._max_size_bytes
        }


# Global cache manager instance
cache_manager = CacheManager()

