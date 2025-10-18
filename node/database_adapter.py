# Path: node/database_adapter.py
# Database abstraction layer for handling motor/pymongo compatibility issues

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Union
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Try to import database dependencies
DATABASE_AVAILABLE = False
AsyncIOMotorDatabase = None
AsyncIOMotorCollection = None

try:
    from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
    DATABASE_AVAILABLE = True
    # logger.info("Motor database driver available")
except ImportError:
    try:
        import pymongo
        # logger.warning("Motor not available, pymongo present but not async")
    except ImportError:
        # logger.warning("No database drivers available - using mock database")
        pass


class DatabaseAdapter(ABC):
    """Abstract database adapter interface"""
    
    @abstractmethod
    def __getitem__(self, collection_name: str):
        pass


class CollectionAdapter(ABC):
    """Abstract collection adapter interface"""
    
    @abstractmethod
    async def find(self, filter_dict: Dict[str, Any] = None, **kwargs):
        pass
    
    @abstractmethod
    async def find_one(self, filter_dict: Dict[str, Any] = None, **kwargs):
        pass
    
    @abstractmethod
    async def insert_one(self, document: Dict[str, Any], **kwargs):
        pass
    
    @abstractmethod
    async def update_one(self, filter_dict: Dict[str, Any], update_dict: Dict[str, Any], **kwargs):
        pass
    
    @abstractmethod
    async def replace_one(self, filter_dict: Dict[str, Any], replacement: Dict[str, Any], **kwargs):
        pass
    
    @abstractmethod
    async def delete_one(self, filter_dict: Dict[str, Any], **kwargs):
        pass
    
    @abstractmethod
    async def delete_many(self, filter_dict: Dict[str, Any], **kwargs):
        pass
    
    @abstractmethod
    async def count_documents(self, filter_dict: Dict[str, Any] = None, **kwargs):
        pass
    
    @abstractmethod
    async def create_index(self, keys: Any, **kwargs):
        pass
    
    @abstractmethod
    def aggregate(self, pipeline: List[Dict[str, Any]], **kwargs):
        pass
    
    @abstractmethod
    async def distinct(self, key: str, filter_dict: Dict[str, Any] = None, **kwargs):
        pass


class MockCursor:
    """Mock cursor for testing without database"""
    
    def __init__(self, data: List[Dict[str, Any]] = None):
        self.data = data or []
        self._index = 0
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if self._index >= len(self.data):
            raise StopAsyncIteration
        result = self.data[self._index]
        self._index += 1
        return result
    
    def sort(self, *args, **kwargs):
        return self
    
    def limit(self, limit: int):
        self.data = self.data[:limit]
        return self


class MockResult:
    """Mock result for database operations"""
    
    def __init__(self, modified_count: int = 1, inserted_id: str = None):
        self.modified_count = modified_count
        self.inserted_id = inserted_id or "mock_id"
        self.acknowledged = True


