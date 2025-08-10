"""
Knowledge Retriever - Handles vector search, reranking, and knowledge fragment selection.
"""

import logging
import requests
import json
from typing import List, Dict, Any, Optional
import time

try:
    from .models import KnowledgeFragment, SearchResult, RankedResult
    from .vector_store import VectorStoreManager
except ImportError:
    from models import KnowledgeFragment, SearchResult, RankedResult
    from vector_store import VectorStoreManager

# Import configuration manager
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from utils.config_manager import get_api_config
except ImportError:
    get_api_config = None
    print("Warning: Configuration manager not available")


class APIError(Exception):
    """Exception raised for API communication errors."""
    pass


class KnowledgeRetriever:
    """Handles vector search, reranking, and knowledge fragment selection."""
    
    def __init__(self, vector_store_manager: VectorStoreManager = None):
        """
        Initialize the Knowledge Retriever.
        
        Args:
            vector_store_manager: VectorStoreManager instance for database operations
        """
        self.logger = logging.getLogger(__name__)
        self.vector_store_manager = vector_store_manager
        
        # Load API configurations
        self.embedding_config = None
        self.reranker_config = None
        
        if get_api_config:
            try:
                self.embedding_config = get_api_config('embedding_api')
                self.reranker_config = get_api_config('reranker_api')
            except Exception as e:
                self.logger.warning(f"Failed to load API configurations: {e}")
        
        # Request session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'QuizGazer-KnowledgeBase/1.0'
        })
        
        self.logger.info("KnowledgeRetriever initialized")
    
    def retrieve_relevant_knowledge(self, query: str, collections: List[str], top_k: int = 10) -> List[KnowledgeFragment]:
        """
        Retrieve relevant knowledge fragments for a query.
        
        Args:
            query: Search query text
            collections: List of collection names to search in
            top_k: Maximum number of fragments to return
            
        Returns:
            List of relevant KnowledgeFragment objects
        """
        if not query.strip():
            return []
        
        if not collections:
            self.logger.warning("No collections specified for search")
            return []
        
        try:
            # Step 1: Generate query embedding
            self.logger.debug(f"Generating embedding for query: {query[:50]}...")
            query_embedding = self.generate_query_embedding(query)
            
            if not query_embedding:
                self.logger.error("Failed to generate query embedding")
                return []
            
            # Step 2: Perform vector search
            self.logger.debug(f"Searching in collections: {collections}")
            search_results = self.vector_search(query_embedding, collections, top_k * 2)  # Get more candidates for reranking
            
            if not search_results:
                self.logger.info("No search results found")
                return []
            
            # Step 3: Rerank results
            self.logger.debug(f"Reranking {len(search_results)} candidates")
            ranked_results = self.rerank_results(query, search_results)
            
            # Step 4: Convert to KnowledgeFragment objects
            fragments = []
            for i, result in enumerate(ranked_results[:top_k]):
                fragment = KnowledgeFragment(
                    content=result.content,
                    source_document=result.source_info.get('source_file', 'Unknown'),
                    collection_name=result.source_info.get('collection_name', 'Unknown'),
                    relevance_score=result.relevance_score,
                    metadata=result.source_info
                )
                fragments.append(fragment)
            
            self.logger.info(f"Retrieved {len(fragments)} relevant knowledge fragments")
            return fragments
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve relevant knowledge: {e}")
            return []
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """
        Generate embeddings for a query using external API.
        
        Args:
            query: Query text to embed
            
        Returns:
            List of embedding values or empty list if failed
        """
        if not self.embedding_config:
            self.logger.error("Embedding API configuration not available")
            return []
        
        try:
            # Prepare API request
            headers = {
                'Authorization': f'Bearer {self.embedding_config["api_key"]}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.embedding_config['model'],
                'input': query,
                'encoding_format': 'float'
            }
            
            # Make API request
            self.logger.debug(f"Calling embedding API: {self.embedding_config['endpoint']}")
            response = self.session.post(
                self.embedding_config['endpoint'],
                headers=headers,
                json=payload,
                timeout=self.embedding_config.get('timeout', 30)
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Extract embedding from response
            if 'data' in result and len(result['data']) > 0:
                embedding = result['data'][0].get('embedding', [])
                self.logger.debug(f"Generated embedding with {len(embedding)} dimensions")
                return embedding
            else:
                self.logger.error(f"Invalid embedding API response format: {result}")
                return []
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Embedding API request failed: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Failed to generate query embedding: {e}")
            return []
    
    def vector_search(self, embedding: List[float], collections: List[str], top_k: int) -> List[SearchResult]:
        """
        Perform vector similarity search in selected collections.
        
        Args:
            embedding: Query embedding vector
            collections: List of collection names to search
            top_k: Maximum number of results to return
            
        Returns:
            List of SearchResult objects
        """
        if not self.vector_store_manager:
            self.logger.error("VectorStoreManager not available for search")
            return []
        
        if not embedding:
            self.logger.error("Empty embedding provided for search")
            return []
        
        try:
            # Perform search using vector store manager
            search_results = self.vector_store_manager.search_similar(
                collection_names=collections,
                query_embedding=embedding,
                top_k=top_k
            )
            
            self.logger.debug(f"Vector search returned {len(search_results)} results")
            return search_results
            
        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            return []
    
    def rerank_results(self, query: str, candidates: List[SearchResult]) -> List[RankedResult]:
        """
        Rerank search results using external reranker API.
        
        Args:
            query: Original search query
            candidates: List of SearchResult objects to rerank
            
        Returns:
            List of RankedResult objects sorted by relevance
        """
        if not candidates:
            return []
        
        # If reranker API is not available, fall back to distance-based ranking
        if not self.reranker_config:
            self.logger.warning("Reranker API not available, using distance-based ranking")
            return self._fallback_ranking(query, candidates)
        
        try:
            # Prepare documents for reranking
            documents = [candidate.content for candidate in candidates]
            
            # Prepare API request
            headers = {
                'Authorization': f'Bearer {self.reranker_config["api_key"]}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': self.reranker_config['model'],
                'query': query,
                'documents': documents,
                'top_k': len(documents),  # Rerank all candidates
                'return_documents': True
            }
            
            # Make API request
            self.logger.debug(f"Calling reranker API: {self.reranker_config['endpoint']}")
            response = self.session.post(
                self.reranker_config['endpoint'],
                headers=headers,
                json=payload,
                timeout=self.reranker_config.get('timeout', 30)
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Process reranker response
            if 'results' in result:
                ranked_results = []
                for item in result['results']:
                    # Map back to original candidate
                    doc_index = item.get('index', 0)
                    if 0 <= doc_index < len(candidates):
                        original_candidate = candidates[doc_index]
                        
                        ranked_result = RankedResult(
                            content=original_candidate.content,
                            relevance_score=item.get('relevance_score', 0.0),
                            source_info={
                                'collection_name': original_candidate.metadata.get('collection_name', 'Unknown'),
                                'source_file': original_candidate.metadata.get('source_file', 'Unknown'),
                                'chunk_id': original_candidate.chunk_id,
                                'original_distance': original_candidate.distance,
                                **original_candidate.metadata
                            }
                        )
                        ranked_results.append(ranked_result)
                
                # Sort by relevance score (higher is better)
                ranked_results.sort(key=lambda x: x.relevance_score, reverse=True)
                self.logger.debug(f"Reranked {len(ranked_results)} results")
                return ranked_results
            
            else:
                self.logger.error(f"Invalid reranker API response format: {result}")
                return self._fallback_ranking(query, candidates)
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Reranker API request failed: {e}")
            return self._fallback_ranking(query, candidates)
        except Exception as e:
            self.logger.error(f"Failed to rerank results: {e}")
            return self._fallback_ranking(query, candidates)
    
    def _fallback_ranking(self, query: str, candidates: List[SearchResult]) -> List[RankedResult]:
        """
        Fallback ranking based on vector similarity distance.
        
        Args:
            query: Original search query
            candidates: List of SearchResult objects
            
        Returns:
            List of RankedResult objects sorted by distance
        """
        ranked_results = []
        
        for candidate in candidates:
            # Convert distance to relevance score (lower distance = higher relevance)
            # Normalize to 0-1 range where 1 is most relevant
            relevance_score = max(0.0, 1.0 - candidate.distance)
            
            ranked_result = RankedResult(
                content=candidate.content,
                relevance_score=relevance_score,
                source_info={
                    'collection_name': candidate.metadata.get('collection_name', 'Unknown'),
                    'source_file': candidate.metadata.get('source_file', 'Unknown'),
                    'chunk_id': candidate.chunk_id,
                    'original_distance': candidate.distance,
                    **candidate.metadata
                }
            )
            ranked_results.append(ranked_result)
        
        # Sort by relevance score (higher is better)
        ranked_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        self.logger.debug(f"Fallback ranking completed for {len(ranked_results)} results")
        return ranked_results
    
    def format_knowledge_context(self, fragments: List[KnowledgeFragment]) -> str:
        """
        Format knowledge fragments into context for LLM prompt.
        
        Args:
            fragments: List of KnowledgeFragment objects
            
        Returns:
            Formatted context string
        """
        if not fragments:
            return ""
        
        context_parts = []
        context_parts.append("以下是相关的知识内容：\n")
        
        for i, fragment in enumerate(fragments, 1):
            # Format each fragment with source information
            fragment_text = f"[知识片段 {i}]"
            fragment_text += f"\n来源：{fragment.source_document}"
            fragment_text += f"\n集合：{fragment.collection_name}"
            fragment_text += f"\n相关度：{fragment.relevance_score:.3f}"
            fragment_text += f"\n内容：{fragment.content}"
            
            # Add metadata if available
            if fragment.metadata:
                relevant_metadata = []
                for key in ['document_type', 'chunk_index', 'page', 'topic', 'difficulty']:
                    if key in fragment.metadata:
                        relevant_metadata.append(f"{key}: {fragment.metadata[key]}")
                
                if relevant_metadata:
                    fragment_text += f"\n元数据：{', '.join(relevant_metadata)}"
            
            context_parts.append(fragment_text)
        
        context_parts.append("\n请基于以上知识内容回答问题。")
        
        formatted_context = "\n\n".join(context_parts)
        self.logger.debug(f"Formatted context with {len(fragments)} fragments, {len(formatted_context)} characters")
        
        return formatted_context
    
    def get_retrieval_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about retrieval operations.
        
        Returns:
            Dictionary with retrieval statistics
        """
        # This could be extended to track more detailed statistics
        return {
            "embedding_api_available": self.embedding_config is not None,
            "reranker_api_available": self.reranker_config is not None,
            "vector_store_available": self.vector_store_manager is not None,
            "session_active": self.session is not None
        }
    
    def close(self):
        """Close the retriever and clean up resources."""
        if self.session:
            self.session.close()
        self.logger.info("KnowledgeRetriever closed")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.close()
        except Exception:
            pass