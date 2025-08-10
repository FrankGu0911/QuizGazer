#!/usr/bin/env python3
"""
Cache Manager for Knowledge Base RAG System

This module provides caching functionality to improve performance:
- Embedding caching for frequently accessed content
- Query result caching
- Document metadata caching
- Connection pooling for API calls
"""

import time
import hashlib
import pickle
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from collections import OrderedDict
import logging

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a cache entry with metadata."""
    data: Any
    timestamp: float
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    size_bytes: int = 0
    
    def __post_init__(self):
        """Calculate size after initialization."""
        try:
            self.size_bytes = len(pickle.dumps(self.data))
        except Exception:
            self.size_bytes = 0


class LRUCache:
    """Thread-safe LRU cache implementation."""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._total_size_bytes = 0
        
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                entry.access_count += 1
                entry.last_accessed = time.time()
                
                # Move to end (most recently used)
                self._cache.move_to_end(key)
                
                logger.debug(f"Cache hit for key: {key[:50]}...")
                return entry.data
            
            logger.debug(f"Cache miss for key: {key[:50]}...")
            return None
    
    def put(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Put item in cache."""
        with self._lock:
            try:
                entry = CacheEntry(
                    data=value,
                    timestamp=time.time()
                )
                
                # Check if we need to evict items
                self._evict_if_needed(entry.size_bytes)
                
                # Remove existing entry if present
                if key in self._cache:
                    old_entry = self._cache[key]
                    self._total_size_bytes -= old_entry.size_bytes
                    del self._cache[key]
                
                # Add new entry
                self._cache[key] = entry
                self._total_size_bytes += entry.size_bytes
                
                logger.debug(f"Cached item with key: {key[:50]}... (size: {entry.size_bytes} bytes)")
                return True
                
            except Exception as e:
                logger.error(f"Failed to cache item: {e}")
                return False
    
    def _evict_if_needed(self, new_item_size: int):
        """Evict items if cache is full."""
        # Evict by count
        while len(self._cache) >= self.max_size:
            self._evict_lru()
        
        # Evict by memory
        while (self._total_size_bytes + new_item_size) > self.max_memory_bytes and self._cache:
            self._evict_lru()
    
    def _evict_lru(self):
        """Evict least recently used item."""
        if self._cache:
            key, entry = self._cache.popitem(last=False)
            self._total_size_bytes -= entry.size_bytes
            logger.debug(f"Evicted LRU item: {key[:50]}...")
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._total_size_bytes = 0
            logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'memory_usage_mb': self._total_size_bytes / (1024 * 1024),
                'max_memory_mb': self.max_memory_bytes / (1024 * 1024),
                'memory_usage_percent': (self._total_size_bytes / self.max_memory_bytes) * 100 if self.max_memory_bytes > 0 else 0
            }


class EmbeddingCache:
    """Specialized cache for embeddings."""
    
    def __init__(self, max_size: int = 10000, max_memory_mb: int = 500):
        self._cache = LRUCache(max_size, max_memory_mb)
        self._lock = threading.RLock()
    
    def get_embedding(self, text: str, model_name: str = "default") -> Optional[List[float]]:
        """Get cached embedding for text."""
        cache_key = self._generate_embedding_key(text, model_name)
        return self._cache.get(cache_key)
    
    def cache_embedding(self, text: str, embedding: List[float], model_name: str = "default") -> bool:
        """Cache embedding for text."""
        cache_key = self._generate_embedding_key(text, model_name)
        return self._cache.put(cache_key, embedding)
    
    def _generate_embedding_key(self, text: str, model_name: str) -> str:
        """Generate cache key for embedding."""
        content = f"{model_name}:{text}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get embedding cache statistics."""
        stats = self._cache.get_stats()
        stats['type'] = 'embedding_cache'
        return stats
    
    def clear(self):
        """Clear embedding cache."""
        self._cache.clear()


