"""
RAG Pipeline - Integrates retrieval with generation, manages the complete RAG workflow.
"""

import logging
from typing import List, Dict, Any, Optional, Callable

try:
    from .manager import KnowledgeBaseManager
    from .retriever import KnowledgeRetriever
    from .models import KnowledgeFragment
except ImportError:
    from manager import KnowledgeBaseManager
    from retriever import KnowledgeRetriever
    from models import KnowledgeFragment

# Import configuration manager
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from utils.config_manager import get_knowledge_base_config
except ImportError:
    get_knowledge_base_config = None
    print("Warning: Configuration manager not available")


class RAGPipeline:
    """Integrates retrieval with generation, manages the complete RAG workflow."""
    
    def __init__(self, knowledge_base_manager: KnowledgeBaseManager = None, 
                 llm_service: Callable[[str], str] = None):
        """
        Initialize the RAG Pipeline.
        
        Args:
            knowledge_base_manager: KnowledgeBaseManager instance
            llm_service: Function to call LLM service (query -> response)
        """
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.kb_config = get_knowledge_base_config() if get_knowledge_base_config else {}
        self.enabled = self.kb_config.get('enabled', False)
        
        # Components
        self.knowledge_base_manager = knowledge_base_manager
        self.llm_service = llm_service
        
        # RAG settings
        self.max_context_length = 4000  # Maximum characters for knowledge context
        self.min_relevance_score = 0.3  # Minimum relevance score for knowledge fragments
        self.max_knowledge_fragments = 5  # Maximum number of knowledge fragments to include
        
        # State
        self._selected_collections: List[str] = []
        self._fallback_mode = False
        
        self.logger.info(f"RAGPipeline initialized (enabled: {self.enabled})")
    
    def set_selected_collections(self, collection_ids: List[str]):
        """
        Set the collections to search in.
        
        Args:
            collection_ids: List of collection IDs to search
        """
        self._selected_collections = collection_ids.copy() if collection_ids else []
        self.logger.debug(f"Selected collections updated: {len(self._selected_collections)} collections")
    
    def get_selected_collections(self) -> List[str]:
        """
        Get the currently selected collections.
        
        Returns:
            List of selected collection IDs
        """
        return self._selected_collections.copy()
    
    def process_query_with_knowledge(self, query: str, selected_collections: List[str] = None) -> str:
        """
        Process a query with knowledge retrieval and generate enhanced response.
        
        Args:
            query: User's query
            selected_collections: Collections to search (None to use default)
            
        Returns:
            Enhanced response from LLM
        """
        if not query or not query.strip():
            return "请提供一个有效的问题。"
        
        query = query.strip()
        
        # Use provided collections or default
        collections_to_search = selected_collections or self._selected_collections
        
        try:
            # Check if knowledge base should be used
            if not self.should_use_knowledge_base():
                self.logger.info("Knowledge base disabled, using standard LLM response")
                return self._generate_standard_response(query)
            
            # Check if we have collections to search
            if not collections_to_search:
                self.logger.info("No collections selected, using standard LLM response")
                return self._generate_standard_response(query)
            
            # Retrieve relevant knowledge
            self.logger.debug(f"Retrieving knowledge for query: {query[:50]}...")
            knowledge_fragments = self._retrieve_knowledge(query, collections_to_search)
            
            if not knowledge_fragments:
                self.logger.info("No relevant knowledge found, using standard LLM response")
                return self._generate_standard_response(query)
            
            # Filter fragments by relevance score
            relevant_fragments = [
                fragment for fragment in knowledge_fragments
                if fragment.relevance_score >= self.min_relevance_score
            ]
            
            if not relevant_fragments:
                self.logger.info("No fragments meet relevance threshold, using standard LLM response")
                return self._generate_standard_response(query)
            
            # Limit number of fragments
            relevant_fragments = relevant_fragments[:self.max_knowledge_fragments]
            
            # Build enhanced prompt
            knowledge_context = self._format_knowledge_context(relevant_fragments)
            enhanced_prompt = self.build_enhanced_prompt(query, knowledge_context)
            
            # Generate response with knowledge
            self.logger.debug(f"Generating enhanced response with {len(relevant_fragments)} knowledge fragments")
            response = self._generate_enhanced_response(enhanced_prompt)
            
            return response
            
        except Exception as e:
            self.logger.error(f"RAG pipeline failed: {e}")
            # Fallback to standard response
            return self._generate_fallback_response(query, str(e))
    
    def build_enhanced_prompt(self, original_query: str, knowledge_context: str) -> str:
        """
        Build an enhanced prompt with knowledge context.
        
        Args:
            original_query: Original user query
            knowledge_context: Formatted knowledge context
            
        Returns:
            Enhanced prompt for LLM
        """
        # Truncate context if too long
        if len(knowledge_context) > self.max_context_length:
            knowledge_context = knowledge_context[:self.max_context_length] + "\n\n[内容已截断...]"
        
        enhanced_prompt = f"""基于以下知识内容回答问题：

{knowledge_context}

问题：{original_query}

请基于上述知识内容提供准确、详细的回答。如果知识内容中没有相关信息，请明确说明并提供你的一般性回答。请在回答中引用相关的知识来源。"""
        
        return enhanced_prompt
    
    def should_use_knowledge_base(self) -> bool:
        """
        Check if knowledge base should be used.
        
        Returns:
            True if knowledge base should be used
        """
        if not self.enabled:
            return False
        
        if self._fallback_mode:
            return False
        
        if not self.knowledge_base_manager:
            return False
        
        # Check if knowledge base has any collections
        try:
            collections = self.knowledge_base_manager.list_collections()
            if hasattr(collections, '__len__'):
                return len(collections) > 0
            else:
                return bool(collections)
        except Exception as e:
            self.logger.warning(f"Failed to check knowledge base status: {e}")
            return False
    
    def get_knowledge_base_status(self) -> Dict[str, Any]:
        """
        Get the current status of the knowledge base.
        
        Returns:
            Dictionary with knowledge base status information
        """
        status = {
            "enabled": self.enabled,
            "fallback_mode": self._fallback_mode,
            "manager_available": self.knowledge_base_manager is not None,
            "llm_service_available": self.llm_service is not None,
            "selected_collections": len(self._selected_collections),
            "total_collections": 0,
            "total_documents": 0,
            "can_process_queries": False
        }
        
        if self.knowledge_base_manager:
            try:
                kb_stats = self.knowledge_base_manager.get_knowledge_base_stats()
                status.update({
                    "total_collections": kb_stats.get("total_collections", 0),
                    "total_documents": kb_stats.get("total_documents", 0),
                    "total_chunks": kb_stats.get("total_chunks", 0),
                    "storage_path": kb_stats.get("storage_path", "Unknown")
                })
            except Exception as e:
                self.logger.warning(f"Failed to get knowledge base stats: {e}")
                status["error"] = str(e)
        
        # Determine if we can process queries
        try:
            total_collections = status.get("total_collections", 0)
            if isinstance(total_collections, int):
                collections_available = total_collections > 0
            else:
                collections_available = bool(total_collections)
        except (TypeError, AttributeError):
            collections_available = False
        
        status["can_process_queries"] = (
            self.enabled and 
            not self._fallback_mode and 
            self.knowledge_base_manager is not None and
            collections_available
        )
        
        return status
    
    def enable_knowledge_base(self):
        """Enable knowledge base functionality."""
        self.enabled = True
        self._fallback_mode = False
        self.logger.info("Knowledge base enabled")
    
    def disable_knowledge_base(self):
        """Disable knowledge base functionality."""
        self.enabled = False
        self.logger.info("Knowledge base disabled")
    
    def enable_fallback_mode(self):
        """Enable fallback mode (disable knowledge retrieval temporarily)."""
        self._fallback_mode = True
        self.logger.info("Fallback mode enabled")
    
    def disable_fallback_mode(self):
        """Disable fallback mode."""
        self._fallback_mode = False
        self.logger.info("Fallback mode disabled")
    
    def search_knowledge_preview(self, query: str, collections: List[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search for knowledge fragments without generating a response (for preview).
        
        Args:
            query: Search query
            collections: Collections to search
            top_k: Maximum number of results
            
        Returns:
            List of knowledge fragment summaries
        """
        if not self.should_use_knowledge_base():
            return []
        
        collections_to_search = collections or self._selected_collections
        if not collections_to_search:
            return []
        
        try:
            fragments = self._retrieve_knowledge(query, collections_to_search, top_k)
            
            return [
                {
                    "content_preview": fragment.content[:200] + "..." if len(fragment.content) > 200 else fragment.content,
                    "source_document": fragment.source_document,
                    "collection_name": fragment.collection_name,
                    "relevance_score": round(fragment.relevance_score, 3),
                    "metadata": {
                        "document_type": fragment.metadata.get("document_type", "unknown"),
                        "chunk_index": fragment.metadata.get("chunk_index", 0)
                    }
                }
                for fragment in fragments
            ]
            
        except Exception as e:
            self.logger.error(f"Knowledge preview search failed: {e}")
            return []
    
    def get_pipeline_statistics(self) -> Dict[str, Any]:
        """
        Get RAG pipeline statistics.
        
        Returns:
            Dictionary with pipeline statistics
        """
        stats = {
            "pipeline_enabled": self.enabled,
            "fallback_mode": self._fallback_mode,
            "selected_collections_count": len(self._selected_collections),
            "max_context_length": self.max_context_length,
            "min_relevance_score": self.min_relevance_score,
            "max_knowledge_fragments": self.max_knowledge_fragments
        }
        
        # Add knowledge base stats if available
        kb_status = self.get_knowledge_base_status()
        stats.update({
            "knowledge_base_status": kb_status,
            "can_process_queries": kb_status.get("can_process_queries", False)
        })
        
        return stats
    
    def _retrieve_knowledge(self, query: str, collections: List[str], top_k: int = None) -> List[KnowledgeFragment]:
        """
        Retrieve knowledge fragments for a query.
        
        Args:
            query: Search query
            collections: Collections to search
            top_k: Maximum number of results
            
        Returns:
            List of knowledge fragments
        """
        if not self.knowledge_base_manager:
            return []
        
        top_k = top_k or self.max_knowledge_fragments * 2  # Get more for filtering
        
        try:
            return self.knowledge_base_manager.search_knowledge(
                query=query,
                collection_ids=collections,
                top_k=top_k
            )
        except Exception as e:
            self.logger.error(f"Knowledge retrieval failed: {e}")
            return []
    
    def _format_knowledge_context(self, fragments: List[KnowledgeFragment]) -> str:
        """
        Format knowledge fragments into context string.
        
        Args:
            fragments: List of knowledge fragments
            
        Returns:
            Formatted context string
        """
        if not fragments:
            return ""
        
        # Use the retriever's formatting if available
        try:
            if (self.knowledge_base_manager and 
                hasattr(self.knowledge_base_manager, 'retriever') and
                self.knowledge_base_manager.retriever and
                hasattr(self.knowledge_base_manager.retriever, 'format_knowledge_context')):
                return self.knowledge_base_manager.retriever.format_knowledge_context(fragments)
        except Exception as e:
            self.logger.debug(f"Could not use retriever formatting: {e}")
        
        # Fallback formatting
        context_parts = ["相关知识内容：\n"]
        
        for i, fragment in enumerate(fragments, 1):
            context_parts.append(f"[知识片段 {i}]")
            context_parts.append(f"来源：{fragment.source_document}")
            context_parts.append(f"相关度：{fragment.relevance_score:.3f}")
            context_parts.append(f"内容：{fragment.content}")
            context_parts.append("")  # Empty line between fragments
        
        return "\n".join(context_parts)
    
    def _generate_standard_response(self, query: str) -> str:
        """
        Generate standard LLM response without knowledge enhancement.
        
        Args:
            query: User query
            
        Returns:
            LLM response
        """
        if self.llm_service:
            try:
                return self.llm_service(query)
            except Exception as e:
                self.logger.error(f"Standard LLM service failed: {e}")
                return f"抱歉，我无法处理您的问题。错误信息：{str(e)}"
        else:
            return "抱歉，语言模型服务不可用。"
    
    def _generate_enhanced_response(self, enhanced_prompt: str) -> str:
        """
        Generate enhanced LLM response with knowledge context.
        
        Args:
            enhanced_prompt: Enhanced prompt with knowledge context
            
        Returns:
            Enhanced LLM response
        """
        if self.llm_service:
            try:
                return self.llm_service(enhanced_prompt)
            except Exception as e:
                self.logger.error(f"Enhanced LLM service failed: {e}")
                # Try to extract original query and use standard response
                lines = enhanced_prompt.split('\n')
                for line in lines:
                    if line.startswith('问题：'):
                        original_query = line[3:].strip()
                        return self._generate_standard_response(original_query)
                return f"抱歉，我无法处理您的问题。错误信息：{str(e)}"
        else:
            return "抱歉，语言模型服务不可用。"
    
    def _generate_fallback_response(self, query: str, error_message: str) -> str:
        """
        Generate fallback response when RAG pipeline fails.
        
        Args:
            query: Original query
            error_message: Error message
            
        Returns:
            Fallback response
        """
        self.logger.warning(f"Using fallback response due to error: {error_message}")
        
        # Try standard response first
        try:
            response = self._generate_standard_response(query)
            # Add a note about the knowledge base being temporarily unavailable
            return f"{response}\n\n注：知识库功能暂时不可用，以上回答基于通用知识。"
        except Exception as e:
            self.logger.error(f"Fallback response also failed: {e}")
            return "抱歉，系统暂时无法处理您的问题，请稍后再试。"
    
    def close(self):
        """Close the RAG pipeline and clean up resources."""
        if self.knowledge_base_manager:
            try:
                self.knowledge_base_manager.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down knowledge base manager: {e}")
        
        self.logger.info("RAG pipeline closed")
    
    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.close()
        except Exception:
            pass