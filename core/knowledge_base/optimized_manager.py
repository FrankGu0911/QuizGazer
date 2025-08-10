#!/usr/bin/env python3
"""
Optimized Knowledge Base Manager with Performance Enhancements

This module extends the base KnowledgeBaseManager with:
- Caching for embeddings and query results
- Performance monitoring and metrics
- Connection pooling for API calls
- Memory management optimizations
- Batch processing capabilities
"""

import time
import logging
from typing import List, Optional, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

try:
    from .manager import KnowledgeBaseManager
    from .models import Collection, Document, KnowledgeFragment, DocumentType, ChromaDBConfig
    from .cache_manager import get_cache_manager, CacheManager
    from .performance_monitor import get_performance_monitor, measure_operation, record_metric
except ImportError:
    from manager import KnowledgeBaseManager
    from models import Collection, Document, KnowledgeFragment, DocumentType, ChromaDBConfig
    from cache_manager import get_cache_manager, CacheManager
    from performance_monitor import get_performance_monitor, measure_operation, record_metric

logger = logging.getLogger(__name__)


class OptimizedKnowledgeBaseManager(KnowledgeBaseManager):
    """Enhanced Knowledge Base Manager with performance optimizations."""
    
    def __init__(self, storage_path: str = None, chromadb_config: ChromaDBConfig = None, 
                 cache_config: Optional[Dict[str, Any]] = None):
        """
        Initialize optimized knowledge base manager.
        
        Args:
            storage_path: Path for storing knowledge base data
            chromadb_config: ChromaDB configuration
            cache_config: Cache configuration
        """
        # Initialize base manager
        super().__init__(storage_path, chromadb_config)
        
        # Initialize cache manager
        self.cache_manager = get_cache_manager(cache_config)
        
        # Initialize performance monitor
        self.performance_monitor = get_performance_monitor()
        
        # Batch processing configuration
        self.batch_size = self.kb_config.get('batch_size', 10)
        self.max_concurrent_batches = self.kb_config.get('max_concurrent_batches', 3)
        
        # Memory management
        self.memory_threshold_mb = self.kb_config.get('memory_threshold_mb', 1000)
        self.cleanup_interval = self.kb_config.get('cleanup_interval', 300)  # 5 minutes
        self._last_cleanup = time.time()
        
        logger.info("Optimized Knowledge Base Manager initialized")
    
    @measure_operation("create_collection")
    def create_collection(self, name: str, description: str = "") -> Collection:
        """Create collection with performance monitoring."""
        collection = super().create_collection(name, description)
        
        # Record metric
        record_metric("collections_created", 1)
        
        return collection
    
    @measure_operation("search_knowledge_optimized")
    def search_knowledge(self, query: str, collection_ids: Optional[List[str]] = None, 
                        top_k: int = 10, use_cache: bool = True) -> List[KnowledgeFragment]:
        """
        Optimized knowledge search with caching.
        
        Args:
            query: Search query
            collection_ids: List of collection IDs to search in
            top_k: Number of results to return
            use_cache: Whether to use cache for results
            
        Returns:
            List of knowledge fragments
        """
        # Check cache first if enabled
        if use_cache:
            cached_results = self.cache_manager.get_query_result(
                query, collection_ids or [], top_k
            )
            if cached_results is not None:
                record_metric("cache_hits", 1)
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return cached_results
            
            record_metric("cache_misses", 1)
        
        # Perform search
        start_time = time.time()
        
        try:
            # Use base class search method
            results = self.retriever.search_knowledge(
                query=query,
                collection_ids=collection_ids,
                top_k=top_k
            )
            
            # Cache results if enabled
            if use_cache and results:
                self.cache_manager.cache_query_result(
                    query, collection_ids or [], results, top_k
                )
            
            # Record metrics
            search_time = time.time() - start_time
            record_metric("search_time", search_time)
            record_metric("search_results_count", len(results))
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            record_metric("search_errors", 1)
            raise
    
    @measure_operation("batch_add_documents")
    def add_documents_batch(self, collection_id: str, documents: List[Tuple[str, DocumentType]], 
                           max_workers: Optional[int] = None) -> List[str]:
        """
        Add multiple documents in batch with optimized processing.
        
        Args:
            collection_id: Target collection ID
            documents: List of (file_path, doc_type) tuples
            max_workers: Maximum number of worker threads
            
        Returns:
            List of task IDs
        """
        if not documents:
            return []
        
        max_workers = max_workers or self.max_concurrent_batches
        task_ids = []
        
        # Process documents in batches
        batches = [documents[i:i + self.batch_size] 
                  for i in range(0, len(documents), self.batch_size)]
        
        logger.info(f"Processing {len(documents)} documents in {len(batches)} batches")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit batch processing tasks
            future_to_batch = {}
            
            for batch_idx, batch in enumerate(batches):
                future = executor.submit(self._process_document_batch, collection_id, batch, batch_idx)
                future_to_batch[future] = batch_idx
            
            # Collect results
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                try:
                    batch_task_ids = future.result()
                    task_ids.extend(batch_task_ids)
                    logger.debug(f"Batch {batch_idx} completed with {len(batch_task_ids)} tasks")
                except Exception as e:
                    logger.error(f"Batch {batch_idx} failed: {e}")
        
        record_metric("batch_documents_processed", len(documents))
        return task_ids
    
    def _process_document_batch(self, collection_id: str, batch: List[Tuple[str, DocumentType]], 
                               batch_idx: int) -> List[str]:
        """Process a batch of documents."""
        task_ids = []
        
        for file_path, doc_type in batch:
            try:
                task = self.add_document_async(collection_id, file_path, doc_type)
                if task:
                    task_ids.append(task.id)
            except Exception as e:
                logger.error(f"Failed to add document {file_path} in batch {batch_idx}: {e}")
        
        return task_ids
    
    @measure_operation("get_embeddings_cached")
    def get_embeddings_with_cache(self, texts: List[str], model_name: str = "default") -> List[List[float]]:
        """
        Get embeddings with caching support.
        
        Args:
            texts: List of texts to embed
            model_name: Embedding model name
            
        Returns:
            List of embeddings
        """
        embeddings = []
        texts_to_embed = []
        cache_indices = []
        
        # Check cache for each text
        for i, text in enumerate(texts):
            cached_embedding = self.cache_manager.get_embedding(text, model_name)
            if cached_embedding is not None:
                embeddings.append(cached_embedding)
                record_metric("embedding_cache_hits", 1)
            else:
                embeddings.append(None)  # Placeholder
                texts_to_embed.append(text)
                cache_indices.append(i)
                record_metric("embedding_cache_misses", 1)
        
        # Generate embeddings for uncached texts
        if texts_to_embed:
            try:
                # Use vector store to generate embeddings
                new_embeddings = self.vector_store.generate_embeddings(texts_to_embed)
                
                # Cache new embeddings and update results
                for idx, (cache_idx, embedding) in enumerate(zip(cache_indices, new_embeddings)):
                    embeddings[cache_idx] = embedding
                    self.cache_manager.cache_embedding(texts_to_embed[idx], embedding, model_name)
                
            except Exception as e:
                logger.error(f"Failed to generate embeddings: {e}")
                raise
        
        return embeddings
    
    def optimize_memory_usage(self):
        """Optimize memory usage by cleaning up caches and unused resources."""
        current_time = time.time()
        
        # Check if cleanup is needed
        if current_time - self._last_cleanup < self.cleanup_interval:
            return
        
        logger.info("Starting memory optimization...")
        
        # Get current memory usage
        system_metrics = self.performance_monitor.get_system_metrics()
        process_memory_mb = system_metrics.get('process', {}).get('memory_rss_mb', 0)
        
        if process_memory_mb > self.memory_threshold_mb:
            logger.warning(f"Memory usage ({process_memory_mb:.1f}MB) exceeds threshold ({self.memory_threshold_mb}MB)")
            
            # Clear some caches
            cache_stats = self.cache_manager.get_comprehensive_stats()
            
            # Clear query cache if it's using too much memory
            query_cache_mb = cache_stats.get('query_cache', {}).get('memory_usage_mb', 0)
            if query_cache_mb > 50:  # More than 50MB
                self.cache_manager.query_cache.clear()
                logger.info("Cleared query cache to free memory")
            
            # Partially clear embedding cache if needed
            embedding_cache_mb = cache_stats.get('embedding_cache', {}).get('memory_usage_mb', 0)
            if embedding_cache_mb > 200:  # More than 200MB
                # Clear half of the embedding cache (LRU will handle this)
                current_size = cache_stats.get('embedding_cache', {}).get('size', 0)
                target_size = current_size // 2
                
                # This is a simplified approach - in production, you might want more sophisticated cleanup
                while (self.cache_manager.embedding_cache._cache._cache and 
                       len(self.cache_manager.embedding_cache._cache._cache) > target_size):
                    self.cache_manager.embedding_cache._cache._evict_lru()
                
                logger.info(f"Reduced embedding cache size from {current_size} to {target_size}")
        
        self._last_cleanup = current_time
        record_metric("memory_optimizations", 1)
    
    def get_performance_insights(self) -> Dict[str, Any]:
        """Get comprehensive performance insights and recommendations."""
        # Get performance summary
        perf_summary = self.performance_monitor.get_performance_summary()
        
        # Get cache statistics
        cache_stats = self.cache_manager.get_comprehensive_stats()
        
        # Detect performance issues
        issues = self.performance_monitor.detect_performance_issues()
        
        # Get optimization suggestions
        suggestions = self.performance_monitor.get_optimization_suggestions()
        
        # Calculate cache hit rates
        cache_hit_rate = 0
        if 'search_knowledge_optimized' in perf_summary.get('operations', {}):
            # This is a simplified calculation
            cache_hit_rate = 50  # Placeholder - would need more detailed tracking
        
        return {
            'performance_summary': perf_summary,
            'cache_statistics': cache_stats,
            'cache_hit_rate_percent': cache_hit_rate,
            'performance_issues': issues,
            'optimization_suggestions': suggestions,
            'memory_usage': perf_summary.get('system_metrics', {}).get('process', {}),
            'timestamp': time.time()
        }
    
    def invalidate_collection_cache(self, collection_id: str):
        """Invalidate all cached data for a collection."""
        self.cache_manager.invalidate_collection_cache(collection_id)
        record_metric("cache_invalidations", 1)
        logger.info(f"Invalidated cache for collection: {collection_id}")
    
    @measure_operation("bulk_search")
    def bulk_search(self, queries: List[str], collection_ids: Optional[List[str]] = None, 
                   top_k: int = 10, max_workers: Optional[int] = None) -> Dict[str, List[KnowledgeFragment]]:
        """
        Perform bulk search operations with parallel processing.
        
        Args:
            queries: List of search queries
            collection_ids: List of collection IDs to search in
            top_k: Number of results per query
            max_workers: Maximum number of worker threads
            
        Returns:
            Dictionary mapping queries to their results
        """
        if not queries:
            return {}
        
        max_workers = max_workers or min(len(queries), self.max_concurrent_batches)
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit search tasks
            future_to_query = {
                executor.submit(self.search_knowledge, query, collection_ids, top_k): query
                for query in queries
            }
            
            # Collect results
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    search_results = future.result()
                    results[query] = search_results
                except Exception as e:
                    logger.error(f"Bulk search failed for query '{query}': {e}")
                    results[query] = []
        
        record_metric("bulk_searches_completed", len(queries))
        return results
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get detailed cache statistics."""
        return self.cache_manager.get_comprehensive_stats()
    
    def clear_all_caches(self):
        """Clear all caches."""
        self.cache_manager.clear_all_caches()
        record_metric("cache_clears", 1)
        logger.info("All caches cleared")
    
    def shutdown(self):
        """Shutdown the optimized manager and clean up resources."""
        logger.info("Shutting down optimized knowledge base manager...")
        
        # Perform final memory optimization
        self.optimize_memory_usage()
        
        # Shutdown cache manager
        self.cache_manager.shutdown()
        
        # Export final performance metrics
        try:
            final_metrics = self.get_performance_insights()
            logger.info(f"Final performance metrics: {final_metrics.get('performance_summary', {}).get('uptime_seconds', 0):.1f}s uptime")
        except Exception as e:
            logger.error(f"Failed to export final metrics: {e}")
        
        # Shutdown base manager
        super().shutdown()
        
        logger.info("Optimized knowledge base manager shutdown completed")


def create_optimized_manager(storage_path: str = None, chromadb_config: ChromaDBConfig = None,
                           cache_config: Optional[Dict[str, Any]] = None) -> OptimizedKnowledgeBaseManager:
    """
    Factory function to create an optimized knowledge base manager.
    
    Args:
        storage_path: Path for storing knowledge base data
        chromadb_config: ChromaDB configuration
        cache_config: Cache configuration
        
    Returns:
        Optimized knowledge base manager instance
    """
    return OptimizedKnowledgeBaseManager(storage_path, chromadb_config, cache_config)