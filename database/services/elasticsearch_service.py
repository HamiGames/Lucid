"""
Elasticsearch Service for Lucid Database Infrastructure
Provides Elasticsearch operations, search functionality, and analytics.

This service implements the Elasticsearch operations layer for the Lucid blockchain system,
handling search indices, document indexing, full-text search, and analytics queries.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import (
    ConnectionError,
    TransportError,
    NotFoundError,
    RequestError,
    ConflictError
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ElasticsearchService:
    """
    Elasticsearch Service for Lucid Database Infrastructure
    
    Provides comprehensive Elasticsearch operations including:
    - Connection management
    - Index management and mapping
    - Document indexing and search
    - Full-text search capabilities
    - Analytics and aggregations
    - Health monitoring
    """
    
    def __init__(self, hosts: List[str], api_key: str = None, 
                 username: str = None, password: str = None):
        """
        Initialize Elasticsearch service
        
        Args:
            hosts: List of Elasticsearch host URLs
            api_key: API key for authentication
            username: Username for basic auth
            password: Password for basic auth
        """
        self.hosts = hosts
        self.api_key = api_key
        self.username = username
        self.password = password
        self.client: Optional[AsyncElasticsearch] = None
        self.index_prefix = "lucid"
        
    async def connect(self) -> bool:
        """
        Establish connection to Elasticsearch
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Configure authentication
            auth_config = {}
            if self.api_key:
                auth_config["api_key"] = self.api_key
            elif self.username and self.password:
                auth_config["basic_auth"] = (self.username, self.password)
            
            # Create Elasticsearch client
            self.client = AsyncElasticsearch(
                hosts=self.hosts,
                **auth_config,
                verify_certs=True,
                ssl_show_warn=False,
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            # Test connection
            info = await self.client.info()
            logger.info(f"Successfully connected to Elasticsearch: {info['version']['number']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Elasticsearch: {e}")
            return False
    
    async def disconnect(self):
        """Close Elasticsearch connection"""
        if self.client:
            await self.client.close()
        logger.info("Elasticsearch connection closed")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        
        Returns:
            Dict containing health status and metrics
        """
        try:
            if not self.client:
                return {"status": "unhealthy", "error": "No connection"}
            
            # Get cluster health
            health = await self.client.cluster.health()
            
            # Get cluster stats
            stats = await self.client.cluster.stats()
            
            # Get node info
            nodes = await self.client.nodes.info()
            
            return {
                "status": health["status"],
                "timestamp": datetime.utcnow().isoformat(),
                "cluster": {
                    "name": health["cluster_name"],
                    "status": health["status"],
                    "number_of_nodes": health["number_of_nodes"],
                    "number_of_data_nodes": health["number_of_data_nodes"],
                    "active_primary_shards": health["active_primary_shards"],
                    "active_shards": health["active_shards"],
                    "relocating_shards": health["relocating_shards"],
                    "initializing_shards": health["initializing_shards"],
                    "unassigned_shards": health["unassigned_shards"]
                },
                "indices": {
                    "count": stats["indices"]["count"],
                    "docs": stats["indices"]["docs"],
                    "store": stats["indices"]["store"],
                    "fielddata": stats["indices"]["fielddata"],
                    "query_cache": stats["indices"]["query_cache"]
                },
                "nodes": {
                    "total": len(nodes["nodes"]),
                    "versions": list(set(node["version"] for node in nodes["nodes"].values()))
                }
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # Index Management
    async def create_index(self, index_name: str, mapping: Dict = None, 
                          settings: Dict = None) -> bool:
        """
        Create an index with mapping and settings
        
        Args:
            index_name: Name of the index to create
            mapping: Index mapping configuration
            settings: Index settings
            
        Returns:
            bool: True if successful
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_name}"
            
            body = {}
            if mapping:
                body["mappings"] = mapping
            if settings:
                body["settings"] = settings
            
            await self.client.indices.create(
                index=full_index_name,
                body=body if body else None
            )
            
            logger.info(f"Index created: {full_index_name}")
            return True
            
        except ConflictError:
            logger.warning(f"Index already exists: {full_index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            return False
    
    async def delete_index(self, index_name: str) -> bool:
        """
        Delete an index
        
        Args:
            index_name: Name of the index to delete
            
        Returns:
            bool: True if successful
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_name}"
            await self.client.indices.delete(index=full_index_name)
            logger.info(f"Index deleted: {full_index_name}")
            return True
            
        except NotFoundError:
            logger.warning(f"Index not found: {full_index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete index {index_name}: {e}")
            return False
    
    async def index_exists(self, index_name: str) -> bool:
        """
        Check if index exists
        
        Args:
            index_name: Name of the index to check
            
        Returns:
            bool: True if index exists
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_name}"
            return await self.client.indices.exists(index=full_index_name)
        except Exception as e:
            logger.error(f"Failed to check index existence {index_name}: {e}")
            return False
    
    async def get_index_mapping(self, index_name: str) -> Optional[Dict]:
        """
        Get index mapping
        
        Args:
            index_name: Name of the index
            
        Returns:
            Index mapping or None if not found
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_name}"
            mapping = await self.client.indices.get_mapping(index=full_index_name)
            return mapping[full_index_name]["mappings"]
        except Exception as e:
            logger.error(f"Failed to get mapping for index {index_name}: {e}")
            return None
    
    async def update_index_mapping(self, index_name: str, mapping: Dict) -> bool:
        """
        Update index mapping
        
        Args:
            index_name: Name of the index
            mapping: New mapping properties
            
        Returns:
            bool: True if successful
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_name}"
            await self.client.indices.put_mapping(
                index=full_index_name,
                body=mapping
            )
            logger.info(f"Mapping updated for index: {full_index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to update mapping for index {index_name}: {e}")
            return False
    
    # Document Operations
    async def index_document(self, index_name: str, document: Dict, 
                           doc_id: str = None) -> Optional[str]:
        """
        Index a document
        
        Args:
            index_name: Target index name
            document: Document to index
            doc_id: Document ID (auto-generated if None)
            
        Returns:
            Document ID if successful, None otherwise
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_name}"
            
            # Add timestamp if not present
            if "timestamp" not in document:
                document["timestamp"] = datetime.utcnow().isoformat()
            
            response = await self.client.index(
                index=full_index_name,
                body=document,
                id=doc_id
            )
            
            logger.debug(f"Document indexed in {full_index_name}: {response['_id']}")
            return response["_id"]
            
        except Exception as e:
            logger.error(f"Failed to index document in {index_name}: {e}")
            return None
    
    async def get_document(self, index_name: str, doc_id: str) -> Optional[Dict]:
        """
        Get a document by ID
        
        Args:
            index_name: Source index name
            doc_id: Document ID
            
        Returns:
            Document data or None if not found
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_name}"
            response = await self.client.get(
                index=full_index_name,
                id=doc_id
            )
            return response["_source"]
            
        except NotFoundError:
            logger.debug(f"Document not found: {doc_id} in {index_name}")
            return None
        except Exception as e:
            logger.error(f"Failed to get document {doc_id} from {index_name}: {e}")
            return None
    
    async def update_document(self, index_name: str, doc_id: str, 
                            update_data: Dict) -> bool:
        """
        Update a document
        
        Args:
            index_name: Target index name
            doc_id: Document ID
            update_data: Data to update
            
        Returns:
            bool: True if successful
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_name}"
            
            # Add update timestamp
            update_data["updated_at"] = datetime.utcnow().isoformat()
            
            await self.client.update(
                index=full_index_name,
                id=doc_id,
                body={"doc": update_data}
            )
            
            logger.debug(f"Document updated in {full_index_name}: {doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document {doc_id} in {index_name}: {e}")
            return False
    
    async def delete_document(self, index_name: str, doc_id: str) -> bool:
        """
        Delete a document
        
        Args:
            index_name: Target index name
            doc_id: Document ID
            
        Returns:
            bool: True if successful
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_name}"
            await self.client.delete(
                index=full_index_name,
                id=doc_id
            )
            
            logger.debug(f"Document deleted from {full_index_name}: {doc_id}")
            return True
            
        except NotFoundError:
            logger.warning(f"Document not found for deletion: {doc_id} in {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id} from {index_name}: {e}")
            return False
    
    async def bulk_index_documents(self, index_name: str, 
                                 documents: List[Dict]) -> Dict[str, int]:
        """
        Bulk index multiple documents
        
        Args:
            index_name: Target index name
            documents: List of documents to index
            
        Returns:
            Dict with success/failure counts
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_name}"
            
            # Prepare bulk operations
            operations = []
            for doc in documents:
                # Add timestamp if not present
                if "timestamp" not in doc:
                    doc["timestamp"] = datetime.utcnow().isoformat()
                
                operations.append({
                    "_index": full_index_name,
                    "_source": doc
                })
            
            response = await self.client.bulk(
                operations=operations,
                refresh=True
            )
            
            # Count successes and failures
            success_count = 0
            failure_count = 0
            
            for item in response["items"]:
                if "index" in item:
                    if item["index"]["status"] in [200, 201]:
                        success_count += 1
                    else:
                        failure_count += 1
            
            logger.info(f"Bulk indexed {success_count} documents, {failure_count} failures")
            
            return {
                "success": success_count,
                "failures": failure_count,
                "total": len(documents)
            }
            
        except Exception as e:
            logger.error(f"Failed to bulk index documents in {index_name}: {e}")
            return {"success": 0, "failures": len(documents), "total": len(documents)}
    
    # Search Operations
    async def search(self, index_name: str, query: Dict, size: int = 10, 
                    from_: int = 0, sort: List = None) -> Dict[str, Any]:
        """
        Search documents
        
        Args:
            index_name: Index to search
            query: Elasticsearch query
            size: Number of results to return
            from_: Starting offset
            sort: Sort specification
            
        Returns:
            Search results
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_name}"
            
            search_body = {
                "query": query,
                "size": size,
                "from": from_
            }
            
            if sort:
                search_body["sort"] = sort
            
            response = await self.client.search(
                index=full_index_name,
                body=search_body
            )
            
            return {
                "total": response["hits"]["total"]["value"],
                "max_score": response["hits"]["max_score"],
                "hits": [hit["_source"] for hit in response["hits"]["hits"]],
                "took": response["took"]
            }
            
        except Exception as e:
            logger.error(f"Failed to search in {index_name}: {e}")
            return {"total": 0, "hits": [], "took": 0}
    
    async def full_text_search(self, index_name: str, query_text: str, 
                             fields: List[str] = None, size: int = 10) -> Dict[str, Any]:
        """
        Perform full-text search
        
        Args:
            index_name: Index to search
            query_text: Text to search for
            fields: Fields to search in (all if None)
            size: Number of results
            
        Returns:
            Search results
        """
        try:
            if fields:
                query = {
                    "multi_match": {
                        "query": query_text,
                        "fields": fields,
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                }
            else:
                query = {
                    "query_string": {
                        "query": query_text,
                        "default_operator": "AND",
                        "fuzziness": "AUTO"
                    }
                }
            
            return await self.search(index_name, query, size)
            
        except Exception as e:
            logger.error(f"Failed to perform full-text search in {index_name}: {e}")
            return {"total": 0, "hits": [], "took": 0}
    
    async def aggregate(self, index_name: str, aggregations: Dict, 
                       query: Dict = None) -> Dict[str, Any]:
        """
        Perform aggregations
        
        Args:
            index_name: Index to aggregate
            aggregations: Aggregation specification
            query: Optional query to filter documents
            
        Returns:
            Aggregation results
        """
        try:
            full_index_name = f"{self.index_prefix}-{index_name}"
            
            search_body = {
                "size": 0,  # Don't return documents, only aggregations
                "aggs": aggregations
            }
            
            if query:
                search_body["query"] = query
            
            response = await self.client.search(
                index=full_index_name,
                body=search_body
            )
            
            return {
                "aggregations": response.get("aggregations", {}),
                "took": response["took"]
            }
            
        except Exception as e:
            logger.error(f"Failed to perform aggregation in {index_name}: {e}")
            return {"aggregations": {}, "took": 0}
    
    # Lucid-specific search operations
    async def search_sessions(self, user_id: str = None, status: str = None, 
                            date_from: datetime = None, date_to: datetime = None,
                            size: int = 10) -> Dict[str, Any]:
        """
        Search sessions with Lucid-specific filters
        
        Args:
            user_id: Filter by user ID
            status: Filter by session status
            date_from: Start date filter
            date_to: End date filter
            size: Number of results
            
        Returns:
            Search results
        """
        try:
            must_clauses = []
            
            if user_id:
                must_clauses.append({"term": {"owner_address": user_id}})
            
            if status:
                must_clauses.append({"term": {"status": status}})
            
            if date_from or date_to:
                date_range = {}
                if date_from:
                    date_range["gte"] = date_from.isoformat()
                if date_to:
                    date_range["lte"] = date_to.isoformat()
                
                must_clauses.append({
                    "range": {"started_at": date_range}
                })
            
            query = {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}]
                }
            }
            
            return await self.search("sessions", query, size, sort=[{"started_at": {"order": "desc"}}])
            
        except Exception as e:
            logger.error(f"Failed to search sessions: {e}")
            return {"total": 0, "hits": [], "took": 0}
    
    async def search_blocks(self, height_from: int = None, height_to: int = None,
                          miner_id: str = None, size: int = 10) -> Dict[str, Any]:
        """
        Search blockchain blocks
        
        Args:
            height_from: Minimum block height
            height_to: Maximum block height
            miner_id: Filter by miner ID
            size: Number of results
            
        Returns:
            Search results
        """
        try:
            must_clauses = []
            
            if height_from is not None or height_to is not None:
                height_range = {}
                if height_from is not None:
                    height_range["gte"] = height_from
                if height_to is not None:
                    height_range["lte"] = height_to
                
                must_clauses.append({
                    "range": {"block_height": height_range}
                })
            
            if miner_id:
                must_clauses.append({"term": {"miner_id": miner_id}})
            
            query = {
                "bool": {
                    "must": must_clauses if must_clauses else [{"match_all": {}}]
                }
            }
            
            return await self.search("blocks", query, size, sort=[{"block_height": {"order": "desc"}}])
            
        except Exception as e:
            logger.error(f"Failed to search blocks: {e}")
            return {"total": 0, "hits": [], "took": 0}
    
    # Index Templates for Lucid
    async def create_lucid_index_templates(self) -> bool:
        """
        Create index templates for Lucid data types
        
        Returns:
            bool: True if successful
        """
        try:
            # Sessions index template
            sessions_template = {
                "index_patterns": [f"{self.index_prefix}-sessions*"],
                "template": {
                    "settings": {
                        "number_of_shards": 2,
                        "number_of_replicas": 1,
                        "refresh_interval": "5s"
                    },
                    "mappings": {
                        "properties": {
                            "session_id": {"type": "keyword"},
                            "owner_address": {"type": "keyword"},
                            "status": {"type": "keyword"},
                            "started_at": {"type": "date"},
                            "completed_at": {"type": "date"},
                            "merkle_root": {"type": "keyword"},
                            "anchor_txid": {"type": "keyword"},
                            "chunks": {
                                "type": "nested",
                                "properties": {
                                    "chunk_id": {"type": "keyword"},
                                    "index": {"type": "integer"},
                                    "size_bytes": {"type": "long"},
                                    "hash_blake3": {"type": "keyword"}
                                }
                            },
                            "metadata": {
                                "properties": {
                                    "original_size": {"type": "long"},
                                    "compressed_size": {"type": "long"},
                                    "compression_ratio": {"type": "float"}
                                }
                            }
                        }
                    }
                }
            }
            
            await self.client.indices.put_index_template(
                name=f"{self.index_prefix}-sessions-template",
                body=sessions_template
            )
            
            # Blocks index template
            blocks_template = {
                "index_patterns": [f"{self.index_prefix}-blocks*"],
                "template": {
                    "settings": {
                        "number_of_shards": 1,
                        "number_of_replicas": 1
                    },
                    "mappings": {
                        "properties": {
                            "block_height": {"type": "long"},
                            "block_hash": {"type": "keyword"},
                            "previous_hash": {"type": "keyword"},
                            "merkle_root": {"type": "keyword"},
                            "timestamp": {"type": "date"},
                            "miner_id": {"type": "keyword"},
                            "transactions": {
                                "type": "nested",
                                "properties": {
                                    "tx_id": {"type": "keyword"},
                                    "tx_type": {"type": "keyword"},
                                    "sender": {"type": "keyword"}
                                }
                            }
                        }
                    }
                }
            }
            
            await self.client.indices.put_index_template(
                name=f"{self.index_prefix}-blocks-template",
                body=blocks_template
            )
            
            logger.info("Lucid index templates created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index templates: {e}")
            return False

# Global Elasticsearch service instance
elasticsearch_service = None

async def get_elasticsearch_service(hosts: List[str], api_key: str = None,
                                  username: str = None, password: str = None) -> ElasticsearchService:
    """
    Get or create Elasticsearch service instance
    
    Args:
        hosts: List of Elasticsearch host URLs
        api_key: API key for authentication
        username: Username for basic auth
        password: Password for basic auth
        
    Returns:
        ElasticsearchService instance
    """
    global elasticsearch_service
    
    if elasticsearch_service is None:
        elasticsearch_service = ElasticsearchService(hosts, api_key, username, password)
        await elasticsearch_service.connect()
    
    return elasticsearch_service

async def close_elasticsearch_service():
    """Close the global Elasticsearch service"""
    global elasticsearch_service
    if elasticsearch_service:
        await elasticsearch_service.disconnect()
        elasticsearch_service = None
