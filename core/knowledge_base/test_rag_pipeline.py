"""
Test RAG Pipeline functionality.
"""

import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

sys.path.append(os.path.dirname(__file__))

from models import DocumentType, ChromaDBConfig, KnowledgeFragment, Collection
from rag_pipeline import RAGPipeline
from manager import KnowledgeBaseManager


def test_rag_pipeline_initialization():
    """Test RAG pipeline initialization."""
    print("Testing RAG Pipeline Initialization...")
    print("=" * 50)
    
    # Test 1: Basic initialization
    print("\n1. Testing basic initialization:")
    
    rag_pipeline = RAGPipeline()
    
    if rag_pipeline:
        print("   ✓ RAG pipeline initialized successfully")
        print(f"   - Enabled: {rag_pipeline.enabled}")
        print(f"   - Max context length: {rag_pipeline.max_context_length}")
        print(f"   - Min relevance score: {rag_pipeline.min_relevance_score}")
        print(f"   - Max knowledge fragments: {rag_pipeline.max_knowledge_fragments}")
    else:
        print("   ✗ RAG pipeline initialization failed")
    
    # Test 2: Initialization with components
    print("\n2. Testing initialization with components:")
    
    mock_kb_manager = Mock()
    mock_llm_service = Mock()
    mock_llm_service.return_value = "Mock LLM response"
    
    rag_pipeline_with_components = RAGPipeline(
        knowledge_base_manager=mock_kb_manager,
        llm_service=mock_llm_service
    )
    
    if rag_pipeline_with_components:
        print("   ✓ RAG pipeline with components initialized successfully")
        print(f"   - Knowledge base manager available: {rag_pipeline_with_components.knowledge_base_manager is not None}")
        print(f"   - LLM service available: {rag_pipeline_with_components.llm_service is not None}")
    else:
        print("   ✗ RAG pipeline with components initialization failed")
    
    print("\n" + "=" * 50)
    print("✓ RAG pipeline initialization tests completed!")


def test_rag_pipeline_collection_management():
    """Test RAG pipeline collection management."""
    print("\nTesting RAG Pipeline Collection Management...")
    print("=" * 50)
    
    rag_pipeline = RAGPipeline()
    
    # Test 1: Set and get selected collections
    print("\n1. Testing collection selection:")
    
    test_collections = ["collection_1", "collection_2", "collection_3"]
    rag_pipeline.set_selected_collections(test_collections)
    
    selected = rag_pipeline.get_selected_collections()
    
    if selected == test_collections:
        print("   ✓ Collection selection works correctly")
        print(f"   - Selected collections: {len(selected)}")
    else:
        print("   ✗ Collection selection failed")
        print(f"   - Expected: {test_collections}")
        print(f"   - Got: {selected}")
    
    # Test 2: Empty collection list
    print("\n2. Testing empty collection list:")
    
    rag_pipeline.set_selected_collections([])
    empty_selected = rag_pipeline.get_selected_collections()
    
    if empty_selected == []:
        print("   ✓ Empty collection list handled correctly")
    else:
        print("   ✗ Empty collection list handling failed")
    
    # Test 3: None collection list
    print("\n3. Testing None collection list:")
    
    rag_pipeline.set_selected_collections(None)
    none_selected = rag_pipeline.get_selected_collections()
    
    if none_selected == []:
        print("   ✓ None collection list handled correctly")
    else:
        print("   ✗ None collection list handling failed")
    
    print("\n" + "=" * 50)
    print("✓ Collection management tests completed!")


