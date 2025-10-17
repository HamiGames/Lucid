"""
Lucid Service Mesh - DNS Resolver
DNS resolution for service discovery.

File: infrastructure/service-mesh/discovery/dns_resolver.py
Lines: ~200
Purpose: DNS resolution
Dependencies: asyncio, aiodns
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import aiodns

logger = logging.getLogger(__name__)


class DNSResolver:
    """
    DNS resolver for service discovery.
    
    Handles:
    - Service name resolution
    - Load balancing
    - Caching
    - Health checking
    """
    
    def __init__(self):
        self.resolver = aiodns.DNSResolver()
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl = 300  # 5 minutes
        self.service_domains = {
            "api-gateway": "api-gateway.lucid.internal",
            "blockchain-core": "blockchain-core.lucid.internal",
            "session-management": "session-management.lucid.internal",
            "node-management": "node-management.lucid.internal",
            "auth-service": "auth-service.lucid.internal",
            "consul": "consul.lucid.internal"
        }
        
    async def initialize(self):
        """Initialize DNS resolver."""
        try:
            logger.info("Initializing DNS Resolver...")
            
            # Test DNS resolution
            await self._test_dns_resolution()
            
            logger.info("DNS Resolver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize DNS Resolver: {e}")
            raise
            
    async def _test_dns_resolution(self):
        """Test DNS resolution capability."""
        try:
            # Try to resolve a common domain
            await self.resolver.query("google.com", "A")
            logger.info("DNS resolution test successful")
            
        except Exception as e:
            logger.warning(f"DNS resolution test failed: {e}")
            
    async def resolve_service(
        self,
        service_name: str,
        record_type: str = "A"
    ) -> List[Dict[str, Any]]:
        """
        Resolve service name to IP addresses.
        
        Args:
            service_name: Service name to resolve
            record_type: DNS record type (A, AAAA, SRV)
            
        Returns:
            List of resolved addresses
        """
        try:
            # Check cache first
            cache_key = f"{service_name}:{record_type}"
            if cache_key in self.cache:
                cached_result = self.cache[cache_key]
                if self._is_cache_valid(cached_result):
                    logger.debug(f"Using cached result for {service_name}")
                    return cached_result["addresses"]
                    
            # Get domain name for service
            domain = self.service_domains.get(service_name, f"{service_name}.lucid.internal")
            
            # Resolve DNS
            if record_type == "A":
                addresses = await self._resolve_a_record(domain)
            elif record_type == "AAAA":
                addresses = await self._resolve_aaaa_record(domain)
            elif record_type == "SRV":
                addresses = await self._resolve_srv_record(domain)
            else:
                logger.error(f"Unsupported record type: {record_type}")
                return []
                
            # Cache result
            self.cache[cache_key] = {
                "addresses": addresses,
                "timestamp": datetime.utcnow().timestamp()
            }
            
            logger.debug(f"Resolved {service_name} to {len(addresses)} addresses")
            return addresses
            
        except Exception as e:
            logger.error(f"Failed to resolve service {service_name}: {e}")
            return []
            
    async def _resolve_a_record(self, domain: str) -> List[Dict[str, Any]]:
        """Resolve A record (IPv4)."""
        try:
            result = await self.resolver.query(domain, "A")
            addresses = []
            
            for record in result:
                addresses.append({
                    "type": "A",
                    "address": record.host,
                    "ttl": getattr(record, 'ttl', 300)
                })
                
            return addresses
            
        except Exception as e:
            logger.error(f"Failed to resolve A record for {domain}: {e}")
            return []
            
    async def _resolve_aaaa_record(self, domain: str) -> List[Dict[str, Any]]:
        """Resolve AAAA record (IPv6)."""
        try:
            result = await self.resolver.query(domain, "AAAA")
            addresses = []
            
            for record in result:
                addresses.append({
                    "type": "AAAA",
                    "address": record.host,
                    "ttl": getattr(record, 'ttl', 300)
                })
                
            return addresses
            
        except Exception as e:
            logger.error(f"Failed to resolve AAAA record for {domain}: {e}")
            return []
            
    async def _resolve_srv_record(self, domain: str) -> List[Dict[str, Any]]:
        """Resolve SRV record."""
        try:
            result = await self.resolver.query(domain, "SRV")
            addresses = []
            
            for record in result:
                addresses.append({
                    "type": "SRV",
                    "host": record.host,
                    "port": record.port,
                    "priority": record.priority,
                    "weight": record.weight,
                    "ttl": getattr(record, 'ttl', 300)
                })
                
            return addresses
            
        except Exception as e:
            logger.error(f"Failed to resolve SRV record for {domain}: {e}")
            return []
            
    def _is_cache_valid(self, cached_result: Dict[str, Any]) -> bool:
        """Check if cached result is still valid."""
        timestamp = cached_result.get("timestamp", 0)
        current_time = datetime.utcnow().timestamp()
        return (current_time - timestamp) < self.cache_ttl
        
    async def resolve_service_with_port(
        self,
        service_name: str,
        default_port: int = 80
    ) -> List[Tuple[str, int]]:
        """
        Resolve service to host:port pairs.
        
        Args:
            service_name: Service name
            default_port: Default port if not specified in SRV record
            
        Returns:
            List of (host, port) tuples
        """
        try:
            # Try SRV record first
            srv_records = await self.resolve_service(service_name, "SRV")
            if srv_records:
                return [(record["host"], record["port"]) for record in srv_records]
                
            # Fall back to A record with default port
            a_records = await self.resolve_service(service_name, "A")
            return [(record["address"], default_port) for record in a_records]
            
        except Exception as e:
            logger.error(f"Failed to resolve service with port {service_name}: {e}")
            return []
            
    async def resolve_service_round_robin(
        self,
        service_name: str,
        default_port: int = 80
    ) -> Optional[Tuple[str, int]]:
        """
        Resolve service using round-robin load balancing.
        
        Args:
            service_name: Service name
            default_port: Default port
            
        Returns:
            (host, port) tuple or None
        """
        try:
            addresses = await self.resolve_service_with_port(service_name, default_port)
            
            if not addresses:
                return None
                
            # Simple round-robin (could be improved with proper load balancing)
            import random
            return random.choice(addresses)
            
        except Exception as e:
            logger.error(f"Failed to resolve service round-robin {service_name}: {e}")
            return None
            
    def add_service_domain(self, service_name: str, domain: str):
        """Add a service domain mapping."""
        self.service_domains[service_name] = domain
        
    def remove_service_domain(self, service_name: str):
        """Remove a service domain mapping."""
        if service_name in self.service_domains:
            del self.service_domains[service_name]
            
    def clear_cache(self):
        """Clear DNS cache."""
        self.cache.clear()
        logger.info("DNS cache cleared")
        
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.cache)
        valid_entries = sum(
            1 for entry in self.cache.values()
            if self._is_cache_valid(entry)
        )
        
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": total_entries - valid_entries,
            "cache_ttl": self.cache_ttl
        }
        
    def get_status(self) -> Dict[str, Any]:
        """Get DNS resolver status."""
        return {
            "service_domains": len(self.service_domains),
            "cache_stats": self.get_cache_stats(),
            "last_update": datetime.utcnow().isoformat()
        }
