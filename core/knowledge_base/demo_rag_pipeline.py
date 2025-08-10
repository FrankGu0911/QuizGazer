"""
Demo script showing RAG Pipeline integration and functionality.
"""

import sys
import os
import tempfile
import shutil
from unittest.mock import Mock

sys.path.append(os.path.dirname(__file__))

from models import KnowledgeFragment, Collection
from rag_pipeline import RAGPipeline


def demo_rag_pipeline():
    """Demonstrate RAG pipeline functionality with realistic examples."""
    print("RAG Pipeline Integration Demo")
    print("=" * 50)
    
    # Create mock knowledge base manager with realistic data
    mock_kb_manager = Mock()
    
    # Mock collections
    mock_collections = [
        Collection(
            id="ai_basics",
            name="AI Fundamentals",
            description="Basic concepts in artificial intelligence",
            created_at="2024-01-01T00:00:00",
            document_count=3,
            total_chunks=25
        ),
        Collection(
            id="ml_advanced",
            name="Machine Learning Advanced",
            description="Advanced machine learning techniques",
            created_at="2024-01-02T00:00:00",
            document_count=2,
            total_chunks=18
        )
    ]
    
    mock_kb_manager.list_collections.return_value = mock_collections
    
    # Mock knowledge base stats
    mock_kb_manager.get_knowledge_base_stats.return_value = {
        "total_collections": 2,
        "total_documents": 5,
        "total_chunks": 43,
        "storage_path": "./data/knowledge_base"
    }
    
    # Mock knowledge fragments for different queries
    def mock_search_knowledge(query, collection_ids=None, top_k=5):
        if "人工智能" in query or "artificial intelligence" in query.lower():
            return [
                KnowledgeFragment(
                    content="人工智能（Artificial Intelligence，AI）是计算机科学的一个分支，它企图了解智能的实质，并生产出一种新的能以人类智能相似的方式做出反应的智能机器。",
                    source_document="ai_introduction.pdf",
                    collection_name="AI Fundamentals",
                    relevance_score=0.95,
                    metadata={"document_type": "knowledge", "page": 1, "chunk_index": 0}
                ),
                KnowledgeFragment(
                    content="AI的主要目标是开发能够执行通常需要人类智能的任务的系统，如视觉感知、语音识别、决策制定和语言翻译。",
                    source_document="ai_applications.pdf",
                    collection_name="AI Fundamentals",
                    relevance_score=0.88,
                    metadata={"document_type": "knowledge", "page": 2, "chunk_index": 1}
                )
            ]
        elif "机器学习" in query or "machine learning" in query.lower():
            return [
                KnowledgeFragment(
                    content="机器学习是人工智能的一个子集，它使计算机能够在没有明确编程的情况下学习和改进。机器学习算法通过经验自动改进其性能。",
                    source_document="ml_basics.pdf",
                    collection_name="Machine Learning Advanced",
                    relevance_score=0.92,
                    metadata={"document_type": "knowledge", "page": 1, "chunk_index": 0}
                ),
                KnowledgeFragment(
                    content="监督学习、无监督学习和强化学习是机器学习的三种主要类型。每种类型都有其特定的应用场景和算法。",
                    source_document="ml_types.pdf",
                    collection_name="Machine Learning Advanced",
                    relevance_score=0.85,
                    metadata={"document_type": "knowledge", "page": 3, "chunk_index": 2}
                )
            ]
        else:
            return []
    
    mock_kb_manager.search_knowledge.side_effect = mock_search_knowledge
    
    # Mock LLM service
    def mock_llm_service(prompt):
        if "人工智能" in prompt:
            return "基于提供的知识内容，人工智能（AI）是计算机科学的一个重要分支，旨在创建能够模拟人类智能的机器系统。AI的核心目标是开发能够执行视觉感知、语音识别、决策制定等通常需要人类智能的任务的系统。这项技术正在革命性地改变我们的生活和工作方式。"
        elif "机器学习" in prompt:
            return "根据知识库中的信息，机器学习是人工智能的一个重要子集，它的核心特点是让计算机能够在没有明确编程的情况下自主学习和改进。机器学习主要包括三种类型：监督学习（使用标记数据）、无监督学习（发现数据中的隐藏模式）和强化学习（通过试错学习最优策略）。"
        else:
            return f"我理解您的问题，但在当前的知识库中没有找到直接相关的信息。基于我的通用知识，我可以为您提供一般性的回答。"
    
    # Initialize RAG pipeline
    rag_pipeline = RAGPipeline(
        knowledge_base_manager=mock_kb_manager,
        llm_service=mock_llm_service
    )
    
    # Enable the pipeline
    rag_pipeline.enable_knowledge_base()
    
    print("\n1. RAG Pipeline Status:")
    print("-" * 30)
    
    status = rag_pipeline.get_knowledge_base_status()
    print(f"   Enabled: {status['enabled']}")
    print(f"   Manager Available: {status['manager_available']}")
    print(f"   Total Collections: {status['total_collections']}")
    print(f"   Total Documents: {status['total_documents']}")
    print(f"   Can Process Queries: {status['can_process_queries']}")
    
    print("\n2. Available Collections:")
    print("-" * 30)
    
    collections = mock_kb_manager.list_collections()
    for i, collection in enumerate(collections, 1):
        print(f"   {i}. {collection.name}")
        print(f"      ID: {collection.id}")
        print(f"      Documents: {collection.document_count}")
        print(f"      Chunks: {collection.total_chunks}")
        print()
    
    # Set selected collections
    rag_pipeline.set_selected_collections(["ai_basics", "ml_advanced"])
    
    print("3. Query Processing Examples:")
    print("-" * 30)
    
    # Example 1: AI query
    print("\n   Example 1 - AI Query:")
    query1 = "什么是人工智能？它有哪些主要应用？"
    print(f"   Query: {query1}")
    
    # Show knowledge preview first
    preview1 = rag_pipeline.search_knowledge_preview(query1, top_k=2)
    print(f"   Knowledge Found: {len(preview1)} fragments")
    for fragment in preview1:
        print(f"   - {fragment['source_document']} (score: {fragment['relevance_score']})")
    
    # Process the query
    response1 = rag_pipeline.process_query_with_knowledge(query1)
    print(f"   Response: {response1}")
    print()
    
    # Example 2: ML query
    print("   Example 2 - Machine Learning Query:")
    query2 = "机器学习有哪些主要类型？"
    print(f"   Query: {query2}")
    
    preview2 = rag_pipeline.search_knowledge_preview(query2, top_k=2)
    print(f"   Knowledge Found: {len(preview2)} fragments")
    for fragment in preview2:
        print(f"   - {fragment['source_document']} (score: {fragment['relevance_score']})")
    
    response2 = rag_pipeline.process_query_with_knowledge(query2)
    print(f"   Response: {response2}")
    print()
    
    # Example 3: Query without relevant knowledge
    print("   Example 3 - Query Without Relevant Knowledge:")
    query3 = "今天天气怎么样？"
    print(f"   Query: {query3}")
    
    preview3 = rag_pipeline.search_knowledge_preview(query3, top_k=2)
    print(f"   Knowledge Found: {len(preview3)} fragments")
    
    response3 = rag_pipeline.process_query_with_knowledge(query3)
    print(f"   Response: {response3}")
    print()
    
    print("4. Pipeline Statistics:")
    print("-" * 30)
    
    stats = rag_pipeline.get_pipeline_statistics()
    print(f"   Pipeline Enabled: {stats['pipeline_enabled']}")
    print(f"   Selected Collections: {stats['selected_collections_count']}")
    print(f"   Max Context Length: {stats['max_context_length']}")
    print(f"   Min Relevance Score: {stats['min_relevance_score']}")
    print(f"   Max Knowledge Fragments: {stats['max_knowledge_fragments']}")
    
    print("\n5. Testing Different Modes:")
    print("-" * 30)
    
    # Test with disabled knowledge base
    print("\n   With Knowledge Base Disabled:")
    rag_pipeline.disable_knowledge_base()
    response_disabled = rag_pipeline.process_query_with_knowledge("什么是人工智能？")
    print(f"   Response: {response_disabled}")
    
    # Test with fallback mode
    print("\n   With Fallback Mode Enabled:")
    rag_pipeline.enable_knowledge_base()
    rag_pipeline.enable_fallback_mode()
    response_fallback = rag_pipeline.process_query_with_knowledge("什么是人工智能？")
    print(f"   Response: {response_fallback}")
    
    # Reset to normal mode
    rag_pipeline.disable_fallback_mode()
    
    print("\n" + "=" * 50)
    print("✓ RAG Pipeline Demo Completed Successfully!")
    print("=" * 50)
    
    # Cleanup
    rag_pipeline.close()


if __name__ == "__main__":
    demo_rag_pipeline()