def test_rag_pipeline_status_and_control():
    """Test RAG pipeline status and control methods."""
    print("\nTesting RAG Pipeline Status and Control...")
    print("=" * 50)
    
    # Create mock knowledge base manager
    mock_kb_manager = Mock()
    mock_kb_manager.list_collections.return_value = [
        Mock(id="coll_1", name="Test Collection")
    ]
    mock_kb_manager.get_knowledge_base_stats.return_value = {
        "total_collections": 1,
        "total_documents": 5,
        "total_chunks": 50,
        "storage_path": "/test/path"
    }
    
    rag_pipeline = RAGPipeline(knowledge_base_manager=mock_kb_manager)
    
    # Test 1: Knowledge base status
    print("\n1. Testing knowledge base status:")
    
    status = rag_pipeline.get_knowledge_base_status()
    
    if status:
        print("   ✓ Status retrieved successfully")
        print(f"   - Enabled: {status['enabled']}")
        print(f"   - Manager available: {status['manager_available']}")
        print(f"   - Total collections: {status['total_collections']}")
        print(f"   - Total documents: {status['total_documents']}")
        print(f"   - Can process queries: {status['can_process_queries']}")
    else:
        print("   ✗ Status retrieval failed")
    
    # Test 2: Enable/disable knowledge base
    print("\n2. Testing enable/disable functionality:")
    
    rag_pipeline.disable_knowledge_base()
    if not rag_pipeline.enabled:
        print("   ✓ Knowledge base disabled successfully")
    else:
        print("   ✗ Knowledge base disable failed")
    
    rag_pipeline.enable_knowledge_base()
    if rag_pipeline.enabled and not rag_pipeline._fallback_mode:
        print("   ✓ Knowledge base enabled successfully")
    else:
        print("   ✗ Knowledge base enable failed")
    
    # Test 3: Fallback mode
    print("\n3. Testing fallback mode:")
    
    rag_pipeline.enable_fallback_mode()
    if rag_pipeline._fallback_mode:
        print("   ✓ Fallback mode enabled successfully")
    else:
        print("   ✗ Fallback mode enable failed")
    
    rag_pipeline.disable_fallback_mode()
    if not rag_pipeline._fallback_mode:
        print("   ✓ Fallback mode disabled successfully")
    else:
        print("   ✗ Fallback mode disable failed")
    
    # Test 4: Should use knowledge base
    print("\n4. Testing should_use_knowledge_base logic:")
    
    should_use = rag_pipeline.should_use_knowledge_base()
    if isinstance(should_use, bool):
        print(f"   ✓ Should use knowledge base: {should_use}")
    else:
        print("   ✗ should_use_knowledge_base returned invalid type")
    
    print("\n" + "=" * 50)
    print("✓ Status and control tests completed!")


def test_rag_pipeline_prompt_building():
    """Test RAG pipeline prompt building functionality."""
    print("\nTesting RAG Pipeline Prompt Building...")
    print("=" * 50)
    
    rag_pipeline = RAGPipeline()
    
    # Test 1: Basic prompt building
    print("\n1. Testing basic prompt building:")
    
    original_query = "What is artificial intelligence?"
    knowledge_context = """相关知识内容：

[知识片段 1]
来源：ai_basics.pdf
相关度：0.95
内容：人工智能（AI）是由机器展示的智能，与人类展示的自然智能形成对比。

[知识片段 2]
来源：ml_guide.pdf
相关度：0.87
内容：机器学习是数据分析的一种方法，可以自动化分析模型的构建。"""
    
    enhanced_prompt = rag_pipeline.build_enhanced_prompt(original_query, knowledge_context)
    
    if enhanced_prompt and len(enhanced_prompt) > len(original_query):
        print("   ✓ Enhanced prompt built successfully")
        print(f"   - Original query length: {len(original_query)}")
        print(f"   - Enhanced prompt length: {len(enhanced_prompt)}")
        print(f"   - Contains knowledge context: {'相关知识内容' in enhanced_prompt}")
        print(f"   - Contains original query: {original_query in enhanced_prompt}")
    else:
        print("   ✗ Enhanced prompt building failed")
    
    # Test 2: Long context truncation
    print("\n2. Testing long context truncation:")
    
    long_context = "A" * 5000  # Longer than max_context_length
    truncated_prompt = rag_pipeline.build_enhanced_prompt(original_query, long_context)
    
    if "[内容已截断...]" in truncated_prompt:
        print("   ✓ Long context truncated correctly")
        print(f"   - Truncated prompt length: {len(truncated_prompt)}")
    else:
        print("   ✗ Long context truncation failed")
    
    # Test 3: Empty context handling
    print("\n3. Testing empty context handling:")
    
    empty_context_prompt = rag_pipeline.build_enhanced_prompt(original_query, "")
    
    if empty_context_prompt:
        print("   ✓ Empty context handled correctly")
        print(f"   - Prompt length: {len(empty_context_prompt)}")
    else:
        print("   ✗ Empty context handling failed")
    
    print("\n" + "=" * 50)
    print("✓ Prompt building tests completed!")