class QueryResultCache:
    """Specialized cache for query results."""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100, default_ttl: int = 3600):
        self._cache = LRUCache(max_size, max_memory_mb)
        self.default_ttl = default_ttl
        self._lock = threading.RLock()
    
    def get_query_result(self, query: str, collection_ids: List[str], top_k: int = 10) -> Optional[List[Any]]:
        """Get cached query result."""
        cache_key = self._generate_query_key(query, collection_ids, top_k)
        
        with self._lock:
            entry = self._cache._cache.get(cache_key)
            if entry:
                # Check TTL
                if time.time() - entry.timestamp > self.default_ttl:
                    self._cache._cache.pop(cache_key, None)
                    logger.debug(f"Query cache entry expired: {cache_key[:50]}...")
                    return None
                
                return self._cache.get(cache_key)
            
            return None
    
    def cache_query_result(self, query: str, collection_ids: List[str], results: List[Any], top_k: int = 10) -> bool:
        """Cache query result."""
        cache_key = self._generate_query_key(query, collection_ids, top_k)
        return self._cache.put(cache_key, results)
    
    def _generate_query_key(self, query: str, collection_ids: List[str], top_k: int) -> str:
        """Generate cache key for query."""
        content = f"{query}:{sorted(collection_ids)}:{top_k}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def invalidate_collection(self, collection_id: str):
        """Invalidate all cached results for a collection."""
        with self._lock:
            keys_to_remove = []
            for key in self._cache._cache.keys():
                # This is a simplified approach - in production, you might want
                # to store collection mapping separately
                if collection_id in key:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self._cache._cache.pop(key, None)
                logger.debug(f"Invalidated cache entry for collection {collection_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get query cache statistics."""
        stats = self._cache.get_stats()
        stats['type'] = 'query_cache'
        stats['default_ttl'] = self.default_ttl
        return stats
    
    def clear(self):
        """Clear query cache."""
        self._cache.clear()


class ConnectionPool:
    """Connection pool for API calls."""
    
    def __init__(self, max_connections: int = 10, timeout: float = 30.0):
        self.max_connections = max_connections
        self.timeout = timeout
        self._connections = []
        self._lock = threading.RLock()
        self._created_connections = 0
    
    def get_connection(self):
        """Get connection from pool."""
        with self._lock:
            if self._connections:
                return self._connections.pop()
            elif self._created_connections < self.max_connections:
                # Create new connection (placeholder - implement based on actual API client)
                connection = self._create_connection()
                self._created_connections += 1
                return connection
            else:
                # Wait for available connection or timeout
                # This is a simplified implementation
                return None
    
    def return_connection(self, connection):
        """Return connection to pool."""
        with self._lock:
            if len(self._connections) < self.max_connections:
                self._connections.append(connection)
    
    def _create_connection(self):
        """Create new connection (placeholder)."""
        # This would create actual API client connection
        return {"created_at": time.time(), "id": self._created_connections}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        with self._lock:
            return {
                'available_connections': len(self._connections),
                'total_connections': self._created_connections,
                'max_connections': self.max_connections,
                'utilization_percent': ((self._created_connections - len(self._connections)) / self.max_connections) * 100 if self.max_connections > 0 else 0
            }
    
    def close_all(self):
        """Close all connections."""
        with self._lock:
            self._connections.clear()
            self._created_connections = 0


class CacheManager:
    """Main cache manager coordinating all caching functionality."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize cache manager with configuration."""
        self.config = config or {}
        
        # Initialize caches
        embedding_config = self.config.get('embedding_cache', {})
        self.embedding_cache = EmbeddingCache(
            max_size=embedding_config.get('max_size', 10000),
            max_memory_mb=embedding_config.get('max_memory_mb', 500)
        )
        
        query_config = self.config.get('query_cache', {})
        self.query_cache = QueryResultCache(
            max_size=query_config.get('max_size', 1000),
            max_memory_mb=query_config.get('max_memory_mb', 100),
            default_ttl=query_config.get('default_ttl', 3600)
        )
        
        # Initialize connection pool
        pool_config = self.config.get('connection_pool', {})
        self.connection_pool = ConnectionPool(
            max_connections=pool_config.get('max_connections', 10),
            timeout=pool_config.get('timeout', 30.0)
        )
        
        logger.info("Cache manager initialized")
    
    def get_embedding(self, text: str, model_name: str = "default") -> Optional[List[float]]:
        """Get cached embedding."""
        return self.embedding_cache.get_embedding(text, model_name)
    
    def cache_embedding(self, text: str, embedding: List[float], model_name: str = "default") -> bool:
        """Cache embedding."""
        return self.embedding_cache.cache_embedding(text, embedding, model_name)
    
    def get_query_result(self, query: str, collection_ids: List[str], top_k: int = 10) -> Optional[List[Any]]:
        """Get cached query result."""
        return self.query_cache.get_query_result(query, collection_ids, top_k)
    
    def cache_query_result(self, query: str, collection_ids: List[str], results: List[Any], top_k: int = 10) -> bool:
        """Cache query result."""
        return self.query_cache.cache_query_result(query, collection_ids, results, top_k)
    
    def invalidate_collection_cache(self, collection_id: str):
        """Invalidate all cached data for a collection."""
        self.query_cache.invalidate_collection(collection_id)
        logger.info(f"Invalidated cache for collection: {collection_id}")
    
    def get_connection(self):
        """Get connection from pool."""
        return self.connection_pool.get_connection()
    
    def return_connection(self, connection):
        """Return connection to pool."""
        self.connection_pool.return_connection(connection)
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            'embedding_cache': self.embedding_cache.get_stats(),
            'query_cache': self.query_cache.get_stats(),
            'connection_pool': self.connection_pool.get_stats(),
            'timestamp': time.time()
        }
    
    def clear_all_caches(self):
        """Clear all caches."""
        self.embedding_cache.clear()
        self.query_cache.clear()
        logger.info("All caches cleared")
    
    def shutdown(self):
        """Shutdown cache manager and clean up resources."""
        self.clear_all_caches()
        self.connection_pool.close_all()
        logger.info("Cache manager shutdown completed")


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None
_cache_manager_lock = threading.Lock()


def get_cache_manager(config: Optional[Dict[str, Any]] = None) -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    
    with _cache_manager_lock:
        if _cache_manager is None:
            _cache_manager = CacheManager(config)
        return _cache_manager


def shutdown_cache_manager():
    """Shutdown global cache manager."""
    global _cache_manager
    
    with _cache_manager_lock:
        if _cache_manager:
            _cache_manager.shutdown()
            _cache_manager = None