class MockCollection(CollectionAdapter):
    """Mock collection for testing without database"""
    
    def __init__(self, name: str):
        self.name = name
        self._data: Dict[str, Dict[str, Any]] = {}
    
    def find(self, filter_dict: Dict[str, Any] = None, **kwargs):
        """Mock find operation - returns cursor directly (not async)"""
        if filter_dict is None:
            return MockCursor(list(self._data.values()))
        
        # Simple mock filtering
        results = []
        for doc in self._data.values():
            if self._matches_filter(doc, filter_dict):
                results.append(doc)
        
        return MockCursor(results)
    
    async def find_one(self, filter_dict: Dict[str, Any] = None, **kwargs):
        """Mock find_one operation"""
        if filter_dict is None and self._data:
            return list(self._data.values())[0]
        
        if filter_dict:
            for doc in self._data.values():
                if self._matches_filter(doc, filter_dict):
                    return doc
        
        return None
    
    async def insert_one(self, document: Dict[str, Any], **kwargs):
        """Mock insert_one operation"""
        doc_id = document.get("_id", f"mock_id_{len(self._data)}")
        document["_id"] = doc_id
        self._data[str(doc_id)] = document.copy()
        return MockResult(inserted_id=doc_id)
    
    async def update_one(self, filter_dict: Dict[str, Any], update_dict: Dict[str, Any], **kwargs):
        """Mock update_one operation"""
        for doc in self._data.values():
            if self._matches_filter(doc, filter_dict):
                if "$set" in update_dict:
                    doc.update(update_dict["$set"])
                return MockResult(modified_count=1)
        return MockResult(modified_count=0)
    
    async def replace_one(self, filter_dict: Dict[str, Any], replacement: Dict[str, Any], **kwargs):
        """Mock replace_one operation"""
        for doc_id, doc in self._data.items():
            if self._matches_filter(doc, filter_dict):
                self._data[doc_id] = replacement.copy()
                return MockResult(modified_count=1)
        
        # Handle upsert
        if kwargs.get("upsert", False):
            doc_id = replacement.get("_id", f"mock_id_{len(self._data)}")
            replacement["_id"] = doc_id
            self._data[str(doc_id)] = replacement.copy()
            return MockResult(modified_count=1)
        
        return MockResult(modified_count=0)
    
    async def delete_one(self, filter_dict: Dict[str, Any], **kwargs):
        """Mock delete_one operation"""
        for doc_id, doc in list(self._data.items()):
            if self._matches_filter(doc, filter_dict):
                del self._data[doc_id]
                return MockResult(modified_count=1)
        return MockResult(modified_count=0)
    
    async def delete_many(self, filter_dict: Dict[str, Any], **kwargs):
        """Mock delete_many operation"""
        deleted_count = 0
        for doc_id, doc in list(self._data.items()):
            if self._matches_filter(doc, filter_dict):
                del self._data[doc_id]
                deleted_count += 1
        return MockResult(modified_count=deleted_count)
    
    async def count_documents(self, filter_dict: Dict[str, Any] = None, **kwargs):
        """Mock count_documents operation"""
        if filter_dict is None:
            return len(self._data)
        
        count = 0
        for doc in self._data.values():
            if self._matches_filter(doc, filter_dict):
                count += 1
        return count
    
    async def create_index(self, keys: Any, **kwargs):
        """Mock create_index operation"""
        pass  # No-op for mock
    
    def aggregate(self, pipeline: List[Dict[str, Any]], **kwargs):
        """Mock aggregate operation"""
        return MockCursor([])  # Simplified mock
    
    async def distinct(self, key: str, filter_dict: Dict[str, Any] = None, **kwargs):
        """Mock distinct operation"""
        values = set()
        for doc in self._data.values():
            if filter_dict is None or self._matches_filter(doc, filter_dict):
                if key in doc:
                    values.add(doc[key])
        return list(values)
    
    def _matches_filter(self, document: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        """Simple filter matching for mock database"""
        if not filter_dict:
            return True
        
        for key, value in filter_dict.items():
            if key == "$or":
                # Handle $or operator
                if not any(self._matches_filter(document, condition) for condition in value):
                    return False
            elif key == "$in":
                # This shouldn't happen at top level, but handle gracefully
                continue
            elif isinstance(value, dict):
                # Handle operators like $gte, $lt, $in, etc.
                doc_value = document.get(key)
                if doc_value is None:
                    return False
                
                for op, op_value in value.items():
                    if op == "$gte" and doc_value < op_value:
                        return False
                    elif op == "$gt" and doc_value <= op_value:
                        return False
                    elif op == "$lte" and doc_value > op_value:
                        return False
                    elif op == "$lt" and doc_value >= op_value:
                        return False
                    elif op == "$ne" and doc_value == op_value:
                        return False
                    elif op == "$in" and doc_value not in op_value:
                        return False
                    elif op == "$nin" and doc_value in op_value:
                        return False
            else:
                # Simple equality check
                if document.get(key) != value:
                    return False
        
        return True


class MockDatabase(DatabaseAdapter):
    """Mock database for testing without database"""
    
    def __init__(self):
        self.collections: Dict[str, MockCollection] = {}
    
    def __getitem__(self, collection_name: str) -> MockCollection:
        if collection_name not in self.collections:
            self.collections[collection_name] = MockCollection(collection_name)
        return self.collections[collection_name]


class RealDatabaseAdapter(DatabaseAdapter):
    """Real database adapter using motor"""
    
    def __init__(self, motor_db: AsyncIOMotorDatabase):
        self.db = motor_db
    
    def __getitem__(self, collection_name: str):
        return self.db[collection_name]


def get_database_adapter(motor_db=None) -> DatabaseAdapter:
    """
    Get appropriate database adapter based on what's available.
    
    Args:
        motor_db: Optional motor database instance
        
    Returns:
        Database adapter (real or mock)
    """
    if motor_db is not None and DATABASE_AVAILABLE:
        # logger.info("Using real database adapter")
        return RealDatabaseAdapter(motor_db)
    else:
        # logger.info("Using mock database adapter")
        return MockDatabase()


# For backward compatibility, export the mock database class
MockAsyncIOMotorDatabase = MockDatabase