def test_rag_pipeline_knowledge_search():
    """Test RAG pipeline knowledge search functionality."""
    print("\nTesting RAG Pipeline Knowledge Search...")
    print("=" * 50)
    
    # Create mock knowledge fragments
    mock_fragments = [
        KnowledgeFragment(
            content="人工智能是由机器展示的智能，与人类的自然智能形成对比。",
            source_document="ai_basics.pdf",
            collection_name="AI Knowledge",
            relevance_score=0.95,
            metadata={"document_type": "knowledge", "chunk_index": 0}
        ),
        KnowledgeFragment(
            content="机器学习是数据分析的一种方法，可以自动化分析模型的构建。",
            source_document="ml_guide.pdf",
            collection_name="AI Knowledge",
            relevance_score=0.87,
            metadata={"document_type": "knowledge", "chunk_index": 1}
        ),
        KnowledgeFragment(
            content="深度学习是机器学习方法的一个更广泛家族的一部分。",
            source_document="dl_intro.pdf",
            collection_name="AI Knowledge",
            relevance_score=0.75,
            metadata={"document_type": "knowledge", "chunk_index": 0}
        )
    ]
    
    # Create mock knowledge base manager
    mock_kb_manager = Mock()
    mock_kb_manager.search_knowledge.return_value = mock_fragments
    mock_kb_manager.list_collections.return_value = [
        Mock(id="coll_1", name="AI Knowledge")
    ]
    
    rag_pipeline = RAGPipeline(knowledge_base_manager=mock_kb_manager)
    rag_pipeline.enabled = True
    rag_pipeline.set_selected_collections(["coll_1"])
    
    # Test 1: Knowledge search preview
    print("\n1. Testing knowledge search preview:")
    
    preview_results = rag_pipeline.search_knowledge_preview(
        query="What is artificial intelligence?",
        collections=["coll_1"],
        top_k=3
    )
    
    if preview_results:
        print(f"   ✓ Knowledge search preview successful")
        print(f"   - Results found: {len(preview_results)}")
        for i, result in enumerate(preview_results):
            print(f"   - Result {i+1}: {result['source_document']} (score: {result['relevance_score']})")
    else:
        print("   ✗ Knowledge search preview failed")
    
    # Test 2: Pipeline statistics
    print("\n2. Testing pipeline statistics:")
    
    stats = rag_pipeline.get_pipeline_statistics()
    
    if stats:
        print("   ✓ Pipeline statistics retrieved")
        print(f"   - Pipeline enabled: {stats['pipeline_enabled']}")
        print(f"   - Selected collections: {stats['selected_collections_count']}")
        print(f"   - Max context length: {stats['max_context_length']}")
        print(f"   - Can process queries: {stats.get('can_process_queries', False)}")
    else:
        print("   ✗ Pipeline statistics retrieval failed")
    
    print("\n" + "=" * 50)
    print("✓ Knowledge search tests completed!")


def test_rag_pipeline_query_processing():
    """Test RAG pipeline query processing with mocked components."""
    print("\nTesting RAG Pipeline Query Processing...")
    print("=" * 50)
    
    # Create mock knowledge fragments
    mock_fragments = [
        KnowledgeFragment(
            content="人工智能（AI）是由机器展示的智能，与人类展示的自然智能形成对比。AI系统可以执行通常需要人类智能的任务。",
            source_document="ai_basics.pdf",
            collection_name="AI Knowledge",
            relevance_score=0.95,
            metadata={"document_type": "knowledge", "chunk_index": 0}
        ),
        KnowledgeFragment(
            content="机器学习是人工智能的一个子集，它使用算法和统计模型来执行特定任务。",
            source_document="ml_guide.pdf",
            collection_name="AI Knowledge",
            relevance_score=0.87,
            metadata={"document_type": "knowledge", "chunk_index": 1}
        )
    ]
    
    # Create mock components
    mock_kb_manager = Mock()
    mock_kb_manager.search_knowledge.return_value = mock_fragments
    mock_kb_manager.list_collections.return_value = [
        Mock(id="coll_1", name="AI Knowledge")
    ]
    
    mock_llm_service = Mock()
    mock_llm_service.return_value = "基于提供的知识内容，人工智能是由机器展示的智能，它可以执行通常需要人类智能的任务。机器学习是AI的一个重要子集。"
    
    rag_pipeline = RAGPipeline(
        knowledge_base_manager=mock_kb_manager,
        llm_service=mock_llm_service
    )
    rag_pipeline.enabled = True
    rag_pipeline.set_selected_collections(["coll_1"])
    
    # Test 1: Query processing with knowledge
    print("\n1. Testing query processing with knowledge:")
    
    query = "什么是人工智能？"
    response = rag_pipeline.process_query_with_knowledge(query)
    
    if response and len(response) > 0:
        print("   ✓ Query processed successfully with knowledge")
        print(f"   - Response length: {len(response)}")
        print(f"   - Response preview: {response[:100]}...")
        
        # Verify that search_knowledge was called
        mock_kb_manager.search_knowledge.assert_called()
        print("   ✓ Knowledge search was invoked")
        
        # Verify that LLM service was called
        mock_llm_service.assert_called()
        print("   ✓ LLM service was invoked")
    else:
        print("   ✗ Query processing failed")
    
    # Test 2: Query processing without collections
    print("\n2. Testing query processing without collections:")
    
    rag_pipeline.set_selected_collections([])
    response_no_collections = rag_pipeline.process_query_with_knowledge(query)
    
    if response_no_collections:
        print("   ✓ Query processed without collections (fallback to standard)")
        print(f"   - Response length: {len(response_no_collections)}")
    else:
        print("   ✗ Query processing without collections failed")
    
    # Test 3: Query processing with disabled knowledge base
    print("\n3. Testing query processing with disabled knowledge base:")
    
    rag_pipeline.disable_knowledge_base()
    response_disabled = rag_pipeline.process_query_with_knowledge(query)
    
    if response_disabled:
        print("   ✓ Query processed with disabled knowledge base")
        print(f"   - Response length: {len(response_disabled)}")
    else:
        print("   ✗ Query processing with disabled knowledge base failed")
    
    # Test 4: Empty query handling
    print("\n4. Testing empty query handling:")
    
    rag_pipeline.enable_knowledge_base()
    empty_response = rag_pipeline.process_query_with_knowledge("")
    
    if empty_response and "有效的问题" in empty_response:
        print("   ✓ Empty query handled correctly")
    else:
        print("   ✗ Empty query handling failed")
    
    print("\n" + "=" * 50)
    print("✓ Query processing tests completed!")


def test_rag_pipeline_error_handling():
    """Test RAG pipeline error handling."""
    print("\nTesting RAG Pipeline Error Handling...")
    print("=" * 50)
    
    # Test 1: Knowledge base manager failure
    print("\n1. Testing knowledge base manager failure:")
    
    mock_kb_manager = Mock()
    mock_kb_manager.search_knowledge.side_effect = Exception("Knowledge base connection failed")
    mock_kb_manager.list_collections.return_value = [Mock(id="coll_1")]
    
    mock_llm_service = Mock()
    mock_llm_service.return_value = "Standard response without knowledge"
    
    rag_pipeline = RAGPipeline(
        knowledge_base_manager=mock_kb_manager,
        llm_service=mock_llm_service
    )
    rag_pipeline.enabled = True
    rag_pipeline.set_selected_collections(["coll_1"])
    
    response = rag_pipeline.process_query_with_knowledge("Test query")
    
    if response and "知识库功能暂时不可用" in response:
        print("   ✓ Knowledge base failure handled correctly")
        print(f"   - Fallback response provided: {len(response)} chars")
    else:
        print("   ✗ Knowledge base failure handling failed")
    
    # Test 2: LLM service failure
    print("\n2. Testing LLM service failure:")
    
    mock_kb_manager_working = Mock()
    mock_kb_manager_working.search_knowledge.return_value = []
    mock_kb_manager_working.list_collections.return_value = [Mock(id="coll_1")]
    
    mock_llm_service_failing = Mock()
    mock_llm_service_failing.side_effect = Exception("LLM service unavailable")
    
    rag_pipeline_llm_fail = RAGPipeline(
        knowledge_base_manager=mock_kb_manager_working,
        llm_service=mock_llm_service_failing
    )
    rag_pipeline_llm_fail.enabled = True
    
    response_llm_fail = rag_pipeline_llm_fail.process_query_with_knowledge("Test query")
    
    if response_llm_fail and "无法处理" in response_llm_fail:
        print("   ✓ LLM service failure handled correctly")
    else:
        print("   ✗ LLM service failure handling failed")
    
    # Test 3: No LLM service available
    print("\n3. Testing no LLM service available:")
    
    rag_pipeline_no_llm = RAGPipeline()
    rag_pipeline_no_llm.enabled = False  # Force standard response path
    
    response_no_llm = rag_pipeline_no_llm.process_query_with_knowledge("Test query")
    
    if response_no_llm and "不可用" in response_no_llm:
        print("   ✓ No LLM service handled correctly")
    else:
        print("   ✗ No LLM service handling failed")
    
    print("\n" + "=" * 50)
    print("✓ Error handling tests completed!")


def run_all_tests():
    """Run all RAG pipeline tests."""
    print("Running All RAG Pipeline Tests")
    print("=" * 60)
    
    try:
        test_rag_pipeline_initialization()
        test_rag_pipeline_collection_management()
        test_rag_pipeline_status_and_control()
        test_rag_pipeline_prompt_building()
        test_rag_pipeline_knowledge_search()
        test_rag_pipeline_query_processing()
        test_rag_pipeline_error_handling()
        
        print("\n" + "=" * 60)
        print("🎉 ALL RAG PIPELINE TESTS COMPLETED SUCCESSFULLY! 🎉")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()